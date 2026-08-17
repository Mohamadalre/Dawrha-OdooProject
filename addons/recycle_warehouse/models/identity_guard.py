# -*- coding: utf-8 -*-
"""One national ID, one email — across EVERY person in the system.

People are recorded in four different tables here, because they arrive four
different ways:

    res.users                  staff who log in (managers, employees, admins)
    recycle.delivery.driver    delivery drivers, recruited inside Odoo
    recycle.driver.request     collectors, mirrored from the NestJS backend
    hr.applicant               job applicants from the website

Each table used to police uniqueness ONLY WITHIN ITSELF. That is not the rule a
national ID actually has: it identifies a human being, not a row. So the same
person could be an applicant, then an employee, then a delivery driver, three
times over — and nothing would notice, because no two of those checks ever
looked at each other. Two records claiming one identity is not a duplicate that
can be cleaned up later: it is two histories, two blocks, two sets of documents,
and no way to tell which one is the person.

This model is the single place that answers "is this identity already taken?",
and every one of the four tables asks it before writing. Adding a fifth kind of
person means adding one entry to `_IDENTITY_SOURCES` — nothing else.

WHAT THIS CANNOT DO, and what does it instead
─────────────────────────────────────────────
Searching four tables and then writing is not atomic. Two requests registering
the same national ID at the same instant both search before either writes, both
find nothing, and both are let through. `recycle.identity` closes that with a
UNIQUE index, and every claim goes through it.

The two are not redundant. This guard produces the message a person can act on
— "that national ID belongs to a delivery driver" — which an index cannot; the
index makes the rule true rather than merely likely. Guard first for the
explanation, registry second for the guarantee.
"""
from odoo import api, models, _
from odoo.exceptions import ValidationError

# (model, national-id field, email field, human label)
#
# The label is what the error names, because "already used by another account"
# sends someone hunting through the wrong screen. Telling them it belongs to a
# delivery driver is the difference between a fixable message and a dead end.
_IDENTITY_SOURCES = [
    ('res.users', 'recycle_national_id', 'email', 'a system user'),
    ('recycle.delivery.driver', 'national_id', 'email', 'a delivery driver'),
    ('recycle.driver.request', 'national_id', 'email', 'a collection driver'),
    ('hr.applicant', 'recycle_national_id', 'recycle_email', 'a job applicant'),
]


class RecycleIdentityGuard(models.AbstractModel):
    _name = 'recycle.identity.guard'
    _description = 'System-wide national ID / email uniqueness'

    @api.model
    def _sources(self):
        """Only the tables that actually exist in this database."""
        for model, nid_field, email_field, label in _IDENTITY_SOURCES:
            if model in self.env:
                yield model, nid_field, email_field, label

    @api.model
    def assert_unique_identity(self, national_id=None, email=None,
                               exclude_model=None, exclude_ids=None):
        """Refuse an identity already claimed by anyone, anywhere.

        `exclude_model` / `exclude_ids` skip the record being written — without
        them a record would collide with itself on every save.

        Archived rows are checked too (`active_test=False`): an archived person
        still exists, and letting their national ID be reused would silently
        merge two people the day the archive is reopened.
        """
        nid = (national_id or '').strip()
        mail = (email or '').strip().lower()
        if not nid and not mail:
            return

        exclusions = self._same_person_exclusions(exclude_model, exclude_ids)

        for model, nid_field, email_field, label in self._sources():
            exclude_here = exclusions.get(model, set())
            Model = self.env[model].sudo().with_context(active_test=False)

            if nid and nid_field in Model._fields:
                domain = [(nid_field, '=', nid)]
                if exclude_here:
                    domain.append(('id', 'not in', list(exclude_here)))
                if Model.search_count(domain):
                    raise ValidationError(_(
                        'National ID "%(nid)s" already belongs to %(who)s. '
                        'Every person in the system has one national ID and it '
                        'cannot be shared.') % {'nid': nid, 'who': _(label)})

            if mail and email_field in Model._fields:
                domain = [(email_field, '=ilike', mail)]
                if exclude_here:
                    domain.append(('id', 'not in', list(exclude_here)))
                if Model.search_count(domain):
                    raise ValidationError(_(
                        'Email "%(mail)s" is already used by %(who)s. An email '
                        'address identifies one person and cannot be shared.'
                    ) % {'mail': mail, 'who': _(label)})

    @api.model
    def register_identity(self, owner_model, owner_id,
                          national_id=None, email=None):
        """Check, then CLAIM — the two halves of the same rule.

        The search above can be beaten by a request that arrives in the
        microsecond between it and the write. The registry cannot: the claim is
        a row behind a UNIQUE index, so a concurrent duplicate is refused by the
        database in the same transaction.

        Callers use this rather than `assert_unique_identity` alone, so that
        passing the check and holding the identity are one step. Splitting them
        is what leaves the window open.
        """
        self.assert_unique_identity(
            national_id=national_id, email=email,
            exclude_model=owner_model, exclude_ids=[owner_id])
        # The SAME exclusions the check just used, handed to the registry. Both
        # halves must agree on who counts as one person, or a driver would pass
        # the check and then be refused their own login by the index.
        same_person = self._same_person_exclusions(owner_model, [owner_id])
        self.env['recycle.identity'].claim_all(
            owner_model, owner_id, national_id=national_id, email=email,
            same_person=same_person)

    @api.model
    def release_identity(self, owner_model, owner_id):
        """Give the identities back when the record goes.

        A claim left behind by a deleted record is worse than a missing one: it
        blocks a real person with a row that names nobody.
        """
        self.env['recycle.identity'].release(owner_model, owner_id)

    @api.model
    def _same_person_exclusions(self, exclude_model, exclude_ids):
        """Which rows, in which tables, are THE SAME PERSON as the one writing.

        A delivery driver and the login issued to them are one human being
        recorded in two tables — deliberately, because one is a person and the
        other is an account. Without this the guard would refuse a driver their
        own login: creating it copies their national ID onto `res.users`, and
        the next save sees "already taken" and points at the driver themselves.

        The context key `recycle_identity_owner` covers the moment the link does
        not exist yet — a login is created BEFORE `user_id` can be filled in, so
        the caller declares the owner up front.
        """
        exclusions = {}
        exclude_ids = set(exclude_ids or [])
        if exclude_model and exclude_ids:
            exclusions.setdefault(exclude_model, set()).update(exclude_ids)

        owner = self.env.context.get('recycle_identity_owner')
        if owner:
            owner_model, owner_id = owner
            exclusions.setdefault(owner_model, set()).add(owner_id)
            exclude_model = exclude_model or owner_model
            if owner_model == 'recycle.delivery.driver':
                exclude_ids = exclude_ids | {owner_id}

        Driver = self.env['recycle.delivery.driver'].sudo().with_context(
            active_test=False)

        # Writing a DRIVER → their own login is not someone else.
        if exclude_model == 'recycle.delivery.driver' and exclude_ids:
            user_ids = Driver.browse(list(exclude_ids)).exists().mapped('user_id').ids
            if user_ids:
                exclusions.setdefault('res.users', set()).update(user_ids)

        # Writing a USER → the driver record behind it is not someone else.
        if exclude_model == 'res.users' and exclude_ids:
            driver_ids = Driver.search(
                [('user_id', 'in', list(exclude_ids))]).ids
            if driver_ids:
                exclusions.setdefault(
                    'recycle.delivery.driver', set()).update(driver_ids)

        return exclusions

    @api.model
    def check_identity(self, national_id=None, email=None,
                       exclude_model=None, exclude_ids=None):
        """Same rule, reported instead of raised.

        Used by the dashboards to warn WHILE the form is being filled in, rather
        than after the user has typed everything and pressed save. Returns
        `{'ok': bool, 'message': str}`.
        """
        try:
            self.assert_unique_identity(
                national_id=national_id, email=email,
                exclude_model=exclude_model, exclude_ids=exclude_ids)
        except ValidationError as exc:
            return {'ok': False, 'message': exc.args[0] if exc.args else ''}
        return {'ok': True, 'message': ''}
