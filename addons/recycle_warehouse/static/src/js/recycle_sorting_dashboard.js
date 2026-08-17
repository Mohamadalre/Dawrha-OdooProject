/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, onWillDestroy, useState } from "@odoo/owl";
import { user } from "@web/core/user";
import { tr as _tr } from "./recycle_i18n_shared";
import { setDashboardPage, unsetDashboardPage } from "./dashboard_page_state";
import { rpcJsonSafe, govLabel, useMessageDialog } from "./dashboard_shared";

// There is deliberately no damage THRESHOLD here any more. Any damaged
// quantity waits for the warehouse manager, however small: a floor made the
// common small write-offs invisible, and who decides one does not depend on
// its size.
// Sorting reconciliation thresholds are admin-configured (Settings > Sorting
// Reconciliation) — these are just the fallback defaults, always overridden
// by state.sortThresholds once loaded from /api/recycle/sort-thresholds.
const SORT_SHORTAGE_AUTO_LIMIT_DEFAULT = 3.0;
const SORT_SHORTAGE_REASON_LIMIT_DEFAULT = 15.0;

export class RecycleSortingDashboard extends Component {
    static template = "recycle_warehouse.RecycleSortingDashboard";
    static props = ["*"];

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.userName = (user && user.name) || "Employee";
        this._navHistory = [];

        this.state = useState({
            view: "home",
            // Sidebar entry painted green — moves only when another one is clicked.
            activeNavGo: 'goHome',
            loading: false,
            sidebarOpen: false,
            navSection: null,
            darkMode: (localStorage.getItem('dw-theme')
                       || (localStorage.getItem('recycle_wms_dark') === '1' ? 'dark' : 'light')) === 'dark',
            lang: (localStorage.getItem('recycle_wms_lang') || 'en').replace(/^ar_.*$/, 'ar'),
            // My warehouse + stats
            myWarehouse: null,
            notifUnreadCount: 0,
            notifications: [],
            notifLoading: false,
            stats: { sorted: 0, toSort: 0, hours: 0, damaged: 0 },
            // Shift
            myShift: null,
            // My shipments (processed by me)
            shipments: [],
            shipmentSearch: '',
            shipmentStateFilter: '',
            selectedShipment: null,
            selectedShipmentLines: [],
            // Sorting queue (accepted, ordered by priority)
            queue: [],
            // Warehouse stock (record rules scope it to my warehouse)
            stock: [],
            stockZones: [],
            stockZoneFilter: '',
            stockCondFilter: null,   // null = All; '' = ungraded/unsorted
            // Sorting process
            proc: null,               // shipment being sorted
            procError: null,
            procSuccess: null,        // { name }
            sortingZones: [],
            storageZones: [],
            selectedSortingZone: '',
            selectedStorageZone: '',
            // Storage-zone assignment mode: 'whole' (one zone for the shipment)
            // or 'per_material' (each material to its own zone). `storageLines`
            // holds the server line rows the per-material picker binds to.
            storageMode: 'whole',
            storageLines: [],
            products: [],
            // What this shipment still needs, as the SERVER sees it: one row
            // per declared material with its grades, its remaining quantity
            // and whether it is finished. The picker, the grade list and the
            // "add a line" button all read from this, so the screen and the
            // rule the server enforces cannot drift apart.
            sortingPlan: [],
            sortingAllComplete: false,
            // False when the shipment arrived without an itemised breakdown —
            // older shipments, or a load nobody declared in advance. There is
            // then nothing to restrict the picker against, so it falls back to
            // the full catalogue rather than showing an empty dropdown.
            hasDeclaredBreakdown: false,
            expectedLines: [],         // [{ product_id, product_name, uom_id, uom_name, qty }] — declared before arrival
            lines: [],                // { product_id, product_name, quantity, condition, is_damaged, saved }
            lineProduct: '',
            lineQty: '',
            lineCondition: '',
            // Grades of the material CURRENTLY being added, from that
            // material's own backend-authored list. Empty means the material is
            // ungraded — a real answer, and the sorter simply enters a quantity.
            lineConditions: [],
            lineConditionsLoading: false,
            // Damage is an OUTCOME, not a grade. It used to be the fourth entry
            // in a fixed grade list, which meant a material graded
            // PREMIUM/STANDARD had no way to say "this did not survive" — and
            // the storing step, which matched the literal word 'damaged', then
            // filed spoiled goods as sellable stock.
            lineIsDamaged: false,
            linesSaved: false,
            damageReason: '',
            weightShortageReason: '',
            shortageReasonCategory: '',
            reasonNeededProducts: [],  // set when the server returns status:'reason_required'
            sortThresholds: { t1: SORT_SHORTAGE_AUTO_LIMIT_DEFAULT, t2: SORT_SHORTAGE_REASON_LIMIT_DEFAULT },
            showStorageZonePicker: false,
            procSaving: false,
            // Stored-material damage report. It says ONE thing: this quantity
            // is gone. The form used to also carry a "downgrade", which made a
            // single screen answer two questions whose effects on the total are
            // opposite — one removes quantity, the other moves it — and forced
            // the sorter to choose between them before anything else made
            // sense. Grade corrections belong to sorting, not to a loss report.
            damageReportForm: {
                product_id: '', condition: '', quantity: '', reason: '', image: null,
            },
            damageReportSaving: false,
            damageReportError: null,
            damageReportSuccess: null,
            damageReports: [],
            // Grades of the material CURRENTLY selected, loaded from the
            // backend-authored list for that material. There is no global set:
            // a material may have its own grades, or none at all, and offering
            // four fixed English words showed grades that did not exist and hid
            // the ones that did.
            damageConditions: [],
            damageConditionsLoading: false,
            damageAvailable: null,
            // Profile
            userProfile: { name: '', email: '', login: '', phone: '', role: 'sorting', warehouse: '', national_id: '', street: '', city: '', country: '' },
            profileLoading: false,
            profileEditMode: false,
            profileForm: { name: '', phone: '', national_id: '', street: '', city: '' },
            profileSaving: false,
            profileSaveSuccess: null,
            profileSaveError: null,
            // Time filter
            filterPeriod: 'month',
            showChangePasswordModal: false,
            changePasswordCurrent: '',
            changePasswordNew: '',
            changePasswordConfirm: '',
            changePasswordError: null,
            changePasswordLoading: false,
            changePasswordStep: 1,
            sessions: [],
            sessionsLoading: false,
        });

        // Shared in-page message/confirm dialog — replaces window.confirm().
        useMessageDialog(this);

        onWillStart(async () => {
            // Session guard: one Odoo session per browser — if another
            // user logged in from a different tab, never render this
            // role's UI with the foreign session; bounce to the
            // dashboard that matches the CURRENT session user.
            try {
                const _w = await fetch('/api/recycle/my-profile', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'same-origin',
                    body: JSON.stringify({ jsonrpc: '2.0', method: 'call', params: {} }),
                });
                const _p = (await _w.json()).result || {};
                if (_p.role && _p.role !== 'sorting') {
                    window.location.replace('/recycle/open-dashboard');
                    return;
                }
            } catch (_e) {}
            try { await this._loadMyWarehouseInfo(); } catch (e) {}
            try { await this._loadStats(); } catch (e) {}
            try { await this._loadNotifCount(); } catch (e) {}
            try { await this._loadSortThresholds(); } catch (e) {}
        });
        onMounted(() => {
            setDashboardPage();
            this._applyTheme();
            this._startPolling();
        });
        onWillDestroy(() => {
            this._stopPolling();
            unsetDashboardPage();
        });
    }

    // ─── Live auto-refresh (every 5s, only for the currently-open,
    // read-only list/overview screen) ────────────────────────────
    _startPolling() {
        this._stopPolling();
        this._pollInterval = setInterval(() => {
            if (document.hidden) return;
            if (this.state.view === 'home') {
                this._loadStats(true);
            } else if (this.state.view === 'shipments_list' && !this._pollingShipments) {
                this._pollRefreshShipments();
            } else if (this.state.view === 'sort_queue' && !this._pollingQueue) {
                this._pollRefreshQueue();
            }
            this._loadNotifCount();
        }, 5000);
    }
    _stopPolling() {
        if (this._pollInterval) { clearInterval(this._pollInterval); this._pollInterval = null; }
    }
    async _pollRefreshShipments() {
        this._pollingShipments = true;
        try {
            this.state.shipments = await this.orm.searchRead(
                'recycle.shipment',
                [['sorter_user_id', '=', user.userId], ['state', 'in', ['sorting', 'sorted']]],
                ['id', 'name', 'driver_name', 'state', 'sorted_at', 'actual_weight',
                 'damage_pct', 'damage_request_state',
                 'sorting_zone_id', 'storage_zone_id'],
                { order: 'id desc', limit: 200 });
        } catch (e) { /* silent */ }
        this._pollingShipments = false;
    }
    async _pollRefreshQueue() {
        this._pollingQueue = true;
        try {
            this.state.queue = await this.orm.searchRead(
                'recycle.shipment', [['state', '=', 'accepted']],
                ['id', 'name', 'driver_name', 'priority', 'actual_weight',
                 'expected_weight', 'received_at'],
                { order: 'priority asc, id asc' });
        } catch (e) { /* silent */ }
        this._pollingQueue = false;
    }

    tr(key) {
        var lang = this.state.lang === 'ar' ? 'ar' : 'en';
        localStorage.setItem('recycle_wms_lang', lang);
        return _tr(key);
    }

    govLabel(code) {
        return govLabel(code, (s) => this.tr(s));
    }

    // ─── Navigation ─────────────────────────────────────────────
    get navSections() {
        // "My Warehouse" isn't in this list — it's its own card above the
        // sections (see o_ra_sb_warehouse in the template), same as the
        // Input/Reception dashboard.
        return [
            { key: 'home', icon: '\u{1F3E0}', label: 'Home', single: true, go: 'goHome', view: 'home' },
            { key: 'shift', icon: '\u{1F551}', label: 'My Shift', single: true, go: 'openShift', view: 'shift' },
            { key: 'shipments', icon: '\u{1F5C2}️', label: 'Shipments', items: [
                { label: 'View Shipments', go: 'openMyShipments' },
                { label: 'Process Sorting', go: 'openSortQueue' },
            ]},
            { key: 'stock', icon: '\u{1F4CA}', label: 'Stock', single: true, go: 'openStockList', view: 'stock_list' },
            { key: 'damage', icon: '\u{26A0}\u{FE0F}', label: 'Report Damaged Material', single: true, go: 'openDamageReportForm', view: 'damage_report_form' },
            { key: 'settings', icon: '⚙️', label: 'Settings', single: true, go: 'showSettings', view: 'settings' },
        ];
    }

    toggleSidebar(ev) { if (ev) { ev.stopPropagation(); ev.preventDefault(); } this.state.sidebarOpen = !this.state.sidebarOpen; }
    toggleNavSection(key) { this.state.navSection = this.state.navSection === key ? null : key; }
    navClick(fnName) {
        this.state.sidebarOpen = false;
        this.state.activeNavGo = fnName;
        const fn = this[fnName];
        if (typeof fn === 'function') fn.call(this);
    }
    _navigate(view) { this._navHistory.push(this.state.view); this.state.view = view; }
    goBack() { this.state.view = this._navHistory.pop() || 'home'; }
    goHome() { this._navHistory = []; this.state.view = 'home'; this._loadStats(); }
    openMyWarehouse() { this._navigate('my_warehouse'); this._loadMyWarehouseInfo(); }
    showSettings() { this._navigate('settings'); }
    setFilterPeriod(period) {
        this.state.filterPeriod = period;
        this._loadStats();
    }

    toggleDarkMode() {
        this.state.darkMode = !this.state.darkMode;
        localStorage.setItem('dw-theme', this.state.darkMode ? 'dark' : 'light');
        this._applyTheme();
    }
    _applyTheme() {
        const root = document.documentElement;
        if (this.state.darkMode) root.classList.add('o_ra_dark');
        else root.classList.remove('o_ra_dark');
    }
    setLang(lang) {
        this.state.lang = lang;
        localStorage.setItem('recycle_wms_lang', lang);
        if (lang === 'ar') document.documentElement.classList.add('o_ra_rtl');
        else document.documentElement.classList.remove('o_ra_rtl');
    }

    // ─── Home stats (period-aware: Today / Week / Month) ────────
    _periodStartStr() {
        const now = new Date();
        const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        let start;
        if (this.state.filterPeriod === 'today') {
            start = todayStart;
        } else if (this.state.filterPeriod === 'week') {
            const dow = (todayStart.getDay() + 6) % 7; // Monday-based week start
            start = new Date(todayStart); start.setDate(start.getDate() - dow);
        } else {
            start = new Date(now.getFullYear(), now.getMonth(), 1);
        }
        const pad = (n) => String(n).padStart(2, '0');
        return start.getFullYear() + '-' + pad(start.getMonth() + 1) + '-' + pad(start.getDate());
    }

    async _loadStats(silent) {
        if (!silent) this.state.loading = true;
        try {
            const periodStart = this._periodStartStr();
            const sorted = await this.orm.searchCount('recycle.shipment',
                [['sorter_user_id', '=', user.userId], ['state', '=', 'sorted'],
                 ['sorted_at', '>=', periodStart + ' 00:00:00']]);
            const toSort = await this.orm.searchCount('recycle.shipment',
                [['state', '=', 'accepted']]);
            const damaged = await this.orm.searchCount('recycle.shipment',
                [['sorter_user_id', '=', user.userId],
                 ['damage_request_state', '!=', 'none']]);
            // Pending: locked to me right now (reserved/in-progress) — a live
            // count, not scoped to the period.
            const pending = await this.orm.searchCount('recycle.shipment',
                [['sorter_user_id', '=', user.userId], ['state', '=', 'sorting']]);
            let hours = 0;
            try {
                const att = await this.orm.searchRead('recycle.attendance',
                    [['employee_user_id', '=', user.userId],
                     ['date', '>=', periodStart]],
                    ['work_hours'], { limit: 200 });
                hours = Math.round(att.reduce((a, r) => a + (r.work_hours || 0), 0) * 10) / 10;
            } catch (e) {}
            this.state.stats = { sorted: sorted, toSort: toSort, hours: hours, damaged: damaged, pending: pending };
        } catch (e) {}
        if (!silent) this.state.loading = false;
    }

    // ─── My Warehouse (dedicated view — no stats here) ──────────
    async _loadMyWarehouseInfo() {
        this.state.loading = true;
        try {
            const whs = await this.orm.searchRead(
                'recycle.warehouse', [],
                ['id', 'name', 'code', 'governorate', 'manager_user_id'],
                { limit: 1 });
            this.state.myWarehouse = whs[0] || null;
        } catch (e) { this.state.myWarehouse = null; }
        this.state.loading = false;
    }

    async _loadSortThresholds() {
        try {
            const st = await this._rpc('/api/recycle/sort-thresholds', {});
            if (st && st.threshold_1 != null) {
                this.state.sortThresholds = { t1: st.threshold_1, t2: st.threshold_2 };
            }
        } catch (e) {}
    }

    // ─── Report damaged material already in storage ──────────────
    // One statement only: this quantity is gone. The manager's approval is what
    // actually deducts it, because a deduction a buyer may already have been
    // quoted against should be a decision rather than a side effect of somebody
    // filling in a form.
    async openDamageReportForm() {
        this._navigate('damage_report_form');
        this.state.damageReportForm = {
            product_id: '', condition: '', quantity: '', reason: '', image: null,
        };
        this.state.damageReportError = null;
        this.state.damageReportSuccess = null;
        this.state.damageAvailable = null;
        this.state.damageConditions = [];
        if (!this.state.products.length) {
            try {
                this.state.products = await this.orm.searchRead('recycle.product',
                    [], ['id', 'name', 'uom_id'], { order: 'name asc' });
            } catch (e) {}
        }
    }

    /** True when the chosen material is graded at all. */
    get damageMaterialIsGraded() {
        return this.state.damageConditions.length > 0;
    }

    /**
     * Load the grades of the material just picked.
     *
     * Grades belong to the material, so the picker cannot be filled until one
     * is chosen — and an empty result is a real answer, not a loading failure:
     * that material is ungraded and the sorter enters a quantity alone.
     */
    async onDamageProductChange() {
        const f = this.state.damageReportForm;
        f.condition = '';
        this.state.damageConditions = [];
        this.state.damageAvailable = null;
        if (!f.product_id) return;

        this.state.damageConditionsLoading = true;
        try {
            const rows = await this.orm.searchRead('recycle.material.condition', [
                ['product_id', '=', parseInt(f.product_id)],
                ['active', '=', true],
            ], ['code', 'name'], { order: 'sort_order asc, id asc' });
            this.state.damageConditions = rows.map((r) => ({
                value: r.code, label: r.name,
            }));
            // One grade is not a choice — do not make the sorter make it.
            if (this.state.damageConditions.length === 1) {
                f.condition = this.state.damageConditions[0].value;
            }
        } catch (e) {
            this.state.damageConditions = [];
        }
        this.state.damageConditionsLoading = false;
        await this.onDamageStockKeyChange();
    }

    /** How much is free right now — reserved stock excluded. */
    async onDamageStockKeyChange() {
        const f = this.state.damageReportForm;
        this.state.damageAvailable = null;
        if (!f.product_id) return;
        // A graded material has no meaningful figure until a grade is chosen:
        // showing the material's total would invite the sorter to write off more
        // of one grade than exists.
        if (this.damageMaterialIsGraded && !f.condition) return;
        try {
            // No warehouse filter needed: the record rules on recycle.stock
            // already scope every read to the sorter's own warehouse.
            const domain = [['product_id', '=', parseInt(f.product_id)]];
            domain.push(['condition', '=', f.condition || false]);
            const rows = await this.orm.searchRead('recycle.stock', domain,
                ['available_qty']);
            this.state.damageAvailable = rows.reduce(
                (sum, r) => sum + (r.available_qty || 0), 0);
        } catch (e) {}
    }

    onDamageImageChange(ev) {
        const file = ev.target.files && ev.target.files[0];
        if (!file) { this.state.damageReportForm.image = null; return; }
        const reader = new FileReader();
        reader.onload = () => {
            this.state.damageReportForm.image = String(reader.result).split(',')[1] || null;
        };
        reader.readAsDataURL(file);
    }

    async submitDamageReport() {
        const f = this.state.damageReportForm;
        if (!f.product_id) { this.state.damageReportError = this.tr('Please select a material.'); return; }
        // Required only when the material HAS grades. Demanding one for an
        // ungraded material would ask for a value that does not exist.
        if (this.damageMaterialIsGraded && !f.condition) {
            this.state.damageReportError = this.tr('Please select the grade that was damaged.');
            return;
        }
        const qty = parseFloat(f.quantity);
        if (!qty || qty <= 0) { this.state.damageReportError = this.tr('Enter a valid quantity.'); return; }
        if (!f.reason || !f.reason.trim()) { this.state.damageReportError = this.tr('Please describe the reason.'); return; }
        // Checked here too so the sorter is told before submitting, not after —
        // the server enforces it again, since stock moves while the form is open.
        if (this.state.damageAvailable !== null && qty > this.state.damageAvailable) {
            this.state.damageReportError = this.tr('Only what is free in this grade can be reported — the rest is promised to open orders.');
            return;
        }
        this.state.damageReportSaving = true;
        this.state.damageReportError = null;
        try {
            const vals = {
                product_id: parseInt(f.product_id),
                // Ungraded material sends no grade at all — false, not an empty
                // string, so the server records "no grade" rather than "a grade
                // whose name is blank".
                condition: f.condition || false,
                quantity: qty,
                reason: f.reason.trim(),
            };
            if (f.image) vals.image = f.image;
            await this.orm.create('recycle.stock.damage.report', [vals]);
            this.state.damageReportSuccess =
                this.tr('Damage report sent to the warehouse manager for approval.');
            this.state.damageReportForm = {
                product_id: '', condition: '', quantity: '', reason: '', image: null,
            };
            this.state.damageConditions = [];
            this.state.damageAvailable = null;
        } catch (e) {
            this.state.damageReportError = (e && e.data && e.data.message) || this.tr('Action failed.');
        }
        this.state.damageReportSaving = false;
    }

    // ─── My Shift ───────────────────────────────────────────────
    async openShift() {
        this._navigate('shift');
        this.state.loading = true;
        this.state.myShift = null;
        try {
            const res = await this._rpc('/api/employee/my-shift', {});
            if (res && res.shift) {
                this.state.myShift = res.shift;
            } else {
                this.state.myShift = null;
            }
        } catch (e) { this.state.myShift = null; }
        this.state.loading = false;
    }

    // ─── My shipments (shipments I've locked/sorted: In Sorting + Stored) ─
    async openMyShipments() {
        this._navigate('shipments_list');
        this.state.shipmentStateFilter = 'sorting';
        this.state.loading = true;
        try {
            // Only shipments reserved to ME: currently in sorting (locked to
            // me) or already fully sorted/stored by me. Accepted (not yet
            // opened) shipments belong to the separate "Process Sorting"
            // queue, not this personal list.
            this.state.shipments = await this.orm.searchRead(
                'recycle.shipment',
                [['sorter_user_id', '=', user.userId], ['state', 'in', ['sorting', 'sorted']]],
                ['id', 'name', 'driver_name', 'state', 'sorted_at', 'actual_weight',
                 'damage_pct', 'damage_request_state',
                 'sorting_zone_id', 'storage_zone_id'],
                { order: 'id desc', limit: 200 });
        } catch (e) { this.state.shipments = []; }
        this.state.loading = false;
    }

    get filteredShipments() {
        const q = (this.state.shipmentSearch || '').toLowerCase().trim();
        const st = this.state.shipmentStateFilter;
        return this.state.shipments.filter(s => {
            if (q && !((s.name || '').toLowerCase().includes(q)
                    || (s.driver_name || '').toLowerCase().includes(q))) return false;
            if (st === 'sorting' && s.state !== 'sorting') return false;
            if (st === 'sorted' && s.state !== 'sorted') return false;
            return true;
        });
    }

    async openShipmentDetail(s) {
        this.state.selectedShipment = s;
        this._navigate('shipment_detail');
        this.state.loading = true;
        try {
            this.state.selectedShipmentLines = await this.orm.searchRead(
                'recycle.shipment.line', [['shipment_id', '=', s.id]],
                ['product_id', 'quantity', 'condition', 'condition_label']);
        } catch (e) { this.state.selectedShipmentLines = []; }
        this.state.loading = false;
    }

    // ─── Sorting queue (priority ordered) ───────────────────────
    async openSortQueue() {
        this._navigate('sort_queue');
        this.state.loading = true;
        try {
            // Record rules hide colleagues' reserved shipments automatically.
            this.state.queue = await this.orm.searchRead(
                'recycle.shipment', [['state', '=', 'accepted']],
                ['id', 'name', 'driver_name', 'priority', 'actual_weight',
                 'expected_weight', 'received_at'],
                { order: 'priority asc, id asc' });
        } catch (e) { this.state.queue = []; }
        this.state.loading = false;
    }

    // ─── Warehouse stock (mine only, via record rules) ──────────
    async openStockList() {
        this._navigate('stock_list');
        this.state.loading = true;
        this.state.stockZoneFilter = '';
        this.state.stockCondFilter = '';
        try {
            this.state.stock = await this.orm.searchRead(
                'recycle.stock', [],
                ['id', 'product_id', 'quantity', 'zone_id', 'condition',
                 'condition_label', 'reserved_qty', 'available_qty'],
                { order: 'product_id asc' });
            this.state.stockZones = await this.orm.searchRead(
                'recycle.zone', [['zone_type', '=', 'storage']],
                ['id', 'name'], { order: 'name asc' });
        } catch (e) { this.state.stock = []; this.state.stockZones = []; }
        this.state.loading = false;
    }

    get filteredStock() {
        let list = this.state.stock;
        const z = this.state.stockZoneFilter;
        if (z) list = list.filter(st => st.zone_id && st.zone_id[0] === Number(z));
        if (this.state.stockCondFilter !== null) {
            // null means "All"; '' is a REAL filter value meaning "no grade" —
            // a state stock can genuinely be in (ungraded material, or arrivals
            // not yet sorted), so it needs a button of its own rather than
            // being folded into "All". Using '' for both is exactly how the
            // ungraded rows would become unfilterable.
            list = list.filter(st => (st.condition || '') === this.state.stockCondFilter);
        }
        return list;
    }

    setStockCondFilter(cond) {
        // Passed through as-is: '' is the "no grade" filter, null is "All".
        this.state.stockCondFilter = cond === undefined ? null : cond;
    }

    /**
     * Grade filter buttons, derived from the stock actually on hand.
     *
     * There is no global grade list to build these from any more — grades belong
     * to each material and the admin names them — so the buttons are whatever
     * grades this warehouse is currently holding. That is also more useful than
     * a fixed set was: it can never offer a filter that matches nothing, and it
     * can never hide a grade that exists.
     */
    get stockGradeOptions() {
        const seen = new Map();
        for (const st of this.state.stock) {
            const key = st.condition || '';
            if (!seen.has(key)) {
                seen.set(key, {
                    value: key,
                    label: st.condition_label || this.tr('No grade'),
                });
            }
        }
        return [...seen.values()];
    }

    /**
     * Colour a grade badge without knowing the grade's name.
     *
     * Grades are the admin's to name per material, so no fixed map of English
     * words can colour them — and the old one silently fell through to "muted"
     * for every material graded any other way, which read as "no grade". The
     * colour now comes from the grade's POSITION within its own material: best
     * first, worst last, which is the only ranking that exists for all of them.
     */
    conditionBadgeClass(condition, gradeList) {
        if (!condition) return 'o_ra_badge_muted';
        const list = gradeList || this.state.lineConditions;
        const at = list.findIndex((c) => c.value === condition);
        if (at < 0) return 'o_ra_badge_info';
        if (list.length === 1) return 'o_ra_badge_success';
        const share = at / (list.length - 1);
        if (share <= 0.25) return 'o_ra_badge_success';
        if (share <= 0.5) return 'o_ra_badge_info';
        if (share <= 0.75) return 'o_ra_badge_warning';
        return 'o_ra_badge_danger';
    }

    get topPriority() {
        return this.state.queue.length ? this.state.queue[0].priority : null;
    }

    priorityLabel(p) {
        if (p <= 3) return this.tr('High');
        if (p <= 7) return this.tr('Medium');
        return this.tr('Low');
    }

    priorityClass(p) {
        if (p <= 3) return 'o_ra_badge_danger';
        if (p <= 7) return 'o_ra_badge_warning';
        return 'o_ra_badge_info';
    }

    // Colour a per-material shortfall the same way Rule 2 reads it: green
    // under threshold_1, amber up to threshold_2, red beyond it.
    shortfallClass(shortfallPct) {
        if (shortfallPct == null) return 'o_ra_badge_muted';
        const t = this.state.sortThresholds || {};
        const t1 = t.t1 != null ? t.t1 : SORT_SHORTAGE_AUTO_LIMIT_DEFAULT;
        const t2 = t.t2 != null ? t.t2 : SORT_SHORTAGE_REASON_LIMIT_DEFAULT;
        if (shortfallPct > t2) return 'o_ra_badge_danger';
        if (shortfallPct > t1) return 'o_ra_badge_warning';
        return 'o_ra_badge_success';
    }

    async startSorting(s) {
        this.state.procError = null;
        try {
            await this.orm.call('recycle.shipment', 'action_start_sorting', [[s.id]]);
            await this._openProc(s.id);
        } catch (e) {
            const msg = (e && e.data && e.data.message) || this.tr('Action failed.');
            this.notification.add(msg, { type: 'danger' });
        }
    }

    async _openProc(shipmentId) {
        this._navigate('sort_process');
        this.state.loading = true;
        try {
            const found = await this.orm.searchRead('recycle.shipment',
                [['id', '=', shipmentId]],
                ['id', 'name', 'driver_name', 'priority', 'actual_weight',
                 'state', 'sorting_zone_id', 'storage_zone_id', 'damage_pct',
                 'damage_request_state', 'damage_reject_reason',
                 'weight_shortfall_pct', 'weight_shortage_reason',
                 'shortage_reason_category', 'manager_approved_sorting',
                 'sort_escalation_state', 'warehouse_id'],
                { limit: 1 });
            this.state.proc = found[0] || null;
            this.state.selectedSortingZone = (found[0] && found[0].sorting_zone_id && found[0].sorting_zone_id[0]) || '';
            this.state.selectedStorageZone = (found[0] && found[0].storage_zone_id && found[0].storage_zone_id[0]) || '';
            this.state.damageReason = '';
            this.state.weightShortageReason = (found[0] && found[0].weight_shortage_reason) || '';
            this.state.shortageReasonCategory = (found[0] && found[0].shortage_reason_category) || '';
            this.state.reasonNeededProducts = [];
            this.state.showStorageZonePicker = false;
            this.state.procError = null;
            this.state.procSuccess = null;
            const lines = await this.orm.searchRead('recycle.shipment.line',
                [['shipment_id', '=', shipmentId]],
                ['product_id', 'quantity', 'condition', 'condition_label',
                 'is_damaged', 'uom_id']);
            this.state.lines = lines.map(l => ({
                product_id: l.product_id[0], product_name: l.product_id[1],
                quantity: l.quantity, condition: l.condition,
                condition_label: l.condition_label || '',
                is_damaged: !!l.is_damaged,
                uom_name: l.uom_id ? l.uom_id[1] : '', saved: true,
            }));
            this.state.linesSaved = !!lines.length;
            // Materials declared before arrival — the reference the sorter
            // must fully account for (see reconciliation getter below).
            const expected = await this.orm.searchRead('recycle.shipment.expected.line',
                [['shipment_id', '=', shipmentId]],
                ['product_id', 'uom_id', 'expected_qty']);
            this.state.expectedLines = expected.map(e => ({
                product_id: e.product_id[0], product_name: e.product_id[1],
                uom_id: e.uom_id ? e.uom_id[0] : false,
                uom_name: e.uom_id ? e.uom_id[1] : '',
                qty: e.expected_qty,
            }));
            const whId = found[0] && found[0].warehouse_id && found[0].warehouse_id[0];
            if (!this.state.sortingZones.length) {
                this.state.sortingZones = await this.orm.searchRead('recycle.zone',
                    [['zone_type', '=', 'sorting'], ['warehouse_id', '=', whId]],
                    ['id', 'name', 'warehouse_id']);
            }
            if (!this.state.storageZones.length) {
                this.state.storageZones = await this.orm.searchRead('recycle.zone',
                    [['zone_type', '=', 'storage'], ['warehouse_id', '=', whId]],
                    ['id', 'name']);
            }
            // The materials of THIS shipment, and what is left to enter for
            // each — decided by the server, not assembled here.
            //
            // The picker used to load EVERY material in the catalogue, so a
            // sorter could log something the lorry never carried. The shipment
            // declared what arrived; anything else is a typing mistake at best.
            await this._loadSortingPlan(shipmentId);
        } catch (e) { this.state.proc = null; }
        this.state.loading = false;
    }

    unitLabel(uomName) {
        return uomName || this.tr('units');
    }

    get selectedProductUnit() {
        const pid = parseInt(this.state.lineProduct);
        const p = this.state.products.find(x => x.id === pid);
        return p && p.uom_id ? p.uom_id[1] : '';
    }

    async setSortingZone() {
        if (!this.state.selectedSortingZone) {
            this.state.procError = this.tr('Please select a sorting zone.'); return;
        }
        this.state.procError = null;
        try {
            await this.orm.call('recycle.shipment', 'action_set_sorting_zone',
                [[this.state.proc.id], parseInt(this.state.selectedSortingZone)]);
            const z = this.state.sortingZones.find(z => z.id === parseInt(this.state.selectedSortingZone));
            this.state.proc.sorting_zone_id = [z.id, z.name];
        } catch (e) {
            this.state.procError = (e && e.data && e.data.message) || this.tr('Action failed.');
        }
    }

    /** True when the material being added has grades of its own. */
    /**
     * Is the chosen material graded at all?
     *
     * Read from the PLAN, not from the remaining-grades list. That list
     * shrinks as grades are entered, so a material on its last grade would
     * otherwise start looking ungraded — and the form would stop asking for
     * the very grade it still needs.
     */
    get lineMaterialIsGraded() {
        const row = this.selectedPlanRow;
        if (row) return row.is_graded;
        return this.state.lineConditions.length > 0;
    }

    /**
     * Load the grades of the material the sorter just picked.
     *
     * Grades cannot be offered before a material is chosen, because they belong
     * to it. An empty list is the answer for an ungraded material, not a
     * failure — the sorter then records a quantity and nothing else.
     */
    /**
     * What the sorter still has to account for, as the SERVER sees it.
     *
     * Re-read after every change rather than adjusted locally: the plan is
     * what decides which materials the picker offers, which grades are left,
     * how much may still be entered and whether "add a line" is shown at all.
     * Keeping one source for that means the screen cannot drift from the rule
     * the server will enforce when sorting is finished.
     */
    async _loadSortingPlan(shipmentId) {
        try {
            const res = await this.orm.call(
                'recycle.shipment', 'get_sorting_plan', [[shipmentId]]);
            this.state.sortingPlan = (res && res.plan) || [];
            this.state.sortingAllComplete = !!(res && res.all_complete);
            this.state.hasDeclaredBreakdown = !!(res && res.has_declared_breakdown);
        } catch (e) {
            this.state.sortingPlan = [];
            this.state.sortingAllComplete = false;
            this.state.hasDeclaredBreakdown = false;
        }

        // A shipment that declared no breakdown has nothing to restrict the
        // picker against. The full catalogue is the only honest fallback —
        // and it is loaded ONLY in that case, so the normal path stays narrow.
        if (!this.state.hasDeclaredBreakdown && !this.state.products.length) {
            try {
                this.state.products = await this.orm.searchRead(
                    'recycle.product', [], ['id', 'name', 'uom_id'],
                    { order: 'name asc' });
            } catch (e) {
                this.state.products = [];
            }
        }
    }

    /**
     * The materials the picker offers: this shipment's, minus the finished.
     *
     * An UNGRADED material disappears the moment a quantity is logged — there
     * was one number to give and it has been given. A GRADED one stays until
     * every grade has a line, because a material is only accounted for when
     * each of its qualities has been looked for.
     */
    get sortableProducts() {
        if (this.state.hasDeclaredBreakdown) {
            return (this.state.sortingPlan || []).filter((p) => !p.complete);
        }
        // No declared breakdown: nothing to restrict against, so the whole
        // catalogue is offered — shaped like a plan row so the template reads
        // one thing either way.
        return (this.state.products || []).map((p) => ({
            product_id: p.id,
            product_name: p.name,
            uom_id: p.uom_id ? p.uom_id[0] : false,
            uom_name: p.uom_id ? p.uom_id[1] : '',
            expected: 0,
            entered: 0,
            remaining_qty: null,   // no declared quantity to count down from
            is_graded: false,      // resolved on selection, see below
            grades: [],
            complete: false,
        }));
    }

    /** The plan row for the material being entered right now. */
    get selectedPlanRow() {
        const pid = parseInt(this.state.lineProduct);
        return (this.state.sortingPlan || []).find((p) => p.product_id === pid)
            || null;
    }

    /** The unit of the chosen material — shown, never chosen. */
    get selectedProductUnitName() {
        const row = this.selectedPlanRow;
        return row ? row.uom_name : '';
    }

    /**
     * How much may still be entered for the chosen material.
     *
     * Zero once the declared quantity is reached, which is what stops the
     * total from ever exceeding what the shipment said arrived.
     */
    get selectedRemainingQty() {
        const row = this.selectedPlanRow;
        return row ? row.remaining_qty : null;
    }

    async onSortLineProductChange() {
        this.state.lineCondition = '';
        this.state.lineConditions = [];
        const pid = parseInt(this.state.lineProduct);
        if (!pid) return;

        // The grades of THIS material, minus the ones already entered — the
        // sorter is moved on to the next quality rather than being allowed to
        // record the same one twice.
        const row = this.selectedPlanRow;
        if (row && row.grades && row.grades.length) {
            this.state.lineConditions = row.grades
                .filter((g) => !g.done)
                .map((g) => ({ value: g.code, label: g.name }));
        } else if (!this.state.hasDeclaredBreakdown) {
            // No breakdown, so no plan to read grades from — they are fetched
            // for the material just chosen.
            this.state.lineConditionsLoading = true;
            try {
                const rows = await this.orm.searchRead(
                    'recycle.material.condition',
                    [['product_id', '=', pid], ['active', '=', true]],
                    ['code', 'name'], { order: 'sort_order asc, id asc' });
                this.state.lineConditions = rows.map(
                    (r) => ({ value: r.code, label: r.name }));
            } catch (e) {
                this.state.lineConditions = [];
            }
        } else {
            this.state.lineConditions = [];
        }
        // One remaining grade is not a choice — do not make the sorter make it.
        if (this.state.lineConditions.length === 1) {
            this.state.lineCondition = this.state.lineConditions[0].value;
        }
        this.state.lineConditionsLoading = false;
    }

    addLine() {
        const pid = parseInt(this.state.lineProduct);
        const qty = parseFloat(this.state.lineQty);
        if (!pid) { this.state.procError = this.tr('Please select a product.'); return; }
        // ZERO is allowed, and deliberately so.
        //
        // A graded material may arrive without one of its grades. Refusing a
        // zero would leave the sorter two bad options: invent a quantity, or
        // leave the grade unrecorded so nobody can tell it was looked for. A
        // zero says "checked, none arrived" — and it keeps the sum of the
        // grades comparable with what the shipment declared.
        if (isNaN(qty) || qty < 0) {
            this.state.procError = this.tr('Enter a valid quantity.');
            return;
        }
        // A grade is required exactly when the material has grades, and never
        // for a damaged line: damaged goods are not being sold at any quality,
        // so there is nothing for a grade to say about them.
        if (!this.state.lineIsDamaged && this.lineMaterialIsGraded
                && !this.state.lineCondition) {
            this.state.procError = this.tr('Please select the grade for this material.');
            return;
        }

        // Never more than the shipment declared for this material. Refused
        // here, while the material is still in front of the sorter, rather
        // than at the end when every line has already been typed — the server
        // enforces the same rule, this only makes it arrive in time to act on.
        const row = this.selectedPlanRow;
        // `remaining_qty` is null when the shipment declared no breakdown:
        // there is no declared quantity to count down from, so there is
        // nothing here to exceed.
        if (row && row.remaining_qty !== null && row.remaining_qty !== undefined) {
            const alreadyPending = this.state.lines
                .filter((l) => l.product_id === pid && !l.saved)
                .reduce((sum, l) => sum + Number(l.quantity || 0), 0);
            if (qty + alreadyPending - row.remaining_qty > 0.0005) {
                this.state.procError = this.tr('Only %s left to enter for this material.')
                    .replace('%s', `${round3(row.remaining_qty - alreadyPending)} ${row.uom_name}`);
                return;
            }
        }

        const p = row || this.state.products.find(x => x.id === pid);
        this.state.lines.push({
            product_id: pid,
            product_name: (row && row.product_name) || (p && p.name) || ('#' + pid),
            quantity: qty,
            uom_name: row ? row.uom_name : '',
            condition: this.state.lineIsDamaged ? false : (this.state.lineCondition || false),
            condition_label: this.state.lineIsDamaged ? '' : this._lineConditionLabel(),
            is_damaged: this.state.lineIsDamaged,
            saved: false,
        });
        this.state.lineProduct = '';
        this.state.lineQty = '';
        this.state.lineCondition = '';
        this.state.lineConditions = [];
        this.state.lineIsDamaged = false;
        this.state.procError = null;
    }

    _lineConditionLabel() {
        const found = this.state.lineConditions.find(
            (c) => c.value === this.state.lineCondition);
        return found ? found.label : '';
    }

    removeLine(idx) {
        if (this.state.lines[idx] && !this.state.lines[idx].saved) {
            this.state.lines.splice(idx, 1);
        }
    }

    /** Is there anything left to take back? */
    get canUndoLine() {
        return this.state.lines.some((l) => !l.saved);
    }

    /**
     * Take back the last line that has not been saved yet.
     *
     * A mistyped quantity is caught a second after it is typed, and until now
     * the only way to correct one was to find the row and hit its ✖ — on a
     * phone, on a list that has scrolled. One button next to the field the
     * sorter is already looking at is the difference between fixing a typo and
     * living with it.
     *
     * Saved lines are left alone: those are on the server, and taking them
     * back is a different act with a different consequence.
     */
    undoLastLine() {
        for (let i = this.state.lines.length - 1; i >= 0; i--) {
            if (!this.state.lines[i].saved) {
                this.state.lines.splice(i, 1);
                this.state.procError = null;
                return;
            }
        }
    }

    /**
     * What is about to be stored, totalled PER UNIT.
     *
     * Kilograms and pieces do not add up, so a single "total entered" figure
     * was a number with no meaning — 40 of a shipment that carried 30 kg and
     * 10 items says nothing about either. The sorter confirms against this
     * instead: one line per unit, with the damaged part called out separately
     * because it is not going to storage at all.
     */
    get confirmPreview() {
        const byUom = {};
        for (const l of this.state.lines) {
            const key = l.uom_name || '';
            const row = byUom[key] || (byUom[key] = {
                uom_name: key, total: 0, storable: 0, damaged: 0, lines: 0,
            });
            const qty = Number(l.quantity || 0);
            row.total += qty;
            row.lines += 1;
            if (l.is_damaged) row.damaged += qty;
            else row.storable += qty;
        }
        return Object.values(byUom)
            .map((r) => ({
                uom_name: r.uom_name,
                lines: r.lines,
                total: round3(r.total),
                storable: round3(r.storable),
                damaged: round3(r.damaged),
            }))
            .sort((a, b) => a.uom_name.localeCompare(b.uom_name));
    }

    /**
     * The LOST quantity for a material: declared minus entered.
     *
     * Shown against the line that COMPLETES the material, not against every
     * line. An ungraded material completes on its only line; a graded one on
     * its last grade — before that the figure would be an artefact of how far
     * the sorter has got, and would read as loss that has not happened.
     *
     * Not the same as "damaged". Damaged goods arrived and are on the floor
     * waiting to be written off; lost goods never came off the lorry.
     */
    lineLoss(index) {
        const line = this.state.lines[index];
        if (!line) return null;

        const planned = (this.state.sortingPlan || [])
            .find((p) => p.product_id === line.product_id);
        if (!planned || !planned.expected) return null;

        // Only on the material's LAST line, so the number appears once and
        // when it means something.
        const lastIndex = this.state.lines
            .map((l, i) => (l.product_id === line.product_id ? i : -1))
            .filter((i) => i >= 0)
            .pop();
        if (lastIndex !== index) return null;

        // A graded material is only finished when every grade has a line.
        if (planned.is_graded && !planned.complete) return null;

        const entered = this.state.lines
            .filter((l) => l.product_id === line.product_id)
            .reduce((sum, l) => sum + Number(l.quantity || 0), 0);

        const lost = Math.max(planned.expected - entered, 0);
        return {
            qty: round3(lost),
            pct: round3(lost / planned.expected * 100),
            uom_name: planned.uom_name,
        };
    }

    get linesTotalQty() {
        return this.state.lines.reduce((a, l) => a + l.quantity, 0);
    }
    /**
     * How much of what was entered is damaged.
     *
     * Read from `is_damaged`, which is the flag the add-line form actually
     * sets. It used to look for a grade called `'damaged'` — a grade that no
     * longer exists, because damaged goods are not sold at any quality and the
     * form stopped asking for one. The effect was a damage figure permanently
     * stuck at 0%, on the very screen the sorter uses to judge it.
     */
    get damagedQtyLocal() {
        return this.state.lines
            .filter((l) => l.is_damaged)
            .reduce((a, l) => a + Number(l.quantity || 0), 0);
    }
    get damagePctLocal() {
        const t = this.linesTotalQty;
        if (!t) return 0;
        return Math.round(this.damagedQtyLocal / t * 1000) / 10;
    }
    /** Is there any damage at all? */
    get hasDamageLocal() {
        return this.damagedQtyLocal > 0;
    }
    /**
     * Storing is blocked by ANY damage, however little.
     *
     * There is no floor under which the sorter may write goods off alone. The
     * threshold that used to sit here made the small cases — the common ones —
     * invisible: quantity disappeared on the sorter's word, and the manager
     * only ever saw the large losses. Who decides a write-off does not depend
     * on its size.
     */
    get damageBlocked() {
        return this.hasDamageLocal
            && this.state.proc
            && this.state.proc.damage_request_state !== 'approved';
    }

    // ─── Reconciliation preview: mirrors recycle.shipment
    // ._sort_reconciliation() exactly (3 rules, uom-generic) so the sorter
    // sees what the server will decide before clicking Finish. Kept under
    // the name "weightCheck" so every existing template binding keeps
    // working. ────────────────────────────────────────────────────────
    get weightCheck() {
        const t = this.state.sortThresholds || {};
        const threshold1 = t.t1 != null ? t.t1 : SORT_SHORTAGE_AUTO_LIMIT_DEFAULT;
        const threshold2 = t.t2 != null ? t.t2 : SORT_SHORTAGE_REASON_LIMIT_DEFAULT;

        const expectedByProduct = {};
        for (const e of this.state.expectedLines) {
            expectedByProduct[e.product_id] = (expectedByProduct[e.product_id] || 0) + (e.qty || 0);
        }
        const enteredByProduct = {};
        for (const l of this.state.lines) {
            enteredByProduct[l.product_id] = (enteredByProduct[l.product_id] || 0) + (l.quantity || 0);
        }

        if (!this.state.expectedLines.length) {
            // Legacy fallback (no declared material breakdown available):
            // compare the flat total against the actual weight, same as
            // the pre-UoM behaviour.
            const total = this.linesTotalQty;
            const actual = (this.state.proc && this.state.proc.actual_weight) || 0;
            if (!actual || !total) return { status: 'ok', pct: 0, missing: [], extra: [], products: [], uomGroups: [], blocked: [], reasonNeeded: [] };
            if (total > actual) return { status: 'over', pct: (total - actual) / actual * 100, missing: [], extra: [], products: [], uomGroups: [], blocked: [], reasonNeeded: [] };
            const shortagePct = (actual - total) / actual * 100;
            let status = 'ok';
            if (shortagePct > threshold2) status = 'blocked';
            else if (shortagePct > threshold1) status = 'reason_needed';
            return { status, pct: shortagePct, missing: [], extra: [], products: [], uomGroups: [], blocked: [], reasonNeeded: [] };
        }

        const expectedIds = new Set(Object.keys(expectedByProduct).map(Number));
        const enteredIds = new Set(Object.keys(enteredByProduct).map(Number));
        const missingIds = [...expectedIds].filter(id => !enteredIds.has(id));
        const extraIds = [...enteredIds].filter(id => !expectedIds.has(id));

        const nameById = {};
        const uomById = {};       // pid -> { id, name, allows_tolerance }
        this.state.expectedLines.forEach(e => {
            nameById[e.product_id] = e.product_name;
            uomById[e.product_id] = { id: e.uom_id, name: e.uom_name };
        });
        this.state.lines.forEach(l => { if (!nameById[l.product_id]) nameById[l.product_id] = l.product_name; });
        this.state.products.forEach(p => {
            if (!uomById[p.id] && p.uom_id) uomById[p.id] = { id: p.uom_id[0], name: p.uom_id[1] };
        });

        const uomGroups = {};   // uom_id -> { name, expected, entered }
        const products = [];
        const blocked = [];
        const reasonNeeded = [];
        let worstPct = 0;

        for (const pid of new Set([...expectedIds, ...enteredIds])) {
            const uom = uomById[pid] || { id: 0, name: '-' };
            const allowsTolerance = uom.allows_tolerance !== false; // default true when unknown (server is authoritative)
            const exp = expectedByProduct[pid] || 0;
            const ent = enteredByProduct[pid] || 0;
            const g = uomGroups[uom.id] || (uomGroups[uom.id] = { name: uom.name, expected: 0, entered: 0 });
            g.expected += exp;
            g.entered += ent;

            const entry = {
                product_id: pid, product_name: nameById[pid] || ('#' + pid),
                uom_name: uom.name, expected: exp, entered: ent,
                pct: exp ? Math.round((exp - ent) / exp * 1000) / 10 : null,
                tier: 'auto',
            };
            if (exp > 0 && ent < exp) {
                const shortfallPct = (exp - ent) / exp * 100;
                worstPct = Math.max(worstPct, shortfallPct);
                if (shortfallPct > threshold2) { entry.tier = 'blocked'; blocked.push(entry); }
                else if (shortfallPct > threshold1) { entry.tier = 'reason_needed'; reasonNeeded.push(entry); }
            }
            products.push(entry);
        }

        const uomGroupList = [];
        let overLimit = false;
        for (const [uomId, g] of Object.entries(uomGroups)) {
            uomGroupList.push({ uom_name: g.name, expected: g.expected, entered: g.entered });
            if (g.entered > g.expected) overLimit = true;
        }

        let status = 'ok';
        if (missingIds.length || extraIds.length) status = 'mismatch';
        else if (overLimit) status = 'over';               // Rule 1 — always, no exception
        else if (blocked.length) status = 'blocked';        // Rule 2 (>threshold_2) or Rule 3 (exact mismatch)
        else if (reasonNeeded.length) status = 'reason_needed'; // Rule 2, reason band

        return {
            status, pct: Math.round(worstPct * 10) / 10,
            missing: missingIds.map(id => ({ id, name: nameById[id] || ('#' + id) })),
            extra: extraIds.map(id => ({ id, name: nameById[id] || ('#' + id) })),
            products, uomGroups: uomGroupList, blocked, reasonNeeded,
        };
    }

    async _saveLines() {
        const unsaved = this.state.lines.filter(l => !l.saved);
        if (unsaved.length) {
            await this.orm.create('recycle.shipment.line', unsaved.map(l => ({
                shipment_id: this.state.proc.id,
                product_id: l.product_id,
                quantity: l.quantity,
                // `false`, never '': the server must record "no grade" rather
                // than "a grade whose name is empty".
                condition: l.is_damaged ? false : (l.condition || false),
                is_damaged: !!l.is_damaged,
            })));
            unsaved.forEach(l => { l.saved = true; });
        }
        this.state.linesSaved = true;
        // Re-read what is still outstanding. The plan is what the picker, the
        // grade list and the "add a line" button are drawn from, so leaving it
        // stale would offer a material that has just been finished.
        await this._loadSortingPlan(this.state.proc.id);
    }

    async requestDamageApproval() {
        if (!this.state.lines.length) { this.state.procError = this.tr('Add at least one product line first.'); return; }
        this.state.procSaving = true;
        this.state.procError = null;
        try {
            await this._saveLines();
            await this.orm.call('recycle.shipment', 'action_request_damage_approval',
                [[this.state.proc.id], this.state.damageReason]);
            this.state.proc.damage_request_state = 'pending';
            this.notification.add(this.tr('Approval request sent to the warehouse manager.'), { type: 'success' });
        } catch (e) {
            this.state.procError = (e && e.data && e.data.message) || this.tr('Action failed.');
        }
        this.state.procSaving = false;
    }

    // Materials screen "End Storage" button: validates client-side, then
    // either reveals the storage-zone step (ok / reason satisfied) or —
    // for the 'blocked' tier — is not shown at all (transferBlockedToManager
    // is used instead, see the XML: the two buttons are mutually exclusive
    // based on weightCheck.status).
    proceedFromMaterials() {
        if (!this.state.lines.length) { this.state.procError = this.tr('Add at least one product line first.'); return; }
        const wc = this.weightCheck;
        this.state.procError = null;
        if (wc.status === 'mismatch') {
            const parts = [];
            if (wc.missing.length) parts.push(this.tr('Missing') + ': ' + wc.missing.map(m => m.name).join(', '));
            if (wc.extra.length) parts.push(this.tr('Not in this shipment') + ': ' + wc.extra.map(m => m.name).join(', '));
            this.state.procError = parts.join(' — ');
            return;
        }
        if (wc.status === 'over') {
            this.state.procError = this.tr('Enter a lower weight and matching quantity.');
            return;
        }
        if (wc.status === 'reason_needed') {
            this.state.reasonNeededProducts = wc.reasonNeeded;
            if (!this.state.shortageReasonCategory
                || (this.state.shortageReasonCategory === 'other' && !this.state.weightShortageReason.trim())) {
                this.state.procError = this.tr('Some materials are short of what was declared. Please choose a reason before finishing.');
                return;
            }
        }
        // Damage NEVER blocks storage: the sorter just describes it, the request
        // is filed to the manager at finish, and the sound materials are stored
        // now. All that is required here is the description itself.
        if (this.hasDamageLocal && !this.state.damageReason.trim()) {
            this.state.procError = this.tr('Describe the damage before moving to storage — it will be sent to the manager, and you can store the sound materials now.');
            return;
        }
        // status is 'ok' or 'reason_needed' (satisfied) — move on to
        // picking the storage zone, the final step before storing.
        this.state.showStorageZonePicker = true;
    }

    // 'blocked' tier (shortage strictly over threshold_2, or an exact-match
    // unit that didn't match): sends the shipment straight to the manager —
    // no storage zone is needed since it isn't being stored right now.
    async transferBlockedToManager() {
        this.state.procSaving = true;
        this.state.procError = null;
        try {
            await this._saveLines();
            const results = await this.orm.call('recycle.shipment', 'action_finish_sorting',
                [[this.state.proc.id], this.state.weightShortageReason || null,
                 this.state.shortageReasonCategory || null]);
            const result = (results && results[0]) || {};
            if (result.status === 'blocked') {
                this.notification.add(
                    this.tr('This shipment needs the warehouse manager\'s approval and was sent for review.'),
                    { type: 'warning' });
                this.state.proc = null;
                this.openSortQueue();
            } else {
                this.state.procError = this.tr('Action failed.');
            }
        } catch (e) {
            this.state.procError = (e && e.data && e.data.message) || this.tr('Action failed.');
        }
        this.state.procSaving = false;
    }

    // Final step: storage zone chosen — set it, then finish for real.
    async confirmStorageZoneAndFinish() {
        if (!this.state.selectedStorageZone) { this.state.procError = this.tr('Please select a storage zone.'); return; }
        this.state.procSaving = true;
        this.state.procError = null;
        try {
            await this.orm.call('recycle.shipment', 'action_set_storage_zone',
                [[this.state.proc.id], parseInt(this.state.selectedStorageZone)]);
            await this._saveLines();
            const results = await this.orm.call('recycle.shipment', 'action_finish_sorting',
                [[this.state.proc.id], this.state.weightShortageReason || null,
                 this.state.shortageReasonCategory || null,
                 this.state.damageReason || null]);
            const result = (results && results[0]) || { status: 'stored' };
            if (result.status === 'stored') {
                this.state.procSuccess = { name: this.state.proc.name };
                this.state.proc = null;
                this.state.showStorageZonePicker = false;
                this._loadStats();
            } else {
                // Reconciliation was re-evaluated server-side and no longer
                // passes (e.g. edited on another tab) — go back to materials.
                this.state.showStorageZonePicker = false;
                this.state.procError = this.tr('Action failed.');
            }
        } catch (e) {
            this.state.procError = (e && e.data && e.data.message) || this.tr('Action failed.');
        }
        this.state.procSaving = false;
    }

    // ── Per-material storage: split the shipment across zones ──────────────
    //
    // Saves the lines first so each has a server id, then loads the storable
    // lines (not damaged, non-zero) for the picker to bind a zone to each. The
    // "whole shipment, one zone" path above is unchanged — this is the other
    // choice the operator (or the manager) has.
    setStorageMode(mode) {
        this.state.storageMode = mode;
        this.state.procError = null;
        if (mode === 'per_material' && !this.state.storageLines.length) {
            this.loadStorageLines();
        }
    }

    async loadStorageLines() {
        this.state.procSaving = true;
        this.state.procError = null;
        try {
            await this._saveLines();
            const rows = await this.orm.searchRead(
                'recycle.shipment.line',
                [['shipment_id', '=', this.state.proc.id]],
                ['id', 'product_id', 'condition', 'condition_label', 'quantity', 'is_damaged']);
            this.state.storageLines = rows
                .filter(r => !r.is_damaged && r.quantity > 0)
                .map(r => ({
                    id: r.id,
                    name: (r.product_id && r.product_id[1]) || '',
                    condition: r.condition_label || r.condition || '',
                    quantity: r.quantity,
                    zone_id: '',
                }));
        } catch (e) {
            this.state.procError = (e && e.data && e.data.message) || this.tr('Action failed.');
        }
        this.state.procSaving = false;
    }

    async confirmPerMaterialZonesAndFinish() {
        const rows = this.state.storageLines || [];
        if (!rows.length) { this.state.procError = this.tr('Nothing to store.'); return; }
        if (rows.some(r => !r.zone_id)) {
            this.state.procError = this.tr('Assign a storage zone to every material.');
            return;
        }
        this.state.procSaving = true;
        this.state.procError = null;
        try {
            await this.orm.call('recycle.shipment', 'action_assign_line_storage_zones',
                [[this.state.proc.id], rows.map(r => ({ line_id: r.id, zone_id: parseInt(r.zone_id) }))]);
            const results = await this.orm.call('recycle.shipment', 'action_finish_sorting',
                [[this.state.proc.id], this.state.weightShortageReason || null,
                 this.state.shortageReasonCategory || null,
                 this.state.damageReason || null]);
            const result = (results && results[0]) || { status: 'stored' };
            if (result.status === 'stored') {
                this.state.procSuccess = { name: this.state.proc.name };
                this.state.proc = null;
                this.state.showStorageZonePicker = false;
                this.state.storageMode = 'whole';
                this.state.storageLines = [];
                this._loadStats();
            } else {
                this.state.procError = this.tr('Action failed.');
            }
        } catch (e) {
            this.state.procError = (e && e.data && e.data.message) || this.tr('Action failed.');
        }
        this.state.procSaving = false;
    }

    async releaseSorting() {
        try {
            await this.orm.call('recycle.shipment', 'action_release_sorting', [[this.state.proc.id]]);
            this.openSortQueue();
        } catch (e) {
            this.state.procError = (e && e.data && e.data.message) || this.tr('Action failed.');
        }
    }

    // ─── Profile (view + persisted edit) ────────────────────────
    async _rpc(url, params) { return rpcJsonSafe(url, params); }

    async showProfile() {
        this._navigate('profile');
        this.state.profileLoading = true;
        this.state.profileEditMode = false;
        this.state.profileSaveSuccess = null;
        this.state.profileSaveError = null;
        try {
            const r = await this._rpc('/api/recycle/my-profile', {});
            if (r && !r.error) {
                this.state.userProfile = {
                    name: r.name || '',
                    email: r.email || '',
                    login: r.login || '',
                    phone: r.phone || '',
                    role: r.role || 'sorting',
                    warehouse: r.warehouse || '',
                    national_id: r.national_id || '',
                    street: r.street || '',
                    city: r.city || '',
                    country: r.country || '',
                };
            }
        } catch (_) {}
        this.state.profileLoading = false;
    }

    startEditProfile() {
        const p = this.state.userProfile || {};
        this.state.profileForm = {
            name: p.name || '',
            email: p.email || '',
            phone: p.phone || '',
            national_id: p.national_id || '',
            street: p.street || '',
            city: p.city || '',
            country: p.country || '',
        };
        this.state.profileEditMode = true;
        this.state.profileSaveError = null;
    }
    cancelEditProfile() { this.state.profileEditMode = false; this.state.profileSaveError = null; }

    get profileRoleLabel() {
        return this.tr(this.state.userProfile?.role || 'Sorting Employee');
    }

    async saveProfile() {
        const f = this.state.profileForm;
        if (!f.name.trim()) { this.state.profileSaveError = this.tr('Name required'); return; }
        this.state.profileSaving = true;
        this.state.profileSaveError = null;
        try {
            const res = await this._rpc('/api/recycle/save-profile', {
                vals: {
                    name: f.name.trim(),
                    phone: f.phone.trim(),
                    recycle_national_id: f.national_id.trim(),
                    street: f.street.trim(),
                    city: f.city.trim(),
                }
            });
            if (res && res.error) {
                this.state.profileSaveError = res.error;
                this.state.profileSaving = false;
                return;
            }
            this.state.userProfile = {
                ...this.state.userProfile,
                name: f.name.trim(),
                phone: f.phone.trim(),
                national_id: f.national_id.trim(),
                street: f.street.trim(),
                city: f.city.trim(),
            };
            this.userName = f.name.trim();
            this.state.profileEditMode = false;
            this.state.profileSaveSuccess = true;
            setTimeout(() => { this.state.profileSaveSuccess = null; }, 3000);
        } catch (e) {
            this.state.profileSaveError = (e && e.data && e.data.message)
                || this.tr('Update failed. Please try again.');
        }
        this.state.profileSaving = false;
    }

    async logout() {
        const ok = await this.askConfirm(this.tr('Sign out'), this.tr('Sign out of your account.'));
        if (!ok) return;
        document.documentElement.classList.remove('o_ra_dark', 'o_ra_rtl');
        localStorage.removeItem('dw-theme');
        localStorage.removeItem('recycle_wms_dark');
        localStorage.removeItem('recycle_wms_lang');
        window.location.href = '/dawrha/logout';
    }

    // ─── Helpers ────────────────────────────────────────────────
    m2oName(field) {
        if (!field) return '—';
        if (Array.isArray(field)) return field[1] || '—';
        if (typeof field === 'string') return field;
        return '—';
    }
    formatDate(val) {
        if (!val) return '—';
        try { return new Date(val).toLocaleDateString('en-GB'); }
        catch { return val; }
    }
    floatToTime(val) {
        var h = Math.floor(val || 0);
        var m = Math.round(((val || 0) - h) * 60);
        return String(h).padStart(2, '0') + ':' + String(m).padStart(2, '0');
    }

    // ─── Notifications ────────────────────────────────────
    async _loadNotifCount() {
        try {
            this.state.notifUnreadCount = await this.orm.searchCount(
                "recycle.notification",
                [["recipient_user_id", "=", user.userId], ["is_read", "=", false]]
            );
        } catch (e) {}
    }

    async showNotifications() {
        this._navigate('notifications');
        this.state.notifLoading = true;
        try {
            const notifs = await this.orm.searchRead(
                "recycle.notification",
                [["recipient_user_id", "=", user.userId]],
                ["id", "title", "message", "notif_type", "state", "is_read", "create_date"],
                { limit: 50, order: "create_date desc" }
            );
            const iconMap = {
                application: '\u{1F9D1}‍\u{1F4BC}', reactivation: '\u{1F504}',
                shift_change: '\u{1F551}', decision: '\u{1F4E9}',
                role_assignment: '\u{1F464}', shipment: '\u{1F4E6}', order: '\u{1F69A}',
                info: '\u{1F514}',
            };
            this.state.notifications = notifs.map(n => ({
                ...n,
                icon: iconMap[n.notif_type] || '\u{1F514}',
                time: n.create_date || '',
            }));
            const toRead = notifs.filter(n => !n.is_read).map(n => n.id);
            if (toRead.length) {
                try { await this.orm.write("recycle.notification", toRead, { is_read: true }); } catch (e) {}
            }
            this.state.notifUnreadCount = 0;
        } catch (e) {
            this.state.notifications = [];
        }
        this.state.notifLoading = false;
    }

    stateLabel(state, type) {
        const map = {
            shipment: { pending: this.tr("Pending"), receiving: this.tr("In Reception"),
                        escalated: this.tr("Transferred"), accepted: this.tr("Received Status"),
                        sorting: this.tr("In Sorting"),
                        pending_sorting_approval: this.tr("Pending Sorting Approval"),
                        sorted: this.tr("Sorted") },
            report_state: { new: this.tr("In Progress"), approved: this.tr("Approved"),
                            rejected: this.tr("Rejected") },
            damage: { none: '—', pending: this.tr("Pending Approval"),
                      approved: this.tr("Approved"), rejected: this.tr("Rejected") },
            condition: { excellent: this.tr("Excellent"), good: this.tr("Good"),
                         poor: this.tr("Poor"), damaged: this.tr("Damaged") },
        };
        return (map[type] && map[type][state]) || state || '—';
    }
    stateBadgeClass(state) {
        const good = ["sorted", "approved", "working", "excellent"];
        const bad = ["rejected", "damaged", "out_of_service", "retired"];
        const warn = ["accepted", "sorting", "pending", "new", "good"];
        if (good.includes(state)) return "o_ra_badge_success";
        if (bad.includes(state)) return "o_ra_badge_danger";
        if (warn.includes(state)) return "o_ra_badge_warn";
        return "o_ra_badge_muted";
    }

    openChangePassword() {
        this.state.showChangePasswordModal = true;
        this.state.changePasswordStep = 1;
        this.state.changePasswordCurrent = '';
        this.state.changePasswordNew = '';
        this.state.changePasswordConfirm = '';
        this.state.changePasswordError = null;
    }
    closeChangePasswordModal() {
        this.state.showChangePasswordModal = false;
    }
    async submitChangePassword() {
        this.state.changePasswordError = null;
        if (!this.state.changePasswordCurrent || !this.state.changePasswordNew || !this.state.changePasswordConfirm) {
            this.state.changePasswordError = this.tr('Please fill in all fields');
            return;
        }
        if (this.state.changePasswordNew !== this.state.changePasswordConfirm) {
            this.state.changePasswordError = this.tr('New passwords do not match');
            return;
        }
        if (this.state.changePasswordNew.length < 6) {
            this.state.changePasswordError = this.tr('Password must be at least 6 characters');
            return;
        }
        this.state.changePasswordLoading = true;
        try {
            const res = await this._rpc('/api/recycle/change-password', {
                current_password: this.state.changePasswordCurrent,
                new_password: this.state.changePasswordNew,
            });
            if (res && res.success) {
                this.state.changePasswordStep = 2;
            } else {
                this.state.changePasswordError = (res && res.error) || this.tr('Failed to change password');
            }
        } catch (e) {
            this.state.changePasswordError = this.tr('Failed to change password');
        }
        this.state.changePasswordLoading = false;
    }
    async showActiveSessions() {
        this._navigate('active_sessions');
        this.state.sessionsLoading = true;
        try {
            const r = await this._rpc('/api/recycle/my-devices', {});
            this.state.sessions = (r && r.devices) || [];
        } catch (e) { this.state.sessions = []; }
        this.state.sessionsLoading = false;
    }
}

/** Matches the three-decimal quantities Odoo stores — floats otherwise show
 *  a remaining "0.30000000000000004 kg", which reads as a system fault. */
function round3(value) {
    return Math.round(Number(value) * 1000) / 1000;
}

registry.category("actions").add("recycle_sorting_dashboard", RecycleSortingDashboard);
