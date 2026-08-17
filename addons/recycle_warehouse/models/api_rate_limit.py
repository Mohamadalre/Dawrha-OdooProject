# -*- coding: utf-8 -*-
"""Rate limiting for the external NestJS-facing REST API
(controllers/api.py) — a leaked or guessed X-API-KEY would otherwise let
an attacker create unlimited orders/shipments with no throttle at all.

One counter row per one-minute window, incremented atomically with a
single upsert (safe across multiple Odoo worker processes — no shared
in-memory state, which would silently stop working the moment the
install grows past one worker). Old windows are garbage-collected by
Odoo's autovacuum cron so the table never grows unbounded.
"""
import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Generous enough for a legitimate backend integration doing bursts of
# order/shipment creation, low enough that a leaked key can't be used to
# hammer the database. Tune via the recycle.api_rate_limit_per_minute
# system parameter if a real integration ever needs more.
DEFAULT_LIMIT_PER_MINUTE = 120


class RecycleApiRateLimit(models.Model):
    _name = 'recycle.api.rate.limit'
    _description = 'External API Rate Limit Counter (per-minute window)'
    _rec_name = 'window_start'
    _log_access = False  # pure counter table — no create/write tracking needed

    window_start = fields.Datetime(required=True, index=True)
    request_count = fields.Integer(default=0)

    # Odoo 19's replacement for the old _sql_constraints list — this MUST
    # actually create the underlying Postgres unique index, since _hit()
    # below relies on it for its ON CONFLICT (window_start) upsert.
    _window_start_uniq = models.Constraint(
        'unique(window_start)',
        'One counter row per one-minute window.',
    )

    @api.autovacuum
    def _gc_old_windows(self):
        cutoff = fields.Datetime.now() - timedelta(hours=1)
        self.sudo().search([('window_start', '<', cutoff)]).unlink()

    @api.model
    def _hit(self):
        """Record one request in the current minute's bucket and return
        the running count for that bucket (atomic upsert — race-safe
        even with several workers hitting it at the same instant)."""
        now = fields.Datetime.now()
        window = now.replace(second=0, microsecond=0)
        self.env.cr.execute("""
            INSERT INTO recycle_api_rate_limit (window_start, request_count)
            VALUES (%s, 1)
            ON CONFLICT (window_start)
            DO UPDATE SET request_count = recycle_api_rate_limit.request_count + 1
            RETURNING request_count
        """, [window])
        return self.env.cr.fetchone()[0]

    @api.model
    def check(self):
        """True if the external API is still within its per-minute quota."""
        limit = self.env['ir.config_parameter'].sudo().get_param(
            'recycle.api_rate_limit_per_minute')
        try:
            limit = int(limit) if limit else DEFAULT_LIMIT_PER_MINUTE
        except (TypeError, ValueError):
            limit = DEFAULT_LIMIT_PER_MINUTE
        count = self.sudo()._hit()
        if count > limit:
            _logger.warning(
                'External API rate limit exceeded: %s requests this minute '
                '(limit %s).', count, limit)
            return False
        return True
