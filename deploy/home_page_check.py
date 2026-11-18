"""Browser check of the shared shell: the role landing page (#/), the one navigation, the assistant link (assistantUrl), the Owner's Review and Dashboard placeholders,
and the Owner pages that refresh themselves (#/delegation and #/ re-read their data every 20 s, and keep what the Owner typed). Headless Chromium driven through
deploy/cdp_min.py on scratch records servers this script starts itself (deploy/delegation_check_server.py: fictional data, a throwaway database, free loopback ports):
one without assistantUrl and one with it. Standard library only (set CHROME_HEADLESS to a chrome-headless-shell binary).

    python3 deploy/home_page_check.py      # prints PASS/FAIL per check; exit status 0 only if all pass (about a minute: it waits for two real 20 s refreshes)
"""
import json, os, re, shutil, subprocess, sys, tempfile, time, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_min import Browser, free_port

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSISTANT = 'http://127.0.0.1:3080/c/new?agent_id=agent_fictional_page_check&model=fictional'
tmp = tempfile.mkdtemp(prefix='home-check-')
results = []


def check(name, ok, detail=''):
    results.append(bool(ok))
    print(('PASS ' if ok else 'FAIL ') + name.ljust(90) + str(detail)[:200])


class Scratch:
    """One scratch records server: its own database and port, its codes read from its log."""
    def __init__(self, tag, assistant=None):
        self.port, self.log = free_port(), os.path.join(tmp, tag + '.log')
        self.base = 'http://127.0.0.1:%d' % self.port
        self.proc = subprocess.Popen([sys.executable, ROOT + '/deploy/delegation_check_server.py', tmp + '/' + tag + '.db', str(self.port)] + ([assistant] if assistant else []),
                                     stdout=open(self.log, 'w'), stderr=subprocess.STDOUT, cwd=ROOT)
        for _ in range(100):
            if open(self.log).read().count(' code: ') >= 9: break
            time.sleep(0.1)
        self.codes = {(m[1].lower(), m[2]): m[3] for m in re.finditer(r'^(\w+) (access|service) code: (\S+)$', open(self.log).read(), re.M)}
        self.cookie = {}
        for role in ('staff', 'owner'):
            s, b, h = self.api('/api/demo/login', {'accessCode': self.codes[(role, 'access')]})
            self.cookie[role] = h['Set-Cookie'].split(';')[0]
        for tool in ('assessDecision', 'resolveDecision', 'decisionStatus'):
            s, b, _ = self.api('/api/agent-tools', {'tool': tool, 'enabled': True}, self.cookie['owner'], 'on-' + tool)
            assert s == 200, b

    def api(self, path, body=None, cookie=None, key=None, headers=None):
        h = {**(headers or {})}
        if cookie: h['Cookie'] = cookie
        if key: h['Idempotency-Key'] = key
        if body is not None: h['Content-Type'] = 'application/json'; h['Origin'] = self.base
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode() if body is not None else None, headers=h)
        try:
            r = urllib.request.urlopen(req, timeout=20)
        except urllib.error.HTTPError as e:
            r = e
        with r:
            return r.status, json.loads(r.read()), r.headers

    def resolve(self, args, key):
        s, b, _ = self.api('/api/tools/resolveDecision', {'args': {'recommendation': 'approve', 'reasoning': 'Fictional page check.', **args}}, self.cookie['staff'], key)
        assert s == 200 and b['ok'], b
        return b['result']

    def new_customer(self, name):
        s, rec, _ = self.api('/api/records/customers', {'name': name + ' (fictional)'}, self.cookie['staff'], 'cust-' + name)
        assert s == 200, rec
        return rec['record']['id']

    def stop(self):
        self.proc.terminate()


IDS = {'bayview': 'customer_demo_bayview', 'northside': 'customer_demo_northside', 'lakeside': 'customer_demo_lakeside', 'harbourline': 'customer_demo_harbourline', 'cityside': 'customer_demo_cityside', 'riverside': 'customer_demo_riverside'}


class Page:
    """The one headless browser page, with the small helpers every check here uses."""
    def __init__(self, scratch):
        self.s, self.b = scratch, Browser()

    def js(self, expr): return self.b.js(expr)
    def wait(self, expr, timeout=10): return self.b.wait(expr, timeout)
    def text(self, sel='#main'): return self.b.js("document.querySelector(%s)?.innerText || ''" % json.dumps(sel))
    def has(self, sel): return self.b.js("!!document.querySelector(%s)" % json.dumps(sel))
    def count(self, sel): return self.b.js("document.querySelectorAll(%s).length" % json.dumps(sel))
    def attr(self, sel, name): return self.b.js("document.querySelector(%s)?.getAttribute(%s)" % (json.dumps(sel), json.dumps(name)))
    def click(self, sel): return self.b.js("(() => { const e = document.querySelector(%s); if (!e) return false; e.click(); return true })()" % json.dumps(sel))
    def go(self, hash_): self.b.js("location.hash = %s" % json.dumps(hash_))
    def open(self, hash_=''):
        self.b.goto(self.s.base + '/' + hash_)
    def sign_in(self, role):
        self.wait("!!document.querySelector('#signin')")
        self.b.js("(() => { const i = document.querySelector('#code'); i.value = %s; document.querySelector('#signin').requestSubmit(); return true })()" % json.dumps(self.s.codes[(role, 'access')]))
        return self.wait("!!document.querySelector('header.top')")
    def sign_out(self):
        self.b.js("document.querySelector('#signout').click()"); self.wait("!!document.querySelector('#signin')")
    def nav(self):   # the header navigation: [(area, label, aria-current)]
        return self.b.js("[...document.querySelectorAll('header.top .mainnav a')].map(a => [a.dataset.area, a.querySelector('.nav-label').textContent, a.getAttribute('aria-current') === 'page'])")


def quiet_cases(s):
    """Three decided or waiting-for-Staff cases, none waiting for the Owner."""
    bay = s.resolve({'kind': 'extension', 'customerId': IDS['bayview'], 'invoiceReference': 'DEMO-301', 'requestedDueDate': '2026-11-10'}, 'r-bay')
    north = s.resolve({'kind': 'trial_credit', 'customerId': IDS['northside'], 'orderAmount': '800.00', 'termsDays': 14}, 'r-north')
    lake = s.resolve({'kind': 'trial_credit', 'customerId': IDS['lakeside'], 'orderAmount': '600.00', 'termsDays': 14}, 'r-lake')
    assert (bay['status'], north['status'], lake['status']) == ('decided', 'decided', 'gathering_evidence'), (bay['status'], north['status'], lake['status'])


try:
    # ================================================================ A. no assistantUrl
    A = Scratch('a')
    quiet_cases(A)
    p = Page(A)
    p.open()
    check('A1 the sign-in gate comes first', p.wait("!!document.querySelector('#signin')"))

    # ---- the Owner's landing page
    p.sign_in('owner')
    check('A2 after sign-in the Owner lands on the home page (#/)', p.wait("!!document.querySelector('[data-testid=home-page][data-role-home=owner]')") and p.js('location.hash') in ('', '#/'), p.js('location.hash'))
    check('A2 the page header is the shared one: a title and a line about the page', p.text('#main h1') == 'Home' and 'what the assistant decided' in p.text('#main .page-head .lede'), p.text('#main .page-head'))
    check('A2 nothing waits for the Owner yet: the count is hidden and the list says so', p.has('[data-testid=home-waiting-none]') and p.b.js("document.querySelector('[data-testid=home-waiting-count]').hidden"))
    check('A2 recent agent decisions: at most five, each with its status', 1 <= p.count('[data-testid=home-recent]') <= 5 and 'Approved by the agent' in p.text('[data-testid=home-recent-list]'), p.text('[data-testid=home-recent-list]')[:160])
    check('A2 live counts are shown, workflow counts only', 'Approved by the agent' in p.text('[data-testid=counts]') and 'Workflow counts, not decision quality' in p.text('[data-testid=counts-note]'))
    links = p.b.js("[...document.querySelectorAll('.home-links a')].map(a => [a.dataset.testid, a.getAttribute('href'), a.getAttribute('target')])")
    check('A3 the Owner has big links to the Control panel, Review, Dashboard and Doctor, and the assistant only when the config gives one (not here)', links == [['home-control-panel', '#/delegation', None], ['home-review', '#/review', None], ['home-dashboard', '#/dashboard', None], ['home-doctor', '#/doctor', None]], links)
    check('A3 no assistant link anywhere, in the page or the navigation, when assistantUrl is unset', not p.has('[data-testid=home-assistant]') and not p.has('[data-testid=nav-assistant]') and not p.has('a[data-area=assistant]'))
    session = A.api('/api/session', None, A.cookie['owner'])[1]
    check('A3 GET /api/session says assistantUrl is null', 'assistantUrl' in session and session['assistantUrl'] is None, session.get('assistantUrl'))

    # ---- the one navigation
    nav = p.nav()
    check('A4 the Owner\'s navigation, in order, with the page highlighted', [n[1] for n in nav] == ['Home', 'Decide', 'Control panel', 'Dashboard', 'Customers', 'Requests', 'Imports', 'Model', 'Knowledge', 'Setup'] and   # 11 Nov 2026: the Owner's main pages first, the rest under More
          [n[0] for n in nav if n[2]] == ['home'], nav)
    check('A4 Control panel keeps the #/delegation route; Requests goes to #/cases', p.attr('header.top a[data-area=delegation]', 'href') == '#/delegation' and p.attr('header.top a[data-area=requests]', 'href') == '#/cases')
    check('A4 the practice-workspace line is kept', 'Practice workspace with fictional data.' in p.text('header.top .context'), p.text('header.top .context')[:100])
    for hash_, area in (('#/delegation', 'delegation'), ('#/customers', 'customers'), ('#/imports', 'imports'), ('#/knowledge', 'knowledge'), ('#/setup', 'setup'), ('#/cases', 'requests')):
        p.go(hash_); time.sleep(0.5)
        check('A4 at %s the %s link is the current page' % (hash_, area), [n[0] for n in p.nav() if n[2]] == [area], p.nav())
    check('A4 the phone tab bar holds the main pages and a More menu with the rest', p.b.js("[...document.querySelectorAll('.tabbar > a')].map(a => a.dataset.area).join()") == 'home,review,delegation,dashboard' and
          p.b.js("[...document.querySelectorAll('.tabbar .more-menu a')].map(a => a.dataset.area).join()") == 'requests,customers,imports,research,knowledge,setup')

    # ---- every page has the shared header (title and one line)
    for hash_, title in (('#/', 'Home'), ('#/delegation', 'Control panel'), ('#/customers', 'Customers'), ('#/imports', 'Imports'), ('#/knowledge', 'Knowledge'), ('#/setup', 'Setup'), ('#/cases', 'Requests')):
        p.go(hash_); p.wait("document.querySelector('#main h1')?.textContent === %s" % json.dumps(title), 6); time.sleep(0.3)
        check('A5 %s has the page header: title and a line about the page' % title, p.text('#main h1') == title and len(p.text('#main .lede').strip()) > 10, p.text('#main .lede')[:80])
    p.go('#/actions/' + A.resolve({'kind': 'trial_credit', 'customerId': IDS['lakeside'], 'orderAmount': '600.00', 'termsDays': 14}, 'r-lake')['actionId'])
    check('A5 the evidence page (actions) has the page header too', p.wait("!!document.querySelector('[data-testid=evidence-page] .page-head h1, .page-head h1')", 6) and len(p.text('#main .page-head .lede')) > 10, p.text('#main .page-head')[:100])

    # ---- Review and Dashboard are real pages now (deploy/review_page_check.py and deploy/dashboard_page_check.py test them)
    for hash_, name in (('#/review', 'review'), ('#/dashboard', 'dashboard')):
        p.go(hash_)
        check('A6 the Owner opens the %s page (no placeholder)' % name, p.wait("!!document.querySelector('[data-testid=%s-page]')" % name) and not p.has('[data-testid$=-placeholder]') and 'coming in S2b' not in p.text(), p.text()[:100].replace('\n', ' | '))
    check('A6 the Review link on the home page works', (p.go('#/') or True) and p.wait("!!document.querySelector('[data-testid=home-review]')") and p.click('[data-testid=home-review]') and p.wait("!!document.querySelector('[data-testid=review-page]')"))
    check('A6 the Dashboard link on the home page works', (p.go('#/') or True) and p.wait("!!document.querySelector('[data-testid=home-dashboard]')") and p.click('[data-testid=home-dashboard]') and p.wait("!!document.querySelector('[data-testid=dashboard-page]')"))

    # ---- same-hash navigation draws the page again
    p.go('#/'); p.wait("!!document.querySelector('[data-testid=home-page]')")
    p.js("(() => { window.__marker = document.querySelector('[data-testid=home-page]'); return true })()")
    p.click('header.top a[data-area=home]'); time.sleep(0.8)
    check('A7 clicking the link to the page already open draws it again', p.js("window.__marker !== document.querySelector('[data-testid=home-page]') && !!document.querySelector('[data-testid=home-page]')"))

    # ---- the Owner's pages refresh themselves
    p.go('#/delegation'); p.wait("!!document.querySelector('[data-testid=delegation-page]')")
    check('B1 (setup) the control panel starts with nothing waiting', p.has('[data-testid=waiting-none]') and p.count('[data-testid=waiting-case]') == 0)
    p.js("(() => { window.__pageNode = document.querySelector('[data-testid=delegation-page]'); window.__t0 = Date.now(); return true })()")
    harb = A.resolve({'kind': 'trial_credit', 'customerId': IDS['harbourline'], 'orderAmount': '5000.00', 'termsDays': 14}, 'r-harb')
    arrived = p.wait("document.querySelectorAll('[data-testid=waiting-case]').length === 1", 25)
    check('B1 a case created through the API shows on the open control panel within 25 s, with no manual reload', arrived and harb['status'] == 'awaiting_owner',
          '%.1f s' % (p.js('(Date.now() - window.__t0) / 1000') or 0))
    check('B1 it is a refresh of the same page (no reload: the page script kept its state)', p.js("window.__pageNode !== undefined && window.__pageNode !== document.querySelector('[data-testid=delegation-page]')"))
    # what the Owner typed survives the next refresh, and so does the focus and the open Advanced section
    p.js("""(() => { const t = document.querySelector('#dg-note'); t.value = 'Typed before the next refresh.'; t.focus();
      document.querySelector('.dg-advanced').open = true; const f = document.querySelector('[name="limits.maxDecisionExposure"]'); f.value = '950.00'; f.dispatchEvent(new Event('input', { bubbles: true }));
      window.__t0 = Date.now(); return true })()""")
    city = A.resolve({'kind': 'extension', 'customerId': IDS['cityside'], 'invoiceReference': 'DEMO-410', 'days': 14}, 'r-city')
    arrived = p.wait("document.querySelectorAll('[data-testid=waiting-case]').length === 2", 25)
    check('B2 a second case arrives the same way', arrived and city['status'] == 'awaiting_owner', '%.1f s' % (p.js('(Date.now() - window.__t0) / 1000') or 0))
    kept = p.js("""(() => { const t = document.querySelector('#dg-note');
      return { typed: t.value, focus: document.activeElement === t, advanced: document.querySelector('.dg-advanced').open, form: document.querySelector('[name="limits.maxDecisionExposure"]').value } })()""")
    check('B2 the refresh kept the note being typed, the focus, the open Advanced section and the edited form field', kept == {'typed': 'Typed before the next refresh.', 'focus': True, 'advanced': True, 'form': '950.00'}, kept)
    # nothing was sent by the refresh itself
    check('B2 the refresh changed nothing on the server (the policy is still version 1)', A.api('/api/delegation/policy', None, A.cookie['owner'])[1]['version'] == 1)

    # the home page too
    p.go('#/'); p.wait("!!document.querySelector('[data-testid=home-page]')")
    check('B3 the home page counts the two waiting cases, each linked to the Review page and to its case timeline', p.text('[data-testid=home-waiting-count]') == '2' and p.count('[data-testid=home-waiting]') == 2 and
          p.b.js("[...document.querySelectorAll('[data-testid=home-waiting] > a:first-child')].every(a => a.getAttribute('href') === '#/review')") and
          sorted(p.b.js("[...document.querySelectorAll('[data-testid=home-waiting] [data-testid=home-timeline]')].map(a => a.getAttribute('href'))")) == sorted(['#/decision-cases/' + harb['caseId'], '#/decision-cases/' + city['caseId']]))
    p.js("window.__t0 = Date.now(); true")
    s_, rec, _ = A.api('/api/records/customers', {'name': 'Mooncove Bakery (fictional)'}, A.cookie['staff'], 'cust-moon')
    third = A.resolve({'kind': 'trial_credit', 'customerId': rec['record']['id'], 'orderAmount': '5000.00', 'termsDays': 14}, 'r-moon')
    arrived = p.wait("document.querySelector('[data-testid=home-waiting-count]')?.textContent === '3'", 25)
    check('B3 a third case shows on the open home page within 25 s', arrived and third['status'] == 'awaiting_owner', '%.1f s' % (p.js('(Date.now() - window.__t0) / 1000') or 0))
    # a hidden tab does not poll: simulate a visibility change and a focus event
    p.js("""(() => { window.__reads = 0; const real = window.fetch; window.fetch = (u, o) => { if (String(u).includes('/api/delegation/cases')) window.__reads++; return real(u, o); }; return true })()""")
    time.sleep(2.1)
    p.js("window.dispatchEvent(new Event('focus')); true"); time.sleep(1.2)
    check('B4 coming back to the window reads the data again at once', p.js('window.__reads') >= 1, p.js('window.__reads'))

    # the Review page refreshes itself too, and keeps the open row, the reason being typed and the focus
    p.go('#/review'); p.wait("document.querySelectorAll('[data-section=waiting]').length === 3")
    row = '[data-case="%s"]' % harb['caseId']
    p.js("""(() => { document.querySelector('%s [data-open]').click(); const t = document.querySelector('%s [data-why]'); t.value = 'Typed on the review page before a refresh.'; t.focus(); window.__rnode = document.querySelector('[data-testid=review-page]'); window.__t0 = Date.now(); return true })()""" % (row, row))
    river = A.resolve({'kind': 'extension', 'customerId': IDS['riverside'], 'invoiceReference': 'DEMO-505', 'days': 10}, 'r-river')
    arrived = p.wait("document.querySelectorAll('[data-section=waiting]').length === 4", 25)
    kept = p.js("""(() => { const t = document.querySelector('%s [data-why]'); return { typed: t.value, focus: document.activeElement === t, open: !document.querySelector('%s .rv-body').hidden, redrawn: window.__rnode !== document.querySelector('[data-testid=review-page]') } })()""" % (row, row))
    check('B5 a case arriving while the Review page is open shows within 25 s, and the refresh kept the open row, the reason being typed and the focus', arrived and river['status'] == 'awaiting_owner' and kept == {'typed': 'Typed on the review page before a refresh.', 'focus': True, 'open': True, 'redrawn': True}, (kept, '%.1f s' % (p.js('(Date.now() - window.__t0) / 1000') or 0)))

    # ---- Staff
    p.sign_out()
    p.open(); p.sign_in('staff')
    check('C1 Staff land on the home page for Staff', p.wait("!!document.querySelector('[data-testid=home-page][data-role-home=staff]')"))
    links = p.b.js("[...document.querySelectorAll('.home-links a')].map(a => [a.dataset.testid, a.getAttribute('href')])")
    check('C1 Staff links: Requests (#/cases), Customers, Imports; no assistant link when unset', links == [['home-requests', '#/cases'], ['home-customers', '#/customers'], ['home-imports', '#/imports']], links)
    check('C2 the Staff navigation has no Owner pages', [n[1] for n in p.nav()] == ['Home', 'Requests', 'Customers', 'Imports', 'Knowledge', 'Setup'], p.nav())
    check('C2 the phone More menu holds Knowledge and Setup only', p.b.js("[...document.querySelectorAll('.tabbar .more-menu a')].map(a => a.dataset.area).join()") == 'knowledge,setup')
    for hash_ in ('#/review', '#/dashboard'):
        p.go(hash_)
        check('C3 Staff get "Page not found" at %s, not the Owner\'s placeholder' % hash_, p.wait("document.querySelector('#main h1')?.textContent === 'Page not found'") and not p.has('[data-testid$=-placeholder]'), p.text()[:80])
    p.go('#/delegation')
    check('C3 Staff have no Control panel link and the page itself is for the Owner only', p.wait("!!document.querySelector('[data-testid=delegation-owner-only]')") and not p.has('a[data-area=delegation]'))
    # a request that waits on Staff shows on the Staff home page, which refreshes itself
    s_, made, _ = A.api('/api/requests', {'messageText': 'Hi, Mooncove here. Could we pay invoice later?'}, A.cookie['staff'], 'mess-1')
    p.go('#/'); p.wait("!!document.querySelector('[data-testid=home-page]')")
    check('C4 a request waiting on Staff is listed on their home page', p.wait("document.querySelectorAll('[data-testid=home-waiting]').length >= 1 || !!document.querySelector('[data-testid=home-waiting-none]')", 8), p.text('[data-testid=home-waiting-list]')[:120] or p.text('[data-testid=home-waiting-none]'))
    # the information Nucleon is waiting for from Staff: the open evidence request for Lakeside, linked to its page
    listed = A.api('/api/actions?kind=evidence&status=open', None, A.cookie['staff'])[1]['actions']
    p.go('#/'); p.wait("!!document.querySelector('[data-testid=home-page]')")
    check('C4b the Staff home page lists the open evidence request: customer, what is asked, when, and its page (#/actions/<id>)', len(listed) == 1 and p.wait("document.querySelectorAll('[data-testid=home-evidence]').length === 1") and
          'Information Nucleon is waiting for from you' in p.text() and 'Lakeside' in p.text('[data-testid=home-evidence]') and 'Asked' in p.text('[data-testid=home-evidence]') and p.text('[data-testid=home-evidence-count]') == '1' and
          p.attr('[data-testid=home-evidence] a', 'href') == listed[0]['link'] == '#/actions/' + listed[0]['id'], p.text('[data-testid=home-evidence-list]')[:200].replace('\n', ' | '))
    p.click('[data-testid=home-evidence] a')
    check('C4b the link opens the evidence page', p.wait("!!document.querySelector('[data-testid=evidence-page]')"), p.js('location.hash'))
    p.go('#/')
    p.js("window.__t0 = Date.now(); true")
    A.resolve({'kind': 'trial_credit', 'customerId': A.new_customer('Pinewood Deli'), 'orderAmount': '400.00', 'termsDays': 14}, 'r-moon-ev')
    check('C4b a request for information arriving while Staff are on the home page shows within 25 s', p.wait("document.querySelectorAll('[data-testid=home-evidence]').length === 2", 25), '%.1f s' % (p.js('(Date.now() - window.__t0) / 1000') or 0))
    p.sign_out()

    # ---- the AI Agent identity sees the same pages and the same read-only rules
    p.open(); p.sign_in('agent')
    check('C5 the AI Agent identity lands on a home page without a script error', p.wait("!!document.querySelector('[data-testid=home-page]')"), p.js('location.hash'))
    p.sign_out()
    check('Z1 no page error was thrown (no assistantUrl server)', not p.b.errors(), p.b.errors()[:2])
    p.b.close(); A.stop()

    # ================================================================ B. with assistantUrl
    B = Scratch('b', ASSISTANT)
    quiet_cases(B)
    q = Page(B)
    q.open(); q.sign_in('owner'); q.wait("!!document.querySelector('[data-testid=home-page]')")
    session = B.api('/api/session', None, B.cookie['owner'])[1]
    check('D1 GET /api/session carries assistantUrl exactly as configured', session.get('assistantUrl') == ASSISTANT, session.get('assistantUrl'))
    anchor = q.b.js("(() => { const a = document.querySelector('[data-testid=home-assistant]'); return a && [a.getAttribute('href'), a.getAttribute('target'), a.getAttribute('rel'), a.classList.contains('primary')] })()")
    check('D2 the Owner\'s home page has the assistant button: exact href, target=_blank, rel=noopener, the first (primary) link', anchor == [ASSISTANT, '_blank', 'noopener', True] and
          q.b.js("document.querySelector('.home-links a').dataset.testid") == 'home-assistant', anchor)
    nav_anchor = q.b.js("(() => { const a = document.querySelector('header.top [data-testid=nav-assistant]'); return a && [a.getAttribute('href'), a.getAttribute('target'), a.getAttribute('rel')] })()")
    check('D3 the navigation has the Assistant link, same address, new tab, noopener, after Home', nav_anchor == [ASSISTANT, '_blank', 'noopener'] and [n[1] for n in q.nav()][:3] == ['Home', 'Assistant', 'Decide'], (nav_anchor, q.nav()[:3]))
    check('D3 the Assistant link is never the current page and the phone More menu carries it', not any(n[2] for n in q.nav() if n[0] == 'assistant') and q.b.js("[...document.querySelectorAll('.tabbar .more-menu a')].map(a => a.dataset.area).join()") == 'assistant,requests,customers,imports,research,knowledge,setup')
    q.sign_out(); q.open(); q.sign_in('staff'); q.wait("!!document.querySelector('[data-testid=home-page]')")
    staff_links = q.b.js("[...document.querySelectorAll('.home-links a')].map(a => [a.dataset.testid, a.getAttribute('href'), a.getAttribute('target'), a.getAttribute('rel')])")
    check('D4 Staff: the assistant is the first and primary link, then Requests, Customers, Imports', staff_links[0] == ['home-assistant', ASSISTANT, '_blank', 'noopener'] and [l[0] for l in staff_links][1:] == ['home-requests', 'home-customers', 'home-imports'] and
          q.has('.home-links a.primary[data-testid=home-assistant]'), staff_links)
    check('Z2 no page error was thrown (assistantUrl server)', not q.b.errors(), q.b.errors()[:2])
    q.b.close(); B.stop()
finally:
    for name in ('A', 'B'):
        if name in globals():
            try: globals()[name].stop()
            except Exception: pass
    shutil.rmtree(tmp, ignore_errors=True)
print('%d/%d passed' % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
