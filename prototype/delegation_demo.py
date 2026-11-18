"""Fictional demonstration data for the Adaptive Decision Authority (docs/ADAPTIVE-DECISION-AUTHORITY.md): six fictional customers on the as-of date
2026-10-24 (AUD, 2 decimal places, Australia/Sydney) that exercise each handling, the fictional decision memory (samples/decision_memory_fictional.json),
and, with with_policy, a fictional demo Owner policy. Everything is named "(fictional)"; every figure is a POC value, not a real threshold or a measured result.

    python3 prototype/delegation_demo.py --db PATH [--with-policy] [--replace]

refuses unless the database is a practice (fictional) workspace, and unless it holds no records yet (--replace clears a practice workspace first).
Stop any service using the database first. Scenarios (the arguments to give assessDecision / resolveDecision):

 1 Bayview Gelato Co      extension  DEMO-301  to 2026-11-10 (+23 days)      -> autonomous approve
 2 Northside Cafe         trial      order 800.00, 14 days (deposit on file) -> autonomous approve, no Staff step
 3 Lakeside Kiosk         trial      order 600.00, 14 days (nothing on file) -> request evidence, then approve after Staff confirm a deposit (checked in the bank
                                                                              account or on a document; the demo policy accepts a Staff-checked deposit up to
                                                                              AUD 600.00 exposure) and the identity. "The customer said so" never counts.
 4 Harbourline Catering   trial      order 5,000.00, 14 days                 -> owner review (exposure over the limit)
 5 Cityside Desserts      extension  DEMO-410  +14 days                      -> owner review (unusual size)
 6 Riverside Foods        extension  DEMO-505  +10 days                      -> owner review (records incomplete, not a decline)"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

import delegation
from records import allocate, empty_document, new_customer, new_invoice, new_payment, settings_of

ROOT = Path(__file__).resolve().parent
MEMORY = ROOT / 'samples' / 'decision_memory_fictional.json'
AS_OF = '2026-10-24'
SETTINGS = {'currency': 'AUD', 'scale': 2, 'timezone': 'Australia/Sydney', 'businessName': 'Nucleon delegation demonstration (fictional)'}
SEED = 'fictional demo seed'
WHEN = AS_OF + 'T00:00:00+00:00'
DEMO_POLICY = {'mode': 'delegated', 'paused': False,
               'limits': {'maxDecisionExposure': '1000.00', 'maxCustomerExposure': '1500.00', 'maxAutonomousExposure30d': '5000.00'},
               'extensions': {'enabled': True, 'maxDays': 30, 'requireNothingElseOverdue': True, 'maxPriorLateShare': '0.25'},
               'newCustomers': {'trialCredit': 'limited', 'maxExposure': '600.00', 'minDepositShare': '0.25', 'maxTermsDays': 30, 'tradeReferenceAbove': '1000.00',
                             'staffCheckedDepositUpTo': '600.00'},
               'evidence': {'confirmedCoverageAbove': None}, 'restrictions': {'holdCustomers': [], 'unusualSizeMultiple': 3},
               'trackRecord': {'minReviewedCases': 5, 'minAgreement': '0.8'}}


class Ids:
    """Stable ids, so a demonstration is the same every time."""

    def __init__(self):
        self.n = 0

    def __call__(self, kind):
        self.n += 1
        return kind + '_demo_' + str(self.n).zfill(3)


def build():
    """(records document, the ids a scenario needs). Built with the same record functions the Records page uses, plus the two defects of Riverside Foods
    (an invoice with no amount, a payment with no received date) that those functions would refuse to enter."""
    today, ids = date.fromisoformat(AS_OF), Ids()
    doc = {**empty_document(SETTINGS, practice=True), 'asOfDate': AS_OF}
    origin = {'kind': 'manual', 'by': 'fictional_seed', 'role': 'staff', 'actorName': None, 'actorRole': 'staff', 'at': WHEN}
    names = {}

    def customer(key, name):
        names[key] = new_customer(doc, {'name': name + ' (fictional)'}, 'customer_demo_' + key, origin)['id']
        return names[key]

    def invoice(cid, ref, issue, total, due, owed=None):
        body = {'customerId': cid, 'reference': ref, 'issueDate': issue, 'total': total, 'dueDate': due,
                **({'stillOwed': owed, 'stillOwedAsOf': AS_OF} if owed else {})}
        return new_invoice(doc, body, SETTINGS, today, ids('invoice'), origin)

    def paid(cid, inv, amount, on, ref):
        p = new_payment(doc, {'customerId': cid, 'receivedDate': on, 'amount': amount, 'reference': ref}, SETTINGS, today, ids('payment'), origin)
        allocate(doc, {'paymentId': p['id'], 'allocations': [{'invoiceId': inv['id'], 'amount': amount}]}, SETTINGS, ids, origin)
        return p

    def history(cid, key, amounts, first='2026-03-02'):
        """Earlier invoices, each paid three days before it fell due."""
        y, m, d = (int(x) for x in first.split('-'))
        for n, amount in enumerate(amounts):
            issue, due = date(y, m + n, d).isoformat(), date(y, m + n, d + 14).isoformat()
            inv = invoice(cid, 'INV-' + key + '-' + str(n + 1), issue, amount, due)
            paid(cid, inv, amount, date(y, m + n, d + 11).isoformat(), 'EFT-' + key + str(n + 1))
    bay = customer('bayview', 'Bayview Gelato Co')
    history(bay, 'BV', ['412.00', '455.50', '480.00', '430.00', '520.00', '465.00'])
    invoice(bay, 'DEMO-301', '2026-10-04', '480.00', '2026-10-18', owed='480.00')
    north = customer('northside', 'Northside Cafe')
    new_payment(doc, {'customerId': north, 'receivedDate': '2026-10-23', 'amount': '200.00', 'reference': 'DEP-NS-01'}, SETTINGS, today, ids('payment'), origin)
    customer('lakeside', 'Lakeside Kiosk')
    harbour = customer('harbourline', 'Harbourline Catering')
    new_payment(doc, {'customerId': harbour, 'receivedDate': '2026-10-22', 'amount': '1000.00', 'reference': 'DEP-HL-01'}, SETTINGS, today, ids('payment'), origin)
    city = customer('cityside', 'Cityside Desserts')
    history(city, 'CS', ['180.00', '200.00', '190.00', '210.00', '220.00'], first='2026-04-01')
    invoice(city, 'DEMO-410', '2026-10-14', '900.00', '2026-10-28', owed='900.00')
    river = customer('riverside', 'Riverside Foods')
    history(river, 'RV', ['260.00', '310.00', '280.00'], first='2026-05-04')
    invoice(river, 'DEMO-504', '2026-09-01', '250.00', '2026-09-15')
    doc['invoices'][-1]['total'] = None   # the invoice has no amount: the records cannot read it
    gap = new_payment(doc, {'customerId': river, 'receivedDate': '2026-09-20', 'amount': '150.00', 'reference': 'EFT-RV-9'}, SETTINGS, today, ids('payment'), origin)
    gap['receivedDate'] = None   # a payment with no received date and no allocation: it cannot be placed
    invoice(river, 'DEMO-505', '2026-10-06', '300.00', '2026-10-20', owed='300.00')
    inv = {i['reference']: i['id'] for i in doc['invoices']}
    return doc, {'customers': names, 'invoices': inv, 'asOf': AS_OF}


def practice_problem(app):
    """Why this database may not be seeded, else None: only a practice (fictional) workspace takes fictional data."""
    ws, doc = app.meta('workspace'), app.fixture()
    if ws is not None and ws.get('mode') != 'practice':
        return 'This is a real workspace (' + str(ws.get('mode')) + '). The delegation demonstration is fictional and loads only into a practice workspace.'
    if doc is not None and doc.get('dataMode') != 'fictional':
        return 'These records are not marked fictional, so nothing was loaded.'
    return None


def seed(app, with_policy=False, replace=False):
    """Load the fictional records, the fictional decision memory and (with_policy) the fictional demo policy into a practice workspace. Refuses a real one, and
    (unless replace) one that already holds records or requests. Returns the ids the scenarios use. Takes the lock; one transaction."""
    problem = practice_problem(app)
    if problem:
        raise ValueError(problem)
    memory = json.loads(MEMORY.read_text())
    doc, ids = build()
    with app.lock:
        existing = app.fixture()
        if not replace and (app.records() or existing and (existing['customers'] or existing['invoices'])):
            raise ValueError('This workspace already holds records or requests. Use a new database, or --replace to clear it first.')
        with app.db:
            for table in ('requests', 'events', 'idempotency', 'runs', 'actions', 'record_ops', 'delegation_policies', 'decision_cases', 'confirmed_facts', 'case_events', 'notices'):
                app.db.execute('DELETE FROM ' + table)
            if app.meta('workspace') is None:
                app.set_meta('workspace', {'mode': 'practice', 'origin': 'delegation_demo', 'createdAt': WHEN, 'sampleFingerprint': None, 'skips': {}})
            app.replace_doc(doc)
            app.db.execute(
                'INSERT INTO confirmed_facts (id, customer_id, kind, created_at, data) VALUES (?,?,?,?,?)',
                ('fact_demo_northside', ids['customers']['northside'], 'business_identity', '2026-10-20T09:00:00+00:00',
                 json.dumps({'values': {'registration': 'Registration 000 000 000 (fictional)', 'tradingName': 'Northside Cafe (fictional)', 'basis': 'document'},
                             'provenance': {'role': 'staff', 'actorId': SEED, 'channel': 'seed', 'actionId': None, 'caseId': None, 'at': '2026-10-20T09:00:00+00:00',
                                            'source': 'fictional seed', 'note': 'Fictional seed: not confirmed by a real person.'}})))
            for c in memory['cases']:
                data = {k: c[k] for k in ('fictional', 'customerName', 'summary', 'features', 'ownerDecision', 'ownerReason', 'outcome', 'decidedOn')}
                at = c['decidedOn'] + 'T00:00:00+00:00'
                app.db.execute('INSERT INTO decision_cases (id, kind, subject, status, dataset, created_at, updated_at, data) VALUES (?,?,?,?,?,?,?,?)',
                               (c['id'], c['kind'], c['id'], 'decided', c['dataset'], at, at, json.dumps({**data, 'version': 1})))
            if with_policy:
                rules = delegation.validate_policy(DEMO_POLICY, settings_of(doc))
                app.db.execute('INSERT INTO delegation_policies (version, created_at, data) VALUES (?,?,?)',
                               (1, WHEN, json.dumps({**rules, 'createdBy': {'actorId': SEED, 'role': 'owner', 'channel': 'seed', 'actorName': None},
                                                     'note': 'Fictional demo policy loaded by the demonstration seed: fictional POC values, not real thresholds.', 'action': 'seed'})))
            app.set_meta('lastReset', {'at': WHEN, 'by': SEED, 'backup': None, 'kind': 'delegation_demo'})   # a new datasetId: the records were replaced
    return {**ids, 'memoryCases': len(memory['cases']), 'policyVersion': 1 if with_policy else 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--db', required=True, help='the SQLite database of a practice workspace (created if missing)')
    parser.add_argument('--with-policy', action='store_true', help='also save the fictional demo Owner policy as version 1')
    parser.add_argument('--replace', action='store_true', help='clear the practice workspace first')
    args = parser.parse_args(argv)
    from server import App
    app = App(args.db, 'mock', sample_data=False)
    try:
        out = seed(app, args.with_policy, args.replace)
    except ValueError as exc:
        print('Not loaded: ' + str(exc), file=sys.stderr)
        return 1
    finally:
        app.close()
    print(json.dumps(out, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
