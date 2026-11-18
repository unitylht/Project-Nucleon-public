"""Rehearse moving a deployed Slice 2 database to the Stage 3 release, and the two ways back, on disposable copies only.

    python3 deploy/rehearse_stage3_upgrade.py --db ~/srv/nucleon/data/nucleon.sqlite3 --old-app <checkout of 89b92d8> [--work DIR]

The live database is only read (SQLite backup API, read-only). Each step runs the real server code of one release, with the
test agent (no model) and sampleData as on the practice instance, against its own copy. Records written here are fictional.
It reports what a code-only rollback shows and what restoring the pre-upgrade backup would discard.
"""
from __future__ import annotations

import argparse
import json
import re
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

NEW_APP = Path(__file__).resolve().parent.parent
results, running = [], []   # servers still running, stopped even when a step fails


def ok(name, passed, detail=''):
    results.append(bool(passed))
    print(('PASS ' if passed else 'FAIL ') + name + (' | ' + str(detail) if detail not in ('', None) else ''), flush=True)


def info(*parts):
    print('INFO', *parts, flush=True)


def copy(src, dst):
    source = sqlite3.connect('file:' + str(src) + '?mode=ro', uri=True)
    target = sqlite3.connect(str(dst))
    source.backup(target)
    source.close()
    target.close()


def rows(db, sql):
    con = sqlite3.connect('file:' + str(db) + '?mode=ro', uri=True)
    try:
        return con.execute(sql).fetchall()
    except sqlite3.OperationalError:   # a table the older release doesn't have
        return []
    finally:
        con.close()


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class Server:
    """One release's server.py on one database copy, test agent, sampleData set. Codes are read from its output, never printed."""

    def __init__(self, app_dir, db, python):
        port = free_port()
        self.proc = subprocess.Popen([python, '-u', str(Path(app_dir) / 'prototype' / 'server.py'), '--db', str(db), '--port', str(port),
                                      '--agent-mode', 'mock', '--sample-data'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        running.append(self)
        self.base, self.codes, self.output, self.cookies = 'http://127.0.0.1:' + str(port), {}, [], {}
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and not {'STAFF', 'OWNER'} <= set(self.codes):
            line = self.proc.stdout.readline()
            if not line:
                break   # the server exited
            match = re.match(r'(STAFF|OWNER|OPERATOR) access code: (\S+)', line)
            if match:
                self.codes[match.group(1)] = match.group(2)
            else:
                self.output.append(line.rstrip())
        threading.Thread(target=lambda: [self.output.append(l.rstrip()) for l in self.proc.stdout], daemon=True).start()
        if self.started:
            for role in ('staff', 'owner'):
                _, _, headers = self.call('/api/demo/login', {'accessCode': self.codes[role.upper()]})
                self.cookies[role] = headers['Set-Cookie'].split(';')[0]

    @property
    def started(self):
        return {'STAFF', 'OWNER'} <= set(self.codes)

    def call(self, path, body=None, role=None, key=None):
        headers = {'Content-Type': 'application/json'} if body is not None else {}
        if role:
            headers['Cookie'] = self.cookies[role]
        if key:
            headers['Idempotency-Key'] = key
        request = Request(self.base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
        try:
            response = urlopen(request, timeout=30)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.loads(response.read()), response.headers

    def must(self, path, body=None, role='staff', key=None):
        status, result, _ = self.call(path, body, role, key or 'rehearsal-' + path + json.dumps(body, sort_keys=True)[:80])
        if status not in (200, 201, 202):
            raise RuntimeError(path + ' -> ' + str(status) + ' ' + json.dumps(result)[:300])
        return result

    def settle(self, request_id, timeout=30):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            r = self.call('/api/requests/' + request_id, role='owner')[1]
            if r['status'] not in ('received', 'analysing'):
                return r
            time.sleep(0.2)
        raise TimeoutError(request_id)

    def stop(self):
        if self in running:
            running.remove(self)
        self.proc.terminate()
        try:
            self.proc.wait(10)
        except subprocess.TimeoutExpired:
            self.proc.kill()

    def tail(self, n=3):
        return ' / '.join(self.output[-n:])


def cases_of(db):
    return sorted((i, json.loads(d)['status']) for i, d in rows(db, 'SELECT id, data FROM requests'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True, help='the deployed database; only read')
    parser.add_argument('--old-app', required=True, help='a checkout of the previous release (89b92d8)')
    parser.add_argument('--python', default=sys.executable)
    parser.add_argument('--work', help='where the copies go (default: a new temporary folder)')
    args = parser.parse_args()
    work = Path(args.work or tempfile.mkdtemp(prefix='nucleon-rehearsal-'))
    work.mkdir(parents=True, exist_ok=True)
    info('copies in', work)

    original = work / 'original.sqlite3'
    copy(args.db, original)
    document = json.loads(rows(original, 'SELECT data FROM fixtures WHERE id=1')[0][0])
    before = cases_of(original)
    info('copy of the deployed database:', len(before), 'cases;', len(document['customers']), 'customers;', len(document['invoices']), 'invoices')

    # 1. Upgrade a copy
    upgraded = work / 'upgraded.sqlite3'
    copy(original, upgraded)
    new = Server(NEW_APP, upgraded, args.python)
    ok('upgrade: Stage 3 starts on the copy', new.started, new.tail())
    if not new.started:
        return finish()
    records = new.must('/api/records')
    ok('upgrade: records unchanged', all(records[k] == document[k] for k in ('customers', 'invoices', 'notes')))
    cases = sorted((c['id'], c['status']) for c in new.must('/api/requests', role='owner'))
    ok('upgrade: every case kept, with its status', cases == before, cases)
    stored = {i: json.loads(d) for i, d in rows(original, 'SELECT id, data FROM requests')}
    for case_id, status in cases:
        if status == 'awaiting_owner':
            now = new.must('/api/requests/' + case_id, role='owner')
            ok('upgrade: pending case ' + case_id[-6:] + ' kept its prepared brief (re-stamped, not prepared again)',
               now['analysis']['id'] == stored[case_id]['analysis']['id'])
        if status in ('decided', 'completed'):
            history = [e['kind'] for e in new.must('/api/requests/' + case_id, role='owner')['history']]
            ok('upgrade: decided case ' + case_id[-6:] + ' gets a baseline for later changes', 'evidence.baseline_recorded' in history)

    # 2. Records made after the upgrade (fictional)
    supplies, logistics = document['customers'][0], document['customers'][1]
    invoice = next(i for i in document['invoices'] if i['customerId'] == supplies['id'])
    today = document['asOfDate']
    payment = new.must('/api/records/payments', {'customerId': supplies['id'], 'receivedDate': today, 'amount': '250.00', 'reference': 'Rehearsal'})['record']
    allocation = new.must('/api/records/allocations', {'paymentId': payment['id'], 'allocations': [{'invoiceId': invoice['id'], 'amount': '250.00'}]})['records'][0]
    new.must('/api/records/allocations/' + allocation['id'] + '/statement', {'status': 'missed'})
    new.must('/api/records/openingBalances', {'customerId': logistics['id'], 'asOf': '2026-09-30', 'amount': '0.00', 'sourceLabel': 'Rehearsal'})
    new.must('/api/records/coverage', {'customers': [supplies['id']], 'recordTypes': ['payments'], 'from': '2026-10-01', 'to': today,
                                       'sourceLabel': 'Rehearsal', 'confirm': True}, role='owner')
    # A new request after the upgrade, decided by the owner (the test agent reads only DEMO-### numbers and ISO dates)
    logistics_invoice = next(i for i in document['invoices'] if i['customerId'] == logistics['id'] and (i.get('originalDueDate') or '') > today)
    created = new.must('/api/requests', {'messageText': 'Could we pay invoice ' + logistics_invoice['reference'] + ' on 2026-11-27 instead?'}, key='rehearsal-request')
    r = new.settle(created['id'])
    decided = None
    if r['status'] == 'awaiting_owner':
        new.must('/api/requests/' + r['id'] + '/decisions', {'expectedRequestVersion': r['version'], 'analysisId': r['analysis']['id'],
                                                             'evidenceVersion': r['analysis']['snapshot']['evidenceVersion'], 'outcome': 'approve',
                                                             'approvedDueDate': '2026-11-27', 'reason': 'Upgrade rehearsal (fictional).'}, role='owner')
        decided = r['id']
    cases = sorted(cases + [(created['id'], 'completed')])
    ok('after the upgrade: payment, allocation, answer, opening balance, completeness and a decided request recorded', decided is not None, r['status'])
    new.stop()
    after = work / 'upgraded-after.sqlite3'
    copy(upgraded, after)

    # 3. Code-only rollback to the previous release
    code_only = work / 'rollback-code-only.sqlite3'
    copy(after, code_only)
    old = Server(args.old_app, code_only, args.python)
    ok('code-only rollback: the previous release starts on the upgraded copy', old.started, old.tail())
    if old.started:
        seen = old.must('/api/records')
        ok('code-only rollback: it shows the records as they were at the upgrade (later payments and opening balances are not there)',
           all(seen[k] == document[k] for k in ('customers', 'invoices', 'notes')) and not seen.get('payments'))
        ok('code-only rollback: cases, including the decision made after the upgrade, are still listed',
           sorted(c['id'] for c in old.must('/api/requests', role='owner')) == [c for c, _ in cases])
        old.must('/api/records/customers', {'name': 'Rehearsal Kiosk'})   # a records change made under the previous release
        old.stop()
        again = Server(NEW_APP, code_only, args.python)
        refused = not again.started and any('changed after the records moved into tables' in line for line in again.output)
        ok('code-only rollback, then Stage 3 again: it refuses to start and says why', refused, again.tail(1))
        again.stop()

    # 4. Rollback by restoring the pre-upgrade backup
    restored = work / 'rollback-restore.sqlite3'
    copy(original, restored)
    old = Server(args.old_app, restored, args.python)
    ok('restore rollback: the previous release starts on the pre-upgrade backup', old.started, old.tail())
    if old.started:
        ok('restore rollback: cases and records are exactly as before the upgrade',
           sorted((c['id'], c['status']) for c in old.must('/api/requests', role='owner')) == before and old.must('/api/records')['invoices'] == document['invoices'])
        old.stop()
    lost = {'payments': rows(after, 'SELECT COUNT(*) FROM payments')[0][0], 'allocations': rows(after, 'SELECT COUNT(*) FROM allocations')[0][0],
            'opening balances': rows(after, 'SELECT COUNT(*) FROM opening_balances')[0][0], 'completeness statements': rows(after, 'SELECT COUNT(*) FROM coverage')[0][0],
            'events': rows(after, 'SELECT COUNT(*) FROM events')[0][0] - rows(original, 'SELECT COUNT(*) FROM events')[0][0],
            'imports': rows(after, 'SELECT COUNT(*) FROM batches')[0][0] - rows(original, 'SELECT COUNT(*) FROM batches')[0][0]}
    changed_cases = [c for c, s in cases_of(after) if (c, s) not in before]
    info('restoring the pre-upgrade backup discards everything after the upgrade:', json.dumps(lost),
         '| cases whose status changed after the upgrade (their new state is lost):', changed_cases)

    # 5. Forward again from the Stage 3 copy
    forward = work / 'forward.sqlite3'
    copy(after, forward)
    new = Server(NEW_APP, forward, args.python)
    ok('forward again: Stage 3 starts on its own copy', new.started, new.tail())
    if new.started:
        records = new.must('/api/records')
        ok('forward again: everything made after the upgrade is there', len(records['payments']) == 1 and len(records['openingBalances']) == 1
           and len(records['coverage']) == 1)
        new.stop()
    return finish()


def finish():
    print('RESULT', sum(results), '/', len(results))
    return 0 if all(results) else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    finally:
        for server in list(running):
            server.stop()
