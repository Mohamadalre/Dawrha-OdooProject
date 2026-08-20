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

export class RecycleAdminDashboard extends Component {
    static template = "recycle_warehouse.RecycleAdminDashboard";
    static props = ["*"];

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.userName = user.name || "Admin";
        this.userEmail = session.partner_id ? session.email || '' : '';
        this._navHistory = [];
    this.state = useState({
        openSection: null,
        view: "dashboard",
        // Sidebar entry painted green — the last clicked nav target; it only
        // moves when another nav entry is clicked (the user's "stays colored
        // until I pick something else" rule).
        activeNavGo: 'goDashboard',
        loading: false,
        dashboardLoading: true,
        _loadingStats: false,
        // Unified theme: prefer the shared website key ('dw-theme'), falling
        // back to the legacy backend key so existing preferences carry over.
        darkMode: (localStorage.getItem('dw-theme')
                   || (localStorage.getItem('recycle_wms_dark') === '1' ? 'dark' : 'light')) === 'dark',
        // Stats
        stats: {
            warehouses: 0, employees: 0, shipments: 0, orders: 0, jobs: 0,
            t_warehouses: '+0%', t_warehouses_up: true,
            t_employees: '+0%', t_employees_up: true,
            t_shipments: '+0%', t_shipments_up: true,
            t_orders: '+0%', t_orders_up: true,
            t_jobs: '+0%', t_jobs_up: true,
        },
        // Warehouses
        warehouses: [], selectedWarehouse: null,
        // Closed sites live on their own screen: they keep their stock and
        // history, so they are not gone — only not taking new work.
        closedWarehouses: [], warehouseSearch: '',
        warehouseScope: null,   // set when a list is opened scoped to a warehouse
        warehouseForm: { name: '', code: '', province_id: '', latitude: '', longitude: '', address: '' },
        warehouseZoneRows: [],
        warehouseError: null, warehouseSuccess: null, warehouseSaving: false,
        // Loaded from recycle.province — the governorate list is authored in
        // the backend and mirrored here, never hard-coded in the client.
        warehouseGovernorates: [],
        warehouseZoneTypes: [
            ['receiving', 'Receiving'], ['sorting', 'Sorting'],
            ['storage', 'Storage'], ['output', 'Output'],
        ],
        // Trucks (fleet — authored here, mirrored live to the NestJS backend)
        trucks: [],
        truckSearch: '', truckWHFilter: '', truckStatusFilter: '',
        selectedTruck: null, truckEditMode: false,
        // `truck_type` is part of creating a truck, not an afterthought: the
        // fleet does two unrelated jobs, and which one this vehicle does
        // decides who may drive it. A truck saved without the answer would
        // silently become a collection truck.
        truckForm: { name: '', plate_number: '', model: '', year: '',
                     max_payload_kg: '', warehouse_id: '', truck_type: 'collection',
                     is_active: true, notes: '' },
        truckTypeFilter: '',
        // ── Delivery drivers: recruited here, unlike collectors ──────────
        deliveryDrivers: [], ddSearch: '', ddWHFilter: '', ddTruckFilter: '',
        ddLoading: false, ddError: null, ddSuccess: null,
        selectedDeliveryDriver: null, ddEditMode: false,
        ddForm: { name: '', phone: '', email: '', national_id: '', address: '',
                  birth_date: '', license_number: '', license_expiry: '',
                  license_image_front: null, license_image_back: null,
                  warehouse_id: '', truck_id: '', is_active: true, notes: '' },
        ddSaving: false,
        ddFreeTrucks: [], ddAssigning: null, ddSelectedTruck: '',
        // A dropdown hides the one thing that distinguishes two trucks — the
        // plate — behind a tap, and on a phone it opens a native list with no
        // room for it. The picker is a screen of cards instead.
        ddTruckPickerOpen: false, ddTruckPickerSearch: '',
        ddBlocking: null, ddBlockReason: '',
        // The driver's own page. A row of six buttons squeezed into a table
        // cell is unreadable on a phone and gives no room for the things worth
        // seeing about a person — their licence scans, their truck history. So
        // the list offers ONE button and everything else lives here.
        ddDetailId: null, ddHistory: [], ddHistoryLoading: false,
        // Licence scans open over the page rather than in a new tab.
        imageViewer: null,
        truckSaving: false, truckError: null, truckSuccess: null,
        // Driver requests (pushed live from the NestJS backend)
        driverRequests: [], driverRequestTab: 'pending',
        driverRequestsLoading: false,
        selectedDriverRequest: null,
        driverAcceptModal: false, driverAcceptWH: '',
        driverRejectModal: false, driverRejectReason: '',
        driverImgReject: null, driverImgRejectReason: '',
        // Asking for a document is a second, separate act — its own modal, so
        // the reviewer cannot fire off a message to the driver by reflex while
        // marking documents.
        driverImgRequest: null, driverImgRequestReason: '',
        driverActionSaving: false, driverActionError: null, driverActionSuccess: null,
        drivers: [],   // accepted drivers (Trucks -> Drivers screen)
        driverHandovers: [],   // driver attendance (pickup/dropoff — read-only)
        driverSearch: '', driverShiftFilter: '', driverTruckFilter: '',
        driverWHFilter: '',
        // Driver detail modal + actions (block / unblock / relocate / PDF)
        driverDetail: null,
        driverBlockModal: false, driverBlockReason: '',
        driverMoveWH: '', driverMoveOpen: false,
        // Take-out-of-service reason modal (server requires a reason)
        truckDisable: null, truckDisableReason: '',
        driverShifts: [],        // driver-type shifts (drivers filters + assignment)
        driverAssignments: [],   // live truck reservations (joined client-side)
        // Assign driver to truck
        assignShiftId: '', assignWHFilter: '',
        assignOptions: { trucks: [], drivers: [] },
        assignTruckId: null, assignDriverKey: '',
        assignLoading: false, assignSaving: false,
        assignError: null, assignSuccess: null,
        // Shipments
        shipments: [], selectedShipment: null, selectedShipmentLines: [],
        selectedShipmentExpectedLines: [],
        shipmentFilter: '', shipmentWHFilter: null, shipmentStateFilter: '',
        shipmentsHasMore: true, shipmentsLoadingMore: false,
        archivedShipments: [], archivedShipmentsHasMore: true, archivedShipmentsLoadingMore: false,
        // Damage, per shipment. `damageOpenId` is the one row expanded to its
        // lines — a list of totals answers "how much", and the administrator's
        // next question is always "of what, and who said so".
        damageRows: [], damageOpenId: null, damageSearch: '',
        damageWHFilter: null, damageFrom: '', damageTo: '',
        // Orders
        orders: [], selectedOrder: null, selectedOrderLines: [],
        orderFilter: '', orderWHFilter: null, orderStateFilter: '',
        // Reassigning one part of a split order to another warehouse (admin only).
        reassignCandidates: [], reassignWarehouseId: '',
        reassignError: null, reassignSuccess: null, reassignBusy: false,
        ordersHasMore: true, ordersLoadingMore: false,
        archivedOrders: [], archivedOrdersHasMore: true, archivedOrdersLoadingMore: false,
        // Warehouse filter context (from warehouse detail nav)
        filterWarehouseId: null, filterWarehouseName: null,
        // Jobs & HR
        jobs: [], selectedJob: null,
        jobEditMode: false,
        jobForm: { name: '', no_of_recruitment: 1, recycle_job_type: 'employee', recycle_publish: false, recycle_description: '' },
        jobSaving: false, jobError: null,
        // Applicants
        applicants: [], selectedApplicant: null,
        applicantsHasMore: true, applicantsLoadingMore: false,
        applicantAttachments: [], applicantDetailLoading: false,
        applicantStageLog: [],
        applicantActionError: null, applicantActionSuccess: null,
        applicantInterviewForm: { when: '', location: '', notes: '' },
        applicantAccountForm: { warehouse_id: null, role: '' },
        applicantSaving: false,
        recruitmentStages: [],       // hr.recruitment.stage list (ordered)
        // Stage management + talent pool
        stagesList: [], stageForm: { name: '', sequence: 10, is_interview: false, description: '' }, stageSaving: false,
        stageError: null, stageSuccess: null,
        talentPool: [], talentPoolLoading: false, talentPoolSearch: '',
        talentPoolHasMore: true, talentPoolLoadingMore: false,
        rejectDialog: null, rejectReason: '',   // reject-reason mini dialog
        applicantJobFilter: null, applicantJobName: null,
        // Accepted / Rejected Applicants
        acceptedApplicants: [], acceptedFilter: '',
        acceptedApplicantsHasMore: true, acceptedApplicantsLoadingMore: false,
        rejectedApplicants: [], rejectedFilter: '',
        rejectedApplicantsHasMore: true, rejectedApplicantsLoadingMore: false,
        acceptedRejectedTab: 'accepted',
        // Deleted Account Applicants
        deletedApplicants: [],
        deletedApplicantsHasMore: true, deletedApplicantsLoadingMore: false,
        // Employees
        employees: [], employeeWHFilter: null,
        employeeTab: 'active',
        // Adding one. The admin can appoint a warehouse MANAGER here, which
        // the manager's own version of this screen deliberately cannot.
        empCreateForm: {
            name: '', email: '', phone: '', national_id: '',
            role: 'input', warehouse_id: '',
        },
        empCreateSaving: false, empCreateError: null, empCreateSuccess: null,
        employeeSearch: '', employeeRoleFilter: '', employeeStatusFilter: '',
        deletedEmployees: [],
        deletedEmployeesHasMore: true, deletedEmployeesLoadingMore: false,
        deletedEmployeeSearch: '', archivedWHFilter: null,
        selectedEmployee: null,
        selectedDeletedEmployee: null,
        employeeEditMode: false,
        employeeForm: { name: '', login: '', email: '', recycle_role: '', recycle_warehouse_id: null, shift_id: null },
        employeeSaving: false,
        employeeError: null,
        employeeSuccess: null,
        // Unassigned employees
        unassignedEmployees: [],
        unassignedLoading: false,
        selectedUnassigned: null,
        warehousesWithoutManager: [],
        unassignedWarehouseForm: { warehouse_id: null },
        unassignedRoleForm: { role_type: '' },
        unassignedSaving: false,
        unassignedError: null,
        unassignedSuccess: null,
        // Employee history
        employeeHistory: [],
        employeeHistoryLoading: false,
        // Website Users management (portal accounts)
        websiteUsers: [], websiteUserSearch: '',
        websiteUsersHasMore: true, websiteUsersLoadingMore: false,
        selectedWebsiteUser: null, websiteUsersLoading: false,
        // Zones
        zones: [], selectedZone: null,
        zoneCreateMode: false,
        zoneForm: { name: '', zone_type: 'storage', warehouse_id: null },
        // Manage-warehouse panel (zones / manager / info)
        whZones: [], whAvailableManagers: [], whManagerPick: '',
        whEditForm: { name: '', code: '' },
        zoneCreateModal: false, whManagerModal: false, whEditModal: false,
        whAdminSaving: false, whAdminError: null, whAdminSuccess: null,
        zoneSaving: false, zoneError: null,
        // Attendance
        attendance: [], attendanceWHFilter: null,
        attendanceDate: '',
        attendanceStats: { present: 0, late: 0, early: 0 },
        // Driver attendance (handovers) — same warehouse + date filters as staff.
        driverAttWHFilter: null, driverAttDate: '',
        driverAttStats: { present: 0, late: 0, missed: 0, total: 0 },
        // Inventory (Stock / Products / Product Categories)
        stock: [], stockWHFilter: null, stockZones: [], stockZoneFilter: '',
        stockCondFilter: '',
        products: [], productsFilter: '',
        productCategories: [],
        // Shifts list
        shifts: [],
        selectedShift: null,
        shiftEditMode: false,
        // Shift create form
        shiftForm: { name: '', start_time: 8.0, end_time: 17.0, tolerance: 15, shift_type: 'warehouse', is_global: false, warehouse_ids: [] },
        shiftWasGlobal: false,       // original scope of the shift being edited
        shiftSaving: false, shiftError: null, shiftSuccess: null,
        shifts: [],
        shiftWarnType: null,         // 'long' | 'unusual' — which confirm modal
        shiftConfirmed: false,       // user pressed "continue" on the warning
        shiftDeleteWarn: null,       // { name, employees:[] } when delete blocked
        // Vertical sidebar
        sidebarOpen: false,          // mobile drawer
        navSection: null,            // which accordion section is expanded
        navSubItem: null,            // which item's nested sub-menu is expanded
        // Dashboard recent activity
        recentShipments: [],
        recentOrders: [],
        // Profile
        userProfile: {
            name: (user && user.name) || 'Administrator',
            email: (session && session.partner_id && session.email) || '',
            login: (user && user.login) || '',
            phone: '',
            role: 'admin',
            national_id: '',
            street: '',
            city: '',
            country: '',
        },
        profileLoading: false,
        profileEditMode: false,
        profileForm: { name: 'Administrator', email: 'admin', login: 'admin', phone: '0982078369', role: 'Administrator' },
        profileSaving: false,
        profileSaveSuccess: null,
        profileSaveError: null,
        // Settings
        settingsSaved: false,
        sortThresholds: { t1: 3, t2: 15 },
        sortThresholdsSaved: false,
        // Notifications
        notifications: [],
        notifLoading: false,
        notifUnreadCount: 0,
        // Filter period
        filterPeriod: 'month',
        // Top insights
        insights: { mostActive: '', mostActiveValue: 0, mostActiveIcon: '', growthPct: 0, growthUp: true },
        // Language (normalise old Odoo codes like 'ar_001' → 'ar')
        lang: (localStorage.getItem('recycle_wms_lang') || 'en').replace(/^ar_.*$/, 'ar'),
        // Nav user email (loaded on start)
        navUserEmail: '',
        // Product create form (admin)
        productForm: { name: '', category_id: '', price_factory: 0, price_free_facility: 0, weight: 0, uom_id: '' },
        productError: null, productSaving: false, productSuccess: null,
        uomList: [],
        // Pictures attached to a material SUGGESTION (base64, uploaded as
        // ir.attachment on save). Not the same as the material-create form above.
        productImages: [],
        // "View Prices" sheet — prices per buyer tier / material condition,
        // mirrored from the backend (recycle.product.condition.price).
        pricesModal: false, pricesProduct: null, pricesLoading: false,
        pricesError: null, priceRows: { factory: [], free_facility: [] },
        // Add Administrator form (Settings)
        adminForm: { name: '', email: '' },
        adminFormError: null, adminFormSaving: false, adminFormSuccess: null,
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

        // The in-page message/confirm dialog every screen shares. Adds
        // `state.dialog` and the handlers its template binds to.
        useMessageDialog(this);

        // Branded loading screen, but only when a load actually drags.
        this._clearSlowLoad = useSlowLoad(this);

        this.donutChart = null;
        this.barChart = null;
        this.donutCanvasRef = useRef('donutCanvas');
        this.barCanvasRef = useRef('barCanvas');
        // Map picker on the "Add Warehouse" screen — click to set the coordinates.
        this.whCreateMapRef = useRef('whCreateMap');
        this._whCreateMap = null;
        this._whCreateMarker = null;

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
                if (_p.role && _p.role !== 'admin') {
                    window.location.replace('/recycle/open-dashboard');
                    return;
                }
            } catch (_e) {}
            try {
                await loadBundle("web.chartjs_lib");
            } catch (e) {
                if (typeof console !== 'undefined' && console.error) console.error("chartjs bundle failed", e);
            }
            var self = this;
            var loadTimeout = setTimeout(function() {
                self.state.dashboardLoading = false;
                self.state._loadingStats = false;
            }, 15000);
            try {
                await this._loadStats();
            } catch (e) {
                this.state.dashboardLoading = false;
                this.state._loadingStats = false;
            }
            clearTimeout(loadTimeout);
            // Load current user email for nav
            try {
                const u = await this.orm.searchRead('res.users', [['id','=',user.userId]], ['email','login'], {limit:1});
                this.state.navUserEmail = (u[0] && (u[0].email || u[0].login)) || '';
            } catch(e) { this.state.navUserEmail = ''; }
            // Load unread notification count for bell badge
            await this._loadNotifCount();
            try {
                const r = await this._rpc('/api/recycle/my-profile', {});
                if (r && !r.error) {
                    this.state.userProfile = {
                        name: r.name || '',
                        email: r.email || '',
                        login: r.login || '',
                        phone: r.phone || '',
                        role: r.role || 'admin',
                        national_id: r.national_id || '',
                        street: r.street || '',
                        city: r.city || '',
                        country: r.country || '',
                    };
                }
            } catch(e) {
                try {
                    const recs = await this.orm.searchRead(
                        "res.users", [["id", "=", user.userId]],
                        ["id", "name", "email", "login", "phone",
                         "recycle_role", "recycle_national_id"]);
                    if (recs.length) {
                        const r2 = recs[0];
                        this.state.userProfile = {
                            name: r2.name || '',
                            email: r2.email || r2.login || '',
                            login: r2.login || '',
                            phone: r2.phone || '',
                            role: r2.recycle_role || 'admin',
                            national_id: r2.recycle_national_id || '',
                            street: '',
                            city: '',
                            country: '',
                        };
                    }
                } catch(e2) {}
            }
            const ctx = this.props.action?.context;
            const iv = ctx && ctx.initial_view;
            if (iv && iv !== "dashboard") {
                if      (iv === "shipments_list")   await this.openShipments();
                else if (iv === "orders_list")       await this.openOrders();
                else if (iv === "warehouse_hub")     await this.openWarehouses();
                else if (iv === "trucks_list")       await this.openTrucks();
                else if (iv === "driver_requests")   await this.openDriverRequests();
                else if (iv === "drivers_list")      await this.openDriversList();
                else if (iv === "jobs_hr")           this.openJobsHR();
                else if (iv === "employees_list")    await this.openEmployeesList();
                else if (iv === "users_list")        await this.openUsersList();
                else if (iv === "talent_pool")       await this.openTalentPool();
                else if (iv === "stages_list")       await this.openStagesList();
                else if (iv === "accepted_applicants")   await this.openAcceptedApplicants();
                else if (iv === "applicants_list")       await this.openApplicantsList();
                else if (iv === "shifts_hub")            this.openShiftsHub();
                else if (iv === "shift_create")          this.openCreateShift();
                else if (iv === "shifts_list")           await this.openShiftsList();
                else if (iv === "zones_list")             await this.openZonesList();
                else if (iv === "attendance_list")       await this.openAttendance();
                else if (iv === "stock_list")            await this.openStockList();
                else if (iv === "products_list")         await this.openProductsList();
                else if (iv === "product_categories_list") await this.openProductCategoriesList();
                else if (iv === "employee_assignment")     await this.openEmployeeAssignment(ctx.employee_id);
        }
        });
        onMounted(() => {
            this._syncCharts();
            this._startPolling();
            // Hide Odoo's old horizontal navbar (keep only the apps launcher)
            // while the admin dashboard (with its own vertical sidebar) is on
            // screen, and unify the theme with the navbar + website.
            setDashboardPage(true);
            this._applyTheme();
            // Scroll-to-load-more for every long-lived list (no page-number
            // buttons anywhere — the next batch of older rows loads itself
            // as the admin nears the bottom of the page).
            this._detachScroll = attachInfiniteScroll(() => this.state.view, {
                shipments_list: () => this.loadMoreShipments(),
                orders_list: () => this.loadMoreOrders(),
                applicants_list: () => this.loadMoreApplicants(),
                talent_pool: () => this.loadMoreTalentPool(),
                users_list: () => this.loadMoreUsers(),
                employees_list: () => this.loadMoreDeletedEmployees(),
                accepted_applicants: () => this.loadMoreAcceptedApplicants(),
                rejected_applicants: () => this.loadMoreRejectedApplicants(),
                deleted_applicants: () => this.loadMoreDeletedApplicants(),
                archived_shipments: () => this.loadMoreArchivedShipments(),
                archived_orders: () => this.loadMoreArchivedOrders(),
            });
        });
        // Re-create the charts whenever their canvases re-enter the DOM
        // (the skeleton t-if unmounts them on every period change).
        onPatched(() => this._syncCharts());
        onWillDestroy(() => {
            this._stopPolling();
            unsetDashboardPage(true);
            if (this._detachScroll) this._detachScroll();
            clearTimeout(this._shipmentSearchTimer);
            // The slow-load timer would otherwise fire on a destroyed
            // component and set state nobody is rendering.
            if (this._clearSlowLoad) this._clearSlowLoad();
            clearTimeout(this._orderSearchTimer);
        });
    }

        // ─── Translation (reactive — reads state.lang so OWL re-renders on switch) ─
    tr(key) {
        // Accessing this.state.lang here makes OWL track it as a reactive dependency,
        // so any template that calls tr() will automatically re-render on language change.
        const lang = this.state.lang === 'ar' ? 'ar' : 'en';
        // Sync localStorage so the shared _tr() function reads the right value
        if (localStorage.getItem('recycle_wms_lang') !== lang) {
            localStorage.setItem('recycle_wms_lang', lang);
        }
        return _tr(key);
    }

    govLabel(code) {
        return govLabel(code, (s) => this.tr(s));
    }

    // Running total as of the end of each of the last 7 days (today first,
    // 6 days ago last), used to draw the sparkline as a real trend curve
    // instead of a straight line between two numbers.
    async _last7DaysCumulative(model, domain) {
        const now = new Date();
        const days = [];
        for (let i = 6; i >= 0; i--) {
            const d = new Date(now);
            d.setDate(d.getDate() - i);
            days.push(d.toISOString().slice(0, 10) + ' 23:59:59');
        }
        try {
            const counts = await Promise.all(
                days.map(cutoff => this.orm.searchCount(model, domain.concat([["create_date", "<=", cutoff]])))
            );
            return counts;
        } catch (e) {
            return [0, 0, 0, 0, 0, 0, 0];
        }
    }

    // ─── Stats ────────────────────────────────────────────
    async _loadStats(period) {
        if (this.state._loadingStats) {
            this.state._pendingPeriod = period;
            return;
        }
        this.state._loadingStats = true;
        this.state._pendingPeriod = null;
        period = period || 'month';
        try {
            const now = new Date();
            // Odoo stores `create_date` in UTC and reads a naive domain string
            // as UTC. So each boundary is built as a LOCAL calendar start, then
            // expressed as the UTC instant that matches it. The old code mixed
            // the two — "today 00:00:00" was a local date string compared as UTC
            // while "yesterday" went through toISOString() — so the window was
            // off by the timezone offset and could pull in or drop a whole day,
            // which is why "today" often looked identical to the month.
            const utc = (dt) => dt.toISOString().slice(0, 19).replace('T', ' ');
            const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
            const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
            const dow = now.getDay();
            const monOffset = dow === 0 ? -6 : 1 - dow;
            const startOfWeek = new Date(now.getFullYear(), now.getMonth(), now.getDate() + monOffset);

            var curDomain = [], prevDomain = [];
            if (period === 'today') {
                const startYesterday = new Date(startOfToday.getTime() - 86400000);
                curDomain = [["create_date", ">=", utc(startOfToday)]];
                prevDomain = [["create_date", ">=", utc(startYesterday)], ["create_date", "<", utc(startOfToday)]];
            } else if (period === 'week') {
                const prevWeekStart = new Date(startOfWeek.getTime() - 7*86400000);
                curDomain = [["create_date", ">=", utc(startOfWeek)]];
                prevDomain = [["create_date", ">=", utc(prevWeekStart)], ["create_date", "<", utc(startOfWeek)]];
            } else {
                const startPrevMonth = new Date(now.getFullYear(), now.getMonth()-1, 1);
                curDomain = [["create_date", ">=", utc(startOfMonth)]];
                prevDomain = [["create_date", ">=", utc(startPrevMonth)], ["create_date", "<", utc(startOfMonth)]];
            }

            const safe = (p, defaultVal) => p.then(v => v, () => defaultVal);
            const allResults = await Promise.all([
                safe(this.orm.searchCount("recycle.warehouse", curDomain), 0),
                safe(this.orm.searchCount("res.users", [["recycle_role", "!=", false]].concat(curDomain)), 0),
                safe(this.orm.searchCount("recycle.shipment", curDomain), 0),
                safe(this.orm.searchCount("recycle.order", curDomain), 0),
                safe(this.orm.searchCount("hr.job", curDomain), 0),
                safe(this.orm.searchCount("recycle.warehouse", prevDomain), 0),
                safe(this.orm.searchCount("res.users", [["recycle_role", "!=", false]].concat(prevDomain)), 0),
                safe(this.orm.searchCount("recycle.shipment", prevDomain), 0),
                safe(this.orm.searchCount("recycle.order", prevDomain), 0),
                safe(this.orm.searchCount("hr.job", prevDomain), 0),
                safe(this.orm.searchRead("recycle.shipment", [], ["id","name","state","received_at","receiver_user_id"], { limit: 3, order: "id desc" }), []),
                safe(this.orm.searchRead("recycle.order", [], ["id","invoice_number","state","create_date","source"], { limit: 3, order: "id desc" }), []),
                // Warehouses/employees/jobs are near-static inventory, not
                // daily activity — the headline number on their KPI card
                // must be the real TOTAL right now, not "created within
                // this period" (which is ~0 most days and looks broken).
                // The period filter still drives their trend %/sparkline
                // above (created-this-period vs created-last-period).
                safe(this.orm.searchCount("recycle.warehouse", []), 0),
                safe(this.orm.searchCount("res.users", [["recycle_role", "!=", false]]), 0),
                safe(this.orm.searchCount("hr.job", []), 0),
                // Real 7-point history (running total as of each of the
                // last 7 days) driving the sparkline shape — a genuine
                // trend curve, not a straight line between two numbers.
                this._last7DaysCumulative("recycle.warehouse", []),
                this._last7DaysCumulative("res.users", [["recycle_role", "!=", false]]),
                this._last7DaysCumulative("recycle.shipment", []),
                this._last7DaysCumulative("recycle.order", []),
                this._last7DaysCumulative("hr.job", []),
            ]);
            const [wh, emp, sh, ord, jobs,
                   whPrev, empPrev, shPrev, ordPrev, jobsPrev,
                   recentSh, recentOrd,
                   whTotal, empTotal, jobsTotal,
                   whHistory, empHistory, shHistory, ordHistory, jobsHistory] = allResults;

            const pct = (cur, prev) => {
                if (prev === 0) return cur > 0 ? '+100%' : '+0%';
                const diff = ((cur - prev) / prev * 100);
                const sign = diff >= 0 ? '+' : '';
                return `${sign}${Math.round(diff)}%`;
            };
            const up = (cur, prev) => cur >= prev;

            this.state.stats = {
                warehouses: whTotal, employees: empTotal, shipments: sh, orders: ord, jobs: jobsTotal,
                // How many of each were ADDED within the selected period — the
                // curDomain counts, surfaced as their own number on every card
                // (the headline is the running TOTAL for the near-static ones, so
                // "added this period" needs saying explicitly rather than being
                // hidden inside the trend %).
                added_warehouses: wh, added_employees: emp, added_shipments: sh,
                added_orders: ord, added_jobs: jobs,
                t_warehouses: pct(wh, whPrev), t_warehouses_up: up(wh, whPrev),
                t_employees: pct(emp, empPrev), t_employees_up: up(emp, empPrev),
                t_shipments: pct(sh, shPrev), t_shipments_up: up(sh, shPrev),
                t_orders: pct(ord, ordPrev), t_orders_up: up(ord, ordPrev),
                t_jobs: pct(jobs, jobsPrev), t_jobs_up: up(jobs, jobsPrev),
                // Real 7-day running-total history driving the sparkline
                // shape in each card (see _sparkPoints) — replaces the old
                // hardcoded decorative squiggle with an honest trend curve.
                spark_warehouses: whHistory,
                spark_employees: empHistory,
                spark_shipments: shHistory,
                spark_orders: ordHistory,
                spark_jobs: jobsHistory,
            };
            this.state.recentShipments = recentSh;
            this.state.recentOrders = recentOrd;

            const items = [
                { label: 'Warehouses', value: wh, icon: '🏭' },
                { label: 'Employees', value: emp, icon: '👥' },
                { label: 'Shipments', value: sh, icon: '📦' },
                { label: 'Orders', value: ord, icon: '📋' },
                { label: 'Jobs', value: jobs, icon: '💼' },
            ];
            var mostActive = items.reduce(function(best, item) { return item.value > best.value ? item : best; }, items[0]);
            var totalCur = wh + emp + sh + ord + jobs;
            var totalPrev = whPrev + empPrev + shPrev + ordPrev + jobsPrev;
            var growthPct = totalPrev > 0 ? Math.round(((totalCur - totalPrev) / totalPrev) * 100) : (totalCur > 0 ? 100 : 0);
            this.state.insights = {
                mostActive: mostActive.label,
                mostActiveValue: mostActive.value,
                mostActiveIcon: mostActive.icon,
                growthPct: growthPct,
                growthUp: growthPct >= 0,
            };

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

    // ─── Filter Period ────────────────────────────────────
    setFilterPeriod(period) {
        // Already on this period and nothing running → nothing to do.
        if (period === this.state.filterPeriod && !this.state._loadingStats) return;
        // Do NOT bail while a load is in flight. The dashboard polls every 5s,
        // so at any moment there is a good chance `_loadingStats` is true — and
        // the old `|| this.state._loadingStats` guard silently DROPPED the
        // click, so the numbers "kept showing the same values" no matter which
        // period was tapped. `_loadStats` already queues a period given while
        // busy (via `_pendingPeriod`) and runs it the moment the current load
        // finishes, so handing the click straight to it makes every tap land.
        this.state.filterPeriod = period; // reflect the choice on the buttons at once
        this.state.dashboardLoading = true;
        this._loadStats(period);
    }

    // ─── Live auto-refresh (every 5s, only for the currently-open,
    // read-only list/overview screen — never while the tab is hidden and
    // never for detail/edit/process screens, so an in-progress form is
    // never yanked out from under the user) ──────────────────────────
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
            } else if (this.state.view === 'employees_list' && !this._pollingEmployees) {
                this._pollRefreshEmployees();
            } else if (this.state.view === 'driver_requests' && !this.state.driverRequestsLoading) {
                this._refetchDriverRequests().catch(() => {});
            }
            this._loadNotifCount();
        }, 5000);
    }
    _stopPolling() {
        if (this._pollInterval) { clearInterval(this._pollInterval); this._pollInterval = null; }
    }
    /**
     * Refresh the employees list WITHOUT tearing the screen down.
     *
     * The poll used to call `openEmployeesList()` — the full page-open
     * routine. That sets `state.loading = true`, and the template answers it
     * by replacing the whole table with "Loading employees…" and hiding the
     * mobile cards outright. So every five seconds the list vanished, a
     * spinner appeared, and the rows came back: on a slow connection that is
     * near-constant flicker, and it threw away the scroll position each time.
     * It also re-ran `_navigate`, which is not a no-op.
     *
     * This does what the shipments and orders polls already do: fetch quietly,
     * assign, and touch nothing the user can see moving. `loading` is left
     * alone deliberately — it means "the user asked for this screen and it is
     * not ready", which is not true of a background tick.
     *
     * Only the ACTIVE tab is refreshed. The deleted tab has its own search box
     * and pagination, and silently re-running that query would reset both
     * under whoever was typing in it.
     */
    async _pollRefreshEmployees() {
        if (this.state.employeeTab !== 'active') return;
        this._pollingEmployees = true;
        try {
            const rows = await this.orm.searchRead(
                "res.users",
                [["recycle_role", "!=", false], ["recycle_deleted", "=", false]],
                ["id", "name", "login", "email", "phone", "active",
                 "recycle_role", "recycle_warehouse_id", "shift_id"],
                { order: "name asc", context: { active_test: false } }
            );
            this.state.employees = rows.map(e => this._shapeEmployeeRow(e));
        } catch (e) {
            // A dropped tick is invisible and self-correcting — the next one
            // succeeds. Surfacing it would put an error banner on a screen the
            // admin never asked to reload.
        }
        this._pollingEmployees = false;
    }

    /** One employee row, as every employee screen wants to read it. */
    _shapeEmployeeRow(e) {
        const s = e.shift_id;
        return {
            ...e,
            role: e.recycle_role || '',
            shift: Array.isArray(s) ? s[1] : '',
            shift_id: Array.isArray(s) ? s[0] : (typeof s === 'number' ? s : ''),
        };
    }

    async _pollRefreshShipments() {
        // If the admin has scrolled down and loaded extra pages, a silent
        // background refresh must never yank those back out from under them
        // — only auto-refresh while still on the first page.
        if (this.state.shipments.length > this.SHIPMENTS_PAGE_SIZE) return;
        this._pollingShipments = true;
        try {
            this.state.shipments = await this.orm.searchRead(
                "recycle.shipment", this._shipmentDomain(),
                ["id", "name", "warehouse_id", "driver_name", "priority",
                 "expected_weight", "actual_weight", "weight_diff_pct",
                 "state", "received_at", "receiver_user_id",
                 "sorted_at", "sorter_user_id",
                 "stored_at", "stored_by",
                 "total_good_qty", "total_damaged_qty", "damage_pct"],
                { order: "id desc", limit: this.SHIPMENTS_PAGE_SIZE }
            );
            this.state.shipmentsHasMore = this.state.shipments.length === this.SHIPMENTS_PAGE_SIZE;
        } catch (e) { /* a silent background refresh must never surface an error */ }
        this._pollingShipments = false;
    }
    async _pollRefreshOrders() {
        if (this.state.orders.length > this.ORDERS_PAGE_SIZE) return;
        this._pollingOrders = true;
        try {
            this.state.orders = await this.orm.searchRead(
                "recycle.order", this._orderDomain(),
                ["id", "name", "customer_name", "owner_name", "customer_email",
                 "warehouse_id", "state", "amount_total", "total_weight",
                 "invoice_number", "source", "output_user_id",
                 "is_split_part", "part_count", "part_sequence",
                 "manager_approval", "backend_order_id"],
                { order: "id desc", limit: this.ORDERS_PAGE_SIZE }
            );
            this.state.ordersHasMore = this.state.orders.length === this.ORDERS_PAGE_SIZE;
        } catch (e) { /* silent */ }
        this._pollingOrders = false;
    }

    // Real 7-day running-total history → a smooth filled area/line chart
    // (like a small stock chart) instead of the old hardcoded squiggle or
    // a plain straight line. Higher current value = curve rises (smaller
    // y), matching the ▲/▼ trend arrow shown next to it. Each day's point
    // also gets an invisible hover target with a native tooltip so the
    // exact value per day is inspectable (id="Day -6" .. "Today").
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
        // Smooth quadratic curve through every point (midpoint smoothing).
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
        const items = [
            { label: 'Warehouses', value: s.warehouses, added: s.added_warehouses ?? 0, color: '#059669', colorDark: '#047857', icon: '🏭', trend: s.t_warehouses || '+0%', trendUp: (s.t_warehouses_up ?? true), spark: s.spark_warehouses },
            { label: 'Employees',  value: s.employees,  added: s.added_employees ?? 0,  color: '#6366f1', colorDark: '#4f46e5', icon: '👥', trend: s.t_employees || '+0%', trendUp: (s.t_employees_up ?? true), spark: s.spark_employees },
            { label: 'Shipments',  value: s.shipments,  added: s.added_shipments ?? 0,  color: '#8b5cf6', colorDark: '#7c3aed', icon: '📦', trend: s.t_shipments || '+0%', trendUp: (s.t_shipments_up ?? true), spark: s.spark_shipments },
            { label: 'Orders',  value: s.orders,     added: s.added_orders ?? 0,     color: '#f97316', colorDark: '#ea580c', icon: '📋', trend: s.t_orders || '+0%', trendUp: (s.t_orders_up ?? true), spark: s.spark_orders },
            { label: 'Jobs',       value: s.jobs,       added: s.added_jobs ?? 0,       color: '#06b6d4', colorDark: '#0891b2', icon: '💼', trend: s.t_jobs || '+0%', trendUp: (s.t_jobs_up ?? true), spark: s.spark_jobs },
        ];
        return items.map(i => {
            const sd = this._sparkData(i.spark);
            return { ...i, labelTr: this.tr(i.label), sparkId: 'spark-' + i.label.replace(/\s+/g, ''),
                     sparkPath: sd.path, sparkArea: sd.area, sparkDots: sd.dots,
                     sparkEndX: sd.endX, sparkEndY: sd.endY };
        });
    }

    // KPI cards mirror the operational metrics. (Website user counts live on
    // the dedicated Users management page, not on the home dashboard.)
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

    // Ensure charts exist & are up to date. Safe to call on every patch:
    // it only (re)builds a chart when the canvas is new or data changed.
    _syncCharts() {
        if (this.state.view !== 'dashboard' || this.state.dashboardLoading) return;
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

    // ─── Theme-aware Chart.js color palette ─────────────────────
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

            // Build gradient backgrounds for each bar (theme-aware)
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

    // ─── Core Navigation ──────────────────────────────────
    _navigate(view) { this._navHistory.push(this.state.view); this.state.view = view; }

    goBack() { this.state.view = this._navHistory.pop() || "dashboard"; }

    goToDashboard() {
        this._navHistory = [];
        this.state.view = "dashboard";
        this.state.selectedWarehouse = null;
        this.state.openSection = null;
        this.state.filterWarehouseId = null;
        this.state.filterWarehouseName = null;
        this.state.dashboardLoading = false;
    }

    toggleSection(section) {
        this.state.openSection = this.state.openSection === section ? null : section;
    }

    // ─── Warehouses ───────────────────────────────────────
    WAREHOUSE_FIELDS = ["id", "name", "code", "governorate", "province_id", "address",
        "manager_user_id", "state", "shipment_count", "employee_count", "order_count",
        "truck_count", "driver_count"];

    async openWarehouses() {
        this.state.openSection = null;
        this._navigate("warehouse_hub");
        this.state.loading = true;
        this.state.warehouseSearch = '';
        // OPEN sites only — the closed ones have their own screen, because a
        // list that mixes them makes an admin read the state badge on every
        // card to know which are taking work.
        //
        // Newest first, matching the backend listing: the warehouse somebody
        // is looking for is almost always the one just created, and by name
        // it is buried at whatever letter it happens to start with.
        this.state.warehouses = await this.orm.searchRead(
            "recycle.warehouse", [["state", "!=", "inactive"]],
            this.WAREHOUSE_FIELDS, { order: "create_date desc" },
        );
        this.state.loading = false;
    }

    /** Name search, applied on what is already loaded. */
    get visibleWarehouses() {
        const q = (this.state.warehouseSearch || '').trim().toLowerCase();
        const rows = this.state.warehouses || [];
        if (!q) return rows;
        // Substring, not whole-word: an admin types three letters of a name
        // they half-remember, and requiring the whole thing would mean already
        // knowing the answer to the question being asked.
        return rows.filter((w) =>
            (w.name || '').toLowerCase().includes(q)
            || (w.code || '').toLowerCase().includes(q));
    }

    /**
     * The sites that have been shut.
     *
     * They are NOT gone: a closed warehouse keeps its stock, its history and
     * whatever orders were already shipping out of it, and it still appears in
     * the backend's own listings. Leaving it off every screen here is what made
     * "where did that warehouse go?" a question with no answer — so it gets the
     * same cards, and a way back.
     */
    async openClosedWarehouses() {
        this._navigate("warehouse_closed");
        this.state.loading = true;
        this.state.warehouseSearch = '';
        this.state.closedWarehouses = await this.orm.searchRead(
            "recycle.warehouse", [["state", "=", "inactive"]],
            this.WAREHOUSE_FIELDS,
            { order: "create_date desc", context: { active_test: false } },
        );
        this.state.loading = false;
    }

    get visibleClosedWarehouses() {
        const q = (this.state.warehouseSearch || '').trim().toLowerCase();
        const rows = this.state.closedWarehouses || [];
        if (!q) return rows;
        return rows.filter((w) =>
            (w.name || '').toLowerCase().includes(q)
            || (w.code || '').toLowerCase().includes(q));
    }

    /** Put a closed warehouse back to work. */
    async reopenWarehouse(wh) {
        if (!wh) return;
        if (!(await this.askConfirm(this.tr('Re-open warehouse'), this.tr('Re-open this warehouse? It will start receiving new shipments and orders again.')))) return;
        this.state.whAdminError = null;
        try {
            await this.orm.call('recycle.warehouse', 'action_reopen_warehouse', [[wh.id]]);
            this.state.whAdminSuccess = this.tr('Warehouse re-opened.');
            setTimeout(() => { this.state.whAdminSuccess = null; }, 4000);
            await this.openClosedWarehouses();
        } catch (e) {
            this.state.whAdminError = this._err(e);
        }
    }

    selectWarehouse(wh) {
        this.state.selectedWarehouse = wh;
        this.state.whAdminError = null;
        this.state.whAdminSuccess = null;
        this._navigate("warehouse_detail");
    }

    // ─── Manage warehouse (admin): its OWN screen ─────────────────────────
    // Everything on it applies to state.selectedWarehouse — the warehouse the
    // admin already opened — so no warehouse picker is ever shown.
    async openWarehouseManage() {
        const wh = this.state.selectedWarehouse;
        if (!wh) return;
        this.state.whAdminError = null;
        this.state.whAdminSuccess = null;
        this._navigate('warehouse_manage');
        await this._refreshManagedWarehouse();
    }

    whStateLabel(s) {
        return s === 'closing' ? this.tr('Closing')
            : s === 'inactive' ? this.tr('Inactive')
            : this.tr('Active');
    }
    whStateBadge(s) {
        return 'o_ra_badge ' + (s === 'closing' ? 'o_ra_badge_warning'
            : s === 'inactive' ? 'o_ra_badge_danger' : 'o_ra_badge_success');
    }

    // ── Closing lifecycle ──
    async startWarehouseClosing() {
        const wh = this.state.selectedWarehouse;
        if (!wh) return;
        if (!(await this.askConfirm(this.tr('Close warehouse'), this.tr('Start closing this warehouse? New intake stops and the team is released.')))) return;
        await this._runWarehouseAdminAction(
            () => this.orm.call('recycle.warehouse', 'action_start_closing', [[wh.id]]),
            this.tr('Closing started — the warehouse no longer accepts new work.'));
    }

    async finalizeWarehouseClosing() {
        const wh = this.state.selectedWarehouse;
        if (!wh) return;
        if (!(await this.askConfirm(this.tr('Stop warehouse permanently'), this.tr('Stop this warehouse permanently? This cannot be undone.')))) return;
        await this._runWarehouseAdminAction(
            () => this.orm.call('recycle.warehouse', 'action_finalize_inactive', [[wh.id]]),
            this.tr('Warehouse stopped permanently.'));
    }

    /** Undo a closing that had not finished yet. */
    async cancelWarehouseClosing() {
        const wh = this.state.selectedWarehouse;
        if (!wh) return;
        await this._runWarehouseAdminAction(
            () => this.orm.call('recycle.warehouse', 'action_cancel_closing', [[wh.id]]),
            this.tr('Closing cancelled — no employee or truck was re-assigned automatically.'));
    }

    /** Bring a fully stopped warehouse back into service — from the MANAGE
     *  screen, which acts on `selectedWarehouse`.
     *
     *  Deliberately a DIFFERENT name from `reopenWarehouse(wh)` above. They are
     *  two flows: the closed-warehouses LIST passes the row it was clicked on,
     *  this one reads the warehouse already open on the manage screen. When both
     *  were called `reopenWarehouse`, this no-arg version silently overrode the
     *  other — so the list's "Reopen" button ran this instead, found no
     *  `selectedWarehouse`, and returned doing nothing. That was the bug. */
    async reopenManagedWarehouse() {
        const wh = this.state.selectedWarehouse;
        if (!wh) return;
        if (!(await this.askConfirm(this.tr('Re-open warehouse'), this.tr('Reopen this warehouse? Its old team and trucks will NOT come back automatically.')))) return;
        await this._runWarehouseAdminAction(
            () => this.orm.call('recycle.warehouse', 'action_reopen_warehouse', [[wh.id]]),
            this.tr('Warehouse reopened. No employee or truck was re-assigned automatically — assign resources manually.'));
    }

    /**
     * Re-reads the managed warehouse (including its lifecycle `state`) plus its
     * zones, and keeps the warehouses grid in sync — WITHOUT navigating away
     * (openWarehouses() would leave this screen).
     */
    async _refreshManagedWarehouse() {
        const wh = this.state.selectedWarehouse;
        if (!wh) return;
        try {
            const fresh = await this.orm.searchRead(
                'recycle.warehouse', [['id', '=', wh.id]],
                ['id', 'name', 'code', 'address', 'governorate', 'province_id', 'manager_user_id',
                 'state', 'active', 'employee_count', 'shipment_count',
                 'order_count', 'truck_count', 'driver_count'],
                { context: { active_test: false } });   // a stopped warehouse is archived
            if (fresh.length) {
                this.state.selectedWarehouse = fresh[0];
                const idx = this.state.warehouses.findIndex((w) => w.id === fresh[0].id);
                if (idx !== -1) this.state.warehouses[idx] = fresh[0];
            }
        } catch (e) { /* keep the current copy on a read failure */ }
        await this._loadWarehouseZones();
    }

    async _loadWarehouseZones() {
        const wh = this.state.selectedWarehouse;
        if (!wh) return;
        try {
            this.state.whZones = await this.orm.searchRead(
                'recycle.zone', [['warehouse_id', '=', wh.id]],
                ['id', 'name', 'zone_type'], { order: 'zone_type asc, name asc' });
        } catch (e) {
            this.state.whZones = [];
        }
    }

    zoneTypeLabel(t) {
        return t === 'receiving' ? this.tr('Receiving')
            : t === 'sorting' ? this.tr('Sorting')
            : t === 'output' ? this.tr('Output')
            : this.tr('Storage');
    }

    /**
     * Add a zone to the warehouse the admin already opened.
     *
     * Named distinctly from the GLOBAL `openZoneCreate()` further down (the
     * Zones section, which must ask which warehouse) — two methods with the
     * same name on one class silently override each other, which is exactly
     * why this button used to open the global screen and ask for a warehouse.
     */
    openWarehouseZoneCreate() {
        this.state.zoneForm = { name: '', zone_type: 'storage', warehouse_id: null };
        this.state.whAdminError = null;
        this.state.zoneCreateModal = true;
    }

    async confirmWarehouseZoneCreate() {
        const wh = this.state.selectedWarehouse;
        const f = this.state.zoneForm;
        if (!wh) return;
        if (!(f.name || '').trim()) {
            this.state.whAdminError = this.tr('Zone name is required.');
            return;
        }
        await this._runWarehouseAdminAction(
            () => this.orm.call('recycle.warehouse', 'action_add_zone',
                [[wh.id], f.name.trim(), f.zone_type]),
            this.tr('Zone added successfully.'));
    }

    async deleteWarehouseZone(zone) {
        const wh = this.state.selectedWarehouse;
        if (!wh || !zone) return;
        if (!(await this.askConfirm(this.tr('Delete zone'), this.tr('Delete this zone?')))) return;
        await this._runWarehouseAdminAction(
            () => this.orm.call('recycle.warehouse', 'action_delete_zone',
                [[wh.id], zone.id]),
            this.tr('Zone deleted successfully.'));
    }

    async openWarehouseManagerChange() {
        this.state.whAdminError = null;
        this.state.whManagerPick = '';
        try {
            this.state.whAvailableManagers = await this.orm.call(
                'recycle.warehouse', 'get_available_managers', []);
        } catch (e) {
            this.state.whAvailableManagers = [];
        }
        this.state.whManagerModal = true;
    }

    async confirmWarehouseManagerChange() {
        const wh = this.state.selectedWarehouse;
        if (!wh) return;
        if (!this.state.whManagerPick) {
            this.state.whAdminError = this.tr('Choose the new manager.');
            return;
        }
        await this._runWarehouseAdminAction(
            () => this.orm.call('recycle.warehouse', 'action_change_manager',
                [[wh.id], parseInt(this.state.whManagerPick)]),
            this.tr('Manager changed successfully.'));
    }

    async openWarehouseEdit() {
        const wh = this.state.selectedWarehouse;
        if (!wh) return;
        // Governorate and address are fixed at creation and cannot be edited
        // (the warehouse cannot move), so this form no longer carries them —
        // only the fields that may actually change.
        this.state.whEditForm = {
            name: wh.name || '', code: wh.code || '',
        };
        this.state.whAdminError = null;
        this.state.whEditModal = true;
    }

    async confirmWarehouseEdit() {
        const wh = this.state.selectedWarehouse;
        const f = this.state.whEditForm;
        if (!wh) return;
        if (!(f.name || '').trim() || !(f.code || '').trim()) {
            this.state.whAdminError = this.tr('Name and code cannot be empty.');
            return;
        }
        // Only the editable fields are sent. action_update_info whitelists them
        // and its write() pings the backend, so a name/code change reflects
        // there immediately — governorate and address are never touched.
        await this._runWarehouseAdminAction(
            () => this.orm.call('recycle.warehouse', 'action_update_info',
                [[wh.id], { name: f.name.trim(), code: f.code.trim() }]),
            this.tr('Warehouse updated successfully.'));
    }

    closeWarehouseAdminModals() {
        this.state.zoneCreateModal = false;
        this.state.whManagerModal = false;
        this.state.whEditModal = false;
        this.state.whAdminError = null;
    }

    /** Runs an admin action, then refreshes the warehouse + its zones. */
    async _runWarehouseAdminAction(call, successMsg) {
        this.state.whAdminSaving = true;
        this.state.whAdminError = null;
        try {
            await call();
            this.closeWarehouseAdminModals();
            this.state.whAdminSuccess = successMsg;
            const self = this;
            setTimeout(function () { self.state.whAdminSuccess = null; }, 4000);
            await this._refreshManagedWarehouse();
        } catch (e) {
            this.state.whAdminError = (e && e.data && e.data.message)
                || this.tr('Action failed. Please try again.');
        } finally {
            this.state.whAdminSaving = false;
        }
    }

    // Warehouse-detail navigation cards (same design as Shipments/Orders):
    // open the global lists pre-filtered to THIS warehouse.
    async openWarehouseTrucks() {
        const wh = this.state.selectedWarehouse; if (!wh) return;
        await this.openTrucks();
        this.state.truckWHFilter = String(wh.id);
        // Scope the screen to this warehouse: hide the warehouse dropdown and
        // show the "Showing items for" note (same as the employees screen).
        this.state.warehouseScope = wh.name || true;
    }
    async openWarehouseDrivers() {
        const wh = this.state.selectedWarehouse; if (!wh) return;
        await this.openDriversList();
        this.state.driverWHFilter = String(wh.id);
        this.state.warehouseScope = wh.name || true;
    }

    // (The warehouse-detail fleet lists were replaced by navigation cards —
    // Trucks/Drivers open the global screens pre-filtered to the warehouse.)

    /**
     * Loads the governorate options from recycle.province — the table mirrored
     * from the backend. Archived provinces (deleted in the backend) are left
     * out so they can no longer be picked, while warehouses already pointing at
     * one keep showing it. Cached for the session: the list changes rarely and
     * every form open would otherwise re-query it.
     */
    async _loadProvinces(force) {
        if (!force && this.state.warehouseGovernorates.length) return;
        try {
            const rows = await this.orm.searchRead(
                'recycle.province', [], ['id', 'name_ar', 'name_en'],
                { order: 'name_ar' });
            this.state.warehouseGovernorates = rows.map(
                (p) => [p.id, p.name_ar || p.name_en]);
        } catch (e) {
            this.state.warehouseGovernorates = [];
        }
    }

    // ── Add Warehouse ──
    async openWarehouseCreate() {
        await this._loadProvinces();
        this.state.warehouseForm = {
            name: '', code: '', province_id: '', latitude: '', longitude: '', address: '',
        };
        // Blank by default: _ensure_zones() on the server auto-fills the 4
        // standard zone types (Receiving/Sorting/Storage/Output) for
        // whichever ones aren't explicitly listed here — so leaving this
        // empty already gives the new warehouse its 4 default zones.
        this.state.warehouseZoneRows = [];
        this.state.warehouseError = null;
        this.state.warehouseSuccess = null;
        this._navigate('warehouse_create');
        // Draw the location-picker map once the form has painted.
        setTimeout(() => this._initWarehouseCreateMap(), 150);
    }

    /**
     * The "Add Warehouse" location picker: an OpenStreetMap map (Leaflet, from
     * the bundle) where the admin CLICKS the spot and the latitude/longitude
     * fields fill themselves. No API key, no typing coordinates by hand.
     */
    _initWarehouseCreateMap() {
        const L = window.L;
        const el = this.whCreateMapRef.el;
        if (!L || !el) return;
        if (this._whCreateMap) { try { this._whCreateMap.remove(); } catch (e) {} this._whCreateMap = null; }
        const f = this.state.warehouseForm;
        const hasPoint = f.latitude !== '' && f.longitude !== '';
        const start = hasPoint ? [parseFloat(f.latitude), parseFloat(f.longitude)] : [33.5138, 36.2765];
        this._whCreateMap = L.map(el).setView(start, hasPoint ? 13 : 6);
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19, attribution: "© OpenStreetMap contributors",
        }).addTo(this._whCreateMap);
        // A clearly RED pin marks the picked spot — a red teardrop drawn as an
        // inline SVG (no image file needed) so it reads instantly as "here".
        const redPin = L.divIcon({
            className: 'o_recycle_redpin',
            html: '<svg width="28" height="40" viewBox="0 0 28 40" xmlns="http://www.w3.org/2000/svg"><path d="M14 0C6.27 0 0 6.27 0 14c0 10.5 14 26 14 26s14-15.5 14-26C28 6.27 21.73 0 14 0z" fill="#dc2626" stroke="#991b1b" stroke-width="1"/><circle cx="14" cy="14" r="5.5" fill="#ffffff"/></svg>',
            iconSize: [28, 40],
            iconAnchor: [14, 40],
        });
        this._whCreateMarker = L.marker(start, { draggable: true, icon: redPin }).addTo(this._whCreateMap);
        const setFromLatLng = (ll) => {
            this.state.warehouseForm.latitude = Number(ll.lat.toFixed(7));
            this.state.warehouseForm.longitude = Number(ll.lng.toFixed(7));
        };
        this._whCreateMarker.on('dragend', () => setFromLatLng(this._whCreateMarker.getLatLng()));
        this._whCreateMap.on('click', (ev) => {
            this._whCreateMarker.setLatLng(ev.latlng);
            setFromLatLng(ev.latlng);
        });
        setTimeout(() => this._whCreateMap && this._whCreateMap.invalidateSize(), 200);
    }
    addWarehouseZoneRow() {
        this.state.warehouseZoneRows.push({ name: '', zone_type: 'storage' });
    }
    removeWarehouseZoneRow(idx) {
        this.state.warehouseZoneRows.splice(idx, 1);
    }
    async saveNewWarehouse() {
        const f = this.state.warehouseForm;
        const name = (f.name || '').trim();
        const code = (f.code || '').trim();
        if (!name) { this.state.warehouseError = this.tr('Warehouse name is required.'); return; }
        if (!code) { this.state.warehouseError = this.tr('Warehouse code is required.'); return; }
        const lat = f.latitude === '' ? 0 : parseFloat(f.latitude);
        const lng = f.longitude === '' ? 0 : parseFloat(f.longitude);
        if (f.latitude !== '' && (isNaN(lat) || lat < -90 || lat > 90)) {
            this.state.warehouseError = this.tr('Latitude must be between -90 and 90.'); return;
        }
        if (f.longitude !== '' && (isNaN(lng) || lng < -180 || lng > 180)) {
            this.state.warehouseError = this.tr('Longitude must be between -180 and 180.'); return;
        }
        // Any partially-filled zone row (name typed but no type, or vice
        // versa) is rejected rather than silently dropped or silently
        // defaulted — the admin must fix or clear it.
        const zoneCmds = [];
        for (const row of this.state.warehouseZoneRows) {
            const zname = (row.name || '').trim();
            if (!zname && !row.zone_type) continue;
            if (!zname || !row.zone_type) {
                this.state.warehouseError = this.tr('Each zone needs both a name and a type — remove incomplete rows.');
                return;
            }
            zoneCmds.push([0, 0, { name: zname, zone_type: row.zone_type }]);
        }
        this.state.warehouseSaving = true;
        this.state.warehouseError = null;
        try {
            const vals = {
                name: name,
                code: code,
                province_id: f.province_id ? parseInt(f.province_id, 10) : false,
                latitude: lat,
                longitude: lng,
                address: (f.address || '').trim() || false,
            };
            if (zoneCmds.length) { vals.zone_ids = zoneCmds; }
            await this.orm.create('recycle.warehouse', [vals]);
            this.state.warehouseSaving = false;
            this.state.warehouseSuccess = this.tr('Warehouse created successfully!');
            this.state.warehouseForm = { name: '', code: '', province_id: '', latitude: '', longitude: '', address: '' };
            this.state.warehouseZoneRows = [];
            setTimeout(() => { this.state.warehouseSuccess = null; }, 4000);
        } catch (e) {
            this.state.warehouseSaving = false;
            this.state.warehouseError = (e && e.data && e.data.message)
                || this.tr('Creation failed. Please check the fields.');
        }
    }

    // ── Open a warehouse's sub-lists, scoped to that warehouse ──
    // The scope hides the warehouse-filter dropdown in the target list, since
    // everything shown already belongs to this warehouse.
    async openWarehouseEmployees() {
        const wh = this.state.selectedWarehouse; if (!wh) return;
        this.state.warehouseScope = wh.name || true;
        this.state.employeeTab = 'active';
        this.state.employeeWHFilter = wh.id;
        this.state.archivedWHFilter = wh.id;
        await this.openEmployeesList();
    }
    async openWarehouseArchived() {
        const wh = this.state.selectedWarehouse; if (!wh) return;
        this.state.warehouseScope = wh.name || true;
        this.state.employeeTab = 'deleted';
        this.state.archivedWHFilter = wh.id;
        this.state.employeeWHFilter = wh.id;
        await this.openEmployeesList();
    }

    // ─── Trucks (fleet) ───────────────────────────────────
    // Authored HERE; every create/write on recycle.truck pings the NestJS
    // backend fleet webhook from the Python model, so the backend mirror
    // (trucks table + admin notification) refreshes on its own — nothing
    // extra to call from this screen.
    TRUCK_FIELDS = ["id", "name", "plate_number", "model", "year",
                    "max_payload_kg", "warehouse_id", "is_active",
                    "truck_type", "disable_reason", "notes"];

    async openTrucks() {
        this.state.openSection = null;
        this._navigate("trucks_list");
        this.state.loading = true;
        try {
            if (!this.state.warehouses.length) {
                this.state.warehouses = await this.orm.searchRead("recycle.warehouse", [["state", "=", "active"]], ["id", "name"]);
            }
            await this._refetchTrucks();
        } finally {
            this.state.loading = false;
        }
    }

    async _refetchTrucks() {
        // Fleet size is bounded (a few trucks per warehouse), so one full
        // fetch + client-side filtering is the right trade-off here — same
        // precedent as zones/shifts, unlike the unbounded shipments/orders.
        this.state.trucks = await this.orm.searchRead(
            "recycle.truck", [], this.TRUCK_FIELDS, { order: "name" });
    }

    get filteredTrucks() {
        const q = (this.state.truckSearch || '').trim().toLowerCase();
        const whFilter = this.state.truckWHFilter;
        const stFilter = this.state.truckStatusFilter;
        const tyFilter = this.state.truckTypeFilter;
        return this.state.trucks.filter((t) => {
            // ONE list showing both kinds, filtered. Two separate screens would
            // drift apart, and a truck whose job was set wrongly would vanish
            // from both instead of showing up in the wrong one.
            if (tyFilter && t.truck_type !== tyFilter) return false;
            if (whFilter === 'none' && t.warehouse_id) return false;
            if (whFilter && whFilter !== 'none'
                && (!t.warehouse_id || t.warehouse_id[0] !== parseInt(whFilter))) return false;
            if (stFilter === 'active' && !t.is_active) return false;
            if (stFilter === 'inactive' && t.is_active) return false;
            if (q) {
                const hay = [t.name, t.plate_number, t.model || '',
                             t.warehouse_id ? t.warehouse_id[1] : ''].join(' ').toLowerCase();
                if (!hay.includes(q)) return false;
            }
            return true;
        });
    }

    onTruckSearchInput(ev) { this.state.truckSearch = ev.target.value; }
    setTruckWHFilter(ev) { this.state.truckWHFilter = ev.target.value; }
    setTruckStatusFilter(ev) { this.state.truckStatusFilter = ev.target.value; }

    async openTruckCreate() {
        if (!this.state.warehouses.length) {
            this.state.warehouses = await this.orm.searchRead("recycle.warehouse", [["state", "=", "active"]], ["id", "name"]);
        }
        this.state.truckEditMode = false;
        this.state.selectedTruck = null;
        this.state.truckForm = { name: '', plate_number: '', model: '', year: '',
                                 max_payload_kg: '', warehouse_id: '',
                                 truck_type: 'collection', is_active: true, notes: '' };
        this.state.truckError = null;
        this.state.truckSuccess = null;
        this._navigate('truck_form');
    }

    openTruckEdit(truck) {
        this.state.truckEditMode = true;
        this.state.selectedTruck = truck;
        this.state.truckForm = {
            name: truck.name || '',
            plate_number: truck.plate_number || '',
            model: truck.model || '',
            year: truck.year ? '' + truck.year : '',
            max_payload_kg: truck.max_payload_kg ? '' + truck.max_payload_kg : '',
            warehouse_id: truck.warehouse_id ? '' + truck.warehouse_id[0] : '',
            truck_type: truck.truck_type || 'collection',
            is_active: !!truck.is_active,
            notes: truck.notes || '',
        };
        this.state.truckError = null;
        this.state.truckSuccess = null;
        this._navigate('truck_form');
    }

    /** Validate the form; returns the ORM vals dict or null (error shown). */
    _truckVals() {
        const f = this.state.truckForm;
        const name = (f.name || '').trim();
        const plate = (f.plate_number || '').trim();
        if (!name) { this.state.truckError = this.tr('Truck name is required.'); return null; }
        if (!plate) { this.state.truckError = this.tr('Plate number is required.'); return null; }
        let year = 0;
        if (f.year !== '' && f.year !== null) {
            year = parseInt(f.year);
            const maxYear = new Date().getFullYear() + 1;
            if (isNaN(year) || year < 1980 || year > maxYear) {
                this.state.truckError = this.tr('Year must be between 1980 and next year.');
                return null;
            }
        }
        let payload = 0;
        if (f.max_payload_kg !== '' && f.max_payload_kg !== null) {
            payload = parseFloat(f.max_payload_kg);
            if (isNaN(payload) || payload < 0) {
                this.state.truckError = this.tr('Max payload must be a positive number.');
                return null;
            }
        }
        return {
            name: name,
            plate_number: plate,
            model: (f.model || '').trim() || false,
            year: year,
            max_payload_kg: payload,
            warehouse_id: f.warehouse_id ? parseInt(f.warehouse_id) : false,
            // Only on CREATE. A truck's job is fixed for life, and re-sending it
            // on every edit would make each save depend on the server's
            // "unchanged" check being exactly right.
            ...(this.state.truckEditMode ? {} : { truck_type: f.truck_type || 'collection' }),
            is_active: !!f.is_active,
            notes: (f.notes || '').trim() || false,
        };
    }

    setTruckTypeFilter(type) { this.state.truckTypeFilter = type || ''; }

    // ══════════════════════════════════════════════════════════════════
    // Delivery drivers — recruited here, unlike collectors.
    //
    // A collector applies through the mobile app, has an account in the NestJS
    // backend, works a SHIFT, and is approved as a driver request. A delivery
    // driver is hired by the administrator right here, has no backend account,
    // works no shift, and carries sold goods from a warehouse to the buyer.
    // The two are separate screens because they are separate records: neither
    // could fill the other's fields.
    // ══════════════════════════════════════════════════════════════════
    DD_FIELDS = ["id", "name", "phone", "email", "national_id", "address",
                 "birth_date", "license_number", "license_expiry",
                 "warehouse_id", "truck_id", "truck_plate", "has_truck",
                 "is_active", "is_blocked", "blocked_reason", "notes", "user_id"];

    async openDeliveryDrivers() {
        this._navigate('delivery_drivers_list');
        this.state.ddDetailId = null;
        await this._reloadDeliveryDrivers();
    }

    /**
     * Refetch the drivers WITHOUT moving the user.
     *
     * Every action (block, assign a truck, create a login) can now be taken
     * from two places: the list and the driver's own page. Reloading used to
     * mean re-entering the list, which threw whoever acted from the driver's
     * page back out of it — losing the record they were working on right after
     * they changed something about it.
     */
    async _reloadDeliveryDrivers() {
        this.state.ddLoading = true;
        this.state.ddError = null;
        this.state.ddAssigning = null;
        try {
            if (!this.state.warehouses.length) {
                this.state.warehouses = await this.orm.searchRead(
                    "recycle.warehouse", [["state", "=", "active"]], ["id", "name"]);
            }
            this.state.deliveryDrivers = await this.orm.searchRead(
                'recycle.delivery.driver', [], this.DD_FIELDS, { order: 'name' });
        } catch (e) {
            this.state.deliveryDrivers = [];
            this.state.ddError = this._err(e);
        }
        this.state.ddLoading = false;
    }

    get filteredDeliveryDrivers() {
        const q = (this.state.ddSearch || '').trim().toLowerCase();
        const wh = this.state.ddWHFilter;
        const tf = this.state.ddTruckFilter;
        return this.state.deliveryDrivers.filter((d) => {
            if (wh && (!d.warehouse_id || '' + d.warehouse_id[0] !== wh)) return false;
            // The one question this screen is opened to answer: who still needs
            // a vehicle.
            if (tf === 'assigned' && !d.has_truck) return false;
            if (tf === 'unassigned' && d.has_truck) return false;
            if (q) {
                const hay = [d.name, d.phone || '', d.national_id || '',
                             d.email || ''].join(' ').toLowerCase();
                if (!hay.includes(q)) return false;
            }
            return true;
        });
    }

    onDeliveryDriverSearchInput(ev) { this.state.ddSearch = ev.target.value; }
    setDeliveryDriverWHFilter(ev) { this.state.ddWHFilter = ev.target.value; }
    setDeliveryDriverFilter(v) { this.state.ddTruckFilter = v || ''; }

    // ─── The driver's own page ──────────────────────────────────
    //
    // The list used to carry six action buttons per row. On a phone that is a
    // wall of wrapped text in one cell, and even on a desktop it left nowhere
    // to SHOW anything: not the licence scans that were made mandatory, not the
    // address, not which trucks the person has held. One button opens a page
    // that has room for both the facts and the actions.

    /** Keyed by id, not by the row object, so the page survives a refetch. */
    get ddDetail() {
        const id = this.state.ddDetailId;
        if (!id) return null;
        return this.state.deliveryDrivers.find((d) => d.id === id) || null;
    }

    async openDeliveryDriverDetail(driver) {
        this.state.ddDetailId = driver.id;
        this.state.ddError = null;
        this.state.ddSuccess = null;
        this.state.ddAssigning = null;
        this.state.ddBlocking = null;
        this._navigate('delivery_driver_detail');
        await this._loadDriverTruckHistory(driver.id);
    }

    /**
     * Every truck this driver has held, newest first.
     *
     * The same rows the printed file is built from — shown on screen so the
     * common case (a quick "which van did he have last month?") does not
     * require generating a PDF to answer.
     */
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
            this.state.ddError = this._err(e);
        }
        this.state.ddHistoryLoading = false;
    }

    /** Odoo's own image route — avoids pulling two base64 scans into state. */
    ddImageUrl(driverId, field) {
        return '/web/image/recycle.delivery.driver/' + driverId + '/' + field;
    }

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

    /**
     * The single point every failed action passes through — so putting the
     * failure where a user actually sees it took one change, not thirteen.
     *
     * Odoo carries a UserError's text on `e.data.message`; anything else is a
     * crash the user cannot act on, so that gets a plain line rather than a
     * Python traceback.
     *
     * It still RETURNS the message as well as showing it. The callers assign it
     * to an inline field inside a form, and that field stays after the dialog
     * is dismissed — the dialog is the announcement, the inline text is the
     * record of which form failed.
     */
    _err(e) {
        const msg = (e && e.data && e.data.message) || this.tr('Action failed.');
        if (this.showError) this.showError(msg);
        return msg;
    }

    // ─── Add / edit ─────────────────────────────────────────────
    async openDeliveryDriverCreate() {
        if (!this.state.warehouses.length) {
            this.state.warehouses = await this.orm.searchRead(
                "recycle.warehouse", [["state", "=", "active"]], ["id", "name"]);
        }
        this.state.ddEditMode = false;
        this.state.selectedDeliveryDriver = null;
        this.state.ddForm = {
            name: '', phone: '', email: '', national_id: '', address: '',
            birth_date: '', license_number: '', license_expiry: '',
            license_image_front: null, license_image_back: null,
            warehouse_id: '', truck_id: '', is_active: true, notes: '',
        };
        this.state.ddError = null;
        this.state.ddSuccess = null;
        this.state.ddFreeTrucks = [];
        this._navigate('delivery_driver_form');
    }

    async openDeliveryDriverEdit(driver) {
        if (!this.state.warehouses.length) {
            this.state.warehouses = await this.orm.searchRead(
                "recycle.warehouse", [["state", "=", "active"]], ["id", "name"]);
        }
        this.state.ddEditMode = true;
        this.state.selectedDeliveryDriver = driver;
        this.state.ddForm = {
            name: driver.name || '',
            phone: driver.phone || '',
            email: driver.email || '',
            national_id: driver.national_id || '',
            address: driver.address || '',
            birth_date: driver.birth_date || '',
            license_number: driver.license_number || '',
            license_expiry: driver.license_expiry || '',
            // Left null on edit: the images are already stored, and re-sending
            // them would mean reading two files back out of the browser for no
            // reason. Picking a new file replaces that side only.
            license_image_front: null,
            license_image_back: null,
            warehouse_id: driver.warehouse_id ? '' + driver.warehouse_id[0] : '',
            truck_id: driver.truck_id ? '' + driver.truck_id[0] : '',
            is_active: !!driver.is_active,
            notes: driver.notes || '',
        };
        this.state.ddError = null;
        this.state.ddSuccess = null;
        await this._loadFreeDeliveryTrucks();
        this._navigate('delivery_driver_form');
    }

    /** Read one licence image into base64 for the ORM. */
    _readImage(ev, side) {
        const file = ev.target.files && ev.target.files[0];
        if (!file) { this.state.ddForm[side] = null; return; }
        const reader = new FileReader();
        reader.onload = () => {
            this.state.ddForm[side] = String(reader.result).split(',')[1] || null;
        };
        reader.readAsDataURL(file);
    }
    onLicenceFrontChange(ev) { this._readImage(ev, 'license_image_front'); }
    onLicenceBackChange(ev) { this._readImage(ev, 'license_image_back'); }

    /**
     * Print this driver's file as a PDF.
     *
     * Opened from the DRIVER, not from a separate reporting screen: whoever
     * wants the file already has the person in front of them, and a standalone
     * report would make them search for someone they were already looking at.
     *
     * The document carries their details plus every truck they have held, with
     * the dates — which is the question actually asked after an accident, a
     * fuel discrepancy or a complaint.
     */
    printDeliveryDriverFile(driver) {
        return this._downloadDriverFile(
            'report_delivery_driver_file', driver);
    }

    printCollectionDriverFile(driver) {
        return this._downloadDriverFile(
            'report_collection_driver_file', driver);
    }

    /**
     * Fetch the file and SAVE it, rather than opening a tab.
     *
     * `window.open` on the report URL leaves the PDF in a browser tab named
     * after the route — on a phone that is a viewer with no obvious way back,
     * and on a desktop it is a document the user then has to save by hand under
     * a name like "report_delivery_driver_file". The file is meant to be kept
     * and sent on, so it is downloaded, named after the person.
     *
     * The blob is revoked afterwards: each one holds the whole PDF in memory
     * until the page is reloaded, and this button gets pressed repeatedly.
     */
    async _downloadDriverFile(reportName, driver) {
        const url = '/report/pdf/recycle_warehouse.' + reportName + '/' + driver.id;
        const safeName = String(driver.name || 'driver')
            .replace(/[\\/:*?"<>|]+/g, '-').trim() || 'driver';
        try {
            const response = await fetch(url, { credentials: 'same-origin' });
            if (!response.ok) throw new Error(String(response.status));
            const blob = await response.blob();
            const objectUrl = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = objectUrl;
            link.download = safeName + '.pdf';
            document.body.appendChild(link);
            link.click();
            link.remove();
            // Given back after the click has been handled — revoking it in the
            // same tick cancels the download in some browsers.
            setTimeout(() => URL.revokeObjectURL(objectUrl), 10_000);
        } catch (e) {
            this.notification && this.notification.add(
                this.tr('Could not generate the PDF file.'), { type: 'danger' });
        }
    }

    // ─── Image viewer ───────────────────────────────────────────
    // Licence scans used to be links with target="_blank". A tab holding a bare
    // image has no context and, on a phone, no clear way back to the driver you
    // were reading. The overlay keeps the page underneath.
    openImageViewer(url, caption) {
        this.state.imageViewer = { url, caption: caption || '' };
    }
    closeImageViewer() { this.state.imageViewer = null; }

    // ─── Truck picker (a screen, not a dropdown) ────────────────
    async openTruckPicker() {
        if (!this.state.ddForm.warehouse_id) {
            this.state.ddError = this.tr('Choose the warehouse first — a driver loads from one site, so only its trucks are offered.');
            return;
        }
        this.state.ddError = null;
        this.state.ddTruckPickerSearch = '';
        await this._loadFreeDeliveryTrucks();
        this.state.ddTruckPickerOpen = true;
    }
    closeTruckPicker() { this.state.ddTruckPickerOpen = false; }
    chooseTruck(truck) {
        this.state.ddForm.truck_id = '' + truck.id;
        this.state.ddTruckPickerOpen = false;
    }
    clearChosenTruck() { this.state.ddForm.truck_id = ''; }
    onTruckPickerSearch(ev) { this.state.ddTruckPickerSearch = ev.target.value; }

    get pickerTrucks() {
        const q = (this.state.ddTruckPickerSearch || '').trim().toLowerCase();
        if (!q) return this.state.ddFreeTrucks;
        return this.state.ddFreeTrucks.filter((t) =>
            [t.name, t.plate_number, t.model || ''].join(' ').toLowerCase().includes(q));
    }

    get chosenTruckLabel() {
        const id = parseInt(this.state.ddForm.truck_id);
        if (!id) return '';
        const t = this.state.ddFreeTrucks.find((x) => x.id === id);
        return t ? (t.name + ' — ' + t.plate_number) : ('#' + id);
    }

    // ─── Blocking ───────────────────────────────────────────────
    startBlockDeliveryDriver(driver) {
        this.state.ddBlocking = driver;
        this.state.ddBlockReason = '';
        this.state.ddError = null;
    }
    cancelBlockDeliveryDriver() { this.state.ddBlocking = null; }

    async confirmBlockDeliveryDriver() {
        const driver = this.state.ddBlocking;
        const reason = (this.state.ddBlockReason || '').trim();
        if (!driver || !reason) {
            this.state.ddError = this.tr('Give a reason for the block — it is what the driver is told.');
            return;
        }
        try {
            await this.orm.call('recycle.delivery.driver', 'action_block',
                [[driver.id], reason]);
            this.notification && this.notification.add(
                this.tr('Driver blocked.'), { type: 'success' });
            this.state.ddBlocking = null;
            await this._afterDriverAction();
        } catch (e) { this.state.ddError = this._err(e); }
    }

    async unblockDeliveryDriver(driver) {
        try {
            await this.orm.call('recycle.delivery.driver', 'action_unblock',
                [[driver.id]]);
            this.notification && this.notification.add(
                this.tr('Driver unblocked.'), { type: 'success' });
            await this._afterDriverAction();
        } catch (e) { this.state.ddError = this._err(e); }
    }

    /**
     * Refresh after an action, staying wherever the user is.
     *
     * Blocking a driver takes their truck back, so the history changes too —
     * and the driver's page shows that history. Reloading only the list would
     * leave the page contradicting itself: no truck at the top, still held at
     * the bottom.
     */
    async _afterDriverAction() {
        await this._reloadDeliveryDrivers();
        if (this.state.view === 'delivery_driver_detail' && this.state.ddDetailId) {
            await this._loadDriverTruckHistory(this.state.ddDetailId);
        }
    }

    async onDeliveryDriverWarehouseChange() {
        // The truck list depends on the warehouse: a driver loads at one site,
        // so a truck parked at another is not a choice they can act on.
        this.state.ddForm.truck_id = '';
        await this._loadFreeDeliveryTrucks();
    }

    async _loadFreeDeliveryTrucks() {
        this.state.ddFreeTrucks = [];
        const whId = this.state.ddForm.warehouse_id;
        if (!whId) return;
        try {
            const trucks = await this.orm.call(
                'recycle.delivery.driver', 'free_delivery_trucks',
                [parseInt(whId)]);
            this.state.ddFreeTrucks = trucks || [];
            // On edit, the driver's CURRENT truck is not "free" — but it must
            // still appear, or saving the form would silently unassign them.
            const cur = this.state.selectedDeliveryDriver;
            if (this.state.ddEditMode && cur && cur.truck_id) {
                const already = this.state.ddFreeTrucks
                    .some((t) => t.id === cur.truck_id[0]);
                if (!already) {
                    this.state.ddFreeTrucks.unshift({
                        id: cur.truck_id[0],
                        name: cur.truck_id[1],
                        plate_number: cur.truck_plate || '',
                    });
                }
            }
        } catch (e) {
            this.state.ddError = this._err(e);
        }
    }

    /** Validate the form; returns ORM vals or null (error shown). */
    _deliveryDriverVals() {
        const f = this.state.ddForm;
        const name = (f.name || '').trim();
        const phone = (f.phone || '').trim();
        const nid = (f.national_id || '').trim();
        if (!name) { this.state.ddError = this.tr('Driver name is required.'); return null; }
        if (!phone) { this.state.ddError = this.tr('Phone is required.'); return null; }
        if (!nid) { this.state.ddError = this.tr('National ID is required.'); return null; }
        if (!f.warehouse_id) {
            this.state.ddError = this.tr('Warehouse is required — deliveries start at one.');
            return null;
        }
        // BOTH sides of the licence, on create. Half a licence proves nothing:
        // the expiry date and the class are printed on the back, and they are
        // what decide whether this person may drive a company truck at all.
        if (!this.state.ddEditMode) {
            if (!f.license_image_front || !f.license_image_back) {
                this.state.ddError = this.tr('Both sides of the driving licence are required.');
                return null;
            }
        }

        const vals = {
            name: name,
            phone: phone,
            email: (f.email || '').trim() || false,
            national_id: nid,
            address: (f.address || '').trim() || false,
            birth_date: f.birth_date || false,
            license_number: (f.license_number || '').trim() || false,
            license_expiry: f.license_expiry || false,
            warehouse_id: parseInt(f.warehouse_id),
            truck_id: f.truck_id ? parseInt(f.truck_id) : false,
            is_active: !!f.is_active,
            notes: (f.notes || '').trim() || false,
        };
        // Only send an image when one was actually chosen, so editing a phone
        // number never wipes a licence scan.
        if (f.license_image_front) vals.license_image_front = f.license_image_front;
        if (f.license_image_back) vals.license_image_back = f.license_image_back;
        return vals;
    }

    async saveDeliveryDriver() {
        const vals = this._deliveryDriverVals();
        if (!vals) return;
        this.state.ddSaving = true;
        this.state.ddError = null;
        try {
            if (this.state.ddEditMode && this.state.selectedDeliveryDriver) {
                await this.orm.write('recycle.delivery.driver',
                    [this.state.selectedDeliveryDriver.id], vals);
            } else {
                await this.orm.create('recycle.delivery.driver', [vals]);
            }
            const wasEdit = this.state.ddEditMode;
            this.state.ddSuccess = wasEdit
                ? this.tr('Delivery driver updated successfully!')
                : this.tr('Delivery driver created successfully!');
            if (wasEdit) {
                // Back to whichever screen opened the form — the driver's own
                // page, usually. Sending an edit to the LIST would make anyone
                // working on one person lose them the moment they saved.
                await this._reloadDeliveryDrivers();
                this.goBack();
                if (this.state.view === 'delivery_driver_detail'
                        && this.state.ddDetailId) {
                    await this._loadDriverTruckHistory(this.state.ddDetailId);
                }
            } else {
                await this.openDeliveryDrivers();
            }
        } catch (e) {
            this.state.ddError = this._err(e);
        }
        this.state.ddSaving = false;
    }

    // ─── Assign a delivery truck ────────────────────────────────
    async startAssignDeliveryTruck(driver) {
        this.state.ddAssigning = driver;
        this.state.ddSelectedTruck = '';
        this.state.ddError = null;
        this.state.ddFreeTrucks = [];
        try {
            // Fetched at the moment of asking, not cached with the page: a
            // truck free when the list was drawn may have been taken since.
            const whId = driver.warehouse_id ? driver.warehouse_id[0] : false;
            this.state.ddFreeTrucks = await this.orm.call(
                'recycle.delivery.driver', 'free_delivery_trucks', [whId]);
        } catch (e) {
            this.state.ddError = this._err(e);
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
            this.state.ddError = this._err(e);
        }
    }

    async unassignDeliveryTruck(driver) {
        try {
            await this.orm.call('recycle.delivery.driver',
                'action_unassign_truck', [driver.id]);
            this.notification && this.notification.add(
                this.tr('Truck assignment removed.'), { type: 'success' });
            await this._afterDriverAction();
        } catch (e) {
            this.state.ddError = this._err(e);
        }
    }

    async createDeliveryDriverLogin(driver) {
        try {
            await this.orm.call('recycle.delivery.driver',
                'action_create_login', [[driver.id]]);
            this.notification && this.notification.add(
                this.tr('Login created for the driver.'), { type: 'success' });
            await this._afterDriverAction();
        } catch (e) {
            this.state.ddError = this._err(e);
        }
    }

    truckTypeLabel(type) {
        return type === 'delivery' ? this.tr('Delivery') : this.tr('Collection');
    }

    async saveTruck() {
        const vals = this._truckVals();
        if (!vals) return;
        this.state.truckSaving = true;
        this.state.truckError = null;
        try {
            if (this.state.truckEditMode && this.state.selectedTruck) {
                await this.orm.write('recycle.truck', [this.state.selectedTruck.id], vals);
            } else {
                await this.orm.create('recycle.truck', [vals]);
            }
            await this._refetchTrucks();
            this.state.truckSuccess = this.state.truckEditMode
                ? this.tr('Truck updated successfully!')
                : this.tr('Truck created successfully!');
            const self = this;
            setTimeout(function () { self.state.truckSuccess = null; }, 4000);
            this.goBack();   // pops the history entry pushed when the form opened
        } catch (e) {
            this.state.truckError = (e && e.data && e.data.message)
                || this.tr('Save failed. Please check the fields.');
        } finally {
            this.state.truckSaving = false;
        }
    }

    async toggleTruckActive(truck) {
        // Disabling REQUIRES a reason (server-enforced, shown next to the
        // truck) — open the modal. Re-enabling is direct.
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
            await this.orm.call('recycle.truck', 'action_toggle_service_state',
                [[truck.id], reason || false]);
            await this._refetchTrucks();
        } catch (e) {
            this.notification.add(
                (e && e.data && e.data.message)
                || this.tr('Could not update the truck status.'), { type: 'danger' });
        }
    }

    // ─── Driver Requests (pushed from the NestJS backend) ─
    // Decisions are STRICT round-trips: the server action posts the
    // driver-decision webhook FIRST and raises when the backend is
    // unreachable — Odoo and the backend can never disagree.
    async openDriverRequests() {
        this.state.openSection = null;
        this._navigate('driver_requests');
        this.state.loading = true;
        try {
            if (!this.state.warehouses.length) {
                this.state.warehouses = await this.orm.searchRead("recycle.warehouse", [["state", "=", "active"]], ["id", "name"]);
            }
            await this._refetchDriverRequests();
        } finally {
            this.state.loading = false;
        }
    }

    async _refetchDriverRequests() {
        this.state.driverRequestsLoading = true;
        try {
            const reqs = await this.orm.searchRead(
                'recycle.driver.request', [],
                ['id', 'name', 'email', 'phone', 'national_id', 'state',
                 'rejection_reason', 'warehouse_id', 'create_date', 'decided_at',
                 'province_name', 'address', 'location_note', 'latitude', 'longitude',
                 'shift_id', 'shift_name', 'shift_start', 'shift_end',
                 'has_rejected_image', 'is_blocked'],
                { order: 'id desc', limit: 300 });
            const ids = reqs.map((r) => r.id);
            const imgs = ids.length ? await this.orm.searchRead(
                'recycle.driver.request.image', [['request_id', 'in', ids]],
                ['id', 'request_id', 'backend_media_id', 'file_type', 'url', 'status',
                 // Whether the driver has actually been ASKED for this one —
                 // which is a different question from whether it was rejected,
                 // and the buttons differ on the answer.
                 'reupload_requested']) : [];
            for (const r of reqs) {
                r.images = imgs.filter((i) => i.request_id && i.request_id[0] === r.id);
            }
            this.state.driverRequests = reqs;
            // Keep the open detail view pointing at the FRESH row (a decision
            // just changed its state/images — the old object would show stale
            // buttons, e.g. Accept still visible after rejecting a document).
            if (this.state.selectedDriverRequest) {
                const fresh = reqs.find((r) => r.id === this.state.selectedDriverRequest.id);
                if (fresh) this.state.selectedDriverRequest = fresh;
            }
        } finally {
            this.state.driverRequestsLoading = false;
        }
    }

    // ── Detail view (account / location / documents in separate cards) ──
    openDriverRequestDetail(req) {
        this.state.selectedDriverRequest = req;
        this.state.driverActionError = null;
        this.state.driverActionSuccess = null;
        this._navigate('driver_request_detail');
    }

    /** "08:30" from Odoo's float hour (8.5). Shared by the shift card. */
    driverShiftTime(f) {
        if (typeof f !== 'number') return '—';
        const h = Math.floor(f);
        const m = Math.round((f - h) * 60);
        return String(h).padStart(2, '0') + ':' + String(m).padStart(2, '0');
    }

    /** Google-Maps link for the registered point (blank when not provided). */
    driverMapLink(req) {
        if (!req || !req.latitude || !req.longitude) return '';
        return 'https://www.google.com/maps?q=' + req.latitude + ',' + req.longitude;
    }

    get filteredDriverRequests() {
        const t = this.state.driverRequestTab;
        if (!t || t === 'all') return this.state.driverRequests;
        return this.state.driverRequests.filter((r) => r.state === t);
    }

    setDriverRequestTab(tab) { this.state.driverRequestTab = tab; }

    // The filters are a <select> rather than a row of buttons — five states
    // wrapped onto three lines on a phone and pushed the list below the fold.
    onDriverRequestTabChange(ev) { this.setDriverRequestTab(ev.target.value); }
    onEmployeeTabChange(ev) { return this.switchEmployeeTab(ev.target.value); }

    driverStateLabel(st) {
        return st === 'accepted' ? this.tr('Accepted')
            : st === 'rejected' ? this.tr('Rejected')
            : st === 'need_changes' ? this.tr('Needs Changes')
            : this.tr('Pending');
    }
    driverStateBadge(st) {
        return 'o_ra_badge ' + (st === 'accepted' ? 'o_ra_badge_success'
            : st === 'rejected' ? 'o_ra_badge_danger'
            : st === 'need_changes' ? 'o_ra_badge_warning' : 'o_ra_badge_info');
    }

    // ── Accept (warehouse is mandatory) ──
    openDriverAccept(req) {
        this.state.selectedDriverRequest = req;
        this.state.driverAcceptWH = '';
        this.state.driverActionError = null;
        this.state.driverAcceptModal = true;
    }
    async confirmDriverAccept() {
        const req = this.state.selectedDriverRequest;
        if (!req) return;
        if (!this.state.driverAcceptWH) {
            this.state.driverActionError = this.tr('Choose the warehouse this driver will serve.');
            return;
        }
        await this._runDriverAction(
            () => this.orm.call('recycle.driver.request', 'action_accept',
                [[req.id], parseInt(this.state.driverAcceptWH)]),
            this.tr('Driver accepted — the backend was notified.'));
    }

    // ── Reject whole request (reason mandatory) ──
    openDriverReject(req) {
        this.state.selectedDriverRequest = req;
        this.state.driverRejectReason = '';
        this.state.driverActionError = null;
        this.state.driverRejectModal = true;
    }
    async confirmDriverReject() {
        const req = this.state.selectedDriverRequest;
        if (!req) return;
        if (!(this.state.driverRejectReason || '').trim()) {
            this.state.driverActionError = this.tr('A rejection reason is required.');
            return;
        }
        await this._runDriverAction(
            () => this.orm.call('recycle.driver.request', 'action_reject',
                [[req.id], this.state.driverRejectReason.trim()]),
            this.tr('Request rejected — the driver was notified.'));
    }

    /** Per-document outcome — shown in every request state, never hidden. */
    driverImgLabel(st) {
        return st === 'rejected' ? this.tr('Rejected')
            : st === 'accepted' ? this.tr('Accepted')
            : this.tr('Pending');
    }
    driverImgBadge(st) {
        return 'o_ra_badge ' + (st === 'rejected' ? 'o_ra_badge_danger'
            : st === 'accepted' ? 'o_ra_badge_success' : 'o_ra_badge_info');
    }

    // ── Re-open a REJECTED request (admin changed his mind) ──
    async reactivateDriverRequest(req) {
        if (!req) return;
        if (!(await this.askConfirm(this.tr('Re-open request'), this.tr('Re-open this rejected request for review?')))) return;
        this.state.selectedDriverRequest = req;
        await this._runDriverAction(
            () => this.orm.call('recycle.driver.request', 'action_reactivate', [[req.id]]),
            this.tr('Request re-opened — it is under review again.'));
    }

    // ── Judging one document ────────────────────────────────────────────
    //
    // Marking a document unacceptable and asking the driver to replace it are
    // two separate buttons, because they are two separate acts. The reviewer
    // marks each document as they read it; only when they have finished do they
    // ask for what is missing — one message instead of one per file.
    openDriverImgReject(req, img) {
        this.state.selectedDriverRequest = req;
        this.state.driverImgReject = img;
        this.state.driverImgRejectReason = '';
        this.state.driverActionError = null;
    }
    async confirmDriverImgReject() {
        const req = this.state.selectedDriverRequest;
        const img = this.state.driverImgReject;
        if (!req || !img) return;
        await this._runDriverAction(
            () => this.orm.call('recycle.driver.request', 'action_reject_image',
                [[req.id], img.id, (this.state.driverImgRejectReason || '').trim()]),
            this.tr('Document rejected. The driver has not been told — ask for it when you are ready.'));
    }

    /** Take a rejection back, without involving the driver. */
    async acceptDriverImg(req, img) {
        if (!req || !img) return;
        this.state.selectedDriverRequest = req;
        await this._runDriverAction(
            () => this.orm.call('recycle.driver.request', 'action_accept_image',
                [[req.id], img.id]),
            this.tr('Document accepted.'));
    }

    /**
     * Stop waiting for a driver who never answered.
     *
     * The way out of the one state this flow could not leave: asking for a
     * document blocks every decision until he replies, so a driver who simply
     * never comes back left the request open for ever with no move available.
     */
    async cancelDriverReuploadRequest(req) {
        if (!req) return;
        if (!(await this.askConfirm(
            this.tr('Stop waiting'),
            this.tr('Stop waiting for this driver? The documents keep their status — you can then reject the request, but accepting it is still blocked by any rejected document.')))) return;
        this.state.selectedDriverRequest = req;
        await this._runDriverAction(
            () => this.orm.call('recycle.driver.request',
                'action_cancel_reupload_request', [[req.id]]),
            this.tr('Stopped waiting — the request is back under review.'));
    }

    /** Ask the driver for one rejected document. This is what reaches him. */
    openDriverImgRequest(req, img) {
        this.state.selectedDriverRequest = req;
        this.state.driverImgRequest = img;
        this.state.driverImgRequestReason = '';
        this.state.driverActionError = null;
    }
    async confirmDriverImgRequest() {
        const req = this.state.selectedDriverRequest;
        const img = this.state.driverImgRequest;
        if (!req || !img) return;
        await this._runDriverAction(
            () => this.orm.call('recycle.driver.request', 'action_request_reupload',
                [[req.id], img.id, (this.state.driverImgRequestReason || '').trim()]),
            this.tr('The driver was asked to re-upload this document.'));
    }

    closeDriverModals() {
        this.state.driverAcceptModal = false;
        this.state.driverRejectModal = false;
        this.state.driverImgReject = null;
        this.state.driverImgRequest = null;
        this.state.driverActionError = null;
    }

    async _runDriverAction(call, successMsg) {
        this.state.driverActionSaving = true;
        this.state.driverActionError = null;
        try {
            await call();
            this.closeDriverModals();
            this.state.driverActionSuccess = successMsg;
            const self = this;
            setTimeout(function () { self.state.driverActionSuccess = null; }, 4000);
            await this._refetchDriverRequests();
        } catch (e) {
            this.state.driverActionError = (e && e.data && e.data.message)
                || this.tr('Action failed. Please try again.');
        } finally {
            this.state.driverActionSaving = false;
        }
    }

    // ── Driver Attendance (pickup / dropoff handovers — READ ONLY) ──
    // Same warehouse + date filters as the warehouse-staff attendance screen.
    async openDriverAttendance(filterWarehouseId, dateStr) {
        this.state.openSection = null;
        if (typeof filterWarehouseId !== 'number') { filterWarehouseId = null; }
        this.state.driverAttWHFilter = filterWarehouseId || null;
        if (dateStr !== undefined) { this.state.driverAttDate = dateStr; }
        this._navigate('driver_attendance');
        if (!this.state.warehouses.length) {
            this.state.warehouses = await this.orm.searchRead('recycle.warehouse', [['state', '=', 'active']], ['id', 'name']);
        }
        await this._loadDriverHandovers();
    }
    async _loadDriverHandovers() {
        this.state.loading = true;
        const domain = [];
        if (this.state.driverAttDate) { domain.push(['work_date', '=', this.state.driverAttDate]); }
        if (this.state.driverAttWHFilter) { domain.push(['warehouse_id', '=', this.state.driverAttWHFilter]); }
        try {
            this.state.driverHandovers = await this.orm.searchRead(
                'recycle.truck.handover', domain,
                ['id', 'driver_name', 'truck_id', 'shift_id', 'warehouse_id',
                 'work_date', 'picked_up_at', 'dropped_off_at', 'dropoff_reason',
                 'late_minutes', 'state'],
                { order: 'work_date desc', limit: 300 });
        } catch (e) { this.state.driverHandovers = []; }
        // Same 4-card summary design as warehouse-staff attendance, with the
        // driver equivalents: Present = picked up, Late = late dropoff,
        // Missed = missed pickup, Total.
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
    async setDriverAttWHFilter(ev) {
        const val = (ev.target.tagName === 'SELECT' || ev.target.value !== undefined)
            ? ev.target.value : (ev.target.dataset && ev.target.dataset.filter);
        this.state.driverAttWHFilter = val ? parseInt(val) : null;
        await this._loadDriverHandovers();
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

    // ── Drivers screen (Trucks section): ACCEPTED drivers only ──
    // Search by name + filter by shift (or shiftless) + filter by whether
    // the driver already reserved a truck. The truck link is joined
    // client-side from recycle.driver.assignment (fleet-sized data).
    async openDriversList() {
        this.state.openSection = null;
        this._navigate('drivers_list');
        this.state.driverDetail = null;
        this.state.driverSearch = '';
        this.state.driverShiftFilter = '';
        this.state.driverTruckFilter = '';
        this.state.driverWHFilter = '';
        await this._reloadDriversList();
    }

    /** Refetch the roster WITHOUT moving the user or clearing their filters. */
    async _reloadDriversList() {
        this.state.loading = true;
        try {
            if (!this.state.warehouses.length) {
                this.state.warehouses = await this.orm.searchRead(
                    'recycle.warehouse', [], ['id', 'name']);
            }
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
        } finally {
            this.state.loading = false;
        }
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
        const wh = this.state.driverWHFilter;
        return this.state.drivers.filter((d) => {
            if (q && !(d.name || '').toLowerCase().includes(q)) return false;
            if (wh && (!d.warehouse_id || d.warehouse_id[0] !== Number(wh))) return false;
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
    setDriverWHFilter(ev) { this.state.driverWHFilter = ev.target.value; }

    // ── Driver detail modal: block / unblock / relocate / export PDF ──
    // ─── The collector's own page ───────────────────────────────
    //
    // Was a modal. A modal has no room for the truck history and cannot be
    // reached or shared on its own, and on a phone it covered the list it was
    // opened from. Delivery drivers get a page; there is no reason the other
    // half of the fleet should be read differently.
    async openDriverDetail(d) {
        this.state.driverDetail = d;
        this.state.driverBlockModal = false;
        this.state.driverBlockReason = '';
        this.state.driverMoveOpen = false;
        this.state.driverMoveWH = '';
        this.state.driverActionError = null;
        this.state.driverActionSuccess = null;
        this._navigate('collection_driver_detail');
        await this._loadCollectorTruckHistory(d.id);
    }
    closeDriverDetail() {
        this.state.driverDetail = null;
        this.goBack();
    }

    /** Every truck this collector has held, newest first. */
    async _loadCollectorTruckHistory(requestId) {
        this.state.ddHistoryLoading = true;
        this.state.ddHistory = [];
        try {
            this.state.ddHistory = await this.orm.searchRead(
                'recycle.truck.assignment.history',
                [['driver_request_id', '=', requestId]],
                ['truck_id', 'truck_plate', 'warehouse_id', 'assigned_at',
                 'released_at', 'release_reason', 'duration_days', 'is_current'],
                { order: 'assigned_at desc, id desc' });
        } catch (e) {
            this.state.driverActionError = this._err(e);
        }
        this.state.ddHistoryLoading = false;
    }

    async _runDriverRosterAction(call, successMsg) {
        this.state.driverActionSaving = true;
        this.state.driverActionError = null;
        try {
            await call();
            this.state.driverActionSuccess = successMsg;
            const self = this;
            setTimeout(function () { self.state.driverActionSuccess = null; }, 4000);
            this.state.driverBlockModal = false;
            this.state.driverMoveOpen = false;
            // Stay on the driver, and re-point at the FRESH row: blocking
            // changes the badge and takes the truck back, and the page shows
            // both. Re-entering the list here would throw whoever acted out of
            // the record they were working on.
            const openId = this.state.driverDetail && this.state.driverDetail.id;
            await this._reloadDriversList();
            if (openId) {
                this.state.driverDetail =
                    this.state.drivers.find((x) => x.id === openId) || null;
                await this._loadCollectorTruckHistory(openId);
            }
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
        await this._runDriverRosterAction(
            () => this.orm.call('recycle.driver.request', 'action_block',
                [[d.id], (this.state.driverBlockReason || '').trim() || false]),
            this.tr('Driver blocked — he was signed out of the app.'));
    }
    async unblockDriver() {
        const d = this.state.driverDetail;
        if (!d) return;
        await this._runDriverRosterAction(
            () => this.orm.call('recycle.driver.request', 'action_unblock', [[d.id]]),
            this.tr('Driver unblocked — he can sign in again.'));
    }

    openDriverMove() {
        this.state.driverMoveOpen = true;
        this.state.driverMoveWH = '';
        this.state.driverActionError = null;
    }
    async confirmDriverMove() {
        const d = this.state.driverDetail;
        if (!d || !this.state.driverMoveWH) return;
        await this._runDriverRosterAction(
            () => this.orm.call('recycle.driver.request', 'action_change_warehouse',
                [[d.id], Number(this.state.driverMoveWH)]),
            this.tr('Driver moved to the new warehouse.'));
    }

    exportDriverPdf(d) {
        // The driver FILE, not the old summary sheet: same document the
        // delivery side prints, carrying the person's details plus every truck
        // they have held with the dates. That history is the reason the export
        // is asked for at all — after an accident, a fuel discrepancy or a
        // complaint — and the old report had no idea the history existed.
        this.printCollectionDriverFile(d);
    }

    // ── Assign driver to truck (Trucks section) ──
    // Shift FIRST → the server returns the trucks still free in that shift
    // and that shift's truckless drivers; both re-checked on save.
    async openAssignDriver() {
        this.state.openSection = null;
        this._navigate('assign_driver');
        this.state.assignShiftId = '';
        this.state.assignWHFilter = '';
        this.state.assignOptions = { trucks: [], drivers: [] };
        this.state.assignTruckId = null;
        this.state.assignDriverKey = '';
        this.state.assignError = null;
        this.state.assignSuccess = null;
        await this._loadDriverShifts();
        if (!this.state.warehouses.length) {
            this.state.warehouses = await this.orm.searchRead(
                'recycle.warehouse', [], ['id', 'name']);
        }
    }

    async onAssignShiftChange(ev) {
        this.state.assignShiftId = ev.target.value;
        await this._loadAssignOptions();
    }
    async onAssignWHChange(ev) {
        this.state.assignWHFilter = ev.target.value;
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
                [Number(this.state.assignShiftId),
                 this.state.assignWHFilter ? Number(this.state.assignWHFilter) : false]);
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

    // ─── Shipments ────────────────────────────────────────
    // Search/state-filter now go server-side (a real domain query) instead
    // of filtering only whatever page happens to be loaded in memory — the
    // old client-side filter could never find a shipment older than the
    // most recent 200. Scrolling to the bottom of the list loads the next
    // 200 (older) rows via a cursor on `id` (no visible page-number UI).
    SHIPMENTS_PAGE_SIZE = 200;

    _shipmentDomain() {
        const domain = [["recycle_archived", "=", false]];
        if (this.state.filterWarehouseId) domain.push(["warehouse_id", "=", this.state.filterWarehouseId]);
        if (this.state.shipmentStateFilter) domain.push(["state", "=", this.state.shipmentStateFilter]);
        const f = (this.state.shipmentFilter || '').trim();
        if (f) {
            domain.push("|", ["name", "ilike", f], "|", ["driver_name", "ilike", f], ["warehouse_id.name", "ilike", f]);
        }
        return domain;
    }

    async _refetchShipments() {
        this.state.loading = true;
        this.state.shipments = [];
        this.state.shipmentsHasMore = true;
        try {
            this.state.shipments = await this.orm.searchRead(
                "recycle.shipment", this._shipmentDomain(),
                ["id", "name", "warehouse_id", "driver_name", "priority",
                 "expected_weight", "actual_weight", "weight_diff_pct",
                 "state", "received_at", "receiver_user_id",
                 "sorted_at", "sorter_user_id",
                 "stored_at", "stored_by",
                 "total_good_qty", "total_damaged_qty", "damage_pct"],
                { order: "id desc", limit: this.SHIPMENTS_PAGE_SIZE }
            );
            this.state.shipmentsHasMore = this.state.shipments.length === this.SHIPMENTS_PAGE_SIZE;
        } finally {
            this.state.loading = false;
        }
    }

    async loadMoreShipments() {
        if (this.state.view !== 'shipments_list') return;
        if (!this.state.shipmentsHasMore || this.state.shipmentsLoadingMore || this.state.loading) return;
        this.state.shipmentsLoadingMore = true;
        try {
            const lastId = this.state.shipments.length
                ? this.state.shipments[this.state.shipments.length - 1].id : 0;
            const domain = this._shipmentDomain().concat(lastId ? [["id", "<", lastId]] : []);
            const more = await this.orm.searchRead(
                "recycle.shipment", domain,
                ["id", "name", "warehouse_id", "driver_name", "priority",
                 "expected_weight", "actual_weight", "weight_diff_pct",
                 "state", "received_at", "receiver_user_id",
                 "sorted_at", "sorter_user_id",
                 "stored_at", "stored_by",
                 "total_good_qty", "total_damaged_qty", "damage_pct"],
                { order: "id desc", limit: this.SHIPMENTS_PAGE_SIZE }
            );
            this.state.shipments = this.state.shipments.concat(more);
            this.state.shipmentsHasMore = more.length === this.SHIPMENTS_PAGE_SIZE;
        } catch (e) { /* silent — the list simply stops growing, no error UI needed */ }
        this.state.shipmentsLoadingMore = false;
    }

    onShipmentSearchInput(ev) {
        this.state.shipmentFilter = ev.target.value;
        clearTimeout(this._shipmentSearchTimer);
        this._shipmentSearchTimer = setTimeout(() => this._refetchShipments(), 400);
    }

    onShipmentStateFilterChange(ev) {
        this.state.shipmentStateFilter = ev.target.value;
        this._refetchShipments();
    }

    async openShipments(filterWarehouseId, filterWarehouseName) {
        if (typeof filterWarehouseId !== "number") { filterWarehouseId = null; filterWarehouseName = null; }
        this.state.filterWarehouseId = filterWarehouseId;
        this.state.filterWarehouseName = filterWarehouseName;
        if (!filterWarehouseId) this.state.shipmentWHFilter = null;
        this.state.shipmentFilter = '';
        this.state.shipmentStateFilter = '';
        this._navigate("shipments_list");
        if (!this.state.warehouses.length) {
            this.state.warehouses = await this.orm.searchRead("recycle.warehouse", [["state", "=", "active"]], ["id", "name"]);
        }
        await this._refetchShipments();
    }

    async openWarehouseShipments() {
        const wh = this.state.selectedWarehouse;
        if (!wh) return;
        await this.openShipments(wh.id, wh.name);
    }

    get filteredShipments() {
        // Filtering now happens server-side (see _shipmentDomain); this
        // getter is kept only so the existing templates don't need to change.
        return this.state.shipments;
    }

    async openShipmentDetail(s) {
        this.state.selectedShipment = s;
        this._navigate("shipment_detail");
        this.state.loading = true;
        this.state.selectedShipmentLines = await this.orm.searchRead(
            "recycle.shipment.line",
            [["shipment_id", "=", s.id]],
            ["product_id", "quantity", "condition", "uom_id"]
        );
        this.state.selectedShipmentExpectedLines = await this.orm.searchRead(
            "recycle.shipment.expected.line",
            [["shipment_id", "=", s.id]],
            ["product_id", "expected_qty", "uom_id"]
        );
        this.state.loading = false;
    }

    // ─── Orders ───────────────────────────────────────────
    // Same server-side search + scroll-to-load-more pattern as Shipments above.
    ORDERS_PAGE_SIZE = 200;

    _orderDomain() {
        const domain = [["recycle_archived", "=", false]];
        if (this.state.filterWarehouseId) domain.push(["warehouse_id", "=", this.state.filterWarehouseId]);
        if (this.state.orderStateFilter) domain.push(["state", "=", this.state.orderStateFilter]);
        const f = (this.state.orderFilter || '').trim();
        if (f) {
            domain.push("|", ["name", "ilike", f], "|", ["customer_name", "ilike", f], ["warehouse_id.name", "ilike", f]);
        }
        return domain;
    }

    async _refetchOrders() {
        this.state.loading = true;
        this.state.orders = [];
        this.state.ordersHasMore = true;
        try {
            this.state.orders = await this.orm.searchRead(
                "recycle.order", this._orderDomain(),
                ["id", "name", "customer_name", "owner_name", "customer_email",
                 "warehouse_id", "state", "amount_total", "total_weight",
                 "invoice_number", "source", "output_user_id",
                 "is_split_part", "part_count", "part_sequence",
                 "manager_approval", "backend_order_id"],
                { order: "id desc", limit: this.ORDERS_PAGE_SIZE }
            );
            this.state.ordersHasMore = this.state.orders.length === this.ORDERS_PAGE_SIZE;
        } finally {
            this.state.loading = false;
        }
    }

    async loadMoreOrders() {
        if (this.state.view !== 'orders_list') return;
        if (!this.state.ordersHasMore || this.state.ordersLoadingMore || this.state.loading) return;
        this.state.ordersLoadingMore = true;
        try {
            const lastId = this.state.orders.length
                ? this.state.orders[this.state.orders.length - 1].id : 0;
            const domain = this._orderDomain().concat(lastId ? [["id", "<", lastId]] : []);
            const more = await this.orm.searchRead(
                "recycle.order", domain,
                ["id", "name", "customer_name", "owner_name", "customer_email",
                 "warehouse_id", "state", "amount_total", "total_weight",
                 "invoice_number", "source", "output_user_id",
                 "is_split_part", "part_count", "part_sequence",
                 "manager_approval", "backend_order_id"],
                { order: "id desc", limit: this.ORDERS_PAGE_SIZE }
            );
            this.state.orders = this.state.orders.concat(more);
            this.state.ordersHasMore = more.length === this.ORDERS_PAGE_SIZE;
        } catch (e) { /* silent — the list simply stops growing, no error UI needed */ }
        this.state.ordersLoadingMore = false;
    }

    onOrderSearchInput(ev) {
        this.state.orderFilter = ev.target.value;
        clearTimeout(this._orderSearchTimer);
        this._orderSearchTimer = setTimeout(() => this._refetchOrders(), 400);
    }

    onOrderStateFilterChange(ev) {
        this.state.orderStateFilter = ev.target.value;
        this._refetchOrders();
    }

    async openOrders(filterWarehouseId, filterWarehouseName) {
        if (typeof filterWarehouseId !== "number") { filterWarehouseId = null; filterWarehouseName = null; }
        this.state.filterWarehouseId = filterWarehouseId;
        this.state.filterWarehouseName = filterWarehouseName;
        if (!filterWarehouseId) this.state.orderWHFilter = null;
        this.state.orderFilter = '';
        this.state.orderStateFilter = '';
        this._navigate("orders_list");
        if (!this.state.warehouses.length) {
            this.state.warehouses = await this.orm.searchRead("recycle.warehouse", [["state", "=", "active"]], ["id", "name"]);
        }
        await this._refetchOrders();
    }

    async openWarehouseOrders() {
        const wh = this.state.selectedWarehouse;
        if (!wh) return;
        await this.openOrders(wh.id, wh.name);
    }

    get filteredOrders() {
        // Filtering now happens server-side (see _orderDomain); this getter
        // is kept only so the existing templates don't need to change.
        return this.state.orders;
    }

    async openOrderDetail(o) {
        this.state.selectedOrder = o;
        this._navigate("order_detail");
        this.state.loading = true;
        this.state.reassignError = null;
        this.state.reassignSuccess = null;
        this.state.reassignWarehouseId = '';
        this.state.reassignCandidates = [];
        this.state.selectedOrderLines = await this.orm.searchRead(
            "recycle.order.line",
            [["order_id", "=", o.id]],
            ["product_id", "quantity", "price_unit", "subtotal"]
        );
        if (this.canReassignOrder(o)) {
            await this._loadReassignCandidates(o);
        }
        this.state.loading = false;
    }

    /**
     * A split part may be re-routed only by the admin, and only before the
     * decision is taken — mirrors the guard the Odoo model enforces, so the
     * button is never shown for a move the server would refuse.
     */
    canReassignOrder(o) {
        return !!o && o.is_split_part
            && o.state === 'pending'
            && o.manager_approval === 'pending';
    }

    /**
     * Active warehouses this part could move to: never its current one, and
     * never one already holding a sibling part — the split may be re-routed,
     * not merged or grown.
     */
    async _loadReassignCandidates(o) {
        const currentWhId = Array.isArray(o.warehouse_id) ? o.warehouse_id[0] : o.warehouse_id;
        let siblingWhIds = [];
        if (o.backend_order_id) {
            const siblings = await this.orm.searchRead(
                "recycle.order",
                [["backend_order_id", "=", o.backend_order_id]],
                ["warehouse_id"]
            );
            siblingWhIds = siblings
                .map((s) => (Array.isArray(s.warehouse_id) ? s.warehouse_id[0] : s.warehouse_id))
                .filter((id) => id && id !== currentWhId);
        }
        const taken = new Set([currentWhId, ...siblingWhIds]);
        const active = await this.orm.searchRead(
            "recycle.warehouse", [["state", "=", "active"]], ["id", "name"]
        );
        this.state.reassignCandidates = active.filter((w) => !taken.has(w.id));
    }

    /** Move this split part to the chosen warehouse (admin decision). */
    async reassignOrderPart() {
        const o = this.state.selectedOrder;
        if (!o || !this.canReassignOrder(o)) return;
        const whId = parseInt(this.state.reassignWarehouseId, 10);
        if (!whId) {
            this.state.reassignError = this.tr('Choose a warehouse to move this part to.');
            return;
        }
        this.state.reassignBusy = true;
        this.state.reassignError = null;
        this.state.reassignSuccess = null;
        try {
            // Runs as the admin; the model enforces the full rule set (split
            // only, still pending, target holds the quantity, no sibling merge).
            await this.orm.call(
                "recycle.order", "action_admin_reassign_warehouse", [[o.id], whId]
            );
            // Re-read the moved part so the detail reflects its new warehouse,
            // distance-driven delivery and total.
            const [fresh] = await this.orm.searchRead(
                "recycle.order", [["id", "=", o.id]],
                ["id", "name", "customer_name", "owner_name", "customer_email",
                 "warehouse_id", "state", "amount_total", "total_weight",
                 "invoice_number", "source", "output_user_id",
                 "is_split_part", "part_count", "part_sequence",
                 "manager_approval", "backend_order_id"]
            );
            if (fresh) this.state.selectedOrder = fresh;
            this.state.reassignWarehouseId = '';
            this.state.reassignSuccess = this.tr('Order part reassigned.');
            setTimeout(() => { this.state.reassignSuccess = null; }, 4000);
            await this._loadReassignCandidates(this.state.selectedOrder);
        } catch (e) {
            this.state.reassignError = this._err(e);
        } finally {
            this.state.reassignBusy = false;
        }
    }

    async printOrderReport(orderId) {
        await this.actionService.doAction(
            'recycle_warehouse.action_report_order_invoice',
            { additionalContext: { active_id: orderId, active_ids: [orderId], active_model: 'recycle.order' } }
        );
    }

    // ─── Jobs & HR ────────────────────────────────────────
    openJobsHR() {
        this.state.openSection = null;
        this._navigate("jobs_hr");
    }

    async openJobsList() {
        this._navigate("jobs_list");
        this.state.loading = true;
        this.state.jobs = await this.orm.searchRead(
            "hr.job", [],
            ["id", "name", "no_of_recruitment", "no_of_hired_employee",
             "recycle_job_type", "recycle_publish", "recycle_description"],
            { order: "name asc" }
        );
        this.state.loading = false;
    }

    openJobDetail(job) {
        this.state.selectedJob = { ...job };
        this.state.jobEditMode = false;
        this.state.jobError = null;
        this._navigate("job_detail");
    }

    startEditJob() {
        const j = this.state.selectedJob;
        this.state.jobForm = {
            name: j.name || '',
            no_of_recruitment: j.no_of_recruitment || 1,
            recycle_job_type: j.recycle_job_type || 'employee',
            recycle_publish: j.recycle_publish || false,
            recycle_description: j.recycle_description || '',
        };
        this.state.jobEditMode = true;
        this.state.jobError = null;
    }

    cancelEditJob() {
        this.state.jobEditMode = false;
        this.state.jobError = null;
    }

    async saveEditJob() {
        const f = this.state.jobForm;
        if (!f.name.trim()) { this.state.jobError = "Job name is required."; return; }
        this.state.jobSaving = true;
        this.state.jobError = null;
        try {
            await this.orm.write("hr.job", [this.state.selectedJob.id], {
                name: f.name.trim(),
                no_of_recruitment: parseInt(f.no_of_recruitment) || 1,
                recycle_job_type: f.recycle_job_type,
                recycle_publish: f.recycle_publish,
                recycle_description: f.recycle_description || '',
            });
            const updated = await this.orm.searchRead(
                "hr.job", [["id", "=", this.state.selectedJob.id]],
                ["id", "name", "no_of_recruitment", "no_of_hired_employee", "recycle_job_type", "recycle_publish", "recycle_description"]
            );
            if (updated.length) {
                this.state.selectedJob = updated[0];
                const idx = this.state.jobs.findIndex(j => j.id === updated[0].id);
                if (idx >= 0) this.state.jobs[idx] = updated[0];
            }
            this.state.jobEditMode = false;
            this.notification.add("Job updated successfully.", { type: "success", sticky: false });
        } catch (e) {
            this.state.jobError = e.message || "Save failed.";
        }
        this.state.jobSaving = false;
    }

    startCreateJob() {
        this.state.jobForm = { name: '', no_of_recruitment: 1, recycle_job_type: 'employee', recycle_publish: false, recycle_description: '' };
        this.state.jobError = null;
        this.state.jobSaving = false;
        this._navigate("job_create");
    }

    async saveNewJob() {
        const f = this.state.jobForm;
        if (!f.name.trim()) { this.state.jobError = "Job name is required."; return; }
        this.state.jobSaving = true;
        this.state.jobError = null;
        try {
            await this.orm.create("hr.job", [{
                name: f.name.trim(),
                no_of_recruitment: parseInt(f.no_of_recruitment) || 1,
                recycle_job_type: f.recycle_job_type,
                recycle_publish: f.recycle_publish,
                recycle_description: f.recycle_description || '',
            }]);
            this.notification.add("Job created successfully.", { type: "success", sticky: false });
            await this.openJobsList();
        } catch (e) {
            this.state.jobError = e.message || "Create failed.";
        } finally {
            this.state.jobSaving = false;
        }
    }

    async togglePublishJob(job) {
        const newVal = !job.recycle_publish;
        await this.orm.write("hr.job", [job.id], { recycle_publish: newVal });
        const idx = this.state.jobs.findIndex(j => j.id === job.id);
        if (idx >= 0) this.state.jobs[idx] = { ...this.state.jobs[idx], recycle_publish: newVal };
        if (this.state.selectedJob && this.state.selectedJob.id === job.id) {
            this.state.selectedJob = { ...this.state.selectedJob, recycle_publish: newVal };
        }
        this.notification.add(
            newVal ? "Job published on website." : "Job unpublished.",
            { type: "success", sticky: false }
        );
    }

    // ─── Applicants ───────────────────────────────────────
    APPLICANTS_FIELDS = ["id", "partner_name", "email_from", "partner_phone",
        "job_id", "recycle_state", "recycle_stage_status", "stage_id",
        "recycle_email", "recycle_phone", "recycle_account_deleted",
        "recycle_national_id", "recycle_interview_datetime", "recycle_interview_notes",
        "recycle_cover_letter"];

    _applicantsDomain() {
        const domain = [["recycle_state", "not in", ["accepted", "rejected"]]];
        if (this.state.applicantJobFilter) domain.push(["job_id", "=", this.state.applicantJobFilter]);
        return domain;
    }

    async openApplicantsList(jobId, jobName) {
        if (typeof jobId !== "number") { jobId = null; jobName = null; }
        this.state.applicantJobFilter = jobId;
        this.state.applicantJobName = jobName;
        this._navigate("applicants_list");
        this.state.loading = true;
        this.state.applicants = [];
        this.state.applicantsHasMore = true;
        try {
            const pager = makePager(this.orm, { model: "hr.applicant", fields: this.APPLICANTS_FIELDS });
            const { rows, hasMore } = await pager.fetchFirst(this._applicantsDomain());
            this.state.applicants = rows;
            this.state.applicantsHasMore = hasMore;
        } finally {
            this.state.loading = false;
        }
    }

    async loadMoreApplicants() {
        if (this.state.view !== 'applicants_list') return;
        if (!this.state.applicantsHasMore || this.state.applicantsLoadingMore || this.state.loading) return;
        this.state.applicantsLoadingMore = true;
        try {
            const lastId = this.state.applicants.length
                ? this.state.applicants[this.state.applicants.length - 1].id : 0;
            const pager = makePager(this.orm, { model: "hr.applicant", fields: this.APPLICANTS_FIELDS });
            const { rows, hasMore } = await pager.fetchMore(this._applicantsDomain(), lastId);
            this.state.applicants = this.state.applicants.concat(rows);
            this.state.applicantsHasMore = hasMore;
        } catch (e) { /* silent */ }
        this.state.applicantsLoadingMore = false;
    }

    async openApplicantDetail(app) {
        // Full applicant processing in the custom Admin Home design.
        this._navigate("applicant_detail");
        this.state.applicantDetailLoading = true;
        this.state.applicantActionError = null;
        this.state.applicantActionSuccess = null;
        this.state.applicantInterviewForm = { when: '', location: '', notes: '' };
        this.state.applicantAccountForm = { warehouse_id: null, role: '' };
        this.state.selectedApplicant = { ...app };
        this.state.applicantAttachments = [];
        this.state.applicantStageLog = [];
        try {
            const recs = await this.orm.searchRead(
                "hr.applicant", [["id", "=", app.id]],
                this._applicantFields(),
                { context: { active_test: false } }
            );
            if (recs.length) this.state.selectedApplicant = recs[0];
            // Recruitment stages (ordered pipeline).
            this.state.recruitmentStages = await this.orm.searchRead(
                "hr.recruitment.stage", [], ["id", "name", "sequence"],
                { order: "sequence asc, id asc" }
            );
            // Attachments (CV, certificates…)
            this.state.applicantAttachments = await this.orm.searchRead(
                "ir.attachment",
                [["res_model", "=", "hr.applicant"], ["res_id", "=", app.id]],
                ["id", "name"], { order: "id desc" }
            );
            // Per-stage approval/advance history (audit trail).
            this.state.applicantStageLog = await this.orm.searchRead(
                "recycle.applicant.stage.log", [["applicant_id", "=", app.id]],
                ["id", "stage_id", "next_stage_id", "decided_by", "decided_at"],
                { order: "decided_at desc, id desc" }
            );
            if (!this.state.warehouses.length) {
                this.state.warehouses = await this.orm.searchRead(
                    "recycle.warehouse", [], ["id", "name", "manager_user_id"]);
            }
        } catch (e) {
            this.state.applicantActionError = this.tr('Could not load the application.');
        }
        this.state.applicantDetailLoading = false;
    }

    _applicantFields() {
        return ["id", "partner_name", "recycle_name", "email_from", "recycle_email",
            "partner_phone", "recycle_phone", "recycle_national_id",
            "job_id", "recycle_job_type", "recycle_state", "recycle_stage_status",
            "stage_id", "recycle_is_last_stage",
            "recycle_cover_letter", "recycle_profile_url",
            "recycle_interview_datetime", "recycle_interview_location",
            "recycle_interview_notes", "recycle_interview_sent_at", "employee_user_id",
            "recycle_role", "recycle_warehouse_id", "recycle_account_deleted",
            "recycle_in_pool", "recycle_pool_date",
            "recycle_is_interview_stage", "recycle_reject_reason"];
    }

    // Current stage index within the ordered pipeline (for the progress bar).
    get applicantStageIndex() {
        const sid = this.state.selectedApplicant && this.state.selectedApplicant.stage_id;
        const id = Array.isArray(sid) ? sid[0] : sid;
        return this.state.recruitmentStages.findIndex(s => s.id === id);
    }

    attachmentUrl(attId) {
        return `/web/content/${attId}?download=true`;
    }

    async _reloadApplicant() {
        const id = this.state.selectedApplicant && this.state.selectedApplicant.id;
        if (!id) return;
        const recs = await this.orm.searchRead(
            "hr.applicant", [["id", "=", id]], this._applicantFields(),
            { context: { active_test: false } }
        );
        if (recs.length) this.state.selectedApplicant = recs[0];
        this.state.applicantStageLog = await this.orm.searchRead(
            "recycle.applicant.stage.log", [["applicant_id", "=", id]],
            ["id", "stage_id", "next_stage_id", "decided_by", "decided_at"],
            { order: "decided_at desc, id desc" }
        );
    }

    // ─── Talent pool ──────────────────────────────────────
    async applicantAddToPool() {
        await this._applicantAction("action_recycle_add_to_pool", [],
            this.tr('Added to the talent pool.'));
    }
    async applicantRemoveFromPool() {
        await this._applicantAction("action_recycle_remove_from_pool", [],
            this.tr('Removed from the talent pool.'));
    }

    TALENT_POOL_FIELDS = ["id", "partner_name", "recycle_name", "email_from", "recycle_email",
        "partner_phone", "recycle_phone", "job_id", "recycle_pool_date",
        "recycle_account_deleted"];

    _talentPoolDomain() {
        const domain = [["recycle_in_pool", "=", true], ["recycle_account_deleted", "!=", true]];
        const q = (this.state.talentPoolSearch || '').trim();
        if (q) {
            domain.push("|", "|", ["partner_name", "ilike", q], ["recycle_name", "ilike", q], "|",
                ["email_from", "ilike", q], ["recycle_email", "ilike", q]);
        }
        return domain;
    }

    async _refetchTalentPool() {
        this.state.talentPoolLoading = true;
        this.state.talentPool = [];
        this.state.talentPoolHasMore = true;
        try {
            const pager = makePager(this.orm, { model: "hr.applicant", fields: this.TALENT_POOL_FIELDS });
            const { rows, hasMore } = await pager.fetchFirst(this._talentPoolDomain());
            this.state.talentPool = rows;
            this.state.talentPoolHasMore = hasMore;
        } finally {
            this.state.talentPoolLoading = false;
        }
    }

    async openTalentPool() {
        this._navigate("talent_pool");
        this.state.talentPoolSearch = '';
        await this._refetchTalentPool();
    }

    onTalentPoolSearchInput(ev) {
        this.state.talentPoolSearch = ev.target.value;
        clearTimeout(this._talentPoolSearchTimer);
        this._talentPoolSearchTimer = setTimeout(() => this._refetchTalentPool(), 400);
    }

    async loadMoreTalentPool() {
        if (this.state.view !== 'talent_pool') return;
        if (!this.state.talentPoolHasMore || this.state.talentPoolLoadingMore || this.state.talentPoolLoading) return;
        this.state.talentPoolLoadingMore = true;
        try {
            const lastId = this.state.talentPool.length
                ? this.state.talentPool[this.state.talentPool.length - 1].id : 0;
            const pager = makePager(this.orm, { model: "hr.applicant", fields: this.TALENT_POOL_FIELDS });
            const { rows, hasMore } = await pager.fetchMore(this._talentPoolDomain(), lastId);
            this.state.talentPool = this.state.talentPool.concat(rows);
            this.state.talentPoolHasMore = hasMore;
        } catch (e) { /* silent */ }
        this.state.talentPoolLoadingMore = false;
    }

    get filteredTalentPool() {
        // Filtering now happens server-side (see _talentPoolDomain).
        return this.state.talentPool;
    }
    async removeFromPoolRow(app) {
        try {
            await this.orm.call("hr.applicant", "action_recycle_remove_from_pool", [[app.id]]);
            this.notification.add(this.tr('Removed from the talent pool.'), { type: "success" });
            await this.openTalentPool();
        } catch (e) {
            this.notification.add((e && e.data && e.data.message) || this.tr('Action failed.'), { type: "danger" });
        }
    }

    // ─── Recruitment stage management (add / delete / reorder) ─────────
    async openStagesList() {
        this._navigate("stages_list");
        this.state.stageError = null;
        this.state.stageSuccess = null;
        this.state.stageForm = { name: '', sequence: 10, is_interview: false, description: '' };
        await this._loadStages();
    }
    async _loadStages() {
        this.state.stagesList = await this.orm.searchRead(
            "hr.recruitment.stage", [],
            ["id", "name", "sequence", "recycle_is_interview", "recycle_description"],
            { order: "sequence asc, id asc" });
    }
    async addStage() {
        const f = this.state.stageForm;
        if (!f.name.trim()) { this.state.stageError = this.tr('Stage name is required.'); return; }
        this.state.stageSaving = true;
        this.state.stageError = null;
        try {
            await this.orm.create("hr.recruitment.stage", [{
                name: f.name.trim(),
                sequence: parseInt(f.sequence, 10) || 10,
                recycle_is_interview: !!f.is_interview,
                // Description is only meaningful for non-interview stages.
                recycle_description: (!f.is_interview && f.description) ? f.description : false,
            }]);
            this.state.stageForm = { name: '', sequence: 10, is_interview: false, description: '' };
            this.state.stageSuccess = this.tr('Stage added.');
            await this._loadStages();
            setTimeout(() => { this.state.stageSuccess = null; }, 2000);
        } catch (e) {
            this.state.stageError = (e && e.data && e.data.message) || this.tr('Failed to add stage.');
        }
        this.state.stageSaving = false;
    }
    // Toggle a stage's interview flag directly from the list.
    async toggleStageInterview(stage) {
        try {
            await this.orm.write("hr.recruitment.stage", [stage.id],
                { recycle_is_interview: !stage.recycle_is_interview });
            await this._loadStages();
        } catch (e) {
            this.notification.add(this.tr('Action failed.'), { type: "danger" });
        }
    }

    // ─── Reject with reason (mini dialog) ─────────────────────────────
    openRejectDialog() {
        this.state.rejectDialog = true;
        this.state.rejectReason = '';
    }
    cancelRejectDialog() { this.state.rejectDialog = null; }
    async confirmReject() {
        const reason = this.state.rejectReason || '';
        this.state.rejectDialog = null;
        await this._applicantAction("action_recycle_web_reject", [reason || false],
            this.tr('Stage rejected.'));
    }
    async deleteStage(stage) {
        const ok = await this.askConfirm(this.tr('Delete stage'), this.tr('Delete this stage? Applications in it may be affected.'));
        if (!ok) return;
        try {
            await this.orm.unlink("hr.recruitment.stage", [stage.id]);
            this.notification.add(this.tr('Stage deleted.'), { type: "success" });
            await this._loadStages();
        } catch (e) {
            this.notification.add((e && e.data && e.data.message) || this.tr('Failed to delete stage.'), { type: "danger" });
        }
    }
    async moveStage(stage, dir) {
        const list = this.state.stagesList;
        const i = list.findIndex(s => s.id === stage.id);
        const j = i + dir;
        if (i < 0 || j < 0 || j >= list.length) return;
        const a = list[i], b = list[j];
        // Swap sequences to reorder.
        try {
            await this.orm.write("hr.recruitment.stage", [a.id], { sequence: b.sequence });
            await this.orm.write("hr.recruitment.stage", [b.id], { sequence: a.sequence });
            await this._loadStages();
        } catch (e) {
            this.notification.add(this.tr('Failed to reorder stages.'), { type: "danger" });
        }
    }

    async _applicantAction(method, args, successMsg) {
        this.state.applicantSaving = true;
        this.state.applicantActionError = null;
        this.state.applicantActionSuccess = null;
        try {
            const res = await this.orm.call("hr.applicant", method,
                [[this.state.selectedApplicant.id]].concat(args || []));
            await this._reloadApplicant();
            this.state.applicantActionSuccess = successMsg || this.tr('Done.');
            this.state.applicantSaving = false;
            setTimeout(() => { this.state.applicantActionSuccess = null; }, 3500);
            return res;
        } catch (e) {
            this.state.applicantSaving = false;
            const msg = (e && e.data && e.data.message) || (e && e.message) || String(e);
            this.state.applicantActionError = msg;
            setTimeout(() => { this.state.applicantActionError = null; }, 4500);
            return null;
        }
    }

    // Stage pipeline
    async applicantApproveStage() {
        await this._applicantAction("action_recycle_stage_approve", [],
            this.tr('Stage approved.'));
    }
    async applicantRejectStage() {
        await this._applicantAction("action_recycle_stage_reject", [],
            this.tr('Stage rejected.'));
    }
    async applicantAdvanceStage() {
        await this._applicantAction("action_recycle_advance_stage", [],
            this.tr('Moved to the next stage.'));
    }

    // Quick state (Applied / Interview / Accepted / Rejected)
    async applicantSetState(newState) {
        await this._applicantAction("write", [{ recycle_state: newState }],
            this.tr('Status updated.'));
    }

    // Interview scheduling (sets fields + emails the applicant)
    async applicantScheduleInterview() {
        const f = this.state.applicantInterviewForm;
        if (!f.when) {
            this.state.applicantActionError = this.tr('Please pick an interview date and time.');
            setTimeout(() => { this.state.applicantActionError = null; }, 4500);
            return;
        }
        // Convert the datetime-local value ("YYYY-MM-DDTHH:MM") to Odoo format.
        const when = f.when.replace('T', ' ') + (f.when.length === 16 ? ':00' : '');
        // The meeting link now lives inside the message/details (no separate
        // location field) — pass an empty location.
        const res = await this._applicantAction(
            "action_recycle_web_schedule_interview",
            [when, false, f.notes || false],
            this.tr('Interview scheduled.'));
        if (res && res.sent === false) {
            this.state.applicantActionSuccess =
                this.tr('Interview saved, but the email could not be sent (configure a mail server).');
            setTimeout(() => { this.state.applicantActionSuccess = null; }, 4500);
        }
    }

    // Account creation (accepted applicants)
    async applicantCreateAccount() {
        const f = this.state.applicantAccountForm;
        if (!f.warehouse_id) {
            this.state.applicantActionError = this.tr('Please select a warehouse.');
            setTimeout(() => { this.state.applicantActionError = null; }, 4500);
            return;
        }
        await this._applicantAction(
            "action_recycle_web_create_account",
            [parseInt(f.warehouse_id, 10), f.role || false],
            this.tr('Account created successfully.'));
    }

    onApplicantRowClick(app) {
        // Ignore clicks on deleted-account rows
        if (!app.recycle_account_deleted) {
            this.openApplicantDetail(app);
        }
    }

    async setApplicantState(newState) {
        const app = this.state.selectedApplicant;
        if (!app) return;
        // Check for duplicate accepted application when accepting
        if (newState === 'accepted') {
            const email = app.recycle_email || app.email_from || '';
            if (email) {
                const dupes = await this.orm.searchRead(
                    "hr.applicant",
                    [["recycle_state", "=", "accepted"],
                     "|", ["recycle_email", "=", email],
                          ["email_from", "=", email],
                     ["id", "!=", app.id]],
                    ["id", "job_id"]
                );
                if (dupes.length) {
                    const jobNames = await Promise.all(dupes.map(d => {
                        const jid = Array.isArray(d.job_id) ? d.job_id[0] : d.job_id;
                        return this.orm.searchRead("hr.job", [["id", "=", jid]], ["name"]);
                    }));
                    const names = jobNames.flat().map(j => j.name).filter(Boolean);
                    if (names.length) {
                        // Was `alert()`: the browser's own box, which cannot be
                        // translated and freezes the page mid-update.
                        this.showMessage(
                            this.tr('Already accepted elsewhere'),
                            this.tr('This applicant already has an accepted application for:')
                                + ' ' + names.join(', '),
                            'error',
                        );
                    }
                }
            }
        }
        // Set the state authoritatively: recycle_syncing bypasses the model's
        // stage-based re-sync so a direct Accept/Reject sticks (otherwise the
        // sync could revert 'accepted' back to 'applied' and block account
        // creation in this custom UI).
        await this.orm.write("hr.applicant", [app.id], { recycle_state: newState },
            { context: { recycle_syncing: true } });
        this.state.selectedApplicant = { ...app, recycle_state: newState };
        // also update in list
        const idx = this.state.applicants.findIndex(a => a.id === app.id);
        if (idx >= 0) this.state.applicants[idx] = { ...this.state.applicants[idx], recycle_state: newState };
    }

    // ─── Employees ────────────────────────────────────────
    DELETED_EMPLOYEES_FIELDS = ["id", "name", "login", "email", "recycle_role",
        "recycle_warehouse_id", "recycle_deleted_date",
        "recycle_delete_reason", "recycle_prev_warehouse_id",
        "recycle_prev_role", "recycle_prev_managed"];

    _deletedEmployeesDomain() {
        const domain = [["recycle_deleted", "=", true]];
        if (this.state.archivedWHFilter) domain.push(["recycle_prev_warehouse_id", "=", this.state.archivedWHFilter]);
        const q = (this.state.deletedEmployeeSearch || '').trim();
        if (q) {
            domain.push("|", ["name", "ilike", q], "|", ["login", "ilike", q], ["email", "ilike", q]);
        }
        return domain;
    }

    async _refetchDeletedEmployees() {
        this.state.deletedEmployees = [];
        this.state.deletedEmployeesHasMore = true;
        // active_test:false is required to see archived (soft-deleted) users.
        const pager = makePager(this.orm, {
            model: "res.users", fields: this.DELETED_EMPLOYEES_FIELDS, context: { active_test: false },
        });
        const { rows, hasMore } = await pager.fetchFirst(this._deletedEmployeesDomain());
        this.state.deletedEmployees = rows;
        this.state.deletedEmployeesHasMore = hasMore;
    }

    async loadMoreDeletedEmployees() {
        if (this.state.view !== 'employees_list' || this.state.employeeTab !== 'deleted') return;
        if (!this.state.deletedEmployeesHasMore || this.state.deletedEmployeesLoadingMore || this.state.loading) return;
        this.state.deletedEmployeesLoadingMore = true;
        try {
            const lastId = this.state.deletedEmployees.length
                ? this.state.deletedEmployees[this.state.deletedEmployees.length - 1].id : 0;
            const pager = makePager(this.orm, {
                model: "res.users", fields: this.DELETED_EMPLOYEES_FIELDS, context: { active_test: false },
            });
            const { rows, hasMore } = await pager.fetchMore(this._deletedEmployeesDomain(), lastId);
            this.state.deletedEmployees = this.state.deletedEmployees.concat(rows);
            this.state.deletedEmployeesHasMore = hasMore;
        } catch (e) { /* silent */ }
        this.state.deletedEmployeesLoadingMore = false;
    }

    onDeletedEmployeeSearchInput(ev) {
        this.state.deletedEmployeeSearch = ev.target.value;
        clearTimeout(this._deletedEmployeeSearchTimer);
        this._deletedEmployeeSearchTimer = setTimeout(() => this._refetchDeletedEmployees(), 400);
    }

    // ─── Adding an employee ─────────────────────────────────────
    //
    // The admin's version of this differs from the manager's by exactly one
    // role: they may appoint a WAREHOUSE MANAGER. A manager may not — otherwise
    // a manager could quietly make themselves a peer in every other warehouse.

    get employeeRoleChoices() {
        return [
            { value: 'input', icon: '📥', label: 'Reception Employee',
              description: 'Receives incoming shipments and checks them in.' },
            { value: 'sorting', icon: '♻️', label: 'Sorting Employee',
              description: 'Grades processed material and moves it to storage.' },
            { value: 'output', icon: '📦', label: 'Output Employee',
              description: 'Prepares orders, deducts stock and invoices them.' },
            { value: 'manager', icon: '🧑‍💼', label: 'Warehouse Manager',
              description: 'Runs one warehouse. A site has one manager, and a manager has one site.' },
        ];
    }

    /**
     * The warehouses this role may be put in.
     *
     * For a MANAGER, only sites that have none. Offering a warehouse that
     * already has a manager and refusing it after the form is filled in wastes
     * the work and reads as a bug; leaving it out states the rule while the
     * choice is still being made.
     *
     * Closing and closed sites are excluded for everyone: the whole point of
     * that state is that work stops arriving there, and staff are work.
     */
    get employeeWarehouseChoices() {
        const active = (this.state.warehouses || []).filter(
            (w) => !w.state || w.state === 'active');
        if (this.state.empCreateForm.role !== 'manager') return active;
        return active.filter((w) => !w.manager_user_id);
    }

    async openEmployeeCreate() {
        this.state.empCreateForm = {
            name: '', email: '', phone: '', national_id: '',
            role: 'input', warehouse_id: '',
        };
        this.state.empCreateError = null;
        this.state.empCreateSuccess = null;
        this.state.empCreateSaving = false;
        // Refetched rather than reused: `manager_user_id` decides which sites
        // are offered, and a list cached from an earlier screen may predate the
        // last appointment.
        this.state.warehouses = await this.orm.searchRead(
            'recycle.warehouse', [],
            ['id', 'name', 'code', 'state', 'manager_user_id'],
            { order: 'name' });
        this._navigate('employee_create');
    }

    setEmployeeRole(role) {
        this.state.empCreateForm.role = role;
        // Changing to MANAGER narrows the warehouse list, and a warehouse
        // chosen under the old role may no longer be on it — clearing is how
        // the form stops holding a choice the screen no longer shows.
        const stillOffered = this.employeeWarehouseChoices.some(
            (w) => '' + w.id === this.state.empCreateForm.warehouse_id);
        if (!stillOffered) this.state.empCreateForm.warehouse_id = '';
        this.state.empCreateError = null;
    }

    async saveNewEmployee() {
        const f = this.state.empCreateForm;
        const name = (f.name || '').trim();
        const email = (f.email || '').trim();

        if (!name) {
            this.state.empCreateError = this.tr('Name required'); return;
        }
        if (!email) {
            this.state.empCreateError = this.tr('Email is required for login and password reset.');
            return;
        }
        if (!f.warehouse_id) {
            this.state.empCreateError = this.tr('Choose the warehouse this employee works in.');
            return;
        }

        this.state.empCreateSaving = true;
        this.state.empCreateError = null;
        try {
            const res = await this._rpc('/api/admin/employee/create', {
                name, email,
                phone: (f.phone || '').trim(),
                national_id: (f.national_id || '').trim(),
                role: f.role,
                warehouse_id: parseInt(f.warehouse_id),
            });

            if (res && res.error) {
                this.state.empCreateError = this._employeeCreateError(res);
            } else {
                this.state.empCreateSuccess = this.tr('Employee added. A set-password link was emailed to them.')
                    + ' — ' + res.name;
                this.goBack();
                await this.switchEmployeeTab(this.state.employeeTab || 'active');
            }
        } catch (e) {
            this.state.empCreateError = this._err(e);
        }
        this.state.empCreateSaving = false;
    }

    /** The server's reason, in words the admin can act on. */
    _employeeCreateError(res) {
        switch (res.error) {
            case 'login_exists':
                return this.tr('An account with this email already exists.');
            case 'identity_taken': {
                // Composed HERE, in the screen's own language.
                //
                // The server's sentence used to be passed straight through. It
                // is built with Odoo's `_()`, which resolves against
                // `res.users.lang` — and this dashboard takes its language from
                // the browser instead. So the one refusal on this form carrying
                // a detail worth reading (whose id it is) was the one always
                // shown in English. The server now sends the PARTS, so the
                // detail survives translation.
                const c = res.conflict || {};
                if (c.value && c.owner_label) {
                    const template = c.kind === 'email'
                        ? this.tr('The email %s is already used by %s.')
                        : this.tr('The national ID %s already belongs to %s.');
                    return template
                        .replace('%s', c.value)
                        .replace('%s', c.owner_label);
                }
                return res.message || this.tr('This national ID or email is already registered.');
            }
            case 'warehouse_has_manager':
                return this.tr('This warehouse already has a manager:') + ' ' + (res.manager || '');
            case 'warehouse_not_active':
                return this.tr('This warehouse is closing or closed and takes no new staff.');
            case 'warehouse_not_found':
                return this.tr('Warehouse not found.');
            case 'warehouse_required':
                return this.tr('Choose the warehouse this employee works in.');
            case 'invalid_role':
                return this.tr('Invalid role.');
            case 'forbidden':
                return this.tr('You do not have permission to perform this action.');
            default:
                return this.tr('Creation failed. Please check the fields.');
        }
    }

    async switchEmployeeTab(tab) {
        this.state.employeeTab = tab;
        this.state.loading = true;
        if (tab === 'unassigned') {
            this.state.unassignedError = null;
            this.state.unassignedSuccess = null;
            try {
                const res = await this._rpc('/api/admin/unassigned-employees', {});
                this.state.unassignedEmployees = res.employees || [];
            } catch (e) {
                this.state.unassignedEmployees = [];
            }
        } else if (tab === 'deleted') {
            if (!this.state.warehouses.length) {
                this.state.warehouses = await this.orm.searchRead("recycle.warehouse", [["state", "=", "active"]], ["id", "name"]);
            }
            await this._refetchDeletedEmployees();
        } else {
            if (!this.state.warehouses.length) {
                this.state.warehouses = await this.orm.searchRead("recycle.warehouse", [["state", "=", "active"]], ["id", "name"]);
            }
            this.state.employees = await this.orm.searchRead(
                "res.users",
                [["recycle_role", "!=", false], ["recycle_deleted", "=", false]],
                ["id", "name", "login", "email", "phone", "active",
                 "recycle_role", "recycle_warehouse_id", "shift_id"],
                { order: "name asc", context: { active_test: false } }
            );
            this.state.employees = this.state.employees.map(
                (e) => this._shapeEmployeeRow(e));
        }
        this.state.loading = false;
    }

    async openEmployeesList() {
        if (this.state.view !== 'employees_list') {
            this._navigate("employees_list");
        }
        this.state.loading = true;
        if (this.state.employeeTab === 'active') {
            if (!this.state.warehouses.length) {
                this.state.warehouses = await this.orm.searchRead("recycle.warehouse", [["state", "=", "active"]], ["id", "name"]);
            }
            this.state.employees = await this.orm.searchRead(
                "res.users",
                [["recycle_role", "!=", false], ["recycle_deleted", "=", false]],
                ["id", "name", "login", "email", "phone", "active",
                 "recycle_role", "recycle_warehouse_id", "shift_id"],
                { order: "name asc", context: { active_test: false } }
            );
            this.state.employees = this.state.employees.map(
                (e) => this._shapeEmployeeRow(e));
        } else {
            if (!this.state.warehouses.length) {
                this.state.warehouses = await this.orm.searchRead("recycle.warehouse", [["state", "=", "active"]], ["id", "name"]);
            }
            await this._refetchDeletedEmployees();
        }
        this.state.loading = false;
    }

    // Client-side search getters (name / email) ---------------------------
    get filteredActiveEmployees() {
        const q = (this.state.employeeSearch || '').trim().toLowerCase();
        const status = this.state.employeeStatusFilter;
        return this.state.employees.filter(e => {
            if (q && !((e.name || '').toLowerCase().includes(q)
                    || (e.login || '').toLowerCase().includes(q))) return false;
            if (status === 'active' && !e.active) return false;
            if (status === 'inactive' && e.active) return false;
            return true;
        });
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
    get filteredDeletedEmployees() {
        // Filtering now happens server-side (see _deletedEmployeesDomain).
        return this.state.deletedEmployees;
    }
    async setArchivedWHFilter(ev) {
        const v = ev.target.dataset ? ev.target.dataset.filter : ev.target.value;
        this.state.archivedWHFilter = v ? parseInt(v, 10) : null;
        await this._refetchDeletedEmployees();
    }

    async setEmployeeWHFilter(ev) {
        const val = ev.target.dataset ? ev.target.dataset.filter : ev.target.value;
        this.state.employeeWHFilter = val ? parseInt(val) : null;
        await this.openEmployeesList();
    }

    async openEmployeeDetail(emp) {
        this.state.selectedEmployee = { ...emp };
        this.state.employeeEditMode = false;
        this.state.employeeError = null;
        this.state.employeeSuccess = null;
        this._navigate("employee_detail");
        this.state.loading = true;
        const records = await this.orm.searchRead(
            "res.users", [["id", "=", emp.id]],
            ["id", "name", "login", "email", "phone", "active",
             "recycle_role", "recycle_national_id", "recycle_warehouse_id",
             "shift_id", "create_date"]
        );
        if (records.length) {
            const r = records[0];
            const shiftArr = r.shift_id;
            r.role = r.recycle_role || '';
            r.shift = Array.isArray(shiftArr) ? shiftArr[1] : '';
            r.shift_id = Array.isArray(shiftArr) ? shiftArr[0] : (typeof shiftArr === 'number' ? shiftArr : '');
            r.national_id = r.recycle_national_id || '';
            this.state.selectedEmployee = r;
        }
        if (!this.state.warehouses.length) {
            this.state.warehouses = await this.orm.searchRead("recycle.warehouse", [["state", "=", "active"]], ["id", "name"]);
        }
        if (!this.state.shifts.length) {
            // Employee assignment: warehouse shifts only — driver shifts are
            // reserved for collectors (recycle.driver.assignment).
            this.state.shifts = await this.orm.searchRead(
                "recycle.shift",
                [["active", "=", true], ["shift_type", "=", "warehouse"]],
                ["id", "name"]);
        }
        this.state.loading = false;
    }

    async openDeletedEmployeeDetail(emp) {
        this.state.selectedDeletedEmployee = { ...emp };
        this._navigate("deleted_employee_detail");
        const records = await this.orm.searchRead(
            "res.users", [["id", "=", emp.id]],
            ["id", "name", "login", "email", "recycle_role",
             "recycle_warehouse_id", "recycle_national_id",
             "recycle_deleted_date", "recycle_delete_reason",
             "recycle_prev_role", "recycle_prev_warehouse_id",
             "recycle_prev_managed"],
            { context: { active_test: false } }
        );
        if (records.length) this.state.selectedDeletedEmployee = records[0];
    }

    // Soft-delete: archive the account (restorable) with an optional reason.
    async deleteEmployee(emp) {
        const reason = window.prompt(
            this.tr('Delete this employee? The account will be archived and can ' +
                    'be restored later.\n\nOptional reason:'),
            ''
        );
        // prompt returns null when the admin cancels.
        if (reason === null) return;
        try {
            await this.orm.call("res.users", "action_recycle_soft_delete",
                [[emp.id], reason || false]);
            this.notification.add(
                this.tr('Employee deleted (archived).'),
                { type: "success", sticky: false });
            this._goBackFromEmployee();
            await this.openEmployeesList();
        } catch (e) {
            this.notification.add(
                this.tr('Failed to delete employee:') + ' ' + (e.message || e),
                { type: "danger", sticky: false });
        }
    }

    // Archive employee: unassign role and warehouse, move to archived tab.
    async archiveEmployee(emp) {
        const ok = await this.askConfirm(
            this.tr('Archive employee'),
            this.tr('Archive this employee? Their role and warehouse will be unassigned.'));
        if (!ok) return;
        try {
            await this.orm.call("res.users", "action_recycle_soft_delete",
                [[emp.id], 'Archived by admin']);
            this.notification.add(
                this.tr('Employee archived.'),
                { type: "success", sticky: false });
            this.state.employeeTab = 'active';
            await this.switchEmployeeTab('active');
        } catch (e) {
            this.notification.add(
                this.tr('Failed to archive employee:') + ' ' + (e.message || e),
                { type: "danger", sticky: false });
        }
    }

    // Restore a soft-deleted employee + send notification + email.
    async restoreEmployee(emp) {
        try {
            await this.orm.call("res.users", "action_recycle_restore_and_notify", [[emp.id]]);
            this.notification.add(
                this.tr('Employee restored. Notification and email sent.'), { type: "success", sticky: false });
            if (this.state.view === 'deleted_employee_detail') this.goBack();
            this.state.employeeTab = 'unassigned';
            await this.switchEmployeeTab('unassigned');
        } catch (e) {
            this.notification.add(
                this.tr('Failed to restore employee:') + ' ' + (e.message || e),
                { type: "danger", sticky: false });
        }
    }

    // Reject archived employee's reactivation + send notification + email.
    async rejectEmployee(emp) {
        try {
            await this.orm.call("res.users", "action_recycle_reject_and_notify", [[emp.id]]);
            this.notification.add(
                this.tr('Request declined. Notification and email sent.'), { type: "success", sticky: false });
            if (this.state.view === 'deleted_employee_detail') this.goBack();
            await this.openDeletedEmployees();
        } catch (e) {
            this.notification.add(
                this.tr('Failed to reject employee:') + ' ' + (e.message || e),
                { type: "danger", sticky: false });
        }
    }

    // ─── Unassigned Employees ─────────────────────────────
    async openUnassignedEmployees() {
        this.state.unassignedError = null;
        this.state.unassignedSuccess = null;
        try {
            const res = await this._rpc('/api/admin/unassigned-employees', {});
            this.state.unassignedEmployees = res.employees || [];
        } catch (e) {
            this.state.unassignedEmployees = [];
        }
    }

    // Entry point from the Recruitment > Unassigned Employees act_window's
    // "Assign" row button (res.users#action_recycle_open_assignment), which
    // hands off here via context({initial_view, employee_id}). Reuses the
    // existing unassigned-list fetch + detail screen — no new endpoint.
    async openEmployeeAssignment(employeeId) {
        const id = parseInt(employeeId, 10);
        await this.openUnassignedEmployees();
        const emp = this.state.unassignedEmployees.find(e => e.id === id);
        if (emp) {
            await this.openUnassignedDetail(emp);
        } else {
            this.notification.add(
                this.tr('This employee was not found or is already assigned.'),
                { type: "danger" });
        }
    }

    get filteredUnassignedEmployees() {
        const q = (this.state.employeeSearch || '').trim().toLowerCase();
        return this.state.unassignedEmployees.filter(e => {
            if (q && !((e.name || '').toLowerCase().includes(q)
                    || (e.email || '').toLowerCase().includes(q)
                    || (e.login || '').toLowerCase().includes(q)
                    || (e.warehouse || '').toLowerCase().includes(q))) return false;
            return true;
        });
    }

    async openUnassignedDetail(emp) {
        this.state.selectedUnassigned = { ...emp };
        this.state.unassignedWarehouseForm = { warehouse_id: emp.recycle_warehouse_id || null };
        this.state.unassignedRoleForm = { role_type: '' };
        this.state.unassignedError = null;
        this.state.unassignedSuccess = null;
        try {
            const res = await this._rpc('/api/admin/warehouses-without-manager', {});
            this.state.warehousesWithoutManager = res.warehouses || [];
        } catch (e) {
            this.state.warehousesWithoutManager = [];
        }
        this._navigate("unassigned_detail");
    }

    async _loadEmployeeHistory(employeeId) {
        this.state.employeeHistoryLoading = true;
        try {
            const res = await this._rpc('/api/admin/employee-history', {
                employee_id: employeeId,
            });
            this.state.employeeHistory = res.history || [];
        } catch (e) {
            this.state.employeeHistory = [];
        }
        this.state.employeeHistoryLoading = false;
    }

    historyTypeLabel(type) {
        const labels = {
            'role': this.tr('Role Change'),
            'warehouse': this.tr('Warehouse Change'),
            'direct_addition': this.tr('Direct Addition'),
            'assignment_start': this.tr('Assignment Start'),
            'assignment_end': this.tr('Assignment End'),
            'archive': this.tr('Archived'),
            'restore': this.tr('Restored'),
        };
        return labels[type] || type;
    }

    historyTypeIcon(type) {
        const icons = {
            'role': '🔄', 'warehouse': '🏭', 'direct_addition': '➕',
            'assignment_start': '🚀', 'assignment_end': '⏹️',
            'archive': '🗄️', 'restore': '♻️',
        };
        return icons[type] || '📋';
    }

    async assignWarehouseToUnassigned() {
        const emp = this.state.selectedUnassigned;
        const f = this.state.unassignedWarehouseForm;
        if (!f.warehouse_id) {
            this.state.unassignedError = this.tr('Please select a warehouse.');
            return;
        }
        this.state.unassignedSaving = true;
        this.state.unassignedError = null;
        this.state.unassignedSuccess = null;
        try {
            const res = await this._rpc('/api/admin/assign-warehouse', {
                employee_id: emp.id,
                warehouse_id: parseInt(f.warehouse_id, 10),
            });
            if (res.error) {
                const errMap = {
                    'warehouse_not_found': this.tr('Warehouse not found.'),
                    'employee_not_found': this.tr('Employee not found.'),
                };
                this.state.unassignedError = errMap[res.error] || this.tr('Assignment failed.');
            } else {
                emp.warehouse = res.warehouse_name;
                emp.recycle_warehouse_id = res.warehouse_id;
                emp.has_warehouse = true;
                this.state.unassignedEmployees = this.state.unassignedEmployees.map(e =>
                    e.id === emp.id ? { ...e, warehouse: res.warehouse_name, recycle_warehouse_id: res.warehouse_id, has_warehouse: true } : e
                );
                let msg = this.tr('Warehouse assigned successfully!');
                if (res.manager_notified) {
                    msg += ' ' + this.tr('Notification sent to warehouse manager.');
                }
                this.state.unassignedSuccess = msg;
                const wRes = await this._rpc('/api/admin/warehouses-without-manager', {});
                this.state.warehousesWithoutManager = wRes.warehouses || [];
                setTimeout(() => { this.state.unassignedSuccess = null; }, 5000);
            }
        } catch (e) {
            this.state.unassignedError = this.tr('Assignment failed. Please try again.');
        }
        this.state.unassignedSaving = false;
    }

    async assignRoleTypeToUnassigned() {
        const emp = this.state.selectedUnassigned;
        const f = this.state.unassignedRoleForm;
        if (!f.role_type) {
            this.state.unassignedError = this.tr('Please select a role type.');
            return;
        }
        if (!emp.recycle_warehouse_id && !this.state.unassignedWarehouseForm.warehouse_id) {
            this.state.unassignedError = this.tr('Please assign a warehouse first.');
            return;
        }
        this.state.unassignedSaving = true;
        this.state.unassignedError = null;
        this.state.unassignedSuccess = null;
        try {
            const warehouseId = emp.recycle_warehouse_id || parseInt(this.state.unassignedWarehouseForm.warehouse_id, 10);
            const res = await this._rpc('/api/admin/assign-role-type', {
                employee_id: emp.id,
                role_type: f.role_type,
                warehouse_id: warehouseId,
            });
            if (res.error) {
                const errMap = {
                    'warehouse_has_manager': this.tr('This warehouse already has a manager.'),
                    'no_warehouse_assigned': this.tr('Please assign a warehouse first.'),
                    'warehouse_not_found': this.tr('Warehouse not found.'),
                    'employee_not_found': this.tr('Employee not found.'),
                    'invalid_role_type': this.tr('Invalid role type.'),
                };
                this.state.unassignedError = errMap[res.error] || this.tr('Assignment failed.');
            } else {
                emp.role = res.role;
                emp.warehouse = res.warehouse_name;
                emp.has_role = true;
                this.state.unassignedEmployees = this.state.unassignedEmployees.filter(e => e.id !== emp.id);
                this.state.unassignedSuccess = res.message || this.tr('Role assigned successfully!');
                setTimeout(() => {
                    this.state.unassignedSuccess = null;
                    this.state.view = 'employees_list';
                    this.switchEmployeeTab('active');
                }, 1500);
            }
        } catch (e) {
            this.state.unassignedError = this.tr('Assignment failed. Please try again.');
        }
        this.state.unassignedSaving = false;
    }

    // Permanent delete: the irreversible SQL purge of the account.
    async permanentDeleteEmployee(emp) {
        const ok = await this.askConfirm(
            this.tr('Delete account permanently'),
            this.tr('Permanently delete this account? This cannot be undone. ' +
                    'Shipment records are kept.'));
        if (!ok) return;
        try {
            await this.orm.call("res.users", "action_recycle_purge_employee", [[emp.id]]);
            this.notification.add(
                this.tr('Account permanently deleted.'),
                { type: "success", sticky: false });
            if (this.state.view === 'deleted_employee_detail') this.goBack();
            await this.openEmployeesList();
        } catch (e) {
            this.notification.add(
                this.tr('Failed to delete account:') + ' ' + (e.message || e),
                { type: "danger", sticky: false });
        }
    }

    _goBackFromEmployee() {
        if (this.state.view === 'employee_detail') this.goBack();
    }

    // ─── Website Users management (portal accounts) ───────────────────
    WEBSITE_USERS_FIELDS = ["id", "name", "login", "email", "recycle_banned",
        "recycle_banned_date", "recycle_ban_reason", "create_date"];

    _websiteUsersDomain() {
        const domain = [["share", "=", true], ["email", "!=", false], ["recycle_deleted", "=", false]];
        const q = (this.state.websiteUserSearch || '').trim();
        if (q) {
            domain.push("|", ["name", "ilike", q], "|", ["login", "ilike", q], ["email", "ilike", q]);
        }
        return domain;
    }

    async _refetchWebsiteUsers() {
        this.state.websiteUsersLoading = true;
        this.state.websiteUsers = [];
        this.state.websiteUsersHasMore = true;
        try {
            // Website/portal accounts = share users with a real email.
            // active_test:false so banned-but-archived accounts still appear.
            const pager = makePager(this.orm, {
                model: "res.users", fields: this.WEBSITE_USERS_FIELDS, context: { active_test: false },
            });
            const { rows, hasMore } = await pager.fetchFirst(this._websiteUsersDomain());
            this.state.websiteUsers = rows;
            this.state.websiteUsersHasMore = hasMore;
        } finally {
            this.state.websiteUsersLoading = false;
        }
    }

    async openUsersList() {
        this._navigate("users_list");
        this.state.websiteUserSearch = '';
        await this._refetchWebsiteUsers();
    }

    onWebsiteUserSearchInput(ev) {
        this.state.websiteUserSearch = ev.target.value;
        clearTimeout(this._websiteUserSearchTimer);
        this._websiteUserSearchTimer = setTimeout(() => this._refetchWebsiteUsers(), 400);
    }

    async loadMoreUsers() {
        if (this.state.view !== 'users_list') return;
        if (!this.state.websiteUsersHasMore || this.state.websiteUsersLoadingMore || this.state.websiteUsersLoading) return;
        this.state.websiteUsersLoadingMore = true;
        try {
            const lastId = this.state.websiteUsers.length
                ? this.state.websiteUsers[this.state.websiteUsers.length - 1].id : 0;
            const pager = makePager(this.orm, {
                model: "res.users", fields: this.WEBSITE_USERS_FIELDS, context: { active_test: false },
            });
            const { rows, hasMore } = await pager.fetchMore(this._websiteUsersDomain(), lastId);
            this.state.websiteUsers = this.state.websiteUsers.concat(rows);
            this.state.websiteUsersHasMore = hasMore;
        } catch (e) { /* silent */ }
        this.state.websiteUsersLoadingMore = false;
    }

    get filteredWebsiteUsers() {
        // Filtering now happens server-side (see _websiteUsersDomain).
        return this.state.websiteUsers;
    }

    async banUser(user) {
        const reason = window.prompt(
            this.tr('Ban this user? They will be signed out and blocked from ' +
                    'logging in.\n\nOptional reason:'), '');
        if (reason === null) return;
        try {
            await this.orm.call("res.users", "action_recycle_ban",
                [[user.id], reason || false]);
            this.notification.add(this.tr('User banned.'),
                { type: "success", sticky: false });
            await this.openUsersList();
        } catch (e) {
            this.notification.add(
                this.tr('Failed to ban user:') + ' ' + (e.message || e),
                { type: "danger", sticky: false });
        }
    }

    async unbanUser(user) {
        try {
            await this.orm.call("res.users", "action_recycle_unban", [[user.id]]);
            this.notification.add(this.tr('User unbanned.'),
                { type: "success", sticky: false });
            await this.openUsersList();
        } catch (e) {
            this.notification.add(
                this.tr('Failed to unban user:') + ' ' + (e.message || e),
                { type: "danger", sticky: false });
        }
    }

    async deleteWebsiteUser(user) {
        const ok = await this.askConfirm(
            this.tr('Delete account permanently'),
            this.tr('Permanently delete this account? This cannot be undone.'));
        if (!ok) return;
        try {
            await this.orm.call("res.users", "action_recycle_delete_account",
                [[user.id]]);
            this.notification.add(this.tr('Account deleted.'),
                { type: "success", sticky: false });
            await this.openUsersList();
        } catch (e) {
            this.notification.add(
                this.tr('Failed to delete account:') + ' ' + (e.message || e),
                { type: "danger", sticky: false });
        }
    }

    startEditEmployee() {
        const e = this.state.selectedEmployee;
        const empShift = e.shift_id;
        this.state.employeeForm = {
            phone: e.phone || '',
            active: String(e.active),
            role: e.role || e.recycle_role || 'input',
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
        const oldRole = e.role || e.recycle_role;
        try {
            const res = await this._rpc('/api/admin/employee/update', {
                employee_id: e.id,
                name: e.name, login: e.login, email: e.email,
                phone: f.phone || '',
                active: f.active === 'true',
                role: f.role || false,
                shift_id: f.shift_id ? parseInt(f.shift_id, 10) : false,
                warehouse_id: e.recycle_warehouse_id ? (Array.isArray(e.recycle_warehouse_id) ? e.recycle_warehouse_id[0] : e.recycle_warehouse_id) : false,
            });
            if (res.error) {
                this.state.employeeError = res.error;
            } else {
                e.name = res.name || e.name;
                e.phone = res.phone !== undefined ? res.phone : e.phone;
                e.active = res.active !== undefined ? res.active : e.active;
                e.role = res.role !== undefined ? res.role : e.role;
                e.recycle_role = res.role !== undefined ? res.role : e.recycle_role;
                e.shift_id = res.shift_id !== undefined ? res.shift_id : e.shift_id;
                e.shift = res.shift !== undefined ? res.shift : e.shift;
                e.national_id = res.national_id !== undefined ? res.national_id : e.national_id;
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

    async _sendRoleChangeNotification(emp, oldRole) {
        const roleLabels = {
            input: 'Input Employee', sorting: 'Sorting Employee',
            output: 'Output Employee',
            manager: 'Warehouse Manager',
        };
        const newLabel = roleLabels[emp.recycle_role] || emp.recycle_role;
        const oldLabel = roleLabels[oldRole] || oldRole || 'None';
        const msg = 'Your role has been changed from ' + oldLabel + ' to ' + newLabel;
        try {
            await this._rpc('/api/admin/notification/send', {
                user_id: emp.id,
                title: 'Role Updated',
                message: msg,
                type: 'info',
            });
        } catch (e) {}
    }

    async printEmployeeReport() {
        const emp = this.state.selectedEmployee;
        if (!emp) return;
        await this.actionService.doAction(
            'recycle_warehouse.action_report_employee',
            { additionalContext: { active_id: emp.id, active_ids: [emp.id], active_model: 'res.users' } }
        );
    }


    // ─── Dark Mode ────────────────────────────────────────
    toggleDarkMode() {
        this.state.darkMode = !this.state.darkMode;
        this._applyTheme();
        // Re-render charts with updated theme colors
        setTimeout(function (self) { self.renderDonutChart(); self.renderBarChart(); }, 50, this);
    }

    // Apply the theme to the whole document so the backend top navbar and the
    // website (which read the shared 'dw-theme' key + data-theme attribute)
    // stay in sync with the dashboard.
    _applyTheme() {
        const theme = this.state.darkMode ? 'dark' : 'light';
        try {
            document.documentElement.setAttribute('data-theme', theme);
            document.documentElement.classList.toggle('o_ra_dark', this.state.darkMode);
            localStorage.setItem('dw-theme', theme);
            localStorage.setItem('recycle_wms_dark', this.state.darkMode ? '1' : '0');
        } catch (e) { /* localStorage/DOM unavailable — ignore */ }
    }

    // ─── Nav Bar Actions ─────────────────────────────────
    goDashboard() {
        this.state.view = 'dashboard';
    }

    // ─── Vertical Sidebar ─────────────────────────────────
    get navSections() {
        return [
            { key: 'home', icon: '🏠', label: 'Home', single: true, go: 'goDashboard', view: 'dashboard' },
            { key: 'operations', icon: '🚚', label: 'Operations', items: [
                { label: 'Shipments', go: 'openShipments' },
                { label: 'Orders', go: 'openOrders' },
                // Written-off material, per shipment. The manager decides each
                // one inside their own warehouse; without this the
                // administrator could only ever read the totals afterwards,
                // with no way back to the delivery that produced them.
                { label: 'Damage by Shipment', go: 'openDamageByShipment' },
            ]},
            { key: 'archived', icon: '🗄️', label: 'Archived', items: [
                { label: 'Archived Shipments', go: 'openArchivedShipments' },
                { label: 'Archived Orders', go: 'openArchivedOrders' },
            ]},
            { key: 'inventory', icon: '📦', label: 'Inventory', items: [
                { label: 'Stock', go: 'openStockList' },
                { label: 'Products', go: 'openProductsList' },
                { label: 'Suggest a Material', go: 'openProductSuggest' },
                { label: 'Product Categories', go: 'openProductCategoriesList' },
            ]},
            { key: 'recruitment', icon: '💼', label: 'Recruitment', items: [
                { label: 'Jobs & HR', go: 'openJobsHR' },
                { label: 'Job Applicants', go: 'openApplicantsList' },
                { label: 'Driver Requests', go: 'openDriverRequests' },
                { label: 'Talent Pool', go: 'openTalentPool' },
                { label: 'Hiring Stages', go: 'openStagesList' },
                { label: 'Employees', go: 'openEmployeesList' },
            ]},
            { key: 'shifts', icon: '🕑', label: 'Shifts', items: [
                { label: 'Manage Shifts', go: 'openShiftsHub' },
                { label: 'All Shifts', go: 'openShiftsList' },
                // One "Attendance" entry that expands to the two attendance
                // screens (drivers / warehouse staff) — same design, own view.
                { label: 'Attendance', subitems: [
                    { label: 'Driver Attendance', go: 'openDriverAttendance' },
                    { label: 'Warehouse Staff Attendance', go: 'openAttendance' },
                ]},
            ]},
            { key: 'warehouses', icon: '🏭', label: 'Warehouses', single: true, go: 'openWarehouses', view: 'warehouse_hub' },
            { key: 'trucks', icon: '🚛', label: 'Trucks', items: [
                // "View Trucks" rather than "All Trucks": the screen now shows
                // BOTH kinds with a filter, so "all" described a list that no
                // longer has a single meaning.
                { label: 'View Trucks', go: 'openTrucks' },
                { label: 'Add Truck', go: 'openTruckCreate' },
                { label: 'Assign Driver to Truck', go: 'openAssignDriver' },
            ]},
            // ONE "Drivers" entry that opens into the two kinds — the same
            // shape the manager's sidebar already had. They were three sibling
            // entries buried under Trucks, which made them read as unrelated
            // features; they are one thing — a person who drives a company
            // truck — split only by which truck they drive. Adding a delivery
            // driver lives on that screen, next to the list it adds to.
            { key: 'drivers', icon: '\u{1F9D1}‍\u{1F527}', label: 'Drivers', items: [
                { label: 'Collection Drivers', go: 'openDriversList' },
                { label: 'Delivery Drivers', go: 'openDeliveryDrivers' },
            ]},
            { key: 'config', icon: '🛠️', label: 'Configuration', items: [
                { label: 'Zones', go: 'openZonesList' },
                { label: 'Users', go: 'openUsersList' },
            ]},
        ];
    }

    toggleSidebar(ev) {
        // Same defensive stopPropagation as openAppLauncher() — a click on
        // our own toggle must never bubble into Odoo's own document-level
        // dropdown/menu listeners (the adjacent app-launcher button is a
        // flex sibling a few pixels away in the same toolbar).
        if (ev) { ev.stopPropagation(); ev.preventDefault(); }
        this.state.sidebarOpen = !this.state.sidebarOpen;
    }

    // Forwards to Odoo's own (visually hidden, see dashboard_navbar_fix.css)
    // native app-launcher button — desktop opens its dropdown in place,
    // mobile navigates to /odoo's app grid. Never touches state.sidebarOpen.
    openAppLauncher(ev) {
        // Stop our own click from also bubbling to `document` — Odoo's
        // dropdown attaches a document-level "click outside closes it"
        // listener, and without this it sees our *original* click (whose
        // target is our own button, not the native toggle) as "outside"
        // and immediately closes the menu the forwarded click just opened.
        if (ev) { ev.stopPropagation(); ev.preventDefault(); }
        const btn = document.querySelector(
            '.o_navbar_apps_menu > button, .o_main_navbar a.o_menu_toggle');
        if (btn) { btn.click(); return; }
        // Odoo doesn't always mount the native toggle inside a client
        // action (observed: present on some loads, absent on others). The
        // Settings card is the admin's ONLY way to reach other apps, so
        // fall back to the backend home — same destination the mobile
        // toggle navigates to.
        window.location.href = '/odoo';
    }

    // ─── Settings: Add Administrator ───────────────────────
    async createAdministrator() {
        const f = this.state.adminForm;
        this.state.adminFormError = null;
        this.state.adminFormSuccess = null;
        if (!f.name.trim()) {
            this.state.adminFormError = this.tr('Name required');
            return;
        }
        if (!f.email.trim()) {
            this.state.adminFormError = this.tr('Email required');
            return;
        }
        this.state.adminFormSaving = true;
        try {
            const r = await this._rpc('/api/admin/create-administrator', {
                name: f.name.trim(), email: f.email.trim(),
            });
            if (r && r.error) {
                const msgs = {
                    name_required: this.tr('Name required'),
                    email_required: this.tr('Email required'),
                    login_exists: this.tr('An account with this email already exists.'),
                    forbidden: this.tr('You are not allowed to do this.'),
                };
                this.state.adminFormError = msgs[r.error] || this.tr('Action failed.');
            } else {
                this.state.adminFormSuccess = this.tr('Administrator account created. A password-setup email was sent.');
                this.state.adminForm = { name: '', email: '' };
                setTimeout(() => { this.state.adminFormSuccess = null; }, 5000);
            }
        } catch (e) {
            this.state.adminFormError = this.tr('Action failed.');
        }
        this.state.adminFormSaving = false;
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
        // Sidebar navigation is never warehouse-scoped: clear the scope and any
        // lingering warehouse filters so the filter dropdowns show again and the
        // global lists aren't stuck on a previously-opened warehouse.
        this.state.warehouseScope = null;
        this.state.employeeWHFilter = null;
        this.state.archivedWHFilter = null;
        this.state.truckWHFilter = '';
        this.state.driverWHFilter = '';
        const fn = this[fnName];
        if (typeof fn === 'function') fn.call(this);
    }
    // JSON-RPC helper — was missing, which silently broke the profile
    // page (load + save both call this._rpc).
    async _rpc(url, params) { return rpcJson(url, params); }

    // ─── Profile ──────────────────────────────────────────
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
                    role: r.role || 'admin',
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
        return this.tr(this.state.userProfile?.role || 'Administrator');
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
                || this.tr('Update failed. Please try again.');
        }
        this.state.profileSaving = false;
    }

    // ─── Settings ─────────────────────────────────────────
    async showSettings() {
        this._navigate('settings');
        this.state.settingsSaved = false;
        try {
            const st = await this._rpc('/api/recycle/sort-thresholds', {});
            if (st && st.threshold_1 != null) {
                this.state.sortThresholds = { t1: st.threshold_1, t2: st.threshold_2 };
            }
        } catch (_e) {}
    }

    async saveSortThresholds() {
        const t = this.state.sortThresholds || {};
        try {
            const r = await this._rpc('/api/recycle/sort-thresholds/save', {
                threshold_1: parseFloat(t.t1),
                threshold_2: parseFloat(t.t2),
            });
            if (r && r.error) {
                this.notification.add(
                    this.tr('Invalid percentages: the first threshold must be lower than the second (both between 0 and 100).'),
                    { type: 'danger' });
                return;
            }
        } catch (_e) {}
        this.state.sortThresholdsSaved = true;
        setTimeout(() => { this.state.sortThresholdsSaved = false; }, 2500);
    }

    // Sign the user out and return to the login page.
    async logout() {
        const ok = await this.askConfirm(this.tr('Sign out'), this.tr('Sign out of your account.'));
        if (!ok) return;
        document.documentElement.classList.remove('o_ra_dark', 'o_ra_rtl');
        localStorage.removeItem('dw-theme');
        localStorage.removeItem('recycle_wms_dark');
        localStorage.removeItem('recycle_wms_lang');
        window.location.href = '/dawrha/logout';
    }

    // ─── Notifications ────────────────────────────────────
    async _loadNotifCount() {
        try {
            this.state.notifUnreadCount = await this.orm.searchCount(
                "recycle.notification",
                ["|", ["for_admin", "=", true], ["recipient_user_id", "=", user.userId]]
                    .concat([["is_read", "=", false]])
            );
        } catch(e) {}
    }

    async showNotifications() {
        this._navigate('notifications');
        this.state.notifLoading = true;
        try {
            // Admin sees admin-wide notifications + any addressed to them.
            const notifs = await this.orm.searchRead(
                "recycle.notification",
                ["|", ["for_admin", "=", true], ["recipient_user_id", "=", user.userId]],
                ["id", "title", "message", "notif_type", "state", "is_read",
                 "request_user_id", "create_date"],
                { limit: 50, order: "create_date desc" }
            );
            const iconMap = {
                application: '🧑‍💼', reactivation: '🔄',
                shift_change: '🕑', decision: '📩',
                role_assignment: '👤', stock_empty: '⚠️', info: '🔔',
            };
            this.state.notifications = notifs.map(n => ({
                ...n,
                icon: iconMap[n.notif_type] || '🔔',
                time: n.create_date || '',
            }));
            // Mark plain (non-actionable) ones as read.
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

    // ─── Global Warehouse Filter for Shipments/Orders ─────
    async setShipmentWHFilter(ev) {
        const val = ev.target.value;
        this.state.shipmentWHFilter = val ? parseInt(val) : null;
        const wh = this.state.warehouses.find(w => w.id === this.state.shipmentWHFilter);
        await this.openShipments(this.state.shipmentWHFilter, wh ? wh.name : null);
    }

    async setOrderWHFilter(ev) {
        const val = ev.target.value;
        this.state.orderWHFilter = val ? parseInt(val) : null;
        const wh = this.state.warehouses.find(w => w.id === this.state.orderWHFilter);
        await this.openOrders(this.state.orderWHFilter, wh ? wh.name : null);
    }

    // ─── Accepted Applicants ──────────────────────────────
    ACCEPTED_APPLICANTS_FIELDS = ["id", "partner_name", "email_from", "partner_phone",
        "job_id", "recycle_state", "recycle_stage_status",
        "recycle_email", "recycle_phone", "recycle_national_id",
        "recycle_interview_datetime", "create_date"];
    REJECTED_APPLICANTS_FIELDS = ["id", "partner_name", "email_from", "partner_phone",
        "job_id", "recycle_state", "recycle_stage_status",
        "recycle_email", "recycle_phone", "recycle_national_id",
        "recycle_interview_datetime", "create_date", "stage_id"];
    DELETED_APPLICANTS_FIELDS = ["id", "partner_name", "recycle_name", "email_from", "recycle_email",
        "partner_phone", "recycle_phone", "job_id", "recycle_state",
        "recycle_interview_datetime", "create_date"];

    _acceptedDomain() {
        const domain = [["recycle_state", "=", "accepted"]];
        const f = (this.state.acceptedFilter || '').trim();
        if (f) domain.push("|", ["partner_name", "ilike", f], ["job_id.name", "ilike", f]);
        return domain;
    }
    async openAcceptedApplicants() {
        this._navigate("accepted_applicants");
        this.state.acceptedFilter = '';
        await this._refetchAccepted();
    }
    async _refetchAccepted() {
        this.state.loading = true;
        this.state.acceptedApplicants = [];
        this.state.acceptedApplicantsHasMore = true;
        try {
            const pager = makePager(this.orm, { model: "hr.applicant", fields: this.ACCEPTED_APPLICANTS_FIELDS });
            const { rows, hasMore } = await pager.fetchFirst(this._acceptedDomain());
            this.state.acceptedApplicants = rows;
            this.state.acceptedApplicantsHasMore = hasMore;
        } finally {
            this.state.loading = false;
        }
    }
    onAcceptedFilterInput(ev) {
        this.state.acceptedFilter = ev.target.value;
        clearTimeout(this._acceptedFilterTimer);
        this._acceptedFilterTimer = setTimeout(() => this._refetchAccepted(), 400);
    }
    async loadMoreAcceptedApplicants() {
        if (this.state.view !== 'accepted_applicants') return;
        if (!this.state.acceptedApplicantsHasMore || this.state.acceptedApplicantsLoadingMore || this.state.loading) return;
        this.state.acceptedApplicantsLoadingMore = true;
        try {
            const lastId = this.state.acceptedApplicants.length
                ? this.state.acceptedApplicants[this.state.acceptedApplicants.length - 1].id : 0;
            const pager = makePager(this.orm, { model: "hr.applicant", fields: this.ACCEPTED_APPLICANTS_FIELDS });
            const { rows, hasMore } = await pager.fetchMore(this._acceptedDomain(), lastId);
            this.state.acceptedApplicants = this.state.acceptedApplicants.concat(rows);
            this.state.acceptedApplicantsHasMore = hasMore;
        } catch (e) { /* silent */ }
        this.state.acceptedApplicantsLoadingMore = false;
    }

    // ─── Rejected Applicants ──────────────────────────────
    _rejectedDomain() {
        const domain = [["recycle_state", "=", "rejected"]];
        const f = (this.state.rejectedFilter || '').trim();
        if (f) domain.push("|", ["partner_name", "ilike", f], ["job_id.name", "ilike", f]);
        return domain;
    }
    async openRejectedApplicants() {
        this._navigate("rejected_applicants");
        this.state.rejectedFilter = '';
        await this._refetchRejected();
    }
    async _refetchRejected() {
        this.state.loading = true;
        this.state.rejectedApplicants = [];
        this.state.rejectedApplicantsHasMore = true;
        try {
            const pager = makePager(this.orm, { model: "hr.applicant", fields: this.REJECTED_APPLICANTS_FIELDS });
            const { rows, hasMore } = await pager.fetchFirst(this._rejectedDomain());
            this.state.rejectedApplicants = rows;
            this.state.rejectedApplicantsHasMore = hasMore;
        } finally {
            this.state.loading = false;
        }
    }
    onRejectedFilterInput(ev) {
        this.state.rejectedFilter = ev.target.value;
        clearTimeout(this._rejectedFilterTimer);
        this._rejectedFilterTimer = setTimeout(() => this._refetchRejected(), 400);
    }
    async loadMoreRejectedApplicants() {
        if (this.state.view !== 'rejected_applicants') return;
        if (!this.state.rejectedApplicantsHasMore || this.state.rejectedApplicantsLoadingMore || this.state.loading) return;
        this.state.rejectedApplicantsLoadingMore = true;
        try {
            const lastId = this.state.rejectedApplicants.length
                ? this.state.rejectedApplicants[this.state.rejectedApplicants.length - 1].id : 0;
            const pager = makePager(this.orm, { model: "hr.applicant", fields: this.REJECTED_APPLICANTS_FIELDS });
            const { rows, hasMore } = await pager.fetchMore(this._rejectedDomain(), lastId);
            this.state.rejectedApplicants = this.state.rejectedApplicants.concat(rows);
            this.state.rejectedApplicantsHasMore = hasMore;
        } catch (e) { /* silent */ }
        this.state.rejectedApplicantsLoadingMore = false;
    }

    // kept for backward compat (not called anymore)
    async openAcceptedRejected() {
        return this.openAcceptedApplicants();
    }

    get filteredAccepted() {
        // Filtering now happens server-side (see _acceptedDomain).
        return this.state.acceptedApplicants;
    }

    get filteredRejected() {
        // Filtering now happens server-side (see _rejectedDomain).
        return this.state.rejectedApplicants;
    }

    // ─── Deleted Account Applicants ───────────────────────
    async openDeletedApplicants() {
        this._navigate("deleted_applicants");
        this.state.loading = true;
        this.state.deletedApplicants = [];
        this.state.deletedApplicantsHasMore = true;
        try {
            const pager = makePager(this.orm, { model: "hr.applicant", fields: this.DELETED_APPLICANTS_FIELDS });
            const { rows, hasMore } = await pager.fetchFirst([["recycle_account_deleted", "=", true]]);
            this.state.deletedApplicants = rows;
            this.state.deletedApplicantsHasMore = hasMore;
        } finally {
            this.state.loading = false;
        }
    }
    async loadMoreDeletedApplicants() {
        if (this.state.view !== 'deleted_applicants') return;
        if (!this.state.deletedApplicantsHasMore || this.state.deletedApplicantsLoadingMore || this.state.loading) return;
        this.state.deletedApplicantsLoadingMore = true;
        try {
            const lastId = this.state.deletedApplicants.length
                ? this.state.deletedApplicants[this.state.deletedApplicants.length - 1].id : 0;
            const pager = makePager(this.orm, { model: "hr.applicant", fields: this.DELETED_APPLICANTS_FIELDS });
            const { rows, hasMore } = await pager.fetchMore([["recycle_account_deleted", "=", true]], lastId);
            this.state.deletedApplicants = this.state.deletedApplicants.concat(rows);
            this.state.deletedApplicantsHasMore = hasMore;
        } catch (e) { /* silent */ }
        this.state.deletedApplicantsLoadingMore = false;
    }

    // ─── Zones ────────────────────────────────────────────
    async openZonesList() {
        this._navigate("zones_list");
        this.state.loading = true;
        if (!this.state.warehouses.length) {
            this.state.warehouses = await this.orm.searchRead("recycle.warehouse", [["state", "=", "active"]], ["id", "name"]);
        }
        this.state.zones = await this.orm.searchRead(
            "recycle.zone", [],
            ["id", "name", "zone_type", "warehouse_id"],
            { order: "warehouse_id asc, zone_type asc" }
        );
        this.state.loading = false;
    }

    async openStockList() {
        this._navigate("stock_list");
        this.state.loading = true;
        this.state.stockZoneFilter = '';
        this.state.stockCondFilter = '';
        if (!this.state.warehouses.length) {
            this.state.warehouses = await this.orm.searchRead("recycle.warehouse", [["state", "=", "active"]], ["id", "name"]);
        }
        this.state.stock = await this.orm.searchRead(
            "recycle.stock", [],
            ["warehouse_id", "product_id", "quantity", "zone_id", "condition"],
            { order: "warehouse_id asc" }
        );
        // All storage zones with their warehouse — the view shows only the
        // zones of the currently selected warehouse (none when "All").
        this.state.stockZones = await this.orm.searchRead(
            "recycle.zone", [["zone_type", "=", "storage"]],
            ["id", "name", "warehouse_id"], { order: "name asc" }
        );
        this.state.loading = false;
    }

    // Storage zones belonging to the selected warehouse only.
    // Empty when "All warehouses" is selected — the zone filter is hidden.
    get stockZonesForWH() {
        if (!this.state.stockWHFilter) return [];
        return this.state.stockZones.filter(
            z => z.warehouse_id && z.warehouse_id[0] === this.state.stockWHFilter);
    }

    get filteredStock() {
        let list = this.state.stockWHFilter
            ? this.state.stock.filter(s => s.warehouse_id && s.warehouse_id[0] === this.state.stockWHFilter)
            : this.state.stock;
        if (this.state.stockWHFilter && this.state.stockZoneFilter) {
            list = list.filter(s => s.zone_id && s.zone_id[0] === Number(this.state.stockZoneFilter));
        }
        if (this.state.stockCondFilter) {
            list = list.filter(s => s.condition === this.state.stockCondFilter);
        }
        return list;
    }

    async openProductsList() {
        this._navigate("products_list");
        this.state.loading = true;
        this.state.products = await this.orm.searchRead(
            "recycle.product", [],
                    ["name", "category_id", "price_factory", "price_free_facility", "weight", "uom_id", "active"],
            { order: "name asc" }
        );
        this.state.loading = false;
    }

    /**
     * Units offered when creating a material come from recycle.measurement.unit
     * — the table mirrored from the backend — so a material can never be given
     * a unit the backend does not know. Archived units (deleted in the backend)
     * are excluded, which is what makes a backend delete take effect here.
     */
    async _loadUomList(force) {
        if (!force && this.state.uomList && this.state.uomList.length) return;
        try {
            this.state.uomList = await this.orm.searchRead(
                'recycle.measurement.unit', [],
                ['id', 'name', 'code', 'allows_tolerance'], { order: 'name asc' });
        } catch (e) { this.state.uomList = []; }
    }

    /**
     * Price sheet of ONE material.
     *
     * A material is priced per buyer tier (factory / free facility) AND, when
     * it has material conditions, per condition — so a single column in the
     * list could only ever show one of several numbers. All of it is authored
     * in the backend and mirrored into recycle.product.condition.price; a row
     * with an EMPTY condition_code is a material that has no conditions, and
     * is shown as its plain price.
     *
     * Read fresh on every open (never cached): a price edited or deleted in
     * the backend must be visible here the moment the admin looks.
     */
    async openProductPrices(product) {
        this.state.pricesProduct = product;
        this.state.pricesModal = true;
        this.state.pricesLoading = true;
        this.state.pricesError = null;
        this.state.priceRows = { factory: [], free_facility: [] };
        try {
            const rows = await this.orm.searchRead(
                'recycle.product.condition.price',
                [['product_id', '=', product.id]],
                // The OFFER travels with the price, and did not before: this
                // read asked for `price` alone, so the sheet showed the list
                // price while the apps were selling at another number — and
                // nothing on the screen said so. The Odoo form view had been
                // taught to show both; this dashboard, which is where the
                // admin actually looks, had not.
                //
                // `has_offer` and `price_display` are computed against the
                // CLOCK rather than stored, so they are read here and are
                // correct at the instant they are looked at: an offer that has
                // run out reads as no offer without anything having to expire
                // it.
                //
                // `offer_percentage` comes from the backend rather than being
                // derived here from the two figures beside it: it is computed
                // against the tier the offer actually faces, and re-deriving it
                // from two rounded numbers on this side would drift from what
                // the buyer is shown in the app.
                ['tier', 'condition_code', 'condition_name', 'price',
                 'has_offer', 'offer_price', 'offer_percentage',
                 'offer_valid_until', 'price_display'],
                { order: 'tier asc, condition_code asc' });
            const grouped = { factory: [], free_facility: [] };
            for (const r of rows) {
                if (grouped[r.tier]) grouped[r.tier].push(r);
            }
            this.state.priceRows = grouped;
        } catch (e) {
            this.state.pricesError = this.tr('Could not load prices.');
        }
        this.state.pricesLoading = false;
    }

    /**
     * Does this material have a price for ANY tier?
     *
     * A material with none is not a material with two empty tables — it has
     * simply not been priced yet, and saying so once beats repeating "no price
     * for this tier" under each heading, which reads as two problems.
     */
    get productHasAnyPrice() {
        const rows = this.state.priceRows || {};
        return Object.keys(rows).some((tier) => (rows[tier] || []).length > 0);
    }

    closeProductPrices() {
        this.state.pricesModal = false;
        this.state.pricesProduct = null;
    }

    /**
     * Label of one price line. Backend rows carry the condition name already;
     * a row with no condition is the material's plain price.
     */
    priceRowLabel(row) {
        if (!row.condition_code) return this.tr('Plain price (no conditions)');
        return row.condition_name || row.condition_code;
    }

    /**
     * "11% off" beside the two prices.
     *
     * Built here rather than in the template so the number is rounded once and
     * the word around it stays translatable — a percentage glued to a literal
     * "%" in QWeb cannot be reordered for Arabic, where the figure and the word
     * do not sit in the same order.
     *
     * Fractions are kept to one place: the backend computes against the tier
     * the offer actually faces and sends e.g. 11.11, and rounding that to 11
     * here would disagree with the figure the app shows the buyer.
     */
    offerPercentLabel(row) {
        const pct = Number(row.offer_percentage || 0);
        if (!pct) return '';
        const shown = Math.round(pct * 10) / 10;
        return this.tr('{pct}% off').replace('{pct}', String(shown));
    }

    async openProductCategoriesList() {
        this._navigate("product_categories_list");
        this.state.loading = true;
        this.state.productCategories = await this.orm.searchRead(
            "recycle.product.category", [],
            ["name"],
            { order: "name asc" }
        );
        this.state.loading = false;
    }

    setStockWHFilter(ev) {
        const val = ev.target.dataset && ev.target.dataset.filter !== undefined
            ? ev.target.dataset.filter : ev.target.value;
        this.state.stockWHFilter = val ? parseInt(val) : null;
        // Zones belong to a warehouse — leaving a stale zone selected after
        // switching warehouses would silently hide everything.
        this.state.stockZoneFilter = '';
    }

    setStockCondFilter(cond) {
        this.state.stockCondFilter = cond || '';
    }

    async setProductsFilter(ev) {
        this.state.productsFilter = ev.target.value;
        await this.openProductsList();
    }

    openZoneCreate() {
        this.state.zoneForm = { name: '', zone_type: 'storage', warehouse_id: null };
        this.state.zoneError = null;
        this.state.zoneCreateMode = true;
        this._navigate("zone_create");
    }

    openZoneDetail(zone) {
        this.state.selectedZone = { ...zone };
        this._navigate("zone_detail");
    }

    cancelZoneCreate() {
        this.state.zoneCreateMode = false;
        this.goBack();
    }

    async saveNewZone() {
        const f = this.state.zoneForm;
        if (!f.name.trim()) { this.state.zoneError = "Zone name is required."; return; }
        if (!f.warehouse_id) { this.state.zoneError = "Warehouse is required."; return; }
        this.state.zoneSaving = true;
        this.state.zoneError = null;
        try {
            await this.orm.create("recycle.zone", [{
                name: f.name.trim(),
                zone_type: f.zone_type,
                warehouse_id: parseInt(f.warehouse_id),
            }]);
            await this.openZonesList();
        } catch (e) {
            this.state.zoneError = e.message || "Create failed.";
            this.state.zoneSaving = false;
        }
    }

    // ─── Attendance ───────────────────────────────────────
    async openAttendance(filterWarehouseId, dateStr) {
        if (typeof filterWarehouseId !== "number") { filterWarehouseId = null; }
        this.state.attendanceWHFilter = filterWarehouseId || null;
        if (dateStr !== undefined) { this.state.attendanceDate = dateStr; }
        this._navigate("attendance_list");
        this.state.loading = true;
        if (!this.state.warehouses.length) {
            this.state.warehouses = await this.orm.searchRead("recycle.warehouse", [["state", "=", "active"]], ["id", "name"]);
        }
        const domain = [];
        if (this.state.attendanceDate) {
            domain.push(["date", "=", this.state.attendanceDate]);
        }
        if (filterWarehouseId) {
            domain.push(["warehouse_id", "=", filterWarehouseId]);
        }
        const records = await this.orm.searchRead(
            "recycle.attendance", domain,
            ["employee_user_id", "warehouse_id", "shift_id",
             "check_in_display", "check_out_display",
             "status", "late_minutes", "early_leave_minutes", "work_hours"],
            { order: "id desc", limit: 500 }
        );
        let present = 0, late = 0, early = 0;
        for (const r of records) {
            if (r.status === "present") present++;
            else if (r.status === "late" || r.status === "late_and_early") late++;
            else if (r.status === "early_leave") early++;
            r._empName = Array.isArray(r.employee_user_id) ? r.employee_user_id[1] : "—";
            r._warehouseName = Array.isArray(r.warehouse_id) ? r.warehouse_id[1] : "—";
            r._shiftName = Array.isArray(r.shift_id) ? r.shift_id[1] : "—";
            const wh = r.work_hours || 0;
            const h = Math.floor(wh);
            const m = Math.round((wh - h) * 60);
            r._workDisplay = wh > 0 ? `${h}h ${m}m` : "—";
        }
        this.state.attendance = records;
        this.state.attendanceStats = { present, late, early };
        this.state.loading = false;
    }

    async setAttendanceWHFilter(ev) {
        // Works for a <select> (ev.target.value) and legacy pill buttons.
        const val = (ev.target.tagName === 'SELECT' || ev.target.value !== undefined)
            ? ev.target.value : (ev.target.dataset && ev.target.dataset.filter);
        const whId = val ? parseInt(val) : null;
        this.state.attendanceWHFilter = whId;
        await this.openAttendance(whId, this.state.attendanceDate);
    }

    async onAttendanceDateInput(ev) {
        const val = ev.target.value;
        this.state.attendanceDate = val;
        await this.openAttendance(this.state.attendanceWHFilter, val);
    }

    get attendanceTotal() { return this.state.attendance.length; }

    attendanceStatusLabel(s) {
        return { present: "Present", late: "Late", early_leave: "Left Early", late_and_early: "Late & Early" }[s] || s;
    }

    attendanceStatusClass(s) {
        if (s === "present") return "o_ra_badge_success";
        if (s === "late" || s === "late_and_early") return "o_ra_badge_danger";
        if (s === "early_leave") return "o_ra_badge_warning";
        return "o_ra_badge_muted";
    }

    // ─── Legacy helpers ──
    openEmployees() {
        this.actionService.doAction({
            type: "ir.actions.client",
            tag: "recycle_employees_board",
            name: "Employees",
        });
    }

    openApplications() {
        this.openApplicantsList();
    }

    openShiftsHub() {
        this._navigate("shifts_hub");
    }

    // ─── Shift time helpers ───────────────────────────────
    shiftDuration(start, end) {
        let d = (end || 0) - (start || 0);
        if (d <= 0) d += 24;              // overnight (e.g. 22:00 → 06:00)
        return Math.round(d * 100) / 100;
    }
    shiftIsRealistic(start, end) {
        // (startMin, startMax, endMin, endMax)
        const windows = [
            [6.0, 8.5, 14.0, 16.5],       // morning
            [14.0, 16.5, 22.0, 23.5],     // afternoon
            [22.0, 24.0, 6.0, 8.0],       // night
        ];
        return windows.some(([sm, sx, em, ex]) =>
            start >= sm && start <= sx && end >= em && end <= ex);
    }
    // Hard errors (block): under 6h or over 12h. Returns message or null.
    shiftTimeError(f) {
        if (!f.name.trim()) return this.tr('Shift name is required.');
        if (f.start_time === f.end_time) return this.tr('Start and end time cannot be the same.');
        const dur = this.shiftDuration(f.start_time, f.end_time);
        if (dur < 6) return this.tr('A shift must last at least 6 hours.');
        if (dur > 12) return this.tr('A shift cannot exceed 12 hours.');
        if ((f.tolerance || 0) < 0) return this.tr('Tolerance cannot be negative.');
        return null;
    }
    // Which confirmation is needed for a valid-length shift, or null.
    // 'long'   → 9h–12h band (accept/reject).
    // 'unusual'→ 6h–9h but outside the usual morning/afternoon/night windows.
    shiftWarnType(f) {
        const dur = this.shiftDuration(f.start_time, f.end_time);
        if (dur > 9) return 'long';
        if (!this.shiftIsRealistic(f.start_time, f.end_time)) return 'unusual';
        return null;
    }
    get shiftWarnMessage() {
        return this.state.shiftWarnType === 'long'
            ? this.tr('This shift is longer than the recommended 9 hours (up to 12h). Do you want to continue?')
            : this.tr('These times are outside the usual shift hours. Do you want to continue?');
    }

    // ─── Shift Create Form ────────────────────────────────
    async openCreateShift() {
        this.state.shiftForm = { name: '', start_time: 8.0, end_time: 17.0, tolerance: 15,
                                 shift_type: 'warehouse', is_global: false, warehouse_ids: [] };
        this.state.shiftError = null;
        this.state.shiftSuccess = null;
        this.state.shiftWarnType = null;
        this.state.shiftConfirmed = false;
        this.state.shiftEditMode = false;
        this.state.selectedShift = null;
        if (!this.state.warehouses.length) {
            this.state.warehouses = await this.orm.searchRead("recycle.warehouse", [["state", "=", "active"]], ["id", "name"]);
        }
        this._navigate("shift_create");
    }

    setShiftTime(field, value) {
        const [h, m] = value.split(':').map(Number);
        this.state.shiftForm[field] = h + (m / 60);
    }

    // ── Scope: global (all warehouses) vs specific (one or more) ──
    setShiftScope(isGlobal) {
        this.state.shiftForm.is_global = !!isGlobal;
        if (isGlobal) this.state.shiftForm.warehouse_ids = [];
    }
    toggleShiftWarehouse(id) {
        const arr = this.state.shiftForm.warehouse_ids;
        const i = arr.indexOf(id);
        if (i >= 0) arr.splice(i, 1); else arr.push(id);
    }
    isShiftWarehouse(id) {
        return this.state.shiftForm.warehouse_ids.includes(id);
    }
    // Editing a SPECIFIC shift: tick "make global" → clears warehouses.
    setShiftMakeGlobal(makeGlobal) {
        this.state.shiftForm.is_global = !!makeGlobal;
        if (makeGlobal) this.state.shiftForm.warehouse_ids = [];
    }

    _shiftScopeError(f) {
        if (!f.is_global && (!f.warehouse_ids || !f.warehouse_ids.length)) {
            return this.tr('Choose at least one warehouse, or make the shift global.');
        }
        return null;
    }

    async saveShift() {
        const f = this.state.shiftForm;
        const err = this.shiftTimeError(f) || this._shiftScopeError(f);
        if (err) { this.state.shiftError = err; return; }
        // Tiered confirmation (long shift 9-12h, or unusual times) unless the
        // user already pressed "continue" on the warning modal.
        if (!this.state.shiftConfirmed) {
            const warn = this.shiftWarnType(f);
            if (warn) { this.state.shiftWarnType = warn; return; }
        }
        this.state.shiftConfirmed = false;
        this.state.shiftWarnType = null;
        this.state.shiftSaving = true;
        this.state.shiftError = null;
        try {
            await this.orm.create('recycle.shift', [{
                name: f.name.trim(),
                start_time: f.start_time,
                end_time: f.end_time,
                tolerance: f.tolerance || 15,
                shift_type: f.shift_type || 'warehouse',
                is_global: f.is_global,
                warehouse_ids: [[6, 0, f.is_global ? [] : f.warehouse_ids]],
            }]);
            this.state.shiftSuccess = this.tr('Shift created successfully.');
            setTimeout(() => { this.state.shiftSuccess = null; this.openShiftsList(); }, 1500);
        } catch(e) {
            this.state.shiftError = (e && e.data && e.data.message) || e.message || this.tr('Failed to save shift.');
        }
        this.state.shiftSaving = false;
    }
    // Modal handlers for the shift warning (long / unusual).
    confirmUnusualTimes() {
        this.state.shiftConfirmed = true;
        this.state.shiftWarnType = null;
        if (this.state.shiftEditMode) this.saveEditShift();
        else this.saveShift();
    }
    cancelUnusualTimes() {
        this.state.shiftWarnType = null;
        this.state.shiftConfirmed = false;
    }

    openShifts() {
        this.actionService.doAction("recycle_warehouse.action_recycle_shift_manager");
    }

    // ─── Shifts List ──────────────────────────────────────
    async openShiftsList() {
        this._navigate("shifts_list");
        this.state.shiftDeleteWarn = null;
        this.state.loading = true;
        this.state.shifts = await this.orm.searchRead(
            "recycle.shift", [],
            ["id", "name", "start_time", "end_time", "tolerance", "employee_count", "active", "assigned_employee_names", "is_global", "warehouse_ids", "shift_type"],
            { order: "name asc" }
        );
        this.state.loading = false;
    }

    // Delete: blocked when employees are assigned.
    async deleteShift(shift) {
        if (shift.employee_count > 0) {
            this.state.shiftDeleteWarn = {
                name: shift.name,
                employees: shift.assigned_employee_names || '',
            };
            return;
        }
        const ok = await this.askConfirm(this.tr('Delete shift'), this.tr('Delete this shift?'));
        if (!ok) return;
        try {
            await this.orm.call("recycle.shift", "action_recycle_delete_shift", [[shift.id]]);
            this.notification.add(this.tr('Shift deleted successfully.'), { type: "success" });
            await this.openShiftsList();
        } catch (e) {
            this.notification.add(
                (e && e.data && e.data.message) || this.tr('Failed to delete shift.'),
                { type: "danger" });
        }
    }
    dismissShiftDeleteWarn() { this.state.shiftDeleteWarn = null; }

    // ─── Language Switch (client-side only — reactive via tr() method) ───────
    setLang(lang) {
        // lang: 'en' or 'ar'
        this.state.lang = lang;
        // tr() reads state.lang and also syncs localStorage — so OWL re-renders
        // with translated text automatically. No page reload needed.
        this.notification.add(
            lang === 'ar' ? 'تم التبديل إلى العربية 🇸🇦' : 'Switched to English 🇺🇸',
            { type: 'success', sticky: false }
        );
        // Notify backend menu translator
        try { if (window.dwTranslateMenus) setTimeout(window.dwTranslateMenus, 50); } catch (_) {}
        try { window.dispatchEvent(new CustomEvent('dw-lang-change', { detail: { lang: lang } })); } catch (_) {}
        // Re-render charts with translated labels
        setTimeout(() => { this.renderDonutChart(); this.renderBarChart(); }, 100);
    }

    openLanguageSettings() {
        this._navigate('settings');
    }

    // ─── Shift Edit ───────────────────────────────────────
    async openEditShift(shift) {
        this.state.selectedShift = shift;
        // warehouse_ids arrives as an array of ids from searchRead.
        const whIds = Array.isArray(shift.warehouse_ids) ? shift.warehouse_ids.slice() : [];
        this.state.shiftForm = {
            name: shift.name || '',
            start_time: shift.start_time,
            end_time: shift.end_time,
            tolerance: shift.tolerance || 15,
            shift_type: shift.shift_type || 'warehouse',
            is_global: !!shift.is_global,
            warehouse_ids: whIds,
        };
        // Remember the shift's original scope so the form can enforce the
        // rule "a global shift can never become specific".
        this.state.shiftWasGlobal = !!shift.is_global;
        this.state.shiftError = null;
        this.state.shiftSuccess = null;
        this.state.shiftSaving = false;
        this.state.shiftWarnType = null;
        this.state.shiftConfirmed = false;
        this.state.shiftEditMode = true;
        if (!this.state.warehouses.length) {
            this.state.warehouses = await this.orm.searchRead("recycle.warehouse", [["state", "=", "active"]], ["id", "name"]);
        }
        this._navigate("shift_edit");
    }

    async saveEditShift() {
        const f = this.state.shiftForm;
        const shift = this.state.selectedShift;
        if (!shift) { this.state.shiftError = this.tr('No shift selected.'); return; }
        const err = this.shiftTimeError(f);
        if (err) { this.state.shiftError = err; return; }
        // A shift that is already global stays global — only name/time/tolerance
        // may change. A specific shift needs a warehouse unless it is being
        // converted to global.
        if (!this.state.shiftWasGlobal) {
            const scopeErr = this._shiftScopeError(f);
            if (scopeErr) { this.state.shiftError = scopeErr; return; }
        }
        if (!this.state.shiftConfirmed) {
            const warn = this.shiftWarnType(f);
            if (warn) { this.state.shiftWarnType = warn; return; }
        }
        this.state.shiftConfirmed = false;
        this.state.shiftWarnType = null;
        const timesChanged = (f.start_time !== shift.start_time || f.end_time !== shift.end_time);
        this.state.shiftSaving = true;
        this.state.shiftError = null;
        try {
            const vals = {
                name: f.name.trim(),
                start_time: f.start_time,
                end_time: f.end_time,
                tolerance: f.tolerance || 15,
            };
            // Scope is editable only for shifts that started out specific.
            // (A global shift can never turn specific — its scope is locked.)
            if (!this.state.shiftWasGlobal) {
                vals.is_global = f.is_global;
                vals.warehouse_ids = [[6, 0, f.is_global ? [] : f.warehouse_ids]];
            }
            await this.orm.write('recycle.shift', [shift.id], vals);
            // Editing the shift's times updates every assigned employee at once
            // (they reference the shift, so their schedule follows it).
            this.state.shiftSuccess = timesChanged
                ? this.tr('Shift updated and times synchronized for all employees.')
                : this.tr('Shift updated successfully.');
            var self = this;
            setTimeout(function () {
                self.state.shiftSuccess = null;
                self.state.shiftEditMode = false;
                self.openShiftsList().catch(function (e2) {
                    if (console && console.warn) console.warn('Shift list reload:', e2);
                });
            }, 1600);
        } catch(e) {
            this.state.shiftError = (e && e.data && e.data.message) || e.message || this.tr('Failed to update shift.');
            this.state.shiftSaving = false;
        }
    }

    // Confirm/cancel already defined for create — reuse for edit via saveEditShift.
    confirmUnusualTimesEdit() { this.state.shiftConfirmed = true; this.state.shiftWarnType = null; this.saveEditShift(); }

    cancelEditShift() {
        this.state.shiftEditMode = false;
        this.state.shiftError = null;
        this.goBack();
    }

    // ─── Float to Time helper ─────────────────────────────
    floatToTime(val) {
        const h = Math.floor(val || 0);
        const m = Math.round(((val || 0) - h) * 60);
        return String(h).padStart(2,'0') + ':' + String(m).padStart(2,'0');
    }

    // ─── Label Helpers ────────────────────────────────────
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
            applicant:  { applied: this.tr("Applied"), interview: this.tr("Interview"),
                          accepted: this.tr("Accepted"), rejected: this.tr("Rejected") },
            role:       { manager: this.tr("Warehouse Manager"), input: this.tr("Input Employee"),
                          sorting: this.tr("Sorting Employee"), output: this.tr("Output Employee") },
            zone_type:  { receiving: this.tr("Receiving"), sorting: this.tr("Sorting"),
                          storage: this.tr("Storage"), output: this.tr("Output") },
            job_type:   { manager: this.tr("Warehouse Manager"), employee: this.tr("General Employee"),
                          input: this.tr("Input Employee"), sorting: this.tr("Sorting Employee"),
                          output: this.tr("Output Employee") },
            stage_status:{ pending: this.tr("Pending"), approved: this.tr("Approved"),
                           rejected: this.tr("Rejected") },
            condition:  { excellent: this.tr("Excellent"), good: this.tr("Good"),
                          poor: this.tr("Poor"), damaged: this.tr("Damaged") },
        };
        return (map[type] && map[type][state]) || state || '—';
    }

    conditionBadgeClass(condition) {
        return {
            excellent: 'o_ra_badge_success',
            good: 'o_ra_badge_info',
            poor: 'o_ra_badge_warning',
            damaged: 'o_ra_badge_danger',
        }[condition] || 'o_ra_badge_muted';
    }

    stateBadgeClass(state) {
        const good = ["accepted","working","completed","resolved","approved","published"];
        const bad  = ["rejected","out_of_service","retired","cancelled"];
        const warn = ["pending","in_progress","interview","receiving"];
        if (good.includes(state)) return "o_ra_badge_success";
        if (bad.includes(state))  return "o_ra_badge_danger";
        if (warn.includes(state)) return "o_ra_badge_warn";
        return "o_ra_badge_muted";
    }

    rejectedAtStage(app) {
        if (app.stage_id && Array.isArray(app.stage_id)) return app.stage_id[1];
        return app.recycle_state ? this.stateLabel(app.recycle_state, "applicant") : "—";
    }

    get donutTotal() {
        return this.chartItems.reduce((s, i) => s + i.value, 0);
    }

    get chartHasData() {
        return this.donutTotal > 0;
    }

    formatDate(val) {
        if (!val) return "—";
        try { return new Date(val).toLocaleDateString("en-GB"); }
        catch { return val; }
    }

    formatDatetime(val) {
        if (!val) return "—";
        try { return new Date(val).toLocaleString("en-GB"); }
        catch { return val; }
    }

    m2oName(field) {
        if (!field) return "—";
        if (Array.isArray(field)) return field[1] || "—";
        if (typeof field === "string") return field;
        return "—";
    }

    // ─── Damage, per shipment ─────────────────────────────────────────
    //
    // The manager decides each write-off inside their own warehouse. What was
    // missing was any way for the administrator to see the decisions side by
    // side and get back from a figure to the delivery behind it — the totals
    // report could say a warehouse lost 300 kg last month and nothing could
    // say which lorries that came off.

    async openDamageByShipment() {
        this._navigate('damage_shipments');
        this.state.loading = true;
        this.state.damageOpenId = null;
        await this._loadDamageRows();
        this.state.loading = false;
    }

    async _loadDamageRows() {
        try {
            this.state.damageRows = await this.orm.call(
                'recycle.damage.entry', 'by_shipment', [], {
                    warehouse_ids: this.state.damageWHFilter
                        ? [this.state.damageWHFilter] : null,
                    date_from: this.state.damageFrom || null,
                    date_to: this.state.damageTo || null,
                });
        } catch (e) {
            this.state.damageRows = [];
        }
    }

    /** "All warehouses" is the empty option, so it has to survive parseInt. */
    async setDamageWHFilter(ev) {
        const raw = ev.target.value;
        this.state.damageWHFilter = raw ? parseInt(raw, 10) : null;
        await this.onDamageFilterChange();
    }

    /** Re-ask the server whenever a filter changes — it owns the scoping. */
    async onDamageFilterChange() {
        this.state.loading = true;
        this.state.damageOpenId = null;
        await this._loadDamageRows();
        this.state.loading = false;
    }

    /** Free-text search runs locally: the rows are already here. */
    get damageRowsFiltered() {
        const q = (this.state.damageSearch || '').toLowerCase().trim();
        if (!q) return this.state.damageRows || [];
        return (this.state.damageRows || []).filter((r) =>
            (r.shipment_name || '').toLowerCase().includes(q)
            || (r.warehouse_name || '').toLowerCase().includes(q)
            || (r.sorter_name || '').toLowerCase().includes(q)
            || (r.driver_name || '').toLowerCase().includes(q)
            || (r.lines || []).some(
                (l) => (l.product_name || '').toLowerCase().includes(q)));
    }

    toggleDamageRow(shipmentId) {
        this.state.damageOpenId =
            this.state.damageOpenId === shipmentId ? null : shipmentId;
    }

    /** How the manager's decision reads, and how it is coloured. */
    damageDecisionLabel(row) {
        return {
            pending: this.tr('Awaiting manager'),
            approved: this.tr('Written off'),
            rejected: this.tr('Refused — stored instead'),
        }[row.damage_request_state] || this.tr('No request');
    }

    damageDecisionClass(row) {
        return {
            pending: 'o_ra_badge_warning',
            approved: 'o_ra_badge_danger',
            rejected: 'o_ra_badge_success',
        }[row.damage_request_state] || 'o_ra_badge_muted';
    }

    // ─── Archived shipments / orders (admin sees who archived them) ───
    ARCHIVED_SHIPMENT_FIELDS = ['id', 'name', 'warehouse_id', 'driver_name', 'state',
        'received_at', 'recycle_archived_by'];
    ARCHIVED_ORDER_FIELDS = ['id', 'name', 'customer_name', 'warehouse_id', 'state',
        'invoice_number', 'amount_total', 'recycle_archived_by'];

    async openArchivedShipments() {
        this._navigate('archived_shipments');
        this.state.loading = true;
        this.state.archivedShipments = [];
        this.state.archivedShipmentsHasMore = true;
        try {
            const pager = makePager(this.orm, { model: 'recycle.shipment', fields: this.ARCHIVED_SHIPMENT_FIELDS });
            const { rows, hasMore } = await pager.fetchFirst([['recycle_archived', '=', true]]);
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
            const pager = makePager(this.orm, { model: 'recycle.shipment', fields: this.ARCHIVED_SHIPMENT_FIELDS });
            const { rows, hasMore } = await pager.fetchMore([['recycle_archived', '=', true]], lastId);
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
            const pager = makePager(this.orm, { model: 'recycle.order', fields: this.ARCHIVED_ORDER_FIELDS });
            const { rows, hasMore } = await pager.fetchFirst([['recycle_archived', '=', true]]);
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
            const pager = makePager(this.orm, { model: 'recycle.order', fields: this.ARCHIVED_ORDER_FIELDS });
            const { rows, hasMore } = await pager.fetchMore([['recycle_archived', '=', true]], lastId);
            this.state.archivedOrders = this.state.archivedOrders.concat(rows);
            this.state.archivedOrdersHasMore = hasMore;
        } catch (e) { /* silent */ }
        this.state.archivedOrdersLoadingMore = false;
    }

    async unarchiveShipment(s) {
        try {
            await this.orm.call('recycle.shipment', 'action_unarchive_recycle', [[s.id]]);
            this.state.archivedShipments = this.state.archivedShipments.filter(x => x.id !== s.id);
            this.notification.add(this.tr('Shipment restored.'), { type: 'success' });
        } catch (e) {}
    }

    async unarchiveOrder(o) {
        try {
            await this.orm.call('recycle.order', 'action_unarchive_recycle', [[o.id]]);
            this.state.archivedOrders = this.state.archivedOrders.filter(x => x.id !== o.id);
            this.notification.add(this.tr('Order restored.'), { type: 'success' });
        } catch (e) {}
    }

    // ─── Materials: SUGGEST (admin) ────────────────────────────────────
    // Replaces the old "Add Product". A material is only visible to a buyer
    // once it has a price list for that buyer's tier, and prices are authored
    // in the backend — so a material created from here appeared to nobody and
    // could be ordered by no one. The admin proposes instead; the backend
    // administrator creates the real material with its prices.
    async openProductSuggest() {
        // A suggestion is a name + a category + pictures + a description — NO
        // unit (the unit is chosen later, when the real material is authored in
        // the backend), matching the backend's own suggestion shape.
        this.state.productForm = { name: '', category_id: '', description: '' };
        this.state.productImages = [];
        this.state.productError = null;
        this.state.productSuccess = null;
        if (!this.state.productCategories.length) {
            try {
                this.state.productCategories = await this.orm.searchRead(
                    'recycle.product.category', [], ['id', 'name'], { order: 'name asc' });
            } catch (e) {}
        }
        this._navigate('product_suggest');
    }

    /** Read the chosen image files into base64 so they can be attached on save. */
    onSuggestImageChange(ev) {
        const files = [...(ev.target.files || [])];
        const readOne = (file) => new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = () => {
                // Strip the "data:...;base64," prefix — ir.attachment wants the
                // raw base64 in `datas`.
                const s = String(reader.result || '');
                resolve({ name: file.name, datas: s.slice(s.indexOf(',') + 1) });
            };
            reader.onerror = () => resolve(null);
            reader.readAsDataURL(file);
        });
        Promise.all(files.map(readOne)).then((imgs) => {
            this.state.productImages = imgs.filter(Boolean);
        });
    }

    async saveProductSuggestion() {
        const f = this.state.productForm;
        if (!f.name.trim()) { this.state.productError = this.tr('Material name is required.'); return; }
        this.state.productSaving = true;
        this.state.productError = null;
        try {
            // Pictures first: create the attachments, then hand their ids to the
            // suggestion so they are present the moment it is created — the model
            // auto-pushes on create and its `_image_urls()` must find them.
            let imageIds = [];
            const imgs = this.state.productImages || [];
            if (imgs.length) {
                imageIds = await this.orm.create('ir.attachment',
                    imgs.map((im) => ({ name: im.name, datas: im.datas, mimetype: false })));
            }
            const [id] = await this.orm.create('recycle.product.suggestion', [{
                name: f.name.trim(),
                category_id: f.category_id ? parseInt(f.category_id) : false,
                description: (f.description || '').trim() || false,
                image_ids: imageIds.length ? [[6, 0, imageIds]] : false,
            }]);
            // Saved first, sent second: if the push fails the proposal is still
            // on file and re-sendable, instead of being lost with the click.
            const result = await this.orm.call(
                'recycle.product.suggestion', 'action_submit', [[id]]);
            this.state.productSaving = false;

            // action_submit records a transport failure and hands back a
            // notification action rather than raising — so a failure arrives
            // here as a value, not as an exception.
            const failure = result && result.params && result.params.type === 'danger';
            if (failure) {
                this.state.productError = result.params.message
                    || this.tr('Could not reach the backend. The suggestion was saved — try sending it again.');
                return;
            }

            this.state.productSuccess = this.tr('Suggestion sent for review.');
            this.state.productForm = { name: '', category_id: '', description: '' };
            this.state.productImages = [];
            setTimeout(() => { this.state.productSuccess = null; }, 4000);
        } catch (e) {
            this.state.productSaving = false;
            this.state.productError = (e && e.data && e.data.message)
                || this.tr('Could not save the suggestion. Please check the fields.');
        }
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

registry.category("actions").add("recycle_admin_dashboard", RecycleAdminDashboard);
