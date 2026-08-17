/** @odoo-module **/
/**
 * Browser-storage failure shield.
 *
 * Odoo core's websocket bus worker keeps a debug log in a browser
 * IndexedDB database ("bus_websocket_worker" — odoo/addons/bus/static/
 * src/workers/bus_worker_utils.js, unrelated to this addon). On a browser
 * profile whose disk store is full or corrupted (Chrome LevelDB errors:
 * "FILE_ERROR_NO_SPACE", "Internal error when calculating storage
 * usage"), every write to it rejects with a DOMException that carries NO
 * `.stack` property. This happens on every websocket reconnect — i.e.
 * every time the user switches back to the tab.
 *
 * Odoo's own error reporter then crashes on those exceptions
 * (formatTraceback does `error.stack.split(...)` unguarded), flooding the
 * console with "Cannot read properties of undefined (reading 'split')".
 * The crash happens while Odoo is *building* the error report, before any
 * registered error_handlers run, so the only interception point is a
 * window listener registered ahead of Odoo's own (module bodies execute
 * before services start, so ours is first in line).
 *
 * Real application errors are untouched. Two independent gates decide
 * whether a rejection is this browser-storage noise, not app logic:
 *   (a) no `.stack` at all (DOMExceptions from the storage layer) — any
 *       message content is treated as noise, since a stackless rejection
 *       can never be a thrown JS Error from our own code anyway; or
 *   (b) a `.stack` IS present, but the message is one of a small, exact
 *       set of Chrome storage-engine signatures observed directly from
 *       this deployment's own console (FILE_ERROR_NO_SPACE, a raw
 *       LevelDB ".ldb" I/O error, or the idb-keyval "UnknownError:
 *       Internal error" pair) — deliberately narrow so nothing else with
 *       a real stack is ever swallowed.
 */

// Part 1 — self-heal: drop the bus worker's log DB once a day so a
// corrupted instance gets recreated fresh (best-effort; a profile-level
// storage failure can make even this fail, which Part 2 then absorbs).
(function () {
    if (typeof indexedDB === 'undefined') return;
    var THROTTLE_KEY = 'recycle_bus_db_gc_at';
    var ONE_DAY_MS = 24 * 60 * 60 * 1000;
    var last = 0;
    try { last = parseInt(localStorage.getItem(THROTTLE_KEY), 10) || 0; } catch (e) { /* ignore */ }
    if (Date.now() - last < ONE_DAY_MS) return;
    try { localStorage.setItem(THROTTLE_KEY, String(Date.now())); } catch (e) { /* ignore */ }
    try {
        var req = indexedDB.deleteDatabase('bus_websocket_worker');
        req.onerror = function () {}; // best-effort — never let this itself throw
    } catch (e) { /* best-effort */ }
})();

// Part 2 — absorb browser-storage-engine rejections before Odoo's error
// service crashes on the stackless ones, and before the stack-bearing
// ones spam the console for something the user can't act on anyway.
(function () {
    var STORAGE_NOISE = /Internal error|FILE_ERROR_NO_SPACE|storage usage|IndexedDB|Quota|message channel closed/i;
    // Narrow, exact-signature set for rejections that DO carry a stack —
    // real LevelDB/idb-keyval internals seen directly in this
    // deployment's console, never something application code throws.
    var EXACT_STORAGE_SIGNATURES = [
        /FILE_ERROR_NO_SPACE/,
        /IO error:.*\.ldb/,
    ];
    window.addEventListener('unhandledrejection', function (ev) {
        var r = ev.reason;
        var hasStack = r != null && typeof r.stack === 'string' && r.stack;
        var msg = r != null ? String(r.message || r.name || r) : '';

        var suppress = false;
        if (!hasStack) {
            // A missing/non-string stack is the precise precondition of
            // the formatTraceback crash — always storage-layer noise.
            suppress = STORAGE_NOISE.test(msg)
                || (typeof Event !== 'undefined' && r instanceof Event);
        } else {
            suppress = EXACT_STORAGE_SIGNATURES.some(function (re) { return re.test(msg); })
                || (r.name === 'UnknownError' && r.message === 'Internal error');
        }
        if (suppress) {
            ev.preventDefault();
            if (ev.stopImmediatePropagation) ev.stopImmediatePropagation();
        }
    });
})();
