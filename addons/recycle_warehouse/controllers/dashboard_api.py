# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta

from odoo import http, fields, _
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class RecycleDashboardApiController(http.Controller):

    def _get_manager_warehouse(self):
        """Return the warehouse managed by the current user, or None.

        Managers can be linked to their warehouse in two ways:
        1. warehouse.manager_user_id (assigned by the admin), or
        2. user.recycle_warehouse_id (the user's own warehouse field).
        Both point to exactly ONE warehouse, so isolation is preserved."""
        user = request.env.user
        if not (user.has_group('recycle_warehouse.group_recycle_manager')
                or user.recycle_role == 'manager'):
            return None
        wh = request.env['recycle.warehouse'].sudo().search([
            ('manager_user_id', '=', user.id)
        ], limit=1)
        if not wh and user.recycle_warehouse_id:
            wh = user.recycle_warehouse_id.sudo()
        return wh or None

    @http.route('/api/recycle/dashboard-stats', type='jsonrpc', auth='user', methods=['POST'])
    def dashboard_stats(self, **kwargs):
        """Return aggregated dashboard statistics for the admin dashboard."""
        now = request.env['recycle.warehouse']._fields.get('create_date') and request.env['recycle.warehouse'] or None

        wh_count = request.env['recycle.warehouse'].search_count([])
        emp_count = request.env['res.users'].sudo().search_count([['recycle_role', '!=', False]])
        sh_count = request.env['recycle.shipment'].search_count([])
        ord_count = request.env['recycle.order'].search_count([])
        job_count = request.env['hr.job'].search_count([])

        return {
            'warehouses': wh_count,
            'employees': emp_count,
            'shipments': sh_count,
            'orders': ord_count,
            'jobs': job_count,
        }

    @http.route('/api/manager/dashboard', type='jsonrpc', auth='user', methods=['POST'])
    def manager_dashboard(self, **kwargs):
        """Return all dashboard data scoped to the manager's warehouse,
        supporting period filtering (today/week/month), trends, insights,
        and recent records — matching the admin dashboard data shape."""
        warehouse = self._get_manager_warehouse()
        if not warehouse:
            return {'error': 'forbidden', 'warehouse_name': ''}

        period = kwargs.get('period', 'month')
        # Day boundaries in the USER's timezone, then expressed in UTC for the
        # query. create_date is stored in UTC; using the raw server clock
        # (datetime.now()) put the "today"/"month" boundary hours off for any
        # user not in the server's timezone, so the current and previous windows
        # captured the wrong records and the filter looked like it did nothing.
        import pytz
        user_tz = pytz.timezone(request.env.user.tz or 'UTC')
        now_local = pytz.utc.localize(fields.Datetime.now()).astimezone(user_tz)
        today_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)

        # Build current & previous period ranges (still in the user's tz)
        if period == 'today':
            cur_start = today_start
            prev_start = cur_start - timedelta(days=1)
            prev_end = cur_start
        elif period == 'week':
            cur_start = today_start - timedelta(days=today_start.weekday())
            prev_start = cur_start - timedelta(days=7)
            prev_end = cur_start
        else:  # month
            cur_start = today_start.replace(day=1)
            prev_start = (cur_start - timedelta(days=1)).replace(day=1)
            prev_end = cur_start

        # …then back to naive UTC strings for the ORM domain.
        def _utc_s(dt_local):
            return dt_local.astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S')
        cur_start_s = _utc_s(cur_start)
        prev_start_s = _utc_s(prev_start)
        prev_end_s = _utc_s(prev_end)

        wh_domain = [('warehouse_id', '=', warehouse.id)]
        Ship = request.env['recycle.shipment'].sudo()
        Order = request.env['recycle.order'].sudo()
        Stock = request.env['recycle.stock'].sudo()
        Users = request.env['res.users'].sudo()

        emp_domain = [
            ('recycle_warehouse_id', '=', warehouse.id),
            ('active', '=', True),
            ('recycle_role', '!=', False),
        ]

        def sc(model, domain):
            try:
                return model.search_count(domain)
            except Exception:
                return 0

        # Current period counts
        emp_cur = sc(Users, emp_domain + [('create_date', '>=', cur_start_s)])
        sh_cur  = sc(Ship,  wh_domain + [('create_date', '>=', cur_start_s)])
        ord_cur = sc(Order, wh_domain + [('create_date', '>=', cur_start_s)])
        st_cur  = sc(Stock, wh_domain + [('create_date', '>=', cur_start_s)])

        # Previous period counts
        emp_prev = sc(Users, emp_domain + [('create_date', '>=', prev_start_s), ('create_date', '<', prev_end_s)])
        sh_prev  = sc(Ship,  wh_domain + [('create_date', '>=', prev_start_s), ('create_date', '<', prev_end_s)])
        ord_prev = sc(Order, wh_domain + [('create_date', '>=', prev_start_s), ('create_date', '<', prev_end_s)])
        st_prev  = sc(Stock, wh_domain + [('create_date', '>=', prev_start_s), ('create_date', '<', prev_end_s)])

        # Employees and stock items are near-static inventory, not daily
        # activity — the headline KPI number must be the real TOTAL right
        # now (staff on the roster / distinct stock lines), not "created
        # within this period" which is ~0 most days and looks broken. The
        # period filter still drives their trend %/sparkline above via
        # emp_cur/emp_prev and st_cur/st_prev.
        emp_total = sc(Users, emp_domain)
        st_total = sc(Stock, wh_domain)

        # Running total as of the end of each of the last 7 days — a real
        # trend curve for the sparkline, not a straight line between two
        # numbers.
        #
        # `now` (naive UTC, matching how create_date is stored) is defined here
        # because the closure below reads it: it was previously undefined in this
        # method's scope, so every sparkline call raised NameError — the manager
        # dashboard's trend curves never rendered. One line fixes all of them.
        now = fields.Datetime.now()

        def last_7_days_cumulative(model, domain):
            history = []
            for i in range(6, -1, -1):
                cutoff = (now - timedelta(days=i)).replace(
                    hour=23, minute=59, second=59, microsecond=0)
                history.append(sc(model, domain + [('create_date', '<=', cutoff.strftime('%Y-%m-%d %H:%M:%S'))]))
            return history

        emp_history = last_7_days_cumulative(Users, emp_domain)
        sh_history = last_7_days_cumulative(Ship, wh_domain)
        ord_history = last_7_days_cumulative(Order, wh_domain)
        st_history = last_7_days_cumulative(Stock, wh_domain)

        # Trucks ASSIGNED to this warehouse. Near-static like the roster, so the
        # headline is the live total; the period filter still drives its trend
        # and "added this period" the same way every other card does.
        Truck = request.env['recycle.truck'].sudo()
        truck_domain = [('warehouse_id', '=', warehouse.id)]
        truck_total = sc(Truck, truck_domain)
        truck_cur = sc(Truck, truck_domain + [('create_date', '>=', cur_start_s)])
        truck_prev = sc(Truck, truck_domain + [('create_date', '>=', prev_start_s), ('create_date', '<', prev_end_s)])
        truck_history = last_7_days_cumulative(Truck, truck_domain)

        def pct(cur, prev):
            if prev == 0:
                return '+100%' if cur > 0 else '+0%'
            diff = round((cur - prev) / prev * 100)
            sign = '+' if diff >= 0 else ''
            return '%s%d%%' % (sign, diff)

        def up(cur, prev):
            return cur >= prev

        # Recent shipments (5)
        recent_ships = []
        try:
            recent_ships = Ship.search_read(
                wh_domain,
                ['id', 'name', 'state', 'received_at', 'receiver_user_id'],
                limit=3, order='id desc')
        except Exception:
            pass

        # Recent orders (5)
        recent_ords = []
        try:
            recent_ords = Order.search_read(
                wh_domain,
                ['id', 'invoice_number', 'state', 'create_date', 'source'],
                limit=3, order='id desc')
        except Exception:
            pass

        # Insights
        items = [
            ('Employees', emp_cur, '\U0001F465'),
            ('Shipments', sh_cur,  '\U0001F4E6'),
            ('Orders',  ord_cur, '\U0001F4CB'),
            ('Stock Items', st_cur, '\U0001F4E5'),
        ]
        most_active = max(items, key=lambda x: x[1])
        total_cur = sum(x[1] for x in items)
        total_prev = emp_prev + sh_prev + ord_prev + st_prev
        growth_pct = round((total_cur - total_prev) / total_prev * 100) if total_prev > 0 else (100 if total_cur > 0 else 0)

        return {
            'warehouse_id': warehouse.id,
            'warehouse_name': warehouse.name,
            'stats': {
                'employees': emp_total,
                'shipments': sh_cur,
                'orders': ord_cur,
                'stock_items': st_total,
                't_employees': pct(emp_cur, emp_prev),
                't_employees_up': up(emp_cur, emp_prev),
                't_shipments': pct(sh_cur, sh_prev),
                't_shipments_up': up(sh_cur, sh_prev),
                't_orders': pct(ord_cur, ord_prev),
                't_orders_up': up(ord_cur, ord_prev),
                't_stock_items': pct(st_cur, st_prev),
                't_stock_items_up': up(st_cur, st_prev),
                'spark_employees': emp_history,
                'spark_shipments': sh_history,
                'spark_orders': ord_history,
                'spark_stock_items': st_history,
                # Trucks assigned to this warehouse — headline total + trend + spark.
                'trucks': truck_total,
                't_trucks': pct(truck_cur, truck_prev),
                't_trucks_up': up(truck_cur, truck_prev),
                'spark_trucks': truck_history,
                # How many were ADDED within the selected period — the current-
                # period counts, surfaced as their own number so every card can
                # show what changed this period even when its headline is a
                # running total (employees / stock items).
                'added_employees': emp_cur,
                'added_shipments': sh_cur,
                'added_orders': ord_cur,
                'added_stock_items': st_cur,
                'added_trucks': truck_cur,
            },
            'insights': {
                'mostActive': most_active[0],
                'mostActiveValue': most_active[1],
                'mostActiveIcon': most_active[2],
                'growthPct': growth_pct,
                'growthUp': growth_pct >= 0,
            },
            'recent_shipments': recent_ships,
            'recent_orders': recent_ords,
        }

    # ------------------------------------------------------------------
    # Manager: Employees management (warehouse-scoped, server-side filtered)
    # ------------------------------------------------------------------
    EMPLOYEE_ROLES = ('input', 'sorting', 'output')

    def _manager_employee_domain(self, warehouse):
        return [
            ('recycle_warehouse_id', '=', warehouse.id),
            '|',
            ('recycle_role', 'in', list(self.EMPLOYEE_ROLES)),
            ('recycle_role', '=', False),
            ('recycle_deleted', '=', False),
        ]

    @http.route('/api/manager/employees', type='jsonrpc', auth='user',
                methods=['POST'])
    def manager_employees(self, **kwargs):
        """List employees of the manager's warehouse only (active + inactive)
        together with a summary. All filtering happens server-side so no
        other warehouse's data can ever leak to the client."""
        warehouse = self._get_manager_warehouse()
        if not warehouse:
            return {'error': 'forbidden', 'employees': []}

        Users = request.env['res.users'].sudo().with_context(active_test=False)
        users = Users.search(
            self._manager_employee_domain(warehouse),
            order='name asc')

        employees = [{
            'id': u.id,
            'name': u.name,
            'login': u.login,
            'email': u.email or '',
            'phone': u.phone or '',
            'role': u.recycle_role,
            'recycle_role': u.recycle_role,
            'active': u.active,
            'shift': u.shift_id.name if u.shift_id else '',
            'shift_id': u.shift_id.id if u.shift_id else False,
            'national_id': u.recycle_national_id or '',
            'recycle_warehouse_id': u.recycle_warehouse_id.id if u.recycle_warehouse_id else False,
            'create_date': u.create_date and u.create_date.strftime('%Y-%m-%d') or '',
            'performance_rating': u.recycle_performance_rating or 0,
        } for u in users]

        by_role = {r: 0 for r in self.EMPLOYEE_ROLES}
        by_role['unassigned'] = 0
        active = inactive = 0
        for e in employees:
            role_key = e['role'] if e['role'] in self.EMPLOYEE_ROLES else 'unassigned'
            by_role[role_key] = by_role.get(role_key, 0) + 1
            if e['active']:
                active += 1
            else:
                inactive += 1

        return {
            'warehouse_id': warehouse.id,
            'warehouse_name': warehouse.name,
            'employees': employees,
            'summary': {
                'total': len(employees),
                'active': active,
                'inactive': inactive,
                'by_role': by_role,
            },
        }

    def _get_manager_employee(self, warehouse, employee_id):
        """Return the employee record ONLY if it belongs to the manager's
        warehouse and is a plain employee (never a manager/admin)."""
        Users = request.env['res.users'].sudo().with_context(active_test=False)
        return Users.search(
            self._manager_employee_domain(warehouse)
            + [('id', '=', int(employee_id))], limit=1)

    ROLE_GROUP_XMLIDS = {
        'input': 'recycle_warehouse.group_recycle_input',
        'sorting': 'recycle_warehouse.group_recycle_sorting',
        'output': 'recycle_warehouse.group_recycle_output',
    }

    def _recycle_job_type_for_user(self, user):
        """The recycle_job_type of the job this user was hired through, if
        any — used to lock role assignment to a specialized position."""
        app = request.env['hr.applicant'].sudo().search(
            [('employee_user_id', '=', user.id)], limit=1, order='id desc')
        return app.recycle_job_type if app else False

    def _apply_employee_role(self, user, role):
        """Replace the employee-role groups of `user` with `role`."""
        groups_field = 'group_ids' if 'group_ids' in user._fields else 'groups_id'
        ops = []
        for xmlid in self.ROLE_GROUP_XMLIDS.values():
            grp = request.env.ref(xmlid).sudo()
            if grp in user[groups_field]:
                ops.append((3, grp.id))
        ops.append((4, request.env.ref(self.ROLE_GROUP_XMLIDS[role]).sudo().id))
        user.sudo().write({groups_field: ops, 'recycle_role': role})

    @http.route('/api/manager/warehouse-shifts', type='jsonrpc', auth='user',
                methods=['POST'])
    def manager_warehouse_shifts(self, **kwargs):
        """Shifts the manager may assign to his employees: ONLY the shifts
        the admin linked to HIS warehouse (never the whole system)."""
        warehouse = self._get_manager_warehouse()
        if not warehouse:
            return {'error': 'forbidden'}
        # Warehouse-staff shifts usable here: GLOBAL ones + those listing this
        # warehouse (scope model).
        shifts = request.env['recycle.shift'].sudo().search(
            ['&', '&', ('active', '=', True), ('shift_type', '=', 'warehouse'),
             '|', ('is_global', '=', True), ('warehouse_ids', 'in', warehouse.id)],
            order='start_time')
        return {'shifts': [{
            'id': s.id,
            'name': s.name,
            'start_time': s.start_time,
            'end_time': s.end_time,
        } for s in shifts]}

    @http.route('/api/manager/employee/update', type='jsonrpc', auth='user',
                methods=['POST'])
    def manager_employee_update(self, employee_id=None, name=None,
                                phone=None, active=None, role=None,
                                shift_id=None, warehouse_id=None, **kwargs):
        warehouse = self._get_manager_warehouse()
        if not warehouse:
            return {'error': 'forbidden'}
        emp = self._get_manager_employee(warehouse, employee_id)
        if not emp:
            return {'error': 'not_found'}
        old_role = emp.recycle_role
        import logging
        _log = logging.getLogger(__name__)
        _log.info('MANAGER UPDATE EMP %s: role=%s shift_id=%s active=%s phone=%s warehouse=%s',
                  emp.id, role, shift_id, active, phone, warehouse.id)
        vals = {}
        if phone is not None:
            vals['phone'] = (phone or '').strip()
        if active is not None:
            vals['active'] = bool(active)
        if shift_id is not None:
            if not shift_id:
                vals['shift_id'] = False
            else:
                shift = request.env['recycle.shift'].sudo().browse(
                    int(shift_id)).exists()
                if not shift:
                    _log.warning('SHIFT %s NOT FOUND for emp %s', shift_id, emp.id)
                    return {'error': 'invalid_shift'}
                # A shift is usable by this warehouse if it is GLOBAL or lists
                # this warehouse among its own (scope model).
                if not (shift.is_global or warehouse.id in shift.warehouse_ids.ids):
                    _log.warning('SHIFT %s not in manager WH %s',
                                 shift_id, warehouse.id)
                    return {'error': 'invalid_shift'}
                vals['shift_id'] = shift.id
        if vals:
            try:
                emp.sudo().write(vals)
                _log.info('EMP %s vals written: %s', emp.id, list(vals.keys()))
            except Exception as e:
                _log.error('FAILED TO WRITE EMP %s: %s', emp.id, e)
                return {'error': 'write_failed'}
        norm_role = role or False
        norm_old_role = old_role or False
        if role and role not in self.EMPLOYEE_ROLES:
            return {'error': 'invalid_role'}
        if role:
            job_type = self._recycle_job_type_for_user(emp)
            if job_type in self.EMPLOYEE_ROLES and role != job_type:
                return {'error': 'role_locked', 'locked_role': job_type}
        if role and norm_old_role != norm_role:
            try:
                self._apply_employee_role(emp, role)
                _log.info('ROLE CHANGED emp %s: %s -> %s', emp.id, old_role, role)
            except Exception as e:
                _log.error('ROLE CHANGE FAILED emp %s: %s', emp.id, e)
                return {'error': 'role_change_failed'}
        History = request.env['recycle.employee.history'].sudo()
        if norm_old_role != norm_role:
            role_labels = {
                'input': 'Input Employee', 'sorting': 'Sorting Employee',
                'output': 'Output Employee',
                'manager': 'Warehouse Manager', False: 'Not Assigned', '': 'Not Assigned',
            }
            History.log_change(
                emp, 'role',
                old_role=role_labels.get(old_role, old_role),
                new_role=role_labels.get(role, role),
                changed_by=request.env.user)
        _log.info('EMP %s FINAL: role=%s shift=%s active=%s phone=%s',
                  emp.id, emp.recycle_role, emp.shift_id.id if emp.shift_id else False,
                  emp.active, emp.phone or '')
        return {'ok': True, 'id': emp.id, 'name': emp.name,
                'active': emp.active, 'phone': emp.phone or '',
                'role': emp.recycle_role,
                'shift_id': emp.shift_id.id if emp.shift_id else False,
                'shift': emp.shift_id.name if emp.shift_id else '',
                'warehouse': emp.recycle_warehouse_id.name or ''}

    @http.route('/api/manager/employee/rate', type='jsonrpc', auth='user',
                methods=['POST'])
    def manager_employee_rate(self, employee_id=None, rating=None, **kwargs):
        """Warehouse manager rates one of their own employees 1-5 stars,
        indicating performance/efficiency. 0 clears the rating."""
        warehouse = self._get_manager_warehouse()
        if not warehouse:
            return {'error': 'forbidden'}
        emp = self._get_manager_employee(warehouse, employee_id)
        if not emp:
            return {'error': 'not_found'}
        try:
            rating = int(rating)
        except (TypeError, ValueError):
            return {'error': 'invalid_rating'}
        if not (0 <= rating <= 5):
            return {'error': 'invalid_rating'}
        emp.sudo().write({
            'recycle_performance_rating': rating,
            'recycle_performance_rated_by': request.env.user.id,
            'recycle_performance_rated_at': fields.Datetime.now(),
        })
        return {'ok': True, 'id': emp.id, 'performance_rating': rating}

    def _get_manager_order(self, warehouse, order_id):
        """The order must exist AND belong to the manager's own warehouse."""
        try:
            order = request.env['recycle.order'].sudo().browse(int(order_id))
        except (TypeError, ValueError):
            return None
        if not order.exists() or order.warehouse_id.id != warehouse.id:
            return None
        return order

    @http.route('/api/manager/order/approve', type='jsonrpc', auth='user',
                methods=['POST'])
    def manager_order_approve(self, order_id=None, **kwargs):
        """Release an API-created order to the output employees' queue."""
        warehouse = self._get_manager_warehouse()
        if not warehouse:
            return {'error': 'forbidden'}
        order = self._get_manager_order(warehouse, order_id)
        if not order:
            return {'error': 'not_found'}
        try:
            # Run as the real manager: _is_supervisor() checks their group,
            # they hold write access on orders, and the chatter entry names
            # them (not OdooBot).
            order.with_user(request.env.user).action_manager_approve()
        except UserError as e:
            return {'error': str(e)}
        return {'ok': True, 'id': order.id, 'manager_approval': 'approved'}

    @http.route('/api/manager/order/reject', type='jsonrpc', auth='user',
                methods=['POST'])
    def manager_order_reject(self, order_id=None, reason=None, **kwargs):
        """Reject an API-created order: output employees never see it."""
        warehouse = self._get_manager_warehouse()
        if not warehouse:
            return {'error': 'forbidden'}
        order = self._get_manager_order(warehouse, order_id)
        if not order:
            return {'error': 'not_found'}
        try:
            order.with_user(request.env.user).action_manager_reject(reason=reason)
        except UserError as e:
            return {'error': str(e)}
        return {'ok': True, 'id': order.id, 'manager_approval': 'rejected'}

    @http.route('/api/admin/order/reassign', type='jsonrpc', auth='user',
                methods=['POST'])
    def admin_order_reassign(self, order_id=None, warehouse_id=None, **kwargs):
        """Move one part of a SPLIT order to another warehouse.

        The administrator's alone: only they see every part of a split, so only
        they can re-route one. The model enforces the rest — split-only, still
        pending, the target holds the quantity, and the order is never grown.
        """
        if not self._test_admin():
            return {'error': 'forbidden'}
        if not order_id or not warehouse_id:
            return {'error': 'missing_parameters'}
        order = request.env['recycle.order'].sudo().browse(int(order_id))
        if not order.exists():
            return {'error': 'not_found'}
        try:
            order.action_admin_reassign_warehouse(int(warehouse_id))
        except UserError as e:
            return {'error': str(e)}
        return {
            'ok': True,
            'id': order.id,
            'warehouse_id': order.warehouse_id.id,
            'warehouse': order.warehouse_id.name,
        }

    @http.route('/api/manager/awaiting-role', type='jsonrpc', auth='user',
                methods=['POST'])
    def manager_awaiting_role(self, **kwargs):
        """Return employees in the manager's warehouse who have no role assigned."""
        warehouse = self._get_manager_warehouse()
        if not warehouse:
            return {'error': 'forbidden', 'employees': []}

        Users = request.env['res.users'].sudo().with_context(active_test=False)
        employees = Users.search([
            ('recycle_warehouse_id', '=', warehouse.id),
            ('recycle_role', '=', False),
            ('active', '=', True),
            ('recycle_deleted', '=', False),
            ('share', '=', False),
        ], order='name asc')

        result = []
        for u in employees:
            job_type = self._recycle_job_type_for_user(u)
            result.append({
                'id': u.id,
                'name': u.name,
                'login': u.login,
                'email': u.email or '',
                'phone': u.phone or '',
                'role': u.recycle_role or '',
                'recycle_warehouse_id': u.recycle_warehouse_id.id,
                'warehouse': u.recycle_warehouse_id.name or '',
                'create_date': u.create_date.strftime('%Y-%m-%d') if u.create_date else '',
                'type': 'awaiting_role',
                'job_type': job_type or 'employee',
                'locked_role': job_type if job_type in self.EMPLOYEE_ROLES else False,
            })

        return {'employees': result}

    @http.route('/api/manager/notification/send', type='jsonrpc', auth='user',
                methods=['POST'])
    def manager_send_notification(self, user_id=None, title=None,
                                  message=None, type='info', **kwargs):
        """Send a notification to a specific user."""
        warehouse = self._get_manager_warehouse()
        if not warehouse:
            return {'error': 'forbidden'}
        if not user_id or not title:
            return {'error': 'missing_params'}
        Notif = request.env['recycle.notification'].sudo()
        Notif._notify_user(
            request.env['res.users'].sudo().browse(int(user_id)),
            title, message, type)
        return {'ok': True}

    @http.route('/api/manager/employee/create', type='jsonrpc', auth='user',
                methods=['POST'])
    def manager_employee_create(self, name=None, login=None, email=None,
                                phone=None, role=None, national_id=None,
                                **kwargs):
        """Create a new employee account inside the manager's OWN warehouse.
        The warehouse is forced server-side; the role must be one of the
        four employee roles (a manager can never create another manager).

        No password is set here — a 'Set Password' email is sent instead
        so the employee can choose their own password via a secure link."""
        warehouse = self._get_manager_warehouse()
        if not warehouse:
            return {'error': 'forbidden'}

        import logging
        _log = logging.getLogger(__name__)

        name = (name or '').strip()
        email = (email or '').strip()
        role = (role or '').strip()

        national_id = (national_id or '').strip()

        if not name:
            return {'error': 'name_required'}
        if not email:
            return {'error': 'email_required'}
        if role not in self.EMPLOYEE_ROLES:
            return {'error': 'invalid_role'}

        # Use email as login (auto-generate)
        login = email.lower()

        Users = request.env['res.users'].sudo().with_context(active_test=False)
        if Users.search_count([('login', '=', login)]):
            return {'error': 'login_exists'}
        # National ID must be unique across ALL users
        if national_id and Users.search_count(
                [('recycle_national_id', '=', national_id)]):
            return {'error': 'national_id_exists'}

        group = request.env.ref(self.ROLE_GROUP_XMLIDS[role]).sudo()
        base_group = request.env.ref('base.group_user').sudo()

        groups_field = 'group_ids' if 'group_ids' in Users._fields else 'groups_id'
        user = Users.with_context(no_reset_password=True).create({
            'name': name,
            'login': login,
            'email': email,
            'phone': (phone or '').strip(),
            'recycle_role': role,
            'recycle_warehouse_id': warehouse.id,
            'recycle_national_id': national_id,
            groups_field: [(6, 0, [base_group.id, group.id])],
        })

        # Send "Set Password" email using Odoo's built-in mechanism
        email_sent = False
        try:
            user.sudo().action_reset_password()
            email_sent = True
            _log.info('Set password email sent to %s for user %s', email, user.login)
        except Exception as e:
            _log.error('Failed to send set password email to %s: %s', email, e)
            # Fallback: try with our custom template
            try:
                template = request.env.ref(
                    'recycle_warehouse.email_template_set_password', raise_if_not_found=False)
                if template and email:
                    template.sudo().with_context(
                        lang=user.lang or 'en',
                    ).send_mail(user.id, force_send=True, raise_exception=True)
                    email_sent = True
                    _log.info('Fallback: custom set password email sent to %s', email)
            except Exception as e2:
                    _log.error('Fallback email also failed for %s: %s', email, e2)

        role_labels = {
            'input': 'Input Employee', 'sorting': 'Sorting Employee',
            'output': 'Output Employee',
        }
        History = request.env['recycle.employee.history'].sudo()
        History.log_change(
            user, 'direct_addition',
            new_role=role_labels.get(role, role),
            changed_by=request.env.user,
            note='Direct addition by manager')

        return {'ok': True, 'id': user.id, 'name': user.name,
                'email_sent': email_sent}

    # ------------------------------------------------------------------
    # Admin: Add another Administrator
    # ------------------------------------------------------------------
    @http.route('/api/admin/create-administrator', type='jsonrpc', auth='user',
                methods=['POST'])
    def admin_create_administrator(self, name=None, email=None, **kwargs):
        """Create a new user with full Administrator permissions. Only an
        existing admin can do this. No warehouse/role picker — the role is
        always 'admin', matching group_recycle_admin."""
        if not request.env.user.has_group('recycle_warehouse.group_recycle_admin'):
            return {'error': 'forbidden'}

        import logging
        _log = logging.getLogger(__name__)

        name = (name or '').strip()
        email = (email or '').strip()
        if not name:
            return {'error': 'name_required'}
        if not email:
            return {'error': 'email_required'}

        login = email.lower()
        Users = request.env['res.users'].sudo().with_context(active_test=False)
        if Users.search_count([('login', '=', login)]):
            return {'error': 'login_exists'}

        admin_group = request.env.ref('recycle_warehouse.group_recycle_admin').sudo()
        base_group = request.env.ref('base.group_user').sudo()
        groups_field = 'group_ids' if 'group_ids' in Users._fields else 'groups_id'

        user = Users.with_context(no_reset_password=True).create({
            'name': name,
            'login': login,
            'email': email,
            'recycle_role': 'admin',
            groups_field: [(6, 0, [base_group.id, admin_group.id])],
        })

        email_sent = False
        try:
            user.sudo().action_reset_password()
            email_sent = True
            _log.info('Set password email sent to %s for new admin %s', email, user.login)
        except Exception as e:
            _log.error('Failed to send set password email to %s: %s', email, e)

        History = request.env['recycle.employee.history'].sudo()
        History.log_change(
            user, 'direct_addition',
            new_role='Administrator',
            changed_by=request.env.user,
            note='Administrator added by %s' % request.env.user.name)

        return {'ok': True, 'id': user.id, 'name': user.name,
                'email_sent': email_sent}

    # ------------------------------------------------------------------
    # Admin: Add an employee (warehouse staff, or a warehouse manager)
    # ------------------------------------------------------------------
    # The roles an ADMIN may hand out here. Wider than the manager's own list
    # (`EMPLOYEE_ROLES`) by exactly one: an admin may appoint a warehouse
    # manager, and a manager may not — otherwise a manager could quietly make
    # themselves a peer in every other warehouse.
    ADMIN_CREATABLE_ROLES = ('input', 'sorting', 'output', 'manager')

    ADMIN_ROLE_GROUP_XMLIDS = {
        'input': 'recycle_warehouse.group_recycle_input',
        'sorting': 'recycle_warehouse.group_recycle_sorting',
        'output': 'recycle_warehouse.group_recycle_output',
        'manager': 'recycle_warehouse.group_recycle_manager',
    }

    ADMIN_ROLE_LABELS = {
        'input': 'Reception Employee',
        'sorting': 'Sorting Employee',
        'output': 'Output Employee',
        'manager': 'Warehouse Manager',
    }

    @http.route('/api/admin/employee/create', type='jsonrpc', auth='user',
                methods=['POST'])
    def admin_employee_create(self, name=None, email=None, phone=None,
                              national_id=None, role=None, warehouse_id=None,
                              **kwargs):
        """Create warehouse staff, or a warehouse manager, in any warehouse.

        The manager case carries a rule the others do not: ONE manager per
        warehouse, in both directions.

          * a warehouse that already has a manager cannot be given a second —
            two people each believing the site is theirs is how a decision gets
            taken twice and reversed once;
          * and a manager runs one warehouse, because every manager screen
            scopes on `recycle_warehouse_id`, a single field. A person holding
            two warehouses would see one of them and be accountable for both.

        Both are checked HERE, before the account exists, so the refusal names
        the conflict instead of leaving a half-made user behind.

        National ID and email are unique across every person in the system —
        staff, delivery drivers, collectors and applicants alike. That is
        enforced by `recycle.identity` (a UNIQUE index, not a search), which
        `res.users.create` goes through on its own; this only turns its
        ValidationError into an answer the screen can show.
        """
        if not request.env.user.has_group('recycle_warehouse.group_recycle_admin'):
            return {'error': 'forbidden'}

        import logging
        _log = logging.getLogger(__name__)

        name = (name or '').strip()
        email = (email or '').strip()
        phone = (phone or '').strip()
        national_id = (national_id or '').strip()
        role = (role or '').strip()

        if not name:
            return {'error': 'name_required'}
        if not email:
            return {'error': 'email_required'}
        if role not in self.ADMIN_CREATABLE_ROLES:
            return {'error': 'invalid_role'}
        if not warehouse_id:
            return {'error': 'warehouse_required'}

        Warehouse = request.env['recycle.warehouse'].sudo()
        warehouse = Warehouse.browse(int(warehouse_id)).exists()
        if not warehouse:
            return {'error': 'warehouse_not_found'}
        # A closing or closed site takes no new staff: the whole point of the
        # state is that work stops arriving there.
        if warehouse.state != 'active':
            return {'error': 'warehouse_not_active',
                    'warehouse': warehouse.name}

        if role == 'manager' and warehouse.manager_user_id:
            return {'error': 'warehouse_has_manager',
                    'warehouse': warehouse.name,
                    'manager': warehouse.manager_user_id.name}

        login = email.lower()
        Users = request.env['res.users'].sudo().with_context(active_test=False)
        if Users.search_count([('login', '=', login)]):
            return {'error': 'login_exists'}

        group = request.env.ref(self.ADMIN_ROLE_GROUP_XMLIDS[role]).sudo()
        base_group = request.env.ref('base.group_user').sudo()
        groups_field = 'group_ids' if 'group_ids' in Users._fields else 'groups_id'

        try:
            # Savepoint so a refused identity leaves the request usable — the
            # screen shows the reason rather than a 500.
            with request.env.cr.savepoint():
                user = Users.with_context(no_reset_password=True).create({
                    'name': name,
                    'login': login,
                    'email': email,
                    'phone': phone,
                    'recycle_role': role,
                    'recycle_warehouse_id': warehouse.id,
                    'recycle_national_id': national_id,
                    groups_field: [(6, 0, [base_group.id, group.id])],
                })
                if role == 'manager':
                    # Written through the warehouse, which is what `_sync_manager`
                    # and the backend ping both hang off — setting the user's
                    # field alone would leave the warehouse with no manager and
                    # the user claiming one.
                    warehouse.write({'manager_user_id': user.id})
        except ValidationError as exc:
            message = exc.args[0] if exc.args else ''
            _log.info('Employee creation refused: %s', message)
            # The PARTS travel too, not only the finished English sentence.
            #
            # The dashboard takes its language from the browser rather than from
            # `res.users.lang`, so anything `_()` builds here is resolved against
            # the wrong language and lands in English however the screen is set.
            # This was the one refusal on that form that carried a detail worth
            # reading — whose national ID it is — and so the one that was always
            # untranslated. Sending the parts lets the client say the same
            # sentence in its own language without losing the detail.
            Guard = request.env['recycle.identity'].sudo()
            details = {}
            for kind, raw in (('national_id', national_id), ('email', login)):
                if not raw:
                    continue
                found = Guard.conflict_details(kind, raw)
                if found.get('owner_label'):
                    details = found
                    break
            return {
                'error': 'identity_taken',
                'message': message,
                'conflict': details,
            }

        email_sent = False
        try:
            # No password is set here. The employee chooses their own through a
            # signed link, so nobody — including the admin who created them —
            # ever knows it.
            user.sudo().action_reset_password()
            email_sent = True
        except Exception as exc:                      # noqa: BLE001
            _log.error('Set-password email failed for %s: %s', email, exc)

        request.env['recycle.employee.history'].sudo().log_change(
            user, 'direct_addition',
            new_role=self.ADMIN_ROLE_LABELS.get(role, role),
            changed_by=request.env.user,
            note='Added by the administrator to %s' % warehouse.name)

        return {'ok': True, 'id': user.id, 'name': user.name,
                'role': role, 'warehouse': warehouse.name,
                'email_sent': email_sent}

    # ------------------------------------------------------------------
    # Admin: Employee Update (with history logging)
    # ------------------------------------------------------------------
    @http.route('/api/admin/employee/update', type='jsonrpc', auth='user',
                methods=['POST'])
    def admin_employee_update(self, employee_id=None, name=None, login=None,
                              email=None, phone=None, active=None, role=None,
                              shift_id=None, warehouse_id=None, **kwargs):
        """Update employee fields (name, login, email, phone, active, role,
        shift, warehouse) with full history logging."""
        if not request.env.user.has_group('recycle_warehouse.group_recycle_admin'):
            return {'error': 'forbidden'}
        if not employee_id:
            return {'error': 'missing_employee'}
        Users = request.env['res.users'].sudo().with_context(active_test=False)
        emp = Users.browse(int(employee_id))
        if not emp.exists():
            return {'error': 'not_found'}
        import logging
        _log = logging.getLogger(__name__)
        old_role = emp.recycle_role
        old_wh = emp.recycle_warehouse_id
        _log.info('ADMIN UPDATE EMPLOYEE %s: old_role=%s, new_role_param=%s', emp.id, old_role, role)
        vals = {}
        if name is not None:
            vals['name'] = (name or '').strip()
        if login is not None:
            vals['login'] = (login or '').strip()
        if email is not None:
            vals['email'] = (email or '').strip()
        if phone is not None:
            vals['phone'] = (phone or '').strip()
        if active is not None:
            vals['active'] = bool(active)
        if shift_id is not None:
            if not shift_id:
                vals['shift_id'] = False
            else:
                shift = request.env['recycle.shift'].sudo().browse(
                    int(shift_id)).exists()
                if shift:
                    vals['shift_id'] = shift.id
        new_wh = False
        if warehouse_id is not None:
            if warehouse_id:
                new_wh = request.env['recycle.warehouse'].sudo().browse(
                    int(warehouse_id)).exists()
                if new_wh:
                    vals['recycle_warehouse_id'] = new_wh.id
            else:
                vals['recycle_warehouse_id'] = False
        if vals:
            emp.sudo().write(vals)
        norm_role = role or False
        norm_old_role = old_role or False
        if role is not None and norm_role != norm_old_role:
            groups_field = 'group_ids' if 'group_ids' in emp._fields else 'groups_id'
            ROLE_GROUP_XMLIDS = {
                'input': 'recycle_warehouse.group_recycle_input',
                'sorting': 'recycle_warehouse.group_recycle_sorting',
                'output': 'recycle_warehouse.group_recycle_output',
                'manager': 'recycle_warehouse.group_recycle_manager',
            }
            ops = []
            for xmlid in ROLE_GROUP_XMLIDS.values():
                grp = request.env.ref(xmlid).sudo()
                if grp in emp[groups_field]:
                    ops.append((3, grp.id))
            if role in ROLE_GROUP_XMLIDS:
                ops.append((4, request.env.ref(ROLE_GROUP_XMLIDS[role]).sudo().id))
            emp.sudo().write({groups_field: ops, 'recycle_role': role or False})
        if role == 'manager' and new_wh:
            if old_wh and old_wh.id != new_wh.id:
                if old_wh.manager_user_id and old_wh.manager_user_id.id == emp.id:
                    old_wh.sudo().write({'manager_user_id': False})
            if not new_wh.manager_user_id or new_wh.manager_user_id.id != emp.id:
                new_wh.sudo().write({'manager_user_id': emp.id})
        elif old_role == 'manager' and old_wh:
            if old_wh.manager_user_id and old_wh.manager_user_id.id == emp.id:
                old_wh.sudo().write({'manager_user_id': False})
        History = request.env['recycle.employee.history'].sudo()
        role_labels = {
            'input': 'Input Employee', 'sorting': 'Sorting Employee',
            'output': 'Output Employee',
            'manager': 'Warehouse Manager', False: 'Not Assigned', '': 'Not Assigned',
        }
        if role is not None and norm_old_role != norm_role:
            rec = History.log_change(
                emp, 'role',
                old_role=role_labels.get(old_role, old_role),
                new_role=role_labels.get(role, role),
                changed_by=request.env.user)
            _log.info('ADMIN HISTORY ROLE LOGGED: id=%s old=%s new=%s', rec.id, old_role, role)
        old_wh_name = old_wh.name if old_wh else ''
        new_wh_name = emp.recycle_warehouse_id.name if emp.recycle_warehouse_id else ''
        if warehouse_id is not None and old_wh_name != new_wh_name:
            History.log_change(
                emp, 'warehouse',
                old_warehouse=old_wh_name or 'None',
                new_warehouse=new_wh_name or 'None',
                changed_by=request.env.user)
        return {'ok': True, 'id': emp.id, 'name': emp.name,
                'login': emp.login, 'email': emp.email or '',
                'active': emp.active, 'phone': emp.phone or '',
                'role': emp.recycle_role,
                'recycle_role': emp.recycle_role,
                'shift_id': emp.shift_id.id if emp.shift_id else False,
                'shift': emp.shift_id.name if emp.shift_id else '',
                'warehouse_id': emp.recycle_warehouse_id.id if emp.recycle_warehouse_id else False,
                'warehouse': emp.recycle_warehouse_id.name or ''}

    # ------------------------------------------------------------------
    # Admin: Send Notification
    # ------------------------------------------------------------------
    @http.route('/api/admin/notification/send', type='jsonrpc', auth='user',
                methods=['POST'])
    def admin_send_notification(self, user_id=None, title=None,
                                message=None, type='info', **kwargs):
        """Send a notification to a specific user (admin)."""
        if not request.env.user.has_group('recycle_warehouse.group_recycle_admin'):
            return {'error': 'forbidden'}
        if not user_id or not title:
            return {'error': 'missing_params'}
        Notif = request.env['recycle.notification'].sudo()
        Notif._notify_user(
            request.env['res.users'].sudo().browse(int(user_id)),
            title, message, type)
        return {'ok': True}

    # ------------------------------------------------------------------
    # Admin: Unassigned Employees Management
    # ------------------------------------------------------------------
    @http.route('/api/admin/unassigned-employees', type='jsonrpc', auth='user',
                methods=['POST'])
    def admin_unassigned_employees(self, **kwargs):
        """Return employees who have no role assigned (with or without warehouse)."""
        if not request.env.user.has_group('recycle_warehouse.group_recycle_admin'):
            return {'error': 'forbidden', 'employees': []}

        Users = request.env['res.users'].sudo().with_context(active_test=False)
        employees = Users.search([
            ('active', '=', True),
            ('recycle_role', '=', False),
            ('recycle_deleted', '=', False),
            ('share', '=', False),
        ], order='name asc')

        result = [{
            'id': u.id,
            'name': u.name,
            'login': u.login,
            'email': u.email or '',
            'phone': u.phone or '',
            'role': u.recycle_role or '',
            'recycle_warehouse_id': u.recycle_warehouse_id.id if u.recycle_warehouse_id else False,
            'warehouse': u.recycle_warehouse_id.name or '',
            'national_id': u.recycle_national_id or '',
            'create_date': u.create_date.strftime('%Y-%m-%d') if u.create_date else '',
            'prev_warehouse': u.recycle_prev_warehouse_id.name if u.recycle_prev_warehouse_id else '',
            'prev_role': u.recycle_prev_role or '',
            'has_warehouse': bool(u.recycle_warehouse_id),
            'has_role': bool(u.recycle_role),
        } for u in employees]

        return {'employees': result}

    @http.route('/api/admin/warehouses-without-manager', type='jsonrpc',
                auth='user', methods=['POST'])
    def admin_warehouses_without_manager(self, **kwargs):
        """Return all active warehouses for assignment."""
        if not request.env.user.has_group('recycle_warehouse.group_recycle_admin'):
            return {'error': 'forbidden', 'warehouses': []}

        warehouses = request.env['recycle.warehouse'].sudo().search([
            ('active', '=', True),
        ], order='name asc')

        result = [{
            'id': wh.id,
            'name': wh.name,
            'code': wh.code or '',
            'governorate': wh.governorate or '',
            'has_manager': bool(wh.manager_user_id),
            'manager_name': wh.manager_user_id.name or '',
        } for wh in warehouses]

        return {'warehouses': result}

    @http.route('/api/admin/assign-warehouse', type='jsonrpc', auth='user',
                methods=['POST'])
    def admin_assign_warehouse(self, employee_id=None, warehouse_id=None,
                                **kwargs):
        """Assign a warehouse to an unassigned employee."""
        if not request.env.user.has_group('recycle_warehouse.group_recycle_admin'):
            return {'error': 'forbidden'}
        if not employee_id or not warehouse_id:
            return {'error': 'missing_params'}

        Users = request.env['res.users'].sudo().with_context(active_test=False)
        emp = Users.browse(int(employee_id))
        if not emp.exists():
            return {'error': 'employee_not_found'}

        wh = request.env['recycle.warehouse'].sudo().browse(int(warehouse_id))
        if not wh.exists():
            return {'error': 'warehouse_not_found'}

        old_wh = emp.recycle_warehouse_id
        old_role = emp.recycle_role

        emp.sudo().write({'recycle_warehouse_id': wh.id})

        role_labels = {
            'admin': 'Administration', 'manager': 'Warehouse Manager',
            'input': 'Input Employee', 'sorting': 'Sorting Employee',
            'output': 'Output Employee',
        }
        History = request.env['recycle.employee.history'].sudo()
        History.log_change(
            emp, 'assignment_start',
            new_role='Pending (awaiting manager assignment)' if not old_role else role_labels.get(old_role, old_role),
            new_warehouse=wh.name,
            changed_by=request.env.user,
            note='Warehouse assigned by admin. Awaiting role assignment.')

        manager = wh.manager_user_id
        manager_notified = False
        if manager:
            Notif = request.env['recycle.notification'].sudo()
            Notif._notify_user(
                manager,
                'New Employee Needs Role Assignment',
                '%s has been assigned to %s. '
                'Please assign a role (Input/Sorting/Output) '
                'to this employee.' % (emp.name, wh.name),
                notif_type='role_assignment')
            manager_notified = True

        return {
            'ok': True,
            'employee_id': emp.id,
            'warehouse_id': wh.id,
            'warehouse_name': wh.name,
            'manager_notified': manager_notified,
        }

    @http.route('/api/admin/assign-role-type', type='jsonrpc', auth='user',
                methods=['POST'])
    def admin_assign_role_type(self, employee_id=None, role_type=None,
                                warehouse_id=None, **kwargs):
        """Assign a role type to an unassigned employee.

        role_type: 'manager' | 'employee'
        - manager: becomes warehouse manager immediately.
        - employee: assigned to warehouse, manager gets notification to assign role.
        """
        if not request.env.user.has_group('recycle_warehouse.group_recycle_admin'):
            return {'error': 'forbidden'}
        if not employee_id or not role_type:
            return {'error': 'missing_params'}
        if role_type not in ('manager', 'employee'):
            return {'error': 'invalid_role_type'}

        Users = request.env['res.users'].sudo().with_context(active_test=False)
        emp = Users.browse(int(employee_id))
        if not emp.exists():
            return {'error': 'employee_not_found'}

        wh = None
        if warehouse_id:
            wh = request.env['recycle.warehouse'].sudo().browse(int(warehouse_id))
            if not wh.exists():
                return {'error': 'warehouse_not_found'}
        else:
            wh = emp.recycle_warehouse_id
            if not wh:
                return {'error': 'no_warehouse_assigned'}

        old_role = emp.recycle_role
        role_labels = {
            'admin': 'Administration', 'manager': 'Warehouse Manager',
            'input': 'Input Employee', 'sorting': 'Sorting Employee',
            'output': 'Output Employee',
        }

        ROLE_GROUP_XMLIDS = {
            'input': 'recycle_warehouse.group_recycle_input',
            'sorting': 'recycle_warehouse.group_recycle_sorting',
            'output': 'recycle_warehouse.group_recycle_output',
            'manager': 'recycle_warehouse.group_recycle_manager',
        }

        if role_type == 'manager':
            if wh.manager_user_id and wh.manager_user_id.id != emp.id:
                return {'error': 'warehouse_has_manager'}

            groups_field = 'group_ids' if 'group_ids' in emp._fields else 'groups_id'
            ops = []
            for xmlid in ROLE_GROUP_XMLIDS.values():
                grp = request.env.ref(xmlid).sudo()
                if grp in emp[groups_field]:
                    ops.append((3, grp.id))
            ops.append((4, request.env.ref(ROLE_GROUP_XMLIDS['manager']).sudo().id))

            emp.sudo().write({
                groups_field: ops,
                'recycle_role': 'manager',
                'recycle_warehouse_id': wh.id,
            })
            wh.sudo().write({'manager_user_id': emp.id})

            History = request.env['recycle.employee.history'].sudo()
            History.log_change(
                emp, 'role',
                old_role=role_labels.get(old_role, old_role or 'Not Assigned'),
                new_role='Warehouse Manager',
                new_warehouse=wh.name,
                changed_by=request.env.user,
                note='Assigned as warehouse manager by admin')

            return {
                'ok': True,
                'role': 'manager',
                'warehouse_name': wh.name,
                'message': '%s is now the manager of %s.' % (emp.name, wh.name),
            }

        else:
            emp.sudo().write({'recycle_warehouse_id': wh.id})

            manager = wh.manager_user_id
            if manager:
                Notif = request.env['recycle.notification'].sudo()
                Notif._notify_user(
                    manager,
                    'New Employee Assignment',
                    '%s has been assigned to %s as an employee. '
                    'Please assign a role (Input/Sorting/Output) '
                    'to this employee.' % (emp.name, wh.name),
                    notif_type='role_assignment')

            History = request.env['recycle.employee.history'].sudo()
            History.log_change(
                emp, 'assignment_start',
                new_role='Pending (awaiting manager assignment)',
                new_warehouse=wh.name,
                changed_by=request.env.user,
                note='Assigned as employee. Manager needs to assign role.')

            msg = '%s has been assigned to %s.' % (emp.name, wh.name)
            if manager:
                msg += ' Notification sent to manager %s.' % manager.name
            else:
                msg += ' Warning: This warehouse has no manager yet.'

            return {
                'ok': True,
                'role': 'employee',
                'warehouse_name': wh.name,
                'manager_notified': bool(manager),
                'message': msg,
            }

    @http.route('/api/admin/employee-history', type='jsonrpc', auth='user',
                methods=['POST'])
    def admin_employee_history(self, employee_id=None, **kwargs):
        """Return the full change history for an employee."""
        if not request.env.user.has_group('recycle_warehouse.group_recycle_admin'):
            return {'error': 'forbidden', 'history': []}
        if not employee_id:
            return {'error': 'missing_params', 'history': []}

        History = request.env['recycle.employee.history'].sudo()
        records = History.search([
            ('user_id', '=', int(employee_id)),
        ], order='create_date desc', limit=300)

        result = [{
            'id': r.id,
            'change_type': r.change_type,
            'old_role': r.old_role or '',
            'new_role': r.new_role or '',
            'old_warehouse': r.old_warehouse or '',
            'new_warehouse': r.new_warehouse or '',
            'changed_by': r.changed_by.name if r.changed_by else '',
            'note': r.note or '',
            'create_date': r.create_date.strftime('%Y-%m-%d %H:%M') if r.create_date else '',
            'assignment_start_date': r.assignment_start_date.strftime('%Y-%m-%d %H:%M') if r.assignment_start_date else '',
            'assignment_end_date': r.assignment_end_date.strftime('%Y-%m-%d %H:%M') if r.assignment_end_date else '',
        } for r in records]

        return {'history': result}

    # ------------------------------------------------------------------
    # TEMPORARY Postman/test routes (will be replaced by the real backend)
    # Admin-only. JSON-RPC body: {"jsonrpc":"2.0","method":"call","params":{...}}
    # ------------------------------------------------------------------
    def _test_admin(self):
        return request.env.user.has_group('recycle_warehouse.group_recycle_admin')

    @http.route('/api/test/create-shipment', type='jsonrpc', auth='user', methods=['POST'])
    def test_create_shipment(self, warehouse_id=None, driver_name=None,
                             priority=10, truck_info=None, truck_serial_number=None,
                             dispatch_date=None, expected_lines=None, **kw):
        """TEMPORARY Postman route simulating the backend sending a new
        shipment. Will be removed once the real NestJS integration exists —
        see /api/receiving/shipment-info for the read side of that seam.

        There is no total-weight field to fill in by hand: the declared
        weight is derived from the material lines below (each material's
        unit of measure is read from the product, not chosen per line).

        Body (JSON):
        {
          "warehouse_id": 1,
          "driver_name": "Ahmad",
          "priority": 10,
          "truck_info": "Truck-42",
          "truck_serial_number": "SN-778812",
          "dispatch_date": "2026-07-10 08:00:00",
          "expected_lines": [
            {"product_id": 5, "qty": 180},
            {"product_id": 7, "qty": 50}
          ]
        }
        """
        if not self._test_admin():
            return {'error': 'forbidden'}
        if not warehouse_id or not driver_name:
            return {'error': 'warehouse_id and driver_name are required'}
        if not expected_lines or not isinstance(expected_lines, list):
            return {'error': '"expected_lines" is required and must be a non-empty list '
                              '(each product with its declared quantity).'}

        vals = {
            'warehouse_id': int(warehouse_id),
            'driver_name': driver_name,
            'priority': int(priority or 10),
        }
        if truck_info:
            vals['truck_info'] = truck_info
        if truck_serial_number:
            vals['truck_serial_number'] = truck_serial_number
        if dispatch_date:
            vals['dispatch_date'] = dispatch_date

        line_vals = []
        kg_total = 0.0
        Product = request.env['recycle.product'].sudo()
        for line in expected_lines:
            if not isinstance(line, dict):
                return {'error': 'Each expected line must be an object.'}
            product_id = line.get('product_id')
            qty = line.get('qty')
            if not product_id or not qty or float(qty) <= 0:
                return {'error': 'Each expected line needs "product_id" and a '
                                  'positive "qty".'}
            product = Product.browse(int(product_id)).exists()
            if not product:
                return {'error': 'Product %s not found.' % product_id}
            qty = float(qty)
            line_vals.append((0, 0, {
                'product_id': product.id, 'expected_qty': qty}))
            # Units are mirrored from the backend, which identifies them by
            # CODE ('KG') — the name is a localised label ('Kilogram' /
            # 'كيلوغرام') and must never be matched on.
            if (product.uom_id.code or '').strip().upper() == 'KG':
                kg_total += qty
        vals['expected_line_ids'] = line_vals
        # Declared weight (legacy field, kept for the weight-diff display
        # elsewhere) = sum of the kg-unit lines only.
        vals['expected_weight'] = kg_total

        s = request.env['recycle.shipment'].sudo().create(vals)
        return {
            'ok': True,
            'id': s.id,
            'name': s.name,
            'driver_name': s.driver_name,
            'truck_info': s.truck_info or '',
            'truck_serial_number': s.truck_serial_number or '',
            'dispatch_date': s.dispatch_date.strftime('%Y-%m-%d %H:%M') if s.dispatch_date else '',
            'expected_totals_display': s.expected_totals_display,
            'lines': [{
                'id': l.id,
                'product_id': l.product_id.id,
                'product': l.product_id.name,
                'category': l.category_id.name or '',
                'uom': l.uom_id.name or '',
                'expected_qty': l.expected_qty,
            } for l in s.expected_line_ids],
        }

    @http.route('/api/test/create-order', type='jsonrpc', auth='user', methods=['POST'])
    def test_create_order(self, warehouse_id=None, customer_name=None,
                          lines=None, **kw):
        if not self._test_admin():
            return {'error': 'forbidden'}
        if not warehouse_id or not customer_name:
            return {'error': 'warehouse_id and customer_name are required'}
        vals = {
            'warehouse_id': int(warehouse_id),
            'customer_name': customer_name,
            'line_ids': [(0, 0, {
                'product_id': int(l['product_id']),
                'quantity': float(l.get('quantity', 1)),
                'price_unit': float(l.get('price_unit', 0)),
            }) for l in (lines or [])],
        }
        o = request.env['recycle.order'].sudo().create(vals)
        return {'ok': True, 'id': o.id, 'name': o.name}

    @http.route('/api/test/create-category', type='jsonrpc', auth='user', methods=['POST'])
    def test_create_category(self, name=None, **kw):
        if not self._test_admin():
            return {'error': 'forbidden'}
        if not name:
            return {'error': 'name is required'}
        c = request.env['recycle.product.category'].sudo().create({'name': name})
        return {'ok': True, 'id': c.id, 'name': c.name}

    @http.route('/api/test/create-product', type='jsonrpc', auth='user', methods=['POST'])
    def test_create_product(self, name=None, category_id=None,
                            price_factory=0, price_free_facility=0,
                            weight=0, **kw):
        if not self._test_admin():
            return {'error': 'forbidden'}
        if not name or not category_id:
            return {'error': 'name and category_id are required'}
        p = request.env['recycle.product'].sudo().create({
            'name': name,
            'category_id': int(category_id),
            'price_factory': float(price_factory or 0),
            'price_free_facility': float(price_free_facility or 0),
            'weight': float(weight or 0),
        })
        return {'ok': True, 'id': p.id, 'name': p.name}

    def _registered_users_domain(self):
        """Domain for 'registered users' = website visitors who created an
        account (portal / share users), explicitly NOT internal employees.
        Excludes the technical public user (no real email)."""
        return [
            ('share', '=', True),
            ('active', '=', True),
            ('email', '!=', False),
        ]

    @http.route('/api/recycle/registered-users', type='jsonrpc', auth='user',
                methods=['POST'])
    def get_registered_users_count(self, **kwargs):
        """Return the number of registered (non-employee) website users and a
        day-over-day trend percentage, for the admin dashboard card.

        Only administrators get the real figure; everyone else gets zero, so
        the endpoint never leaks user counts to unauthorised roles.
        """
        if not request.env.user.has_group('recycle_warehouse.group_recycle_admin'):
            return {'count': 0, 'trend': '+0%', 'trend_up': True}

        Users = request.env['res.users'].sudo()
        base = self._registered_users_domain()

        total = Users.search_count(base)

        # Day-over-day comparison (created today vs. created yesterday).
        from datetime import datetime, timedelta
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        today_s = today.strftime('%Y-%m-%d %H:%M:%S')
        yesterday_s = yesterday.strftime('%Y-%m-%d %H:%M:%S')

        created_today = Users.search_count(
            base + [('create_date', '>=', today_s)])
        created_yesterday = Users.search_count(
            base + [('create_date', '>=', yesterday_s),
                    ('create_date', '<', today_s)])

        if created_yesterday == 0:
            pct = 100 if created_today > 0 else 0
        else:
            pct = round((created_today - created_yesterday)
                        / created_yesterday * 100)
        sign = '+' if pct >= 0 else ''

        return {
            'count': total,
            'today': created_today,
            'trend': '%s%s%%' % (sign, pct),
            'trend_up': pct >= 0,
        }

    # ------------------------------------------------------------------
    # Shift management API (admin only)
    # ------------------------------------------------------------------
    def _shift_admin(self):
        if not request.env.user.has_group('recycle_warehouse.group_recycle_admin'):
            return False
        return True

    @http.route('/api/recycle/shift/validate-times', type='jsonrpc', auth='user',
                methods=['POST'])
    def validate_shift_times(self, start_time=None, end_time=None, **kw):
        return request.env['recycle.shift'].validate_shift_times(
            start_time, end_time)

    @http.route('/api/recycle/shift/available-employees', type='jsonrpc',
                auth='user', methods=['POST'])
    def shift_available_employees(self, warehouse_id=None, shift_id=None, **kw):
        if not self._shift_admin():
            return {'error': 'forbidden', 'employees': []}
        return {'employees': request.env['recycle.shift'].get_available_employees(
            warehouse_id=warehouse_id, shift_id=shift_id)}

    @http.route('/api/recycle/shift/create', type='jsonrpc', auth='user',
                methods=['POST'])
    def create_shift(self, shift_data=None, employee_ids=None, **kw):
        if not self._shift_admin():
            return {'error': 'forbidden'}
        data = shift_data or {}
        chk = request.env['recycle.shift'].validate_shift_times(
            data.get('start_time'), data.get('end_time'))
        if not chk.get('valid'):
            return {'error': chk.get('error')}
        shift = request.env['recycle.shift'].create({
            'name': (data.get('name') or '').strip(),
            'start_time': float(data.get('start_time')),
            'end_time': float(data.get('end_time')),
            'tolerance': int(data.get('tolerance') or 15),
            'warehouse_id': data.get('warehouse_id') or False,
        })
        # Spec §6b: shift CREATION only links a warehouse (or stays
        # unassigned). Employees are assigned later by the warehouse
        # manager from the employee-edit screen — any employee_ids sent
        # from the create screen are deliberately ignored.
        return {'id': shift.id, 'name': shift.name}

    @http.route('/api/recycle/shift/update', type='jsonrpc', auth='user',
                methods=['POST'])
    def update_shift(self, shift_id=None, new_data=None, employee_ids=None, **kw):
        if not self._shift_admin():
            return {'error': 'forbidden'}
        shift = request.env['recycle.shift'].browse(int(shift_id)).exists()
        if not shift:
            return {'error': 'not_found'}
        data = new_data or {}
        chk = request.env['recycle.shift'].validate_shift_times(
            data.get('start_time', shift.start_time),
            data.get('end_time', shift.end_time))
        if not chk.get('valid'):
            return {'error': chk.get('error')}
        vals = {}
        for f in ('name', 'start_time', 'end_time', 'tolerance', 'warehouse_id'):
            if f in data:
                vals[f] = data[f]
        shift.write(vals)
        if employee_ids is not None:
            shift.action_set_employees(employee_ids)
        return {'id': shift.id, 'name': shift.name,
                'employee_count': shift.employee_count}

    @http.route('/api/recycle/shift/delete', type='jsonrpc', auth='user',
                methods=['POST'])
    def delete_shift(self, shift_id=None, **kw):
        if not self._shift_admin():
            return {'error': 'forbidden'}
        shift = request.env['recycle.shift'].browse(int(shift_id)).exists()
        if not shift:
            return {'error': 'not_found'}
        info = shift.can_delete()
        if not info['ok']:
            return {'error': 'assigned', 'employees': info['employees']}
        shift.unlink()
        return {'ok': True}

    # ------------------------------------------------------------------
    # Manager: Assign shift to employee (warehouse-scoped)
    # ------------------------------------------------------------------
    @http.route('/api/manager/shift-assignment/employees', type='jsonrpc',
                auth='user', methods=['POST'])
    def manager_shift_assignment_employees(self, shift_filter=None, **kwargs):
        """Return employees of the manager's warehouse (excluding the manager
        themselves) with their shift assignment status.

        shift_filter: 'assigned' | 'unassigned' | '' (all)
        """
        warehouse = self._get_manager_warehouse()
        if not warehouse:
            return {'error': 'forbidden', 'employees': []}

        user = request.env.user
        Users = request.env['res.users'].sudo().with_context(active_test=False)
        domain = [
            ('recycle_warehouse_id', '=', warehouse.id),
            ('recycle_role', 'in', list(self.EMPLOYEE_ROLES)),
            ('active', '=', True),
            ('id', '!=', user.id),
        ]
        employees = Users.search(domain, order='name asc')

        result = []
        for u in employees:
            has_shift = bool(u.shift_id)
            result.append({
                'id': u.id,
                'name': u.name,
                'email': u.email or '',
                'phone': u.phone or '',
                'role': u.recycle_role or '',
                'shift_id': u.shift_id.id if u.shift_id else False,
                'shift_name': u.shift_id.name if u.shift_id else '',
                'has_shift': has_shift,
            })

        # Apply filter
        if shift_filter == 'assigned':
            result = [e for e in result if e['has_shift']]
        elif shift_filter == 'unassigned':
            result = [e for e in result if not e['has_shift']]

        return {
            'employees': result,
            'warehouse_id': warehouse.id,
            'warehouse_name': warehouse.name,
        }

    @http.route('/api/manager/shift-assignment/warehouse-shifts', type='jsonrpc',
                auth='user', methods=['POST'])
    def manager_shift_assignment_warehouse_shifts(self, **kwargs):
        """Return shifts the admin linked to THIS manager's warehouse only."""
        warehouse = self._get_manager_warehouse()
        if not warehouse:
            return {'error': 'forbidden', 'shifts': []}
        shifts = request.env['recycle.shift'].sudo().search(
            ['&', '&', ('active', '=', True), ('shift_type', '=', 'warehouse'),
             '|', ('is_global', '=', True), ('warehouse_ids', 'in', warehouse.id)],
            order='start_time')
        return {'shifts': [{
            'id': s.id,
            'name': s.name,
            'start_time': s.start_time,
            'end_time': s.end_time,
            'tolerance': s.tolerance,
        } for s in shifts]}

    @http.route('/api/manager/shift-assignment/assign', type='jsonrpc',
                auth='user', methods=['POST'])
    def manager_shift_assign(self, employee_id=None, shift_id=None, **kwargs):
        """Assign (or unassign) a shift to an employee.

        The shift MUST belong to the manager's warehouse.
        Pass shift_id=0 to unassign the current shift.
        Sends a notification to the employee on success."""
        warehouse = self._get_manager_warehouse()
        if not warehouse:
            return {'error': 'forbidden'}

        emp = self._get_manager_employee(warehouse, employee_id)
        if not emp:
            return {'error': 'not_found'}

        manager_name = request.env.user.name or 'Manager'

        if not shift_id:
            # Unassign
            old_shift_name = emp.shift_id.name if emp.shift_id else ''
            emp.sudo().write({'shift_id': False})
            try:
                self.env['recycle.notification']._notify_user(
                    emp, _('Shift Unassigned'),
                    _('%s from "%s" has unassigned you from shift "%s". '
                       'You are no longer assigned to any shift.') % (
                        manager_name, warehouse.name, old_shift_name),
                    notif_type='shift_change')
            except Exception:
                pass
            return {'ok': True, 'shift_id': False, 'shift_name': ''}

        shift = request.env['recycle.shift'].sudo().browse(int(shift_id)).exists()
        if not shift or not (shift.is_global or warehouse.id in shift.warehouse_ids.ids):
            return {'error': 'invalid_shift'}

        emp.sudo().write({'shift_id': shift.id})
        try:
            self.env['recycle.notification']._notify_user(
                emp, _('Shift Assigned'),
                _('%s from "%s" has assigned you to shift "%s" '
                   '(%s – %s, ±%d min).') % (
                    manager_name, warehouse.name, shift.name,
                    shift.format_time(shift.start_time),
                    shift.format_time(shift.end_time),
                    shift.tolerance),
                notif_type='shift_change')
        except Exception:
            pass
        return {
            'ok': True,
            'shift_id': shift.id,
            'shift_name': shift.name,
        }

    # ------------------------------------------------------------------
    # Employee: My Shift (always fresh, no cache)
    # ------------------------------------------------------------------
    @http.route('/api/employee/my-shift', type='jsonrpc', auth='user',
                methods=['POST'])
    def employee_my_shift(self, **kwargs):
        """Return the current employee's assigned shift details.
        This endpoint is called with cache: 'no-store' to ensure
        the employee always sees the latest shift assignment."""
        user = request.env.user
        shift = user.shift_id
        if not shift:
            return {'shift': False}
        return {'shift': {
            'id': shift.id,
            'name': shift.name,
            'start_time': shift.start_time,
            'end_time': shift.end_time,
            'tolerance': shift.tolerance,
            'assigned_employee_names': shift.assigned_employee_names or '',
            'employee_count': shift.employee_count,
        }}

    # ------------------------------------------------------------------ #
    #  Barcode image scanning for receiving employees                     #
    # ------------------------------------------------------------------ #

    @http.route('/api/receiving/scan-barcode', type='jsonrpc', auth='user',
                methods=['POST'])
    def scan_barcode(self, image=None, **kwargs):
        """Decode a barcode from a base64-encoded image and return the
        shipment reference (the ``name`` field on ``recycle.shipment``).

        The receiving-employee OWL component uploads a photo taken with
        the device camera or chosen from the gallery; this endpoint
        decodes it with *pyzbar* and returns the first barcode found.

        Returns ``{'shipment_ref': '<ID>'}`` on success, or
        ``{'error': '<reason>'}`` on failure.
        """
        if not image:
            return {'error': 'no_image'}

        # FALLBACK PATH ONLY — the browser decodes uploads now.
        #
        # `pyzbar` is a wrapper over the NATIVE `zbar` shared library, which the
        # official Odoo image does not ship. The Python package imports fine and
        # then fails on the C library:
        #
        #     ImportError: Unable to find zbar shared library
        #
        # So this route answered `pyzbar_missing` for every upload and the
        # feature never worked. The client now decodes with `html5-qrcode` (the
        # same library the live camera scan uses), and only falls back here if
        # that script did not load at all.
        #
        # Do NOT "fix" this by apt-installing libzbar into a running container:
        # it vanishes on the next rebuild and the button silently dies again.
        # It belongs in the image, or nowhere.
        try:
            from pyzbar import pyzbar
        except ImportError:
            return {'error': 'pyzbar_missing'}

        import base64, io
        try:
            from PIL import Image
        except ImportError:
            return {'error': 'pillow_missing'}

        try:
            raw = base64.b64decode(image)
        except Exception:
            return {'error': 'invalid_base64'}

        try:
            img = Image.open(io.BytesIO(raw))
        except Exception:
            return {'error': 'invalid_image'}

        codes = pyzbar.decode(img)
        if not codes:
            return {'error': 'no_barcode'}

        ref = codes[0].data.decode('utf-8', errors='ignore').strip()
        return {'shipment_ref': ref}

    def _shipment_scan_payload(self, s):
        """Shared shipment-detail shape for the QR-scan flow.

        This is the seam that stands in for the real backend today: once
        the NestJS integration exists, this method's body is the only
        thing that needs to change (fetch from the backend instead of the
        local ``recycle.shipment`` record) — callers stay the same.
        """
        return {
            'id': s.id,
            'name': s.name,
            'driver_name': s.driver_name or '',
            'truck_info': s.truck_info or '',
            'truck_serial_number': s.truck_serial_number or '',
            'dispatch_date': s.dispatch_date.strftime('%Y-%m-%d %H:%M') if s.dispatch_date else '',
            'state': s.state,
            'priority': s.priority or 10,
            # Reception is read-only: only the DECLARED total weight is shown,
            # never actual_weight/weight_diff_pct (no weighing step anymore).
            'expected_weight': s.expected_weight or 0,
            'expected_totals_display': s.expected_totals_display or '',
            'receiver_user_id': [s.receiver_user_id.id, s.receiver_user_id.name] if s.receiver_user_id else False,
            'create_date': s.create_date.strftime('%Y-%m-%d %H:%M') if s.create_date else '',
            'expected_lines': [{
                'id': l.id,
                'product_id': l.product_id.id,
                'product': l.product_id.name,
                'category': l.category_id.name or '',
                'uom': l.uom_id.name or '',
                'expected_qty': l.expected_qty,
            } for l in s.expected_line_ids],
        }

    @http.route('/api/receiving/scan-shipment', type='jsonrpc', auth='user',
                methods=['POST'])
    def scan_shipment(self, shipment_ref=None, **kwargs):
        """Handle QR scan for receiving employees — all 4 cases.

        Called by the OWL frontend after a QR code is decoded (or manually
        entered). The barcode encodes the shipment's own database ID (not
        its display name/reference), so the shipment is always identified
        by ID — this is what the physical barcode label must contain.
        Uses ``sudo()`` only for the initial search to bypass record
        rules, then switches back to the real user for actions.

        Returns one of:
          case='reserved'        — pending shipment was just reserved for this user
          case='mine'            — shipment already reserved by this user (welcome back)
          case='other'           — shipment reserved by another employee
          case='processed'       — shipment already accepted/sorted/etc.
          case='not_found'       — no shipment with that ID
          case='wrong_warehouse' — shipment belongs to a different warehouse
          case='error'           — something went wrong
        """
        user = request.env.user
        uid = user.id
        ref = (shipment_ref or '').strip()
        if not ref:
            return {'case': 'error', 'message': 'no_ref'}
        try:
            shipment_id = int(ref)
        except (TypeError, ValueError):
            return {'case': 'not_found',
                    'message': 'Invalid shipment barcode.'}

        # Search with sudo to bypass record rules (warehouse isolation).
        shipment = request.env['recycle.shipment'].sudo().search(
            [('id', '=', shipment_id)], limit=1)
        if not shipment:
            return {'case': 'not_found',
                    'message': 'Shipment not found. It may not exist or belong to another warehouse.'}

        s = shipment[0]

        # A receiving employee can only ever handle their own warehouse's
        # shipments — reject clearly instead of letting a record-rule
        # AccessError bubble up as a raw/ugly error.
        if not user.recycle_warehouse_id or s.warehouse_id.id != user.recycle_warehouse_id.id:
            return {
                'case': 'wrong_warehouse',
                'message': 'You cannot receive this shipment because it does not '
                            'belong to your warehouse.',
            }

        state = s.state
        receiver_id = s.receiver_user_id.id if s.receiver_user_id else 0

        # ── Case 1: pending → reserve it now ──
        if state == 'pending':
            # Call action_start_receiving with the REAL user context
            # so receiver_user_id is set to the employee, not superuser.
            s.with_user(user).action_start_receiving()
            # Re-read to get updated state
            s.invalidate_recordset(['state', 'receiver_user_id'])
            return {
                'case': 'reserved',
                'shipment': self._shipment_scan_payload(s),
                'message': 'Shipment reserved successfully.',
            }

        # ── Case 2: receiving + reserved by ME → welcome back ──
        if state == 'receiving' and receiver_id == uid:
            return {
                'case': 'mine',
                'shipment': self._shipment_scan_payload(s),
                'message': 'Welcome back.',
            }

        # ── Case 3: receiving + reserved by ANOTHER employee ──
        if state == 'receiving' and receiver_id != uid:
            other_name = s.receiver_user_id.name if s.receiver_user_id else 'another employee'
            return {
                'case': 'other',
                'reserved_by': other_name,
                'message': 'This shipment is currently reserved by %s.' % other_name,
            }

        # ── Case 4: already processed (accepted / sorting / sorted / escalated) ──
        if state in ('accepted', 'sorting', 'sorted', 'escalated'):
            return {
                'case': 'processed',
                'state': state,
                'message': 'This shipment has already been processed (%s).' % state,
            }

        # Fallback
        return {'case': 'error', 'message': 'Unexpected state: %s' % state}

    @http.route('/api/receiving/shipment-info', type='jsonrpc', auth='user',
                methods=['POST'])
    def shipment_info(self, shipment_ref=None, **kwargs):
        """Read-only shipment lookup — NO reservation side effect.

        This is the dedicated "fetch shipment info from the backend" seam:
        it currently reads the locally-created (Postman-simulated) shipment,
        but once the NestJS backend is connected this is the route whose
        body gets pointed at the real backend call. /api/receiving/scan-
        shipment (which DOES reserve the shipment) can then simply call
        this same lookup internally instead of querying the local model.
        """
        ref = (shipment_ref or '').strip()
        if not ref:
            return {'error': 'shipment_ref is required'}

        user = request.env.user
        # `sudo()` below bypasses the warehouse record rules, so the scope has
        # to be re-applied BY HAND — and it was not.
        #
        # Every other route in this flow checks it: `scan-shipment` refuses a
        # shipment outside the caller's warehouse, and `my-shipments` filters on
        # it. This one searched every warehouse's shipments by reference and
        # returned the full payload — supplier, weights, lines, driver — to any
        # authenticated user who could guess or iterate a reference. Read-only
        # is not harmless when the thing read is another site's consignments.
        wh = user.recycle_warehouse_id
        if not wh:
            return {'error': 'not_found'}

        s = request.env['recycle.shipment'].sudo().search(
            [('name', '=', ref), ('warehouse_id', '=', wh.id)], limit=1)
        if not s:
            # Deliberately the same answer as "belongs to another warehouse":
            # distinguishing them would confirm that a reference exists
            # somewhere, which is the half of the leak that survives a fix.
            return {'error': 'not_found'}
        return {'ok': True, 'shipment': self._shipment_scan_payload(s)}

    @http.route('/api/receiving/my-shipments', type='jsonrpc', auth='user',
                methods=['POST'])
    def my_shipments(self, state_filter=None, **kwargs):
        """Return shipments for the current user, respecting role isolation.

        Uses ``sudo()`` to bypass record rules, then manually filters by
        warehouse and user to ensure correct isolation.

        KEY RULE: Pending shipments are NEVER shown in the employee list.
        The employee must scan the QR code again to find and reserve them.
        """
        user = request.env.user
        uid = user.id
        wh = user.recycle_warehouse_id

        if not wh:
            return {'shipments': [], 'error': 'No warehouse assigned'}

        domain = [
            ('warehouse_id', '=', wh.id),
            ('recycle_archived', '=', False),
        ]

        if state_filter == 'receiving':
            # Only my receiving shipments (claimed, awaiting acceptance)
            domain += [('state', '=', 'receiving'), ('receiver_user_id', '=', uid)]
        elif state_filter == 'processed':
            # My accepted shipments — "Received" from the receiving
            # employee's point of view.
            domain += [('state', '=', 'accepted'), ('receiver_user_id', '=', uid)]
        else:
            # Default ("All"): reception only ever sees its own two states
            # (receiving + accepted). Once sorting starts, the shipment
            # disappears from this list — that's the sorter/manager's job now.
            domain += [('receiver_user_id', '=', uid),
                       ('state', 'in', ['receiving', 'accepted'])]

        shipments = request.env['recycle.shipment'].sudo().search_read(
            domain,
            ['id', 'name', 'driver_name', 'truck_info', 'state', 'received_at',
             'expected_weight', 'expected_totals_display',
             'receiver_user_id', 'create_date'],
            order='priority asc, id desc',
            limit=200)

        return {'shipments': shipments}

    @http.route('/api/receiving/dashboard-stats', type='jsonrpc', auth='user',
                methods=['POST'])
    def receiving_dashboard_stats(self, period='month', **kwargs):
        """Return real-time dashboard stats for the receiving employee.

        period: 'today' | 'week' | 'month' | 'year'
        Returns 4 metrics computed from the database:
          - processed: shipments received/accepted in period
          - working_hours: actual work hours from attendance
          - completion_rate: (processed / total assigned) * 100
          - transferred: shipments escalated in period
        """
        user = request.env.user
        uid = user.id
        wh = user.recycle_warehouse_id

        if not wh:
            return {
                'processed': 0, 'working_hours': 0,
                'completion_rate': 0, 'transferred': 0,
            }

        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # ── Calculate period date range ──
        if period == 'today':
            period_start = today_start
        elif period == 'week':
            # Start of week (Monday)
            period_start = today_start - timedelta(days=today_start.weekday())
        elif period == 'year':
            period_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:  # month (default)
            period_start = today_start.replace(day=1)

        period_start_s = period_start.strftime('%Y-%m-%d %H:%M:%S')

        Ship = request.env['recycle.shipment'].sudo()

        # ── 1) Processed Shipments ──
        # Shipments where this employee is the receiver AND state is accepted/sorting/sorted
        processed_domain = [
            ('warehouse_id', '=', wh.id),
            ('receiver_user_id', '=', uid),
            ('state', 'in', ['accepted', 'sorting', 'sorted']),
            ('received_at', '>=', period_start_s),
        ]
        processed = Ship.search_count(processed_domain)

        # ── 2) Transferred Shipments ──
        # Shipments escalated by this employee in the period
        transferred_domain = [
            ('warehouse_id', '=', wh.id),
            ('receiver_user_id', '=', uid),
            ('state', '=', 'escalated'),
            ('received_at', '>=', period_start_s),
        ]
        transferred = Ship.search_count(transferred_domain)

        # ── 2b) Pending Shipments ──
        # Shipments currently reserved to this employee (scanned but not
        # yet marked received) — a live count, not scoped to the period.
        pending = Ship.search_count([
            ('warehouse_id', '=', wh.id),
            ('receiver_user_id', '=', uid),
            ('state', '=', 'receiving'),
        ])

        # ── 3) Total Assigned (for completion rate) ──
        # All shipments this employee received/processed in the period
        total_domain = [
            ('warehouse_id', '=', wh.id),
            ('receiver_user_id', '=', uid),
            ('received_at', '>=', period_start_s),
        ]
        total_assigned = Ship.search_count(total_domain)

        # ── 4) Completion Rate ──
        if total_assigned > 0:
            completed = Ship.search_count([
                ('warehouse_id', '=', wh.id),
                ('receiver_user_id', '=', uid),
                ('state', 'in', ['accepted', 'sorting', 'sorted']),
                ('received_at', '>=', period_start_s),
            ])
            completion_rate = round((completed / total_assigned) * 100)
        else:
            completion_rate = 0

        # ── 5) Working Hours ──
        Att = request.env['recycle.attendance'].sudo()
        att_domain = [
            ('employee_user_id', '=', uid),
            ('date', '>=', period_start.date()),
        ]
        attendances = Att.search(att_domain)
        working_hours = 0.0
        for att in attendances:
            if att.check_in and att.check_out:
                delta = att.check_out - att.check_in
                working_hours += delta.total_seconds() / 3600.0
            elif att.check_in and not att.check_out:
                delta = now - att.check_in
                working_hours += delta.total_seconds() / 3600.0

        return {
            'processed': processed,
            'working_hours': round(working_hours, 1),
            'completion_rate': completion_rate,
            'transferred': transferred,
            'pending': pending,
            'period': period,
            'period_start': period_start_s,
        }

    @http.route('/api/recycle/change-password', type='jsonrpc', auth='user',
                methods=['POST'])
    def change_password(self, current_password=None, new_password=None, **kwargs):
        """Change the current user's password after verifying the old one."""
        user = request.env.user
        if not current_password or not new_password:
            return {'success': False, 'error': 'Please provide both current and new password'}
        if len(new_password) < 6:
            return {'success': False, 'error': 'Password must be at least 6 characters'}
        try:
            # Verify current password via SQL + passlib (same as attendance_api)
            # Avoids session.authenticate() which destroys the current session
            request.env.cr.execute(
                "SELECT COALESCE(password, '') FROM res_users WHERE id = %s AND active = true",
                [user.id]
            )
            row = request.env.cr.fetchone()
            if not row or not row[0]:
                return {'success': False, 'error': 'Current password is incorrect'}
            try:
                valid, _ = user._crypt_context().verify_and_update(current_password, row[0])
            except Exception:
                valid = False
            if not valid:
                return {'success': False, 'error': 'Current password is incorrect'}
            # Set new password. res.users.write() already fires Odoo's
            # native security-change notification (overridden in
            # models/warehouse.py to use the shared Dawrha email design) —
            # no separate email needs to be sent here.
            user.sudo().write({'password': new_password})
            return {'success': True}
        except Exception:
            return {'success': False, 'error': 'Current password is incorrect'}

    @http.route('/api/recycle/thresholds', type='jsonrpc', auth='user',
                methods=['POST'], csrf=False)
    def get_thresholds(self, **kwargs):
        """Admin-configurable approval percentages (never static)."""
        from odoo.addons.recycle_warehouse.models.shipment import (
            _pct_param, WEIGHT_TOLERANCE, WEIGHT_HARD_LIMIT, DAMAGE_LIMIT)
        env = request.env
        return {
            'weight_warn_pct': _pct_param(env, 'recycle.weight_warn_pct',
                                          WEIGHT_TOLERANCE),
            'weight_max_pct': _pct_param(env, 'recycle.weight_max_pct',
                                         WEIGHT_HARD_LIMIT),
            'damage_max_pct': _pct_param(env, 'recycle.damage_max_pct',
                                         DAMAGE_LIMIT),
        }

    @http.route('/api/recycle/thresholds/save', type='jsonrpc', auth='user',
                methods=['POST'], csrf=False)
    def save_thresholds(self, weight_warn_pct=None, weight_max_pct=None,
                        damage_max_pct=None, **kwargs):
        """Only the administrator may change the approval percentages."""
        if not request.env.user.has_group(
                'recycle_warehouse.group_recycle_admin'):
            return {'error': 'forbidden'}
        try:
            warn = float(weight_warn_pct)
            hard = float(weight_max_pct)
            damage = float(damage_max_pct)
        except (TypeError, ValueError):
            return {'error': 'invalid_values'}
        if not (0 < warn < hard <= 100) or not (0 < damage <= 100):
            return {'error': 'invalid_range'}
        icp = request.env['ir.config_parameter'].sudo()
        icp.set_param('recycle.weight_warn_pct', str(warn))
        icp.set_param('recycle.weight_max_pct', str(hard))
        icp.set_param('recycle.damage_max_pct', str(damage))
        return {'ok': True}

    @http.route('/api/recycle/sort-thresholds', type='jsonrpc', auth='user',
                methods=['POST'], csrf=False)
    def get_sort_thresholds(self, **kwargs):
        """Sorting reconciliation thresholds (res.config.settings:
        sorting_tolerance_threshold_1 / _2) — read via the single shared
        helper so this always matches what action_finish_sorting() uses."""
        from odoo.addons.recycle_warehouse.models.shipment import _get_sorting_thresholds
        t1, t2 = _get_sorting_thresholds(request.env)
        return {'threshold_1': t1, 'threshold_2': t2}

    @http.route('/api/recycle/sort-thresholds/save', type='jsonrpc', auth='user',
                methods=['POST'], csrf=False)
    def save_sort_thresholds(self, threshold_1=None, threshold_2=None, **kwargs):
        """Only the administrator may change the sorting thresholds."""
        if not request.env.user.has_group(
                'recycle_warehouse.group_recycle_admin'):
            return {'error': 'forbidden'}
        try:
            t1 = float(threshold_1)
            t2 = float(threshold_2)
        except (TypeError, ValueError):
            return {'error': 'invalid_values'}
        if not (0 <= t1 < t2 <= 100):
            return {'error': 'invalid_range'}
        icp = request.env['ir.config_parameter'].sudo()
        icp.set_param('warehouse.sorting_tolerance_threshold_1', str(t1))
        icp.set_param('warehouse.sorting_tolerance_threshold_2', str(t2))
        return {'ok': True}

    @http.route('/api/recycle/my-profile', type='jsonrpc', auth='user', methods=['POST'], csrf=False)
    def my_profile(self, **kwargs):
        """Return current user profile data (sensitive fields need sudo read)."""
        user = request.env.user.sudo()
        return {
            'name': user.name or '',
            'email': user.email or '',
            'login': user.login or '',
            'phone': user.phone or '',
            'national_id': user.recycle_national_id or '',
            'role': user.recycle_role or '',
            'warehouse': user.recycle_warehouse_id.name if user.recycle_warehouse_id else '',
            'street': user.street or '',
            'city': user.city or '',
            'country': user.country_id.name if user.country_id else '',
        }

    # ------------------------------------------------------------------
    # Delivery driver
    # ------------------------------------------------------------------
    @http.route('/api/recycle/my-delivery-truck', type='jsonrpc', auth='user',
                methods=['POST'])
    def my_delivery_truck(self, **kwargs):
        """The delivery driver's own record and the truck they were given.

        This screen takes the place of the shift screen every other role has. A
        delivery driver works no shift at all — they carry sold goods when there
        is an order to carry — so the question their home screen has to answer
        is not "when am I on" but "which vehicle am I responsible for".

        `assigned: False` is a real answer, not an error: a driver can be on file
        before a truck is free, and saying so plainly is better than an empty
        screen that reads like a failure.
        """
        driver = request.env['recycle.delivery.driver'].sudo().search(
            [('user_id', '=', request.env.uid)], limit=1)
        if not driver:
            return {'error': 'not_a_delivery_driver'}

        truck = driver.truck_id
        return {
            'driver': {
                'name': driver.name or '',
                'phone': driver.phone or '',
                'national_id': driver.national_id or '',
                'warehouse': driver.warehouse_id.name or '',
                'is_active': driver.is_active,
                'license_number': driver.license_number or '',
                'license_expiry': str(driver.license_expiry or ''),
            },
            'assigned': bool(truck),
            'truck': {
                'id': truck.id,
                'name': truck.name or '',
                'plate_number': truck.plate_number or '',
                'model': truck.model or '',
                'year': truck.year or '',
                'max_payload_kg': truck.max_payload_kg or 0.0,
                'truck_type': truck.truck_type or '',
                'warehouse': truck.warehouse_id.name or '',
                'is_active': truck.is_active,
                'disable_reason': truck.disable_reason or '',
            } if truck else None,
        }

    @http.route('/api/recycle/my-delivery-trips', type='jsonrpc', auth='user',
                methods=['POST'])
    def my_delivery_trips(self, **kwargs):
        """The driver's live trips — each showing ONLY the next station to drive
        to, not the whole route.

        A milk run has an order (farthest warehouse first, so the truck never
        doubles back), and a driver staring at five stops collects them in the
        wrong sequence. The next stop opens when the one before it is confirmed,
        and its map pin is right there to navigate to.
        """
        driver = request.env['recycle.delivery.driver'].sudo().search(
            [('user_id', '=', request.env.uid)], limit=1)
        if not driver:
            return {'error': 'not_a_delivery_driver', 'trips': []}

        trips = request.env['recycle.delivery.trip'].sudo().search([
            ('driver_id', '=', driver.id),
            ('status', 'in', ['assigned', 'in_progress']),
        ], order='create_date asc')

        out = []
        for trip in trips:
            nxt = trip.next_stop()
            collected = trip.stop_ids.filtered(lambda s: s.picked_up_at)
            out.append({
                'trip_id': trip.id,
                'trip_number': trip.trip_number,
                'order_number': trip.order_number,
                'buyer_name': trip.buyer_name,
                'status': trip.status,
                'total_stops': len(trip.stop_ids),
                'collected_stops': len(collected),
                'destination': {
                    'latitude': trip.dest_latitude,
                    'longitude': trip.dest_longitude,
                    'maps_url': trip.dest_maps_url or '',
                },
                # ONLY the next station — the whole point of the screen.
                'next_stop': {
                    'stop_id': nxt.id,
                    'backend_stop_id': nxt.backend_stop_id,
                    'sequence': nxt.sequence,
                    'warehouse': nxt.warehouse_id.name or '',
                    'goods': nxt.product_summary or '',
                    'distance_to_buyer_km': nxt.distance_to_buyer_km,
                    'maps_url': nxt.maps_url or '',
                } if nxt else None,
                'ready_to_deliver': not trip.next_stop() and trip.status == 'in_progress',
            })
        return {'trips': out}

    @http.route('/api/recycle/delivery-confirm-pickup', type='jsonrpc',
                auth='user', methods=['POST'])
    def delivery_confirm_pickup(self, trip_id=None, backend_stop_id=None, **kwargs):
        """The driver confirms taking the next station's goods; the time is
        recorded and the backend is told at once."""
        driver = request.env['recycle.delivery.driver'].sudo().search(
            [('user_id', '=', request.env.uid)], limit=1)
        if not driver:
            return {'error': 'not_a_delivery_driver'}
        trip = request.env['recycle.delivery.trip'].sudo().browse(int(trip_id or 0))
        if not trip.exists() or trip.driver_id != driver:
            return {'error': 'not_your_trip'}
        try:
            return trip.action_driver_confirm_pickup(backend_stop_id)
        except UserError as e:
            return {'error': str(e)}

    @http.route('/api/recycle/delivery-complete', type='jsonrpc', auth='user',
                methods=['POST'])
    def delivery_complete(self, trip_id=None, **kwargs):
        """The driver hands the whole load to the buyer at the last stop."""
        driver = request.env['recycle.delivery.driver'].sudo().search(
            [('user_id', '=', request.env.uid)], limit=1)
        if not driver:
            return {'error': 'not_a_delivery_driver'}
        trip = request.env['recycle.delivery.trip'].sudo().browse(int(trip_id or 0))
        if not trip.exists() or trip.driver_id != driver:
            return {'error': 'not_your_trip'}
        try:
            return trip.action_driver_complete()
        except UserError as e:
            return {'error': str(e)}

    @http.route('/api/recycle/my-devices', type='jsonrpc', auth='user', methods=['POST'])
    def my_devices(self, **kwargs):
        """Devices this user has signed in from — exactly one entry per
        physical device (repeat logins update last_activity instead of
        adding rows), with a human device name parsed from the User-Agent.
        Viewing the screen also counts as activity for the current device,
        which guarantees it always appears even right after an upgrade."""
        uid = request.env.uid
        Dev = request.env['recycle.user.device'].sudo()
        Dev._track(request, uid)  # bump last_seen for the current device
        ua = request.httprequest.headers.get('User-Agent', '')
        current_key = Dev._device_key(uid, ua)
        devices = Dev.search([('user_id', '=', uid)],
                             order='last_seen desc', limit=50)
        fmt = '%Y-%m-%d %H:%M:%S'
        return {'devices': [{
            'id': d.id,
            'device_name': d.device_name or '',
            'platform': d.platform or '',
            'browser': d.browser or '',
            'device_type': d.device_type or 'computer',
            'ip_address': d.ip_address or '',
            'first_activity': d.first_seen.strftime(fmt) if d.first_seen else '',
            'last_activity': d.last_seen.strftime(fmt) if d.last_seen else '',
            'last_event': d.last_event or '',
            'is_current': d.device_key == current_key,
        } for d in devices]}

    @http.route('/api/recycle/save-profile', type='jsonrpc', auth='user', methods=['POST'])
    def save_profile(self, **kwargs):
        """Save current user profile fields (uses sudo to bypass access rules)."""
        user = request.env.user.sudo()
        vals = kwargs.get('vals', {})

        # Validate National ID uniqueness
        nid = (vals.get('recycle_national_id') or '').strip()
        if nid:
            if not nid.isdigit() or not (5 <= len(nid) <= 20):
                return {'error': 'National ID must contain only digits (5 to 20 characters).'}
            existing = user.search([
                ('recycle_national_id', '=', nid),
                ('id', '!=', user.id),
            ], limit=1)
            if existing:
                return {'error': 'This National ID is already used by another person.'}

        allowed_partner = {}
        allowed_user = {}
        if 'name' in vals:
            allowed_partner['name'] = vals['name']
        if 'phone' in vals:
            allowed_partner['phone'] = vals['phone'] or False
        if 'street' in vals:
            allowed_partner['street'] = vals['street'] or False
        if 'city' in vals:
            allowed_partner['city'] = vals['city'] or False
        if 'country_id' in vals:
            allowed_partner['country_id'] = vals['country_id'] or False
        if nid:
            allowed_user['recycle_national_id'] = nid
        if allowed_partner and user.partner_id:
            user.partner_id.write(allowed_partner)
        if allowed_user:
            user.write(allowed_user)
        return {'success': True}


class RecycleOutputApiController(http.Controller):

    @http.route('/api/output/dashboard', type='jsonrpc', auth='user', methods=['POST'])
    def dashboard(self, period='month', **kwargs):
        user = request.env.user.sudo()
        wh = user.recycle_warehouse_id
        if not wh:
            return {'error': 'No warehouse assigned'}

        from datetime import date, timedelta
        today = date.today()
        if period == 'today':
            period_start = today
        elif period == 'week':
            period_start = today - timedelta(days=today.weekday())
        else:  # month
            period_start = today.replace(day=1)

        # Work hours for the selected period (was hardcoded to "this week"
        # regardless of the period filter — now matches it).
        attendances = request.env['recycle.attendance'].sudo().search([
            ('employee_user_id', '=', user.id),
            ('date', '>=', period_start),
            ('date', '<=', today),
        ])
        work_hours = 0.0
        for att in attendances:
            if att.check_in and att.check_out:
                delta = att.check_out - att.check_in
                work_hours += delta.total_seconds() / 3600.0

        # Orders stats. Total/Completed are genuine period activity (orders
        # placed / finished in the selected window). Processing/Pending
        # reflect what needs action RIGHT NOW, so they stay live counts,
        # not scoped to the period, same as every other dashboard's
        # "reserved to me" style metrics.
        Order = request.env['recycle.order'].sudo()
        wh_domain = [('warehouse_id', '=', wh.id)]
        period_start_s = period_start.strftime('%Y-%m-%d 00:00:00')
        total_orders = Order.search_count(wh_domain + [('create_date', '>=', period_start_s)])
        completed_orders = Order.search_count(
            wh_domain + [('state', '=', 'completed'), ('invoice_date', '>=', period_start)])
        processing_orders = Order.search_count(wh_domain + [('state', '=', 'processing')])
        pending_orders = Order.search_count(wh_domain + [('state', '=', 'pending')])

        return {
            'warehouse': {
                'id': wh.id,
                'name': wh.name or '',
                'code': wh.code or '',
                'governorate': wh.governorate or '',
                'manager': wh.manager_user_id.name if wh.manager_user_id else '',
            },
            'weekly_hours': round(work_hours, 1),
            'stats': {
                'total': total_orders,
                'completed': completed_orders,
                'processing': processing_orders,
                'pending': pending_orders,
            },
        }

    # 'completed' orders accumulate forever with no natural cap (unlike
    # pending/processing/ready, which are always self-limiting — an order
    # leaves that bucket the moment it's actioned). Capping only the
    # completed bucket to the most recent N keeps the payload bounded as
    # a warehouse's history grows across years, without ever hiding an
    # order an employee still needs to act on (which would silently break
    # the priority-queue logic that depends on seeing every pending order).
    COMPLETED_ORDERS_LIMIT = 200

    @http.route('/api/output/orders', type='jsonrpc', auth='user', methods=['POST'])
    def orders_list(self, state_filter='', **kwargs):
        user = request.env.user.sudo()
        wh = user.recycle_warehouse_id
        if not wh:
            return {'error': 'No warehouse assigned'}

        Order = request.env['recycle.order'].sudo()
        # Output employees only ever see orders the warehouse manager has
        # explicitly approved — pending/rejected API orders are invisible.
        base_domain = [('warehouse_id', '=', wh.id),
                       ('manager_approval', '=', 'approved')]
        if state_filter:
            domain = base_domain + [('state', '=', state_filter)]
            limit = self.COMPLETED_ORDERS_LIMIT if state_filter == 'completed' else None
            orders = Order.search(domain, order='priority asc, create_date desc', limit=limit)
        else:
            active = Order.search(
                base_domain + [('state', 'in', ['pending', 'processing', 'ready'])],
                order='priority asc, create_date desc')
            completed = Order.search(
                base_domain + [('state', '=', 'completed')],
                order='create_date desc', limit=self.COMPLETED_ORDERS_LIMIT)
            orders = active + completed
        # One query for the whole warehouse's stock instead of one
        # per-line _available_qty() call — this list is now live-polled
        # every 5s by the output dashboard, so N orders x M lines worth of
        # per-line queries would otherwise multiply fast under load.
        stock_model = request.env['recycle.stock'].sudo()
        stock_by_key = {}
        for s in stock_model.search([('warehouse_id', '=', wh.id)]):
            key = (s.product_id.id, s.condition)
            stock_by_key[key] = stock_by_key.get(key, 0.0) + s.quantity
        result = []
        for o in orders:
            # Pre-check: can this order even be fulfilled? Every line must
            # have enough stock of its OWN condition — used to gray out
            # "Start Processing" before the employee wastes a reservation
            # on an order that can never be completed as-is.
            stock_sufficient = all(
                stock_by_key.get((l.product_id.id, l.condition), 0.0) >= l.quantity
                for l in o.line_ids
            ) if o.line_ids else True
            # Priority-gate: a higher-priority pending order still waiting
            # blocks this one from starting (skipped over if it lacks stock
            # — see get_blocking_order). Only meaningful while pending.
            blocker = o.get_blocking_order() if o.state == 'pending' else o.browse()
            result.append({
                'id': o.id,
                'name': o.name or '',
                'customer_name': o.customer_name or '',
                'owner_name': o.owner_name or '',
                'state': o.state or '',
                'order_type': o.order_type or '',
                'priority': o.priority or 10,
                'amount_total': o.amount_total or 0.0,
                'total_weight': o.total_weight or 0.0,
                'output_user': o.output_user_id.name if o.output_user_id else '',
                'output_user_id': o.output_user_id.id if o.output_user_id else False,
                'invoice_number': o.invoice_number or '',
                'create_date': o.create_date.strftime('%Y-%m-%d %H:%M') if o.create_date else '',
                'line_count': len(o.line_ids),
                'stock_sufficient': stock_sufficient,
                'blocking_order_id': blocker.id if blocker else False,
                'blocking_order_name': blocker.name if blocker else '',
            })
        return {'orders': result}

    @http.route('/api/output/order/<int:order_id>', type='jsonrpc', auth='user', methods=['POST'])
    def order_detail(self, order_id, **kwargs):
        user = request.env.user.sudo()
        order = request.env['recycle.order'].sudo().browse(order_id)
        if not order.exists():
            return {'error': 'Order not found'}
        # Defense in depth: an output employee must never open a
        # not-yet-approved order, even with a guessed/stale id.
        if (order.manager_approval != 'approved'
                and user.recycle_role == 'output'):
            return {'error': 'Order not found'}

        stock_model = request.env['recycle.stock'].sudo()
        lines = []
        for line in order.line_ids:
            product = line.product_id
            if order.order_type == 'factory':
                price = product.price_factory
            else:
                price = product.price_free_facility
            # Availability is per condition: an 'excellent' line can only
            # ever be fulfilled from 'excellent' stock.
            available = stock_model._available_qty(
                order.warehouse_id, product, condition=line.condition)
            lines.append({
                'id': line.id,
                'product_id': product.id,
                'product_name': product.name or '',
                'category': product.category_id.name if product.category_id else '',
                'quantity': line.quantity or 0.0,
                'condition': line.condition or 'good',
                'stock_available': available,
                'sufficient': available >= (line.quantity or 0.0),
                'price_unit': price,
                'subtotal': (line.quantity or 0.0) * price,
                'weight': product.weight or 0.0,
            })

        blocker = order.get_blocking_order() if order.state == 'pending' else order.browse()
        return {
            'id': order.id,
            'name': order.name or '',
            'customer_name': order.customer_name or '',
            'owner_name': order.owner_name or '',
            'customer_email': order.customer_email or '',
            'state': order.state or '',
            'order_type': order.order_type or '',
            'blocking_order_id': blocker.id if blocker else False,
            'blocking_order_name': blocker.name if blocker else '',
            'priority': order.priority or 10,
            'amount_total': order.amount_total or 0.0,
            'total_weight': order.total_weight or 0.0,
            'output_user': order.output_user_id.name if order.output_user_id else '',
            'output_user_id': order.output_user_id.id if order.output_user_id else False,
            'invoice_number': order.invoice_number or '',
            'invoice_date': order.invoice_date.strftime('%Y-%m-%d') if order.invoice_date else '',
            'create_date': order.create_date.strftime('%Y-%m-%d %H:%M') if order.create_date else '',
            'lines': lines,
        }

    @http.route('/api/output/order/reserve', type='jsonrpc', auth='user', methods=['POST'])
    def reserve_order(self, order_id, **kwargs):
        order = request.env['recycle.order'].sudo().browse(order_id)
        if not order.exists():
            return {'error': 'Order not found'}

        # Delegates to the model's action_start_processing, which is the
        # single authoritative place enforcing the priority queue: a
        # higher-priority pending order (that actually has stock to be
        # fulfilled) must be started first.
        try:
            order.sudo().action_start_processing()
        except UserError as e:
            return {'error': str(e)}

        order.sudo()._compute_amount_total()
        return {'success': True, 'amount_total': order.amount_total}

    @http.route('/api/output/order/complete', type='jsonrpc', auth='user', methods=['POST'])
    def complete_order(self, order_id, allocations=None, **kwargs):
        user = request.env.user.sudo()
        order = request.env['recycle.order'].sudo().browse(order_id)
        if not order.exists():
            return {'error': 'Order not found'}
        if order.state != 'processing':
            return {'error': 'Order is not in processing state'}
        if order.output_user_id and order.output_user_id.id != user.id:
            return {'error': 'This order is reserved by another employee'}
        if not allocations or not isinstance(allocations, list):
            return {'error': _(
                'Choose the storage zone(s) to deduct the quantity from '
                'for every product first.')}

        # action_complete is the authoritative deduction path: it re-checks
        # every allocation against the exact (zone, condition) stock line
        # and raises a friendly UserError (e.g. "Quantity insufficient,
        # check your stock") if any zone can't cover what was picked for it.
        try:
            order.sudo().action_complete(allocations=allocations)
        except UserError as e:
            return {'error': str(e)}

        pdf_url = '/api/output/order/%s/print-invoice' % order.id
        return {
            'success': True,
            'state': order.state,
            'invoice_number': order.invoice_number or '',
            'invoice_date': order.invoice_date.strftime('%Y-%m-%d') if order.invoice_date else '',
            'stock_deducted_at': (order.stock_deducted_at.strftime('%Y-%m-%d %H:%M:%S')
                                   if order.stock_deducted_at else ''),
            'amount_total': order.amount_total,
            'pdf_url': pdf_url,
        }

    @http.route('/api/output/storage-zones', type='jsonrpc', auth='user', methods=['POST'])
    def storage_zones(self, order_id, **kwargs):
        order = request.env['recycle.order'].sudo().browse(order_id)
        if not order.exists():
            return {'error': 'Order not found'}

        wh = order.warehouse_id
        stock_model = request.env['recycle.stock'].sudo()

        # Only the exact (product, condition) pairs this order actually
        # needs — a storage zone holding anything else is irrelevant here.
        line_by_key = {}
        order_requirements = []
        for line in order.line_ids:
            line_by_key[(line.product_id.id, line.condition)] = line
            available = stock_model._available_qty(
                wh, line.product_id, condition=line.condition)
            order_requirements.append({
                'line_id': line.id,
                'product_id': line.product_id.id,
                'product_name': line.product_id.name or '',
                'condition': line.condition or 'good',
                'required': line.quantity,
                'available': available,
                'sufficient': available >= line.quantity,
            })

        zones = request.env['recycle.zone'].sudo().search([
            ('warehouse_id', '=', wh.id),
            ('zone_type', '=', 'storage'),
        ])

        result = []
        for zone in zones:
            zone_stocks = stock_model.search([
                ('warehouse_id', '=', wh.id),
                ('zone_id', '=', zone.id),
                ('quantity', '>', 0),
            ])
            zone_products = []
            for stock in zone_stocks:
                line = line_by_key.get((stock.product_id.id, stock.condition))
                if not line:
                    continue
                zone_products.append({
                    'line_id': line.id,
                    'product_id': stock.product_id.id,
                    'product_name': stock.product_id.name or '',
                    'quantity': stock.quantity,
                    'condition': stock.condition or 'good',
                })
            # Never show a zone with nothing (or nothing relevant) in it.
            if not zone_products:
                continue
            result.append({
                'id': zone.id,
                'name': zone.name or '',
                'products': zone_products,
            })

        return {
            'zones': result,
            'requirements': order_requirements,
        }

    @http.route('/api/output/output-zones', type='jsonrpc', auth='user', methods=['POST'])
    def output_zones(self, order_id, **kwargs):
        """List valid destination zones for the final 'Finish' step
        (after stock has been deducted, state == 'ready')."""
        order = request.env['recycle.order'].sudo().browse(order_id)
        if not order.exists():
            return {'error': 'Order not found'}
        zones = request.env['recycle.zone'].sudo().search([
            ('warehouse_id', '=', order.warehouse_id.id),
            ('zone_type', '=', 'output'),
        ])
        return {'zones': [{'id': z.id, 'name': z.name or ''} for z in zones]}

    @http.route('/api/output/order/finish', type='jsonrpc', auth='user', methods=['POST'])
    def finish_order(self, order_id, output_zone_id, **kwargs):
        user = request.env.user.sudo()
        order = request.env['recycle.order'].sudo().browse(order_id)
        if not order.exists():
            return {'error': 'Order not found'}
        if order.output_user_id and order.output_user_id.id != user.id:
            return {'error': 'This order is reserved by another employee'}
        try:
            order.sudo().action_finish(output_zone_id)
        except UserError as e:
            return {'error': str(e)}
        return {
            'success': True,
            'state': order.state,
            'output_zone': order.output_zone_id.name or '',
            'finished_at': (order.finished_at.strftime('%Y-%m-%d %H:%M:%S')
                             if order.finished_at else ''),
        }

    @http.route('/api/output/order/cancel', type='jsonrpc', auth='user', methods=['POST'])
    def cancel_order(self, order_id, **kwargs):
        user = request.env.user.sudo()
        order = request.env['recycle.order'].sudo().browse(order_id)
        if not order.exists():
            return {'error': 'Order not found'}
        if order.state not in ('pending', 'processing'):
            return {'error': 'Cannot cancel this order'}
        if order.output_user_id and order.output_user_id.id != user.id:
            return {'error': 'Order is reserved by another employee'}

        order.sudo().write({
            'state': 'cancelled',
            'output_user_id': False,
        })
        return {'success': True}

    @http.route('/api/output/order/create-test', type='jsonrpc', auth='user', methods=['POST'])
    def create_test_order(self, customer_name='Test Factory', owner_name='Test Owner',
                          customer_email='test@example.com', order_type='factory',
                          priority=10, products=None, **kwargs):
        """Create a test order for debugging. products = [{'product_id': int, 'quantity': float}]"""
        user = request.env.user.sudo()
        wh = user.recycle_warehouse_id
        if not wh:
            return {'error': 'No warehouse assigned'}

        if not products:
            # Use first available products
            prods = request.env['recycle.product'].sudo().search([], limit=5)
            products = [{'product_id': p.id, 'quantity': 10.0} for p in prods]

        order_vals = {
            'customer_name': customer_name,
            'owner_name': owner_name,
            'customer_email': customer_email,
            'warehouse_id': wh.id,
            'order_type': order_type,
            'priority': priority,
            'state': 'pending',
            'line_ids': [],
        }
        for p in products:
            product = request.env['recycle.product'].sudo().browse(p['product_id'])
            if not product.exists():
                continue
            if order_type == 'factory':
                price = product.price_factory
            else:
                price = product.price_free_facility
            order_vals['line_ids'].append((0, 0, {
                'product_id': product.id,
                'quantity': p.get('quantity', 10.0),
                'price_unit': price,
            }))

        order = request.env['recycle.order'].sudo().create(order_vals)
        return {
            'success': True,
            'order_id': order.id,
            'order_name': order.name,
        }

    @http.route('/api/output/order/create-test-batch', type='jsonrpc', auth='user', methods=['POST'])
    def create_test_batch(self, count=5, **kwargs):
        """Create multiple test orders at once."""
        user = request.env.user.sudo()
        wh = user.recycle_warehouse_id
        if not wh:
            return {'error': 'No warehouse assigned'}

        prods = request.env['recycle.product'].sudo().search([], limit=5)
        if not prods:
            return {'error': 'No products found in system'}

        customers = [
            ('Factory Alpha', 'Ahmad Ali', 'alpha@test.com', 'factory'),
            ('Factory Beta', 'Sara Mohammad', 'beta@test.com', 'factory'),
            ('Free Facility Gamma', 'Omar Hassan', 'gamma@test.com', 'free_facility'),
            ('Factory Delta', 'Lina Khalil', 'delta@test.com', 'factory'),
            ('Free Facility Epsilon', 'Youssef Omar', 'epsilon@test.com', 'free_facility'),
        ]

        import random
        created = []
        for i in range(count):
            cname, oname, email, otype = customers[i % len(customers)]
            lines = []
            sample = random.sample(list(prods), min(random.randint(2, 4), len(prods)))
            for p in sample:
                if otype == 'factory':
                    price = p.price_factory
                else:
                    price = p.price_free_facility
                lines.append((0, 0, {
                    'product_id': p.id,
                    'quantity': float(random.randint(5, 50)),
                    'price_unit': price,
                }))
            order = request.env['recycle.order'].sudo().create({
                'customer_name': cname,
                'owner_name': oname,
                'customer_email': email,
                'warehouse_id': wh.id,
                'order_type': otype,
                'priority': random.randint(1, 20),
                'state': 'pending',
                'line_ids': lines,
            })
            created.append({'id': order.id, 'name': order.name, 'priority': order.priority, 'type': otype})

        return {'success': True, 'count': len(created), 'orders': created}

    @http.route('/api/output/order/<int:order_id>/print-invoice', type='http', auth='user', methods=['GET'])
    def print_invoice(self, order_id, **kwargs):
        """Download invoice PDF for a completed order."""
        order = request.env['recycle.order'].sudo().browse(order_id)
        if not order.exists():
            return request.not_found()
        if order.state != 'completed':
            return request.make_json_response({'error': 'Order not completed.'}, status=400)
        if not order.invoice_number:
            return request.make_json_response(
                {'error': 'No invoice has been generated for this order yet.'}, status=400)

        pdf_content, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'recycle_warehouse.report_order_invoice', res_ids=order.ids)
        filename = 'Invoice-%s.pdf' % (order.invoice_number or order.name)
        return request.make_response(pdf_content, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'attachment; filename="%s"' % filename),
        ])
