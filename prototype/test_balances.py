"""Where a stated amount still owed meets recorded payments (Stage 3). A statement "X still owed as of D" may already reflect
payments made on or before D; those are never subtracted again, and whether it reflects them is unresolved until the amounts
reconcile or a person says. All data is fictional."""
import unittest

from test_payment_import import PaymentImportCase


class StatementCase(PaymentImportCase):
    def stated(self, owed='400.00', as_of='2026-10-09', total='1000.00', reference='INV-1'):
        return self.invoice(reference, total=total, stillOwed=owed, stillOwedAsOf=as_of)

    def paid(self, invoice, amount, date, allocate=None, **extra):
        payment = self.pay(amount, date=date, **extra)
        if allocate != '0':
            self.allocate(payment, (invoice, allocate or amount))
        return payment

    def position(self, invoice):
        return self.positions()['invoices'].get(invoice['id'])

    def allocation_of(self, payment):
        return next(a for a in self.app.fixture()['allocations'] if a['paymentId'] == payment['id'])

    def answer(self, payment, status, expect=200, key=None):
        allocation = self.allocation_of(payment)
        status_code, result, _ = self.call('/api/records/allocations/' + allocation['id'] + '/statement', {'status': status}, 'staff',
                                           key or 'ans-' + allocation['id'] + status)
        self.assertEqual(status_code, expect, result)
        return result


class StatementBoundaryTests(StatementCase):
    def test_a_payment_before_the_statement_is_not_subtracted_again(self):
        self.ready()
        invoice = self.stated()                                   # 1,000.00 invoice, 400.00 still owed as of 9 Oct
        early = self.paid(invoice, '600.00', '2026-10-05')        # paid before 9 Oct: 1,000 - 600 = 400 suggests the statement reflects it
        position = self.position(invoice)
        allocation = self.allocation_of(early)['id']
        self.assertEqual((position['status'], self.minor(position['atMost'])), ('open', '40000'))
        self.assertEqual((position['inclusion']['reconciles'], position['inclusion']['unresolved']), ([allocation], [allocation]))

    def test_a_further_payment_after_the_statement_counts_against_it(self):
        self.ready()
        invoice = self.stated()
        self.paid(invoice, '600.00', '2026-10-05')
        self.paid(invoice, '300.00', '2026-10-12')
        self.assertEqual(self.minor(self.position(invoice)['atMost']), '10000')

    def test_later_payments_cannot_be_allocated_beyond_the_amount_stated(self):
        self.ready()
        invoice = self.stated()
        late = self.pay('500.00', date='2026-10-12')
        result = self.allocate(late, (invoice, '500.00'), expect=422)   # the total leaves 1,000.00, but only 400.00 was still owed
        self.assertEqual(result['error'], 'OVER_INVOICE')
        self.assertIn('400.00', result['message'])
        self.allocate(late, (invoice, '400.00'))
        self.assertEqual(self.position(invoice)['status'], 'settled')

    def test_whether_a_statement_reflects_an_earlier_payment_is_unresolved_until_a_person_says(self):
        self.ready()
        invoice = self.stated()
        early = self.paid(invoice, '200.00', '2026-10-05')       # 1,000 - 200 = 800, not 400: the amounts don't explain each other
        position = self.position(invoice)
        self.assertEqual((self.minor(position['atMost']), position['inclusion']['unresolved']), ('40000', [self.allocation_of(early)['id']]))
        self.answer(early, 'missed')                              # the statement was made without it: it still comes off
        self.assertEqual(self.minor(self.position(invoice)['atMost']), '20000')
        self.answer(early, 'included', key='inc')                 # it was already counted: other payments or credits explain the rest
        position = self.position(invoice)
        self.assertEqual((self.minor(position['atMost']), position['inclusion']['unresolved'], position['conflicts']), ('40000', [], []))
        self.answer(early, 'unsure', key='unsure')
        self.assertEqual(len(self.position(invoice)['inclusion']['unresolved']), 1)

    def test_a_payment_on_the_statement_date_is_not_assumed_either_way(self):
        self.ready()
        invoice = self.stated()
        same_day = self.paid(invoice, '100.00', '2026-10-09')
        self.assertEqual(self.position(invoice)['inclusion']['unresolved'], [self.allocation_of(same_day)['id']])
        self.assertEqual(self.minor(self.position(invoice)['atMost']), '40000')

    def test_evidence_that_contradicts_itself_is_a_conflict_and_never_settles(self):
        self.ready()
        invoice = self.stated()
        full = self.paid(invoice, '1000.00', '2026-10-05')        # the whole invoice paid before 9 Oct, yet 400.00 stated owed on 9 Oct
        self.answer(full, 'included')
        position = self.position(invoice)
        self.assertEqual((position['status'], self.minor(position['atMost'])), ('conflict', '40000'))
        self.assertTrue(position['conflicts'])

    def test_an_answer_stops_applying_when_the_statement_changes(self):
        self.ready()
        invoice = self.stated()
        early = self.paid(invoice, '200.00', '2026-10-05')
        self.answer(early, 'missed')
        self.assertEqual(self.correct('invoices', invoice, stillOwed='350.00', stillOwedAsOf='2026-10-10', reason='Newer statement')[0], 200)
        position = self.position(invoice)
        self.assertEqual((self.minor(position['atMost']), len(position['inclusion']['unresolved']), position['inclusion']['stale']), ('35000', 1, 1))

    def test_the_samples_figure_counts_as_stated_on_the_samples_date(self):
        self.start(sample_data=True)
        doc = self.app.fixture()
        invoice = next(i for i in doc['invoices'] if i['reference'] == 'DEMO-101')   # AUD 1,250.00 in the sample, no as-of date
        supplies = next(c for c in doc['customers'] if c['id'] == invoice['customerId'])
        self.paid(invoice, '250.00', '2026-10-16', customer=supplies)                 # on the sample's own date
        position = self.position(invoice)
        self.assertEqual((self.minor(position['atMost']), position['statedAsOf'], len(position['inclusion']['unresolved'])), ('125000', '2026-10-16', 1))




class StatementInCasesTests(StatementCase):
    def brief(self, r):
        return {f['key']: f for f in r['analysis']['brief']['facts']}, {i['kind']: i['text'] for i in r['analysis']['brief']['openItems']}

    def test_the_owner_sees_what_is_unresolved_in_plain_words(self):
        self.ready()
        invoice = self.stated(reference='DEMO-501')
        self.paid(invoice, '200.00', '2026-10-05')
        facts, items = self.brief(self.wait_status(self.create(), ('awaiting_owner',)))
        self.assertEqual((facts['outstandingAmount']['kind'], self.minor(facts['outstandingAmount']['value'])), ('bounded', '40000'))
        self.assertIn('stated still owed as of Fri 9 Oct 2026', facts['outstandingAmount']['note'])
        self.assertIn('not taken off', items['statement_inclusion_unresolved'])

    def test_contradicting_records_reach_the_owner_as_a_conflict_not_as_paid(self):
        self.ready()
        invoice = self.stated(reference='DEMO-501')
        self.answer(self.paid(invoice, '1000.00', '2026-10-05'), 'included')
        self.invoice('DEMO-502')
        facts, items = self.brief(self.wait_status(self.create(), ('awaiting_owner',)))
        self.assertEqual(self.minor(facts['outstandingAmount']['value']), '40000')
        self.assertIn('contradict', items['records_conflict'])
    def decided(self):
        self.ready()
        invoice = self.stated(reference='DEMO-501')
        early = self.paid(invoice, '200.00', '2026-10-05')
        r = self.wait_status(self.create(), ('awaiting_owner',))
        self.assertEqual(self.decide(r)[0], 201)
        return invoice, early, self.wait_status(r, ('completed',))

    def test_a_decided_case_is_flagged_when_what_its_invoice_shows_changes_and_says_how(self):
        invoice, early, done = self.decided()
        self.answer(early, 'missed')                                   # changes what the invoice shows, without touching the invoice
        after = self.reopen(done)
        flag = after['flags'][-1]
        self.assertEqual(flag['kind'], 'records_changed_after_decision')
        self.assertIn('at most AUD 400.00', flag['outstandingBefore'])
        self.assertIn('at most AUD 200.00', flag['outstandingNow'])
        self.assertEqual((after['decision'], after['analysis']), (done['decision'], done['analysis']))   # never rewritten

    def test_a_flag_says_in_plain_words_which_record_changed_and_who_changed_it(self):   # QA B5, U7
        _, _, done = self.decided()
        self.paid(self.app.fixture()['invoices'][0], '50.00', '2026-10-12', reference='LATE-1')
        flag = self.reopen(done)['flags'][-1]
        self.assertEqual(flag['role'], 'staff')
        self.assertRegex(flag['description'], r'^AUD 50.00 from payment LATE-1 allocated to invoice DEMO-501 \(.+\) by staff$')
        events = [e for e in self.reopen(done)['history'] if e['kind'] == 'evidence.changed_after_decision']
        self.assertEqual(events[-1]['data']['description'], flag['description'])

    def test_changes_to_another_customer_leave_a_decided_case_alone(self):
        _, _, done = self.decided()
        self.pay('90.00', customer=self.coastline)
        self.assertEqual(self.reopen(done).get('flags', []), [])

    def test_decisions_from_before_this_release_are_compared_from_the_first_start(self):
        invoice, early, done = self.decided()
        with self.app.lock, self.app.db:                               # as an earlier release stored it
            stored = self.app.get(done['id'])
            del stored['evidenceSeen']
            self.app.save(stored)
        self.restart()
        self.assertIn('evidence.baseline_recorded', [e['kind'] for e in self.reopen(done)['history']])
        self.answer(early, 'missed', key='after-restart')
        self.assertEqual([f['kind'] for f in self.reopen(done)['flags']], ['records_changed_after_decision'])
    def statement_file(self, owed, as_of, key):
        batch = self.upload('Customer,Invoice No,Invoice Date,Amount,Balance\nBayside Café,INV-1,01/10/2026,1000.00,' + owed + '\n',
                            shape='invoices', label='Accounts spreadsheet', key=key)
        return self.params(batch, key=key + '-p', asOf=as_of, dateOrder='dmy')

    def test_a_later_statement_that_shows_more_owed_needs_a_person(self):
        self.ready()
        self.apply(self.statement_file('400.00', '2026-10-09', 'first'))
        batch = self.statement_file('700.00', '2026-10-12', 'second')
        row = batch['preview']['rows'][0]
        self.assertEqual((row['status'], row['conflictFields']), ('conflict', ['outstandingAmount']))
        self.assertFalse(batch['preview']['ready'])

    def test_reverting_a_statement_restores_the_earlier_one_and_lists_answers_that_stop_applying(self):
        self.ready()
        self.apply(self.statement_file('1000.00', '2026-10-01', 'first'))
        invoice = next(i for i in self.app.fixture()['invoices'] if i['reference'] == 'INV-1')
        early = self.paid(invoice, '200.00', '2026-10-05')                   # after the 1 Oct statement: counted
        self.assertEqual(self.minor(self.position(invoice)['atMost']), '80000')
        second = self.apply(self.statement_file('400.00', '2026-10-09', 'second'))
        self.answer(early, 'missed')                                         # about the 9 Oct statement
        self.assertEqual(self.minor(self.position(invoice)['atMost']), '20000')
        status, error, _ = self.call('/api/imports/' + second['id'] + '/revert', {'reason': 'Wrong export'}, 'staff', 'rv1')
        self.assertEqual((status, error['error']), (409, 'REVIEW_REQUIRED'))
        self.assertEqual(len(error['impact']['review']['answers']), 1)
        self.assertEqual(self.call('/api/imports/' + second['id'] + '/revert', {'reason': 'Wrong export', 'confirm': True}, 'staff', 'rv2')[0], 200)
        position = self.position(invoice)
        self.assertEqual((position['statedAsOf'], self.minor(position['atMost']), position['inclusion']['stale']), ('2026-10-01', '80000', 0))

    def test_reverting_payments_returns_the_invoice_to_its_statement(self):
        self.records_setup()                                                  # sample invoice list, amounts as of 9 Oct
        batch = self.payments_imported()                                      # payments from 12 Oct onwards
        bayside = self.invoices[('Bayside Café', 'INV-1001')]
        self.assertEqual(self.minor(self.position(bayside)['atMost']), '40000')
        self.assertEqual(self.call('/api/imports/' + batch['id'] + '/revert', {'reason': 'Wrong account'}, 'staff', 'rv')[0], 200)
        self.assertIsNone(self.position(bayside))
        self.assertEqual(self.app.fixture()['invoices'][0]['outstandingAmount']['minorUnits'], '100000')


class StatementMigrationTests(StatementCase):
    def test_stated_amounts_in_a_records_document_move_into_tables_and_follow_the_same_rules(self):
        document = {'dataMode': 'fictional', 'version': 3, 'businessTimezone': 'Australia/Sydney', 'currency': 'AUD', 'scale': 2, 'businessName': None,
                    'customers': [{'id': 'customer_b', 'displayCode': 'C-0001', 'name': 'Bayside Café', 'status': 'active', 'version': 1,
                                   'origin': {'kind': 'manual', 'by': 'staff_demo', 'at': '2026-10-17T01:00:00+00:00'}, 'history': []}],
                    'invoices': [{'id': 'invoice_b1', 'customerId': 'customer_b', 'reference': 'INV-1', 'issueDate': '2026-10-01',
                                  'total': {'minorUnits': '100000', 'currency': 'AUD', 'scale': 2}, 'originalDueDate': '2026-10-31',
                                  'outstandingAmount': {'minorUnits': '40000', 'currency': 'AUD', 'scale': 2}, 'outstandingAsOf': '2026-10-09',
                                  'outstandingSource': 'manual', 'status': 'active', 'version': 1,
                                  'origin': {'kind': 'manual', 'by': 'staff_demo', 'at': '2026-10-17T01:00:00+00:00'}, 'history': []}],
                    'notes': []}
        self.store(document, {'mode': 'practice', 'origin': 'first_run', 'sampleFingerprint': None, 'skips': {}})
        self.start()
        self.assertEqual(self.app.fixture(), document)
        invoice, customer = document['invoices'][0], document['customers'][0]
        self.paid(invoice, '600.00', '2026-10-05', customer=customer)         # reconciles with the stated 400.00
        self.paid(invoice, '150.00', '2026-10-12', customer=customer)
        position = self.position(invoice)
        self.assertEqual((self.minor(position['atMost']), len(position['inclusion']['reconciles'])), ('25000', 1))


if __name__ == '__main__':
    unittest.main()
