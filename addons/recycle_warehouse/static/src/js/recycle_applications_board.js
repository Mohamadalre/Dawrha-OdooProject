/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, useRef, onWillStart, onMounted, onWillDestroy } from "@odoo/owl";
import { tr } from "./recycle_i18n_shared";
import { makePager } from "./dashboard_shared";

const FIELDS = ["id", "recycle_name", "partner_name", "job_id", "stage_id",
    "recycle_stage_status", "recycle_email"];
const DOMAIN = [["recycle_state", "!=", "accepted"]];

/**
 * Admin "Job Applications" board — themed like the Recycle dashboard.
 * Lists submitted applications that are NOT yet accepted, and opens the
 * standard applicant form (with the stage Approve/Reject/Advance buttons)
 * when a card is clicked. Scrolling to the bottom loads the next batch of
 * older applications — no page-number buttons.
 */
export class RecycleApplicationsBoard extends Component {
    static template = "recycle_warehouse.RecycleApplicationsBoard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({ applications: [], loaded: false, hasMore: true, loadingMore: false });
        this.tr = tr;
        this.scrollRoot = useRef("scrollRoot");
        onWillStart(async () => {
            await this.load();
        });
        onMounted(() => {
            this._onScroll = () => {
                const el = this.scrollRoot.el;
                if (!el) return;
                const nearBottom = (el.scrollTop + el.clientHeight) >= (el.scrollHeight - 400);
                if (nearBottom) this.loadMore();
            };
            if (this.scrollRoot.el) this.scrollRoot.el.addEventListener("scroll", this._onScroll, { passive: true });
        });
        onWillDestroy(() => {
            if (this.scrollRoot.el && this._onScroll) this.scrollRoot.el.removeEventListener("scroll", this._onScroll);
        });
    }

    async load() {
        const pager = makePager(this.orm, { model: "hr.applicant", fields: FIELDS, pageSize: 300 });
        const { rows, hasMore } = await pager.fetchFirst(DOMAIN);
        this.state.applications = rows;
        this.state.hasMore = hasMore;
        this.state.loaded = true;
    }

    async loadMore() {
        if (!this.state.hasMore || this.state.loadingMore || !this.state.loaded) return;
        this.state.loadingMore = true;
        try {
            const lastId = this.state.applications.length
                ? this.state.applications[this.state.applications.length - 1].id : 0;
            const pager = makePager(this.orm, { model: "hr.applicant", fields: FIELDS, pageSize: 300 });
            const { rows, hasMore } = await pager.fetchMore(DOMAIN, lastId);
            this.state.applications = this.state.applications.concat(rows);
            this.state.hasMore = hasMore;
        } catch (e) { /* silent */ }
        this.state.loadingMore = false;
    }

    statusLabel(s) {
        return { pending: this.tr("Pending"), approved: this.tr("Approved"), rejected: this.tr("Rejected") }[s] || this.tr("Pending");
    }
    statusClass(s) {
        return (
            {
                pending: "o_recycle_badge_pending",
                approved: "o_recycle_badge_approved",
                rejected: "o_recycle_badge_rejected",
            }[s] || "o_recycle_badge_pending"
        );
    }

    openApplication(appId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "hr.applicant",
            res_id: appId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    goBack() {
        this.actionService.doAction("recycle_warehouse.action_recycle_admin_home");
    }
}

registry.category("actions").add("recycle_applications_board", RecycleApplicationsBoard);
