# -*- coding: utf-8 -*-
"""What the OUTPUT employee's order screen is handed, per material line.

Three things this pins down, each a real bug the screen showed before:

  - A material with NO grades must carry NO condition. The endpoint used to
    default an empty grade to 'good', so an ungraded material appeared "Good".
    `condition` is now False and `has_conditions` (authored in the backend,
    mirrored as recycle.material.condition) says plainly whether the material is
    graded at all.

  - Every line names its own UNIT of measure, so a "piece" count is never read
    as kilograms.

  - Every line also carries its KG equivalent (quantity x weight-per-unit) — the
    same basis a shipment's load weight uses — so a non-kg quantity shows how
    much it actually weighs.
"""
import json

from odoo.tests.common import HttpCase, tagged

from .common import make_warehouse


@tagged('post_install', '-at_install')
class TestOutputOrderDetail(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.wh = make_warehouse(cls.env, **{
            'name': 'Output Detail WH', 'code': 'OUTDETWH'})
        cls.category = cls.env['recycle.product.category'].create(
            {'name': 'Output Detail Cat'})

        Unit = cls.env['recycle.measurement.unit']
        cls.kg = Unit.search([('code', '=', 'KG')], limit=1) or Unit.create(
            {'code': 'KG', 'name': 'Kilogram', 'allows_tolerance': True})
        cls.piece = Unit.search([('code', '=', 'PIECE')], limit=1) or Unit.create(
            {'code': 'PIECE', 'name': 'Piece', 'allows_tolerance': False})

        # Graded material (has grades) — measured in kg.
        cls.graded = cls.env['recycle.product'].create({
            'name': 'Graded Copper', 'category_id': cls.category.id,
            'uom_id': cls.kg.id, 'price_factory': 5.0})
        Condition = cls.env['recycle.material.condition']
        Condition.create({'product_id': cls.graded.id, 'code': 'PREMIUM',
                          'name': 'Premium', 'sort_order': 1})

        # Ungraded material — measured in kg, no grades at all.
        cls.plain = cls.env['recycle.product'].create({
            'name': 'Plain Paper', 'category_id': cls.category.id,
            'uom_id': cls.kg.id, 'price_factory': 2.0})

        # Ungraded material measured in PIECES, each weighing 2.5 kg.
        cls.counted = cls.env['recycle.product'].create({
            'name': 'Car Battery', 'category_id': cls.category.id,
            'uom_id': cls.piece.id, 'weight': 2.5, 'price_factory': 30.0})

        cls.order = cls.env['recycle.order'].create({
            'customer_name': 'Test Factory',
            'owner_name': 'Owner',
            'customer_email': 'factory@test.local',
            'warehouse_id': cls.wh.id,
            'order_type': 'factory',
            'state': 'pending',
            'manager_approval': 'approved',
            'line_ids': [
                (0, 0, {'product_id': cls.graded.id, 'quantity': 10.0,
                        'condition': 'PREMIUM', 'price_unit': 5.0}),
                (0, 0, {'product_id': cls.plain.id, 'quantity': 5.0,
                        'price_unit': 2.0}),
                (0, 0, {'product_id': cls.counted.id, 'quantity': 4.0,
                        'price_unit': 30.0}),
            ],
        })

        cls.emp = cls.env['res.users'].create({
            'name': 'Output Emp',
            'login': 'output.detail@test.local',
            'password': 'output-detail-pw-1',
            'recycle_role': 'output',
            'recycle_warehouse_id': cls.wh.id,
            'group_ids': [(4, cls.env.ref(
                'recycle_warehouse.group_recycle_output').id)],
        })

    def setUp(self):
        super().setUp()
        self.authenticate('output.detail@test.local', 'output-detail-pw-1')

    def _detail(self):
        res = self.url_open(
            '/api/output/order/%s' % self.order.id,
            data=json.dumps({'jsonrpc': '2.0', 'method': 'call', 'params': {}}),
            headers={'Content-Type': 'application/json'},
        )
        self.assertEqual(res.status_code, 200, res.text)
        return res.json().get('result') or {}

    def _line_for(self, detail, product_name):
        for ln in detail.get('lines', []):
            if ln.get('product_name') == product_name:
                return ln
        self.fail('line not found for %r' % product_name)

    # ------------------------------------------------------------------
    def test_graded_material_carries_its_grade(self):
        graded = self._line_for(self._detail(), 'Graded Copper')
        self.assertEqual(graded['condition'], 'PREMIUM')
        self.assertTrue(graded['has_conditions'])
        self.assertEqual(graded['unit'], 'Kilogram')

    def test_ungraded_material_carries_no_grade(self):
        # The bug: this used to come back as 'good'.
        plain = self._line_for(self._detail(), 'Plain Paper')
        self.assertFalse(plain['condition'])
        self.assertFalse(plain['has_conditions'])

    def test_a_piece_line_reports_its_unit_and_kg_equivalent(self):
        counted = self._line_for(self._detail(), 'Car Battery')
        self.assertEqual(counted['unit'], 'Piece')
        self.assertFalse(counted['has_conditions'])
        # 4 pieces x 2.5 kg = 10 kg, the same basis a shipment load uses.
        self.assertEqual(counted['weight_kg'], 10.0)
