/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, onWillDestroy, useState, useRef } from "@odoo/owl";
import { session } from "@web/session";
import { user } from "@web/core/user";
import { tr as _tr } from "./recycle_i18n_shared";
import { setDashboardPage, unsetDashboardPage } from "./dashboard_page_state";
import { rpcJson, govLabel, useMessageDialog } from "./dashboard_shared";

export class RecycleHomeAction extends Component {
    static template = "recycle_warehouse.RecycleHomeAction";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.barcodeFileInput = useRef("barcodeFileInput");
        this.userName = (user && user.name) || "Employee";
        this.userEmail = (session && session.email) || '';
        this.userLogin = (user && user.login) || this.userName;
        this._navHistory = [];

        this.state = useState({
            view: "my_warehouse",
            // Sidebar entry painted green — moves only when another one is clicked.
            activeNavGo: 'goHome',
            loading: false,
            sidebarOpen: false,
            navSection: null,
            darkMode: (localStorage.getItem('dw-theme')
                       || (localStorage.getItem('recycle_wms_dark') === '1' ? 'dark' : 'light')) === 'dark',
            lang: (localStorage.getItem('recycle_wms_lang') || 'en').replace(/^ar_.*$/, 'ar'),
            myWarehouse: null,
            myShift: null,
            showWarehouseInfo: false,
            notifUnreadCount: 0,
            notifications: [],
            notifLoading: false,
            stats: { processed: 0, transferred: 0, acceptRate: 0, avgHours: 0 },
            shipments: [],
            shipmentSearch: '',
            shipmentStateFilter: '',
            processRef: '',
            processError: null,
            processLoading: false,
            processShipment: null,
            receivingZones: [],
            processZoneId: '',
            processSaving: false,
            processSuccess: null,
            processToast: null,
            barcodeScanning: false,
            cameraFacing: 'environment',
            barcodeError: null,
            errorModal: null,
            userProfile: null,
            profileLoading: false,
            profileEditMode: false,
            profileForm: { name: '', phone: '', national_id: '', street: '', city: '' },
            profileSaving: false,
            profileSaveSuccess: null,
            profileSaveError: null,
            filterPeriod: 'month',
            showChangePasswordModal: false,
            changePasswordCurrent: '',
            changePasswordNew: '',
            changePasswordConfirm: '',
            changePasswordError: null,
            changePasswordLoading: false,
            changePasswordStep: 1,
            navUserEmail: '',
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
                if (_p.role && _p.role !== 'input') {
                    window.location.replace('/recycle/open-dashboard');
                    return;
                }
            } catch (_e) {}
            try { await this._loadMyWarehouse(); } catch (e) {}
            try { await this._loadReceivingStats('month'); } catch (e) {}
            try { await this._loadNotifCount(); } catch (e) {}
            // Load profile email from database for navbar
            try {
                const p = await this._rpc('/api/recycle/my-profile', {});
                if (p && p.email) {
                    this.state.navUserEmail = p.email;
                }
            } catch (_e) {}
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
            if (this.state.view === 'my_warehouse') {
                this._loadMyWarehouse(true);
            } else if (this.state.view === 'shipments_list' && !this._pollingShipments) {
                this._pollRefreshShipments();
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
            const resp = await this._rpc('/api/receiving/my-shipments', {});
            this.state.shipments = resp.shipments || [];
        } catch (e) { /* silent */ }
        this._pollingShipments = false;
    }

    tr(key) {
        var lang = this.state.lang === 'ar' ? 'ar' : 'en';
        localStorage.setItem('recycle_wms_lang', lang);
        return _tr(key);
    }

    govLabel(code) {
        return govLabel(code, (s) => this.tr(s));
    }

    get navSections() {
        return [
            { key: 'home', icon: '\u{1F3E0}', label: 'Home', single: true, go: 'goHome', view: 'my_warehouse' },
            { key: 'shift', icon: '\u{1F551}', label: 'My Shift', single: true, go: 'openShift', view: 'shift' },
            { key: 'shipments', icon: '\u{1F4E6}', label: 'Shipments', items: [
                { label: 'View Shipments', go: 'openMyShipments' },
                { label: 'Process New Shipment', go: 'openProcess' },
            ]},
            { key: 'settings', icon: '\u2699\uFE0F', label: 'Settings', single: true, go: 'showSettings', view: 'settings' },
        ];
    }

    get profileRoleLabel() {
        return this.tr(this.state.userProfile?.role || 'Input Employee');
    }

    toggleSidebar(ev) { if (ev) { ev.stopPropagation(); ev.preventDefault(); } this.state.sidebarOpen = !this.state.sidebarOpen; }
    toggleWarehouseInfo() { this.state.showWarehouseInfo = !this.state.showWarehouseInfo; }
    toggleNavSection(key) { this.state.navSection = this.state.navSection === key ? null : key; }
    navClick(fnName) {
        this.state.sidebarOpen = false;
        this.state.activeNavGo = fnName;
        const fn = this[fnName];
        if (typeof fn === 'function') fn.call(this);
    }
    _navigate(view) { this.stopQrScanner(); this._navHistory.push(this.state.view); this.state.view = view; this.state.showWarehouseInfo = false; }
    goBack() { this.stopQrScanner(); this.state.view = this._navHistory.pop() || 'my_warehouse'; this.state.showWarehouseInfo = false; }
    goHome() { this.stopQrScanner(); this._navHistory = []; this.state.view = 'my_warehouse'; this.state.showWarehouseInfo = false; this._loadMyWarehouse(); }
    showSettings() { this._navigate('settings'); }
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
    showMyWarehouse() { this._navigate('my_warehouse_detail'); }
    showProcessToast(msg, type) {
        this.state.processToast = { msg, type: type || 'error' };
        clearTimeout(this._processToastTimer);
        this._processToastTimer = setTimeout(() => { this.state.processToast = null; }, 4000);
    }
    async setShipmentFilter(ev) {
        const filter = ev.currentTarget.dataset.filter || '';
        this.state.shipmentStateFilter = filter;
        this.state.loading = true;
        try {
            const resp = await this._rpc('/api/receiving/my-shipments', {
                state_filter: filter || undefined,
            });
            this.state.shipments = resp.shipments || [];
        } catch (e) {
            this.state.shipments = [];
        }
        this.state.loading = false;
    }

    setFilterPeriod(period) {
        this.state.filterPeriod = period;
        this._loadReceivingStats(period);
    }

    async _loadReceivingStats(period) {
        try {
            const res = await this._rpc('/api/receiving/dashboard-stats', {
                period: period || 'month',
            });
            if (res) {
                this.state.stats.processed = res.processed || 0;
                this.state.stats.transferred = res.transferred || 0;
                this.state.stats.acceptRate = res.completion_rate || 0;
                this.state.stats.avgHours = res.working_hours || 0;
                this.state.stats.pending = res.pending || 0;
            }
        } catch (e) {
            console.error('Failed to load receiving stats', e);
        }
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

    async _loadMyWarehouse(silent) {
        if (!silent) this.state.loading = true;
        try {
            const whs = await this.orm.searchRead(
                'recycle.warehouse', [],
                ['id', 'name', 'code', 'governorate', 'manager_user_id'],
                { limit: 1 });
            this.state.myWarehouse = whs[0] || null;
        } catch (e) { this.state.myWarehouse = null; }
        try {
            const now = new Date();
            const monthStart = now.getFullYear() + '-'
                + String(now.getMonth() + 1).padStart(2, '0') + '-01 00:00:00';
            const mine = await this.orm.searchRead(
                'recycle.shipment',
                [['receiver_user_id', '=', user.userId],
                 ['received_at', '>=', monthStart]],
                ['id', 'state', 'create_date', 'received_at'],
                { limit: 500 });
            const accepted = mine.filter(s => ['accepted', 'sorting', 'sorted'].includes(s.state)).length;
            const transferred = mine.filter(s => s.state === 'escalated').length;
            const done = accepted + transferred;
            let avgH = 0;
            const withTimes = mine.filter(s => s.create_date && s.received_at);
            if (withTimes.length) {
                const total = withTimes.reduce((acc, s) =>
                    acc + (new Date(s.received_at) - new Date(s.create_date)) / 3600000, 0);
                avgH = total / withTimes.length;
            }
            // Pending: reserved to me right now (scanned, not yet received) —
            // a live count, not scoped to this month like the metrics above.
            const pendingCount = await this.orm.searchCount('recycle.shipment',
                [['receiver_user_id', '=', user.userId], ['state', '=', 'receiving']]);
            this.state.stats = {
                processed: done,
                transferred: transferred,
                pending: pendingCount,
                acceptRate: done > 0 ? Math.round((accepted / done) * 100) : 0,
                avgHours: Math.round(avgH * 10) / 10,
            };
        } catch (e) {}
        if (!silent) this.state.loading = false;
    }

    async openMyShipments() {
        this._navigate('shipments_list');
        this.state.loading = true;
        this.state.shipmentStateFilter = '';
        this.state.shipmentSearch = '';
        this.state.shipments = [];
        try {
            const resp = await this._rpc('/api/receiving/my-shipments', {});
            this.state.shipments = resp.shipments || [];
        } catch (e) {
            this.state.shipments = [];
            this.showProcessToast(this.tr('Failed to load shipments. Please try again.'));
        }
        this.state.loading = false;
    }

    get filteredShipments() {
        const q = (this.state.shipmentSearch || '').toLowerCase().trim();
        return this.state.shipments.filter(s => {
            if (q && !((s.name || '').toLowerCase().includes(q)
                    || (s.driver_name || '').toLowerCase().includes(q))) return false;
            return true;
        });
    }

    async openShipmentDetail(s) {
        // Reception only ever has "receiving" or "accepted" shipments in
        // its own list — both are shown read-only through the same process
        // view. Only "receiving" gets the Accept/Release action buttons.
        this.state.processLoading = true;
        this.state.processError = null;
        this.state.processSuccess = null;
        this.state.processRef = s.name;
        this.state.processZoneId = '';
        this.state.processSaving = false;
        try {
            const result = await this._rpc('/api/receiving/shipment-info', {
                shipment_ref: s.name,
            });
            if (result && result.ok) {
                await this._openProcessView(result.shipment);
                this._navigate('process');
            } else {
                this.showProcessToast(this.tr('Failed to load shipment for processing.'));
            }
        } catch (e) {
            this.showProcessToast(this.tr('Failed to load shipment for processing.'));
        }
        this.state.processLoading = false;
    }

    openProcess() {
        this.state.processRef = '';
        this.state.processError = null;
        this.state.processShipment = null;
        this.state.processSuccess = null;
        this._navigate('process');
    }

    async loadShipmentForProcessing() {
        const ref = (this.state.processRef || '').trim();
        if (!ref) {
            this.showProcessToast(this.tr('Enter the shipment ID first.'));
            return;
        }
        this.state.processLoading = true;
        this.state.processError = null;
        this.state.processShipment = null;
        try {
            const result = await this._rpc('/api/receiving/scan-shipment', {
                shipment_ref: ref,
            });

            if (result.case === 'not_found') {
                this.showProcessToast(this.tr('Shipment not found. It may not exist or be reserved by a colleague.'));
            } else if (result.case === 'wrong_warehouse') {
                this.showProcessToast(this.tr('You cannot receive this shipment because it does not belong to your warehouse.'));
            } else if (result.case === 'other') {
                this.showProcessToast(this.tr('This shipment is currently reserved by %s.').replace('%s', result.reserved_by));
            } else if (result.case === 'processed') {
                this.showProcessToast(this.tr('This shipment has already been processed and cannot be received again.'));
            } else if (result.case === 'reserved') {
                this.showProcessToast(this.tr('Shipment reserved successfully by %s.').replace('%s', this.userName), 'success');
                const s = result.shipment;
                const exists = this.state.shipments.find(x => x.id === s.id);
                if (!exists) {
                    this.state.shipments = [s, ...this.state.shipments];
                }
                await this._openProcessView(s);
            } else if (result.case === 'mine') {
                this.showProcessToast(this.tr('Welcome back! Shipment %s is still reserved for you.').replace('%s', result.shipment.name), 'success');
                await this._openProcessView(result.shipment);
            } else if (result.case === 'error') {
                this.showProcessToast(this.tr('Loading failed. Please try again.'));
            }
        } catch (e) {
            this.showProcessToast((e && e.data && e.data.message) || this.tr('Loading failed. Please try again.'));
        }
        this.state.processLoading = false;
    }

    async _openProcessView(s) {
        this.state.processShipment = s;
        // Only shipments still awaiting acceptance need a zone selector.
        if (s.state === 'receiving') {
            await this._loadReceivingZones(s.id);
        } else {
            this.state.receivingZones = [];
            this.state.processZoneId = '';
        }
    }

    startQrScanner() {
        if (!window.Html5Qrcode) {
            this.showProcessToast(this.tr('QR library not loaded yet. Please try again.'));
            return;
        }
        this.state.barcodeScanning = true;
        this.state.cameraFacing = this.state.cameraFacing || 'environment';

        // Create full-screen overlay
        const overlay = document.createElement('div');
        overlay.className = 'o_ra_scan_overlay';
        overlay.id = 'qr-scan-overlay';
        overlay.innerHTML = `
            <div class="o_ra_scan_overlay_header">
                <span class="o_ra_scan_overlay_title">${this.tr('Scan QR Code')}</span>
                <button class="o_ra_scan_overlay_close" id="qr-close-btn">&times;</button>
            </div>
            <div class="o_ra_scan_overlay_viewfinder">
                <div id="qr-reader-overlay"></div>
            </div>
            <div class="o_ra_scan_overlay_status">
                <div class="o_ra_scan_overlay_pulsing"></div>
                <span class="o_ra_scan_overlay_status_text">${this.tr('Scanning...')}</span>
            </div>
            <div class="o_ra_scan_overlay_controls">
                <button class="o_ra_scan_overlay_btn o_ra_scan_overlay_btn_switch" id="qr-switch-btn">
                    &#x1F504; ${this.tr('Switch Camera')}
                </button>
                <button class="o_ra_scan_overlay_btn o_ra_scan_overlay_btn_stop" id="qr-stop-btn">
                    &#x23F9; ${this.tr('Stop')}
                </button>
            </div>
        `;
        document.body.appendChild(overlay);

        // Close button
        document.getElementById('qr-close-btn').addEventListener('click', () => {
            this._closeQrOverlay();
        });

        // Switch camera button
        document.getElementById('qr-switch-btn').addEventListener('click', () => {
            this._switchCameraInOverlay();
        });

        // Stop button
        document.getElementById('qr-stop-btn').addEventListener('click', () => {
            this._closeQrOverlay();
        });

        // Start scanner in overlay
        this._qrScanner = new window.Html5Qrcode('qr-reader-overlay');
        this._qrDecoded = false;
        this._qrOverlay = overlay;

        this._qrScanner.start(
            { facingMode: this.state.cameraFacing },
            { fps: 24, qrbox: { width: 250, height: 250 } },
            (decodedText) => {
                if (this._qrDecoded) return;
                this._qrDecoded = true;
                this.state.barcodeScanning = false;
                this.state.processRef = decodedText;
                this._closeQrOverlay();
                this.loadShipmentForProcessing();
            },
            () => {}
        ).catch(() => {
            this.state.barcodeScanning = false;
            this._closeQrOverlay();
            this.showProcessToast(this.tr('Cannot access camera. Please allow camera permission.'));
        });
    }

    _closeQrOverlay() {
        if (this._qrScanner) {
            try { this._qrScanner.stop(); } catch (e) {}
            try { this._qrScanner.clear(); } catch (e) {}
            this._qrScanner = null;
        }
        if (this._qrOverlay) {
            this._qrOverlay.remove();
            this._qrOverlay = null;
        }
        this.state.barcodeScanning = false;
    }

    async _switchCameraInOverlay() {
        if (!this._qrScanner) return;
        try { await this._qrScanner.stop(); } catch (e) {}
        this.state.cameraFacing = this.state.cameraFacing === 'environment' ? 'user' : 'environment';
        this._qrScanner = new window.Html5Qrcode('qr-reader-overlay');
        this._qrScanner.start(
            { facingMode: this.state.cameraFacing },
            { fps: 24, qrbox: { width: 250, height: 250 } },
            (decodedText) => {
                if (this._qrDecoded) return;
                this._qrDecoded = true;
                this.state.barcodeScanning = false;
                this.state.processRef = decodedText;
                this._closeQrOverlay();
                this.loadShipmentForProcessing();
            },
            () => {}
        ).catch(() => {
            this.state.barcodeScanning = false;
            this._closeQrOverlay();
        });
    }

    stopQrScanner() {
        this._closeQrOverlay();
    }

    triggerBarcodeInput() {
        if (this.barcodeFileInput && this.barcodeFileInput.el) {
            this.barcodeFileInput.el.click();
        }
    }

    onBarcodeFileChange(ev) {
        const file = ev.target.files && ev.target.files[0];
        if (!file) return;
        this._scanBarcodeFile(file);
    }

    onBarcodeDrop(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const file = ev.dataTransfer && ev.dataTransfer.files && ev.dataTransfer.files[0];
        if (file && file.type.startsWith('image/')) {
            this._scanBarcodeFile(file);
        }
    }

    onBarcodeDragOver(ev) {
        ev.preventDefault();
        ev.stopPropagation();
    }

    /**
     * Decode a QR code from an uploaded photo — IN THE BROWSER first.
     *
     * This used to post the image to `/api/receiving/scan-barcode`, which
     * decodes with pyzbar. pyzbar is a thin wrapper over the NATIVE `zbar`
     * shared library, and that library is not in the Odoo image:
     *
     *     from pyzbar import pyzbar
     *     ImportError: Unable to find zbar shared library
     *
     * So the route answered `pyzbar_missing` for every upload and the feature
     * had never worked. Installing zbar into the running container is not a
     * fix either — it disappears on the next rebuild, and the button would
     * quietly stop working again with nothing in the logs to explain it (the
     * same trap the Arabic fonts note in docker-compose.yml describes).
     *
     * The decoder was already here. `html5-qrcode` is loaded for the camera
     * scanner and exposes `scanFile()` for exactly this case, so the upload
     * path now uses the SAME decoder as the live scan — one behaviour to
     * reason about instead of two, no native dependency, and the image never
     * leaves the device.
     *
     * The server call is kept as a fallback for when the CDN is unreachable:
     * it is broken today, but it is the only path left if the library never
     * loads, and a clear "library not installed" beats a dead button.
     */
    async _scanBarcodeFile(file) {
        this.state.barcodeScanning = true;
        this.state.barcodeError = null;
        this.state.processError = null;

        if (window.Html5Qrcode && typeof window.Html5Qrcode.prototype.scanFile === 'function') {
            try {
                // Needs a real element to mount into, even though nothing of
                // it is shown: `scanFile(file, false)` draws no preview.
                const holder = document.getElementById('qr-reader');
                const decoder = new window.Html5Qrcode(holder ? 'qr-reader' : 'qr-reader-overlay');
                const text = await decoder.scanFile(file, false);
                // Release the camera/canvas the instance allocated. It never
                // started a stream here, so a failure to clear is harmless.
                try { await decoder.clear(); } catch (e) { /* nothing to release */ }

                const ref = (text || '').trim();
                if (ref) {
                    this.state.processRef = ref;
                    this.state.barcodeError = null;
                    this.state.barcodeScanning = false;
                    await this.loadShipmentForProcessing();
                    return;
                }
            } catch (e) {
                // A photo with no readable code is the ordinary case, not a
                // crash: say so instead of falling through to a server that
                // will answer `pyzbar_missing` and confuse the message.
                this.showProcessToast(
                    this.tr('No QR code or barcode found in the image.'));
                this.state.barcodeScanning = false;
                return;
            }
        }

        try {
            const base64 = await this._readFileAsBase64(file);
            const resp = await fetch('/api/receiving/scan-barcode', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({
                    jsonrpc: '2.0', method: 'call',
                    params: { image: base64 },
                }),
            });
            const wrapper = await resp.json();
            const result = (wrapper && wrapper.result) || wrapper || {};
            if (result.error) {
                const msgs = {
                    no_image: this.tr('No image received. Please try again.'),
                    pyzbar_missing: this.tr('QR/Barcode library not installed on the server.'),
                    pillow_missing: this.tr('Image library not installed on the server.'),
                    invalid_base64: this.tr('Invalid image data.'),
                    invalid_image: this.tr('Cannot read the file as an image.'),
                    no_barcode: this.tr('No QR code or barcode found in the image.'),
                };
                this.showProcessToast(msgs[result.error] || this.tr('Scan failed.'));
            } else if (result.shipment_ref) {
                this.state.processRef = result.shipment_ref;
                this.state.barcodeError = null;
                await this.loadShipmentForProcessing();
            }
        } catch (e) {
            this.showProcessToast(this.tr('Network error. Please check your connection.'));
        }
        this.state.barcodeScanning = false;
    }

    _readFileAsBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => { resolve((reader.result || '').split(',')[1] || ''); };
            reader.onerror = () => reject(new Error('FileReader failed'));
            reader.readAsDataURL(file);
        });
    }

    showErrorModal(title, message, type = 'danger') {
        this.state.errorModal = { title, message, type };
    }
    closeErrorModal() { this.state.errorModal = null; }

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
                    name: r.name || this.userName,
                    email: r.email || '',
                    login: r.login || '',
                    phone: r.phone || '',
                    national_id: r.national_id || '',
                    role: r.role || 'input',
                    warehouse: r.warehouse || this.state.myWarehouse?.name || '',
                    street: r.street || '',
                    city: r.city || '',
                    country: r.country || '',
                };
            } else {
                this.state.userProfile = {
                    name: this.userName, email: this.userEmail || '', login: this.userLogin || '',
                    phone: '', national_id: '', role: 'input', warehouse: this.state.myWarehouse?.name || '',
                    street: '', city: '', country: '',
                };
            }
        } catch (e) {
            this.state.userProfile = {
                name: this.userName, email: this.userEmail || '', login: this.userLogin || '',
                phone: '', national_id: '', role: 'input', warehouse: this.state.myWarehouse?.name || '',
                street: '', city: '', country: '',
            };
        }
        this.state.profileLoading = false;
    }

    startEditProfile() {
        const p = this.state.userProfile || {};
        this.state.profileForm = {
            name: p.name || '',
            phone: p.phone || '',
            national_id: p.national_id || '',
            street: p.street || '',
            city: p.city || '',
        };
        this.state.profileEditMode = true;
        this.state.profileSaveError = null;
        this.state.profileSaveSuccess = null;
    }

    cancelEditProfile() {
        this.state.profileEditMode = false;
        this.state.profileSaveError = null;
    }

    async saveProfile() {
        const f = this.state.profileForm;
        if (!f.name.trim()) {
            this.state.profileSaveError = this.tr('Name required');
            return;
        }
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
            this.state.profileSaveError = (e && e.data && e.data.message) || this.tr('Update failed.');
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

    // Receiving zones of the shipment's warehouse — the input employee
    // must pick where the shipment is physically placed.
    async _loadReceivingZones(shipmentId) {
        try {
            const sh = await this.orm.searchRead(
                'recycle.shipment', [['id', '=', shipmentId]], ['warehouse_id']);
            const whId = sh[0] && sh[0].warehouse_id && sh[0].warehouse_id[0];
            this.state.receivingZones = whId
                ? await this.orm.searchRead(
                    'recycle.zone',
                    [['warehouse_id', '=', whId], ['zone_type', '=', 'receiving']],
                    ['id', 'name'])
                : [];
        } catch (e) { this.state.receivingZones = []; }
        this.state.processZoneId = this.state.receivingZones.length === 1
            ? String(this.state.receivingZones[0].id) : '';
    }

    async confirmAccept() {
        const s = this.state.processShipment;
        if (!s) return;
        if (!this.state.processZoneId) {
            this.showErrorModal(this.tr('Error'),
                this.tr('Select a receiving zone of your warehouse before accepting the shipment.'),
                'danger');
            return;
        }
        this.state.processSaving = true;
        this.state.processError = null;
        try {
            await this.orm.write('recycle.shipment', [s.id],
                { receiving_zone_id: parseInt(this.state.processZoneId) });
            await this.orm.call('recycle.shipment', 'action_accept', [[s.id]]);
            this.state.processSuccess = { mode: 'accepted', name: s.name };
            this.state.processShipment = null;
            this._loadMyWarehouse();
        } catch (e) {
            this.showErrorModal(this.tr('Error'), (e && e.data && e.data.message) || this.tr('Action failed.'), 'danger');
        }
        this.state.processSaving = false;
    }

    async releaseFromProcess() {
        const s = this.state.processShipment;
        if (!s) return;
        try {
            await this.orm.call('recycle.shipment', 'action_release', [[s.id]]);
            // Remove from local list — pending shipments don't appear
            this.state.shipments = this.state.shipments.filter(x => x.id !== s.id);
            this.showProcessToast(this.tr('Shipment released. Scan the QR code again to reserve it.'), 'success');
            this.openProcess();
        } catch (e) {
            this.showErrorModal(this.tr('Error'), (e && e.data && e.data.message) || this.tr('Action failed.'), 'danger');
        }
    }

    async _rpc(url, params) { return rpcJson(url, params); }

    m2oName(field) {
        if (!field) return '\u2014';
        if (Array.isArray(field)) return field[1] || '\u2014';
        if (typeof field === 'string') return field;
        return '\u2014';
    }

    formatDate(val) {
        if (!val) return '\u2014';
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
                        escalated: this.tr("Transferred"),
                        accepted: this.tr("Received Status"), sorting: this.tr("In Sorting"),
                        pending_sorting_approval: this.tr("Pending Sorting Approval"),
                        sorted: this.tr("Sorted") },
        };
        return (map[type] && map[type][state]) || state || '\u2014';
    }

    stateBadgeClass(state) {
        const good = ["accepted", "sorted"];
        const bad = ["escalated", "rejected", "cancelled"];
        const warn = ["pending", "receiving", "sorting"];
        if (good.includes(state)) return "o_ra_badge_success";
        if (bad.includes(state)) return "o_ra_badge_danger";
        if (warn.includes(state)) return "o_ra_badge_warn";
        return "o_ra_badge_muted";
    }
}

registry.category("actions").add("recycle_home_action", RecycleHomeAction);
