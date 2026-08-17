# -*- coding: utf-8 -*-
"""Delivery pricing — authored HERE, in Odoo, by the administrator.

Odoo owns the fleet (trucks, drivers, shifts), so it also owns what a delivery
costs. The NestJS backend keeps a read-only mirror and quotes from it, which is
what lets a buyer's cart show a delivery estimate without an RPC round-trip —
and without the cart breaking whenever Odoo is briefly unreachable.

Only FACTORY buyers can request delivery; free facilities always collect their
own goods, so no tariff ever applies to them.

Resolution is most-specific-wins: a tariff on the warehouse beats one on its
governorate, which beats the global one. That is deliberate — a remote
warehouse can be priced differently without touching anything else.
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

TARIFF_SCOPES = [
    ('warehouse', 'This Warehouse'),
    ('province', 'Governorate'),
    ('global', 'All Warehouses'),
]

# Lower number = more specific. Used by both sides to pick a winner.
SCOPE_SPECIFICITY = {'warehouse': 0, 'province': 1, 'global': 2}


class RecycleDeliveryTariff(models.Model):
    _name = 'recycle.delivery.tariff'
    _description = 'Delivery Tariff'
    _inherit = ['mail.thread']
    _order = 'scope, id'

    name = fields.Char(
        compute='_compute_name', store=True,
        help='Readable label built from the scope — nothing to type.')
    scope = fields.Selection(
        TARIFF_SCOPES, required=True, default='global', tracking=True,
        help='Which deliveries this tariff prices. The most specific matching '
             'tariff wins: warehouse, then governorate, then global.')
    warehouse_id = fields.Many2one(
        'recycle.warehouse', string='Warehouse', ondelete='cascade', index=True,
        tracking=True)
    province_id = fields.Many2one(
        'recycle.province', string='Governorate', ondelete='cascade',
        index=True, tracking=True)
    base_fee = fields.Float(
        string='Base Fee', default=0.0, required=True, tracking=True,
        help='Charged once per delivery, before distance.')
    rate_per_km = fields.Float(
        string='Rate per km', default=0.0, required=True, tracking=True,
        help='Multiplied by the road distance from the warehouse to the buyer.')
    min_fee = fields.Float(
        string='Minimum Fee', default=0.0, tracking=True,
        help='Floor for the whole delivery. 0 = no floor.')
    currency = fields.Char(default='JOD', required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)

    _positive_amounts = models.Constraint(
        'CHECK (base_fee >= 0 AND rate_per_km >= 0 AND min_fee >= 0)',
        'Delivery amounts cannot be negative.')

    @api.depends('scope', 'warehouse_id', 'province_id')
    def _compute_name(self):
        for rec in self:
            if rec.scope == 'warehouse':
                rec.name = _('Warehouse: %s') % (rec.warehouse_id.name or '—')
            elif rec.scope == 'province':
                rec.name = _('Governorate: %s') % (rec.province_id.name_ar or '—')
            else:
                rec.name = _('All warehouses')

    @api.constrains('scope', 'warehouse_id', 'province_id')
    def _check_scope_target(self):
        """A scope without its target would silently price nothing, so it is
        refused rather than stored as a tariff that can never match."""
        for rec in self:
            if rec.scope == 'warehouse' and not rec.warehouse_id:
                raise ValidationError(_('Choose the warehouse this tariff applies to.'))
            if rec.scope == 'province' and not rec.province_id:
                raise ValidationError(_('Choose the governorate this tariff applies to.'))
            if rec.scope == 'global' and (rec.warehouse_id or rec.province_id):
                raise ValidationError(_(
                    'A global tariff must not target a specific warehouse or '
                    'governorate — narrow the scope instead.'))
            duplicate = self.with_context(active_test=False).search_count([
                ('id', '!=', rec.id),
                ('scope', '=', rec.scope),
                ('warehouse_id', '=', rec.warehouse_id.id),
                ('province_id', '=', rec.province_id.id),
            ])
            if duplicate:
                raise ValidationError(_(
                    'A tariff for this scope already exists — edit it instead '
                    'of adding a second one.'))

    # ------------------------------------------------------------------
    # Mirror push (Odoo -> backend)
    # ------------------------------------------------------------------
    # Every write pings the backend, which then RE-READS the whole (tiny) list.
    # A ping rather than a diff: the list is small, the re-read is idempotent,
    # and a lost ping is repaired by the backend's reconcile cron instead of
    # leaving a half-applied change behind.
    def _ping_backend(self):
        try:
            self.env['recycle.backend.sync'].sudo().sync_delivery_tariffs()
        except Exception:
            # Never let the mirror push block the admin's edit — the cron
            # reconciles.
            pass

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._ping_backend()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._ping_backend()
        return res

    def unlink(self):
        res = super().unlink()
        self._ping_backend()
        return res

    # ------------------------------------------------------------------
    # Read side (consumed by the backend mirror sync)
    # ------------------------------------------------------------------
    @api.model
    def export_for_backend(self):
        """The whole tariff list in the shape the backend mirrors.

        `province_backend_id` travels instead of the Odoo province id so the
        backend can link the row to its own `provinces` table directly.
        """
        rows = self.sudo().with_context(active_test=False).search([])
        return [{
            'odoo_id': r.id,
            'scope': r.scope,
            'odoo_warehouse_id': r.warehouse_id.id or None,
            'province_backend_id': r.province_id.backend_province_id or None,
            'base_fee': r.base_fee,
            'rate_per_km': r.rate_per_km,
            'min_fee': r.min_fee,
            'currency': r.currency,
            'active': r.active,
        } for r in rows]
