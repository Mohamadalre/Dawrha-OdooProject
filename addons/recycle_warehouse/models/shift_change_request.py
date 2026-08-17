# -*- coding: utf-8 -*-
"""Driver shift-change requests, decided by the WAREHOUSE MANAGER.

Flow (the backend owns the DRIVER + the request row; Odoo owns the DECISION):
1. A driver with an ACTIVE account **and a truck** asks (in the app) to move
   to a different driver shift of his warehouse, with a mandatory reason.
   The backend pushes it here over JSON-RPC (``create`` — CONTRACT fields:
   backend_request_id, backend_driver_id, driver_name, shift_id (requested,
   this database's id), current_shift_id, reason, warehouse_odoo_id).
2. The manager sees it in his dashboard (Trucks → Shift Change Requests),
   newest first, filterable by state:
   - pending → "Start processing" (state sync to the backend);
   - processing → APPROVE: he picks one of HIS warehouse's in-service trucks
     that is still FREE in the requested shift → the driver's assignment
     MOVES to (that truck, that shift); or REJECT with a reason.
3. Every move is sent to the backend FIRST through the strict
   shift-change-decision webhook — unreachable backend = UserError and
   nothing is saved, so the two systems can never disagree.
4. The driver may cancel while still pending: the backend calls
   ``action_backend_cancel`` (idempotent) and deletes its row.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError

REQUEST_STATES = [
    ('pending', 'Pending'),
    ('processing', 'Processing'),
    ('accepted', 'Accepted'),
    ('rejected', 'Rejected'),
]


class RecycleShiftChangeRequest(models.Model):
    _name = 'recycle.shift.change.request'
    _description = 'Driver Shift Change Request (from backend)'
    _order = 'create_date desc'

    backend_request_id = fields.Char(
        'Backend Request ID', required=True, index=True,
        help='UUID of the request row in the NestJS backend.')
    backend_driver_id = fields.Char(
        'Backend Driver ID', required=True, index=True)
    driver_request_id = fields.Many2one(
        'recycle.driver.request', string='Driver', ondelete='set null',
        help='The accepted driver (roster row) this request belongs to.')
    driver_name = fields.Char('Driver Name')
    warehouse_id = fields.Many2one(
        'recycle.warehouse', string='Warehouse', index=True,
        ondelete='set null',
        help="The driver's warehouse — scopes the request to its manager.")
    current_shift_id = fields.Many2one(
        'recycle.shift', string='Current Shift', ondelete='set null')
    shift_id = fields.Many2one(
        'recycle.shift', string='Requested Shift', required=True,
        ondelete='restrict')
    reason = fields.Text('Reason', required=True)
    state = fields.Selection(
        REQUEST_STATES, default='pending', required=True, index=True)
    truck_id = fields.Many2one(
        'recycle.truck', string='Assigned Truck', ondelete='set null',
        help='The truck the manager reserved on approval.')
    rejection_reason = fields.Text('Rejection Reason')
    decided_at = fields.Datetime('Decided At', readonly=True)

    _backend_request_uniq = models.Constraint(
        'unique(backend_request_id)',
        'This shift-change request already exists.')

    # ------------------------------------------------------------------
    # Create (called by the backend over JSON-RPC)
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """UPSERT by backend_request_id.

        The backend re-pushes any request whose ``odoo_request_id`` is still
        empty (a push lost to an outage). A plain create would then hit the
        unique constraint and the request could never be recovered — so an
        existing row is refreshed instead, making re-pushes idempotent.
        """
        records = self.browse()
        for vals in vals_list:
            # warehouse_odoo_id is this database's warehouse id, sent raw by
            # the backend — resolve + drop the transport key.
            if 'warehouse_odoo_id' in vals:
                raw = vals.pop('warehouse_odoo_id')
                wh = self.env['recycle.warehouse'].sudo().browse(
                    int(raw or 0)).exists()
                vals.setdefault('warehouse_id', wh.id if wh else False)
            if vals.get('backend_driver_id'):
                roster = self.env['recycle.driver.request'].sudo().search(
                    [('backend_driver_id', '=', vals['backend_driver_id'])],
                    limit=1)
                if roster:
                    vals.setdefault('driver_request_id', roster.id)
                    vals.setdefault('driver_name', roster.name)
                    # Fall back to the roster's warehouse when the backend
                    # didn't know it (legacy drivers accepted before the
                    # warehouse started being mirrored).
                    if not vals.get('warehouse_id'):
                        vals['warehouse_id'] = roster.warehouse_id.id
            existing = self.browse()
            if vals.get('backend_request_id'):
                existing = self.search(
                    [('backend_request_id', '=', vals['backend_request_id'])],
                    limit=1)
            if existing:
                existing.write(vals)
                records |= existing
            else:
                records |= super().create([vals])
        return records

    # ------------------------------------------------------------------
    # Access scope (same actor rules as the assignment screen)
    # ------------------------------------------------------------------
    def _check_actor_scope(self):
        """Admin: any request. Manager: only requests of his warehouse."""
        self.ensure_one()
        is_admin, forced_wh = self.env[
            'recycle.driver.assignment']._assignment_actor_scope()
        if not is_admin and self.warehouse_id.id != forced_wh.id:
            raise UserError(_(
                'Only the manager of this request\'s warehouse can '
                'process it.'))

    # ------------------------------------------------------------------
    # STRICT state sync to the backend (fail = nothing saved)
    # ------------------------------------------------------------------
    def _send_status(self, status, truck=None, reason=None):
        self.ensure_one()
        ok = self.env['recycle.backend.sync'].sudo().notify_shift_change_status(
            self.backend_request_id, status,
            truck_odoo_id=truck.id if truck else None,
            reason=reason)
        if not ok:
            raise UserError(_(
                'Could not reach the Dawrha backend — the driver was NOT '
                'notified, so nothing was saved. Check the backend '
                'connection settings and try again.'))

    # ------------------------------------------------------------------
    # Manager actions
    # ------------------------------------------------------------------
    def action_start_processing(self):
        self.ensure_one()
        self._check_actor_scope()
        if self.state != 'pending':
            raise UserError(_('Only pending requests can start processing.'))
        self._send_status('PROCESSING')
        self.sudo().write({'state': 'processing'})
        return True

    def action_approve(self, truck_id):
        """Approve: reserve `truck_id` for the driver on the REQUESTED shift.
        The driver's existing assignment MOVES (he had a truck — that was a
        submission precondition backend-side); a truckless legacy driver
        simply gets a new assignment row."""
        self.ensure_one()
        self._check_actor_scope()
        if self.state != 'processing':
            raise UserError(_(
                'Start processing the request before approving it.'))

        truck = self.env['recycle.truck'].sudo().browse(
            int(truck_id or 0)).exists()
        if not truck or not truck.is_active:
            raise UserError(_('This truck is not available.'))
        if self.warehouse_id and truck.warehouse_id.id != self.warehouse_id.id:
            raise UserError(_(
                'Pick a truck of this request\'s warehouse.'))

        Assignment = self.env['recycle.driver.assignment'].sudo()
        taken = Assignment.search(
            [('truck_id', '=', truck.id), ('shift_id', '=', self.shift_id.id),
             ('backend_driver_id', '!=', self.backend_driver_id)], limit=1)
        if taken:
            raise UserError(_(
                'Truck "%s" is already reserved in that shift.') % truck.name)

        self._send_status('ACCEPTED', truck=truck)

        row = Assignment.search(
            [('backend_driver_id', '=', self.backend_driver_id)], limit=1)
        if row:
            row.write({'truck_id': truck.id, 'shift_id': self.shift_id.id})
        else:
            Assignment.create({
                'backend_driver_id': self.backend_driver_id,
                'truck_id': truck.id,
                'shift_id': self.shift_id.id,
            })
        if self.driver_request_id:
            self.driver_request_id.sudo().write(
                {'shift_id': self.shift_id.id})
        self.sudo().write({
            'state': 'accepted',
            'truck_id': truck.id,
            'rejection_reason': False,
            'decided_at': fields.Datetime.now(),
        })
        return True

    def action_reject(self, reason):
        self.ensure_one()
        self._check_actor_scope()
        if self.state != 'processing':
            raise UserError(_(
                'Start processing the request before rejecting it.'))
        reason = (reason or '').strip()
        if not reason:
            raise UserError(_('A rejection reason is required.'))
        self._send_status('REJECTED', reason=reason)
        self.sudo().write({
            'state': 'rejected',
            'rejection_reason': reason,
            'decided_at': fields.Datetime.now(),
        })
        return True

    # ------------------------------------------------------------------
    # Backend-initiated cancel (driver deleted his still-pending request)
    # ------------------------------------------------------------------
    @api.model
    def action_backend_cancel(self, backend_request_id):
        """Idempotent: unlink the mirror ONLY while still pending — a request
        the manager already moved keeps its history here."""
        rec = self.sudo().search(
            [('backend_request_id', '=', backend_request_id or '')], limit=1)
        if rec and rec.state == 'pending':
            rec.unlink()
        return True
