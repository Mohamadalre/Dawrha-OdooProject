# -*- coding: utf-8 -*-
"""What a delivery driver can see when they sign in.

Their dashboard is built on the same shell as every other role's, so the part
worth testing is not the layout — it is the two things the shell cannot get
wrong on its own:

  * the driver is routed to THEIR dashboard, not to a warehouse one. They hold
    no warehouse role, so the staff check that gates the backend had to learn
    about them; without that they log in successfully and are bounced away from
    the only screen they have.
  * they see EXACTLY their own record and their own truck. The dashboard reads
    through ordinary searches, which is only safe because the record rules make
    "their own" the only answer those searches can give.

The screen replaces "My Shift" with "My Truck", and that is a claim about the
job rather than a layout preference: a delivery driver works no shift, so an
empty shift card would state something untrue about how they are scheduled.
"""
import base64

from odoo.tests.common import TransactionCase, tagged
from .common import make_warehouse

FRONT = base64.b64encode(b'licence-front').decode()
BACK = base64.b64encode(b'licence-back').decode()


@tagged('post_install', '-at_install')
class TestDeliveryDriverDashboard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = make_warehouse(cls.env, **{
            'name': 'Dashboard WH', 'code': 'DDD1',
        })
        cls.other_warehouse = make_warehouse(cls.env, **{
            'name': 'Dashboard WH 2', 'code': 'DDD2',
        })
        cls.truck = cls.env['recycle.truck'].create({
            'name': 'My Delivery Truck', 'plate_number': 'DDD-001',
            'truck_type': 'delivery', 'warehouse_id': cls.warehouse.id,
            'model': 'Hyundai HD65', 'year': 2021, 'max_payload_kg': 3500,
        })
        # A second delivery truck nobody drives — it must stay invisible.
        cls.other_truck = cls.env['recycle.truck'].create({
            'name': 'Someone Else Truck', 'plate_number': 'DDD-002',
            'truck_type': 'delivery', 'warehouse_id': cls.other_warehouse.id,
        })
        cls.env.ref('recycle_warehouse.group_recycle_admin').sudo().write(
            {'user_ids': [(4, cls.env.user.id)]})

        cls.driver = cls.env['recycle.delivery.driver'].create({
            'name': 'Kareem Delivery',
            'phone': '0999111222',
            'email': 'kareem.dashboard@dawrha.test',
            'national_id': 'DDD-N-1',
            'warehouse_id': cls.warehouse.id,
            'truck_id': cls.truck.id,
            'license_number': 'LIC-77',
            'license_image_front': FRONT,
            'license_image_back': BACK,
        })
        cls.driver.action_create_login()
        cls.driver_user = cls.driver.user_id

        # A colleague at another warehouse — the isolation counterpart.
        cls.colleague = cls.env['recycle.delivery.driver'].create({
            'name': 'Other Driver',
            'phone': '0999333444',
            'email': 'other.dashboard@dawrha.test',
            'national_id': 'DDD-N-2',
            'warehouse_id': cls.other_warehouse.id,
            'truck_id': cls.other_truck.id,
            'license_image_front': FRONT,
            'license_image_back': BACK,
        })

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------
    def test_a_login_is_created_in_the_delivery_driver_group_only(self):
        user = self.driver_user
        self.assertTrue(user, 'the driver must get a login')
        self.assertTrue(user.has_group(
            'recycle_warehouse.group_recycle_delivery_driver'))
        # Not a warehouse employee: they work no shift and touch no stock, so
        # inheriting an employee group would hand them screens written for
        # someone else's job.
        for group in ('group_recycle_sorting', 'group_recycle_output',
                      'group_recycle_input', 'group_recycle_manager',
                      'group_recycle_admin'):
            self.assertFalse(
                user.has_group('recycle_warehouse.%s' % group),
                'a delivery driver must not hold %s' % group)

    def test_the_driver_record_is_found_from_the_login(self):
        found = self.env['recycle.delivery.driver'].for_user(self.driver_user)
        self.assertEqual(found, self.driver)

    # ------------------------------------------------------------------
    # Isolation — the dashboard reads through ordinary searches
    # ------------------------------------------------------------------
    def test_a_driver_sees_only_their_own_record(self):
        visible = self.env['recycle.delivery.driver'].with_user(
            self.driver_user).search([])

        self.assertEqual(visible, self.driver)

    def test_a_driver_sees_only_their_own_truck(self):
        visible = self.env['recycle.truck'].with_user(
            self.driver_user).search([])

        # Not the colleague's truck, and not the rest of the fleet — the
        # dashboard is safe to build on a plain search precisely because this
        # is the only answer it can get.
        self.assertEqual(visible, self.truck)

    def test_a_driver_without_a_truck_sees_no_truck_at_all(self):
        lone = self.env['recycle.delivery.driver'].create({
            'name': 'Truckless', 'phone': '0999555666',
            'email': 'truckless@dawrha.test', 'national_id': 'DDD-N-3',
            'warehouse_id': self.warehouse.id,
            'license_image_front': FRONT, 'license_image_back': BACK,
        })
        lone.action_create_login()

        visible = self.env['recycle.truck'].with_user(lone.user_id).search([])

        self.assertFalse(visible)

    # ------------------------------------------------------------------
    # What the dashboard is handed
    # ------------------------------------------------------------------
    def test_the_dashboard_payload_carries_the_truck_and_the_driver(self):
        """Mirrors /api/recycle/my-delivery-truck without the HTTP layer."""
        driver = self.env['recycle.delivery.driver'].for_user(self.driver_user)
        self.assertTrue(driver)

        truck = driver.truck_id
        self.assertTrue(truck)
        self.assertEqual(truck.plate_number, 'DDD-001')
        self.assertEqual(truck.truck_type, 'delivery')
        self.assertEqual(truck.warehouse_id, self.warehouse)
        self.assertEqual(driver.warehouse_id, self.warehouse)

    def test_no_truck_yet_is_a_real_answer_not_an_error(self):
        """A driver can be on file before a truck is free.

        Reporting that plainly is the point: an empty screen would read like
        something broke, and the driver would go looking for a fault that does
        not exist.
        """
        lone = self.env['recycle.delivery.driver'].create({
            'name': 'Waiting Driver', 'phone': '0999777888',
            'email': 'waiting@dawrha.test', 'national_id': 'DDD-N-4',
            'warehouse_id': self.warehouse.id,
            'license_image_front': FRONT, 'license_image_back': BACK,
        })

        self.assertFalse(lone.truck_id)
        self.assertFalse(lone.has_truck)
        # The warehouse is still known, so the screen is not blank.
        self.assertEqual(lone.warehouse_id, self.warehouse)
