"""The assessment: facts computed from the records and checks against the limits the owner set, no model and no score; the
authority settings (the owner's alone); staff acting exactly within them; the owner's decision recording whether it followed the
recommendation; guidance with an end date; and concerns that escalate. All data is fictional; no real model is called."""
import json
import re
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from coordinator import CAPABILITIES
from test_records import RecordsCase
from test_situation import SituationCase
import test_tool_surface   # its helpers only

NO_MODEL = ("These figures are numerical analysis of the recorded ledger plus the owner's policy checks. No approval predictor runs: the team's "
            "labelled data are proxies for lateness, not owner decisions, and too few to measure. The features carry the pipeline's names so a "
            "validated predictor can be attached later.")
WORRY = "I'm worried about this one: they sounded unsure on the phone."
WORRY_AGAIN = "I'm worried still: the second invoice is slow as well."
LIMITS = {'staffMayApproveUpToDays': 30, 'maxOutstanding': '5000.00'}   # DEMO-501 asks 21 days; Bayside owes 2 x 1,200.00


class AssessmentCase(SituationCase):
    T = test_tool_surface.ToolSurfaceTests
    case, bayside_subject, second_case = T.case, T.bayside_subject, T.second_case

    def authority(self, role='owner', method='PUT', **values):
        headers = {'Cookie': self.cookies[role], 'Content-Type': 'application/json'}
        req = Request(self.base + '/api/setup/authority', data=json.dumps(values).encode() if method == 'PUT' else None, headers=headers, method=method)
        try:
            response = urlopen(req, timeout=10)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.loads(response.read())

    def set_limits(self, **values):
        status, body = self.authority(**{**LIMITS, **values})
        self.assertEqual(status, 200, body)
        return body

    def assess(self, role='staff', **args):
        return self.ok('assessRequest', role, requestId=self.r['id'], **args)

    def overdue_invoice(self):
        self.add_invoice(self.bayside, 'DEMO-499', dueDate='2026-10-05', total='400.00')
        self.wait_status(self.r, ('awaiting_owner',))   # the new invoice sends the case back through its analysis

    def act(self, key='act-1'):
        return self.tool('actWithinAuthority', 'staff', key, requestId=self.r['id'])

    def decide(self, **values):
        c = self.case()
        body = {'expectedRequestVersion': c['version'], 'analysisId': c['analysis']['id'], 'evidenceVersion': c['analysis']['snapshot']['evidenceVersion'],
                'outcome': 'approve', 'approvedDueDate': '2026-11-03', 'reason': 'This invoice only.', **values}
        return self.call('/api/requests/' + self.r['id'] + '/decisions', body, 'owner', 'decide-' + json.dumps(values, sort_keys=True))


class AssessmentTests(AssessmentCase):
    def test_with_no_settings_everything_escalates_and_the_result_holds_no_score(self):   # Review Focus 4
        self.assertEqual(self.authority(method='GET')[1], {'staffMayApproveUpToDays': None, 'maxOutstanding': None, 'maxOutstandingText': None,
                                                           'requireNothingOverdue': True, 'maxPriorLateShare': None, 'hardRules': [], 'maxConcernRounds': 2})
        a = self.assess()
        self.assertEqual((a['recommendation']['outcome'], a['model']), ('escalate', {'status': 'unavailable', 'reason': NO_MODEL}))
        self.assertEqual([(c['name'], c['passes']) for c in a['policy']['checks']],
                         [('nothing_overdue', True), ('late_history', True), ('requested_days', False), ('outstanding_amount', True)])
        self.assertIn('No limits are set for staff', a['recommendation']['reasons'][0])
        self.assertEqual(set(a), {'requestId', 'recorded', 'facts', 'policy', 'model', 'recommendation', 'evidence', 'limitations', 'subject', 'version', 'basisSummary', 'completeness'})
        by = {x['name']: x for x in a['facts']['items']}
        self.assertEqual((by['debt_before_m']['value'], by['overdue_before_m']['value'], by['prior_invoice_documents']['value']), (240000, 0, 2))
        self.assertEqual(by['debt_before_m']['text'], 'AUD 2,400.00 is owed on the recorded invoices after the recorded payments.')
        self.assertIn('(2 with a recorded total, 2 of them also stating an amount still owed).', by['prior_invoice_documents']['text'])
        self.assertNotIn('with a stated amount still owed', by['prior_invoice_documents']['text'])
        self.assertEqual((a['facts']['asOf'], a['facts']['allocationBasis'], a['facts']['reconciles']), ('2026-10-18', 'fifo', True))
        self.assertEqual(a['evidence']['decisionsRecorded'], 0)
        for banned in (r'%', r'percent', r'probab', r'confiden', r'risk', r'score'):
            self.assertIsNone(re.search(banned, json.dumps(a), re.I), banned)

    def test_with_limits_set_and_a_clean_history_staff_can_act_and_the_decision_says_how(self):   # Review Focus 4
        self.set_limits()
        a = self.assess()
        self.assertEqual(a['recommendation']['outcome'], 'approve_within_authority')
        self.assertTrue(all(c['passes'] for c in a['policy']['checks']))
        status, body, _ = self.act()
        self.assertEqual((status, body['ok']), (200, True), body)
        self.assertEqual((body['result']['outcome'], body['result']['approvedDueDate']), ('approve', '2026-11-10'))
        c = self.case('staff')
        d = c['decision']
        self.assertEqual((c['status'] in ('decided', 'completed'), d['outcome'], d['approvedDueDate'], d['approvedExtensionDays'], d['decisionSource'],
                          d['decidedBy'], d['followedRecommendation']), (True, 'approve', '2026-11-10', 21, 'staff_within_authority', 'staff_demo', True))
        self.assertEqual(d['authority']['staffMayApproveUpToDays'], 30)
        self.assertEqual(d['recommendation']['outcome'], 'approve_within_authority')
        self.assertEqual(d['assessment']['facts']['asOf'], '2026-10-18')
        self.assertIn('is within the 30 days staff may approve', d['reason'])
        self.assertIn('decision.committed', [e['kind'] for e in c['history']])
        self.assertEqual(self.act('act-2')[1]['error'], 'INVALID_ARGUMENT')   # decided: nothing left to act on

    def test_an_open_invoice_without_a_due_date_is_overdue_unknown_and_staff_cannot_act(self):   # repair E, finding A
        self.set_limits(requireNothingOverdue=True)
        self.add_invoice(self.bayside, 'DEMO-497', total='3000.00')   # no due date
        self.wait_status(self.r, ('awaiting_owner',))
        a = self.assess()
        said = {i['name']: i['text'] for i in a['facts']['items']}
        self.assertIn('Overdue not known: 1 open invoice has no due date (AUD 3,000.00).', said['overdue_before_m'])
        self.assertNotIn('Nothing is overdue', json.dumps(a['facts']))
        self.assertNotIn('Nothing is past due', json.dumps(a['facts']))
        c = next(c for c in a['policy']['checks'] if c['name'] == 'nothing_overdue')
        self.assertEqual((c['passes'], c['unknown'], c['sentence']), (False, True, 'Cannot be established: 1 open invoice has no due date'))
        self.assertNotIn('Nothing else is overdue', json.dumps(a['policy']))
        self.assertEqual(a['recommendation']['outcome'], 'escalate')
        status, body, _ = self.act()
        self.assertEqual(body['error'], 'NOT_WITHIN_AUTHORITY')

    def test_a_manually_entered_amount_still_owed_names_who_entered_it(self):   # repair E, finding D
        self.add_invoice(self.bayside, 'DEMO-496', dueDate='2026-10-30', stillOwed='300.00', stillOwedAsOf='2026-10-18')
        r = self.wait_status(self.create('Could we pay invoice DEMO-496 on 2026-11-10 instead?', key='intake-496'), ('awaiting_owner',))
        fact = {f['key']: f for f in self.case('owner', r['id'])['analysis']['brief']['facts']}['outstandingAmount']
        self.assertEqual((fact['kind'], fact['source']['origin']), ('stated', 'manual'))
        by = fact['source']['setBy']
        self.assertEqual((by['kind'], by['role'], by['by'], bool(by['at'])), ('manual', 'staff', 'staff_demo', True))   # the web page words it from this, never as the customer's

    def test_staff_cannot_act_when_the_request_is_over_the_day_limit_or_anything_is_overdue(self):   # Review Focus 4
        self.set_limits(staffMayApproveUpToDays=14)
        self.assertEqual(self.assess()['recommendation']['outcome'], 'escalate')
        status, body, _ = self.act()
        self.assertEqual((status, body['ok'], body['error']), (200, False, 'NOT_WITHIN_AUTHORITY'))
        self.assertIn('21 days', body['message'])
        self.assertIsNone(self.case()['decision'])
        [row] = [x for x in self.ok('workQueue')['forYou'] if x['requestId'] == self.r['id']]
        self.assertEqual(row['why'], 'escalated: requested days over the staff limit')
        self.set_limits()   # 30 days: now only the overdue invoice stops it
        self.overdue_invoice()
        a = self.assess()
        self.assertEqual(a['recommendation']['outcome'], 'escalate')
        self.assertFalse(next(c for c in a['policy']['checks'] if c['name'] == 'nothing_overdue')['passes'])
        by = {x['name']: x for x in a['facts']['items']}
        self.assertEqual((by['overdue_before_m']['value'], by['max_days_past_due_before']['value']), (40000, 13))
        self.assertEqual(by['overdue_before_m']['text'], 'AUD 400.00 is overdue, the oldest 13 days past due.')
        body = self.act('act-2')[1]
        self.assertEqual(body['error'], 'NOT_WITHIN_AUTHORITY')
        self.assertIn('overdue', body['message'])
        self.assertIsNone(self.case()['decision'])

    def test_an_invoice_entered_today_counts_in_the_current_facts_and_the_amount_limit(self):   # Repair A, F1
        self.set_limits()   # limit 5,000.00; Bayside already owes 2,400.00 across two invoices issued 2026-10-01
        self.add_invoice(self.bayside, 'DEMO-498', issueDate='2026-10-18', dueDate='2026-10-25', total='3000.00', stillOwed='3000.00', stillOwedAsOf='2026-10-18')
        self.wait_status(self.r, ('awaiting_owner',))
        a = self.assess()
        by = {x['name']: x for x in a['facts']['items']}
        self.assertEqual(by['debt_before_m']['value'], 540000)   # 2,400.00 + the 3,000.00 entered today
        out = next(c for c in a['policy']['checks'] if c['name'] == 'outstanding_amount')
        self.assertFalse(out['passes'], out)
        self.assertIn('5,400.00', out['sentence'])
        self.assertEqual(a['recommendation']['outcome'], 'escalate')
        self.assertIn('5,400.00 owed', a['facts']['currentText'])
        self.assertEqual(by['prior_billed_m']['value'], 240000)   # history still strictly before today

    def test_an_active_invoice_with_no_issue_date_counts_and_staff_cannot_act_on_a_case_it_makes_ineligible(self):   # Repair D
        self.set_limits()   # 30 days, 5,000.00; DEMO-501 asks 21 days
        self.assertEqual(self.assess()['recommendation']['outcome'], 'approve_within_authority')   # the control: as the records are, staff may act
        other = self.add_invoice(self.bayside, 'DEMO-497', dueDate='2026-10-05', total='9000.00', stillOwed='9000.00', stillOwedAsOf='2026-10-16')
        self.wait_status(self.r, ('awaiting_owner',))
        with self.app.lock, self.app.db:   # an invoice the records now hold without an issue date (the form and the import both refuse one)
            doc = self.app.fixture()
            next(i for i in doc['invoices'] if i['id'] == other['id']).pop('issueDate')
            self.app.save_doc(doc)
        a = self.assess()
        by = {x['name']: x for x in a['facts']['items']}
        self.assertEqual(by['debt_before_m']['value'], 240000 + 900000)
        self.assertEqual(by['overdue_before_m']['value'], 900000 + 0)
        self.assertEqual(by['prior_invoice_documents']['value'], 2)   # the undated one is left out of the history
        checks = {c['name']: c for c in a['policy']['checks']}
        self.assertFalse(checks['outstanding_amount']['passes'])
        self.assertFalse(checks['nothing_overdue']['passes'])
        self.assertEqual(a['recommendation']['outcome'], 'escalate')
        self.assertIn('1 invoice has no issue date: counted in what is owed and overdue, left out of the history.', a['facts']['currentText'])
        r = self.act()
        self.assertEqual(r[1]['error'], 'NOT_WITHIN_AUTHORITY', r)

    def test_a_failing_check_the_owner_marked_as_a_hard_rule_declines_by_policy(self):
        self.set_limits(hardRules=['nothing_overdue'])
        self.overdue_invoice()
        a = self.assess()
        self.assertEqual(a['recommendation']['outcome'], 'decline_by_policy')
        self.assertIn('overdue', a['recommendation']['reasons'][0])
        self.assertEqual(self.act()[1]['error'], 'NOT_WITHIN_AUTHORITY')

    def test_the_owner_s_decision_records_its_source_and_whether_it_followed_the_recommendation(self):
        self.set_limits()
        self.assess('owner')
        status, d, _ = self.decide(outcome='decline', approvedDueDate=None)
        self.assertEqual(status, 201, d)
        got = self.case()['decision']
        self.assertEqual((got['decisionSource'], got['followedRecommendation'], got['recommendation']['outcome']), ('owner', False, 'approve_within_authority'))

    def test_an_owner_decision_that_matches_the_recommendation_followed_it_and_one_with_no_assessment_has_none(self):
        self.set_limits()
        self.assess()
        self.assertEqual(self.decide()[0], 201)
        got = self.case()['decision']
        self.assertEqual((got['decisionSource'], got['followedRecommendation']), ('owner', True))
        other = self.second_case()
        c = self.call('/api/requests/' + other['id'], role='owner')[1]
        body = {'expectedRequestVersion': c['version'], 'analysisId': c['analysis']['id'], 'evidenceVersion': c['analysis']['snapshot']['evidenceVersion'],
                'outcome': 'approve', 'approvedDueDate': '2026-11-03', 'reason': 'Fine.'}
        self.assertEqual(self.call('/api/requests/' + other['id'] + '/decisions', body, 'owner', 'd2')[0], 201)
        got = self.call('/api/requests/' + other['id'], role='owner')[1]['decision']
        self.assertEqual((got['decisionSource'], got['recommendation'], got['followedRecommendation']), ('owner', None, None))

    def test_remember_can_end_on_a_date_and_a_bad_date_is_refused(self):
        keep = {'text': 'Fine to give Bayside up to 14 days', 'keepForCustomer': True}
        status, error, _ = self.decide(remember={**keep, 'until': '31 December'})
        self.assertEqual((status, error['field']), (400, 'remember'))
        self.assertEqual(self.decide(remember={**keep, 'until': '2026-12-31'})[0], 201)
        [line] = [x for s in self.app.statements() for x in s['lines'] if x['quote'] == keep['text']]
        self.assertEqual(line['until'], '2026-12-31')
        context = self.ok('ownerContext', customerId=self.bayside['id'])
        self.assertEqual([x['until'] for x in context['lines'] if x['quote'] == keep['text']], ['2026-12-31'])

    def test_two_concerns_on_an_assessed_case_escalate_it_and_the_queue_says_so(self):
        self.set_limits()
        self.assess()
        first = self.ok('raiseConcern', 'staff', key='k1', message=WORRY, requestId=self.r['id'], text=WORRY)
        self.assertEqual(first['line']['disagreesWith'], 'approve_within_authority')
        [row] = [x for x in self.ok('workQueue')['forYou'] if x['requestId'] == self.r['id']]
        self.assertEqual(row['why'], 'staff raised a concern')
        self.ok('raiseConcern', 'staff', key='k2', message=WORRY_AGAIN, requestId=self.r['id'], text=WORRY_AGAIN)
        for role, bucket in (('owner', 'forYou'), ('staff', 'waitingOnOthers')):
            [row] = [x for x in self.ok('workQueue', role)[bucket] if x['requestId'] == self.r['id']]
            self.assertEqual(row['why'], 'escalated: concern rounds', role)
        self.assertEqual([x['disagreesWith'] for x in self.case('staff')['concerns']], ['approve_within_authority'] * 2)

    def test_a_concern_on_a_case_never_assessed_is_kept_as_before(self):
        self.ok('raiseConcern', 'staff', key='k1', message=WORRY, requestId=self.r['id'], text=WORRY)
        self.ok('raiseConcern', 'staff', key='k2', message=WORRY_AGAIN, requestId=self.r['id'], text=WORRY_AGAIN)
        [row] = [x for x in self.ok('workQueue')['forYou'] if x['requestId'] == self.r['id']]
        self.assertEqual(row['why'], 'staff raised a concern')
        self.assertNotIn('disagreesWith', self.case()['concerns'][0])

    def test_only_the_owner_reads_and_sets_the_authority_and_the_agent_never_writes_it(self):
        self.assertEqual(self.authority('staff')[0], 403)
        self.assertEqual(self.authority('staff', method='GET')[0], 403)
        self.set_limits(maxPriorLateShare=0.25, hardRules=['late_history'], maxConcernRounds=3)
        got = self.authority(method='GET')[1]
        self.assertEqual((got['staffMayApproveUpToDays'], got['maxOutstandingText'], got['maxPriorLateShare'], got['hardRules'], got['maxConcernRounds']),
                         (30, 'AUD 5,000.00', 0.25, ['late_history'], 3))
        for bad in ({'staffMayApproveUpToDays': 0}, {'staffMayApproveUpToDays': '30'}, {'staffMayApproveUpToDays': True}, {'maxOutstanding': 'lots'},
                    {'maxOutstanding': '1.234'}, {'requireNothingOverdue': 'yes'}, {'maxPriorLateShare': 25}, {'hardRules': ['everything']},
                    {'hardRules': 'nothing_overdue'}, {'maxConcernRounds': 0}, {'maxConcernRounds': 2.5}, {'surprise': 1}):
            status, error = self.authority(**bad)
            self.assertEqual((status, error['error'] in ('INVALID_INPUT', 'INVALID_AMOUNT')), (400, True), bad)
        self.assertEqual(self.authority(method='GET')[1]['staffMayApproveUpToDays'], 30)   # a refused change changes nothing
        self.assertEqual([c['name'] for c in CAPABILITIES if c['name'].startswith(('set', 'save', 'update', 'write', 'change'))], [])
        for role, expected in (('staff', []), ('owner', [])):   # staff act within it only by pressing the button (pressedBy); no agent is offered a way to change it
            offered = [t['name'] for t in self.call('/api/tools', role=role)[1]['tools']]
            self.assertEqual([n for n in offered if 'uthority' in n], expected, role)

    def test_staff_case_details_carry_the_assessment_and_never_the_preparations(self):
        self.set_limits()
        self.assess()
        self.ok('prepareDecision', key='p1', message='approve 14 days', outcome='approve', days=14, requestId=self.r['id'])
        for role in ('staff', 'owner'):
            case = self.ok('caseDetails', role, requestId=self.r['id'])['case']
            self.assertEqual((case['assessment']['version'], case['assessment']['recommendation']['outcome'], set(case['assessment']) - {'atText'}),
                             (1, 'approve_within_authority', {'at', 'version', 'facts', 'policy', 'recommendation', 'evidence', 'basisSummary'}), role)
            self.assertEqual(case['preparations'] is None, role == 'staff')
        self.assertEqual(self.assess()['version'], 2)
        self.assertEqual(self.ok('caseDetails', 'staff', requestId=self.r['id'])['case']['assessment']['version'], 2)

    def test_a_request_made_after_its_due_date_is_approvable_when_nothing_else_is_overdue(self):
        self.set_limits(staffMayApproveUpToDays=60)
        self.add_invoice(self.bayside, 'DEMO-498', dueDate='2026-10-10', stillOwed='300.00', stillOwedAsOf='2026-10-16', total='300.00')
        late = self.wait_status(self.create('Could we pay invoice DEMO-498 on 2026-11-10 instead?', key='intake-late'), ('awaiting_owner',))
        a = self.ok('assessRequest', 'staff', requestId=late['id'])
        self.assertEqual(a['recommendation']['outcome'], 'approve_within_authority')
        self.assertEqual(a['facts']['ownInvoiceText'], 'This invoice was due on Sat 10 Oct 2026, 8 days before this date. By oldest-first matching, AUD 300.00 of it is still open.')
        self.assertEqual(next(c for c in a['policy']['checks'] if c['name'] == 'nothing_overdue')['sentence'], 'Nothing else is overdue.')
        self.assertEqual(self.tool('actWithinAuthority', 'staff', 'act-late', requestId=late['id'])[1]['ok'], True)

    def follow_up_due_source(self, key):
        later = self.wait_status(self.create('Could we pay invoice DEMO-501 on 2026-12-20 instead?', key=key), ('awaiting_owner',))
        view = self.call('/api/requests/' + later['id'], role='owner')[1]
        fact = next(f for f in view['analysis']['brief']['facts'] if f['key'] == 'currentEffectiveDueDate')
        return fact, self.ok('invoices', 'owner', customerId=self.r['customerId'], which='all')['invoices']

    def test_a_follow_up_case_names_the_staff_decision_that_moved_the_due_date(self):
        self.set_limits()
        self.assess()
        self.assertEqual(self.act()[1]['ok'], True)
        fact, invoices = self.follow_up_due_source('intake-follow-up')
        self.assertEqual((fact['kind'], fact['source']['decisionSource'], fact['source']['decidedBy']), ('owner_decision_record', 'staff_within_authority', 'staff_demo'))
        row = next(x for x in invoices if x['invoiceId'] == self.r['invoiceId'])
        self.assertTrue(row['dueNowSource'].endswith(" by staff, within the owner's authority"), row['dueNowSource'])

    def test_a_decision_stored_without_attribution_stays_neutral(self):
        self.set_limits()
        self.assess()
        self.assertEqual(self.act()[1]['ok'], True)
        old = self.app.get(self.r['id'])
        for k in ('decisionSource', 'decidedBy', 'actorName', 'actorRole'):
            old['decision'].pop(k, None)
        self.app.save(old)
        fact, invoices = self.follow_up_due_source('intake-old-shape')
        self.assertTrue(all(k not in fact['source'] for k in ('decisionSource', 'decidedBy', 'actorName', 'actorRole')), fact['source'])
        row = next(x for x in invoices if x['invoiceId'] == self.r['invoiceId'])
        self.assertTrue(row['dueNowSource'].startswith('approved to ') and ' by ' not in row['dueNowSource'], row['dueNowSource'])

    def test_after_the_concern_rounds_staff_cannot_act_even_when_the_checks_pass(self):
        self.set_limits()
        self.assess()
        self.ok('raiseConcern', 'staff', key='k1', message=WORRY, requestId=self.r['id'], text=WORRY)
        self.ok('raiseConcern', 'staff', key='k2', message=WORRY_AGAIN, requestId=self.r['id'], text=WORRY_AGAIN)
        body = self.act()[1]
        self.assertEqual((body['error'], body['failing']), ('NOT_WITHIN_AUTHORITY', ['concern rounds']))
        self.assertIsNone(self.case()['decision'])

    def test_similar_decisions_are_newest_first_and_the_limits_say_how_overdue_is_judged(self):
        self.assertEqual(self.decide()[0], 201)
        a = self.ok('assessRequest', 'owner', customerId=self.bayside['id'])
        self.assertEqual((a['evidence']['decisionsForThisCustomer'], len(a['evidence']['similar'])), (1, 1))
        self.assertIn('Overdue is judged by the due dates recorded on the invoices, not by extensions already granted.', a['limitations'])

    def test_a_preparation_keeps_what_to_remember_through_revisions_and_the_confirm_commits_it(self):
        keep = {'text': 'Fine to give Bayside up to 14 days', 'keepForCustomer': True, 'until': '2026-12-31'}
        first = self.ok('prepareDecision', key='p1', message='approve 14 days', outcome='approve', days=14, requestId=self.r['id'], remember=keep)
        self.assertEqual({k: v for k, v in first['prepared']['remember'].items() if k != 'untilText'}, keep)
        second = self.ok('prepareDecision', key='p2', message='make it ten days', days=10, requestId=self.r['id'])   # remember not given: retained
        p = second['prepared']
        self.assertEqual((p['days'], {k: v for k, v in p['remember'].items() if k != 'untilText'}), (10, keep))
        self.assertEqual([x['remember']['until'] for x in self.ok('caseDetails', requestId=self.r['id'])['case']['preparations']], ['2026-12-31'] * 2)
        self.assertEqual(self.refused('prepareDecision', key='p3', message='ten days', days=10, requestId=self.r['id'], remember={'text': 'x', 'until': 'soon'}), 'INVALID_ARGUMENT')
        c = self.case()
        body = {'expectedRequestVersion': c['version'], 'analysisId': c['analysis']['id'], 'evidenceVersion': c['analysis']['snapshot']['evidenceVersion'],
                'outcome': p['outcome'], 'approvedDueDate': p['approvedDueDate'], 'reason': p['reason'], 'preparedVersion': p['version'],
                'suggestionShown': c['preparedDecision']['suggestionShown']}
        self.assertEqual(self.call('/api/requests/' + self.r['id'] + '/decisions', body, 'owner', 'confirm-1')[0], 201)
        [line] = [x for s in self.app.statements() for x in s['lines'] if x['quote'] == keep['text']]
        self.assertEqual(line['until'], '2026-12-31')

    def test_the_stored_assessment_carries_the_evidence_for_the_case_details(self):
        self.set_limits()
        self.assess()
        for role in ('staff', 'owner'):
            ev = self.ok('caseDetails', role, requestId=self.r['id'])['case']['assessment']['evidence']
            self.assertEqual((ev['decisionsRecorded'], ev['decisionsForThisCustomer'], ev['similar']), (0, 0, []), role)

    def test_staff_assessment_sentences_are_plain_facts(self):
        a = self.assess('staff')
        self.assertEqual(a['recommendation']['reasons'], ['No limits are set for staff to act within, so this case goes to the owner.'])
        self.assertIn('so this case goes to the owner', next(c for c in a['policy']['checks'] if c['name'] == 'requested_days')['sentence'])
        self.assertIn('no day limit', self.assess('owner')['recommendation']['reasons'][0])
        self.set_limits(staffMayApproveUpToDays=14, hardRules=['requested_days'])
        for role in ('staff', 'owner'):
            a = self.assess(role)
            texts = [c['sentence'] for c in a['policy']['checks']] + a['recommendation']['reasons'] + a['limitations'] + [x['text'] for x in a['facts']['items']]
            for text in texts:
                self.assertNotIn('never shown to staff', text)
                self.assertNotIn('owner-only', text.lower())

    def test_staff_read_the_neutral_sentence_in_the_stored_assessment_and_the_owner_the_owner_worded_one(self):
        self.assess('owner')   # keeps an assessment with no limits set
        staff = self.ok('caseDetails', 'staff', requestId=self.r['id'])['case']['assessment']
        text = json.dumps(staff)
        self.assertIn('No limits are set for staff to act within, so this case goes to the owner.', text)
        self.assertNotIn('The owner has set no day limit', text)
        self.assertIn('The owner has set no day limit for staff', json.dumps(self.ok('caseDetails', 'owner', requestId=self.r['id'])['case']['assessment']))
        self.assertIn('The owner has set no day limit for staff', json.dumps(self.app.get(self.r['id'])['assessment']))   # stored as the owner's

    def test_the_case_says_when_its_assessment_no_longer_holds_for_changed_records_or_limits(self):
        """An assessment of a case not yet decided reads stale in the case details once the customer's records or the owner's limits
        changed after it, so the Lab drops Act before anyone presses it (live, 24 Oct: QG-3 added, the old card still offered Act)."""
        self.set_limits()
        self.assess()
        stale = lambda: self.ok('caseDetails', 'staff', requestId=self.r['id'])['case']['assessment'].get('stale')
        self.assertIsNone(stale())
        self.set_limits(staffMayApproveUpToDays=29)
        self.assertEqual(stale()['reason'], 'limits')
        self.assess()
        self.assertIsNone(stale())   # assessed again: current
        self.overdue_invoice()   # a new invoice for the customer; the case goes back through its analysis
        self.assertEqual(stale()['reason'], 'records')
        self.assertIn('assess', stale()['text'].lower())
        self.assess()
        self.assertIsNone(stale())

    def test_acting_is_refused_when_the_owner_lowers_a_limit_after_the_assessment(self):
        self.set_limits()
        self.assertEqual(self.assess()['recommendation']['outcome'], 'approve_within_authority')
        self.set_limits(staffMayApproveUpToDays=1)
        body = self.act()[1]
        self.assertEqual((body['ok'], body['error'], body['failing']), (False, 'NOT_WITHIN_AUTHORITY', ['requested days over the staff limit']))
        self.assertIsNone(self.case()['decision'])

    def test_the_assess_tool_says_whether_staff_may_act_with_no_score_and_never_acts(self):
        self.set_limits()
        a = self.ok('assessRequest', 'staff', requestId=self.r['id'])
        self.assertEqual(a['recommendation']['outcome'], 'approve_within_authority')
        self.assertNotIn('score', json.dumps(a).lower())
        self.assertNotIn('actWithinAuthority', [t['name'] for t in self.call('/api/tools', role='staff')[1]['tools']])   # a person presses Act within authority
        self.assertIsNone(self.case()['decision'])


class ZeroScaleTests(RecordsCase):
    def test_a_workspace_of_a_currency_without_decimals_shows_none(self):
        self.start()
        self.practice_ready(currency='VND', scale=0)
        c = self.add_customer('Hoang Foods')
        self.add_invoice(c, 'HD-1', dueDate='2026-09-01', issueDate='2026-08-01', total='5000000')
        a = self.call('/api/tools/assessRequest', {'args': {'customerId': c['id']}}, 'staff')[1]['result']
        by = {x['name']: x for x in a['facts']['items']}
        self.assertEqual(by['overdue_before_m']['text'], 'VND 5,000,000 is overdue, the oldest 47 days past due.')
        self.assertNotIn('.00', json.dumps(a))
        self.assertEqual((a['recorded'], a['requestId']), (False, None))
        self.assertEqual(a['recommendation']['outcome'], 'escalate')


if __name__ == '__main__':
    unittest.main()
