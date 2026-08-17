# -*- coding: utf-8 -*-
"""Truck handover (pickup / dropoff) sessions, pushed from the NestJS backend.

The driver presses "Pick up" / "Hand over" in the app (guarded by his shift
window there); the backend authors the session and mirrors it here so the
warehouse MANAGER reads it in his READ-ONLY "Driver Attendance" screen. Nothing
flows back to the backend from this model.

CONTRACT (create on pickup): backend_handover_id, backend_driver_id,
driver_name, truck_odoo_id, shift_odoo_id, warehouse_odoo_id, work_date,
picked_up_at. Dropoff calls ``backend_close``; the missed-pickup / late-dropoff
manager alerts call ``backend_alert_manager``.
"""
from odoo import api, fields, models, _

HANDOVER_STATES = [
    ('open', 'Holding'),
    ('closed', 'Handed Over'),
    ('missed_pickup', 'Missed Pickup'),
]


class RecycleTruckHandover(models.Model):
    _name = 'recycle.truck.handover'
    _description = 'Driver Truck Handover (from backend)'
    _order = 'picked_up_at desc, create_date desc'

    backend_handover_id = fields.Char(
        'Backend Handover ID', required=True, index=True,
        help='UUID of the handover row in the NestJS backend.')
    backend_driver_id = fields.Char('Backend Driver ID', index=True)
    driver_request_id = fields.Many2one(
        'recycle.driver.request', string='Driver', ondelete='set null')
    driver_name = fields.Char('Driver Name')
    truck_id = fields.Many2one(
        'recycle.truck', string='Truck', ondelete='set null')
    shift_id = fields.Many2one(
        'recycle.shift', string='Shift', ondelete='set null')
    warehouse_id = fields.Many2one(
        'recycle.warehouse', string='Warehouse', index=True,
        ondelete='set null',
        help="The driver's warehouse — scopes the row to its manager.")
    work_date = fields.Date('Date')
    picked_up_at = fields.Datetime('Picked Up At')
    dropped_off_at = fields.Datetime('Handed Over At')
    dropoff_reason = fields.Text('Truck Note (at handover)')
    late_minutes = fields.Integer('Late Handover (min)', default=0)
    state = fields.Selection(
        HANDOVER_STATES, default='open', required=True, index=True)

    _backend_handover_uniq = models.Constraint(
        'unique(backend_handover_id)',
        'This handover already exists.')

    # ------------------------------------------------------------------
    # Create (backend PICKUP) — resolve the raw *_odoo_id transport keys
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        Truck = self.env['recycle.truck'].sudo()
        Shift = self.env['recycle.shift'].sudo()
        WH = self.env['recycle.warehouse'].sudo()
        Roster = self.env['recycle.driver.request'].sudo()
        records = self.browse()
        for vals in vals_list:
            if 'truck_odoo_id' in vals:
                t = Truck.browse(int(vals.pop('truck_odoo_id') or 0)).exists()
                vals.setdefault('truck_id', t.id if t else False)
            if 'shift_odoo_id' in vals:
                s = Shift.browse(int(vals.pop('shift_odoo_id') or 0)).exists()
                vals.setdefault('shift_id', s.id if s else False)
            if 'warehouse_odoo_id' in vals:
                w = WH.browse(int(vals.pop('warehouse_odoo_id') or 0)).exists()
                vals.setdefault('warehouse_id', w.id if w else False)
            if vals.get('backend_driver_id'):
                roster = Roster.search(
                    [('backend_driver_id', '=', vals['backend_driver_id'])],
                    limit=1)
                if roster:
                    vals.setdefault('driver_request_id', roster.id)
                    vals.setdefault('driver_name', roster.name)
                    if not vals.get('warehouse_id'):
                        vals['warehouse_id'] = roster.warehouse_id.id
            # UPSERT by backend_handover_id: the backend re-pushes any custody
            # session whose odoo_handover_id is still empty (a push lost to an
            # outage). Without this the unique constraint would make a lost
            # pickup unrecoverable and it would vanish from Driver Attendance.
            existing = self.browse()
            if vals.get('backend_handover_id'):
                existing = self.search(
                    [('backend_handover_id', '=', vals['backend_handover_id'])],
                    limit=1)
            if existing:
                existing.write(vals)
                records |= existing
            else:
                records |= super().create([vals])
        return records

    # ------------------------------------------------------------------
    # Backend DROPOFF — close the row (idempotent by backend id)
    # ------------------------------------------------------------------
    @api.model
    def backend_close(self, backend_handover_id, dropped_off_at,
                      dropoff_reason=False, late_minutes=0):
        rec = self.sudo().search(
            [('backend_handover_id', '=', backend_handover_id or '')], limit=1)
        if rec:
            rec.write({
                'state': 'closed',
                'dropped_off_at': dropped_off_at or False,
                'dropoff_reason': dropoff_reason or False,
                'late_minutes': int(late_minutes or 0),
            })
            # If the truck's warehouse started closing while the driver still
            # held it, this hand-back is the moment it can finally be freed for
            # another warehouse.
            try:
                self.env['recycle.warehouse'].sudo()._unassign_if_warehouse_closing(
                    rec.truck_id)
            except Exception:
                pass
        return True

    # ------------------------------------------------------------------
    # Backend ALERT — notify the driver's warehouse manager (missed / late)
    # ------------------------------------------------------------------
    @api.model
    def backend_alert_manager(self, backend_driver_id, kind, shift_name,
                              late_minutes=0):
        """Called by the backend cron. The DRIVER is already notified over FCM
        by the backend; this creates the Odoo notification for his warehouse
        manager only. Fire-and-forget (returns True even if no manager)."""
        roster = self.env['recycle.driver.request'].sudo().search(
            [('backend_driver_id', '=', backend_driver_id or '')], limit=1)
        manager = roster.warehouse_id.manager_user_id if roster else False
        if not manager:
            return True
        driver = roster.name or _('A driver')
        if kind == 'MISSED_PICKUP':
            title = _('Driver has not picked up his truck')
            msg = _('%(driver)s has not picked up his truck for shift '
                    '"%(shift)s".') % {'driver': driver, 'shift': shift_name}
        else:
            title = _('Driver has not handed his truck back')
            msg = _('%(driver)s has not handed his truck back — shift '
                    '"%(shift)s" ended %(min)s minute(s) ago.') % {
                        'driver': driver, 'shift': shift_name,
                        'min': int(late_minutes or 0)}
        self.env['recycle.notification'].sudo()._notify_user(
            manager, title, msg, 'shift_change')
        return True
