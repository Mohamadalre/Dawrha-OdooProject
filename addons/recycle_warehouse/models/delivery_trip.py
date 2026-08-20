# -*- coding: utf-8 -*-
"""A delivery trip, as the DRIVER and the ADMIN see it in Odoo.

The trip itself is planned and costed in the NestJS backend — that is where the
order, the split and the fleet score live. What Odoo needs is a MIRROR the
delivery driver can act on: their truck, their route, and a button to confirm
each pickup. So the backend pushes the trip here when it dispatches, and every
confirmation the driver makes is reported straight back.

TWO THINGS ARE DELIBERATE.

The driver is shown ONE stop at a time — the next uncollected warehouse — not
the whole route. A milk run has an order to it (farthest warehouse first, so the
truck never doubles back), and a driver looking at five stops at once is a
driver who collects them in the wrong sequence. The next stop opens only when
the one before it is done.

And custody is recorded at the STOP, with its time. "Who had this part when it
went missing" is answered by a row with a driver, a warehouse and a timestamp —
never by a single status on the trip, which cannot say that half the load is
aboard and half is still on a floor.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


TRIP_STATUSES = [
    ('assigned', 'Assigned'),
    ('in_progress', 'In Progress'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
]


class RecycleDeliveryTrip(models.Model):
    _name = 'recycle.delivery.trip'
    _description = 'Delivery Trip'
    _inherit = ['mail.thread']
    _order = 'create_date desc'
    _rec_name = 'trip_number'

    # The backend's trip id — the key every push and every report matches on, so
    # a re-push updates the same trip instead of making a second.
    backend_trip_id = fields.Char(
        string='Backend Trip', required=True, index=True, copy=False)
    trip_number = fields.Char(string='Trip Number', required=True, index=True)
    order_number = fields.Char(string='Order')
    # The order's backend UUID — matches recycle.order.backend_order_id, so an
    # order can read the delivery cost of its own trip.
    backend_order_id = fields.Char(string='Backend Order', index=True)
    buyer_name = fields.Char(string='Buyer')

    origin_warehouse_id = fields.Many2one(
        'recycle.warehouse', string='Starts At', ondelete='set null')
    truck_id = fields.Many2one(
        'recycle.truck', string='Truck', ondelete='set null')
    driver_id = fields.Many2one(
        'recycle.delivery.driver', string='Driver', index=True,
        ondelete='set null')

    status = fields.Selection(
        TRIP_STATUSES, string='Status', default='assigned', required=True,
        index=True, tracking=True)

    # Stamped the instant a trip is delivered — the honest "when did this finish"
    # a monthly count needs. `write_date` would drift on any later edit; this
    # does not move once set.
    completed_at = fields.Datetime(string='Completed At', copy=False, readonly=True)

    route_distance_km = fields.Float(string='Route Distance (km)')
    delivery_cost = fields.Float(string='Delivery Cost')
    currency_code = fields.Char(string='Currency', default='SYP')

    # The buyer's yard — where every trip ends. Kept as plain coordinates (the
    # buyer is a backend entity Odoo does not otherwise hold) so the last leg
    # gets a map pin like every warehouse stop.
    dest_latitude = fields.Float(string='Destination Latitude', digits=(10, 7))
    dest_longitude = fields.Float(string='Destination Longitude', digits=(10, 7))
    dest_maps_url = fields.Char(
        string='Destination Map', compute='_compute_dest_maps_url')

    stop_ids = fields.One2many(
        'recycle.delivery.trip.stop', 'trip_id', string='Stops')

    _backend_trip_uniq = models.Constraint(
        'unique(backend_trip_id)',
        'This delivery trip already exists.')

    @api.depends('dest_latitude', 'dest_longitude')
    def _compute_dest_maps_url(self):
        for rec in self:
            rec.dest_maps_url = _maps_url(rec.dest_latitude, rec.dest_longitude)

    # ------------------------------------------------------------------
    # Received from the backend
    # ------------------------------------------------------------------
    @api.model
    def backend_upsert(self, payload):
        """Create or refresh a trip pushed from the backend.

        Idempotent on `backend_trip_id`: dispatched once and re-pushed after an
        edit both land on the same record. The stops are REPLACED wholesale
        rather than diffed — the backend owns the route, the list is short, and
        a replace cannot leave a stale stop behind that a diff might.

        A pickup a driver already confirmed here is preserved across a re-push:
        its time is the one fact Odoo owns, not the backend, and dropping it
        would ask the driver to collect the same warehouse twice.
        """
        backend_trip_id = payload.get('backend_trip_id')
        if not backend_trip_id:
            raise UserError(_('A delivery trip push needs a backend trip id.'))

        trip = self.sudo().search(
            [('backend_trip_id', '=', backend_trip_id)], limit=1)
        vals = {
            'backend_trip_id': backend_trip_id,
            'trip_number': payload.get('trip_number') or backend_trip_id,
            'order_number': payload.get('order_number') or '',
            'backend_order_id': payload.get('backend_order_id') or '',
            'buyer_name': payload.get('buyer_name') or '',
            'origin_warehouse_id': self._warehouse(payload.get('origin_warehouse_odoo_id')),
            'truck_id': self._truck(payload.get('truck_odoo_id')),
            'driver_id': int(payload['driver_odoo_id']) if payload.get('driver_odoo_id') else False,
            'status': payload.get('status') or 'assigned',
            'route_distance_km': float(payload.get('route_distance_km') or 0),
            'delivery_cost': float(payload.get('delivery_cost') or 0),
            'currency_code': payload.get('currency') or 'SYP',
            'dest_latitude': float(payload.get('dest_latitude') or 0),
            'dest_longitude': float(payload.get('dest_longitude') or 0),
        }
        is_new = not trip
        if trip:
            trip.write(vals)
        else:
            trip = self.sudo().create(vals)

        # Preserve pickups the driver already confirmed, keyed by backend stop id.
        already = {
            s.backend_stop_id: s.picked_up_at
            for s in trip.stop_ids if s.picked_up_at
        }
        trip.stop_ids.unlink()
        Stop = self.env['recycle.delivery.trip.stop'].sudo()
        for raw in payload.get('stops') or []:
            bsid = raw.get('backend_stop_id')
            Stop.create({
                'trip_id': trip.id,
                'backend_stop_id': bsid,
                'sequence': int(raw.get('sequence') or 1),
                'warehouse_id': self._warehouse(raw.get('warehouse_odoo_id')),
                'part_ref': raw.get('part_ref') or '',
                'product_summary': raw.get('product_summary') or '',
                'distance_to_buyer_km': float(raw.get('distance_to_buyer_km') or 0),
                'latitude': float(raw.get('latitude') or 0),
                'longitude': float(raw.get('longitude') or 0),
                'picked_up_at': raw.get('picked_up_at') or already.get(bsid) or False,
            })

        # Tell the driver they have a run — once, when the trip first arrives.
        if is_new and trip.driver_id and trip.driver_id.user_id:
            self.env['recycle.notification'].sudo()._notify_user(
                trip.driver_id.user_id,
                _('New delivery trip'),
                _('Trip %(trip)s — %(count)s stop(s), ending at %(buyer)s.') % {
                    'trip': trip.trip_number,
                    'count': len(trip.stop_ids),
                    'buyer': trip.buyer_name or _('the buyer'),
                },
                notif_type='delivery_trip',
            )
        return {'ok': True, 'id': trip.id, 'trip_number': trip.trip_number}

    def _warehouse(self, odoo_id):
        if not odoo_id:
            return False
        wh = self.env['recycle.warehouse'].sudo().browse(int(odoo_id))
        return wh.id if wh.exists() else False

    def _truck(self, odoo_id):
        if not odoo_id:
            return False
        t = self.env['recycle.truck'].sudo().browse(int(odoo_id))
        return t.id if t.exists() else False

    # ------------------------------------------------------------------
    # Driver actions
    # ------------------------------------------------------------------
    def next_stop(self):
        """The one station the driver should drive to now: the nearest-in-
        sequence stop not yet collected. None means the load is complete."""
        self.ensure_one()
        pending = self.stop_ids.sorted('sequence').filtered(
            lambda s: not s.picked_up_at)
        return pending[:1]

    def action_driver_confirm_pickup(self, backend_stop_id=None):
        """The DRIVER confirms taking one warehouse's goods, and the time is
        recorded. Refused out of order: the route runs farthest warehouse first
        so the truck never doubles back, and a stop reported before the one
        ahead of it means the wrong button was pressed.

        The backend is told at once — it owns the order the buyer is watching,
        and the part does not move to DISPATCHED there until this lands.
        """
        self.ensure_one()
        if self.status not in ('assigned', 'in_progress'):
            raise UserError(_('This trip is not out for delivery.'))

        stop = self.next_stop()
        if not stop:
            raise UserError(_('Every stop on this trip is already collected.'))
        if backend_stop_id and stop.backend_stop_id != backend_stop_id:
            raise UserError(_(
                'That is not the next stop. Collect stop %s first.'
            ) % stop.sequence)

        stop.picked_up_at = fields.Datetime.now()
        if self.status == 'assigned':
            self.status = 'in_progress'
        self.message_post(body=_('Stop %(seq)s collected by %(who)s.') % {
            'seq': stop.sequence, 'who': self.env.user.name})
        self._notify_backend('picked_up', stop)
        return {'ok': True, 'stop_id': stop.id, 'sequence': stop.sequence,
                'remaining': len(self.stop_ids.filtered(lambda s: not s.picked_up_at))}

    def action_driver_complete(self):
        """The driver hands the whole load to the buyer at the last stop.

        Refused while any warehouse is still outstanding — arriving with a
        partial load and closing the trip would strand the rest. This does NOT
        complete the buyer's order: the backend marks the goods delivered and
        the BUYER confirms receipt themselves, which is the second signature on
        the same handover.
        """
        self.ensure_one()
        if self.status not in ('assigned', 'in_progress'):
            raise UserError(_('This trip is not out for delivery.'))
        outstanding = self.stop_ids.filtered(lambda s: not s.picked_up_at)
        if outstanding:
            raise UserError(_(
                '%s stop(s) have not been collected — the load is incomplete.'
            ) % len(outstanding))
        self.status = 'completed'
        self.completed_at = fields.Datetime.now()
        self.message_post(body=_('Delivered to the buyer by %s.')
                          % self.env.user.name)
        self._notify_backend('completed')
        return {'ok': True}

    def _notify_backend(self, event, stop=None):
        """Report a delivery event to the backend. Swallows failure like the
        order channel — a driver's confirmation must never be blocked because
        the backend is briefly unreachable — and the backend's own 10-minute
        reconcile re-reads anything a dropped call lost."""
        self.ensure_one()
        try:
            self.env['recycle.backend.sync'].sudo().sync_delivery(self, event, stop)
        except Exception:
            pass


class RecycleDeliveryTripStop(models.Model):
    _name = 'recycle.delivery.trip.stop'
    _description = 'Delivery Trip Stop'
    _order = 'sequence'

    trip_id = fields.Many2one(
        'recycle.delivery.trip', string='Trip', required=True,
        ondelete='cascade', index=True)
    backend_stop_id = fields.Char(string='Backend Stop', index=True)
    sequence = fields.Integer(string='Sequence', default=1)
    warehouse_id = fields.Many2one(
        'recycle.warehouse', string='Warehouse', ondelete='set null')
    part_ref = fields.Char(string='Order Part')
    product_summary = fields.Char(string='Goods')
    distance_to_buyer_km = fields.Float(string='Distance to Buyer (km)')

    latitude = fields.Float(string='Latitude', digits=(10, 7))
    longitude = fields.Float(string='Longitude', digits=(10, 7))
    maps_url = fields.Char(string='Map', compute='_compute_maps_url')

    picked_up_at = fields.Datetime(string='Collected At', copy=False)
    is_collected = fields.Boolean(
        string='Collected', compute='_compute_is_collected', store=True)

    @api.depends('picked_up_at')
    def _compute_is_collected(self):
        for rec in self:
            rec.is_collected = bool(rec.picked_up_at)

    @api.depends('latitude', 'longitude')
    def _compute_maps_url(self):
        for rec in self:
            rec.maps_url = _maps_url(rec.latitude, rec.longitude)


def _maps_url(lat, lng):
    """A Google Maps link that drops a pin on the point. Empty coordinates
    (a stop pushed before its warehouse had any) yield no link rather than a
    pin in the Atlantic at 0,0."""
    if not lat and not lng:
        return False
    return 'https://www.google.com/maps/search/?api=1&query=%s,%s' % (lat, lng)
