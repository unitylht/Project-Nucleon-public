"""The MCP server at mcp/ over streamable HTTP, with the mcp client: the Lab served by uvicorn on a scratch port, against the
scratch records server tests/harness.py starts (its setUpModule, reused here). The bearer token gives the role; the records session
for that role is signed in once, with the codes the records log shows for its latest start. Fictional data only."""
import asyncio
import html
import json
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import httpx2
import uvicorn
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.exceptions import MCPError

from lab.app import create_app
from lab.config import load
from lab import card
from lab.mcp_server import ACTS, LabMCP, NON_DESTRUCTIVE, READ_ONLY, annotations_for, codes_from_log, exposed
from harness import SERVER, free_port, setUpModule, tearDownModule   # noqa: F401 (the scratch records server, for this module too)

OWNER, STAFF = 'owner-test-token-' + 'o' * 32, 'staff-test-token-' + 's' * 32
PUBLIC = 'https://nucleon.dracooz.top'
EXAMPLE = Path(__file__).resolve().parents[1] / 'config.example.json'
HIDDEN_FROM_STAFF = {'prepareDecision', 'withdrawPreparation', 'requestSuggestion', 'interpretStatement', 'openRequest'}
INITIALIZE = {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
              'params': {'protocolVersion': '2025-06-18', 'capabilities': {}, 'clientInfo': {'name': 'test', 'version': '1'}}}


class MCPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix='lab-mcp-')
        cls.app = create_app({'recordsUrl': SERVER['url'], 'store': cls.dir + '/lab.db', 'model': {'provider': 'mock'}, 'rootPath': '',
                              'mcpTokens': {OWNER: 'owner', STAFF: 'staff'}, 'recordsLog': SERVER['dir'] + '/records.log',
                              'publicOrigins': [PUBLIC]})
        cls.mcp = next(r.app for r in cls.app.routes if getattr(r, 'path', None) == '/mcp')
        port = free_port()
        cls.url = 'http://127.0.0.1:' + str(port) + '/mcp/'
        cls.server = uvicorn.Server(uvicorn.Config(cls.app, host='127.0.0.1', port=port, log_level='warning'))
        cls.thread = threading.Thread(target=cls.server.run, daemon=True)
        cls.thread.start()
        deadline = time.monotonic() + 20
        while not cls.server.started:
            if time.monotonic() > deadline:
                raise RuntimeError('the Lab did not start')
            time.sleep(0.05)

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.thread.join(10)
        shutil.rmtree(cls.dir, ignore_errors=True)

    def client(self, token, work):
        """work(session) in an initialized MCP client session sent with this bearer token."""
        async def go():
            async with httpx2.AsyncClient(headers={'Authorization': 'Bearer ' + token}, timeout=60) as http, \
                    streamable_http_client(self.url, http_client=http) as (read, write), ClientSession(read, write) as session:
                await session.initialize()
                return await work(session)
        try:
            return asyncio.run(go())
        except BaseExceptionGroup as group:   # the client's task groups wrap what the server answered
            while isinstance(group, BaseExceptionGroup):
                group = group.exceptions[0]
            raise group

    def tools(self, token):
        return {t.name: t for t in self.client(token, lambda s: s.list_tools()).tools}

    def call(self, token, name, args):
        out = self.client(token, lambda s: s.call_tool(name, args))
        return out.is_error, json.loads(out.content[0].text)

    def test_staff_tools_leave_out_owner_and_act_tools(self):
        tools = self.tools(STAFF)
        self.assertFalse(HIDDEN_FROM_STAFF & set(tools), sorted(tools))
        self.assertIn('compareExtension', tools)
        self.assertIn('workQueue', tools)
        self.assertEqual(tools['compareExtension'].input_schema['required'], ['requestId'])   # the registry's parameters
        self.assertIn('message', tools['compareExtension'].input_schema['properties'])

    def test_owner_tools(self):
        tools = self.tools(OWNER)
        for name in ('prepareDecision', 'compareExtension', 'withdrawPreparation', 'requestSuggestion', 'interpretStatement'):
            self.assertIn(name, tools)
        self.assertNotIn('openRequest', tools)

    def test_owner_work_queue_has_the_awaiting_case(self):
        error, result = self.call(OWNER, 'workQueue', {})
        self.assertFalse(error)
        self.assertIn((SERVER['case'], 'you'), [(x['requestId'], x['waitingOn']) for x in result['forYou']])

    def test_staff_compare_carries_no_limit_and_passes_the_message(self):
        with mock.patch.object(self.mcp.records, 'call', wraps=self.mcp.records.call) as sent:
            error, result = self.call(STAFF, 'compareExtension', {'requestId': SERVER['case'], 'days': 10, 'message': 'Would ten days fit?'})
        self.assertFalse(error)
        self.assertEqual((result['proposedDateText'], result['limitDays'], result['latestWithinLimit'], result['withinLimit']),
                         ('Mon 16 Nov 2026', None, None, None))
        self.assertEqual(sent.call_args.args[1:4], ('compareExtension', {'requestId': SERVER['case'], 'days': 10}, 'Would ten days fit?'))

    def test_the_completeness_contract_survives_the_mcp_path_unchanged(self):
        """The Lab passes the records' result through as JSON text: the new fields arrive whole, and the two tools agree for one customer."""
        _, found = self.call(STAFF, 'findCustomers', {'query': 'Harbour'})
        customer = found['matches'][0]['customerId']
        error, overview = self.call(STAFF, 'customerOverview', {'customerId': customer})
        error2, listed = self.call(STAFF, 'invoices', {'customerId': customer, 'which': 'all'})
        self.assertFalse(error or error2)
        w = overview['completeness']
        self.assertEqual(w, listed['completeness'])
        self.assertEqual(overview['completeTo'], listed['completeTo'])
        self.assertEqual({k for k in w if k == 'caveatText' or not k.endswith('Text')}, {'asOf', 'invoices', 'payments', 'balanceEstablished', 'reasons', 'caveatText'})   # dated() adds asOfText
        self.assertEqual({k for k in w['payments'] if not k.endswith('Text')}, {'completeTo', 'state', 'lastActivity', 'recordedCount', 'contradicted'})
        self.assertIn(w['payments']['state'], ('complete', 'completeToEarlierDate', 'notConfirmed'))
        self.assertTrue(w['caveatText'] and isinstance(w['balanceEstablished'], bool))
        self.assertIn('scopeText', listed)
        error, filtered = self.call(STAFF, 'invoices', {'customerId': customer, 'which': 'open', 'dueOn': '2026-01-01'})
        self.assertFalse(error)
        self.assertEqual(filtered['completeness'], w)   # a filtered list is still said against the whole customer
        self.assertIn('only', filtered['scopeText'])

    def raw(self, token, name, args):
        return self.client(token, lambda s: s.call_tool(name, args))

    def records_result(self, name, args):
        """The records' own result of a read tool, as the Lab gets it."""
        import httpx2
        with httpx2.Client(base_url=SERVER['url'], timeout=30) as c:
            r = c.post('/api/tools/' + name, headers={'Cookie': SERVER['staff']}, json={'args': args})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()['result']

    def harbour(self):
        return self.call(STAFF, 'findCustomers', {'query': 'Harbour'})[1]['matches'][0]['customerId']

    def test_overview_and_invoices_carry_a_card_after_their_unchanged_json(self):
        customer = self.harbour()
        for name, args in (('customerOverview', {'customerId': customer}), ('invoices', {'customerId': customer, 'which': 'all'})):
            out = self.raw(STAFF, name, args)
            self.assertFalse(out.is_error)
            self.assertEqual([c.type for c in out.content], ['text', 'resource'], name)
            text = json.loads(out.content[0].text)
            result = self.records_result(name, args)   # the card is made from the records' whole result
            # the overview's JSON item is that result, first and whole; the invoices list gives the model its compact forModel instead (every invoice, short rows:
            # Hoang's NTK round, 9 Nov 2026), with the same completeness object
            self.assertEqual(text, result['forModel'] if name == 'invoices' else result)
            self.assertEqual(text['customerId'], customer)
            self.assertEqual(text['completeness'], result['completeness'])
            res = out.content[1].resource
            self.assertEqual((res.uri, res.mime_type), ('ui://nucleon/card/' + name + '/' + customer, 'text/html'))
            self.assertEqual(res.text, card.card_html(name, result))
            self.assertIn(result['completeness']['caveatText'], html.unescape(res.text))   # verbatim, in the card
            self.assertEqual(res.text, self.raw(STAFF, name, args).content[1].resource.text)   # the same result, the same card
            self.assertEqual(out.content[0].text, self.raw(STAFF, name, args).content[0].text)

    def test_omission_simulation_through_the_mcp_path(self):
        """AUTOMATED SIMULATION: a final answer that states the amount and drops the caveat. The MCP tool takes no answer, so the resource item
        beside the unchanged JSON item carries the caveat whatever the agent later says; and it survives the stored (JSON) shape."""
        customer = self.harbour()
        answers = ('Harbour owes the amount shown.', 'Just the figure, please.')   # simulated, caveat-free
        got = []
        for _ in answers:
            out = self.raw(STAFF, 'customerOverview', {'customerId': customer})
            self.assertEqual([c.type for c in out.content], ['text', 'resource'])
            got.append((out.content[0].text, out.content[1].resource))
        result = json.loads(got[0][0])
        caveat = result['completeness']['caveatText']   # the JSON item still carries it
        self.assertTrue(caveat)
        for answer in answers:
            self.assertNotIn(caveat, answer)
        self.assertEqual(got[0][0], got[1][0])
        self.assertEqual(got[0][1].text, got[1][1].text)
        self.assertIn(html.escape(caveat, quote=True), got[0][1].text)   # the resource item carries it, verbatim (escaped)
        for answer in answers:
            self.assertNotIn(answer, got[0][1].text)
        res = got[0][1]
        stored = json.loads(json.dumps({'uri': res.uri, 'mimeType': res.mime_type, 'text': res.text}))   # LibreChat's storage shape, simulated
        self.assertEqual(stored['text'].encode(), card.card_html('customerOverview', result).encode())
        if result['completeness']['balanceEstablished'] is not True and result['owedNow'].get('amount'):
            self.assertIn(html.escape(result['owedNow']['amount']), stored['text'])
            self.assertIn('Recorded amount', stored['text'])

    def test_other_tools_and_errors_carry_no_card(self):
        customer = self.harbour()
        for name, args in (('findCustomers', {'query': 'Harbour'}), ('cases', {'customerId': customer}), ('ownerContext', {'customerId': customer}),
                           ('customerOverview', {'customerId': 'C-NOPE-404'}), ('invoices', {'customerId': 'C-NOPE-404', 'which': 'all'})):
            out = self.raw(STAFF, name, args)
            self.assertEqual([c.type for c in out.content], ['text'], name)
        self.assertTrue(self.raw(STAFF, 'customerOverview', {'customerId': 'C-NOPE-404'}).is_error)
        self.assertIn('No customer matches', json.loads(self.raw(STAFF, 'invoices', {'customerId': 'C-NOPE-404', 'which': 'all'}).content[0].text)['message'])

    def test_a_card_that_cannot_be_made_leaves_the_plain_result(self):
        customer = self.harbour()
        plain = self.raw(STAFF, 'customerOverview', {'customerId': customer}).content[0].text
        with mock.patch('lab.mcp_server.card_html', side_effect=RuntimeError('boom')), self.assertLogs('lab.mcp_server', 'ERROR') as logs:
            out = self.raw(STAFF, 'customerOverview', {'customerId': customer})
        self.assertFalse(out.is_error)
        self.assertEqual([c.type for c in out.content], ['text'])
        self.assertEqual(out.content[0].text, plain)
        self.assertNotIn(STAFF, ' '.join(logs.output))

    def test_the_card_changes_no_tool_list_or_permission(self):
        staff = self.tools(STAFF)
        self.assertFalse(HIDDEN_FROM_STAFF & set(staff))
        for name in ('customerOverview', 'invoices'):
            self.assertTrue(staff[name].annotations.read_only_hint)
            self.assertNotIn('ui', (staff[name].meta or {}))   # no ui metadata: the card travels as a result item only
        self.assertTrue({'prepareDecision', 'compareExtension'} <= set(self.tools(OWNER)))   # the owner's tools are as they were

    def test_a_customer_that_is_not_found_is_an_error_result_not_a_balance(self):
        error, result = self.call(STAFF, 'customerOverview', {'customerId': 'C-NOPE-404'})
        self.assertTrue(error)
        self.assertEqual(set(result), {'error', 'message'})

    def test_every_listed_tool_has_annotations_and_only_the_audited_reads_are_read_only(self):
        for token in (STAFF, OWNER):
            tools = self.tools(token)
            for name, tool in tools.items():
                self.assertIsNotNone(tool.annotations, name)
                self.assertEqual(bool(tool.annotations.read_only_hint), name in READ_ONLY, name)
                self.assertIs(tool.annotations.open_world_hint, False, name)
                if name not in READ_ONLY:
                    self.assertIs(tool.annotations.read_only_hint, False, name)
                    self.assertEqual(tool.annotations.destructive_hint, False if name in NON_DESTRUCTIVE else None, name)
            for name in ('assessRequest', 'prepareCustomer', 'proposeImport', 'prepareHoldingMessage'):
                self.assertFalse(tools[name].annotations.read_only_hint, name)   # stores a version, a draft's call or a proposal: never claimed read-only
            self.assertTrue(tools['customerOverview'].annotations.read_only_hint)
        self.assertFalse(self.tools(OWNER)['withdrawPreparation'].annotations.read_only_hint)
        self.assertIsNone(self.tools(OWNER)['withdrawPreparation'].annotations.destructive_hint)   # left to the client's cautious default

    def test_annotations_change_neither_the_tool_lists_nor_role_gating(self):
        staff, owner = self.tools(STAFF), self.tools(OWNER)
        self.assertFalse(HIDDEN_FROM_STAFF & set(staff))
        self.assertTrue(HIDDEN_FROM_STAFF - {'openRequest'} <= set(owner))
        self.assertEqual(set(staff), {'findCustomers', 'customerOverview', 'invoices', 'ownerContext', 'cases', 'caseDetails', 'whereIs', 'prepareCustomer',
                                      'compareExtension', 'workQueue', 'listRequests', 'prepareHoldingMessage', 'assessRequest', 'proposeImport',
                                      'whatIsNeeded', 'comparableCases', 'customerStatus'})   # as before the annotations, plus the S3 read tools (on by default since S6a)
        for tool in list(staff.values()) + list(owner.values()):
            self.assertEqual(tool.input_schema['type'], 'object')
            self.assertIn('message', tool.input_schema['properties'])
        with self.assertRaisesRegex(MCPError, 'Unknown tool: prepareDecision'):
            self.call(STAFF, 'prepareDecision', {'outcome': 'approve', 'requestId': SERVER['case']})

    def test_a_tool_not_offered_is_refused(self):
        for token, name in ((STAFF, 'prepareDecision'), (STAFF, 'openRequest')):
            with self.assertRaisesRegex(MCPError, 'Unknown tool: ' + name):
                self.call(token, name, {'outcome': 'approve', 'requestId': SERVER['case']})

    def test_a_records_refusal_is_an_error_result(self):
        error, result = self.call(OWNER, 'caseDetails', {'requestId': 'req_unknown'})
        self.assertTrue(error)
        self.assertEqual(set(result), {'error', 'message'})

    def test_a_bad_or_missing_token_is_401(self):
        for headers in ({'Authorization': 'Bearer made-up'}, {'Authorization': OWNER}, {'Authorization': 'Basic ' + OWNER}, {}):
            r = httpx2.post(self.url, json=INITIALIZE, headers={**headers, 'Accept': 'application/json, text/event-stream'})
            self.assertEqual(r.status_code, 401, headers)

    def test_the_public_host_is_accepted_and_others_are_not(self):
        sent = {'Authorization': 'Bearer ' + OWNER, 'Accept': 'application/json, text/event-stream'}
        self.assertEqual(httpx2.post(self.url, json=INITIALIZE, headers={**sent, 'Host': 'nucleon.dracooz.top', 'Origin': PUBLIC}).status_code, 200)
        with self.assertLogs('mcp.server.transport_security', 'WARNING'):
            self.assertEqual(httpx2.post(self.url, json=INITIALIZE, headers={**sent, 'Host': 'elsewhere.example'}).status_code, 421)

    def test_the_records_cookie_is_cached_per_role(self):
        self.mcp.cookies.clear()
        with mock.patch.object(self.mcp, 'sign_in', wraps=self.mcp.sign_in) as signed:
            self.tools(OWNER)
            self.call(OWNER, 'workQueue', {})
            self.tools(STAFF)
            self.call(STAFF, 'workQueue', {})
        self.assertEqual(sorted(c.args[0] for c in signed.call_args_list), ['owner', 'staff'])
        self.assertEqual(set(self.mcp.cookies), {'owner', 'staff'})

    def test_an_expired_session_signs_in_again(self):
        self.mcp.cookies['owner'] = 'nucleon_owner=expired'
        error, _ = self.call(OWNER, 'workQueue', {})
        self.assertFalse(error)
        self.assertNotEqual(self.mcp.cookies['owner'], 'nucleon_owner=expired')


class ConfigTests(unittest.TestCase):
    def test_placeholder_tokens_are_refused(self):
        with tempfile.TemporaryDirectory() as d:
            config = Path(d) / 'lab.json'
            config.write_text(EXAMPLE.read_text())
            with self.assertRaisesRegex(ValueError, 'mcpTokens'):
                load(config)
            config.write_text(json.dumps({**json.loads(EXAMPLE.read_text()), 'mcpTokens': {OWNER: 'owner'}, 'recordsLog': 'records.log'}))
            self.assertEqual(load(config)['recordsLog'], str((Path(d) / 'records.log').resolve()))


    def test_records_codes_are_role_to_code(self):
        with tempfile.TemporaryDirectory() as d:
            config = Path(d) / 'lab.json'
            for codes in (['owner-code'], {'owner': 5}, {'operator': 'op-code'}, 'owner-code'):
                config.write_text(json.dumps({'recordsCodes': codes}))
                with self.assertRaisesRegex(ValueError, 'recordsCodes', msg=codes):
                    load(config)
            config.write_text(json.dumps({'recordsCodes': {'owner': 'o-code', 'staff': 's-code'}}))
            self.assertEqual(load(config)['recordsCodes'], {'owner': 'o-code', 'staff': 's-code'})


    def test_the_example_reads_the_codes_from_the_records_log(self):
        example = json.loads(EXAMPLE.read_text())
        self.assertIsInstance(example['recordsLog'], str)
        self.assertNotIn('recordsCodes', example)


class ExposureTests(unittest.TestCase):
    def test_only_read_and_prepare_kinds_and_the_named_acts_are_exposed(self):
        """Fail closed: a kind the Lab does not know, or an act not named in ACTS, is never exposed."""
        registry = {'tools': [{'name': 'findCustomers', 'kind': 'read'}, {'name': 'prepareDecision', 'kind': 'prepare'},
                              {'name': 'decide', 'kind': 'act'}, {'name': 'withdrawPreparation', 'kind': 'act'}, {'name': 'openRequest', 'kind': 'act'},
                              {'name': 'sendEmail', 'kind': 'external'}, {'name': 'unlabelled'}, {'name': 'openRequest', 'kind': 'read'}]}
        self.assertEqual([t['name'] for t in exposed(registry)], ['findCustomers', 'prepareDecision', 'withdrawPreparation'])


class AnnotationTests(unittest.TestCase):
    def test_read_only_is_a_fail_closed_allow_list(self):
        self.assertTrue(annotations_for('invoices').read_only_hint)
        for name in ('assessRequest', 'prepareDecision', 'withdrawPreparation', 'requestSuggestion', 'someNewReadTool', ''):
            self.assertIs(annotations_for(name).read_only_hint, False, name)
        self.assertFalse(READ_ONLY & ACTS)
        self.assertNotIn('assessRequest', READ_ONLY)   # a read in kind that keeps the latest assessment on the case

    def test_the_hints_serialize_as_the_protocol_names(self):
        self.assertEqual(annotations_for('invoices').model_dump(by_alias=True, exclude_none=True), {'readOnlyHint': True, 'openWorldHint': False})
        self.assertEqual(annotations_for('prepareDecision').model_dump(by_alias=True, exclude_none=True),
                         {'readOnlyHint': False, 'destructiveHint': False, 'openWorldHint': False})


class CodesTests(unittest.TestCase):
    def test_the_latest_start_wins(self):
        log = ('t0 URL: http://127.0.0.1:1\nSTAFF access code: old-a\nOWNER access code: old-b\nSTAFF service code: old-s\nOWNER service code: old-o\n'
               't1 Workspace: practice\nt1 URL: http://127.0.0.1:1\nSTAFF access code: person-s\nOWNER access code: person-o\nOPERATOR access code: op\n'
               'STAFF service code: new-s\nOWNER service code: new-o\n')
        self.assertEqual(codes_from_log(log), {'staff': 'new-s', 'owner': 'new-o'})   # the service codes; a person's access code is never read here
        self.assertEqual(codes_from_log('t URL: http://127.0.0.1:1\nSTAFF access code: a\nOWNER access code: b\n'), {})   # a records instance with none
        self.assertEqual(codes_from_log(log + 't2 URL: http://127.0.0.1:1\n'), {})   # a start whose codes are not printed yet

    def test_the_log_wins_and_records_codes_fill_in(self):
        with tempfile.TemporaryDirectory() as d:
            config = {'recordsCodes': {'owner': 'set-o', 'staff': 'set-s'}, 'recordsLog': d + '/records.log'}
            self.assertEqual(LabMCP(config, None).codes(), {'owner': 'set-o', 'staff': 'set-s'})   # no log
            Path(config['recordsLog']).write_text('t URL: http://127.0.0.1:1\nOWNER access code: person-o\nOWNER service code: new-o\n')
            self.assertEqual(LabMCP(config, None).codes(), {'owner': 'new-o', 'staff': 'set-s'})


if __name__ == '__main__':
    unittest.main()
