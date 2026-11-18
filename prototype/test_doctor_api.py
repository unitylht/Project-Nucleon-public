"""The Doctor's endpoint (11 Nov 2026): GET api/delegation/doctor, Owner only, read only. Fictional demonstration data, as of 2026-10-24."""
import unittest

import delegation
import doctor
from test_delegation import DelegationCase, APPROVE


class DoctorApi(DelegationCase):
    def get(self, query='', role='owner'):
        status, body, _ = self.call('/api/delegation/doctor' + query, None, role)
        return status, body

    def table_counts(self):
        return {t: self.app.db.execute('SELECT COUNT(*) FROM ' + t).fetchone()[0]
                for t in ('requests', 'events', 'actions', 'decision_cases', 'delegation_policies', 'notices', 'case_events')}

    def three_to_the_owner(self):
        for i, (who, ref) in enumerate((('bayview', 'DEMO-301'), ('cityside', 'DEMO-410'), ('harbourline', 'DEMO-501'))):
            try:
                self.resolved(**self.extension(who, ref, date='2027-01-30', reasoning='Fictional: a long ask %d.' % i))
            except (AssertionError, KeyError, StopIteration):
                pass

    def test_owner_only(self):
        self.assertEqual(self.get(role='staff')[0], 403)
        self.assertEqual(self.get('?question=came', role='staff')[0], 403)

    def test_unknown_question_and_days(self):
        status, body = self.get('?question=nope')
        self.assertEqual((status, body['field']), (400, 'question'))
        status, body = self.get('?days=7')
        self.assertEqual((status, body['field']), (400, 'days'))

    def test_list_has_six_headlines(self):
        status, body = self.get()
        self.assertEqual(status, 200, body)
        self.assertEqual([q['question'] for q in body['questions']], [q for q, _ in doctor.QUESTIONS])
        self.assertTrue(all(q['headline'] for q in body['questions']))

    def test_came_answers_on_real_resolved_cases(self):
        self.three_to_the_owner()
        came = [c for c in self.app.dg_cases("dataset='live'") if doctor.came(c)]
        self.assertGreaterEqual(len(came), 1)
        status, out = self.get('?question=came&days=all')
        self.assertEqual(status, 200, out)
        self.assertTrue(out['headline'].startswith(str(len(came)) + ' of your '), out['headline'])
        self.assertFalse(out['enough'])
        policy = self.app.policy_current()
        for s in out['suggestions']:
            delegation.validate_policy(delegation.quick_setup_policy({**delegation.quick_setup_answers(policy), **s['answers']}, policy), {'currency': 'AUD', 'scale': 2})
        self.assertEqual(out['facts'][0], out['headline'])

    def test_doctor_writes_nothing(self):
        self.three_to_the_owner()
        before = self.table_counts()
        self.get()
        for q, _ in doctor.QUESTIONS:
            for days in ('30', '90', 'all'):
                self.assertEqual(self.get('?question=%s&days=%s' % (q, days))[0], 200, q)
        self.assertEqual(self.table_counts(), before)


class DoctorNoRecords(DelegationCase):
    def setUp(self):
        super(DelegationCase, self).setUp()
        from test_controlled_actions import Tripwire
        self.start(Tripwire(), 'live', sample_data=False)

    def test_no_records(self):
        status, body, _ = self.call('/api/delegation/doctor', None, 'owner')
        self.assertEqual((status, body.get('error')), (409, 'NO_RECORDS'), body)


if __name__ == '__main__':
    unittest.main()
