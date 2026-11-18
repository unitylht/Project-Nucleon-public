"""The research hook (research.py): the training table the cases produce for the team's classifier, and the shadow score. The rules never read either.
Fictional data throughout; the model fitted here is fitted on a handful of invented rows and proves the plumbing, nothing about credit."""
import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import research
from test_delegation import APPROVE, DelegationCase


def synthetic_rows(n=40):
    """Invented rows: the Owner declines big exposures asked for long. Enough signal for a logistic fit to separate them."""
    rows = []
    for i in range(n):
        exposure, days = 10000 + 7000 * (i % 8), 7 + 5 * (i % 5)
        decline = 1 if exposure > 40000 and days > 14 else 0
        rows.append({'exposure': exposure, 'extensionDays': days, research.LABEL: decline})
    return rows


class ResearchUnitTests(unittest.TestCase):
    def test_numbers_from_stored_features(self):
        f = research.numeric({'priorLateShare': '1/4', 'sizeRatio': '11/10', 'nothingElseOverdue': True, 'exposure': 52000, 'isNew': None, 'depositShare': 'x'},
                             ('priorLateShare', 'sizeRatio', 'nothingElseOverdue', 'exposure', 'isNew', 'depositShare', 'termsDays'))
        self.assertEqual(f, {'priorLateShare': 0.25, 'sizeRatio': 1.1, 'nothingElseOverdue': 1.0, 'exposure': 52000.0, 'isNew': None, 'depositShare': None, 'termsDays': None})

    def test_fit_then_score_and_missing_feature_is_unavailable(self):
        m = research.load_model(research.fit(synthetic_rows(), ['exposure', 'extensionDays'], name='t', version='1'))
        self.assertEqual((m['name'], m['version'], m['features'], m['trainedOn']['rows']), ('t', '1', ['exposure', 'extensionDays'], 40))
        low = research.score(m, {'exposure': 10000.0, 'extensionDays': 7.0})
        high = research.score(m, {'exposure': 59000.0, 'extensionDays': 27.0})
        self.assertTrue(low['available'] and high['available'])
        self.assertLess(low['probability'], 0.5)
        self.assertGreater(high['probability'], 0.5)
        gone = research.score(m, {'exposure': 59000.0, 'extensionDays': None})
        self.assertEqual((gone['available'], gone['missing'], gone['probability']), (False, ['extensionDays'], None))   # an unknown is never zero

    def test_fit_refuses_one_class_and_load_checks_shape(self):
        with self.assertRaises(ValueError):
            research.fit([{'exposure': 1, research.LABEL: 0}, {'exposure': 2, research.LABEL: 0}], ['exposure'])
        with self.assertRaises(ValueError):
            research.load_model({'features': ['a', 'b'], 'mean': [0], 'scale': [1], 'coef': [1]})
        with self.assertRaises(ValueError):
            research.load_model({'features': ['a'], 'mean': [0], 'scale': [0], 'coef': [1]})
        self.assertIsNone(research.load_model(None))

    def test_training_rows_and_csv_keep_request_time_features(self):
        cases = [{'id': 'c1', 'kind': 'extension', 'dataset': 'live', 'customerId': 'cust-1', 'createdAt': '2026-10-24T03:00:00Z', 'policyVersion': 2, 'handling': 'owner_review',
                  'ownerDecision': 'decline', 'outcome': None, 'features': {'exposure': 99}, 'research': {'features': {'exposure': 52000.0, 'credit_term_days': 30.0}}},
                 {'id': 'c2', 'kind': 'trial_credit', 'dataset': 'fictional_example', 'decidedOn': '2026-05-12', 'ownerDecision': 'approve', 'features': {'exposure': 1000, 'depositShare': '1/4'}},
                 {'id': 'c3', 'kind': 'extension', 'dataset': 'live', 'ownerDecision': None}]
        rows = research.training_rows(cases)
        self.assertEqual([r['case_id'] for r in rows], ['c1', 'c2'])
        self.assertEqual((rows[0]['exposure'], rows[0]['credit_term_days'], rows[0][research.LABEL], rows[0]['request_date']), (52000.0, 30.0, 1, '2026-10-24'))   # the stored row, not features[]
        self.assertEqual((rows[1]['depositShare'], rows[1][research.LABEL], rows[1]['request_date']), (0.25, 0, '2026-05-12'))
        text = research.csv_text(rows)
        head = text.splitlines()[0].split(',')
        self.assertEqual(head[:4], ['case_id', 'kind', 'dataset', 'customer_id'])
        self.assertIn('prior_late_receipt_fraction', head)
        self.assertEqual(head[-1], 'Target_Deny')
        self.assertEqual(len(text.splitlines()), 3)

    def test_agreement_counts_only_scored_decided_cases(self):
        cases = [{'ownerDecision': 'decline', 'research': {'shadow': {'probability': 0.8}}}, {'ownerDecision': 'approve', 'research': {'shadow': {'probability': 0.7}}},
                 {'ownerDecision': 'approve', 'research': {'shadow': None}}, {'ownerDecision': 'approve'}]
        self.assertEqual(research.agreement(cases), {'n': 2, 'agreed': 1, 'threshold': 0.5})


class ShadowCase(DelegationCase):
    """The delegation demonstration with a shadow model configured (fitted on invented rows; features the live cases carry)."""

    def setUp(self):
        self.model_path = Path(tempfile.mkdtemp()) / 'shadow.json'
        self.model_path.write_text(json.dumps(research.fit(synthetic_rows(), ['exposure', 'extensionDays'], name='fictional-lr', version='0')))
        super().setUp()

    def start(self, adapter=None, mode='mock', inline_wait=10, sample_data=False, **options):
        return super().start(adapter, mode, inline_wait, sample_data=sample_data, shadow_model=str(self.model_path), **options)

    def raw(self, path, role):
        req = Request(self.base + path, headers={'Cookie': self.cookies[role]})
        try:
            response = urlopen(req, timeout=10)
        except HTTPError as error:
            response = error
        with response:
            return response.status, response.read().decode('utf-8'), response.headers


class ShadowTests(ShadowCase):
    def test_owner_sees_the_shadow_score_staff_do_not_and_the_decision_is_the_rules_own(self):
        out = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        self.assertEqual((out['status'], out['handling']), ('decided', 'autonomous_approve'))   # exactly as without a model (test_1 in test_delegation)
        self.assertNotIn('research', out)   # Staff resolved it: no research row in their view
        owner = self.call('/api/decision-cases/' + out['caseId'], None, 'owner')[1]
        r = owner['research']
        self.assertTrue({'asOf', 'at', 'features', 'shadow'} <= set(r), sorted(r))   # (dated() adds asOfText for the page)
        self.assertEqual(r['asOf'], '2026-10-24')   # the request date the training table reports: the business's as-of date, not the wall clock
        self.assertEqual((r['shadow']['model'], r['shadow']['version'], r['shadow']['available']), ('fictional-lr', '0', True))
        self.assertTrue(0.0 <= r['shadow']['probability'] <= 1.0)
        self.assertEqual(r['features']['extensionDays'], 23.0)
        self.assertEqual(r['features']['exposure'], 48000.0)
        self.assertIn('credit_term_days', r['features'])   # the replay's pipeline features travelled with the case
        self.assertIn('prior_receipt_count', r['features'])
        staff = self.call('/api/decision-cases/' + out['caseId'], None, 'staff')[1]
        self.assertNotIn('research', staff)
        self.assertNotIn('research', owner['reasons'])   # nothing of it in the evaluation itself
        self.assertFalse(any('model' in x.lower() and 'shadow' in x.lower() for x in owner['reasons'] + owner['warnings']))
        self.assertEqual(self.model.calls, 0)

    def test_training_table_and_research_figures_are_the_owners(self):
        out = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        self.assertEqual(self.raw('/api/delegation/training.csv', 'staff')[0], 403)
        status, text, headers = self.raw('/api/delegation/training.csv', 'owner')
        self.assertEqual(status, 200)
        self.assertTrue(headers['Content-Type'].startswith('text/csv'))
        lines = text.splitlines()
        head = lines[0].split(',')
        self.assertEqual(head[-1], 'Target_Deny')
        self.assertIn('credit_term_days', head)
        self.assertGreater(len(lines), 2)   # the fictional decision memory is in it, labelled by dataset
        self.assertFalse(any(line.startswith(out['caseId']) for line in lines))   # the agent's approval is not a label until the Owner answers it
        self.assertEqual(self.feedback(out['caseId'], {'verdict': 'disagree', 'reason': 'Too long for this one.'})[0], 200)
        lines = self.raw('/api/delegation/training.csv', 'owner')[1].splitlines()
        row = next(line for line in lines if line.startswith(out['caseId'] + ',extension,live,'))
        cells = dict(zip(lines[0].split(','), row.split(',')))
        self.assertEqual((cells['owner_decision'], cells['Target_Deny'], cells['extensionDays'], cells['policy_version'], cells['request_date']), ('decline', '1', '23.0', '1', '2026-10-24'))
        self.assertNotEqual(cells['credit_term_days'], '')   # the replay's features, as kept at request time
        research_view = self.call('/api/delegation/research', None, 'owner')[1]
        self.assertEqual((research_view['model']['name'], research_view['model']['features']), ('fictional-lr', ['exposure', 'extensionDays']))
        self.assertEqual(research_view['agreement']['n'], 1)   # one decided case carries a score and an Owner verdict
        self.assertEqual(self.call('/api/delegation/research', None, 'staff')[0], 403)


class NoModelTests(DelegationCase):
    def test_without_a_model_the_case_keeps_its_features_and_no_score(self):
        out = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        owner = self.call('/api/decision-cases/' + out['caseId'], None, 'owner')[1]
        self.assertIsNone(owner['research']['shadow'])
        self.assertEqual(owner['research']['features']['extensionDays'], 23.0)
        view = self.call('/api/delegation/research', None, 'owner')[1]
        self.assertEqual((view['model'], view['agreement']['n'], view['withFeatures'], view['decided']), (None, 0, 0, 27))   # 27 = the fictional decision memory; the agent's approval has no Owner verdict yet


if __name__ == '__main__':
    unittest.main()


class LoopTests(DelegationCase):
    """The loop: the Owner refits (or the setting does), versions are saved immutably, the settings hold the promotion bar."""

    def test_owner_refits_on_the_table_and_versions_accumulate(self):
        self.assertEqual(self.send('POST', '/api/delegation/research/refit', {}, role='staff')[0], 403)
        status, body = self.send('POST', '/api/delegation/research/refit', {'note': 'first fit'})
        self.assertEqual(status, 200, body)
        m = body['model']
        self.assertEqual((m['name'], m['version'], m['source'], m['scoring']), ('nucleon-builtin', '1', 'saved', 'builtin'))
        self.assertTrue(m['features'] and set(m['features']) <= set(research.LADDER_FEATURES + research.REPLAY_FEATURES), m['features'])
        self.assertEqual((m['trainedOn']['rows'], m['trainedOn']['positives']), (27, 6))   # the fictional decision memory, labelled
        self.assertTrue(m['coefficients'] and set(m['coefficients']) == set(m['features']))
        status, body = self.send('POST', '/api/delegation/research/refit', {'features': ['exposure', 'isNew']})
        self.assertEqual((status, body['model']['version'], body['model']['features']), (200, '2', ['exposure', 'isNew']))
        self.assertEqual([v['version'] for v in body['versions']], ['2', '1'])
        self.assertEqual(body['versions'][1]['createdBy']['note'], 'first fit')
        # a feature the fictional rows do not carry leaves no usable row: refused, nothing saved
        status, body = self.send('POST', '/api/delegation/research/refit', {'features': ['credit_term_days']})
        self.assertEqual((status, body['error']), (409, 'NOT_ENOUGH_DATA'))
        status, body = self.send('POST', '/api/delegation/research/refit', {'features': ['nope']})
        self.assertEqual((status, body['error']), (400, 'INVALID_INPUT'))
        self.assertEqual(self.count('research_models'), 2)
        self.assertEqual(self.model.calls, 0)

    def test_settings_are_validated_and_kept(self):
        status, body = self.send('POST', '/api/delegation/research/settings', {'promotion': {'enabled': True, 'minCases': 3, 'minAgreement': 0.6}, 'autoRefitEvery': 5})
        self.assertEqual(status, 200, body)
        self.assertEqual(body['settings'], {'autoRefitEvery': 5, 'promotion': {'enabled': True, 'minCases': 3, 'minAgreement': 0.6, 'threshold': 0.5}})
        self.assertEqual(self.call('/api/delegation/research', None, 'owner')[1]['settings']['autoRefitEvery'], 5)
        self.assertEqual(self.send('POST', '/api/delegation/research/settings', {'promotion': {'minCases': 0}})[0], 400)
        self.assertEqual(self.send('POST', '/api/delegation/research/settings', {'bogus': 1})[0], 400)
        self.assertEqual(self.send('POST', '/api/delegation/research/settings', {}, role='staff')[0], 403)
        self.assertFalse(self.call('/api/delegation/research', None, 'owner')[1]['promotion']['active'])   # enabled, but no model and no cases

    def test_a_verdict_refits_automatically_under_the_setting(self):
        self.assertEqual(self.send('POST', '/api/delegation/research/settings', {'autoRefitEvery': 1})[0], 200)
        out = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        self.assertIsNone(self.call('/api/delegation/research', None, 'owner')[1]['model'])   # no verdict yet: nothing fitted
        self.assertEqual(self.feedback(out['caseId'], {'verdict': 'agree', 'reason': 'Right call.'})[0], 200)
        view = self.call('/api/delegation/research', None, 'owner')[1]
        m = view['model']
        self.assertEqual((m['version'], m['source'], m['trainedOn']['rows'], m['trainedOn']['ownerAnswered']), ('1', 'saved', 28, 1))
        self.assertTrue(view['versions'][0]['createdBy']['auto'])
        # the next case is scored by the saved version
        trial = self.resolved(**self.trial('northside', '800.00'))
        owner = self.call('/api/decision-cases/' + trial['caseId'], None, 'owner')[1]
        self.assertEqual((owner['research']['modelVersion'], owner['research']['promoted'], owner['research']['shadow']['model']), ('1', False, 'nucleon-builtin'))
        self.assertEqual(trial['handling'], 'autonomous_approve')   # promotion is off: the score changed nothing


class PromotionCase(DelegationCase):
    """A decisive bootstrap model on exposure alone (invented rows: big exposures are declined), so a promoted score escalates the demo's trial credit."""

    def setUp(self):
        rows = [{'exposure': 10000 + 5000 * i, research.LABEL: 1 if 10000 + 5000 * i > 40000 else 0} for i in range(20)]
        self.model_path = Path(tempfile.mkdtemp()) / 'shadow.json'
        self.model_path.write_text(json.dumps(research.fit(rows, ['exposure'], name='fictional-exposure', version='0')))
        super().setUp()

    def start(self, adapter=None, mode='mock', inline_wait=10, sample_data=False, **options):
        return super().start(adapter, mode, inline_wait, sample_data=sample_data, shadow_model=str(self.model_path), **options)


class PromotionTests(PromotionCase):
    def test_once_the_bar_is_met_the_score_sends_a_case_to_the_owner(self):
        first = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))   # exposure 48000: the model says decline; the rules approved
        self.assertEqual(first['handling'], 'autonomous_approve')
        self.assertEqual(self.feedback(first['caseId'], {'verdict': 'disagree', 'reason': 'Not this one.'})[0], 200)   # the Owner declines too: 1 of 1 agreed
        view = self.call('/api/delegation/research', None, 'owner')[1]
        self.assertEqual((view['agreement']['n'], view['agreement']['agreed'], view['promotion']['active']), (1, 1, False))   # promotion is off
        status, body = self.send('POST', '/api/delegation/research/settings', {'promotion': {'enabled': True, 'minCases': 1, 'minAgreement': 0.5}})
        self.assertEqual((status, body['promotion']['active']), (200, True), body['promotion'])
        trial = self.resolved(**self.trial('northside', '800.00'))   # exposure 60000: within every bound (test_2 approves it), but the promoted model says decline
        self.assertEqual((trial['status'], trial['handling']), ('awaiting_owner', 'owner_review'), trial['reasons'])
        self.assertIn("the team's model", trial['why'])
        self.assertTrue(any('fictional-exposure v0' in r and 'chance that you decline' in r for r in trial['reasons']), trial['reasons'])
        owner = self.call('/api/decision-cases/' + trial['caseId'], None, 'owner')[1]
        self.assertEqual((owner['research']['promoted'], owner['research']['recommendation']), (True, 'escalate'))
        self.assertGreaterEqual(owner['research']['shadow']['probability'], 0.5)
        # off again: the next request is the rules' own
        self.assertEqual(self.send('POST', '/api/delegation/research/settings', {'promotion': {'enabled': False}})[0], 200)
        self.assertEqual(self.model.calls, 0)


class FakeModelService:
    """A model service as tools/model-service answers: /train returns an http-scored model, /score a fixed probability."""

    def __init__(self, probability=0.9):
        import http.server
        import threading
        service = self

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0)) or 0) or b'{}')
                service.seen.append((self.path, body))
                if self.path == '/train':
                    out = {'name': 'team-xgb', 'features': body['features'], 'scoring': 'http', 'ref': 'team-xgb-' + body['version'], 'trainedOn': {'service': True}}
                elif self.path == '/score':
                    out = {'probability': service.probability}
                else:
                    self.send_response(404); self.end_headers(); return
                data = json.dumps(out).encode()
                self.send_response(200); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(data))); self.end_headers()
                self.wfile.write(data)
        self.seen, self.probability = [], probability
        self.server = http.server.HTTPServer(('127.0.0.1', 0), H)
        self.url = 'http://127.0.0.1:' + str(self.server.server_port)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


class HttpProviderTests(DelegationCase):
    def setUp(self):
        self.service = FakeModelService()
        super().setUp()

    def tearDown(self):
        self.service.stop()
        super().tearDown()

    def start(self, adapter=None, mode='mock', inline_wait=10, sample_data=False, **options):
        return super().start(adapter, mode, inline_wait, sample_data=sample_data, research_provider={'kind': 'http', 'url': self.service.url, 'timeoutSeconds': 2}, **options)

    def test_training_and_scoring_go_through_the_service_and_its_absence_is_no_score(self):
        status, body = self.send('POST', '/api/delegation/research/refit', {'features': ['exposure', 'isNew']})
        self.assertEqual(status, 200, body)
        self.assertEqual((body['model']['name'], body['model']['scoring'], body['model']['version'], body['provider']['kind']), ('team-xgb', 'http', '1', 'http'))
        self.assertEqual(self.service.seen[0][0], '/train')
        self.assertEqual(len(self.service.seen[0][1]['rows']), 27)
        self.assertEqual(self.service.seen[0][1]['label'], 'Target_Deny')
        out = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        owner = self.call('/api/decision-cases/' + out['caseId'], None, 'owner')[1]
        self.assertEqual((owner['research']['shadow']['probability'], owner['research']['shadow']['model'], owner['research']['modelVersion']), (0.9, 'team-xgb', '1'))
        self.assertEqual(self.service.seen[-1][0], '/score')
        self.assertEqual(sorted(self.service.seen[-1][1]['features']), ['exposure', 'isNew'])
        self.assertEqual(out['handling'], 'autonomous_approve')   # research only
        self.service.stop()
        trial = self.resolved(**self.trial('northside', '800.00'))
        owner = self.call('/api/decision-cases/' + trial['caseId'], None, 'owner')[1]
        self.assertFalse(owner['research']['shadow']['available'])
        self.assertIn('model service', owner['research']['shadow']['error'])
        self.assertEqual(trial['handling'], 'autonomous_approve')   # the service being down changes nothing


class ExceptionBandCase(DelegationCase):
    """A bootstrap model on extensionDays alone (invented rows: the Owner approves extensions up to about 40 days), for the exception band."""

    def setUp(self):
        rows = [{'extensionDays': 5 + 3 * i, research.LABEL: 1 if 5 + 3 * i > 40 else 0} for i in range(30)]
        self.model_path = Path(tempfile.mkdtemp()) / 'shadow.json'
        self.model_path.write_text(json.dumps(research.fit(rows, ['extensionDays'], name='fictional-days', version='0')))
        super().setUp()

    def start(self, adapter=None, mode='mock', inline_wait=10, sample_data=False, **options):
        return super().start(adapter, mode, inline_wait, sample_data=sample_data, shadow_model=str(self.model_path), **options)

    def policy_with(self, **exceptions):
        p = self.call('/api/delegation/policy', None, 'owner')[1]
        body = {k: p[k] for k in ('mode', 'limits', 'extensions', 'newCustomers', 'evidence', 'restrictions', 'trackRecord', 'feedback', 'customers')}
        body['exceptions'] = {'enabled': True, 'maxOverExposureShare': '0.5', 'maxExtraDays': 15, 'minModelApprove': '0.6', 'minSimilarApproved': 3, 'suggestDeclineAbove': '0.8', **exceptions}
        body['expectedVersion'] = p['version']
        status, out = self.send('PUT', '/api/delegation/policy', body)
        self.assertEqual(status, 200, out)
        return out


class ExceptionBandTests(ExceptionBandCase):
    def test_a_breach_inside_the_band_is_approved_as_an_exception_and_labelled(self):
        # 38 days: over the 30-day bound, inside the band (30 + 15), the model says approve, and the demo memory has approved comparable extensions
        self.policy_with()
        out = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-20'))   # 33 days: over the 30-day bound, inside the band (30 + 15); the model is confident at 33
        self.assertEqual((out['status'], out['handling']), ('decided', 'autonomous_approve'), out['reasons'] + out['warnings'][:1])
        self.assertTrue(out['exception']['applied'], out['exception'])
        self.assertEqual(out['exception']['checks'], ['extension_days'])
        self.assertIn('Approved as an exception inside the band', out['reasons'][0])
        self.assertEqual([c['status'] for c in out['risk']['checks'] if c['key'] == 'extension_days'], ['exception'])
        rows = self.call('/api/delegation/cases', None, 'owner')[1]['cases']
        self.assertTrue(next(r for r in rows if r['caseId'] == out['caseId'])['exception'])
        self.assertEqual(self.model.calls, 0)

    def test_beyond_the_band_or_without_the_owner_switch_the_case_goes_to_the_owner(self):
        out = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-20'))   # band off: the 30-day bound escalates as before
        self.assertEqual(out['handling'], 'owner_review')
        self.assertFalse(out['exception']['applied'])
        self.assertEqual(self.feedback(out['caseId'], {'verdict': 'agree', 'reason': 'x'})[0], 409)   # not an agent decision; just to keep the case out of the way
        self.policy_with(maxExtraDays=5)
        far = self.resolved(**self.extension('cityside', 'DEMO-410', date='2026-12-31'))   # 64 days: beyond 30 + 5, and unusually large: escalates with the reason
        self.assertEqual(far['handling'], 'owner_review')
        self.assertFalse(far['exception']['applied'])
        self.assertTrue(any('exception band' in w.lower() for w in far['warnings']), far['warnings'])

    def test_a_prepared_decline_appears_only_when_the_model_is_confident(self):
        self.policy_with(suggestDeclineAbove='0.5')
        far = self.resolved(**self.extension('cityside', 'DEMO-410', date='2026-12-31'))   # 64 days: the model's chance of a decline is high
        self.assertEqual(far['handling'], 'owner_review')
        self.assertEqual(far['suggested']['outcome'], 'decline')
        self.assertGreaterEqual(far['suggested']['probability'], 0.5)
        self.assertIn('Decline with one click', far['suggested']['text'])
        self.assertEqual(self.call('/api/decision-cases/' + far['caseId'], None, 'staff')[1].get('suggested'), far['suggested'])   # the card says it to both roles; only the Owner can act


class OldPolicyVersionTests(DelegationCase):
    def test_a_version_saved_before_the_band_reads_with_the_band_off(self):
        # a stored version without 'customers' and 'exceptions' (as every version before 2 and 3 Nov 2026): it must read back, with the band off
        import json as _json
        row = self.app.db.execute('SELECT data FROM delegation_policies ORDER BY version DESC LIMIT 1').fetchone()
        data = _json.loads(row[0]); data.pop('customers', None); data.pop('exceptions', None)
        with self.app.db:
            self.app.db.execute('INSERT INTO delegation_policies (version, created_at, data) VALUES (?,?,?)', (99, '2026-10-24T00:00:00+00:00', _json.dumps(data)))
        status, p, _ = self.call('/api/delegation/policy', None, 'owner')
        self.assertEqual((status, p['version'], p['exceptions']['enabled'], p['customers']), (200, 99, False, {}))
        out = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))   # and the ladder still runs on it
        self.assertEqual(out['handling'], 'autonomous_approve')


class EmptyTableRefitTests(DelegationCase):
    """A workspace with no decided case and no answered what-if yet (NTK, 11 Nov 2026): "Fit a new version" said "features is a list of feature names"."""
    def setUp(self):
        super(DelegationCase, self).setUp()
        from test_controlled_actions import Tripwire
        self.start(Tripwire(), 'live', sample_data=False)
        self.call('/api/setup/workspace', {'mode': 'practice', 'withSample': False}, 'owner', 'ws')
        self.call('/api/setup/settings', {'currency': 'AUD', 'scale': 2, 'timezone': 'Australia/Sydney'}, 'owner', 'st')

    def test_an_empty_training_table_says_there_is_nothing_to_fit_on(self):
        status, body = self.send('POST', '/api/delegation/research/refit', {})
        self.assertEqual((status, body['error']), (409, 'NOT_ENOUGH_DATA'), body)
        self.assertIn('0 usable rows', body['message'])
        self.assertIn('approved some and declined some', body['message'])
        self.assertNotIn('list of feature names', body['message'])
        self.assertEqual(self.count('research_models'), 0)
