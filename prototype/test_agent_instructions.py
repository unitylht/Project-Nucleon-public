"""The ADA Staff agent's instructions (integrations/librechat/agents): one source, instructions_staff.txt, copied into update_ada_agent_hints.js and shown in
the integration README; the model bench reads the same file. The script is never run here (it changes the live LibreChat Mongo); this checks the copies agree
and that the rules the agent relies on are in the text. Compatible with Python 3.9."""
import importlib.util
import json
import re
import unittest
from pathlib import Path

AGENTS = Path(__file__).resolve().parent.parent / 'integrations' / 'librechat' / 'agents'
spec = importlib.util.spec_from_file_location('sync_instructions', AGENTS / 'sync_instructions.py')
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class InstructionsTests(unittest.TestCase):
    def test_the_script_and_the_readme_carry_exactly_the_text_file(self):
        self.assertEqual(sync.synced(), sync.SCRIPT.read_text(encoding='utf-8'), 'run integrations/librechat/agents/sync_instructions.py')
        found = re.search(r'const LINES = (\[.*?\n\]);', sync.SCRIPT.read_text(encoding='utf-8'), re.S).group(1)
        self.assertEqual(json.loads(re.sub(r',\s*\]$', ']', found)), sync.paragraphs())
        self.assertEqual(sync.synced_readme(), sync.README.read_text(encoding='utf-8'), 'run integrations/librechat/agents/sync_instructions.py')
        readme = (AGENTS.parent / 'README.md').read_text(encoding='utf-8')
        for paragraph in sync.paragraphs():
            self.assertIn(paragraph, readme)

    def test_the_rules_the_agent_relies_on_are_in_the_text(self):
        text = sync.instructions()
        # S7 phase B (31 Oct 2026): resolve-only steps with an explicit ambiguity check; no assessDecision or whatIsNeeded step
        for phrase in ('never invent', 'exactly one kind', 'ask Staff exactly hint.question', 'hint.options', 'classify the message', 'calling no decision tool',
                       'resolveDecision, once', 'Do not call assessDecision or whatIsNeeded', 'statusText', 'nextStep', 'never say something is approved',
                       'Nothing is ever sent to the customer', 'missing information is not a reason to escalate', 'decisionStatus'):
            self.assertIn(phrase, text)
        self.assertNotIn('\n', text)
        self.assertLess(len(text), 4000)

    def test_the_script_names_only_the_staff_server_and_the_read_tools(self):
        script = sync.SCRIPT.read_text(encoding='utf-8')
        self.assertIn("'nucleon-local-staff'", script)
        self.assertIn("['whatIsNeeded', 'customerStatus']", script)
        self.assertNotIn('resolveDecision_mcp', script)


class OwnerAgentTests(unittest.TestCase):
    """The Owner agent (agents/seed_owner_agent_3080.js, never run here): every tool is a read the Owner role is offered, and the MCP entry is the owner-token one."""
    SEED = (AGENTS / 'seed_owner_agent_3080.js').read_text(encoding='utf-8')

    def tools(self):
        return re.search(r"const tools = \[(.*?)\]\.map", self.SEED, re.S).group(1).replace("'", '').replace(' ', '').split(',')

    def test_every_tool_is_a_read_for_the_owner(self):
        from coordinator import CAPABILITIES
        rows = {c['name']: c for c in CAPABILITIES}
        tools = self.tools()
        self.assertEqual(tools, ['decisionStatus', 'customerStatus', 'comparableCases', 'policyBacktest', 'impactSummary', 'doctor', 'modelStatus', 'cases', 'workQueue', 'customerOverview', 'invoices', 'findCustomers'])
        for name in tools:
            self.assertEqual(rows[name]['kind'], 'read', name)
            self.assertIn('owner', rows[name]['roles'], name)
            self.assertFalse(rows[name]['needsConfirmation'], name)
        for forbidden in ('resolveDecision', 'assessDecision', 'prepareRequest', 'prepareDecision', 'requestSuggestion', 'answerConcern', 'withdrawPreparation'):
            self.assertNotIn(forbidden, self.SEED.split('const instructions')[0].split('const tools')[1])

    def test_the_instructions_carry_the_s6a_rules(self):
        for phrase in ('decisionCasesForYou', 'never a name or a code in requestId', 'After one NOT_FOUND', 'Setup -> Agent tools', 'policyBacktest with {}',
                       "state the case\\'s current status from decisionStatus in one sentence"):
            self.assertIn(phrase, self.SEED)

    def test_the_agent_uses_the_owner_server_and_sends_the_owner_to_the_pages(self):
        self.assertIn("const SRV = 'nucleon-local-owner'", self.SEED)
        self.assertIn("'Nucleon ADA Owner (Qwen)'", self.SEED)
        for link in ("RECORDS + '/#/review)", "RECORDS + '/#/delegation)"):
            self.assertIn(link, self.SEED)
        self.assertIn('never say or imply that you did', self.SEED)
        self.assertNotIn("principalType: 'role'", self.SEED)   # not shared with the USER role
        yaml = (AGENTS.parent / 'librechat.yaml.example').read_text(encoding='utf-8')
        entry = yaml.split('  nucleon-local-owner:')[1].split('\n\n')[0]
        self.assertIn('http://host.docker.internal:8630/mcp/', entry)
        self.assertIn('${NUCLEON_LOCAL_OWNER_MCP_TOKEN}', entry)
        self.assertIn('chatMenu: false', entry)
        staff = yaml.split('  nucleon-local-staff:')[1].split('  # The Owner')[0]
        self.assertIn('http://host.docker.internal:8630/mcp/', staff)


if __name__ == '__main__':
    unittest.main()
