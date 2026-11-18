"""What a customer owes, said with the right figure under the right label. The expected numbers were worked out by hand before any
code (balance-expectations.md of the replay round): two synthetic customers on Sat 24 Oct 2026, VND with no decimals, and one whose opening
balance is fully paid by earlier payments (like the imported Customer 0012). The recorded net (invoices less payments) leaves out the
opening balance, so it is never the figure owed. All data is fictional."""
import unittest
from datetime import date

from behaviour import assessment_facts, facts_view, replay
from server import balance_line
from test_openings import OpeningCase

BUSINESS_DATE = date(2026, 10, 24)


class BalanceCase(OpeningCase):
    def ready(self):
        if self.apps:   # one workspace for as many synthetic customers as a test builds
            return
        self.start(today=lambda: BUSINESS_DATE)
        self.practice_ready(currency='VND', scale=0, timezone='Asia/Ho_Chi_Minh')

    def customer(self, name, opening=None, direction='owed'):
        c = self.add_customer(name)
        if opening:
            self.opening(c, amount=opening, as_of='2026-06-30', direction=direction)
        return c

    def inv(self, c, ref, issued, total, due=None):
        return self.invoice(ref, total=total, customer=c, issueDate=issued, **({'dueDate': due} if due else {}))

    def overview(self, c, key='ov'):
        status, body, _ = self.call('/api/tools/customerOverview', {'args': {'customerId': c['id']}}, 'staff', key + c['id'])
        self.assertEqual(status, 200, body)
        return body['result']

    def owed(self, c):
        return self.positions()['customers'][c['id']]['owed']

    def synth_balance(self):
        """QA Balance Synth: 50m owed at 30 Jun; INV-A..E; P1 and P3 allocated by record, P2 left to oldest-first."""
        self.ready()
        c = self.customer('QA Balance Synth', '50000000')
        a = self.inv(c, 'INV-A', '2026-07-01', '30000000', '2026-07-31')
        self.inv(c, 'INV-B', '2026-08-01', '40000000', '2026-08-31')
        cc = self.inv(c, 'INV-C', '2026-09-01', '25000000', '2026-10-01')
        self.inv(c, 'INV-D', '2026-10-01', '20000000', '2026-10-31')
        self.inv(c, 'INV-E', '2026-10-10', '5000000')
        self.allocate(self.pay('30000000', date='2026-07-15', reference='P1', customer=c), (a, '30000000'))
        self.pay('60000000', date='2026-08-20', reference='P2', customer=c)
        self.allocate(self.pay('10000000', date='2026-09-15', reference='P3', customer=c), (cc, '10000000'))
        return c

    def synth_credit(self):
        """QA Credit Synth: a 10m credit at 30 Jun, INV-F 8m, an unallocated 15m payment, INV-G 12m: 5m credit held, nothing owed."""
        self.ready()
        c = self.customer('QA Credit Synth', '10000000', 'credit')
        self.inv(c, 'INV-F', '2026-07-01', '8000000', '2026-07-31')
        self.pay('15000000', date='2026-08-15', reference='P4', customer=c)
        self.inv(c, 'INV-G', '2026-09-01', '12000000', '2026-09-30')
        return c

    def synth_paid_opening(self):
        """An opening balance of 5m fully paid by one payment beyond the invoices then open (the shape of Customer 0012)."""
        self.ready()
        c = self.customer('QA Paid Opening Synth', '5000000')
        self.inv(c, 'INV-H', '2026-07-01', '8000000', '2026-07-31')
        self.inv(c, 'INV-I', '2026-08-01', '6000000', '2026-08-31')
        self.pay('19000000', date='2026-09-01', reference='P5', customer=c)
        self.inv(c, 'INV-J', '2026-10-01', '7000000', '2026-10-15')
        self.inv(c, 'INV-K', '2026-10-10', '3000000', '2026-10-31')
        return c


def texts(result, *keys):
    return [result[k]['amount'] for k in keys]


def by_reference(result):
    return {i['reference']: i for i in result['invoices']}


class BalanceSynthTests(BalanceCase):
    def test_owed_now_and_its_parts_are_the_hand_computed_figures(self):
        c = self.synth_balance()
        o = self.overview(c)
        self.assertEqual(texts(o, 'owedNow', 'owedOverdue', 'owedNotYetDue', 'owedNoDueDate', 'owedFromOpening', 'openingBalance', 'creditHeld'),
                         ['VND 70,000,000', 'VND 15,000,000', 'VND 20,000,000', 'VND 5,000,000', 'VND 30,000,000', 'VND 50,000,000', 'VND 0'])
        for key in ('owedNow', 'owedOverdue', 'owedNotYetDue', 'owedNoDueDate', 'owedFromOpening', 'creditHeld'):
            self.assertEqual(o[key]['mark'], 'worked out', key)
            self.assertIn('(worked out', o[key]['amountText'], key)
        self.assertEqual(o['openingBalance']['mark'], 'as recorded')
        self.assertEqual(o['recordedNet']['amount'], 'VND 20,000,000')
        self.assertIn('this leaves out the opening balance', o['recordedNet']['amountText'])
        self.assertTrue(o['recordedNet']['amountText'].startswith('VND 20,000,000 (as recorded'), o['recordedNet']['amountText'])

    def test_each_open_invoice_shows_the_worked_out_remainder_where_none_is_recorded(self):
        c = self.synth_balance()
        rows = by_reference(self.overview(c))
        self.assertEqual(sorted(rows), ['INV-C', 'INV-D', 'INV-E'])   # INV-A (allocated in full) and INV-B (paid oldest-first) have nothing left: not open
        for ref, left in (('INV-C', 'VND 15,000,000'), ('INV-D', 'VND 20,000,000'), ('INV-E', 'VND 5,000,000')):
            self.assertIn(left, rows[ref]['stillOwedText'], ref)
            self.assertNotIn('not recorded', rows[ref]['stillOwedText'], ref)
        for ref in ('INV-D', 'INV-E'):   # no amount still owed recorded and no allocation: the replay's own remainder
            self.assertIn('worked out', rows[ref]['stillOwedText'], ref)
            self.assertIn('worked out', rows[ref]['amountText'], ref)

    def test_open_and_overdue_counts_follow_the_replay_for_the_synthetic_customer(self):
        c = self.synth_balance()
        o = self.overview(c)
        self.assertEqual((o['openCount'], o['overdueCount'], o['knownAmountCount']), (3, 1, 3))
        self.assertEqual(o['overdueText'], '3 open invoices, 1 overdue; overdue not known for 1 invoice with no due date')
        self.assertEqual({i['reference']: i['daysOverdue'] for i in o['invoices']}, {'INV-C': 23, 'INV-D': 0, 'INV-E': None})   # C is 23 days past 1 Oct
        tool = lambda **args: self.call('/api/tools/invoices', {'args': {'customerId': c['id'], **args}}, 'staff', 'inv' + str(sorted(args.items())))[1]['result']
        opened, late = tool(which='open'), tool(which='overdue')
        self.assertEqual([i['reference'] for i in opened['invoices']], ['INV-C', 'INV-D', 'INV-E'])
        self.assertNotIn('unknownCount', opened)
        self.assertEqual([i['reference'] for i in late['invoices']], ['INV-C'])
        self.assertEqual((late['unknownCount'], late['summaryText']), (1, 'Overdue not known for 1 open invoice: no due date is recorded.'))
        self.assertEqual([i['reference'] for i in tool(which='all')['invoices']], ['INV-A', 'INV-B', 'INV-C', 'INV-D', 'INV-E'])

    def test_an_imported_shaped_customer_has_two_open_invoices_both_overdue(self):
        """The shape of Customer 0012: many settled invoices, an opening balance paid off, two invoices still open and past due."""
        self.ready()
        c = self.customer('QA Imported Synth', '5000000')
        for n in range(1, 9):
            self.inv(c, 'H%d' % n, '2026-07-%02d' % n, '1000000', '2026-08-%02d' % n)
        self.pay('13000000', date='2026-09-01', reference='P6', customer=c)   # 8m of invoices and the 5m opening balance
        self.inv(c, 'L1', '2026-09-20', '7000000', '2026-10-09')
        self.inv(c, 'L2', '2026-10-01', '3000000', '2026-10-16')
        o = self.overview(c)
        self.assertEqual((o['owedNow']['amount'], o['owedOverdue']['amount'], o['owedFromOpening']['amount']), ('VND 10,000,000', 'VND 10,000,000', 'VND 0'))
        self.assertEqual((o['openCount'], o['overdueCount'], o['overdueText']), (2, 2, '2 open invoices, 2 overdue'))
        self.assertEqual(sorted(i['reference'] for i in o['invoices']), ['L1', 'L2'])

    def test_an_approved_later_due_date_is_named_beside_the_overdue_part_and_on_the_row(self):
        self.ready()
        c = self.customer('QA Approved Synth')
        self.inv(c, 'DEMO-702', '2026-09-01', '12000000', '2026-10-01')
        r = self.create('Could we pay invoice DEMO-702 on 2026-11-13 instead?')
        case = self.wait_status(r, ('awaiting_owner',))
        # the case's invoice says what the replay leaves on it today, worked out; its stored snapshot is untouched
        invoice = self.call('/api/tools/caseDetails', {'args': {'requestId': r['id']}}, 'staff', 'cd1')[1]['result']['case']['invoice']
        self.assertEqual((invoice['mark'], invoice['amountText']), ('workedOut', 'VND 12,000,000 (worked out)'))
        self.assertIn('worked out', invoice['stillOwedText'])
        self.assertIsNone(case['analysis']['snapshot']['facts'].get('invoiceOutstanding'))
        status, decided, _ = self.decide(case, approved='2026-11-13')
        self.assertEqual(status, 201, decided)
        o = self.overview(c)
        self.assertEqual((o['openCount'], o['overdueCount']), (1, 1))   # still overdue by the original due date, the replay's rule
        self.assertIn('Owed now VND 12,000,000 (worked out; invoices not confirmed complete; payments not confirmed complete), all of it overdue by the original due date (DEMO-702: later date approved, Fri 13 Nov 2026).', o['balanceLine'])
        [row] = o['invoices']
        self.assertEqual((row['dueDate'], row['daysOverdue'], row['overdueBasisText']),
                         ('2026-11-13', 23, 'Overdue judged by the original due date Thu 1 Oct 2026; later date approved: Fri 13 Nov 2026.'))
        self.assertEqual(self.call('/api/tools/caseDetails', {'args': {'requestId': r['id']}}, 'staff', 'cd2')[1]['result']['case']['invoice']['mark'], 'workedOut')
        # the model's short row of the invoices list keeps the date in force and why it is still overdue (Hoang's NTK round, 9 Nov 2026)
        listed = self.call('/api/tools/invoices', {'args': {'customerId': c['id'], 'which': 'all'}}, 'staff', 'inv-moved')[1]['result']['forModel']['invoices'][0]
        self.assertEqual((listed['dueNowText'], listed['daysOverdue']), ('Fri 13 Nov 2026', 23))
        self.assertTrue(listed['dueNowSource'].startswith('approved to Fri 13 Nov 2026'))
        self.assertIn('original due date', listed['overdueBasisText'])
        self.assertEqual(listed['overdueText'], '23 days past the original due date (Thu 1 Oct 2026). Extended to Fri 13 Nov 2026, which has not passed yet.')

    def test_the_balance_line_leads_with_owed_now_then_its_parts_in_order_then_the_recorded_net_under_its_own_label(self):
        c = self.synth_balance()
        line = self.overview(c)['balanceLine']
        self.assertTrue(line.startswith('Owed now VND 70,000,000 (worked out; invoices not confirmed complete; payments not confirmed complete)'), line)
        order = ['VND 15,000,000 (worked out) overdue', 'VND 20,000,000 (worked out) not yet due', 'VND 5,000,000 (worked out) with no due date',
                 'VND 30,000,000 (worked out) left of the opening balance of VND 50,000,000 (as recorded)', 'Recorded invoices less recorded payments: VND 20,000,000',
                 'this leaves out the opening balance', 'Still owed per invoice']   # how complete the records are is said beside owed now (the start)
        at = [line.find(x) for x in order]
        self.assertNotIn(-1, at, (order, line))
        self.assertEqual(at, sorted(at), line)
        self.assertNotIn('Customer balance', line)
        self.assertEqual(line.count('VND 20,000,000'), 3)   # not yet due, the recorded net, INV-D's remainder
        self.assertEqual(line.find('VND 20,000,000'), line.find('VND 20,000,000 (worked out) not yet due'))   # first said as a part of owed now, never as the balance
        self.assertIn('INV-C VND 15,000,000', line)
        self.assertNotIn('not recorded', line)
        self.assertNotIn('credit', line.lower())   # none held

    def test_it_equals_the_assessment_of_the_same_customer_and_date(self):
        c = self.synth_balance()
        o, doc = self.overview(c), self.app.fixture()
        mine = [x for x in doc['invoices'] if x['customerId'] == c['id']]
        paid = {p['id'] for p in doc['payments'] if p['customerId'] == c['id']}
        f = assessment_facts(mine, [p for p in doc['payments'] if p['id'] in paid], doc['allocations'], [x for x in doc['openingBalances'] if x['customerId'] == c['id']], BUSINESS_DATE)
        trail = f['trail']['current']
        self.assertEqual((f['debt_before_m'], f['overdue_before_m'], f['noDueAmount'], f['openingOwing'], f['openingBalance'], trail['creditHeld']),
                         (70000000, 15000000, 5000000, 30000000, 50000000, 0))
        self.assertEqual({i['reference']: i['left'] for i in trail['invoices']},
                         {'INV-A': 0, 'INV-B': 0, 'INV-C': 15000000, 'INV-D': 20000000, 'INV-E': 5000000})
        self.assertEqual((f['reconciles'], f['allocationBasis'], f['lateReceipts']), (True, 'mixed', 0))
        self.assertEqual(f['debt_before_m'] - f['overdue_before_m'] - f['noDueAmount'] - f['openingOwing'], 20000000)   # not yet due
        self.assertEqual(o['owedNow']['amount'], 'VND 70,000,000')
        self.assertEqual(o['owedOverdue']['amount'], 'VND 15,000,000')
        self.assertEqual(self.owed(c)['owedNow']['minorUnits'], '70000000')

    def test_it_equals_the_assessment_of_a_request_on_one_of_their_invoices(self):
        self.ready()
        c = self.customer('QA Asked Synth', '20000000')   # 25m owed: 5m overdue on DEMO-701 (the 25m payment goes to it oldest-first) and the 20m opening balance
        self.inv(c, 'DEMO-701', '2026-09-01', '30000000', '2026-10-01')
        self.pay('25000000', date='2026-09-20', reference='P7', customer=c)
        r = self.create('Could we pay invoice DEMO-701 on 2026-11-30 instead?')
        self.wait_status(r, ('awaiting_owner', 'needs_information'))
        status, body, _ = self.call('/api/tools/assessRequest', {'args': {'requestId': r['id']}}, 'owner', 'assess-synth')
        self.assertEqual((status, body.get('ok')), (200, True), body)
        said = {x['name']: x for x in body['result']['facts']['items']}
        o = self.overview(c)
        self.assertEqual((said['debt_before_m']['value'], said['overdue_before_m']['value']), (25000000, 5000000))
        self.assertEqual((o['owedNow']['amount'], o['owedOverdue']['amount'], o['owedFromOpening']['amount']), ('VND 25,000,000', 'VND 5,000,000', 'VND 20,000,000'))
        self.assertEqual(said['debt_before_m']['text'], 'VND 25,000,000 is owed on the recorded invoices after the recorded payments. '
                                                        'It includes VND 20,000,000 from an opening balance of unknown age.')

    def test_not_yet_due_is_never_negative_and_the_parts_add_up(self):
        for make in (self.synth_balance, self.synth_credit, self.synth_paid_opening):
            c = make()
            o = self.owed(c)
            part = lambda k: int(o[k]['minorUnits'])
            self.assertGreaterEqual(part('notYetDue'), 0)
            self.assertEqual(part('overdue') + part('notYetDue') + part('noDueDate') + part('openingOwing'), part('owedNow'))

    def test_the_positions_the_customer_page_reads_carry_the_same_figures(self):
        c = self.synth_balance()
        p = self.owed(c)
        self.assertEqual([p[k]['minorUnits'] for k in ('owedNow', 'overdue', 'notYetDue', 'noDueDate', 'openingOwing', 'openingBalance', 'creditHeld')],
                         ['70000000', '15000000', '20000000', '5000000', '30000000', '50000000', '0'])
        self.assertEqual({k: v['minorUnits'] for k, v in p['left'].items() if v['minorUnits'] != '0'},
                         {i['id']: v for i in self.app.fixture()['invoices'] for r, v in (('INV-C', '15000000'), ('INV-D', '20000000'), ('INV-E', '5000000')) if i['reference'] == r})
        self.assertFalse(p['openingPaid'])


class CreditSynthTests(BalanceCase):
    def test_a_credit_customer_owes_nothing_and_the_positive_recorded_net_is_not_presented_as_owed(self):
        c = self.synth_credit()
        o = self.overview(c)
        self.assertEqual(texts(o, 'owedNow', 'owedOverdue', 'creditHeld', 'recordedNet'), ['VND 0', 'VND 0', 'VND 5,000,000', 'VND 5,000,000'])
        line = o['balanceLine']
        self.assertTrue(line.startswith('Owed now VND 0 (worked out; invoices not confirmed complete; payments not confirmed complete)'), line)
        self.assertIn('Customer credit held VND 5,000,000 (worked out)', line)
        self.assertIn('Recorded invoices less recorded payments: VND 5,000,000 (as recorded; this leaves out the opening balance)', line)
        self.assertNotIn('Owed now VND 5,000,000', line)
        self.assertNotIn('overdue', line)
        self.assertLess(line.find('Customer credit held'), line.find('Recorded invoices less'))
        doc = self.app.fixture()
        mine = lambda kind: [x for x in doc[kind] if x['customerId'] == c['id']]
        f = replay(mine('invoices'), mine('payments'), [], mine('openingBalances'), BUSINESS_DATE, with_trail=True, horizon=date(2026, 10, 25))
        self.assertEqual((f['debt_before_m'], f['trail']['creditHeld'], f['reconciles'], f['difference']), (0, 5000000, False, 5000000))


class PaidOpeningTests(BalanceCase):
    def test_an_opening_balance_paid_by_earlier_payments_is_said_as_paid_and_nothing_is_of_unknown_age(self):
        c = self.synth_paid_opening()
        o = self.overview(c)
        self.assertEqual(texts(o, 'owedNow', 'owedOverdue', 'owedNotYetDue', 'owedFromOpening', 'creditHeld', 'recordedNet'),
                         ['VND 10,000,000', 'VND 7,000,000', 'VND 3,000,000', 'VND 0', 'VND 0', 'VND 5,000,000'])
        line = o['balanceLine']
        self.assertIn('The opening balance of VND 5,000,000 (as recorded) was paid by earlier payments, oldest first.', line)
        self.assertTrue(line.startswith('Owed now VND 10,000,000 (worked out; invoices not confirmed complete; payments not confirmed complete)'), line)
        self.assertNotIn('unknown age', line)
        self.assertNotIn('no due date', line)
        self.assertIn('INV-J VND 7,000,000 (worked out)', line)
        self.assertIn('INV-K VND 3,000,000 (worked out)', line)
        self.assertNotIn('INV-H', line)   # nothing left on a paid invoice: left out, not listed as zero
        self.assertTrue(self.owed(c)['openingPaid'])
        left = {i['reference']: i['stillOwedText'] for i in o['invoices']}
        self.assertIn('VND 7,000,000', left['INV-J'])
        self.assertEqual(self.minor_owed(o), 10000000)

    def minor_owed(self, o):
        return int(o['owedNow']['amount'].replace('VND ', '').replace(',', ''))

    def test_the_assessment_sentence_says_the_same_in_the_same_words(self):
        c = self.synth_paid_opening()
        doc = self.app.fixture()
        mine = lambda kind: [x for x in doc[kind] if x['customerId'] == c['id']]
        f = assessment_facts(mine('invoices'), mine('payments'), doc.get('allocations', []), mine('openingBalances'), BUSINESS_DATE)
        said = {x['name']: x['text'] for x in facts_view(f, {'currency': 'VND', 'scale': 0}, BUSINESS_DATE)['items']}
        self.assertEqual(said['debt_before_m'], 'VND 10,000,000 is owed on the recorded invoices after the recorded payments. '
                                                'The opening balance of VND 5,000,000 was paid by earlier payments, oldest first.')


class DebtSentenceTests(unittest.TestCase):
    TEMPLATE = {'currency': 'AUD', 'scale': 2}

    def facts(self, invoices, payments, opening):
        money = lambda n: {'minorUnits': str(n), 'currency': 'AUD', 'scale': 2}
        invs = [{'id': i, 'issueDate': d, 'originalDueDate': due, 'total': money(t)} for i, d, due, t in invoices]
        pays = [{'id': i, 'receivedDate': d, 'amount': money(a)} for i, d, a in payments]
        ob = [{'id': 'O', 'asOf': '2026-01-01', 'amount': money(opening)}] if opening else []
        f = assessment_facts(invs, pays, [], ob, date(2026, 4, 1))
        return {x['name']: x['text'] for x in facts_view(f, self.TEMPLATE, date(2026, 4, 1))['items']}['debt_before_m']

    def test_the_sentence_is_accurate_for_each_mix_of_invoices_and_opening_balance(self):
        inv = [('A', '2026-01-10', '2026-02-09', 10000)]
        self.assertEqual(self.facts(inv, [('P', '2026-01-20', 5000)], 0), 'AUD 50.00 is owed on the recorded invoices after the recorded payments.')
        self.assertEqual(self.facts(inv, [('P', '2026-01-20', 5000)], 20000), 'AUD 250.00 is owed on the recorded invoices after the recorded payments. '
                                                                               'It includes AUD 200.00 from an opening balance of unknown age.')
        # the invoice is paid and the payment beyond it reduced the opening balance: all that is owed is the opening balance, not "on the invoices"
        self.assertEqual(self.facts(inv, [('P', '2026-01-20', 15000)], 20000), 'AUD 150.00 is owed, all of it from an opening balance of unknown age '
                                                                                '(AUD 150.00 of the opening balance of AUD 200.00 remains after payments); the recorded invoices are paid.')
        self.assertEqual(self.facts(inv, [('P', '2026-01-20', 10000)], 20000), 'AUD 200.00 is owed, all of it from an opening balance of unknown age; '
                                                                                'the recorded invoices are paid.')
        self.assertEqual(self.facts(inv, [('P', '2026-01-20', 30000)], 20000), 'AUD 0.00 is owed on the recorded invoices after the recorded payments. '
                                                                                'The opening balance of AUD 200.00 was paid by earlier payments, oldest first.')


class BalanceLineTests(unittest.TestCase):
    def test_a_customer_with_no_invoices_and_nothing_owed_has_no_amount_to_quote(self):
        self.assertEqual(balance_line('Riverside Bakery', None, {}, [], 0), 'No invoices are recorded for Riverside Bakery.')


if __name__ == '__main__':
    unittest.main()
