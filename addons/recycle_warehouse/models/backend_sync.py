# -*- coding: utf-8 -*-
"""Central OUTBOUND-sync layer to the NestJS backend.

ALL Odoo → backend calls live in this single file.

════════════════════════════════════════════════════════════════════
HOW TO CONNECT YOUR NESTJS BACKEND (two steps, nothing else to touch)
════════════════════════════════════════════════════════════════════
1. Set two system parameters (Settings → Technical → Parameters):

       recycle.backend_base_url    e.g. https://api.dawrha.com
       recycle.backend_api_key     shared secret sent as X-API-KEY header

2. If your NestJS route paths differ from the defaults below, edit
   ONLY the BACKEND_ROUTES dict — every sync call reads its path from
   this dict, nothing is hard-coded anywhere else. Each route can
   also be overridden per-environment WITHOUT code changes via a
   system parameter named  recycle.backend_route_<key>
   (e.g. recycle.backend_route_shipments = /v2/hooks/shipments).

Full request/response contract: see BACKEND_INTEGRATION.md at the
project root.

Every payload carries `event` + the record data (including
`backend_shipment_id` for correlation). Calls are fire-and-forget:
a network failure only logs a warning and never blocks the workflow.
"""
import json
import logging
from functools import partial
from urllib import request as _urlrequest

from odoo import SUPERUSER_ID, api, models
# Odoo 19 removed the `odoo.registry(db)` shortcut; the registry is reached
# through its class now. Imported explicitly rather than through `odoo.` so a
# rename fails loudly at import time instead of inside a post-commit callback,
# where the only symptom is a log line nobody reads and a mirror that stops
# updating — which is precisely how this went unnoticed the first time.
from odoo.modules.registry import Registry

_logger = logging.getLogger(__name__)

# Key under which the pending pings of ONE transaction are collected.
_PENDING = 'recycle_backend_pings'


def _flush_pings(dbname, pending):
    """Send the pings a committed transaction earned, on a fresh cursor.

    Runs AFTER the commit, so the backend can only ever be told about data that
    actually landed. The old call sites posted mid-transaction, which left two
    ways to be wrong: a rolled-back write could still announce itself, and a
    backend that re-read immediately could read the row as it was BEFORE the
    change it was being notified about.

    The cursor is new because the one that scheduled this is finished by now.
    """
    try:
        with Registry(dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            sync = env['recycle.backend.sync']
            for key, warehouse_id in sorted(pending):
                payload = {'odoo_warehouse_id': warehouse_id} if warehouse_id else {}
                sync._post_signed(key, payload)
    except Exception:                    # noqa: BLE001 - reported, never raised
        _logger.exception('Backend ping flush failed')

# ════════════════════════════════════════════════════════════════════
# THE ONLY PLACE ROUTE PATHS ARE DEFINED.
# key → path appended to recycle.backend_base_url.
# ════════════════════════════════════════════════════════════════════
BACKEND_ROUTES = {
    'shipments':  '/webhooks/odoo/shipments',   # shipment created / stored
    # Order events (manager decision, processing, deduction, finish, handover).
    # LIVE in the NestJS backend (OdooWebhookController @Post('orders')) — note
    # the versioned path and the x-odoo-webhook-secret auth, exactly like
    # 'fleet'. The old unversioned '/webhooks/odoo/orders' had NO listener: every
    # decision a warehouse made 404'd, so the buyer was never told their order
    # had been approved, prepared or handed over.
    'orders':     '/api/v1/odoo/webhooks/orders',
    # REVERSE product sync — LIVE in the NestJS backend (OdooWebhookController
    # @Post('products')): a product name edited on the Odoo screen is mirrored
    # back. Versioned path + x-odoo-webhook-secret auth, like 'orders'/'fleet'.
    # (The old unversioned '/webhooks/odoo/products' had no listener and 404'd.)
    'products':   '/api/v1/odoo/webhooks/products',
    'categories': '/webhooks/odoo/categories',  # category created
    'warehouses': '/webhooks/odoo/warehouses',  # warehouse created / updated
    # Fleet ping — this one is LIVE in the NestJS backend (OdooWebhookController):
    # it just enqueues a SYNC_FLEET job there; the backend then reads
    # recycle.truck / recycle.shift / recycle.driver.assignment back over
    # JSON-RPC. Auth differs from the routes above: header
    # x-odoo-webhook-secret = recycle.backend_webhook_secret (NOT X-API-KEY).
    'fleet':      '/api/v1/odoo/webhooks/fleet',
    # Delivery-trip events (driver confirmed a pickup / completed the run) —
    # LIVE in the NestJS backend, same x-odoo-webhook-secret auth as orders.
    'delivery':   '/api/v1/odoo/webhooks/delivery',
    # Driver lifecycle decision (accept / reject / need-changes) — LIVE
    # NestJS endpoint; same x-odoo-webhook-secret auth as 'fleet'.
    'driver_decision': '/api/v1/odoo/webhooks/driver-decision',
    # Shift-change request state moves (manager: processing/accepted/rejected)
    # — LIVE in the backend (same strict, secret-header contract).
    'shift_change_decision': '/api/v1/odoo/webhooks/shift-change-decision',
    # Delivery tariff changed — a payload-less ping, exactly like 'fleet':
    # the backend re-reads the whole (tiny) tariff list back over JSON-RPC,
    # so bursts of edits collapse into one idempotent re-read.
    'delivery_tariffs': '/api/v1/odoo/webhooks/delivery-tariffs',
    # Stock moved in a warehouse — another payload-less ping (same secret auth
    # as 'fleet'): the backend enqueues a SYNC_WAREHOUSE job that re-reads the
    # whole warehouse, so a burst of moves collapses into one re-read and a
    # replayed ping is harmless.
    'inventory': '/api/v1/odoo/webhooks/inventory',
    # Warehouse master data changed — most importantly the MANAGER, which Odoo
    # owns and the backend has no screen for. Same payload-less ping and same
    # SYNC_WAREHOUSE job as 'inventory'; a separate key because the two are
    # triggered by different events and one may be silenced without the other.
    'warehouse': '/api/v1/odoo/webhooks/warehouse',
}


class RecycleBackendSync(models.AbstractModel):
    _name = 'recycle.backend.sync'
    _description = 'NestJS Backend Sync (outbound)'

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------
    @api.model
    def _route(self, key):
        """Resolve a route path: system-parameter override first
        (recycle.backend_route_<key>), then the BACKEND_ROUTES default."""
        icp = self.env['ir.config_parameter'].sudo()
        return (icp.get_param('recycle.backend_route_%s' % key)
                or BACKEND_ROUTES[key])

    @api.model
    def _post(self, route_key, payload, extra_headers=None):
        icp = self.env['ir.config_parameter'].sudo()
        base = (icp.get_param('recycle.backend_base_url') or '').rstrip('/')
        if not base:
            # WARNING, not debug: an unset base URL silently disables EVERY
            # outbound sync (fleet, inventory, warehouse, suggestions), so a
            # truck added here never reaches the backend and nothing says why.
            # Set it in Settings → Recycling → Backend integration.
            _logger.warning(
                'Backend sync skipped: recycle.backend_base_url is not set, so '
                'the "%s" change was NOT sent to the backend. Configure it in '
                'Settings → Recycling.', route_key)
            return False
        path = self._route(route_key)
        headers = {
            'Content-Type': 'application/json',
            'X-API-KEY': icp.get_param('recycle.backend_api_key') or '',
        }
        headers.update(extra_headers or {})
        try:
            req = _urlrequest.Request(
                base + path,
                data=json.dumps(payload, default=str).encode('utf-8'),
                headers=headers,
                method='POST')
            with _urlrequest.urlopen(req, timeout=8) as resp:
                return 200 <= resp.status < 300
        except Exception as exc:
            _logger.warning('Backend sync failed (%s): %s', path, exc)
            return False

    @api.model
    def _post_signed(self, route_key, payload=None):
        """POST a payload-less-style ping, authenticated by the shared secret.

        The inventory / warehouse / fleet / tariff routes all authenticate this
        way and all carry (at most) a warehouse id, so the guard clause and the
        header were being written out five times. One copy means a route added
        later cannot forget the secret and fail silently as an unauthorised 401
        nobody reads.
        """
        icp = self.env['ir.config_parameter'].sudo()
        secret = icp.get_param('recycle.backend_webhook_secret') or ''
        if not secret:
            # WARNING, not debug: the signed pings (fleet / inventory / warehouse
            # / tariffs) all need this shared secret, and without it the backend
            # rejects them 401 — or, as here, they are never sent. Silent before,
            # which is why a missing secret looked like "sync just doesn't work".
            _logger.warning(
                'Ping skipped: recycle.backend_webhook_secret is not set, so the '
                '"%s" change was NOT sent to the backend. Set it (matching the '
                'backend ODOO_WEBHOOK_SECRET) in Settings → Recycling.', route_key)
            return False
        return self._post(route_key, payload or {}, extra_headers={
            'x-odoo-webhook-secret': secret,
        })

    @api.model
    def post_signed_return(self, path, payload):
        """Like `_post_signed`, but a REQUEST/RESPONSE call: POST to an explicit
        backend PATH with the shared secret and RETURN the parsed JSON body.

        The signed pings above are fire-and-forget (a boolean is enough). The
        RECEPTION scan is different: it needs the shipment's load back — materials,
        quantities, driver, truck — so this returns the decoded body (including a
        backend 4xx error body, so "not your warehouse" reaches the employee) or
        None when the backend could not be reached at all.
        """
        icp = self.env['ir.config_parameter'].sudo()
        base = (icp.get_param('recycle.backend_base_url') or '').rstrip('/')
        secret = icp.get_param('recycle.backend_webhook_secret') or ''
        if not base or not secret:
            _logger.warning(
                'Backend request skipped: base URL or webhook secret is not set '
                '(Settings → Recycling). Path: %s', path)
            return None
        headers = {
            'Content-Type': 'application/json',
            'x-odoo-webhook-secret': secret,
        }
        data = json.dumps(payload or {}, default=str).encode('utf-8')
        try:
            req = _urlrequest.Request(
                base + path, data=data, headers=headers, method='POST')
            with _urlrequest.urlopen(req, timeout=10) as resp:
                body = resp.read().decode('utf-8')
                return json.loads(body) if body else {}
        except _urlrequest.HTTPError as exc:
            # A validation/authorisation failure (e.g. 403 wrong warehouse) — the
            # backend still sends a JSON body explaining it; surface that.
            try:
                return json.loads(exc.read().decode('utf-8') or '{}')
            except Exception:
                return {'success': False, 'statusCode': exc.code}
        except Exception as exc:
            _logger.warning('Backend request failed (%s): %s', path, exc)
            return None

    # ------------------------------------------------------------------
    # Deferred, de-duplicated pings
    # ------------------------------------------------------------------
    @api.model
    def schedule_ping(self, route_key, warehouse=None):
        """Announce a change ONCE per transaction, after it commits.

        This exists because the pings used to hang off individual workflows —
        order.py, shipment.py, stock_damage_report.py each called
        `notify_inventory_changed` by hand. Every other path that moved stock
        told nobody: a reservation, a release, a direct correction, a deduction
        reached from anywhere else. So the backend's mirror was right after the
        three flows somebody had remembered to wire, and quietly wrong after
        everything else — which is exactly the "the API keeps its old number
        until I call sync" symptom.

        Hanging it off the MODEL instead (see `recycle.stock`) closes that,
        but turns one sorting run into a ping per row written. Collecting them
        here solves both at once: any number of writes anywhere in a request
        produce exactly one ping per (route, warehouse), sent once the
        transaction is safely committed.
        """
        callbacks = self.env.cr.postcommit
        pending = callbacks.data.get(_PENDING)
        if pending is None:
            pending = set()
            callbacks.data[_PENDING] = pending
            # Bound to the database NAME, not to this cursor: by the time the
            # callback runs, this cursor is done.
            callbacks.add(partial(_flush_pings, self.env.cr.dbname, pending))
        pending.add((route_key, warehouse.id if warehouse else 0))
        return True

    # ------------------------------------------------------------------
    # Public entry points — call these from the models
    # ------------------------------------------------------------------
    @api.model
    def sync_shipment(self, shipment, event):
        return self._post('shipments', {
            'event': event,
            'odoo_id': shipment.id,
            'name': shipment.name,
            'backend_shipment_id': shipment.backend_shipment_id or '',
            'state': shipment.state,
            'warehouse': shipment.warehouse_id.name,
            'actual_weight': shipment.actual_weight,
            'lines': [{
                'product': l.product_id.name,
                'quantity': l.quantity,
                'condition': l.condition,
            } for l in shipment.line_ids],
        })

    @api.model
    def sync_order(self, order, event):
        """Report one thing the warehouse did to the buyer's order.

        Uses the same secret-header contract as the fleet and driver channels:
        the route is a webhook, not an API-key endpoint, and it answered 503
        without the header. Missing it was the second of three reasons this
        channel was silently dead.
        """
        icp = self.env['ir.config_parameter'].sudo()
        secret = icp.get_param('recycle.backend_webhook_secret') or ''
        if not secret:
            _logger.warning('Order event NOT sent (no webhook secret set)')
            return False
        return self._post('orders', {
            'event': event,
            'odoo_id': order.id,
            'name': order.name,
            'state': order.state,
            'factory_id': order.backend_factory_id or '',
            # The piece of the buyer's order this belongs to — the key every
            # decision here is matched back on.
            'part_id': order.backend_part_id or '',
            'priority': order.priority,
            'warehouse': order.warehouse_id.name,
            # Carried so a reassignment (admin re-routing a split part) can be
            # mapped to the backend's own warehouse row and its distance/delivery
            # recomputed for the new leg.
            'warehouse_odoo_id': order.warehouse_id.id,
            'invoice_number': order.invoice_number or '',
            'output_zone': order.output_zone_id.name or '',
            'stock_deducted_at': str(order.stock_deducted_at or ''),
            'finished_at': str(order.finished_at or ''),
            # Handover is the manager's step and is what moves the buyer-facing
            # status on — "on the way" for a carrier, "delivered" for a
            # collection — so it travels with every order event.
            'manager_approval': order.manager_approval,
            'approval_reject_reason': order.approval_reject_reason or '',
            'handover_state': order.handover_state,
            'handover_type': order.handover_type or '',
            'handover_at': str(order.handover_at or ''),
            'handover_note': order.handover_note or '',
        }, extra_headers={'x-odoo-webhook-secret': secret})

    def sync_delivery(self, trip, event, stop=None):
        """Report a delivery-trip event (a driver's pickup, or completion) back
        to the backend, which owns the order and the buyer-facing status.

        Same secret-header contract as the order channel. The stop's backend id
        travels so the backend applies the pickup to the exact part, not a
        guess at which one moved.
        """
        icp = self.env['ir.config_parameter'].sudo()
        secret = icp.get_param('recycle.backend_webhook_secret') or ''
        if not secret:
            _logger.warning('Delivery event NOT sent (no webhook secret set)')
            return False
        return self._post('delivery', {
            'event': event,
            'backend_trip_id': trip.backend_trip_id,
            'trip_number': trip.trip_number,
            'status': trip.status,
            'backend_stop_id': stop.backend_stop_id if stop else '',
            'stop_sequence': stop.sequence if stop else 0,
            'picked_up_at': str(stop.picked_up_at or '') if stop else '',
        }, extra_headers={'x-odoo-webhook-secret': secret})

    @api.model
    def sync_product(self, product, event):
        return self._post('products', {
            'event': event,
            'odoo_id': product.id,
            'name': product.name,
            'category': product.category_id.name or '',
            'price_factory': product.price_factory,
            'price_free_facility': product.price_free_facility,
        })

    @api.model
    def sync_category(self, category, event):
        return self._post('categories', {
            'event': event,
            'odoo_id': category.id,
            'name': category.name,
        })

    @api.model
    def sync_delivery_tariffs(self):
        """Ping the backend that delivery pricing changed.

        Carries no payload for the same reason the fleet ping does not: the
        backend re-reads  over
        JSON-RPC, which keeps Odoo the single author and makes a replayed or
        duplicated ping harmless.
        """
        return self.schedule_ping('delivery_tariffs')

    @api.model
    def notify_inventory_changed(self, warehouse=None):
        """Tell the backend this warehouse's stock moved.

        The backend ALLOCATES orders from its mirror of these quantities. Until
        this existed the mirror only refreshed when an admin pressed sync, so an
        approved write-off or downgrade left the allocator promising grade and
        quantity the warehouse no longer had — and the mistake surfaced as a
        failed order rather than as a number on a screen.

        The warehouse id is the only thing that travels: it scopes the re-read
        to one warehouse instead of all of them.

        Deferred and de-duplicated (see `schedule_ping`): `recycle.stock` now
        raises this itself on every write, so one sorting run would otherwise
        mean one HTTP call per row.
        """
        return self.schedule_ping('inventory', warehouse)

    @api.model
    def notify_warehouse_changed(self, warehouse=None):
        """Tell the backend this warehouse's master data changed.

        Added for the MANAGER, which had no route to the backend at all. Odoo
        owns the assignment — the admin dashboard has the "Change Manager"
        action and the backend deliberately has none — but nothing told the
        backend when it changed. Its `warehouse_managers` table was written only
        by two manual admin endpoints, so `GET /admin/warehouses` answered
        `manager: null` for a warehouse that plainly had one on this screen,
        until somebody remembered to press sync.

        Payload-less by design, like the inventory and fleet pings: the backend
        replies 202 and re-reads the warehouse from Odoo over JSON-RPC, so Odoo
        stays the single source of truth and a burst of edits collapses into one
        idempotent re-read. Only the warehouse id travels, to scope that re-read
        to one site instead of all of them.
        """
        return self.schedule_ping('warehouse', warehouse)

    @api.model
    def notify_product_changed(self, product):
        """Tell the backend a product's NAME was edited here (reverse sync).

        Carries the Odoo product id; the backend re-reads the name over JSON-RPC
        and mirrors it onto its own row. Loop-safe by construction on the far
        side: the backend writes only when the value actually differs and never
        pushes back, so the backend→Odoo push and this Odoo→backend mirror
        converge after one hop instead of ping-ponging. Best-effort — a failed
        ping is a name that stays briefly out of step, never a blocked edit.
        """
        if not product or not product.id:
            return False
        return self._post_signed('products', {'odoo_product_id': product.id})

    @api.model
    def notify_fleet_changed(self):
        """Ping the backend that the fleet changed (truck added / edited /
        (un)assigned to a warehouse, assignment changed…).

        The backend replies 202 and enqueues its SYNC_FLEET job, which
        re-reads the whole fleet from Odoo over JSON-RPC — so this ping
        carries no payload: Odoo stays the single source of truth and
        bursts of changes collapse into idempotent re-reads.
        """
        return self.schedule_ping('fleet')

    @api.model
    def notify_driver_decision(self, backend_driver_id, status,
                               reason=None, rejected_media_ids=None,
                               approved_media_ids=None,
                               warehouse_odoo_id=None,
                               warehouse_change_only=False,
                               documents_only=False,
                               request_reupload=False,
                               cancel_reupload=False):
        """Tell the backend the admin's decision on a driver request.

        status: ACTIVE | REJECTED | BLOCKED | NEED_CHANGES |
        PENDING_APPROVAL (the backend's driver-decision webhook contract;
        PENDING_APPROVAL re-opens a rejected application for review).
        warehouse_odoo_id mirrors the driver's warehouse there (sent on
        acceptance / relocation); warehouse_change_only=True means "just move
        the warehouse — no status change, no notification".

        Two flags split what used to be one act, because marking a document
        unacceptable and telling the driver to replace it are different things
        and the reviewer needs to do the first several times before doing the
        second:

        documents_only=True   mark the listed documents rejected and change
                              NOTHING else — no account status, no
                              notification. The reviewer is still working.
        request_reupload=True sent with NEED_CHANGES: the listed documents are
                              recorded as ASKED FOR, and the driver is told.
                              It is what the backend counts to decide when he
                              has finished answering.
        cancel_reupload=True  sent with PENDING_APPROVAL: the reviewer gave up
                              waiting. The requests are withdrawn and the
                              account is released — but the documents keep the
                              status they were given, because withdrawing the
                              question is not accepting the answer.

        Returns True only on a 2xx response — callers treat False as a HARD
        error (decisions must never be lost, unlike the fire-and-forget pings
        above).
        """
        icp = self.env['ir.config_parameter'].sudo()
        secret = icp.get_param('recycle.backend_webhook_secret') or ''
        if not secret:
            _logger.warning('Driver decision NOT sent (no webhook secret set)')
            return False
        payload = {
            'backend_driver_id': backend_driver_id,
            'status': status,
        }
        if reason:
            payload['rejection_reason'] = reason
        if rejected_media_ids:
            payload['rejected_media_ids'] = rejected_media_ids
        # Accepting a document has to travel too. Rejecting one always did;
        # accepting one wrote in Odoo and stopped — so the backend went on
        # holding the document REJECTED while this screen showed it accepted,
        # and the driver could still be asked to replace a file already taken.
        if approved_media_ids:
            payload['approved_media_ids'] = approved_media_ids
        if warehouse_odoo_id:
            payload['warehouse_odoo_id'] = warehouse_odoo_id
        if warehouse_change_only:
            payload['warehouse_change_only'] = True
        if documents_only:
            payload['documents_only'] = True
        if request_reupload:
            payload['request_reupload'] = True
        if cancel_reupload:
            payload['cancel_reupload'] = True
        return self._post('driver_decision', payload, extra_headers={
            'x-odoo-webhook-secret': secret,
        })

    @api.model
    def notify_shift_change_status(self, backend_request_id, status,
                                   truck_odoo_id=None, reason=None):
        """Tell the backend the manager's move on a shift-change request.

        status: PROCESSING | ACCEPTED (with truck_odoo_id) | REJECTED (with
        reason). Same strictness contract as driver decisions: True only on
        a 2xx — callers refuse to save anything on False.
        """
        icp = self.env['ir.config_parameter'].sudo()
        secret = icp.get_param('recycle.backend_webhook_secret') or ''
        if not secret:
            _logger.warning(
                'Shift-change status NOT sent (no webhook secret set)')
            return False
        payload = {
            'backend_request_id': backend_request_id,
            'status': status,
        }
        if truck_odoo_id:
            payload['truck_odoo_id'] = truck_odoo_id
        if reason:
            payload['rejection_reason'] = reason
        return self._post('shift_change_decision', payload, extra_headers={
            'x-odoo-webhook-secret': secret,
        })

    @api.model
    def sync_warehouse(self, warehouse, event):
        return self._post('warehouses', {
            'event': event,
            'odoo_id': warehouse.id,
            'name': warehouse.name,
            'code': warehouse.code or '',
            'governorate': warehouse.governorate or '',
        })
