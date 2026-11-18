"""Regenerates lab/tests/fixtures/decision_card/*.json: REAL results of assessDecision, resolveDecision and decisionStatus from the records' own delegation
test harness (the fictional demonstration data, business date Sat 24 Oct 2026) for the decision card in test_decision_card.py, one file per state.
Run from the repo root with the system python:   python3 lab/tests/make_decision_card_fixtures.py
Nothing here computes a result; the records tools do. The files are committed so the Lab's suite needs no records server for the renderer."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'prototype'))
os.chdir(ROOT / 'prototype')
from test_delegation import DelegationCase   # noqa: E402

OUT = ROOT / 'lab' / 'tests' / 'fixtures' / 'decision_card'


class Make(DelegationCase):
    def save(self, name, **parts):
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / (name + '.json')).write_text(json.dumps(parts, ensure_ascii=False, indent=1, sort_keys=True) + '\n')

    def status(self, case_id):
        return self.tool('decisionStatus', caseId=case_id)['result']

    def test_make(self):
        a = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        self.save('decided_extension', resolve=a, status=self.status(a['caseId']))
        self.save('assessed_extension', assess=self.tool('assessDecision', kind='extension', customerId=self.cust['bayview'], invoiceReference='DEMO-301', requestedDueDate='2026-11-10')['result'])
        self.save('decided_trial', resolve=self.resolved(**self.trial('northside', '800.00')))
        g = self.resolved(**self.trial('lakeside', '600.00'))
        self.save('gathering', resolve=g, status=self.status(g['caseId']))
        self.save('owner_review_trial', resolve=self.resolved(**self.trial('harbourline', '5000.00')))
        self.save('owner_review_extension', resolve=self.resolved(**self.extension('cityside', 'DEMO-410', days=14)))
        self.save('incomplete', resolve=self.resolved(**self.extension('riverside', 'DEMO-505', days=10)))
        self.pause()
        self.save('assessed_paused', assess=self.tool('assessDecision', kind='trial_credit', customerId=self.cust['northside'], orderAmount='800.00', termsDays=14)['result'])
        status, _ = self.send('POST', '/api/delegation/policy/resume', {'expectedVersion': 2})
        status, body = self.override(a['caseId'])
        self.save('overridden', status=self.status(a['caseId']))
        t = self.resolved(**self.trial('northside', '800.00'))
        self.override(t['caseId'])
        self.save('overridden_trial', status=self.status(t['caseId']))
        # Lakeside: what Staff saw in the bank account is a Staff-checked deposit, not a recorded payment; the customer's word alone never counts
        said = self.resolved(**self.trial('lakeside', '600.00'))
        items = [{'kind': 'deposit', 'basis': 'customer_statement', 'amount': '150.00', 'receivedDate': '2026-10-23', 'reference': 'DEP-LK-01'},
                 {'kind': 'business_identity', 'basis': 'document', 'registration': 'Registration 111 (fictional)', 'tradingName': 'Lakeside Kiosk (fictional)'}]
        status, body = self.submit(said['actionId'], items, key='ev-said')
        self.save('gathering_customer_said', resolve=body['case'], status=self.status(said['caseId']))
        status, body = self.submit(body['case']['actionId'], [{'kind': 'deposit', 'basis': 'bank', 'amount': '150.00', 'receivedDate': '2026-10-23', 'reference': 'DEP-LK-02'}],
                                   version=1, key='ev-bank')
        self.save('decided_staff_checked', resolve=body['case'], status=self.status(said['caseId']))

    def override(self, case_id):
        return self.feedback(case_id, {'verdict': 'disagree', 'reason': 'Revoke.', 'override': True})


if __name__ == '__main__':
    import unittest
    unittest.main(argv=['x', 'Make'])
