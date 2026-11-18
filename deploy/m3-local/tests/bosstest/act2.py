"""Second pass as the Owner: the count in the bar, approving with a reason (a waiting case and a held one), where the approval shows, every Doctor question,
the held-customer field by name, a scheduled change in words. Then Staff: Home, a request by the form.
    act2.py <base-url> <log-file> <out-dir>"""
import json, os, re, sys, time
from playwright.sync_api import sync_playwright

base, logf, out = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(out, exist_ok=True)
codes = {(m[1].lower(), m[2]): m[3] for m in re.finditer(r'^(\w+) (access|service) code: (\S+)$', open(logf).read(), re.M)}
def note(step, what): print('[%s] %s\n' % (step, str(what)[:1300].replace('\n', ' / ')))

with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={'width': 1280, 'height': 900})
    p = ctx.new_page(); p.set_default_timeout(12000)
    errors = []
    p.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)[:300]))
    p.on('console', lambda m: errors.append('console: ' + m.text[:300]) if m.type == 'error' else None)
    p.on('response', lambda r: errors.append('http %d %s' % (r.status, r.url.replace(base, ''))) if r.status >= 400 else None)
    p.on('dialog', lambda d: d.accept())
    def go(h, wait=1.5): p.evaluate('location.hash = %s' % json.dumps(h)); time.sleep(wait)
    def text(sel='#main'): return re.sub(r'[ \t]+', ' ', p.evaluate("document.querySelector(%s)?.innerText || ''" % json.dumps(sel)))
    def shot(name): p.screenshot(path=os.path.join(out, name + '.png'), full_page=True)
    def flush(step):
        if errors: note(step + ' ERRORS', list(errors)); errors.clear()
    badge = lambda: p.evaluate("(() => { const e = document.querySelector('header.top [data-count]'); return e ? [e.closest('a').dataset.area, e.textContent, e.hidden] : null })()")
    def sign_in(role):
        ctx.clear_cookies(); p.goto(base + '/'); p.wait_for_selector('#signin'); p.fill('#code', codes[(role, 'access')]); p.evaluate("document.querySelector('#signin').requestSubmit()"); p.wait_for_selector('header.top'); time.sleep(2.5)

    sign_in('owner')
    note('badge on Home', badge()); go('#/dashboard', 2); note('badge on Dashboard', badge()); shot('home-nav')
    go('#/review', 2)
    rows = p.evaluate("[...document.querySelectorAll('[data-section=waiting]')].map(r => [r.dataset.case, r.innerText.replace(/\\s+/g, ' ').slice(0, 200)])")
    note('waiting rows', rows)
    for kind, pick in (('plain', [r for r in rows if 'hold' not in r[1].lower()]), ('held', [r for r in rows if 'hold' in r[1].lower()])):
        if not pick: continue
        cid = pick[0][0]
        p.click('[data-case="%s"] [data-open]' % cid); time.sleep(0.6)
        note(kind + ' open: controls', p.evaluate("[...document.querySelectorAll('[data-case=\"%s\"] .dg-decide label, [data-case=\"%s\"] .dg-decide button, [data-case=\"%s\"] .dg-decide input')].map(e => (e.tagName + ':' + (e.innerText || e.name || e.value || '')).slice(0, 90))" % (cid, cid, cid)))
        p.fill('#rv-why-' + cid, 'Long-standing customer, one-off delay')
        p.click('[data-case="%s"] [data-act=approve]' % cid); time.sleep(2)
        note(kind + ' approved', {'error': text('[data-case="%s"] [data-error]' % cid), 'row now': text('[data-case="%s"]' % cid)[:420], 'top notice': text('.callout')[:300]}); flush(kind + ' approve')
        go('#/decision-cases/' + cid, 1.8); note(kind + ' request page after approval', text()[:1500]); shot('case-' + kind); flush(kind + ' case page')
        go('#/review', 1.8)
    note('badge after deciding', badge())

    go('#/doctor', 2.5)
    qs = p.evaluate("[...document.querySelectorAll('[data-testid=dr-question]')].map(b => b.innerText.trim())")
    for i, q in enumerate(qs):
        p.evaluate("document.querySelectorAll('[data-testid=dr-question]')[%d].click()" % i); time.sleep(2.2)
        note('doctor: ' + q, text('[data-testid=dr-answer]')[:1200]); flush('doctor %d' % i)
    shot('doctor')
    href = p.evaluate("document.querySelector('[data-testid=dr-try]')?.getAttribute('href') || null")
    if href:
        go(href, 3); note('doctor suggestion in Quick setup', text('[data-testid=qs-from-doctor]') + ' || ' + text('[data-testid=qs-preview]')[:700]); shot('qs-from-doctor'); flush('qs try')

    go('#/delegation', 2.5)
    note('summary: never decides', p.evaluate("[...document.querySelectorAll('[data-testid=policy-summary] .fact')].map(f => f.innerText.replace(/\\n/g, ': ')).filter(t => /never decides/.test(t))"))
    p.evaluate("document.querySelector('.dg-advanced').open = true")
    note('hold field', p.input_value('#dg-hold'))
    p.fill('#dg-hold', p.input_value('#dg-hold') + ', customer 0002, Nobody Pty'); p.click('#dg-save'); time.sleep(2)
    note('save with an unknown name', {'errors': p.evaluate("[...document.querySelectorAll('#dg-form .error:not(:empty)')].map(e => e.innerText)"), 'notice': text('[data-testid=notice]')}); errors.clear()
    p.evaluate("document.querySelector('.dg-advanced').open = true")
    p.fill('#dg-hold', p.input_value('#dg-hold').replace(', Nobody Pty', '')); p.click('#dg-save'); time.sleep(2)
    note('save with names', {'errors': p.evaluate("[...document.querySelectorAll('#dg-form .error:not(:empty)')].map(e => e.innerText)"), 'notice': text('[data-testid=notice]'),
                             'summary': p.evaluate("[...document.querySelectorAll('[data-testid=policy-summary] .fact')].map(f => f.innerText.replace(/\\n/g, ': ')).filter(t => /never decides/.test(t))")}); flush('hold save')
    p.fill('#dg-ext-days', '45'); p.fill('#dg-sched-at', '2026-12-01'); p.fill('#dg-sched-revert', '2027-01-05'); p.click('[data-testid=schedule-add]'); time.sleep(2)
    note('schedule row', text('[data-testid=schedules-pending]')); flush('schedule'); shot('controlpanel')
    go('#/research', 2.5); p.select_option('#own-customer', index=1); time.sleep(0.6)
    note('own invoices', p.evaluate("[...document.querySelectorAll('#own-invoice option')].map(o => o.textContent).slice(0, 5)")); shot('model')

    sign_in('staff')
    note('staff badge', badge()); note('staff home', text()[:900]); flush('staff home')
    go('#/cases/new', 2); note('staff new request form', text()[:1200]); shot('staff-new'); flush('staff new')
    b.close()
