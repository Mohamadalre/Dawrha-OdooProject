# -*- coding: utf-8 -*-
"""Phone is one-per-person on the MANAGER's employee screen too.

The admin routes already refuse a duplicate phone (see
test_admin_employee_create). A manager adds and edits staff through a DIFFERENT
pair of endpoints, scoped to their own warehouse — so the same rule has to hold
there independently, or the check an admin sees enforced simply is not enforced
for the person who does most of the hiring.

Two things this file pins down:
  - CREATE refuses a phone already on file.
  - EDIT refuses moving an employee onto another's phone, but EXCLUDES the
    employee being edited (keeping your own number is a no-op, not a clash).
"""
import zlib

from odoo.tests.common import HttpCase, tagged

from .common import make_warehouse


@tagged('post_install', '-at_install')
class TestManagerEmployeePhone(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.wh = make_warehouse(cls.env, **{'name': 'Mgr WH', 'code': 'MGRWH'})
        cls.manager = cls.env['res.users'].create({
            'name': 'Warehouse Manager',
            'login': 'mgr.phone@example.com',
            'email': 'mgr.phone@example.com',
            'password': 'mgr-phone-pw-1',
            'recycle_role': 'manager',
            'recycle_warehouse_id': cls.wh.id,
            'group_ids': [(4, cls.env.ref(
                'recycle_warehouse.group_recycle_manager').id)],
        })
        cls.wh.write({'manager_user_id': cls.manager.id})

    def setUp(self):
        super().setUp()
        self.authenticate('mgr.phone@example.com', 'mgr-phone-pw-1')

    def _create(self, **overrides):
        email = overrides.get('email', 'mgr.hire@example.com')
        payload = {
            'name': 'Mgr Hire',
            'email': 'mgr.hire@example.com',
            # Unique per email by default — phone is one-per-person now, so a
            # fixed default would make the second hire in a test collide on it.
            'phone': '07' + str(zlib.crc32(email.encode()) % 100000000).zfill(8),
            'national_id': 'MGR-HIRE-DEFAULT',
            'role': 'sorting',
        }
        payload.update(overrides)
        return self.make_jsonrpc_request(
            '/api/manager/employee/create', params=payload)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------
    def test_create_refuses_a_phone_already_in_use(self):
        first = self._create(email='mgr.p1@example.com',
                             national_id='MGR-P1', phone='0777000000')
        self.assertTrue(first.get('ok'), first)
        second = self._create(email='mgr.p2@example.com',
                              national_id='MGR-P2', phone='0777000000')
        self.assertEqual(second.get('error'), 'phone_exists')

    def test_create_allows_an_empty_phone(self):
        res = self._create(email='mgr.nophone@example.com',
                           national_id='MGR-NOPHONE', phone='')
        self.assertTrue(res.get('ok'), res)

    # ------------------------------------------------------------------
    # Edit
    # ------------------------------------------------------------------
    def test_edit_refuses_moving_onto_another_phone_but_excludes_self(self):
        a = self._create(email='mgr.a@example.com',
                        national_id='MGR-A', phone='0777100000')
        b = self._create(email='mgr.b@example.com',
                        national_id='MGR-B', phone='0777100001')
        self.assertTrue(a.get('ok'), a)
        self.assertTrue(b.get('ok'), b)
        # Moving B onto A's number is refused.
        clash = self.make_jsonrpc_request(
            '/api/manager/employee/update',
            params={'employee_id': b['id'], 'phone': '0777100000'})
        self.assertEqual(clash.get('error'), 'phone_exists')
        # Keeping B's OWN number is fine — the edited record is excluded.
        same = self.make_jsonrpc_request(
            '/api/manager/employee/update',
            params={'employee_id': b['id'], 'phone': '0777100001'})
        self.assertTrue(same.get('ok'), same)
