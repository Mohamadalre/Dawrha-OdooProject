# -*- coding: utf-8 -*-
from odoo import api, fields, models, _



class RecycleAttendance(models.Model):
    _name = 'recycle.attendance'
    _description = 'Employee Attendance'
    _order = 'date desc, check_in desc'
    _rec_name = 'employee_user_id'

    employee_user_id = fields.Many2one(
        'res.users', 'Employee',
        required=True, ondelete='cascade')
    employee_name = fields.Char(
        related='employee_user_id.name',
        store=True, string='Employee Name')
    warehouse_id = fields.Many2one(
        'recycle.warehouse', 'Warehouse',
        compute='_compute_warehouse', store=True)
    shift_id = fields.Many2one(
        'recycle.shift', 'Shift',
        compute='_compute_shift', store=True)

    date = fields.Date('Date', required=True, default=fields.Date.today)

    # Raw datetime fields used only for work_hours calculation (stored as-is, not shown)
    check_in = fields.Datetime('Check In Raw')
    check_out = fields.Datetime('Check Out Raw')

    # Display fields — store the exact time the employee entered, never converted
    check_in_display = fields.Char(
        string='Check In', readonly=True,
        help='Exact check-in time as entered by the employee (no timezone conversion).')
    check_out_display = fields.Char(
        string='Check Out', readonly=True,
        help='Exact check-out time as entered by the employee (no timezone conversion).')

    status = fields.Selection([
        ('present',      'Present'),
        ('late',         'Late'),
        ('early_leave',  'Left Early'),
        ('late_and_early', 'Late & Left Early'),
    ], string='Status', default='present')

    late_minutes = fields.Integer('Late (min)', default=0)
    early_leave_minutes = fields.Integer('Left Early (min)', default=0)
    work_hours = fields.Float(
        'Work Hours',
        compute='_compute_work_hours',
        store=True, digits=(4, 2))

    @api.depends('employee_user_id')
    def _compute_warehouse(self):
        for rec in self:
            rec.warehouse_id = (
                rec.employee_user_id.recycle_warehouse_id
                if rec.employee_user_id else False)

    @api.depends('employee_user_id')
    def _compute_shift(self):
        for rec in self:
            rec.shift_id = (
                rec.employee_user_id.shift_id
                if rec.employee_user_id else False)

    @api.depends('check_in', 'check_out')
    def _compute_work_hours(self):
        for rec in self:
            if rec.check_in and rec.check_out:
                delta = rec.check_out - rec.check_in
                rec.work_hours = delta.total_seconds() / 3600.0
            else:
                rec.work_hours = 0.0

    _unique_employee_date = models.Constraint(
        'UNIQUE(employee_user_id, date)',
        'An attendance record already exists for this employee on this date.',
    )
