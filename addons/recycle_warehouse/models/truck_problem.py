# -*- coding: utf-8 -*-
"""Driver truck-problem reports, pushed from the NestJS backend.

The driver submits a mandatory reason + optional photos in the app; the
backend mirrors it here (``create`` over JSON-RPC — CONTRACT fields:
backend_problem_id, backend_driver_id, driver_name, reason, truck_odoo_id,
warehouse_odoo_id, image_ids[url]). The driver's WAREHOUSE MANAGER reads the
reports in his dashboard (Trucks → Truck Problems) — READ-ONLY, nothing
flows back to the backend.
"""
from odoo import api, fields, models, _


class RecycleTruckProblem(models.Model):
    _name = 'recycle.truck.problem'
    _description = 'Driver Truck Problem Report (from backend)'
    _order = 'create_date desc'

    backend_problem_id = fields.Char(
        'Backend Problem ID', required=True, index=True,
        help='UUID of the report row in the NestJS backend.')
    backend_driver_id = fields.Char('Backend Driver ID', index=True)
    driver_request_id = fields.Many2one(
        'recycle.driver.request', string='Driver', ondelete='set null')
    driver_name = fields.Char('Driver Name')
    warehouse_id = fields.Many2one(
        'recycle.warehouse', string='Warehouse', index=True,
        ondelete='set null',
        help="The driver's warehouse — scopes the report to its manager.")
    truck_id = fields.Many2one(
        'recycle.truck', string='Truck', ondelete='set null',
        help='The truck the driver was on when he reported the problem.')
    reason = fields.Text('Problem Description', required=True)
    image_ids = fields.One2many(
        'recycle.truck.problem.image', 'problem_id', string='Photos')

    _backend_problem_uniq = models.Constraint(
        'unique(backend_problem_id)',
        'This problem report already exists.')

    @api.model_create_multi
    def create(self, vals_list):
        Truck = self.env['recycle.truck'].sudo()
        WH = self.env['recycle.warehouse'].sudo()
        Roster = self.env['recycle.driver.request'].sudo()
        records = self.browse()   # everything the caller asked for
        created = self.browse()   # only the genuinely new rows (→ notify)
        for vals in vals_list:
            # truck_odoo_id / warehouse_odoo_id are this database's own ids,
            # sent raw by the backend — resolve + drop the transport keys.
            if 'truck_odoo_id' in vals:
                truck = Truck.browse(int(vals.pop('truck_odoo_id') or 0)).exists()
                vals.setdefault('truck_id', truck.id if truck else False)
            if 'warehouse_odoo_id' in vals:
                wh = WH.browse(int(vals.pop('warehouse_odoo_id') or 0)).exists()
                vals.setdefault('warehouse_id', wh.id if wh else False)
            if vals.get('backend_driver_id'):
                roster = Roster.search(
                    [('backend_driver_id', '=', vals['backend_driver_id'])],
                    limit=1)
                if roster:
                    vals.setdefault('driver_request_id', roster.id)
                    vals.setdefault('driver_name', roster.name)
                    if not vals.get('warehouse_id'):
                        vals['warehouse_id'] = roster.warehouse_id.id
                    # No truck sent (driver truckless when reporting): fall
                    # back to his current assignment if one exists.
                    if not vals.get('truck_id'):
                        asg = self.env['recycle.driver.assignment'].sudo().search(
                            [('backend_driver_id', '=',
                              vals['backend_driver_id'])], limit=1)
                        if asg:
                            vals['truck_id'] = asg.truck_id.id
            # UPSERT by backend_problem_id: the backend re-pushes any report
            # whose odoo_problem_id is still empty (a push lost to an outage).
            # A plain create would hit the unique constraint and the report
            # could never be recovered — the manager would never see it.
            existing = self.browse()
            if vals.get('backend_problem_id'):
                existing = self.search(
                    [('backend_problem_id', '=', vals['backend_problem_id'])],
                    limit=1)
            if existing:
                existing.write(vals)
                records |= existing
            else:
                new = super().create([vals])
                created |= new
                records |= new
        # Only genuinely NEW reports ping the manager — a recovery re-push must
        # never notify him twice about the same problem.
        created._notify_manager_new()
        return records

    def _notify_manager_new(self):
        """A driver reported a truck problem → notify his warehouse manager."""
        for rec in self:
            manager = rec.warehouse_id.manager_user_id
            if not manager:
                continue
            try:
                self.env['recycle.notification'].sudo()._notify_user(
                    manager,
                    _('New truck problem reported'),
                    _('%(driver)s reported a truck problem: %(reason)s') % {
                        'driver': rec.driver_name or _('A driver'),
                        'reason': (rec.reason or '')[:200]},
                    'shift_change')
            except Exception:
                pass


class RecycleTruckProblemImage(models.Model):
    _name = 'recycle.truck.problem.image'
    _description = 'Truck Problem Photo'
    _order = 'id'

    problem_id = fields.Many2one(
        'recycle.truck.problem', required=True, ondelete='cascade',
        index=True)
    url = fields.Char('Photo URL', required=True)
