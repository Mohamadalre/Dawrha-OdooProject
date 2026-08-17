# -*- coding: utf-8 -*-
"""
Attendance REST API — three endpoints:

  POST /api/login
      Body:  { "email": "...", "password": "..." }
      Returns: { token, employee_id, email, name }   or 401 on bad credentials

  POST /api/attendance/check-in          (requires Bearer token)
      Body:  { "employee_id": 24, "check_in_time": "2026-06-14T08:00:00" }

  POST /api/attendance/check-out         (requires Bearer token)
      Body:  { "employee_id": 24, "check_out_time": "2026-06-14T16:00:00" }

The time the employee sends is stored EXACTLY as-is — no UTC conversion.
The manager sees the same value in the Odoo backend.
"""
import json
import secrets
from datetime import datetime, time as dt_time, timedelta

from odoo import http
from odoo.http import request


class RecycleAttendanceAPI(http.Controller):

    # ------------------------------------------------------------------ #
    #  Generic helpers                                                     #
    # ------------------------------------------------------------------ #

    def _ok(self, data):
        return request.make_response(
            json.dumps(data, ensure_ascii=False, default=str),
            headers=[('Content-Type', 'application/json; charset=utf-8'),
                     ('Access-Control-Allow-Origin', '*')],
        )

    def _err(self, message, code=400):
        return request.make_response(
            json.dumps({'success': False, 'error': message}, ensure_ascii=False),
            headers=[('Content-Type', 'application/json; charset=utf-8'),
                     ('Access-Control-Allow-Origin', '*')],
            status=code,
        )

    @staticmethod
    def _float_to_hm(f):
        h = int(f)
        m = int(round((f - h) * 60))
        return h, m

    @staticmethod
    def _fmt(f):
        h, m = RecycleAttendanceAPI._float_to_hm(f)
        return f'{h:02d}:{m:02d}'

    @staticmethod
    def _parse_dt(s):
        """Parse ISO-like datetime string into a naive datetime object."""
        for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M'):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
        raise ValueError(f'Cannot parse datetime: {s!r}')

    # ------------------------------------------------------------------ #
    #  Token helpers  (stored in ir.config_parameter — no DB migration)  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _token_key(user_id):
        return f'recycle.api.token.{user_id}'

    def _store_token(self, user_id, token):
        ICP = request.env['ir.config_parameter'].sudo()
        ICP.set_param(self._token_key(user_id), token)

    def _validate_token(self):
        """
        Extract Bearer token from Authorization header, search ir.config_parameter
        for a matching entry, and return the corresponding res.users record or None.
        """
        auth_header = request.httprequest.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:].strip()
        else:
            token = auth_header.strip()

        if not token:
            return None

        ICP = request.env['ir.config_parameter'].sudo()
        # Search for any key matching our prefix whose value is this token
        param = ICP.search([
            ('key', 'like', 'recycle.api.token.'),
            ('value', '=', token),
        ], limit=1)

        if not param:
            return None

        try:
            user_id = int(param.key.replace('recycle.api.token.', ''))
        except (ValueError, TypeError):
            return None

        user = request.env['res.users'].sudo().browse(user_id)
        return user if user.exists() and user.active else None

    def _get_warehouse_employee(self, employee_id):
        """Return res.users record if the user is a registered warehouse employee."""
        return request.env['res.users'].sudo().search([
            ('id', '=', int(employee_id)),
            ('recycle_warehouse_id', '!=', False),
        ], limit=1)

    def _resolve_subject(self, token_user, data):
        """The employee an attendance write may touch: ONLY the token holder.

        Both routes take `employee_id` from the request body. They used to
        validate the token and then never look at it again, so any employee
        holding a valid token could punch in or out as ANY other employee just
        by changing that number — the body decided whose day was written.

        The body is kept for compatibility (the app already sends it) but is now
        only allowed to CONFIRM who the caller is; a mismatch is refused rather
        than silently honoured. Returns (employee, None) or (None, error).
        """
        employee = self._get_warehouse_employee(token_user.id)
        if not employee:
            return None, self._err(
                'Employee not found or not a registered warehouse employee.', 404)

        claimed = data.get('employee_id')
        if claimed not in (None, ''):
            try:
                claimed = int(claimed)
            except (ValueError, TypeError):
                return None, self._err('employee_id must be an integer.')
            if claimed != employee.id:
                return None, self._err(
                    'You may only record your own attendance.', 403)
        return employee, None

    # ------------------------------------------------------------------ #
    #  POST /api/login                                                     #
    # ------------------------------------------------------------------ #

    @http.route('/api/login',
                type='http', auth='none',
                methods=['POST'], csrf=False, readonly=False)
    def login(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data or b'{}')
        except (ValueError, TypeError):
            return self._err('Invalid JSON body.')

        email = (data.get('email') or data.get('login') or '').strip()
        password = data.get('password') or ''

        if not email or not password:
            return self._err('email and password are required.')

        # Find active user by login (email)
        user = request.env['res.users'].sudo().search([
            ('login', '=', email),
            ('active', '=', True),
        ], limit=1)

        if not user:
            return self._err('Invalid email or password.', 401)

        # Verify password directly via SQL + passlib (same as Odoo internaly)
        # Avoids version-specific _check_credentials() API differences
        request.env.cr.execute(
            "SELECT COALESCE(password, '') FROM res_users WHERE id = %s AND active = true",
            [user.id]
        )
        row = request.env.cr.fetchone()
        if not row or not row[0]:
            return self._err('Invalid email or password.', 401)

        try:
            valid, _ = user._crypt_context().verify_and_update(password, row[0])
        except Exception:
            valid = False

        if not valid:
            return self._err('Invalid email or password.', 401)

        # Generate a fresh token and store it in ir.config_parameter (no DB column needed)
        token = secrets.token_hex(32)
        self._store_token(user.id, token)

        return self._ok({
            'success': True,
            'token': token,
            'employee_id': user.id,
            'email': user.login,
            'name': user.name,
        })

    # ------------------------------------------------------------------ #
    #  POST /api/attendance/check-in                                       #
    # ------------------------------------------------------------------ #

    @http.route('/api/attendance/check-in',
                type='http', auth='none',
                methods=['POST'], csrf=False, readonly=False)
    def check_in(self, **kwargs):
        # ---- token auth ----
        token_user = self._validate_token()
        if not token_user:
            return self._err(
                'Missing or invalid Bearer token. '
                'Call POST /api/login first.', 401)

        # ---- parse body ----
        try:
            data = json.loads(request.httprequest.data or b'{}')
        except (ValueError, TypeError):
            return self._err('Invalid JSON body.')

        check_in_str = data.get('check_in_time') or data.get('check_in')
        if not check_in_str:
            return self._err('check_in_time is required.')

        # Whose day this is comes from the TOKEN, never from the body.
        employee, err = self._resolve_subject(token_user, data)
        if err:
            return err
        employee_id = employee.id

        try:
            check_in_dt = self._parse_dt(str(check_in_str))
        except ValueError as e:
            return self._err(str(e))

        today = check_in_dt.date()

        # Build the display string — exactly what the employee typed
        check_in_display = check_in_dt.strftime('%H:%M')

        # ---- duplicate check ----
        existing = request.env['recycle.attendance'].sudo().search([
            ('employee_user_id', '=', employee_id),
            ('date', '=', today),
        ], limit=1)

        if existing and existing.check_in_display:
            return self._err(
                f'Employee "{employee.name}" already checked in today '
                f'at {existing.check_in_display}.', 409)

        # ---- shift required ----
        shift = employee.shift_id
        if not shift:
            return self._err(
                'No work shift assigned to this employee. '
                'Contact your warehouse manager.', 400)

        # ---- late calculation (uses naive datetimes — no timezone involved) ----
        sh, sm = self._float_to_hm(shift.start_time)
        shift_start = datetime.combine(today, dt_time(sh, sm))
        late_threshold = shift_start + timedelta(minutes=shift.tolerance)

        status = 'present'
        late_minutes = 0
        warning = None

        if check_in_dt > late_threshold:
            status = 'late'
            late_minutes = int((check_in_dt - shift_start).total_seconds() / 60)
            warning = (
                f'You are {late_minutes} minutes late. '
                f'Shift started at {self._fmt(shift.start_time)}, '
                f'tolerance is {shift.tolerance} min.'
            )

        # ---- write record ----
        Att = request.env['recycle.attendance'].sudo()
        vals = {
            'check_in': check_in_dt,            # kept for work_hours computation
            'check_in_display': check_in_display,  # shown to manager — no conversion
            'status': status,
            'late_minutes': late_minutes,
        }
        if existing:
            existing.write(vals)
        else:
            Att.create({
                'employee_user_id': employee_id,
                'date': today,
                **vals,
            })

        result = {
            'success': True,
            'message': 'Check-in recorded successfully.',
            'employee_name': employee.name,
            'employee_id': employee_id,
            'date': str(today),
            'check_in_time': check_in_display,
            'shift': shift.name,
            'shift_start': self._fmt(shift.start_time),
            'shift_end': self._fmt(shift.end_time),
            'tolerance_minutes': shift.tolerance,
            'status': status,
        }
        if warning:
            result['warning'] = warning
            result['late_minutes'] = late_minutes

        return self._ok(result)

    # ------------------------------------------------------------------ #
    #  POST /api/attendance/check-out                                      #
    # ------------------------------------------------------------------ #

    @http.route('/api/attendance/check-out',
                type='http', auth='none',
                methods=['POST'], csrf=False, readonly=False)
    def check_out(self, **kwargs):
        # ---- token auth ----
        token_user = self._validate_token()
        if not token_user:
            return self._err(
                'Missing or invalid Bearer token. '
                'Call POST /api/login first.', 401)

        # ---- parse body ----
        try:
            data = json.loads(request.httprequest.data or b'{}')
        except (ValueError, TypeError):
            return self._err('Invalid JSON body.')

        check_out_str = data.get('check_out_time') or data.get('check_out')
        if not check_out_str:
            return self._err('check_out_time is required.')

        # Whose day this is comes from the TOKEN, never from the body.
        employee, err = self._resolve_subject(token_user, data)
        if err:
            return err
        employee_id = employee.id

        try:
            check_out_dt = self._parse_dt(str(check_out_str))
        except ValueError as e:
            return self._err(str(e))

        today = check_out_dt.date()

        # Build the display string — exactly what the employee typed
        check_out_display = check_out_dt.strftime('%H:%M')

        # ---- must have checked in first ----
        attendance = request.env['recycle.attendance'].sudo().search([
            ('employee_user_id', '=', employee_id),
            ('date', '=', today),
        ], limit=1)

        if not attendance or not attendance.check_in_display:
            return self._err(
                'You have not checked in today. '
                'Please call POST /api/attendance/check-in first.', 400)

        if attendance.check_out_display:
            return self._err(
                f'You have already checked out today '
                f'at {attendance.check_out_display}.', 409)

        # ---- early-leave detection ----
        shift = employee.shift_id
        early_leave_minutes = 0
        early_warning = None

        if shift:
            eh, em = self._float_to_hm(shift.end_time)
            shift_end = datetime.combine(today, dt_time(eh, em))
            if check_out_dt < shift_end:
                early_leave_minutes = int(
                    (shift_end - check_out_dt).total_seconds() / 60)
                early_warning = (
                    f'You left {early_leave_minutes} minutes early. '
                    f'Shift ends at {self._fmt(shift.end_time)}.'
                )

        # ---- work hours (uses raw datetimes — correct regardless of timezone) ----
        work_secs = (check_out_dt - attendance.check_in).total_seconds()
        work_hours = work_secs / 3600.0

        new_status = attendance.status
        if early_leave_minutes > 0:
            new_status = (
                'late_and_early' if attendance.late_minutes > 0 else 'early_leave')

        attendance.write({
            'check_out': check_out_dt,              # kept for work_hours computation
            'check_out_display': check_out_display, # shown to manager — no conversion
            'early_leave_minutes': early_leave_minutes,
            'status': new_status,
        })

        wh = int(work_hours)
        wm = int((work_hours - wh) * 60)

        result = {
            'success': True,
            'message': 'Check-out recorded successfully.',
            'employee_name': employee.name,
            'employee_id': employee_id,
            'date': str(today),
            'check_in_time': attendance.check_in_display,
            'check_out_time': check_out_display,
            'work_hours': round(work_hours, 2),
            'work_hours_display': f'{wh}h {wm}m',
            'status': new_status,
        }
        if early_warning:
            result['warning'] = early_warning
            result['early_leave_minutes'] = early_leave_minutes
        if attendance.late_minutes > 0:
            result['late_minutes'] = attendance.late_minutes

        return self._ok(result)
