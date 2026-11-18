"""The coordinator in the case flow: what a case still needs, asked of the owner with its reason and answered once, and the
brief-v3 fields. All data is fictional. No real model is called."""
import json
import unittest

from agent import MockAdapter
from coordinator import NEEDS_FAILED, STAFF_MOVED
from model_adapter import AdapterError, AdapterResult
from test_helpers import NAMED, tell_owner
from test_records import RecordsCase

GUIDANCE = 'I would consider a small extension'
QUESTION = 'You said "' + GUIDANCE + '". Is 21 days acceptable here?'   # due 20 Oct, asked for 10 Nov
ANSWER = 'Up to 14 days this time'
DOWNGRADED = 'Marked as needed to calculate, but code found no blocking condition left for it, so it is needed to suggest only.'


class CalculateNeed(MockAdapter):
    """The mock, except that planning returns a need the model calls 'calculate' although the records are complete."""
    def respond(self, task, messages, tools=None, schema=None, timeout=None):
        if task == 'plan_needs':
            return AdapterResult('structured_output', meta={'latencyMs': 0}, value={'needs': [{
                'need': 'Which allocation is right', 'why': 'Needed to calculate the amount still owed.', 'from': 'staff',
                'kind': 'calculate', 'answeredBy': None, 'question': 'Which allocation of the payments is right?'}]})
        return super().respond(task, messages, tools, schema, timeout)


class StaffNeed(MockAdapter):
    """The mock's needs plus one 'calculate' need asked of staff, as a model may ask when the records stop the calculation. The
    mock never asks one itself: the facts it is given do not say that the records contradict each other."""
    question = 'Which of the payment and invoice records for this invoice are right?'

    def respond(self, task, messages, tools=None, schema=None, timeout=None):
        result = super().respond(task, messages, tools, schema, timeout)
        if task == 'plan_needs':
            result.value['needs'].append({'need': 'Which records are right', 'why': 'Needed to calculate the amount still owed.', 'from': 'staff',
                                          'kind': 'calculate', 'answeredBy': None, 'question': self.question})
        return result


class StaffNeedQuotingTheOwner(StaffNeed):
    question = 'The owner said "' + GUIDANCE + '". Which records are right?'


class NeedsUnreachable(MockAdapter):
    def respond(self, task, messages, tools=None, schema=None, timeout=None):
        if task == 'plan_needs':
            raise AdapterError('timeout', 'the needs step timed out')
        return super().respond(task, messages, tools, schema, timeout)


class CaseCoordinatorTests(RecordsCase):
    def ready(self, adapter=None, mode='mock'):
        self.start(adapter, mode)
        self.practice_ready()
        c = self.add_customer('Bayside Café')
        for reference in ('DEMO-501', 'DEMO-502'):
            self.add_invoice(c, reference, dueDate='2026-10-20')
        return c

    def tell(self, text=NAMED):
        """The owner's paragraph about Bayside, kept as a confirmed statement; its guidance line is undefined ("small")."""
        return tell_owner(self, text, 'say')

    def conflict(self, adapter=None, mode='mock'):
        """Bayside's DEMO-501 with records that contradict each other (as in test_balances): paid in full on 5 Oct, yet 400.00
        stated still owed on 9 Oct with that payment reflected. Code finds records_conflict, so one need may be asked of staff."""
        self.start(adapter, mode)
        self.practice_ready()
        c = self.add_customer('Bayside Café')
        invoice = self.add_invoice(c, 'DEMO-501', dueDate='2026-10-20', total='1000.00', stillOwed='400.00', stillOwedAsOf='2026-10-09')
        status, paid, _ = self.call('/api/records/payments', {'customerId': c['id'], 'receivedDate': '2026-10-05', 'amount': '1000.00'}, 'staff', 'pay')
        self.assertEqual(status, 200, paid)
        body = {'paymentId': paid['record']['id'], 'allocations': [{'invoiceId': invoice['id'], 'amount': '1000.00'}]}
        self.assertEqual(self.call('/api/records/allocations', body, 'staff', 'allocate')[0], 200)
        allocation = next(a for a in self.app.fixture()['allocations'] if a['paymentId'] == paid['record']['id'])
        self.assertEqual(self.call('/api/records/allocations/' + allocation['id'] + '/statement', {'status': 'included'}, 'staff', 'included')[0], 200)
        return c

    def case(self, reference='DEMO-501', key='intake-1'):
        r = self.wait_status(self.create('Could we pay invoice ' + reference + ' on 2026-11-10 instead?', key=key), ('awaiting_owner',))
        return self.call('/api/requests/' + r['id'], role='owner')[1]

    def question(self, r, action, body, role='owner', key='q1', index=0):
        q = r['analysis']['brief']['questions'][index]
        return self.call('/api/requests/' + r['id'] + '/questions/' + q['id'] + '/' + action, body, role, key)

    def test_a_case_with_undefined_guidance_gets_one_owner_question_with_its_reason(self):
        self.ready()
        s = self.tell()
        r = self.case()
        brief = r['analysis']['brief']
        [q] = brief['questions']
        self.assertEqual((brief['format'], r['status'], q['kind'], q['from'], q['status'], q['answeredBy'], q['question']),
                         ('brief-v3', 'awaiting_owner', 'recommend', 'owner', 'open', None, QUESTION))
        self.assertTrue(q['why'].strip())
        self.assertEqual((brief['suggestion'], brief['suggestionStatus']), (None, 'off'))
        self.assertEqual(brief['contextShown'], [x['id'] for x in s['lines']])   # what the model was given
        self.assertEqual([x['quote'] for x in r['context']['lines']], [x['quote'] for x in s['lines']])   # live, for the owner
        self.assertEqual((r['analysis']['stats']['needsModelCalls'], r['task']['kind'], r['task']['status']), (1, 'approval', 'pending'))
        self.assertEqual(self.decide(r, approved='2026-11-10')[0], 201)   # the decision controls stay: a question never blocks

    def test_no_owner_notes_is_listed_unless_this_role_can_see_confirmed_context(self):
        self.ready()
        r = self.case()

        def listed():   # whether each role is told there are no owner notes, as each sees the case now
            return tuple('no_owner_notes' in [i['kind'] for i in self.call('/api/requests/' + r['id'], role=role)[1]['analysis']['brief']['openItems']]
                         for role in ('owner', 'staff'))
        self.assertEqual(listed(), (True, True))
        status, body, _ = self.call('/api/tools/interpretStatement', {'args': {'text': NAMED}, 'message': NAMED}, 'owner', 'read')
        self.assertEqual((status, body['ok']), (200, True), body)
        self.assertEqual(listed(), (True, True))   # read, not kept: nothing is said until the owner's words are stored as confirmed
        tell_owner(self, NAMED, 'say')
        self.assertEqual(listed(), (False, True))   # kept for the owner: staff cannot tell that it exists
        tell_owner(self, 'Bayside Café pays on Fridays.', 'say2', visibility='staff')
        self.assertEqual(listed(), (False, False))   # shared with staff

    def test_answering_stores_a_case_scoped_line_and_marks_the_question_answered(self):
        self.ready()
        self.tell()
        r = self.case()
        for bad in ({'text': ' '}, {'text': 'x' * 501}, {'text': ANSWER, 'keepForCustomer': 'yes'}):
            self.assertEqual(self.question(r, 'answer', bad, key='bad' + str(len(json.dumps(bad))))[0], 400)
        status, view, _ = self.question(r, 'answer', {'text': ANSWER})
        self.assertEqual(status, 200, view)
        [q] = view['analysis']['brief']['questions']
        s = self.app.statements()[-1]
        self.assertEqual((s['text'], s['status'], s['visibility'], s['scope'], s['source'], [(x['kind'], x['quote']) for x in s['lines']]),
                         (ANSWER, 'confirmed', 'owner', {'kind': 'case', 'requestId': r['id']}, {'kind': 'answer', 'questionId': q['id']},
                          [('guidance', ANSWER)]))
        self.assertEqual((q['status'], q['answeredBy']), ('answered', s['lines'][0]['id']))
        self.assertEqual(view['context']['lines'][-1]['id'], s['lines'][0]['id'])
        self.assertEqual((view['version'], view['status'], view['analysis']['id']), (r['version'], 'awaiting_owner', r['analysis']['id']))
        self.assertEqual([e['data'] for e in view['history'] if e['kind'] == 'question.answered'], [{'questionId': q['id'], 'from': 'owner'}])
        self.assertEqual(self.question(r, 'answer', {'text': ANSWER})[:2], (200, view))   # a retry: the same result, stored once
        self.assertEqual(len(self.app.statements()), 2)
        self.assertEqual(self.question(r, 'answer', {'text': 'Fine'}, key='q2')[0], 409)   # answered once
        staff = self.reopen(r)   # no trace of the question for staff: not its event, its id, its wording or the answer
        for trace in (q['id'], 'question.answered', GUIDANCE, ANSWER):
            self.assertNotIn(trace, json.dumps(staff))
        self.assertEqual([x for x in staff['analysis']['brief']['openItems'] if 'step' in x], [])
        self.assertEqual(self.decide(view, approved='2026-11-03')[0], 201)   # the evidence version is untouched by the answer

    def test_a_case_scoped_answer_is_not_reused_on_another_case(self):
        self.ready()
        self.tell()
        self.question(self.case(), 'answer', {'text': ANSWER})
        second = self.case('DEMO-502', 'intake-2')
        [q] = second['analysis']['brief']['questions']
        self.assertEqual((q['status'], q['answeredBy'], q['question']), ('open', None, QUESTION))
        self.assertNotIn(ANSWER, json.dumps(second['context']))
        status, view, _ = self.question(second, 'skip', {}, key='q2')
        self.assertEqual((status, view['analysis']['brief']['questions'][0]['status'], view['version']), (200, 'skipped', second['version']))
        self.assertEqual([e['data'] for e in view['history'] if e['kind'] == 'question.skipped'], [{'questionId': q['id'], 'from': 'owner'}])
        self.assertNotIn(q['id'], json.dumps(self.reopen(second)))   # nor of a skipped one

    def test_keep_for_customer_makes_the_answer_reusable(self):
        c = self.ready()
        self.tell()
        self.question(self.case(), 'answer', {'text': ANSWER, 'keepForCustomer': True})
        s = self.app.statements()[-1]
        self.assertEqual(s['scope'], {'kind': 'customer', 'customerId': c['id']})
        second = self.case('DEMO-502', 'intake-2')
        [q] = second['analysis']['brief']['questions']
        self.assertEqual((q['status'], q['answeredBy'], q['question']), ('answered', s['lines'][0]['id'], QUESTION))   # already known
        self.assertIn(s['lines'][0]['id'], second['analysis']['brief']['contextShown'])

    def test_a_calculate_need_the_code_does_not_recognise_cannot_block(self):
        self.ready(CalculateNeed(), 'live')
        r = self.case()
        [q] = r['analysis']['brief']['questions']
        self.assertEqual((r['status'], q['kind'], q['from'], q['status'], q['checks']), ('awaiting_owner', 'recommend', 'owner', 'open', [DOWNGRADED]))
        self.assertEqual(self.decide(r, approved='2026-11-10')[0], 201)
        self.assertEqual(self.question(r, 'skip', {})[0], 409)   # decided: nothing is waiting for the owner

    def test_when_the_needs_step_fails_the_case_is_prepared_without_questions(self):
        self.ready(NeedsUnreachable(), 'live')
        self.tell()
        r = self.case()
        brief = r['analysis']['brief']
        self.assertEqual((r['status'], r['analysis']['aiStatus'], brief['questions']), ('awaiting_owner', 'live', []))
        self.assertIn({'kind': 'code_check', 'text': NEEDS_FAILED, 'step': 'needs'}, brief['openItems'])
        self.assertNotIn(NEEDS_FAILED, json.dumps(self.reopen(r)))   # the needs step's checks are the owner's, like its questions

    def test_staff_cannot_answer_owner_questions(self):
        self.ready()
        self.tell()
        r = self.case()
        self.assertEqual(self.question(r, 'answer', {'text': 'Fine'}, 'staff')[0], 403)
        self.assertEqual(self.question(r, 'skip', {}, 'staff', 'q2')[0], 403)
        self.assertEqual(self.app.statements()[-1]['source']['kind'], 'turn')   # nothing stored
        staff = self.reopen(r)
        brief = staff['analysis']['brief']
        self.assertEqual((brief['questions'], brief['contextShown'], staff['context']), ([], [], {'lines': [], 'decisions': []}))
        self.assertNotIn(GUIDANCE, json.dumps(staff))   # the owner's words, quoted in the question, stay with the owner

    def test_staff_see_and_answer_the_question_asked_of_them_and_no_other(self):
        self.conflict(StaffNeed(), 'live')
        self.tell()
        r = self.case()
        mine, theirs = r['analysis']['brief']['questions']
        self.assertEqual([(q['kind'], q['from'], q['status']) for q in (mine, theirs)], [('recommend', 'owner', 'open'), ('calculate', 'staff', 'open')])
        staff = self.reopen(r)
        self.assertEqual(staff['analysis']['brief']['questions'],
                         [{k: theirs[k] for k in ('id', 'kind', 'from', 'question', 'why', 'status', 'answeredBy')}])
        self.assertEqual(staff['analysis']['brief']['contextShown'], [])
        for trace in (mine['id'], GUIDANCE):   # the owner's question, here or in the briefs kept in the activity
            self.assertNotIn(trace, json.dumps(staff))
        self.assertEqual(self.question(staff, 'skip', {}, 'staff', 'q0')[0], 403)   # deciding without it is the owner's
        status, view, _ = self.question(staff, 'answer', {'text': 'The 5 Oct payment was for DEMO-502', 'keepForCustomer': True}, 'staff')
        self.assertEqual(status, 200, view)
        s = self.app.statements()[-1]
        self.assertEqual((s['status'], s['visibility'], s['scope'], s['source'], s['saidBy'], s['role'], [(x['kind'], x['quote']) for x in s['lines']]),
                         ('proposed', 'staff', {'kind': 'case', 'requestId': r['id']}, {'kind': 'answer', 'questionId': theirs['id']}, 'staff_demo',
                          'staff', [('observation', 'The 5 Oct payment was for DEMO-502')]))   # a draft for this case: keepForCustomer is ignored
        [answered] = view['analysis']['brief']['questions']
        self.assertEqual((answered['status'], answered['answeredBy']), ('answered', s['lines'][0]['id']))
        self.assertEqual([e['data'] for e in view['history'] if e['kind'].startswith('question.')], [{'questionId': theirs['id'], 'from': 'staff'}])
        self.assertEqual(self.question(r, 'answer', {'text': 'Fine'}, 'staff', 'q2')[0], 403)   # the owner's question
        self.assertEqual(self.app.statements()[-1]['id'], s['id'])

    def test_the_owner_may_answer_a_question_asked_of_staff(self):
        self.conflict(StaffNeed(), 'live')
        r = self.case()
        status, view, _ = self.question(r, 'answer', {'text': ANSWER})
        s = self.app.statements()[-1]
        self.assertEqual((status, s['status'], s['visibility']), (200, 'confirmed', 'owner'))
        staff = self.reopen(r)
        self.assertEqual([(q['status'], q['answeredBy']) for q in staff['analysis']['brief']['questions']], [('answered', s['lines'][0]['id'])])
        self.assertNotIn(ANSWER, json.dumps(staff))   # answered, but the owner's words stay with the owner

    def test_a_question_for_staff_that_repeats_private_context_goes_to_the_owner(self):
        self.conflict(StaffNeedQuotingTheOwner(), 'live')
        self.tell()
        r = self.case()
        mine, moved = r['analysis']['brief']['questions']
        self.assertEqual([(q['kind'], q['from'], q['checks']) for q in (mine, moved)], [('recommend', 'owner', []), ('calculate', 'owner', [STAFF_MOVED])])
        staff = self.reopen(r)
        self.assertEqual(staff['analysis']['brief']['questions'], [])
        self.assertNotIn(GUIDANCE, json.dumps(staff))
        self.assertEqual(self.question(r, 'answer', {'text': 'Fine'}, 'staff', index=1)[0], 403)

    def test_old_v2_briefs_still_read(self):
        self.ready()
        r = self.case()
        stored = self.app.get(r['id'])
        brief = stored['analysis']['brief']
        for key in ('contextShown', 'questions', 'suggestion', 'suggestionStatus'):
            del brief[key]
        brief['format'] = 'brief-v2'
        with self.app.lock, self.app.db:
            self.app.save(stored)
        for role in ('owner', 'staff'):
            view = self.call('/api/requests/' + r['id'], role=role)[1]
            self.assertEqual({k: v for k, v in view.items() if k not in ('history', 'runs', 'context')}, stored)
            self.assertEqual(view['context'], {'lines': [], 'decisions': []})


if __name__ == '__main__':
    unittest.main()
