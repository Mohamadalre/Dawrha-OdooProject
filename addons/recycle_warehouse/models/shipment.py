# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


SHIPMENT_STATES = [
    ('pending', 'Pending'),
    ('receiving', 'In Reception'),
    ('escalated', 'Transferred to Manager'),
    ('accepted', 'Accepted'),
    ('sorting', 'Sorting'),
    ('pending_sorting_approval', 'Pending Sorting Approval'),
    ('sorted', 'Sorted'),
    ('rejected', 'Rejected (legacy)'),
]

WEIGHT_TOLERANCE = 5.0    # percent — warning band starts here (default)
WEIGHT_HARD_LIMIT = 10.0  # percent — transfer-to-manager limit (default)
DAMAGE_LIMIT = 40.0       # percent — manager damage approval (default)
SORT_TOLERANCE_THRESHOLD_1 = 3.0   # percent — per-material shortage auto-accepted (default)
SORT_TOLERANCE_THRESHOLD_2 = 15.0  # percent — per-material shortage ceiling before
                                    # manager approval is required (default)


def _pct_param(env, key, default):
    """Admin-configurable percentage (System Parameters). The admin edits
    these from Dashboard → Settings — nothing is hard-coded."""
    try:
        return float(env['ir.config_parameter'].sudo().get_param(key) or default)
    except (TypeError, ValueError):
        return default


def _get_sorting_thresholds(env):
    """Single source of truth for the two admin-configured sorting
    reconciliation thresholds (res.config.settings: sorting_tolerance_
    threshold_1 / _2). Every place that needs them — the reconciliation
    preview, the finish-sorting validation — must call this instead of
    reading the config parameters directly."""
    t1 = _pct_param(env, 'warehouse.sorting_tolerance_threshold_1',
                    SORT_TOLERANCE_THRESHOLD_1)
    t2 = _pct_param(env, 'warehouse.sorting_tolerance_threshold_2',
                    SORT_TOLERANCE_THRESHOLD_2)
    return t1, t2


class RecycleShipment(models.Model):
    _name = 'recycle.shipment'
    _description = 'Incoming Shipment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority, id desc'

    name = fields.Char(
        string='Shipment ID', required=True, copy=False, readonly=True,
        default=lambda self: _('New'))
    warehouse_id = fields.Many2one(
        'recycle.warehouse', required=True, tracking=True, index=True,
        default=lambda self: self._default_warehouse())
    driver_name = fields.Char(required=True, tracking=True)
    truck_info = fields.Char(
        string='Truck ID', tracking=True,
        help='Truck plate number or other vehicle identification given by the driver.')
    truck_serial_number = fields.Char(
        string='Truck Serial Number', tracking=True,
        help='Serial number of the truck, as declared by the backend/driver.')
    dispatch_date = fields.Datetime(
        string='Dispatch Date',
        help='When the shipment was sent out, as declared by the backend/driver (optional).')
    priority = fields.Integer(
        string='Priority', default=10, tracking=True,
        help='Lower number = higher priority. Shipments are shown highest priority first.')
    expected_weight = fields.Float(
        string='Declared Weight (kg)', tracking=True,
        help='Total declared weight. Auto-computed from the expected material '
             'lines when the shipment is created with a material breakdown.')
    actual_weight = fields.Float(string='Actual Weight (kg)', tracking=True)
    receiving_zone_id = fields.Many2one(
        'recycle.zone', string='Receiving Zone', copy=False, tracking=True,
        domain="[('warehouse_id', '=', warehouse_id), ('zone_type', '=', 'receiving')]",
        help='Receiving-area zone (of this warehouse) chosen by the input '
             'employee when accepting — or by the manager when resolving a '
             'transferred shipment.')
    backend_shipment_id = fields.Char(
        string='Shipment ID (Backend)', index=True, copy=False,
        help='External identifier of this shipment in the NestJS backend — '
             'used to correlate records during API synchronisation.')
    weight_diff_pct = fields.Float(
        string='Weight Difference (%)', compute='_compute_weight_diff', store=True)
    state = fields.Selection(
        SHIPMENT_STATES, default='pending', required=True, tracking=True, index=True)
    receiver_user_id = fields.Many2one(
        'res.users', string='Reserved By (Reception)', readonly=True, copy=False, index=True)
    sorter_user_id = fields.Many2one(
        'res.users', string='Reserved By (Sorter)', readonly=True, copy=False, index=True)
    received_at = fields.Datetime(
        string='Processed At (Reception)', readonly=True, copy=False)
    sorted_at = fields.Datetime(
        string='Processed At (Sorting)', readonly=True, copy=False)
    # Storage is the moment sorting FINISHES and the graded stock is written to a
    # storage zone (see action_finish_sorting). Recorded explicitly — who put it
    # away and when — so the shipment detail can report the full received →
    # sorted → stored trail rather than leaving the last leg to be inferred.
    stored_at = fields.Datetime(
        string='Stored At', readonly=True, copy=False)
    stored_by = fields.Many2one(
        'res.users', string='Stored By', readonly=True, copy=False, index=True)
    line_ids = fields.One2many(
        'recycle.shipment.line', 'shipment_id', string='Sorted Products')
    # What this shipment cost the warehouse, alongside what it delivered.
    # Written when sorting finishes; kept here so the loss is readable from the
    # shipment itself rather than only from a warehouse-wide report, which is
    # where the question "which delivery was this?" is actually asked.
    damage_entry_ids = fields.One2many(
        'recycle.damage.entry', 'shipment_id', string='Damage Recorded',
        readonly=True)
    damage_entry_count = fields.Integer(
        string='Damage Entries', compute='_compute_damage_entry_count')

    @api.depends('damage_entry_ids')
    def _compute_damage_entry_count(self):
        for rec in self:
            rec.damage_entry_count = len(rec.damage_entry_ids)
    expected_line_ids = fields.One2many(
        'recycle.shipment.expected.line', 'shipment_id',
        string='Expected Materials',
        help='Materials declared by the backend/driver before the shipment '
             'arrives — shown read-only to the receiving employee as a '
             'visual sanity check.')
    expected_totals_display = fields.Char(
        string='Expected Totals', compute='_compute_expected_totals', store=True,
        help='Declared quantities grouped by unit of measure, e.g. '
             '"180.00 kg, 50.00 Units" — built dynamically from whatever '
             'units the declared materials actually use, never hard-coded.')
    note = fields.Text()
    total_good_qty = fields.Float(
        string='Total Good Quantity', compute='_compute_totals')
    total_damaged_qty = fields.Float(
        string='Total Damaged Quantity', compute='_compute_totals')
    recycle_archived = fields.Boolean(
        string='Archived', default=False, copy=False, index=True,
        help='Archived by the warehouse manager. Archived shipments are only '
             'visible to the warehouse manager and the administrator.')
    recycle_archived_by = fields.Many2one(
        'res.users', string='Archived By', readonly=True, copy=False)
    sorting_zone_id = fields.Many2one(
        'recycle.zone', string='Sorting Zone', copy=False, tracking=True)
    storage_zone_id = fields.Many2one(
        'recycle.zone', string='Storage Zone', copy=False, tracking=True)
    damage_pct = fields.Float(
        string='Damaged (%)', compute='_compute_damage_pct', store=True)
    damage_request_state = fields.Selection([
        ('none', 'None'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='none', copy=False, tracking=True,
       string='Damage Approval')
    damage_reason = fields.Text(string='Damage Reason', copy=False)
    damage_reject_reason = fields.Text(string='Damage Rejection Reason', copy=False)
    weight_shortfall_pct = fields.Float(
        string='Quantity Shortfall (%)', compute='_compute_weight_shortfall', store=True)
    weight_shortage_reason = fields.Text(
        string='Quantity Shortage Reason', copy=False,
        help='Sorter-entered free-text reason when a material\'s logged '
             'quantity falls in the reason-required tolerance band.')
    shortage_reason_category = fields.Selection([
        ('humidity_evaporation', 'Humidity / Evaporation'),
        ('excluded_from_sorting', 'Materials excluded from sorting'),
        ('original_qty_error', 'Error in the original declared quantity'),
        ('other', 'Other'),
    ], string='Shortage Reason Category', copy=False)
    manager_approved_sorting = fields.Boolean(
        string='Manager Approved Sorting Reconciliation', default=False,
        copy=False, tracking=True,
        help='Set by the warehouse manager to unblock a shipment whose '
             'sorted quantities failed the automatic reconciliation rules '
             '(a material short by more than the second threshold, or an '
             'exact-match unit that did not match). The sorter can then '
             'finish the shipment normally.')
    sort_escalation_state = fields.Selection([
        ('none', 'None'),
        ('pending', 'Pending Manager Review'),
        ('resolved', 'Resolved'),
    ], default='none', copy=False, tracking=True,
       string='Sorting Escalation')
    sort_escalation_reason = fields.Text(
        string='Sorting Escalation Reason', copy=False)

    @api.depends('line_ids.quantity', 'line_ids.product_id', 'actual_weight',
                 'expected_line_ids.expected_qty', 'expected_line_ids.product_id')
    def _compute_weight_shortfall(self):
        for rec in self:
            rec.weight_shortfall_pct = rec._sort_reconciliation()['worst_shortfall_pct']

    def _sort_reconciliation(self):
        """Compare what was actually sorted (line_ids) against what was
        declared before arrival (expected_line_ids), and classify the
        result according to exactly three rules — see
        action_finish_sorting() for how each is enforced:

          Rule 1 (always, no tolerance): the total entered for a unit of
              measure must never exceed the total expected for that unit
              of measure, summed across every material that uses it.
          Rule 2 (only for uom_id.allows_tolerance = True materials): a
              per-material shortage is auto-accepted up to threshold_1,
              requires a reason up to threshold_2, and blocks beyond it.
          Rule 3 (only for uom_id.allows_tolerance = False materials): the
              entered quantity must equal the expected quantity exactly.

        Returns a dict:
          missing_product_ids / extra_product_ids — declared materials
              never logged / logged materials never declared.
          products — full per-material breakdown (expected/entered/pct/
              tier), for the UI preview.
          uom_groups — per-unit-of-measure expected/entered totals, the
              basis for Rule 1.
          rule1_violations — uom groups where entered > expected.
          blocked_products — materials that trip Rule 2 (over threshold_2)
              or Rule 3 (exact mismatch on a non-tolerant unit).
          reason_needed_products — materials in Rule 2's reason-required
              band.
          worst_shortfall_pct — worst Rule-2-eligible shortfall, kept for
              simple UI badges.
          over_limit — True if rule1_violations is non-empty.
        """
        self.ensure_one()
        Product = self.env['recycle.product'].sudo()

        expected_by_product = {}
        for el in self.expected_line_ids:
            expected_by_product[el.product_id.id] = (
                expected_by_product.get(el.product_id.id, 0.0) + el.expected_qty)

        entered_by_product = {}
        for line in self.line_ids:
            entered_by_product[line.product_id.id] = (
                entered_by_product.get(line.product_id.id, 0.0) + line.quantity)

        expected_products = set(expected_by_product.keys())
        entered_products = set(entered_by_product.keys())

        if not self.expected_line_ids:
            # Legacy fallback for shipments with no declared material
            # breakdown: compare the flat logged total against the actual
            # weight recorded at reception (old, pre-UoM behaviour).
            total_qty = sum(self.line_ids.mapped('quantity'))
            actual = self.actual_weight or 0.0
            over = bool(actual and total_qty > actual)
            shortfall = (max(0.0, (actual - total_qty) / actual * 100.0)
                         if actual else 0.0)
            return {
                'missing_product_ids': [], 'extra_product_ids': [],
                'products': [], 'uom_groups': [], 'rule1_violations': [],
                'worst_shortfall_pct': round(shortfall, 1),
                'over_limit': over,
                'blocked_products': [], 'reason_needed_products': [],
            }

        missing = expected_products - entered_products
        extra = entered_products - expected_products

        threshold_1, threshold_2 = _get_sorting_thresholds(self.env)

        uom_groups = {}  # uom_id -> {'name': str, 'expected': float, 'entered': float}
        products = []
        blocked_products = []
        reason_needed_products = []
        worst_pct = 0.0

        for pid in (expected_products | entered_products):
            product = Product.browse(pid)
            exp = expected_by_product.get(pid, 0.0)
            ent = entered_by_product.get(pid, 0.0)
            uom = product.uom_id
            g = uom_groups.setdefault(
                uom.id, {'name': uom.name or '-', 'expected': 0.0, 'entered': 0.0})
            g['expected'] += exp
            g['entered'] += ent

            entry = {
                'product_id': pid,
                'product_name': product.name,
                'uom_id': uom.id,
                'uom_name': uom.name or '-',
                'allows_tolerance': uom.allows_tolerance,
                'expected': exp,
                'entered': ent,
                'pct': round((exp - ent) / exp * 100.0, 1) if exp else None,
                'tier': 'auto',
            }
            if exp > 0:
                if uom.allows_tolerance:
                    # Rule 2 — overage is Rule 1's job, this only looks at
                    # shortage for THIS specific material.
                    if ent < exp:
                        shortfall_pct = (exp - ent) / exp * 100.0
                        worst_pct = max(worst_pct, shortfall_pct)
                        if shortfall_pct > threshold_2:
                            entry['tier'] = 'blocked'
                            blocked_products.append(entry)
                        elif shortfall_pct > threshold_1:
                            entry['tier'] = 'reason_needed'
                            reason_needed_products.append(entry)
                else:
                    # Rule 3 — no tolerance at all: any mismatch blocks.
                    if ent != exp:
                        entry['tier'] = 'blocked'
                        blocked_products.append(entry)
            products.append(entry)

        rule1_violations = []
        for uom_id, g in uom_groups.items():
            if g['entered'] > g['expected']:
                rule1_violations.append({
                    'uom_id': uom_id, 'uom_name': g['name'],
                    'expected': g['expected'], 'entered': g['entered'],
                    'over_by': round(g['entered'] - g['expected'], 3),
                })

        # ── The LOST quantity ────────────────────────────────────────────
        #
        # What was declared and never arrived: expected − entered. Per
        # material, and per unit of measure across the materials that share
        # one — kilograms with kilograms, pieces with pieces. Adding them
        # together would produce a number with no unit anyone could write
        # beside it.
        #
        # This is NOT `damage_pct`, which counts goods that DID arrive and
        # were found unusable. Those are two different physical things: one
        # is on the warehouse floor waiting to be written off, the other
        # never came off the lorry. Keeping them apart is what lets a
        # shipment that arrived complete-but-damaged be told from one that
        # arrived short.
        #
        # Computed for THIS shipment alone — nothing is carried forward from
        # a previous one.
        for entry in products:
            exp = entry['expected']
            lost = max(exp - entry['entered'], 0.0)
            entry['lost_qty'] = round(lost, 3)
            entry['lost_pct'] = round(lost / exp * 100.0, 1) if exp else None

        for g in uom_groups.values():
            lost = max(g['expected'] - g['entered'], 0.0)
            g['lost_qty'] = round(lost, 3)
            g['lost_pct'] = (round(lost / g['expected'] * 100.0, 1)
                             if g['expected'] else None)

        return {
            'missing_product_ids': sorted(missing),
            'extra_product_ids': sorted(extra),
            'products': products,
            'uom_groups': [
                {'uom_id': k, 'uom_name': v['name'],
                 'expected': v['expected'], 'entered': v['entered'],
                 'lost_qty': v['lost_qty'], 'lost_pct': v['lost_pct']}
                for k, v in uom_groups.items()],
            'rule1_violations': rule1_violations,
            'worst_shortfall_pct': round(worst_pct, 1),
            'over_limit': bool(rule1_violations),
            'blocked_products': blocked_products,
            'reason_needed_products': reason_needed_products,
        }

    def report_material_rows(self):
        """Per-material breakdown for the shipment-detail PDF: expected, sorted
        (entered) and LOST quantity for each material this shipment declared.

        Reuses `_sort_reconciliation` — the same figures the sorting screen and
        the shortfall rules run on — so the printed sheet can never disagree with
        what the warehouse acted on. Defensive: a shipment not far enough along
        to reconcile simply prints no rows rather than failing the whole report.
        """
        self.ensure_one()
        try:
            return self._sort_reconciliation().get('products', [])
        except Exception:            # noqa: BLE001 - a report must never 500
            return []

    def get_sorting_plan(self):
        """What the sorter still has to account for, decided by the SERVER.

        The picker on the sorting screen must offer only the materials this
        shipment actually declared, and only the grades of those materials
        that have not been entered yet. Deciding that in the browser alone
        would make it a suggestion: anything that reaches `action_finish_sorting`
        by another route — a stale tab, a replayed call — would bypass it.
        So the rule lives here and the screen renders what it is told.

        For each declared material:
            grades          the material's own grades, each marked `done`
            remaining_qty   expected − entered so far, never below zero
            complete        nothing left to enter for it

        A material with NO grades is complete the moment any quantity is
        logged for it: there is one number to give and it has been given.

        A GRADED material is complete when every one of its grades has a
        line — including the ones that arrived empty. A grade that did not
        turn up is entered as ZERO, deliberately: it is the honest record
        that it was looked for and not found, and it keeps the sum of the
        grades comparable with what was declared.
        """
        self.ensure_one()
        Conditions = self.env['recycle.material.condition'].sudo()

        entered_by_product = {}
        grades_by_product = {}
        for line in self.line_ids:
            pid = line.product_id.id
            entered_by_product[pid] = entered_by_product.get(pid, 0.0) + line.quantity
            grades_by_product.setdefault(pid, set()).add(
                (line.condition or '').strip().upper())

        plan = []
        for el in self.expected_line_ids:
            product = el.product_id
            pid = product.id
            expected = el.expected_qty or 0.0
            entered = entered_by_product.get(pid, 0.0)
            used = grades_by_product.get(pid, set())

            rows = Conditions.search(
                [('product_id', '=', pid), ('active', '=', True)],
                order='sort_order, id')
            grades = [{
                'code': row.code,
                'name': row.name,
                'done': row.code.strip().upper() in used,
            } for row in rows]

            if grades:
                complete = all(g['done'] for g in grades)
            else:
                complete = pid in entered_by_product

            plan.append({
                'product_id': pid,
                'product_name': product.name,
                'uom_id': product.uom_id.id,
                'uom_name': product.uom_id.name or '',
                'allows_tolerance': product.uom_id.allows_tolerance,
                'expected': expected,
                'entered': round(entered, 3),
                # What may still be entered. A material already at its
                # declared quantity offers zero, which is what stops the
                # total from ever exceeding what was declared.
                'remaining_qty': round(max(expected - entered, 0.0), 3),
                'is_graded': bool(grades),
                'grades': grades,
                'complete': complete,
            })

        # ── A shipment that declared NOTHING ─────────────────────────────
        #
        # Not every shipment arrives with a material breakdown: older ones
        # predate the feature, and a driver can still turn up with a load
        # nobody itemised in advance. There is then nothing to restrict the
        # picker against — and restricting it to an empty list would leave the
        # sorter staring at a dropdown with no options and no explanation,
        # unable to do the one job the screen exists for.
        #
        # So the screen is TOLD there is no breakdown and falls back to the
        # full catalogue. Saying it explicitly beats inferring it from an empty
        # list, which is also what a fully-sorted shipment looks like.
        has_breakdown = bool(self.expected_line_ids)

        return {
            'plan': plan,
            'has_declared_breakdown': has_breakdown,
            # The screen hides "add a line" on this alone, so the decision
            # about when sorting is fully entered is made in one place.
            #
            # Never true without a breakdown: there is no declared quantity to
            # measure completeness against, so the sorter decides when they are
            # finished — the button stays.
            'all_complete': has_breakdown and all(p['complete'] for p in plan),
        }

    def get_sort_reconciliation(self):
        """RPC-callable wrapper around _sort_reconciliation() — lets the
        sorting UI show the exact same preview the server will use to
        decide auto-pass / reason-required / manager-approval-needed,
        before the employee even clicks Finish."""
        self.ensure_one()
        self._check_reservation('sorter_user_id')
        result = self._sort_reconciliation()
        Product = self.env['recycle.product'].sudo()
        result['missing_products'] = [
            {'id': pid, 'name': Product.browse(pid).name}
            for pid in result['missing_product_ids']]
        result['extra_products'] = [
            {'id': pid, 'name': Product.browse(pid).name}
            for pid in result['extra_product_ids']]
        t1, t2 = _get_sorting_thresholds(self.env)
        result['threshold_1'] = t1
        result['threshold_2'] = t2
        return result

    @api.depends('line_ids.quantity', 'line_ids.is_damaged')
    def _compute_damage_pct(self):
        for rec in self:
            total = sum(rec.line_ids.mapped('quantity'))
            damaged = sum(l.quantity for l in rec.line_ids if l.is_damaged)
            rec.damage_pct = (damaged / total * 100.0) if total else 0.0

    # ---------------- Archive (manager / admin only) ----------------

    def action_archive_recycle(self):
        if not self._is_supervisor():
            raise UserError(_('Only the warehouse manager or the administrator can archive shipments.'))
        # A shipment is archived only once it is FINISHED. Archiving is how the
        # warehouse puts a shipment to rest; doing it while work is still
        # outstanding would hide a live task from the very lists people work
        # from, and leave stock unstored or a decision unmade with no screen
        # still showing it.
        for rec in self:
            if rec.state != 'sorted':
                raise UserError(_(
                    'Shipment %s is not finished yet, so it cannot be archived. '
                    'Finish sorting and storing it first.') % rec.name)
            if rec.damage_request_state == 'pending':
                raise UserError(_(
                    'Shipment %s has a damage decision still pending with the '
                    'warehouse manager. Settle it before archiving.') % rec.name)
            if rec.sort_escalation_state == 'pending':
                raise UserError(_(
                    'Shipment %s is still with the warehouse manager for a '
                    'shortfall review. Resolve it before archiving.') % rec.name)
        self.write({'recycle_archived': True,
                    'recycle_archived_by': self.env.user.id})
        for rec in self:
            rec.message_post(body=_('Shipment archived by %s.') % self.env.user.name)

    def action_unarchive_recycle(self):
        if not self._is_supervisor():
            raise UserError(_('Only the warehouse manager or the administrator can restore shipments.'))
        self.write({'recycle_archived': False, 'recycle_archived_by': False})
        for rec in self:
            rec.message_post(body=_('Shipment restored from archive by %s.') % self.env.user.name)

    def _warehouse_manager_user(self):
        """The manager user of this shipment's warehouse (both linkages)."""
        self.ensure_one()
        manager = self.warehouse_id.manager_user_id
        if not manager:
            manager = self.env['res.users'].sudo().search([
                ('recycle_role', '=', 'manager'),
                ('recycle_warehouse_id', '=', self.warehouse_id.id)], limit=1)
        return manager

    def _default_warehouse(self):
        user = self.env.user
        if user.recycle_warehouse_id:
            return user.recycle_warehouse_id.id
        wh = self.env['recycle.warehouse'].search(
            [('manager_user_id', '=', user.id)], limit=1)
        return wh.id or False

    @api.depends('expected_weight', 'actual_weight')
    def _compute_weight_diff(self):
        for rec in self:
            if rec.expected_weight and rec.actual_weight:
                rec.weight_diff_pct = abs(
                    rec.actual_weight - rec.expected_weight
                ) / rec.expected_weight * 100.0
            else:
                rec.weight_diff_pct = 0.0

    @api.depends('expected_line_ids.uom_id', 'expected_line_ids.expected_qty')
    def _compute_expected_totals(self):
        for rec in self:
            totals = {}  # uom_id -> [qty, name]
            for el in rec.expected_line_ids:
                key = el.uom_id.id
                if key not in totals:
                    totals[key] = [0.0, el.uom_id.name or '-']
                totals[key][0] += el.expected_qty
            rec.expected_totals_display = ', '.join(
                '%.2f %s' % (qty, name) for qty, name in totals.values()
            ) if totals else ''

    @api.depends('line_ids.quantity', 'line_ids.is_damaged')
    def _compute_totals(self):
        # Usable is now everything NOT written off, rather than a fixed list of
        # three grade names. That list was wrong the moment a material was
        # graded PREMIUM/STANDARD: neither name appeared in it, so every sorted
        # unit of that material counted as neither usable nor damaged and simply
        # vanished from both totals.
        for rec in self:
            damaged = rec.line_ids.filtered(lambda l: l.is_damaged)
            usable = rec.line_ids - damaged
            rec.total_good_qty = sum(usable.mapped('quantity'))
            rec.total_damaged_qty = sum(damaged.mapped('quantity'))

    @api.constrains('priority')
    def _check_priority(self):
        for rec in self:
            if rec.priority < 0:
                raise ValidationError(_('Priority cannot be negative.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].sudo().next_by_code(
                    'recycle.shipment') or _('New')
        return super().create(vals_list)

    @api.model
    def backend_upsert_shipment(self, payload):
        """Create or refresh an incoming shipment from the NestJS backend, keyed
        by `backend_shipment_id` so a retry lands on the same record (idempotent).

        Called when the RECEPTION employee scans the shipment QR: the backend has
        already validated warehouse isolation and flipped the shipment's state,
        and hands the materials AGGREGATED per product — reception, sorting and
        storage only ever work off the shipment's TOTALS, never per collection
        request. The per-request breakdown stays in the backend for the admin.

        The shipment lands in the normal `pending` state, so the whole existing
        reception → sorting → storage flow works UNCHANGED — nothing here touches
        it. `expected_line_ids` are the same aggregated declared lines the sorter
        already reconciles against.
        """
        backend_id = (payload.get('backend_shipment_id') or '').strip()
        if not backend_id:
            raise UserError(_('backend_shipment_id is required.'))
        wh_backend_id = (payload.get('warehouse_backend_id') or '').strip()
        warehouse = self.env['recycle.warehouse'].sudo().search(
            [('backend_id', '=', wh_backend_id)], limit=1)
        if not warehouse:
            raise UserError(
                _('No warehouse matches backend id %s.') % (wh_backend_id or '-'))

        vals = {
            'warehouse_id': warehouse.id,
            'driver_name': payload.get('driver_name') or _('Driver'),
            'truck_info': payload.get('truck_info') or False,
            'truck_serial_number': payload.get('truck_serial_number') or False,
            'expected_weight': float(
                payload.get('total_weight_kg')
                or payload.get('expected_weight') or 0.0),
            'backend_shipment_id': backend_id,
        }
        if payload.get('dispatch_date'):
            # The backend sends ISO 8601 (e.g. 2026-08-22T21:25:51.447Z); Odoo
            # stores naive UTC datetimes, so normalise to 'YYYY-MM-DD HH:MM:SS'.
            raw = str(payload['dispatch_date'])
            vals['dispatch_date'] = (
                raw.replace('T', ' ').replace('Z', '').split('.')[0].strip())

        # Aggregated declared materials: one expected line per product.
        exp_cmds = []
        for line in (payload.get('expected_lines') or []):
            pid = int(line.get('odoo_product_id') or 0)
            qty = float(line.get('quantity') or 0.0)
            if pid and qty > 0:
                exp_cmds.append((0, 0, {'product_id': pid, 'expected_qty': qty}))

        shipment = self.sudo().search(
            [('backend_shipment_id', '=', backend_id)], limit=1)
        if shipment:
            # Refresh declared lines only while still awaiting reception; never
            # rewrite a shipment a sorter has already started working.
            if shipment.state == 'pending':
                vals['expected_line_ids'] = [(5, 0, 0)] + exp_cmds
            shipment.sudo().write(vals)
        else:
            vals['expected_line_ids'] = exp_cmds
            shipment = self.sudo().create(vals)

        return {
            'odoo_shipment_id': shipment.id,
            'name': shipment.name,
            'state': shipment.state,
        }

    def write(self, vals):
        # Priority comes from the backend or is set by the warehouse
        # manager/admin only — reception and sorting employees never touch it.
        if 'priority' in vals and not self._is_supervisor():
            raise UserError(_(
                'Only the warehouse manager or the administrator can change '
                'shipment priority.'))
        return super().write(vals)

    # ---------------- Helpers ----------------

    def _is_supervisor(self):
        user = self.env.user
        return (user.has_group('recycle_warehouse.group_recycle_admin')
                or user.has_group('recycle_warehouse.group_recycle_manager'))

    def _check_reservation(self, reserver_field):
        """Alert if the shipment is reserved by someone else."""
        for rec in self:
            reserver = rec[reserver_field]
            if reserver and reserver != self.env.user and not rec._is_supervisor():
                raise UserError(_(
                    'This shipment is currently being processed by %s.'
                ) % reserver.name)

    def _log_zone_movement(self, from_zone, to_zone):
        """Record a shipment's move into (or between) warehouse zones."""
        self.ensure_one()
        self.env['recycle.shipment.zone.movement'].sudo().create({
            'shipment_id': self.id,
            'from_zone_id': from_zone.id if from_zone else False,
            'to_zone_id': to_zone.id,
            'moved_by': self.env.user.id,
            'moved_at': fields.Datetime.now(),
        })

    # ---------------- Reception workflow ----------------

    def action_start_receiving(self):
        """Input employee reserves the shipment (قيد الاستقبال)."""
        for rec in self:
            if rec.state != 'pending':
                raise UserError(_('Only pending shipments can be received.'))
            rec._check_reservation('receiver_user_id')
            rec.write({
                'state': 'receiving',
                'receiver_user_id': self.env.user.id,
            })
            rec.message_post(body=_(
                'Reception started by %s. Shipment reserved.') % self.env.user.name)

    def action_accept(self):
        """Accept the shipment. Actual weight is optional; a difference inside
        the 5-10% band is allowed (the UI shows a warning); above the 10%
        hard limit acceptance is blocked and the shipment must be
        transferred to the warehouse manager."""
        for rec in self:
            if rec.state != 'receiving':
                raise UserError(_('Start receiving the shipment first.'))
            rec._check_reservation('receiver_user_id')
            hard_limit = _pct_param(self.env, 'recycle.weight_max_pct',
                                    WEIGHT_HARD_LIMIT)
            if rec.actual_weight and rec.weight_diff_pct > hard_limit:
                raise UserError(_(
                    'Weight difference is %.2f%% (more than %s%%).\n'
                    'You cannot accept this shipment - transfer it to the warehouse manager.'
                ) % (rec.weight_diff_pct, int(hard_limit)))
            if not rec.receiving_zone_id:
                raise UserError(_(
                    'Select a receiving zone of your warehouse before '
                    'accepting the shipment.'))
            rec.write({'state': 'accepted', 'received_at': fields.Datetime.now()})
            rec._log_zone_movement(False, rec.receiving_zone_id)
            rec.message_post(body=_(
                'Shipment accepted by %s (difference: %.2f%%). Moved to sorting area.'
            ) % (self.env.user.name, rec.weight_diff_pct))

    def action_escalate(self):
        """Transfer the shipment to the warehouse manager (difference > 5%)."""
        for rec in self:
            if rec.state != 'receiving':
                raise UserError(_('Only shipments in reception can be transferred.'))
            rec._check_reservation('receiver_user_id')
            rec.write({'state': 'escalated', 'received_at': fields.Datetime.now()})
            rec.message_post(body=_(
                'Shipment transferred to the warehouse manager by %s '
                '(weight difference: %.2f%%).'
            ) % (self.env.user.name, rec.weight_diff_pct))
            # Notify the warehouse manager on their dashboard
            self.env['recycle.notification']._notify_user(
                rec._warehouse_manager_user(),
                _('Transferred shipment: %s') % rec.name,
                _('%s transferred shipment %s (weight difference %.2f%%). '
                  'Review it in the Transferred Shipments screen.')
                % (self.env.user.name, rec.name, rec.weight_diff_pct))

    def action_release(self):
        """Input employee releases a reserved shipment so a colleague can take it."""
        for rec in self:
            if rec.state != 'receiving':
                raise UserError(_('Only shipments in reception can be released.'))
            rec._check_reservation('receiver_user_id')
            rec.write({'state': 'pending', 'receiver_user_id': False})
            rec.message_post(body=_(
                'Shipment released by %s and is available again.') % self.env.user.name)

    def action_resolve_escalated(self):
        """Warehouse manager resolves a transferred shipment and sends it to sorting."""
        if not self._is_supervisor():
            raise UserError(_('Only the warehouse manager can process transferred shipments.'))
        for rec in self:
            if rec.state != 'escalated':
                raise UserError(_('Only transferred shipments can be processed here.'))
            if not rec.receiving_zone_id:
                raise UserError(_(
                    'Select a receiving zone of your warehouse before '
                    'approving the transferred shipment.'))
            rec.write({'state': 'accepted', 'receiver_user_id': False})
            rec._log_zone_movement(False, rec.receiving_zone_id)
            rec.message_post(body=_(
                'Transferred shipment reviewed and approved by %s. Sent to sorting.'
            ) % self.env.user.name)

    # ---------------- Sorting workflow ----------------

    def action_start_sorting(self):
        for rec in self:
            if rec.state != 'accepted':
                raise UserError(_('Only accepted shipments can be sorted.'))
            rec._check_reservation('sorter_user_id')
            # Priority rule: a shipment can only be sorted when no OTHER
            # accepted shipment of the same warehouse has a higher priority
            # (lower number = higher priority).
            higher_ship = self.search([
                ('warehouse_id', '=', rec.warehouse_id.id),
                ('state', '=', 'accepted'),
                ('id', '!=', rec.id),
                ('priority', '<', rec.priority),
            ], order='priority asc', limit=1)
            if higher_ship and not rec._is_supervisor():
                raise UserError(_(
                    'You cannot process shipment %s (priority %s) — shipment '
                    '%s has a higher priority (%s). Process higher priority '
                    'shipments first.'
                ) % (rec.name, rec.priority, higher_ship.name, higher_ship.priority))
            rec.write({
                'state': 'sorting',
                'sorter_user_id': self.env.user.id,
            })
            rec.message_post(body=_(
                'Sorting started by %s. Shipment reserved.') % self.env.user.name)

    def action_set_sorting_zone(self, zone_id):
        """Pick the sorting zone where this shipment will be processed.
        Records the receiving-zone → sorting-zone move in the zone
        movement log."""
        zone = self.env['recycle.zone'].browse(int(zone_id)).exists()
        if not zone or zone.zone_type != 'sorting':
            raise UserError(_('Please select a valid sorting zone.'))
        for rec in self:
            if rec.state != 'sorting':
                raise UserError(_('Start sorting the shipment first.'))
            rec._check_reservation('sorter_user_id')
            if zone.warehouse_id != rec.warehouse_id:
                raise UserError(_(
                    'Select a sorting zone that belongs to this shipment\'s '
                    'warehouse.'))
            previous_zone = rec.sorting_zone_id
            rec.write({'sorting_zone_id': zone.id})
            rec._log_zone_movement(previous_zone or rec.receiving_zone_id, zone)
            rec.message_post(body=_(
                'Shipment moved from the receiving zone to sorting zone "%s" by %s.'
            ) % (zone.name, self.env.user.name))
        return True

    def action_set_storage_zone(self, zone_id):
        """Pick the storage zone before logging materials (Start Storage).
        Records the sorting-zone → storage-zone move in the zone movement
        log."""
        zone = self.env['recycle.zone'].browse(int(zone_id)).exists()
        if not zone or zone.zone_type != 'storage':
            raise UserError(_('Please select a valid storage zone.'))
        for rec in self:
            if rec.state != 'sorting':
                raise UserError(_('Shipment is not in sorting state.'))
            rec._check_reservation('sorter_user_id')
            if not rec.sorting_zone_id:
                raise UserError(_('Move the shipment to a sorting zone first.'))
            if zone.warehouse_id != rec.warehouse_id:
                raise UserError(_(
                    'Select a storage zone that belongs to this shipment\'s '
                    'warehouse.'))
            previous_zone = rec.storage_zone_id
            rec.write({'storage_zone_id': zone.id})
            rec._log_zone_movement(previous_zone or rec.sorting_zone_id, zone)
            rec.message_post(body=_(
                'Storage started by %s: storage zone set to "%s".'
            ) % (self.env.user.name, zone.name))
        return True

    def action_assign_line_storage_zones(self, assignments):
        """Assign individual materials to storage zones — split a shipment.

        `assignments` = [{'line_id': int, 'zone_id': int}, ...]. The counterpart
        to `action_set_storage_zone` (which puts the WHOLE shipment in one zone):
        this puts each named material in its own. A material left out keeps
        whatever zone it had, or falls back to the shipment-wide zone at storing
        time. The write to stock still happens once, at `action_finish_sorting`;
        this only records WHERE each material will go, validated against this
        shipment's own lines and its warehouse's storage zones.

        Usable by the reserved sorter OR the warehouse manager (who may store an
        escalated shipment themselves), exactly like the finish action.
        """
        self.ensure_one()
        if self.state not in ('sorting', 'pending_sorting_approval'):
            raise UserError(_('Shipment is not in a sortable state.'))
        self._check_reservation('sorter_user_id')
        Zone = self.env['recycle.zone']
        for a in (assignments or []):
            line = self.line_ids.filtered(lambda l: l.id == int(a.get('line_id') or 0))
            if not line:
                raise UserError(_('Unknown shipment line %s.') % a.get('line_id'))
            zone = Zone.browse(int(a.get('zone_id') or 0)).exists()
            if (not zone or zone.zone_type != 'storage'
                    or zone.warehouse_id != self.warehouse_id):
                raise UserError(_(
                    'Select a valid storage zone of this warehouse for "%s".'
                ) % line.product_id.name)
            line.storage_zone_id = zone.id
        self.message_post(body=_(
            '%s assigned storage zones to %d material line(s).'
        ) % (self.env.user.name, len(assignments or [])))
        return True

    def action_request_damage_approval(self, reason=None):
        """Ask the warehouse manager to authorise a write-off — at ANY amount.

        There used to be a floor here: below 40% the request was REFUSED as
        unnecessary. That matched a storing rule which also let small damage
        through, and the pair moved together.

        They no longer do. Storing now requires approval for any damaged line,
        so a floor on the request would deadlock the sorter completely — unable
        to store, and told the approval they need is not needed. The two gates
        have to agree, and this is the half that had to change.
        """
        for rec in self:
            if rec.state != 'sorting':
                raise UserError(_('Shipment is not in sorting state.'))
            rec._check_reservation('sorter_user_id')
            if not rec.line_ids.filtered('is_damaged'):
                raise UserError(_(
                    'Nothing on this shipment is marked damaged, so there is '
                    'nothing to write off.'))
            rec.write({'damage_request_state': 'pending',
                       'damage_reason': (reason or '').strip()})
            rec._notify_damage_request(reason)
        return True

    def _notify_damage_request(self, reason=None):
        """Tell the warehouse manager (and the administrator) that a write-off
        is waiting on the manager's decision. Called both when the sorter flags
        it explicitly and when finishing raises it automatically."""
        self.ensure_one()
        reason = (reason or self.damage_reason or '').strip()
        body = _('%(who)s reports %(pct).1f%% damaged materials in shipment '
                 '%(name)s. Reason: %(reason)s. Review it in Damaged Sorting '
                 'Requests.') % {
            'who': self.env.user.name, 'pct': self.damage_pct,
            'name': self.name, 'reason': reason or '-'}
        manager = self._warehouse_manager_user()
        self.env['recycle.notification']._notify_user(
            manager, _('Damaged sorting request: %s') % self.name, body)
        # The administrator is told too. A write-off that only ever appears
        # inside one warehouse's own queue is one nobody outside it can question
        # while the material is still there to look at — by the time it shows on
        # a monthly total, the material is gone.
        self.env['recycle.notification']._notify_admins(
            _('Damage reported: %(name)s (%(warehouse)s)') % {
                'name': self.name, 'warehouse': self.warehouse_id.name or '-'},
            body, request_user=self.env.user,
            related_model='recycle.shipment', related_res_id=self.id)

    def action_approve_damage(self):
        if not self._is_supervisor():
            raise UserError(_('Only the warehouse manager can approve damaged sorting requests.'))
        Damage = self.env['recycle.damage.entry']
        for rec in self:
            if rec.damage_request_state != 'pending':
                raise UserError(_('Only pending requests can be approved.'))
            # Commit the write-off to the loss ledger. Finishing HELD the
            # damaged lines (neither stored nor written off); approving is what
            # records the loss. The quantity is NOT stored — it stays flagged
            # damaged on the shipment so the shipment shows what was lost.
            for line in rec.line_ids.filtered('is_damaged'):
                Damage.record_from_sorting(rec, line)
            rec.write({'damage_request_state': 'approved'})
            self.env['recycle.notification']._notify_user(
                rec.sorter_user_id,
                _('Damage request approved: %s') % rec.name,
                _('The manager approved the write-off. The damaged quantity is '
                  'recorded as damaged on the shipment and was not stored.'))
        return True

    def action_reject_damage(self, reason=None, grades=None, storage_zone_id=None):
        """The manager refuses the write-off: the goods are sound, store them.

        A rejection is a decision that the material the sorter wanted destroyed
        is fit to sell. The damaged flag is CLEARED and the quantity becomes
        ordinary stock.

        WHERE it is stored depends on when the manager rules:
          - If the shipment has already been SORTED, finishing HELD the damaged
            goods out of storage, so the manager stores them now and picks the
            zone (`storage_zone_id`, falling back to the shipment's).
          - If it is still being sorted, the flag is cleared and the sorter's
            finish step stores it, exactly as any sound line.

        A GRADED material cannot be stored without a grade, and the sorter's
        judgement is the one just overruled — so the manager supplies it.
        `grades` maps a line id to a grade code: {line_id: 'GOOD'}. The grade is
        required only where the material actually has grades.
        """
        if not self._is_supervisor():
            raise UserError(_('Only the warehouse manager can reject damaged sorting requests.'))

        Conditions = self.env['recycle.material.condition']
        Stock = self.env['recycle.stock']
        grades = {int(k): v for k, v in (grades or {}).items()}

        for rec in self:
            if rec.damage_request_state != 'pending':
                raise UserError(_('Only pending requests can be rejected.'))

            damaged = rec.line_ids.filtered('is_damaged')

            # Every graded material among them needs a grade before anything is
            # written — checked first so a partial answer cannot leave half the
            # lines cleared and half still flagged.
            missing = damaged.filtered(
                lambda line: Conditions.has_grades(line.product_id)
                and not (grades.get(line.id) or '').strip())
            if missing:
                raise UserError(_(
                    'These materials are graded, so storing them needs a grade '
                    'you choose: %s'
                ) % ', '.join(missing.mapped('product_id.name')))

            # Once finished, the damaged goods were held out of storage: the
            # manager stores them now and chooses where.
            store_now = rec.state == 'sorted'
            zone = rec.storage_zone_id
            if store_now:
                if storage_zone_id:
                    zone = self.env['recycle.zone'].browse(int(storage_zone_id))
                if not zone:
                    raise UserError(_(
                        'Choose a storage zone to store these materials in.'))

            for line in damaged:
                code = (grades.get(line.id) or '').strip()
                # Normalised against THIS material, so a code that is not one of
                # its grades is refused rather than stored.
                cond = (Conditions.normalize(line.product_id, code)
                        if code else False)
                line.write({'is_damaged': False, 'condition': cond})
                if store_now and line.quantity > 0:
                    Stock._add_quantity(
                        rec.warehouse_id, line.product_id, line.quantity,
                        condition=cond or False, zone=zone or None)

            rec.write({'damage_request_state': 'rejected',
                       'damage_reject_reason': (reason or '').strip()})
            self.env['recycle.notification']._notify_user(
                rec.sorter_user_id,
                _('Damage request rejected: %s') % rec.name,
                (_('The manager decided this material is sound and stored it '
                   'instead of writing it off. Reason: %s.')
                 if store_now else
                 _('The manager decided this material is sound. Reason: %s. It '
                   'is no longer marked damaged — finish sorting to store it.'))
                % ((reason or '').strip() or '-'))
        return True

    def action_release_sorting(self):
        """Sorting employee releases a reserved shipment so a colleague can take it."""
        for rec in self:
            if rec.state != 'sorting':
                raise UserError(_('Only shipments currently being sorted can be released.'))
            if rec.sorting_zone_id and not rec._is_supervisor():
                raise UserError(_(
                    'This shipment was already moved to a sorting zone and '
                    'can no longer be released.'))
            rec._check_reservation('sorter_user_id')
            rec.write({'state': 'accepted', 'sorter_user_id': False})
            rec.message_post(body=_(
                'Sorting reservation released by %s. Shipment is available again.'
            ) % self.env.user.name)

    def action_escalate_sorting(self, description=None):
        """Sorter transfers a shipment with a large quantity shortfall to the
        warehouse manager instead of finishing it (blocks finishing until
        the manager resolves it). Records who escalated it and when, plus
        a per-unit-of-measure breakdown of the shortfall so the manager can
        see exactly what's missing without re-deriving it."""
        for rec in self:
            if rec.state != 'sorting':
                raise UserError(_('Shipment is not in sorting state.'))
            rec._check_reservation('sorter_user_id')
            recon = rec._sort_reconciliation()
            shortage_pct = recon['worst_shortfall_pct']
            group_lines = ', '.join(
                _('%s: %.2f / %.2f') % (g['uom_name'], g['entered'], g['expected'])
                for g in recon['uom_groups']
            ) or '-'
            now = fields.Datetime.now()
            desc = (description or '').strip()
            reason_text = _(
                '%s%% short of the declared materials. %s'
                '\nBy %s on %s.'
            ) % (('%.2f' % shortage_pct), group_lines, self.env.user.name, now)
            if desc:
                reason_text = desc + '\n' + reason_text
            rec.write({
                'sort_escalation_state': 'pending',
                'sort_escalation_reason': reason_text,
            })
            rec.message_post(body=_(
                'Shipment transferred to the warehouse manager by %s due to a '
                '%.2f%% quantity shortfall (%s).')
                % (self.env.user.name, shortage_pct, group_lines))
            self.env['recycle.notification']._notify_user(
                rec._warehouse_manager_user(),
                _('Sorting quantity issue: %s') % rec.name,
                _('%s reports a %.2f%% quantity shortfall while sorting shipment %s '
                  '(%s). Review it in Sorting Escalations.')
                % (self.env.user.name, shortage_pct, rec.name, group_lines))
        return True

    def action_resolve_sort_escalation(self):
        """Warehouse manager acknowledges the shortfall and unblocks the
        sorter so they can correct the quantities and finish the shipment."""
        if not self._is_supervisor():
            raise UserError(_('Only the warehouse manager can resolve sorting escalations.'))
        for rec in self:
            if rec.sort_escalation_state != 'pending':
                raise UserError(_('Only pending escalations can be resolved.'))
            rec.write({'sort_escalation_state': 'resolved'})
            self.env['recycle.notification']._notify_user(
                rec.sorter_user_id,
                _('Sorting escalation resolved: %s') % rec.name,
                _('The manager reviewed shipment %s. You can now correct the '
                  'quantities and finish storing it.') % rec.name)
        return True

    def _block_sorting_for_approval(self, blocked_products):
        """Rule 2 (over threshold_2) or Rule 3 (exact-match mismatch)
        tripped: block finishing and hand the shipment to the warehouse
        manager for explicit approval (manager_approved_sorting)."""
        self.ensure_one()
        names = ', '.join(
            '%s (%.2f/%.2f %s)' % (
                p['product_name'], p['entered'], p['expected'], p['uom_name'])
            for p in blocked_products)
        self.write({
            'state': 'pending_sorting_approval',
            'manager_approved_sorting': False,
        })
        self.message_post(body=_(
            'Sorting blocked and sent for the warehouse manager\'s approval '
            'by %s: %s.') % (self.env.user.name, names))
        manager = self._warehouse_manager_user()
        if manager:
            self.env['recycle.notification'].sudo()._notify_user(
                manager,
                _('Sorting approval needed: %s') % self.name,
                _('%s could not finish sorting shipment %s: %s. Review it '
                  'and approve to unblock.')
                % (self.env.user.name, self.name, names))
            try:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_('Approve sorting reconciliation: %s') % self.name,
                    note=_('%s could not finish sorting shipment %s: %s.')
                    % (self.env.user.name, self.name, names),
                    user_id=manager.id)
            except Exception:
                pass

    def action_approve_sorting_reconciliation(self):
        """Warehouse manager unblocks a shipment that failed Rule 2 or
        Rule 3 — the sorter then finishes it themselves (this action does
        NOT store it directly)."""
        if not self._is_supervisor():
            raise UserError(_(
                'Only the warehouse manager can approve sorting '
                'reconciliation issues.'))
        for rec in self:
            if rec.state != 'pending_sorting_approval':
                raise UserError(_(
                    'Only shipments pending sorting approval can be '
                    'approved here.'))
            rec.write({'state': 'sorting', 'manager_approved_sorting': True})
            rec.message_post(body=_(
                'Sorting reconciliation approved by %s. The sorter can now '
                'finish storing this shipment.') % self.env.user.name)
            if rec.sorter_user_id:
                self.env['recycle.notification'].sudo()._notify_user(
                    rec.sorter_user_id,
                    _('Sorting approved: %s') % rec.name,
                    _('The manager approved shipment %s. You can now '
                      'finish storing it.') % rec.name)
        return True

    def action_finish_sorting(self, shortage_reason=None, shortage_reason_category=None,
                              damage_reason=None):
        """Enforces exactly three reconciliation rules (see
        _sort_reconciliation() for the full breakdown) then stores the
        sorted materials. Returns a list of per-shipment result dicts
        instead of raising for the two outcomes that must persist a
        state change (blocked / reason_required) — raising would roll
        back the very state change the rule requires."""
        results = []
        for rec in self:
            if rec.state != 'sorting':
                raise UserError(_('Shipment is not in sorting state.'))
            rec._check_reservation('sorter_user_id')
            if not rec.line_ids:
                raise UserError(_('Add at least one product line before finishing.'))
            if rec.sort_escalation_state == 'pending' and not rec._is_supervisor():
                raise UserError(_(
                    'This shipment was transferred to the warehouse manager '
                    'and is awaiting review.'))

            recon = rec._sort_reconciliation()

            if not rec._is_supervisor():
                if recon['missing_product_ids']:
                    names = ', '.join(
                        self.env['recycle.product'].sudo().browse(pid).name
                        for pid in recon['missing_product_ids'])
                    raise UserError(_(
                        'You forgot to log these expected materials: %s.'
                    ) % names)
                if recon['extra_product_ids']:
                    names = ', '.join(
                        self.env['recycle.product'].sudo().browse(pid).name
                        for pid in recon['extra_product_ids'])
                    raise UserError(_(
                        'These materials were not declared for this shipment: '
                        '%s. Remove them or check the product.'
                    ) % names)

            # ── Rule 1: no unit-of-measure group may exceed what was
            # declared. Applies ALWAYS — no exception, not even for the
            # warehouse manager. ──
            if recon['rule1_violations']:
                parts = '; '.join(
                    _('%(uom)s: %(entered).2f logged vs %(expected).2f '
                      'declared (%(over).2f over)') % {
                        'uom': v['uom_name'], 'entered': v['entered'],
                        'expected': v['expected'], 'over': v['over_by']}
                    for v in recon['rule1_violations'])
                raise UserError(_(
                    'The quantities you entered exceed what was declared '
                    'for this shipment. %s'
                ) % parts)

            if not rec._is_supervisor() and not rec.manager_approved_sorting:
                # ── Rule 2 (over threshold_2) / Rule 3 (exact mismatch):
                # block and hand off to the manager. ──
                if recon['blocked_products']:
                    rec._block_sorting_for_approval(recon['blocked_products'])
                    results.append({'status': 'blocked', 'shipment_id': rec.id})
                    continue
                # ── Rule 2, reason-required band: a category (+ free text
                # for "other") is mandatory before finishing. ──
                if recon['reason_needed_products']:
                    category = (shortage_reason_category
                                or rec.shortage_reason_category or '').strip()
                    reason = (shortage_reason
                              or rec.weight_shortage_reason or '').strip()
                    if not category or (category == 'other' and not reason):
                        results.append({
                            'status': 'reason_required', 'shipment_id': rec.id,
                            'products': [
                                {'product_id': p['product_id'],
                                 'product_name': p['product_name'],
                                 'pct': p['pct']}
                                for p in recon['reason_needed_products']],
                        })
                        continue
                    rec.weight_shortage_reason = reason
                    rec.shortage_reason_category = category

            # Storage zones are only required once every rule has passed — the
            # sorter (or the manager) assigns them as the final step, right
            # before storing. Each material to be stored must have SOME zone: its
            # own per-line one, or the shipment-wide fallback. A material with
            # neither blocks finishing and is named, so the UI can send the
            # operator back to assign a zone for exactly those.
            to_store = rec.line_ids.filtered(
                lambda l: l.quantity and not l.is_damaged)
            unzoned = to_store.filtered(
                lambda l: not (l.storage_zone_id or rec.storage_zone_id))
            if unzoned:
                names = ', '.join(sorted(set(unzoned.mapped('product_id.name'))))
                raise UserError(_(
                    'These materials still have no storage zone: %s. Assign a '
                    'zone to each (or set one storage zone for the whole '
                    'shipment) before finishing.') % names)
            # Every zone actually used must be a STORAGE zone of this warehouse —
            # a per-line zone pointing elsewhere would scatter stock into a bay
            # that does not belong to the shipment.
            for line in to_store:
                zone = line.storage_zone_id or rec.storage_zone_id
                if zone.zone_type != 'storage' or zone.warehouse_id != rec.warehouse_id:
                    raise UserError(_(
                        'Material "%s" is assigned to "%s", which is not a '
                        'storage zone of this warehouse.')
                        % (line.product_id.name, zone.name))

            # ── Damage is REPORTED here, never carried out here ──────────
            #
            # The sorter records what did not survive, with a reason, and
            # finishes: the good quantities are stored now, and the damaged
            # ones are HELD — neither stored nor written off — until the
            # warehouse manager decides. Damage does NOT block finishing: a
            # sorter must never be left unable to store sound material because a
            # write-off is waiting on someone else. The manager then either
            # approves the write-off (action_approve_damage — recorded as
            # damaged on the shipment, not stored) or rejects it and stores the
            # goods themselves, choosing the zone (action_reject_damage).
            damaged_lines = rec.line_ids.filtered('is_damaged')
            # The description travels WITH the finish now: the sorter types it in
            # the same step, and storing goes ahead. Damage never waits for the
            # manager — the request is filed (below) and the sound materials are
            # stored at once.
            if damage_reason and damage_reason.strip():
                rec.damage_reason = damage_reason.strip()
            if damaged_lines and not (rec.damage_reason or '').strip():
                raise UserError(_(
                    'Give a reason for the damaged materials before finishing.'))

            Stock = self.env['recycle.stock']
            for line in rec.line_ids:
                if line.quantity < 0:
                    raise UserError(_('Line quantities cannot be negative.'))
                # A ZERO line is a record, not a mistake: a graded material may
                # arrive without one of its grades, and zero is how the sorter
                # says "looked for it, none came". Nothing is stored for it.
                if not line.quantity:
                    continue
                if line.is_damaged:
                    # Held for the manager — not stored, not written off yet.
                    continue
                # Each material to ITS OWN zone (per-line), falling back to the
                # shipment-wide zone — the split-across-zones rule made concrete.
                Stock._add_quantity(
                    rec.warehouse_id, line.product_id, line.quantity,
                    condition=line.condition,
                    zone=line.storage_zone_id or rec.storage_zone_id or None)
            vals = {'state': 'sorted', 'sorted_at': fields.Datetime.now(),
                    # Storing happens right here — the graded stock was just
                    # written to its storage zone above — so the "stored" trail
                    # is recorded with the same finish action.
                    'stored_at': fields.Datetime.now(),
                    'stored_by': self.env.user.id,
                    'manager_approved_sorting': False}
            if rec.sort_escalation_state == 'pending':
                vals['sort_escalation_state'] = 'resolved'
            # What happens to the held damage depends on WHO finished:
            #   - a sorter raises the manager's decision now, so it lands in the
            #     "Damaged sorting requests" list (pending);
            #   - a supervisor finishing directly IS the approver, so the
            #     write-off is authorised as it is recorded — no request to
            #     themselves.
            # Either way it is only for damage the manager has not already ruled
            # on (approved/rejected), which is left untouched.
            notify_manager = False
            if (damaged_lines
                    and rec.damage_request_state not in ('approved', 'rejected')):
                if rec._is_supervisor():
                    Damage = self.env['recycle.damage.entry']
                    for line in damaged_lines:
                        if line.quantity > 0:
                            Damage.record_from_sorting(rec, line)
                    vals['damage_request_state'] = 'approved'
                else:
                    vals['damage_request_state'] = 'pending'
                    notify_manager = True
            rec.write(vals)
            if notify_manager:
                rec._notify_damage_request(rec.damage_reason)
            rec.message_post(body=_(
                'Sorting finished by %s: %s usable units (Excellent+Good+Poor) '
                'added to Storage. %s damaged units recorded.'
            ) % (self.env.user.name, rec.total_good_qty, rec.total_damaged_qty))
            # Notify administrators: shipment stored in the storage zone.
            try:
                self.env['recycle.notification'].sudo()._notify_admins(
                    _('Shipment stored'),
                    _('Shipment %s was sorted and stored in the storage zone '
                      'of warehouse %s (%s usable units).') % (
                        rec.name, rec.warehouse_id.name, rec.total_good_qty),
                    notif_type='shipment',
                    related_model='recycle.shipment', related_res_id=rec.id)
            except Exception:
                pass
            # Outbound sync to the NestJS backend (no-op until configured).
            try:
                self.env['recycle.backend.sync'].sudo().sync_shipment(
                    rec, 'stored')
            except Exception:
                pass
            # Stock just GREW. The backend allocates buyer orders from its mirror
            # of these quantities, and until this ping existed the mirror only
            # refreshed when an admin pressed sync — so goods sat on the shelf
            # invisible to the allocator, and buyers were told "out of stock" for
            # material the warehouse was holding.
            try:
                self.env['recycle.backend.sync'].sudo().notify_inventory_changed(
                    rec.warehouse_id)
            except Exception:
                pass
            results.append({'status': 'stored', 'shipment_id': rec.id})
        return results

    # ---------------- Reports ----------------

    def action_print_report(self):
        return self.env.ref(
            'recycle_warehouse.action_report_shipment').report_action(self)


class RecycleShipmentLine(models.Model):
    _name = 'recycle.shipment.line'
    _inherit = ['recycle.grade.mixin']
    _description = 'Shipment Sorted Line'

    shipment_id = fields.Many2one(
        'recycle.shipment', required=True, ondelete='cascade')
    product_id = fields.Many2one(
        'recycle.product', required=True, ondelete='restrict')
    quantity = fields.Float(required=True, default=1.0)
    # Read from the product so the sort-reconciliation logic always knows
    # this line's unit of measure (and whether it tolerates a shortage
    # margin) — see recycle.shipment._sort_reconciliation().
    uom_id = fields.Many2one(
        'recycle.measurement.unit', related='product_id.uom_id',
        store=True, readonly=True)
    # ── Where THIS material is stored ───────────────────────────────────────
    #
    # Per line, so a shipment can be SPLIT across storage zones: excellent PET
    # in one, mixed paper in another. Optional — a line with no zone of its own
    # falls back to the shipment-level `storage_zone_id`, which is how "store the
    # whole shipment in one zone" still works. Storing (`action_finish_sorting`)
    # writes each material to whichever of the two applies, and refuses to finish
    # while any material still has neither.
    storage_zone_id = fields.Many2one(
        'recycle.zone', string='Storage Zone', ondelete='restrict',
        help='Which storage zone this specific material goes to. Leave empty to '
             'use the shipment-wide storage zone.')
    # ── Outcome vs grade — two different questions ──────────────────────────
    #
    # "Damaged" used to be the fourth entry in a fixed grade list, so the sorter
    # said DAMAGED the same way they said GOOD. That conflated two unrelated
    # facts: a GRADE is a quality this material is sold at, while DAMAGE is the
    # decision that this quantity is not sold at all. Once grades became the
    # admin's to name per material, the conflation broke outright — a material
    # graded PREMIUM/STANDARD had no way to say "damaged", and the storing step,
    # which matched the literal string 'damaged', silently stored spoiled goods
    # as sellable stock.
    is_damaged = fields.Boolean(
        string='Damaged', default=False, index=True,
        help='This quantity did not survive sorting. It is written off rather '
             'than stored, and recorded in the warehouse damage log.')
    condition = fields.Char(
        string='Grade', size=30,
        help='Grade this quantity was sorted into. Empty when the material is '
             'ungraded, or when the line is damaged — damaged goods are not '
             'graded, they are written off.')
    condition_label = fields.Char(
        string='Grade Name', compute='_compute_condition_label')

    @api.depends('product_id', 'condition')
    def _compute_condition_label(self):
        Conditions = self.env['recycle.material.condition']
        for line in self:
            line.condition_label = Conditions.label_for(
                line.product_id, line.condition)

    @api.constrains('product_id', 'condition', 'is_damaged')
    def _check_condition(self):
        Conditions = self.env['recycle.material.condition']
        for line in self:
            if not line.product_id:
                continue
            if line.is_damaged:
                # A damaged quantity carries no grade: it is not being sold at
                # any quality, so there is nothing for a grade to say.
                continue
            Conditions.normalize(line.product_id, line.condition)

    @api.constrains('quantity')
    def _check_quantity_not_negative(self):
        """Zero is a record. Below zero is nothing at all.

        A zero line says "this grade was looked for and none arrived", which is
        why zero is accepted everywhere. A negative says nothing — it is a typo
        or a stray minus, and letting one through would subtract from stock at
        storage time, or quietly cancel out a sound line in the same material's
        total. Refused here rather than at storage so it is caught while the
        material is still in front of the sorter.
        """
        for line in self:
            if line.quantity < 0:
                raise ValidationError(_(
                    'A sorted quantity cannot be negative. Enter zero if none '
                    'of this grade arrived.'))

    @api.constrains('product_id', 'quantity', 'shipment_id')
    def _check_not_more_than_declared(self):
        """A material may never be sorted for more than the shipment declared.

        Checked per MATERIAL and on the model, not only per unit at the end.
        The existing rule compares totals per unit of measure when sorting is
        finished; that catches the shipment as a whole but lets one material be
        entered at double while another covers for it — and it only speaks up
        after every line has been typed.

        Refusing at the line means the sorter is told which material and by how
        much, while the material is still in front of them.

        A material NOT declared on this shipment has nothing to exceed, so it is
        left to `_sort_reconciliation`, which reports it as an extra rather than
        blocking the entry outright.
        """
        for line in self:
            shipment = line.shipment_id
            if not shipment or not line.product_id:
                continue

            expected = sum(
                el.expected_qty or 0.0
                for el in shipment.expected_line_ids
                if el.product_id.id == line.product_id.id
            )
            if not expected:
                continue

            entered = sum(
                other.quantity
                for other in shipment.line_ids
                if other.product_id.id == line.product_id.id
            )
            # Float noise: a sorter entering 33.333 three times against 100
            # must not be refused for a millionth of a kilogram.
            if entered - expected > 0.0005:
                raise ValidationError(_(
                    'The shipment declared %(expected)s %(uom)s of "%(product)s", '
                    'and %(entered)s has now been entered. A material cannot be '
                    'sorted for more than was declared.'
                ) % {
                    'expected': round(expected, 3),
                    'entered': round(entered, 3),
                    'uom': line.product_id.uom_id.name or '',
                    'product': line.product_id.name,
                })

    @api.onchange('is_damaged')
    def _onchange_is_damaged(self):
        if self.is_damaged:
            self.condition = False


class RecycleShipmentExpectedLine(models.Model):
    _name = 'recycle.shipment.expected.line'
    _description = 'Shipment Expected Material (declared before arrival)'

    shipment_id = fields.Many2one(
        'recycle.shipment', required=True, ondelete='cascade')
    product_id = fields.Many2one(
        'recycle.product', required=True, ondelete='restrict')
    category_id = fields.Many2one(
        'recycle.product.category', related='product_id.category_id',
        store=True, readonly=True)
    # The unit of measure is a property of the MATERIAL, not something the
    # reception employee picks per shipment — it's read straight from the
    # product so materials can never be mismatched between reception and
    # sorting, and any unit the backend adds in the future works with no
    # code change.
    uom_id = fields.Many2one(
        'recycle.measurement.unit', related='product_id.uom_id',
        store=True, readonly=True)
    expected_qty = fields.Float(string='Expected Quantity')

    @api.constrains('expected_qty')
    def _check_expected_qty(self):
        for rec in self:
            if rec.expected_qty <= 0:
                raise ValidationError(_('Expected quantity must be positive.'))


class RecycleShipmentZoneMovement(models.Model):
    _name = 'recycle.shipment.zone.movement'
    _description = 'Shipment Zone Movement Log'
    _order = 'moved_at desc, id desc'

    shipment_id = fields.Many2one(
        'recycle.shipment', required=True, ondelete='cascade', index=True)
    from_zone_id = fields.Many2one('recycle.zone', string='From Zone')
    to_zone_id = fields.Many2one('recycle.zone', string='To Zone', required=True)
    moved_by = fields.Many2one('res.users', string='Moved By', required=True)
    moved_at = fields.Datetime(string='Moved At', required=True, default=fields.Datetime.now)
