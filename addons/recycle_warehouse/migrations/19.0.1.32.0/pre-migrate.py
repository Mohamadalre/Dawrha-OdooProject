# -*- coding: utf-8 -*-
"""Grades become a property of each material instead of a global list.

`recycle.material.condition.product_id` is now required, and the rows already
here belong to no material — they were the global vocabulary every material had
to borrow from. There is no honest way to assign them: a 'GOOD' that described
everything describes nothing in particular.

So they are removed, and the backend re-pushes each material's own grades. That
is safe because the backend is the sole author of this table; Odoo has only ever
mirrored it.
"""


def migrate(cr, version):
    if not version:
        return

    cr.execute("""
        SELECT 1 FROM information_schema.tables
         WHERE table_name = 'recycle_material_condition'
    """)
    if not cr.fetchone():
        return

    # Drop the old global uniqueness first — the new one is (product, code).
    cr.execute("""
        ALTER TABLE recycle_material_condition
        DROP CONSTRAINT IF EXISTS recycle_material_condition_code_uniq
    """)
    cr.execute("DELETE FROM recycle_material_condition")
