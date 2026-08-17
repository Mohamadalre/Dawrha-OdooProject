# -*- coding: utf-8 -*-
"""Regression tests for the recruitment stage pipeline: the freeze that
must kick in once an applicant is fully accepted at the final stage, and
that a rejection at any earlier stage can always be un-done by re-approving."""
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestRecruitmentPipeline(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin = cls.env.ref('base.user_admin')
        cls.job = cls.env['hr.job'].create({'name': 'Test Position'})
        cls.stage = cls.env['hr.recruitment.stage'].search([], order='sequence, id', limit=1)

    def _applicant(self, name='Applicant'):
        return self.env['hr.applicant'].with_user(self.admin).create({
            'partner_name': name,
            'recycle_name': name,
            'recycle_email': '%s@example.com' % name.lower().replace(' ', ''),
            'job_id': self.job.id,
            'stage_id': self.stage.id,
        })

    def test_pipeline_freezes_after_final_acceptance(self):
        """Once recycle_state == 'accepted', approve/reject/advance must
        all be blocked — this is what stops an admin from accidentally
        re-opening a position that's already been filled."""
        app = self._applicant('Frozen Test')
        app.with_context(recycle_syncing=True).write({'recycle_state': 'accepted'})

        with self.assertRaises(UserError):
            app.with_user(self.admin).action_recycle_stage_approve()
        with self.assertRaises(UserError):
            app.with_user(self.admin).action_recycle_stage_reject()
        with self.assertRaises(UserError):
            app.with_user(self.admin).action_recycle_advance_stage()

    def test_rejection_can_be_undone_by_reapproving(self):
        """Rejecting a stage must never be a dead end while the pipeline
        is still open — approving again must work normally."""
        app = self._applicant('Recoverable Test')
        app.with_user(self.admin).action_recycle_stage_reject()
        self.assertEqual(app.recycle_stage_status, 'rejected')

        app.with_user(self.admin).action_recycle_stage_approve()
        self.assertEqual(app.recycle_stage_status, 'approved')

    def test_advance_stage_logs_a_history_entry(self):
        """Every completed stage must leave exactly one audit-trail row
        recording who approved it and when."""
        stages = self.env['hr.recruitment.stage'].search([], order='sequence, id')
        if len(stages) < 2:
            self.skipTest('Needs at least 2 recruitment stages configured.')
        app = self._applicant('History Test')
        app.stage_id = stages[0].id
        app.with_user(self.admin).action_recycle_stage_approve()
        app.with_user(self.admin).action_recycle_advance_stage()

        self.assertEqual(len(app.recycle_stage_log_ids), 1)
        log = app.recycle_stage_log_ids[0]
        self.assertEqual(log.stage_id, stages[0])
        self.assertEqual(log.next_stage_id, stages[1])
        self.assertTrue(log.decided_at)
