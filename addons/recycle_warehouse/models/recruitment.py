# -*- coding: utf-8 -*-
import logging
import time
from html import escape as _esc

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import format_datetime

_logger = logging.getLogger(__name__)

APPLICATION_STATES = [
    ('applied', 'Applied'),
    ('interview', 'Interview'),
    ('accepted', 'Accepted'),
    ('rejected', 'Rejected'),
]

EMPLOYEE_ROLES = [
    ('input', 'Input Employee'),
    ('sorting', 'Sorting Employee'),
    ('output', 'Output Employee'),
]

ROLE_GROUP_MAP = {
    'manager':     'recycle_warehouse.group_recycle_manager',
    'input':       'recycle_warehouse.group_recycle_input',
    'sorting':     'recycle_warehouse.group_recycle_sorting',
    'output':      'recycle_warehouse.group_recycle_output',
}


class RecycleSignupOtp(models.Model):
    """Pending website signup awaiting email verification.
    One row per email; replaces the previous ir.config_parameter storage
    (which collided with the unique 'key' constraint)."""
    _name = 'recycle.signup.otp'
    _description = 'Pending Website Signup (email OTP)'
    _rec_name = 'email'

    email = fields.Char(required=True, index=True)
    name = fields.Char()
    password = fields.Char()
    otp = fields.Char()
    expires = fields.Integer(help='Unix timestamp when the code expires.')
    attempts = fields.Integer(default=0)

    @api.autovacuum
    def _gc_expired_otps(self):
        """Periodically delete expired pending signups (Odoo autovacuum)."""
        self.search([('expires', '<', int(time.time()))]).unlink()


class HrJob(models.Model):
    _inherit = 'hr.job'

    recycle_publish = fields.Boolean(string='Publish on Recycle Website')
    recycle_job_type = fields.Selection([
        ('manager', 'Warehouse Manager'),
        ('employee', 'General Employee'),
        ('input', 'Input Employee'),
        ('sorting', 'Sorting Employee'),
        ('output', 'Output Employee'),
    ], string='Recycle Job Type', default='employee',
       help='"General Employee" lets the admin/manager assign any of the three '
            'employee roles later. Choosing a specific role (Input/Sorting/'
            'Output) locks every hire from this job to that role.')
    recycle_description = fields.Html(string='Recycle Website Description')

    def _recycle_is_specialized(self):
        self.ensure_one()
        return self.recycle_job_type in ('input', 'sorting', 'output')

    def _recycle_update_publish(self):
        """Auto-close the job when accepted applicants meet the target;
        auto-reopen when target increases and spots are available."""
        accepted = self.env['hr.applicant'].search_count([
            ('job_id', '=', self.id),
            ('recycle_state', '=', 'accepted')
        ])
        target = self.no_of_recruitment or 1
        if accepted >= target and self.recycle_publish:
            self.with_context(recycle_skip_job_check=True).write({'recycle_publish': False})
        elif accepted < target and not self.recycle_publish:
            self.with_context(recycle_skip_job_check=True).write({'recycle_publish': True})

    def write(self, vals):
        res = super().write(vals)
        if 'no_of_recruitment' in vals and not self.env.context.get('recycle_skip_job_check'):
            for job in self:
                job._recycle_update_publish()
        return res


class HrRecruitmentStage(models.Model):
    _inherit = 'hr.recruitment.stage'

    recycle_is_interview = fields.Boolean(
        string='Interview Stage',
        help='When set, reaching this stage enables interview scheduling, and '
             'the application cannot advance until an interview is scheduled.')
    recycle_description = fields.Text(
        string='Stage Description',
        help='Optional description shown for normal (non-interview) stages.')


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    recycle_name = fields.Char(string='Applicant Name (Recycle)')
    recycle_email = fields.Char(string='Applicant Email (Recycle)', index=True)
    recycle_phone = fields.Char(string='Phone Number (Recycle)')
    recycle_national_id = fields.Char(string='National ID', index=True)
    recycle_cover_letter = fields.Text(string='Applicant Description')
    recycle_profile_url = fields.Char(string='Profile Link (LinkedIn/GitHub)')
    recycle_state = fields.Selection(
        APPLICATION_STATES, string='Recycle Application Status',
        default='applied', tracking=True)
    recycle_interview_datetime = fields.Datetime(string='Interview Date & Time')
    recycle_interview_location = fields.Char(string='Interview Location / Link')
    recycle_interview_notes = fields.Text(string='Interview Message')
    recycle_interview_sent_at = fields.Datetime(
        string='Interview Invite Sent At', readonly=True, copy=False,
        help='When the interview date/details were actually emailed to the '
             'applicant — kept even after the application moves past the '
             'interview stage, as a record of when it was sent.')
    recycle_stage_log_ids = fields.One2many(
        'recycle.applicant.stage.log', 'applicant_id', string='Stage History')
    # Per-stage decision status for the recruitment pipeline.
    recycle_stage_status = fields.Selection([
        ('pending',  'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Stage Status', default='pending', tracking=True, copy=False)
    recycle_is_interview_stage = fields.Boolean(
        compute='_compute_recycle_stage_flags')
    recycle_is_last_stage = fields.Boolean(
        compute='_compute_recycle_stage_flags')

    recycle_reject_reason = fields.Text(string='Rejection Reason', copy=False)

    @api.depends('stage_id', 'stage_id.recycle_is_interview')
    def _compute_recycle_stage_flags(self):
        stages = self.env['hr.recruitment.stage'].search([], order='sequence, id')
        last_id = stages[-1].id if stages else False
        for rec in self:
            name = (rec.stage_id.name or '').lower()
            # Prefer the explicit per-stage flag; fall back to name matching.
            rec.recycle_is_interview_stage = bool(
                rec.stage_id and (
                    rec.stage_id.recycle_is_interview
                    or 'interview' in name or 'مقابلة' in name))
            rec.recycle_is_last_stage = bool(
                rec.stage_id and rec.stage_id.id == last_id)
    recycle_role = fields.Selection(
        [('manager', 'Warehouse Manager')] + EMPLOYEE_ROLES,
        string='Assigned Role',
        compute='_compute_recycle_role', store=True, readonly=False)
    recycle_warehouse_id = fields.Many2one(
        'recycle.warehouse', string='Assigned Warehouse',
        compute='_compute_recycle_warehouse', store=True, readonly=False)

    @api.depends('recycle_job_type', 'employee_user_id', 'employee_user_id.recycle_role')
    def _compute_recycle_role(self):
        for rec in self:
            if rec.recycle_job_type == 'manager':
                # Manager positions: role is always Warehouse Manager, fixed.
                rec.recycle_role = 'manager'
            elif rec.recycle_job_type in ('input', 'sorting', 'output'):
                # Specialized positions: the role is the job type itself,
                # locked — nobody picks it, it's implied by the job posting.
                rec.recycle_role = rec.recycle_job_type
            elif rec.recycle_role == 'manager':
                # General employee positions can never hold the manager role.
                rec.recycle_role = False
            elif rec.employee_user_id and rec.employee_user_id.recycle_role:
                rec.recycle_role = rec.employee_user_id.recycle_role

    @api.depends('employee_user_id', 'employee_user_id.recycle_warehouse_id')
    def _compute_recycle_warehouse(self):
        for rec in self:
            if rec.employee_user_id and rec.employee_user_id.recycle_warehouse_id:
                rec.recycle_warehouse_id = rec.employee_user_id.recycle_warehouse_id
    recycle_job_type = fields.Selection(
        related='job_id.recycle_job_type', store=True, readonly=True)

    def _recycle_is_specialized(self):
        self.ensure_one()
        return self.recycle_job_type in ('input', 'sorting', 'output')
    employee_user_id = fields.Many2one(
        'res.users', string='Created User', readonly=True, copy=False)
    recycle_account_deleted = fields.Boolean(
        string='Account Deleted', default=False, readonly=True, copy=False)
    # Talent pool: retained candidates kept for future positions.
    recycle_in_pool = fields.Boolean(
        string='In Talent Pool', default=False, copy=False)
    recycle_pool_date = fields.Datetime(
        string='Added to Pool', readonly=True, copy=False)

    def action_recycle_add_to_pool(self):
        """Keep this candidate in the talent pool for future positions."""
        self.ensure_one()
        self._recycle_check_admin()
        self.sudo().write({
            'recycle_in_pool': True,
            'recycle_pool_date': fields.Datetime.now(),
        })
        try:
            self.message_post(body=_('Added to the talent pool by %s.')
                              % self.env.user.name)
        except Exception:
            pass
        return True

    def action_recycle_remove_from_pool(self):
        self.ensure_one()
        self._recycle_check_admin()
        self.sudo().write({'recycle_in_pool': False, 'recycle_pool_date': False})
        return True

    # ---------------- Create: notify admins of new applications ----------------

    @api.model_create_multi
    def create(self, vals_list):
        apps = super().create(vals_list)
        for app in apps:
            # Only genuine website applications (they carry a recycle_email).
            if app.recycle_email and not app.recycle_account_deleted:
                try:
                    self.env['recycle.notification']._notify_admins(
                        _('New job application'),
                        _('%s applied for "%s".') % (
                            app.recycle_name or app.recycle_email,
                            app.job_id.name or '—'),
                        notif_type='application',
                        related_model='hr.applicant', related_res_id=app.id)
                except Exception as e:
                    _logger.error('Application notification failed: %s', e)
        return apps

    # ---------------- Constraints ----------------

    def unlink(self):
        if (not self.env.context.get('recycle_force_delete')
                and self.filtered('recycle_account_deleted')):
            raise UserError(_('Cannot delete an application linked to a deleted account.'))
        return super().unlink()

    @api.constrains('recycle_national_id')
    def _check_national_id_format(self):
        for rec in self:
            if rec.recycle_national_id:
                nid = rec.recycle_national_id.strip()
                if not nid.isdigit() or not (5 <= len(nid) <= 20):
                    raise ValidationError(
                        _('National ID must contain only digits (5 to 20 characters).'))

    @api.constrains('recycle_national_id', 'recycle_email', 'job_id')
    def _check_duplicate_application(self):
        for rec in self:
            if not rec.job_id:
                continue
            # Applications belonging to a deleted account are historical
            # records; they must never block a fresh re-application.
            if rec.recycle_national_id:
                dup = self.sudo().search_count([
                    ('id', '!=', rec.id),
                    ('job_id', '=', rec.job_id.id),
                    ('recycle_account_deleted', '!=', True),
                    ('recycle_national_id', '=', rec.recycle_national_id)])
                if dup:
                    raise ValidationError(_(
                        'An application with this national ID already exists for this job.'))
            if rec.recycle_email:
                dup = self.sudo().search_count([
                    ('id', '!=', rec.id),
                    ('job_id', '=', rec.job_id.id),
                    ('recycle_account_deleted', '!=', True),
                    ('recycle_email', '=', rec.recycle_email)])
                if dup:
                    raise ValidationError(_(
                        'An application with this email already exists for this job.'))

    # ---------------- Status buttons (Admin) ----------------

    def action_recycle_interview(self):
        """Open the interview-scheduling dialog so the admin can pick the
        date/time and details that get emailed to the applicant."""
        self.ensure_one()
        if not self.env.user.has_group('recycle_warehouse.group_recycle_admin'):
            raise UserError(_('Only administrators can schedule interviews.'))
        if not (self.recycle_email or '').strip():
            raise UserError(_('This applicant has no email address on file.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Schedule Interview'),
            'res_model': 'recycle.interview.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_applicant_id': self.id},
        }

    def _send_interview_email(self, when_dt, location, notes):
        """Email the applicant the interview details."""
        self.ensure_one()
        email = (self.recycle_email or '').strip()
        if not email:
            return False
        company = self.env.company
        tz = self.env.user.tz or 'UTC'
        when_txt = format_datetime(
            self.env, when_dt, tz=tz, dt_format="EEEE, d MMMM y 'at' HH:mm")
        # Every value below can originate from user input (applicant name,
        # interview location/notes typed by the admin, job title) and is
        # spliced into raw HTML — escape each one individually so none of
        # them can break out of their attribute/text context and inject
        # markup into an email the applicant's own mail client will render.
        job_name_raw = self.job_id.name or 'Dawrha'
        job_name = _esc(job_name_raw)
        applicant_name = _esc(self.recycle_name or 'Applicant')
        location_html = ''
        if location:
            location_html = (
                f'<tr><td style="padding:6px 0;color:#64748b;">Location / Link</td>'
                f'<td style="padding:6px 0;font-weight:700;color:#0f172a;">{_esc(location)}</td></tr>'
            )
        notes_html = ''
        if notes:
            safe_notes = _esc(notes).replace('\n', '<br/>')
            notes_html = (
                f'<div style="margin-top:18px;padding:14px 16px;background:#f1f5f9;'
                f'border-radius:12px;color:#334155;font-size:14px;">{safe_notes}</div>'
            )
        body = f"""
        <div style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:auto;
                    background:#ffffff;border-radius:16px;overflow:hidden;
                    border:1px solid #e2e8f0;">
            <div style="background:linear-gradient(135deg,#047857,#10b981);
                        padding:24px 28px;color:#fff;">
                <div style="font-size:24px;font-weight:900;">Dawrha</div>
                <div style="opacity:.9;font-size:14px;margin-top:2px;">Interview Invitation</div>
            </div>
            <div style="padding:28px;">
                <p style="font-size:16px;color:#0f172a;margin:0 0 14px;">
                    Dear {applicant_name},
                </p>
                <p style="font-size:15px;color:#334155;line-height:1.6;margin:0 0 20px;">
                    We are pleased to invite you to an interview for the position of
                    <strong>{job_name}</strong>. Please find the details below.
                </p>
                <table style="width:100%;border-collapse:collapse;font-size:14px;">
                    <tr><td style="padding:6px 0;color:#64748b;width:140px;">Position</td>
                        <td style="padding:6px 0;font-weight:700;color:#0f172a;">{job_name}</td></tr>
                    <tr><td style="padding:6px 0;color:#64748b;">Date &amp; Time</td>
                        <td style="padding:6px 0;font-weight:700;color:#0f172a;">{when_txt}</td></tr>
                    {location_html}
                </table>
                {notes_html}
                <p style="font-size:13px;color:#94a3b8;margin-top:24px;">
                    If you have any questions, simply reply to this email.
                </p>
            </div>
        </div>
        """
        from_email = self.env['ir.config_parameter'].sudo().get_param(
            'recycle.otp.from_email', company.email or 'noreply@dawrha.com')
        try:
            mail = self.env['mail.mail'].sudo().create({
                'subject': f'Interview Invitation — {job_name_raw}',
                'body_html': body,
                'email_to': email,
                'email_from': from_email,
                'auto_delete': True,
            })
            mail.send()
            self.sudo().write({'recycle_interview_sent_at': fields.Datetime.now()})
            return True
        except Exception as e:
            _logger.error('Interview email failed: %s', e)
            return False

    # ---------------- Stage pipeline (status per stage) ----------------

    def _recycle_all_stages(self):
        return self.env['hr.recruitment.stage'].search([], order='sequence, id')

    def _recycle_next_stage(self):
        """Return the immediate next stage (by sequence) or an empty recordset."""
        self.ensure_one()
        stages = self._recycle_all_stages()
        ids = stages.ids
        if self.stage_id and self.stage_id.id in ids:
            idx = ids.index(self.stage_id.id)
            if idx + 1 < len(ids):
                return stages[idx + 1]
        return self.env['hr.recruitment.stage']

    def _recycle_sync_state(self):
        """Keep the legacy recycle_state in sync with the stage + status, so
        account-creation gating and security rules keep working."""
        for rec in self:
            status = rec.recycle_stage_status
            if status == 'rejected':
                target = 'rejected'
            elif rec.recycle_is_last_stage and status == 'approved':
                target = 'accepted'
            elif rec.recycle_is_interview_stage:
                target = 'interview'
            else:
                target = 'applied'
            if rec.recycle_state != target:
                rec.with_context(recycle_syncing=True).write(
                    {'recycle_state': target})
                # Email the applicant the final decision (accepted / rejected).
                if target in ('accepted', 'rejected'):
                    try:
                        rec._recycle_send_decision_email(target)
                    except Exception as e:
                        _logger.error('Decision email failed: %s', e)

    def _recycle_send_decision_email(self, decision):
        """Email the applicant the final hiring decision, using the shared
        Dawrha branded design."""
        self.ensure_one()
        email = (self.recycle_email or '').strip()
        if not email:
            return False
        # Escape everything user-controlled (applicant name, job title,
        # rejection reason typed by the admin) before splicing into HTML —
        # only the plain-text email subject uses the raw, unescaped value.
        job_name_raw = self.job_id.name or 'Dawrha'
        job_name = _esc(job_name_raw)
        applicant_name = _esc(self.recycle_name or 'Applicant')
        if decision == 'accepted':
            headline = _('Congratulations!')
            intro = _('We are pleased to inform you that your application for '
                      '<strong>%s</strong> has been accepted.') % job_name
            reason = ''
        else:
            headline = _('Application Update')
            intro = _('Thank you for your interest in <strong>%s</strong>. '
                      'After careful review, your application was not '
                      'successful this time.') % job_name
            reason = ''
            if self.recycle_reject_reason:
                reason = (
                    '<div style="margin-top:18px;padding:14px 16px;'
                    'background:#f1f5f9;border-radius:12px;color:#334155;'
                    'font-size:14px;">%s</div>' % _esc(self.recycle_reject_reason))
        body = f"""
        <div style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:auto;
                    background:#ffffff;border-radius:16px;overflow:hidden;
                    border:1px solid #e2e8f0;">
            <div style="background:linear-gradient(135deg,#047857,#10b981);
                        padding:24px 28px;color:#fff;">
                <div style="font-size:24px;font-weight:900;">Dawrha</div>
                <div style="opacity:.9;font-size:14px;margin-top:2px;">{headline}</div>
            </div>
            <div style="padding:28px;">
                <p style="font-size:16px;color:#0f172a;margin:0 0 14px;">
                    Dear {applicant_name},
                </p>
                <p style="font-size:15px;color:#334155;line-height:1.6;margin:0 0 8px;">
                    {intro}
                </p>
                {reason}
                <p style="font-size:13px;color:#94a3b8;margin-top:24px;">— The Dawrha Team</p>
            </div>
        </div>
        """
        from_email = self.env['ir.config_parameter'].sudo().get_param(
            'recycle.otp.from_email', self.env.company.email or 'noreply@dawrha.com')
        subject = (_('Application Accepted — %s') if decision == 'accepted'
                   else _('Application Update — %s')) % job_name_raw
        mail = self.env['mail.mail'].sudo().create({
            'subject': subject,
            'body_html': body,
            'email_to': email,
            'email_from': from_email,
            'auto_delete': True,
        })
        mail.send()
        return True

    def write(self, vals):
        # Block changes to deleted accounts — except when an admin operation
        # explicitly forces it (permanent delete / re-marking during purge),
        # or when only the account-deleted flag itself is being toggled.
        if (self.filtered('recycle_account_deleted')
                and not self.env.context.get('recycle_force_delete')
                and set(vals) - {'recycle_account_deleted'}):
            raise UserError(_('Cannot modify an application linked to a deleted account.'))
        # Enforce the pipeline rules whenever the stage changes.
        if 'stage_id' in vals and not self.env.context.get('recycle_syncing'):
            new_stage = self.env['hr.recruitment.stage'].browse(vals['stage_id'])
            for rec in self:
                old = rec.stage_id
                if not old or not new_stage or new_stage.id == old.id:
                    continue
                # No going back to a previous stage.
                if new_stage.sequence < old.sequence:
                    raise UserError(_(
                        'You cannot move back to a previous stage. '
                        'The pipeline only moves forward.'))
                # The current stage must be approved before advancing.
                if rec.recycle_stage_status != 'approved':
                    raise UserError(_(
                        'Set the current stage status to "Approved" before '
                        'moving to the next stage.'))
                # If the current stage is an interview stage, an interview must
                # be scheduled before the application can move forward.
                if rec.recycle_is_interview_stage and not rec.recycle_interview_datetime:
                    raise UserError(_(
                        'This is an interview stage. Schedule the interview '
                        'before advancing to the next stage.'))
                # Only the immediate next stage is allowed (no skipping).
                nxt = rec._recycle_next_stage()
                if nxt and new_stage.id != nxt.id:
                    raise UserError(_(
                        'You can only advance to the next stage in order — '
                        'skipping stages is not allowed.'))
        res = super().write(vals)
        # Reset the status for the freshly entered stage, then sync state.
        if not self.env.context.get('recycle_syncing'):
            if 'stage_id' in vals and 'recycle_stage_status' not in vals:
                self.with_context(recycle_syncing=True).write(
                    {'recycle_stage_status': 'pending'})
            self.with_context(recycle_syncing=True)._recycle_sync_state()
            # Auto-close/reopen job when applicant state changes
            if 'recycle_state' in vals or 'stage_id' in vals or 'recycle_stage_status' in vals:
                for app in self:
                    if app.job_id:
                        app.job_id._recycle_update_publish()
        return res

    def _recycle_check_pipeline_open(self):
        """Once an applicant is fully accepted (final stage approved), the
        pipeline is frozen: no more approve/reject/advance — the only way
        forward from there is creating the account (or deleting the
        employee if a mistake needs undoing)."""
        self.ensure_one()
        if self.recycle_state == 'accepted':
            raise UserError(_(
                'This application has already been accepted at the final '
                'stage — the hiring pipeline is closed.'))

    def action_recycle_stage_approve(self):
        self.ensure_one()
        self._recycle_check_admin()
        self._recycle_check_pipeline_open()
        self.write({'recycle_stage_status': 'approved'})

    def action_recycle_stage_reject(self):
        self.ensure_one()
        self._recycle_check_admin()
        self._recycle_check_pipeline_open()
        self.write({'recycle_stage_status': 'rejected'})

    def action_recycle_advance_stage(self):
        self.ensure_one()
        self._recycle_check_admin()
        self._recycle_check_pipeline_open()
        if self.recycle_stage_status != 'approved':
            raise UserError(_(
                'Approve the current stage before moving to the next one.'))
        nxt = self._recycle_next_stage()
        if not nxt:
            raise UserError(_('This is already the final stage.'))
        prev_stage = self.stage_id
        self.write({'stage_id': nxt.id})
        self.env['recycle.applicant.stage.log'].sudo().create({
            'applicant_id': self.id,
            'stage_id': prev_stage.id,
            'next_stage_id': nxt.id,
            'decided_by': self.env.user.id,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'title': _('Stage Advanced'),
                'message': _('Moved to "%s".') % nxt.name,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    def _recycle_check_admin(self):
        if not self.env.user.has_group('recycle_warehouse.group_recycle_admin'):
            raise UserError(_('Only administrators can manage applications.'))

    def action_recycle_delete_employee(self):
        """Admin: delete the employee created from this application — their
        user account, all their job applications and HR record — detaching
        them from their warehouse/manager role. Shipment records are kept."""
        self.ensure_one()
        self._recycle_check_admin()
        if not self.employee_user_id:
            raise UserError(_('There is no employee account for this applicant.'))
        name = self.employee_user_id.sudo()._recycle_purge()
        # The current application was deleted as part of the purge, so go back
        # to the applications list.
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'title': _('Employee Deleted'),
                'message': _('"%s" and all related data were removed. '
                             'Shipment records were kept.') % (name or ''),
                'next': {
                    'type': 'ir.actions.act_window',
                    'name': _('Job Applications'),
                    'res_model': 'hr.applicant',
                    'view_mode': 'list,form',
                    'target': 'main',
                },
            },
        }

    # ---------------- User creation ----------------

    def _create_recycle_user(self, role=None, warehouse=None):
        """Upgrade (or create) the applicant's user account.
        role=None -> employee without role yet (manager assigns it later)."""
        self.ensure_one()
        if self.employee_user_id:
            raise UserError(_('A user has already been created for this applicant.'))
        if self.recycle_state != 'accepted':
            raise UserError(_('The application must be Accepted first.'))
        login = (self.recycle_email or '').strip().lower()
        if not login:
            raise UserError(_('The applicant has no email address.'))
        Users = self.env['res.users'].sudo()
        user = Users.search([('login', '=', login)], limit=1)
        if user:
            # The applicant signed up on the website (portal user):
            # upgrade that same account so they keep their password.
            user.write({
                'recycle_warehouse_id': warehouse.id if warehouse else False,
                'recycle_role': role or False,
            })
        else:
            user = Users.with_context(no_reset_password=True).create({
                'name': self.recycle_name or login,
                'login': login,
                'email': login,
                'recycle_warehouse_id': warehouse.id if warehouse else False,
                'recycle_role': role or False,
            })
        # Groups: remove portal, add internal user + role group (atomic write)
        groups_field = 'group_ids' if 'group_ids' in user._fields else 'groups_id'
        ops = []
        portal_group = self.env.ref('base.group_portal', raise_if_not_found=False)
        if portal_group and portal_group in user[groups_field]:
            ops.append((3, portal_group.id))
        ops.append((4, self.env.ref('base.group_user').id))
        group_xmlid = ROLE_GROUP_MAP.get(role) if role else None
        if group_xmlid:
            ops.append((4, self.env.ref(group_xmlid).id))
        user.write({groups_field: ops})
        # HR integration: create the employee record
        self.env['hr.employee'].sudo().create({
            'name': user.name,
            'work_email': login,
            'user_id': user.id,
            'job_id': self.job_id.id if self.job_id else False,
        })
        self.sudo().write({
            'employee_user_id': user.id,
            'recycle_warehouse_id': warehouse.id if warehouse else False,
        })
        # Send password setup email if outgoing mail is configured
        try:
            user.sudo().action_reset_password()
        except Exception:
            pass
        return user

    def action_open_manager_wizard(self):
        """Admin: open the 'assign warehouse' dialog for an accepted manager applicant."""
        self.ensure_one()
        if not self.env.user.has_group('recycle_warehouse.group_recycle_admin'):
            raise UserError(_('Only administrators can create manager accounts.'))
        if self.recycle_state != 'accepted':
            raise UserError(_('Accept the application first.'))
        if self.recycle_job_type != 'manager':
            raise UserError(_('This application is not for a manager position.'))
        if self.employee_user_id:
            raise UserError(_('A user has already been created for this applicant.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Warehouse Manager'),
            'res_model': 'recycle.manager.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_applicant_id': self.id},
        }

    def action_open_employee_wizard(self):
        """Admin: open the 'assign warehouse' dialog for an accepted employee applicant."""
        self.ensure_one()
        if not self.env.user.has_group('recycle_warehouse.group_recycle_admin'):
            raise UserError(_('Only administrators can create employee accounts.'))
        if self.recycle_state != 'accepted':
            raise UserError(_('Accept the application first.'))
        if self.recycle_job_type == 'manager':
            raise UserError(_('This application is not for an employee position.'))
        if self.employee_user_id:
            raise UserError(_('A user has already been created for this applicant.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Warehouse Employee'),
            'res_model': 'recycle.employee.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_applicant_id': self.id},
        }

    def action_open_role_wizard(self):
        """Warehouse manager: open the role-selection dialog for an employee."""
        self.ensure_one()
        if not self.employee_user_id:
            raise UserError(_(
                'No user account yet.\n'
                'The administrator must create the employee account first.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Assign Employee Role'),
            'res_model': 'recycle.role.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_applicant_id': self.id},
        }

    # ---------------- Web (Admin Home dashboard) processing ----------------
    # These mirror the wizards above but return plain values so the custom
    # Owl dashboard can call them directly (orm.call) instead of opening the
    # native Odoo dialogs.

    def action_recycle_web_reject(self, reason=None):
        """Reject the current stage and record the reason (from the small
        reject dialog in the custom UI)."""
        self.ensure_one()
        self._recycle_check_admin()
        self._recycle_check_pipeline_open()
        self.write({
            'recycle_stage_status': 'rejected',
            'recycle_reject_reason': (reason or '').strip() or False,
        })
        try:
            if reason:
                self.message_post(body=_('Rejected: %s') % reason)
        except Exception:
            pass
        return True

    def action_recycle_web_schedule_interview(self, when, location=None, notes=None):
        """Set the interview date/details and email the applicant."""
        self.ensure_one()
        self._recycle_check_admin()
        if not (self.recycle_email or '').strip():
            raise UserError(_('This applicant has no email address on file.'))
        if not when:
            raise UserError(_('Please pick an interview date and time.'))
        self.sudo().write({
            'recycle_interview_datetime': when,
            'recycle_interview_location': (location or '').strip() or False,
            'recycle_interview_notes': (notes or '').strip() or False,
        })
        sent = self._send_interview_email(
            self.recycle_interview_datetime, location, notes)
        try:
            self.message_post(body=_('Interview scheduled by %s.')
                              % self.env.user.name)
        except Exception:
            pass
        return {'sent': bool(sent)}

    def _recycle_check_single_warehouse(self):
        """An applicant must never end up assigned to more than one
        warehouse. If a user account already exists for this applicant's
        email (from a previous acceptance) and is already tied to a
        warehouse, block creating/reassigning a new one."""
        self.ensure_one()
        login = (self.recycle_email or '').strip().lower()
        if not login:
            return
        existing = self.env['res.users'].sudo().with_context(
            active_test=False).search([('login', '=', login)], limit=1)
        if existing and existing.recycle_warehouse_id:
            raise UserError(_(
                'This person is already assigned to warehouse "%s".\n'
                'An employee cannot belong to more than one warehouse.'
            ) % existing.recycle_warehouse_id.name)

    def action_recycle_web_create_account(self, warehouse_id, role=None):
        """Create the employee/manager account for an accepted applicant.

        For a manager position the warehouse must be free. For a specialized
        employee position (Input/Sorting/Output) the role is
        forced to the job's own type — the incoming `role` is ignored/
        validated, never freely chosen. For a general employee position the
        role is optional (the warehouse manager can assign it later)."""
        self.ensure_one()
        self._recycle_check_admin()
        if self.recycle_state != 'accepted':
            raise UserError(_('The application must be Accepted first.'))
        if self.employee_user_id:
            raise UserError(_('A user has already been created for this applicant.'))
        if not warehouse_id:
            raise UserError(_('Please select a warehouse.'))
        warehouse = self.env['recycle.warehouse'].sudo().browse(int(warehouse_id))
        if not warehouse.exists():
            raise UserError(_('Please select a valid warehouse.'))
        self._recycle_check_single_warehouse()
        if self.recycle_job_type == 'manager':
            if warehouse.manager_user_id:
                raise UserError(_(
                    'Warehouse "%s" already has a manager (%s).'
                ) % (warehouse.name, warehouse.manager_user_id.name))
            user = self._create_recycle_user(role='manager', warehouse=warehouse)
            warehouse.write({'manager_user_id': user.id})
            self.sudo().write({'recycle_role': 'manager'})
        elif self._recycle_is_specialized():
            # Specialized job: the role is the job type itself — the admin
            # may only choose WHETHER to assign it now, never WHICH role.
            effective_role = self.recycle_job_type if role else None
            user = self._create_recycle_user(role=effective_role, warehouse=warehouse)
        else:
            user = self._create_recycle_user(role=role or None, warehouse=warehouse)
        try:
            self.message_post(body=_('Account "%s" created for warehouse "%s".')
                              % (user.login, warehouse.name))
        except Exception:
            pass
        return {'user_id': user.id, 'name': user.name}


class RecycleApplicantStageLog(models.Model):
    """One row per completed pipeline stage: exactly when it was approved
    and the applicant moved on to the next stage. Created only by
    action_recycle_advance_stage — never edited afterwards."""
    _name = 'recycle.applicant.stage.log'
    _description = 'Applicant Stage Transition Log'
    _order = 'decided_at desc, id desc'

    applicant_id = fields.Many2one(
        'hr.applicant', required=True, ondelete='cascade', index=True)
    stage_id = fields.Many2one(
        'hr.recruitment.stage', string='Completed Stage', required=True)
    next_stage_id = fields.Many2one(
        'hr.recruitment.stage', string='Moved To')
    decided_by = fields.Many2one(
        'res.users', string='Approved By', required=True,
        default=lambda self: self.env.user)
    decided_at = fields.Datetime(
        string='Approved & Advanced At', required=True,
        default=fields.Datetime.now)
