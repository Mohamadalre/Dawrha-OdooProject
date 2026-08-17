# -*- coding: utf-8 -*-
"""One national ID, one email — enforced by the database, not by timing.

`recycle.identity.guard` searches four tables and then the caller writes. That
is correct in a quiet system and wrong under load: search-then-write is not
atomic, so two requests registering the same national ID at the same instant
both search before either writes, both find nothing, and both are let through.
Nothing in the code is at fault and nothing in the logs shows it — there are
simply two records that are the same person.

`recycle.identity` closes it with a UNIQUE index. These tests pin down the three
things that have to be true for that to be worth anything:

1. the index actually refuses a second claim;
2. a driver and the login issued to them — one person in two tables by design —
   are NOT refused;
3. deleting a record gives the identity back, so the same person can register
   again instead of being blocked by a row that names nobody.
"""
import psycopg2

from odoo.exceptions import ValidationError
from .common import make_warehouse
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestIdentityRegistry(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Identity = cls.env['recycle.identity']
        cls.Guard = cls.env['recycle.identity.guard']

    # ------------------------------------------------------------------
    # The index
    # ------------------------------------------------------------------
    def test_a_second_claim_on_the_same_value_is_refused(self):
        self.Identity.claim('national_id', 'REG-1', 'res.users', 9001)
        with self.assertRaises(ValidationError):
            self.Identity.claim('national_id', 'REG-1',
                                'recycle.delivery.driver', 9002)

    def test_the_database_refuses_it_even_when_the_check_is_bypassed(self):
        """The guarantee, as opposed to the courtesy.

        Every check in Python can be raced. This writes straight past all of
        them to prove the constraint is real — if this test ever passes without
        raising, the registry is decoration.
        """
        self.Identity.claim('national_id', 'REG-RACE', 'res.users', 9101)
        with self.assertRaises(psycopg2.IntegrityError), mute_logger('odoo.sql_db'):
            with self.env.cr.savepoint():
                self.env.cr.execute("""
                    INSERT INTO recycle_identity
                        (kind, value, owner_model, owner_id,
                         create_uid, create_date, write_uid, write_date)
                    VALUES ('national_id', 'REG-RACE',
                            'recycle.delivery.driver', 9102, 1, NOW(), 1, NOW())
                """)

    def test_reclaiming_your_own_identity_is_not_a_conflict(self):
        """Re-saving a record without touching its national ID must not fail."""
        first = self.Identity.claim('national_id', 'REG-2', 'res.users', 9003)
        again = self.Identity.claim('national_id', 'REG-2', 'res.users', 9003)
        self.assertEqual(first, again)

    def test_an_email_and_a_national_id_may_be_the_same_string(self):
        """They are different KINDS of claim, so they do not collide."""
        self.Identity.claim('national_id', 'shared-value', 'res.users', 9004)
        self.Identity.claim('email', 'shared-value', 'res.users', 9005)
        self.assertEqual(
            self.Identity.holder_of('national_id', 'shared-value'),
            ('res.users', 9004))

    def test_emails_are_compared_case_insensitively(self):
        """Addresses are not case-sensitive in practice, and treating them as
        if they were is how one person registers twice."""
        self.Identity.claim('email', 'Person@Example.com', 'res.users', 9006)
        with self.assertRaises(ValidationError):
            self.Identity.claim('email', 'person@example.COM',
                                'recycle.delivery.driver', 9007)

    def test_changing_a_value_releases_the_old_one(self):
        """An edit replaces a claim; it does not add one.

        Otherwise a corrected typo would hold the wrong number for ever and
        block whoever it really belongs to.
        """
        self.Identity.claim('national_id', 'REG-OLD', 'res.users', 9008)
        self.Identity.claim('national_id', 'REG-NEW', 'res.users', 9008)
        self.assertIsNone(self.Identity.holder_of('national_id', 'REG-OLD'))
        self.assertEqual(self.Identity.holder_of('national_id', 'REG-NEW'),
                         ('res.users', 9008))

    def test_releasing_frees_the_value(self):
        """A claim left by a deleted record blocks a real person with a row
        that names nobody — usually the same person, re-registering."""
        self.Identity.claim('national_id', 'REG-3', 'res.users', 9009)
        self.Identity.release('res.users', 9009)
        self.Identity.claim('national_id', 'REG-3',
                            'recycle.delivery.driver', 9010)
        self.assertEqual(self.Identity.holder_of('national_id', 'REG-3'),
                         ('recycle.delivery.driver', 9010))

    def test_blank_values_are_not_claimed(self):
        """An empty national ID is not an identity, and one blank claim would
        block every other record that has not filled the field in yet."""
        self.Identity.claim('national_id', '   ', 'res.users', 9011)
        self.Identity.claim('national_id', '', 'res.users', 9012)
        self.assertFalse(self.Identity.search([('owner_id', 'in', [9011, 9012])]))

    # ------------------------------------------------------------------
    # Two records, one person
    # ------------------------------------------------------------------
    def test_the_other_half_of_the_same_person_may_hold_it(self):
        """A driver and the login issued to them share a national ID BY DESIGN.

        One row is a person, the other is an account. Without this the registry
        refuses a driver their own login — creating it copies their national ID
        onto res.users, and the driver already holds the claim.
        """
        self.Identity.claim('national_id', 'REG-PAIR',
                            'recycle.delivery.driver', 9013)

        claim = self.Identity.claim(
            'national_id', 'REG-PAIR', 'res.users', 9014,
            same_person={'recycle.delivery.driver': {9013}})

        # Left where it was: moving it between two records of one human would
        # churn rows to no purpose.
        self.assertEqual(claim.owner_model, 'recycle.delivery.driver')
        self.assertEqual(claim.owner_id, 9013)

    def test_an_unrelated_record_still_cannot_hold_it(self):
        """The same-person allowance is not a way round the rule."""
        self.Identity.claim('national_id', 'REG-PAIR-2',
                            'recycle.delivery.driver', 9015)
        with self.assertRaises(ValidationError):
            self.Identity.claim(
                'national_id', 'REG-PAIR-2', 'res.users', 9016,
                same_person={'recycle.delivery.driver': {999999}})

    # ------------------------------------------------------------------
    # Through the real models
    # ------------------------------------------------------------------
    def test_creating_a_delivery_driver_claims_their_identity(self):
        driver = self.env['recycle.delivery.driver'].create({
            'name': 'Registry Test Driver',
            'phone': '0999000111',
            'national_id': 'REG-DRIVER-1',
            'warehouse_id': make_warehouse(self.env, **{
                'name': 'Registry WH', 'code': 'REGWH'}).id,
        })
        self.assertEqual(
            self.Identity.holder_of('national_id', 'REG-DRIVER-1'),
            ('recycle.delivery.driver', driver.id))

    def test_a_second_driver_cannot_take_that_national_id(self):
        """Refused — by whichever layer gets there first.

        The drivers table has its own unique index, so within THIS table the
        database usually wins the race and raises before the registry is
        consulted. That is the right outcome and the reason both are allowed
        here: what matters is that the second driver does not exist, not which
        guard turned them away.
        """
        warehouse = make_warehouse(self.env, **{
            'name': 'Registry WH 2', 'code': 'REGWH2'})
        self.env['recycle.delivery.driver'].create({
            'name': 'Registry Driver A', 'phone': '0999000222',
            'national_id': 'REG-DRIVER-2', 'warehouse_id': warehouse.id,
        })
        refused = False
        with mute_logger('odoo.sql_db'):
            try:
                with self.env.cr.savepoint():
                    self.env['recycle.delivery.driver'].create({
                        'name': 'Registry Driver B', 'phone': '0999000333',
                        'national_id': 'REG-DRIVER-2',
                        'warehouse_id': warehouse.id,
                    })
            except Exception:
                refused = True

        self.assertTrue(refused, 'the duplicate driver was created')
        # What actually matters: there is one driver holding that number.
        self.assertEqual(
            self.env['recycle.delivery.driver'].search_count(
                [('national_id', '=', 'REG-DRIVER-2')]), 1)

    def test_a_driver_cannot_take_a_national_id_held_in_ANOTHER_table(self):
        """The gap the per-table index cannot see.

        Each table used to police only itself, so one human could be a system
        user AND a delivery driver — two records, two histories, and no way to
        say which one is the person. This is the case the registry exists for.
        """
        self.Identity.claim('national_id', 'REG-CROSS', 'res.users', 9020)
        warehouse = make_warehouse(self.env, **{
            'name': 'Registry WH 4', 'code': 'REGWH4'})
        with self.assertRaises(ValidationError):
            self.env['recycle.delivery.driver'].create({
                'name': 'Registry Driver D', 'phone': '0999000555',
                'national_id': 'REG-CROSS', 'warehouse_id': warehouse.id,
            })

    def test_deleting_a_driver_frees_their_national_id(self):
        warehouse = make_warehouse(self.env, **{
            'name': 'Registry WH 3', 'code': 'REGWH3'})
        driver = self.env['recycle.delivery.driver'].create({
            'name': 'Registry Driver C', 'phone': '0999000444',
            'national_id': 'REG-DRIVER-3', 'warehouse_id': warehouse.id,
        })
        driver.unlink()
        self.assertIsNone(self.Identity.holder_of('national_id', 'REG-DRIVER-3'))
