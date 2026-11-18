"""Slice S2b, the Owner pages' backend: the loop view's stage counts (pure and over HTTP), the page-use events (D11: validation, who may send, the per-session rate limit, the
summary), the read-only list of the evidence requests waiting for Staff, and the extra fields the Review page and the control panel read. Deterministic, on the fictional
delegation demonstration as of 2026-10-24; no model is ever asked. Every figure is a fictional POC value."""
import json
import unittest
from datetime import datetime, timedelta, timezone

import impact
import server
from test_decision_loop import LAKESIDE_ITEMS, LoopCase


def case(i, status, dataset='live', **more):
    return {'id': 'c' + str(i), 'dataset': dataset, 'status': status, 'kind': 'extension', 'decision': more.pop('decision', None), **more}


def decided(i, by='agent', **more):
    return case(i, 'decided', decision={'by': by, 'outcome': 'approve', **more.pop('d', {})}, **more)


# ---------------------------------------------------------------- 1. the loop view

class LoopStagePureTests(unittest.TestCase):
    def test_each_state_has_one_stage(self):
        self.assertEqual(impact.loop_stage(case(1, 'gathering_evidence')), 'evidence')
        self.assertEqual(impact.loop_stage(case(2, 'awaiting_owner')), 'evaluation')
        self.assertEqual(impact.loop_stage(case(3, 'on_hold')), 'evaluation')
        self.assertEqual(impact.loop_stage(decided(4)), 'decision')
        self.assertEqual(impact.loop_stage(decided(5, feedback=[{'verdict': 'agree'}])), 'feedback')
        self.assertEqual(impact.loop_stage(decided(6, feedback=[{'verdict': 'tacit_agree'}])), 'feedback')
        self.assertEqual(impact.loop_stage(decided(7, d={'overridden': True})), 'feedback')
        self.assertEqual(impact.loop_stage(decided(8, feedback=[{'verdict': 'agree'}], outcomeObserved={'outcome': 'on_time'})), 'outcome')
        self.assertEqual(impact.loop_stage(decided(9, by='owner', outcomeObserved={'outcome': 'open_not_due'})), 'outcome')
        self.assertIsNone(impact.loop_stage(case(10, 'closed')))
        self.assertEqual(impact.loop_stage(case(11, 'something_new'), has_evaluated=False), 'request')

    def test_counts_add_up_leave_out_closed_and_fictional_and_name_the_cases(self):
        cases = [case(1, 'gathering_evidence'), case(2, 'awaiting_owner'), case(3, 'on_hold'), decided(4), decided(5), decided(6, feedback=[{'verdict': 'agree'}]),
                 decided(7, outcomeObserved={'outcome': 'late_paid'}), case(8, 'closed'), decided(9, dataset='fictional_evaluation'), case(10, 'awaiting_owner', dataset='fictional_example')]
        out = impact.loop_counts(cases)
        self.assertEqual([s['stage'] for s in out['stages']], ['request', 'evidence', 'evaluation', 'decision', 'feedback', 'outcome'])
        self.assertEqual({s['stage']: s['count'] for s in out['stages']}, {'request': 0, 'evidence': 1, 'evaluation': 2, 'decision': 2, 'feedback': 1, 'outcome': 1})
        self.assertEqual((out['total'], out['closed'], out['dataset']), (8, 1, 'live'))
        self.assertEqual(sum(s['count'] for s in out['stages']), out['total'] - out['closed'])
        self.assertEqual(next(s for s in out['stages'] if s['stage'] == 'decision')['caseIds'], ['c4', 'c5'])

    def test_an_empty_list_is_all_zero_counts_not_an_error(self):
        out = impact.loop_counts([])
        self.assertEqual((out['total'], [s['count'] for s in out['stages']]), (0, [0] * 6))


class LoopRouteTests(LoopCase):
    def test_the_route_counts_the_live_cases_by_stage_for_the_owner_only(self):
        a = self.approved_extension()                                   # decided by the agent
        self.agree(a['caseId'])                                         # feedback
        self.resolved(**self.trial('lakeside', '600.00'))               # gathering evidence
        self.resolved(**self.trial('harbourline', '5000.00'))           # awaiting the Owner
        status, body, _ = self.call('/api/delegation/loop', None, 'owner')
        self.assertEqual(status, 200, body)
        got = {s['stage']: s['count'] for s in body['stages']}
        self.assertEqual((got['evidence'], got['evaluation'], got['feedback']), (1, 1, 1), got)
        self.assertEqual(body['total'], 3)
        self.assertEqual(self.call('/api/delegation/loop', None, 'staff')[0], 403)

    def test_the_fictional_decision_memory_is_never_counted(self):
        status, body, _ = self.call('/api/delegation/loop', None, 'owner')
        self.assertEqual((status, body['total']), (200, 0))   # the demonstration holds many fictional cases and no live one

    def test_a_service_session_is_refused(self):
        status, login, headers = self.call('/api/demo/login', {'accessCode': self.app.service_codes['owner'], 'role': 'owner'})
        self.assertEqual(status, 200, login)
        status, body, _ = self.call('/api/delegation/loop', None, None, None, {'Cookie': headers['Set-Cookie'].split(';')[0], 'X-Nucleon-Role': 'owner'})
        self.assertEqual((status, body['error']), (403, 'PERSON_REQUIRED'))


# ---------------------------------------------------------------- 2. page-use events (D11)

class UiEventTests(LoopCase):
    def post(self, events, role='owner', **kw):
        return self.call('/api/ui-events', events, role, None, {'Origin': self.base, **kw})

    def stored(self):
        return self.row('SELECT at, role, channel, page, kind, data FROM ui_events ORDER BY seq')

    def test_the_table_is_additive_and_a_data_table_a_reset_clears(self):
        self.assertIn('ui_events', server.DATA_TABLES)
        self.assertEqual([c[1] for c in self.row('PRAGMA table_info(ui_events)')], ['seq', 'at', 'role', 'channel', 'page', 'kind', 'data'])

    def test_a_batch_from_the_owner_and_from_staff_is_stored_with_the_role_and_channel(self):
        status, body, _ = self.post([{'page': 'review', 'kind': 'page_enter'}, {'page': 'review', 'kind': 'click', 'data': {'name': 'review-agree'}},
                                     {'page': 'review', 'kind': 'page_leave', 'data': {'ms': 5200}}])
        self.assertEqual((status, body), (200, {'accepted': 3, 'dropped': 0}))
        status, body, _ = self.post({'events': [{'page': 'home', 'kind': 'page_enter'}]}, 'staff')
        self.assertEqual((status, body['accepted']), (200, 1))
        rows = self.stored()
        self.assertEqual([(r[1], r[2], r[3], r[4]) for r in rows], [('owner', 'person', 'review', 'page_enter'), ('owner', 'person', 'review', 'click'), ('owner', 'person', 'review', 'page_leave'),
                                                                   ('staff', 'person', 'home', 'page_enter')])
        self.assertEqual(json.loads(rows[1][5]), {'name': 'review-agree'})
        self.assertTrue(all(r[0] for r in rows))

    def test_a_service_session_and_the_ai_agent_are_403_and_nothing_is_stored(self):
        status, _, headers = self.call('/api/demo/login', {'accessCode': self.app.service_codes['staff'], 'role': 'staff'})
        self.assertEqual(status, 200)
        status, body, _ = self.call('/api/ui-events', [{'page': 'home', 'kind': 'page_enter'}], None, None,
                                    {'Origin': self.base, 'Cookie': headers['Set-Cookie'].split(';')[0], 'X-Nucleon-Role': 'staff'})
        self.assertEqual((status, body['error']), (403, 'PERSON_REQUIRED'))
        self.app.agent_code = 'agent-code-for-tests'
        status, _, headers = self.call('/api/demo/login', {'accessCode': 'agent-code-for-tests'})
        self.assertEqual(status, 200)
        cookies = {c.split('=')[0]: c.split(';')[0] for c in headers.get_all('Set-Cookie')}
        status, body, _ = self.call('/api/ui-events', [{'page': 'home', 'kind': 'page_enter'}], None, None, {'Origin': self.base, 'Cookie': cookies['nucleon_staff'], 'X-Nucleon-Role': 'staff'})
        self.assertEqual((status, body['error']), (403, 'PERSON_REQUIRED'))
        self.assertEqual(self.call('/api/ui-events', [{'page': 'home', 'kind': 'page_enter'}])[0], 401)   # no session
        self.assertEqual(self.stored(), [])

    def test_a_kind_a_page_or_data_outside_the_rules_is_400_and_the_whole_batch_is_refused(self):
        good = {'page': 'home', 'kind': 'page_enter'}
        for bad in ({'page': 'home', 'kind': 'keystroke'}, {'page': 'home', 'kind': 'click', 'extra': 1}, {'page': 'Home Page', 'kind': 'click'}, {'page': '', 'kind': 'click'},
                    {'page': 'a' * 41, 'kind': 'click'}, {'kind': 'click'}, {'page': 'home'}, {'page': 'home', 'kind': 'click', 'data': 'text'},
                    {'page': 'home', 'kind': 'click', 'data': {'name': 'x' * 101}}, {'page': 'home', 'kind': 'click', 'data': {'nested': {'a': 1}}},
                    {'page': 'home', 'kind': 'click', 'data': {str(i): i for i in range(9)}}, {'page': 'home', 'kind': 'click', 'at': 'yesterday'}, 'a string'):
            status, body, _ = self.post([good, bad])
            self.assertEqual((status, body['error']), (400, 'INVALID_INPUT'), bad)
        for bad_body in ({'events': 'x'}, {'nope': []}):
            self.assertEqual(self.post(bad_body)[0], 400)
        self.assertEqual(self.stored(), [])

    def test_the_rate_limit_keeps_sixty_a_minute_per_session_and_drops_the_rest_silently(self):
        batch = [{'page': 'home', 'kind': 'click', 'data': {'name': 'n' + str(i)}} for i in range(50)]
        self.assertEqual(self.post(batch)[1], {'accepted': 50, 'dropped': 0})
        status, body, _ = self.post(batch)
        self.assertEqual((status, body), (200, {'accepted': 10, 'dropped': 40}))   # no error: the page cannot tell
        self.assertEqual(self.post(batch[:3])[1], {'accepted': 0, 'dropped': 3})
        self.assertEqual(len(self.stored()), 60)
        self.assertEqual(self.post([good for good in batch[:2]], 'staff')[1]['accepted'], 2)   # another session has its own minute

    def test_the_rate_limit_window_is_a_minute(self):
        self.post([{'page': 'home', 'kind': 'click'}] * 50)
        self.post([{'page': 'home', 'kind': 'click'}] * 10)
        self.assertEqual(self.post([{'page': 'home', 'kind': 'click'}])[1], {'accepted': 0, 'dropped': 1})
        for key in self.app.ui_seen:
            self.app.ui_seen[key] = [t - 61 for t in self.app.ui_seen[key]]
        self.assertEqual(self.post([{'page': 'home', 'kind': 'click'}])[1], {'accepted': 1, 'dropped': 0})

    def test_a_closing_page_names_its_role_in_the_address_because_a_beacon_cannot_set_a_header(self):
        both = {'Cookie': self.cookies['staff'] + '; ' + self.cookies['owner'], 'Origin': self.base}
        batch = [{'page': 'review', 'kind': 'page_leave', 'data': {'ms': 900}}]
        status, body, _ = self.call('/api/ui-events', batch, None, None, both)
        self.assertEqual((status, body['error']), (400, 'ROLE_REQUIRED'))   # two roles are signed in and none is named
        self.assertEqual(self.call('/api/ui-events?role=owner', batch, None, None, both)[1], {'accepted': 1, 'dropped': 0})
        self.assertEqual(self.call('/api/ui-events?role=nobody', batch, None, None, both)[0], 400)
        self.assertEqual([(r[1], r[2]) for r in self.stored()], [('owner', 'person')])

    def test_a_batch_is_read_up_to_fifty_events(self):
        self.assertEqual(self.post([{'page': 'home', 'kind': 'click'}] * 70)[1], {'accepted': 50, 'dropped': 20})

    def test_a_given_time_is_kept_only_when_it_is_recent_else_the_servers(self):
        now = datetime.now(timezone.utc)
        recent = (now - timedelta(minutes=5)).isoformat().replace('+00:00', 'Z')
        self.post([{'page': 'home', 'kind': 'page_enter', 'at': recent}, {'page': 'home', 'kind': 'page_enter', 'at': '2001-01-01T00:00:00Z'},
                   {'page': 'home', 'kind': 'page_enter', 'at': (now + timedelta(days=3)).isoformat()}])
        first, second, third = [datetime.fromisoformat(r[0]) for r in self.stored()]
        self.assertLess(abs((first - (now - timedelta(minutes=5))).total_seconds()), 1)
        self.assertLess(abs((second - now).total_seconds()), 10)
        self.assertLess(abs((third - now).total_seconds()), 10)



class UiEventResetTests(LoopCase):
    demo = True   # the demo console is on, so the operator can reset

    def test_a_demo_reset_clears_the_events_and_the_operator_cannot_send_any(self):
        send = lambda role: self.call('/api/ui-events', [{'page': 'home', 'kind': 'click'}], role, None, {'Origin': self.base})   # noqa: E731
        self.assertEqual(send('owner')[0], 200)
        self.assertEqual(send('operator')[0], 403)
        self.assertEqual(self.count('ui_events'), 1)
        self.assertEqual(self.console('reset', {})[0], 200)
        self.assertEqual(self.count('ui_events'), 0)


class UiSummaryPureTests(unittest.TestCase):
    def rows(self):
        def r(day, page, kind, **data):
            return {'at': '2026-10-' + day + 'T10:00:00+00:00', 'role': 'owner', 'page': page, 'kind': kind, 'data': data}
        return [r('24', 'review', 'page_enter'), r('24', 'review', 'page_leave', ms=10000), r('24', 'review', 'page_enter'), r('24', 'review', 'page_leave', ms=30000),
                r('25', 'review', 'page_enter'), r('25', 'review', 'page_leave', ms=20000), r('25', 'review', 'click', name='review-agree'), r('25', 'review', 'click', name='review-agree'),
                r('25', 'review', 'click', name='review-override'), r('25', 'home', 'page_enter'), r('25', 'review', 'decide_start'), r('25', 'review', 'decide_start'),
                r('25', 'review', 'decide_done', ms=4000), r('26', 'review', 'decide_done', ms=8000), r('26', 'dashboard', 'page_enter')]

    def test_counts_per_page_and_median_dwell(self):
        out = impact.ui_summary(self.rows())
        pages = {p['page']: p for p in out['pages']}
        self.assertEqual((pages['review']['enters'], pages['review']['leaves'], pages['review']['clicks']), (3, 3, 3))
        self.assertEqual((pages['review']['medianDwellSeconds'], pages['review']['dwellSamples']), (20, 3))
        self.assertEqual((pages['home']['enters'], pages['home']['medianDwellSeconds']), (1, None))   # no leave reported: unknown, not 0
        self.assertEqual([p['page'] for p in out['pages']], ['review', 'dashboard', 'home'])   # most entered first, then by name
        self.assertEqual(out['buttons'], [{'page': 'review', 'name': 'review-agree', 'count': 2}, {'page': 'review', 'name': 'review-override', 'count': 1}])
        self.assertEqual(out['decisions'], {'started': 2, 'done': 2, 'medianSeconds': 6, 'samples': 2})
        self.assertEqual(out['events'], 15)

    def test_the_window_is_by_day_and_an_even_count_takes_the_mean_of_the_middle_two(self):
        out = impact.ui_summary(self.rows(), {'from': '2026-10-25', 'to': '2026-10-25'})
        review = next(p for p in out['pages'] if p['page'] == 'review')
        self.assertEqual((review['enters'], review['medianDwellSeconds']), (1, 20))
        self.assertEqual(out['decisions']['medianSeconds'], 4)
        two = impact.ui_summary(self.rows()[:4])
        self.assertEqual(two['pages'][0]['medianDwellSeconds'], 20)   # (10 + 30) / 2

    def test_nothing_is_none_not_zero_and_a_bad_duration_is_ignored(self):
        out = impact.ui_summary([])
        self.assertEqual((out['pages'], out['events'], out['decisions']['medianSeconds']), ([], 0, None))
        odd = impact.ui_summary([{'at': '2026-10-24T00:00:00+00:00', 'role': 'owner', 'page': 'x', 'kind': 'page_leave', 'data': {'ms': -5}},
                                 {'at': '2026-10-24T00:00:00+00:00', 'role': 'owner', 'page': 'x', 'kind': 'page_leave', 'data': {'ms': True}},
                                 {'at': '2026-10-24T00:00:00+00:00', 'role': 'owner', 'page': 'x', 'kind': 'page_leave', 'data': {'ms': 'soon'}}])
        self.assertEqual((odd['pages'][0]['leaves'], odd['pages'][0]['medianDwellSeconds']), (3, None))


class UiSummaryRouteTests(LoopCase):
    def test_the_owner_reads_the_summary_of_what_was_sent_and_staff_cannot(self):
        send = lambda events, role='owner': self.call('/api/ui-events', events, role, None, {'Origin': self.base})   # noqa: E731
        send([{'page': 'review', 'kind': 'page_enter'}, {'page': 'review', 'kind': 'page_leave', 'data': {'ms': 12000}}, {'page': 'review', 'kind': 'click', 'data': {'name': 'review-agree'}}])
        send([{'page': 'home', 'kind': 'page_enter'}], 'staff')
        status, body, _ = self.call('/api/delegation/ui-summary', None, 'owner')
        self.assertEqual(status, 200, body)
        pages = {p['page']: p for p in body['pages']}
        self.assertEqual((pages['review']['enters'], pages['review']['medianDwellSeconds'], pages['home']['enters']), (1, 12, 1))
        self.assertEqual(body['buttons'], [{'page': 'review', 'name': 'review-agree', 'count': 1}])
        self.assertEqual(self.call('/api/delegation/ui-summary', None, 'staff')[0], 403)
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        self.assertEqual(self.call('/api/delegation/ui-summary?from=' + today + '&to=' + today, None, 'owner')[1]['events'], 4)
        self.assertEqual(self.call('/api/delegation/ui-summary?from=2001-01-01&to=2001-01-02', None, 'owner')[1]['events'], 0)
        for q in ('from=soon', 'to=2026-13-40', 'from=2026-10-25&to=2026-10-24'):
            self.assertEqual(self.call('/api/delegation/ui-summary?' + q, None, 'owner')[0], 400, q)


# ---------------------------------------------------------------- 3. the evidence requests waiting for Staff

class OpenEvidenceActionsTests(LoopCase):
    def open_list(self, role='staff', **kw):
        return self.call('/api/actions?kind=evidence&status=open', None, role, None, kw.get('headers'))

    def test_the_list_is_empty_then_names_the_open_request_with_customer_ask_and_link(self):
        status, body, _ = self.open_list()
        self.assertEqual((status, body), (200, {'kind': 'evidence', 'status': 'open', 'actions': []}))
        out = self.resolved(**self.trial('lakeside', '600.00'))
        for role in ('staff', 'owner'):
            status, body, _ = self.open_list(role)
            self.assertEqual(status, 200, body)
            self.assertEqual(len(body['actions']), 1)
            a = body['actions'][0]
            self.assertEqual((a['id'], a['caseId'], a['link'], a['status'], a['kind']), (out['actionId'], out['caseId'], '#/actions/' + out['actionId'], 'open', 'evidence'))
            self.assertIn('Lakeside', a['customer']['name'])
            self.assertTrue(a['createdAt'] and a['expiresAt'] and a['asks'])
            self.assertEqual([n['kind'] for n in a['needs']], ['deposit', 'business_identity'])
        self.assertNotIn('ownerReason', json.dumps(body))

    def test_a_service_session_may_read_it_and_an_unsigned_call_is_401(self):
        self.resolved(**self.trial('lakeside', '600.00'))
        status, _, headers = self.call('/api/demo/login', {'accessCode': self.app.service_codes['staff'], 'role': 'staff'})
        self.assertEqual(status, 200)
        status, body, _ = self.call('/api/actions?kind=evidence&status=open', None, None, None, {'Cookie': headers['Set-Cookie'].split(';')[0], 'X-Nucleon-Role': 'staff'})
        self.assertEqual((status, len(body['actions'])), (200, 1))
        self.assertEqual(self.call('/api/actions?kind=evidence&status=open')[0], 401)

    def test_it_is_read_only_and_other_queries_are_400(self):
        for q in ('', '?kind=evidence', '?status=open', '?kind=extension&status=open', '?kind=evidence&status=confirmed', '?kind=evidence&status=all'):
            self.assertEqual(self.call('/api/actions' + q, None, 'staff')[0], 400, q)
        self.assertEqual(self.call('/api/actions?kind=evidence&status=open', {}, 'staff', 'k1', {'Origin': self.base})[0], 404)   # no write on the list

    def test_an_answered_expired_or_replaced_request_is_not_listed(self):
        a = self.resolved(**self.trial('lakeside', '600.00'))
        b = self.resolved(**self.trial('northside', '800.00', terms=14))   # decided by the agent: nothing to ask
        self.assertEqual(len(self.open_list()[1]['actions']), 1)
        # expired: past its time, without anyone confirming it
        row = self.row('SELECT data FROM actions WHERE id=?', a['actionId'])[0][0]
        data = json.loads(row)
        data['expiresAt'] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        with self.app.lock, self.app.db:
            self.app.db.execute('UPDATE actions SET data=? WHERE id=?', (json.dumps(data), a['actionId']))
        self.assertEqual(self.open_list()[1]['actions'], [])
        self.assertTrue(b['status'] in ('decided', 'awaiting_owner'))

    def test_once_staff_answer_it_the_request_leaves_the_list(self):
        a = self.resolved(**self.trial('lakeside', '600.00'))
        status, body = self.submit(a['actionId'], LAKESIDE_ITEMS)
        self.assertEqual(status, 200, body)
        self.assertEqual(self.open_list()[1]['actions'], [])


# ---------------------------------------------------------------- 4. what the Review page and the control panel read

class OwnerPageFieldsTests(LoopCase):
    def test_a_case_row_carries_the_one_line_why_and_a_comparables_summary_and_the_track_record_wording(self):
        out = self.resolved(**self.trial('harbourline', '5000.00'))
        row = next(c for c in self.call('/api/delegation/cases', None, 'owner')[1]['cases'] if c['caseId'] == out['caseId'])
        self.assertTrue(isinstance(row['why'], str) and row['why'])
        c = row['comparables']
        self.assertEqual(set(c), {'n', 'approved', 'declined', 'sameCustomer'})
        self.assertEqual(c['n'], c['approved'] + c['declined'])
        self.assertTrue(set(row['reliability']) >= {'sources', 'gatedOn', 'sentence'})
        self.assertNotIn('ownerReason', json.dumps(c))

    def test_the_stats_carry_the_current_track_record_gate_counts_for_both_kinds(self):
        body = self.call('/api/delegation/stats', None, 'owner')[1]
        self.assertEqual(set(body['trackRecord']), {'extension', 'trial_credit'})
        for kind, tr in body['trackRecord'].items():
            self.assertEqual(tr['sources'], 'both')
            g = tr['gate']
            self.assertEqual(set(g), {'sources', 'gatedOn', 'fictional', 'live', 'pooled', 'needed', 'shortBy'}, kind)
            self.assertEqual(g['live']['cases'], 0)
            self.assertEqual(g['pooled']['cases'], g['fictional']['cases'] + g['live']['cases'])
        self.assertEqual(self.call('/api/delegation/stats', None, 'staff')[0], 403)

    def test_a_tacit_agreement_records_its_days_and_a_row_says_what_an_override_does_not_undo(self):
        out = self.approved_extension()
        self.change_policy(feedback={'tacitAgreeAfterDays': 3})
        with self.app.lock, self.app.db:
            data = json.loads(self.app.db.execute('SELECT data FROM decision_cases WHERE id=?', (out['caseId'],)).fetchone()[0])
            data['decision']['at'] = '2026-10-01T09:00:00+00:00'
            self.app.db.execute('UPDATE decision_cases SET data=? WHERE id=?', (json.dumps(data), out['caseId']))
        row = next(c for c in self.call('/api/delegation/cases', None, 'owner')[1]['cases'] if c['caseId'] == out['caseId'])   # reading the list runs the sweep
        self.assertEqual([(f['verdict'], f['afterDays']) for f in row['feedback']], [('tacit_agree', 3)])
        self.assertIn('Staff must follow up', row['overrideEffects'])
        self.assertIsNone(row['externalEffects'])   # nothing overridden yet

    def test_a_policy_saved_with_the_two_keys_the_control_panel_sends_keeps_them(self):
        policy = self.policy()
        body = {**{k: policy[k] for k in ('mode', 'limits', 'extensions', 'newCustomers', 'evidence', 'restrictions')}, 'trackRecord': {**policy['trackRecord'], 'sources': 'live'},
                'feedback': {'tacitAgreeAfterDays': 7}, 'expectedVersion': policy['version'], 'note': None}
        status, out = self.put_policy(body)
        self.assertEqual(status, 200, out)
        now = self.policy()
        self.assertEqual((now['trackRecord']['sources'], now['feedback']['tacitAgreeAfterDays']), ('live', 7))
        again = self.put_policy({**body, 'expectedVersion': now['version'], 'feedback': {'tacitAgreeAfterDays': None}})
        self.assertEqual(again[0], 200, again)
        self.assertIsNone(self.policy()['feedback']['tacitAgreeAfterDays'])


if __name__ == '__main__':
    unittest.main()
