"""Hoang's NTK test round (8 Nov 2026): extension dates are worked out by code, never by the model, and the Owner's opt-in autonomous decline
(policy.autoDecline). Fictional demonstration data (delegation_demo.py), as of 2026-10-24: Bayview's DEMO-301 is due 2026-10-18, so it is 6 days overdue."""
import unittest

import delegation
import delegation_demo
from test_delegation import DelegationCase

DECLINE = {'recommendation': 'decline', 'reasoning': 'Fictional: far longer than this customer usually gets.'}
LINES = {'enabled': True, 'maxExtensionDays': 40, 'maxDecisionExposure': None, 'maxCustomerExposure': None, 'maxPriorLateShare': None}


class ExtensionDateTests(DelegationCase):
    def refused(self, **args):
        body = self.tool('resolveDecision', **args)
        self.assertFalse(body['ok'], body)
        return body

    def test_days_that_land_in_the_past_are_refused_with_both_readings_worked_out(self):
        before = self.counts()
        body = self.refused(**self.extension('bayview', 'DEMO-301', days=3))   # 18 Oct + 3 = 21 Oct, before 24 Oct
        self.assertEqual(body['error'], 'ASK_STAFF_DATE')
        self.assertIn('Wed 21 Oct 2026, which is already past', body['message'])
        self.assertIn('3 days from today (Tue 27 Oct 2026, 9 days after the current due date)', body['message'])
        self.assertIn('Do not choose a date yourself', body['message'])
        self.assertEqual(self.counts(), before)   # nothing opened

    def test_a_date_that_disagrees_with_the_days_in_the_reasoning_is_refused(self):
        body = self.refused(**self.extension('bayview', 'DEMO-301', date='2026-11-10', reasoning='Customer asks for exactly 15 extra days.'))
        self.assertEqual(body['error'], 'DAYS_MISMATCH')
        self.assertIn('Your reasoning says 15 days, but Tue 10 Nov 2026 is 23 days after the current due date', body['message'])

    def test_a_date_that_matches_the_days_after_the_due_date_or_from_today_is_accepted(self):
        out = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10', reasoning='A 17-day extension from today, as Staff confirmed.'))
        self.assertEqual(out['status'], 'decided')
        self.assertIn('new date Tue 10 Nov 2026 = 23 days after the current due date (17 days from today, Sat 24 Oct 2026)', out['statusText'])
        self.assertIn('23 days after the current due date', out['forModel']['statusText'])

    def test_days_that_do_not_land_on_the_date_the_reasoning_names_are_refused(self):
        # the owners' session, 12 Nov 2026: Staff asked for 31 December; the model sent days that landed on 1 December and wrote 31 December in its reasoning
        before = self.counts()
        body = self.refused(**self.extension('bayview', 'DEMO-301', days=30, reasoning='The customer cannot commit to paying by the requested extended due date of 15 December 2026.'))
        self.assertEqual(body['error'], 'DATE_MISMATCH')
        self.assertIn('Your reasoning names Tue 15 Dec 2026, but 30 days after the current due date (Sun 18 Oct 2026) is Tue 17 Nov 2026', body['message'])
        self.assertIn('requestedDueDate set to exactly that date', body['message'])
        self.assertEqual(self.counts(), before)
        body = self.refused(**self.extension('bayview', 'DEMO-301', date='2026-11-15', reasoning='Asks to pay on December 15 instead.'))   # no year, month first
        self.assertEqual(body['error'], 'DATE_MISMATCH')
        self.assertIn('Your reasoning names Tue 15 Dec 2026, but requestedDueDate is Sun 15 Nov 2026', body['message'])

    def test_the_date_the_reasoning_names_is_accepted_and_other_dates_do_not_block_it(self):
        out = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10',
                                             reasoning='Asks to pay on 10 November 2026; a part payment is promised for 3 Nov. The invoice was due Sun 18 Oct 2026.'))
        self.assertEqual(out['keyFacts']['requestedDueDate'], '2026-11-10')

    def test_days_from_a_due_date_that_is_no_longer_current_are_refused(self):
        before = self.counts()
        body = self.refused(**self.extension('bayview', 'DEMO-301', days=20, reasoning='Extension to 15 days from today, which is 20 days after current due date (Sun 11 Oct 2026).'))
        self.assertEqual(body['error'], 'DUE_DATE_CHANGED')
        self.assertIn('Your reasoning says the current due date is Sun 11 Oct 2026, but invoice DEMO-301 is currently due Sun 18 Oct 2026', body['message'])
        self.assertEqual(self.counts(), before)

    def test_the_right_current_due_date_in_the_reasoning_is_accepted(self):
        out = self.resolved(**self.extension('bayview', 'DEMO-301', days=20, reasoning='20 days after the current due date of Sun 18 Oct 2026, as Staff asked.'))
        self.assertEqual(out['keyFacts']['requestedDueDate'], '2026-11-07')

    def test_days_counted_after_the_due_date_are_used_when_that_is_still_ahead(self):
        out = self.resolved(**self.extension('bayview', 'DEMO-301', days=20))
        self.assertEqual(out['keyFacts']['requestedDueDate'], '2026-11-07')
        self.assertIn('currently due Sun 18 Oct 2026, new date Sat 7 Nov 2026 = 20 days after the current due date', out['statusText'])


class AutoDeclineTests(DelegationCase):
    def setUp(self):
        super().setUp()
        self.change_policy(autoDecline=LINES)

    def long_one(self, rec=DECLINE):
        return self.extension('bayview', 'DEMO-301', date='2026-12-10', **rec)   # 53 days after the current due date: over the 40-day line

    def test_over_a_line_with_a_decline_recommendation_the_agent_declines_and_the_due_date_stays(self):
        out = self.resolved(**self.long_one())
        self.assertEqual((out['status'], out['handling'], out['decision']['outcome'], out['decision']['by']), ('decided', 'autonomous_decline', 'decline', 'agent'))
        self.assertIn('Declined by the agent under the Owner\'s decline rules', out['statusText'])
        self.assertIn('keeps its due date of Sun 18 Oct 2026', out['statusText'])
        self.assertEqual(self.due('bayview', 'DEMO-301'), '2026-10-18')
        r = self.request_of(out['requestId'])
        self.assertEqual((r['status'], r['decision']['outcome'], r['decision']['decisionSource'], r['decision']['decidedBy']), ('completed', 'decline', 'delegated_policy', 'nucleon_agent'))
        self.assertIn('53 days is over your decline line of 40 days', r['decision']['reason'])
        self.assertIn('declined', r['responseDraft']['text'])
        self.assertEqual(r['responseDraft']['deliveryStatus'], 'not_sent')

    def test_over_a_line_without_a_decline_recommendation_goes_to_the_owner(self):
        from test_delegation import APPROVE
        out = self.resolved(**self.long_one(APPROVE))
        self.assertEqual((out['status'], out['handling']), ('awaiting_owner', 'owner_review'))
        self.assertIn('decline line', out['why'])

    def test_a_decline_recommendation_inside_every_line_goes_to_the_owner(self):
        out = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10', **DECLINE))   # 23 days
        self.assertEqual((out['status'], out['handling']), ('awaiting_owner', 'owner_review'))

    def test_paused_the_agent_never_declines(self):
        self.pause()
        out = self.resolved(**self.long_one())
        self.assertEqual(out['status'], 'awaiting_owner')

    def test_the_owner_reverses_a_decline_and_the_date_asked_for_takes_effect(self):
        out = self.resolved(**self.long_one())
        status, body = self.feedback(out['caseId'], {'verdict': 'disagree', 'reason': 'They are good for it.', 'override': True})
        self.assertEqual(status, 200, body)
        self.assertIn("reversed the agent's decline", body['statusText'])
        self.assertEqual(self.due('bayview', 'DEMO-301'), '2026-12-10')
        r = self.request_of(out['requestId'])
        self.assertEqual((r['decision']['outcome'], r['decision']['decisionSource'], r['decision']['approvedDueDate']), ('approve', 'owner_override', '2026-12-10'))
        self.assertEqual(r['decisionHistory'][0]['outcome'], 'decline')
        case = self.app.dg_case(out['caseId'])
        self.assertEqual(self.app.dg_owner_view(case), 'approve')

    def test_agreeing_with_a_decline_counts_as_a_decline(self):
        out = self.resolved(**self.long_one())
        self.assertEqual(self.feedback(out['caseId'], {'verdict': 'agree', 'reason': 'Right.'})[0], 200)
        self.assertEqual(self.app.dg_owner_view(self.app.dg_case(out['caseId'])), 'decline')


class AutoDeclineOffTests(DelegationCase):
    def test_off_by_default_a_decline_recommendation_goes_to_the_owner(self):
        out = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-12-10', **DECLINE))
        self.assertEqual((out['status'], out['handling']), ('awaiting_owner', 'owner_review'))
        self.assertIn('autonomous decline is off', ' '.join(out['reasons']))

    def test_switching_it_on_needs_at_least_one_line(self):
        current = self.policy()
        status, body = self.put_policy({**delegation_demo.DEMO_POLICY, 'autoDecline': {'enabled': True}, 'expectedVersion': current['version']})
        self.assertEqual((status, body['error']), (400, 'INVALID_INPUT'))

    def test_a_saved_policy_without_the_setting_keeps_its_digest(self):
        p = delegation.validate_policy(delegation_demo.DEMO_POLICY, {'currency': 'AUD', 'scale': 2})
        without = {k: v for k, v in p.items() if k != 'autoDecline'}
        self.assertEqual(delegation.policy_digest(p), delegation.policy_digest(without))
        self.assertNotEqual(delegation.policy_digest({**p, 'autoDecline': LINES}), delegation.policy_digest(p))


if __name__ == '__main__':
    unittest.main()
