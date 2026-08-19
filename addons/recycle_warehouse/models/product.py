# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class RecycleProductCategory(models.Model):
    _name = 'recycle.product.category'
    _description = 'Recycle Product Category'
    _order = 'name'

    name = fields.Char(required=True)
    product_ids = fields.One2many('recycle.product', 'category_id', string='Products')

    @api.constrains('name')
    def _check_name_unique(self):
        for rec in self:
            if self.search_count([('name', '=', rec.name), ('id', '!=', rec.id)]):
                raise ValidationError(_('Category name must be unique.'))

    # Categories are authored in the backend and pushed here, exactly like
    # materials — so the outbound POST that used to sit on `create` had nothing
    # to tell the backend that the backend had not just told Odoo, and posted it
    # to a path with no listener anyway. See the note on RecycleProduct.create.


class RecycleProduct(models.Model):
    _name = 'recycle.product'
    _description = 'Recycle Product'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    category_id = fields.Many2one(
        'recycle.product.category', string='Category', required=True, tracking=True)
    price_factory = fields.Float(string='Factory Price', default=0.0, tracking=True)
    price_free_facility = fields.Float(string='Free Facility Price', default=0.0, tracking=True)
    weight = fields.Float(string='Weight per Unit (kg)', default=0.0, tracking=True)
    uom_id = fields.Many2one(
        'recycle.measurement.unit', string='Unit of Measure', required=True,
        tracking=True, ondelete='restrict',
        default=lambda self: self._default_uom_id(),
        help='How this material is counted throughout the app (expected '
             'materials, sorting, stock). The list comes from the backend: '
             'a material can only be measured in a unit the backend '
             'defines, so the two systems can never disagree. Whether a '
             'unit tolerates small natural variance during sorting is '
             'configured on the unit itself, in the backend.')
    condition_price_ids = fields.One2many(
        'recycle.product.condition.price', 'product_id',
        string='Prices per Condition', readonly=True,
        help='Prices pushed by the backend: one line per buyer tier and '
             'material condition, or a single line per tier when the '
             'material has no conditions.')
    active = fields.Boolean(default=True)
    pricing_suspended = fields.Boolean(
        string='Pricing Suspended', compute='_compute_pricing_suspended',
        help='True while this material has no price list at all. Derived from '
             'the mirrored prices rather than synced separately, so it can '
             'never disagree with them.')
    pricing_notice = fields.Char(
        string='Pricing Notice', compute='_compute_pricing_suspended')

    @api.depends('condition_price_ids')
    def _compute_pricing_suspended(self):
        """A material with no prices is SUSPENDED, and says so.

        The admin withdraws a price list in the backend; the empty list is
        pushed here and every price row disappears. Showing such a material with
        a blank price sheet would leave the warehouse guessing whether it is
        free, unpriced or broken — so the sheet states plainly that the list was
        withdrawn and the material is on hold until a new one is added.
        """
        for rec in self:
            suspended = not rec.condition_price_ids
            rec.pricing_suspended = suspended
            rec.pricing_notice = _(
                'The price list for this material was deleted. It is suspended '
                'and cannot be ordered until a new price list is added.'
            ) if suspended else False

    @api.model
    def _default_uom_id(self):
        """First mirrored unit, weight-like ones first (KG is what almost every
        material is measured in). Only a real backend unit is ever proposed —
        there is deliberately no Odoo-side fallback to invent one."""
        Unit = self.env['recycle.measurement.unit'].sudo()
        return Unit.search([('code', '=ilike', 'KG')], limit=1).id \
            or Unit.search([('allows_tolerance', '=', True)], limit=1).id \
            or Unit.search([], limit=1).id \
            or False

    def assert_orderable(self):
        """Refuses a material whose price list was withdrawn.

        Checked here as well as in the backend because an order can also be
        raised inside Odoo, and a material with no price cannot be invoiced —
        the failure would otherwise surface at the invoice, after the goods had
        already been picked.
        """
        for rec in self:
            if rec.pricing_suspended:
                raise ValidationError(_(
                    '"%s" is currently unavailable — its price list was '
                    'deleted and is waiting to be replaced.') % rec.name)

    @api.constrains('price_factory', 'price_free_facility')
    def _check_price(self):
        for rec in self:
            if rec.price_factory < 0 or rec.price_free_facility < 0:
                raise ValidationError(_('Price cannot be negative.'))

    def action_view_prices(self):
        """Open the price sheet of ONE material.

        Prices are authored in the backend (per buyer tier, and per material
        condition when the material has conditions) and mirrored into
        recycle.product.condition.price, so this reads the mirror rather than
        any Odoo-side price of its own.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Prices — %s', self.name),
            'res_model': 'recycle.product.condition.price',
            'view_mode': 'list',
            'domain': [('product_id', '=', self.id)],
            'context': {'default_product_id': self.id, 'create': False},
            'target': 'current',
        }

    @api.model
    def _resolve_unit_code(self, vals):
        """Turn the transient `unit_code` key into a real `uom_id`, in place.

        The backend knows its units by CODE ('KG'), never by an Odoo id, so the
        product push carries the code and it is resolved here — which keeps the
        push a single RPC with no id table on either side. Shared by create AND
        write, so an EDIT that changes the unit in the backend reaches Odoo the
        same way a create does (it did not before: write ignored the key, so a
        unit change never propagated)."""
        code = vals.pop('unit_code', None)
        if code and not vals.get('uom_id'):
            unit = self.env['recycle.measurement.unit'].sudo().with_context(
                active_test=False).search([('code', '=ilike', code)], limit=1)
            if not unit:
                raise ValidationError(_(
                    'Unknown measurement unit "%s". Sync the units first.', code))
            vals['uom_id'] = unit.id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._resolve_unit_code(vals)
        return super().create(vals_list)

    def write(self, vals):
        # A backend EDIT that changes the unit sends `unit_code`; resolve it the
        # same way create does, otherwise Odoo would reject the write with
        # "Invalid field 'unit_code'" and the edit would never land.
        self._resolve_unit_code(vals)
        res = super().write(vals)
        # REVERSE sync: a NAME edited on the Odoo screen is mirrored back to the
        # backend. Fired on any name write — the backend applies it only when it
        # actually differs and never pushes back, so a backend→Odoo push that
        # comes straight back here finds no diff and stops (no ping-pong).
        if 'name' in vals:
            Sync = self.env['recycle.backend.sync'].sudo()
            for rec in self:
                try:
                    Sync.notify_product_changed(rec)
                except Exception:            # noqa: BLE001 — reported, never raised
                    _logger.exception(
                        'Could not tell the backend that product %s was renamed',
                        rec.display_name)
        return res

    # NOTE — deliberately NOT pushed to the backend.
    #
    # `create` and `write` used to POST to `/webhooks/odoo/products`, a path the
    # backend has no listener for. Every call 404'd in silence, and because a
    # product only ever reaches Odoo by being pushed FROM the backend, the
    # commonest effect was a doomed outbound request on every catalog sync — the
    # backend telling Odoo about a product, and Odoo immediately telling the
    # backend about the product it had just been given.
    #
    # The catalog has one author: the backend. Odoo cannot create or edit a
    # material — its dashboard offers a SUGGESTION form instead, and that route
    # (`product-suggestion`) is live and listened to. So there is nothing here
    # for the backend to learn, and a push that only ever fails is worse than no
    # push: it reads, to anyone auditing, as a channel that exists.
