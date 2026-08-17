# -*- coding: utf-8 -*-
"""The loading splash must be in the HTML the SERVER sends.

That is the whole point of it, and the only part a test can meaningfully pin.
Loading the back office means downloading a large JS/CSS bundle, and until that
arrives the browser has a parsed <body> with nothing in it. Anything that ships
inside the bundle — a component, a stylesheet, an OWL template — cannot cover
that gap, because it IS the thing being waited for.

So these tests assert the one property that makes the splash work: it is
present in the first response, with its styles inline, before any asset has
been fetched. A hard reload (Ctrl+Shift+R) empties the cache and re-runs
exactly this request, which is why it is also the case that most needs it.

They also pin the fences that keep it from appearing where it would be wrong,
and — most importantly — that a way to REMOVE it always ships with it. An
overlay with no removal path turns a slow page into a permanently unusable one,
which is strictly worse than the blank screen it replaced.
"""
from odoo.tests.common import HttpCase, tagged

from .common import make_warehouse


@tagged('post_install', '-at_install')
class TestSplashScreen(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = make_warehouse(cls.env, **{
            'name': 'Splash WH', 'code': 'SPLASHWH',
        })

    def _backend_html(self, login, password):
        self.authenticate(login, password)
        res = self.url_open('/web')
        self.assertEqual(res.status_code, 200, res.text)
        return res.text

    # ------------------------------------------------------------------
    def test_splash_is_server_rendered_for_the_back_office(self):
        """Present in the first response — not delivered by the bundle."""
        html = self._backend_html('admin', 'admin')

        self.assertIn('recycle_splash', html)
        # The logo, not a spinner: the point is that the user sees WHOSE
        # application is loading.
        self.assertIn('/recycle_warehouse/static/src/img/icon_logo.png', html)

    def test_styles_and_animation_are_inline(self):
        """A splash that waits for a stylesheet is not a splash.

        The CSS cannot live in `web.assets_backend`: that bundle is one of the
        things being waited for, so the splash would appear only once the wait
        was already over.
        """
        html = self._backend_html('admin', 'admin')
        splash = html[html.index('recycle_splash'):]

        # Positioned and painted by attributes carried in the document itself.
        self.assertIn('position:fixed', splash)
        # The keyframes travel with it too.
        self.assertIn('@keyframes recycle_splash_spin', splash)
        self.assertIn('@keyframes recycle_splash_glow', splash)

    def test_it_can_always_be_taken_down(self):
        """A removal path ships in the same page load, with a hard deadline.

        Note what is NOT asserted: that `recycle_splash.js` appears in the HTML.
        It never does — Odoo concatenates the bundle into one
        `web.assets_web.min.js`, so no individual source file is named in the
        document. The meaningful checks are that the remover is FIRST in the
        bundle declaration (nothing can fail ahead of it) and that it carries
        more than one way out.
        """
        import os

        addon_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        with open(os.path.join(addon_root, '__manifest__.py'), encoding='utf-8') as fh:
            manifest = fh.read()
        backend = manifest[manifest.index("'web.assets_backend'"):]
        first_js = backend[backend.index('recycle_warehouse/static'):]
        self.assertTrue(
            first_js.startswith('recycle_warehouse/static/src/js/recycle_splash.js'),
            'the splash remover must be the first entry in web.assets_backend — '
            'anything ahead of it that throws would strand the overlay',
        )

        with open(
            os.path.join(addon_root, 'static', 'src', 'js', 'recycle_splash.js'),
            encoding='utf-8',
        ) as fh:
            source = fh.read()

        # Two independent exits, because the failure modes are not symmetric:
        # removed early costs one bare frame, never removed costs the whole
        # application.
        self.assertIn('MAX_SPLASH_MS', source)
        self.assertIn('MutationObserver', source)

        # And explicitly NOT `window.load`.
        #
        # It was here, and it was the reason the splash flashed and vanished
        # while the dashboard was still fetching: `load` fires once the bundle
        # and images have settled, which is BEFORE the first request goes out.
        # Removing on it hands the user the empty frame and spinner the splash
        # exists to cover.
        self.assertNotIn(
            "addEventListener('load'", source,
            'window.load fires before the dashboard fetches — removing on it '
            'reintroduces the blank frame this splash exists to hide',
        )

    def test_waits_for_the_fetch_not_just_the_mount(self):
        """The splash must outlive the render, not just the bundle.

        `.o_web_client` — the old signal — is a class on <body> ITSELF, present
        from the moment the tag opens. Waiting on it measured nothing: the
        splash came down before a single row had been asked for.

        The gate is now BOTH: an action rendered inside `.o_action_manager`,
        AND no `.o_ra_loading` left anywhere. Every dashboard in this addon
        renders that element while its first fetch is in flight.
        """
        import os

        addon_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(
            os.path.join(addon_root, 'static', 'src', 'js', 'recycle_splash.js'),
            encoding='utf-8',
        ) as fh:
            source = fh.read()

        self.assertIn('o_action_manager', source)
        self.assertIn('o_ra_loading', source)
        self.assertNotIn(
            "querySelector('.o_web_client')", source,
            'that class sits on <body> and is true before anything has loaded',
        )

    def test_respects_reduced_motion(self):
        """Motion is decoration; someone who asked for less still gets the logo."""
        html = self._backend_html('admin', 'admin')

        self.assertIn('prefers-reduced-motion', html)

    def test_not_shown_on_the_public_website(self):
        """`web.layout` also renders the public site, which never sits blank.

        The splash is fenced to the back office by `body_classname`. Without
        that fence every server-rendered public page would flash an overlay
        over content that was already there.
        """
        res = self.url_open('/web/login')
        self.assertEqual(res.status_code, 200)

        self.assertNotIn('recycle_splash', res.text)
