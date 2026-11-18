"""Payment-list CSV import (Stage 3): preview, explicit same-customer allocation, safe re-import and overlapping
exports, review of ambiguous identity, corrections, and dependency-aware revert. Uses the fictional files in samples/."""
import json
import unittest
from pathlib import Path

from test_payments import PaymentCase

SAMPLES = Path(__file__).parent / 'samples'


class PaymentImportCase(PaymentCase):
    def upload(self, text, shape='payments', label='Bank export', key=None):
        status, batch, _ = self.call('/api/imports', {'sourceLabel': label, 'fileName': 'file.csv', 'csvText': text, 'shape': shape}, 'staff',
                                     key or 'u-' + shape + str(abs(hash(text)) % 10 ** 9) + label)
        self.assertEqual(status, 200, batch)
        return batch

    def params(self, batch, key=None, **params):
        body = {'mapping': batch['mapping'], 'resolutions': {'customers': {}, 'conflicts': {}, 'rows': {}}, **params}
        status, batch, _ = self.call('/api/imports/' + batch['id'] + '/mapping', body, 'staff', key or 'p-' + json.dumps(body, sort_keys=True))
        self.assertEqual(status, 200, batch)
        return batch

    def apply(self, batch, expect=200):
        status, result, _ = self.call('/api/imports/' + batch['id'] + '/apply', {}, 'staff', 'apply-' + batch['id'])
        self.assertEqual(status, expect, result)
        return result

    def rows(self, batch):
        return {r['row']: r for r in batch['preview']['rows']}

    def records_setup(self):
        """Practice workspace with the sample invoice list imported, amounts as of 9 Oct (before the payments)."""
        self.start()
        self.practice_ready()
        batch = self.upload((SAMPLES / 'invoices-list.csv').read_text(), shape='invoices', label='Accounts spreadsheet')
        batch = self.params(batch, asOf='2026-10-09')
        new = {c['key']: 'new' for c in batch['preview']['customers']}
        self.apply(self.params(batch, key='inv-ready', asOf='2026-10-09', resolutions={'customers': new, 'conflicts': {}, 'rows': {}}))
        doc = self.app.fixture()
        self.customers = {c['name']: c for c in doc['customers']}
        self.invoices = {(next(c['name'] for c in doc['customers'] if c['id'] == i['customerId']), i['reference']): i for i in doc['invoices']}

    def payments_imported(self, name='payments-list.csv', key='pay', label='Bank export'):
        batch = self.upload((SAMPLES / name).read_text(), label=label, key=key)
        self.assertTrue(batch['preview']['ready'], batch['preview']['needs'])
        return self.apply(batch)


class PaymentImportTests(PaymentImportCase):
    def test_preview_allocates_only_explicitly_and_only_within_the_customer(self):
        self.records_setup()
        batch = self.upload((SAMPLES / 'payments-list.csv').read_text())
        self.assertEqual(batch['mapping'], {'customer': 0, 'paymentDate': 1, 'amount': 2, 'reference': 3, 'invoiceNumber': 4})
        rows = self.rows(batch)
        self.assertEqual([rows[n]['status'] for n in range(2, 7)], ['new', 'new', 'new', 'new', 'rejected'])
        self.assertEqual(rows[2]['allocation']['amount']['minorUnits'], '60000')                       # partial payment
        self.assertEqual(rows[3]['allocation']['amount']['minorUnits'], '40000')                       # overpayment: only what is left
        self.assertIn('100.00 stays unallocated', rows[3]['allocation']['note'])
        self.assertIsNone(rows[4]['allocation'])                                                       # no reference: unallocated
        self.assertIsNone(rows[5]['allocation'])                                                       # another customer's invoice
        self.assertIn('not an invoice of this customer', rows[5]['allocationNote'])
        self.apply(batch)
        positions = self.positions()
        bayside1001, bayside1002 = self.invoices[('Bayside Café', 'INV-1001')], self.invoices[('Bayside Café', 'INV-1002')]
        self.assertEqual((positions['invoices'][bayside1001['id']]['status'], self.minor(positions['invoices'][bayside1001['id']]['atMost'])), ('open', '40000'))
        self.assertEqual(positions['invoices'][bayside1002['id']]['status'], 'settled')
        self.assertEqual(self.minor(positions['customers'][self.customers['Bayside Café']['id']]['unallocated']), '35000')
        self.assertEqual(self.minor(positions['customers'][self.customers['Coastline Foods']['id']]['unallocated']), '20000')

    def test_reimport_and_an_overlapping_export_add_only_what_is_new(self):
        self.records_setup()
        self.payments_imported()
        before = len(self.app.fixture()['payments']), len(self.app.fixture()['allocations'])
        again = self.upload((SAMPLES / 'payments-list.csv').read_text(), key='again')
        self.assertEqual((again['preview']['counts']['new'], again['preview']['counts']['unchanged']), (0, 4))
        self.apply(again)
        self.assertEqual((len(self.app.fixture()['payments']), len(self.app.fixture()['allocations'])), before)
        overlap = self.upload((SAMPLES / 'payments-overlap.csv').read_text(), key='overlap')
        self.assertEqual([r['status'] for r in overlap['preview']['rows']], ['unchanged', 'unchanged', 'new'])
        self.apply(overlap)
        coastline1001 = self.invoices[('Coastline Foods', 'INV-1001')]
        self.assertEqual(self.positions()['invoices'][coastline1001['id']]['status'], 'settled')
        self.assertEqual(len(self.app.fixture()['payments']), before[0] + 1)

    def test_a_reference_repeated_in_a_file_with_different_values_needs_review(self):
        self.records_setup()
        text = 'Customer,Date,Amount,Reference\nBayside Café,12/10/2026,600.00,EFT 7781\nBayside Café,15/10/2026,300.00,EFT 7781\n'
        batch = self.upload(text)
        self.assertEqual([r['status'] for r in batch['preview']['rows']], ['unresolved', 'unresolved'])
        self.assertFalse(batch['preview']['ready'])
        batch = self.params(batch, resolutions={'customers': {}, 'conflicts': {}, 'rows': {'3': 'skip'}})
        self.assertEqual([r['status'] for r in batch['preview']['rows']], ['new', 'leftOut'])
        both = self.params(batch, key='both', resolutions={'customers': {}, 'conflicts': {}, 'rows': {'2': 'distinct', '3': 'distinct'}})
        self.assertEqual([r['status'] for r in both['preview']['rows']], ['new', 'new'])

    def test_an_unreferenced_payment_like_one_already_recorded_needs_review(self):
        self.records_setup()
        self.pay('250.00', date='2026-10-14', customer=self.customers['Bayside Café'])
        batch = self.upload('Customer,Date,Amount\nBayside Café,14/10/2026,250.00\n')
        self.assertEqual(batch['preview']['rows'][0]['status'], 'unresolved')
        same = self.params(batch, resolutions={'customers': {}, 'conflicts': {}, 'rows': {'2': 'same'}})
        self.assertEqual(same['preview']['rows'][0]['status'], 'unchanged')
        self.apply(same)
        self.assertEqual(len(self.app.fixture()['payments']), 1)

    def test_a_reference_matches_a_payment_typed_in_and_a_correction_wins(self):
        self.records_setup()
        typed = self.pay('600.00', date='2026-10-13', reference='EFT 7781', customer=self.customers['Bayside Café'])
        batch = self.upload('Customer,Date,Amount,Reference\nBayside Café,13/10/2026,600.00,eft 7781\n')
        self.assertEqual(batch['preview']['rows'][0]['status'], 'unchanged')
        self.assertEqual(self.correct('payments', typed, amount='590.00', reason='Bank fee')[0], 200)
        again = self.upload('Customer,Date,Amount,Reference\nBayside Café,13/10/2026,600.00,eft 7781\n', key='after-fix')
        row = again['preview']['rows'][0]
        self.assertEqual((row['status'], row['correctedByPerson']), ('conflict', True))

    def test_a_preview_made_stale_by_a_records_change_is_refused_then_refreshed(self):
        self.records_setup()
        batch = self.upload((SAMPLES / 'payments-list.csv').read_text())
        self.pay('250.00', date='2026-10-14', customer=self.customers['Bayside Café'])   # the same money, typed in meanwhile
        status, error, _ = self.call('/api/imports/' + batch['id'] + '/apply', {}, 'staff', 'stale-apply')
        self.assertEqual((status, error['error']), (409, 'RECORDS_CHANGED'))
        fresh = self.call('/api/imports/' + batch['id'], role='staff')[1]
        self.assertEqual(self.rows(fresh)[4]['status'], 'unresolved')   # now a possible duplicate of the typed-in payment
        self.assertEqual(len(self.app.fixture()['payments']), 1)          # nothing was applied from the stale preview

    def test_revert_waits_for_allocations_made_after_the_import(self):
        self.records_setup()
        batch = self.payments_imported()
        unreferenced = next(p for p in self.app.fixture()['payments'] if p['amount']['minorUnits'] == '25000')
        allocation = self.allocate(unreferenced, (self.invoices[('Bayside Café', 'INV-1001')], '250.00'))['records'][0]
        status, error, _ = self.call('/api/imports/' + batch['id'] + '/revert', {'reason': 'Wrong account'}, 'staff', 'rv1')
        self.assertEqual((status, error['error']), (409, 'REVERT_BLOCKED'))
        self.assertIn('allocated after the import', ' '.join(error['impact']['blocked']))
        self.call('/api/records/allocations/' + allocation['id'] + '/remove', {'reason': 'Undo before revert'}, 'staff', 'ra')
        self.assertEqual(self.call('/api/imports/' + batch['id'] + '/revert', {'reason': 'Wrong account'}, 'staff', 'rv2')[0], 200)
        doc = self.app.fixture()
        self.assertEqual([p['status'] for p in doc['payments']], ['reverted'] * 4)
        self.assertTrue(all(a['status'] in ('reverted', 'removed') for a in doc['allocations']))
        self.assertEqual(self.positions()['invoices'], {})


if __name__ == '__main__':
    unittest.main()


class PaymentBeforeInvoiceTests(PaymentImportCase):
    """H1: a payment reference matches an invoice only when the invoice was issued on or before the payment was received."""
    CSV = ('Customer,Date received,Amount received,Payment reference,Invoice number\n'
           'Bayside Café,2025-10-10,1000.00,BCV-EARLY,54\n'
           'Bayside Café,2026-08-15,500.00,BCV-LATE,54\n')

    def fixture(self):
        self.ready()
        self.invoice('00000054', total='900.00', issueDate='2026-07-30', dueDate='2026-08-30')
        self.invoice('54', total='200.00', customer=self.coastline, issueDate='2025-01-01', dueDate='2025-02-01')   # another customer's earlier 54

    def test_a_payment_dated_before_the_invoice_stays_unmatched_and_says_why(self):
        self.fixture()
        rows = self.rows(self.upload(self.CSV))
        early, late = rows[2], rows[3]
        self.assertIsNone(early['allocation'])
        self.assertEqual(early['unmatched'], 'issuedAfter')
        self.assertEqual(early['allocationNote'], 'This payment names invoice 00000054, issued after this payment; left unmatched.')
        self.assertEqual(late['allocation']['reference'], '00000054')   # received after the invoice was issued: matched as before

    def test_find_invoice_never_matches_an_invoice_issued_after_the_payment(self):
        import importer
        self.fixture()
        doc = self.app.fixture()
        self.assertEqual(importer.find_invoice(doc, self.bayside['id'], '54', '2025-10-10'), (None, 'issuedAfter'))
        self.assertEqual(importer.find_invoice(doc, self.bayside['id'], '54', '2026-07-30')[0]['reference'], '00000054')   # the issue day itself
        self.assertEqual(importer.find_invoice(doc, self.bayside['id'], '54'), importer.find_invoice(doc, self.bayside['id'], '54', '2026-12-01'))


class ValidatorSelftestTests(unittest.TestCase):
    def test_the_validator_selftest_passes_including_the_hand_replay_dating_rule(self):
        import subprocess, sys
        script = Path(__file__).resolve().parent.parent / 'deploy' / 'validate_import.py'
        done = subprocess.run([sys.executable, str(script), '--selftest'], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr[-500:])
        self.assertIn('selftest ok', done.stdout)
