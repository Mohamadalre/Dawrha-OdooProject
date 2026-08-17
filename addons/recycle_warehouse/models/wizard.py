# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import format_datetime
from .recruitment import EMPLOYEE_ROLES

WEIGHT_TOLERANCE = 5.0


class RecycleReceiveWizard(models.TransientModel):
    """Reception screen for input employees:
    scan/type the shipment ID, the shipment is auto-reserved, info is shown
    read-only, the employee enters the actual weight then accepts (<=5%),
    transfers to the manager (>5%) or releases the shipment."""
    _name = 'recycle.receive.wizard'
    _description = 'Process Shipment (Reception)'

    input_mode = fields.Selection([
        ('manual', 'Enter Shipment ID'),
        ('scan', 'Scan Barcode Image'),
    ], string='Input Method', default='manual', required=True)
    barcode_image = fields.Binary(string='Barcode Image')
    shipment_ref = fields.Char(string='Shipment ID / Barcode')
    shipment_id = fields.Many2one('recycle.shipment', string='Shipment', readonly=True)
    driver_name = fields.Char(related='shipment_id.driver_name', readonly=True)
    warehouse_id = fields.Many2one(related='shipment_id.warehouse_id', readonly=True)
    priority = fields.Integer(related='shipment_id.priority', readonly=True)
    expected_weight = fields.Float(related='shipment_id.expected_weight', readonly=True)
    state = fields.Selection(related='shipment_id.state', readonly=True)
    actual_weight = fields.Float(string='Actual Weight (kg)')
    diff_pct = fields.Float(string='Weight Difference (%)', compute='_compute_diff_pct')

    @api.depends('actual_weight', 'shipment_id', 'shipment_id.expected_weight')
    def _compute_diff_pct(self):
        for wiz in self:
            if wiz.shipment_id and wiz.shipment_id.expected_weight and wiz.actual_weight:
                wiz.diff_pct = abs(
                    wiz.actual_weight - wiz.shipment_id.expected_weight
                ) / wiz.shipment_id.expected_weight * 100.0
            else:
                wiz.diff_pct = 0.0

    def _reopen(self):
        """Return an action that reopens this wizard dialog."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Process Shipment'),
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _alert(self, alert_type, title, message, sticky=False):
        """Show a professional notification banner and reopen the wizard.

        alert_type: 'danger' | 'warning' | 'info' | 'success'
        """
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': alert_type,
                'title': title,
                'message': message,
                'sticky': sticky,
                'next': self._reopen(),
            },
        }

    # ------------------------------------------------------------------ #
    #  Step 1 – Load / scan shipment                                       #
    # ------------------------------------------------------------------ #

    def action_scan_barcode(self):
        """Decode the uploaded barcode image and load the matching shipment."""
        self.ensure_one()
        if not self.barcode_image:
            return self._alert(
                'warning', _('No Image Uploaded'),
                _('Please upload a barcode image before scanning.'))
        try:
            from pyzbar import pyzbar
        except ImportError:
            return self._alert(
                'danger', _('Barcode Library Missing'),
                _(
                    'The barcode library is not installed on the server.\n'
                    'Ask the administrator to run inside the Odoo container:\n'
                    'apt-get install -y libzbar0  &&  '
                    'pip3 install pyzbar --break-system-packages'
                ), sticky=True)
        import base64, io
        from PIL import Image
        try:
            image = Image.open(io.BytesIO(base64.b64decode(self.barcode_image)))
        except Exception:
            return self._alert(
                'danger', _('Invalid Image'),
                _('Cannot open the file as an image. Upload a valid PNG/JPG barcode photo.'))
        codes = pyzbar.decode(image)
        if not codes:
            return self._alert(
                'warning', _('No Barcode Detected'),
                _('No barcode was found in the image.\n'
                  'Try a clearer, well-lit photo taken straight-on.'))
        self.shipment_ref = codes[0].data.decode('utf-8', errors='ignore').strip()
        return self.action_load()

    def action_load(self):
        """Find the shipment by its database ID (the barcode encodes the
        ID, not the display reference) and auto-reserve it."""
        self.ensure_one()
        ref = (self.shipment_ref or '').strip()
        if not ref:
            return self._alert(
                'warning', _('Shipment ID Required'),
                _('Enter the shipment ID in the field above or use the barcode scanner.'))
        try:
            shipment_id = int(ref)
        except ValueError:
            return self._alert(
                'danger', _('Invalid Shipment ID'),
                _('"%s" is not a valid shipment ID.') % ref)
        shipment = self.env['recycle.shipment'].search(
            [('id', '=', shipment_id)], limit=1)
        if not shipment:
            return self._alert(
                'danger', _('Shipment Not Found'),
                _('No shipment matches the ID "%s".\n'
                  'It may not exist, belong to a different warehouse, '
                  'or already be reserved by a colleague.') % ref)
        if shipment.state not in ('pending', 'receiving'):
            state_label = dict(shipment._fields['state'].selection).get(
                shipment.state, shipment.state)
            return self._alert(
                'danger', _('Cannot Process This Shipment'),
                _('Shipment %s is currently in status "%s" and '
                  'cannot be processed at this stage.') % (shipment.name, state_label))
        # Auto-reserve (raises UserError if already reserved by someone else — kept as-is)
        shipment._check_reservation('receiver_user_id')
        if shipment.state == 'pending':
            shipment.action_start_receiving()
        self.write({
            'shipment_id': shipment.id,
            'actual_weight': shipment.actual_weight,
        })
        return self._reopen()

    # ------------------------------------------------------------------ #
    #  Step 2 – Accept / Transfer / Release                                #
    # ------------------------------------------------------------------ #

    def action_accept(self):
        """Accept the shipment and send it to sorting."""
        self.ensure_one()
        if not self.shipment_id:
            return self._alert(
                'warning', _('No Shipment Loaded'),
                _('Load a shipment first — enter or scan its ID above.'))
        self.shipment_id.write({'actual_weight': self.actual_weight})
        self.shipment_id.action_accept()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'title': _('Shipment Accepted'),
                'message': _('%s has been accepted and sent to the sorting area.')
                           % self.shipment_id.name,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    def action_transfer(self):
        """Escalate the shipment to the warehouse manager (weight mismatch > 5%)."""
        self.ensure_one()
        if not self.shipment_id:
            return self._alert(
                'warning', _('No Shipment Loaded'),
                _('Load a shipment first — enter or scan its ID above.'))
        self.shipment_id.write({'actual_weight': self.actual_weight})
        if self.shipment_id.weight_diff_pct <= WEIGHT_TOLERANCE:
            return self._alert(
                'info', _('Transfer Not Required'),
                _('The weight difference is within %.1f%% — '
                  'you can accept this shipment directly.') % WEIGHT_TOLERANCE)
        self.shipment_id.action_escalate()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'warning',
                'title': _('Transferred to Warehouse Manager'),
                'message': _('%s has been transferred to the warehouse manager for review.')
                           % self.shipment_id.name,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    def action_release(self):
        """Release the reservation so other employees can process the shipment."""
        self.ensure_one()
        if not self.shipment_id:
            return self._alert(
                'warning', _('No Shipment Loaded'),
                _('There is no shipment to release.'))
        self.shipment_id.action_release()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'title': _('Shipment Released'),
                'message': _('%s is now available for any employee to process.')
                           % self.shipment_id.name,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }


# ======================================================================= #
#  Interview scheduling wizard  (admin → applicant email notification)     #
# ======================================================================= #

class RecycleInterviewWizard(models.TransientModel):
    """Admin dialog to set the interview date/time and details, then move the
    application to the Interview stage and email the applicant."""
    _name = 'recycle.interview.wizard'
    _description = 'Schedule Interview'

    applicant_id = fields.Many2one('hr.applicant', required=True, readonly=True, string='Applicant Record')
    applicant_name = fields.Char(
        related='applicant_id.recycle_name', string='Applicant', readonly=True)
    applicant_email = fields.Char(
        related='applicant_id.recycle_email', string='Email', readonly=True)
    job_name = fields.Char(
        related='applicant_id.job_id.name', string='Position', readonly=True)
    interview_datetime = fields.Datetime(
        string='Interview Date & Time', required=True)
    location = fields.Char(
        string='Location / Video Link',
        help='Office address or a video-call link sent to the applicant.')
    notes = fields.Text(
        string='Message to Applicant',
        help='Optional message included in the interview email.')

    def action_confirm(self):
        self.ensure_one()
        app = self.applicant_id
        if not self.env.user.has_group('recycle_warehouse.group_recycle_admin'):
            raise UserError(_('Only administrators can schedule interviews.'))
        if not (app.recycle_email or '').strip():
            raise UserError(_('This applicant has no email address on file.'))
        if self.interview_datetime < fields.Datetime.now():
            raise UserError(_('The interview date/time must be in the future.'))

        app.sudo().write({
            'recycle_interview_datetime': self.interview_datetime,
            'recycle_interview_location': self.location,
            'recycle_interview_notes': self.notes,
        })
        sent = app._send_interview_email(
            self.interview_datetime, self.location, self.notes)
        app.message_post(body=_(
            'Interview scheduled for %s by %s.') % (
                format_datetime(self.env, self.interview_datetime),
                self.env.user.name))

        if sent:
            msg = _('An email with the interview details was sent to %s.') % (
                app.recycle_email)
            ntype = 'success'
        else:
            msg = _('The application moved to Interview, but the email could '
                    'not be sent. Check the outgoing mail server.')
            ntype = 'warning'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': ntype,
                'title': _('Interview Scheduled'),
                'message': msg,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }


# ======================================================================= #
#  Role assignment wizard  (warehouse manager → employee)                  #
# ======================================================================= #

class RecycleRoleWizard(models.TransientModel):
    """Popup dialog that lets a warehouse manager pick one of the three
    employee roles (Input / Sorting / Output) and immediately applies it
    to the employee's user account and group membership."""
    _name = 'recycle.role.wizard'
    _description = 'Assign Employee Role'

    applicant_id = fields.Many2one('hr.applicant', required=True, readonly=True, string='Applicant Record')
    employee_name = fields.Char(
        related='applicant_id.recycle_name', string='Employee', readonly=True)
    warehouse_name = fields.Char(
        related='applicant_id.recycle_warehouse_id.name', string='Warehouse', readonly=True)
    current_role = fields.Selection(
        related='applicant_id.recycle_role', string='Current Role', readonly=True)
    role = fields.Selection([
        ('input',       'Input Employee'),
        ('sorting',     'Sorting Employee'),
        ('output',      'Output Employee'),
    ], string='New Role', required=True, default=lambda self: self._default_role(),
       help='Select the role to assign to this employee.\n'
            'Input = receives shipments | Sorting = sorts items | '
            'Output = manages outgoing orders.')

    def _default_role(self):
        applicant_id = self.env.context.get('default_applicant_id')
        if applicant_id:
            app = self.env['hr.applicant'].browse(applicant_id)
            if app.exists() and app._recycle_is_specialized():
                return app.recycle_job_type
        return False
    shift_id = fields.Many2one(
        'recycle.shift', string='Work Shift',
        domain=[('active', '=', True)],
        help='Select the shift this employee will work. Required for attendance tracking.')

    _ROLE_GROUP = {
        'input':       'recycle_warehouse.group_recycle_input',
        'sorting':     'recycle_warehouse.group_recycle_sorting',
        'output':      'recycle_warehouse.group_recycle_output',
    }

    def action_confirm(self):
        self.ensure_one()
        app = self.applicant_id
        env_user = self.env.user
        if not app.employee_user_id:
            raise UserError(_(
                'No user account exists for this employee yet.\n'
                'Ask the administrator to create the account first.'))
        # Manager can only assign roles within their own warehouse
        if not env_user.has_group('recycle_warehouse.group_recycle_admin'):
            mgr_wh = self.env['recycle.warehouse'].sudo().search(
                [('manager_user_id', '=', env_user.id)], limit=1)
            if not mgr_wh and env_user.recycle_warehouse_id:
                mgr_wh = env_user.recycle_warehouse_id
            if not mgr_wh:
                raise UserError(_('You are not assigned as manager of any warehouse.'))
            if app.recycle_warehouse_id != mgr_wh:
                raise UserError(_('This employee does not belong to your warehouse.'))
        if app._recycle_is_specialized() and self.role != app.recycle_job_type:
            raise UserError(_(
                'This position is specialized for "%s" — you cannot assign a '
                'different role.'
            ) % dict(EMPLOYEE_ROLES).get(app.recycle_job_type, app.recycle_job_type))
        user = app.employee_user_id.sudo()
        groups_field = 'group_ids' if 'group_ids' in user._fields else 'groups_id'
        # Remove all current employee-role groups then add the chosen one
        ops = [(3, self.env.ref(xmlid).id) for xmlid in self._ROLE_GROUP.values()
               if self.env.ref(xmlid) in user[groups_field]]
        ops.append((4, self.env.ref(self._ROLE_GROUP[self.role]).id))
        user_vals = {groups_field: ops, 'recycle_role': self.role}
        if self.shift_id:
            user_vals['shift_id'] = self.shift_id.id
        user.write(user_vals)
        app.sudo().write({'recycle_role': self.role})
        role_label = dict(self._fields['role'].selection).get(self.role, self.role)
        app.message_post(body=_(
            'Role changed to "%s" by %s.') % (role_label, env_user.name))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'title': _('Role Assigned'),
                'message': _('%s is now: %s.') % (user.name, role_label),
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }


# ======================================================================= #
#  Admin wizards                                                            #
# ======================================================================= #

class RecycleManagerWizard(models.TransientModel):
    _name = 'recycle.manager.wizard'
    _description = 'Assign Warehouse Manager'

    applicant_id = fields.Many2one('hr.applicant', required=True, readonly=True, string='Applicant Record')
    applicant_name = fields.Char(
        related='applicant_id.recycle_name', string='Applicant', readonly=True)
    applicant_email = fields.Char(
        related='applicant_id.recycle_email', string='Email', readonly=True)
    warehouse_id = fields.Many2one(
        'recycle.warehouse', string='Assign to Warehouse', required=True,
        domain=[('manager_user_id', '=', False)],
        help='Only warehouses that do not yet have a manager are listed.')

    def action_confirm(self):
        self.ensure_one()
        app = self.applicant_id
        if app.recycle_state != 'accepted':
            raise UserError(_('The application must be in "Accepted" status first.'))
        if app.recycle_job_type != 'manager':
            raise UserError(_('This application is not for a Manager position.'))
        if app.employee_user_id:
            raise UserError(_('A user account has already been created for this applicant.'))
        if self.warehouse_id.manager_user_id:
            raise UserError(_(
                'Warehouse "%s" already has a manager (%s).\n'
                'Each warehouse can have exactly ONE manager. '
                'Please choose a different warehouse.'
            ) % (self.warehouse_id.name, self.warehouse_id.manager_user_id.name))
        app._recycle_check_single_warehouse()
        user = app._create_recycle_user(role='manager', warehouse=self.warehouse_id)
        self.warehouse_id.write({'manager_user_id': user.id})
        app.sudo().write({'recycle_role': 'manager'})
        app.message_post(body=_(
            'Manager account "%s" created and assigned to warehouse "%s".'
        ) % (user.login, self.warehouse_id.name))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'title': _('Manager Account Created'),
                'message': _('%s is now the manager of %s.') % (
                    user.name, self.warehouse_id.name),
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }


class RecycleEmployeeWizard(models.TransientModel):
    _name = 'recycle.employee.wizard'
    _description = 'Assign Warehouse Employee'

    applicant_id = fields.Many2one('hr.applicant', required=True, readonly=True, string='Applicant Record')
    applicant_name = fields.Char(
        related='applicant_id.recycle_name', string='Applicant', readonly=True)
    applicant_email = fields.Char(
        related='applicant_id.recycle_email', string='Email', readonly=True)
    warehouse_id = fields.Many2one(
        'recycle.warehouse', string='Assign to Warehouse', required=True,
        help='The employee will belong to this warehouse. '
             'The role (Input / Sorting / Output) is assigned later by the warehouse manager.')

    def action_confirm(self):
        self.ensure_one()
        app = self.applicant_id
        if app.recycle_state != 'accepted':
            raise UserError(_('The application must be in "Accepted" status first.'))
        if app.recycle_job_type == 'manager':
            raise UserError(_('This application is not for an Employee position.'))
        if app.employee_user_id:
            raise UserError(_('A user account has already been created for this applicant.'))
        app._recycle_check_single_warehouse()
        role = app.recycle_job_type if app._recycle_is_specialized() else None
        user = app._create_recycle_user(role=role, warehouse=self.warehouse_id)
        app.message_post(body=_(
            'Employee account "%s" created and assigned to warehouse "%s". '
            'The warehouse manager will assign the role.'
        ) % (user.login, self.warehouse_id.name))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'title': _('Employee Account Created'),
                'message': _('%s is now assigned to %s. '
                             'The warehouse manager will set their role.') % (
                    user.name, self.warehouse_id.name),
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }


class RecycleAddAdminWizard(models.TransientModel):
    """Configuration → Users → Add Administrator.

    Creates an internal user that carries the Recycle 'Administration'
    role exclusively (spec: add user with admin permissions only)."""
    _name = 'recycle.add.admin.wizard'
    _description = 'Add Administrator User'

    name = fields.Char(string='Full Name', required=True)
    email = fields.Char(string='Email', required=True)

    def action_create_admin(self):
        self.ensure_one()
        if not self.env.user.has_group('recycle_warehouse.group_recycle_admin'):
            raise UserError(_('Only administrators can add admin users.'))
        email = (self.email or '').strip().lower()
        if not email or '@' not in email:
            raise UserError(_('Please enter a valid email address.'))
        Users = self.env['res.users'].sudo()
        if Users.with_context(active_test=False).search_count(
                [('login', '=', email)]):
            raise UserError(_('A user with this email already exists.'))
        groups = [
            self.env.ref('base.group_user').id,
            self.env.ref('recycle_warehouse.group_recycle_admin').id,
        ]
        user = Users.create({
            'name': (self.name or '').strip(),
            'login': email,
            'email': email,
            'recycle_role': 'admin',
            'group_ids': [(6, 0, groups)],
        })
        # Send the branded "Set Password" email so they choose their own
        # password on first login.
        try:
            user.partner_id.sudo().signup_prepare()
            self.env.ref(
                'recycle_warehouse.email_template_set_password'
            ).sudo().send_mail(user.id, force_send=True)
        except Exception:
            pass
        return {'type': 'ir.actions.act_window_close'}
