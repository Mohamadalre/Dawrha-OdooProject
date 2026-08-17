# -*- coding: utf-8 -*-
"""Shared behaviour for every record that carries a material grade.

Four models store a grade code: stock lines, order lines, sorted shipment lines
and damage reports. Each one needs the same two things, and getting either
slightly different on one of them is how the four drift apart:

  * the code is stored in the material's OWN spelling (upper-case, as the
    backend authors it), and
  * it is checked against the grades that material actually has.

Validation alone is not enough, and that distinction matters. A constraint that
only *checks* lets 'premium' be stored next to 'PREMIUM' — both pass, because
the check normalises before comparing, but the two rows can never match each
other again. The value has to be REWRITTEN on the way in, which is what this
mixin does.
"""
from odoo import api, fields, models


class RecycleGradeMixin(models.AbstractModel):
    _name = 'recycle.grade.mixin'
    _description = 'Carries a per-material grade code'

    # Subclasses declare `condition` themselves (labels and help differ), and
    # all of them name the material field `product_id`.
    _grade_product_field = 'product_id'

    def _grade_product(self, vals=None):
        """The material a grade would belong to, from vals or from the record."""
        field = self._grade_product_field
        if vals and vals.get(field):
            return self.env['recycle.product'].browse(int(vals[field]))
        return self[field] if self else self.env['recycle.product']

    @api.model
    def _normalize_grade_vals(self, vals, record=None):
        """Rewrite `condition` in-place into the material's own spelling."""
        if 'condition' not in vals:
            return vals
        product = None
        field = self._grade_product_field
        if vals.get(field):
            product = self.env['recycle.product'].browse(int(vals[field]))
        elif record is not None:
            product = record[field]
        if not product:
            return vals
        vals['condition'] = self.env['recycle.material.condition'
                                     ].normalize_optional(product, vals['condition'])
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._normalize_grade_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        if 'condition' in vals:
            # Per record: two records in the same call may hold different
            # materials, and a grade is only meaningful against its own.
            for record in self:
                one = dict(vals)
                record._normalize_grade_vals(one, record=record)
                super(RecycleGradeMixin, record).write(one)
            return True
        return super().write(vals)
