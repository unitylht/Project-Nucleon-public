"""Workspace setup, sample loading, manual records, owner knowledge, CSV import, corrections and revert.
All data is fictional. No real model is called."""
import json
import sqlite3
import unittest
from datetime import date

import importer
from agent import fingerprint
from records import RecordsError
from server import App
from test_agent import ISO_MESSAGE
from test_demo import FIXTURE, DemoCase

TODAY = date(2026, 10, 18)   # a fixed "today" for workspaces that use the real clock


class RecordsCase(DemoCase):
    demo = False

    def start(self, adapter=None, mode='mock', inline_wait=10, sample_data=False, today=lambda: TODAY, **options):
        app = super().start(adapter, mode, inline_wait, sample_data=sample_data, today=today, **options)
        return app

    def setup_workspace(self, mode='practice', with_sample=False, role='owner'):
        return self.call('/api/setup/workspace', {'mode': mode, 'withSample': with_sample}, role, 'ws-' + mode)

    def settings(self, role='owner', key='settings-1', **values):
        body = {'currency': 'AUD', 'scale': 2, 'timezone': 'Australia/Sydney', 'businessName': 'Bayside Practice', **values}
        return self.call('/api/setup/settings', body, role, key)

    def setup(self):
        return self.call('/api/setup', role='staff')[1]

    def restart(self, **options):
        app, server, thread = self.apps.pop()
        server.shutdown()
        server.server_close()
        thread.join()
        app.close()
        return self.start(**options)

    def practice_ready(self, **settings):
        self.setup_workspace('practice')
        self.settings(**settings)

    def add_customer(self, name='Bayside Café', role='staff', key=None):
        status, body, _ = self.call('/api/records/customers', {'name': name}, role, key or 'c-' + name)
        self.assertEqual(status, 200, body)
        return body['record']

    def add_invoice(self, customer, reference='DEMO-501', role='staff', key=None, expect=200, **values):
        body = {'customerId': customer['id'], 'reference': reference, 'issueDate': '2026-10-01', 'total': '1200.00', **values}
        status, result, _ = self.call('/api/records/invoices', body, role, key or 'i-' + reference + json.dumps(values, sort_keys=True))
        self.assertEqual(status, expect, result)
        return result.get('record', result)

    def correct(self, kind, record, role='staff', key=None, **values):
        return self.call('/api/records/' + kind + '/' + record['id'], values, role, key or 'fix-' + json.dumps(values, sort_keys=True))

    def create(self, message='Could we pay invoice DEMO-501 on 2026-10-30 instead?', key='intake-1'):
        return super().create(message, key)

    def facts(self, r):
        return {f['key']: f for f in r['analysis']['brief']['facts']}

    def store(self, records, workspace=None):
        db = sqlite3.connect(self.path)
        db.execute('CREATE TABLE IF NOT EXISTS fixtures (id INTEGER PRIMARY KEY, data TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, data TEXT NOT NULL)')
        db.execute('INSERT OR REPLACE INTO fixtures VALUES (1, ?)', (json.dumps(records),))
        if workspace:
            db.execute('INSERT OR REPLACE INTO meta VALUES (?, ?)', ('workspace', json.dumps(workspace)))
        db.commit()
        db.close()


class WorkspaceTests(RecordsCase):
    def test_first_run_has_no_workspace_and_cannot_take_requests(self):
        self.start()
        state = self.setup()
        self.assertIsNone(state['workspace'])
        self.assertFalse(state['ready'])
        self.assertEqual([i['status'] for i in state['checklist'] if i['tier'] == 'required'], ['todo', 'todo', 'todo'])
        status, error, _ = self.call('/api/requests', {'messageText': ISO_MESSAGE}, 'staff', 'k1')
        self.assertEqual((status, error['error']), (409, 'NO_RECORDS'))

    def test_only_the_owner_sets_up_the_workspace_and_settings(self):
        self.start()
        self.assertEqual(self.setup_workspace(role='staff')[0], 403)
        self.assertEqual(self.setup_workspace()[0], 200)
        self.assertEqual(self.setup_workspace()[0], 409)   # one workspace per database
        self.assertEqual(self.settings(role='staff')[0], 403)

    def test_settings_are_validated(self):
        self.start()
        self.setup_workspace()
        for field, value in (('currency', 'aud1'), ('scale', 7), ('scale', '2'), ('timezone', 'Mars/Base')):
            status, error, _ = self.settings(key='bad-' + field + str(value), **{field: value})
            self.assertEqual((status, error.get('field')), (400, field), (field, value))
        self.assertEqual(self.settings()[0], 200)
        state = self.setup()
        self.assertEqual(state['settings'], {'currency': 'AUD', 'scale': 2, 'timezone': 'Australia/Sydney', 'businessName': 'Bayside Practice'})
        self.assertEqual([i['status'] for i in state['checklist'] if i['tier'] == 'required'], ['done', 'done', 'todo'])
        self.assertEqual(self.call('/api/session', role='staff')[1]['asOfDate'], '2026-10-18')   # the real clock, not the sample's date

    def test_a_practice_workspace_started_empty_stays_empty_even_with_sample_data_configured(self):
        self.start()
        self.setup_workspace(mode='practice', with_sample=False)
        self.settings()
        app = self.restart(sample_data=True)
        self.assertEqual(app.fixture()['customers'], [])
        self.assertEqual(self.setup()['workspace']['mode'], 'practice')

    def test_a_real_workspace_refuses_the_sample(self):
        self.demo = True
        self.start()
        self.setup_workspace(mode='real')
        self.settings()
        status, error, _ = self.call('/api/setup/sample', {}, 'owner', 's1')
        self.assertEqual((status, error['error']), (409, 'REAL_WORKSPACE'))
        app = self.restart(sample_data=True)
        self.assertEqual((app.fixture()['dataMode'], app.fixture()['customers']), ('real', []))
        self.assertEqual(self.call('/api/demo/console', role='operator')[0], 404)

    def test_an_empty_practice_workspace_can_load_the_sample_on_request(self):
        self.start()
        self.setup_workspace(mode='practice')
        self.assertEqual(self.call('/api/setup/sample', {}, 'owner', 's1')[0], 200)
        self.assertEqual(self.app.fixture(), FIXTURE)
        self.assertTrue(self.setup()['ready'])

    def test_modified_practice_records_are_not_replaced_by_a_newer_sample(self):
        old = {**FIXTURE, 'version': 1}
        changed = {**old, 'customers': old['customers'] + [{'id': 'customer_own', 'displayCode': 'C-0001', 'name': 'My Own Café'}]}
        self.store(changed, {'mode': 'practice', 'origin': 'first_run', 'sampleFingerprint': fingerprint(old)})
        app = self.start(sample_data=True)
        self.assertEqual(app.fixture(), changed)

    def test_an_unmodified_older_sample_is_still_upgraded(self):
        old = {**FIXTURE, 'version': 1, 'invoices': FIXTURE['invoices'][:1]}
        self.store(old, {'mode': 'practice', 'origin': 'config', 'sampleFingerprint': fingerprint(old)})
        self.assertEqual(self.start().fixture(), FIXTURE)

    def test_a_database_from_before_workspaces_keeps_its_cases(self):
        self.start(sample_data=True)
        self.create(key='old-case')
        with self.app.lock, self.app.db:
            self.app.db.execute("DELETE FROM meta WHERE key='workspace'")   # as written by the previous release
        app = self.restart()
        self.assertEqual(app.meta('workspace')['mode'], 'practice')
        self.assertEqual(app.meta('workspace')['origin'], 'migration')
        self.assertEqual(len(app.records()), 1)

    def test_console_can_start_empty_and_reset_to_the_sample(self):
        self.demo = True
        app = self.start(sample_data=True)
        status, result, _ = self.call('/api/demo/start-empty', {}, 'operator')
        self.assertEqual((status, result['emptied']), (200, True))
        self.assertEqual((app.fixture()['customers'], app.fixture()['invoices'], app.fixture()['notes']), ([], [], []))
        self.assertIsNone(app.meta('workspace')['sampleFingerprint'])
        self.assertFalse(self.setup()['ready'])
        self.call('/api/demo/reset', {}, 'operator')
        self.assertEqual(app.fixture(), FIXTURE)


class ManualRecordsTests(RecordsCase):
    def test_manual_setup_reaches_a_prepared_case_with_unknowns_stated(self):
        self.start()
        self.practice_ready()
        bayside = self.add_customer()
        self.assertFalse(self.setup()['ready'])
        self.add_invoice(bayside)
        self.assertTrue(self.setup()['ready'])
        r = self.wait_status(self.create(), ('awaiting_owner',))
        facts = self.facts(r)
        self.assertEqual((facts['outstandingAmount']['kind'], facts['outstandingAmount']['value']), ('unknown', None))
        self.assertEqual((facts['currentEffectiveDueDate']['value'], facts['daysOverdue']['value']), (None, None))
        self.assertEqual(r['analysis']['snapshot']['asOfDate'], '2026-10-18')

    def test_input_errors_name_the_field(self):
        self.start()
        self.practice_ready()
        bayside = self.add_customer()
        for values, field in (({'total': '12,0O'}, 'total'), ({'total': '12.005'}, 'total'), ({'issueDate': '2026-02-31'}, 'issueDate'),
                              ({'dueDate': '2026-09-01'}, 'dueDate'), ({'stillOwed': '1500.00', 'stillOwedAsOf': '2026-10-10'}, 'stillOwed'),
                              ({'stillOwed': '100.00'}, 'stillOwedAsOf'), ({'stillOwed': '100.00', 'stillOwedAsOf': '2026-10-19'}, 'stillOwedAsOf')):
            error = self.add_invoice(bayside, expect=400, **values)
            self.assertEqual(error['field'], field, values)
        self.add_invoice(bayside)
        self.assertEqual(self.add_invoice(bayside, key='again', expect=409)['field'], 'reference')   # same customer, same number
        self.assertEqual(self.call('/api/records/customers', {'name': 'bayside cafe'}, 'staff', 'dup')[1].get('field'), 'name')

    def test_a_stated_amount_is_qualified_and_overdue_days_need_a_statement_from_today(self):
        self.start()
        self.practice_ready()
        invoice = self.add_invoice(self.add_customer(), dueDate='2026-10-10', stillOwed='600.00', stillOwedAsOf='2026-10-15')
        r = self.wait_status(self.create(), ('awaiting_owner',))
        facts = self.facts(r)
        self.assertEqual((facts['outstandingAmount']['kind'], facts['outstandingAmount']['value']['minorUnits']), ('stated', '60000'))
        self.assertIsNone(facts['daysOverdue']['value'])
        self.assertIn('15 Oct', facts['daysOverdue']['reason'])
        status, _, _ = self.correct('invoices', invoice, stillOwed='600.00', stillOwedAsOf='2026-10-18', reason='Checked with the bank today')
        self.assertEqual(status, 200)
        again = self.wait_status(r, ('awaiting_owner',))   # re-prepared because the records changed
        self.assertEqual(self.facts(again)['daysOverdue']['value'], 8)

    def test_a_stated_zero_goes_back_to_staff_and_a_correction_resolves_it(self):
        self.start()
        self.practice_ready()
        bayside = self.add_customer()
        invoice = self.add_invoice(bayside, stillOwed='0', stillOwedAsOf='2026-10-17')
        self.assertFalse(self.setup()['ready'])   # a fully paid invoice is not an open invoice
        self.add_invoice(bayside, reference='DEMO-502')
        r = self.wait_status(self.create(), ('needs_information',))
        self.assertEqual([m['field'] for m in r['task']['missingFields']], ['invoiceReference'])   # not a date: the invoice is the issue
        self.assertIn('fully paid as of Sat 17 Oct 2026', r['task']['question'])
        self.assertEqual(self.correct('invoices', invoice, stillOwed='250.00', stillOwedAsOf='2026-10-18', reason='Part was refunded')[0], 200)
        r = self.reopen(r)
        self.call('/api/requests/' + r['id'] + '/reanalyse', {'expectedRequestVersion': r['version']}, 'staff', 'again')
        self.assertEqual(self.wait_status(r, ('awaiting_owner',))['status'], 'awaiting_owner')

    def test_corrections_are_new_versions_that_keep_the_old_values(self):
        self.start()
        self.practice_ready()
        invoice = self.add_invoice(self.add_customer())
        self.assertEqual(self.correct('invoices', invoice, total='1100.00')[1]['field'], 'reason')
        status, result, _ = self.correct('invoices', invoice, total='1100.00', reason='Typo in the amount')
        self.assertEqual(status, 200)
        fixed = result['record']
        self.assertEqual((fixed['version'], fixed['total']['minorUnits'], fixed['setBy']['kind']), (2, '110000', 'correction'))
        self.assertEqual(fixed['history'][0]['values']['total']['minorUnits'], '120000')

    def test_removal_is_blocked_by_dependents_and_reviewed_for_cases(self):
        self.start()
        self.practice_ready()
        bayside = self.add_customer()
        invoice = self.add_invoice(bayside)
        status, error, _ = self.call('/api/records/customers/' + bayside['id'] + '/remove', {'reason': 'Duplicate'}, 'staff', 'rm-c')
        self.assertEqual((status, error['error']), (409, 'REMOVE_BLOCKED'))
        r = self.wait_status(self.create(), ('awaiting_owner',))
        path = '/api/records/invoices/' + invoice['id'] + '/remove'
        status, error, _ = self.call(path, {'reason': 'Entered twice'}, 'staff', 'rm-1')
        self.assertEqual((status, error['error'], error['impact']['pendingCases']), (409, 'REVIEW_REQUIRED', [r['id']]))
        self.assertEqual(self.call(path, {'reason': 'Entered twice', 'confirm': True}, 'staff', 'rm-2')[0], 200)
        self.assertEqual(self.wait_status(r, ('needs_information',))['status'], 'needs_information')   # its invoice is gone
        self.add_invoice(bayside, key='re-add')   # a removed invoice no longer blocks its number

    def test_a_decided_case_is_flagged_not_undone_when_its_invoice_changes(self):
        self.start()
        self.practice_ready()
        invoice = self.add_invoice(self.add_customer())
        r = self.wait_status(self.create(), ('awaiting_owner',))
        self.assertEqual(self.decide(r)[0], 201)
        self.correct('invoices', invoice, total='1100.00', reason='Credit for a damaged item')
        after = self.wait_status(r, ('completed',))
        self.assertEqual((after['decision']['outcome'], after['decision']['approvedDueDate']), ('approve', '2026-10-30'))
        self.assertEqual([f['kind'] for f in after['flags']], ['records_changed_after_decision'])


class KnowledgeTests(RecordsCase):
    def note(self, role='owner', key=None, **values):
        return self.call('/api/records/notes', {'kind': 'context', **values}, role, key or 'n-' + json.dumps(values, sort_keys=True))

    def test_owner_notes_are_confirmed_staff_notes_are_drafts_and_only_confirmed_reach_the_agent(self):
        self.start()
        self.practice_ready()
        bayside = self.add_customer()
        self.add_invoice(bayside)
        owner_note = self.note(text="We don't extend into December without a call", scope='business', kind='rule', confirm=True)[1]['record']
        self.assertEqual(owner_note['status'], 'confirmed')
        staff_note = self.note(role='staff', text='Says their busy season ends in December', scope=bayside['id'])[1]['record']
        self.assertEqual(staff_note['status'], 'draft')
        self.assertEqual(self.note(role='staff', key='x', text='Trusted', scope=bayside['id'], confirm=True)[0], 403)
        r = self.wait_status(self.create(), ('awaiting_owner',))
        notes = r['analysis']['brief']['ownerNotes']
        self.assertEqual([(n['text'], n['scope']['kind'], n['kind']) for n in notes], [(owner_note['text'], 'business', 'rule')])
        self.assertEqual(self.call('/api/records/notes/' + staff_note['id'] + '/confirm', {}, 'staff', 'c1')[0], 403)
        self.assertEqual(self.call('/api/records/notes/' + staff_note['id'] + '/confirm', {}, 'owner', 'c2')[0], 200)
        again = self.wait_status(self.create(key='intake-2'), ('awaiting_owner',))
        self.assertEqual(len(again['analysis']['brief']['ownerNotes']), 2)
        self.call('/api/records/notes/' + owner_note['id'] + '/retire', {'reason': 'No longer our practice'}, 'owner', 'r1')
        third = self.wait_status(self.create(key='intake-3'), ('awaiting_owner',))
        self.assertEqual([n['text'] for n in third['analysis']['brief']['ownerNotes']], [staff_note['text']])

    def test_a_customer_note_needs_an_existing_customer_and_knowledge_can_be_skipped(self):
        self.start()
        self.practice_ready()
        self.assertEqual(self.note(text='Pays late in winter', scope='customer_nobody', confirm=True)[1]['field'], 'scope')
        self.call('/api/setup/skip', {'item': 'knowledge'}, 'owner', 'skip')
        self.assertEqual(next(i for i in self.setup()['checklist'] if i['id'] == 'knowledge')['status'], 'skipped')


CSV = """Customer,Invoice No,Invoice Date,Amount,Due Date,Balance
Bayside Café,DEMO-601,01/10/2026,"1,200.00",31/10/2026,1200.00
Bayside Café,DEMO-602,05/10/2026,800.00,,800.00
Coastline Foods,DEMO-601,03/10/2026,450.50,02/11/2026,450.50
Dune Traders,DEMO-603,31/02/2026,300.00,,300.00
Dune Traders,DEMO-604,06/10/2026,"1,2O0",,
"""


class ImportTests(RecordsCase):
    def upload(self, text=CSV, label='Accounts spreadsheet', key=None):
        status, batch, _ = self.call('/api/imports', {'sourceLabel': label, 'fileName': 'invoices.csv', 'csvText': text}, 'staff', key or 'up-' + fingerprint(text)[:16])
        self.assertEqual(status, 200, batch)
        return batch

    def params(self, batch, key=None, **params):
        status, batch, _ = self.call('/api/imports/' + batch['id'] + '/mapping', params, 'staff', key or 'p-' + json.dumps(params, sort_keys=True))
        self.assertEqual(status, 200, batch)
        return batch

    def apply(self, batch, expect=200):
        status, result, _ = self.call('/api/imports/' + batch['id'] + '/apply', {}, 'staff', 'apply-' + batch['id'])
        self.assertEqual(status, expect, result)
        return result

    def revert(self, batch, key, **body):
        return self.call('/api/imports/' + batch['id'] + '/revert', {'reason': 'Wrong file', **body}, 'staff', key)

    def invoices(self, reference=None):
        return [i for i in self.app.fixture()['invoices'] if i.get('status', 'active') == 'active' and (reference is None or i['reference'] == reference)]

    def statuses(self, batch):
        return {r['row']: r['status'] for r in batch['preview']['rows']}

    def imported(self, text=CSV, as_of='2026-10-17', **resolutions):
        batch = self.upload(text, key='up-' + as_of + fingerprint(text)[:16])
        batch = self.params(batch, mapping=batch['mapping'], asOf=as_of, resolutions={'customers': {}, 'conflicts': {}, **resolutions})
        return batch

    def test_preview_classifies_rows_and_customers_must_be_resolved_before_apply(self):
        self.start()
        self.practice_ready()
        self.add_customer('Bayside Café')
        batch = self.upload()
        self.assertEqual(batch['mapping'], {'customer': 0, 'invoiceNumber': 1, 'issueDate': 2, 'amount': 3, 'dueDate': 4, 'stillOwed': 5})
        self.assertIn('amounts as of', ' '.join(batch['preview']['needs']))
        batch = self.params(batch, mapping=batch['mapping'], asOf='2026-10-17')
        self.assertEqual(batch['preview']['dateOrder'], 'dmy')
        self.assertEqual(self.statuses(batch), {2: 'new', 3: 'new', 4: 'unresolved', 5: 'rejected', 6: 'rejected'})
        self.assertFalse(batch['preview']['ready'])
        self.apply(batch, expect=409)
        coastline = next(c for c in batch['preview']['customers'] if c['name'] == 'Coastline Foods')
        batch = self.params(batch, mapping=batch['mapping'], asOf='2026-10-17', resolutions={'customers': {coastline['key']: 'new'}})
        self.assertTrue(batch['preview']['ready'])
        self.apply(batch)
        self.assertEqual(sorted((i['reference'], i['total']['minorUnits']) for i in self.invoices()),
                         [('DEMO-601', '120000'), ('DEMO-601', '45050'), ('DEMO-602', '80000')])   # two customers share DEMO-601
        bayside601 = next(i for i in self.invoices('DEMO-601') if i['total']['minorUnits'] == '120000')
        self.assertEqual((bayside601['outstandingAsOf'], bayside601['outstandingSource'], bayside601['originalDueDate']), ('2026-10-17', 'file', '2026-10-31'))

    def ready_import(self, text=CSV, as_of='2026-10-17'):
        first = self.upload(text, key='first')
        key = next(c['key'] for c in self.params(first, key='f1', mapping=first['mapping'], asOf=as_of)['preview']['customers'] if c['name'] == 'Coastline Foods')
        batch = self.params(first, key='f2', mapping=first['mapping'], asOf=as_of, resolutions={'customers': {key: 'new'}})
        self.apply(batch)
        return batch

    def test_reimporting_the_same_rows_in_any_order_changes_nothing(self):
        self.start()
        self.practice_ready()
        self.add_customer('Bayside Café')
        self.ready_import()
        before = json.dumps(self.invoices(), sort_keys=True)
        lines = CSV.strip().split('\n')
        shuffled = '\n'.join([lines[0]] + lines[1:][::-1]) + '\n'
        again = self.upload(shuffled, key='again')
        self.assertEqual(again['mapping'], {'customer': 0, 'invoiceNumber': 1, 'issueDate': 2, 'amount': 3, 'dueDate': 4, 'stillOwed': 5})
        again = self.params(again, mapping=again['mapping'], asOf='2026-10-17')
        self.assertEqual(again['preview']['counts']['new'], 0)
        self.assertEqual(again['preview']['counts']['unchanged'], 3)
        self.apply(again)
        self.assertEqual([{k: v for k, v in i.items() if k != 'confirmedBy'} for i in self.invoices()],
                         [{k: v for k, v in i.items() if k != 'confirmedBy'} for i in json.loads(before)])

    def test_a_newer_statement_updates_and_a_same_date_difference_is_a_conflict(self):
        self.start()
        self.practice_ready()
        self.add_customer('Bayside Café')
        self.ready_import()
        changed = CSV.replace('31/10/2026,1200.00', '31/10/2026,500.00')
        newer = self.imported(changed, as_of='2026-10-18')
        self.assertEqual(self.statuses(newer)[2], 'updated')
        same = self.imported(changed, as_of='2026-10-17')
        self.assertEqual(self.statuses(same)[2], 'conflict')
        self.assertFalse(same['preview']['ready'])
        same = self.params(same, mapping=same['mapping'], asOf='2026-10-17', resolutions={'customers': {}, 'conflicts': {'2': 'keep'}})
        self.apply(same)
        bayside601 = next(i for i in self.invoices('DEMO-601') if i['total']['minorUnits'] == '120000')
        self.assertEqual(bayside601['outstandingAmount']['minorUnits'], '120000')

    def test_an_invoice_typed_in_earlier_is_matched_never_duplicated(self):
        self.start()
        self.practice_ready()
        bayside = self.add_customer('Bayside Café')
        self.add_invoice(bayside, reference='DEMO-601', issueDate='2026-10-01', total='1200.00')
        batch = self.imported(CSV.split('Bayside Café,DEMO-602')[0])
        self.assertEqual(self.statuses(batch), {2: 'updated'})   # the file adds the due date and the amount still owed
        self.apply(batch)
        self.assertEqual(len(self.invoices('DEMO-601')), 1)

    def test_a_correction_by_a_person_wins_unless_they_choose_to_replace_it(self):
        self.start()
        self.practice_ready()
        self.add_customer('Bayside Café')
        self.ready_import()
        bayside601 = next(i for i in self.invoices('DEMO-601') if i['total']['minorUnits'] == '120000')
        self.assertEqual(self.correct('invoices', bayside601, total='1100.00', stillOwed='1100.00', reason='Discount agreed')[0], 200)
        again = self.imported()
        self.assertEqual(self.statuses(again)[2], 'conflict')
        self.assertTrue(next(r for r in again['preview']['rows'] if r['row'] == 2)['correctedByPerson'])

    def test_revert_restores_the_earlier_version_and_respects_later_changes(self):
        self.start()
        self.practice_ready()
        text = 'Customer,Invoice,Date,Amount,Balance\nDune Traders,DEMO-700,2026-09-01,2000.00,2000.00\n'
        first = self.upload(text, key='b1')
        dune = first['preview']['customers'] or self.params(first, key='b1p', mapping=first['mapping'], asOf='2026-09-30')['preview']['customers']
        b1 = self.params(first, key='b1r', mapping=first['mapping'], asOf='2026-09-30', resolutions={'customers': {dune[0]['key']: 'new'}})
        self.apply(b1)
        b2 = self.imported(text.replace(',2000.00\n', ',500.00\n'), as_of='2026-10-15')
        self.assertEqual(self.statuses(b2), {2: 'updated'})
        self.apply(b2)
        status, error, _ = self.revert(b1, 'rb1')
        self.assertEqual((status, error['error']), (409, 'REVERT_BLOCKED'))
        self.assertEqual(self.revert(b2, 'rb2')[0], 200)
        invoice = self.invoices('DEMO-700')[0]
        self.assertEqual((invoice['outstandingAmount']['minorUnits'], invoice['outstandingAsOf']), ('200000', '2026-09-30'))
        r = self.wait_status(self.create('Could we pay invoice DEMO-700 on 2026-10-30 instead?'), ('awaiting_owner',))
        status, error, _ = self.revert(b1, 'rb1-again')
        self.assertEqual((status, error['error'], error['impact']['review']['pendingCases']), (409, 'REVIEW_REQUIRED', [r['id']]))
        self.assertEqual(self.decide(self.reopen(r))[0], 201)
        status, error, _ = self.revert(b1, 'rb1-decided')
        self.assertEqual(error['impact']['review']['decidedCases'], [r['id']])
        self.assertEqual(self.revert(b1, 'rb1-ok', confirm=True)[0], 200)
        self.assertEqual(self.invoices('DEMO-700'), [])
        done = self.wait_status(r, ('completed',))
        self.assertEqual((done['decision']['outcome'], [f['kind'] for f in done['flags']]), ('approve', ['invoice_no_longer_in_records']))

    def impact(self, batch):
        return self.call('/api/imports/' + batch['id'] + '/impact', role='staff')

    def test_a_draft_can_be_discarded_and_is_then_never_applied(self):   # QA B4: closed previews stayed as open drafts
        self.start()
        self.practice_ready()
        draft = self.upload()
        status, gone, _ = self.call('/api/imports/' + draft['id'] + '/discard', {}, 'staff', 'discard-1')
        self.assertEqual((status, gone['status']), (200, 'discarded'))
        self.assertEqual(self.call('/api/imports/' + draft['id'] + '/discard', {}, 'staff', 'discard-2')[1]['status'], 'discarded')   # again: no change
        self.assertEqual(self.apply(draft, expect=409)['error'], 'NOT_PREVIEW')
        self.assertEqual(self.call('/api/imports/' + draft['id'] + '/mapping', {'mapping': draft['mapping']}, 'staff', 'm')[0], 409)
        listed = self.call('/api/imports', role='staff')[1]
        self.assertEqual([(b['status'], bool(b['discardedAt'])) for b in listed], [('discarded', True)])
        self.assertEqual(self.app.fixture()['invoices'], [])
        text = 'Customer,Invoice,Date,Amount\nDune Traders,DEMO-730,2026-09-01,100.00\n'
        first = self.upload(text, key='f1')
        applied = self.params(first, key='f2', mapping=first['mapping'], resolutions={'customers': {first['preview']['customers'][0]['key']: 'new'}})
        self.apply(applied)
        self.assertEqual(self.call('/api/imports/' + applied['id'] + '/discard', {}, 'staff', 'discard-3')[1]['error'], 'NOT_PREVIEW')

    def test_revert_impact_is_available_before_submitting_and_changes_nothing(self):   # QA B3
        self.start()
        self.practice_ready()
        text = 'Customer,Invoice,Date,Amount\nDune Traders,DEMO-720,2026-09-01,2000.00\n'
        first = self.upload(text, key='e1')
        key = first['preview']['customers'][0]['key']
        batch = self.params(first, key='e2', mapping=first['mapping'], resolutions={'customers': {key: 'new'}})
        self.apply(batch)
        status, view, _ = self.impact(batch)
        self.assertEqual((status, view['blocked'], view['needsReview']), (200, [], False))
        self.assertIn('Invoice DEMO-720 (Dune Traders) is marked reverted', ' '.join(view['effects']))
        self.assertIn('Customer Dune Traders is marked reverted', ' '.join(view['effects']))
        dune = next(c for c in self.app.fixture()['customers'] if c['name'] == 'Dune Traders')
        self.call('/api/records/payments', {'customerId': dune['id'], 'receivedDate': '2026-10-02', 'amount': '500.00'}, 'staff', 'pay')
        payment = self.app.fixture()['payments'][0]
        invoice = self.invoices('DEMO-720')[0]
        self.call('/api/records/allocations', {'paymentId': payment['id'], 'allocations': [{'invoiceId': invoice['id'], 'amount': '500.00'}]}, 'staff', 'al')
        before = self.app.fixture()
        status, view, _ = self.impact(batch)
        self.assertEqual(status, 200)
        self.assertIn('Invoice DEMO-720 has payments allocated to it', ' '.join(view['blocked']))
        self.assertNotIn('from elsewhere', ' '.join(view['blocked']))   # its own invoice is not "from elsewhere"
        self.assertEqual(self.app.fixture(), before)   # looking changes nothing
        self.assertEqual(self.revert(batch, 'blocked')[1]['error'], 'REVERT_BLOCKED')   # and the server still refuses on submit
        again = self.imported(text, as_of='2026-10-16')   # the same file again: nothing new
        self.apply(again)
        view = self.impact(again)[1]
        self.assertEqual(view['blocked'], [])
        self.assertIn('added or changed no records', ' '.join(view['effects']))
        self.assertEqual(self.impact(self.upload(text, key='draft'))[0], 409)   # a draft has nothing to revert

    def test_a_customer_created_by_an_import_keeps_later_records(self):
        self.start()
        self.practice_ready()
        text = 'Customer,Invoice,Date,Amount\nDune Traders,DEMO-710,2026-09-01,2000.00\n'
        first = self.upload(text, key='d1')
        key = first['preview']['customers'][0]['key']
        batch = self.params(first, key='d2', mapping=first['mapping'], resolutions={'customers': {key: 'new'}})
        self.apply(batch)
        dune = next(c for c in self.app.fixture()['customers'] if c['name'] == 'Dune Traders')
        self.add_invoice(dune, reference='DEMO-711')
        status, error, _ = self.revert(batch, 'rd')
        self.assertEqual((status, error['error']), (409, 'REVERT_BLOCKED'))
        self.assertIn('Dune Traders', ' '.join(error['impact']['blocked']))


class ImporterUnitTests(unittest.TestCase):
    SETTINGS = {'currency': 'AUD', 'scale': 2}
    DOC = {'customers': [{'id': 'c1', 'displayCode': 'C-0001', 'name': 'Bayside Café'}], 'invoices': [], 'notes': []}

    def run_preview(self, text, **params):
        header, rows = importer.read_csv(text)
        mapping = importer.suggest_mapping(header)
        return importer.preview(self.DOC, header, rows, {'mapping': mapping, 'resolutions': {}, **params}, self.SETTINGS, TODAY)

    def test_semicolon_files_currency_symbols_and_text_dates(self):
        result = self.run_preview('Customer;Invoice;Date;Amount\nBayside Café;A-1;1 Oct 2026;$1,200.50\n')
        row = result['rows'][0]
        self.assertEqual((row['status'], row['values']['issueDate'], row['values']['total']['minorUnits']), ('new', '2026-10-01', '120050'))

    def test_ambiguous_dates_need_the_order_and_then_parse_that_way(self):
        text = 'Customer,Invoice,Date,Amount\nBayside Café,A-1,02/03/2026,10.00\n'
        self.assertIn('day/month/year', ' '.join(self.run_preview(text)['needs']))
        self.assertEqual(self.run_preview(text, dateOrder='mdy')['rows'][0]['values']['issueDate'], '2026-02-03')
        self.assertEqual(self.run_preview(text, dateOrder='dmy')['rows'][0]['values']['issueDate'], '2026-03-02')

    def test_rows_repeated_within_a_file_are_rejected_not_counted_twice(self):
        text = 'Customer,Invoice,Date,Amount\nBayside Café,A-1,2026-10-01,10.00\nbayside cafe,a-1,2026-10-01,10.00\nBayside Café,A-2,2026-10-01,5.00\nBayside Café,A-2,2026-10-02,5.00\n'
        statuses = [(r['row'], r['status']) for r in self.run_preview(text)['rows']]
        self.assertEqual(statuses, [(2, 'new'), (3, 'rejected'), (4, 'rejected'), (5, 'rejected')])

    def test_a_file_that_supplies_a_missing_date_or_amount_updates_rather_than_conflicts(self):
        doc = {'customers': [{'id': 'c1', 'displayCode': 'C-DEMO-01', 'name': 'Harbour Demo Supplies'}], 'notes': [],
               'invoices': [{'id': 'i1', 'reference': 'DEMO-101', 'customerId': 'c1', 'originalDueDate': '2026-10-20',
                             'outstandingAmount': {'minorUnits': '125000', 'currency': 'AUD', 'scale': 2}}]}   # the sample's shape
        header, rows = importer.read_csv('Customer,Invoice,Date,Amount\nHarbour Demo Supplies,DEMO-101,2026-10-06,1250.00\n')
        result = importer.preview(doc, header, rows, {'mapping': importer.suggest_mapping(header), 'resolutions': {}}, self.SETTINGS, TODAY)
        row = result['rows'][0]
        self.assertEqual((row['status'], sorted(row['updates'])), ('updated', ['issueDate', 'total']))

    def test_empty_or_header_only_files_are_refused(self):
        for text in ('', '\n\n', 'Customer,Invoice,Date,Amount\n'):
            with self.assertRaises(RecordsError) as caught:
                importer.read_csv(text)
            self.assertEqual(caught.exception.code, 'INVALID_FILE')


class AssistantLinkTests(RecordsCase):
    URL = 'http://127.0.0.1:3080/c/new?agent_id=agent_fictional_1'

    def test_the_session_names_the_assistant_link_only_when_the_config_sets_it(self):
        self.start()
        for role in ('staff', 'owner'):
            status, body, _ = self.call('/api/session', role=role)
            self.assertEqual((status, body['authenticated'], body['assistantUrl']), (200, True, None), role)
        self.restart(assistant_url=self.URL)
        for role in ('staff', 'owner'):
            self.assertEqual(self.call('/api/session', role=role)[1]['assistantUrl'], self.URL, role)
        status, probe, _ = self.call('/api/session')   # a probe before sign-in reveals nothing about the environment
        self.assertEqual((status, probe.get('authenticated'), 'assistantUrl' in probe), (200, False, False))

    def test_the_owner_gets_their_own_assistant_link_when_the_config_names_one(self):
        # Hoang, 6 Nov 2026: the Owner's pages opened the Staff assistant, because the config had one link for both.
        owner_url = self.URL + '&owner=1'
        self.start(assistant_url=self.URL, owner_assistant_url=owner_url)
        self.assertEqual(self.call('/api/session', role='staff')[1]['assistantUrl'], self.URL)
        self.assertEqual(self.call('/api/session', role='owner')[1]['assistantUrl'], owner_url)
        self.restart(owner_assistant_url=owner_url)   # only the Owner's is set
        self.assertEqual(self.call('/api/session', role='staff')[1]['assistantUrl'], None)
        self.assertEqual(self.call('/api/session', role='owner')[1]['assistantUrl'], owner_url)
        with self.assertRaises(ValueError):
            App(self.path, 'mock', None, owner_assistant_url='javascript:alert(1)')

    def test_only_an_http_or_https_link_without_quotes_or_spaces_is_accepted(self):
        from server import checked_assistant_url
        self.assertEqual((checked_assistant_url(None), checked_assistant_url('')), (None, None))
        self.assertEqual(checked_assistant_url('https://chat.example.org/c/new?agent_id=a1&x=2'), 'https://chat.example.org/c/new?agent_id=a1&x=2')
        for bad in ('javascript:alert(1)', 'ftp://x.example.org', '//x.example.org', 'http://x.example.org/a b', 'http://x.example.org/"onmouseover=1',
                    'http://x.example.org/<script>', 'http://' + 'a' * 600, 42, ['http://x.example.org']):
            with self.assertRaises(ValueError, msg=str(bad)[:40]):
                checked_assistant_url(bad)
        with self.assertRaises(ValueError):
            App(self.path, 'mock', None, assistant_url='javascript:alert(1)')


if __name__ == '__main__':
    unittest.main()
