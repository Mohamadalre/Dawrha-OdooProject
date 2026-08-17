# -*- coding: utf-8 -*-
import hmac
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class RecycleApiController(http.Controller):
    """REST API for the Next.js frontend.

    Authentication: header  X-API-KEY: <value of ir.config_parameter 'recycle.api_key'>
    """

    def _check_api_key(self):
        key = request.httprequest.headers.get('X-API-KEY') or ''
        expected = request.env['ir.config_parameter'].sudo().get_param('recycle.api_key') or ''
        # Constant-time comparison — a plain `==` leaks timing information
        # proportional to the matching prefix length, letting an attacker
        # brute-force the key one byte at a time over many requests.
        return bool(expected) and hmac.compare_digest(key, expected)

    def _json(self, payload, status=200):
        return request.make_json_response(payload, status=status)

    def _error(self, message, status=400):
        return self._json({'success': False, 'error': message}, status=status)

    def _authenticate(self):
        """Single guard for every external route: valid API key AND still
        within the per-minute rate limit. Returns an error HTTP response
        to return immediately, or None if the request may proceed."""
        if not self._check_api_key():
            return self._error('Invalid or missing API key.', status=401)
        if not request.env['recycle.api.rate.limit'].sudo().check():
            return self._error(
                'Rate limit exceeded. Please slow down and retry shortly.',
                status=429)
        return None

    # ------------------------------------------------------------------
    # GET /api/recycle/products  -> product catalog for Next.js
    # ------------------------------------------------------------------
    @http.route('/api/recycle/products', type='http', auth='public',
                methods=['GET'], csrf=False)
    def list_products(self, **kwargs):
        auth_err = self._authenticate()
        if auth_err:
            return auth_err
        products = request.env['recycle.product'].sudo().search([], limit=500)
        return self._json({
            'success': True,
            'products': [{
                'id': p.id,
                'name': p.name,
                'category': p.category_id.name,
                'price_factory': p.price_factory,
                'price_free_facility': p.price_free_facility,
            } for p in products],
        })

    # ------------------------------------------------------------------
    # POST /api/recycle/orders  -> create an order from the backend
    # Body (JSON):
    # {
    #   "warehouse_id": 3,                       # optional — Odoo's own id
    #                                           # for the warehouse (returned
    #                                           # by sync_warehouse/GET
    #                                           # /api/recycle/products etc.).
    #                                           # Preferred when known, since
    #                                           # it can never collide across
    #                                           # warehouses the way a code
    #                                           # theoretically could.
    #   "warehouse_code": "WH1",                 # required if warehouse_id
    #                                           # is not given; if BOTH are
    #                                           # given they must point to
    #                                           # the same warehouse.
    #   "customer_name": "Customer",
    #   "customer_email": "c@example.com",
    #   "lines": [{"product_id": 1, "quantity": 3,
    #              "condition": "excellent"}],  # optional, default "good";
    #                                           # one of excellent/good/poor/damaged.
    #                                           # Completing the order deducts stock
    #                                           # of this exact condition only.
    #   "factory_id": "FAC-2091",                # optional — your backend's
    #                                           # factory/customer id, stored for
    #                                           # correlation and returned below.
    #   "priority": 5                            # optional, default 10; lower
    #                                           # number = processed first. See
    #                                           # the priority queue rule in
    #                                           # BACKEND_INTEGRATION.md.
    # }
    # Unit price is NEVER sent by the caller — it's looked up server-side
    # from the product's price_factory / price_free_facility based on
    # order_type, so the backend can never under/over-price a line.
    # ------------------------------------------------------------------
    @http.route('/api/recycle/orders', type='http', auth='public',
                methods=['POST'], csrf=False)
    def create_order(self, **kwargs):
        auth_err = self._authenticate()
        if auth_err:
            return auth_err
        try:
            data = json.loads(request.httprequest.get_data() or b'{}')
        except (ValueError, TypeError):
            return self._error('Invalid JSON body.')

        warehouse_id = data.get('warehouse_id')
        warehouse_code = data.get('warehouse_code')
        customer_name = data.get('customer_name')
        order_type = data.get('order_type', 'factory')
        lines = data.get('lines')

        if not warehouse_id and not warehouse_code:
            return self._error('Field "warehouse_id" or "warehouse_code" is required.')
        if not customer_name:
            return self._error('Field "customer_name" is required.')
        if not lines or not isinstance(lines, list):
            return self._error('Field "lines" must be a non-empty list.')

        priority = data.get('priority', 10)
        try:
            priority = int(priority)
        except (ValueError, TypeError):
            return self._error('Priority must be an integer.')

        Warehouse = request.env['recycle.warehouse'].sudo()
        warehouse = None
        if warehouse_id:
            try:
                warehouse_id = int(warehouse_id)
            except (ValueError, TypeError):
                return self._error('Field "warehouse_id" must be an integer.')
            warehouse = Warehouse.browse(warehouse_id).exists()
            if not warehouse:
                return self._error('Warehouse id %s not found.' % warehouse_id, status=404)
            # If a code was ALSO supplied, it must agree with the id — this
            # catches a stale/mismatched pair on the caller's side early
            # instead of silently trusting whichever field happened to
            # resolve, which could route an order to the wrong warehouse.
            if warehouse_code and warehouse.code != warehouse_code:
                return self._error(
                    'Warehouse id %s does not match warehouse_code "%s" '
                    '(id %s is "%s").' % (
                        warehouse_id, warehouse_code, warehouse_id, warehouse.code))
        else:
            warehouse = Warehouse.search([('code', '=', warehouse_code)], limit=1)
            if not warehouse:
                return self._error('Warehouse "%s" not found.' % warehouse_code, status=404)

        Product = request.env['recycle.product'].sudo()
        line_vals = []
        for line in lines:
            if not isinstance(line, dict):
                return self._error('Each line must be an object.')
            product_id = line.get('product_id')
            quantity = line.get('quantity')
            if not product_id or not quantity:
                return self._error('Each line needs "product_id" and "quantity".')
            try:
                quantity = float(quantity)
            except (ValueError, TypeError):
                return self._error('Quantity must be a number.')
            if quantity <= 0:
                return self._error('Quantity must be positive.')
            product = Product.browse(int(product_id)).exists()
            if not product:
                return self._error('Product %s not found.' % product_id, status=404)
            # Grades belong to the MATERIAL and are authored in the backend, so
            # the valid set depends on which material this line names. A single
            # global list could not refuse a grade borrowed from a different
            # material, nor accept one the admin invented for this one.
            Conditions = request.env['recycle.material.condition'].sudo()
            valid = Conditions.codes_for(product)
            condition = (line.get('condition') or '').strip().upper()
            if valid and condition not in valid:
                return self._error(
                    'Invalid "condition" %r for material %r — must be one of: '
                    '%s.' % (line.get('condition'), product.name,
                             ', '.join(valid)))
            if not valid and condition:
                return self._error(
                    'Material %r has no grades, so "condition" must be omitted.'
                    % product.name)
            condition = condition or False
            price = product.price_factory if order_type == 'factory' else product.price_free_facility
            line_vals.append((0, 0, {
                'product_id': product.id,
                'quantity': quantity,
                'condition': condition,
                'price_unit': price,
            }))

        order = request.env['recycle.order'].sudo().create({
            'customer_name': customer_name,
            'customer_email': data.get('customer_email') or False,
            'backend_factory_id': data.get('factory_id') or False,
            'warehouse_id': warehouse.id,
            'order_type': order_type,
            'priority': priority,
            'source': 'nextjs',
            # API orders are NOT released to output employees until the
            # warehouse manager explicitly approves them.
            'manager_approval': 'pending',
            'line_ids': line_vals,
        })
        # Tell the warehouse manager a new order is waiting for approval.
        try:
            request.env['recycle.notification'].sudo()._notify_user(
                warehouse.manager_user_id,
                'طلبية جديدة بانتظار الموافقة / New order awaiting approval',
                'الطلبية %s من "%s" بانتظار موافقتك. / Order %s from "%s" '
                'is waiting for your approval.' % (
                    order.name, customer_name, order.name, customer_name),
                notif_type='order',
            )
        except Exception:
            _logger.warning('Could not notify manager for order %s', order.name, exc_info=True)
        return self._json({
            'success': True,
            'order_id': order.id,
            'name': order.name,
            'state': order.state,
            'manager_approval': order.manager_approval,
            'amount_total': order.amount_total,
            'priority': order.priority,
            'factory_id': order.backend_factory_id or None,
            'warehouse_id': warehouse.id,
            'warehouse_code': warehouse.code,
        }, status=201)

    # ------------------------------------------------------------------
    # POST /api/recycle/shipments  -> create an incoming shipment from
    # the backend. Returns the ODOO shipment id — this is the number the
    # reception employee scans as a barcode.
    # Body (JSON):
    # {
    #   "warehouse_code": "WHD1",
    #   "driver_name": "Ahmad",                       (required)
    #   "backend_shipment_id": "BK-1042",             (your backend's own id)
    #   "truck_info": "DAM 1234",                     (optional)
    #   "truck_serial_number": "SN-99",               (optional)
    #   "dispatch_date": "2026-07-12 08:00:00",       (optional)
    #   "priority": 5,                                (optional, lower = higher)
    #   "expected_materials": [                       (optional)
    #       {"product_id": 1, "quantity": 40}
    #   ]
    # }
    # ------------------------------------------------------------------
    @http.route('/api/recycle/shipments', type='http', auth='public',
                methods=['POST'], csrf=False)
    def create_shipment(self, **kwargs):
        auth_err = self._authenticate()
        if auth_err:
            return auth_err
        try:
            data = json.loads(request.httprequest.get_data() or b'{}')
        except (ValueError, TypeError):
            return self._error('Invalid JSON body.')

        warehouse_code = data.get('warehouse_code')
        driver_name = data.get('driver_name')
        if not warehouse_code:
            return self._error('Field "warehouse_code" is required.')
        if not driver_name:
            return self._error('Field "driver_name" is required.')

        warehouse = request.env['recycle.warehouse'].sudo().search(
            [('code', '=', warehouse_code)], limit=1)
        if not warehouse:
            return self._error('Warehouse "%s" not found.' % warehouse_code,
                               status=404)

        Product = request.env['recycle.product'].sudo()
        expected_vals = []
        for line in (data.get('expected_materials') or []):
            if not isinstance(line, dict):
                return self._error('Each expected material must be an object.')
            product_id = line.get('product_id')
            quantity = line.get('quantity')
            if not product_id or not quantity:
                return self._error(
                    'Each expected material needs "product_id" and "quantity".')
            try:
                quantity = float(quantity)
            except (ValueError, TypeError):
                return self._error('Quantity must be a number.')
            if quantity <= 0:
                return self._error('Quantity must be positive.')
            product = Product.browse(int(product_id)).exists()
            if not product:
                return self._error('Product %s not found.' % product_id,
                                   status=404)
            expected_vals.append((0, 0, {
                'product_id': product.id,
                'expected_qty': quantity,
            }))

        vals = {
            'warehouse_id': warehouse.id,
            'driver_name': driver_name,
            'backend_shipment_id': data.get('backend_shipment_id') or False,
            'truck_info': data.get('truck_info') or False,
            'truck_serial_number': data.get('truck_serial_number') or False,
            'expected_line_ids': expected_vals,
        }
        if data.get('dispatch_date'):
            vals['dispatch_date'] = data['dispatch_date']
        if data.get('priority') is not None:
            try:
                vals['priority'] = int(data['priority'])
            except (ValueError, TypeError):
                return self._error('Priority must be an integer.')

        shipment = request.env['recycle.shipment'].sudo().create(vals)
        return self._json({
            'success': True,
            # ⇩ scan THIS id as the barcode at reception
            'shipment_id': shipment.id,
            'name': shipment.name,
            'state': shipment.state,
            'backend_shipment_id': shipment.backend_shipment_id or None,
            'expected_weight': shipment.expected_weight,
        }, status=201)

    # ------------------------------------------------------------------
    # GET /api/recycle/orders/<id>  -> order status for Next.js
    # ------------------------------------------------------------------
    @http.route('/api/recycle/orders/<int:order_id>', type='http', auth='public',
                methods=['GET'], csrf=False)
    def order_status(self, order_id, **kwargs):
        auth_err = self._authenticate()
        if auth_err:
            return auth_err
        order = request.env['recycle.order'].sudo().browse(order_id).exists()
        if not order:
            return self._error('Order not found.', status=404)
        return self._json({
            'success': True,
            'order_id': order.id,
            'name': order.name,
            'state': order.state,
            'customer_name': order.customer_name,
            'warehouse_id': order.warehouse_id.id,
            'warehouse_code': order.warehouse_id.code,
            'factory_id': order.backend_factory_id or None,
            'priority': order.priority,
            'amount_total': order.amount_total,
            'invoice_number': order.invoice_number or None,
            'output_zone': order.output_zone_id.name or None,
            'stock_deducted_at': (
                order.stock_deducted_at.strftime('%Y-%m-%d %H:%M:%S')
                if order.stock_deducted_at else None),
            'finished_at': (
                order.finished_at.strftime('%Y-%m-%d %H:%M:%S')
                if order.finished_at else None),
            'lines': [{
                'product_id': l.product_id.id,
                'product': l.product_id.name,
                'quantity': l.quantity,
                'condition': l.condition,
                'price_unit': l.price_unit,
                'subtotal': l.subtotal,
            } for l in order.line_ids],
        })
