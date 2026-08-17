# -*- coding: utf-8 -*-
"""Delivery drivers — hired HERE, unlike collectors.

The fleet carries two kinds of driver and they have almost nothing in common:

  COLLECTOR      applies through the mobile app, has an account in the NestJS
                 backend, works a SHIFT, picks material up from citizens, and is
                 approved through `recycle.driver.request`. Odoo mirrors him.
  DELIVERY DRIVER is recruited by the administrator in Odoo, has no backend
                 account at all, works NO shift, and carries sold goods from a
                 warehouse to the buyer who bought them.

Because a collector's identity lives in another system, the two could not share
one table without one of them being half-empty: a collector has no licence
scan stored here, and a delivery driver has no backend uuid, no shift and no
onboarding state. Modelling them separately is what lets each carry only the
facts that are true of it.

The licence images are REQUIRED, both of them. A driving licence is the one
document that decides whether this person may legally be behind the wheel of a
company truck, and half of it proves nothing: the expiry and the class are on
the back.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class RecycleDeliveryDriver(models.Model):
    _name = 'recycle.delivery.driver'
    _description = 'Delivery Driver'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char('Full Name', required=True, tracking=True)
    phone = fields.Char('Phone', required=True, tracking=True)
    email = fields.Char('Email')
    national_id = fields.Char('National ID', required=True, index=True, tracking=True)
    address = fields.Char('Address')
    birth_date = fields.Date('Date of Birth')
    notes = fields.Text('Notes')

    # ── Driving licence: both sides, both required ──────────────────────────
    license_number = fields.Char('Licence Number', tracking=True)
    license_expiry = fields.Date('Licence Expiry', tracking=True)
    license_image_front = fields.Binary(
        'Licence — Front', attachment=True, required=True,
        help='Photo of the FRONT of the driving licence.')
    license_image_front_name = fields.Char('Front Image Name')
    license_image_back = fields.Binary(
        'Licence — Back', attachment=True, required=True,
        help='Photo of the BACK of the driving licence. Required as well as the '
             'front: the expiry date and the licence class are printed there, '
             'and they are what decide whether this person may drive at all.')
    license_image_back_name = fields.Char('Back Image Name')

    warehouse_id = fields.Many2one(
        'recycle.warehouse', string='Warehouse', required=True, index=True,
        ondelete='restrict', tracking=True,
        help='The warehouse this driver delivers from. Deliveries start at a '
             'warehouse, so a driver belonging to none has nowhere to load.')
    truck_id = fields.Many2one(
        'recycle.truck', string='Delivery Truck', tracking=True,
        ondelete='set null',
        domain="[('truck_type', '=', 'delivery')]",
        help='A DELIVERY truck. Collection trucks run pick-up rounds on a shift '
             'and are driven by backend collectors.')
    is_active = fields.Boolean('Active', default=True, tracking=True)
    # ── Blocking ────────────────────────────────────────────────────────────
    #
    # Separate from `is_active`. "Inactive" is an administrative state — on
    # leave, off the roster, seasonal. "Blocked" is a decision about the person,
    # and it must also stop them signing in. Folding the two into one flag would
    # mean every driver taken off the roster looks disciplined, and every
    # blocked one can be quietly reinstated by ticking a box that says nothing.
    is_blocked = fields.Boolean('Blocked', default=False, tracking=True, index=True)
    blocked_reason = fields.Char('Block Reason', copy=False)
    blocked_at = fields.Datetime('Blocked At', readonly=True, copy=False)
    blocked_by = fields.Many2one(
        'res.users', string='Blocked By', readonly=True, copy=False)

    # The login this driver signs in with. Their dashboard is an Odoo screen, so
    # they need a user; created on demand rather than always, because a driver
    # may be recorded before they are given access.
    user_id = fields.Many2one(
        'res.users', string='Login', readonly=True, copy=False,
        ondelete='set null')

    truck_plate = fields.Char(
        'Truck Plate', related='truck_id.plate_number', readonly=True)
    # Every truck this person has ever held, newest first. Read straight off the
    # record so the printed file and the screen cannot disagree.
    truck_history_ids = fields.One2many(
        'recycle.truck.assignment.history', 'delivery_driver_id',
        string='Trucks Held', readonly=True)
    has_truck = fields.Boolean(
        'Has a Truck', compute='_compute_has_truck', store=True,
        help='Stored so the "assigned / unassigned" filter is a plain indexed '
             'search rather than a scan of every driver.')

    _national_id_uniq = models.Constraint(
        'unique(national_id)',
        'A delivery driver with this national ID already exists.')

    @api.constrains('national_id', 'email')
    def _check_identity_unique(self):
        """The national ID and email must be free ACROSS the whole system.

        The unique index above only covers this table. A delivery driver who is
        also on file as an employee or an applicant would pass it and still be
        the same person recorded twice — which is two blocks, two document sets,
        and no way to say which record is them.
        """
        Guard = self.env['recycle.identity.guard']
        for rec in self:
            # Checks AND claims. The search alone can be beaten by a request
            # arriving between it and the write; the claim is a row behind a
            # UNIQUE index, so a concurrent duplicate is refused by the database
            # rather than by luck.
            Guard.register_identity(
                'recycle.delivery.driver', rec.id,
                national_id=rec.national_id, email=rec.email)

    def unlink(self):
        """Give the identities back before the record goes.

        A claim left behind by a deleted driver blocks a real person with a row
        that names nobody — and the person it blocks is usually the same one,
        re-registering after a mistake.
        """
        Guard = self.env['recycle.identity.guard']
        for rec in self:
            Guard.release_identity('recycle.delivery.driver', rec.id)
        return super().unlink()

    @api.depends('truck_id')
    def _compute_has_truck(self):
        for rec in self:
            rec.has_truck = bool(rec.truck_id)

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------
    def write(self, vals):
        """Record every change of holder, whichever screen made it.

        Written here rather than in the assign/unassign actions because the
        truck can also change from the classic Odoo form, from an import, or
        from the warehouse-move release — and a history that only some paths
        write to is a history nobody can trust.
        """
        History = self.env['recycle.truck.assignment.history']
        track = 'truck_id' in vals and not self.env.context.get(
            'recycle_history_done')
        before = {rec.id: rec.truck_id for rec in self} if track else {}

        res = super().write(vals)

        if track:
            for rec in self:
                old, new = before.get(rec.id), rec.truck_id
                if old == new:
                    continue
                if old:
                    History.close_open_periods(
                        old, reason='manual', delivery_driver=rec)
                if new:
                    History.open_period(new, 'delivery', delivery_driver=rec)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        History = self.env['recycle.truck.assignment.history']
        for rec in records:
            if rec.truck_id:
                History.open_period(rec.truck_id, 'delivery',
                                    delivery_driver=rec)
        return records

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    @api.constrains('truck_id')
    def _check_truck_type(self):
        """A delivery driver drives a DELIVERY truck, and only one driver per truck.

        The domain on the field guides the picker; this enforces it. A record can
        also be written by the dashboard route and by an import, and a rule that
        lives only in a widget is a rule those paths do not have.
        """
        for rec in self:
            if not rec.truck_id:
                continue
            if rec.truck_id.truck_type != 'delivery':
                raise ValidationError(_(
                    'Truck "%s" is a collection truck. Delivery drivers can '
                    'only be assigned to delivery trucks.') % rec.truck_id.name)
            clash = self.search([
                ('truck_id', '=', rec.truck_id.id),
                ('id', '!=', rec.id),
                ('is_active', '=', True),
            ], limit=1)
            if clash:
                raise ValidationError(_(
                    'Truck "%(truck)s" is already assigned to %(driver)s.') % {
                        'truck': rec.truck_id.name, 'driver': clash.name})

    @api.constrains('truck_id', 'warehouse_id')
    def _check_truck_warehouse(self):
        """The truck must belong to the driver's own warehouse.

        Otherwise a driver is booked onto a vehicle parked at a site they never
        load from — an assignment that reads as done and cannot be worked.
        """
        for rec in self:
            if not rec.truck_id or not rec.truck_id.warehouse_id:
                continue
            if rec.truck_id.warehouse_id.id != rec.warehouse_id.id:
                raise ValidationError(_(
                    'Truck "%(truck)s" belongs to warehouse "%(tw)s", but this '
                    'driver delivers from "%(dw)s".') % {
                        'truck': rec.truck_id.name,
                        'tw': rec.truck_id.warehouse_id.name,
                        'dw': rec.warehouse_id.name})

    @api.constrains('license_image_front', 'license_image_back')
    def _check_license_images(self):
        for rec in self:
            if not rec.license_image_front or not rec.license_image_back:
                raise ValidationError(_(
                    'Both sides of the driving licence are required.'))

    # ------------------------------------------------------------------
    # Scope
    # ------------------------------------------------------------------
    @api.model
    def _actor_scope(self):
        """(is_admin, forced_warehouse) — who is allowed to act, and where.

        Same shape as the collector-assignment scope, deliberately: a manager may
        only ever touch their own warehouse, and the dashboard routes below run
        under sudo AFTER this check rather than relying on record rules alone.
        """
        user = self.env.user
        if self.env.su or user.has_group('recycle_warehouse.group_recycle_admin'):
            return True, self.env['recycle.warehouse'].browse()
        if user.has_group('recycle_warehouse.group_recycle_manager'):
            wh = self.env['recycle.warehouse'].sudo().search(
                ['|', ('manager_user_id', '=', user.id),
                 ('id', '=', user.recycle_warehouse_id.id)], limit=1)
            if wh:
                return False, wh
        raise UserError(_(
            'Only the administrator or a warehouse manager can manage delivery '
            'drivers.'))

    # ------------------------------------------------------------------
    # Assignment (manager + admin screens)
    # ------------------------------------------------------------------
    @api.model
    def free_delivery_trucks(self, warehouse_id=False):
        """Delivery trucks nobody is driving yet, inside the actor's scope."""
        is_admin, forced_wh = self._actor_scope()
        wh_id = forced_wh.id if not is_admin else int(warehouse_id or 0)

        taken = self.sudo().search(
            [('truck_id', '!=', False), ('is_active', '=', True)]
        ).mapped('truck_id').ids
        domain = [('truck_type', '=', 'delivery'),
                  ('is_active', '=', True),
                  ('id', 'not in', taken)]
        if wh_id:
            domain.append(('warehouse_id', '=', wh_id))
        trucks = self.env['recycle.truck'].sudo().search(domain, order='name')
        return [{
            'id': t.id,
            'name': t.name,
            'plate_number': t.plate_number,
            'model': t.model or '',
            'warehouse': t.warehouse_id.name or '',
        } for t in trucks]

    @api.model
    def action_assign_truck(self, driver_id, truck_id):
        """Give a delivery driver a truck. Every rule is re-checked here.

        The screen can be stale — a truck free when the list was drawn may have
        been taken since — so the decision is made against the data, not against
        what the browser last saw.
        """
        is_admin, forced_wh = self._actor_scope()
        driver = self.sudo().browse(int(driver_id or 0)).exists()
        if not driver:
            raise UserError(_('This delivery driver does not exist.'))
        if not is_admin and driver.warehouse_id.id != forced_wh.id:
            raise UserError(_(
                'You can only manage drivers of your own warehouse.'))

        truck = self.env['recycle.truck'].sudo().browse(
            int(truck_id or 0)).exists()
        if not truck or not truck.is_active:
            raise UserError(_('This truck is not available.'))
        if truck.truck_type != 'delivery':
            raise UserError(_(
                'Truck "%s" is a collection truck — delivery drivers are '
                'assigned to delivery trucks only.') % truck.name)
        if not is_admin and truck.warehouse_id.id != forced_wh.id:
            raise UserError(_(
                'You can only assign trucks of your own warehouse.'))

        driver.write({'truck_id': truck.id})
        driver.message_post(body=_('Assigned to truck %s (%s).') % (
            truck.name, truck.plate_number))
        return True

    @api.model
    def action_unassign_truck(self, driver_id):
        is_admin, forced_wh = self._actor_scope()
        driver = self.sudo().browse(int(driver_id or 0)).exists()
        if not driver:
            raise UserError(_('This delivery driver does not exist.'))
        if not is_admin and driver.warehouse_id.id != forced_wh.id:
            raise UserError(_(
                'You can only manage drivers of your own warehouse.'))
        driver.write({'truck_id': False})
        driver.message_post(body=_('Truck assignment removed.'))
        return True

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------
    def action_create_login(self):
        """Give this driver an Odoo login so they can open their dashboard.

        Separate from creating the driver: a driver may be on file before they
        are given access, and issuing a login is a decision of its own.
        """
        self.ensure_one()
        self._actor_scope()
        if self.user_id:
            raise UserError(_('This driver already has a login.'))
        if not self.email:
            raise UserError(_(
                'An email address is required to create a login — it is what '
                'the driver signs in with.'))

        group = self.env.ref('recycle_warehouse.group_recycle_delivery_driver')
        # Declared UP FRONT: the login carries this driver's national ID and
        # email, and `user_id` cannot be filled in until the user exists — so
        # without this the identity guard would refuse a driver their own
        # account, pointing at the driver themselves as the clash.
        user = self.env['res.users'].sudo().with_context(
            recycle_identity_owner=('recycle.delivery.driver', self.id),
        ).create({
            'name': self.name,
            'login': self.email,
            'email': self.email,
            'phone': self.phone,
            'recycle_warehouse_id': self.warehouse_id.id,
            'recycle_national_id': self.national_id,
            'group_ids': [(6, 0, [group.id])],
        })
        self.sudo().write({'user_id': user.id})
        self.message_post(body=_('Login created: %s') % self.email)
        return True

    # ------------------------------------------------------------------
    # Blocking
    # ------------------------------------------------------------------
    def action_block(self, reason=None):
        """Stop this driver working — and take the truck back.

        Leaving the vehicle with them would be the whole point of the block
        undone: the truck would sit unavailable to everyone else while the one
        person barred from driving it still holds it on paper.

        The login is disabled in the same breath. A block that leaves the
        account able to sign in is a note, not a block.
        """
        self._actor_scope()
        for rec in self:
            if rec.is_blocked:
                raise UserError(_('%s is already blocked.') % rec.name)
            note = (reason or '').strip()
            if not note:
                raise UserError(_(
                    'Give a reason for the block — it is what the driver is '
                    'told, and what the next reviewer reads.'))

            if rec.truck_id:
                self.env['recycle.truck.assignment.history'].close_open_periods(
                    rec.truck_id, reason='driver_blocked', delivery_driver=rec)
                rec.with_context(recycle_history_done=True).sudo().write(
                    {'truck_id': False})

            rec.sudo().write({
                'is_blocked': True,
                'blocked_reason': note,
                'blocked_at': fields.Datetime.now(),
                'blocked_by': self.env.user.id,
                'is_active': False,
            })
            if rec.user_id:
                rec.user_id.sudo().write({'active': False})
            rec.message_post(body=_('Blocked by %(who)s. Reason: %(why)s') % {
                'who': self.env.user.name, 'why': note})
        return True

    def action_unblock(self):
        """Let them work again. The truck is NOT given back automatically —
        it may have been handed to someone else in the meantime, and quietly
        taking it off that person would be a second surprise."""
        self._actor_scope()
        for rec in self:
            if not rec.is_blocked:
                raise UserError(_('%s is not blocked.') % rec.name)
            rec.sudo().write({
                'is_blocked': False,
                'blocked_reason': False,
                'blocked_at': False,
                'blocked_by': False,
                'is_active': True,
            })
            if rec.user_id:
                rec.user_id.sudo().write({'active': True})
            rec.message_post(body=_('Unblocked by %s.') % self.env.user.name)
        return True

    @api.model
    def for_user(self, user=None):
        """The driver record behind a login — the dashboard's entry point."""
        user = user or self.env.user
        return self.sudo().search([('user_id', '=', user.id)], limit=1)

    @api.model
    def backend_driver_for_truck(self, truck_id):
        """The active driver of a delivery truck — the backend's way to learn
        who to dispatch and notify once it has scored and picked the truck.

        Returns the driver's Odoo id, name, phone and whether they have a login,
        or an empty dict when the truck has no active driver (a real state the
        backend must handle, not an error to raise)."""
        driver = self.sudo().search([
            ('truck_id', '=', int(truck_id or 0)),
            ('is_active', '=', True),
            ('is_blocked', '=', False),
        ], limit=1)
        if not driver:
            return {}
        return {
            'driver_id': driver.id,
            'name': driver.name,
            'phone': driver.phone or '',
            'has_login': bool(driver.user_id),
        }

    @api.model
    def backend_available_driver_truck_ids(self, truck_ids):
        """Which of these delivery trucks have an AVAILABLE driver — active and
        unblocked — right now.

        The backend scores its fleet before it dispatches, and a truck with no
        driver cannot run; knowing this up front lets the score rank a driverless
        truck last (a last resort) instead of picking it and stalling at
        dispatch. One call for the whole candidate set rather than one per truck.
        Returns the subset of `truck_ids` that have such a driver."""
        ids = [int(t) for t in (truck_ids or []) if t]
        if not ids:
            return []
        drivers = self.sudo().search([
            ('truck_id', 'in', ids),
            ('is_active', '=', True),
            ('is_blocked', '=', False),
        ])
        return list({d.truck_id.id for d in drivers if d.truck_id})
