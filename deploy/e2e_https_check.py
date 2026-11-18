"""End-to-end checks through the deployed HTTPS URL (run on the server; reads codes from the private log).

Each scenario expects a fresh isolated database:   nucleonctl isolate <name> [fault]
    python3 deploy/e2e_https_check.py <scenario> [--base https://nucleon.dracooz.top] [--state file]

Scenarios: approve, stale, change-date, decline, clarify, restart (after approve + `nucleonctl restart`),
fallback-unavailable (isolate ... unreachable-model), fallback-invalid (isolate ... truncated-model),
legacy (isolate on a copy of a database written by extension-v0.2; pass --db with that copy's path),
console (demo reset/restore and its permissions).
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

LOG = Path.home() / 'Library/Logs/nucleon/service.log'
CONFIG = Path.home() / 'srv/nucleon/config/service.json'   # the active config; the console no longer reports server paths
NATURAL = "Hi, it's Harbour Demo Supplies. Could we pay invoice DEMO-101 on Friday 30 October instead? We're still waiting on a payment from one of our own customers."
ISO = 'Could we pay invoice DEMO-101 on 2026-10-30 instead? We are waiting for a customer receipt.'
results = []


def ok(name, condition, detail=''):
    results.append(bool(condition))
    print(('PASS ' if condition else 'FAIL ') + name.ljust(58) + ' ' + str(detail)[:160], flush=True)
    return condition


class Site:
    def __init__(self, base):
        self.base, self.origin, self.cookies = base.rstrip('/'), base.rstrip('/'), {}

    def codes(self):
        text = LOG.read_text()
        latest = text[text.rfind(' URL: http'):]   # codes printed by the most recent start only
        return {m.group(1).lower(): m.group(2) for m in re.finditer(r'^(STAFF|OWNER|OPERATOR) access code: (\S+)$', latest, re.M)}

    def call(self, path, body=None, role=None, key=None, origin=True, cookie=None):
        headers = {'User-Agent': 'nucleon-e2e'}
        if body is not None:
            headers['Content-Type'] = 'application/json'
            if origin:
                headers['Origin'] = self.origin if origin is True else origin
        if role or cookie:
            headers['Cookie'] = cookie or self.cookies[role]
        if key:
            headers['Idempotency-Key'] = key
        req = Request(self.base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
        try:
            response = urlopen(req, timeout=60)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.loads(response.read()), response.headers

    def login(self):
        for role, code in self.codes().items():
            status, actor, headers = self.call('/api/demo/login', {'accessCode': code})
            ok('login ' + role + ' via HTTPS', status == 200 and actor['role'] == role, actor.get('role'))
            cookie = headers['Set-Cookie']
            ok('session cookie is HttpOnly, SameSite=Strict, Secure (' + role + ')', all(x in cookie for x in ('HttpOnly', 'SameSite=Strict', 'Secure')))
            self.cookies[role] = cookie.split(';')[0]

    def submit(self, message, key=None):
        status, r, _ = self.call('/api/requests', {'messageText': message}, 'staff', key or str(uuid.uuid4()))
        ok('staff submission accepted (202)', status == 202, r.get('status'))
        return self.settle(r['id'])

    def settle(self, request_id, timeout=400):
        started, deadline = time.monotonic(), time.monotonic() + timeout
        while time.monotonic() < deadline:
            r = self.call('/api/requests/' + request_id, role='staff')[1]
            if r['status'] not in ('received', 'analysing'):
                r['_wait'] = round(time.monotonic() - started, 1)
                return r
            time.sleep(0.7)
        raise TimeoutError(request_id)

    def decide(self, r, outcome='approve', approved='2026-10-30', role='owner', key=None, extra=None):
        body = {'expectedRequestVersion': r['version'], 'analysisId': r['analysis']['id'],
                'evidenceVersion': r['analysis']['snapshot']['evidenceVersion'], 'outcome': outcome,
                'approvedDueDate': approved, 'reason': 'E2E check: this invoice only.', **(extra or {})}
        return self.call('/api/requests/' + r['id'] + '/decisions', body, role, key or str(uuid.uuid4()))

    def reopen(self, r):
        return self.call('/api/requests/' + r['id'], role='staff')[1]


def live_case(site, r, label, ext=10, overdue=0, requested='2026-10-30'):
    a = r['analysis']
    facts = a['snapshot'].get('facts') or {}
    run_events = [e for e in r['history'] if e['data'].get('runId') == a['runId']]
    tools = [e['data']['tool'] for e in run_events if e['kind'] == 'tool.executed']
    calls = [e for e in run_events if e['kind'] == 'model.call']
    ok(label + ': live model run (aiStatus=live)', a['aiStatus'] == 'live', (a.get('failure') or '') and json.dumps(a['failure']))
    ok(label + ': model identity recorded', a.get('modelId') and (a.get('model') or {}).get('serving', {}).get('arch'),
       str(a.get('modelId')) + ' / ' + str((a.get('model') or {}).get('serving')))
    ok(label + ': model-selected tools executed', tools[:4] == ['findCustomers', 'getInvoiceFacts', 'getConfirmedKnowledge', 'calculateExtension'] and tools[-1] == 'prepareApprovalTask', tools)
    ok(label + ': code facts AUD 1,250.00, ' + str(ext) + '-day extension, ' + str(overdue) + ' overdue',
       facts.get('invoiceOutstanding', {}).get('minorUnits') == '125000' and facts.get('extensionDays') == ext and facts.get('daysOverdue') == overdue and facts.get('requestedDueDate') == requested,
       {k: facts.get(k) for k in ('currentEffectiveDueDate', 'requestedDueDate', 'extensionDays', 'daysOverdue')})
    brief = a['brief']
    typed = {f['key']: f for f in brief['facts']}
    ok(label + ': structured brief, no stored suggestion', brief['format'] in ('brief-v2', 'brief-v3') and brief['suggestedOption'] is None and brief['summaryBy'] == 'application_code')
    ok(label + ': typed facts bound to sources', typed['extensionDays']['value'] == ext and typed['daysOverdue']['value'] == overdue and
       typed['outstandingAmount']['source']['field'] == 'outstandingAmount' and typed['extensionDays']['inputs'] == ['requestedDueDate', 'currentEffectiveDueDate'])
    ok(label + ': customer statements are verbatim and unverified', all(s['attribution'] == 'customer' and not s['verified'] and
       re.sub('[^a-z0-9]', '', s['quote'].lower()) in re.sub('[^a-z0-9]', '', r['intake']['text'].lower()) for s in brief['customerStatements']),
       [s['quote'] for s in brief['customerStatements']])
    print('      latency: wait ' + str(r['_wait']) + ' s; model calls ' + ', '.join(c['data']['task'] + ' ' + str(c['data'].get('latencyMs')) + 'ms' for c in calls) +
          '; prompt ' + str(a['promptVersion']), flush=True)


def scenario_approve(site, state):
    r = site.submit(NATURAL)
    ok('natural-language request reaches owner task', r['status'] == 'awaiting_owner', r['status'])
    live_case(site, r, 'approve')
    again = site.call('/api/requests', {'messageText': NATURAL}, 'staff', 'dup-key-1')[1]
    dup = site.call('/api/requests', {'messageText': NATURAL}, 'staff', 'dup-key-1')[1]
    ok('duplicate submission with same key returns same request', again['id'] == dup['id'])
    ok('same key with different payload rejected (409)', site.call('/api/requests', {'messageText': NATURAL + ' x'}, 'staff', 'dup-key-1')[0] == 409)
    site.settle(again['id'])
    status, body, _ = site.call('/api/requests/' + r['id'] + '/reanalyse', {'expectedRequestVersion': r['version']}, 'staff', str(uuid.uuid4()), origin='https://evil.example')
    ok('cross-origin write rejected (403)', status == 403, body.get('error'))
    status, body, _ = site.call('/api/requests', {'messageText': ISO}, 'staff', str(uuid.uuid4()), origin='http://nucleon.dracooz.top')
    ok('http:// origin variant rejected (403)', status == 403)
    status, body, _ = site.decide(r, role='staff', extra={'role': 'owner', 'decidedBy': 'owner_demo'})
    ok('staff cannot spoof owner decision (403)', status == 403, body.get('error'))
    status, body, _ = site.call('/api/requests/' + r['id'], cookie='nucleon_session=forged')
    ok('forged session cannot read (401)', status == 401)
    key = str(uuid.uuid4())
    first = site.decide(r, key=key)
    second = site.decide(r, key=key)
    ok('owner approval committed (201)', first[0] == 201, first[1].get('outcome'))
    ok('duplicate decision returns same decision', first[1].get('id') == second[1].get('id'))
    done = site.reopen(r)
    commits = [e for e in done['history'] if e['kind'] == 'decision.committed']
    ok('exactly one committed decision', len(commits) == 1)
    ok('reply draft matches approved date, not sent', done['status'] == 'completed' and 'Friday 30 October 2026' in done['responseDraft']['text'] and done['responseDraft']['deliveryStatus'] == 'not_sent', done['responseDraft']['text'])
    ok('decision carries no model suggestion', 'aiSuggestion' not in done['decision'] and 'historicalAiSuggestion' not in done['decision'])
    status, health, _ = site.call('/api/model-status', role='staff')
    ok('model-status endpoint reports the loaded model', status == 200 and health['state'] == 'ready', (health.get('state'), (health.get('serving') or {}).get('arch')))
    ok('model-status needs a session (401)', site.call('/api/model-status', cookie='nucleon_session=forged')[0] == 401)
    later = site.submit(NATURAL)
    ok('approved extension changes later effective due date', later['analysis']['snapshot']['currentEffectiveDueDate'] == '2026-10-30' and later['status'] == 'needs_information', later['status'])
    state.write_text(json.dumps({'ids': [r['id'], later['id']], 'snapshot': {x: site.reopen({'id': x}) for x in (r['id'], later['id'])},
                                 'cookie': site.cookies['staff']}))


def scenario_restart(site, state):
    saved = json.loads(state.read_text())
    status, _, _ = site.call('/api/requests/' + saved['ids'][0], cookie=saved['cookie'])
    ok('old session rejected after restart (401)', status == 401)
    for request_id in saved['ids']:
        now = site.reopen({'id': request_id})
        before = saved['snapshot'][request_id]
        ok('record survives restart: ' + request_id[-6:], now['decision'] == before['decision'] and now['responseDraft'] == before['responseDraft'] and now['history'] == before['history'], now['status'])


def scenario_stale(site, state):
    a, b = site.submit(ISO), site.submit(ISO)
    ok('two pending owner tasks', a['status'] == b['status'] == 'awaiting_owner', (a['status'], b['status']))
    ok('first approval committed', site.decide(a)[0] == 201)
    status, body, _ = site.decide(b)
    ok('second owner task now stale (409 STALE_EVIDENCE)', status == 409 and body['error'] == 'STALE_EVIDENCE', body.get('error'))
    status, body, _ = site.call('/api/requests/' + b['id'] + '/reanalyse', {'expectedRequestVersion': 0}, 'staff', str(uuid.uuid4()))
    ok('stale request version rejected (409)', status == 409, body.get('error'))
    site.call('/api/requests/' + b['id'] + '/reanalyse', {'expectedRequestVersion': b['version']}, 'staff', str(uuid.uuid4()))
    refreshed = site.settle(b['id'])
    ok('reanalysis uses new effective due date and asks for later date', refreshed['status'] == 'needs_information' and refreshed['analysis']['snapshot']['currentEffectiveDueDate'] == '2026-10-30', refreshed['status'])


def scenario_change_date(site, state):
    r = site.submit(NATURAL)
    live_case(site, r, 'change-date')
    ok('owner approves a different date (201)', site.decide(r, approved='2026-11-03')[0] == 201)
    done = site.reopen(r)
    ok('decision keeps requested and approved dates distinct', done['requestedDueDate'] == '2026-10-30' and done['decision']['approvedDueDate'] == '2026-11-03')
    ok('draft states owner date only, written out', 'Tuesday 3 November 2026' in done['responseDraft']['text'] and 'October' not in done['responseDraft']['text'], done['responseDraft']['text'])


def scenario_decline(site, state):
    r = site.submit(NATURAL)
    live_case(site, r, 'decline')
    ok('owner declines (201)', site.decide(r, 'decline', None)[0] == 201)
    done = site.reopen(r)
    ok('declined draft, no approved date, not sent', 'declined' in done['responseDraft']['text'] and done['decision']['approvedDueDate'] is None and done['responseDraft']['deliveryStatus'] == 'not_sent', done['responseDraft']['text'])


def scenario_clarify(site, state):
    r = site.submit('Could we pay invoice DEMO-101 later?')
    ok('missing date creates clarification (live)', r['status'] == 'needs_information' and r['analysis']['aiStatus'] == 'live' and 'requestedDueDate' in [m['field'] for m in r['task']['missingFields']], r['task'] and r['task'].get('question'))
    path = '/api/requests/' + r['id'] + '/clarifications/' + r['task']['id'] + '/answers'
    status, err, _ = site.call(path, {'expectedRequestVersion': r['version'], 'answers': [{'field': 'requestedDueDate', 'value': '2026-10-19'}]}, 'staff', str(uuid.uuid4()))
    ok('too-early date gets a field-specific error (422)', status == 422 and err.get('field') == 'requestedDueDate', err.get('message'))
    ok('rejected answer leaves the task unchanged', site.reopen(r)['status'] == 'needs_information' and site.reopen(r)['version'] == r['version'])
    status, _, _ = site.call(path, {'expectedRequestVersion': r['version'], 'answers': [{'field': 'requestedDueDate', 'value': '2026-10-30'}]}, 'staff', str(uuid.uuid4()))
    ok('staff answer accepted (202)', status == 202)
    resumed = site.settle(r['id'])
    ok('continuation reaches owner task with new version', resumed['status'] == 'awaiting_owner' and resumed['version'] == 2, resumed['status'])
    live_case(site, resumed, 'clarify-continuation')
    ok('staff-reported date disclosed in brief', any(i['kind'] == 'staff_reported' for i in resumed['analysis']['brief']['openItems']))
    ambiguous = site.submit('Can we push DEMO-101 back to next Friday?')
    ok('ambiguous "next Friday" asks instead of guessing', ambiguous['status'] == 'needs_information' and ambiguous['requestedDueDate'] is None, ambiguous['task'] and ambiguous['task'].get('question'))


def scenario_fallback(site, state, kind):
    r = site.submit(ISO)
    a = r['analysis']
    ok('model failure disclosed (aiStatus=failed, ' + kind + ')', a['aiStatus'] == 'failed' and a['failure']['kind'] == kind, a.get('failure'))
    ok('manual fallback owner task, no AI recommendation', r['task']['mode'] == 'manual_fallback' and a['brief']['suggestedOption'] is None and a['modelId'] is None)
    ok('fallback brief uses the structured format and says AI failed', a['brief']['format'] in ('brief-v2', 'brief-v3') and a['brief']['openItems'][0]['kind'] == 'ai_failed')
    ok('fallback decision still owner-only and saved', site.decide(r, role='staff')[0] == 403 and site.decide(r)[0] == 201)
    ok('template draft after fallback', site.reopen(r)['responseDraft']['generation'] == 'template')


def scenario_legacy(site, state, db):
    rows = lambda: {rid: data for rid, data in sqlite3.connect('file:' + db + '?mode=ro', uri=True).execute('SELECT id, data FROM requests')}
    before = rows()
    views = [site.reopen({'id': rid}) for rid in before]
    legacy = [v for v in views if (v.get('analysis') or {}).get('brief') and v['analysis']['brief']['format'] == 'brief-v1-legacy']
    ok('legacy database opens; every record readable', len(views) == len(before) and all('status' in v for v in views), str(len(views)) + ' records')
    ok('legacy briefs labelled, not presented as checked', legacy and all('not for meaning' in v['analysis']['brief']['legacyNotice'] for v in legacy), str(len(legacy)) + ' legacy briefs')
    ok('no legacy brief exposes a current suggestion', all(v['analysis']['brief']['suggestedOption'] is None for v in legacy))
    hist = [v['analysis']['brief']['historicalSuggestion'] for v in legacy if 'historicalSuggestion' in v['analysis']['brief']]
    ok('historical suggestions kept with provenance', hist and all(h['status'] == 'historical_unvalidated' and h['origin'] == 'model_suggestion' for h in hist), str(len(hist)) + ' kept')
    decided = [v['decision'] for v in views if v.get('decision')]
    ok('legacy decisions keep owner outcome; old suggestion marked historical', decided and all('aiSuggestion' not in d and d['outcome'] in ('approve', 'decline') for d in decided) and
       all(d['historicalAiSuggestion']['status'] == 'historical_unvalidated' for d in decided if 'historicalAiSuggestion' in d))
    ok('reading did not rewrite stored records', rows() == before)
    pending = [v for v in legacy if v['status'] == 'awaiting_owner']
    if pending:
        p = pending[0]
        site.call('/api/requests/' + p['id'] + '/reanalyse', {'expectedRequestVersion': p['version']}, 'staff', str(uuid.uuid4()))
        fresh = site.settle(p['id'])
        ok('legacy owner task can be prepared again in the structured format', fresh['analysis']['brief'] and fresh['analysis']['brief']['format'] in ('brief-v2', 'brief-v3') or fresh['status'] == 'needs_information',
           (fresh['status'], fresh['analysis']['aiStatus']))


def scenario_console(site, state):
    ok('staff cannot open the demo console (403)', site.call('/api/demo/console', role='staff')[0] == 403)
    ok('owner cannot reset (403)', site.call('/api/demo/reset', {}, 'owner')[0] == 403)
    ok('demo console code cannot submit cases (403)', site.call('/api/requests', {'messageText': ISO}, 'operator', str(uuid.uuid4()))[0] == 403)
    r = site.submit(NATURAL)
    ok('owner approval before reset', site.decide(r)[0] == 201)
    status, reset, _ = site.call('/api/demo/reset', {}, 'operator')
    ok('reset clears every case and reports the backup', status == 200 and reset['reset'] and reset['console']['cases'] == 0 and reset['backup'], reset.get('backup'))
    backup = Path(json.loads(CONFIG.read_text())['demo']['backupDir']).expanduser() / reset['backup']
    ok('backup file exists and is private', backup.is_file() and backup.stat().st_mode & 0o777 == 0o600 and
       sqlite3.connect(backup).execute('SELECT COUNT(*) FROM requests').fetchone()[0] == 1)
    ok('cleared case is gone (404)', site.call('/api/requests/' + r['id'], role='staff')[0] == 404)
    ok('sign-ins survive the reset', site.call('/api/session', role='owner')[1]['authenticated'])
    status, again, _ = site.call('/api/demo/reset', {}, 'operator')
    ok('second reset on clean data changes nothing', status == 200 and not again['reset'] and again['backup'] is None)
    fresh = site.submit(NATURAL)
    live_case(site, fresh, 'after reset')   # DEMO-101 is due 20 Oct again, so the extension is 10 days
    status, restored, _ = site.call('/api/demo/restore', {'backup': reset['backup']}, 'operator')
    ok('restore brings the reset case back', status == 200 and site.reopen(r)['status'] == 'completed', restored.get('restored'))
    ok('restore saved the replaced data first', bool(restored.get('backup')), restored.get('backup'))
    ok('unknown backup names are refused (404)', site.call('/api/demo/restore', {'backup': '../nucleon.sqlite3'}, 'operator')[0] == 404)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scenario')
    parser.add_argument('--base', default='https://nucleon.dracooz.top')
    parser.add_argument('--state', default=str(Path.home() / 'srv/nucleon/reports/e2e-state.json'))
    parser.add_argument('--db', help='database file of the isolated service (legacy scenario)')
    args = parser.parse_args()
    site, state = Site(args.base), Path(args.state)
    print('E2E through ' + args.base + ' | scenario ' + args.scenario, flush=True)
    site.login()
    {'approve': scenario_approve, 'restart': scenario_restart, 'stale': scenario_stale, 'change-date': scenario_change_date,
     'decline': scenario_decline, 'clarify': scenario_clarify, 'console': scenario_console, 'legacy': lambda s, st: scenario_legacy(s, st, args.db),
     'fallback-unavailable': lambda s, st: scenario_fallback(s, st, 'unavailable'),
     'fallback-invalid': lambda s, st: scenario_fallback(s, st, 'invalid_output')}[args.scenario](site, state)
    print('RESULT ' + args.scenario + ': ' + str(sum(results)) + '/' + str(len(results)) + ' checks passed', flush=True)
    return 0 if all(results) else 1


if __name__ == '__main__':
    sys.exit(main())
