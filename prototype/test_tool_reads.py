"""What the read and prepare tools return over the tool surface (POST api/tools/<name>), each figure written by code: a customer's
position with the mark each amount carries, the cases with plain labels and links, what staff may read of the owner's context, where
a task is done in the app, and a customer prepared as a draft and never created. Ported from the tests that asked the same things
through the Records desk chat (removed on 31 Oct 2026). All data is fictional. No real model is called."""
import unittest

from coordinator import STAFF_SEE, WHERE_IS
from server import case_label
from test_helpers import NAMED, REQUEST, SHARED, tell_owner
from test_payments import PaymentCase


class ToolReadTests(PaymentCase):
    def run_tool(self, tool, role='staff', key=None, message=None, current=None, **args):
        body = {'args': args, **({'message': message} if message is not None else {}), **({'current': current} if current else {})}
        status, out, _ = self.call('/api/tools/' + tool, body, role, key or tool + str(sorted(args.items())) + role + str(message))
        self.assertEqual(status, 200, out)
        return out

    def ok(self, tool, role='staff', **kw):
        out = self.run_tool(tool, role, **kw)
        self.assertTrue(out['ok'], out)
        return out['result']

    def names(self):
        return sorted(c['name'] for c in self.call('/api/records', role='owner')[1]['customers'])

    # ---------------------------------------------------------------- amounts, each with the mark Records gives it

    def test_the_overview_gives_code_written_amounts_with_marks(self):
        self.ready()
        part = self.invoice('INV-1')
        stated = self.invoice('INV-2', total='500.00', stillOwed='450.00', stillOwedAsOf='2026-10-15')
        unknown, paid = self.invoice('INV-3', total='300.00', issueDate='2026-10-05'), self.invoice('INV-4', total='200.00')   # INV-3 is issued after the others: oldest-first leaves it whole
        self.allocate(self.pay('700.00'), (part, '400.00'), (paid, '200.00'))
        o = self.ok('customerOverview', customerId=self.bayside['id'])
        self.assertEqual((o['customerId'], o['name'], o['asOf']), (self.bayside['id'], 'Bayside Café', '2026-10-18'))
        self.assertEqual((o['recordedNet']['amount'], o['notAllocated']['amount'], o['completeTo']), ('AUD 1,300.00', 'AUD 100.00', {'invoices': None, 'payments': None}))
        # the settled INV-4 is not open; each mark is the one Records shows (at most, stated as of a date), and where none is recorded the
        # replay's remainder, worked out (INV-3: nothing is applied to it, 100.00 not allocated goes to the oldest)
        self.assertEqual([(i['reference'], i['status'], i['stillOwed'], i['mark'], i['amountAsOf']) for i in o['invoices']],
                         [('INV-1', 'open', 'AUD 600.00', 'at most, from allocated payments', None), ('INV-2', 'open', 'AUD 450.00', 'stated as of Thu 15 Oct', '2026-10-15'),
                          ('INV-3', 'open', 'AUD 300.00', 'worked out', None)])
        self.assertEqual(o['openCount'], 3)
        self.assertEqual(self.minor(self.positions()['customers'][self.bayside['id']]['recordedNet']), '130000')

    def test_the_balance_line_is_written_by_code_whole(self):
        self.ready()
        self.invoice('INV-1', dueDate='2026-10-10', stillOwed='1000.00', stillOwedAsOf='2026-10-10')
        self.invoice('INV-2', total='300.00', dueDate='2026-11-30', issueDate='2026-10-05')   # issued after INV-1: the 250.00 not allocated goes to INV-1 first
        self.pay('250.00')
        line = self.ok('customerOverview', customerId=self.bayside['id'])['balanceLine']
        self.assertEqual(line, 'Owed now AUD 1,050.00 (worked out; invoices not confirmed complete; payments not confirmed complete): AUD 750.00 (worked out) '
                               'overdue; AUD 300.00 (worked out) not yet due. '   # no opening balance: the recorded net equals owed now and is not repeated
                               'Still owed per invoice: INV-1 AUD 1,000.00 (stated as of Sat 10 Oct); INV-2 AUD 300.00 (worked out).')

    def test_a_customer_with_no_invoices_is_reported_as_having_none_recorded(self):
        self.ready()
        riverside = self.add_customer('Riverside Bakery')
        result = self.ok('customerOverview', customerId=riverside['id'])
        self.assertEqual((result['invoiceCount'], result['recordsExist']), (0, False))
        self.assertEqual(result['balanceLine'], 'No invoices are recorded for Riverside Bakery.')   # no amount to quote, not "owes AUD 0.00"

    # ---------------------------------------------------------------- cases, with plain labels

    def test_a_case_label_names_the_approved_date_as_the_case_list_does(self):
        case = {'status': 'completed', 'outcome': 'approve', 'approvedDueDate': '2026-10-18', 'aiStatus': 'mocked'}
        self.assertEqual((case_label(case, 'staff'), case_label({**case, 'approvedDueDate': None}, 'owner')), ('Approved to Sun 18 Oct', 'Approved'))

    def test_the_cases_tool_lists_the_cases_with_plain_labels_and_links(self):
        self.ready()
        self.add_invoice(self.bayside)
        r = self.create(REQUEST)
        self.wait_status(r, ('awaiting_owner',))
        item = {'requestId': r['id'], 'invoiceReference': 'DEMO-501', 'link': '#/case/' + r['id']}
        staff = self.ok('cases', 'staff', customerId=self.bayside['id'])
        self.assertEqual((staff['caseCount'], [{k: x[k] for k in item} for x in staff['cases']], staff['cases'][0]['status']), (1, [item], 'With the owner'))
        owner = self.ok('cases', 'owner', customerId=self.bayside['id'])
        self.assertEqual(owner['cases'][0]['status'], 'Needs your decision')
        by_reference = self.ok('cases', 'staff', reference='DEMO-501')
        self.assertEqual([x['requestId'] for x in by_reference['cases']], [r['id']])
        none = self.ok('cases', 'staff', reference='DEMO-777')
        self.assertEqual((none['caseCount'], none['reference']), (0, 'DEMO-777'))   # the reference it looked for is in its result

    # ---------------------------------------------------------------- what staff may read of the owner's context

    def test_staff_get_only_shared_context_and_no_hint_that_more_exists(self):
        self.ready()
        private = [x['quote'] for x in tell_owner(self, NAMED, 'n')['lines']]
        result = self.ok('ownerContext', 'staff', customerId=self.bayside['id'])
        self.assertEqual((result['lines'], result['note'], 'message' in result), ([], STAFF_SEE, False))   # a message made the live model stop reading (21 Oct)
        self.assertNotRegex(str(result), r'(?i)private|more')
        shared = [x['quote'] for x in tell_owner(self, SHARED, 's', visibility='staff')['lines']][0]
        lines = self.ok('ownerContext', 'staff', customerId=self.bayside['id'])['lines']
        self.assertEqual([(x['kind'], x['quote'], x['saidOn'], x['until'], x['expired']) for x in lines], [('observation', shared, '2026-10-18', None, False)])
        everything = str([self.ok('customerOverview', 'staff', customerId=self.bayside['id']), self.ok('cases', 'staff', customerId=self.bayside['id']), lines])
        for quote in private:
            self.assertNotIn(quote, everything)
        owner = self.ok('ownerContext', 'owner', customerId=self.bayside['id'])
        self.assertEqual(sorted(x['quote'] for x in owner['lines']), sorted(private + [shared]))

    def test_each_role_may_run_only_its_own_action_tool_and_nothing_is_stored_by_a_refusal(self):
        self.ready()
        status, body, _ = self.call('/api/tools/interpretStatement', {'args': {'text': NAMED}, 'message': NAMED}, 'staff', 'i1')
        self.assertEqual((status, body['error'], self.app.statements()), (403, 'FORBIDDEN', []))
        status, body, _ = self.call('/api/tools/openRequest', {'args': {'text': REQUEST}, 'message': REQUEST}, 'owner', 'o1')
        self.assertEqual((status, body['error'], self.app.records()), (403, 'FORBIDDEN', []))
        self.assertEqual(self.call('/api/tools/sendMessage', {'args': {'to': 'Bayside'}}, 'staff', 'm1')[0], 404)   # a made-up tool name

    # ---------------------------------------------------------------- navigation

    def test_where_is_gives_the_place_for_each_task_and_staff_are_sent_to_the_statements(self):
        self.ready()
        place = self.ok('whereIs', topic='addCustomer')
        self.assertEqual((place['topic'], place['route'], place['label'], place['steps']), ('addCustomer', '#/customers', 'Add customer', WHERE_IS['addCustomer']['steps']))
        for topic, route in (('allocatePayment', '#/customers'), ('revertImport', '#/imports'), ('signOut', None)):   # sign out: a button on every page
            self.assertEqual(self.ok('whereIs', topic=topic).get('route'), route, topic)
        self.assertEqual([self.ok('whereIs', role, topic='completeness')['label'] for role in ('staff', 'owner')], ['Completeness statements', 'Confirm completeness'])

    # ---------------------------------------------------------------- a customer is prepared as a draft, never created by the agent

    def test_a_new_customer_is_prepared_as_a_draft_and_nothing_is_created(self):
        self.ready()
        before = self.names()
        draft = self.ok('prepareCustomer', key='d1', message='add Riverside Bakery as a customer', name='Riverside Bakery')
        self.assertEqual(draft['draft'], {'name': 'Riverside Bakery'})
        owner = self.ok('prepareCustomer', 'owner', key='d2', message='Create a customer called Riverside Bakery.', name='Riverside Bakery')
        self.assertEqual(owner['draft'], {'name': 'Riverside Bakery'})
        self.assertEqual((self.names(), self.app.statements()), (before, []))   # the agent created nothing

    def test_a_customer_name_not_written_in_the_message_is_refused_and_case_and_accents_aside_the_name_as_written_passes(self):
        self.ready()
        out = self.run_tool('prepareCustomer', key='r1', message='Please add a new customer for me.', name='Riverside Bakery')
        self.assertEqual((out['ok'], out['error']), (False, 'INVALID_ARGUMENT'))
        self.assertNotIn('Riverside Bakery', self.names())
        self.assertTrue(self.run_tool('prepareCustomer', key='r2', message='add riverside   BAKERY as a customer', name='Riverside Bakery')['ok'])
        self.assertTrue(self.run_tool('prepareCustomer', key='r3', message='add Creperie Lune as a customer', name='Crêperie Lune')['ok'])   # typed without the accent

    def test_a_customer_already_in_the_records_is_surfaced_and_no_draft_is_given(self):
        self.ready()
        for n, text in enumerate(('add bayside cafe as a customer', 'Add Bayside as a customer')):   # by name key; by find_customers
            result = self.ok('prepareCustomer', key='e' + str(n), message=text, name='Bayside Café' if n == 0 else 'Bayside')
            self.assertEqual(result['existing'], [{'customerId': self.bayside['id'], 'name': 'Bayside Café', 'code': self.bayside['displayCode']}], text)
            self.assertNotIn('draft', result)
        self.assertEqual(self.names(), ['Bayside Café', 'Coastline Foods'])

    # ---------------------------------------------------------------- which customer

    def test_find_customers_reads_a_name_without_its_accent_and_gives_up_to_five_names_for_an_unknown_one(self):
        self.ready()
        self.assertEqual([m['name'] for m in self.ok('findCustomers', query='bayside cafe')['matches']], ['Bayside Café'])
        for name in ('Harbor Bistro', 'Hilltop Deli', 'Riverside Grocer', 'Seaview Kiosk'):
            self.add_customer(name)
        unknown = self.ok('findCustomers', query='Harbour Lounge')
        self.assertEqual((unknown['count'], unknown['matches'], len(unknown['similar'])), (0, [], 5))
        self.assertEqual(unknown['similar'][0], 'Harbor Bistro')   # the closest name first


if __name__ == '__main__':
    unittest.main()
