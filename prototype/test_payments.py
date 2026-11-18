"""Payments and explicit allocations (Stage 3): recording, allocating, correcting, removing, and what the records
support about settlement. Absent payments prove nothing; nothing is ever claimed exact. All data is fictional."""
import json
import unittest

from test_records import RecordsCase


class PaymentCase(RecordsCase):
    def ready(self):
        self.start()
        self.practice_ready()
        self.bayside = self.add_customer('Bayside Café')
        self.coastline = self.add_customer('Coastline Foods')

    def invoice(self, reference, total='1000.00', customer=None, **values):
        return self.add_invoice(customer or self.bayside, reference=reference, total=total, **{'issueDate': '2026-10-01', **values})

    def pay(self, amount, date='2026-10-12', reference=None, customer=None, expect=200, key=None, **extra):
        body = {'customerId': (customer or self.bayside)['id'], 'receivedDate': date, 'amount': amount, 'reference': reference, **extra}
        status, result, _ = self.call('/api/records/payments', body, 'staff', key or 'p-' + json.dumps(body, sort_keys=True))
        self.assertEqual(status, expect, result)
        return result.get('record', result)

    def allocate(self, payment, *pairs, expect=200, key=None):
        body = {'paymentId': payment['id'], 'allocations': [{'invoiceId': i['id'], 'amount': a} for i, a in pairs]}
        status, result, _ = self.call('/api/records/allocations', body, 'staff', key or 'a-' + json.dumps(body, sort_keys=True))
        self.assertEqual(status, expect, result)
        return result

    def positions(self):
        return self.call('/api/records', role='staff')[1]['positions']

    def minor(self, money):
        return money and money['minorUnits']


class PaymentRecordTests(PaymentCase):
    def test_a_payment_can_be_split_across_invoices_and_the_rest_stays_unallocated(self):
        self.ready()
        first, second = self.invoice('INV-1'), self.invoice('INV-2', total='500.00')
        payment = self.pay('1300.00', reference='EFT 7781')
        self.allocate(payment, (first, '1000.00'), (second, '100.00'))
        positions = self.positions()
        one, two = positions['invoices'][first['id']], positions['invoices'][second['id']]
        self.assertEqual((one['status'], self.minor(one['atMost']), self.minor(one['allocated'])), ('settled', '0', '100000'))
        self.assertEqual((two['status'], self.minor(two['atMost']), self.minor(two['allocated'])), ('open', '40000', '10000'))
        customer = positions['customers'][self.bayside['id']]
        self.assertEqual((self.minor(customer['paymentsRecorded']), self.minor(customer['unallocated']), self.minor(customer['recordedNet'])),
                         ('130000', '20000', '20000'))

    def test_allocations_stay_within_the_payment_the_invoice_and_the_customer(self):
        self.ready()
        mine, theirs = self.invoice('INV-1'), self.invoice('INV-9', customer=self.coastline)
        payment = self.pay('600.00')
        self.assertEqual(self.allocate(payment, (theirs, '100.00'), expect=400)['error'], 'OTHER_CUSTOMER')
        self.assertEqual(self.allocate(payment, (mine, '700.00'), expect=422)['error'], 'OVER_PAYMENT')
        self.assertEqual(self.allocate(payment, (mine, '0'), expect=400)['field'], 'amount')
        self.assertEqual(self.allocate(payment, (mine, '100.00'), (mine, '100.00'), expect=400)['field'], 'invoiceId')
        self.allocate(payment, (mine, '600.00'))
        other = self.pay('500.00', date='2026-10-13')
        self.assertEqual(self.allocate(other, (mine, '500.00'), expect=422)['error'], 'OVER_INVOICE')   # only 400.00 left on INV-1
        self.allocate(other, (mine, '400.00'))
        self.assertEqual(self.minor(self.positions()['customers'][self.bayside['id']]['unallocated']), '10000')

    def test_possible_duplicate_payments_need_a_person_to_confirm(self):
        self.ready()
        self.pay('250.00', reference='EFT 100')
        duplicate = self.pay('250.00', date='2026-10-13', reference='eft 100', expect=409)
        self.assertEqual((duplicate['error'], duplicate['field']), ('POSSIBLE_DUPLICATE', 'reference'))
        self.pay('250.00', date='2026-10-13', reference='eft 100', confirmDistinct=True)
        self.pay('80.00', date='2026-10-14')
        self.assertEqual(self.pay('80.00', date='2026-10-14', expect=409, key='again')['error'], 'POSSIBLE_DUPLICATE')

    def test_corrections_and_removals_respect_allocations(self):
        self.ready()
        invoice = self.invoice('INV-1')
        payment = self.pay('600.00')
        allocation = self.allocate(payment, (invoice, '400.00'))['records'][0]
        status, error, _ = self.correct('payments', payment, amount='300.00', reason='Bank fee')
        self.assertEqual((status, error['error']), (409, 'ALLOCATED'))
        status, fixed, _ = self.correct('payments', payment, amount='580.00', reason='Bank fee deducted')
        self.assertEqual((status, fixed['record']['version'], fixed['record']['history'][0]['values']['amount']['minorUnits']), (200, 2, '60000'))
        self.assertEqual(self.call('/api/records/payments/' + payment['id'] + '/remove', {'reason': 'Entered twice'}, 'staff', 'r1')[1]['error'], 'REMOVE_BLOCKED')
        self.assertEqual(self.call('/api/records/invoices/' + invoice['id'] + '/remove', {'reason': 'Wrong'}, 'staff', 'r2')[1]['error'], 'REMOVE_BLOCKED')
        self.assertEqual(self.call('/api/records/allocations/' + allocation['id'] + '/remove', {'reason': 'Wrong invoice'}, 'staff', 'r3')[0], 200)
        self.assertEqual(self.call('/api/records/payments/' + payment['id'] + '/remove', {'reason': 'Entered twice'}, 'staff', 'r4')[0], 200)
        self.assertEqual(self.positions()['invoices'], {})

    def test_a_statement_of_what_was_owed_counts_only_later_payments(self):
        self.ready()
        invoice = self.invoice('INV-1', stillOwed='800.00', stillOwedAsOf='2026-10-10')
        self.allocate(self.pay('200.00', date='2026-10-08'), (invoice, '200.00'))   # before the statement: 1,000 - 200 = 800 reconciles
        early = self.positions()['invoices'][invoice['id']]
        self.assertEqual((self.minor(early['atMost']), len(early['inclusion']['reconciles'])), ('80000', 1))
        self.allocate(self.pay('300.00', date='2026-10-12'), (invoice, '300.00'))
        position = self.positions()['invoices'][invoice['id']]
        self.assertEqual((position['basis'], self.minor(position['atMost']), position['statedAsOf']), ('stated', '50000', '2026-10-10'))


class SettlementInCasesTests(PaymentCase):
    def brief(self, r):
        return {f['key']: f for f in r['analysis']['brief']['facts']}, [i['kind'] for i in r['analysis']['brief']['openItems']]

    def test_absent_payments_prove_nothing(self):
        self.ready()
        self.invoice('DEMO-501', total='1000.00', dueDate='2026-10-10')
        r = self.wait_status(self.create(), ('awaiting_owner',))
        facts, items = self.brief(r)
        self.assertEqual((facts['outstandingAmount']['kind'], facts['daysOverdue']['value']), ('unknown', None))   # not 'unpaid', not 'overdue'
        self.assertNotIn('overdue.', r['analysis']['brief']['summary'])

    def test_a_partly_paid_invoice_reaches_the_owner_with_an_upper_bound_only(self):
        self.ready()
        invoice = self.invoice('DEMO-501', total='1000.00', dueDate='2026-10-10')
        payment = self.pay('500.00')
        self.allocate(payment, (invoice, '300.00'))
        r = self.wait_status(self.create(), ('awaiting_owner',))
        facts, items = self.brief(r)
        self.assertEqual((facts['outstandingAmount']['kind'], facts['outstandingAmount']['value']['minorUnits']), ('bounded', '70000'))
        self.assertIn('At most', facts['outstandingAmount']['display'])
        self.assertIsNone(facts['daysOverdue']['value'])
        self.assertTrue({'payments_allocated', 'unallocated_payments', 'recorded_net'} <= set(items), items)

    def test_a_settled_invoice_goes_back_to_staff_with_the_reason(self):
        self.ready()
        invoice = self.invoice('DEMO-501', total='1000.00')
        self.allocate(self.pay('1000.00'), (invoice, '1000.00'))
        self.invoice('DEMO-502')   # keeps the workspace ready: another open invoice
        r = self.wait_status(self.create(), ('needs_information',))
        self.assertIn('cover it in full', r['task']['question'])

    def test_a_customer_with_unallocated_money_is_not_treated_as_paid(self):
        self.ready()
        self.invoice('DEMO-501', total='1000.00')
        self.pay('1000.00', date='2026-10-01', reference='Deposit')   # net of records is zero, but nothing is allocated
        r = self.wait_status(self.create(), ('awaiting_owner',))
        facts, items = self.brief(r)
        self.assertEqual(facts['outstandingAmount']['kind'], 'unknown')
        self.assertIn('unallocated_payments', items)
        self.assertEqual(self.minor(self.positions()['customers'][self.bayside['id']]['recordedNet']), '0')

    def test_removing_an_allocation_flags_a_decided_case_and_never_changes_it(self):
        self.ready()
        invoice = self.invoice('DEMO-501', total='1000.00')
        allocation = self.allocate(self.pay('400.00'), (invoice, '400.00'))['records'][0]
        r = self.wait_status(self.create(), ('awaiting_owner',))
        self.assertEqual(self.decide(r)[0], 201)
        path = '/api/records/allocations/' + allocation['id'] + '/remove'
        self.assertEqual(self.call(path, {'reason': 'Belongs to INV-2'}, 'staff', 'x1')[1]['error'], 'REVIEW_REQUIRED')
        self.assertEqual(self.call(path, {'reason': 'Belongs to INV-2', 'confirm': True}, 'staff', 'x2')[0], 200)
        done = self.wait_status(r, ('completed',))
        self.assertEqual((done['decision']['outcome'], [f['kind'] for f in done['flags']]), ('approve', ['records_changed_after_decision']))

    def test_an_invoice_import_cannot_be_reverted_under_allocations(self):
        self.ready()
        first = self.call('/api/imports', {'sourceLabel': 'Sheet', 'fileName': 'a.csv', 'csvText': 'Customer,Invoice,Date,Amount\nBayside Café,INV-77,2026-10-01,900.00\n'}, 'staff', 'u')[1]
        self.call('/api/imports/' + first['id'] + '/apply', {}, 'staff', 'ap')
        invoice = next(i for i in self.app.fixture()['invoices'] if i['reference'] == 'INV-77')
        self.allocate(self.pay('900.00'), (invoice, '900.00'))
        status, error, _ = self.call('/api/imports/' + first['id'] + '/revert', {'reason': 'Wrong file'}, 'staff', 'rv')
        self.assertEqual((status, error['error']), (409, 'REVERT_BLOCKED'))
        self.assertIn('allocated', ' '.join(error['impact']['blocked']))


if __name__ == '__main__':
    unittest.main()
