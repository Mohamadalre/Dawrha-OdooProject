/** @odoo-module **/
/*
 * Recycle Warehouse — Odoo Backend Menu Translator
 * ------------------------------------------------
 * Translates the Odoo 19 backend navbar, section menus, submenus,
 * and mobile drawers into Arabic when the recycle_wms_lang key is 'ar'.
 *
 * How it works:
 *   1. On load, translates everything once.
 *   2. A click capture listener translates immediately when any nav
 *      element is clicked (before Odoo's re-render completes).
 *   3. Three follow-up passes (30/150/600 ms) catch async re-renders.
 *   4. A debounced MutationObserver handles dynamic DOM updates.
 *   5. A 2-second interval re-applies translation as a safety net
 *      while the language is 'ar'.
 *   6. A resize listener re-translates when the viewport changes
 *      between desktop and mobile breakpoints.
 */

(function () {
    'use strict';

    try {
        /* ── Constants ──────────────────────────────────── */
        var LANG_KEY = 'recycle_wms_lang';
        var DEBOUNCE_MS = 100;
        var INTERVAL_MS = 2000;
        var RETRY_DELAYS = [30, 150, 600];

        /* ── Helpers ─────────────────────────────────────── */
        function getLang() {
            var v = localStorage.getItem(LANG_KEY);
            return v === 'ar' ? 'ar' : 'en';
        }

        function tr(key) {
            var fn = window.dwTrBackend || window.tr;
            return typeof fn === 'function' ? fn(key) : key;
        }

        /* ── Core: translate textual content ────────────── */
        function translateTextContent(root) {
            if (!root) return;
            try {
                var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null, false);
                var node;
                while ((node = walker.nextNode())) {
                    var text = (node.textContent || '').trim();
                    if (!text || text.length < 2 || text.length > 60) continue;
                    var translated = tr(text);
                    if (translated !== text) node.textContent = translated;
                }
            } catch (_) { /* single-node failures are non-fatal */ }
        }

        /* ── Selectors for every piece of backend nav UI ── */
        var CONTAINER_SELECTORS = [
            '.o_navbar',
            '.o_main_navbar',
            '.o_navbar_apps_menu',
            '.o_menu_brand',
            '.o_menu_sections',
            '.o_menu_sections_more',
            '.o_menu_systray',
            '.o_user_menu',
            '.o_app_menu_sidebar',
            '.o_sidebar_topbar',
            '.o_burger_menu_content',
            '.o_burger_menu',
            '.o_menu_section',
            '.o_menu_header',
            '.o_sub_menu',
            '.o_app_menu',
            '.o_extra_menu_items',
            '.o_user_menu_mobile',
            '.o_control_panel',
            '.o-dropdown--menu',
            '.dropdown-menu',
            '.o_navbar_breadcrumbs',
            '.o_dropdown_menu_group_entry',
        ].join(', ');

        var ITEM_SELECTORS = [
            // Desktop sections & dropdowns
            '.o_nav_entry',
            '[role="menuitem"]',
            '[role="menu"] a',
            '.dropdown-item',
            '.dropdown-header',
            '.dropdown-menu_group',
            '.o_menu_section > a',
            '.o_menu_sections > a',
            // Mobile sidebar & burger
            '.o_app_menu_sidebar a',
            '.o_burger_menu a',
            '.o_burger_menu .o_app',
            '.o_sidebar_topbar a',
            '.o_sidebar_topbar span',
            '.o_sidebar_close',
            // User menus
            '.o_user_menu_mobile a',
        ].join(', ');

        /* ── translateMenus: scan and translate ──────────── */
        function translateMenus() {
            try {
                if (getLang() !== 'ar') return;

                // Translate container subtrees (text nodes)
                var containers = document.querySelectorAll(CONTAINER_SELECTORS);
                for (var i = 0; i < containers.length; i++)
                    translateTextContent(containers[i]);

                // Translate individual items (element textContent)
                var items = document.querySelectorAll(ITEM_SELECTORS);
                for (var j = 0; j < items.length; j++) {
                    var el = items[j];
                    var text = (el.textContent || '').trim();
                    if (!text) continue;
                    var translated = tr(text);
                    if (translated !== text) el.textContent = translated;
                }
            } catch (_) { /* silently ignore selector/runtime errors */ }
        }

        /* ── Immediate + deferred passes ─────────────────── */
        function translateMenusNow() {
            translateMenus();
            for (var d = 0; d < RETRY_DELAYS.length; d++)
                setTimeout(translateMenus, RETRY_DELAYS[d]);
        }

        /* ── Debounced re-translation for MutationObserver ─ */
        var debounceTimer = null;
        function scheduleTranslate() {
            if (debounceTimer) clearTimeout(debounceTimer);
            debounceTimer = setTimeout(function () {
                debounceTimer = null;
                translateMenus();
            }, DEBOUNCE_MS);
        }

        /* ── Public API ──────────────────────────────────── */
        window.dwTranslateMenus = translateMenus;

        /* ── Events ─────────────────────────────────────── */

        // Language change from another tab
        window.addEventListener('storage', function (e) {
            if (e.key === LANG_KEY) setTimeout(translateMenus, 50);
        });

        // Language change from the admin dashboard
        window.addEventListener('dw-lang-change', function () {
            translateMenusNow();
        });

        // Click capture — translate immediately when interacting with nav
        document.addEventListener('click', function (e) {
            if (getLang() !== 'ar') return;
            var navElements = '.o_main_navbar, .o_menu_sections, .dropdown, ' +
                '[role="menubar"], .o_app_menu_sidebar, .o_burger_menu, ' +
                '.o_menu_toggle, .o_mobile_menu_toggle';
            if (e.target && e.target.closest && e.target.closest(navElements))
                translateMenusNow();
        }, true);

        // Viewport resize (desktop ↔ mobile switch)
        window.addEventListener('resize', function () {
            if (getLang() !== 'ar') return;
            setTimeout(translateMenus, 100);
            setTimeout(translateMenus, 500);
        });

        /* ── Initialisation ─────────────────────────────── */
        function onReady() {
            translateMenus();
            // Safety interval
            setInterval(function () {
                if (getLang() === 'ar') translateMenus();
            }, INTERVAL_MS);
        }

        if (document.readyState === 'loading')
            document.addEventListener('DOMContentLoaded', onReady);
        else
            onReady();

        /* ── MutationObserver: catch dynamic re-renders ──── */
        var target = document.querySelector('.o_main_navbar') || document.body;
        if (target) {
            var observer = new MutationObserver(function () {
                if (getLang() === 'ar') scheduleTranslate();
            });
            observer.observe(target, {
                childList: true,
                subtree: true,
            });
        }
    } catch (e) {
        if (console && console.warn)
            console.warn('dwBackendI18n: initialisation error —', e);
    }
})();