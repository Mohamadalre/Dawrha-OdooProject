/** @odoo-module **/
/**
 * Shared plumbing for the five role dashboards (Admin / Manager /
 * Reception / Sorting / Output). Anything here must stay free of
 * component state (`this`) so every dashboard can delegate to it without
 * behavioural coupling.
 */

/** JSON-RPC POST helper — the contract used by Admin, Manager, Output and
 *  Reception: resolves to `result` when present, otherwise the raw
 *  envelope; network errors propagate to the caller's try/catch. */
export async function rpcJson(url, params) {
    const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        cache: 'no-store',
        body: JSON.stringify({ jsonrpc: '2.0', method: 'call', params: params || {} }),
    });
    const wrapper = await resp.json();
    if (wrapper && 'result' in wrapper) return wrapper.result;
    // A RAISED server error arrives as { error: { message, data: { message } } }.
    // Returning that object let callers print it straight into a toast, where it
    // rendered as the useless "[object Object]". Normalise it to a plain
    // { error: string } so every caller shows the real reason instead.
    if (wrapper && wrapper.error) {
        const e = wrapper.error;
        return { error: (e.data && e.data.message) || e.message || 'Server error' };
    }
    return wrapper || {};
}

/** Sorting dashboard's variant of the same call: never throws — network
 *  failures and server errors both come back as `{error}` so its
 *  callers can stay linear without try/catch. */
export async function rpcJsonSafe(url, params) {
    try {
        const result = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'call',
                id: new Date().getTime(),
                params: params || {},
            }),
            credentials: 'same-origin',
            cache: 'no-store',
        });
        const data = await result.json();
        if (data && 'result' in data) return data.result;
        // Same normalisation as rpcJson: a raised server error is an object, and
        // must reach the caller as { error: string }, never the raw object.
        if (data && data.error) {
            const e = data.error;
            return { error: (e.data && e.data.message) || e.message || 'Server error' };
        }
        return data || {};
    } catch (e) {
        return { error: e.message || 'Request failed' };
    }
}

/** recycle.warehouse.governorate is now a stored mirror of the linked
 *  recycle.province NAME (the governorate list moved out of a hard-coded
 *  Selection into a table synced from the backend), so the value arriving
 *  here is already display-ready. The legacy Selection keys are still mapped
 *  so a record read from a cached/stale payload never shows "damascus" raw.
 *  Usage: govLabel(state.myWarehouse.governorate, this.tr.bind(this)) */
export const GOVERNORATE_LABELS = {
    damascus: 'Damascus', rif_dimashq: 'Rif Dimashq', aleppo: 'Aleppo',
    homs: 'Homs', hama: 'Hama', latakia: 'Latakia', tartus: 'Tartus',
    idlib: 'Idlib', deir_ez_zor: 'Deir ez-Zor', raqqa: 'Raqqa',
    hasakah: 'Al-Hasakah', daraa: 'Daraa', sweida: 'As-Suwayda',
    quneitra: 'Quneitra',
};
export function govLabel(code, trFn) {
    if (!code) return '—';
    // Many2one values arrive as [id, display_name] when read directly.
    const raw = Array.isArray(code) ? code[1] : code;
    if (!raw) return '—';
    const label = GOVERNORATE_LABELS[raw];
    // Already a real name (the common case now): show it as the backend
    // wrote it — translating a user-authored province name would fail anyway.
    if (!label) return raw;
    return trFn ? trFn(label) : label;
}

/** Cursor-based "load more as you scroll" pager for the long-lived lists
 *  (shipments, orders, applicants, deleted employees…) that used to be
 *  hard-capped at a fixed limit with no way to reach older rows. Every
 *  list keeps using `orm.searchRead` itself — this just standardizes the
 *  "first page" / "next page by id cursor" shape so each screen doesn't
 *  re-implement the same three methods. `id desc` cursoring (not offset)
 *  so a page never skips/duplicates rows if new records are inserted
 *  while the user is scrolling. */
export function makePager(orm, { model, fields, order = 'id desc', pageSize = 200, context }) {
    const opts = context ? { order, limit: pageSize, context } : { order, limit: pageSize };
    return {
        pageSize,
        async fetchFirst(domain) {
            const rows = await orm.searchRead(model, domain, fields, opts);
            return { rows, hasMore: rows.length === pageSize };
        },
        async fetchMore(domain, lastId) {
            const d = lastId ? domain.concat([["id", "<", lastId]]) : domain;
            const rows = await orm.searchRead(model, d, fields, opts);
            return { rows, hasMore: rows.length === pageSize };
        },
    };
}

/** One `window` scroll listener shared by every list on a dashboard.
 *  `getView()` returns the component's current `state.view`; `handlers`
 *  maps a view name to the loadMore function to call when the user nears
 *  the bottom of the page. Call the returned function in onWillDestroy to
 *  detach. No page-number UI anywhere — the next page loads itself. */
export function attachInfiniteScroll(getView, handlers) {
    const onScroll = () => {
        const fn = handlers[getView()];
        if (!fn) return;
        const nearBottom = (window.innerHeight + window.scrollY) >= (document.documentElement.scrollHeight - 400);
        if (nearBottom) fn();
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
}

/**
 * Wires the shared MessageDialog onto a dashboard component.
 *
 * Call once in `setup()`. It adds `state.dialog` plus the three handlers the
 * template binds to, so a screen gets an in-page dialog without copying any of
 * it — which is how nineteen `alert()` calls accumulated in the first place.
 *
 * `alert()` and `confirm()` are not merely ugly here: they BLOCK the thread, so
 * an OWL component that calls one mid-render leaves the screen half-drawn until
 * the user dismisses it. These resolve through the normal reactive state, so
 * the page keeps painting.
 *
 * @param {Object} cmp  the component (`this` inside setup)
 */
export function useMessageDialog(cmp) {
    cmp.state.dialog = null;

    /** A message with a single OK. `kind` drives the colour and icon. */
    cmp.showMessage = (title, message, kind = 'info') => {
        cmp.state.dialog = { title, message, kind, onConfirm: null };
    };

    /** The error path — what every `alert()` in a catch block should have been. */
    cmp.showError = (message, title) => {
        cmp.state.dialog = {
            title: title || (cmp.tr ? cmp.tr('Something went wrong') : 'Something went wrong'),
            message,
            kind: 'error',
            onConfirm: null,
        };
    };

    cmp.showSuccess = (message, title) => {
        cmp.state.dialog = {
            title: title || (cmp.tr ? cmp.tr('Done') : 'Done'),
            message,
            kind: 'success',
            onConfirm: null,
        };
    };

    /**
     * Replaces `window.confirm()`. Returns a PROMISE of the answer.
     *
     * A callback API was the first shape tried, and it was the wrong one: every
     * call site would have had to be turned inside out, its whole body moved
     * into a closure, for a change that alters nothing about what the code
     * does. Thirteen such rewrites in this file alone is thirteen chances to
     * move a line into the wrong branch.
     *
     * Awaiting instead keeps the shape `confirm()` already had —
     *
     *     if (!(await this.askConfirm(title, msg))) return;
     *
     * — so the diff at each site is one line, and a reviewer can see that the
     * guard still guards the same statements. It is also the honest signature:
     * the answer genuinely arrives later, and `await` is how that is said.
     */
    cmp.askConfirm = (title, message, confirmLabel) =>
        new Promise((resolve) => {
            cmp.state.dialog = {
                title,
                message,
                kind: 'info',
                confirmLabel,
                // Presence of this is also what tells the template to render a
                // Cancel button — a plain message has none.
                onConfirm: () => resolve(true),
                onCancel: () => resolve(false),
            };
        });

    /** Dismissal — the X, the overlay, or Cancel — always answers "no". */
    cmp.closeDialog = () => {
        const dialog = cmp.state.dialog;
        cmp.state.dialog = null;
        if (dialog && dialog.onCancel) dialog.onCancel();
    };

    cmp.confirmDialog = () => {
        const dialog = cmp.state.dialog;
        // Cleared BEFORE resolving: the awaiting code may open another dialog
        // (an error raised while confirming), and this line must not wipe it.
        cmp.state.dialog = null;
        if (dialog && dialog.onConfirm) dialog.onConfirm();
    };
}

/**
 * Turns `state.loading` into `state.slowLoading` — true only once a load has
 * lasted long enough to be worth explaining.
 *
 * Showing the branded screen the instant loading starts would flash it for the
 * 80ms a cached dashboard takes, which reads as a glitch rather than progress.
 * Waiting a beat means a fast screen stays silent and a slow one stops looking
 * broken, which is the whole point of having it.
 *
 * The timer is cleared on every change, so a load that finishes inside the
 * delay never shows anything at all.
 *
 * @param {Object} cmp    component (`this` in setup)
 * @param {number} delay  ms to wait before calling a load "slow"
 * @returns {Function}    call in onWillDestroy to drop the pending timer
 */
export function useSlowLoad(cmp, delay = 400) {
    cmp.state.slowLoading = false;
    let timer = null;

    const clear = () => {
        if (timer) { clearTimeout(timer); timer = null; }
    };

    /** Call whenever loading starts or stops. */
    cmp.setLoading = (isLoading) => {
        cmp.state.loading = isLoading;
        clear();
        if (isLoading) {
            timer = setTimeout(() => {
                timer = null;
                // Re-checked at fire time: `loading` may have finished while
                // this was queued, and showing the splash then would put a
                // loading screen over a page that is already drawn.
                if (cmp.state.loading) cmp.state.slowLoading = true;
            }, delay);
        } else {
            cmp.state.slowLoading = false;
        }
    };

    return clear;
}
