# -*- coding: utf-8 -*-
"""Fleet trucks — authored HERE (Odoo is the fleet master).

The NestJS backend mirrors this model 1:1 through its SYNC_FLEET job
(`recycle.truck` is read over JSON-RPC with the exact field names below,
see odoo.service.ts::fetchTrucks). Any create / update / delete therefore
pings the backend fleet webhook so the mirror refreshes within seconds.

Field names are a CONTRACT with the backend — do not rename:
    model, year, plate_number, max_payload_kg, warehouse_id, is_active
"""
from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

TRUCK_YEAR_MIN = 1980


class RecycleTruck(models.Model):
    _name = 'recycle.truck'
    _description = 'Fleet Truck'
    _order = 'name'

    name = fields.Char(
        'Truck Name', required=True,
        help='Friendly label shown in lists (e.g. "Damascus Truck 1").')
    # ── What the truck is FOR ───────────────────────────────────────────────
    #
    # The fleet does two unrelated jobs. A COLLECTION truck goes out to citizens
    # and institutions to pick material up; it is driven by a collector whose
    # account lives in the backend, who works a shift, and whose whole app is
    # built around that. A DELIVERY truck carries sold goods from a warehouse to
    # a buyer; it is driven by someone hired here, with no backend account and no
    # shift at all.
    #
    # Without this field the two were one pool, so a collector could be booked
    # onto a truck that never goes near a collection round — and the mistake
    # would only surface as a driver standing next to the wrong vehicle.
    truck_type = fields.Selection([
        ('collection', 'Collection'),
        ('delivery', 'Delivery'),
    ], string='Truck Type', required=True, default='collection', index=True,
        help='Collection trucks pick material up from citizens and are driven '
             'by backend collectors. Delivery trucks carry sold goods to buyers '
             'and are driven by delivery drivers created here.')
    plate_number = fields.Char('Plate Number', required=True, index=True)
    model = fields.Char(
        'Model',
        help='Manufacturer / model, e.g. "Hyundai HD65".')
    year = fields.Integer('Year')
    max_payload_kg = fields.Float('Max Payload (kg)', digits=(10, 2))
    # Bed dimensions. Recorded for EVERY truck (collection and delivery alike):
    # a load is not only a weight — a bulky-but-light load can fill the bed long
    # before the payload ceiling — so the person planning a run needs the size,
    # not just the kilograms.
    length_m = fields.Float(
        'Length (m)', digits=(6, 2),
        help='Cargo bed length in metres. Optional; mirrored to the backend.')
    width_m = fields.Float(
        'Width (m)', digits=(6, 2),
        help='Cargo bed width in metres. Optional; mirrored to the backend.')
    warehouse_id = fields.Many2one(
        'recycle.warehouse', string='Warehouse', index=True,
        ondelete='set null',
        help='Warehouse this truck serves. Leave empty for an '
             'unassigned truck.')
    is_active = fields.Boolean(
        'In Service', default=True,
        help='Out-of-service trucks stay visible here but are marked '
             'DISABLED in the backend mirror.')
    disable_reason = fields.Char(
        'Disable Reason',
        help='Why the truck was taken out of service (mandatory when a '
             'manager disables it; cleared when it returns to service).')
    notes = fields.Text('Notes')

    _plate_number_uniq = models.Constraint(
        'unique(plate_number)',
        'A truck with this plate number already exists.')

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    @api.constrains('year')
    def _check_year(self):
        year_max = date.today().year + 1
        for rec in self:
            if rec.year and not (TRUCK_YEAR_MIN <= rec.year <= year_max):
                raise ValidationError(_(
                    'Year must be between %(mn)s and %(mx)s.',
                    mn=TRUCK_YEAR_MIN, mx=year_max))

    @api.constrains('max_payload_kg')
    def _check_payload(self):
        for rec in self:
            if rec.max_payload_kg < 0:
                raise ValidationError(_('Max payload cannot be negative.'))
            if rec.length_m < 0 or rec.width_m < 0:
                raise ValidationError(_('Truck dimensions cannot be negative.'))

    # ------------------------------------------------------------------
    # Backend mirror sync (fire-and-forget, never blocks the workflow)
    # ------------------------------------------------------------------
    def _ping_backend_fleet(self):
        try:
            self.env['recycle.backend.sync'].sudo().notify_fleet_changed()
        except Exception:
            pass

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._ping_backend_fleet()
        return records

    def write(self, vals):
        # ── A truck's JOB is fixed for life ────────────────────────────────
        #
        # Flipping it would strand every assignment built on it: a collection
        # truck carries a collector booked to a shift, a delivery truck carries
        # a delivery driver, and the two are different tables with different
        # rules. Changing the type would leave those rows pointing at a vehicle
        # that no longer does the job they were written for — and nothing on
        # either screen would show it. Retire the truck and add the right one.
        if 'truck_type' in vals:
            changed = self.filtered(lambda t: t.truck_type != vals['truck_type'])
            if changed:
                raise UserError(_(
                    'A truck\'s job cannot be changed. "%s" was created as a '
                    '%s truck and every driver assignment made since assumes '
                    'that. Take it out of service and add the other truck '
                    'instead.') % (
                        changed[0].name,
                        _('collection') if changed[0].truck_type == 'collection'
                        else _('delivery')))

        res = super().write(vals)
        if 'warehouse_id' in vals:
            self._release_drivers_of_other_warehouse()
        self._ping_backend_fleet()
        return res

    def _release_drivers_of_other_warehouse(self):
        """A truck that MOVED leaves behind any driver who did not move with it.

        Deliveries and collection rounds both start at a warehouse, so a driver
        at site A holding a vehicle now parked at site B has an assignment that
        reads as done and cannot be worked. Releasing it is the honest outcome:
        the truck returns to the pool of its new warehouse and is re-assigned
        there, to someone who can actually reach it.

        Silence would be worse than the release, so both sides are told.
        """
        for truck in self:
            wh = truck.warehouse_id

            # Delivery drivers hold the truck directly.
            History = self.env['recycle.truck.assignment.history'].sudo()
            drivers = self.env['recycle.delivery.driver'].sudo().search(
                [('truck_id', '=', truck.id)])
            for driver in drivers:
                if wh and driver.warehouse_id.id == wh.id:
                    continue
                History.close_open_periods(
                    truck, reason='warehouse_change', delivery_driver=driver)
                driver.with_context(recycle_history_done=True).write(
                    {'truck_id': False})
                driver.message_post(body=_(
                    'Truck %(truck)s moved to warehouse %(wh)s, so this '
                    'assignment was released — a driver cannot load from a '
                    'site they do not work at.') % {
                        'truck': truck.name,
                        'wh': wh.name if wh else _('none')})

            # Collectors hold it through an assignment row, and their warehouse
            # lives on the driver REQUEST rather than on the row itself.
            Assignment = self.env['recycle.driver.assignment'].sudo()
            Request = self.env['recycle.driver.request'].sudo()
            for row in Assignment.search([('truck_id', '=', truck.id)]):
                request = Request.search(
                    [('backend_driver_id', '=', row.backend_driver_id)], limit=1)
                if wh and request and request.warehouse_id.id == wh.id:
                    continue
                History.close_open_periods(
                    truck, reason='warehouse_change', driver_request=request)
                row.with_context(recycle_history_done=True).unlink()

    def unlink(self):
        res = super().unlink()
        self._ping_backend_fleet()
        return res

    # ------------------------------------------------------------------
    # Dashboard helpers
    # ------------------------------------------------------------------
    def action_assign_warehouse(self, warehouse_id):
        """Assign (or unassign with falsy id) the truck to a warehouse."""
        self.ensure_one()
        self.write({'warehouse_id': int(warehouse_id) if warehouse_id else False})
        return True

    def action_toggle_service_state(self, reason=None):
        """Flip in-service / out-of-service.

        Admin: any truck. Warehouse manager: ONLY trucks of his own
        warehouse — and only the state, never the truck's data (managers
        hold read-only ACL on this model; the state flip runs under sudo
        after this explicit ownership check).

        Disabling REQUIRES a reason (shown to the admin next to the truck);
        re-enabling clears it.
        """
        self.ensure_one()
        user = self.env.user
        if not (self.env.su
                or user.has_group('recycle_warehouse.group_recycle_admin')):
            wh = self.warehouse_id
            is_own_manager = bool(
                user.has_group('recycle_warehouse.group_recycle_manager')
                and wh
                and (wh.manager_user_id.id == user.id
                     or (user.recycle_warehouse_id
                         and user.recycle_warehouse_id.id == wh.id)))
            if not is_own_manager:
                raise UserError(_(
                    'Only the administrator or the manager of this '
                    "truck's warehouse can change its service state."))
        if self.is_active:
            reason = (reason or '').strip()
            if not reason:
                raise UserError(_(
                    'A reason is required to take a truck out of service.'))
            self.sudo().write({'is_active': False,
                               'disable_reason': reason})
        else:
            self.sudo().write({'is_active': True, 'disable_reason': False})
        return True


class RecycleDriverAssignment(models.Model):
    """Driver ↔ truck ↔ shift assignment (minimal backend contract).

    The backend SYNC_FLEET job reads this model right after the trucks
    (fields backend_driver_id / truck_id / shift_id — a contract, do not
    rename); without it the whole fleet sync job crashes and retries
    forever. Rows are created when the Odoo admin approves a driver
    request — that flow lands in a later iteration, so an empty table is
    the expected steady state for now.
    """
    _name = 'recycle.driver.assignment'
    _description = 'Driver Truck Assignment'

    backend_driver_id = fields.Char(
        'Backend Driver ID', required=True, index=True,
        help='UUID of the collector profile in the NestJS backend.')
    truck_id = fields.Many2one(
        'recycle.truck', string='Truck', required=True, ondelete='cascade')
    shift_id = fields.Many2one(
        'recycle.shift', string='Shift', required=True, ondelete='cascade')

    _driver_uniq = models.Constraint(
        'unique(backend_driver_id)',
        'This driver already has a truck assignment.')
    _truck_shift_uniq = models.Constraint(
        'unique(truck_id, shift_id)',
        'This truck is already reserved by another driver in that shift.')

    @api.constrains('shift_id')
    def _check_driver_shift(self):
        """Drivers may only work driver shifts — never warehouse-staff ones
        (the mirror of the guard on res.users.shift_id)."""
        for rec in self:
            if rec.shift_id and rec.shift_id.shift_type != 'driver':
                raise ValidationError(_(
                    'Shift "%s" is a warehouse-staff shift and cannot be '
                    'assigned to a driver.') % rec.shift_id.name)

    @api.constrains('truck_id')
    def _check_truck_is_collection(self):
        """This table books COLLECTORS, and collectors drive collection trucks.

        A delivery truck runs no collection round and belongs to no shift, so
        booking a collector onto one produces an assignment that can never be
        worked. Enforced on the model rather than only in the pickers because the
        row can also be created by the backend sync and by the driver-approval
        flow, and a rule that lives in one screen is a rule the other paths do
        not have.
        """
        for rec in self:
            if rec.truck_id and rec.truck_id.truck_type != 'collection':
                raise ValidationError(_(
                    'Truck "%s" is a DELIVERY truck. Collectors can only be '
                    'assigned to collection trucks — a delivery truck is driven '
                    'by a delivery driver instead.') % rec.truck_id.name)

    def _ping_backend_fleet(self):
        try:
            self.env['recycle.backend.sync'].sudo().notify_fleet_changed()
        except Exception:
            pass

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._record_history_open()
        records._ping_backend_fleet()
        return records

    def write(self, vals):
        # A row that moves to another truck ends one holding period and starts
        # another; recorded here so the change is caught whichever screen made
        # it, including the manager's "change shift + truck" action.
        moving = 'truck_id' in vals
        before = {r.id: r.truck_id for r in self} if moving else {}
        res = super().write(vals)
        if moving:
            History = self.env['recycle.truck.assignment.history']
            Request = self.env['recycle.driver.request'].sudo()
            for row in self:
                old, new = before.get(row.id), row.truck_id
                if old == new:
                    continue
                request = Request.search(
                    [('backend_driver_id', '=', row.backend_driver_id)], limit=1)
                if old:
                    History.close_open_periods(
                        old, reason='reassigned', driver_request=request)
                if new:
                    History.open_period(new, 'collection',
                                        driver_request=request)
        self._ping_backend_fleet()
        return res

    def unlink(self):
        if not self.env.context.get('recycle_history_done'):
            History = self.env['recycle.truck.assignment.history']
            Request = self.env['recycle.driver.request'].sudo()
            for row in self:
                request = Request.search(
                    [('backend_driver_id', '=', row.backend_driver_id)], limit=1)
                if row.truck_id:
                    History.close_open_periods(
                        row.truck_id, reason='manual', driver_request=request)
        res = super().unlink()
        self._ping_backend_fleet()
        return res

    def _record_history_open(self):
        History = self.env['recycle.truck.assignment.history']
        Request = self.env['recycle.driver.request'].sudo()
        for row in self:
            request = Request.search(
                [('backend_driver_id', '=', row.backend_driver_id)], limit=1)
            History.open_period(row.truck_id, 'collection',
                                driver_request=request)

    # ------------------------------------------------------------------
    # Assign-driver-to-truck screen (admin + warehouse manager)
    # ------------------------------------------------------------------
    @api.model
    def _assignment_actor_scope(self):
        """Who is asking? → (is_admin, forced_warehouse).

        Admin: unrestricted (no forced warehouse). Warehouse manager: hard
        scoped to his own warehouse. Anyone else is refused — this backs the
        dashboard screen, so the check is explicit rather than ACL-only
        (reads/creates below run under sudo after it)."""
        user = self.env.user
        # env.su: the shell/tests superuser is a member of NO custom group —
        # same bypass every other supervisor check in this module uses.
        if self.env.su or user.has_group(
                'recycle_warehouse.group_recycle_admin'):
            return True, self.env['recycle.warehouse'].browse()
        if user.has_group('recycle_warehouse.group_recycle_manager'):
            wh = self.env['recycle.warehouse'].sudo().search(
                ['|', ('manager_user_id', '=', user.id),
                 ('id', '=', user.recycle_warehouse_id.id)], limit=1)
            if wh:
                return False, wh
        raise UserError(_(
            'Only the administrator or a warehouse manager can assign '
            'drivers to trucks.'))

    @api.model
    def get_assignment_options(self, shift_id, warehouse_id=False):
        """Everything the 'Assign driver to truck' screen needs for one
        shift: the trucks still free in that shift and the drivers of that
        shift who have no truck yet.

        Business rules (server-enforced, mirrored by action_assign_driver):
        - the shift is chosen FIRST and must be a driver shift;
        - a truck is offered when it is in service and has NO assignment in
          that shift (assignments in other shifts don't block it);
        - a driver is offered when his request was accepted, his onboarding
          shift matches, and he has no assignment in ANY shift."""
        is_admin, forced_wh = self._assignment_actor_scope()
        shift = self.env['recycle.shift'].sudo().browse(
            int(shift_id or 0)).exists()
        if not shift or shift.shift_type != 'driver':
            raise UserError(_('Choose a driver shift first.'))

        wh_id = forced_wh.id if not is_admin else int(warehouse_id or 0)

        Assignment = self.env['recycle.driver.assignment'].sudo()
        taken_truck_ids = Assignment.search(
            [('shift_id', '=', shift.id)]).mapped('truck_id').ids
        # COLLECTION only: this screen books collectors, and a delivery truck
        # runs no collection round. Offering one would let the picker propose an
        # assignment the model then refuses.
        truck_domain = [('is_active', '=', True),
                        ('truck_type', '=', 'collection'),
                        ('id', 'not in', taken_truck_ids)]
        if wh_id:
            truck_domain.append(('warehouse_id', '=', wh_id))
        trucks = self.env['recycle.truck'].sudo().search(
            truck_domain, order='name')

        assigned_driver_keys = Assignment.search(
            []).mapped('backend_driver_id')
        driver_domain = [('state', '=', 'accepted'),
                         ('is_blocked', '=', False),
                         ('shift_id', '=', shift.id),
                         ('backend_driver_id', 'not in',
                          assigned_driver_keys)]
        if wh_id:
            driver_domain.append(('warehouse_id', '=', wh_id))
        drivers = self.env['recycle.driver.request'].sudo().search(
            driver_domain, order='name')

        return {
            'trucks': [{
                'id': t.id,
                'name': t.name,
                'plate_number': t.plate_number,
                'model': t.model or '',
                'warehouse': t.warehouse_id.name or '',
            } for t in trucks],
            'drivers': [{
                'id': d.id,
                'backend_driver_id': d.backend_driver_id,
                'name': d.name,
                'phone': d.phone or '',
                'warehouse': d.warehouse_id.name or '',
            } for d in drivers],
        }

    @api.model
    def action_assign_driver(self, backend_driver_id, truck_id, shift_id):
        """Reserve a truck for a driver in one shift. Every business rule is
        re-checked here (the screen might be stale): the truck must be free
        in that shift, the driver must be accepted, of that shift, truckless
        across ALL shifts, and both must be inside the actor's scope."""
        is_admin, forced_wh = self._assignment_actor_scope()

        shift = self.env['recycle.shift'].sudo().browse(
            int(shift_id or 0)).exists()
        if not shift or shift.shift_type != 'driver':
            raise UserError(_('Choose a driver shift first.'))

        truck = self.env['recycle.truck'].sudo().browse(
            int(truck_id or 0)).exists()
        if not truck or not truck.is_active:
            raise UserError(_('This truck is not available.'))
        if truck.truck_type != 'collection':
            raise UserError(_(
                'Truck "%s" is a delivery truck — collectors are assigned to '
                'collection trucks only.') % truck.name)
        if not is_admin and truck.warehouse_id.id != forced_wh.id:
            raise UserError(_(
                'You can only assign trucks of your own warehouse.'))

        driver = self.env['recycle.driver.request'].sudo().search(
            [('backend_driver_id', '=', backend_driver_id or '')], limit=1)
        if not driver or driver.state != 'accepted':
            raise UserError(_('This driver is not an accepted driver.'))
        if not is_admin and driver.warehouse_id.id != forced_wh.id:
            raise UserError(_(
                'You can only assign drivers of your own warehouse.'))
        if driver.shift_id and driver.shift_id.id != shift.id:
            raise UserError(_(
                'Driver "%s" belongs to shift "%s" — pick that shift to '
                'assign him.') % (driver.name, driver.shift_id.name))

        Assignment = self.env['recycle.driver.assignment'].sudo()
        if Assignment.search_count(
                [('backend_driver_id', '=', driver.backend_driver_id)]):
            raise UserError(_(
                'Driver "%s" already has a truck reserved.') % driver.name)
        if Assignment.search_count([('truck_id', '=', truck.id),
                                    ('shift_id', '=', shift.id)]):
            raise UserError(_(
                'Truck "%s" is already reserved in that shift.') % truck.name)

        Assignment.create({
            'backend_driver_id': driver.backend_driver_id,
            'truck_id': truck.id,
            'shift_id': shift.id,
        })
        return True

    @api.model
    def get_shift_free_trucks(self, shift_id):
        """Trucks the actor may reserve on `shift_id` right now: in service
        (disabled trucks NEVER appear in any picker), inside his scope, and
        not already reserved in that shift. Used by the manager's
        change-driver-shift and approve-request pickers."""
        is_admin, forced_wh = self._assignment_actor_scope()
        shift = self.env['recycle.shift'].sudo().browse(
            int(shift_id or 0)).exists()
        if not shift or shift.shift_type != 'driver':
            raise UserError(_('Choose a driver shift first.'))
        Assignment = self.env['recycle.driver.assignment'].sudo()
        taken_ids = Assignment.search(
            [('shift_id', '=', shift.id)]).mapped('truck_id').ids
        domain = [('is_active', '=', True),
                  ('truck_type', '=', 'collection'),
                  ('id', 'not in', taken_ids)]
        if not is_admin:
            domain.append(('warehouse_id', '=', forced_wh.id))
        trucks = self.env['recycle.truck'].sudo().search(domain, order='name')
        return [{
            'id': t.id,
            'name': t.name,
            'plate_number': t.plate_number,
            'model': t.model or '',
            'warehouse': t.warehouse_id.name or '',
        } for t in trucks]

    @api.model
    def action_change_driver_shift(self, backend_driver_id, shift_id,
                                   truck_id):
        """Directly move a driver to another shift + a free truck of it
        (manager scoped to his warehouse / admin anywhere). His existing
        assignment MOVES; a truckless driver simply gets one. The backend
        mirror follows through the fleet ping (SYNC_FLEET re-aligns the
        driver's shift too)."""
        is_admin, forced_wh = self._assignment_actor_scope()

        shift = self.env['recycle.shift'].sudo().browse(
            int(shift_id or 0)).exists()
        if not shift or shift.shift_type != 'driver':
            raise UserError(_('Choose a driver shift first.'))

        driver = self.env['recycle.driver.request'].sudo().search(
            [('backend_driver_id', '=', backend_driver_id or '')], limit=1)
        if not driver or driver.state != 'accepted':
            raise UserError(_('This driver is not an accepted driver.'))
        if driver.is_blocked:
            raise UserError(_('This driver is blocked.'))
        if not is_admin and driver.warehouse_id.id != forced_wh.id:
            raise UserError(_(
                'You can only manage drivers of your own warehouse.'))

        truck = self.env['recycle.truck'].sudo().browse(
            int(truck_id or 0)).exists()
        if not truck or not truck.is_active:
            raise UserError(_('This truck is not available.'))
        if truck.truck_type != 'collection':
            raise UserError(_(
                'Truck "%s" is a delivery truck — collectors are assigned to '
                'collection trucks only.') % truck.name)
        if not is_admin and truck.warehouse_id.id != forced_wh.id:
            raise UserError(_(
                'You can only assign trucks of your own warehouse.'))

        Assignment = self.env['recycle.driver.assignment'].sudo()
        taken = Assignment.search(
            [('truck_id', '=', truck.id), ('shift_id', '=', shift.id),
             ('backend_driver_id', '!=', driver.backend_driver_id)], limit=1)
        if taken:
            raise UserError(_(
                'Truck "%s" is already reserved in that shift.') % truck.name)

        row = Assignment.search(
            [('backend_driver_id', '=', driver.backend_driver_id)], limit=1)
        if row:
            row.write({'truck_id': truck.id, 'shift_id': shift.id})
        else:
            Assignment.create({
                'backend_driver_id': driver.backend_driver_id,
                'truck_id': truck.id,
                'shift_id': shift.id,
            })
        driver.sudo().write({'shift_id': shift.id})
        return True
