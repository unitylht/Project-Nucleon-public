"""Opening balances and inclusion (Stage 3, P002 section 8.1). A customer's opening balance summarises everything up to its
as-at date. Each invoice or payment dated on or before it is included in it, missed from it, or unresolved (the default);
later ones are new activity. Nothing is counted twice, and nothing is assumed. All data is fictional."""
import unittest

from test_payment_import import SAMPLES, PaymentImportCase


class OpeningCase(PaymentImportCase):
    def opening(self, customer=None, amount='5000.00', as_of='2026-09-30', direction='owed', expect=200, key=None, **extra):
        body = {'customerId': (customer or self.bayside)['id'], 'asOf': as_of, 'amount': amount, 'direction': direction,
                'sourceLabel': "Accountant's balance list", **extra}
        status, result, _ = self.call('/api/records/openingBalances', body, 'staff', key or 'ob-' + str(sorted(body.items())))
        self.assertEqual(status, expect, result)
        return result.get('record', result)

    def include(self, kind, record, status, expect=200, key=None, **extra):
        code, result, _ = self.call('/api/records/' + kind + '/' + record['id'] + '/inclusion', {'status': status, **extra}, 'staff',
                                    key or 'inc-' + record['id'] + status + str(sorted(extra.items())))
        self.assertEqual(code, expect, result)
        return result

    def view(self, customer=None):
        return self.positions()['customers'][(customer or self.bayside)['id']]['opening']

    def statuses(self, customer=None):
        return {r['reference']: r['status'] for r in self.view(customer)['records']}


class OpeningBalanceTests(OpeningCase):
    def test_an_opening_balance_has_a_date_a_source_and_who_entered_it(self):
        self.ready()
        ob = self.opening()
        self.assertEqual((ob['asOf'], ob['amount']['minorUnits'], ob['sourceLabel'], ob['origin']['role'], ob['credits']),
                         ('2026-09-30', '500000', "Accountant's balance list", 'staff', None))
        self.assertEqual(self.opening(amount='10.00', expect=409, key='again')['error'], 'OPENING_EXISTS')
        credit = self.opening(self.coastline, amount='200.00', direction='credit')
        self.assertEqual(credit['amount']['minorUnits'], '-20000')
        self.assertEqual(self.opening(self.add_customer('Dune Traders'), as_of='2026-10-19', expect=400, key='future')['field'], 'asOf')
        status, fixed, _ = self.correct('openingBalances', ob, amount='5200.00', reason='Accountant revised it')
        self.assertEqual((status, fixed['record']['version'], fixed['record']['history'][0]['values']['amount']['minorUnits']), (200, 2, '500000'))

    def test_records_before_the_as_at_date_are_unresolved_until_answered_and_later_ones_are_new(self):
        self.ready()
        self.opening()
        self.invoice('INV-77', total='1200.00', issueDate='2026-09-15')
        self.invoice('INV-90', total='800.00', issueDate='2026-10-05')
        self.pay('300.00', date='2026-10-03', reference='EFT 1')
        self.pay('100.00', date='2026-09-20', reference='EFT 0')
        view = self.view()
        self.assertEqual(self.statuses(), {'INV-77': 'unresolved', 'INV-90': 'new', 'EFT 1': 'new', 'EFT 0': 'unresolved'})
        self.assertEqual(self.minor(view['balance']), '550000')                      # 5,000 + 800 new - 300 new
        self.assertEqual((self.minor(view['unresolvedInvoices']['amount']), self.minor(view['unresolvedPayments']['amount'])), ('120000', '10000'))

    def test_an_included_invoice_explains_the_balance_and_a_missed_one_adds_to_it(self):
        self.ready()
        self.opening()
        included = self.invoice('INV-77', total='1200.00', issueDate='2026-09-15', inclusion='included')   # asked at entry
        missed = self.invoice('INV-78', total='400.00', issueDate='2026-09-20')
        self.include('invoices', missed, 'missed')
        self.assertEqual(self.statuses(), {'INV-77': 'included', 'INV-78': 'missed'})
        self.assertEqual(self.minor(self.view()['balance']), '540000')               # included adds nothing; missed adds 400
        self.include('invoices', included, 'unsure')
        self.assertEqual(self.statuses()['INV-77'], 'unresolved')
        record = next(i for i in self.app.fixture()['invoices'] if i['id'] == included['id'])
        self.assertEqual([a['value'] and a['value']['status'] for a in record['answers']], ['included', None])   # answers keep their history

    def test_an_included_invoice_can_say_what_was_still_owed_at_the_as_at_date(self):
        self.ready()
        self.opening(amount='1200.00')
        invoice = self.invoice('INV-77', total='1500.00', issueDate='2026-09-15')
        self.include('invoices', invoice, 'included', stillOwed='1200.00')
        record = next(i for i in self.app.fixture()['invoices'] if i['id'] == invoice['id'])
        self.assertEqual((record['outstandingAmount']['minorUnits'], record['outstandingAsOf'], record['outstandingSource']), ('120000', '2026-09-30', 'opening_balance'))
        later = self.invoice('INV-79', total='500.00', issueDate='2026-09-16', stillOwed='500.00', stillOwedAsOf='2026-10-10')
        self.assertEqual(self.include('invoices', later, 'included', stillOwed='500.00', expect=409)['error'], 'LATER_STATEMENT')

    def test_included_invoices_may_add_up_to_more_than_a_net_opening_balance(self):
        self.ready()
        self.opening(amount='1000.00')
        for ref, total in (('INV-1', '1200.00'), ('INV-2', '300.00')):
            self.include('invoices', self.invoice(ref, total=total, issueDate='2026-09-10'), 'included', stillOwed=total)
        view = self.view()
        self.assertEqual((self.minor(view['impliedCredits']), view['conflicts']), ('50000', []))   # credits or prepayments, not an error
        self.correct('openingBalances', self.app.fixture()['openingBalances'][0], credits='none', reason='Statement shows no credits')
        self.assertTrue(self.view()['conflicts'])

    def test_invoices_whose_amounts_at_the_as_at_date_add_up_to_it_are_suggested_not_included(self):
        self.records_setup()                                                      # invoice list, amounts as of 9 Oct
        bayside = self.customers['Bayside Café']
        self.opening(bayside, amount='1400.00', as_of='2026-10-09')               # Bayside's invoices: 1,000 + 400 still owed on 9 Oct
        self.assertEqual(self.statuses(bayside), {'INV-1001': 'unresolved', 'INV-1002': 'unresolved'})
        self.assertEqual(sorted(self.view(bayside)['suggestion']['references']), ['INV-1001', 'INV-1002'])
        self.correct('openingBalances', self.app.fixture()['openingBalances'][0], amount='1500.00', reason='Revised')
        self.assertIsNone(self.view(bayside)['suggestion'])

    def test_answers_stop_applying_when_the_as_at_date_is_corrected(self):
        self.ready()
        ob = self.opening()
        self.invoice('INV-77', total='1200.00', issueDate='2026-09-15', inclusion='included')
        self.invoice('INV-80', total='100.00', issueDate='2026-09-28', inclusion='missed')
        self.correct('openingBalances', ob, asOf='2026-09-25', reason='Wrong date')
        view = self.view()
        self.assertEqual(self.statuses(), {'INV-77': 'unresolved', 'INV-80': 'new'})
        self.assertEqual(view['staleAnswers'], 1)

    def test_a_record_after_the_as_at_date_has_nothing_to_answer(self):
        self.ready()
        self.opening()
        later = self.invoice('INV-90', total='800.00', issueDate='2026-10-05')
        self.assertEqual(self.include('invoices', later, 'included', expect=409)['error'], 'NOT_APPLICABLE')
        self.assertEqual(self.include('invoices', self.invoice('INV-91', issueDate='2026-10-06', customer=self.coastline), 'included',
                                      expect=409)['error'], 'NO_OPENING')

    def test_removing_the_opening_balance_needs_review_when_cases_use_the_customer(self):
        self.ready()
        ob = self.opening()
        self.invoice('DEMO-501', total='1000.00', issueDate='2026-10-01')
        self.wait_status(self.create(), ('awaiting_owner',))
        path = '/api/records/openingBalances/' + ob['id'] + '/remove'
        self.assertEqual(self.call(path, {'reason': 'Wrong customer'}, 'staff', 'r1')[1]['error'], 'REVIEW_REQUIRED')
        self.assertEqual(self.call(path, {'reason': 'Wrong customer', 'confirm': True}, 'staff', 'r2')[0], 200)
        self.assertIsNone(self.view())

    def test_an_opening_balance_for_one_customer_leaves_other_customers_cases_alone(self):
        self.ready()
        self.invoice('DEMO-501', total='1000.00', issueDate='2026-10-01')
        self.invoice('DEMO-601', total='700.00', issueDate='2026-10-01', customer=self.coastline)
        mine = self.wait_status(self.create(), ('awaiting_owner',))
        theirs = self.wait_status(self.create('Could we pay invoice DEMO-601 on 2026-10-30 instead?', key='theirs'), ('awaiting_owner',))
        self.opening(self.coastline, amount='700.00')
        self.assertEqual(self.reopen(mine)['analysis']['id'], mine['analysis']['id'])
        self.assertNotEqual(self.wait_status(theirs, ('awaiting_owner',))['analysis']['id'], theirs['analysis']['id'])

    def test_the_owner_sees_the_customer_balance_separately_from_the_invoice(self):
        self.ready()
        self.opening(amount='1000.00')
        self.invoice('INV-77', total='1200.00', issueDate='2026-09-15')
        self.invoice('DEMO-501', total='600.00', issueDate='2026-10-02')
        r = self.wait_status(self.create(), ('awaiting_owner',))
        items = {i['kind']: i['text'] for i in r['analysis']['brief']['openItems']}
        self.assertIn('not this invoice', items['customer_balance'])
        self.assertIn('AUD 1,600.00', items['customer_balance'])                       # 1,000 + 600 new
        self.assertIn('INV-77', items['opening_inclusion_unresolved'])
        self.assertIn('entered by staff', items['customer_balance'])                   # QA B2: who entered the figure is shown
        self.assertIn('Neither invoice nor payment records', items['customer_balance'])

    def test_the_brief_names_which_record_type_is_complete(self):   # QA U8: "payments are complete" then "records are not complete"
        self.ready()
        self.call('/api/records/openingBalances', {'customerId': self.bayside['id'], 'asOf': '2026-09-30', 'amount': '0.00', 'direction': 'owed',
                                                    'credits': 'none', 'sourceLabel': 'Starts from zero'}, 'owner', 'ob-owner')
        self.invoice('DEMO-501', total='600.00', issueDate='2026-10-02')
        self.call('/api/records/coverage', {'customers': [self.bayside['id']], 'recordTypes': ['payments'], 'from': '2026-10-01', 'to': '2026-10-16',
                                            'sourceLabel': 'Bank statements', 'confirm': True}, 'owner', 'cov')
        r = self.wait_status(self.create(), ('awaiting_owner',))
        items = {i['kind']: i['text'] for i in r['analysis']['brief']['openItems']}
        self.assertIn('Payment records are confirmed complete to Fri 16 Oct 2026, but invoice records are not confirmed complete',
                      items['customer_balance'])
        self.assertNotIn('Records for this customer are not confirmed complete', items['customer_balance'])
        self.assertIn('entered by the owner', items['customer_balance'])
        self.assertIn('entered by the owner', items['opening_credits'])

    def test_reverting_an_import_lists_inclusion_answers_on_its_records(self):
        self.ready()                                                              # the customers exist before the import
        batch = self.upload((SAMPLES / 'invoices-list.csv').read_text(), shape='invoices', label='Accounts spreadsheet')
        batch = self.apply(self.params(batch, asOf='2026-10-09'))
        self.opening(amount='2000.00', as_of='2026-10-09')
        invoice = next(i for i in self.app.fixture()['invoices'] if i['reference'] == 'INV-1001' and i['customerId'] == self.bayside['id'])
        self.include('invoices', invoice, 'included')
        status, error, _ = self.call('/api/imports/' + batch['id'] + '/revert', {'reason': 'Wrong file'}, 'staff', 'rv')
        self.assertEqual((status, error['error'], len(error['impact']['review']['answers'])), (409, 'REVIEW_REQUIRED', 1))


    def test_a_customer_an_import_created_is_not_reverted_from_under_its_opening_balance(self):
        self.records_setup()                                                      # the import created the customers
        self.opening(self.customers['Bayside Café'], amount='1400.00', as_of='2026-10-09')
        batch = next(b for b in self.call('/api/imports', role='staff')[1] if b['shape'] == 'invoices')
        status, error, _ = self.call('/api/imports/' + batch['id'] + '/revert', {'reason': 'Wrong file'}, 'staff', 'rv')
        self.assertEqual((status, error['error']), (409, 'REVERT_BLOCKED'))
        self.assertIn('opening balance', ' '.join(error['impact']['blocked']))

if __name__ == '__main__':
    unittest.main()
