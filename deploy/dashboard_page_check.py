"""Browser check of the Owner's dashboard (#/dashboard) in a headless Chromium, on scratch records servers this script starts itself (deploy/delegation_check_server.py:
fictional data, a throwaway database, free loopback ports): the impact tiles equal GET /api/delegation/impact, a value that is null reads "no data yet" and never 0, the date and
policy-version filters, the loop strip equals GET /api/delegation/loop, outcomes by label as bars, "Observe outcomes now", the usage section, the fictional footnote, and Staff cannot open
the page. Standard library only (set CHROME_HEADLESS to a chrome-headless-shell binary).

    python3 deploy/dashboard_page_check.py      # prints PASS/FAIL per check; exit status 0 only if all pass
"""
import json, os, shutil, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from page_check_lib import Checks, Scratch, Page, IDS
import delegation_demo

tmp = tempfile.mkdtemp(prefix='dashboard-check-')
check = Checks()
E = F = None

# the tile keys and where each one's metric sits in the impact payload
def tiles_of(r):
    return {'cases': r['cases'], 'autonomousCoverage': r['autonomousCoverage'], 'escalationRate': r['escalationRate'], 'overridesCount': r['overrides']['count'], 'overridesRate': r['overrides']['rate'],
            'disagreements': r['disagreements']['count'], 'agreementRate': r['liveAgreement']['agreementRate'], 'agreementExplicit': r['liveAgreement']['explicit'], 'agreementTacit': r['liveAgreement']['tacit'],
            'evidenceRequests': r['evidenceRequests']['count'], 'evidenceAnswered': r['evidenceRequests']['answered'], 'evidenceTurnaround': r['evidenceRequests']['medianTurnaroundSeconds'],
            'timeToDecision': r['timeToDecisionSeconds']['median'], 'timeToDecisionP90': r['timeToDecisionSeconds']['p90'], 'ownerIntervention': r['ownerInterventionSeconds']['median'],
            'ownerInterventionCases': r['ownerInterventionSeconds']['cases'], 'timeSaved': r['timeSaved']}


def shown(p):
    return {t['key']: t for t in p.js("""[...document.querySelectorAll('[data-testid=tile]')].map(e => ({ key: e.dataset.tile, raw: e.dataset.raw, num: e.dataset.num, den: e.dataset.den, source: e.dataset.source,
      value: e.querySelector('[data-testid=tile-value]').innerText, frac: e.querySelector('[data-testid=tile-frac]').innerText, chip: e.querySelector('[data-testid=tile-source]').innerText, set: e.querySelector('[data-testid=tile-dataset]').innerText }))""")}


def tiles_equal(p, impact):
    got, want = shown(p), tiles_of(impact)
    bad = []
    for key, m in want.items():
        t = got.get(key)
        if not t: bad.append((key, 'missing')); continue
        v = json.loads(t['raw'])
        if v != m['value'] or t['source'] != m['source'] or (t['num'] or None) != (None if m['numerator'] is None else str(m['numerator'])) or (t['den'] or None) != (None if m['denominator'] is None else str(m['denominator'])):
            bad.append((key, t['raw'], m['value']))
    return not bad and set(got) == set(want), bad[:3]


try:
    # ================================================================ E. an empty practice: nothing to measure yet
    E = Scratch(tmp, 'e')
    p = Page(E)
    p.open('#/dashboard'); p.sign_in('staff')
    check('A1 Staff get "Page not found" at #/dashboard', p.wait("document.querySelector('#main h1')?.textContent === 'Page not found'") and not p.has('[data-testid=dashboard-page]'))
    check('A1 and the Owner-only endpoints are refused to Staff (impact, loop, usage)', all(E.api(x, None, E.cookie['staff'])[0] == 403 for x in ('/api/delegation/impact', '/api/delegation/loop', '/api/delegation/ui-summary')))
    p.sign_out()
    p.open('#/dashboard'); p.sign_in('owner')
    check('B1 the Owner opens the dashboard', p.wait("!!document.querySelector('[data-testid=dashboard-page]')") and p.text('#main h1') == 'Dashboard' and p.js("document.querySelector('header.top a[aria-current=page]')?.dataset.area") == 'dashboard')
    impact = E.api('/api/delegation/impact', None, E.cookie['owner'])[1]
    ok, bad = tiles_equal(p, impact)
    check('B1 every tile equals the impact endpoint: value, numerator, denominator and source', ok and p.count('[data-testid=tile]') == 17, bad)
    got = shown(p)
    nulls = [k for k, t in got.items() if t['raw'] == 'null']
    check('B1 a value the backend cannot establish reads "no data yet" and never 0 (rates, times)', len(nulls) >= 8 and all(got[k]['value'] == 'no data yet' for k in nulls if k != 'timeSaved'), [(k, got[k]['value']) for k in nulls if got[k]['value'] != 'no data yet'])
    check('B1 time saved says "not measured — set from PoV interviews" and is labelled an assumption', got['timeSaved']['value'] == 'not measured — set from PoV interviews' and got['timeSaved']['chip'] == 'assumption, not measured', got['timeSaved'])
    check('B1 each tile names where its number comes from: measured, derived or assumption, and the dataset', {t['chip'] for t in got.values()} == {'measured', 'derived', 'assumption, not measured'} and all(t['set'] == 'live cases' for t in got.values()), {t['chip'] for t in got.values()})
    check('B1 counts are real zeros ("0"), because a count of nothing is zero', got['cases']['value'] == '0' and got['cases']['frac'] == '0 of 0' or got['cases']['value'] == '0', got['cases'])
    check('B2 the loop strip has the six stages in order, all zero, and no case is counted from the fictional memory', p.js("[...document.querySelectorAll('[data-testid=loop-stage]')].map(e => e.dataset.stage + ':' + e.dataset.count).join()") ==
          'request:0,evidence:0,evaluation:0,decision:0,feedback:0,outcome:0', p.text('[data-testid=loop-strip]'))
    check('B2 outcomes say none has been observed yet; usage says nothing recorded yet or lists the page itself', p.has('[data-testid=outcomes-none]'))
    check('B3 the footnote says fictional cases are excluded', 'Fictional cases are excluded' in p.text('[data-testid=fictional-note]'), p.text('[data-testid=fictional-note]'))
    heads = p.js("[...document.querySelectorAll('[data-testid=exposure-table] thead th')].map(e => e.textContent).join('|')")
    check('B4 the owed table uses statement words and says what total at risk is', heads == 'Customer|Outstanding balance|Of which overdue|Trial credit in force|Total at risk|Limit|Open cases'
          and 'Total at risk = outstanding balance + trial credit in force' in p.text('[data-testid=exposure-note]') and p.text('#d-exp') == 'What customers owe now', heads)
    p.sign_out(); p.b.close(); E.stop(); E = None

    # ================================================================ F. a practice with decisions at several stages
    F = Scratch(tmp, 'f')
    bay = F.resolve({'kind': 'extension', 'customerId': IDS['bayview'], 'invoiceReference': 'DEMO-301', 'requestedDueDate': '2026-11-10'}, 'f-bay')
    north = F.resolve({'kind': 'trial_credit', 'customerId': IDS['northside'], 'orderAmount': '800.00', 'termsDays': 14}, 'f-north')
    extra = F.approved_trial('Pinecrest Kiosk')
    harb = F.resolve({'kind': 'trial_credit', 'customerId': IDS['harbourline'], 'orderAmount': '5000.00', 'termsDays': 14}, 'f-harb')
    city = F.resolve({'kind': 'extension', 'customerId': IDS['cityside'], 'invoiceReference': 'DEMO-410', 'days': 14}, 'f-city')
    asked_cid, asked = F.asked_trial('Waiting Cafe')
    ver = lambda c: F.case(c)['version']
    F.owner('/api/decision-cases/%s/decide' % harb['caseId'], {'outcome': 'decline', 'reason': 'Too large (dashboard check).', 'version': ver(harb['caseId'])})
    F.owner('/api/decision-cases/%s/feedback' % bay['caseId'], {'verdict': 'agree', 'reason': 'Fine.', 'version': ver(bay['caseId'])}, 'fb1')
    F.owner('/api/decision-cases/%s/feedback' % north['caseId'], {'verdict': 'disagree', 'override': True, 'reason': 'Revoke.', 'version': ver(north['caseId'])}, 'fb2')
    F.owner('/api/decision-cases/%s/viewed' % extra, {})
    F.owner('/api/decision-cases/%s/feedback' % extra, {'verdict': 'agree', 'reason': 'Fine too.', 'version': ver(extra)}, 'fb3')
    observed = F.owner('/api/delegation/observe-outcomes', {}, 'obs0')[1]
    # a new policy version, and one more case under it
    pol = F.api('/api/delegation/policy', None, F.cookie['owner'])[1]
    F.owner('/api/delegation/policy', {**delegation_demo.DEMO_POLICY, 'note': 'a second version', 'expectedVersion': pol['version']}, method='PUT')
    F.resolve({'kind': 'extension', 'customerId': IDS['riverside'], 'invoiceReference': 'DEMO-505', 'days': 10}, 'f-river')

    q = Page(F)
    q.open('#/dashboard'); q.sign_in('owner'); q.wait("!!document.querySelector('[data-testid=dashboard-page]')")
    impact = F.api('/api/delegation/impact', None, F.cookie['owner'])[1]
    ok, bad = tiles_equal(q, impact)
    check('C1 with data, every tile still equals the impact endpoint', ok, bad)
    got = shown(q)
    check('C1 a rate shows as a percentage of numerator over denominator (autonomous coverage)', got['autonomousCoverage']['frac'] == '%d of %d' % (impact['autonomousCoverage']['numerator'], impact['autonomousCoverage']['denominator']) and
          got['autonomousCoverage']['value'].endswith('%') and abs(float(got['autonomousCoverage']['value'][:-1]) - impact['autonomousCoverage']['value'] * 100) < 0.06, got['autonomousCoverage'])
    check('C1 the tiles that are still null say "no data yet" and none of them shows 0', all(t['value'] == 'no data yet' for t in got.values() if t['raw'] == 'null' and t['key'] != 'timeSaved') and not any(t['value'] in ('0', '0%') for t in got.values() if t['raw'] == 'null'),
          [(k, t['value']) for k, t in got.items() if t['raw'] == 'null'])
    check('C1 the Owner\'s own time on a case is measured once the Review page has posted a view (the view above)', got['ownerIntervention']['raw'] != 'null' and got['ownerIntervention']['value'] != 'no data yet', got['ownerIntervention'])
    loop = F.api('/api/delegation/loop', None, F.cookie['owner'])[1]
    strip = q.js("Object.fromEntries([...document.querySelectorAll('[data-testid=loop-stage]')].map(e => [e.dataset.stage, Number(e.dataset.count)]))")
    check('C2 the loop strip equals the backend\'s counts', strip == {s['stage']: s['count'] for s in loop['stages']}, strip)
    check('C2 and they are what happened: 1 waiting for information, 2 with the Owner, 1 declined by the Owner (decision), 1 overridden (feedback), 2 agreed and observed (outcome)',
          strip == {'request': 0, 'evidence': 1, 'evaluation': 2, 'decision': 1, 'feedback': 1, 'outcome': 2}, strip)
    check('C2 the six stages are named in order', q.js("[...document.querySelectorAll('[data-testid=loop-stage] .loop-name')].map(e => e.innerText).join()") == 'Request,Evidence,Evaluation,Decision,Owner feedback,Outcome')
    rows = q.js("[...document.querySelectorAll('[data-testid=outcome-row]')].map(e => [e.dataset.label, Number(e.dataset.count), e.querySelector('.bar').style.width])")
    by = {k: v['value'] for k, v in impact['outcomes']['byLabel'].items()}
    check('C3 outcomes by label are bars whose counts equal the endpoint', {r[0]: r[1] for r in rows} == by and sum(by.values()) >= 1, rows)
    total = sum(by.values())
    check('C3 each bar\'s width is its share of the observed total (set from the script: the page allows no inline style)', all(abs(float(r[2][:-1]) - 100 * r[1] / total) < 0.1 for r in rows if r[2]) and any(r[2] not in ('', '0%') for r in rows), [r[2] for r in rows])
    # filters
    q.fill('#df-from', '2999-01-01'); q.click('[data-testid=apply-filter]'); q.wait("document.querySelector('[data-tile=cases]')?.dataset.raw === '0'")
    filt = F.api('/api/delegation/impact?from=2999-01-01', None, F.cookie['owner'])[1]
    ok, bad = tiles_equal(q, filt)
    check('D1 a from-date filter reloads the tiles and they equal the endpoint with the same filter (no cases: counts 0, rates "no data yet")', ok and shown(q)['cases']['raw'] == '0' and shown(q)['autonomousCoverage']['value'] == 'no data yet', bad)
    q.fill('#df-from', ''); q.fill('#df-to', '2000-01-01'); q.click('[data-testid=apply-filter]'); q.wait("document.querySelector('[data-tile=cases]')?.dataset.raw === '0'")
    check('D1 a to-date filter too', tiles_equal(q, F.api('/api/delegation/impact?to=2000-01-01', None, F.cookie['owner'])[1])[0])
    q.fill('#df-to', ''); q.fill('#df-from', '2026-01-01'); q.js("document.querySelector('#df-version').value = '1'; document.querySelector('#df-version').dispatchEvent(new Event('input', { bubbles: true })); true")
    q.click('[data-testid=apply-filter]'); q.wait("document.querySelector('[data-tile=cases]')?.dataset.raw !== '0'")
    one = F.api('/api/delegation/impact?from=2026-01-01&policyVersion=1', None, F.cookie['owner'])[1]
    ok, bad = tiles_equal(q, one)
    check('D2 a policy-version filter (with a from-date) equals the endpoint with the same query, and counts fewer cases than all', ok and one['cases']['value'] < impact['cases']['value'], (bad, one['cases']['value'], impact['cases']['value']))
    check('D2 the version choices are the saved versions', q.js("[...document.querySelectorAll('#df-version option')].map(o => o.value).join()") == ',2,1', q.js("[...document.querySelectorAll('#df-version option')].map(o => o.value).join()"))
    q.fill('#df-from', '2026-12-31'); q.fill('#df-to', '2026-01-01'); q.click('[data-testid=apply-filter]')
    check('D3 an impossible range is refused by the backend and the page says so, keeping what was shown', q.wait("!!document.querySelector('[data-testid=notice]')") and 'from is after to' in q.text('[data-testid=notice]'), q.text('[data-testid=notice]'))
    q.fill('#df-from', ''); q.fill('#df-to', ''); q.js("document.querySelector('#df-version').value = ''; document.querySelector('#df-version').dispatchEvent(new Event('input', { bubbles: true })); true"); q.click('[data-testid=apply-filter]')
    q.wait("!document.querySelector('[data-testid=notice]')")
    # observe now
    F.resolve({'kind': 'extension', 'customerId': IDS['riverside'], 'invoiceReference': 'DEMO-505', 'days': 10}, 'f-river')   # replay: nothing new
    before = q.js("Number(document.querySelector('[data-stage=outcome]').dataset.count)")
    q.click('[data-testid=observe-outcomes]')
    check('E1 "Observe outcomes now" shows the counts the backend returned', q.wait("!!document.querySelector('[data-testid=observed-result]')") and ('Observed %d' % F.owner('/api/delegation/observe-outcomes', {}, 'obs-again')[1]['observed']) in q.text('[data-testid=observed-result]'), q.text('[data-testid=observed-result]'))
    check('E1 and they are the counts: observed, new or changed, unchanged (a second run changes nothing)', 'unchanged' in q.text('[data-testid=observed-result]') and observed['observed'] >= 1, q.text('[data-testid=observed-result]'))
    # usage
    q.js('flushTrack(); true'); time.sleep(0.5)
    q.go('#/'); q.go('#/dashboard'); q.wait("!!document.querySelector('[data-testid=dashboard-page]')"); time.sleep(0.3)
    q.js('flushTrack(); true'); time.sleep(0.5)
    q.go('#/review'); q.go('#/dashboard'); q.wait("!!document.querySelector('[data-testid=dashboard-page]')"); time.sleep(0.5)
    summary = F.api('/api/delegation/ui-summary', None, F.cookie['owner'])[1]
    check('F1 the Usage section lists the pages visited with visits and median time on the page, from the backend\'s summary', q.has('[data-testid=usage-table]') and q.count('[data-testid=usage-row]') == len(summary['pages']) and
          'dashboard' in q.text('[data-testid=usage-table]'), q.text('[data-testid=usage-table]')[:200].replace('\n', ' | '))
    check('F1 a median time not yet reported reads "no data yet", and the section says where the data is kept', 'no data yet' in q.text('[data-testid=usage-table]') or all(x['medianDwellSeconds'] is not None for x in summary['pages']) and 'stored on this machine only' in q.text('[data-testid=usage-decisions]'), q.text('[data-testid=usage-decisions]')[-120:])
    # the page refreshes itself and keeps the filter being typed
    q.fill('#df-from', '2026-02-02'); q.js("window.__n0 = document.querySelector('[data-testid=dashboard-page]'); window.__t0 = Date.now(); true")
    F.asked_trial('Another Cafe')
    arrived = q.wait("window.__n0 !== document.querySelector('[data-testid=dashboard-page]')", 25)
    check('G1 the dashboard reads itself again within 25 s and keeps the filter being typed', arrived and q.js("document.querySelector('#df-from').value") == '2026-02-02', '%.1f s' % (q.js('(Date.now() - window.__t0) / 1000') or 0))
    check('G1 the loop strip followed (a second case waiting for information)', q.js("Number(document.querySelector('[data-stage=evidence]').dataset.count)") == 2)
    # layout
    q.phone(True); q.fill('#df-from', ''); time.sleep(0.4)
    check('L1 the dashboard with data has no horizontal scroll at 390 px', q.no_hscroll(), q.width_info())
    check('L1 the six loop stages stay in one row at 390 px', q.js("new Set([...document.querySelectorAll('[data-testid=loop-stage]')].map(e => Math.round(e.getBoundingClientRect().top))).size") == 1)
    q.phone(False)
    check('Z no page error was thrown (the page uses no inline style: the CSP would report it)', not q.b.errors(), q.b.errors()[:2])
    q.b.close()
finally:
    for s_ in (E, F):
        if s_:
            try: s_.stop()
            except Exception: pass
    shutil.rmtree(tmp, ignore_errors=True)
sys.exit(check.finish())
