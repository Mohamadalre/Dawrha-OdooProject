# -*- coding: utf-8 -*-
"""Reviewing a driver's documents: judging one, and asking for one.

These used to be a single act. Rejecting a document notified the driver and
flipped his whole request to "needs changes" on the spot, so a reviewer could
not work down four documents marking each one — the first rejection ended the
review and sent him off to start fixing, before anybody had looked at the rest.
And a driver could be told to fix a document without ever being told which, or
told twice about the same one.

So the two are separate here, and the tests hold them apart:

  REJECTING is silent. It records the reviewer's judgement, moves nothing, and
  tells nobody. The mirror in the backend still moves — its re-upload route
  accepts a rejected document and nothing else — but no status changes and no
  message is sent.

  ASKING is the one act that reaches the driver. It requires a rejection to
  already be on record, so "send this again" always follows a stated reason.

The third rule is the subtle one: the driver comes back when nothing is still
ASKED FOR, not when nothing is rejected. Those differ, and the difference is a
trap — a document rejected but never requested is one he was never told about
and cannot see, so counting it would hold him in "needs changes" for ever with
nothing on his screen left to fix.
"""
from unittest.mock import patch

from odoo.exceptions import UserError
from .common import make_warehouse
from odoo.tests.common import TransactionCase, tagged

# The webhook is STRICT: a decision that cannot reach the backend is not saved
# here either, so every test that takes a decision has to stand it up.
NOTIFY = ('odoo.addons.recycle_warehouse.models.backend_sync.'
          'RecycleBackendSync.notify_driver_decision')


@tagged('post_install', '-at_install')
class TestDriverDocumentReview(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = make_warehouse(cls.env, 
            {'name': 'Doc Review WH', 'code': 'DOCREV'})

    _seq = 0

    def _request(self, images=(('LICENSE', 'pending'), ('ID_CARD_FRONT', 'pending'))):
        # A unique backend id per request: `create` is an UPSERT on it, so a
        # shared value would silently return the previous test's row.
        type(self)._seq += 1
        request = self.env['recycle.driver.request'].create({
            'backend_driver_id': 'drv-doc-%s' % type(self)._seq,
            'name': 'Test Driver',
            'email': 'driver@example.com',
        })
        for file_type, status in images:
            self.env['recycle.driver.request.image'].create({
                'request_id': request.id,
                'backend_media_id': '%s-%s' % (request.id, file_type),
                'file_type': file_type,
                'url': 'https://cdn/%s.jpg' % file_type,
                'status': status,
            })
        return request

    # ------------------------------------------------------------------
    # Rejecting a document is silent
    # ------------------------------------------------------------------
    def test_rejecting_a_document_does_not_move_the_request(self):
        request = self._request()
        image = request.image_ids[0]

        with patch(NOTIFY, return_value=True):
            request.action_reject_image(image.id)

        self.assertEqual(image.status, 'rejected')
        self.assertEqual(request.state, 'pending',
                         'rejecting one document ended the whole review')

    def test_rejecting_a_document_tells_the_driver_nothing(self):
        request = self._request()
        image = request.image_ids[0]

        with patch(NOTIFY, return_value=True) as notify:
            request.action_reject_image(image.id)

        # The mirror still moves — the backend's re-upload route accepts a
        # rejected document and nothing else — but as a documents-only push.
        self.assertTrue(notify.called)
        self.assertTrue(notify.call_args.kwargs.get('documents_only'))
        self.assertFalse(notify.call_args.kwargs.get('request_reupload'))

    def test_a_rejection_can_be_taken_back(self):
        """A reviewer who mis-clicks, or re-reads a scan and changes their
        mind, must be able to say so without involving the driver.

        The BACKEND is still told — telling the driver and telling the mirror
        are different things. Without the mirror moving, the backend would go
        on holding the document rejected while this screen showed it accepted.
        """
        request = self._request()
        image = request.image_ids[0]
        with patch(NOTIFY, return_value=True):
            request.action_reject_image(image.id)
            request.action_accept_image(image.id)

        self.assertEqual(image.status, 'accepted')

    def test_documents_are_frozen_once_the_request_is_accepted(self):
        request = self._request(images=(('LICENSE', 'accepted'),))
        image = request.image_ids[0]
        with patch(NOTIFY, return_value=True):
            request.action_accept(self.warehouse.id)

        with self.assertRaises(UserError):
            request.action_reject_image(image.id)

    # ------------------------------------------------------------------
    # Asking for a document is the act that reaches him
    # ------------------------------------------------------------------
    def test_asking_moves_the_request_and_tells_the_driver(self):
        request = self._request()
        image = request.image_ids[0]
        with patch(NOTIFY, return_value=True):
            request.action_reject_image(image.id)

            request.action_request_reupload(image.id, 'الصورة غير واضحة')

        self.assertEqual(request.state, 'need_changes')
        self.assertTrue(image.reupload_requested)
        self.assertEqual(request.rejection_reason, 'الصورة غير واضحة')

    def test_a_document_that_was_never_rejected_cannot_be_asked_for(self):
        """"We need this again" has to follow a stated reason — otherwise the
        driver is asked to replace a document nobody said anything about."""
        request = self._request()

        with self.assertRaises(UserError):
            request.action_request_reupload(request.image_ids[0].id)

    def test_the_same_document_is_not_asked_for_twice(self):
        request = self._request()
        image = request.image_ids[0]
        with patch(NOTIFY, return_value=True):
            request.action_reject_image(image.id)
            request.action_request_reupload(image.id)

            with self.assertRaises(UserError):
                request.action_request_reupload(image.id)

    def test_asking_re_opens_a_rejected_request(self):
        """The only way back into a rejected application: accepting it is
        blocked by the rejected document, and the document cannot be
        relabelled under a decided request."""
        request = self._request(images=(('LICENSE', 'pending'),))
        image = request.image_ids[0]
        with patch(NOTIFY, return_value=True):
            request.action_reject_image(image.id)
            request.action_reject('السجل منتهٍ')
            self.assertEqual(request.state, 'rejected')

            request.action_request_reupload(image.id)

        self.assertEqual(request.state, 'need_changes')

    # ------------------------------------------------------------------
    # Accepting and rejecting the request
    # ------------------------------------------------------------------
    def test_accepting_is_blocked_by_a_rejected_document(self):
        request = self._request()
        with patch(NOTIFY, return_value=True):
            request.action_reject_image(request.image_ids[0].id)

            with self.assertRaises(UserError):
                request.action_accept(self.warehouse.id)

    def test_accepting_settles_the_documents_still_unread(self):
        """Accepting is itself a statement that the submission is acceptable,
        so it settles what is open — it just may not override a rejection."""
        request = self._request()

        with patch(NOTIFY, return_value=True):
            request.action_accept(self.warehouse.id)

        self.assertEqual(set(request.image_ids.mapped('status')), {'accepted'})

    def test_rejecting_is_blocked_by_an_unread_document(self):
        """A rejection has to be answerable afterwards, and "we said no while
        three of your four documents were unread" is not an answer.

        Note this is STRICTER than acceptance, deliberately: accepting settles
        what is open, rejecting names a fault and so has to have looked.
        """
        request = self._request()

        with self.assertRaises(UserError):
            request.action_reject('لا ينطبق')

    def test_rejecting_leaves_the_documents_as_judged(self):
        request = self._request()
        with patch(NOTIFY, return_value=True):
            request.action_reject_image(request.image_ids[0].id)
            request.action_accept_image(request.image_ids[1].id)

            request.action_reject('السجل منتهٍ')

        self.assertEqual(request.image_ids[0].status, 'rejected')
        self.assertEqual(request.image_ids[1].status, 'accepted')

    def test_no_decision_while_the_driver_has_been_asked_for_something(self):
        request = self._request()
        with patch(NOTIFY, return_value=True):
            request.action_reject_image(request.image_ids[0].id)
            request.action_request_reupload(request.image_ids[0].id)

            with self.assertRaises(UserError):
                request.action_reject('لا ينطبق')

    def test_an_accepted_request_cannot_be_rejected(self):
        request = self._request(images=(('LICENSE', 'accepted'),))
        with patch(NOTIFY, return_value=True):
            request.action_accept(self.warehouse.id)

            with self.assertRaises(UserError):
                request.action_reject('غيّرت رأيي')

    # ------------------------------------------------------------------
    # A reviewer must be able to work with the backend down
    # ------------------------------------------------------------------
    def test_marking_documents_survives_an_unreachable_backend(self):
        """Marking a document is a reviewer's private working note.

        Nothing reaches the driver, no status moves, nothing he can see
        changes. Refusing to record it because a remote service is unreachable
        blocked the reviewer's whole workflow over a step that never needed to
        be atomic — with the backend down, neither button saved anything and
        both looked broken.

        Safe because it SELF-HEALS where it matters: asking the driver for the
        document re-sends those media ids and the backend marks them REJECTED
        again.
        """
        request = self._request()
        # `False` is what the sync layer returns when the backend cannot be
        # reached — the exact condition, not an invented one.
        with patch(NOTIFY, return_value=False):
            request.action_reject_image(request.image_ids[0].id)
            self.assertEqual(request.image_ids[0].status, 'rejected')

            request.action_accept_image(request.image_ids[0].id)
            self.assertEqual(request.image_ids[0].status, 'accepted')

    def test_decisions_that_reach_the_driver_stay_strict(self):
        """The rule narrows nothing it was not meant to narrow.

        Accepting or rejecting the REQUEST changes his account and notifies
        him, so the two systems must never disagree about it — those still
        refuse to save when the backend is unreachable.
        """
        request = self._request()
        with patch(NOTIFY, return_value=False):
            with self.assertRaises(UserError):
                request.action_reject('لا ينطبق')
            with self.assertRaises(UserError):
                request.action_accept(self.warehouse.id)
        self.assertEqual(request.state, 'pending')

    def test_asking_the_driver_stays_strict_too(self):
        """It is the act he actually sees — and the one that re-asserts the
        markings the backend may have missed."""
        request = self._request()
        with patch(NOTIFY, return_value=True):
            request.action_reject_image(request.image_ids[0].id)
        with patch(NOTIFY, return_value=False):
            with self.assertRaises(UserError):
                request.action_request_reupload(request.image_ids[0].id)
        self.assertFalse(request.image_ids[0].reupload_requested)

    # ------------------------------------------------------------------
    # Accepting a document is a decision too, and has to travel
    # ------------------------------------------------------------------
    def test_accepting_a_document_tells_the_backend(self):
        """Rejecting one always did; accepting one wrote here and stopped.

        The backend went on holding the document REJECTED while this screen
        showed it accepted — so the driver could still be asked to replace a
        file already taken, and the backend's approval gate went on counting a
        rejection that no longer existed.
        """
        request = self._request()
        with patch(NOTIFY, return_value=True) as notify:
            request.action_reject_image(request.image_ids[0].id)
            notify.reset_mock()

            request.action_accept_image(request.image_ids[0].id)

        self.assertEqual(request.image_ids[0].status, 'accepted')
        self.assertEqual(
            notify.call_args.kwargs.get('approved_media_ids'),
            [request.image_ids[0].backend_media_id])
        self.assertTrue(notify.call_args.kwargs.get('documents_only'))

    def test_accepting_closes_any_outstanding_request(self):
        """An accepted document is not something he still owes."""
        request = self._request()
        with patch(NOTIFY, return_value=True):
            request.action_reject_image(request.image_ids[0].id)
            request.action_request_reupload(request.image_ids[0].id)
            self.assertTrue(request.image_ids[0].reupload_requested)

            request.action_accept_image(request.image_ids[0].id)

        self.assertFalse(request.image_ids[0].reupload_requested)

    # ------------------------------------------------------------------
    # A rejected request freezes its documents
    # ------------------------------------------------------------------
    def test_a_rejected_request_freezes_its_documents(self):
        """The refusal has been taken and sent. Re-marking the evidence
        underneath it changes what the driver was refused for, after he was
        told — and nothing on either side would show the grounds had moved."""
        request = self._request()
        with patch(NOTIFY, return_value=True):
            request.action_reject_image(request.image_ids[0].id)
            request.action_accept_image(request.image_ids[1].id)
            request.action_reject('الوثائق غير مقبولة')

            with self.assertRaises(UserError):
                request.action_accept_image(request.image_ids[0].id)
            with self.assertRaises(UserError):
                request.action_reject_image(request.image_ids[1].id)

    def test_re_opening_thaws_them(self):
        """Reconsidering is allowed — in the open. Re-opening says so, tells
        the backend, and puts the request back where documents are editable."""
        request = self._request()
        with patch(NOTIFY, return_value=True):
            request.action_reject_image(request.image_ids[0].id)
            request.action_accept_image(request.image_ids[1].id)
            request.action_reject('الوثائق غير مقبولة')

            request.action_reactivate()
            self.assertEqual(request.state, 'pending')

            request.action_accept_image(request.image_ids[0].id)

        self.assertEqual(request.image_ids[0].status, 'accepted')

    # ------------------------------------------------------------------
    # The driver never answers
    # ------------------------------------------------------------------
    def test_a_driver_who_never_answers_used_to_freeze_the_request(self):
        """The state this flow could not leave.

        Asking for a document blocks every decision until he replies, so a
        driver who simply never comes back left the reviewer with no move at
        all — unable to accept, reject or close it.
        """
        request = self._request()
        with patch(NOTIFY, return_value=True):
            request.action_reject_image(request.image_ids[0].id)
            request.action_request_reupload(request.image_ids[0].id)

            with self.assertRaises(UserError):
                request.action_reject('لا ينطبق')
            with self.assertRaises(UserError):
                request.action_accept(self.warehouse.id)

            # The one move that exists.
            request.action_cancel_reupload_request()

        self.assertEqual(request.state, 'pending')
        self.assertFalse(request.image_ids.filtered('reupload_requested'))

    def test_stopping_the_wait_withdraws_the_question_not_the_finding(self):
        """Turning "I gave up waiting" into "I accept what you sent" would
        approve, silently, a document the reviewer had just called
        unacceptable."""
        request = self._request()
        with patch(NOTIFY, return_value=True):
            request.action_reject_image(request.image_ids[0].id)
            request.action_request_reupload(request.image_ids[0].id)

            request.action_cancel_reupload_request()

        self.assertEqual(request.image_ids[0].status, 'rejected')

    def test_after_stopping_it_can_be_rejected_but_not_accepted(self):
        """The pair of doors this deliberately leaves open: every document has
        been judged, so a rejection is answerable; one is still marked
        unacceptable, so an acceptance would override the reviewer's finding."""
        request = self._request()
        with patch(NOTIFY, return_value=True):
            request.action_reject_image(request.image_ids[0].id)
            request.action_accept_image(request.image_ids[1].id)
            request.action_request_reupload(request.image_ids[0].id)
            request.action_cancel_reupload_request()

            with self.assertRaises(UserError):
                request.action_accept(self.warehouse.id)

            request.action_reject('الوثيقة غير مقبولة ولم تُستبدل')

        self.assertEqual(request.state, 'rejected')

    def test_nothing_to_cancel_is_refused(self):
        """Cancelling is withdrawing a question. If none was asked, the button
        would silently move a request between states for no reason."""
        request = self._request()

        with self.assertRaises(UserError):
            request.action_cancel_reupload_request()

    def test_stopping_the_wait_tells_the_backend(self):
        """It holds the same record and releases the account off it — without
        the call the driver stays in NEED_CHANGES there while Odoo shows the
        request back under review."""
        request = self._request()
        with patch(NOTIFY, return_value=True) as notify:
            request.action_reject_image(request.image_ids[0].id)
            request.action_request_reupload(request.image_ids[0].id)
            notify.reset_mock()

            request.action_cancel_reupload_request()

        self.assertTrue(notify.call_args.kwargs.get('cancel_reupload'))
        self.assertEqual(notify.call_args.args[1], 'PENDING_APPROVAL')

    # ------------------------------------------------------------------
    # The driver answers
    # ------------------------------------------------------------------
    def test_the_request_returns_to_the_queue_when_the_last_ask_is_answered(self):
        """The backend re-pushes the whole request when he replaces a file."""
        request = self._request()
        with patch(NOTIFY, return_value=True):
            request.action_reject_image(request.image_ids[0].id)
            request.action_request_reupload(request.image_ids[0].id)

        # The re-push: same backend_driver_id, fresh images, nothing asked for.
        self.env['recycle.driver.request'].create({
            'backend_driver_id': request.backend_driver_id,
            'name': 'Test Driver',
            'email': 'driver@example.com',
            'image_ids': [(0, 0, {
                'backend_media_id': 'm-new',
                'file_type': 'LICENSE',
                'url': 'https://cdn/new.jpg',
                'status': 'pending',
                'reupload_requested': False,
            })],
        })

        self.assertEqual(request.state, 'pending')

    def test_it_stays_out_of_the_queue_while_another_ask_is_open(self):
        """Replacing the first of two requested documents must not put the
        request back under review — the reviewer would open an application that
        looks complete and is not."""
        request = self._request()
        with patch(NOTIFY, return_value=True):
            request.action_reject_image(request.image_ids[0].id)
            request.action_request_reupload(request.image_ids[0].id)

        self.env['recycle.driver.request'].create({
            'backend_driver_id': request.backend_driver_id,
            'name': 'Test Driver',
            'email': 'driver@example.com',
            'image_ids': [
                (0, 0, {
                    'backend_media_id': 'm-new', 'file_type': 'LICENSE',
                    'url': 'https://cdn/new.jpg', 'status': 'pending',
                    'reupload_requested': False,
                }),
                (0, 0, {
                    'backend_media_id': 'm-other', 'file_type': 'ID_CARD_FRONT',
                    'url': 'https://cdn/id.jpg', 'status': 'rejected',
                    'reupload_requested': True,
                }),
            ],
        })

        self.assertEqual(request.state, 'need_changes')

    def test_a_re_push_no_longer_erases_the_reviewer_s_judgement(self):
        """The push replaces Odoo's whole image list, so the statuses have to
        travel with the files. Without them, a driver fixing one document reset
        the verdict on every other — a request with two bad documents became a
        request with none."""
        request = self._request()
        with patch(NOTIFY, return_value=True):
            request.action_reject_image(request.image_ids[1].id)

        self.env['recycle.driver.request'].create({
            'backend_driver_id': request.backend_driver_id,
            'name': 'Test Driver',
            'email': 'driver@example.com',
            'image_ids': [
                (0, 0, {
                    'backend_media_id': 'm-a', 'file_type': 'LICENSE',
                    'url': 'https://cdn/a.jpg', 'status': 'accepted',
                }),
                (0, 0, {
                    'backend_media_id': 'm-b', 'file_type': 'ID_CARD_FRONT',
                    'url': 'https://cdn/b.jpg', 'status': 'rejected',
                }),
            ],
        })

        by_type = {i.file_type: i.status for i in request.image_ids}
        self.assertEqual(by_type['ID_CARD_FRONT'], 'rejected')
        self.assertEqual(by_type['LICENSE'], 'accepted')

    # ------------------------------------------------------------------
    # Blocking
    # ------------------------------------------------------------------
    def test_only_an_accepted_driver_can_be_blocked(self):
        """Blocking removes access somebody has. Applying it to an application
        still under review conflates "we are not letting you in" with "you were
        in and we threw you out"."""
        request = self._request()

        with self.assertRaises(UserError):
            request.action_block('اشتباه')
