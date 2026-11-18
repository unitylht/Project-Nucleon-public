"""The decision loop's backend (slice S1a): the append-only case timeline (case_events), stored outcome observations, tacit consent (D8) and the Owner's
view timestamps. Deterministic, on the fictional delegation demonstration (delegation_demo.py) as of 2026-10-24; no model is ever asked. Every figure is a
fictional POC value. The pure outcome rules are in outcomes.py and tested here without a server; the rest through the real HTTP routes."""
import json
import unittest
from datetime import date, datetime, timedelta, timezone

import delegation
import delegation_demo
import outcomes
import server
from records import RecordsError
from test_delegation import AS_OF, DelegationCase, MEMORY, SETTINGS

LAKESIDE_ITEMS = [{'kind': 'deposit', 'basis': 'bank', 'amount': '150.00', 'receivedDate': '2026-10-23', 'reference': 'DEP-LK-01'},
                  {'kind': 'business_identity', 'basis': 'document', 'registration': 'Registration 111 (fictional)', 'tradingName': 'Lakeside Kiosk (fictional)'}]


class LoopCase(DelegationCase):
    """The delegation demonstration with helpers for the case timeline and the new routes."""

    def kinds(self, case_id):
        return [k for k, in self.row('SELECT kind FROM case_events WHERE case_id=? ORDER BY seq', case_id)]

    def pairs(self, case_id):
        return [(k, a) for k, a in self.row('SELECT kind, actor FROM case_events WHERE case_id=? ORDER BY seq', case_id)]

    def total_events(self):
        return self.row('SELECT COUNT(*) FROM case_events')[0][0]

    def timeline(self, case_id, role='owner'):
        status, body, _ = self.call('/api/decision-cases/' + case_id + '/events', None, role)
        self.assertEqual(status, 200, body)
        return body

    def approved_extension(self, who='bayview', reference='DEMO-301', date_='2026-11-10'):
        return self.resolved(**self.extension(who, reference, date=date_))

    def assess(self, **args):
        return self.tool('assessDecision', **{k: v for k, v in args.items() if k not in ('recommendation', 'reasoning')})['result']

    def agree(self, case_id, verdict='agree', **more):
        status, body = self.feedback(case_id, {'verdict': verdict, 'reason': 'Fictional reason.', **more})
        self.assertEqual(status, 200, body)
        return body


# ---------------------------------------------------------------- 1. the case timeline

class CaseEventTests(LoopCase):
    def test_the_table_is_additive_indexed_and_a_data_table_a_reset_clears(self):
        self.assertIn('case_events', server.DATA_TABLES)
        columns = [c[1] for c in self.row('PRAGMA table_info(case_events)')]
        self.assertEqual(columns, ['seq', 'case_id', 'kind', 'at', 'actor', 'policy_version', 'data'])
        self.assertIn('case_events_by_case', [i[1] for i in self.row('PRAGMA index_list(case_events)')])
        with self.assertRaises(ValueError):
            server.case_event(self.app.db, 'case_x', 'invented', 'system', 1)
        with self.assertRaises(ValueError):
            server.case_event(self.app.db, 'case_x', 'created', 'somebody', 1)

    def test_an_agent_approval_is_created_evaluated_decided_once_each(self):
        out = self.approved_extension()
        self.assertEqual(self.pairs(out['caseId']), [('created', 'agent'), ('evaluated', 'system'), ('decided', 'agent')])
        body = self.timeline(out['caseId'])
        self.assertEqual(body['caseId'], out['caseId'])
        self.assertEqual([e['seq'] for e in body['events']], sorted(e['seq'] for e in body['events']))
        decided = body['events'][2]
        self.assertEqual((decided['policyVersion'], decided['data']['outcome'], decided['data']['by']), (1, 'approve', 'agent'))
        self.assertEqual(body['events'][1]['data']['handling'], 'autonomous_approve')
        self.assertTrue(all(e['at'] for e in body['events']))

    def test_a_replayed_resolve_writes_no_event(self):
        out = self.approved_extension()
        before = self.total_events()
        again = self.resolved(key='another-key', **self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        self.assertTrue(again['replayed'])
        self.assertEqual(again['caseId'], out['caseId'])
        self.assertEqual(self.total_events(), before)
        waiting = self.resolved(**self.trial('lakeside', '600.00'))
        before = self.total_events()
        self.assertTrue(self.resolved(key='k2', **self.trial('lakeside', '600.00'))['replayed'])
        self.assertEqual(self.total_events(), before)
        self.assertEqual(self.kinds(waiting['caseId']), ['created', 'evaluated', 'evidence_requested'])

    def test_evidence_is_requested_then_submitted_then_the_case_is_evaluated_again_and_decided(self):
        out = self.resolved(**self.trial('lakeside', '600.00'))
        self.assertEqual(self.pairs(out['caseId']), [('created', 'agent'), ('evaluated', 'system'), ('evidence_requested', 'system')])
        self.assertEqual(self.timeline(out['caseId'])['events'][2]['data']['needs'], ['deposit', 'business_identity'])
        status, body = self.submit(out['actionId'], LAKESIDE_ITEMS)
        self.assertEqual(status, 200, body)
        self.assertEqual(self.kinds(out['caseId'])[3:], ['evidence_submitted', 'evaluated', 'decided'])
        submitted = self.timeline(out['caseId'])['events'][3]
        self.assertEqual((submitted['actor'], submitted['data']['kinds']), ('staff', ['deposit', 'business_identity']))
        before = self.total_events()
        replay = self.submit(out['actionId'], LAKESIDE_ITEMS, key='ev-2')[1]
        self.assertTrue(replay['replayed'])
        self.assertEqual(self.total_events(), before)

    def test_a_still_missing_need_is_evaluated_and_asked_again(self):
        out = self.resolved(**self.trial('lakeside', '600.00'))
        small = [{**LAKESIDE_ITEMS[0], 'amount': '100.00'}, LAKESIDE_ITEMS[1]]
        status, body = self.submit(out['actionId'], small)
        self.assertEqual(status, 200, body)
        self.assertEqual(self.kinds(out['caseId'])[3:], ['evidence_submitted', 'evaluated', 'evidence_requested'])

    def test_escalation_and_hold_each_write_their_event(self):
        big = self.resolved(**self.trial('harbourline', '5000.00'))
        self.assertEqual(self.pairs(big['caseId']), [('created', 'agent'), ('evaluated', 'system'), ('escalated', 'system')])
        ext = self.resolved(**self.extension('cityside', 'DEMO-410', days=14))
        self.assertEqual(self.kinds(ext['caseId']), ['created', 'evaluated', 'escalated'])
        held = self.resolved(**self.trial('lakeside', '600.00'))
        self.add_invoice(self.cust['lakeside'], 'DEMO-701', '90.00', '2026-11-03', issue='2026-10-20')
        items = [*LAKESIDE_ITEMS, {'kind': 'no_prior_account', 'confirmed': True}]
        status, body = self.submit(held['actionId'], items)
        self.assertEqual(status, 200, body)
        self.assertEqual(self.kinds(held['caseId'])[3:], ['evidence_submitted', 'evaluated', 'held'])

    def test_the_owner_deciding_a_trial_credit_and_an_extension_each_write_one_decided_event(self):
        trial = self.resolved(**self.trial('harbourline', '5000.00'))
        status, body = self.send('POST', '/api/decision-cases/' + trial['caseId'] + '/decide', {'outcome': 'decline', 'reason': 'Too large.', 'version': trial['version']})
        self.assertEqual(status, 200, body)
        self.assertEqual(self.pairs(trial['caseId'])[-1], ('decided', 'owner'))
        last = self.timeline(trial['caseId'])['events'][-1]
        self.assertEqual((last['data']['outcome'], last['data']['by'], last['data']['reason'], last['data']['agreement']), ('decline', 'owner', 'Too large.', False))
        before = self.total_events()
        self.assertTrue(self.send('POST', '/api/decision-cases/' + trial['caseId'] + '/decide', {'outcome': 'decline', 'reason': 'again', 'version': 1})[1]['replayed'])
        self.assertEqual(self.total_events(), before)
        ext = self.resolved(**self.extension('cityside', 'DEMO-410', days=14))
        r = self.request_of(ext['requestId'])
        status, body, _ = self.decide(r, 'approve', '2026-11-11', key='owner-decides')
        self.assertEqual(status, 201, body)
        self.assertEqual(self.pairs(ext['caseId']), [('created', 'agent'), ('evaluated', 'system'), ('escalated', 'system'), ('decided', 'owner')])
        decided = self.timeline(ext['caseId'])['events'][-1]['data']
        self.assertEqual((decided['outcome'], decided['by'], decided['requestId']), ('approve', 'owner', r['id']))

    def test_an_owner_exception_on_a_held_case_is_decided_by_owner_exception(self):
        held = self.resolved(**self.trial('lakeside', '600.00'))
        self.add_invoice(self.cust['lakeside'], 'DEMO-701', '90.00', '2026-11-03', issue='2026-10-20')
        self.submit(held['actionId'], [*LAKESIDE_ITEMS, {'kind': 'no_prior_account', 'confirmed': True}])
        version = self.case(held['caseId'])['version']
        status, body = self.send('POST', '/api/decision-cases/' + held['caseId'] + '/decide', {'outcome': 'approve', 'reason': 'I know them.', 'version': version})
        self.assertEqual(status, 200, body)
        last = self.timeline(held['caseId'])['events'][-1]
        self.assertEqual((last['kind'], last['actor'], last['data']['by']), ('decided', 'owner', 'owner_exception'))

    def test_feedback_writes_one_event_and_an_override_a_second(self):
        out = self.approved_extension()
        self.agree(out['caseId'])
        self.assertEqual(self.pairs(out['caseId'])[3:], [('feedback', 'owner')])
        self.assertEqual(self.timeline(out['caseId'])['events'][3]['data'], {'verdict': 'agree', 'override': False, 'reason': 'Fictional reason.'})
        self.agree(out['caseId'], 'disagree', override=True)
        self.assertEqual(self.kinds(out['caseId'])[4:], ['feedback', 'override'])
        override = self.timeline(out['caseId'])['events'][-1]
        self.assertEqual((override['actor'], override['data']['outcome'], override['data']['overridesPolicyVersion']), ('owner', 'decline', 1))
        # a refused feedback (stale version, bad verdict) and a replayed one (same Idempotency-Key) write nothing
        before = self.total_events()
        self.assertEqual(self.feedback(out['caseId'], {'verdict': 'agree', 'reason': 'x', 'version': 1})[0], 409)
        self.assertEqual(self.feedback(out['caseId'], {'verdict': 'maybe', 'reason': 'x'})[0], 400)
        self.assertEqual(self.total_events(), before)
        other = self.resolved(**self.trial('northside', '800.00'))
        first = self.feedback(other['caseId'], {'verdict': 'agree', 'reason': 'Fine.'}, key='fb-1')
        before = self.total_events()
        again = self.feedback(other['caseId'], {'verdict': 'agree', 'reason': 'Fine.', 'version': first[1]['version'] - 1}, key='fb-1')
        self.assertTrue(again[1]['replayed'])
        self.assertEqual(self.total_events(), before)

    def test_a_withdrawn_request_closes_its_case_with_an_event(self):
        ext = self.resolved(**self.extension('cityside', 'DEMO-410', days=14))
        status, body, _ = self.call('/api/tools/withdrawRequest', {'args': {'requestId': ext['requestId'], 'reason': 'Customer paid, fictional.'}}, 'staff', 'wd-1')
        self.assertEqual(status, 200, body)
        self.assertEqual(self.case(ext['caseId'])['status'], 'closed')
        self.assertEqual(self.pairs(ext['caseId'])[-1], ('closed', 'system'))

    def test_the_state_change_and_its_events_stand_or_fall_together(self):
        """A failure after the events were written and before the commit leaves no case, no request, no action and no event."""
        before = (self.total_events(), self.count('decision_cases'), self.count('requests'), self.count('actions'))
        real = self.app.dg_put

        def broken(case, new=False):
            raise RuntimeError('simulated failure before the commit')
        self.app.dg_put = broken
        try:
            with self.app.lock:
                c = self.app.evidence().customer(self.cust['lakeside'])
                with self.assertRaises(RuntimeError):
                    self.app.delegation_resolve({'id': 'staff_demo', 'role': 'staff', 'name': 'Staff'}, 'test', 'trial_credit', c, None, {'orderAmount': 60000, 'termsDays': 14},
                                                {'recommendation': 'approve', 'reasoning': 'Fictional.'}, None, None)
        finally:
            self.app.dg_put = real
        self.assertEqual((self.total_events(), self.count('decision_cases'), self.count('requests'), self.count('actions')), before)
        # and the success path leaves both
        out = self.resolved(**self.trial('lakeside', '600.00'))
        self.assertEqual(self.count('decision_cases'), before[1] + 1)
        self.assertEqual(len(self.kinds(out['caseId'])), 3)

    def test_the_owner_reads_every_reason_and_signal_staff_read_neither(self):
        out = self.approved_extension()
        self.agree(out['caseId'], 'disagree', override=True)
        owner = self.timeline(out['caseId'])['events']
        self.assertEqual([e['kind'] for e in owner], ['created', 'evaluated', 'decided', 'feedback', 'override'])
        self.assertEqual(owner[3]['data']['reason'], 'Fictional reason.')
        staff = self.timeline(out['caseId'], 'staff')['events']
        self.assertEqual([e['kind'] for e in staff], ['created', 'evaluated', 'decided', 'override'])
        self.assertNotIn('Fictional reason.', json.dumps(staff))
        self.assertTrue(all('reason' not in e['data'] for e in staff))
        trial = self.resolved(**self.trial('harbourline', '5000.00'))
        self.send('POST', '/api/decision-cases/' + trial['caseId'] + '/decide', {'outcome': 'decline', 'reason': 'Private reasoning.', 'version': trial['version']})
        self.assertIn('Private reasoning.', json.dumps(self.timeline(trial['caseId'])['events']))
        self.assertNotIn('Private reasoning.', json.dumps(self.timeline(trial['caseId'], 'staff')))

    def test_who_may_read_the_timeline(self):
        out = self.approved_extension()
        path = '/api/decision-cases/' + out['caseId'] + '/events'
        status, body, _ = self.call(path, None, None, None, {'Cookie': self.service_cookie('owner')})
        self.assertEqual((status, body['error']), (403, 'PERSON_REQUIRED'))
        self.assertEqual(self.call(path, None, None, None, {'Cookie': self.service_cookie('staff')})[0], 200)
        self.assertEqual(self.call('/api/decision-cases/case_nope/events', None, 'owner')[0], 404)
        self.assertEqual(self.call('/api/decision-cases/' + MEMORY['cases'][0]['id'] + '/events', None, 'owner')[0], 404)   # the fictional memory has no live timeline
        self.assertIn(self.call(path)[0], (401, 403))

    def test_assess_and_reads_write_no_event(self):
        before = self.total_events()
        self.assess(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        self.assertEqual(self.total_events(), before)
        out = self.approved_extension()
        self.assertEqual(self.total_events(), before + 3)
        self.case(out['caseId'])
        self.tool('decisionStatus', caseId=out['caseId'])
        self.assertEqual(self.total_events(), before + 3)


# ---------------------------------------------------------------- 2. outcome observations

def inv(total=48000, open_=True, conflict=False):
    return {'id': 'i1', 'reference': 'R-1', 'total': total, 'open': open_, 'conflict': conflict}


class OutcomeRuleTests(unittest.TestCase):
    """outcomes.invoice_outcome / combine / observe_case: pure, on fictional figures."""
    D = date(2026, 10, 24)

    def one(self, payments, due='2026-11-10', as_of=D, current=True, **more):
        return outcomes.invoice_outcome(inv(**more), due, as_of, payments, current)[0]

    LATER = date(2026, 12, 1)

    def test_the_vocabulary_has_written_off_but_nothing_produces_it(self):
        self.assertEqual(outcomes.OUTCOMES, ('on_time', 'late_paid', 'partial', 'open_not_due', 'open_past_due', 'written_off', 'unknown'))
        seen = {self.one(p, due=d, as_of=a, open_=o) for p in ([], [('2026-10-01', 48000)], [('2026-12-01', 48000)], [('2026-10-01', 100)]) for d in ('2026-11-10', '2026-10-01')
                for a in (self.D, date(2026, 12, 2)) for o in (True, False)}
        self.assertNotIn('written_off', seen)
        self.assertTrue(seen <= set(outcomes.OUTCOMES))

    def test_paid_in_full_on_or_before_the_due_date_is_on_time_after_it_is_late(self):
        self.assertEqual(self.one([('2026-11-10', 48000)], as_of=self.LATER, open_=False), 'on_time')   # on the due date itself
        self.assertEqual(self.one([('2026-11-01', 20000), ('2026-11-09', 28000)], as_of=self.LATER, open_=False), 'on_time')
        self.assertEqual(self.one([('2026-11-11', 48000)], as_of=date(2026, 11, 12), open_=False), 'late_paid')
        self.assertEqual(self.one([('2026-11-01', 20000), ('2026-11-12', 28000)], as_of=date(2026, 11, 13), open_=False), 'late_paid')   # the last part came late

    def test_open_and_partly_paid(self):
        self.assertEqual(self.one([]), 'open_not_due')
        self.assertEqual(self.one([], as_of=date(2026, 11, 10)), 'open_not_due')   # the due date itself is not past due
        self.assertEqual(self.one([], as_of=date(2026, 11, 11)), 'open_past_due')
        self.assertEqual(self.one([('2026-11-01', 10000)], as_of=date(2026, 11, 11)), 'partial')
        self.assertEqual(self.one([('2026-11-01', 10000)]), 'open_not_due')   # partly paid, not yet due
        self.assertEqual(self.one([('2026-11-01', 10000)], total=None, as_of=date(2026, 11, 11)), 'partial')   # no total: still open and some of it paid

    def test_what_the_records_cannot_establish_is_unknown_never_good_and_never_zero(self):
        self.assertEqual(self.one([], due=None), 'unknown')
        self.assertEqual(self.one([('2026-11-01', 48000)], conflict=True, open_=False), 'unknown')
        self.assertEqual(self.one([(None, 48000)], open_=False), 'unknown')   # a payment with no received date cannot be placed
        self.assertEqual(self.one([], open_=False), 'unknown')   # closed in the records, no payment shows when
        self.assertEqual(self.one([('2026-11-01', 10000)], open_=False), 'unknown')   # closed, but the payments do not cover it
        self.assertEqual(self.one([('2026-11-01', 48000)], total=None, open_=False), 'unknown')   # no total: cannot say it is paid in full

    def test_an_earlier_as_of_reads_only_the_payments_dated_by_then(self):
        paid = [('2026-11-05', 48000)]
        self.assertEqual(self.one(paid, as_of=date(2026, 11, 20), open_=False), 'on_time')
        self.assertEqual(self.one(paid, as_of=date(2026, 11, 2), current=False, open_=False), 'open_not_due')   # not yet paid on 2 Nov
        self.assertEqual(self.one(paid, as_of=date(2026, 11, 11), current=False, open_=False), 'on_time')

    def test_several_invoices_are_on_time_only_if_all_are(self):
        on, late, past, soon, unknown = (('on_time', {}), ('late_paid', {}), ('open_past_due', {}), ('open_not_due', {}), ('unknown', {}))
        self.assertEqual(outcomes.combine([on, on]), 'on_time')
        self.assertEqual(outcomes.combine([on, late]), 'late_paid')
        self.assertEqual(outcomes.combine([on, soon]), 'open_not_due')
        self.assertEqual(outcomes.combine([on, unknown]), 'unknown')
        self.assertEqual(outcomes.combine([unknown, late]), 'late_paid')   # a definite adverse fact outranks unknown
        self.assertEqual(outcomes.combine([late, past, ('partial', {})]), 'open_past_due')
        self.assertEqual(outcomes.combine([]), 'unknown')

    def test_a_trial_credit_reads_the_invoices_issued_on_or_after_the_approval(self):
        facts = lambda ref, issue, due, paid: {'id': ref, 'reference': ref, 'issueDate': issue, 'due': due, 'total': 1000, 'open': paid is None,
                                               'conflict': False, 'payments': [] if paid is None else [(paid, 1000)]}
        seen = [facts('A', '2026-09-01', '2026-09-15', None), facts('B', '2026-10-24', '2026-11-07', '2026-11-01'), facts('C', '2026-10-25', '2026-11-08', '2026-11-08')]
        out = outcomes.observe_case('trial_credit', {}, None, '2026-10-24', seen, date(2026, 11, 9), True)
        self.assertEqual(out['outcome'], 'on_time')   # A was issued before the approval and is not counted
        self.assertEqual([b['invoiceId'] for b in out['basis']['invoices']], ['B', 'C'])
        self.assertEqual(outcomes.observe_case('trial_credit', {}, None, '2026-10-30', seen[:1], date(2026, 11, 9), True)['outcome'], 'unknown')
        self.assertEqual(outcomes.observe_case('extension', {'invoiceId': 'zzz'}, '2026-11-01', None, seen, date(2026, 11, 9), True)['outcome'], 'unknown')


class ObservationTests(LoopCase):
    def observe(self, body=None, role='owner', **kw):
        return self.send('POST', '/api/delegation/observe-outcomes', body or {}, role=role, **kw)

    def observed_events(self, case_id):
        return [json.loads(d) for k, d in self.row('SELECT kind, data FROM case_events WHERE case_id=? AND kind=? ORDER BY seq', case_id, 'outcome_observed')]

    def pay_in_full(self, who, invoice, amount, on, key):
        """A recorded payment allocated to the invoice, dated `on` (any day: it is the ledger edit a later import or entry would make)."""
        later = date(2027, 1, 1)
        body = {'customerId': self.cust[who], 'receivedDate': on, 'amount': amount, 'reference': 'LOOP-' + key}
        pay = self.records(lambda doc: delegation_demo.new_payment(doc, body, SETTINGS, later, 'payment_t_' + key, self.ORIGIN))['id']
        self.records(lambda doc: delegation_demo.allocate(doc, {'paymentId': pay, 'allocations': [{'invoiceId': self.inv[invoice], 'amount': amount}]}, SETTINGS,
                                                          lambda kind: kind + '_t_' + key, self.ORIGIN))

    def payments_batch(self, day, key):
        """An uploaded payments list (one fictional bank line paying Bayview's DEMO-301 in full), previewed and ready to apply."""
        csv = 'Customer,Date,Amount,Reference,Invoice\nBayview Gelato Co (fictional),' + day + ',480.00,EFT-IMP-' + key + ',DEMO-301\n'
        status, batch, _ = self.call('/api/imports', {'sourceLabel': 'Bank export', 'fileName': 'p.csv', 'csvText': csv, 'shape': 'payments'}, 'staff', key)
        self.assertEqual(status, 200, batch)
        body = {'mapping': batch['mapping'], 'dateOrder': 'dmy', 'resolutions': {'customers': {}, 'conflicts': {}, 'rows': {}}}
        status, batch, _ = self.call('/api/imports/' + batch['id'] + '/mapping', body, 'staff', 'map-' + key)
        self.assertEqual(status, 200, batch)
        self.assertTrue(batch['preview']['ready'], batch['preview'])
        return batch

    def test_an_approved_case_is_observed_once_with_its_basis_and_again_only_when_the_outcome_changes(self):
        out = self.approved_extension()
        status, body = self.observe()
        self.assertEqual((status, body['observed'], body['changed'], body['unchanged'], body['cases']), (200, 1, 1, 0, 1), body)
        [seen] = self.observed_events(out['caseId'])
        self.assertEqual((seen['outcome'], seen['asOf'], seen['policyVersion']), ('open_not_due', '2026-10-24', 1))
        self.assertTrue(seen['observedAt'])
        self.assertEqual(seen['basis']['invoices'][0]['dueDate'], '2026-11-10')
        self.assertEqual(seen['basis']['invoices'][0]['reference'], 'DEMO-301')
        timeline = self.timeline(out['caseId'])['events'][-1]
        self.assertEqual((timeline['kind'], timeline['actor'], timeline['data']['outcome']), ('outcome_observed', 'system', 'open_not_due'))
        # the same ledger, again and on another day with the same result: nothing is written
        before = self.total_events()
        for body in ({}, {}, {'asOf': '2026-11-09'}):
            status, again = self.observe(body)
            self.assertEqual((status, again['changed'], again['unchanged']), (200, 0, 1), again)
        self.assertEqual(self.total_events(), before)

    def test_the_case_shows_the_stored_observation_and_the_current_ledger_label_apart(self):
        out = self.approved_extension()
        self.observe()
        view = self.case(out['caseId'])
        self.assertEqual(view['outcomeObserved']['outcome'], 'open_not_due')
        self.assertEqual((view['outcomeNow']['label'], view['outcomeNow']['source']), ('open_not_due', 'current ledger says'))
        self.assertEqual(view['outcome']['label'], 'open_not_due')   # the earlier field is unchanged
        self.assertEqual(self.case(out['caseId'], 'staff')['outcomeObserved']['outcome'], 'open_not_due')
        row = next(c for c in self.call('/api/delegation/cases', None, 'owner')[1]['cases'] if c['caseId'] == out['caseId'])
        self.assertEqual(row['outcomeObserved']['outcome'], 'open_not_due')
        # a case not yet observed says so
        fresh = self.resolved(**self.trial('northside', '800.00'))
        self.assertIsNone(self.case(fresh['caseId'])['outcomeObserved'])

    def test_an_observation_does_not_count_as_a_new_case_version(self):
        out = self.approved_extension()
        version = self.case(out['caseId'])['version']
        self.observe()
        self.assertEqual(self.case(out['caseId'])['version'], version)
        self.assertEqual(self.feedback(out['caseId'], {'verdict': 'agree', 'reason': 'x', 'version': version})[0], 200)   # the Owner's view is not stale
        self.assertEqual(self.case(out['caseId'])['outcomeObserved']['outcome'], 'open_not_due')   # and a later write keeps the observation

    def test_a_later_ledger_edit_appends_a_new_observation_and_never_rewrites_the_old_one(self):
        out = self.approved_extension()
        self.observe()
        first = self.row('SELECT seq, at, data FROM case_events WHERE case_id=? AND kind=?', out['caseId'], 'outcome_observed')
        self.pay_in_full('bayview', 'DEMO-301', '480.00', '2026-11-05', 'bv1')   # paid in full before the approved date
        self.assertEqual(self.observe({'asOf': '2026-11-20'})[1]['changed'], 1)
        events = self.observed_events(out['caseId'])
        self.assertEqual([e['outcome'] for e in events], ['open_not_due', 'on_time'])
        self.assertEqual(events[1]['asOf'], '2026-11-20')
        self.assertEqual(self.row('SELECT seq, at, data FROM case_events WHERE case_id=? AND kind=? ORDER BY seq', out['caseId'], 'outcome_observed')[0], first[0])   # byte for byte
        self.assertEqual(self.case(out['caseId'])['outcomeObserved']['outcome'], 'on_time')
        # the ledger is edited again (the payment is taken back): a third observation, the first two stay
        self.records(lambda doc: [p.update({'status': 'removed'}) for p in doc['payments'] if p['id'] == 'payment_t_bv1'])
        self.assertEqual(self.observe({'asOf': '2026-11-20'})[1]['changed'], 1)
        self.assertEqual([e['outcome'] for e in self.observed_events(out['caseId'])], ['open_not_due', 'on_time', 'open_past_due'])

    def test_a_late_payment_a_partial_payment_and_a_past_due_invoice(self):
        a = self.approved_extension()   # Bayview, approved to 10 Nov
        owner = self.resolved(**self.extension('cityside', 'DEMO-410', days=14))
        status, body, _ = self.decide(self.request_of(owner['requestId']), 'approve', '2026-11-11', key='owner-decides')   # the Owner approves Cityside to 11 Nov
        self.assertEqual(status, 201, body)
        self.pay_in_full('bayview', 'DEMO-301', '480.00', '2026-11-12', 'bv2')   # two days after the approved date
        self.pay_in_full('cityside', 'DEMO-410', '300.00', '2026-11-01', 'cs1')   # a third of 900.00
        self.assertEqual(self.observe({'asOf': '2026-11-13'})[1]['cases'], 2)   # the Owner-approved case is observed too
        self.assertEqual(self.observed_events(a['caseId'])[-1]['outcome'], 'late_paid')
        self.assertEqual(self.observed_events(owner['caseId'])[-1]['outcome'], 'partial')
        self.assertEqual(self.observed_events(a['caseId'])[-1]['basis']['invoices'][0]['settledOn'], '2026-11-12')

    def test_a_trial_credit_is_unknown_until_an_invoice_is_issued_then_on_time_only_if_all_are(self):
        out = self.resolved(**self.trial('northside', '800.00'))
        self.observe()
        self.assertEqual(self.observed_events(out['caseId'])[-1]['outcome'], 'unknown')   # nothing issued after the approval: unknown, not repaid
        for ref, due in (('NS-1', '2026-11-07'), ('NS-2', '2026-11-07')):
            self.add_invoice(self.cust['northside'], ref, '400.00', due, issue='2026-10-24')
        self.assertEqual(self.observe({'asOf': '2026-10-30'})[1]['changed'], 1)
        self.assertEqual(self.observed_events(out['caseId'])[-1]['outcome'], 'open_not_due')
        northside = self.cust['northside']
        for ref, on, key in (('NS-1', '2026-11-03', 'n1'), ('NS-2', '2026-11-08', 'n2')):
            invoice_id = 'invoice_t_' + ref
            body = {'customerId': northside, 'receivedDate': on, 'amount': '400.00', 'reference': 'LOOP-' + key}
            pay = self.records(lambda doc: delegation_demo.new_payment(doc, body, SETTINGS, date(2027, 1, 1), 'payment_t_' + key, self.ORIGIN))['id']
            self.records(lambda doc: delegation_demo.allocate(doc, {'paymentId': pay, 'allocations': [{'invoiceId': invoice_id, 'amount': '400.00'}]}, SETTINGS,
                                                              lambda kind: kind + '_t_' + key, self.ORIGIN))
        self.assertEqual(self.observe({'asOf': '2026-11-09'})[1]['changed'], 1)
        last = self.observed_events(out['caseId'])[-1]
        self.assertEqual(last['outcome'], 'late_paid')   # NS-2 was paid a day late, so not on time
        self.assertEqual(sorted(b['outcome'] for b in last['basis']['invoices']), ['late_paid', 'on_time'])

    def test_overridden_declined_and_undecided_cases_are_not_observed(self):
        overridden = self.approved_extension()
        self.agree(overridden['caseId'], 'disagree', override=True)
        declined = self.resolved(**self.trial('harbourline', '5000.00'))
        self.send('POST', '/api/decision-cases/' + declined['caseId'] + '/decide', {'outcome': 'decline', 'reason': 'Too large.', 'version': declined['version']})
        waiting = self.resolved(**self.trial('lakeside', '600.00'))
        status, body = self.observe()
        self.assertEqual((status, body['cases'], body['changed']), (200, 0, 0), body)
        for case in (overridden, declined, waiting):
            self.assertEqual(self.observed_events(case['caseId']), [])
            self.assertIsNone(self.case(case['caseId'])['outcomeObserved'])

    def test_the_route_is_for_an_owner_person_with_csrf_and_origin(self):
        self.approved_extension()
        before = self.total_events()
        self.assertEqual(self.observe(role='staff')[0], 403)
        status, body = self.observe(cookie=self.service_cookie('owner'))
        self.assertEqual((status, body['error']), (403, 'PERSON_REQUIRED'))
        agent = self.agent_cookies()
        self.assertEqual(self.observe(cookie=agent['nucleon_owner'], headers={'X-Nucleon-Role': 'owner'})[1]['error'], 'PERSON_REQUIRED')
        self.assertEqual(self.observe(csrf=False)[1]['error'], 'CSRF_REQUIRED')
        self.assertEqual(self.observe(origin=False)[1]['error'], 'ORIGIN_REQUIRED')
        self.assertEqual(self.observe({'asOf': 'tomorrow'})[0], 400)
        self.assertEqual(self.observe({'asOf': 20261110})[0], 400)
        self.assertEqual(self.total_events(), before)
        self.assertEqual(self.call('/api/delegation/observe-outcomes', None, 'owner')[0], 404)   # no GET

    def test_a_failure_after_the_observation_leaves_neither_the_event_nor_the_stored_copy(self):
        out = self.approved_extension()
        real = self.app.dg_patch

        def broken(*args):
            real(*args)
            raise RuntimeError('simulated failure before the commit')
        self.app.dg_patch = broken
        try:
            with self.app.lock, self.assertRaises(RuntimeError):
                self.app.observe_outcomes()
        finally:
            self.app.dg_patch = real
        self.assertEqual(self.observed_events(out['caseId']), [])
        self.assertIsNone(self.case(out['caseId'])['outcomeObserved'])
        self.assertEqual(self.observe()[1]['changed'], 1)

    def test_applying_an_import_observes_the_outcomes(self):
        out = self.approved_extension()
        self.observe()
        batch = self.payments_batch('20/10/2026', 'up-1')
        self.assertEqual([e['outcome'] for e in self.observed_events(out['caseId'])], ['open_not_due'])
        status, applied, _ = self.call('/api/imports/' + batch['id'] + '/apply', {}, 'staff', 'apply-1')
        self.assertEqual(status, 200, applied)
        events = self.observed_events(out['caseId'])
        self.assertEqual([e['outcome'] for e in events], ['open_not_due', 'on_time'])   # paid in full on 20 Oct, before the approved 10 Nov
        self.assertEqual(self.case(out['caseId'])['outcomeObserved']['outcome'], 'on_time')

    def test_a_failing_observation_never_fails_the_import(self):
        self.approved_extension()
        batch = self.payments_batch('20/10/2026', 'up-2')
        real = self.app.observe_outcomes
        self.app.observe_outcomes = lambda *a, **k: 1 / 0
        try:
            status, applied, _ = self.call('/api/imports/' + batch['id'] + '/apply', {}, 'staff', 'apply-2')
        finally:
            self.app.observe_outcomes = real
        self.assertEqual((status, applied['status']), (200, 'applied'))


# ---------------------------------------------------------------- 3. tacit consent (D8)

class TacitPolicyKeyTests(unittest.TestCase):
    def test_the_key_is_declared_off_by_default_and_a_key_left_out_stays_off(self):
        self.assertIn('feedback', delegation.POLICY_KEYS)
        self.assertEqual(delegation.default_policy(SETTINGS)['feedback'], {'tacitAgreeAfterDays': None})
        self.assertEqual(delegation.validate_policy({}, SETTINGS)['feedback'], {'tacitAgreeAfterDays': None})
        self.assertEqual(delegation.validate_policy(delegation_demo.DEMO_POLICY, SETTINGS)['feedback'], {'tacitAgreeAfterDays': None})

    def test_one_to_365_days_or_null_and_nothing_else(self):
        for good in (1, 7, 365, None):
            self.assertEqual(delegation.validate_policy({'feedback': {'tacitAgreeAfterDays': good}}, SETTINGS)['feedback'], {'tacitAgreeAfterDays': good})
        for bad in (0, -1, 366, 1000, 7.5, '7', True, False, [], {}):
            with self.assertRaises(RecordsError, msg=repr(bad)) as raised:
                delegation.validate_policy({'feedback': {'tacitAgreeAfterDays': bad}}, SETTINGS)
            self.assertEqual(raised.exception.field, 'feedback.tacitAgreeAfterDays')

    def test_unknown_sub_keys_and_a_non_object_are_refused(self):
        for body in ({'feedback': {'tacitAgreeAfterDays': 7, 'autoDecline': True}}, {'feedback': {'tacitDeclineAfterDays': 7}}, {'feedback': 7}, {'feedback': [7]}, {'tacit': 7}):
            with self.assertRaises(RecordsError, msg=repr(body)):
                delegation.validate_policy(body, SETTINGS)

    def test_the_digest_is_unchanged_while_the_key_is_off_and_differs_once_it_is_set(self):
        base = delegation.validate_policy(delegation_demo.DEMO_POLICY, SETTINGS)
        old = {k: v for k, v in base.items() if k != 'feedback'}   # a policy saved before the key existed
        self.assertEqual(delegation.policy_digest(base), delegation.policy_digest(old))
        on = delegation.validate_policy({**delegation_demo.DEMO_POLICY, 'feedback': {'tacitAgreeAfterDays': 7}}, SETTINGS)
        self.assertNotEqual(delegation.policy_digest(on), delegation.policy_digest(base))
        self.assertNotEqual(delegation.policy_digest(on), delegation.policy_digest(delegation.validate_policy({**delegation_demo.DEMO_POLICY, 'feedback': {'tacitAgreeAfterDays': 8}}, SETTINGS)))


class TacitConsentTests(LoopCase):
    def age(self, case_id, days):
        """The agent decided this case `days` days before the ledger date (the fixed 24 Oct 2026)."""
        at = (AS_OF - timedelta(days=days)).isoformat() + 'T09:00:00+00:00'
        with self.app.lock, self.app.db:
            data = json.loads(self.app.db.execute('SELECT data FROM decision_cases WHERE id=?', (case_id,)).fetchone()[0])
            data['decision']['at'] = at
            self.app.db.execute('UPDATE decision_cases SET data=? WHERE id=?', (json.dumps(data), case_id))

    def tacit_after(self, days):
        return self.change_policy(feedback={'tacitAgreeAfterDays': days})

    def sweep(self, role='owner', **kw):
        return self.send('POST', '/api/delegation/sweep-tacit-consent', {}, role=role, **kw)

    def feedback_of(self, case_id):
        return self.case(case_id)['feedback']

    def test_the_policy_saves_reads_back_and_versions_the_setting(self):
        self.assertEqual(self.policy()['feedback'], {'tacitAgreeAfterDays': None})
        out = self.tacit_after(7)
        self.assertEqual((out['version'], out['feedback']), (2, {'tacitAgreeAfterDays': 7}))
        self.assertEqual(self.policy('staff')['feedback'], {'tacitAgreeAfterDays': 7})
        for bad in (0, 366, '7', 7.5):
            status, body = self.put_policy({**delegation_demo.DEMO_POLICY, 'feedback': {'tacitAgreeAfterDays': bad}, 'expectedVersion': 2})
            self.assertEqual((status, body['field']), (400, 'feedback.tacitAgreeAfterDays'), bad)
        status, body = self.put_policy({**delegation_demo.DEMO_POLICY, 'feedback': {'tacitAgreeAfterDays': 7, 'autoDecline': True}, 'expectedVersion': 2})
        self.assertEqual(status, 400)
        self.assertEqual(self.policy()['version'], 2)
        self.assertEqual([h['feedback'] for h in self.call('/api/delegation/policy/history', None, 'owner')[1]['versions']], [{'tacitAgreeAfterDays': 7}, {'tacitAgreeAfterDays': None}])
        self.assertEqual(self.pause()['version'], 3)   # pause keeps the setting
        self.assertEqual(self.policy()['feedback'], {'tacitAgreeAfterDays': 7})

    def test_a_version_saved_before_the_key_existed_reads_as_off_with_its_own_digest(self):
        with self.app.lock, self.app.db:
            rules = delegation.validate_policy(delegation_demo.DEMO_POLICY, SETTINGS)
            rules.pop('feedback')
            self.app.db.execute('INSERT INTO delegation_policies (version, created_at, data) VALUES (?,?,?)', (2, '2026-10-24T01:00:00+00:00', json.dumps({**rules, 'createdBy': None, 'note': 'old', 'action': 'save'})))
            current = self.app.policy_current()
        self.assertEqual(current['feedback'], {'tacitAgreeAfterDays': None})
        self.assertEqual(current['digest'], delegation.policy_digest(rules))
        self.assertEqual(self.policy()['digest'], current['digest'])
        self.assertEqual(self.resolved(**self.trial('northside', '800.00'))['authority']['version'], 2)

    def test_it_fires_for_an_agent_decision_nobody_answered_once_the_days_have_passed(self):
        out = self.approved_extension()
        self.tacit_after(7)
        self.age(out['caseId'], 7)
        status, body = self.sweep()
        self.assertEqual((status, body['agreed'], body['tacitAgreeAfterDays']), (200, [out['caseId']], 7), body)
        self.assertEqual(body['skipped'], {'paused': 0, 'off': 0, 'tooRecent': 0, 'hasFeedback': 0, 'alreadyTacit': 0})
        [entry] = self.feedback_of(out['caseId'])
        self.assertEqual((entry['verdict'], entry['reason'], entry['policyVersion']), ('tacit_agree', 'No Owner objection within 7 days (policy setting)', 2))
        self.assertTrue(entry['at'])
        self.assertEqual(self.pairs(out['caseId'])[-1], ('tacit_agree', 'system'))
        event = self.timeline(out['caseId'])['events'][-1]
        self.assertEqual((event['policyVersion'], event['data']['verdict'], event['data']['afterDays']), (2, 'tacit_agree', 7))
        self.assertEqual(self.case(out['caseId'])['decision']['by'], 'agent')   # the decision itself is untouched
        # staff never see it
        self.assertNotIn('tacit_agree', [e['kind'] for e in self.timeline(out['caseId'], 'staff')['events']])
        self.assertNotIn('feedback', self.case(out['caseId'], 'staff'))
        # idempotent: a case is agreed once
        before = self.total_events()
        again = self.sweep()[1]
        self.assertEqual((again['agreed'], again['skipped']['alreadyTacit']), ([], 1))
        self.assertEqual(self.total_events(), before)
        self.assertEqual(len(self.feedback_of(out['caseId'])), 1)

    def test_it_never_fires_before_the_days_have_passed(self):
        out = self.approved_extension()
        self.tacit_after(7)
        self.age(out['caseId'], 6)
        body = self.sweep()[1]
        self.assertEqual((body['agreed'], body['skipped']['tooRecent']), ([], 1))
        self.assertEqual(self.feedback_of(out['caseId']), [])
        self.age(out['caseId'], 7)
        self.assertEqual(self.sweep()[1]['agreed'], [out['caseId']])

    def test_it_never_fires_while_the_setting_is_off_or_the_policy_is_paused(self):
        out = self.approved_extension()
        self.age(out['caseId'], 400)
        body = self.sweep()[1]   # the setting is null
        self.assertEqual((body['agreed'], body['skipped']['off'], body['tacitAgreeAfterDays']), ([], 1, None))
        self.tacit_after(7)
        self.pause()
        body = self.sweep()[1]
        self.assertEqual((body['agreed'], body['skipped']['paused']), ([], 1))
        self.assertEqual(self.feedback_of(out['caseId']), [])
        self.assertEqual(self.pairs(out['caseId'])[-1], ('decided', 'agent'))
        status, resumed = self.send('POST', '/api/delegation/policy/resume', {'expectedVersion': self.policy()['version']})
        self.assertEqual(status, 200, resumed)
        self.assertEqual(self.sweep()[1]['agreed'], [out['caseId']])   # once running again, the elapsed time counts

    def test_it_never_fires_on_an_overridden_case_or_one_with_feedback_or_one_the_owner_decided(self):
        overridden, answered, owner_case = self.approved_extension(), self.resolved(**self.trial('northside', '800.00')), self.resolved(**self.trial('harbourline', '5000.00'))
        self.assertEqual(self.send('POST', '/api/decision-cases/' + owner_case['caseId'] + '/decide', {'outcome': 'approve', 'reason': 'Known to me.', 'version': owner_case['version']})[0], 200)
        self.agree(overridden['caseId'], 'disagree', override=True)
        self.agree(answered['caseId'], 'disagree')
        self.tacit_after(1)
        for c in (overridden, answered, owner_case):
            self.age(c['caseId'], 30)
        before = self.total_events()
        body = self.sweep()[1]
        self.assertEqual((body['agreed'], body['skipped']), ([], {'paused': 0, 'off': 0, 'tooRecent': 0, 'hasFeedback': 1, 'alreadyTacit': 0}))
        self.assertEqual(self.total_events(), before)
        self.assertEqual([f['verdict'] for f in self.feedback_of(answered['caseId'])], ['disagree'])
        self.assertEqual(self.feedback_of(owner_case['caseId']), [])
        self.assertEqual([f['verdict'] for f in self.feedback_of(overridden['caseId'])], ['disagree'])

    def test_a_case_that_has_explicit_feedback_is_counted_as_having_feedback(self):
        a, b = self.approved_extension(), self.resolved(**self.trial('northside', '800.00'))
        self.agree(a['caseId'])
        self.tacit_after(3)
        self.age(a['caseId'], 10)
        self.age(b['caseId'], 10)
        body = self.sweep()[1]
        self.assertEqual((body['agreed'], body['skipped']['hasFeedback']), ([b['caseId']], 1))
        self.assertEqual([f['verdict'] for f in self.feedback_of(a['caseId'])], ['agree'])

    def test_fictional_cases_are_never_touched(self):
        self.approved_extension()
        self.tacit_after(1)
        before = self.row("SELECT COUNT(*) FROM decision_cases WHERE dataset <> 'live' AND data LIKE '%tacit%'")
        self.sweep()
        self.assertEqual(self.row("SELECT COUNT(*) FROM decision_cases WHERE dataset <> 'live' AND data LIKE '%tacit%'"), before)
        self.assertEqual(before, [(0,)])

    def test_a_tacit_agreement_counts_as_an_approving_verdict_labelled_tacit_and_an_explicit_one_after_it_wins(self):
        out = self.approved_extension()
        self.tacit_after(7)
        with self.app.lock:
            case = self.app.dg_case(out['caseId'])
            self.assertEqual((self.app.dg_owner_view(case), self.app.dg_owner_kind(case)), (None, None))   # unanswered: not counted
        self.age(out['caseId'], 9)
        self.sweep()
        with self.app.lock:
            case = self.app.dg_case(out['caseId'])
            self.assertEqual((self.app.dg_owner_view(case), self.app.dg_owner_kind(case)), ('approve', 'tacit'))
            row = next(m for m in self.app.dg_memory(self.app.evidence(), self.app.fixture()) if m['id'] == out['caseId'])
            self.assertEqual((row['ownerDecision'], row['verdictKind'], row['ownerReason']), ('approve', 'tacit', None))   # the system's sentence is not an Owner's reason
        self.agree(out['caseId'], 'disagree')   # the Owner then answers explicitly: that is the verdict
        with self.app.lock:
            case = self.app.dg_case(out['caseId'])
            self.assertEqual((self.app.dg_owner_view(case), self.app.dg_owner_kind(case)), ('decline', 'explicit'))
        self.assertEqual([f['verdict'] for f in self.feedback_of(out['caseId'])], ['tacit_agree', 'disagree'])

    def test_the_live_track_record_and_comparables_report_tacit_and_explicit_separately(self):
        tacit, explicit = self.resolved(**self.trial('northside', '800.00')), self.resolved(**self.trial('harbourline', '5000.00'))
        self.assertEqual(self.send('POST', '/api/decision-cases/' + explicit['caseId'] + '/decide', {'outcome': 'approve', 'reason': 'Known to me.', 'version': explicit['version']})[0], 200)
        shown = self.assess(**self.trial('lakeside', '600.00'))
        self.assertEqual(shown['reliability']['live']['verdictKinds'], {'explicit': 1, 'tacit': 0})   # before the sweep the unanswered agent decision is not counted
        self.tacit_after(2)
        self.age(tacit['caseId'], 5)
        self.assertEqual(self.sweep()[1]['agreed'], [tacit['caseId']])
        with self.app.lock:
            memory = {m['id']: m for m in self.app.dg_memory(self.app.evidence(), self.app.fixture()) if m['dataset'] == 'live'}
        self.assertEqual({k: m['verdictKind'] for k, m in memory.items()}, {tacit['caseId']: 'tacit', explicit['caseId']: 'explicit'})
        shown = self.assess(**self.trial('lakeside', '600.00'))
        self.assertEqual(shown['reliability']['live']['verdictKinds'], {'explicit': 1, 'tacit': 1})
        live = {c['id']: c for c in shown['comparables'] if c['dataset'] == 'live'}
        self.assertEqual(live[tacit['caseId']]['verdictKind'], 'tacit')   # the closest comparables (five at most) include the Northside trial
        self.assertTrue(all(c['verdictKind'] == memory[k]['verdictKind'] for k, c in live.items()))
        self.assertNotIn('ownerReason', live[tacit['caseId']])   # Staff never see an Owner's reason
        stored = self.case(self.resolved(**self.trial('lakeside', '600.00'))['caseId'], 'owner')
        mine = {c['id']: c for c in stored['comparables'] if c['dataset'] == 'live'}
        self.assertEqual((mine[tacit['caseId']]['verdictKind'], mine[tacit['caseId']]['ownerReason']), ('tacit', None))   # the system's sentence is not an Owner's reason
        self.assertEqual(stored['reliability']['live']['verdictKinds'], {'explicit': 1, 'tacit': 1})
        self.assertEqual(memory[explicit['caseId']]['ownerReason'], 'Known to me.')
        self.assertTrue(all('verdictKind' not in c for c in shown['comparables'] if c['dataset'] != 'live'))
        # the rules' own back-test figures are what delegation.track_record computes: the report is added beside them
        self.assertEqual(set(shown['reliability']['live']) - {'verdictKinds'}, {'dataset', 'reviewed', 'wouldApprove', 'ownerApproved', 'ownerDeclined', 'outcomes', 'agreement'})

    def test_reading_the_owner_list_records_elapsed_time_only_when_the_setting_is_on(self):
        out = self.approved_extension()
        self.age(out['caseId'], 30)
        before = self.total_events()
        listed = self.call('/api/delegation/cases', None, 'owner')[1]['cases']
        self.assertEqual(next(c for c in listed if c['caseId'] == out['caseId'])['feedback'], [])
        self.assertEqual(self.total_events(), before)   # off: a read changes nothing
        self.tacit_after(7)
        row = next(c for c in self.call('/api/delegation/cases', None, 'owner')[1]['cases'] if c['caseId'] == out['caseId'])
        self.assertEqual([f['verdict'] for f in row['feedback']], ['tacit_agree'])
        after = self.total_events()
        self.call('/api/delegation/cases', None, 'owner')
        self.call('/api/delegation/cases', None, 'owner')
        self.assertEqual(self.total_events(), after)   # idempotent
        self.assertEqual(self.call('/api/delegation/cases', None, 'staff')[0], 403)

    def test_a_paused_policy_does_not_sweep_when_the_list_is_read(self):
        out = self.approved_extension()
        self.tacit_after(7)
        self.age(out['caseId'], 30)
        self.pause()
        self.call('/api/delegation/cases', None, 'owner')
        self.assertEqual(self.feedback_of(out['caseId']), [])

    def test_the_route_is_for_an_owner_person_with_csrf_and_origin(self):
        out = self.approved_extension()
        self.tacit_after(7)
        self.age(out['caseId'], 30)
        before = self.total_events()
        self.assertEqual(self.sweep(role='staff')[0], 403)
        status, body = self.sweep(cookie=self.service_cookie('owner'))
        self.assertEqual((status, body['error']), (403, 'PERSON_REQUIRED'))
        agent = self.agent_cookies()
        self.assertEqual(self.sweep(cookie=agent['nucleon_owner'], headers={'X-Nucleon-Role': 'owner'})[1]['error'], 'PERSON_REQUIRED')
        self.assertEqual(self.sweep(csrf=False)[1]['error'], 'CSRF_REQUIRED')
        self.assertEqual(self.sweep(origin=False)[1]['error'], 'ORIGIN_REQUIRED')
        self.assertEqual(self.total_events(), before)
        self.assertEqual(self.sweep()[1]['agreed'], [out['caseId']])

    def test_the_agreements_of_one_sweep_are_one_transaction(self):
        a, b = self.approved_extension(), self.resolved(**self.trial('northside', '800.00'))
        self.tacit_after(3)
        self.age(a['caseId'], 10)
        self.age(b['caseId'], 10)
        before = self.total_events()
        real, calls = self.app.case_event, []

        def broken(*args, **kw):
            calls.append(args)
            if len(calls) == 2:
                raise RuntimeError('simulated failure before the commit')
            return real(*args, **kw)
        self.app.case_event = broken
        try:
            with self.app.lock, self.assertRaises(RuntimeError):
                self.app.sweep_tacit_consent()
        finally:
            self.app.case_event = real
        self.assertEqual(self.total_events(), before)
        self.assertEqual((self.feedback_of(a['caseId']), self.feedback_of(b['caseId'])), ([], []))
        self.assertEqual(sorted(self.sweep()[1]['agreed']), sorted([a['caseId'], b['caseId']]))

    def test_the_sweep_takes_its_date_from_the_caller_only_inside_the_app(self):
        out = self.approved_extension()
        self.tacit_after(7)
        self.age(out['caseId'], 3)
        with self.app.lock:
            self.assertEqual(self.app.sweep_tacit_consent(as_of=AS_OF + timedelta(days=3))['agreed'], [])
            self.assertEqual(self.app.sweep_tacit_consent(as_of=(AS_OF + timedelta(days=4)).isoformat())['agreed'], [out['caseId']])
        # the route accepts no date: an asOf in its body changes nothing
        other = self.resolved(**self.trial('northside', '800.00'))
        self.age(other['caseId'], 1)
        self.assertEqual(self.send('POST', '/api/delegation/sweep-tacit-consent', {'asOf': '2030-01-01'})[1]['agreed'], [])


# ---------------------------------------------------------------- 4. the Owner's view timestamps

class ViewedTests(LoopCase):
    def viewed(self, case_id, role='owner', **kw):
        return self.send('POST', '/api/decision-cases/' + case_id + '/viewed', {}, role=role, **kw)

    def views(self, case_id):
        return self.row("SELECT at, actor, policy_version FROM case_events WHERE case_id=? AND kind='viewed' ORDER BY seq", case_id)

    def test_the_owner_opening_a_case_writes_one_viewed_event_and_floods_write_none(self):
        out = self.approved_extension()
        status, body = self.viewed(out['caseId'])
        self.assertEqual((status, body['caseId'], body['recorded']), (200, out['caseId'], True), body)
        self.assertTrue(body['at'])
        [(at, actor, version)] = self.views(out['caseId'])
        self.assertEqual((at, actor, version), (body['at'], 'owner', 1))
        before = self.total_events()
        for _ in range(3):
            status, again = self.viewed(out['caseId'])
            self.assertEqual((status, again['recorded'], again['at']), (200, False, body['at']))   # the earlier time comes back
        self.assertEqual(self.total_events(), before)

    def test_a_second_view_after_the_window_is_written(self):
        out = self.approved_extension()
        self.viewed(out['caseId'])
        with self.app.lock, self.app.db:   # the first view is now older than the window
            old = (datetime.now(timezone.utc) - timedelta(seconds=server.VIEWED_EVERY_SECONDS + 1)).isoformat()
            self.app.db.execute("UPDATE case_events SET at=? WHERE case_id=? AND kind='viewed'", (old, out['caseId']))
        status, body = self.viewed(out['caseId'])
        self.assertEqual((status, body['recorded']), (200, True))
        self.assertEqual(len(self.views(out['caseId'])), 2)
        self.assertEqual(self.viewed(out['caseId'])[1]['recorded'], False)

    def test_the_window_is_per_case(self):
        a, b = self.approved_extension(), self.resolved(**self.trial('northside', '800.00'))
        self.assertTrue(self.viewed(a['caseId'])[1]['recorded'])
        self.assertTrue(self.viewed(b['caseId'])[1]['recorded'])
        self.assertEqual((len(self.views(a['caseId'])), len(self.views(b['caseId']))), (1, 1))

    def test_a_view_is_on_the_owners_timeline_and_never_the_staffs(self):
        out = self.approved_extension()
        self.viewed(out['caseId'])
        self.assertEqual(self.timeline(out['caseId'])['events'][-1]['kind'], 'viewed')
        self.assertNotIn('viewed', [e['kind'] for e in self.timeline(out['caseId'], 'staff')['events']])

    def test_a_view_changes_nothing_in_the_case(self):
        out = self.approved_extension()
        before = self.case(out['caseId'])
        self.viewed(out['caseId'])
        self.assertEqual(self.case(out['caseId']), before)
        self.assertEqual(self.feedback(out['caseId'], {'verdict': 'agree', 'reason': 'x', 'version': before['version']})[0], 200)

    def test_staff_service_and_the_agent_are_refused_and_nothing_is_written(self):
        out = self.approved_extension()
        self.assertEqual(self.viewed(out['caseId'], role='staff')[0], 403)
        status, body = self.viewed(out['caseId'], cookie=self.service_cookie('owner'))
        self.assertEqual((status, body['error']), (403, 'PERSON_REQUIRED'))
        status, body = self.viewed(out['caseId'], cookie=self.service_cookie('staff'), headers={'X-Nucleon-Role': 'staff'})
        self.assertEqual(status, 403)
        agent = self.agent_cookies()
        status, body = self.viewed(out['caseId'], cookie=agent['nucleon_owner'], headers={'X-Nucleon-Role': 'owner'})
        self.assertEqual((status, body['error']), (403, 'PERSON_REQUIRED'))
        status, body = self.viewed(out['caseId'], cookie=agent['nucleon_staff'], headers={'X-Nucleon-Role': 'staff'})
        self.assertEqual((status, body['error']), (403, 'PERSON_REQUIRED'))
        self.assertEqual(self.viewed(out['caseId'], csrf=False)[1]['error'], 'CSRF_REQUIRED')
        self.assertEqual(self.viewed(out['caseId'], origin=False)[1]['error'], 'ORIGIN_REQUIRED')
        self.assertEqual(self.viewed(out['caseId'], origin='https://evil.example')[0], 403)
        self.assertEqual(self.views(out['caseId']), [])
        self.assertEqual(self.call('/api/decision-cases/' + out['caseId'] + '/viewed', None, 'owner')[0], 404)   # no GET

    def test_an_unknown_case_and_the_fictional_memory_are_404(self):
        self.assertEqual(self.viewed('case_nope')[0], 404)
        self.assertEqual(self.viewed(MEMORY['cases'][0]['id'])[0], 404)
        self.assertEqual(self.total_events(), 0)


if __name__ == '__main__':
    unittest.main()
