"""Revert provenance. Keeping the recorded value rejects a conflicting file's values: that file never becomes a source supporting the
values kept. Only a later import that listed the record unchanged, with every value it has now, can take over when the import it came
from is reverted; otherwise the revert is blocked, says which record and which later conflict depend on it, and names the way out.
A blocked revert changes nothing. All data is fictional."""
import json
import unittest

from test_evidence_keys import EvidenceCase

HEADER = 'Customer,Invoice No,Invoice Date,Amount,Due Date,Balance\n'
INVOICE = HEADER + 'Coastline Foods,DEMO-601,01/10/2026,"1,000.00",31/10/2026,1000.00\n'
CONFLICT = HEADER + 'Coastline Foods,DEMO-601,01/10/2026,"1,200.00",31/10/2026,1200.00\n'           # the example: 1,000 kept against 1,200
NO_DUE_DATE = 'Customer,Invoice No,Invoice Date,Amount,Balance\nCoastline Foods,DEMO-601,01/10/2026,"1,000.00",1000.00\n'
PAYMENTS = 'Customer,Date,Amount,Reference,Invoice\n'
PAYMENT = PAYMENTS + 'Coastline Foods,12/10/2026,500.00,EFT-601,\n'
PAYMENT_CONFLICT = PAYMENTS + 'Coastline Foods,12/10/2026,450.00,EFT-601,\n'


class ProvenanceCase(EvidenceCase):
    def invoices(self, text, key, keep=False, as_of='2026-10-17'):
        batch = self.upload(text, shape='invoices', label='Accounts ' + key, key='up-' + key)
        batch = self.params(batch, key='p-' + key, asOf=as_of, dateOrder='dmy', resolutions={'customers': {}, 'conflicts': {'2': 'keep'} if keep else {}, 'rows': {}})
        self.apply(batch)
        return batch

    def payments(self, text, key, keep=False):
        batch = self.upload(text, shape='payments', label='Bank ' + key, key='up-' + key)
        batch = self.params(batch, key='p-' + key, dateOrder='dmy', resolutions={'customers': {}, 'conflicts': {'2': 'keep'} if keep else {}, 'rows': {}})
        self.apply(batch)
        return batch

    def attempt(self, batch, key):
        return self.call('/api/imports/' + batch['id'] + '/revert', {'reason': 'Wrong file', 'confirm': True}, 'staff', key)

    def preview(self, batch):
        status, result, _ = self.call('/api/imports/' + batch['id'] + '/impact', role='staff')
        self.assertEqual(status, 200, result)
        return result

    def record(self, kind, **match):
        return next(r for r in self.app.fixture()[kind] if all(r.get(k) == v for k, v in match.items()))

    def state(self):
        return list(self.app.db.iterdump())

    def assert_blocked_and_unchanged(self, batch, key, *expected):
        preview, before = self.preview(batch), self.state()
        status, result, _ = self.attempt(batch, key)
        self.assertEqual((status, result['error']), (409, 'REVERT_BLOCKED'), result)
        self.assertEqual(self.state(), before)                             # nothing written, not even a reverted flag
        for text in expected:
            self.assertTrue(any(text in line for line in preview['blocked']), (text, preview['blocked']))
        self.assertEqual(result['impact']['blocked'], preview['blocked'])  # the preview and the server say the same
        return preview['blocked']


class InvoiceProvenanceTests(ProvenanceCase):
    def test_a_kept_conflict_never_becomes_the_source_and_reverting_the_original_is_blocked(self):
        self.ready()
        original = self.invoices(INVOICE, 'a')
        conflict = self.invoices(CONFLICT, 'b', keep=True)               # 1,200 proposed; a person keeps 1,000
        blocked = self.assert_blocked_and_unchanged(original, 'revert-a', 'DEMO-601', 'Accounts b', 'row 2', 'rejected', 'Revert that import first')
        self.assertEqual(len(blocked), 1)
        invoice = self.record('invoices', reference='DEMO-601')
        self.assertEqual((invoice['status'], invoice['setBy']['batchId'], invoice['total']['minorUnits']), ('active', original['id'], '100000'))
        self.assertNotIn('note', invoice['setBy'])
        self.assertEqual(invoice['disputedBy'], [conflict['id']])

    def test_the_documented_way_out_reverts_the_later_conflict_first(self):
        self.ready()
        original = self.invoices(INVOICE, 'a')
        conflict = self.invoices(CONFLICT, 'b', keep=True)
        self.assertEqual(self.preview(conflict)['blocked'], [])
        self.assertTrue(any('rejected' in line for line in self.preview(conflict)['effects']), self.preview(conflict)['effects'])
        self.revert(conflict, 'revert-b')
        self.assertEqual(self.preview(original)['blocked'], [])
        self.revert(original, 'revert-a')
        self.assertEqual(self.record('invoices', reference='DEMO-601')['status'], 'reverted')   # nothing is credited to anyone else

    def test_a_genuine_matching_import_supports_the_record(self):
        self.ready()
        original = self.invoices(INVOICE, 'a')
        matching = self.invoices(INVOICE, 'c')                           # every value the same
        self.assertTrue(any('lists it with the same values' in line for line in self.preview(original)['effects']))
        self.revert(original, 'revert-a')
        invoice = self.record('invoices', reference='DEMO-601')
        self.assertEqual((invoice['status'], invoice['setBy']['batchId']), ('active', matching['id']))

    def test_an_equal_amount_alone_is_not_support(self):
        self.ready()
        original = self.invoices(INVOICE, 'a')
        self.invoices(NO_DUE_DATE, 'c')                                   # the same amount, but it does not state the due date
        self.assert_blocked_and_unchanged(original, 'revert-a', 'DEMO-601', 'Accounts c', 'due date')

    def test_with_matching_and_conflicting_later_imports_only_the_matching_one_is_the_source(self):
        self.ready()
        original = self.invoices(INVOICE, 'a')
        matching = self.invoices(INVOICE, 'c')
        conflict = self.invoices(CONFLICT, 'b', keep=True)               # the last entry, which the old rule would have credited
        self.assertEqual(self.record('invoices', reference='DEMO-601')['confirmedBy'][-1], conflict['id'])
        self.revert(original, 'revert-a')
        invoice = self.record('invoices', reference='DEMO-601')
        self.assertEqual((invoice['setBy']['batchId'], invoice['total']['minorUnits']), (matching['id'], '100000'))

    def test_a_restored_earlier_version_is_not_credited_to_an_import_that_listed_other_values(self):
        self.ready()
        first = self.invoices(INVOICE, 'x', as_of='2026-10-09')           # 1,000 owed as of 9 Oct
        newer = HEADER + 'Coastline Foods,DEMO-601,01/10/2026,"1,000.00",31/10/2026,900.00\n'
        update = self.invoices(newer, 'u', as_of='2026-10-15')            # 900 owed as of 15 Oct: a new version
        self.invoices(newer, 'c', as_of='2026-10-15')                     # lists the 900 version unchanged
        self.revert(update, 'revert-u')                                   # back to the 1,000 version, credited to its own import
        invoice = self.record('invoices', reference='DEMO-601')
        self.assertEqual((invoice['outstandingAmount']['minorUnits'], invoice['setBy']['batchId']), ('100000', first['id']))
        self.assert_blocked_and_unchanged(first, 'revert-x', 'DEMO-601', 'Accounts c', 'still owed')

    def test_reverting_the_import_a_kept_record_was_credited_to_leaves_it_with_no_other_source(self):
        self.ready()
        original = self.invoices(INVOICE, 'a')
        matching = self.invoices(INVOICE, 'c')
        self.revert(original, 'revert-a')                                 # now credited to the matching import
        self.revert(matching, 'revert-c')
        invoice = self.record('invoices', reference='DEMO-601')
        self.assertEqual(invoice['status'], 'reverted')                   # never left active and credited to a reverted import


class ScanTests(ProvenanceCase):
    def test_the_scan_finds_a_record_the_old_rule_credited_to_a_rejected_conflict(self):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'deploy'))
        from provenance_scan import scan
        self.ready()
        self.invoices(INVOICE, 'a')
        conflict = self.invoices(CONFLICT, 'b', keep=True)
        self.assertEqual(scan(self.path)['credited'], [])
        self.assertEqual([k['conflict'] for k in scan(self.path)['keptConflicts']], [conflict['id']])
        with self.app.lock, self.app.db:                               # what the old rule wrote when the original import was reverted
            doc = self.app.fixture()
            invoice = next(i for i in doc['invoices'] if i['reference'] == 'DEMO-601')
            invoice['setBy'] = {**invoice['setBy'], 'batchId': conflict['id'], 'note': 'confirmed by a later import; kept when batch_x was reverted'}
            self.app.save_doc(doc)
        found = scan(self.path)['credited']
        self.assertEqual([(c['record'], c['creditedTo'], c['row']) for c in found],
                         [('DEMO-601', conflict['id'], 'conflict, values differ: total, outstandingAmount')])


class PaymentProvenanceTests(ProvenanceCase):
    def test_a_kept_payment_conflict_never_becomes_the_source(self):
        self.ready()
        original = self.payments(PAYMENT, 'a')
        conflict = self.payments(PAYMENT_CONFLICT, 'b', keep=True)
        self.assert_blocked_and_unchanged(original, 'revert-a', 'EFT-601', 'Bank b', 'row 2', 'rejected', 'Revert that import first')
        payment = self.record('payments', reference='EFT-601')
        self.assertEqual((payment['status'], payment['setBy']['batchId'], payment['disputedBy']), ('active', original['id'], [conflict['id']]))
        self.revert(conflict, 'revert-b')                                 # the way out
        self.revert(original, 'revert-a')
        self.assertEqual(self.record('payments', reference='EFT-601')['status'], 'reverted')

    def test_a_genuine_matching_payment_import_supports_the_payment(self):
        self.ready()
        original = self.payments(PAYMENT, 'a')
        conflict = self.payments(PAYMENT_CONFLICT, 'b', keep=True)
        matching = self.payments(PAYMENT, 'c')
        self.revert(original, 'revert-a')
        payment = self.record('payments', reference='EFT-601')
        self.assertEqual((payment['status'], payment['setBy']['batchId'], payment['amount']['minorUnits']), ('active', matching['id'], '50000'))
        self.assertNotEqual(payment['setBy']['batchId'], conflict['id'])


if __name__ == '__main__':
    unittest.main()
