# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class RecycleEmployeeHistory(models.Model):
    _name = 'recycle.employee.history'
    _description = 'Employee Change History'
    _order = 'create_date desc, id desc'

    user_id = fields.Many2one('res.users', string='Employee',
                              required=True, index=True, ondelete='cascade')
    change_type = fields.Selection([
        ('role', 'Role Change'),
        ('warehouse', 'Warehouse Change'),
        ('direct_addition', 'Direct Addition'),
        ('assignment_start', 'Assignment Start'),
        ('assignment_end', 'Assignment End'),
        ('archive', 'Archived'),
        ('restore', 'Restored'),
    ], string='Change Type', required=True)
    old_role = fields.Char(string='Old Role')
    new_role = fields.Char(string='New Role')
    old_warehouse = fields.Char(string='Old Warehouse')
    new_warehouse = fields.Char(string='New Warehouse')
    assignment_start_date = fields.Datetime(
        string='Assignment Start Date',
        help='When the employee was assigned to this role/warehouse')
    assignment_end_date = fields.Datetime(
        string='Assignment End Date',
        help='When the employee was unassigned (archived)')
    changed_by = fields.Many2one('res.users', string='Changed By',
                                 ondelete='set null')
    note = fields.Text(string='Notes')

    @api.model
    def log_change(self, user, change_type, old_role=None, new_role=None,
                   old_warehouse=None, new_warehouse=None,
                   changed_by=None, note=None,
                   assignment_start_date=None, assignment_end_date=None):
        vals = {
            'user_id': user.id,
            'change_type': change_type,
            'changed_by': changed_by.id if changed_by else False,
            'note': note,
        }
        if old_role is not None:
            vals['old_role'] = old_role
        if new_role is not None:
            vals['new_role'] = new_role
        if old_warehouse is not None:
            vals['old_warehouse'] = old_warehouse
        if new_warehouse is not None:
            vals['new_warehouse'] = new_warehouse
        if assignment_start_date is not None:
            vals['assignment_start_date'] = assignment_start_date
        if assignment_end_date is not None:
            vals['assignment_end_date'] = assignment_end_date
        return self.sudo().create(vals)

    def get_history_for_user(self, user_id):
        """Return all history records for a given user, ordered by date."""
        return self.sudo().search([
            ('user_id', '=', user_id),
        ], order='create_date desc', limit=300)
