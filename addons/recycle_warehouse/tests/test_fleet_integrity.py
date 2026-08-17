# -*- coding: utf-8 -*-
"""Rules that keep the fleet's records honest once people start using it.

Four separate problems, all of them the kind that look like nothing on the day
they happen and cannot be untangled later:

  * ONE IDENTITY PER PERSON. A national ID identifies a human being, not a row.
    Four tables hold people here, and until they consulted each other the same
    person could exist in all four — four histories, four blocks, no way to say
    which record is them.
  * A TRUCK'S JOB IS FIXED. Flipping collection to delivery would strand every
    assignment built on it, in a different table with different rules, and
    nothing on either screen would show it.
  * A MOVED TRUCK LEAVES ITS DRIVER BEHIND. Loading happens at a warehouse, so a
    driver at site A holding a van now parked at site B has an assignment that
    reads as done and cannot be worked.
  * WHO HELD WHAT, AND WHEN. The first question after an accident or a fuel
    discrepancy — and one the system could not answer at all, because only the
    CURRENT holder was ever stored.
"""
import base64

from odoo.exceptions import UserError, ValidationError
from .common import make_warehouse
from odoo.tests.common import TransactionCase, tagged

FRONT = base64.b64encode(b'front').decode()
BACK = base64.b64encode(b'back').decode()


@tagged('post_install', '-at_install')
class TestFleetIntegrity(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.wh = make_warehouse(cls.env, **{
            'name': 'Integrity WH', 'code': 'ITG1'})
        cls.wh2 = make_warehouse(cls.env, **{
            'name': 'Integrity WH 2', 'code': 'ITG2'})
        cls.truck = cls.env['recycle.truck'].create({
            'name': 'ITG Delivery', 'plate_number': 'ITG-D1',
            'truck_type': 'delivery', 'warehouse_id': cls.wh.id})
        cls.collection = cls.env['recycle.truck'].create({
            'name': 'ITG Collection', 'plate_number': 'ITG-C1',
            'truck_type': 'collection', 'warehouse_id': cls.wh.id})
        cls.env.ref('recycle_warehouse.group_recycle_admin').sudo().write(
            {'user_ids': [(4, cls.env.user.id)]})

    def _driver(self, **over):
        vals = {
            'name': 'ITG Driver', 'phone': '0911111111',
            'national_id': 'ITG-N1', 'email': 'itg1@dawrha.test',
            'warehouse_id': self.wh.id,
            'license_image_front': FRONT, 'license_image_back': BACK,
        }
        vals.update(over)
        return self.env['recycle.delivery.driver'].create(vals)

    # ------------------------------------------------------------------
    # One identity per person, across every table
    # ------------------------------------------------------------------
    def test_a_national_id_cannot_be_reused_by_a_system_user(self):
        self._driver(national_id='ITG-SHARED', email='shared1@dawrha.test')

        with self.assertRaises(ValidationError):
            self.env['res.users'].create({
                'name': 'Impostor', 'login': 'itg_impostor',
                'recycle_national_id': 'ITG-SHARED',
            })

    def test_an_email_cannot_be_reused_by_a_system_user(self):
        self._driver(national_id='ITG-N-MAIL', email='taken@dawrha.test')

        with self.assertRaises(ValidationError):
            self.env['res.users'].create({
                'name': 'Impostor 2', 'login': 'itg_impostor_2',
                'email': 'taken@dawrha.test',
            })

    def test_a_driver_cannot_reuse_a_users_national_id(self):
        self.env['res.users'].create({
            'name': 'Existing Staff', 'login': 'itg_staff',
            'recycle_national_id': 'ITG-STAFF-1',
        })

        with self.assertRaises(ValidationError):
            self._driver(national_id='ITG-STAFF-1', email='other@dawrha.test')

    def test_the_error_names_WHERE_the_identity_is_already_used(self):
        """"Already in use" sends someone hunting through the wrong screen."""
        self._driver(national_id='ITG-NAMED', email='named@dawrha.test')

        with self.assertRaises(ValidationError) as caught:
            self.env['res.users'].create({
                'name': 'Impostor 3', 'login': 'itg_impostor_3',
                'recycle_national_id': 'ITG-NAMED',
            })

        self.assertIn('delivery driver', str(caught.exception))

    def test_a_driver_and_their_own_login_are_ONE_person(self):
        """Issuing a login copies the driver's national ID onto res.users.

        Treating that as a clash would refuse a driver their own account and
        point at the driver themselves as the culprit.
        """
        driver = self._driver(national_id='ITG-SELF', email='self@dawrha.test')

        driver.action_create_login()

        self.assertTrue(driver.user_id)
        self.assertEqual(driver.user_id.recycle_national_id, 'ITG-SELF')
        # And editing the driver afterwards still works.
        driver.write({'phone': '0922222222'})

    # ------------------------------------------------------------------
    # A truck's job is fixed for life
    # ------------------------------------------------------------------
    def test_a_delivery_truck_cannot_become_a_collection_truck(self):
        with self.assertRaises(UserError):
            self.truck.write({'truck_type': 'collection'})

    def test_a_collection_truck_cannot_become_a_delivery_truck(self):
        with self.assertRaises(UserError):
            self.collection.write({'truck_type': 'delivery'})

    def test_writing_the_SAME_job_is_not_a_change(self):
        """A form that posts every field must not fail just for re-sending one."""
        self.truck.write({'truck_type': 'delivery', 'model': 'Isuzu'})

        self.assertEqual(self.truck.model, 'Isuzu')

    # ------------------------------------------------------------------
    # A moved truck leaves its driver behind
    # ------------------------------------------------------------------
    def test_moving_a_truck_releases_a_driver_who_did_not_move(self):
        driver = self._driver(national_id='ITG-MOVE', email='move@dawrha.test',
                              truck_id=self.truck.id)
        self.assertTrue(driver.has_truck)

        self.truck.write({'warehouse_id': self.wh2.id})

        # The assignment could no longer be worked: the driver loads at one
        # site and the van now sits at another.
        self.assertFalse(driver.truck_id)
        self.assertFalse(driver.has_truck)

    def test_moving_a_truck_keeps_a_driver_who_belongs_to_the_new_warehouse(self):
        driver = self._driver(
            national_id='ITG-STAY', email='stay@dawrha.test',
            warehouse_id=self.wh2.id)
        truck = self.env['recycle.truck'].create({
            'name': 'ITG Stay', 'plate_number': 'ITG-D2',
            'truck_type': 'delivery', 'warehouse_id': self.wh2.id})
        driver.write({'truck_id': truck.id})

        truck.write({'warehouse_id': self.wh2.id, 'model': 'Same site'})

        self.assertEqual(driver.truck_id, truck)

    # ------------------------------------------------------------------
    # Who held what, and when
    # ------------------------------------------------------------------
    def test_assigning_opens_a_holding_period(self):
        driver = self._driver(national_id='ITG-HIST', email='hist@dawrha.test')
        History = self.env['recycle.truck.assignment.history']

        self.env['recycle.delivery.driver'].action_assign_truck(
            driver.id, self.truck.id)

        row = History.search([('delivery_driver_id', '=', driver.id)], limit=1)
        self.assertTrue(row, 'the hand-over must be recorded')
        self.assertTrue(row.is_current)
        self.assertFalse(row.released_at)
        self.assertEqual(row.driver_kind, 'delivery')
        # The name is SNAPSHOTTED so a report still reads correctly after a
        # rename or a removal.
        self.assertEqual(row.driver_name, driver.name)

    def test_unassigning_closes_the_period_rather_than_erasing_it(self):
        driver = self._driver(national_id='ITG-HIST2', email='hist2@dawrha.test',
                              truck_id=self.truck.id)
        History = self.env['recycle.truck.assignment.history']

        self.env['recycle.delivery.driver'].action_unassign_truck(driver.id)

        row = History.search([('delivery_driver_id', '=', driver.id)], limit=1)
        self.assertTrue(row.released_at, 'the period must be closed, not deleted')
        self.assertFalse(row.is_current)

    def test_a_warehouse_move_is_recorded_with_its_own_reason(self):
        """"Released because the truck moved" and "unassigned by a manager" are
        different facts, and the person reading the report needs to tell them
        apart."""
        driver = self._driver(national_id='ITG-HIST3', email='hist3@dawrha.test',
                              truck_id=self.truck.id)
        History = self.env['recycle.truck.assignment.history']

        self.truck.write({'warehouse_id': self.wh2.id})

        row = History.search([('delivery_driver_id', '=', driver.id)], limit=1)
        self.assertEqual(row.release_reason, 'warehouse_change')

    def test_history_cannot_be_edited_or_deleted(self):
        driver = self._driver(national_id='ITG-HIST4', email='hist4@dawrha.test',
                              truck_id=self.truck.id)
        row = self.env['recycle.truck.assignment.history'].search(
            [('delivery_driver_id', '=', driver.id)], limit=1)

        # A period whose dates can be rewritten afterwards proves nothing.
        with self.assertRaises(UserError):
            row.write({'driver_name': 'Someone Else'})
        with self.assertRaises(UserError):
            row.unlink()

    def test_the_report_returns_flat_rows_for_export(self):
        driver = self._driver(national_id='ITG-REP', email='rep@dawrha.test',
                              truck_id=self.truck.id)

        rows = self.env['recycle.truck.assignment.history'].driver_report(
            driver_kind='delivery', warehouse_id=self.wh.id)

        self.assertTrue(rows)
        row = rows[0]
        for key in ('driver_name', 'truck_plate', 'assigned_at',
                    'duration_days', 'is_current', 'driver_kind'):
            self.assertIn(key, row)
        self.assertEqual(row['driver_name'], driver.name)

    # ------------------------------------------------------------------
    # Blocking
    # ------------------------------------------------------------------
    def test_blocking_takes_the_truck_back_and_disables_the_login(self):
        driver = self._driver(national_id='ITG-BLOCK', email='block@dawrha.test',
                              truck_id=self.truck.id)
        driver.action_create_login()
        user = driver.user_id

        driver.action_block('Repeated unreported damage')

        self.assertTrue(driver.is_blocked)
        # Leaving the van with them would undo the point of the block: it would
        # sit unavailable to everyone while the one person barred from driving
        # it still holds it on paper.
        self.assertFalse(driver.truck_id)
        # A block that leaves the account able to sign in is a note, not a block.
        self.assertFalse(user.active)

    def test_a_block_requires_a_reason(self):
        driver = self._driver(national_id='ITG-BLOCK2', email='block2@dawrha.test')

        with self.assertRaises(UserError):
            driver.action_block('   ')

    def test_unblocking_does_not_silently_take_the_truck_off_someone_else(self):
        driver = self._driver(national_id='ITG-BLOCK3', email='block3@dawrha.test',
                              truck_id=self.truck.id)
        driver.action_block('Suspended pending review')
        # The truck went back to the pool and someone else took it.
        other = self._driver(national_id='ITG-BLOCK4', email='block4@dawrha.test',
                             name='Replacement')
        self.env['recycle.delivery.driver'].action_assign_truck(
            other.id, self.truck.id)

        driver.action_unblock()

        self.assertFalse(driver.is_blocked)
        self.assertFalse(driver.truck_id)
        self.assertEqual(other.truck_id, self.truck)
