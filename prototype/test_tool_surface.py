"""The business tool surface: GET api/tools lists the desk tools this role is offered now, with their JSON schemas; POST
api/tools/<name> runs one as the desk agent runs it (DeskTools.execute), for another front end or agent, with each operation
keeping the roles' privacy itself. The operations a browser review found missing: compareExtension (no write),
withdrawPreparation (not a decline), workQueue (who acts next, across customers), listRequests (filtered by status) and
prepareHoldingMessage (a status text that promises nothing). All data is fictional; no real model is called."""
import json
import threading
import unittest
from datetime import timedelta
from unittest import mock

from agent import AMOUNT, calendar_date, display_date
from coordinator import CAPABILITIES
from model_adapter import AdapterError
from server import APIError, App, DeskTools
from test_case_coordinator import ANSWER
from test_situation import SituationCase

OWNER_ONLY = ('prepareDecision', 'withdrawPreparation', 'requestSuggestion', 'interpretStatement')
DUE = '2026-10-20'   # DEMO-501 and DEMO-502 (SituationCase)
SAID = 'Hi, Bayside Café here. Could we pay invoice DEMO-502 on 2026-11-10 instead?'
STAFF = {'role': 'staff', 'id': 'staff_demo'}


class Unreachable:
    """A model that cannot be reached."""

    def respond(self, task, messages, tools=None, schema=None, timeout=None):
        raise AdapterError('timeout', 'the gateway did not answer')


class ToolSurfaceTests(SituationCase):
    def case(self, role='owner', rid=None):
        status, c, _ = self.call('/api/requests/' + (rid or self.r['id']), role=role)
        self.assertEqual(status, 200, c)
        return c

    def stored(self):
        """The case and its events as stored."""
        with self.app.lock:
            return self.app.get(self.r['id']), self.app.history(self.r['id'])

    def prepare(self, days, key):
        return self.ok('prepareDecision', key=key, message='approve ' + str(days) + ' days', outcome='approve', days=days, requestId=self.r['id'])['prepared']

    def second_case(self):
        return self.wait_status(self.create('Could we pay invoice DEMO-502 on 2026-11-10 instead?', key='intake-2'), ('awaiting_owner',))

    def bayside_subject(self):
        return {'customerId': self.bayside['id'], 'name': 'Bayside Café'}

    def test_each_role_is_listed_its_tools_with_their_schemas_and_may_run_no_other(self):
        status, staff, _ = self.call('/api/tools', role='staff')
        self.assertEqual(status, 200, staff)
        names = [t['name'] for t in staff['tools']]
        self.assertEqual(names, [c['name'] for c in CAPABILITIES if 'staff' in c['roles'] and c['defaultEnabled']])
        for name in OWNER_ONLY:
            self.assertNotIn(name, names)
        for name in ('compareExtension', 'workQueue', 'listRequests', 'prepareHoldingMessage', 'raiseConcern'):
            self.assertIn(name, names)
        compare = next(t for t in staff['tools'] if t['name'] == 'compareExtension')
        self.assertEqual(set(compare), {'name', 'kind', 'needsConfirmation', 'description', 'parameters'})
        self.assertEqual((compare['kind'], compare['needsConfirmation'], compare['parameters']['type'], set(compare['parameters']['properties'])),
                         ('read', False, 'object', {'requestId', 'days', 'date', 'otherDays', 'otherDate'}))
        owner = [t['name'] for t in self.call('/api/tools', role='owner')[1]['tools']]
        self.assertEqual(owner, [c['name'] for c in CAPABILITIES if 'owner' in c['roles'] and c['defaultEnabled']])
        self.assertNotIn('raiseConcern', owner)   # staff raise concerns; the owner decides
        concern = next(t for t in staff['tools'] if t['name'] == 'raiseConcern')
        self.assertEqual((concern['kind'], concern['needsConfirmation'], set(concern['parameters']['properties'])), ('act', False, {'requestId', 'text'}))
        # a tool the owner turned off is neither listed nor run
        self.assertEqual(self.call('/api/agent-tools', {'tool': 'compareExtension', 'enabled': False}, 'owner', 'off')[0], 200)
        self.assertNotIn('compareExtension', [t['name'] for t in self.call('/api/tools', role='staff')[1]['tools']])
        self.assertEqual(self.tool('compareExtension', 'staff', requestId=self.r['id'], days=10)[0], 403)
        # another role's tool is 403, an unknown one (reply is no tool) 404, and no session is refused
        status, body, _ = self.tool('prepareDecision', 'staff', 'k1', message='decline', outcome='decline', requestId=self.r['id'])
        self.assertEqual((status, body['error']), (403, 'FORBIDDEN'))
        self.assertEqual([self.tool(name)[0] for name in ('sendEmail', 'reply')], [404, 404])
        self.assertEqual(self.call('/api/tools')[0], 401)
        self.assertEqual(self.call('/api/tools/workQueue', {'args': {}})[0], 401)
        self.assertNotIn('preparedDecision', self.case())

    def test_an_act_or_prepare_tool_needs_an_idempotency_key_and_runs_once_per_key(self):
        status, body, _ = self.tool('prepareDecision', message='approve 14 days', outcome='approve', days=14, requestId=self.r['id'])
        self.assertEqual((status, body['error']), (400, 'IDEMPOTENCY_REQUIRED'))
        first = self.prepare(14, 'p1')
        self.assertEqual(self.prepare(14, 'p1'), first)   # the stored result: not prepared again
        self.assertEqual(self.case()['preparedDecision']['version'], 1)
        status, body, _ = self.tool('prepareDecision', key='p1', message='approve 10 days', outcome='approve', days=10, requestId=self.r['id'])
        self.assertEqual((status, body['error']), (409, 'KEY_REUSED'))
        self.assertEqual(self.ok('workQueue')['forYou'][0]['requestId'], self.r['id'])   # a read needs no key

    def test_prepare_decision_over_the_surface_keeps_only_the_days_the_person_s_message_gives(self):
        for key, message in (('g0', None), ('g1', 'approve it')):
            missing = self.ok('prepareDecision', key=key, message=message, outcome='approve', days=10, requestId=self.r['id'])
            self.assertEqual((missing['missing'], 'prepared' in missing), ('days', False), message)
        self.assertNotIn('preparedDecision', self.case())
        p = self.ok('prepareDecision', key='g2', message='approve 10 days', outcome='approve', days=10, requestId=self.r['id'])['prepared']
        self.assertEqual((p['approvedDueDate'], p['days'], p['version']), ('2026-10-30', 10, 1))

    def test_one_key_prepares_once_when_the_same_call_arrives_while_it_runs(self):
        body = {'args': {'outcome': 'approve', 'days': 14, 'requestId': self.r['id']}, 'message': 'approve 14 days'}
        again, run = [], DeskTools.execute

        def execute(tools, name, raw):   # the same call sent again while the first runs
            if not again:
                again.append(threading.Thread(target=lambda: again.append(self.call('/api/tools/prepareDecision', body, 'owner', 'same'))))
                again[0].start()
                again[0].join(0.5)
            return run(tools, name, raw)
        with mock.patch.object(DeskTools, 'execute', execute):
            first = self.call('/api/tools/prepareDecision', body, 'owner', 'same')
        again[0].join(10)
        self.assertEqual((first[0], again[1][:2]), (200, (200, {**first[1], 'replayed': True})))   # it waited for the lock: the first one's answer, said to be a replay
        self.assertEqual([e['data']['version'] for e in self.case()['history'] if e['kind'] == 'decision.prepared'], [1])

    def test_open_request_over_the_surface_opens_one_case_per_key_from_the_person_s_own_message(self):
        status, body, _ = self.tool('openRequest', 'owner', 'o0', message=SAID, text=SAID)
        self.assertEqual((status, body['error']), (403, 'FORBIDDEN'))
        status, body, _ = self.tool('openRequest', 'staff', message=SAID, text=SAID)
        self.assertEqual((status, body['error']), (400, 'IDEMPOTENCY_REQUIRED'))
        before = len(self.app.records())
        status, body, _ = self.tool('openRequest', 'staff', 'o1', text=SAID)   # the agent's words never become a case's intake text
        self.assertEqual((status, body), (200, {'ok': False, 'error': 'MISSING', 'message': "Send the customer's message as 'message'."}))
        # a retry with the same key while the first waits for its case to be prepared: not a second case, and not an answer yet either
        retried, wait = [], App.wait_settled

        def waiting(app, request_id, timeout):
            if not retried:
                retried.append(None)
                try:
                    app.tool_call(STAFF, 'openRequest', {'args': {'text': SAID}, 'message': SAID}, 'o2')
                except APIError as error:
                    retried.append((error.status, error.code))
            return wait(app, request_id, timeout)
        with mock.patch.object(App, 'wait_settled', waiting):
            status, opened, _ = self.tool('openRequest', 'staff', 'o2', message=SAID, text=SAID)
        self.assertEqual((status, retried[1]), (200, (409, 'OPERATION_IN_PROGRESS')))
        rid = opened['result']['opened']['id']
        self.assertEqual((opened['result']['opened']['ordinal'], opened['result']['opened']['flags']), (1, []))   # the first request on DEMO-502
        self.assertEqual((len(self.app.records()), self.app.get(rid)['intake']['text']), (before + 1, SAID))
        self.assertEqual(self.tool('openRequest', 'staff', 'o2', message=SAID, text=SAID)[1], {**opened, 'replayed': True})
        status, body, _ = self.tool('openRequest', 'staff', 'o2', message=SAID + ' Thanks.', text=SAID)
        self.assertEqual((status, body['error']), (409, 'KEY_REUSED'))
        self.assertEqual(len(self.app.records()), before + 1)

    def test_a_model_that_cannot_be_reached_is_a_refusal_that_a_retry_with_the_key_can_overcome(self):
        said = 'Bayside Café is opening a second shop next month.'
        self.app.model_adapter = Unreachable()
        status, body, _ = self.tool('interpretStatement', key='m1', message=said, text=said)
        self.assertEqual((status, body['ok'], body['error']), (200, False, 'MODEL_UNAVAILABLE'))
        self.app.model_adapter = self.model
        self.assertTrue(self.ok('interpretStatement', key='m1', message=said, text=said)['reading']['lines'])

    def test_staff_case_details_carry_no_day_limit_suggestion_or_prepared_decision_and_the_owner_s_carry_all_three(self):   # Review Focus 1
        self.prepare(14, 'p1')
        staff = self.ok('caseDetails', 'staff', requestId=self.r['id'])
        self.assertEqual((staff['case']['dayLimit'], staff['case']['suggestion'], staff['case']['preparedDecision'], staff['case']['comparison']),
                         (None, None, None, None))
        for words in self.owner_only():
            self.assertNotIn(words, json.dumps(staff, ensure_ascii=False))
        self.assertEqual(staff['subject'], self.bayside_subject())
        owner = self.ok('caseDetails', requestId=self.r['id'])
        self.assertEqual((owner['case']['dayLimit']['days'], owner['case']['suggestion']['status'], owner['case']['preparedDecision']['version']),
                         (14, 'given', 1))
        self.assertIn(ANSWER, json.dumps(owner, ensure_ascii=False))

    def test_compare_extension_works_out_the_date_against_the_limit_and_writes_nothing(self):   # Review Focus 2
        self.prepare(14, 'p1')
        before = self.stored()
        for _ in range(2):
            c = self.ok('compareExtension', requestId=self.r['id'], days=10)
        self.assertEqual(self.stored(), before)   # no request, event or preparation changed
        self.assertEqual(c, {'requestId': self.r['id'], 'invoiceReference': 'DEMO-501', 'currentDue': DUE, 'currentDueText': 'Tue 20 Oct 2026',
                             'proposedDate': '2026-10-30', 'proposedDateText': display_date((calendar_date(DUE) + timedelta(days=10)).isoformat()),
                             'daysFromDue': 10, 'askedDate': '2026-11-10', 'askedDateText': 'Tue 10 Nov 2026', 'askedDays': 21, 'limitDays': 14,
                             'latestWithinLimit': '2026-11-03', 'latestWithinLimitText': 'Tue 3 Nov 2026', 'withinLimit': True,
                             'subject': self.bayside_subject()})
        beyond = self.ok('compareExtension', requestId='current', current={'requestId': self.r['id']}, date='2026-11-10')   # "current": the case given
        self.assertEqual((beyond['daysFromDue'], beyond['withinLimit'], beyond['proposedDateText']), (21, False, 'Tue 10 Nov 2026'))
        self.assertEqual(self.refused('compareExtension', requestId=self.r['id']), 'MISSING')
        self.assertEqual(self.refused('compareExtension', requestId=self.r['id'], days=3, date='2026-11-10'), 'INVALID_ARGUMENT')
        self.assertEqual(self.refused('compareExtension', requestId=self.r['id'], date='2026-10-01'), 'INVALID_ARGUMENT')   # not after the due date
        self.assertEqual(self.stored(), before)

    def test_staff_compare_without_the_owner_s_limit_unless_the_owner_shared_one(self):
        s = self.ok('compareExtension', 'staff', requestId=self.r['id'], days=10)
        self.assertEqual((s['proposedDateText'], s['daysFromDue'], s['askedDays']), ('Fri 30 Oct 2026', 10, 21))
        self.assertEqual((s['limitDays'], s['latestWithinLimit'], s['latestWithinLimitText'], s['withinLimit']), (None, None, None, None))
        self.assertNotIn(ANSWER, json.dumps(s))
        self.tell('I would allow Bayside Café up to 20 days.', 'limit', visibility='staff')
        s = self.ok('compareExtension', 'staff', requestId=self.r['id'], days=10)
        self.assertEqual((s['limitDays'], s['withinLimit']), (20, True))

    def test_withdraw_preparation_clears_only_the_current_one_and_is_not_a_decline(self):   # Review Focus 2
        self.assertEqual(self.ok('withdrawPreparation', key='w0', requestId=self.r['id']),
                         {'requestId': self.r['id'], 'invoiceReference': 'DEMO-501', 'withdrawn': False, 'note': 'Nothing was prepared.', 'subject': self.bayside_subject()})
        p = self.prepare(14, 'p1')
        status, body, _ = self.tool('withdrawPreparation', 'staff', 'ws', requestId=self.r['id'])
        self.assertEqual((status, body['error']), (403, 'FORBIDDEN'))
        done = self.ok('withdrawPreparation', key='w1', requestId=self.r['id'], version=1)
        self.assertEqual((done['withdrawn'], done['version'], done['invoiceReference']), (True, 1, 'DEMO-501'))   # the reply names the case by it
        c = self.case()
        self.assertEqual((c['status'], c['decision'], 'preparedDecision' in c), ('awaiting_owner', None, False))
        self.assertIsNone(self.situation('owner')['case']['preparedDecision'])
        self.assertEqual([e['data']['version'] for e in c['history'] if e['kind'] == 'decision.withdrawn'], [1])
        self.assertNotIn('decision.withdrawn', json.dumps(self.case('staff')))
        self.assertEqual(self.ok('withdrawPreparation', key='w1', requestId=self.r['id'], version=1), done)   # the same key: the stored result
        self.assertEqual(self.ok('withdrawPreparation', key='w1b', requestId=self.r['id'], version=1),   # withdrawn already
                         {'requestId': self.r['id'], 'invoiceReference': 'DEMO-501', 'withdrawn': False, 'note': 'No prepared decision is waiting.', 'subject': self.bayside_subject()})
        # a withdrawn preparation cannot be confirmed
        confirm = {'expectedRequestVersion': c['version'], 'analysisId': c['analysis']['id'], 'evidenceVersion': c['analysis']['snapshot']['evidenceVersion'],
                   'outcome': 'approve', 'approvedDueDate': p['approvedDueDate'], 'reason': p['reason'], 'preparedVersion': 1}
        status, body, _ = self.call('/api/requests/' + self.r['id'] + '/decisions', confirm, 'owner', 'c1')
        self.assertEqual((status, body['error']), (409, 'STALE_PREPARATION'))
        # a version that is not the current one is STALE, and the current one stays
        self.assertEqual(self.prepare(10, 'p2')['version'], 2)
        self.assertEqual(self.refused('withdrawPreparation', key='w2', requestId='DEMO-501', version=1), 'STALE')
        self.assertEqual(self.case()['preparedDecision']['version'], 2)
        self.assertEqual([e['data']['version'] for e in self.case()['history'] if e['kind'] == 'decision.withdrawn'], [1])
        self.assertIsNone(self.case()['decision'])

    def test_the_work_queue_says_who_acts_next_on_every_customer_s_cases(self):
        other = self.second_case()
        staff = self.ok('workQueue', 'staff')
        self.assertEqual(staff['forYou'], [])
        self.assertEqual(sorted(x['requestId'] for x in staff['waitingOnOthers']), sorted([self.r['id'], other['id']]))
        self.assertEqual({(x['waitingOn'], x['statusLabel'], x['status']) for x in staff['waitingOnOthers']}, {('owner', 'With the owner', 'awaiting_owner')})
        row = next(x for x in staff['waitingOnOthers'] if x['requestId'] == self.r['id'])
        self.assertEqual({k: row[k] for k in ('invoiceReference', 'customer', 'askedDateText', 'link')},
                         {'invoiceReference': 'DEMO-501', 'customer': self.bayside_subject(), 'askedDateText': 'Tue 10 Nov 2026', 'link': '#/case/' + self.r['id']})
        self.assertTrue(row['why'])
        owner = self.ok('workQueue')
        self.assertEqual(sorted(x['requestId'] for x in owner['forYou']), sorted([self.r['id'], other['id']]))
        self.assertEqual(({x['waitingOn'] for x in owner['forYou']}, owner['waitingOnOthers'], owner['subject']), ({'you'}, [], None))
        # in words, by code: what waits for this person, then on whom the rest wait, each invoice with its customer
        for text, start, end in ((owner['summaryText'], '2 cases need your decision: ', '. Nothing is waiting on others.'),
                                 (staff['summaryText'], 'Nothing is waiting for you. 2 cases are with the owner: ', '.')):
            self.assertTrue(text.startswith(start) and text.endswith(end), text)
            self.assertEqual(sorted(text[len(start):-len(end)].split(', ')), ['DEMO-501 (Bayside Café)', 'DEMO-502 (Bayside Café)'], text)
        self.assertIn('asOfText', owner)
        for words in self.owner_only():   # staff's queue and list repeat nothing the owner kept for themselves
            self.assertNotIn(words, json.dumps(staff, ensure_ascii=False))
            self.assertNotIn(words, json.dumps(self.ok('listRequests', 'staff', status='all'), ensure_ascii=False))

    def test_list_requests_filters_by_status_customer_and_invoice(self):
        other = self.second_case()
        c = self.case()
        decision = {'expectedRequestVersion': c['version'], 'analysisId': c['analysis']['id'], 'evidenceVersion': c['analysis']['snapshot']['evidenceVersion'],
                    'outcome': 'approve', 'approvedDueDate': '2026-11-03', 'reason': 'This invoice only.'}
        self.assertEqual(self.call('/api/requests/' + self.r['id'] + '/decisions', decision, 'owner', 'd1')[0], 201)
        self.wait_status(self.r, ('completed',))
        decided = self.ok('listRequests', status='decided')
        self.assertEqual(([x['id'] for x in decided['requests']], decided['requests'][0]['waitingOn'], decided['subject']), ([self.r['id']], 'none', None))
        self.assertEqual(decided['requests'][0]['approvedDueDateText'], 'Tue 3 Nov 2026')
        opened = self.ok('listRequests', 'staff', customerId=self.bayside['id'])   # open by default
        self.assertEqual(([x['id'] for x in opened['requests']], opened['requests'][0]['waitingOn'], opened['subject']), ([other['id']], 'owner', self.bayside_subject()))
        self.assertEqual([x['id'] for x in self.ok('listRequests', invoiceReference='DEMO-502', status='all')['requests']], [other['id']])
        self.assertEqual(sorted(x['id'] for x in self.ok('listRequests', status='all')['requests']), sorted([self.r['id'], other['id']]))
        self.assertEqual(self.refused('listRequests', status='closed'), 'INVALID_ARGUMENT')

    def test_a_holding_message_names_the_invoice_where_it_stands_and_the_due_date_and_promises_no_amount(self):
        before = self.stored()
        h = self.ok('prepareHoldingMessage', 'staff', key='h1', requestId=self.r['id'])
        for words in ('DEMO-501', 'with the owner', 'Tue 20 Oct 2026'):
            self.assertIn(words, h['text'])
        self.assertIsNone(AMOUNT.search(h['text']))
        self.assertEqual((h['status'], h['subject']), ('awaiting_owner', self.bayside_subject()))
        self.assertEqual(self.stored(), before)   # nothing is kept on the case

    def test_a_model_calling_tool_is_run_through_the_adapter_and_keeps_nothing(self):
        said = 'Bayside Café is opening a second shop next month.'
        before = len(self.app.statements())
        reading = self.ok('interpretStatement', key='i1', message=said, text=said)['reading']
        self.assertEqual(reading['customerQuery'], 'Bayside Café')
        self.assertTrue(reading['lines'])
        self.assertEqual(len(self.app.statements()), before)


class StaleCurrentTests(SituationCase):
    """"current" is a hint: a customer or case that is gone (the records were reset) is dropped and said, not refused."""
    GONE_C = 'The customer this conversation focused on is no longer in the records.'
    GONE_R = 'The case this conversation focused on is no longer in the records.'

    def run_tool(self, name, current, **args):
        status, body, _ = self.call('/api/tools/' + name, {'args': args, 'current': current}, 'owner', None)
        self.assertEqual((status, body.get('ok')), (200, True), body)
        return body['result']

    def test_stale_current_runs_the_tool_with_a_note(self):
        for name, args in (('workQueue', {}), ('findCustomers', {'query': 'Bayside'}), ('listRequests', {'status': 'all'}), ('invoices', {'customerId': self.r['customerId'], 'which': 'all'})):
            with self.subTest(name):
                r = self.run_tool(name, {'customerId': 'cust_gone', 'requestId': 'req_gone'}, **args)
                self.assertEqual(r['notes'], [self.GONE_C, self.GONE_R])

    def test_current_that_exists_still_focuses(self):
        r = self.run_tool('invoices', {'customerId': self.r['customerId']}, customerId='current', which='all')
        self.assertNotIn('notes', r)

    def test_stale_current_customer_refusal_says_so(self):
        status, body, _ = self.call('/api/tools/invoices', {'args': {'customerId': 'current', 'which': 'all'}, 'current': {'customerId': 'cust_gone'}}, 'owner', None)
        self.assertEqual((status, body['ok']), (200, False), body)
        self.assertTrue(body['message'].startswith('There is no current customer.'), body)
        self.assertEqual(body['notes'], [self.GONE_C])

    def test_valid_current_request_still_focuses_the_case(self):
        r = self.run_tool('caseDetails', {'requestId': self.r['id']}, requestId='current')
        self.assertNotIn('notes', r)



if __name__ == '__main__':
    unittest.main()
