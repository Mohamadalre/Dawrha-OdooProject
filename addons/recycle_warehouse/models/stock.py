# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

# Grades are NOT a module-wide vocabulary any more.
#
# There used to be one hard-coded list of four English words here, shared by
# stock lines, sorted shipment lines, order lines and damage reports. It could
# not answer the only question that matters — does THIS material have grades,
# and which ones? — so a material the admin never graded still offered four, and
# a material whose grades the admin named PREMIUM/STANDARD could never hold
# stock at all. Worse, the backend authors codes upper-case, so every order it
# pushed carried 'GOOD' into a field that only accepted 'good' and was rejected
# outright.
#
# Grades now live on `recycle.material.condition`, keyed by material and
# mirrored from the backend where the admin authors them. Ask that model:
#
#   env['recycle.material.condition'].codes_for(product)   -> ['EXCELLENT', ...]
#   env['recycle.material.condition'].normalize(product, code)
#   env['recycle.material.condition'].label_for(product, code)
#
# An empty list is a real answer: that material is ungraded, and its quantities
# carry no grade at all.


def _conditions(env):
    """Shorthand for the grade registry — one import site, one spelling."""
    return env['recycle.material.condition']


class RecycleStock(models.Model):
    _name = 'recycle.stock'
    _inherit = ['recycle.grade.mixin']
    _description = 'Warehouse Stock'
    _rec_name = 'product_id'
    _order = 'warehouse_id, product_id'

    warehouse_id = fields.Many2one(
        'recycle.warehouse', required=True, ondelete='cascade', index=True)
    product_id = fields.Many2one(
        'recycle.product', required=True, ondelete='restrict', index=True)
    quantity = fields.Float(string='Quantity', default=0.0)
    # Quantity promised to an order that has been allocated but not yet
    # deducted. Without it, two orders allocated seconds apart can both be
    # promised the same stock and the shortage only surfaces when the output
    # employee tries to deduct — i.e. AFTER the customer was told yes.
    reserved_qty = fields.Float(
        string='Reserved', default=0.0, readonly=True, copy=False,
        help='Promised to allocated orders and not deductible by anyone else. '
             'Released when the order is rejected, cancelled or expires, and '
             'converted into a real deduction when the order is completed.')
    available_qty = fields.Float(
        string='Available', compute='_compute_available_qty', store=True,
        help='quantity − reserved_qty: what a new order may actually take.')
    zone_id = fields.Many2one(
        'recycle.zone', string='Storage Zone', index=True, ondelete='set null',
        domain="[('warehouse_id', '=', warehouse_id)]",
        help='Zone inside the warehouse where this stock is physically kept.')
    condition = fields.Char(
        string='Grade', index=True, size=30,
        help="Grade code of this material, as authored in the backend (e.g. "
             "EXCELLENT). EMPTY means either that the material is ungraded, or "
             "that this quantity has not been sorted yet — both are real "
             "states, and neither is a grade.")
    condition_label = fields.Char(
        string='Grade Name', compute='_compute_condition_label',
        help='Human name of the grade for THIS material.')

    @api.depends('product_id', 'condition')
    def _compute_condition_label(self):
        for rec in self:
            rec.condition_label = _conditions(self.env).label_for(
                rec.product_id, rec.condition)

    @api.constrains('product_id', 'condition')
    def _check_condition_belongs_to_product(self):
        """A stock row may only carry a grade its own material actually has.

        Left unchecked, a row could sit under a grade nobody sells it at: no
        order would ever match it, so the quantity would be invisible to the
        allocator while still counting as stock on every report.
        """
        Conditions = _conditions(self.env)
        for rec in self:
            if not rec.condition:
                continue  # unsorted or ungraded — both legitimate
            Conditions.normalize(rec.product_id, rec.condition)

    @api.depends('quantity', 'reserved_qty')
    def _compute_available_qty(self):
        for rec in self:
            rec.available_qty = max(rec.quantity - rec.reserved_qty, 0.0)

    @api.constrains('warehouse_id', 'product_id', 'zone_id', 'condition')
    def _check_unique_line(self):
        for rec in self:
            if self.sudo().search_count([
                    ('warehouse_id', '=', rec.warehouse_id.id),
                    ('product_id', '=', rec.product_id.id),
                    ('zone_id', '=', rec.zone_id.id),
                    ('condition', '=', rec.condition),
                    ('id', '!=', rec.id)]):
                raise ValidationError(
                    _('A stock line for this product/zone/condition already '
                      'exists in this warehouse.'))

    @api.constrains('quantity')
    def _check_quantity(self):
        for rec in self:
            if rec.quantity < 0:
                raise ValidationError(_('Stock quantity cannot be negative.'))

    # ------------------------------------------------------------------
    # The backend mirrors these quantities. It learns from HERE.
    # ------------------------------------------------------------------
    # The pings used to hang off individual workflows — order.py, shipment.py
    # and stock_damage_report.py each called `notify_inventory_changed` by hand.
    # Every other path that moved stock told nobody: a reservation, a release, a
    # direct correction, a deduction reached from anywhere else. So the mirror
    # was right after the three flows somebody had remembered to wire and
    # quietly wrong after everything else — the "the API keeps its old number
    # until I call sync" symptom.
    #
    # The rows themselves are the one thing every quantity change must pass
    # through, so the announcement belongs to them and not to the callers. A
    # caller cannot forget what it does not have to remember.
    #
    # `schedule_ping` collapses the burst: a sorting run writing forty rows
    # produces ONE ping per warehouse, sent after the transaction commits.
    #
    # No field filter here, unlike `recycle.warehouse`. Every writable field on
    # this model — quantity, reserved_qty, condition, product, warehouse, zone —
    # is one the backend mirrors, so a list would name all of them and read as
    # if it excluded something. And the failure this whole file exists to
    # prevent is a field somebody forgot to add to exactly such a list: with a
    # de-duplicated ping costing one round trip per transaction, announcing too
    # often is the cheaper mistake.
    def _announce_stock_change(self):
        Sync = self.env['recycle.backend.sync'].sudo()
        for warehouse in self.mapped('warehouse_id'):
            Sync.schedule_ping('inventory', warehouse)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._announce_stock_change()
        return records

    def write(self, vals):
        was_positive = {}
        if 'quantity' in vals:
            was_positive = {rec.id: rec.quantity > 0 for rec in self}
        # Read BEFORE the write: a row moved to another warehouse leaves the old
        # one holding a different total, and after `super()` the old warehouse
        # is no longer reachable from the record.
        touched = self.mapped('warehouse_id') if 'warehouse_id' in vals \
            else self.env['recycle.warehouse']
        res = super().write(vals)
        if 'quantity' in vals:
            for rec in self:
                if was_positive.get(rec.id) and rec.quantity <= 0:
                    rec._notify_zero_stock()
        Sync = self.env['recycle.backend.sync'].sudo()
        for warehouse in touched | self.mapped('warehouse_id'):
            Sync.schedule_ping('inventory', warehouse)
        return res

    def unlink(self):
        """A removed row is a quantity that went to zero — the mirror must hear
        about it, and after `super()` there is nothing left to ask."""
        warehouses = self.mapped('warehouse_id')
        res = super().unlink()
        Sync = self.env['recycle.backend.sync'].sudo()
        for warehouse in warehouses:
            Sync.schedule_ping('inventory', warehouse)
        return res

    def _notify_zero_stock(self):
        """Warn the warehouse manager that this product just ran out."""
        self.ensure_one()
        manager = self.warehouse_id.manager_user_id
        if not manager:
            return
        self.env['recycle.notification'].sudo()._notify_user(
            manager,
            _('Stock Depleted'),
            _('%(product)s is now out of stock in warehouse %(wh)s.') % {
                'product': self.product_id.name or '',
                'wh': self.warehouse_id.name or '',
            },
            notif_type='stock_empty',
        )

    @api.model
    def _default_storage_zone(self, warehouse):
        return warehouse.zone_ids.filtered(
            lambda z: z.zone_type == 'storage')[:1]

    @api.model
    def _add_quantity(self, warehouse, product, qty, condition=None, zone=None):
        """Add stock, tracked per storage zone and per grade.

        The grade is validated against THIS material rather than coerced to a
        default. The old behaviour silently rewrote anything unrecognised to
        'good', which meant a typo or a stale code did not fail — it quietly
        filed the quantity under a grade the sorter never chose.
        """
        if qty <= 0:
            return
        condition = _conditions(self.env).normalize_optional(product, condition)
        zone = zone or self._default_storage_zone(warehouse)
        line = self.search([
            ('warehouse_id', '=', warehouse.id),
            ('product_id', '=', product.id),
            ('zone_id', '=', zone.id if zone else False),
            ('condition', '=', condition)], limit=1)
        if line:
            line.quantity += qty
        else:
            self.create({
                'warehouse_id': warehouse.id,
                'product_id': product.id,
                'zone_id': zone.id if zone else False,
                'condition': condition,
                'quantity': qty,
            })

    @api.model
    def _available_qty(self, warehouse, product, condition=None):
        """Total available quantity of a product in a warehouse.

        Available means quantity MINUS what is already promised to allocated
        orders — never the raw quantity, or two orders would be sold the same
        stock. With ``condition`` set, only lines of that exact condition count
        — this is what order processing must use so that e.g. an 'excellent'
        order line can never consume 'good' stock."""
        return sum(
            self.search(self._stock_domain(warehouse, product, condition))
                .mapped('available_qty'))

    @api.model
    def _stock_domain(self, warehouse, product, condition=None):
        domain = [
            ('warehouse_id', '=', warehouse.id),
            ('product_id', '=', product.id),
        ]
        if condition:
            domain.append(('condition', '=', condition))
        return domain

    # ------------------------------------------------------------------
    # Reservation (called by the backend allocator over RPC)
    # ------------------------------------------------------------------
    @api.model
    def reserve_for_order(self, warehouse_id, lines):
        """Promise `lines` to an order, all-or-nothing.

        `lines`: [{'product_id': int, 'condition': str, 'quantity': float}]
        Returns {'reserved': True} or {'reserved': False, 'shortages': [...]}.

        All-or-nothing matters: a partially reserved order would hold stock it
        can never use while blocking someone who could. The whole call runs in
        one transaction, so a raised error rolls the partial work back.
        """
        warehouse = self.env['recycle.warehouse'].browse(warehouse_id)
        if not warehouse.exists():
            raise UserError(_('Unknown warehouse.'))

        shortages = self._shortages(warehouse, lines)
        if shortages:
            return {'reserved': False, 'shortages': shortages}

        for line in lines:
            self._apply_reservation(
                warehouse, line, sign=1)
        return {'reserved': True}

    @api.model
    def release_for_order(self, warehouse_id, lines):
        """Give back stock promised to an order that was rejected, cancelled or
        expired. Never raises on an over-release: a reservation released twice
        (retried job, manual admin fix) must not block the caller — the floor at
        zero keeps the number honest either way."""
        warehouse = self.env['recycle.warehouse'].browse(warehouse_id)
        if not warehouse.exists():
            return {'released': False}
        for line in lines:
            self._apply_reservation(warehouse, line, sign=-1)
        return {'released': True}

    @api.model
    def _shortages(self, warehouse, lines):
        """Lines the warehouse cannot cover right now, with the numbers."""
        Product = self.env['recycle.product']
        shortages = []
        for line in lines:
            product = Product.browse(int(line['product_id']))
            available = self._available_qty(
                warehouse, product, condition=line.get('condition'))
            required = float(line['quantity'])
            if available < required - 0.0001:
                shortages.append({
                    'product_id': product.id,
                    'condition': line.get('condition'),
                    'required': required,
                    'available': available,
                })
        return shortages

    @api.model
    def _apply_reservation(self, warehouse, line, sign):
        """Move `sign * quantity` of one line into/out of reservation, spread
        over the matching stock rows in order. One loop, no nesting: each row
        takes as much as it can and the remainder moves to the next."""
        Product = self.env['recycle.product']
        product = Product.browse(int(line['product_id']))
        remaining = float(line['quantity'])
        rows = self.sudo().search(
            self._stock_domain(warehouse, product, line.get('condition')))
        for row in rows:
            if remaining <= 0.0001:
                break
            headroom = row.available_qty if sign > 0 else row.reserved_qty
            take = min(remaining, headroom)
            if take <= 0:
                continue
            row.reserved_qty = max(row.reserved_qty + sign * take, 0.0)
            remaining -= take

    # ------------------------------------------------------------------
    # Re-grading (called by the backend admin over RPC)
    # ------------------------------------------------------------------
    @api.model
    def transfer_grade(self, warehouse_id, product_id, from_condition,
                       to_condition, quantity):
        """Move UNRESERVED stock of one material from one grade to another,
        keeping the warehouse total unchanged.

        A re-inspection changes the answer: material graded GOOD on arrival
        turns out to be EXCELLENT. The admin triggers this from the backend, but
        the move must happen HERE — the backend only mirrors quantities, so a
        move it made on its own side was overwritten by the next inventory sync
        and silently reverted. Odoo owns the number; the mirror follows the
        inventory ping this write fires.

        Total-neutral by construction: every unit removed from a `from` row is
        added to a `to` row in the SAME zone, so the building holds exactly as
        much as before — only labelled differently.

        Only AVAILABLE (unreserved) quantity moves. Reserved stock is promised
        to an order that has not shipped; re-labelling it would leave that order
        pointing at a grade its goods are no longer in, and the shortage would
        surface at deduction time — after the buyer was told yes.

        Returns {'transferred': True, 'moved': qty} on success, or
        {'transferred': False, 'movable': x, 'requested': qty} when the
        unreserved stock cannot cover the request (a race with another
        movement since the admin looked — the backend pre-checks its mirror,
        but Odoo is the authority).
        """
        warehouse = self.env['recycle.warehouse'].browse(int(warehouse_id))
        product = self.env['recycle.product'].browse(int(product_id))
        if not warehouse.exists() or not product.exists():
            raise UserError(_('Unknown warehouse or product.'))

        Conditions = _conditions(self.env)
        # Validates each grade belongs to THIS material — a code is unique only
        # within its material, so 'GOOD' names a different thing per product.
        from_code = Conditions.normalize(product, from_condition)
        to_code = Conditions.normalize(product, to_condition)
        if from_code == to_code:
            raise UserError(
                _('Source and destination grades are the same.'))
        qty = float(quantity)
        if qty <= 0:
            raise UserError(_('Transfer quantity must be positive.'))

        from_rows = self.sudo().search(
            self._stock_domain(warehouse, product, from_code))
        movable = sum(from_rows.mapped('available_qty'))
        if movable < qty - 0.0001:
            return {
                'transferred': False,
                'movable': movable,
                'requested': qty,
            }

        remaining = qty
        for row in from_rows:
            if remaining <= 0.0001:
                break
            take = min(remaining, row.available_qty)
            if take <= 0:
                continue
            # The from-grade shrinks; its reservation is left exactly where it
            # was, so available_qty can never fall below zero.
            row.quantity -= take
            # The destination is the SAME physical zone, re-graded — so the
            # material does not move, only its label does.
            dest = self.sudo().search([
                ('warehouse_id', '=', warehouse.id),
                ('product_id', '=', product.id),
                ('zone_id', '=', row.zone_id.id if row.zone_id else False),
                ('condition', '=', to_code)], limit=1)
            if dest:
                dest.quantity += take
            else:
                self.sudo().create({
                    'warehouse_id': warehouse.id,
                    'product_id': product.id,
                    'zone_id': row.zone_id.id if row.zone_id else False,
                    'condition': to_code,
                    'quantity': take,
                })
            remaining -= take

        # The source rows are LEFT even at zero: an empty grade is still one the
        # material is sold at, and removing it would change the price sheet and
        # every sorting screen. `write` already scheduled the inventory ping.
        return {'transferred': True, 'moved': qty}

    @api.model
    def _order_by_grade(self, product, lines):
        """Stock rows sorted by the MATERIAL'S OWN grade ranking, best first.

        Ordering by the code string would be alphabetical — DAMAGED before
        EXCELLENT — so a bulk deduction would eat the worst grade first on some
        materials and the best on others, depending on nothing but spelling.
        """
        Conditions = _conditions(self.env)
        return lines.sorted(
            key=lambda l: (Conditions.rank_for(product, l.condition), l.id))

    @api.model
    def _deduct_from_zone(self, warehouse, product, zone, qty, condition):
        """Deduct EXACTLY from one (warehouse, zone, product, condition)
        stock line — used by order completion, where the output employee
        picks specific storage zones to fulfill the order from. Raises if
        that exact line doesn't have enough."""
        if qty <= 0:
            return
        line = self.search([
            ('warehouse_id', '=', warehouse.id),
            ('product_id', '=', product.id),
            ('zone_id', '=', zone.id),
            ('condition', '=', condition),
        ], limit=1)
        available = line.quantity if line else 0.0
        if available < qty - 0.0001:
            raise UserError(_(
                'Not enough stock of "%(product)s" in zone "%(zone)s" '
                '(%(cond)s). Available: %(avail)s, required: %(req)s.'
            ) % {
                'product': product.name, 'zone': zone.name,
                'cond': _conditions(self.env).label_for(product, condition),
                'avail': available, 'req': qty})
        line.quantity -= qty

    @api.model
    def _deduct_quantity(self, warehouse, product, qty, condition=None):
        """Deduct stock of a product.

        - ``condition`` given (order lines, damage reports): deduct ONLY from
          lines of that exact grade. Stock of any other grade is untouchable —
          if the matching-grade stock is insufficient the whole operation fails
          with an explicit error naming the grade.
        - ``condition`` omitted: the material is ungraded (or the caller means
          "any"), and lines are consumed best grade first.
        """
        if qty <= 0:
            return
        domain = [
            ('warehouse_id', '=', warehouse.id),
            ('product_id', '=', product.id),
        ]
        if condition:
            condition = _conditions(self.env).normalize(product, condition)
            domain.append(('condition', '=', condition))
        # Best grade first: `sort_order` is the material's own ranking, so the
        # ordering has to come from the grade table rather than from the code
        # string, which sorts alphabetically and would consume DAMAGED before
        # EXCELLENT.
        lines = self._order_by_grade(product, self.search(domain))
        available = sum(lines.mapped('quantity'))
        if available < qty:
            if condition:
                label = _conditions(self.env).label_for(product, condition)
                raise UserError(_(
                    'Not enough "%(cond)s" stock of "%(product)s" in warehouse '
                    '"%(wh)s". Available in this condition: %(avail)s, '
                    'required: %(req)s. Stock of other conditions cannot be '
                    'used for this order line.') % {
                        'cond': label, 'product': product.name,
                        'wh': warehouse.name, 'avail': available, 'req': qty})
            raise UserError(_(
                'Not enough stock of "%s" in warehouse "%s". Available: %s, required: %s.'
            ) % (product.name, warehouse.name, available, qty))
        remaining = qty
        for line in lines:
            take = min(line.quantity, remaining)
            line.quantity -= take
            remaining -= take
            if remaining <= 0:
                break
