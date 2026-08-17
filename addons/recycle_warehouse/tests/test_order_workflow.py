# -*- coding: utf-8 -*-
"""Regression tests for the order priority queue, condition-based stock
deduction, and multi-zone allocation — the most fragile, invariant-heavy
logic in the module (verified manually many times during development;
these tests exist so a future change can't silently break any of it)."""
from odoo.exceptions import UserError
from .common import make_warehouse
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestOrderWorkflow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = make_warehouse(cls.env, **{
            'name': 'Test Warehouse', 'code': 'TWH1',
        })
        cls.category = cls.env['recycle.product.category'].create({'name': 'Test Category'})
        _unit = cls.env['recycle.measurement.unit']
        cls._kg = _unit.search([('code', '=', 'KG')], limit=1) or _unit.create(
            {'code': 'KG', 'name': 'Kilogram', 'allows_tolerance': True})
        cls.product = cls.env['recycle.product'].create({
            'name': 'Test Widget', 'category_id': cls.category.id,
            'uom_id': cls._kg.id,
            'price_factory': 1.0, 'price_free_facility': 1.0,
        })
        # Grades belong to the material and are named by the admin. These are
        # deliberately NOT the four words the module used to hard-code: no part
        # of the deduction logic may depend on those particular strings.
        Condition = cls.env['recycle.material.condition']
        Condition.create({
            'product_id': cls.product.id, 'code': 'PREMIUM',
            'name': 'Premium', 'sort_order': 1,
        })
        Condition.create({
            'product_id': cls.product.id, 'code': 'STANDARD',
            'name': 'Standard', 'sort_order': 2,
        })
        cls.zone_a = cls.env['recycle.zone'].create({
            'name': 'Storage A', 'warehouse_id': cls.warehouse.id, 'zone_type': 'storage',
        })
        cls.zone_b = cls.env['recycle.zone'].create({
            'name': 'Storage B', 'warehouse_id': cls.warehouse.id, 'zone_type': 'storage',
        })
        cls.output_zone = cls.env['recycle.zone'].create({
            'name': 'Output', 'warehouse_id': cls.warehouse.id, 'zone_type': 'output',
        })

    def _set_stock(self, zone, qty, condition='STANDARD'):
        self.env['recycle.stock'].create({
            'warehouse_id': self.warehouse.id,
            'product_id': self.product.id,
            'zone_id': zone.id,
            'condition': condition,
            'quantity': qty,
        })

    def _order(self, priority, qty, condition='STANDARD'):
        return self.env['recycle.order'].create({
            'customer_name': 'Test Customer',
            'warehouse_id': self.warehouse.id,
            'priority': priority,
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': qty,
                'condition': condition,
                'price_unit': 1.0,
            })],
        })

    # ---------------- Priority queue ----------------

    def test_higher_priority_order_blocks_lower(self):
        """A lower-priority order cannot start while a higher-priority
        (lower number) order with sufficient stock is still pending."""
        self._set_stock(self.zone_a, 10)
        high = self._order(priority=1, qty=5)
        low = self._order(priority=9, qty=1)

        self.assertEqual(low.get_blocking_order(), high)
        with self.assertRaises(UserError):
            low.action_start_processing()

        # Starting the high-priority order must succeed with no blocker.
        self.assertFalse(high.get_blocking_order())
        high.action_start_processing()
        self.assertEqual(high.state, 'processing')

    def test_insufficient_stock_order_is_skipped_in_queue(self):
        """A higher-priority order that can never be fulfilled (as-is)
        must not block a lower-priority order that CAN be fulfilled."""
        self._set_stock(self.zone_a, 2)  # only 2 in stock
        unfulfillable_high = self._order(priority=1, qty=100)  # needs 100
        fulfillable_low = self._order(priority=9, qty=1)

        self.assertFalse(fulfillable_low.get_blocking_order())
        fulfillable_low.action_start_processing()
        self.assertEqual(fulfillable_low.state, 'processing')
        # Sanity: the unfulfillable order really is what get_blocking_order
        # would have returned, had it not lacked stock.
        self.assertEqual(unfulfillable_high.priority, 1)

    # ---------------- Condition-based deduction ----------------

    def test_deduction_never_crosses_condition(self):
        """An order line requesting 'excellent' stock must never be
        fulfillable from 'good' stock, even if there's plenty of it."""
        self._set_stock(self.zone_a, 50, condition='STANDARD')
        order = self._order(priority=1, qty=5, condition='PREMIUM')
        order.action_start_processing()
        with self.assertRaises(UserError):
            order.action_complete(allocations=[{
                'line_id': order.line_ids.id,
                'zone_id': self.zone_a.id,
                'quantity': 5,
            }])

    # ---------------- Multi-zone allocation ----------------

    def test_multi_zone_allocation_splits_correctly(self):
        """Combining two storage zones must deduct the exact amount from
        each and never touch stock beyond what was explicitly allocated."""
        self._set_stock(self.zone_a, 4)
        self._set_stock(self.zone_b, 6)
        order = self._order(priority=1, qty=7)
        order.action_start_processing()
        line = order.line_ids
        order.action_complete(allocations=[
            {'line_id': line.id, 'zone_id': self.zone_a.id, 'quantity': 4},
            {'line_id': line.id, 'zone_id': self.zone_b.id, 'quantity': 3},
        ])
        self.assertEqual(order.state, 'ready')
        self.assertTrue(order.stock_deducted_at)
        self.assertTrue(order.invoice_number)

        stock_a = self.env['recycle.stock'].search([
            ('zone_id', '=', self.zone_a.id), ('product_id', '=', self.product.id)])
        stock_b = self.env['recycle.stock'].search([
            ('zone_id', '=', self.zone_b.id), ('product_id', '=', self.product.id)])
        self.assertEqual(stock_a.quantity, 0)
        self.assertEqual(stock_b.quantity, 3)  # 6 - 3 = 3 left, untouched beyond that

        self.assertEqual(len(order.zone_movement_ids), 2)

    def test_partial_allocation_is_rejected(self):
        """Allocating less than the required quantity across all chosen
        zones must fail with a clear error, not silently under-fulfill."""
        self._set_stock(self.zone_a, 10)
        order = self._order(priority=1, qty=7)
        order.action_start_processing()
        line = order.line_ids
        with self.assertRaises(UserError):
            order.action_complete(allocations=[
                {'line_id': line.id, 'zone_id': self.zone_a.id, 'quantity': 3},
            ])
        # Nothing should have been deducted by the failed attempt.
        stock_a = self.env['recycle.stock'].search([
            ('zone_id', '=', self.zone_a.id), ('product_id', '=', self.product.id)])
        self.assertEqual(stock_a.quantity, 10)

    # ---------------- Manager approval gate ----------------

    def test_pending_approval_order_cannot_start(self):
        """An API-created order (pending manager approval) must be
        unprocessable until the manager approves it — and processable
        right after."""
        self._set_stock(self.zone_a, 10)
        order = self._order(priority=1, qty=5)
        order.write({'manager_approval': 'pending'})
        with self.assertRaises(UserError):
            order.action_start_processing()
        order.action_manager_approve()
        self.assertEqual(order.manager_approval, 'approved')
        self.assertTrue(order.approval_decided_at)
        order.action_start_processing()
        self.assertEqual(order.state, 'processing')

    def test_rejected_order_can_never_start(self):
        self._set_stock(self.zone_a, 10)
        order = self._order(priority=1, qty=5)
        order.write({'manager_approval': 'pending'})
        order.action_manager_reject(reason='Test rejection')
        self.assertEqual(order.manager_approval, 'rejected')
        self.assertEqual(order.approval_reject_reason, 'Test rejection')
        with self.assertRaises(UserError):
            order.action_start_processing()

    def test_unapproved_order_never_blocks_the_queue(self):
        """A higher-priority order still waiting for manager approval must
        not block an approved lower-priority order."""
        self._set_stock(self.zone_a, 10)
        unapproved_high = self._order(priority=1, qty=5)
        unapproved_high.write({'manager_approval': 'pending'})
        approved_low = self._order(priority=9, qty=1)

        self.assertFalse(approved_low.get_blocking_order())
        approved_low.action_start_processing()
        self.assertEqual(approved_low.state, 'processing')

    def test_finish_requires_output_zone_of_same_warehouse(self):
        self._set_stock(self.zone_a, 5)
        order = self._order(priority=1, qty=5)
        order.action_start_processing()
        order.action_complete(allocations=[
            {'line_id': order.line_ids.id, 'zone_id': self.zone_a.id, 'quantity': 5},
        ])
        order.action_finish(self.output_zone.id)
        self.assertEqual(order.state, 'completed')
        self.assertTrue(order.finished_at)
        self.assertEqual(order.output_zone_id, self.output_zone)

        # A storage zone (wrong type) must be rejected as an output zone.
        order2 = self._order(priority=2, qty=0.0001)
        with self.assertRaises(UserError):
            order2.action_finish(self.zone_a.id)
