"""The AI Agent testing account: one access code (accessCodes.agent) gives a session for every role, each acting as the actor ai_agent.
The role of a request is the one its X-Nucleon-Role header names; the permissions are the role's own; the audit trail keeps the actor's
name and the role it acted as. Fictional data and a fictional code only."""
import json
import unittest
from urllib.request import Request, urlopen

from server import App, actor_words, trail
from test_agent import ISO_MESSAGE
from test_demo import DemoCase

CODE = 'agent-test-code'
WORRY = "I'm worried about this one: they sounded unsure on the phone."
EXPLAIN = 'Their event is next month; they pay on time.'


class AgentAccountCase(DemoCase):
    def setUp(self):
        super().setUp()
        self.start(access_codes={'agent': CODE})
        status, body, headers = self.call('/api/demo/login', {'accessCode': CODE})
        self.login = (status, body)
        self.agent_cookies = [c.split(';')[0] for c in headers.get_all('Set-Cookie')]
        self.cookies['agent'] = '; '.join(self.agent_cookies)

    def as_(self, role, path, body=None, key=None):
        return self.call(path, body, 'agent', key, headers={'X-Nucleon-Role': role})

    def tool(self, role, name, message, key, **args):
        return self.as_(role, '/api/tools/' + name, {'args': args, 'message': message}, key)

    def case_with_concern(self):
        r = self.wait_status(self.create(), ('awaiting_owner',))
        status, body, _ = self.tool('staff', 'raiseConcern', WORRY, 'agent-c1', requestId=r['id'], text=WORRY)
        self.assertEqual((status, body['ok']), (200, True), body)
        return r


class LoginTests(AgentAccountCase):
    def test_one_login_sets_a_session_for_every_role_and_reports_the_identity(self):
        status, body = self.login
        self.assertEqual(status, 200)
        self.assertEqual(sorted(c.split('=')[0] for c in self.agent_cookies), ['nucleon_operator', 'nucleon_owner', 'nucleon_staff'])
        self.assertEqual((body['identity'], body['held'], body['role']), ({'id': 'ai_agent', 'name': 'AI Agent', 'kind': 'agent'}, ['operator', 'owner', 'staff'], 'staff'))

    def test_the_session_names_the_agent_and_the_role_the_header_selects(self):
        probe = self.call('/api/session', role='agent')[1]   # no role chosen: several are held
        self.assertEqual((probe['authenticated'], probe['signedIn'], probe['identity']['name']), (False, ['operator', 'owner', 'staff'], 'AI Agent'))
        for role in ('staff', 'owner', 'operator'):
            s = self.as_(role, '/api/session')[1]
            self.assertEqual((s['authenticated'], s['role'], s['identity'], s['held']), (True, role, {'id': 'ai_agent', 'name': 'AI Agent', 'kind': 'agent'}, ['operator', 'owner', 'staff']))
        self.assertEqual(self.call('/api/session', role='staff')[1].get('identity', {}).get('kind', 'person'), 'person')   # a person's session is unchanged

    def test_the_console_reports_the_identity_and_the_selected_role(self):
        status, state, _ = self.as_('operator', '/api/demo/console')
        self.assertEqual((status, state['identity']['name'], state['role'], state['held']), (200, 'AI Agent', 'operator', ['operator', 'owner', 'staff']))
        self.assertEqual(self.as_('staff', '/api/demo/console')[0], 403)

    def test_permissions_are_the_selected_roles(self):
        self.assertEqual(self.as_('staff', '/api/setup/authority')[0], 403)   # owner-only
        self.assertEqual(self.as_('owner', '/api/setup/authority')[0], 200)
        status, body, _ = self.tool('staff', 'answerConcern', 'x', 'k', requestId='req_x', text='x', kind='explain')
        self.assertEqual(status, 403)   # an owner-only tool, as staff
        self.assertEqual(self.call('/api/session', role='agent')[0], 200)
        self.assertEqual(self.call('/api/requests', role='agent')[0], 400)   # several roles, none chosen

    def test_a_wrong_code_and_no_configured_code_give_no_session(self):
        self.assertEqual(self.call('/api/demo/login', {'accessCode': 'wrong-code'})[0], 403)
        self.apps[0][0].agent_code = None
        self.assertEqual(self.call('/api/demo/login', {'accessCode': CODE})[0], 403)

    def test_the_agent_code_is_validated_like_the_others(self):
        with self.assertRaises(Exception):
            App(self.tmp.name + '/s.sqlite3', 'mock', demo={'enabled': True, 'backupDir': self.tmp.name}, access_codes={'agent': 'short'})
        with self.assertRaises(Exception):
            App(self.tmp.name + '/v.sqlite3', 'mock', demo={'enabled': True, 'backupDir': self.tmp.name}, access_codes={'agent': 'same-code', 'owner': 'same-code'})


class AuditTests(AgentAccountCase):
    def test_events_decisions_and_lines_keep_the_id_the_name_and_the_role(self):
        r = self.case_with_concern()
        status, body, _ = self.tool('owner', 'answerConcern', EXPLAIN, 'agent-a1', requestId=r['id'], text=EXPLAIN, kind='explain')
        self.assertEqual((status, body['ok']), (200, True), body)
        history = self.as_('owner', '/api/requests/' + r['id'])[1]['history']
        by_kind = {e['kind']: e['data'] for e in history}
        self.assertEqual((by_kind['concern.raised']['byId'], by_kind['concern.raised']['actorName'], by_kind['concern.raised']['actorRole']), ('ai_agent', 'AI Agent', 'staff'))
        self.assertEqual((by_kind['concern.answered']['byId'], by_kind['concern.answered']['actorName'], by_kind['concern.answered']['actorRole']), ('ai_agent', 'AI Agent', 'owner'))
        view = self.as_('owner', '/api/requests/' + r['id'])[1]
        self.assertEqual(([x['actorRole'] for x in view['concerns']], [x['actorName'] for x in view['concernAnswers']]), (['staff'], ['AI Agent']))

    def test_a_decision_by_the_agent_is_attributed_with_its_effective_role(self):
        r = self.wait_status(self.create(), ('awaiting_owner',))
        a = self.as_('owner', '/api/requests/' + r['id'])[1]
        body = {'expectedRequestVersion': a['version'], 'analysisId': a['analysis']['id'], 'evidenceVersion': a['analysis']['snapshot']['evidenceVersion'],
                'outcome': 'decline', 'reason': 'Not this time.'}
        status, decided, _ = self.as_('owner', '/api/requests/' + r['id'] + '/decisions', body, 'agent-d1')
        self.assertEqual(status, 201, decided)
        d = self.as_('owner', '/api/requests/' + r['id'])[1]['decision']
        self.assertEqual((d['decidedBy'], d['actorName'], d['actorRole']), ('ai_agent', 'AI Agent', 'owner'))
        committed = next(e['data'] for e in self.as_('staff', '/api/requests/' + r['id'])[1]['history'] if e['kind'] == 'decision.committed')
        self.assertEqual((committed['actorName'], committed['actorRole']), ('AI Agent', 'owner'))

    def test_the_ordinary_demo_actors_keep_their_words(self):
        r = self.wait_status(self.create(), ('awaiting_owner',))
        self.assertEqual(self.call('/api/tools/raiseConcern', {'args': {'requestId': r['id'], 'text': WORRY}, 'message': WORRY}, 'staff', 'p1')[0], 200)
        data = next(e['data'] for e in self.call('/api/requests/' + r['id'], role='owner')[1]['history'] if e['kind'] == 'concern.raised')
        self.assertEqual((data['byId'], data['actorName'], data['actorRole']), ('staff_demo', None, 'staff'))
        self.assertEqual((actor_words({'role': 'owner'}), actor_words({'role': 'staff', 'name': 'AI Agent'}), trail({'role': 'staff'})),
                         ('owner', 'AI Agent (as staff)', {'actorName': None, 'actorRole': 'staff'}))

    def test_a_records_change_names_the_agent_and_its_role(self):
        status, body, _ = self.as_('owner', '/api/records/customers', {'name': 'Agent Test Pty'}, 'agent-cust')
        self.assertEqual(status, 200, body)
        self.assertEqual(body['record']['origin']['role'], 'owner')
        self.assertEqual((body['record']['origin']['actorName'], body['record']['origin']['actorRole']), ('AI Agent', 'owner'))


if __name__ == '__main__':
    unittest.main()


class DueDateProvenanceTests(AgentAccountCase):
    def test_a_follow_up_case_names_the_ai_agent_that_moved_the_due_date(self):
        req = Request(self.base + '/api/setup/authority', data=json.dumps({'staffMayApproveUpToDays': 60, 'maxOutstanding': '999999.00'}).encode(),
                      headers={'Cookie': self.cookies['agent'], 'X-Nucleon-Role': 'owner', 'Content-Type': 'application/json'}, method='PUT')
        with urlopen(req, timeout=10) as response:
            self.assertEqual(response.status, 200)
        r = self.wait_status(self.create(), ('awaiting_owner',))
        status, acted, _ = self.tool('staff', 'actWithinAuthority', '', 'agent-act', requestId=r['id'])
        self.assertEqual((status, acted.get('ok')), (200, True), acted)
        later = self.wait_status(self.create('Could we pay invoice DEMO-101 on 2026-12-01 instead?', key='intake-follow-up'), ('awaiting_owner',))
        view = self.as_('staff', '/api/requests/' + later['id'])[1]
        fact = next(f for f in view['analysis']['brief']['facts'] if f['key'] == 'currentEffectiveDueDate')
        self.assertEqual((fact['kind'], fact['source']['decidedBy'], fact['source']['actorName'], fact['source']['actorRole']), ('owner_decision_record', 'ai_agent', 'AI Agent', 'staff'))


class SharedRoleTests(AgentAccountCase):
    LAB = 'nucleonl_lab_role='

    def with_lab(self, role, path, body=None, header=None, follow=False):
        return self.call(path, body, None, None, headers={'Cookie': self.cookies['agent'] + '; ' + self.LAB + role, **({'X-Nucleon-Role': header} if header is not None else {}), **({'X-Nucleon-Follow-Role': '1'} if follow else {})})

    def test_the_default_role_is_the_one_in_the_shared_cookie(self):
        self.assertIsNone(self.call('/api/session', role='agent')[1]['selectedRole'])   # none chosen yet: the page defaults to staff
        for role in ('owner', 'staff'):
            self.assertEqual(self.with_lab(role, '/api/session', header='')[1]['selectedRole'], role)
        self.assertNotIn('selectedRole', self.call('/api/session', role='staff')[1])   # a person's session is unchanged
        self.assertEqual(self.with_lab('operator', '/api/session', header='')[1]['selectedRole'], None)   # the console is never the shared choice

    def test_switching_here_sets_the_cookie_under_the_given_path_and_a_stale_page_is_told_to_follow(self):
        status, body, headers = self.call('/api/session/role', {'role': 'owner', 'path': '/lab'}, 'agent')
        cookie = headers['Set-Cookie']
        self.assertEqual((status, body), (200, {'role': 'owner'}))
        self.assertTrue(cookie.startswith(self.LAB + 'owner') and 'Path=/lab' in cookie and 'HttpOnly' in cookie, cookie)
        self.assertEqual(self.call('/api/session/role', {'role': 'operator'}, 'agent')[0], 400)
        self.assertEqual(self.call('/api/session/role', {'role': 'owner', 'path': '/../x'}, 'agent')[0], 400)
        self.assertEqual(self.call('/api/session/role', {'role': 'owner'}, 'staff')[0], 400)   # a person has nothing to choose
        status, body, _ = self.with_lab('owner', '/api/requests', header='staff', follow=True)   # another tab switched to owner; this page still says staff
        self.assertEqual((status, body['error']), (409, 'ROLE_CHANGED'))
        self.assertEqual(self.with_lab('owner', '/api/requests', header='staff')[0], 200)   # a call that names its role without the page's mark is trusted
        self.assertEqual(self.with_lab('owner', '/api/requests', header='owner')[0], 200)


class OverviewTermsAndProvenanceTests(AgentAccountCase):
    """Repair G: the overview says the payment terms and who recorded each payment."""
    def test_terms_and_where_each_payment_came_from(self):
        from server import entered_text
        fixture = self.app.fixture()
        customer = next(c for c in fixture['customers'] if any(i['customerId'] == c['id'] for i in fixture['invoices']))
        status, record, _ = self.as_('staff', '/api/records/payments', {'customerId': customer['id'], 'receivedDate': '2026-10-12', 'amount': '10.00', 'reference': 'EFT G3'}, 'g3-pay')
        self.assertEqual(status, 200, record)
        status, body, _ = self.tool('staff', 'customerOverview', 'How is this customer doing?', 'g3-ov', customerId=customer['id'])
        self.assertEqual(status, 200, body)
        result = body['result']
        self.assertRegex(result['termsText'], r'^(Invoices are issued on \d+-day terms \(the median of due date minus issue date over \d+ recorded invoices?\)|No payment terms are recorded)$')
        [mine] = [p for p in result['payments'] if p['paymentReference'] == 'EFT G3']
        self.assertRegex(mine['enteredByText'], r'^Entered by AI Agent \(as staff\) on \w+ \d+ \w+ \d{4}$')
        self.assertEqual(entered_text({'setBy': {'kind': 'file', 'fileName': 'bank.csv', 'at': '2026-10-05T01:00:00+00:00'}}), 'From the import of bank.csv on Mon 5 Oct 2026')
        self.assertEqual(entered_text({'origin': {'kind': 'manual', 'role': 'owner', 'at': '2026-10-05T01:00:00+00:00'}}), 'Entered by owner on Mon 5 Oct 2026')

    def test_terms_are_the_median_of_due_minus_issue(self):
        from server import entered_text  # noqa: F401
        fixture = self.app.fixture()
        customer = fixture['customers'][0]
        for n, (issue, due) in enumerate((('2026-09-01', '2026-10-01'), ('2026-09-05', '2026-10-05'), ('2026-09-10', '2026-09-30'))):
            status, body, _ = self.as_('staff', '/api/records/invoices', {'customerId': customer['id'], 'reference': 'G2-%d' % n, 'issueDate': issue, 'total': '100.00', 'dueDate': due}, 'g2-%d' % n)
            self.assertEqual(status, 200, body)
        result = self.tool('staff', 'customerOverview', 'Which payment terms?', 'g2-ov', customerId=customer['id'])[1]['result']
        self.assertTrue(result['termsText'].startswith('Invoices are issued on '), result['termsText'])


class CustomerListTests(AgentAccountCase):
    def test_find_customers_all_lists_everyone_by_name(self):
        """'all' (or '*') returns the whole customer list by name, for "who are our customers"; the result points at the Customers page."""
        status, body, _ = self.tool('staff', 'findCustomers', 'Who are our customers?', 'fc-all', query='all')
        self.assertEqual(status, 200, body)
        r = body['result']
        self.assertTrue(r['listedAll'])
        names = [m['name'] for m in r['matches']]
        self.assertGreater(len(names), 1)
        self.assertEqual(names, sorted(names, key=str.lower))
        self.assertEqual(r['count'], len(names))   # the fixture has fewer than 25 customers
        self.assertEqual(r['shown'], len(names))
        self.assertIn('Customers page', r['nextStep'])
        self.assertTrue(all(m['customerId'] and m['code'] for m in r['matches']))
        status, body, _ = self.tool('owner', 'findCustomers', 'list customers', 'fc-star', query='*')
        self.assertEqual(body['result']['count'], r['count'])
        status, body, _ = self.tool('staff', 'findCustomers', 'Harbour', 'fc-name', query='Harbour')
        self.assertNotIn('listedAll', body['result'])   # a name search is unchanged
