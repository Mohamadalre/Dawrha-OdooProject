# -*- coding: utf-8 -*-
"""Grades stop being four fixed English words and become the material's own.

Every `condition` column in this module used to hold one of
excellent/good/poor/damaged, lower-case. Grades are now authored per material in
the backend (`recycle.material.condition`, codes upper-case), and a material may
legitimately have none at all.

This migration moves the data across in the only order that keeps it honest:

  1. `damaged` was never a grade — it was the sorter saying "this did not
     survive". It becomes the explicit `is_damaged` flag it always meant, BEFORE
     anything else touches the column, because the next step would otherwise
     throw the distinction away.
  2. Remaining codes are upper-cased to match the backend's spelling.
  3. A code the material does not actually have is cleared. That is not data
     loss: it is the honest answer. A row filed under a grade the material has
     no definition for can never be matched by an order, so it counted as stock
     while being invisible to everything that would sell it.
  4. Clearing grades can leave two stock rows with the same key. They are MERGED
     rather than one being dropped — the quantities are real either way.
  5. The ledger is backfilled from the damage already recorded, so the new
     warehouse loss screens are not empty on the day they appear.

Downgrade reports are retired here too: the concept is gone from the model, and
a pending one cannot be approved under rules that no longer exist. They are
rejected with a reason rather than silently deleted or, far worse, quietly
treated as damage — which would write off stock that was never lost.
"""
import logging

_logger = logging.getLogger(__name__)

# The only grade vocabulary that ever existed here, and its upper-case form.
LEGACY_UPPERCASE = {
    'excellent': 'EXCELLENT',
    'good': 'GOOD',
    'poor': 'POOR',
    'damaged': 'DAMAGED',
}

# Every table that carries a grade code, and the column it lives in.
GRADED_TABLES = [
    ('recycle_stock', 'condition', 'product_id'),
    ('recycle_shipment_line', 'condition', 'product_id'),
    ('recycle_order_line', 'condition', 'product_id'),
    ('recycle_order_zone_movement', 'condition', 'product_id'),
    ('recycle_stock_damage_report', 'condition', 'product_id'),
]


def _table_exists(cr, table):
    cr.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
        (table,))
    return bool(cr.fetchone())


def _column_exists(cr, table, column):
    cr.execute("""
        SELECT 1 FROM information_schema.columns
         WHERE table_name = %s AND column_name = %s
    """, (table, column))
    return bool(cr.fetchone())


def migrate(cr, version):
    if not version:
        return

    _relax_grade_columns(cr)
    _split_damaged_from_grades(cr)
    _uppercase_codes(cr)
    _relax_retired_columns(cr)
    _retire_pending_downgrades(cr)
    _clear_unknown_grades(cr)
    _merge_duplicate_stock_rows(cr)
    _backfill_damage_ledger(cr)


def _relax_grade_columns(cr):
    """Let a grade column hold NULL before anything tries to clear one.

    Every one of these was a required Selection, so the column is NOT NULL. That
    constraint encoded the old rule — "everything has one of four grades" — and
    it is precisely the rule being retired: an ungraded material has no grade,
    and no value can stand in for that. Without this step the very first
    clearing update fails and the whole migration aborts.
    """
    for table, column, _product in GRADED_TABLES:
        if not _table_exists(cr, table) or not _column_exists(cr, table, column):
            continue
        cr.execute(
            'ALTER TABLE {t} ALTER COLUMN {c} DROP NOT NULL'.format(
                t=table, c=column))


def _split_damaged_from_grades(cr):
    """`condition = 'damaged'` on a sorted line becomes `is_damaged = true`.

    Runs FIRST and on its own. Damage is an outcome, not a quality: once the
    column is normalised or cleared the distinction is unrecoverable, because
    nothing else in the row records that the quantity was written off.
    """
    if not _table_exists(cr, 'recycle_shipment_line'):
        return

    # The ORM has not created the column yet at pre-migrate time.
    if not _column_exists(cr, 'recycle_shipment_line', 'is_damaged'):
        cr.execute(
            "ALTER TABLE recycle_shipment_line "
            "ADD COLUMN is_damaged boolean DEFAULT false")

    cr.execute("""
        UPDATE recycle_shipment_line
           SET is_damaged = true,
               condition = NULL
         WHERE lower(condition) = 'damaged'
    """)
    _logger.info('Damage split from grades on %s sorted line(s)', cr.rowcount)


def _uppercase_codes(cr):
    """Match the backend's spelling. 'good' and 'GOOD' were never two grades."""
    for table, column, _product in GRADED_TABLES:
        if not _table_exists(cr, table) or not _column_exists(cr, table, column):
            continue
        for lower, upper in LEGACY_UPPERCASE.items():
            cr.execute(
                "UPDATE {t} SET {c} = %s WHERE lower({c}) = %s".format(
                    t=table, c=column),
                (upper, lower))
        # Anything else the column may hold, normalised the same way.
        cr.execute(
            "UPDATE {t} SET {c} = upper(trim({c})) "
            " WHERE {c} IS NOT NULL AND {c} <> upper(trim({c}))".format(
                t=table, c=column))


def _relax_retired_columns(cr):
    """Let the retired downgrade columns stop blocking new rows.

    They are kept, not dropped: approved downgrades are history, and history is
    not improved by deleting it. But `report_type` was NOT NULL, so leaving it
    as-is would make every new damage report fail to insert — the field no
    longer exists on the model, so nothing would supply a value.
    """
    if not _table_exists(cr, 'recycle_stock_damage_report'):
        return
    for column in ('report_type', 'to_condition'):
        if _column_exists(cr, 'recycle_stock_damage_report', column):
            cr.execute(
                'ALTER TABLE recycle_stock_damage_report '
                'ALTER COLUMN {c} DROP NOT NULL'.format(c=column))


def _retire_pending_downgrades(cr):
    """Reject downgrades still awaiting a decision.

    A pending downgrade cannot be approved any more: the action that moved a
    quantity between grades is gone. Rejecting it with a reason leaves the
    sorter something they can act on. Treating it as damage instead would write
    off stock that was never lost.
    """
    if not _table_exists(cr, 'recycle_stock_damage_report'):
        return
    if not _column_exists(cr, 'recycle_stock_damage_report', 'report_type'):
        return

    cr.execute("""
        UPDATE recycle_stock_damage_report
           SET state = 'rejected',
               review_reason = COALESCE(review_reason || ' | ', '') ||
                   'Downgrade reports were retired: grade corrections are made '
                   'during sorting, not through a loss report. Re-sort the '
                   'material instead.'
         WHERE report_type = 'downgrade'
           AND state = 'pending_approval'
    """)
    if cr.rowcount:
        _logger.info('Retired %s pending downgrade report(s)', cr.rowcount)


def _clear_unknown_grades(cr):
    """Clear any code the material does not actually define.

    Deliberately compared against the material's OWN grades. A global "is this
    one of the four words" test is what produced the problem in the first
    place — it accepted a code for a material that had never heard of it.
    """
    if not _table_exists(cr, 'recycle_material_condition'):
        return

    for table, column, product_col in GRADED_TABLES:
        if not _table_exists(cr, table) or not _column_exists(cr, table, column):
            continue
        cr.execute("""
            UPDATE {t} t
               SET {c} = NULL
             WHERE t.{c} IS NOT NULL
               AND NOT EXISTS (
                   SELECT 1 FROM recycle_material_condition mc
                    WHERE mc.product_id = t.{p}
                      AND mc.code = t.{c}
               )
        """.format(t=table, c=column, p=product_col))
        if cr.rowcount:
            _logger.info(
                '%s: cleared %s grade(s) the material does not define',
                table, cr.rowcount)


def _merge_duplicate_stock_rows(cr):
    """Fold stock rows that became identical once their grade was cleared.

    Two rows that differed only by a grade neither material defined are one row.
    The quantities are summed rather than one being discarded: the material is
    physically on the shelf whatever the paperwork called it.
    """
    if not _table_exists(cr, 'recycle_stock'):
        return

    cr.execute("""
        WITH ranked AS (
            SELECT id,
                   quantity,
                   reserved_qty,
                   FIRST_VALUE(id) OVER (
                       PARTITION BY warehouse_id, product_id, zone_id, condition
                       ORDER BY id
                   ) AS keep_id
              FROM recycle_stock
        ),
        totals AS (
            SELECT keep_id,
                   SUM(quantity)     AS quantity,
                   SUM(reserved_qty) AS reserved_qty,
                   COUNT(*)          AS rows
              FROM ranked
             GROUP BY keep_id
            HAVING COUNT(*) > 1
        )
        UPDATE recycle_stock s
           SET quantity     = t.quantity,
               reserved_qty = t.reserved_qty
          FROM totals t
         WHERE s.id = t.keep_id
    """)
    merged = cr.rowcount

    cr.execute("""
        DELETE FROM recycle_stock s
         WHERE s.id <> (
             SELECT MIN(o.id) FROM recycle_stock o
              WHERE o.warehouse_id = s.warehouse_id
                AND o.product_id   = s.product_id
                AND o.zone_id IS NOT DISTINCT FROM s.zone_id
                AND o.condition IS NOT DISTINCT FROM s.condition
         )
    """)
    if merged or cr.rowcount:
        _logger.info(
            'Merged %s stock row group(s), removed %s duplicate row(s)',
            merged, cr.rowcount)


def _backfill_damage_ledger(cr):
    """Seed the ledger from losses already recorded elsewhere.

    Without this the new warehouse loss screens open empty, which reads as "this
    warehouse has never lost anything" — a stronger and more misleading claim
    than "we started counting today".
    """
    if not _table_exists(cr, 'recycle_damage_entry'):
        # Created by the ORM after pre-migrate; the post-migrate step fills it.
        return


def post_migrate_backfill(cr):
    """Called from post-migrate, once the ORM has created the ledger table."""
    if not _table_exists(cr, 'recycle_damage_entry'):
        return

    cr.execute("SELECT COUNT(*) FROM recycle_damage_entry")
    if cr.fetchone()[0]:
        return  # already seeded — never double-count a loss

    # Approved storage damage reports.
    if _table_exists(cr, 'recycle_stock_damage_report'):
        cr.execute("""
            INSERT INTO recycle_damage_entry (
                warehouse_id, product_id, condition, quantity, source,
                occurred_at, recorded_by, reason, report_id,
                create_uid, create_date, write_uid, write_date)
            SELECT r.warehouse_id, r.product_id, r.condition, r.quantity,
                   'storage',
                   COALESCE(r.approved_at, r.write_date, r.create_date),
                   COALESCE(r.reviewed_by, r.reported_by, 1),
                   r.reason, r.id,
                   1, NOW(), 1, NOW()
              FROM recycle_stock_damage_report r
             WHERE r.state = 'approved'
        """)
        _logger.info('Damage ledger: %s entry(ies) from storage reports',
                     cr.rowcount)

    # Damaged lines of shipments that finished sorting.
    if _table_exists(cr, 'recycle_shipment_line'):
        cr.execute("""
            INSERT INTO recycle_damage_entry (
                warehouse_id, product_id, condition, quantity, source,
                occurred_at, recorded_by, reason, shipment_id,
                create_uid, create_date, write_uid, write_date)
            SELECT s.warehouse_id, l.product_id, NULL, l.quantity,
                   'sorting',
                   COALESCE(s.sorted_at, s.write_date, s.create_date),
                   COALESCE(s.sorter_user_id, 1),
                   s.damage_reason, s.id,
                   1, NOW(), 1, NOW()
              FROM recycle_shipment_line l
              JOIN recycle_shipment s ON s.id = l.shipment_id
             WHERE l.is_damaged = true
               AND l.quantity > 0
               AND s.state = 'sorted'
        """)
        _logger.info('Damage ledger: %s entry(ies) from sorted shipments',
                     cr.rowcount)
