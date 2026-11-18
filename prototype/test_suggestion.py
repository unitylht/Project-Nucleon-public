"""The advisory suggestion: off by default and the owner's alone, withheld while a question is open, checked whole by code,
stored apart from the owner's decision, withdrawn when the records change; a remembered outcome stays history; the
counters count the workflow. All data is fictional. No real model is called."""
import json
import time
import unittest
from unittest import mock

from agent import MockAdapter
from coordinator import COUNTERS_NOTE, STEP_FAILED, SUGGEST_FAILED, SUGGESTION_LABEL, WITHHELD
import test_case_coordinator as coordinated   # a module, so that its tests are not collected twice here
from test_helpers import NAMED, tell_owner
from test_records import RecordsCase

YEARS = 'Bayside Café have been customers for years.'                  # one relationship line: nothing to ask
AGAINST = 'Bayside Café: no extension this time, I do not want their debt to grow.'   # one constraint line
REMEMBER = 'approved 14 Nov, fine this time'


class Faulty(MockAdapter):
    """The mock, except that planning and suggesting fail with an error that is not a model failure (a fault in code)."""
    def respond(self, task, messages, tools=None, schema=None, timeout=None):
        if task in ('plan_needs', 'suggest'):
            raise RuntimeError('a fault in the step')
        return super().respond(task, messages, tools, schema, timeout)


class BareCite(MockAdapter):
    """The mock, except that the suggestion cites an id that was never loaded."""
    def respond(self, task, messages, tools=None, schema=None, timeout=None):
        out = super().respond(task, messages, tools, schema, timeout)
        if task == 'suggest':
            out.value['cites'] = ['nowhere']
        return out


class PastTheLimit(MockAdapter):
    """The mock, except that the suggestion approves the requested date (21 days after the due date) whatever limit the owner
    stated, as the live model did on 20 October."""
    def respond(self, task, messages, tools=None, schema=None, timeout=None):
        out = super().respond(task, messages, tools, schema, timeout)
        if task == 'suggest':
            out.value['approvedDueDate'] = '2026-11-10'
        return out


class SuggestionTests(RecordsCase):
    case, question = coordinated.CaseCoordinatorTests.case, coordinated.CaseCoordinatorTests.question

    def ready(self, adapter=None, mode='mock'):
        self.start(adapter, mode)
        self.practice_ready()
        self.bayside = self.add_customer('Bayside Café')
        for n in range(501, 506):
            self.add_invoice(self.bayside, 'DEMO-' + str(n), dueDate='2026-10-20')

    def tell(self, text, key='say'):
        return tell_owner(self, text, key)

    def switch(self, on):
        status, body, _ = self.call('/api/suggestions', {'on': on}, 'owner')
        self.assertEqual(status, 200, body)
        return body

    def owner_view(self, r):
        return self.call('/api/requests/' + r['id'], role='owner')[1]

    def wait_suggestion(self, r, status, version):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            view = self.owner_view(r)
            brief = view['analysis']['brief']
            if brief['suggestionStatus'] == status and (brief['suggestion'] or {}).get('version', version) == version:
                return view
            time.sleep(.02)
        self.fail('the suggestion did not reach ' + status)

    def decide(self, r, outcome='approve', approved='2026-11-10', key='decision-1', shown=None, **extra):
        body = {'expectedRequestVersion': r['version'], 'analysisId': r['analysis']['id'], 'evidenceVersion': r['analysis']['snapshot']['evidenceVersion'],
                'outcome': outcome, 'approvedDueDate': approved, 'reason': 'This invoice only.',
                'suggestionShown': shown and {k: shown[k] for k in ('version', 'outcome', 'approvedDueDate')}, **extra}
        return self.call('/api/requests/' + r['id'] + '/decisions', body, 'owner', key)

    def test_suggestions_are_off_by_default_and_owner_only(self):
        self.ready()
        self.tell(YEARS)
        self.assertEqual([self.call('/api/suggestions', role=role)[:2] for role in ('owner', 'staff')], [(200, {'on': False})] * 2)
        r = self.case()
        self.assertEqual((r['analysis']['brief']['suggestion'], r['analysis']['brief']['suggestionStatus']), (None, 'off'))
        self.assertEqual(self.call('/api/suggestions', {'on': True}, 'staff')[0], 403)
        self.assertEqual(self.call('/api/suggestions', {'on': 'yes'}, 'owner')[0], 400)
        self.assertEqual(self.switch(True), {'on': True})
        self.assertEqual(self.call('/api/suggestions', role='staff')[1], {'on': False})
        view = self.wait_suggestion(r, 'given', 1)   # turned on: the case already waiting gets one
        s = view['analysis']['brief']['suggestion']
        self.assertEqual((s['outcome'], s['approvedDueDate'], s['status'], s['label']), ('approve', '2026-11-10', 'advisory', SUGGESTION_LABEL))
        self.assertEqual((view['version'], view['analysis']['id']), (r['version'], r['analysis']['id']))
        self.switch(False)   # off means off: the waiting case's suggestion is withdrawn, and cannot be accepted
        brief = self.owner_view(r)['analysis']['brief']
        self.assertEqual((brief['suggestion'], brief['suggestionStatus']), (None, 'off'))
        self.assertEqual(self.decide(view, shown=s)[1]['error'], 'STALE_SUGGESTION')
        self.switch(True)
        view = self.wait_suggestion(r, 'given', 3)
        status, d, _ = self.decide(view, shown=view['analysis']['brief']['suggestion'])
        self.assertEqual((status, self.owner_view(r)['suggestionSeen']['relation']), (201, 'accepted'))
        staff = self.reopen(r)
        brief = staff['analysis']['brief']
        self.assertEqual((brief['suggestion'], brief['suggestionStatus'], brief['withheldBecause']), (None, 'off', []))
        for key in ('suggestionSeen', 'suggestionVersion', 'suggestModelCalls'):
            self.assertNotIn('"' + key + '"', json.dumps(staff))
        self.assertNotIn(s['sentence'], json.dumps(staff))
        self.assertNotIn('suggest', [x.get('kind') for x in staff['runs']])
        self.assertNotIn('suggestion.updated', [e['kind'] for e in staff['history']])

    def test_a_suggestion_is_withheld_while_an_owner_question_is_open_and_given_after_the_answer(self):
        self.ready()
        self.switch(True)
        self.tell(NAMED)   # its guidance ("a small extension") is unclear for this case: one owner question
        r = self.case()
        brief = r['analysis']['brief']
        [q] = brief['questions']
        self.assertEqual((brief['suggestionStatus'], brief['suggestion'], brief['withheldBecause']), ('withheld', None, [q['id']]))
        self.assertEqual(r['analysis']['stats']['suggestModelCalls'], 0)   # withheld without asking the model
        status, view, _ = self.question(r, 'answer', {'text': coordinated.ANSWER})   # the answer starts a suggestion step; the reply waits for it
        self.assertEqual(status, 200, view)
        brief, line = view['analysis']['brief'], self.app.statements()[-1]['lines'][0]['id']
        s = brief['suggestion']
        self.assertEqual((brief['suggestionStatus'], brief['withheldBecause'], s['version'], s['outcome'], s['approvedDueDate']),
                         ('given', [], 2, 'approve', '2026-11-03'))   # current due 20 Oct + up to 14 days, written by code
        self.assertIn(line, s['cites'])
        self.assertEqual((view['version'], view['status'], view['analysis']['id']), (r['version'], 'awaiting_owner', r['analysis']['id']))
        self.assertEqual([e['data'] for e in view['history'] if e['kind'] == 'suggestion.updated'], [{'version': 2, 'status': 'given'}])
        self.assertEqual([(x['kind'], x['status']) for x in view['runs'] if x.get('kind')], [('suggest', 'finished')])

    def test_context_arguing_against_approval_never_suggests_approve(self):
        self.ready()
        self.switch(True)
        said = self.tell(AGAINST)
        self.assertEqual([x['kind'] for x in said['lines']], ['constraint'])
        brief = self.case()['analysis']['brief']
        s = brief['suggestion']
        self.assertEqual((brief['suggestionStatus'], s['outcome'], s['approvedDueDate'], s['cites']),
                         ('given', 'decline', None, [said['lines'][0]['id']]))

    def test_the_suggestion_shown_is_stored_beside_the_decision_not_in_it(self):
        self.ready()
        self.switch(True)
        self.tell(YEARS)
        r = self.case()
        s = r['analysis']['brief']['suggestion']
        self.assertEqual(self.decide(r, shown={'version': 'one', 'outcome': 'approve', 'approvedDueDate': None}, key='d0')[0], 400)
        self.assertEqual(self.decide(r, shown={**s, 'approvedDueDate': '2026-11-11'}, key='d1')[1]['error'], 'STALE_SUGGESTION')   # not what was shown
        status, d, _ = self.decide(r, 'decline', None, shown=s)
        self.assertEqual(status, 201, d)
        view = self.owner_view(r)
        self.assertEqual((d['outcome'], d['approvedDueDate'], view['suggestionSeen']),
                         ('decline', None, {'version': 1, 'outcome': 'approve', 'approvedDueDate': '2026-11-10', 'relation': 'declined_against'}))
        self.assertEqual([k for k in d if k.startswith('suggestion')], [])   # the decision holds no trace of it, nor does its event
        self.assertEqual([e['data'] for e in view['history'] if e['kind'] == 'decision.committed'], [d])

    def test_a_stale_suggestion_cannot_be_accepted(self):
        self.ready()
        self.switch(True)
        self.tell(YEARS)
        r = self.case()
        s = r['analysis']['brief']['suggestion']
        body = {'customerId': self.bayside['id'], 'receivedDate': '2026-10-12', 'amount': '100.00', 'reference': 'EFT-1'}
        self.assertEqual(self.call('/api/records/payments', body, 'staff', 'pay-1')[0], 200)   # the records change: prepared again
        self.wait_status(r, ('awaiting_owner',))
        again = self.owner_view(r)
        fresh = again['analysis']['brief']['suggestion']
        self.assertNotEqual(again['analysis']['id'], r['analysis']['id'])
        self.assertEqual((fresh['version'], fresh['outcome'], fresh['approvedDueDate']), (2, s['outcome'], s['approvedDueDate']))
        self.assertEqual(self.decide(again, shown=s, key='d1')[1]['error'], 'STALE_SUGGESTION')   # the same advice, from older records
        self.assertEqual(self.decide(r, shown=s, key='d2')[1]['error'], 'STALE_VERSION')   # the page it was shown on is older still
        self.assertEqual(self.decide(again, shown=fresh, key='d3')[0], 201)

    def test_a_remembered_outcome_is_history_not_guidance(self):
        self.ready()
        self.switch(True)
        first = self.case()
        status, d, _ = self.decide(first, approved='2026-11-14', remember={'text': REMEMBER, 'keepForCustomer': True})
        self.assertEqual(status, 201, d)
        s = self.app.statements()[-1]
        self.assertEqual((s['text'], s['status'], s['visibility'], s['scope'], s['source'], [(x['kind'], x['quote']) for x in s['lines']]),
                         (REMEMBER, 'confirmed', 'owner', {'kind': 'customer', 'customerId': self.bayside['id']},
                          {'kind': 'decision', 'id': d['id']}, [('guidance', REMEMBER)]))
        years = self.tell(YEARS)['lines'][0]['id']
        second = self.case('DEMO-502', 'intake-2')
        lines, decisions = second['context']['lines'], second['context']['decisions']
        self.assertEqual([(x['requestId'], x['outcome'], x['approvedDueDate']) for x in decisions], [(first['id'], 'approve', '2026-11-14')])
        self.assertEqual([(x['id'], x['kind'], x['source']) for x in lines], [(s['lines'][0]['id'], 'guidance', 'decision'), (years, 'relationship', 'turn')])
        self.assertNotIn(d['reason'], json.dumps(lines))   # the decision's reason stays on the decision
        self.assertIn(first['id'], second['analysis']['brief']['contextShown'])   # shown to the agent as a decision, not as a line
        view = self.question(second, 'skip', {}, key='skip-1')[1]   # decide without the question: the suggestion is given
        brief = view['analysis']['brief']
        # The mock cites every line it is given; code drops the words kept at the first decision, which stay shown to the owner.
        self.assertEqual((brief['suggestionStatus'], brief['suggestion']['cites']), ('given', [years]))
        self.assertIn(s['lines'][0]['id'], [x['id'] for x in view['context']['lines']])
        self.assertFalse({first['id'], d['id']} & {x['id'] for x in lines})   # the decision record is never a line

    def test_counters_count_the_workflow_not_quality(self):
        self.ready()
        self.switch(True)
        failed = self.case('DEMO-501', 'i-501')   # nothing said yet: nothing for a suggestion to rest on
        self.assertEqual(failed['analysis']['brief']['suggestionStatus'], 'failed')
        self.assertEqual([x['text'] for x in failed['analysis']['brief']['openItems'] if x.get('step') == 'suggest'],
                         [SUGGEST_FAILED, WITHHELD['evidence']])   # an approve with nothing to cite: why, in a fixed sentence
        self.assertTrue(failed['analysis']['stats']['suggestReason'].startswith('evidence: '))   # the raw reason, kept for tuning
        staff = json.dumps(self.reopen(failed))
        for text in (SUGGEST_FAILED, WITHHELD['evidence'], 'suggestReason'):   # staff: not even that a suggestion failed
            self.assertNotIn(text, staff)
        self.assertEqual(self.decide(failed, key='d-501')[0], 201)
        self.assertIsNone(self.owner_view(failed)['suggestionSeen'])   # no suggestion was on screen
        self.tell(YEARS)
        for reference, outcome, approved, relation in (('DEMO-502', 'approve', '2026-11-10', 'accepted'), ('DEMO-503', 'approve', '2026-11-03', 'changed'),
                                                       ('DEMO-504', 'decline', None, 'declined_against')):
            r = self.case(reference, 'i-' + reference)
            self.assertEqual(self.decide(r, outcome, approved, 'd-' + reference, shown=r['analysis']['brief']['suggestion'])[0], 201)
            self.assertEqual(self.owner_view(r)['suggestionSeen']['relation'], relation)
        self.tell(NAMED, 'say-2')
        self.assertEqual(self.case('DEMO-505', 'i-505')['analysis']['brief']['suggestionStatus'], 'withheld')
        self.assertEqual(self.call('/api/suggestions/counters', role='staff')[0], 403)
        status, counters, _ = self.call('/api/suggestions/counters', role='owner')
        self.assertEqual((status, counters), (200, {'given': 3, 'withheld': 1, 'failed': 1, 'accepted': 1, 'changed': 1, 'declinedAgainst': 1,
                                                    'note': COUNTERS_NOTE}))
        self.assertEqual(COUNTERS_NOTE, 'Workflow counters on fictional data; not a measure of real-world decision quality.')

    def test_a_suggestion_step_cut_off_by_a_restart_runs_again(self):
        self.ready()
        self.switch(True)
        self.tell(YEARS)
        r = self.case()
        with self.app.lock, self.app.db:   # as if the process stopped during a suggestion step
            self.app.store_run({'id': 'run_cut', 'kind': 'suggest', 'requestId': r['id'], 'requestVersion': r['version'],
                                'analysisId': r['analysis']['id'], 'status': 'running', 'mode': 'mock', 'cause': 'test', 'queuedAt': None})
        self.restart()
        view = self.wait_suggestion(r, 'given', 2)
        self.assertEqual([(x['id'], x['status']) for x in view['runs'] if x.get('kind')][0], ('run_cut', 'interrupted'))

    def test_a_suggestion_after_a_business_date_move_is_new(self):
        self.demo = True
        self.ready()
        self.switch(True)
        self.tell(YEARS)
        r = self.case()
        s = r['analysis']['brief']['suggestion']
        self.assertEqual(self.call('/api/demo/advance', {'days': 7}, 'operator')[:2], (200, {'today': '2026-10-25'}))
        self.wait_status(r, ('awaiting_owner',))
        again = self.owner_view(r)
        self.assertNotEqual(again['analysis']['id'], r['analysis']['id'])   # prepared again for the new as-of date
        self.assertEqual(self.facts(again)['asOfDate']['value'], '2026-10-25')
        self.assertEqual(self.decide(again, shown=s)[1]['error'], 'STALE_SUGGESTION')
        self.assertEqual(self.decide(again, shown=again['analysis']['brief']['suggestion'], key='d2')[0], 201)

    def test_a_suggestion_step_that_fails_a_check_keeps_its_reason_in_the_run(self):
        self.ready(BareCite(), 'live')
        self.switch(True)
        self.tell(NAMED)
        view = self.question(self.case(), 'answer', {'text': coordinated.ANSWER})[1]
        brief = view['analysis']['brief']
        self.assertEqual((brief['suggestionStatus'], [x['text'] for x in brief['openItems'] if x.get('step') == 'suggest']),
                         ('failed', [SUGGEST_FAILED, 'The agent cited evidence that was not loaded.']))
        [run] = [x for x in view['runs'] if x.get('kind') == 'suggest']
        self.assertEqual(run['suggestionStats']['suggestReason'], 'cite: not loaded ["nowhere"]')
        self.assertNotIn('nowhere', json.dumps(self.reopen(view)))

    def test_a_suggestion_beyond_the_days_the_owner_allowed_is_withheld(self):
        self.ready(PastTheLimit(), 'live')
        self.switch(True)
        self.tell(NAMED)
        view = self.question(self.case(), 'answer', {'text': coordinated.ANSWER})[1]   # "Up to 14 days this time", for this case
        brief = view['analysis']['brief']
        self.assertEqual((brief['suggestionStatus'], brief['suggestion'], [x['text'] for x in brief['openItems'] if x.get('step') == 'suggest']),
                         ('failed', None, [SUGGEST_FAILED, 'The suggested date goes beyond the days you allowed.']))
        [run] = [x for x in view['runs'] if x.get('kind') == 'suggest']
        self.assertTrue(run['suggestionStats']['suggestReason'].startswith('exceeds_day_limit: approve to 2026-11-10, due 2026-10-20, up to 14 days'))

    def test_a_request_beyond_the_limit_gets_the_latest_date_within_it(self):
        self.ready()
        self.switch(True)
        self.tell(NAMED)
        # asked for 10 Nov, 21 days after the due date of 20 Oct; the owner allows up to 14 days: approve to 3 Nov, said so
        view = self.question(self.case(), 'answer', {'text': coordinated.ANSWER})[1]
        s = view['analysis']['brief']['suggestion']
        self.assertEqual((s['outcome'], s['approvedDueDate'], s['sentence']),
                         ('approve', '2026-11-03', 'A shorter extension than asked, within the days you allowed.'))
        # a request within the limit keeps its own date, not the latest the limit would allow
        within = self.question(self.case('DEMO-502', key='intake-2'), 'answer', {'text': 'Up to 30 days this time'}, key='q2')[1]
        s = within['analysis']['brief']['suggestion']
        self.assertEqual((s['outcome'], s['approvedDueDate'], s['sentence']), ('approve', '2026-11-10', 'Based on what you said and the records.'))

    def test_a_fault_in_a_suggestion_step_marks_the_suggestion_failed(self):
        self.ready()
        self.switch(True)
        self.tell(NAMED)
        r = self.case()
        with mock.patch('server.suggestion_inputs', side_effect=RuntimeError('a fault')):
            view = self.question(r, 'answer', {'text': coordinated.ANSWER})[1]
        brief = view['analysis']['brief']
        self.assertEqual((brief['suggestionStatus'], brief['withheldBecause'], brief['suggestion']), ('failed', [], None))   # not left withheld
        self.assertIn({'kind': 'code_check', 'text': STEP_FAILED, 'step': 'suggest'}, brief['openItems'])
        self.assertEqual([(x['status'], x['failure']['kind']) for x in view['runs'] if x.get('kind')], [('failed', 'internal_error')])

    def test_a_fault_in_an_agent_step_costs_that_step_never_the_case(self):
        self.ready(Faulty(), 'live')
        self.switch(True)
        self.tell(NAMED)
        r = self.case()
        brief = r['analysis']['brief']
        self.assertEqual((r['status'], r['analysis']['aiStatus'], brief['questions'], brief['suggestionStatus']), ('awaiting_owner', 'live', [], 'failed'))
        self.assertEqual([x for x in brief['openItems'] if x['text'] == STEP_FAILED],
                         [{'kind': 'code_check', 'text': STEP_FAILED, 'step': 'needs'}, {'kind': 'code_check', 'text': STEP_FAILED, 'step': 'suggest'}])

    def test_a_complete_request_with_context_asks_nothing_and_suggests(self):
        self.ready()
        self.switch(True)
        said = self.tell(YEARS)   # one relationship line: nothing unclear to ask about
        r = self.case()
        brief = r['analysis']['brief']
        self.assertEqual((r['status'], brief['questions'], brief['withheldBecause'], brief['suggestionStatus']), ('awaiting_owner', [], [], 'given'))
        s = brief['suggestion']
        self.assertEqual((s['outcome'], s['approvedDueDate'], s['cites'], s['label']), ('approve', '2026-11-10', [said['lines'][0]['id']], SUGGESTION_LABEL))
        self.assertEqual((r['analysis']['stats']['needsModelCalls'], r['analysis']['stats']['suggestModelCalls']), (1, 1))

    def test_ai_unavailable_shows_lines_and_no_suggestion(self):
        self.ready()
        self.switch(True)
        said = self.tell(YEARS)
        self.restart(mode='unavailable')   # the model cannot be reached: the code-only fallback prepares the case
        r = self.case()
        brief = r['analysis']['brief']
        self.assertEqual((r['status'], r['task']['mode'], r['analysis']['aiStatus']), ('awaiting_owner', 'manual_fallback', 'failed'))
        self.assertEqual([x['id'] for x in r['context']['lines']], [said['lines'][0]['id']])   # what the owner said is still shown
        self.assertEqual((brief['suggestion'], brief['suggestionStatus'], brief['questions']), (None, 'off', []))
        self.assertNotIn('suggest', [x.get('kind') for x in r['runs']])   # and no suggestion step is queued for it
        self.assertEqual(self.decide(r, key='d-fallback')[0], 201)


if __name__ == '__main__':
    unittest.main()
