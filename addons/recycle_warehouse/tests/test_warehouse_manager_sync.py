# -*- coding: utf-8 -*-
"""Changing a warehouse's manager must reach the backend.

Odoo owns this assignment — the admin dashboard has the "Change Manager" action
and the backend deliberately has no screen for it — but nothing carried the
change across. The backend's `warehouse_managers` table was written only by two
manual admin endpoints (`:id/sync-manager` and `import-from-odoo`), so
`GET /admin/warehouses` answered `manager: null` for a warehouse that plainly
has one here, until somebody remembered to press sync by hand.

Two things are pinned down:

1. **Assigning fires the ping.** Otherwise the backend never learns.
2. **REMOVING fires it too.** The old code tested `vals.get('manager_user_id')`,
   which is falsy for `False` — so clearing a manager was silently skipped. That
   is the worse of the two directions: the backend would keep naming somebody
   who is no longer responsible for the site, and stale data presented as fact
   is harder to notice than missing data.
"""
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged
from .common import make_warehouse

PING = ('odoo.addons.recycle_warehouse.models.backend_sync.'
        'RecycleBackendSync.notify_warehouse_changed')


@tagged('post_install', '-at_install')
class TestWarehouseManagerSync(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = make_warehouse(cls.env, **{
            'name': 'Ping Test Warehouse',
            'code': 'PING1',
        })
        cls.manager = cls.env['res.users'].create({
            'name': 'Ping Manager',
            'login': 'ping.manager@example.com',
            'email': 'ping.manager@example.com',
        })
        cls.other_manager = cls.env['res.users'].create({
            'name': 'Second Ping Manager',
            'login': 'ping.manager2@example.com',
            'email': 'ping.manager2@example.com',
        })

    def test_assigning_a_manager_pings_the_backend(self):
        with patch(PING) as ping:
            self.warehouse.write({'manager_user_id': self.manager.id})

        ping.assert_called_once()
        # The warehouse travels so the backend re-reads ONE site, not all.
        self.assertEqual(ping.call_args[0][0], self.warehouse)

    def test_replacing_a_manager_pings_the_backend(self):
        self.warehouse.write({'manager_user_id': self.manager.id})

        with patch(PING) as ping:
            self.warehouse.write({'manager_user_id': self.other_manager.id})

        ping.assert_called_once()

    def test_removing_the_manager_pings_the_backend(self):
        """The direction the truthiness test used to swallow."""
        self.warehouse.write({'manager_user_id': self.manager.id})

        with patch(PING) as ping:
            self.warehouse.write({'manager_user_id': False})

        ping.assert_called_once()

    def test_an_unmirrored_edit_does_not_ping(self):
        """The ping costs an HTTP round trip, so it is scoped to what the
        backend actually mirrors.

        This used to write `address`, on the grounds that the backend kept
        coordinates and a governorate for allocation but not a street line.
        That stopped being true: the backend now holds the address — a driver
        is sent to one, and coordinates do not name a gate — so it is mirrored,
        and it is also fixed after creation.

        A ZONE is the honest remaining example. Adding one changes the
        warehouse's contents, not the record the backend keeps, so there is
        nothing to announce.
        """
        with patch(PING) as ping:
            self.warehouse.write({
                'zone_ids': [(0, 0, {'name': 'Extra Zone',
                                     'zone_type': 'storage'})],
            })

        ping.assert_not_called()

    def test_a_mirrored_edit_pings_too(self):
        """Not only the manager: every field the backend mirrors."""
        with patch(PING) as ping:
            self.warehouse.write({'name': 'Renamed Warehouse'})

        ping.assert_called_once()

    def test_a_failing_ping_never_breaks_the_write(self):
        """A remote service being down must not refuse a manager change.

        Losing the ping costs one stale field that the next sync corrects.
        Raising here would mean the administrator cannot reassign a warehouse
        because the backend is unreachable — which is exactly when they might
        need to.
        """
        with patch(PING, side_effect=RuntimeError('backend unreachable')):
            self.warehouse.write({'manager_user_id': self.manager.id})

        self.assertEqual(self.warehouse.manager_user_id, self.manager)

    def test_the_route_is_the_live_backend_endpoint(self):
        """A ping to a path with no listener is indistinguishable from none.

        That has already happened here once: the orders webhook posted to an
        unversioned path nothing was serving, so every decision a warehouse made
        404'd in silence.
        """
        route = self.env['recycle.backend.sync'].sudo()._route('warehouse')
        self.assertEqual(route, '/api/v1/odoo/webhooks/warehouse')
