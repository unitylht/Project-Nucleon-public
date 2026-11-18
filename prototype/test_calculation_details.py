"""Calculation details: the basis of an assessment, made by the computation that produced it and kept with it, and the frozen basis
of a decision, which later record changes, assessments and limits never change. The tool results carry a compact summary; the full
basis is read like the case itself (GET api/requests/<id>/basis). No tool and no staff request changes the owner's limits. All data
is fictional; no real model is called."""
import json
import unittest

from behaviour import CALCULATION_VERSION, NO_LIMIT, STAFF_NO_LIMIT
from test_assessment import AssessmentCase


class CalculationDetailsTests(AssessmentCase):
    def basis(self, role='owner', version=None, rid=None, expect=200):
        status, body, _ = self.call('/api/requests/' + (rid or self.r['id']) + '/basis' + ('' if version is None else '?version=' + str(version)), role=role)
        self.assertEqual(status, expect, body)
        return body

    def stored(self):
        return self.app.get(self.r['id'])

    def pay(self, amount, date, reference, key):
        body = {'customerId': self.bayside['id'], 'receivedDate': date, 'amount': amount, 'reference': reference}
        status, result, _ = self.call('/api/records/payments', body, 'staff', key)
        self.assertEqual(status, 200, result)
        return result['record']

    def allocate(self, payment, invoice, amount, key):
        body = {'paymentId': payment['id'], 'allocations': [{'invoiceId': invoice['id'], 'amount': amount}]}
        status, result, _ = self.call('/api/records/allocations', body, 'staff', key)
        self.assertEqual(status, 200, result)

    def test_an_assessment_keeps_its_calculation_details_and_the_tool_result_carries_only_their_summary(self):
        self.set_limits()
        a = self.assess('owner')
        self.assertNotIn('basis', a)
        self.assertEqual(a['basisSummary'], {'calculationVersion': CALCULATION_VERSION, 'asOf': '2026-10-18', 'asOfText': 'Sun 18 Oct 2026', 'requestId': self.r['id'],
                                             'assessmentVersion': 1, 'records': {'invoices': 2, 'payments': 0, 'allocations': 0, 'openingBalances': 0},
                                             'missing': 0, 'excluded': 0, 'assumptions': ['original_due']})
        b = self.stored()['assessment']['basis']
        self.assertEqual((b['calculationVersion'], b['assessmentVersion'], b['asOf'], b['currency'], b['scale'], b['requestId'], b['invoiceReference']),
                         ('calc-v1', 1, '2026-10-18', 'AUD', 2, self.r['id'], 'DEMO-501'))
        self.assertEqual(b['policy']['authority']['staffMayApproveUpToDays'], 30)
        rows = {x['key']: x['text'] for x in b['policy']['rows']}
        self.assertEqual((rows['staffMayApproveUpToDays'], rows['maxOutstanding'], rows['maxPriorLateShare'], rows['requireNothingOverdue']),
                         ('30 days', 'AUD 5,000.00', 'Not set', 'Required'))
        x = {i['reference']: i for i in b['records']['invoices']}['DEMO-501']
        self.assertEqual((x['issueDate'], x['originalDueDate'], x['effectiveDueDate'], x['effectiveDueSource'], x['total'], x['totalText'], x['counted']),
                         ('2026-10-01', '2026-10-20', '2026-10-20', {'kind': 'invoice'}, 120000, 'AUD 1,200.00', 'issued'))
        self.assertEqual((x['stated']['amount'], x['stated']['asOf'], x['stated']['sourceText'], x['remainder'], x['remainderText'], x['link']),
                         (120000, '2026-10-16', 'manual entry', 120000, 'AUD 1,200.00', '#/customers/' + self.bayside['id'] + '/invoices'))
        self.assertEqual([(e['kind'], e['reference'], e['leftAfter']) for e in b['trail']], [('invoice', 'DEMO-501', 120000), ('invoice', 'DEMO-502', 120000)]
                         if b['trail'][0]['reference'] == 'DEMO-501' else [('invoice', 'DEMO-502', 120000), ('invoice', 'DEMO-501', 120000)])
        facts = {i['name']: i['value'] for i in a['facts']['items']}
        exposure, history = {r['key']: r for r in b['exposure']['rows']}, {r['key']: r for r in b['history']['rows']}
        self.assertEqual((b['exposure']['label'], b['history']['label']), ('Current exposure (up to and including today)', 'History (strictly before today)'))
        self.assertEqual((exposure['debt']['value'], exposure['overdue']['text'], exposure['remainingOpening']['text'], exposure['creditHeld']['text']),
                         (facts['debt_before_m'], 'Nothing overdue', 'AUD 0.00', 'AUD 0.00'))
        self.assertEqual((history['invoices']['value'], history['billed']['value'], history['receipts']['text'], history['lateReceipts']['text']),
                         (facts['prior_invoice_documents'], facts['prior_billed_m'], '0', 'No earlier payments'))
        self.assertEqual([(c['key'], c['result']) for c in b['checks']],
                         [('nothing_overdue', 'pass'), ('late_history', 'not set'), ('requested_days', 'pass'), ('outstanding_amount', 'pass')])
        checks = {c['key']: c for c in b['checks']}
        self.assertEqual((checks['requested_days']['actualText'], checks['requested_days']['thresholdText'], checks['outstanding_amount']['actualText'],
                          checks['outstanding_amount']['thresholdText'], checks['late_history']['thresholdText']),
                         ('21 days', 'Up to 30 days', 'AUD 2,400.00', 'Up to AUD 5,000.00', 'Not set'))
        # the measured amount in Actual, the rule in Threshold, apart
        self.assertEqual((checks['nothing_overdue']['actualText'], checks['nothing_overdue']['thresholdText']), ('AUD 0.00 overdue besides this invoice', 'None allowed'))
        self.assertEqual([c['sentence'] for c in b['checks']], [c['sentence'] for c in a['policy']['checks']])   # the checks' own sentences
        self.assertEqual(b['recommendation'], a['recommendation'])
        self.assertEqual((b['links']['case'], b['links']['customer']), ('#/case/' + self.r['id'], '#/customers/' + self.bayside['id']))
        self.assertEqual(self.assess('owner')['basisSummary']['assessmentVersion'], 2)   # a new version per assessment
        self.assertEqual((self.stored()['assessment']['basis']['assessmentVersion'], [x['version'] for x in self.stored()['earlierBases']]), (2, [1]))
        for _ in range(4):
            self.assess('owner')
        self.assertEqual([x['version'] for x in self.stored()['earlierBases']], [3, 4, 5])   # the last three before the latest (6) stay readable
        self.assertEqual(self.basis(version=3)['assessment']['version'], 3)
        self.assertEqual(self.basis(version=2, expect=404)['error'], 'NOT_FOUND')

    def test_payment_by_payment_each_amount_is_placed_and_the_parts_add_up(self):
        opening = self.call('/api/records/openingBalances', {'customerId': self.bayside['id'], 'asOf': '2026-08-31', 'amount': '100.00', 'direction': 'owed',
                                                             'sourceLabel': "Accountant's balance list"}, 'staff', 'ob-1')
        self.assertEqual(opening[0], 200, opening[1])
        old = self.add_invoice(self.bayside, 'DEMO-498', issueDate='2026-09-01', dueDate='2026-09-30', total='200.00')
        second = next(i for i in self.app.fixture()['invoices'] if i['reference'] == 'DEMO-502')
        recorded = self.pay('300.00', '2026-10-05', 'PAY-1', 'p1')
        self.allocate(recorded, second, '300.00', 'a1')
        self.pay('500.00', '2026-10-06', 'PAY-2', 'p2')
        self.pay('3000.00', '2026-10-07', 'PAY-3', 'p3')
        self.wait_status(self.r, ('awaiting_owner', 'needs_information'))
        a = self.assess('owner')
        b = self.stored()['assessment']['basis']
        pays = {p['reference']: {**p, 'trail': b['trail'][p['step']]} for p in b['records']['payments']}   # each payment row points at its step
        for p in pays.values():
            t = p['trail']
            self.assertEqual((t['kind'], t['id']), ('payment', p['id']))
            self.assertEqual(p['amount'], sum(x['amount'] for x in t['recorded']) + sum(x['amount'] for x in t['oldestFirst']) + t['toOpening'] + t['toCredit'], p)
        self.assertEqual([(x['reference'], x['amount'], x['status']) for x in pays['PAY-1']['trail']['recorded']], [('DEMO-502', 30000, 'applied')])
        self.assertEqual(pays['PAY-2']['trail']['oldestFirst'][0]['reference'], 'DEMO-498')   # oldest first: the invoice issued first
        self.assertEqual((pays['PAY-2']['trail']['oldestFirst'][0]['amount'], sum(x['amount'] for x in pays['PAY-2']['trail']['oldestFirst'])), (20000, 50000))
        self.assertEqual((pays['PAY-3']['trail']['toOpening'], pays['PAY-3']['trail']['toCredit']), (10000, 110000))   # what is left after every invoice
        [allocation] = b['records']['allocations']
        self.assertEqual((allocation['paymentReference'], allocation['reference'], allocation['amount'], allocation['origin']['kind']), ('PAY-1', 'DEMO-502', 30000, 'manual'))
        self.assertTrue(allocation['origin']['text'].startswith('Entered by staff on '), allocation['origin'])
        [ob] = b['records']['openingBalances']
        self.assertEqual((ob['asOf'], ob['amount'], ob['kind'], ob['counted']), ('2026-08-31', 10000, 'owing', True))
        exposure = {r['key']: r for r in b['exposure']['rows']}
        self.assertEqual((exposure['debt']['value'], exposure['remainingOpening']['text'], exposure['creditHeld']['text']), (0, 'AUD 0.00', 'AUD 1,100.00'))
        self.assertEqual(exposure['debt']['value'], {i['name']: i['value'] for i in a['facts']['items']}['debt_before_m'])
        self.assertEqual({x['key'] for x in b['assumptions']}, {'oldest_first', 'opening_age', 'customer_credit', 'original_due'})
        fifo = next(x for x in b['assumptions'] if x['key'] == 'oldest_first')
        self.assertTrue(fifo['text'].startswith('Applied oldest first (an assumption, not a record): '), fifo)
        self.assertEqual(old['reference'], 'DEMO-498')

    def test_what_cannot_be_established_is_unknown_never_zero_or_none(self):
        self.set_limits()
        self.add_invoice(self.bayside, 'DEMO-497', total='3000.00')   # no due date
        self.wait_status(self.r, ('awaiting_owner',))
        self.assess('owner')
        b = self.stored()['assessment']['basis']
        exposure = {r['key']: r for r in b['exposure']['rows']}
        self.assertEqual((exposure['overdue']['text'], exposure['overdue']['value'], exposure['oldestDaysPastDue']['text']), ('Unknown', None, 'Unknown'))
        self.assertEqual([(m['reference'], m['why']) for m in b['missing']], [('DEMO-497', 'No due date')])
        check = next(c for c in b['checks'] if c['key'] == 'nothing_overdue')
        self.assertEqual((check['result'], check['actualText']), ('unknown', 'Unknown'))
        self.assertEqual(next(i for i in b['records']['invoices'] if i['reference'] == 'DEMO-497')['effectiveDueText'], 'No due date')

    def test_a_decision_freezes_the_assessment_it_was_made_on(self):
        self.set_limits()
        self.assess('owner')
        before = self.stored()['assessment']
        self.assertEqual(self.decide()[0], 201)
        frozen = self.stored()['decision']['basis']
        self.assertEqual((frozen['assessmentVersion'], frozen['basis'], frozen['recommendation'], frozen['policy']), (1, before['basis'], before['recommendation'], before['policy']))
        kept = json.dumps(frozen, sort_keys=True)
        # a record changes, the owner changes the limits, and the case is assessed again
        self.add_invoice(self.bayside, 'DEMO-499', dueDate='2026-10-05', total='400.00')
        self.set_limits(staffMayApproveUpToDays=7, maxOutstanding='100.00')
        again = self.assess('owner')
        self.assertNotEqual(again['recommendation'], before['recommendation'])
        self.assertNotEqual({i['name']: i['value'] for i in again['facts']['items']}['debt_before_m'], 240000)
        self.assertEqual(again['policy']['authority']['staffMayApproveUpToDays'], 7)
        self.assertEqual(json.dumps(self.stored()['decision']['basis'], sort_keys=True), kept)   # unchanged, byte for byte
        self.assertEqual(json.dumps(self.basis()['decision']['basis'], sort_keys=True), kept)
        self.assertEqual(json.dumps(self.case('owner')['decision']['basis'], sort_keys=True), kept)
        d = self.ok('caseDetails', 'owner', requestId=self.r['id'])['case']['decision']
        self.assertEqual((d['assessmentVersion'], d['basisSummary']['assessmentVersion'], 'basis' in d), (1, 1, False))

    def test_staff_acting_within_authority_freeze_the_assessment_made_as_they_act(self):
        self.set_limits()
        self.assess()   # version 1
        self.assertEqual(self.act()[1]['ok'], True)
        r = self.stored()
        self.assertEqual((r['assessment']['version'], r['decision']['basis']['assessmentVersion'], r['decision']['basis']['basis']), (2, 2, r['assessment']['basis']))
        self.assertEqual(self.basis('staff', version=1)['assessment']['basis']['assessmentVersion'], 1)   # the earlier card's own version is still kept
        self.assertEqual(self.basis('staff', version=2)['assessment']['basis'], r['assessment']['basis'])
        self.assertEqual(self.basis('staff', version=9, expect=404)['error'], 'NOT_FOUND')
        self.assertEqual(self.basis('staff', version='x', expect=400)['error'], 'INVALID_INPUT')
        self.assertEqual(self.basis('staff')['decision']['basis']['basis'], r['decision']['basis']['basis'])

    def test_the_details_are_read_like_the_case_itself_with_the_same_numbers_for_both_roles(self):
        a = self.assess('owner')   # no limits: the owner's no-limit sentence
        owner, staff = self.basis('owner'), self.basis('staff')
        self.assertEqual(owner['assessment']['version'], a['version'])
        pick = lambda b: [(c['key'], c['actual'], c['threshold'], c['result']) for c in b['checks']] + [(r['key'], r['value']) for r in b['exposure']['rows'] + b['history']['rows']]
        self.assertEqual(pick(owner['assessment']['basis']), pick(staff['assessment']['basis']))
        self.assertIn(NO_LIMIT, [c['sentence'] for c in owner['assessment']['basis']['checks']])
        self.assertIn(STAFF_NO_LIMIT, [c['sentence'] for c in staff['assessment']['basis']['checks']])
        self.assertNotIn(NO_LIMIT, json.dumps(staff))
        self.assertEqual(self.case('staff')['assessment']['basis']['checks'], staff['assessment']['basis']['checks'])   # the case view carries it in full
        self.assertNotIn('earlierBases', self.case('owner'))
        status, body, _ = self.call('/api/requests/' + self.r['id'] + '/basis')   # no session
        self.assertEqual(status, 401, body)
        for role in ('owner', 'staff'):
            case = self.ok('caseDetails', role, requestId=self.r['id'])['case']
            self.assertEqual(('basis' in case['assessment'], case['assessment']['basisSummary']['assessmentVersion']), (False, a['version']), role)

    def test_no_tool_and_no_staff_request_changes_the_owner_s_limits(self):
        self.set_limits()
        before = self.authority(method='GET')[1]
        status, body = self.authority('staff', staffMayApproveUpToDays=365, maxOutstanding='999999.00', hardRules=[])
        self.assertEqual((status, body['error']), (403, 'FORBIDDEN'))
        self.assertEqual(self.authority(method='GET')[1], before)   # nothing changed
        for role in ('owner', 'staff'):
            tools = self.call('/api/tools', role=role)[1]['tools']
            for t in tools:
                self.assertFalse({'staffMayApproveUpToDays', 'maxOutstanding', 'hardRules', 'maxPriorLateShare', 'requireNothingOverdue', 'authority'}
                                 & set(json.dumps(t['parameters']).replace('"', ' ').split()), t['name'])
            for name in ('setAuthority', 'saveAuthority', 'updateAuthority', 'changeLimits'):
                self.assertEqual(self.tool(name, role, 'k-' + name + role)[0], 404, name)
        self.assertEqual(self.authority(method='GET')[1], before)


if __name__ == '__main__':
    unittest.main()
