# -*- coding: utf-8 -*-
"""A receiving employee may only reach THEIR OWN warehouse's shipments.

Every route in this flow bypasses the record rules with `sudo()` — reasonable
in itself, because the employee must see a pending shipment before any rule
would grant it to them. What `sudo()` costs is that the warehouse scope stops
being enforced by the framework and has to be re-applied by hand in each route.

`scan-shipment` did that. `shipment-info` did not: it searched every
warehouse's shipments by reference and returned the whole payload — supplier,
weights, lines, driver — to any authenticated user who could guess or iterate a
reference.

Driven over real HTTP rather than by calling the controller directly: these
endpoints read `request.env.user` to decide the scope, so a test that calls the
method in-process has no session and cannot exercise the thing being fixed.
"""
import json

from odoo.tests.common import HttpCase, tagged

from .common import make_warehouse


@tagged('post_install', '-at_install')
class TestReceivingScope(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.wh_a = make_warehouse(cls.env, **{
            'name': 'Receiving Scope A', 'code': 'RCVSCOPEA',
        })
        cls.wh_b = make_warehouse(cls.env, **{
            'name': 'Receiving Scope B', 'code': 'RCVSCOPEB',
        })
        # Two receiving employees, one per warehouse. Both are legitimate
        # users, which is why no permission check catches the leak on its own.
        cls.emp_a = cls.env['res.users'].create({
            'name': 'Receiver A',
            'login': 'receiver.a@test.local',
            'password': 'receiver-a-pw-4471',
            'recycle_warehouse_id': cls.wh_a.id,
        })
        cls.emp_b = cls.env['res.users'].create({
            'name': 'Receiver B',
            'login': 'receiver.b@test.local',
            'password': 'receiver-b-pw-4471',
            'recycle_warehouse_id': cls.wh_b.id,
        })
        cls.shipment_a = cls.env['recycle.shipment'].create({
            'warehouse_id': cls.wh_a.id, 'driver_name': 'Driver A',
        })
        cls.shipment_b = cls.env['recycle.shipment'].create({
            'warehouse_id': cls.wh_b.id, 'driver_name': 'Driver B',
        })

    # ------------------------------------------------------------------
    def _call(self, path, params):
        """POST an Odoo jsonrpc call and return its `result`."""
        res = self.url_open(
            path,
            data=json.dumps({'jsonrpc': '2.0', 'method': 'call', 'params': params}),
            headers={'Content-Type': 'application/json'},
        )
        self.assertEqual(res.status_code, 200, res.text)
        return res.json().get('result') or {}

    # ------------------------------------------------------------------
    def test_shipment_info_hides_another_warehouse(self):
        """B's shipment must be invisible to A — the leak this file exists for."""
        self.authenticate('receiver.a@test.local', 'receiver-a-pw-4471')

        res = self._call('/api/receiving/shipment-info',
                         {'shipment_ref': self.shipment_b.name})

        self.assertEqual(
            res.get('error'), 'not_found',
            "a receiving employee read another warehouse's shipment")
        self.assertNotIn('shipment', res)

    def test_shipment_info_finds_own_warehouse(self):
        """The fix must not break the honest lookup."""
        self.authenticate('receiver.a@test.local', 'receiver-a-pw-4471')

        res = self._call('/api/receiving/shipment-info',
                         {'shipment_ref': self.shipment_a.name})

        self.assertTrue(res.get('ok'), res)
        self.assertIn('shipment', res)

    def test_shipment_info_refuses_a_user_with_no_warehouse(self):
        """No warehouse = no shipments, rather than every warehouse's."""
        self.env['res.users'].create({
            'name': 'No Warehouse',
            'login': 'no.warehouse@test.local',
            'password': 'no-warehouse-pw-4471',
        })
        self.authenticate('no.warehouse@test.local', 'no-warehouse-pw-4471')

        res = self._call('/api/receiving/shipment-info',
                         {'shipment_ref': self.shipment_b.name})

        self.assertEqual(res.get('error'), 'not_found')

    def test_scan_shipment_still_refuses_another_warehouse(self):
        """The route that already had the check keeps it."""
        self.authenticate('receiver.a@test.local', 'receiver-a-pw-4471')

        res = self._call('/api/receiving/scan-shipment',
                         {'shipment_ref': str(self.shipment_b.id)})

        self.assertEqual(res.get('case'), 'wrong_warehouse', res)
