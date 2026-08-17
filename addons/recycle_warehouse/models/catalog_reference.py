# -*- coding: utf-8 -*-
"""Reference data mirrored FROM the NestJS backend.

The admin creates measurement units and material conditions in the backend
(they are dynamic, admin-managed tables there). Odoo mirrors them so its own
screens — sorting, stock, shipment grading — can label a quantity with the same
unit and grade the backend uses.

CONTRACT with the backend (do not rename these fields — `odoo.service.ts`
writes them by name):
  recycle.measurement.unit : name, code, allows_tolerance
  recycle.material.condition: name, code, sort_order

Both were being pushed by the backend before these models existed, so every
create/update/delete failed with a 404 and the mirror stayed empty.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class RecycleMeasurementUnit(models.Model):
    _name = 'recycle.measurement.unit'
    _description = 'Measurement Unit (mirrored from backend)'
    _order = 'name'

    name = fields.Char(required=True)
    code = fields.Char(
        required=True, index=True,
        help='Stable identifier used by the backend (e.g. KG, PIECE).')
    allows_tolerance = fields.Boolean(
        'Allows Tolerance', default=False,
        help='Weight-like units accept a small mismatch between the declared '
             'and the received quantity; countable units must match exactly.')
    active = fields.Boolean(default=True)

    _code_uniq = models.Constraint(
        'unique(code)', 'A measurement unit with this code already exists.')


class RecycleProvince(models.Model):
    """Governorates, mirrored from the backend's `provinces` table.

    This replaces the old hard-coded Selection on the warehouse: the admin now
    manages governorates in ONE place (the backend) and Odoo follows. A real
    table also means a warehouse's governorate can be renamed without touching
    code, and the two systems can never disagree on the list.

    CONTRACT (written by `odoo.service.upsertProvince`):
      backend_province_id (the backend uuid — the match key), name_en, name_ar
    """
    _name = 'recycle.province'
    _description = 'Governorate (mirrored from backend)'
    _rec_name = 'name_ar'
    _order = 'name_ar'

    backend_province_id = fields.Char(
        'Backend ID', required=True, index=True,
        help='UUID of the province row in the NestJS backend — the match key '
             'used by every sync so a rename never creates a duplicate.')
    name_en = fields.Char('Name (EN)', required=True)
    name_ar = fields.Char('Name (AR)', required=True)
    active = fields.Boolean(default=True)

    _backend_uniq = models.Constraint(
        'unique(backend_province_id)',
        'This province is already mirrored.')

    def name_get(self):
        return [(r.id, r.name_ar or r.name_en) for r in self]

    LEGACY_PREFIX = 'legacy:'

    @api.model
    def backend_upsert(self, backend_id, name_en, name_ar):
        """Create or update by backend id (idempotent — the backend replays a
        push after a connection drop, and the reconcile cron replays them all).

        If no row carries this uuid yet, a placeholder row left by the
        Selection→table migration (`backend_province_id = 'legacy:<key>'`) with
        the same name is ADOPTED: its placeholder is rewritten to the real uuid.
        Without that step the first backend push would create a second
        'Damascus' next to the one every existing warehouse points at.
        """
        Province = self.sudo().with_context(active_test=False)
        rec = Province.search([('backend_province_id', '=', backend_id)], limit=1)
        if not rec:
            rec = Province.search([
                ('backend_province_id', '=like', self.LEGACY_PREFIX + '%'),
                '|', ('name_en', '=ilike', name_en or ''),
                     ('name_ar', '=ilike', name_ar or ''),
            ], limit=1)
            if rec:
                rec.write({'backend_province_id': backend_id})

        vals = {'name_en': name_en, 'name_ar': name_ar, 'active': True}
        if rec:
            rec.write(vals)
            return rec.id
        vals['backend_province_id'] = backend_id
        return Province.create(vals).id

    @api.model
    def backend_archive(self, backend_id):
        """The backend deleted a province. It is ARCHIVED here, never deleted —
        warehouses may still point at it and that history must survive."""
        rec = self.sudo().search([('backend_province_id', '=', backend_id)], limit=1)
        if rec:
            rec.active = False
        return True

    @api.model
    def resolve_by_backend_id(self, backend_id):
        """Backend uuid → Odoo id. Refuses an unknown id loudly rather than
        silently dropping the governorate off the record."""
        rec = self.sudo().with_context(active_test=False).search(
            [('backend_province_id', '=', backend_id)], limit=1)
        if not rec:
            raise UserError(_(
                'Unknown governorate id "%s". Sync the governorates first.',
                backend_id))
        return rec.id

    @api.model
    def resolve_by_name(self, name):
        """Governorate NAME (Arabic or English, any case) → Odoo id.

        This is what lets the backend send the plain name it stores on a
        warehouse: no key-conversion table on either side, and a rename in the
        backend keeps resolving because the name arrives from the same source
        that renamed it.
        """
        name = (name or '').strip()
        if not name:
            return False
        rec = self.sudo().with_context(active_test=False).search([
            '|', ('name_ar', '=ilike', name), ('name_en', '=ilike', name),
        ], limit=1)
        if not rec:
            raise UserError(_(
                'Unknown governorate "%s". Sync the governorates first.', name))
        return rec.id

    @api.model
    def backend_sync_all(self, provinces):
        """Full replace-in-place from the backend's province list.

        Called on backend startup and by its reconcile cron, so a push lost
        while Odoo was down still converges. Anything Odoo holds that the
        backend no longer lists is archived (not deleted) — including
        migration placeholders nothing adopted.

        `provinces`: [{'id': uuid, 'name_en': ..., 'name_ar': ...}, ...]
        """
        seen_ids = []
        for row in provinces or []:
            backend_id = row.get('id')
            if not backend_id:
                continue
            seen_ids.append(self.backend_upsert(
                backend_id, row.get('name_en'), row.get('name_ar')))

        stale = self.sudo().search([('id', 'not in', seen_ids)])
        if stale:
            stale.write({'active': False})
        return {'synced': len(seen_ids), 'archived': len(stale)}


class RecycleProductConditionPrice(models.Model):
    """Per-condition price of a product for ONE buyer tier.

    A product is not worth the same in every grade: 'EXCELLENT' PET pays more
    than 'DAMAGED'. Odoo invoices factories and free facilities from these
    lines, so the backend replaces the whole set for a (product, tier) pair on
    every pricing change.

    A material may also have NO conditions at all — then the backend prices it
    once per tier and sends that row with an EMPTY `condition_code`. Such a row
    is the material's plain price for that tier.

    CONTRACT (written by `odoo.service.replaceConditionPrices`):
      product_id, tier, condition_code, price
    The backend also `search`es on (product_id, tier) then `unlink`s before
    re-creating — so the replacement is atomic from its point of view.
    """
    _name = 'recycle.product.condition.price'
    _description = 'Product Price per Condition and Tier'
    _order = 'product_id, tier, condition_code'

    product_id = fields.Many2one(
        'recycle.product', required=True, ondelete='cascade', index=True)
    tier = fields.Selection([
        ('factory', 'Factory'),
        ('free_facility', 'Free Facility'),
    ], required=True, index=True,
        help='Which buyer tier this price applies to.')
    condition_code = fields.Char(
        index=True,
        help='Material-condition code (mirrors recycle.material.condition.code). '
             'Empty means the material has no conditions and this is its plain '
             'price for the tier.')
    condition_name = fields.Char(
        string='Condition', compute='_compute_condition_name',
        help='Human label of the condition, resolved from the mirrored '
             'material-condition list.')
    price = fields.Float('Price', default=0.0)

    # ── Offer mirror ──────────────────────────────────────────────────
    #
    # The backend owns offers entirely; this is a READ-ONLY reflection so the
    # Odoo admin can see that a material is currently discounted and by how
    # much. Without it the price sheet here showed the list price while the
    # apps were selling at another number, and nothing on this screen said so.
    #
    # `price` above deliberately keeps meaning the LIST price. Overwriting it
    # with the offer would lose the very thing an administrator needs to see —
    # what it was before — and would silently become the new list price the
    # moment the offer expired and the mirror stopped being refreshed.
    offer_price = fields.Float(
        'Offer Price', default=0.0,
        help='Discounted price currently advertised by the app. Zero means no '
             'live offer on this line.')
    offer_valid_until = fields.Datetime(
        'Offer Ends',
        help='When the discount lapses and the list price applies again. '
             'Empty with an offer present means it runs until withdrawn.')
    offer_percentage = fields.Float(
        'Offer %', default=0.0,
        help='How much the offer takes off, as a percentage of the list price. '
             'Sent by the backend rather than derived here: it is computed '
             'against the tier the offer actually faces, and re-deriving it '
             'from two rounded figures on this side would drift from the '
             'number the buyer is shown in the app.')
    # NOT stored, and that is the whole point.
    #
    # Both of these depend on the CLOCK — an offer is live until its end date
    # passes — and the clock is not a field, so it can never appear in
    # `@api.depends`. Stored, Odoo recomputes them only when `price`,
    # `offer_price` or `offer_valid_until` is written, which means an offer that
    # simply ran out kept showing as live: measured five minutes after lapsing,
    # `has_offer` was still True and the price still struck through. The
    # discount was over and the screen said it was running.
    #
    # Computed on read, they are correct at the instant they are looked at. The
    # cost is that they cannot be searched or ordered in SQL — neither of which
    # anything here does; the list only styles a row by `has_offer`.
    has_offer = fields.Boolean(
        'On Offer', compute='_compute_offer_display',
        help='True while a discount is live on this exact tier and condition.')
    price_display = fields.Char(
        'Price', compute='_compute_offer_display',
        help='List price struck through beside the offer price when one is '
             'live, so the old figure stays readable next to the new one.')

    _line_uniq = models.Constraint(
        'unique(product_id, tier, condition_code)',
        'This product already has a price for that tier and condition.')

    # No @api.depends: the values turn on the CLOCK, not on a field. Declaring
    # dependencies here would only invite somebody to re-add store=True.
    def _compute_offer_display(self):
        """One string carrying BOTH numbers, and a flag to style it by.

        An offer is a change of price, and a change is two values — showing
        only the new one answers "what does it cost" while losing "what did it
        cost", which is the question an administrator opens this screen with.

        The strike-through is done with combining characters rather than markup
        because this renders in a plain list cell, where HTML would be escaped
        and shown literally.
        """
        for rec in self:
            live = bool(rec.offer_price) and rec.offer_price > 0
            if live and rec.offer_valid_until:
                live = rec.offer_valid_until > fields.Datetime.now()
            rec.has_offer = live
            if not live:
                rec.price_display = '%.2f' % (rec.price or 0.0)
                continue
            struck = ''.join(
                ch + '̶' for ch in ('%.2f' % (rec.price or 0.0)))
            rec.price_display = '%s  →  %.2f' % (struck, rec.offer_price)

    @api.depends('condition_code')
    def _compute_condition_name(self):
        """Resolve codes to names in ONE query for the whole recordset — the
        price sheet of a material renders every line at once."""
        # Grades belong to a material, so a code alone cannot name one: two
        # materials may each have a 'GOOD'. The lookup is keyed by the pair.
        pairs = [(r.product_id.id, r.condition_code)
                 for r in self if r.condition_code]
        names = {}
        if pairs:
            conditions = self.env['recycle.material.condition'].sudo(
            ).with_context(active_test=False).search([
                ('product_id', 'in', [p for p, _c in pairs]),
                ('code', 'in', [c for _p, c in pairs]),
            ])
            names = {(c.product_id.id, c.code): c.name for c in conditions}
        for rec in self:
            if not rec.condition_code:
                rec.condition_name = _('No condition (plain price)')
            else:
                rec.condition_name = names.get(
                    (rec.product_id.id, rec.condition_code),
                    rec.condition_code)


class RecycleMaterialCondition(models.Model):
    """A grade that belongs to ONE material.

    Grades are not a shared vocabulary: the words that describe scrap paper say
    nothing useful about copper. Each material carries its own, and a material
    may have none at all — which is a normal answer, not missing setup.

    That is what lets the sorting screen offer only the grades of the material
    actually in front of the employee, instead of a global list where most
    entries are meaningless for the item being sorted.
    """
    _name = 'recycle.material.condition'
    _description = 'Material Condition / Grade (mirrored from backend)'
    _order = 'product_id, sort_order, name'

    product_id = fields.Many2one(
        'recycle.product', string='Material', required=True,
        ondelete='cascade', index=True,
        help='The material this grade belongs to.')
    name = fields.Char(required=True)
    code = fields.Char(
        required=True, index=True,
        help='Identifier of this grade WITHIN its material (e.g. EXCELLENT). '
             'Two materials may each have their own GOOD — they are different '
             'grades of different things.')
    sort_order = fields.Integer(
        'Sort Order', default=0,
        help='Display order within the material — lowest first, best first.')
    active = fields.Boolean(default=True)

    _code_uniq = models.Constraint(
        'unique(product_id, code)',
        'This material already has a grade with that code.')

    # ------------------------------------------------------------------
    # The one place the rest of the module asks about grades.
    #
    # Everything that carries a condition — stock lines, order lines, sorted
    # shipment lines, damage reports — used to read a hard-coded Selection of
    # four English words. That list could not answer the only question that
    # matters: does THIS material have grades, and which ones? A material the
    # admin gave no grades still offered four, and a material whose grades the
    # admin named differently could never hold stock at all.
    #
    # Every helper below is keyed by the MATERIAL. A code on its own is not a
    # grade: two materials may each have a 'GOOD', and they are different grades
    # of different things.
    # ------------------------------------------------------------------
    @api.model
    def _rows_for(self, product):
        """Active grades of one material, best first."""
        if not product:
            return self.browse()
        return self.sudo().search(
            [('product_id', '=', product.id), ('active', '=', True)],
            order='sort_order, id')

    @api.model
    def codes_for(self, product):
        """Grade codes of a material, best first. Empty list = ungraded."""
        return self._rows_for(product).mapped('code')

    @api.model
    def selection_for(self, product):
        """[(code, name)] — what a picker for this material should offer."""
        return [(r.code, r.name) for r in self._rows_for(product)]

    @api.model
    def has_grades(self, product):
        """The question that decides whether a quantity needs a grade at all."""
        return bool(self.codes_for(product))

    @api.model
    def label_for(self, product, code):
        """Human name of one grade, falling back to the raw code.

        Falls back rather than raising: a label is needed most often inside an
        error message, and a missing translation must never replace the error
        the user was about to read.
        """
        if not code:
            return _('No grade')
        row = self._rows_for(product).filtered(lambda r: r.code == code)
        return row[0].name if row else code

    @api.model
    def rank_for(self, product, code):
        """Position of a grade within its material — lower is better.

        Returns a large number for an unknown code so it sorts last instead of
        silently ranking as the best.
        """
        for index, row in enumerate(self._rows_for(product)):
            if row.code == code:
                return index
        return 10 ** 6

    @api.model
    def normalize(self, product, code):
        """The grade a record should store for this material, or False.

        This is the gate every write goes through, and it enforces the two rules
        that make grades trustworthy:

          * an UNGRADED material may not carry a grade — there is nothing for
            one to mean, and accepting it would let a buyer believe they bought
            a quality that was never recorded;
          * a GRADED material must carry one of ITS OWN grades — accepting a
            code borrowed from another material is exactly how an order for one
            thing gets filled with another.

        Codes are compared upper-case because that is the form the backend
        authors them in; accepting 'good' for 'GOOD' quietly created a second,
        unmatchable grade.
        """
        normalized = (code or '').strip().upper()
        valid = self.codes_for(product)

        if not valid:
            if normalized:
                raise ValidationError(_(
                    'Material "%(product)s" has no grades, so no grade can be '
                    'recorded for it.') % {'product': product.name})
            return False

        if not normalized:
            raise ValidationError(_(
                'Material "%(product)s" is graded — choose one of: %(codes)s.'
            ) % {'product': product.name, 'codes': ', '.join(valid)})

        if normalized not in valid:
            raise ValidationError(_(
                'Unknown grade "%(code)s" for material "%(product)s". Its '
                'grades are: %(codes)s.') % {
                    'code': code, 'product': product.name,
                    'codes': ', '.join(valid)})
        return normalized

    @api.model
    def normalize_optional(self, product, code):
        """Like `normalize`, but tolerates a missing grade on a graded material.

        Used where a grade genuinely may be unknown — stock that arrived but has
        not been sorted yet is real, and refusing to record it would lose the
        quantity rather than the uncertainty.
        """
        normalized = (code or '').strip().upper()
        if not normalized:
            return False
        return self.normalize(product, normalized)
