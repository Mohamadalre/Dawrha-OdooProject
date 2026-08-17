# -*- coding: utf-8 -*-
"""Re-grading stored stock between two conditions of the same material.

The backend admin triggers this, but the move happens HERE because Odoo owns
the quantities — the backend only mirrors them, and a move it made on its own
side was overwritten by the next inventory sync. Four invariants are protected:

  * The warehouse TOTAL never changes — units are re-labelled, not created or
    destroyed. This is the whole point of a re-grade and the first thing that
    would break if the two rows were not kept in step.
  * Only UNRESERVED quantity moves. Reserved stock is promised to an order that
    has not shipped; re-labelling it would leave that order pointing at a grade
    its goods are no longer in.
  * A grade belongs to ONE material — a code is unique only within its material.
  * The source row SURVIVES emptying — an empty grade is still one the material
    is sold at.
"""
from .common import make_warehouse
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestGradeTransfer(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = make_warehouse(cls.env, **{
            'name': 'Transfer Test Warehouse', 'code': 'TTW1',
        })
        cls.zone = cls.env['recycle.zone'].create({
            'name': 'Storage T', 'warehouse_id': cls.warehouse.id,
            'zone_type': 'storage',
        })
        cls.zone_b = cls.env['recycle.zone'].create({
            'name': 'Storage T2', 'warehouse_id': cls.warehouse.id,
            'zone_type': 'storage',
        })
        cls.category = cls.env['recycle.product.category'].create(
            {'name': 'Transfer Test Category'})
        Unit = cls.env['recycle.measurement.unit']
        cls.kg = Unit.search([('code', '=', 'KG')], limit=1) or Unit.create(
            {'code': 'KG', 'name': 'Kilogram', 'allows_tolerance': True})
        cls.product = cls.env['recycle.product'].create({
            'name': 'Transfer Test Material', 'category_id': cls.category.id,
            'uom_id': cls.kg.id,
        })
        Condition = cls.env['recycle.material.condition']
        cls.good = Condition.create({
            'product_id': cls.product.id, 'code': 'GOOD',
            'name': 'Good', 'sort_order': 2,
        })
        cls.excellent = Condition.create({
            'product_id': cls.product.id, 'code': 'EXCELLENT',
            'name': 'Excellent', 'sort_order': 1,
        })
        # A DIFFERENT material, whose 'GOOD' is a different thing entirely.
        cls.other = cls.env['recycle.product'].create({
            'name': 'Other Material', 'category_id': cls.category.id,
            'uom_id': cls.kg.id,
        })
        cls.env['recycle.material.condition'].create({
            'product_id': cls.other.id, 'code': 'GOOD',
            'name': 'Good', 'sort_order': 1,
        })

    def setUp(self):
        super().setUp()
        self.env['recycle.stock'].search([
            ('warehouse_id', '=', self.warehouse.id)]).unlink()

    def _stock(self, qty, condition='GOOD', reserved=0.0, zone=None, product=None):
        line = self.env['recycle.stock'].create({
            'warehouse_id': self.warehouse.id,
            'product_id': (product or self.product).id,
            'zone_id': (zone or self.zone).id,
            'condition': condition,
            'quantity': qty,
        })
        if reserved:
            line.reserved_qty = reserved
        return line

    def _qty_of(self, condition):
        return sum(self.env['recycle.stock'].search([
            ('warehouse_id', '=', self.warehouse.id),
            ('product_id', '=', self.product.id),
            ('condition', '=', condition)]).mapped('quantity'))

    def _total(self):
        return sum(self.env['recycle.stock'].search([
            ('warehouse_id', '=', self.warehouse.id),
            ('product_id', '=', self.product.id)]).mapped('quantity'))

    def _transfer(self, qty, frm='GOOD', to='EXCELLENT'):
        return self.env['recycle.stock'].transfer_grade(
            self.warehouse.id, self.product.id, frm, to, qty)

    # ------------------------------------------------------------------
    # The total is preserved — the heart of the feature
    # ------------------------------------------------------------------
    def test_regrade_moves_quantity_and_keeps_the_warehouse_total(self):
        self._stock(100, 'GOOD')

        res = self._transfer(40)

        self.assertTrue(res['transferred'])
        self.assertEqual(self._qty_of('GOOD'), 60)
        self.assertEqual(self._qty_of('EXCELLENT'), 40)
        # Nothing was created or destroyed — only re-labelled.
        self.assertEqual(self._total(), 100)

    def test_regrade_adds_to_an_existing_destination_grade(self):
        self._stock(100, 'GOOD')
        self._stock(10, 'EXCELLENT')

        self._transfer(30)

        self.assertEqual(self._qty_of('GOOD'), 70)
        self.assertEqual(self._qty_of('EXCELLENT'), 40)
        self.assertEqual(self._total(), 110)

    def test_regrade_stays_within_the_same_zone(self):
        """Material does not physically move — its label changes. So the
        destination lands in the SAME zone the source sat in."""
        self._stock(50, 'GOOD', zone=self.zone_b)

        self._transfer(50)

        dest = self.env['recycle.stock'].search([
            ('warehouse_id', '=', self.warehouse.id),
            ('product_id', '=', self.product.id),
            ('condition', '=', 'EXCELLENT')])
        self.assertEqual(dest.zone_id, self.zone_b)

    # ------------------------------------------------------------------
    # Reserved stock is untouchable
    # ------------------------------------------------------------------
    def test_only_unreserved_quantity_moves(self):
        # 100 held, 30 reserved → 70 movable.
        self._stock(100, 'GOOD', reserved=30)

        res = self._transfer(70)

        self.assertTrue(res['transferred'])
        self.assertEqual(self._qty_of('GOOD'), 30)
        self.assertEqual(self._qty_of('EXCELLENT'), 70)
        self.assertEqual(self._total(), 100)

    def test_a_request_beyond_the_unreserved_quantity_is_refused(self):
        # 71 of 70 movable: the extra is promised to an order.
        self._stock(100, 'GOOD', reserved=30)

        res = self._transfer(71)

        self.assertFalse(res['transferred'])
        self.assertEqual(res['movable'], 70)
        # Nothing moved.
        self.assertEqual(self._qty_of('GOOD'), 100)
        self.assertEqual(self._qty_of('EXCELLENT'), 0)

    # ------------------------------------------------------------------
    # Grade identity
    # ------------------------------------------------------------------
    def test_a_grade_of_another_material_is_refused(self):
        self._stock(100, 'GOOD')
        with self.assertRaises(UserError):
            self.env['recycle.stock'].transfer_grade(
                self.warehouse.id, self.product.id, 'GOOD', 'NOPE', 10)

    def test_same_source_and_destination_is_refused(self):
        self._stock(100, 'GOOD')
        with self.assertRaises(UserError):
            self._transfer(10, frm='GOOD', to='GOOD')

    def test_codes_are_matched_case_insensitively(self):
        self._stock(100, 'GOOD')
        res = self._transfer(20, frm='good', to='excellent')
        self.assertTrue(res['transferred'])
        self.assertEqual(self._qty_of('EXCELLENT'), 20)

    # ------------------------------------------------------------------
    # The source grade survives emptying
    # ------------------------------------------------------------------
    def test_the_source_grade_row_survives_when_emptied(self):
        line = self._stock(100, 'GOOD')

        self._transfer(100)

        self.assertTrue(line.exists(), 'an emptied grade is still a grade sold')
        self.assertEqual(self._qty_of('GOOD'), 0)
        self.assertEqual(self._qty_of('EXCELLENT'), 100)
        self.assertEqual(self._total(), 100)
