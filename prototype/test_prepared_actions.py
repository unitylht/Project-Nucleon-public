"""The owner prepares a decision through the tool surface and confirms it with one button; asks for a new suggestion, which goes
through the same guarded step as the automatic one; and both roles get their next steps from the workflow (actions_for), never a
generic instruction. All data is fictional. No real model is called: the mock stands in, and test adapters change what it says."""
import json
import unittest
from unittest import mock

import coordinator
from agent import ToolError
from server import NO_REASON, DeskTools
from test_helpers import Recording
from test_situation import SituationCase
from test_suggestion import PastTheLimit

BEYOND = 'The suggested date goes beyond the days you allowed.'
OPEN = 'a request for this invoice is already open'
ASK = 'How many days, or until which date?'
OFF = 'turned off under Setup → Agent tools'


class PreparedActionsTests(SituationCase):
    def case(self, rid=None, role='owner'):
        status, c, _ = self.call('/api/requests/' + (rid or self.r['id']), role=role)
        self.assertEqual(status, 200, c)
        return c

    def confirm(self, p, role='owner', key='c1', **change):
        """The Confirm decision button: the case as it stands now, with the prepared values and their version."""
        c = self.case()
        shown = (c.get('preparedDecision') or {}).get('suggestionShown')
        body = {'expectedRequestVersion': c['version'], 'analysisId': c['analysis']['id'], 'evidenceVersion': c['analysis']['snapshot']['evidenceVersion'],
                'outcome': p['outcome'], 'approvedDueDate': p['approvedDueDate'], 'reason': p['reason'], 'preparedVersion': p['version'],
                **({'suggestionShown': shown} if shown else {}), **change}
        return self.call('/api/requests/' + c['id'] + '/decisions', body, role, key)

    def second_case(self):
        return self.wait_status(self.create('Could we pay invoice DEMO-502 on 2026-11-10 instead?', key='intake-2'), ('awaiting_owner',))

    def prepare(self, text, key, role='owner', request_id=None, **args):
        """One call to prepareDecision with args and the person's words: what the tool returned (the refusal itself when it was refused)."""
        status, body, _ = self.tool('prepareDecision', role, key, message=text, requestId=request_id or self.r['id'], **args)
        self.assertEqual(status, 200, body)
        return body['result'] if body['ok'] else body

    def test_approve_14_days_then_prepares_the_decision_and_only_confirm_commits_it(self):
        before = self.case()
        result = self.prepare('approve 14 days, then', 'q1', outcome='approve', days=14)
        p = result['prepared']
        self.assertEqual((result['requestId'], p['version'], p['outcome'], p['approvedDueDate'], p['days'], p['currentDue'], p['askedDate']),
                         (self.r['id'], 1, 'approve', '2026-11-03', 14, '2026-10-20', '2026-11-10'))
        self.assertEqual(p['comparison'], {'askedDays': 21, 'days': 14, 'limitDays': 14, 'withinLimit': True})
        self.assertIn('Prepared, not decided', result['note'])
        # nothing is decided: the case is as it was, with the preparation beside it for the owner only
        after = self.case()
        self.assertEqual((after['status'], after['decision'], after['version']), ('awaiting_owner', None, before['version']))
        stored = after['preparedDecision']
        self.assertEqual((stored['version'], stored['by'], stored['outcome'], stored['approvedDueDate'], stored['days'], stored['comparison']),
                         (1, 'owner_demo', 'approve', '2026-11-03', 14, p['comparison']))
        self.assertEqual(stored['suggestionShown'], {'version': 2, 'outcome': 'approve', 'approvedDueDate': '2026-11-03'})
        self.assertEqual([e['data']['version'] for e in after['history'] if e['kind'] == 'decision.prepared'], [1])
        shown = self.situation('owner')['case']['preparedDecision']
        self.assertEqual((shown['version'], shown['approvedDueDate'], 'at' in shown), (1, '2026-11-03', False))
        staff = json.dumps(self.case(role='staff'))
        for key in ('preparedDecision', 'preparedVersion', 'decision.prepared'):
            self.assertNotIn(key, staff)
        self.assertIsNone(self.situation('staff')['case']['preparedDecision'])
        # a second preparation replaces the first
        p2 = self.prepare('approve 10 days, then', 'q2', outcome='approve', days=10)['prepared']
        self.assertEqual((p2['version'], p2['approvedDueDate'], p2['comparison']), (2, '2026-10-30', {'askedDays': 21, 'days': 10, 'limitDays': 14, 'withinLimit': True}))
        self.assertEqual(self.case()['preparedDecision']['version'], 2)
        self.assertEqual([(x['version'], x['status'], x.get('replacedBy')) for x in self.case()['preparations']], [(1, 'superseded', 2), (2, 'current', None)])
        # a replaced preparation, values other than the prepared ones, and staff are refused; nothing is decided
        for n, (prepared, change, expected) in enumerate(((p, {}, (409, 'STALE_PREPARATION')), (p2, {'approvedDueDate': '2026-11-03'}, (409, 'STALE_PREPARATION')),
                                                          (p2, {'reason': 'Another reason.'}, (409, 'STALE_PREPARATION')))):
            status, error, _ = self.confirm(prepared, key='bad' + str(n), **change)
            self.assertEqual((status, error['error']), expected, error)
        self.assertEqual(self.confirm(p2, role='staff', key='staff')[0], 403)
        self.assertIsNone(self.case()['decision'])
        # confirmed: the decision is the preparation, and the preparation is gone
        status, decision, _ = self.confirm(p2, key='ok')
        self.assertEqual(status, 201, decision)
        self.assertEqual((decision['outcome'], decision['approvedDueDate'], decision['reason']), (p2['outcome'], p2['approvedDueDate'], p2['reason']))
        done = self.wait_status(self.r, ('completed',))
        owner = self.case()
        self.assertEqual((owner['suggestionSeen']['relation'], 'preparedDecision' in owner, 'preparedDecision' in done), ('changed', False, False))
        self.assertIsNone(self.situation('owner')['case']['preparedDecision'])
        self.assertEqual([(x['version'], x['status']) for x in owner['preparations']], [(1, 'superseded'), (2, 'confirmed')])
        earlier = self.situation('owner')['case']['preparations']
        self.assertEqual([(x['version'], x['status'], x['approvedDueDate']) for x in earlier], [(1, 'superseded', '2026-11-03'), (2, 'confirmed', '2026-10-30')])

    def test_with_no_due_date_on_record_days_are_not_counted_and_the_owner_is_asked(self):
        self.add_invoice(self.bayside, 'DEMO-503', stillOwed='300.00', stillOwedAsOf='2026-10-16')   # no due date
        r = self.wait_status(self.create('Could we pay invoice DEMO-503 on 2026-11-10 instead?', key='intake-3'), ('awaiting_owner',))
        refused = self.prepare('approve 14 days, then', 'q1', request_id=r['id'], outcome='approve', days=14)
        self.assertEqual(refused['missing'], 'currentDue')
        self.assertIn('No due date is on record for invoice DEMO-503, so 14 days cannot be counted from it.', refused['ask'])
        after = self.case(r['id'])
        self.assertEqual(('preparedDecision' in after, [e for e in after['history'] if e['kind'] == 'decision.prepared']), (False, []))
        # a date the owner names is checked as a decision's is, and prepared with no day count
        early = self.prepare('approve to 10 November, not 1 October', 'q2', request_id=r['id'], outcome='approve', date='2026-10-01')
        prepared = self.prepare('approve to 10 November, not 1 October', 'q3', request_id=r['id'], outcome='approve', date='2026-11-10', reason='They asked nicely.')
        self.assertEqual((early['ok'], early['error']), (False, 'INVALID_ARGUMENT'))
        self.assertEqual((prepared['prepared']['approvedDueDate'], prepared['prepared']['days'], prepared['prepared']['comparison']),
                         ('2026-11-10', None, {'askedDays': None, 'days': None, 'limitDays': None, 'withinLimit': None}))
        self.assertEqual(prepared['prepared']['reason'], NO_REASON)   # not the owner's words: never recorded as theirs

    def test_days_and_dates_are_kept_only_as_the_owner_said_them(self):
        for n, args in enumerate(({'days': 30}, {'date': '2026-12-25'})):   # "two weeks" is neither 30 days nor Christmas
            result = self.prepare('approve two weeks', 'w' + str(n), outcome='approve', **args)
            self.assertEqual((result['missing'], result['ask'], 'prepared' in result), (list(args)[0], ASK, False), args)
        self.assertNotIn('preparedDecision', self.case())
        self.assertEqual(self.prepare('approve two weeks', 'w2', outcome='approve', days=14)['prepared']['approvedDueDate'], '2026-11-03')
        # a number that is part of a date or counts weeks is no day count; a day and month in either order, or the ISO form, is a date
        for n, (text, args, kept) in enumerate((('approve to 3 November', {'days': 3}, False), ('approve 2 weeks', {'days': 2}, False),
                                                ('approve a fortnight', {'days': 14}, True), ('approve a week', {'days': 7}, True),
                                                ('approve three weeks', {'days': 21}, True), ('approve ten days', {'days': 10}, True),
                                                ('approve to November 10th', {'date': '2026-11-10'}, True), ('approve to 10 Nov', {'date': '2026-11-10'}, True),
                                                ('approve to 2026-11-10', {'date': '2026-11-10'}, True), ('approve to 10 December', {'date': '2026-11-10'}, False))):
            result = self.prepare(text, 'g' + str(n), outcome='approve', **args)
            self.assertEqual('prepared' in result, kept, (text, args, result))

    def test_a_reason_of_only_the_decision_s_own_words_is_not_kept(self):
        for n, (text, reason, kept) in enumerate((('approve 14 days, then', 'approve', False),
                                                  ('approve 14 days for Bayside Café', 'approve 14 days for Bayside Café', False),
                                                  ('approve 14 days, they have an event next month', 'they have an event next month', True))):
            result = self.prepare(text, 'r' + str(n), outcome='approve', days=14, reason=reason)
            self.assertEqual(result['prepared']['reason'], reason if kept else NO_REASON, text)

    def test_a_case_whose_records_changed_since_its_analysis_is_refreshed_before_preparing(self):
        with self.app.lock, self.app.db:
            r = self.app.get(self.r['id'])
            r['analysis']['snapshot']['evidenceVersion'] = 'changed since'
            self.app.save(r)
        refused = self.prepare('approve 14 days, then', 'q1', outcome='approve', days=14)
        self.assertEqual((refused['missing'], refused['ask']), ('refresh', 'The records changed since the analysis; refresh the case first.'))
        self.assertNotIn('preparedDecision', self.case())

    def test_the_owner_s_tools_refuse_staff_even_when_called_directly(self):
        with self.app.lock:
            tools = DeskTools(self.app, {'role': 'staff', 'id': 'staff_demo'}, 'approve 14 days', None, None, None, request_id=self.r['id'])
            for name, args in (('_prepareDecision', {'outcome': 'approve', 'days': 14}), ('_requestSuggestion', {'requestId': 'current'})):
                with self.assertRaises(ToolError) as refused:
                    getattr(tools, name)(args)
                self.assertEqual(refused.exception.code, 'FORBIDDEN', name)
        self.assertNotIn('preparedDecision', self.case())

    def test_a_new_suggestion_withdraws_the_prepared_decision(self):
        self.prepare('approve 14 days, then', 'q1', outcome='approve', days=14)
        self.assertEqual(self.situation('owner')['case']['preparedDecision']['version'], 1)
        self.ok('requestSuggestion', key='q2', message='Can you suggest something?', requestId=self.r['id'])   # a new version: what the preparation was shown is no longer on screen
        self.assertNotIn('preparedDecision', self.case())
        self.assertIsNone(self.situation('owner')['case']['preparedDecision'])   # the case block draws no Confirm
        self.assertEqual([(x['version'], x['status']) for x in self.case()['preparations']], [(1, 'withdrawn')])
        self.prepare('approve 10 days, then', 'q3', outcome='approve', days=10)
        self.assertEqual(self.call('/api/suggestions', {'on': False}, 'owner')[0], 200)   # turned off: withdrawn too
        self.assertNotIn('preparedDecision', self.case())

    def test_a_step_whose_tool_is_turned_off_is_not_allowed_and_says_why(self):
        for n, tool in enumerate(('prepareDecision', 'requestSuggestion', 'interpretStatement', 'openRequest')):
            self.assertEqual(self.call('/api/agent-tools', {'tool': tool, 'enabled': False}, 'owner', 'off' + str(n))[0], 200)
        acts = {a['id']: a for a in self.situation('owner')['actions']}
        for step in ('prepare_decision', 'request_suggestion', 'add_context'):
            self.assertEqual((acts[step]['allowed'], acts[step]['why']), (False, OFF), step)
        self.assertTrue(acts['decide']['allowed'])
        requests = {a['label']: (a['allowed'], a['why']) for a in self.situation('staff')['actions'] if a['id'] == 'open_request'}
        self.assertEqual(requests, {'Enter a request for invoice DEMO-501': (False, OPEN), 'Enter a request for invoice DEMO-502': (False, OFF)})

    def test_two_cases_waiting_for_the_customer_and_no_case_named_is_ambiguous(self):
        other = self.second_case()
        current = {'customerId': self.bayside['id']}   # the customer is current; no case is
        status, body, _ = self.tool('prepareDecision', 'owner', 'g1', message='approve 14 days for Bayside', current=current, outcome='approve', days=14)
        ambiguous = body['result']
        self.assertEqual((status, body['ok']), (200, True), body)
        self.assertEqual(sorted(x['requestId'] for x in ambiguous['ambiguous']), sorted([self.r['id'], other['id']]))
        self.assertTrue(ambiguous['ask'].startswith('Which case do you mean?'))
        self.assertNotIn('preparedDecision', self.case())
        prepared = self.prepare('approve 14 days for Bayside', 'g2', request_id=other['id'], outcome='approve', days=14)
        self.assertEqual((prepared['prepared']['approvedDueDate'], self.case(other['id'])['preparedDecision']['version']), ('2026-11-03', 1))

    def test_staff_are_offered_neither_tool_and_cannot_confirm(self):
        p = self.prepare('approve 14 days, then', 'q1', outcome='approve', days=14)['prepared']
        offered = [t['name'] for t in self.call('/api/tools', role='staff')[1]['tools']]
        self.assertNotIn('prepareDecision', offered)
        self.assertNotIn('requestSuggestion', offered)
        for name, args in (('prepareDecision', {'outcome': 'approve', 'days': 10}), ('requestSuggestion', {'requestId': 'current'})):
            status, body, _ = self.tool(name, 'staff', 'st-' + name, message='approve 10 days, then', **args)
            self.assertEqual((status, body['error']), (403, 'FORBIDDEN'), name)
        self.assertEqual((self.case()['preparedDecision']['version'], self.situation('owner')['case']['suggestion']['version']), (1, 2))
        self.assertEqual(self.confirm(p, role='staff')[0], 403)
        self.assertIsNone(self.case()['decision'])

    def test_request_suggestion_runs_the_guarded_step_with_the_day_limit_and_keeps_the_next_version(self):
        self.app.model_adapter = PastTheLimit()   # approves the date asked, 21 days, beyond the 14 the owner allowed
        with mock.patch('coordinator.validate_suggestion', wraps=coordinator.validate_suggestion) as checked:
            result = self.ok('requestSuggestion', key='q1', message='Can you suggest something?', requestId=self.r['id'])
        [check] = checked.call_args_list
        self.assertEqual(check.kwargs['day_limits'], [(self.answer_line, 14)])
        s = self.situation('owner')['case']['suggestion']
        self.assertEqual((s['version'], s['status'], s['outcome']), (3, 'failed', None))
        self.assertIn(BEYOND, s['withheldBecause'])
        self.assertEqual((result['suggestion']['status'], result['suggestion']['withheldBecause']), ('failed', s['withheldBecause']))
        self.assertEqual([e['data'] for e in self.case()['history'] if e['kind'] == 'suggestion.updated'][-1], {'version': 3, 'status': 'failed'})
        # within the limit: given, as the next version
        self.app.model_adapter = Recording()
        result = self.ok('requestSuggestion', key='q2', message='Any advice?', requestId=self.r['id'])
        s = self.situation('owner')['case']['suggestion']
        self.assertEqual((s['version'], s['status'], s['outcome'], s['approvedDueDate']), (4, 'given', 'approve', '2026-11-03'))
        self.assertEqual((result['suggestion']['approvedDueDateText'], result['suggestion']['version']), ('Tue 3 Nov 2026', 4))
        # turned off, nothing is formed
        self.assertEqual(self.call('/api/suggestions', {'on': False}, 'owner')[0], 200)
        result = self.ok('requestSuggestion', key='q3', message='What do you recommend?', requestId=self.r['id'])
        self.assertEqual((result['suggestion']['status'], self.case()['analysis']['brief']['suggestionStatus']), ('off', 'off'))

    def test_staff_with_two_cases_waiting_for_the_owner_are_told_to_wait_and_not_to_enter_them_again(self):
        other = self.second_case()
        s = self.situation('staff')
        acts = s['actions']
        self.assertEqual(sorted((a['label'], a['allowed'], a['why']) for a in acts if a['id'] == 'wait_for_owner'),
                         [("Wait for the owner's decision on invoice " + ref, True, 'the owner decides; nothing to enter') for ref in ('DEMO-501', 'DEMO-502')])
        self.assertEqual(sorted((a['label'], a['allowed'], a['why']) for a in acts if a['id'] == 'open_request'),
                         [('Enter a request for invoice ' + ref, False, OPEN) for ref in ('DEMO-501', 'DEMO-502')])
        self.assertEqual({a['id'] for a in acts}, {'wait_for_owner', 'open_request', 'add_invoice', 'record_payment'})
        self.assertEqual({a['link'] for a in acts if a['id'] == 'wait_for_owner'}, {'#/case/' + self.r['id'], '#/case/' + other['id']})
        details = self.ok('caseDetails', 'staff', requestId=self.r['id'])   # the agent reads the same steps
        self.assertEqual(details['case']['requestId'], self.r['id'])

    def test_the_owner_s_next_steps_are_to_decide_prepare_or_ask_for_a_suggestion(self):
        acts = {a['id']: a for a in self.situation('owner')['actions']}
        self.assertEqual(list(acts), ['decide', 'prepare_decision', 'request_suggestion', 'add_context'])
        self.assertEqual((acts['decide']['label'], acts['decide']['link'], acts['decide']['needsConfirmation']),
                         ('Decide the request for invoice DEMO-501', '#/case/' + self.r['id'], True))
        self.assertTrue(acts['request_suggestion']['allowed'])
        # suggestions off: turning them on is a step, and a new suggestion is not until then
        self.assertEqual(self.call('/api/suggestions', {'on': False}, 'owner')[0], 200)
        acts = {a['id']: a for a in self.situation('owner')['actions']}
        self.assertEqual((acts['request_suggestion']['allowed'], acts['request_suggestion']['why'], 'turn_on_suggestions' in acts), (False, 'suggestions are off', True))


if __name__ == '__main__':
    unittest.main()
