# -*- coding: utf-8 -*-
"""Adding staff from the admin screen — and the two rules that make it safe.

ONE MANAGER PER WAREHOUSE, BOTH WAYS
────────────────────────────────────
A warehouse with two managers is two people each believing the site is theirs:
a decision gets taken twice and reversed once, and neither is wrong about their
authority. And a manager holding two warehouses would see one of them — every
manager screen scopes on `recycle_warehouse_id`, a single field — while being
accountable for both.

Both directions are refused BEFORE the account exists, so the message names the
conflict instead of leaving a half-made user behind for someone to find.

ONE IDENTITY PER PERSON
───────────────────────
The national ID and the email are unique across everyone in the system — staff,
delivery drivers, collectors and job applicants alike — because they identify a
human being and not a row in one table. That is `recycle.identity`, a UNIQUE
index rather than a search, and `res.users.create` goes through it on its own.
What is tested here is that the endpoint turns its refusal into an answer the
screen can show, rather than a 500 on a half-written transaction.
"""
from odoo.tests.common import HttpCase, tagged
from .common import make_warehouse


@tagged('post_install', '-at_install')
class TestAdminEmployeeCreate(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.free_wh = make_warehouse(cls.env, **{'name': 'Hire WH Free', 'code': 'HIREFREE'})
        cls.taken_wh = make_warehouse(cls.env, **{'name': 'Hire WH Taken', 'code': 'HIRETAKEN'})
        cls.closing_wh = make_warehouse(cls.env, **{'name': 'Hire WH Closing', 'code': 'HIRECLOSE'})
        cls.closing_wh.state = 'closing'

        cls.sitting_manager = cls.env['res.users'].create({
            'name': 'Sitting Manager',
            'login': 'sitting.manager@example.com',
            'email': 'sitting.manager@example.com',
            'recycle_national_id': 'HIRE-SITTING-1',
            'group_ids': [(4, cls.env.ref(
                'recycle_warehouse.group_recycle_manager').id)],
        })
        cls.taken_wh.write({'manager_user_id': cls.sitting_manager.id})

        cls.admin = cls.env['res.users'].create({
            'name': 'Hiring Admin',
            'login': 'hiring.admin@example.com',
            'email': 'hiring.admin@example.com',
            'password': 'hiring-admin-pw-1',
            'group_ids': [(4, cls.env.ref(
                'recycle_warehouse.group_recycle_admin').id)],
        })

    def setUp(self):
        super().setUp()
        self.authenticate('hiring.admin@example.com', 'hiring-admin-pw-1')

    def _create(self, **overrides):
        import zlib
        email = overrides.get('email', 'new.hire@example.com')
        payload = {
            'name': 'New Hire',
            'email': 'new.hire@example.com',
            # A phone UNIQUE per email by default. Phone is now one-per-person
            # (like the national id), so a fixed default would make the second
            # employee in any test collide on it — a collision unrelated to what
            # these tests check. A test that WANTS a phone clash passes phone=.
            'phone': '09' + str(zlib.crc32(email.encode()) % 100000000).zfill(8),
            'national_id': 'HIRE-NEW-1',
            'role': 'input',
            'warehouse_id': self.free_wh.id,
        }
        payload.update(overrides)
        return self.make_jsonrpc_request(
            '/api/admin/employee/create', params=payload)

    # ------------------------------------------------------------------
    # The ordinary case
    # ------------------------------------------------------------------
    def test_a_warehouse_employee_is_created_and_assigned(self):
        res = self._create(role='output', email='out.hire@example.com',
                           national_id='HIRE-OUT-1')
        self.assertTrue(res.get('ok'), res)

        user = self.env['res.users'].sudo().browse(res['id'])
        self.assertEqual(user.recycle_role, 'output')
        self.assertEqual(user.recycle_warehouse_id, self.free_wh)
        self.assertTrue(user.has_group('recycle_warehouse.group_recycle_output'))

    def test_no_password_is_set_here(self):
        """The employee chooses their own through a signed link.

        An admin who types a password knows it, and a password two people know
        is not one that identifies either of them.
        """
        res = self._create(email='nopw.hire@example.com',
                           national_id='HIRE-NOPW-1')
        user = self.env['res.users'].sudo().browse(res['id'])
        self.assertFalse(user.password)

    def test_the_warehouse_is_required(self):
        res = self._create(warehouse_id=None)
        self.assertEqual(res.get('error'), 'warehouse_required')

    def test_a_closing_warehouse_takes_no_new_staff(self):
        """The point of the state is that work stops arriving — staff are work."""
        res = self._create(warehouse_id=self.closing_wh.id,
                           email='closing.hire@example.com',
                           national_id='HIRE-CLOSE-1')
        self.assertEqual(res.get('error'), 'warehouse_not_active')

    def test_an_unknown_role_is_refused(self):
        res = self._create(role='admin')
        self.assertEqual(res.get('error'), 'invalid_role')

    # ------------------------------------------------------------------
    # One manager per warehouse
    # ------------------------------------------------------------------
    def test_a_manager_is_appointed_to_a_free_warehouse(self):
        res = self._create(role='manager', email='mgr.hire@example.com',
                           national_id='HIRE-MGR-1')
        self.assertTrue(res.get('ok'), res)

        user = self.env['res.users'].sudo().browse(res['id'])
        self.free_wh.invalidate_recordset()
        self.assertEqual(self.free_wh.manager_user_id, user)
        # Written through the WAREHOUSE, so the link exists on both sides — the
        # user's own field alone would leave the site with no manager and the
        # user claiming one.
        self.assertEqual(user.recycle_warehouse_id, self.free_wh)
        self.assertTrue(user.has_group('recycle_warehouse.group_recycle_manager'))

    def test_a_warehouse_that_has_a_manager_cannot_be_given_another(self):
        res = self._create(role='manager', warehouse_id=self.taken_wh.id,
                           email='second.mgr@example.com',
                           national_id='HIRE-MGR-2')
        self.assertEqual(res.get('error'), 'warehouse_has_manager')
        # And the refusal NAMES who holds it, so the admin knows what to do next.
        self.assertEqual(res.get('manager'), 'Sitting Manager')

    def test_the_refused_manager_leaves_no_account_behind(self):
        """Checked before the account exists, not after.

        A half-made user found later is worse than a refusal: it has a login,
        it has no warehouse, and nobody remembers why.
        """
        before = self.env['res.users'].sudo().search_count(
            [('login', '=', 'ghost.mgr@example.com')])
        self._create(role='manager', warehouse_id=self.taken_wh.id,
                     email='ghost.mgr@example.com',
                     national_id='HIRE-GHOST-1')
        after = self.env['res.users'].sudo().search_count(
            [('login', '=', 'ghost.mgr@example.com')])
        self.assertEqual(before, after, 'a refused manager left an account')

    def test_ordinary_staff_may_share_a_warehouse_freely(self):
        """The rule is about MANAGERS. A warehouse has many employees."""
        first = self._create(role='sorting', email='s1@example.com',
                             national_id='HIRE-S1')
        second = self._create(role='sorting', email='s2@example.com',
                              national_id='HIRE-S2')
        self.assertTrue(first.get('ok'), first)
        self.assertTrue(second.get('ok'), second)

    def test_staff_may_join_a_warehouse_that_has_a_manager(self):
        res = self._create(role='input', warehouse_id=self.taken_wh.id,
                           email='staff.taken@example.com',
                           national_id='HIRE-STAFF-TAKEN')
        self.assertTrue(res.get('ok'), res)

    # ------------------------------------------------------------------
    # One identity per person
    # ------------------------------------------------------------------
    def test_a_national_id_already_in_the_system_is_refused(self):
        res = self._create(email='dup.nid@example.com',
                           national_id='HIRE-SITTING-1')
        self.assertEqual(res.get('error'), 'identity_taken')
        # The message names what holds it rather than saying "already in use",
        # which sends someone hunting through the wrong screen.
        self.assertIn('HIRE-SITTING-1', res.get('message', ''))

    def test_an_email_already_used_as_a_login_is_refused(self):
        res = self._create(email='sitting.manager@example.com',
                           national_id='HIRE-DUP-EMAIL')
        self.assertEqual(res.get('error'), 'login_exists')

    def test_a_phone_already_in_the_system_is_refused(self):
        """Phone is one-per-person now — a second hire cannot reuse it."""
        first = self._create(email='phone.one@example.com',
                             national_id='HIRE-PHONE-1', phone='0999555000')
        self.assertTrue(first.get('ok'), first)
        second = self._create(email='phone.two@example.com',
                              national_id='HIRE-PHONE-2', phone='0999555000')
        self.assertEqual(second.get('error'), 'phone_exists')

    def test_editing_a_phone_onto_one_already_used_is_refused(self):
        """The same one-per-person rule on EDIT — and self is excluded."""
        a = self._create(email='edit.a@example.com',
                         national_id='HIRE-EDIT-A', phone='0999600000')
        b = self._create(email='edit.b@example.com',
                         national_id='HIRE-EDIT-B', phone='0999600001')
        self.assertTrue(a.get('ok'), a)
        self.assertTrue(b.get('ok'), b)
        # Moving B onto A's number is refused.
        clash = self.make_jsonrpc_request(
            '/api/admin/employee/update',
            params={'employee_id': b['id'], 'phone': '0999600000'})
        self.assertEqual(clash.get('error'), 'phone_exists')
        # Keeping B's OWN number is fine — the edited record is excluded.
        same = self.make_jsonrpc_request(
            '/api/admin/employee/update',
            params={'employee_id': b['id'], 'phone': '0999600001'})
        self.assertTrue(same.get('ok'), same)

    def test_a_refused_identity_leaves_no_account_behind(self):
        """The savepoint doing its job.

        Without it the failed create would poison the transaction and the
        request would 500 — and the screen would show nothing it could act on.
        """
        self._create(email='ghost.nid@example.com',
                     national_id='HIRE-SITTING-1')
        self.assertFalse(self.env['res.users'].sudo().search_count(
            [('login', '=', 'ghost.nid@example.com')]))

    def test_a_national_id_held_by_a_DELIVERY_DRIVER_is_refused(self):
        """Uniqueness spans the tables, not just res.users.

        A person on file as a delivery driver and again as an employee is two
        histories, two blocks and two sets of documents — with no way to say
        which one is them.
        """
        self.env['recycle.delivery.driver'].sudo().create({
            'name': 'Existing Driver',
            'phone': '0999123123',
            'national_id': 'HIRE-DRIVER-1',
            'warehouse_id': self.free_wh.id,
        })
        res = self._create(email='clash.driver@example.com',
                           national_id='HIRE-DRIVER-1')
        self.assertEqual(res.get('error'), 'identity_taken')

    # ------------------------------------------------------------------
    # Who may do this
    # ------------------------------------------------------------------
    def test_a_warehouse_manager_cannot_use_this_endpoint(self):
        """Otherwise a manager could make themselves a peer elsewhere."""
        self.env['res.users'].sudo().browse(self.sitting_manager.id).write(
            {'password': 'sitting-manager-pw-1'})
        self.authenticate('sitting.manager@example.com', 'sitting-manager-pw-1')

        res = self.make_jsonrpc_request('/api/admin/employee/create', params={
            'name': 'Sneaky Hire',
            'email': 'sneaky@example.com',
            'role': 'manager',
            'warehouse_id': self.free_wh.id,
        })
        self.assertEqual(res.get('error'), 'forbidden')
