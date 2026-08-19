# -*- coding: utf-8 -*-
import json
from urllib import request as _urlrequest, error as _urlerror

from odoo import _, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ── Backend integration ────────────────────────────────────────────
    # Where the NestJS backend lives, and the shared secret that authenticates
    # the outbound pings (fleet / inventory / warehouse / suggestions). Both
    # were system parameters with NO screen, so an unconfigured deployment sent
    # nothing and gave no hint why — a truck added here simply never reached the
    # backend. Surfacing them here is the supported place to wire the link.
    backend_base_url = fields.Char(
        string='Backend base URL',
        config_parameter='recycle.backend_base_url',
        help='The NestJS backend origin the pings are sent to, e.g. '
             'https://api.dawrha.example (or http://host.docker.internal:3000 '
             'when Odoo runs in Docker and the backend runs on the host). '
             'Empty = every outbound sync is disabled.')
    backend_webhook_secret = fields.Char(
        string='Backend webhook secret',
        config_parameter='recycle.backend_webhook_secret',
        help='Shared secret sent as x-odoo-webhook-secret. Must match the '
             'backend ODOO_WEBHOOK_SECRET exactly, or the backend rejects the '
             'ping (401). Empty = the signed pings are not sent.')

    def action_test_backend_connection(self):
        """Ping the backend NOW and report the result to the admin.

        The whole class of "a truck/warehouse added in Odoo never showed in the
        app" was ONE silent failure: the outbound pings need a base URL and a
        shared secret, and when either was unset every ping was dropped with
        nothing on screen. This turns that invisible state into a button: it
        makes a real signed request to the backend's fleet webhook (payload-less,
        harmless — it only asks the backend to re-read the fleet) and shows
        whether the link, the secret and the network path actually work.
        """
        self.ensure_one()
        icp = self.env['ir.config_parameter'].sudo()
        base = (icp.get_param('recycle.backend_base_url') or '').rstrip('/')
        secret = icp.get_param('recycle.backend_webhook_secret') or ''
        if not base:
            return self._conn_notice('warning', _('No backend base URL is set.'))
        if not secret:
            return self._conn_notice('warning', _('No backend webhook secret is set.'))

        route = (icp.get_param('recycle.backend_route_fleet')
                 or '/api/v1/odoo/webhooks/fleet')
        try:
            req = _urlrequest.Request(
                base + route,
                data=json.dumps({}).encode('utf-8'),
                headers={'Content-Type': 'application/json',
                         'x-odoo-webhook-secret': secret},
                method='POST')
            with _urlrequest.urlopen(req, timeout=8) as resp:
                code = resp.status
            if 200 <= code < 300:
                return self._conn_notice(
                    'success',
                    _('Connected. The backend accepted the ping (HTTP %s) — sync '
                      'is wired correctly.') % code)
            return self._conn_notice(
                'danger', _('The backend answered HTTP %s — check the secret.') % code)
        except _urlerror.HTTPError as exc:
            hint = _(' (the webhook secret does not match)') if exc.code == 401 else ''
            return self._conn_notice(
                'danger', _('The backend rejected the ping: HTTP %s%s.') % (exc.code, hint))
        except Exception as exc:  # noqa: BLE001 — surfaced to the admin, not raised
            return self._conn_notice(
                'danger',
                _('Could not reach the backend at %s: %s. If Odoo runs in Docker '
                  'and the backend on the host, use http://host.docker.internal:'
                  '<port> and make sure the host firewall allows the container.')
                % (base, exc))

    def _conn_notice(self, kind, message):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': kind,
                'title': _('Backend connection'),
                'message': message,
                'sticky': kind != 'success',
            },
        }

    sorting_tolerance_threshold_1 = fields.Float(
        string='Auto-accepted shortage per material (%)',
        config_parameter='warehouse.sorting_tolerance_threshold_1',
        default=3.0,
        help='Any shortage for a single material at or below this value is '
             'accepted automatically, with no warning. Represents the '
             'natural tolerance margin (humidity, dust, minor residue).')
    sorting_tolerance_threshold_2 = fields.Float(
        string='Maximum shortage per material before manager approval (%)',
        config_parameter='warehouse.sorting_tolerance_threshold_2',
        default=15.0,
        help='Any shortage for a single material above the first threshold '
             'and up to this value is accepted but requires a mandatory '
             'reason. Any shortage beyond this value blocks finishing the '
             'sorting and requires the warehouse manager\'s approval.')
