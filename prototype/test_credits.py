"""Credits held for a customer at the opening balance, and amounts that only appear to reconcile (Stage 3 correctness pass).

A credit (a prepayment or a credit note) can settle a later invoice, so while it is unaccounted for no amount for that customer is
exact. Equal amounts suggest which records make up a balance or a statement, but only a person confirms it: offsetting
omissions (a missing invoice and a missing credit) and ambiguous identities reconcile just as well. All data is fictional."""
import unittest

from test_exact import ExactCase


class CreditCase(ExactCase):
    def credit(self, amount, date='2026-09-30', **extra):
        return self.pay(amount, date=date, kind='credit', reference=extra.pop('reference', 'Credit note CN-1'), **extra)


class OpeningCreditTests(CreditCase):
    def test_an_unaccounted_opening_credit_blocks_an_exact_amount(self):
        self.ready()                                                            # the reported case
        self.opening(amount='50.00', direction='credit')                       # AUD 50 held in credit as at 30 Sep
        invoice = self.invoice('INV-1', total='100.00', issueDate='2026-10-05')
        self.attest(start='2026-10-01', end='2026-10-18')
        self.assertIsNone(self.exact(invoice))
        self.assertIn('credit of AUD 50.00', self.not_exact(invoice))

    def test_a_credit_applied_to_the_invoice_comes_off_it(self):
        self.ready()
        self.opening(amount='50.00', direction='credit', credits='recorded')
        invoice = self.invoice('INV-1', total='100.00', issueDate='2026-10-05')
        held = self.credit('50.00', inclusion='included')
        self.allocate(held, (invoice, '50.00'))
        self.attest(start='2026-10-01', end='2026-10-18')
        self.assertEqual(self.minor(self.exact(invoice)['amount']), '5000')

    def test_a_credit_kept_for_something_else_leaves_the_invoice_amount(self):
        self.ready()
        self.opening(amount='50.00', direction='credit', credits='recorded')
        invoice = self.invoice('INV-1', total='100.00', issueDate='2026-10-05')
        held = self.credit('50.00', inclusion='included')
        self.attest(start='2026-10-01', end='2026-10-18')
        self.assertIn('neither allocated nor marked', self.not_exact(invoice))
        self.unrelated(held)
        self.assertEqual(self.minor(self.exact(invoice)['amount']), '10000')

    def test_a_credit_balance_cannot_be_stated_to_have_no_credits(self):
        self.ready()
        self.assertEqual(self.opening(amount='50.00', direction='credit', credits='none', expect=400)['field'], 'credits')

    def test_credits_recorded_must_cover_the_credits_the_balance_implies(self):
        self.ready()
        self.opening(amount='50.00', direction='credit', credits='recorded')   # says every credit is recorded, but none is
        invoice = self.invoice('INV-1', total='100.00', issueDate='2026-10-05')
        self.attest(start='2026-10-01', end='2026-10-18')
        self.assertIn('only AUD 0.00', self.not_exact(invoice))

    def test_a_positive_net_balance_may_hold_credits_too(self):
        self.ready()
        self.opening(amount='1000.00')                                          # net: 1,200 still owed on INV-77, so a 200 credit sits in it
        self.include('invoices', self.invoice('INV-77', total='1200.00', issueDate='2026-09-10'), 'included', stillOwed='1200.00')
        later = self.invoice('INV-90', total='300.00', issueDate='2026-10-05')
        self.attest(start='2026-10-01', end='2026-10-18')
        self.assertIn('includes credits', self.not_exact(later))
        self.correct('openingBalances', self.app.fixture()['openingBalances'][0], credits='none', reason='Accountant: no credits')
        self.assertIsNone(self.exact(later))                                    # 1,200 owed against 1,000 net contradicts "no credits"
        self.assertTrue(self.view()['conflicts'])

    def test_without_an_opening_balance_the_position_before_completeness_is_unknown(self):
        self.ready()
        invoice = self.invoice('INV-1', total='100.00', issueDate='2026-10-05')
        self.attest(start='2026-10-01', end='2026-10-18')
        self.assertIsNone(self.exact(invoice))
        self.assertIn('No opening balance', self.not_exact(invoice))

    def test_money_received_before_the_opening_balance_still_needs_a_disposition(self):
        self.ready()
        self.opening(amount='0.00', credits='none')
        early = self.pay('50.00', date='2026-09-20', inclusion='included')     # included in the balance, not applied to anything
        invoice = self.invoice('INV-1', total='100.00', issueDate='2026-10-05')
        self.attest(start='2026-10-01', end='2026-10-18')
        self.assertIn('neither allocated nor marked', self.not_exact(invoice))
        self.unrelated(early)
        self.assertEqual(self.minor(self.exact(invoice)['amount']), '10000')

    def test_the_owner_is_told_why_a_credit_blocks_the_amount_and_a_later_disposition_is_flagged(self):
        self.ready()
        self.opening(amount='50.00', direction='credit', credits='recorded')
        invoice = self.invoice('DEMO-501', total='100.00', issueDate='2026-10-05')
        held = self.credit('50.00', inclusion='included')
        self.attest(start='2026-10-01', end='2026-10-18')
        r = self.wait_status(self.create(), ('awaiting_owner',))
        items = {i['kind']: i['text'] for i in r['analysis']['brief']['openItems']}
        self.assertIn('neither allocated nor marked', items['not_exact'])
        self.assertEqual(self.decide(r)[0], 201)
        done = self.wait_status(r, ('completed',))
        self.allocate(held, (invoice, '50.00'))
        flag = self.reopen(done)['flags'][-1]
        self.assertEqual(flag['outstandingNow'], 'exactly AUD 50.00 as of Sun 18 Oct 2026')


class ReconciliationTests(CreditCase):
    def test_equal_amounts_only_suggest_what_an_opening_balance_is_made_of(self):
        self.ready()
        self.opening(amount='1500.00', credits='none')
        self.invoice('INV-77', total='1200.00', issueDate='2026-09-01', stillOwed='1200.00', stillOwedAsOf='2026-09-30')
        self.invoice('INV-78', total='300.00', issueDate='2026-09-15', stillOwed='300.00', stillOwedAsOf='2026-09-30')
        view = self.view()
        self.assertEqual((self.statuses(), sorted(view['suggestion']['references'])),
                         ({'INV-77': 'unresolved', 'INV-78': 'unresolved'}, ['INV-77', 'INV-78']))

    def test_a_missing_invoice_and_a_missing_credit_can_reconcile_just_as_well(self):
        self.ready()
        # The accountant's 1,500 is really INV-77 (1,200) + an invoice not in these records (500) - a credit (200); INV-78 was left out.
        self.opening(amount='1500.00')
        self.invoice('INV-77', total='1200.00', issueDate='2026-09-01', stillOwed='1200.00', stillOwedAsOf='2026-09-30')
        late = self.invoice('INV-78', total='300.00', issueDate='2026-09-15', stillOwed='300.00', stillOwedAsOf='2026-09-30')
        self.assertTrue(self.view()['suggestion'])                              # the amounts reconcile...
        self.include('invoices', late, 'missed')                                # ...but a person knows better
        self.assertEqual((self.statuses()['INV-78'], self.view()['suggestion']), ('missed', None))
        self.assertEqual(self.minor(self.view()['balance']), '180000')

    def test_no_suggestion_when_several_combinations_would_reconcile(self):
        self.ready()
        self.opening(amount='600.00')
        for ref in ('INV-1', 'INV-2', 'INV-3'):                                 # any two of three equal invoices make 600
            self.invoice(ref, total='300.00', issueDate='2026-09-10', stillOwed='300.00', stillOwedAsOf='2026-09-30')
        self.assertEqual((self.view()['suggestion'], set(self.statuses().values())), (None, {'unresolved'}))

    def test_an_exact_amount_waits_for_a_person_to_confirm_a_suggestion(self):
        self.ready()
        self.opening(amount='1000.00', credits='none')
        invoice = self.invoice('INV-77', total='1000.00', issueDate='2026-09-01', stillOwed='1000.00', stillOwedAsOf='2026-09-30')
        self.attest(start='2026-10-01', end='2026-10-18')
        self.assertIsNone(self.exact(invoice))
        self.include('invoices', invoice, 'included')
        self.assertEqual(self.minor(self.exact(invoice)['amount']), '100000')

    def test_a_statement_that_reconciles_with_earlier_payments_is_a_suggestion(self):
        self.ready()
        invoice = self.stated_invoice()
        early = self.pay('600.00', date='2026-10-05')
        self.allocate(early, (invoice, '600.00'))
        position = self.positions()['invoices'][invoice['id']]
        allocation = next(a['id'] for a in self.app.fixture()['allocations'])
        self.assertEqual((position['inclusion']['reconciles'], position['inclusion']['unresolved'], self.minor(position['atMost'])),
                         ([allocation], [allocation], '40000'))

    def test_a_reconciling_statement_can_still_be_wrong(self):
        # 1,000 - 600 = 400 as stated, but the 400 really reflects an unrecorded 600 credit note: the payment still comes off.
        self.ready()
        invoice = self.stated_invoice()
        early = self.pay('600.00', date='2026-10-05')
        self.allocate(early, (invoice, '600.00'))
        allocation = next(a for a in self.app.fixture()['allocations'])
        self.call('/api/records/allocations/' + allocation['id'] + '/statement', {'status': 'missed'}, 'staff', 'missed')
        position = self.positions()['invoices'][invoice['id']]
        self.assertEqual((position['status'], position['inclusion']['reconciles']), ('conflict', []))

    def stated_invoice(self):
        return self.invoice('INV-1', total='1000.00', stillOwed='400.00', stillOwedAsOf='2026-10-09')



class CreditsInCasesAndRevertsTests(CreditCase):
    def brief_items(self, r):
        return {i['kind']: i['text'] for i in r['analysis']['brief']['openItems']}

    def test_the_owner_sees_suggestions_as_suggestions_and_what_was_said_about_credits(self):
        self.ready()
        self.opening(amount='1500.00')
        self.invoice('INV-77', total='1200.00', issueDate='2026-09-01', stillOwed='1200.00', stillOwedAsOf='2026-09-30')
        self.invoice('INV-78', total='300.00', issueDate='2026-09-15', stillOwed='300.00', stillOwedAsOf='2026-09-30')
        self.invoice('DEMO-501', total='1000.00', issueDate='2026-10-02', stillOwed='400.00', stillOwedAsOf='2026-10-09')
        self.allocate(self.pay('600.00', date='2026-10-05'), (self.app.fixture()['invoices'][-1], '600.00'))
        items = self.brief_items(self.wait_status(self.create(), ('awaiting_owner',)))
        self.assertIn('not assumed until a person confirms', items['opening_reconciles'])
        self.assertIn('not stated', items['opening_credits'])
        self.assertIn('unrecorded credit would reconcile just as well', items['statement_reconciles'])

    def test_saying_the_balance_has_no_credits_changes_a_decided_cases_evidence_visibly(self):
        self.ready()
        ob = self.opening(amount='0.00')
        self.invoice('DEMO-501', total='1000.00', issueDate='2026-10-05')
        self.attest(start='2026-10-01', end='2026-10-18')
        r = self.wait_status(self.create(), ('awaiting_owner',))
        self.assertEqual(self.decide(r)[0], 201)
        done = self.wait_status(r, ('completed',))
        self.correct('openingBalances', ob, credits='none', reason='Accountant: no credits')
        flag = self.reopen(done)['flags'][-1]
        self.assertEqual((flag['outstandingBefore'], flag['outstandingNow']), ('not recorded', 'exactly AUD 1,000.00 as of Sun 18 Oct 2026'))

    def test_answers_confirmed_from_a_suggestion_are_listed_when_reverting_the_import(self):
        self.records_setup()
        bayside = self.customers['Bayside Café']
        self.opening(bayside, amount='1400.00', as_of='2026-10-09', credits='none')
        for ref in ('INV-1001', 'INV-1002'):
            self.include('invoices', self.invoices[('Bayside Café', ref)], 'included')
        self.opening(self.customers['Coastline Foods'], amount='0.00', key='coastline-ob')
        status, error, _ = self.call('/api/imports/' + next(b for b in self.call('/api/imports', role='staff')[1])['id'] + '/revert',
                                     {'reason': 'Wrong file'}, 'staff', 'rv')
        self.assertEqual((status, error['error']), (409, 'REVERT_BLOCKED'))   # its customers now have opening balances
        self.assertEqual(len(error['impact']['review']['answers']), 2)

if __name__ == '__main__':
    unittest.main()
