"""An exact amount still owed (Stage 3, P002 section 8.3). Only when every prerequisite holds: the invoice amount is known, its
starting amount is known (dated after the customer's base, or part of the opening balance with what was still owed then), the
customer's payments are confirmed complete, every payment in that period is allocated or marked as not for an open invoice, and
nothing about the customer is unresolved. Otherwise the reasons are given in plain words. All data is fictional."""
import unittest

from test_coverage import CoverageCase


class ExactCase(CoverageCase):
    def exact(self, invoice):
        return (self.positions()['invoices'].get(invoice['id']) or {}).get('exact')

    def not_exact(self, invoice):
        return ' '.join(self.positions()['notExact'].get(invoice['id'], []))

    def complete_from_opening(self, end='2026-10-18', amount='0.00'):
        self.opening(amount=amount, credits='none')                   # as at 30 Sep, said to include no credits
        self.attest(start='2026-10-01', end=end)

    def unrelated(self, payment, value=True, expect=200, key=None):
        status, result, _ = self.call('/api/records/payments/' + payment['id'] + '/unrelated', {'unrelated': value, 'reason': 'Deposit for a future order'},
                                      'staff', key or 'un-' + payment['id'] + str(value))
        self.assertEqual(status, expect, result)
        return result


class ExactAmountTests(ExactCase):
    def test_an_exact_amount_needs_complete_payment_records(self):
        self.ready()
        invoice = self.invoice('INV-1', total='1000.00', issueDate='2026-10-05')
        self.allocate(self.pay('600.00', date='2026-10-12'), (invoice, '600.00'))
        self.assertIsNone(self.exact(invoice))
        self.assertIn('no confirmed completeness', self.not_exact(invoice))
        self.complete_from_opening()
        exact = self.exact(invoice)
        self.assertEqual((self.minor(exact['amount']), exact['asOf'], exact['basis']), ('40000', '2026-10-18', 'total'))
        self.assertEqual([(s['label'], self.minor(s['amount'])) for s in exact['steps']],
                         [('Invoice amount', '100000'), ('Payments and credits allocated to it up to Sun 18 Oct 2026', '-60000')])

    def test_a_late_entry_is_named_when_exactness_is_withdrawn(self):   # QA U7
        self.ready()
        invoice = self.invoice('INV-1', total='1000.00', issueDate='2026-10-05')
        self.allocate(self.pay('600.00', date='2026-10-12'), (invoice, '600.00'))
        self.complete_from_opening()
        self.assertIsNotNone(self.exact(invoice))
        late = self.pay('10.00', date='2026-10-14', reference='LATE-ENTRY')   # recorded after the statement, inside its period
        self.assertIsNone(self.exact(invoice))
        why = self.not_exact(invoice)
        self.assertIn('no confirmed completeness from Thu 1 Oct 2026, the day after the opening balance', why)   # not "from Wed 30 Sep"
        self.assertIn('The statement that they were complete from Thu 1 Oct 2026 to Sun 18 Oct 2026 no longer holds: LATE-ENTRY was added '
                      'inside that period after it was confirmed', why)
        changes = self.coverage()['contradicted'][0]['changes']
        self.assertEqual(changes, [{'id': late['id'], 'record': 'LATE-ENTRY', 'change': 'added'}])

    def test_money_neither_allocated_nor_marked_unrelated_blocks_it(self):
        self.ready()
        invoice = self.invoice('INV-1', total='1000.00', issueDate='2026-10-05')
        deposit = self.pay('50.00', date='2026-10-14', reference='Deposit')    # recorded before completeness is confirmed
        self.complete_from_opening()
        self.assertIn('neither allocated nor marked', self.not_exact(invoice))
        self.unrelated(deposit)
        self.assertEqual(self.minor(self.exact(invoice)['amount']), '100000')   # complete records, nothing paid: exactly the invoice amount
        customer = self.positions()['customers'][self.bayside['id']]
        self.assertEqual((self.minor(customer['markedUnrelated']), self.minor(customer['unallocatedOpen'])), ('5000', '0'))
        self.unrelated(deposit, False, key='undo')
        self.assertIsNone(self.exact(invoice))

    def test_an_invoice_from_before_the_opening_balance_needs_what_was_owed_on_it_then(self):
        self.ready()
        self.opening(amount='1200.00', credits='none')
        invoice = self.invoice('INV-77', total='1500.00', issueDate='2026-09-15')
        self.allocate(self.pay('200.00', date='2026-10-05'), (invoice, '200.00'))
        self.attest(start='2026-10-01', end='2026-10-18')
        self.assertIn('part of the opening balance', self.not_exact(invoice))
        self.include('invoices', invoice, 'included')
        self.assertIn('still owed on it at', self.not_exact(invoice))
        self.include('invoices', invoice, 'included', stillOwed='1200.00', key='with-amount')
        exact = self.exact(invoice)
        self.assertEqual((self.minor(exact['amount']), exact['basis']), ('100000', 'opening'))   # 1,200 at 30 Sep, less 200 on 5 Oct

    def test_anything_unresolved_about_the_customer_blocks_it(self):
        self.ready()
        self.complete_from_opening()
        invoice = self.invoice('INV-1', total='1000.00', issueDate='2026-10-05')
        self.assertIsNotNone(self.exact(invoice))
        self.invoice('INV-0', total='300.00', issueDate='2026-09-20')            # before the opening balance, not answered
        self.assertIsNone(self.exact(invoice))
        self.assertIn('not yet answered', self.not_exact(invoice))

    def test_a_statement_that_disagrees_with_complete_records_blocks_it(self):
        self.ready()
        self.complete_from_opening()
        invoice = self.invoice('INV-1', total='1000.00', issueDate='2026-10-05', stillOwed='400.00', stillOwedAsOf='2026-10-09')
        self.assertIn('does not match', self.not_exact(invoice))                # complete records show nothing paid by 9 Oct

    def test_a_record_added_inside_the_confirmed_period_withdraws_it(self):
        self.ready()
        invoice = self.invoice('INV-1', total='1000.00', issueDate='2026-10-05')
        self.complete_from_opening()
        self.assertIsNotNone(self.exact(invoice))
        self.pay('25.00', date='2026-10-08')
        self.assertIsNone(self.exact(invoice))
        self.assertIn('no confirmed completeness', self.not_exact(invoice))


class ExactInCasesTests(ExactCase):
    def facts_and_items(self, r):
        return {f['key']: f for f in r['analysis']['brief']['facts']}, {i['kind']: i['text'] for i in r['analysis']['brief']['openItems']}

    def test_the_owner_sees_the_exact_amount_with_its_basis_and_as_of_date(self):
        self.ready()
        invoice = self.invoice('DEMO-501', total='1000.00', issueDate='2026-10-05', dueDate='2026-10-10')
        self.allocate(self.pay('600.00', date='2026-10-12'), (invoice, '600.00'))
        self.complete_from_opening()
        facts, items = self.facts_and_items(self.wait_status(self.create(), ('awaiting_owner',)))
        amount = facts['outstandingAmount']
        self.assertEqual((amount['kind'], self.minor(amount['value']), amount['asOf']), ('calculation', '40000', '2026-10-18'))
        self.assertIn('exact', amount['display'])
        self.assertEqual(facts['daysOverdue']['value'], 8)                     # complete to today, so overdue can be stated
        self.assertIn('confirmed complete', items['exact_outstanding'])
        self.assertIn('not this invoice', items['customer_balance'])

    def test_days_overdue_are_not_stated_when_records_are_complete_only_to_an_earlier_day(self):
        self.ready()
        self.invoice('DEMO-501', total='1000.00', issueDate='2026-10-05', dueDate='2026-10-10')
        self.complete_from_opening(end='2026-10-16')
        facts, _ = self.facts_and_items(self.wait_status(self.create(), ('awaiting_owner',)))
        self.assertEqual((facts['outstandingAmount']['asOf'], facts['daysOverdue']['value']), ('2026-10-16', None))
        self.assertIn('Fri 16 Oct 2026', facts['daysOverdue']['reason'])

    def test_an_invoice_paid_in_full_by_complete_records_goes_back_to_staff(self):
        self.ready()
        invoice = self.invoice('DEMO-501', total='1000.00', issueDate='2026-10-05')
        self.invoice('DEMO-502', issueDate='2026-10-06')
        self.allocate(self.pay('1000.00', date='2026-10-12'), (invoice, '1000.00'))
        self.complete_from_opening()
        r = self.wait_status(self.create(), ('needs_information',))
        self.assertIn('cover it in full', r['task']['question'])

    def test_the_owner_is_told_in_plain_words_why_an_amount_is_not_exact(self):
        self.ready()
        self.opening(amount='0.00')
        invoice = self.invoice('DEMO-501', total='1000.00', issueDate='2026-10-05')
        self.allocate(self.pay('300.00', date='2026-10-12'), (invoice, '300.00'))
        _, items = self.facts_and_items(self.wait_status(self.create(), ('awaiting_owner',)))
        self.assertIn('no confirmed completeness', items['not_exact'])

    def test_the_no_ai_path_shows_the_same_exact_amount(self):
        self.start(mode='unavailable')
        self.practice_ready()
        self.bayside, self.coastline = self.add_customer('Bayside Café'), self.add_customer('Coastline Foods')
        invoice = self.invoice('DEMO-501', total='1000.00', issueDate='2026-10-05', dueDate='2026-10-10')
        self.allocate(self.pay('600.00', date='2026-10-12'), (invoice, '600.00'))
        self.complete_from_opening()
        r = self.wait_status(self.create(), ('awaiting_owner',))
        facts, items = self.facts_and_items(r)
        self.assertEqual((r['analysis']['aiStatus'], facts['outstandingAmount']['kind'], self.minor(facts['outstandingAmount']['value'])),
                         ('failed', 'calculation', '40000'))
        self.assertIn('exact_outstanding', items)


if __name__ == '__main__':
    unittest.main()
