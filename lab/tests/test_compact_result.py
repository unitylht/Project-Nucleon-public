"""What the model reads (slice S3): when the records' result holds a `forModel`, the Lab's text item is that compact object (plus `hint`), at most a few
hundred characters; the full result feeds the card only. Every other tool's text is unchanged, a refusal carries its `hint`, and the optional timing log
(config timingLog) gets one line per call with no arguments and no token. Same harness as test_controlled_actions_mcp (the Lab on a scratch port
against the scratch records server). Fictional data only; tokens are test strings."""
import json
import tempfile
import unittest
from pathlib import Path

import httpx2
from mcp.shared.exceptions import MCPError

from lab import card
from lab.mcp_server import LabMCP, TimingLog, model_text
from harness import SERVER, setUpModule, tearDownModule   # noqa: F401 (the scratch records server, for this module)
import test_mcp
from test_mcp import OWNER, STAFF

DECISION_TOOLS = ('assessDecision', 'resolveDecision', 'decisionStatus')
COMPACT_LIMIT = 900   # a decision tool's forModel is at most 800 characters since 8 Nov 2026 (the dates sentence); a hint or the JSON separators may add a little


READ_TOOLS = ('whatIsNeeded', 'comparableCases', 'customerStatus', 'policyBacktest', 'impactSummary')


class CompactResultTests(unittest.TestCase):
    setUpClass, tearDownClass = test_mcp.MCPTests.__dict__['setUpClass'], test_mcp.MCPTests.__dict__['tearDownClass']
    client, tools, raw = test_mcp.MCPTests.client, test_mcp.MCPTests.tools, test_mcp.MCPTests.raw

    def records(self):
        return httpx2.Client(base_url=SERVER['url'], timeout=30)

    def switch(self, on):
        with self.records() as c:
            for name in DECISION_TOOLS:
                r = c.post('/api/agent-tools', headers={'Cookie': SERVER['owner'], 'Idempotency-Key': 'compact-' + name + str(on) + str(id(self))}, json={'tool': name, 'enabled': on})
                self.assertEqual(r.status_code, 200, r.text)

    def setUp(self):
        self.switch(True)
        self.addCleanup(self.switch, False)

    def full(self, name, args, cookie=None, key='compact-full'):
        """The records' own result of a tool, as the card is made from it."""
        with self.records() as c:
            r = c.post('/api/tools/' + name, headers={'Cookie': cookie or SERVER['staff'], 'Idempotency-Key': key + name + json.dumps(args, sort_keys=True)}, json={'args': args})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()['result']

    def test_the_text_of_a_decision_tool_is_the_compact_forModel_and_the_card_is_made_from_the_full_result(self):
        args = {'kind': 'extension', 'customerId': 'customer_demo_01', 'invoiceId': 'invoice_demo_101', 'days': 14}
        out = self.raw(STAFF, 'assessDecision', args)
        self.assertEqual([c.type for c in out.content], ['text', 'resource'])
        text = out.content[0].text
        full = self.full('assessDecision', args)
        self.assertGreater(len(json.dumps(full)), 3000)   # the full result is large ...
        self.assertLessEqual(len(text), COMPACT_LIMIT, text)   # ... what the model reads is not
        self.assertEqual(json.loads(text), full['forModel'])
        self.assertEqual(set(json.loads(text)), {'status', 'handling', 'statusText', 'why', 'nextStep', 'keyFacts'})
        for private in ('comparables', 'reliability', 'ownerReason', 'authority', 'communication'):
            self.assertNotIn(private, text)
        self.assertEqual(out.content[1].resource.text, card.card_html('assessDecision', full, self.mcp.config.get('recordsPublicUrl')))   # the card: unchanged, from the full result
        self.assertIn('Nucleon decision card', out.content[1].resource.text)

    def test_resolve_and_status_are_compact_too_for_both_roles_and_their_card_is_unchanged(self):
        args = {'kind': 'extension', 'customerId': 'customer_demo_01', 'invoiceId': 'invoice_demo_101', 'days': 14, 'recommendation': 'approve', 'reasoning': 'Fictional test.'}
        resolved = self.raw(STAFF, 'resolveDecision', args)
        self.assertFalse(resolved.is_error)
        compact = json.loads(resolved.content[0].text)
        self.assertLessEqual(len(resolved.content[0].text), COMPACT_LIMIT)
        case_id = compact['keyFacts']['caseId']
        for token, cookie in ((STAFF, SERVER['staff']), (OWNER, SERVER['owner'])):
            out = self.raw(token, 'decisionStatus', {'caseId': case_id})
            self.assertLessEqual(len(out.content[0].text), COMPACT_LIMIT, out.content[0].text)
            full = self.full('decisionStatus', {'caseId': case_id}, cookie)
            self.assertEqual(json.loads(out.content[0].text), full['forModel'])
            self.assertEqual(out.content[1].resource.text, card.card_html('decisionStatus', full, self.mcp.config.get('recordsPublicUrl')))

    def test_a_refusal_keeps_its_code_and_message_and_carries_the_hint(self):
        out = self.raw(STAFF, 'assessDecision', {'customerId': 'customer_demo_01'})
        self.assertTrue(out.is_error)
        self.assertEqual([c.type for c in out.content], ['text'])
        body = json.loads(out.content[0].text)
        self.assertEqual((body['error'], body['message']), ('INVALID_ARGUMENT', 'Missing argument(s): kind.'))
        self.assertEqual((body['hint']['ask'], body['hint']['options']), ('kind', ['trial_credit', 'extension']))
        self.assertLessEqual(len(out.content[0].text), COMPACT_LIMIT)

    def test_a_tool_without_forModel_keeps_the_records_result_as_it_is(self):
        out = self.raw(STAFF, 'findCustomers', {'query': 'Harbour'})
        self.assertEqual(json.loads(out.content[0].text), self.full('findCustomers', {'query': 'Harbour'}))
        self.assertEqual(model_text({'a': 1, 'b': 'é'}, True), json.dumps({'a': 1, 'b': 'é'}, ensure_ascii=False))
        self.assertEqual(model_text({'forModel': 'text'}, True), json.dumps({'forModel': 'text'}))   # only an object is a compact result
        self.assertEqual(model_text({'forModel': {'s': 1}, 'hint': {'ask': 'kind'}, 'x': 'y'}, True), json.dumps({'s': 1, 'hint': {'ask': 'kind'}}))
        self.assertEqual(model_text({'error': 'E', 'message': 'm', 'forModel': {'s': 1}}, False), json.dumps({'error': 'E', 'message': 'm', 'forModel': {'s': 1}}))   # a refusal is never compacted

    def switch_reads(self, on):
        with self.records() as c:
            for name in READ_TOOLS:
                r = c.post('/api/agent-tools', headers={'Cookie': SERVER['owner'], 'Idempotency-Key': 'compact-read-' + name + str(on) + str(id(self))}, json={'tool': name, 'enabled': on})
                self.assertEqual(r.status_code, 200, r.text)

    def test_the_s3_read_tools_are_on_by_default_then_read_only_by_role_with_a_compact_text(self):
        self.assertEqual(set(READ_TOOLS) & set(self.tools(STAFF)), set(READ_TOOLS[:3]))   # on by default since S6a
        self.switch_reads(False)
        self.assertFalse(set(READ_TOOLS) & (set(self.tools(STAFF)) | set(self.tools(OWNER))))   # the Owner can switch them off
        self.switch_reads(True)
        self.addCleanup(self.switch_reads, True)
        staff, owner = self.tools(STAFF), self.tools(OWNER)
        self.assertEqual(set(READ_TOOLS) & set(staff), set(READ_TOOLS[:3]))
        self.assertEqual(set(READ_TOOLS) & set(owner), set(READ_TOOLS))
        for tools in (staff, owner):
            for name in set(READ_TOOLS) & set(tools):
                self.assertTrue(tools[name].annotations.read_only_hint, name)
        args = {'kind': 'trial_credit', 'customerId': 'customer_demo_02', 'orderAmount': '800.00', 'termsDays': 14}
        out = self.raw(STAFF, 'whatIsNeeded', args)
        self.assertFalse(out.is_error, out.content[0].text)
        self.assertEqual([c.type for c in out.content], ['text'])   # no card for these
        self.assertIsNone(out.meta)   # a read: no operation
        body = json.loads(out.content[0].text)
        self.assertLessEqual(len(out.content[0].text), 600)
        self.assertEqual(set(body), {'status', 'statusText', 'staffCanProvide', 'staffCannotProvide', 'nextStep'})
        owner_only = self.raw(OWNER, 'policyBacktest', {'changes': {'extensions': {'maxDays': 10}}})
        self.assertFalse(owner_only.is_error, owner_only.content[0].text)
        self.assertEqual(json.loads(owner_only.content[0].text)['status'], 'backtest')
        self.assertLessEqual(len(owner_only.content[0].text), 1500)
        impact = self.raw(OWNER, 'impactSummary', {})
        self.assertEqual(json.loads(impact.content[0].text)['dataset'], 'live')
        doc = self.raw(OWNER, 'doctor', {'question': 'came'})   # the Doctor (11 Nov 2026): the model reads only the lines code wrote
        self.assertFalse(doc.is_error, doc.content[0].text)
        body = json.loads(doc.content[0].text)
        self.assertEqual((body['status'], body['question'], set(body)), ('doctor', 'came', {'status', 'question', 'statusText', 'enough', 'facts', 'howToChange', 'currentRules'}))
        self.assertTrue(body['currentRules']['theAgentDecides'] and body['currentRules']['alwaysComesToTheOwner'])   # 12 Nov 2026: the rules in force, in plain words
        self.assertLessEqual(len(doc.content[0].text), 2400)
        with self.assertRaisesRegex(MCPError, 'Unknown tool: doctor'):
            self.raw(STAFF, 'doctor', {})
        with self.assertRaisesRegex(MCPError, 'Unknown tool: policyBacktest'):
            self.raw(STAFF, 'policyBacktest', {})

    def test_the_timing_log_gets_one_line_per_call_without_arguments_or_tokens(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'logs' / 'tool-timing.jsonl'   # the directory is made
            self.mcp.timing = TimingLog(str(path))
            self.addCleanup(setattr, self.mcp, 'timing', None)
            args = {'kind': 'extension', 'customerId': 'customer_demo_01', 'invoiceId': 'invoice_demo_101', 'days': 14}
            self.raw(STAFF, 'assessDecision', args)
            self.raw(STAFF, 'findCustomers', {'query': 'Harbour'})
            self.raw(STAFF, 'assessDecision', {'customerId': 'customer_demo_01'})
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            raw = path.read_text()
        self.assertEqual([(r['tool'], r['role'], r['ok']) for r in rows], [('assessDecision', 'staff', True), ('findCustomers', 'staff', True), ('assessDecision', 'staff', False)])
        self.assertTrue(all(set(r) == {'tool', 'role', 'caseId', 'start', 'durationMs', 'ok', 'resultChars', 'forModelChars'} for r in rows))
        self.assertTrue(rows[0]['forModelChars'] and rows[0]['forModelChars'] <= COMPACT_LIMIT and rows[0]['resultChars'] > rows[0]['forModelChars'] * 4)
        self.assertEqual((rows[1]['forModelChars'], rows[2]['forModelChars']), (None, None))
        self.assertTrue(all(r['durationMs'] >= 0 and r['start'].endswith('+00:00') for r in rows))
        for secret in (STAFF, OWNER, 'customer_demo_01', 'Harbour'):
            self.assertNotIn(secret, raw)

    def test_the_timing_log_is_off_unless_configured_and_never_fails_a_call(self):
        self.assertIsNone(self.mcp.timing)
        self.mcp.timing = TimingLog(__file__ + '/x.jsonl')   # a directory that is a file: the line cannot be written
        self.addCleanup(setattr, self.mcp, 'timing', None)
        with self.assertLogs('lab.mcp_server', 'ERROR'):
            out = self.raw(STAFF, 'findCustomers', {'query': 'Harbour'})
        self.assertFalse(out.is_error)


if __name__ == '__main__':
    unittest.main()
