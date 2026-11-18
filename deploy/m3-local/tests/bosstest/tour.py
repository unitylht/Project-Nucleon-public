"""Walk the copy as the Owner would, then as Staff: every page, its errors, its text, a screenshot. Read-only pass (nothing is clicked that saves).
    tour.py <base-url> <log-file> <out-dir> [phone]"""
import json, os, re, sys, time
from playwright.sync_api import sync_playwright

base, logf, out = sys.argv[1], sys.argv[2], sys.argv[3]
phone = len(sys.argv) > 4
os.makedirs(out, exist_ok=True)
codes = {(m[1].lower(), m[2]): m[3] for m in re.finditer(r'^(\w+) (access|service) code: (\S+)$', open(logf).read(), re.M)}
report = []

with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={'width': 400, 'height': 800} if phone else {'width': 1280, 'height': 900}, device_scale_factor=1)
    p = ctx.new_page()
    p.set_default_timeout(15000)
    errors = []
    p.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)[:300]))
    p.on('console', lambda m: errors.append('console: ' + m.text[:300]) if m.type == 'error' else None)
    p.on('response', lambda r: errors.append('http %d %s' % (r.status, r.url.replace(base, ''))) if r.status >= 400 else None)

    def sign_in(role):
        ctx.clear_cookies()
        p.goto(base + '/')
        p.wait_for_selector('#signin')
        p.fill('#code', codes[(role, 'access')])
        p.evaluate("document.querySelector('#signin').requestSubmit()")
        p.wait_for_selector('header.top')

    def visit(role, name, hash_, wait=1.6, shot=True):
        errors.clear()
        p.evaluate('location.hash = %s' % json.dumps(hash_))
        time.sleep(wait)
        text = p.evaluate("document.querySelector('#main')?.innerText || ''")
        wide = p.evaluate('document.documentElement.scrollWidth > document.documentElement.clientWidth + 2')
        tag = ('phone-' if phone else '') + role + '-' + name
        if shot:
            p.screenshot(path=os.path.join(out, tag + '.png'), full_page=True)
        report.append({'page': tag, 'hash': hash_, 'errors': list(errors), 'sidewaysScroll': wide, 'chars': len(text),
                       'didNotLoad': "didn't load" in text or 'This page' in text[:60], 'head': re.sub(r'\s+', ' ', text)[:260]})
        return text

    sign_in('owner')
    nav = p.evaluate("[...document.querySelectorAll('header.top nav.mainnav > a, header.top nav.mainnav summary')].map(a => a.innerText.trim())")
    more = p.evaluate("[...document.querySelectorAll('header.top .nav-more-menu a')].map(a => a.innerText.trim())")
    report.append({'page': 'owner-nav', 'top': nav, 'more': more})
    owner_pages = [('home', '#/'), ('decide', '#/review'), ('controlpanel', '#/delegation'), ('dashboard', '#/dashboard'), ('customers', '#/customers'),
                   ('requests', '#/cases'), ('imports', '#/imports'), ('model', '#/research'), ('knowledge', '#/knowledge'), ('setup', '#/setup'),
                   ('quicksetup', '#/quick-setup'), ('doctor', '#/doctor'), ('completeness', '#/completeness')]
    for name, h in owner_pages:
        visit('owner', name, h, wait=2.5 if name in ('quicksetup', 'doctor', 'dashboard') else 1.6)
    # every customer page, every waiting or recent case page: errors only
    ids = p.evaluate("fetch('api/records').then(r => r.json()).then(d => d.customers.map(c => c.id))")
    for i, cid in enumerate(ids):
        visit('owner', 'customer%02d' % i, '#/customers/' + cid, wait=0.9, shot=i < 2)
    cases = p.evaluate("fetch('api/delegation/cases').then(r => r.json()).then(d => d.cases.map(c => [c.caseId, c.status, c.requestId || null]))")
    report.append({'page': 'owner-cases', 'cases': [[c[1], bool(c[2])] for c in cases]})
    for i, (cid, status, rid) in enumerate(cases):
        visit('owner', 'case%02d-%s' % (i, status), '#/decision-cases/' + cid, wait=1.0, shot=i < 3)
        if rid:
            visit('owner', 'request%02d' % i, '#/case/' + rid, wait=1.0, shot=i < 1)
    # the Doctor's six questions
    visit('owner', 'doctor', '#/doctor', wait=2.0, shot=False)
    qs = p.evaluate("[...document.querySelectorAll('[data-question], [data-q], .doctor-q button, button[data-testid^=doctor-q]')].length")
    report.append({'page': 'owner-doctor-questions', 'buttons': qs})
    sign_in('staff')
    nav = p.evaluate("[...document.querySelectorAll('header.top nav.mainnav > a, header.top nav.mainnav summary')].map(a => a.innerText.trim())")
    more = p.evaluate("[...document.querySelectorAll('header.top .nav-more-menu a')].map(a => a.innerText.trim())")
    report.append({'page': 'staff-nav', 'top': nav, 'more': more})
    for name, h in [('home', '#/'), ('requests', '#/cases'), ('customers', '#/customers'), ('imports', '#/imports'), ('knowledge', '#/knowledge'), ('setup', '#/setup'),
                    ('controlpanel', '#/delegation'), ('decide', '#/review'), ('newrequest', '#/cases/new')]:
        visit('staff', name, h)
    b.close()

json.dump(report, open(os.path.join(out, ('phone-' if phone else '') + 'report.json'), 'w'), indent=1)
bad = [r for r in report if r.get('errors') or r.get('sidewaysScroll') or r.get('didNotLoad')]
print(len(report), 'entries;', len(bad), 'with something to look at')
for r in report:
    if 'top' in r: print(r['page'], '| top:', r['top'], '| more:', r['more'])
for r in bad:
    print('-', r['page'], r['hash'], '| sideways' if r['sidewaysScroll'] else '', '| DID NOT LOAD' if r['didNotLoad'] else '', '|', r['errors'][:3], '|', r['head'][:120])
