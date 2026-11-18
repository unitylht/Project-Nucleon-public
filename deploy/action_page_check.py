"""Browser check of the confirmation page of a controlled action (#/actions/<id>), in a headless Chromium, on a scratch records server it starts
itself (deploy/ui_check_server.py on a free loopback port, a throwaway database, the fictional sample). Fictional data only. Standard library only:
the browser is driven through deploy/cdp_min.py (set CHROME_HEADLESS to a chrome-headless-shell binary if Playwright's cache is elsewhere).

    python3 deploy/action_page_check.py          # prints PASS/FAIL per check; exit status 0 only if all pass
"""
import json, os, re, shutil, sqlite3, subprocess, sys, tempfile, time, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_min import Browser, free_port

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tmp = tempfile.mkdtemp(prefix='page-check-')
port, log = free_port(), os.path.join(tmp, 'records.log')
server = subprocess.Popen([sys.executable, ROOT + '/deploy/ui_check_server.py', tmp + '/records.db', str(port)], stdout=open(log, 'w'), stderr=subprocess.STDOUT, cwd=ROOT)
BASE = 'http://127.0.0.1:%d' % port
results = []


def check(name, ok, detail=''):
    results.append(bool(ok))
    print(('PASS ' if ok else 'FAIL ') + name.ljust(88) + str(detail)[:200])


def api(path, body=None, cookie=None, key=None, headers=None):
    h = {**(headers or {})}
    if cookie: h['Cookie'] = cookie
    if key: h['Idempotency-Key'] = key
    if body is not None: h['Content-Type'] = 'application/json'; h['Origin'] = BASE
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None, headers=h)
    try:
        r = urllib.request.urlopen(req, timeout=20)
    except urllib.error.HTTPError as e:
        r = e
    with r:
        return r.status, json.loads(r.read()), r.headers


try:
    for _ in range(100):
        t = open(log).read()
        if t.count(' code: ') >= 8: break
        time.sleep(0.1)
    codes = {}
    for m in re.finditer(r'^(\w+) (access|service) code: (\S+)$', open(log).read(), re.M):
        codes[(m[1].lower(), m[2])] = m[3]
    cookie = {}
    for role in ('staff', 'owner'):
        s, b, h = api('/api/demo/login', {'accessCode': codes[(role, 'access')]})
        cookie[role] = h['Set-Cookie'].split(';')[0]
    # the owner turns the two tools on (they are off by default)
    for tool in ('prepareRequest', 'actionStatus'):
        s, b, _ = api('/api/agent-tools', {'tool': tool, 'enabled': True}, cookie['owner'], 'on-' + tool)
        assert s == 200, b

    def prepare(customer, invoice, days=14, reason='Customer is waiting on a payment.', key=None):
        s, b, _ = api('/api/tools/prepareRequest', {'args': {'customerId': customer, 'invoiceId': invoice, 'days': days, **({'reason': reason} if reason else {})}}, cookie['staff'], key or 'prep-' + invoice + str(time.time()))
        assert s == 200 and b['ok'], b
        return b['result']['actionId']

    def new_invoice(ref):
        s_, r_, _ = api('/api/records/invoices', {'customerId': 'customer_demo_01', 'reference': ref, 'issueDate': '2026-10-01', 'total': '500.00', 'dueDate': '2026-10-25', 'stillOwed': '500.00', 'stillOwedAsOf': '2026-10-16'}, cookie['staff'], 'inv-' + ref)
        assert s_ == 200, r_
        return r_['record']['id']
    a1 = prepare('customer_demo_01', 'invoice_demo_101')
    a2 = prepare('customer_demo_02', 'invoice_demo_201')
    a3 = prepare('customer_demo_02', 'invoice_demo_202', reason=None)

    b = Browser()
    def sign_in(code):
        b.js("(() => { const i = document.querySelector('#code'); i.value = %s; document.querySelector('#signin').requestSubmit(); return true })()" % json.dumps(code))
    def text(sel='#main'):
        return b.js("document.querySelector(%s)?.innerText || ''" % json.dumps(sel))
    def has(sel):
        return b.js("!!document.querySelector(%s)" % json.dumps(sel))
    def click(sel):
        return b.js("(() => { const e = document.querySelector(%s); if (!e) return false; e.click(); return true })()" % json.dumps(sel))

    # ---- 1. deep link survives sign-in (staff)
    b.goto(BASE + '/#/actions/' + a1)
    check('1 a deep link with no session shows the sign-in gate', b.wait("!!document.querySelector('#signin')"))
    sign_in(codes[('staff', 'access')])
    check('1 after sign-in the same link opens the action page', b.wait("!!document.querySelector('[data-testid=action-page]')"), b.js('location.hash'))
    page = text()
    check('1 shows customer, invoice, dates and extension', all(x in page for x in ('Customer', 'DEMO-101', 'Original due date', 'Proposed due date', '14 days')), page[:300].replace('\n', ' | '))
    check('1 shows the reason read-only, labelled as the assistant draft', 'Customer is waiting on a payment.' in page and 'Drafted by the assistant' in page and not b.js("!!document.querySelector('#main textarea, #main input[type=text]')"))
    check('1 says plainly that confirming submits for review and does not approve', 'Confirming submits this request to the owner for review. It does not approve the extension.' in page)
    check('1 completeness warning is shown (records are unconfirmed)', has('[data-testid=completeness]') and 'Unconfirmed' in page, text('[data-testid=completeness]')[:120])
    check('1 the controls are Submit for owner review and Cancel proposal, no Approve', 'Submit for owner review' in page and 'Cancel proposal' in page and 'Approve' not in b.js("[...document.querySelectorAll('#main button, #main a.btn')].map(e => e.innerText).join('|')"))
    check('1 links to the customer page', b.js("document.querySelector('[data-testid=customer-link]')?.getAttribute('href')") == '#/customers/customer_demo_01')

    # ---- 2. confirm: key, csrf header, double click -> one request
    b.js("""(() => { window.__calls = []; const real = window.fetch; window.fetch = (u, o = {}) => { if (String(u).includes('/confirm') || String(u).includes('/cancel')) window.__calls.push({ u: String(u), h: o.headers, b: o.body }); return real(u, o); }; return true })()""")
    b.js("(() => { const e = document.querySelector('#act-confirm'); e.click(); e.click(); e.click(); return true })()")
    check('2 the page shows the submitted state with a request id', b.wait("document.querySelector('[data-testid=action-page]')?.dataset.status === 'executed'"), text('[data-testid=submitted]')[:200].replace('\n', ' | '))
    calls = b.js('window.__calls')
    check('2 a triple click sent exactly one confirm', len(calls) == 1, len(calls))
    c = calls[0]
    check('2 the confirm sent {version} only, with Idempotency-Key and X-Nucleon-CSRF', json.loads(c['b']) == {'version': 1} and c['h'].get('Idempotency-Key') and c['h'].get('X-Nucleon-CSRF') and len(c['h']['X-Nucleon-CSRF']) >= 24, json.dumps(c)[:200])
    s, reqs, _ = api('/api/requests', None, cookie['staff'])
    mine = [r for r in reqs if r.get('confirmedAction') == a1]
    check('2 exactly one request exists for the action, awaiting the owner', len(mine) == 1 and mine[0]['status'] == 'awaiting_owner', [r['status'] for r in mine])
    page = text()
    check('2 submitted text: for the owner to review, not approved; request link', 'Submitted for the owner to review.' in page and 'Open the request' in page and mine[0]['id'] in page)
    check('2 no submit button remains', not has('#act-confirm'))
    b.goto(BASE + '/#/actions/' + a1); b.js('location.reload()', False); time.sleep(1)
    check('2 reload shows the persisted submitted state', b.wait("document.querySelector('[data-testid=action-page]')?.dataset.status === 'executed'"))
    # request/case page as staff
    b.goto(BASE + '/#/case/' + mine[0]['id'])
    check('3 staff case page says submitted by staff and not AI-prepared', b.wait("!!document.querySelector('[data-testid=confirmed-action]')") and 'Prepared by' not in text('.case-head'), text('.case-head')[:240].replace('\n', ' | '))
    check('3 staff see no answer form and no decision form', not has('#answer') and not has('#decide'))

    # ---- 4. replayed
    b.goto(BASE + '/#/actions/' + a1); time.sleep(0.5)

    # ---- 5. owner: read-only with cancel only
    b.js("document.querySelector('#signout').click()")
    check('5 sign out returns to the gate', b.wait("!!document.querySelector('#signin')"))
    b.goto(BASE + '/#/actions/' + a2)
    b.wait("!!document.querySelector('#signin')")
    sign_in(codes[('owner', 'access')])
    check('5 owner opens the deep link', b.wait("!!document.querySelector('[data-testid=action-page]')"))
    check('5 owner has no submit button, only Cancel proposal', not has('#act-confirm') and has('#act-cancel'), text('[data-testid=controls]')[:200].replace('\n', ' | '))
    # owner sees the executed one as "submitted by staff for your review"
    b.goto(BASE + '/#/actions/' + a1)
    b.wait("document.querySelector('[data-testid=action-page]')?.dataset.action === %s" % json.dumps(a1))
    check('5 owner sees the submitted action as submitted by staff for your review', 'Submitted by staff for your review.' in text() and 'Open the request to decide' in text(), text('[data-testid=submitted]')[:160].replace('\n', ' | '))
    b.goto(BASE + '/#/case/' + mine[0]['id'])
    b.wait("!!document.querySelector('[data-testid=confirmed-action]')")
    cap = text('.case-head')
    check('5 owner case page: Submitted by staff for your review (confirmed action act_...)', re.search(r'Submitted by staff for your review \(confirmed action act_[0-9a-f]{16}\)', cap) is not None, cap[:260].replace('\n', ' | '))
    check('5 owner decision form works as ever (is present)', b.wait("!!document.querySelector('#decide')"))
    # cancel as owner (a2)
    b.goto(BASE + '/#/actions/' + a2)
    b.wait("!!document.querySelector('#act-cancel')")
    click('#act-cancel')
    check('5 the cancel dialog opens', b.wait("!!document.querySelector('dialog[open]')"))
    b.js("document.querySelector('dialog[open] [type=submit]').click()")
    check('5 owner cancelled it: state cancelled, nothing submitted', b.wait("document.querySelector('[data-testid=action-page]')?.dataset.status === 'cancelled'"), text('[data-testid=banner]'))
    s, reqs, _ = api('/api/requests', None, cookie['staff'])
    check('5 no request was made for the cancelled action', not [r for r in reqs if r.get('confirmedAction') == a2])

    # ---- 6. lost response and retry with the same key (staff)
    b.js("document.querySelector('#signout').click()"); b.wait("!!document.querySelector('#signin')")
    b.goto(BASE + '/#/actions/' + a3); b.wait("!!document.querySelector('#signin')")
    sign_in(codes[('staff', 'access')])
    b.wait("!!document.querySelector('#act-confirm')")
    check('6 a proposal with no drafted reason says so', 'No reason was drafted.' in text())
    # first attempt: the request never leaves (network error before sending)
    b.js("""(() => { window.__keys = []; window.__mode = 'drop'; const real = window.fetch; window.fetch = (u, o = {}) => { if (String(u).includes('/confirm')) { window.__keys.push(o.headers['Idempotency-Key']); if (window.__mode === 'drop') { window.__mode = 'lostresponse'; return Promise.reject(new TypeError('Failed to fetch')); } if (window.__mode === 'lostresponse') { window.__mode = 'real'; return real(u, o).then(() => { throw new TypeError('Failed to fetch'); }); } } return real(u, o); }; return true })()""")
    click('#act-confirm')
    check('6 a dropped request: the page re-reads and says it was not submitted, offering Try again', b.wait("!!document.querySelector('[data-testid=uncertain]')") and 'has not been submitted' in text('[data-testid=uncertain]') and 'Try again' in text('#act-confirm'), text('[data-testid=uncertain]')[:200].replace('\n', ' | '))
    s, reqs, _ = api('/api/requests', None, cookie['staff'])
    check('6 nothing was created by the dropped request', not [r for r in reqs if r.get('confirmedAction') == a3])
    # second attempt: the server runs it, the response is lost
    click('#act-confirm')
    check('6 a lost response: the page re-reads and shows it IS submitted', b.wait("document.querySelector('[data-testid=action-page]')?.dataset.status === 'executed'") and 'it did go through' in text('[data-testid=notice]'), text('[data-testid=notice]')[:200])
    keys = b.js('window.__keys')
    check('6 both attempts used the same Idempotency-Key', len(keys) == 2 and keys[0] == keys[1], keys)
    s, reqs, _ = api('/api/requests', None, cookie['staff'])
    check('6 exactly one request exists for that action', len([r for r in reqs if r.get('confirmedAction') == a3]) == 1)

    # ---- 7. expired and superseded and invalidated, staff
    con = sqlite3.connect(tmp + '/records.db')
    # superseded: two proposals on the same free invoice (201; a2 was cancelled)
    old = prepare('customer_demo_02', 'invoice_demo_201', days=14, key='sup1')
    new = prepare('customer_demo_02', 'invoice_demo_201', days=21, key='sup2')
    b.goto(BASE + '/#/actions/' + old)
    check('7 a superseded proposal reads Replaced and has no submit button', b.wait("document.querySelector('[data-testid=action-page]')?.dataset.status === 'superseded'") and not has('#act-confirm') and 'Replaced by a newer proposal' in text('[data-testid=banner]'))
    row = con.execute('SELECT data FROM actions WHERE id=?', (new,)).fetchone()
    d = json.loads(row[0]); d['expiresAt'] = '2026-01-01T00:00:00+00:00'
    con.execute('UPDATE actions SET data=? WHERE id=?', (json.dumps(d), new)); con.commit()
    b.goto(BASE + '/#/actions/' + new)
    check('7 an expired proposal reads Expired and has no submit button', b.wait("document.querySelector('[data-testid=action-page]')?.dataset.status === 'expired'") and not has('#act-confirm'), text('[data-testid=banner]'))
    check('7 an unknown action is "not found" and nothing else', (b.goto(BASE + '/#/actions/act_0000000000000000') or True) and b.wait("!!document.querySelector('[data-testid=action-missing]')"))

    # ---- 8. the page was loaded, then the records changed: the backend refuses and settles it; the page shows the backend's words
    i5 = new_invoice('PG-5'); a5 = prepare('customer_demo_01', i5, days=14, key='p5')
    b.goto(BASE + '/#/actions/' + a5); b.wait("!!document.querySelector('#act-confirm')")
    s_, body_, _ = api('/api/records/invoices/' + i5, {'dueDate': '2026-11-20', 'reason': 'Terms corrected (page check)'}, cookie['staff'], 'fix-202')
    check('8 (setup) the records were changed behind the page', s_ == 200, body_)
    click('#act-confirm')
    check('8 the refusal is shown as not submitted, in the backend words', b.wait("document.querySelector('[data-testid=action-page]')?.dataset.status === 'invalidated'") and 'No longer valid, not submitted' in text('[data-testid=banner]') and has('[data-testid=notice]'), text('[data-testid=notice]')[:200])
    check('8 and there is no submit button, and no request', not has('#act-confirm') and not [r for r in api('/api/requests', None, cookie['staff'])[1] if r.get('confirmedAction') == a5])

    # ---- 9. a stale csrf token: refused, refreshed, then it works
    i7, i8 = new_invoice('PG-7'), new_invoice('PG-8')   # first: any invoice change for a customer invalidates its live proposals
    a7 = prepare('customer_demo_01', i7, days=28, key='p7')
    a8 = prepare('customer_demo_01', i8, days=7, key='p8')
    b.goto(BASE + '/#/actions/' + a7); b.wait("document.querySelector('[data-testid=action-page]')?.dataset.action === %s && !!document.querySelector('#act-confirm')" % json.dumps(a7))
    b.js("S.session.csrf = 'a-stale-token'")
    click('#act-confirm')
    check('9 a stale token is refused and nothing is submitted', b.wait("!!document.querySelector('[data-testid=notice]')") and 'security token' in text('[data-testid=notice]') and has('#act-confirm') and
          not [r for r in api('/api/requests', None, cookie['staff'])[1] if r.get('confirmedAction') == a7], text('[data-testid=notice]')[:160])
    click('#act-confirm')
    ok9 = b.wait("document.querySelector('[data-testid=action-page]')?.dataset.status === 'executed'")
    check('9 after the token is refreshed, the same page submits', ok9, '' if ok9 else text()[:600] + str(b.js('JSON.stringify([S.session.csrf, ACT.flight, ACT.notice])')))
    # ---- 10. the AI Agent identity: no confirm offered
    b.js("document.querySelector('#signout').click()"); b.wait("!!document.querySelector('#signin')")
    b.goto(BASE + '/#/actions/' + a8)
    b.wait("!!document.querySelector('#signin')")
    sign_in(codes[('agent', 'access')])
    check('10 the AI Agent identity sees the page and is offered no submit or cancel', b.wait("!!document.querySelector('[data-testid=action-page]')") and not has('#act-confirm') and not has('#act-cancel'), text('[data-testid=controls]')[:240])
    check('11 no page error was thrown', not b.errors(), b.errors()[:2])
    b.close()
finally:
    server.terminate()
    shutil.rmtree(tmp, ignore_errors=True)
print('%d/%d passed' % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
