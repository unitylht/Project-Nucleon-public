"""Slice S1b of the decision loop: the track-record sources (D7), tightening suggestions, the impact endpoint and the structured hints with a compact
model-facing result. Deterministic, on the fictional delegation demonstration as of 2026-10-24; no model is ever asked. Every figure is a fictional POC value."""
import json
import unittest

import delegation
import delegation_demo
import server
from records import RecordsError
from test_decision_loop import LAKESIDE_ITEMS, LoopCase
from test_delegation import AS_OF, MEMORY, SETTINGS, evaluate, ledger, memory, policy, trial_request


def live_row(i, decision='approve', kind_of_verdict='explicit', kind='extension', **more):
    """A live Owner-reviewed case the demo policy would approve (the features are those of the demo extension / trial request)."""
    features = evaluate(kind)['features']
    return {'id': 'live-' + str(i), 'kind': kind, 'dataset': 'live', 'features': features, 'ownerDecision': decision, 'verdictKind': kind_of_verdict,
            'outcome': {'label': 'repaid'}, 'ownerReason': None, **more}


def sources(value, **more):
    return policy(trackRecord={'minReviewedCases': 5, 'minAgreement': '0.8', 'sources': value, **more})


# ---------------------------------------------------------------- 1. track-record sources (D7)

class TrackSourcesPolicyTests(unittest.TestCase):
    def test_the_key_defaults_to_both_validates_strictly_and_a_key_left_out_is_both(self):
        self.assertEqual(delegation.default_policy(SETTINGS)['trackRecord']['sources'], 'both')
        self.assertEqual(delegation.validate_policy({}, SETTINGS)['trackRecord']['sources'], 'both')
        self.assertEqual(delegation.validate_policy({'trackRecord': {'minReviewedCases': 3}}, SETTINGS)['trackRecord']['sources'], 'both')
        for good in ('fictional', 'live', 'both'):
            self.assertEqual(delegation.validate_policy({'trackRecord': {'sources': good}}, SETTINGS)['trackRecord']['sources'], good)
        for bad in ('Live', 'all', '', None, 1, True, ['live'], {}):
            with self.assertRaises(RecordsError, msg=repr(bad)) as raised:
                delegation.validate_policy({'trackRecord': {'sources': bad}}, SETTINGS)
            self.assertEqual((raised.exception.status, raised.exception.field), (400, 'trackRecord.sources'))
        with self.assertRaises(RecordsError):
            delegation.validate_policy({'trackRecord': {'source': 'live'}}, SETTINGS)

    def test_the_digest_of_a_both_policy_is_the_digest_it_always_had(self):
        base = delegation.validate_policy(delegation_demo.DEMO_POLICY, SETTINGS)
        old = json.loads(json.dumps(base))
        del old['trackRecord']['sources']   # a policy saved before the key existed
        self.assertEqual(delegation.policy_digest(base), delegation.policy_digest(old))
        live = delegation.validate_policy({**delegation_demo.DEMO_POLICY, 'trackRecord': {'minReviewedCases': 5, 'minAgreement': '0.8', 'sources': 'live'}}, SETTINGS)
        self.assertNotEqual(delegation.policy_digest(live), delegation.policy_digest(base))


class TrackSourcesRuleTests(unittest.TestCase):
    def test_fictional_is_exactly_the_earlier_behaviour_and_live_cases_do_not_count(self):
        cases = memory() + [live_row(i, 'decline') for i in range(10)]
        only = delegation.track_record(sources('fictional'), 'extension', cases)
        earlier = delegation.track_record(policy(), 'extension', memory())
        self.assertEqual((only['status'], only['sentence'], only['evaluation']), (earlier['status'], earlier['sentence'], earlier['evaluation']))
        self.assertEqual((only['gatedOn'], only['gate']['gatedOn']), ('fictional', 'fictional'))
        self.assertEqual(only['gate']['live']['cases'], 10)   # still shown, not counted

    def test_both_with_no_live_case_is_the_fictional_behaviour(self):
        both, fict = delegation.track_record(sources('both'), 'extension', memory()), delegation.track_record(sources('fictional'), 'extension', memory())
        self.assertEqual((both['status'], both['sentence'], both['gatedOn']), (fict['status'], fict['sentence'], 'fictional'))
        self.assertEqual(both['gate']['pooled']['cases'], both['gate']['fictional']['cases'])
        self.assertEqual(both['gate']['live'], {'dataset': 'live', 'cases': 0, 'approved': 0, 'declined': 0, 'agreement': None, 'explicit': 0, 'tacit': 0})

    def test_live_counts_explicit_and_tacit_verdicts_apart_and_ignores_the_fictional_set(self):
        rows = [live_row(1), live_row(2), live_row(3, kind_of_verdict='tacit'), live_row(4, kind_of_verdict='tacit'), live_row(5)]
        tr = delegation.track_record(sources('live'), 'extension', memory() + rows)
        g = tr['gate']
        self.assertEqual((tr['status'], tr['gatedOn'], g['live']['cases'], g['live']['explicit'], g['live']['tacit'], g['live']['agreement']), ('established', 'live', 5, 3, 2, '1'))
        self.assertEqual((g['fictional']['cases'], g['fictional']['agreement']), (6, '5/6'))   # shown, not gating
        self.assertFalse(tr['simulation'])
        self.assertNotIn('SIMULATION', tr['sentence'])
        self.assertIn('2 tacit', tr['sentence'])

    def test_live_with_too_few_cases_says_how_many_more_are_needed(self):
        tr = delegation.track_record(sources('live'), 'extension', memory() + [live_row(1), live_row(2)])
        self.assertEqual(tr['status'], 'not_established')
        self.assertEqual((tr['gate']['needed'], tr['gate']['shortBy']), (5, 3))
        self.assertIn('3 more live Owner-reviewed cases the policy would approve are needed (2 of 5)', tr['sentence'])
        none = delegation.track_record(sources('live'), 'extension', memory())
        self.assertEqual(none['status'], 'not_established')
        self.assertIn('5 more live', none['sentence'])
        self.assertIn('0 of 5', none['sentence'])

    def test_live_reaching_the_count_but_not_the_agreement_says_so(self):
        rows = [live_row(i) for i in range(4)] + [live_row(9, 'decline')]
        tr = delegation.track_record(sources('live'), 'extension', rows)
        self.assertEqual((tr['status'], tr['gate']['live']['agreement']), ('established', '0.8'))   # 4 of 5 meets 0.8 exactly
        tr = delegation.track_record(sources('live', minAgreement='0.9'), 'extension', rows)
        self.assertEqual(tr['status'], 'not_established')
        self.assertIn('below the 0.9', tr['sentence'])

    def test_both_pools_the_fictional_back_test_and_the_live_verdicts_and_shows_all_three(self):
        rows = [live_row(1), live_row(2, kind_of_verdict='tacit')]
        tr = delegation.track_record(sources('both'), 'extension', memory() + rows)
        g = tr['gate']
        self.assertEqual((tr['gatedOn'], g['fictional']['cases'], g['fictional']['approved'], g['live']['cases'], g['pooled']['cases'], g['pooled']['approved']), ('pooled', 6, 5, 2, 8, 7))
        self.assertEqual((g['pooled']['agreement'], g['live']['explicit'], g['live']['tacit']), ('0.875', 1, 1))
        self.assertEqual(tr['status'], 'established')   # 8 cases, 7/8 = 0.875 >= 0.8
        self.assertIn('pooled', tr['sentence'])
        self.assertEqual(tr['evaluation']['dataset'], 'fictional_evaluation')   # the earlier figures are unchanged beside the new ones
        self.assertEqual(tr['live']['dataset'], 'live')

    def test_live_declines_can_unestablish_a_pooled_record_and_a_tiny_live_sample_cannot_alone_establish_it(self):
        bad = [live_row(i, 'decline') for i in range(3)]
        tr = delegation.track_record(sources('both'), 'extension', memory() + bad)
        self.assertEqual((tr['status'], tr['gate']['pooled']['cases'], tr['gate']['pooled']['approved']), ('not_established', 9, 5))
        self.assertIn('below the 0.8', tr['sentence'])
        # with the fictional bootstrap switched off the live count alone must reach the Owner's own number
        self.assertEqual(delegation.track_record(sources('live'), 'extension', [live_row(1)])['status'], 'not_established')

    def test_not_required_stays_not_required_and_categories_are_counted_apart(self):
        tr = delegation.track_record(sources('live', minReviewedCases=None, minAgreement=None), 'extension', [])
        self.assertEqual(tr['status'], 'not_required')
        trial = delegation.track_record(sources('live'), 'trial_credit', [live_row(i) for i in range(5)])   # extension cases do not count for trial credit
        self.assertEqual((trial['status'], trial['gate']['live']['cases']), ('not_established', 0))

    def test_step_seven_escalates_with_the_shortfall_in_its_reason(self):
        e = evaluate(pol=sources('live'), mem=memory() + [live_row(1)])
        self.assertEqual((e['handling'], e['step']), ('owner_review', 7))
        reason = next(r for r in e['reasons'] if r.startswith('The track record'))
        self.assertIn('4 more live Owner-reviewed cases', reason)
        self.assertEqual((e['reliability']['sources'], e['reliability']['gatedOn']), ('live', 'live'))
        ok = evaluate(pol=sources('live'), mem=memory() + [live_row(i) for i in range(5)])
        self.assertEqual((ok['handling'], ok['step']), ('autonomous_approve', 10))
        self.assertEqual(ok['reliability']['gate']['live']['cases'], 5)

    def test_a_policy_dict_without_the_key_counts_both(self):
        p = policy()
        del p['trackRecord']['sources']
        self.assertEqual(delegation.track_record(p, 'extension', memory())['sources'], 'both')


class TrackSourcesServerTests(LoopCase):
    def test_the_policy_saves_reads_back_and_a_version_saved_before_the_key_reads_as_both(self):
        self.assertEqual(self.policy()['trackRecord']['sources'], 'both')
        out = self.change_policy(trackRecord={'minReviewedCases': 5, 'minAgreement': '0.8', 'sources': 'live'})
        self.assertEqual((out['version'], out['trackRecord']['sources']), (2, 'live'))
        self.assertEqual(self.policy('staff')['trackRecord']['sources'], 'live')
        status, body = self.put_policy({**delegation_demo.DEMO_POLICY, 'trackRecord': {'sources': 'nobody'}, 'expectedVersion': 2})
        self.assertEqual((status, body['field']), (400, 'trackRecord.sources'))
        self.assertEqual(self.pause()['version'], 3)   # pause keeps it
        self.assertEqual(self.policy()['trackRecord']['sources'], 'live')
        with self.app.lock, self.app.db:
            rules = delegation.validate_policy(delegation_demo.DEMO_POLICY, SETTINGS)
            del rules['trackRecord']['sources']
            self.app.db.execute('INSERT INTO delegation_policies (version, created_at, data) VALUES (?,?,?)', (4, '2026-10-24T01:00:00+00:00', json.dumps({**rules, 'createdBy': None, 'note': 'old', 'action': 'save'})))
            current = self.app.policy_current()
        self.assertEqual(current['trackRecord']['sources'], 'both')
        self.assertEqual(current['digest'], delegation.policy_digest(rules))
        self.assertEqual(self.call('/api/delegation/policy/history', None, 'owner')[1]['versions'][0]['trackRecord']['sources'], 'both')

    def test_a_live_owner_decline_enters_the_pooled_gate_through_the_real_memory(self):
        self.change_policy(mode='advisory')   # in advisory mode the in-bounds request goes to the Owner, who declines it
        out = self.resolved(**self.trial('northside', '500.00'))
        self.assertEqual(self.send('POST', '/api/decision-cases/' + out['caseId'] + '/decide', {'outcome': 'decline', 'reason': 'Not this one.', 'version': out['version']})[0], 200)
        self.change_policy()
        shown = self.assess(**self.trial('lakeside', '600.00'))['reliability']
        self.assertEqual((shown['sources'], shown['gatedOn'], shown['gate']['live']['dataset']), ('both', 'pooled', 'live'))
        self.assertEqual((shown['gate']['live']['cases'], shown['gate']['live']['approved'], shown['gate']['live']['explicit'], shown['gate']['live']['tacit']), (1, 0, 1, 0))
        self.assertEqual(shown['live']['wouldApprove'], 1)   # the earlier figures keep their shape beside the new ones
        self.assertEqual(shown['gate']['pooled']['cases'], shown['gate']['fictional']['cases'] + 1)


# ---------------------------------------------------------------- 2. tightening suggestions

TEMPLATE = {'currency': 'AUD', 'scale': 2}


def row(i, kind='trial_credit', dataset='live', decision='approve', exposure=None, days=None, observed=None, label=None, verdict='explicit', **more):
    """A reviewed case for the suggestion rules: a trial credit at `exposure` (minor units) or an extension of `days`."""
    features = dict(evaluate(kind)['features'])
    if kind == 'trial_credit':
        features['exposure'] = exposure if exposure is not None else 30000
    else:
        features['extensionDays'] = days if days is not None else 10
    out = {'id': dataset[:2] + '-' + str(i), 'kind': kind, 'dataset': dataset, 'features': features, 'ownerDecision': decision, 'outcome': {'label': label or 'repaid'},
           'observed': observed if dataset == 'live' else None, 'ownerReason': None, 'customerName': 'C'}
    if dataset == 'live':
        out['verdictKind'] = verdict
    return {**out, **more}


def lowering(found, field):
    return [s for s in found if s['kind'] == 'lower_limit' and s['field'] == field]


class TighteningSuggestionTests(unittest.TestCase):
    def test_two_owner_declines_inside_the_bound_propose_lowering_it_to_just_below_the_band(self):
        pol = policy()   # trial exposure cap AUD 600.00
        cases = [row(1, exposure=30000), row(2, exposure=52000, decision='decline'), row(3, exposure=58000, decision='decline')]
        [s] = lowering(delegation.suggestions(pol, cases, TEMPLATE), 'newCustomers.maxExposure')
        self.assertTrue(s['suggestionOnly'])
        self.assertEqual((s['current']['text'], s['suggested']['text']), ('AUD 600.00', 'AUD 519.99'))
        self.assertEqual((s['evidence']['n'], s['evidence']['ownerDeclined'], s['evidence']['ownerApproved'], s['evidence']['adverseOutcomes']), (2, 2, 0, 0))
        self.assertEqual((s['evidence']['cases'], s['evidence']['datasets'], s['evidence']['byDataset']['live']['n']), (['li-2', 'li-3'], ['live'], 2))
        self.assertEqual(s['evidence']['problemCases'][0]['value'], '52000')
        self.assertIn('This is a suggestion', s['text'])
        self.assertIn('works against growing autonomy', s['note'])
        self.assertEqual(pol['newCustomers']['maxExposure']['minorUnits'], '60000')   # nothing was applied

    def test_the_thresholds_are_named_constants(self):
        self.assertEqual((delegation.LOWER_MIN_DECLINES, delegation.LOWER_MIN_ADVERSE, delegation.ADVISORY_MIN_OVERRIDES), (2, 1, 2))

    def test_a_single_owner_decline_with_no_adverse_outcome_does_not_trigger_it(self):
        pol = policy()
        self.assertEqual(delegation.suggestions(pol, [row(1, exposure=52000, decision='decline')], TEMPLATE), [])
        self.assertEqual(delegation.suggestions(pol, [row(1, 'extension', days=20, decision='decline'), row(2, 'extension', days=10)], TEMPLATE), [])
        # a decline whose case also went badly is an adverse case, and one is enough
        [s] = lowering(delegation.suggestions(pol, [row(1, exposure=52000, decision='decline', observed='written_off')], TEMPLATE), 'newCustomers.maxExposure')
        self.assertEqual(s['evidence']['adverseOutcomes'], 1)
        # declines are counted per bound: one in each is still one each
        self.assertEqual(delegation.suggestions(pol, [row(1, exposure=52000, decision='decline'), row(2, 'extension', days=20, decision='decline')], TEMPLATE), [])
        # declines of a different kind or above the bound do not add up
        self.assertEqual(delegation.suggestions(pol, [row(1, exposure=52000, decision='decline'), row(2, exposure=70000, decision='decline')], TEMPLATE), [])

    def test_an_adverse_case_alone_sets_the_band_and_a_lone_lower_decline_does_not_widen_it(self):
        cases = [row(1, exposure=20000, decision='decline'), row(2, exposure=50000, observed='partial')]
        [s] = lowering(delegation.suggestions(policy(), cases, TEMPLATE), 'newCustomers.maxExposure')
        self.assertEqual((s['suggested']['minorUnits'], s['evidence']['cases']), ('49999', ['li-2']))
        two = [row(1, exposure=20000, decision='decline'), row(3, exposure=25000, decision='decline'), row(2, exposure=50000, observed='partial')]
        [t] = lowering(delegation.suggestions(policy(), two, TEMPLATE), 'newCustomers.maxExposure')
        self.assertEqual((t['suggested']['minorUnits'], t['evidence']['cases']), ('19999', ['li-1', 'li-3', 'li-2']))

    def test_an_adverse_observed_outcome_on_a_live_case_counts_and_a_good_or_missing_one_does_not(self):
        pol = policy()
        for observed in ('late_paid', 'partial', 'open_past_due', 'written_off'):
            found = lowering(delegation.suggestions(pol, [row(1, exposure=45000, observed=observed)], TEMPLATE), 'newCustomers.maxExposure')
            self.assertEqual([s['suggested']['minorUnits'] for s in found], ['44999'], observed)
            self.assertEqual(found[0]['evidence']['problemCases'][0]['outcome'], observed)
        for fine in ('on_time', 'open_not_due', 'unknown', None):   # unknown is neither adverse nor good, and an unobserved case is not assumed bad
            self.assertEqual(delegation.suggestions(pol, [row(1, exposure=45000, observed=fine)], TEMPLATE), [], fine)

    def test_a_live_case_is_judged_by_its_stored_observation_and_not_the_read_time_label(self):
        pol = policy()
        self.assertEqual(delegation.suggestions(pol, [row(1, exposure=45000, label='late', observed='on_time')], TEMPLATE), [])
        self.assertEqual(len(lowering(delegation.suggestions(pol, [row(1, exposure=45000, label='repaid', observed='late_paid')], TEMPLATE), 'newCustomers.maxExposure')), 1)

    def test_a_fictional_case_is_judged_by_its_stored_label(self):
        pol = policy()
        found = delegation.suggestions(pol, [row(1, 'extension', 'fictional_example', days=20, label='defaulted')], TEMPLATE)
        [s] = lowering(found, 'extensions.maxDays')
        self.assertEqual((s['current'], s['suggested'], s['evidence']['datasets'], s['evidence']['adverseOutcomes']), (30, 19, ['fictional_example'], 1))
        self.assertEqual(s['evidence']['problemCases'][0]['outcome'], 'defaulted')
        self.assertEqual(delegation.suggestions(pol, [row(1, 'extension', 'fictional_example', days=20, label='repaid')], TEMPLATE), [])
        self.assertEqual(len(lowering(delegation.suggestions(pol, [row(1, 'extension', 'fictional_example', days=20, label='late')], TEMPLATE), 'extensions.maxDays')), 1)

    def test_the_held_out_evaluation_set_is_never_read(self):
        found = delegation.suggestions(policy(), [row(1, exposure=45000, decision='decline', dataset='fictional_evaluation'), row(2, 'extension', 'fictional_evaluation', decision='decline', days=20)], TEMPLATE)
        self.assertEqual(found, [])

    def test_the_lowest_problem_case_sets_the_new_bound_and_the_band_runs_up_to_the_old_one(self):
        cases = [row(1, exposure=55000, decision='decline'), row(2, exposure=41000, decision='decline'), row(3, exposure=50000, observed='late_paid'), row(4, exposure=20000)]
        [s] = lowering(delegation.suggestions(policy(), cases, TEMPLATE), 'newCustomers.maxExposure')
        self.assertEqual(s['suggested']['minorUnits'], '40999')
        self.assertEqual((s['evidence']['n'], s['evidence']['cases']), (3, ['li-2', 'li-3', 'li-1']))   # the clean AUD 200.00 case is below the band
        self.assertEqual(s['id'], 'newCustomers.maxExposure:lower:40999')

    def test_a_problem_above_the_bound_is_not_a_reason_to_lower_it_and_the_bound_is_never_below_zero(self):
        self.assertEqual(delegation.suggestions(policy(), [row(1, exposure=70000, decision='decline'), row(2, exposure=70000, decision='decline')], TEMPLATE), [])
        [s] = lowering(delegation.suggestions(policy(), [row(1, exposure=0, decision='decline'), row(2, exposure=0, decision='decline')], TEMPLATE), 'newCustomers.maxExposure')
        self.assertEqual(s['suggested']['minorUnits'], '0')
        [d] = lowering(delegation.suggestions(policy(), [row(1, 'extension', days=0, decision='decline'), row(2, 'extension', days=0, decision='decline')], TEMPLATE), 'extensions.maxDays')
        self.assertEqual(d['suggested'], 0)

    def test_restrictions_are_never_touched_and_every_suggestion_is_suggestion_only(self):
        pol = policy(restrictions={'holdCustomers': ['c9'], 'unusualSizeMultiple': '3'})
        cases = [row(i, exposure=40000 + i, decision='decline') for i in range(4)] + [row(9, 'extension', days=25, decision='decline'), row(10, 'extension', days=26, decision='decline')]
        found = delegation.suggestions(pol, cases, TEMPLATE, [{'caseId': 'a'}, {'caseId': 'b'}])
        self.assertEqual({s['field'] for s in found}, {'newCustomers.maxExposure', 'extensions.maxDays', 'mode'})
        for s in found:
            self.assertTrue(s['suggestionOnly'])
            self.assertNotIn('restrictions', s['field'])
            self.assertNotIn('holdCustomers', json.dumps(s))
        self.assertEqual(pol['restrictions']['holdCustomers'], ['c9'])

    def test_evidence_keeps_live_and_fictional_counts_apart(self):
        cases = [row(1, exposure=45000, decision='decline'), row(2, exposure=47000, dataset='fictional_example', decision='decline', label='defaulted')]
        [s] = lowering(delegation.suggestions(policy(), cases, TEMPLATE), 'newCustomers.maxExposure')
        self.assertEqual(s['evidence']['datasets'], ['fictional_example', 'live'])
        self.assertEqual({k: v['n'] for k, v in s['evidence']['byDataset'].items()}, {'live': 1, 'fictional_example': 1})
        self.assertEqual(s['evidence']['byDataset']['fictional_example']['adverseOutcomes'], 1)
        self.assertEqual(s['evidence']['byDataset']['live']['adverseOutcomes'], 0)


class RaiseAndTacitTests(unittest.TestCase):
    def band(self, verdicts, **more):
        """Trial credits above the AUD 600.00 cap, all approved and repaid, with these verdict kinds."""
        return [row(i, exposure=65000 + 1000 * i, verdict=v, **more) for i, v in enumerate(verdicts)]

    def raise_of(self, cases):
        return [s for s in delegation.suggestions(policy(), cases, TEMPLATE) if s['kind'] == 'raise_limit']

    def test_explicit_agreements_raise_the_bound_and_the_evidence_counts_the_tacit_ones(self):
        [s] = self.raise_of(self.band(['explicit', 'explicit', 'tacit']))
        self.assertEqual((s['evidence']['tacitAgreements'], s['evidence']['explicitAgreements'], s['evidence']['n']), (1, 2, 3))
        [none] = self.raise_of(self.band(['explicit', 'explicit', 'explicit']))
        self.assertEqual((none['evidence']['tacitAgreements'], none['evidence']['explicitAgreements']), (0, 3))

    def test_one_explicit_approval_is_enough_and_tacit_verdicts_alone_never_raise_a_bound(self):
        [s] = self.raise_of(self.band(['tacit', 'tacit', 'explicit']))
        self.assertEqual(s['evidence']['tacitAgreements'], 2)
        self.assertEqual(self.raise_of(self.band(['tacit', 'tacit', 'tacit', 'tacit'])), [])
        self.assertEqual(self.raise_of(self.band(['tacit'] * 3 + ['explicit']))[0]['evidence']['explicitAgreements'], 1)

    def test_a_live_case_with_an_adverse_observation_stops_the_band(self):
        cases = self.band(['explicit'] * 4)
        cases[1]['observed'] = 'late_paid'
        self.assertEqual(self.raise_of(cases), [])   # the read-time label still says repaid, the stored observation says it was paid late

    def test_fictional_bands_are_unchanged_and_report_no_tacit(self):
        found = delegation.suggestions(policy(), memory(), TEMPLATE)
        [s] = [x for x in found if x['kind'] == 'raise_limit']
        self.assertEqual((s['field'], s['evidence']['n'], s['evidence']['tacitAgreements'], s['evidence']['datasets']), ('newCustomers.maxExposure', 4, 0, ['fictional_example']))
        self.assertEqual(lowering(found, 'newCustomers.maxExposure'), [])   # the demonstration's declines are far above the bound


class OverrideSuggestionTests(unittest.TestCase):
    def test_two_overrides_propose_advisory_mode_with_the_list_as_evidence(self):
        ov = [{'caseId': 'c1', 'kind': 'extension', 'policyVersion': 1}, {'caseId': 'c2', 'kind': 'trial_credit', 'policyVersion': 1}]
        found = [s for s in delegation.suggestions(policy(), [], TEMPLATE, ov) if s['field'] == 'mode']
        [s] = found
        self.assertEqual((s['kind'], s['current'], s['suggested'], s['suggestionOnly']), ('switch_mode', 'delegated', 'advisory', True))
        self.assertEqual((s['evidence']['n'], s['evidence']['cases'], s['evidence']['overrides'], s['evidence']['datasets']), (2, ['c1', 'c2'], ov, ['live']))
        self.assertEqual(delegation.suggestions(policy(), [], TEMPLATE, ov[:1]), [])
        self.assertEqual(delegation.suggestions(policy(mode='advisory'), [], TEMPLATE, ov), [])   # already advisory

    def test_a_policy_that_is_not_delegated_gets_no_mode_suggestion_and_nothing_is_applied(self):
        pol = policy()
        delegation.suggestions(pol, [], TEMPLATE, [{'caseId': 'a'}, {'caseId': 'b'}, {'caseId': 'c'}])
        self.assertEqual(pol['mode'], 'delegated')


class SuggestionRouteTests(LoopCase):
    def suggestions(self):
        status, body, _ = self.call('/api/delegation/suggestions', None, 'owner')
        self.assertEqual(status, 200, body)
        return body['suggestions']

    def override(self, case_id):
        status, body = self.feedback(case_id, {'verdict': 'disagree', 'reason': 'Fictional: not this one.', 'override': True})
        self.assertEqual(status, 200, body)

    def test_two_overrides_under_the_current_version_propose_advisory_one_does_not(self):
        a = self.approved_extension('bayview', 'DEMO-301', '2026-11-10')
        self.override(a['caseId'])
        self.assertEqual([s for s in self.suggestions() if s['field'] == 'mode'], [])
        b = self.resolved(**self.trial('northside', '800.00'))
        self.override(b['caseId'])
        [s] = [s for s in self.suggestions() if s['field'] == 'mode']
        self.assertEqual(sorted(s['evidence']['cases']), sorted([a['caseId'], b['caseId']]))
        self.assertEqual({o['policyVersion'] for o in s['evidence']['overrides']}, {1})
        self.assertEqual(self.policy()['mode'], 'delegated')   # a suggestion applies nothing

    def test_overrides_made_under_an_earlier_version_do_not_count_toward_the_current_one(self):
        a = self.approved_extension('bayview', 'DEMO-301', '2026-11-10')
        b = self.resolved(**self.trial('northside', '800.00'))
        self.override(a['caseId'])
        self.override(b['caseId'])
        self.assertEqual(len([s for s in self.suggestions() if s['field'] == 'mode']), 1)
        self.change_policy()   # version 2: the Owner reviewed the policy; the earlier overrides were of version 1
        self.assertEqual([s for s in self.suggestions() if s['field'] == 'mode'], [])

    def test_memory_rows_carry_the_stored_observation_of_a_live_case_and_the_tightening_reads_it(self):
        out = self.resolved(**self.trial('northside', '500.00'))
        self.feedback(out['caseId'], {'verdict': 'agree', 'reason': 'Fine.'})
        with self.app.lock, self.app.db:
            self.app.dg_patch(out['caseId'], 'outcomeObserved', {'outcome': 'late_paid', 'asOf': '2026-10-24', 'observedAt': '2026-10-24T00:00:00+00:00', 'policyVersion': 1, 'basis': {}})
            row_ = next(m for m in self.app.dg_memory(self.app.evidence(), self.app.fixture()) if m['id'] == out['caseId'])
        self.assertEqual(row_['observed'], 'late_paid')
        [s] = [s for s in self.suggestions() if s['kind'] == 'lower_limit']
        self.assertEqual((s['field'], s['evidence']['cases'], s['evidence']['byDataset']['live']['adverseOutcomes']), ('newCustomers.maxExposure', [out['caseId']], 1))

    def test_the_route_is_for_the_owner_only(self):
        self.assertEqual(self.call('/api/delegation/suggestions', None, 'staff')[0], 403)


# ---------------------------------------------------------------- 3. the impact endpoint

import impact
from datetime import datetime, timedelta, timezone


class Timeline:
    """Synthetic live cases and their events for the pure impact rules: a case is built from (id, kind, created, [(kind, seconds after created, actor, data)], **case fields)."""
    T0 = datetime(2026, 10, 20, 9, 0, 0)

    def __init__(self):
        self.cases, self.events, self.seq = [], [], 0

    def add(self, cid, kind, steps, day=0, **case):
        created = self.T0 + timedelta(days=day)
        self.cases.append({'id': cid, 'kind': kind, 'dataset': 'live', 'createdAt': created.isoformat() + '+00:00', 'status': 'awaiting_owner', 'handling': 'owner_review',
                           'policy': {'version': 1}, 'decision': None, 'feedback': [], **case})
        for what, after, actor, *data in [('created', 0, 'agent')] + list(steps):
            self.seq += 1
            self.events.append({'seq': self.seq, 'case_id': cid, 'kind': what, 'at': (created + timedelta(seconds=after)).isoformat() + '+00:00', 'actor': actor,
                                'policy_version': 1, 'data': data[0] if data else {}})
        return self

    def compute(self, **window):
        return impact.compute(self.cases, self.events, window)


def agent_case(tl, cid, kind='extension', after=10, verdict=None, observed=None, overridden=False, day=0, version=1):
    feedback = [{'verdict': verdict}] if verdict else []
    decision = {'by': 'agent', 'outcome': 'approve', 'overridden': overridden}
    return tl.add(cid, kind, [('evaluated', 1, 'system'), ('decided', after, 'agent')], day=day, status='decided', handling='autonomous_approve', decision=decision, feedback=feedback,
                  policy={'version': version}, **({'outcomeObserved': {'outcome': observed}} if observed else {}))


def walk(node, path=''):
    """Every dict that carries a `value`, with its path; a number anywhere else (outside `window`) is a failure of the labelling rule."""
    if isinstance(node, dict):
        if 'value' in node:
            yield path, node
        else:
            for k, v in node.items():
                if k != 'window':
                    for hit in walk(v, path + '/' + str(k)):
                        yield hit
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        raise AssertionError('a bare number at ' + path + ': ' + repr(node))


class ImpactRuleTests(unittest.TestCase):
    def sample(self):
        tl = Timeline()
        agent_case(tl, 'a1', 'extension', 10, verdict='agree', observed='on_time')
        agent_case(tl, 'a2', 'trial_credit', 30, verdict='tacit_agree', observed='open_not_due')
        agent_case(tl, 'a3', 'extension', 20, verdict='disagree', overridden=True, observed=None)
        agent_case(tl, 'a4', 'trial_credit', 40)   # approved, never reviewed, not yet observed
        tl.add('o1', 'trial_credit', [('evaluated', 1, 'system'), ('escalated', 2, 'system'), ('viewed', 100, 'owner'), ('decided', 160, 'owner', {'by': 'owner', 'outcome': 'decline'})],
               status='decided', handling='owner_review', decision={'by': 'owner', 'outcome': 'decline'})
        tl.add('o2', 'extension', [('evaluated', 1, 'system'), ('escalated', 2, 'system')], status='awaiting_owner', handling='owner_review')
        tl.add('h1', 'trial_credit', [('held', 2, 'system')], status='on_hold', handling='policy_hold')
        tl.add('g1', 'trial_credit', [('evaluated', 1, 'system'), ('evidence_requested', 2, 'system'), ('evidence_submitted', 302, 'staff'), ('evaluated', 303, 'system'), ('evidence_requested', 304, 'system')],
               status='gathering_evidence', handling='request_evidence')
        return tl

    def test_every_number_carries_source_and_dataset(self):
        hits = list(walk(self.sample().compute()))
        self.assertGreater(len(hits), 60)
        for path, m in hits:
            self.assertEqual(set(m), {'value', 'numerator', 'denominator', 'source', 'dataset', 'note'}, path)
            self.assertIn(m['source'], ('measured', 'derived', 'assumption'), path)
            self.assertEqual(m['dataset'], 'live', path)

    def test_coverage_escalation_and_overrides(self):
        r = self.sample().compute()
        self.assertEqual((r['cases']['value'], r['autonomousCoverage']['numerator'], r['autonomousCoverage']['denominator'], r['autonomousCoverage']['value']), (8, 4, 7, 0.5714))   # g1 gathers evidence: left out
        self.assertEqual((r['autonomousCoverage']['source'], r['escalationRate']['source']), ('derived', 'derived'))
        self.assertEqual((r['escalationRate']['numerator'], r['escalationRate']['denominator'], r['escalationRate']['value']), (3, 8, 0.375))   # o1, o2 and the hold
        self.assertEqual((r['overrides']['count']['value'], r['overrides']['rate']['numerator'], r['overrides']['rate']['denominator'], r['overrides']['rate']['value']), (1, 1, 4, 0.25))
        self.assertEqual((r['disagreements']['count']['value'], r['disagreements']['count']['denominator']), (1, 3))

    def test_live_agreement_counts_explicit_and_tacit_apart(self):
        a = self.sample().compute()['liveAgreement']
        self.assertEqual((a['explicit']['value'], a['tacit']['value'], a['explicit']['denominator']), (2, 1, 3))
        self.assertEqual((a['agreementRate']['numerator'], a['agreementRate']['denominator'], a['agreementRate']['value']), (2, 3, 0.6667))

    def test_outcomes_use_the_latest_stored_observation_and_pending_is_approved_cases_with_none(self):
        o = self.sample().compute()['outcomes']
        self.assertEqual({k: v['value'] for k, v in o['byLabel'].items() if v['value']}, {'on_time': 1, 'open_not_due': 1})
        self.assertEqual(set(o['byLabel']), set(impact.OBSERVED))
        self.assertEqual((o['pending']['value'], o['pending']['denominator']), (1, 3))   # a4; the overridden a3 and the declined o1 are never observed
        self.assertEqual(o['neverObserved']['value'], 2)
        tl = self.sample()
        tl.cases[0]['outcomeObserved'] = {'outcome': 'late_paid'}   # a later observation replaces the earlier one in the count
        self.assertEqual(tl.compute()['outcomes']['byLabel']['late_paid']['value'], 1)
        self.assertEqual(tl.compute()['outcomes']['byLabel']['on_time']['value'], 0)

    def test_evidence_turnaround_pairs_each_request_with_the_next_answer(self):
        e = self.sample().compute()['evidenceRequests']
        self.assertEqual((e['count']['value'], e['answered']['value'], e['pending']['value']), (2, 1, 1))
        self.assertEqual((e['medianTurnaroundSeconds']['value'], e['medianTurnaroundSeconds']['numerator']), (300, 1))

    def test_time_to_decision_is_created_to_decided_per_kind(self):
        t = self.sample().compute()['timeToDecisionSeconds']
        self.assertEqual((t['median']['value'], t['median']['numerator'], t['p90']['value']), (30, 5, 160))   # 10, 20, 30, 40 and the Owner's 160
        self.assertEqual((t['byKind']['extension']['median']['value'], t['byKind']['extension']['cases']['value']), (15, 2))
        self.assertEqual((t['byKind']['trial_credit']['median']['value'], t['byKind']['trial_credit']['p90']['value']), (40, 160))

    def test_owner_intervention_is_first_view_to_the_action_and_unknown_without_a_view(self):
        i = self.sample().compute()['ownerInterventionSeconds']
        self.assertEqual((i['median']['value'], i['median']['source'], i['cases']['value'], i['withoutView']['value']), (60, 'measured', 1, 0))
        self.assertIn('viewed', i['median']['note'])
        tl = Timeline().add('x', 'trial_credit', [('feedback', 50, 'owner', {'verdict': 'agree'})], status='decided', decision={'by': 'agent'})
        i = tl.compute()['ownerInterventionSeconds']
        self.assertEqual((i['median']['value'], i['cases']['value'], i['withoutView']['value']), (None, 0, 1))   # unknown, never zero
        late = Timeline().add('y', 'trial_credit', [('viewed', 10, 'owner'), ('feedback', 95, 'owner', {}), ('override', 96, 'owner', {})], status='decided', decision={'by': 'agent'})
        self.assertEqual(late.compute()['ownerInterventionSeconds']['median']['value'], 85)

    def test_an_empty_window_has_no_medians_and_no_rates_rather_than_zeros(self):
        r = Timeline().compute()
        for m in (r['autonomousCoverage'], r['escalationRate'], r['overrides']['rate'], r['liveAgreement']['agreementRate'], r['timeToDecisionSeconds']['median'], r['timeToDecisionSeconds']['p90'],
                  r['evidenceRequests']['medianTurnaroundSeconds'], r['ownerInterventionSeconds']['median']):
            self.assertIsNone(m['value'])
        self.assertEqual(r['cases']['value'], 0)

    def test_the_window_filters_by_day_created_and_by_policy_version(self):
        tl = Timeline()
        agent_case(tl, 'old', day=0, version=1)
        agent_case(tl, 'mid', day=3, version=1)
        agent_case(tl, 'new', day=6, version=2)
        self.assertEqual(tl.compute()['cases']['value'], 3)
        self.assertEqual(tl.compute(**{'from': '2026-10-23'})['cases']['value'], 2)
        self.assertEqual(tl.compute(**{'from': '2026-10-21', 'to': '2026-10-23'})['cases']['value'], 1)
        self.assertEqual(tl.compute(policyVersion=2)['cases']['value'], 1)
        self.assertEqual(tl.compute(policyVersion=9)['cases']['value'], 0)
        self.assertEqual(tl.compute(**{'to': '2026-10-20'})['window'], {'from': None, 'to': '2026-10-20', 'policyVersion': None, 'note': tl.compute()['window']['note']})

    def test_per_policy_version_groups_the_same_counts(self):
        tl = Timeline()
        agent_case(tl, 'a', day=0, version=1, verdict='agree')
        agent_case(tl, 'b', day=1, version=2, verdict='disagree', overridden=True)
        agent_case(tl, 'c', day=2, version=2)
        per = tl.compute()['perPolicyVersion']
        self.assertEqual(sorted(per), ['1', '2'])
        self.assertEqual((per['1']['cases']['value'], per['1']['overrides']['count']['value'], per['1']['liveAgreement']['agreementRate']['value']), (1, 0, 1.0))
        self.assertEqual((per['2']['cases']['value'], per['2']['overrides']['count']['value'], per['2']['overrides']['rate']['value'], per['2']['disagreements']['count']['value']), (2, 1, 0.5, 1))
        self.assertEqual(sum(v['cases']['value'] for v in per.values()), tl.compute()['cases']['value'])

    def test_time_saved_is_an_explicit_assumption_placeholder(self):
        t = self.sample().compute()['timeSaved']
        self.assertEqual(t, {'value': None, 'numerator': None, 'denominator': None, 'source': 'assumption', 'dataset': 'live', 'note': 'manual baseline not measured; set from PoV interviews'})

    def test_fictional_cases_are_never_read(self):
        tl = self.sample()
        tl.cases.append({**tl.cases[0], 'id': 'fx', 'dataset': 'fictional_example'})
        self.assertEqual(tl.compute()['cases']['value'], 8)

    def test_median_and_percentile_rules(self):
        self.assertEqual([impact.median(x) for x in ([], [5], [1, 2], [1, 2, 4], [1, 2, 3, 4])], [None, 5, 1.5, 2, 2.5])
        self.assertEqual([impact.percentile(list(range(1, 11)), p) for p in (50, 90, 100)], [5, 9, 10])
        self.assertIsNone(impact.percentile([], 90))


class ImpactRouteTests(LoopCase):
    def impact(self, query='', role='owner'):
        return self.call('/api/delegation/impact' + query, None, role)

    def populate(self):
        """Every handling: two agent approvals (one agreed, one overridden), an escalation the Owner viewed and declined, and one gathering evidence."""
        self.a = self.approved_extension()
        self.b = self.resolved(**self.trial('northside', '800.00'))
        self.c = self.resolved(**self.trial('harbourline', '5000.00'))
        self.d = self.resolved(**self.trial('lakeside', '600.00'))
        self.agree(self.b['caseId'], 'agree')
        self.agree(self.a['caseId'], 'disagree', override=True)
        self.assertEqual(self.send('POST', '/api/decision-cases/' + self.c['caseId'] + '/viewed', {})[0], 200)
        self.assertEqual(self.send('POST', '/api/decision-cases/' + self.c['caseId'] + '/decide', {'outcome': 'decline', 'reason': 'Too large.', 'version': self.c['version']})[0], 200)
        self.assertEqual(self.send('POST', '/api/delegation/observe-outcomes', {})[0], 200)

    def test_only_the_owner_person_reads_it(self):
        self.assertEqual(self.impact(role='staff')[0], 403)
        self.assertEqual(self.impact()[0], 200)
        service = self.call('/api/delegation/impact', None, None, None, {'Cookie': self.service_cookie('owner'), 'X-Nucleon-Role': 'owner'})
        self.assertEqual((service[0], service[1]['error']), (403, 'PERSON_REQUIRED'))   # the Owner as a person; a service session reads no impact

    def test_an_empty_database_reports_unknowns_not_zeros(self):
        status, body, _ = self.impact()
        self.assertEqual(status, 200, body)
        self.assertEqual((body['dataset'], body['cases']['value'], body['autonomousCoverage']['value'], body['timeToDecisionSeconds']['median']['value']), ('live', 0, None, None))
        self.assertEqual(body['perPolicyVersion'], {})

    def test_the_totals_reconcile_with_the_stats_for_the_same_window(self):
        self.populate()
        status, body, _ = self.impact()
        self.assertEqual(status, 200, body)
        stats = self.call('/api/delegation/stats', None, 'owner')[1]
        self.assertEqual({k: v['value'] for k, v in body['counts'].items()}, stats['counts'])
        self.assertEqual(body['cases']['value'], stats['denominator'])
        self.assertEqual({v['denominator'] for v in body['counts'].values()}, {stats['denominator']})
        self.assertEqual(body['autonomousCoverage']['numerator'], stats['counts']['autonomous'] + stats['counts']['autonomousDeclined'] + stats['counts']['overrides'])   # agent-decided, overridden or not
        self.assertEqual(body['overrides']['count']['value'], stats['counts']['overrides'])
        decided_or_escalated = stats['denominator'] - stats['counts']['gatheringEvidence'] - stats['counts']['closed']
        self.assertEqual(body['autonomousCoverage']['denominator'], decided_or_escalated)
        self.assertEqual(body['escalationRate']['denominator'], stats['denominator'])
        # the same window spelled out gives the same numbers
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')   # the report's window is in UTC days
        again = self.impact('?from=2000-01-01&to=2100-01-01&policyVersion=1')[1]
        self.assertEqual(again['counts'], body['counts'])
        self.assertEqual(again['window'], {'from': '2000-01-01', 'to': '2100-01-01', 'policyVersion': 1, 'note': body['window']['note']})
        self.assertEqual(self.impact('?from=' + today + '&to=' + today)[1]['counts'], body['counts'])

    def test_the_populated_report_has_every_metric_labelled_and_the_expected_counts(self):
        self.populate()
        body = self.impact()[1]
        self.assertEqual(len(list(walk(body))) > 50, True)
        for path, m in walk(body):
            self.assertIn(m['source'], ('measured', 'derived', 'assumption'), path)
            self.assertEqual(m['dataset'], 'live', path)
        self.assertEqual((body['autonomousCoverage']['numerator'], body['autonomousCoverage']['denominator']), (2, 3))
        self.assertEqual((body['escalationRate']['numerator'], body['escalationRate']['denominator']), (1, 4))   # only harbourline: the gathering-evidence case is not an escalation, and the overridden approval was handled autonomously
        self.assertEqual((body['overrides']['count']['value'], body['disagreements']['count']['value']), (1, 1))
        self.assertEqual((body['liveAgreement']['explicit']['value'], body['liveAgreement']['tacit']['value'], body['liveAgreement']['agreementRate']['value']), (2, 0, 0.5))
        self.assertEqual(body['outcomes']['byLabel']['unknown']['value'], 1)   # the Northside trial has no invoice yet; the overridden extension and the declined case are never observed
        self.assertEqual(body['outcomes']['pending']['value'], 0)
        self.assertEqual(body['evidenceRequests']['count']['value'], 1)
        self.assertIsNone(body['evidenceRequests']['medianTurnaroundSeconds']['value'])   # not answered yet: unknown, not zero
        self.assertEqual(body['ownerInterventionSeconds']['cases']['value'], 1)
        self.assertGreaterEqual(body['ownerInterventionSeconds']['median']['value'], 0)
        self.assertEqual(body['timeToDecisionSeconds']['median']['numerator'], 3)
        self.assertEqual(body['perPolicyVersion']['1']['cases']['value'], 4)
        self.assertEqual(body['timeSaved']['source'], 'assumption')

    def test_a_staff_evidence_answer_gives_a_turnaround(self):
        out = self.resolved(**self.trial('lakeside', '600.00'))
        self.assertEqual(self.submit(out['actionId'], LAKESIDE_ITEMS)[0], 200)
        e = self.impact()[1]['evidenceRequests']
        self.assertEqual((e['count']['value'], e['answered']['value'], e['pending']['value']), (1, 1, 0))
        self.assertGreaterEqual(e['medianTurnaroundSeconds']['value'], 0)

    def test_the_window_uses_the_day_a_case_was_created(self):
        self.populate()
        with self.app.lock, self.app.db:
            self.app.db.execute("UPDATE decision_cases SET created_at='2026-09-01T00:00:00+00:00' WHERE id=?", (self.a['caseId'],))
        self.assertEqual(self.impact()[1]['cases']['value'], 4)
        self.assertEqual(self.impact('?from=2026-10-01')[1]['cases']['value'], 3)
        self.assertEqual(self.impact('?to=2026-09-30')[1]['cases']['value'], 1)

    def test_bad_arguments_are_400(self):
        for query in ('?from=yesterday', '?to=2026-13-40', '?from=2026-10-02&to=2026-10-01', '?policyVersion=x', '?policyVersion=-1', '?from=2026-1-1'):
            status, body, _ = self.impact(query)
            self.assertEqual((status, body['error']), (400, 'INVALID_INPUT'), query)

    def test_reading_it_writes_nothing(self):
        self.populate()
        before = (self.total_events(), self.row('SELECT COUNT(*) FROM decision_cases')[0][0])
        self.impact()
        self.assertEqual((self.total_events(), self.row('SELECT COUNT(*) FROM decision_cases')[0][0]), before)


# ---------------------------------------------------------------- 4. structured hints and the compact model-facing result

class HintTests(LoopCase):
    def fails(self, name='assessDecision', **args):
        body = self.tool(name, **args)
        self.assertFalse(body['ok'], body)
        return body

    def test_a_message_that_could_be_either_kind_asks_which(self):
        for name, more in (('assessDecision', {}), ('resolveDecision', {'recommendation': 'approve', 'reasoning': 'x'})):
            body = self.fails(name, customerId=self.cust['bayview'], **more)
            self.assertEqual((body['error'], body['hint']['ask'], body['hint']['options']), ('INVALID_ARGUMENT', 'kind', ['trial_credit', 'extension']), name)
            self.assertEqual(body['message'], 'Missing argument(s): kind.')   # the existing code and message are unchanged
            self.assertLessEqual(len(body['hint']['question']), 120)
        body = self.fails(kind='loan', customerId=self.cust['bayview'])
        self.assertEqual((body['hint']['ask'], body['message']), ('kind', "kind is 'extension' or 'trial_credit'."))

    def test_an_extension_without_an_invoice_asks_which_one_with_the_open_references(self):
        body = self.fails(kind='extension', customerId=self.cust['riverside'], days=7)
        self.assertEqual((body['error'], body['hint']['ask'], body['hint']['options']), ('INVALID_ARGUMENT', 'invoice', ['DEMO-504', 'DEMO-505']))
        self.assertIn('Riverside Foods', body['hint']['question'])
        self.assertEqual(body['message'], 'Give exactly one of invoiceId and invoiceReference.')
        one = self.fails(kind='extension', customerId=self.cust['bayview'], days=7)
        self.assertEqual(one['hint']['options'], ['DEMO-301'])   # paid invoices are not offered
        both = self.fails(kind='extension', customerId=self.cust['bayview'], days=7, invoiceId='invoice_demo_019', invoiceReference='DEMO-301')
        self.assertEqual(both['hint']['ask'], 'invoice')

    def test_an_invoice_that_is_not_the_customers_asks_again(self):
        body = self.fails(kind='extension', customerId=self.cust['bayview'], invoiceReference='NOPE-1', days=7)
        self.assertEqual((body['error'], body['hint']['ask'], body['hint']['options']), ('NOT_FOUND', 'invoice', ['DEMO-301']))

    def test_an_extension_without_days_or_a_date_asks_for_the_due_date(self):
        body = self.fails(kind='extension', customerId=self.cust['bayview'], invoiceReference='DEMO-301')
        self.assertEqual((body['error'], body['hint']['ask']), ('INVALID_ARGUMENT', 'dueDate'))
        self.assertNotIn('options', body['hint'])
        self.assertEqual(self.fails(kind='extension', customerId=self.cust['bayview'], invoiceReference='DEMO-301', days=0)['hint']['ask'], 'dueDate')
        self.assertEqual(self.fails(kind='extension', customerId=self.cust['bayview'], invoiceReference='DEMO-301', requestedDueDate='next week')['hint']['ask'], 'dueDate')

    def test_an_unknown_customer_asks_which_with_the_matches_if_any(self):
        body = self.fails(kind='trial_credit', customerId='Zzyzx Traders', orderAmount='500.00', termsDays=14)
        self.assertEqual((body['error'], body['hint']['ask']), ('INVALID_ARGUMENT', 'customer'))
        self.assertNotIn('options', body['hint'])
        many = self.fails(kind='trial_credit', customerId='fictional', orderAmount='500.00', termsDays=14)
        self.assertEqual(many['hint']['ask'], 'customer')
        self.assertIn('Bayview Gelato Co (fictional) (C-0001)', many['hint']['options'])
        self.assertLessEqual(len(many['hint']['options']), 5)
        self.assertEqual(self.fails(kind='trial_credit', orderAmount='500.00', termsDays=14)['hint']['ask'], 'customer')   # none given at all
        status = self.fails('decisionStatus', customerId='Zzyzx Traders')
        self.assertEqual(status['hint']['ask'], 'customer')

    def test_a_trial_credit_without_an_amount_or_terms_asks_for_it(self):
        both = self.fails(kind='trial_credit', customerId=self.cust['northside'])
        self.assertEqual((both['hint']['ask'], both['hint']['alsoMissing']), ('amount', ['terms']))
        amount = self.fails(kind='trial_credit', customerId=self.cust['northside'], termsDays=14)
        self.assertEqual((amount['hint']['ask'], 'alsoMissing' in amount['hint']), ('amount', False))
        terms = self.fails(kind='trial_credit', customerId=self.cust['northside'], orderAmount='500.00')
        self.assertEqual(terms['hint']['ask'], 'terms')
        for bad in ('abc', '-5.00', '0.00'):
            self.assertEqual(self.fails(kind='trial_credit', customerId=self.cust['northside'], orderAmount=bad, termsDays=14)['hint']['ask'], 'amount', bad)
        for bad in ('14', 0, 400):
            self.assertEqual(self.fails(kind='trial_credit', customerId=self.cust['northside'], orderAmount='500.00', termsDays=bad)['hint']['ask'], 'terms', bad)

    def test_mixed_up_arguments_ask_for_the_kind(self):
        a = self.fails(kind='extension', customerId=self.cust['bayview'], invoiceReference='DEMO-301', days=7, orderAmount='500.00')
        b = self.fails(kind='trial_credit', customerId=self.cust['northside'], orderAmount='500.00', termsDays=14, invoiceReference='DEMO-301')
        for body in (a, b):
            self.assertEqual((body['hint']['ask'], body['hint']['options']), ('kind', ['trial_credit', 'extension']))

    def test_errors_that_need_no_answer_from_staff_carry_no_hint(self):
        # a recommendation the model got wrong is the model's to fix, a role that may not call is not a question for Staff
        body = self.fails('resolveDecision', kind='trial_credit', customerId=self.cust['northside'], orderAmount='500.00', termsDays=14, recommendation='maybe', reasoning='x')
        self.assertEqual(body['error'], 'INVALID_ARGUMENT')
        self.assertNotIn('hint', body)
        status, owner, _ = self.call('/api/tools/assessDecision', {'args': {'kind': 'trial_credit', 'customerId': self.cust['northside'], 'orderAmount': '500.00', 'termsDays': 14}}, 'owner', 'k-owner')
        self.assertNotIn('hint', owner)

    def test_every_hint_is_small_and_well_formed(self):
        bodies = [self.fails(customerId=self.cust['bayview']), self.fails(kind='extension', customerId=self.cust['riverside'], days=7), self.fails(kind='extension', customerId=self.cust['bayview'], invoiceReference='DEMO-301'),
                  self.fails(kind='trial_credit', customerId='fictional', orderAmount='500.00', termsDays=14), self.fails(kind='trial_credit', customerId=self.cust['northside']),
                  self.fails(kind='trial_credit', customerId=self.cust['northside'], orderAmount='500.00')]
        self.assertEqual({b['hint']['ask'] for b in bodies}, {'kind', 'invoice', 'dueDate', 'customer', 'amount', 'terms'})
        for b in bodies:
            h = b['hint']
            self.assertTrue(set(h) <= {'ask', 'question', 'options', 'alsoMissing'}, h)
            self.assertTrue(h['question'].endswith('?') and len(h['question']) <= 120, h)
            self.assertTrue(all(isinstance(o, str) for o in h.get('options', [])))
        self.assertEqual(self.total_events(), 0)   # a refused call writes nothing


class ForModelTests(LoopCase):
    def check(self, out):
        fm = out['forModel']
        self.assertEqual(set(fm), {'status', 'handling', 'statusText', 'why', 'nextStep', 'keyFacts'})
        self.assertLessEqual(len(json.dumps(fm, ensure_ascii=False)), delegation.FOR_MODEL_LIMIT)
        self.assertLessEqual(len(fm['keyFacts']), 8)
        self.assertTrue(all(isinstance(v, str) and len(v) <= 60 for v in fm['keyFacts'].values()), fm['keyFacts'])
        self.assertEqual((fm['status'], fm['handling']), (out['status'], out['handling']))
        self.assertTrue(fm['nextStep'])
        for key in ('statusText', 'keyFacts', 'warnings', 'reasons', 'evidence', 'risk', 'reliability', 'comparables', 'authority', 'recommendation', 'communication', 'customer'):
            self.assertIn(key, out, key)   # nothing was removed from the full result: the card reads it
        return fm

    def test_assess_resolve_and_status_each_carry_a_compact_model_view_beside_the_full_result(self):
        assessed = self.assess(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        fm = self.check(assessed)
        self.assertEqual((fm['status'], fm['handling']), ('assessed', 'autonomous_approve'))
        self.assertIn('preview', fm['nextStep'])
        self.assertEqual(fm['keyFacts']['invoice'], 'DEMO-301')
        approved = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        fm = self.check(approved)
        self.assertEqual((fm['status'], fm['handling'], approved['caseId'] in fm['keyFacts'].values()), ('decided', 'autonomous_approve', True))
        self.assertIn('Approved within', fm['statusText'])
        self.assertIn('Nucleon sent nothing', fm['nextStep'])
        self.assertEqual(self.check(self.tool('decisionStatus', caseId=approved['caseId'])['result'])['status'], 'decided')

    def test_every_handling_stays_inside_the_size_bound(self):
        seen = set()
        for result in (self.resolved(**self.trial('lakeside', '600.00')),                  # gathering evidence
                       self.resolved(**self.trial('harbourline', '5000.00')),                 # awaiting the Owner
                       self.resolved(**self.trial('northside', '800.00')),                    # approved
                       self.resolved(**self.extension('cityside', 'DEMO-410', days=14))):    # awaiting the Owner (an extension)
            fm = self.check(result)
            seen.add(fm['status'])
        self.assertEqual(seen, {'gathering_evidence', 'awaiting_owner', 'decided'})
        waiting = self.resolved(**self.trial('lakeside', '600.00'))
        fm = self.check(waiting)
        self.assertIn('#/actions/', fm['nextStep'])
        self.assertIn('Nothing is approved', fm['nextStep'])
        escalated = self.resolved(**self.trial('harbourline', '5000.00'))
        self.assertIn('Do not say it is approved', self.check(escalated)['nextStep'])
        self.assertTrue(self.check(escalated)['why'])

    def test_a_replay_an_already_handled_assessment_and_an_override_carry_it_too(self):
        out = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        again = self.resolved(key='another', **self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        self.assertTrue(again['replayed'])
        self.check(again)
        handled = self.assess(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        self.assertTrue(handled['alreadyHandled'])
        self.check(handled)
        self.agree(out['caseId'], 'disagree', override=True)
        fm = self.check(self.tool('decisionStatus', caseId=out['caseId'])['result'])
        self.assertIn('reversed', fm['nextStep'])

    def test_a_long_status_text_or_long_names_are_cut_not_the_status(self):
        view = {'status': 'awaiting_owner', 'handling': 'owner_review', 'statusText': 'S' * 900, 'why': 'W' * 400, 'caseId': 'case_' + 'c' * 16,
                'customer': {'name': 'N' * 200, 'id': 'x'},
                'keyFacts': {'kind': 'trial_credit', 'orderAmount': {'text': 'AUD ' + '9' * 50}, 'verifiedDeposit': {'text': 'AUD ' + '9' * 50}, 'exposure': {'text': 'AUD ' + '9' * 50},
                             'termsDays': 14, 'dueDateIfApproved': '2026-11-10'}}
        fm = delegation.for_model(view)
        self.assertLessEqual(len(json.dumps(fm, ensure_ascii=False)), delegation.FOR_MODEL_LIMIT)
        self.assertEqual((fm['status'], fm['handling']), ('awaiting_owner', 'owner_review'))
        self.assertTrue(fm['statusText'].startswith('SSS') and fm['statusText'].endswith('…'))
        self.assertLessEqual(len(fm['keyFacts']), 8)

    def test_a_view_with_nothing_in_it_still_makes_a_valid_small_model_view(self):
        fm = delegation.for_model({})
        self.assertEqual((fm['status'], fm['handling'], fm['keyFacts']), (None, None, {}))
        self.assertLessEqual(len(json.dumps(fm)), delegation.FOR_MODEL_LIMIT)


# ---------------------------------------------------------------- the policy save keeps two settings the page cannot send yet

class PolicySaveKeepsTests(LoopCase):
    def save(self, **sections):
        """A PUT as the Owner page sends it today: the demo rules, with these sections changed, and neither `feedback` nor `trackRecord.sources` unless given."""
        body = {**delegation_demo.DEMO_POLICY, **sections, 'expectedVersion': self.policy()['version']}
        status, out = self.put_policy(body)
        self.assertEqual(status, 200, out)
        return out

    def set_both(self):
        out = self.save(feedback={'tacitAgreeAfterDays': 7}, trackRecord={'minReviewedCases': 5, 'minAgreement': '0.8', 'sources': 'live'})
        self.assertEqual((out['feedback'], out['trackRecord']['sources']), ({'tacitAgreeAfterDays': 7}, 'live'))

    def test_a_save_that_omits_them_keeps_the_current_values(self):
        self.set_both()
        out = self.save()   # the page's body: no feedback, trackRecord without sources
        self.assertEqual((out['feedback'], out['trackRecord']['sources'], out['version']), ({'tacitAgreeAfterDays': 7}, 'live', 3))
        self.assertEqual(self.policy()['trackRecord'], {'minReviewedCases': 5, 'minAgreement': '0.8', 'sources': 'live'})
        no_section = {k: v for k, v in delegation_demo.DEMO_POLICY.items() if k != 'trackRecord'}
        status, out = self.put_policy({**no_section, 'expectedVersion': 3})
        self.assertEqual(status, 200, out)
        self.assertEqual((out['trackRecord']['sources'], out['feedback']), ('live', {'tacitAgreeAfterDays': 7}))
        self.assertEqual((out['trackRecord']['minReviewedCases'], out['trackRecord']['minAgreement']), (5, '0.8'))   # the section's own keys took their defaults
        self.assertEqual(self.save(feedback={})['feedback'], {'tacitAgreeAfterDays': 7})   # an empty section also keeps it

    def test_an_explicit_value_wins_null_for_tacit_turns_it_off(self):
        self.set_both()
        self.assertEqual(self.save(feedback={'tacitAgreeAfterDays': None})['feedback'], {'tacitAgreeAfterDays': None})
        self.assertEqual(self.policy()['trackRecord']['sources'], 'live')   # the other one is still kept
        out = self.save(trackRecord={'minReviewedCases': 5, 'minAgreement': '0.8', 'sources': 'fictional'})
        self.assertEqual((out['trackRecord']['sources'], out['feedback']), ('fictional', {'tacitAgreeAfterDays': None}))
        self.assertEqual(self.save(feedback={'tacitAgreeAfterDays': 30})['feedback'], {'tacitAgreeAfterDays': 30})

    def test_a_bad_explicit_value_is_still_refused_and_nothing_is_saved(self):
        self.set_both()
        status, body = self.put_policy({**delegation_demo.DEMO_POLICY, 'trackRecord': {'sources': 'nobody'}, 'expectedVersion': 2})
        self.assertEqual((status, body['field']), (400, 'trackRecord.sources'))
        status, body = self.put_policy({**delegation_demo.DEMO_POLICY, 'feedback': {'tacitAgreeAfterDays': 0}, 'expectedVersion': 2})
        self.assertEqual((status, body['field']), (400, 'feedback.tacitAgreeAfterDays'))
        self.assertEqual(self.policy()['version'], 2)

    def test_every_bound_and_limit_left_out_still_takes_its_version_zero_value(self):
        self.set_both()
        defaults = delegation.default_policy(SETTINGS)
        sparse = {'mode': 'delegated', 'expectedVersion': 2}   # nothing else: a save that leaves every bound out
        status, out = self.put_policy(sparse)
        self.assertEqual(status, 200, out)
        for key in ('limits', 'extensions', 'newCustomers', 'evidence', 'restrictions'):
            self.assertEqual(out[key], defaults[key], key)
        self.assertEqual((out['trackRecord'], out['feedback']), ({'minReviewedCases': 5, 'minAgreement': '0.8', 'sources': 'live'}, {'tacitAgreeAfterDays': 7}))

    def test_pause_still_keeps_everything(self):
        self.set_both()
        self.assertEqual(self.pause()['trackRecord']['sources'], 'live')
        self.assertEqual(self.policy()['feedback'], {'tacitAgreeAfterDays': 7})
