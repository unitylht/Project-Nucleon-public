"""Quick setup (11 Nov 2026): two optional extension limits beside the days after the current due date. One counts from the day the request was received
(how an Owner reads "30 days"), one from the invoice's original due date (so asking again and again cannot go past it). Fictional demonstration data, as of
2026-10-24: Bayview's DEMO-301 is due 2026-10-18; the demo policy allows 30 days after the current due date."""
import unittest

import delegation
import delegation_demo
from test_delegation import DelegationCase

AUD = {'currency': 'AUD', 'scale': 2}


def demo_with(**ext):
    return {**delegation_demo.DEMO_POLICY, 'extensions': {**delegation_demo.DEMO_POLICY['extensions'], **ext}}


class DayLimitTests(DelegationCase):
    def limits(self, **ext):
        self.change_policy(extensions={**delegation_demo.DEMO_POLICY['extensions'], **ext})

    def request_for(self, who, reference, date, received):
        with self.app.lock:
            doc, ev = self.app.fixture(), self.app.evidence()
            c = ev.customer(self.cust[who])
            invoice = next(i for i in doc['invoices'] if i.get('customerId') == c['id'] and i.get('reference') == reference)
            return self.app.dg_request('extension', ev, doc, c, invoice, {'requestedDueDate': date}, received=received)

    def test_from_request_limit_sends_a_later_date_to_the_owner(self):
        self.limits(maxDaysFromRequest=10)
        out = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))   # 23 days after the due date, 17 days from 24 Oct
        self.assertEqual(out['handling'], 'owner_review')
        self.assertIn('Days after the day the request was received: 17 days is over the limit of 10 days', ' '.join(out['reasons']))

    def test_from_request_limit_passes_inside(self):
        self.limits(maxDaysFromRequest=20)
        self.assertEqual(self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))['handling'], 'autonomous_approve')

    def test_total_lateness_limit_stops_repeated_extensions(self):
        self.limits(maxDaysPastOriginalDue=30)
        first = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-07', reasoning='Fictional: first ask.'))    # 20 days past 18 Oct
        second = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-27', reasoning='Fictional: asks again.'))  # 20 more, 40 past 18 Oct
        self.assertEqual((first['handling'], second['handling']), ('autonomous_approve', 'owner_review'))
        self.assertIn('Days after the original due date: 40 days is over the limit of 30 days', ' '.join(second['reasons']))
        self.assertEqual(self.due('bayview', 'DEMO-301'), '2026-11-07')

    def test_without_the_new_limits_nothing_changes(self):
        p = delegation.validate_policy(delegation_demo.DEMO_POLICY, AUD)
        self.assertIsNone(p['extensions']['maxDaysFromRequest'])
        self.assertIsNone(p['extensions']['maxDaysPastOriginalDue'])
        old = {**p, 'extensions': {k: v for k, v in p['extensions'].items() if k not in ('maxDaysFromRequest', 'maxDaysPastOriginalDue')}}
        self.assertEqual(delegation.policy_digest(p), delegation.policy_digest(old))
        self.assertNotEqual(delegation.policy_digest(p), delegation.policy_digest(delegation.validate_policy(demo_with(maxDaysFromRequest=14), AUD)))
        checks = delegation.risk_checks({**old, 'version': 1}, 'extension', {'exposure': 1, 'customerExposure': 1, 'extensionDays': 5, 'nothingElseOverdue': True}, AUD)
        self.assertFalse({'days_from_request', 'days_past_original_due'} & {c['key'] for c in checks})

    def test_no_original_due_date_is_unknown_never_approved(self):
        f = {'exposure': 1, 'customerExposure': 1, 'extensionDays': 5, 'daysFromRequest': 5, 'daysPastOriginalDue': None, 'nothingElseOverdue': True}
        p = delegation.validate_policy(demo_with(maxDaysPastOriginalDue=30), AUD)
        row = [c for c in delegation.risk_checks(p, 'extension', f, AUD) if c['key'] == 'days_past_original_due'][0]
        self.assertEqual(row['status'], 'unknown')
        self.assertFalse(delegation.would_approve(p, 'extension', f))

    def test_a_recheck_counts_from_the_day_the_request_was_received(self):
        req, _ = self.request_for('bayview', 'DEMO-301', '2026-11-10', received='2026-10-20')
        self.assertEqual((req['daysFromRequest'], req['daysPastOriginalDue']), (21, 23))
        req, _ = self.request_for('bayview', 'DEMO-301', '2026-11-10', received=None)
        self.assertEqual(req['daysFromRequest'], 17)

    def test_the_case_records_the_day_it_was_received(self):
        out = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        self.assertEqual(self.app.dg_case(out['caseId'])['receivedDate'], '2026-10-24')

    def test_out_of_range_is_a_field_error(self):
        for key, value in (('maxDaysFromRequest', 0), ('maxDaysPastOriginalDue', 366)):
            status, body = self.put_policy({**demo_with(**{key: value}), 'expectedVersion': self.policy()['version']})
            self.assertEqual((status, body['error'], body.get('field')), (400, 'INVALID_INPUT', 'extensions.' + key))


class OlderClientTests(DelegationCase):
    def test_a_save_that_leaves_the_new_limits_out_keeps_them(self):
        """A Control panel tab opened before the two limits existed sends four extension keys: the limits stay as they are (an explicit null still clears them)."""
        self.change_policy(extensions={**delegation_demo.DEMO_POLICY['extensions'], 'maxDaysFromRequest': 14, 'maxDaysPastOriginalDue': 30})
        status, out = self.put_policy({**delegation_demo.DEMO_POLICY, 'expectedVersion': self.policy()['version']})
        self.assertEqual(status, 200, out)
        self.assertEqual((out['extensions']['maxDaysFromRequest'], out['extensions']['maxDaysPastOriginalDue']), (14, 30))
        self.limits = None
        status, out = self.put_policy({**demo_with(maxDaysFromRequest=None, maxDaysPastOriginalDue=None), 'expectedVersion': self.policy()['version']})
        self.assertEqual((out['extensions']['maxDaysFromRequest'], out['extensions']['maxDaysPastOriginalDue']), (None, None))


if __name__ == '__main__':
    unittest.main()
