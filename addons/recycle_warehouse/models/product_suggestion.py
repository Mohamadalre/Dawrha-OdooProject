# -*- coding: utf-8 -*-
"""The Odoo administrator PROPOSES a material; they no longer create one.

Why the change: a material only becomes visible to a buyer once it has a price
list for that buyer's tier, and prices are authored in the backend. A material
created here would therefore exist in Odoo, appear to nobody in the app, and be
orderable by no one — a row that looks like work done and does nothing. So the
Odoo side sends the idea to the backend's review queue and the backend admin
creates the real material together with its prices.

The proposal itself is deliberately thin: name, category, unit, description.
Anything more (prices, tiers, conditions) would be authored on the wrong side.
"""
import json
import logging
from urllib import request as _urlrequest

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class RecycleProductSuggestion(models.Model):
    _name = 'recycle.product.suggestion'
    _description = 'Material Suggestion (to backend review)'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(string='Material Name', required=True, tracking=True)
    # ── Which category? An existing one, or one that does not exist yet ──
    #
    # A new material very often belongs to a category nobody has set up. With
    # only the picker below, the proposer had two options and both lost the
    # information the proposal was made to carry: file it under a category it
    # does not belong to, or leave it empty and hope the reviewer guesses.
    category_mode = fields.Selection([
        ('existing', 'An existing category'),
        ('new', 'A new category (propose it too)'),
    ], string='Category', default='existing', required=True, tracking=True)
    category_id = fields.Many2one(
        'recycle.product.category', string='Existing Category', tracking=True,
        help='Sent to the backend BY NAME: the two systems name categories the '
             'same way but do not share keys. An unmatched name is kept as '
             'text on the proposal so the reviewer still reads it.')
    new_category_name = fields.Char(
        string='Proposed Category', tracking=True,
        help='A category you believe should exist. It is sent as a REQUEST — '
             'nothing is created automatically on either side. Categories are '
             'the shape of the whole catalogue, and one created from a typed '
             'name would be spelled differently by the next proposer with '
             'nothing to merge the two.')
    # The unit is NOT part of a backend suggestion — the backend proposal is a
    # name + a category + pictures + a description, and the unit is chosen later,
    # when the real material is authored there. Kept on the model (optional, no
    # longer on the form or in the payload) only so existing rows are undisturbed.
    uom_id = fields.Many2one(
        'recycle.measurement.unit', string='Unit of Measure', required=False,
        ondelete='restrict', tracking=True)
    description = fields.Text(string='Why this material?')

    # ── Pictures of the proposed material ──────────────────────────────
    #
    # The backend already stores image URLs on a suggestion and shows them to the
    # reviewer; the Odoo side simply never sent any. A name and a category rarely
    # settle whether a material is worth adding — a photo does — so the proposer
    # attaches one or more here and they travel to the backend as URLs (see
    # `_image_urls`).
    image_ids = fields.Many2many(
        'ir.attachment',
        'recycle_suggestion_attachment_rel', 'suggestion_id', 'attachment_id',
        string='Images',
        help='Photos of the material. Sent to the backend so the reviewer sees '
             'what is being proposed.')

    state = fields.Selection(
        [('draft', 'Draft'),
         ('submitted', 'Sent for Review'),
         ('failed', 'Not Sent')],
        default='draft', required=True, tracking=True, readonly=True,
        help='Only whether the proposal REACHED the backend. The decision '
             'itself is taken there and is not mirrored here — showing a stale '
             '"approved" in Odoo would be worse than showing nothing.')
    backend_suggestion_id = fields.Char(
        string='Backend Reference', readonly=True, copy=False,
        help='The id the backend filed this proposal under.')
    submitted_on = fields.Datetime(readonly=True, copy=False)
    last_error = fields.Char(readonly=True, copy=False)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _submit(self):
        """Push the proposal and record the outcome. True on success.

        Never raises: a failure is RECORDED, not thrown. Raising would roll the
        transaction back — taking the error message with it — and leave a record
        that shows no sign anything went wrong. The state stays re-sendable, so
        the reconcile cron (and the Send button) can try again when the backend
        is back.
        """
        self.ensure_one()
        if self.state == 'submitted':
            return True
        ok, data, error = self._push()
        if ok:
            self.with_context(recycle_suggestion_sync=True).write({
                'state': 'submitted',
                'submitted_on': fields.Datetime.now(),
                'backend_suggestion_id': (data or {}).get('suggestion_id') or '',
                'last_error': False,
            })
            self.message_post(body=_('Sent to the backend for review.'))
            return True
        self.with_context(recycle_suggestion_sync=True).write({
            'state': 'failed',
            'last_error': error or _('Unknown error'),
        })
        return False

    def action_submit(self):
        """Manual re-send (the button). Auto-send already runs on create.

        Idempotent on an already-sent proposal: since `create` now auto-submits,
        a caller that creates and then submits (the admin dashboard does exactly
        that) would otherwise hit "already sent" on its own successful push. An
        already-submitted proposal is simply reported as sent.
        """
        self.ensure_one()
        if self.state == 'submitted':
            return True
        if self._submit():
            return True
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'danger',
                'title': _('Not sent'),
                'message': _('Could not reach the backend: %s\n'
                             'Nothing was lost — it will be re-sent automatically '
                             'when the backend is back, or press Send again.')
                           % (self.last_error or _('unknown error')),
                'sticky': True,
            },
        }

    def action_reset_to_draft(self):
        self.write({'state': 'draft', 'last_error': False})
        return True

    @api.model_create_multi
    def create(self, vals_list):
        """Send the proposal to the backend the moment it is created.

        "Appears immediately" without a second click. Best-effort: a push that
        cannot reach the backend leaves the record 'failed' and re-sendable, and
        the reconcile cron retries it when the connection returns — so a proposal
        made while the backend was down still turns up once it is back.
        """
        records = super().create(vals_list)
        for rec in records:
            try:
                rec._submit()
            except Exception as exc:  # a sync failure must never block the create
                _logger.warning('Auto-submit on create failed: %s', exc)
        return records

    @api.model
    def _cron_resend_pending(self):
        """Retry proposals that never reached the backend (the disconnect case).

        A proposal created while the backend was unreachable sits in 'failed';
        this re-pushes it the moment the backend is back, so it 'appears when the
        connection returns' without anyone re-opening it. Drafts are left alone —
        those were intentionally not sent.
        """
        for rec in self.search([('state', '=', 'failed')], limit=50):
            rec._submit()

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------
    def _push(self):
        """POST the proposal. Returns (ok, parsed_body, error_message).

        Written here rather than through recycle.backend.sync because this is
        the one outbound call whose RESPONSE matters: the backend hands back the
        id it filed the proposal under, and that id is what makes a retry after
        a timeout update the same row instead of filing a duplicate.
        """
        self.ensure_one()
        icp = self.env['ir.config_parameter'].sudo()
        base = (icp.get_param('recycle.backend_base_url') or '').rstrip('/')
        secret = icp.get_param('recycle.backend_webhook_secret') or ''
        if not base:
            return False, None, _('backend base URL is not configured')
        if not secret:
            return False, None, _('backend webhook secret is not configured')

        path = (icp.get_param('recycle.backend_route_product_suggestion')
                or '/api/v1/odoo/webhooks/product-suggestion')
        # The two category fields travel in DIFFERENT keys. `category_name` is
        # matched against the backend's existing categories; `new_category_name`
        # is a request for one that has none to match. Sending both under one key
        # would make an unmatched name indistinguishable from a typo in an
        # existing one — and the reviewer's response to those is not the same.
        payload = {
            'odoo_suggestion_id': self.id,
            'product_name': self.name,
            'category_name': (
                self.category_id.name if self.category_mode == 'existing' else None
            ) or None,
            'new_category_name': (
                (self.new_category_name or '').strip()
                if self.category_mode == 'new' else None
            ) or None,
            'description': self.description or None,
            # Pictures as URLs the backend can display — see `_image_urls`.
            'image_urls': self._image_urls(),
            'suggested_by': self.env.user.name,
        }
        try:
            req = _urlrequest.Request(
                base + path,
                data=json.dumps(payload, default=str).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'x-odoo-webhook-secret': secret,
                },
                method='POST')
            with _urlrequest.urlopen(req, timeout=8) as resp:
                body = json.loads(resp.read().decode('utf-8') or '{}')
                # The backend wraps every response in {success, message, data}.
                data = body.get('data') if isinstance(body, dict) else None
                return True, (data if isinstance(data, dict) else body), None
        except Exception as exc:
            _logger.warning('Material suggestion push failed: %s', exc)
            return False, None, str(exc)

    def _image_urls(self):
        """Public, tokened URLs for the proposal's images.

        The backend stores URLs, not bytes, so each attachment is addressed
        through Odoo's own image route with an access token — the link works for
        whoever holds it (the reviewer) without turning every proposal photo into
        an unauthenticated public asset. Empty when there are no images, which the
        backend accepts (`image_urls` is optional there).
        """
        self.ensure_one()
        base = (self.env['ir.config_parameter'].sudo()
                .get_param('web.base.url') or '').rstrip('/')
        urls = []
        for att in self.image_ids:
            token = att.sudo().generate_access_token()[0]
            urls.append('%s/web/image/%s?access_token=%s' % (base, att.id, token))
        return urls

    # ------------------------------------------------------------------
    # Guards
    # ------------------------------------------------------------------
    @api.constrains('category_mode', 'category_id', 'new_category_name')
    def _check_category_choice(self):
        """Whichever mode is chosen must actually carry its answer.

        A proposal that says "a new category" and names none is not a request —
        it is a blank the reviewer cannot act on, and it would arrive looking
        exactly like a proposal with no category at all.
        """
        for rec in self:
            if rec.category_mode == 'new' and not (rec.new_category_name or '').strip():
                raise ValidationError(_(
                    'Name the category you are proposing, or choose an existing '
                    'one instead.'))

    @api.onchange('category_mode')
    def _onchange_category_mode(self):
        """Clear the field that no longer applies.

        Leaving the other one filled would send a category the proposer has
        stopped choosing, and the payload keys are what tell the reviewer which
        of the two questions was being answered.
        """
        if self.category_mode == 'new':
            self.category_id = False
        else:
            self.new_category_name = False

    def write(self, vals):
        # A proposal the backend has already filed must not drift from what was
        # actually sent; edit it there, or reset and send again.
        if not self.env.context.get('recycle_suggestion_sync'):
            locked = self.filtered(lambda r: r.state == 'submitted')
            content = {'name', 'category_id', 'uom_id', 'description',
                       'category_mode', 'new_category_name', 'image_ids'}
            if locked and content.intersection(vals):
                raise UserError(
                    _('This suggestion is already with the backend. Reset it to '
                      'draft first if you need to change it.'))
        return super().write(vals)

    @api.model
    def _default_uom_id(self):
        return self.env['recycle.measurement.unit'].search([], limit=1)
