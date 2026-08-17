# -*- coding: utf-8 -*-
"""Per-user known-devices registry for the "Active Sessions" screen.

Odoo's own res.device.log stores one row per login *session* (so the same
phone shows up again after every login) and only knows "android / chrome".
This model keeps exactly ONE row per physical device per user: a repeat
login (or logout) from the same device just bumps ``last_seen``, and the
device gets a human name parsed from the User-Agent (e.g. "SM-A525F
(Android 13)" or "Windows PC (Windows 10/11)") instead of a bare platform
word.
"""
import hashlib
import logging
import re

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class RecycleUserDevice(models.Model):
    _name = 'recycle.user.device'
    _description = "User's Known Devices"
    _order = 'last_seen desc'
    _log_access = False  # rows are written via raw upserts on every login

    user_id = fields.Many2one(
        'res.users', required=True, index=True, ondelete='cascade')
    device_key = fields.Char(
        required=True,
        help='Stable fingerprint of (user, device model, platform, browser '
             'family) — deliberately ignores browser/OS minor versions so an '
             'app update does not create a "new device".')
    device_name = fields.Char(
        help='Human-readable device name parsed from the User-Agent, e.g. '
             '"SM-A525F (Android 13)", "iPhone (iOS 17.5)", "Windows PC".')
    platform = fields.Char()
    browser = fields.Char()
    device_type = fields.Selection(
        [('computer', 'Computer'), ('mobile', 'Mobile')], default='computer')
    ip_address = fields.Char(help='IP address seen at the most recent activity.')
    first_seen = fields.Datetime()
    last_seen = fields.Datetime(index=True)
    last_event = fields.Selection(
        [('login', 'Login'), ('logout', 'Logout')], default='login',
        help='Whether the most recent tracked activity was a login or a logout.')

    _user_device_uniq = models.Constraint(
        'unique(user_id, device_key)',
        'One row per device per user.',
    )

    # ------------------------------------------------------------------
    # User-Agent parsing
    # ------------------------------------------------------------------
    @api.model
    def _parse_user_agent(self, ua):
        ua = ua or ''
        low = ua.lower()

        if 'edg/' in low or 'edge/' in low:
            browser = 'Edge'
        elif 'opr/' in low or 'opera' in low:
            browser = 'Opera'
        elif 'samsungbrowser' in low:
            browser = 'Samsung Internet'
        elif 'firefox' in low or 'fxios' in low:
            browser = 'Firefox'
        elif 'chrome' in low or 'crios' in low:
            browser = 'Chrome'
        elif 'safari' in low:
            browser = 'Safari'
        else:
            browser = 'Unknown'

        m = re.search(r'\(([^)]*)\)', ua)
        parts = [p.strip() for p in (m.group(1) if m else '').split(';')]

        name, platform, device_type = 'Unknown device', 'Unknown', 'computer'
        if 'android' in low:
            platform, device_type = 'Android', 'mobile'
            # The device model is the token that is neither "Linux",
            # "Android N", the "wv"/"U" markers, nor an arch string —
            # e.g. "SM-A525F Build/TP1A..." -> "SM-A525F".
            model = ''
            for p in parts:
                pl = p.lower()
                if (pl.startswith('linux') or pl.startswith('android')
                        or pl in ('u', 'wv', 'k') or pl.startswith('arm')
                        or pl.startswith('x86')):
                    continue
                candidate = re.sub(r'\s*build/.*$', '', p, flags=re.I).strip()
                if candidate:
                    model = candidate
            vm = re.search(r'android\s+([\d.]+)', low)
            ver = vm.group(1) if vm else ''
            name = (model or 'Android device') + (' (Android %s)' % ver if ver else '')
        elif 'iphone' in low or 'ipad' in low or 'ipod' in low:
            platform, device_type = 'iOS', 'mobile'
            dev = 'iPhone' if 'iphone' in low else ('iPad' if 'ipad' in low else 'iPod')
            vm = re.search(r'os\s+([\d_]+)', low)
            ver = vm.group(1).replace('_', '.') if vm else ''
            name = dev + (' (iOS %s)' % ver if ver else '')
        elif 'windows' in low:
            platform = 'Windows'
            vm = re.search(r'windows nt ([\d.]+)', low)
            winver = {'10.0': '10/11', '6.3': '8.1', '6.2': '8', '6.1': '7'}.get(
                vm.group(1) if vm else '', '')
            name = 'Windows PC' + (' (Windows %s)' % winver if winver else '')
        elif 'mac os x' in low or 'macintosh' in low:
            platform, name = 'macOS', 'Mac'
        elif 'linux' in low:
            platform, name = 'Linux', 'Linux PC'

        return {'name': name, 'platform': platform,
                'browser': browser, 'device_type': device_type}

    @api.model
    def _device_key(self, user_id, ua):
        info = self._parse_user_agent(ua)
        raw = '%s|%s|%s|%s' % (user_id, info['name'], info['platform'], info['browser'])
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    # ------------------------------------------------------------------
    # Tracking (login / logout / screen refresh)
    # ------------------------------------------------------------------
    @api.model
    def _track(self, req, user_id, event=None):
        """Upsert the device row for the current request's User-Agent.

        Atomic across workers (single ON CONFLICT statement). ``event``
        ('login'/'logout') updates last_event; None (e.g. just viewing the
        sessions screen) only bumps last_seen/ip.
        Never raises: device bookkeeping must not be able to break a login.
        """
        try:
            ua = req.httprequest.headers.get('User-Agent', '')
            info = self._parse_user_agent(ua)
            key = self._device_key(user_id, ua)
            now = fields.Datetime.now()
            ip = req.httprequest.remote_addr or ''
            self.env.cr.execute("""
                INSERT INTO recycle_user_device
                    (user_id, device_key, device_name, platform, browser,
                     device_type, ip_address, first_seen, last_seen, last_event)
                VALUES (%(uid)s, %(key)s, %(name)s, %(platform)s, %(browser)s,
                        %(dtype)s, %(ip)s, %(now)s, %(now)s,
                        COALESCE(%(event)s, 'login'))
                ON CONFLICT (user_id, device_key) DO UPDATE SET
                    last_seen = %(now)s,
                    ip_address = %(ip)s,
                    device_name = %(name)s,
                    last_event = COALESCE(%(event)s, recycle_user_device.last_event)
            """, {
                'uid': user_id, 'key': key, 'name': info['name'],
                'platform': info['platform'], 'browser': info['browser'],
                'dtype': info['device_type'], 'ip': ip, 'now': now,
                'event': event,
            })
        except Exception:
            _logger.warning('Device tracking failed for user %s', user_id, exc_info=True)
