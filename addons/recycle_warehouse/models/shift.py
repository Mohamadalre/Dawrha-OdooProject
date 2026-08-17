# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

# ── Shift duration limits (hours) ──
#   Hard bounds enforced by the model: 6h .. 12h.
#   The UI additionally warns for the 9h–12h band (long shift, needs confirm).
MIN_SHIFT_HOURS = 6.0
MAX_SHIFT_HOURS = 12.0
RECOMMENDED_MAX_HOURS = 9.0

# ── Recommended (realistic) shift windows ──
#   (start_min, start_max, end_min, end_max) as decimal hours.
REALISTIC_WINDOWS = {
    'morning':   (6.0, 8.5, 14.0, 16.5),
    'afternoon': (14.0, 16.5, 22.0, 23.5),
    'night':     (22.0, 24.0, 6.0, 8.0),
}


def shift_duration(start, end):
    """Length of a shift in hours, correctly handling overnight shifts
    (e.g. 22:00 → 06:00 = 8h)."""
    d = (end or 0.0) - (start or 0.0)
    if d <= 0:
        d += 24.0
    return round(d, 4)


def is_realistic(start, end):
    """True when the times fall inside one of the recommended windows."""
    for (smin, smax, emin, emax) in REALISTIC_WINDOWS.values():
        if smin <= start <= smax and emin <= end <= emax:
            return True
    return False


class RecycleShift(models.Model):
    _name = 'recycle.shift'
    _description = 'Work Shift'
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char('Shift Name', required=True)
    # Who the shift is meant for — a CONTRACT with the NestJS backend:
    # only 'driver' shifts are offered to collectors during onboarding.
    # Warehouse shifts can never be assigned to drivers and vice versa
    # (enforced by constraints here, on res.users and on
    # recycle.driver.assignment).
    shift_type = fields.Selection([
        ('warehouse', 'Warehouse Staff'),
        ('driver', 'Drivers'),
    ], string='Shift For', default='warehouse', required=True, index=True)
    start_time = fields.Float(
        'Start Time', required=True,
        help='Enter time as decimal (e.g. 8.5 = 08:30, 17.0 = 17:00)')
    end_time = fields.Float(
        'End Time', required=True,
        help='Enter time as decimal (e.g. 17.0 = 17:00)')
    tolerance = fields.Integer(
        'Tolerance (minutes)', default=15,
        help='Grace period allowed for late check-in')
    # ── Scope: a shift is GLOBAL (shown to every warehouse — the ones a new
    # driver picks during onboarding) or SPECIFIC to one or more warehouses.
    is_global = fields.Boolean(
        'Global (all warehouses)', default=False, index=True,
        help='Global shifts appear for every warehouse and are the only ones '
             'a not-yet-accepted driver can pick. A global shift can never '
             'become warehouse-specific again.')
    warehouse_ids = fields.Many2many(
        'recycle.warehouse', relation='recycle_shift_warehouse_rel',
        column1='shift_id', column2='warehouse_id',
        string='Warehouses',
        help='The warehouses a SPECIFIC shift belongs to (empty for a global '
             'shift).')
    # DEPRECATED (kept dormant for the mirror/migration): the single warehouse
    # from before multi-warehouse scoping. Logic now uses is_global +
    # warehouse_ids; this column is only backfilled once and no longer read.
    warehouse_id = fields.Many2one(
        'recycle.warehouse', string='Warehouse (legacy)')
    active = fields.Boolean(default=True)
    employee_count = fields.Integer(
        'Assigned Employees',
        compute='_compute_employee_count')
    duration = fields.Float(
        'Duration (hours)', compute='_compute_duration', store=True,
        digits=(4, 2))
    assigned_employee_names = fields.Char(
        'Assigned To', compute='_compute_assigned_names')

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for rec in self:
            rec.duration = shift_duration(rec.start_time, rec.end_time)

    def _compute_employee_count(self):
        for rec in self:
            rec.employee_count = self.env['res.users'].search_count([
                ('shift_id', '=', rec.id),
                ('active', '=', True),
            ])

    def _assigned_employees(self):
        self.ensure_one()
        return self.env['res.users'].search([
            ('shift_id', '=', self.id), ('active', '=', True),
        ])

    def _compute_assigned_names(self):
        for rec in self:
            rec.assigned_employee_names = ', '.join(
                rec._assigned_employees().mapped('name')) or ''

    # ------------------------------------------------------------------
    # Backend mirror sync — the NestJS backend mirrors shifts (SYNC_FLEET),
    # so any authoring here must ping it (fire-and-forget, never blocks).
    # ------------------------------------------------------------------
    def _ping_backend_fleet(self):
        try:
            self.env['recycle.backend.sync'].sudo().notify_fleet_changed()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Scope (global / warehouse-specific)
    # ------------------------------------------------------------------
    def _normalize_scope(self):
        """Convenience: a SPECIFIC shift that ends up covering EVERY warehouse
        is promoted to GLOBAL (the admin picking all warehouses = "make it
        global", per the spec). Global shifts keep no warehouses."""
        all_wh = self.env['recycle.warehouse'].search([])
        for rec in self:
            if rec.is_global:
                if rec.warehouse_ids:
                    rec.with_context(_shift_norm=True).warehouse_ids = [(5, 0, 0)]
            elif all_wh and rec.warehouse_ids >= all_wh:
                rec.with_context(_shift_norm=True).write(
                    {'is_global': True, 'warehouse_ids': [(5, 0, 0)]})

    @api.constrains('is_global', 'warehouse_ids')
    def _check_scope(self):
        for rec in self:
            if rec.is_global and rec.warehouse_ids:
                raise ValidationError(_(
                    'A global shift cannot be tied to specific warehouses.'))
            if not rec.is_global and not rec.warehouse_ids:
                raise ValidationError(_(
                    'Choose at least one warehouse, or make the shift global.'))

    @api.constrains('name', 'start_time', 'end_time', 'shift_type', 'tolerance')
    def _check_no_duplicate_times(self):
        """Reject only an EXACT clone: a shift is a duplicate when ANOTHER shift
        already has the same name AND start AND end AND audience type AND
        tolerance. Anything that differs in even one of those (e.g. same times
        but a different name, or same everything but a different tolerance) is
        allowed — overlapping and identical times are fine on their own."""
        for rec in self:
            twin = self.search([
                ('id', '!=', rec.id),
                ('name', '=', rec.name),
                ('shift_type', '=', rec.shift_type),
                ('start_time', '=', rec.start_time),
                ('end_time', '=', rec.end_time),
                ('tolerance', '=', rec.tolerance),
            ], limit=1)
            if twin:
                raise ValidationError(_(
                    'A shift "%s" with the same times (%s–%s), audience and '
                    'tolerance already exists.') % (
                        rec.name,
                        rec.format_time(rec.start_time),
                        rec.format_time(rec.end_time)))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._normalize_scope()
        records._ping_backend_fleet()
        return records

    def unlink(self):
        res = super().unlink()
        self._ping_backend_fleet()
        return res

    # ------------------------------------------------------------------
    # Notify assigned employees when the shift times change
    # ------------------------------------------------------------------
    def write(self, vals):
        # A GLOBAL shift can never become warehouse-specific again (it may hold
        # employees from several warehouses; narrowing its scope would orphan
        # them). Widening specific → global stays allowed.
        if not self.env.context.get('_shift_norm'):
            if vals.get('is_global') is False:
                for rec in self:
                    if rec.is_global:
                        raise UserError(_(
                            'A global shift cannot be turned into a '
                            'warehouse-specific one.'))
            if 'warehouse_ids' in vals:
                for rec in self:
                    if rec.is_global and not vals.get('is_global'):
                        raise UserError(_(
                            'A global shift has no warehouses — it applies to '
                            'all of them.'))

        times_changing = ('start_time' in vals or 'end_time' in vals)
        old = {r.id: (r.start_time, r.end_time) for r in self} if times_changing else {}
        res = super().write(vals)
        if not self.env.context.get('_shift_norm') and (
                'warehouse_ids' in vals or 'is_global' in vals):
            self._normalize_scope()
        self._ping_backend_fleet()
        if times_changing and not self.env.context.get('recycle_no_notify'):
            for rec in self:
                o = old.get(rec.id)
                if o and (o[0] != rec.start_time or o[1] != rec.end_time):
                    emps = rec._assigned_employees()
                    if emps:
                        try:
                            self.env['recycle.notification']._notify_users(
                                emps, _('Shift schedule updated'),
                                _('Your shift "%s" times changed to %s – %s.') % (
                                    rec.name,
                                    rec.format_time(rec.start_time),
                                    rec.format_time(rec.end_time)),
                                notif_type='shift_change')
                        except Exception:
                            pass
        return res

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    @api.constrains('shift_type')
    def _check_type_switch(self):
        """A shift already assigned to employees cannot become a driver
        shift (and its employees would silently violate the separation)."""
        for rec in self:
            if rec.shift_type == 'driver' and rec._assigned_employees():
                raise ValidationError(_(
                    'Cannot mark "%s" as a driver shift: warehouse employees '
                    'are still assigned to it. Unassign them first.') % rec.name)

    @api.constrains('start_time', 'end_time')
    def _check_times(self):
        for rec in self:
            if not (0 <= rec.start_time < 24):
                raise ValidationError(_('Start time must be between 00:00 and 23:59.'))
            if not (0 <= rec.end_time < 24):
                raise ValidationError(_('End time must be between 00:00 and 23:59.'))
            if rec.start_time == rec.end_time:
                raise ValidationError(_('Start and end time cannot be the same.'))
            dur = shift_duration(rec.start_time, rec.end_time)
            if dur < MIN_SHIFT_HOURS:
                raise ValidationError(_(
                    'The shift is too short (%.1f h). A shift must last at '
                    'least %d hours.') % (dur, int(MIN_SHIFT_HOURS)))
            if dur > MAX_SHIFT_HOURS:
                raise ValidationError(_(
                    'The shift is too long (%.1f h). A shift cannot exceed '
                    '%d hours.') % (dur, int(MAX_SHIFT_HOURS)))

    @api.model
    def validate_shift_times(self, start_time, end_time):
        """Stateless validator usable from the API / JS. Returns a dict:
        {valid, duration, realistic, error}."""
        try:
            start = float(start_time)
            end = float(end_time)
        except (TypeError, ValueError):
            return {'valid': False, 'error': _('Invalid time value.')}
        if not (0 <= start < 24) or not (0 <= end < 24):
            return {'valid': False, 'error': _('Times must be between 00:00 and 23:59.')}
        if start == end:
            return {'valid': False, 'error': _('Start and end time cannot be the same.')}
        dur = shift_duration(start, end)
        if dur < MIN_SHIFT_HOURS:
            return {'valid': False, 'duration': dur,
                    'error': _('A shift must last at least %d hours.') % int(MIN_SHIFT_HOURS)}
        if dur > MAX_SHIFT_HOURS:
            return {'valid': False, 'duration': dur,
                    'error': _('A shift cannot exceed %d hours.') % int(MAX_SHIFT_HOURS)}
        return {'valid': True, 'duration': dur, 'realistic': is_realistic(start, end)}

    # ------------------------------------------------------------------
    # Employee filtering / assignment
    # ------------------------------------------------------------------
    @api.model
    def get_available_employees(self, warehouse_id=None, shift_id=None):
        """Employees that can be assigned to a shift, optionally scoped to a
        warehouse. Flags those already assigned to THIS shift."""
        domain = [('recycle_role', '!=', False), ('active', '=', True)]
        if warehouse_id:
            domain.append(('recycle_warehouse_id', '=', int(warehouse_id)))
        users = self.env['res.users'].sudo().search(domain, order='name')
        out = []
        for u in users:
            cur = u.shift_id
            out.append({
                'id': u.id,
                'name': u.name,
                'role': u.recycle_role or '',
                'warehouse': u.recycle_warehouse_id.name or '',
                'assigned_here': bool(shift_id and cur and cur.id == int(shift_id)),
                'assigned_other': bool(cur and (not shift_id or cur.id != int(shift_id))),
                'other_shift': cur.name if cur else '',
            })
        return out

    def action_set_employees(self, user_ids):
        """Assign exactly the given users to this shift (and unassign users
        previously on this shift who are no longer selected)."""
        self.ensure_one()
        user_ids = [int(u) for u in (user_ids or [])]
        if self.shift_type == 'driver' and user_ids:
            raise UserError(_(
                'This is a driver shift — warehouse employees cannot be '
                'assigned to it.'))
        Users = self.env['res.users'].sudo()
        # Unassign users removed from the selection.
        current = self._assigned_employees()
        to_remove = current.filtered(lambda u: u.id not in user_ids)
        to_remove.write({'shift_id': False})
        # Assign the selected users.
        if user_ids:
            Users.browse(user_ids).write({'shift_id': self.id})
        return True

    # ------------------------------------------------------------------
    # Delete guard
    # ------------------------------------------------------------------
    def can_delete(self):
        """Return {ok, employees:[names]} — a shift can only be deleted when
        no employee is assigned to it."""
        self.ensure_one()
        emps = self._assigned_employees()
        return {'ok': not emps, 'employees': emps.mapped('name')}

    def action_recycle_delete_shift(self):
        """Delete the shift, refusing if employees are still assigned."""
        self.ensure_one()
        info = self.can_delete()
        if not info['ok']:
            raise UserError(_(
                'Cannot delete this shift as it is assigned to employees: %s.\n'
                'Unassign them from the shift first, then delete it.'
            ) % ', '.join(info['employees']))
        self.unlink()
        return True

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------
    def format_time(self, float_val):
        """Convert float hour to HH:MM string."""
        h = int(float_val)
        m = int(round((float_val - h) * 60))
        return f'{h:02d}:{m:02d}'

    def name_get(self):
        result = []
        for rec in self:
            label = (
                f'{rec.name}  '
                f'({rec.format_time(rec.start_time)} – '
                f'{rec.format_time(rec.end_time)}, '
                f'±{rec.tolerance}min)'
            )
            result.append((rec.id, label))
        return result
