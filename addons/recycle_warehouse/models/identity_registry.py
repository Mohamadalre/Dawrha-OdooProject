# -*- coding: utf-8 -*-
"""One row per claimed identity, with the database enforcing it.

`recycle.identity.guard` answers "is this national ID already taken?" by
searching four tables. That is correct in a quiet system and wrong under load:
search-then-write is not atomic. Two requests registering the same national ID
at the same moment both run their searches before either writes, both find
nothing, and both are allowed through. Nothing in the code is at fault and
nothing in the logs will show it — there will simply be two people who are the
same person.

The window is small and the consequence is not: two records claiming one
identity means two histories, two blocks, two sets of documents, and no way to
tell which one is the human being. It is also exactly the kind of duplicate that
surfaces months later, when merging them means deciding which history to throw
away.

So the rule lives where a rule can actually be enforced: a UNIQUE index. A claim
is a row here; a second claim on the same value is refused by PostgreSQL, in the
same transaction, whatever the timing. The four tables keep their search-based
check because it produces the BETTER MESSAGE — it can say "this belongs to a
delivery driver" while the index can only say "duplicate key" — but the index is
what makes the rule true rather than likely.

Two layers, two jobs:

    guard      → a helpful refusal, before the work is done
    this model → the guarantee, at the moment of writing
"""
import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

IDENTITY_KINDS = [
    ('national_id', 'National ID'),
    ('email', 'Email'),
]

# What each owner table is CALLED in a refusal. "Already in use" sends someone
# hunting through the wrong screen; naming the kind of record is the difference
# between a fixable message and a dead end.
OWNER_LABELS = {
    'res.users': 'a system user',
    'recycle.delivery.driver': 'a delivery driver',
    'recycle.driver.request': 'a collection driver',
    'hr.applicant': 'a job applicant',
}


def normalize(kind, value):
    """The form an identity is COMPARED in.

    Emails fold to lower case because addresses are not case-sensitive in
    practice and treating them as if they were is how one person registers
    twice. National IDs only lose surrounding whitespace — the characters
    themselves are significant, and "cleaning" them further would silently merge
    two different numbers.
    """
    text = (value or '').strip()
    if not text:
        return ''
    if kind == 'email':
        return text.lower()
    return text


class RecycleIdentity(models.Model):
    _name = 'recycle.identity'
    _description = 'Claimed Identity Registry'
    _order = 'kind, value'
    _rec_name = 'value'

    kind = fields.Selection(
        IDENTITY_KINDS, required=True, index=True,
        help='What sort of identifier this is. A national ID and an email may '
             'be the same string and still be two different claims.')
    value = fields.Char(
        required=True, index=True,
        help='Normalised: emails folded to lower case, everything trimmed. '
             'The raw form is kept on the owning record.')

    # Not a Many2one: the owner lives in one of four unrelated tables, and four
    # nullable columns would let a row point at two owners at once.
    owner_model = fields.Char(required=True, index=True)
    owner_id = fields.Integer(required=True, index=True)
    # Snapshotted so a refusal can name the holder without loading a record the
    # current user may have no right to read.
    owner_label = fields.Char()

    # THE point of this model. Everything else here is bookkeeping.
    #
    # Declared as `models.Constraint`, not as the old `_sql_constraints` list:
    # Odoo 19 silently IGNORES that list, so the table was created with the
    # indexes above and no unique constraint at all — a registry that enforced
    # nothing while every Python check went on passing. The test that writes
    # straight past the checks is what caught it, and is why that test exists.
    _identity_unique = models.Constraint(
        'UNIQUE(kind, value)',
        'This identity is already registered to someone else.')
    # One record holds ONE identity per kind. Two would be two people wearing
    # one record.
    _owner_unique_per_kind = models.Constraint(
        'UNIQUE(kind, owner_model, owner_id)',
        'A record cannot hold two identities of the same kind.')

    # ------------------------------------------------------------------
    @api.model
    def _label_for(self, owner_model):
        return _(OWNER_LABELS.get(owner_model, 'another record'))

    @api.model
    def claim(self, kind, value, owner_model, owner_id, same_person=None):
        """Register an identity to a record, or refuse it.

        Idempotent for the SAME owner: re-saving a record without touching its
        national ID must not fail, and a record re-claiming what it already
        holds is not a conflict.

        `same_person` names the OTHER records that are the same human being —
        `{model: {ids}}`. This is not a loophole, it is the domain: a delivery
        driver and the login issued to them are one person deliberately recorded
        in two tables, one being a person and the other an account. Without it
        the registry refuses a driver their own login, because creating it
        copies their national ID onto `res.users` and the driver already holds
        the claim. The guard has always had this notion; the registry needs the
        same one or the two disagree about who is who.

        A claim by a genuinely different owner raises, naming what holds it. The
        check is a read followed by a write and therefore still racy on its own
        — which is fine, because the UNIQUE index behind it is not. This read
        exists to produce a message a human can act on; the index is what makes
        the refusal certain.
        """
        normalized = normalize(kind, value)
        if not normalized:
            return self.browse()

        Registry = self.sudo()
        existing = Registry.search(
            [('kind', '=', kind), ('value', '=', normalized)], limit=1)
        if existing:
            if (existing.owner_model == owner_model
                    and existing.owner_id == owner_id):
                return existing
            if self._is_same_person(existing, same_person):
                # Held by the other half of the same person. Left exactly where
                # it is: moving the claim between two records of one human
                # would churn rows to no purpose and lose the earlier holder.
                return existing
            raise ValidationError(self._conflict_message(kind, normalized,
                                                         existing.owner_label))

        # Whatever this owner held under this kind BEFORE — an edit replaces a
        # claim, it does not add one.
        Registry.search([
            ('kind', '=', kind),
            ('owner_model', '=', owner_model),
            ('owner_id', '=', owner_id),
        ]).unlink()

        try:
            with self.env.cr.savepoint():
                return Registry.create({
                    'kind': kind,
                    'value': normalized,
                    'owner_model': owner_model,
                    'owner_id': owner_id,
                    'owner_label': self._label_for(owner_model),
                })
        except Exception as exc:
            # The race the search above cannot close: somebody claimed it
            # between the read and the write. The savepoint keeps the rest of
            # the transaction usable so this can be reported rather than
            # crashing the request.
            if 'identity_unique' not in str(exc).replace('_', ''):
                raise
            _logger.info('Identity %s "%s" was claimed concurrently',
                         kind, normalized)
            holder = Registry.search(
                [('kind', '=', kind), ('value', '=', normalized)], limit=1)
            raise ValidationError(self._conflict_message(
                kind, normalized, holder.owner_label)) from exc

    @api.model
    def _is_same_person(self, claim, same_person):
        """Is the current holder the other half of the person now claiming?"""
        if not same_person:
            return False
        return claim.owner_id in (same_person.get(claim.owner_model) or set())

    @api.model
    def conflict_details(self, kind, value):
        """The conflict as DATA, for callers that must translate it themselves.

        The dashboard picks its language from the browser, not from
        `res.users.lang`, so a sentence built here with `_()` is resolved
        against the wrong language and arrives in English however the screen is
        set. The refusal that names WHO holds the id is the one message on that
        form worth reading, and it was the only one always in English.

        Returning the parts lets the client compose the same sentence in its own
        language without losing the detail — which is what "just show something
        vaguer" would have cost.
        """
        Registry = self.sudo()
        normalized = normalize(kind, value)
        holder = Registry.search(
            [('kind', '=', kind), ('value', '=', normalized)], limit=1)
        return {
            'kind': kind,
            'value': normalized,
            'owner_label': holder.owner_label or '',
        }

    @api.model
    def _conflict_message(self, kind, value, owner_label):
        who = owner_label or _('another record')
        if kind == 'email':
            return _(
                'Email "%(value)s" is already used by %(who)s. An email address '
                'identifies one person and cannot be shared.'
            ) % {'value': value, 'who': who}
        return _(
            'National ID "%(value)s" already belongs to %(who)s. Every person '
            'in the system has one national ID and it cannot be shared.'
        ) % {'value': value, 'who': who}

    @api.model
    def claim_all(self, owner_model, owner_id, national_id=None, email=None,
                  same_person=None):
        """Claim both identities of one record, or neither.

        Both go through one call so a record whose email is refused does not
        end up holding a national-ID claim from a save that failed. The
        transaction takes care of the rollback; this only makes the intent
        explicit.
        """
        if national_id is not None:
            self.claim('national_id', national_id, owner_model, owner_id,
                       same_person=same_person)
        if email is not None:
            self.claim('email', email, owner_model, owner_id,
                       same_person=same_person)

    @api.model
    def release(self, owner_model, owner_id, kind=None):
        """Give an identity back, so it can be claimed again.

        Called when a record is deleted, and when a field is cleared. A claim
        left behind by a deleted record is worse than a missing one: it blocks a
        real person with a row that names nobody.
        """
        domain = [('owner_model', '=', owner_model), ('owner_id', '=', owner_id)]
        if kind:
            domain.append(('kind', '=', kind))
        return self.sudo().search(domain).unlink()

    @api.model
    def holder_of(self, kind, value):
        """Who holds this identity — `(owner_model, owner_id)` or None."""
        normalized = normalize(kind, value)
        if not normalized:
            return None
        row = self.sudo().search(
            [('kind', '=', kind), ('value', '=', normalized)], limit=1)
        return (row.owner_model, row.owner_id) if row else None
