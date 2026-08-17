# -*- coding: utf-8 -*-
from odoo import fields, models


class UomUom(models.Model):
    _inherit = 'uom.uom'

    allows_tolerance = fields.Boolean(
        string='Allows Tolerance Margin?',
        default=True,
        help='Enable for physically divisible units (kg, liter) where small '
             'natural variance occurs. Disable for indivisible units (piece, '
             'box) where the count must match exactly with no exceptions.')
