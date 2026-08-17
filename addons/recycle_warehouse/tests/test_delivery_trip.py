# -*- coding: utf-8 -*-
"""The delivery trip as Odoo mirrors it: the driver's next stop, and custody.

The trip is planned in the backend and pushed here for the driver to run. Three
things are protected:

  * a re-push UPDATES the same trip and keeps any pickup the driver already
    confirmed — the time is Odoo's fact, and dropping it asks for the same
    warehouse to be collected twice;
  * the driver is given ONE stop at a time, farthest first, and cannot confirm
    one out of order — the route exists so the truck never doubles back;
  * every confirmation records WHO and WHEN, at the stop, not as a single flag
    on the trip.
"""
import base64
from odoo.exceptions import UserError
from .common import make_warehouse
from odoo.tests.common import TransactionCase, tagged

_IMG = base64.b64encode(b'fake-image-bytes')


@tagged('post_install', '-at_install')
class TestDeliveryTrip(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.wh_far = make_warehouse(cls.env, {'name': 'Trip Far', 'code': 'TF'})
        cls.wh_near = make_warehouse(cls.env, {'name': 'Trip Near', 'code': 'TN'})
        cls.Trip = cls.env['recycle.delivery.trip']

    def _payload(self, **over):
        vals = {
            'backend_trip_id': 'bt-1',
            'trip_number': 'TRIP-ORD-1',
            'order_number': 'ORD-1',
            'buyer_name': 'A Factory',
            'origin_warehouse_odoo_id': self.wh_far.id,
            'status': 'assigned',
            'route_distance_km': 50,
            'delivery_cost': 600,
            'dest_latitude': 31.95,
            'dest_longitude': 35.91,
            'stops': [
                {'backend_stop_id': 'bs-far', 'sequence': 1,
                 'warehouse_odoo_id': self.wh_far.id, 'part_ref': 'p-far',
                 'distance_to_buyer_km': 40, 'latitude': 32.1, 'longitude': 36.0},
                {'backend_stop_id': 'bs-near', 'sequence': 2,
                 'warehouse_odoo_id': self.wh_near.id, 'part_ref': 'p-near',
                 'distance_to_buyer_km': 10, 'latitude': 31.99, 'longitude': 35.95},
            ],
        }
        vals.update(over)
        return vals

    # ------------------------------------------------------------------
    def test_backend_upsert_creates_the_trip_and_its_stops(self):
        res = self.Trip.backend_upsert(self._payload())
        trip = self.Trip.browse(res['id'])
        self.assertEqual(trip.backend_trip_id, 'bt-1')
        self.assertEqual(len(trip.stop_ids), 2)
        self.assertEqual(trip.origin_warehouse_id, self.wh_far)
        # Map links are built for stops and destination.
        self.assertIn('google.com/maps', trip.dest_maps_url)
        self.assertIn('google.com/maps', trip.stop_ids.sorted('sequence')[0].maps_url)

    def test_re_push_updates_the_same_trip(self):
        self.Trip.backend_upsert(self._payload())
        self.Trip.backend_upsert(self._payload(delivery_cost=999))
        trips = self.Trip.search([('backend_trip_id', '=', 'bt-1')])
        self.assertEqual(len(trips), 1)
        self.assertEqual(trips.delivery_cost, 999)

    def test_next_stop_is_the_farthest_uncollected(self):
        trip = self.Trip.browse(self.Trip.backend_upsert(self._payload())['id'])
        self.assertEqual(trip.next_stop().backend_stop_id, 'bs-far')

    def test_driver_confirms_in_order_and_time_is_recorded(self):
        trip = self.Trip.browse(self.Trip.backend_upsert(self._payload())['id'])

        trip.action_driver_confirm_pickup('bs-far')
        far = trip.stop_ids.filtered(lambda s: s.backend_stop_id == 'bs-far')
        self.assertTrue(far.picked_up_at)
        self.assertTrue(far.is_collected)
        self.assertEqual(trip.status, 'in_progress')
        # Next stop advanced to the nearer one.
        self.assertEqual(trip.next_stop().backend_stop_id, 'bs-near')

    def test_a_stop_cannot_be_collected_out_of_order(self):
        trip = self.Trip.browse(self.Trip.backend_upsert(self._payload())['id'])
        with self.assertRaises(UserError):
            trip.action_driver_confirm_pickup('bs-near')  # far is still first

    def test_a_re_push_keeps_a_confirmed_pickup(self):
        trip = self.Trip.browse(self.Trip.backend_upsert(self._payload())['id'])
        trip.action_driver_confirm_pickup('bs-far')

        # The backend re-pushes (say, a cost edit); the pickup must survive.
        self.Trip.backend_upsert(self._payload(delivery_cost=777))
        trip = self.Trip.search([('backend_trip_id', '=', 'bt-1')])
        far = trip.stop_ids.filtered(lambda s: s.backend_stop_id == 'bs-far')
        self.assertTrue(far.picked_up_at, 'a confirmed pickup must survive a re-push')

    def test_driver_cannot_complete_with_outstanding_stops(self):
        trip = self.Trip.browse(self.Trip.backend_upsert(self._payload())['id'])
        trip.action_driver_confirm_pickup('bs-far')  # near still outstanding
        with self.assertRaises(UserError):
            trip.action_driver_complete()

    def test_driver_completes_once_everything_is_collected(self):
        trip = self.Trip.browse(self.Trip.backend_upsert(self._payload())['id'])
        trip.action_driver_confirm_pickup('bs-far')
        trip.action_driver_confirm_pickup('bs-near')
        trip.action_driver_complete()
        self.assertEqual(trip.status, 'completed')

    def test_notify_complaint_reaches_the_manager(self):
        mgr = self.env['res.users'].create({
            'name': 'Complaint Mgr', 'login': 'complaint.mgr@example.com'})
        self.wh_far.manager_user_id = mgr.id
        Notif = self.env['recycle.notification']
        before = Notif.search_count([('recipient_user_id', '=', mgr.id)])

        res = self.env['recycle.warehouse'].notify_complaint(
            self.wh_far.id, 'SHORTAGE', 'Missing 10 kg of PET', 'ORD-9')

        self.assertTrue(res['notified'])
        self.assertEqual(
            Notif.search_count([('recipient_user_id', '=', mgr.id)]), before + 1)

    def test_notify_complaint_without_a_manager_is_not_an_error(self):
        self.wh_near.manager_user_id = False
        res = self.env['recycle.warehouse'].notify_complaint(
            self.wh_near.id, 'QUALITY', 'Wrong grade', 'ORD-10')
        self.assertFalse(res['notified'])

    def test_backend_driver_for_truck(self):
        Truck = self.env['recycle.truck']
        truck = Truck.create({
            'name': 'DTruck', 'plate_number': 'DT-1', 'model': 'X', 'year': 2022,
            'truck_type': 'delivery', 'warehouse_id': self.wh_far.id,
        })
        driver = self.env['recycle.delivery.driver'].create({
            'name': 'Sami', 'phone': '0790000000', 'national_id': 'ND-1',
            'warehouse_id': self.wh_far.id, 'truck_id': truck.id,
            'license_image_front': _IMG, 'license_image_back': _IMG,
        })
        info = self.env['recycle.delivery.driver'].backend_driver_for_truck(truck.id)
        self.assertEqual(info['driver_id'], driver.id)
        self.assertEqual(info['name'], 'Sami')
        # No driver on an unknown truck → empty, not an error.
        self.assertEqual(
            self.env['recycle.delivery.driver'].backend_driver_for_truck(999999), {})
