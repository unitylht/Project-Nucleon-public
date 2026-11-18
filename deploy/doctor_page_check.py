"""Browser check of the Doctor (#/doctor, 11 Nov 2026): six questions about how the Owner's setup is working, answered by code, and a suggestion opened in
Quick setup with nothing saved. Fictional data on a scratch records server (deploy/delegation_check_server.py). Standard library only (set CHROME_HEADLESS
to a chrome-headless-shell binary).

    python3 deploy/doctor_page_check.py      # prints PASS/FAIL per check; exit status 0 only if all pass
"""
import os, shutil, sys, tempfile, time, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from page_check_lib import Checks, Scratch, Page, IDS

tmp = tempfile.mkdtemp(prefix='doctor-check-')
check = Checks()
S = None
try:
    S = Scratch(tmp, 'dr')
    for i, (who, ref) in enumerate((('bayview', 'DEMO-301'), ('cityside', 'DEMO-410'))):   # long asks: they go to the Owner on the day limit
        S.resolve({'kind': 'extension', 'customerId': IDS[who], 'invoiceReference': ref, 'requestedDueDate': '2027-01-30', 'reasoning': 'Fictional page check: a long ask %d.' % i}, 'long-%d' % i)
    version = S.api('/api/delegation/policy', None, S.cookie['owner'])[1]['version']
    p = Page(S)
    p.open('#/doctor'); p.sign_in('staff'); p.go('#/doctor'); time.sleep(0.8)
    check('A1 Staff do not get the Doctor', not p.has('[data-testid=doctor-page]'), p.text()[:100])
    p.sign_out()
    p.open('#/doctor'); p.sign_in('owner'); p.go('#/doctor')
    loaded = p.wait("document.querySelectorAll('[data-testid=dr-question]').length === 6")
    heads = p.js("[...document.querySelectorAll('[data-testid=dr-question]')].map(b => b.dataset.question + ': ' + (b.querySelector('.dr-headline-short')?.innerText || ''))")
    check('A1 the page shows six questions, each with its headline', loaded and all(h.split(': ', 1)[1] for h in heads), heads)

    p.click('[data-testid=dr-question][data-question=came]')
    shown = p.wait("!!document.querySelector('[data-testid=dr-answer][data-question=came] [data-testid=dr-headline]')")
    sug = p.js("[...document.querySelectorAll('[data-testid=dr-answer] [data-testid=dr-suggestion]')].map(s => s.innerText)")
    check('A2 "came" shows its findings and a suggestion that states where it starts', shown and p.count('[data-testid=dr-answer] [data-testid=dr-finding]') >= 1 and any('(now' in s for s in sug),
          (p.text('[data-testid=dr-answer]')[:300], sug))
    check('A6 with this few cases it says there are too few to see a pattern', p.has('[data-testid=dr-answer] [data-testid=dr-few]'))
    check('A2 the address names the question, so a reload opens it again', 'q=came' in p.js('location.hash'), p.js('location.hash'))
    href = p.attr('[data-testid=dr-answer] [data-testid=dr-try]', 'href') or ''
    p.click('[data-testid=dr-answer] [data-testid=dr-try]')
    filled = p.wait("!!document.querySelector('[data-testid=qs-from-doctor]') && !!document.querySelector('[data-testid=qs-preview]:not([aria-busy])')", 15)
    wanted = __import__('json').loads(urllib.parse.unquote(href.split('try=', 1)[1])) if 'try=' in href else {}
    values = {k: p.js("document.querySelector('#qs-%s')?.%s" % (k, 'checked' if isinstance(v, bool) else 'value')) for k, v in wanted.items() if k not in ('holdCustomers', 'start', 'lateHistory')}
    same = all(str(values[k]).lower() == str(v).lower() for k, v in wanted.items() if k in values)
    after = S.api('/api/delegation/policy', None, S.cookie['owner'])[1]['version']
    check('A3 "Try this in Quick setup" opens Quick setup with that answer filled in and nothing saved', filled and wanted and same and after == version, (wanted, values, after, version))

    p.go('#/doctor?q=came'); p.wait("!!document.querySelector('[data-testid=dr-answer][data-question=came]')")
    p.js("(() => { const s = document.querySelector('[data-testid=dr-window]'); s.value = 'all'; s.dispatchEvent(new Event('change', { bubbles: true })); return true })()")
    time.sleep(1.0)
    check('A4 the window choice reloads the open answer', p.has('[data-testid=dr-answer][data-question=came][data-days=all]'), p.attr('[data-testid=dr-answer]', 'data-days'))
    p.go('#/'); time.sleep(0.3); p.go('#/doctor?q=corrections')
    check('A5 an address with ?q=corrections opens that answer directly', p.wait("!!document.querySelector('[data-testid=dr-answer][data-question=corrections] [data-testid=dr-headline]')"),
          p.text('[data-testid=dr-answer]')[:160])

    for label, raw in (('script text', '{"maxInvoice":"<img src=x onerror=window.__pwned=1>"}'), ('a list', '[1,2]'), ('not JSON', 'not json'),
                       ('unknown keys and wrong types', '{"maxInvoice":5,"evil":"x","holdCustomers":"all","daysPastOriginalDue":"9"}')):
        p.go('#/'); time.sleep(0.3)
        p.go('#/quick-setup?try=' + urllib.parse.quote(raw))
        ok = p.wait("!!document.querySelector('[data-testid=qs-preview]:not([aria-busy])')", 15)
        check('B1 Quick setup with a broken suggestion (%s) still loads, runs no script and saves nothing' % label,
              ok and not p.js('window.__pwned') and S.api('/api/delegation/policy', None, S.cookie['owner'])[1]['version'] == version and not p.has('#main img[src=x]'),
              p.text()[:120])

    p.go('#/'); time.sleep(0.3)
    p.js("(() => { const f = window.fetch; window.fetch = (u, o) => String(u).includes('question=') ? new Promise(r => setTimeout(() => r(f(u, o)), 1200)) : f(u, o); return true })()")   # answers arrive late
    p.go('#/doctor?q=came'); p.wait("!!document.querySelector('[data-testid=doctor-page]')"); p.go('#/')   # leave while the answer is still loading
    time.sleep(2.0)
    check('A7 leaving while an answer loads: Home stays, the Doctor is not drawn over it', p.has('[data-testid=home-page]') and not p.has('[data-testid=doctor-page]'), p.text()[:80])
    p.go('#/'); p.wait("!!document.querySelector('.home-links')"); time.sleep(0.3)
    home = p.has('.home-links a[href="#/doctor"]')
    p.go('#/delegation'); p.wait("!!document.querySelector('#dg-form')"); time.sleep(0.3)
    panel = p.has('[data-testid=doctor-link] a[href="#/doctor"]')
    p.go('#/review'); p.wait("!!document.querySelector('[data-testid=review-page]')"); time.sleep(0.5)
    review = p.has('[data-testid=review-doctor-link] a[href="#/doctor"]')
    check('C1 Home, the Control panel and the Decide page link to the Doctor', home and panel and review, (home, panel, review))
    p.go('#/doctor?q=came'); p.wait("!!document.querySelector('[data-testid=dr-answer]')"); time.sleep(0.4)
    p.phone(True); time.sleep(0.4)
    check('C2 no sideways scrolling at phone width', p.no_hscroll(), p.width_info())
    p.phone(False)
    check('Z no page error was thrown', not p.b.errors(), p.b.errors()[:2])
except Exception as e:
    check('no exception', False, repr(e))
finally:
    if S: S.stop()
    shutil.rmtree(tmp, ignore_errors=True)
sys.exit(check.finish())
