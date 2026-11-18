"""Use the copy as the Owner would: decide, decline without a reason, override, change a rule, ask the Doctor, add own decisions, fit the model. Prints what happened.
    act.py <base-url> <log-file> <out-dir>"""
import json, os, re, sys, time
from playwright.sync_api import sync_playwright

base, logf, out = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(out, exist_ok=True)
codes = {(m[1].lower(), m[2]): m[3] for m in re.finditer(r'^(\w+) (access|service) code: (\S+)$', open(logf).read(), re.M)}
notes = []
def note(step, what): notes.append((step, what)); print('[%s] %s' % (step, str(what)[:700]))

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
    def toast(): return text('.toast, [role=status].toast, .toasts')[:200]

    p.goto(base + '/'); p.wait_for_selector('#signin'); p.fill('#code', codes[('owner', 'access')]); p.evaluate("document.querySelector('#signin').requestSubmit()"); p.wait_for_selector('header.top')
    time.sleep(1.5)
    note('nav', {'count on Decide': p.evaluate("document.querySelector('header.top a[data-area=review] [data-count]')?.textContent || null"), 'hidden': p.evaluate("document.querySelector('header.top a[data-area=review] [data-count]')?.hidden")})
    # More menu opens and navigates
    p.click('header.top .nav-more summary'); time.sleep(0.3); shot('more-open')
    note('more', p.evaluate("[...document.querySelectorAll('header.top .nav-more-menu a')].map(a => a.innerText.trim() + (a.offsetParent ? '' : ' (not visible)'))"))
    p.click('header.top .nav-more-menu a[data-area=research]'); time.sleep(1.5)
    note('more->model', {'hash': p.evaluate('location.hash'), 'more marked current': p.evaluate("document.querySelector('header.top .nav-more summary').className"), 'still open': p.evaluate("!!document.querySelector('header.top .nav-more[open]')")})
    flush('nav')

    # ---- Decide
    go('#/review', 2)
    rows = p.evaluate("[...document.querySelectorAll('[data-testid=review-row], [data-section]')].map(r => [r.dataset.case || r.dataset.request, r.dataset.section, r.innerText.replace(/\\s+/g, ' ').slice(0, 330)])")
    for r in rows: note('decide row', r)
    shot('decide-before')
    waiting = [r for r in rows if r[1] and r[1].startswith('waiting') and r[0]]
    auto = [r for r in rows if r[1] == 'auto']
    def open_row(cid):
        p.click('[data-case="%s"] [data-open]' % cid); time.sleep(0.6)
        return text('[data-case="%s"]' % cid)
    if waiting:
        cid = waiting[0][0]
        note('open waiting 1', open_row(cid)); shot('decide-open')
        # decline with no reason: what does it say?
        p.click('[data-case="%s"] [data-act=decline]' % cid); time.sleep(1)
        note('decline, no reason', {'error': text('[data-case="%s"] [data-error]' % cid), 'toast': toast()})
        still = p.evaluate("!!document.querySelector('[data-case=\"%s\"][data-section^=waiting]')" % cid)
        if still:
            p.fill('#rv-why-' + cid, 'Too long for this customer')
            p.click('[data-case="%s"] [data-act=decline]' % cid); time.sleep(1.5)
        note('declined', {'toast': toast(), 'row now': text('[data-case="%s"]' % cid)[:300]}); flush('decline')
    if len(waiting) > 1:
        cid = waiting[1][0]
        note('open waiting 2', open_row(cid)[:900])
        p.click('[data-case="%s"] [data-act=approve]' % cid); time.sleep(1.8)
        note('approved', {'toast': toast(), 'error': text('[data-case="%s"] [data-error]' % cid), 'row now': text('[data-case="%s"]' % cid)[:400]}); flush('approve')
    held = [r for r in waiting[2:] if 'hold' in r[2].lower()]
    if held:
        cid = held[0][0]
        note('open held', open_row(cid)[:900])
        p.click('[data-case="%s"] [data-act=approve]' % cid); time.sleep(1.8)
        note('approved held', {'toast': toast(), 'error': text('[data-case="%s"] [data-error]' % cid), 'row now': text('[data-case="%s"]' % cid)[:400]}); flush('approve held')
    if auto:
        cid = auto[0][0]
        note('open auto', open_row(cid)[:900])
        p.click('[data-case="%s"] [data-act=override]' % cid); time.sleep(1)
        note('override asked', {'error': text('[data-case="%s"] [data-error]' % cid), 'confirm': text('[data-testid=override-confirm]')})
        if not p.evaluate("!!document.querySelector('[data-testid=override-confirm]')"):
            p.fill('#rv-why-' + cid, 'I know this customer'); p.click('[data-case="%s"] [data-act=override]' % cid); time.sleep(1)
            note('override asked 2', text('[data-testid=override-confirm]'))
        if p.evaluate("!!document.querySelector('[data-testid=act-override-confirm]')"):
            p.click('[data-testid=act-override-confirm]'); time.sleep(1.8)
        note('overridden', {'toast': toast(), 'row now': text('[data-case="%s"]' % cid)[:400]}); flush('override')
    go('#/review', 2); shot('decide-after'); note('decide after', text()[:1500])
    go('#/', 2); note('home after', text()[:900]); flush('home')

    # ---- Control panel: change one number and save; a customer rule; a schedule
    go('#/delegation', 2.5)
    note('policy state', text('[data-testid=policy-state]') + ' || ' + text('[data-testid=policy-summary]')[:900])
    before = p.input_value('#dg-ext-days')
    p.fill('#dg-ext-days', '60'); p.click('#dg-save'); time.sleep(2)
    note('saved days 60 (was %s)' % before, {'notice': text('[data-testid=notice]'), 'form error': text('#dg-form .form-error'), 'state': text('[data-testid=policy-state]')}); flush('save policy')
    p.fill('#dg-max-decision', 'abc'); p.click('#dg-save'); time.sleep(1.5)
    note('bad amount', {'errors': p.evaluate("[...document.querySelectorAll('#dg-form .error:not(:empty)')].map(e => e.innerText)"), 'notice': text('[data-testid=notice]')}); errors.clear()
    go('#/review', 1); go('#/delegation', 2.5)
    opts = p.evaluate("[...document.querySelectorAll('#dg-rule-cust option')].map(o => o.value).filter(Boolean)")
    if opts:
        p.select_option('#dg-rule-cust', opts[0]); p.fill('#dg-rule-days', '10'); p.click('[data-testid=rule-add]'); time.sleep(2)
        note('customer rule', {'notice': text('[data-testid=notice]'), 'table': text('[data-testid=customer-rules]')[:300]}); flush('rule')
    p.fill('#dg-sched-at', '2026-12-01'); p.click('[data-testid=schedule-add]'); time.sleep(2)
    note('schedule', {'notice': text('[data-testid=notice]'), 'pending': text('[data-testid=schedules-pending]')[:300], 'err': text('#dg-sched .error:not(:empty)')}); flush('schedule')
    p.reload(); time.sleep(3); note('control panel after reload', text()[:200]); flush('reload'); shot('controlpanel-after')

    # ---- Quick setup
    go('#/quick-setup', 3); note('quick setup', text()[:1800]); shot('quicksetup'); flush('quick setup')

    # ---- Doctor: each question
    go('#/doctor', 2.5)
    n = p.evaluate("document.querySelectorAll('[data-testid=dr-ask]').length")
    for i in range(n):
        p.evaluate("document.querySelectorAll('[data-testid=dr-ask]')[%d].click()" % i); time.sleep(2.2)
        note('doctor q%d' % (i + 1), text('[data-testid=dr-answer]')[:1100] or text()[:600]); flush('doctor %d' % (i + 1))
    shot('doctor')
    tries = p.evaluate("[...document.querySelectorAll('[data-testid=dr-try]')].map(a => a.getAttribute('href'))")
    if tries:
        go(tries[0], 3); note('doctor -> quick setup', text('[data-testid=qs-from-doctor]') + ' || ' + text('[data-testid=qs-preview]')[:500]); flush('doctor try')

    # ---- Model: add own decisions, fit
    go('#/research', 2.5)
    custs = p.evaluate("[...document.querySelectorAll('#own-customer option')].map(o => [o.value, o.textContent]).filter(o => o[0])")
    note('own form customers', len(custs))
    p.click('[data-testid=own-add]'); time.sleep(0.5); note('own empty submit', p.evaluate("[...document.querySelectorAll('#rs-own .error:not(:empty)')].map(e => e.innerText)"))
    if custs:
        p.select_option('#own-customer', custs[0][0]); time.sleep(0.6)
        invs = p.evaluate("[...document.querySelectorAll('#own-invoice option')].map(o => [o.value, o.textContent]).filter(o => o[0])")
        note('own invoices for ' + custs[0][1], invs[:4])
        if invs:
            p.select_option('#own-invoice', invs[0][0]); p.fill('#own-days', '45'); p.check('#rs-own [name=outcome][value=decline]'); p.fill('#own-reason', 'They were already two months late')
            shot('model-own-form'); p.click('[data-testid=own-add]'); time.sleep(2)
            note('own extension added', {'toast': toast(), 'errors': p.evaluate("[...document.querySelectorAll('#rs-own .error:not(:empty)')].map(e => e.innerText)"), 'recent': text('[data-testid=own-recent]')[:400]}); flush('own ext')
        p.select_option('#own-customer', custs[-1][0]); time.sleep(0.6)
        p.check('#rs-own [name=kind][value=trial_credit]'); time.sleep(0.3)
        p.fill('#own-amount', '50,000,000'); p.fill('#own-terms', '30'); p.check('#rs-own [name=outcome][value=approve]')
        p.click('[data-testid=own-add]'); time.sleep(2)
        note('own trial added', {'toast': toast(), 'errors': p.evaluate("[...document.querySelectorAll('#rs-own .error:not(:empty)')].map(e => e.innerText)")}); flush('own trial')
        p.evaluate("document.querySelector('[data-testid=own-recent]')?.setAttribute('open', '')"); note('own recent', text('[data-testid=own-recent]')[:700])
    p.click('#rs-refit'); time.sleep(3); note('fit', {'toast': toast(), 'notice': text('[data-testid=notice], .callout')[:400], 'top': text()[:700]}); flush('fit'); shot('model-after')
    go('#/dashboard', 3); note('dashboard', text()[:1600]); flush('dashboard'); shot('dashboard-after')
    b.close()
json.dump(notes, open(os.path.join(out, 'act.json'), 'w'), indent=1)
