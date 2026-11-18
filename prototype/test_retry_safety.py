"""Interface states and retry safety, on the records' side (final round): a second Act or Confirm on a case that is decided, or whose
evidence or limits changed, is refused in words and never makes a second decision; the same press sent again with its key is the
first one's answer; an Act refused on changed records leaves the case's assessment re-made, so a card can show it; and a decision
without calculation details says why, from what the case recorded of its assessments. All data is fictional; no real model is called."""
import json
import unittest

import server
from test_assessment import AssessmentCase


class RetrySafetyTests(AssessmentCase):
    def committed(self):
        with self.app.lock:
            return [e for e in self.app.history(self.r['id']) if e['kind'] == 'decision.committed']

    def test_a_second_act_on_a_decided_case_is_refused_and_the_same_press_again_is_the_first_answer(self):
        self.set_limits()
        self.assess()
        status, first, _ = self.act('act-1')
        self.assertEqual((status, first['ok']), (200, True), first)
        self.assertEqual(self.act('act-1')[1], {**first, 'replayed': True})   # the same press sent again (a transport retry): its stored answer, nothing new
        status, again, _ = self.act('act-2')   # another tab, or a reload, presses again
        self.assertEqual((again['ok'], again['error'], again['message']),
                         (False, 'INVALID_ARGUMENT', 'There is no pending owner decision on this request, so there is nothing to act on.'))
        self.assertEqual(len(self.committed()), 1)

    def test_an_act_on_changed_records_is_refused_with_why_and_the_case_is_assessed_again(self):
        self.set_limits()
        card = self.assess()   # what the card shows: within the authority
        self.assertEqual(card['recommendation']['outcome'], 'approve_within_authority')
        self.add_invoice(self.bayside, 'DEMO-498', dueDate='2026-12-30', total='3000.00')   # a new invoice: the amount owed goes over the limit
        self.wait_status(self.r, ('awaiting_owner',))
        status, refused, _ = self.act('act-after-change')
        self.assertEqual((refused['ok'], refused['error']), (False, 'NOT_WITHIN_AUTHORITY'))
        self.assertEqual(refused['message'], "This is not within the owner's authority, so it stays with the owner: AUD 5,400.00 is owed; the limit is AUD 5,000.00.")
        c = self.case('staff')
        self.assertIsNone(c['decision'])
        self.assertEqual((c['assessment']['version'], c['assessment']['recommendation']['outcome']), (card['version'] + 1, 'escalate'))   # the refreshed assessment
        self.assertEqual(c['escalated']['reason'], 'the amount owed is over the limit')
        details = self.ok('caseDetails', 'staff', requestId=self.r['id'])['case']
        self.assertEqual((details['assessment']['version'], details['label']), (card['version'] + 1, 'With the owner'))   # what the card reads: version, next person
        self.assertEqual(len(self.committed()), 0)

    def test_a_second_confirm_never_makes_a_second_decision(self):
        self.set_limits()
        self.assess('owner')
        c = self.case()
        body = {'expectedRequestVersion': c['version'], 'analysisId': c['analysis']['id'], 'evidenceVersion': c['analysis']['snapshot']['evidenceVersion'],
                'outcome': 'approve', 'approvedDueDate': '2026-11-03', 'reason': 'This invoice only.'}
        press = lambda key, **more: self.call('/api/requests/' + self.r['id'] + '/decisions', {**body, **more}, 'owner', key)
        status, first, _ = press('confirm-1')
        self.assertEqual(status, 201, first)
        status, again, _ = press('confirm-1')   # the same press sent again (a transport retry): the same decision
        self.assertEqual((status, again['id']), (201, first['id']))
        status, other, _ = press('confirm-2')   # a second press from a card read before the decision: another tab
        self.assertEqual((status, other['error'], other['message']), (409, 'STALE_VERSION', 'The request changed. Refresh before acting.'))
        status, other, _ = press('confirm-3', expectedRequestVersion=self.case()['version'])   # one read after it: a reload
        self.assertEqual((status, other['error'], other['message']), (409, 'INVALID_TRANSITION', 'There is no pending owner decision.'))
        self.assertEqual(len(self.committed()), 1)


class BasisGapTests(AssessmentCase):
    """Why a decision has no calculation details: never inferred from the missing basis alone."""

    def edit(self, change):
        with self.app.lock, self.app.db:
            r = self.app.get(self.r['id'])
            change(r)
            self.app.save(r)

    def gap(self, role='owner'):
        status, body, _ = self.call('/api/requests/' + self.r['id'] + '/basis', role=role)
        self.assertEqual(status, 200, body)
        self.assertEqual(body['decisionBasisGap'], self.case(role).get('decisionBasisGap'))   # the case page reads the same (only a decided case has it)
        return body['decisionBasisGap'] and body['decisionBasisGap']['kind']

    def test_a_decision_made_with_no_assessment_says_none_was_performed(self):
        self.assertEqual(self.decide()[0], 201)
        self.assertEqual(self.gap(), 'no_assessment')
        self.assertEqual(self.case()['decisionBasisGap']['text'], 'No assessment was performed before this decision, so it has no calculation details.')

    def test_a_decision_with_its_details_has_no_gap_and_an_older_one_says_which_version_kept_none(self):
        self.set_limits()
        self.assess('owner')
        self.assertEqual(self.decide()[0], 201)
        self.assertIsNone(self.gap())
        self.edit(lambda r: r['decision']['basis'].update(basis=None))   # assessed by a version before calc-v1, decided after
        self.assertEqual(self.gap(), 'assessment_before_calc')
        self.edit(lambda r: r['decision'].pop('basis'))   # decided by a version before calc-v1: the case's assessment says one was made
        self.assertEqual(self.gap('staff'), 'decision_before_calc')
        self.assertEqual(self.case()['decisionBasisGap']['text'], 'Calculation details were not recorded by the application version that made this decision (before calc-v1).')

    def test_an_older_decision_with_no_assessment_recorded_says_none_was_performed(self):
        self.assertEqual(self.decide()[0], 201)
        self.edit(lambda r: (r['decision'].pop('basis'), r['decision'].pop('recommendation', None)))
        self.assertEqual(self.gap(), 'no_assessment')

    def test_an_undecided_case_has_no_gap(self):
        self.assess()
        self.assertIsNone(self.gap())


if __name__ == '__main__':
    unittest.main()
