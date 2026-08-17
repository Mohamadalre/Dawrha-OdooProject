# -*- coding: utf-8 -*-
"""The Odoo admin proposes a material; they no longer create one.

The transport is stubbed — what is tested is everything AROUND it: that a
failure leaves the proposal on file and re-sendable rather than lost, that a
sent proposal cannot silently drift from what the backend received, and that the
payload carries the unit CODE (which the backend validates against) rather than
a display name.
"""
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

MODEL = 'odoo.addons.recycle_warehouse.models.product_suggestion.RecycleProductSuggestion'


@tagged('post_install', '-at_install')
class TestProductSuggestion(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls.env['recycle.product.category'].create(
            {'name': 'Suggestion Test Category'})
        cls.unit = cls.env['recycle.measurement.unit'].create({
            'name': 'Kilogram (test)', 'code': 'KG_TEST',
        })

    def _new(self, **overrides):
        vals = {
            'name': 'Shredded Aluminium',
            'category_id': self.category.id,
            'uom_id': self.unit.id,
            'description': 'Comes out of the sorting line already separated.',
        }
        vals.update(overrides)
        return self.env['recycle.product.suggestion'].create(vals)

    @staticmethod
    def _push_returns(ok, data=None, error=None):
        """Patch the one method that touches the network."""
        return patch(MODEL + '._push', return_value=(ok, data, error))

    # ------------------------------------------------------------------
    def test_submit_records_the_backend_reference(self):
        s = self._new()
        with self._push_returns(True, {'suggestion_id': 'be-123'}):
            self.assertTrue(s.action_submit())

        self.assertEqual(s.state, 'submitted')
        self.assertEqual(s.backend_suggestion_id, 'be-123')
        self.assertTrue(s.submitted_on)
        self.assertFalse(s.last_error)

    def test_a_failed_push_stays_on_file_and_re_sendable(self):
        """The point of not raising: the record and the error both survive."""
        s = self._new()
        with self._push_returns(False, None, 'connection refused'):
            result = s.action_submit()

        # A notification, not an exception — so nothing is rolled back.
        self.assertEqual(result['tag'], 'display_notification')
        self.assertEqual(result['params']['type'], 'danger')
        self.assertEqual(s.state, 'failed')
        self.assertIn('connection refused', s.last_error)

        # And it can be sent again once the backend is back.
        with self._push_returns(True, {'suggestion_id': 'be-9'}):
            s.action_submit()
        self.assertEqual(s.state, 'submitted')
        self.assertEqual(s.backend_suggestion_id, 'be-9')

    def test_cannot_submit_twice(self):
        s = self._new()
        with self._push_returns(True, {'suggestion_id': 'be-1'}):
            s.action_submit()
            with self.assertRaises(UserError):
                s.action_submit()

    def test_a_sent_proposal_cannot_be_edited_behind_the_backend_s_back(self):
        s = self._new()
        with self._push_returns(True, {'suggestion_id': 'be-1'}):
            s.action_submit()

        with self.assertRaises(UserError):
            s.name = 'Something Else'

        # Resetting to draft is the supported way to change it.
        s.action_reset_to_draft()
        s.name = 'Something Else'
        self.assertEqual(s.name, 'Something Else')

    def test_payload_carries_the_unit_code_not_its_label(self):
        """The backend validates the unit against its own `measurement_units`
        table BY CODE — sending 'Kilogram (test)' would be rejected."""
        s = self._new()
        captured = {}

        real_urlopen = None

        class _FakeResponse:
            status = 200

            def read(self):
                return b'{"data": {"suggestion_id": "be-1"}}'

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def fake_urlopen(req, timeout=None):
            captured['url'] = req.full_url
            captured['body'] = req.data.decode('utf-8')
            captured['secret'] = req.get_header('X-odoo-webhook-secret')
            return _FakeResponse()

        icp = self.env['ir.config_parameter'].sudo()
        base = icp.get_param('recycle.backend_base_url')
        secret = icp.get_param('recycle.backend_webhook_secret')
        icp.set_param('recycle.backend_base_url', 'http://backend.test')
        icp.set_param('recycle.backend_webhook_secret', 'shh')
        try:
            with patch(
                'odoo.addons.recycle_warehouse.models.product_suggestion'
                '._urlrequest.urlopen', side_effect=fake_urlopen
            ):
                ok, data, error = s._push()
        finally:
            icp.set_param('recycle.backend_base_url', base or '')
            icp.set_param('recycle.backend_webhook_secret', secret or '')

        self.assertTrue(ok, error)
        self.assertEqual(data['suggestion_id'], 'be-1')
        self.assertEqual(captured['secret'], 'shh')
        self.assertIn('/odoo/webhooks/product-suggestion', captured['url'])
        import json
        payload = json.loads(captured['body'])
        self.assertEqual(payload['unit_type'], 'KG_TEST')
        self.assertEqual(payload['category_name'], 'Suggestion Test Category')
        # The idempotency key: a retry after a timeout must land on this row.
        self.assertEqual(payload['odoo_suggestion_id'], s.id)

    def test_push_is_skipped_when_the_backend_is_not_configured(self):
        """No base URL means no silent 'sent' — the admin is told."""
        icp = self.env['ir.config_parameter'].sudo()
        original = icp.get_param('recycle.backend_base_url')
        icp.set_param('recycle.backend_base_url', '')
        try:
            s = self._new()
            ok, data, error = s._push()
            self.assertFalse(ok)
            self.assertIn('base URL', error)
        finally:
            icp.set_param('recycle.backend_base_url', original or '')
