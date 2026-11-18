"""The concern loop, owner side: answerConcern. What the owner's answer is sets the status and the next person (needs_info, explain,
guidance send the case back to staff, each with its own why); the words are shared with staff and nothing else of the owner's is;
a concern-rounds escalation is cleared and the rounds start again; staff raising another concern puts the case with the owner
again. All data is fictional; no real model is called."""
import json
import unittest

from agent import display_date

from test_assessment import AssessmentCase, WORRY, WORRY_AGAIN

ASK = 'Please send me their last three payment dates.'
EXPLAIN = 'The overdue invoice is under dispute, so the check is right to ignore it.'
RULE = 'From now on Bayside Café may pay up to 14 days late without asking me.'
PRIVATE = 'Between us, Bayside Café is a friend of mine and I never chase them.'


class ConcernLoopTests(AssessmentCase):
    stored = AssessmentCase.T.stored
    def raise_concern(self, text=WORRY, key='c1'):
        return self.ok('raiseConcern', 'staff', key=key, message=text, requestId=self.r['id'], text=text)

    def answer(self, text, kind, key='a1', message=None, **extra):
        return self.ok('answerConcern', 'owner', key=key, message=message or text, requestId=self.r['id'], text=text, kind=kind, **extra)

    def row(self, role, bucket):
        [row] = [x for x in self.ok('workQueue', role)[bucket] if x['requestId'] == self.r['id']]
        return row

    def test_needs_info_sends_the_case_back_to_staff_with_the_owner_s_question(self):
        concern = self.raise_concern()['line']
        self.assertEqual(self.row('owner', 'forYou')['why'], 'staff raised a concern')
        result = self.answer(ASK, 'needs_info')
        line = result['line']
        self.assertEqual((line['kind'], line['by'], line['text'], line['answers'], line['responseKind']), ('answer', 'owner', ASK, concern['id'], 'needs_info'))
        self.assertEqual((result['waitingOn'], result['why']), ('staff', 'the owner asked: ' + ASK))
        for role, bucket in (('staff', 'forYou'), ('owner', 'waitingOnOthers')):
            row = self.row(role, bucket)
            self.assertEqual((row['statusLabel'], row['why']), ('Waiting on staff', 'the owner asked: ' + ASK), role)
        self.assertEqual([x['requestId'] for x in self.ok('workQueue', 'owner')['forYou']], [])
        for role in ('owner', 'staff'):
            case = self.ok('caseDetails', role, requestId=self.r['id'])['case']
            self.assertEqual((case['label'], case['withStaff']['kind'], [x['quote'] for x in case['answers']]), ('Waiting on staff', 'needs_info', [ASK]), role)
            self.assertEqual([(x['id'], x.get('answeredBy')) for x in case['concerns']], [(concern['id'], line['id'])], role)
            [said] = [x for x in case['contextLines'] if x['kind'] == 'answer']
            self.assertEqual((said['quote'], said['by'], said['source']), (ASK, 'owner', 'concern_answer'), role)
            self.assertIn('concern.answered', [e['kind'] for e in self.case(role)['history']], role)

    def test_explain_returns_the_case_to_staff_and_staff_replying_returns_it_to_the_owner(self):
        self.raise_concern()
        self.answer(EXPLAIN, 'explain')
        self.assertEqual(self.row('staff', 'forYou')['why'], 'the owner answered the concern')
        self.assertEqual(self.row('owner', 'waitingOnOthers')['why'], 'the owner answered the concern')
        reply = self.raise_concern(WORRY_AGAIN, 'c2')['line']   # staff reply: the owner has the case again
        self.assertEqual(reply['kind'], 'reply')
        self.assertEqual(self.row('owner', 'forYou')['why'], 'staff replied: ' + WORRY_AGAIN)
        self.assertEqual(self.row('staff', 'waitingOnOthers')['statusLabel'], 'With the owner')
        self.assertIsNone(self.ok('caseDetails', 'staff', requestId=self.r['id'])['case']['withStaff'])

    def test_staff_answering_what_the_owner_asked_is_a_reply_not_a_concern_round(self):
        self.set_limits()
        self.assess()
        self.raise_concern(WORRY, 'c1')
        self.answer(ASK, 'needs_info')
        reply = self.raise_concern('Their last payments were on 3 and 17 September and 1 October.', 'c2')['line']
        self.assertEqual((reply['kind'], 'disagreesWith' in reply), ('reply', False))
        stored, _ = self.stored()
        self.assertNotIn('escalated', stored)
        row = self.row('owner', 'forYou')
        self.assertEqual(row['why'], 'staff replied: ' + reply['quote'])
        self.assertEqual(self.row('staff', 'waitingOnOthers')['statusLabel'], 'With the owner')
        for role in ('owner', 'staff'):
            self.assertEqual([x['kind'] for x in self.case(role)['concerns']], ['concern', 'reply'], role)
        self.raise_concern(WORRY_AGAIN, 'c3')   # a real concern: the reply did not use up a round
        stored, _ = self.stored()
        self.assertNotIn('escalated', stored)
        self.assertEqual(self.row('owner', 'forYou')['why'], 'staff raised a concern')

    def test_staff_reporting_back_after_guidance_with_next_staff_is_a_reply_and_never_escalates(self):
        self.set_limits()
        self.assess()
        self.raise_concern(WORRY, 'c1')
        for n in (1, 2):   # two exchanges: guidance sends it to staff, staff report back
            self.answer(RULE, 'guidance', key='a%d' % n, next='staff')
            reply = self.raise_concern('I called them and they will pay on the 20th (%d).' % n, 'r%d' % n)['line']
            self.assertEqual((reply['kind'], 'disagreesWith' in reply), ('reply', False))
            self.assertEqual(self.row('owner', 'forYou')['why'], 'staff replied: ' + reply['quote'])
            self.assertNotIn('escalated', self.stored()[0])
        self.assertEqual([x['kind'] for x in self.case('owner')['concerns']], ['concern', 'reply', 'reply'])

    def test_guidance_is_kept_for_the_customer_and_staff_see_only_its_words(self):
        self.raise_concern()
        result = self.answer(RULE, 'guidance', until='2026-12-31', next='staff')
        self.assertEqual(result['why'], 'the owner gave guidance')   # the first guidance on the case
        for role in ('owner', 'staff'):
            context = self.ok('ownerContext', role, customerId=self.bayside['id'])
            [kept] = [x for x in context['lines'] if x['kind'] == 'guidance' and x['quote'] == RULE]
            self.assertEqual(kept['until'], '2026-12-31', role)
        [stmt] = [s for s in self.app.statements() if s['text'] == RULE]
        self.assertEqual((stmt['status'], stmt['visibility'], stmt['scope']), ('confirmed', 'staff', {'kind': 'customer', 'customerId': self.bayside['id']}))
        self.assertEqual(self.row('staff', 'forYou')['why'], 'the owner gave guidance')
        self.assertEqual(self.refused('answerConcern', 'owner', 'a2', message=RULE, requestId=self.r['id'], text=RULE, kind='explain', until='2026-12-31'), 'INVALID_ARGUMENT')
        self.assertEqual(self.refused('answerConcern', 'owner', 'a3', message=RULE, requestId=self.r['id'], text=RULE, kind='guidance', until='next year'), 'INVALID_ARGUMENT')

    def test_only_the_words_meant_for_staff_are_shared_and_nothing_else_of_the_owner_s_reaches_them(self):
        message = PRIVATE + ' ' + EXPLAIN
        self.answer(EXPLAIN, 'explain', key='a1', message=message)
        staff = json.dumps([self.case('staff'), self.ok('caseDetails', 'staff', requestId=self.r['id']), self.ok('workQueue', 'staff'),
                            self.ok('ownerContext', 'staff', customerId=self.bayside['id'], requestId=self.r['id'])])
        self.assertIn(EXPLAIN, staff)
        self.assertNotIn('friend of mine', staff)
        self.assertEqual(self.refused('answerConcern', 'owner', 'a4', message='Please look.', requestId=self.r['id'], text=EXPLAIN, kind='explain'), 'INVALID_ARGUMENT')   # not their words

    def test_refusals(self):
        status, body, _ = self.tool('answerConcern', 'staff', 'r1', message=ASK, requestId=self.r['id'], text=ASK, kind='needs_info')
        self.assertEqual((status, body['error']), (403, 'FORBIDDEN'))   # the owner's tool: not offered to staff
        for kind in ('decide', 'resolved', None):
            self.assertEqual(self.refused('answerConcern', 'owner', 'r-' + str(kind), message=ASK, requestId=self.r['id'], text=ASK, **({'kind': kind} if kind else {})),
                             'INVALID_ARGUMENT', kind)
        c = self.case()
        body = {'expectedRequestVersion': c['version'], 'analysisId': c['analysis']['id'], 'evidenceVersion': c['analysis']['snapshot']['evidenceVersion'],
                'outcome': 'approve', 'approvedDueDate': '2026-11-03', 'reason': 'This invoice only.'}
        self.assertEqual(self.call('/api/requests/' + self.r['id'] + '/decisions', body, 'owner', 'dec')[0], 201)
        self.assertEqual(self.refused('answerConcern', 'owner', 'r-decided', message=ASK, requestId=self.r['id'], text=ASK, kind='needs_info'), 'INVALID_ARGUMENT')

    def test_an_answer_clears_the_concern_rounds_and_staff_may_act_within_authority_again(self):
        self.set_limits()
        self.assess()
        self.raise_concern(WORRY, 'c1')
        self.raise_concern(WORRY_AGAIN, 'c2')
        for role in ('owner', 'staff'):
            self.assertEqual((self.row(role, 'forYou' if role == 'owner' else 'waitingOnOthers'))['why'], 'escalated: concern rounds', role)
        self.assertEqual(self.act()[1]['error'], 'NOT_WITHIN_AUTHORITY')
        self.answer(EXPLAIN, 'explain')
        stored, _ = self.stored()
        self.assertNotIn('escalated', stored)
        self.assertEqual(self.row('staff', 'forYou')['why'], 'the owner answered the concern')
        self.assertEqual(self.case('owner')['concerns'][-1].get('answeredBy') is not None, True)
        self.raise_concern('I am worried still, a third time.', 'c3')   # the case was with staff after the answer: this is their reply, not a round
        stored, _ = self.stored()
        self.assertNotIn('escalated', stored)
        self.assertEqual(self.row('owner', 'forYou')['why'], 'staff replied: I am worried still, a third time.')
        self.answer(EXPLAIN + ' Again.', 'explain', key='a2')
        status, body, _ = self.act('act-after')
        self.assertEqual((status, body.get('ok')), (200, True), body)

    def test_the_situation_lists_the_answer_for_both_roles(self):
        self.raise_concern()
        self.answer(ASK, 'needs_info')
        for role in ('owner', 'staff'):
            [said] = [x for x in self.situation(role)['case']['contextLines'] if x['kind'] == 'answer']
            self.assertEqual((said['quote'], said['by'], said['scope'], said['source']), (ASK, 'owner', 'case', 'concern_answer'), role)

    def test_the_owner_s_question_is_the_why_even_when_a_failed_check_escalated_the_case_first(self):
        from server import queue_why, waiting_on
        r = {'status': 'awaiting_owner', 'escalated': {'reason': 'day limit'}, 'concerns': [{'quote': WORRY, 'kind': 'concern'}], 'analysis': None,
             'withStaff': {'kind': 'needs_info', 'why': 'the owner asked: ' + ASK}}
        for role in ('owner', 'staff'):
            self.assertEqual((waiting_on(r, role), queue_why(r, 'staff', role)), ('staff', 'the owner asked: ' + ASK), role)
        r.pop('withStaff')   # nothing sent it back: the escalation is the reason
        self.assertEqual(queue_why(r, 'owner', 'owner'), 'escalated: day limit')

    def test_the_assessment_lists_only_open_concerns_not_answered_ones_or_replies(self):
        self.set_limits()
        self.raise_concern(WORRY, 'c1')
        self.assertEqual([x['quote'] for x in self.assess()['evidence']['openConcerns']], [WORRY])
        self.answer(ASK, 'needs_info')
        self.assertEqual(self.assess()['evidence']['openConcerns'], [])   # answered
        self.raise_concern('Their last payments were on 3 and 17 September.', 'c2')   # a reply to the question, not a concern
        self.assertEqual(self.assess()['evidence']['openConcerns'], [])

    def test_a_request_is_not_opened_inside_a_case_thread(self):
        text = 'Could we pay invoice DEMO-502 on 2026-11-10 instead?'
        before = len(self.app.records())
        status, body, _ = self.tool('openRequest', 'staff', 'o-case', message=text, text=text, current={'requestId': self.r['id']})
        self.assertEqual((status, body.get('ok'), body.get('error')), (200, False, 'INVALID_ARGUMENT'), body)
        self.assertIn('Open new requests from the General thread; in a case, raise a concern or reply instead.', body['message'])
        self.assertEqual(len(self.app.records()), before)

    def test_assessing_a_case_still_being_prepared_says_so_instead_of_failing(self):
        r = self.create('Could we pay invoice DEMO-501 on 2026-11-10 instead?', key='g4-new')
        stored = self.app.get(r['id'])   # the analysis run has not settled: no customer or invoice found yet
        stored.update(status='analysing', customerId=None, invoiceId=None, analysis=None)
        with self.app.db:
            self.app.save(stored)
        status, body, _ = self.tool('assessRequest', 'staff', 'g4-a', message='Assess it.', requestId=r['id'])
        self.assertEqual((status, body.get('ok'), body.get('error')), (200, False, 'CASE_PREPARING'), body)
        self.assertIn('still being prepared', body['message'])
        self.assertEqual(self.tool('caseDetails', 'staff', 'g4-c', message='Open it.', requestId=r['id'])[0], 200)

    def test_current_names_the_one_open_case_of_the_customer_in_focus_for_every_case_tool(self):
        focus = {'customerId': self.bayside['id']}
        status, body, _ = self.tool('raiseConcern', 'staff', 'g5-a', message=WORRY, current=focus, requestId='current', text=WORRY)
        self.assertEqual((status, body.get('ok')), (200, True), body)
        self.assertEqual(body['result']['requestId'], self.r['id'])
        status, body, _ = self.tool('prepareDecision', 'owner', 'g5-b', message='Approve it for 14 days.', current=focus, requestId='current', outcome='approve', days=14)
        self.assertNotIn('Use a requestId', json.dumps(body))
        self.assertEqual(body.get('error') != 'INVALID_ARGUMENT' or 'requestId' not in body.get('message', ''), True, body)
        status, body, _ = self.tool('answerConcern', 'owner', 'g5-c', message=EXPLAIN, current=focus, requestId='current', text=EXPLAIN, kind='explain')
        self.assertEqual((status, body.get('ok')), (200, True), body)

    GUIDE = 'Please ask them for a written payment plan and come back to me with it before I decide.'

    def test_guidance_before_any_concern_is_stored_sends_the_case_to_staff_and_the_second_one_changes_it(self):
        self.assertEqual(self.ok('caseDetails', 'owner', requestId=self.r['id'])['case']['concerns'], [])
        result = self.answer(self.GUIDE, 'guidance', next='staff')
        self.assertEqual((result['line']['answers'], result['line']['responseKind'], result['waitingOn'], result['why']), (None, 'guidance', 'staff', 'the owner gave guidance'))
        for role in ('owner', 'staff'):
            case = self.ok('caseDetails', role, requestId=self.r['id'])['case']
            self.assertEqual((case['withStaff']['kind'], [x['quote'] for x in case['answers']]), ('guidance', [self.GUIDE]), role)
            self.assertEqual(self.row(role, 'forYou' if role == 'staff' else 'waitingOnOthers')['why'], 'the owner gave guidance', role)
        [event] = [e for e in self.case('owner')['history'] if e['kind'] == 'concern.answered']
        self.assertEqual((event['data']['text'], event['data']['answers'], event['data']['actorRole']), (self.GUIDE, None, 'owner'))
        second = self.answer('Make it a signed plan.', 'guidance', key='a2', next='staff')
        self.assertEqual(second['why'], 'the owner changed the guidance')
        asked = self.answer(ASK, 'needs_info', key='a3')
        self.assertEqual((asked['line']['answers'], asked['waitingOn']), (None, 'staff'))

    # Repair B, F3: who acts next follows the intended next action, not the kind.
    def test_next_defaults_by_kind_and_needs_info_is_always_staff(self):
        self.raise_concern()
        self.assertEqual(self.refused('answerConcern', 'owner', 'n1', message=ASK, requestId=self.r['id'], text=ASK, kind='needs_info', next='owner'), 'INVALID_ARGUMENT')
        self.assertEqual(self.refused('answerConcern', 'owner', 'n2', message=ASK, requestId=self.r['id'], text=ASK, kind='explain', next='nobody'), 'INVALID_ARGUMENT')
        for kind, text, expect in (('needs_info', ASK, 'staff'), ('explain', EXPLAIN, 'staff'), ('guidance', RULE, 'owner')):
            result = self.answer(text, kind, key='d-' + kind)
            self.assertEqual((result['next'], result['waitingOn']), (expect, expect), kind)
            self.assertTrue(result['statement'].startswith('Back with staff: ' if expect == 'staff' else 'Still with the owner: '), result['statement'])
            self.raise_concern(WORRY_AGAIN + ' ' + kind, 'c-' + kind)   # staff reply: the case is the owner's again

    def test_every_kind_with_next_owner_keeps_the_case_with_the_owner_in_both_queues(self):
        for kind, text, why in (('explain', EXPLAIN, 'explanation given; your decision is still pending'), ('guidance', RULE, 'guidance given; your decision is still pending')):
            self.raise_concern(WORRY + ' ' + kind, 'c-' + kind)
            result = self.answer(text, kind, key='o-' + kind, next='owner')
            self.assertEqual((result['next'], result['why']), ('owner', why), kind)
            row = self.row('owner', 'forYou')
            self.assertEqual((row['statusLabel'], row['why']), ('Needs your decision', why), kind)
            row = self.row('staff', 'waitingOnOthers')
            self.assertEqual((row['statusLabel'], row['why']), ('With the owner', "the owner's decision is still pending"), kind)
            stored, _ = self.stored()
            self.assertNotIn('withStaff', stored)
            self.assertEqual(stored['withOwner']['kind'], kind)
            for role in ('owner', 'staff'):
                case = self.ok('caseDetails', role, requestId=self.r['id'])['case']
                self.assertIsNone(case['withStaff'], role)
                self.assertEqual(case['withOwner']['why'], why if role == 'owner' else "the owner's decision is still pending", role)
                self.assertEqual(case['label'], 'Needs your decision' if role == 'owner' else 'With the owner', role)
                self.assertIn(text, [x['quote'] for x in case['answers']], role)   # staff see the answer on the case
                self.assertIn(text, [x['quote'] for x in case['contextLines'] if x['kind'] == 'answer'], role)

    def test_next_staff_sends_the_case_to_staff_for_every_kind_and_only_then(self):
        for kind, text in (('explain', EXPLAIN), ('guidance', RULE)):
            self.raise_concern(WORRY + ' ' + kind, 'c-' + kind)
            self.answer(text, kind, key='s-' + kind, next='staff')
            stored, _ = self.stored()
            self.assertEqual((stored['withStaff']['kind'], 'withOwner' in stored), (kind, False), kind)
            self.assertEqual(self.row('staff', 'forYou')['statusLabel'], 'Waiting on staff', kind)
            self.assertEqual(self.row('owner', 'waitingOnOthers')['statusLabel'], 'Waiting on staff', kind)
            self.assertIsNone(self.ok('caseDetails', 'owner', requestId=self.r['id'])['case']['withOwner'], kind)

    def test_guidance_kept_with_the_owner_shows_staff_the_words_and_nothing_private(self):
        self.answer(RULE, 'guidance', message=PRIVATE + ' ' + RULE)
        staff = json.dumps([self.ok('caseDetails', 'staff', requestId=self.r['id']), self.ok('workQueue', 'staff'),
                            self.ok('ownerContext', 'staff', customerId=self.bayside['id'], requestId=self.r['id'])], ensure_ascii=False)
        self.assertIn(RULE, staff)
        self.assertNotIn('friend of mine', staff)
        self.assertNotIn('guidance given; your decision', staff)   # the owner's wording is the owner's

    def test_staff_raising_a_concern_after_an_answer_kept_with_the_owner_leaves_the_owner_why_alone(self):
        self.answer(RULE, 'guidance')
        self.raise_concern(WORRY_AGAIN, 'c9')
        self.assertEqual(self.row('owner', 'forYou')['why'], 'staff raised a concern')
        self.assertNotIn('withOwner', self.stored()[0])

    # Repair B, F4: the recorded decision and its reason reach staff.
    REASON = 'This invoice only; the bank receipt for VND 1,000,000 was checked.'

    def decide(self):
        c = self.case()
        body = {'expectedRequestVersion': c['version'], 'analysisId': c['analysis']['id'], 'evidenceVersion': c['analysis']['snapshot']['evidenceVersion'],
                'outcome': 'approve', 'approvedDueDate': '2026-11-03', 'reason': self.REASON,
                'remember': {'text': 'Private: Bayside Café is a friend of mine.', 'keepForCustomer': False}}
        self.assertEqual(self.call('/api/requests/' + self.r['id'] + '/decisions', body, 'owner', 'dec-b')[0], 201)

    def test_staff_and_owner_read_the_recorded_decision_with_its_reason_and_staff_nothing_private(self):
        self.assertIsNone(self.ok('caseDetails', 'staff', requestId=self.r['id'])['case']['decision'])
        self.decide()
        keys = {'outcome', 'approvedDueDate', 'approvedDueDateText', 'days', 'reason', 'decidedOn', 'decidedOnText', 'decisionSource', 'followedRecommendation'}
        staff = self.ok('caseDetails', 'staff', requestId=self.r['id'])['case']
        self.assertTrue(keys <= set(staff['decision']), staff['decision'])
        self.assertEqual((staff['decision']['reason'], staff['decision']['outcome'], staff['decision']['approvedDueDateText'], staff['decision']['decisionSource'], staff['decision']['days']),
                         (self.REASON, 'approve', 'Tue 3 Nov 2026', 'owner', 14))
        self.assertNotIn('recommendation', staff['decision'])   # the owner's snapshot
        owner = self.ok('caseDetails', 'owner', requestId=self.r['id'])['case']
        self.assertIn('recommendation', owner['decision'])
        self.assertEqual(owner['decision']['reason'], self.REASON)
        everything = json.dumps([self.ok('caseDetails', 'staff', requestId=self.r['id']), self.ok('cases', 'staff', customerId=self.bayside['id']),
                                 self.ok('ownerContext', 'staff', customerId=self.bayside['id'], requestId=self.r['id'])], ensure_ascii=False)
        self.assertNotIn('friend of mine', everything)
        self.assertNotIn('decidedAt', json.dumps(staff['decision']))   # a time's digits are no figure

    def test_the_case_summary_carries_the_decision_for_the_list_and_the_cases_tool(self):
        from server import summary
        self.assertIsNone(summary(self.stored()[0])['decision'])
        self.decide()
        stored, _ = self.stored()
        self.assertEqual((summary(stored)['decision']['reason'], summary(stored)['decision']['decidedOnText']), (self.REASON, display_date(stored['decision']['decidedAt'][:10])))   # the day it was made, whatever day the suite runs
        self.assertNotIn('recommendation', summary(stored)['decision'])


if __name__ == '__main__':
    unittest.main()


class InvoiceDateFilterTests(AssessmentCase):
    """G11: the invoices tool selects by the original due date, the approved (effective) due date or the issue date, in code."""
    REASON = ConcernLoopTests.REASON
    decide = ConcernLoopTests.decide

    def inv(self, **args):
        return self.ok('invoices', 'staff', customerId=self.bayside['id'], which='all', **args)

    def test_same_day_matches_one_match_and_no_match(self):
        self.add_invoice(self.bayside, 'DEMO-503', dueDate='2026-10-20', stillOwed='300.00', stillOwedAsOf='2026-10-16')
        self.add_invoice(self.bayside, 'DEMO-504', dueDate='2026-12-01', stillOwed='50.00', stillOwedAsOf='2026-10-16')
        r = self.inv(dueOn='2026-10-20')
        self.assertEqual(sorted(x['reference'] for x in r['invoices']), ['DEMO-501', 'DEMO-502', 'DEMO-503'])
        self.assertEqual({x['matchedOn'] for x in r['invoices']}, {'original_due'})
        self.assertEqual((r['invoiceCount'], r['filter']['text']), (3, 'due on Tue 20 Oct 2026 (original or approved)'))
        one = self.inv(dueOn='2026-12-01')
        self.assertEqual([x['reference'] for x in one['invoices']], ['DEMO-504'])
        none = self.inv(dueOn='2026-08-16')
        self.assertEqual((none['invoiceCount'], none['invoices']), (0, []))
        self.assertEqual(none['filter']['noneText'], 'No invoice of Bayside Café has Sun 16 Aug 2026 as its due date (original or approved).')
        self.assertEqual(self.refused('invoices', 'staff', 'bad', message='x', customerId=self.bayside['id'], which='all', dueOn='August'), 'INVALID_ARGUMENT')

    def test_a_match_by_the_approved_date_states_both_dates(self):
        self.decide()   # the owner approves one case to Tue 3 Nov 2026
        moved = self.inv(dueOn='2026-11-03')
        [row] = moved['invoices']
        self.assertEqual(row['matchedOn'], 'approved_due')
        self.assertEqual((row['originalDueText'], row['dueNowText']), ('Tue 20 Oct 2026', 'Tue 3 Nov 2026'))
        again = self.inv(dueOn='2026-10-20')
        self.assertEqual({x['reference']: x['matchedOn'] for x in again['invoices']}, {'DEMO-501': 'original_due', 'DEMO-502': 'original_due'})   # the original date still matches
        issued = self.inv(issuedOn='2026-10-01')
        self.assertTrue(all(x['matchedOn'] == 'issue' for x in issued['invoices']))


class CurrentFallbackTests(AssessmentCase):
    """G5: "current" outside a case thread resolves only when the customer in focus has exactly one open case."""
    def current(self, tool='caseDetails', **extra):
        status, body, _ = self.tool(tool, 'staff', 'cur-' + tool + str(len(extra)), message='x', current={'customerId': self.bayside['id']}, requestId='current', **extra)
        return status, body

    def test_one_open_case_resolves_two_ask_which_and_none_says_so(self):
        status, body = self.current()
        self.assertEqual((status, body['ok'], body['result']['case']['requestId']), (200, True, self.r['id']))
        second = self.wait_status(self.create('Could we pay invoice DEMO-502 on 2026-11-10 instead?', key='second'), ('awaiting_owner', 'needs_information'))
        status, body = self.current()
        self.assertEqual((status, body['ok'], body['error']), (200, False, 'INVALID_ARGUMENT'))
        self.assertIn('DEMO-501', body['message'])
        self.assertIn('DEMO-502', body['message'])
        self.assertIn('Which case do you mean?', body['message'])
        self.assertNotIn(self.r['id'], body['message'])
        self.assertEqual(sorted(body['candidates']), ['DEMO-501', 'DEMO-502'])
        # none: both closed
        for rid in (self.r['id'], second['id']):
            with self.app.lock, self.app.db:
                x = self.app.get(rid)
                x['status'] = 'withdrawn'
                self.app.save(x)
        status, body = self.current()
        self.assertEqual((body['ok'], body['error']), (False, 'INVALID_ARGUMENT'))
        self.assertIn('no open case', body['message'])
