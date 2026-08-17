# -*- coding: utf-8 -*-
"""Driver applications pushed from the NestJS backend.

Flow (the backend owns the driver ACCOUNT, Odoo owns the DECISION):
1. A collector finishes onboarding in the app → the backend calls
   ``recycle.driver.request`` ``create`` over JSON-RPC with his info and
   uploaded document images (CONTRACT — field names must not change:
   backend_driver_id, name, email, phone, image_ids[backend_media_id,
   file_type, url]).
2. The Odoo admin reviews it in the dashboard ("Driver Requests"):
   - Accept → assign a warehouse → webhook driver-decision {status:ACTIVE}
     → backend activates the account and notifies the driver.
   - Reject with a reason → {status:REJECTED, rejection_reason}.
   - Reject a single image → {status:NEED_CHANGES, rejected_media_ids}
     → backend marks that media REJECTED, the driver re-uploads and the
     request is RE-PUSHED here (create() upserts by backend_driver_id).

Unlike the fire-and-forget stat pings, decision webhooks are STRICT: when
the backend cannot be reached the action raises and nothing is saved, so
Odoo and the backend can never disagree about a driver's status.
"""
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

DECISION_STATES = [
    ('pending', 'Pending'),
    ('accepted', 'Accepted'),
    ('rejected', 'Rejected'),
    ('need_changes', 'Needs Changes'),
]


class RecycleDriverRequest(models.Model):
    _name = 'recycle.driver.request'
    _description = 'Driver Application (from backend)'
    _order = 'create_date desc'

    backend_driver_id = fields.Char(
        'Backend Driver ID', required=True, index=True,
        help='UUID of the collector profile in the NestJS backend.')
    name = fields.Char('Driver Name', required=True)
    email = fields.Char('Email')
    phone = fields.Char('Phone')
    truck_history_ids = fields.One2many(
        'recycle.truck.assignment.history', 'driver_request_id',
        string='Trucks Held', readonly=True)
    national_id = fields.Char(
        'National ID',
        help='National identity number the driver registered with — check it '
             'against the uploaded identity documents.')
    state = fields.Selection(
        DECISION_STATES, default='pending', required=True, index=True)

    # ── Registered location (pushed by the backend, which owns the provinces
    # table — it sends the province NAME so nothing here shows a raw uuid). ──
    province_name = fields.Char('Governorate')
    address = fields.Char('Address')
    location_note = fields.Char('Location Note')
    latitude = fields.Float('Latitude', digits=(10, 7))
    longitude = fields.Float('Longitude', digits=(10, 7))
    rejection_reason = fields.Text('Rejection / Change Reason')
    warehouse_id = fields.Many2one(
        'recycle.warehouse', string='Warehouse', ondelete='set null',
        help='Warehouse the driver was assigned to on acceptance.')
    shift_id = fields.Many2one(
        'recycle.shift', string='Shift', ondelete='set null', index=True,
        help='The driver shift the driver picked during onboarding in the '
             'app (pushed by the backend as shift_odoo_id).')
    is_blocked = fields.Boolean(
        'Blocked', default=False,
        help='Mirror of the BLOCKED account status in the backend: the '
             'driver is thrown out of the app and cannot sign in again '
             'until unblocked.')
    blocked_reason = fields.Char('Block Reason')
    decided_at = fields.Datetime('Decided At', readonly=True)
    image_ids = fields.One2many(
        'recycle.driver.request.image', 'request_id', string='Documents')

    # Shift details, surfaced flat so the review screen can show "name
    # (start – end)" without a second round-trip per request.
    shift_name = fields.Char(related='shift_id.name', string='Shift Name', readonly=True)
    shift_start = fields.Float(related='shift_id.start_time', string='Shift Start', readonly=True)
    shift_end = fields.Float(related='shift_id.end_time', string='Shift End', readonly=True)

    has_rejected_image = fields.Boolean(
        'Has a rejected document', compute='_compute_has_rejected_image',
        help='True while at least one document is rejected. The request cannot '
             'be accepted until the driver re-uploads it (the re-push from the '
             'backend replaces the images and clears this).')

    _backend_driver_uniq = models.Constraint(
        'unique(backend_driver_id)',
        'A request for this driver already exists.')

    @api.depends('image_ids.status')
    def _compute_has_rejected_image(self):
        for rec in self:
            rec.has_rejected_image = any(
                i.status == 'rejected' for i in rec.image_ids)

    # ------------------------------------------------------------------
    # Create = UPSERT (contract with the backend re-push after re-upload)
    # ------------------------------------------------------------------
    @api.model
    def _resolve_shift_vals(self, vals):
        """The backend pushes the driver's chosen shift as ``shift_odoo_id``
        (this database's shift id, mirrored there) — translate it to the
        relational field and drop the raw key so ``create/write`` stay
        clean. Unknown/stale ids resolve to no shift rather than crashing."""
        if 'shift_odoo_id' in vals:
            raw = vals.pop('shift_odoo_id')
            shift = self.env['recycle.shift'].sudo().browse(
                int(raw or 0)).exists()
            vals['shift_id'] = shift.id if shift else False
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        """The backend always calls plain ``create`` — including when the
        driver re-uploads a rejected document. Upsert by backend_driver_id:
        refresh the existing request (replacing its images) and reset it to
        pending instead of duplicating."""
        records = self.browse()
        for vals in vals_list:
            self._resolve_shift_vals(vals)
            existing = self.browse()
            if vals.get('backend_driver_id'):
                existing = self.search(
                    [('backend_driver_id', '=', vals['backend_driver_id'])],
                    limit=1)
            if existing:
                if vals.get('image_ids'):
                    existing.image_ids.sudo().unlink()
                vals.setdefault('rejection_reason', False)
                existing.write(vals)
                # The request is back under review only once the driver has
                # answered EVERYTHING he was asked for.
                #
                # This used to force 'pending' unconditionally, which was wrong
                # the moment two documents were requested at once: replacing the
                # first put the whole request back in the queue while the second
                # was still outstanding, and the reviewer opened an application
                # that looked complete and was not.
                #
                # The statuses now arrive from the backend with each file, so
                # what is still outstanding is knowable here rather than assumed.
                if 'state' not in vals:
                    still_asked = existing.image_ids.filtered('reupload_requested')
                    existing.state = 'need_changes' if still_asked else 'pending'
                records |= existing
            else:
                records |= super().create([vals])
        records._notify_admins_new()
        return records

    def _notify_admins_new(self):
        for rec in self:
            try:
                self.env['recycle.notification'].sudo()._notify_admins(
                    _('New driver request'),
                    _('Driver "%s" submitted an application — review it in '
                      'Driver Requests.') % rec.name)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Decisions (STRICT webhook: raise when the backend is unreachable)
    # ------------------------------------------------------------------
    def _send_decision(self, status, reason=None, rejected_media_ids=None,
                       approved_media_ids=None,
                       warehouse_odoo_id=None, warehouse_change_only=False,
                       documents_only=False, request_reupload=False,
                       cancel_reupload=False):
        self.ensure_one()
        ok = self.env['recycle.backend.sync'].sudo().notify_driver_decision(
            self.backend_driver_id, status,
            reason=reason, rejected_media_ids=rejected_media_ids,
            approved_media_ids=approved_media_ids,
            warehouse_odoo_id=warehouse_odoo_id,
            warehouse_change_only=warehouse_change_only,
            documents_only=documents_only,
            request_reupload=request_reupload,
            cancel_reupload=cancel_reupload)
        if not ok:
            # MARKING A DOCUMENT IS NOT A DECISION ABOUT THE DRIVER.
            #
            # `documents_only` is a reviewer's private working note: they are
            # reading four scans and marking each as they go. Nothing reaches
            # the driver, no status moves, and nothing he can see changes. So
            # refusing to record it because a remote service is unreachable
            # blocks the reviewer's entire workflow over a step that never
            # needed to be atomic — which is exactly what happened: with the
            # backend down, neither "reject image" nor "accept image" would
            # save anything at all, and the buttons looked broken.
            #
            # It is safe to let this one through because it SELF-HEALS at the
            # only moment it matters. Asking the driver for a document
            # (`action_request_reupload`) re-sends those media ids with
            # `request_reupload`, and the backend marks them REJECTED again —
            # so a lost marking ping is re-asserted by the very act that makes
            # the marking consequential.
            #
            # Every other call here DOES reach the driver or moves his account,
            # and those stay strict: the two systems must never disagree about
            # whether somebody was accepted, rejected or asked for something.
            if documents_only:
                _logger.warning(
                    'Backend unreachable while marking documents on driver '
                    'request %s — recorded here; the next request/cancel will '
                    're-assert it.', self.id)
                return
            raise UserError(_(
                'Could not reach the Dawrha backend — the driver was NOT '
                'notified, so the decision was not saved. Check the backend '
                'connection settings and try again.'))

    def action_accept(self, warehouse_id):
        """Accept the driver and assign him to a warehouse (mandatory). The
        backend mirrors the warehouse, flips the account ACTIVE and notifies
        him he will be assigned to a truck soon."""
        self.ensure_one()
        if self.state == 'accepted':
            raise UserError(_('This request is already accepted.'))
        # A rejected document must be replaced FIRST: the driver re-uploads it
        # in the app, which re-pushes the request here (images replaced, state
        # back to pending) and only then can it be accepted.
        if self.has_rejected_image:
            raise UserError(_(
                'A document was rejected — wait until the driver re-uploads it '
                'before accepting this request.'))
        warehouse = self.env['recycle.warehouse'].browse(
            int(warehouse_id or 0)).exists()
        if not warehouse:
            raise UserError(_('Choose the warehouse this driver will serve.'))
        self._send_decision('ACTIVE', warehouse_odoo_id=warehouse.id)
        self.write({
            'state': 'accepted',
            'warehouse_id': warehouse.id,
            'rejection_reason': False,
            'decided_at': fields.Datetime.now(),
        })
        self.image_ids.filtered(
            lambda i: i.status != 'accepted').write({'status': 'accepted'})
        return True

    def action_reject(self, reason):
        """Reject the application with a mandatory reason.

        Every document must have been judged first. A rejection has to be
        answerable afterwards, and "we said no while three of your four
        documents were still unread" is not an answer — the driver cannot be
        told what to fix, and nobody reviewing the decision later can tell what
        it rested on.

        Note this is a STRICTER gate than acceptance, which tolerates unread
        documents and settles them. That asymmetry is deliberate: accepting is
        itself a statement that the submission is acceptable, so it can settle
        what is open; rejecting names a fault and therefore has to have looked.
        """
        self.ensure_one()
        reason = (reason or '').strip()
        if not reason:
            raise UserError(_('A rejection reason is required.'))
        if self.state == 'accepted':
            raise UserError(_(
                'This request is already accepted — an acceptance cannot be '
                'withdrawn. Block the driver instead.'))
        if self.state == 'need_changes':
            raise UserError(_(
                'This driver was asked to re-upload a document and has not done '
                'so yet — wait for his answer before deciding.'))
        unread = self.image_ids.filtered(lambda i: i.status == 'pending')
        if unread:
            raise UserError(_(
                'Some documents have not been reviewed. Accept or reject each '
                'of them before rejecting the request.'))
        self._send_decision('REJECTED', reason=reason)
        self.write({
            'state': 'rejected',
            'rejection_reason': reason,
            'decided_at': fields.Datetime.now(),
        })
        return True

    def action_reactivate(self):
        """Undo a rejection: put the request back under review (pending) and
        flip the driver's account back to PENDING_APPROVAL in the backend, so
        the admin can reconsider an application he rejected by mistake.

        Uses the same STRICT webhook as every other decision — if the backend
        is unreachable nothing is saved here, so the two sides cannot disagree.
        """
        self.ensure_one()
        if self.state != 'rejected':
            raise UserError(_('Only a rejected request can be re-opened.'))
        self._send_decision('PENDING_APPROVAL')
        self.write({
            'state': 'pending',
            'rejection_reason': False,
            'decided_at': False,
        })
        return True

    # ------------------------------------------------------------------
    # Block / unblock (admin, or the manager of the driver's warehouse)
    # ------------------------------------------------------------------
    def _check_block_scope(self):
        """Admin: any driver. Manager: only drivers of his own warehouse."""
        self.ensure_one()
        is_admin, forced_wh = self.env[
            'recycle.driver.assignment']._assignment_actor_scope()
        if not is_admin and self.warehouse_id.id != forced_wh.id:
            raise UserError(_(
                'Only the administrator or the manager of this driver\'s '
                'warehouse can block or unblock him.'))

    def action_block(self, reason=None):
        """Block the driver: the backend flips his account to BLOCKED, kills
        every session (forced logout) and refuses sign-ins until unblocked."""
        self.ensure_one()
        self._check_block_scope()
        if self.state != 'accepted':
            raise UserError(_('Only accepted drivers can be blocked.'))
        if self.is_blocked:
            raise UserError(_('This driver is already blocked.'))
        reason = (reason or '').strip() or None
        self._send_decision('BLOCKED', reason=reason)
        self.sudo().write({'is_blocked': True, 'blocked_reason': reason})
        return True

    def action_unblock(self):
        """Unblock: the backend re-activates the account so he can sign in
        again (his warehouse is re-sent so the mirror stays intact)."""
        self.ensure_one()
        self._check_block_scope()
        if not self.is_blocked:
            raise UserError(_('This driver is not blocked.'))
        self._send_decision(
            'ACTIVE', warehouse_odoo_id=self.warehouse_id.id or None)
        self.sudo().write({'is_blocked': False, 'blocked_reason': False})
        return True

    # ------------------------------------------------------------------
    # Relocate to another warehouse (admin only)
    # ------------------------------------------------------------------
    def action_change_warehouse(self, warehouse_id):
        """Move the driver to another warehouse. His truck assignment is
        dropped when the truck belongs to the OLD warehouse (trucks never
        follow drivers across warehouses); the backend mirror is updated
        silently (no status change, no notification)."""
        self.ensure_one()
        if not (self.env.su or self.env.user.has_group(
                'recycle_warehouse.group_recycle_admin')):
            raise UserError(_(
                'Only the administrator can change a driver\'s warehouse.'))
        if self.state != 'accepted':
            raise UserError(_('Only accepted drivers can be relocated.'))
        warehouse = self.env['recycle.warehouse'].browse(
            int(warehouse_id or 0)).exists()
        if not warehouse:
            raise UserError(_('Choose the new warehouse.'))
        if warehouse.id == self.warehouse_id.id:
            raise UserError(_('The driver is already in this warehouse.'))

        self._send_decision(
            'ACTIVE', warehouse_odoo_id=warehouse.id,
            warehouse_change_only=True)

        assignment = self.env['recycle.driver.assignment'].sudo().search(
            [('backend_driver_id', '=', self.backend_driver_id)], limit=1)
        if assignment and assignment.truck_id.warehouse_id.id != warehouse.id:
            assignment.unlink()

        self.sudo().write({'warehouse_id': warehouse.id})
        return True

    def action_reject_image(self, image_id, reason=None):
        """Mark ONE document unacceptable — SILENTLY.

        The driver is not told and the request does not move. This used to do
        both: rejecting a document notified him and flipped the request to
        `need_changes` on the spot, so a reviewer could not work down four
        documents marking each one — the first rejection ended the review and
        sent the driver off to start fixing, before anybody had looked at the
        rest.

        Telling him is now `action_request_reupload`, which is a separate,
        deliberate act.
        """
        self.ensure_one()
        image = self._own_image(image_id)
        if self.state == 'accepted':
            # The documents are the evidence the acceptance rests on; re-marking
            # one afterwards rewrites the basis of a decision already acted on.
            raise UserError(_(
                'This request is already accepted — its documents can no longer '
                'be re-judged.'))
        if self.state == 'rejected':
            # Same reasoning in the other direction: the refusal has been sent,
            # so the grounds for it cannot move underneath it in silence.
            raise UserError(_(
                'This request is rejected — re-open it before judging its '
                'documents again.'))
        if image.status == 'rejected':
            return True
        image.write({'status': 'rejected'})
        # The mirror has to move too, or the backend will not let the driver
        # replace the file: its re-upload route accepts a REJECTED document and
        # nothing else. Sent WITHOUT a status change and without a notification.
        self._send_decision(
            'NEED_CHANGES',
            reason=(reason or '').strip() or None,
            rejected_media_ids=[image.backend_media_id],
            documents_only=True)
        return True

    def action_accept_image(self, image_id):
        """Mark a document acceptable — and tell the backend so.

        A reviewer who mis-clicks, or re-reads a scan and changes their mind,
        must be able to say so without involving the driver at all.

        The MIRROR has to move with it, and did not. Rejecting a document sent
        `documents_only` to the backend; accepting one wrote here and stopped —
        so the backend went on holding the document as REJECTED while this
        screen showed it accepted. Two consequences, both silent: the driver
        could still be asked to replace a document already accepted, and the
        acceptance gate on the backend side counted a rejection that no longer
        existed.
        """
        self.ensure_one()
        image = self._own_image(image_id)
        if self.state == 'accepted':
            raise UserError(_(
                'This request is already accepted — its documents can no longer '
                'be re-judged.'))
        if self.state == 'rejected':
            # A refusal has been taken and sent. Re-marking the evidence
            # underneath it changes what the driver was refused for, after he
            # was told — reconsidering is done in the open, by re-opening.
            raise UserError(_(
                'This request is rejected — re-open it before judging its '
                'documents again.'))
        if image.status == 'accepted':
            return True
        image.write({'status': 'accepted', 'reupload_requested': False})
        self._send_decision(
            'NEED_CHANGES',
            approved_media_ids=[image.backend_media_id],
            documents_only=True)
        return True

    def action_request_reupload(self, image_id, reason=None):
        """Ask the driver for ONE document again.

        The only act in this flow that reaches him. It requires the document to
        be REJECTED already, so "send this again" always follows a recorded
        judgement of what was wrong with it — a request with no rejection behind
        it is a reviewer asking for a document they never said anything about.

        It is also the way back into a REJECTED application: accepting one is
        blocked by the rejected document, and the document cannot be relabelled
        under a decided request. Asking for a replacement changes the facts
        rather than the paperwork.
        """
        self.ensure_one()
        image = self._own_image(image_id)
        if self.state == 'accepted':
            raise UserError(_(
                'This request is already accepted — there is nothing to ask for.'))
        if image.status != 'rejected':
            raise UserError(_(
                'Only a rejected document can be requested again — reject it '
                'first, so there is a recorded reason to give the driver.'))
        if image.reupload_requested:
            raise UserError(_(
                'This document has already been requested — the driver has not '
                'replaced it yet.'))

        reason = (reason or '').strip() or _(
            'Document "%s" was not accepted — please upload a clearer one.'
        ) % (image.file_type or '')
        self._send_decision(
            'NEED_CHANGES', reason=reason,
            rejected_media_ids=[image.backend_media_id],
            request_reupload=True)
        image.write({'reupload_requested': True})
        self.write({
            'state': 'need_changes',
            'rejection_reason': reason,
            'decided_at': fields.Datetime.now(),
        })
        return True

    def action_cancel_reupload_request(self, reason=None):
        """Stop waiting for a driver who never answered.

        Without this the flow had a state it could not leave. Asking for a
        document moves the request to `need_changes`; no decision may be taken
        in `need_changes`, because deciding then judges an application the
        reviewer has themselves called incomplete. So a driver who simply never
        comes back left the request open for ever, and the reviewer had no move
        at all — unable to accept it, reject it, or close it.

        Cancelling is NOT accepting. The documents keep the status they were
        given, so a rejected one stays rejected: what is withdrawn is the
        question, not the finding. The request therefore comes back to the
        queue where it can now be REJECTED (every document has been judged) and
        still cannot be ACCEPTED over a document marked unacceptable — which is
        the right pair of doors to leave open. Turning "I gave up waiting" into
        "I accept what you sent" would approve, silently, a document the
        reviewer had just called unacceptable.
        """
        self.ensure_one()
        asked = self.image_ids.filtered('reupload_requested')
        if not asked:
            raise UserError(_(
                'This driver has not been asked for any document, so there is '
                'nothing to cancel.'))
        # The backend holds the same record and releases the account off it, so
        # it has to be told — otherwise the driver stays in NEED_CHANGES there
        # while Odoo shows the request back under review.
        self._send_decision(
            'PENDING_APPROVAL',
            reason=(reason or '').strip() or None,
            rejected_media_ids=asked.mapped('backend_media_id'),
            cancel_reupload=True)
        asked.write({'reupload_requested': False})
        self.write({
            'state': 'pending',
            'rejection_reason': False,
        })
        return True

    def _own_image(self, image_id):
        image = self.image_ids.filtered(lambda i: i.id == int(image_id or 0))
        if not image:
            raise UserError(_('This document does not belong to the request.'))
        return image


class RecycleDriverRequestImage(models.Model):
    _name = 'recycle.driver.request.image'
    _description = 'Driver Request Document Image'
    _order = 'id'

    request_id = fields.Many2one(
        'recycle.driver.request', required=True, ondelete='cascade',
        index=True)
    backend_media_id = fields.Char(
        'Backend Media ID', required=True,
        help='UUID of the media row in the NestJS backend.')
    file_type = fields.Char('Document Type')   # e.g. LICENSE / ID_CARD_FRONT
    url = fields.Char('Image URL', required=True)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ], default='pending', required=True)

    reupload_requested = fields.Boolean(
        'Asked For Again', default=False,
        help='True once the driver has actually been ASKED to replace this '
             'document. A rejected document he was never told about is not '
             'the same thing, and only this decides when he is finished: '
             'counting rejections instead would hold him in "needs changes" '
             'over a file he cannot see and was never asked for.')
