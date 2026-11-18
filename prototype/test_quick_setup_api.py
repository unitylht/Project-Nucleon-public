"""Quick setup endpoints (11 Nov 2026): GET api/delegation/quick-setup gives the figures the helper offers; POST api/delegation/quick-setup/preview runs
delegation.evaluate with an UNSAVED policy over every open invoice and writes nothing. Fictional demonstration data, as of 2026-10-24."""
import unittest
from datetime import date, timedelta

import delegation
from test_delegation import DelegationCase, APPROVE

AS_OF = date(2026, 10, 24)
OPEN = {'start': 'now', 'maxInvoice': '100000', 'maxCustomer': '100000', 'daysFromRequest': 365, 'daysPastOriginalDue': 365, 'allowOtherOverdue': True,
        'lateHistory': 'any', 'holdCustomers': [], 'agentDeclines': False}


class QuickSetupApi(DelegationCase):
    def preview(self, answers, days=14, role='owner'):
        return self.send('POST', '/api/delegation/quick-setup/preview', {'answers': answers, 'days': days}, role)

    def table_count(self, name):
        return self.app.db.execute('SELECT COUNT(*) FROM ' + name).fetchone()[0]

    def test_preview_counts_add_up_and_name_reasons(self):
        status, out = self.preview({**OPEN, 'daysPastOriginalDue': 1})   # 1 day in total blocks every invoice
        self.assertEqual(status, 200, out)
        self.assertGreater(out['total'], 0)
        self.assertEqual(out['counts']['agent'], 0)
        self.assertEqual(sum(out['counts'].values()), out['total'])
        self.assertEqual((out['reasons'][0]['key'], out['reasons'][0]['question']), ('days_past_original_due', 'daysPastOriginalDue'))
        self.assertTrue(out['summary']['decides'])

    def test_generous_answers_let_the_agent_decide_some(self):
        status, out = self.preview(OPEN)
        self.assertEqual(status, 200, out)
        self.assertGreater(out['counts']['agent'], 0, out)

    def test_preview_matches_a_real_request(self):
        out = self.preview(OPEN)[1]
        status, saved = self.put_policy({**out['policy'], 'expectedVersion': self.policy()['version']})
        self.assertEqual(status, 200, saved)
        ex = out['examples']['agent'][0]
        cid = next(i for i, c in self.cust.items() if self.app.evidence().customer(c)['name'] == ex['customer'])
        real = self.resolved(**self.extension(cid, ex['invoice'], date=(AS_OF + timedelta(days=14)).isoformat()))
        self.assertEqual(real['handling'], 'autonomous_approve', real.get('reasons'))

    def test_preview_writes_nothing(self):
        before = (self.counts(), self.policy()['version'], self.table_count('notices'))
        self.preview(OPEN)
        self.preview({**OPEN, 'maxInvoice': 'abc'})
        self.assertEqual(before, (self.counts(), self.policy()['version'], self.table_count('notices')))

    def test_a_bad_answer_names_the_question(self):
        status, body = self.preview({**OPEN, 'maxInvoice': 'abc'})
        self.assertEqual((status, body['field']), (400, 'maxInvoice'))
        self.assertIn(body['error'], ('INVALID_INPUT', 'INVALID_AMOUNT'))
        status, body = self.preview({**OPEN, 'daysPastOriginalDue': 0})
        self.assertEqual((status, body['field']), (400, 'daysPastOriginalDue'))

    def test_held_customers_are_counted_as_held(self):
        out = self.preview({**OPEN, 'holdCustomers': [self.cust['bayview']]})[1]
        self.assertGreaterEqual(out['counts']['held'], 1)
        self.assertIn('held_customer', [r['key'] for r in out['reasons']])

    def test_staff_are_refused(self):
        self.assertEqual(self.preview(OPEN, role='staff')[0], 403)
        self.assertEqual(self.call('/api/delegation/quick-setup', None, 'staff')[0], 403)

    def test_days_out_of_range(self):
        for days in (0, 400, '14'):
            status, body = self.preview(OPEN, days=days)
            self.assertEqual((status, body['error'], body['field']), (400, 'INVALID_INPUT', 'days'))

    def test_get_gives_answers_customers_and_amounts(self):
        status, out, _ = self.call('/api/delegation/quick-setup', None, 'owner')
        self.assertEqual(status, 200, out)
        self.assertEqual(out['answers'], delegation.quick_setup_answers(self.app.policy_current()))
        self.assertEqual({c['id'] for c in out['customers']}, set(self.cust.values()))
        self.assertGreater(out['openInvoices'], 0)
        self.assertTrue(out['amounts']['largest']['text'].startswith('AUD '))
        self.assertLessEqual(int(out['amounts']['median']['minorUnits']), int(out['amounts']['largest']['minorUnits']))


class QuickSetupFirstRun(DelegationCase):
    """A workspace whose Owner has saved no policy yet: the helper opens on its own defaults and the first preview works."""
    with_policy = False

    def test_first_run_starts_from_the_helpers_defaults(self):
        status, out, _ = self.call('/api/delegation/quick-setup', None, 'owner')
        self.assertEqual(status, 200, out)
        self.assertEqual(out['policy']['version'], 0)
        self.assertEqual(out['answers'], delegation.quick_setup_first_answers(out['amounts']))
        status, prev = self.send('POST', '/api/delegation/quick-setup/preview', {'answers': out['answers']}, 'owner')
        self.assertEqual(status, 200, prev)
        self.assertEqual(prev['policy']['mode'], 'delegated')


class QuickSetupEmpty(DelegationCase):
    """A workspace whose records hold no invoice: the preview is empty, not an error."""
    def setUp(self):
        super(DelegationCase, self).setUp()
        from test_controlled_actions import Tripwire
        self.start(Tripwire(), 'live', sample_data=False)
        self.call('/api/setup/workspace', {'mode': 'practice', 'withSample': False}, 'owner', 'ws')
        self.call('/api/setup/settings', {'currency': 'AUD', 'scale': 2, 'timezone': 'Australia/Sydney'}, 'owner', 'st')

    def test_no_open_invoices(self):
        status, out = self.send('POST', '/api/delegation/quick-setup/preview', {'answers': OPEN}, 'owner')
        self.assertEqual(status, 200, out)
        self.assertEqual((out['total'], out['counts'], out['reasons']), (0, {'agent': 0, 'owner': 0, 'held': 0}, []))
        self.assertIsNone(self.call('/api/delegation/quick-setup', None, 'owner')[1]['amounts'])


if __name__ == '__main__':
    unittest.main()
