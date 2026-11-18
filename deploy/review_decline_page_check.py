"""Browser check of an agent decline (policy.autoDecline, 8 Nov 2026) on the Owner's pages: the Review row, its override back to the date asked for, the Control panel list and
counts, and Home. Hoang's NTK round on 9 Nov found the Review page crashing on such a row ("Cannot access 'declined' before initialization") and the Control panel calling it an
approval. Fictional data on a scratch records server (deploy/delegation_check_server.py). Standard library only (set CHROME_HEADLESS to a chrome-headless-shell binary).

    python3 deploy/review_decline_page_check.py      # prints PASS/FAIL per check; exit status 0 only if all pass
"""
import os, shutil, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from page_check_lib import Checks, Scratch, Page, IDS
import delegation_demo

LINES = {'enabled': True, 'maxExtensionDays': 40, 'maxDecisionExposure': None, 'maxCustomerExposure': None, 'maxPriorLateShare': None}
tmp = tempfile.mkdtemp(prefix='review-decline-check-')
check = Checks()
S = None
try:
    S = Scratch(tmp, 'd')
    pol = S.api('/api/delegation/policy', None, S.cookie['owner'])[1]
    s_, out, _ = S.owner('/api/delegation/policy', {**delegation_demo.DEMO_POLICY, 'autoDecline': LINES, 'expectedVersion': pol['version']}, method='PUT')
    check('0 (setup) the Owner saves decline lines (40 days)', s_ == 200, out)
    dec = S.resolve({'kind': 'extension', 'customerId': IDS['bayview'], 'invoiceReference': 'DEMO-301', 'requestedDueDate': '2026-12-10', 'recommendation': 'decline',
                     'reasoning': 'Fictional page check: far longer than this customer usually gets.'}, 'd-bay')
    check('0 (setup) the agent declines the 53-day extension', (dec['status'], dec['handling'], dec['decision']['outcome']) == ('decided', 'autonomous_decline', 'decline'), dec.get('handling'))
    row = '[data-section=auto][data-case="%s"]' % dec['caseId']

    p = Page(S)
    p.open('#/review'); p.sign_in('owner')
    loaded = p.wait("!!document.querySelector('[data-testid=review-page]')")
    check('A1 the Review page loads with an agent-declined case (no crash)', loaded and 'didn\'t load' not in p.text(), p.text()[:200].replace('\n', ' | '))
    check('A1 the row is under the agent\'s decisions, marked "Declined by the agent"', p.has(row) and p.has(row + ' [data-testid=agent-declined-label]'))
    check('A1 its override button approves the date asked for', p.text(row + ' [data-testid=act-override]') == 'Override: approve the date asked for', p.text(row + ' [data-testid=act-override]'))

    p.click(row + ' [data-open]'); p.wait("!document.querySelector('%s .rv-body').hidden" % row)
    p.fill(row + ' [data-why]', 'Fictional page check: they are good for it.')
    p.click(row + ' [data-testid=act-override]')
    shown = p.wait("!!document.querySelector('%s [data-testid=override-confirm]')" % row)
    check('A2 the override asks first and says it moves the due date', shown and 'approves the date asked for' in p.text(row + ' [data-testid=override-effects]'), p.text(row + ' [data-testid=override-effects]'))
    p.fill(row + ' [data-why]', 'Fictional page check: they are good for it.')
    p.click(row + ' [data-testid=act-override-confirm]')
    time.sleep(1.0)
    case = S.case(dec['caseId'])
    due = S.sql("SELECT json_extract(data, '$.dueDate') FROM invoices WHERE json_extract(data, '$.reference') = 'DEMO-301'")
    check('A2 confirmed: the case is overridden to an approval and the page did not crash', (case.get('override') or {}).get('outcome') == 'approve' and 'didn\'t load' not in p.text(), (case.get('override'), p.text()[:160]))

    # ---- a second decline left as it is, for the Control panel and Home
    dec2 = S.resolve({'kind': 'extension', 'customerId': IDS['cityside'], 'invoiceReference': 'DEMO-410', 'days': 60, 'recommendation': 'decline',
                      'reasoning': 'Fictional page check: 60 days is far too long.'}, 'd-city')
    check('B0 (setup) a second agent decline', dec2['handling'] == 'autonomous_decline', dec2.get('handling'))
    p.go('#/delegation'); p.wait("!!document.querySelector('[data-testid=counts]')"); time.sleep(0.5)
    item = '[data-testid=agent-decision][data-case="%s"]' % dec2['caseId']
    check('B1 the Control panel lists it as "Declined by the agent", not an approval', p.has(item) and 'Declined by the agent' in p.text(item + ' h3') and 'Approved' not in p.text(item + ' h3'), p.text(item + ' h3'))
    counts = p.text('[data-testid=counts]')
    check('B1 the counts show 0 approved and 1 declined by the agent (the reversed one counts as overridden)', 'Approved by the agent\n0' in counts and 'Declined by the agent\n1' in counts and 'Overridden\n1' in counts, counts.replace('\n', ' | '))
    p.go('#/'); p.wait("!!document.querySelector('[data-testid=home-recent-list], [data-testid=home-recent-none]')"); time.sleep(0.3)
    home = '[data-testid=home-recent][data-case="%s"]' % dec2['caseId']
    check('B2 Home\'s recent agent decisions say "Declined by the agent"', p.has(home) and 'Declined by the agent' in p.text(home), p.text(home))
    p.go('#/decision-cases/' + dec['caseId']); time.sleep(1.0)
    check('B3 the reversed case\'s timeline loads and says the decline was reversed', 'reversed' in p.text(), p.text()[:300].replace('\n', ' | '))
    p.close() if hasattr(p, 'close') else None
except Exception as e:
    check('no exception', False, repr(e))
finally:
    if S: S.stop()
    shutil.rmtree(tmp, ignore_errors=True)
sys.exit(check.finish())
