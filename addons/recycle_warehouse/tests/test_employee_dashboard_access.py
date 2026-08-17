# -*- coding: utf-8 -*-
"""Every role must be able to open its own dashboard.

The bug this exists for: opening the sorting employee's dashboard threw an
AccessError. `/api/employee/my-shift` reads `recycle.shift` WITHOUT sudo — which
is right, an employee should only see shifts they are entitled to — and the
record rule scoping them to their own warehouse was written and correct.

The ACL row was never added.

In Odoo a record rule filters WITHIN what an ACL already permits. With no ACL
row the model is denied outright and the rule never runs, so the rule sat there
looking like the access it was supposed to refine. Every check short of actually
being that user passes: the rule exists, its domain is right, the code is right.

Two things are therefore pinned here:

  1. each employee role can read what its dashboard reads, as itself;
  2. no record rule exists for a group that has no ACL for the same model —
     the shape of the original mistake, caught by structure rather than by
     someone remembering to test the third role.
"""
from odoo.tests.common import TransactionCase, tagged
from .common import make_warehouse

# (model, the roles whose dashboard reads it)
DASHBOARD_READS = [
    ('recycle.shift', ('input', 'sorting', 'output')),
    ('recycle.attendance', ('input', 'sorting', 'output')),
    ('recycle.product', ('input', 'sorting', 'output')),
    ('recycle.material.condition', ('sorting', 'output')),
    ('recycle.stock', ('sorting', 'output')),
    ('recycle.shipment', ('input', 'sorting')),
    ('recycle.zone', ('input', 'sorting', 'output')),
    ('recycle.warehouse', ('input', 'sorting', 'output')),
    ('recycle.notification', ('input', 'sorting', 'output')),
]

ROLE_GROUPS = {
    'input': 'recycle_warehouse.group_recycle_input',
    'sorting': 'recycle_warehouse.group_recycle_sorting',
    'output': 'recycle_warehouse.group_recycle_output',
}


@tagged('post_install', '-at_install')
class TestEmployeeDashboardAccess(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = make_warehouse(cls.env, 
            {'name': 'Access WH', 'code': 'ACCESSWH'})
        cls.users = {}
        for role, xmlid in ROLE_GROUPS.items():
            cls.users[role] = cls.env['res.users'].create({
                'name': 'Access %s' % role,
                'login': 'access.%s@example.com' % role,
                'email': 'access.%s@example.com' % role,
                'recycle_role': role,
                'recycle_warehouse_id': cls.warehouse.id,
                'recycle_national_id': 'ACCESS-%s' % role.upper(),
                'group_ids': [(4, cls.env.ref('base.group_user').id),
                              (4, cls.env.ref(xmlid).id)],
            })

    def test_each_role_can_read_what_its_dashboard_reads(self):
        """As the user, not as sudo — sudo is what hides this class of bug."""
        denied = []
        for model, roles in DASHBOARD_READS:
            if model not in self.env:
                continue
            for role in roles:
                user = self.users[role]
                try:
                    self.env[model].with_user(user).search_read(
                        [], ['id'], limit=1)
                except Exception as exc:
                    denied.append('%s cannot read %s (%s)'
                                  % (role, model, type(exc).__name__))

        self.assertEqual(denied, [], '\n'.join(
            ['These reads fail on the employee dashboards:'] + denied))

    def test_my_shift_works_for_every_employee_role(self):
        """The exact call that broke.

        `/api/employee/my-shift` touches `shift_id` fields directly and without
        sudo; with no ACL that raises before any rule is consulted.
        """
        shift = self.env['recycle.shift'].create({
            'name': 'Access Shift',
            'start_time': 8.0,
            'end_time': 16.0,
            'warehouse_ids': [(6, 0, [self.warehouse.id])],
        })
        failed = []
        for role, user in self.users.items():
            user.sudo().write({'shift_id': shift.id})
            try:
                as_user = self.env['res.users'].with_user(user).browse(user.id)
                _ = as_user.shift_id.name
                _ = as_user.shift_id.start_time
            except Exception as exc:
                failed.append('%s: %s' % (role, type(exc).__name__))

        self.assertEqual(failed, [], 'my-shift fails for: %s' % failed)

    def test_no_record_rule_exists_without_an_acl_behind_it(self):
        """The SHAPE of the original mistake.

        A rule for a group that has no ACL on the same model is dead code that
        reads as working access control. It is worse than a missing rule,
        because it is the thing someone checks when access is refused and finds
        nothing wrong with.
        """
        rules = self.env['ir.rule'].sudo().search([('active', '=', True)])
        access = self.env['ir.model.access'].sudo().search(
            [('perm_read', '=', True)])

        allowed = {}
        for row in access:
            allowed.setdefault(row.model_id.model, set()).update(
                row.group_id.ids or [])

        dead = []
        for rule in rules:
            model = rule.model_id.model
            # Only this addon's models — Odoo's own are not ours to audit.
            if not model.startswith('recycle.'):
                continue
            for group in rule.groups:
                if group.id not in allowed.get(model, set()):
                    dead.append('%s :: rule "%s" is scoped to group "%s", '
                                'which has no read ACL for that model'
                                % (model, rule.name, group.full_name))

        self.assertEqual(dead, [], '\n'.join(
            ['Record rules with no ACL behind them — the rule never runs and '
             'the model is denied outright:'] + dead))
