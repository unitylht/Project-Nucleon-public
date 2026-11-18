"""The ledger replay (behaviour.replay) on a fixture computed by hand: three invoices, two payments, one recorded allocation.
All data is fictional."""
import unittest
from datetime import date

from behaviour import FEATURES, assessment_facts, checks_for, facts_view, recommend, replay


def money(units, scale=2, currency='AUD'):
    return {'minorUnits': str(units), 'currency': currency, 'scale': scale}


def invoice(id, issue, due, total, scale=2):
    return {'id': id, 'issueDate': issue, 'originalDueDate': due, 'total': money(total, scale)}


def payment(id, day, amount, scale=2):
    return {'id': id, 'receivedDate': day, 'amount': money(amount, scale)}


def allocation(payment_id, invoice_id, amount, scale=2):
    return {'id': 'a-' + payment_id + invoice_id, 'paymentId': payment_id, 'invoiceId': invoice_id, 'amount': money(amount, scale)}


# A 1000.00 issued 1 Jan due 31 Jan (30 days); B 500.00 issued 1 Feb due 1 Mar (28); C 300.00 issued 1 Mar due 31 Mar (30).
# P1 600.00 on 20 Jan (nothing past due then); P2 400.00 on 20 Mar (A and B past due then).
def ledger(scale=2):
    return ([invoice('A', '2026-01-01', '2026-01-31', 100000, scale), invoice('B', '2026-02-01', '2026-03-01', 50000, scale),
             invoice('C', '2026-03-01', '2026-03-31', 30000, scale)],
            [payment('P1', '2026-01-20', 60000, scale), payment('P2', '2026-03-20', 40000, scale)])


class ReplayTests(unittest.TestCase):
    def test_fifo_by_hand(self):
        invoices, payments = ledger()
        got = replay(invoices, payments, [], [], date(2026, 4, 10))
        # P2 pays A's last 400.00 (A is 0); B 500.00 (40 days past due) and C 300.00 (10 days) remain
        self.assertEqual({k: got[k] for k in FEATURES}, {
            'credit_term_days': 30, 'debt_before_m': 80000, 'overdue_before_m': 80000, 'max_days_past_due_before': 40,
            'prior_invoice_documents': 3, 'prior_billed_m': 180000, 'prior_received_m': 100000, 'prior_receipt_count': 2,
            'has_prior_receipt': 1, 'days_since_prior_receipt': 21, 'observed_relationship_days': 99, 'prior_late_receipt_fraction': 0.5})
        self.assertEqual((got['lateReceipts'], got['allocationBasis'], got['reconciles'], got['difference']), (1, 'fifo', True, 0))

    def test_a_recorded_allocation_beats_fifo_and_the_basis_says_mixed(self):
        invoices, payments = ledger()
        # P2 recorded as 300.00 to C and 100.00 to B; P1 has no record, so FIFO pays A 600.00
        got = replay(invoices, payments, [allocation('P2', 'C', 30000), allocation('P2', 'B', 10000)], [], date(2026, 4, 10))
        self.assertEqual((got['debt_before_m'], got['overdue_before_m'], got['max_days_past_due_before']), (80000, 80000, 69))   # A 400.00 (69 days) and B 400.00
        self.assertEqual((got['allocationBasis'], got['reconciles'], got['lateReceipts']), ('mixed', True, 1))

    def test_a_recorded_allocation_to_a_later_invoice_leaves_the_older_one_open(self):
        invoices = [invoice('A', '2026-01-01', '2026-01-31', 10000), invoice('B', '2026-02-01', '2026-03-03', 5000)]
        payments = [payment('P1', '2026-02-10', 5000)]   # recorded to B, while A (older) is open
        got = replay(invoices, payments, [allocation('P1', 'B', 5000)], [], date(2026, 4, 1))
        self.assertEqual((got['debt_before_m'], got['overdue_before_m'], got['reconciles'], got['difference']), (10000, 10000, True, 0))
        # a later payment recorded to A: oldest-first from the earlier payment must not consume it
        invoices = [invoice('A', '2026-01-01', '2026-01-31', 10000), invoice('B', '2026-01-05', '2026-02-04', 10000)]
        payments = [payment('P1', '2026-02-01', 10000), payment('P2', '2026-02-10', 10000)]
        got = replay(invoices, payments, [allocation('P2', 'A', 10000)], [], date(2026, 4, 1))
        self.assertEqual((got['debt_before_m'], got['overdue_before_m'], got['reconciles'], got['lateReceipts']), (0, 0, True, 2))

    def test_a_prepayment_is_carried_to_the_invoices_that_follow(self):
        invoices = [invoice('A', '2026-02-01', '2026-03-03', 10000), invoice('B', '2026-03-01', '2026-03-31', 4000)]
        payments = [payment('P1', '2026-01-05', 12000)]
        got = replay(invoices, payments, [], [], date(2026, 6, 1))
        self.assertEqual((got['debt_before_m'], got['overdue_before_m'], got['reconciles'], got['lateReceipts']), (2000, 2000, True, 0))   # B 20.00 open, past due
        self.assertEqual(got['prepaymentApplied'], 12000)
        got = replay(invoices, payments, [], [], date(2026, 2, 15))
        self.assertEqual((got['debt_before_m'], got['overdue_before_m'], got['prepaymentApplied']), (0, 0, 10000))
        text = facts_view(replay(invoices, payments, [], [], date(2026, 6, 1)), {'currency': 'AUD', 'scale': 2}, date(2026, 6, 1))['prepaymentText']
        self.assertIn('was received before any invoice was open and applied to later invoices', text)

    def test_an_opening_advance_in_credit_is_applied_to_invoices_as_issued(self):
        invoices = [invoice('A', '2026-02-01', '2026-03-03', 10000), invoice('B', '2026-03-01', '2026-03-31', 4000)]
        opening = [{'id': 'O1', 'asOf': '2026-01-01', 'amount': money(-12000)}]
        got = replay(invoices, [], [], opening, date(2026, 6, 1))
        self.assertEqual((got['debt_before_m'], got['overdue_before_m'], got['reconciles'], got['openingCreditApplied']), (2000, 2000, True, 12000))
        text = facts_view(got, {'currency': 'AUD', 'scale': 2}, date(2026, 6, 1))['openingCreditText']
        self.assertIn('was held in credit at the start and applied to later invoices', text)
        self.assertIn('120.00', text)

    def test_lateness_does_not_depend_on_the_order_of_payments_on_one_day(self):
        invoices = [invoice('A', '2026-01-01', '2026-01-31', 10000)]
        payments = [payment('P1', '2026-03-01', 10000), payment('P2', '2026-03-01', 500)]
        got = replay(invoices, payments, [], [], date(2026, 4, 1))
        self.assertEqual(got['lateReceipts'], 2)

    def test_a_payment_dated_before_its_recorded_invoice(self):
        invoices = [invoice('A', '2026-01-01', '2026-01-31', 10000), invoice('B', '2026-02-01', '2026-03-03', 5000)]
        payments = [payment('P1', '2026-01-10', 5000)]   # recorded to B, which is issued later
        got = replay(invoices, payments, [allocation('P1', 'B', 5000)], [], date(2026, 4, 1))
        self.assertEqual((got['debt_before_m'], got['overdue_before_m'], got['reconciles']), (10000, 10000, True))   # A stays open; B was paid on issue
        self.assertEqual((got['allocationBasis'], got['prepaymentApplied']), ('recorded', 5000))

    def test_every_payment_recorded_is_recorded(self):
        invoices, payments = ledger()
        got = replay(invoices, payments, [allocation('P1', 'A', 60000), allocation('P2', 'A', 40000)], [], date(2026, 4, 10))
        self.assertEqual((got['allocationBasis'], got['max_days_past_due_before'], got['debt_before_m']), ('recorded', 40, 80000))

    def test_before_is_strictly_before_the_date(self):
        invoices, payments = ledger()
        got = replay(invoices, payments, [], [], date(2026, 3, 20))   # P2 arrives that day: not before it
        self.assertEqual((got['prior_receipt_count'], got['lateReceipts'], got['prior_late_receipt_fraction']), (1, 0, 0.0))
        self.assertEqual((got['debt_before_m'], got['overdue_before_m'], got['max_days_past_due_before']), (120000, 90000, 48))   # A 400.00 and B 500.00
        self.assertEqual(replay(invoices, payments, [], [], date(2026, 1, 1))['prior_invoice_documents'], 0)   # A is issued that day

    def test_nothing_before_the_date_has_no_fraction_and_no_days(self):
        got = replay(*ledger(), [], [], date(2025, 1, 1))
        self.assertEqual((got['prior_late_receipt_fraction'], got['days_since_prior_receipt'], got['observed_relationship_days'], got['credit_term_days']),
                         (None, None, None, None))
        self.assertEqual((got['has_prior_receipt'], got['allocationBasis'], got['reconciles']), (0, 'fifo', True))

    def test_money_of_a_zero_scale_currency_is_whole_units(self):
        invoices, payments = ledger(scale=0)
        got = replay(invoices, payments, [], [], date(2026, 4, 10))
        self.assertEqual((got['debt_before_m'], got['prior_billed_m']), (80000, 180000))   # VND 80,000 of VND 180,000

    def test_an_opening_balance_is_debt_with_no_age_and_an_overpayment_does_not_reconcile(self):
        opening = [{'id': 'O', 'asOf': '2026-01-01', 'amount': money(20000)}]
        got = replay([invoice('A', '2026-01-10', '2026-02-09', 10000)], [payment('P', '2026-01-20', 5000)], [], opening, date(2026, 4, 1))
        self.assertEqual((got['debt_before_m'], got['overdue_before_m'], got['openingBalance'], got['reconciles']), (25000, 5000, 20000, True))
        over = replay([invoice('A', '2026-01-10', '2026-02-09', 10000)], [payment('P', '2026-01-20', 15000)], [], [], date(2026, 4, 1))
        self.assertEqual((over['debt_before_m'], over['reconciles'], over['difference']), (0, False, 5000))   # 50.00 paid beyond what was billed

    def test_a_payment_beyond_the_open_invoices_reduces_the_opening_balance_and_the_sentence_names_what_remains(self):
        opening = [{'id': 'O', 'asOf': '2026-01-01', 'amount': money(20000)}]
        got = replay([invoice('A', '2026-01-10', '2026-02-09', 10000)], [payment('P', '2026-01-20', 15000)], [], opening, date(2026, 4, 1))
        self.assertEqual((got['debt_before_m'], got['openingBalance'], got['openingOwing'], got['reconciles']), (15000, 20000, 15000, True))
        said = facts_view(got, {'currency': 'AUD', 'scale': 2}, date(2026, 4, 1))['items']
        debt = next(x['text'] for x in said if x['name'] == 'debt_before_m')
        self.assertIn('AUD 150.00 of the opening balance of AUD 200.00 remains after payments', debt)
        self.assertNotIn('It includes AUD 200.00', debt)
        untouched = replay([invoice('A', '2026-01-10', '2026-02-09', 10000)], [payment('P', '2026-01-20', 5000)], [], opening, date(2026, 4, 1))
        text = next(x['text'] for x in facts_view(untouched, {'currency': 'AUD', 'scale': 2}, date(2026, 4, 1))['items'] if x['name'] == 'debt_before_m')
        self.assertIn('It includes AUD 200.00 from an opening balance of unknown age.', text)

    def test_removed_records_and_those_inside_the_opening_balance_are_ignored(self):
        invoices, payments = ledger()
        invoices[0] = {**invoices[0], 'status': 'removed'}
        invoices[1] = {**invoices[1], 'openingInclusion': {'status': 'included'}}
        self.assertEqual(replay(invoices, payments, [], [], date(2026, 4, 10))['prior_invoice_documents'], 1)

    def test_the_median_term_averages_the_two_middle_values_and_rounds_a_half_day_up(self):
        got = replay([invoice('A', '2026-01-01', '2026-01-31', 100), invoice('B', '2026-02-01', '2026-03-02', 100)], [], [], [], date(2026, 4, 1))
        self.assertEqual(got['credit_term_days'], 30)   # terms 30 and 29: 29.5

    def test_the_request_s_own_invoice_is_left_out_of_what_else_is_overdue(self):
        invoices, payments = ledger()
        got = replay(invoices, payments, [], [], date(2026, 4, 10), 'B')   # B: 500.00, 40 days past due; C: 300.00, 10 days
        self.assertEqual((got['overdue_before_m'], got['overdue_other_m'], got['own_overdue_m'], got['own_days_past_due']), (80000, 30000, 50000, 40))

    def test_the_own_invoice_text_states_the_date_and_the_matching_apart(self):   # live test L1
        from behaviour import facts_view
        tpl = {'currency': 'AUD', 'scale': 2}
        text = lambda *a: facts_view(replay(*ledger(), [], [], date(*a[:3]), a[3]), tpl, date(*a[:3]))['ownInvoiceText']
        self.assertEqual(text(2026, 4, 10, 'B'), 'This invoice was due on Sun 1 Mar 2026, 40 days before this date. By oldest-first matching, AUD 500.00 of it is still open.')
        self.assertEqual(text(2026, 4, 10, 'A'), 'This invoice was due on Sat 31 Jan 2026, 69 days before this date. By oldest-first matching, '
                         'earlier payments already cover it; the records state no amount still owed for it.')
        self.assertEqual(text(2026, 3, 20, 'C'), 'This invoice is due on Tue 31 Mar 2026, in 11 days.')

    def test_a_stated_amount_without_a_total_counts_and_an_unreadable_invoice_makes_it_incomplete(self):   # live test L10
        from behaviour import checks_for, facts_view, recommend
        tpl = {'currency': 'AUD', 'scale': 2}
        demo = {'id': 'invoice_demo_101', 'reference': 'DEMO-101', 'originalDueDate': '2026-10-20', 'outstandingAmount': money(125000)}
        early = replay([demo], [], [], [], date(2026, 10, 16), demo['id'])
        self.assertEqual((early['prior_invoice_documents'], early['undatedInvoices'], early['debt_before_m'], early['overdue_before_m'], early['incomplete'], early['reconciles']),
                         (0, 1, 125000, 0, False, True))   # Repair D: no issue date, so counted in what is owed but not in the history
        late = replay([demo], [], [], [], date(2026, 10, 25), demo['id'])
        self.assertEqual((late['overdue_before_m'], late['own_overdue_m'], late['own_days_past_due']), (125000, 125000, 5))
        broken = replay([demo, {'id': 'x', 'originalDueDate': '2026-10-01'}], [], [], [], date(2026, 10, 16))
        self.assertEqual((broken['incomplete'], broken['unreadableInvoices']), (True, 1))
        facts = facts_view(broken, tpl, date(2026, 10, 16))
        self.assertIn('incomplete', facts['incompleteText'])
        auth = {'requireNothingOverdue': False, 'maxPriorLateShare': None, 'staffMayApproveUpToDays': 30, 'maxOutstanding': None, 'hardRules': []}
        self.assertEqual(recommend(auth, checks_for(auth, early, 7, tpl))['outcome'], 'approve_within_authority')
        rec = recommend(auth, checks_for(auth, broken, 7, tpl))
        self.assertEqual(rec['outcome'], 'escalate')

    def test_the_late_share_is_compared_without_floats(self):
        from behaviour import checks_for
        f = {**replay(*ledger(), [], [], date(2026, 4, 10)), 'lateReceipts': 1, 'prior_receipt_count': 3, 'prior_late_receipt_fraction': 1 / 3}
        auth = {'requireNothingOverdue': False, 'maxPriorLateShare': 0.3333333333333333, 'staffMayApproveUpToDays': 5, 'maxOutstanding': None}
        self.assertFalse(next(c for c in checks_for(auth, f, 1, {'currency': 'AUD', 'scale': 2}) if c['name'] == 'late_history')['passes'])  # 1/3 is more than 0.3333...

    # Repair A, F1: an invoice entered on the as-of date is owed that day; history stays strictly before it
    def test_invoices_entered_on_the_as_of_day_count_as_current_facts_while_history_stays_before_it(self):
        from behaviour import assessment_facts, checks_for, facts_view, recommend
        tpl = {'currency': 'VND', 'scale': 0}
        day = date(2026, 10, 23)
        a = {**invoice('QA1', '2026-10-23', '2026-10-30', 1000000, 0), 'outstandingAmount': money(1000000, 0, 'VND')}
        b = {**invoice('QA2', '2026-10-23', '2026-10-30', 2000000, 0), 'outstandingAmount': money(2000000, 0, 'VND')}
        old = replay([a, b], [], [], [], day, 'QA1')
        self.assertEqual((old['prior_invoice_documents'], old['debt_before_m'], old['incomplete']), (0, 0, True))   # the strict replay misses both (and the target)
        f = assessment_facts([a, b], [], [], [], day, 'QA1')
        self.assertEqual((f['debt_before_m'], f['overdue_before_m'], f['incomplete'], f['ownOpen'], f['current_invoice_documents']), (3000000, 0, False, 1000000, 2))
        self.assertEqual((f['prior_invoice_documents'], f['prior_billed_m'], f['prior_receipt_count']), (0, 0, 0))   # history is still strictly before
        text = facts_view(f, tpl, day)
        self.assertIn('VND 3,000,000 owed', text['currentText'])
        self.assertIn('VND 1,000,000 is still owed', text['ownOpenText'])
        auth = {'requireNothingOverdue': True, 'maxPriorLateShare': None, 'staffMayApproveUpToDays': 30, 'maxOutstanding': money(2500000, 0, 'VND'), 'hardRules': []}
        checks = {c['name']: c for c in checks_for(auth, f, 7, tpl)}
        self.assertFalse(checks['outstanding_amount']['passes'])   # VND 3,000,000 is over the VND 2,500,000 limit
        self.assertIn('3,000,000', checks['outstanding_amount']['sentence'])
        self.assertEqual(recommend(auth, list(checks.values()))['outcome'], 'escalate')

    def test_imported_invoices_with_totals_and_a_payment_on_the_day_are_current(self):
        from behaviour import assessment_facts, checks_for
        day = date(2026, 10, 23)
        invs = [invoice('I1', '2026-10-23', '2026-11-22', 5000000, 0), invoice('I2', '2026-10-01', '2026-10-10', 4000000, 0)]
        f = assessment_facts(invs, [payment('P', '2026-10-23', 1000000, 0)], [], [], day, 'I1')
        self.assertEqual((f['debt_before_m'], f['overdue_before_m'], f['overdue_other_m'], f['ownOpen']), (8000000, 3000000, 3000000, 5000000))
        auth = {'requireNothingOverdue': False, 'maxPriorLateShare': None, 'staffMayApproveUpToDays': 30, 'maxOutstanding': money(6000000, 0, 'VND'), 'hardRules': []}
        self.assertFalse(next(c for c in checks_for(auth, f, 7, {'currency': 'VND', 'scale': 0}) if c['name'] == 'outstanding_amount')['passes'])

    def test_a_target_invoice_missing_from_the_current_records_makes_the_assessment_incomplete_and_escalate(self):
        from behaviour import assessment_facts, checks_for, recommend
        day = date(2026, 10, 23)
        f = assessment_facts([invoice('Z', '2026-10-24', '2026-11-30', 1000000, 0)], [], [], [], day, 'Z')   # dated after the as-of date
        self.assertTrue(f['incomplete'] and f['ownMissing'])
        auth = {'requireNothingOverdue': True, 'maxPriorLateShare': None, 'staffMayApproveUpToDays': 30, 'maxOutstanding': None, 'hardRules': []}
        rec = recommend(auth, checks_for(auth, f, 7, {'currency': 'VND', 'scale': 0}))
        self.assertEqual(rec['outcome'], 'escalate')
        self.assertIn('not among the current records', ' '.join(rec['reasons']))


# Repair D: an active record whose timing cannot be established never silently reduces current exposure or makes a request eligible
class UndatedRecordsTests(unittest.TestCase):
    DAY = date(2026, 10, 23)
    TPL = {'currency': 'VND', 'scale': 0}
    AUTH = {'requireNothingOverdue': True, 'maxPriorLateShare': None, 'staffMayApproveUpToDays': 14, 'hardRules': [], 'maxOutstanding': money(500000000, 0, 'VND')}

    def target(self, **extra):
        return {**invoice('T', '2026-10-23', '2026-10-30', 1000000, 0), 'outstandingAmount': money(1000000, 0, 'VND'), **extra}

    def undated(self, id='U', due='2026-10-01', total=600000000, owed=600000000, **extra):
        i = {'id': id}
        if due:
            i['originalDueDate'] = due
        if total:
            i['total'] = money(total, 0, 'VND')
        if owed:
            i['outstandingAmount'] = money(owed, 0, 'VND')
        return {**i, **extra}

    def outcome(self, f, asked=7):
        checks = checks_for(self.AUTH, f, asked, self.TPL)
        return {c['name']: c for c in checks}, recommend(self.AUTH, checks)

    def test_1_an_undated_invoice_with_a_total_and_a_stated_amount_counts_for_exposure_and_overdue(self):   # the reviewer's case
        f = assessment_facts([self.target(), self.undated()], [], [], [], self.DAY, 'T')
        self.assertEqual((f['debt_before_m'], f['overdue_before_m'], f['max_days_past_due_before'], f['overdue_other_m'], f['incomplete']),
                         (601000000, 600000000, 22, 600000000, False))
        self.assertEqual((f['prior_invoice_documents'], f['prior_billed_m'], f['undatedInvoices']), (0, 0, 1))   # left out of the history
        self.assertTrue(f['reconciles'], f['difference'])
        checks, rec = self.outcome(f)
        self.assertFalse(checks['outstanding_amount']['passes'])   # VND 601,000,000 is over the VND 500,000,000 limit
        self.assertFalse(checks['nothing_overdue']['passes'])
        self.assertEqual(rec['outcome'], 'escalate')
        text = facts_view(f, self.TPL, self.DAY)
        self.assertEqual(text['undatedText'], '1 invoice has no issue date: counted in what is owed and overdue, left out of the history.')
        self.assertIn('VND 601,000,000 owed, VND 600,000,000 of it overdue. 1 invoice has no issue date', text['currentText'])

    def test_2_the_undated_invoice_as_the_target_is_counted_and_says_its_issue_date_is_missing(self):
        f = assessment_facts([self.undated(id='U', due='2026-10-01'), self.target()], [], [], [], self.DAY, 'U')
        self.assertEqual((f['debt_before_m'], f['ownOpen'], f['own_overdue_m'], f['own_days_past_due'], f['overdue_other_m'], f['incomplete']),
                         (601000000, 600000000, 600000000, 22, 0, False))
        text = facts_view(f, self.TPL, self.DAY)
        self.assertIn('The issue date of this invoice is missing', text['ownInvoiceText'])
        self.assertIn('was due on Thu 1 Oct 2026, 22 days before this date', text['ownInvoiceText'])
        self.assertIn('VND 600,000,000 is still owed', text['ownOpenText'])

    def test_3_an_undated_invoice_with_a_total_only_counts_by_total_less_allocations(self):
        pay = payment('P', '2026-10-10', 100000000, 0)
        f = assessment_facts([self.target(), self.undated(owed=None)], [pay], [allocation('P', 'U', 100000000, 0)], [], self.DAY, 'T')
        self.assertEqual((f['debt_before_m'], f['overdue_before_m'], f['incomplete'], f['allocationBasis']), (501000000, 500000000, False, 'recorded'))
        self.assertTrue(f['reconciles'], f['difference'])
        bare = assessment_facts([self.target(), self.undated(owed=None)], [], [], [], self.DAY, 'T')
        self.assertEqual((bare['debt_before_m'], bare['overdue_before_m']), (601000000, 600000000))
        # an undated payment's recorded allocation counts too; the unallocated rest of a dated payment is not applied to an undated invoice
        undated_pay = {'id': 'Q', 'amount': money(100000000, 0)}
        g = assessment_facts([self.target(), self.undated(owed=None)], [undated_pay], [allocation('Q', 'U', 100000000, 0)], [], self.DAY, 'T')
        self.assertEqual((g['debt_before_m'], g['incomplete']), (501000000, False))
        self.assertTrue(g['reconciles'], g['difference'])
        h = assessment_facts([self.target(), self.undated(owed=None)], [payment('R', '2026-10-10', 700000000, 0)], [], [], self.DAY, 'T')
        self.assertEqual(h['debt_before_m'], 600000000)   # the target is paid; the rest is not applied to an invoice whose age is unknown

    def test_4_an_active_invoice_with_neither_amount_makes_the_assessment_incomplete_and_escalate(self):
        f = assessment_facts([self.target(), {'id': 'N', 'originalDueDate': '2026-10-01'}], [], [], [], self.DAY, 'T')
        self.assertEqual((f['incomplete'], f['unreadableInvoices'], f['debt_before_m']), (True, 1, 1000000))
        checks, rec = self.outcome(f)
        self.assertFalse(checks['records_complete']['passes'])
        self.assertEqual(rec['outcome'], 'escalate')
        both = assessment_facts([self.target(), {'id': 'N'}], [], [], [], self.DAY, 'T')   # no due date either
        self.assertTrue(both['incomplete'])

    def test_6_an_open_invoice_without_a_due_date_counts_and_makes_the_assessment_incomplete(self):
        f = assessment_facts([self.target(), {**invoice('ND', '2026-09-01', None, 700000, 0)}], [], [], [], self.DAY, 'T')
        self.assertEqual((f['debt_before_m'], f['noDueDate'], f['incomplete']), (1700000, 1, True))
        self.assertIn('1 invoice has no due date: whether it is overdue cannot be established', facts_view(f, self.TPL, self.DAY)['incompleteText'])
        checks, rec = self.outcome(f)
        self.assertFalse(checks['records_complete']['passes'])
        self.assertEqual(rec['outcome'], 'escalate')
        settled = assessment_facts([self.target(), invoice('ND', '2026-09-01', None, 700000, 0)], [payment('P', '2026-09-05', 700000, 0)], [], [], self.DAY, 'T')
        self.assertFalse(settled['incomplete'])   # nothing open on it, so nothing to be overdue
        self.assertTrue(assessment_facts([self.undated(due=None)], [], [], [], self.DAY)['incomplete'])

    def test_7_an_open_invoice_without_a_due_date_is_overdue_unknown_not_none(self):   # repair E, finding A
        f = assessment_facts([self.target(), {**invoice('ND', '2026-10-23', None, 2000000, 0)}], [], [], [], self.DAY, 'T')
        said = {i['name']: i['text'] for i in facts_view(f, self.TPL, self.DAY)['items']}
        self.assertIn('Overdue not known: 1 open invoice has no due date (VND 2,000,000).', said['overdue_before_m'])
        self.assertNotIn('Nothing is overdue', said['overdue_before_m'])
        self.assertNotIn('Nothing is past due', said['max_days_past_due_before'])
        self.assertNotIn('Nothing is overdue', facts_view(f, self.TPL, self.DAY)['summaryText'])
        checks, rec = self.outcome(f)
        c = checks['nothing_overdue']
        self.assertEqual((c['passes'], c['unknown'], c['sentence']), (False, True, 'Cannot be established: 1 open invoice has no due date'))
        self.assertEqual(rec['outcome'], 'escalate')
        hard = {**self.AUTH, 'hardRules': ['nothing_overdue']}
        self.assertEqual(recommend(hard, checks_for(hard, f, 7, self.TPL))['outcome'], 'escalate')   # unknown never declines
        late = {**self.AUTH, 'maxPriorLateShare': 0.5}
        self.assertTrue({c['name']: c for c in checks_for(late, f, 7, self.TPL)}['late_history']['unknown'])
        g = assessment_facts([self.target()], [{'id': 'Q', 'amount': money(900000, 0)}], [], [], self.DAY, 'T')
        self.assertTrue({c['name']: c for c in checks_for(late, g, 7, self.TPL)}['late_history']['unknown'])   # undated payment
        ok = assessment_facts([self.target()], [], [], [], self.DAY, 'T')
        self.assertFalse({c['name']: c for c in checks_for(self.AUTH, ok, 7, self.TPL)}['nothing_overdue']['unknown'])

    def test_5_an_undated_payment_without_an_allocation_makes_the_assessment_incomplete(self):
        f = assessment_facts([self.target()], [{'id': 'Q', 'amount': money(900000, 0)}], [], [], self.DAY, 'T')
        self.assertEqual((f['incomplete'], f['unplacedPayments'], f['debt_before_m']), (True, 1, 1000000))
        self.assertIn('no received date and no recorded allocation', facts_view(f, self.TPL, self.DAY)['incompleteText'])
        checks, rec = self.outcome(f)
        self.assertFalse(checks['records_complete']['passes'])
        self.assertEqual(rec['outcome'], 'escalate')

    def test_an_allocation_to_an_invoice_not_in_the_records_cannot_be_placed(self):
        f = assessment_facts([self.target()], [payment('P', '2026-10-10', 500000, 0)], [allocation('P', 'GONE', 500000, 0)], [], self.DAY, 'T')
        self.assertEqual((f['incomplete'], f['unplacedAllocations']), (True, 1))
        withdrawn = {**self.undated(), 'status': 'withdrawn'}   # a withdrawn invoice is not live: an allocation to it is unplaced, the invoice itself is not counted
        g = assessment_facts([self.target(), withdrawn], [payment('P', '2026-10-10', 500000, 0)], [allocation('P', 'U', 500000, 0)], [], self.DAY, 'T')
        self.assertEqual((g['incomplete'], g['debt_before_m']), (True, 1000000))
        # an allocation to an invoice dated after the date is a prepayment, not unplaced
        ahead = invoice('F', '2026-11-01', '2026-12-01', 800000, 0)
        h = assessment_facts([self.target(), ahead], [payment('P', '2026-10-10', 500000, 0)], [allocation('P', 'F', 500000, 0)], [], self.DAY, 'T')
        self.assertFalse(h['incomplete'])

    def test_an_allocation_to_a_stated_amount_invoice_uses_up_the_payment_instead_of_reducing_other_invoices(self):
        stated = {'id': 'S', 'issueDate': '2026-09-01', 'originalDueDate': '2026-09-20', 'outstandingAmount': money(300000, 0, 'VND')}
        dated = invoice('D', '2026-09-02', '2026-09-30', 400000, 0)
        f = assessment_facts([stated, dated], [payment('P', '2026-10-01', 300000, 0)], [allocation('P', 'S', 300000, 0)], [], self.DAY)
        self.assertEqual(f['debt_before_m'], 300000 + 400000)   # the 300,000 paid was for S, whose stated amount is already net of it; D is untouched


class DocumentCountWording(unittest.TestCase):
    """Repair C, C3: the count of invoices says what each carries, without reading a total plus a stated amount as two kinds."""
    def test_both_only_stated_and_neither(self):
        from behaviour import _stated_clause
        self.assertEqual(_stated_clause(2, 0), ', 2 of them also stating an amount still owed')
        self.assertEqual(_stated_clause(0, 1), ', 1 more with only a stated amount still owed')
        self.assertEqual(_stated_clause(1, 1), ', 1 of them also stating an amount still owed, 1 more with only a stated amount still owed')
        self.assertEqual(_stated_clause(0, 0), '')


if __name__ == '__main__':
    unittest.main()


# Calculation details: the replay's own trail, from the loop that computes the figures (fictional data, worked out by hand)
class TrailTests(unittest.TestCase):
    TPL = {'currency': 'AUD', 'scale': 2}

    @staticmethod
    def events(trail, kind):
        return {e['id']: e for e in trail['events'] if e['kind'] == kind}

    def reconciles(self, got):
        t = got['trail']
        left = sum(x['left'] for x in t['invoices'])
        stated = sum(x['amount'] for x in t['stated'])
        undated = sum(x['open'] for x in t['undated'])
        self.assertEqual(left + t['remainingOpening'] + stated + undated, got['debt_before_m'], t)
        for p in self.events(t, 'payment').values():
            self.assertEqual(p['amount'], sum(x['amount'] for x in p['recorded']) + sum(x['amount'] for x in p['oldestFirst']) + p['toOpening'] + p['toCredit'], p)

    def test_the_trail_is_only_returned_when_asked_for(self):
        self.assertNotIn('trail', replay(*ledger(), [], [], date(2026, 4, 10)))
        self.assertIn('trail', replay(*ledger(), [], [], date(2026, 4, 10), with_trail=True))

    def test_fifo_by_hand_payment_by_payment(self):
        got = replay(*ledger(), [], [], date(2026, 4, 10), with_trail=True)
        self.reconciles(got)
        t = got['trail']
        self.assertEqual([(e['kind'], e['id']) for e in t['events']], [('invoice', 'A'), ('payment', 'P1'), ('invoice', 'B'), ('invoice', 'C'), ('payment', 'P2')])
        p1, p2 = self.events(t, 'payment')['P1'], self.events(t, 'payment')['P2']
        self.assertEqual((p1['oldestFirst'], p1['recorded'], p1['late']), ([{'invoiceId': 'A', 'amount': 60000}], [], False))
        self.assertEqual((p2['oldestFirst'], p2['late']), ([{'invoiceId': 'A', 'amount': 40000}], True))   # A and B were past due on 20 Mar
        self.assertEqual({x['id']: x['left'] for x in t['invoices']}, {'A': 0, 'B': 50000, 'C': 30000})
        self.assertEqual((t['remainingOpening'], t['creditHeld'], t['readsBefore']), (0, 0, '2026-04-10'))

    def test_recorded_allocations_and_oldest_first_are_told_apart(self):
        got = replay(*ledger(), [allocation('P2', 'C', 30000), allocation('P2', 'B', 10000)], [], date(2026, 4, 10), with_trail=True)
        self.reconciles(got)
        p2 = self.events(got['trail'], 'payment')['P2']
        self.assertEqual(sorted((x['invoiceId'], x['amount'], x['status']) for x in p2['recorded']), [('B', 10000, 'applied'), ('C', 30000, 'applied')])
        self.assertEqual((p2['oldestFirst'], p2['basis']), ([], 'recorded'))
        self.assertEqual(self.events(got['trail'], 'payment')['P1']['basis'], 'fifo')

    def test_a_payment_naming_an_invoice_issued_later_is_held_as_credit_and_applied_when_it_is_issued(self):
        # the import leaves such a payment unmatched (importer.find_invoice: issuedAfter), so it carries no recorded allocation
        b = invoice('B', '2030-02-01', '2030-02-02', 10000)
        got = replay([b], [payment('P', '2030-01-05', 10000)], [], [], date(2030, 3, 1), with_trail=True)
        self.reconciles(got)
        p, issued = self.events(got['trail'], 'payment')['P'], self.events(got['trail'], 'invoice')['B']
        self.assertEqual((p['recorded'], p['oldestFirst'], p['toOpening'], p['toCredit']), ([], [], 0, 10000))
        self.assertEqual((issued['fromCustomerCredit'], issued['fromOpeningCredit'], issued['fromRecordedAllocations'], issued['leftAfter']), (10000, 0, [], 0))
        self.assertEqual((got['debt_before_m'], got['overdue_before_m'], got['trail']['creditHeld']), (0, 0, 0))
        # with an opening debt it pays the opening balance instead, and B stays open and overdue (validate_import's hand replay, case 1)
        owing = [{'id': 'O', 'asOf': '2030-01-01', 'amount': money(10000)}]
        got = replay([b], [payment('P', '2030-01-05', 10000)], [], owing, date(2030, 3, 1), with_trail=True)
        self.reconciles(got)
        p = self.events(got['trail'], 'payment')['P']
        self.assertEqual((p['toOpening'], p['toCredit'], got['trail']['remainingOpening'], got['debt_before_m'], got['overdue_before_m']), (10000, 0, 0, 10000, 10000))

    def test_a_recorded_allocation_received_before_its_invoice_waits_and_is_applied_on_issue(self):
        invoices = [invoice('A', '2026-01-01', '2026-01-31', 10000), invoice('B', '2026-02-01', '2026-03-03', 5000)]
        got = replay(invoices, [payment('P1', '2026-01-10', 5000)], [allocation('P1', 'B', 5000)], [], date(2026, 4, 1), with_trail=True)
        self.reconciles(got)
        p, issued = self.events(got['trail'], 'payment')['P1'], self.events(got['trail'], 'invoice')['B']
        self.assertEqual(p['recorded'], [{'invoiceId': 'B', 'amount': 5000, 'status': 'waiting'}])
        self.assertEqual((issued['fromRecordedAllocations'], issued['leftAfter']), ([{'paymentId': 'P1', 'amount': 5000}], 0))

    def test_opening_credit_and_a_prepayment_are_shown_where_they_are_applied(self):
        invoices = [invoice('A', '2026-02-01', '2026-03-03', 10000), invoice('B', '2026-03-01', '2026-03-31', 4000)]
        credit = [{'id': 'O1', 'asOf': '2026-01-01', 'amount': money(-6000)}]
        got = replay(invoices, [payment('P1', '2026-01-05', 5000)], [], credit, date(2026, 6, 1), with_trail=True)
        self.reconciles(got)
        t = got['trail']
        self.assertEqual((t['opening']['creditAtStart'], t['opening']['owingAtStart'], t['opening']['balances'][0]['amount']), (6000, 0, -6000))
        a, b = self.events(t, 'invoice')['A'], self.events(t, 'invoice')['B']
        self.assertEqual((a['fromOpeningCredit'], a['fromCustomerCredit'], a['leftAfter']), (6000, 4000, 0))   # opening credit first, then the prepayment
        self.assertEqual((b['fromOpeningCredit'], b['fromCustomerCredit'], b['leftAfter']), (0, 1000, 3000))
        self.assertEqual(self.events(t, 'payment')['P1']['toCredit'], 5000)
        self.assertEqual((got['openingCreditApplied'], got['prepaymentApplied'], got['debt_before_m'], t['creditHeld']), (6000, 5000, 3000, 0))

    def test_credit_still_held_and_the_remaining_opening_balance_are_shown_at_the_end(self):
        owing = [{'id': 'O', 'asOf': '2026-01-01', 'amount': money(20000)}]
        got = replay([invoice('A', '2026-01-10', '2026-02-09', 10000)], [payment('P', '2026-01-20', 15000)], [], owing, date(2026, 4, 1), with_trail=True)
        self.reconciles(got)
        self.assertEqual((got['trail']['remainingOpening'], self.events(got['trail'], 'payment')['P']['toOpening']), (15000, 5000))
        over = replay([invoice('A', '2026-01-10', '2026-02-09', 10000)], [payment('P', '2026-01-20', 15000)], [], [], date(2026, 4, 1), with_trail=True)
        self.reconciles(over)
        self.assertEqual((over['trail']['creditHeld'], self.events(over['trail'], 'payment')['P']['toCredit']), (5000, 5000))

    def test_what_cannot_be_placed_is_listed_with_its_effect(self):
        day = date(2026, 10, 23)
        target = {**invoice('T', '2026-10-01', '2026-10-30', 100000), 'reference': 'T-1'}
        stated = {'id': 'S', 'issueDate': '2026-09-01', 'originalDueDate': '2026-09-30', 'outstandingAmount': money(20000)}
        undated = {'id': 'U', 'originalDueDate': '2026-10-01', 'total': money(30000)}
        no_due = invoice('N', '2026-09-15', None, 40000)
        unreadable = {'id': 'X', 'issueDate': '2026-09-01'}
        later = invoice('L', '2026-11-01', '2026-11-30', 50000)
        pays = [payment('P', '2026-10-05', 10000), {'id': 'Q', 'amount': money(500)}]   # Q: no received date and no allocation
        allocs = [allocation('P', 'gone', 1000)]   # to an invoice not in the records
        got = assessment_facts([target, stated, undated, no_due, unreadable, later], pays, allocs, [], day, 'T')
        t = got['trail']['current']
        self.reconciles({'trail': t, 'debt_before_m': got['debt_before_m']})
        self.assertEqual([x['id'] for x in t['stated']], ['S'])
        self.assertEqual([(x['id'], x['open']) for x in t['undated']], [('U', 30000)])
        self.assertEqual([x['id'] for x in t['openNoDueDate']], ['N'])
        self.assertEqual([x['id'] for x in t['unplacedPayments']], ['Q'])
        self.assertEqual([(x['paymentId'], x['invoiceId']) for x in t['unplacedAllocations']], [('P', 'gone')])
        self.assertEqual([x['id'] for x in t['unreadableInvoices']], ['X'])
        self.assertTrue(all(x['effect'] for k in ('stated', 'undated', 'openNoDueDate', 'unplacedPayments', 'unplacedAllocations', 'unreadableInvoices') for x in t[k]))
        self.assertEqual([(x['kind'], x['id']) for x in t['excluded']], [('invoice', 'L')])   # issued after the as-of date
        p = self.events(t, 'payment')['P']
        self.assertEqual(p['recorded'], [{'invoiceId': 'gone', 'amount': 1000, 'status': 'unplaced'}])
        self.assertEqual((got['unreadableInvoices'], got['unplacedPayments'], got['unplacedAllocations'], got['noDueDate']), (1, 1, 1, 1))   # the counts are the lists'

    def test_assessment_facts_carries_the_current_trail_and_a_summary_of_the_prior_run(self):
        a = {**invoice('A', '2026-10-01', '2026-10-30', 100000), 'reference': 'A-1'}
        today = {**invoice('B', '2026-10-23', '2026-11-22', 50000), 'reference': 'B-1'}
        got = assessment_facts([a, today], [payment('P', '2026-10-23', 20000)], [], [], date(2026, 10, 23), 'A')
        current, prior = got['trail']['current'], got['trail']['prior']
        self.assertEqual((current['readsBefore'], current['asOf']), ('2026-10-24', '2026-10-23'))   # up to and including the as-of date
        self.assertEqual([e['id'] for e in current['events']], ['A', 'B', 'P'])
        self.assertEqual(sum(x['left'] for x in current['invoices']), got['debt_before_m'])
        self.assertEqual((prior['readsBefore'], prior['prior_invoice_documents'], prior['prior_billed_m'], prior['prior_receipt_count']), ('2026-10-23', 1, 100000, 0))
        self.assertEqual((current['events'][0]['reference'], current['events'][0]['total']), ('A-1', 100000))

    def test_checks_measure_what_they_compare(self):
        f = assessment_facts(*ledger(), [], [], date(2026, 4, 10), 'B')
        auth = {'requireNothingOverdue': True, 'maxPriorLateShare': 0.25, 'staffMayApproveUpToDays': 30, 'maxOutstanding': money(70000), 'hardRules': []}
        measured = []
        checks = checks_for(auth, f, 14, self.TPL, measured)
        self.assertEqual(checks, checks_for(auth, f, 14, self.TPL))   # measuring changes no check
        by = {m['name']: m for m in measured}
        self.assertEqual(by['nothing_overdue'], {'name': 'nothing_overdue', 'actual': {'overdueOther': 30000, 'noDueOther': 0}, 'threshold': True})
        self.assertEqual(by['late_history'], {'name': 'late_history', 'actual': {'late': 1, 'of': 2}, 'threshold': 0.25})
        self.assertEqual(by['requested_days'], {'name': 'requested_days', 'actual': 14, 'threshold': 30})
        self.assertEqual(by['outstanding_amount'], {'name': 'outstanding_amount', 'actual': 80000, 'threshold': 70000})
