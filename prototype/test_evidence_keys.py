"""Evidence keys (docs/EVIDENCE-KEYS.md). A decided case is flagged, and a pending case prepared again, when what its invoice
shows changes: never for import bookkeeping or for the wording of an explanation, and an unchanged amount is not unchanged
evidence. Keys stored by release a9ce30d are carried over only when the records are shown unchanged. All data is fictional."""
import json
import sqlite3
import unittest
from pathlib import Path
from unittest import mock

from test_exact import ExactCase

FIXTURE = Path(__file__).parent / 'testdata' / 'a9ce30d-evidence.sql'   # written by a9ce30d's own code: testdata/make_a9ce30d_evidence.py
INVOICE_FILE = 'Customer,Invoice No,Invoice Date,Amount,Due Date,Balance\nCoastline Foods,DEMO-601,01/10/2026,"1,200.00",31/10/2026,1200.00\n'
CONFLICTING_FILE = INVOICE_FILE.replace(',1200.00\n', ',1100.00\n')


class EvidenceCase(ExactCase):
    def invoice_file(self, text, key, conflicts=None):
        batch = self.upload(text, shape='invoices', label='Accounts spreadsheet', key='up-' + key)
        batch = self.params(batch, key='p-' + key, asOf='2026-10-17', resolutions={'customers': {}, 'conflicts': conflicts or {}, 'rows': {}})
        self.apply(batch)
        return batch

    def revert(self, batch, key):
        status, result, _ = self.call('/api/imports/' + batch['id'] + '/revert', {'reason': 'Wrong file', 'confirm': True}, 'staff', key)
        self.assertEqual(status, 200, result)

    def decided(self, reference, date, key):
        r = self.wait_status(self.create('Could we pay invoice ' + reference + ' on ' + date + ' instead?', key='intake-' + key), ('awaiting_owner',))
        self.assertEqual(self.decide(r, approved=date, key='decision-' + key)[0], 201)
        return self.wait_status(r, ('completed',))

    def stored(self, r):
        return self.app.get(r['id'])

    def kinds(self, r, kind):
        return [e for e in self.app.history(r['id']) if e['kind'] == kind]


class BookkeepingTests(EvidenceCase):
    def test_the_same_file_again_and_its_revert_leave_a_decided_case_alone(self):
        self.ready()
        self.invoice_file(INVOICE_FILE, 'first')
        done = self.decided('DEMO-601', '2026-11-20', 'c')
        again = self.invoice_file(INVOICE_FILE, 'again')                 # every row unchanged: only which imports listed it changes
        self.assertEqual(self.stored(done).get('flags', []), [])
        self.revert(again, 'revert-again')
        self.assertEqual(self.stored(done).get('flags', []), [])

    def test_the_same_file_again_does_not_prepare_a_pending_case_again(self):
        self.ready()
        self.invoice_file(INVOICE_FILE, 'first')
        r = self.wait_status(self.create('Could we pay invoice DEMO-601 on 2026-11-20 instead?'), ('awaiting_owner',))
        self.invoice_file(INVOICE_FILE, 'again')
        self.assertEqual((self.stored(r)['status'], len(self.kinds(r, 'analysis.queued'))), ('awaiting_owner', 1))

    def test_a_kept_conflict_is_flagged_although_the_amount_is_unchanged_and_so_is_its_revert(self):
        self.ready()
        self.invoice_file(INVOICE_FILE, 'first')
        done = self.decided('DEMO-601', '2026-11-20', 'c')
        conflict = self.invoice_file(CONFLICTING_FILE, 'conflict', conflicts={'2': 'keep'})
        flags = self.stored(done)['flags']
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]['outstandingBefore'], flags[0]['outstandingNow'])   # a later file disagreed: new evidence, same amount
        self.revert(conflict, 'revert-conflict')
        self.assertEqual(len(self.stored(done)['flags']), 2)

    def test_a_taken_conflict_is_flagged(self):
        self.ready()
        self.invoice_file(INVOICE_FILE, 'first')
        done = self.decided('DEMO-601', '2026-11-20', 'c')
        self.invoice_file(CONFLICTING_FILE, 'conflict', conflicts={'2': 'take'})
        flag = self.stored(done)['flags'][0]
        self.assertEqual((flag['outstandingBefore'][:12], flag['outstandingNow'][:12]), ('AUD 1,200.00', 'AUD 1,100.00'))


class ExplanationTests(EvidenceCase):
    def broken_completeness(self):
        """DEMO-501 at most AUD 400.00, its completeness statement broken by a payment added inside the confirmed period."""
        self.ready()
        invoice = self.invoice('DEMO-501', total='1000.00', issueDate='2026-10-05')
        self.allocate(self.pay('600.00', date='2026-10-12', reference='EFT-501'), (invoice, '600.00'))
        self.complete_from_opening(end='2026-10-16')
        self.pay('50.00', date='2026-10-14', reference='LATE-1')
        return invoice

    def test_a_new_reason_with_the_same_amount_is_flagged(self):
        self.ready()
        self.opening(amount='0.00', credits='none')                     # as at 30 Sep
        invoice = self.invoice('DEMO-501', total='1000.00', issueDate='2026-10-05')
        self.allocate(self.pay('600.00', date='2026-10-12'), (invoice, '600.00'))
        done = self.decided('DEMO-501', '2026-10-30', 'b')
        self.invoice('DEMO-500', total='100.00', issueDate='2026-09-20')  # before the opening balance: is it part of it? Not answered.
        flag = self.stored(done)['flags'][0]
        self.assertEqual((flag['outstandingBefore'], flag['outstandingNow']), ('at most AUD 400.00', 'at most AUD 400.00'))
        self.assertIn('not yet answered', ' '.join(self.positions()['notExact'][invoice['id']]))

    def test_the_wording_of_an_explanation_does_not_move_a_key(self):
        invoice = self.broken_completeness()
        ev = self.app.evidence()
        before = (ev.decision_evidence(invoice['id'])['key'], ev.version_for(invoice['id']), ev.invoice(invoice['id'])['position']['notExact'])
        self.assertTrue(any('no longer holds' in t for t in before[2]))
        with mock.patch('records.day_text', lambda iso: '[' + iso + ']'), mock.patch('records.describe_record', lambda r: '<' + r['id'] + '>'):
            ev = self.app.evidence()
            after = (ev.decision_evidence(invoice['id'])['key'], ev.version_for(invoice['id']), ev.invoice(invoice['id'])['position']['notExact'])
        self.assertNotEqual(before[2], after[2])                       # the wording did change
        self.assertEqual(before[:2], after[:2])

    def test_what_an_explanation_states_still_moves_the_key(self):
        invoice = self.broken_completeness()
        key = self.app.evidence().decision_evidence(invoice['id'])['key']
        self.pay('25.00', date='2026-10-15', reference='LATE-2')          # another record added inside the period: the same kind of reason
        self.assertNotEqual(self.app.evidence().decision_evidence(invoice['id'])['key'], key)


class MigrationTests(EvidenceCase):
    """The first start of this release on a database written by a9ce30d."""
    def load(self, change=None):
        with sqlite3.connect(self.path) as db:
            db.executescript(FIXTURE.read_text())
            if change:
                change(db)
        self.start()
        with self.app.lock:   # the worker prepares stale cases on the same connection: read once each case has settled
            for r in self.app.records():
                self.app.wait_settled(r['id'], 10)
            refs = {i['id']: i['reference'] for i in self.app.fixture()['invoices']}
            return {refs[r['invoiceId']]: r for r in self.app.records()}

    @staticmethod
    def fixture_cases():
        db = sqlite3.connect(':memory:')
        db.executescript(FIXTURE.read_text())
        refs = {i['id']: i['reference'] for i in (json.loads(d) for (d,) in db.execute('SELECT data FROM invoices'))}
        cases = {refs[r['invoiceId']]: r for r in (json.loads(d) for (d,) in db.execute('SELECT data FROM requests'))}
        for r in cases.values():
            r['events'] = db.execute('SELECT COUNT(*) FROM events WHERE request_id=?', (r['id'],)).fetchone()[0]
        return cases

    def new_events(self, before):
        return [e['kind'] for e in self.app.history(before['id'])[before['events']:]]

    def test_unchanged_records_carry_over_without_a_flag_and_the_pending_case_is_not_prepared_again(self):
        before, after = self.fixture_cases(), self.load()
        for ref in ('DEMO-501', 'DEMO-601', 'DEMO-801'):
            self.assertEqual(after[ref].get('flags', []), before[ref].get('flags', []), ref)   # existing flags kept exactly
            self.assertEqual(after[ref]['evidenceSeen']['format'], 2)
            self.assertEqual(after[ref]['evidenceSeen']['key'], self.app.evidence().decision_evidence(after[ref]['invoiceId'])['key'])
            self.assertEqual(self.new_events(before[ref]), ['evidence.key_format_updated'], ref)
        pending = after['DEMO-701']
        self.assertEqual((pending['status'], pending['task']['evidenceVersion']), ('awaiting_owner', self.app.evidence().version_for(pending['invoiceId'])))
        self.assertEqual(self.new_events(before['DEMO-701']), ['evidence.version_updated'])
        self.assertEqual((pending['version'], pending['analysis']), (before['DEMO-701']['version'], before['DEMO-701']['analysis'] | {
            'snapshot': before['DEMO-701']['analysis']['snapshot'] | {'evidenceVersion': pending['task']['evidenceVersion']}}))
        marker = self.app.meta('evidenceKeys')
        self.assertEqual({k: marker[k] for k in ('format', 'rebaselined', 'restamped', 'flagged', 'disputes')},
                         {'format': 2, 'rebaselined': 3, 'restamped': 1, 'flagged': 0, 'disputes': 1})

    def test_a_kept_conflict_is_recorded_as_a_disagreement(self):
        self.load()
        invoice = next(i for i in self.app.fixture()['invoices'] if i['reference'] == 'DEMO-601')
        batches = [json.loads(d) for (d,) in self.app.db.execute('SELECT data FROM batches')]
        conflict = next(b['id'] for b in batches if [r['status'] for r in b['preview']['rows']] == ['conflict'])
        self.assertEqual((invoice['disputedBy'], len(invoice['confirmedBy'])), ([conflict], 2))

    def test_a_change_made_while_changes_were_not_tracked_is_flagged_at_startup(self):
        def change(db):                                                  # as if edited by a release that did not compare
            for table, ref in (('invoices', 'DEMO-801'), ('invoices', 'DEMO-701')):
                for rowid, data in db.execute('SELECT rowid, data FROM ' + table).fetchall():
                    record = json.loads(data)
                    if record['reference'] == ref:
                        record['total'] = {**record['total'], 'minorUnits': str(int(record['total']['minorUnits']) + 5000)}
                        db.execute('UPDATE ' + table + ' SET data=? WHERE rowid=?', (json.dumps(record), rowid))
        before, after = self.fixture_cases(), self.load(change)
        flags = after['DEMO-801'].get('flags', [])
        self.assertEqual(len(flags), 1)
        self.assertEqual((flags[0]['kind'], flags[0]['cause']), ('records_changed_after_decision', 'startup comparison'))
        self.assertIn('not recorded', flags[0]['description'])
        self.assertEqual(after['DEMO-501'].get('flags'), before['DEMO-501'].get('flags'))
        self.assertGreater(after['DEMO-701']['version'], before['DEMO-701']['version'])   # pending: prepared again, as before
        self.assertEqual(self.app.meta('evidenceKeys')['flagged'], 1)

    def test_afterwards_unrelated_changes_flag_nothing_and_real_ones_still_do(self):
        before = self.load()
        self.add_customer('Unrelated fictional customer', key='unrelated')
        after = {r['id']: r for r in self.app.records()}
        self.assertEqual({r['id']: len(after[r['id']].get('flags', [])) for r in before.values()},
                         {r['id']: len(r.get('flags', [])) for r in before.values()})
        invoice = next(i for i in self.app.fixture()['invoices'] if i['reference'] == 'DEMO-801')
        self.correct('invoices', invoice, total='320.00', reason='Fictional correction')
        self.assertEqual(len(self.app.get(before['DEMO-801']['id'])['flags']), 1)

    def test_a_second_start_changes_nothing(self):
        self.load()
        first = sorted(json.dumps(r, sort_keys=True) for r in self.app.records())
        marker = self.app.meta('evidenceKeys')
        self.restart()
        self.assertEqual(sorted(json.dumps(r, sort_keys=True) for r in self.app.records()), first)
        self.assertEqual(self.app.meta('evidenceKeys'), marker)


if __name__ == '__main__':
    unittest.main()
