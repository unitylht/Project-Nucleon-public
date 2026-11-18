"""Regenerates lab/tests/fixtures/card/*.json: REAL results of the customerOverview and invoices tools (from the records' own test
fixtures, fictional data, business date Sun 18 Oct 2026) for the card scenarios in test_card.py. Run from the repo root with the system
python (the prototype's tests need no packages):   python3 lab/tests/make_card_fixtures.py
Nothing here computes a result; the records tools do. The files are committed so the Lab's suite needs no records server for the renderer."""
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'prototype'))
os.chdir(ROOT / 'prototype')
from test_completeness_contract import AS_OF, ContractCase   # noqa: E402

OUT = ROOT / 'lab' / 'tests' / 'fixtures' / 'card'
XSS_NAME = '<script>alert(1)</script> & "Co" \'s'


class Make(ContractCase):
    def save(self, name, c, **invoice_args):
        ov, inv = self.overview(c), self.invoices(c, **({'which': 'all'} | invoice_args))
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / (name + '.json')).write_text(json.dumps({'overview': ov, 'invoices': inv}, ensure_ascii=False, indent=1, sort_keys=True) + '\n')

    def one(self, paid=None):
        self.ready()
        invoice = self.invoice('INV-1', total='1000.00', issueDate='2026-10-05', dueDate='2026-11-05')
        if paid:
            self.allocate(self.pay(paid, date='2026-10-12', reference='EFT 1'), (invoice, paid))
        return invoice

    def test_both_unconfirmed(self):
        self.one('400.00')
        self.invoice('INV-2', total='500.00', issueDate='2026-09-01', dueDate='2026-09-30')
        self.save('both_unconfirmed', self.bayside)
        self.save('both_unconfirmed_open', self.bayside, which='open')

    def test_both_complete(self):
        self.one('600.00')
        self.established(self.bayside)
        self.save('both_complete', self.bayside)

    def test_invoices_only(self):
        self.one('600.00')
        self.attest(types=('invoices',), start='2026-10-01', end=AS_OF)
        self.save('invoices_only', self.bayside)

    def test_payments_only(self):
        self.one()
        self.attest(types=('payments',), start='2026-10-01', end=AS_OF)
        self.save('payments_only', self.bayside)

    def test_earlier_date(self):
        self.one()
        self.established(self.bayside, end='2026-10-10')
        self.save('earlier_date', self.bayside)

    def test_contradicted(self):
        self.one()
        self.opening(amount='0.00', credits='none')
        self.attest(types=('invoices', 'payments'), start='2026-10-01', end=AS_OF)
        self.pay('90.00', date='2026-10-10', reference='LATE')
        self.attest(types=('payments',), start='2026-10-01', end='2026-10-09', key='second')
        self.save('contradicted', self.bayside)

    def test_no_payments(self):
        self.one()
        self.save('no_payments', self.bayside)

    def test_no_invoices(self):
        self.ready()
        self.save('no_invoices', self.coastline)

    def test_unknown_outstanding(self):
        self.ready()
        self.invoice('INV-U', total='1000.00', issueDate='2026-10-05', dueDate='2026-11-05')
        self.pay('1000.00', date='2026-10-06', reference='Deposit')   # received, not matched to the invoice: what is still owed is not known
        self.save('unknown_outstanding', self.bayside)

    def test_verified_zero(self):
        self.one('1000.00')
        self.established(self.bayside)
        self.save('verified_zero', self.bayside)

    def test_unverified_zero(self):
        self.one('1000.00')
        self.save('unverified_zero', self.bayside)

    def test_filtered_invoices(self):
        self.one()
        self.invoice('INV-2', total='200.00', issueDate='2026-10-06', dueDate='2026-12-25')
        self.save('filtered', self.bayside, dueOn='2026-12-25')

    def test_long_caveat(self):
        self.ready()
        self.invoice('INV-1', total='1000.00', issueDate='2026-10-05', dueDate='2026-11-05')
        self.opening(amount='0.00')
        self.attest(types=('invoices', 'payments'), start='2026-10-01', end='2026-10-10')
        self.pay('90.00', date='2026-10-08', reference='LATE')
        self.save('long_caveat', self.bayside)

    def test_xss_name(self):
        self.ready()
        c = self.add_customer(XSS_NAME)
        self.add_invoice(c, reference='INV-<b>X</b>', total='100.00', issueDate='2026-10-05', dueDate='2026-11-05')
        self.save('xss_name', c)


if __name__ == '__main__':
    unittest.main(verbosity=1)
