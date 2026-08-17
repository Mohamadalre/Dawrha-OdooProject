# -*- coding: utf-8 -*-
"""Rebuild `recycle.warehouse.governorate` as a link into `recycle.province`.

The old Selection stored a technical key ('damascus'). Provinces are now rows
mirrored from the backend's `provinces` table, matched by the backend uuid.
At migration time no backend push has happened yet, so the rows created here
carry a placeholder id `legacy:<key>`; `recycle.province.backend_upsert()`
ADOPTS such a row by name on the first real push (rewriting the placeholder to
the true uuid) instead of creating a duplicate. That keeps every warehouse's
governorate link intact across the cut-over.
"""

# key → (name_en, name_ar). The English names are exactly the labels the old
# Selection used AND exactly what the backend seeds, which is what makes the
# name-based adoption in `backend_upsert` land on the right row.
LEGACY_PROVINCES = [
    ('damascus', 'Damascus', 'دمشق'),
    ('rif_dimashq', 'Rif Dimashq', 'ريف دمشق'),
    ('aleppo', 'Aleppo', 'حلب'),
    ('homs', 'Homs', 'حمص'),
    ('hama', 'Hama', 'حماة'),
    ('latakia', 'Latakia', 'اللاذقية'),
    ('tartus', 'Tartus', 'طرطوس'),
    ('idlib', 'Idlib', 'إدلب'),
    ('deir_ez_zor', 'Deir ez-Zor', 'دير الزور'),
    ('raqqa', 'Raqqa', 'الرقة'),
    ('hasakah', 'Al-Hasakah', 'الحسكة'),
    ('daraa', 'Daraa', 'درعا'),
    ('sweida', 'As-Suwayda', 'السويداء'),
    ('quneitra', 'Quneitra', 'القنيطرة'),
]


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


def _uom_translation_map(cr):
    """old uom.uom id → recycle.measurement.unit id.

    Matched on the unit's NAME/CODE rather than a hard-coded pairing, so a
    backend that named its units differently still lands correctly. Anything
    unmatched keeps whatever Odoo's field default already put there — never
    NULL, because the column is required.
    """
    cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'uom_uom'")
    if not cr.fetchone():
        return {}

    cr.execute("SELECT id, code, lower(name) FROM recycle_measurement_unit")
    units = cr.fetchall()
    if not units:
        return {}
    by_code = {(c or '').strip().lower(): uid for uid, c, _n in units}
    by_name = {n: uid for uid, _c, n in units if n}

    # uom.uom.name is a jsonb translated field in Odoo 19; ->>'en_US' reads the
    # English term, which is what the old records were created with.
    cr.execute("SELECT id, lower(name->>'en_US') FROM uom_uom")
    mapping = {}
    for old_id, old_name in cr.fetchall():
        name = (old_name or '').strip()
        target = by_code.get(name) or by_name.get(name)
        if not target and name in ('kg', 'kgm', 'kilogram', 'kilograms'):
            target = by_code.get('kg')
        if not target and name in ('units', 'unit', 'piece', 'pieces', 'pce'):
            target = by_code.get('piece')
        if target:
            mapping[old_id] = target
    return mapping


def _migrate_units(cr):
    mapping = _uom_translation_map(cr)
    for table, column in UOM_COLUMNS:
        legacy = '%s_legacy_uom' % column
        if not _column_exists(cr, table, legacy):
            continue
        if mapping and _column_exists(cr, table, column):
            for old_id, new_id in mapping.items():
                cr.execute(
                    'UPDATE "%s" SET "%s" = %%s WHERE "%s" = %%s'
                    % (table, column, legacy), (new_id, old_id))
        cr.execute('ALTER TABLE "%s" DROP COLUMN "%s"' % (table, legacy))


def migrate(cr, version):
    if not version:
        return

    _migrate_units(cr)

    cr.execute("""
        SELECT 1 FROM information_schema.tables
         WHERE table_name = 'recycle_warehouse_governorate_legacy'
    """)
    if not cr.fetchone():
        return

    cr.execute("SELECT warehouse_id, legacy_key FROM recycle_warehouse_governorate_legacy")
    legacy_rows = cr.fetchall()
    if not legacy_rows:
        cr.execute("DROP TABLE recycle_warehouse_governorate_legacy")
        return

    used_keys = {key for _, key in legacy_rows}
    province_id_by_key = {}

    for key, name_en, name_ar in LEGACY_PROVINCES:
        if key not in used_keys:
            continue  # only seed governorates a warehouse actually used
        backend_id = 'legacy:%s' % key
        cr.execute(
            "SELECT id FROM recycle_province WHERE backend_province_id = %s",
            (backend_id,))
        row = cr.fetchone()
        if row:
            province_id_by_key[key] = row[0]
            continue
        cr.execute("""
            INSERT INTO recycle_province
                   (backend_province_id, name_en, name_ar, active,
                    create_uid, write_uid, create_date, write_date)
            VALUES (%s, %s, %s, TRUE, 1, 1, NOW(), NOW())
         RETURNING id
        """, (backend_id, name_en, name_ar))
        province_id_by_key[key] = cr.fetchone()[0]

    for warehouse_id, key in legacy_rows:
        province_id = province_id_by_key.get(key)
        if not province_id:
            continue
        cr.execute(
            "UPDATE recycle_warehouse SET province_id = %s WHERE id = %s",
            (province_id, warehouse_id))

    # Refresh the denormalised name so the column is never left stale between
    # the upgrade and the first write on the record.
    cr.execute("""
        UPDATE recycle_warehouse w
           SET governorate = p.name_ar
          FROM recycle_province p
         WHERE w.province_id = p.id
    """)
    cr.execute("""
        UPDATE recycle_warehouse SET governorate = NULL WHERE province_id IS NULL
    """)

    cr.execute("DROP TABLE recycle_warehouse_governorate_legacy")
