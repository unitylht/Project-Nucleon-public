"""Make a9ce30d-evidence.sql: a database written by release a9ce30d's own code, for the evidence-key migration tests
(docs/EVIDENCE-KEYS.md). Run it against an export of that release, never against this tree:

    git archive a9ce30d prototype | tar -x -C /tmp/a9ce30d
    python3 make_a9ce30d_evidence.py /tmp/a9ce30d/prototype a9ce30d-evidence.sql

All data is fictional. Four customers:
  Bayside Café     decided; an exact amount, then a payment added inside the confirmed period after the decision (flagged then)
  Coastline Foods  decided on an imported invoice; then the same file again (unchanged) and a conflicting file, kept (flagged twice)
  Dune Traders     awaiting the owner; a payment allocated, so its invoice has a position
  Eastside Grocer  decided; nothing changed afterwards
"""
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from test_exact import ExactCase   # noqa: E402  (the release's own test harness)

OUT = Path(sys.argv[2]).resolve()
INVOICE_FILE = 'Customer,Invoice No,Invoice Date,Amount,Due Date,Balance\nCoastline Foods,DEMO-601,01/10/2026,"1,200.00",31/10/2026,1200.00\n'


class Make(ExactCase):
    def decided(self, reference, date, key):
        r = self.wait_status(self.create('Could we pay invoice ' + reference + ' on ' + date + ' instead?', key='intake-' + key), ('awaiting_owner',))
        self.assertEqual(self.decide(r, approved=date, key='decision-' + key)[0], 201)
        return self.wait_status(r, ('completed',))

    def invoice_file(self, text, key):
        batch = self.upload(text, shape='invoices', label='Accounts spreadsheet', key='up-' + key)
        return self.apply(self.params(batch, key='p-' + key, asOf='2026-10-17'))

    def test_make(self):
        self.ready()
        dune, eastside = self.add_customer('Dune Traders'), self.add_customer('Eastside Grocer')
        # Bayside: exact, decided, then completeness broken by a payment added inside the confirmed period.
        bayside = self.invoice('DEMO-501', total='1000.00', issueDate='2026-10-05')
        self.allocate(self.pay('600.00', date='2026-10-12', reference='EFT-501'), (bayside, '600.00'))
        self.complete_from_opening(end='2026-10-16')
        self.assertIsNotNone(self.exact(bayside))
        self.decided('DEMO-501', '2026-10-30', 'bayside')
        self.pay('50.00', date='2026-10-14', reference='LATE-1')
        # Coastline: an imported invoice, decided, then the same file again and a conflicting one, kept.
        self.invoice_file(INVOICE_FILE, 'first')
        self.decided('DEMO-601', '2026-11-20', 'coastline')
        self.invoice_file(INVOICE_FILE, 'again')
        conflict = self.upload(INVOICE_FILE.replace(',1200.00\n', ',1100.00\n'), shape='invoices', label='Accounts spreadsheet', key='up-conflict')
        conflict = self.params(conflict, key='p-conflict', asOf='2026-10-17', resolutions={'customers': {}, 'conflicts': {'2': 'keep'}, 'rows': {}})
        self.assertEqual([r['status'] for r in conflict['preview']['rows']], ['conflict'])
        self.apply(conflict)
        # Dune: awaiting the owner, with a position.
        owed = self.invoice('DEMO-701', total='500.00', customer=dune, issueDate='2026-10-02')
        self.allocate(self.pay('200.00', date='2026-10-08', reference='EFT-701', customer=dune), (owed, '200.00'))
        self.wait_status(self.create('Could we pay invoice DEMO-701 on 2026-10-30 instead?', key='intake-dune'), ('awaiting_owner',))
        # Eastside: decided, unchanged afterwards.
        self.invoice('DEMO-801', total='300.00', customer=eastside, issueDate='2026-10-03')
        self.decided('DEMO-801', '2026-10-30', 'eastside')
        flags = {r['invoiceId']: len(r.get('flags', [])) for r in self.app.records()}
        self.assertEqual(sorted(flags.values()), [0, 0, 1, 2])
        copy = sqlite3.connect(':memory:')
        self.app.db.backup(copy)
        OUT.write_text('\n'.join(copy.iterdump()) + '\n')


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=0).run(unittest.TestSuite([Make('test_make')]))
    sys.exit(0 if result.wasSuccessful() else 1)
