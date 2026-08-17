# -*- coding: utf-8 -*-
"""Shift scope migration: derive is_global + warehouse_ids from the old
single warehouse_id column.

- shift with NO warehouse  → GLOBAL (is_global = TRUE, no warehouses)
- shift WITH a warehouse    → SPECIFIC to that one warehouse

Runs AFTER the new schema (including the recycle_shift_warehouse_rel M2M
table) exists, so the relation rows can be inserted directly.
"""


def migrate(cr, version):
    # Global = shifts that had no warehouse before.
    cr.execute(
        "UPDATE recycle_shift SET is_global = (warehouse_id IS NULL)"
    )
    # Seed the M2M with the old single warehouse for the specific ones
    # (idempotent — skip pairs that somehow already exist).
    cr.execute(
        """
        INSERT INTO recycle_shift_warehouse_rel (shift_id, warehouse_id)
        SELECT s.id, s.warehouse_id
          FROM recycle_shift s
         WHERE s.warehouse_id IS NOT NULL
           AND NOT EXISTS (
             SELECT 1 FROM recycle_shift_warehouse_rel r
              WHERE r.shift_id = s.id AND r.warehouse_id = s.warehouse_id
           )
        """
    )
