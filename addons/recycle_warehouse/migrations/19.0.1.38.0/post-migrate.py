# -*- coding: utf-8 -*-
"""Open a holding period for every driver who ALREADY has a truck.

The history table was introduced after drivers were already assigned, and a new
table starts empty. So `recycle.truck.assignment.history` recorded only the
hand-overs that happened AFTERWARDS — and every driver assigned before it existed
appeared, on their own file and in their printed PDF, to have never held a
vehicle at all.

That is worse than an empty report: the document looks complete and states
something false about the person. Anyone reading it would conclude the driver
had never been given a truck, while the same screen shows them holding one.

The backfill opens ONE period per current holder, with no end date, because that
is exactly what is true: they hold it now. `assigned_at` falls back to the
record's own creation date rather than to "now" — a driver assigned three months
ago should not read as assigned today, and the creation date is the earliest
moment the assignment could honestly have started.

Idempotent: a driver who already has an open period for that truck is skipped,
so re-running this never doubles a holding.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def _table_exists(cr, table):
    cr.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
        (table,))
    return bool(cr.fetchone())


def migrate(cr, version):
    if not version:
        return
    if not _table_exists(cr, 'recycle_truck_assignment_history'):
        return

    delivery = _backfill_delivery(cr)
    collection = _backfill_collection(cr)
    fixed = _recompute_stored_fields(cr)
    _logger.info(
        'Truck history backfilled: %s delivery driver(s), %s collector(s), '
        '%s row(s) recomputed',
        delivery, collection, fixed)


def _recompute_stored_fields(cr):
    """Fill in the fields a raw INSERT cannot.

    `truck_plate`, `truck_type` and `duration_days` are STORED computed fields.
    The backfill above writes with SQL — deliberately, because it must run
    before the registry is usable for this model — and SQL knows nothing about
    the compute methods, so those three columns came out NULL and 0.

    That is the same failure the backfill was written to fix, one level down: a
    driver file that prints a truck with no plate and "0 days held" looks
    complete and says nothing. The plate is the only thing distinguishing two
    vans in a fleet.

    Deferring to the ORM here rather than writing the values by hand keeps one
    definition of what each field means — a second SQL expression for
    `duration_days` would be a second answer to "how long did he have it".
    """
    cr.execute("""
        SELECT id FROM recycle_truck_assignment_history
         WHERE truck_plate IS NULL OR truck_type IS NULL
    """)
    ids = [row[0] for row in cr.fetchall()]
    if not ids:
        return 0

    env = api.Environment(cr, SUPERUSER_ID, {})
    rows = env['recycle.truck.assignment.history'].browse(ids)
    for name in ('truck_plate', 'truck_type', 'duration_days', 'is_current'):
        env.add_to_compute(rows._fields[name], rows)
    rows.flush_recordset()
    return len(ids)


def _backfill_delivery(cr):
    """Delivery drivers hold the truck directly on their own record."""
    if not _table_exists(cr, 'recycle_delivery_driver'):
        return 0

    cr.execute("""
        INSERT INTO recycle_truck_assignment_history (
            truck_id, warehouse_id, driver_kind, delivery_driver_id,
            driver_name, driver_national_id, assigned_at, assigned_by,
            is_current, duration_days,
            create_uid, create_date, write_uid, write_date)
        SELECT d.truck_id,
               d.warehouse_id,
               'delivery',
               d.id,
               d.name,
               d.national_id,
               -- The record's own creation date: a driver assigned months ago
               -- must not read as assigned today.
               COALESCE(d.create_date, NOW()),
               1,
               true,
               0,
               1, NOW(), 1, NOW()
          FROM recycle_delivery_driver d
         WHERE d.truck_id IS NOT NULL
           AND NOT EXISTS (
               SELECT 1 FROM recycle_truck_assignment_history h
                WHERE h.delivery_driver_id = d.id
                  AND h.truck_id = d.truck_id
                  AND h.released_at IS NULL
           )
    """)
    return cr.rowcount


def _backfill_collection(cr):
    """Collectors hold a truck through an assignment row.

    Their name and national id live on the driver REQUEST, which is the mirror
    of the backend account — so the snapshot is taken from there.
    """
    if not _table_exists(cr, 'recycle_driver_assignment'):
        return 0
    if not _table_exists(cr, 'recycle_driver_request'):
        return 0

    cr.execute("""
        INSERT INTO recycle_truck_assignment_history (
            truck_id, warehouse_id, driver_kind, driver_request_id,
            driver_name, driver_national_id, assigned_at, assigned_by,
            is_current, duration_days,
            create_uid, create_date, write_uid, write_date)
        SELECT a.truck_id,
               t.warehouse_id,
               'collection',
               r.id,
               COALESCE(r.name, a.backend_driver_id),
               r.national_id,
               COALESCE(a.create_date, NOW()),
               1,
               true,
               0,
               1, NOW(), 1, NOW()
          FROM recycle_driver_assignment a
          JOIN recycle_truck t ON t.id = a.truck_id
          LEFT JOIN recycle_driver_request r
                 ON r.backend_driver_id = a.backend_driver_id
         WHERE NOT EXISTS (
               SELECT 1 FROM recycle_truck_assignment_history h
                WHERE h.truck_id = a.truck_id
                  AND h.released_at IS NULL
                  AND h.driver_kind = 'collection'
                  AND (
                      (r.id IS NOT NULL AND h.driver_request_id = r.id)
                      OR (r.id IS NULL AND h.driver_name = a.backend_driver_id)
                  )
           )
    """)
    return cr.rowcount
