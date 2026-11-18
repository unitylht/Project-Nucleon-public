"""Shared helpers for the Owner-page browser checks (deploy/review_page_check.py, deploy/dashboard_page_check.py): a scratch records server the check starts itself
(deploy/delegation_check_server.py: fictional data, a throwaway database, a free loopback port), API calls with the page's headers, and a small page driver on deploy/cdp_min.py.
Fictional data only. Standard library only."""
import json, os, re, sqlite3, subprocess, sys, tempfile, time, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_min import Browser, free_port

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT + '/prototype')
IDS = {k: 'customer_demo_' + k for k in ('bayview', 'northside', 'lakeside', 'harbourline', 'cityside', 'riverside')}


class Checks:
    def __init__(self, width=100):
        self.results, self.width = [], width

    def __call__(self, name, ok, detail=''):
        self.results.append(bool(ok))
        print(('PASS ' if ok else 'FAIL ') + name.ljust(self.width) + str(detail)[:200])

    def finish(self):
        print('%d/%d passed' % (sum(self.results), len(self.results)))
        return 0 if all(self.results) else 1


class Scratch:
    """One scratch records server: its own database and port, its codes read from its log."""
    def __init__(self, tmp, tag):
        self.tmp, self.port, self.log = tmp, free_port(), os.path.join(tmp, tag + '.log')
        self.base = 'http://127.0.0.1:%d' % self.port
        self.db_path = os.path.join(tmp, tag + '.db')
        self.proc = subprocess.Popen([sys.executable, ROOT + '/deploy/delegation_check_server.py', self.db_path, str(self.port)], stdout=open(self.log, 'w'), stderr=subprocess.STDOUT, cwd=ROOT)
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

    def api(self, path, body=None, cookie=None, key=None, headers=None, method=None):
        h = {**(headers or {})}
        if cookie: h['Cookie'] = cookie
        if key: h['Idempotency-Key'] = key
        if body is not None: h['Content-Type'] = 'application/json'; h['Origin'] = self.base
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode() if body is not None else None, headers=h, method=method)
        try:
            r = urllib.request.urlopen(req, timeout=20)
        except urllib.error.HTTPError as e:
            r = e
        with r:
            return r.status, json.loads(r.read()), r.headers

    def owner(self, path, body=None, key=None, method=None):
        """An Owner write as the page sends it: its cookie, Origin and csrf token."""
        csrf = self.api('/api/session', None, self.cookie['owner'])[1]['csrf']
        return self.api(path, body, self.cookie['owner'], key, {'X-Nucleon-CSRF': csrf}, method)

    def resolve(self, args, key):
        s, b, _ = self.api('/api/tools/resolveDecision', {'args': {'recommendation': 'approve', 'reasoning': 'Fictional page check.', **args}}, self.cookie['staff'], key)
        assert s == 200 and b['ok'], b
        return b['result']

    def staff(self, path, body, key):
        """A Staff write as the page sends it: the Staff cookie, Origin and csrf token."""
        csrf = self.api('/api/session', None, self.cookie['staff'])[1]['csrf']
        return self.api(path, body, self.cookie['staff'], key, {'X-Nucleon-CSRF': csrf})

    def new_customer(self, name):
        s, rec, _ = self.api('/api/records/customers', {'name': name + ' (fictional)'}, self.cookie['staff'], 'cust-' + name)
        assert s == 200, rec
        return rec['record']['id']

    def asked_trial(self, name, order='600.00', terms=14):
        """A new customer's trial credit: the agent asks Staff for a deposit and the business identity. Returns (customer id, the resolve result)."""
        cid = self.new_customer(name)
        out = self.resolve({'kind': 'trial_credit', 'customerId': cid, 'orderAmount': order, 'termsDays': terms}, 'trial-' + name)
        assert out['status'] == 'gathering_evidence', out
        return cid, out

    def approved_trial(self, name):
        """A trial credit the agent approved after Staff confirmed a bank deposit and the identity (as deploy/delegation_page_check.py does)."""
        cid, out = self.asked_trial(name)
        items = [{'kind': 'deposit', 'basis': 'bank', 'amount': '150.00', 'receivedDate': '2026-10-23', 'reference': 'DEP-' + name},
                 {'kind': 'business_identity', 'basis': 'document', 'registration': 'Registration ' + name + ' (fictional)', 'tradingName': name + ' (fictional)'}]
        s, b, _ = self.staff('/api/actions/' + out['actionId'] + '/evidence', {'version': 1, 'items': items}, 'ev-' + name)
        assert s == 200, b
        return out['caseId']

    def case(self, case_id):
        return self.api('/api/decision-cases/' + case_id, None, self.cookie['owner'])[1]

    def sql(self, query, *args):
        con = sqlite3.connect(self.db_path)
        try:
            return con.execute(query, args).fetchall()
        finally:
            con.close()

    def stop(self):
        self.proc.terminate()


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
    def fill(self, sel, value): return self.b.js("(() => { const e = document.querySelector(%s); if (!e) return false; e.value = %s; e.dispatchEvent(new Event('input', { bubbles: true })); return true })()" % (json.dumps(sel), json.dumps(value)))
    def go(self, hash_): self.b.js("location.hash = %s" % json.dumps(hash_))
    def open(self, hash_=''): self.b.goto(self.s.base + '/' + hash_)
    def sign_in(self, role):
        self.wait("!!document.querySelector('#signin')")
        self.b.js("(() => { const i = document.querySelector('#code'); i.value = %s; document.querySelector('#signin').requestSubmit(); return true })()" % json.dumps(self.s.codes[(role, 'access')]))
        return self.wait("!!document.querySelector('header.top')")
    def sign_out(self):
        self.b.js("document.querySelector('#signout').click()"); self.wait("!!document.querySelector('#signin')")
    def phone(self, on=True):
        """Emulate a 390 px wide phone (or back to the desktop window)."""
        if on: self.b.cmd('Emulation.setDeviceMetricsOverride', width=390, height=844, deviceScaleFactor=2, mobile=True)
        else: self.b.cmd('Emulation.clearDeviceMetricsOverride')
        time.sleep(0.3)
    def no_hscroll(self):
        return self.b.js("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1 && document.body.scrollWidth <= document.documentElement.clientWidth + 1")
    def width_info(self):
        return self.b.js("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
