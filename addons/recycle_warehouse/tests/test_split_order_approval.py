# -*- coding: utf-8 -*-
"""A split buyer order is one decision, taken by the administrator.

A buyer order no single warehouse can fill is broken into parts, and each part
arrives in Odoo as its own order in its own warehouse. Letting each warehouse
manager decide their own piece has two failure modes, and both end with the
buyer waiting on a state nobody chose:

  * one manager approves and another rejects — the order is half promised, and
    no one is answerable for the whole;
  * one manager approves and the others simply have not looked yet — the buyer
    sees movement on an order that cannot complete.

There is exactly one person who can see every part, so the decision is theirs.
And when they take it, it applies to ALL the parts in one transaction —
approving them one at a time is the same failure arriving by another route.
"""
from odoo.exceptions import UserError
from .common import make_warehouse
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSplitOrderApproval(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls.env['recycle.product.category'].create(
            {'name': 'Split Cat'})
        _unit = cls.env['recycle.measurement.unit']
        cls._kg = _unit.search([('code', '=', 'KG')], limit=1) or _unit.create(
            {'code': 'KG', 'name': 'Kilogram', 'allows_tolerance': True})
        cls.product = cls.env['recycle.product'].create({
            'name': 'Split Material', 'category_id': cls.category.id,
            'uom_id': cls._kg.id,
        })
        # A material with NO price rows is suspended and cannot be ordered —
        # the push refuses it at the door rather than at the invoice, after the
        # goods would already have been picked. So give it a price list.
        cls.env['recycle.product.condition.price'].create([
            {'product_id': cls.product.id, 'tier': 'factory', 'price': 10.0},
            {'product_id': cls.product.id, 'tier': 'free_facility', 'price': 8.0},
        ])
        cls.wh_a = make_warehouse(cls.env, 
            {'name': 'Split WH A', 'code': 'SPLITA'})
        cls.wh_b = make_warehouse(cls.env, 
            {'name': 'Split WH B', 'code': 'SPLITB'})

        cls.manager = cls.env['res.users'].create({
            'name': 'Split Manager',
            'login': 'split.manager@example.com',
            'group_ids': [(4, cls.env.ref(
                'recycle_warehouse.group_recycle_manager').id)],
        })
        cls.manager.recycle_warehouse_id = cls.wh_a.id

        cls.admin = cls.env['res.users'].create({
            'name': 'Split Admin',
            'login': 'split.admin@example.com',
            'group_ids': [(4, cls.env.ref(
                'recycle_warehouse.group_recycle_admin').id)],
        })

    def _part(self, warehouse, order_id, sequence, count):
        return self.env['recycle.order'].sudo().create({
            'backend_part_id': '%s-p%s' % (order_id, sequence),
            'backend_order_id': order_id,
            'part_sequence': sequence,
            'part_count': count,
            'customer_name': 'Split Buyer',
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

    def _split_order(self, order_id='ORD-SPLIT-1'):
        return (self._part(self.wh_a, order_id, 1, 2),
                self._part(self.wh_b, order_id, 2, 2))

    # ------------------------------------------------------------------
    def test_parts_of_one_order_know_they_are_split(self):
        part_a, part_b = self._split_order('ORD-SPLIT-FLAG')
        self.assertTrue(part_a.is_split_part)
        self.assertTrue(part_b.is_split_part)
        self.assertEqual(set(part_a.sibling_parts().ids),
                         {part_a.id, part_b.id})

    def test_a_single_warehouse_order_is_not_split(self):
        """The common case must be untouched — one warehouse, one manager."""
        order = self._part(self.wh_a, 'ORD-SOLO', 1, 1)
        self.assertFalse(order.is_split_part)
        self.assertEqual(order.sibling_parts().ids, order.ids)

    def test_a_manager_cannot_approve_a_split_part(self):
        part_a, _part_b = self._split_order('ORD-SPLIT-MGR')
        with self.assertRaises(UserError):
            part_a.with_user(self.manager).action_manager_approve()

    def test_a_manager_cannot_reject_a_split_part(self):
        part_a, _part_b = self._split_order('ORD-SPLIT-MGR-REJ')
        with self.assertRaises(UserError):
            part_a.with_user(self.manager).action_manager_reject('no')

    def test_a_manager_still_decides_their_own_single_warehouse_order(self):
        """The rule narrows nothing it was not meant to narrow."""
        order = self._part(self.wh_a, 'ORD-SOLO-MGR', 1, 1)
        order.with_user(self.manager).action_manager_approve()
        self.assertEqual(order.manager_approval, 'approved')

    def test_the_admin_approves_EVERY_part_at_once(self):
        part_a, part_b = self._split_order('ORD-SPLIT-APPROVE')

        part_a.with_user(self.admin).action_manager_approve()

        self.assertEqual(part_a.manager_approval, 'approved')
        self.assertEqual(part_b.manager_approval, 'approved',
                         'the other warehouse was left un-approved')

    def test_the_admin_rejects_EVERY_part_at_once(self):
        """Rejecting one piece would leave the others holding stock reserved
        for an order that can never complete."""
        part_a, part_b = self._split_order('ORD-SPLIT-REJECT')

        part_b.with_user(self.admin).action_manager_reject('out of stock')

        self.assertEqual(part_a.manager_approval, 'rejected')
        self.assertEqual(part_b.manager_approval, 'rejected')

    def test_approving_an_already_approved_split_is_refused(self):
        part_a, _part_b = self._split_order('ORD-SPLIT-TWICE')
        part_a.with_user(self.admin).action_manager_approve()
        with self.assertRaises(UserError):
            part_a.with_user(self.admin).action_manager_approve()

    # ------------------------------------------------------------------
    # Reaching the output employees
    # ------------------------------------------------------------------
    def _push_part(self, warehouse, order_id, sequence, count):
        """Create through the BACKEND entry point, not with a raw write.

        The priority is set there, and a test that wrote it by hand would be
        asserting its own input.
        """
        return self.env['recycle.order'].sudo().backend_upsert_part({
            'part_id': '%s-p%s' % (order_id, sequence),
            'order_id': order_id,
            'part_sequence': sequence,
            'part_count': count,
            'customer_name': 'Split Buyer',
            'warehouse_odoo_id': warehouse.id,
            'order_type': 'factory',
            'lines': [{
                'product_odoo_id': self.product.id,
                'quantity': 3.0,
                'price_unit': 10.0,
            }],
        })

    def test_a_split_part_outranks_ordinary_orders_in_the_output_queue(self):
        """The buyer waits on the SLOWEST part.

        A part queued behind an ordinary single-warehouse order is not one part
        running late — it holds the whole order, while the two warehouses that
        already finished store prepared goods that cannot leave.
        """
        split = self._push_part(self.wh_a, 'ORD-PRIO-SPLIT', 1, 3)
        solo = self._push_part(self.wh_a, 'ORD-PRIO-SOLO', 1, 1)

        split_order = self.env['recycle.order'].sudo().browse(split['odoo_id'])
        solo_order = self.env['recycle.order'].sudo().browse(solo['odoo_id'])

        self.assertLess(split_order.priority, solo_order.priority)

    def test_every_part_of_a_split_is_prioritised_in_its_own_warehouse(self):
        """Parallel preparation is the whole point.

        Prioritising only the first part would serialise the split — the very
        thing splitting it was meant to avoid.
        """
        first = self._push_part(self.wh_a, 'ORD-PRIO-ALL', 1, 2)
        second = self._push_part(self.wh_b, 'ORD-PRIO-ALL', 2, 2)

        Order = self.env['recycle.order'].sudo()
        self.assertEqual(
            {Order.browse(first['odoo_id']).priority,
             Order.browse(second['odoo_id']).priority},
            {1})

    def test_an_approved_split_part_is_visible_to_output_employees(self):
        """Approval is the ONLY gate.

        The output queue selects on `manager_approval = 'approved'`, so nothing
        further has to happen for the part to appear — and nothing further
        should, or the admin's decision would not be the decision.
        """
        pushed = self._push_part(self.wh_a, 'ORD-PRIO-VISIBLE', 1, 2)
        order = self.env['recycle.order'].sudo().browse(pushed['odoo_id'])
        self.assertEqual(order.manager_approval, 'pending')

        order.with_user(self.admin).action_manager_approve()

        queue = self.env['recycle.order'].sudo().search([
            ('warehouse_id', '=', self.wh_a.id),
            ('manager_approval', '=', 'approved'),
            ('state', '=', 'pending'),
        ], order='priority asc, create_date desc')
        self.assertIn(order, queue)
        self.assertEqual(queue[0].priority, 1,
                         'a split part is not at the head of the queue')

    def test_the_decision_reaches_parts_in_warehouses_the_admin_is_not_in(self):
        """The sibling lookup runs as sudo on purpose.

        The parts sit in different warehouses; a record rule scoping to the
        reader's own would return a "whole" that is only one piece, and the
        approval would cover one part while reporting that it covered the
        order — the worst of the three outcomes, because it looks correct.
        """
        part_a, part_b = self._split_order('ORD-SPLIT-SCOPE')
        self.assertNotEqual(part_a.warehouse_id, part_b.warehouse_id)

        part_a.with_user(self.admin).action_manager_approve()

        self.assertEqual(
            set(part_a.sibling_parts().mapped('manager_approval')),
            {'approved'})
