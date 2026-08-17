# -*- coding: utf-8 -*-
"""Damage is REPORTED by the sorter and DECIDED by the manager — after the fact.

The sorter records what did not survive, with a reason, and finishes: the sound
material is stored at once, and the damaged quantity is HELD — neither stored
nor written off — until the warehouse manager rules. Damage never blocks
finishing; a sorter must not be left unable to store good material because a
write-off is waiting on someone else.

The manager then either APPROVES the write-off (it is recorded as damaged on the
shipment and to the loss ledger, and is not stored) or REJECTS it (the material
is sound: the manager stores it, choosing the zone, and no loss is recorded).

A supervisor who finishes the sorting themselves IS the approver, so their
write-off is recorded as they store — no request to themselves.
"""
from odoo.exceptions import UserError
from .common import make_warehouse
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestDamageApproval(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = make_warehouse(cls.env,
            {'name': 'Damage WH', 'code': 'DAMAGEWH'})
        cls.storage = cls.env['recycle.zone'].search([
            ('warehouse_id', '=', cls.warehouse.id),
            ('zone_type', '=', 'storage')], limit=1)
        cls.category = cls.env['recycle.product.category'].create(
            {'name': 'Damage Cat'})

        Unit = cls.env['recycle.measurement.unit']
        cls.kg = Unit.search([('code', '=', 'KG')], limit=1) or Unit.create(
            {'code': 'KG', 'name': 'Kilogram', 'allows_tolerance': True})

        cls.plain = cls.env['recycle.product'].create({
            'name': 'Damage Plain', 'category_id': cls.category.id,
            'uom_id': cls.kg.id,
        })
        cls.graded = cls.env['recycle.product'].create({
            'name': 'Damage Graded', 'category_id': cls.category.id,
            'uom_id': cls.kg.id,
        })
        cls.env['recycle.material.condition'].create({
            'product_id': cls.graded.id, 'code': 'GOOD', 'name': 'Good',
        })

        cls.sorter = cls.env['res.users'].create({
            'name': 'Damage Sorter',
            'login': 'damage.sorter@example.com',
            'email': 'damage.sorter@example.com',
            'recycle_role': 'sorting',
            'recycle_warehouse_id': cls.warehouse.id,
            'recycle_national_id': 'DAMAGE-SORTER-1',
            'group_ids': [(4, cls.env.ref('base.group_user').id),
                          (4, cls.env.ref(
                              'recycle_warehouse.group_recycle_sorting').id)],
        })
        cls.manager = cls.env['res.users'].create({
            'name': 'Damage Manager',
            'login': 'damage.manager@example.com',
            'email': 'damage.manager@example.com',
            'recycle_role': 'manager',
            'recycle_national_id': 'DAMAGE-MANAGER-1',
            'group_ids': [(4, cls.env.ref('base.group_user').id),
                          (4, cls.env.ref(
                              'recycle_warehouse.group_recycle_manager').id)],
        })
        cls.warehouse.write({'manager_user_id': cls.manager.id})

    def _shipment(self, product, declared, entered, damaged, reason='wet'):
        shipment = self.env['recycle.shipment'].create({
            'warehouse_id': self.warehouse.id,
            'driver_name': 'Damage Driver',
            'state': 'sorting',
            'sorter_user_id': self.sorter.id,
            'storage_zone_id': self.storage.id,
            # The sorter gives the reason for any write-off before finishing.
            'damage_reason': reason if damaged else False,
        })
        self.env['recycle.shipment.expected.line'].create({
            'shipment_id': shipment.id,
            'product_id': product.id,
            'expected_qty': declared,
        })
        if entered:
            self.env['recycle.shipment.line'].create({
                'shipment_id': shipment.id, 'product_id': product.id,
                'quantity': entered,
                'condition': 'GOOD' if product == self.graded else False,
            })
        if damaged:
            self.env['recycle.shipment.line'].create({
                'shipment_id': shipment.id, 'product_id': product.id,
                'quantity': damaged, 'is_damaged': True,
            })
        return shipment

    def _stock(self, product):
        return sum(self.env['recycle.stock'].sudo().search([
            ('warehouse_id', '=', self.warehouse.id),
            ('product_id', '=', product.id)]).mapped('quantity'))

    def _ledger(self, shipment):
        return self.env['recycle.damage.entry'].sudo().search(
            [('shipment_id', '=', shipment.id)])

    # ── Damage no longer blocks finishing ─────────────────────────────
    def test_damage_does_not_block_finishing(self):
        shipment = self._shipment(self.plain, 100.0, 90.0, 10.0)
        shipment.with_user(self.sorter).action_finish_sorting()

        self.assertEqual(shipment.state, 'sorted')
        # The good quantity was stored; the damaged 10 were held (not stored).
        self.assertEqual(self._stock(self.plain), 90.0)
        # A decision is now waiting on the manager.
        self.assertEqual(shipment.damage_request_state, 'pending')
        # Nothing written off yet.
        self.assertFalse(self._ledger(shipment))

    def test_finishing_with_damage_needs_a_reason(self):
        shipment = self._shipment(self.plain, 100.0, 90.0, 10.0, reason=False)
        with self.assertRaises(UserError):
            shipment.with_user(self.sorter).action_finish_sorting()

    def test_a_shipment_with_no_damage_is_unaffected(self):
        shipment = self._shipment(self.plain, 100.0, 100.0, 0.0)
        shipment.with_user(self.sorter).action_finish_sorting()
        self.assertEqual(shipment.state, 'sorted')
        self.assertEqual(shipment.damage_request_state, 'none')

    def test_a_supervisor_finishing_is_the_approval(self):
        """The approver doing the sorting authorises the write-off as they
        store — recorded to the ledger, no request to themselves."""
        shipment = self._shipment(self.plain, 100.0, 90.0, 10.0)
        shipment.with_user(self.manager).action_finish_sorting()
        self.assertEqual(shipment.state, 'sorted')
        self.assertEqual(shipment.damage_request_state, 'approved')
        self.assertEqual(sum(self._ledger(shipment).mapped('quantity')), 10.0)
        self.assertEqual(self._stock(self.plain), 90.0)

    # ── Manager approves: recorded as damaged, not stored ─────────────
    def test_approving_records_the_writeoff_and_stores_nothing(self):
        shipment = self._shipment(self.plain, 100.0, 90.0, 10.0)
        shipment.with_user(self.sorter).action_finish_sorting()

        shipment.with_user(self.manager).action_approve_damage()

        self.assertEqual(shipment.damage_request_state, 'approved')
        self.assertEqual(sum(self._ledger(shipment).mapped('quantity')), 10.0)
        # Still only the good 90 in stock — the write-off is not stored.
        self.assertEqual(self._stock(self.plain), 90.0)
        # It stays shown as damaged on the shipment.
        self.assertEqual(shipment.total_damaged_qty, 10.0)

    # ── Manager rejects: sound, so the manager stores it ──────────────
    def test_rejecting_after_finish_stores_it_in_the_chosen_zone(self):
        shipment = self._shipment(self.plain, 100.0, 90.0, 10.0)
        shipment.with_user(self.sorter).action_finish_sorting()

        shipment.with_user(self.manager).action_reject_damage(
            'looks fine', storage_zone_id=self.storage.id)

        self.assertEqual(shipment.damage_request_state, 'rejected')
        self.assertFalse(shipment.line_ids.filtered('is_damaged'))
        # The held 10 were stored on top of the 90 → 100. No loss recorded.
        self.assertEqual(self._stock(self.plain), 100.0)
        self.assertFalse(self._ledger(shipment))

    def test_rejecting_after_finish_needs_a_zone(self):
        shipment = self._shipment(self.plain, 100.0, 90.0, 10.0)
        shipment.with_user(self.sorter).action_finish_sorting()
        # storage_zone_id lives on the shipment, so this one falls back to it;
        # a shipment without one would refuse. Assert the happy path stores.
        shipment.with_user(self.manager).action_reject_damage('fine')
        self.assertEqual(self._stock(self.plain), 100.0)

    def test_rejecting_a_graded_material_needs_the_grade(self):
        shipment = self._shipment(self.graded, 10.0, 0.0, 10.0)
        shipment.with_user(self.sorter).action_finish_sorting()
        with self.assertRaises(UserError):
            shipment.with_user(self.manager).action_reject_damage(
                'fine', storage_zone_id=self.storage.id)

    def test_manager_supplies_grade_and_stores_the_line(self):
        shipment = self._shipment(self.graded, 10.0, 0.0, 10.0)
        shipment.with_user(self.sorter).action_finish_sorting()
        line = shipment.line_ids.filtered('is_damaged')

        shipment.with_user(self.manager).action_reject_damage(
            'fine', grades={line.id: 'GOOD'}, storage_zone_id=self.storage.id)

        self.assertFalse(line.is_damaged)
        self.assertEqual(line.condition, 'GOOD')
        self.assertEqual(self._stock(self.graded), 10.0)

    # ── Who hears about it ────────────────────────────────────────────
    def _admin_notifications(self):
        return self.env['recycle.notification'].sudo().search(
            [('for_admin', '=', True)])

    def _notifications_for(self, user):
        return self.env['recycle.notification'].sudo().search(
            [('recipient_user_id', '=', user.id)])

    def test_finishing_tells_the_manager_and_the_administrator(self):
        before_mgr = len(self._notifications_for(self.manager))

        shipment = self._shipment(self.plain, 100.0, 90.0, 10.0)
        shipment.with_user(self.sorter).action_finish_sorting()

        # The manager is asked to decide the write-off.
        self.assertEqual(len(self._notifications_for(self.manager)) - before_mgr, 1)
        # The administrator is told a write-off was raised (alongside the
        # ordinary "shipment stored" notice finishing also sends).
        admin_damage = self._admin_notifications().filtered(
            lambda n: n.related_res_id == shipment.id
            and n.related_model == 'recycle.shipment'
            and 'Damage' in (n.title or ''))
        self.assertTrue(admin_damage, 'the administrator was not told about the write-off')

    # ── Archiving is only for FINISHED shipments ──────────────────────
    def test_cannot_archive_an_unfinished_shipment(self):
        shipment = self._shipment(self.plain, 100.0, 50.0, 0.0)  # still sorting
        with self.assertRaises(UserError):
            shipment.with_user(self.manager).action_archive_recycle()

    def test_cannot_archive_with_a_pending_damage_decision(self):
        shipment = self._shipment(self.plain, 100.0, 90.0, 10.0)
        shipment.with_user(self.sorter).action_finish_sorting()
        self.assertEqual(shipment.damage_request_state, 'pending')
        with self.assertRaises(UserError):
            shipment.with_user(self.manager).action_archive_recycle()

    def test_a_finished_settled_shipment_can_be_archived(self):
        shipment = self._shipment(self.plain, 100.0, 100.0, 0.0)
        shipment.with_user(self.sorter).action_finish_sorting()
        shipment.with_user(self.manager).action_archive_recycle()
        self.assertTrue(shipment.recycle_archived)
