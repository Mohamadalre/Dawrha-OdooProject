# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sorting_tolerance_threshold_1 = fields.Float(
        string='Auto-accepted shortage per material (%)',
        config_parameter='warehouse.sorting_tolerance_threshold_1',
        default=3.0,
        help='Any shortage for a single material at or below this value is '
             'accepted automatically, with no warning. Represents the '
             'natural tolerance margin (humidity, dust, minor residue).')
    sorting_tolerance_threshold_2 = fields.Float(
        string='Maximum shortage per material before manager approval (%)',
        config_parameter='warehouse.sorting_tolerance_threshold_2',
        default=15.0,
        help='Any shortage for a single material above the first threshold '
             'and up to this value is accepted but requires a mandatory '
             'reason. Any shortage beyond this value blocks finishing the '
             'sorting and requires the warehouse manager\'s approval.')
