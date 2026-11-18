"""Repair A, F2: what the records' invoice tools hand the model and the Lab cards. Each invoice carries its original amount
(totalText), the amount still owed with its basis (stillOwedText), the payments allocated to it with their references
(allocationsText) and whether it is settled, separately and labelled. All data is fictional."""
import time
import unittest

from test_assessment import AssessmentCase


class InvoiceFiguresTests(AssessmentCase):
    def pay(self, customer, invoice, amount, reference, day='2026-10-05'):
        status, paid, _ = self.call('/api/records/payments', {'customerId': customer['id'], 'receivedDate': day, 'amount': amount, 'reference': reference},
                                    'staff', 'pay-' + reference)
        self.assertEqual(status, 200, paid)
        body = {'paymentId': paid['record']['id'], 'allocations': [{'invoiceId': invoice['id'], 'amount': amount}]}
        self.assertEqual(self.call('/api/records/allocations', body, 'staff', 'alloc-' + reference)[0], 200)
        return paid['record']

    def rows(self, role='staff', **args):
        return {x['reference']: x for x in self.ok('invoices', role, customerId=self.bayside['id'], which='all', **args)['invoices']}

    def test_a_settled_invoice_says_its_original_amount_the_payment_allocated_and_that_it_is_settled(self):
        paid = self.add_invoice(self.bayside, 'DEMO-601', issueDate='2026-09-01', dueDate='2026-10-01', total='1026.00')
        self.pay(self.bayside, paid, '1026.00', 'BCV-FIC-001', '2026-09-20')
        row = self.rows()['DEMO-601']
        self.assertEqual(row['totalText'], 'AUD 1,026.00 (as recorded), the original invoice amount')
        self.assertTrue(row['settled'])
        self.assertIn('Still owed: AUD 0.00 (at most, derived: the invoice amount AUD 1,026.00 (as recorded) less AUD 1,026.00 (as recorded) allocated from payments)',
                      row['stillOwedText'])
        self.assertIn('settled', row['stillOwedText'])
        self.assertEqual(row['allocationsText'], 'Payment BCV-FIC-001, received ' + 'Sun 20 Sep 2026' + ': AUD 1,026.00 (as recorded) allocated.')
        self.assertEqual([(a['paymentReference'], a['receivedDate']) for a in row['allocations']], [('BCV-FIC-001', '2026-09-20')])

    def test_an_invoice_with_a_total_and_no_amount_still_owed_shows_the_replay_remainder_worked_out_with_the_original_amount(self):
        self.add_invoice(self.bayside, 'DEMO-602', issueDate='2026-09-30', dueDate='2026-10-30', total='1536.99')
        row = self.rows()['DEMO-602']
        self.assertEqual(row['totalText'], 'AUD 1,536.99 (as recorded), the original invoice amount')
        self.assertEqual(row['stillOwedText'], 'Still owed: AUD 1,536.99 (worked out: the invoice amount AUD 1,536.99 (as recorded) less the payments applied to it, '
                                               'by recorded allocation first and then oldest first).')
        self.assertEqual((row['mark'], row['amountText']), ('worked out', 'AUD 1,536.99 (worked out)'))
        self.assertEqual((row['allocationsText'], row['allocations'], row['settled']), ('No payment is allocated to this invoice.', [], False))

    def test_a_stated_amount_and_the_case_card_carry_the_same_labelled_figures(self):
        row = self.rows()['DEMO-501']
        self.assertEqual(row['totalText'], 'AUD 1,200.00 (as recorded), the original invoice amount')
        self.assertTrue(row['stillOwedText'].startswith('Still owed: '))
        got = self.ok('caseDetails', 'staff', requestId=self.r['id'])['case']['invoice']
        self.assertEqual(got['totalText'], 'AUD 1,200.00 (as recorded), the original invoice amount')
        self.assertIn('Still owed', got['stillOwedText'])
        self.assertIn('allocationsText', got)

    def test_a_case_on_a_part_paid_invoice_shows_the_allocated_payment(self):
        self.pay(self.bayside, next(i for i in self.app.fixture()['invoices'] if i['reference'] == 'DEMO-501'), '200.00', 'BCV-FIC-002', '2026-10-17')
        got = None
        for _ in range(100):   # the payment sends the case back through its analysis
            got = self.ok('caseDetails', 'staff', requestId=self.r['id'])['case']['invoice']
            if got and 'BCV-FIC-002' in got['allocationsText']:
                break
            time.sleep(0.1)
        self.assertEqual(got['totalText'], 'AUD 1,200.00 (as recorded), the original invoice amount')
        self.assertIn('BCV-FIC-002', got['allocationsText'])
        self.assertIn('AUD 200.00 (as recorded) allocated', got['allocationsText'])
        self.assertIn('Still owed: AUD 1,000.00 (at most, derived: the amount stated still owed AUD 1,200.00 (stated as of Fri 16 Oct 2026), less AUD 200.00 (as recorded) from payments after it)', got['stillOwedText'])
        self.assertFalse(got['settled'])

    # Repair A, F5a: a name or code given as customerId resolves as findCustomers matches it
    def test_a_name_or_code_as_customer_id_resolves_when_it_is_unique_and_asks_when_it_is_not(self):
        got = self.ok('invoices', 'staff', customerId='Bayside', which='all')
        self.assertEqual((got['customerId'], got['name']), (self.bayside['id'], self.bayside['name']))
        self.assertEqual(self.ok('invoices', 'staff', customerId=self.bayside['displayCode'], which='all')['customerId'], self.bayside['id'])
        self.add_customer('Bayside Bakery')
        message = self.refused_message('invoices', 'staff', customerId='Bayside', which='all')
        self.assertIn('Several customers match "Bayside"', message)
        self.assertIn('Bayside Bakery', message)
        self.assertIn('No customer matches "Zzyzx"', self.refused_message('invoices', 'staff', customerId='Zzyzx', which='all'))

    # Repair A, F5c: two options compared with the current due date and with each other, preparing nothing
    def test_compare_extension_takes_two_dates_and_compares_both_with_the_due_date_and_each_other(self):
        before = self.case()['version']
        c = self.ok('compareExtension', requestId=self.r['id'], date='2026-10-30', otherDate='2026-11-10')   # the owner's limit is 14 days
        self.assertEqual((c['proposedDate'], c['daysFromDue'], c['withinLimit'], c['currentDue']), ('2026-10-30', 10, True, '2026-10-20'))
        self.assertEqual((c['other']['proposedDate'], c['other']['proposedDateText'], c['other']['daysFromDue'], c['other']['withinLimit']),
                         ('2026-11-10', 'Tue 10 Nov 2026', 21, False))
        self.assertEqual(c['daysBetween'], 11)
        d = self.ok('compareExtension', requestId=self.r['id'], days=10, otherDays=40)
        self.assertEqual((d['daysFromDue'], d['other']['daysFromDue'], d['other']['withinLimit'], d['daysBetween']), (10, 40, False, 30))
        self.assertEqual(self.case()['version'], before)   # nothing prepared or recorded
        self.assertNotIn('other', self.ok('compareExtension', requestId=self.r['id'], days=10))
        self.assertEqual(self.refused('compareExtension', requestId=self.r['id'], days=10, otherDays=5, otherDate='2026-11-17'), 'INVALID_ARGUMENT')
        self.assertEqual(self.refused('compareExtension', requestId=self.r['id'], otherDays=5), 'MISSING')

    def refused_message(self, name, role, **args):
        status, body, _ = self.tool(name, role, None, **args)
        self.assertEqual((status, body.get('ok'), body.get('error')), (200, False, 'INVALID_ARGUMENT'), body)
        return body['message']


if __name__ == '__main__':
    unittest.main()
