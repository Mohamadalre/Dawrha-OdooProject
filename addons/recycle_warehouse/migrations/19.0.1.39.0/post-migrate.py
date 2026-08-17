# -*- coding: utf-8 -*-
"""Repair truck-history rows whose stored computed fields were never filled.

The 19.0.1.38.0 backfill opened a holding period for every driver who already
had a truck, using raw SQL. SQL cannot run a compute method, so three columns
came out empty on those rows:

    truck_plate    NULL
    truck_type     NULL
    duration_days  0

The plate is the only thing that distinguishes two vans in a fleet, and it is
the field a driver file is read FOR. A printed document showing a truck with no
plate and "0 days held" is worse than a missing document: it looks complete and
states something false about the person.

19.0.1.38.0 now recomputes as part of the backfill, so a database upgrading from
older than that never sees the problem. This file exists for the databases that
already ran 1.38.0 in its first form — a migration that has run does not run
again, so the repair needs its own version to reach them.

Idempotent: only rows still missing the values are touched.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

RECOMPUTED = ('truck_plate', 'truck_type', 'duration_days', 'is_current')


def migrate(cr, version):
    if not version:
        return

    cr.execute("""
        SELECT 1 FROM information_schema.tables
         WHERE table_name = 'recycle_truck_assignment_history'
    """)
    if not cr.fetchone():
        return

    cr.execute("""
        SELECT id FROM recycle_truck_assignment_history
         WHERE truck_plate IS NULL OR truck_type IS NULL
    """)
    ids = [row[0] for row in cr.fetchall()]
    if not ids:
        _logger.info('Truck history: nothing to repair.')
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    rows = env['recycle.truck.assignment.history'].browse(ids)
    for name in RECOMPUTED:
        env.add_to_compute(rows._fields[name], rows)
    rows.flush_recordset()

    _logger.info('Truck history: repaired %s row(s) — plate, job and days held '
                 'are now filled in.', len(ids))
