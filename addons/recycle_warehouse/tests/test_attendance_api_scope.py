# -*- coding: utf-8 -*-
"""An attendance token may only write ITS OWN day.

The check-in / check-out routes take `employee_id` from the request body. They
validated the Bearer token and then never looked at it again, so the body — not
the token — decided whose attendance was written: any employee holding a valid
token could punch in or out as any colleague by changing one number. Nothing in
the codebase objected, because nothing ever compared the two.

These tests drive the real HTTP routes rather than the helper, because the bug
was never in the helper: it was that the two routes each forgot to call one.
"""
import json

from odoo.tests.common import HttpCase, tagged

from .common import make_warehouse


@tagged('post_install', '-at_install')
class TestAttendanceApiScope(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = make_warehouse(cls.env, **{
            'name': 'Attendance Scope WH', 'code': 'ATTSCOPE',
        })
        # Check-in refuses an employee with no shift, so the honest-path tests
        # need one — the scope tests must be refused BEFORE reaching that check.
        cls.shift = cls.env['recycle.shift'].create({
            'name': 'Attendance Scope Shift',
            'start_time': 8.0,
            'end_time': 16.0,
            'shift_type': 'warehouse',
            'warehouse_ids': [(6, 0, [cls.warehouse.id])],
        })
        # Two colleagues in the same warehouse — the realistic attacker and
        # victim: both are legitimate users, so no permission check catches it.
        cls.alice = cls.env['res.users'].create({
            'name': 'Alice Attendance',
            'login': 'alice.attendance@test.local',
            'password': 'alice-test-pw-9134',
            'recycle_warehouse_id': cls.warehouse.id,
            'shift_id': cls.shift.id,
        })
        cls.bob = cls.env['res.users'].create({
            'name': 'Bob Attendance',
            'login': 'bob.attendance@test.local',
            'password': 'bob-test-pw-9134',
            'recycle_warehouse_id': cls.warehouse.id,
            'shift_id': cls.shift.id,
        })

    # ------------------------------------------------------------------
    def _post(self, path, payload, token=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        return self.url_open(
            path, data=json.dumps(payload).encode(), headers=headers)

    def _login(self, email, password):
        res = self._post('/api/login', {'email': email, 'password': password})
        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertTrue(body.get('token'), body)
        return body['token']

    def _attendance_of(self, user, date=None):
        domain = [('employee_user_id', '=', user.id)]
        if date:
            domain.append(('date', '=', date))
        return self.env['recycle.attendance'].sudo().search(domain)

    # ------------------------------------------------------------------
    def test_check_in_cannot_target_another_employee(self):
        """Alice's token + Bob's id = refused, and Bob's day stays untouched."""
        token = self._login('alice.attendance@test.local', 'alice-test-pw-9134')

        res = self._post('/api/attendance/check-in', {
            'employee_id': self.bob.id,
            'check_in_time': '2026-08-03T08:00:00',
        }, token=token)

        self.assertEqual(res.status_code, 403, res.text)
        self.assertFalse(
            self._attendance_of(self.bob),
            'Bob was checked in by somebody else\'s token')
        self.assertFalse(
            self._attendance_of(self.alice),
            'a refused request must not write anything at all')

    def test_check_out_cannot_target_another_employee(self):
        token = self._login('alice.attendance@test.local', 'alice-test-pw-9134')

        res = self._post('/api/attendance/check-out', {
            'employee_id': self.bob.id,
            'check_out_time': '2026-08-03T16:00:00',
        }, token=token)

        self.assertEqual(res.status_code, 403, res.text)
        self.assertFalse(self._attendance_of(self.bob))

    def test_own_check_in_still_works(self):
        """The fix must not break the honest case the app actually sends."""
        token = self._login('alice.attendance@test.local', 'alice-test-pw-9134')

        res = self._post('/api/attendance/check-in', {
            'employee_id': self.alice.id,
            'check_in_time': '2026-08-03T08:00:00',
        }, token=token)

        self.assertEqual(res.status_code, 200, res.text)
        self.assertTrue(res.json().get('success'), res.text)
        self.assertTrue(self._attendance_of(self.alice))

    def test_employee_id_may_be_omitted_entirely(self):
        """The token identifies the employee, so the body need not repeat it."""
        token = self._login('bob.attendance@test.local', 'bob-test-pw-9134')

        res = self._post('/api/attendance/check-in', {
            'check_in_time': '2026-08-03T09:00:00',
        }, token=token)

        self.assertEqual(res.status_code, 200, res.text)
        self.assertTrue(self._attendance_of(self.bob))

    def test_no_token_is_still_rejected(self):
        res = self._post('/api/attendance/check-in', {
            'employee_id': self.alice.id,
            'check_in_time': '2026-08-03T08:00:00',
        })
        self.assertEqual(res.status_code, 401, res.text)
