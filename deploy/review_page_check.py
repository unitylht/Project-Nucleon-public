"""Browser check of the Owner's Review page (#/review), the case timeline (#/decision-cases/<id>) and the page-use events they send, in a headless Chromium on a scratch
records server this script starts itself (deploy/delegation_check_server.py: fictional data, a throwaway database, a free loopback port). Fictional data only. Standard library only
(set CHROME_HEADLESS to a chrome-headless-shell binary).

    python3 deploy/review_page_check.py      # prints PASS/FAIL per check; exit status 0 only if all pass
"""
import json, os, shutil, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from page_check_lib import Checks, Scratch, Page, IDS, ROOT
import delegation_demo

tmp = tempfile.mkdtemp(prefix='review-check-')
check = Checks()
S = None
try:
    S = Scratch(tmp, 'r')
    ext_bay = S.resolve({'kind': 'extension', 'customerId': IDS['bayview'], 'invoiceReference': 'DEMO-301', 'requestedDueDate': '2026-11-10'}, 'r-bay')
    trial_n8 = S.resolve({'kind': 'trial_credit', 'customerId': IDS['northside'], 'orderAmount': '800.00', 'termsDays': 14}, 'r-n8')
    trial_n7 = {'caseId': S.approved_trial('Pinecrest Kiosk'), 'status': 'decided'}   # the agent asked Staff for a deposit and the identity, then approved
    trial_n6 = {'caseId': S.approved_trial('Quarry Bakehouse'), 'status': 'decided'}
    harb = S.resolve({'kind': 'trial_credit', 'customerId': IDS['harbourline'], 'orderAmount': '5000.00', 'termsDays': 14}, 'r-harb')
    city = S.resolve({'kind': 'extension', 'customerId': IDS['cityside'], 'invoiceReference': 'DEMO-410', 'days': 14}, 'r-city')
    river = S.resolve({'kind': 'extension', 'customerId': IDS['riverside'], 'invoiceReference': 'DEMO-505', 'days': 10}, 'r-river')
    lake_cid, lake = S.asked_trial('Lakeside Gather')   # left waiting for Staff
    s_, rec, _ = S.api('/api/records/customers', {'name': 'Mooncove Bakery (fictional)'}, S.cookie['staff'], 'cust-moon')
    moon_id = rec['record']['id']
    pol = S.api('/api/delegation/policy', None, S.cookie['owner'])[1]
    s_, out, _ = S.owner('/api/delegation/policy', {**delegation_demo.DEMO_POLICY, 'restrictions': {**delegation_demo.DEMO_POLICY['restrictions'], 'holdCustomers': [moon_id]}, 'expectedVersion': pol['version']}, method='PUT')
    assert s_ == 200, out
    moon = S.resolve({'kind': 'trial_credit', 'customerId': moon_id, 'orderAmount': '300.00', 'termsDays': 14}, 'r-moon')
    check('0 (setup) cases: 4 agent approvals, 3 waiting for the Owner, 1 held, 1 gathering evidence',
          [x['status'] for x in (ext_bay, trial_n8, trial_n7, trial_n6, harb, city, river, moon, lake)] == ['decided'] * 4 + ['awaiting_owner'] * 3 + ['on_hold', 'gathering_evidence'], [x['status'] for x in (ext_bay, trial_n8, trial_n7, trial_n6, harb, city, river, moon, lake)])

    p = Page(S)
    p.open('#/review')
    p.sign_in('staff')
    check('A1 Staff get "Page not found" at #/review', p.wait("document.querySelector('#main h1')?.textContent === 'Page not found'") and not p.has('[data-testid=review-page]'))
    p.go('#/dashboard')
    check('A1 Staff get "Page not found" at #/dashboard too', p.wait("document.querySelector('#main h1')?.textContent === 'Page not found'") and not p.has('[data-testid=dashboard-page]'))
    p.sign_out()
    p.open('#/review'); p.sign_in('owner')
    check('B1 the Owner opens the Review page', p.wait("!!document.querySelector('[data-testid=review-page]')") and p.text('#main h1') == 'Decide', p.js('location.hash'))
    check('B1 Review is the current page in the navigation', p.js("document.querySelector('header.top a[aria-current=page]')?.dataset.area") == 'review')
    waiting = p.js("[...document.querySelectorAll('[data-section=waiting]')].map(e => e.dataset.case)")
    auto = p.js("[...document.querySelectorAll('[data-section=auto]')].map(e => e.dataset.case)")
    check('B1 waiting: the escalated (3) and the held (1) cases', sorted(waiting) == sorted([harb['caseId'], city['caseId'], river['caseId'], moon['caseId']]) and p.text('[data-testid=waiting-count]') == '4', waiting)
    check('B1 autonomous decisions to review: the 4 agent approvals; the case gathering evidence is on neither list', sorted(auto) == sorted([ext_bay['caseId'], trial_n8['caseId'], trial_n7['caseId'], trial_n6['caseId']]) and lake['caseId'] not in waiting + auto, auto)
    check('B1 recently reviewed is empty', p.has('[data-testid=reviewed-none]'))
    check('B1 the held case says it is on hold by policy', 'On hold by policy' in p.text('[data-section=waiting][data-case=%s]' % moon['caseId']) if False else 'On hold by policy' in p.js("document.querySelector('[data-case=\"%s\"]').innerText" % moon['caseId']))
    check('B1 every row has a one-line why and a timeline link', p.count('[data-testid=review-row]') == 8 and all(p.js("(document.querySelector('[data-case=\"%s\"] [data-testid=row-why]')?.innerText || '').length > 10" % c) and
          p.attr('[data-case="%s"] [data-testid=row-timeline]' % c, 'href') == '#/decision-cases/' + c for c in waiting + auto))
    check('B2 rows are closed and nothing was posted as viewed when the list was drawn', p.count('.rv-body:not([hidden])') == 0 and S.sql("SELECT COUNT(*) FROM case_events WHERE kind='viewed'")[0][0] == 0)

    # ---- a request sent through the form (no decision case) is listed under Waiting too, with a link to its own page
    s_, form_req, _ = S.staff('/api/requests', {'messageText': 'Cityside Desserts asks to move the due date for invoice DEMO-410 from 28 October 2026 to 14 November 2026 because of a temporary cash-flow delay.'}, 'form-city')
    check('B3 (setup) the form request is prepared and waits for the Owner, with the written date and reason read from the message', s_ == 202 and form_req['status'] == 'awaiting_owner' and form_req.get('requestedDueDate') == '2026-11-14', (s_, form_req.get('status'), form_req.get('requestedDueDate')))
    p.go('#/dashboard'); p.wait("!!document.querySelector('[data-testid=dashboard-page]')")
    p.go('#/review'); p.wait("!!document.querySelector('[data-testid=review-page]')"); time.sleep(0.3)
    form_row = '[data-testid=review-form-row][data-request="%s"]' % form_req['id']
    check('B3 the form request is a row under Waiting for you, counted with the others (5), marked as sent through the form', p.has(form_row) and p.text('[data-testid=waiting-count]') == '5' and 'Sent through the form' in p.text(form_row + ' [data-testid=row-why]') and 'DEMO-410' in p.text(form_row + ' [data-testid=row-why]'), (p.count('[data-testid=review-form-row]'), p.text('[data-testid=waiting-count]')))
    check('B3 its button opens the request\'s own page, where it is decided', p.attr(form_row + ' [data-testid=row-request]', 'href') == '#/case/' + form_req['id'])
    s_, gone, _ = S.staff('/api/tools/withdrawRequest', {'args': {'requestId': form_req['id'], 'reason': 'Fictional page check: withdrawn again.'}}, 'form-city-withdraw')
    p.go('#/dashboard'); p.wait("!!document.querySelector('[data-testid=dashboard-page]')")
    p.go('#/review'); p.wait("!!document.querySelector('[data-testid=review-page]')"); time.sleep(0.3)
    check('B3 withdrawn, it leaves the list and the count returns to 4', s_ == 200 and not p.has(form_row) and p.text('[data-testid=waiting-count]') == '4', (s_, gone if s_ != 200 else ''))

    # ---- opening a row: viewed once
    row = '[data-case="%s"]' % harb['caseId']
    p.click(row + ' [data-open]')
    check('C1 opening a row shows the key facts, the assistant\'s recommendation with its reasoning, the closest reviewed cases and the track-record wording',
          p.wait("!document.querySelector('%s .rv-body').hidden" % row) and 'Trial credit' in p.text(row + ' [data-testid=row-facts]') and 'recommended' in p.text(row + ' [data-testid=row-recommendation]') and
          'Fictional page check.' in p.text(row + ' [data-testid=row-recommendation]') and 'closest reviewed cases' in p.text(row + ' [data-testid=row-comparables]') and 'Setting:' in p.text(row + ' [data-testid=row-track]'), p.text(row)[:300].replace('\n', ' | '))
    time.sleep(0.8)
    viewed = S.sql("SELECT case_id FROM case_events WHERE kind='viewed'")
    check('C1 opening posted exactly one viewed event for that case', viewed == [(harb['caseId'],)], viewed)
    p.click(row + ' [data-open]'); time.sleep(0.2); p.click(row + ' [data-open]'); time.sleep(0.8)
    check('C1 closing and reopening posted no second viewed event', S.sql("SELECT COUNT(*) FROM case_events WHERE kind='viewed'")[0][0] == 1)

    # ---- decide a trial credit: reason required
    p.click(row + ' [data-act=decline]')
    check('D1 declining with no reason asks for one and decides nothing', 'Enter a brief reason.' in p.text(row) and S.case(harb['caseId'])['status'] == 'awaiting_owner')
    p.js("window.__w = []; const real = window.fetch; window.fetch = (u, o = {}) => { if (/decide|feedback|decisions/.test(String(u))) window.__w.push({ u: String(u), h: o.headers, b: o.body }); return real(u, o); }; true")
    p.fill(row + ' [data-why]', 'Too large for a first order (page check).')
    p.js("(() => { const b = document.querySelector('%s [data-act=decline]'); b.click(); b.click(); return true })()" % row)
    check('D1 declining with a reason records the Owner\'s decision, once for a double click', p.wait("!document.querySelector('%s [data-act=decline]')" % row) and S.case(harb['caseId'])['decision']['by'] == 'owner' and
          S.case(harb['caseId'])['decision']['outcome'] == 'decline' and S.case(harb['caseId'])['decision']['reason'] == 'Too large for a first order (page check).', S.case(harb['caseId'])['decision'])
    sent = p.js('window.__w')
    check('D1 the decision sent version, reason, Idempotency-Key and the csrf token, one request', len(sent) == 1 and '/decide' in sent[0]['u'] and isinstance(json.loads(sent[0]['b'])['version'], int) and sent[0]['h'].get('Idempotency-Key') and len(sent[0]['h'].get('X-Nucleon-CSRF', '')) > 10, sent)
    check('D1 the decision appears under Recently reviewed with its timeline link', p.has('[data-testid=reviewed-row][data-case="%s"]' % harb['caseId']) and 'You declined' in p.text('[data-testid=reviewed-row][data-case="%s"]' % harb['caseId']))
    check('D1 a decision event was written once (decide_start/decide_done are page events, not case events)', S.sql("SELECT COUNT(*) FROM case_events WHERE case_id=? AND kind='decided'", harb['caseId'])[0][0] == 1)

    # ---- hold: exception
    mrow = '[data-case="%s"]' % moon['caseId']
    p.click(mrow + ' [data-open]')
    check('D2 a held case offers "Approve as an exception"', 'Approve as an exception' in p.text(mrow + ' [data-act=approve]'), p.text(mrow)[:200])
    p.fill(mrow + ' [data-why]', 'A known customer vouched for them (page check).')
    p.click(mrow + ' [data-act=approve]')
    check('D2 approving records an Owner exception', p.wait("!document.querySelector('%s [data-act=approve]')" % mrow) and S.case(moon['caseId'])['decision']['by'] == 'owner_exception', S.case(moon['caseId'])['decision'])

    # ---- extension: the request decision route
    crow = '[data-case="%s"]' % city['caseId']
    p.click(crow + ' [data-open]')
    check('D3 an escalated extension row links to the whole request', p.attr(crow + ' [data-testid=open-request]', 'href') == '#/case/' + city['requestId'])
    p.click(crow + ' [data-act=approve]')
    check('D3 approving an extension with no reason asks for one', 'Enter a brief reason.' in p.text(crow))
    p.fill(crow + ' [data-why]', 'Ordinary request, approved here (page check).')
    p.click(crow + ' [data-act=approve]')
    ok = p.wait("!document.querySelector('%s [data-act=approve]')" % crow)
    r = S.api('/api/requests/' + city['requestId'], None, S.cookie['owner'])[1]
    check('D3 the request decision route recorded the approval with the reason and the date asked for', ok and r['decision']['outcome'] == 'approve' and r['decision']['reason'] == 'Ordinary request, approved here (page check).' and r['decision']['approvedDueDate'], r.get('decision'))
    check('D3 the delegation case is decided by the Owner too', S.case(city['caseId'])['status'] == 'decided' and S.case(city['caseId'])['decision']['by'] == 'owner')
    rrow = '[data-case="%s"]' % river['caseId']
    p.click(rrow + ' [data-open]'); p.fill(rrow + ' [data-why]', 'Records are incomplete (page check).'); p.click(rrow + ' [data-act=decline]')
    check('D3 declining an extension records a decline with no date', p.wait("!document.querySelector('%s [data-act=decline]')" % rrow) and S.api('/api/requests/' + river['requestId'], None, S.cookie['owner'])[1]['decision']['outcome'] == 'decline')
    check('D3 waiting is now empty and the count hidden', p.has('[data-testid=waiting-none]') and p.js("document.querySelector('[data-testid=waiting-count]').hidden"))

    # ---- autonomous decisions: agree, disagree, override
    arow = '[data-case="%s"]' % ext_bay['caseId']
    p.click(arow + ' [data-open]')
    p.fill(arow + ' [data-why]', 'Typed before the page reads again.')
    check('E1 the buttons are Agree, Disagree and Override, and the Override button says what it does', p.has(arow + ' [data-act=agree]') and p.has(arow + ' [data-act=disagree]') and 'decline and restore the due date' in p.text(arow + ' [data-act=override]'))
    p.fill(arow + ' [data-why]', ''); p.click(arow + ' [data-act=disagree]')
    check('E1 disagree needs a reason', 'Enter a brief reason.' in p.text(arow) and not S.case(ext_bay['caseId'])['feedback'])
    p.click(arow + ' [data-act=agree]')
    check('E1 agree is one click with no reason, recorded as an explicit agreement and shown under Recently reviewed', p.wait("!!document.querySelector('[data-testid=reviewed-row][data-case=\"%s\"]')" % ext_bay['caseId']) and
          S.case(ext_bay['caseId'])['feedback'][-1]['verdict'] == 'agree' and 'You agreed' in p.text('[data-testid=reviewed-row][data-case="%s"]' % ext_bay['caseId']), S.case(ext_bay['caseId'])['feedback'])
    drow = '[data-case="%s"]' % trial_n8['caseId']
    p.click(drow + ' [data-open]'); p.fill(drow + ' [data-why]', 'I would not have approved this (page check).'); p.click(drow + ' [data-act=disagree]')
    check('E2 disagree with a reason is recorded and listed as reviewed', p.wait("!!document.querySelector('[data-testid=reviewed-row][data-case=\"%s\"]')" % trial_n8['caseId']) and S.case(trial_n8['caseId'])['feedback'][-1]['verdict'] == 'disagree' and not S.case(trial_n8['caseId'])['decision'].get('overridden'))
    orow = '[data-case="%s"]' % trial_n7['caseId']
    p.click(orow + ' [data-open]'); p.click(orow + ' [data-act=override]')
    check('E3 override with no reason asks for one and shows no confirmation yet', 'Enter a brief reason.' in p.text(orow) and not p.has('[data-testid=override-confirm]'))
    p.fill(orow + ' [data-why]', 'Revoke it (page check).'); p.click(orow + ' [data-act=override]')
    check('E3 override first shows what it does NOT undo, before anything is changed', p.wait("!!document.querySelector('[data-testid=override-confirm]')") and 'sent nothing' in p.text('[data-testid=override-effects]') and
          not S.case(trial_n7['caseId'])['decision'].get('overridden'), p.text('[data-testid=override-effects]')[:200])
    p.click('[data-testid=act-override-cancel]')
    check('E3 "Not now" leaves the case alone and keeps the reason typed', not p.has('[data-testid=override-confirm]') and p.js("document.querySelector('%s [data-why]').value" % orow) == 'Revoke it (page check).' and not S.case(trial_n7['caseId'])['decision'].get('overridden'))
    p.click(orow + ' [data-act=override]'); p.wait("!!document.querySelector('[data-testid=override-confirm]')")
    p.click('[data-testid=act-override-confirm]')
    check('E3 confirming overrides: the credit line is revoked, the page repeats what it does not undo', p.wait("!!document.querySelector('[data-testid=reviewed-row][data-case=\"%s\"]')" % trial_n7['caseId']) and S.case(trial_n7['caseId'])['decision'].get('overridden') is True and
          'Staff must follow up' in p.text('[data-testid=notice]'), p.text('[data-testid=notice]')[:200])
    fb = [x for x in p.js('window.__w') if '/feedback' in x['u']]
    check('E3 every feedback carried the version it showed and an Idempotency-Key; the override says override: true', all(isinstance(json.loads(x['b']).get('version'), int) and x['h'].get('Idempotency-Key') for x in fb) and any(json.loads(x['b']).get('override') is True for x in fb), len(fb))

    # ---- a stale version: the case changes behind the page; the click is refused and the row is read again
    srow = '[data-case="%s"]' % trial_n6['caseId']
    p.click(srow + ' [data-open]')
    s_, out_, _ = S.owner('/api/decision-cases/' + trial_n6['caseId'] + '/feedback', {'verdict': 'agree', 'reason': 'Another tab.', 'version': S.case(trial_n6['caseId'])['version']}, 'behind-1')
    check('F1 (setup) the case was changed behind the page', s_ == 200, out_)
    n_fb = len(S.case(trial_n6['caseId'])['feedback'])
    p.fill(srow + ' [data-why]', 'Disagree from a stale page (page check).')
    p.click(srow + ' [data-act=disagree]')
    check('F1 a stale case version is refused: the page says the case changed and nothing was recorded', p.wait("document.querySelector('[data-testid=notice]')?.innerText.includes('changed while you were reading it')") and
          len(S.case(trial_n6['caseId'])['feedback']) == n_fb, p.text('[data-testid=notice]'))
    check('F1 the row is read again: it has moved to Recently reviewed (the other tab agreed) and nothing else was written', p.has('[data-testid=reviewed-row][data-case="%s"]' % trial_n6['caseId']))

    # ---- the tacit agreement is shown as the policy's doing
    # (a fresh scratch server below is used for it: here the setting is off)
    check('G1 with the setting off, no row says "treated as agreed"', 'Treated as agreed' not in p.text())

    # ---- links: timeline
    p.click('[data-testid=reviewed-row][data-case="%s"] [data-testid=row-timeline]' % ext_bay['caseId'])
    check('H1 a row\'s timeline link opens the case timeline', p.wait("!!document.querySelector('[data-testid=timeline-page]')") and p.js('location.hash') == '#/decision-cases/' + ext_bay['caseId'], p.js('location.hash'))
    check('H1 Review stays the current page in the navigation while reading a case', p.js("document.querySelector('header.top a[aria-current=page]')?.dataset.area") == 'review')

    # ---- timeline content (Owner)
    p.go('#/decision-cases/' + ext_bay['caseId']); p.wait("!!document.querySelector('[data-testid=timeline-page]')"); time.sleep(0.3)
    kinds = p.js("[...document.querySelectorAll('[data-testid=tl-event]')].map(e => e.dataset.kind)")
    api_kinds = [e['kind'] for e in S.api('/api/decision-cases/%s/events' % ext_bay['caseId'], None, S.cookie['owner'])[1]['events']]
    check('T1 the timeline lists every recorded event, in the recorded order (created, evaluated, decided, then the Owner\'s feedback and view)', kinds == api_kinds and kinds[:3] == ['created', 'evaluated', 'decided'] and 'feedback' in kinds, kinds)
    check('T1 each event shows its time, who did it and the policy version', all('policy v1' in t and ' by ' in t for t in p.js("[...document.querySelectorAll('[data-testid=tl-event] .hint')].map(e => e.innerText)")))
    states = p.js("[...document.querySelectorAll('[data-testid=stages] .tl-stage')].map(e => [e.dataset.stage, e.dataset.state])")
    check('T1 the six loop stages are marked: request, evidence (not needed), evaluation, decision reached; Owner feedback now; outcome not yet', [s[0] for s in states] == ['request', 'evidence', 'evaluation', 'decision', 'feedback', 'outcome'] and
          dict(states)['request'] == 'done' and dict(states)['decision'] == 'done' and dict(states)['feedback'] == 'current' and dict(states)['outcome'] == 'todo' and dict(states)['evidence'] == 'todo', states)
    check('T1 the three dimensions are shown from the frozen evaluation, with the track-record wording', all(p.has('[data-testid=dim-%s]' % d) for d in ('evidence', 'risk', 'reliability')) and 'Setting:' in p.text('[data-testid=dim-reliability-sources]'), p.text('[data-testid=dimensions]')[:200].replace('\n', ' | '))
    check('T1 the decision line names the agent and the Owner policy version', 'Decided by the agent under Owner policy v1' in p.text('[data-testid=decision-line]'), p.text('[data-testid=decision-line]'))
    check('T1 the Owner\'s feedback is shown to the Owner', 'You agreed' in p.text('[data-testid=feedback-list]'), p.text('[data-testid=feedback-list]'))
    check('T1 the outcome is "pending" when nothing has been observed, and the current ledger is shown apart, labelled', p.has('[data-testid=outcome-pending]') and 'pending' in p.text('[data-testid=outcome-pending]') and p.has('[data-testid=tl-outcome-pending]') and
          'Current ledger says' in p.text('[data-testid=outcome-now]') and 'read now, not stored' in p.text('[data-testid=outcome-now]'), p.text('[data-testid=outcome]') if False else p.text('#main')[-600:])
    S.owner('/api/delegation/observe-outcomes', {}, 'obs-1')
    p.go('#/'); p.go('#/decision-cases/' + ext_bay['caseId']); p.wait("!!document.querySelector('[data-testid=outcome-observed]')")
    check('T2 after outcomes are observed, the observed outcome shows with when, apart from what the ledger says now', 'Observed:' in p.text('[data-testid=outcome-observed]') and 'recorded' in p.text('[data-testid=outcome-observed]') and not p.has('[data-testid=outcome-pending]') and
          p.has('[data-testid=outcome-now]') and 'outcome_observed' in p.js("[...document.querySelectorAll('[data-testid=tl-event]')].map(e => e.dataset.kind).join()"), p.text('[data-testid=outcome-observed]'))
    check('T2 the stage strip now has the outcome stage as the current one', dict(p.js("[...document.querySelectorAll('[data-testid=stages] .tl-stage')].map(e => [e.dataset.stage, e.dataset.state])"))['outcome'] == 'current')
    # an escalated, Owner-decided case with a lot of kinds: evidence asked, given, decided
    p.go('#/decision-cases/' + lake['caseId']); p.wait("!!document.querySelector('[data-testid=timeline-page]')"); time.sleep(0.3)
    check('T3 a case still gathering evidence shows the evidence stage as the current one and no decision', dict(p.js("[...document.querySelectorAll('[data-testid=stages] .tl-stage')].map(e => [e.dataset.stage, e.dataset.state])"))['evidence'] == 'current' and p.has('[data-testid=decision-none]') and
          p.js("[...document.querySelectorAll('[data-testid=tl-event]')].map(e => e.dataset.kind).join()") == 'created,evaluated,evidence_requested')
    p.go('#/decision-cases/case_missing'); 
    check('T3 an unknown case says so', p.wait("!!document.querySelector('[data-testid=timeline-missing]')"))
    p.sign_out()

    # ---- Staff on the timeline: no Owner reasons or feedback
    p.open('#/decision-cases/' + harb['caseId']); p.sign_in('staff')
    check('S1 Staff can open a case timeline', p.wait("!!document.querySelector('[data-testid=timeline-page]')"))
    page = p.text('#main')
    check('S1 Staff see no Owner reason, feedback section or viewed event, and the feedback stage is marked Owner only', 'Too large for a first order' not in page and not p.has('[data-testid=feedback-list]') and not p.has('[data-testid=feedback-none]') and
          not p.js("[...document.querySelectorAll('[data-testid=tl-event]')].some(e => ['feedback','viewed','tacit_agree'].includes(e.dataset.kind))") and
          p.js("document.querySelector('[data-stage=feedback]').dataset.state") == 'private' and 'viewed' not in p.js("[...document.querySelectorAll('[data-testid=tl-event]')].map(e => e.dataset.kind).join()"), page[:200].replace('\n', ' | '))
    check('S1 the Staff back link goes to Requests, and Requests is the current page', p.attr('.back a', 'href') == '#/cases' and p.js("document.querySelector('header.top a[aria-current=page]')?.dataset.area") == 'requests')
    check('S1 the decision line for Staff has no reason', not p.has('[data-testid=decision-reason]'))
    p.go('#/decision-cases/' + ext_bay['caseId']); p.wait("!!document.querySelector('[data-testid=timeline-page]')"); time.sleep(0.3)
    check('S1 Staff see an agent-decided case without the Owner\'s feedback', 'You agreed' not in p.text('#main') and not p.has('[data-testid=feedback-list]'))
    p.sign_out()
    check('Z no page error was thrown', not p.b.errors(), p.b.errors()[:2])
    p.b.close()
    S.stop()

    # ================================================================ C. page-use events (D11) and the 390 px layout
    C = Scratch(tmp, 'c')
    s_, rec, _ = C.api('/api/records/customers', {'name': 'Mooncove Bakery (fictional)'}, C.cookie['staff'], 'cust-moon')
    harb2 = C.resolve({'kind': 'trial_credit', 'customerId': IDS['harbourline'], 'orderAmount': '5000.00', 'termsDays': 14}, 'c-harb')
    bay2 = C.resolve({'kind': 'extension', 'customerId': IDS['bayview'], 'invoiceReference': 'DEMO-301', 'requestedDueDate': '2026-11-10'}, 'c-bay')
    asked_cid, asked = C.asked_trial('Waiting Cafe')
    q = Page(C)

    def events():
        q.js('flushTrack(); true'); time.sleep(0.6)
        return [(r[0], r[1], r[2], r[3], json.loads(r[4] or '{}')) for r in C.sql('SELECT role, page, kind, channel, data FROM ui_events ORDER BY seq')]
    q.open(); q.sign_in('owner'); q.wait("!!document.querySelector('[data-testid=home-page]')")
    q.click('[data-testid=home-review]'); q.wait("!!document.querySelector('[data-testid=review-page]')")
    row = '[data-case="%s"]' % harb2['caseId']
    q.click(row + ' [data-open]'); q.fill(row + ' [data-why]', 'Secret reason text that must not leave the page (page check).')
    q.click(row + ' [data-act=decline]'); q.wait("!document.querySelector('%s [data-act=decline]')" % row)
    q.go('#/delegation'); q.wait("!!document.querySelector('[data-testid=delegation-page]')")
    q.click('#dg-pause'); q.wait("!!document.querySelector('[data-testid=resume]')")
    q.click('#dg-pause'); q.wait("!!document.querySelector('[data-testid=pause]')")
    q.go('#/'); q.wait("!!document.querySelector('[data-testid=home-page]')")
    ev = events()
    kinds = [(e[1], e[2]) for e in ev]
    check('U1 the Owner\'s pages report: entering home, review, the control panel; leaving each', ('home', 'page_enter') in kinds and ('review', 'page_enter') in kinds and ('delegation', 'page_enter') in kinds and ('review', 'page_leave') in kinds and ('delegation', 'page_leave') in kinds, kinds[:14])
    check('U1 a page_leave carries the time on the page in ms', all(isinstance(e[4].get('ms'), int) and e[4]['ms'] >= 0 for e in ev if e[2] == 'page_leave') and any(e[2] == 'page_leave' for e in ev))
    clicks = [e[4].get('name') for e in ev if e[2] == 'click']
    check('U1 clicks on marked elements are reported by name: the big link, Approve/Decline, Pause and Resume', {'home-review', 'review-decline', 'panel-pause', 'panel-resume'} <= set(clicks), clicks)
    check('U1 a review decision reports decide_start and a decide_done with its duration and result', any(e[2] == 'decide_start' for e in ev) and any(e[2] == 'decide_done' and e[4].get('name') == 'decline' and e[4].get('ok') is True and isinstance(e[4].get('ms'), int) for e in ev), [e for e in ev if e[2].startswith('decide')])
    check('U1 the events are the Owner\'s, from a person session, and carry no case id, customer or typed text', all(e[0] == 'owner' and e[3] == 'person' for e in ev) and 'Secret reason' not in json.dumps(ev) and 'case_' not in json.dumps(ev) and 'Harbourline' not in json.dumps(ev), json.dumps(ev)[:200])
    # the page is closing: sendBeacon, naming the role in the address
    q.js("window.__beacon = []; const real = navigator.sendBeacon.bind(navigator); navigator.sendBeacon = (u, d) => { window.__beacon.push(String(u)); return real(u, d); }; true")
    before = len(events())
    q.go('#/review'); q.wait("!!document.querySelector('[data-testid=review-page]')"); time.sleep(0.3)
    q.js("window.dispatchEvent(new Event('pagehide')); true"); time.sleep(0.8)
    after = C.sql('SELECT COUNT(*) FROM ui_events')[0][0]
    check('U2 when the page is closing the events go by sendBeacon (the role in the address) and arrive', q.js('window.__beacon').__len__() >= 1 and q.js('window.__beacon')[0].endswith('/api/ui-events?role=owner') and after > before, (q.js('window.__beacon'), before, after))
    s_, summary, _ = C.api('/api/delegation/ui-summary', None, C.cookie['owner'])
    pages = {x['page']: x for x in summary['pages']}
    check('U3 the summary counts visits per page and the median time on a page from what the pages sent', s_ == 200 and pages['review']['enters'] >= 2 and pages['delegation']['enters'] == 1 and pages['delegation']['medianDwellSeconds'] is not None, summary['pages'])
    check('U3 and the named clicks and the decisions', any(b['name'] == 'review-decline' for b in summary['buttons']) and summary['decisions']['done'] >= 1, summary['buttons'][:3])
    q.sign_out()
    q.open(); q.sign_in('staff'); q.wait("!!document.querySelector('[data-testid=home-page]')")
    q.click('[data-testid=home-requests]'); time.sleep(0.5)
    ev2 = events()
    check('U4 Staff report too, under their role', any(e[0] == 'staff' and e[2] == 'page_enter' for e in ev2) and any(e[0] == 'staff' and e[2] == 'click' and e[4].get('name') == 'home-requests' for e in ev2), [e for e in ev2 if e[0] == 'staff'][:3])
    check('U4 Staff cannot read the usage summary', C.api('/api/delegation/ui-summary', None, C.cookie['staff'])[0] == 403)
    q.sign_out()
    n_rows = C.sql('SELECT COUNT(*) FROM ui_events')[0][0]
    q.open(); q.sign_in('agent'); q.wait("!!document.querySelector('[data-testid=home-page]')"); q.go('#/review'); time.sleep(0.5); q.go('#/'); q.js('flushTrack(); true'); time.sleep(0.6)
    check('U5 the AI Agent identity\'s page reports nothing', C.sql('SELECT COUNT(*) FROM ui_events')[0][0] == n_rows, (n_rows, C.sql('SELECT COUNT(*) FROM ui_events')[0][0]))
    q.sign_out()

    # ---- the 390 px layout of the new pages
    q.open(); q.sign_in('owner'); q.wait("!!document.querySelector('[data-testid=home-page]')")
    q.phone(True)
    q.go('#/review'); q.wait("!!document.querySelector('[data-testid=review-page]')"); time.sleep(0.4)
    q.click('[data-case="%s"] [data-open]' % bay2['caseId']); q.fill('[data-case="%s"] [data-why]' % bay2['caseId'], 'A reason long enough to wrap onto more than one line on a phone screen (page check).')
    q.click('[data-case="%s"] [data-act=override]' % bay2['caseId']); q.wait("!!document.querySelector('[data-testid=override-confirm]')")
    check('L1 the Review page (a row open, the override confirmation showing) has no horizontal scroll at 390 px', q.no_hscroll(), q.width_info())
    q.go('#/decision-cases/' + bay2['caseId']); q.wait("!!document.querySelector('[data-testid=timeline-page]')"); time.sleep(0.4)
    check('L1 the case timeline has no horizontal scroll at 390 px', q.no_hscroll(), q.width_info())
    q.go('#/dashboard'); q.wait("!!document.querySelector('[data-testid=dashboard-page]')"); time.sleep(0.4)
    check('L1 the dashboard has no horizontal scroll at 390 px', q.no_hscroll(), q.width_info())
    q.go('#/delegation'); q.wait("!!document.querySelector('[data-testid=delegation-page]')"); time.sleep(0.4)
    q.js("document.querySelector('.dg-advanced').open = true; true")
    check('L1 the control panel with its new settings has no horizontal scroll at 390 px', q.no_hscroll(), q.width_info())
    q.phone(False)
    q.sign_out()
    q.open(); q.sign_in('staff'); q.wait("!!document.querySelector('[data-testid=home-page]')"); q.phone(True); time.sleep(0.4)
    check('L1 the Staff home page with the evidence list has no horizontal scroll at 390 px', q.has('[data-testid=home-evidence]') and q.no_hscroll(), q.width_info())
    q.go('#/decision-cases/' + bay2['caseId']); q.wait("!!document.querySelector('[data-testid=timeline-page]')"); time.sleep(0.3)
    check('L1 the Staff case timeline has no horizontal scroll at 390 px', q.no_hscroll(), q.width_info())
    q.phone(False)
    check('Z no page error was thrown (scenario C)', not q.b.errors(), q.b.errors()[:2])
    q.b.close(); C.stop()

    # ================================================================ D. the tacit agreement is shown as the policy's doing, never as the Owner's words
    D = Scratch(tmp, 'd')
    bay3 = D.resolve({'kind': 'extension', 'customerId': IDS['bayview'], 'invoiceReference': 'DEMO-301', 'requestedDueDate': '2026-11-10'}, 'd-bay')
    north3 = D.resolve({'kind': 'trial_credit', 'customerId': IDS['northside'], 'orderAmount': '800.00', 'termsDays': 14}, 'd-north')
    import sqlite3
    con = sqlite3.connect(D.db_path)
    for cid in (bay3['caseId'], north3['caseId']):
        data = json.loads(con.execute('SELECT data FROM decision_cases WHERE id=?', (cid,)).fetchone()[0]); data['decision']['at'] = '2026-10-01T09:00:00+00:00'
        con.execute('UPDATE decision_cases SET data=? WHERE id=?', (json.dumps(data), cid))
    con.commit(); con.close()
    pol = D.api('/api/delegation/policy', None, D.cookie['owner'])[1]
    s_, out, _ = D.owner('/api/delegation/policy', {**delegation_demo.DEMO_POLICY, 'feedback': {'tacitAgreeAfterDays': 3}, 'expectedVersion': pol['version']}, method='PUT')
    assert s_ == 200, out
    r = Page(D)
    r.open('#/review'); r.sign_in('owner'); r.wait("!!document.querySelector('[data-testid=review-page]')"); time.sleep(0.5)
    tacit_row = '[data-case="%s"]' % bay3['caseId']
    label = r.text(tacit_row + ' [data-testid=tacit-label]')
    check('G2 a tacit agreement is labelled "Treated as agreed after 3 days (no Owner objection)" on the Review page and is still listed to review', label == 'Treated as agreed after 3 days (no Owner objection)' and r.attr(tacit_row, 'data-tacit') == 'true', label)
    check('G2 the label does not claim the Owner wrote it: no "You agreed", no system sentence as a reason', 'You agreed' not in r.text(tacit_row) and 'policy setting' not in r.text(tacit_row), r.text(tacit_row)[:200])
    check('G2 the stored feedback is the policy\'s: verdict tacit_agree with afterDays 3', D.case(bay3['caseId'])['feedback'][-1]['verdict'] == 'tacit_agree' and D.case(bay3['caseId'])['feedback'][-1]['afterDays'] == 3)
    r.click(tacit_row + ' [data-open]'); r.click(tacit_row + ' [data-act=agree]')
    check('G3 the Owner\'s explicit agreement replaces it: the row is reviewed ("You agreed") and the standing verdict is agree', r.wait("!!document.querySelector('[data-testid=reviewed-row][data-case=\"%s\"]')" % bay3['caseId']) and
          'You agreed' in r.text('[data-testid=reviewed-row][data-case="%s"]' % bay3['caseId']) and D.case(bay3['caseId'])['feedback'][-1]['verdict'] == 'agree' and len(D.case(bay3['caseId'])['feedback']) == 2)
    r.go('#/delegation'); r.wait("!!document.querySelector('[data-testid=delegation-page]')")
    north_card = '[data-testid=agent-decision][data-case="%s"]' % north3['caseId']
    check('G4 the control panel shows the other tacit one as "Treated as agreed after 3 days (no Owner objection)", never as feedback the Owner gave', 'Treated as agreed after 3 days (no Owner objection)' in r.text(north_card) and 'your feedback' not in r.text(north_card) and
          'tacit_agree' not in r.text(north_card) and 'policy setting' not in r.text(north_card), r.text(north_card)[:300].replace('\n', ' | '))
    r.go('#/decision-cases/' + north3['caseId']); r.wait("!!document.querySelector('[data-testid=timeline-page]')"); time.sleep(0.3)
    check('G5 the timeline shows the tacit_agree event and the feedback list in the same words', 'Treated as agreed after 3 days (no Owner objection)' in r.text('[data-testid=feedback-list]') and
          r.js("[...document.querySelectorAll('[data-testid=tl-event][data-kind=tacit_agree]')].length") == 1 and 'Treated as agreed after 3 days' in r.text('[data-testid=tl-event][data-kind=tacit_agree]'), r.text('[data-testid=feedback-list]'))
    check('Z no page error was thrown (scenario D)', not r.b.errors(), r.b.errors()[:2])
    r.b.close(); D.stop()
finally:
    for name in ('S', 'C', 'D'):
        if globals().get(name):
            try: globals()[name].stop()
            except Exception: pass
    shutil.rmtree(tmp, ignore_errors=True)
sys.exit(check.finish())
