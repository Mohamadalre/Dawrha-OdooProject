# -*- coding: utf-8 -*-
"""Fill the identity registry from the four tables that already hold people.

The registry only guarantees anything if it knows what is already claimed. An
empty one would let the first person to re-register take a national ID that
somebody has held for months — the exact duplicate it exists to prevent, created
by the fix.

Existing DUPLICATES are the interesting case, and they can exist: until now each
table policed itself, so one human could be an applicant, an employee and a
delivery driver at once. The first claim wins and the rest are LOGGED with
enough detail to find them. Not merged, not dropped, not guessed at: deciding
which of two histories is the real person is a judgement about a human being,
and a migration that made it silently would be making it wrongly and invisibly.

Ordered deliberately. `res.users` goes first because a login is the record most
likely to be in active use, so when a collision has to be resolved by hand the
row left holding the claim is the one somebody is signing in with.
"""
import logging

_logger = logging.getLogger(__name__)

# (table, id column, national-id column, email column, model name)
#
# Raw SQL rather than the ORM: this runs during an upgrade, the tables are
# large enough that a per-record loop would be slow, and none of the models'
# create/write logic is wanted here — the rows already exist.
SOURCES = [
    ('res_users', 'id', 'recycle_national_id', None, 'res.users'),
    ('recycle_delivery_driver', 'id', 'national_id', 'email',
     'recycle.delivery.driver'),
    ('recycle_driver_request', 'id', 'national_id', 'email',
     'recycle.driver.request'),
    ('hr_applicant', 'id', 'recycle_national_id', 'recycle_email',
     'hr.applicant'),
]

OWNER_LABELS = {
    'res.users': 'a system user',
    'recycle.delivery.driver': 'a delivery driver',
    'recycle.driver.request': 'a collection driver',
    'hr.applicant': 'a job applicant',
}


def _table_exists(cr, table):
    cr.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
        (table,))
    return bool(cr.fetchone())


def _column_exists(cr, table, column):
    cr.execute("""
        SELECT 1 FROM information_schema.columns
         WHERE table_name = %s AND column_name = %s
    """, (table, column))
    return bool(cr.fetchone())


def _normalize(kind, value):
    """Must match `recycle.identity.normalize` exactly.

    If it does not, the backfill stores one form and the live claim looks up
    another — and the registry would then be enforcing nothing while appearing
    to work.
    """
    text = (value or '').strip()
    if not text:
        return ''
    return text.lower() if kind == 'email' else text


def _driver_login_pairs(cr):
    """Records that are ONE person deliberately kept in two tables.

    A delivery driver and the login issued to them share a national ID because
    they are the same human being — one row is a person, the other an account.
    Reporting that as a duplicate would bury the real collisions under noise
    that is supposed to be there.

    Returns a set of frozensets, each holding the two `(model, id)` pairs.
    """
    if not _table_exists(cr, 'recycle_delivery_driver'):
        return set()
    if not _column_exists(cr, 'recycle_delivery_driver', 'user_id'):
        return set()

    cr.execute("""
        SELECT id, user_id FROM recycle_delivery_driver
         WHERE user_id IS NOT NULL
    """)
    return {
        frozenset({('recycle.delivery.driver', driver_id),
                   ('res.users', user_id)})
        for driver_id, user_id in cr.fetchall()
    }


def migrate(cr, version):
    if not version:
        return
    if not _table_exists(cr, 'recycle_identity'):
        return

    same_person = _driver_login_pairs(cr)
    claimed = {}        # (kind, value) -> (model, id)
    inserted = 0
    collisions = []

    # What the registry already holds, so a re-run adds nothing twice.
    cr.execute("SELECT kind, value, owner_model, owner_id FROM recycle_identity")
    for kind, value, owner_model, owner_id in cr.fetchall():
        claimed[(kind, value)] = (owner_model, owner_id)

    for table, id_col, nid_col, email_col, model in SOURCES:
        if not _table_exists(cr, table):
            continue

        columns = [(nid_col, 'national_id'), (email_col, 'email')]
        for column, kind in columns:
            if not column or not _column_exists(cr, table, column):
                continue

            cr.execute("""
                SELECT %(id)s AS rid, %(col)s AS raw
                  FROM %(table)s
                 WHERE %(col)s IS NOT NULL AND btrim(%(col)s) <> ''
                 ORDER BY %(id)s
            """ % {'id': id_col, 'col': column, 'table': table})

            for record_id, raw in cr.fetchall():
                value = _normalize(kind, raw)
                if not value:
                    continue

                holder = claimed.get((kind, value))
                if holder:
                    mine = (model, record_id)
                    if holder != mine and frozenset({holder, mine}) not in same_person:
                        collisions.append(
                            '%s=%r held by %s #%s, also on %s #%s'
                            % (kind, value, holder[0], holder[1],
                               model, record_id))
                    continue

                # One record holds ONE identity per kind. A second value for
                # the same owner would be a second person wearing one record.
                cr.execute("""
                    SELECT 1 FROM recycle_identity
                     WHERE kind = %s AND owner_model = %s AND owner_id = %s
                """, (kind, model, record_id))
                if cr.fetchone():
                    continue

                cr.execute("""
                    INSERT INTO recycle_identity
                        (kind, value, owner_model, owner_id, owner_label,
                         create_uid, create_date, write_uid, write_date)
                    VALUES (%s, %s, %s, %s, %s, 1, NOW(), 1, NOW())
                """, (kind, value, model, record_id,
                      OWNER_LABELS.get(model, 'another record')))
                claimed[(kind, value)] = (model, record_id)
                inserted += 1

    _logger.info('Identity registry backfilled: %s claim(s) registered.',
                 inserted)

    if collisions:
        # Loud, and itemised. A count alone would say "you have a problem" and
        # not "here it is" — and these are people, not rows.
        _logger.warning(
            'Identity registry found %s EXISTING duplicate(s). The first '
            'holder keeps the claim; the others are listed below and need a '
            'human decision — merging two records means choosing which history '
            'to keep:\n  %s',
            len(collisions), '\n  '.join(collisions))
