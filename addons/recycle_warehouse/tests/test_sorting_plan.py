# -*- coding: utf-8 -*-
"""What the sorter may enter, and what the shipment says was lost.

Two rules, both decided by the SERVER so the screen cannot drift from them:

  1. A material may only be sorted for what the shipment DECLARED — never
     more, and never a material the lorry did not carry. The picker used to
     offer the whole catalogue, so a sorter could log something that never
     arrived, and the mistake surfaced as stock nobody could account for.

  2. The LOST quantity is `declared − entered`, per material and per unit of
     measure. It is NOT `damage_pct`, which counts goods that DID arrive and
     were found unusable — those are on the warehouse floor waiting to be
     written off, while lost goods never came off the lorry. A shipment that
     arrived complete-but-damaged and one that arrived short are different
     events, and one number cannot describe both.

A grade that did not arrive is entered as ZERO on purpose: it records that the
grade was looked for and not found, and it keeps the sum of a material's grades
comparable with what was declared.
"""
from odoo.exceptions import ValidationError
from .common import make_warehouse
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSortingPlan(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = make_warehouse(cls.env, 
            {'name': 'Sort Plan WH', 'code': 'SORTPLAN'})
        cls.category = cls.env['recycle.product.category'].create(
            {'name': 'Sort Plan Cat'})

        Unit = cls.env['recycle.measurement.unit']
        cls.kg = Unit.search([('code', '=', 'KG')], limit=1) or Unit.create(
            {'code': 'KG', 'name': 'Kilogram', 'allows_tolerance': True})
        cls.piece = Unit.search([('code', '=', 'PIECE')], limit=1) or Unit.create(
            {'code': 'PIECE', 'name': 'Piece', 'allows_tolerance': False})

        Product = cls.env['recycle.product']
        cls.plain = Product.create({
            'name': 'Sort Plain', 'category_id': cls.category.id,
            'uom_id': cls.kg.id,
        })
        cls.graded = Product.create({
            'name': 'Sort Graded', 'category_id': cls.category.id,
            'uom_id': cls.kg.id,
        })
        Condition = cls.env['recycle.material.condition']
        for index, code in enumerate(('EXCELLENT', 'GOOD', 'FAIR')):
            Condition.create({
                'product_id': cls.graded.id,
                'code': code, 'name': code.title(), 'sort_order': index,
            })

    def _shipment(self, declared):
        """`declared` is [(product, qty), …]."""
        shipment = self.env['recycle.shipment'].create({
            'warehouse_id': self.warehouse.id,
            'driver_name': 'Sort Plan Driver',
            'state': 'sorting',
        })
        for product, qty in declared:
            self.env['recycle.shipment.expected.line'].create({
                'shipment_id': shipment.id,
                'product_id': product.id,
                'expected_qty': qty,
            })
        return shipment

    def _line(self, shipment, product, qty, condition=False):
        return self.env['recycle.shipment.line'].create({
            'shipment_id': shipment.id,
            'product_id': product.id,
            'quantity': qty,
            'condition': condition,
        })

    # ------------------------------------------------------------------
    # The plan
    # ------------------------------------------------------------------
    def test_the_plan_offers_only_what_the_shipment_declared(self):
        shipment = self._shipment([(self.plain, 100.0)])
        plan = shipment.get_sorting_plan()['plan']

        self.assertEqual([p['product_id'] for p in plan], [self.plain.id])
        self.assertEqual(plan[0]['remaining_qty'], 100.0)
        self.assertEqual(plan[0]['uom_name'], self.kg.name)

    def test_an_ungraded_material_is_complete_once_a_quantity_is_logged(self):
        """One number to give, and it has been given."""
        shipment = self._shipment([(self.plain, 100.0)])
        self._line(shipment, self.plain, 90.0)

        plan = shipment.get_sorting_plan()
        self.assertTrue(plan['plan'][0]['complete'])
        self.assertTrue(plan['all_complete'])

    def test_a_graded_material_stays_until_every_grade_is_entered(self):
        shipment = self._shipment([(self.graded, 90.0)])

        self._line(shipment, self.graded, 40.0, 'EXCELLENT')
        plan = shipment.get_sorting_plan()
        self.assertFalse(plan['plan'][0]['complete'],
                         'the material vanished before its grades were done')
        self.assertEqual(
            {g['code'] for g in plan['plan'][0]['grades'] if not g['done']},
            {'GOOD', 'FAIR'})

        self._line(shipment, self.graded, 30.0, 'GOOD')
        self._line(shipment, self.graded, 20.0, 'FAIR')

        plan = shipment.get_sorting_plan()
        self.assertTrue(plan['plan'][0]['complete'])
        self.assertTrue(plan['all_complete'])

    def test_a_grade_that_did_not_arrive_is_entered_as_zero(self):
        """Not skipped, and not invented.

        Zero says "looked for, none found". Leaving the grade out would make
        the material read as still outstanding for ever; inventing a quantity
        would put material into stock that nobody ever handled.
        """
        shipment = self._shipment([(self.graded, 70.0)])
        self._line(shipment, self.graded, 40.0, 'EXCELLENT')
        self._line(shipment, self.graded, 30.0, 'GOOD')
        self._line(shipment, self.graded, 0.0, 'FAIR')

        self.assertTrue(shipment.get_sorting_plan()['all_complete'])

    def test_a_shipment_with_no_declared_breakdown_says_so(self):
        """The bug that made the picker empty.

        Not every shipment arrives itemised: older ones predate the feature,
        and a driver can turn up with a load nobody declared in advance — 21 of
        the 41 shipments on this database are like that. The plan is then
        legitimately empty, and a screen that restricted the picker to it left
        the sorter staring at a dropdown with no options and no explanation.

        So the emptiness is reported as a FACT rather than left to be inferred:
        an empty plan also describes a fully-sorted shipment, and the screen has
        to tell those two apart to know whether to offer the full catalogue.
        """
        shipment = self.env['recycle.shipment'].create({
            'warehouse_id': self.warehouse.id,
            'driver_name': 'No Breakdown Driver',
            'state': 'sorting',
        })

        plan = shipment.get_sorting_plan()

        self.assertEqual(plan['plan'], [])
        self.assertFalse(plan['has_declared_breakdown'])
        # And never "complete": there is no declared quantity to measure
        # completeness against, so the sorter decides when they are done — the
        # add button must stay.
        self.assertFalse(plan['all_complete'])

    def test_a_declared_shipment_is_marked_as_having_a_breakdown(self):
        shipment = self._shipment([(self.plain, 100.0)])
        self.assertTrue(shipment.get_sorting_plan()['has_declared_breakdown'])

    def test_remaining_never_goes_below_zero(self):
        shipment = self._shipment([(self.plain, 100.0)])
        self._line(shipment, self.plain, 100.0)
        self.assertEqual(shipment.get_sorting_plan()['plan'][0]['remaining_qty'], 0.0)

    # ------------------------------------------------------------------
    # Never more than was declared
    # ------------------------------------------------------------------
    def test_a_material_cannot_be_sorted_for_more_than_declared(self):
        shipment = self._shipment([(self.plain, 100.0)])
        with self.assertRaises(ValidationError):
            self._line(shipment, self.plain, 101.0)

    def test_the_grades_of_one_material_cannot_sum_past_what_was_declared(self):
        """The case a per-unit total at the end would let through.

        Entering 60 + 60 against a declared 90 is caught on the SECOND line,
        while the material is still in front of the sorter — not after every
        line has been typed.
        """
        shipment = self._shipment([(self.graded, 90.0)])
        self._line(shipment, self.graded, 60.0, 'EXCELLENT')
        with self.assertRaises(ValidationError):
            self._line(shipment, self.graded, 60.0, 'GOOD')

    def test_entering_exactly_what_was_declared_is_allowed(self):
        """"Not more than" — not "strictly less than".

        A shipment sorted with no loss at all is the ideal outcome, and a rule
        that refused it would refuse perfection.
        """
        shipment = self._shipment([(self.plain, 100.0)])
        self._line(shipment, self.plain, 100.0)
        self.assertEqual(len(shipment.line_ids), 1)

    # ------------------------------------------------------------------
    # A zero grade has to survive all the way to storage
    # ------------------------------------------------------------------
    def test_a_zero_grade_line_does_not_block_finishing(self):
        """The other half of allowing zero.

        The screen accepted a zero and the plan counted the grade as done, but
        storing then refused every line at or below zero — so the sorter who
        followed the instruction could not finish the shipment at all. Allowing
        a record and then rejecting it is worse than never allowing it: the
        work is lost at the last step, with the material already in the zone.
        """
        warehouse = make_warehouse(self.env, 
            {'name': 'Zero Grade WH', 'code': 'ZEROGRD'})
        storage = self.env['recycle.zone'].search(
            [('warehouse_id', '=', warehouse.id),
             ('zone_type', '=', 'storage')], limit=1)
        shipment = self.env['recycle.shipment'].create({
            'warehouse_id': warehouse.id,
            'driver_name': 'Zero Grade Driver',
            'state': 'sorting',
            'storage_zone_id': storage.id,
        })
        self.env['recycle.shipment.expected.line'].create({
            'shipment_id': shipment.id,
            'product_id': self.graded.id,
            'expected_qty': 70.0,
        })
        for qty, code in ((40.0, 'EXCELLENT'), (30.0, 'GOOD'), (0.0, 'FAIR')):
            self.env['recycle.shipment.line'].create({
                'shipment_id': shipment.id,
                'product_id': self.graded.id,
                'quantity': qty,
                'condition': code,
            })

        shipment.action_finish_sorting()

        self.assertEqual(shipment.state, 'sorted')
        # And the zero put nothing on a shelf — it is a record, not a quantity.
        stock = self.env['recycle.stock'].search([
            ('warehouse_id', '=', warehouse.id),
            ('product_id', '=', self.graded.id),
            ('condition', '=', 'FAIR'),
        ])
        self.assertFalse(
            stock.filtered(lambda s: s.quantity),
            'a grade that did not arrive was given stock')

    def test_a_negative_quantity_is_still_refused(self):
        """Zero is a record. Below zero is nothing at all.

        Refused on the LINE rather than at storage: a stray minus caught while
        the material is still in front of the sorter is a correction, and the
        same minus caught at the end is a shipment that cannot be finished.
        """
        shipment = self._shipment([(self.plain, 50.0)])

        with self.assertRaises(ValidationError):
            self._line(shipment, self.plain, -5.0)

    # ------------------------------------------------------------------
    # The lost quantity
    # ------------------------------------------------------------------
    def test_loss_is_declared_minus_entered_per_material(self):
        shipment = self._shipment([(self.plain, 100.0)])
        self._line(shipment, self.plain, 90.0)

        entry = next(p for p in shipment._sort_reconciliation()['products']
                     if p['product_id'] == self.plain.id)
        self.assertEqual(entry['lost_qty'], 10.0)
        self.assertEqual(entry['lost_pct'], 10.0)

    def test_loss_is_totalled_per_unit_of_measure(self):
        """Kilograms with kilograms, pieces with pieces.

        Adding them would produce a number with no unit anyone could write
        beside it.
        """
        counted = self.env['recycle.product'].create({
            'name': 'Sort Counted', 'category_id': self.category.id,
            'uom_id': self.piece.id,
        })
        shipment = self._shipment([(self.plain, 100.0), (counted, 10.0)])
        self._line(shipment, self.plain, 80.0)
        self._line(shipment, counted, 9.0)

        groups = {g['uom_name']: g
                  for g in shipment._sort_reconciliation()['uom_groups']}
        self.assertEqual(groups[self.kg.name]['lost_qty'], 20.0)
        self.assertEqual(groups[self.piece.name]['lost_qty'], 1.0)

    def test_loss_is_not_the_damaged_figure(self):
        """Two different physical things.

        Goods that arrived and were found unusable are on the floor; goods
        that never arrived are not. A shipment that came complete but damaged
        must not report a loss.
        """
        shipment = self._shipment([(self.plain, 100.0)])
        self.env['recycle.shipment.line'].create({
            'shipment_id': shipment.id,
            'product_id': self.plain.id,
            'quantity': 100.0,
            'is_damaged': True,
        })

        entry = next(p for p in shipment._sort_reconciliation()['products']
                     if p['product_id'] == self.plain.id)
        self.assertEqual(entry['lost_qty'], 0.0, 'damaged goods were counted as lost')
        self.assertEqual(shipment.damage_pct, 100.0)
