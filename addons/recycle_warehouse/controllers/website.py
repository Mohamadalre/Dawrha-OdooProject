# -*- coding: utf-8 -*-
import base64
import json
import random
import time
from datetime import timedelta
from html import escape as _esc

from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import AccessDenied
from odoo.tools import html2plaintext

# Escalating login-lockout thresholds: every 5 consecutive failed attempts
# triggers the next stage (1 min -> 2 min -> 24h, capped at stage 3).
RECYCLE_LOGIN_LOCKOUT_THRESHOLD = 5
RECYCLE_LOGIN_LOCKOUT_DURATIONS = {1: 60, 2: 120, 3: 24 * 3600}

APPLICATION_STATE_LABELS = {
    'applied': 'Applied',
    'interview': 'Interview',
    'accepted': 'Accepted',
    'rejected': 'Rejected',
}


try:
    from odoo.addons.website.controllers.main import Website as _WebsiteMain

    class DawrhaHome(_WebsiteMain):
        """Make the Dawrha home page the homepage of the whole website."""

        @http.route()
        def index(self, **kw):
            # Render the home page directly at "/" with a normal 200.
            # We must NOT return a redirect here: a 3xx response on the
            # homepage breaks the Website builder's preview iframe
            # (onIframeLoad reads contentDocument.body on a null document).
            return RecycleWebsiteController().home_page(**kw)
except ImportError:  # pragma: no cover
    pass

try:
    from odoo.addons.portal.controllers.portal import CustomerPortal as _Portal

    class DawrhaPortal(_Portal):
        """Replace the default portal home (/my) with the Dawrha account page."""

        @http.route()
        def home(self, **kw):
            return request.redirect('/account')
except ImportError:  # pragma: no cover
    pass


try:
    from odoo.addons.web.controllers.home import Home as _WebHome

    class DawrhaBackendGuard(_WebHome):
        """Route backend access through the Recycle experience.

        - The technical Odoo system administrator always keeps full direct
          access (so the instance can never be locked out).
        - Recycle staff (admin / manager / employee with a role) who land on
          the bare backend entry point are taken straight to their Recycle
          dashboard instead of the generic Odoo home.
        - Logged-in non-staff users (e.g. portal applicants) have no backend,
          so they are sent to the website.
        - After logging in, everyone lands on the website.
        """

        def _login_redirect(self, uid, redirect=None):
            # After a successful login EVERY role (user / employee / admin)
            # lands on the website Home page, unless an explicit redirect
            # was requested (e.g. deep link back to an apply form).
            if not redirect:
                return '/'
            return super()._login_redirect(uid, redirect=redirect)

        @http.route()
        def web_login(self, redirect=None, **kw):
            """Show a clear, bilingual message when a banned, inactive, or
            deleted account tries to sign in. Block authentication entirely
            for inactive/banned users so the site never opens for them.

            CSRF fix: Forces Cache-Control: no-store so the browser never
            serves a cached login page with a stale CSRF token.
            """
            if request.httprequest.method == 'POST':
                login = (kw.get('login') or '').strip().lower()
                user = False
                if login:
                    user = request.env['res.users'].sudo().with_context(
                        active_test=False).search(
                        [('login', '=', login)], limit=1)
                    is_ar = str(request.lang or 'en')[:2] == 'ar'
                    if user:
                        remaining = RecycleWebsiteController()._recycle_lockout_remaining(user)
                        if remaining > 0:
                            # Never test the submitted password while locked.
                            # Odoo core's web_login reads the credential from
                            # request.params directly (not from **kw), so the
                            # only way to force its own "wrong password"
                            # branch — guaranteeing a rendered qcontext, never
                            # a login-success redirect, and skipping the real
                            # bcrypt check during a lockout — is to override
                            # it there too.
                            request.params['password'] = '\x00recycle-locked\x00'
                            response = super().web_login(redirect=redirect, **kw)
                            response.headers['Cache-Control'] = 'no-store, max-age=0'
                            if request.session.uid:
                                request.session.logout()
                            if getattr(response, 'qcontext', None) is not None:
                                response.qcontext['error'] = RecycleWebsiteController(
                                    )._recycle_lockout_message(remaining, is_ar)
                                response.qcontext['recycle_login_locked'] = True
                            return response
                    if user and (user.recycle_banned or not user.active or user.recycle_deleted):
                        # Block authentication entirely — return the login
                        # page with an error so the site never opens.
                        response = super().web_login(redirect=redirect, **kw)
                        response.headers['Cache-Control'] = 'no-store, max-age=0'
                        # If super() somehow authenticated the user, kill the session
                        if request.session.uid:
                            request.session.logout()
                        if getattr(response, 'qcontext', None) is not None:
                            if user.recycle_banned:
                                if is_ar:
                                    msg = ('تم حظر حسابك. يرجى التواصل مع الإدارة '
                                           'لمزيد من المعلومات.')
                                else:
                                    msg = ('Your account has been banned. Please '
                                           'contact the administration for more '
                                           'information.')
                            elif not user.active:
                                if is_ar:
                                    msg = ('حسابك محظور. يرجى التواصل مع مدير مستودعك.')
                                else:
                                    msg = ('Your account is blocked. Please '
                                           'contact your warehouse manager.')
                            elif user.recycle_deleted:
                                if is_ar:
                                    msg = ('تم تسجيل طلبك. يرجى الانتظار حتى يتم '
                                           'التواصل معك من قبل قسم الموارد البشرية.')
                                else:
                                    msg = ('Your request has been registered. '
                                           'Please wait until you are contacted '
                                           'by the HR department.')
                                try:
                                    user._recycle_request_reactivation(employee_msg=msg)
                                except Exception:
                                    import logging as _log
                                    _log.getLogger(__name__).warning(
                                        'Failed to create reactivation request for user %s', user.id, exc_info=True)
                            response.qcontext['error'] = msg
                            response.qcontext.setdefault('recycle_login_locked', False)
                        return response
                # Normal login — not banned/inactive/deleted
                try:
                    response = super().web_login(redirect=redirect, **kw)
                except Exception:
                    return request.redirect('/web/login', code=302)
                response.headers['Cache-Control'] = 'no-store, max-age=0'
                if user:
                    if request.session.uid:
                        RecycleWebsiteController()._recycle_reset_login_lockout(user)
                        request.env['recycle.user.device'].sudo()._track(
                            request, request.session.uid, 'login')
                    else:
                        RecycleWebsiteController()._recycle_register_failed_login(user)
                if getattr(response, 'qcontext', None) is not None:
                    response.qcontext.setdefault('recycle_login_locked', False)
                return response
            # GET request
            response = super().web_login(redirect=redirect, **kw)
            response.headers['Cache-Control'] = 'no-store, max-age=0'
            if getattr(response, 'qcontext', None) is not None:
                response.qcontext.setdefault('recycle_login_locked', False)
            return response

        @http.route()
        def web_client(self, *args, **kw):
            user = request.env.user
            if user and not user._is_public():
                path = (request.httprequest.path or '').rstrip('/')
                is_bare = path in ('/odoo', '/web', '')
                # Typing /odoo (or /web) directly ALWAYS goes to the website,
                # for EVERYONE (employee, admin, even the system administrator).
                # The backend is reachable only through the website Account
                # page → 'Open Dashboard', which sets this session flag and
                # opens a deep action URL (allowed below).
                if is_bare or not request.session.get('recycle_dash_ok'):
                    return request.redirect('/')
            return super().web_client(*args, **kw)
except ImportError:  # pragma: no cover
    pass


class RecycleWebsiteController(http.Controller):

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_allowed_domain(self):
        domain = request.env['ir.config_parameter'].sudo().get_param(
            'recycle.allowed_email_domain', 'gmail.com')
        return (domain or '').strip().lstrip('@').lower()

    def _user_email(self):
        user = request.env.user
        return (user.email or user.login or '').strip().lower()

    def _nid_taken(self, nid, exclude_user=None):
        """Check if a National ID is already used by another user
        (excluding the current one). Returns the user record or False."""
        if not nid:
            return False
        domain = [('recycle_national_id', '=', nid)]
        if exclude_user:
            domain.append(('id', '!=', exclude_user.id))
        other = request.env['res.users'].sudo().search(domain, limit=1)
        return other if other else False

    def _email_allowed(self, email):
        domain = self._get_allowed_domain()
        if not domain:
            return True
        return email.endswith('@' + domain)

    def _recycle_authenticate(self, login, password):
        """Log the current session in. Handles the different
        Session.authenticate signatures across Odoo versions. Returns True on
        success, False on wrong credentials."""
        db = request.env.cr.dbname
        cred = {'login': login, 'password': password, 'type': 'password'}
        for args in ((db, cred), (cred,), (db, login, password)):
            try:
                request.session.authenticate(*args)
                if request.session.uid:
                    request.env['recycle.user.device'].sudo()._track(
                        request, request.session.uid, 'login')
                return True
            except AccessDenied:
                return False
            except Exception:
                continue
        return False

    def _recycle_lockout_remaining(self, user):
        """Seconds left in the current lockout, or 0 if not locked."""
        if not user or not user.recycle_locked_until:
            return 0
        remaining = (user.recycle_locked_until - fields.Datetime.now()).total_seconds()
        return max(0, int(remaining))

    def _recycle_lockout_message(self, remaining_seconds, is_ar):
        minutes = remaining_seconds // 60
        seconds = remaining_seconds % 60
        if remaining_seconds >= 3600:
            hours = remaining_seconds // 3600
            if is_ar:
                return _('تم قفل هذا الحساب مؤقتًا بسبب محاولات دخول خاطئة متكررة. '
                          'حاول مرة أخرى بعد حوالي %d ساعة.') % hours
            return _('This account is temporarily locked due to repeated failed '
                      'login attempts. Please try again in about %d hour(s).') % hours
        if is_ar:
            return _('تم قفل هذا الحساب مؤقتًا بسبب محاولات دخول خاطئة متكررة. '
                      'حاول مرة أخرى بعد %d دقيقة و%d ثانية.') % (minutes, seconds)
        return _('This account is temporarily locked due to repeated failed login '
                  'attempts. Please try again in %d minute(s) %d second(s).') % (minutes, seconds)

    def _recycle_register_failed_login(self, user):
        """Atomically increments the failed-attempt counter (safe under
        concurrent brute-force requests across multiple Odoo workers) and
        escalates to the next lockout stage every 5 consecutive failures."""
        cr = request.env.cr
        cr.execute("""
            UPDATE res_users
            SET recycle_failed_login_count = recycle_failed_login_count + 1
            WHERE id = %s
            RETURNING recycle_failed_login_count, recycle_lockout_stage
        """, [user.id])
        count, stage = cr.fetchone()
        if count >= RECYCLE_LOGIN_LOCKOUT_THRESHOLD:
            stage = min(stage + 1, 3)
            locked_until = fields.Datetime.now() + timedelta(
                seconds=RECYCLE_LOGIN_LOCKOUT_DURATIONS[stage])
            cr.execute("""
                UPDATE res_users
                SET recycle_failed_login_count = 0,
                    recycle_lockout_stage = %s,
                    recycle_locked_until = %s
                WHERE id = %s
            """, [stage, locked_until, user.id])
        user.invalidate_recordset([
            'recycle_failed_login_count', 'recycle_lockout_stage', 'recycle_locked_until'])

    def _recycle_reset_login_lockout(self, user):
        user.sudo().write({
            'recycle_failed_login_count': 0,
            'recycle_lockout_stage': 0,
            'recycle_locked_until': False,
        })

    def _is_recycle_staff(self, user=None):
        """An 'accepted employee' = internal user with a recycle role,
        a warehouse manager, or an administrator. Only these may open the
        Odoo backend dashboard."""
        user = user or request.env.user
        if user._is_public():
            return False
        if user.has_group('base.group_system'):
            return True
        if user.has_group('recycle_warehouse.group_recycle_admin'):
            return True
        # Delivery drivers are staff too, but they hold no warehouse role: they
        # work no shift and touch no stock. Without this line they log in
        # successfully and are bounced away from the only screen they have.
        if user.has_group('recycle_warehouse.group_recycle_delivery_driver'):
            return True
        return user.has_group('base.group_user') and bool(user.recycle_role)

    def _recycle_home_action_id(self, user=None):
        """Resolve the client-action id of the Recycle dashboard that matches
        the user's role, so 'Open Dashboard' lands straight on it."""
        user = user or request.env.user

        def _id(xmlid):
            rec = request.env.ref(xmlid, raise_if_not_found=False)
            return rec.id if rec else None

        if user.has_group('recycle_warehouse.group_recycle_admin'):
            return _id('recycle_warehouse.action_recycle_admin_home')
        if user.has_group('recycle_warehouse.group_recycle_manager'):
            return _id('recycle_warehouse.action_recycle_manager_home')
        if user.has_group('recycle_warehouse.group_recycle_delivery_driver'):
            return _id('recycle_warehouse.action_recycle_delivery_driver_home')
        role_map = {
            'input':       'recycle_warehouse.action_recycle_home',
            'sorting':     'recycle_warehouse.action_recycle_sorting_home',
            'output':      'recycle_warehouse.action_recycle_output_home',
            'delivery_driver':
                'recycle_warehouse.action_recycle_delivery_driver_home',
        }
        xmlid = role_map.get(user.recycle_role)
        action_id = _id(xmlid) if xmlid else None
        # Fallback for internal users without a specific role (e.g. the
        # technical system administrator): land on the admin dashboard so
        # 'Open Dashboard' always reaches a deep backend URL (never bare /odoo,
        # which would bounce back to the website).
        if not action_id and user.has_group('base.group_user'):
            action_id = _id('recycle_warehouse.action_recycle_admin_home')
        return action_id

    def _base_values(self, nav_active='home'):
        user = request.env.user
        is_public = user._is_public()
        is_admin = (not is_public) and user.has_group('recycle_warehouse.group_recycle_admin')
        has_accepted = False
        if not is_public:
            # Jobs must be hidden from ANY account holding an operational
            # role (manager / input / sorting / output) —
            # not only from users that came through recruitment and have an
            # hr.employee record. A manager created directly by the admin
            # has no hr.employee row, which used to leak the Jobs page.
            # Also check security groups directly — a user may have the
            # manager group assigned without recycle_role being set.
            operational_role = user.recycle_role and user.recycle_role != 'admin'
            has_manager_group = user.has_group('recycle_warehouse.group_recycle_manager')
            # A delivery driver is a delivery EMPLOYEE, not an applicant — the
            # Jobs page (openings + "apply") is not theirs. Their account is
            # created straight into the delivery-driver group with no hr.employee
            # row and often no recycle_role, so without this check the Jobs link
            # leaked into their site navigation.
            has_delivery_group = user.has_group(
                'recycle_warehouse.group_recycle_delivery_driver')
            has_accepted = bool(operational_role) or has_manager_group or (
                has_delivery_group) or bool(
                request.env['hr.employee'].sudo().search_count([
                    ('user_id', '=', user.id),
                ], limit=1))
        return {
            'is_public': is_public,
            'is_admin': is_admin,
            'is_staff': self._is_recycle_staff(user),
            'has_accepted_applicant': has_accepted,
            'nav_active': nav_active,
        }

    # ------------------------------------------------------------------
    # Logout (CSRF-proof)
    # ------------------------------------------------------------------
    @http.route(['/dawrha/logout'], type='http', auth='public',
                methods=['GET', 'POST'], csrf=False, sitemap=False)
    def dawrha_logout(self, **kwargs):
        """Log the current session out and land on a fresh login page.

        A plain GET route with csrf=False can never raise the
        '400 Session expired (invalid CSRF token)' error, whatever the
        session state is (fresh, rotated, or already expired). The
        no-store header guarantees the login page is re-fetched with a
        newly generated CSRF token."""
        if request.session.uid:
            request.env['recycle.user.device'].sudo()._track(
                request, request.session.uid, 'logout')
        try:
            request.session.logout(keep_db=True)
        except Exception:
            pass
        response = request.redirect('/web/login', code=303)
        response.headers['Cache-Control'] = 'no-store, max-age=0'
        return response

    # ------------------------------------------------------------------
    # About page
    # ------------------------------------------------------------------
    @http.route(['/about'], type='http', auth='public', website=True, sitemap=True)
    def about_page(self, **kwargs):
        values = self._base_values('about')
        return request.render('recycle_warehouse.about_page', values)

    # ------------------------------------------------------------------
    # Home page
    # ------------------------------------------------------------------
    def home_page(self, **kwargs):
        """Public landing page. Every figure is computed live from the
        database — no static/mock numbers (spec §5)."""
        env = request.env
        warehouse_count = env['recycle.warehouse'].sudo().search_count([])
        employee_count = env['hr.employee'].sudo().search_count([])
        order_count = env['recycle.order'].sudo().search_count(
            [('state', '!=', 'cancelled')])

        # Tons recycled = total actual weight (kg) of shipments that finished
        # processing (accepted or fully sorted), converted to tons.
        # Computed as two server-side SUMs (not a Python loop over every
        # shipment row ever created) so this public, unauthenticated page
        # stays fast no matter how much history accumulates.
        Shipment = env['recycle.shipment'].sudo()
        processed_domain = [('state', 'in', ('accepted', 'sorting', 'sorted'))]
        actual_sum = Shipment._read_group(
            processed_domain + [('actual_weight', '!=', 0)],
            aggregates=['actual_weight:sum'])[0][0] or 0.0
        fallback_sum = Shipment._read_group(
            processed_domain + [('actual_weight', '=', 0)],
            aggregates=['expected_weight:sum'])[0][0] or 0.0
        total_kg = actual_sum + fallback_sum
        tons_recycled = round(total_kg / 1000.0, 1)

        # Month-over-month growth of processed shipments (value/total, §charts).
        from datetime import date, timedelta
        today = date.today()
        month_start = today.replace(day=1)
        prev_month_end = month_start - timedelta(days=1)
        prev_month_start = prev_month_end.replace(day=1)
        this_month = Shipment.search_count(
            [('create_date', '>=', str(month_start))])
        prev_month = Shipment.search_count([
            ('create_date', '>=', str(prev_month_start)),
            ('create_date', '<', str(month_start))])
        if prev_month:
            growth_pct = round((this_month - prev_month) / prev_month * 100.0)
        else:
            growth_pct = 100 if this_month else 0

        values = self._base_values('home')
        values.update({
            'warehouse_count': warehouse_count,
            'employee_count': employee_count,
            'order_count': order_count,
            'tons_recycled': tons_recycled,
            'growth_display': '%+d%%' % growth_pct,
        })
        return request.render('recycle_warehouse.home_page', values)

    # ------------------------------------------------------------------
    # Jobs list
    # ------------------------------------------------------------------
    @http.route(['/jobs'], type='http', auth='public', website=True, sitemap=True)
    def jobs_list(self, **kwargs):
        values = self._base_values('openings')
        # Admins also see unpublished jobs (marked with a badge in the UI);
        # everyone else only sees published openings.
        domain = [] if values['is_admin'] else [('recycle_publish', '=', True)]
        jobs = request.env['hr.job'].sudo().search(domain, order='name')
        excerpts = {}
        for job in jobs:
            text = html2plaintext(job.recycle_description or '').strip()
            excerpts[job.id] = (text[:120] + '…') if len(text) > 120 else text
        values.update({
            'jobs': jobs,
            'excerpts': excerpts,
        })
        return request.render('recycle_warehouse.jobs_list_page', values)

    # ------------------------------------------------------------------
    # Job detail
    # ------------------------------------------------------------------
    @http.route(['/jobs/<int:job_id>'], type='http', auth='public', website=True,
                sitemap=False)
    def job_detail(self, job_id, **kwargs):
        job = request.env['hr.job'].sudo().browse(job_id).exists()
        values = self._base_values('openings')
        # Unpublished jobs stay reachable for admins only.
        if not job or (not job.recycle_publish and not values['is_admin']):
            return request.not_found()
        values.update({'job': job})
        return request.render('recycle_warehouse.job_detail_page', values)

    # ------------------------------------------------------------------
    # Apply (login required)
    # ------------------------------------------------------------------
    @http.route(['/jobs/apply/<int:job_id>'], type='http', auth='user',
                website=True, methods=['GET', 'POST'], sitemap=False)
    def job_apply(self, job_id, **post):
        job = request.env['hr.job'].sudo().browse(job_id).exists()
        if not job or not job.recycle_publish:
            return request.not_found()

        # Administrators manage jobs and cannot apply to them.
        if request.env.user.has_group('recycle_warehouse.group_recycle_admin'):
            return request.redirect(f'/jobs/{job.id}?noadmin=1')

        user = request.env.user
        email = self._user_email()
        errors = []
        user_nid = (user.recycle_national_id or '').strip()

        # Language preference: from hidden form field (JS toggle) or request.lang
        dw_lang = post.get('dw_lang') or str(request.lang or 'en')
        dw_lang = dw_lang[:2]
        is_ar = dw_lang == 'ar'

        values = self._base_values('openings')
        values.update({
            'job': job,
            'email': email,
            'phone': post.get('phone', user.phone or ''),
            'national_id': user_nid,
            'errors': errors,
            'user_has_nid': bool(user_nid),
        })

        # Check if user has a National ID in their profile
        if not user_nid and not user.has_group('recycle_warehouse.group_recycle_admin'):
            return request.redirect(f'/jobs/apply/{job.id}/complete-profile')

        Applicant = request.env['hr.applicant'].sudo()

        # Email domain restriction
        if not self._email_allowed(email):
            values['domain_blocked'] = self._get_allowed_domain()
            return request.render('recycle_warehouse.job_apply_page', values)

        if request.httprequest.method == 'POST':
            phone = (post.get('phone') or '').strip()
            description = (post.get('description') or '').strip()
            profile_url = (post.get('profile_url') or '').strip()
            values.update({'description': description, 'profile_url': profile_url})
            files = request.httprequest.files.getlist('attachments')
            files = [f for f in files if f and f.filename]

            if not phone or len(phone) < 6:
                errors.append(_('Please enter a valid phone number.'))
            if not files:
                errors.append(_('Please upload at least one file (CV is required).'))
            if profile_url and not (profile_url.startswith('http://')
                                    or profile_url.startswith('https://')):
                errors.append(_('Profile link must start with http:// or https://'))

            # Duplicate checks -> language-aware popup (Dawrha modal)
            dup_error = False
            dup_type = None
            dup_title = ''
            dup_msg = ''
            if Applicant.search_count([
                    ('job_id', '=', job.id),
                    ('recycle_email', '=', email),
                    ('recycle_account_deleted', '!=', True)]):
                dup_error = True
                dup_type = 'same_job'
                if is_ar:
                    dup_title = 'مسجل مسبقاً'
                    dup_msg = (
                        'لقد تقدمت بالفعل لهذه الوظيفة.<br><br>'
                        'يرجى التحقق من حالة طلبك في قسم '
                        '<a href="/my/jobs">طلباتي</a>.'
                    )
                else:
                    dup_title = 'Already Registered'
                    dup_msg = (
                        'You have already applied for this position.<br><br>'
                        'Please check your application status in '
                        '<a href="/my/jobs">My Applications</a>.'
                    )
            elif user_nid and Applicant.search_count([
                    ('recycle_national_id', '=', user_nid),
                    ('recycle_email', '!=', email),
                    ('recycle_account_deleted', '!=', True)]):
                dup_error = True
                dup_type = 'other_nid_taken'
                if is_ar:
                    dup_title = 'الرقم الوطني مستخدم'
                    dup_msg = (
                        'هذا الرقم الوطني مسجل بالفعل لمقدم طلب آخر.<br><br>'
                        'إذا كان هذا خطأ، يرجى التواصل مع الإدارة.'
                    )
                else:
                    dup_title = 'National ID In Use'
                    dup_msg = (
                        'This National ID is already registered by another applicant.<br><br>'
                        'If you believe this is an error, please contact administration.'
                    )
            # Check if this user already applied with a *different* National ID
            if email and user_nid and not dup_error:
                old_app = Applicant.search([
                    ('recycle_email', '=', email),
                    ('recycle_national_id', '!=', False),
                    ('job_id', '!=', job.id),
                    ('recycle_account_deleted', '!=', True),
                ], limit=1, order='create_date asc')
                if old_app and old_app.recycle_national_id != user_nid:
                    values['nid_mismatch'] = old_app.recycle_national_id
                    dup_error = True
                    dup_type = 'nid_mismatch'
                    if is_ar:
                        dup_title = 'الرقم الوطني غير متطابق'
                        dup_msg = (
                            'لقد تقدمت سابقاً باستخدام رقم وطني مختلف:<br><br>'
                            '<strong style="font-size:24px;color:var(--g400);display:block;text-align:center;">%s</strong><br>'
                            'يرجى استخدام نفس الرقم الوطني لجميع الطلبات.'
                        ) % old_app.recycle_national_id
                    else:
                        dup_title = 'National ID Mismatch'
                        dup_msg = (
                            'You previously applied using a different National ID:<br><br>'
                            '<strong style="font-size:24px;color:var(--g400);display:block;text-align:center;">%s</strong><br>'
                            'Please use the same National ID for all applications.'
                        ) % old_app.recycle_national_id

            if dup_error:
                values['dup_error'] = True
                values['dup_type'] = dup_type
                values['dup_title'] = dup_title
                values['dup_msg'] = dup_msg

            if not errors and not dup_error:
                vals = {
                    'job_id': job.id,
                    'recycle_name': user.name,
                    'recycle_email': email,
                    'recycle_phone': phone,
                    'recycle_national_id': user_nid,
                    'recycle_cover_letter': description or False,
                    'recycle_profile_url': profile_url or False,
                    'recycle_state': 'applied',
                }
                # Link to hr.candidate when the version uses it,
                # otherwise set standard fields if they exist.
                if 'candidate_id' in Applicant._fields and 'hr.candidate' in request.env:
                    candidate_vals = {'partner_name': user.name}
                    Candidate = request.env['hr.candidate'].sudo()
                    if 'email_from' in Candidate._fields:
                        candidate_vals['email_from'] = email
                    if 'partner_phone' in Candidate._fields:
                        candidate_vals['partner_phone'] = phone
                    vals['candidate_id'] = Candidate.create(candidate_vals).id
                else:
                    for fname, fval in (('partner_name', user.name),
                                        ('email_from', email),
                                        ('partner_phone', phone)):
                        if fname in Applicant._fields:
                            vals[fname] = fval
                applicant = Applicant.create(vals)

                Attachment = request.env['ir.attachment'].sudo()
                for f in files:
                    content = f.read()
                    if not content:
                        continue
                    Attachment.create({
                        'name': f.filename,
                        'datas': base64.b64encode(content),
                        'res_model': 'hr.applicant',
                        'res_id': applicant.id,
                    })
                return request.redirect('/my/applications?applied=1')

        return request.render('recycle_warehouse.job_apply_page', values)

    # ------------------------------------------------------------------
    # Account page (Dawrha design)
    # ------------------------------------------------------------------
    def _account_values(self, **extra):
        user = request.env.user
        lang = str(request.lang or 'en')
        is_ar = lang[:2] == 'ar'
        if is_ar:
            role_labels = {
                'admin': 'الإدارة العامة',
                'manager': 'مدير مستودع',
                'input': 'موظف استقبال',
                'sorting': 'موظف فرز',
                'output': 'موظف إخراج',
            }
            default_role = 'مقدم طلب'
            admin_label = 'الإدارة العامة'
        else:
            role_labels = {
                'admin': 'Administration',
                'manager': 'Warehouse Manager',
                'input': 'Input Employee',
                'sorting': 'Sorting Employee',
                'output': 'Output Employee',
            }
            default_role = 'Applicant'
            admin_label = 'Administration'
        is_admin_user = user.has_group('recycle_warehouse.group_recycle_admin')
        if is_admin_user:
            account_role = admin_label
        else:
            account_role = role_labels.get(user.recycle_role, default_role)

        # Recent activity: show current status for the employee
        Applicant = request.env['hr.applicant'].sudo()
        my_email = self._user_email()
        applications_count = Applicant.search_count(
            [('recycle_email', '=', my_email)])
        role_labels = {
            'admin': 'الإدارة العامة' if is_ar else 'Administration',
            'manager': 'مدير مستودع' if is_ar else 'Warehouse Manager',
            'input': 'موظف استقبال' if is_ar else 'Input Employee',
            'sorting': 'موظف فرز' if is_ar else 'Sorting Employee',
            'output': 'موظف إخراج' if is_ar else 'Output Employee',
        }
        recent_activity = []

        # Show current role/status as activity
        if user.recycle_role and user.recycle_role != 'admin':
            recent_activity.append({
                'title': role_labels.get(user.recycle_role, user.recycle_role),
                'stage': 'Current Assignment',
                'date': user.create_date.strftime('%Y-%m-%d') if user.create_date else '',
                'status': 'approved' if user.active else 'rejected',
                'status_css': 'st-accepted' if user.active else 'st-rejected',
            })

        # Sort by date descending
        recent_activity.sort(key=lambda x: x.get('date', ''), reverse=True)
        recent_activity = recent_activity[:10]
        values = self._base_values('account')
        user_nid = (user.recycle_national_id or '').strip()
        # Show a photo only when the user really uploaded one — stock Odoo
        # avatars (e.g. the default admin image) fall back to the
        # first-letter avatar instead.
        img = user.image_1920 if user.recycle_avatar_custom else False
        img_uri = ''
        if img:
            img_uri = 'data:image/png;base64,' + img.decode()
        addr_parts = [p for p in [user.street or '', user.city or ''] if p]
        account_address = ', '.join(addr_parts) if addr_parts else ''
        values.update({
            'account_name': user.name,
            'account_email': user.email or user.login,
            'account_role': account_role,
            'account_warehouse': user.recycle_warehouse_id.name or '',
            'account_national_id': user_nid,
            'user_has_nid': bool(user_nid),
            'account_image_uri': img_uri,
            'account_address': account_address,
            'account_street': user.street or '',
            'account_city': user.city or '',
            'is_internal': user.has_group('base.group_user'),
            'is_admin_user': is_admin_user,
            'applications_count': applications_count,
            'recent_activity': recent_activity,
            'member_since': user.create_date.strftime('%Y-%m-%d') if user.create_date else '',
            'pwd_error': None,
            'pwd_success': False,
            'no_dashboard': False,
        })
        values.update(extra)
        return values

    @http.route(['/account'], type='http', auth='user', website=True,
                sitemap=False)
    def account(self, **kwargs):
        return request.render(
            'recycle_warehouse.account_page',
            self._account_values(
                pwd_success=(kwargs.get('pwd') == '1'),
                no_dashboard=(kwargs.get('nodash') == '1'),
                saved_nid=(kwargs.get('saved_nid') == '1'),
            ),
        )

    # ------------------------------------------------------------------
    # Change password (from the website Account page)
    # ------------------------------------------------------------------
    @http.route(['/account/change-password'], type='http', auth='user',
                website=True, methods=['POST'], sitemap=False)
    def account_change_password(self, **post):
        user = request.env.user
        old_pw     = post.get('old_password') or ''
        new_pw     = post.get('new_password') or ''
        confirm_pw = post.get('confirm_password') or ''

        error = None
        if not old_pw or not new_pw:
            error = _('Please fill in all password fields.')
        elif len(new_pw) < 6:
            error = _('New password must be at least 6 characters.')
        elif new_pw != confirm_pw:
            error = _('New password and confirmation do not match.')
        elif new_pw == old_pw:
            error = _('New password must be different from the current one.')
        else:
            try:
                # change_password verifies the old password and raises when it
                # is wrong. Run it inside a savepoint so a failed attempt is
                # rolled back cleanly and the transaction stays usable for
                # rendering the error page (otherwise the cursor is aborted).
                with request.env.cr.savepoint():
                    request.env.user.change_password(old_pw, new_pw)
            except Exception:
                error = _('Your current password is incorrect.')

        if error:
            return request.render(
                'recycle_warehouse.account_page',
                self._account_values(pwd_error=error),
            )

        # Log the user out and send them to a freshly-loaded login page to
        # sign in again with the new password. Loading /web/login fresh after
        # logout guarantees a valid CSRF token, so the login never shows the
        # "Session expired (invalid CSRF token)" 400 page.
        try:
            request.session.logout(keep_db=True)
        except Exception:
            pass
        return request.redirect('/web/login?password_changed=1')

    # ------------------------------------------------------------------
    # Save National ID (from Account page)
    # ------------------------------------------------------------------
    @http.route(['/account/save-nid'], type='http', auth='user',
                website=True, methods=['POST'], sitemap=False)
    def account_save_nid(self, **post):
        nid = (post.get('national_id') or '').strip()
        error = None
        user = request.env.user
        lang = post.get('dw_lang') or str(request.lang or 'en')
        lang = 'ar' if lang[:2] == 'ar' else 'en'
        is_ar = lang == 'ar'
        if not nid.isdigit() or not (5 <= len(nid) <= 20):
            if is_ar:
                error = 'يجب أن يحتوي الرقم الوطني على أرقام فقط (5 إلى 20 رقماً).'
            else:
                error = 'National ID must contain only digits (5 to 20 characters).'
        elif self._nid_taken(nid, exclude_user=user):
            if is_ar:
                error = 'هذا الرقم الوطني مستخدم بالفعل من قبل شخص آخر.'
            else:
                error = 'This National ID is already in use by another person.'
        else:
            user.sudo().write({'recycle_national_id': nid})
            return request.redirect('/account?saved_nid=1')
        return request.render(
            'recycle_warehouse.account_page',
            self._account_values(nid_error=error, nid_val=nid),
        )

    # ------------------------------------------------------------------
    # Edit Profile (from Account page)
    # ------------------------------------------------------------------
    @http.route(['/account/edit-profile'], type='http', auth='user',
                website=True, methods=['POST'], sitemap=False)
    def account_edit_profile(self, **post):
        user = request.env.user
        name = (post.get('name') or '').strip()
        street = (post.get('street') or '').strip()
        city = (post.get('city') or '').strip()
        nid = (post.get('national_id') or '').strip()
        error = None
        lang = post.get('dw_lang') or str(request.lang or 'en')
        is_ar = lang[:2] == 'ar'

        vals = {}
        if name:
            vals['name'] = name

        # NID validation (allow editing even if already saved; admin exempt)
        if nid and not user.has_group('recycle_warehouse.group_recycle_admin'):
            if not nid.isdigit() or not (5 <= len(nid) <= 20):
                if is_ar:
                    error = 'يجب أن يحتوي الرقم الوطني على أرقام فقط (5 إلى 20 رقماً).'
                else:
                    error = 'National ID must contain only digits (5 to 20 characters).'
            elif self._nid_taken(nid, exclude_user=user):
                if is_ar:
                    error = 'هذا الرقم الوطني مستخدم بالفعل من قبل شخص آخر.'
                else:
                    error = 'This National ID is already in use by another person.'
            else:
                vals['recycle_national_id'] = nid

        if not error:
            if street:
                vals['street'] = street
            if city:
                vals['city'] = city
            # Profile image upload
            image_file = request.httprequest.files.get('profile_image')
            if image_file and image_file.filename:
                content = image_file.read()
                if content:
                    vals['image_1920'] = base64.b64encode(content)
                    vals['recycle_avatar_custom'] = True
            if vals:
                user.sudo().write(vals)
            return request.redirect('/account')

        return request.render(
            'recycle_warehouse.account_page',
            self._account_values(nid_error=error),
        )

    # ------------------------------------------------------------------
    # Complete profile (before applying)
    # ------------------------------------------------------------------
    @http.route(['/jobs/apply/<int:job_id>/complete-profile'],
                type='http', auth='user', website=True,
                methods=['GET', 'POST'], sitemap=False)
    def apply_complete_profile(self, job_id, **post):
        job = request.env['hr.job'].sudo().browse(job_id).exists()
        if not job or not job.recycle_publish:
            return request.not_found()

        user = request.env.user
        user_nid = (user.recycle_national_id or '').strip()
        # If NID already saved, redirect straight to the apply form
        if user_nid or user.has_group('recycle_warehouse.group_recycle_admin'):
            return request.redirect(f'/jobs/apply/{job.id}')

        # Language
        dw_lang = post.get('dw_lang') or str(request.lang or 'en')
        dw_lang = 'ar' if dw_lang[:2] == 'ar' else 'en'
        is_ar = dw_lang == 'ar'

        if request.httprequest.method == 'POST':
            nid = (post.get('national_id') or '').strip()
            street = (post.get('street') or '').strip()
            city = (post.get('city') or '').strip()
            error = None

            if not nid.isdigit() or not (5 <= len(nid) <= 20):
                if is_ar:
                    error = 'يجب أن يحتوي الرقم الوطني على أرقام فقط (5 إلى 20 رقماً).'
                else:
                    error = 'National ID must contain only digits (5 to 20 characters).'
            elif self._nid_taken(nid, exclude_user=user):
                # Another person already registered this National ID.
                if is_ar:
                    error = 'هذا الرقم الوطني مستخدم بالفعل من قبل شخص آخر.'
                else:
                    error = 'This National ID is already in use by another person.'
            else:
                # Save to user profile
                vals = {'recycle_national_id': nid}
                if street:
                    vals['street'] = street
                if city:
                    vals['city'] = city
                # Handle profile image upload
                image_file = request.httprequest.files.get('profile_image')
                if image_file and image_file.filename:
                    content = image_file.read()
                    if content:
                        vals['image_1920'] = base64.b64encode(content)
                user.sudo().write(vals)
                return request.redirect(f'/jobs/apply/{job.id}')

            # Render with error
            values = self._base_values('openings')
            values.update({
                'job': job,
                'nid_val': nid,
                'street_val': street,
                'city_val': city,
                'error': error,
            })
            return request.render('recycle_warehouse.profile_complete_page', values)

        values = self._base_values('openings')
        values.update({
            'job': job,
            'nid_val': '',
            'street_val': user.street or '',
            'city_val': user.city or '',
            'error': None,
        })
        return request.render('recycle_warehouse.profile_complete_page', values)

    # ------------------------------------------------------------------
    # Profile Completion Page (full, bilingual, standalone)
    # ------------------------------------------------------------------
    # Accepted CV extensions and helper validators kept here so both the
    # server and (mirrored) the JS enforce the exact same rules.
    _CV_EXTS = ('.pdf', '.doc', '.docx')

    def _pc_lang(self, post):
        """Resolve the active website language ('ar' or 'en') from the JS
        hidden field, falling back to the request language."""
        lang = post.get('dw_lang') or str(request.lang or 'en')
        return 'ar' if lang[:2] == 'ar' else 'en'

    def _pc_msg(self, key, is_ar):
        """Bilingual message catalogue for the profile page (server side).
        Mirrors the keys used in static/src/js/profile_completion.js so the
        experience is identical whether validation fires on client or server."""
        ar = {
            'saved':        'تم حفظ البيانات بنجاح',
            'required':     'الرجاء ملء جميع الحقول المطلوبة',
            'bad_email':    'البريد الإلكتروني غير صحيح',
            'bad_phone':    'رقم الهاتف يجب أن يحتوي على أرقام فقط',
            'bad_cv':       'اسمح فقط ملفات PDF أو Word',
            'bad_nid':      'يجب أن يحتوي الرقم الوطني على أرقام فقط (5 إلى 20 رقماً).',
            'nid_taken':    'هذا الرقم الوطني مستخدم بالفعل من قبل شخص آخر.',
            'dup_title':    'طلب موجود مسبقاً',
            'dup_msg':      'أنت قد قدمت على هذه الوظيفة من قبل. هل تريد تحديث طلبك؟',
            'updated':      'تم تحديث طلبك بنجاح',
        }
        en = {
            'saved':        'Data saved successfully',
            'required':     'Please fill all required fields',
            'bad_email':    'Invalid email',
            'bad_phone':    'Phone must contain only numbers',
            'bad_cv':       'Only PDF or Word files allowed',
            'bad_nid':      'National ID must contain only digits (5 to 20 characters).',
            'nid_taken':    'This National ID is already in use by another person.',
            'dup_title':    'Application already exists',
            'dup_msg':      'You have already applied for this position. Do you want to update your application?',
            'updated':      'Your application has been updated successfully',
        }
        return (ar if is_ar else en).get(key, key)

    def _pc_values(self, is_ar, **extra):
        """Base render context for the profile completion page: current user
        prefill + the list of open positions to choose from."""
        user = request.env.user
        # Split the stored full name into first / last for the two inputs.
        parts = (user.name or '').strip().split(' ', 1)
        first = parts[0] if parts else ''
        last = parts[1] if len(parts) > 1 else ''
        jobs = request.env['hr.job'].sudo().search(
            [('recycle_publish', '=', True)], order='name')
        values = self._base_values('account')
        values.update({
            'jobs': jobs,
            'pc_first_name': user.name and first or '',
            'pc_last_name': last,
            'pc_email': user.email or user.login or '',
            'pc_phone': user.phone or '',
            'pc_street': user.street or '',
            'pc_city': user.city or '',
            'pc_country': user.country_id.name or '',
            'pc_national_id': (user.recycle_national_id or '').strip(),
            'pc_job_id': '',
            'pc_company_name': '',
            'pc_company_type': '',
            'pc_experience': '',
            'errors': [],
            'success_msg': None,
            'dup_error': False,
            'dup_title': '',
            'dup_msg': '',
            'dup_job_id': '',
        })
        values.update(extra)
        return values

    @http.route(['/profile/complete'], type='http', auth='user',
                website=True, methods=['GET', 'POST'], sitemap=False)
    def complete_profile(self, **post):
        """Standalone profile completion page.

        * Fully bilingual (Arabic / English) driven by the website language.
        * Server-side validation for every field (email, phone, CV type,
          National ID) with language-aware messages.
        * Duplicate-application detection: if the user already applied for the
          selected position, a bilingual confirmation prompt is shown; on
          confirmation the existing application is updated instead of duplicated.
        """
        user = request.env.user
        is_ar = self._pc_lang(post)

        # Administrators manage the platform and do not fill applicant profiles.
        if user.has_group('recycle_warehouse.group_recycle_admin'):
            return request.redirect('/account')

        if request.httprequest.method != 'POST':
            saved = post.get('saved')
            success_msg = None
            if saved == '1':
                success_msg = self._pc_msg('saved', is_ar)
            elif saved == '2':
                success_msg = self._pc_msg('updated', is_ar)
            return request.render(
                'recycle_warehouse.profile_completion_page',
                self._pc_values(is_ar, success_msg=success_msg),
            )

        # ── Collect submitted values ──────────────────────────────────
        f = {
            'first_name':   (post.get('first_name') or '').strip(),
            'last_name':    (post.get('last_name') or '').strip(),
            'email':        (post.get('email') or '').strip(),
            'phone':        (post.get('phone') or '').strip(),
            'street':       (post.get('street') or '').strip(),
            'city':         (post.get('city') or '').strip(),
            'country':      (post.get('country') or '').strip(),
            'job_id':       (post.get('job_id') or '').strip(),
            'company_name': (post.get('company_name') or '').strip(),
            'company_type': (post.get('company_type') or '').strip(),
            'experience':   (post.get('experience') or '').strip(),
            'national_id':  (post.get('national_id') or '').strip(),
            'id_expiry':    (post.get('id_expiry') or '').strip(),
        }
        confirm_update = post.get('confirm_update') == '1'

        cv_file = request.httprequest.files.get('cv_file')
        extra_files = [x for x in request.httprequest.files.getlist('extra_docs')
                       if x and x.filename]

        errors = []

        # Required fields
        required = ['first_name', 'last_name', 'email', 'phone', 'job_id',
                    'company_name', 'company_type', 'national_id']
        if any(not f[k] for k in required):
            errors.append(self._pc_msg('required', is_ar))

        # Email format
        import re
        email_re = r'^[^@\s]+@[^@\s]+\.[^@\s]+$'
        if f['email'] and not re.match(email_re, f['email']):
            errors.append(self._pc_msg('bad_email', is_ar))

        # Phone: digits only (allow leading + and spaces stripped)
        phone_digits = f['phone'].replace('+', '').replace(' ', '')
        if f['phone'] and not phone_digits.isdigit():
            errors.append(self._pc_msg('bad_phone', is_ar))

        # National ID: digits, 5–20
        if f['national_id'] and (not f['national_id'].isdigit()
                                 or not (5 <= len(f['national_id']) <= 20)):
            errors.append(self._pc_msg('bad_nid', is_ar))
        elif f['national_id'] and self._nid_taken(f['national_id'], exclude_user=user):
            errors.append(self._pc_msg('nid_taken', is_ar))

        # CV: required + must be PDF / Word
        has_cv = bool(cv_file and cv_file.filename)
        if not has_cv:
            errors.append(self._pc_msg('bad_cv', is_ar))
        elif not cv_file.filename.lower().endswith(self._CV_EXTS):
            errors.append(self._pc_msg('bad_cv', is_ar))

        # Extra documents (optional) must also be PDF / Word if provided
        for x in extra_files:
            if not x.filename.lower().endswith(self._CV_EXTS):
                errors.append(self._pc_msg('bad_cv', is_ar))
                break

        job = None
        if f['job_id']:
            job = request.env['hr.job'].sudo().browse(int(f['job_id'])).exists()
            if not job or not job.recycle_publish:
                errors.append(self._pc_msg('required', is_ar))
                job = None

        # Re-render with errors, keeping the entered values.
        if errors:
            return request.render(
                'recycle_warehouse.profile_completion_page',
                self._pc_values(
                    is_ar,
                    errors=errors,
                    pc_first_name=f['first_name'], pc_last_name=f['last_name'],
                    pc_email=f['email'], pc_phone=f['phone'],
                    pc_street=f['street'], pc_city=f['city'],
                    pc_country=f['country'], pc_national_id=f['national_id'],
                    pc_job_id=f['job_id'], pc_company_name=f['company_name'],
                    pc_company_type=f['company_type'], pc_experience=f['experience'],
                ),
            )

        # ── Duplicate application detection ───────────────────────────
        Applicant = request.env['hr.applicant'].sudo()
        existing = Applicant.search([
            ('job_id', '=', job.id),
            ('recycle_email', '=', f['email']),
            ('recycle_account_deleted', '!=', True),
        ], limit=1, order='create_date desc')

        if existing and not confirm_update:
            return request.render(
                'recycle_warehouse.profile_completion_page',
                self._pc_values(
                    is_ar,
                    dup_error=True,
                    dup_title=self._pc_msg('dup_title', is_ar),
                    dup_msg=self._pc_msg('dup_msg', is_ar),
                    dup_job_id=f['job_id'],
                    pc_first_name=f['first_name'], pc_last_name=f['last_name'],
                    pc_email=f['email'], pc_phone=f['phone'],
                    pc_street=f['street'], pc_city=f['city'],
                    pc_country=f['country'], pc_national_id=f['national_id'],
                    pc_job_id=f['job_id'], pc_company_name=f['company_name'],
                    pc_company_type=f['company_type'], pc_experience=f['experience'],
                ),
            )

        # ── Persist standard profile fields on the user ───────────────
        full_name = (f['first_name'] + ' ' + f['last_name']).strip()
        user_vals = {'name': full_name or user.name}
        if f['phone']:
            user_vals['phone'] = f['phone']
        if f['street']:
            user_vals['street'] = f['street']
        if f['city']:
            user_vals['city'] = f['city']
        if f['national_id']:
            user_vals['recycle_national_id'] = f['national_id']
        if f['country']:
            country = request.env['res.country'].sudo().search(
                [('name', 'ilike', f['country'])], limit=1)
            if country:
                user_vals['country_id'] = country.id
        user.sudo().write(user_vals)

        # ── Build a structured cover-letter block that carries the extra
        #    employment info (no schema change needed) ─────────────────
        cover = "\n".join([
            "Job Position: %s" % (job.name or ''),
            "Company Name: %s" % f['company_name'],
            "Company Type: %s" % f['company_type'],
            "Years of Experience: %s" % (f['experience'] or '-'),
            "National ID Expiry: %s" % (f['id_expiry'] or '-'),
            "Address: %s, %s, %s" % (f['street'], f['city'], f['country']),
        ])

        app_vals = {
            'job_id': job.id,
            'recycle_name': full_name,
            'recycle_email': f['email'],
            'recycle_phone': phone_digits,
            'recycle_national_id': f['national_id'],
            'recycle_cover_letter': cover,
            'recycle_state': 'applied',
        }
        for fname, fval in (('partner_name', full_name),
                            ('email_from', f['email']),
                            ('partner_phone', phone_digits)):
            if fname in Applicant._fields:
                app_vals[fname] = fval

        if existing:
            existing.write(app_vals)
            applicant = existing
            success_key = 'updated'
        else:
            applicant = Applicant.create(app_vals)
            success_key = 'saved'

        # ── Attach CV + additional documents ──────────────────────────
        Attachment = request.env['ir.attachment'].sudo()
        for upload in ([cv_file] + extra_files):
            if not (upload and upload.filename):
                continue
            content = upload.read()
            if not content:
                continue
            Attachment.create({
                'name': upload.filename,
                'datas': base64.b64encode(content),
                'res_model': 'hr.applicant',
                'res_id': applicant.id,
            })

        return request.redirect('/profile/complete?saved=%s' % (
            '2' if success_key == 'updated' else '1'))

    # ------------------------------------------------------------------
    # Open Odoo dashboard (accepted employees / admins only)
    # ------------------------------------------------------------------
    @http.route(['/recycle/open-dashboard'], type='http', auth='user',
                website=True, sitemap=False)
    def open_dashboard(self, **kwargs):
        if not self._is_recycle_staff():
            return request.redirect('/account?nodash=1')
        # Grant this session permission to reach the backend, then open the
        # Recycle dashboard that matches the user's role directly.
        request.session['recycle_dash_ok'] = True
        action_id = self._recycle_home_action_id()
        if action_id:
            return request.redirect('/odoo/action-%s' % action_id)
        # No backend landing available → keep them on the website.
        return request.redirect('/account?nodash=1')

    # ------------------------------------------------------------------
    # Admin: My Jobs (jobs created by this admin + applicant counts)
    # ------------------------------------------------------------------
    @http.route(['/my/jobs'], type='http', auth='user', website=True,
                sitemap=False)
    def my_jobs(self, **kwargs):
        user = request.env.user
        if not user.has_group('recycle_warehouse.group_recycle_admin'):
            return request.redirect('/account')
        jobs = request.env['hr.job'].sudo().search(
            [('create_uid', '=', user.id)], order='create_date desc')
        Applicant = request.env['hr.applicant'].sudo()
        rows = []
        for job in jobs:
            rows.append({
                'job': job,
                'applicants': Applicant.search_count([('job_id', '=', job.id)]),
            })
        values = self._base_values('myjobs')
        values.update({'rows': rows})
        return request.render('recycle_warehouse.admin_jobs_page', values)

    # ------------------------------------------------------------------
    # Contact page (Dawrha design)
    # ------------------------------------------------------------------
    @http.route(['/contact'], type='http', auth='public', website=True,
                sitemap=True)
    def contact(self, **kwargs):
        values = self._base_values('contact')
        values['company'] = request.env.company.sudo()
        return request.render('recycle_warehouse.contact_page', values)

    # ------------------------------------------------------------------
    # My applications (login required)
    # ------------------------------------------------------------------
    @http.route(['/my/applications'], type='http', auth='user', website=True,
                sitemap=False)
    def my_applications(self, **kwargs):
        email = self._user_email()
        applications = request.env['hr.applicant'].sudo().search(
            [('recycle_email', '=', email)], order='id desc')
        values = self._base_values('account')
        values.update({
            'applications': applications,
            'state_labels': APPLICATION_STATE_LABELS,
            'stage_status_labels': {
                'pending': 'Pending',
                'approved': 'Approved',
                'rejected': 'Rejected',
            },
            'just_applied': kwargs.get('applied') == '1',
        })
        return request.render('recycle_warehouse.my_applications_page', values)

    # ------------------------------------------------------------------
    # Registration (with email OTP verification)
    # ------------------------------------------------------------------

    def _otp_session_key(self):
        return 'dw_pending_signup'

    def _send_otp_email(self, email, name, otp):
        """Send 6-digit OTP to the provided email address.

        Uses the same branded card design as the interview-invitation email so
        all Dawrha emails share one consistent look."""
        # `name` is whatever the visitor typed on the public signup form,
        # before any account exists — escape it before splicing into HTML.
        greeting = _esc(name or 'there')
        body = f"""
        <div style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:auto;
                    background:#ffffff;border-radius:16px;overflow:hidden;
                    border:1px solid #e2e8f0;">
            <div style="background:linear-gradient(135deg,#047857,#10b981);
                        padding:24px 28px;color:#fff;">
                <div style="font-size:24px;font-weight:900;">Dawrha</div>
                <div style="opacity:.9;font-size:14px;margin-top:2px;">Verify Your Account</div>
            </div>
            <div style="padding:28px;">
                <p style="font-size:16px;color:#0f172a;margin:0 0 14px;">
                    Dear {greeting},
                </p>
                <p style="font-size:15px;color:#334155;line-height:1.6;margin:0 0 20px;">
                    You requested a verification code for your Dawrha account.
                    Please use the code below to continue.
                </p>
                <div style="text-align:center;margin:24px 0;">
                    <div style="display:inline-block;background:#f1f5f9;
                                border:2px dashed #10b981;border-radius:12px;
                                padding:16px 30px;color:#047857;font-size:32px;
                                font-weight:800;letter-spacing:8px;font-family:monospace;">{otp}</div>
                </div>
                <p style="font-size:13px;color:#94a3b8;line-height:1.6;margin-top:20px;">
                    This code expires in 10 minutes. If you did not request it, please
                    ignore this email.
                </p>
                <p style="font-size:13px;color:#94a3b8;margin-top:18px;">— The Dawrha Team</p>
            </div>
        </div>
        """
        import logging
        _log = logging.getLogger(__name__)
        ICP = request.env['ir.config_parameter'].sudo()

        # If no outgoing mail server is configured, sending will fail. Detect it
        # up-front so we can give an accurate result instead of a false success.
        has_mail_server = bool(
            request.env['ir.mail_server'].sudo().search_count([]))

        try:
            from_email = (
                request.env['res.company'].sudo().browse(1).email
                or ICP.get_param('recycle.otp.from_email', 'noreply@dawrha.com')
            )
            mail = request.env['mail.mail'].sudo().create({
                'subject': f'Dawrha — Your verification code is {otp}',
                'email_to': email,
                'email_from': from_email,
                'body_html': body,
                'auto_delete': True,
            })
            # raise_exception=True is essential: without it, mail.send() swallows
            # the "no SMTP server" error and returns silently, so the signup flow
            # would wrongly believe the code was delivered.
            mail.send(raise_exception=True)
            _log.info('OTP email sent to %s', email)
            return True
        except Exception as e:
            _log.error('OTP email could not be sent to %s: %s', email, e)
            # Dev fallback: when no mail server is set up yet (or the param
            # 'recycle.otp.dev_mode' = '1'), log the code so the signup flow can
            # still be tested. Read it from the server log:  docker logs odoo19
            dev_mode = ICP.get_param('recycle.otp.dev_mode', '0') == '1'
            if dev_mode or not has_mail_server:
                _log.warning(
                    '[DEV OTP] No email delivered — verification code for %s is: %s '
                    '(configure an Outgoing Mail Server to send real emails; '
                    'set ir.config_parameter recycle.otp.dev_mode=0 to disable this).',
                    email, otp)
                return True
            return False

    # ------------------------------------------------------------------
    # OTP helpers — stored in ir.config_parameter (100% reliable, no session)
    # ------------------------------------------------------------------

    def _otp_model(self):
        return request.env['recycle.signup.otp'].sudo()

    def _generate_unique_otp(self):
        """Return a 6-digit code that is not currently used by any other
        pending signup, so every active verification code is unique."""
        Otp = self._otp_model()
        for _attempt in range(100):
            code = str(random.randint(100000, 999999))
            if not Otp.search_count([('otp', '=', code)]):
                return code
        # Extremely unlikely fallback (would need ~900k active signups).
        return str(random.randint(100000, 999999))

    def _otp_store(self, email, name, otp, password):
        """Persist OTP + signup data in a dedicated model (one row per email)."""
        email = (email or '').strip().lower()
        Otp = self._otp_model()
        # Remove any previous pending signup for this email, then store fresh.
        Otp.search([('email', '=', email)]).unlink()
        Otp.create({
            'email': email,
            'name': name,
            'password': password,
            'otp': otp,
            'expires': int(time.time()) + 600,   # 10 minutes
            'attempts': 0,
        })

    def _otp_load(self, email):
        """Read the pending signup data for this email, or None.
        Expired records are deleted on access so an expired code can never
        be used again."""
        email = (email or '').strip().lower()
        rec = self._otp_model().search([('email', '=', email)], limit=1)
        if not rec:
            return None
        if (rec.expires or 0) < int(time.time()):
            rec.unlink()
            return None
        return {
            'name': rec.name or '',
            'email': rec.email,
            'password': rec.password or '',
            'otp': rec.otp or '',
            'expires': rec.expires or 0,
            'attempts': rec.attempts or 0,
        }

    def _otp_save(self, email, data):
        """Update the pending signup data (e.g. increment attempts)."""
        email = (email or '').strip().lower()
        rec = self._otp_model().search([('email', '=', email)], limit=1)
        if rec:
            rec.write({
                'name': data.get('name'),
                'password': data.get('password'),
                'otp': data.get('otp'),
                'expires': data.get('expires'),
                'attempts': data.get('attempts', 0),
            })

    def _otp_clear(self, email):
        """Remove the pending signup record after success / expiry."""
        email = (email or '').strip().lower()
        self._otp_model().search([('email', '=', email)]).unlink()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    @http.route(['/register'], type='http', auth='public', website=True,
                methods=['GET', 'POST'], sitemap=True)
    def register(self, **post):
        if not request.env.user._is_public():
            return request.redirect('/')

        errors = []
        form_data = {
            'name':  post.get('name', ''),
            'email': post.get('email', ''),
        }

        if request.httprequest.method == 'POST':
            name     = (post.get('name') or '').strip()
            email    = (post.get('email') or '').strip().lower()
            password = (post.get('password') or '')
            confirm  = (post.get('confirm_password') or '')

            if not name or len(name) < 2:
                errors.append(_('Please enter your full name (at least 2 characters).'))
            if not email or '@' not in email or '.' not in email.split('@')[-1]:
                errors.append(_('Please enter a valid email address.'))
            if len(password) < 6:
                errors.append(_('Password must be at least 6 characters.'))
            if password != confirm:
                errors.append(_('Passwords do not match.'))

            if not errors:
                existing = request.env['res.users'].sudo().with_context(
                    active_test=False).search([('login', '=', email)], limit=1)
                if existing and existing.recycle_deleted:
                    # Archived employee — cannot recreate the account. Raise a
                    # reactivation request instead.
                    is_ar_reg = str(request.lang or 'en')[:2] == 'ar'
                    if is_ar_reg:
                        reg_msg = ('تم تسجيل طلبك. يرجى الانتظار حتى يتم '
                                   'التواصل معك من قبل قسم الموارد البشرية.')
                    else:
                        reg_msg = ('Your request has been registered. Please wait until '
                                   'you are contacted by the HR department.')
                    try:
                        existing._recycle_request_reactivation(employee_msg=reg_msg)
                    except Exception:
                        import logging as _log
                        _log.getLogger(__name__).warning(
                            'Failed to create reactivation request for user %s', existing.id, exc_info=True)
                    errors.append(reg_msg)
                elif existing and existing.active:
                    errors.append(_(
                        'An account with this email already exists. '
                        'Please sign in instead.'))

            if not errors:
                otp = self._generate_unique_otp()

                # Save OTP + signup data directly in the database
                self._otp_store(email, name, otp, password)

                sent = self._send_otp_email(email, name, otp)
                if not sent:
                    errors.append(_(
                        'Could not send the verification email. '
                        'Please check the address and try again.'))
                else:
                    # Pass email via URL — no session needed
                    import werkzeug.urls as wu
                    safe_email = wu.url_quote(email, safe='')
                    return request.redirect(f'/verify-email?e={safe_email}')

        values = self._base_values('register')
        values.update({'errors': errors, 'form_data': form_data})
        return request.render('recycle_warehouse.register_page', values)

    # ------------------------------------------------------------------
    # OTP Verification
    # ------------------------------------------------------------------

    @http.route(['/verify-email'], type='http', auth='public', website=True,
                methods=['GET', 'POST'], csrf=False, sitemap=False)
    def verify_email(self, **post):
        if not request.env.user._is_public():
            return request.redirect('/')

        import werkzeug.urls as wu

        # Email comes from URL param (GET) or hidden form field (POST)
        email = (
            post.get('_email') or
            request.httprequest.args.get('e') or
            ''
        ).strip().lower()

        if not email:
            return request.redirect('/register')

        # Load OTP data from database
        pending = self._otp_load(email)
        if not pending:
            return request.redirect('/register?expired=1')

        name  = pending.get('name', '')
        error = None

        if request.httprequest.method == 'POST':
            # Collect the 6 digits sent as d1..d6
            digits      = [post.get(f'd{i}', '').strip() for i in range(1, 7)]
            entered_otp = ''.join(digits)

            # ── Expiry ──
            if int(time.time()) > pending.get('expires', 0):
                self._otp_clear(email)
                return request.redirect('/register?expired=1')

            # ── Max attempts ──
            attempts = pending.get('attempts', 0) + 1
            pending['attempts'] = attempts
            self._otp_save(email, pending)

            if attempts > 5:
                self._otp_clear(email)
                return request.redirect('/register?locked=1')

            # ── Compare ──
            stored_otp = str(pending.get('otp', '')).strip()
            if entered_otp == stored_otp:
                # ✅ OTP correct → create account → delete OTP → login
                import logging as _log
                _logger = _log.getLogger(__name__)
                try:
                    env = request.env['res.users'].sudo()

                    # Check for existing user (including archived)
                    existing = env.with_context(active_test=False).search([
                        ('login', '=', email),
                    ], limit=1)

                    if existing and existing.active:
                        self._otp_clear(email)
                        return request.redirect('/web/login?already=1')

                    if existing and not existing.active:
                        # Archived user → reactivate and update.
                        # Keep existing groups (don't re-add portal — it may
                        # conflict with internal-user groups the user already had).
                        existing.write({
                            'name': pending['name'],
                            'email': email,
                            'active': True,
                        })
                        existing.write({'password': pending['password']})
                        new_user = existing
                    else:
                        # Build vals — set the password directly in create() vals,
                        # which is the reliable way in Odoo 19 (same approach the
                        # standard signup uses). Avoid the non-public _set_password.
                        vals = {
                            'name':     pending['name'],
                            'login':    email,
                            'email':    email,
                            'password': pending['password'],
                        }

                        portal_group = request.env.ref(
                            'base.group_portal', raise_if_not_found=False)
                        if portal_group:
                            groups_field = (
                                'group_ids'
                                if 'group_ids' in env._fields
                                else 'groups_id'
                            )
                            vals[groups_field] = [(6, 0, [portal_group.id])]

                        new_user = env.with_context(
                            no_reset_password=True,
                            mail_notrack=True,
                        ).create(vals)

                    # Delete OTP from database immediately
                    self._otp_clear(email)

                    # Registration succeeded → sign the user in and land on
                    # the Home page (spec: register success goes to Home).
                    if self._recycle_authenticate(email, pending['password']):
                        return request.redirect('/')
                    # Authentication fallback (should not happen) — let the
                    # user sign in manually.
                    return request.redirect('/web/login?created=1')

                except Exception as ex:
                    _logger.error('User creation error: %s', ex, exc_info=True)
                    error = _('Account creation failed: %s') % ex
                    # Roll back attempt counter so user can try again
                    pending['attempts'] = max(0, attempts - 1)
                    self._otp_save(email, pending)
            else:
                remaining = max(0, 5 - attempts)
                if remaining > 0:
                    error = _('Incorrect code — %d attempt(s) left.') % remaining
                else:
                    error = _('Too many wrong attempts.')

        safe_email = wu.url_quote(email, safe='')
        values = self._base_values('register')
        values.update({
            'email':      email,
            'safe_email': safe_email,
            'name':       name,
            'error':      error,
            'resent':     request.httprequest.args.get('resent') == '1',
        })
        return request.render('recycle_warehouse.verify_email_page', values)

    @http.route(['/verify-email/resend'], type='http', auth='public',
                website=True, methods=['POST'], csrf=False, sitemap=False)
    def resend_otp(self, **post):
        import werkzeug.urls as wu

        email = (post.get('_email') or '').strip().lower()
        if not email:
            return request.redirect('/register')

        pending = self._otp_load(email)
        if not pending:
            return request.redirect('/register')

        new_otp = self._generate_unique_otp()
        pending['otp']      = new_otp
        pending['expires']  = int(time.time()) + 600
        pending['attempts'] = 0
        self._otp_save(email, pending)

        self._send_otp_email(email, pending.get('name', ''), new_otp)
        safe_email = wu.url_quote(email, safe='')
        return request.redirect(f'/verify-email?e={safe_email}&resent=1')
