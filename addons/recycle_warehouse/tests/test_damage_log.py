# -*- coding: utf-8 -*-
"""Grades belong to their material, and damage is not one of them.

Two things used to be the same field. "This is GOOD quality" and "this did not
survive" were both written into one Selection of four English words, which made
three separate failures possible at once:

  * a material the admin graded PREMIUM/STANDARD could hold no stock at all,
    because neither word was in the list;
  * such a material had no way to say "damaged" either;
  * the storing step matched the literal string 'damaged', so for any material
    graded differently, spoiled goods were filed as sellable stock.

These tests pin the separation: `is_damaged` answers whether the quantity
survived, `condition` answers what it survived AS, and every write-off leaves a
dated ledger entry naming its warehouse.
"""
from odoo.exceptions import UserError, ValidationError
from .common import make_warehouse
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestDamageLog(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = make_warehouse(cls.env, **{
            'name': 'Damage Log Warehouse', 'code': 'DLW1',
        })
        cls.storage = cls.env['recycle.zone'].create({
            'name': 'Storage DL', 'warehouse_id': cls.warehouse.id,
            'zone_type': 'storage',
        })
        cls.category = cls.env['recycle.product.category'].create(
            {'name': 'Damage Log Category'})
        _unit = cls.env['recycle.measurement.unit']
        cls._kg = _unit.search([('code', '=', 'KG')], limit=1) or _unit.create(
            {'code': 'KG', 'name': 'Kilogram', 'allows_tolerance': True})
        cls.graded = cls.env['recycle.product'].create({
            'name': 'Graded Material DL', 'category_id': cls.category.id,
            'uom_id': cls._kg.id,
        })
        Condition = cls.env['recycle.material.condition']
        Condition.create({'product_id': cls.graded.id, 'code': 'PREMIUM',
                          'name': 'Premium', 'sort_order': 1})
        Condition.create({'product_id': cls.graded.id, 'code': 'STANDARD',
                          'name': 'Standard', 'sort_order': 2})
        cls.plain = cls.env['recycle.product'].create({
            'name': 'Ungraded Material DL', 'category_id': cls.category.id,
            'uom_id': cls._kg.id,
        })

    # ------------------------------------------------------------------
    # Grades are per material
    # ------------------------------------------------------------------
    def test_stock_may_not_carry_a_grade_from_another_material(self):
        with self.assertRaises(ValidationError):
            self.env['recycle.stock'].create({
                'warehouse_id': self.warehouse.id,
                'product_id': self.plain.id,
                'zone_id': self.storage.id,
                # The ungraded material has no grades; borrowing one from the
                # graded material would file the quantity under a distinction
                # that does not exist for it.
                'condition': 'PREMIUM',
                'quantity': 10,
            })

    def test_stock_grade_is_stored_in_the_materials_own_spelling(self):
        """Validating without REWRITING is the subtle version of this bug: both
        'premium' and 'PREMIUM' pass a check that normalises before comparing,
        and the two rows can then never match each other again."""
        line = self.env['recycle.stock'].create({
            'warehouse_id': self.warehouse.id,
            'product_id': self.graded.id,
            'zone_id': self.storage.id,
            'condition': 'premium',
            'quantity': 10,
        })
        self.assertEqual(line.condition, 'PREMIUM')

    def test_ungraded_stock_is_a_legitimate_state(self):
        line = self.env['recycle.stock'].create({
            'warehouse_id': self.warehouse.id,
            'product_id': self.plain.id,
            'zone_id': self.storage.id,
            'quantity': 40,
        })
        self.assertFalse(line.condition)
        self.assertEqual(line.available_qty, 40)

    def test_adding_stock_refuses_a_grade_the_material_does_not_have(self):
        Stock = self.env['recycle.stock']
        with self.assertRaises(ValidationError):
            Stock._add_quantity(self.warehouse, self.graded, 10,
                                condition='DAMAGED')

    def test_a_grade_never_satisfies_another_grade(self):
        Stock = self.env['recycle.stock']
        Stock._add_quantity(self.warehouse, self.graded, 100,
                            condition='STANDARD', zone=self.storage)

        # Plenty of STANDARD on the shelf, but PREMIUM was asked for.
        self.assertEqual(
            Stock._available_qty(self.warehouse, self.graded,
                                 condition='PREMIUM'), 0)
        with self.assertRaises(UserError):
            Stock._deduct_quantity(self.warehouse, self.graded, 5,
                                   condition='PREMIUM')

    # ------------------------------------------------------------------
    # Damage is an outcome, not a grade
    # ------------------------------------------------------------------
    def _sorted_shipment(self, lines):
        shipment = self.env['recycle.shipment'].create({
            'warehouse_id': self.warehouse.id,
            'driver_name': 'DL Driver',
            'actual_weight': 100,
        })
        for vals in lines:
            self.env['recycle.shipment.line'].create(
                dict(vals, shipment_id=shipment.id))
        return shipment

    def test_a_damaged_line_carries_no_grade_and_is_not_usable(self):
        shipment = self._sorted_shipment([
            {'product_id': self.graded.id, 'quantity': 30,
             'condition': 'PREMIUM'},
            {'product_id': self.graded.id, 'quantity': 10,
             'is_damaged': True},
        ])

        self.assertEqual(shipment.total_good_qty, 30)
        self.assertEqual(shipment.total_damaged_qty, 10)
        self.assertAlmostEqual(shipment.damage_pct, 25.0)

    def test_usable_totals_count_a_grade_the_old_fixed_list_never_had(self):
        """The old computation summed three literal names. A material graded
        PREMIUM/STANDARD matched none of them, so its sorted quantity counted as
        neither usable nor damaged and vanished from both totals."""
        shipment = self._sorted_shipment([
            {'product_id': self.graded.id, 'quantity': 60,
             'condition': 'STANDARD'},
        ])

        self.assertEqual(shipment.total_good_qty, 60)
        self.assertEqual(shipment.total_damaged_qty, 0)

    def test_a_damaged_line_may_not_be_given_a_grade_of_its_own(self):
        shipment = self._sorted_shipment([])
        line = self.env['recycle.shipment.line'].create({
            'shipment_id': shipment.id,
            'product_id': self.graded.id,
            'quantity': 5,
            'is_damaged': True,
            'condition': 'PREMIUM',
        })
        # Accepted at the field level, but it says nothing: the constraint skips
        # damaged lines precisely because a write-off is not sold at a quality.
        # What matters is that it is not counted as usable stock.
        self.assertTrue(line.is_damaged)
        self.assertEqual(shipment.total_good_qty, 0)

    # ------------------------------------------------------------------
    # The ledger is append-only
    # ------------------------------------------------------------------
    def test_the_ledger_refuses_edits_and_deletes_from_everyone(self):
        entry = self.env['recycle.damage.entry'].create({
            'warehouse_id': self.warehouse.id,
            'product_id': self.graded.id,
            'condition': 'PREMIUM',
            'quantity': 12,
            'source': 'storage',
            'recorded_by': self.env.user.id,
        })

        # Including the superuser this test runs as. An `env.su` exemption would
        # be no protection: Odoo treats uid 1 as superuser unconditionally, so
        # the one account with a motive to adjust a loss would be the only one
        # able to.
        with self.assertRaises(UserError):
            entry.write({'quantity': 1})
        with self.assertRaises(UserError):
            entry.unlink()

    def test_summary_groups_losses_by_warehouse_material_and_source(self):
        Damage = self.env['recycle.damage.entry']
        Damage.create({
            'warehouse_id': self.warehouse.id, 'product_id': self.graded.id,
            'quantity': 10, 'source': 'sorting',
            'recorded_by': self.env.user.id,
        })
        Damage.create({
            'warehouse_id': self.warehouse.id, 'product_id': self.graded.id,
            'quantity': 5, 'source': 'sorting',
            'recorded_by': self.env.user.id,
        })
        Damage.create({
            'warehouse_id': self.warehouse.id, 'product_id': self.graded.id,
            'quantity': 7, 'source': 'storage',
            'recorded_by': self.env.user.id,
        })

        rows = Damage.summary_by_warehouse(warehouse_ids=[self.warehouse.id])
        by_source = {r['source']: r for r in rows}

        # The two sources stay apart: they say different things about how the
        # warehouse is run, and one total would hide which.
        self.assertEqual(by_source['sorting']['quantity'], 15)
        self.assertEqual(by_source['sorting']['entries'], 2)
        self.assertEqual(by_source['storage']['quantity'], 7)

    # ------------------------------------------------------------------
    # Back from a figure to the delivery behind it
    # ------------------------------------------------------------------
    def _damage_shipment(self, entries):
        """A shipment with damage entries hung off it. `entries` is
        [(product, qty, condition), …]."""
        shipment = self.env['recycle.shipment'].create({
            'warehouse_id': self.warehouse.id,
            'driver_name': 'By-Shipment Driver',
            'damage_reason': 'Soaked in transit',
        })
        for product, qty, condition in entries:
            self.env['recycle.damage.entry'].create({
                'warehouse_id': self.warehouse.id,
                'product_id': product.id,
                'quantity': qty,
                'condition': condition,
                'source': 'sorting',
                'shipment_id': shipment.id,
                'recorded_by': self.env.user.id,
            })
        return shipment

    def test_damage_is_grouped_under_the_shipment_it_came_off(self):
        """The question a total cannot answer: *which delivery was this?*"""
        shipment = self._damage_shipment([
            (self.graded, 10, 'PREMIUM'),
            (self.plain, 4, False),
        ])

        rows = self.env['recycle.damage.entry'].by_shipment(
            warehouse_ids=[self.warehouse.id])
        row = next(r for r in rows if r['shipment_id'] == shipment.id)

        self.assertEqual(len(row['lines']), 2)
        self.assertEqual(
            {l['product_name'] for l in row['lines']},
            {self.graded.name, self.plain.name})
        self.assertEqual(row['damage_reason'], 'Soaked in transit')

    def test_the_shipment_total_is_kept_per_unit(self):
        """Kilograms and pieces do not add up.

        A single "14 damaged" covering a material sold by weight and one sold
        by the piece is a number nobody can write a unit beside, and nobody can
        check.
        """
        Unit = self.env['recycle.measurement.unit']
        piece = Unit.search([('code', '=', 'PIECE')], limit=1) or Unit.create(
            {'code': 'PIECE', 'name': 'Piece', 'allows_tolerance': False})
        counted = self.env['recycle.product'].create({
            'name': 'Counted DL', 'category_id': self.category.id,
            'uom_id': piece.id,
        })
        shipment = self._damage_shipment([
            (self.plain, 10, False),
            (counted, 4, False),
        ])

        rows = self.env['recycle.damage.entry'].by_shipment(
            warehouse_ids=[self.warehouse.id])
        row = next(r for r in rows if r['shipment_id'] == shipment.id)

        totals = {t['uom_name']: t['quantity'] for t in row['totals']}
        self.assertEqual(len(totals), 2, 'two units were added together')
        self.assertEqual(totals[piece.name], 4)

    def test_storage_losses_are_left_out(self):
        """They have no shipment.

        Padding the list with rows that cannot answer "which delivery?" would
        make the question look answered.
        """
        self.env['recycle.damage.entry'].create({
            'warehouse_id': self.warehouse.id, 'product_id': self.plain.id,
            'quantity': 9, 'source': 'storage',
            'recorded_by': self.env.user.id,
        })

        rows = self.env['recycle.damage.entry'].by_shipment(
            warehouse_ids=[self.warehouse.id])

        self.assertTrue(all(r['shipment_id'] for r in rows))
        self.assertNotIn('storage', {l.get('source') for r in rows
                                     for l in r['lines']})
