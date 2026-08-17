# -*- coding: utf-8 -*-
"""Where a warehouse is: answered once, and then fixed.

Two facts about a warehouse are not really editable properties of it — they are
what it IS. Order allocation matches buyers to warehouses by GOVERNORATE, and
every cached distance, open order and delivery price already computed assumes
where the building stands. A driver is sent to an ADDRESS; coordinates put a pin
on a map and do not name a gate.

So both are required when the warehouse is created, and neither can be changed
afterwards. Moving a warehouse between governorates is not an edit — it is a new
warehouse and the closure of an old one.

Neither is declared `required=True` on the field, deliberately: warehouses
already exist without them, a NOT NULL column would fail the upgrade outright,
and there is no honest value to backfill with. Inventing a governorate is
inventing where a building is. The rule is therefore enforced where it can be
answered — at creation — and the one exception is FILLING IN what was never
recorded, because refusing that would leave those rows permanently unroutable.
"""
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestWarehouseLocationRules(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # `recycle.province` carries name_ar / name_en, not `name` — it mirrors
        # a bilingual table, so there is no single "name" to read.
        Province = cls.env['recycle.province']
        cls.damascus = Province.create({
            'name_en': 'Loc Rules Damascus', 'name_ar': 'دمشق - قواعد الموقع',
            'backend_province_id': 'prov-locrules-1',
        })
        cls.other = Province.create({
            'name_en': 'Loc Rules Aleppo', 'name_ar': 'حلب - قواعد الموقع',
            'backend_province_id': 'prov-locrules-2',
        })

    def _warehouse(self, **over):
        vals = {
            'name': 'Location Rules WH',
            'code': 'LOCRULE1',
            'province_id': self.damascus.id,
            'address': 'المزة — الطريق الشمالي',
        }
        vals.update(over)
        return self.env['recycle.warehouse'].create(vals)

    # ------------------------------------------------------------------
    # Required at creation
    # ------------------------------------------------------------------
    def test_a_warehouse_without_a_governorate_is_refused(self):
        """It would hold stock no order could ever be routed to, and the
        failure surfaces far away as "no warehouse can fulfil this"."""
        with self.assertRaises(ValidationError):
            self._warehouse(province_id=False)

    def test_a_warehouse_without_an_address_is_refused(self):
        """Coordinates do not tell a driver which gate."""
        with self.assertRaises(ValidationError):
            self._warehouse(address=False)

    def test_a_blank_address_is_not_an_address(self):
        with self.assertRaises(ValidationError):
            self._warehouse(address='   ')

    def test_a_complete_warehouse_is_created(self):
        wh = self._warehouse()
        self.assertEqual(wh.province_id, self.damascus)
        self.assertTrue(wh.address)

    def test_the_backend_may_still_name_its_province(self):
        """The backend sends a NAME or its own uuid, never an Odoo id — the
        check runs after those are resolved, or it would refuse every warehouse
        the backend creates."""
        wh = self.env['recycle.warehouse'].create({
            'name': 'Backend Created WH',
            'code': 'LOCRULE2',
            'province_name': self.damascus.name_ar,
            'address': 'حلب — المنطقة الصناعية',
        })
        self.assertEqual(wh.province_id, self.damascus)

    # ------------------------------------------------------------------
    # Fixed afterwards
    # ------------------------------------------------------------------
    def test_a_warehouse_cannot_be_moved_to_another_governorate(self):
        wh = self._warehouse()
        with self.assertRaises(ValidationError):
            wh.write({'province_id': self.other.id})

    def test_a_warehouse_address_cannot_be_changed(self):
        wh = self._warehouse()
        with self.assertRaises(ValidationError):
            wh.write({'address': 'عنوان آخر تماماً'})

    def test_writing_the_SAME_value_is_not_a_change(self):
        """A save that re-sends every field must not be refused for the fields
        it did not touch — which is what an ordinary form save does."""
        wh = self._warehouse()
        wh.write({
            'province_id': self.damascus.id,
            'address': wh.address,
            'capacity': 4000,
        })
        self.assertEqual(wh.capacity, 4000)

    def test_a_legacy_row_can_still_be_FILLED_IN(self):
        """The one exception, and the reason the rule is not a NOT NULL column.

        Warehouses already exist with no governorate. Refusing to write one
        would leave them permanently unroutable with no way to correct them —
        a worse outcome than the rule protects against. Filling a blank is not
        moving a building.
        """
        wh = self._warehouse()
        # Cleared the way a legacy row is: past the constraint, in SQL.
        self.env.cr.execute(
            'UPDATE recycle_warehouse SET province_id = NULL, address = NULL '
            'WHERE id = %s', (wh.id,))
        wh.invalidate_recordset()

        wh.write({'province_id': self.other.id, 'address': 'عنوان مستدرك'})

        self.assertEqual(wh.province_id, self.other)

    def test_editable_things_are_still_editable(self):
        """The rule narrows nothing it was not meant to narrow."""
        wh = self._warehouse()
        wh.write({'name': 'Location Rules WH — renamed', 'capacity': 9000})
        self.assertEqual(wh.capacity, 9000)

    # ------------------------------------------------------------------
    # What the backend is told
    # ------------------------------------------------------------------
    def test_capacity_is_mirrored_to_the_backend(self):
        """It was missing from the mirrored list, so editing it here never
        reached the backend — which reports load as a PERCENTAGE of it. The two
        systems showed different fullness for the same building."""
        self.assertIn(
            'capacity',
            self.env['recycle.warehouse']._BACKEND_MIRRORED_FIELDS)
        self.assertIn(
            'address',
            self.env['recycle.warehouse']._BACKEND_MIRRORED_FIELDS)
