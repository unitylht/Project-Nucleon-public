"""The impact report (slice S1b, docs/product/POV-IMPLEMENTATION-PLAN-20261030.md section 5): what the decision loop did, as numbers a person can check.

A pure computation over LIVE `decision_cases` and `case_events` rows (plain dicts): no database, no clock, no model. Every number is a metric object
{value, numerator, denominator, source, dataset, note}: `source` is `measured` (counted or timed from recorded events), `derived` (arithmetic on measured
numbers, such as a rate) or `assumption` (a figure nobody measured). `dataset` is always `live`: the fictional decision memory is never read here, so a
fictional and a live case are never one number. A value that cannot be established is None (never 0): an empty sample has no median.

Rates are the exact fraction numerator/denominator, shown as a decimal rounded half up to 4 places. Times are whole seconds between two recorded timestamps.
Compatible with Python 3.9."""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

DATASET = 'live'
KINDS = ('extension', 'trial_credit')
OBSERVED = ('on_time', 'late_paid', 'partial', 'open_not_due', 'open_past_due', 'written_off', 'unknown')   # outcomes.OUTCOMES (kept apart: this module is pure and standalone)
ESCALATING = ('owner_review', 'policy_hold')
OWNER_ACTIONS = ('decided', 'feedback', 'override')


def metric(value, numerator=None, denominator=None, source='measured', note=None):
    return {'value': value, 'numerator': numerator, 'denominator': denominator, 'source': source, 'dataset': DATASET, 'note': note}


def count(n, denominator=None, note=None):
    """A counted number (measured)."""
    return metric(n, n, denominator, 'measured', note)


def rate(num, den, note=None):
    """num/den as a decimal to 4 places, or None when there is nothing to divide by (unknown, never zero)."""
    value = None if not den else float((Decimal(num) / Decimal(den)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP))
    return metric(value, num, den, 'derived', note or ('No cases to divide by yet, so there is no rate (not zero).' if not den else None))


def _time(text):
    return datetime.fromisoformat(text)


def _seconds(start, end):
    return int((_time(end) - _time(start)).total_seconds())


def median(values):
    """The middle value (the mean of the two middle ones for an even count), or None for no values."""
    s = sorted(values)
    if not s:
        return None
    mid = len(s) // 2
    if len(s) % 2:
        return s[mid]
    total = s[mid - 1] + s[mid]
    return total // 2 if total % 2 == 0 else total / 2


def percentile(values, p):
    """The nearest-rank percentile (p in 1..100), or None for no values."""
    s = sorted(values)
    if not s:
        return None
    rank = -(-len(s) * p // 100)   # ceil(len * p / 100)
    return s[max(1, rank) - 1]


def spread(values, what, unit_note):
    """{median, p90, cases}: each a metric. An empty sample has no median or p90 (None)."""
    return {'median': metric(median(values), len(values), None, 'measured', unit_note), 'p90': metric(percentile(values, 90), len(values), None, 'measured',
                                                                                                         'Nearest-rank 90th percentile. ' + unit_note),
            'cases': count(len(values), note=what)}


# ---------------------------------------------------------------- one case, read

def decision_of(c):
    return c.get('decision') or {}


def agent_decided(c):
    return c.get('status') == 'decided' and decision_of(c).get('by') == 'agent'


def overridden(c):
    return agent_decided(c) and bool(decision_of(c).get('overridden'))


def owner_decided(c):
    return c.get('status') == 'decided' and decision_of(c).get('by') in ('owner', 'owner_exception')


def last_verdict(c):
    """The Owner's standing verdict on an agent decision: agree | disagree | tacit_agree, or None. A later explicit verdict replaces a tacit one."""
    f = c.get('feedback') or []
    return f[-1].get('verdict') if f and agent_decided(c) else None


def reached(c, events):
    """The case reached a decision or an escalation (it is not still gathering evidence): decided, awaiting the Owner or on hold, or closed after it had."""
    if c.get('status') in ('decided', 'awaiting_owner', 'on_hold'):
        return True
    return c.get('status') == 'closed' and any(e['kind'] in ('decided', 'escalated', 'held') for e in events)


def observation(c, events):
    """The latest stored outcome observation of a case (its outcomeObserved, else the last outcome_observed event): the vocabulary word, or None."""
    seen = (c.get('outcomeObserved') or {}).get('outcome')
    if seen:
        return seen
    last = [e for e in events if e['kind'] == 'outcome_observed']
    return (last[-1].get('data') or {}).get('outcome') if last else None


def observable(c):
    """outcomes.observe_case runs over approved, not overridden live decisions: only those can have (or still wait for) an observation."""
    return c.get('status') == 'decided' and decision_of(c).get('outcome') == 'approve' and not decision_of(c).get('overridden')


# ---------------------------------------------------------------- the counts every group shares

def counts_of(cases):
    """The stats-compatible counts (same definitions as App.delegation_stats) of a group of live cases, each a metric."""
    decided = [c for c in cases if c.get('status') == 'decided']
    agent = [c for c in decided if decision_of(c).get('by') == 'agent']
    raw = {'autonomous': sum(1 for c in agent if not decision_of(c).get('overridden') and decision_of(c).get('outcome') != 'decline'),
           'autonomousDeclined': sum(1 for c in agent if not decision_of(c).get('overridden') and decision_of(c).get('outcome') == 'decline'), 'gatheringEvidence': sum(1 for c in cases if c.get('status') == 'gathering_evidence'),
            'ownerReview': sum(1 for c in cases if c.get('status') == 'awaiting_owner'), 'onHold': sum(1 for c in cases if c.get('status') == 'on_hold'),
            'ownerDecided': sum(1 for c in decided if decision_of(c).get('by') in ('owner', 'owner_exception')), 'overrides': sum(1 for c in agent if decision_of(c).get('overridden')),
           'closed': sum(1 for c in cases if c.get('status') == 'closed')}
    return {k: count(v, len(cases), 'Same definition as GET /api/delegation/stats counts.') for k, v in raw.items()}


def group_metrics(cases, events_by_case):
    """The counted metrics that can be grouped (the whole window, or one policy version): coverage, escalation, overrides, disagreements, live agreement, outcomes."""
    ev = lambda c: events_by_case.get(c['id'], [])   # noqa: E731
    total = len(cases)
    reached_n = sum(1 for c in cases if reached(c, ev(c)))
    agent = [c for c in cases if agent_decided(c)]
    escalated = sum(1 for c in cases if c.get('handling') in ESCALATING)
    reviewed = [c for c in agent if last_verdict(c) in ('agree', 'disagree', 'tacit_agree')]
    explicit = [c for c in reviewed if last_verdict(c) in ('agree', 'disagree')]
    tacit = [c for c in reviewed if last_verdict(c) == 'tacit_agree']
    agreed = sum(1 for c in reviewed if last_verdict(c) in ('agree', 'tacit_agree'))
    watched = [c for c in cases if observable(c)]
    seen = {c['id']: observation(c, ev(c)) for c in watched}
    labels = {w: sum(1 for v in seen.values() if v == w) for w in OBSERVED}
    observed_n = sum(labels.values())
    return {
        'cases': count(total, note='Live cases in this window (the fictional decision memory is not counted).'),
        'autonomousCoverage': {**rate(len(agent), reached_n, 'Agent-decided cases (including any the Owner later overrode) over cases that reached a decision or an escalation, '
                                                              'so cases still gathering evidence are left out.')},
        'escalationRate': rate(escalated, total, 'Cases handled as owner_review or policy_hold over all cases in the window (including those still gathering evidence).'),
        'overrides': {'count': count(sum(1 for c in agent if overridden(c)), len(agent), 'Agent decisions the Owner overrode.'),
                      'rate': rate(sum(1 for c in agent if overridden(c)), len(agent), 'Overridden agent decisions over agent decisions.')},
        'disagreements': {'count': count(sum(1 for c in reviewed if last_verdict(c) == 'disagree'), len(reviewed),
                                         'Agent decisions whose standing Owner verdict is disagree (an override is one, a disagreement without override is another). Denominator: agent decisions with a verdict.')},
        'liveAgreement': {'explicit': count(len(explicit), len(reviewed), 'Agent decisions with an explicit Owner verdict (agree or disagree).'),
                          'tacit': count(len(tacit), len(reviewed), 'Agent decisions agreed tacitly under the policy\'s tacit-agreement setting (D8); labelled apart, never an Owner reason.'),
                          'agreementRate': rate(agreed, len(reviewed), '(agree + tacit agree) over agent decisions with a verdict. Owner-decided cases are not agent decisions and are not in it.')},
        'outcomes': {'byLabel': {w: count(labels[w], observed_n, 'Approved, not overridden cases whose latest stored observation is ' + w + '.') for w in OBSERVED},
                     'pending': count(len(watched) - observed_n, len(watched), 'Approved, not overridden decisions with no observation yet. Declined and overridden decisions are never observed and are not pending.'),
                     'neverObserved': count(sum(1 for c in cases if c.get('status') == 'decided' and not observable(c)), None,
                                            'Decided cases that are not observed by design: declined by the Owner, or overridden.')}}


def timing(cases, events_by_case):
    """The timed metrics: evidence turnaround, time to decision (created to decided), the Owner's time on a case (first viewed to the action)."""
    asked = answered = pending = 0
    turnaround, by_kind, owner_times, owner_unmeasured = [], {k: [] for k in KINDS}, [], 0
    missing_events = 0
    for c in cases:
        events = sorted(events_by_case.get(c['id'], []), key=lambda e: e['seq'])
        if not events:
            missing_events += 1
        waiting = None
        for e in events:
            if e['kind'] == 'evidence_requested':
                asked += 1
                waiting = waiting or e['at']
            elif e['kind'] == 'evidence_submitted' and waiting:
                answered += 1
                turnaround.append(_seconds(waiting, e['at']))
                waiting = None
        pending += 1 if waiting else 0
        created = next((e for e in events if e['kind'] == 'created'), None)
        decided = next((e for e in events if e['kind'] == 'decided'), None)
        if created and decided and c.get('kind') in by_kind:
            by_kind[c['kind']].append(_seconds(created['at'], decided['at']))
        viewed, handled = None, False
        for e in events:
            if e['kind'] == 'viewed' and viewed is None:
                viewed = e
            elif e['kind'] in OWNER_ACTIONS and (e['kind'] != 'decided' or e['actor'] == 'owner'):
                handled = True
                if viewed is not None:
                    owner_times.append(_seconds(viewed['at'], e['at']))
                    break
        if handled and viewed is None:
            owner_unmeasured += 1
    every = [s for v in by_kind.values() for s in v]
    return {
        'evidenceRequests': {'count': count(asked, None, 'evidence_requested events (a case asked again after a partial answer counts again).'),
                             'answered': count(answered, asked, 'Requests followed by an evidence_submitted event.'),
                             'pending': count(pending, None, 'Cases whose latest evidence request is still unanswered.'),
                             'medianTurnaroundSeconds': metric(median(turnaround), len(turnaround), None, 'measured',
                                                               'evidence_requested to the next evidence_submitted, over answered requests; None until one is answered.')},
        'timeToDecisionSeconds': {**spread(every, 'Cases with a created and a decided event.', 'Seconds from the created event to the decided event (an Owner-decided case includes the wait for the Owner).'),
                                  'byKind': {k: spread(by_kind[k], 'Cases of this kind with a created and a decided event.', 'Seconds from created to decided, ' + k + ' cases.') for k in KINDS}},
        'ownerInterventionSeconds': {'median': metric(median(owner_times), len(owner_times), None, 'measured',
                                                      'Seconds from the Owner first viewing a case to their first decided, feedback or override event on it. It needs the Owner page to post `viewed`; '
                                                      'until it does this is None, not zero.'),
                                     'cases': count(len(owner_times), None, 'Owner-handled cases with a viewed event before the action.'),
                                     'withoutView': count(owner_unmeasured, None, 'Owner-handled cases with no viewed event before the action: their time is unknown.')},
        'casesWithoutEvents': count(missing_events, None, 'Cases with no timeline rows (made before the timeline existed): their times are unknown, not zero.')}


def compute(cases, events, window=None):
    """The impact report for the live `cases` (decision_cases rows, as the server loads them) and their `events` (case_events rows as dicts with case_id, seq, kind, at, actor,
    policy_version, data), restricted to the window {from, to, policyVersion} (a case is in it by the day it was created and the policy version it was decided under; any
    part may be None). Pure."""
    window = window or {}
    cases = [c for c in cases if c.get('dataset', DATASET) == DATASET]
    if window.get('from'):
        cases = [c for c in cases if c['createdAt'][:10] >= window['from']]
    if window.get('to'):
        cases = [c for c in cases if c['createdAt'][:10] <= window['to']]
    if window.get('policyVersion') is not None:
        cases = [c for c in cases if (c.get('policy') or {}).get('version') == window['policyVersion']]
    ids = {c['id'] for c in cases}
    by_case = {}
    for e in events:
        if e['case_id'] in ids:
            by_case.setdefault(e['case_id'], []).append(e)
    out = {'dataset': DATASET, 'window': {'from': window.get('from'), 'to': window.get('to'), 'policyVersion': window.get('policyVersion'),
                                          'note': 'A case is in the window by the day it was created (UTC) and the policy version it was decided under; no window means all time.'},
           'counts': counts_of(cases), 'excluded': {'note': 'The fictional decision memory is never read here; fictional and live cases are never one number.'}}
    out.update(group_metrics(cases, by_case))
    out.update(timing(cases, by_case))
    versions = sorted({(c.get('policy') or {}).get('version') for c in cases if (c.get('policy') or {}).get('version') is not None})
    out['perPolicyVersion'] = {str(v): {'counts': counts_of(sub), **group_metrics(sub, by_case)} for v in versions for sub in [[c for c in cases if (c.get('policy') or {}).get('version') == v]]}
    out['timeSaved'] = metric(None, None, None, 'assumption', 'manual baseline not measured; set from PoV interviews')
    return out


# ---------------------------------------------------------------- the loop view (S2b)

LOOP_STAGES = (('request', 'Request'), ('evidence', 'Evidence'), ('evaluation', 'Evaluation'), ('decision', 'Decision'), ('feedback', 'Owner feedback'), ('outcome', 'Outcome'))


def loop_stage(c, has_evaluated=True):
    """Where a live case is in the loop now, from its own state (pure): `request` (created, not yet evaluated: transient), `evidence` (asked Staff for facts and waiting),
    `evaluation` (evaluated and waiting for the Owner to decide, escalated or on hold), `decision` (decided, no Owner feedback or tacit agreement yet), `feedback` (the Owner has
    given feedback, tacit or explicit, or overridden), `outcome` (an outcome has been observed). A closed case has left the loop: None."""
    status = c.get('status')
    if status == 'closed':
        return None
    if status == 'gathering_evidence':
        return 'evidence'
    if status in ('awaiting_owner', 'on_hold'):
        return 'evaluation'
    if status == 'decided':
        if (c.get('outcomeObserved') or {}).get('outcome'):
            return 'outcome'
        if c.get('feedback') or decision_of(c).get('overridden'):
            return 'feedback'
        return 'decision'
    return 'request' if not has_evaluated else 'evaluation'


def loop_counts(cases, events=None):
    """The loop view: how many LIVE cases are at each stage now. `cases` as the server loads them; `events` (optional case_events rows) only decide whether a case with no
    recognised status has been evaluated. Returns {dataset, total, closed, stages: [{stage, label, count, caseIds}]}; counts add up to total - closed. Fictional cases are never counted."""
    live = [c for c in cases if c.get('dataset', DATASET) == DATASET]
    evaluated = {e['case_id'] for e in (events or []) if e.get('kind') == 'evaluated'}
    at = {key: [] for key, _ in LOOP_STAGES}
    closed = 0
    for c in live:
        stage = loop_stage(c, c['id'] in evaluated or events is None)
        if stage is None:
            closed += 1
        else:
            at[stage].append(c['id'])
    return {'dataset': DATASET, 'total': len(live), 'closed': closed,
            'stages': [{'stage': key, 'label': label, 'count': len(at[key]), 'caseIds': at[key]} for key, label in LOOP_STAGES],
            'note': 'Live cases only, by where each stands now. Declined or overridden decisions are never observed, so they stay at Decision or Owner feedback. Closed cases have left the loop.'}


# ---------------------------------------------------------------- page use (D11, S2b)

def _ms(data):
    v = (data or {}).get('ms')
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 86400000 else None


def ui_summary(rows, window=None):
    """Summarise ui_events rows [{at, role, page, kind, data}] in the window {from, to} (by the UTC day the event happened; either may be None). Pure.
    pages: per page the page_enter count, page_leave count, click count and the median seconds on the page (from the `ms` the page reported on page_leave; None until a leave is
    reported, never 0). buttons: named clicks (data.name) with counts. decisions: decide_start and decide_done counts and the median seconds from start to done (data.ms on decide_done).
    Nothing here is about a customer or a case: the pages report only route names, button names and durations."""
    window = window or {}
    rows = [r for r in rows if (not window.get('from') or r['at'][:10] >= window['from']) and (not window.get('to') or r['at'][:10] <= window['to'])]
    pages, buttons, started, done_ms, done = {}, {}, 0, [], 0
    for r in rows:
        p = pages.setdefault(r['page'], {'page': r['page'], 'enters': 0, 'leaves': 0, 'clicks': 0, 'dwell': []})
        if r['kind'] == 'page_enter':
            p['enters'] += 1
        elif r['kind'] == 'page_leave':
            p['leaves'] += 1
            ms = _ms(r.get('data'))
            if ms is not None:
                p['dwell'].append(ms / 1000)
        elif r['kind'] == 'click':
            p['clicks'] += 1
            name = (r.get('data') or {}).get('name')
            if isinstance(name, str) and name:
                buttons[(r['page'], name)] = buttons.get((r['page'], name), 0) + 1
        elif r['kind'] == 'decide_start':
            started += 1
        elif r['kind'] == 'decide_done':
            done += 1
            ms = _ms(r.get('data'))
            if ms is not None:
                done_ms.append(ms / 1000)
    out_pages = sorted(({'page': p['page'], 'enters': p['enters'], 'leaves': p['leaves'], 'clicks': p['clicks'],
                         'medianDwellSeconds': median(p['dwell']), 'dwellSamples': len(p['dwell'])} for p in pages.values()), key=lambda p: (-p['enters'], p['page']))
    return {'window': {'from': window.get('from'), 'to': window.get('to')}, 'events': len(rows), 'pages': out_pages,
            'buttons': [{'page': k[0], 'name': k[1], 'count': n} for k, n in sorted(buttons.items(), key=lambda kv: (-kv[1], kv[0]))],
            'decisions': {'started': started, 'done': done, 'medianSeconds': median(done_ms), 'samples': len(done_ms)},
            'source': 'measured', 'note': 'Reported by the pages in this browser and stored on this machine only. A time reads "no data yet" (None) until a page reports one, never 0.'}
