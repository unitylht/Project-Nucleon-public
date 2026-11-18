"""Browser check of Quick setup (#/quick-setup, 11 Nov 2026): the Owner's first setup in a few questions, a live preview on their own open invoices, a plain
summary, and saving a normal policy version. Fictional data on a scratch records server (deploy/delegation_check_server.py). Standard library only (set
CHROME_HEADLESS to a chrome-headless-shell binary).

    python3 deploy/quick_setup_page_check.py      # prints PASS/FAIL per check; exit status 0 only if all pass
"""
import json, os, shutil, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from page_check_lib import Checks, Scratch, Page

tmp = tempfile.mkdtemp(prefix='quick-setup-check-')
check = Checks()
S = None


def preview_settled(p):
    """Wait until the preview has been drawn for the current answers (no request in flight)."""
    time.sleep(0.6)
    return p.wait("!!document.querySelector('[data-testid=qs-preview]') && !document.querySelector('[data-testid=qs-preview][aria-busy=true]')")


def counts(p):
    return [int(p.text('[data-testid=qs-count-%s]' % k) or -1) for k in ('agent', 'owner', 'held')]


try:
    S = Scratch(tmp, 'q')
    p = Page(S)
    p.open('#/quick-setup'); p.sign_in('staff')
    p.go('#/quick-setup'); time.sleep(0.8)
    check('A1 Staff do not get the helper', not p.has('[data-testid=qs-save]'), p.text()[:120])
    p.sign_out()
    p.open('#/quick-setup'); p.sign_in('owner'); p.go('#/quick-setup')
    loaded = p.wait("!!document.querySelector('[data-testid=quick-setup-page]')")
    a = p.text('[data-testid=qs-assurances]')
    check('A1 the page loads for the Owner with the three assurances', loaded and 'never contacts your customer' in a and 'undo any decision' in a and 'pause the agent' in a, a[:200])
    marks = p.js("[...document.querySelectorAll('#qs-form .field')].map(f => [f.querySelector('input').name, !!f.querySelector('label .req'), !!f.querySelector('label .opt'), f.querySelector('input').getAttribute('aria-required')])")
    want = [['maxInvoice', True, False, 'true'], ['maxCustomer', True, False, 'true'], ['daysFromRequest', False, True, None], ['daysPastOriginalDue', True, False, 'true']]
    check('A1b every field says Required or Optional, and the form explains the two', marks == want and p.has('#qs-form [data-testid=required-legend]'), marks)
    preview_settled(p)
    total = int(p.attr('[data-testid=qs-preview]', 'data-total') or -1)
    check('A2 the preview shows three counts that add up to the total', total > 0 and sum(counts(p)) == total, (counts(p), total))

    p.fill('#qs-daysPastOriginalDue', '1'); preview_settled(p)
    first = p.attr('[data-testid=qs-reason]', 'data-question')
    check('A3 one day in total: the agent decides none, the callout says so, and the main reason points at that question',
          counts(p)[0] == 0 and p.has('[data-testid=qs-none]') and first == 'daysPastOriginalDue', (counts(p), first))
    p.click('[data-testid=qs-reason]'); time.sleep(0.3)
    check('A3 clicking the reason focuses its question', p.js("document.activeElement?.id") == 'qs-daysPastOriginalDue', p.js("document.activeElement?.id"))
    p.click('[name=start][value=now]')   # the demo policy asks for a track record first; deciding from today shows the effect at once
    p.click('[name=lateHistory][value=any]')
    p.fill('#qs-daysPastOriginalDue', '365'); p.fill('#qs-daysFromRequest', '365')
    p.click('#qs-allowOtherOverdue') if not p.js("document.querySelector('#qs-allowOtherOverdue').checked") else None
    preview_settled(p)
    before = counts(p)
    p.fill('#qs-maxInvoice', '1'); preview_settled(p)
    tiny = counts(p)
    p.click('[data-testid=qs-amount-choice][data-for=maxInvoice][data-which=largest]'); preview_settled(p)
    check('A4 an amount choice fills the field and the preview follows it', p.js("document.querySelector('#qs-maxInvoice').value") != '1' and counts(p) != tiny and tiny[0] == 0,
          (before, tiny, counts(p), p.js("document.querySelector('#qs-maxInvoice').value")))

    p.fill('#qs-maxInvoice', 'abc'); preview_settled(p)
    err = p.text('[data-error-for=maxInvoice]')
    check('A5 a bad amount is named under its question and the page keeps working', bool(err) and p.has('[data-testid=qs-save]'), err)
    p.click('[data-testid=qs-amount-choice][data-for=maxInvoice][data-which=largest]'); preview_settled(p)

    v0 = S.api('/api/delegation/policy', None, S.cookie['owner'])[1]['version']
    p.fill('#qs-daysPastOriginalDue', '45'); p.fill('#qs-daysFromRequest', '14'); preview_settled(p)
    summary = p.text('[data-testid=qs-summary]')
    check('A6 the summary says, in plain words, what the agent decides and what comes to you', 'up to 14 days after the day the customer asks' in summary and 'Anything over those limits.' in summary, summary[:300])
    p.click('[data-testid=qs-save]')
    saved = p.wait("!!document.querySelector('[data-testid=qs-saved]')")
    pol = S.api('/api/delegation/policy', None, S.cookie['owner'])[1]
    check('B1 Save stores a new version noted "Saved from Quick setup"', saved and pol['version'] == v0 + 1 and pol.get('note') == 'Saved from Quick setup'
          and (pol['extensions']['maxDaysFromRequest'], pol['extensions']['maxDaysPastOriginalDue']) == (14, 45), (pol['version'], pol.get('note'), pol['extensions']))
    p.go('#/delegation'); p.wait("!!document.querySelector('#dg-form')"); time.sleep(0.4)
    check('B2 the Control panel shows the same day limits', (p.js("document.querySelector('#dg-ext-from-request').value"), p.js("document.querySelector('#dg-ext-total').value")) == ('14', '45'))
    check('C1 the Control panel links to Quick setup', p.has('#main a[href="#/quick-setup"]'))

    p.go('#/quick-setup'); p.wait("!!document.querySelector('[data-testid=qs-save]')"); preview_settled(p)
    p.fill('#qs-daysPastOriginalDue', '50'); preview_settled(p)
    s_, out, _ = S.owner('/api/delegation/policy/pause', {'expectedVersion': pol['version']})   # a change behind the page's back
    p.click('[data-testid=qs-save]')
    conflict = p.wait("!!document.querySelector('[data-testid=qs-conflict]')")
    check('B3 a change made elsewhere is shown, and the answers are kept', s_ == 200 and conflict and p.js("document.querySelector('#qs-daysPastOriginalDue').value") == '50', p.text('[data-testid=qs-conflict]'))
    p.click('[data-testid=qs-save]')
    again = p.wait("!!document.querySelector('[data-testid=qs-saved]')")
    pol2 = S.api('/api/delegation/policy', None, S.cookie['owner'])[1]
    check('B3 saving again then works', again and pol2['version'] == pol['version'] + 2 and pol2['extensions']['maxDaysPastOriginalDue'] == 50, (pol2['version'], pol2['extensions']))

    p.go('#/'); p.wait("!!document.querySelector('[data-testid=where-to-start]')"); time.sleep(0.3)
    check('C1 Home\'s first step links to Quick setup', p.has('[data-testid=where-to-start] a[href="#/quick-setup"]'))
    p.go('#/quick-setup'); p.wait("!!document.querySelector('[data-testid=qs-save]')"); preview_settled(p)
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
