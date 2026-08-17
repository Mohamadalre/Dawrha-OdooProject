# -*- coding: utf-8 -*-
"""The price sheet the ADMIN actually opens must show the offer.

There are two price screens in this module, and only one of them is the one an
administrator uses. The Odoo form view (`product_views.xml`) was taught to show
a live discount — struck-through list price beside the offer price. The custom
DASHBOARD modal, reached from Inventory → Products → "View Prices", was not: it
read `price` and nothing else.

So the sheet showed the list price while the apps were selling at another
number, and nothing on the screen said so. The data had been correct in Odoo the
whole time; the screen simply never asked for it.

This pins the READ. A field the modal does not request is a field it cannot
render, however right the model is — which is exactly how the gap survived
being "verified" against the other screen.
"""
from odoo.tests.common import TransactionCase, tagged

import os
import re

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD_JS = os.path.join(
    ADDON, 'static', 'src', 'js', 'recycle_admin_dashboard.js')
DASHBOARD_XML = os.path.join(
    ADDON, 'static', 'src', 'xml', 'dashboard_admin.xml')


@tagged('post_install', '-at_install')
class TestDashboardOfferDisplay(TransactionCase):

    def _price_modal_read(self):
        """The field list `openProductPrices` asks Odoo for."""
        source = open(DASHBOARD_JS, encoding='utf-8').read()
        start = source.index('async openProductPrices')
        block = source[start:start + 2000]
        match = re.search(r"\[([^\]]*'tier'[^\]]*)\]", block, re.S)
        self.assertTrue(match, 'could not find the field list of the price modal')
        return match.group(1)

    def test_the_modal_asks_for_the_offer(self):
        """`price` alone is the list price — it cannot show a discount."""
        fields = self._price_modal_read()
        for field in ('has_offer', 'offer_price', 'offer_percentage',
                      'offer_valid_until'):
            self.assertIn(
                field, fields,
                '"View Prices" does not read %s, so it cannot show a live '
                'offer however correct the model is' % field)

    def test_the_offer_fields_exist_and_are_readable(self):
        """Computed against the CLOCK and deliberately not stored, so they are
        correct at the instant they are looked at — an offer that has run out
        reads as no offer without anything having to expire it."""
        CP = self.env['recycle.product.condition.price']
        for field in ('has_offer', 'price_display', 'offer_price',
                      'offer_percentage', 'offer_valid_until'):
            self.assertIn(field, CP._fields, 'missing field: %s' % field)
        self.assertFalse(
            CP._fields['has_offer'].store,
            'has_offer must stay unstored — stored, an expired offer goes on '
            'reading as live until something else writes the row')

    def test_the_template_shows_BOTH_numbers(self):
        """An offer is a CHANGE of price. Showing only the new figure answers
        "what does it cost" while losing "what did it cost", which is the
        question this sheet is opened with."""
        xml = open(DASHBOARD_XML, encoding='utf-8').read()
        start = xml.index('state.pricesModal')
        # Bounded by the NEXT screen rather than by a character count: a fixed
        # window silently shrinks past the thing it is meant to cover as soon as
        # a comment is added above it, and the assertion then fails for a reason
        # that has nothing to do with the markup.
        block = xml[start:xml.index('PRODUCT CATEGORIES LIST', start)]

        self.assertIn('row.has_offer', block,
                      'the modal never branches on whether an offer is live')
        self.assertIn('row.offer_price', block,
                      'the modal never renders the offer price')
        self.assertIn('<s ', block,
                      'the superseded price is not struck through')
        self.assertIn('row.offer_percentage', block,
                      'the modal never renders how big the offer is — "18 → 16" '
                      'is the fact, but the percentage is what one material is '
                      'compared against another with')

    def test_the_percentage_is_translatable(self):
        """Arabic puts the number and the word in the other order, so the
        figure is substituted INTO the sentence rather than concatenated onto
        it — a glued-on "%" cannot be moved by a translator."""
        source = open(DASHBOARD_JS, encoding='utf-8').read()
        self.assertIn('offerPercentLabel', source,
                      'no helper builds the percentage label')
        start = source.index('offerPercentLabel')
        block = source[start:start + 600]
        self.assertIn('{pct}', block,
                      'the percentage is not substituted into a translatable '
                      'sentence')

        i18n = open(os.path.join(
            ADDON, 'static', 'src', 'js', 'recycle_i18n_shared.js'),
            encoding='utf-8').read()
        self.assertIn("reg('{pct}% off'", i18n,
                      'the percentage label has no Arabic translation')
