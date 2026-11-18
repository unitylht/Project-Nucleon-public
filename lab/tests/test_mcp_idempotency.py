"""MCP operation identity: a client that sends _meta nucleon.lab/idempotencyKey names its operation, and the records run it once (bound to
the token and role that sent it); without the key every call is a new operation. Same harness as test_mcp (the Lab on a scratch port,
against the scratch records server, so the duplicates below are true end to end). Fictional data only; tokens here are test strings."""
import json
import re
import time
import unittest
import uuid
from unittest import mock

import httpx2
from mcp.shared.exceptions import MCPError

from lab.mcp_server import IDEMPOTENCY_META, OPERATION_META, READ_ONLY, LabMCP
from harness import SERVER, setUpModule, tearDownModule   # noqa: F401 (the scratch records server, for this module)
import test_mcp
from test_mcp import OWNER, STAFF

OPERATION = OPERATION_META


class OperationIdentityTests(unittest.TestCase):
    setUpClass, tearDownClass = test_mcp.MCPTests.__dict__['setUpClass'], test_mcp.MCPTests.__dict__['tearDownClass']
    client, tools, raw = test_mcp.MCPTests.client, test_mcp.MCPTests.tools, test_mcp.MCPTests.raw

    def send(self, token, name, args, key=None, **meta):
        """The tool's result, with _meta idempotencyKey `key` when given, and the records key the Lab sent for it."""
        if key is not None:
            meta[IDEMPOTENCY_META] = key
        with mock.patch.object(self.mcp.records, 'call', wraps=self.mcp.records.call) as sent:
            out = self.client(token, lambda s: s.call_tool(name, args, meta=meta or None))
        [call] = sent.call_args_list
        return out, call.kwargs['key']

    def settled(self):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            case = json.loads(self.raw(OWNER, 'caseDetails', {'requestId': SERVER['case']}).content[0].text).get('case', {})
            if case.get('status') == 'awaiting_owner':
                return case
            time.sleep(0.1)
        self.fail('the scratch case did not settle')

    def test_a_client_key_gives_the_same_records_key_on_a_retry_and_another_for_another_token_role_or_key(self):
        _, first = self.send(STAFF, 'workQueue', {}, key='client-key-0001')
        _, again = self.send(STAFF, 'workQueue', {}, key='client-key-0001')
        _, other_key = self.send(STAFF, 'workQueue', {}, key='client-key-0002')
        _, other_token = self.send(OWNER, 'workQueue', {}, key='client-key-0001')
        self.assertRegex(first, r'mcpc-[0-9a-f]{40}')
        self.assertEqual(first, again)
        self.assertEqual(len({first, other_key, other_token}), 3)
        for token in (STAFF, OWNER):   # the token is never in what the records are sent
            self.assertNotIn(token, first + other_token)
        headers = {'authorization': 'Bearer ' + STAFF}
        self.assertEqual(LabMCP.operation_key(headers, 'staff', 'client-key-0001'), first)
        self.assertNotEqual(LabMCP.operation_key(headers, 'owner', 'client-key-0001'), first)   # the role is part of it too

    def test_without_a_client_key_each_call_is_a_new_operation_even_with_identical_arguments(self):
        keys = [self.send(STAFF, 'workQueue', {})[1] for _ in range(2)]
        self.assertTrue(all(re.fullmatch(r'mcp-[0-9a-f]{32}', k) for k in keys), keys)
        self.assertNotEqual(*keys)
        uuid.UUID(keys[0][4:])

    def test_an_invalid_client_key_is_refused_before_anything_is_sent_to_the_records(self):
        for bad in ('', 'short', 'x' * 129, 'has space 1234', 'new\nline-1234', 'ünïcode-1234', 12345678, ['client-key-0001']):
            with mock.patch.object(self.mcp.records, 'call') as sent:
                with self.assertRaisesRegex(MCPError, 'must be 8 to 128 characters', msg=repr(bad)):
                    self.client(STAFF, lambda s: s.call_tool('workQueue', {}, meta={IDEMPOTENCY_META: bad}))
            sent.assert_not_called()
        for good in ('a' * 8, 'A.b_c:d-e' + '1' * 9, 'k' * 128):
            self.assertFalse(self.send(STAFF, 'workQueue', {}, key=good)[0].is_error, good)

    def test_the_arguments_never_name_the_operation(self):
        _, first = self.send(STAFF, 'workQueue', {}, key='client-key-0003')
        _, with_argument = self.send(STAFF, 'workQueue', {IDEMPOTENCY_META: 'client-key-0003', 'idempotencyKey': 'client-key-0003'})
        self.assertTrue(with_argument.startswith('mcp-'))
        self.assertNotEqual(first, with_argument)

    def test_a_read_result_is_unchanged_and_a_non_read_result_says_which_operation_it_was(self):
        plain, sent = self.send(STAFF, 'workQueue', {})
        keyed, _ = self.send(STAFF, 'workQueue', {}, key='client-key-0004')
        for out in (plain, keyed):
            self.assertIn('workQueue', READ_ONLY)
            self.assertIsNone(out.meta)
        self.assertEqual([c.text for c in plain.content], [c.text for c in keyed.content])
        self.settled()
        args = {'requestId': SERVER['case']}
        server_made, _ = self.send(STAFF, 'assessRequest', args)   # a read in kind, not read-only
        self.assertEqual(server_made.meta, {OPERATION: {'keySource': 'server', 'replayed': False}})
        first, _ = self.send(STAFF, 'assessRequest', args, key='client-key-0005')
        again, _ = self.send(STAFF, 'assessRequest', args, key='client-key-0005')
        self.assertEqual((first.meta, again.meta), ({OPERATION: {'keySource': 'client', 'replayed': False}}, {OPERATION: {'keySource': 'client', 'replayed': True}}))
        self.assertEqual(first.content[0].text, again.content[0].text)   # the stored answer, as the records gave it
        self.assertEqual(json.loads(again.content[0].text)['version'], json.loads(first.content[0].text)['version'])
        fresh, _ = self.send(STAFF, 'assessRequest', args, key='client-key-0006')   # a new key: a new operation, a new version
        self.assertEqual(json.loads(fresh.content[0].text)['version'], json.loads(first.content[0].text)['version'] + 1)

    def test_a_duplicate_mcp_call_with_the_same_key_prepares_once_end_to_end(self):
        self.settled()
        args = {'requestId': SERVER['case'], 'outcome': 'approve', 'days': 7, 'message': 'approve 7 days'}
        first, key = self.send(OWNER, 'prepareDecision', args, key='client-key-0007')
        again, same = self.send(OWNER, 'prepareDecision', args, key='client-key-0007')
        self.assertEqual((first.is_error, again.is_error), (False, False), (first.content, again.content))
        self.assertEqual(key, same)
        self.assertEqual((first.meta[OPERATION]['replayed'], again.meta[OPERATION]['replayed']), (False, True))
        one, two = (json.loads(x.content[0].text) for x in (first, again))
        self.assertEqual(one, two)
        version = one['prepared']['version']
        self.assertEqual(json.loads(self.raw(OWNER, 'caseDetails', {'requestId': SERVER['case']}).content[0].text)['case']['preparedDecision']['version'], version)
        # other arguments under the key: the records' refusal arrives as an error result with its code, and nothing is prepared
        other, _ = self.send(OWNER, 'prepareDecision', {**args, 'days': 9, 'message': 'approve 9 days'}, key='client-key-0007')
        self.assertTrue(other.is_error)
        self.assertEqual(set(json.loads(other.content[0].text)), {'error', 'message'})
        self.assertEqual(json.loads(other.content[0].text)['error'], 'KEY_REUSED')
        self.assertEqual(other.meta, {OPERATION: {'keySource': 'client', 'replayed': False}})
        # the same text from the staff token is not the owner's operation, and the key keeps no other client's answer
        new, _ = self.send(OWNER, 'prepareDecision', args, key='client-key-0008')
        self.assertEqual(json.loads(new.content[0].text)['prepared']['version'], version + 1)   # a new key is a new operation
        cleared, _ = self.send(OWNER, 'withdrawPreparation', {'requestId': SERVER['case']}, key='client-key-0009')
        self.assertFalse(cleared.is_error)

    def test_no_token_is_still_401_whatever_the_meta(self):
        body = {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {'name': 'workQueue', 'arguments': {}, '_meta': {IDEMPOTENCY_META: 'client-key-0010'}}}
        for headers in ({}, {'Authorization': 'Bearer made-up'}):
            r = httpx2.post(self.url, json=body, headers={**headers, 'Accept': 'application/json, text/event-stream'})
            self.assertEqual(r.status_code, 401, headers)


if __name__ == '__main__':
    unittest.main()
