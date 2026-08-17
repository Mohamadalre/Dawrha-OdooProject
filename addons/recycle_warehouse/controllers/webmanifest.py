# -*- coding: utf-8 -*-
"""Override Odoo's default PWA identity (icons, app name, theme color) with
Dawrha's own branding, so the Chrome "Install app" prompt / download bar and
the installed app icon show our logo instead of the stock Odoo icon."""
from odoo import http
from odoo.addons.web.controllers.webmanifest import WebManifest
from odoo.http import request

APP_NAME = 'Dawrha'
ICON_192 = '/recycle_warehouse/static/src/img/pwa_icon_192.png'
ICON_512 = '/recycle_warehouse/static/src/img/pwa_icon_512.png'
THEME_COLOR = '#059669'


class DawrhaWebManifest(WebManifest):

    def _get_webmanifest(self):
        manifest = super()._get_webmanifest()
        manifest['name'] = APP_NAME
        manifest['short_name'] = APP_NAME
        manifest['background_color'] = '#0f172a'
        manifest['theme_color'] = THEME_COLOR
        manifest['icons'] = [
            {'src': ICON_192, 'sizes': '192x192', 'type': 'image/png'},
            {'src': ICON_512, 'sizes': '512x512', 'type': 'image/png'},
        ]
        return manifest

    def _icon_path(self):
        # Used for /odoo/offline and as an Apple-touch-icon fallback.
        return 'recycle_warehouse/static/src/img/pwa_icon_192.png'
