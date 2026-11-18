"""Observable HTTP workflow checks using fictional fixtures and isolated databases."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from server import App, make_server

MESSAGE = 'Could we pay invoice DEMO-101 on 2026-10-30 instead?'


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'demo.sqlite3'
        self.start()

    def start(self):
        self.app = App(self.path, sample_data=True)
        self.server = make_server(self.app, 0)
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=.02), daemon=True)
        self.thread.start()
        self.base = 'http://127.0.0.1:' + str(self.server.server_port)
        self.cookies = {}
        for role in ('staff', 'owner'):
            status, data, headers = self.call('/api/demo/login', {'accessCode': self.app.demo_codes[role]})
            self.assertEqual(status, 200)
            self.cookies[role] = headers['Set-Cookie'].split(';')[0]

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.app.db.close()

    def tearDown(self):
        self.stop()
        self.tmp.cleanup()

    def call(self, path, body=None, role=None, key=None):
        headers = {}
        if role:
            headers['Cookie'] = self.cookies[role]
        if key:
            headers['Idempotency-Key'] = key
        if body is not None:
            headers['Content-Type'] = 'application/json'
        req = Request(self.base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
        try:
            response = urlopen(req, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.loads(response.read()), response.headers

    def create(self, message=MESSAGE, key='intake-1'):
        status, r, _ = self.call('/api/requests', {'messageText': message}, 'staff', key)
        self.assertEqual(status, 202, r)
        return r

    def payload(self, r, outcome='approve', approved='2026-10-30'):
        return {'expectedRequestVersion': r['version'], 'analysisId': r['analysis']['id'],
                'evidenceVersion': r['analysis']['snapshot']['evidenceVersion'],
                'outcome': outcome, 'approvedDueDate': approved, 'reason': 'This invoice only.'}

    def decide(self, r, payload=None, role='owner', key='decision-1'):
        return self.call('/api/requests/' + r['id'] + '/decisions', payload or self.payload(r), role, key)

    def reopen(self, r):
        status, result, _ = self.call('/api/requests/' + r['id'], role='staff')
        self.assertEqual(status, 200)
        return result

    def test_complete_flow_and_reopen(self):
        r = self.create()
        self.assertEqual(r['status'], 'awaiting_owner')
        self.assertEqual(r['analysis']['aiStatus'], 'mocked')
        self.assertIsNone(r['analysis']['modelId'])
        facts = r['analysis']['snapshot']['facts']
        self.assertEqual(facts['extensionDays'], 10)
        self.assertEqual(facts['daysOverdue'], 0)
        self.assertEqual(facts['invoiceOutstanding']['minorUnits'], '125000')
        status, decision, _ = self.decide(r)
        self.assertEqual(status, 201, decision)
        result = self.reopen(r)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['responseDraft']['decisionId'], decision['id'])
        self.assertEqual(result['responseDraft']['deliveryStatus'], 'not_sent')
        self.assertIn('is Friday 30 October 2026.', result['responseDraft']['text'])   # QA U4: written out, not ISO
        self.assertNotIn('2026-10-30', result['responseDraft']['text'])
        invoice = next(i for i in self.app.fixture()['invoices'] if i['reference'] == 'DEMO-101')
        self.assertEqual(invoice['originalDueDate'], '2026-10-20')
        tools = [e['data']['tool'] for e in result['history'] if e['kind'] == 'tool.executed']
        self.assertIn('prepareApprovalTask', tools)
        self.assertIn('saveResponseDraft', tools)

    def test_clarification_resumes_new_version(self):
        r = self.create('Could we pay invoice DEMO-101 later?')
        self.assertEqual(r['status'], 'needs_information')
        self.assertIsNone(r['requestedDueDate'])
        path = '/api/requests/' + r['id'] + '/clarifications/' + r['task']['id'] + '/answers'
        body = {'expectedRequestVersion': r['version'], 'answers': [{'field': 'requestedDueDate', 'value': '2026-10-30'}]}
        status, result, _ = self.call(path, body, 'staff', 'answer-1')
        self.assertEqual(status, 202, result)
        self.assertEqual(result['version'], 2)
        self.assertEqual(result['status'], 'awaiting_owner')
        self.assertNotEqual(result['analysis']['id'], r['analysis']['id'])
        status, _, _ = self.call(path, body, 'staff', 'answer-2')
        self.assertEqual(status, 409)

    def test_owner_changes_date(self):
        r = self.create()
        status, _, _ = self.decide(r, self.payload(r, approved='2026-11-03'))
        self.assertEqual(status, 201)
        result = self.reopen(r)
        self.assertEqual(result['requestedDueDate'], '2026-10-30')
        self.assertEqual(result['decision']['approvedDueDate'], '2026-11-03')
        self.assertIn('Tuesday 3 November 2026', result['responseDraft']['text'])
        self.assertNotIn('2026-10-30', result['responseDraft']['text'])

    def test_owner_declines(self):
        r = self.create()
        status, _, _ = self.decide(r, self.payload(r, 'decline', None))
        self.assertEqual(status, 201)
        result = self.reopen(r)
        self.assertIn('declined', result['responseDraft']['text'])
        self.assertIsNone(result['decision']['approvedDueDate'])

    def test_staff_cannot_spoof_owner_and_anonymous_cannot_read(self):
        r = self.create()
        payload = {**self.payload(r), 'role': 'owner', 'decidedBy': 'owner_demo'}
        status, _, _ = self.decide(r, payload, role='staff')
        self.assertEqual(status, 403)
        status, _, _ = self.call('/api/requests/' + r['id'])
        self.assertEqual(status, 401)
        self.assertIsNone(self.reopen(r)['decision'])

    def test_duplicate_intake_and_key_conflict(self):
        first = self.create()
        again = self.create()
        self.assertEqual(first['id'], again['id'])
        self.assertEqual(len(self.app.records()), 1)
        status, _, _ = self.call('/api/requests', {'messageText': MESSAGE + ' changed'}, 'staff', 'intake-1')
        self.assertEqual(status, 409)

    def test_duplicate_decision_is_single_commit(self):
        r = self.create()
        payload = self.payload(r)
        first = self.decide(r, payload)
        second = self.decide(r, payload)
        self.assertEqual(first[0], 201)
        self.assertEqual(first[1]['id'], second[1]['id'])
        commits = [e for e in self.reopen(r)['history'] if e['kind'] == 'decision.committed']
        self.assertEqual(len(commits), 1)

    def test_stale_request_version_rejected(self):
        r = self.create()
        payload = self.payload(r)
        payload['expectedRequestVersion'] = 0
        status, _, _ = self.decide(r, payload)
        self.assertEqual(status, 409)
        self.assertIsNone(self.reopen(r)['decision'])

    def test_changed_evidence_blocks_old_owner_task(self):
        first = self.create(key='first')
        second = self.create(key='second')
        self.assertEqual(self.decide(first)[0], 201)
        status, result, _ = self.decide(second, key='other-decision')
        self.assertEqual(status, 409)
        self.assertEqual(result['error'], 'STALE_EVIDENCE')
        status, refreshed, _ = self.call('/api/requests/' + second['id'] + '/reanalyse',
                                       {'expectedRequestVersion': second['version']}, 'staff', 'refresh-1')
        self.assertEqual(status, 202)
        self.assertEqual(refreshed['status'], 'needs_information')
        self.assertEqual(refreshed['analysis']['snapshot']['currentEffectiveDueDate'], '2026-10-30')

    def test_unavailable_adapter_is_honest_manual_fallback(self):
        self.app.agent_mode = 'unavailable'
        r = self.create()
        self.assertEqual(r['analysis']['aiStatus'], 'failed')
        self.assertEqual(r['task']['mode'], 'manual_fallback')
        self.assertIsNone(r['analysis']['brief']['suggestedOption'])
        self.assertEqual(self.decide(r)[0], 201)
        self.assertEqual(self.reopen(r)['responseDraft']['generation'], 'template')

    def test_restart_preserves_completed_record(self):
        r = self.create()
        self.assertEqual(self.decide(r)[0], 201)
        before = self.reopen(r)
        self.stop()
        self.start()
        after = self.reopen(r)
        self.assertEqual(before['decision'], after['decision'])
        self.assertEqual(before['responseDraft'], after['responseDraft'])
        self.assertEqual(before['history'], after['history'])

    def test_invalid_and_ambiguous_dates_do_not_guess(self):
        invalid = self.create('Invoice DEMO-101: please pay 2026-02-30.', 'bad-date')
        self.assertEqual(invalid['status'], 'needs_information')
        ambiguous = self.create('Move invoice DEMO-101 to 2026-10-20 or 2026-10-30.', 'two-dates')
        self.assertEqual(ambiguous['status'], 'needs_information')
        self.assertIsNone(ambiguous['requestedDueDate'])
        moved = self.create('Move invoice DEMO-101 from 2026-10-20 to 2026-10-30.', 'from-to')   # the date after "from" is the current one
        self.assertEqual((moved['status'], moved['requestedDueDate']), ('awaiting_owner', '2026-10-30'))

    def test_unknown_invoice_does_not_attach_another_invoices_facts(self):
        r = self.create('Please extend invoice DEMO-999 to 2026-10-30.')
        self.assertEqual(r['status'], 'needs_information')
        self.assertIsNone(r['customerId'])
        self.assertIsNone(r['analysis']['snapshot']['invoice'])
        self.assertEqual(r['analysis']['snapshot']['confirmedNotes'], [])
        path = '/api/requests/' + r['id'] + '/clarifications/' + r['task']['id'] + '/answers'
        status, resumed, _ = self.call(path, {'expectedRequestVersion': r['version'],
                     'answers': [{'field': 'invoiceReference', 'value': 'DEMO-101'}]}, 'staff', 'invoice-answer')
        self.assertEqual(status, 202)
        self.assertEqual(resumed['status'], 'awaiting_owner')


if __name__ == '__main__':
    unittest.main()
