# -*- coding: utf-8 -*-
"""What the sorter reports about material ALREADY in storage.

The report says one thing only: **this quantity is gone.** It was damaged on the
shelf, and the warehouse no longer has it.

An earlier version of this model also carried a "downgrade" — material that was
still present but had slipped to a lower grade. That has been removed on
purpose. It made a single form answer two questions whose effects on the total
are opposite (one removes quantity, the other moves it), and the sorter had to
choose between them before anything else on the screen made sense. Grade
corrections belong to sorting, not to a loss report.

The report still needs the manager's approval, because approving it deducts real
stock a buyer may already have been quoted against — and because the deduction
should be a decision, not a side effect of someone filling in a form.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class RecycleStockDamageReport(models.Model):
    _name = 'recycle.stock.damage.report'
    _description = 'Stored Material Damage Report'
    _inherit = ['mail.thread', 'recycle.grade.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'))
    warehouse_id = fields.Many2one(
        'recycle.warehouse', required=True, tracking=True,
        default=lambda self: self.env.user.recycle_warehouse_id.id)
    product_id = fields.Many2one(
        'recycle.product', string='Material', required=True, tracking=True)
    uom_id = fields.Many2one(
        'recycle.measurement.unit', related='product_id.uom_id',
        store=True, readonly=True)

    # ── Which grade was lost ────────────────────────────────────────────────
    #
    # Grades belong to the MATERIAL and are authored by the backend admin, so
    # this is a code rather than a fixed choice. It is required exactly when the
    # material has grades: without it the deduction fell on whichever grade
    # happened to sort first, which is not the one the sorter was looking at —
    # and for an ungraded material there is no grade to name at all.
    condition = fields.Char(
        string='Grade', size=30, tracking=True,
        help='The grade this material is filed under today. Required when the '
             'material has grades; left empty when it has none.')
    condition_label = fields.Char(
        string='Grade Name', compute='_compute_condition_label')
    product_has_grades = fields.Boolean(
        compute='_compute_condition_label',
        help='Drives the form: the grade field only appears for a material '
             'that actually has grades.')

    quantity = fields.Float(string='Quantity', required=True, tracking=True)
    available_qty = fields.Float(
        string='Available Now', compute='_compute_available_qty',
        help='What can still be reported on: stock of this grade MINUS what '
             'is already promised to open orders.')
    reason = fields.Text(string='Reason', required=True)
    image = fields.Binary(string='Photo', attachment=True)
    state = fields.Selection([
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='pending_approval', required=True, copy=False, tracking=True)
    reported_by = fields.Many2one(
        'res.users', string='Reported By', readonly=True, copy=False,
        default=lambda self: self.env.user.id)
    reviewed_by = fields.Many2one(
        'res.users', string='Reviewed By', readonly=True, copy=False)
    review_reason = fields.Text(string='Rejection Reason', copy=False)
    approved_at = fields.Datetime(
        string='Approved At', readonly=True, copy=False,
        help='When the stock was actually deducted — the date the warehouse '
             'loss is counted under.')
    damage_entry_id = fields.Many2one(
        'recycle.damage.entry', string='Damage Log Entry', readonly=True,
        copy=False,
        help='The ledger row this report produced when it was approved.')

    # ------------------------------------------------------------------
    # Computes / constraints
    # ------------------------------------------------------------------
    @api.depends('product_id', 'condition')
    def _compute_condition_label(self):
        Conditions = self.env['recycle.material.condition']
        for rec in self:
            rec.product_has_grades = Conditions.has_grades(rec.product_id)
            rec.condition_label = Conditions.label_for(
                rec.product_id, rec.condition)

    @api.depends('warehouse_id', 'product_id', 'condition')
    def _compute_available_qty(self):
        for rec in self:
            if rec.warehouse_id and rec.product_id:
                rec.available_qty = self.env['recycle.stock']._available_qty(
                    rec.warehouse_id, rec.product_id, rec.condition or None)
            else:
                rec.available_qty = 0.0

    @api.constrains('quantity')
    def _check_quantity(self):
        for rec in self:
            if rec.quantity <= 0:
                raise ValidationError(_('Quantity must be positive.'))

    @api.constrains('product_id', 'condition')
    def _check_condition(self):
        """A graded material must say WHICH grade was lost; an ungraded one must not.

        Both halves matter. Deducting without a grade takes the quantity off
        whichever row the database returned first — not the one the sorter was
        looking at. And accepting a grade for an ungraded material records a
        distinction that does not exist, which no later reader can undo.
        """
        Conditions = self.env['recycle.material.condition']
        for rec in self:
            if not rec.product_id:
                continue
            Conditions.normalize(rec.product_id, rec.condition)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Clear a grade carried over from the previously chosen material.

        Grades are per material, so a code left behind from the last selection
        is not merely stale — it belongs to something else entirely.
        """
        self.condition = False
        Conditions = self.env['recycle.material.condition']
        codes = Conditions.codes_for(self.product_id)
        if len(codes) == 1:
            # Exactly one grade: choosing it is not a decision, so do not make
            # the sorter make it.
            self.condition = codes[0]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].sudo().next_by_code(
                    'recycle.stock.damage.report') or _('New')
        records = super().create(vals_list)
        for rec in records:
            rec._assert_reportable()
            rec._notify_manager()
        return records

    def _assert_reportable(self):
        """Refuse a report bigger than what is actually free.

        AVAILABLE, not raw quantity: stock promised to an open order is not the
        sorter's to write off. Letting it through would leave the warehouse
        owing an order more than it holds — a discrepancy nobody would notice
        until the output employee could not fill it.
        """
        self.ensure_one()
        available = self.env['recycle.stock']._available_qty(
            self.warehouse_id, self.product_id, self.condition or None)
        if self.quantity > available:
            raise UserError(_(
                'Only %(avail)s %(uom)s of "%(product)s"%(cond)s is free in '
                '%(wh)s — the rest is already promised to open orders. You '
                'reported %(req)s.') % {
                    'avail': available, 'uom': self.uom_id.name or '',
                    'product': self.product_id.name,
                    'cond': self._grade_suffix(),
                    'wh': self.warehouse_id.name, 'req': self.quantity})

    def _grade_suffix(self):
        """' in grade "X"' — or nothing at all for an ungraded material.

        Kept out of the sentences themselves so an ungraded material never
        produces a message with an empty pair of quotes in it.
        """
        self.ensure_one()
        if not self.condition:
            return ''
        label = self.env['recycle.material.condition'].label_for(
            self.product_id, self.condition)
        return _(' in grade "%s"') % label

    def _notify_manager(self):
        self.ensure_one()
        manager = self.warehouse_id.manager_user_id
        if not manager:
            return
        body = _('%(who)s reports %(qty)s %(uom)s of "%(product)s"%(cond)s '
                 'damaged in storage. Reason: %(reason)s. Approve it to write '
                 'the quantity off.') % {
            'who': self.reported_by.name, 'qty': self.quantity,
            'uom': self.uom_id.name or '', 'product': self.product_id.name,
            'cond': self._grade_suffix(),
            'reason': self.reason or '-'}
        self.env['recycle.notification'].sudo()._notify_user(
            manager, _('Damage report: %s') % self.name, body)

    def _is_supervisor(self):
        user = self.env.user
        return (user.has_group('recycle_warehouse.group_recycle_admin')
                or user.has_group('recycle_warehouse.group_recycle_manager'))

    # ------------------------------------------------------------------
    # Manager decision
    # ------------------------------------------------------------------
    def action_approve(self):
        if not self._is_supervisor():
            raise UserError(_('Only the warehouse manager or the administrator '
                              'can approve damage reports.'))
        Stock = self.env['recycle.stock']
        Damage = self.env['recycle.damage.entry']
        for rec in self:
            if rec.state != 'pending_approval':
                raise UserError(_('Only pending reports can be approved.'))

            # Re-checked HERE, not only at creation: the report sat waiting for
            # the manager, and an order allocated in the meantime may have
            # spoken for the same stock.
            rec._assert_reportable()

            Stock._deduct_quantity(
                rec.warehouse_id, rec.product_id, rec.quantity,
                condition=rec.condition or None)

            # The quantity is gone from stock; this is where it is written DOWN,
            # so the warehouse can answer what it lost, of what, and when.
            entry = Damage.record_from_report(rec)

            rec.write({
                'state': 'approved',
                'reviewed_by': self.env.user.id,
                'approved_at': fields.Datetime.now(),
                'damage_entry_id': entry.id,
            })
            rec.message_post(body=_(
                'Damage approved by %(who)s. %(qty)s %(uom)s of "%(product)s"'
                '%(cond)s written off and recorded in the warehouse damage '
                'log.') % {
                    'who': self.env.user.name, 'qty': rec.quantity,
                    'uom': rec.uom_id.name or '',
                    'product': rec.product_id.name,
                    'cond': rec._grade_suffix()})
            self.env['recycle.notification'].sudo()._notify_user(
                rec.reported_by, _('Report approved: %s') % rec.name,
                _('The manager approved your damage report. Stock was '
                  'updated.'))

            # The backend prices and allocates from its mirror of these
            # quantities. Without this the mirror keeps offering grade and
            # quantity the warehouse no longer has, and the error surfaces as a
            # failed order rather than as a number.
            rec._notify_backend()

    def action_reject(self, reason=None):
        if not self._is_supervisor():
            raise UserError(_('Only the warehouse manager or the administrator '
                              'can reject damage reports.'))
        for rec in self:
            if rec.state != 'pending_approval':
                raise UserError(_('Only pending reports can be rejected.'))
            rec.write({'state': 'rejected', 'reviewed_by': self.env.user.id,
                       'review_reason': (reason or '').strip()})
            rec.message_post(body=_('Report rejected by %s.') % self.env.user.name)
            self.env['recycle.notification'].sudo()._notify_user(
                rec.reported_by,
                _('Report rejected: %s') % rec.name,
                _('The manager rejected your report. Reason: %s.')
                % ((reason or '').strip() or '-'))

    def _notify_backend(self):
        self.ensure_one()
        try:
            self.env['recycle.backend.sync'].sudo().notify_inventory_changed(
                self.warehouse_id)
        except Exception:
            # Never let the mirror push undo the manager's decision — the
            # backend's periodic warehouse sync reconciles either way.
            pass
