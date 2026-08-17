# -*- coding: utf-8 -*-
"""Every change the backend mirrors must announce itself, with no route called.

The complaint this file exists for: the backend's stock figures stayed frozen
at whatever they were when someone last pressed a sync button, while Odoo moved
on. Same for warehouse master data.

The cause was that the announcements hung off THREE workflows — order.py,
shipment.py and stock_damage_report.py each called `notify_inventory_changed`
by hand. Every other path that moved stock told nobody: a reservation, a
release, a direct correction, a deduction reached from anywhere else, a row
created or deleted. So the mirror was right after the three flows somebody had
remembered to wire and quietly wrong after everything else.

The fix moves the announcement onto `recycle.stock` itself, which is the one
thing every quantity change must pass through. These tests pin that down by
exercising the paths, not by calling the notifier — a test that calls the
notifier proves only that the notifier exists.

Note what is asserted: that the ping was SCHEDULED. It is deliberately sent
after the transaction commits (see `schedule_ping`), which a test transaction
never does, and which is also the point — the backend can only be told about
data that actually landed.
"""
from odoo.tests.common import TransactionCase, tagged
from .common import make_warehouse

PENDING = 'recycle_backend_pings'


@tagged('post_install', '-at_install')
class TestBackendAutoSync(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = make_warehouse(cls.env, **{
            'name': 'Auto Sync Warehouse', 'code': 'AUTOSYNC',
        })
        cls.other_warehouse = make_warehouse(cls.env, **{
            'name': 'Auto Sync Warehouse 2', 'code': 'AUTOSYNC2',
        })
        cls.category = cls.env['recycle.product.category'].create(
            {'name': 'Auto Sync Cat'})
        cls.product = cls.env['recycle.product'].create({
            'name': 'Auto Sync Material', 'category_id': cls.category.id,
        })
        cls.Stock = cls.env['recycle.stock']

    # ------------------------------------------------------------------
    def _pending(self):
        """The pings this transaction has earned so far."""
        return set(self.env.cr.postcommit.data.get(PENDING) or ())

    def _clear(self):
        self.env.cr.postcommit.data.pop(PENDING, None)
        self.env.cr.postcommit._funcs.clear()

    def _inventory_ping_for(self, warehouse):
        return ('inventory', warehouse.id) in self._pending()

    def _new_stock(self, warehouse=None, qty=10.0):
        return self.Stock.create({
            'warehouse_id': (warehouse or self.warehouse).id,
            'product_id': self.product.id,
            'quantity': qty,
        })

    # ------------------------------------------------------------------
    # Stock
    # ------------------------------------------------------------------
    def test_creating_a_stock_row_announces_it(self):
        self._clear()
        self._new_stock()
        self.assertTrue(self._inventory_ping_for(self.warehouse))

    def test_changing_the_quantity_announces_it(self):
        row = self._new_stock()
        self._clear()
        row.write({'quantity': 25.0})
        self.assertTrue(self._inventory_ping_for(self.warehouse))

    def test_reserving_announces_it(self):
        """The path that used to tell nobody.

        Reserved stock is subtracted from what the backend may sell. A mirror
        that never hears about a reservation keeps offering material that is
        already promised to somebody else.
        """
        row = self._new_stock()
        self._clear()
        row.write({'reserved_qty': 4.0})
        self.assertTrue(self._inventory_ping_for(self.warehouse))

    def test_deleting_a_row_announces_it(self):
        row = self._new_stock()
        self._clear()
        row.unlink()
        self.assertTrue(self._inventory_ping_for(self.warehouse))

    def test_moving_a_row_announces_BOTH_warehouses(self):
        """Both totals changed, so both mirrors are stale.

        The old warehouse has to be read before the write — afterwards the
        record no longer knows where it came from.
        """
        row = self._new_stock()
        self._clear()
        row.write({'warehouse_id': self.other_warehouse.id})
        self.assertTrue(self._inventory_ping_for(self.warehouse))
        self.assertTrue(self._inventory_ping_for(self.other_warehouse))

    def test_a_burst_of_writes_collapses_into_one_ping(self):
        """A sorting run writes many rows. It must not send many pings.

        This is why the announcement is deferred rather than sent inline: moving
        it onto the model fixes the missing pings and would, on its own, replace
        them with a flood — one HTTP call per row written.
        """
        self._clear()
        row = self._new_stock()
        for quantity in range(1, 13):
            row.write({'quantity': float(quantity)})

        inventory_pings = [p for p in self._pending() if p[0] == 'inventory']
        self.assertEqual(len(inventory_pings), 1, inventory_pings)
        # And exactly one callback registered to send them.
        self.assertEqual(len(self.env.cr.postcommit._funcs), 1)

    def test_rows_in_several_warehouses_get_one_ping_each(self):
        """De-duplication must not collapse DIFFERENT warehouses together.

        Each mirror is re-read per warehouse, so merging them would leave every
        site but one stale — the original bug wearing a different hat.
        """
        self._clear()
        self._new_stock(self.warehouse)
        self._new_stock(self.other_warehouse)

        inventory_pings = {p for p in self._pending() if p[0] == 'inventory'}
        self.assertEqual(inventory_pings, {
            ('inventory', self.warehouse.id),
            ('inventory', self.other_warehouse.id),
        })

    # ------------------------------------------------------------------
    # Warehouse master data
    # ------------------------------------------------------------------
    def test_renaming_a_warehouse_announces_it(self):
        self._clear()
        self.warehouse.write({'name': 'Renamed Auto Sync'})
        self.assertIn(('warehouse', self.warehouse.id), self._pending())

    def test_changing_the_lifecycle_state_announces_it(self):
        """The most consequential of the mirrored fields.

        A warehouse put into `closing` stops taking new intake. A backend that
        has not been told keeps allocating orders to a site that is winding
        down.
        """
        self._clear()
        self.warehouse.write({'state': 'closing'})
        self.assertIn(('warehouse', self.warehouse.id), self._pending())
        self.warehouse.write({'state': 'active'})

    def test_moving_a_warehouse_announces_it(self):
        """Coordinates price deliveries per kilometre downstream."""
        self._clear()
        self.warehouse.write({'latitude': 33.5, 'longitude': 36.3})
        self.assertIn(('warehouse', self.warehouse.id), self._pending())

    def test_an_unmirrored_warehouse_field_does_not_announce(self):
        # Was `address`, which the backend did not keep. It does now — a driver
        # is sent to one — so it is mirrored, and fixed after creation besides.
        # Adding a ZONE changes the warehouse's contents, not the record the
        # backend keeps, so there is nothing to announce.
        self._clear()
        self.warehouse.write({
            'zone_ids': [(0, 0, {'name': 'Extra Zone', 'zone_type': 'storage'})],
        })
        self.assertNotIn(('warehouse', self.warehouse.id), self._pending())

    # ------------------------------------------------------------------
    # The routes themselves
    # ------------------------------------------------------------------
    def test_the_ping_routes_have_listeners(self):
        """A ping to a path nothing serves is indistinguishable from no ping.

        That has happened here twice: the orders webhook posted to an
        unversioned path with no listener, and the product push still does. Both
        404'd in silence.
        """
        Sync = self.env['recycle.backend.sync'].sudo()
        self.assertEqual(Sync._route('inventory'),
                         '/api/v1/odoo/webhooks/inventory')
        self.assertEqual(Sync._route('warehouse'),
                         '/api/v1/odoo/webhooks/warehouse')
        self.assertEqual(Sync._route('fleet'), '/api/v1/odoo/webhooks/fleet')
        self.assertEqual(Sync._route('delivery_tariffs'),
                         '/api/v1/odoo/webhooks/delivery-tariffs')

    # ------------------------------------------------------------------
    # A warehouse BORN in Odoo
    # ------------------------------------------------------------------
    def test_creating_a_warehouse_announces_it(self):
        """Only `write` announced, so a site created HERE told the backend
        nothing at all.

        It existed on this screen, held stock and took shipments, and was
        simply absent from every backend listing. Nobody noticed because the
        backend was assumed to be the only place warehouses are created — which
        stopped being true the moment this screen grew a "create" button.
        """
        self._clear()
        warehouse = make_warehouse(
            self.env, name='Born In Odoo WH', code='BORNODOO')

        self.assertIn(('warehouse', warehouse.id), self._pending())
