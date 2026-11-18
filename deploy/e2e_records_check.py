"""Slice 2 checks through the deployed HTTPS URL (run on the server; codes come from the private service log).

    python3 deploy/e2e_records_check.py production --compare <pre-deploy backup.sqlite3>   read-only: nothing is written
    python3 deploy/e2e_records_check.py seed <db-file> practice|real                     an explicitly set-up, empty workspace
    nucleonctl isolate <name>                 then one of:
    python3 deploy/e2e_records_check.py practice      (fresh database: sampleData gives practice + sample)
    python3 deploy/e2e_records_check.py empty         (database seeded 'practice': must stay empty)
    python3 deploy/e2e_records_check.py real          (database seeded 'real': refuses the sample, no console)

All data is fictional. The request flows use whatever agent the service runs (live Gemma on the home server).
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).parent))
from e2e_https_check import Site, ok, results  # noqa: E402

CSV = """Customer,Invoice No,Invoice Date,Amount,Due Date,Balance
Bayside Café,INV-2001,01/10/2026,"1,200.00",31/10/2026,1200.00
Coastline Foods,INV-2002,03/10/2026,450.50,02/11/2026,450.50
Dune Traders,INV-2003,31/02/2026,300.00,,300.00
"""


def seed(db, mode):
    """A database whose owner already chose this workspace type; the service must respect it whatever sampleData says."""
    path = Path(db)
    if path.exists():
        sys.exit('refusing to seed an existing file: ' + db)
    con = sqlite3.connect(db)
    con.execute('CREATE TABLE meta (key TEXT PRIMARY KEY, data TEXT NOT NULL)')
    con.execute('INSERT INTO meta VALUES (?, ?)', ('workspace', json.dumps({'mode': mode, 'origin': 'first_run', 'createdAt': time.strftime('%Y-%m-%dT%H:%M:%S'),
                                                                          'createdBy': 'owner_demo', 'sampleFingerprint': None, 'skips': {}})))
    con.commit()
    con.close()
    path.chmod(0o600)
    print('seeded', db, 'as an empty', mode, 'workspace')


def step(site, path, body, role='owner', key=None, expect=200, name=None):
    status, data, _ = site.call(path, body, role, key or path + json.dumps(body, sort_keys=True)[:60])
    ok(name or (path + ' -> ' + str(expect)), status == expect, data.get('message') or data.get('error') or '')
    return data


def settings(site):
    return step(site, '/api/setup/settings', {'currency': 'AUD', 'scale': 2, 'timezone': 'Australia/Sydney', 'businessName': 'Harbourside Practice Co'},
                name='owner saves settings')


def decide_flow(site, message, label, choose=None):
    """A staff request through the agent to a completed owner decision; optionally a staff choice between customers."""
    r = site.submit(message)
    if choose:
        ok(label + ': shared number asks staff to choose', r['status'] == 'needs_information' and r['task']['missingFields'][0]['field'] == 'invoiceId',
           r.get('task', {}).get('question'))
        target = next(c for c in r['task']['missingFields'][0]['choices'] if c['customerName'] == choose)
        site.call('/api/requests/' + r['id'] + '/clarifications/' + r['task']['id'] + '/answers',
                  {'expectedRequestVersion': r['version'], 'answers': [{'field': 'invoiceId', 'value': target['invoiceId']}]}, 'staff', 'choose-' + r['id'])
        r = site.settle(r['id'])
        ok(label + ': resolved to the chosen invoice', r.get('invoiceId') == target['invoiceId'], r['analysis']['snapshot']['customer']['name'])
    ok(label + ': owner case prepared', r['status'] == 'awaiting_owner', r['status'] + ' / ' + str((r.get('analysis') or {}).get('aiStatus')))
    if r['status'] != 'awaiting_owner':
        return r
    requested = next(f['value'] for f in r['analysis']['brief']['facts'] if f['key'] == 'requestedDueDate')
    body = {'expectedRequestVersion': r['version'], 'analysisId': r['analysis']['id'], 'evidenceVersion': r['analysis']['snapshot']['evidenceVersion'],
            'outcome': 'approve', 'approvedDueDate': requested, 'reason': 'Deployment check: this invoice only.'}
    status, decision, _ = site.call('/api/requests/' + r['id'] + '/decisions', body, 'owner', 'decide-' + r['id'])
    ok(label + ': owner decision committed', status == 201, decision.get('outcome'))
    r = site.settle(r['id'])
    ok(label + ': completed with a reply draft (not sent)', r['status'] == 'completed' and r['responseDraft']['deliveryStatus'] == 'not_sent')
    return r


def csv_flow(site, label):
    as_of = site.call('/api/setup', role='staff')[1]['asOfDate']   # the workspace's own 'today' (the sample's is fixed)
    batch = step(site, '/api/imports', {'sourceLabel': 'Deployment check spreadsheet', 'fileName': 'check.csv', 'csvText': CSV}, role='staff',
                 name=label + ': CSV uploaded for preview')
    batch = step(site, '/api/imports/' + batch['id'] + '/mapping', {'mapping': batch['mapping'], 'asOf': as_of}, role='staff',
                 name=label + ': preview with "amounts as of"')
    statuses = sorted(r['status'] for r in batch['preview']['rows'])
    ok(label + ': preview sorts rows (rejected bad date, unknown customers)', 'rejected' in statuses, statuses)
    resolutions = {'customers': {c['key']: 'new' for c in batch['preview']['customers']}, 'conflicts': {}}
    batch = step(site, '/api/imports/' + batch['id'] + '/mapping', {'mapping': batch['mapping'], 'asOf': as_of, 'resolutions': resolutions},
                 role='staff', name=label + ': customers resolved')
    ok(label + ': preview ready', batch['preview']['ready'], batch['preview']['needs'])
    applied = step(site, '/api/imports/' + batch['id'] + '/apply', {}, role='staff', name=label + ': import applied')
    again = step(site, '/api/imports', {'sourceLabel': 'Deployment check spreadsheet', 'fileName': 'check.csv', 'csvText': CSV}, role='staff',
                 key='again-' + applied['id'], name=label + ': same file uploaded again')
    again = step(site, '/api/imports/' + again['id'] + '/mapping', {'mapping': again['mapping'], 'asOf': as_of}, role='staff',
                 name=label + ': re-import preview')
    ok(label + ': re-import adds nothing', again['preview']['counts']['new'] == 0 and again['preview']['counts']['unchanged'] == 2, again['preview']['counts'])
    return applied


def scenario_production(site, compare):
    """Read-only: the shared practice instance after deployment. Writes nothing."""
    setup = site.call('/api/setup', role='owner')[1]
    ok('production: workspace recorded as practice', (setup['workspace'] or {}).get('mode') == 'practice', setup['workspace'])
    ok('production: sample still loaded and setup ready', setup['sampleLoaded'] and setup['ready'])
    cases = site.call('/api/requests', role='owner')[1]
    before = [json.loads(d) for (d,) in sqlite3.connect('file:' + compare + '?mode=ro', uri=True).execute('SELECT data FROM requests')]
    ok('production: every case kept with its status', sorted((c['id'], c['status']) for c in cases) == sorted((c['id'], c['status']) for c in before),
       str(len(cases)) + ' cases')
    for c in cases:
        if c['status'] == 'awaiting_owner':
            full = site.call('/api/requests/' + c['id'], role='owner')[1]
            ok('production: pending case ' + c['id'][-6:] + ' readable', full['task']['kind'] == 'approval')
    records = site.call('/api/records', role='staff')[1]
    # The sample must be there; labelled fictional records added by release checks may be too.
    sample = [i for i in records['invoices'] if i['customerId'] in ('customer_demo_01', 'customer_demo_02')]
    ok('production: Records shows the sample', {'customer_demo_01', 'customer_demo_02'} <= {c['id'] for c in records['customers']} and len(sample) == 3,
       '%d customers, %d invoices' % (len(records['customers']), len(records['invoices'])))
    ok('production: console available to the operator', site.call('/api/demo/console', role='operator')[0] == 200)
    with urlopen(Request(site.base + '/static/customers.js', headers={'User-Agent': 'nucleon-e2e'}), timeout=30) as page:
        ok('production: Customers page script served', page.status == 200 and b'PAGES.customer' in page.read())


def scenario_practice(site):
    setup = site.call('/api/setup', role='owner')[1]
    ok('practice: fresh database set up from sampleData', setup['workspace']['mode'] == 'practice' and setup['sampleLoaded'], setup['workspace'])
    customer = step(site, '/api/records/customers', {'name': 'Harbour Kiosk'}, role='staff', name='practice: manual customer added')['record']
    step(site, '/api/records/invoices', {'customerId': customer['id'], 'reference': 'DEMO-101', 'issueDate': '2026-10-02', 'total': '330.00',
                                         'dueDate': '2026-10-23', 'stillOwed': '330.00', 'stillOwedAsOf': '2026-10-16'},
         role='staff', name='practice: manual invoice with a number another customer also has')
    decide_flow(site, "Hi, could we pay invoice DEMO-101 on Friday 30 October instead?", 'practice', choose='Harbour Kiosk')
    csv_flow(site, 'practice')


def scenario_empty(site):
    setup = site.call('/api/setup', role='owner')[1]
    ok('empty: explicit practice workspace stayed empty despite sampleData', setup['workspace']['mode'] == 'practice' and not setup['sampleLoaded']
       and setup['settings'] is None, setup['workspace'])
    status, error, _ = site.call('/api/requests', {'messageText': 'Can we pay INV-1 later?'}, 'staff', 'too-early')
    ok('empty: requests refused until setup is done', status == 409 and error['error'] == 'NO_RECORDS')
    settings(site)
    customer = step(site, '/api/records/customers', {'name': 'Bayside Café'}, role='staff', name='empty: customer added')['record']
    step(site, '/api/records/invoices', {'customerId': customer['id'], 'reference': 'INV-1001', 'issueDate': '2026-10-01', 'total': '1200.00'},
         role='staff', name='empty: invoice added (no due date, nothing stated)')
    r = decide_flow(site, "Hi, it's Bayside Café. Could we pay INV-1001 on 6 November? Cash is tight this month.", 'empty')
    facts = {f['key']: f for f in ((r.get('analysis') or {}).get('brief') or {}).get('facts', [])}
    ok('empty: unknowns stated, nothing invented', facts.get('outstandingAmount', {}).get('kind') == 'unknown'
       and facts.get('daysOverdue', {}).get('value') is None)


def scenario_real(site):
    setup = site.call('/api/setup', role='owner')[1]
    ok('real: workspace is real and empty', setup['workspace']['mode'] == 'real' and not setup['sampleLoaded'], setup['workspace'])
    status, error, _ = site.call('/api/setup/sample', {}, 'owner', 'no-sample')
    ok('real: sample refused', status == 409 and error['error'] in ('REAL_WORKSPACE', 'NO_WORKSPACE'), error.get('error'))
    ok('real: no demo console', site.call('/api/demo/console', role='operator')[0] == 404)
    settings(site)
    csv_flow(site, 'real')
    decide_flow(site, 'Could Coastline Foods pay INV-2002 on 13 November instead of 2 November?', 'real')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scenario', choices=['production', 'practice', 'empty', 'real', 'seed'])
    parser.add_argument('args', nargs='*')
    parser.add_argument('--base', default='https://nucleon.dracooz.top')
    parser.add_argument('--compare')
    options = parser.parse_args()
    if options.scenario == 'seed':
        return seed(*options.args)
    site = Site(options.base)
    site.login()
    {'production': lambda: scenario_production(site, options.compare), 'practice': lambda: scenario_practice(site),
     'empty': lambda: scenario_empty(site), 'real': lambda: scenario_real(site)}[options.scenario]()
    print('RESULT', sum(results), '/', len(results))
    return 0 if all(results) else 1


if __name__ == '__main__':
    sys.exit(main() or 0)
