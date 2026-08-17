/** @odoo-module **/
import { Component, onMounted, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { tr } from "./recycle_i18n_shared";

function fmtDt(dtStr) {
    if (!dtStr) return "—";
    const d = new Date(dtStr);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
}

function statusLabel(s) {
    return { present: tr("Present"), late: tr("Late"), early_leave: tr("Left Early"), late_and_early: tr("Late & Early") }[s] || s;
}

function statusClass(s) {
    if (s === "present") return "o_att_badge_present";
    if (s === "late" || s === "late_and_early") return "o_att_badge_late";
    return "o_att_badge_early";
}

export class RecycleManagerAttendance extends Component {
    static template = "recycle_warehouse.RecycleManagerAttendance";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.userName = user.name || "Manager";
        this.tr = tr;

        const today = new Date().toISOString().slice(0, 10);
        this.state = useState({
            loading: true,
            today,
            records: [],
            totalPresent: 0,
            totalLate: 0,
            totalEarly: 0,
        });

        onMounted(async () => {
            await this.loadAttendance();
        });
    }

    async loadAttendance() {
        this.state.loading = true;
        try {
            const records = await this.orm.searchRead(
                "recycle.attendance",
                [["date", "=", this.state.today]],
                [
                    "employee_user_id", "shift_id",
                    "check_in", "check_out",
                    "status", "late_minutes",
                    "early_leave_minutes", "work_hours",
                ],
                { limit: 200 }
            );

            let present = 0, late = 0, early = 0;
            for (const r of records) {
                if (r.status === "present") present++;
                else if (r.status === "late" || r.status === "late_and_early") late++;
                else if (r.status === "early_leave") early++;

                // format helpers on each record
                r._checkInFmt  = fmtDt(r.check_in);
                r._checkOutFmt = fmtDt(r.check_out);
                r._statusLabel = statusLabel(r.status);
                r._statusClass = statusClass(r.status);
                r._empName     = Array.isArray(r.employee_user_id) ? r.employee_user_id[1] : "—";
                r._shiftName   = Array.isArray(r.shift_id) ? r.shift_id[1] : "—";

                // work hours display
                const wh = r.work_hours || 0;
                const h = Math.floor(wh);
                const m = Math.round((wh - h) * 60);
                r._workDisplay = wh > 0 ? `${h}h ${m}m` : "—";
            }

            this.state.records = records;
            this.state.totalPresent = present;
            this.state.totalLate = late;
            this.state.totalEarly = early;
        } catch (e) {
            if (console && console.error) console.error("Attendance load error:", e);
        }
        this.state.loading = false;
    }

    openFullList() {
        this.actionService.doAction("recycle_warehouse.action_attendance_manager");
    }

    goBack() {
        window.history.back();
    }
}

registry.category("actions").add("recycle_manager_attendance", RecycleManagerAttendance);
