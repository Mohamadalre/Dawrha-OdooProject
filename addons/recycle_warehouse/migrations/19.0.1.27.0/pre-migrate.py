# -*- coding: utf-8 -*-
"""Two comodel changes need their old values parked before Odoo rewrites the
schema:

1. `recycle.warehouse.governorate` becomes a stored mirror of the new
   `province_id`. The column keeps its SQL type, so Odoo will not drop it — but
   it WILL recompute it from the (still empty) `province_id` and wipe every
   value. The keys are copied aside so post-migrate can rebuild the link.

2. `recycle.product.uom_id` (and the stored `related` copies on shipment lines
   and damage reports) moves from `uom.uom` to `recycle.measurement.unit` — the
   list mirrored from the backend. The old int ids point at rows in another
   table, so they are renamed out of the way: Odoo then creates a FRESH
   `uom_id` column, fills it from the field default and can still apply NOT
   NULL, and post-migrate remaps each row to the matching backend unit.
"""

# (table, column) pairs holding a uom.uom id that must be remapped.
UOM_COLUMNS = [
    ('recycle_product', 'uom_id'),
    ('recycle_shipment_line', 'uom_id'),
    ('recycle_shipment_expected_line', 'uom_id'),
    ('recycle_stock_damage_report', 'uom_id'),
]


def _column_exists(cr, table, column):
    cr.execute("""
        SELECT 1 FROM information_schema.columns
         WHERE table_name = %s AND column_name = %s
    """, (table, column))
    return bool(cr.fetchone())


def migrate(cr, version):
    if not version:
        return

    # ── 1. governorate ────────────────────────────────────────────────
    if _column_exists(cr, 'recycle_warehouse', 'governorate'):
        cr.execute("DROP TABLE IF EXISTS recycle_warehouse_governorate_legacy")
        cr.execute("""
            CREATE TABLE recycle_warehouse_governorate_legacy AS
            SELECT id AS warehouse_id, governorate AS legacy_key
              FROM recycle_warehouse
             WHERE governorate IS NOT NULL AND governorate <> ''
        """)

    # ── 2. units of measure ───────────────────────────────────────────
    for table, column in UOM_COLUMNS:
        legacy = '%s_legacy_uom' % column
        if not _column_exists(cr, table, column):
            continue
        if _column_exists(cr, table, legacy):
            continue  # a previous (interrupted) run already parked it
        cr.execute(
            'ALTER TABLE "%s" RENAME COLUMN "%s" TO "%s"' % (table, column, legacy))
