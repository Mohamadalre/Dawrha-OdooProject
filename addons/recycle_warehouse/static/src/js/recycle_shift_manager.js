/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { tr } from "./recycle_i18n_shared";

/**
 * Convert "HH:MM" string (from <input type="time">) to float hours.
 * "08:30" → 8.5,  "17:00" → 17.0
 */
function timeToFloat(s) {
    if (!s) return 0;
    const [h, m] = s.split(":").map(Number);
    return h + m / 60;
}

/**
 * Convert float hours to "HH:MM" string for <input type="time"> default value.
 * 8.5 → "08:30",  17.0 → "17:00"
 */
function floatToTimeStr(f) {
    const h = Math.floor(f);
    const m = Math.round((f - h) * 60);
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

export class RecycleShiftManager extends Component {
    static template = "recycle_warehouse.RecycleShiftManager";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.userName = user.name || "Admin";
        this.tr = tr;

        this.state = useState({
            view: "menu",   // "menu" | "create" | "success"
            saving: false,
            error: null,
            savedName: "",
            form: {
                name: "",
                startTime: "08:00",
                endTime: "17:00",
                tolerance: 15,
            },
        });
    }

    showCreateForm() {
        this.state.view = "create";
        this.state.error = null;
    }

    viewShifts() {
        this.actionService.doAction("recycle_warehouse.action_recycle_shifts");
    }

    goBack() {
        if (this.state.view !== "menu") {
            // Go back to the shift menu
            this.state.view = "menu";
            this.state.error = null;
            this.state.form = { name: "", startTime: "08:00", endTime: "17:00", tolerance: 15 };
        } else {
            // Already on menu — navigate back to the admin dashboard
            this.actionService.doAction("recycle_warehouse.action_recycle_admin_home");
        }
    }

    onNameInput(ev) {
        this.state.form.name = ev.target.value;
    }
    onStartInput(ev) {
        this.state.form.startTime = ev.target.value;
    }
    onEndInput(ev) {
        this.state.form.endTime = ev.target.value;
    }
    onToleranceInput(ev) {
        this.state.form.tolerance = parseInt(ev.target.value) || 0;
    }

    async createShift() {
        const f = this.state.form;
        if (!f.name.trim()) {
            this.state.error = this.tr("Shift name is required.");
            return;
        }
        const startFloat = timeToFloat(f.startTime);
        const endFloat = timeToFloat(f.endTime);
        // An overnight shift (end < start) is valid — it crosses midnight
        // (e.g. 17:00 -> 00:00). Only an identical start/end is rejected.
        if (endFloat === startFloat) {
            this.state.error = this.tr("Start and end time cannot be the same.");
            return;
        }
        if (f.tolerance < 0) {
            this.state.error = this.tr("Tolerance cannot be negative.");
            return;
        }

        this.state.saving = true;
        this.state.error = null;

        try {
            await this.orm.create("recycle.shift", [{
                name: f.name.trim(),
                start_time: startFloat,
                end_time: endFloat,
                tolerance: f.tolerance,
                active: true,
            }]);
            this.state.savedName = f.name.trim();
            this.state.view = "success";
        } catch (e) {
            this.state.error = e.message || this.tr("An error occurred while saving.");
        } finally {
            this.state.saving = false;
        }
    }

    createAnother() {
        this.state.view = "create";
        this.state.error = null;
        this.state.form = { name: "", startTime: "08:00", endTime: "17:00", tolerance: 15 };
    }
}

registry.category("actions").add("recycle_shift_manager", RecycleShiftManager);
