"""Controlled agent actions over MCP (Phases A and B): with the owner having turned prepareRequest and actionStatus on in the scratch records, a
staff token prepares a payment-extension request and reads where it stands; neither token can confirm anything. Confirming is an HTTP call of a
person's session with the page's Origin and the session's csrf token: the Lab signs in with the records' SERVICE codes, the records mark that
session a service's by the code, and it is refused (PERSON_REQUIRED); the Lab checks that and fails closed on a person's session. The two tools
carry an action card (lab/card.py). While the tools are off (their default) the tool lists are exactly what they were. Same harness as test_mcp_idempotency: the Lab on a scratch port
against the scratch records server. Fictional data only; tokens are test strings."""
import json
import re
import unittest
from pathlib import Path
from unittest import mock

import httpx2
from mcp.shared.exceptions import MCPError

from lab.mcp_server import NON_DESTRUCTIVE, READ_ONLY, LabMCP, annotations_for, exposed
from harness import SERVER, setUpModule, tearDownModule   # noqa: F401 (the scratch records server, for this module)
import test_mcp
from test_mcp import OWNER, STAFF

NEW = {'prepareRequest', 'actionStatus'}
DEFAULT_STAFF = {'findCustomers', 'customerOverview', 'invoices', 'ownerContext', 'cases', 'caseDetails', 'whereIs', 'prepareCustomer',
                 'compareExtension', 'workQueue', 'listRequests', 'prepareHoldingMessage', 'assessRequest', 'proposeImport',
                 'whatIsNeeded', 'comparableCases', 'customerStatus'}   # as test_mcp has them, plus the S3 read tools (on by default since S6a)


class ControlledActionsMCPTests(unittest.TestCase):
    setUpClass, tearDownClass = test_mcp.MCPTests.__dict__['setUpClass'], test_mcp.MCPTests.__dict__['tearDownClass']
    client, tools, raw = test_mcp.MCPTests.client, test_mcp.MCPTests.tools, test_mcp.MCPTests.raw

    def records(self):
        return httpx2.Client(base_url=SERVER['url'], timeout=30)

    def switch(self, on):
        with self.records() as c:
            for name in sorted(NEW):
                r = c.post('/api/agent-tools', headers={'Cookie': SERVER['owner'], 'Idempotency-Key': 'switch-' + name + str(on) + str(id(self))}, json={'tool': name, 'enabled': on})
                self.assertEqual(r.status_code, 200, r.text)

    def turn_on(self):
        self.switch(True)
        self.addCleanup(self.switch, False)

    def result(self, token, name, args):
        out = self.raw(token, name, args)
        return out, json.loads(out.content[0].text)

    def confirm(self, cookie, action_id, origin=None, key='lab-confirm', csrf=True):
        """The confirmation page's POST: the session's csrf token (from its own /api/session) unless csrf is False; no reason, the proposal's is frozen."""
        with self.records() as c:
            token = csrf and c.get('/api/session', headers={'Cookie': cookie}).json()['csrf']
            headers = {'Cookie': cookie, 'Idempotency-Key': key, **({'Origin': origin} if origin else {}), **({'X-Nucleon-CSRF': token} if token else {})}
            r = c.post('/api/actions/' + action_id + '/confirm', headers=headers, json={'version': 1})
        return r.status_code, r.json()

    def test_while_the_tools_are_off_the_lists_are_what_they_were(self):
        staff, owner = self.tools(STAFF), self.tools(OWNER)
        self.assertEqual(set(staff), DEFAULT_STAFF)
        self.assertFalse(NEW & (set(staff) | set(owner)))
        for token in (STAFF, OWNER):
            with self.assertRaisesRegex(MCPError, 'Unknown tool: prepareRequest'):
                self.raw(token, 'prepareRequest', {'customerId': 'customer_demo_02', 'invoiceId': 'invoice_demo_201', 'days': 14})
            with self.assertRaisesRegex(MCPError, 'Unknown tool: actionStatus'):
                self.raw(token, 'actionStatus', {'actionId': 'act_x'})

    def test_on_the_owner_switch_staff_get_prepareRequest_and_both_roles_get_actionStatus_and_nothing_else_changes(self):
        self.turn_on()
        staff, owner = self.tools(STAFF), self.tools(OWNER)
        self.assertEqual(set(staff), DEFAULT_STAFF | NEW)
        self.assertEqual(set(owner) & NEW, {'actionStatus'})   # the owner decides requests; staff prepare them
        self.assertIn('actionStatus', READ_ONLY)
        self.assertNotIn('prepareRequest', READ_ONLY)
        self.assertTrue(staff['actionStatus'].annotations.read_only_hint)
        self.assertFalse(staff['prepareRequest'].annotations.read_only_hint)
        self.assertIsNone(staff['prepareRequest'].annotations.destructive_hint)   # not claimed harmless beyond what was audited
        for tool in (staff['prepareRequest'], staff['actionStatus'], owner['actionStatus']):
            self.assertIs(tool.annotations.open_world_hint, False)
            self.assertIn('message', tool.input_schema['properties'])
        self.assertEqual(staff['prepareRequest'].input_schema['required'], ['customerId'])
        for token in (STAFF, OWNER):   # no tool the model can reach confirms, cancels or executes anything
            self.assertFalse([n for n in self.tools(token) if any(w in n.lower() for w in ('confirm', 'cancel', 'execute'))], token)
        with self.assertRaisesRegex(MCPError, 'Unknown tool: prepareRequest'):
            self.raw(OWNER, 'prepareRequest', {'customerId': 'customer_demo_02', 'invoiceId': 'invoice_demo_201', 'days': 14})
        for name in ('confirmAction', 'confirm_action', 'cancelAction'):
            with self.assertRaisesRegex(MCPError, 'Unknown tool: ' + name):
                self.raw(STAFF, name, {'actionId': 'act_x'})

    def test_staff_prepare_over_mcp_read_it_back_and_the_lab_session_cannot_confirm_but_a_person_can(self):
        self.turn_on()
        out, prepared = self.result(STAFF, 'prepareRequest', {'customerId': 'customer_demo_02', 'invoiceId': 'invoice_demo_201', 'days': 14,
                                                              'reason': 'Waiting on a customer payment.', 'message': 'Prepare a 14 day extension for DEMO-201.'})
        self.assertFalse(out.is_error, prepared)
        self.assertEqual(len(out.content), 2)   # the JSON, then the action card (no button here: the scratch records are on neither contract origin)
        self.assertNotIn('<button', out.content[1].resource.text)
        self.assertEqual(out.meta['nucleon.lab/operation']['keySource'], 'server')
        action_id = prepared['actionId']
        self.assertEqual((prepared['status'], prepared['preview']['proposedChange']['requestedDueDate'], prepared['preview']['proposedChange']['days']), ('proposed', '2026-10-23', 14))
        self.assertEqual(prepared['preview']['fromRecords']['invoice']['reference'], 'DEMO-201')
        self.assertIn('approves nothing', prepared['preview']['requires']['ownerDecision'])
        self.assertIn('caveatText', prepared['preview']['completeness'])
        # the same operation under a client key is the same action
        meta = {'nucleon.lab/idempotencyKey': 'client-key-actions-1'}
        args = {'customerId': 'customer_demo_02', 'invoiceId': 'invoice_demo_202', 'days': 7}
        first = self.client(STAFF, lambda s: s.call_tool('prepareRequest', args, meta=meta))
        again = self.client(STAFF, lambda s: s.call_tool('prepareRequest', args, meta=meta))
        self.assertEqual(json.loads(first.content[0].text)['error'], 'OPEN_REQUEST_EXISTS')   # DEMO-202 has the scratch server's open case
        self.assertTrue(first.is_error)
        self.assertEqual(first.content[0].text, again.content[0].text)
        # where it stands, for either role, by a read
        for token in (STAFF, OWNER):
            out, status = self.result(token, 'actionStatus', {'actionId': action_id})
            self.assertFalse(out.is_error)
            self.assertIsNone(out.meta)   # a read: no operation
            self.assertEqual((status['status'], status['request'], status['params']['invoiceReference']), ('proposed', None, 'DEMO-201'))
        out, missing = self.result(STAFF, 'actionStatus', {'actionId': 'act_nope'})
        self.assertEqual((out.is_error, missing['error']), (True, 'NOT_FOUND'))
        # confirming over HTTP with the Lab's own records session: refused as a service, nothing changes
        lab_cookie = self.client_run(self.mcp.session('staff'))
        status, body = self.confirm(lab_cookie, action_id, origin=SERVER['url'])
        self.assertEqual((status, body['error']), (403, 'PERSON_REQUIRED'))
        self.assertEqual(self.result(STAFF, 'actionStatus', {'actionId': action_id})[1]['status'], 'proposed')
        # a person's session, from the page (its Origin), confirms; a script with no Origin is refused even with a person's cookie
        status, body = self.confirm(SERVER['staff'], action_id, origin=None, key='person-1')
        self.assertEqual((status, body['error']), (403, 'ORIGIN_REQUIRED'))
        status, body = self.confirm(SERVER['staff'], action_id, origin=SERVER['url'], key='person-2')
        self.assertEqual(status, 200, body)
        self.assertEqual((body['action']['status'], body['request']['status']), ('executed', 'awaiting_owner'))
        # and the assistant reads the result by the same status tool
        out, status = self.result(STAFF, 'actionStatus', {'actionId': action_id})
        self.assertEqual((status['status'], status['request']['id'], status['request']['label']), ('executed', body['request']['id'], 'With the owner'))
        out, status = self.result(OWNER, 'actionStatus', {'actionId': action_id})
        self.assertEqual(status['request']['label'], 'Needs your decision')
        # the owner's case queue now has it, built without a model
        case = json.loads(self.raw(OWNER, 'caseDetails', {'requestId': body['request']['id']}).content[0].text)['case']
        self.assertEqual(case['status'], 'awaiting_owner')

    def switch_decisions(self, on):
        with self.records() as c:
            for name in ('assessDecision', 'resolveDecision', 'decisionStatus'):
                r = c.post('/api/agent-tools', headers={'Cookie': SERVER['owner'], 'Idempotency-Key': 'dswitch-' + name + str(on) + str(id(self))}, json={'tool': name, 'enabled': on})
                self.assertEqual(r.status_code, 200, r.text)

    def test_the_decision_tools_are_off_by_default_then_exposed_by_the_registry_with_one_decision_card(self):
        names = {'assessDecision', 'resolveDecision', 'decisionStatus'}
        self.assertFalse(names & (set(self.tools(STAFF)) | set(self.tools(OWNER))))
        self.switch_decisions(True)
        self.addCleanup(self.switch_decisions, False)
        staff, owner = self.tools(STAFF), self.tools(OWNER)
        self.assertEqual(names & set(staff), names)
        self.assertEqual(names & set(owner), {'decisionStatus'})
        self.assertTrue(staff['assessDecision'].annotations.read_only_hint and staff['decisionStatus'].annotations.read_only_hint)
        self.assertFalse(staff['resolveDecision'].annotations.read_only_hint)
        self.assertIsNone(staff['resolveDecision'].annotations.destructive_hint)
        args = {'kind': 'extension', 'customerId': 'customer_demo_01', 'invoiceId': 'invoice_demo_101', 'days': 14}
        out, assessed = self.result(STAFF, 'assessDecision', args)
        self.assertFalse(out.is_error, assessed)
        self.assertIsNone(out.meta)   # a read: no operation, and the records stored nothing
        self.assertEqual((assessed['status'], assessed['handling']), ('assessed', 'owner_review'))   # version 0: nothing executes (the model reads the compact forModel; the card the full result)
        [item] = [c for c in out.content if c.type == 'resource']
        self.assertEqual(item.resource.uri, 'ui://nucleon/card/assessDecision/customer_demo_01')
        self.assertIn('WOULD GO TO THE OWNER FOR REVIEW — PREVIEW, NOT DECIDED', item.resource.text)
        self.assertNotIn('<button', item.resource.text)
        out, resolved = self.result(STAFF, 'resolveDecision', {**args, 'recommendation': 'approve', 'reasoning': 'Fictional test.'})
        self.assertFalse(out.is_error, resolved)
        self.assertEqual(out.meta['nucleon.lab/operation']['keySource'], 'server')
        self.assertEqual(resolved['status'], 'awaiting_owner')
        self.assertIn('WITH THE OWNER FOR REVIEW', [c for c in out.content if c.type == 'resource'][0].resource.text)
        out, status = self.result(OWNER, 'decisionStatus', {'caseId': resolved['keyFacts']['caseId']})
        self.assertEqual(status['status'], 'awaiting_owner')
        self.assertIn('WITH THE OWNER FOR REVIEW', [c for c in out.content if c.type == 'resource'][0].resource.text)

    def client_run(self, coroutine):
        import asyncio
        return asyncio.run(coroutine)

    def test_the_lab_signs_in_to_the_records_as_a_service_for_every_role(self):
        for role in ('staff', 'owner'):
            cookie = self.client_run(self.mcp.session(role, again=True))
            with self.records() as c:
                r = c.get('/api/session', headers={'Cookie': cookie, 'X-Nucleon-Role': role})
            self.assertEqual((r.json()['authenticated'], r.json().get('channel')), (True, 'service'), role)
        with self.records() as c:   # a person's own session is a person's
            self.assertEqual(c.get('/api/session', headers={'Cookie': SERVER['staff']}).json().get('channel'), 'person')

    def codes_in_log(self):
        found = {'access': {}, 'service': {}}
        for line in (Path(SERVER['dir']) / 'records.log').read_text().splitlines():
            m = re.fullmatch(r'(STAFF|OWNER) (access|service) code: (\S+)', line)
            if m:
                found[m[2]][m[1].lower()] = m[3]
        return found

    def lab_with(self, codes):
        """A Lab MCP server object (no HTTP) holding only these records codes."""
        lab = LabMCP.__new__(LabMCP)
        lab.config, lab.records, lab.cookies = {'recordsCodes': codes}, self.mcp.records, {}
        return lab

    def test_the_lab_never_operates_on_a_person_session_it_fails_closed_and_ends_it(self):
        codes = self.codes_in_log()
        self.assertTrue(codes['service']['staff'] and codes['access']['staff'] and codes['service']['staff'] != codes['access']['staff'])
        for role in ('staff', 'owner'):
            lab = self.lab_with({role: codes['service'][role]})
            cookie = self.client_run(lab.session(role))
            with self.records() as c:
                self.assertEqual(c.get('/api/session', headers={'Cookie': cookie}).json()['channel'], 'service')
            lab = self.lab_with({role: codes['access'][role]})   # a person's access code: a valid login whose session is a person's
            with self.assertRaisesRegex(MCPError, 'not a service session'):
                self.client_run(lab.session(role))
            self.assertEqual(lab.cookies, {})   # nothing kept
        with self.assertRaisesRegex(MCPError, 'service codes may be out of date'):
            self.client_run(self.lab_with({'staff': 'not-a-code'}).session('staff'))

    def test_the_lab_sends_no_channel_and_a_records_session_it_cannot_read_back_is_refused(self):
        sent = []
        real = httpx2.AsyncClient.post

        async def spy(client, url, *args, **kwargs):
            if url.endswith('/api/demo/login'):
                sent.append(kwargs.get('json'))
            return await real(client, url, *args, **kwargs)
        with mock.patch.object(httpx2.AsyncClient, 'post', spy):
            self.client_run(self.mcp.session('staff', again=True))
        self.assertEqual([set(x) for x in sent], [{'accessCode', 'role'}])   # no channel field: the records decide from the code

    def test_the_action_cards_over_mcp_carry_the_button_for_this_action_only_on_a_contract_url(self):
        self.turn_on()
        with mock.patch.dict(self.mcp.config, {'recordsPublicUrl': 'http://127.0.0.1:18631'}):
            out, prepared = self.result(STAFF, 'prepareRequest', {'customerId': 'customer_demo_01', 'invoiceId': 'invoice_demo_101', 'days': 14,
                                                                  'reason': 'Waiting on a customer payment.'})
            self.assertFalse(out.is_error, prepared)
            [item] = [c for c in out.content if c.type == 'resource']
            page = item.resource.text
            self.assertIn('data-url="http://127.0.0.1:18631/#/actions/' + prepared['actionId'] + '"', page)
            self.assertIn('PROPOSED — NOT SUBMITTED.', page)
            self.assertEqual(item.resource.uri, 'ui://nucleon/card/prepareRequest/' + prepared['actionId'])
            self.assertNotRegex(page, r'(?i)bearer|token|cookie|nucleon_staff|' + STAFF[:20])
            out, status = self.result(STAFF, 'actionStatus', {'actionId': prepared['actionId']})
            self.assertEqual(len(out.content), 2)
            self.assertIn('PROPOSED — NOT SUBMITTED.', out.content[1].resource.text)
        with mock.patch.dict(self.mcp.config, {'recordsPublicUrl': 'https://evil.example'}):   # not a contract origin (config.load would refuse it): no button
            out, _ = self.result(STAFF, 'actionStatus', {'actionId': prepared['actionId']})
            self.assertNotIn('<button', out.content[1].resource.text)
        out, _ = self.result(STAFF, 'actionStatus', {'actionId': 'act_nope'})
        self.assertEqual(len(out.content), 1)   # an error has no card
        out, _ = self.result(STAFF, 'prepareRequest', {'customerId': 'customer_demo_01', 'invoiceId': 'invoice_demo_101', 'days': 0})
        self.assertEqual((out.is_error, len(out.content)), (True, 1))

    def test_prepareRequest_is_stored_work_not_read_only_and_not_marked_harmless(self):
        self.assertNotIn('prepareRequest', READ_ONLY | NON_DESTRUCTIVE)
        hints = annotations_for('prepareRequest')
        self.assertEqual((hints.read_only_hint, hints.destructive_hint, hints.open_world_hint), (False, None, False))
        self.turn_on()
        text = self.tools(STAFF)['prepareRequest'].description
        self.assertIn('stores the proposal', text)
        self.assertIn('replaces any earlier live proposal for the same invoice', text)
        self.assertIn('submits nothing', text)

    def test_exposed_still_lists_only_read_and_prepare_kinds_and_the_two_acts(self):
        registry = {'tools': [{'name': 'prepareRequest', 'kind': 'prepare'}, {'name': 'actionStatus', 'kind': 'read'}, {'name': 'confirmAction', 'kind': 'act'},
                              {'name': 'openRequest', 'kind': 'act'}]}
        self.assertEqual([t['name'] for t in exposed(registry)], ['prepareRequest', 'actionStatus'])
        self.assertTrue(annotations_for('actionStatus').read_only_hint)


if __name__ == '__main__':
    unittest.main()
