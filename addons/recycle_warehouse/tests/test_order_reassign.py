# -*- coding: utf-8 -*-
"""Re-routing one part of a split order to another warehouse.

Deciding a split is the administrator's, and part of that is correcting a
warehouse the allocator chose. It is bounded on purpose, and every bound is a
way it would otherwise go wrong:

  * only a SPLIT part, and only the administrator;
  * only BEFORE the decision (still pending);
  * the order is never GROWN — the target may not already hold a sibling, so the
    number of warehouses stays exactly what the allocator decided;
  * the target must actually hold the quantity.

And the reservation travels with the part: released where it was, taken where it
goes, so no stock is promised twice and none is stranded.
"""
from odoo.exceptions import UserError
from .common import make_warehouse
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestOrderReassign(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls.env['recycle.product.category'].create(
            {'name': 'Reassign Cat'})
        Unit = cls.env['recycle.measurement.unit']
        cls.kg = Unit.search([('code', '=', 'KG')], limit=1) or Unit.create(
            {'code': 'KG', 'name': 'Kilogram', 'allows_tolerance': True})
        cls.product = cls.env['recycle.product'].create({
            'name': 'Reassign Material', 'category_id': cls.category.id,
            'uom_id': cls.kg.id,
        })
        cls.env['recycle.product.condition.price'].create([
            {'product_id': cls.product.id, 'tier': 'factory', 'price': 10.0},
            {'product_id': cls.product.id, 'tier': 'free_facility', 'price': 8.0},
        ])
        cls.wh_a = make_warehouse(cls.env, {'name': 'Reassign A', 'code': 'RA'})
        cls.wh_b = make_warehouse(cls.env, {'name': 'Reassign B', 'code': 'RB'})
        cls.wh_c = make_warehouse(cls.env, {'name': 'Reassign C', 'code': 'RC'})

        cls.admin = cls.env['res.users'].create({
            'name': 'Reassign Admin', 'login': 'reassign.admin@example.com',
            'group_ids': [(4, cls.env.ref(
                'recycle_warehouse.group_recycle_admin').id)],
        })
        cls.manager = cls.env['res.users'].create({
            'name': 'Reassign Mgr', 'login': 'reassign.mgr@example.com',
            'group_ids': [(4, cls.env.ref(
                'recycle_warehouse.group_recycle_manager').id)],
        })

    def setUp(self):
        super().setUp()
        Stock = self.env['recycle.stock']
        Stock.search([('product_id', '=', self.product.id)]).unlink()
        # A and C can supply the part (20 each); B is where a sibling sits.
        Stock._add_quantity(self.wh_a, self.product, 20.0)
        Stock._add_quantity(self.wh_c, self.product, 20.0)

    def _available(self, warehouse):
        return self.env['recycle.stock']._available_qty(warehouse, self.product)

    def _part(self, warehouse, order_id, sequence, count):
        return self.env['recycle.order'].sudo().create({
            'backend_part_id': '%s-p%s' % (order_id, sequence),
            'backend_order_id': order_id,
            'part_sequence': sequence,
            'part_count': count,
            'customer_name': 'Reassign Buyer',
            'warehouse_id': warehouse.id,
            'order_type': 'factory',
            'source': 'nextjs',
            'manager_approval': 'pending',
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 5.0,
                'price_unit': 10.0,
            })],
        })

    def _reserved_split(self, order_id='ORD-RA-1'):
        """A split whose part in A holds a real reservation."""
        part_a = self._part(self.wh_a, order_id, 1, 2)
        part_b = self._part(self.wh_b, order_id, 2, 2)
        self.env['recycle.stock'].reserve_for_order(
            self.wh_a.id, part_a._reservation_lines())
        part_a.stock_reserved = True
        return part_a, part_b

    # ------------------------------------------------------------------
    # The move, and the reservation travelling with it
    # ------------------------------------------------------------------
    def test_admin_reassigns_and_the_reservation_moves(self):
        part_a, _ = self._reserved_split()
        self.assertEqual(self._available(self.wh_a), 15)  # 20 − 5 reserved

        part_a.with_user(self.admin).action_admin_reassign_warehouse(self.wh_c.id)

        self.assertEqual(part_a.warehouse_id, self.wh_c)
        self.assertTrue(part_a.stock_reserved)
        # A gets its 5 back; C now holds the reservation.
        self.assertEqual(self._available(self.wh_a), 20)
        self.assertEqual(self._available(self.wh_c), 15)

    # ------------------------------------------------------------------
    # The bounds
    # ------------------------------------------------------------------
    def test_only_the_admin_may_reassign(self):
        part_a, _ = self._reserved_split()
        with self.assertRaises(UserError):
            part_a.with_user(self.manager).action_admin_reassign_warehouse(
                self.wh_c.id)

    def test_a_single_warehouse_order_cannot_be_reassigned(self):
        single = self._part(self.wh_a, False, 1, 1)  # no backend_order_id → single
        self.assertFalse(single.is_split_part)
        with self.assertRaises(UserError):
            single.with_user(self.admin).action_admin_reassign_warehouse(
                self.wh_c.id)

    def test_cannot_reassign_onto_a_sibling_warehouse(self):
        # B already holds the other part — merging is not the same as re-routing.
        part_a, _ = self._reserved_split()
        with self.assertRaises(UserError):
            part_a.with_user(self.admin).action_admin_reassign_warehouse(
                self.wh_b.id)

    def test_cannot_reassign_to_a_warehouse_without_the_quantity(self):
        part_a, _ = self._reserved_split()
        # Empty C out; it can no longer cover the part.
        self.env['recycle.stock'].search([
            ('warehouse_id', '=', self.wh_c.id),
            ('product_id', '=', self.product.id)]).write({'quantity': 1.0})
        with self.assertRaises(UserError):
            part_a.with_user(self.admin).action_admin_reassign_warehouse(
                self.wh_c.id)
        # Nothing moved.
        self.assertEqual(part_a.warehouse_id, self.wh_a)

    def test_cannot_reassign_once_approved(self):
        part_a, part_b = self._reserved_split()
        part_a.with_user(self.admin).action_manager_approve()
        with self.assertRaises(UserError):
            part_a.with_user(self.admin).action_admin_reassign_warehouse(
                self.wh_c.id)
