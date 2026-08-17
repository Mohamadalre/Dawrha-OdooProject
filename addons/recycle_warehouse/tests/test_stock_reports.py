# -*- coding: utf-8 -*-
"""Damage reports on stored material, under per-material grades.

Three invariants are protected here, and each one is a way the warehouse's
numbers could quietly stop matching the shelf:

  * A grade belongs to ONE material. A report may only name a grade its own
    material has, and an ungraded material may not carry one at all — otherwise
    the deduction lands on whichever row the database returned first, which is
    not the shelf the sorter was looking at.
  * Reserved stock is not the sorter's to write off. Doing so leaves the
    warehouse owing an open order more than it holds, and nobody finds out until
    the output employee cannot fill it.
  * An approved report must leave a LEDGER entry. Deducting the stock and
    recording nothing makes the loss visible only as a smaller number, which
    cannot answer what was lost, when, or why.
"""
from odoo.exceptions import UserError, ValidationError
from .common import make_warehouse
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestStockReports(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = make_warehouse(cls.env, **{
            'name': 'Report Test Warehouse', 'code': 'RTW1',
        })
        cls.zone = cls.env['recycle.zone'].create({
            'name': 'Storage R', 'warehouse_id': cls.warehouse.id,
            'zone_type': 'storage',
        })
        cls.category = cls.env['recycle.product.category'].create(
            {'name': 'Report Test Category'})

        # A GRADED material. Its grades are deliberately NOT the old fixed
        # four: nothing in the system may depend on those particular words.
        _unit = cls.env['recycle.measurement.unit']
        cls._kg = _unit.search([('code', '=', 'KG')], limit=1) or _unit.create(
            {'code': 'KG', 'name': 'Kilogram', 'allows_tolerance': True})
        cls.product = cls.env['recycle.product'].create({
            'name': 'Report Test Material', 'category_id': cls.category.id,
            'uom_id': cls._kg.id,
        })
        Condition = cls.env['recycle.material.condition']
        cls.grade_top = Condition.create({
            'product_id': cls.product.id, 'code': 'PREMIUM',
            'name': 'Premium', 'sort_order': 1,
        })
        cls.grade_mid = Condition.create({
            'product_id': cls.product.id, 'code': 'STANDARD',
            'name': 'Standard', 'sort_order': 2,
        })

        # An UNGRADED material — a normal, common case, not missing setup.
        cls.plain = cls.env['recycle.product'].create({
            'name': 'Ungraded Material', 'category_id': cls.category.id,
            'uom_id': cls._kg.id,
        })

        # Approving is a supervisor action, so the test user has to be one.
        cls.env.ref('recycle_warehouse.group_recycle_admin').sudo().write(
            {'user_ids': [(4, cls.env.user.id)]})

    def setUp(self):
        super().setUp()
        self.env['recycle.stock'].search([
            ('warehouse_id', '=', self.warehouse.id)]).unlink()

    def _stock(self, qty, condition='PREMIUM', reserved=0.0, product=None):
        line = self.env['recycle.stock'].create({
            'warehouse_id': self.warehouse.id,
            'product_id': (product or self.product).id,
            'zone_id': self.zone.id,
            'condition': condition,
            'quantity': qty,
        })
        if reserved:
            line.reserved_qty = reserved
        return line

    def _total(self, product=None):
        return sum(self.env['recycle.stock'].search([
            ('warehouse_id', '=', self.warehouse.id),
            ('product_id', '=', (product or self.product).id)]).mapped('quantity'))

    def _qty_of(self, condition, product=None):
        return sum(self.env['recycle.stock'].search([
            ('warehouse_id', '=', self.warehouse.id),
            ('product_id', '=', (product or self.product).id),
            ('condition', '=', condition)]).mapped('quantity'))

    def _report(self, **overrides):
        vals = {
            'warehouse_id': self.warehouse.id,
            'product_id': self.product.id,
            'condition': 'PREMIUM',
            'quantity': 10.0,
            'reason': 'Left near the loading door over a wet week.',
        }
        vals.update(overrides)
        return self.env['recycle.stock.damage.report'].create(vals)

    # ------------------------------------------------------------------
    # Grades belong to the material
    # ------------------------------------------------------------------
    def test_a_report_may_only_name_a_grade_this_material_has(self):
        self._stock(100, 'PREMIUM')
        # 'GOOD' was one of the four words the whole module used to share. It
        # is not a grade of THIS material, and must be refused rather than
        # matched against nothing.
        with self.assertRaises(ValidationError):
            self._report(condition='GOOD')

    def test_a_graded_material_must_say_which_grade_was_lost(self):
        self._stock(100, 'PREMIUM')
        with self.assertRaises(ValidationError):
            self._report(condition=False)

    def test_an_ungraded_material_may_not_carry_a_grade(self):
        self._stock(100, condition=False, product=self.plain)
        with self.assertRaises(ValidationError):
            self._report(product_id=self.plain.id, condition='PREMIUM')

    def test_grade_codes_are_matched_case_insensitively(self):
        """The backend authors codes upper-case; a lower-case one is the same
        grade, not a second one that matches nothing."""
        self._stock(100, 'PREMIUM')
        report = self._report(condition='premium', quantity=10)
        self.assertEqual(report.condition, 'PREMIUM')

    # ------------------------------------------------------------------
    # Damage
    # ------------------------------------------------------------------
    def test_damage_writes_the_quantity_off_from_its_own_grade(self):
        self._stock(100, 'PREMIUM')
        self._stock(50, 'STANDARD')

        self._report(condition='PREMIUM', quantity=40).action_approve()

        self.assertEqual(self._qty_of('PREMIUM'), 60)
        # The other grade is untouched — the sorter reported on one shelf.
        self.assertEqual(self._qty_of('STANDARD'), 50)
        self.assertEqual(self._total(), 110)

    def test_damage_on_an_ungraded_material_needs_no_grade(self):
        self._stock(80, condition=False, product=self.plain)

        report = self._report(product_id=self.plain.id, condition=False,
                              quantity=30)
        report.action_approve()

        self.assertEqual(self._total(product=self.plain), 50)

    # ------------------------------------------------------------------
    # The ledger
    # ------------------------------------------------------------------
    def test_approval_writes_a_ledger_entry_with_the_date_and_the_warehouse(self):
        self._stock(100, 'PREMIUM')
        report = self._report(quantity=25)

        report.action_approve()

        entry = report.damage_entry_id
        self.assertTrue(entry, 'an approved report must leave a ledger entry')
        self.assertEqual(entry.warehouse_id, self.warehouse)
        self.assertEqual(entry.product_id, self.product)
        self.assertEqual(entry.condition, 'PREMIUM')
        self.assertEqual(entry.quantity, 25)
        self.assertEqual(entry.source, 'storage')
        self.assertTrue(entry.occurred_at, 'the loss must carry its date')
        # Traceable back to the paperwork behind the figure.
        self.assertEqual(entry.report_id, report)

    def test_a_rejected_report_leaves_no_ledger_entry(self):
        self._stock(100, 'PREMIUM')
        report = self._report(quantity=25)

        report.action_reject('Photo shows a different pallet')

        self.assertFalse(report.damage_entry_id)
        self.assertEqual(self._total(), 100)

    def test_the_ledger_cannot_be_edited_or_deleted(self):
        """A figure that can be adjusted afterwards is not evidence of anything.
        A correction is a new entry, which leaves both the error and the fix."""
        self._stock(100, 'PREMIUM')
        report = self._report(quantity=25)
        report.action_approve()
        entry = report.damage_entry_id

        with self.assertRaises(UserError):
            entry.with_user(self.env.user).write({'quantity': 1})
        with self.assertRaises(UserError):
            entry.with_user(self.env.user).unlink()

    # ------------------------------------------------------------------
    # Reserved stock
    # ------------------------------------------------------------------
    def test_reserved_stock_cannot_be_reported_on(self):
        """80 on the shelf, 60 promised to an order → only 20 is reportable."""
        self._stock(80, 'PREMIUM', reserved=60)

        with self.assertRaises(UserError):
            self._report(quantity=30)

        # And what IS free still goes through.
        report = self._report(quantity=20)
        self.assertEqual(report.state, 'pending_approval')

    def test_the_check_runs_again_at_approval_not_only_at_filing(self):
        """The report waits for the manager, and an order can be allocated in
        the meantime — approving on a stale check would overdraw the shelf."""
        line = self._stock(80, 'PREMIUM')
        report = self._report(quantity=50)

        # An order is allocated while the manager is deciding.
        line.reserved_qty = 60

        with self.assertRaises(UserError):
            report.action_approve()
        self.assertEqual(report.state, 'pending_approval')
        self.assertEqual(self._total(), 80)

    # ------------------------------------------------------------------
    # Approval
    # ------------------------------------------------------------------
    def test_only_a_supervisor_may_approve(self):
        self._stock(100, 'PREMIUM')
        report = self._report(quantity=10)

        sorter = self.env['res.users'].create({
            'name': 'Sorter', 'login': 'sorter_report_test',
        })
        self.env.ref('recycle_warehouse.group_recycle_sorting').sudo().write(
            {'user_ids': [(4, sorter.id)]})

        with self.assertRaises(UserError):
            report.with_user(sorter).action_approve()
        self.assertEqual(self._total(), 100)

    def test_a_report_cannot_be_decided_twice(self):
        self._stock(100, 'PREMIUM')
        report = self._report(quantity=10)
        report.action_approve()

        with self.assertRaises(UserError):
            report.action_approve()
        with self.assertRaises(UserError):
            report.action_reject('changed my mind')
        # Still deducted exactly once, and logged exactly once.
        self.assertEqual(self._total(), 90)
        self.assertEqual(self.env['recycle.damage.entry'].search_count(
            [('report_id', '=', report.id)]), 1)

    def test_rejection_changes_no_stock(self):
        self._stock(100, 'PREMIUM')
        report = self._report(quantity=10)

        report.action_reject('Photo shows a different pallet')

        self.assertEqual(report.state, 'rejected')
        self.assertEqual(self._total(), 100)
        self.assertIn('different pallet', report.review_reason)
