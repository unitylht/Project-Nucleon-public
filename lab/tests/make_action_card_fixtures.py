"""Regenerates lab/tests/fixtures/action_card/*.json: REAL results of prepareRequest and actionStatus (from the records' own controlled-actions test
harness, fictional data, business date Sun 18 Oct 2026) for the action cards in test_action_card.py, one file per state an action can be in. Run from
the repo root with the system python:   python3 lab/tests/make_action_card_fixtures.py
Nothing here computes a result; the records tools do. The files are committed (ids and times are those of the run that made them) so the Lab's
suite needs no records server for the renderer."""
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'prototype'))
os.chdir(ROOT / 'prototype')
from test_controlled_actions import ActionsCase   # noqa: E402

OUT = ROOT / 'lab' / 'tests' / 'fixtures' / 'action_card'


class Make(ActionsCase):
    def status(self, action_id, role='staff'):
        status, body, _ = self.call('/api/tools/actionStatus', {'args': {'actionId': action_id}}, role)
        self.assertEqual((status, body['ok']), (200, True), body)
        return body['result']

    def save(self, name, **parts):
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / (name + '.json')).write_text(json.dumps(parts, ensure_ascii=False, indent=1, sort_keys=True) + '\n')

    def test_proposed(self):
        a = self.prepared()
        self.save('proposed', prepare=a, status=self.status(a['actionId']))
        b = self.prepared('p2', invoiceId=self.other['id'], reason=None, days=None, requestedDueDate='2026-11-10')
        self.save('proposed_no_reason', prepare=b, status=self.status(b['actionId']))

    def test_executed(self):
        a, body = self.confirmed()
        self.save('executed', status=self.status(a['actionId']))
        r = self.request_of(body['request']['id'], 'owner')
        decision = {'expectedRequestVersion': r['version'], 'analysisId': r['analysis']['id'], 'evidenceVersion': r['analysis']['snapshot']['evidenceVersion'],
                    'outcome': 'approve', 'approvedDueDate': '2026-11-03', 'reason': 'Fine.'}
        self.assertEqual(self.call('/api/requests/' + r['id'] + '/decisions', decision, 'owner', 'd1')[0], 201)
        self.save('executed_decided', status=self.status(a['actionId']))

    def test_cancelled(self):
        a = self.prepared()
        self.assertEqual(self.cancel(a['actionId'])[0], 200)
        self.save('cancelled', status=self.status(a['actionId']))

    def test_expired(self):
        a = self.prepared()
        self.age(a['actionId'])
        self.save('expired', status=self.status(a['actionId']))

    def test_superseded(self):
        a = self.prepared()
        self.prepared('p2', days=21)
        self.save('superseded', status=self.status(a['actionId']))

    def test_invalidated(self):
        a = self.prepared()
        self.assertEqual(self.correct('invoices', self.inv, dueDate='2026-10-27', reason='Terms corrected')[0], 200)
        self.assertEqual(self.confirm(a['actionId'])[0], 409)
        self.save('invalidated', status=self.status(a['actionId']))


if __name__ == '__main__':
    unittest.main(argv=['x'], verbosity=0)
