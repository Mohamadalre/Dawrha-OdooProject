# -*- coding: utf-8 -*-
import logging
from html import escape as _esc
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class RecycleNotification(models.Model):
    _name = 'recycle.notification'
    _description = 'Dashboard Notification'
    _order = 'create_date desc, id desc'

    title = fields.Char(required=True)
    message = fields.Text()
    notif_type = fields.Selection([
        ('application', 'Job Application'),
        ('reactivation', 'Reactivation Request'),
        ('shift_change', 'Shift Change'),
        ('decision', 'Application Decision'),
        ('shipment', 'Shipment Stored'),
        ('order', 'Order Completed'),
        ('role_assignment', 'Role Assignment Request'),
        ('stock_empty', 'Stock Depleted'),
        ('delivery_trip', 'Delivery Trip'),
        ('order_complaint', 'Order Complaint'),
        ('info', 'Info'),
    ], default='info', string='Type')
    # Who sees it. Empty + for_admin=True => visible to all administrators.
    recipient_user_id = fields.Many2one(
        'res.users', string='Recipient', index=True, ondelete='cascade')
    for_admin = fields.Boolean(string='For Administrators', default=False)
    is_read = fields.Boolean(string='Read', default=False)
    # Actionable notifications (e.g. reactivation requests) carry a state.
    state = fields.Selection([
        ('pending', 'Pending'),
        ('done', 'Handled'),
    ], default='done', string='Status')
    request_user_id = fields.Many2one(
        'res.users', string='Requesting User', ondelete='cascade',
        help='For reactivation requests: the archived user asking to return.')
    related_model = fields.Char()
    related_res_id = fields.Integer()

    # ------------------------------------------------------------------
    # Creation helpers
    # ------------------------------------------------------------------
    @api.model
    def _notify_admins(self, title, message, notif_type='info',
                       request_user=None, state='done',
                       related_model=None, related_res_id=None):
        return self.sudo().create({
            'title': title,
            'message': message,
            'notif_type': notif_type,
            'for_admin': True,
            'state': state,
            'request_user_id': request_user.id if request_user else False,
            'related_model': related_model,
            'related_res_id': related_res_id,
        })

    @api.model
    def _notify_user(self, user, title, message, notif_type='info'):
        if not user:
            return self.browse()
        return self.sudo().create({
            'title': title,
            'message': message,
            'notif_type': notif_type,
            'recipient_user_id': user.id,
        })

    @api.model
    def _notify_users(self, users, title, message, notif_type='info'):
        recs = self.browse()
        for u in users:
            recs |= self._notify_user(u, title, message, notif_type)
        return recs

    # ------------------------------------------------------------------
    # Email helper — sends a real email to a user
    # ------------------------------------------------------------------
    @api.model
    def _send_email_to_user(self, user, subject, body_html):
        """Send an actual email to the given user's email address.
        Returns True on success, False on failure."""
        if not user or not user.email:
            return False
        company = self.env['res.company'].sudo().browse(1)
        ICP = self.env['ir.config_parameter'].sudo()
        from_email = ICP.get_param(
            'recycle.otp.from_email', company.email or 'noreply@dawrha.com')
        try:
            mail = self.env['mail.mail'].sudo().create({
                'subject': subject,
                'body_html': body_html,
                'email_to': user.email,
                'email_from': from_email,
                'auto_delete': True,
            })
            mail.send()
            _logger.info('Email sent to %s: %s', user.email, subject)
            return True
        except Exception as e:
            _logger.error('Email to %s failed: %s', user.email, e)
            return False

    # ------------------------------------------------------------------
    # Reactivation request handling (admin decides)
    # ------------------------------------------------------------------
    def action_reactivation_approve(self):
        self.ensure_one()
        if not self.env.user.has_group('recycle_warehouse.group_recycle_admin'):
            from odoo.exceptions import UserError
            raise UserError(_('Only administrators can handle requests.'))
        user = self.request_user_id
        if user:
            user.sudo().action_recycle_restore()
            # Use the user's partner language, not the admin's context
            partner_lang = getattr(user.sudo().partner_id, 'lang', '') or ''
            is_ar = str(partner_lang)[:2] == 'ar'
            if is_ar:
                title = 'تمت استعادة الحساب'
                msg = 'تم استعادة حسابك بنجاح. يمكنك الآن تسجيل الدخول مرة أخرى.'
                email_subject = 'Dawrha — تمت استعادة حسابك'
                email_body = """
                <div style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:auto;
                            background:#ffffff;border-radius:16px;overflow:hidden;
                            border:1px solid #e2e8f0;">
                    <div style="background:linear-gradient(135deg,#047857,#10b981);
                                padding:24px 28px;color:#fff;">
                        <div style="font-size:24px;font-weight:900;">Dawrha</div>
                        <div style="opacity:.9;font-size:14px;margin-top:2px;">تمت استعادة الحساب</div>
                    </div>
                    <div style="padding:28px;">
                        <p style="font-size:16px;color:#0f172a;margin:0 0 14px;">%s،</p>
                        <p style="font-size:15px;color:#334155;line-height:1.8;margin:0 0 20px;">
                            تم استعادة حسابك بنجاح. يمكنك الآن تسجيل الدخول مرة أخرى والعودة إلى العمل.
                        </p>
                        <div style="text-align:center;margin:24px 0;">
                            <a href="/web/login" style="display:inline-block;background:linear-gradient(135deg,#047857,#10b981);
                                color:#fff;text-decoration:none;padding:12px 32px;border-radius:8px;
                                font-weight:600;font-size:15px;">تسجيل الدخول</a>
                        </div>
                        <p style="font-size:13px;color:#94a3b8;margin-top:18px;">— فريق Dawrha</p>
                    </div>
                </div>
                """ % _esc(user.name or 'المستخدم')
            else:
                title = 'Account Reactivated'
                msg = ('Your account has been successfully restored. '
                       'You can now log in again.')
                email_subject = 'Dawrha — Your Account Has Been Restored'
                email_body = """
                <div style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:auto;
                            background:#ffffff;border-radius:16px;overflow:hidden;
                            border:1px solid #e2e8f0;">
                    <div style="background:linear-gradient(135deg,#047857,#10b981);
                                padding:24px 28px;color:#fff;">
                        <div style="font-size:24px;font-weight:900;">Dawrha</div>
                        <div style="opacity:.9;font-size:14px;margin-top:2px;">Account Reactivated</div>
                    </div>
                    <div style="padding:28px;">
                        <p style="font-size:16px;color:#0f172a;margin:0 0 14px;">Dear %s,</p>
                        <p style="font-size:15px;color:#334155;line-height:1.8;margin:0 0 20px;">
                            Your account has been successfully restored. You can now log in again and resume your work.
                        </p>
                        <div style="text-align:center;margin:24px 0;">
                            <a href="/web/login" style="display:inline-block;background:linear-gradient(135deg,#047857,#10b981);
                                color:#fff;text-decoration:none;padding:12px 32px;border-radius:8px;
                                font-weight:600;font-size:15px;">Log In</a>
                        </div>
                        <p style="font-size:13px;color:#94a3b8;margin-top:18px;">— The Dawrha Team</p>
                    </div>
                </div>
                """ % _esc(user.name or 'User')
            self._notify_user(user, title, msg, 'decision')
            self._send_email_to_user(user, email_subject, email_body)
        self.write({'state': 'done', 'is_read': True})
        return True

    def action_reactivation_reject(self):
        self.ensure_one()
        if not self.env.user.has_group('recycle_warehouse.group_recycle_admin'):
            from odoo.exceptions import UserError
            raise UserError(_('Only administrators can handle requests.'))
        if self.request_user_id:
            user = self.request_user_id
            # Use the user's partner language, not the admin's context
            partner_lang = getattr(user.sudo().partner_id, 'lang', '') or ''
            is_ar = str(partner_lang)[:2] == 'ar'
            if is_ar:
                title = 'تم رفض طلب استعادة الحساب'
                msg = ('لم يتم استعادة حسابك بسبب السياسات الأمنية للمؤسسة. '
                       'يرجى التواصل مع قسم الموارد البشرية للمزيد من المعلومات.')
                email_subject = 'Dawrha — رفض طلب استعادة الحساب'
                email_body = """
                <div style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:auto;
                            background:#ffffff;border-radius:16px;overflow:hidden;
                            border:1px solid #e2e8f0;">
                    <div style="background:linear-gradient(135deg,#047857,#10b981);
                                padding:24px 28px;color:#fff;">
                        <div style="font-size:24px;font-weight:900;">Dawrha</div>
                        <div style="opacity:.9;font-size:14px;margin-top:2px;">رفض طلب استعادة الحساب</div>
                    </div>
                    <div style="padding:28px;">
                        <p style="font-size:16px;color:#0f172a;margin:0 0 14px;">%s،</p>
                        <p style="font-size:15px;color:#334155;line-height:1.8;margin:0 0 20px;">
                            لم يتم استعادة حسابك بسبب السياسات الأمنية للمؤسسة.
                            يرجى التواصل مع قسم الموارد البشرية للمزيد من المعلومات.
                        </p>
                        <p style="font-size:13px;color:#94a3b8;margin-top:18px;">— فريق Dawrha</p>
                    </div>
                </div>
                """ % _esc(user.name or 'المستخدم')
            else:
                title = 'Reactivation Request Declined'
                msg = ('Your account restoration request has been declined '
                       'due to the organization\'s security policies. '
                       'Please contact the HR department for more information.')
                email_subject = 'Dawrha — Reactivation Request Declined'
                email_body = """
                <div style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:auto;
                            background:#ffffff;border-radius:16px;overflow:hidden;
                            border:1px solid #e2e8f0;">
                    <div style="background:linear-gradient(135deg,#047857,#10b981);
                                padding:24px 28px;color:#fff;">
                        <div style="font-size:24px;font-weight:900;">Dawrha</div>
                        <div style="opacity:.9;font-size:14px;margin-top:2px;">Reactivation Request Declined</div>
                    </div>
                    <div style="padding:28px;">
                        <p style="font-size:16px;color:#0f172a;margin:0 0 14px;">Dear %s,</p>
                        <p style="font-size:15px;color:#334155;line-height:1.8;margin:0 0 20px;">
                            Your account restoration request has been declined due to the
                            organization's security policies. Please contact the HR department
                            for more information.
                        </p>
                        <p style="font-size:13px;color:#94a3b8;margin-top:18px;">— The Dawrha Team</p>
                    </div>
                </div>
                """ % _esc(user.name or 'User')
            self._notify_user(user, title, msg, 'decision')
            self._send_email_to_user(user, email_subject, email_body)
        self.write({'state': 'done', 'is_read': True})
        return True
