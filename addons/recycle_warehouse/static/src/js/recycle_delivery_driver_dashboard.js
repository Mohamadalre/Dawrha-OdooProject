/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, onWillDestroy, useState } from "@odoo/owl";
import { user } from "@web/core/user";
import { tr as _tr } from "./recycle_i18n_shared";
import { setDashboardPage, unsetDashboardPage } from "./dashboard_page_state";
import { rpcJsonSafe } from "./dashboard_shared";

/**
 * The delivery driver's dashboard.
 *
 * Built on the same shell as the sorting employee's — same sidebar, same theme
 * and language switches, same profile and security screens — because it is the
 * same product and a driver should not have to learn a second one.
 *
 * ONE deliberate difference: there is no "My Shift".
 *
 * A collector works a shift: their whole day is a window they clock into, and
 * their screen leads with it. A delivery driver has no shift at all — they
 * carry sold goods when there is an order to carry. Leaving an empty shift card
 * on their home screen would not be a blank field, it would be a claim about
 * how their job works that is simply untrue. In its place sits **My Truck**,
 * which answers the question their role actually raises: which vehicle am I
 * responsible for, and is it in service?
 */
export class RecycleDeliveryDriverDashboard extends Component {
    static template = "recycle_warehouse.RecycleDeliveryDriverDashboard";
    static props = ["*"];

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.userName = (user && user.name) || "Driver";
        this._navHistory = [];

        this.state = useState({
            view: "home",
            activeNavGo: 'goHome',
            loading: false,
            sidebarOpen: false,
            navSection: null,
            darkMode: (localStorage.getItem('dw-theme')
                       || (localStorage.getItem('recycle_wms_dark') === '1' ? 'dark' : 'light')) === 'dark',
            lang: (localStorage.getItem('recycle_wms_lang') || 'en').replace(/^ar_.*$/, 'ar'),

            // Who this driver is, and the vehicle they hold.
            driver: null,
            truck: null,
            truckAssigned: false,
            truckError: null,

            // The driver's base warehouse (the "My Warehouse" screen every other
            // role has) and how many trips they have delivered this month.
            warehouse: null,
            tripsThisMonth: 0,

            // The driver's live delivery trips — one NEXT stop each.
            trips: [],
            tripsError: null,
            tripBusy: null,
            // My Trips has two tabs: the trips still to run (active), and the
            // ones already delivered (completed, in full — time, warehouses and
            // quantities, but never the order cost).
            tripsTab: 'active',
            tripsActive: [],
            tripsCompleted: [],

            notifUnreadCount: 0,
            notifications: [],
            notifLoading: false,

            // Profile
            userProfile: { name: '', email: '', login: '', phone: '', role: 'delivery_driver', warehouse: '', national_id: '', street: '', city: '', country: '' },
            profileLoading: false,
            profileEditMode: false,
            profileForm: { name: '', phone: '', national_id: '', street: '', city: '' },
            profileSaving: false,
            profileSaveSuccess: null,
            profileSaveError: null,

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


        onWillStart(async () => {
            // One Odoo session per browser: if another user signed in from a
            // second tab, never render this role's UI with the foreign session.
            try {
                const p = await this._rpc('/api/recycle/my-profile', {});
                if (p && p.role && p.role !== 'delivery_driver') {
                    window.location.replace('/recycle/open-dashboard');
                    return;
                }
            } catch (e) {}
            try { await this._loadMyTruck(); } catch (e) {}
            try { await this._loadNotifCount(); } catch (e) {}
        });
        onMounted(() => {
            setDashboardPage();
            this._applyTheme();
        });
        onWillDestroy(() => unsetDashboardPage());
    }

    // ─── Shared shell helpers (same behaviour as the other dashboards) ──
    async _rpc(route, params) {
        return rpcJsonSafe(route, params);
    }

    tr(key) {
        return _tr(key);
    }

    get navSections() {
        return [
            { key: 'home', icon: '\u{1F3E0}', label: 'Home', single: true, go: 'goHome', view: 'home' },
            // Where "My Shift" sits for every other role. A delivery driver has
            // no shift; the vehicle is the thing they are answerable for.
            { key: 'trips', icon: '\u{1F4E6}', label: 'My Trips', single: true, go: 'openMyTrips', view: 'my_trips' },
            { key: 'truck', icon: '\u{1F69A}', label: 'My Truck', single: true, go: 'openMyTruck', view: 'my_truck' },
            // The base warehouse this driver belongs to — the "My Warehouse"
            // screen every other role has, given to the driver too.
            { key: 'warehouse', icon: '\u{1F3ED}', label: 'My Warehouse', single: true, go: 'openMyWarehouse', view: 'my_warehouse' },
            { key: 'settings', icon: '⚙️', label: 'Settings', single: true, go: 'showSettings', view: 'settings' },
        ];
    }

    toggleSidebar(ev) {
        if (ev) { ev.stopPropagation(); ev.preventDefault(); }
        this.state.sidebarOpen = !this.state.sidebarOpen;
    }
    toggleNavSection(key) {
        this.state.navSection = this.state.navSection === key ? null : key;
    }
    navClick(fnName) {
        this.state.sidebarOpen = false;
        this.state.activeNavGo = fnName;
        const fn = this[fnName];
        if (typeof fn === 'function') fn.call(this);
    }
    _navigate(view) { this._navHistory.push(this.state.view); this.state.view = view; }
    goBack() { this.state.view = this._navHistory.pop() || 'home'; }
    goHome() { this._navHistory = []; this.state.view = 'home'; this._loadMyTruck(); }
    showSettings() { this._navigate('settings'); }

    /** The driver's base warehouse — its details refresh with the truck call.
     *  No map: the screen shows the coordinates and a Google-Maps button only. */
    async openMyWarehouse() {
        this._navigate('my_warehouse');
        await this._loadMyTruck();
    }

    toggleDarkMode() {
        this.state.darkMode = !this.state.darkMode;
        localStorage.setItem('dw-theme', this.state.darkMode ? 'dark' : 'light');
        this._applyTheme();
    }
    _applyTheme() {
        const root = document.documentElement;
        if (this.state.darkMode) root.setAttribute('data-theme', 'dark');
        else root.removeAttribute('data-theme');
    }
    setLanguage(lang) {
        this.state.lang = lang;
        localStorage.setItem('recycle_wms_lang', lang);
        window.location.reload();
    }

    // ─── My Trips (delivery) ────────────────────────────────────
    async openMyTrips() {
        this._navigate('my_trips');
        await this._loadMyTrips();
    }

    setTripsTab(tab) { this.state.tripsTab = tab; }

    async _loadMyTrips() {
        this.state.loading = true;
        this.state.tripsError = null;
        try {
            const res = await this._rpc('/api/recycle/my-delivery-trips', {});
            if (res && res.error) {
                this.state.tripsError = this.tr('This account is not linked to a delivery driver record.');
                this.state.trips = [];
                this.state.tripsActive = [];
                this.state.tripsCompleted = [];
            } else {
                this.state.tripsActive = (res && res.active) || [];
                this.state.tripsCompleted = (res && res.completed) || [];
                // The active flow (confirm-pickup) still reads state.trips.
                this.state.trips = this.state.tripsActive;
            }
        } catch (e) {
            this.state.tripsError = (e && e.data && e.data.message) || this.tr('Action failed.');
        } finally {
            this.state.loading = false;
        }
    }

    /** Confirm taking the next station's goods; the next stop then opens. */
    async confirmPickup(trip) {
        if (!trip || !trip.next_stop || this.state.tripBusy) return;
        this.state.tripBusy = trip.trip_id;
        try {
            const res = await this._rpc('/api/recycle/delivery-confirm-pickup', {
                trip_id: trip.trip_id,
                backend_stop_id: trip.next_stop.backend_stop_id,
            });
            if (res && res.error) this.state.tripsError = res.error;
            await this._loadMyTrips();
        } catch (e) {
            this.state.tripsError = (e && e.data && e.data.message) || this.tr('Action failed.');
        } finally {
            this.state.tripBusy = null;
        }
    }

    /** Hand the whole load to the buyer at the last stop. */
    async completeDelivery(trip) {
        if (!trip || this.state.tripBusy) return;
        this.state.tripBusy = trip.trip_id;
        try {
            const res = await this._rpc('/api/recycle/delivery-complete', { trip_id: trip.trip_id });
            if (res && res.error) this.state.tripsError = res.error;
            await this._loadMyTrips();
        } catch (e) {
            this.state.tripsError = (e && e.data && e.data.message) || this.tr('Action failed.');
        } finally {
            this.state.tripBusy = null;
        }
    }

    // ─── My Truck ───────────────────────────────────────────────
    async openMyTruck() {
        this._navigate('my_truck');
        await this._loadMyTruck();
    }

    async _loadMyTruck() {
        this.state.loading = true;
        this.state.truckError = null;
        try {
            const res = await this._rpc('/api/recycle/my-delivery-truck', {});
            if (res && res.error) {
                this.state.truckError = this.tr('This account is not linked to a delivery driver record.');
            } else if (res) {
                this.state.driver = res.driver || null;
                // "No truck yet" is a real answer, not a failure: a driver can
                // be on file before one is free. Saying so plainly beats an
                // empty screen that reads like something broke.
                this.state.truckAssigned = !!res.assigned;
                this.state.truck = res.truck || null;
                this.state.warehouse = res.warehouse || null;
                this.state.tripsThisMonth = res.trips_completed_this_month || 0;
            }
        } catch (e) {
            this.state.truckError = (e && e.data && e.data.message) || this.tr('Action failed.');
        }
        this.state.loading = false;
    }

    get truckStatusLabel() {
        if (!this.state.truck) return '';
        return this.state.truck.is_active
            ? this.tr('In Service') : this.tr('Out of Service');
    }

    // ─── Notifications ──────────────────────────────────────────
    async _loadNotifCount() {
        try {
            const r = await this._rpc('/api/recycle/notifications/unread-count', {});
            this.state.notifUnreadCount = (r && r.count) || 0;
        } catch (e) { this.state.notifUnreadCount = 0; }
    }

    async showNotifications() {
        this._navigate('notifications');
        this.state.notifLoading = true;
        try {
            const r = await this._rpc('/api/recycle/notifications', { limit: 50 });
            this.state.notifications = (r && r.notifications) || [];
            await this._rpc('/api/recycle/notifications/mark-all-read', {});
            this.state.notifUnreadCount = 0;
        } catch (e) { this.state.notifications = []; }
        this.state.notifLoading = false;
    }

    // ─── Profile ────────────────────────────────────────────────
    async showProfile() {
        this._navigate('profile');
        this.state.profileLoading = true;
        this.state.profileEditMode = false;
        this.state.profileSaveSuccess = null;
        this.state.profileSaveError = null;
        try {
            const p = await this._rpc('/api/recycle/my-profile', {});
            if (p) this.state.userProfile = Object.assign(this.state.userProfile, p);
        } catch (e) {}
        this.state.profileLoading = false;
    }

    startEditProfile() {
        const p = this.state.userProfile;
        this.state.profileForm = {
            name: p.name || '', phone: p.phone || '',
            national_id: p.national_id || '', street: p.street || '',
            city: p.city || '',
        };
        this.state.profileEditMode = true;
        this.state.profileSaveSuccess = null;
        this.state.profileSaveError = null;
    }
    cancelEditProfile() { this.state.profileEditMode = false; }

    async saveProfile() {
        this.state.profileSaving = true;
        this.state.profileSaveError = null;
        try {
            const res = await this._rpc('/api/recycle/save-profile', this.state.profileForm);
            if (res && res.error) {
                this.state.profileSaveError = res.error;
            } else {
                Object.assign(this.state.userProfile, this.state.profileForm);
                this.state.profileEditMode = false;
                this.state.profileSaveSuccess = this.tr('Profile updated successfully.');
            }
        } catch (e) {
            this.state.profileSaveError = (e && e.data && e.data.message) || this.tr('Action failed.');
        }
        this.state.profileSaving = false;
    }

    // ─── Security ───────────────────────────────────────────────
    openChangePasswordModal() {
        this.state.showChangePasswordModal = true;
        this.state.changePasswordStep = 1;
        this.state.changePasswordCurrent = '';
        this.state.changePasswordNew = '';
        this.state.changePasswordConfirm = '';
        this.state.changePasswordError = null;
    }
    closeChangePasswordModal() { this.state.showChangePasswordModal = false; }

    async submitChangePassword() {
        const s = this.state;
        if (!s.changePasswordCurrent) {
            s.changePasswordError = this.tr('Current password is required'); return;
        }
        if (s.changePasswordNew !== s.changePasswordConfirm) {
            s.changePasswordError = this.tr('Passwords do not match'); return;
        }
        s.changePasswordLoading = true;
        s.changePasswordError = null;
        try {
            const res = await this._rpc('/api/recycle/change-password', {
                current_password: s.changePasswordCurrent,
                new_password: s.changePasswordNew,
            });
            if (res && res.error) {
                s.changePasswordError = res.error;
            } else {
                // Step 2 is a confirmation panel rather than a toast: the
                // other dashboards do the same, and a driver who just changed
                // their password should see it acknowledged where they typed
                // it, not in a corner that fades.
                s.changePasswordStep = 2;
            }
        } catch (e) {
            s.changePasswordError = (e && e.data && e.data.message) || this.tr('Action failed.');
        }
        s.changePasswordLoading = false;
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

    formatDate(val) {
        if (!val) return '—';
        try { return new Date(val).toLocaleDateString('en-GB'); }
        catch { return val; }
    }

    /** Date AND time — for "when was this trip delivered / collected". Odoo
     *  hands back naive UTC strings ("2026-08-19 21:30:00"); normalise to a
     *  parseable ISO so the browser shows the driver a real local time. */
    formatDateTime(val) {
        if (!val) return '—';
        try {
            const iso = String(val).includes('T') ? val : String(val).replace(' ', 'T') + 'Z';
            const d = new Date(iso);
            return isNaN(d.getTime()) ? val
                : d.toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
        } catch { return val; }
    }
}

registry.category("actions").add(
    "recycle_delivery_driver_dashboard", RecycleDeliveryDriverDashboard);
