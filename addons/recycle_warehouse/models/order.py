# -*- coding: utf-8 -*-
import base64
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

ORDER_STATES = [
    ('pending', 'Pending'),
    ('processing', 'Processing'),
    ('ready', 'Ready'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
]


# Where a split part sits in the output queue.
#
# Ordinary orders default to 10 and `_order` is 'priority asc', so this puts
# every part of a split order ahead of them — in EVERY warehouse at once, which
# is the point: three warehouses preparing in parallel is the only way a split
# order finishes in the time one order should take.
#
# Not 0. Zero leaves no room to put something ahead of a split later, and the
# first time that is needed it would mean renumbering live orders.
SPLIT_PART_PRIORITY = 1


class RecycleOrder(models.Model):
    _name = 'recycle.order'
    _description = 'Customer Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority asc, id desc'

    name = fields.Char(
        string='Order Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'))
    customer_name = fields.Char(
        string='Factory Name', required=True, tracking=True)
    owner_name = fields.Char(
        string='Factory Owner Name', tracking=True)
    customer_email = fields.Char(string='Contact Email')
    backend_factory_id = fields.Char(
        string='Factory ID (Backend)', index=True, copy=False,
        help='External identifier of the factory/customer in the NestJS '
             'backend — used to correlate records during API synchronisation.')
    backend_part_id = fields.Char(
        string='Order Part ID (Backend)', index=True, copy=False,
        help='The backend order-part this order fulfils. A buyer order split '
             'across three warehouses becomes three orders here, one per '
             'warehouse, each carrying its own part id — that is what lets '
             'every decision taken here find its way back to the right piece '
             'of the buyer\'s order.')
    # ── Split orders ────────────────────────────────────────────────────
    # A buyer order that no single warehouse could fill is broken into parts,
    # and each part arrives here as its own order. These three fields are what
    # lets Odoo see them as ONE thing again.
    backend_order_id = fields.Char(
        string='Buyer Order ID (Backend)', index=True, copy=False,
        help='The buyer order these parts belong to. Parts sharing this id are '
             'one order and are approved together.')
    part_sequence = fields.Integer(
        string='Part No.', copy=False,
        help='Which piece of the buyer order this is — "part 2 of 3".')
    part_count = fields.Integer(
        string='Parts in Order', copy=False, default=1)
    is_split_part = fields.Boolean(
        string='Part of a Split Order', compute='_compute_is_split_part',
        store=True, index=True,
        help='True when the buyer order was spread over more than one '
             'warehouse. Split parts are approved by the administrator as one '
             'decision, not warehouse by warehouse.')

    @api.depends('part_count', 'backend_order_id')
    def _compute_is_split_part(self):
        for order in self:
            order.is_split_part = bool(
                order.backend_order_id and (order.part_count or 1) > 1)

    def sibling_parts(self):
        """Every order belonging to the same buyer order, including this one.

        Read with `sudo`: the parts sit in DIFFERENT warehouses, and the whole
        point is that one person decides for all of them — a record rule that
        scopes to the reader's own warehouse would return a "whole" that is
        only their piece, and the approval would silently cover one part while
        reporting that it covered the order.
        """
        self.ensure_one()
        if not self.backend_order_id:
            return self
        return self.sudo().search(
            [('backend_order_id', '=', self.backend_order_id)])
    warehouse_id = fields.Many2one(
        'recycle.warehouse', required=True, tracking=True, index=True)
    order_type = fields.Selection([
        ('factory', 'Factory'),
        ('free_facility', 'Free Facility'),
    ], string='Order Type', required=True, default='factory', tracking=True,
        help='Determines which product price tier to use for this order.')
    priority = fields.Integer(
        string='Priority', default=10, required=True, tracking=True,
        help='Lower number = higher priority. Orders are processed from lowest to highest.')
    line_ids = fields.One2many('recycle.order.line', 'order_id', string='Lines')
    state = fields.Selection(
        ORDER_STATES, default='pending', required=True, tracking=True, index=True)
    source = fields.Selection([
        ('manual', 'Manual'),
        ('nextjs', 'Next.js'),
    ], default='manual', required=True)
    amount_total = fields.Float(
        compute='_compute_amount_total', store=True, string='Total Amount')
    total_weight = fields.Float(
        compute='_compute_total_weight', store=True, string='Total Weight (kg)')

    # Delivery cost of the trip(s) fulfilling this order — read from the backend's
    # delivery trip by the shared order UUID. Not stored: the trip is pushed
    # separately and can arrive or change after the order, so it is computed live.
    delivery_cost = fields.Float(
        string='Delivery Cost', compute='_compute_delivery',
        help='Total delivery cost of this order\'s trip(s), from the backend. '
             'Zero when the order has no delivery trip.')
    delivery_currency = fields.Char(
        string='Delivery Currency', compute='_compute_delivery')
    has_delivery_cost = fields.Boolean(
        string='Has Delivery Cost', compute='_compute_delivery')
    output_user_id = fields.Many2one(
        'res.users', string='Processed By', readonly=True, copy=False, tracking=True)
    invoice_number = fields.Char(readonly=True, copy=False)
    output_zone_id = fields.Many2one(
        'recycle.zone', string='Output Zone', copy=False,
        domain="[('warehouse_id', '=', warehouse_id), ('zone_type', '=', 'output')]",
        help='Zone the goods were moved to for delivery. Set automatically '
             'when the order is completed.')
    invoice_date = fields.Date(readonly=True, copy=False)
    stock_deducted_at = fields.Datetime(
        string='Stock Deducted At', readonly=True, copy=False,
        help='When the warehouse stock was actually decremented for this '
             'order (at the "Complete" step, from the zones the output '
             'employee chose). See the Zone Movements for the per-line '
             'breakdown.')
    finished_at = fields.Datetime(
        string='Finished At', readonly=True, copy=False,
        help='When the output employee chose the output zone and clicked '
             'Finish — the true end of the order workflow.')
    zone_movement_ids = fields.One2many(
        'recycle.order.zone.movement', 'order_id', string='Zone Movements')
    recycle_archived = fields.Boolean(
        string='Archived', default=False, copy=False, index=True,
        help='Archived by the warehouse manager. Archived orders are only '
             'visible to the warehouse manager and the administrator.')
    recycle_archived_by = fields.Many2one(
        'res.users', string='Archived By', readonly=True, copy=False)
    # ── Warehouse-manager approval gate ──
    # Orders created through the external backend API land as 'pending'
    # and are invisible/unactionable to output employees until the
    # warehouse manager approves them. Manual orders (created by an admin
    # or manager in the system itself) are auto-approved so the internal
    # flow keeps working exactly as before.
    manager_approval = fields.Selection([
        ('approved', 'Approved'),
        ('pending', 'Pending Approval'),
        ('rejected', 'Rejected'),
    ], string='Manager Approval', default='approved', required=True,
        index=True, tracking=True, copy=False)
    approval_decided_by = fields.Many2one(
        'res.users', string='Approval Decided By', readonly=True, copy=False)
    approval_decided_at = fields.Datetime(
        string='Approval Decided At', readonly=True, copy=False)
    # ── Handover: the warehouse MANAGER's one step in the order ──
    # Preparation (pick, deduct, invoice, move to the output zone) belongs
    # entirely to the output employee. The manager's involvement begins only
    # when the goods physically LEAVE: handed to the carrier when the buyer
    # chose delivery, or to the buyer themselves when they collect.
    #
    # Kept separate from `state` on purpose: `state = completed` already means
    # "prepared and waiting in the output zone", and every existing screen,
    # domain and report treats it as such. Overloading it would quietly change
    # what "completed" means everywhere it is already read.
    handover_state = fields.Selection([
        ('pending', 'Awaiting Handover'),
        ('handed_over', 'Handed Over'),
    ], string='Handover', default='pending', required=True, index=True,
        tracking=True, copy=False,
        help='Whether the prepared goods have left the warehouse yet.')
    handover_type = fields.Selection([
        ('carrier', 'To Carrier (delivery)'),
        ('buyer', 'To Buyer (collected)'),
    ], string='Handed Over To', copy=False, tracking=True,
        help='Delivery orders go to a carrier; collection orders go straight '
             'to the buyer.')
    handover_by = fields.Many2one(
        'res.users', string='Handover Confirmed By', readonly=True, copy=False)
    handover_at = fields.Datetime(
        string='Handover Confirmed At', readonly=True, copy=False)
    handover_note = fields.Char(
        string='Handover Note', copy=False,
        help='Free text kept for the record — carrier name, plate, who signed.')
    # True once the backend allocator has promised this order's stock (see
    # recycle.stock.reserve_for_order). Kept on the order so the release is
    # idempotent: whatever ends the order — rejection, cancellation, or a
    # completed deduction — releases exactly once and never twice.
    stock_reserved = fields.Boolean(
        string='Stock Reserved', default=False, readonly=True, copy=False)
    approval_reject_reason = fields.Char(
        string='Rejection Reason', copy=False)

    def action_archive_recycle(self):
        if not self._is_supervisor():
            raise UserError(_('Only the warehouse manager or the administrator can archive orders.'))
        # Only a FINISHED order may be archived — one that has been completed or
        # cancelled. Archiving an order still being processed would hide live
        # work from the lists people fulfil it from.
        for rec in self:
            if rec.state not in ('completed', 'cancelled'):
                raise UserError(_(
                    'Order %s is not finished yet, so it cannot be archived. '
                    'Only completed or cancelled orders can be archived.'
                ) % rec.name)
        self.write({'recycle_archived': True,
                    'recycle_archived_by': self.env.user.id})
        for rec in self:
            rec.message_post(body=_('Order archived by %s.') % self.env.user.name)

    def action_unarchive_recycle(self):
        if not self._is_supervisor():
            raise UserError(_('Only the warehouse manager or the administrator can restore orders.'))
        self.write({'recycle_archived': False, 'recycle_archived_by': False})
        for rec in self:
            rec.message_post(body=_('Order restored from archive by %s.') % self.env.user.name)

    @api.depends('line_ids.subtotal')
    def _compute_amount_total(self):
        for order in self:
            order.amount_total = sum(order.line_ids.mapped('subtotal'))

    @api.depends('line_ids.quantity', 'line_ids.product_id.weight')
    def _compute_total_weight(self):
        for order in self:
            order.total_weight = sum(
                l.quantity * l.product_id.weight for l in order.line_ids
            )

    @api.depends('backend_order_id')
    def _compute_delivery(self):
        """Read the delivery cost from the backend's trip(s) for this order.

        Matched by the shared order UUID (`backend_order_id`). An order may be
        split across several trips, so the costs are summed. Zero (and no
        currency badge) when the order has no trip — which is the normal state
        for a collection order the buyer picks up themselves.
        """
        Trip = self.env['recycle.delivery.trip'].sudo()
        for order in self:
            trips = (
                Trip.search([('backend_order_id', '=', order.backend_order_id)])
                if order.backend_order_id else Trip.browse()
            )
            order.delivery_cost = sum(trips.mapped('delivery_cost'))
            order.delivery_currency = (
                trips[:1].currency_code or 'SYP') if trips else 'SYP'
            order.has_delivery_cost = bool(trips) and order.delivery_cost > 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].sudo().next_by_code(
                    'recycle.order') or _('New')
        return super().create(vals_list)

    # ---------------- Helpers ----------------

    def _is_supervisor(self):
        # Superuser mode (odoo shell, server actions, tests) bypasses the
        # group check, matching standard Odoo semantics.
        if self.env.su:
            return True
        user = self.env.user
        return (user.has_group('recycle_warehouse.group_recycle_admin')
                or user.has_group('recycle_warehouse.group_recycle_manager'))

    def _check_order_reservation(self):
        """Raise if the order is being processed by a different output employee."""
        for order in self:
            if (order.output_user_id
                    and order.output_user_id != self.env.user
                    and not self._is_supervisor()):
                raise UserError(_(
                    'This order is currently being processed by %s.'
                ) % order.output_user_id.name)

    def _line_stock_sufficient(self):
        """True if every line of this order has enough stock of its own
        condition right now. Orders lacking stock are skippable in the
        priority queue (see get_blocking_order)."""
        self.ensure_one()
        Stock = self.env['recycle.stock']
        return all(
            Stock._available_qty(self.warehouse_id, l.product_id,
                                  condition=l.condition) >= l.quantity
            for l in self.line_ids
        ) if self.line_ids else True

    @api.model
    def backend_upsert_part(self, payload):
        """Create (or find) the Odoo order for ONE part of a buyer's order.

        Keyed on `backend_part_id`, which makes the push idempotent: the
        backend may retry after a timeout without knowing whether the first
        attempt landed, and a duplicate order here would mean a warehouse
        preparing the same goods twice.

        Lands as `manager_approval = 'pending'` — the manager's acceptance is
        what the buyer's order is waiting on, so it must be an explicit
        decision, never a default.

        :param payload: {
            part_id, factory_id, customer_name, owner_name, customer_email,
            warehouse_odoo_id, order_type,
            lines: [{product_odoo_id, quantity, condition, price_unit}]
          }
        """
        part_id = (payload.get('part_id') or '').strip()
        if not part_id:
            raise UserError(_('The order part id is required.'))

        existing = self.sudo().search([('backend_part_id', '=', part_id)], limit=1)
        if existing:
            return {'odoo_id': existing.id, 'created': False}

        warehouse = self.env['recycle.warehouse'].sudo().browse(
            int(payload['warehouse_odoo_id']))
        if not warehouse.exists():
            raise UserError(_('Unknown warehouse for this order part.'))

        Product = self.env['recycle.product'].sudo()
        Conditions = self.env['recycle.material.condition']
        lines = []
        for row in payload.get('lines') or []:
            product = Product.browse(int(row['product_odoo_id']))
            if not product.exists():
                raise UserError(_(
                    'Unknown material %s in this order part.'
                ) % row.get('product_odoo_id'))
            # A material whose price list was withdrawn cannot be invoiced, so
            # it is refused at the door rather than at the invoice — after the
            # goods would already have been picked.
            product.assert_orderable()
            # Validated against THIS material, not coerced to a default. The
            # backend authors grade codes upper-case; the old code dropped an
            # unrecognised value onto 'good', which either invented a grade the
            # buyer never chose or — once codes stopped being one of four fixed
            # English words — failed the whole push and left the order stranded
            # with nobody told.
            condition = Conditions.normalize(product, row.get('condition'))
            lines.append((0, 0, {
                'product_id': product.id,
                'quantity': float(row['quantity']),
                'condition': condition,
                'price_unit': float(row.get('price_unit') or 0.0),
            }))
        if not lines:
            raise UserError(_('An order part cannot be empty.'))

        order = self.sudo().create({
            'backend_part_id': part_id,
            # What ties the parts of one buyer order together. Absent for an
            # order created inside Odoo, which is not a part of anything.
            'backend_order_id': (payload.get('order_id') or '').strip() or False,
            'part_sequence': int(payload.get('part_sequence') or 1),
            'part_count': int(payload.get('part_count') or 1),
            'backend_factory_id': payload.get('factory_id') or False,
            'customer_name': payload.get('customer_name') or _('Buyer'),
            'owner_name': payload.get('owner_name') or False,
            'customer_email': payload.get('customer_email') or False,
            'warehouse_id': warehouse.id,
            'order_type': payload.get('order_type') or 'factory',
            'source': 'nextjs',
            # A part of a SPLIT order jumps the output queue.
            #
            # The buyer is waiting on every warehouse at once, so the order
            # finishes when the SLOWEST part finishes. A part left behind an
            # ordinary single-warehouse order is not one part running late — it
            # holds the whole order, and the two warehouses that already
            # finished are storing prepared goods that cannot leave.
            #
            # `_order` is 'priority asc', and ordinary orders default to 10.
            'priority': SPLIT_PART_PRIORITY if int(
                payload.get('part_count') or 1) > 1 else 10,
            'manager_approval': 'pending',
            'line_ids': lines,
        })
        order.message_post(body=_(
            'Received from the backend as part of a buyer order. Awaiting the '
            'warehouse manager\'s decision.'))
        return {'odoo_id': order.id, 'created': True}

    @api.model
    def backend_cancel_part(self, part_id, reason=None):
        """The buyer cancelled before the goods were committed.

        Also WITHDRAWS a pending manager decision, so nobody accepts an order
        that no longer exists — the reservation is released on the way out.
        """
        order = self.sudo().search([('backend_part_id', '=', part_id)], limit=1)
        if not order:
            return {'cancelled': False, 'reason': 'not_found'}
        if order.state == 'completed':
            return {'cancelled': False, 'reason': 'already_completed'}
        order.action_cancel()
        order.message_post(body=_('Cancelled by the buyer. %s') % (reason or ''))
        return {'cancelled': True}

    def get_blocking_order(self):
        """Return the higher-priority PENDING order (lower priority number)
        in the same warehouse that must be processed before this one —
        empty recordset if none. Orders whose stock is currently
        insufficient are skipped: they cannot block anyone since they
        cannot be completed as-is (§ priority queue rule)."""
        self.ensure_one()
        candidates = self.search([
            ('warehouse_id', '=', self.warehouse_id.id),
            ('state', '=', 'pending'),
            # An order the manager hasn't approved (or rejected) can never
            # be processed, so it must never block the queue either.
            ('manager_approval', '=', 'approved'),
            ('priority', '<', self.priority),
            ('id', '!=', self.id),
        ], order='priority asc, id asc')
        for candidate in candidates:
            if candidate._line_stock_sufficient():
                return candidate
        return self.browse()

    def _notify_backend(self, event):
        """Tell the backend what just happened to this order.

        Every step a warehouse takes is something the buyer is waiting to see,
        so each one reports. Failure is swallowed deliberately: a warehouse
        employee's work must never be blocked because the backend is briefly
        unreachable.

        That trade only holds because something else picks the loss up. For a
        long time nothing did — this docstring claimed a reconcile pass re-read
        anything lost, and there was none. Fleet, warehouse, province and tariff
        data each had one; orders did not, so a single dropped call froze the
        buyer's order at whatever it last heard while the goods were invoiced
        and handed over, with nothing that would ever correct it.

        The pass now exists: OrderStateReconcileService in the backend re-reads
        every still-moving part from Odoo every 10 minutes and replays whatever
        it missed. Keep it in step — a new order event that this method reports
        must also be derivable from the order's fields there, or it becomes the
        next thing that can be lost silently.
        """
        self.ensure_one()
        try:
            self.env['recycle.backend.sync'].sudo().sync_order(self, event)
        except Exception:
            pass

    # ---------------- Stock reservation ----------------

    def _reservation_lines(self):
        """This order's lines in the shape recycle.stock speaks."""
        self.ensure_one()
        return [{
            'product_id': line.product_id.id,
            'condition': line.condition,
            'quantity': line.quantity,
        } for line in self.line_ids]

    def action_reserve_stock(self):
        """Promise this order's stock. Called by the backend allocator the
        moment a warehouse is chosen — BEFORE the manager is asked — because
        the gap between choosing and approving is exactly where two orders
        would otherwise be sold the same stock."""
        self.ensure_one()
        if self.stock_reserved:
            return {'reserved': True, 'already': True}
        result = self.env['recycle.stock'].sudo().reserve_for_order(
            self.warehouse_id.id, self._reservation_lines())
        if result.get('reserved'):
            self.sudo().stock_reserved = True
            self.message_post(body=_('Stock reserved for this order.'))
        return result

    def _release_stock(self, reason):
        """Give the promise back. Idempotent by the `stock_reserved` flag."""
        for order in self:
            if not order.stock_reserved:
                continue
            self.env['recycle.stock'].sudo().release_for_order(
                order.warehouse_id.id, order._reservation_lines())
            order.sudo().stock_reserved = False
            order.message_post(body=_('Reserved stock released (%s).') % reason)

    # ---------------- Workflow ----------------

    def _is_admin(self):
        return self.env.su or self.env.user.has_group(
            'recycle_warehouse.group_recycle_admin')

    def _assert_may_decide(self):
        """Who is allowed to approve or reject THIS order.

        A single-warehouse order is the warehouse manager's call — they own the
        floor it will be picked from.

        A SPLIT order is not. Its parts sit in different warehouses, and letting
        each manager decide their own piece means a buyer order can end up half
        approved and half rejected, with nobody answerable for the whole and the
        buyer waiting on a state no one intended. There is exactly one person
        who can see every part, so the decision is theirs: the administrator.
        """
        self.ensure_one()
        if self.is_split_part and not self._is_admin():
            raise UserError(_(
                'Order %(name)s is part %(seq)s of %(count)s of a split buyer '
                'order. Split orders are decided by the administrator for all '
                'their parts at once — a warehouse manager cannot approve or '
                'reject one piece on its own.'
            ) % {'name': self.name, 'seq': self.part_sequence or 1,
                 'count': self.part_count or 1})
        if not self._is_supervisor():
            raise UserError(_(
                'Only the warehouse manager or the administrator can decide '
                'orders.'))

    def action_manager_approve(self):
        """Release an API-created order to the output employees' queue.

        For a SPLIT order this approves EVERY part, in every warehouse, in one
        transaction. Approving them one at a time is the same failure the
        permission check above prevents, arriving by a different route: a buyer
        order is one promise, and half of it being released is not half a
        promise kept.
        """
        for order in self:
            order._assert_may_decide()
            targets = order.sibling_parts() if order.is_split_part else order

            blocked = targets.filtered(lambda o: o.state != 'pending')
            if blocked:
                raise UserError(_(
                    'Only orders that have not started processing can be '
                    'approved. Already started: %s'
                ) % ', '.join(blocked.mapped('name')))
            if all(o.manager_approval == 'approved' for o in targets):
                raise UserError(_('Order %s is already approved.') % order.name)

            for target in targets:
                if target.manager_approval == 'approved':
                    continue
                target.write({
                    'manager_approval': 'approved',
                    'approval_decided_by': self.env.user.id,
                    'approval_decided_at': fields.Datetime.now(),
                    'approval_reject_reason': False,
                })
                note = _('Order approved by %s — released to output employees.') \
                    % self.env.user.name
                if target.is_split_part:
                    note += ' ' + _(
                        'Approved as part %(seq)s of %(count)s of the buyer '
                        'order, together with its other parts.'
                    ) % {'seq': target.part_sequence or 1,
                         'count': target.part_count or 1}
                target.message_post(body=note)
                target._notify_backend('manager_approved')

    def action_manager_reject(self, reason=None):
        """Reject an order: it never appears to output employees.

        For a SPLIT order this rejects every part, releasing the stock each one
        was holding. Rejecting a single piece would leave the buyer with an
        order that can never complete while the other warehouses go on holding
        material reserved for it.
        """
        for order in self:
            order._assert_may_decide()
            targets = order.sibling_parts() if order.is_split_part else order

            blocked = targets.filtered(lambda o: o.state != 'pending')
            if blocked:
                raise UserError(_(
                    'Only orders that have not started processing can be '
                    'rejected. Already started: %s'
                ) % ', '.join(blocked.mapped('name')))
            if all(o.manager_approval == 'rejected' for o in targets):
                raise UserError(_('Order %s is already rejected.') % order.name)

            for target in targets:
                if target.manager_approval == 'rejected':
                    continue
                target.write({
                    'manager_approval': 'rejected',
                    'approval_decided_by': self.env.user.id,
                    'approval_decided_at': fields.Datetime.now(),
                    'approval_reject_reason': (reason or '').strip() or False,
                })
                target._release_stock(_('order rejected by the manager'))
                msg = _('Order rejected by %s.') % self.env.user.name
                if reason:
                    msg += ' %s' % _('Reason: %s') % reason
                if target.is_split_part:
                    msg += ' ' + _(
                        'Rejected as part %(seq)s of %(count)s of the buyer '
                        'order, together with its other parts.'
                    ) % {'seq': target.part_sequence or 1,
                         'count': target.part_count or 1}
                target.message_post(body=msg)
                target._notify_backend('manager_rejected')

    def action_admin_reassign_warehouse(self, new_warehouse_id):
        """Move ONE part of a split buyer order to a different warehouse.

        Deciding a split is the administrator's, and part of that decision is
        correcting a warehouse the allocator chose — a site that cannot prepare
        in time, say. Bounded on purpose, and every bound is a way this would
        otherwise go wrong:

          * only a SPLIT part, and only the administrator. A single-warehouse
            order is the manager's to accept or reject, never to relocate.
          * only BEFORE the decision (still pending). Once approved the goods
            are being prepared, and moving the order then would strand them.
          * the order is never GROWN. The allocator decided HOW MANY warehouses
            the order needs; the admin may change WHICH ones, not add another —
            so the target may not already hold a sibling, and the count stays.
          * the new warehouse must actually hold the quantity, checked against
            available (unreserved) stock — the same bar allocation used.

        The reservation travels with the part: released where it was, taken
        where it goes, so nothing is double-promised and nothing is left held
        for an order that moved on.
        """
        self.ensure_one()
        if not self._is_admin():
            raise UserError(_(
                'Only the administrator can reassign a split order part.'))
        if not self.is_split_part:
            raise UserError(_(
                'Only a part of a split order can be reassigned. A '
                'single-warehouse order is accepted or rejected by its '
                'manager, not relocated.'))
        if self.state != 'pending' or self.manager_approval != 'pending':
            raise UserError(_(
                'Only a part still awaiting the decision can be reassigned.'))

        new_wh = self.env['recycle.warehouse'].browse(int(new_warehouse_id))
        if not new_wh.exists():
            raise UserError(_('Unknown warehouse.'))
        if new_wh == self.warehouse_id:
            raise UserError(_('The part is already in that warehouse.'))
        others = self.sibling_parts() - self
        if new_wh in others.mapped('warehouse_id'):
            raise UserError(_(
                'Another part of this order is already assigned to that '
                'warehouse. A split may be re-routed but not merged.'))

        shortages = self.env['recycle.stock']._shortages(
            new_wh, self._reservation_lines())
        if shortages:
            raise UserError(_(
                'The chosen warehouse does not have enough available stock '
                'for this part.'))

        old_wh = self.warehouse_id
        # Release where it was, reserve where it goes — in that order, so the
        # stock is never counted as promised in two places at once.
        self._release_stock(_('reassigned to another warehouse'))
        self.warehouse_id = new_wh.id
        result = self.env['recycle.stock'].reserve_for_order(
            new_wh.id, self._reservation_lines())
        self.stock_reserved = bool(result.get('reserved'))
        self.message_post(body=_(
            'Reassigned from %(old)s to %(new)s by %(user)s.'
        ) % {'old': old_wh.name, 'new': new_wh.name,
             'user': self.env.user.name})
        self._notify_backend('reassigned')
        return True

    def action_start_processing(self):
        for order in self:
            if order.state != 'pending':
                raise UserError(_('Only pending orders can be processed.'))
            if order.manager_approval != 'approved':
                raise UserError(_(
                    'Order %s has not been approved by the warehouse manager yet.'
                ) % order.name)
            if not order.line_ids:
                raise UserError(_('Order has no lines.'))
            order._check_order_reservation()
            blocker = order.get_blocking_order()
            if blocker:
                raise UserError(_(
                    'Order %s has a higher priority and must be processed '
                    'first.'
                ) % blocker.name)
            order.write({
                'state': 'processing',
                'output_user_id': self.env.user.id,
            })
            order.message_post(body=_(
                'Processing started by %s. Order reserved.'
            ) % self.env.user.name)
            order._notify_backend('processing')

    def action_complete(self, allocations=None):
        """Deduct stock from the SPECIFIC zones the output employee chose,
        log a zone-movement record per allocation (with a timestamp — this
        is when stock actually leaves the warehouse for this order), and
        generate the invoice. Moves processing -> ready; the order still
        needs an output zone (action_finish) to reach 'completed'.

        :param allocations: list of dicts, one per (line, zone) pick:
            {'line_id': int, 'zone_id': int, 'quantity': float}
            Every line's allocations must sum to exactly its required
            quantity — validated here again even though the controller
            already checked, since this is the authoritative deduction.
        """
        Stock = self.env['recycle.stock']
        Movement = self.env['recycle.order.zone.movement']
        allocations = allocations or []
        for order in self:
            if order.state != 'processing':
                raise UserError(_('Only processing orders can be completed.'))
            order._check_order_reservation()

            by_line = {}
            for alloc in allocations:
                by_line.setdefault(alloc['line_id'], []).append(alloc)

            for line in order.line_ids:
                line_allocs = by_line.get(line.id, [])
                allocated_qty = sum(a['quantity'] for a in line_allocs)
                # Tolerate float rounding noise.
                if allocated_qty < line.quantity - 0.0001:
                    raise UserError(_(
                        'Storage zone allocation for "%(product)s" only '
                        'covers %(alloc)s of the %(need)s required — choose '
                        'more storage zones or larger quantities.') % {
                            'product': line.product_id.name,
                            'alloc': round(allocated_qty, 2),
                            'need': line.quantity})
                for alloc in line_allocs:
                    zone = self.env['recycle.zone'].browse(alloc['zone_id'])
                    qty = alloc['quantity']
                    if qty <= 0:
                        continue
                    Stock._deduct_from_zone(
                        order.warehouse_id, line.product_id, zone, qty,
                        condition=line.condition)
                    Movement.create({
                        'order_id': order.id,
                        'line_id': line.id,
                        'zone_id': zone.id,
                        'product_id': line.product_id.id,
                        'condition': line.condition,
                        'quantity': qty,
                        'moved_by': self.env.user.id,
                    })

            # The promise has now become a real deduction: release it so the
            # same quantity is not subtracted twice from what others can take.
            order._release_stock(_('stock deducted'))
            order.write({
                'state': 'ready',
                'stock_deducted_at': fields.Datetime.now(),
                'invoice_number': self.env['ir.sequence'].sudo().next_by_code(
                    'recycle.invoice'),
                'invoice_date': fields.Date.context_today(order),
            })
            order.message_post(body=_(
                'Order completed by %s. Stock deducted from the chosen '
                'storage zones, invoice %s generated. Waiting for an '
                'output zone to finish.'
            ) % (self.env.user.name, order.invoice_number))
            order._notify_backend('stock_deducted')
            # Stock just LEFT. The allocator decides from the backend's mirror of
            # these quantities, so without this ping it keeps offering goods that
            # have already been picked — and the error surfaces as a failed order
            # for the next buyer rather than as a number on a screen.
            try:
                self.env['recycle.backend.sync'].sudo().notify_inventory_changed(
                    order.warehouse_id)
            except Exception:
                pass

    def action_finish(self, output_zone_id):
        """Last step of PREPARATION, done by the output employee.

        The output employee owns the whole physical job: taking the order,
        deducting the stock, generating the invoice, and moving the goods to an
        output zone. The manager does not take part in any of it — their one
        involvement comes afterwards, at `action_confirm_handover`, when the
        goods actually leave the warehouse.

        Reaching 'completed' therefore means "prepared and waiting in the output
        zone", not "gone".
        """
        zone = self.env['recycle.zone'].browse(output_zone_id)
        for order in self:
            if order.state != 'ready':
                raise UserError(_(
                    'Only orders that have completed stock deduction can be finished.'))
            order._check_order_reservation()
            if not zone.exists() or zone.warehouse_id != order.warehouse_id \
                    or zone.zone_type != 'output':
                raise UserError(_(
                    'Choose a valid output zone of this warehouse.'))
            order.write({
                'state': 'completed',
                'output_zone_id': zone.id,
                'finished_at': fields.Datetime.now(),
            })
            order.message_post(body=_(
                'Order finished by %s. Goods moved to output zone "%s".'
            ) % (self.env.user.name, zone.name))
            try:
                self.env['recycle.notification'].sudo()._notify_admins(
                    _('Order completed'),
                    _('Order %s was processed and completed in warehouse %s '
                      '(invoice %s).') % (
                        order.name, order.warehouse_id.name,
                        order.invoice_number),
                    notif_type='order',
                    related_model='recycle.order', related_res_id=order.id)
            except Exception:
                pass
            order._notify_backend('completed')

    def action_confirm_handover(self, handover_type, note=None):
        """The warehouse MANAGER confirms the goods physically left.

        This is the manager's only step in an order. Everything before it — the
        picking, the deduction, the invoice, the move to the output zone — is
        the output employee's work, and the manager takes no part in it.

        Two destinations, and the difference is what the buyer's app shows next:
          'carrier' → the buyer chose delivery; the order becomes "on the way".
          'buyer'   → the buyer collected it; this part is delivered.

        Why the manager and not the output employee: this is the moment
        responsibility for the goods leaves the warehouse. The person who
        prepared them should not also be the sole record that they left — and
        for a split order it is the per-warehouse fact the buyer's status is
        assembled from.

        :param handover_type: 'carrier' or 'buyer'
        :param note: carrier name / plate / who signed — free text, kept.
        """
        if handover_type not in ('carrier', 'buyer'):
            raise UserError(_(
                'Say whether the order went to a carrier or to the buyer.'))
        for order in self:
            if not order._is_supervisor():
                raise UserError(_(
                    'Only the warehouse manager or the administrator can '
                    'confirm that an order was handed over.'))
            if order.state != 'completed':
                raise UserError(_(
                    'Order %s has not been prepared and moved to an output '
                    'zone yet.') % order.name)
            if order.handover_state == 'handed_over':
                raise UserError(_(
                    'Order %s was already handed over.') % order.name)
            order.write({
                'handover_state': 'handed_over',
                'handover_type': handover_type,
                'handover_by': self.env.user.id,
                'handover_at': fields.Datetime.now(),
                'handover_note': (note or '').strip() or False,
            })
            label = _('the carrier') if handover_type == 'carrier' else _('the buyer')
            order.message_post(body=_(
                'Handover confirmed by %(user)s — goods released to %(to)s.%(note)s'
            ) % {
                'user': self.env.user.name,
                'to': label,
                'note': (' %s' % note) if note else '',
            })
            # Moves the buyer-facing status on: "on the way" for a delivery,
            # "delivered" for a collection.
            order._notify_backend('handed_over')
        return True

    # Odoo form buttons cannot pass arguments, so each destination gets its own
    # entry point. Two named buttons also read better to the manager than one
    # button plus a dialog asking where the goods went.
    def action_handover_to_carrier(self):
        """Delivery order: the goods were loaded for transport to the buyer."""
        return self.action_confirm_handover('carrier')

    def action_handover_to_buyer(self):
        """Collection order: the buyer took the goods from the output zone."""
        return self.action_confirm_handover('buyer')

    def action_release_order(self):
        """Output employee releases a reserved order so a colleague can take it."""
        for order in self:
            if order.state != 'processing':
                raise UserError(_('Only processing orders can be released.'))
            order._check_order_reservation()
            order.write({'state': 'pending', 'output_user_id': False})
            order.message_post(body=_(
                'Order released by %s and is available again.'
            ) % self.env.user.name)

    def action_cancel(self):
        for order in self:
            if order.state == 'completed':
                raise UserError(_('Completed orders cannot be cancelled.'))
            order._release_stock(_('order cancelled'))
            order.state = 'cancelled'

    def action_print_invoice(self):
        """Generate the invoice PDF server-side with sudo so that
        output employees (who cannot access base.document.layout)
        can still download their invoices without an Access Error."""
        self.ensure_one()
        if not self.invoice_number:
            raise UserError(_('No invoice has been generated for this order yet.'))

        # Render PDF with elevated privileges — Odoo 19's report pipeline
        # always reads base.document.layout regardless of the template used.
        pdf_content, _ = self.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'recycle_warehouse.report_order_invoice',
            res_ids=self.ids,
        )

        filename = 'Invoice-%s.pdf' % (self.invoice_number or self.name)

        # Store as an attachment linked to this order (visible in the chatter)
        attachment = self.env['ir.attachment'].sudo().create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(pdf_content).decode('utf-8'),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%d/%s?download=true' % (attachment.id, filename),
            'target': 'new',
        }


class RecycleOrderLine(models.Model):
    _name = 'recycle.order.line'
    _inherit = ['recycle.grade.mixin']
    _description = 'Customer Order Line'

    order_id = fields.Many2one('recycle.order', required=True, ondelete='cascade')
    product_id = fields.Many2one(
        'recycle.product', required=True, ondelete='restrict')
    quantity = fields.Float(required=True, default=1.0)
    condition = fields.Char(
        string='Grade', size=30,
        help='Grade the customer ordered, as authored in the backend. Empty '
             'when the material is ungraded. Completing the order deducts '
             'stock of this exact grade only — stock of another grade is never '
             'consumed for this line.')
    condition_label = fields.Char(
        string='Grade Name', compute='_compute_condition_label')

    @api.depends('product_id', 'condition')
    def _compute_condition_label(self):
        Conditions = self.env['recycle.material.condition']
        for line in self:
            line.condition_label = Conditions.label_for(
                line.product_id, line.condition)

    @api.constrains('product_id', 'condition')
    def _check_condition(self):
        """The ordered grade must be one this material actually has.

        Enforced on the line rather than only at the door, because an order can
        be built by hand inside Odoo as well as pushed by the backend, and a
        line carrying a grade the material does not have can never be filled
        from stock — the shortage would only appear when the output employee
        tried to pick it.
        """
        Conditions = self.env['recycle.material.condition']
        for line in self:
            if not line.product_id:
                continue
            Conditions.normalize(line.product_id, line.condition)
    price_unit = fields.Float(string='Unit Price')
    subtotal = fields.Float(compute='_compute_subtotal', store=True)
    stock_qty = fields.Float(
        string='In Stock', compute='_compute_stock_qty',
        help='Quantity available in the warehouse stock for this product '
             'in the requested condition.')

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit

    @api.depends('product_id', 'condition', 'order_id.warehouse_id')
    def _compute_stock_qty(self):
        Stock = self.env['recycle.stock']
        for line in self:
            if line.product_id and line.order_id.warehouse_id:
                line.stock_qty = Stock._available_qty(
                    line.order_id.warehouse_id, line.product_id,
                    condition=line.condition)
            else:
                line.stock_qty = 0.0

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                order = line.order_id
                if order.order_type == 'factory':
                    line.price_unit = line.product_id.price_factory
                else:
                    line.price_unit = line.product_id.price_free_facility

    def recalculate_prices(self):
        """Recalculate all line prices based on the order's order_type."""
        for line in self:
            product = line.product_id
            if not product:
                continue
            order = line.order_id
            if order.order_type == 'factory':
                line.price_unit = product.price_factory
            else:
                line.price_unit = product.price_free_facility

    @api.onchange('quantity', 'product_id', 'condition')
    def _onchange_check_stock(self):
        if not self.product_id or not self.quantity:
            return
        warehouse = self.order_id.warehouse_id
        if not warehouse:
            return
        available = self.env['recycle.stock']._available_qty(
            warehouse, self.product_id, condition=self.condition)
        if self.quantity > available:
            label = self.env['recycle.material.condition'].label_for(
                self.product_id, self.condition)
            return {
                'warning': {
                    'title': _('⚠ Insufficient Stock'),
                    'message': _(
                        'Product:  %s\n'
                        'Condition:  %s\n'
                        'Requested:  %.2f units\n'
                        'Available in "%s" (this condition only):  %.2f units\n\n'
                        'The requested quantity exceeds available stock of '
                        'this condition. Stock of other conditions cannot be '
                        'used for this line.'
                    ) % (
                        self.product_id.name,
                        label,
                        self.quantity,
                        warehouse.name,
                        available,
                    ),
                }
            }

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('Order line quantity must be positive.'))


class RecycleOrderZoneMovement(models.Model):
    _name = 'recycle.order.zone.movement'
    _inherit = ['recycle.grade.mixin']
    _description = 'Order Stock Deduction Log (per storage zone)'
    _order = 'moved_at desc, id desc'

    order_id = fields.Many2one(
        'recycle.order', required=True, ondelete='cascade', index=True)
    line_id = fields.Many2one(
        'recycle.order.line', required=True, ondelete='cascade')
    zone_id = fields.Many2one(
        'recycle.zone', string='Storage Zone', required=True)
    product_id = fields.Many2one('recycle.product', required=True)
    condition = fields.Char(
        string='Grade', size=30,
        help='Grade actually taken off the shelf. Empty for an ungraded '
             'material — this log records what left, and for such a material '
             'there is no grade that left.')
    quantity = fields.Float(required=True)
    moved_by = fields.Many2one('res.users', string='Deducted By', required=True)
    moved_at = fields.Datetime(
        string='Deducted At', required=True, default=fields.Datetime.now)
