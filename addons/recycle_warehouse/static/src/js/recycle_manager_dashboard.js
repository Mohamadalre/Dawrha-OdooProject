/** @odoo-module **/
import { registry } from "@web/core/registry";
import { loadBundle } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, onPatched, onWillDestroy, useState, useRef } from "@odoo/owl";
import { session } from "@web/session";
import { user } from "@web/core/user";
import { tr as _tr } from "./recycle_i18n_shared";
import { setDashboardPage, unsetDashboardPage } from "./dashboard_page_state";
import { rpcJson, govLabel, makePager, attachInfiniteScroll, useMessageDialog, useSlowLoad } from "./dashboard_shared";

// Fallback defaults for the admin-configurable sort-reconciliation
// thresholds (warehouse.sorting_tolerance_threshold_1 / _2), used only to
// color-code the per-material breakdown in Sorting Escalations — the
// server is always authoritative for the actual approval decision. The
// real values are loaded into state.sortThresholds on start.
const SORT_SHORTAGE_AUTO_LIMIT_DEFAULT = 3.0;
const SORT_SHORTAGE_REASON_LIMIT_DEFAULT = 15.0;

export class RecycleManagerDashboard extends Component {
    static template = "recycle_warehouse.RecycleManagerDashboard";
    static props = ["*"];

    setup() {
        // Safe defaults — always initialized, never undefined
        this.actionService = null;
        this.orm = null;
        this.notification = null;
        this.userName = (user && user.name) || "Manager";
        this.userEmail = (session && session.partner_id && session.email) || '';
        this.userLogin = (user && user.login) || this.userName;
        this._navHistory = [];
        this.donutChart = null;
        this.barChart = null;
        this.donutCanvasRef = null;
        this.barCanvasRef = null;

        this.state = useState({
            view: "dashboard",
            // Sidebar entry painted green — moves only when another one is clicked.
            activeNavGo: 'goDashboard',
            loading: false,
            dashboardLoading: true,
            _loadingStats: false,
            warehouseName: "",
            sidebarOpen: false,
            navSection: null,
            navSubItem: null,           // which item's nested sub-menu is expanded
            darkMode: (localStorage.getItem('dw-theme')
                       || (localStorage.getItem('recycle_wms_dark') === '1' ? 'dark' : 'light')) === 'dark',
            lang: (localStorage.getItem('recycle_wms_lang') || 'en').replace(/^ar_.*$/, 'ar'),
            stats: {
                employees: 0, shipments: 0, orders: 0, stock_items: 0,
                t_employees: '+0%', t_employees_up: true,
                t_shipments: '+0%', t_shipments_up: true,
                t_orders: '+0%', t_orders_up: true,
                t_stock_items: '+0%', t_stock_items_up: true,
            },
            insights: { mostActive: '', mostActiveValue: 0, mostActiveIcon: '', growthPct: 0, growthUp: true },
            recentShipments: [],
            recentOrders: [],
            filterPeriod: 'month',
            userProfile: {
                name: (user && user.name) || 'Manager',
                email: (session && session.partner_id && session.email) || '',
                login: (user && user.login) || '',
                phone: '',
                role: 'manager',
                warehouse: '',
                national_id: '',
                street: '',
                city: '',
                country: '',
            },
            profileLoading: false,
            profileEditMode: false,
            profileForm: { name: 'Manager', email: '', login: '', phone: '' },
            profileSaving: false,
            profileSaveSuccess: null,
            profileSaveError: null,
            settingsSaved: false,
            notifications: [],
            notifLoading: false,
            notifUnreadCount: 0,
            navUserEmail: '',
            warehouseId: null,
            // ── Employees management ──
            employees: [],
            employeesSummary: { total: 0, active: 0, inactive: 0, by_role: {} },
            employeeSearch: '',
            employeeRoleFilter: '',
            employeeStatusFilter: '',
            selectedEmployee: null,
            employeeEditMode: false,
            employeeForm: { name: '', phone: '', active: true },
            employeeCreateForm: { name: '', email: '', phone: '', national_id: '', role: 'input' },
            employeeSaving: false,
            employeeRatingSaving: false,
            employeeError: null,
            employeeSuccess: null,
            showCreateSuccess: false,
            employeeCreatedName: null,
            employeeCreatedEmail: null,
            warehouses: [],
            // ── Shipments ──
            shipments: [],
            shipmentSearch: '',
            shipmentStateFilter: '',
            shipmentZoneFilter: '',
            shipmentsHasMore: true, shipmentsLoadingMore: false,
            selectedShipment: null,
            selectedShipmentLines: [],
            selectedShipmentExpectedLines: [],
            archivedShipments: [], archivedShipmentsHasMore: true, archivedShipmentsLoadingMore: false,
            // ── Orders ──
            orders: [],
            orderSearch: '',
            orderStateFilter: '',
            orderApprovalFilter: '',
            ordersHasMore: true, ordersLoadingMore: false,
            archivedOrders: [], archivedOrdersHasMore: true, archivedOrdersLoadingMore: false,
            orderRejecting: null,
            orderRejectReason: '',
            orderApprovalSaving: false,
            selectedOrder: null,
            selectedOrderLines: [],
            // ── Stock ──
            stock: [],
            stockZones: [],
            stockZoneFilter: '',
            stockCondFilter: '',
            // ── Attendance ──
            attendance: [],
            attendanceDate: '',
            attendanceStats: { present: 0, late: 0, absentish: 0 },
            // ── Shifts ──
            shifts: [],
            // ── Shift Assignment (manager assigns shifts to employees) ──
            shiftAssignmentEmployees: [],
            shiftAssignmentShifts: [],
            shiftAssignmentSearch: '',
            shiftAssignmentFilter: '',
            selectedShiftEmployee: null,
            shiftAssignForm: { shift_id: '' },
            shiftAssignSaving: false,
            shiftAssignError: null,
            shiftAssignSuccess: null,
            // ── Job Applications (accepted by admin, assigned to my warehouse) ──
            applications: [],
            selectedApplication: null,
            roleForm: { role: 'input', shift_id: '' },
            roleSaving: false,
            roleError: null,
            roleSuccess: null,
            // ── My Warehouse ──
            myWarehouse: null,
            // ── Damaged sorting requests ──
            damaged: [],
            damagedSearch: '',
            rejectingId: null,
            rejectReason: '',
            // ── Sorting escalations (quantity shortfall / auto-blocked) ──
            sortEscalations: [],
            escalationDetailId: null,
            escalationDetail: null,
            escalationDetailLoading: false,
            escalationBusyId: null,
            sortThresholds: { t1: SORT_SHORTAGE_AUTO_LIMIT_DEFAULT, t2: SORT_SHORTAGE_REASON_LIMIT_DEFAULT },
            // ── Damage reports (material damaged after being stored) ──
            damageReports: [],
            damageReportBusyId: null,
            damageReportRejectingId: null,
            damageReportRejectReason: '',
            // ── Filters ──
            zones: [],
            zoneTypeFilter: '',
            // Trucks of MY warehouse (record rule enforces the scope):
            // view + service-state toggle only — data edits are admin-only.
            trucks: [],
            truckSearch: '',
            truckStatusFilter: '',
            // '' = both kinds. Trucks stay one list with a filter rather than
            // two lists, so a truck with a mis-set type shows up in the wrong
            // place instead of vanishing from everywhere.
            truckTypeFilter: '',
            // ── Delivery drivers (recruited here; no shift, no backend account)
            deliveryDrivers: [],
            ddSearch: '',
            ddTruckFilter: '',      // '' | 'assigned' | 'unassigned'
            ddAssigning: null,      // the driver whose assign panel is open
            ddFreeTrucks: [],
            ddSelectedTruck: '',
            ddError: null,
            // The driver's own page. A table cell has room for actions and
            // nothing else; a manager deciding who to give a van to wants to
            // see the licence and its expiry date first.
            ddDetailId: null, ddHistory: [], ddHistoryLoading: false,
            // Licence scans open over the page rather than in a new tab.
            imageViewer: null,
            // Drivers of MY warehouse (accepted driver requests; the record
            // rule scopes reads) + their live truck reservations.
            drivers: [],
            driverSearch: '', driverShiftFilter: '', driverTruckFilter: '',
            driverShifts: [],
            driverAssignments: [],
            // Assign driver to truck (server re-scopes me to my warehouse)
            assignShiftId: '',
            assignOptions: { trucks: [], drivers: [] },
            assignTruckId: null, assignDriverKey: '',
            assignLoading: false, assignSaving: false,
            assignError: null, assignSuccess: null,
            // Shift-change requests (submitted by drivers in the app)
            shiftChangeRequests: [],
            scrTab: 'pending',
            scrApprove: null, scrTrucks: [], scrTruckId: null,
            scrReject: null, scrRejectReason: '',
            scrSaving: false, scrError: null, scrSuccess: null,
            // Truck problems (read-only reports from drivers)
            truckProblems: [],
            // Driver attendance (pickup/dropoff handovers — read-only)
            driverHandovers: [], driverAttDate: '',
            driverAttStats: { present: 0, late: 0, missed: 0, total: 0 },
            // Take-out-of-service reason modal
            truckDisable: null, truckDisableReason: '',
            // Driver detail modal + actions
            driverDetail: null,
            driverBlockModal: false, driverBlockReason: '',
            dscShiftId: '', dscTrucks: [], dscTruckId: null,
            dscOpen: false,
            driverActionSaving: false, driverActionError: null,
            driverActionSuccess: null,
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

        // Shared in-page message/confirm dialog (see useMessageDialog).
        useMessageDialog(this);

        // Branded loading screen, but only when a load actually drags.
        this._clearSlowLoad = useSlowLoad(this);

        try {
            this.actionService = useService("action");
            this.orm = useService("orm");
            this.notification = useService("notification");
        } catch(e) { if (typeof console !== 'undefined' && console.error) console.error("ManagerDashboard services:", e); }

        try { this.donutCanvasRef = useRef('donutCanvas'); } catch(e) {};
        try { this.barCanvasRef = useRef('barCanvas'); } catch(e) {};

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
                if (_p.role && _p.role !== 'manager') {
                    window.location.replace('/recycle/open-dashboard');
                    return;
                }
            } catch (_e) {}
            var self = this;
            try { await loadBundle("web.chartjs_lib"); } catch(e) {}
            var loadTimeout = setTimeout(function() {
                self.state.dashboardLoading = false;
                self.state._loadingStats = false;
            }, 15000);
            try { await this._loadStats(); } catch(e) {}
            try {
                var st = await this._rpc('/api/recycle/sort-thresholds', {});
                if (st && st.threshold_1 != null) {
                    self.state.sortThresholds = { t1: st.threshold_1, t2: st.threshold_2 };
                }
            } catch(e) {}
            clearTimeout(loadTimeout);
            try {
                var u = await this.orm.searchRead('res.users', [['id','=',user.userId]], ['email','login'], {limit:1});
                self.state.navUserEmail = (u && u[0] && (u[0].email || u[0].login)) || '';
            } catch(e) { self.state.navUserEmail = ''; }
            try {
                var r = await this._rpc('/api/recycle/my-profile', {});
                if (r && !r.error) {
                    this.state.userProfile = {
                        name: r.name || '',
                        email: r.email || '',
                        login: r.login || '',
                        phone: r.phone || '',
                        role: r.role || 'manager',
                        warehouse: r.warehouse || '',
                        national_id: r.national_id || '',
                        street: r.street || '',
                        city: r.city || '',
                        country: r.country || '',
                    };
                }
            } catch(e) {
                try {
                    var recs = await this.orm.searchRead(
                        "res.users", [["id", "=", user.userId]],
                        ["id", "name", "email", "login", "phone", "recycle_role",
                         "recycle_warehouse_id", "recycle_national_id"]);
                    if (recs.length) {
                        var r2 = recs[0];
                        this.state.userProfile = {
                            name: r2.name || '',
                            email: r2.email || r2.login || '',
                            login: r2.login || '',
                            phone: r2.phone || '',
                            role: r2.recycle_role || 'manager',
                            warehouse: Array.isArray(r2.recycle_warehouse_id)
                                ? r2.recycle_warehouse_id[1] : '',
                            national_id: r2.recycle_national_id || '',
                            street: '',
                            city: '',
                            country: '',
                        };
                    }
                } catch(e2) {}
            }
            // Load unread notification count for bell badge
            await this._loadNotifCount();
        });
        onMounted(() => {
            this._syncCharts();
            this._startPolling();
            if (typeof Chart === 'undefined') {
                var self = this;
                var checkTimer = setInterval(function() {
                    if (typeof Chart !== 'undefined') {
                        clearInterval(checkTimer);
                        self._chartsStale = true;
                        self._syncCharts();
                    }
                }, 500);
            }
            setDashboardPage();
            this._applyTheme();
            // Scroll-to-load-more for the long-lived lists — no page-number
            // buttons, the next batch of older rows loads itself.
            this._detachScroll = attachInfiniteScroll(() => this.state.view, {
                shipments_list: () => this.loadMoreShipments(),
                orders_list: () => this.loadMoreOrders(),
                archived_shipments: () => this.loadMoreArchivedShipments(),
                archived_orders: () => this.loadMoreArchivedOrders(),
            });
        });
        onPatched(() => this._syncCharts());
        onWillDestroy(() => {
            this._stopPolling();
            unsetDashboardPage();
            if (this._detachScroll) this._detachScroll();
            clearTimeout(this._shipmentSearchTimer);
            // The slow-load timer would otherwise fire on a destroyed
            // component and set state nobody is rendering.
            if (this._clearSlowLoad) this._clearSlowLoad();
            clearTimeout(this._orderSearchTimer);
        });
    }

    tr(key) {
        var lang = this.state.lang === 'ar' ? 'ar' : 'en';
        localStorage.setItem('recycle_wms_lang', lang);
        return _tr(key);
    }

    govLabel(code) {
        return govLabel(code, (s) => this.tr(s));
    }

    async _loadStats(period) {
        if (this.state._loadingStats) {
            this.state._pendingPeriod = period;
            return;
        }
        this.state._loadingStats = true;
        this.state._pendingPeriod = null;
        period = period || 'month';
        try {
            var result = await this._rpc('/api/manager/dashboard', { period: period });
            if (!result || result.error) {
                this.state.dashboardLoading = false;
                this.state._loadingStats = false;
                return;
            }
            this.state.warehouseName = result.warehouse_name || '';
            this.state.warehouseId = result.warehouse_id || null;
            this.state.stats = result.stats || this.state.stats;
            this.state.insights = result.insights || this.state.insights;
            this.state.recentShipments = result.recent_shipments || [];
            this.state.recentOrders = result.recent_orders || [];
            this.state.filterPeriod = period;
            this._chartsStale = true;
            this.state.dashboardLoading = false;
            this.state._loadingStats = false;
            if (this.state._pendingPeriod && this.state._pendingPeriod !== period) {
                this._loadStats(this.state._pendingPeriod);
            }
        } catch (e) {
            this.state.dashboardLoading = false;
            this.state._loadingStats = false;
            this.state._pendingPeriod = null;
        }
    }

    setFilterPeriod(period) {
        if (!this.state.view) return;
        // Already on this period and idle → nothing to do.
        if (period === this.state.filterPeriod && !this.state._loadingStats) return;
        // Never bail just because a load is running: the dashboard polls, so
        // `_loadingStats` is often true, and the old guard swallowed the click
        // — the filter appeared stuck on the same values. `_loadStats` queues a
        // period given while busy and runs it next, so pass it straight on.
        this.state._chartsStale = true;
        this.state.filterPeriod = period; // reflect on the buttons immediately
        this.state.dashboardLoading = true;
        this._loadStats(period);
    }

    _startPolling() {
        this._stopPolling();
        this._pollInterval = setInterval(() => {
            if (document.hidden) return;
            if (this.state.view === 'dashboard' && !this.state._loadingStats) {
                this._loadStats(this.state.filterPeriod);
            } else if (this.state.view === 'shipments_list' && !this._pollingShipments) {
                this._pollRefreshShipments();
            } else if (this.state.view === 'orders_list' && !this._pollingOrders) {
                this._pollRefreshOrders();
            }
            this._loadNotifCount();
        }, 5000);
    }
    _stopPolling() {
        if (this._pollInterval) { clearInterval(this._pollInterval); this._pollInterval = null; }
    }
    async _pollRefreshShipments() {
        // If the manager has scrolled down and loaded extra pages, a silent
        // background refresh must never yank those back out from under them.
        if (this.state.shipments.length > this.SHIPMENTS_PAGE_SIZE) return;
        this._pollingShipments = true;
        try {
            const pager = makePager(this.orm, { model: 'recycle.shipment', fields: this.MGR_SHIPMENT_FIELDS, pageSize: this.SHIPMENTS_PAGE_SIZE });
            const { rows, hasMore } = await pager.fetchFirst(this._shipmentDomain());
            this.state.shipments = rows;
            this.state.shipmentsHasMore = hasMore;
        } catch (e) { /* silent */ }
        this._pollingShipments = false;
    }
    async _pollRefreshOrders() {
        // Don't yank the list out from under an open reject dialog.
        if (this.state.orderRejecting) return;
        if (this.state.orders.length > this.ORDERS_PAGE_SIZE) return;
        this._pollingOrders = true;
        try {
            const pager = makePager(this.orm, { model: 'recycle.order', fields: this.MGR_ORDER_FIELDS, pageSize: this.ORDERS_PAGE_SIZE });
            const { rows, hasMore } = await pager.fetchFirst(this._orderDomain());
            this.state.orders = rows;
            this.state.ordersHasMore = hasMore;
        } catch (e) { /* silent */ }
        this._pollingOrders = false;
    }

    // Real 7-day running-total history → a smooth filled area/line chart
    // (like a small stock chart) instead of the old hardcoded squiggle or
    // a plain straight line. Higher current value = curve rises (smaller
    // y), matching the ▲/▼ trend arrow shown next to it. Each day's point
    // also gets an invisible hover target with a native tooltip so the
    // exact value per day is inspectable.
    _sparkData(series) {
        const vals = (series && series.length) ? series : [0, 0];
        const min = Math.min(...vals);
        const max = Math.max(...vals, min + 1);
        const n = vals.length;
        const pts = vals.map((v, i) => ({
            x: (i / (n - 1)) * 70,
            y: 24 - ((v - min) / (max - min)) * 20,
            v,
            daysAgo: n - 1 - i,
        }));
        let path = `M ${pts[0].x.toFixed(1)},${pts[0].y.toFixed(1)}`;
        for (let i = 0; i < pts.length - 1; i++) {
            const p0 = pts[i], p1 = pts[i + 1];
            const mx = (p0.x + p1.x) / 2, my = (p0.y + p1.y) / 2;
            path += ` Q ${p0.x.toFixed(1)},${p0.y.toFixed(1)} ${mx.toFixed(1)},${my.toFixed(1)}`;
        }
        const last = pts[pts.length - 1];
        path += ` T ${last.x.toFixed(1)},${last.y.toFixed(1)}`;
        const area = `${path} L ${last.x.toFixed(1)},28 L 0,28 Z`;
        return {
            path, area,
            dots: pts,
            endX: last.x.toFixed(1), endY: last.y.toFixed(1),
        };
    }

    get chartItems() {
        const s = this.state.stats;
        return [
            { label: 'Employees',   value: s.employees,    added: s.added_employees ?? 0,   color: '#6366f1', colorDark: '#4f46e5', icon: '\u{1F465}', trend: s.t_employees || '+0%', trendUp: (s.t_employees_up ?? true), spark: s.spark_employees },
            { label: 'Shipments',   value: s.shipments,    added: s.added_shipments ?? 0,   color: '#8b5cf6', colorDark: '#7c3aed', icon: '\u{1F4E6}', trend: s.t_shipments || '+0%', trendUp: (s.t_shipments_up ?? true), spark: s.spark_shipments },
            { label: 'Orders',      value: s.orders,       added: s.added_orders ?? 0,      color: '#f97316', colorDark: '#ea580c', icon: '\u{1F4CB}', trend: s.t_orders || '+0%', trendUp: (s.t_orders_up ?? true), spark: s.spark_orders },
            { label: 'Stock Items', value: s.stock_items,  added: s.added_stock_items ?? 0, color: '#10b981', colorDark: '#059669', icon: '\u{1F4E5}', trend: s.t_stock_items || '+0%', trendUp: (s.t_stock_items_up ?? true), spark: s.spark_stock_items },
            // Trucks assigned to this warehouse — same card shape as the rest; the
            // KPI grid is already laid out for five columns and is responsive.
            { label: 'Trucks', value: s.trucks, added: s.added_trucks ?? 0, color: '#0ea5e9', colorDark: '#0284c7', icon: '\u{1F69A}', trend: s.t_trucks || '+0%', trendUp: (s.t_trucks_up ?? true), spark: s.spark_trucks },
        ].map(i => {
            const sd = this._sparkData(i.spark);
            return { ...i, labelTr: this.tr(i.label), sparkId: 'spark-' + i.label.replace(/\s+/g, ''),
                     sparkPath: sd.path, sparkArea: sd.area, sparkDots: sd.dots,
                     sparkEndX: sd.endX, sparkEndY: sd.endY };
        });
    }

    get kpiCards() {
        return this.chartItems;
    }

    get chartMaxVal() {
        return Math.max(...this.chartItems.map(i => i.value), 1);
    }

    get donutItems() {
        var items = this.chartItems;
        var total = items.reduce(function (s, i) { return s + i.value; }, 0);
        return items.map(function (i) {
            var pct = total > 0 ? Math.round((i.value / total) * 100) : 0;
            return Object.assign({}, i, { pct: pct });
        });
    }

    get chartHasData() {
        return this.chartItems.some(i => i.value > 0);
    }

    get donutTotal() {
        return this.chartItems.reduce(function (s, i) { return s + i.value; }, 0);
    }

    get navSections() {
        return [
            { key: 'home', icon: '\u{1F3E0}', label: 'Home', single: true, go: 'goDashboard', view: 'dashboard' },
            { key: 'mywarehouse', icon: '\u{1F3ED}', label: 'My Warehouse', single: true, go: 'openMyWarehouse', view: 'my_warehouse' },
            // Trucks stay ONE screen with a type filter: they are the same kind
            // of record wearing a flag, and two lists would drift apart — a
            // truck with a mis-set type would vanish from both instead of
            // showing up in the wrong one.
            { key: 'trucks', icon: '\u{1F69B}', label: 'Trucks', items: [
                { label: 'Truck Management', go: 'openTrucks' },
                { label: 'Assign Driver to Truck', go: 'openAssignDriver' },
                { label: 'Shift Change Requests', go: 'openShiftChangeRequests' },
                { label: 'Truck Problems', go: 'openTruckProblems' },
            ]},
            // Drivers get their OWN section, split by kind — the opposite
            // decision from trucks, and for the opposite reason. A collector has
            // a backend account, an onboarding state and a shift; a delivery
            // driver has a licence on file and a delivery truck. They share
            // almost no field, so one merged list would show half its columns
            // empty on every row, and even the assign action differs: a
            // collector is booked through the shift picker, a delivery driver
            // straight onto a truck.
            { key: 'drivers', icon: '\u{1F9D1}‍\u{1F527}', label: 'Drivers', items: [
                { label: 'Collection Drivers', go: 'openDriversList' },
                { label: 'Delivery Drivers', go: 'openDeliveryDrivers' },
            ]},
            { key: 'operations', icon: '\u{1F69A}', label: 'Operations', items: [
                { label: 'Shipments', go: 'openShipments' },
                { label: 'Orders', go: 'openOrders' },
                { label: 'Sorting Escalations', go: 'openSortingEscalations' },
            ]},
            // Damaged materials get their own section: the two ways material is
            // written off are read side by side \u2014 what did not survive sorting,
            // and what spoiled after it was already stored.
            { key: 'damaged', icon: '\u{1F5D1}\uFE0F', label: 'Damaged Materials', items: [
                { label: 'Damaged during sorting', go: 'openDamagedRequests' },
                { label: 'Damaged in inventory', go: 'openDamageReports' },
            ]},
            { key: 'archived', icon: '\u{1F5C4}\uFE0F', label: 'Archived', items: [
                { label: 'Archived Shipments', go: 'openArchivedShipments' },
                { label: 'Archived Orders', go: 'openArchivedOrders' },
            ]},
            { key: 'employees', icon: '\u{1F465}', label: 'Employees', items: [
                { label: 'My Employees', go: 'openEmployeesList' },
                { label: 'Job Applications', go: 'openApplications' },
                { label: 'Add Employee', go: 'openCreateEmployee' },
            ]},
            { key: 'inventory', icon: '\u{1F4E6}', label: 'Inventory', items: [
                { label: 'Stock', go: 'openStockList' },
                { label: 'Zones', go: 'openZonesList' },
            ]},
            { key: 'shifts', icon: '\u{1F551}', label: 'Shifts', items: [
                { label: 'All Shifts', go: 'openShiftsList' },
                { label: 'Assign Shift', go: 'openShiftAssignment' },
                // One "Attendance" entry expanding to the two attendance screens
                // (drivers / warehouse staff) — same design, own view.
                { label: 'Attendance', subitems: [
                    { label: 'Driver Attendance', go: 'openDriverAttendance' },
                    { label: 'Warehouse Staff Attendance', go: 'openAttendance' },
                ]},
            ]},
        ];
    }

    toggleSidebar(ev) {
        if (ev) { ev.stopPropagation(); ev.preventDefault(); }
        this.state.sidebarOpen = !this.state.sidebarOpen;
    }

    toggleNavSection(key) {
        this.state.navSection = this.state.navSection === key ? null : key;
    }

    // Expand/collapse a nested sub-menu inside a section item (e.g. Attendance).
    toggleNavSubItem(label) {
        this.state.navSubItem = this.state.navSubItem === label ? null : label;
    }

    navClick(fnName) {
        this.state.sidebarOpen = false;
        this.state.activeNavGo = fnName;
        const fn = this[fnName];
        if (typeof fn === 'function') fn.call(this);
    }

    _navigate(view) { this._navHistory.push(this.state.view); this.state.view = view; }

    goBack() { this.state.view = this._navHistory.pop() || "dashboard"; }

    goDashboard() {
        this._navHistory = [];
        this.state.view = "dashboard";
        this.state.dashboardLoading = false;
    }

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
                    role: r.role || 'manager',
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
        const p = this.state.userProfile;
        this.state.profileForm = {
            name: p.name || '',
            email: p.email || '',
            login: p.login || '',
            phone: p.phone || '',
            national_id: p.national_id || '',
            street: p.street || '',
            city: p.city || '',
            country: p.country || '',
        };
        this.state.profileEditMode = true;
        this.state.profileSaveSuccess = null;
        this.state.profileSaveError = null;
    }

    get profileRoleLabel() {
        return this.tr(this.state.userProfile?.role || 'Manager');
    }

    cancelEditProfile() {
        this.state.profileEditMode = false;
        this.state.profileSaveError = null;
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
                || this.tr('Failed to save profile. Please try again.');
        }
        this.state.profileSaving = false;
    }

    showSettings() {
        this._navigate('settings');
        this.state.settingsSaved = false;
    }

    saveSettings() {
        this.state.settingsSaved = true;
        setTimeout(() => { this.state.settingsSaved = false; }, 2500);
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

    async _loadNotifCount() {
        try {
            this.state.notifUnreadCount = await this.orm.searchCount(
                "recycle.notification",
                [["recipient_user_id", "=", user.userId], ["is_read", "=", false]]
            );
        } catch(e) {}
    }

    async showNotifications() {
        this._navigate('notifications');
        this.state.notifLoading = true;
        try {
            // Managers only see notifications addressed to THEM personally
            // (admin broadcasts stay admin-only).
            const notifs = await this.orm.searchRead(
                "recycle.notification",
                [["recipient_user_id", "=", user.userId]],
                ["id", "title", "message", "notif_type", "state", "is_read",
                 "request_user_id", "create_date"],
                { limit: 50, order: "create_date desc" }
            );
            const iconMap = {
                application: '\u{1F9D1}\u200D\u{1F4BC}', reactivation: '\u{1F504}',
                shift_change: '\u{1F551}', decision: '\u{1F4E9}',
                role_assignment: '\u{1F464}', stock_empty: '\u26A0\uFE0F',
                info: '\u{1F514}',
            };
            this.state.notifications = notifs.map(n => ({
                ...n,
                icon: iconMap[n.notif_type] || '\u{1F514}',
                time: n.create_date || '',
            }));
            const toRead = notifs.filter(n => !n.is_read && n.state !== 'pending').map(n => n.id);
            if (toRead.length) {
                try { await this.orm.write("recycle.notification", toRead, { is_read: true }); } catch (e) {}
            }
            this.state.notifUnreadCount = notifs.filter(n => !n.is_read && n.state === 'pending').length;
        } catch(e) {
            this.state.notifications = [];
        }
        this.state.notifLoading = false;
    }

    async approveReactivation(notif) {
        try {
            await this.orm.call("recycle.notification", "action_reactivation_approve", [[notif.id]]);
            this.notification.add(this.tr('Account reactivated.'), { type: "success" });
            await this.showNotifications();
        } catch (e) {
            this.notification.add((e && e.data && e.data.message) || this.tr('Action failed.'), { type: "danger" });
        }
    }
    async rejectReactivation(notif) {
        try {
            await this.orm.call("recycle.notification", "action_reactivation_reject", [[notif.id]]);
            this.notification.add(this.tr('Request declined.'), { type: "success" });
            await this.showNotifications();
        } catch (e) {
            this.notification.add((e && e.data && e.data.message) || this.tr('Action failed.'), { type: "danger" });
        }
    }

    _syncCharts() {
        if (typeof Chart === 'undefined') return;
        const donutEl = this.donutCanvasRef && this.donutCanvasRef.el;
        const barEl = this.barCanvasRef && this.barCanvasRef.el;
        if (donutEl && (this._chartsStale || !Chart.getChart(donutEl))) {
            this.renderDonutChart();
        }
        if (barEl && (this._chartsStale || !Chart.getChart(barEl))) {
            this.renderBarChart();
        }
        this._chartsStale = false;
    }

    _chartTheme() {
        var dark = document.documentElement.classList.contains('o_ra_dark') ||
                   (this.state && this.state.darkMode);
        return {
            isDark: dark,
            text:      dark ? '#e8edf5' : '#1f2937',
            muted:     dark ? '#9aa6bd' : '#6b7280',
            grid:      dark ? 'rgba(255,255,255,0.08)' : 'rgba(148,163,184,0.18)',
            tooltipBg: dark ? 'rgba(15,23,42,0.95)' : 'rgba(255,255,255,0.95)',
            tooltipTitle: dark ? '#f1f5f9' : '#1f2937',
            tooltipBody:  dark ? '#cbd5e1' : '#4b5563',
        };
    }

    renderDonutChart() {
        var canvas = this.donutCanvasRef && this.donutCanvasRef.el;
        if (!canvas || typeof Chart === 'undefined') return;
        if (this.donutChart) { this.donutChart.destroy(); this.donutChart = null; }
        try {
            var th = this._chartTheme();
            var items = this.donutItems;
            var labels = items.map(function (i) { return i.labelTr || i.label; });
            var values = items.map(function (i) { return i.value; });
            var colors = items.map(function (i) { return i.color; });
            var donutTotal = values.reduce(function (a, b) { return a + b; }, 0);

            this.donutChart = new Chart(canvas, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: values,
                        backgroundColor: colors,
                        borderWidth: 0,
                        hoverOffset: 8,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    cutout: '72%',
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: th.tooltipBg,
                            titleColor: th.tooltipTitle,
                            bodyColor: th.tooltipBody,
                            padding: 12,
                            cornerRadius: 10,
                            callbacks: {
                                label: function (ctx) {
                                    var t = ctx.dataset.data.reduce(function (a, b) { return a + b; }, 0);
                                    var pct = t > 0 ? ((ctx.parsed / t) * 100).toFixed(1) : 0;
                                    return ctx.label + ': ' + ctx.parsed + ' (' + pct + '%)';
                                },
                            },
                        },
                    },
                    animation: {
                        animateRotate: true,
                        duration: 1000,
                    },
                },
                plugins: [{
                    id: 'centerText',
                    beforeDraw: function (chart) {
                        var w = chart.width, h = chart.height;
                        var ctx = chart.ctx;
                        ctx.save();
                        var totalVal = chart._totals || chart.data.datasets[0].data.reduce(function (a, b) { return a + b; }, 0);
                        chart._totals = totalVal;
                        var fontSize = Math.min(w, h) / 7.5;
                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'middle';
                        ctx.font = '700 ' + fontSize + 'px system-ui, sans-serif';
                        ctx.fillStyle = getComputedStyle(canvas).getPropertyValue('--ra-text') || '#0f172a';
                        ctx.fillText(totalVal, w / 2, h / 2 - fontSize * 0.3);
                        ctx.font = '500 ' + (fontSize * 0.38) + 'px system-ui, sans-serif';
                        ctx.fillStyle = getComputedStyle(canvas).getPropertyValue('--ra-text-muted') || '#64748b';
                        ctx.fillText('Total', w / 2, h / 2 + fontSize * 0.45);
                        ctx.restore();
                    },
                }],
            });
        } catch (e) {
            if (console && console.warn) console.warn('DonutChart:', e);
        }
    }

    renderBarChart() {
        var canvas = this.barCanvasRef && this.barCanvasRef.el;
        if (!canvas || typeof Chart === 'undefined') return;
        if (this.barChart) { this.barChart.destroy(); this.barChart = null; }
        try {
            var th = this._chartTheme();
            var items = this.donutItems;
            var labels = items.map(function (i) { return i.labelTr || i.label; });
            var values = items.map(function (i) { return i.value; });
            var colors = items.map(function (i) { return i.color; });

            var bgColors = items.map(function (i) {
                if (typeof canvas.getContext === 'undefined') return i.color;
                var ctx = canvas.getContext('2d');
                var grad = ctx.createLinearGradient(0, 0, 0, 200);
                var c = i.color;
                var cDark = i.colorDark || c;
                var c1 = th.isDark ? cDark : c;
                var c2 = th.isDark ? c : (c + 'cc');
                grad.addColorStop(0, c1);
                grad.addColorStop(0.5, c2);
                grad.addColorStop(1, th.isDark ? (c + '99') : (c + '88'));
                return grad;
            });
            this.barChart = new Chart(canvas, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        data: values,
                        backgroundColor: bgColors,
                        borderColor: colors,
                        borderWidth: 0,
                        borderRadius: 8,
                        barPercentage: 0.55,
                        categoryPercentage: 0.8,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    indexAxis: 'x',
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: th.tooltipBg,
                            titleColor: th.tooltipTitle,
                            bodyColor: th.tooltipBody,
                            padding: 12,
                            cornerRadius: 10,
                            callbacks: {
                                label: function (ctx) {
                                    var t = ctx.dataset.data.reduce(function (a, b) { return a + b; }, 0);
                                    var pct = t > 0 ? ((ctx.parsed / t) * 100).toFixed(1) : 0;
                                    return ctx.label + ': ' + ctx.parsed + ' (' + pct + '%)';
                                },
                            },
                        },
                        datalabels: { display: false },
                    },
                    scales: {
                        x: {
                            grid: { display: false },
                            ticks: {
                                color: th.muted,
                                font: { weight: '600', size: 11 },
                                maxRotation: 0,
                            },
                        },
                        y: {
                            beginAtZero: true,
                            grid: { color: th.grid, drawBorder: false },
                            ticks: {
                                color: th.muted,
                                font: { size: 10 },
                            },
                        },
                    },
                    animation: {
                        duration: 800,
                        easing: 'easeOutQuart',
                    },
                },
                plugins: [{
                    id: 'barLabels',
                    afterDraw: function (chart) {
                        var ctx = chart.ctx;
                        chart.data.datasets.forEach(function (ds, i) {
                            var t = ds.data.reduce(function (a, b) { return a + b; }, 0);
                            var meta = chart.getDatasetMeta(i);
                            meta.data.forEach(function (bar, idx) {
                                var val = ds.data[idx];
                                var pct = t > 0 ? ((val / t) * 100).toFixed(1) : 0;
                                ctx.save();
                                ctx.textAlign = 'center';
                                ctx.textBaseline = 'bottom';
                                ctx.font = '700 12px system-ui, sans-serif';
                                ctx.fillStyle = th.text;
                                ctx.fillText(pct + '%', bar.x, bar.y - 6);
                                ctx.restore();
                            });
                        });
                    },
                }],
            });
        } catch (e) {
            if (console && console.warn) console.warn('BarChart:', e);
        }
    }

    toggleDarkMode() {
        this.state.darkMode = !this.state.darkMode;
        localStorage.setItem('dw-theme', this.state.darkMode ? 'dark' : 'light');
        this._applyTheme();
    }

    _applyTheme() {
        const root = document.documentElement;
        if (this.state.darkMode) {
            root.classList.add('o_ra_dark');
        } else {
            root.classList.remove('o_ra_dark');
        }
    }

    setLang(lang) {
        this.state.lang = lang;
        localStorage.setItem('recycle_wms_lang', lang);
        if (lang === 'ar') {
            document.documentElement.classList.add('o_ra_rtl');
        } else {
            document.documentElement.classList.remove('o_ra_rtl');
        }
    }

    stateLabel(state, type) {
        const map = {
            shipment:   { pending: this.tr("Pending"), receiving: this.tr("In Reception"),
                          escalated: this.tr("Transferred"),
                          accepted: this.tr("Received Status"), sorting: this.tr("In Sorting"),
                          pending_sorting_approval: this.tr("Pending Sorting Approval"),
                          sorted: this.tr("Sorted") },
            order:      { pending: this.tr("Pending"), processing: this.tr("Processing"),
                          ready: this.tr("Ready"),
                          completed: this.tr("Completed"), cancelled: this.tr("Cancelled") },
            role:       { manager: this.tr("Warehouse Manager"), input: this.tr("Input Employee"),
                          sorting: this.tr("Sorting Employee"), output: this.tr("Output Employee") },
            zone_type:  { receiving: this.tr("Receiving"), sorting: this.tr("Sorting"),
                          storage: this.tr("Storage"), output: this.tr("Output") },
            report_state: { new: this.tr("New"), approved: this.tr("Approved"),
                            rejected: this.tr("Rejected") },
            condition:  { excellent: this.tr("Excellent"), good: this.tr("Good"),
                          poor: this.tr("Poor"), damaged: this.tr("Damaged") },
        };
        return (map[type] && map[type][state]) || state || '—';
    }

    stateBadgeClass(state) {
        const good = ["accepted","working","completed","resolved","approved","published"];
        const bad  = ["rejected","out_of_service","retired","cancelled","escalated"];
        const warn = ["pending","in_progress","interview","receiving"];
        if (good.includes(state)) return "o_ra_badge_success";
        if (bad.includes(state))  return "o_ra_badge_danger";
        if (warn.includes(state)) return "o_ra_badge_warn";
        return "o_ra_badge_muted";
    }

    formatDate(val) {
        if (!val) return "—";
        try { return new Date(val).toLocaleDateString("en-GB"); }
        catch { return val; }
    }

    // ─── JSON-RPC helper for the warehouse-scoped manager API ─────────
    async _rpc(url, params) { return rpcJson(url, params); }

    // Explicit warehouse domain — belt & braces on top of the record rules.
    _whDomain() {
        return this.state.warehouseId
            ? [['warehouse_id', '=', this.state.warehouseId]]
            : [];
    }

    m2oName(field) {
        if (!field) return '—';
        if (Array.isArray(field)) return field[1] || '—';
        if (typeof field === 'string') return field;
        return '—';
    }

    floatToTime(val) {
        var h = Math.floor(val || 0);
        var m = Math.round(((val || 0) - h) * 60);
        return String(h).padStart(2, '0') + ':' + String(m).padStart(2, '0');
    }

    // ─── Employees (server-side filtered API) ──────────────────────────
    async openEmployeesList() {
        this._navigate('employees_list');
        this.state.loading = true;
        this.state.employeeSuccess = null;
        try {
            const res = await this._rpc('/api/manager/employees', {});
            if (!res.error) {
                this.state.employees = res.employees || [];
                this.state.employeesSummary = res.summary ||
                    { total: 0, active: 0, inactive: 0, by_role: {} };
                this.state.warehouseId = res.warehouse_id || this.state.warehouseId;
                this.state.warehouseName = res.warehouse_name || this.state.warehouseName;
            } else {
                this.state.employees = [];
            }
        } catch (e) { this.state.employees = []; }
        if (this.state.warehouseId && !this.state.warehouses.length) {
            try {
                const wh = await this.orm.searchRead(
                    'recycle.warehouse', [['id', '=', this.state.warehouseId]],
                    ['id', 'name'], { limit: 1 });
                this.state.warehouses = wh || [];
            } catch (e) { this.state.warehouses = []; }
        }
        this.state.loading = false;
    }

    get filteredEmployees() {
        const q = (this.state.employeeSearch || '').toLowerCase().trim();
        const role = this.state.employeeRoleFilter;
        const status = this.state.employeeStatusFilter;
        return this.state.employees.filter(e => {
            if (q && !((e.name || '').toLowerCase().includes(q)
                    || (e.email || '').toLowerCase().includes(q)
                    || (e.login || '').toLowerCase().includes(q))) return false;
            if (role && e.role !== role) return false;
            if (status === 'active' && !e.active) return false;
            if (status === 'inactive' && e.active) return false;
            return true;
        });
    }

    async openEmployeeDetail(emp) {
        this.state.selectedEmployee = emp;
        this.state.employeeEditMode = false;
        this.state.employeeError = null;
        this.state.employeeSuccess = null;
        try {
            const res = await this._rpc('/api/manager/warehouse-shifts', {});
            if (res && res.shifts) {
                this.state.shifts = res.shifts;
            } else {
                this.state.shifts = [];
            }
        } catch (e) { this.state.shifts = []; }
        if (this.state.warehouseId && !this.state.warehouses.length) {
            try {
                const wh = await this.orm.searchRead(
                    'recycle.warehouse', [['id', '=', this.state.warehouseId]],
                    ['id', 'name'], { limit: 1 });
                this.state.warehouses = wh || [];
            } catch (e) { this.state.warehouses = []; }
        }
        this._navigate('employee_detail');
    }

    startEditEmployee() {
        const e = this.state.selectedEmployee;
        const empShift = e.shift_id;
        this.state.employeeForm = {
            phone: e.phone || '',
            active: String(e.active),
            role: e.role || 'input',
            shift_id: Array.isArray(empShift) ? empShift[0] : (typeof empShift === 'number' ? empShift : ''),
        };
        this.state.employeeEditMode = true;
        this.state.employeeError = null;
        this.state.employeeSuccess = null;
    }

    cancelEditEmployee() {
        this.state.employeeEditMode = false;
        this.state.employeeError = null;
        this.state.employeeSuccess = null;
    }

    async saveEditEmployee() {
        const e = this.state.selectedEmployee;
        const f = this.state.employeeForm;
        this.state.employeeSaving = true;
        this.state.employeeError = null;
        this.state.employeeSuccess = null;
        const oldRole = e.role;
        try {
            const res = await this._rpc('/api/manager/employee/update', {
                employee_id: e.id,
                phone: f.phone || '',
                active: f.active === 'true',
                role: f.role || false,
                shift_id: f.shift_id ? parseInt(f.shift_id, 10) : false,
            });
            if (res.error) {
                const errMap = {
                    'invalid_shift': this.tr('Invalid shift. Please select a valid shift for your warehouse.'),
                    'invalid_role': this.tr('Invalid role.'),
                    'not_found': this.tr('Employee not found.'),
                    'forbidden': this.tr('You do not have permission to perform this action.'),
                    'write_failed': this.tr('Failed to save. Please try again.'),
                };
                this.state.employeeError = errMap[res.error] || this.tr('Update failed: ') + res.error;
            } else {
                e.phone = res.phone !== undefined ? res.phone : e.phone;
                e.active = res.active !== undefined ? res.active : e.active;
                e.role = res.role !== undefined ? res.role : e.role;
                e.recycle_role = res.role !== undefined ? res.role : e.recycle_role;
                e.shift_id = res.shift_id !== undefined ? res.shift_id : e.shift_id;
                e.shift = res.shift !== undefined ? res.shift : e.shift;
                const idx = this.state.employees.findIndex(x => x.id === e.id);
                if (idx >= 0) Object.assign(this.state.employees[idx], e);
                this.state.employeeEditMode = false;
                this.state.employeeSuccess = this.tr('Employee information has been updated successfully.');
                setTimeout(() => { this.state.employeeSuccess = null; }, 3000);
                if (oldRole !== res.role) {
                    this._sendRoleChangeNotification(e, oldRole);
                }
            }
        } catch (err) {
            this.state.employeeError = this.tr('Update failed. Please try again.');
        }
        this.state.employeeSaving = false;
    }

    ratingStars(n) {
        n = n || 0;
        return '★'.repeat(n) + '☆'.repeat(5 - n);
    }

    async rateEmployee(stars) {
        const e = this.state.selectedEmployee;
        if (!e || this.state.employeeRatingSaving) return;
        // Clicking the already-set star again clears the rating (toggle to 0).
        const rating = (e.performance_rating === stars) ? 0 : stars;
        this.state.employeeRatingSaving = true;
        try {
            const res = await this._rpc('/api/manager/employee/rate', {
                employee_id: e.id, rating,
            });
            if (res && !res.error) {
                e.performance_rating = res.performance_rating;
                const idx = this.state.employees.findIndex(x => x.id === e.id);
                if (idx >= 0) this.state.employees[idx].performance_rating = res.performance_rating;
                this.notification.add(this.tr('Rating saved.'), { type: 'success' });
            } else {
                this.notification.add(this.tr('Failed to save rating.'), { type: 'danger' });
            }
        } catch (err) {
            this.notification.add(this.tr('Failed to save rating.'), { type: 'danger' });
        }
        this.state.employeeRatingSaving = false;
    }

    async printEmployeeReport() {
        const emp = this.state.selectedEmployee;
        if (!emp) return;
        await this.actionService.doAction(
            'recycle_warehouse.action_report_employee',
            { additionalContext: { active_id: emp.id, active_ids: [emp.id], active_model: 'res.users' } }
        );
    }

    async _sendRoleChangeNotification(emp, oldRole, oldShift) {
        const roleLabels = {
            input: 'Input Employee', sorting: 'Sorting Employee',
            output: 'Output Employee',
        };
        let msg = '';
        if (oldRole !== emp.role) {
            msg = this.tr('Your role has been changed to') + ' ' + (roleLabels[emp.role] || emp.role);
        }
        if (oldShift !== emp.shift_id) {
            const extra = this.tr('Your shift has been updated');
            msg = msg ? msg + '. ' + extra : extra;
        }
        if (!msg) return;
        try {
            await this._rpc('/api/manager/notification/send', {
                user_id: emp.id,
                title: this.tr('Role Updated'),
                message: msg,
                type: 'info',
            });
        } catch (e) {}
    }

    async toggleEmployeeActive(emp) {
        try {
            const res = await this._rpc('/api/manager/employee/update', {
                employee_id: emp.id, active: !emp.active,
            });
            if (!res.error) {
                emp.active = res.active;
                const s = this.state.employeesSummary;
                s.active += emp.active ? 1 : -1;
                s.inactive += emp.active ? -1 : 1;
            }
        } catch (e) {}
    }

    openCreateEmployee() {
        this.state.employeeCreateForm = {
            name: '', email: '', phone: '', national_id: '', role: 'input',
        };
        this.state.employeeError = null;
        this.state.employeeSaving = false;
        this.state.employeeCreatedName = null;
        this._navigate('employee_create');
    }

    async saveNewEmployee() {
        const f = this.state.employeeCreateForm;
        if (!f.name.trim()) { this.state.employeeError = this.tr('Name required'); return; }
        if (!f.email.trim()) { this.state.employeeError = this.tr('Email is required for login and password reset.'); return; }
        this.state.employeeSaving = true;
        this.state.employeeError = null;
        try {
            const res = await this._rpc('/api/manager/employee/create', {
                name: f.name, email: f.email,
                phone: f.phone, national_id: f.national_id, role: f.role,
            });
            this.state.employeeSaving = false;
            if (res.error === 'login_exists') {
                this.state.employeeError = this.tr('An account with this email already exists.');
            } else if (res.error === 'national_id_exists') {
                this.state.employeeError = this.tr('This national ID is already registered for another employee.');
            } else if (res.error === 'email_required') {
                this.state.employeeError = this.tr('Email is required for login and password reset.');
            } else if (res.error) {
                this.state.employeeError = this.tr('Creation failed. Please check the fields.');
            } else {
                this.state.employeeCreatedName = f.name;
                this.state.employeeCreatedEmail = f.email;
                this.state.showCreateSuccess = true;
                setTimeout(() => { this.state.showCreateSuccess = false; }, 6000);
            }
        } catch (e) {
            this.state.employeeSaving = false;
            this.state.employeeError = this.tr('Creation failed. Please check the fields.');
        }
    }

    // ─── Shipments (record rules + explicit warehouse domain) ─────────
    SHIPMENTS_PAGE_SIZE = 200;
    MGR_SHIPMENT_FIELDS = ['id', 'name', 'driver_name', 'state', 'received_at',
        'expected_weight', 'actual_weight', 'receiver_user_id', 'sorter_user_id',
        'sorted_at'];

    // Current zone is derived from the shipment state (workflow zones)
    zoneForState(state) {
        if (['pending', 'receiving', 'escalated'].includes(state)) return 'receiving';
        if (['accepted', 'sorting'].includes(state)) return 'sorting';
        if (state === 'sorted') return 'storage';
        return 'receiving';
    }

    _shipmentDomain() {
        const domain = this._whDomain().concat([['recycle_archived', '=', false]]);
        if (this.state.shipmentStateFilter) domain.push(['state', '=', this.state.shipmentStateFilter]);
        const zone = this.state.shipmentZoneFilter;
        if (zone === 'sorting') domain.push(['state', 'in', ['accepted', 'sorting']]);
        else if (zone === 'storage') domain.push(['state', '=', 'sorted']);
        else if (zone === 'receiving') domain.push(['state', 'not in', ['accepted', 'sorting', 'sorted']]);
        const q = (this.state.shipmentSearch || '').trim();
        if (q) domain.push("|", ['name', 'ilike', q], ['driver_name', 'ilike', q]);
        return domain;
    }

    async openShipments() {
        this._navigate('shipments_list');
        await this._refetchShipments();
    }

    async _refetchShipments() {
        this.state.loading = true;
        this.state.shipments = [];
        this.state.shipmentsHasMore = true;
        try {
            const pager = makePager(this.orm, { model: 'recycle.shipment', fields: this.MGR_SHIPMENT_FIELDS, pageSize: this.SHIPMENTS_PAGE_SIZE });
            const { rows, hasMore } = await pager.fetchFirst(this._shipmentDomain());
            this.state.shipments = rows;
            this.state.shipmentsHasMore = hasMore;
        } catch (e) { this.state.shipments = []; }
        this.state.loading = false;
    }

    onShipmentSearchInput(ev) {
        this.state.shipmentSearch = ev.target.value;
        clearTimeout(this._shipmentSearchTimer);
        this._shipmentSearchTimer = setTimeout(() => this._refetchShipments(), 400);
    }

    onShipmentFilterChange() {
        this._refetchShipments();
    }

    async loadMoreShipments() {
        if (this.state.view !== 'shipments_list') return;
        if (!this.state.shipmentsHasMore || this.state.shipmentsLoadingMore || this.state.loading) return;
        this.state.shipmentsLoadingMore = true;
        try {
            const lastId = this.state.shipments.length
                ? this.state.shipments[this.state.shipments.length - 1].id : 0;
            const pager = makePager(this.orm, { model: 'recycle.shipment', fields: this.MGR_SHIPMENT_FIELDS, pageSize: this.SHIPMENTS_PAGE_SIZE });
            const { rows, hasMore } = await pager.fetchMore(this._shipmentDomain(), lastId);
            this.state.shipments = this.state.shipments.concat(rows);
            this.state.shipmentsHasMore = hasMore;
        } catch (e) { /* silent */ }
        this.state.shipmentsLoadingMore = false;
    }

    get filteredShipments() {
        // Filtering now happens server-side (see _shipmentDomain).
        return this.state.shipments;
    }

    async openShipmentDetail(s) {
        this.state.selectedShipment = s;
        this._navigate('shipment_detail');
        this.state.loading = true;
        try {
            this.state.selectedShipmentLines = await this.orm.searchRead(
                'recycle.shipment.line', [['shipment_id', '=', s.id]],
                ['product_id', 'quantity', 'condition', 'uom_id']);
        } catch (e) { this.state.selectedShipmentLines = []; }
        try {
            this.state.selectedShipmentExpectedLines = await this.orm.searchRead(
                'recycle.shipment.expected.line', [['shipment_id', '=', s.id]],
                ['product_id', 'expected_qty', 'uom_id']);
        } catch (e) { this.state.selectedShipmentExpectedLines = []; }
        this.state.loading = false;
    }

    // ─── Orders ────────────────────────────────────────────────────────
    ORDERS_PAGE_SIZE = 200;
    MGR_ORDER_FIELDS = ['id', 'name', 'customer_name', 'state', 'create_date',
        'amount_total', 'invoice_number', 'output_user_id',
        'manager_approval', 'approval_reject_reason'];

    _orderDomain() {
        const domain = this._whDomain().concat([['recycle_archived', '=', false]]);
        if (this.state.orderStateFilter) domain.push(['state', '=', this.state.orderStateFilter]);
        if (this.state.orderApprovalFilter) domain.push(['manager_approval', '=', this.state.orderApprovalFilter]);
        const q = (this.state.orderSearch || '').trim();
        if (q) domain.push("|", ['name', 'ilike', q], "|", ['customer_name', 'ilike', q], ['invoice_number', 'ilike', q]);
        return domain;
    }

    async openOrders() {
        this._navigate('orders_list');
        await this._refetchOrders();
    }

    async _refetchOrders() {
        this.state.loading = true;
        this.state.orders = [];
        this.state.ordersHasMore = true;
        try {
            const pager = makePager(this.orm, { model: 'recycle.order', fields: this.MGR_ORDER_FIELDS, pageSize: this.ORDERS_PAGE_SIZE });
            const { rows, hasMore } = await pager.fetchFirst(this._orderDomain());
            this.state.orders = rows;
            this.state.ordersHasMore = hasMore;
        } catch (e) { this.state.orders = []; }
        this.state.loading = false;
    }

    onOrderSearchInput(ev) {
        this.state.orderSearch = ev.target.value;
        clearTimeout(this._orderSearchTimer);
        this._orderSearchTimer = setTimeout(() => this._refetchOrders(), 400);
    }

    onOrderFilterChange() {
        this._refetchOrders();
    }

    async loadMoreOrders() {
        if (this.state.view !== 'orders_list') return;
        if (!this.state.ordersHasMore || this.state.ordersLoadingMore || this.state.loading) return;
        this.state.ordersLoadingMore = true;
        try {
            const lastId = this.state.orders.length
                ? this.state.orders[this.state.orders.length - 1].id : 0;
            const pager = makePager(this.orm, { model: 'recycle.order', fields: this.MGR_ORDER_FIELDS, pageSize: this.ORDERS_PAGE_SIZE });
            const { rows, hasMore } = await pager.fetchMore(this._orderDomain(), lastId);
            this.state.orders = this.state.orders.concat(rows);
            this.state.ordersHasMore = hasMore;
        } catch (e) { /* silent */ }
        this.state.ordersLoadingMore = false;
    }

    // ── Manager approval of API-created orders ──
    async approveOrder(o, ev) {
        if (ev) { ev.stopPropagation(); ev.preventDefault(); }
        if (this.state.orderApprovalSaving) return;
        this.state.orderApprovalSaving = true;
        try {
            const r = await this._rpc('/api/manager/order/approve', { order_id: o.id });
            if (r && r.ok) {
                o.manager_approval = 'approved';
                if (this.state.selectedOrder && this.state.selectedOrder.id === o.id) {
                    this.state.selectedOrder.manager_approval = 'approved';
                }
                if (this.notification) this.notification.add(
                    this.tr('Order approved and released to output employees.'), { type: 'success' });
            } else if (this.notification) {
                this.notification.add((r && r.error) || 'Error', { type: 'danger' });
            }
        } catch (e) {
            if (this.notification) this.notification.add(String(e), { type: 'danger' });
        }
        this.state.orderApprovalSaving = false;
    }
    rejectOrder(o, ev) {
        if (ev) { ev.stopPropagation(); ev.preventDefault(); }
        this.state.orderRejecting = o;
        this.state.orderRejectReason = '';
    }
    cancelRejectOrder() {
        this.state.orderRejecting = null;
        this.state.orderRejectReason = '';
    }
    async confirmRejectOrder() {
        const o = this.state.orderRejecting;
        if (!o || this.state.orderApprovalSaving) return;
        this.state.orderApprovalSaving = true;
        try {
            const r = await this._rpc('/api/manager/order/reject', {
                order_id: o.id, reason: this.state.orderRejectReason || '' });
            if (r && r.ok) {
                o.manager_approval = 'rejected';
                o.approval_reject_reason = this.state.orderRejectReason || '';
                if (this.state.selectedOrder && this.state.selectedOrder.id === o.id) {
                    this.state.selectedOrder.manager_approval = 'rejected';
                }
                if (this.notification) this.notification.add(
                    this.tr('Order rejected.'), { type: 'success' });
                this.cancelRejectOrder();
            } else if (this.notification) {
                this.notification.add((r && r.error) || 'Error', { type: 'danger' });
            }
        } catch (e) {
            if (this.notification) this.notification.add(String(e), { type: 'danger' });
        }
        this.state.orderApprovalSaving = false;
    }
    approvalBadgeClass(v) {
        if (v === 'approved') return 'o_ra_badge_success';
        if (v === 'rejected') return 'o_ra_badge_danger';
        return 'o_ra_badge_warning';
    }
    approvalLabel(v) {
        if (v === 'approved') return this.tr('Approved');
        if (v === 'rejected') return this.tr('Rejected');
        return this.tr('Pending Approval');
    }

    get filteredOrders() {
        // Filtering now happens server-side (see _orderDomain).
        return this.state.orders;
    }

    get pendingApprovalCount() {
        return this.state.orders.filter(o => o.manager_approval === 'pending').length;
    }

    async openOrderDetail(o) {
        this.state.selectedOrder = o;
        this._navigate('order_detail');
        this.state.loading = true;
        try {
            this.state.selectedOrderLines = await this.orm.searchRead(
                'recycle.order.line', [['order_id', '=', o.id]],
                ['product_id', 'quantity', 'price_unit', 'subtotal']);
        } catch (e) { this.state.selectedOrderLines = []; }
        this.state.loading = false;
    }

    // ─── Stock ─────────────────────────────────────────────────────────
    async openStockList() {
        this._navigate('stock_list');
        this.state.loading = true;
        this.state.stockZoneFilter = '';
        this.state.stockSearch = '';         // free-text product-name filter
        this.state.stockCondFilter = null;   // null = All; '' = ungraded/unsorted
        try {
            this.state.stock = await this.orm.searchRead(
                'recycle.stock', this._whDomain(),
                ['id', 'product_id', 'quantity', 'warehouse_id', 'zone_id', 'condition',
                 'condition_label', 'reserved_qty', 'available_qty'],
                { order: 'product_id asc' });
            this.state.stockZones = await this.orm.searchRead(
                'recycle.zone', this._whDomain().concat([['zone_type', '=', 'storage']]),
                ['id', 'name'], { order: 'name asc' });
        } catch (e) { this.state.stock = []; this.state.stockZones = []; }
        this.state.loading = false;
    }

    get filteredStock() {
        let list = this.state.stock;
        // Free-text search on the product name — product_id is Odoo's
        // [id, display_name] pair, so the name is the second element.
        const q = (this.state.stockSearch || '').toLowerCase().trim();
        if (q) {
            list = list.filter(st =>
                ((st.product_id && st.product_id[1]) || '').toLowerCase().includes(q));
        }
        const z = this.state.stockZoneFilter;
        if (z) list = list.filter(st => st.zone_id && st.zone_id[0] === Number(z));
        if (this.state.stockCondFilter !== null) {
            // null is "All"; '' is the real filter for ungraded/unsorted stock,
            // which is a state stock can genuinely be in and must stay
            // selectable on its own.
            list = list.filter(st => (st.condition || '') === this.state.stockCondFilter);
        }
        return list;
    }

    setStockCondFilter(cond) {
        this.state.stockCondFilter = cond === undefined ? null : cond;
    }

    /** Grade filter buttons, derived from the stock actually held. */
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

    conditionBadgeClass(condition) {
        return {
            excellent: 'o_ra_badge_success',
            good: 'o_ra_badge_info',
            poor: 'o_ra_badge_warning',
            damaged: 'o_ra_badge_danger',
        }[condition] || 'o_ra_badge_muted';
    }

    get stockTotalQty() {
        return this.state.stock.reduce((s, r) => s + (r.quantity || 0), 0);
    }

    // ─── Attendance ────────────────────────────────────────────────────
    async openAttendance() {
        this._navigate('attendance_list');
        this.state.loading = true;
        if (!this.state.attendanceDate) {
            const n = new Date();
            this.state.attendanceDate = n.getFullYear() + '-'
                + String(n.getMonth() + 1).padStart(2, '0') + '-'
                + String(n.getDate()).padStart(2, '0');
        }
        try {
            this.state.attendance = await this.orm.searchRead(
                'recycle.attendance',
                this._whDomain().concat([['date', '=', this.state.attendanceDate]]),
                ['id', 'employee_name', 'date', 'check_in_display',
                 'check_out_display', 'status', 'late_minutes', 'work_hours',
                 'shift_id'],
                { order: 'employee_name asc' });
            const present = this.state.attendance.filter(a => a.status === 'present').length;
            const late = this.state.attendance.filter(a => (a.status || '').includes('late')).length;
            this.state.attendanceStats = {
                present: present,
                late: late,
                absentish: Math.max(this.state.employeesSummary.active - this.state.attendance.length, 0),
            };
        } catch (e) { this.state.attendance = []; }
        this.state.loading = false;
    }

    setAttendanceDate(val) {
        this.state.attendanceDate = val;
        this.openAttendance();
    }

    // ─── Shifts ────────────────────────────────────────────────────────
    async openShiftsList() {
        this._navigate('shifts_list');
        this.state.loading = true;
        try {
            this.state.shifts = await this.orm.searchRead(
                'recycle.shift', [],
                ['id', 'name', 'start_time', 'end_time', 'tolerance', 'warehouse_id'],
                { order: 'name asc' });
        } catch (e) { this.state.shifts = []; }
        this.state.loading = false;
    }

    // ─── Shift Assignment (manager assigns shifts to employees) ─────
    async openShiftAssignment() {
        this._navigate('shift_assignment_list');
        this.state.loading = true;
        this.state.shiftAssignSuccess = null;
        this.state.shiftAssignError = null;
        try {
            const res = await this._rpc('/api/manager/shift-assignment/employees', {
                shift_filter: this.state.shiftAssignmentFilter || '',
            });
            if (!res.error) {
                this.state.shiftAssignmentEmployees = res.employees || [];
                this.state.warehouseId = res.warehouse_id || this.state.warehouseId;
                this.state.warehouseName = res.warehouse_name || this.state.warehouseName;
            } else {
                this.state.shiftAssignmentEmployees = [];
            }
        } catch (e) { this.state.shiftAssignmentEmployees = []; }
        // Load warehouse shifts for the assignment dropdown
        try {
            const sRes = await this._rpc('/api/manager/shift-assignment/warehouse-shifts', {});
            if (!sRes.error) {
                this.state.shiftAssignmentShifts = sRes.shifts || [];
            }
        } catch (e) {}
        this.state.loading = false;
    }

    get filteredShiftAssignmentEmployees() {
        const q = (this.state.shiftAssignmentSearch || '').toLowerCase().trim();
        const f = this.state.shiftAssignmentFilter;
        return this.state.shiftAssignmentEmployees.filter(e => {
            if (q && !((e.name || '').toLowerCase().includes(q)
                    || (e.email || '').toLowerCase().includes(q))) return false;
            if (f === 'assigned' && !e.has_shift) return false;
            if (f === 'unassigned' && e.has_shift) return false;
            return true;
        });
    }

    setShiftAssignmentFilter(val) {
        this.state.shiftAssignmentFilter = val;
        this.openShiftAssignment();
    }

    openShiftAssignmentDetail(emp) {
        this.state.selectedShiftEmployee = emp;
        this.state.shiftAssignForm = { shift_id: emp.shift_id ? String(emp.shift_id) : '' };
        this.state.shiftAssignError = null;
        this.state.shiftAssignSuccess = null;
        this._navigate('shift_assignment_detail');
    }

    async assignShiftToEmployee() {
        const emp = this.state.selectedShiftEmployee;
        const f = this.state.shiftAssignForm;
        this.state.shiftAssignSaving = true;
        this.state.shiftAssignError = null;
        this.state.shiftAssignSuccess = null;
        try {
            const shiftId = f.shift_id ? parseInt(f.shift_id) : 0;
            const res = await this._rpc('/api/manager/shift-assignment/assign', {
                employee_id: emp.id,
                shift_id: shiftId,
            });
            if (res.error) {
                this.state.shiftAssignError = res.error === 'invalid_shift'
                    ? this.tr('Invalid shift selection.')
                    : this.tr('Assignment failed. Please try again.');
            } else {
                emp.shift_id = res.shift_id || false;
                emp.shift_name = res.shift_name || '';
                emp.has_shift = !!res.shift_id;
                // Update the employee in the list too
                const listEmp = this.state.shiftAssignmentEmployees.find(e => e.id === emp.id);
                if (listEmp) {
                    listEmp.shift_id = res.shift_id || false;
                    listEmp.shift_name = res.shift_name || '';
                    listEmp.has_shift = !!res.shift_id;
                }
                this.state.shiftAssignSuccess = this.tr('Shift assigned successfully!');
                setTimeout(() => { this.state.shiftAssignSuccess = null; }, 4000);
            }
        } catch (e) {
            this.state.shiftAssignError = this.tr('Assignment failed. Please try again.');
        }
        this.state.shiftAssignSaving = false;
    }

    // ─── My Warehouse ──────────────────────────────────────────────────
    async openMyWarehouse() {
        this._navigate('my_warehouse');
        this.state.loading = true;
        try {
            const whs = await this.orm.searchRead(
                'recycle.warehouse', [],
                ['id', 'name', 'code', 'governorate', 'shipment_count',
                 'employee_count', 'order_count'],
                { limit: 1 });
            this.state.myWarehouse = whs[0] || null;
            if (whs[0]) {
                this.state.warehouseId = whs[0].id;
                this.state.warehouseName = whs[0].name;
            }
        } catch (e) { this.state.myWarehouse = null; }
        this.state.loading = false;
    }

    // ─── Job Applications (accepted by admin — role/shift assignment only)
    async openApplications() {
        this._navigate('applications_list');
        this.state.loading = true;
        this.state.roleSuccess = null;
        try {
            // Fetch job applicants accepted by admin
            const appRes = await this.orm.searchRead(
                'hr.applicant',
                [['recycle_state', '=', 'accepted']],
                ['id', 'recycle_name', 'partner_name', 'email_from',
                 'recycle_role', 'recycle_warehouse_id', 'employee_user_id',
                 'recycle_job_type', 'create_date'],
                { order: 'id desc', limit: 200 });
            const apps = (appRes || []).map(a => ({ ...a, type: 'applicant' }));

            // Fetch employees awaiting role assignment
            let awaiting = [];
            try {
                const res = await this._rpc('/api/manager/awaiting-role', {});
                awaiting = (res.employees || []).map(e => ({
                    id: e.id,
                    recycle_name: e.name,
                    partner_name: e.name,
                    email_from: e.email,
                    recycle_role: e.role,
                    recycle_warehouse_id: e.recycle_warehouse_id,
                    employee_user_id: e.id,
                    recycle_job_type: e.job_type,
                    create_date: e.create_date,
                    type: 'awaiting_role',
                    _userId: e.id,
                }));
            } catch (e) {}

            this.state.applications = [...awaiting, ...apps];
        } catch (e) { this.state.applications = []; }
        // Shifts for the assignment select
        try {
            if (!this.state.shifts.length) {
                this.state.shifts = await this.orm.searchRead(
                    'recycle.shift', [],
                    ['id', 'name', 'start_time', 'end_time', 'tolerance', 'warehouse_id'],
                    { order: 'name asc' });
            }
        } catch (e) {}
        this.state.loading = false;
    }

    get roleFormSpecializedRole() {
        const jt = this.state.selectedApplication && this.state.selectedApplication.recycle_job_type;
        return ['input', 'sorting', 'output'].includes(jt) ? jt : null;
    }

    openApplicationDetail(app) {
        this.state.selectedApplication = app;
        const specialized = ['input', 'sorting', 'output'].includes(app.recycle_job_type);
        this.state.roleForm = { role: specialized ? app.recycle_job_type : (app.recycle_role || 'input'), shift_id: '' };
        this.state.roleError = null;
        this.state.roleSuccess = null;
        this._navigate('application_detail');
    }

    async assignRole() {
        const app = this.state.selectedApplication;
        const f = this.state.roleForm;
        if (!f.role) { this.state.roleError = this.tr('Please select a role.'); return; }
        this.state.roleSaving = true;
        this.state.roleError = null;
        try {
            if (app.type === 'awaiting_role') {
                const userId = app._userId || app.employee_user_id;
                const res = await this._rpc('/api/manager/employee/update', {
                    employee_id: userId,
                    role: f.role,
                    shift_id: f.shift_id ? parseInt(f.shift_id) : undefined,
                });
                if (res.error === 'role_locked') {
                    throw new Error(this.tr('This position is specialized — only the role designated for the job can be assigned.'));
                }
                if (res.error) {
                    throw new Error(res.error);
                }
                app.recycle_role = f.role;
                this.state.applications = this.state.applications.filter(a => a.id !== app.id || a.type !== 'awaiting_role');
            } else {
                const wizVals = { applicant_id: app.id, role: f.role };
                if (f.shift_id) wizVals.shift_id = parseInt(f.shift_id);
                const wizId = await this.orm.create('recycle.role.wizard', [wizVals]);
                await this.orm.call('recycle.role.wizard', 'action_confirm', [wizId]);
                app.recycle_role = f.role;
            }
            this.state.roleSuccess = this.tr('Role and shift assigned successfully!');
            setTimeout(() => { this.state.roleSuccess = null; }, 4000);
        } catch (e) {
            this.state.roleError = (e && e.data && e.data.message)
                || this.tr('Assignment failed. Make sure the employee account exists.');
        }
        this.state.roleSaving = false;
    }

    // ─── Damaged sorting requests (>40% damaged) ───────────────────────
    async openDamagedRequests() {
        this._navigate('damaged_list');
        this.state.loading = true;
        this.state.rejectingId = null;
        try {
            this.state.damaged = await this.orm.searchRead(
                'recycle.shipment',
                this._whDomain().concat([['damage_request_state', 'in', ['pending', 'approved', 'rejected']]]),
                ['id', 'name', 'sorter_user_id', 'damage_pct', 'damage_reason',
                 'damage_request_state', 'damage_reject_reason', 'state'],
                // Oldest first — the longest-waiting write-off is dealt with first.
                { order: 'id asc' });
        } catch (e) { this.state.damaged = []; }
        this.state.loading = false;
    }

    get filteredDamaged() {
        const q = (this.state.damagedSearch || '').toLowerCase().trim();
        return this.state.damaged.filter(s =>
            !q || (s.name || '').toLowerCase().includes(q)
               || (Array.isArray(s.sorter_user_id) ? s.sorter_user_id[1] : '').toLowerCase().includes(q));
    }

    async approveDamaged(s) {
        try {
            await this.orm.call('recycle.shipment', 'action_approve_damage', [[s.id]]);
            s.damage_request_state = 'approved';
            this.notification.add(this.tr('Request approved. The employee was notified.'), { type: 'success' });
        } catch (e) {
            this.notification.add((e && e.data && e.data.message) || this.tr('Action failed.'), { type: 'danger' });
        }
    }

    startRejectDamaged(s) { this.state.rejectingId = s.id; this.state.rejectReason = ''; }
    cancelRejectDamaged() { this.state.rejectingId = null; }

    async confirmRejectDamaged(s) {
        try {
            await this.orm.call('recycle.shipment', 'action_reject_damage',
                [[s.id], this.state.rejectReason]);
            s.damage_request_state = 'rejected';
            s.damage_reject_reason = this.state.rejectReason;
            this.state.rejectingId = null;
            this.notification.add(this.tr('Request rejected. The employee was notified.'), { type: 'success' });
        } catch (e) {
            this.notification.add((e && e.data && e.data.message) || this.tr('Action failed.'), { type: 'danger' });
        }
    }

    async managerMoveToStorage(s) {
        try {
            await this.orm.call('recycle.shipment', 'action_finish_sorting', [[s.id]]);
            this.state.damaged = this.state.damaged.filter(x => x.id !== s.id);
            this.notification.add(this.tr('Shipment moved to storage.'), { type: 'success' });
        } catch (e) {
            this.notification.add((e && e.data && e.data.message) || this.tr('Action failed.'), { type: 'danger' });
        }
    }

    // ─── Sorting escalations: sorter-initiated transfers (sort_escalation_
    // state='pending') AND shipments auto-blocked by Rule 2/Rule 3
    // (state='pending_sorting_approval') — one queue, both need the
    // manager's review. ─────────────────────────────────────────────────
    async openSortingEscalations() {
        this._navigate('sort_escalations_list');
        this.state.loading = true;
        try {
            const manual = await this.orm.searchRead(
                'recycle.shipment',
                this._whDomain().concat([['sort_escalation_state', '=', 'pending']]),
                ['id', 'name', 'sorter_user_id', 'actual_weight',
                 'weight_shortfall_pct', 'sort_escalation_reason', 'state'],
                { order: 'id desc' });
            const blocked = await this.orm.searchRead(
                'recycle.shipment',
                this._whDomain().concat([['state', '=', 'pending_sorting_approval']]),
                ['id', 'name', 'sorter_user_id', 'actual_weight',
                 'weight_shortfall_pct', 'sort_escalation_reason', 'state'],
                { order: 'id desc' });
            this.state.sortEscalations = manual.map(s => ({ ...s, kind: 'manual' }))
                .concat(blocked.map(s => ({ ...s, kind: 'auto_blocked' })));
        } catch (e) { this.state.sortEscalations = []; }
        this.state.loading = false;
    }

    // Auto-blocked (Rule 2 over threshold_2 / Rule 3 exact-match mismatch):
    // unblock the sorter to correct/finish it themselves — does NOT store
    // directly (unlike approveAndStoreSortEscalation below).
    async approveSortingReconciliation(s) {
        this.state.escalationBusyId = s.id;
        try {
            await this.orm.call('recycle.shipment', 'action_approve_sorting_reconciliation', [[s.id]]);
            this.state.sortEscalations = this.state.sortEscalations.filter(x => x.id !== s.id);
            if (this.state.escalationDetailId === s.id) {
                this.state.escalationDetailId = null;
                this.state.escalationDetail = null;
            }
            this.notification.add(this.tr('Approved. The sorter can now finish this shipment.'), { type: 'success' });
        } catch (e) {
            this.notification.add((e && e.data && e.data.message) || this.tr('Action failed.'), { type: 'danger' });
        }
        this.state.escalationBusyId = null;
    }

    async resolveSortEscalation(s) {
        try {
            await this.orm.call('recycle.shipment', 'action_resolve_sort_escalation', [[s.id]]);
            this.state.sortEscalations = this.state.sortEscalations.filter(x => x.id !== s.id);
            if (this.state.escalationDetailId === s.id) {
                this.state.escalationDetailId = null;
                this.state.escalationDetail = null;
            }
            this.notification.add(this.tr('Sent back to the employee to correct the quantities.'), { type: 'success' });
        } catch (e) {
            this.notification.add((e && e.data && e.data.message) || this.tr('Action failed.'), { type: 'danger' });
        }
    }

    // Manager reviews the numbers as logged by the sorter and stores the
    // shipment directly (bypasses the shortage thresholds server-side —
    // action_finish_sorting skips all reconciliation checks for a
    // supervisor). This is the "approve" half of the transfer; "Resolve"
    // above is the "send back to fix" half.
    async approveAndStoreSortEscalation(s) {
        this.state.escalationBusyId = s.id;
        try {
            await this.orm.call('recycle.shipment', 'action_finish_sorting', [[s.id]]);
            this.state.sortEscalations = this.state.sortEscalations.filter(x => x.id !== s.id);
            if (this.state.escalationDetailId === s.id) {
                this.state.escalationDetailId = null;
                this.state.escalationDetail = null;
            }
            this.notification.add(this.tr('Approved. The shipment was moved to storage.'), { type: 'success' });
        } catch (e) {
            this.notification.add((e && e.data && e.data.message) || this.tr('Action failed.'), { type: 'danger' });
        }
        this.state.escalationBusyId = null;
    }

    shortfallClass(pct) {
        if (pct == null) return 'o_ra_badge_muted';
        const t = this.state.sortThresholds || {};
        const t1 = t.t1 != null ? t.t1 : SORT_SHORTAGE_AUTO_LIMIT_DEFAULT;
        const t2 = t.t2 != null ? t.t2 : SORT_SHORTAGE_REASON_LIMIT_DEFAULT;
        if (pct > t2) return 'o_ra_badge_danger';
        if (pct > t1) return 'o_ra_badge_warning';
        return 'o_ra_badge_success';
    }

    unitLabel(uomName) {
        return uomName || this.tr('units');
    }

    // ─── Damage reports (material damaged AFTER being stored) ──────────
    async openDamageReports() {
        this._navigate('damage_reports_list');
        this.state.loading = true;
        try {
            this.state.damageReports = await this.orm.searchRead(
                'recycle.stock.damage.report',
                this._whDomain().concat([['state', '=', 'pending_approval']]),
                // `condition_label` rather than the raw code: grades belong to
                // the material and are named by the admin, so only the server
                // can turn a code into the word this material's grade actually
                // is. A manager approving a write-off should read the name they
                // set, not a machine code.
                ['id', 'name', 'product_id', 'condition', 'condition_label',
                 'quantity', 'uom_id', 'reason',
                 'reported_by', 'create_date'],
                // Oldest first — same order as the sorting write-offs.
                { order: 'create_date asc' });
        } catch (e) { this.state.damageReports = []; }
        this.state.loading = false;
    }

    async approveDamageReport(r) {
        this.state.damageReportBusyId = r.id;
        try {
            await this.orm.call('recycle.stock.damage.report', 'action_approve', [[r.id]]);
            this.state.damageReports = this.state.damageReports.filter(x => x.id !== r.id);
            this.notification.add(this.tr('Approved. Stock was updated.'), { type: 'success' });
        } catch (e) {
            this.notification.add((e && e.data && e.data.message) || this.tr('Action failed.'), { type: 'danger' });
        }
        this.state.damageReportBusyId = null;
    }

    startRejectDamageReport(r) {
        this.state.damageReportRejectingId = r.id;
        this.state.damageReportRejectReason = '';
    }
    cancelRejectDamageReport() {
        this.state.damageReportRejectingId = null;
        this.state.damageReportRejectReason = '';
    }
    async confirmRejectDamageReport(r) {
        this.state.damageReportBusyId = r.id;
        try {
            await this.orm.call('recycle.stock.damage.report', 'action_reject',
                [[r.id], this.state.damageReportRejectReason || null]);
            this.state.damageReports = this.state.damageReports.filter(x => x.id !== r.id);
            this.state.damageReportRejectingId = null;
            this.notification.add(this.tr('Rejected.'), { type: 'success' });
        } catch (e) {
            this.notification.add((e && e.data && e.data.message) || this.tr('Action failed.'), { type: 'danger' });
        }
        this.state.damageReportBusyId = null;
    }

    // Toggle the per-material entered-vs-expected breakdown for one
    // escalated shipment, fetched on demand so the list itself stays fast.
    async toggleEscalationDetail(s) {
        if (this.state.escalationDetailId === s.id) {
            this.state.escalationDetailId = null;
            this.state.escalationDetail = null;
            return;
        }
        this.state.escalationDetailId = s.id;
        this.state.escalationDetail = null;
        this.state.escalationDetailLoading = true;
        try {
            this.state.escalationDetail = await this.orm.call(
                'recycle.shipment', 'get_sort_reconciliation', [[s.id]]);
        } catch (e) {
            this.state.escalationDetail = null;
            this.notification.add((e && e.data && e.data.message) || this.tr('Action failed.'), { type: 'danger' });
        }
        this.state.escalationDetailLoading = false;
    }

    async openZonesList() {
        this._navigate('zones_list');
        this.state.loading = true;
        try {
            this.state.zones = await this.orm.searchRead(
                'recycle.zone', this._whDomain(),
                ['id', 'name', 'zone_type'], { order: 'zone_type asc, name asc' });
        } catch (e) { this.state.zones = []; }
        this.state.loading = false;
    }

    get filteredZones() {
        const t = this.state.zoneTypeFilter;
        return t ? this.state.zones.filter(z => z.zone_type === t) : this.state.zones;
    }

    // ─── Trucks (my warehouse — view + service-state toggle only) ──────
    async openTrucks() {
        this._navigate('trucks_list');
        this.state.loading = true;
        try {
            // The record rule already scopes reads to this manager's
            // warehouse; the explicit domain keeps intent obvious.
            this.state.trucks = await this.orm.searchRead(
                'recycle.truck', this._whDomain(),
                ['id', 'name', 'plate_number', 'model', 'year',
                 'max_payload_kg', 'warehouse_id', 'is_active',
                 'truck_type', 'disable_reason'],
                { order: 'name' });
        } catch (e) { this.state.trucks = []; }
        this.state.loading = false;
    }

    get filteredTrucks() {
        const q = (this.state.truckSearch || '').trim().toLowerCase();
        const st = this.state.truckStatusFilter;
        const ty = this.state.truckTypeFilter;
        return this.state.trucks.filter((t) => {
            if (st === 'active' && !t.is_active) return false;
            if (st === 'inactive' && t.is_active) return false;
            // One screen for both kinds, filtered. Two separate lists would
            // drift apart, and a truck whose type was mis-set would disappear
            // from both instead of showing up in the wrong one.
            if (ty && t.truck_type !== ty) return false;
            if (q) {
                const hay = [t.name, t.plate_number, t.model || ''].join(' ').toLowerCase();
                if (!hay.includes(q)) return false;
            }
            return true;
        });
    }

    onTruckSearchInput(ev) { this.state.truckSearch = ev.target.value; }
    setTruckStatusFilter(ev) { this.state.truckStatusFilter = ev.target.value; }
    setTruckTypeFilter(type) { this.state.truckTypeFilter = type || ''; }

    truckTypeLabel(type) {
        return type === 'delivery' ? this.tr('Delivery') : this.tr('Collection');
    }

    // ─── Delivery drivers (recruited in Odoo — no shift, no backend) ───
    //
    // Kept apart from the collector list on purpose: a collector's identity
    // lives in the backend and their assignment is made through a shift, while
    // this person is hired here and is put straight onto a delivery truck.
    async openDeliveryDrivers() {
        this._navigate('delivery_drivers_list');
        this.state.ddDetailId = null;
        await this._reloadDeliveryDrivers();
    }

    /**
     * Refetch the drivers WITHOUT moving the manager.
     *
     * Assigning a truck can now be done from two places — the list and the
     * driver's own page. Reloading used to mean re-entering the list, which
     * threw whoever acted from the page back out of the record they had just
     * changed.
     */
    async _reloadDeliveryDrivers() {
        this.state.loading = true;
        this.state.ddError = null;
        this.state.ddAssigning = null;
        try {
            // Record rules already scope this to the manager's own warehouse;
            // the explicit domain keeps the intent readable.
            this.state.deliveryDrivers = await this.orm.searchRead(
                'recycle.delivery.driver', this._whDomain(),
                ['id', 'name', 'phone', 'email', 'national_id', 'address',
                 'birth_date', 'warehouse_id',
                 'truck_id', 'truck_plate', 'has_truck', 'is_active',
                 'is_blocked', 'blocked_reason', 'license_number',
                 'license_expiry'],
                { order: 'name' });
        } catch (e) {
            this.state.deliveryDrivers = [];
            this.state.ddError = (e && e.data && e.data.message) || this.tr('Action failed.');
        }
        this.state.loading = false;
    }

    // ─── The driver's own page ──────────────────────────────────
    // Read-only on the personal details: a manager assigns the vehicle, the
    // administrator owns the record. What the manager needs to SEE before
    // handing over a van — the licence and its expiry — has nowhere to live in
    // a table row.

    /** Keyed by id, not by the row object, so the page survives a refetch. */
    get ddDetail() {
        const id = this.state.ddDetailId;
        if (!id) return null;
        return this.state.deliveryDrivers.find((d) => d.id === id) || null;
    }

    async openDeliveryDriverDetail(driver) {
        this.state.ddDetailId = driver.id;
        this.state.ddError = null;
        this.state.ddAssigning = null;
        this._navigate('delivery_driver_detail');
        await this._loadDriverTruckHistory(driver.id);
    }

    /** Every truck this driver has held, newest first. */
    async _loadDriverTruckHistory(driverId) {
        this.state.ddHistoryLoading = true;
        this.state.ddHistory = [];
        try {
            this.state.ddHistory = await this.orm.searchRead(
                'recycle.truck.assignment.history',
                [['delivery_driver_id', '=', driverId]],
                ['truck_id', 'truck_plate', 'warehouse_id', 'assigned_at',
                 'released_at', 'release_reason', 'duration_days', 'is_current'],
                { order: 'assigned_at desc, id desc' });
        } catch (e) {
            this.state.ddError = (e && e.data && e.data.message) || this.tr('Action failed.');
        }
        this.state.ddHistoryLoading = false;
    }

    /** Refresh after an action, staying wherever the manager is. */
    async _afterDriverAction() {
        await this._reloadDeliveryDrivers();
        if (this.state.view === 'delivery_driver_detail' && this.state.ddDetailId) {
            await this._loadDriverTruckHistory(this.state.ddDetailId);
        }
    }

    /** Odoo's own image route — avoids pulling two base64 scans into state. */
    ddImageUrl(driverId, field) {
        return '/web/image/recycle.delivery.driver/' + driverId + '/' + field;
    }

    /**
     * The driver's file: their details plus every truck they have held, with
     * the dates. Printed from the DRIVER, because whoever wants it already has
     * the person in front of them.
     */
    async printDeliveryDriverFile(driver) {
        // Downloaded, not opened in a tab: the file is meant to be kept and
        // sent on, and a tab named after the route is a document the manager
        // then has to save by hand. On a phone it is a viewer with no obvious
        // way back to the driver they were reading.
        const url = '/report/pdf/recycle_warehouse.report_delivery_driver_file/'
            + driver.id;
        const safeName = String(driver.name || 'driver')
            .replace(/[\\/:*?"<>|]+/g, '-').trim() || 'driver';
        try {
            const response = await fetch(url, { credentials: 'same-origin' });
            if (!response.ok) throw new Error(String(response.status));
            const objectUrl = URL.createObjectURL(await response.blob());
            const link = document.createElement('a');
            link.href = objectUrl;
            link.download = safeName + '.pdf';
            document.body.appendChild(link);
            link.click();
            link.remove();
            setTimeout(() => URL.revokeObjectURL(objectUrl), 10_000);
        } catch (e) {
            this.notification && this.notification.add(
                this.tr('Could not generate the PDF file.'), { type: 'danger' });
        }
    }

    // Licence scans open over the page, not in a new tab — a tab holding a
    // bare image has no context and, on a phone, no clear way back.
    openImageViewer(url, caption) {
        this.state.imageViewer = { url, caption: caption || '' };
    }
    closeImageViewer() { this.state.imageViewer = null; }

    /** Why a holding period ended, in words rather than a stored code. */
    releaseReasonLabel(code) {
        const map = {
            manual: this.tr('Unassigned by an administrator or manager'),
            warehouse_change: this.tr('Truck moved to another warehouse'),
            reassigned: this.tr('Given to another driver'),
            driver_blocked: this.tr('Driver blocked'),
            driver_removed: this.tr('Driver record removed or deactivated'),
        };
        return map[code] || '—';
    }

    get filteredDeliveryDrivers() {
        const q = (this.state.ddSearch || '').trim().toLowerCase();
        const f = this.state.ddTruckFilter;
        return this.state.deliveryDrivers.filter((d) => {
            if (f === 'assigned' && !d.has_truck) return false;
            if (f === 'unassigned' && d.has_truck) return false;
            if (q) {
                const hay = [d.name, d.phone || '', d.national_id || ''].join(' ').toLowerCase();
                if (!hay.includes(q)) return false;
            }
            return true;
        });
    }

    onDeliveryDriverSearchInput(ev) { this.state.ddSearch = ev.target.value; }
    setDeliveryDriverFilter(value) { this.state.ddTruckFilter = value || ''; }

    /**
     * Open the assign panel for one driver, loading the trucks still free.
     *
     * The list is fetched at the moment of asking rather than cached with the
     * page: a truck free when the screen was drawn may have been taken since,
     * and the server re-checks anyway — but offering a stale choice invites a
     * refusal the manager cannot understand.
     */
    async startAssignDeliveryTruck(driver) {
        this.state.ddAssigning = driver;
        this.state.ddSelectedTruck = '';
        this.state.ddFreeTrucks = [];
        this.state.ddError = null;
        try {
            this.state.ddFreeTrucks = await this.orm.call(
                'recycle.delivery.driver', 'free_delivery_trucks', [false]);
        } catch (e) {
            this.state.ddError = (e && e.data && e.data.message) || this.tr('Action failed.');
        }
    }

    cancelAssignDeliveryTruck() {
        this.state.ddAssigning = null;
        this.state.ddSelectedTruck = '';
        this.state.ddFreeTrucks = [];
    }

    async confirmAssignDeliveryTruck() {
        const driver = this.state.ddAssigning;
        const truckId = parseInt(this.state.ddSelectedTruck);
        if (!driver || !truckId) {
            this.state.ddError = this.tr('Please select a delivery truck.');
            return;
        }
        try {
            await this.orm.call('recycle.delivery.driver', 'action_assign_truck',
                [driver.id, truckId]);
            this.notification && this.notification.add(
                this.tr('Driver assigned to the truck.'), { type: 'success' });
            this.cancelAssignDeliveryTruck();
            await this._afterDriverAction();
        } catch (e) {
            this.state.ddError = (e && e.data && e.data.message) || this.tr('Action failed.');
        }
    }

    async unassignDeliveryTruck(driver) {
        try {
            await this.orm.call('recycle.delivery.driver', 'action_unassign_truck',
                [driver.id]);
            this.notification && this.notification.add(
                this.tr('Truck assignment removed.'), { type: 'success' });
            await this._afterDriverAction();
        } catch (e) {
            this.state.ddError = (e && e.data && e.data.message) || this.tr('Action failed.');
        }
    }

    async toggleTruckActive(truck) {
        // Disabling REQUIRES a reason (shown to the admin) — open the modal.
        // Re-enabling is direct.
        if (truck.is_active) {
            this.state.truckDisable = truck;
            this.state.truckDisableReason = '';
            return;
        }
        await this._callToggleTruck(truck, null);
    }

    async confirmTruckDisable() {
        const truck = this.state.truckDisable;
        const reason = (this.state.truckDisableReason || '').trim();
        if (!truck || !reason) return;
        await this._callToggleTruck(truck, reason);
        this.state.truckDisable = null;
    }
    closeTruckDisable() { this.state.truckDisable = null; }

    async _callToggleTruck(truck, reason) {
        try {
            // Guarded server-side: managers may only flip trucks of their
            // own warehouse (never edit truck data).
            await this.orm.call('recycle.truck', 'action_toggle_service_state',
                [[truck.id], reason || false]);
            truck.is_active = !truck.is_active;
            truck.disable_reason = truck.is_active ? false : reason;
            this.notification && this.notification.add(
                truck.is_active ? this.tr('Truck put in service.') : this.tr('Truck taken out of service.'),
                { type: 'success' });
        } catch (e) {
            this.notification && this.notification.add(
                (e && e.data && e.data.message) || this.tr('Action failed.'), { type: 'danger' });
        }
    }

    // ─── Shift-change requests (drivers ask in the app; I decide) ──────
    async openShiftChangeRequests() {
        this._navigate('shift_change_requests');
        this.state.loading = true;
        this.state.scrError = null;
        this.state.scrSuccess = null;
        try {
            // Record rule scopes me to my warehouse; newest first (_order).
            this.state.shiftChangeRequests = await this.orm.searchRead(
                'recycle.shift.change.request', [],
                ['id', 'driver_name', 'backend_driver_id', 'state', 'reason',
                 'shift_id', 'current_shift_id', 'truck_id',
                 'rejection_reason', 'create_date'],
                { limit: 300 });
        } catch (e) { this.state.shiftChangeRequests = []; }
        this.state.loading = false;
    }

    setScrTab(tab) { this.state.scrTab = tab; }

    get filteredShiftChangeRequests() {
        const t = this.state.scrTab;
        if (!t || t === 'all') return this.state.shiftChangeRequests;
        return this.state.shiftChangeRequests.filter((r) => r.state === t);
    }

    async _runScrAction(call, successMsg) {
        this.state.scrSaving = true;
        this.state.scrError = null;
        try {
            await call();
            this.state.scrApprove = null;
            this.state.scrReject = null;
            this.state.scrSuccess = successMsg;
            const self = this;
            setTimeout(function () { self.state.scrSuccess = null; }, 4000);
            await this.openShiftChangeRequests();
        } catch (e) {
            this.state.scrError = (e && e.data && e.data.message)
                || this.tr('Action failed. Please try again.');
        } finally {
            this.state.scrSaving = false;
        }
    }

    async scrStartProcessing(req) {
        await this._runScrAction(
            () => this.orm.call('recycle.shift.change.request',
                'action_start_processing', [[req.id]]),
            this.tr('Request moved to processing.'));
    }

    async openScrApprove(req) {
        this.state.scrApprove = req;
        this.state.scrTruckId = null;
        this.state.scrError = null;
        try {
            this.state.scrTrucks = await this.orm.call(
                'recycle.driver.assignment', 'get_shift_free_trucks',
                [req.shift_id[0]]);
        } catch (e) {
            this.state.scrTrucks = [];
            this.state.scrError = (e && e.data && e.data.message)
                || this.tr('Could not load available trucks.');
        }
    }
    selectScrTruck(id) {
        this.state.scrTruckId = this.state.scrTruckId === id ? null : id;
    }
    async confirmScrApprove() {
        const req = this.state.scrApprove;
        if (!req || !this.state.scrTruckId) return;
        await this._runScrAction(
            () => this.orm.call('recycle.shift.change.request',
                'action_approve', [[req.id], this.state.scrTruckId]),
            this.tr('Request approved — the driver was notified.'));
    }

    openScrReject(req) {
        this.state.scrReject = req;
        this.state.scrRejectReason = '';
        this.state.scrError = null;
    }
    async confirmScrReject() {
        const req = this.state.scrReject;
        const reason = (this.state.scrRejectReason || '').trim();
        if (!req || !reason) return;
        await this._runScrAction(
            () => this.orm.call('recycle.shift.change.request',
                'action_reject', [[req.id], reason]),
            this.tr('Request rejected — the driver was notified.'));
    }
    closeScrModals() {
        this.state.scrApprove = null;
        this.state.scrReject = null;
        this.state.scrError = null;
    }

    // ─── Truck problems (read-only reports from my drivers) ────────────
    async openTruckProblems() {
        this._navigate('truck_problems');
        this.state.loading = true;
        try {
            const problems = await this.orm.searchRead(
                'recycle.truck.problem', [],
                ['id', 'driver_name', 'truck_id', 'reason', 'create_date'],
                { limit: 300 });
            const ids = problems.map((p) => p.id);
            const images = ids.length ? await this.orm.searchRead(
                'recycle.truck.problem.image',
                [['problem_id', 'in', ids]],
                ['id', 'problem_id', 'url']) : [];
            for (const p of problems) {
                p.images = images.filter((i) => i.problem_id[0] === p.id);
            }
            this.state.truckProblems = problems;
        } catch (e) { this.state.truckProblems = []; }
        this.state.loading = false;
    }

    // ─── Driver Attendance (pickup / dropoff — READ ONLY) ──────────────
    async openDriverAttendance() {
        this._navigate('driver_attendance');
        await this._loadDriverHandovers();
    }
    async _loadDriverHandovers() {
        this.state.loading = true;
        // Record rule scopes me to my warehouse — NO warehouse filter here, only
        // a date filter (mirrors my warehouse-staff attendance screen).
        const domain = this.state.driverAttDate
            ? [['work_date', '=', this.state.driverAttDate]] : [];
        try {
            this.state.driverHandovers = await this.orm.searchRead(
                'recycle.truck.handover', domain,
                ['id', 'driver_name', 'truck_id', 'shift_id', 'work_date',
                 'picked_up_at', 'dropped_off_at', 'dropoff_reason',
                 'late_minutes', 'state'],
                { order: 'work_date desc', limit: 300 });
        } catch (e) { this.state.driverHandovers = []; }
        // Same summary metrics as the admin driver-attendance screen.
        let present = 0, late = 0, missed = 0;
        for (const h of this.state.driverHandovers) {
            if (h.picked_up_at) present++;
            if (h.late_minutes) late++;
            if (h.state === 'missed_pickup') missed++;
        }
        this.state.driverAttStats = {
            present, late, missed, total: this.state.driverHandovers.length };
        this.state.loading = false;
    }
    async onDriverAttDateInput(ev) {
        this.state.driverAttDate = ev.target.value || '';
        await this._loadDriverHandovers();
    }

    handoverStateBadge(s) {
        return s === 'closed' ? 'o_ra_badge o_ra_badge_success'
            : s === 'missed_pickup' ? 'o_ra_badge o_ra_badge_danger'
            : 'o_ra_badge o_ra_badge_info';
    }
    handoverStateLabel(s) {
        return s === 'closed' ? this.tr('Handed Over')
            : s === 'missed_pickup' ? this.tr('Missed Pickup')
            : this.tr('Holding');
    }

    // ─── Driver detail modal + actions (block / unblock / change shift) ─
    openDriverDetail(d) {
        this.state.driverDetail = d;
        this.state.driverBlockModal = false;
        this.state.driverBlockReason = '';
        this.state.dscOpen = false;
        this.state.dscShiftId = '';
        this.state.dscTrucks = [];
        this.state.dscTruckId = null;
        this.state.driverActionError = null;
        this.state.driverActionSuccess = null;
    }
    closeDriverDetail() { this.state.driverDetail = null; }

    async _runDriverAction(call, successMsg) {
        this.state.driverActionSaving = true;
        this.state.driverActionError = null;
        try {
            await call();
            this.state.driverActionSuccess = successMsg;
            const self = this;
            setTimeout(function () { self.state.driverActionSuccess = null; }, 4000);
            this.state.driverBlockModal = false;
            this.state.dscOpen = false;
            this.state.driverDetail = null;
            await this.openDriversList();
        } catch (e) {
            this.state.driverActionError = (e && e.data && e.data.message)
                || this.tr('Action failed. Please try again.');
        } finally {
            this.state.driverActionSaving = false;
        }
    }

    openDriverBlock() {
        this.state.driverBlockModal = true;
        this.state.driverBlockReason = '';
        this.state.driverActionError = null;
    }
    async confirmDriverBlock() {
        const d = this.state.driverDetail;
        if (!d) return;
        await this._runDriverAction(
            () => this.orm.call('recycle.driver.request', 'action_block',
                [[d.id], (this.state.driverBlockReason || '').trim() || false]),
            this.tr('Driver blocked — he was signed out of the app.'));
    }
    async unblockDriver() {
        const d = this.state.driverDetail;
        if (!d) return;
        await this._runDriverAction(
            () => this.orm.call('recycle.driver.request', 'action_unblock', [[d.id]]),
            this.tr('Driver unblocked — he can sign in again.'));
    }

    openDriverShiftChange() {
        this.state.dscOpen = true;
        this.state.dscShiftId = '';
        this.state.dscTrucks = [];
        this.state.dscTruckId = null;
        this.state.driverActionError = null;
    }
    async onDscShiftChange(ev) {
        this.state.dscShiftId = ev.target.value;
        this.state.dscTruckId = null;
        this.state.dscTrucks = [];
        if (!this.state.dscShiftId) return;
        try {
            this.state.dscTrucks = await this.orm.call(
                'recycle.driver.assignment', 'get_shift_free_trucks',
                [Number(this.state.dscShiftId)]);
        } catch (e) {
            this.state.driverActionError = (e && e.data && e.data.message)
                || this.tr('Could not load available trucks.');
        }
    }
    selectDscTruck(id) {
        this.state.dscTruckId = this.state.dscTruckId === id ? null : id;
    }
    async confirmDriverShiftChange() {
        const d = this.state.driverDetail;
        if (!d || !this.state.dscShiftId || !this.state.dscTruckId) return;
        await this._runDriverAction(
            () => this.orm.call('recycle.driver.assignment',
                'action_change_driver_shift',
                [d.backend_driver_id, Number(this.state.dscShiftId),
                 Number(this.state.dscTruckId)]),
            this.tr('Driver moved to the new shift and truck.'));
    }

    // ─── Drivers of my warehouse (Trucks → Drivers) ────────────────────
    // The record rule limits reads to drivers ACCEPTED into my warehouse;
    // search by name + shift / no-shift + linked-to-truck filters happen
    // client-side over that scoped set (fleet-sized data).
    async openDriversList() {
        this._navigate('drivers_list');
        this.state.loading = true;
        this.state.driverSearch = '';
        this.state.driverShiftFilter = '';
        this.state.driverTruckFilter = '';
        try {
            const [drivers, assignments] = await Promise.all([
                this.orm.searchRead(
                    'recycle.driver.request', [['state', '=', 'accepted']],
                    ['id', 'name', 'email', 'phone', 'warehouse_id',
                     'shift_id', 'backend_driver_id', 'decided_at',
                     'is_blocked', 'blocked_reason'],
                    { order: 'decided_at desc', limit: 300 }),
                this.orm.searchRead(
                    'recycle.driver.assignment', [],
                    ['id', 'backend_driver_id', 'truck_id', 'shift_id']),
            ]);
            this.state.drivers = drivers;
            this.state.driverAssignments = assignments;
            await this._loadDriverShifts();
        } catch (e) {
            this.state.drivers = [];
            this.state.driverAssignments = [];
        }
        this.state.loading = false;
    }

    async _loadDriverShifts() {
        this.state.driverShifts = await this.orm.searchRead(
            'recycle.shift', [['shift_type', '=', 'driver']],
            ['id', 'name'], { order: 'name' });
    }

    driverTruckOf(d) {
        const row = this.state.driverAssignments.find(
            (a) => a.backend_driver_id === d.backend_driver_id);
        return row ? this.m2oName(row.truck_id) : null;
    }

    get filteredDrivers() {
        const q = (this.state.driverSearch || '').trim().toLowerCase();
        const shift = this.state.driverShiftFilter;
        const truck = this.state.driverTruckFilter;
        return this.state.drivers.filter((d) => {
            if (q && !(d.name || '').toLowerCase().includes(q)) return false;
            if (shift === 'none') { if (d.shift_id) return false; }
            else if (shift) { if (!d.shift_id || d.shift_id[0] !== Number(shift)) return false; }
            const linked = !!this.driverTruckOf(d);
            if (truck === 'linked' && !linked) return false;
            if (truck === 'unlinked' && linked) return false;
            return true;
        });
    }

    onDriverSearchInput(ev) { this.state.driverSearch = ev.target.value; }
    setDriverShiftFilter(ev) { this.state.driverShiftFilter = ev.target.value; }
    setDriverTruckFilter(ev) { this.state.driverTruckFilter = ev.target.value; }

    // ─── Assign driver to truck (my warehouse only — server enforced) ──
    async openAssignDriver() {
        this._navigate('assign_driver');
        this.state.assignShiftId = '';
        this.state.assignOptions = { trucks: [], drivers: [] };
        this.state.assignTruckId = null;
        this.state.assignDriverKey = '';
        this.state.assignError = null;
        this.state.assignSuccess = null;
        await this._loadDriverShifts();
    }

    async onAssignShiftChange(ev) {
        this.state.assignShiftId = ev.target.value;
        await this._loadAssignOptions();
    }

    async _loadAssignOptions() {
        this.state.assignTruckId = null;
        this.state.assignDriverKey = '';
        this.state.assignError = null;
        this.state.assignSuccess = null;
        if (!this.state.assignShiftId) {
            this.state.assignOptions = { trucks: [], drivers: [] };
            return;
        }
        this.state.assignLoading = true;
        try {
            this.state.assignOptions = await this.orm.call(
                'recycle.driver.assignment', 'get_assignment_options',
                [Number(this.state.assignShiftId), false]);
        } catch (e) {
            this.state.assignOptions = { trucks: [], drivers: [] };
            this.state.assignError = (e && e.data && e.data.message)
                || this.tr('Could not load assignment options.');
        } finally {
            this.state.assignLoading = false;
        }
    }

    selectAssignTruck(truckId) {
        this.state.assignTruckId =
            this.state.assignTruckId === truckId ? null : truckId;
    }

    async confirmAssignDriver() {
        if (!this.state.assignShiftId || !this.state.assignTruckId
            || !this.state.assignDriverKey) return;
        this.state.assignSaving = true;
        this.state.assignError = null;
        try {
            await this.orm.call(
                'recycle.driver.assignment', 'action_assign_driver',
                [this.state.assignDriverKey,
                 Number(this.state.assignTruckId),
                 Number(this.state.assignShiftId)]);
            // Reload first — _loadAssignOptions() clears both banners, so
            // the success message must be set AFTER it or it never shows.
            await this._loadAssignOptions();
            this.state.assignSuccess =
                this.tr('Driver assigned to the truck successfully!');
        } catch (e) {
            this.state.assignError = (e && e.data && e.data.message)
                || this.tr('Assignment failed. Please try again.');
        } finally {
            this.state.assignSaving = false;
        }
    }

    // ─── Archive (manager + admin only) ────────────────────────────────
    async archiveShipment(s) {
        try {
            await this.orm.call('recycle.shipment', 'action_archive_recycle', [[s.id]]);
            this.state.shipments = this.state.shipments.filter(x => x.id !== s.id);
            if (this.state.view === 'shipment_detail') this.goBack();
            this.notification && this.notification.add(this.tr('Shipment archived.'), { type: 'success' });
        } catch (e) {
            this.notification && this.notification.add(
                (e && e.data && e.data.message) || this.tr('Action failed.'), { type: 'danger' });
        }
    }

    async archiveOrder(o) {
        try {
            await this.orm.call('recycle.order', 'action_archive_recycle', [[o.id]]);
            this.state.orders = this.state.orders.filter(x => x.id !== o.id);
            if (this.state.view === 'order_detail') this.goBack();
            this.notification && this.notification.add(this.tr('Order archived.'), { type: 'success' });
        } catch (e) {
            this.notification && this.notification.add(
                (e && e.data && e.data.message) || this.tr('Action failed.'), { type: 'danger' });
        }
    }

    MGR_ARCHIVED_SHIPMENT_FIELDS = ['id', 'name', 'driver_name', 'state', 'received_at',
        'expected_weight', 'actual_weight'];
    MGR_ARCHIVED_ORDER_FIELDS = ['id', 'name', 'customer_name', 'state', 'create_date',
        'amount_total', 'invoice_number'];

    async openArchivedShipments() {
        this._navigate('archived_shipments');
        this.state.loading = true;
        this.state.archivedShipments = [];
        this.state.archivedShipmentsHasMore = true;
        try {
            const pager = makePager(this.orm, { model: 'recycle.shipment', fields: this.MGR_ARCHIVED_SHIPMENT_FIELDS });
            const { rows, hasMore } = await pager.fetchFirst(this._whDomain().concat([['recycle_archived', '=', true]]));
            this.state.archivedShipments = rows;
            this.state.archivedShipmentsHasMore = hasMore;
        } catch (e) { this.state.archivedShipments = []; }
        this.state.loading = false;
    }

    async loadMoreArchivedShipments() {
        if (this.state.view !== 'archived_shipments') return;
        if (!this.state.archivedShipmentsHasMore || this.state.archivedShipmentsLoadingMore || this.state.loading) return;
        this.state.archivedShipmentsLoadingMore = true;
        try {
            const lastId = this.state.archivedShipments.length
                ? this.state.archivedShipments[this.state.archivedShipments.length - 1].id : 0;
            const pager = makePager(this.orm, { model: 'recycle.shipment', fields: this.MGR_ARCHIVED_SHIPMENT_FIELDS });
            const { rows, hasMore } = await pager.fetchMore(this._whDomain().concat([['recycle_archived', '=', true]]), lastId);
            this.state.archivedShipments = this.state.archivedShipments.concat(rows);
            this.state.archivedShipmentsHasMore = hasMore;
        } catch (e) { /* silent */ }
        this.state.archivedShipmentsLoadingMore = false;
    }

    async openArchivedOrders() {
        this._navigate('archived_orders');
        this.state.loading = true;
        this.state.archivedOrders = [];
        this.state.archivedOrdersHasMore = true;
        try {
            const pager = makePager(this.orm, { model: 'recycle.order', fields: this.MGR_ARCHIVED_ORDER_FIELDS });
            const { rows, hasMore } = await pager.fetchFirst(this._whDomain().concat([['recycle_archived', '=', true]]));
            this.state.archivedOrders = rows;
            this.state.archivedOrdersHasMore = hasMore;
        } catch (e) { this.state.archivedOrders = []; }
        this.state.loading = false;
    }

    async loadMoreArchivedOrders() {
        if (this.state.view !== 'archived_orders') return;
        if (!this.state.archivedOrdersHasMore || this.state.archivedOrdersLoadingMore || this.state.loading) return;
        this.state.archivedOrdersLoadingMore = true;
        try {
            const lastId = this.state.archivedOrders.length
                ? this.state.archivedOrders[this.state.archivedOrders.length - 1].id : 0;
            const pager = makePager(this.orm, { model: 'recycle.order', fields: this.MGR_ARCHIVED_ORDER_FIELDS });
            const { rows, hasMore } = await pager.fetchMore(this._whDomain().concat([['recycle_archived', '=', true]]), lastId);
            this.state.archivedOrders = this.state.archivedOrders.concat(rows);
            this.state.archivedOrdersHasMore = hasMore;
        } catch (e) { /* silent */ }
        this.state.archivedOrdersLoadingMore = false;
    }

    async unarchiveShipment(s) {
        try {
            await this.orm.call('recycle.shipment', 'action_unarchive_recycle', [[s.id]]);
            this.state.archivedShipments = this.state.archivedShipments.filter(x => x.id !== s.id);
            this.notification && this.notification.add(this.tr('Shipment restored.'), { type: 'success' });
        } catch (e) {}
    }

    async unarchiveOrder(o) {
        try {
            await this.orm.call('recycle.order', 'action_unarchive_recycle', [[o.id]]);
            this.state.archivedOrders = this.state.archivedOrders.filter(x => x.id !== o.id);
            this.notification && this.notification.add(this.tr('Order restored.'), { type: 'success' });
        } catch (e) {}
    }

    // ─── PDF reports ────────────────────────────────────────────────────
    async printOrderReport(orderId) {
        if (!this.actionService) return;
        try {
            await this.actionService.doAction(
                'recycle_warehouse.action_report_order_invoice',
                { additionalContext: { active_id: orderId, active_ids: [orderId], active_model: 'recycle.order' } });
        } catch (e) {}
    }

    async printShipmentReport(shipmentId) {
        if (!this.actionService) return;
        try {
            await this.actionService.doAction(
                'recycle_warehouse.action_report_shipment',
                { additionalContext: { active_id: shipmentId, active_ids: [shipmentId], active_model: 'recycle.shipment' } });
        } catch (e) {}
    }

    openManagerAction(actionRef) {
        if (!this.actionService) return;
        try { this.actionService.doAction(actionRef); } catch(e) {}
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

registry.category("actions").add("recycle_manager_dashboard", RecycleManagerDashboard);
