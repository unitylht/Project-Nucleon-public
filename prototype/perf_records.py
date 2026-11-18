"""Measure what the Records page, case preparation and a records change cost at larger, fictional record volumes.

    python3 prototype/perf_records.py [--sizes 500 5000 20000] [--repeat 3]

Each dataset is generated from a fixed seed (the same records every run): customers with an opening balance said to have no
credits, invoices (some with a stated amount), payments allocated to them, and owner completeness statements. It is written straight
into the record tables of a temporary database. Timings use the test agent (no model) and are wall-clock seconds on this machine.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import tempfile
import threading
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

from server import App, make_server

TODAY = date(2026, 10, 18)
CREATED, CONFIRMED = '2026-10-17T01:00:00+00:00', '2026-10-17T23:00:00+00:00'   # records exist before completeness is confirmed


def money(units):
    return {'minorUnits': str(units), 'currency': 'AUD', 'scale': 2}


def dataset(size, seed=3605):
    """About `size` records: 1 customer per 50, 45% invoices, 35% payments, the rest allocations, opening balances and statements.
    Half the customers have payments confirmed complete and their leftover money marked, so exact amounts arise too."""
    rng = random.Random(seed + size)
    customers = max(2, size // 50)
    origin = {'kind': 'manual', 'by': 'staff_demo', 'role': 'staff', 'at': CREATED}
    doc = {'dataMode': 'fictional', 'version': 0, 'businessTimezone': 'Australia/Sydney', 'currency': 'AUD', 'scale': 2, 'businessName': 'Perf Practice',
           'customers': [], 'invoices': [], 'notes': [], 'payments': [], 'allocations': [], 'openingBalances': [], 'coverage': []}

    def record(**fields):
        return {**fields, 'status': 'active', 'version': 1, 'origin': origin, 'setBy': origin, 'history': []}
    for c in range(customers):
        cid = 'customer_p%05d' % c
        doc['customers'].append(record(id=cid, displayCode='C-%05d' % (c + 1), name='Perf Customer %d' % c))
        doc['openingBalances'].append(record(id='opening_p%05d' % c, customerId=cid, asOf='2026-09-30', amount=money(0), credits='none',
                                             sourceLabel='Generated'))
    for n in range(int(size * 0.45)):
        cid = 'customer_p%05d' % rng.randrange(customers)
        issue = date(2026, 10, 1) + timedelta(days=rng.randrange(17))
        total = rng.randrange(10000, 500000)
        stated = rng.random() < 0.2
        doc['invoices'].append(record(id='invoice_p%06d' % n, customerId=cid, reference='DEMO-%06d' % n, issueDate=issue.isoformat(), total=money(total),
                                      originalDueDate=(issue + timedelta(days=30)).isoformat(),
                                      outstandingAmount=money(total) if stated else None, outstandingAsOf=issue.isoformat() if stated else None,
                                      outstandingSource='manual' if stated else None))
    by_customer = {}
    for invoice in doc['invoices']:
        by_customer.setdefault(invoice['customerId'], []).append(invoice)
    allocations = int(size * 0.18)
    for n in range(int(size * 0.35)):
        cid = 'customer_p%05d' % rng.randrange(customers)
        received = date(2026, 10, 1) + timedelta(days=rng.randrange(18))
        amount = rng.randrange(1000, 100000)
        payment = record(id='payment_p%06d' % n, customerId=cid, receivedDate=received.isoformat(), amount=money(amount), reference='EFT %06d' % n, kind='payment')
        doc['payments'].append(payment)
        own = [i for i in by_customer.get(cid, []) if i['issueDate'] <= payment['receivedDate'] and not i['outstandingAsOf']]
        if own and len(doc['allocations']) < allocations:
            invoice = rng.choice(own)
            doc['allocations'].append(record(id='allocation_p%06d' % n, paymentId=payment['id'], invoiceId=invoice['id'], customerId=cid,
                                             amount=money(min(amount, int(invoice['total']['minorUnits']) // 4))))
    allocated = {}
    for allocation in doc['allocations']:
        allocated[allocation['paymentId']] = allocated.get(allocation['paymentId'], 0) + int(allocation['amount']['minorUnits'])
    covered = {'customer_p%05d' % c for c in range(0, customers, 2)}
    for payment in doc['payments']:   # the covered customers' leftover money is said not to be for an open invoice, so exact amounts arise
        if payment['customerId'] in covered and int(payment['amount']['minorUnits']) > allocated.get(payment['id'], 0):
            payment['notForOpenInvoices'] = {'by': 'staff_demo', 'role': 'staff', 'at': CREATED, 'reason': 'Generated'}
    for c in range(0, customers, 2):
        doc['coverage'].append(record(id='coverage_p%05d' % c, customers=['customer_p%05d' % c], recordTypes=['payments'], **{'from': '2026-10-01'}, to='2026-10-18',
                                      basis='attestation', batchId=None, sourceLabel='Generated', confirmedBy='owner_demo', confirmedRole='owner',
                                      confirmedAt=CONFIRMED))
    return doc


def timed(fn, repeat):
    runs = []
    for _ in range(repeat):
        started = time.perf_counter()
        fn()
        runs.append(time.perf_counter() - started)
    return statistics.median(runs)


def call(base, path, body=None, cookie=None, key=None):
    headers = {'Content-Type': 'application/json'} if body is not None else {}
    if cookie:
        headers['Cookie'] = cookie
    if key:
        headers['Idempotency-Key'] = key
    with urlopen(Request(base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers), timeout=600) as response:
        return json.loads(response.read()), response.headers


def measure(size, repeat):
    doc = dataset(size)
    total = sum(len(doc[k]) for k in ('customers', 'invoices', 'payments', 'allocations', 'openingBalances', 'coverage'))
    with tempfile.TemporaryDirectory() as tmp:
        app = App(Path(tmp) / 'perf.sqlite3', 'mock', today=lambda: TODAY, inline_wait=0)
        with app.lock, app.db:
            app.set_meta('workspace', {'mode': 'practice', 'origin': 'first_run', 'createdAt': CREATED, 'sampleFingerprint': None, 'skips': {}})
            started = time.perf_counter()
            app.save_doc(doc)
            loaded = time.perf_counter() - started
        server = make_server(app, 0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = 'http://127.0.0.1:%d' % server.server_port
        cookies = {}
        for role in ('staff', 'owner'):
            _, headers = call(base, '/api/demo/login', {'accessCode': app.demo_codes[role]})
            cookies[role] = headers['Set-Cookie'].split(';')[0]
        result = {'records': total, 'customers': len(doc['customers']), 'invoices': len(doc['invoices']), 'payments': len(doc['payments']),
                  'allocations': len(doc['allocations']), 'write all (s)': loaded}
        result['records page (s)'] = timed(lambda: call(base, '/api/records', cookie=cookies['staff']), repeat)
        result['records page (KB)'] = len(json.dumps(call(base, '/api/records', cookie=cookies['staff'])[0])) // 1024
        with app.lock:
            result['evidence (s)'] = timed(app.evidence, repeat)
        invoices = [i for i in doc['invoices'] if not i['outstandingAsOf']][:6]
        cases = []
        started = time.perf_counter()
        for n, invoice in enumerate(invoices):
            r, _ = call(base, '/api/requests', {'messageText': 'Could we pay invoice %s on 2026-12-18 instead?' % invoice['reference']}, cookies['staff'], 'perf-%d' % n)
            cases.append(r['id'])
        for case_id in cases:
            while call(base, '/api/requests/' + case_id, cookie=cookies['owner'])[0]['status'] in ('received', 'analysing'):
                time.sleep(0.05)
        result['prepare one case (s)'] = (time.perf_counter() - started) / len(cases)
        for n, case_id in enumerate(cases[:3]):   # three decided cases, three left waiting for the owner
            r, _ = call(base, '/api/requests/' + case_id, cookie=cookies['owner'])
            call(base, '/api/requests/' + case_id + '/decisions', {'expectedRequestVersion': r['version'], 'analysisId': r['analysis']['id'],
                                                                   'evidenceVersion': r['analysis']['snapshot']['evidenceVersion'], 'outcome': 'approve',
                                                                   'approvedDueDate': '2026-12-18', 'reason': 'Measurement.'}, cookies['owner'], 'decide-%d' % n)
        customer = invoices[-1]['customerId']
        started = time.perf_counter()
        call(base, '/api/records/payments', {'customerId': customer, 'receivedDate': '2026-10-18', 'amount': '1.00', 'reference': 'Perf'}, cookies['staff'], 'perf-pay')
        result['one records change (s)'] = time.perf_counter() - started
        server.shutdown()
        server.server_close()
        app.close()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sizes', type=int, nargs='+', default=[500, 5000, 20000])
    parser.add_argument('--repeat', type=int, default=3)
    args = parser.parse_args()
    rows = []
    for size in args.sizes:
        rows.append(measure(size, args.repeat))
        print(json.dumps({k: round(v, 3) if isinstance(v, float) else v for k, v in rows[-1].items()}), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
