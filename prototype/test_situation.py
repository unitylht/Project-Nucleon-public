"""The shared situation: one role-filtered picture of a case and its customer, built by App.situation and returned by caseDetails
for any case; context in a case includes the case's own lines. All data is fictional. No real model is called: the mock stands in
for it, and test adapters record what it was sent."""
import json
import unittest

from agent import display_date
from test_case_coordinator import ANSWER
from test_helpers import NAMED, SHARED, Recording, tell_owner
from server import dated
from test_records import RecordsCase

REQUEST = 'Could we pay invoice DEMO-501 on 2026-11-10 instead?'   # due 20 Oct: 21 days asked


class SituationCase(RecordsCase):
    """Bayside Café with DEMO-501 and DEMO-502 due 20 Oct, suggestions on, the owner's context (kept and shared), and a case for
    DEMO-501 asking 21 days whose question the owner answered "Up to 14 days this time": suggestion version 2, approve to 3 Nov."""
    def setUp(self):
        super().setUp()
        self.model = Recording()
        self.start(self.model, 'live')
        self.practice_ready()
        self.bayside = self.add_customer('Bayside Café')
        for reference in ('DEMO-501', 'DEMO-502'):
            self.add_invoice(self.bayside, reference, dueDate='2026-10-20', stillOwed='1200.00', stillOwedAsOf='2026-10-16')
        self.assertEqual(self.call('/api/suggestions', {'on': True}, 'owner')[0], 200)
        self.private = [x['quote'] for x in self.tell(NAMED, 'n')['lines']]   # kept for the owner
        [self.shared] = [x['quote'] for x in self.tell(SHARED, 's', visibility='staff')['lines']]
        r = self.wait_status(self.create(REQUEST), ('awaiting_owner',))
        [q] = self.call('/api/requests/' + r['id'], role='owner')[1]['analysis']['brief']['questions']   # the guidance is unclear: one question
        self.question = q['question']
        status, view, _ = self.call('/api/requests/' + r['id'] + '/questions/' + q['id'] + '/answer', {'text': ANSWER}, 'owner', 'a1')
        self.assertEqual(status, 200, view)
        self.r = r
        self.answer_line = next(x['id'] for s in self.app.statements() for x in s['lines'] if x['quote'] == ANSWER)
        self.assertEqual(self.situation('owner')['case']['suggestion']['status'], 'given')

    def tell(self, text, key, **confirm):
        return tell_owner(self, text, key, **confirm)

    def tool(self, name, role='owner', key=None, message=None, current=None, **args):
        """One call to POST api/tools/<name>, as the AI Agent's session makes it."""
        body = {'args': args, **({'message': message} if message is not None else {}), **({'current': current} if current else {})}
        return self.call('/api/tools/' + name, body, role, key)

    def ok(self, name, role='owner', key=None, **kw):
        status, body, _ = self.tool(name, role, key, **kw)
        self.assertEqual((status, body.get('ok')), (200, True), body)
        self.assertEqual(set(body) - {'replayed'}, {'ok', 'result'})   # a retry of a once-per-key tool says replayed beside the result
        return body['result']

    def refused(self, name, role='owner', key=None, **kw):
        status, body, _ = self.tool(name, role, key, **kw)
        self.assertEqual((status, body.get('ok')), (200, False), body)
        return body['error']

    def situation(self, role, request_id=None):
        with self.app.lock:
            return self.app.situation(role, request_id=request_id or self.r['id'])

    def owner_only(self):
        return self.private + [ANSWER, self.question, 'A shorter extension than asked']


class SituationTests(SituationCase):
    def test_the_owner_situation_holds_the_case_line_the_limit_the_comparison_and_the_suggestion(self):
        s = self.situation('owner')
        case, customer = s['case'], s['customer']
        self.assertEqual((case['requestId'], case['status'], case['label'], case['customer'], case['invoice']['reference']),
                         (self.r['id'], 'awaiting_owner', 'Needs your decision', 'Bayside Café', 'DEMO-501'))
        self.assertEqual((case['askedDate'], case['currentDue'], case['extensionDays']), ('2026-11-10', '2026-10-20', 21))
        self.assertEqual((case['invoice']['amountText'], case['invoice']['mark']), ('AUD 1,200.00 (stated as of Fri 16 Oct)', 'stated'))
        line = next(x for x in case['contextLines'] if x['quote'] == ANSWER)
        self.assertEqual((line['scope'], line['by'], line['source'], line['saidOn']), ('case', 'owner', 'answer', '2026-10-18'))
        self.assertEqual(sorted(x['quote'] for x in case['contextLines']), sorted(self.private + [self.shared, ANSWER]))
        self.assertEqual(case['dayLimit'], {'days': 14, 'fromLineId': self.answer_line, 'latestDate': '2026-11-03'})
        self.assertEqual(case['comparison'], {'askedDays': 21, 'limitDays': 14, 'withinLimit': False})
        [q] = case['questions']
        self.assertEqual((q['question'], q['status'], q['answer']), (self.question, 'answered', ANSWER))
        sug = case['suggestion']
        self.assertEqual((sug['version'], sug['status'], sug['outcome'], sug['approvedDueDate'], sug['sentence'], sug['withheldBecause']),
                         (2, 'given', 'approve', '2026-11-03', 'A shorter extension than asked, within the days you allowed.', []))
        self.assertIn('"' + ANSWER + '"', sug['cites'])
        self.assertEqual((case['decision'], case['replyDraft'], case['preparedDecision'], case['priorDecisions']), (None, None, None, []))
        self.assertEqual((customer['name'], customer['openCount'], [x['requestId'] for x in customer['openCases']]), ('Bayside Café', 2, [self.r['id']]))
        self.assertEqual([a['id'] for a in s['actions']], ['decide', 'prepare_decision', 'request_suggestion', 'add_context'])

    def test_the_staff_situation_is_what_the_staff_case_view_shows_and_holds_nothing_owner_only(self):
        s, c = self.situation('staff'), self.situation('staff')['case']
        view = self.call('/api/requests/' + self.r['id'], role='staff')[1]
        with self.app.lock:
            context = self.app.context_for(self.r['customerId'], 'staff', self.r['id'])
        facts = view['analysis']['snapshot']['facts']
        self.assertEqual((c['askedDate'], c['currentDue'], c['extensionDays'], c['label']),
                         (facts['requestedDueDate'], facts['currentEffectiveDueDate'], facts['extensionDays'], 'With the owner'))
        self.assertEqual([x['quote'] for x in c['contextLines']], [x['quote'] for x in context['lines']])
        self.assertEqual([x['quote'] for x in c['contextLines']], [self.shared])
        self.assertEqual(([q['question'] for q in c['questions']], [q['question'] for q in view['analysis']['brief']['questions']]), ([], []))
        self.assertEqual((c['suggestion'], c['preparedDecision'], c['dayLimit'], c['comparison']), (None, None, None, None))
        for quote in self.owner_only():
            self.assertNotIn(quote, json.dumps(s, ensure_ascii=False))
        # the agent reads exactly what the situation holds: caseDetails, with each date's words beside it
        details = self.ok('caseDetails', 'staff', requestId='current', current={'requestId': self.r['id']})
        self.assertEqual((details['case'], details['customer']), (dated(c), dated(s['customer'])))
        cases = self.ok('cases', 'staff', reference='DEMO-501')
        self.assertEqual(cases['cases'][0]['summary'], 'Invoice DEMO-501 for Bayside Café: With the owner. Asked to pay on Tue 10 Nov 2026.')
        shared = self.ok('ownerContext', 'staff', customerId='current', current={'customerId': self.bayside['id'], 'requestId': self.r['id']})   # shared lines only
        self.assertEqual([x['quote'] for x in shared['lines']], [self.shared])
        payloads = json.dumps([details, cases, shared], ensure_ascii=False)
        for quote in self.owner_only():
            self.assertNotIn(quote, payloads)

    def test_case_details_current_returns_the_situation_of_the_case_given_and_an_id_works_anywhere(self):
        s = self.situation('owner')
        details = self.ok('caseDetails', requestId='current', current={'requestId': self.r['id']})
        self.assertEqual((details['case'], details['customer']), (dated(s['case']), dated(s['customer'])))
        # with no case given "current" names none; an id from cases works anywhere, and an unknown one is refused
        self.assertEqual(self.refused('caseDetails', requestId='current'), 'INVALID_ARGUMENT')
        self.assertEqual(self.ok('caseDetails', requestId=self.r['id'])['case'], dated(s['case']))
        self.assertEqual(self.refused('caseDetails', requestId='req_nowhere'), 'INVALID_ARGUMENT')
        # a case whose invoice and customer are not identified yet: no invoice, no customer, nothing worked out
        other = self.wait_status(self.create('Could we pay invoice DEMO-999 on 2026-11-10 instead?', key='intake-2'))
        details = self.ok('caseDetails', requestId=other['id'])
        self.assertEqual((details['case']['status'], details['case']['invoice'], details['customer'], details['case']['dayLimit']),
                         ('needs_information', None, None, None))

    def test_a_case_is_named_by_its_invoice_reference_as_the_situation_shows_it(self):
        s = self.situation('owner')
        by_ref, lower = self.ok('caseDetails', requestId='DEMO-501'), self.ok('caseDetails', requestId='demo-501')
        self.assertEqual((by_ref['case'], lower['case']), (dated(s['case']), dated(s['case'])))
        self.assertFalse(self.tool('caseDetails', requestId='DEMO-999')[1]['ok'])

    def test_a_string_shaped_like_a_date_that_is_no_date_gets_no_words(self):
        self.assertEqual(dated({'reference': '2026-02-30', 'dueDate': '2026-03-01', 'lines': [{'until': '2026-13-01'}]}),
                         {'reference': '2026-02-30', 'dueDate': '2026-03-01', 'dueDateText': 'Sun 1 Mar 2026', 'lines': [{'until': '2026-13-01'}]})
        result = self.ok('cases', reference='2026-02-30')   # no error: no request has that reference
        self.assertEqual((result['reference'], result['caseCount'], 'referenceText' in result), ('2026-02-30', 0, False))

    def test_a_reread_after_a_preparation_shows_it(self):
        before = self.ok('caseDetails', requestId=self.r['id'])
        self.ok('prepareDecision', key='p1', message='approve 14 days, then', outcome='approve', days=14, requestId=self.r['id'])
        after = self.ok('caseDetails', requestId=self.r['id'])
        self.assertEqual((before['case']['preparedDecision'], after['case']['preparedDecision']['approvedDueDate']), (None, '2026-11-03'))

    def test_results_give_each_date_in_the_page_s_words_beside_its_iso_form(self):
        current = {'customerId': self.bayside['id'], 'requestId': self.r['id']}
        details = self.ok('caseDetails', requestId='current', current=current)
        context = self.ok('ownerContext', customerId='current', current=current)
        prepared = self.ok('prepareDecision', key='p1', message='approve 14 days, then', outcome='approve', days=14, requestId='current', current=current)
        case = details['case']
        self.assertEqual((case['askedDateText'], case['currentDueText'], case['dayLimit']['latestDateText'], details['customer']['invoices'][0]['dueDateText']),
                         ('Tue 10 Nov 2026', 'Tue 20 Oct 2026', 'Tue 3 Nov 2026', 'Tue 20 Oct 2026'))
        lines = case['contextLines'] + context['lines']
        self.assertTrue(lines and all(x['saidOnText'] == display_date(x['saidOn']) for x in lines))
        ended = [x for x in lines if x['until']]
        self.assertTrue(ended and all(x['untilText'] == display_date(x['until']) for x in ended))
        self.assertTrue(all('untilText' not in x for x in lines if not x['until']))   # no date, no words
        self.assertEqual((prepared['prepared']['approvedDueDateText'], prepared['prepared']['askedDateText']), ('Tue 3 Nov 2026', 'Tue 10 Nov 2026'))
        self.assertTrue(self.ok('cases', customerId=self.bayside['id'])['cases'])

    def test_context_for_a_case_includes_its_own_line_and_another_customer_s_never_takes_it(self):
        current = {'customerId': self.bayside['id'], 'requestId': self.r['id']}
        own = self.ok('ownerContext', customerId='current', current=current)
        self.assertIn(ANSWER, [x['quote'] for x in own['lines']])
        coastline = self.add_customer('Coastline Foods')
        bayside = self.ok('ownerContext', customerId=self.bayside['id'], requestId=self.r['id'])   # by the case's id, with no current case
        other = self.ok('ownerContext', customerId=coastline['id'], requestId=self.r['id'])
        self.assertIn(ANSWER, [x['quote'] for x in bayside['lines']])
        self.assertEqual(other['lines'], [])
        self.assertNotIn(ANSWER, [x['quote'] for x in self.ok('ownerContext', customerId=self.bayside['id'])['lines']])   # without the case: the customer's own

    def test_a_decided_case_s_situation_carries_its_label_and_the_decision_s_day_only(self):
        s = self.situation('owner')['case']
        body = {'expectedRequestVersion': self.r['version'], 'analysisId': self.r['analysis']['id'],
                'evidenceVersion': self.r['analysis']['snapshot']['evidenceVersion'], 'outcome': 'approve', 'approvedDueDate': '2026-11-03',
                'reason': 'This invoice only.', 'suggestionShown': {k: s['suggestion'][k] for k in ('version', 'outcome', 'approvedDueDate')}}
        self.assertEqual(self.call('/api/requests/' + self.r['id'] + '/decisions', body, 'owner', 'd1')[0], 201)
        self.wait_status(self.r, ('completed',))
        decided = self.situation('owner')['case']
        stamp = self.call('/api/requests/' + self.r['id'], role='owner')[1]['decision']['decidedAt']   # the real clock's time; the situation keeps its day only
        self.assertEqual((decided['label'], decided['decision']['decidedOn'], 'decidedAt' in decided['decision'], decided['replyDraft'] is not None),
                         ('Approved to Tue 3 Nov', stamp[:10], False, True))


class FreshWorkspaceTests(RecordsCase):
    def test_the_tools_say_there_are_no_records_before_and_right_after_workspace_setup(self):
        self.start()
        for step in ('before', 'after'):
            if step == 'after':
                self.setup_workspace('practice')   # no settings yet, so no records to work anything out from
            for role in ('owner', 'staff'):
                status, body, _ = self.call('/api/tools/workQueue', {'args': {}}, role)
                self.assertEqual((status, body['error']), (409, 'NO_RECORDS'), (step, role, body))
                with self.app.lock:
                    s = self.app.situation(role)
                self.assertEqual((s['case'], s['customer'], s['actions']), (None, None, []))


if __name__ == '__main__':
    unittest.main()
