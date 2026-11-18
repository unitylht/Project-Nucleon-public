"""The whole records workflow, end to end through the HTTP API with the test agent: an empty practice workspace, first records,
an opening balance, the inclusion of earlier invoices, payments and their allocation, a completeness statement, a payment-extension
request, the owner's decision, and then a revert that changes the evidence. All data is fictional."""
import unittest

from test_exact import ExactCase

PAYMENTS = ('Customer,Date,Amount,Reference,Invoice\n'
            'Bayside Café,09/10/2026,1200.00,EFT 7702,INV-77\n'
            'Bayside Café,09/10/2026,300.00,EFT 7703,INV-78\n'
            'Bayside Café,13/10/2026,600.00,EFT 7781,DEMO-501\n')


class FullWorkflowTests(ExactCase):
    def test_from_an_empty_workspace_to_a_decision_and_a_revert(self):
        self.start()
        self.practice_ready()                                                       # empty practice workspace, then the basics
        self.assertEqual(self.call('/api/requests', {'messageText': 'Can we pay DEMO-501 later?'}, 'staff', 'too-early')[1]['error'], 'NO_RECORDS')
        self.bayside, self.coastline = self.add_customer('Bayside Café'), self.add_customer('Coastline Foods')

        # Opening balance, and the earlier invoices it is made of
        self.opening(amount='1500.00', credits='none')                              # owed as at 30 Sep, with no credits in it
        inv77 = self.invoice('INV-77', total='1200.00', issueDate='2026-09-01', inclusion='included')
        inv78 = self.invoice('INV-78', total='300.00', issueDate='2026-09-15', stillOwed='300.00', stillOwedAsOf='2026-09-30')
        self.assertEqual(self.statuses(), {'INV-77': 'included', 'INV-78': 'unresolved'})
        self.include('invoices', inv77, 'included', stillOwed='1200.00')            # 1,200 + 300 = 1,500: INV-78 reconciles...
        self.assertEqual((self.statuses()['INV-78'], self.view()['suggestion']['references']), ('unresolved', ['INV-78']))
        self.include('invoices', inv78, 'included')                                 # ...which a person confirms
        self.assertEqual(self.statuses(), {'INV-77': 'included', 'INV-78': 'included'})
        demo = self.invoice('DEMO-501', total='1000.00', issueDate='2026-10-02', dueDate='2026-10-16')

        # Payments from a bank export, each naming the invoice it pays
        batch = self.upload(PAYMENTS, key='bank')
        self.assertEqual([r['allocation']['reference'] for r in batch['preview']['rows']], ['INV-77', 'INV-78', 'DEMO-501'])
        batch = self.apply(batch)
        self.assertIsNone(self.exact(demo))
        self.assertIn('no confirmed completeness', self.not_exact(demo))
        self.assertEqual(self.minor(self.view()['balance']), '40000')               # 1,500 + 1,000 - 2,100: the whole account

        # The owner confirms the payment records are complete: now the amount is exact
        self.attest(start='2026-10-01', end='2026-10-18')
        exact = self.exact(demo)
        self.assertEqual((self.minor(exact['amount']), exact['asOf']), ('40000', '2026-10-18'))

        # A request, prepared by the agent, decided by the owner
        r = self.wait_status(self.create('Could we pay invoice DEMO-501 on 2026-11-06 instead?'), ('awaiting_owner',))
        facts = {f['key']: f for f in r['analysis']['brief']['facts']}
        self.assertEqual((facts['outstandingAmount']['kind'], self.minor(facts['outstandingAmount']['value']), facts['daysOverdue']['value']),
                         ('calculation', '40000', 2))
        self.assertEqual(self.decide(r, approved='2026-11-06')[0], 201)
        done = self.wait_status(r, ('completed',))

        # The bank export was the wrong account: reverting it needs review, keeps the decision, and flags the case
        status, error, _ = self.call('/api/imports/' + batch['id'] + '/revert', {'reason': 'Wrong account'}, 'staff', 'rv1')
        self.assertEqual((status, error['error'], error['impact']['review']['decidedCases']), (409, 'REVIEW_REQUIRED', [r['id']]))
        self.assertEqual(self.call('/api/imports/' + batch['id'] + '/revert', {'reason': 'Wrong account', 'confirm': True}, 'staff', 'rv2')[0], 200)
        after = self.reopen(done)
        self.assertEqual((after['decision'], after['analysis']['snapshot']), (done['decision'], done['analysis']['snapshot']))
        flag = after['flags'][-1]
        self.assertEqual((flag['outstandingBefore'], flag['outstandingNow']), ('exactly AUD 400.00 as of Sun 18 Oct 2026', 'not recorded'))
        self.assertIn('EFT 7781', ' '.join(self.coverage()['contradicted'][0]['records']))   # the statement no longer holds
        self.assertIsNone(self.exact(demo))


if __name__ == '__main__':
    unittest.main()
