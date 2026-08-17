/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, onWillDestroy, useState } from "@odoo/owl";
import { user } from "@web/core/user";
import { tr as _tr } from "./recycle_i18n_shared";
import { setDashboardPage, unsetDashboardPage } from "./dashboard_page_state";
import { rpcJson, govLabel, useMessageDialog } from "./dashboard_shared";

export class RecycleOutputDashboard extends Component {
    static template = "recycle_warehouse.RecycleOutputDashboard";
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
            // Warehouse
            myWarehouse: null,
            notifUnreadCount: 0,
            notifications: [],
            notifLoading: false,
            // Stats
            weeklyHours: 0,
            stats: { total: 0, completed: 0, processing: 0, pending: 0 },
            // Shift
            myShift: null,
            // Orders
            orders: [],
            orderSearch: '',
            orderStateFilter: '',
            selectedOrder: null,
            // Invoices
            invoices: [],
            invoiceSearch: '',
            selectedInvoice: null,
            // Process
            processOrder: null,
            processLines: [],
            processError: null,
            processSuccess: null,
            processSaving: false,
            // Complete (zone allocation)
            completeLines: [],       // [{line_id, product_name, condition, required, zones:[{zone_id, zone_name, available}]}]
            allocInputs: {},         // { [line_id]: { [zone_id]: qty(number) } }
            completeError: null,
            completeSaving: false,
            // Finish (output zone)
            outputZones: [],
            selectedOutputZoneId: null,
            finishError: null,
            finishSaving: false,
            finishSuccess: null,
            // Profile
            userProfile: {
                name: user.name || '',
                email: '',
                login: '',
                phone: '',
                role: 'output',
                warehouse: '',
                national_id: '',
                street: '',
                city: '',
                country: '',
            },
            profileLoading: false,
            profileEditMode: false,
            profileSaveSuccess: null,
            profileSaveError: null,
            profileSaving: false,
            profileForm: { name: '', phone: '', national_id: '', street: '', city: '' },
            // Error modal
            errorModal: null,
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
                if (_p.role && _p.role !== 'output') {
                    window.location.replace('/recycle/open-dashboard');
                    return;
                }
            } catch (_e) {}
            try { await this._loadDashboard(); } catch (_) {}
            try { await this._loadMyShift(); } catch (_) {}
            try { await this._loadNotifCount(); } catch (_) {}
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
                this._loadDashboard(true);
            } else if (this.state.view === 'orders_list' && !this._pollingOrders) {
                this._pollRefreshOrders();
            } else if (this.state.view === 'invoices_list' && !this._pollingInvoices) {
                this._pollRefreshInvoices();
            }
            this._loadNotifCount();
        }, 5000);
    }
    _stopPolling() {
        if (this._pollInterval) { clearInterval(this._pollInterval); this._pollInterval = null; }
    }
    async _pollRefreshOrders() {
        this._pollingOrders = true;
        try {
            const r = await this._rpc('/api/output/orders', { state_filter: this.state.orderStateFilter || '' });
            if (r && !r.error) this.state.orders = r.orders || [];
        } catch (_) { /* silent */ }
        this._pollingOrders = false;
    }
    async _pollRefreshInvoices() {
        this._pollingInvoices = true;
        try {
            const r = await this._rpc('/api/output/orders', { state_filter: 'completed' });
            if (r && !r.error) this.state.invoices = (r.orders || []).filter(o => o.invoice_number);
        } catch (_) { /* silent */ }
        this._pollingInvoices = false;
    }

    tr(key) {
        var lang = this.state.lang === 'ar' ? 'ar' : 'en';
        localStorage.setItem('recycle_wms_lang', lang);
        return _tr(key);
    }

    govLabel(code) {
        return govLabel(code, (s) => this.tr(s));
    }

    // ─── Navigation ─────────────────────────────────────────
    // "My Warehouse" isn't in this list — it's its own card above the
    // sections (see o_ra_sb_warehouse in the template), same as the
    // Input/Reception and Sorting dashboards.
    get navSections() {
        return [
            { key: 'home', icon: '\u{1F3E0}', label: 'Home', single: true, go: 'goHome', view: 'home' },
            { key: 'shift', icon: '\u{1F551}', label: 'My Shift', single: true, go: 'openShift', view: 'shift' },
            { key: 'orders', icon: '\u{1F4CB}', label: 'Orders', items: [
                { label: 'My Orders', go: 'openOrdersList' },
                { label: 'My Invoices', go: 'openInvoicesList' },
                { label: 'Process Order', go: 'openProcessOrder' },
            ]},
            { key: 'settings', icon: '\u2699\uFE0F', label: 'Settings', single: true, go: 'showSettings', view: 'settings' },
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
    goHome() { this._navHistory = []; this.state.view = 'home'; this._loadDashboard(); }
    openMyWarehouse() { this._navigate('my_warehouse'); this._loadDashboard(); }
    showSettings() { this._navigate('settings'); }
    setFilterPeriod(period) {
        if (period === this.state.filterPeriod) return;
        this.state.filterPeriod = period;
        this._loadDashboard();
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

    showErrorModal(title, message, type) {
        this.state.errorModal = { title, message, type: type || 'error' };
    }
    closeErrorModal() { this.state.errorModal = null; }

    // JSON-RPC helper — was missing, which silently broke EVERY data
    // load in this dashboard (this._rpc was undefined).
    async _rpc(url, params) { return rpcJson(url, params); }

    // ─── Dashboard Home ─────────────────────────────────────
    async _loadDashboard(silent) {
        if (!silent) this.state.loading = true;
        try {
            const r = await this._rpc('/api/output/dashboard', { period: this.state.filterPeriod || 'month' });
            if (r && !r.error) {
                this.state.myWarehouse = r.warehouse;
                this.state.weeklyHours = r.weekly_hours || 0;
                this.state.stats = r.stats || {};
                if (this.state.myWarehouse) {
                    this.state.userProfile.warehouse = this.state.myWarehouse.name;
                }
            }
        } catch (_) {}
        if (!silent) this.state.loading = false;
    }

    // ─── My Shift ───────────────────────────────────────────
    async _loadMyShift() {
        try {
            const res = await this._rpc('/api/employee/my-shift', {});
            if (res && res.shift) {
                this.state.myShift = res.shift;
            } else {
                this.state.myShift = null;
            }
        } catch (_) { this.state.myShift = null; }
    }

    openShift() {
        this._navigate('shift');
    }

    floatToTime(f) {
        if (f === undefined || f === null) return '—';
        const h = Math.floor(f);
        const m = Math.round((f - h) * 60);
        return String(h).padStart(2, '0') + ':' + String(m).padStart(2, '0');
    }

    // ─── Orders List ────────────────────────────────────────
    async openOrdersList() {
        this._navigate('orders_list');
        this.state.loading = true;
        this.state.orderSearch = '';
        this.state.orderStateFilter = '';
        try {
            const r = await this._rpc('/api/output/orders', { state_filter: '' });
            if (r && !r.error) {
                this.state.orders = r.orders || [];
            }
        } catch (_) {}
        this.state.loading = false;
    }

    async filterOrders(state) {
        this.state.orderStateFilter = state;
        this.state.loading = true;
        try {
            const r = await this._rpc('/api/output/orders', { state_filter: state });
            if (r && !r.error) {
                this.state.orders = r.orders || [];
            }
        } catch (_) {}
        this.state.loading = false;
    }

    get filteredOrders() {
        let list = this.state.orders || [];
        if (this.state.orderSearch) {
            const q = this.state.orderSearch.toLowerCase();
            list = list.filter(o =>
                (o.name || '').toLowerCase().includes(q) ||
                (o.customer_name || '').toLowerCase().includes(q) ||
                (o.owner_name || '').toLowerCase().includes(q)
            );
        }
        return list;
    }

    async viewOrder(orderId) {
        this._navigate('order_detail');
        this.state.loading = true;
        try {
            const r = await this._rpc('/api/output/order/' + orderId, {});
            if (r && !r.error) {
                this.state.selectedOrder = r;
            }
        } catch (_) {}
        this.state.loading = false;
    }

    // ─── Invoices List ──────────────────────────────────────
    async openInvoicesList() {
        this._navigate('invoices_list');
        this.state.loading = true;
        this.state.invoiceSearch = '';
        try {
            const r = await this._rpc('/api/output/orders', { state_filter: 'completed' });
            if (r && !r.error) {
                this.state.invoices = (r.orders || []).filter(o => o.invoice_number);
            }
        } catch (_) {}
        this.state.loading = false;
    }

    get filteredInvoices() {
        let list = this.state.invoices || [];
        if (this.state.invoiceSearch) {
            const q = this.state.invoiceSearch.toLowerCase();
            list = list.filter(o =>
                (o.name || '').toLowerCase().includes(q) ||
                (o.invoice_number || '').toLowerCase().includes(q) ||
                (o.customer_name || '').toLowerCase().includes(q)
            );
        }
        return list;
    }

    async viewInvoice(orderId) {
        this._navigate('invoice_detail');
        this.state.loading = true;
        try {
            const r = await this._rpc('/api/output/order/' + orderId, {});
            if (r && !r.error) {
                this.state.selectedInvoice = r;
            }
        } catch (_) {}
        this.state.loading = false;
    }

    downloadInvoiceById(orderId) {
        window.open('/api/output/order/' + orderId + '/print-invoice', '_blank');
    }

    stateLabel(s) {
        const map = { pending: 'Pending', processing: 'In Progress', ready: 'Ready', completed: 'Completed', cancelled: 'Cancelled' };
        return this.tr(map[s] || s || '');
    }

    conditionLabel(condition) {
        const map = { excellent: 'Excellent', good: 'Good', poor: 'Poor', damaged: 'Damaged' };
        return this.tr(map[condition] || condition || '—');
    }

    conditionBadgeClass(condition) {
        return {
            excellent: 'o_ra_badge_success',
            good: 'o_ra_badge_info',
            poor: 'o_ra_badge_warning',
            damaged: 'o_ra_badge_danger',
        }[condition] || 'o_ra_badge_muted';
    }

    stateBadgeClass(s) {
        const map = { pending: 'o_ra_badge_warning', processing: 'o_ra_badge_info', ready: 'o_ra_badge_success', completed: 'o_ra_badge_success', cancelled: 'o_ra_badge_danger' };
        return map[s] || '';
    }

    formatDate(d) {
        if (!d) return '—';
        try { return new Date(d).toLocaleDateString(); } catch { return d; }
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

    stateClass(s) {
        const map = { pending: 'o_ra_badge_warning', processing: 'o_ra_badge_info', ready: 'o_ra_badge_success', completed: 'o_ra_badge_success', cancelled: 'o_ra_badge_danger' };
        return map[s] || '';
    }

    orderTypeLabel(t) {
        const map = { factory: 'Factory', free_facility: 'Free Facility' };
        return this.tr(map[t] || t || '');
    }

    orderTypeClass(t) {
        const map = { factory: 'o_ra_badge_info', free_facility: 'o_ra_badge_success' };
        return map[t] || '';
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

    // ─── Process Order ──────────────────────────────────────
    async openProcessOrder() {
        this._navigate('process_order');
        this.state.loading = true;
        this.state.processError = null;
        this.state.processSuccess = null;
        try {
            const r = await this._rpc('/api/output/orders', { state_filter: 'pending' });
            if (r && !r.error) {
                this.state.orders = (r.orders || []).filter(o => !o.output_user_id);
            }
        } catch (_) {}
        this.state.loading = false;
    }

    async selectOrderToProcess(orderId) {
        this._navigate('process_detail');
        this.state.loading = true;
        this.state.processError = null;
        this.state.processSuccess = null;
        try {
            const r = await this._rpc('/api/output/order/' + orderId, {});
            if (r && !r.error) {
                this.state.processOrder = r;
            }
        } catch (_) {}
        this.state.loading = false;
    }

    async reserveOrder() {
        if (!this.state.processOrder) return;
        this.state.processSaving = true;
        this.state.processError = null;
        try {
            const r = await this._rpc('/api/output/order/reserve', {
                order_id: this.state.processOrder.id,
            });
            if (r && r.error) {
                this.state.processError = r.error;
                this.state.processSaving = false;
                return;
            }
            this.state.processOrder.state = 'processing';
            this.state.processOrder.output_user = this.userName;
            this.state.processSuccess = { message: 'Order reserved successfully!' };
            setTimeout(() => { this.state.processSuccess = null; }, 3000);
        } catch (e) {
            this.state.processError = (e && e.data && e.data.message) || 'Failed to reserve order.';
        }
        this.state.processSaving = false;
    }

    async openComplete() {
        if (!this.state.processOrder) return;
        this._navigate('complete_order');
        this.state.loading = true;
        this.state.completeError = null;
        this.state.processSuccess = null;
        this.state.allocInputs = {};
        try {
            const r = await this._rpc('/api/output/storage-zones', {
                order_id: this.state.processOrder.id,
            });
            if (r && !r.error) {
                const zones = r.zones || [];
                const requirements = r.requirements || [];
                const inputs = {};
                this.state.completeLines = requirements.map(req => {
                    inputs[req.line_id] = {};
                    const lineZones = zones
                        .filter(z => (z.products || []).some(p => p.line_id === req.line_id))
                        .map(z => {
                            const p = z.products.find(pp => pp.line_id === req.line_id);
                            inputs[req.line_id][z.id] = 0;
                            return { zone_id: z.id, zone_name: z.name, available: p.quantity };
                        });
                    return { ...req, zones: lineZones };
                });
                this.state.allocInputs = inputs;
            } else if (r && r.error) {
                this.state.completeError = r.error;
            }
        } catch (_) {}
        this.state.loading = false;
    }

    setAllocation(lineId, zoneId, value) {
        let qty = parseFloat(value);
        if (isNaN(qty) || qty < 0) qty = 0;
        if (!this.state.allocInputs[lineId]) this.state.allocInputs[lineId] = {};
        this.state.allocInputs[lineId][zoneId] = qty;
    }

    allocatedQty(lineId) {
        const zoneMap = this.state.allocInputs[lineId] || {};
        return Object.values(zoneMap).reduce((sum, q) => sum + (q || 0), 0);
    }

    lineIsSatisfied(line) {
        return this.allocatedQty(line.line_id) >= line.required - 0.0001;
    }

    get allLinesSatisfied() {
        return (this.state.completeLines || []).every(l => this.lineIsSatisfied(l));
    }

    async completeOrder() {
        if (!this.state.processOrder) return;
        this.state.completeSaving = true;
        this.state.completeError = null;
        const allocations = [];
        for (const line of this.state.completeLines) {
            const zoneMap = this.state.allocInputs[line.line_id] || {};
            for (const [zoneId, qty] of Object.entries(zoneMap)) {
                if (qty > 0) {
                    allocations.push({ line_id: line.line_id, zone_id: parseInt(zoneId, 10), quantity: qty });
                }
            }
        }
        try {
            const r = await this._rpc('/api/output/order/complete', {
                order_id: this.state.processOrder.id,
                allocations,
            });
            if (r && r.error) {
                this.state.completeError = r.error;
                this.state.completeSaving = false;
                return;
            }
            this.state.processSuccess = {
                message: 'Order completed! Invoice: ' + (r.invoice_number || ''),
                invoice_number: r.invoice_number,
                amount_total: r.amount_total,
                pdf_url: r.pdf_url || '',
                stock_deducted_at: r.stock_deducted_at || '',
            };
            this.state.processOrder.state = r.state || 'ready';
            this.state.processOrder.invoice_number = r.invoice_number;
        } catch (e) {
            this.state.completeError = (e && e.data && e.data.message) || 'Failed to complete order.';
        }
        this.state.completeSaving = false;
    }

    // ─── Finish (choose output zone) ─────────────────────────
    async openFinish() {
        if (!this.state.processOrder) return;
        this._navigate('finish_order');
        this.state.loading = true;
        this.state.finishError = null;
        this.state.finishSuccess = null;
        this.state.selectedOutputZoneId = null;
        try {
            const r = await this._rpc('/api/output/output-zones', {
                order_id: this.state.processOrder.id,
            });
            if (r && !r.error) {
                this.state.outputZones = r.zones || [];
            }
        } catch (_) {}
        this.state.loading = false;
    }

    selectOutputZone(zoneId) {
        this.state.selectedOutputZoneId = zoneId;
    }

    async finishOrder() {
        if (!this.state.processOrder || !this.state.selectedOutputZoneId) return;
        this.state.finishSaving = true;
        this.state.finishError = null;
        try {
            const r = await this._rpc('/api/output/order/finish', {
                order_id: this.state.processOrder.id,
                output_zone_id: this.state.selectedOutputZoneId,
            });
            if (r && r.error) {
                this.state.finishError = r.error;
                this.state.finishSaving = false;
                return;
            }
            this.state.processOrder.state = 'completed';
            this.state.finishSuccess = true;
        } catch (e) {
            this.state.finishError = (e && e.data && e.data.message) || 'Failed to finish order.';
        }
        this.state.finishSaving = false;
    }

    // ─── Profile ────────────────────────────────────────────
    get profileRoleLabel() {
        return this.tr(this.state.userProfile?.role || 'Output Employee');
    }

    async createTestOrders() {
        this.state.loading = true;
        try {
            const r = await this._rpc('/api/output/order/create-test-batch', { count: 5 });
            if (r && r.error) {
                this.showErrorModal('Error', r.error);
            } else {
                this.showErrorModal('Success', 'Created ' + (r.count || 0) + ' test orders!', 'success');
                if (this.state.view === 'orders_list' || this.state.view === 'process_order') {
                    await this.openOrdersList();
                }
            }
        } catch (e) {
            this.showErrorModal('Error', 'Failed to create test orders.');
        }
        this.state.loading = false;
    }

    downloadInvoice(orderId) {
        window.open('/api/output/order/' + orderId + '/print-invoice', '_blank');
    }

    showProfile() {
        this._navigate('profile');
        this.state.profileLoading = true;
        this.state.profileEditMode = false;
        this.state.profileSaveSuccess = null;
        this.state.profileSaveError = null;
        this._fetchProfile();
    }

    async _fetchProfile() {
        try {
            const r = await this._rpc('/api/recycle/my-profile', {});
            if (r && !r.error) {
                this.state.userProfile = {
                    name: r.name || '',
                    email: r.email || '',
                    login: r.login || '',
                    phone: r.phone || '',
                    role: r.role || 'output',
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
            phone: p.phone || '',
            national_id: p.national_id || '',
            street: p.street || '',
            city: p.city || '',
        };
        this.state.profileEditMode = true;
        this.state.profileSaveSuccess = null;
        this.state.profileSaveError = null;
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
            this.showErrorModal(this.tr('Profile Updated'), this.tr('Your profile has been updated successfully.'), 'success');
            setTimeout(() => { this.state.profileSaveSuccess = null; }, 3000);
        } catch (e) {
            this.state.profileSaveError = (e && e.data && e.data.message)
                || this.tr('Failed to save profile. Please try again.');
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

    // ─── Helpers ────────────────────────────────────────────
    m2oName(field) {
        if (!field) return '—';
        if (Array.isArray(field)) return field[1] || '—';
        if (typeof field === 'string') return field;
        return '—';
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

registry.category("actions").add("recycle_output_dashboard", RecycleOutputDashboard);
