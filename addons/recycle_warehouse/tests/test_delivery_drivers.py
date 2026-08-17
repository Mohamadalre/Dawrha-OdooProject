# -*- coding: utf-8 -*-
"""Two kinds of driver, two kinds of truck, and the line between them.

The fleet does two unrelated jobs:

  COLLECTION — a truck goes out to citizens and picks material up. It is driven
               by a COLLECTOR, whose account lives in the NestJS backend and who
               works a shift.
  DELIVERY   — a truck carries sold goods from a warehouse to the buyer. It is
               driven by a DELIVERY DRIVER, recruited here, with no backend
               account and no shift at all.

Before the split they were one pool, so a collector could be booked onto a truck
that never goes near a collection round — and the mistake only surfaced as a
driver standing next to the wrong vehicle. These tests hold the two apart at
every door: the model constraint, the picker that offers the choice, and the
action that commits it. A rule enforced in only one of the three is a rule the
other two paths do not have.
"""
import base64

from odoo.exceptions import UserError, ValidationError
from .common import make_warehouse
from odoo.tests.common import TransactionCase, tagged

# Odoo Binary fields hold base64, not raw bytes — an unencoded value fails deep
# inside ir.attachment with "Incorrect padding" rather than at the field.
FRONT = base64.b64encode(b'licence-front').decode()
BACK = base64.b64encode(b'licence-back').decode()


@tagged('post_install', '-at_install')
class TestDeliveryDrivers(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = make_warehouse(cls.env, **{
            'name': 'Delivery Test Warehouse', 'code': 'DTW1',
        })
        cls.other_warehouse = make_warehouse(cls.env, **{
            'name': 'Other Warehouse', 'code': 'DTW2',
        })
        cls.collection_truck = cls.env['recycle.truck'].create({
            'name': 'Collector 1', 'plate_number': 'COL-001',
            'truck_type': 'collection', 'warehouse_id': cls.warehouse.id,
        })
        cls.delivery_truck = cls.env['recycle.truck'].create({
            'name': 'Deliverer 1', 'plate_number': 'DEL-001',
            'truck_type': 'delivery', 'warehouse_id': cls.warehouse.id,
        })
        cls.env.ref('recycle_warehouse.group_recycle_admin').sudo().write(
            {'user_ids': [(4, cls.env.user.id)]})

    def _driver(self, **overrides):
        vals = {
            'name': 'Sami Driver',
            'phone': '0900000001',
            'national_id': 'ND-0001',
            'warehouse_id': self.warehouse.id,
            # Both sides of the licence — the model refuses a half-filed one.
            'license_image_front': FRONT,
            'license_image_back': BACK,
        }
        vals.update(overrides)
        return self.env['recycle.delivery.driver'].create(vals)

    # ------------------------------------------------------------------
    # Truck type
    # ------------------------------------------------------------------
    def test_a_truck_declares_what_it_is_for(self):
        self.assertEqual(self.collection_truck.truck_type, 'collection')
        self.assertEqual(self.delivery_truck.truck_type, 'delivery')

    def test_existing_trucks_default_to_collection(self):
        """The fleet was entirely collection before the split, so anything
        created without saying is what it always was — not an unset flag that
        would leave a real truck belonging to neither pool."""
        truck = self.env['recycle.truck'].create({
            'name': 'Unspecified', 'plate_number': 'UNS-001',
        })
        self.assertEqual(truck.truck_type, 'collection')

    # ------------------------------------------------------------------
    # A collector may not be put on a delivery truck
    # ------------------------------------------------------------------
    def test_a_collector_cannot_be_assigned_to_a_delivery_truck(self):
        shift = self.env['recycle.shift'].create({
            'name': 'DT Morning', 'shift_type': 'driver',
            'start_time': 8.0, 'end_time': 16.0, 'is_global': True,
        })
        with self.assertRaises(ValidationError):
            self.env['recycle.driver.assignment'].create({
                'backend_driver_id': 'uuid-collector-1',
                'truck_id': self.delivery_truck.id,
                'shift_id': shift.id,
            })

    def test_the_collector_picker_never_offers_a_delivery_truck(self):
        """Enforced at the picker too, not only at the model.

        A screen that offers a choice the server then refuses teaches the user
        that the system is unreliable — the refusal is correct but arrives after
        they have already made a decision.
        """
        shift = self.env['recycle.shift'].create({
            'name': 'DT Evening', 'shift_type': 'driver',
            'start_time': 16.0, 'end_time': 23.0, 'is_global': True,
        })
        trucks = self.env['recycle.driver.assignment'].get_shift_free_trucks(
            shift.id)
        offered = {t['plate_number'] for t in trucks}

        self.assertIn('COL-001', offered)
        self.assertNotIn('DEL-001', offered)

    # ------------------------------------------------------------------
    # A delivery driver may not be put on a collection truck
    # ------------------------------------------------------------------
    def test_a_delivery_driver_cannot_take_a_collection_truck(self):
        with self.assertRaises(ValidationError):
            self._driver(truck_id=self.collection_truck.id)

    def test_a_delivery_driver_takes_a_delivery_truck(self):
        driver = self._driver(truck_id=self.delivery_truck.id)

        self.assertEqual(driver.truck_id, self.delivery_truck)
        self.assertTrue(driver.has_truck)

    def test_assigning_through_the_action_refuses_a_collection_truck(self):
        driver = self._driver()
        with self.assertRaises(UserError):
            self.env['recycle.delivery.driver'].action_assign_truck(
                driver.id, self.collection_truck.id)

    # ------------------------------------------------------------------
    # One truck, one driver — and the same warehouse
    # ------------------------------------------------------------------
    def test_two_drivers_cannot_share_one_truck(self):
        self._driver(truck_id=self.delivery_truck.id)
        with self.assertRaises(ValidationError):
            self._driver(name='Second Driver', national_id='ND-0002',
                         phone='0900000002',
                         truck_id=self.delivery_truck.id)

    def test_a_driver_cannot_take_a_truck_parked_at_another_warehouse(self):
        far_truck = self.env['recycle.truck'].create({
            'name': 'Far Deliverer', 'plate_number': 'DEL-999',
            'truck_type': 'delivery', 'warehouse_id': self.other_warehouse.id,
        })
        # An assignment to a vehicle at a site they never load from reads as
        # done and cannot be worked.
        with self.assertRaises(ValidationError):
            self._driver(truck_id=far_truck.id)

    def test_the_free_truck_list_excludes_one_already_driven(self):
        free_before = {t['plate_number'] for t
                       in self.env['recycle.delivery.driver']
                       .free_delivery_trucks(self.warehouse.id)}
        self.assertIn('DEL-001', free_before)

        self._driver(truck_id=self.delivery_truck.id)

        free_after = {t['plate_number'] for t
                      in self.env['recycle.delivery.driver']
                      .free_delivery_trucks(self.warehouse.id)}
        self.assertNotIn('DEL-001', free_after)

    def test_the_free_truck_list_never_offers_a_collection_truck(self):
        offered = {t['plate_number'] for t
                   in self.env['recycle.delivery.driver']
                   .free_delivery_trucks(self.warehouse.id)}

        self.assertNotIn('COL-001', offered)

    # ------------------------------------------------------------------
    # The licence
    # ------------------------------------------------------------------
    def test_both_sides_of_the_licence_are_required(self):
        """Half a licence proves nothing: the expiry date and the class are
        printed on the back, and they decide whether this person may drive a
        company truck at all."""
        with self.assertRaises(Exception):
            self.env['recycle.delivery.driver'].create({
                'name': 'No Back', 'phone': '0900000003',
                'national_id': 'ND-0003',
                'warehouse_id': self.warehouse.id,
                'license_image_front': FRONT,
            })

    def test_unassigning_frees_the_truck_again(self):
        driver = self._driver(truck_id=self.delivery_truck.id)

        self.env['recycle.delivery.driver'].action_unassign_truck(driver.id)

        self.assertFalse(driver.truck_id)
        self.assertFalse(driver.has_truck)
        offered = {t['plate_number'] for t
                   in self.env['recycle.delivery.driver']
                   .free_delivery_trucks(self.warehouse.id)}
        self.assertIn('DEL-001', offered)

    # ------------------------------------------------------------------
    # The happy paths, and the ones the screens depend on
    # ------------------------------------------------------------------
    def test_assigning_a_delivery_truck_through_the_action_works(self):
        """The refusals above only mean something if the allowed case passes —
        otherwise a rule that blocks everything would look equally correct."""
        driver = self._driver()

        self.env['recycle.delivery.driver'].action_assign_truck(
            driver.id, self.delivery_truck.id)

        self.assertEqual(driver.truck_id, self.delivery_truck)
        self.assertTrue(driver.has_truck)

    def test_a_collector_may_still_be_booked_onto_a_collection_truck(self):
        """The counterpart to the delivery-truck refusal: the split must not
        have broken the flow it was carved out of."""
        shift = self.env['recycle.shift'].create({
            'name': 'Collector Shift DTW', 'shift_type': 'driver',
            'start_time': 8.0, 'end_time': 16.0, 'is_global': True,
        })

        row = self.env['recycle.driver.assignment'].create({
            'backend_driver_id': 'be-collector-dtw',
            'truck_id': self.collection_truck.id,
            'shift_id': shift.id,
        })

        self.assertEqual(row.truck_id, self.collection_truck)

    def test_an_out_of_service_truck_is_never_offered(self):
        """A disabled truck cannot be driven, so proposing it would produce an
        assignment nobody can work — and the driver would find out in the yard."""
        self.delivery_truck.write({'is_active': False,
                                   'disable_reason': 'Engine failure'})

        offered = {t['plate_number'] for t
                   in self.env['recycle.delivery.driver']
                   .free_delivery_trucks(self.warehouse.id)}

        self.assertNotIn('DEL-001', offered)

    # ------------------------------------------------------------------
    # A manager is confined to their own warehouse
    # ------------------------------------------------------------------
    def _manager(self, login):
        manager = self.env['res.users'].create({
            'name': 'DTW Manager', 'login': login,
            'recycle_warehouse_id': self.warehouse.id,
        })
        self.env.ref('recycle_warehouse.group_recycle_manager').sudo().write(
            {'user_ids': [(4, manager.id)]})
        return manager

    def test_a_manager_cannot_assign_a_driver_of_another_warehouse(self):
        manager = self._manager('dtw_manager_scope')
        outsider = self._driver(national_id='ND-9001',
                                warehouse_id=self.other_warehouse.id)
        far_truck = self.env['recycle.truck'].create({
            'name': 'Far Deliverer', 'plate_number': 'DEL-FAR',
            'truck_type': 'delivery', 'warehouse_id': self.other_warehouse.id,
        })

        with self.assertRaises(UserError):
            self.env['recycle.delivery.driver'].with_user(
                manager).action_assign_truck(outsider.id, far_truck.id)

    def test_a_managers_truck_list_ignores_the_warehouse_they_ask_for(self):
        """The scope is FORCED, not taken from the argument.

        A manager passing another warehouse's id must not widen their own view —
        otherwise the server would trust a number the browser chose.
        """
        manager = self._manager('dtw_manager_scope_2')
        self.env['recycle.truck'].create({
            'name': 'Far Deliverer 2', 'plate_number': 'DEL-FAR2',
            'truck_type': 'delivery', 'warehouse_id': self.other_warehouse.id,
        })

        offered = {t['plate_number'] for t
                   in self.env['recycle.delivery.driver'].with_user(manager)
                   .free_delivery_trucks(self.other_warehouse.id)}

        self.assertNotIn('DEL-FAR2', offered)
        # And they still see their own.
        self.assertIn('DEL-001', offered)
