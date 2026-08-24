# -*- coding: utf-8 -*-
"""The reception-resync cron heals shipments the backend never acknowledged.

Reception accepts a shipment locally and THEN tells the backend to flip it to
RECEIVED so the collection driver sees the receipt. If that second call fails,
the shipment is stranded — accepted here, never RECEIVED there, and re-scanning
only says "already processed". `_cron_resync_reception` re-sends every accepted
-but-not-acknowledged shipment until the backend confirms, so a dropped call or
a brief outage heals on its own instead of freezing the driver's status.

The one method that touches the network (`post_signed_return`) is patched, so
these tests exercise the cron's decision logic without a live backend. The cron
sweeps the WHOLE table, so every assertion is scoped to the shipments THIS test
creates — never to a global call count, which the database's own data changes.
"""
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

from .common import make_warehouse


@tagged('post_install', '-at_install')
class TestReceptionResync(TransactionCase):

    def setUp(self):
        super().setUp()
        self.wh = make_warehouse(self.env, **{
            'name': 'Resync WH', 'code': 'RESYNCWH'})
        self.wh.backend_id = 'wh-be-9'
        self.Shipment = self.env['recycle.shipment']

    def _shipment(self, **vals):
        base = {'warehouse_id': self.wh.id, 'driver_name': 'D'}
        base.update(vals)
        return self.Shipment.create(base)

    def _patch_backend(self, result):
        """Patch the single method that reaches the backend."""
        sync_cls = type(self.env['recycle.backend.sync'])
        return patch.object(sync_cls, 'post_signed_return', return_value=result)

    @staticmethod
    def _call_for(mock, backend_shipment_id):
        """The (path, payload) the cron sent for one shipment, or None."""
        for args, _ in mock.call_args_list:
            if len(args) >= 2 and args[1].get('backend_shipment_id') == backend_shipment_id:
                return args
        return None

    # ------------------------------------------------------------------
    def test_accepted_unsynced_is_resent_and_marked_done(self):
        s = self._shipment(state='accepted', backend_shipment_id='resync-uniq-1')
        self.assertFalse(s.backend_received_synced)

        with self._patch_backend({'success': True}) as mock:
            self.Shipment._cron_resync_reception()

        s.invalidate_recordset(['backend_received_synced'])
        self.assertTrue(s.backend_received_synced)
        # It was sent to the confirm route with our shipment + warehouse ids.
        sent = self._call_for(mock, 'resync-uniq-1')
        self.assertIsNotNone(sent, 'the cron never sent our shipment')
        self.assertEqual(sent[0], '/api/v1/odoo/shipments/confirm')
        self.assertEqual(sent[1]['warehouse_backend_id'], 'wh-be-9')

    def test_a_failed_backend_leaves_it_unsynced_for_the_next_tick(self):
        s = self._shipment(state='accepted', backend_shipment_id='resync-uniq-2')

        with self._patch_backend({'success': False}):
            self.Shipment._cron_resync_reception()

        s.invalidate_recordset(['backend_received_synced'])
        self.assertFalse(s.backend_received_synced)

    def test_pending_and_escalated_shipments_are_left_alone(self):
        # Only a legitimately ACCEPTED shipment may be reported RECEIVED. A
        # pending one was never received; an escalated one is under dispute.
        # A success backend would MARK anything it touched, so an untouched
        # shipment staying False proves the state filter excluded it.
        p = self._shipment(state='pending', backend_shipment_id='resync-uniq-3')
        e = self._shipment(state='escalated', backend_shipment_id='resync-uniq-4')

        with self._patch_backend({'success': True}):
            self.Shipment._cron_resync_reception()

        p.invalidate_recordset(['backend_received_synced'])
        e.invalidate_recordset(['backend_received_synced'])
        self.assertFalse(p.backend_received_synced)
        self.assertFalse(e.backend_received_synced)

    def test_a_shipment_whose_warehouse_is_not_linked_is_skipped(self):
        # No warehouse backend id → the warehouse sync must close that first;
        # sending with an empty id would only be refused. It must stay unsynced.
        self.wh.backend_id = False
        s = self._shipment(state='accepted', backend_shipment_id='resync-uniq-5')

        with self._patch_backend({'success': True}) as mock:
            self.Shipment._cron_resync_reception()

        s.invalidate_recordset(['backend_received_synced'])
        self.assertFalse(s.backend_received_synced)
        self.assertIsNone(self._call_for(mock, 'resync-uniq-5'),
                          'a warehouse with no backend id was still sent')
