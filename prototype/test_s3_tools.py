"""The S3 read tools (docs/ADAPTIVE-DECISION-AUTHORITY.md, "As built (S3)"): whatIsNeeded, comparableCases, customerStatus (Staff and Owner), policyBacktest and
impactSummary (Owner only). On by default since S6a (the Owner can switch each off under Setup); none stores or decides anything; each result carries a compact `forModel` of
bounded size for the Lab to give the model. Deterministic, on the fictional delegation demonstration (delegation_demo.py) as of 2026-10-24; no model is asked.
The pure views are tested without a server."""
import json
import unittest

import agent_views
import delegation
from coordinator import CAPABILITIES, tools_for
from test_delegation import DelegationCase

NEW = ('whatIsNeeded', 'comparableCases', 'customerStatus', 'policyBacktest', 'impactSummary')
TABLES = ('decision_cases', 'case_events', 'delegation_policies', 'confirmed_facts', 'actions', 'requests')


class S3Case(DelegationCase):
    def setUp(self):
        super().setUp()
        for name in NEW:
            self.assertEqual(self.call('/api/agent-tools', {'tool': name, 'enabled': True}, 'owner', 'on3-' + name)[0], 200)

    def counts(self):
        return {t: self.row('SELECT COUNT(*) FROM ' + t)[0][0] for t in TABLES}

    def ok(self, name, role='staff', **args):
        body = self.tool(name, role, **args)
        self.assertTrue(body['ok'], body)
        return body

    def fails(self, name, role='staff', **args):
        body = self.tool(name, role, **args)
        self.assertFalse(body['ok'], body)
        return body

    def lakeside(self, **more):
        return {'kind': 'trial_credit', 'customerId': self.cust['lakeside'], 'orderAmount': '600.00', 'termsDays': 14, **more}


# ---------------------------------------------------------------- the registry

class RegistryTests(unittest.TestCase):
    def test_the_five_tools_are_read_only_registry_rows_that_are_on_by_default_since_s6a(self):
        rows = {c['name']: c for c in CAPABILITIES}
        for name in NEW:
            self.assertEqual((rows[name]['kind'], rows[name]['defaultEnabled'], rows[name]['needsConfirmation']), ('read', True, False), name)
        both = ['staff', 'owner']
        self.assertEqual([rows[n]['roles'] for n in NEW], [both, both, both, ['owner'], ['owner']])
        self.assertEqual({t['function']['name'] for t in tools_for('staff', None)} & set(NEW), set(NEW[:3]))
        self.assertEqual({t['function']['name'] for t in tools_for('owner', None)} & set(NEW), set(NEW))   # a fresh database offers them
        off = {n: {'enabled': False} for n in NEW}   # the Owner can still switch each off under Setup
        for role in both:
            self.assertFalse(set(NEW) & {t['function']['name'] for t in tools_for(role, off)}, role)
        on = {n: {'enabled': True} for n in NEW}
        self.assertEqual({t['function']['name'] for t in tools_for('staff', on)} & set(NEW), set(NEW[:3]))
        self.assertEqual({t['function']['name'] for t in tools_for('owner', on)} & set(NEW), set(NEW))


# ---------------------------------------------------------------- whatIsNeeded

class WhatIsNeededTests(S3Case):
    def test_a_trial_credit_with_nothing_on_file_lists_what_staff_can_provide(self):
        before = self.counts()
        body = self.ok('whatIsNeeded', **self.lakeside())
        r = body['result']
        self.assertEqual((r['stored'], r['kind'], r['evidence']['status']), (False, 'trial_credit', 'missing'))
        self.assertEqual([m['key'] for m in r['evidence']['missing']], ['deposit', 'business_identity'])
        fm = r['forModel']
        self.assertEqual((fm['status'], [m['need'] for m in fm['staffCanProvide']]), ('missing', ['Deposit', 'Business identity']))
        self.assertIn('Staff can provide: deposit and business identity.', fm['statusText'])
        self.assertLessEqual(len(json.dumps(fm)), agent_views.STATUS_LIMIT)
        self.assertEqual(set(r) - {'subject'}, {'stored', 'kind', 'customer', 'policyVersion', 'evidence', 'note', 'forModel'})   # the evidence section and forModel, nothing else of the evaluation
        self.assertEqual(self.counts(), before)

    def test_it_is_the_evidence_assessDecision_would_use(self):
        for args in (self.lakeside(), self.trial('northside', '800.00'), self.trial('harbourline', '5000.00')):
            args = {k: v for k, v in args.items() if k not in ('recommendation', 'reasoning')}
            needed = self.ok('whatIsNeeded', **args)['result']['evidence']
            assessed = self.ok('assessDecision', **args)['result']['evidence']
            self.assertEqual(needed, assessed, args)

    def test_enough_on_file_says_so_and_an_extension_works(self):
        r = self.ok('whatIsNeeded', **{k: v for k, v in self.trial('northside', '800.00').items() if k not in ('recommendation', 'reasoning')})['result']
        self.assertEqual((r['evidence']['status'], r['forModel']['staffCanProvide']), ('sufficient', []))
        self.assertIn('call resolveDecision', r['forModel']['nextStep'])
        e = self.ok('whatIsNeeded', kind='extension', customerId=self.cust['bayview'], invoiceReference='DEMO-301', requestedDueDate='2026-11-10')['result']
        self.assertEqual((e['kind'], e['evidence']['status']), ('extension', 'sufficient'))

    def test_staff_confirmations_are_counted_and_the_owner_may_ask_too(self):
        case = self.resolved(**self.trial('lakeside', '600.00'))
        from test_decision_loop import LAKESIDE_ITEMS
        small = [{**LAKESIDE_ITEMS[0], 'amount': '100.00'}, LAKESIDE_ITEMS[1]]
        self.assertEqual(self.submit(case['actionId'], small)[0], 200)
        r = self.ok('whatIsNeeded', 'owner', **self.lakeside())['result']
        self.assertEqual([m['key'] for m in r['evidence']['missing']], ['deposit'])   # the identity Staff confirmed counts now; the deposit is still short
        self.assertEqual(r['evidence']['verifiedDeposit'], 10000)
        self.assertEqual([m['need'] for m in r['forModel']['staffCanProvide']], ['Deposit'])

    def test_a_refused_call_asks_the_question_instead_of_guessing(self):
        body = self.fails('whatIsNeeded', kind='trial_credit', customerId=self.cust['lakeside'])
        self.assertEqual((body['error'], body['hint']['ask']), ('INVALID_ARGUMENT', 'amount'))
        body = self.fails('whatIsNeeded', kind='extension', customerId=self.cust['riverside'], days=7)
        self.assertEqual((body['hint']['ask'], body['hint']['options']), ('invoice', ['DEMO-504', 'DEMO-505']))
        self.assertEqual(self.fails('whatIsNeeded', customerId=self.cust['lakeside'])['hint']['ask'], 'kind')


# ---------------------------------------------------------------- comparableCases

class ComparableCasesTests(S3Case):
    def test_staff_get_analogies_without_the_owners_reasons_and_the_owner_gets_them(self):
        args = {k: v for k, v in self.trial('harbourline', '5000.00').items() if k not in ('recommendation', 'reasoning')}
        staff = self.ok('comparableCases', **args)['result']
        owner = self.ok('comparableCases', 'owner', **args)['result']
        self.assertTrue(staff['comparables'])
        self.assertEqual([c['id'] for c in staff['comparables']], [c['id'] for c in owner['comparables']])
        self.assertTrue(all('ownerReason' not in c for c in staff['comparables']))
        self.assertTrue(any(c.get('ownerReason') for c in owner['comparables']))
        reasons = [c['ownerReason'] for c in owner['comparables'] if c.get('ownerReason')]
        self.assertFalse(any(reason[:20] in json.dumps(staff) for reason in reasons))
        self.assertFalse(any('ownerReason' in row for row in staff['forModel']['comparables']))
        self.assertTrue(any('ownerReason' in row for row in owner['forModel']['comparables']))
        self.assertTrue(all("not this customer's history" in c['analogyNote'] or c['sameCustomer'] for c in staff['comparables']))
        for r in (staff, owner):
            self.assertLessEqual(len(json.dumps(r['forModel'])), agent_views.ANALYSIS_LIMIT)
            self.assertEqual((r['stored'], r['forModel']['status']), (False, 'comparables'))
        self.assertIn('analogies', staff['forModel']['statusText'])

    def test_they_are_the_comparables_the_evaluation_uses_and_nothing_is_stored(self):
        args = {k: v for k, v in self.trial('northside', '800.00').items() if k not in ('recommendation', 'reasoning')}
        before = self.counts()
        got = self.ok('comparableCases', **args)['result']
        assessed = self.ok('assessDecision', **args)['result']
        self.assertEqual([c['id'] for c in got['comparables']], [c['id'] for c in assessed['comparables']])
        self.assertEqual(got['declinedMajority'], assessed['reliability']['comparablesDeclinedMajority'])
        self.assertEqual(self.counts(), before)
        self.assertTrue(all(c['dataset'] in ('fictional_example', 'live') or not c['dataset'].startswith('fictional_eval') for c in got['comparables']))


# ---------------------------------------------------------------- customerStatus

class CustomerStatusTests(S3Case):
    def test_a_customer_with_no_case_has_none(self):
        r = self.ok('customerStatus', customerId=self.cust['northside'])['result']
        self.assertEqual((r['latest'], r['cases'], r['trialInForce'], r['waitingForStaff'], r['lastOutcome']), (None, [], None, [], None))
        self.assertEqual(r['forModel']['status'], 'no_case')
        self.assertIn('no decision case', r['forModel']['statusText'])

    def test_waiting_evidence_the_line_in_force_and_the_last_observation(self):
        lake = self.resolved(**self.trial('lakeside', '600.00'))
        north = self.resolved(**self.trial('northside', '800.00'))
        bay = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        before = self.counts()
        w = self.ok('customerStatus', customerId=self.cust['lakeside'])['result']
        self.assertEqual((w['latest']['caseId'], w['latest']['status']), (lake['caseId'], 'gathering_evidence'))
        self.assertEqual([(x['caseId'], x['actionId'], x['evidenceLink']) for x in w['waitingForStaff']], [(lake['caseId'], lake['actionId'], '#/actions/' + lake['actionId'])])
        self.assertEqual(w['waitingForStaff'][0]['needs'], ['Deposit', 'Business identity'])
        self.assertIsNone(w['trialInForce'])
        n = self.ok('customerStatus', customerId=self.cust['northside'])['result']
        self.assertEqual((n['latest']['status'], n['waitingForStaff']), ('decided', []))
        self.assertEqual(n['trialInForce']['caseId'], north['caseId'])
        self.assertIn('Trial credit in force', n['forModel']['trialInForce'])
        self.assertIsNone(n['lastOutcome'])
        with self.app.lock:
            self.app.observe_outcomes()
        b = self.ok('customerStatus', customerId=self.cust['bayview'])['result']
        self.assertEqual(b['lastOutcome']['caseId'], bay['caseId'])
        self.assertTrue(b['lastOutcome']['outcome'])
        self.assertEqual(self.counts()['decision_cases'], before['decision_cases'])
        for r in (w, n, b):
            self.assertLessEqual(len(json.dumps(r['forModel'])), agent_views.STATUS_LIMIT)

    def test_both_roles_read_it_and_the_owner_reasons_are_not_in_it(self):
        self.resolved(**self.trial('harbourline', '5000.00'))
        staff = self.ok('customerStatus', customerId=self.cust['harbourline'])['result']
        owner = self.ok('customerStatus', 'owner', customerId=self.cust['harbourline'])['result']
        self.assertEqual(staff, owner)
        self.assertEqual(staff['latest']['status'], 'awaiting_owner')
        for key in ('feedback', 'override', 'ownerReason'):
            self.assertNotIn(key, json.dumps(staff))

    def test_an_unknown_customer_asks_which(self):
        body = self.fails('customerStatus', customerId='Zzyzx Traders')
        self.assertEqual((body['error'], body['hint']['ask']), ('INVALID_ARGUMENT', 'customer'))


# ---------------------------------------------------------------- policyBacktest and impactSummary (Owner only)

class PolicyBacktestTests(S3Case):
    def test_it_is_for_the_owner_only(self):
        for name in ('policyBacktest', 'impactSummary'):
            status, body, _ = self.call('/api/tools/' + name, {'args': {}}, 'staff', 'staff-' + name)
            self.assertEqual((status, body['error']), (403, 'FORBIDDEN'), name)   # not even offered to Staff: refused at the tool surface
        with self.app.lock:   # and the tool itself refuses a role it is not for, were it ever reached
            from server import DeskTools, ToolError
            tools = DeskTools(self.app, {'role': 'staff', 'id': 'x'}, '', None, None, 1)
            for name in ('_policyBacktest', '_impactSummary'):
                with self.assertRaises(ToolError):
                    getattr(tools, name)({})
        for name in ('policyBacktest', 'impactSummary'):
            status, body, _ = self.call('/api/tools', None, 'staff')
            self.assertNotIn(name, [t['name'] for t in body['tools']])
            status, body, _ = self.call('/api/tools', None, 'owner')
            self.assertIn(name, [t['name'] for t in body['tools']])

    def test_no_change_gives_the_same_counts_twice_and_stores_nothing(self):
        before = (self.counts(), self.policy()['version'])
        r = self.ok('policyBacktest', 'owner')['result']
        self.assertEqual((r['stored'], r['saved'], r['changed']), (False, False, []))
        for kind in delegation.KINDS:
            self.assertEqual(r['categories'][kind]['current'], r['categories'][kind]['withChanges'])
        self.assertEqual((self.counts(), self.policy()['version']), before)
        self.assertIn('Nothing was saved', r['note'])
        self.assertIn('SIMULATION', r['label'])

    def test_a_change_moves_the_counts_the_way_the_back_test_does(self):
        current = self.policy()
        memory = None
        with self.app.lock:
            memory = self.app.dg_memory(self.app.evidence(), self.app.fixture())
        r = self.ok('policyBacktest', 'owner', changes={'extensions': {'maxDays': 5}, 'newCustomers': {'maxExposure': '100.00'}})['result']
        self.assertEqual(sorted(r['changed']), ['extensions.maxDays', 'newCustomers.maxExposure'])
        rules = {k: current[k] for k in delegation.POLICY_KEYS}
        for kind in delegation.KINDS:
            want = delegation.track_record(rules, kind, memory)['evaluation']
            got = r['categories'][kind]['current']['fictionalEvaluation']
            self.assertEqual({k: want[k] for k in got}, got, kind)
        loose = r['categories']['extension']
        self.assertLessEqual(loose['withChanges']['fictionalEvaluation']['wouldApprove'], loose['current']['fictionalEvaluation']['wouldApprove'])
        self.assertLess(loose['withChanges']['fictionalEvaluation']['wouldApprove'], loose['current']['fictionalEvaluation']['wouldApprove'])   # five days is tighter than thirty
        self.assertLessEqual(len(json.dumps(r['forModel'])), agent_views.ANALYSIS_LIMIT)
        self.assertIn('fictional simulation', json.dumps(r['forModel']['categories']))
        self.assertEqual(r['forModel']['changed'], r['changed'])

    def test_a_bad_change_is_refused_and_nothing_is_saved(self):
        for changes in ('x', {'allowExternalMessages': True}, {'extensions': {'maxDays': 'ten'}}, {'newCustomers': {'maxExposure': 'lots'}}, {'extensions': {'nope': 1}}):
            body = self.fails('policyBacktest', 'owner', changes=changes)
            self.assertEqual(body['error'], 'INVALID_ARGUMENT', changes)
        self.assertEqual(self.policy()['version'], 1)

    def test_live_reviewed_cases_are_counted_apart(self):
        approved = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        status, out = self.feedback(approved['caseId'], {'verdict': 'agree', 'reason': 'Fictional.'})
        self.assertEqual(status, 200, out)
        r = self.ok('policyBacktest', 'owner')['result']
        live = r['categories']['extension']['current']['live']
        self.assertEqual((live['reviewed'], live['ownerApproved']), (1, 1))
        self.assertGreater(r['categories']['extension']['current']['fictionalEvaluation']['reviewed'], 1)
        self.assertIn('live: would approve 1 of 1 reviewed', json.dumps(r['forModel']))


class ImpactSummaryTests(S3Case):
    def test_it_is_the_impact_endpoints_figures_for_the_owner(self):
        self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        self.resolved(**self.trial('lakeside', '600.00'))
        self.resolved(**self.trial('harbourline', '5000.00'))
        before = self.counts()
        r = self.ok('impactSummary', 'owner')['result']
        status, endpoint, _ = self.call('/api/delegation/impact', None, 'owner')
        self.assertEqual(status, 200, endpoint)
        for key in ('counts', 'cases', 'autonomousCoverage', 'escalationRate', 'evidenceRequests', 'timeToDecisionSeconds', 'overrides', 'liveAgreement', 'outcomes', 'timeSaved'):
            self.assertEqual(r[key], endpoint[key], key)
        self.assertEqual(r['dataset'], 'live')
        fm = r['forModel']
        self.assertLessEqual(len(json.dumps(fm)), agent_views.ANALYSIS_LIMIT)
        self.assertEqual(fm['counts'], {k: v['value'] for k, v in endpoint['counts'].items()})
        self.assertIn('autonomousCoverage', fm['figures'])
        self.assertIn('of', fm['figures']['autonomousCoverage'])   # numerator of denominator, with its source
        self.assertIn('derived', fm['figures']['escalationRate'])
        self.assertEqual(self.counts(), before)

    def test_a_window_and_a_bad_date(self):
        self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        r = self.ok('impactSummary', 'owner', **{'from': '2020-01-01', 'to': '2020-01-31'})['result']
        self.assertEqual(r['counts']['autonomous']['value'], 0)
        self.assertEqual(r['forModel']['window'], {'from': '2020-01-01', 'to': '2020-01-31', 'policyVersion': None})
        self.assertEqual(self.fails('impactSummary', 'owner', **{'from': 'last week'})['error'], 'INVALID_ARGUMENT')
        self.assertEqual(self.fails('impactSummary', 'owner', **{'from': '2026-02-30'})['error'], 'INVALID_ARGUMENT')

    def test_the_route_still_needs_a_person(self):
        self.assertEqual(self.call('/api/delegation/impact', None, 'staff')[0], 403)


# ---------------------------------------------------------------- the pure views

class ViewTests(unittest.TestCase):
    def test_fit_shortens_lists_then_strings_and_never_the_status(self):
        out = {'status': 'x', 'rows': [{'a': 'y' * 200}] * 10, 'text': 'z' * 900}
        agent_views.fit(out, 600, lists=('rows',), strings=('text',))
        self.assertLessEqual(agent_views.size(out), 600)
        self.assertEqual(out['status'], 'x')
        self.assertEqual(len(out['rows']), 1)

    def test_deep_merge_and_changed_paths(self):
        base = {'extensions': {'enabled': True, 'maxDays': 30}, 'mode': 'delegated'}
        changes = {'extensions': {'maxDays': 45, 'enabled': True}, 'mode': 'advisory'}
        self.assertEqual(agent_views.deep_merge(base, changes), {'extensions': {'enabled': True, 'maxDays': 45}, 'mode': 'advisory'})
        self.assertEqual(agent_views.changed_paths(base, changes), ['extensions.maxDays', 'mode'])
        self.assertEqual(base['extensions']['maxDays'], 30)

    def test_an_empty_impact_is_not_known_not_zero(self):
        self.assertEqual(agent_views.metric_text({'value': None, 'numerator': 0, 'denominator': 0, 'source': 'derived'}), 'not known yet')
        self.assertEqual(agent_views.metric_text({'value': 0.5, 'numerator': 1, 'denominator': 2, 'source': 'derived'}), '1 of 2 (0.5, derived)')


if __name__ == '__main__':
    unittest.main()


# ---------------------------------------------------------------- workQueue lists the decision cases (S6a)

class WorkQueueDecisionCaseTests(S3Case):
    def queue(self, role):
        body = self.tool('workQueue', role)
        self.assertTrue(body['ok'], body)
        return body['result']

    def test_the_owner_sees_the_case_waiting_for_the_owner_with_its_link(self):
        hl = self.resolved(**self.trial('harbourline', '5000.00'))
        lake = self.resolved(**self.trial('lakeside', '600.00'))
        before = self.counts()
        q = self.queue('owner')
        self.assertEqual([(x['caseId'], x['status']) for x in q['decisionCasesForYou']], [(hl['caseId'], 'awaiting_owner')])
        row = q['decisionCasesForYou'][0]
        self.assertEqual((row['customer'], row['kind'], row['link']), (self.row('SELECT json_extract(data, "$.customerName") FROM decision_cases WHERE id=?', hl['caseId'])[0][0], 'trial_credit', '#/review'))
        self.assertIn('4,000', row['exposureText'])
        self.assertTrue(row['since'] and row['sinceText'])
        self.assertEqual([x['caseId'] for x in q['decisionCasesWaitingOnOthers']], [lake['caseId']])   # Lakeside waits on Staff for evidence
        # The sentence names every case (Hoang, 6 Nov 2026: with two waiting, the Owner's assistant reported one; the code-written sentence said nothing waited).
        self.assertIn('1 decision case needs your decision: ' + row['customer'] + ' (trial credit, ' + row['exposureText'] + '). Decide on the Decide page. 1 decision case is with staff: ', q['summaryText'])
        fm = q['forModel']
        self.assertIn(q['summaryText'], json.dumps(fm))   # the model gets the same sentence
        self.assertEqual([x['caseId'] for x in fm['decisionCasesForYou']], [hl['caseId']])
        self.assertEqual((fm['link'], fm['decisionCasesWithOthers']), ('#/review', 1))
        self.assertIn('4,000', fm['decisionCasesForYou'][0]['exposure'])
        self.assertLessEqual(len(json.dumps(fm)), agent_views.QUEUE_LIMIT)
        self.assertEqual(self.counts(), before)   # a read

    def test_staff_see_the_case_gathering_evidence_with_what_is_needed(self):
        hl = self.resolved(**self.trial('harbourline', '5000.00'))
        lake = self.resolved(**self.trial('lakeside', '600.00'))
        q = self.queue('staff')
        self.assertEqual([x['caseId'] for x in q['decisionCasesForYou']], [lake['caseId']])
        row = q['decisionCasesForYou'][0]
        self.assertEqual((row['link'], row['needs']), ('#/actions/' + lake['actionId'], ['Deposit', 'Business identity']))
        self.assertEqual([x['caseId'] for x in q['decisionCasesWaitingOnOthers']], [hl['caseId']])
        self.assertEqual(q['forModel']['decisionCasesForYou'][0]['needs'], ['Deposit', 'Business identity'])
        self.assertLessEqual(len(json.dumps(q['forModel'])), agent_views.QUEUE_LIMIT)

    def test_decided_cases_and_an_empty_queue(self):
        self.resolved(**self.trial('northside', '800.00'))   # approved by the agent
        for role in ('owner', 'staff'):
            q = self.queue(role)
            self.assertEqual((q['decisionCasesForYou'], q['decisionCasesWaitingOnOthers']), ([], []), role)
            self.assertEqual(q['forModel']['decisionCasesForYou'], [])
            self.assertIn('Nothing is waiting for you.', q['forModel']['statusText'])   # the request queue is still there, as the sentence to repeat

    def test_the_request_queue_is_unchanged(self):
        q = self.queue('owner')
        self.assertEqual((q['forYou'], q['waitingOnOthers']), ([], []))
        self.assertIn('summaryText', q)

    def test_the_model_view_stays_within_the_bound_with_many_cases(self):
        cases = [{'caseId': 'case_%016d' % i, 'customer': 'Harbourline Catering (fictional)', 'kind': 'trial_credit', 'status': 'awaiting_owner', 'exposureText': 'AUD 4,000.00',
                  'since': '2026-10-27T15:11:51+00:00', 'link': '#/review', 'needs': []} for i in range(9)]
        out = agent_views.queue_for_model('owner', 'x' * 900, cases, 3)
        self.assertEqual(out['statusText'], 'x' * 900)   # the sentence is kept whole: the lists give way first (12 Nov 2026)
        self.assertLessEqual(len(json.dumps(out)), agent_views.QUEUE_LIMIT)
        self.assertEqual(out['link'], '#/review')
        self.assertGreaterEqual(len(out['decisionCasesForYou']), 1)


# ---------------------------------------------------------------- doctor (Owner only, 11 Nov 2026)

class DoctorToolTests(S3Case):
    def setUp(self):
        super().setUp()
        self.assertEqual(self.call('/api/agent-tools', {'tool': 'doctor', 'enabled': True}, 'owner', 'on3-doctor')[0], 200)

    def test_the_owner_gets_the_endpoints_lines_for_the_model(self):
        self.resolved(**self.extension('bayview', 'DEMO-301', date='2027-01-30', reasoning='Fictional: a long ask.'))
        before = self.counts()
        r = self.ok('doctor', 'owner', question='came', days='all')['result']
        status, endpoint, _ = self.call('/api/delegation/doctor?question=came&days=all', None, 'owner')
        self.assertEqual(status, 200, endpoint)
        self.assertEqual(r['forModel']['facts'], endpoint['facts'][1:])   # the headline is statusText, not repeated
        self.assertEqual(r['forModel']['enough'], endpoint['enough'])
        self.assertEqual((r['forModel']['status'], r['forModel']['question'], r['forModel']['statusText']), ('doctor', 'came', endpoint['headline']))
        self.assertIn('Quick setup', r['forModel']['howToChange'])
        self.assertLessEqual(len(json.dumps(r['forModel'])), agent_views.DOCTOR_LIMIT)
        self.assertEqual(self.counts(), before)

    def test_without_a_question_it_gives_six_headlines(self):
        r = self.ok('doctor', 'owner')['result']
        self.assertEqual(len(r['forModel']['facts']), 6)
        self.assertTrue(r['forModel']['facts'][0].startswith('Why do so many requests still come to me? '), r['forModel']['facts'][0])

    def test_staff_and_bad_arguments_are_refused(self):
        status, body, _ = self.call('/api/tools/doctor', {'args': {}}, 'staff', 'staff-doctor')
        self.assertEqual((status, body['error']), (403, 'FORBIDDEN'))   # not offered to Staff
        with self.app.lock:   # and the tool itself refuses Staff, were it ever reached
            from server import DeskTools, ToolError
            with self.assertRaises(ToolError):
                DeskTools(self.app, {'role': 'staff', 'id': 'x'}, '', None, None, 1)._doctor({})
        self.assertEqual(self.fails('doctor', 'owner', question='nope')['error'], 'INVALID_ARGUMENT')
        self.assertEqual(self.fails('doctor', 'owner', days=7)['error'], 'INVALID_ARGUMENT')
        self.assertTrue(self.ok('doctor', 'owner', question='help', days=30)['ok'])   # a number is taken as its text

    def test_long_facts_are_cut_by_whole_lines_and_say_so(self):
        lines = ['line %d ' % i + 'x' * 200 for i in range(40)]
        view = {'question': 'came', 'headline': 'H', 'enough': False, 'findings': lines[:20], 'suggestions': [{'text': t} for t in lines[20:]], 'notes': ['NOTE limits only', 'NOTE too few'],
                'facts': ['H'] + lines + ['NOTE limits only', 'NOTE too few']}
        out = agent_views.doctor_for_model(view)
        self.assertLessEqual(len(json.dumps(out)), agent_views.DOCTOR_LIMIT)
        self.assertEqual(out['facts'][-2:], ['NOTE limits only', 'NOTE too few'])   # the honesty notes are kept
        self.assertIn('more lines left out', out['facts'][-3])
        self.assertIs(out['enough'], False)
