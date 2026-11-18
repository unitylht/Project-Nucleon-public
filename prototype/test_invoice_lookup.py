"""The invoices tool finds the invoice numbers Staff name, and gives the model a short row per invoice (Hoang's NTK round, 9 Nov 2026: with 20-28 invoices the
full result was 19-28 thousand characters, and the model said invoices that were in it did not exist). Fictional data. No real model is called."""
import json
import unittest

from test_payments import PaymentCase
from test_tool_reads import ToolReadTests


class InvoiceLookupTests(PaymentCase):
    run_tool, ok = ToolReadTests.run_tool, ToolReadTests.ok   # the helpers only, not the inherited tests

    def many(self, n=25):
        self.ready()
        for k in range(1, n + 1):
            self.invoice('INV-%02d' % k, total='%d.00' % (100 + k))

    def test_a_named_invoice_number_is_found_by_code(self):
        self.many()
        r = self.ok('invoices', customerId=self.bayside['id'], which='open', reference=['inv-17 '])
        self.assertEqual([i['reference'] for i in r['invoices']], ['INV-17'])
        self.assertEqual(r['which'], 'all')   # a named invoice is found whatever its status
        self.assertEqual([i['reference'] for i in r['forModel']['invoices']], ['INV-17'])
        self.assertIn('invoice number inv-17', r['forModel']['filter']['text'])

    def test_a_number_of_another_customer_says_whose_it_is(self):
        self.many(2)
        other = self.add_customer('Riverside Bakery')
        self.invoice('RB-9', customerId=other['id'])
        r = self.ok('invoices', customerId=self.bayside['id'], which='all', reference=['RB-9', 'NOPE-1'])
        self.assertEqual(r['invoices'], [])
        self.assertIn("Invoice RB-9 is not one of Bayside Café's; it is recorded for Riverside Bakery.", r['forModel']['filter']['noneText'])
        self.assertIn('Invoice NOPE-1 is not recorded for Bayside Café or any other customer.', r['forModel']['filter']['noneText'])

    def test_the_model_reads_every_invoice_in_a_short_row(self):
        self.many()
        r = self.ok('invoices', customerId=self.bayside['id'], which='all')
        rows = r['forModel']['invoices']
        self.assertEqual(len(rows), 25)
        self.assertEqual(len(rows), r['invoiceCount'])
        self.assertTrue(all('allocations' not in x for x in rows))
        self.assertLess(len(json.dumps(r['forModel'], ensure_ascii=False)), len(json.dumps(r, ensure_ascii=False)) / 2)
        self.assertIn('scopeText', r['forModel'])

    def test_resolve_decision_names_the_customer_an_invoice_number_belongs_to(self):
        self.ready()
        other = self.add_customer('Riverside Bakery')
        self.invoice('RB-9', customerId=other['id'])
        self.assertEqual(self.call('/api/agent-tools', {'tool': 'resolveDecision', 'enabled': True}, 'owner', 'on-resolve')[0], 200)
        out = self.run_tool('resolveDecision', key='rd-other', customerId=self.bayside['id'], kind='extension', invoiceReference='RB-9', days=10, recommendation='approve', reasoning='Fictional.')
        self.assertEqual(out['error'], 'NOT_FOUND', out)
        self.assertIn('Invoice RB-9 is recorded for Riverside Bakery: ask Staff which customer they mean', out['message'])
        self.assertEqual(out['hint']['ask'], 'customer')   # not a list of Bayside's invoices to pick from
        self.assertEqual(out['hint']['options'], ['Riverside Bakery', 'Bayside Café'])

    def test_a_bad_reference_is_refused(self):
        self.ready()
        out = self.run_tool('invoices', customerId=self.bayside['id'], which='all', reference=[''])
        self.assertEqual((out['ok'], out['error']), (False, 'INVALID_ARGUMENT'))


if __name__ == '__main__':
    unittest.main()
