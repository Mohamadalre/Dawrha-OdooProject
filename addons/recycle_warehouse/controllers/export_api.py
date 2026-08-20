# -*- coding: utf-8 -*-
"""Admin data exports — shipments and orders as Excel, one shipment as PDF.

Kept apart from dashboard_api.py because these are FILE downloads (`type='http'`
returning a binary body), not the JSON-RPC the dashboard speaks everywhere else.
All three are admin-only, checked the same way the dashboard's admin routes are.
"""
import io
import logging
import os

import pytz

from odoo import http, fields
from odoo.http import request, content_disposition
from odoo.modules.module import get_module_path

_logger = logging.getLogger(__name__)

try:
    import xlsxwriter
except ImportError:  # pragma: no cover - the base image ships it
    xlsxwriter = None

# The Dawrha app logo, stamped at the top of every exported report.
_LOGO_REL = 'static/src/img/Logo.png'


def _logo_path():
    """Absolute path to the app logo, or None if it cannot be resolved — the
    export must never fail just because the logo is missing."""
    try:
        base = get_module_path('recycle_warehouse')
        path = os.path.join(base, _LOGO_REL)
        return path if os.path.exists(path) else None
    except Exception:  # pragma: no cover - defensive
        return None


class RecycleExportController(http.Controller):

    # ------------------------------------------------------------------
    def _is_admin(self):
        return request.env.user.has_group('recycle_warehouse.group_recycle_admin')

    def _forbidden(self):
        return request.make_response('Forbidden', status=403)

    def _dt(self, value):
        """A stored (UTC) datetime as a readable string in the user's timezone."""
        if not value:
            return ''
        tz = pytz.timezone(request.env.user.tz or 'UTC')
        return pytz.utc.localize(value).astimezone(tz).strftime('%Y-%m-%d %H:%M')

    def _xlsx(self, rows, headers, sheet_name, filename):
        """Build a one-sheet workbook from a list of row-tuples and return it as
        a download response.

        No logo image is placed in the Excel file — a spreadsheet is data, not a
        branded document, and a floated image only gets in the way of filtering,
        sorting and copying. The sheet carries a plain text title band instead;
        the branded logo belongs on the PDF reports, not here.
        """
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})
        ws = wb.add_worksheet(sheet_name)
        head_fmt = wb.add_format({
            'bold': True, 'bg_color': '#10b981', 'font_color': 'white',
            'border': 1, 'align': 'center', 'valign': 'vcenter',
        })
        title_fmt = wb.add_format({
            'bold': True, 'font_size': 18, 'font_color': '#10b981',
            'valign': 'vcenter',
        })
        cell = wb.add_format({'border': 1})

        # ── Title band (text only, NO logo image) ─────────────────────────────
        # A plain title on the first row; the table starts two rows below it.
        HEADER_ROW = 2  # 0-indexed: the header lands on the 3rd row
        ws.set_row(0, 26)
        if len(headers) > 1:
            ws.merge_range(0, 0, 0, min(len(headers) - 1, 6),
                           'Dawrha — %s Report' % sheet_name, title_fmt)
        else:
            ws.write(0, 0, 'Dawrha — %s Report' % sheet_name, title_fmt)

        for c, h in enumerate(headers):
            ws.write(HEADER_ROW, c, h, head_fmt)
            ws.set_column(c, c, max(14, len(h) + 2))
        for r, row in enumerate(rows, start=HEADER_ROW + 1):
            for c, val in enumerate(row):
                ws.write(r, c, '' if val is None else val, cell)
        ws.freeze_panes(HEADER_ROW + 1, 0)
        wb.close()
        data = output.getvalue()
        output.close()
        return request.make_response(data, headers=[
            ('Content-Type',
             'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', content_disposition(filename)),
        ])

    # ------------------------------------------------------------------
    # Shipments → Excel (ALL, admin)
    # ------------------------------------------------------------------
    @http.route('/recycle/admin/export/shipments.xlsx', type='http',
                auth='user', methods=['GET'])
    def export_shipments(self, **kw):
        if not self._is_admin():
            return self._forbidden()
        if xlsxwriter is None:
            return request.make_response('xlsxwriter not available', status=500)

        Ship = request.env['recycle.shipment'].sudo()
        ships = Ship.search([], order='id desc')
        headers = [
            'Reference', 'Warehouse', 'Driver', 'State', 'Priority',
            'Expected Weight (kg)', 'Actual Weight (kg)', 'Weight Diff %',
            'Received At', 'Received By', 'Sorted At', 'Sorted By',
            'Stored At', 'Stored By', 'Good Qty', 'Damaged Qty', 'Damaged %',
            'Backend Shipment ID',
        ]
        rows = []
        for s in ships:
            rows.append((
                s.name or '',
                s.warehouse_id.name or '',
                s.driver_name or '',
                dict(s._fields['state'].selection).get(s.state, s.state or ''),
                s.priority,
                s.expected_weight,
                s.actual_weight,
                s.weight_diff_pct,
                self._dt(s.received_at),
                s.receiver_user_id.name or '',
                self._dt(s.sorted_at),
                s.sorter_user_id.name or '',
                self._dt(s.stored_at),
                s.stored_by.name or '',
                s.total_good_qty,
                s.total_damaged_qty,
                s.damage_pct,
                s.backend_shipment_id or '',
            ))
        return self._xlsx(rows, headers, 'Shipments', 'shipments.xlsx')

    # ------------------------------------------------------------------
    # Orders → Excel (ALL, admin)
    # ------------------------------------------------------------------
    @http.route('/recycle/admin/export/orders.xlsx', type='http',
                auth='user', methods=['GET'])
    def export_orders(self, **kw):
        if not self._is_admin():
            return self._forbidden()
        if xlsxwriter is None:
            return request.make_response('xlsxwriter not available', status=500)

        Order = request.env['recycle.order'].sudo()
        orders = Order.search([], order='id desc')
        headers = [
            'Reference', 'Warehouse', 'Customer', 'Type', 'State', 'Priority',
            'Amount Total', 'Delivery Cost', 'Delivery Currency',
            'Invoice #', 'Stock Deducted At', 'Finished At', 'Factory ID',
        ]
        rows = []
        for o in orders:
            rows.append((
                o.name or '',
                o.warehouse_id.name or '',
                o.customer_name or '',
                dict(o._fields['order_type'].selection).get(o.order_type, o.order_type or ''),
                dict(o._fields['state'].selection).get(o.state, o.state or ''),
                o.priority,
                o.amount_total,
                # From the order's delivery trip(s); 0 for a self-collected order.
                o.delivery_cost,
                o.delivery_currency if o.has_delivery_cost else '',
                o.invoice_number or '',
                self._dt(o.stock_deducted_at),
                self._dt(o.finished_at),
                o.backend_factory_id or '',
            ))
        return self._xlsx(rows, headers, 'Orders', 'orders.xlsx')

    # ------------------------------------------------------------------
    # One shipment → PDF (full detail)
    # ------------------------------------------------------------------
    @http.route('/recycle/admin/export/shipment/<int:shipment_id>.pdf',
                type='http', auth='user', methods=['GET'])
    def export_shipment_pdf(self, shipment_id, **kw):
        if not self._is_admin():
            return self._forbidden()
        shipment = request.env['recycle.shipment'].sudo().browse(shipment_id).exists()
        if not shipment:
            return request.make_response('Shipment not found', status=404)
        pdf, _ct = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'recycle_warehouse.action_report_shipment_detail', [shipment.id])
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition',
             content_disposition('shipment_%s.pdf' % (shipment.name or shipment.id))),
        ])
