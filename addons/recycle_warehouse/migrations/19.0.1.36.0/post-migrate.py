# -*- coding: utf-8 -*-
"""Seed the damage ledger, once the ORM has created its table.

Split from pre-migrate because `recycle_damage_entry` does not exist yet at that
point — the ORM builds it between the two steps. The backfill itself lives with
the rest of the grade migration so the whole move reads as one change.
"""
import importlib.util
import logging
import os

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    # Loaded by PATH, not by name: a migration directory is not an importable
    # package (its name starts with a digit and it has no __init__), so the
    # sibling module cannot simply be imported.
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location(
        'recycle_pre_migrate_1_36_0', os.path.join(here, 'pre-migrate.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    module.post_migrate_backfill(cr)
    _logger.info('Damage ledger backfill complete')
