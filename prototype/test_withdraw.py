"""withdrawRequest: staff or the owner close a request opened by mistake, with a reason, while no decision exists. It leaves both
queues, is listed as done, ends a prepared decision, and is refused on a decided or already withdrawn request. Fictional data."""
import unittest

from test_assessment import AssessmentCase

REASON = 'Opened by mistake: the customer wrote about a different invoice.'


class WithdrawRequestTests(AssessmentCase):
    stored, prepare = AssessmentCase.T.stored, AssessmentCase.T.prepare

    def queued(self, role):
        queue = self.ok('workQueue', role)
        return [x['requestId'] for x in queue['forYou'] + queue['waitingOnOthers']]

    def test_staff_withdraw_a_request_with_a_reason_and_it_leaves_both_queues(self):
        self.assertIn(self.r['id'], self.queued('owner'))
        result = self.ok('withdrawRequest', 'staff', key='w1', requestId=self.r['id'], reason=REASON)
        self.assertEqual((result['withdrawn'], result['reason'], result['invoiceReference']), (True, REASON, 'DEMO-501'))
        stored, history = self.stored()
        self.assertEqual((stored['status'], stored['withdrawn']['reason'], stored['withdrawn']['role']), ('withdrawn', REASON, 'staff'))
        self.assertIn('request.withdrawn', [e['kind'] for e in history])
        self.assertIn('request.withdrawn', [e['kind'] for e in self.case('staff')['history']])   # staff see it too
        for role in ('owner', 'staff'):
            self.assertNotIn(self.r['id'], self.queued(role), role)
            self.assertEqual(self.case(role)['status'], 'withdrawn', role)
            self.assertNotIn(self.r['id'], [x['id'] for x in self.ok('listRequests', role)['requests']], role)   # open: not listed
            [row] = [x for x in self.ok('listRequests', role, status='all')['requests'] if x['id'] == self.r['id']]
            self.assertEqual((row['status'], row['withdrawnReason']), ('withdrawn', REASON), role)
        status, rows, _ = self.call('/api/requests', role='owner')
        [summary] = [x for x in rows if x['id'] == self.r['id']]
        self.assertEqual((summary['status'], summary['withdrawnReason'], summary['outcome']), ('withdrawn', REASON, None))

    def test_the_owner_withdraws_too_ends_a_preparation_and_the_label_says_so(self):
        self.prepare(7, 'p1')
        self.ok('withdrawRequest', 'owner', key='w2', requestId=self.r['id'], reason='Duplicate of another request.')
        stored, history = self.stored()
        self.assertNotIn('preparedDecision', stored)
        self.assertIn('decision.withdrawn', [e['kind'] for e in history])
        self.assertEqual(self.ok('caseDetails', 'owner', requestId=self.r['id'])['case']['label'], 'Withdrawn')

    def test_refusals(self):
        self.assertEqual(self.refused('withdrawRequest', 'staff', key='w3', requestId=self.r['id'], reason='  '), 'INVALID_ARGUMENT')
        self.ok('withdrawRequest', 'staff', key='w4', requestId=self.r['id'], reason=REASON)
        again = self.tool('withdrawRequest', 'owner', 'w5', requestId=self.r['id'], reason=REASON)[1]
        self.assertEqual((again['ok'], again['error']), (False, 'INVALID_ARGUMENT'))
        self.assertIn('already withdrawn', again['message'])
        other = self.second_case()
        with self.app.lock, self.app.db:   # a decided request cannot be withdrawn
            record = self.app.get(other['id'])
            record['status'], record['decision'] = 'completed', {'id': 'decision_x', 'outcome': 'approve', 'approvedDueDate': '2026-11-10', 'reason': 'Fine.', 'decidedAt': '2026-10-22T10:00:00+00:00'}
            self.app.save(record)
        decided = self.tool('withdrawRequest', 'owner', 'w6', requestId=other['id'], reason=REASON)[1]
        self.assertIn('is decided', decided['message'])


if __name__ == '__main__':
    unittest.main()
