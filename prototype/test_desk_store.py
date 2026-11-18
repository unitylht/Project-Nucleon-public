"""Coordinator stores: statements, threads and turns, the context retrieved for a customer, and the practice business date.
All data is fictional. No real model is called."""
import unittest
from datetime import date
from pathlib import Path

from records import RecordsError
from server import APIError
from test_records import RecordsCase

OWNER, STAFF, OPERATOR = ({'id': role + '_demo', 'role': role} for role in ('owner', 'staff', 'operator'))


class DeskStoreTests(RecordsCase):
    def ready(self):
        self.start()
        self.practice_ready()
        return self.add_customer()

    def statement(self, quote='They always pay by the end of the month', actor=OWNER, scope=None, visibility='owner', status='confirmed', until=None):
        return self.app.new_statement(actor, quote + '.', thread_id=self.app.general_thread()['id'], scope=scope or {'kind': 'business'},
                                      visibility=visibility, status=status, source={'kind': 'test'},
                                      lines=[{'kind': 'observation', 'quote': quote, 'until': until, 'certainty': None}])

    def quotes(self, customer, role='owner', request_id=None):
        return sorted(line['quote'] for line in self.app.context_for(customer['id'], role, request_id)['lines'])

    def test_a_statement_is_stored_with_its_provenance_and_business_date(self):
        self.ready()
        s = self.statement(status='proposed')
        self.assertEqual((s['saidBy'], s['role'], s['saidOn'], s['status'], s['visibility'], s['version'], s['history']),
                         ('owner_demo', 'owner', '2026-10-18', 'proposed', 'owner', 1, []))
        self.assertTrue(s['id'].startswith('stmt_'))
        self.assertTrue(all(line['id'].startswith('line_') for line in s['lines']))
        self.assertEqual([(line['status'], line['supersededBy']) for line in s['lines']], [('active', None)])
        self.assertEqual((self.app.statement(s['id']), self.app.statements()), (s, [s]))   # stored exactly as returned

    def test_only_the_owner_confirms_or_changes_visibility(self):
        self.ready()
        s = self.statement(visibility='staff', status='proposed')
        for change in ({'status': 'confirmed'}, {'status': 'retired'}, {'visibility': 'owner'}):
            with self.assertRaises(RecordsError) as refused:
                self.app.update_statement(STAFF, s, **change)
            self.assertEqual(refused.exception.status, 403, change)
        with self.assertRaises(RecordsError):   # nor can staff store one already confirmed
            self.statement(actor=STAFF)
        line = s['lines'][0]['id']
        confirmed = self.app.update_statement(OWNER, s, status='confirmed', lines=[{'id': line, 'until': '2026-12-31'}])
        self.assertEqual((confirmed['status'], confirmed['version'], confirmed['lines'][0]['until']), ('confirmed', 2, '2026-12-31'))
        self.assertEqual([(h['version'], h['status'], h['lines'][0]['until']) for h in confirmed['history']], [(1, 'proposed', None)])
        self.assertEqual(self.app.statement(s['id']), confirmed)
        with self.assertRaises(RecordsError):   # a confirmed statement is the owner's to change
            self.app.update_statement(STAFF, confirmed, lines=[{'id': line, 'remove': True}])
        removed = self.app.update_statement(OWNER, confirmed, lines=[{'id': line, 'remove': True}])
        self.assertEqual((removed['lines'][0]['status'], removed['version']), ('removed', 3))

    def test_statement_scope_and_line_kinds_are_checked(self):
        self.ready()
        s = self.statement(status='proposed')
        for bad in (lambda: self.statement(scope={'kind': 'everyone'}),
                    lambda: self.app.new_statement(OWNER, 'Hm.', thread_id='thread_general', scope={'kind': 'business'}, visibility='owner',
                                                   status='proposed', source=None, lines=[{'kind': 'opinion', 'quote': 'Hm', 'until': None}]),
                    lambda: self.app.update_statement(OWNER, s, scope={'kind': 'everyone'}),
                    lambda: self.app.update_statement(OWNER, s, lines=[{'id': s['lines'][0]['id'], 'kind': 'opinion'}])):
            with self.assertRaises(APIError) as refused:
                bad()
            self.assertEqual((refused.exception.status, refused.exception.code), (400, 'INVALID_INPUT'))
        self.assertEqual(self.app.statements(), [s])   # nothing changed

    def test_context_for_merges_notes_and_statements_and_filters_staff(self):
        c = self.ready()
        status, note, _ = self.call('/api/records/notes', {'kind': 'context', 'text': 'Busy season ends in December', 'scope': c['id'],
                                                           'confirm': True}, 'owner', 'n1')
        self.assertEqual(status, 200, note)
        mine = {'kind': 'customer', 'customerId': c['id']}
        private = self.statement('Up to two weeks is fine for them', scope=mine)
        self.statement('They prefer email', scope=mine, visibility='staff')
        self.statement('Another customer entirely', scope={'kind': 'customer', 'customerId': 'customer_other'})
        self.statement('Not confirmed yet', scope=mine, status='proposed')
        self.assertEqual(self.quotes(c, 'staff'), ['Busy season ends in December', 'They prefer email'])
        self.assertEqual(self.quotes(c), ['Busy season ends in December', 'They prefer email', 'Up to two weeks is fine for them'])
        lines = {line['quote']: line for line in self.app.context_for(c['id'], 'owner')['lines']}
        from_note, said = lines['Busy season ends in December'], lines['Up to two weeks is fine for them']
        self.assertEqual((from_note['id'], from_note['kind'], from_note['scope'], from_note['saidOn'], from_note['visibility'], from_note['source']),
                         ('note:' + note['record']['id'], 'observation', mine, note['record']['createdAt'][:10], 'staff', 'note'))
        self.assertEqual((said['statementId'], said['saidBy'], said['role'], said['saidOn'], said['visibility'], said['expired'], said['source']),
                         (private['id'], 'owner_demo', 'owner', '2026-10-18', 'owner', False, 'test'))

    def test_case_scoped_lines_appear_only_for_that_case(self):
        c = self.ready()
        self.statement('Up to 14 days this time', scope={'kind': 'case', 'requestId': 'req_x'})
        self.statement('No customer was named', scope={'kind': 'unassigned'})
        self.assertEqual(self.quotes(c, request_id='req_x'), ['Up to 14 days this time'])
        self.assertEqual(self.quotes(c, request_id='req_y'), [])
        self.assertEqual(self.quotes(c), [])

    def test_expired_lines_are_kept_and_marked(self):
        c = self.ready()
        self.statement('Hold off until October', until='2026-10-01')
        self.statement('Fine until the end of the year', until='2026-12-31')
        lines = {line['quote']: line['expired'] for line in self.app.context_for(c['id'], 'owner')['lines']}
        self.assertEqual(lines, {'Hold off until October': True, 'Fine until the end of the year': False})

    def test_context_for_lists_the_customers_decided_cases(self):
        c = self.ready()
        self.add_invoice(c)
        r = self.wait_status(self.create(), ('awaiting_owner',))
        self.assertEqual(self.app.context_for(c['id'], 'owner')['decisions'], [])
        self.assertEqual(self.decide(r)[0], 201)
        decision = self.reopen(r)['decision']
        self.assertEqual(self.app.context_for(c['id'], 'staff')['decisions'], [
            {'requestId': r['id'], 'decidedAt': decision['decidedAt'], 'outcome': 'approve', 'approvedDueDate': '2026-10-30',
             'approvedExtensionDays': None, 'reason': 'This invoice only.', 'invoiceReference': 'DEMO-501'}])
        self.assertEqual(self.app.context_for(self.add_customer('Coastline Foods')['id'], 'owner')['decisions'], [])
        self.assertEqual(self.app.case_thread(r['id'])['id'], 'thread_' + r['id'])

    def test_turns_are_filtered_by_visibility(self):
        self.ready()
        thread = self.app.general_thread()
        self.assertEqual((thread['id'], self.app.general_thread()), ('thread_general', thread))   # created once, on first use
        shared = self.app.add_turn(thread['id'], by='staff_demo', role='staff', kind='message', text='Bayside asked for more time')
        private = self.app.add_turn(thread['id'], by='owner_demo', role='owner', kind='message', text='Two weeks at most', visibility='owner')
        self.assertEqual(self.app.turns(thread['id'], 'staff'), [shared])
        self.assertEqual(self.app.turns(thread['id'], 'owner'), [shared, private])
        self.assertEqual(self.app.threads(), [thread])

    def test_advance_business_date_moves_today_in_a_practice_workspace(self):
        self.demo = True
        self.ready()
        self.assertEqual(self.call('/api/demo/advance', {'days': 7}, 'owner')[0], 403)
        self.assertEqual(self.call('/api/demo/advance', {'days': '7'}, 'operator')[0], 400)
        self.assertEqual(self.call('/api/demo/advance', {'days': 7}, 'operator')[:2], (200, {'today': '2026-10-25'}))
        self.assertEqual(self.app.today(self.app.fixture()), date(2026, 10, 25))
        self.assertEqual(self.statement()['saidOn'], '2026-10-25')   # statements are dated by the business date
        self.path = Path(self.tmp.name) / 'real.sqlite3'
        self.start()
        self.setup_workspace(mode='real')
        self.settings()
        with self.assertRaises(RecordsError) as refused:
            self.app.advance_business_date(OPERATOR, 7)
        self.assertEqual((refused.exception.status, refused.exception.code), (409, 'NOT_PRACTICE'))
        with self.app.lock, self.app.db:
            self.app.set_meta('businessDateOffset', 7)   # e.g. left in a database: a real workspace never uses it
        self.assertEqual(self.app.today(self.app.fixture()), date(2026, 10, 18))

    def test_reset_and_start_empty_clear_what_was_said_and_the_moved_date(self):
        self.demo = True
        self.start(sample_data=True)   # the sample's business date is fixed at 2026-10-16
        self.call('/api/demo/advance', {'days': 7}, 'operator')
        self.statement()
        self.app.add_turn(self.app.general_thread()['id'], by='owner_demo', role='owner', kind='message', text='Two weeks at most')
        self.assertEqual(self.console()[1]['asOfDate'], '2026-10-23')
        self.assertEqual(self.console('reset', {})[1]['reset'], True)   # not "already clean": there were statements and a moved date
        self.assertEqual((self.app.statements(), self.app.threads(), self.count('turns')), ([], [], 0))
        self.assertEqual(self.app.today(self.app.fixture()), date(2026, 10, 16))
        self.assertEqual(self.console()[1]['asOfDate'], '2026-10-16')
        self.assertEqual(self.console('start-empty', {})[1]['emptied'], True)
        self.call('/api/demo/advance', {'days': 3}, 'operator')
        self.statement()
        self.assertEqual(self.console('start-empty', {})[1]['emptied'], True)   # an emptied workspace with statements is not empty
        self.assertEqual((self.app.statements(), self.app.threads(), self.app.today(self.app.fixture())), ([], [], date(2026, 10, 18)))


if __name__ == '__main__':
    unittest.main()
