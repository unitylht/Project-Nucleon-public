"""Presentation of a customer's position through the tool surface: overdue is worked out where no amount is recorded, a position from
stated amounts only is marked as stated, and a customer's code is taken for its id. All data is fictional. No real model is called."""
import unittest

import server

from test_payments import PaymentCase


class PresentationTests(PaymentCase):
    def two_invoices(self):
        self.ready()
        return (self.invoice('INV-1', dueDate='2026-10-10', stillOwed='1000.00', stillOwedAsOf='2026-10-18'),
                self.invoice('INV-2', total='300.00', dueDate='2026-11-30'))

    def tool(self, name, key, role='staff', **args):
        return self.call('/api/tools/' + name, {'args': args}, role, key)

    def test_overdue_is_worked_out_where_no_amount_is_recorded_and_not_known_only_with_no_due_date(self):
        self.ready()
        self.invoice('INV-1', dueDate='2026-10-10')   # no stillOwed: the replay leaves 1,000.00 on it, 8 days past its due date
        self.invoice('INV-2', issueDate='2026-10-02')   # no due date: owed, but whether it is overdue cannot be established
        tool = lambda name, **args: self.call('/api/tools/' + name, {'args': {'customerId': self.bayside['id'], **args}}, 'staff', name + str(args))[1]['result']
        o, i = tool('customerOverview'), tool('invoices', which='overdue')
        self.assertEqual((o['openCount'], o['overdueCount'], o['overdueText']), (2, 1, '2 open invoices, 1 overdue; overdue not known for 1 invoice with no due date'))
        self.assertEqual((i['invoiceCount'], i['unknownCount'], i['summaryText']), (1, 1, 'Overdue not known for 1 open invoice: no due date is recorded.'))
        self.assertNotIn('unknownCount', tool('invoices', which='open'))

    def test_a_position_from_stated_amounts_only_is_marked_stated(self):
        self.start(mode='mock', sample_data=True)   # the sample's invoices carry only stated amounts still owed, no totals
        ids = {c['name'].split()[-1]: c['id'] for c in self.call('/api/records', role='owner')[1]['customers']}
        o = self.call('/api/tools/customerOverview', {'args': {'customerId': ids['Logistics']}}, 'staff', 'stated')[1]['result']
        self.assertEqual(o['statedTotal']['amount'], 'AUD 2,580.00')
        self.assertTrue(o['balanceLine'].startswith('Owed now AUD 2,580.00 (worked out; invoices not confirmed complete; payments not confirmed complete)'), o['balanceLine'])
        self.assertIn('DEMO-201 AUD 480.00 (stated); DEMO-202 AUD 2,100.00 (stated)', o['balanceLine'])   # each invoice stays as stated
        self.assertEqual((o['openCount'], o['overdueCount']), (2, 1))

    def test_a_customer_s_code_is_taken_for_its_id(self):
        self.two_invoices()
        code = self.bayside['displayCode']   # as the customer list shows it
        for given in (code, code.lower()):
            status, body, _ = self.tool('customerOverview', 'c-' + given, customerId=given)
            self.assertEqual((status, body['ok'], body['result']['name'], body['result']['customerId']), (200, True, 'Bayside Café', self.bayside['id']))
        status, body, _ = self.tool('customerOverview', 'c-x', customerId='C-NOWHERE')   # a code no customer has is still refused
        self.assertEqual((status, body['ok']), (200, False))


class StillOwedHeader(unittest.TestCase):
    VND = {'currency': 'VND', 'scale': 0}

    def amount(self, minor):
        return {**self.VND, 'minorUnits': str(minor)}

    def test_an_invoice_with_a_total_and_no_stated_amount_says_what_is_known(self):
        f = {'invoiceOutstanding': None, 'invoiceTotal': self.amount(5000000),
             'unmatchedPayments': {'count': 2, 'amount': self.amount(2500000)}}
        self.assertEqual(server.case_amount(f)['markDetail'], 'Invoice VND 5,000,000 \u00b7 VND 0 allocated \u00b7 still owed not stated. '
                         '2 unmatched payments for this customer (VND 2,500,000) may apply')
        f['unmatchedPayments'] = None
        self.assertEqual(server.case_amount(f)['markDetail'], 'Invoice VND 5,000,000 \u00b7 VND 0 allocated \u00b7 still owed not stated')

    def test_the_old_sentence_stays_when_there_is_neither_a_total_nor_a_stated_amount(self):
        self.assertIn('no amount still owed is stated, and no payments are allocated', server.case_amount({'invoiceOutstanding': None})['markDetail'])


if __name__ == '__main__':
    unittest.main()
