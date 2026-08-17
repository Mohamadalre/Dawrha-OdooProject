# -*- coding: utf-8 -*-
"""The warehouse's record of what was lost, and when.

Material is written off in two quite different moments, and before this model
neither of them left anything countable behind:

  SORTING  — the shipment arrived and part of it did not survive. The quantity
             was recorded as a PERCENTAGE on the shipment and nowhere else, so
             the loss existed only inside one shipment's own paperwork.
  STORAGE  — material already on the shelf spoiled. The approved report deducted
             the stock and then said nothing further, so the deduction was
             visible as a smaller number but never as a loss.

In both cases the quantity left the warehouse and no row said so. That makes the
one question an administrator actually asks unanswerable: *how much did each
warehouse lose, of what, and when?* A ledger answers it directly, and because
every entry names its source and its origin record, any figure on the summary
screen can be traced back to the shipment or the report that produced it.

Entries are append-only. A correction is a new entry, never an edit: a loss that
can be quietly rewritten afterwards is not evidence of anything.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError

DAMAGE_SOURCES = [
    ('sorting', 'Sorting (incoming shipment)'),
    ('storage', 'Storage (already stocked)'),
]


class RecycleDamageEntry(models.Model):
    _name = 'recycle.damage.entry'
    _description = 'Warehouse Damage Log'
    _order = 'occurred_at desc, id desc'
    _rec_name = 'display_name'

    warehouse_id = fields.Many2one(
        'recycle.warehouse', string='Warehouse', required=True, index=True,
        ondelete='cascade')
    product_id = fields.Many2one(
        'recycle.product', string='Material', required=True, index=True,
        ondelete='restrict')
    uom_id = fields.Many2one(
        'recycle.measurement.unit', related='product_id.uom_id',
        store=True, readonly=True)
    # The grade the material was FILED UNDER when it was lost — not a grade of
    # damage. Empty for an ungraded material, and for anything written off
    # during sorting before a grade was ever assigned.
    condition = fields.Char(string='Grade', size=30)
    condition_label = fields.Char(
        string='Grade Name', compute='_compute_condition_label')
    quantity = fields.Float(string='Quantity', required=True)
    source = fields.Selection(
        DAMAGE_SOURCES, string='Source', required=True, index=True,
        help='Where the loss happened: during sorting of an incoming shipment, '
             'or to material already in storage.')
    occurred_at = fields.Datetime(
        string='Damaged At', required=True, index=True,
        default=fields.Datetime.now,
        help='When the loss was recorded — the sorting was finished, or the '
             'manager approved the storage report.')
    recorded_by = fields.Many2one(
        'res.users', string='Recorded By', required=True,
        default=lambda self: self.env.user.id)
    reason = fields.Text(string='Reason')

    # Provenance. Exactly one is set, and it is what makes a summary figure
    # traceable back to the paperwork that produced it.
    shipment_id = fields.Many2one(
        'recycle.shipment', string='From Shipment', ondelete='set null',
        index=True)
    report_id = fields.Many2one(
        'recycle.stock.damage.report', string='From Report',
        ondelete='set null', index=True)

    display_name = fields.Char(compute='_compute_display_name')

    @api.depends('product_id', 'condition')
    def _compute_condition_label(self):
        Conditions = self.env['recycle.material.condition']
        for rec in self:
            rec.condition_label = Conditions.label_for(
                rec.product_id, rec.condition)

    @api.depends('product_id', 'quantity', 'occurred_at')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s — %s %s' % (
                rec.product_id.name or '',
                rec.quantity,
                rec.uom_id.name or '')

    # ------------------------------------------------------------------
    # Append-only
    # ------------------------------------------------------------------
    def write(self, vals):
        """Refuse edits to anything that carries meaning.

        A ledger whose figures can be adjusted after the fact proves nothing. A
        mistake is corrected by recording the correction, which leaves both the
        error and the fix visible.
        """
        protected = {'warehouse_id', 'product_id', 'condition', 'quantity',
                     'source', 'occurred_at', 'shipment_id', 'report_id'}
        touched = protected.intersection(vals)
        # Refused for EVERYONE, superuser included. An `env.su` exemption would
        # be no protection at all here: Odoo treats uid 1 as superuser
        # unconditionally, so the administrator — the one person with a motive
        # to adjust a loss figure — would be the only one able to.
        if touched:
            raise UserError(_(
                'The damage log cannot be edited (%s). Record a new entry '
                'instead — a loss that can be rewritten afterwards is not a '
                'record of anything.') % ', '.join(sorted(touched)))
        return super().write(vals)

    def unlink(self):
        raise UserError(_(
            'Damage log entries cannot be deleted. They are what the '
            'warehouse loss figures are built from.'))

    # ------------------------------------------------------------------
    # The two ways an entry comes to exist
    # ------------------------------------------------------------------
    @api.model
    def record_from_sorting(self, shipment, line):
        """A sorted line that did not survive."""
        if line.quantity <= 0:
            return self.browse()
        return self.sudo().create({
            'warehouse_id': shipment.warehouse_id.id,
            'product_id': line.product_id.id,
            # Damaged goods carry no grade — they are not being sold at any
            # quality — but an ungraded line may still have one recorded if the
            # sorter graded it before deciding it was a write-off.
            'condition': line.condition or False,
            'quantity': line.quantity,
            'source': 'sorting',
            'occurred_at': fields.Datetime.now(),
            'recorded_by': self.env.user.id,
            'reason': shipment.damage_reason or False,
            'shipment_id': shipment.id,
        })

    @api.model
    def record_from_report(self, report):
        """An approved storage damage report."""
        return self.sudo().create({
            'warehouse_id': report.warehouse_id.id,
            'product_id': report.product_id.id,
            'condition': report.condition or False,
            'quantity': report.quantity,
            'source': 'storage',
            'occurred_at': fields.Datetime.now(),
            'recorded_by': self.env.user.id,
            'reason': report.reason or False,
            'report_id': report.id,
        })

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------
    @api.model
    def summary_by_warehouse(self, warehouse_ids=None, date_from=None,
                             date_to=None):
        """Damage totals per warehouse and material, for the admin screen.

        Aggregated in the database rather than in Python: the answer is a
        handful of rows however many entries stand behind it, and an
        administrator looking at a year of losses should not pay for reading
        every one of them into memory.
        """
        domain = []
        if warehouse_ids:
            domain.append(('warehouse_id', 'in', warehouse_ids))
        if date_from:
            domain.append(('occurred_at', '>=', date_from))
        if date_to:
            domain.append(('occurred_at', '<=', date_to))

        rows = self.sudo().read_group(
            domain,
            fields=['quantity:sum'],
            groupby=['warehouse_id', 'product_id', 'source'],
            lazy=False)

        out = []
        for row in rows:
            out.append({
                'warehouse_id': row['warehouse_id'][0] if row['warehouse_id'] else None,
                'warehouse_name': row['warehouse_id'][1] if row['warehouse_id'] else '',
                'product_id': row['product_id'][0] if row['product_id'] else None,
                'product_name': row['product_id'][1] if row['product_id'] else '',
                'source': row['source'],
                'quantity': row['quantity'],
                'entries': row['__count'],
            })
        return out

    @api.model
    def by_shipment(self, warehouse_ids=None, date_from=None, date_to=None,
                    limit=200):
        """Damage grouped by the SHIPMENT it came off, with its lines.

        The summary answers "how much did this warehouse lose, of what"; this
        answers the question an administrator asks next and could not ask
        before — *which delivery was this, who sorted it, and what exactly did
        not survive?* A total with no shipment behind it cannot be queried,
        disputed, or charged back to anyone.

        Storage losses are deliberately absent: they have no shipment, and
        padding the list with rows that cannot answer the question would make
        it look answered.

        Read as the CALLING USER, not as sudo. A warehouse manager asking this
        gets their own warehouse because the record rules say so, and no
        argument passed from a browser can widen that.
        """
        domain = [('source', '=', 'sorting'), ('shipment_id', '!=', False)]
        if warehouse_ids:
            domain.append(('warehouse_id', 'in', warehouse_ids))
        if date_from:
            domain.append(('occurred_at', '>=', date_from))
        if date_to:
            domain.append(('occurred_at', '<=', date_to))

        entries = self.search(domain, limit=limit)

        grouped = {}
        order = []
        for entry in entries:
            shipment = entry.shipment_id
            row = grouped.get(shipment.id)
            if row is None:
                row = grouped[shipment.id] = {
                    'shipment_id': shipment.id,
                    'shipment_name': shipment.name or '',
                    'warehouse_id': entry.warehouse_id.id,
                    'warehouse_name': entry.warehouse_id.name or '',
                    'driver_name': shipment.driver_name or '',
                    'sorter_name': shipment.sorter_user_id.name or '',
                    'state': shipment.state,
                    'damage_request_state': shipment.damage_request_state,
                    'damage_reason': shipment.damage_reason or '',
                    'damage_reject_reason': shipment.damage_reject_reason or '',
                    'occurred_at': fields.Datetime.to_string(entry.occurred_at),
                    # Totalled per UNIT, because kilograms and pieces do not
                    # add up and a single figure covering both would be a
                    # number nobody could write a unit beside.
                    'totals': {},
                    'lines': [],
                }
                order.append(row)
            row['lines'].append({
                'entry_id': entry.id,
                'product_id': entry.product_id.id,
                'product_name': entry.product_id.name or '',
                'condition': entry.condition or '',
                'condition_label': entry.condition_label or '',
                'quantity': entry.quantity,
                'uom_name': entry.uom_id.name or '',
                'reason': entry.reason or '',
                'recorded_by': entry.recorded_by.name or '',
            })
            uom = entry.uom_id.name or ''
            row['totals'][uom] = row['totals'].get(uom, 0.0) + entry.quantity

        for row in order:
            row['totals'] = [
                {'uom_name': uom, 'quantity': round(qty, 3)}
                for uom, qty in sorted(row['totals'].items())
            ]
        return order
