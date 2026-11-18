"""Adaptive Decision Authority (docs/ADAPTIVE-DECISION-AUTHORITY.md): the Owner's versioned delegation policy, the assistant's recommend-and-explain tools
(assessDecision, resolveDecision, decisionStatus), the evidence page for Staff, the Owner's feedback and override, and the pure rules in delegation.py.
Deterministic: no model is ever asked (a tripwire adapter counts calls). The scenarios are the fictional demonstration data (delegation_demo.py), as of
2026-10-24. Every figure is a fictional POC value, not a real threshold or a measured result."""
import hashlib
import json
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import delegation
import delegation_demo
import research
import coordinator
import server
from records import RecordsError, new_opening
from test_controlled_actions import Tripwire
from test_records import RecordsCase

AS_OF = date(2026, 10, 24)
MEMORY = json.loads((Path(__file__).parent / 'samples' / 'decision_memory_fictional.json').read_text())
SETTINGS = {'currency': 'AUD', 'scale': 2, 'timezone': 'Australia/Sydney', 'businessName': None}
TEMPLATE = {'currency': 'AUD', 'scale': 2}
TOOLS = ('assessDecision', 'resolveDecision', 'decisionStatus', 'prepareRequest', 'actionStatus')
APPROVE = {'recommendation': 'approve', 'reasoning': 'Fictional: a reliable customer, an ordinary request.'}


class DelegationCase(RecordsCase):
    """The fictional delegation demonstration (six customers, the decision memory), with the demo policy as version 1 unless with_policy is False. The Owner has
    turned the delegation tools on."""
    with_policy = True

    def setUp(self):
        super().setUp()
        self.model = Tripwire()
        self.start(self.model, 'live', sample_data=False)
        self.ids = delegation_demo.seed(self.app, with_policy=self.with_policy)
        self.cust, self.inv = self.ids['customers'], self.ids['invoices']
        for name in TOOLS:
            self.assertEqual(self.call('/api/agent-tools', {'tool': name, 'enabled': True}, 'owner', 'on-' + name)[0], 200)

    # ---- helpers

    def tool(self, name, role='staff', key=None, **args):
        key = key or self.key_of(name, args)
        status, body, _ = self.call('/api/tools/' + name, {'args': args}, role, key)
        self.assertEqual(status, 200, body)
        return body

    @staticmethod
    def key_of(name, args):
        """The Idempotency-Key a call gets when the test names none: the same arguments, the same key (a retry)."""
        return 'k-' + name + '-' + hashlib.sha1(json.dumps(args, sort_keys=True).encode()).hexdigest()[:20]

    def resolved(self, role='staff', key=None, **args):
        body = self.tool('resolveDecision', role, key, **args)
        self.assertTrue(body['ok'], body)
        return body['result']

    def extension(self, who, reference, days=None, date=None, **more):
        args = {'kind': 'extension', 'customerId': self.cust[who], 'invoiceReference': reference, **APPROVE, **more}
        args.update({'days': days} if days else {'requestedDueDate': date})
        return args

    def trial(self, who, order, terms=14, **more):
        return {'kind': 'trial_credit', 'customerId': self.cust[who], 'orderAmount': order, 'termsDays': terms, **APPROVE, **more}

    def csrf(self, role='staff', cookie=None, extra=None):
        status, body, _ = self.call('/api/session', None, None if cookie else role, None, {**({'Cookie': cookie} if cookie else {}), **(extra or {})})
        self.assertEqual((status, body.get('authenticated')), (200, True), body)
        return body['csrf']

    def send(self, method, path, body, role='owner', key=None, origin=True, csrf=True, cookie=None, headers=None):
        """A write as a Nucleon page sends it: JSON, the page's Origin, the session's csrf token (csrf: True its own, a string to send that, False none)."""
        headers = {**({'Origin': self.base} if origin is True else {'Origin': origin} if origin else {}), 'Content-Type': 'application/json', **(headers or {})}
        headers['Cookie'] = cookie or self.cookies[role]
        if csrf is True:
            csrf = self.csrf(role, cookie, {k: v for k, v in headers.items() if k == 'X-Nucleon-Role'})
        if csrf:
            headers['X-Nucleon-CSRF'] = csrf
        if key:
            headers['Idempotency-Key'] = key
        req = Request(self.base + path, data=json.dumps(body).encode(), headers=headers, method=method)
        try:
            response = urlopen(req, timeout=10)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.loads(response.read())

    def put_policy(self, body, **kw):
        return self.send('PUT', '/api/delegation/policy', body, **kw)

    def policy(self, role='owner'):
        return self.call('/api/delegation/policy', None, role)[1]

    def change_policy(self, version=None, **sections):
        """Save a new policy version made from the demo policy with these sections changed; the new policy."""
        current = self.policy()
        body = {**delegation_demo.DEMO_POLICY, **sections, 'expectedVersion': current['version'] if version is None else version}
        status, out = self.put_policy(body)
        self.assertEqual(status, 200, out)
        return out

    def pause(self):
        status, out = self.send('POST', '/api/delegation/policy/pause', {'expectedVersion': self.policy()['version']})
        self.assertEqual(status, 200, out)
        return out

    def case(self, case_id, role='owner'):
        status, body, _ = self.call('/api/decision-cases/' + case_id, None, role)
        self.assertEqual(status, 200, body)
        return body

    def submit(self, action_id, items, version=1, key='ev-1', **kw):
        return self.send('POST', '/api/actions/' + action_id + '/evidence', {'version': version, 'items': items}, role=kw.pop('role', 'staff'), key=key, **kw)

    def feedback(self, case_id, body, **kw):
        """The Owner's feedback as the page sends it: naming the case version the Owner saw (the current one unless the body names another)."""
        if 'version' not in body:
            body = {**body, 'version': self.case(case_id)['version']}
        return self.send('POST', '/api/decision-cases/' + case_id + '/feedback', body, **kw)

    ORIGIN = {'kind': 'manual', 'by': 'test', 'role': 'staff', 'actorName': None, 'actorRole': 'staff', 'at': '2026-10-20T00:00:00+00:00'}

    def records(self, change):
        """Change the records the way a Staff entry does (one document write under the lock); what change(doc) returns."""
        with self.app.lock, self.app.db:
            doc = self.app.fixture()
            out = change(doc)
            self.app.save_doc(doc)
            return out

    def add_customer(self, name):
        return self.records(lambda doc: delegation_demo.new_customer(doc, {'name': name + ' (fictional)'}, 'customer_t_' + name.lower().replace(' ', '_'), self.ORIGIN))['id']

    def add_invoice(self, customer, reference, total, due, issue='2026-10-14', owed=None):
        body = {'customerId': customer, 'reference': reference, 'issueDate': issue, 'total': total, 'dueDate': due, **({'stillOwed': owed, 'stillOwedAsOf': '2026-10-24'} if owed else {})}
        return self.records(lambda doc: delegation_demo.new_invoice(doc, body, SETTINGS, AS_OF, 'invoice_t_' + reference, self.ORIGIN))['id']

    def add_receipt(self, customer, amount, reference, on='2026-10-23'):
        body = {'customerId': customer, 'receivedDate': on, 'amount': amount, 'reference': reference}
        return self.records(lambda doc: delegation_demo.new_payment(doc, body, SETTINGS, AS_OF, 'payment_t_' + reference, self.ORIGIN))['id']

    def add_history(self, customer, key, amounts=('400.00', '400.00')):
        """Two earlier invoices, each paid three days before it fell due: an established, punctual customer."""
        for n, amount in enumerate(amounts):
            invoice = self.add_invoice(customer, 'H-' + key + str(n), amount, '2026-0%d-16' % (3 + n), issue='2026-0%d-02' % (3 + n))
            payment = self.add_receipt(customer, amount, 'EFT-' + key + str(n), '2026-0%d-13' % (3 + n))
            self.records(lambda doc: delegation_demo.allocate(doc, {'paymentId': payment, 'allocations': [{'invoiceId': invoice, 'amount': amount}]}, SETTINGS,
                                                              lambda kind: kind + '_t_' + key + str(n), self.ORIGIN))

    def add_opening(self, customer, amount):
        self.records(lambda doc: new_opening(doc, {'customerId': customer, 'asOf': '2026-09-01', 'amount': amount, 'credits': 'none', 'sourceLabel': 'Fictional test'},
                                                             SETTINGS, AS_OF, 'opening_t_' + customer, self.ORIGIN))

    def add_identity(self, customer, basis='document'):
        """A business identity Staff confirmed earlier (a fact row, as submit_evidence writes it)."""
        with self.app.lock, self.app.db:
            self.app.db.execute('INSERT INTO confirmed_facts (id, customer_id, kind, created_at, data) VALUES (?,?,?,?,?)',
                                ('fact_t_' + customer, customer, 'business_identity', '2026-10-20T09:00:00+00:00',
                                 json.dumps({'values': {'registration': 'R-T', 'tradingName': 'T (fictional)', **({'basis': basis} if basis else {})},
                                             'provenance': {'role': 'staff', 'actorId': 'staff_demo', 'channel': 'person', 'actionId': None, 'caseId': None, 'at': '2026-10-20T09:00:00+00:00'}})))

    def ledger_of(self, customer):
        with self.app.lock:
            return self.app.dg_ledger(self.app.fixture(), self.app.evidence(), customer)[0]

    def request_of(self, request_id, role='staff'):
        status, body, _ = self.call('/api/requests/' + request_id, None, role)
        self.assertEqual(status, 200, body)
        return body

    def due(self, who, reference):
        with self.app.lock:
            ev = self.app.evidence()
            return ev.current_due(next(i for i in ev.invoices if i['reference'] == reference))

    def row(self, sql, *args):
        with self.app.lock:
            return self.app.db.execute(sql, args).fetchall()

    def history_kinds(self, request_id):
        with self.app.lock:
            return [e['kind'] for e in self.app.history(request_id)]

    def counts(self):
        return {t: self.count(t) for t in ('requests', 'events', 'actions', 'decision_cases', 'confirmed_facts', 'delegation_policies')}

    def agent_cookies(self):
        self.app.agent_code = 'agent-code-for-tests'
        status, _, headers = self.call('/api/demo/login', {'accessCode': 'agent-code-for-tests'})
        self.assertEqual(status, 200)
        return {c.split('=')[0]: c.split(';')[0] for c in headers.get_all('Set-Cookie')}

    def service_cookie(self, role):
        status, body, headers = self.call('/api/demo/login', {'accessCode': self.app.service_codes[role], 'role': role})
        self.assertEqual(status, 200, body)
        return headers['Set-Cookie'].split(';')[0]


# ---------------------------------------------------------------- one request per Staff message (the assistant's service session)

class OneRequestPerMessageTests(DelegationCase):
    """Hoang, 6 Nov 2026: given two requests and told to handle the extension first, the assistant sent both, 8 seconds apart. The page cannot see the
    conversation, so the backstop is in the records: a service session (the Lab's, which the assistant calls through) opens one new case per
    ONE_AT_A_TIME_SECONDS for another customer; the second is refused with what to tell Staff, and nothing opens. People are never refused."""
    def via_service(self, cookie, key, **args):
        status, body, _ = self.call('/api/tools/resolveDecision', {'args': args}, None, key, {'Cookie': cookie, 'X-Nucleon-Role': 'staff'})
        self.assertEqual(status, 200, body)
        return body

    def test_a_second_customer_right_after_the_first_is_refused_and_nothing_opens_until_the_window_passes(self):
        cookie = self.service_cookie('staff')
        first = self.via_service(cookie, 'svc-1', **self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        self.assertTrue(first['ok'], first)
        before = self.counts()
        second = self.via_service(cookie, 'svc-2', **self.trial('lakeside', '600.00'))
        self.assertFalse(second['ok'], second)
        self.assertEqual(second['error'], 'ONE_AT_A_TIME')
        self.assertIn('one request per Staff message', second['message'])
        self.assertIn('Lakeside', second['message'])
        self.assertIn('Bayview', second['message'])
        self.assertEqual(self.counts(), before)   # nothing opened, nothing stored
        self.assertEqual(self.row("SELECT COUNT(*) FROM decision_cases WHERE dataset='live'")[0][0], 1)
        again = self.via_service(cookie, 'svc-3', **self.extension('bayview', 'DEMO-301', date='2026-11-10'))   # the same customer: not this rule's business
        self.assertTrue(again['ok'], again)
        person = self.resolved(**self.trial('lakeside', '600.00'))   # a person's session is never refused
        self.assertEqual(person['kind'], 'trial_credit')
        for opened in self.app.recent_opens.values():   # the window passes
            opened['at'] -= server.ONE_AT_A_TIME_SECONDS
        later = self.via_service(cookie, 'svc-4', **self.trial('harbourline', '5000.00'))
        self.assertTrue(later['ok'], later)


# ---------------------------------------------------------------- information Staff add unasked

class UnaskedEvidenceTests(DelegationCase):
    """Hoang's round, 6 Nov 2026: Staff could only give information when the evaluation asked for it. Now a trial-credit case the Owner has takes a deposit or
    business identity Staff offer: an evidence action on the same form and path, after which the case is evaluated again."""
    def test_staff_add_a_deposit_to_a_case_the_owner_has_and_it_is_evaluated_again(self):
        hl = self.resolved(**self.trial('harbourline', '5000.00'))
        self.assertEqual(hl['status'], 'awaiting_owner')
        self.assertEqual(hl['addEvidence'], {'kinds': ['Deposit', 'Business identity', 'Trade reference']})   # what the evaluation found missing
        self.assertNotIn('addEvidence', self.case(hl['caseId'], 'owner'))   # the Owner's view does not carry Staff's button
        self.assertEqual(self.send('POST', '/api/decision-cases/' + hl['caseId'] + '/evidence-request', {}, role='owner')[0], 403)
        status, out = self.send('POST', '/api/decision-cases/' + hl['caseId'] + '/evidence-request', {}, role='staff')
        self.assertEqual(status, 200, out)
        self.assertEqual((out['link'], out['needs']), ('#/actions/' + out['actionId'], ['Deposit', 'Business identity', 'Trade reference']))
        again = self.send('POST', '/api/decision-cases/' + hl['caseId'] + '/evidence-request', {}, role='staff')[1]
        self.assertEqual((again['actionId'], again.get('replayed')), (out['actionId'], True))   # one open action per case
        status, page, _ = self.call('/api/actions/' + out['actionId'], None, 'staff')
        self.assertEqual((status, page['kind'], [n['kind'] for n in page['needs']]), (200, 'evidence', ['deposit', 'business_identity', 'trade_reference']))
        version = self.case(hl['caseId'])['version']
        status, body = self.submit(out['actionId'], [{'kind': 'deposit', 'amount': '1500.00', 'receivedDate': '2026-10-20', 'reference': 'HL-DEP', 'basis': 'bank'}], key='ev-unasked')
        self.assertEqual(status, 200, body)
        c = self.case(hl['caseId'])
        self.assertIn(c['status'], ('awaiting_owner', 'on_hold', 'decided'))   # evaluated again on the current policy
        self.assertGreater(c['version'], version)   # the Owner's page says it changed
        kinds = [(e['kind'], e['actor']) for e in self.call('/api/decision-cases/' + hl['caseId'] + '/events', None, 'owner')[1]['events']]
        self.assertIn(('evidence_requested', 'staff'), kinds)
        self.assertIn(('evidence_submitted', 'staff'), kinds)
        self.assertEqual([x['kind'] for x in self.app.dg_case(hl['caseId'])['evidenceItems']], ['deposit'])   # kept with the case
        self.assertIn('Business identity', self.send('POST', '/api/decision-cases/' + hl['caseId'] + '/evidence-request', {}, role='staff')[1].get('needs'))   # a new action for what is still open

    def test_nothing_to_add_to_an_extension_a_decided_case_or_one_gathering_evidence(self):
        ext = self.resolved(**self.extension('cityside', 'DEMO-410', days=14))
        self.assertIsNone(ext.get('addEvidence'))
        status, out = self.send('POST', '/api/decision-cases/' + ext['caseId'] + '/evidence-request', {}, role='staff')
        self.assertEqual((status, out['error']), (409, 'NOTHING_TO_ADD'))
        lake = self.resolved(**self.trial('lakeside', '600.00'))   # gathering evidence: that request is the way
        self.assertEqual(lake['status'], 'gathering_evidence')
        self.assertIsNone(lake.get('addEvidence'))
        self.assertEqual(self.send('POST', '/api/decision-cases/' + lake['caseId'] + '/evidence-request', {}, role='staff')[0], 409)


# ---------------------------------------------------------------- the scenarios

class ScenarioTests(DelegationCase):
    def test_1_an_established_low_risk_extension_is_approved_by_the_agent_and_takes_effect(self):
        self.assertEqual(self.due('bayview', 'DEMO-301'), '2026-10-18')
        before = self.counts()
        out = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        self.assertEqual((out['status'], out['handling'], out['kind']), ('decided', 'autonomous_approve', 'extension'))
        facts = out['keyFacts']
        self.assertEqual((facts['originalDueDate'], facts['currentDueDate'], facts['asOfDate'], facts['requestedDueDate'], facts['extensionDays'], facts['daysOverdueAsOf']),
                         ('2026-10-18', '2026-10-18', '2026-10-24', '2026-11-10', 23, 6))
        self.assertEqual((facts['amountOwed']['text'], facts['amountMark']), ('AUD 480.00', 'stated'))
        self.assertEqual(out['communication'], {'sent': False, 'note': 'Nucleon sent nothing to the customer. Staff informs the customer.'})
        self.assertEqual(out['authority']['version'], 1)
        self.assertIn('Approved within the Owner\'s delegation policy (policy version 1)', out['statusText'])
        self.assertEqual(self.due('bayview', 'DEMO-301'), '2026-11-10')   # the effective due date moved, by the existing evidence code
        r = self.request_of(out['requestId'])
        d = r['decision']
        self.assertEqual((r['status'], d['outcome'], d['approvedDueDate'], d['decisionSource'], d['decidedBy']), ('completed', 'approve', '2026-11-10', 'delegated_policy', 'nucleon_agent'))
        self.assertEqual((d['decidedByKind'], d['requestedBy']), ('agent', {'actorId': 'staff_demo', 'role': 'staff', 'channel': 'person'}))
        self.assertNotIn('actorRole', d)   # nothing marks it a Staff approval
        self.assertEqual(server.decision_view(d, 'staff')['decisionSource'], 'delegated_policy')
        self.assertEqual(server.decider_words(d), "the assistant, within the owner's delegation policy")
        self.assertEqual((d['authority']['source'], d['authority']['policyVersion'], d['delegationCaseId']), ('owner_delegation_policy', 1, out['caseId']))
        self.assertEqual(d['aiRecommendation']['recommendation'], 'approve')
        self.assertEqual(r['intake']['channel'], 'delegated_agent')
        self.assertIn('decision.committed', self.history_kinds(r['id']))
        self.assertEqual(r['responseDraft']['deliveryStatus'], 'not_sent')
        shown = self.call('/api/requests', None, 'owner')[1]
        row = next(x for x in shown if x['id'] == r['id'])
        self.assertEqual((row['decision']['decisionSource'], row['decision']['authority']['policyVersion'], row['delegationCaseId']), ('delegated_policy', 1, out['caseId']))
        case = self.case(out['caseId'])
        self.assertEqual((case['status'], case['decision']['by'], case['requestId']), ('decided', 'agent', r['id']))
        after = self.counts()
        self.assertEqual({t: after[t] - before[t] for t in before}, {'requests': 1, 'events': after['events'] - before['events'], 'actions': 0, 'decision_cases': 1,
                                                                      'confirmed_facts': 0, 'delegation_policies': 0})
        self.assertEqual(self.model.calls, 0)

    def test_2_a_new_customer_trial_with_a_records_verified_deposit_executes_with_no_staff_step(self):
        out = self.resolved(**self.trial('northside', '800.00'))
        self.assertEqual((out['status'], out['handling'], out['actionId'], out['requestId']), ('decided', 'autonomous_approve', None, None))
        f = out['keyFacts']
        self.assertEqual((f['orderAmount']['text'], f['verifiedDeposit']['text'], f['depositShare'], f['exposure']['text'], f['termsDays'], f['dueDateIfApproved']),
                         ('AUD 800.00', 'AUD 200.00', '0.25', 'AUD 600.00', 14, '2026-11-07'))
        d = out['decision']
        self.assertEqual((d['decidedBy'], d['decidedByKind'], d['requestedBy']['role']), ('nucleon_agent', 'agent', 'staff'))
        self.assertEqual((d['outcome'], d['by'], d['creditLine']['exposure'], d['creditLine']['verifiedDeposit'], d['creditLine']['termsDays'], d['creditLine']['approvedOn']),
                         ('approve', 'agent', 60000, 20000, 14, '2026-10-24'))
        self.assertEqual(d['authoritySource']['version'], 1)
        evidence = {i['key']: i['status'] for i in out['evidence']['items']}
        self.assertEqual((evidence['deposit'], evidence['business_identity'], evidence['records_complete']), ('verified', 'verified', 'verified'))
        self.assertEqual(self.count('actions'), 0)
        self.assertEqual(self.count('requests'), 0)
        self.assertEqual(self.model.calls, 0)

    def test_3_a_new_customer_with_nothing_on_file_gets_an_evidence_request_and_is_approved_after_a_staff_person_confirms(self):
        out = self.resolved(**self.trial('lakeside', '600.00'))
        self.assertEqual((out['status'], out['handling']), ('gathering_evidence', 'request_evidence'))
        self.assertEqual(out['needs'], ['Deposit', 'Business identity'])
        self.assertTrue(out['actionId'].startswith('act_') and len(out['actionId']) == 20)
        self.assertEqual(out['evidenceLink'], '#/actions/' + out['actionId'])
        self.assertIn('Not decided yet', out['statusText'])
        [(kind, status, invoice_id)] = self.row('SELECT kind, status, invoice_id FROM actions')
        self.assertEqual((kind, status, invoice_id), ('evidence', 'proposed', out['caseId']))
        page = self.call('/api/actions/' + out['actionId'], None, 'staff')[1]
        self.assertEqual((page['kind'], page['status']), ('evidence', 'proposed'))
        self.assertIn('confirming facts, not approving credit', page['statement'])
        self.assertEqual(next(n for n in page['needs'] if n['kind'] == 'deposit')['atLeastText'], 'AUD 150.00')
        items = [{'kind': 'deposit', 'basis': 'bank', 'amount': '150.00', 'receivedDate': '2026-10-23', 'reference': 'DEP-LK-01'},
                 {'kind': 'business_identity', 'basis': 'document', 'registration': 'Registration 111 (fictional)', 'tradingName': 'Lakeside Kiosk (fictional)'}]
        before = self.counts()
        # a service session, the owner, a call with no csrf token, a bad Origin and none are refused; nothing changes
        for role in ('staff', 'owner'):
            cookie = self.service_cookie(role)
            status, body = self.submit(out['actionId'], items, role=role, cookie=cookie)
            self.assertEqual((status, body['error']), (403, 'PERSON_REQUIRED'), role)
        status, body = self.submit(out['actionId'], items, role='owner')
        self.assertEqual((status, body['error']), (403, 'FORBIDDEN'))
        status, body = self.submit(out['actionId'], items, csrf=False)
        self.assertEqual((status, body['error']), (403, 'CSRF_REQUIRED'))
        status, body = self.submit(out['actionId'], items, csrf='wrong-token')
        self.assertEqual((status, body['error']), (403, 'CSRF_REQUIRED'))
        status, body = self.submit(out['actionId'], items, origin='https://evil.example')
        self.assertEqual((status, body['error']), (403, 'FORBIDDEN'))
        status, body = self.submit(out['actionId'], items, origin=False)
        self.assertEqual((status, body['error']), (403, 'ORIGIN_REQUIRED'))
        agent = self.agent_cookies()
        status, body = self.submit(out['actionId'], items, cookie=agent['nucleon_staff'], headers={'X-Nucleon-Role': 'staff'})
        self.assertEqual((status, body['error']), (403, 'PERSON_REQUIRED'))
        self.assertEqual(self.counts(), before)
        status, body = self.submit(out['actionId'], items)   # the staff person
        self.assertEqual(status, 200, body)
        case = body['case']
        self.assertEqual((case['status'], case['handling'], body['action']['status']), ('decided', 'autonomous_approve', 'executed'))
        self.assertEqual((case['keyFacts']['verifiedDeposit']['text'], case['keyFacts']['exposure']['text']), ('AUD 150.00', 'AUD 450.00'))
        facts = self.row('SELECT kind, data FROM confirmed_facts WHERE customer_id=? ORDER BY kind', self.cust['lakeside'])
        self.assertEqual([k for k, _ in facts], ['business_identity', 'deposit'])
        provenance = json.loads(facts[1][1])['provenance']
        self.assertEqual((provenance['role'], provenance['actorId'], provenance['channel'], provenance['actionId']), ('staff', 'staff_demo', 'person', out['actionId']))
        replay = self.submit(out['actionId'], items, key='ev-2')[1]
        self.assertTrue(replay['replayed'])
        self.assertEqual(replay['case']['status'], 'decided')
        self.assertEqual(self.count('confirmed_facts'), 3)   # with the one fictional seed fact on file for Northside Cafe
        self.assertEqual(self.model.calls, 0)
        self.assertEqual(self.tool('decisionStatus', caseId=out['caseId'])['result']['status'], 'decided')

    def test_3b_a_deposit_that_is_too_small_leaves_the_case_gathering_with_a_new_request(self):
        out = self.resolved(**self.trial('lakeside', '600.00'))
        items = [{'kind': 'deposit', 'basis': 'bank', 'amount': '100.00', 'receivedDate': '2026-10-23'}, {'kind': 'business_identity', 'basis': 'document', 'registration': 'R-1', 'tradingName': 'Lakeside'}]
        status, body = self.submit(out['actionId'], items)
        self.assertEqual(status, 200, body)
        self.assertEqual((body['case']['status'], body['case']['needs']), ('gathering_evidence', ['Deposit']))
        self.assertNotEqual(body['case']['actionId'], out['actionId'])
        self.assertEqual(self.row('SELECT status FROM actions WHERE id=?', out['actionId']), [('executed',)])
        self.assertEqual(self.row('SELECT status FROM actions WHERE id=?', body['case']['actionId']), [('proposed',)])

    def test_3c_evidence_items_are_validated_per_kind(self):
        out = self.resolved(**self.trial('lakeside', '600.00'))
        bad = [[], 'x', [{'kind': 'deposit', 'basis': 'bank', 'amount': '0', 'receivedDate': '2026-10-23'}], [{'kind': 'deposit', 'basis': 'bank', 'amount': '150.00', 'receivedDate': '2026-10-30'}],
               [{'kind': 'deposit', 'basis': 'bank', 'amount': '150.00', 'receivedDate': '2026-10-23', 'extra': 1}], [{'kind': 'trade_reference', 'referee': 'x', 'summary': 'y'}],
               [{'kind': 'business_identity', 'basis': 'document', 'registration': 'R'}], [{'kind': 'no_prior_account', 'confirmed': False}],
               [{'kind': 'business_identity', 'basis': 'document', 'registration': 'R', 'tradingName': 'T'}, {'kind': 'business_identity', 'basis': 'document', 'registration': 'R', 'tradingName': 'T'}],
               [{'kind': 'deposit', 'basis': 'bank', 'amount': '12.345', 'receivedDate': '2026-10-23'}], [{'kind': 'nonsense'}]]
        for items in bad:
            status, body = self.submit(out['actionId'], items)
            self.assertEqual(status, 400, (items, body))
        self.assertEqual(self.submit(out['actionId'], [{'kind': 'business_identity', 'basis': 'document', 'registration': 'R', 'tradingName': 'T'}], version=9)[1]['error'], 'STALE_ACTION_VIEW')
        self.assertEqual(self.count('confirmed_facts'), 1)   # only the fictional seed fact: nothing was kept

    def test_4_a_large_exposure_goes_to_the_owner_with_the_recommendation_and_nothing_executes(self):
        out = self.resolved(**self.trial('harbourline', '5000.00'))
        self.assertEqual((out['status'], out['handling'], out['decision']), ('awaiting_owner', 'owner_review', None))
        self.assertEqual(out['keyFacts']['exposure']['text'], 'AUD 4,000.00')
        self.assertEqual(out['risk']['status'], 'outside')
        self.assertTrue(any('over the limit' in w for w in out['warnings']), out['warnings'])
        self.assertEqual(out['recommendation']['recommendation'], 'approve')
        self.assertIn('Not approved', out['statusText'])
        # the Owner decides it; the agreement is whether the Owner's outcome is the assistant's recommendation
        status, body = self.send('POST', '/api/decision-cases/' + out['caseId'] + '/decide', {'outcome': 'decline', 'reason': 'Too large for a first order.', 'version': out['version']})
        self.assertEqual(status, 200, body)
        self.assertEqual((body['status'], body['decision']['by'], body['decision']['outcome'], body['decision']['agreement']), ('decided', 'owner', 'decline', False))
        self.assertTrue(self.send('POST', '/api/decision-cases/' + out['caseId'] + '/decide', {'outcome': 'decline', 'reason': 'again', 'version': 1})[1]['replayed'])
        self.assertEqual(self.send('POST', '/api/decision-cases/' + out['caseId'] + '/decide', {'outcome': 'approve', 'reason': 'x', 'version': 1})[0], 409)

    def test_4b_an_extension_sent_to_the_owner_is_a_request_only_the_owner_decides_and_its_case_follows(self):
        out = self.resolved(**self.extension('cityside', 'DEMO-410', days=14))
        self.assertEqual((out['status'], out['handling'], out['decision']), ('awaiting_owner', 'owner_review', None))
        r = self.request_of(out['requestId'])
        self.assertEqual((r['status'], r['decision'], r['intake']['channel']), ('awaiting_owner', None, 'delegated_agent'))
        self.assertEqual(self.due('cityside', 'DEMO-410'), '2026-10-28')   # nothing moved
        status, body, _ = self.call('/api/tools/actWithinAuthority', {'args': {'requestId': r['id']}}, 'staff', 'act-1')
        self.assertEqual((status, body['error']), (409, 'OWNER_REVIEW_REQUIRED'))
        self.assertEqual(self.due('cityside', 'DEMO-410'), '2026-10-28')
        self.assertEqual(self.call('/api/requests/' + r['id'] + '/decisions', {}, 'staff', 'd0')[0], 403)
        status, body, _ = self.decide(r, 'approve', '2026-11-11', key='owner-decides')
        self.assertEqual(status, 201, body)
        case = self.case(out['caseId'])
        self.assertEqual((case['status'], case['decision']['by'], case['decision']['outcome'], case['decision']['agreement']), ('decided', 'owner', 'approve', True))
        self.assertEqual(self.due('cityside', 'DEMO-410'), '2026-11-11')

    def test_a_records_change_prepares_a_delegated_request_again_by_code_and_no_model_is_asked(self):
        out = self.resolved(**self.extension('cityside', 'DEMO-410', days=14))
        with self.app.lock, self.app.db:   # a payment arrives for the customer: the evidence of the waiting request changes
            doc = self.app.fixture()
            delegation_demo.new_payment(doc, {'customerId': self.cust['cityside'], 'receivedDate': '2026-10-24', 'amount': '50.00', 'reference': 'EFT-NEW'}, SETTINGS, AS_OF,
                                        'payment_extra', {'kind': 'manual', 'by': 'test', 'role': 'staff', 'at': '2026-10-24T00:00:00+00:00'})
            self.app.save_doc(doc)
            self.app.records_changed('test', {'id': 'staff_demo', 'role': 'staff'}, 'a payment')
        r = self.wait_status({'id': out['requestId']}, ('awaiting_owner',))
        self.assertEqual((r['status'], r['intake']['structured']['caseId']), ('awaiting_owner', out['caseId']))
        self.assertEqual(self.model.calls, 0)
        self.assertEqual(self.tool('decisionStatus', caseId=out['caseId'])['result']['status'], 'awaiting_owner')
        # the decided delegated request is flagged by the ordinary code when its evidence changes later, and its decision stands
        done = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        self.assertEqual(self.request_of(done['requestId'])['decisionBasisGap']['kind'], 'delegated')

    def test_5_an_unusually_large_amount_goes_to_the_owner(self):
        out = self.resolved(**self.extension('cityside', 'DEMO-410', days=14))
        self.assertEqual(out['handling'], 'owner_review')
        self.assertEqual(out['keyFacts']['extensionDays'], 14)
        size = next(c for c in out['risk']['checks'] if c['key'] == 'unusual_size')
        self.assertEqual(size['status'], 'fail')
        self.assertIn('4.5 times the median', size['sentence'])   # 4.5 times the median of earlier invoices (900 against 200)
        self.assertEqual(out['risk']['status'], 'outside')

    def test_6_incomplete_records_go_to_the_owner_and_are_never_a_decline(self):
        out = self.resolved(**self.extension('riverside', 'DEMO-505', days=10))
        self.assertEqual((out['status'], out['handling']), ('awaiting_owner', 'owner_review'))
        self.assertEqual(out['evidence']['status'], 'insufficient')
        self.assertTrue(any('incomplete for this customer' in w for w in out['warnings']), out['warnings'])
        self.assertIsNone(out['decision'])
        self.assertNotIn('decline', json.dumps(out['statusText']).lower())
        r = self.request_of(out['requestId'])
        self.assertIsNone(r['decision'])

    def test_6b_no_earlier_account_confirmed_while_invoices_exist_puts_the_case_on_hold(self):
        out = self.resolved(**self.trial('lakeside', '600.00'))
        with self.app.lock, self.app.db:   # an invoice appears in the records for the customer Staff will say has no earlier account
            doc = self.app.fixture()
            delegation_demo.new_invoice(doc, {'customerId': self.cust['lakeside'], 'reference': 'DEMO-701', 'issueDate': '2026-10-20', 'total': '90.00', 'dueDate': '2026-11-03'},
                                        SETTINGS, AS_OF, 'invoice_extra', {'kind': 'manual', 'by': 'test', 'role': 'staff', 'at': '2026-10-20T00:00:00+00:00'})
            self.app.save_doc(doc)
        items = [{'kind': 'deposit', 'basis': 'bank', 'amount': '150.00', 'receivedDate': '2026-10-23', 'reference': 'DEP-LK-5'},
                 {'kind': 'business_identity', 'basis': 'document', 'registration': 'R-2', 'tradingName': 'Lakeside'}, {'kind': 'no_prior_account', 'confirmed': True}]
        status, body = self.submit(out['actionId'], items)
        self.assertEqual(status, 200, body)
        case = body['case']
        self.assertEqual((case['status'], case['handling'], case['evidence']['status']), ('on_hold', 'policy_hold', 'contradictory'))
        self.assertIn('no earlier account', json.dumps(case['evidence']['items']))
        self.assertIsNone(case['decision'])

    def test_6c_a_confirmed_deposit_with_the_reference_of_a_recorded_receipt_but_another_amount_is_a_contradiction(self):
        out = self.resolved(**self.trial('lakeside', '600.00'))
        with self.app.lock, self.app.db:   # a receipt recorded under the reference Staff will confirm, in another amount
            doc = self.app.fixture()
            delegation_demo.new_payment(doc, {'customerId': self.cust['lakeside'], 'receivedDate': '2026-10-22', 'amount': '40.00', 'reference': 'DEP-LK-77'},
                                        SETTINGS, AS_OF, 'payment_extra', {'kind': 'manual', 'by': 'test', 'role': 'staff', 'at': '2026-10-22T00:00:00+00:00'})
            self.app.save_doc(doc)
        items = [{'kind': 'deposit', 'basis': 'bank', 'amount': '150.00', 'receivedDate': '2026-10-23', 'reference': 'dep-lk-77'},
                 {'kind': 'business_identity', 'basis': 'document', 'registration': 'R-3', 'tradingName': 'Lakeside'}]
        status, body = self.submit(out['actionId'], items)
        self.assertEqual(status, 200, body)
        case = body['case']
        self.assertEqual((case['status'], case['handling'], case['evidence']['status']), ('on_hold', 'policy_hold', 'contradictory'))
        self.assertIn('not a decline', case['statusText'])
        self.assertIsNone(case['decision'])
        self.assertEqual(self.count('requests'), 0)

    def test_the_assistants_decline_or_escalate_inside_the_policy_goes_to_the_owner_and_is_never_an_autonomous_decline(self):
        for rec in ('decline', 'escalate'):
            args = self.extension('bayview', 'DEMO-301', date='2026-11-10')
            args['recommendation'] = rec
            out = self.resolved(key='rec-' + rec, **args)
            self.assertEqual((out['status'], out['handling'], out['decision']), ('awaiting_owner', 'owner_review', None), rec)
            self.assertIn('not approval', ' '.join(out['reasons']))
            self.assertEqual(self.due('bayview', 'DEMO-301'), '2026-10-18')
            r = self.request_of(out['requestId'])
            self.assertEqual(self.call('/api/requests/' + r['id'], None, 'staff')[1]['decision'], None)
            self.withdraw(r['id'])   # frees the invoice for the next iteration
        self.assertEqual(self.count('requests'), 2)

    def withdraw(self, request_id):
        body = self.call('/api/tools/withdrawRequest', {'args': {'requestId': request_id, 'reason': 'test'}}, 'staff', 'w-' + request_id)[1]
        self.assertTrue(body['ok'], body)


# ---------------------------------------------------------------- duplicates, concurrency, policy changes

class DuplicateTests(DelegationCase):
    def test_7_an_identical_resolve_replays_the_stored_case_and_creates_nothing(self):
        out = self.resolved(**self.extension('cityside', 'DEMO-410', days=14))
        before = self.counts()
        again = self.resolved(key='another-key', **self.extension('cityside', 'DEMO-410', days=14))
        self.assertEqual((again['caseId'], again['replayed']), (out['caseId'], True))
        self.assertEqual(self.counts(), before)
        same_key = self.call('/api/tools/resolveDecision', {'args': self.extension('cityside', 'DEMO-410', days=14)}, 'staff', self.key_of('resolveDecision', self.extension('cityside', 'DEMO-410', days=14)))
        self.assertTrue(same_key[1]['replayed'])   # the tool surface's own replay of a retried key

    def test_7b_different_terms_while_a_case_is_live_are_409_case_open_naming_it(self):
        out = self.resolved(**self.trial('lakeside', '600.00'))
        status, body, _ = self.call('/api/tools/resolveDecision', {'args': self.trial('lakeside', '700.00')}, 'staff', 'different')
        self.assertEqual((status, body['error'], body['caseId'], body['caseStatus']), (409, 'CASE_OPEN', out['caseId'], 'gathering_evidence'))
        self.assertEqual(self.count('decision_cases') - len(MEMORY['cases']), 1)
        self.assertEqual(self.count('actions'), 1)

    def test_7c_an_extension_the_agent_already_approved_for_the_same_date_returns_that_decision(self):
        out = self.resolved(**self.extension('bayview', 'DEMO-301', days=23))   # to 2026-11-10
        before = self.counts()
        again = self.resolved(key='again', **self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        self.assertEqual((again['caseId'], again['replayed'], again['status']), (out['caseId'], True, 'decided'))
        self.assertEqual(self.counts(), before)
        # asked in days again, the days count from a due date the decision already moved: the same ask, so the same decision (within a day of it)
        by_days = self.resolved(key='by-days', **self.extension('bayview', 'DEMO-301', days=23))
        self.assertEqual((by_days['caseId'], by_days['replayed']), (out['caseId'], True))
        self.assertEqual(self.counts(), before)
        self.assertEqual(self.due('bayview', 'DEMO-301'), '2026-11-10')

    def test_7d_concurrent_resolves_make_one_case_and_one_request(self):
        args = self.extension('bayview', 'DEMO-301', date='2026-11-10')

        def one(n):
            return self.call('/api/tools/resolveDecision', {'args': args}, 'staff', 'concurrent-' + str(n))
        with ThreadPoolExecutor(8) as pool:
            results = list(pool.map(one, range(8)))
        self.assertTrue(all(status == 200 and body['ok'] for status, body, _ in results), results)
        self.assertEqual({body['result']['caseId'] for _, body, _ in results}, {results[0][1]['result']['caseId']})
        self.assertEqual(sum(1 for _, body, _ in results if not body['result'].get('replayed')), 1)
        self.assertEqual(self.count('requests'), 1)
        self.assertEqual(self.count('decision_cases') - len(MEMORY['cases']), 1)

    def test_a_second_live_case_is_refused_by_the_unique_index_itself(self):
        out = self.resolved(**self.trial('lakeside', '600.00'))
        with self.app.lock:
            case = self.app.dg_case(out['caseId'])
            with self.assertRaises(sqlite_integrity()):
                self.app.db.execute('INSERT INTO decision_cases (id, kind, subject, status, dataset, created_at, updated_at, data) VALUES (?,?,?,?,?,?,?,?)',
                                    ('case_dup', case['kind'], case['subject'], 'awaiting_owner', 'live', 'x', 'x', '{}'))
            self.app.db.rollback()
        self.assertEqual(self.row('SELECT COUNT(*) FROM decision_cases WHERE id=?', 'case_dup'), [(0,)])


def sqlite_integrity():
    import sqlite3
    return sqlite3.IntegrityError


class AlreadyHandledTests(DelegationCase):
    def assess(self, args):
        return self.tool('assessDecision', **{k: v for k, v in args.items() if k not in ('recommendation', 'reasoning')})['result']

    def test_assess_after_an_agent_approval_returns_the_stored_status_and_stores_nothing(self):
        for args in (self.trial('northside', '800.00'), self.extension('bayview', 'DEMO-301', date='2026-11-10')):
            first = self.resolved(**args)
            self.assertEqual(first['status'], 'decided')
            before = self.counts()
            out = self.assess(args)
            self.assertEqual((out['alreadyHandled'], out['caseId'], out['status'], out['statusText']), (True, first['caseId'], 'decided', first['statusText']))
            self.assertNotIn('stored', out)
            self.assertIn('already handled (case ' + first['caseId'] + ', decided)', out['note'])
            self.assertIn('report this statusText', out['note'])
            self.assertEqual(self.counts(), before)

    def test_assess_by_days_matches_the_resolve_replay(self):
        first = self.resolved(**self.extension('bayview', 'DEMO-301', days=23))
        out = self.assess(self.extension('bayview', 'DEMO-301', days=23))   # days count from the moved due date: the same ask within a day of the approval
        self.assertEqual((out['alreadyHandled'], out['caseId']), (True, first['caseId']))

    def test_assess_after_owner_review_returns_awaiting_owner(self):
        first = self.resolved(**self.trial('harbourline', '5000.00'))
        self.assertEqual(first['status'], 'awaiting_owner')
        before = self.counts()
        out = self.assess(self.trial('harbourline', '5000.00'))
        self.assertEqual((out['alreadyHandled'], out['caseId'], out['status']), (True, first['caseId'], 'awaiting_owner'))
        self.assertEqual(self.counts(), before)

    def test_different_parameters_are_assessed_as_new(self):
        self.resolved(**self.trial('northside', '800.00'))
        out = self.assess(self.trial('northside', '650.00'))
        self.assertEqual((out['status'], out.get('alreadyHandled'), out['stored']), ('assessed', None, False))
        self.resolved(**self.trial('harbourline', '5000.00'))
        self.assertEqual(self.assess(self.trial('harbourline', '4000.00'))['status'], 'assessed')
        self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        self.assertEqual(self.assess(self.extension('bayview', 'DEMO-301', date='2026-11-12'))['status'], 'assessed')

    def test_after_an_override_the_request_is_evaluated_normally(self):
        first = self.resolved(**self.trial('northside', '800.00'))
        self.assertEqual(self.feedback(first['caseId'], {'verdict': 'disagree', 'reason': 'Revoke.', 'override': True})[0], 200)
        out = self.assess(self.trial('northside', '800.00'))
        self.assertEqual((out['status'], out.get('alreadyHandled')), ('assessed', None))


class TrialInForceTests(DelegationCase):
    def test_a_repeated_resolve_of_an_approved_trial_credit_replays_it_and_other_terms_go_to_the_owner(self):
        first = self.resolved(**self.trial('northside', '800.00'))
        self.assertEqual(first['status'], 'decided')
        before = self.counts()
        again = self.resolved(key='again', **self.trial('northside', '800.00'))
        self.assertEqual((again['caseId'], again['replayed'], again['status']), (first['caseId'], True, 'decided'))
        self.assertEqual(self.counts(), before)
        decided = self.row("SELECT COUNT(*) FROM decision_cases WHERE dataset='live' AND kind='trial_credit' AND status='decided'")
        self.assertEqual(decided, [(1,)])
        other = self.resolved(key='other', **self.trial('northside', '700.00'))
        self.assertEqual((other['handling'], other['status']), ('owner_review', 'awaiting_owner'))
        self.assertIn('A trial credit for this customer is already in force; a further one goes to the Owner.', other['reasons'][0] + ' '.join(other['reasons']))
        self.assertIn('already in force', other['statusText'])
        preview = self.tool('assessDecision', kind='trial_credit', customerId=self.cust['northside'], orderAmount='650.00', termsDays=14)['result']
        self.assertEqual(preview['handling'], 'owner_review')
        self.assertIn('already in force', preview['statusText'])
        self.assertEqual(self.row("SELECT COUNT(*) FROM decision_cases WHERE dataset='live' AND status='decided'"), [(1,)])

    def test_concurrent_repeats_make_one_line(self):
        args = self.trial('northside', '800.00')
        with ThreadPoolExecutor(6) as pool:
            results = list(pool.map(lambda n: self.call('/api/tools/resolveDecision', {'args': args}, 'staff', 'c-%d' % n), range(6)))
        self.assertEqual({b['result']['caseId'] for _, b, _ in results}, {results[0][1]['result']['caseId']})
        self.assertEqual(self.row("SELECT COUNT(*) FROM decision_cases WHERE dataset='live' AND status='decided'"), [(1,)])

    def test_after_an_override_a_new_request_is_evaluated_normally(self):
        first = self.resolved(**self.trial('northside', '800.00'))
        status, body = self.feedback(first['caseId'], {'verdict': 'disagree', 'reason': 'Revoke.', 'override': True})
        self.assertEqual(status, 200, body)
        again = self.resolved(key='after', **self.trial('northside', '700.00'))
        self.assertEqual((again['handling'], again['status']), ('autonomous_approve', 'decided'))
        self.assertNotEqual(again['caseId'], first['caseId'])


class RecommendationUpdateTests(DelegationCase):
    def test_escalate_for_missing_information_then_approve_update_then_evidence_is_decided_by_the_agent(self):
        args = self.trial('lakeside', '600.00')
        args.update(recommendation='escalate', reasoning='Nothing is verified yet.')
        first = self.resolved(**args)
        self.assertEqual(first['status'], 'gathering_evidence')
        self.assertIn("Your recommendation 'escalate' is recorded", first['note'])
        self.assertIn('call resolveDecision again', first['note'])
        before = self.counts()
        upd = self.resolved(key='upd', **{**args, 'recommendation': 'approve', 'reasoning': 'On the merits it is fine once verified.'})
        self.assertEqual((upd['caseId'], upd['replayed'], upd['recommendationUpdated'], upd['status'], upd['recommendation']['recommendation']), (first['caseId'], True, True, 'gathering_evidence', 'approve'))
        self.assertNotIn('note', upd)
        self.assertEqual(self.counts(), before)   # no new case, action or request, and nothing executed
        self.assertIsNone(upd['decision'])
        case = self.case(first['caseId'])
        history = json.loads(self.row('SELECT data FROM decision_cases WHERE id=?', first['caseId'])[0][0])['recommendationHistory']
        self.assertEqual([h['recommendation'] for h in history], ['escalate', 'approve'])
        self.assertEqual((history[0]['reasoning'], history[1]['requestedBy']['role']), ('Nothing is verified yet.', 'staff'))
        self.assertEqual(case['recommendation']['recommendation'], 'approve')
        items = [{'kind': 'deposit', 'basis': 'bank', 'amount': '150.00', 'receivedDate': '2026-10-23'}, {'kind': 'business_identity', 'basis': 'document', 'registration': 'R', 'tradingName': 'T'}]
        status, body = self.submit(first_action(self, first), items)
        self.assertEqual((status, body['case']['status'], body['case']['decision']['by']), (200, 'decided', 'agent'))

    def test_an_update_never_executes_while_evidence_is_missing_and_same_text_changes_nothing(self):
        out = self.resolved(**self.trial('lakeside', '600.00'))
        for n in range(3):
            upd = self.resolved(key='u%d' % n, **{**self.trial('lakeside', '600.00'), 'reasoning': 'Reason %d' % n})
            self.assertEqual((upd['status'], upd['handling'], upd['decision']), ('gathering_evidence', 'request_evidence', None))
        self.assertEqual((self.count('actions'), self.row("SELECT COUNT(*) FROM decision_cases WHERE status='decided' AND dataset='live'")), (1, [(0,)]))
        again = self.resolved(key='same', **{**self.trial('lakeside', '600.00'), 'reasoning': 'Reason 2'})
        self.assertNotIn('recommendationUpdated', again)
        self.assertEqual(len(json.loads(self.row('SELECT data FROM decision_cases WHERE id=?', out['caseId'])[0][0])['recommendationHistory']), 4)

    def test_once_with_the_owner_the_recommendation_is_not_changed(self):
        out = self.resolved(**self.trial('harbourline', '5000.00'))
        upd = self.resolved(key='late', **{**self.trial('harbourline', '5000.00'), 'recommendation': 'decline', 'reasoning': 'Changed my mind.'})
        self.assertEqual((upd['caseId'], upd['replayed'], upd['recommendation']['recommendation']), (out['caseId'], True, 'approve'))
        self.assertNotIn('recommendationUpdated', upd)
        self.assertIn('was not changed', upd['note'])
        self.assertNotIn('recommendationHistory', json.loads(self.row('SELECT data FROM decision_cases WHERE id=?', out['caseId'])[0][0]))

    def test_the_tool_descriptions_say_missing_information_is_not_a_reason_to_escalate(self):
        for name in ('assessDecision', 'resolveDecision'):
            d = next(t for t in coordinator.DESK_TOOLS if t['function']['name'] == name)['function']['description']
            self.assertIn('Missing information is not a reason to escalate', d)


def first_action(test, result):
    return result['actionId']


class ApproveIfVerifiedTests(DelegationCase):
    IV = 'approve_if_verified'

    def test_missing_evidence_asks_staff_and_never_executes_then_evidence_makes_the_agent_decide(self):
        args = {**self.trial('lakeside', '600.00'), 'recommendation': self.IV, 'reasoning': 'Fine once the deposit and identity are confirmed.'}
        out = self.resolved(**args)
        self.assertEqual((out['status'], out['handling'], out['decision']), ('gathering_evidence', 'request_evidence', None))
        self.assertEqual(out['recommendation']['recommendation'], self.IV)   # recorded verbatim
        self.assertEqual(out['recommendation']['text'], 'The assistant recommended approval once the information is confirmed')
        self.assertNotIn('note', out)   # it already says what the note would ask for
        self.assertEqual(self.count('requests'), 0)
        status, body = self.submit(out['actionId'], [{'kind': 'deposit', 'basis': 'bank', 'amount': '150.00', 'receivedDate': '2026-10-23'}, {'kind': 'business_identity', 'basis': 'document', 'registration': 'R', 'tradingName': 'T'}])
        self.assertEqual((status, body['case']['status'], body['case']['decision']['by']), (200, 'decided', 'agent'))
        self.assertEqual(body['case']['recommendation']['recommendation'], self.IV)

    def test_with_the_evidence_already_complete_it_is_decided_and_the_decision_keeps_the_words(self):
        out = self.resolved(**{**self.extension('bayview', 'DEMO-301', date='2026-11-10'), 'recommendation': self.IV})
        self.assertEqual((out['status'], out['handling']), ('decided', 'autonomous_approve'))
        self.assertEqual(self.request_of(out['requestId'])['decision']['aiRecommendation']['recommendation'], self.IV)
        trial = self.resolved(**{**self.trial('northside', '800.00'), 'recommendation': self.IV})
        self.assertEqual(trial['status'], 'decided')

    def test_outside_the_policy_it_goes_to_the_owner_and_the_owners_approval_counts_as_agreement(self):
        out = self.resolved(**{**self.trial('harbourline', '5000.00'), 'recommendation': self.IV})
        self.assertEqual((out['status'], out['handling']), ('awaiting_owner', 'owner_review'))
        status, body = self.send('POST', '/api/decision-cases/' + out['caseId'] + '/decide', {'outcome': 'approve', 'reason': 'Fine.', 'version': out['version']})
        self.assertTrue(body['decision']['agreement'])
        self.assertNotIn('did not recommend approval', ' '.join(out['reasons']))

    def test_the_text_is_shown_in_the_assessment_and_the_other_recommendations_have_theirs(self):
        a = self.tool('assessDecision', kind='trial_credit', customerId=self.cust['lakeside'], orderAmount='600.00', termsDays=14, recommendation=self.IV)['result']
        self.assertEqual((a['handling'], a['recommendation']['text']), ('request_evidence', 'The assistant recommended approval once the information is confirmed'))
        e = delegation.RECOMMENDATION_WORDS
        self.assertEqual(sorted(e), sorted(delegation.RECOMMENDATIONS))
        self.assertEqual(delegation.RECOMMENDATIONS[0], 'approve_if_verified')
        for name in ('assessDecision', 'resolveDecision'):
            spec = next(t for t in coordinator.DESK_TOOLS if t['function']['name'] == name)['function']
            self.assertEqual(spec['parameters']['properties']['recommendation']['enum'][0], 'approve_if_verified')
            self.assertIn('approve_if_verified', spec['description'])
        self.assertTrue(delegation.agrees('approve', self.IV) and not delegation.agrees('decline', self.IV))
        e2 = evaluate(rec=self.IV)
        self.assertEqual(e2['handling'], 'autonomous_approve')


class FixesTests(DelegationCase):
    def test_a_customer_overview_works_with_a_payment_that_has_no_received_date(self):
        for who in ('riverside', 'bayview'):
            out = self.tool('customerOverview', customerId=self.cust[who])
            self.assertTrue(out['ok'], out)
        for q in self.tool('invoices', customerId=self.cust['riverside'], which='all')['result']['invoices']:
            self.assertIn('stillOwedText', q)
        self.assertTrue(self.call('/api/records', None, 'staff')[0] == 200)

    def test_decision_status_by_customer_gives_the_latest_live_case_and_recent_cases(self):
        self.resolved(**self.trial('lakeside', '600.00'))
        first = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        live = self.resolved(**self.trial('harbourline', '5000.00'))
        got = self.tool('decisionStatus', customerId=self.cust['harbourline'])['result']
        self.assertEqual((got['caseId'], got['status']), (live['caseId'], 'awaiting_owner'))
        self.assertEqual([c['caseId'] for c in got['recentCases']], [live['caseId']])
        self.assertTrue(got['recentCases'][0]['statusText'])
        done = self.tool('decisionStatus', customerId=self.cust['bayview'], kind='extension')['result']
        self.assertEqual((done['caseId'], done['status']), (first['caseId'], 'decided'))
        self.assertEqual(self.tool('decisionStatus', customerId=self.cust['bayview'], kind='trial_credit')['error'], 'NOT_FOUND')
        self.assertEqual(self.tool('decisionStatus', customerId=self.cust['northside'])['error'], 'NOT_FOUND')
        for bad in ({'customerId': self.cust['bayview'], 'caseId': 'x'}, {'kind': 'extension'}, {'caseId': first['caseId'], 'kind': 'extension'}, {'customerId': self.cust['bayview'], 'kind': 'nope'}):
            self.assertEqual(self.tool('decisionStatus', **bad)['error'], 'INVALID_ARGUMENT', bad)
        spec = next(t for t in coordinator.DESK_TOOLS if t['function']['name'] == 'decisionStatus')['function']
        self.assertIn('customerId', spec['parameters']['properties'])
        self.assertIn('exactly one selector', spec['description'])

    def test_the_owner_review_status_names_the_deciding_reason(self):
        def said(**kw):
            out = self.resolved(key=kw.pop('key', None), **kw)
            if out['kind'] == 'trial_credit' and out['status'] == 'awaiting_owner':   # the Owner settles it, so the customer can be asked about again
                self.assertEqual(self.send('POST', '/api/decision-cases/' + out['caseId'] + '/decide', {'outcome': 'decline', 'reason': 'x', 'version': out['version']})[0], 200)
            return out
        self.pause()
        paused = said(**self.trial('northside', '800.00'))
        self.assertIn("The Owner has paused the agent's authority, so the Owner decides", paused['statusText'])
        self.send('POST', '/api/delegation/policy/resume', {'expectedVersion': 2})
        self.change_policy(mode='advisory')
        self.assertIn('The agent is in advisory mode, so the Owner decides', said(**self.trial('northside', '750.00'), key='a')['statusText'])
        # the three trial credits the Owner declined above are now live reviewed cases; this test is about the wording of step 8, so it counts the fictional set only (D7 'both' would pool them)
        self.change_policy(newCustomers={**delegation_demo.DEMO_POLICY['newCustomers'], 'trialCredit': 'off'}, trackRecord={**delegation_demo.DEMO_POLICY['trackRecord'], 'sources': 'fictional'})
        self.assertIn('turned off in the policy', said(**self.trial('northside', '740.00'), key='b')['statusText'])
        self.change_policy()
        outside = said(**self.trial('harbourline', '5000.00'), key='c')
        self.assertIn('outside what the Owner delegated (exposure of this decision)', outside['statusText'])
        self.assertIn('records are insufficient', said(**self.extension('riverside', 'DEMO-505', days=10), key='d')['statusText'])
        args = self.extension('bayview', 'DEMO-301', date='2026-11-10')
        args['recommendation'] = 'decline'
        self.assertIn('The assistant did not recommend approval', said(**args, key='e')['statusText'])
        card_why = outside['why']
        self.assertTrue(card_why.startswith('it is outside'))

    def test_a_missing_order_amount_or_terms_says_what_to_send(self):
        for drop, word in (('termsDays', 'termsDays (e.g. 14)'), ('orderAmount', 'orderAmount (e.g. "800.00")')):
            args = {k: v for k, v in self.trial('lakeside', '600.00').items() if k != drop}
            for name in ('resolveDecision', 'assessDecision'):
                body = self.tool(name, key='m-%s-%s' % (name, drop), **(args if name == 'resolveDecision' else {k: v for k, v in args.items() if k not in ('reasoning', 'recommendation')}))
                self.assertFalse(body['ok'])
                self.assertIn('trial_credit needs orderAmount (e.g. "800.00") and termsDays (e.g. 14). Missing: ' + word, body['message'])
        self.assertEqual(self.count('decision_cases') - len(MEMORY['cases']), 0)


class PolicyChangeTests(DelegationCase):
    def test_8_a_policy_change_between_assess_and_resolve_applies_the_current_version(self):
        assessed = self.tool('assessDecision', **{k: v for k, v in self.extension('bayview', 'DEMO-301', date='2026-11-10').items() if k in
                                                  ('kind', 'customerId', 'invoiceReference', 'requestedDueDate')}, policyVersion=1)['result']
        self.assertEqual((assessed['handling'], assessed['stored'], assessed['caseId'], assessed['authority']['version']), ('autonomous_approve', False, None, 1))
        self.assertEqual((self.count('requests'), self.count('actions')), (0, 0))   # an assessment stores nothing
        self.assertEqual(self.pause()['version'], 2)
        out = self.resolved(policyVersion=1, **self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        self.assertEqual((out['handling'], out['status'], out['authority']['version'], out['authority']['paused']), ('owner_review', 'awaiting_owner', 2, True))
        self.assertTrue(out['policyChangedSinceAssessment'])
        self.assertTrue(any('version 1 then, version 2 now' in w for w in out['warnings']), out['warnings'])
        self.assertEqual(self.case(out['caseId'])['authority']['version'], 2)
        self.assertEqual(self.due('bayview', 'DEMO-301'), '2026-10-18')

    def test_8b_a_policy_change_between_the_evidence_request_and_its_submission_applies_the_current_version(self):
        out = self.resolved(**self.trial('lakeside', '600.00'))
        self.assertEqual(out['authority']['version'], 1)
        self.pause()
        items = [{'kind': 'deposit', 'basis': 'bank', 'amount': '150.00', 'receivedDate': '2026-10-23'}, {'kind': 'business_identity', 'basis': 'document', 'registration': 'R', 'tradingName': 'T'}]
        status, body = self.submit(out['actionId'], items)
        self.assertEqual(status, 200, body)
        case = body['case']
        self.assertEqual((case['status'], case['handling'], case['authority']['version'], case['policyChangedSinceAssessment']), ('awaiting_owner', 'owner_review', 2, True))
        self.assertIsNone(case['decision'])

    def test_9_version_zero_advisory_paused_and_a_category_off_never_execute(self):
        # advisory mode: even an ordinary request goes to the owner; evidence is still asked for (it saves the owner a round trip)
        self.change_policy(mode='advisory')
        out = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        self.assertEqual((out['handling'], out['status']), ('owner_review', 'awaiting_owner'))
        self.assertIn('advisory', ' '.join(out['reasons']))
        self.assertEqual(self.resolved(**self.trial('lakeside', '600.00'))['handling'], 'request_evidence')
        self.assertEqual(self.resolved(**self.trial('northside', '800.00'))['handling'], 'owner_review')
        self.assertEqual(self.count('requests'), 1)
        self.assertEqual(self.due('bayview', 'DEMO-301'), '2026-10-18')
        self.assertEqual([c for c in self.row("SELECT status FROM decision_cases WHERE dataset='live' AND status='decided'")], [])

    def test_9b_paused_and_each_category_off(self):
        self.pause()
        self.assertEqual(self.resolved(**self.trial('northside', '800.00'))['handling'], 'owner_review')
        status, body = self.send('POST', '/api/delegation/policy/resume', {'expectedVersion': 2})
        self.assertEqual((status, body['version'], body['paused']), (200, 3, False))
        self.change_policy(extensions={**delegation_demo.DEMO_POLICY['extensions'], 'enabled': False})
        out = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        self.assertEqual(out['handling'], 'owner_review')
        self.assertIn('turned off', ' '.join(out['reasons']))
        self.change_policy(newCustomers={**delegation_demo.DEMO_POLICY['newCustomers'], 'trialCredit': 'off'})
        out = self.resolved(**self.trial('northside', '800.00'))
        self.assertEqual((out['handling'], out['status']), ('owner_review', 'awaiting_owner'))
        self.assertEqual(self.count('requests'), 1)

    def test_9c_with_no_policy_saved_the_effective_policy_is_version_zero_and_nothing_executes(self):
        with self.app.lock, self.app.db:
            self.app.db.execute('DELETE FROM delegation_policies')
        p = self.policy()
        self.assertEqual((p['version'], p['mode'], p['paused'], p['extensions']['enabled'], p['newCustomers']['trialCredit']), (0, 'advisory', False, False, 'off'))
        out = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        self.assertEqual((out['handling'], out['authority']['version']), ('owner_review', 0))
        self.assertEqual(self.resolved(**self.trial('northside', '800.00'))['handling'], 'owner_review')
        self.assertEqual(self.due('bayview', 'DEMO-301'), '2026-10-18')

    def test_a_limit_the_owner_lowers_is_applied_at_once(self):
        self.change_policy(limits={**delegation_demo.DEMO_POLICY['limits'], 'maxDecisionExposure': '400.00'})
        out = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        self.assertEqual((out['handling'], out['risk']['status']), ('owner_review', 'outside'))

    def test_a_policy_hold_on_a_customer_is_never_decided_by_the_agent(self):
        self.change_policy(restrictions={'holdCustomers': [self.cust['bayview']], 'unusualSizeMultiple': 3})
        out = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        self.assertEqual((out['handling'], out['status']), ('policy_hold', 'on_hold'))
        self.assertEqual(self.request_of(out['requestId'])['status'], 'awaiting_owner')

    def test_the_rolling_bound_counts_the_agents_own_approvals(self):
        self.change_policy(limits={**delegation_demo.DEMO_POLICY['limits'], 'maxAutonomousExposure30d': '1000.00'})
        self.assertEqual(self.resolved(**self.trial('northside', '800.00'))['handling'], 'autonomous_approve')   # 600.00
        out = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))   # 480.00 more would make 1,080.00
        self.assertEqual(out['handling'], 'owner_review')
        self.assertTrue(any(c['key'] == 'autonomous_30d' and c['status'] == 'fail' for c in out['risk']['checks']))


# ---------------------------------------------------------------- who may write the policy

class PolicyWriteTests(DelegationCase):
    def valid(self, **more):
        return {**delegation_demo.DEMO_POLICY, 'expectedVersion': self.policy()['version'], **more}

    def test_10_the_owner_person_saves_a_new_version_and_staff_may_only_read(self):
        status, out = self.put_policy(self.valid(note='Raise the day limit.', extensions={**delegation_demo.DEMO_POLICY['extensions'], 'maxDays': 45}))
        self.assertEqual((status, out['version'], out['extensions']['maxDays'], out['note']), (200, 2, 45, 'Raise the day limit.'))
        self.assertEqual(out['createdBy']['actorId'], 'owner_demo')
        self.assertEqual(out['limits']['maxDecisionExposure'], {'minorUnits': '100000', 'currency': 'AUD', 'scale': 2})
        seen = self.policy('staff')
        self.assertEqual((seen['version'], seen['readOnly'], 'createdBy' in seen), (2, True, False))
        history = self.call('/api/delegation/policy/history', None, 'owner')[1]
        self.assertEqual([v['version'] for v in history['versions']], [2, 1])
        self.assertEqual(self.call('/api/delegation/policy/history', None, 'staff')[0], 403)
        # the policy read back can be saved again as it is read
        again = {**out, 'expectedVersion': 2}
        for k in ('version', 'createdAt', 'createdBy', 'digest', 'readOnly', 'action'):
            again.pop(k, None)
        self.assertEqual(self.put_policy(again)[1]['version'], 3)

    def test_10b_staff_service_sessions_and_the_ai_agent_cannot_write_the_policy(self):
        before = self.counts()
        status, body = self.put_policy(self.valid(), role='staff')
        self.assertEqual((status, body['error']), (403, 'FORBIDDEN'))
        for role in ('staff', 'owner'):
            cookie = self.service_cookie(role)
            for method, path in (('PUT', '/api/delegation/policy'), ('POST', '/api/delegation/policy/pause'), ('POST', '/api/delegation/policy/resume')):
                status, body = self.send(method, path, self.valid(), role=role, cookie=cookie)
                self.assertEqual((status, body['error']), (403, 'PERSON_REQUIRED'), (role, path))
        agent = self.agent_cookies()
        for role in ('staff', 'owner'):
            status, body = self.send('PUT', '/api/delegation/policy', self.valid(), role=role, cookie=agent['nucleon_' + role], headers={'X-Nucleon-Role': role})
            self.assertEqual((status, body['error']), (403, 'PERSON_REQUIRED'), role)
            status, body = self.send('POST', '/api/decision-cases/case_x/decide', {}, role=role, cookie=agent['nucleon_' + role], headers={'X-Nucleon-Role': role})
            self.assertEqual((status, body['error']), (403, 'PERSON_REQUIRED'))
        self.assertEqual(self.counts(), before)
        self.assertEqual(self.policy()['version'], 1)

    def test_10c_csrf_and_origin_are_required_exactly_as_confirm_requires_them(self):
        self.assertEqual(self.put_policy(self.valid(), csrf=False)[1]['error'], 'CSRF_REQUIRED')
        self.assertEqual(self.put_policy(self.valid(), csrf='nope')[1]['error'], 'CSRF_REQUIRED')
        status, body = self.put_policy(self.valid(), origin='https://evil.example')
        self.assertEqual((status, body['error']), (403, 'FORBIDDEN'))
        self.assertEqual(self.put_policy(self.valid(), origin=False)[1]['error'], 'ORIGIN_REQUIRED')
        for path in ('/api/delegation/policy/pause', '/api/delegation/policy/resume'):
            self.assertEqual(self.send('POST', path, {'expectedVersion': 1}, origin=False)[1]['error'], 'ORIGIN_REQUIRED')
            self.assertEqual(self.send('POST', path, {'expectedVersion': 1}, csrf=False)[1]['error'], 'CSRF_REQUIRED')
        self.assertEqual(self.send('POST', '/api/delegation/policy', self.valid())[0], 405)   # saved with PUT only
        for action in ('decide', 'feedback'):
            self.assertEqual(self.send('POST', '/api/decision-cases/case_x/' + action, {}, origin=False)[1]['error'], 'ORIGIN_REQUIRED')
            self.assertEqual(self.send('POST', '/api/decision-cases/case_x/' + action, {}, csrf=False)[1]['error'], 'CSRF_REQUIRED')
        self.assertEqual(self.policy()['version'], 1)

    def test_10d_unknown_keys_bad_values_and_a_stale_version_are_refused(self):
        for body in (self.valid(allowExternalMessages=True), self.valid(autoDecline=True),
                     self.valid(limits={**delegation_demo.DEMO_POLICY['limits'], 'allowExternalMessages': True}),
                     self.valid(extensions={'enabled': True, 'autoDecline': True}), self.valid(mode='autonomous'),
                     self.valid(limits={'maxDecisionExposure': '10.00', 'maxCustomerExposure': 'abc'}),
                     self.valid(limits={'maxDecisionExposure': {'minorUnits': '1000', 'currency': 'USD', 'scale': 2}}),
                     self.valid(limits={'maxDecisionExposure': 1000}), self.valid(limits={'maxDecisionExposure': '10.001'}),
                     self.valid(extensions={**delegation_demo.DEMO_POLICY['extensions'], 'maxPriorLateShare': '1.5'}),
                     self.valid(extensions={**delegation_demo.DEMO_POLICY['extensions'], 'maxPriorLateShare': 0.5, 'maxDays': -1}),
                     self.valid(newCustomers={**delegation_demo.DEMO_POLICY['newCustomers'], 'minDepositShare': '25%'}),
                     self.valid(newCustomers={**delegation_demo.DEMO_POLICY['newCustomers'], 'trialCredit': 'unlimited'}),
                     self.valid(trackRecord={'minReviewedCases': 0}), self.valid(restrictions={'holdCustomers': 'c1'}), self.valid(paused='yes')):
            status, out = self.put_policy(body)
            self.assertEqual((status, out['error'] in ('INVALID_INPUT', 'INVALID_AMOUNT')), (400, True), (body, out))
        status, out = self.put_policy(self.valid(allowExternalMessages=True))
        self.assertIn('allowExternalMessages', out['message'])
        self.assertEqual(self.put_policy({**self.valid(), 'expectedVersion': None})[1]['error'], 'INVALID_INPUT')
        status, out = self.put_policy(self.valid(expectedVersion=0))
        self.assertEqual((status, out['error'], out['current']['version']), (409, 'POLICY_CHANGED', 1))
        self.assertEqual(self.send('POST', '/api/delegation/policy/pause', {'expectedVersion': 7})[1]['error'], 'POLICY_CHANGED')
        self.assertEqual(self.policy()['version'], 1)

    def test_10e_pause_and_resume_are_new_versions_and_a_put_keeps_the_pause(self):
        self.assertEqual(self.pause()['version'], 2)
        self.assertEqual(self.send('POST', '/api/delegation/policy/pause', {'expectedVersion': 2})[1]['error'], 'INVALID_TRANSITION')
        status, out = self.put_policy({k: v for k, v in self.valid().items() if k != 'paused'})   # a PUT that does not mention the pause keeps it
        self.assertEqual((status, out['version'], out['paused']), (200, 3, True))
        status, out = self.send('POST', '/api/delegation/policy/resume', {'expectedVersion': 3})
        self.assertEqual((status, out['version'], out['paused']), (200, 4, False))
        self.assertEqual([v['paused'] for v in self.call('/api/delegation/policy/history', None, 'owner')[1]['versions']], [False, True, True, False])

    def test_the_first_save_from_version_zero_is_version_one(self):
        with self.app.lock, self.app.db:
            self.app.db.execute('DELETE FROM delegation_policies')
        status, out = self.put_policy({**delegation_demo.DEMO_POLICY, 'expectedVersion': 0})
        self.assertEqual((status, out['version']), (200, 1))
        self.assertEqual(self.put_policy({'expectedVersion': 1})[1]['version'], 2)   # a PUT with nothing else is the version-0 defaults, advisory
        self.assertEqual(self.policy()['mode'], 'advisory')

    def test_no_tool_writes_the_policy(self):
        names = {t['function']['name'] for t in server.tools_for('staff', {n: {'enabled': True} for n in TOOLS}, pressed=True)} | \
                {t['function']['name'] for t in server.tools_for('owner', {n: {'enabled': True} for n in TOOLS}, pressed=True)}
        self.assertFalse([n for n in names if ('olicy' in n or 'elegat' in n) and n != 'policyBacktest'])   # policyBacktest (S3) reads and saves nothing: test_s3_tools
        for name in ('assessDecision', 'resolveDecision', 'decisionStatus'):
            spec = next(t for t in coordinator.DESK_TOOLS if t['function']['name'] == name)['function']['parameters']
            self.assertFalse([k for k in spec['properties'] if 'policy' in k.lower() and k != 'policyVersion'])
        out = self.call('/api/tools/resolveDecision', {'args': {**self.extension('bayview', 'DEMO-301', date='2026-11-10'), 'policy': {'mode': 'delegated'}}}, 'staff', 'inj')[1]
        self.assertEqual(out['error'], 'INVALID_ARGUMENT')


# ---------------------------------------------------------------- feedback and override

class FeedbackTests(DelegationCase):
    def approved_extension(self):
        return self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))

    def test_11_the_owner_can_agree_or_disagree_without_changing_the_decision(self):
        out = self.approved_extension()
        status, body = self.feedback(out['caseId'], {'verdict': 'agree', 'reason': 'Right call.'})
        self.assertEqual((status, body['feedback'][0]['verdict'], body['decision']['by']), (200, 'agree', 'agent'))
        status, body = self.feedback(out['caseId'], {'verdict': 'disagree', 'reason': 'I would have asked first.'})
        self.assertEqual((status, [f['verdict'] for f in body['feedback']], body['decision'].get('overridden')), (200, ['agree', 'disagree'], None))
        self.assertEqual(self.due('bayview', 'DEMO-301'), '2026-11-10')
        for bad in ({'verdict': 'maybe', 'reason': 'x'}, {'verdict': 'agree', 'reason': ''}, {'verdict': 'agree', 'reason': 'x', 'override': True}, {'verdict': 'agree', 'reason': 'x', 'override': 'yes'}):
            self.assertEqual(self.feedback(out['caseId'], bad)[0], 400, bad)
        self.assertEqual(self.feedback(out['caseId'], {'verdict': 'agree', 'reason': 'x'}, role='staff')[0], 403)
        pending = self.resolved(**self.trial('lakeside', '600.00'))
        self.assertEqual(self.feedback(pending['caseId'], {'verdict': 'agree', 'reason': 'x'})[1]['error'], 'INVALID_TRANSITION')   # not decided yet

    def test_11b_an_override_replaces_the_decision_reverts_the_due_date_and_keeps_the_history(self):
        out = self.approved_extension()
        self.assertEqual(self.due('bayview', 'DEMO-301'), '2026-11-10')
        status, body = self.feedback(out['caseId'], {'verdict': 'disagree', 'reason': 'They had missed a promise.', 'override': True})
        self.assertEqual(status, 200, body)
        self.assertTrue(body['decision']['overridden'])
        self.assertIn('overrode', body['statusText'])
        self.assertEqual(self.due('bayview', 'DEMO-301'), '2026-10-18')   # the effective due date is back
        r = self.request_of(out['requestId'])
        self.assertEqual((r['decision']['outcome'], r['decision']['decisionSource'], r['decision']['approvedDueDate']), ('decline', 'owner_override', None))
        self.assertEqual([d['decisionSource'] for d in r['decisionHistory']], ['delegated_policy'])
        self.assertEqual(r['decisionHistory'][0]['outcome'], 'approve')
        kinds = self.history_kinds(r['id'])
        self.assertIn('decision.committed', kinds)
        self.assertIn('decision.overridden', kinds)
        self.assertIn('declined', r['responseDraft']['text'])
        self.assertEqual(self.feedback(out['caseId'], {'verdict': 'disagree', 'reason': 'again', 'override': True})[1]['error'], 'INVALID_TRANSITION')
        stats = self.call('/api/delegation/stats', None, 'owner')[1]
        self.assertEqual((stats['counts']['overrides'], stats['counts']['autonomous']), (1, 0))
        # an overridden decision is not in force: the same ask can be made and is judged afresh
        again = self.resolved(key='after-override', **self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        self.assertNotEqual(again['caseId'], out['caseId'])

    def test_11c_overriding_a_trial_credit_revokes_the_line(self):
        out = self.resolved(**self.trial('northside', '800.00'))
        status, body = self.feedback(out['caseId'], {'verdict': 'disagree', 'reason': 'Revoke.', 'override': True})
        self.assertEqual((status, body['decision']['overridden'], body['decision']['by']), (200, True, 'agent'))
        self.assertIn('revoked', body['statusText'])
        with self.app.lock:
            self.assertEqual(self.app.dg_lines(self.cust['northside'], self.app.evidence()), 0)
        self.assertEqual(self.call('/api/delegation/stats', None, 'owner')[1]['counts']['overrides'], 1)

    def test_11d_the_owner_can_withdraw_their_own_approval_but_not_a_decline_and_it_is_no_override_of_the_agent(self):
        out = self.resolved(**self.trial('northside', '5000.00'))   # over the limits: the Owner decides
        self.assertEqual(out['status'], 'awaiting_owner')
        status, body = self.send('POST', '/api/decision-cases/' + out['caseId'] + '/decide', {'outcome': 'approve', 'reason': 'Fine.', 'version': self.case(out['caseId'])['version']})[:2]
        self.assertEqual((status, body['decision']['by']), (200, 'owner'), body)
        with self.app.lock:
            self.assertEqual(self.app.dg_lines(self.cust['northside'], self.app.evidence()), 480000)   # the line in force: 5,000 less the 200 deposit
        status, body = self.feedback(out['caseId'], {'verdict': 'disagree', 'reason': 'Clicked approve by mistake.', 'override': True})
        self.assertEqual((status, body['decision']['overridden'], body['decision']['by'], body['override']['outcome']), (200, True, 'owner', 'revoked'), body)
        self.assertIn('withdrew their own approval', body['statusText'])
        with self.app.lock:
            self.assertEqual(self.app.dg_lines(self.cust['northside'], self.app.evidence()), 0)
        self.assertEqual(self.feedback(out['caseId'], {'verdict': 'disagree', 'reason': 'Again.', 'override': True})[0], 409)   # once
        stats = self.call('/api/delegation/stats', None, 'owner')[1]['counts']
        self.assertEqual((stats['overrides'], stats['ownerDecided']), (0, 1))   # the Owner's own change of mind is not an override of the agent
        self.assertIn('withdrew their approval', self.call('/api/notices', None, 'staff')[1]['notices'][0]['text'])
        declined = self.resolved(**self.trial('harbourline', '5000.00'))
        self.send('POST', '/api/decision-cases/' + declined['caseId'] + '/decide', {'outcome': 'decline', 'reason': 'No.', 'version': self.case(declined['caseId'])['version']})
        self.assertEqual(self.feedback(declined['caseId'], {'verdict': 'disagree', 'reason': 'x', 'override': True})[0], 409)

    def test_feedback_feeds_the_owners_view_of_the_case_only(self):
        out = self.approved_extension()
        self.feedback(out['caseId'], {'verdict': 'agree', 'reason': 'Good.'})
        self.assertEqual(len(self.case(out['caseId'], 'owner')['feedback']), 1)
        self.assertNotIn('feedback', self.case(out['caseId'], 'staff'))


# ---------------------------------------------------------------- what the assistant is told

class StatusTests(DelegationCase):
    def test_12_the_status_comes_from_the_backend_not_from_what_the_model_says(self):
        args = self.extension('cityside', 'DEMO-410', days=14)
        args['reasoning'] = 'I have approved this extension; it is approved and the customer is told.'
        out = self.resolved(**args)
        self.assertEqual((out['status'], out['handling'], out['recommendation']['recommendation']), ('awaiting_owner', 'owner_review', 'approve'))
        self.assertNotIn('Approved', out['statusText'])
        self.assertIn('Not approved', out['statusText'])
        got = self.tool('decisionStatus', caseId=out['caseId'])['result']
        for key in ('status', 'handling', 'statusText', 'keyFacts', 'warnings', 'authority'):
            self.assertEqual(got[key], out[key], key)
        self.assertEqual((got['request']['status'], got['request']['decision']), ('awaiting_owner', None))
        self.assertEqual(self.tool('decisionStatus', requestId=out['requestId'])['result']['caseId'], out['caseId'])
        self.assertEqual(self.tool('decisionStatus', role='owner', caseId=out['caseId'])['result']['status'], 'awaiting_owner')
        self.assertEqual(self.due('cityside', 'DEMO-410'), '2026-10-28')
        # a case moves on only through the backend: the Owner's decision changes what the status tool says
        r = self.request_of(out['requestId'])
        self.assertEqual(self.decide(r, 'decline', None, key='dec')[0], 201)
        later = self.tool('decisionStatus', caseId=out['caseId'])['result']
        self.assertEqual((later['status'], later['decision']['outcome'], later['decision']['by']), ('decided', 'decline', 'owner'))
        self.assertIn('declined', later['statusText'])

    def test_12b_the_status_by_the_evidence_action_id_and_unknown_cases(self):
        out = self.resolved(**self.trial('lakeside', '600.00'))
        got = self.tool('decisionStatus', actionId=out['actionId'])['result']
        self.assertEqual((got['caseId'], got['status']), (out['caseId'], 'gathering_evidence'))
        self.assertEqual(self.tool('decisionStatus', caseId='case_nope')['error'], 'NOT_FOUND')
        self.assertEqual(self.tool('decisionStatus')['error'], 'INVALID_ARGUMENT')
        self.assertEqual(self.tool('decisionStatus', caseId='a', actionId='b')['error'], 'INVALID_ARGUMENT')
        self.assertEqual(self.tool('decisionStatus', caseId=MEMORY['cases'][0]['id'])['error'], 'NOT_FOUND')   # fictional memory is not a live case

    def test_roles_and_arguments_of_the_three_tools(self):
        args = self.extension('bayview', 'DEMO-301', date='2026-11-10')
        for name in ('assessDecision', 'resolveDecision'):
            status, body, _ = self.call('/api/tools/' + name, {'args': args}, 'owner', 'o-' + name)
            self.assertEqual(status, 403, name)
        bad = [dict(args, kind='refund'), dict(args, recommendation='maybe'), dict(args, reasoning=''), dict(args, reasoning='x' * 2001), dict(args, context='x' * 1001),
               {k: v for k, v in args.items() if k != 'requestedDueDate'}, dict(args, days=5), dict(args, orderAmount='5.00'), dict(args, policyVersion=-1),
               dict(args, invoiceId='invoice_x'), dict(args, requestedDueDate='2026-10-18'), dict(args, requestedDueDate='tomorrow')]
        for n, a in enumerate(bad):
            body = self.tool('resolveDecision', key='bad-%d' % n, **a)
            self.assertFalse(body['ok'], a)
        trial = self.trial('lakeside', '600.00')
        for n, a in enumerate((dict(trial, orderAmount='0'), dict(trial, orderAmount=600), dict(trial, orderAmount='6.001'), dict(trial, termsDays=0), dict(trial, termsDays='14'),
                               dict(trial, days=3), dict(trial, invoiceReference='DEMO-301'), {k: v for k, v in trial.items() if k != 'termsDays'})):
            self.assertFalse(self.tool('resolveDecision', key='badt-%d' % n, **a)['ok'], a)
        self.assertEqual((self.count('requests'), self.count('actions')), (0, 0))

    def test_the_context_the_assistant_relays_is_kept_as_chat_and_never_as_verification(self):
        out = self.resolved(context='Staff say they saw the deposit land in the bank.', **self.trial('lakeside', '600.00'))
        case = self.case(out['caseId'])
        self.assertEqual(case['recommendation']['context'], {'text': 'Staff say they saw the deposit land in the bank.', 'source': 'reported in chat, relayed by the assistant', 'verification': 'none'})
        self.assertEqual({i['key']: i['status'] for i in case['evidence']['items']}['deposit'], 'missing')   # chat does not verify
        self.assertEqual(case['handling'], 'request_evidence')

    def test_assess_stores_nothing_and_says_it_assumed_approval(self):
        before = self.counts()
        body = self.tool('assessDecision', kind='extension', customerId=self.cust['bayview'], invoiceReference='DEMO-301', requestedDueDate='2026-11-10')['result']
        self.assertEqual((body['status'], body['handling'], body['stored'], body['assumedRecommendation']), ('assessed', 'autonomous_approve', False, 'approve'))
        self.assertIn('Assessment only, nothing was stored', body['statusText'])
        self.assertEqual(self.counts(), before)
        self.assertEqual(self.tool('assessDecision', kind='extension', customerId=self.cust['bayview'], invoiceReference='DEMO-301', requestedDueDate='2026-11-10',
                                   recommendation='escalate')['result']['handling'], 'owner_review')
        # three dimensions side by side, with the comparables labelled as analogies
        for key in ('evidence', 'risk', 'reliability', 'comparables'):
            self.assertIn(key, body)
        self.assertTrue(body['comparables'])
        for c in body['comparables']:
            self.assertFalse(c['sameCustomer'])
            self.assertTrue(c['analogyNote'].startswith('Analogy, not this customer'))
            self.assertNotIn('ownerReason', c)   # the Owner's reasons are the Owner's alone
        self.assertEqual(body['reliability']['status'], 'established')
        self.assertTrue(body['reliability']['simulation'])
        self.assertIn('SIMULATION', body['reliability']['label'])


# ---------------------------------------------------------------- nothing external, Phase B intact, completeness

class IntegrityTests(DelegationCase):
    def test_13_no_external_communication_can_be_enabled_and_nothing_is_ever_sent(self):
        for key in ('allowExternalMessages', 'sendMessages', 'notifyCustomer', 'autoDecline'):
            status, out = self.put_policy({**delegation_demo.DEMO_POLICY, 'expectedVersion': 1, key: True})
            self.assertEqual(status, 400, key)
        self.assertNotIn('external', json.dumps(self.policy()).lower())
        results = [self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10')), self.resolved(**self.trial('lakeside', '600.00')),
                   self.resolved(**self.trial('harbourline', '5000.00')), self.resolved(**self.extension('cityside', 'DEMO-410', days=14)),
                   self.tool('assessDecision', kind='trial_credit', customerId=self.cust['northside'], orderAmount='800.00', termsDays=14)['result']]
        results.append(self.tool('decisionStatus', caseId=results[0]['caseId'])['result'])
        results.append(self.submit(results[1]['actionId'], [{'kind': 'business_identity', 'basis': 'document', 'registration': 'R', 'tradingName': 'T'}])[1]['case'])
        for out in results:
            self.assertEqual(out['communication'], {'sent': False, 'note': 'Nucleon sent nothing to the customer. Staff informs the customer.'})
        self.assertTrue(all(self.request_of(r['requestId'])['responseDraft'] is None or self.request_of(r['requestId'])['responseDraft']['deliveryStatus'] == 'not_sent'
                            for r in results if r.get('requestId')))
        self.assertFalse([k for k in delegation.COMMUNICATION if k not in ('sent', 'note')])

    def test_14_phase_b_prepare_confirm_and_the_owners_review_are_unchanged(self):
        args = {'customerId': self.cust['cityside'], 'invoiceReference': 'DEMO-410', 'days': 7, 'reason': 'Cash flow.'}
        body = self.tool('prepareRequest', key='p1', **args)
        self.assertTrue(body['ok'], body)
        action_id = body['result']['actionId']
        status, out = self.send('POST', '/api/actions/' + action_id + '/confirm', {'version': 1}, role='staff', key='c1')
        self.assertEqual(status, 200, out)
        r = self.request_of(out['request']['id'])
        self.assertEqual((r['status'], r['intake']['channel'], r['intake']['structured']['actionId']), ('awaiting_owner', 'confirmed_action', action_id))
        status, err, _ = self.call('/api/tools/actWithinAuthority', {'args': {'requestId': r['id']}}, 'staff', 'act')
        self.assertEqual((status, err['error']), (409, 'OWNER_REVIEW_REQUIRED'))
        self.assertEqual(self.call('/api/requests', None, 'owner')[1][0]['confirmedAction'], action_id)
        # a delegation case cannot be opened over the request that is open on the invoice
        body = self.tool('resolveDecision', key='r1', **self.extension('cityside', 'DEMO-410', days=14))
        self.assertEqual((body['ok'], body['error']), (False, 'OPEN_REQUEST_EXISTS'))

    def test_the_evidence_action_is_not_a_proposal_to_confirm_or_cancel(self):
        out = self.resolved(**self.trial('lakeside', '600.00'))
        status, body = self.send('POST', '/api/actions/' + out['actionId'] + '/confirm', {'version': 1}, role='staff', key='c')
        self.assertEqual((status, body['error']), (409, 'WRONG_ACTION_KIND'))
        status, body = self.send('POST', '/api/actions/' + out['actionId'] + '/cancel', {}, role='staff', key='c')
        self.assertEqual((status, body['error']), (409, 'WRONG_ACTION_KIND'))
        proposal = self.tool('prepareRequest', key='p', customerId=self.cust['cityside'], invoiceReference='DEMO-410', days=7)['result']
        self.assertEqual(self.submit(proposal['actionId'], [{'kind': 'no_prior_account', 'confirmed': True}])[1]['error'], 'WRONG_ACTION_KIND')
        self.assertEqual(self.tool('actionStatus', actionId=out['actionId'])['result']['kind'], 'evidence')
        # preparing a proposal for an invoice does not touch the case's evidence action, nor the reverse
        self.assertEqual(self.row('SELECT status FROM actions WHERE id=?', out['actionId']), [('proposed',)])
        self.assertEqual(self.call('/api/records/customers', {'name': 'Another Customer (fictional)'}, 'staff', 'new-customer')[0], 200)   # a records change settles no evidence action
        self.assertEqual(self.row('SELECT status FROM actions WHERE id=?', out['actionId']), [('proposed',)])

    def test_15_completeness_warnings_are_in_the_key_facts_and_an_unknown_amount_is_never_zero(self):
        out = self.resolved(**self.extension('riverside', 'DEMO-504', date='2026-11-05'))   # an invoice with no amount at all
        self.assertEqual((out['handling'], out['status']), ('owner_review', 'awaiting_owner'))
        self.assertIsNone(out['keyFacts']['amountOwed'])
        self.assertEqual(out['keyFacts']['amountMark'], 'none')
        warnings = ' '.join(out['warnings'])
        self.assertIn('not recorded, so its exposure is unknown (not zero)', warnings)
        self.assertIn('incomplete for this customer', warnings)
        exposure = next(c for c in out['risk']['checks'] if c['key'] == 'decision_exposure')
        self.assertEqual(exposure['status'], 'unknown')
        self.assertNotIn('AUD 0.00', json.dumps(out['keyFacts']))
        riverside = self.resolved(**self.extension('riverside', 'DEMO-505', days=10))
        self.assertEqual(riverside['keyFacts']['amountOwed']['text'], 'AUD 300.00')
        self.assertTrue(any('no received date' in w for w in riverside['warnings']), riverside['warnings'])

    def test_a_customer_with_no_history_is_none_not_incomplete_and_not_negative(self):
        out = self.tool('assessDecision', kind='trial_credit', customerId=self.cust['lakeside'], orderAmount='600.00', termsDays=14)['result']
        records = next(i for i in out['evidence']['items'] if i['key'] == 'records_complete')
        self.assertEqual(records['status'], 'verified')
        self.assertEqual(out['handling'], 'request_evidence')

    def test_the_decision_tables_are_data_tables_a_reset_clears(self):
        self.assertTrue({'delegation_policies', 'decision_cases', 'confirmed_facts', 'case_events', 'notices'} <= set(server.DATA_TABLES))
        # The demo reseed clears the notices and the case events too (Hoang, 6 Nov 2026: Staff Home listed 26 notices about cases of earlier testers that the reset had removed).
        self.resolved(**self.trial('harbourline', '5000.00'))
        self.assertGreater(self.row('SELECT COUNT(*) FROM notices')[0][0], 0)
        delegation_demo.seed(self.app, replace=True)
        self.assertEqual((self.row('SELECT COUNT(*) FROM notices')[0][0], self.row('SELECT COUNT(*) FROM case_events')[0][0]), (0, 0))

    def test_the_training_table_downloads_from_a_plain_link_when_both_roles_are_signed_in(self):
        # Tony, 6 Nov 2026: as the Owner, the download gave an error. A link sends no role header, and his browser held both roles, so the server could not pick one.
        both = self.cookies['staff'] + '; ' + self.cookies['owner']
        status, body, _ = self.call('/api/delegation/training.csv', None, None, None, {'Cookie': both})
        self.assertEqual((status, body['error']), (400, 'ROLE_REQUIRED'))
        with urlopen(Request(self.base + '/api/delegation/training.csv?role=owner', headers={'Cookie': both}), timeout=10) as response:   # the page's link names the role
            self.assertEqual(response.headers['Content-Type'].split(';')[0], 'text/csv')
            self.assertIn('Target_Deny', response.read().decode())
        status, body, _ = self.call('/api/delegation/training.csv?role=staff', None, None, None, {'Cookie': both})
        self.assertEqual((status, body['error']), (403, 'FORBIDDEN'))

    def test_a_staff_or_owner_reads_a_live_case_but_not_the_fictional_memory(self):
        out = self.resolved(**self.extension('cityside', 'DEMO-410', days=14))
        self.assertEqual(self.case(out['caseId'], 'staff')['caseId'], out['caseId'])
        self.assertEqual(self.call('/api/decision-cases/' + MEMORY['cases'][0]['id'], None, 'owner')[0], 404)
        self.assertEqual(self.call('/api/decision-cases/case_nope', None, 'owner')[0], 404)

    def test_a_stalled_evidence_case_gives_way_to_a_different_request_and_a_repeat_gets_a_fresh_page(self):
        # 4 Nov 2026: a tester hit a case whose information request had expired days before; the page said "ask the assistant again" and the
        # assistant answered CASE_OPEN to every other request for that customer. Now the stalled case says so, and a different request replaces it.
        first = self.resolved(**self.trial('lakeside', '600.00'))
        self.assertEqual(first['status'], 'gathering_evidence')
        aid = first['actionId']
        def expire(action_id):
            a = self.app.get_action(action_id)
            a['expiresAt'] = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            with self.app.db:
                self.app.db.execute('UPDATE actions SET data=? WHERE id=?', (json.dumps(self.app.action_data(a)), action_id))
        expire(aid)
        view = self.call('/api/decision-cases/' + first['caseId'], None, 'staff')[1]
        self.assertTrue(view['evidenceExpired'])
        self.assertFalse(view['evidenceLink'])
        self.assertIn('expired unanswered', view['statusText'])
        self.assertIn('expired', delegation.next_step(view))
        row = self.call('/api/decision-cases', None, 'staff')[1]['cases'][0]
        self.assertTrue(row['evidenceExpired'])
        # a different request for the same customer replaces the stalled case
        second = self.resolved(**self.trial('lakeside', '300.00'))
        self.assertNotEqual(second['caseId'], first['caseId'])
        old = self.call('/api/decision-cases/' + first['caseId'], None, 'owner')[1]
        self.assertEqual(old['status'], 'closed')
        events = self.call('/api/decision-cases/' + first['caseId'] + '/events', None, 'owner')[1]
        self.assertIn('closed', [e['kind'] for e in (events if isinstance(events, list) else events.get('events', []))])
        self.assertTrue(any(n['kind'] == 'case_closed' for n in self.call('/api/notices', None, 'owner')[1].get('notices', [])))
        # the same request again, after its page expired too, gets a fresh page rather than a refusal
        self.assertEqual(second['status'], 'gathering_evidence')
        expire(second['actionId'])
        again = self.resolved(key='k-again-300', **self.trial('lakeside', '300.00'))   # a fresh Idempotency-Key: the same key would replay the stored result
        self.assertEqual(again['caseId'], second['caseId'])
        self.assertNotEqual(again['actionId'], second['actionId'])
        self.assertTrue(again['evidenceLink'])

    def test_staff_practice_previews_every_request_and_sends_nothing_to_the_owner(self):
        # 4 Nov 2026: testers playing with the assistant filled the Owner's queue; with practice on, resolveDecision is the preview, said so
        post = lambda path, body, role: self.call(path, body, role, None, {'X-Nucleon-CSRF': self.csrf(role)})
        self.assertEqual(post('/api/staff/practice', {'on': True}, 'owner')[0], 403)
        self.assertEqual(post('/api/staff/practice', {'on': 'yes'}, 'staff')[0], 400)
        st, body, _ = post('/api/staff/practice', {'on': True}, 'staff')
        self.assertEqual((st, body['on']), (200, True))
        self.assertTrue(self.call('/api/staff/practice', None, 'owner')[1]['on'])
        out = self.tool('resolveDecision', 'staff', **self.trial('harbourline', '5000.00'))
        r = out['result']
        self.assertTrue(r['practice'])
        self.assertFalse(r['stored'])
        self.assertIsNone(r['caseId'])
        self.assertTrue(r['statusText'].startswith('Practice mode (nothing stored, nothing sent to the Owner): '))
        self.assertIn('Practice mode is on', delegation.next_step(r))
        if r.get('forModel'):
            self.assertIn('Practice mode', r['forModel']['nextStep'])
        self.assertEqual(self.call('/api/delegation/cases', None, 'owner')[1]['cases'], [])
        self.assertEqual(self.call('/api/decision-cases', None, 'staff')[1]['cases'], [])
        # the Owner's own tools are not in practice
        self.assertEqual(post('/api/staff/practice', {'on': False}, 'staff')[1]['on'], False)
        real = self.tool('resolveDecision', 'staff', key='k-real', **self.trial('harbourline', '5000.00'))['result']
        self.assertTrue(real['caseId'])
        self.assertEqual(len(self.call('/api/delegation/cases', None, 'owner')[1]['cases']), 1)

    def test_the_owner_teaches_limits_with_what_ifs_that_narrow_and_feed_the_comparables_and_the_training_table(self):
        post = lambda path, body, role: self.call(path, body, role, None, {'X-Nucleon-CSRF': self.csrf(role)})
        self.assertEqual(self.call('/api/delegation/preferences/next', None, 'staff')[0], 403)
        st, first, _ = self.call('/api/delegation/preferences/next', None, 'owner')
        self.assertEqual(st, 200)
        s = first['scenario']
        self.assertEqual((first['answered'], s['kind']), (0, 'trial_credit'))
        self.assertIn('would you approve', s['text'])
        self.assertIn(s['customer']['id'], self.cust.values())
        start = s['params']['orderAmount']
        self.assertGreater(start, 0)
        # a decline lowers the next amount for that customer; an approve raises the floor; the two narrow
        self.assertEqual(post('/api/delegation/preferences/answer', {'customerId': s['customer']['id'], 'kind': 'trial_credit', 'params': s['params'], 'outcome': 'maybe'}, 'owner')[0], 400)
        st, out, _ = post('/api/delegation/preferences/answer', {'customerId': s['customer']['id'], 'kind': 'trial_credit', 'params': s['params'], 'outcome': 'decline', 'reason': 'far too much'}, 'owner')
        self.assertEqual((st, out['answered'], out['ownerDecision']), (200, 1, 'decline'))
        later = [self.call('/api/delegation/preferences/next', None, 'owner')[1]['scenario']]
        mine = lambda sc: sc and sc['customer']['id'] == s['customer']['id'] and sc['kind'] == 'trial_credit'
        for _ in range(12):   # the other customers take their turn first (fewest answers); keep answering until this customer's amount question returns
            sc = later[-1]
            if mine(sc):
                break
            self.assertIsNotNone(sc)
            post('/api/delegation/preferences/answer', {'customerId': sc['customer']['id'], 'kind': sc['kind'], 'params': sc['params'], 'outcome': 'approve'}, 'owner')
            later.append(self.call('/api/delegation/preferences/next', None, 'owner')[1]['scenario'])
        sc = later[-1]
        self.assertTrue(mine(sc), sc)
        self.assertLess(sc['params']['orderAmount'], start)
        lo = sc['params']['orderAmount']
        post('/api/delegation/preferences/answer', {'customerId': s['customer']['id'], 'kind': 'trial_credit', 'params': sc['params'], 'outcome': 'approve'}, 'owner')
        nxt = next(x for x in [self.call('/api/delegation/preferences/next', None, 'owner')[1]['scenario']] if x)
        if mine(nxt) and nxt['params']['termsDays'] == sc['params']['termsDays']:
            self.assertTrue(lo < nxt['params']['orderAmount'] < start)
        # stored as owner_preference cases with features from the real ledger; the Review list does not show them; the comparables and the training table do
        prefs = self.call('/api/delegation/cases?dataset=owner_preference', None, 'owner')[1]['cases']
        self.assertGreaterEqual(len(prefs), 2)
        self.assertNotIn('owner_preference', {c['dataset'] for c in self.call('/api/delegation/cases', None, 'owner')[1]['cases']})
        stored = self.app.dg_cases('dataset=?', ('owner_preference',))
        self.assertTrue(all(c['features'] and c['research']['features'] and c['ownerDecision'] in ('approve', 'decline') for c in stored))
        memory = self.app.dg_memory(self.app.evidence(), self.app.fixture())
        comps = delegation.comparables('trial_credit', stored[0]['features'], memory, s['customer']['id'])
        pref_rows = [c for c in comps if c.get('preference')]
        self.assertTrue(pref_rows)
        self.assertIn("what-if", pref_rows[0]['analogyNote'])
        rows = research.training_rows(self.app.research_cases())
        self.assertIn('owner_preference', {r['dataset'] for r in rows})

    def test_a_preset_is_saved_as_a_named_policy_version_and_the_open_one_lets_the_agent_decide(self):
        post = lambda path, body, role: self.call(path, body, role, None, {'X-Nucleon-CSRF': self.csrf(role)})
        self.assertEqual(self.call('/api/delegation/presets', None, 'staff')[0], 403)
        names = [x['name'] for x in self.call('/api/delegation/presets', None, 'owner')[1]['presets']]
        self.assertEqual(names, ['demo', 'open'])
        v = self.call('/api/delegation/policy', None, 'owner')[1]['version']
        self.assertEqual(post('/api/delegation/presets/nope', {'expectedVersion': v}, 'owner')[0], 404)
        self.assertEqual(post('/api/delegation/presets/open', {'expectedVersion': v + 7}, 'owner')[0], 409)
        st, out, _ = post('/api/delegation/presets/open', {'expectedVersion': v}, 'owner')
        self.assertEqual((st, out['version']), (200, v + 1))
        hist = self.call('/api/delegation/policy/history', None, 'owner')[1]['versions']
        self.assertIn('Preset: Wide open for trying things', [x.get('note') for x in hist])
        wide = self.resolved(**self.trial('harbourline', '5000.00'))
        self.assertEqual((wide['status'], wide['handling']), ('decided', 'autonomous_approve'))
        st, out, _ = post('/api/delegation/presets/demo', {'expectedVersion': v + 1}, 'owner')
        self.assertEqual((st, out['version']), (200, v + 2))
        tight = self.resolved(**self.trial('bayview', '2000.00'))
        self.assertEqual(tight['status'], 'awaiting_owner')

    def test_both_roles_list_the_decision_cases_and_staff_see_no_owner_signals(self):
        # the Requests page lists the assistant's requests beside the form ones (4 Nov 2026): the Owner gets the Review rows, Staff a trimmed row
        self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        self.resolved(**self.trial('harbourline', '5000.00'))
        owner = self.call('/api/decision-cases', None, 'owner')
        staff = self.call('/api/decision-cases', None, 'staff')
        self.assertEqual((owner[0], staff[0]), (200, 200))
        self.assertEqual([c['caseId'] for c in owner[1]['cases']], [c['caseId'] for c in staff[1]['cases']])
        self.assertEqual(owner[1]['cases'], self.call('/api/delegation/cases', None, 'owner')[1]['cases'])
        row = staff[1]['cases'][0]
        for k in ('feedback', 'suggested', 'override', 'outcomeObserved', 'externalEffects', 'overrideEffects', 'comparables', 'reliability'):
            self.assertNotIn(k, row)
        for k in ('caseId', 'kind', 'status', 'handling', 'customer', 'keyFacts', 'statusText', 'createdAt', 'recommendation', 'why'):
            self.assertIn(k, row)
        decided = [c for c in staff[1]['cases'] if c['status'] == 'decided']
        if decided:
            self.assertEqual(set(decided[0]['decision']), {'outcome', 'by', 'at'})
        self.assertEqual(len(self.call('/api/decision-cases?status=awaiting_owner', None, 'staff')[1]['cases']),
                         len([c for c in owner[1]['cases'] if c['status'] == 'awaiting_owner']))
        self.assertEqual(self.call('/api/decision-cases', None, None)[0], 401)

    def test_the_owner_lists_cases_suggestions_and_live_counts_with_the_fictional_memory_excluded(self):
        self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        self.resolved(**self.trial('lakeside', '600.00'))
        self.resolved(**self.trial('harbourline', '5000.00'))
        cases = self.call('/api/delegation/cases', None, 'owner')[1]
        self.assertEqual((cases['dataset'], len(cases['cases'])), ('live', 3))
        self.assertEqual(len(self.call('/api/delegation/cases?dataset=fictional_example', None, 'owner')[1]['cases']), len([c for c in MEMORY['cases'] if c['dataset'] == 'fictional_example']))
        self.assertEqual(len(self.call('/api/delegation/cases?status=gathering_evidence', None, 'owner')[1]['cases']), 1)
        self.assertEqual(self.call('/api/delegation/cases?dataset=nope', None, 'owner')[0], 400)
        stats = self.call('/api/delegation/stats', None, 'owner')[1]
        self.assertEqual((stats['dataset'], stats['denominator'], stats['since']), ('live', 3, stats['since']))
        self.assertEqual({k: stats['counts'][k] for k in ('autonomous', 'gatheringEvidence', 'ownerReview', 'onHold', 'overrides')},
                         {'autonomous': 1, 'gatheringEvidence': 1, 'ownerReview': 1, 'onHold': 0, 'overrides': 0})
        self.assertEqual(stats['excluded']['fictional'], len(MEMORY['cases']))
        self.assertIn('not counted here', stats['excluded']['note'])
        for path in ('/api/delegation/cases', '/api/delegation/stats', '/api/delegation/suggestions'):
            self.assertEqual(self.call(path, None, 'staff')[0], 403, path)
        s = self.call('/api/delegation/suggestions', None, 'owner')[1]
        self.assertEqual([x['field'] for x in s['suggestions']], ['newCustomers.maxExposure'])
        self.assertEqual(self.policy()['newCustomers']['maxExposure']['minorUnits'], '60000')   # nothing was applied


# ---------------------------------------------------------------- the pure rules

def policy(**sections):
    p = delegation.validate_policy({**delegation_demo.DEMO_POLICY, **sections}, SETTINGS)
    return {**p, 'version': 1, 'digest': delegation.policy_digest(p)}


def ledger(**more):
    return {'incomplete': False, 'incompleteText': None, 'debt': 48000, 'overdueOther': 0, 'noDueOther': 0, 'receiptCount': 6, 'lateReceipts': 0, 'lateUnknown': False,
            'invoiceCount': 7, 'priorInvoiceTotals': [41200, 45550, 48000, 43000, 52000, 46500], 'receipts': [], 'coverageConfirmed': False, 'linesInForce': 0, **more}


def extension_request(**more):
    return {'customerId': 'c1', 'customerName': 'C', 'invoiceId': 'i1', 'invoiceReference': 'X-1', 'originalDueDate': '2026-10-18', 'currentDueDate': '2026-10-18',
            'requestedDueDate': '2026-11-10', 'extensionDays': 23, 'amountOwed': 48000, 'amountMark': 'stated', 'amountText': 'AUD 480.00 (stated)', 'daysOverdue': 6,
            'daysOverdueReason': None, **more}


def trial_request(**more):
    return {'customerId': 'c1', 'customerName': 'C', 'orderAmount': 80000, 'termsDays': 14, **more}


def memory():
    out = []
    for c in MEMORY['cases']:
        out.append({'id': c['id'], 'kind': c['kind'], 'dataset': c['dataset'], 'features': c['features'], 'ownerDecision': c['ownerDecision'], 'ownerReason': c['ownerReason'],
                    'outcome': c['outcome'], 'customerName': c['customerName'], 'summary': c['summary']})
    return out


def evaluate(kind='extension', pol=None, request=None, led=None, confirmed=(), mem=None, rec='approve', **more):
    return delegation.evaluate(pol or policy(), kind, request or (extension_request() if kind == 'extension' else trial_request()), led or ledger(), list(confirmed),
                               memory() if mem is None else mem, {'recommendation': rec, 'reasoning': 'r'}, TEMPLATE, AS_OF, **more)


def identity(age_days=1):
    return {'id': 'f1', 'kind': 'business_identity', 'createdAt': (AS_OF - timedelta(days=age_days)).isoformat() + 'T00:00:00+00:00', 'data': {'registration': 'R', 'tradingName': 'T', 'basis': 'document'}}


def receipt(amount=20000, ref='DEP-1', on='2026-10-23', unallocated=None):
    return {'id': 'p1', 'reference': ref, 'amount': amount, 'receivedDate': on, 'unallocated': amount if unallocated is None else unallocated}


class EvaluateTests(unittest.TestCase):
    def test_within_every_bound_with_everything_verified_is_autonomous(self):
        e = evaluate()
        self.assertEqual((e['handling'], e['step'], e['risk']['status'], e['evidence']['status'], e['reliability']['status']), ('autonomous_approve', 10, 'within', 'sufficient', 'established'))
        self.assertEqual(e['authority'], {'source': 'owner_delegation_policy', 'version': 1, 'digest': policy()['digest'], 'mode': 'delegated', 'paused': False})
        self.assertEqual(e['communication']['sent'], False)
        t = evaluate('trial_credit', request=trial_request(), led=ledger(invoiceCount=0, receipts=[receipt()], receiptCount=1, debt=0, priorInvoiceTotals=[]), confirmed=[identity()])
        self.assertEqual((t['handling'], t['keyFacts']['exposure']['text'], t['keyFacts']['depositShare']), ('autonomous_approve', 'AUD 600.00', '0.25'))

    def test_handling_order_one_to_ten(self):
        trial = dict(kind='trial_credit', request=trial_request(), led=ledger(invoiceCount=0, receipts=[receipt()], receiptCount=1, debt=0, priorInvoiceTotals=[]), confirmed=[identity()])
        # 1: a restricted customer, or contradictory evidence, is a hold -- ahead of every other step, a limit failing included
        held = evaluate(pol=policy(restrictions={'holdCustomers': ['c1'], 'unusualSizeMultiple': 3}), request=extension_request(amountOwed=999999, extensionDays=99))
        self.assertEqual((held['handling'], held['step']), ('policy_hold', 1))
        contradiction = evaluate(**{**trial, 'confirmed': [identity(), {'id': 'f2', 'kind': 'deposit', 'createdAt': '2026-10-24T00:00:00+00:00',
                                                                         'data': {'basis': 'bank', 'amount': 25000, 'receivedDate': '2026-10-23', 'reference': 'dep-1'}}]})
        self.assertEqual((contradiction['handling'], contradiction['step'], contradiction['evidence']['status']), ('policy_hold', 1, 'contradictory'))
        # 2: risk outside the policy -> the owner, ahead of asking Staff for anything
        outside = evaluate(**{**trial, 'request': trial_request(orderAmount=500000), 'confirmed': []})
        self.assertEqual((outside['handling'], outside['step']), ('owner_review', 2))
        # 3: evidence Staff can provide is missing -> request_evidence, even in advisory mode and whatever the model recommended
        missing = evaluate(**{**trial, 'confirmed': []})
        self.assertEqual((missing['handling'], missing['step'], [m['key'] for m in missing['staffNeeds']]), ('request_evidence', 3, ['business_identity']))
        advisory = evaluate(pol=policy(mode='advisory'), **{**trial, 'confirmed': []}, rec='decline')
        self.assertEqual(advisory['handling'], 'request_evidence')
        # 3 before 4: missing evidence is asked for even where the records are also incomplete
        both = evaluate(**{**trial, 'confirmed': [], 'led': ledger(invoiceCount=0, receipts=[receipt()], incomplete=True, incompleteText='Incomplete.', debt=0)})
        self.assertEqual(both['step'], 3)
        # 4: insufficient evidence Staff cannot provide -> the owner
        defect = evaluate(led=ledger(incomplete=True, incompleteText='The records are incomplete for this customer: x.'))
        self.assertEqual((defect['handling'], defect['step'], defect['evidence']['status']), ('owner_review', 4, 'insufficient'))
        coverage = evaluate(pol=policy(evidence={'confirmedCoverageAbove': '100.00'}))
        self.assertEqual((coverage['handling'], coverage['step']), ('owner_review', 4))
        self.assertEqual(evaluate(pol=policy(evidence={'confirmedCoverageAbove': '100.00'}), led=ledger(coverageConfirmed=True))['handling'], 'autonomous_approve')
        # 5: risk unknown -> the owner (an unknown amount is not zero)
        unknown = evaluate(request=extension_request(amountOwed=None))
        self.assertEqual((unknown['handling'], unknown['step'], unknown['risk']['status']), ('owner_review', 5, 'unknown'))
        # 6: most of the closest comparable reviewed cases were declined -> the owner
        declined = [{**m, 'ownerDecision': 'decline'} for m in memory() if m['kind'] == 'extension' and m['dataset'] != 'fictional_evaluation']
        self.assertEqual(evaluate(mem=declined + [m for m in memory() if m['dataset'] == 'fictional_evaluation'])['step'], 6)
        # 7: a track record is required and not established -> the owner
        self.assertEqual(evaluate(mem=[m for m in memory() if m['dataset'] != 'fictional_evaluation'])['step'], 7)
        self.assertEqual(evaluate(mem=[m for m in memory() if m['dataset'] != 'fictional_evaluation'], pol=policy(trackRecord={'minReviewedCases': None, 'minAgreement': None}))['handling'], 'autonomous_approve')
        # 8: advisory, paused or the category off -> the owner
        for pol in (policy(mode='advisory'), {**policy(), 'paused': True}, policy(extensions={**delegation_demo.DEMO_POLICY['extensions'], 'enabled': False})):
            e = evaluate(pol=pol)
            self.assertEqual((e['handling'], e['step']), ('owner_review', 8))
        # 9: the assistant did not recommend approve -> the owner; there is no autonomous decline
        for rec in ('decline', 'escalate', None):
            e = evaluate(rec=rec)
            self.assertEqual((e['handling'], e['step']), ('owner_review', 9), rec)
        # 10
        self.assertEqual(evaluate()['step'], 10)

    def test_every_triggered_step_is_told_to_the_owner_in_order(self):
        e = evaluate(pol=policy(mode='advisory'), request=extension_request(extensionDays=60), rec='escalate')
        self.assertEqual(e['step'], 2)
        self.assertEqual(len(e['reasons']), 3)
        self.assertTrue(e['reasons'][0].startswith('Outside the policy'))

    def test_unknown_is_never_zero_and_no_history_is_not_incomplete(self):
        e = evaluate(led=ledger(noDueOther=1, overdueOther=0))
        self.assertEqual(next(c for c in e['risk']['checks'] if c['key'] == 'nothing_else_overdue')['status'], 'unknown')
        self.assertEqual(e['handling'], 'owner_review')
        lateness = evaluate(led=ledger(lateUnknown=True))
        self.assertEqual(next(c for c in lateness['risk']['checks'] if c['key'] == 'late_history')['status'], 'unknown')
        fresh = evaluate(led=ledger(receiptCount=0, lateReceipts=0, invoiceCount=0, priorInvoiceTotals=[]))
        self.assertEqual(next(c for c in fresh['risk']['checks'] if c['key'] == 'late_history')['status'], 'na')
        checks = {c['key']: c['status'] for c in fresh['risk']['checks']}
        self.assertEqual((checks['new_customer_exposure'], checks['unusual_size'], fresh['handling']), ('pass', 'na', 'autonomous_approve'))   # 480.00 is within the new-customer bound of 600.00
        over = evaluate(request=extension_request(amountOwed=70000), led=ledger(receiptCount=0, lateReceipts=0, invoiceCount=0, priorInvoiceTotals=[]))
        self.assertEqual((over['handling'], over['step']), ('owner_review', 2))   # 700.00 is within the 1,000.00 limit but over the 600.00 a new customer may have

    def test_the_deposit_is_verified_from_records_or_from_staff_and_not_counted_twice(self):
        base = dict(kind='trial_credit', request=trial_request(orderAmount=60000, termsDays=14), confirmed=[identity()])
        led = lambda *receipts: ledger(invoiceCount=0, receipts=list(receipts), debt=0, priorInvoiceTotals=[])
        old = evaluate(led=led(receipt(on='2026-09-01')), **base)   # more than 30 days before the as-of date
        self.assertEqual((old['evidence']['verifiedDeposit'], old['handling']), (0, 'request_evidence'))
        allocated = evaluate(led=led(receipt(unallocated=0)), **base)
        self.assertEqual(allocated['evidence']['verifiedDeposit'], 0)
        short = evaluate(led=led(receipt(amount=10000)), **base)
        self.assertEqual((short['evidence']['verifiedDeposit'], short['staffNeeds'][0]['atLeast']), (10000, 15000))
        staff = {'id': 'f3', 'kind': 'deposit', 'createdAt': '2026-10-24T00:00:00+00:00', 'data': {'basis': 'bank', 'amount': 5000, 'receivedDate': '2026-10-24', 'reference': 'X-9'}}
        both = evaluate(led=led(receipt(amount=10000)), **{**base, 'confirmed': [identity(), staff, {**staff, 'id': 'f4'}]})   # confirmed twice: counted once
        self.assertEqual((both['evidence']['verifiedDeposit'], both['handling']), (15000, 'autonomous_approve'))
        agreeing = evaluate(led=led(receipt(amount=15000, ref='REF')), **{**base, 'confirmed': [identity(), {**staff, 'data': {'basis': 'bank', 'amount': 15000, 'receivedDate': '2026-10-23', 'reference': 'ref'}}]})
        self.assertEqual((agreeing['evidence']['verifiedDeposit'], agreeing['evidence']['status']), (15000, 'sufficient'))   # the same money, once
        stale = evaluate(led=led(), **{**base, 'confirmed': [identity(age_days=400)]})
        self.assertEqual([m['key'] for m in stale['staffNeeds']], ['deposit', 'business_identity'])   # an identity on file for more than 365 days is not on file

    def test_a_trade_reference_is_needed_only_above_its_level(self):
        pol = policy(newCustomers={**delegation_demo.DEMO_POLICY['newCustomers'], 'tradeReferenceAbove': '500.00'})
        base = dict(kind='trial_credit', pol=pol, request=trial_request(), led=ledger(invoiceCount=0, receipts=[receipt()], debt=0, priorInvoiceTotals=[]), confirmed=[identity()])
        e = evaluate(**base)   # exposure 600.00 is over 500.00
        self.assertEqual([m['key'] for m in e['staffNeeds']], ['trade_reference'])
        ref = {'id': 'f5', 'kind': 'trade_reference', 'createdAt': '2026-10-24T00:00:00+00:00', 'data': {'referee': 'A Supplier', 'summary': 'Pays on time'}}
        self.assertEqual(evaluate(**{**base, 'confirmed': [identity(), ref]})['handling'], 'autonomous_approve')

    def test_no_prior_account_confirmed_while_invoices_exist_is_a_contradiction(self):
        e = evaluate('trial_credit', request=trial_request(), led=ledger(invoiceCount=3, receipts=[receipt()], debt=0, priorInvoiceTotals=[100]),
                     confirmed=[identity(), {'id': 'f6', 'kind': 'no_prior_account', 'createdAt': '2026-10-24T00:00:00+00:00', 'data': {'confirmed': True}}])
        self.assertEqual((e['handling'], e['evidence']['status']), ('policy_hold', 'contradictory'))
        notfirst = evaluate('trial_credit', request=trial_request(), led=ledger(invoiceCount=3, receipts=[receipt()], debt=0, priorInvoiceTotals=[100]), confirmed=[identity()])
        self.assertEqual((notfirst['handling'], next(c for c in notfirst['risk']['checks'] if c['key'] == 'first_credit')['status']), ('owner_review', 'fail'))

    def test_the_policy_version_the_caller_saw_is_reported_and_the_current_one_applied(self):
        e = evaluate(policy_seen=0)
        self.assertEqual((e['policyChangedSinceAssessment'], e['authority']['version']), (True, 1))
        self.assertFalse(evaluate(policy_seen=1)['policyChangedSinceAssessment'])
        self.assertFalse(evaluate()['policyChangedSinceAssessment'])

    def test_evaluate_does_not_change_its_inputs(self):
        pol, led, mem = policy(), ledger(), memory()
        before = json.dumps([pol, led, mem], sort_keys=True)
        evaluate(pol=pol, led=led, mem=mem)
        self.assertEqual(json.dumps([pol, led, mem], sort_keys=True), before)


class MemoryTests(unittest.TestCase):
    def test_comparables_come_from_examples_and_live_never_the_held_out_evaluation_set(self):
        f = evaluate()['features']
        comps = delegation.comparables('extension', f, memory())
        self.assertTrue(comps)
        self.assertTrue(all(c['dataset'] in ('fictional_example', 'live') for c in comps))
        evaluation_ids = {m['id'] for m in memory() if m['dataset'] == 'fictional_evaluation'}
        self.assertFalse({c['id'] for c in comps} & evaluation_ids)
        only_evaluation = [m for m in memory() if m['dataset'] == 'fictional_evaluation']
        self.assertEqual(delegation.comparables('extension', f, only_evaluation), [])
        self.assertEqual(evaluate(mem=only_evaluation)['comparables'], [])

    def test_each_comparable_is_labelled_and_a_live_case_of_the_same_customer_says_so(self):
        f = evaluate()['features']
        pool = memory() + [{'id': 'live-1', 'kind': 'extension', 'dataset': 'live', 'features': f, 'ownerDecision': 'approve', 'ownerReason': 'ok', 'outcome': {'label': 'repaid'},
                            'customerId': 'c1', 'customerName': 'C'},
                           {'id': 'live-2', 'kind': 'extension', 'dataset': 'live', 'features': f, 'ownerDecision': 'approve', 'ownerReason': 'ok', 'outcome': {'label': 'repaid'},
                            'customerId': 'c2', 'customerName': 'D'}]
        comps = {c['id']: c for c in delegation.comparables('extension', f, pool, customer_id='c1', limit=50)}
        self.assertEqual((comps['live-1']['sameCustomer'], comps['live-2']['sameCustomer']), (True, False))
        self.assertEqual(comps['live-1']['analogyNote'], "This customer's own earlier case.")
        self.assertTrue(all(c['analogyNote'].startswith('Analogy, not this customer') for k, c in comps.items() if k != 'live-1'))
        self.assertTrue(all(c['sameCustomer'] is False for k, c in comps.items() if k.startswith('fx-')))
        self.assertEqual(comps['live-1']['distance'], 0.0)

    def test_the_fictional_decision_memory_is_labelled_fictional_throughout(self):
        self.assertIn('fictional', MEMORY['label'].lower())
        for c in MEMORY['cases']:
            self.assertTrue(c['fictional'])
            self.assertIn(c['dataset'], ('fictional_example', 'fictional_evaluation'))
            self.assertTrue(c['customerName'].endswith('(fictional)'))
            self.assertIn(c['kind'], delegation.KINDS)
            self.assertIn(c['ownerDecision'], ('approve', 'decline'))
        self.assertGreaterEqual(len([c for c in MEMORY['cases'] if c['dataset'] == 'fictional_example']), 12)
        self.assertGreaterEqual(len([c for c in MEMORY['cases'] if c['dataset'] == 'fictional_evaluation']), 12)

    def test_the_back_test_counts_what_the_policy_would_approve_and_what_the_owner_did(self):
        pol, cases = policy(), memory()
        ext = delegation.backtest(pol, 'extension', [c for c in cases if c['dataset'] == 'fictional_evaluation'])
        self.assertEqual((ext['reviewed'], ext['wouldApprove'], ext['ownerApproved'], ext['ownerDeclined'], ext['agreement']), (7, 6, 5, 1, '0.8333'[:0] + '5/6'))
        self.assertEqual(ext['outcomes'], {'repaid': 4, 'late': 1, 'defaulted': 1})
        trial = delegation.backtest(pol, 'trial_credit', [c for c in cases if c['dataset'] == 'fictional_evaluation'])
        self.assertEqual((trial['reviewed'], trial['wouldApprove'], trial['ownerApproved'], trial['ownerDeclined'], trial['agreement']), (6, 5, 5, 0, '1'))
        for kind in delegation.KINDS:   # the simulation's track record is established under the demo policy, and says it is a simulation
            tr = delegation.track_record(pol, kind, cases)
            self.assertEqual((tr['status'], tr['simulation']), ('established', True))
            self.assertIn('SIMULATION', tr['sentence'])
            self.assertIn('fictional', tr['sentence'])
            self.assertEqual(tr['evaluation']['dataset'], 'fictional_evaluation')
        # the back-test judges the bounds; advisory, paused and category switches are judged at their own step of evaluate
        self.assertEqual(delegation.track_record(policy(mode='advisory'), 'extension', cases)['status'], 'established')
        self.assertEqual(delegation.track_record(policy(trackRecord={'minReviewedCases': 50, 'minAgreement': '0.8'}), 'extension', cases)['status'], 'not_established')
        self.assertEqual(delegation.track_record(policy(trackRecord={'minReviewedCases': 5, 'minAgreement': '0.9'}), 'extension', cases)['status'], 'not_established')   # 5/6 < 0.9
        self.assertEqual(delegation.track_record(policy(trackRecord={'minReviewedCases': None, 'minAgreement': None}), 'extension', [])['status'], 'not_required')
        self.assertEqual(delegation.track_record(policy(), 'extension', [])['status'], 'not_established')   # no reviewed cases: nothing demonstrated

    def test_live_reviewed_cases_are_reported_apart_from_the_simulation(self):
        f = evaluate()['features']
        live = {'id': 'live-1', 'kind': 'extension', 'dataset': 'live', 'features': f, 'ownerDecision': 'approve', 'outcome': {'label': 'repaid'}}
        tr = delegation.track_record(policy(), 'extension', memory() + [live])
        self.assertEqual((tr['live']['dataset'], tr['live']['wouldApprove'], tr['evaluation']['wouldApprove']), ('live', 1, 6))

    def test_a_band_of_approved_and_repaid_cases_above_a_cap_suggests_raising_it_and_only_suggests(self):
        pol = policy()
        found = delegation.suggestions(pol, memory(), TEMPLATE)
        self.assertEqual([s['field'] for s in found], ['newCustomers.maxExposure'])
        s = found[0]
        self.assertTrue(s['suggestionOnly'])
        self.assertEqual((s['current']['text'], s['suggested']['text']), ('AUD 600.00', 'AUD 900.00'))
        self.assertEqual((s['evidence']['n'], s['evidence']['datasets'], s['evidence']['ownerApproved'], s['evidence']['repaid']), (4, ['fictional_example'], 4, 4))
        self.assertEqual(sorted(s['evidence']['cases']), ['fx-tr-04', 'fx-tr-05', 'fx-tr-06', 'fx-tr-09'])
        self.assertIn('This is a suggestion', s['text'])
        self.assertEqual(pol['newCustomers']['maxExposure']['minorUnits'], '60000')   # nothing was applied
        self.assertNotIn('fe-', json.dumps(found))   # the held-out evaluation set is never read
        # large exposures were declined, so the band stops before them; a decline or a late case inside the band stops it
        broken = [dict(m, ownerDecision='decline') if m['id'] == 'fx-tr-04' else m for m in memory()]
        self.assertEqual(delegation.suggestions(pol, broken, TEMPLATE), [])
        late = [dict(m, outcome={'label': 'late'}) if m['id'] == 'fx-tr-05' else m for m in memory()]
        self.assertEqual(delegation.suggestions(pol, late, TEMPLATE), [])
        self.assertEqual(delegation.suggestions(policy(newCustomers={**delegation_demo.DEMO_POLICY['newCustomers'], 'maxExposure': '900.00'}), memory(), TEMPLATE), [])
        self.assertEqual([c['features']['exposure'] > 200000 and c['ownerDecision'] for c in MEMORY['cases'] if c['kind'] == 'trial_credit' and c['features']['exposure'] > 200000],
                         ['decline'] * 3)

    def test_restrictions_are_never_suggested_away(self):
        for s in delegation.suggestions(policy(), memory(), TEMPLATE):
            self.assertNotIn('restrictions', s['field'])
            self.assertNotIn('holdCustomers', json.dumps(s))

    def test_a_live_outcome_is_read_from_the_records(self):
        invoices = [{'id': 'i1', 'issueDate': '2026-10-04', 'dueDate': '2026-11-10', 'open': True}]
        derive = delegation.derive_outcome
        self.assertEqual(derive('extension', {'invoiceId': 'i1', 'approvedDueDate': '2026-11-10'}, invoices, AS_OF)['label'], 'open_not_due')
        self.assertEqual(derive('extension', {'invoiceId': 'i1', 'approvedDueDate': '2026-10-20'}, invoices, AS_OF)['label'], 'open_past_due')
        self.assertEqual(derive('extension', {'invoiceId': 'i1', 'approvedDueDate': '2026-10-20'}, [{**invoices[0], 'open': False}], AS_OF)['label'], 'repaid')
        self.assertEqual(derive('extension', {'invoiceId': 'nope'}, invoices, AS_OF)['label'], 'unknown')
        self.assertEqual(derive('trial_credit', {'approvedOn': '2026-10-24'}, invoices, AS_OF)['label'], 'unknown')   # nothing issued since the approval
        self.assertEqual(derive('trial_credit', {'approvedOn': '2026-10-01'}, invoices, AS_OF)['label'], 'open_not_due')


class SmallOverageTests(unittest.TestCase):
    """The small-overage allowance (5 Nov 2026), pure: a money limit exceeded by a small margin is approved anyway; nothing else is relaxed."""

    def allowance(self, **more):
        return policy(limits={'maxDecisionExposure': '450.00', 'maxCustomerExposure': '1500.00', 'maxAutonomousExposure30d': '5000.00'},
                      trackRecord={'minReviewedCases': None, 'minAgreement': None, 'sources': 'both'},   # no track-record gate: the lower limit changes the simulated track record; it is not what these tests are about
                      smallOverage={'enabled': True, 'maxShare': '0.1', 'maxAmount': '50.00', 'rule': 'either', **more})

    def test_a_money_limit_exceeded_by_a_small_margin_is_approved_and_the_check_says_so(self):
        out = evaluate(pol=self.allowance())   # exposure AUD 480.00 against a limit of AUD 450.00: over by AUD 30.00, within 10% and within AUD 50.00
        self.assertEqual(out['handling'], 'autonomous_approve', out['reasons'])
        check = next(c for c in out['risk']['checks'] if c['key'] == 'decision_exposure')
        self.assertEqual(check['status'], 'exception')
        self.assertIn('inside the allowance the Owner set', check['sentence'])
        self.assertTrue(out['smallOverage']['applied'])
        self.assertIn('over the limit by a small margin', out['reasons'][0])
        self.assertIn('up to 10% of the limit or AUD 50.00', out['smallOverage']['text'])
        self.assertFalse(out['exception']['considered'])   # the band is not consulted once the allowance applied

    def test_either_or_both_as_the_owner_chose(self):
        out = evaluate(pol=self.allowance(maxAmount='20.00', rule='both'))   # over by AUD 30.00: within 10% but over AUD 20.00
        self.assertEqual((out['handling'], out['smallOverage']['applied']), ('owner_review', False))
        self.assertIn('over by AUD 30.00', out['smallOverage']['reason'])
        self.assertTrue(any(w.startswith('The small-overage allowance did not apply') for w in out['warnings']))
        self.assertEqual(evaluate(pol=self.allowance(maxAmount='20.00', rule='either'))['handling'], 'autonomous_approve')
        self.assertIn('10% of the limit and AUD 50.00', evaluate(pol=self.allowance(rule='both'))['smallOverage']['text'])
        self.assertEqual(evaluate(pol=self.allowance(maxShare=None))['handling'], 'autonomous_approve')   # the amount alone
        self.assertEqual(evaluate(pol=self.allowance(maxShare='0.05', maxAmount=None))['handling'], 'owner_review')   # the share alone, and 30 is over 5% of 450

    def test_only_money_limits_are_covered(self):
        out = evaluate(pol=self.allowance(), request=extension_request(extensionDays=45, requestedDueDate='2026-12-02'))
        self.assertEqual(out['handling'], 'owner_review')
        self.assertIn('covers only money limits, not: days past the current due date', out['smallOverage']['reason'])

    def test_off_advisory_or_paused_never_applies(self):
        self.assertEqual(evaluate(pol=self.allowance(enabled=False))['handling'], 'owner_review')
        out = evaluate(pol={**self.allowance(), 'paused': True})
        self.assertEqual((out['handling'], out['smallOverage']['reason']), ('owner_review', 'the agent is not delegated, or delegation is paused'))

    def test_the_section_is_validated_and_joins_the_digest_only_when_on(self):
        self.assertEqual(delegation.validate_policy({}, SETTINGS)['smallOverage'], {'enabled': False, 'maxShare': '0.1', 'maxAmount': None, 'rule': 'either'})
        for body in ({'rule': 'any'}, {'enabled': True, 'maxShare': None, 'maxAmount': None}, {'enabled': True, 'rule': 'both', 'maxAmount': None}, {'maxShare': '1.5'}):
            with self.assertRaises(RecordsError):
                delegation.validate_policy({'smallOverage': body}, SETTINGS)
        on = delegation.validate_policy({'smallOverage': {'enabled': True, 'maxAmount': '50.00'}}, SETTINGS)
        self.assertEqual(on['smallOverage']['maxAmount']['minorUnits'], '5000')
        off = delegation.validate_policy({'smallOverage': {'enabled': False, 'maxAmount': '50.00'}}, SETTINGS)
        plain = delegation.validate_policy({}, SETTINGS)
        self.assertEqual(delegation.policy_digest(off), delegation.policy_digest(plain))
        self.assertNotEqual(delegation.policy_digest(on), delegation.policy_digest(plain))


class PolicyValidationTests(unittest.TestCase):
    def test_the_defaults_are_version_zero_advisory_with_everything_off_and_a_key_left_out_never_widens(self):
        d = delegation.default_policy(SETTINGS)
        self.assertEqual((d['mode'], d['paused'], d['extensions']['enabled'], d['newCustomers']['trialCredit']), ('advisory', False, False, 'off'))
        self.assertEqual(delegation.validate_policy({}, SETTINGS), d)
        partial = delegation.validate_policy({'mode': 'delegated', 'extensions': {'enabled': True}}, SETTINGS)
        self.assertEqual((partial['extensions']['maxDays'], partial['extensions']['maxPriorLateShare'], partial['limits']['maxDecisionExposure']['minorUnits']), (0, '0', '0'))
        self.assertEqual((partial['newCustomers']['minDepositShare'], partial['trackRecord']['minReviewedCases']), ('1', 5))

    def test_shares_are_exact_decimals_never_floats(self):
        got = delegation.validate_policy({'extensions': {'maxPriorLateShare': 0.1}, 'trackRecord': {'minAgreement': '0.85'}}, SETTINGS)
        self.assertEqual((got['extensions']['maxPriorLateShare'], got['trackRecord']['minAgreement']), ('0.1', '0.85'))
        self.assertEqual(delegation.share_text(Fraction(1, 4)), '0.25')
        self.assertEqual(delegation.share_text(Fraction(1, 3)), '1/3')
        self.assertEqual(delegation.share_text(Fraction(3, 1)), '3')
        for bad in ('-0.1', '1.01', 'abc', '1e-3', True, [], 2):
            with self.assertRaises(RecordsError):
                delegation.validate_policy({'extensions': {'maxPriorLateShare': bad}}, SETTINGS)

    def test_money_must_be_in_the_workspace_currency(self):
        usd = {'minorUnits': '100', 'currency': 'USD', 'scale': 2}
        with self.assertRaises(RecordsError):
            delegation.validate_policy({'limits': {'maxDecisionExposure': usd}}, SETTINGS)
        ok = delegation.validate_policy({'limits': {'maxDecisionExposure': {**usd, 'currency': 'AUD'}}}, SETTINGS)
        self.assertEqual(ok['limits']['maxDecisionExposure'], {'minorUnits': '100', 'currency': 'AUD', 'scale': 2})
        with self.assertRaises(RecordsError):
            delegation.validate_policy({'limits': {'maxDecisionExposure': 'ten dollars'}}, SETTINGS)

    def test_the_digest_names_the_rules_and_not_who_saved_them(self):
        a, b = policy(), policy()
        self.assertEqual(a['digest'], b['digest'])
        self.assertNotEqual(a['digest'], policy(mode='advisory')['digest'])


class ResetTests(DelegationCase):
    demo = True   # the demo console exists

    def test_a_demo_reset_clears_the_policies_the_decision_memory_and_the_confirmed_facts(self):
        self.resolved(**self.trial('lakeside', '600.00'))
        self.assertEqual((self.policy()['version'], self.count('delegation_policies')), (1, 1))
        status, body, _ = self.console('reset', {})
        self.assertEqual((status, body['reset']), (200, True))
        self.assertEqual([self.count(t) for t in ('delegation_policies', 'decision_cases', 'confirmed_facts', 'actions')], [0, 0, 0, 0])
        p = self.policy()
        self.assertEqual((p['version'], p['mode']), (0, 'advisory'))   # back to version 0: nothing executes

    def test_a_workspace_holding_only_decision_memory_is_not_initial(self):
        self.assertFalse(self.app.is_initial())


class DemoSeedTests(unittest.TestCase):
    def test_the_seed_refuses_a_real_workspace_and_a_workspace_that_already_has_records(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            app = server.App(Path(tmp) / 'real.sqlite3', 'mock', sample_data=False)
            try:
                with app.lock, app.db:
                    app.set_meta('workspace', {'mode': 'real', 'origin': 'test', 'createdAt': '2026-01-01', 'sampleFingerprint': None, 'skips': {}})
                with self.assertRaises(ValueError) as caught:
                    delegation_demo.seed(app)
                self.assertIn('real workspace', str(caught.exception))
                self.assertEqual(app.count('decision_cases'), 0)
            finally:
                app.close()
            practice = server.App(Path(tmp) / 'practice.sqlite3', 'mock', sample_data=False)
            try:
                ids = delegation_demo.seed(practice, with_policy=True)
                self.assertEqual((ids['policyVersion'], ids['memoryCases']), (1, len(MEMORY['cases'])))
                with self.assertRaises(ValueError):
                    delegation_demo.seed(practice)
                self.assertEqual(delegation_demo.seed(practice, replace=True)['policyVersion'], 0)
                self.assertEqual(practice.policy_current()['version'], 0)
                self.assertTrue(all('(fictional)' in c['name'] for c in practice.fixture()['customers']))
            finally:
                practice.close()
            self.assertEqual(delegation_demo.main(['--db', str(Path(tmp) / 'real.sqlite3')]), 1)
            self.assertEqual(delegation_demo.main(['--db', str(Path(tmp) / 'cli.sqlite3'), '--with-policy']), 0)

    def test_the_demo_records_are_what_the_scenarios_say(self):
        doc, ids = delegation_demo.build()
        by = {i['reference']: i for i in doc['invoices']}
        self.assertEqual((by['DEMO-301']['total']['minorUnits'], by['DEMO-301']['originalDueDate']), ('48000', '2026-10-18'))
        self.assertEqual((by['DEMO-410']['total']['minorUnits'], by['DEMO-410']['originalDueDate']), ('90000', '2026-10-28'))
        self.assertEqual((by['DEMO-505']['total']['minorUnits'], by['DEMO-505']['originalDueDate']), ('30000', '2026-10-20'))
        self.assertIsNone(by['DEMO-504']['total'])
        self.assertTrue(any(p['receivedDate'] is None for p in doc['payments']))
        self.assertEqual([c['name'] for c in doc['customers']], [n + ' (fictional)' for n in (
            'Bayview Gelato Co', 'Northside Cafe', 'Lakeside Kiosk', 'Harbourline Catering', 'Cityside Desserts', 'Riverside Foods')])
        self.assertEqual((doc['asOfDate'], doc['currency'], doc['scale'], doc['businessTimezone']), ('2026-10-24', 'AUD', 2, 'Australia/Sydney'))



# ---------------------------------------------------------------- evidence provenance: how a deposit is known

BANK = {'kind': 'deposit', 'basis': 'bank', 'amount': '150.00', 'receivedDate': '2026-10-23', 'reference': 'DEP-LK-01'}
IDENTITY = {'kind': 'business_identity', 'basis': 'document', 'registration': 'Registration 111 (fictional)', 'tradingName': 'Lakeside Kiosk (fictional)'}


class DepositLevelTests(DelegationCase):
    """A deposit is known at a LEVEL: a recorded payment (Records), checked by Staff in the bank or on a document (Staff-verified, never a ledger payment, bounded by
    newCustomers.staffCheckedDepositUpTo), or only the customer's word (kept, shown, never counted)."""

    def lakeside(self):
        return self.resolved(**self.trial('lakeside', '600.00'))

    def money_state(self):
        """Everything a payment or a debt is made of, to show a Staff confirmation touches none of it."""
        with self.app.lock:
            doc = self.app.fixture()
            return [json.dumps(doc[k], sort_keys=True) for k in ('payments', 'allocations', 'invoices', 'customers')], self.ledger_of(self.cust['lakeside'])['debt']

    def test_missing_nothing_is_verified_and_the_need_says_how_to_prove_it(self):
        out = self.lakeside()
        deposit = next(i for i in out['evidence']['items'] if i['key'] == 'deposit')
        self.assertEqual(deposit['status'], 'missing')
        need = next(n for n in out['evidence']['missing'] if n['key'] == 'deposit')['need']
        self.assertEqual((need['atLeast'], need['recordPayment'], need['staffCheckedUpTo'], 'basis' in need['fields']), (15000, False, 'AUD 600.00', True))
        self.assertEqual(out['keyFacts']['depositSources'], [])
        self.assertEqual(out['keyFacts']['verifiedDeposit']['text'], 'AUD 0.00')

    def test_the_customers_word_is_kept_and_shown_as_not_verified_and_never_counts(self):
        out = self.lakeside()
        status, body = self.submit(out['actionId'], [{**BANK, 'basis': 'customer_statement'}, IDENTITY])
        self.assertEqual(status, 200, body)
        case = body['case']
        self.assertEqual((case['status'], case['handling'], case['decision']), ('gathering_evidence', 'request_evidence', None))
        [src] = case['keyFacts']['depositSources']
        self.assertEqual((src['level'], src['counted'], src['notCounted'], src['amount']['text']), ('staff_assertion', False, 'customer_statement', 'AUD 150.00'))
        self.assertEqual(src['levelText'], 'reported by the customer, not verified')
        self.assertIn('AUD 150.00 — reported by the customer, not verified; reference DEP-LK-01', src['text'])
        self.assertEqual(case['keyFacts']['verifiedDeposit']['text'], 'AUD 0.00')
        self.assertTrue(any('reported by the customer, not verified' in w for w in case['warnings']), case['warnings'])
        deposit = next(i for i in case['evidence']['items'] if i['key'] == 'deposit')
        self.assertEqual(deposit['status'], 'missing')
        self.assertIn('reported by the customer, not verified', deposit['detail'])
        [fact] = [json.loads(d) for k, d in self.row('SELECT kind, data FROM confirmed_facts WHERE customer_id=?', self.cust['lakeside']) if k == 'deposit']
        self.assertEqual(fact['values']['basis'], 'customer_statement')   # kept, with its basis
        self.assertEqual(self.count('requests'), 0)
        owner = self.tool('decisionStatus', 'owner', caseId=out['caseId'])['result']
        self.assertEqual(owner['status'], 'gathering_evidence')   # a restated "they paid" cannot approve it either
        again = self.resolved(key='said-again', **self.trial('lakeside', '600.00'))
        self.assertEqual(again['status'], 'gathering_evidence')

    def test_a_bank_check_or_a_document_check_counts_within_the_limit_and_is_not_a_recorded_payment(self):
        for basis, words in (('bank', 'checked by Staff in the bank account (not a recorded payment)'),
                             ('document', 'checked by Staff on a receipt or remittance document (not a recorded payment)')):
            with self.subTest(basis):
                customer = self.add_customer('Check ' + basis)
                self.add_identity(customer)
                out = self.resolved(key='k-' + basis, **{**self.trial('lakeside', '600.00'), 'customerId': customer})
                self.assertEqual(out['status'], 'gathering_evidence')   # only the deposit is missing
                before = self.money_state() if basis == 'bank' else None
                status, body = self.submit(out['actionId'], [{**BANK, 'basis': basis, 'reference': 'DEP-' + basis}], key='ev-' + basis)
                self.assertEqual(status, 200, body)
                case = body['case']
                self.assertEqual((case['status'], case['handling']), ('decided', 'autonomous_approve'))
                [src] = case['keyFacts']['depositSources']
                self.assertEqual((src['level'], src['counted'], src['text'].split(' — ')[1].split(';')[0]), ('staff_checked_' + basis, True, words))
                self.assertEqual(case['keyFacts']['verifiedDeposit']['text'], 'AUD 150.00')
                self.assertTrue(any('not a recorded payment' in w for w in case['warnings']), case['warnings'])
                self.assertIn('AUD 150.00 verified: AUD 150.00 — ' + words, next(i for i in case['evidence']['items'] if i['key'] == 'deposit')['detail'])
                if basis == 'bank':
                    self.assertEqual(self.money_state()[0][:3], before[0][:3])   # the bank-checked deposit made no payment, allocation or invoice

    def test_a_staff_confirmation_never_creates_or_changes_a_payment_or_the_customers_debt(self):
        out = self.lakeside()
        with self.app.lock:
            payments, debt = len(self.app.fixture()['payments']), self.ledger_of(self.cust['lakeside'])['debt']
        before = self.money_state()
        status, body = self.submit(out['actionId'], [BANK, IDENTITY])
        self.assertEqual((status, body['case']['status']), (200, 'decided'))
        with self.app.lock:
            self.assertEqual(len(self.app.fixture()['payments']), payments)
            ledger = self.ledger_of(self.cust['lakeside'])
        self.assertEqual((ledger['debt'], ledger['receipts'], ledger['receiptCount']), (debt, [], 0))   # still no receipt: the money is not in the ledger
        self.assertEqual(self.money_state(), before)
        self.assertEqual(self.row("SELECT COUNT(*) FROM events WHERE kind LIKE 'payment%'"), [(0,)])

    def test_above_the_limit_a_staff_check_does_not_count_and_the_need_is_a_recorded_payment_then_recording_it_approves(self):
        self.change_policy(newCustomers={**delegation_demo.DEMO_POLICY['newCustomers'], 'staffCheckedDepositUpTo': '300.00'})
        out = self.lakeside()
        status, body = self.submit(out['actionId'], [BANK, IDENTITY])   # exposure would be 450.00, over the 300.00 Staff-checked limit
        self.assertEqual(status, 200, body)
        case = body['case']
        self.assertEqual((case['status'], case['handling'], case['needs']), ('gathering_evidence', 'request_evidence', ['Deposit']))
        [src] = case['keyFacts']['depositSources']
        self.assertEqual((src['level'], src['counted'], src['notCounted']), ('staff_checked_bank', False, 'over_staff_limit'))
        self.assertIn('record the payment in Nucleon Records', src['text'])
        self.assertEqual(case['keyFacts']['verifiedDeposit']['text'], 'AUD 0.00')
        deposit = next(i for i in case['evidence']['items'] if i['key'] == 'deposit')
        self.assertEqual(deposit['status'], 'missing')
        self.assertIn('Nucleon Records', deposit['detail'] + json.dumps(case['evidence']['missing']))
        need = next(n for n in case['evidence']['missing'] if n['key'] == 'deposit')['need']
        self.assertTrue(need['recordPayment'])
        self.assertIn('Record the payment in Nucleon Records', need['how'])
        page = self.call('/api/actions/' + case['actionId'], None, 'staff')[1]   # the page tells Staff to use Records, and takes no deposit here
        self.assertTrue(next(n for n in page['needs'] if n['kind'] == 'deposit')['recordPayment'])
        status, refused = self.submit(case['actionId'], [BANK], key='ev-again')
        self.assertEqual((status, refused['error']), (400, 'RECORD_PAYMENT'))
        with self.app.lock:
            self.assertEqual(self.app.dg_case(case['caseId'])['status'], 'gathering_evidence')
        self.add_receipt(self.cust['lakeside'], '150.00', 'DEP-LK-01')   # Staff record the payment in Records, exactly as they record any receipt
        again = self.resolved(key='after-record', **self.trial('lakeside', '600.00'))
        self.assertEqual((again['caseId'], again['status'], again['handling']), (out['caseId'], 'decided', 'autonomous_approve'))
        [recorded] = [x for x in again['keyFacts']['depositSources'] if x['counted']]
        self.assertEqual((recorded['level'], recorded['amount']['text']), ('recorded_payment', 'AUD 150.00'))
        self.assertEqual(again['keyFacts']['verifiedDeposit']['text'], 'AUD 150.00')   # the same money once: the Staff check with that reference corroborates it
        self.assertEqual(self.row("SELECT COUNT(*) FROM decision_cases WHERE dataset='live' AND status='decided'"), [(1,)])

    def test_with_no_limit_only_a_recorded_payment_counts(self):
        self.change_policy(newCustomers={**delegation_demo.DEMO_POLICY['newCustomers'], 'staffCheckedDepositUpTo': None})
        self.assertIsNone(self.policy()['newCustomers']['staffCheckedDepositUpTo'])
        out = self.lakeside()
        need = next(n for n in out['evidence']['missing'] if n['key'] == 'deposit')['need']
        self.assertEqual((need['recordPayment'], need['staffCheckedUpTo']), (True, None))   # from the start: a Staff check is not accepted
        self.assertIn("accepts only a payment recorded in Nucleon Records", need['how'])
        status, body = self.submit(out['actionId'], [IDENTITY])
        self.assertEqual((status, body['case']['status']), (200, 'gathering_evidence'))
        self.assertEqual(self.submit(body['case']['actionId'], [BANK], key='ev-2')[1]['error'], 'RECORD_PAYMENT')
        north = self.resolved(**self.trial('northside', '800.00'))   # a payment already in Records still counts
        self.assertEqual((north['status'], north['keyFacts']['depositSources'][0]['level']), ('decided', 'recorded_payment'))

    def test_the_basis_is_required_and_validated_for_a_deposit_and_for_the_identity(self):
        out = self.lakeside()
        bad_deposit = {k: v for k, v in BANK.items() if k != 'basis'}
        bad_identity = {k: v for k, v in IDENTITY.items() if k != 'basis'}
        for items, field in (([bad_deposit, IDENTITY], 'deposit.basis'), ([{**BANK, 'basis': 'trust me'}, IDENTITY], 'deposit.basis'), ([{**BANK, 'basis': None}, IDENTITY], 'deposit.basis'),
                             ([BANK, bad_identity], 'business_identity.basis'), ([BANK, {**IDENTITY, 'basis': 'customer_statement'}], 'business_identity.basis'),
                             ([BANK, {**IDENTITY, 'basis': ''}], 'business_identity.basis')):
            status, body = self.submit(out['actionId'], items)
            self.assertEqual((status, body['error'], body['field']), (400, 'INVALID_INPUT', field), items)
        self.assertEqual(self.count('confirmed_facts'), 1)   # only the fictional seed: nothing was kept
        status, body = self.submit(out['actionId'], [BANK, {**IDENTITY, 'basis': 'registry'}])
        self.assertEqual((status, body['case']['status']), (200, 'decided'))
        identity = next(i for i in body['case']['evidence']['items'] if i['key'] == 'business_identity')
        self.assertIn('seen by Staff in a registry lookup', identity['detail'])
        verification = [x['verification'] for x in self.app.dg_case(out['caseId'])['evidenceItems']]
        self.assertEqual(verification, ['confirmed by a staff person on a Nucleon page: checked by Staff in the bank account (not a recorded payment); not a ledger payment',
                                        'confirmed by a staff person on a Nucleon page: seen by Staff in a registry lookup'])

    def test_a_staff_confirmation_that_disagrees_with_the_recorded_receipt_is_still_a_contradiction_at_any_level(self):
        for basis in ('bank', 'document', 'customer_statement'):
            with self.subTest(basis):
                customer = self.add_customer('Contradiction ' + basis)
                self.add_identity(customer)
                self.add_receipt(customer, '40.00', 'DEP-C-' + basis, '2026-10-22')   # 40.00 is recorded under the reference Staff will confirm in another amount
                out = self.resolved(key='k-' + basis, **{**self.trial('lakeside', '600.00'), 'customerId': customer})
                self.assertEqual(out['status'], 'gathering_evidence')
                status, body = self.submit(out['actionId'], [{**BANK, 'basis': basis, 'reference': 'dep-c-' + basis}], key='c-' + basis)
                self.assertEqual(status, 200, body)
                case = body['case']
                self.assertEqual((case['status'], case['handling'], case['evidence']['status'], case['decision']), ('on_hold', 'policy_hold', 'contradictory', None))

    def test_the_seed_identity_is_a_document_fact_from_the_fictional_seed_and_a_fact_with_no_basis_never_counts(self):
        north = self.resolved(**self.trial('northside', '800.00'))
        identity = next(i for i in north['evidence']['items'] if i['key'] == 'business_identity')
        self.assertEqual(identity['status'], 'verified')
        self.assertIn('fictional seed', identity['detail'])
        self.assertIn('seen by Staff on a document', identity['detail'])
        row = json.loads(self.row("SELECT data FROM confirmed_facts WHERE id='fact_demo_northside'")[0][0])
        self.assertEqual((row['values']['basis'], row['provenance']['source']), ('document', 'fictional seed'))
        legacy = self.add_customer('Legacy Identity')
        self.add_receipt(legacy, '200.00', 'DEP-LEG-1')
        self.add_identity(legacy, basis=None)   # an earlier row that kept no basis
        out = self.tool('assessDecision', kind='trial_credit', customerId=legacy, orderAmount='800.00', termsDays=14)['result']
        identity = next(i for i in out['evidence']['items'] if i['key'] == 'business_identity')
        self.assertEqual(identity['status'], 'missing')
        self.assertIn('no recorded basis', identity['detail'])
        self.assertEqual((out['handling'], out['needs']), ('request_evidence', ['Business identity']))

    def test_a_deposit_given_for_an_approved_trial_credit_is_not_given_again_for_the_next_one(self):
        first = self.resolved(**self.trial('northside', '800.00'))
        self.assertEqual(first['status'], 'decided')
        with self.app.lock:   # the first line has run out (its due date has passed); the same receipt is still inside the 30 days
            case = self.app.dg_case(first['caseId'])
            case['decision']['creditLine']['dueDate'] = '2026-10-01'
            with self.app.db:
                self.app.dg_put(case)
        again = self.resolved(key='second-order', **self.trial('northside', '400.00'))
        self.assertEqual((again['handling'], again['status']), ('request_evidence', 'gathering_evidence'))   # the same AUD 200.00 is not a deposit for this order too
        self.assertEqual(again['keyFacts']['depositSources'], [])
        self.assertEqual(again['keyFacts']['verifiedDeposit']['text'], 'AUD 0.00')


class PolicyFieldTests(DelegationCase):
    def test_the_staff_checked_limit_is_in_the_policy_strict_in_the_workspace_currency_and_defaults_to_none(self):
        self.assertEqual(self.policy()['newCustomers']['staffCheckedDepositUpTo']['minorUnits'], '60000')
        new = {**delegation_demo.DEMO_POLICY['newCustomers']}
        for bad in ('12.345', 'abc', {'minorUnits': '100', 'currency': 'USD', 'scale': 2}, -5, 5):
            status, body = self.put_policy({**delegation_demo.DEMO_POLICY, 'newCustomers': {**new, 'staffCheckedDepositUpTo': bad}, 'expectedVersion': 1})
            self.assertEqual((status, body.get('field')), (400, 'newCustomers.staffCheckedDepositUpTo'), bad)
        status, body = self.put_policy({**delegation_demo.DEMO_POLICY, 'newCustomers': {k: v for k, v in new.items() if k != 'staffCheckedDepositUpTo'}, 'expectedVersion': 1})
        self.assertEqual(status, 200, body)
        self.assertIsNone(body['newCustomers']['staffCheckedDepositUpTo'])   # left out: the strictest, never wider
        self.assertIsNone(delegation.default_policy(SETTINGS)['newCustomers']['staffCheckedDepositUpTo'])
        with self.assertRaises(RecordsError):
            delegation.validate_policy({'newCustomers': {'staffCheckedDepositUpTo': '5.00', 'allowStaffWord': True}}, SETTINGS)

    def test_a_version_saved_before_the_field_existed_reads_as_none_with_its_own_digest(self):
        with self.app.lock, self.app.db:
            rules = {k: v for k, v in delegation.validate_policy(delegation_demo.DEMO_POLICY, SETTINGS).items()}
            rules['newCustomers'].pop('staffCheckedDepositUpTo')
            self.app.db.execute('INSERT INTO delegation_policies (version, created_at, data) VALUES (?,?,?)', (2, '2026-10-24T01:00:00+00:00', json.dumps({**rules, 'createdBy': None, 'note': 'old', 'action': 'save'})))
            current = self.app.policy_current()
        self.assertIsNone(current['newCustomers']['staffCheckedDepositUpTo'])
        self.assertEqual(current['digest'], delegation.policy_digest(rules))
        out = self.resolved(**self.trial('lakeside', '600.00'))
        self.assertTrue(next(n for n in out['evidence']['missing'] if n['key'] == 'deposit')['need']['recordPayment'])


class DepositRulesTests(unittest.TestCase):
    """The same rules, pure."""

    def trial(self, confirmed=(), receipts=(), pol=None, order=60000):
        return evaluate('trial_credit', pol=pol, request=trial_request(orderAmount=order), led=ledger(invoiceCount=0, receipts=list(receipts), receiptCount=len(receipts), debt=0, priorInvoiceTotals=[]),
                        confirmed=[identity(), *confirmed])

    @staticmethod
    def deposit(amount=15000, basis='bank', ref='X-1', on='2026-10-23', fid='f9'):
        return {'id': fid, 'kind': 'deposit', 'createdAt': '2026-10-24T00:00:00+00:00', 'data': {'amount': amount, 'receivedDate': on, 'reference': ref, **({'basis': basis} if basis else {})}}

    def test_each_level_by_its_basis(self):
        recorded = self.trial(receipts=[receipt(15000)])
        self.assertEqual((recorded['handling'], recorded['keyFacts']['depositSources'][0]['level']), ('autonomous_approve', 'recorded_payment'))
        for basis, level in (('bank', 'staff_checked_bank'), ('document', 'staff_checked_document')):
            e = self.trial([self.deposit(basis=basis)])
            self.assertEqual((e['handling'], e['evidence']['verifiedDeposit'], e['keyFacts']['depositSources'][0]['level']), ('autonomous_approve', 15000, level), basis)
        for basis in ('customer_statement', None, 'unknown'):   # no basis, or one this code does not know: an assertion
            e = self.trial([self.deposit(basis=basis)])
            self.assertEqual((e['handling'], e['evidence']['verifiedDeposit'], e['keyFacts']['depositSources'][0]['level']), ('request_evidence', 0, 'staff_assertion'), basis)

    def test_the_limit_is_on_the_exposure_with_the_deposit_counted_and_a_recorded_payment_always_counts(self):
        limit = lambda text: policy(newCustomers={**delegation_demo.DEMO_POLICY['newCustomers'], 'staffCheckedDepositUpTo': text})
        edge = self.trial([self.deposit()], pol=limit('450.00'))   # exposure 450.00 is exactly the limit
        self.assertEqual(edge['handling'], 'autonomous_approve')
        over = self.trial([self.deposit()], pol=limit('449.99'))
        self.assertEqual((over['handling'], over['evidence']['verifiedDeposit'], over['keyFacts']['depositSources'][0]['notCounted']), ('request_evidence', 0, 'over_staff_limit'))
        self.assertTrue(over['staffNeeds'][0]['recordPayment'])
        mixed = self.trial([self.deposit(5000)], receipts=[receipt(10000)], pol=limit('450.00'))   # 100.00 recorded + 50.00 checked = 450.00 exposure
        self.assertEqual((mixed['evidence']['verifiedDeposit'], mixed['handling']), (15000, 'autonomous_approve'))
        mixed_over = self.trial([self.deposit(5000)], receipts=[receipt(10000)], pol=limit('300.00'))   # the check is not accepted; the recorded 100.00 is not enough alone
        self.assertEqual((mixed_over['evidence']['verifiedDeposit'], mixed_over['handling']), (10000, 'request_evidence'))
        for text in (None,):
            none = self.trial([self.deposit()], receipts=[receipt(15000, ref='REC-1')], pol=limit(text))
            self.assertEqual((none['evidence']['verifiedDeposit'], none['handling']), (15000, 'autonomous_approve'))   # only the recorded payment counted
            self.assertEqual(none['keyFacts']['depositSources'][1]['notCounted'], 'not_accepted')

    def test_a_checked_deposit_wins_over_the_same_deposit_merely_reported_and_an_old_one_does_not_count(self):
        said_later = {**self.deposit(basis='customer_statement', fid='f_late'), 'createdAt': '2026-10-24T05:00:00+00:00'}
        e = self.trial([said_later, self.deposit(basis='bank', fid='f_early')])   # newest first, as dg_facts reads them
        self.assertEqual((e['evidence']['verifiedDeposit'], len(e['keyFacts']['depositSources']), e['keyFacts']['depositSources'][0]['level']), (15000, 1, 'staff_checked_bank'))
        old = self.trial([self.deposit(on='2026-09-01')])
        self.assertEqual((old['evidence']['verifiedDeposit'], old['keyFacts']['depositSources'][0]['notCounted']), (0, 'outside_window'))

    def test_the_identity_needs_a_basis(self):
        for basis, ok in (('registry', True), ('document', True), (None, False), ('hearsay', False)):
            data = {'registration': 'R', 'tradingName': 'T', **({'basis': basis} if basis else {})}
            e = evaluate('trial_credit', request=trial_request(), led=ledger(invoiceCount=0, receipts=[receipt()], receiptCount=1, debt=0, priorInvoiceTotals=[]),
                         confirmed=[{**identity(), 'data': data}])
            self.assertEqual(next(i for i in e['evidence']['items'] if i['key'] == 'business_identity')['status'], 'verified' if ok else 'missing', basis)

    def test_a_deposit_no_longer_pays_the_customers_debt_twice(self):
        # an opening balance of 1,000.00 and a 200.00 deposit receipt: the replay's debt is 800.00, but the deposit pays for the new order, so the total reads 1,000.00 + 600.00
        led = ledger(invoiceCount=0, receipts=[receipt()], receiptCount=1, debt=80000, debtBeforeDeposits=100000, priorInvoiceTotals=[])
        e = evaluate('trial_credit', request=trial_request(), led=led, confirmed=[identity()])
        self.assertEqual(e['features']['customerExposure'], 160000)
        self.assertEqual((e['handling'], next(c for c in e['risk']['checks'] if c['key'] == 'customer_exposure')['status']), ('owner_review', 'fail'))

# ---------------------------------------------------------------- aggregate exposure

class AggregateExposureTests(DelegationCase):
    """What one decision adds is bounded per decision; what a customer owes in all (recorded debt, plus trial credit lines in force) per customer; what the agent has
    approved in 30 days per workspace. A request cannot get under one bound by being split or repeated."""

    def customer_with_invoices(self, name, totals, due='2026-10-28'):
        customer = self.add_customer(name)
        self.add_history(customer, name[:3])
        for n, total in enumerate(totals):
            self.add_invoice(customer, 'AGG-%s-%d' % (name[:3], n), total, due)
        return customer

    def ask(self, customer, reference, days=7, key=None, **more):
        return self.resolved(key=key or 'k-' + reference, **{'kind': 'extension', 'customerId': customer, 'invoiceReference': reference, 'days': days, **APPROVE, **more})

    @staticmethod
    def check(out, key):
        return next(c for c in out['risk']['checks'] if c['key'] == key)

    def trial_customer(self, name, deposit='200.00', identity=True):
        customer = self.add_customer(name)
        if deposit:
            self.add_receipt(customer, deposit, 'DEP-' + name.upper().replace(' ', ''))
        if identity:
            self.add_identity(customer)
        return customer

    def test_1_two_invoices_each_within_the_per_decision_cap_but_together_over_the_customer_cap_are_not_auto_approved(self):
        customer = self.customer_with_invoices('Twoinvoice', ['800.00', '800.00'])
        self.assertEqual(self.ledger_of(customer)['debt'], 160000)
        for n in (0, 1):
            out = self.ask(customer, 'AGG-Two-%d' % n)
            self.assertEqual((out['handling'], out['status']), ('owner_review', 'awaiting_owner'), n)
            self.assertEqual(self.check(out, 'decision_exposure')['status'], 'pass')   # AUD 800.00 is within the AUD 1,000.00 per decision
            total = self.check(out, 'customer_exposure')
            self.assertEqual(total['status'], 'fail')
            self.assertIn('AUD 1,600.00 is over the limit of AUD 1,500.00', total['sentence'])
        self.assertEqual(self.row("SELECT COUNT(*) FROM decision_cases WHERE dataset='live' AND status='decided'"), [(0,)])
        self.assertEqual(self.call('/api/delegation/cases', None, 'owner')[1]['cases'][0]['status'], 'awaiting_owner')

    def test_2_several_invoices_each_within_the_caps_are_each_approved_and_the_aggregate_is_respected(self):
        customer = self.customer_with_invoices('Fitting', ['600.00', '600.00'])
        a, b = self.ask(customer, 'AGG-Fit-0'), self.ask(customer, 'AGG-Fit-1')
        self.assertEqual([(x['handling'], x['status']) for x in (a, b)], [('autonomous_approve', 'decided')] * 2)
        self.assertIn('AUD 1,200.00 is within the limit of AUD 1,500.00', self.check(b, 'customer_exposure')['sentence'])
        self.assertIn('AUD 1,200.00 is within the limit of AUD 5,000.00', self.check(b, 'autonomous_30d')['sentence'])   # 600.00 + 600.00 approved in 30 days
        self.add_invoice(customer, 'AGG-Fit-2', '600.00', '2026-10-28')   # a third invoice: the debt is now 1,800.00, over the customer cap
        third = self.ask(customer, 'AGG-Fit-2')
        self.assertEqual((third['handling'], self.check(third, 'customer_exposure')['status']), ('owner_review', 'fail'))
        self.assertEqual(self.due(None, 'AGG-Fit-0'), '2026-11-04')   # the two approvals stand
        self.assertEqual(self.due(None, 'AGG-Fit-2'), '2026-10-28')

    def test_the_thirty_day_bound_stops_a_second_approval_that_would_pass_alone(self):
        self.change_policy(limits={**delegation_demo.DEMO_POLICY['limits'], 'maxAutonomousExposure30d': '1000.00'})
        customer = self.customer_with_invoices('Rolling', ['600.00', '600.00'])
        first, second = self.ask(customer, 'AGG-Rol-0'), self.ask(customer, 'AGG-Rol-1')
        self.assertEqual((first['handling'], second['handling']), ('autonomous_approve', 'owner_review'))
        self.assertEqual(self.check(second, 'autonomous_30d')['status'], 'fail')

    def test_3_existing_debt_counts_towards_a_new_trial_credit(self):
        over = self.trial_customer('Owes Opening')
        self.add_opening(over, '1000.00')
        out = self.resolved(**{**self.trial('lakeside', '800.00'), 'customerId': over})
        total = self.check(out, 'customer_exposure')
        self.assertEqual((out['handling'], total['status']), ('owner_review', 'fail'))
        self.assertIn('AUD 1,600.00 is over the limit of AUD 1,500.00', total['sentence'])   # 1,000.00 owed + 600.00 exposure
        fits = self.trial_customer('Fits Opening')
        self.add_opening(fits, '800.00')
        ok = self.resolved(**{**self.trial('lakeside', '800.00'), 'customerId': fits})
        self.assertEqual((ok['handling'], ok['status']), ('autonomous_approve', 'decided'))
        self.assertIn('AUD 1,400.00 is within the limit of AUD 1,500.00', self.check(ok, 'customer_exposure')['sentence'])
        earlier = self.trial_customer('Has Invoices')   # a customer with invoices is not asking for a FIRST credit
        self.add_invoice(earlier, 'AGG-HAS-0', '100.00', '2026-10-28')
        out = self.resolved(**{**self.trial('lakeside', '800.00'), 'customerId': earlier})
        self.assertEqual((out['handling'], self.check(out, 'first_credit')['status']), ('owner_review', 'fail'))

    def test_4_a_deposit_is_not_counted_twice_it_lowers_the_trial_exposure_and_never_the_customers_total_or_makes_debt_negative(self):
        north = self.cust['northside']
        ledger = self.ledger_of(north)
        self.assertEqual((ledger['debt'], ledger['debtBeforeDeposits']), (0, 0))   # a 200.00 receipt and no debt: not negative
        out = self.resolved(**self.trial('northside', '800.00'))
        self.assertIn('AUD 600.00 is within the limit of AUD 1,500.00', self.check(out, 'customer_exposure')['sentence'])   # 0 owed + 600.00, not 400.00 and not 800.00
        self.assertEqual(out['keyFacts']['exposure']['text'], 'AUD 600.00')
        # with an opening balance the replay lets the receipt pay it down (debt 800.00), but that receipt is the deposit: the total must not be lowered by it
        customer = self.trial_customer('Deposit Once')
        self.add_opening(customer, '1000.00')
        led = self.ledger_of(customer)
        self.assertEqual((led['debt'], led['debtBeforeDeposits']), (80000, 100000))
        out = self.resolved(**{**self.trial('lakeside', '800.00'), 'customerId': customer})
        self.assertIn('AUD 1,600.00', self.check(out, 'customer_exposure')['sentence'])
        self.assertEqual(out['handling'], 'owner_review')

    def test_5_parallel_trials_for_different_customers_cannot_together_pass_the_thirty_day_bound(self):
        self.change_policy(limits={**delegation_demo.DEMO_POLICY['limits'], 'maxAutonomousExposure30d': '1500.00'})
        customers = [self.trial_customer('Parallel ' + 'abcd'[n]) for n in range(4)]
        with ThreadPoolExecutor(4) as pool:
            results = list(pool.map(lambda n: self.call('/api/tools/resolveDecision', {'args': {**self.trial('lakeside', '800.00'), 'customerId': customers[n]}}, 'staff', 'par-%d' % n), range(4)))
        handled = sorted(b['result']['handling'] for _, b, _ in results)
        self.assertEqual(handled, ['autonomous_approve', 'autonomous_approve', 'owner_review', 'owner_review'])   # 600.00 + 600.00; a third would make 1,800.00
        with self.app.lock:
            self.assertEqual(self.app.dg_autonomous(self.app.evidence()), 120000)
        self.assertEqual(self.row("SELECT COUNT(*) FROM decision_cases WHERE dataset='live' AND status='decided'"), [(2,)])
        self.assertEqual(self.row("SELECT COUNT(*) FROM decision_cases WHERE dataset='live' AND status='awaiting_owner'"), [(2,)])

    def test_8_splitting_one_order_into_small_requests_cannot_get_under_the_bounds_and_an_overridden_line_stops_counting(self):
        small = self.resolved(**self.trial('northside', '400.00'))   # 200.00 deposit: exposure 200.00
        self.assertEqual((small['handling'], small['keyFacts']['exposure']['text']), ('autonomous_approve', 'AUD 200.00'))
        same = self.resolved(key='split-0', **self.trial('northside', '400.00'))
        self.assertEqual((same['caseId'], same['replayed']), (small['caseId'], True))   # the same ask is the same decision
        more = self.resolved(key='split-1', **self.trial('northside', '300.00'))   # a second slice of the same order
        self.assertEqual((more['handling'], more['status'], self.check(more, 'trial_in_force')['status']), ('owner_review', 'awaiting_owner', 'fail'))
        status, body, _ = self.call('/api/tools/resolveDecision', {'args': self.trial('northside', '250.00')}, 'staff', 'split-2')   # and a third: the Owner has the second open
        self.assertEqual((status, body['error']), (409, 'CASE_OPEN'))
        with self.app.lock:
            self.assertEqual(self.app.dg_lines(self.cust['northside'], self.app.evidence()), 20000)
        status, body = self.feedback(small['caseId'], {'verdict': 'disagree', 'reason': 'Revoke.', 'override': True})
        self.assertEqual(status, 200, body)
        with self.app.lock:
            self.assertEqual(self.app.dg_lines(self.cust['northside'], self.app.evidence()), 0)   # the overridden line no longer counts
        status, body = self.send('POST', '/api/decision-cases/' + more['caseId'] + '/decide', {'outcome': 'decline', 'reason': 'Not now.', 'version': more['version']})
        self.assertEqual(status, 200, body)   # the Owner settles the second slice; the next ask is judged on its own
        fresh = self.resolved(key='after', **self.trial('northside', '700.00'))   # evaluated afresh
        self.assertEqual(self.check(fresh, 'trial_in_force')['status'], 'pass')
        self.assertIn('AUD 500.00 is within the limit of AUD 1,500.00', self.check(fresh, 'customer_exposure')['sentence'])   # 500.00 only: not 200.00 more

    def test_a_trial_line_in_force_adds_to_the_same_customers_total_for_an_extension(self):
        customer = self.trial_customer('Line Then Invoice')
        self.assertEqual(self.resolved(**{**self.trial('lakeside', '800.00'), 'customerId': customer})['handling'], 'autonomous_approve')
        self.add_invoice(customer, 'AGG-LIN-0', '700.00', '2026-10-28')
        self.assertEqual(self.ledger_of(customer)['linesInForce'], 60000)
        out = self.tool('assessDecision', kind='extension', customerId=customer, invoiceReference='AGG-LIN-0', days=7)['result']
        self.assertIn('AUD 1,300.00', self.check(out, 'customer_exposure')['sentence'])   # 700.00 owed + 600.00 line in force

    def test_9_missing_financial_data_is_unknown_never_zero(self):
        out = self.resolved(**self.extension('riverside', 'DEMO-505', days=10))   # an unreadable invoice and an unplaced payment in the customer's records
        total = self.check(out, 'customer_exposure')
        self.assertEqual((out['handling'], total['status']), ('owner_review', 'unknown'))
        self.assertIn('cannot be established', total['sentence'])
        self.assertNotIn('AUD 0.00', total['sentence'])
        none = self.resolved(**self.extension('riverside', 'DEMO-504', date='2026-11-05'))   # no amount at all on the invoice
        self.assertEqual([self.check(none, k)['status'] for k in ('decision_exposure', 'customer_exposure')], ['unknown', 'unknown'])
        led = ledger(incomplete=True, incompleteText='Incomplete.', invoiceCount=0, receipts=[receipt()], receiptCount=1, debt=0, priorInvoiceTotals=[])
        trial = evaluate('trial_credit', request=trial_request(), led=led, confirmed=[identity()])
        self.assertIsNone(trial['features']['customerExposure'])
        self.assertEqual(next(c for c in trial['risk']['checks'] if c['key'] == 'customer_exposure')['status'], 'unknown')
        self.assertEqual(trial['handling'], 'owner_review')

    def test_the_total_is_called_the_recorded_exposure_while_the_records_are_not_confirmed_complete(self):
        out = self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))
        total = self.check(out, 'customer_exposure')
        self.assertEqual(total['status'], 'pass')
        self.assertIn('This is the RECORDED exposure; the records are not confirmed complete.', total['sentence'])
        self.assertTrue(any('RECORDED exposure' in w and 'not confirmed complete' in w for w in out['warnings']), out['warnings'])
        self.assertEqual(out['status'], 'decided')   # a caveat, not a block
        confirmed = evaluate(led=ledger(coverageConfirmed=True))
        self.assertNotIn('RECORDED', json.dumps(confirmed['risk']) + json.dumps(confirmed['warnings']))
        failing = evaluate(request=extension_request(amountOwed=99000), led=ledger(debt=99000))
        self.assertIn('RECORDED exposure', next(c for c in failing['risk']['checks'] if c['key'] == 'customer_exposure')['sentence'])
        # the Owner can make confirmed coverage a requirement above a level: then it is a block (evidence insufficient), not a caveat
        blocked = evaluate(pol=policy(evidence={'confirmedCoverageAbove': '100.00'}))
        self.assertEqual((blocked['handling'], blocked['evidence']['status']), ('owner_review', 'insufficient'))
        self.assertIsNone(evaluate(led=ledger(coverageConfirmed=None))['features']['coverageConfirmed'])

# ---------------------------------------------------------------- the Owner's override

EFFECTS = ("This reverses Nucleon's internal decision only. Nucleon sent nothing to the customer; if Staff already told the customer or acted on it outside Nucleon, "
           "that is not undone — Staff must follow up.")
OVERRIDE = {'verdict': 'disagree', 'reason': 'They had missed a promise.', 'override': True}


class OverrideTests(DelegationCase):
    def approved(self):
        return self.resolved(**self.extension('bayview', 'DEMO-301', date='2026-11-10'))

    def events(self, request_id, kind):
        return [k for k in self.history_kinds(request_id) if k == kind]

    def test_an_override_names_the_case_version_the_owner_saw_and_a_stale_one_changes_nothing(self):
        out = self.approved()
        before = (self.counts(), self.case(out['caseId'])['version'], self.due('bayview', 'DEMO-301'))
        status, body = self.send('POST', '/api/decision-cases/' + out['caseId'] + '/feedback', OVERRIDE)   # no version at all
        self.assertEqual((status, body['error'], body['field']), (400, 'INVALID_INPUT', 'version'))
        for stale in (before[1] - 1, before[1] + 1, '1', None, True):
            status, body = self.feedback(out['caseId'], {**OVERRIDE, 'version': stale})
            self.assertEqual(status, 409 if type(stale) is int else 400, stale)
            if type(stale) is int:
                self.assertEqual(body['error'], 'STALE_CASE')
        self.assertEqual((self.counts(), self.case(out['caseId'])['version'], self.due('bayview', 'DEMO-301')), before)   # nothing changed
        self.assertEqual(self.case(out['caseId'])['feedback'], [])
        status, body = self.feedback(out['caseId'], {'verdict': 'agree', 'reason': 'x', 'version': before[1]})   # the same rule for plain feedback
        self.assertEqual(status, 200)
        status, body = self.feedback(out['caseId'], {**OVERRIDE, 'version': before[1]})   # the feedback just given moved the version on
        self.assertEqual((status, body['error']), (409, 'STALE_CASE'))
        status, body = self.feedback(out['caseId'], OVERRIDE)
        self.assertEqual((status, body['decision']['overridden']), (200, True))

    def test_a_retry_with_the_same_key_is_the_same_result_and_a_double_click_makes_one_override(self):
        out = self.approved()
        body = {**OVERRIDE, 'version': self.case(out['caseId'])['version']}
        first = self.send('POST', '/api/decision-cases/' + out['caseId'] + '/feedback', body, key='ovr-1')
        again = self.send('POST', '/api/decision-cases/' + out['caseId'] + '/feedback', body, key='ovr-1')   # a double click, a lost response
        self.assertEqual((first[0], again[0]), (200, 200))
        self.assertTrue(again[1].pop('replayed'))
        self.assertEqual(again[1], first[1])
        self.assertEqual(len(self.case(out['caseId'])['feedback']), 1)
        r = self.request_of(out['requestId'])
        self.assertEqual((len(r['decisionHistory']), r['decision']['decisionSource']), (1, 'owner_override'))
        self.assertEqual(len(self.events(r['id'], 'decision.overridden')), 1)
        reused = self.send('POST', '/api/decision-cases/' + out['caseId'] + '/feedback', {**body, 'reason': 'Another reason.'}, key='ovr-1')
        self.assertEqual((reused[0], reused[1]['error']), (409, 'KEY_REUSED'))
        # without a key the second click is stale (the first moved the version on): still one
        late = self.send('POST', '/api/decision-cases/' + out['caseId'] + '/feedback', body)
        self.assertEqual((late[0], late[1]['error']), (409, 'STALE_CASE'))
        late = self.feedback(out['caseId'], OVERRIDE)   # a fresh version of an already overridden case
        self.assertEqual((late[0], late[1]['error']), (409, 'INVALID_TRANSITION'))
        self.assertEqual(len(self.case(out['caseId'])['feedback']), 1)
        parallel = self.approved_trial('Parallel Override')
        body = {**OVERRIDE, 'version': self.case(parallel)['version']}
        with ThreadPoolExecutor(5) as pool:
            results = list(pool.map(lambda n: self.send('POST', '/api/decision-cases/' + parallel + '/feedback', body, key='par-ovr'), range(5)))
        self.assertEqual({r[0] for r in results}, {200})
        self.assertEqual(len(self.case(parallel)['feedback']), 1)

    def approved_trial(self, name):
        customer = self.add_customer(name)
        self.add_receipt(customer, '200.00', 'DEP-' + name.upper().replace(' ', ''))
        self.add_identity(customer)
        return self.resolved(**{**self.trial('lakeside', '800.00'), 'customerId': customer})['caseId']

    def test_the_override_is_a_new_traceable_decision_that_keeps_the_ordered_history_and_names_the_policy_it_replaces(self):
        out = self.approved()
        earlier = self.request_of(out['requestId'])['decision']
        self.change_policy(extensions={**delegation_demo.DEMO_POLICY['extensions'], 'maxDays': 20})   # policy version 2 before the Owner overrides a version 1 decision
        status, body = self.feedback(out['caseId'], OVERRIDE)
        self.assertEqual(status, 200, body)
        r = self.request_of(out['requestId'])
        d = r['decision']
        self.assertEqual((d['decisionSource'], d['outcome'], d['overrides'], d['overridesPolicyVersion']), ('owner_override', 'decline', earlier['id'], 1))
        self.assertNotEqual(d['id'], earlier['id'])
        self.assertEqual(d['overriddenBy'], {'actorId': 'owner_demo', 'role': 'owner', 'channel': 'person', 'actorName': None, 'actorRole': 'owner'})
        self.assertEqual((d['decidedBy'], d['actorRole']), ('owner_demo', 'owner'))
        self.assertEqual([x['id'] for x in r['decisionHistory']], [earlier['id']])   # kept, in order
        self.assertEqual((r['decisionHistory'][0]['decisionSource'], r['decisionHistory'][0]['outcome'], r['decisionHistory'][0]['approvedDueDate']), ('delegated_policy', 'approve', '2026-11-10'))
        kinds = self.history_kinds(r['id'])
        self.assertLess(kinds.index('decision.committed'), kinds.index('decision.overridden'))
        with self.app.lock:
            event = next(e for e in self.app.history(r['id']) if e['kind'] == 'decision.overridden')
        self.assertEqual((event['data']['overrides'], event['data']['overridesPolicyVersion'], event['data']['channel']), (earlier['id'], 1, 'person'))
        case = self.case(out['caseId'])
        self.assertEqual(case['override']['overridesPolicyVersion'], 1)
        self.assertEqual((case['override']['by']['channel'], case['override']['by']['actorId'], case['override']['decisionId']), ('person', 'owner_demo', d['id']))
        self.assertEqual((case['decision']['by'], case['decision']['overridden'], case['decision']['overridesPolicyVersion']), ('agent', True, 1))   # the agent's decision is kept, marked
        self.assertEqual(case['feedback'][0]['channel'], 'person')
        self.assertEqual(self.due('bayview', 'DEMO-301'), '2026-10-18')

    def test_the_result_and_every_view_say_what_the_override_does_not_undo(self):
        out = self.approved()
        status, body = self.feedback(out['caseId'], OVERRIDE)
        self.assertEqual((status, body['externalEffects']), (200, EFFECTS))
        self.assertEqual(body['communication']['sent'], False)
        for role in ('owner', 'staff'):
            self.assertEqual(self.case(out['caseId'], role)['externalEffects'], EFFECTS, role)
            self.assertEqual(self.tool('decisionStatus', role, caseId=out['caseId'])['result']['externalEffects'], EFFECTS, role)
        row = next(c for c in self.call('/api/delegation/cases', None, 'owner')[1]['cases'] if c['caseId'] == out['caseId'])
        self.assertEqual(row['externalEffects'], EFFECTS)
        self.assertNotIn('override', self.case(out['caseId'], 'staff'))   # the Owner's own reason stays with the Owner
        self.assertNotIn('externalEffects', self.resolved(key='other', **self.extension('cityside', 'DEMO-410', days=14)))   # a case not overridden says nothing of the kind
        trial = self.resolved(**self.trial('northside', '800.00'))
        status, body = self.feedback(trial['caseId'], OVERRIDE)
        self.assertEqual((status, body['externalEffects']), (200, EFFECTS + ' Amounts already invoiced under this credit remain owed.'))
        self.assertEqual(body['override']['outcome'], 'revoked')
        self.assertEqual((body['override']['overridesPolicyVersion'], body['override']['by']['channel']), (1, 'person'))

    def test_a_payment_recorded_between_the_approval_and_the_override_leaves_a_consistent_state(self):
        out = self.approved()
        invoice = next(i for i in self.app.fixture()['invoices'] if i['reference'] == 'DEMO-301')['id']
        payment = self.add_receipt(self.cust['bayview'], '480.00', 'EFT-BV-LATE', '2026-10-24')
        self.records(lambda doc: delegation_demo.allocate(doc, {'paymentId': payment, 'allocations': [{'invoiceId': invoice, 'amount': '480.00'}]}, SETTINGS,
                                                          lambda kind: kind + '_t_late', self.ORIGIN))
        with self.app.lock:
            ev = self.app.evidence()
            self.assertFalse(server.is_open(ev.invoice(invoice)))   # the invoice is paid in full
            debt = self.ledger_of(self.cust['bayview'])['debt']
        self.assertEqual(debt, 0)
        status, body = self.feedback(out['caseId'], OVERRIDE)
        self.assertEqual(status, 200, body)
        with self.app.lock:
            ev = self.app.evidence()
            self.assertFalse(server.is_open(ev.invoice(invoice)))   # paid stays paid
            self.assertEqual(self.ledger_of(self.cust['bayview'])['debt'], 0)   # not negative, not 480.00
            self.assertEqual(sum(1 for p in self.app.fixture()['payments'] if p['id'] == payment and p['status'] == 'active'), 1)
        self.assertEqual(self.due('bayview', 'DEMO-301'), '2026-10-18')   # the due date is the original again, on a paid invoice
        r = self.request_of(out['requestId'])
        self.assertEqual((r['decision']['decisionSource'], len(r['decisionHistory'])), ('owner_override', 1))
        self.assertTrue(self.case(out['caseId'])['decision']['overridden'])

    def test_a_records_change_racing_the_override_under_the_lock_is_consistent(self):
        out = self.approved()
        invoice = next(i for i in self.app.fixture()['invoices'] if i['reference'] == 'DEMO-301')['id']
        gate = threading.Barrier(2)

        def override():
            gate.wait()
            return self.feedback(out['caseId'], OVERRIDE)

        def pay():
            gate.wait()
            payment = self.add_receipt(self.cust['bayview'], '480.00', 'EFT-BV-RACE', '2026-10-24')
            self.records(lambda doc: delegation_demo.allocate(doc, {'paymentId': payment, 'allocations': [{'invoiceId': invoice, 'amount': '480.00'}]}, SETTINGS,
                                                              lambda kind: kind + '_t_race', self.ORIGIN))
        with ThreadPoolExecutor(2) as pool:
            ovr, paid = pool.submit(override), pool.submit(pay)
            status, body = ovr.result()
            paid.result()
        self.assertEqual(status, 200, body)
        with self.app.lock:
            ev = self.app.evidence()
            self.assertFalse(server.is_open(ev.invoice(invoice)))
        self.assertEqual(self.due('bayview', 'DEMO-301'), '2026-10-18')
        self.assertEqual(len(self.case(out['caseId'])['feedback']), 1)
        self.assertEqual(len(self.request_of(out['requestId'])['decisionHistory']), 1)

    def test_restart_recovery_the_override_and_its_history_persist_and_a_replay_returns_the_stored_result(self):
        out = self.approved()
        body = {**OVERRIDE, 'version': self.case(out['caseId'])['version']}
        first = self.send('POST', '/api/decision-cases/' + out['caseId'] + '/feedback', body, key='ovr-restart')
        self.assertEqual(first[0], 200)
        before_request = self.request_of(out['requestId'])
        self.restart(adapter=self.model, mode='live', sample_data=False)   # close the App; a new one opens the same database
        case = self.case(out['caseId'])
        self.assertEqual((case['decision']['overridden'], len(case['feedback']), case['externalEffects']), (True, 1, EFFECTS))
        r = self.request_of(out['requestId'])
        self.assertEqual((r['decision'], r['decisionHistory']), (before_request['decision'], before_request['decisionHistory']))
        self.assertEqual(self.due('bayview', 'DEMO-301'), '2026-10-18')   # evidence() agrees with the stored override
        with self.app.lock:
            self.assertEqual(self.app.evidence().current_due(next(i for i in self.app.evidence().invoices if i['reference'] == 'DEMO-301')), '2026-10-18')
        replay = self.send('POST', '/api/decision-cases/' + out['caseId'] + '/feedback', body, key='ovr-restart')
        self.assertEqual(replay[0], 200)
        self.assertTrue(replay[1].pop('replayed'))
        self.assertEqual(replay[1], first[1])
        self.assertEqual((len(self.case(out['caseId'])['feedback']), len(self.request_of(out['requestId'])['decisionHistory'])), (1, 1))
        self.assertEqual(self.tool('decisionStatus', caseId=out['caseId'])['result']['status'], 'decided')

if __name__ == '__main__':
    unittest.main()


class BusinessBackgroundTests(unittest.TestCase):
    """11 Nov 2026: the ABN check and 'registered since' are shown to the Owner and read by no rule."""

    def test_abn_check(self):
        self.assertEqual(delegation.abn_check('51 824 753 556'), {'abn': '51 824 753 556', 'valid': True})
        self.assertEqual(delegation.abn_check('ABN: 51-824-753-556'), {'abn': '51 824 753 556', 'valid': True})
        self.assertEqual(delegation.abn_check('51824753557')['valid'], False)
        for other in ('Registration 111 (fictional)', '004 085 616', '', None, '0312345678'):
            self.assertIsNone(delegation.abn_check(other))

    def test_operating_words(self):
        as_of = date(2026, 11, 11)
        self.assertEqual(delegation.operating_words('2020-07-01', as_of), '6 years 4 months')
        self.assertEqual(delegation.operating_words('2025-11-11', as_of), '1 year')
        self.assertEqual(delegation.operating_words('2026-10-12', as_of), 'less than a month')
        self.assertEqual(delegation.operating_words('2026-06-30', as_of), '4 months')
        self.assertIsNone(delegation.operating_words('2027-01-01', as_of))
        self.assertIsNone(delegation.operating_words('soon', as_of))

    def test_background_sentence(self):
        as_of = date(2026, 11, 11)
        good = delegation.business_background({'registration': '51 824 753 556', 'registeredSince': '2020-07-01'}, as_of)
        self.assertEqual((good['abnValid'], good['operatingFor'], good['lookupUrl']), (True, '6 years 4 months', 'https://abr.business.gov.au/ABN/View?abn=51824753556'))
        self.assertIn('passes the ABN check', good['sentence'])
        self.assertIn('6 years 4 months', good['sentence'])
        self.assertTrue(good['sentence'].endswith(delegation.BACKGROUND_NOTE))
        bad = delegation.business_background({'registration': '51824753557'}, as_of)
        self.assertIn('FAILS the ABN check', bad['sentence'])
        self.assertEqual(delegation.business_background({'registration': 'Registration 111 (fictional)'}, as_of)['sentence'], '')


class BusinessBackgroundFlowTests(DelegationCase):
    """The same Lakeside request as ScenarioTests.test_3, with an ABN and a registration date: the handling is the same whatever they say."""

    def run_with(self, registration, since=None):
        out = self.resolved(**self.trial('lakeside', '600.00'))
        identity = {'kind': 'business_identity', 'basis': 'registry', 'registration': registration, 'tradingName': 'Lakeside Kiosk (fictional)'}
        if since is not None:
            identity['registeredSince'] = since
        return out, self.submit(out['actionId'], [{'kind': 'deposit', 'basis': 'bank', 'amount': '150.00', 'receivedDate': '2026-10-23', 'reference': 'DEP-LK-01'}, identity])

    def identity_item(self, body):
        return next(i for i in body['case']['evidence']['items'] if i['key'] == 'business_identity')

    def test_a_valid_abn_and_a_long_registration_are_shown(self):
        _, (status, body) = self.run_with('51 824 753 556', '2019-07-01')
        self.assertEqual((status, body['case']['status'], body['case']['handling']), (200, 'decided', 'autonomous_approve'))
        item = self.identity_item(body)
        self.assertEqual((item['status'], item['background']['abnValid'], item['background']['operatingFor']), ('verified', True, '7 years 3 months'))
        self.assertIn('passes the ABN check', item['detail'])
        self.assertIn(delegation.BACKGROUND_NOTE, item['detail'])

    def test_a_failed_check_and_a_week_old_business_change_nothing(self):
        _, (status, body) = self.run_with('51 824 753 557', '2026-10-20')
        self.assertEqual((status, body['case']['status'], body['case']['handling']), (200, 'decided', 'autonomous_approve'))
        item = self.identity_item(body)
        self.assertEqual((item['status'], item['background']['abnValid'], item['background']['operatingFor']), ('verified', False, 'less than a month'))
        self.assertIn('FAILS the ABN check', item['detail'])

    def test_a_date_after_today_or_not_a_date_is_refused(self):
        for since in ('2026-12-01', 'last year'):
            with self.subTest(since=since):
                _, (status, body) = self.run_with('51 824 753 556', since)
                self.assertEqual((status, body['error'], body.get('field')), (400, 'INVALID_DATE', 'business_identity.registeredSince'))
                self.tearDown(); self.setUp()


class OwnScenarioTests(DelegationCase):
    """11 Nov 2026 (Hoang): the Owner types in a decision made outside Nucleon; it is stored like an answered what-if, marked as their own."""

    def post(self, body):
        return self.call('/api/delegation/preferences/answer', body, 'owner', None, {'X-Nucleon-CSRF': self.csrf('owner')})[:2]

    def test_an_own_trial_scenario_takes_the_amount_as_typed_and_is_listed(self):
        status, out = self.post({'source': 'own', 'customerId': self.cust['lakeside'], 'kind': 'trial_credit', 'params': {'orderAmountText': '2,500.00', 'termsDays': 30},
                                 'outcome': 'decline', 'reason': 'too much for a first order'})
        self.assertEqual((status, out['ownerDecision'], out['answered'], out['own']), (200, 'decline', 1, 1))
        row = out['recent'][0]
        self.assertEqual((row['source'], row['ownerDecision'], row['ownerReason']), ('own', 'decline', 'too much for a first order'))
        self.assertTrue(row['summary'].startswith('Your own scenario: AUD 2,500.00 on 30-day terms'), row['summary'])
        [(dataset, data)] = self.row('SELECT dataset, data FROM decision_cases WHERE id=?', out['stored'])
        self.assertEqual((dataset, json.loads(data)['params']['orderAmount']), (delegation.PREFERENCE, 250000))
        self.assertEqual(self.count('actions'), 0)

    def test_an_asked_what_if_is_still_marked_asked_and_bad_input_is_refused(self):
        s = self.call('/api/delegation/preferences/next', None, 'owner')[1]['scenario']
        status, out = self.post({'customerId': s['customer']['id'], 'kind': s['kind'], 'params': s['params'], 'outcome': 'approve'})
        self.assertEqual((status, out['own'], out['recent'][0]['source']), (200, 0, 'asked'))
        self.assertTrue(out['recent'][0]['summary'].startswith('What-if: '))
        status, out = self.post({'source': 'own', 'customerId': self.cust['lakeside'], 'kind': 'trial_credit', 'params': {'orderAmountText': 'lots', 'termsDays': 30}, 'outcome': 'approve'})
        self.assertEqual(status, 400, out)
        status, out = self.post({'source': 'own', 'customerId': self.cust['lakeside'], 'kind': 'extension', 'params': {'invoiceId': 'nope', 'days': 30}, 'outcome': 'approve'})
        self.assertEqual(status, 404, out)
