"""The financial completeness contract: every customer-level figure the desk tools return travels with how far its records are
confirmed complete. Invoices and payments are judged apart; a past confirmation is never current; no recorded payment is not proof of
no payment; a figure worked out from records stays "worked out" however complete they are; a customer that is not found is an error,
never a zero balance. Also the MCP operation-safety audit: pure reads store nothing, assessRequest keeps the latest assessment.
All data is fictional (business date Sun 18 Oct 2026)."""
import hashlib
import sqlite3
import unittest

import records
import server
from agent import AMOUNT
from test_exact import ExactCase

AS_OF = '2026-10-18'
OLD_OVERVIEW_KEYS = {'customerId', 'name', 'link', 'asOf', 'recordedNet', 'owedNow', 'owedOverdue', 'owedNotYetDue', 'owedNoDueDate', 'owedFromOpening',
                     'creditHeld', 'openingPaid', 'notAllocated', 'completeTo', 'lastActivity', 'openCount', 'overdueCount', 'knownAmountCount',
                     'caseCount', 'overdueText', 'balanceLine', 'invoiceCount', 'recordsExist', 'invoices', 'openCases', 'termsText', 'payments'}
OLD_INVOICES_KEYS = {'customerId', 'name', 'which', 'asOf', 'invoiceCount', 'invoices'}
PURE_READS = {'findCustomers': lambda c, r: {'query': 'Bayside'}, 'customerOverview': lambda c, r: {'customerId': c['id']},
              'invoices': lambda c, r: {'customerId': c['id'], 'which': 'all'}, 'ownerContext': lambda c, r: {'customerId': c['id']},
              'cases': lambda c, r: {'customerId': c['id']}, 'caseDetails': lambda c, r: {'requestId': r['id']},
              'whereIs': lambda c, r: {'topic': 'completeness'}, 'compareExtension': lambda c, r: {'requestId': r['id'], 'days': 14},
              'workQueue': lambda c, r: {}, 'listRequests': lambda c, r: {}}


class ContractCase(ExactCase):
    n = 0

    def tool(self, name, role='staff', **args):
        ContractCase.n += 1
        status, body, _ = self.call('/api/tools/' + name, {'args': args}, role, 'contract-' + str(ContractCase.n))
        return status, body

    def overview(self, c):
        status, body = self.tool('customerOverview', customerId=c['id'])
        self.assertEqual((status, body.get('ok')), (200, True), body)
        return body['result']

    def invoices(self, c, which='all', **args):
        status, body = self.tool('invoices', customerId=c['id'], which=which, **args)
        self.assertEqual((status, body.get('ok')), (200, True), body)
        return body['result']

    def both(self, c):
        """(overview, invoices) of one customer, whose completeness must be the same object."""
        ov, inv = self.overview(c), self.invoices(c)
        self.assertEqual(ov['completeness'], inv['completeness'])
        self.assertEqual(ov['completeTo'], inv['completeTo'])
        return ov, inv

    def owed_minor(self, c):
        return self.minor(self.positions()['customers'][c['id']]['owed']['owedNow'])

    def established(self, c, **dates):
        """An opening balance of nothing owed with no credits, and invoices and payments confirmed complete to the business date."""
        self.opening(c, amount='0.00', credits='none')
        self.attest([c['id']], ('invoices', 'payments'), start='2026-10-01', end=dates.get('end', AS_OF))


class CompletenessScenarioTests(ContractCase):
    def test_1_invoices_and_no_payments(self):
        self.ready()
        self.invoice('INV-1', total='1000.00', issueDate='2026-10-05', dueDate='2026-11-05')
        ov, inv = self.both(self.bayside)
        w = ov['completeness']
        self.assertEqual((w['asOf'], w['invoices']['state'], w['payments']['state'], w['balanceEstablished']), (AS_OF, 'notConfirmed', 'notConfirmed', False))
        self.assertEqual((w['invoices']['recordedCount'], w['payments']['recordedCount']), (1, 0))
        for code in ('invoices_not_confirmed', 'payments_not_confirmed', 'no_payments_recorded', 'no_opening_balance'):
            self.assertIn(code, w['reasons'])
        self.assertNotIn('no_invoices_recorded', w['reasons'])
        self.assertTrue(w['caveatText'].startswith('Not a confirmed balance: invoice records are not confirmed complete; payment records are not confirmed complete.'), w['caveatText'])
        self.assertIn('No payments are recorded, which does not show that none were made.', w['caveatText'])
        # the figures and marks old consumers read are as they were: worked out, never exact, never zero
        self.assertEqual((self.owed_minor(self.bayside), ov['owedNow']['mark']), ('100000', 'worked out'))
        self.assertIn('1,000.00', ov['owedNow']['amountText'])
        self.assertTrue(ov['balanceLine'].startswith('Owed now AUD 1,000.00 (worked out; invoices not confirmed complete; payments not confirmed complete), '
                                                     'all of it not yet due.'), ov['balanceLine'])
        self.assertEqual(ov['completeTo'], {'invoices': None, 'payments': None})
        self.assertTrue(OLD_OVERVIEW_KEYS <= set(ov) and OLD_INVOICES_KEYS <= set(inv))

    def test_2_partial_payments(self):
        self.ready()
        invoice = self.invoice('INV-1', total='1000.00', issueDate='2026-10-05', dueDate='2026-11-05')
        self.allocate(self.pay('400.00', date='2026-10-12', reference='EFT 1'), (invoice, '400.00'))
        ov, inv = self.both(self.bayside)
        w = ov['completeness']
        self.assertEqual((w['payments']['recordedCount'], w['payments']['lastActivity'], w['payments']['state']), (1, '2026-10-12', 'notConfirmed'))
        self.assertIn('payments_not_confirmed', w['reasons'])
        self.assertNotIn('no_payments_recorded', w['reasons'])
        self.assertEqual((self.owed_minor(self.bayside), ov['owedNow']['mark']), ('60000', 'worked out'))
        self.assertEqual(inv['invoices'][0]['mark'].split(',')[0].split(';')[0], 'at most')   # an upper bound, not exact
        self.assertFalse(w['balanceEstablished'])

    def test_3_unallocated_payments_stay_unallocated_and_unconfirmed(self):
        self.ready()
        self.invoice('INV-1', total='1000.00', issueDate='2026-10-05', dueDate='2026-11-05')
        self.pay('300.00', date='2026-10-12', reference='EFT 9')
        ov, inv = self.both(self.bayside)
        self.assertEqual(ov['completeness']['payments']['recordedCount'], 1)
        self.assertIn('unmatchedText', ov)
        self.assertIn('not allocated', ov['unmatchedText'])
        self.assertFalse(ov['completeness']['balanceEstablished'])
        self.assertIn('payments_not_confirmed', ov['completeness']['reasons'])
        self.assertEqual(ov['notAllocated']['mark'], 'as recorded')

    def test_4_both_incomplete_and_last_activity_is_never_completeness(self):
        self.ready()
        self.invoice('INV-1', total='1000.00', issueDate='2026-10-05')
        self.pay('100.00', date='2026-10-17')
        ov, _ = self.both(self.bayside)
        w = ov['completeness']
        self.assertEqual((w['invoices']['lastActivity'], w['payments']['lastActivity']), ('2026-10-05', '2026-10-17'))
        self.assertEqual((w['invoices']['completeTo'], w['payments']['completeTo']), (None, None))
        self.assertEqual((w['invoices']['state'], w['payments']['state']), ('notConfirmed', 'notConfirmed'))

    def test_5_invoices_complete_payments_not(self):
        self.ready()
        self.invoice('INV-1', total='1000.00', issueDate='2026-10-05', dueDate='2026-11-05')
        self.attest(types=('invoices',), start='2026-10-01', end=AS_OF)
        ov, inv = self.both(self.bayside)
        w = ov['completeness']
        self.assertEqual((w['invoices']['state'], w['invoices']['completeTo'], w['payments']['state']), ('complete', AS_OF, 'notConfirmed'))
        self.assertNotIn('invoices_not_confirmed', w['reasons'])
        self.assertIn('payments_not_confirmed', w['reasons'])
        self.assertFalse(w['balanceEstablished'])
        self.assertIn('invoice records are confirmed complete to Sun 18 Oct; payment records are not confirmed complete', w['caveatText'])

    def test_6_payments_complete_invoices_not(self):
        self.ready()
        self.invoice('INV-1', total='1000.00', issueDate='2026-10-05', dueDate='2026-11-05')
        self.attest(types=('payments',), start='2026-10-01', end=AS_OF)
        ov, _ = self.both(self.bayside)
        w = ov['completeness']
        self.assertEqual((w['payments']['state'], w['invoices']['state']), ('complete', 'notConfirmed'))
        self.assertIn('invoices_not_confirmed', w['reasons'])
        self.assertNotIn('payments_not_confirmed', w['reasons'])
        # payments are complete to the date and none is recorded: that is established, so it is not said to prove nothing
        self.assertNotIn('no_payments_recorded', w['reasons'])
        self.assertIn('No payments are recorded in the confirmed records.', w['caveatText'])
        self.assertFalse(w['balanceEstablished'])

    def test_7_both_complete_to_the_business_date(self):
        self.ready()
        invoice = self.invoice('INV-1', total='1000.00', issueDate='2026-10-05', dueDate='2026-11-05')
        self.allocate(self.pay('600.00', date='2026-10-12', reference='EFT 1'), (invoice, '600.00'))
        self.established(self.bayside)
        ov, inv = self.both(self.bayside)
        w = ov['completeness']
        self.assertEqual((w['invoices']['state'], w['payments']['state'], w['balanceEstablished'], w['reasons']), ('complete', 'complete', True, []))
        self.assertEqual(w['caveatText'], 'Invoice and payment records are confirmed complete to Sun 18 Oct 2026.')
        self.assertEqual({k: v for k, v in ov['completeTo'].items() if not k.endswith('Text')}, {'invoices': AS_OF, 'payments': AS_OF})   # dated() adds the words beside each date
        self.assertEqual(inv['completeness']['balanceEstablished'], True)
        self.assertEqual((self.owed_minor(self.bayside), ov['owedNow']['mark']), ('40000', 'worked out'))   # complete records do not make the mark exact

    def test_8_complete_only_to_an_earlier_date_is_never_current(self):
        self.ready()
        self.invoice('INV-1', total='1000.00', issueDate='2026-10-05', dueDate='2026-11-05')
        self.established(self.bayside, end='2026-10-10')
        ov, inv = self.both(self.bayside)
        w = ov['completeness']
        self.assertEqual((w['invoices']['state'], w['payments']['state'], w['balanceEstablished']), ('completeToEarlierDate', 'completeToEarlierDate', False))
        self.assertEqual((w['invoices']['completeTo'], w['payments']['completeTo']), ('2026-10-10', '2026-10-10'))
        self.assertTrue({'invoices_complete_to_earlier_date', 'payments_complete_to_earlier_date'} <= set(w['reasons']))
        self.assertIn('invoice records are confirmed complete only to Sat 10 Oct; payment records are confirmed complete only to Sat 10 Oct', w['caveatText'])
        self.assertNotIn('Invoice and payment records are confirmed complete to', w['caveatText'])

    def test_9_a_contradicted_statement_counts_even_when_another_gives_a_completeTo(self):
        self.ready()
        self.invoice('INV-1', total='1000.00', issueDate='2026-10-05', dueDate='2026-11-05')
        self.opening(amount='0.00', credits='none')
        self.attest(types=('invoices', 'payments'), start='2026-10-01', end=AS_OF)
        self.pay('90.00', date='2026-10-10', reference='LATE')                    # entered after the period was confirmed complete
        self.attest(types=('payments',), start='2026-10-01', end='2026-10-09', key='second')   # a later statement for an earlier period
        ov, inv = self.both(self.bayside)
        w = ov['completeness']
        self.assertEqual((w['payments']['completeTo'], w['payments']['state'], w['payments']['contradicted']), ('2026-10-09', 'completeToEarlierDate', 1))
        self.assertIn('payments_contradicted', w['reasons'])
        self.assertEqual((w['invoices']['state'], w['invoices']['contradicted']), ('complete', 0))
        self.assertFalse(w['balanceEstablished'])
        self.assertIn('no longer holds', w['caveatText'])

    def test_9b_a_contradicted_statement_alone_leaves_the_kind_not_confirmed(self):
        self.ready()
        self.established(self.bayside)
        self.pay('90.00', date='2026-10-10', reference='LATE')
        w = self.both(self.bayside)[0]['completeness']
        self.assertEqual((w['payments']['state'], w['payments']['contradicted'], w['balanceEstablished']), ('notConfirmed', 1, False))
        self.assertTrue({'payments_not_confirmed', 'payments_contradicted'} <= set(w['reasons']))

    def test_10_no_invoices_recorded(self):
        self.ready()
        ov, inv = self.both(self.coastline)
        w = ov['completeness']
        self.assertIn('no_invoices_recorded', w['reasons'])
        self.assertEqual((ov['recordsExist'], w['invoices']['recordedCount'], w['balanceEstablished']), (False, 0, False))
        self.assertEqual(ov['balanceLine'], 'No invoices are recorded for Coastline Foods.')
        self.assertIn('No invoices are recorded, which does not show that none were issued.', w['caveatText'])
        self.assertEqual((inv['invoiceCount'], inv['invoices']), (0, []))

    def test_11_a_customer_not_found_is_an_error_never_a_zero_balance(self):
        self.ready()
        for name, args in (('customerOverview', {}), ('invoices', {'which': 'all'})):
            status, body = self.tool(name, customerId='C-NOPE-404', **args)
            self.assertFalse(body.get('ok'), body)
            self.assertEqual(body['error'], 'INVALID_ARGUMENT')
            self.assertIn('No customer matches', body['message'])
            self.assertFalse({'result', 'completeness', 'owedNow', 'balanceLine'} & set(body), body)

    def test_12_a_genuinely_established_zero_balance(self):
        self.ready()
        invoice = self.invoice('INV-1', total='1000.00', issueDate='2026-10-05', dueDate='2026-11-05')
        self.allocate(self.pay('1000.00', date='2026-10-12', reference='EFT 1'), (invoice, '1000.00'))
        self.established(self.bayside)
        ov, inv = self.both(self.bayside)
        self.assertEqual((self.owed_minor(self.bayside), ov['completeness']['balanceEstablished'], ov['completeness']['reasons']), ('0', True, []))
        self.assertEqual(ov['owedNow']['mark'], 'worked out')                    # established records do not turn a worked-out figure into a recorded one
        self.assertEqual(ov['openCount'], 0)

    def test_an_unstated_opening_credit_blocks_an_established_balance(self):
        self.ready()
        self.opening(amount='0.00')                                              # nobody said what credits it includes
        self.attest(types=('invoices', 'payments'), start='2026-10-01', end=AS_OF)
        w = self.both(self.bayside)[0]['completeness']
        self.assertEqual((w['invoices']['state'], w['payments']['state'], w['balanceEstablished']), ('complete', 'complete', False))
        self.assertIn('opening_credits_not_stated', w['reasons'])
        self.assertIn('not fully settled', w['caveatText'])
        # the same code exact_outstanding gives, from the one shared check
        self.assertEqual(records.customer_blocks(self.positions()['customers'][self.bayside['id']]['opening'], '2026-09-30'), ['opening_credits_not_stated'])


class InvoicesToolContextTests(ContractCase):
    def three(self):
        self.ready()
        self.invoice('INV-1', total='1000.00', issueDate='2026-09-01', dueDate='2026-09-30')
        self.invoice('INV-2', total='500.00', issueDate='2026-10-05', dueDate='2026-11-05')
        self.invoice('INV-3', total='200.00', issueDate='2026-10-06', dueDate='2026-11-05')

    def test_every_list_carries_the_customers_completeness_and_says_what_it_lists(self):
        self.three()
        want = self.overview(self.bayside)['completeness']
        said = {}
        for which in ('open', 'overdue', 'all'):
            inv = self.invoices(self.bayside, which)
            self.assertEqual(inv['completeness'], want, which)
            said[which] = inv['scopeText']
            self.assertIn('not the customer\'s', inv['scopeText'])
            self.assertNotIn('completeness says', inv['scopeText'])   # no instruction to the model
        self.assertEqual(said['open'], "This list shows only the open invoices of Bayside Café, not the customer's complete account balance.")
        self.assertEqual(said['overdue'], "This list shows only the overdue invoices of Bayside Café, not the customer's complete account balance.")
        self.assertEqual(said['all'], "This list shows every recorded invoice of Bayside Café; per-invoice amounts are not the customer's account balance.")
        self.assertEqual([i['reference'] for i in self.invoices(self.bayside, 'overdue')['invoices']], ['INV-1'])

    def test_a_filtered_list_keeps_the_customer_level_context(self):
        self.three()
        want = self.overview(self.bayside)['completeness']
        for filter_ in ({'dueOn': '2026-11-05'}, {'issuedOn': '2026-10-06'}, {'dueOn': '2026-12-25'}):
            inv = self.invoices(self.bayside, 'open', **filter_)
            self.assertEqual((inv['completeness'], inv['which']), (want, 'all'), filter_)
            self.assertEqual(inv['scopeText'], "This list shows only the matching invoices of Bayside Café, not the customer's complete account balance.")
            self.assertTrue(OLD_INVOICES_KEYS <= set(inv) and 'filter' in inv)
        self.assertEqual(self.invoices(self.bayside, 'open', dueOn='2026-12-25')['invoiceCount'], 0)   # nothing matched is not "nothing owed"

    def test_amounts_on_a_list_keep_their_marks_and_unknown_amounts_are_not_zero(self):
        self.ready()
        invoice = self.invoice('INV-1', total='1000.00', issueDate='2026-10-05', dueDate='2026-11-05')
        self.allocate(self.pay('250.00', date='2026-10-12'), (invoice, '250.00'))
        self.invoice('INV-S', total='300.00', issueDate='2026-10-06')            # no due date, nothing allocated
        rows = {r['reference']: r for r in self.invoices(self.bayside)['invoices']}
        self.assertTrue(rows['INV-1']['mark'].startswith('at most'), rows['INV-1']['mark'])
        self.assertIn('750.00', rows['INV-1']['amountText'])
        self.assertTrue(rows['INV-S']['mark'].startswith('worked out'), rows['INV-S']['mark'])   # derived, never exact
        self.assertIsNone(rows['INV-S']['daysOverdue'])                           # no due date: overdue is not known, never 0
        self.assertFalse(self.invoices(self.bayside)['completeness']['balanceEstablished'])

    def test_before_the_workspace_has_a_currency_no_completeness_is_claimed(self):
        self.ready()
        self.invoice('INV-1', total='1000.00', issueDate='2026-10-05')
        tools = server.DeskTools(self.app, {'role': 'staff', 'id': 'staff_demo'}, '', None, None, None)
        tools.seen = {c['id']: c for c in tools.ev.customers}
        tools.positions = {}                                                      # records_view has no positions without a currency
        out = tools._invoices({'customerId': self.bayside['id'], 'which': 'all'})
        self.assertNotIn('completeness', out)
        self.assertNotIn('completeTo', out)
        self.assertIn('scopeText', out)
        self.assertEqual(out['invoiceCount'], 1)


class PureHelperTests(unittest.TestCase):
    COVER = {'invoices': {'completeTo': None, 'lastActivity': None, 'contradicted': []}, 'payments': {'completeTo': None, 'lastActivity': None, 'contradicted': []}}

    def view(self, invoices=None, payments=None, count=(1, 1), owed=None, blocks=(), as_of='2026-10-18', contradicted=()):
        cover = {k: {**v, 'completeTo': {'invoices': invoices, 'payments': payments}[k], 'contradicted': [{}] if k in contradicted else []} for k, v in self.COVER.items()}
        return server.completeness_view(cover, as_of, count[0], count[1], owed or {'incompleteText': None}, blocks)

    def test_state_is_judged_against_the_business_date_per_kind(self):
        w = self.view(invoices='2026-10-18', payments='2026-10-17')
        self.assertEqual((w['invoices']['state'], w['payments']['state']), ('complete', 'completeToEarlierDate'))
        self.assertEqual(self.view(invoices='2026-10-20', payments='2026-10-18')['balanceEstablished'], True)   # later than the date is still complete

    def test_unreadable_or_unplaced_records_block_an_established_balance(self):
        w = self.view(invoices='2026-10-18', payments='2026-10-18', owed={'incompleteText': 'The records are incomplete for this customer: 1 payment has no received date.'})
        self.assertEqual((w['balanceEstablished'], 'records_incomplete' in w['reasons']), (False, True))
        self.assertIn('could not be read or placed', w['caveatText'])

    def test_the_caveat_has_no_amount(self):
        for w in (self.view(), self.view(invoices='2026-10-10', payments='2026-10-18', count=(0, 0)), self.view('2026-10-18', '2026-10-18', contradicted=('payments',)),
                  self.view('2026-10-18', '2026-10-18')):
            self.assertTrue(w['caveatText'])
            self.assertIsNone(AMOUNT.search(w['caveatText']), w['caveatText'])   # dates and words only: no amount to quote


class OperationSafetyTests(ContractCase):
    """The MCP audit: what a call actually stores. Pure reads leave every table as it was; assessRequest keeps the latest assessment."""

    def snapshot(self):
        db = sqlite3.connect(self.path)
        try:
            out = {}
            for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall():
                rows = sorted(repr(r) for r in db.execute('SELECT * FROM "' + table + '"'))
                out[table] = hashlib.sha256('\n'.join(rows).encode()).hexdigest()
            return out
        finally:
            db.close()

    def case(self):
        self.ready()
        self.invoice('DEMO-501', total='1000.00', dueDate='2026-10-10')
        return self.wait_status(self.create(), ('awaiting_owner',))

    def test_pure_reads_store_nothing_for_either_role(self):
        r = self.case()
        for role in ('staff', 'owner'):
            for name, args in PURE_READS.items():
                before = self.snapshot()
                status, body = self.tool(name, role, **args(self.bayside, r))
                self.assertEqual((status, body.get('ok')), (200, True), (role, name, body))
                changed = [t for t, h in self.snapshot().items() if before.get(t) != h]
                self.assertEqual(changed, [], (role, name))

    def test_assess_request_keeps_the_latest_assessment_and_is_not_read_only(self):
        r = self.case()
        before = self.snapshot()
        status, first = self.tool('assessRequest', requestId=r['id'])
        after = self.snapshot()
        self.assertEqual((status, first['ok'], first['result']['recorded'], first['result']['version']), (200, True, True, 1))
        self.assertNotEqual(before['requests'], after['requests'])                # the documented change: the assessment kept on the case
        _, second = self.tool('assessRequest', requestId=r['id'])
        self.assertEqual(second['result']['version'], 2)                          # a new version each call
        self.assertIn('completeness', first['result'])                            # the customer-level figures it states travel with their completeness
        self.assertEqual(first['result']['completeness']['asOf'], AS_OF)

    def test_case_details_carries_the_same_completeness_as_the_overview(self):
        r = self.case()
        _, body = self.tool('caseDetails', requestId=r['id'])
        self.assertEqual(body['result']['customer']['completeness'], self.overview(self.bayside)['completeness'])


if __name__ == '__main__':
    unittest.main()
