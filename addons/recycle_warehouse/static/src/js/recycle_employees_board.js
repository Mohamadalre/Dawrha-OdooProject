/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";
import { tr } from "./recycle_i18n_shared";
import { useMessageDialog } from "./dashboard_shared";

/**
 * Admin "Employees" board — themed like the Recycle dashboard.
 * Lists current employees/managers and lets the admin delete one. Deleting
 * removes the account, job applications and warehouse role, but KEEPS the
 * employee's shipment links intact (the account is deactivated, not erased).
 */
export class RecycleEmployeesBoard extends Component {
    static template = "recycle_warehouse.RecycleEmployeesBoard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({ employees: [], loaded: false });

        // Shared in-page message/confirm dialog — replaces window.confirm().
        useMessageDialog(this);
        this.tr = tr;
        onWillStart(async () => {
            await this.load();
        });
    }

    async load() {
        this.state.employees = await this.orm.searchRead(
            "res.users",
            [["recycle_role", "!=", false]],
            ["name", "login", "recycle_role", "recycle_warehouse_id"],
            { order: "name" }
        );
        this.state.loaded = true;
    }

    roleLabel(r) {
        return (
            {
                manager: this.tr("Warehouse Manager"),
                input: this.tr("Input Employee"),
                sorting: this.tr("Sorting Employee"),
                output: this.tr("Output Employee"),
            }[r] || r || this.tr("Employee")
        );
    }

    async deleteEmployee(emp) {
        // The name moves into the TITLE and the consequence into the body.
        // `confirm()` had one string for both, so the two were glued with
        // `\n\n` — which a dialog renders as the paragraph break it always
        // meant, and a title bar renders properly instead of truncating.
        const ok = await this.askConfirm(
            this.tr('Delete employee') + ` — ${emp.name}`,
            this.tr('This removes their account, job applications and warehouse role. Shipment records are kept.'),
        );
        if (!ok) {
            return;
        }
        try {
            await this.orm.call("res.users", "action_recycle_purge_employee", [[emp.id]]);
            await this.actionService.doAction({
                type: 'ir.actions.client',
                tag: 'display_notification',
                params: {
                    type: 'success',
                    title: this.tr('Success'),
                    message: this.tr('Employee deleted successfully.') + ` "${emp.name}"`,
                    sticky: false,
                },
            });
        } catch (e) {
            await this.actionService.doAction({
                type: 'ir.actions.client',
                tag: 'display_notification',
                params: {
                    type: 'danger',
                    title: this.tr('Error'),
                    message: this.tr('Failed to delete employee:') + ` ${e.message || e}`,
                    sticky: false,
                },
            });
        }
        await this.load();
    }

    goBack() {
        this.actionService.doAction("recycle_warehouse.action_recycle_admin_home");
    }
}

registry.category("actions").add("recycle_employees_board", RecycleEmployeesBoard);
