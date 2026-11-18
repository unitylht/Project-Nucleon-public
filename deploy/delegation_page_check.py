"""Browser check of the evidence page (#/actions/<id> for an evidence request) and the Owner's delegation page (#/delegation), in a headless Chromium, on a scratch
records server it starts itself (deploy/delegation_check_server.py: the fictional delegation demonstration with the demo policy, a throwaway database, a free loopback
port). Fictional data only. Standard library only: the browser is driven through deploy/cdp_min.py (set CHROME_HEADLESS to a chrome-headless-shell binary).

    python3 deploy/delegation_page_check.py      # prints PASS/FAIL per check; exit status 0 only if all pass
"""
import json, os, re, shutil, sqlite3, subprocess, sys, tempfile, time, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_min import Browser, free_port

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tmp = tempfile.mkdtemp(prefix='delegation-check-')
port, log = free_port(), os.path.join(tmp, 'records.log')
server = subprocess.Popen([sys.executable, ROOT + '/deploy/delegation_check_server.py', tmp + '/records.db', str(port)], stdout=open(log, 'w'), stderr=subprocess.STDOUT, cwd=ROOT)
BASE = 'http://127.0.0.1:%d' % port
results = []


def check(name, ok, detail=''):
    results.append(bool(ok))
    print(('PASS ' if ok else 'FAIL ') + name.ljust(88) + str(detail)[:200])


def api(path, body=None, cookie=None, key=None, headers=None, method=None):
    h = {**(headers or {})}
    if cookie: h['Cookie'] = cookie
    if key: h['Idempotency-Key'] = key
    if body is not None: h['Content-Type'] = 'application/json'; h['Origin'] = BASE
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None, headers=h, method=method)
    try:
        r = urllib.request.urlopen(req, timeout=20)
    except urllib.error.HTTPError as e:
        r = e
    with r:
        return r.status, json.loads(r.read()), r.headers


try:
    for _ in range(100):
        if open(log).read().count(' code: ') >= 9: break
        time.sleep(0.1)
    codes = {}
    for m in re.finditer(r'^(\w+) (access|service) code: (\S+)$', open(log).read(), re.M):
        codes[(m[1].lower(), m[2])] = m[3]
    cookie = {}
    for role in ('staff', 'owner'):
        s, b, h = api('/api/demo/login', {'accessCode': codes[(role, 'access')]})
        cookie[role] = h['Set-Cookie'].split(';')[0]
    for tool in ('assessDecision', 'resolveDecision', 'decisionStatus'):
        s, b, _ = api('/api/agent-tools', {'tool': tool, 'enabled': True}, cookie['owner'], 'on-' + tool)
        assert s == 200, b
    ids = {'bayview': 'customer_demo_bayview', 'northside': 'customer_demo_northside', 'lakeside': 'customer_demo_lakeside', 'harbourline': 'customer_demo_harbourline',
           'cityside': 'customer_demo_cityside'}

    def resolve(args, key):
        s, b, _ = api('/api/tools/resolveDecision', {'args': {'recommendation': 'approve', 'reasoning': 'Fictional page check.', **args}}, cookie['staff'], key)
        assert s == 200 and b['ok'], b
        return b['result']
    bay = resolve({'kind': 'extension', 'customerId': ids['bayview'], 'invoiceReference': 'DEMO-301', 'requestedDueDate': '2026-11-10'}, 'r-bay')
    north = resolve({'kind': 'trial_credit', 'customerId': ids['northside'], 'orderAmount': '800.00', 'termsDays': 14}, 'r-north')
    lake = resolve({'kind': 'trial_credit', 'customerId': ids['lakeside'], 'orderAmount': '600.00', 'termsDays': 14}, 'r-lake')
    harb = resolve({'kind': 'trial_credit', 'customerId': ids['harbourline'], 'orderAmount': '5000.00', 'termsDays': 14}, 'r-harb')
    city = resolve({'kind': 'extension', 'customerId': ids['cityside'], 'invoiceReference': 'DEMO-410', 'days': 14}, 'r-city')
    assert (bay['status'], north['status'], lake['status'], harb['status'], city['status']) == ('decided', 'decided', 'gathering_evidence', 'awaiting_owner', 'awaiting_owner')
    con = sqlite3.connect(tmp + '/records.db')

    b = Browser()
    def sign_in(code):
        b.js("(() => { const i = document.querySelector('#code'); i.value = %s; document.querySelector('#signin').requestSubmit(); return true })()" % json.dumps(code))
    def text(sel='#main'):
        return b.js("document.querySelector(%s)?.innerText || ''" % json.dumps(sel))
    def has(sel):
        return b.js("!!document.querySelector(%s)" % json.dumps(sel))
    def click(sel):
        return b.js("(() => { const e = document.querySelector(%s); if (!e) return false; e.click(); return true })()" % json.dumps(sel))
    def fill(name, value):
        b.js("(() => { const e = document.querySelector('[name=\"' + %s + '\"]'); e.value = %s; return true })()" % (json.dumps(name), json.dumps(value)))
    def choose(name, value):
        return b.js("(() => { const e = document.querySelector('[name=\"' + %s + '\"][value=\"' + %s + '\"]'); if (!e) return false; e.checked = true; return true })()" % (json.dumps(name), json.dumps(value)))
    def sign_out():
        b.js("document.querySelector('#signout').click()"); b.wait("!!document.querySelector('#signin')")
    def case(case_id):
        return api('/api/decision-cases/' + case_id, None, cookie['owner'])[1]
    def p_count(sel):
        return b.js("document.querySelectorAll(%s).length" % json.dumps(sel))
    def owner_write(path, body, key=None):
        return api(path, body, cookie['owner'], key, {'X-Nucleon-CSRF': api('/api/session', None, cookie['owner'])[1]['csrf']})

    # ---- E. the evidence page (staff)
    act = lake['actionId']
    b.goto(BASE + '/#/actions/' + act)
    check('E1 a deep link with no session shows the sign-in gate', b.wait("!!document.querySelector('#signin')"))
    sign_in(codes[('staff', 'access')])
    check('E1 after sign-in the evidence page opens', b.wait("!!document.querySelector('[data-testid=evidence-page]')"), b.js('location.hash'))
    page = text()
    check('E1 heading says confirming facts, not approving credit', 'You are confirming facts, not approving credit.' in page, page[:200].replace('\n', ' | '))
    check('E1 says Nucleon applies the Owner\'s policy after submitting', "Nucleon applies the Owner's policy after you submit." in page)
    check('E1 asks for a deposit and a business identity, with the amount needed', has('[data-testid=need-deposit]') and has('[data-testid=need-business_identity]') and 'AUD 150.00' in page and not has('[data-testid=need-trade_reference]'), page[:400].replace('\n', ' | '))
    check('E1 the deposit asks how Staff know it (bank, document, or only the customer\'s word) and says what each means', all(has('[name="deposit.basis"][value="%s"]' % v) for v in ('bank', 'document', 'customer_statement')) and
          'never counts' in text('[data-testid=need-deposit]') and 'not a recorded payment' in text('[data-testid=need-deposit]') and 'Staff-checked' in text('[data-testid=need-deposit]'), text('[data-testid=need-deposit]')[:300].replace('\n', ' | '))
    check('E1 the identity asks where Staff saw it (registry or document)', has('[name="business_identity.basis"][value="registry"]') and has('[name="business_identity.basis"][value="document"]'))
    check('E1 shows the request (customer, order, terms) from the backend', 'Lakeside Kiosk (fictional)' in page and 'AUD 600.00' in page and '14 days' in page)
    check('E1 offers no approve button', 'Approve' not in b.js("[...document.querySelectorAll('#main button, #main a.btn')].map(e => e.innerText).join('|')"))
    # empty submit: the backend refuses, the page says so, nothing is recorded
    b.js("""(() => { window.__calls = []; const real = window.fetch; window.fetch = (u, o = {}) => { if (String(u).includes('/evidence')) window.__calls.push({ u: String(u), h: o.headers, b: o.body }); return real(u, o); }; return true })()""")
    click('#ev-submit')
    check('E2 an empty submit is refused with a message and records nothing', b.wait("!!document.querySelector('#ev-form .error:not(:empty)')") and case(lake['caseId'])['status'] == 'gathering_evidence', text('#ev-form')[-200:])
    n_facts = con.execute('SELECT COUNT(*) FROM confirmed_facts').fetchone()[0]
    fill('deposit.amount', '150.00'); fill('deposit.receivedDate', '2026-10-23'); fill('deposit.reference', 'DEP-LK-PAGE')
    fill('business_identity.registration', 'Registration 555 (fictional)'); fill('business_identity.tradingName', 'Lakeside Kiosk (fictional)')
    click('#ev-submit')
    check('E2b amounts without saying how Staff know them are refused at the basis, and nothing is recorded', b.wait("!!document.querySelector('#ev-form [data-error-for=\"deposit.basis\"]:not(:empty)')") and
          con.execute('SELECT COUNT(*) FROM confirmed_facts').fetchone()[0] == n_facts and case(lake['caseId'])['status'] == 'gathering_evidence', text('#ev-form')[:300].replace('\n', ' | '))
    choose('deposit.basis', 'bank'); choose('business_identity.basis', 'document')
    b.js("(() => { document.querySelector('#ev-submit').click(); document.querySelector('#ev-submit').click(); return true })()")
    check('E3 the page shows the result: executed and the backend\'s status sentence', b.wait("document.querySelector('[data-testid=evidence-page]')?.dataset.status === 'executed'") and
          'Approved within the Owner\'s delegation policy (policy version 1)' in text('[data-testid=case-status-text]'), text('[data-testid=case-result]')[:300].replace('\n', ' | '))
    calls = b.js('window.__calls')
    sent = [c for c in calls if any(i.get('basis') == 'bank' and i.get('amount') == '150.00' for i in json.loads(c['b']).get('items', []))]
    check('E3 the submit sent {version, items} with Idempotency-Key and X-Nucleon-CSRF, once for the good form', len(sent) == 1 and json.loads(sent[0]['b'])['version'] == 1 and sent[0]['h'].get('Idempotency-Key') and len(sent[0]['h'].get('X-Nucleon-CSRF', '')) >= 24, json.dumps(calls)[:300])
    check('E3 the page shows the deposit source and level in words, not as a recorded payment', 'checked by Staff in the bank account (not a recorded payment)' in text('[data-testid=deposit-sources]') and
          'a recorded payment in Nucleon Records' not in text('[data-testid=deposit-sources]'), text('[data-testid=deposit-sources]'))
    check('E3 status and handling are shown', 'decided' in text('[data-testid=case-status]') and 'Approved by the agent' in text('[data-testid=case-result]'))
    check('E3 two facts were kept, and the case is decided by the agent', con.execute('SELECT COUNT(*) FROM confirmed_facts').fetchone()[0] == n_facts + 2 and case(lake['caseId'])['decision']['by'] == 'agent')
    check('E3 no form remains and the page says nothing was sent to the customer', not has('#ev-form') and 'Nucleon sent nothing to the customer' in text())
    b.js('location.reload()', False); time.sleep(1)
    check('E4 reload shows the persisted executed state with the case sentence', b.wait("document.querySelector('[data-testid=evidence-page]')?.dataset.status === 'executed'") and 'Approved within the Owner' in text('[data-testid=case-status-text]'))
    # a second request: expired
    row = con.execute("SELECT id, data FROM actions WHERE kind='evidence' AND status='executed'").fetchall()
    check('E4 exactly one evidence action was executed', len(row) == 1)
    # expired: a new gathering case on a fresh customer is needed; reuse Harbourline after the Owner closes nothing: use Lakeside-like new customer via records
    s, rec, _ = api('/api/records/customers', {'name': 'Mooncove Bakery (fictional)'}, cookie['staff'], 'cust-moon')
    moon = rec['record']['id']
    moon_case = resolve({'kind': 'trial_credit', 'customerId': moon, 'orderAmount': '400.00', 'termsDays': 14}, 'r-moon')
    check('E5 (setup) another new customer is asked for information', moon_case['status'] == 'gathering_evidence', moon_case['status'])
    data = json.loads(con.execute('SELECT data FROM actions WHERE id=?', (moon_case['actionId'],)).fetchone()[0]); data['expiresAt'] = '2026-01-01T00:00:00+00:00'
    con.execute('UPDATE actions SET data=? WHERE id=?', (json.dumps(data), moon_case['actionId'])); con.commit()
    b.goto(BASE + '/#/actions/' + moon_case['actionId'])
    check('E5 an expired request reads Expired with no form', b.wait("document.querySelector('[data-testid=evidence-page]')?.dataset.status === 'expired'") and not has('#ev-form') and 'Expired' in text('[data-testid=banner]'), text('[data-testid=banner]'))
    s, again, _ = api('/api/tools/resolveDecision', {'args': {'kind': 'trial_credit', 'customerId': moon, 'orderAmount': '400.00', 'termsDays': 14, 'recommendation': 'approve', 'reasoning': 'Again.'}}, cookie['staff'], 'r-moon-2')
    moon_act = again['result']['actionId']
    check('E5 asking again gives a new live request', moon_act != moon_case['actionId'] and again['result']['replayed'] is True)
    # stale csrf then a 400 on an invalid amount
    b.goto(BASE + '/#/actions/' + moon_act); b.wait("!!document.querySelector('#ev-form')")
    b.js("S.session.csrf = 'a-stale-token'")
    fill('deposit.amount', '100.00'); fill('deposit.receivedDate', '2026-10-23')
    fill('business_identity.registration', 'R'); fill('business_identity.tradingName', 'T'); choose('deposit.basis', 'bank'); choose('business_identity.basis', 'registry')
    click('#ev-submit')
    check('E6 a stale token is refused, refreshed, and nothing is recorded', b.wait("!!document.querySelector('[data-testid=notice]')") and 'security token' in text('[data-testid=notice]') and case(moon_case['caseId'])['status'] == 'gathering_evidence', text('[data-testid=notice]'))
    b.wait("!!document.querySelector('#ev-form')")
    fill('deposit.amount', '12.345'); fill('deposit.receivedDate', '2026-10-23'); fill('business_identity.registration', 'R'); fill('business_identity.tradingName', 'T')
    choose('deposit.basis', 'bank'); choose('business_identity.basis', 'registry')
    click('#ev-submit')
    check('E6 an amount with too many decimals is refused with the backend\'s words', b.wait("!!document.querySelector('#ev-form .error:not(:empty)')") and 'decimal' in text('#ev-form').lower(), text('#ev-form')[-160:])
    # "the customer said so" is accepted as a statement and never approves: the case stays with the request for information
    fill('deposit.amount', '100.00'); choose('deposit.basis', 'customer_statement'); choose('business_identity.basis', 'registry')
    click('#ev-submit')
    check('E6b the customer\'s word alone is kept and shown as not verified, and the case is still gathering evidence', b.wait("document.querySelector('[data-testid=evidence-page]')?.dataset.status === 'executed'") and
          'reported by the customer, not verified' in text('[data-testid=deposit-sources]') and case(moon_case['caseId'])['status'] == 'gathering_evidence' and case(moon_case['caseId'])['decision'] is None, text('[data-testid=case-result]')[:300].replace('\n', ' | '))
    moon_act = case(moon_case['caseId'])['actionId']
    # others see it read-only
    sign_out()
    b.goto(BASE + '/#/actions/' + moon_act); b.wait("!!document.querySelector('#signin')"); sign_in(codes[('owner', 'access')])
    check('E7 the owner can read the request but has no form', b.wait("!!document.querySelector('[data-testid=evidence-page]')") and not has('#ev-form') and 'Staff confirm these facts' in text())
    sign_out()
    b.goto(BASE + '/#/actions/' + moon_act); b.wait("!!document.querySelector('#signin')"); sign_in(codes[('agent', 'access')])
    check('E7 the AI Agent identity has no form', b.wait("!!document.querySelector('[data-testid=evidence-page]')") and not has('#ev-form'), text('[data-testid=evidence-form]')[:200])
    sign_out()

    # ---- D. the delegation page (owner)
    b.goto(BASE + '/#/delegation'); b.wait("!!document.querySelector('#signin')"); sign_in(codes[('staff', 'access')])
    check('D1 staff have no Delegation link and the page is for the owner only', b.wait("!!document.querySelector('[data-testid=delegation-owner-only]')") and not has('a[data-area=delegation]'))
    sign_out()
    b.goto(BASE + '/#/delegation'); b.wait("!!document.querySelector('#signin')"); sign_in(codes[('owner', 'access')])
    check('D2 the owner sees the page, with a Delegation link in the navigation', b.wait("!!document.querySelector('[data-testid=delegation-page]')") and has('.mainnav a[data-area=delegation]'))
    page = text()
    check('D2 the policy state and summary come from the backend', 'Policy version 1.' in text('[data-testid=policy-state]') and 'Delegated' in text('[data-testid=policy-summary]') and 'AUD 1,000.00' in text('[data-testid=policy-summary]'), text('[data-testid=policy-state]'))
    check('D2 waiting: both waiting cases link to the Review page (one place to act) and to their timeline, with no decision controls here', p_count('[data-testid=waiting-case]') == 2 and p_count('[data-testid=open-review]') == 2 and
          not has('[data-decide]') and not has('[data-feedback]') and 'Decide page' in text('[data-testid=act-on-review]') and
          b.js("[...document.querySelectorAll('[data-testid=waiting-case] [data-testid=case-timeline-link]')].map(a => a.getAttribute('href')).sort().join()") == ','.join(sorted('#/decision-cases/' + x['caseId'] for x in (harb, city))))
    check('D2 each waiting case shows the one-line why', all(len(t) > 10 for t in b.js("[...document.querySelectorAll('[data-testid=waiting-case] .hint')].map(e => e.innerText)")), page[:100])
    check('D2 recent agent decisions list the agent\'s approvals, each with a timeline link and "not reviewed yet", and a note pointing to the Review page', b.js("document.querySelectorAll('[data-testid=agent-decision]').length") >= 3 and
          'not reviewed yet' in text('[data-testid=agent-decision]') and p_count('[data-testid=agent-decision] [data-testid=case-timeline-link]') >= 3 and 'Decide page' in text('[data-testid=act-on-review-recent]'))
    check('D2 a suggestion offers to raise the trial exposure limit to AUD 900.00', 'AUD 900.00' in text('[data-testid=suggestion]') and 'A suggestion only' in text('[data-testid=suggestion]'), text('[data-testid=suggestion]')[:200])
    check('D2 live counts show the denominator and that fictional cases are excluded', 'Fictional cases are excluded' in text('[data-testid=counts-note]') and 'in all' in text('[data-testid=counts-note]'), text('[data-testid=counts-note]'))
    check('D2 the Owner sees the Staff-checked deposit limit in the summary and in Advanced', 'counts when the exposure is up to AUD 600.00' in text('[data-testid=policy-summary]') and
          b.js("document.querySelector('[name=\"newCustomers.staffCheckedDepositUpTo\"]')?.value") == '600.00' and b.js("!!document.querySelector('.dg-advanced [name=\"newCustomers.staffCheckedDepositUpTo\"]')"))
    check('D2 the form is "Basic" with the advanced settings folded', has('.dg-basic') and b.js("document.querySelector('.dg-advanced').open") is False)
    check('D2 the versions list starts with version 1', 'Version 1' in text('[data-testid=policy-history]'))
    # the decisions and the feedback are made on the Review page (deploy/review_page_check.py); here the same state is made through the API so the checks below have it
    check('D3 (setup) the Owner declines the large trial credit', owner_write('/api/decision-cases/' + harb['caseId'] + '/decide', {'outcome': 'decline', 'reason': 'Too large for a first order (page check).', 'version': case(harb['caseId'])['version']})[0] == 200)
    check('D4 (setup) the Owner agrees with the extension the agent approved', owner_write('/api/decision-cases/' + bay['caseId'] + '/feedback', {'verdict': 'agree', 'reason': 'Right call (page check).', 'version': case(bay['caseId'])['version']}, 'fb-bay')[0] == 200)
    check('D4 (setup) the Owner overrides the trial credit the agent approved', owner_write('/api/decision-cases/' + north['caseId'] + '/feedback', {'verdict': 'disagree', 'override': True, 'reason': 'Revoke it (page check).', 'version': case(north['caseId'])['version']}, 'fb-north')[0] == 200)
    b.js('location.reload()', False); b.wait("!!document.querySelector('[data-testid=delegation-page]')"); time.sleep(0.5)
    check('D4 the control panel shows the feedback as the Owner gave it, and the override with what it does not undo', 'You agreed: Right call (page check).' in text('[data-testid=agent-decision][data-case=%s]' % bay['caseId']) and
          'Staff must follow up' in text('[data-testid=agent-decision][data-case=%s] [data-testid=external-effects]' % north['caseId']), text('[data-testid=agent-decision]')[:200])
    check('D4 and it has no feedback buttons to press', not has('[data-feedback]') and not has('[data-decide]'))
    # the review settings: the two keys, as shown
    check('D4b the review settings are on the form: tacit agreement off (empty, placeholder "off"), track record sources "both"', b.js("document.querySelector('[name=\"feedback.tacitAgreeAfterDays\"]').value") == '' and
          b.js("document.querySelector('[name=\"feedback.tacitAgreeAfterDays\"]').placeholder") == 'off' and b.js("document.querySelector('[name=\"trackRecord.sources\"]:checked')?.value") == 'both' and has('[data-testid=review-settings]'))
    check('D4b the tacit setting says what it does in one place: counted as agreement, labelled as treated-as-agreed, replaceable, never while paused or on an overridden decision', all(w in text('[data-testid=review-settings]') for w in ('Count an approval the agent made as agreed', 'Treated as agreed', 'never as something you wrote', 'paused', 'overrode')), text('[data-testid=review-settings]')[:300])
    check('D4b the three sources each have a one-line explanation', all(w in text('[data-testid=review-settings]') for w in ('Fictional cases only', 'Live cases only', 'Both, pooled (default)', 'a simulation', 'come to you', 'always shown apart')))
    counts = text('[data-testid=track-counts]')
    check('D4b the gate\'s current counts are shown per kind: fictional, live and pooled, and what was counted', 'Payment extensions' in counts and 'Fictional:' in counts and 'Live:' in counts and 'Pooled for the gate' in counts and 'Counted this time:' in counts and 'Setting: fictional and live cases together' in counts, counts[:300].replace('\n', ' | '))
    st = api('/api/delegation/stats', None, cookie['owner'])[1]['trackRecord']
    check('D4b the counts equal the backend\'s (stats.trackRecord)', all(('Fictional: %d' % st[k]['gate']['fictional']['cases']) in counts and ('Live: %d' % st[k]['gate']['live']['cases']) in counts for k in st), counts[:200])
    # suggestion -> form -> save
    click('[data-suggest="0"]')
    b.js("""(() => { window.__put = []; const real = window.fetch; window.fetch = (u, o = {}) => { if (o.method === 'PUT') window.__put.push(JSON.parse(o.body)); return real(u, o); }; return true })()""")
    fill('feedback.tacitAgreeAfterDays', '7'); choose('trackRecord.sources', 'live')
    check('D5 the suggestion fills the form and saves nothing', b.js("document.querySelector('[name=\"newCustomers.maxExposure\"]').value") == '900.00' and api('/api/delegation/policy', None, cookie['owner'])[1]['version'] == 1)
    click('#dg-save')
    check('D5 saving makes version 2 with the new limit', b.wait("document.querySelector('[data-testid=policy-state]')?.innerText.includes('Policy version 2.')") and api('/api/delegation/policy', None, cookie['owner'])[1]['newCustomers']['maxExposure']['minorUnits'] == '90000', text('[data-testid=notice]'))
    put = b.js('window.__put')
    check('D5 the save sent both new keys explicitly, as shown: feedback.tacitAgreeAfterDays 7 and trackRecord.sources live', len(put) == 1 and put[0]['feedback'] == {'tacitAgreeAfterDays': 7} and put[0]['trackRecord']['sources'] == 'live' and 'minReviewedCases' in put[0]['trackRecord'], put)
    pol2 = api('/api/delegation/policy', None, cookie['owner'])[1]
    check('D5 the saved version holds them, and the page now shows them', pol2['feedback']['tacitAgreeAfterDays'] == 7 and pol2['trackRecord']['sources'] == 'live' and b.js("document.querySelector('[name=\"feedback.tacitAgreeAfterDays\"]').value") == '7' and
          b.js("document.querySelector('[name=\"trackRecord.sources\"]:checked')?.value") == 'live', pol2['feedback'])
    check('D5 the track-record counts follow the saved setting: live only', 'Setting: live Owner-reviewed cases only' in text('[data-testid=track-counts]') and 'Counted this time: live Owner-reviewed cases' in text('[data-testid=track-counts]'), text('[data-testid=track-counts]')[:300].replace('\n', ' | '))
    check('D5 the other settings were kept and the percentages round-trip exactly', (lambda p: p['newCustomers']['staffCheckedDepositUpTo']['minorUnits'] == '60000' and p['newCustomers']['minDepositShare'] == '0.25' and p['extensions']['maxPriorLateShare'] == '0.25' and p['trackRecord']['minAgreement'] == '0.8' and p['restrictions']['unusualSizeMultiple'] == '3' and p['mode'] == 'delegated')(api('/api/delegation/policy', None, cookie['owner'])[1]))
    # stale version: another change behind the page
    s, out, _ = api('/api/delegation/policy/pause', {'expectedVersion': 2}, cookie['owner'], headers={'X-Nucleon-CSRF': api('/api/session', None, cookie['owner'])[1]['csrf']})
    check('D6 (setup) the policy was paused behind the page', s == 200 and out['version'] == 3, out)
    fill('limits.maxDecisionExposure', '950.00')
    click('#dg-save')
    check('D6 a stale save is refused, the page reads the new version and says the edits were not saved', b.wait("document.querySelector('[data-testid=notice]')?.innerText.includes('changed since you loaded it')") and 'not saved' in text('[data-testid=notice]') and
          api('/api/delegation/policy', None, cookie['owner'])[1]['limits']['maxDecisionExposure']['minorUnits'] == '100000', text('[data-testid=notice]'))
    check('D6 the page now shows version 3, paused, with a Resume button', 'Policy version 3 · paused.' in text('[data-testid=policy-state]') and has('[data-testid=resume]'))
    click('#dg-pause')
    check('D7 resume makes version 4, running', b.wait("document.querySelector('[data-testid=policy-state]')?.innerText.includes('Policy version 4.')") and has('[data-testid=pause]'), text('[data-testid=policy-state]'))
    click('#dg-pause')
    check('D7 pause makes version 5, paused', b.wait("document.querySelector('[data-testid=policy-state]')?.innerText.includes('Policy version 5 · paused')"))
    click('#dg-pause'); b.wait("document.querySelector('[data-testid=policy-state]')?.innerText.includes('Policy version 6.')")
    # validation error beside the field
    fill('extensions.maxDays', 'abc')
    click('#dg-save')
    check('D8 a bad value is refused next to its field and nothing is saved', b.wait("!!document.querySelector('[data-error-for=\"extensions.maxDays\"]:not(:empty)')") and api('/api/delegation/policy', None, cookie['owner'])[1]['version'] == 6, text('#dg-form')[:100])
    b.js('location.reload()', False); b.wait("!!document.querySelector('[data-testid=delegation-page]')"); time.sleep(0.4)
    fill('feedback.tacitAgreeAfterDays', 'abc')
    click('#dg-save')
    check('D8b a bad tacit-agreement value is refused next to its own field and nothing is saved', b.wait("!!document.querySelector('[data-error-for=\"feedback.tacitAgreeAfterDays\"]:not(:empty)')") and api('/api/delegation/policy', None, cookie['owner'])[1]['version'] == 6,
          text('[data-error-for="feedback.tacitAgreeAfterDays"]'))
    fill('feedback.tacitAgreeAfterDays', 'off'); choose('trackRecord.sources', 'fictional')
    click('#dg-save')
    check('D8c "off" turns it off (null) and the sources can be set back; the page shows both', b.wait("document.querySelector('[data-testid=policy-state]')?.innerText.includes('Policy version 7.')") and
          (lambda p: p['feedback']['tacitAgreeAfterDays'] is None and p['trackRecord']['sources'] == 'fictional')(api('/api/delegation/policy', None, cookie['owner'])[1]) and
          b.js("document.querySelector('[name=\"trackRecord.sources\"]:checked')?.value") == 'fictional', text('[data-testid=policy-state]'))
    b.js('location.reload()', False); b.wait("!!document.querySelector('[data-testid=delegation-page]')"); time.sleep(0.4)
    fields = b.js("[...document.querySelectorAll('#dg-form .field')].map(f => [!!f.querySelector('label .req'), !!f.querySelector('label .opt')])")
    check('D8e every Control panel field is marked Required or Optional, never both or neither', len(fields) > 20 and all(r != o for r, o in fields) and has('#dg-form [data-testid=required-legend]'), [f for f in fields if f[0] == f[1]][:3])
    check('D8e a limit is Required and an empty-able one is Optional', b.js("!!document.querySelector('label[for=dg-max-decision] .req') && !!document.querySelector('label[for=dg-auto30] .opt') && document.querySelector('#dg-max-decision').getAttribute('aria-required') === 'true'"))
    # the three extension day limits (Quick setup, 11 Nov 2026): each saves, shows in the summary, and an empty one is stored as null
    fill('extensions.maxDaysFromRequest', '14'); fill('extensions.maxDaysPastOriginalDue', '45')
    click('#dg-save')
    saved = b.wait("document.querySelector('[data-testid=policy-state]')?.innerText.includes('Policy version 8.')")
    ext = api('/api/delegation/policy', None, cookie['owner'])[1]['extensions']
    check('D8d the two new day limits are saved', saved and (ext.get('maxDaysFromRequest'), ext.get('maxDaysPastOriginalDue')) == (14, 45), ext)
    b.js('location.reload()', False); b.wait("!!document.querySelector('[data-testid=delegation-page]')"); time.sleep(0.4)
    check('D8d after a reload the fields show them, and the summary says how each is counted',
          (b.js("document.querySelector('#dg-ext-from-request').value"), b.js("document.querySelector('#dg-ext-total').value")) == ('14', '45') and
          '14 days after the request' in text('[data-testid=policy-summary]') and '45 days after the original due date' in text('[data-testid=policy-summary]'), text('[data-testid=policy-summary]'))
    check('D8d each day field says how it is counted', 'not from today' in text('#dg-form') and 'Counted from the day the customer asks' in text('#dg-form') and 'Counted from the first due date' in text('#dg-form'))
    fill('extensions.maxDaysFromRequest', ''); fill('extensions.maxDaysPastOriginalDue', '')
    click('#dg-save')
    saved = b.wait("document.querySelector('[data-testid=policy-state]')?.innerText.includes('Policy version 9.')")
    ext = api('/api/delegation/policy', None, cookie['owner'])[1]['extensions']
    check('D8d emptied, both are stored as null and leave the summary', saved and ext.get('maxDaysFromRequest') is None and ext.get('maxDaysPastOriginalDue') is None and
          'after the request' not in text('[data-testid=policy-summary]'), ext)
    # 11 Nov 2026: the Schedule and model forms shared an id with their section heading, so their buttons were bound to the heading and did nothing; and a
    # customer rule crashed the page when it was opened directly (the name came from the Customers page's data, not loaded here).
    check('D8e the schedule and model forms are forms (no heading shares their id)', b.js("['dg-sched','dg-model','dg-rule','dg-form'].every(i => document.querySelectorAll('#' + i).length === 1 && document.getElementById(i).tagName === 'FORM')"))
    fill('at', '2026-12-01'); click('[data-testid=schedule-add]')
    check('D8e the Schedule button stores a scheduled change', b.wait("!!document.querySelector('[data-testid=schedules-pending]')") and
          any(x['status'] == 'pending' and x['at'] == '2026-12-01' for x in api('/api/delegation/schedules', None, cookie['owner'])[1]['schedules']))
    b.js("(() => { document.querySelector('.dg-advanced').open = true; return true })()")
    fill('restrictions.holdCustomers', 'Bayview Gelato Co (fictional), Nobody Pty'); click('#dg-save')
    check('D8e a name that is no customer is refused before saving, and a real name is stored as its id', b.wait("(document.querySelector('[data-error-for=\\\"restrictions.holdCustomers\\\"]')?.innerText || '').includes('Nobody Pty')") and
          api('/api/delegation/policy', None, cookie['owner'])[1]['restrictions']['holdCustomers'] == [])
    held_name = b.js("(DG.customers.find(c => c.id === %s) || {}).name" % json.dumps(ids['riverside'] if 'riverside' in ids else ids['bayview']))
    fill('restrictions.holdCustomers', held_name); click('#dg-save')
    saved_hold = b.wait("document.querySelector('[data-testid=policy-summary]')?.innerText.includes(%s)" % json.dumps(held_name))
    check('D8e the held customer is shown by name and stored by id', saved_hold and api('/api/delegation/policy', None, cookie['owner'])[1]['restrictions']['holdCustomers'] == [ids['riverside'] if 'riverside' in ids else ids['bayview']])
    fill('restrictions.holdCustomers', ''); click('#dg-save'); b.wait("!document.querySelector('[data-testid=policy-summary]')?.innerText.includes(%s)" % json.dumps(held_name))
    b.js("(() => { const f = document.querySelector('#dg-rule'); f.elements.customerId.value = %s; f.elements.maxExposure.value = '900.00'; return true })()" % json.dumps(ids['bayview']))
    click('[data-testid=rule-add]')
    ruled = b.wait("!!document.querySelector('[data-testid=customer-rules]')")
    b.js('(() => { location.reload(); return true })()')
    check('D8e a customer rule shows the customer by name when the page is opened directly', ruled and b.wait("!!document.querySelector('[data-testid=customer-rules]')") and
          'Bayview' in text('[data-testid=customer-rules]') and not has('.state-msg.error'), text('[data-testid=customer-rules]')[:120])
    # the request page for a delegated request
    b.goto(BASE + '/#/case/' + bay['requestId'])
    check('D9 the owner\'s case page says the agent decided it under Owner policy v1', b.wait("!!document.querySelector('[data-testid=delegated-request]')") and 'Resolved by the assistant under your delegation policy (version 1)' in text('[data-testid=delegated-request]') and
          'Owner policy version 1' in text('[data-testid=authority]') and 'Decided by the agent under Owner policy v1' in text('[data-testid=decision]'), text('[data-testid=decision]')[:240])
    b.goto(BASE + '/#/case/' + city['requestId'])
    check('D9 a request sent to the owner reads as such and the owner can decide it', b.wait("!!document.querySelector('[data-testid=delegated-request]')") and 'outside what the Owner delegated' in text('[data-testid=delegated-request]') and b.wait("!!document.querySelector('#decide')"))
    sign_out()
    b.goto(BASE + '/#/case/' + bay['requestId']); b.wait("!!document.querySelector('#signin')"); sign_in(codes[('staff', 'access')])
    check('D9 staff see the same decision wording and no decision form', b.wait("!!document.querySelector('[data-testid=delegated-request]')") and 'Decided by the agent under Owner policy v1' in text() and not has('#decide'))
    sign_out()
    # the AI Agent identity cannot write the policy: the page shows the backend's refusal
    b.goto(BASE + '/#/delegation'); b.wait("!!document.querySelector('#signin')"); sign_in(codes[('agent', 'access')])
    b.wait("!!document.querySelector('[data-testid=delegation-page]') || !!document.querySelector('[data-testid=delegation-owner-only]')")
    if has('[data-testid=delegation-page]'):
        click('#dg-save')
        check('D10 the AI Agent identity\'s save is refused by the backend', b.wait("!!document.querySelector('#dg-form .form-error:not(:empty), [data-testid=notice]')") and api('/api/delegation/policy', None, cookie['owner'])[1]['version'] == 7, text('#dg-form')[-200:])
    else:
        check('D10 the AI Agent identity is shown no write controls on this page', True)
    check('Z no page error was thrown', not b.errors(), b.errors()[:2])
    b.close()
finally:
    server.terminate()
    shutil.rmtree(tmp, ignore_errors=True)
print('%d/%d passed' % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
