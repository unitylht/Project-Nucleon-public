"""Stage 3 checks through the deployed HTTPS URL: payments, credits and allocations, opening balances and inclusion,
completeness, exact versus uncertain amounts, corrections, revert, decided-case flags, restart recovery and the no-AI path.
Run on the server; codes come from the private service log. All data is fictional.

    python3 deploy/e2e_records_check.py seed <db> practice      an empty practice workspace, then `nucleonctl isolate <name>`
    python3 deploy/e2e_stage3_check.py full                      the whole flow with the service's agent (live Gemma)
    nucleonctl restart && python3 deploy/e2e_stage3_check.py after-restart
    python3 deploy/e2e_stage3_check.py fallback                  on an isolate started with `unreachable-model`
    python3 deploy/e2e_stage3_check.py smoke                     the shared practice instance after a deploy: a small, labelled
                                                                 fictional customer, its credit and payment, completeness, and
                                                                 one owner decision. It changes nothing else.

Dates are relative to the workspace's own 'today' (the sample's is fixed), so the same checks run on any practice workspace.
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from e2e_https_check import Site, ok, results  # noqa: E402

STATE = Path.home() / 'srv/nucleon/reports/e2e-stage3-state.json'


class Flow:
    def __init__(self, site, label):
        self.site, self.label = site, label
        setup = site.call('/api/setup', role='owner')[1]
        self.today = date.fromisoformat(setup['asOfDate'])
        self.asat = self.today - timedelta(days=18)

    def day(self, offset_from_asat):
        return (self.asat + timedelta(days=offset_from_asat)).isoformat()

    def must(self, path, body=None, role='staff', expect=(200, 201, 202), name=None, key=None):
        status, result, _ = self.site.call(path, body, role, key or str(uuid.uuid4()))
        good = status in ((expect,) if isinstance(expect, int) else expect)
        ok(name or (self.label + ': ' + path + ' -> ' + str(status)), good, '' if good else json.dumps(result)[:200])
        return result

    def records(self):
        return self.site.call('/api/records', role='staff')[1]

    def invoice(self, reference, records=None):
        return next(i for i in (records or self.records())['invoices'] if i['reference'] == reference and i.get('status', 'active') == 'active')

    def customer(self, name, records=None):
        return next(c for c in (records or self.records())['customers'] if c['name'] == name)

    def exact(self, reference):
        records = self.records()
        position = records['positions']['invoices'].get(self.invoice(reference, records)['id']) or {}
        return position.get('exact'), ' '.join(records['positions'].get('notExact', {}).get(self.invoice(reference, records)['id'], []))

    def request(self, message):
        r = self.site.submit(message)
        return r

    def decide(self, r, approved):
        status, decision, _ = self.site.decide(r, approved=approved)
        ok(self.label + ': owner decision committed', status == 201, decision.get('outcome'))
        return self.site.settle(r['id'])


def natural(day_iso):
    d = date.fromisoformat(day_iso)
    return d.strftime('%A ') + str(d.day) + d.strftime(' %B')


def setup_bayside(f, name='Bayside Café', ref='INV-501', credits='none'):
    """An opening balance whose make-up is suggested by equal amounts and confirmed by a person, and a later invoice."""
    customer = f.must('/api/records/customers', {'name': name}, name=f.label + ': customer added')['record']
    f.must('/api/records/openingBalances', {'customerId': customer['id'], 'asOf': f.day(0), 'amount': '1500.00', 'direction': 'owed', 'credits': credits,
                                            'sourceLabel': "Accountant's balance list (fictional)"}, name=f.label + ': opening balance recorded')
    for number, total, offset in (('-77', '1200.00', -29), ('-78', '300.00', -15)):
        f.must('/api/records/invoices', {'customerId': customer['id'], 'reference': ref + number, 'issueDate': f.day(offset), 'total': total,
                                         'stillOwed': total, 'stillOwedAsOf': f.day(0)}, name=f.label + ': earlier invoice ' + ref + number + ' added')
    view = f.records()['positions']['customers'][customer['id']]['opening']
    ok(f.label + ': equal amounts only suggest the make-up', view['suggestion'] and sorted(view['suggestion']['references']) == [ref + '-77', ref + '-78']
       and {r['status'] for r in view['records']} == {'unresolved'}, view['suggestion'])
    for reference in view['suggestion']['references']:
        f.must('/api/records/invoices/' + f.invoice(reference)['id'] + '/inclusion', {'status': 'included'}, name=f.label + ': ' + reference + ' confirmed by a person')
    f.must('/api/records/invoices', {'customerId': customer['id'], 'reference': ref, 'issueDate': f.day(2), 'total': '1000.00',
                                     'dueDate': (f.today - timedelta(days=2)).isoformat()}, name=f.label + ': invoice ' + ref + ' added')
    return customer


def settings(site, label, name):
    setup = site.call('/api/setup', role='owner')[1]
    ok(label + ': empty practice workspace', setup['workspace']['mode'] == 'practice' and not setup['sampleLoaded'], setup['workspace'])
    status, _, _ = site.call('/api/setup/settings', {'currency': 'AUD', 'scale': 2, 'timezone': 'Australia/Sydney', 'businessName': name}, 'owner', str(uuid.uuid4()))
    ok(label + ': settings saved', status == 200)


def scenario_full(site, state):
    settings(site, 'full', 'Stage 3 check (fictional)')
    f = Flow(site, 'full')
    bayside = setup_bayside(f)

    # Payments from a bank export, each naming the invoice it pays
    csv = ('Customer,Date,Amount,Reference,Invoice\n'
           'Bayside Café,{0},1200.00,EFT 7702,INV-501-77\nBayside Café,{0},300.00,EFT 7703,INV-501-78\nBayside Café,{1},600.00,EFT 7781,INV-501\n'
           ).format(date.fromisoformat(f.day(9)).strftime('%d/%m/%Y'), date.fromisoformat(f.day(13)).strftime('%d/%m/%Y'))
    batch = f.must('/api/imports', {'sourceLabel': 'Bank export (fictional)', 'fileName': 'bank.csv', 'csvText': csv, 'shape': 'payments'},
                   name='full: payment list uploaded for preview')
    batch = f.must('/api/imports/' + batch['id'] + '/mapping', {'mapping': batch['mapping'], 'dateOrder': 'dmy'}, name='full: preview with day/month dates')
    ok('full: each payment allocated only to the invoice it names', [r['allocation'] and r['allocation']['reference'] for r in batch['preview']['rows']] ==
       ['INV-501-77', 'INV-501-78', 'INV-501'])
    batch = f.must('/api/imports/' + batch['id'] + '/apply', {}, name='full: payment list applied')
    exact, why = f.exact('INV-501')
    ok('full: without completeness the amount is not exact, and says why', exact is None and 'no confirmed completeness' in why, why[:120])

    # Completeness: only the owner, and only explicitly
    body = {'customers': [bayside['id']], 'recordTypes': ['payments'], 'from': f.day(1), 'to': f.today.isoformat(),
            'sourceLabel': 'Checked against the bank statements (fictional)', 'confirm': True}
    f.must('/api/records/coverage', body, role='staff', expect=403, name='full: staff cannot confirm completeness')
    f.must('/api/records/coverage', body, role='owner', name='full: owner confirms Bayside payments complete')
    exact, why = f.exact('INV-501')
    ok('full: exact AUD 400.00 as of today, with its steps', exact and exact['amount']['minorUnits'] == '40000' and exact['asOf'] == f.today.isoformat(),
       exact and [s['label'] for s in exact['steps']] or why)

    # An opening credit nobody has accounted for blocks exactness; recorded and applied, it comes off
    kiosk = f.must('/api/records/customers', {'name': 'Kiosk Co'}, name='full: second customer added')['record']
    opening = f.must('/api/records/openingBalances', {'customerId': kiosk['id'], 'asOf': f.day(0), 'amount': '50.00', 'direction': 'credit',
                                                      'sourceLabel': "Accountant's balance list (fictional)"}, name='full: opening credit of AUD 50.00')['record']
    f.must('/api/records/invoices', {'customerId': kiosk['id'], 'reference': 'INV-K1', 'issueDate': f.day(5), 'total': '100.00',
                                     'dueDate': (f.today + timedelta(days=17)).isoformat()}, name='full: Kiosk invoice added')
    f.must('/api/records/coverage', {**body, 'customers': [kiosk['id']]}, role='owner', name='full: owner confirms Kiosk payments complete')
    exact, why = f.exact('INV-K1')
    ok('full: an unaccounted opening credit blocks the exact amount', exact is None and 'credit of AUD 50.00' in why, why[:140])
    credit = f.must('/api/records/payments', {'customerId': kiosk['id'], 'receivedDate': f.day(0), 'amount': '50.00', 'reference': 'Credit note CN-12',
                                              'kind': 'credit', 'inclusion': 'included'}, name='full: credit recorded, part of the opening balance')['record']
    f.must('/api/records/openingBalances/' + opening['id'], {'credits': 'recorded', 'reason': 'CN-12 is the only credit'}, name='full: every credit said to be recorded')
    f.must('/api/records/allocations', {'paymentId': credit['id'], 'allocations': [{'invoiceId': f.invoice('INV-K1')['id'], 'amount': '50.00'}]},
           name='full: credit applied to INV-K1')
    exact, why = f.exact('INV-K1')
    ok('full: with the credit applied, exactly AUD 50.00', exact and exact['amount']['minorUnits'] == '5000', why[:120])

    # A request through the agent, decided by the owner
    asked = (f.today + timedelta(days=21)).isoformat()
    r = f.request("Hi, it's Bayside Café. Could we pay INV-501 on " + natural(asked) + '? Our own customer paid us late.')
    facts = {x['key']: x for x in ((r.get('analysis') or {}).get('brief') or {}).get('facts', [])}
    ok('full: owner case prepared', r['status'] == 'awaiting_owner', (r['status'], (r.get('analysis') or {}).get('aiStatus')))
    ok('full: owner sees the exact amount as a calculation, overdue from complete records',
       facts.get('outstandingAmount', {}).get('kind') == 'calculation' and facts['outstandingAmount']['value']['minorUnits'] == '40000'
       and facts.get('daysOverdue', {}).get('value') == 2, {k: facts.get(k, {}).get('display') for k in ('outstandingAmount', 'daysOverdue')})
    items = {i['kind']: i['text'] for i in r['analysis']['brief']['openItems']}
    ok('full: brief explains the basis and keeps the customer balance apart', 'exact_outstanding' in items and 'not this invoice' in items.get('customer_balance', ''))
    done = f.decide(r, asked)
    ok('full: completed with a reply draft (not sent)', done['status'] == 'completed' and done['responseDraft']['deliveryStatus'] == 'not_sent')

    # A correction that changes nothing about this invoice (the other customer's credit), then records that change what it shows.
    # (Correcting a payment the bank export created would rightly block reverting that export: covered by unit tests.)
    fixed = f.must('/api/records/payments/' + credit['id'], {'reference': 'Credit note CN-12 (Kiosk)', 'reason': 'Clearer reference'},
                   name='full: credit corrected (versioned)')['record']
    ok('full: correction keeps the earlier version', fixed['version'] == 2 and fixed['history'][0]['values']['reference'] == 'Credit note CN-12')
    ok('full: an immaterial correction does not flag the decision', not site.reopen(done).get('flags'))
    stray = f.must('/api/records/payments', {'customerId': bayside['id'], 'receivedDate': f.day(10), 'amount': '25.00', 'reference': 'Cash at counter'},
                   name='full: a payment added inside the confirmed period')['record']
    flags = site.reopen(done).get('flags') or []
    ok('full: the decided case is flagged with the amount before and after', flags and flags[-1]['outstandingBefore'].startswith('exactly AUD 400.00')
       and flags[-1]['outstandingNow'].startswith('at most'), flags and (flags[-1]['outstandingBefore'], flags[-1]['outstandingNow']))
    f.must('/api/records/payments/' + stray['id'] + '/remove', {'reason': 'Entered twice'}, name='full: the stray payment removed')
    ok('full: the statement holds again and the amount is exact again', f.exact('INV-501')[0] is not None)

    # A pending case, left for the restart check
    pending = f.request('Kiosk Co here: could we pay INV-K1 on ' + natural((f.today + timedelta(days=30)).isoformat()) + ' instead?')
    ok('full: a second case waits for the owner', pending['status'] == 'awaiting_owner', pending['status'])

    # Revert the bank export: review first; the decision stays, the case is flagged
    status, error, _ = site.call('/api/imports/' + batch['id'] + '/revert', {'reason': 'Wrong bank account'}, 'staff', str(uuid.uuid4()))
    ok('full: revert asks for review when a decided case uses the invoice', status == 409 and error['error'] == 'REVIEW_REQUIRED' and done['id'] in error['impact']['review']['decidedCases'])
    f.must('/api/imports/' + batch['id'] + '/revert', {'reason': 'Wrong bank account', 'confirm': True}, name='full: payment list reverted after review')
    after = site.reopen(done)
    ok('full: the decision and its stored evidence are unchanged', after['decision'] == done['decision'] and after['analysis']['snapshot'] == done['analysis']['snapshot'])
    ok('full: the revert is visible on the decided case', after['flags'][-1]['outstandingNow'] in ('not recorded',) and len(after['flags']) >= 3, after['flags'][-1])
    exact, why = f.exact('INV-501')
    ok('full: after the revert nothing about INV-501 is called exact', exact is None and why, why[:120])
    records = f.records()
    STATE.write_text(json.dumps({'decided': done['id'], 'pending': pending['id'], 'pendingAnalysis': site.reopen(pending)['analysis']['id'],
                                 'payments': sorted(p['id'] for p in records['payments'] if p.get('status', 'active') == 'active'),
                                 'positions': records['positions'], 'flags': len(after['flags'])}))


def scenario_after_restart(site, state):
    saved = json.loads(STATE.read_text())
    records = site.call('/api/records', role='staff')[1]
    ok('restart: records and positions are as before the restart', records['positions'] == saved['positions'] and
       sorted(p['id'] for p in records['payments'] if p.get('status', 'active') == 'active') == saved['payments'])
    pending = site.reopen({'id': saved['pending']})
    ok('restart: the pending case still waits for the owner, with the same brief', pending['status'] == 'awaiting_owner' and pending['analysis']['id'] == saved['pendingAnalysis'],
       (pending['status'], pending['analysis']['id'][-6:]))
    decided = site.reopen({'id': saved['decided']})
    ok('restart: the decided case keeps its decision and its flags', decided['status'] == 'completed' and len(decided['flags']) == saved['flags'])
    status, result, _ = site.decide(pending, approved=(date.fromisoformat(site.call('/api/setup', role='owner')[1]['asOfDate']) + timedelta(days=30)).isoformat())
    ok('restart: the pending case can be decided after the restart', status == 201, result.get('outcome') or result.get('error'))


def scenario_fallback(site, state):
    settings(site, 'fallback', 'No-AI check (fictional)')
    f = Flow(site, 'fallback')
    customer = f.must('/api/records/customers', {'name': 'Harbour Kiosk'}, name='fallback: customer added')['record']
    f.must('/api/records/openingBalances', {'customerId': customer['id'], 'asOf': f.day(0), 'amount': '0.00', 'credits': 'none',
                                            'sourceLabel': 'Fictional'}, name='fallback: opening balance with no credits')
    invoice = f.must('/api/records/invoices', {'customerId': customer['id'], 'reference': 'DEMO-701', 'issueDate': f.day(2), 'total': '900.00',
                                               'dueDate': (f.today + timedelta(days=5)).isoformat()}, name='fallback: invoice added')['record']
    payment = f.must('/api/records/payments', {'customerId': customer['id'], 'receivedDate': f.day(8), 'amount': '300.00', 'reference': 'EFT 1'},
                     name='fallback: payment recorded')['record']
    f.must('/api/records/allocations', {'paymentId': payment['id'], 'allocations': [{'invoiceId': invoice['id'], 'amount': '300.00'}]}, name='fallback: allocated')
    f.must('/api/records/coverage', {'customers': [customer['id']], 'recordTypes': ['payments'], 'from': f.day(1), 'to': f.today.isoformat(),
                                     'sourceLabel': 'Fictional', 'confirm': True}, role='owner', name='fallback: completeness confirmed')
    r = f.request('Could we pay invoice DEMO-701 on ' + (f.today + timedelta(days=20)).isoformat() + ' instead?')
    a = r['analysis']
    facts = {x['key']: x for x in a['brief']['facts']}
    ok('fallback: model failure disclosed; case prepared by code', a['aiStatus'] == 'failed' and r['task']['mode'] == 'manual_fallback', a.get('failure'))
    ok('fallback: the same exact amount, from code', facts['outstandingAmount']['kind'] == 'calculation' and facts['outstandingAmount']['value']['minorUnits'] == '60000')
    ok('fallback: the basis is explained', any(i['kind'] == 'exact_outstanding' for i in a['brief']['openItems']))
    ok('fallback: decision still owner-only', site.decide(r, role='staff', approved=(f.today + timedelta(days=20)).isoformat())[0] == 403
       and site.decide(r, approved=(f.today + timedelta(days=20)).isoformat())[0] == 201)


def scenario_smoke(site, state):
    """The shared practice instance after a deploy. Adds one clearly labelled fictional customer; touches nothing else."""
    f = Flow(site, 'smoke')
    before = site.call('/api/records', role='staff')[1]
    ok('smoke: Records page data served', before['workspace'] == 'practice' and before['settings']['currency'] == 'AUD')
    run = datetime.now(timezone.utc).strftime('%m%d%H%M%S')   # a label per run, so the smoke can be repeated on the same database
    ref = 'RC' + run
    customer = setup_bayside(f, name='Release check café ' + run + ' (fictional)', ref=ref)
    credit = f.must('/api/records/payments', {'customerId': customer['id'], 'receivedDate': f.day(4), 'amount': '100.00', 'reference': 'Prepayment RC (fictional)',
                                              'kind': 'credit'}, name='smoke: a credit recorded')['record']
    payment = f.must('/api/records/payments', {'customerId': customer['id'], 'receivedDate': f.day(9), 'amount': '500.00', 'reference': 'EFT RC (fictional)'},
                     name='smoke: a payment recorded')['record']
    invoice = f.invoice(ref)
    f.must('/api/records/allocations', {'paymentId': credit['id'], 'allocations': [{'invoiceId': invoice['id'], 'amount': '100.00'}]}, name='smoke: credit applied')
    f.must('/api/records/allocations', {'paymentId': payment['id'], 'allocations': [{'invoiceId': invoice['id'], 'amount': '500.00'}]}, name='smoke: payment applied')
    f.must('/api/records/coverage', {'customers': [customer['id']], 'recordTypes': ['payments'], 'from': f.day(1), 'to': f.today.isoformat(),
                                     'sourceLabel': 'Release check (fictional)', 'confirm': True}, role='owner', name='smoke: completeness confirmed')
    exact, why = f.exact(ref)
    ok('smoke: exactly AUD 400.00 from complete records', exact and exact['amount']['minorUnits'] == '40000', why[:120])
    asked = (f.today + timedelta(days=21)).isoformat()
    r = f.request('Release check café ' + run + ' here (fictional). Could we pay ' + ref + ' on ' + natural(asked) + '?')
    facts = {x['key']: x for x in ((r.get('analysis') or {}).get('brief') or {}).get('facts', [])}
    ok('smoke: owner sees the exact amount', r['status'] == 'awaiting_owner' and facts.get('outstandingAmount', {}).get('kind') == 'calculation',
       (r['status'], facts.get('outstandingAmount', {}).get('display')))
    done = f.decide(r, asked)
    ok('smoke: decision completed with an unsent reply draft', done['status'] == 'completed' and done['responseDraft']['deliveryStatus'] == 'not_sent')
    after = site.call('/api/records', role='staff')[1]
    ok('smoke: the sample records are untouched', [i for i in after['invoices'] if i['id'] in {x['id'] for x in before['invoices']}] == before['invoices'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scenario', choices=['full', 'after-restart', 'fallback', 'smoke'])
    parser.add_argument('--base', default='https://nucleon.dracooz.top')
    args = parser.parse_args()
    site = Site(args.base)
    site.login()
    {'full': scenario_full, 'after-restart': scenario_after_restart, 'fallback': scenario_fallback, 'smoke': scenario_smoke}[args.scenario](site, None)
    print('RESULT', args.scenario, sum(results), '/', len(results))
    return 0 if all(results) else 1


if __name__ == '__main__':
    sys.exit(main() or 0)
