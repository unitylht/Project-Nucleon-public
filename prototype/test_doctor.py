"""The Doctor (11 Nov 2026): six questions about how the Owner's setup is working, answered by code from the Owner's own cases. Handwritten fictional cases
with known answers; the policy is the fictional demonstration policy (invoice limit AUD 1,000.00, customer total AUD 1,500.00, 30 days, nothing else
overdue required, a quarter of earlier payments late at most)."""
import unittest
from datetime import date

import delegation
import delegation_demo
import doctor

S = {'currency': 'AUD', 'scale': 2}
POLICY = delegation.validate_policy(delegation_demo.DEMO_POLICY, S)
AS_OF = date(2026, 10, 24)
LABELS = {'decision_exposure': 'Exposure of this decision', 'customer_exposure': "The customer's total exposure after this decision",
          'extension_days': 'Days past the current due date', 'nothing_else_overdue': 'Nothing else overdue', 'late_history': 'Earlier late payments',
          'days_past_original_due': 'Days after the original due date'}


def feats(**more):
    f = {'exposure': 50000, 'customerExposure': 50000, 'extensionDays': 10, 'daysFromRequest': 10, 'daysPastOriginalDue': 10, 'nothingElseOverdue': True,
         'priorLateShare': '0', 'lateUnknown': False, 'sizeRatio': None, 'isNew': False, 'heldCustomer': False, 'evidenceComplete': True}
    f.update(more)
    return f


def case(i, handling='owner_review', failing=(), features=None, owner=None, agent=None, verdict=None, overridden=False, kind='extension', customer='c1',
         created='2026-10-20T00:00:00+00:00', observed=None, status=None):
    c = {'id': 'case_%s' % i, 'kind': kind, 'customerId': customer, 'createdAt': created, 'feedback': [],
         'evaluation': {'handling': handling, 'features': features if features is not None else feats(), 'why': None,
                        'risk': {'checks': [{'key': k, 'label': LABELS.get(k, k), 'status': 'fail'} for k in failing]}}}
    if agent:
        c['status'], c['decision'] = 'decided', {'by': 'agent', 'outcome': agent, 'overridden': overridden}
        if verdict:
            c['feedback'] = [{'verdict': verdict}]
    elif owner:
        c['status'], c['decision'] = 'decided', {'by': 'owner', 'outcome': owner}
    else:
        c['status'], c['decision'] = status or ('on_hold' if handling == 'policy_hold' else 'awaiting_owner'), None
    if observed:
        c['outcomeObserved'] = {'outcome': observed}
    return c


def ask(question, cases, policy=POLICY, days=30, names=None, preview=None, preview_for=None):
    return doctor.answer(question, cases, policy, S, AS_OF, days, names or {'c1': 'Bayview', 'c2': 'Cityside', 'c3': 'Harbour'}, {}, preview, preview_for)


def spec_example():
    """20 requests that came to the Owner (11 other overdue, 6 too many days, 3 over the invoice limit) and 21 the agent decided."""
    cs, n = [], 0
    for owner in ['approve'] * 9 + ['decline'] + [None]:
        n += 1; cs.append(case(n, failing=('nothing_else_overdue',), features=feats(nothingElseOverdue=False), owner=owner))
    for owner in ['approve'] + ['decline'] * 5:
        n += 1; cs.append(case(n, failing=('extension_days',), features=feats(extensionDays=40, daysPastOriginalDue=40), owner=owner))
    for owner in ['approve'] * 3:
        n += 1; cs.append(case(n, failing=('decision_exposure',), features=feats(exposure=150000, customerExposure=150000), owner=owner))
    for k in range(18):
        n += 1; cs.append(case(n, handling='autonomous_approve', agent='approve'))
    for k in range(3):
        n += 1; cs.append(case(n, handling='autonomous_decline', agent='decline'))
    return cs


class CameTests(unittest.TestCase):
    def test_came_groups_by_reason_with_what_the_owner_did(self):
        out = ask('came', spec_example())
        self.assertEqual(out['headline'], '20 of your 41 requests came to you. The most common reason: nothing else overdue (11).')
        self.assertIn('11 — Nothing else overdue: you approved 9, declined 1, 1 still waiting.', out['findings'])
        self.assertIn('6 — Days past the current due date: you approved 1, declined 5, 0 still waiting.', out['findings'])
        self.assertTrue(out['enough'])

    def test_came_single_what_if_states_start_gain_and_cost(self):
        out = ask('came', spec_example())
        first = next(s for s in out['suggestions'] if s['answers'] == {'allowOtherOverdue': True})
        self.assertEqual(first['text'], 'If customers with another overdue invoice were allowed: the agent would have decided 11 of these 20 itself (now 0). '
                                        'Of the 11 it would add, you had approved 9 and declined 1.')
        self.assertEqual(first['answers'], {'allowOtherOverdue': True})
        self.assertIn('If the invoice limit were AUD 1,500.00: the agent would have decided 3 of these 20 itself (now 0). Of the 3 it would add, you had approved 3 and declined 0.',
                      [s['text'] for s in out['suggestions']])

    def test_a_what_if_that_approves_what_the_owner_declined_goes_last_and_says_so(self):
        last = ask('came', spec_example())['suggestions'][-1]
        self.assertIsNone(last['answers'])   # no "Try this in Quick setup" for a change you mostly declined
        self.assertTrue(last['text'].startswith('If the total-lateness limit were 45 days: the agent would have decided 6 of these 20 itself (now 0).'), last['text'])
        self.assertTrue(last['text'].endswith('You declined most of these, so this change is not recommended.'))

    def test_came_combination_beats_single_changes(self):
        cs = [case(i, failing=('nothing_else_overdue', 'extension_days'), features=feats(nothingElseOverdue=False, extensionDays=40, daysPastOriginalDue=40), owner='approve')
              for i in range(6)]
        out = ask('came', cs)
        texts = [s['text'] for s in out['suggestions']]
        combined = [t for t in texts if ' and ' in t.split(':')[0]]
        self.assertEqual(len(combined), 1, texts)
        self.assertIn('the agent would have decided 6 of these 6 itself (now 0)', combined[0])
        self.assertEqual(out['suggestions'][0]['text'], combined[0])
        self.assertEqual(out['suggestions'][0]['answers'], {'allowOtherOverdue': True, 'daysPastOriginalDue': 45})

    def test_look_ahead_on_open_invoices_is_added_when_the_server_gives_it(self):
        preview = {'total': 22, 'counts': {'agent': 0, 'owner': 13, 'held': 9}, 'reasons': []}
        out = ask('came', spec_example(), preview=preview, preview_for=lambda patch: {'total': 22, 'counts': {'agent': 2, 'owner': 11, 'held': 9}, 'reasons': []})
        self.assertTrue(out['suggestions'][0]['text'].endswith("If each customer asked today for 14 more days on each open invoice, it would decide 2 of 22 (now 0)."), out['suggestions'][0]['text'])


class CorrectionTests(unittest.TestCase):
    def cases(self):
        cs = [case('c%d' % d, handling='autonomous_approve', agent='approve', overridden=True, features=feats(daysPastOriginalDue=d, extensionDays=d)) for d in (26, 27, 28, 29, 5)]
        cs += [case('a%d' % i, handling='autonomous_approve', agent='approve', verdict='agree', features=feats(daysPastOriginalDue=d, extensionDays=d)) for i, d in enumerate((22, 23, 24, 5, 5, 5, 5))]
        return cs

    def test_corrections_finds_the_limit_that_catches_corrected_not_agreed(self):
        out = ask('corrections', self.cases())
        self.assertEqual(out['headline'], "You reviewed 12 of the agent's 12 decisions: you agreed with 7 and corrected 5.")
        self.assertEqual(out['suggestions'][0]['text'], 'If the total-lateness limit were 25 days: 4 of the 5 approvals you corrected would have come to you instead (now 0), '
                                                        'and so would 0 of the 7 you agreed with (now 0).')
        self.assertEqual(out['suggestions'][0]['answers'], {'daysPastOriginalDue': 25})

    def test_corrections_counts_reversed_declines_apart(self):
        cs = self.cases() + [case('d1', handling='autonomous_decline', agent='decline', overridden=True)]
        out = ask('corrections', cs)
        self.assertIn('1 of the corrections was a decline you reversed.', out['findings'])

    def test_no_agent_decisions(self):
        out = ask('corrections', [case(1)])
        self.assertEqual(out['headline'], 'The agent has not decided anything in this window.')
        self.assertEqual(out['suggestions'], [])


class OtherQuestionTests(unittest.TestCase):
    def test_help_counts(self):
        one = ask('help', [case(1, handling='autonomous_decline', agent='decline')])
        self.assertIn("Of the agent's 1 decision you agreed with 0, corrected 0, and 1 is not reviewed yet.", one['findings'])
        out = ask('help', spec_example())
        self.assertEqual(out['headline'], 'Of your 41 requests, the agent decided 21 by itself (18 approved, 3 declined) and 20 came to you.')

    def test_outcomes_labels(self):
        cs = [case(i, handling='autonomous_approve', agent='approve', observed=o) for i, o in enumerate(['on_time'] * 3 + ['late_paid', 'open_not_due', None])]
        out = ask('outcomes', cs)
        self.assertEqual(out['headline'], 'The agent approved 6 requests that still stand: 3 paid by the new date, 1 paid late, 1 not due yet, 1 not known yet.')

    def test_customers_top_five(self):
        cs = [case(i, customer='c2', failing=('nothing_else_overdue',)) for i in range(3)] + [case('b', customer='c1', failing=('extension_days',)),
                                                                                               case('x', customer='c1', handling='autonomous_approve', agent='approve')]
        out = ask('customers', cs)
        self.assertEqual(out['findings'][0], 'Cityside: 3 of 3 requests came to you, mostly: Nothing else overdue (3).')
        self.assertEqual(out['findings'][1], 'Bayview: 1 of 2 requests came to you, mostly: Days past the current due date (1).')

    def test_rules_blocks_and_never_mattered(self):
        cs = [case(i, failing=('nothing_else_overdue',)) for i in range(6)]
        preview = {'total': 20, 'counts': {'agent': 0, 'owner': 20, 'held': 0}, 'reasons': [{'key': 'days_past_original_due', 'label': 'Days after the original due date', 'count': 19, 'question': 'daysPastOriginalDue'}]}
        out = ask('rules', cs, preview=preview)
        self.assertEqual(out['headline'], 'Days after the original due date blocks almost every open invoice (19 of 20).')
        self.assertIn("Nothing else overdue: sent 6 requests to you; blocks 0 of today's 20 open invoices.", out['findings'])
        self.assertTrue(any(f.startswith('These never sent you a request in this window:') and 'Earlier late payments' in f for f in out['findings']), out['findings'])


class EdgeTests(unittest.TestCase):
    def test_too_few_cases_says_so_and_still_counts(self):
        out = ask('came', [case(i, failing=('nothing_else_overdue',), features=feats(nothingElseOverdue=False)) for i in range(3)])
        self.assertFalse(out['enough'])
        self.assertTrue(any('too few' in n for n in out['notes']))
        self.assertEqual(out['headline'], '3 of your 3 requests came to you. The most common reason: nothing else overdue (3).')

    def test_no_cases_at_all(self):
        for q, _ in doctor.QUESTIONS:
            out = ask(q, [])
            self.assertFalse(out['enough'], q)
            self.assertTrue(out['headline'], q)
            self.assertEqual(out['facts'][0], out['headline'])

    def test_cases_without_features_are_left_out_and_counted(self):
        cs = spec_example()[:11] + [case('old', failing=('extension_days',), features={})]
        cs[-1]['evaluation'].pop('features')
        out = ask('came', cs)
        self.assertTrue(any(n.startswith('1 request was not tried') for n in out['notes']), out['notes'])
        self.assertIn('of these 11 itself', out['suggestions'][0]['text'])

    def test_trial_credit_cases_are_counted_but_not_tried(self):
        cs = spec_example()[:11] + [case('t', kind='trial_credit', failing=('trial_exposure',))]
        out = ask('came', cs)
        self.assertEqual(out['headline'].split('.')[0], '12 of your 12 requests came to you')
        self.assertTrue(any(n.startswith('1 request was not tried') for n in out['notes']))

    def test_window(self):
        cs = [case(1, created='2026-10-20T00:00:00+00:00'), case(2, created='2026-08-01T00:00:00+00:00')]
        self.assertEqual(ask('help', cs, days=30)['window'], {'days': 30, 'cases': 1})
        self.assertEqual(ask('help', cs, days=None)['window'], {'days': None, 'cases': 2})

    def test_facts_are_headline_findings_suggestions_notes(self):
        out = ask('came', spec_example())
        self.assertEqual(out['facts'], [out['headline']] + out['findings'] + [s['text'] for s in out['suggestions']] + out['notes'])

    def test_headlines_has_six(self):
        h = doctor.headlines(spec_example(), POLICY, S, AS_OF, 30, {}, {}, None)
        self.assertEqual([x['question'] for x in h], [q for q, _ in doctor.QUESTIONS])
        self.assertTrue(all(x['headline'] for x in h))

    def test_unknown_question(self):
        with self.assertRaises(ValueError):
            ask('nope', [])


if __name__ == '__main__':
    unittest.main()


class ReviewFixTests(unittest.TestCase):
    """The final review of 11 Nov 2026: numbers the Doctor states must be true."""

    def tight_policy(self):
        return delegation.validate_policy({**delegation_demo.DEMO_POLICY, 'limits': {**delegation_demo.DEMO_POLICY['limits'], 'maxDecisionExposure': '300.00'},
                                           'extensions': {**delegation_demo.DEMO_POLICY['extensions'], 'maxDays': 20, 'maxDaysPastOriginalDue': 20}}, S)

    def test_corrections_never_suggests_loosening_what_the_owner_already_tightened(self):
        cs = [case('c%d' % i, handling='autonomous_approve', agent='approve', overridden=True, features=feats(daysPastOriginalDue=28, extensionDays=28, exposure=90000)) for i in range(4)]
        cs += [case('a%d' % i, handling='autonomous_approve', agent='approve', verdict='agree', features=feats(daysPastOriginalDue=5, extensionDays=5, exposure=10000)) for i in range(4)]
        out = ask('corrections', cs, policy=self.tight_policy())
        self.assertEqual(out['suggestions'], [], [s['text'] for s in out['suggestions']])
        self.assertTrue(any('already' in n for n in out['notes']), out['notes'])

    def test_corrections_states_what_today_already_catches(self):
        out = ask('corrections', CorrectionTests().cases())
        self.assertIn('(now 0)', out['suggestions'][0]['text'])
        self.assertIn('you agreed with (now 0)', out['suggestions'][0]['text'])

    def test_corrections_never_suggests_sending_everything(self):
        cs = [case('c%d' % i, handling='autonomous_approve', agent='approve', overridden=True) for i in range(8)]
        cs += [case('a%d' % i, handling='autonomous_approve', agent='approve', verdict='agree') for i in range(3)]
        out = ask('corrections', cs)
        self.assertEqual(out['suggestions'], [], [s['text'] for s in out['suggestions']])

    def test_corrections_counts_what_it_could_not_try(self):
        cs = CorrectionTests().cases() + [case('t', kind='trial_credit', handling='autonomous_approve', agent='approve', overridden=True)]
        out = ask('corrections', cs)
        self.assertTrue(any(n.startswith('1 corrected decision was not tried') for n in out['notes']), out['notes'])

    def test_came_cost_is_counted_over_what_the_change_adds(self):
        cs = [case('r%d' % i, failing=(), owner='decline') for i in range(4)]   # came because the assistant did not recommend approval; pass every limit
        for c in cs:
            c['evaluation']['why'] = 'the assistant did not recommend approving'
        cs += [case('o%d' % i, failing=('nothing_else_overdue',), features=feats(nothingElseOverdue=False), owner='approve') for i in range(3)]
        s = next(x for x in ask('came', cs)['suggestions'] if x['answers'] == {'allowOtherOverdue': True})
        self.assertIn('the agent would have decided 7 of these 7 itself (now 4). Of the 3 it would add, you had approved 3 and declined 0.', s['text'])
        self.assertNotIn('not recommended', s['text'])
        self.assertTrue(any(n.startswith("4 of these pass today's limits") for n in ask('came', cs)['notes']))

    def test_other_reasons_are_kept_apart(self):
        cs = []
        for i, why in enumerate(['the agent is in advisory mode'] * 2 + ['the assistant did not recommend approving'] * 3):
            c = case('w%d' % i); c['evaluation']['why'] = why; cs.append(c)
        f = ask('came', cs)['findings']
        self.assertIn('3 — the assistant did not recommend approving: you approved 0, declined 0, 3 still waiting.', f)
        self.assertIn('2 — the agent is in advisory mode: you approved 0, declined 0, 2 still waiting.', f)

    def test_closed_and_withdrawn_are_said(self):
        cs = [case(i, failing=('nothing_else_overdue',), features=feats(nothingElseOverdue=False), status='closed') for i in range(2)]
        w = case('w', failing=('nothing_else_overdue',), features=feats(nothingElseOverdue=False), owner='approve'); w['decision']['overridden'] = True
        f = ask('came', cs + [w])['findings']
        self.assertIn('3 — Nothing else overdue: you approved 0, declined 0, 0 still waiting, 2 closed, 1 withdrawn.', f)

    def test_now_uses_the_real_policy_without_a_total_limit(self):
        cs = [case(i, handling='owner_review', failing=('nothing_else_overdue',), features=feats(nothingElseOverdue=False, extensionDays=10, daysPastOriginalDue=50), owner='approve') for i in range(5)]
        s = next(x for x in ask('came', cs)['suggestions'] if x['answers'] == {'allowOtherOverdue': True})
        self.assertIn('the agent would have decided 5 of these 5 itself (now 0)', s['text'])   # 50 days past the original due date: no such limit in the demo policy

    def test_outcome_and_decline_wording(self):
        one = ask('outcomes', [case(1, handling='autonomous_approve', agent='approve', observed='on_time')])
        self.assertEqual(one['headline'], 'The agent approved 1 request that still stands: 1 paid by the new date.')
        d = case('d', handling='autonomous_decline', agent='decline', verdict='disagree')
        f = ask('corrections', CorrectionTests().cases() + [d])['findings']
        self.assertIn('1 of the corrections was a decline you disagreed with.', f)


class MinorFixTests(unittest.TestCase):
    """The deferred minors of the final review, 11 Nov 2026."""

    def test_look_ahead_names_its_assumption_and_the_cap(self):
        preview = {'total': 200, 'truncated': True, 'counts': {'agent': 0, 'owner': 200, 'held': 0}, 'reasons': []}
        out = ask('came', spec_example(), preview=preview, preview_for=lambda patch: {**preview, 'counts': {'agent': 2, 'owner': 198, 'held': 0}})
        s = out['suggestions'][0]['text']
        self.assertIn('If each customer asked today for 14 more days on each open invoice, it would decide 2 of 200 (now 0); only the first 200 open invoices were tried.', s)
        r = ask('rules', [case(i, failing=('nothing_else_overdue',)) for i in range(6)], preview=preview)
        self.assertTrue(any(n.startswith('Blocks count each open invoice as if its customer asked today for 14 more days') and 'first 200' in n for n in r['notes']), r['notes'])

    def test_one_day_limit_is_named_once_like_the_preview(self):
        c = case(1, failing=('extension_days', 'days_past_original_due'))
        self.assertEqual([k for k, _ in doctor.reasons_of(c)], ['days_past_original_due'])
        self.assertEqual([k for k, _ in doctor.reasons_of(case(2, failing=('extension_days',)))], ['extension_days'])

    def test_a_not_recommended_change_has_no_try_link_and_a_note_when_it_is_all_there_is(self):
        cs = [case(i, failing=('extension_days',), features=feats(extensionDays=40, daysPastOriginalDue=40), owner='decline') for i in range(5)]
        out = ask('came', cs)
        self.assertEqual(len(out['suggestions']), 1)
        self.assertIsNone(out['suggestions'][0]['answers'])
        self.assertTrue(any(n.startswith('No change here is recommended') for n in out['notes']), out['notes'])

    def test_help_tells_held_customers_from_contradicting_information(self):
        held = case('h', handling='policy_hold', features=feats(heldCustomer=True))
        contra = case('x', handling='policy_hold', features=feats(heldCustomer=False))
        f = ask('help', [held, contra])['findings']
        self.assertIn('1 of those that came to you was from a customer on your never-decide list.', f)
        self.assertIn('1 was held because the information contradicted the records.', f)
