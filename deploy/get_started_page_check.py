"""Browser check of Get started (#/get-started), the three levels and the three display levels (12 Nov 2026). Fictional data on a scratch records server
(deploy/delegation_check_server.py). Standard library only (set CHROME_HEADLESS to a chrome-headless-shell binary).

    python3 deploy/get_started_page_check.py      # prints PASS/FAIL per check; exit status 0 only if all pass
"""
import json, os, shutil, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from page_check_lib import Checks, Scratch, Page

tmp = tempfile.mkdtemp(prefix='get-started-check-')
check = Checks()
S = None


def settled(p, box):
    time.sleep(0.6)
    return p.wait("!!document.querySelector('%s') && !document.querySelector('%s[aria-busy=true]')" % (box, box))


def shown(p, sel):
    """Whether the first match is laid out (not display:none)."""
    return p.js("(() => { const e = document.querySelector(%s); return !!e && e.getClientRects().length > 0 && (!e.checkVisibility || e.checkVisibility()) })()" % json.dumps(sel))


def nav(p):
    return p.js("[...document.querySelectorAll('.mainnav > a.nav-link')].map(a => a.innerText.replace(/[^A-Za-z ]/g, '').trim())")


try:
    S = Scratch(tmp, 'g')
    p = Page(S)
    p.open('#/get-started'); p.sign_in('staff')
    p.go('#/get-started'); time.sleep(0.8)
    check('A1 Staff do not get the path', not p.has('[data-testid=gs-next]'), p.text()[:120])
    p.sign_out()
    p.open('#/'); p.sign_in('owner'); p.go('#/')
    p.wait("!!document.querySelector('[data-testid=home-brief]')")
    check('A2 Home opens with one sentence on what waits', p.attr('[data-testid=home-brief]', 'data-state') in ('clear', 'waiting', 'start'), p.text('[data-testid=home-brief]'))
    check('A3 Home\'s first step links to Get started', p.has('[data-testid=where-to-start] a[href="#/get-started"]'))

    p.go('#/get-started')
    loaded = p.wait("!!document.querySelector('[data-testid=get-started-page][data-step=\"1\"]')")
    levels = p.js("[...document.querySelectorAll('[data-testid=gs-levels] [data-level]')].map(b => b.dataset.level)")
    check('B1 step 1 offers the three levels, and keeping the saved rules', loaded and levels == ['strict', 'balanced', 'relaxed'] and p.has('[data-testid=gs-keep]'), levels)
    settled(p, '#gs-preview')
    count = lambda: int(p.text('[data-testid=gs-count-agent]') or -1)
    p.click('[data-testid=level-strict]'); settled(p, '#gs-preview'); strict = count()
    p.click('[data-testid=level-relaxed]'); settled(p, '#gs-preview'); relaxed = count()
    check('B2 the preview follows the level: relaxed lets the agent decide at least as many as strict', strict >= 0 and relaxed >= strict, (strict, relaxed))
    check('B3 the chosen level is marked', p.attr('[data-testid=level-relaxed]', 'aria-pressed') == 'true' and p.attr('[data-testid=level-strict]', 'aria-pressed') == 'false')

    v0 = S.api('/api/delegation/policy', None, S.cookie['owner'])[1]
    p.click('[data-testid=gs-next]')
    p.wait("!!document.querySelector('[data-testid=get-started-page][data-step=\"2\"]')")
    boxes = p.count('[name=gs-hold]')
    first = p.attr('[name=gs-hold]', 'value')
    p.click('[name=gs-hold]')
    check('C1 step 2 lists the customers to keep', boxes >= 1, boxes)
    picked = p.js("document.querySelector('[name=gs-new]:checked')?.value")
    note = p.text('[data-testid=gs-new]')
    check('C2 step 2 asks about new customers, set as the rules in force, with the level\'s one-request limit', picked == 'trial' and 'It always comes to me' in note
          and 'Up to AUD 900.00 at risk' in note, (picked, note[:200]))
    p.click('[data-testid=gs-next]')
    p.wait("!!document.querySelector('[data-testid=get-started-page][data-step=\"3\"]')")
    check('D1 step 3 offers three display levels with a preview', p.count('[data-testid=gs-view] [name=viewLevel]') == 3 and p.has('[data-testid=gs-demo]'))
    p.click('[data-testid=view-simple]'); time.sleep(0.3)
    check('D2 Simple: the preview hides the explanation and the menu becomes Home, Assistant?, Decide, Rules',
          p.attr('[data-testid=gs-demo]', 'data-demo') == 'simple' and not shown(p, '[data-testid=gs-demo] .hint') and 'Rules' in nav(p) and 'Control panel' not in nav(p), nav(p))
    check('D3 the page itself survives the menu change', p.has('[data-testid=gs-finish]') and p.has('[data-testid=gs-demo]'))
    check('D4 nothing was saved before the last button', S.api('/api/delegation/policy', None, S.cookie['owner'])[1]['version'] == v0['version'])
    p.click('[data-testid=gs-finish]')
    done = p.wait("!!document.querySelector('[data-testid=gs-done]')")
    pol = S.api('/api/delegation/policy', None, S.cookie['owner'])[1]
    check('E1 the last button saves one version, noted with the level', done and pol['version'] == v0['version'] + 1 and pol.get('note') == 'Saved from Get started (Relaxed)', (pol['version'], pol.get('note')))
    check('E2 the level and the kept customer are in the policy', pol['extensions']['maxDaysFromRequest'] == 30 and pol['extensions']['maxDaysPastOriginalDue'] == 90
          and pol['restrictions']['holdCustomers'] == [first], (pol['extensions'], pol['restrictions']['holdCustomers']))
    check('E3 what the path does not ask about is kept', pol['newCustomers'] == v0['newCustomers'] and pol['mode'] == v0['mode'] and pol['trackRecord'] == v0['trackRecord'],
          (pol['newCustomers'], v0['newCustomers']))

    p.go('#/delegation')
    p.wait("!!document.querySelector('[data-testid=dg-quick]')")
    check('F1 the Control panel has the same three choices at the top', p.has('[data-testid=dg-levels] [data-level=strict]') and p.has('[data-testid=dg-held-change]') and p.count('[data-testid=dg-view] [name=viewLevel]') == 3)
    check('F2 it marks the level in force', p.attr('[data-testid=dg-levels] [data-level=relaxed]', 'aria-pressed') == 'true')
    check('F3 Simple: explanations are hidden and the occasional sections are folded', not shown(p, '#dg-max-decision-hint') and p.has('[data-testid=dg-more-settings]') and not shown(p, '#dg-hist'), (shown(p, '#dg-max-decision-hint'), p.has('[data-testid=dg-more-settings]'), shown(p, '#dg-hist'), p.js('document.documentElement.dataset.view')))
    check('F4 a jump link opens the folded section', p.click('[data-jump=dg-hist]') and shown(p, '#dg-hist'))
    p.click('[data-testid=dg-view] [data-testid=view-standard]'); time.sleep(0.4)
    one_line = p.js("(() => { const h = document.querySelector('#dg-max-decision-hint'); return !!h && h.getClientRects().length > 0 && h.scrollHeight > h.clientHeight + 2 })()")
    check('F5 Standard: one line of each explanation, the full menu back', one_line and 'Control panel' in nav(p) and not p.has('[data-testid=dg-more-settings]'), nav(p))
    p.js("document.querySelector('#dg-max-decision-hint').click()"); time.sleep(0.2)
    check('F6 a click opens the explanation', p.js("(() => { const h = document.querySelector('#dg-max-decision-hint'); return h.scrollHeight <= h.clientHeight + 2 })()"))
    p.click('[data-testid=dg-view] [data-testid=view-detailed]'); time.sleep(0.4)
    check('F7 Detailed: explanations in full', p.js("(() => { const h = document.querySelectorAll('.hint')[3]; return !!h && h.scrollHeight <= h.clientHeight + 2 })()"))
    p.click('[data-testid=dg-held-change]'); time.sleep(0.3)
    check('F8 "Change" on the kept customers goes to their field', p.js("document.activeElement?.id") == 'dg-hold', p.js("document.activeElement?.id"))
    p.click('[data-testid=dg-levels] [data-level=strict]')
    p.wait("!!document.querySelector('[data-testid=quick-setup-page]')"); settled(p, '[data-testid=qs-preview]')
    check('G1 a level on the Control panel opens Quick setup filled in, and saves nothing',
          p.js("document.querySelector('#qs-daysFromRequest').value") == '7' and p.attr('[data-testid=qs-levels] [data-level=strict]', 'aria-pressed') == 'true'
          and S.api('/api/delegation/policy', None, S.cookie['owner'])[1]['version'] == pol['version'], p.js("document.querySelector('#qs-daysFromRequest').value"))
    p.fill('#qs-daysFromRequest', '9'); settled(p, '[data-testid=qs-preview]')
    check('G2 changing an answer turns the level to Custom', p.attr('[data-testid=qs-levels] [data-level=custom]', 'aria-pressed') == 'true')
    p.click('[data-testid=qs-levels] [data-level=balanced]'); settled(p, '[data-testid=qs-preview]')
    check('G3 a level button fills the answers', p.js("document.querySelector('#qs-daysFromRequest').value") == '14' and p.js("document.querySelector('#qs-daysPastOriginalDue').value") == '60')

    p.go('#/get-started'); p.wait("!!document.querySelector('[data-testid=gs-next]')")
    p.phone(True); time.sleep(0.4)
    check('H1 no sideways scrolling at phone width', p.no_hscroll(), p.width_info())
    p.phone(False)
    p.sign_out(); p.open('#/'); p.sign_in('staff'); p.go('#/customers'); time.sleep(0.6)
    check('H2 Staff pages always show their instructions in full', p.js("document.documentElement.dataset.view") == 'detailed')
    check('Z no page error was thrown', not p.b.errors(), p.b.errors()[:2])
except Exception as e:
    check('no exception', False, repr(e))
finally:
    if S: S.stop()
    shutil.rmtree(tmp, ignore_errors=True)
sys.exit(check.finish())
