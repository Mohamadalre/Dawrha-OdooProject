/** @odoo-module **/
/**
 * Dashboard Page State Manager
 *
 * This utility toggles body classes to control navbar visibility:
	 * - o_recycle_home_page: indicates we're on a dashboard page
	 * - o_ra_no_main_navbar: hides Odoo's default navbar
	 * - o_ra_dash_admin: only added when the ADMIN dashboard is mounted —
	 *   gates the (forwarded, near-invisible) native Apps launcher toggle.
	 *   Every other role gets it fully display:none'd (see
	 *   dashboard_navbar_fix.css) so it can never flash visible after a
	 *   mobile orientation change, since only admin has a visible button
	 *   that forwards clicks to it.
 *
 * Usage:
 *   import { setDashboardPage, unsetDashboardPage } from "./dashboard_page_state";
 *
 *   onMounted(() => setDashboardPage(isAdmin));
 *   onWillDestroy(() => unsetDashboardPage());
 */

let dashboardPageCount = 0;
let adminDashboardCount = 0;

export function setDashboardPage(isAdmin) {
    dashboardPageCount++;
    if (dashboardPageCount === 1) {
        document.body.classList.add('o_recycle_home_page');
        document.body.classList.add('o_ra_no_main_navbar');
    }
    if (isAdmin) {
        adminDashboardCount++;
        document.body.classList.add('o_ra_dash_admin');
    }
}

export function unsetDashboardPage(isAdmin) {
    dashboardPageCount--;
    if (dashboardPageCount <= 0) {
        dashboardPageCount = 0;
        document.body.classList.remove('o_recycle_home_page');
        document.body.classList.remove('o_ra_no_main_navbar');
    }
    if (isAdmin) {
        adminDashboardCount--;
        if (adminDashboardCount <= 0) {
            adminDashboardCount = 0;
            document.body.classList.remove('o_ra_dash_admin');
        }
    }
}
