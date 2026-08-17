# -*- coding: utf-8 -*-
"""Give the damage entries back their unit of measure.

`recycle.damage.entry.uom_id` is a STORED related on the material's unit. A
stored related is written when the row is written — so every entry created
before the material had a unit, or before the field existed, kept a NULL that
nothing afterwards would ever fill in.

Empty is not a harmless default here. The damage screen totals per unit
precisely because kilograms and pieces cannot be added together, so a NULL unit
does not read as "unknown": it collects into its own nameless bucket beside the
real ones, and a figure appears with nothing written beside it. On a screen
whose whole purpose is to make a written-off quantity answerable, that is the
one column that must not be blank.

Recomputed rather than back-filled by SQL, so the value comes from the same
place a new row's would.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    Damage = env['recycle.damage.entry'].sudo()

    stale = Damage.search([
        ('uom_id', '=', False),
        ('product_id.uom_id', '!=', False),
    ])
    if not stale:
        _logger.info('Damage entries: every row already carries its unit.')
        return

    env.add_to_compute(Damage._fields['uom_id'], stale)
    env.flush_all()

    still_empty = Damage.search([
        ('id', 'in', stale.ids), ('uom_id', '=', False)])
    _logger.info(
        'Damage entries: filled the unit on %s row(s); %s still empty.',
        len(stale) - len(still_empty), len(still_empty))
