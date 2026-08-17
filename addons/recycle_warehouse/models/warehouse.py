# -*- coding: utf-8 -*-
import logging
from html import escape as _esc

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessDenied

_logger = logging.getLogger(__name__)

ZONE_TYPES = [
    ('receiving', 'Receiving'),
    ('sorting', 'Sorting'),
    ('storage', 'Storage'),
    ('output', 'Output'),
]


class RecycleWarehouse(models.Model):
    _name = 'recycle.warehouse'
    _description = 'Recycle Warehouse'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, copy=False, tracking=True)
    # Location: governorate + GPS coordinates entered by the admin when the
    # warehouse is created, so it can be placed on a map and grouped by region.
    # Governorates live in their own mirrored table (recycle.province) rather
    # than a hard-coded Selection, so the list is authored ONCE in the backend
    # and Odoo follows every add/rename/delete. `governorate` survives as a
    # stored, read-only mirror of the province NAME so every existing reader
    # (dashboard API, backend payload, reports, JS) keeps working unchanged.
    province_id = fields.Many2one(
        'recycle.province', string='Governorate', tracking=True,
        ondelete='restrict')
    governorate = fields.Char(
        string='Governorate (name)', compute='_compute_governorate',
        store=True, readonly=True)
    # The backend's own uuid for this governorate, carried here so the mirror
    # sync can link a warehouse to a `provinces` row in ONE read — without it
    # the backend would have to match on the display name, which is exactly the
    # fragility the province table was introduced to remove.
    province_backend_id = fields.Char(
        string='Governorate ID (Backend)',
        related='province_id.backend_province_id', store=True, readonly=True)
    address = fields.Char(string='Address', tracking=True)
    capacity = fields.Integer(
        string='Capacity', tracking=True,
        help='Storage capacity as recorded in the backend, mirrored here so '
             'both systems report the same figure.')
    latitude = fields.Float(
        string='Latitude', digits=(10, 7), tracking=True,
        help='GPS latitude in decimal degrees (e.g. 33.5138).')
    longitude = fields.Float(
        string='Longitude', digits=(10, 7), tracking=True,
        help='GPS longitude in decimal degrees (e.g. 36.2765).')
    manager_user_id = fields.Many2one(
        'res.users', string='Warehouse Manager', tracking=True)
    zone_ids = fields.One2many('recycle.zone', 'warehouse_id', string='Zones')
    shipment_ids = fields.One2many('recycle.shipment', 'warehouse_id', string='Shipments')
    stock_ids = fields.One2many('recycle.stock', 'warehouse_id', string='Stock')
    order_ids = fields.One2many('recycle.order', 'warehouse_id', string='Orders')
    employee_user_ids = fields.One2many(
        'res.users', 'recycle_warehouse_id', string='Warehouse Employees')
    active = fields.Boolean(default=True)
    # ── Lifecycle ──────────────────────────────────────────────────────
    # `active` alone cannot express the middle of a shutdown: a warehouse that
    # stops taking NEW work but must still ship out what it already holds.
    #   active   → fully operational
    #   closing  → no new shipments/orders; existing stock is still shipped out
    #   inactive → fully stopped; never offered anywhere
    # `active` (the archive flag) is only flipped off at the very end, so all
    # history (shipments, employees, trucks) stays attached to the record.
    state = fields.Selection([
        ('active', 'Active'),
        ('closing', 'Closing'),
        ('inactive', 'Inactive'),
    ], default='active', required=True, tracking=True, index=True,
        help='Active: normal. Closing: no new intake, existing stock is still '
             'shipped out. Inactive: fully stopped.')
    closing_started_at = fields.Datetime('Closing Started At', readonly=True)
    closed_at = fields.Datetime('Closed At', readonly=True)
    shipment_count = fields.Integer(compute='_compute_counts')
    employee_count = fields.Integer(compute='_compute_counts')
    order_count = fields.Integer(compute='_compute_counts')
    truck_count = fields.Integer(compute='_compute_fleet_counts')
    driver_count = fields.Integer(compute='_compute_fleet_counts')

    @api.depends('province_id', 'province_id.name_ar', 'province_id.name_en')
    def _compute_governorate(self):
        """Denormalise the province name onto the warehouse. Stored (so it is
        searchable/groupable exactly like the old Selection was) and recomputed
        automatically when the backend renames a province."""
        for wh in self:
            province = wh.province_id
            wh.governorate = (
                province.name_ar or province.name_en) if province else False

    def _compute_counts(self):
        for wh in self:
            wh.shipment_count = len(wh.shipment_ids)
            wh.employee_count = len(wh.employee_user_ids)
            wh.order_count = len(wh.order_ids)

    def _compute_fleet_counts(self):
        """Fleet figures per warehouse: its trucks, and the drivers accepted
        into it (driver requests are the driver roster here — the driver
        ACCOUNT itself lives in the NestJS backend)."""
        Truck = self.env['recycle.truck'].sudo()
        Driver = self.env['recycle.driver.request'].sudo()
        for wh in self:
            wh.truck_count = Truck.search_count(
                [('warehouse_id', '=', wh.id)])
            wh.driver_count = Driver.search_count(
                [('warehouse_id', '=', wh.id), ('state', '=', 'accepted')])

    # The code identifies ONE site, and the database says so — a search-based
    # check alone can be beaten by two requests arriving together, and a
    # duplicate code means stock counted against the wrong warehouse and orders
    # routed to the wrong building. The constraint is on the raw column; the
    # check below adds the case- and whitespace-insensitivity a human expects,
    # plus a message that names the rule.
    _code_uniq = models.Constraint(
        'unique(code)', 'Warehouse code must be unique.')

    @api.constrains('code')
    def _check_code_unique(self):
        """Unique ignoring case and padding, and across ARCHIVED sites too.

        `=ilike` rather than `=`: to everyone who writes a code on paperwork or
        reads one over the phone, "wh1" and "WH1" are the same warehouse, and a
        rule that disagrees with its users is a rule they route around by
        accident. `active_test=False` because an archived warehouse still owns
        its code — reopening it later must not collide with a site created in
        the meantime.
        """
        for rec in self:
            code = (rec.code or '').strip()
            if not code:
                raise ValidationError(_('Warehouse code is required.'))
            if self.with_context(active_test=False).search_count(
                    [('code', '=ilike', code), ('id', '!=', rec.id)]):
                raise ValidationError(_(
                    'Warehouse code "%s" is already used by another warehouse. '
                    'A code identifies one site and cannot be shared.') % code)


    # ------------------------------------------------------------------
    # WHERE the warehouse is: required once, and then fixed
    # ------------------------------------------------------------------
    # Neither is declared `required=True` on the field, deliberately. Warehouses
    # already exist without a governorate — a NOT NULL
    # column would fail the module upgrade outright, and there is no honest
    # value to backfill the others with: inventing a governorate is inventing
    # where a building is. So the rule is enforced on CREATION, where it can be
    # answered, and the legacy rows are left visible as the gaps they are.
    _LOCATION_FIELDS = ('province_id', 'address')

    def _assert_location_given(self, vals):
        """A new warehouse must say where it is."""
        if not vals.get('province_id'):
            raise ValidationError(_(
                'A governorate is required. Order allocation matches buyers to '
                'warehouses by it, so a warehouse without one holds stock that '
                'no order can ever be routed to.'))
        if not (vals.get('address') or '').strip():
            raise ValidationError(_(
                'An address is required. Coordinates put a pin on a map; they '
                'do not tell a driver which gate, and a collection order with '
                'no address is one the buyer cannot act on.'))

    def _assert_location_unchanged(self, vals):
        """A warehouse cannot MOVE.

        Order allocation matches by governorate, and every cached distance,
        open order and delivery price already computed assumes where this
        building is. Moving it between governorates is not an edit — it is a
        new warehouse and the closure of an old one.

        The one exception is FILLING IN what was never recorded. Warehouses
        already exist with no governorate; refusing to write one would leave
        them permanently unroutable with no way to correct them,
        which is a worse outcome than the rule protects against.
        """
        for rec in self:
            if 'province_id' in vals and rec.province_id \
                    and vals['province_id'] != rec.province_id.id:
                raise ValidationError(_(
                    'A warehouse cannot be moved to another governorate. '
                    'Close this one and create the new site instead.'))
            if 'address' in vals and (rec.address or '').strip() \
                    and (vals.get('address') or '').strip() != (rec.address or '').strip():
                raise ValidationError(_(
                    'A warehouse address cannot be changed. Close this one and '
                    'create the new site instead.'))

    @api.constrains('name')
    def _check_name_unique(self):
        for rec in self:
            name = (rec.name or '').strip()
            if name and self.with_context(active_test=False).search_count(
                    [('name', '=ilike', name), ('id', '!=', rec.id)]):
                raise ValidationError(_('Warehouse name must be unique.'))

    @api.constrains('latitude', 'longitude')
    def _check_coordinates(self):
        for rec in self:
            if rec.latitude and not (-90.0 <= rec.latitude <= 90.0):
                raise ValidationError(_('Latitude must be between -90 and 90.'))
            if rec.longitude and not (-180.0 <= rec.longitude <= 180.0):
                raise ValidationError(_('Longitude must be between -180 and 180.'))

    @api.constrains('manager_user_id')
    def _check_manager_unique(self):
        for rec in self:
            if rec.manager_user_id and self.search_count([
                    ('manager_user_id', '=', rec.manager_user_id.id),
                    ('id', '!=', rec.id)]):
                raise ValidationError(
                    _('This user already manages another warehouse.'))

    def _ensure_zones(self):
        Zone = self.env['recycle.zone'].sudo()
        for wh in self:
            existing_types = wh.zone_ids.mapped('zone_type')
            for ztype, zlabel in ZONE_TYPES:
                if ztype not in existing_types:
                    Zone.create({
                        'name': zlabel,
                        'zone_type': ztype,
                        'warehouse_id': wh.id,
                    })

    def _sync_manager(self):
        for wh in self:
            if wh.manager_user_id:
                wh.manager_user_id.sudo().write({
                    'recycle_warehouse_id': wh.id,
                    'recycle_role': 'manager',
                })

    @api.model_create_multi
    def create(self, vals_list):
        # The backend authors warehouses and knows its governorate by NAME (or
        # by the province uuid) — never by an Odoo database id. Both are
        # accepted as transient keys here and resolved against the mirrored
        # province table, which is why the backend needs no key-mapping table
        # of its own any more.
        Province = self.env['recycle.province'].sudo()
        for vals in vals_list:
            # Trimmed on the way in: a trailing space makes two codes that
            # print alike and compare differently, and the one nobody can see
            # is the one that breaks.
            if vals.get('code'):
                vals['code'] = vals['code'].strip()
            backend_id = vals.pop('province_backend_id', None)
            name = vals.pop('province_name', None)
            if vals.get('province_id'):
                continue
            if backend_id:
                vals['province_id'] = Province.resolve_by_backend_id(backend_id)
            elif name:
                vals['province_id'] = Province.resolve_by_name(name)
        # Checked AFTER the province keys are resolved: the backend sends a name
        # or a backend uuid, not an Odoo id, so testing before the resolution
        # above would refuse every warehouse the backend creates.
        for vals in vals_list:
            self._assert_location_given(vals)
        records = super().create(vals_list)
        records._ensure_zones()
        records._sync_manager()
        # A warehouse BORN HERE has to announce itself.
        #
        # Only `write` pinged, so a site created in Odoo told the backend
        # nothing at all — it existed on this screen, held stock, took
        # shipments, and simply was not in the backend's list. Nobody noticed
        # because the backend was assumed to be the only place warehouses are
        # created, which stopped being true the moment this screen grew a
        # "create" button.
        records._notify_backend_changed()
        return records

    # Fields the backend mirrors. A change to any of them is a change the
    # backend must hear about on its own — its `SYNC_WAREHOUSE` job re-reads
    # exactly these, plus the manager and the stock lines.
    _BACKEND_MIRRORED_FIELDS = (
        'name', 'code', 'governorate', 'province_id', 'latitude', 'longitude',
        'state', 'manager_user_id', 'active',
        # CAPACITY was missing, so editing it here never reached the backend —
        # which reports load as a percentage of it. The two sides showed
        # different fullness for the same building until somebody called a sync
        # by hand.
        'capacity', 'address',
    )

    def write(self, vals):
        # Before the write, not after: a refusal must leave the record
        # untouched, and `super().write` has already committed by then.
        if any(f in vals for f in self._LOCATION_FIELDS):
            self._assert_location_unchanged(vals)
        res = super().write(vals)
        if 'manager_user_id' in vals:
            # `in vals`, not `.get(...)`: REMOVING a manager is a change too,
            # and the truthiness test skipped it — so the backend was never told
            # a site had been left without one.
            self._sync_manager()
        if any(f in vals for f in self._BACKEND_MIRRORED_FIELDS):
            self._notify_backend_changed()
        return res

    def _notify_backend_changed(self):
        """Tell the backend this warehouse's master data moved.

        Covers every mirrored field, not just the manager. Editing a warehouse
        here left the backend showing the OLD name, code, governorate,
        coordinates and lifecycle state until somebody called a sync route by
        hand — and the lifecycle one matters most: a warehouse put into
        `closing` stops accepting new orders, and a backend that has not been
        told keeps allocating orders to a site that is winding down.

        Never allowed to break the write. Losing the ping costs one stale field
        that the next sync corrects; raising here would refuse a warehouse edit
        because a remote service was unreachable — which is exactly when an
        administrator might need to make one.
        """
        Sync = self.env['recycle.backend.sync'].sudo()
        for warehouse in self:
            try:
                Sync.notify_warehouse_changed(warehouse)
            except Exception:            # noqa: BLE001 - reported, never raised
                _logger.exception(
                    'Could not tell the backend that warehouse %s changed',
                    warehouse.display_name)

    # ------------------------------------------------------------------
    # Admin actions on ONE warehouse (dashboard "manage warehouse" screen)
    # ------------------------------------------------------------------
    def _assert_admin(self):
        """Every action below reshapes a warehouse — admin only."""
        if not (self.env.su or self.env.user.has_group(
                'recycle_warehouse.group_recycle_admin')):
            raise UserError(_('Only the administrator can manage warehouses.'))

    def action_add_zone(self, name, zone_type):
        """Add a zone (area) to THIS warehouse.

        A warehouse starts with one zone of each type (`_ensure_zones`), but a
        real site often needs several — e.g. two storage halls — so extra zones
        of any type are allowed. Only the NAME must stay unique inside the
        warehouse, otherwise operators cannot tell two zones apart.
        """
        self.ensure_one()
        self._assert_admin()
        name = (name or '').strip()
        if not name:
            raise UserError(_('Zone name is required.'))
        if zone_type not in dict(ZONE_TYPES):
            raise UserError(_('Choose a valid zone type.'))
        if any(z.name.strip().lower() == name.lower() for z in self.zone_ids):
            raise UserError(_('A zone with this name already exists in this warehouse.'))
        zone = self.env['recycle.zone'].sudo().create({
            'name': name,
            'zone_type': zone_type,
            'warehouse_id': self.id,
        })
        return zone.id

    def action_delete_zone(self, zone_id):
        """Delete a zone — ONLY when nothing was ever stored in it.

        Stock rows point at the zone, so deleting a zone that holds (or held)
        product would orphan the stock history. The check is on stock ROWS, not
        on quantity: a row with quantity 0 still records that this zone was
        used, and its condition/product pairing is part of the audit trail.
        """
        self.ensure_one()
        self._assert_admin()
        zone = self.zone_ids.filtered(lambda z: z.id == int(zone_id or 0))
        if not zone:
            raise UserError(_('This zone does not belong to this warehouse.'))
        stock_rows = self.env['recycle.stock'].sudo().search_count(
            [('zone_id', '=', zone.id)])
        if stock_rows:
            raise UserError(_(
                'Zone "%s" cannot be deleted: it still holds stock records. '
                'Move or clear its stock first.') % zone.name)
        zone.sudo().unlink()
        return True

    @api.model
    def get_available_managers(self):
        """Managers who are NOT running a warehouse yet — the pool the admin
        picks a replacement from. Includes users whose role is already
        'manager' but who were detached from their warehouse."""
        assigned = self.sudo().search(
            [('manager_user_id', '!=', False)]).mapped('manager_user_id').ids
        users = self.env['res.users'].sudo().search([
            ('recycle_role', '=', 'manager'),
            ('active', '=', True),
            ('id', 'not in', assigned),
        ], order='name')
        return [{'id': u.id, 'name': u.name, 'login': u.login} for u in users]

    def action_change_manager(self, user_id):
        """Hand this warehouse to another manager.

        The OUTGOING manager keeps his `manager` role (he is still a warehouse
        manager by profession and can be assigned elsewhere) but is detached
        from this warehouse — `recycle_warehouse_id` is cleared, which is what
        every manager screen scopes on, so his dashboard no longer opens this
        warehouse's data.
        """
        self.ensure_one()
        self._assert_admin()
        new_manager = self.env['res.users'].sudo().browse(
            int(user_id or 0)).exists()
        if not new_manager:
            raise UserError(_('Choose the new manager.'))
        if new_manager.id == self.manager_user_id.id:
            raise UserError(_('This user already manages this warehouse.'))
        other = self.sudo().search([
            ('manager_user_id', '=', new_manager.id), ('id', '!=', self.id)], limit=1)
        if other:
            raise UserError(_(
                'This user already manages warehouse "%s".') % other.name)

        outgoing = self.manager_user_id
        self.sudo().write({'manager_user_id': new_manager.id})
        # Role stays 'manager'; only the warehouse link is cut.
        if outgoing and outgoing.id != new_manager.id:
            outgoing.sudo().write({'recycle_warehouse_id': False})
        self._sync_manager()
        return True

    # ------------------------------------------------------------------
    # Deactivation lifecycle: active → closing → inactive
    # ------------------------------------------------------------------
    # A shipment still occupying the floor. Anything not finished ('sorted')
    # or dropped ('rejected') is mid-workflow (reception / sorting / escalated).
    IN_PROCESS_SHIPMENT_STATES = [
        'pending', 'receiving', 'escalated', 'accepted',
        'sorting', 'pending_sorting_approval',
    ]

    def action_start_closing(self):
        """Begin shutting the warehouse down.

        Refused while ANY shipment is still being processed — closing then would
        strand it with no team to finish it. Once accepted, the warehouse stops
        being offered anywhere, its team is released and its trucks are freed.
        """
        self.ensure_one()
        self._assert_admin()
        if self.state != 'active':
            raise UserError(_('Only an active warehouse can start closing.'))

        in_process = self.env['recycle.shipment'].sudo().search_count([
            ('warehouse_id', '=', self.id),
            ('state', 'in', self.IN_PROCESS_SHIPMENT_STATES),
        ])
        if in_process:
            raise UserError(_(
                'Cannot start closing: %d shipment(s) are still being processed '
                '(reception / sorting). Finish or move them first.') % in_process)

        self.sudo().write({
            'state': 'closing',
            'closing_started_at': fields.Datetime.now(),
        })
        released_emps = self._release_employees_on_closing()
        freed, held = self._release_trucks_on_closing()
        self.message_post(body=_(
            'Closing started. %d employee(s) released, %d truck(s) freed, '
            '%d still held by a driver (pending hand-back).'
        ) % (released_emps, freed, held))
        return {'employees_released': released_emps,
                'trucks_freed': freed, 'trucks_held': held}

    def _release_employees_on_closing(self):
        """Detach the team: each employee KEEPS his account and his role, but
        loses this warehouse — a new posting is a deliberate manual decision by
        an admin (same rule as restoring an archived employee). Every release is
        written to the employee-history log for the audit trail."""
        self.ensure_one()
        History = self.env['recycle.employee.history'].sudo()
        employees = self.env['res.users'].sudo().search([
            ('recycle_warehouse_id', '=', self.id),
            ('active', '=', True),
        ])
        count = 0
        for user in employees:
            try:
                History.log_change(
                    user, 'assignment_end',
                    old_warehouse=self.name, new_warehouse='',
                    changed_by=self.env.user,
                    note=_('Released because the warehouse was closed'),
                    assignment_end_date=fields.Datetime.now())
            except Exception:
                # Logging must never block the shutdown.
                pass
            # Role stays; only the warehouse link is cut.
            user.write({'recycle_warehouse_id': False})
            count += 1
        return count

    def _release_trucks_on_closing(self):
        """Free the fleet.

        A truck NOT in a driver's hands is unassigned immediately (it becomes
        available for another warehouse). A truck currently held (an OPEN
        handover) is left assigned on purpose — the driver is still physically
        responsible for it; the manager is alerted to have it handed back, and
        `_unassign_if_warehouse_closing` releases it the moment it is returned.
        """
        self.ensure_one()
        Handover = self.env['recycle.truck.handover'].sudo()
        trucks = self.env['recycle.truck'].sudo().search(
            [('warehouse_id', '=', self.id)])
        freed = held = 0
        for truck in trucks:
            open_handover = Handover.search_count([
                ('truck_id', '=', truck.id), ('state', '=', 'open')])
            if open_handover:
                held += 1
                continue
            truck.write({'warehouse_id': False})
            freed += 1
        if held:
            try:
                self.env['recycle.notification'].sudo()._notify_admins(
                    _('Trucks pending hand-back'),
                    _('%d truck(s) of warehouse "%s" are still held by drivers. '
                      'They will be released automatically once handed back.')
                    % (held, self.name))
            except Exception:
                pass
        return freed, held

    @api.model
    def notify_complaint(self, warehouse_id, kind, description, order_number=''):
        """Tell a warehouse's manager that a buyer complained about one of its
        parts — a shortage or a quality problem, called in from the backend.

        These are decided HERE, not on the platform, because the evidence is
        here: the zone-movement log records exactly what left, from which zone,
        deducted by whom and when. A manager with no complaint in front of them
        cannot go and check it. A warehouse with no manager returns quietly —
        there is nobody to tell, and that is a state, not an error.
        """
        wh = self.sudo().browse(int(warehouse_id or 0))
        if not wh.exists() or not wh.manager_user_id:
            return {'notified': False}
        self.env['recycle.notification'].sudo()._notify_user(
            wh.manager_user_id,
            _('New order complaint'),
            _('A %(kind)s complaint on order %(order)s: %(desc)s') % {
                'kind': (kind or '').replace('_', ' ').title() or _('general'),
                'order': order_number or _('(unknown)'),
                'desc': description or '',
            },
            notif_type='order_complaint',
        )
        return {'notified': True}

    @api.model
    def _unassign_if_warehouse_closing(self, truck):
        """Called after a truck is handed back: if its warehouse is no longer
        active, release the truck so it can be re-assigned elsewhere."""
        if truck and truck.warehouse_id and truck.warehouse_id.state != 'active':
            truck.sudo().write({'warehouse_id': False})

    def action_finalize_inactive(self):
        """Final stop — only from `closing`, and only once the warehouse is
        empty. Any remaining stock must be shipped out first, otherwise it would
        be frozen in a warehouse nobody operates."""
        self.ensure_one()
        self._assert_admin()
        if self.state != 'closing':
            raise UserError(_(
                'Only a warehouse that is already closing can be stopped.'))

        remaining = self.env['recycle.stock'].sudo().search_count([
            ('warehouse_id', '=', self.id), ('quantity', '>', 0),
        ])
        if remaining:
            raise UserError(_(
                'Cannot stop the warehouse: %d stock line(s) still hold '
                'quantity. Ship the remaining stock out first.') % remaining)

        self.sudo().write({
            'state': 'inactive',
            'closed_at': fields.Datetime.now(),
            'active': False,          # archived — kept for history, never deleted
        })
        self.message_post(body=_('Warehouse stopped permanently.'))
        return True

    # ------------------------------------------------------------------
    # Coming back: cancel a closing, or reopen a stopped warehouse
    # ------------------------------------------------------------------
    # THE RULE FOR BOTH: nothing is re-attached automatically.
    #
    # Closing and reopening can be months apart. In that time the released
    # employees and trucks may well have been posted to OTHER warehouses.
    # Re-linking them from history would create contradictions — an employee
    # belonging to two warehouses, or a truck yanked away from the site that is
    # actually using it today. So reopening only makes the warehouse SELECTABLE
    # again; staffing it is a fresh, deliberate decision, exactly like a brand
    # new warehouse. For the same reason neither action calls
    # `_release_employees_on_closing` / `_release_trucks_on_closing`: those
    # belong to the shutdown path and have no meaningful inverse.

    def action_cancel_closing(self):
        """Undo a closing that was started by mistake (only while `closing`).

        The warehouse never fully stopped, so it simply becomes selectable
        again. Employees released when the closing began are NOT restored.
        """
        self.ensure_one()
        self._assert_admin()
        if self.state != 'closing':
            raise UserError(_(
                'Cannot cancel: this warehouse is not currently closing.'))
        self.sudo().write({'state': 'active', 'closing_started_at': False})
        self.message_post(body=_(
            'Closing cancelled — the warehouse is active again. No employee or '
            'truck was re-assigned automatically.'))
        return True

    def action_reopen_warehouse(self):
        """Bring a fully stopped (`inactive`) warehouse back into service.

        Restores the record itself — same id, same history — and un-archives it
        so it reappears in every selection list. Its old team and fleet are NOT
        restored (see the note above).
        """
        self.ensure_one()
        self._assert_admin()
        if self.state != 'inactive':
            raise UserError(_(
                'This warehouse is not stopped, so it cannot be reopened.'))
        self.sudo().write({
            'state': 'active',
            'active': True,       # un-archive: visible again everywhere
            'closed_at': False,
            'closing_started_at': False,
        })
        self.message_post(body=_(
            'Warehouse reopened. No employee or truck was re-assigned '
            'automatically — assign resources manually.'))
        return True

    # Backwards-compatible alias: the dashboard used to call `action_reopen`
    # while the only reopenable state was `closing`.
    def action_reopen(self):
        self.ensure_one()
        return (self.action_cancel_closing() if self.state == 'closing'
                else self.action_reopen_warehouse())

    def unlink(self):
        """A warehouse is never deleted: shipments, employees, trucks and
        attendance all reference it, and that history must survive. Shutting one
        down goes through the closing lifecycle instead."""
        raise UserError(_(
            'A warehouse cannot be deleted. Use "Close warehouse" instead so '
            'its full history is preserved.'))

    def action_update_info(self, vals):
        """Edit the warehouse's own details (name / code / address / …).

        Whitelisted so a dashboard call can never reach sensitive relational
        fields (manager, zones, employees) — those have dedicated actions with
        their own rules.
        """
        self.ensure_one()
        self._assert_admin()
        allowed = {'name', 'code', 'address', 'province_id', 'latitude',
                   'longitude', 'active', 'capacity'}
        clean = {k: v for k, v in (vals or {}).items() if k in allowed}
        if not clean:
            raise UserError(_('Nothing to update.'))
        for key in ('name', 'code'):
            if key in clean:
                clean[key] = (clean[key] or '').strip()
                if not clean[key]:
                    raise UserError(_('Name and code cannot be empty.'))
        if 'province_id' in clean:
            # The dashboard <select> hands back a string id (or '' for "none").
            clean['province_id'] = int(clean['province_id']) or False \
                if str(clean['province_id'] or '').strip() else False
        self.write(clean)
        return True


class RecycleZone(models.Model):
    _name = 'recycle.zone'
    _description = 'Warehouse Zone'
    _order = 'warehouse_id, zone_type'

    name = fields.Char(required=True)
    zone_type = fields.Selection(ZONE_TYPES, required=True, default='storage')
    warehouse_id = fields.Many2one(
        'recycle.warehouse', required=True, ondelete='cascade', index=True)


class ResUsers(models.Model):
    _inherit = 'res.users'

    recycle_warehouse_id = fields.Many2one(
        'recycle.warehouse', string='Recycle Warehouse', index=True)
    recycle_role = fields.Selection([
        ('admin', 'Administration'),
        ('manager', 'Warehouse Manager'),
        ('input', 'Input Employee'),
        ('sorting', 'Sorting Employee'),
        ('output', 'Output Employee'),
        ('delivery_driver', 'Delivery Driver'),
    ], string='Recycle Role')
    # The delivery-driver record behind this login, if any.
    #
    # Declared so a record rule can say `user.recycle_delivery_driver_ids.truck_id`
    # instead of running a search inside its domain: a rule is evaluated on every
    # read of the model it guards, and one that queries has to be right about
    # both access and performance every time it fires.
    recycle_delivery_driver_ids = fields.One2many(
        'recycle.delivery.driver', 'user_id', string='Delivery Driver Record')
    recycle_national_id = fields.Char(string='National ID', index=True)
    recycle_avatar_custom = fields.Boolean(
        string='Custom Profile Photo', default=False, copy=False,
        help='True only after the user uploads a real profile photo from the '
             'website. While False the UI shows a first-letter avatar instead '
             'of any stock/default Odoo image.')
    shift_id = fields.Many2one(
        'recycle.shift', string='Work Shift',
        domain=[('active', '=', True), ('shift_type', '=', 'warehouse')],
        help='Assigned work shift for attendance tracking')

    @api.constrains('shift_id')
    def _check_shift_is_warehouse_type(self):
        """Warehouse employees may only take warehouse shifts — driver
        shifts belong exclusively to collectors (recycle.driver.assignment)."""
        for user in self:
            if user.shift_id and user.shift_id.shift_type != 'warehouse':
                raise ValidationError(_(
                    'Shift "%s" is reserved for drivers and cannot be '
                    'assigned to a warehouse employee.') % user.shift_id.name)
    recycle_performance_rating = fields.Integer(
        string='Performance Rating', default=0,
        help='1-5 star rating set by the warehouse manager, indicating this '
             'employee\'s performance/efficiency. 0 = not rated yet.')
    recycle_performance_rated_by = fields.Many2one(
        'res.users', string='Rated By', readonly=True, copy=False)
    recycle_performance_rated_at = fields.Datetime(
        string='Rated At', readonly=True, copy=False)

    # ── Login brute-force lockout (escalating: 1min -> 2min -> 24h) ──
    recycle_failed_login_count = fields.Integer(
        string='Failed Login Attempts', default=0, copy=False,
        help='Consecutive failed login attempts since the last lockout '
             'expired. Resets to 0 on a successful login or once it '
             'triggers the next lockout stage.')
    recycle_lockout_stage = fields.Integer(
        string='Lockout Stage', default=0, copy=False,
        help='0 = never locked. 1/2/3 = the escalating lockout stage last '
             'triggered (1 min / 2 min / 24h). Only resets to 0 on a '
             'successful login.')
    recycle_locked_until = fields.Datetime(
        string='Locked Until', copy=False,
        help='Login is blocked for this account until this timestamp, '
             'regardless of whether the password given is correct.')

    @api.constrains('recycle_performance_rating')
    def _check_recycle_performance_rating(self):
        for user in self:
            if not (0 <= user.recycle_performance_rating <= 5):
                raise ValidationError(_('Performance rating must be between 0 and 5 stars.'))

    # ── Soft-delete (employees): the account is archived but restorable ──
    recycle_deleted = fields.Boolean(
        string='Employee Deleted', default=False, copy=False,
        help='Soft-deleted employee account. Archived but restorable by an '
             'administrator until it is permanently deleted.')
    recycle_deleted_date = fields.Datetime(
        string='Deletion Date', copy=False, readonly=True)
    recycle_delete_reason = fields.Char(
        string='Deletion Reason', copy=False)
    # Remembered assignment at archive time (for admins reviewing / restoring).
    recycle_prev_warehouse_id = fields.Many2one(
        'recycle.warehouse', string='Previous Warehouse', copy=False,
        help='Warehouse this archived employee was assigned to or managed '
             'before archiving. Kept for reference; the live assignment is '
             'removed on archive.')
    recycle_prev_managed = fields.Boolean(
        string='Was Warehouse Manager', copy=False)
    recycle_prev_role = fields.Selection([
        ('admin', 'Administration'),
        ('manager', 'Warehouse Manager'),
        ('input', 'Input Employee'),
        ('sorting', 'Sorting Employee'),
        ('output', 'Output Employee'),
    ], string='Previous Role', copy=False,
        help='Role this employee held before archiving — kept for review '
             'so the admin can see what the archived employee was assigned.')

    # ── Ban (website / portal accounts): login blocked, account kept ──
    recycle_banned = fields.Boolean(
        string='Account Banned', default=False, copy=False,
        help='Banned website account. The user is blocked from logging in but '
             'the account is kept until deleted or unbanned.')
    recycle_banned_date = fields.Datetime(
        string='Ban Date', copy=False, readonly=True)
    recycle_ban_reason = fields.Char(
        string='Ban Reason', copy=False)

    # ------------------------------------------------------------------
    # Uniqueness rules (system-wide: users AND employees)
    # ------------------------------------------------------------------
    def _assert_identity_free(self):
        """Run the system-wide identity check for these users.

        Called from create/write rather than left to @api.constrains alone:
        `email` is a DELEGATED field (res.users inherits res.partner), and a
        constraint declared on a delegated field does not reliably fire — so the
        email half of the rule silently did nothing. The national-id half kept
        working, which is exactly what made the gap hard to notice.
        """
        Guard = self.env['recycle.identity.guard']
        for user in self:
            # Checks AND claims. The search alone can be beaten by a request
            # arriving between it and the write; the claim is a row behind a
            # UNIQUE index, so a concurrent duplicate is refused by the database
            # rather than by luck.
            Guard.register_identity(
                'res.users', user.id,
                national_id=user.recycle_national_id, email=user.email)

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users._assert_identity_free()
        return users

    def unlink(self):
        """Give the identities back before the account goes."""
        Guard = self.env['recycle.identity.guard']
        for user in self:
            Guard.release_identity('res.users', user.id)
        return super().unlink()

    def write(self, vals):
        res = super().write(vals)
        if {'recycle_national_id', 'email', 'login'} & set(vals):
            self._assert_identity_free()
        return res

    @api.constrains('recycle_national_id')
    def _check_recycle_identity_unique(self):
        """Unique across EVERY person, not just among users.

        The old pair of checks only looked inside `res.users`, so the same human
        could be an applicant, an employee and a delivery driver at once — three
        records, three histories, three sets of documents, and no way to tell
        which one is the person. A national ID identifies a human being, not a
        row in one table.
        """
        Guard = self.env['recycle.identity.guard']
        for user in self:
            Guard.assert_unique_identity(
                national_id=user.recycle_national_id,
                email=user.email,
                exclude_model='res.users', exclude_ids=[user.id])

    # ------------------------------------------------------------------
    # Login gate: banned users cannot authenticate.
    # ------------------------------------------------------------------
    def _check_credentials(self, *args, **kwargs):
        res = super()._check_credentials(*args, **kwargs)
        for user in self:
            if user.sudo().recycle_banned:
                raise AccessDenied(_(
                    'Your account has been banned. Please contact the '
                    'administration for more information.'))
        return res

    def _get_session_token_fields(self):
        """Include the ban and deleted flags in the session-token fingerprint
        so that banning or archiving a user immediately invalidates every
        session they hold — they are logged out on their very next request."""
        return super()._get_session_token_fields() | {'recycle_banned', 'recycle_deleted'}

    # ------------------------------------------------------------------
    # Soft-delete / restore (employees)
    # ------------------------------------------------------------------
    def _recycle_admin_guard(self):
        if not self.env.user.has_group('recycle_warehouse.group_recycle_admin'):
            raise UserError(_('Only administrators can manage employee accounts.'))

    def action_recycle_soft_delete(self, reason=None):
        """Archive the employee account (restorable). Keeps the user row, HR
        record, applications, shipments and orders intact — nothing is purged.

        Archiving STRIPS every live assignment (warehouse, work shift, and the
        warehouse-manager link) so the person can no longer perform any task,
        while their ROLE is kept. The previous warehouse is remembered so the
        admin knows what they were assigned to / managed."""
        self.ensure_one()
        self._recycle_admin_guard()
        # Remember what they were assigned to / managed before stripping it.
        managed = self.env['recycle.warehouse'].sudo().search(
            [('manager_user_id', '=', self.id)], limit=1)
        prev_wh = managed or self.recycle_warehouse_id
        prev_role = self.recycle_role
        now = fields.Datetime.now()

        # Log assignment end + archive in history
        role_labels = {
            'admin': 'Administration', 'manager': 'Warehouse Manager',
            'input': 'Input Employee', 'sorting': 'Sorting Employee',
            'output': 'Output Employee',
        }
        History = self.env['recycle.employee.history'].sudo()
        if prev_role or prev_wh:
            # Find the last assignment_start record to get the start date
            last_start = History.search([
                ('user_id', '=', self.id),
                ('change_type', '=', 'assignment_start'),
            ], limit=1, order='create_date desc')
            History.log_change(
                self, 'assignment_end',
                old_role=role_labels.get(prev_role, prev_role or 'Not Assigned'),
                old_warehouse=prev_wh.name if prev_wh else 'None',
                changed_by=self.env.user,
                assignment_start_date=last_start.create_date if last_start else False,
                assignment_end_date=now,
                note='Employee archived' + (': %s' % reason if reason else ''))

        # Free any warehouse this person managed (keep the warehouse itself).
        self.env['recycle.warehouse'].sudo().search(
            [('manager_user_id', '=', self.id)]).write({'manager_user_id': False})
        self.sudo().write({
            'recycle_deleted': True,
            'recycle_deleted_date': now,
            'recycle_delete_reason': (reason or '').strip() or False,
            'recycle_prev_warehouse_id': prev_wh.id if prev_wh else False,
            'recycle_prev_managed': bool(managed),
            'recycle_prev_role': prev_role or False,
            # Strip EVERY live assignment — role AND warehouse are removed
            # (kept in recycle_prev_* for review of what they held).
            'recycle_role': False,
            'recycle_warehouse_id': False,
            'shift_id': False,
            'active': False,
        })
        # Archive the linked HR employee too (kept, restorable).
        self.env['hr.employee'].sudo().with_context(active_test=False).search(
            [('user_id', '=', self.id)]).write({'active': False})
        return True

    def action_recycle_restore(self):
        """Reactivate an archived employee account. The account comes back
        WITHOUT its old role/warehouse/shift — the admin re-assigns them.
        The recycle_prev_* fields are kept so the admin can review what
        the employee held before archiving."""
        self.ensure_one()
        self._recycle_admin_guard()

        # Log restore in history
        self.env['recycle.employee.history'].sudo().log_change(
            self, 'restore',
            old_role=self.recycle_prev_role or False,
            old_warehouse=self.recycle_prev_warehouse_id.name if self.recycle_prev_warehouse_id else False,
            changed_by=self.env.user,
            note='Employee restored from archive')

        self.sudo().write({
            'recycle_deleted': False,
            'recycle_deleted_date': False,
            'recycle_delete_reason': False,
            'active': True,
            # Role, warehouse, shift are intentionally NOT restored.
            # Admin must re-assign them manually.
        })
        self.env['hr.employee'].sudo().with_context(active_test=False).search(
            [('user_id', '=', self.id)]).write({'active': True})
        return True

    def action_recycle_restore_and_notify(self):
        """Restore an archived employee AND send them a notification + email.
        Used from both the archived-employees list and the notifications view."""
        self.ensure_one()
        self._recycle_admin_guard()
        user = self
        # Determine language
        partner_lang = getattr(user.sudo().partner_id, 'lang', '') or ''
        is_ar = str(partner_lang)[:2] == 'ar'

        # Restore the account
        user.action_recycle_restore()

        # In-app notification
        Notif = self.env['recycle.notification'].sudo()
        if is_ar:
            title = 'تمت استعادة الحساب'
            msg = 'تم استعادة حسابك بنجاح. يمكنك الآن تسجيل الدخول مرة أخرى.'
        else:
            title = 'Account Reactivated'
            msg = ('Your account has been successfully restored. '
                   'You can now log in again.')
        Notif._notify_user(user, title, msg, 'decision')

        # Email
        if is_ar:
            email_subject = 'Dawrha — تمت استعادة حسابك'
            email_body = """
            <div style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:auto;
                        background:#ffffff;border-radius:16px;overflow:hidden;
                        border:1px solid #e2e8f0;">
                <div style="background:linear-gradient(135deg,#047857,#10b981);
                            padding:24px 28px;color:#fff;">
                    <div style="font-size:24px;font-weight:900;">Dawrha</div>
                    <div style="opacity:.9;font-size:14px;margin-top:2px;">تمت استعادة الحساب</div>
                </div>
                <div style="padding:28px;">
                    <p style="font-size:16px;color:#0f172a;margin:0 0 14px;">%s،</p>
                    <p style="font-size:15px;color:#334155;line-height:1.8;margin:0 0 20px;">
                        تم استعادة حسابك بنجاح. يمكنك الآن تسجيل الدخول مرة أخرى والعودة إلى العمل.
                    </p>
                    <div style="text-align:center;margin:24px 0;">
                        <a href="/web/login" style="display:inline-block;background:linear-gradient(135deg,#047857,#10b981);
                            color:#fff;text-decoration:none;padding:12px 32px;border-radius:8px;
                            font-weight:600;font-size:15px;">تسجيل الدخول</a>
                    </div>
                    <p style="font-size:13px;color:#94a3b8;margin-top:18px;">— فريق Dawrha</p>
                </div>
            </div>
            """ % _esc(user.name or 'المستخدم')
        else:
            email_subject = 'Dawrha — Your Account Has Been Restored'
            email_body = """
            <div style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:auto;
                        background:#ffffff;border-radius:16px;overflow:hidden;
                        border:1px solid #e2e8f0;">
                <div style="background:linear-gradient(135deg,#047857,#10b981);
                            padding:24px 28px;color:#fff;">
                    <div style="font-size:24px;font-weight:900;">Dawrha</div>
                    <div style="opacity:.9;font-size:14px;margin-top:2px;">Account Reactivated</div>
                </div>
                <div style="padding:28px;">
                    <p style="font-size:16px;color:#0f172a;margin:0 0 14px;">Dear %s,</p>
                    <p style="font-size:15px;color:#334155;line-height:1.8;margin:0 0 20px;">
                        Your account has been successfully restored. You can now log in again and resume your work.
                    </p>
                    <div style="text-align:center;margin:24px 0;">
                        <a href="/web/login" style="display:inline-block;background:linear-gradient(135deg,#047857,#10b981);
                            color:#fff;text-decoration:none;padding:12px 32px;border-radius:8px;
                            font-weight:600;font-size:15px;">Log In</a>
                    </div>
                    <p style="font-size:13px;color:#94a3b8;margin-top:18px;">— The Dawrha Team</p>
                </div>
            </div>
            """ % _esc(user.name or 'User')
        Notif._send_email_to_user(user, email_subject, email_body)
        return True

    def action_recycle_reject_and_notify(self):
        """Reject an archived employee's reactivation request: keep them
        archived AND send them a notification + email explaining the rejection."""
        self.ensure_one()
        self._recycle_admin_guard()
        user = self
        # Determine language
        partner_lang = getattr(user.sudo().partner_id, 'lang', '') or ''
        is_ar = str(partner_lang)[:2] == 'ar'

        # Mark any pending reactivation request as done
        Notif = self.env['recycle.notification'].sudo()
        pending = Notif.search([
            ('notif_type', '=', 'reactivation'),
            ('request_user_id', '=', user.id),
            ('state', '=', 'pending'),
        ])
        if pending:
            pending.write({'state': 'done', 'is_read': True})

        # In-app notification
        if is_ar:
            title = 'تم رفض طلب استعادة الحساب'
            msg = ('لم يتم استعادة حسابك بسبب السياسات الأمنية للمؤسسة. '
                   'يرجى التواصل مع قسم الموارد البشرية للمزيد من المعلومات.')
        else:
            title = 'Reactivation Request Declined'
            msg = ('Your account restoration request has been declined '
                   'due to the organization\'s security policies. '
                   'Please contact the HR department for more information.')
        Notif._notify_user(user, title, msg, 'decision')

        # Email
        if is_ar:
            email_subject = 'Dawrha — رفض طلب استعادة الحساب'
            email_body = """
            <div style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:auto;
                        background:#ffffff;border-radius:16px;overflow:hidden;
                        border:1px solid #e2e8f0;">
                <div style="background:linear-gradient(135deg,#047857,#10b981);
                            padding:24px 28px;color:#fff;">
                    <div style="font-size:24px;font-weight:900;">Dawrha</div>
                    <div style="opacity:.9;font-size:14px;margin-top:2px;">رفض طلب استعادة الحساب</div>
                </div>
                <div style="padding:28px;">
                    <p style="font-size:16px;color:#0f172a;margin:0 0 14px;">%s،</p>
                    <p style="font-size:15px;color:#334155;line-height:1.8;margin:0 0 20px;">
                        لم يتم استعادة حسابك بسبب السياسات الأمنية للمؤسسة.
                        يرجى التواصل مع قسم الموارد البشرية للمزيد من المعلومات.
                    </p>
                    <p style="font-size:13px;color:#94a3b8;margin-top:18px;">— فريق Dawrha</p>
                </div>
            </div>
            """ % _esc(user.name or 'المستخدم')
        else:
            email_subject = 'Dawrha — Reactivation Request Declined'
            email_body = """
            <div style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:auto;
                        background:#ffffff;border-radius:16px;overflow:hidden;
                        border:1px solid #e2e8f0;">
                <div style="background:linear-gradient(135deg,#047857,#10b981);
                            padding:24px 28px;color:#fff;">
                    <div style="font-size:24px;font-weight:900;">Dawrha</div>
                    <div style="opacity:.9;font-size:14px;margin-top:2px;">Reactivation Request Declined</div>
                </div>
                <div style="padding:28px;">
                    <p style="font-size:16px;color:#0f172a;margin:0 0 14px;">Dear %s,</p>
                    <p style="font-size:15px;color:#334155;line-height:1.8;margin:0 0 20px;">
                        Your account restoration request has been declined due to the
                        organization's security policies. Please contact the HR department
                        for more information.
                    </p>
                    <p style="font-size:13px;color:#94a3b8;margin-top:18px;">— The Dawrha Team</p>
                </div>
            </div>
            """ % _esc(user.name or 'User')
        Notif._send_email_to_user(user, email_subject, email_body)
        return True

    # ------------------------------------------------------------------
    # Reactivation request (archived employee tries to log in)
    # ------------------------------------------------------------------
    def _recycle_request_reactivation(self, employee_msg=None):
        """Create a pending reactivation request + notify administrators.
        Deduplicated: one open request per user at a time.

        If employee_msg is provided, the admin notification will show the
        same message the employee sees (so both sides see identical text)."""
        self.ensure_one()
        Notif = self.env['recycle.notification'].sudo()
        existing = Notif.search([
            ('notif_type', '=', 'reactivation'),
            ('request_user_id', '=', self.id),
            ('state', '=', 'pending'),
        ], limit=1)
        if existing:
            return existing
        # Determine language: prefer partner's lang, fall back to context, then 'en'.
        partner_lang = getattr(self.sudo().partner_id, 'lang', '') or ''
        ctx_lang = str(self.env.context.get('lang', '')) or ''
        lang = (partner_lang or ctx_lang or 'en')[:2]
        is_ar = lang == 'ar'
        if employee_msg:
            # Use the exact same message the employee sees
            title = 'طلب استعادة حساب' if is_ar else 'Account Reactivation Request'
            msg = employee_msg
        else:
            if is_ar:
                title = 'طلب استعادة حساب'
                msg = ('%s (%s) حاول تسجيل الدخول بحساب مؤرشف. '
                       'يرجى مراجعة الطلب والقرار: استعادة أو رفض.') % (self.name, self.login)
            else:
                title = 'Account Reactivation Request'
                msg = ('%s (%s) attempted to log in with an archived account. '
                       'Please review the request and decide: restore or reject.') % (self.name, self.login)
        return Notif._notify_admins(
            title, msg,
            notif_type='reactivation', request_user=self,
            state='pending', related_model='res.users',
            related_res_id=self.id)

    # ------------------------------------------------------------------
    # Ban / unban (website portal accounts)
    # ------------------------------------------------------------------
    def action_recycle_ban(self, reason=None):
        """Ban a website account: block login immediately and terminate any
        active sessions the user currently holds."""
        self.ensure_one()
        self._recycle_admin_guard()
        self.sudo().write({
            'recycle_banned': True,
            'recycle_banned_date': fields.Datetime.now(),
            'recycle_ban_reason': (reason or '').strip() or False,
        })
        # Writing recycle_banned changes the session-token fingerprint (see
        # _get_session_token_fields), so any live session for this user is
        # invalidated automatically on their next request.
        return True

    def action_recycle_unban(self):
        self.ensure_one()
        self._recycle_admin_guard()
        self.sudo().write({
            'recycle_banned': False,
            'recycle_banned_date': False,
            'recycle_ban_reason': False,
        })
        return True

    def write(self, vals):
        res = super().write(vals)
        if 'recycle_national_id' in vals:
            nid = vals.get('recycle_national_id')
            for user in self:
                email = (user.email or user.login or '').strip().lower()
                if email:
                    # Only sync live applications — never touch historical
                    # applications belonging to a previously deleted account
                    # (they are read-only and would raise the guard error).
                    self.env['hr.applicant'].sudo().search([
                        ('recycle_email', '=', email),
                        ('recycle_account_deleted', '!=', True),
                    ]).write({'recycle_national_id': nid or False})
        return res

    def _recycle_free_login(self):
        """Rename the login so the original email can be reused for a new account."""
        import time as _time
        self.sudo().write({
            'login': 'deleted_%s_%d' % (self.id, int(_time.time())),
        })

    def unlink(self):
        for user in self:
            user._recycle_free_login()
        return super().unlink()

    def _recycle_purge(self):
        """Admin tool: permanently delete an employee account while keeping
        their job applications (read-only), shipments, and orders intact.

        The user is fully deleted (the login is freed first so the email can
        be reused). Related records that point to this user (shipments, orders)
        use ondelete='set null' so they keep their data with a NULL reference."""
        self.ensure_one()
        self = self.with_context(
            tracking_disable=True, mail_activity_skip=True, mail_notrack=True,
            mail_channel_skip=True)
        env = self.env
        uid = self.id
        name = self.name
        email = (self.email or self.login or '').strip().lower()

        # Detach as a warehouse manager (keep the warehouse itself).
        env['recycle.warehouse'].sudo().search(
            [('manager_user_id', '=', uid)]).write({'manager_user_id': False})

        # Mark this person's job applications as account-deleted (keep them
        # for history/display but they become read-only in the dashboard).
        Applicant = env['hr.applicant'].sudo()
        if email:
            apps = Applicant.search([
                '|', ('employee_user_id', '=', uid),
                ('recycle_email', '=ilike', email)])
        else:
            apps = Applicant.search([('employee_user_id', '=', uid)])
        apps.with_context(
            tracking_disable=True, mail_notrack=True,
            recycle_force_delete=True).write({
                'recycle_account_deleted': True,
            })

        # Delete the HR employee record.
        env['hr.employee'].sudo().with_context(
            tracking_disable=True, mail_notrack=True
        ).search([('user_id', '=', uid)]).unlink()

        # Permanently delete the user from res_users only (not res_partner).
        # This removes login capability and frees the email, while keeping the
        # partner record intact so existing shipments/orders still display the
        # person's name. Odoo's ORM unlink() would trigger UI dialogs, so we
        # bypass it with raw SQL.
        self.sudo()._recycle_free_login()
        self.env.cr.execute("DELETE FROM res_users WHERE id = %s", [uid])
        return name

    def action_recycle_purge_employee(self):
        """Callable from the admin Employees board (checks admin rights)."""
        self.ensure_one()
        if not self.env.user.has_group('recycle_warehouse.group_recycle_admin'):
            raise UserError(_('Only administrators can delete employees.'))
        return self._recycle_purge()

    def action_recycle_delete_account(self):
        """Permanently delete a website (portal) account from Odoo.

        Unlike the employee purge — which uses raw SQL to keep the partner so
        historical shipments/orders still show a name — a website visitor has
        no operational history to preserve, so we delete the account through
        the ORM. The ORM respects each foreign key's ondelete rule, which is
        why it succeeds where the raw-SQL DELETE hit constraint violations
        ('Odoo Server Error')."""
        self.ensure_one()
        self._recycle_admin_guard()
        user = self.sudo().with_context(
            tracking_disable=True, mail_notrack=True)
        uid = user.id
        name = user.name
        email = (user.email or user.login or '').strip().lower()

        # Detach as a warehouse manager (keep the warehouse itself).
        self.env['recycle.warehouse'].sudo().search(
            [('manager_user_id', '=', uid)]).write({'manager_user_id': False})

        # Remove this person's job applications (a visitor has no history to
        # keep). recycle_force_delete bypasses the read-only guard.
        Applicant = self.env['hr.applicant'].sudo()
        if email:
            apps = Applicant.search([
                '|', ('employee_user_id', '=', uid),
                ('recycle_email', '=ilike', email)])
        else:
            apps = Applicant.search([('employee_user_id', '=', uid)])
        apps.with_context(
            recycle_force_delete=True, tracking_disable=True,
            mail_notrack=True).unlink()

        # Remove any HR employee record.
        self.env['hr.employee'].sudo().with_context(active_test=False).search(
            [('user_id', '=', uid)]).unlink()

        # Free the login (so the email can be reused) and delete via the ORM.
        user._recycle_free_login()
        user.with_context(recycle_force_delete=True).unlink()

    def _notify_security_setting_update(self, subject, content, mail_values=None, **kwargs):
        """Odoo's native security-change email (login/password/email changed)
        uses the generic 'Powered by Odoo' layout. Replace it with the same
        branded card every other Dawrha email uses (OTP, interview, decision,
        set-password) so the whole system has one consistent look — sent
        directly here instead of through mail.account_security_alert so no
        second, differently-styled email goes out for the same event."""
        reset_url = '%s/web/reset_password' % self.get_base_url()
        mail_create_values = []
        for user in self:
            # user.name is editable by the account owner — escape before
            # splicing into HTML so a crafted display name can't inject
            # markup into their own security-alert email.
            greeting = _esc(user.name or user.login or '')
            reset_html = ''
            if kwargs.get('suggest_password_reset', True):
                reset_html = f"""
                <p style="font-size:14px;color:#334155;line-height:1.6;margin:18px 0 0;">
                    If this wasn't you, please reset your password immediately:
                </p>
                <div style="text-align:center;margin:18px 0 0;">
                    <a href="{reset_url}"
                       style="display:inline-block;background:linear-gradient(135deg,#047857,#10b981);
                              color:#ffffff;text-decoration:none;font-size:15px;font-weight:700;
                              padding:12px 32px;border-radius:10px;letter-spacing:0.3px;">
                        Reset Password
                    </a>
                </div>
                """
            body_html = f"""
            <div style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:auto;
                        background:#ffffff;border-radius:16px;overflow:hidden;
                        border:1px solid #e2e8f0;">
                <div style="background:linear-gradient(135deg,#047857,#10b981);
                            padding:24px 28px;color:#fff;">
                    <div style="font-size:24px;font-weight:900;">Dawrha</div>
                    <div style="opacity:.9;font-size:14px;margin-top:2px;">{subject}</div>
                </div>
                <div style="padding:28px;">
                    <p style="font-size:16px;color:#0f172a;margin:0 0 14px;">
                        Dear {greeting},
                    </p>
                    <p style="font-size:15px;color:#334155;line-height:1.6;margin:0 0 8px;">
                        {content}
                    </p>
                    {reset_html}
                    <p style="font-size:13px;color:#94a3b8;line-height:1.6;margin-top:24px;">
                        If you did not expect this change, please contact your
                        warehouse manager or administrator.
                    </p>
                    <p style="font-size:13px;color:#94a3b8;margin-top:18px;">— The Dawrha Team</p>
                </div>
            </div>
            """
            vals = {
                'auto_delete': True,
                'body_html': body_html,
                'email_from': (
                    user.company_id.partner_id.email_formatted
                    or self.env.user.email_formatted
                    or self.env.ref('base.user_root').email_formatted
                ),
                'email_to': kwargs.get('force_email') or user.email_formatted,
                'subject': subject,
            }
            if mail_values:
                vals.update(mail_values)
            mail_create_values.append(vals)

        mails = self.env['mail.mail'].sudo().create(mail_create_values)
        try:
            mails.send()
        except Exception:
            _logger.warning('Security notification email failed to send.')
        return mails

    def action_recycle_open_assignment(self):
        """'Assign' button on Recruitment > Unassigned Employees.

        Hands off to the admin dashboard's own Assignment screen via
        context instead of a model view, so the page keeps the dashboard
        theme, sidebar and no-navbar rules already enforced there.
        """
        self.ensure_one()
        if not self.env.user.has_group('recycle_warehouse.group_recycle_admin'):
            raise UserError(_('Only administrators can assign employees.'))
        if self.recycle_role:
            raise UserError(_('%s already has a role assigned.') % self.name)
        return {
            'type': 'ir.actions.client',
            'tag': 'recycle_admin_dashboard',
            'name': _('Assign Employee'),
            'target': 'current',
            'context': {
                'initial_view': 'employee_assignment',
                'employee_id': self.id,
            },
        }
        return name
