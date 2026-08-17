# -*- coding: utf-8 -*-
"""Who held which truck, and when.

A truck moves between drivers: someone is given it, someone hands it back, a
warehouse change releases it, a driver is blocked. Each of those is a fact with
a date, and until now none of them left anything behind — the only thing stored
was the CURRENT holder, so "who had this van in March?" had no answer at all.

That question is not idle. It is the first one asked after an accident, a fuel
discrepancy, a damaged vehicle or a complaint about a delivery, and a system
that cannot answer it makes the honest driver and the careless one look the
same.

So every hand-over writes a row here, and rows are never edited: a period that
can be rewritten afterwards proves nothing. An open row (`released_at` empty) is
the current holder; closing it is what "handed back" means.

Both kinds of driver share this table on purpose. A collector and a delivery
driver are different records in different tables, but "who had the truck" is one
question, and answering it from two places would mean two reports that never
quite agree.
"""
from odoo import api, fields, models, _

DRIVER_KINDS = [
    ('collection', 'Collection Driver'),
    ('delivery', 'Delivery Driver'),
]

RELEASE_REASONS = [
    ('manual', 'Unassigned by an administrator or manager'),
    ('warehouse_change', 'Truck moved to another warehouse'),
    ('reassigned', 'Given to another driver'),
    ('driver_blocked', 'Driver blocked'),
    ('driver_removed', 'Driver record removed or deactivated'),
]


class RecycleTruckAssignmentHistory(models.Model):
    _name = 'recycle.truck.assignment.history'
    _description = 'Truck Holding History'
    _order = 'assigned_at desc, id desc'

    truck_id = fields.Many2one(
        'recycle.truck', string='Truck', required=True, index=True,
        ondelete='cascade')
    truck_plate = fields.Char(
        string='Plate', related='truck_id.plate_number', store=True,
        readonly=True)
    truck_type = fields.Selection(
        related='truck_id.truck_type', store=True, readonly=True,
        string='Truck Job')
    warehouse_id = fields.Many2one(
        'recycle.warehouse', string='Warehouse', index=True, ondelete='set null')

    driver_kind = fields.Selection(
        DRIVER_KINDS, string='Driver Type', required=True, index=True)
    # The two kinds live in different tables, so the link is kept twice and the
    # NAME is snapshotted. A report about last year must still read correctly
    # after a driver record is renamed or removed.
    delivery_driver_id = fields.Many2one(
        'recycle.delivery.driver', string='Delivery Driver',
        ondelete='set null', index=True)
    driver_request_id = fields.Many2one(
        'recycle.driver.request', string='Collection Driver',
        ondelete='set null', index=True)
    driver_name = fields.Char(string='Driver', required=True)
    driver_national_id = fields.Char(string='National ID')

    assigned_at = fields.Datetime(
        string='Held From', required=True, index=True,
        default=fields.Datetime.now)
    released_at = fields.Datetime(
        string='Held Until', index=True,
        help='Empty means the driver still holds this truck.')
    release_reason = fields.Selection(RELEASE_REASONS, string='Released Because')
    assigned_by = fields.Many2one('res.users', string='Assigned By')
    released_by = fields.Many2one('res.users', string='Released By')

    is_current = fields.Boolean(
        string='Currently Held', compute='_compute_is_current', store=True,
        help='Stored so "who holds what right now" is an indexed lookup rather '
             'than a scan of the whole history.')
    duration_days = fields.Float(
        string='Days Held', compute='_compute_duration', store=True)

    @api.depends('released_at')
    def _compute_is_current(self):
        for rec in self:
            rec.is_current = not rec.released_at

    @api.depends('assigned_at', 'released_at')
    def _compute_duration(self):
        now = fields.Datetime.now()
        for rec in self:
            if not rec.assigned_at:
                rec.duration_days = 0.0
                continue
            end = rec.released_at or now
            rec.duration_days = round(
                (end - rec.assigned_at).total_seconds() / 86400.0, 2)

    # ------------------------------------------------------------------
    # Append-only
    # ------------------------------------------------------------------
    def write(self, vals):
        """Only the CLOSING of a period may be written.

        Everything else is a fact that already happened. A history whose dates
        and drivers can be edited afterwards answers the question it exists for
        with whatever the last editor preferred.
        """
        closing = {'released_at', 'release_reason', 'released_by'}
        touched = set(vals) - closing
        if touched:
            from odoo.exceptions import UserError
            raise UserError(_(
                'Truck history cannot be edited (%s). It records what already '
                'happened; only the end of a holding period may be filled in.'
            ) % ', '.join(sorted(touched)))
        return super().write(vals)

    def unlink(self):
        from odoo.exceptions import UserError
        raise UserError(_(
            'Truck history cannot be deleted — it is what the driver and '
            'vehicle reports are built from.'))

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------
    @api.model
    def open_period(self, truck, kind, delivery_driver=None, driver_request=None):
        """Start a holding period, closing any other open one for that truck.

        Closing first matters: two open rows for one truck would mean two people
        holding one vehicle, which is exactly the confusion this table exists to
        remove.
        """
        if not truck:
            return self.browse()

        self.close_open_periods(truck, reason='reassigned')

        if kind == 'delivery' and delivery_driver:
            name = delivery_driver.name
            nid = delivery_driver.national_id
        elif driver_request:
            name = driver_request.name
            nid = getattr(driver_request, 'national_id', False)
        else:
            return self.browse()

        return self.sudo().create({
            'truck_id': truck.id,
            'warehouse_id': truck.warehouse_id.id or False,
            'driver_kind': kind,
            'delivery_driver_id': delivery_driver.id if delivery_driver else False,
            'driver_request_id': driver_request.id if driver_request else False,
            'driver_name': name or _('Unknown'),
            'driver_national_id': nid or False,
            'assigned_at': fields.Datetime.now(),
            'assigned_by': self.env.uid,
        })

    @api.model
    def close_open_periods(self, truck, reason='manual', delivery_driver=None,
                           driver_request=None):
        """End the open period(s) for a truck — or for one driver's hold on it."""
        domain = [('truck_id', '=', truck.id), ('released_at', '=', False)]
        if delivery_driver:
            domain.append(('delivery_driver_id', '=', delivery_driver.id))
        if driver_request:
            domain.append(('driver_request_id', '=', driver_request.id))
        rows = self.sudo().search(domain)
        if rows:
            rows.write({
                'released_at': fields.Datetime.now(),
                'release_reason': reason,
                'released_by': self.env.uid,
            })
        return rows

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    @api.model
    def driver_report(self, driver_kind=None, warehouse_id=None,
                      date_from=None, date_to=None):
        """Flat rows for the driver/vehicle export.

        Returns plain dicts rather than records so the same shape feeds the
        dashboard table, the CSV download and any later PDF without three
        different readings of the same data.
        """
        domain = []
        if driver_kind:
            domain.append(('driver_kind', '=', driver_kind))
        if warehouse_id:
            domain.append(('warehouse_id', '=', int(warehouse_id)))
        if date_from:
            domain.append(('assigned_at', '>=', date_from))
        if date_to:
            domain.append(('assigned_at', '<=', date_to))

        rows = self.sudo().search(domain, order='driver_name, assigned_at desc')
        return [{
            'id': r.id,
            'driver_kind': r.driver_kind,
            'driver_name': r.driver_name,
            'driver_national_id': r.driver_national_id or '',
            'warehouse': r.warehouse_id.name or '',
            'truck': r.truck_id.name or '',
            'truck_plate': r.truck_plate or '',
            'truck_type': r.truck_type or '',
            'assigned_at': fields.Datetime.to_string(r.assigned_at) or '',
            'released_at': fields.Datetime.to_string(r.released_at) or '',
            'release_reason': r.release_reason or '',
            'duration_days': r.duration_days,
            'is_current': r.is_current,
            'assigned_by': r.assigned_by.name or '',
            'released_by': r.released_by.name or '',
        } for r in rows]
