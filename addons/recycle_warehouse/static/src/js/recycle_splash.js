/** @odoo-module **/

/**
 * Takes the loading splash down once the DASHBOARD is actually on screen.
 *
 * The splash markup lives in the page itself (see `splash_templates.xml`), with
 * its styles inline, so it paints before any bundle arrives. THIS file is part
 * of a bundle — which is exactly why it is the right place to remove it: this
 * module running at all is proof the download finished.
 *
 * The removal is deliberately belt-and-braces, because the failure modes are
 * not symmetric. A splash removed a fraction early shows a bare frame for one
 * frame; a splash never removed makes the application unusable and looks like a
 * hang. So there are three independent ways out:
 *
 *   1. the dashboard rendering AND finishing its first fetch (the real signal),
 *   2. a hard timeout, in case that never happens at all.
 *
 * Whichever runs first wins; the other finds it already gone.
 */

/** Longest the splash may ever stay up, however badly the boot goes. */
const MAX_SPLASH_MS = 12000;

/** Matches the CSS transition in the template, so it fades rather than blinks. */
const FADE_MS = 450;

let removed = false;

/**
 * Take the splash down. Returns whether it actually did.
 *
 * The return value matters: callers use it to decide whether their job is
 * finished, and "the element was not there yet" is not the same answer as
 * "the splash is gone".
 */
function removeSplash() {
    if (removed) return true;
    const el = document.getElementById('recycle_splash');
    if (!el) {
        // NOT `removed = true`, and NOT a success.
        //
        // This bundle is loaded from <head>, so the first call can happen while
        // <body> is still being parsed and the splash does not exist yet.
        // Latching "removed" on that miss poisoned every later attempt: the
        // element appeared a moment afterwards and nothing would ever take it
        // down again.
        return false;
    }
    removed = true;
    el.style.opacity = '0';
    el.style.visibility = 'hidden';
    el.style.pointerEvents = 'none'; // clicks land on the app during the fade
    setTimeout(() => el.remove(), FADE_MS);
    return true;
}

/**
 * Is the dashboard actually ON SCREEN — rendered AND done fetching?
 *
 * Two conditions, and the second is the one that was missing:
 *
 *   1. an action has rendered inside `.o_action_manager`. The old test was
 *      `.o_web_client`, which is a class on <body> ITSELF — present from the
 *      moment the tag opens, so it was true before anything had loaded and the
 *      splash came down instantly. It looked like it worked; it was measuring
 *      nothing.
 *
 *   2. no `.o_ra_loading` is left. Every dashboard in this addon renders that
 *      element while its first fetch is in flight (118 places). Removing the
 *      splash on mount alone just swaps one waiting screen for another — the
 *      user watches an empty frame and a spinner instead, which is exactly the
 *      blank page the splash exists to hide.
 */
function dashboardReady() {
    const action = document.querySelector('.o_action_manager');
    if (!action || !action.firstElementChild) return false;
    return !document.querySelector('.o_ra_loading');
}

/**
 * Hold the splash until the dashboard is genuinely ready, then take it down.
 *
 * Re-checked on every DOM mutation rather than on a timer: the fetch settles at
 * a moment nothing can predict, and polling either wastes work or adds a delay
 * the user sees.
 */
function watchForDashboard() {
    if (dashboardReady() && removeSplash()) {
        return;
    }
    const observer = new MutationObserver(() => {
        if (!dashboardReady()) return;
        observer.disconnect();
        // One frame of grace: the content exists a moment before it has
        // painted, and removing on the same tick can show a bare frame.
        requestAnimationFrame(() => requestAnimationFrame(removeSplash));
    });
    observer.observe(document.body, { childList: true, subtree: true });

    // The observer holds a reference to the whole body subtree; drop it once
    // the deadline has passed whether or not it ever fired.
    setTimeout(() => observer.disconnect(), MAX_SPLASH_MS);
}

/**
 * Arm the removal — UNCONDITIONALLY.
 *
 * This used to be guarded by `if (document.getElementById('recycle_splash'))`,
 * which looked like a sensible "only do this on pages that have a splash" and
 * was in fact the bug that stopped the whole thing working. Odoo serves this
 * bundle from <head>, so the guard runs while <body> is still being parsed:
 * the splash element does not exist yet, the check is false, and NOTHING is
 * ever registered. The splash then sits over the dashboard for good — the
 * observer and the timeout were both inside the branch that
 * never ran.
 *
 * There is nothing to guard against anyway: `removeSplash` is a no-op when the
 * element is absent, and `watchForDashboard` disconnects on its own deadline.
 */
function arm() {
    watchForDashboard();

    // NO `window.load` fallback.
    //
    // It used to be here and it was actively harmful: `load` fires when the
    // bundle and images have settled, which is BEFORE the dashboard has asked
    // the server for anything. Taking the splash down then hands the user the
    // empty frame and spinner that the splash exists to cover — the exact
    // complaint that led here.
    //
    // What remains is the real signal (above) and a hard deadline (below).
    // Pages with no dashboard at all — Settings, Discuss — still clear
    // promptly, because they render an action and never show `.o_ra_loading`.
    setTimeout(removeSplash, MAX_SPLASH_MS);
}

// `watchForDashboard` observes document.body, which must therefore exist. From
// <head> it does not yet — so wait for the parser when that is the case.
if (document.body) {
    arm();
} else {
    document.addEventListener('DOMContentLoaded', arm, { once: true });
}
