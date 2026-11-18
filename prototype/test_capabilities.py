"""The agent's capabilities: a registry says what each tool does, for whom, of what kind and whether a person confirms its effect;
the owner turns tools off and on under Setup. The tool surface lists, and the server runs, only the tools on for this person's
role. All data is fictional; no real model is called."""
import json
import unittest
from unittest import mock

from coordinator import CAPABILITIES, DESK_TOOLS, check_capabilities, tools_for
from server import DeskTools
from test_payments import PaymentCase

OFF_BY_DEFAULT = ('prepareRequest', 'actionStatus', 'assessDecision', 'resolveDecision', 'decisionStatus')   # S3 read tools are on by default since S6a (test_s3_tools)   # controlled actions and delegation: in no registry until the owner turns them on (test_controlled_actions, test_delegation)
EXTERNAL = {'name': 'sendEmail', 'kind': 'external', 'roles': ['owner'], 'needsConfirmation': True, 'defaultEnabled': True,
            'description': 'Sends an email to a customer.'}


def names(tools):
    return [t['function']['name'] for t in tools]


class RegistryTests(unittest.TestCase):
    def test_the_registry_lists_every_implemented_tool_with_its_kind_roles_and_confirmation(self):
        both = ['staff', 'owner']
        self.assertEqual({c['name']: (c['kind'], c['roles'], c['needsConfirmation']) for c in CAPABILITIES}, {
            'findCustomers': ('read', both, False), 'customerOverview': ('read', both, False), 'invoices': ('read', both, False),
            'ownerContext': ('read', both, False), 'cases': ('read', both, False), 'caseDetails': ('read', both, False),
            'whereIs': ('read', both, False), 'prepareCustomer': ('prepare', both, True), 'openRequest': ('act', ['staff'], False),
            'interpretStatement': ('prepare', ['owner'], True), 'prepareDecision': ('prepare', ['owner'], True),
            'requestSuggestion': ('act', ['owner'], False), 'compareExtension': ('read', both, False), 'withdrawPreparation': ('act', ['owner'], False),
            'withdrawRequest': ('act', [], True),
            'workQueue': ('read', both, False), 'listRequests': ('read', both, False), 'prepareHoldingMessage': ('prepare', both, False),
            'raiseConcern': ('act', ['staff'], False), 'answerConcern': ('act', ['owner'], False), 'assessRequest': ('read', both, False), 'actWithinAuthority': ('act', [], True),
            'proposeImport': ('prepare', both, True),
            'applyImportProposal': ('act', [], True),   # offered to no agent: a person presses Import, or staff Act within authority (pressedBy)
            'prepareRequest': ('prepare', ['staff'], True), 'actionStatus': ('read', both, False),   # controlled actions: off by default
            'assessDecision': ('read', ['staff'], False), 'resolveDecision': ('act', ['staff'], False), 'decisionStatus': ('read', both, False),   # delegation: off by default
            'whatIsNeeded': ('read', both, False), 'comparableCases': ('read', both, False), 'customerStatus': ('read', both, False),
            'policyBacktest': ('read', ['owner'], False), 'impactSummary': ('read', ['owner'], False),   # S3 read tools: off by default
            'modelStatus': ('read', ['owner'], False),   # the team's model (research.py), 2 Nov 2026
            'doctor': ('read', ['owner'], False)})   # the Doctor (11 Nov 2026)
        self.assertEqual([c['name'] for c in CAPABILITIES], names(DESK_TOOLS))
        for c in CAPABILITIES:
            self.assertIs(c['defaultEnabled'], c['name'] not in OFF_BY_DEFAULT)
            self.assertRegex(c['description'], r'^[A-Z][^.]+\.$')   # one plain sentence

    def test_each_role_is_offered_its_own_tools(self):
        for role in ('staff', 'owner'):
            mine = [c['name'] for c in CAPABILITIES if role in c['roles'] and c['defaultEnabled']]
            self.assertEqual(names(tools_for(role, None)), mine)
        self.assertNotIn('interpretStatement', names(tools_for('staff', {'interpretStatement': {'enabled': True}})))   # an override never adds a role

    def test_a_tool_turned_off_is_not_offered(self):
        for c in CAPABILITIES:
            self.assertNotIn(c['name'], names(tools_for('owner', {c['name']: {'enabled': False}})))

    def test_a_kind_the_registry_does_not_implement_cannot_be_registered_or_turned_on(self):
        with self.assertRaises(ValueError):
            check_capabilities(CAPABILITIES + [EXTERNAL])
        with self.assertRaises(ValueError):   # every capability names a tool, and every tool has one
            check_capabilities(CAPABILITIES[1:])
        with mock.patch('coordinator.CAPABILITIES', CAPABILITIES + [EXTERNAL]):
            self.assertNotIn('sendEmail', names(tools_for('owner', {'sendEmail': {'enabled': True}})))


class AgentToolsTests(PaymentCase):
    def offered(self, role):
        status, body, _ = self.call('/api/tools', role=role)
        self.assertEqual(status, 200, body)
        return [t['name'] for t in body['tools']]

    def table(self, role='owner'):
        return self.call('/api/agent-tools', role=role)

    def turn(self, tool, enabled, key, role='owner'):
        return self.call('/api/agent-tools', {'tool': tool, 'enabled': enabled}, role, key)

    def test_the_owner_sees_the_table_and_staff_are_refused(self):
        self.ready()
        status, body, _ = self.table()
        self.assertEqual(status, 200, body)
        self.assertEqual(body['tools'], [{**c, 'enabled': c['defaultEnabled']} for c in CAPABILITIES if c['roles']])   # applyImportProposal is no agent's
        self.assertEqual(self.table('staff')[:2], (403, {'error': 'FORBIDDEN', 'message': 'Only the owner manages the agent\'s tools.'}))
        self.assertEqual(self.turn('customerOverview', False, 's1', role='staff')[0], 403)
        self.assertIsNone(self.app.meta('agentTools'))

    def test_turning_a_tool_off_is_checked_kept_once_per_key_and_refused_for_unknown_tools_and_kinds(self):
        self.ready()
        self.assertEqual(self.call('/api/agent-tools', {'tool': 'customerOverview', 'enabled': False}, 'owner')[1]['error'], 'IDEMPOTENCY_REQUIRED')
        for n, body in enumerate(({'tool': 'sendEmail', 'enabled': True}, {'tool': 'reply', 'enabled': False},
                                  {'tool': 'customerOverview', 'enabled': 'no'}, {'enabled': False})):
            status, result, _ = self.call('/api/agent-tools', body, 'owner', 'bad' + str(n))
            self.assertEqual((status, result['error']), (400, 'INVALID_INPUT'), body)
        with mock.patch('coordinator.CAPABILITIES', CAPABILITIES + [EXTERNAL]):   # a kind not implemented: listed off, never turned on
            self.assertEqual(self.table()[1]['tools'][-1], {**EXTERNAL, 'enabled': False})
            status, result, _ = self.turn('sendEmail', True, 'ext')
            self.assertEqual((status, result['error'], result['field']), (400, 'INVALID_INPUT', 'tool'))
        self.assertIsNone(self.app.meta('agentTools'))
        status, body, _ = self.turn('customerOverview', False, 'off')
        self.assertEqual(status, 200, body)
        self.assertEqual([c['name'] for c in body['tools'] if not c['enabled']], ['customerOverview', *OFF_BY_DEFAULT])
        self.assertEqual(self.app.meta('agentTools'), {'customerOverview': {'enabled': False}})
        self.assertEqual(self.turn('customerOverview', False, 'off')[1], body)   # the same key again: the stored result
        self.assertEqual(self.turn('customerOverview', True, 'off')[:2], (409, {'error': 'KEY_REUSED', 'message': 'This key was already used with different input.'}))
        self.assertEqual(self.table()[1], body)

    def test_staff_are_never_offered_owner_tools(self):
        self.ready()
        self.assertEqual(self.offered('staff'), [c['name'] for c in CAPABILITIES if 'staff' in c['roles'] and c['defaultEnabled']])
        self.assertEqual(self.offered('owner'), [c['name'] for c in CAPABILITIES if 'owner' in c['roles'] and c['defaultEnabled']])
        self.assertNotIn('interpretStatement', self.offered('staff'))
        self.assertNotIn('openRequest', self.offered('owner'))
        self.assertIn('openRequest', self.offered('staff'))

    def test_a_tool_turned_off_while_the_model_reads_is_refused_when_it_is_called(self):
        self.ready()
        with self.app.lock:   # the turn starts with whereIs on
            tools = DeskTools(self.app, {'role': 'staff', 'id': 'staff_demo'}, 'Where do I record a payment?', None, None, None)
        self.assertIn('whereIs', tools.specs)
        self.assertEqual(self.turn('whereIs', False, 'off')[0], 200)
        out = tools.execute('whereIs', json.dumps({'topic': 'recordPayment'}))
        self.assertEqual((out.ok, out.executed, out.error, 'navigation' in tools.blocks), (False, False, 'FORBIDDEN', False))
        self.assertNotIn('whereIs', out.result['message'].split('Permitted tools: ')[1])

    def test_a_disabled_tool_is_neither_offered_nor_run_and_comes_back_when_turned_on(self):
        self.ready()
        self.invoice('INV-1')
        args = {'args': {'customerId': self.bayside['id']}}
        self.assertEqual(self.call('/api/tools/customerOverview', args, 'staff')[0], 200)
        self.assertEqual(self.turn('customerOverview', False, 'off')[0], 200)
        self.assertNotIn('customerOverview', self.offered('staff'))
        with mock.patch.object(DeskTools, '_customerOverview', autospec=True, side_effect=DeskTools._customerOverview) as overview:
            status, body, _ = self.call('/api/tools/customerOverview', args, 'staff')   # a caller naming it anyway: refused, never run
        self.assertEqual((status, body['error'], overview.call_count), (403, 'FORBIDDEN', 0))
        # turned on again, it is offered and runs
        self.assertEqual(self.turn('customerOverview', True, 'on')[0], 200)
        self.assertIn('customerOverview', self.offered('staff'))
        status, body, _ = self.call('/api/tools/customerOverview', args, 'staff')
        self.assertEqual((status, body['ok'], body['result']['name']), (200, True, 'Bayside Café'))


if __name__ == '__main__':
    unittest.main()
