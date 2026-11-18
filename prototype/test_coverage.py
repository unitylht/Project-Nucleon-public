"""Coverage statements (Stage 3, P002 section 8.2): which records are confirmed complete, for which customers, record types and
period, by whom. Completeness is never derived from the records or from file dates; it is the unbroken run of confirmed periods
from the customer's base. All data is fictional."""
import unittest

from test_openings import OpeningCase
from test_payment_import import SAMPLES


class CoverageCase(OpeningCase):
    def attest(self, customers=None, types=('payments',), start='2026-10-01', end='2026-10-16', role='owner', expect=200, key=None, **extra):
        body = {'customers': customers if customers is not None else [self.bayside['id']], 'recordTypes': list(types), 'from': start, 'to': end,
                'sourceLabel': 'Checked against the bank statements', 'confirm': True, **extra}
        status, result, _ = self.call('/api/records/coverage', body, role, key or 'cov-' + str(sorted((k, str(v)) for k, v in body.items())))
        self.assertEqual(status, expect, result)
        return result.get('record', result)

    def coverage(self, customer=None, kind='payments'):
        return self.positions()['customers'][(customer or self.bayside)['id']]['coverage'][kind]


class CoverageTests(CoverageCase):
    def test_completeness_is_never_derived_from_records_or_file_dates(self):
        self.records_setup()
        self.payments_imported()
        bayside = self.customers['Bayside Café']
        payments = self.coverage(bayside)
        self.assertEqual((payments['completeTo'], payments['lastActivity']), (None, '2026-10-14'))
        self.assertEqual(self.coverage(bayside, 'invoices')['completeTo'], None)

    def test_the_owner_confirms_completeness_with_its_scope_period_and_source(self):
        self.ready()
        statement = self.attest()
        self.assertEqual((statement['customers'], statement['recordTypes'], statement['from'], statement['to'], statement['basis'],
                          statement['confirmedBy'], statement['sourceLabel']),
                         ([self.bayside['id']], ['payments'], '2026-10-01', '2026-10-16', 'attestation', 'owner_demo', 'Checked against the bank statements'))
        self.assertEqual(self.attest(role='staff', expect=403, key='staff')['error'], 'FORBIDDEN')
        self.assertEqual(self.attest(end='2026-10-19', expect=400, key='future')['field'], 'to')
        self.assertEqual(self.attest(start='2026-10-17', end='2026-10-16', expect=400, key='backwards')['field'], 'from')
        self.assertEqual(self.attest(confirm=False, expect=400, key='unticked')['field'], 'confirm')
        self.assertEqual(self.attest(types=(), expect=400, key='no-types')['field'], 'recordTypes')

    def test_complete_to_is_the_unbroken_run_from_the_base(self):
        self.ready()
        self.attest(start='2026-10-03', end='2026-10-09')
        self.assertEqual((self.coverage()['base'], self.coverage()['completeTo']), ('2026-10-03', '2026-10-09'))   # no opening balance: from the earliest
        self.attest(start='2026-10-10', end='2026-10-12', key='adjacent')                                          # the next day joins the run
        self.attest(start='2026-10-11', end='2026-10-15', key='overlap')                                           # overlaps extend it
        self.assertEqual(self.coverage()['completeTo'], '2026-10-15')
        self.attest(start='2026-10-17', end='2026-10-18', key='after-gap')                                         # 16 Oct is missing
        self.assertEqual(self.coverage()['completeTo'], '2026-10-15')

    def test_with_an_opening_balance_the_run_must_start_right_after_it(self):
        self.ready()
        self.opening()                                                             # as at 30 Sep
        self.attest(start='2026-10-05', end='2026-10-16')
        self.assertEqual((self.coverage()['base'], self.coverage()['completeTo']), ('2026-09-30', None))   # 1-4 Oct not confirmed
        self.attest(start='2026-09-25', end='2026-10-04', key='gap-filled')
        self.assertEqual(self.coverage()['completeTo'], '2026-10-16')

    def test_a_statement_about_one_customer_says_nothing_about_another(self):
        self.ready()
        self.attest()
        self.assertIsNone(self.coverage(self.coastline)['completeTo'])
        self.attest(customers='all', types=('invoices', 'payments'), key='all')
        self.assertEqual((self.coverage(self.coastline)['completeTo'], self.coverage(self.coastline, 'invoices')['completeTo']), ('2026-10-16', '2026-10-16'))

    def test_a_record_added_later_inside_a_confirmed_period_contradicts_it_for_that_customer(self):
        self.ready()
        self.attest(customers='all')
        late = self.pay('90.00', date='2026-10-10')                                # entered after the period was confirmed complete
        payments = self.coverage()
        self.assertEqual((payments['completeTo'], payments['contradicted'][0]['records']), (None, ['2026-10-10 90.00']))
        self.assertEqual(self.coverage(self.coastline)['completeTo'], '2026-10-16')   # only Bayside's records contradict it
        self.call('/api/records/payments/' + late['id'] + '/remove', {'reason': 'Entered by mistake'}, 'staff', 'rm')
        self.assertEqual(self.coverage()['completeTo'], '2026-10-16')                # recalculated once the record is gone

    def test_a_record_corrected_into_a_confirmed_period_afterwards_contradicts_it(self):
        self.ready()
        payment = self.pay('90.00', date='2026-09-20')                             # before the period: no effect
        self.attest()
        self.assertEqual(self.coverage()['completeTo'], '2026-10-16')
        self.correct('payments', payment, receivedDate='2026-10-10', reason='Wrong date typed')
        self.assertIsNone(self.coverage()['completeTo'])

    def test_a_record_that_leaves_a_confirmed_period_afterwards_contradicts_it(self):
        self.ready()
        removed = self.pay('90.00', date='2026-10-10', reference='EFT 1')
        moved = self.pay('40.00', date='2026-10-11', reference='EFT 2')
        self.attest()                                                              # both were part of what was confirmed complete
        self.call('/api/records/payments/' + removed['id'] + '/remove', {'reason': 'Bounced'}, 'staff', 'rm')
        self.assertEqual(self.coverage()['contradicted'][0]['records'], ['EFT 1'])
        self.assertIsNone(self.coverage()['completeTo'])

    def test_a_record_corrected_out_of_a_confirmed_period_contradicts_it(self):
        self.ready()
        moved = self.pay('40.00', date='2026-10-11', reference='EFT 2')
        self.attest()
        self.correct('payments', moved, receivedDate='2026-09-28', reason='Wrong date typed')
        self.assertIsNone(self.coverage()['completeTo'])

    def test_a_record_entered_after_confirmation_and_removed_again_changes_nothing(self):
        self.ready()
        self.attest()
        stray = self.pay('90.00', date='2026-10-10')
        self.call('/api/records/payments/' + stray['id'] + '/remove', {'reason': 'Typed by mistake'}, 'staff', 'rm')
        self.assertEqual(self.coverage()['completeTo'], '2026-10-16')

    def test_retiring_a_statement_recalculates_completeness(self):
        self.ready()
        statement = self.attest()
        self.assertEqual(self.call('/api/records/coverage/' + statement['id'] + '/retire', {'reason': 'Bank feed was incomplete'}, 'staff', 'rs')[0], 403)
        self.assertEqual(self.call('/api/records/coverage/' + statement['id'] + '/retire', {'reason': 'Bank feed was incomplete'}, 'owner', 'ro')[0], 200)
        self.assertIsNone(self.coverage()['completeTo'])

    def test_a_statement_for_one_customer_leaves_other_customers_cases_alone(self):
        self.ready()
        self.invoice('DEMO-501', total='1000.00')
        self.invoice('DEMO-601', total='700.00', customer=self.coastline)
        mine = self.wait_status(self.create(), ('awaiting_owner',))
        theirs = self.wait_status(self.create('Could we pay invoice DEMO-601 on 2026-10-30 instead?', key='theirs'), ('awaiting_owner',))
        self.attest(customers=[self.coastline['id']])
        self.assertEqual(self.reopen(mine)['analysis']['id'], mine['analysis']['id'])
        self.assertNotEqual(self.wait_status(theirs, ('awaiting_owner',))['analysis']['id'], theirs['analysis']['id'])


class ImportCoverageTests(CoverageCase):
    def payments_file(self, role='staff', coverage=None, key='pay'):
        batch = self.upload((SAMPLES / 'payments-list.csv').read_text(), key=key)
        return self.call('/api/imports/' + batch['id'] + '/mapping', {'mapping': batch['mapping'], 'coverage': coverage,
                                                                         'resolutions': {'customers': {}, 'conflicts': {}, 'rows': {}}},
                         role, key + '-params')

    def test_an_import_confirms_completeness_only_when_the_owner_says_so_and_only_for_its_customers(self):
        self.records_setup()
        harbour = self.add_customer('Harbour Kiosk')                               # not in the file
        status, batch, _ = self.payments_file()
        self.assertEqual((status, batch['preview']['coverage']), (200, None))     # by default an import says nothing about completeness
        status, error, _ = self.payments_file(role='staff', coverage={'customers': 'file', 'from': '2026-10-10', 'to': '2026-10-16'}, key='staff-cov')
        self.assertEqual((status, error['error']), (403, 'FORBIDDEN'))
        status, batch, _ = self.payments_file(role='owner', coverage={'customers': 'file', 'from': '2026-10-10', 'to': '2026-10-16'}, key='owner-cov')
        self.assertEqual(status, 200, batch)
        self.apply(batch)
        bayside, coastline = self.customers['Bayside Café'], self.customers['Coastline Foods']
        self.opening(bayside, amount='1400.00', as_of='2026-10-09')
        self.assertEqual((self.coverage(bayside)['completeTo'], self.coverage(coastline)['completeTo']), ('2026-10-16', '2026-10-16'))
        self.assertEqual((self.coverage(harbour)['statements'], self.coverage(harbour)['completeTo']), ([], None))
        statement = next(c for c in self.app.fixture()['coverage'])
        self.assertEqual((statement['basis'], statement['recordTypes'], statement['batchId']), ('export', ['payments'], batch['id']))

    def test_reverting_the_import_removes_its_statement_after_review(self):
        self.records_setup()
        _, batch, _ = self.payments_file(role='owner', coverage={'customers': 'all', 'from': '2026-10-10', 'to': '2026-10-16'}, key='all-cov')
        batch = self.apply(batch)
        self.assertEqual(self.coverage(self.customers['Coastline Foods'])['completeTo'], '2026-10-16')
        status, error, _ = self.call('/api/imports/' + batch['id'] + '/revert', {'reason': 'Wrong account'}, 'owner', 'rv1')
        self.assertEqual((status, error['error'], len(error['impact']['review']['coverage'])), (409, 'REVIEW_REQUIRED', 1))
        self.assertEqual(self.call('/api/imports/' + batch['id'] + '/revert', {'reason': 'Wrong account', 'confirm': True}, 'owner', 'rv2')[0], 200)
        self.assertIsNone(self.coverage(self.customers['Coastline Foods'])['completeTo'])


if __name__ == '__main__':
    unittest.main()
