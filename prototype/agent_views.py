"""The compact, model-facing results of the S3 read tools (whatIsNeeded, comparableCases, customerStatus, policyBacktest, impactSummary), and the pure
arithmetic behind the Owner's what-if. Pure: plain dicts in, plain dicts out; no database, no clock, no model. The full result of each tool is unchanged
for any client that shows it; `forModel` is what the Lab gives the model as the tool's text (lab/mcp_server.py model_text), written by code, so the
model repeats numbers and sentences it did not make up. A status tool's forModel is at most STATUS_LIMIT characters of JSON, an analysis tool's at most
ANALYSIS_LIMIT; if it is too long the lists and then the sentences are shortened, never the status. Compatible with Python 3.9."""
import json

QUEUE_LIMIT = 1800      # workQueue: the sentence that lists every waiting case must fit whole
STATUS_LIMIT = 600     # whatIsNeeded and customerStatus (the same bound as the decision tools' forModel)
ANALYSIS_LIMIT = 1500  # comparableCases, policyBacktest, impactSummary: they carry figures the model reports


def clip(text, n):
    text = ' '.join(str(text).split())
    return text if len(text) <= n else text[:max(0, n - 1)].rstrip() + '…'


def size(out):
    return len(json.dumps(out))   # as a JSON client sends it (ASCII escapes count: a clipped text's ellipsis is 6 characters there)


def fit(out, limit, lists=(), strings=()):
    """Shorten `out` in place to at most `limit` characters of JSON: drop the last item of each named list (down to one), then clip the named strings, then drop
    what is left of the lists. Fields not named are never touched."""
    for key in lists:
        while size(out) > limit and isinstance(out.get(key), list) and len(out[key]) > 1:
            out[key].pop()
    for key in strings:   # again while the clip itself (its ellipsis, 6 characters as JSON) keeps it over; never below 40 characters
        while size(out) > limit and isinstance(out.get(key), str) and len(out[key]) > 40:
            out[key] = clip(out[key], max(40, len(out[key]) - (size(out) - limit)))
    for key in lists:
        if size(out) > limit and isinstance(out.get(key), list):
            out[key] = []
    return out


def join(items):
    items = [str(i) for i in items]
    return ', '.join(items[:-1]) + ' and ' + items[-1] if len(items) > 1 else (items[0] if items else '')


# ---------------------------------------------------------------- whatIsNeeded

def needs_view(kind, customer_name, evidence):
    """{status, staffCanProvide [{need, how}], staffCannotProvide [label], statusText, nextStep} for the evidence section of an evaluation (delegation.assess_evidence).
    `status` is the evidence status: sufficient | missing | insufficient | contradictory. Written by code."""
    can = [{'need': m['label'], 'how': clip(m.get('how') or m['detail'], 110)} for m in evidence.get('missing', [])]
    cannot = [i['label'] for i in evidence.get('insufficient', [])]
    wrong = [c.get('key', '').replace('_', ' ') for c in evidence.get('contradictions', [])]
    status = evidence['status']
    if status == 'sufficient':
        text = 'Nothing more is needed from Staff for this ' + ('trial credit' if kind == 'trial_credit' else 'extension') + ' for ' + customer_name + ': the evidence on file is sufficient.'
        step = 'Now call resolveDecision. This check stored nothing.'
    elif status == 'missing':
        text = 'Check only, not a decision. Staff can provide: ' + join(m['need'].lower() for m in can) + '.' + (' Staff cannot provide: ' + join(c.lower() for c in cannot) + ' (it goes to the Owner).' if cannot else '')
        step = 'This is a check and nothing was stored. Call resolveDecision to submit the request; Nucleon then asks Staff for these on its page.'
    elif status == 'contradictory':
        text = 'The evidence contradicts the records (' + join(wrong) + '), so the request would be on hold for the Owner.'
        step = 'Now call resolveDecision; the Owner resolves the hold. Do not say it is approved.'
    else:
        text = 'The records are insufficient and Staff cannot supply what is missing (' + join(c.lower() for c in cannot) + '), so the Owner would decide.'
        step = 'Now call resolveDecision; the Owner decides. Do not say it is approved.'
    return {'status': status, 'staffCanProvide': can, 'staffCannotProvide': cannot, 'statusText': text, 'nextStep': step}


def needs_for_model(kind, customer_name, evidence):
    out = needs_view(kind, customer_name, evidence)
    out = {'status': out['status'], 'statusText': out['statusText'], 'staffCanProvide': out['staffCanProvide'], 'staffCannotProvide': out['staffCannotProvide'], 'nextStep': out['nextStep']}
    return fit(out, STATUS_LIMIT, lists=('staffCanProvide', 'staffCannotProvide'), strings=('nextStep', 'statusText'))


# ---------------------------------------------------------------- comparableCases

def comparables_for_model(kind, customer_name, comps, declined_majority, owner):
    """A short list of the comparables the evaluation used, each an analogy unless it is the same customer's own earlier case. An Owner reason is shown (clipped)
    to the Owner only; the full result already has it stripped for Staff."""
    rows = []
    for c in comps:
        row = {'id': c['id'], 'dataset': 'fictional example' if c.get('fictional') else 'live', 'similarity': c['similarity'], 'sameCustomer': bool(c['sameCustomer']),
               'ownerDecision': c['ownerDecision'], 'outcome': c.get('outcome'), 'summary': clip(c.get('summary') or '', 70)}
        if owner and c.get('ownerReason'):
            row['ownerReason'] = clip(c['ownerReason'], 70)
        rows.append(row)
    n = len(comps)
    declined = sum(1 for c in comps if c['ownerDecision'] == 'decline')
    text = ('No reviewed comparable case exists yet for this kind of request.' if not n else
            str(n) + ' closest reviewed ' + ('case' if n == 1 else 'cases') + ' for a ' + ('trial credit' if kind == 'trial_credit' else 'extension') + ' like this one: the Owner approved ' +
            str(n - declined) + ' and declined ' + str(declined) + (' (most were declined)' if declined_majority else '') + '. They are analogies, not ' + customer_name + "'s own history, unless marked sameCustomer.")
    out = {'status': 'comparables', 'statusText': text, 'declinedMajority': bool(declined_majority), 'comparables': rows,
           'nextStep': 'Report these as analogies. Nothing was stored and nothing was decided.'}
    return fit(out, ANALYSIS_LIMIT, lists=('comparables',), strings=('statusText', 'nextStep'))


# ---------------------------------------------------------------- customerStatus

def customer_status_for_model(customer_name, latest, cases, trial_line, waiting, outcome):
    """latest: the most recent live case view (caseId, kind, status, statusText) or None; cases: recent [{caseId, kind, status}]; trial_line: sentence or None;
    waiting: [{caseId, kind, needs [labels]}]; outcome: {caseId, outcome, asOf} or None. Every sentence is written by code."""
    if latest is None:
        out = {'status': 'no_case', 'statusText': 'There is no decision case for ' + customer_name + ' yet.', 'nextStep': 'If Staff want one, they ask for a trial credit or an extension.'}
        return out
    out = {'status': latest['status'], 'statusText': latest['statusText'], 'cases': [{'caseId': c['caseId'], 'kind': c['kind'], 'status': c['status']} for c in cases[:2]],
           'trialInForce': trial_line, 'waitingForStaff': [{'caseId': w['caseId'], 'kind': w['kind'], 'needs': w['needs']} for w in waiting],
           'lastOutcome': outcome, 'nextStep': 'Report the statusText. decisionStatus with a caseId gives one case. Nothing was changed.'}
    return fit(out, STATUS_LIMIT, lists=('cases', 'waitingForStaff'), strings=('statusText', 'trialInForce', 'nextStep'))


# ---------------------------------------------------------------- workQueue

def queue_for_model(role, summary_text, cases, others_count, requests=()):
    """workQueue for the model: the request queue in words (summary_text, written by code) and the decision cases waiting for this role, each with caseId, customer,
    kind, status, exposure, since and (for Staff) what is needed; the Owner's go to #/review; and the requests waiting for this role (compact rows). Nothing is lost when they are shortened: the full result is the card's. At most STATUS_LIMIT characters of JSON."""
    rows = [{'caseId': c['caseId'], 'customer': c['customer'], 'kind': c['kind'], 'status': c['status'], 'exposure': c['exposureText'], 'since': c['since'][:10],
             **({'needs': c['needs'], 'link': c['link']} if role == 'staff' else {})} for c in cases]
    # 12 Nov 2026: the Owner's assistant read the lists aloud with their field names and named 2 of 8 cases, because the sentence was called "requests" and was
    # clipped first. The sentence is now statusText (what the assistants repeat), comes first, and the lists give way before it does.
    out = {'status': 'work_queue', 'statusText': summary_text.strip(),
           'say': 'Repeat statusText as it is: it lists every case. Do not read out the lists below or their field names; they only give you ids for other tools.',
           'decisionCasesForYou': rows, 'decisionCasesWithOthers': others_count,
           'forYou': [{'requestId': r['requestId'], 'customer': (r.get('customer') or {}).get('name'), 'invoiceReference': r['invoiceReference'], 'status': r['status'], 'waitingOn': r['waitingOn']}
                      for r in requests]}
    if role == 'owner':
        out['link'] = '#/review'
    return fit(out, QUEUE_LIMIT, lists=('forYou', 'decisionCasesForYou'), strings=('statusText',))


# ---------------------------------------------------------------- policyBacktest

def deep_merge(base, changes):
    """The policy's rules with the Owner's partial changes applied: a section given as an object is merged into the section, any other value replaces it."""
    out = dict(base)
    for key, value in changes.items():
        out[key] = {**base[key], **value} if isinstance(base.get(key), dict) and isinstance(value, dict) else value
    return out


def changed_paths(base, changes):
    """The settings a partial change names, as 'section.key' (or the key itself), that actually differ from the base."""
    paths = []
    for key, value in changes.items():
        if isinstance(base.get(key), dict) and isinstance(value, dict):
            paths += [key + '.' + k for k, v in value.items() if base[key].get(k) != v]
        elif base.get(key) != value:
            paths.append(key)
    return paths


def tally_text(t):
    """One backtest tally (delegation.backtest) in a sentence: 'would approve 8 of 12 reviewed; the Owner approved 8 and declined 0 (agreement 100%)'."""
    if not t['reviewed']:
        return 'no reviewed cases'
    return ('would approve ' + str(t['wouldApprove']) + ' of ' + str(t['reviewed']) + ' reviewed; the Owner approved ' + str(t['ownerApproved']) + ' and declined ' + str(t['ownerDeclined']) +
            (' (agreement ' + str(t['agreement']) + ')' if t['agreement'] else ''))


def backtest_section(policy, kind, track_record):
    """What one policy would have decided on the reviewed cases of one kind: the fictional evaluation set (a SIMULATION) and the live Owner-reviewed cases, apart, plus
    whether the track-record gate (ladder step 7) would be established. `track_record` is delegation.track_record(policy, kind, memory)."""
    ev, live = track_record['evaluation'], track_record['live']
    keys = ('reviewed', 'wouldApprove', 'ownerApproved', 'ownerDeclined', 'agreement')
    return {'fictionalEvaluation': {k: ev[k] for k in keys}, 'live': {k: live[k] for k in keys}, 'trackRecord': track_record['status'], 'gatedOn': track_record['gatedOn']}


def backtest_for_model(version, paths, sections, label):
    """sections: {kind: {'current': backtest_section, 'withChanges': backtest_section}}. Strings written by code; the fictional evaluation set is labelled a simulation."""
    kinds = {}
    for kind, both in sections.items():
        kinds[kind] = {which: 'fictional simulation: ' + tally_text(s['fictionalEvaluation']) + '; live: ' + tally_text(s['live']) + '; track record ' + s['trackRecord'].replace('_', ' ')
                       for which, s in both.items()}
    text = ('Policy version ' + str(version) + ' with ' + ('these changes (' + join(paths) + ')' if paths else 'no changes') + ', counted on the reviewed cases. Nothing was saved: only the Owner '
            'saves a policy, on the Control panel.')
    out = {'status': 'backtest', 'statusText': text, 'changed': paths, 'categories': kinds, 'label': clip(label, 150)}
    return fit(out, ANALYSIS_LIMIT, strings=('label', 'statusText'))


# ---------------------------------------------------------------- impactSummary

def metric_text(m):
    if m is None:
        return None
    if m.get('value') is None:
        return 'not known yet' + (' (' + str(m['numerator']) + ' of ' + str(m['denominator']) + ')' if m.get('denominator') else '')
    if m.get('denominator'):
        return str(m['numerator']) + ' of ' + str(m['denominator']) + ' (' + str(m['value']) + ', ' + str(m['source']) + ')'
    return str(m['value']) + ' (' + str(m['source']) + ')'


def impact_for_model(report):
    """The impact report's headline figures, each with its numerator, denominator and source (live data only). Strings written by code."""
    ev, ttd, oit = report.get('evidenceRequests') or {}, report.get('timeToDecisionSeconds') or {}, report.get('ownerInterventionSeconds') or {}
    rows = [('autonomousCoverage', report.get('autonomousCoverage')), ('escalationRate', report.get('escalationRate')), ('evidenceRequests', ev.get('count')),
            ('evidenceStillPending', ev.get('pending')), ('medianSecondsToDecision', ttd.get('median')), ('medianOwnerSecondsPerCase', oit.get('median')),
            ('overrides', (report.get('overrides') or {}).get('count')), ('disagreements', (report.get('disagreements') or {}).get('count')),
            ('liveAgreement', (report.get('liveAgreement') or {}).get('agreementRate')), ('approvedAwaitingOutcome', (report.get('outcomes') or {}).get('pending'))]
    figures = {k: metric_text(v) for k, v in rows if isinstance(v, dict)}
    cases = report.get('cases')
    out = {'status': 'impact', 'dataset': 'live', 'statusText': 'Live cases only (the fictional examples are never counted): ' + (metric_text(cases) if isinstance(cases, dict) else 'n/a') + ' in the window. '
           'Every figure says its numerator, denominator and source; a figure that cannot be known yet is "not known yet", not zero. Time saved is an assumption nobody has measured.',
           'counts': {k: (v.get('value') if isinstance(v, dict) else v) for k, v in (report.get('counts') or {}).items()}, 'figures': figures, 'window': {k: v for k, v in (report.get('window') or {}).items() if k in ('from', 'to', 'policyVersion')}}
    return fit(out, ANALYSIS_LIMIT, strings=('statusText',))


# ---------------------------------------------------------------- doctor (11 Nov 2026)

DOCTOR_LIMIT = 2400
DOCTOR_CHANGE = 'You cannot change settings. The Owner changes them in Quick setup, which shows the effect before saving.'


def doctor_for_model(view, rules=None):
    """The Doctor's lines for the model: {status, question, statusText, enough, facts, howToChange}, every string written by code. The headline is statusText and
    is not repeated in facts. When the lines do not fit DOCTOR_LIMIT, findings and suggestions are dropped from the end and a line says how many; the notes
    (limits only, not tried, too few) are always kept."""
    if 'findings' in view:
        body, notes = list(view['findings']) + [s['text'] for s in view.get('suggestions') or []], list(view.get('notes') or [])
    else:
        body, notes = list(view.get('facts') or []), []
    out = {'status': 'doctor', 'question': view.get('question'), 'statusText': view.get('headline') or '', 'enough': view.get('enough', True), 'facts': body + notes,
           'howToChange': DOCTOR_CHANGE}
    if rules:   # 12 Nov 2026: asked "what are my rules?", the assistant could only say which rules sent requests to the Owner
        out['currentRules'] = rules
    dropped = 0
    while size(out) > DOCTOR_LIMIT and dropped < len(body):
        dropped += 1
        out['facts'] = body[:len(body) - dropped] + ['(' + str(dropped) + ' more lines left out; ask about one question at a time.)'] + notes
    return out
