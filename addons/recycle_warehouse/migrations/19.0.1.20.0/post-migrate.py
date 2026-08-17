# -*- coding: utf-8 -*-
"""Backfill the new uom.uom-based fields from the old weight/piece flags
that this module used before it depended on the 'uom' module."""


def migrate(cr, version):
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'recycle_product' AND column_name = 'measure_type'
    """)
    if not cr.fetchone():
        return

    # uom.uom.name is a translated (JSONB) field in this Odoo version, so
    # resolve the default units via their stable xmlids instead of raw
    # name matching.
    cr.execute("""
        SELECT module, name, res_id FROM ir_model_data
        WHERE model = 'uom.uom' AND module = 'uom'
              AND name IN ('product_uom_kgm', 'product_uom_unit')
    """)
    by_xmlid = {row[1]: row[2] for row in cr.fetchall()}
    kg_id = by_xmlid.get('product_uom_kgm')
    unit_id = by_xmlid.get('product_uom_unit')
    if not kg_id or not unit_id:
        return

    cr.execute("""
        UPDATE recycle_product SET uom_id = %s
        WHERE uom_id IS NULL AND (measure_type = 'weight' OR measure_type IS NULL)
    """, (kg_id,))
    cr.execute("""
        UPDATE recycle_product SET uom_id = %s
        WHERE uom_id IS NULL AND measure_type = 'piece'
    """, (unit_id,))

    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'recycle_shipment_expected_line' AND column_name = 'expected_qty'
    """)
    if cr.fetchone():
        cr.execute("""
            UPDATE recycle_shipment_expected_line
            SET expected_qty = CASE WHEN measure_type = 'piece'
                                     THEN piece_count ELSE weight END
            WHERE expected_qty IS NULL OR expected_qty = 0
        """)
