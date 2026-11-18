"""Table-backed records (Stage 3 foundation): migration from the records document, one writable source, stable ids,
versions and provenance, per-customer evidence versions. All data is fictional."""
import json
import sqlite3
import unittest

from agent import fingerprint
from test_demo import FIXTURE
from test_records import RecordsCase

CHANGED = {**FIXTURE, 'customers': FIXTURE['customers'] + [
    {'id': 'customer_own', 'displayCode': 'C-0003', 'name': 'Bayside Café', 'status': 'active', 'version': 2,
     'origin': {'kind': 'manual', 'by': 'staff_demo', 'at': '2026-10-17T01:00:00+00:00'},
     'setBy': {'kind': 'correction', 'by': 'owner_demo', 'at': '2026-10-17T02:00:00+00:00', 'reason': 'Spelling'},
     'history': [{'version': 1, 'values': {'name': 'Bayside Cafe'}, 'setBy': {'kind': 'manual', 'by': 'staff_demo'},
                  'replacedAt': '2026-10-17T02:00:00+00:00', 'replacedBy': {'kind': 'correction', 'by': 'owner_demo'}}]}]}


class StoreTests(RecordsCase):
    def table(self, name):
        return [json.loads(d) for (d,) in self.app.db.execute('SELECT data FROM ' + name + ' ORDER BY seq')]

    def test_a_new_database_keeps_records_in_tables_only(self):
        app = self.start(sample_data=True)
        self.assertEqual(app.db.execute('SELECT COUNT(*) FROM fixtures').fetchone()[0], 0)
        self.assertEqual([c['id'] for c in self.table('customers')], ['customer_demo_01', 'customer_demo_02'])
        self.assertEqual(app.fixture(), FIXTURE)   # the document-shaped projection is exactly the sample

    def test_a_records_document_moves_into_tables_losslessly_and_is_then_frozen(self):
        self.store(CHANGED, {'mode': 'practice', 'origin': 'first_run', 'sampleFingerprint': None, 'skips': {}})
        app = self.start()
        self.assertEqual(app.fixture(), CHANGED)
        self.assertEqual(app.meta('records')['documentFingerprint'], fingerprint(CHANGED))
        own = next(c for c in self.table('customers') if c['id'] == 'customer_own')
        self.assertEqual((own['version'], own['history'][0]['values']['name'], own['origin']['by']), (2, 'Bayside Cafe', 'staff_demo'))
        status, result, _ = self.call('/api/records/customers/customer_own', {'name': 'Bayside Café & Co', 'reason': 'New sign'}, 'owner', 'fix')
        self.assertEqual((status, result['record']['version'], len(result['record']['history'])), (200, 3, 2))
        frozen = json.loads(app.db.execute('SELECT data FROM fixtures WHERE id=1').fetchone()[0])
        self.assertEqual(frozen, CHANGED)   # the old document is never written again
        self.assertEqual(next(c for c in app.fixture()['customers'] if c['id'] == 'customer_own')['name'], 'Bayside Café & Co')

    def test_a_document_changed_after_the_move_stops_startup(self):
        self.store(CHANGED, {'mode': 'practice', 'origin': 'first_run', 'sampleFingerprint': None, 'skips': {}})
        self.start()
        self.app.close()
        db = sqlite3.connect(self.path)   # as if the previous release ran on this database and saved its records document
        db.execute('UPDATE fixtures SET data=? WHERE id=1', (json.dumps({**CHANGED, 'customers': CHANGED['customers'][:2]}),))
        db.commit()
        db.close()
        with self.assertRaisesRegex(RuntimeError, 'changed after the records moved into tables'):
            self.start()

    def test_saving_never_deletes_a_record(self):
        app = self.start(sample_data=True)
        with app.lock, self.assertRaises(ValueError), app.db:
            app.save_doc({**app.fixture(), 'customers': app.fixture()['customers'][:1]})
        self.assertEqual(len(self.table('customers')), 2)

    def test_evidence_versions_are_per_customer(self):
        self.start(sample_data=True)
        supplies = self.wait_status(self.create('Could we pay invoice DEMO-101 on 2026-10-30 instead?', key='a'), ('awaiting_owner',))
        logistics = self.wait_status(self.create('Could we pay invoice DEMO-202 on 2026-11-20 instead?', key='b'), ('awaiting_owner',))
        status, _, _ = self.call('/api/records/notes', {'text': 'Pays on the 20th.', 'scope': 'customer_demo_02', 'confirm': True}, 'owner', 'n')
        self.assertEqual(status, 200)
        again = self.wait_status(logistics, ('awaiting_owner',))
        self.assertNotEqual(again['analysis']['id'], logistics['analysis']['id'])            # customer 02 changed: prepared again
        self.assertEqual(self.reopen(supplies)['analysis']['id'], supplies['analysis']['id'])  # customer 01 untouched
        self.assertEqual(self.decide(self.reopen(supplies))[0], 201)

    def test_a_case_with_outdated_evidence_is_prepared_again_once_at_startup(self):
        app = self.start(sample_data=True)
        r = self.wait_status(self.create('Could we pay invoice DEMO-101 on 2026-10-30 instead?'), ('awaiting_owner',))
        with app.lock, app.db:   # as if written with an earlier evidence formula
            stored = app.get(r['id'])
            stored['task']['evidenceVersion'] = 'from-an-earlier-release'
            app.save(stored)
        self.restart(sample_data=True)
        again = self.wait_status(r, ('awaiting_owner',))
        self.assertNotEqual(again['task']['evidenceVersion'], 'from-an-earlier-release')
        self.assertEqual(self.decide(again, key='after-restart')[0], 201)

    def test_a_case_whose_evidence_only_changed_format_is_re_stamped_not_re_run(self):
        app = self.start(sample_data=True)
        r = self.wait_status(self.create('Could we pay invoice DEMO-101 on 2026-10-30 instead?'), ('awaiting_owner',))
        with app.lock, app.db:   # the version an earlier release wrote: a fingerprint of the whole document
            ev = app.evidence()
            invoice = ev.invoice(r['invoiceId'])
            legacy = fingerprint({'fixture': ev.fixture, 'invoiceId': invoice['id'], 'currentEffectiveDueDate': ev.current_due(invoice)})
            stored = app.get(r['id'])
            stored['task']['evidenceVersion'] = stored['analysis']['snapshot']['evidenceVersion'] = legacy
            app.save(stored)
        self.restart(sample_data=True)
        after = self.reopen(r)
        self.assertEqual((after['status'], after['analysis']['id']), ('awaiting_owner', r['analysis']['id']))   # not prepared again
        self.assertIn('evidence.version_updated', [e['kind'] for e in after['history']])
        self.assertEqual(self.decide(after, key='restamped')[0], 201)

    def test_restoring_a_backup_from_before_the_tables_migrates_it(self):
        self.demo = True
        app = self.start(sample_data=True)
        self.backups.mkdir(exist_ok=True)
        old = self.backups / (self.path.stem + '-20261016-000000-before-reset.sqlite3')
        db = sqlite3.connect(old)
        db.executescript('CREATE TABLE fixtures (id INTEGER PRIMARY KEY, data TEXT NOT NULL); CREATE TABLE requests (id TEXT PRIMARY KEY, data TEXT NOT NULL);'
                         'CREATE TABLE events (seq INTEGER PRIMARY KEY AUTOINCREMENT, request_id TEXT NOT NULL, kind TEXT NOT NULL, at TEXT NOT NULL, data TEXT NOT NULL);')
        db.execute('INSERT INTO fixtures VALUES (1, ?)', (json.dumps(CHANGED),))
        db.commit()
        db.close()
        status, result, _ = self.call('/api/demo/restore', {'backup': old.name}, 'operator')
        self.assertEqual(status, 200, result)
        self.assertEqual(app.fixture(), CHANGED)
        self.assertEqual(len(self.table('customers')), 3)


if __name__ == '__main__':
    unittest.main()


class PerCustomerCalculationTests(unittest.TestCase):
    def test_each_customers_part_gives_the_same_positions_as_the_whole_records(self):
        from perf_records import dataset
        from records import active_view, coverage_view, exact_outstanding, invoice_position, opening_view, split_by_customer
        doc = dataset(500)
        view, parts, whole = active_view(doc), None, split_by_customer(doc)
        parts = split_by_customer(view)
        for invoice in view['invoices']:
            plain = {k: v for k, v in invoice.items() if k != 'position'}
            self.assertEqual(invoice_position(view, plain), invoice.get('position'))
            self.assertEqual(exact_outstanding(view, plain), exact_outstanding(parts[invoice['customerId']], plain))
        for customer in doc['customers']:
            cid = customer['id']
            self.assertEqual((opening_view(doc, cid), coverage_view(doc, cid)), (opening_view(whole[cid], cid), coverage_view(whole[cid], cid)))
        self.assertTrue(any(i.get('position', {}).get('exact') for i in view['invoices']))   # the dataset exercises exact amounts
