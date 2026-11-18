"""The Doctor (11 Nov 2026; docs/superpowers/specs/2026-11-11-doctor-design.md): six questions the Owner asks about how their setup is working, answered by
code from the Owner's own cases. Pure functions over case dicts and a policy: no database, no server, no model. A suggestion is a Quick setup answers patch
(delegation.quick_setup_policy), so the Owner tries it in Quick setup and sees the preview before saving; the Doctor never changes a setting.

What-ifs on past cases judge the policy's bounds only (delegation.would_approve), on the facts recorded when each case was decided."""
from datetime import date, timedelta
from itertools import combinations

import delegation
import impact
from records import money_text_plain

QUESTIONS = (('came', 'Why do so many requests still come to me?'), ('corrections', 'Why do I keep correcting the agent?'),
             ('help', 'How much is the agent helping?'), ('outcomes', 'Did the extensions the agent approved get paid?'),
             ('customers', 'Which customers come to me most?'), ('rules', 'Which rules never matter, and which block everything?'))
LABEL = dict(QUESTIONS)
MIN_CASES = 5
DAY_STEPS = (45, 60, 90, 120, 180, 365)
MAX_COMBINED = 3
CAME = ('owner_review', 'policy_hold')
RULE_NAMES = {'decision_exposure': 'Exposure of this decision', 'customer_exposure': "The customer's total exposure after this decision",
              'extension_days': 'Days past the current due date', 'days_from_request': 'Days after the day the request was received',
              'days_past_original_due': 'Days after the original due date', 'nothing_else_overdue': 'Nothing else overdue', 'late_history': 'Earlier late payments'}
OUTCOME_WORDS = (('on_time', 'paid by the new date'), ('late_paid', 'paid late'), ('partial', 'part paid'), ('open_not_due', 'not due yet'),
                 ('open_past_due', 'past the new date and unpaid'), ('written_off', 'written off'), ('unknown', 'not known yet'))
WHAT_IF_NOTE = 'What-ifs judge the limits only, on the facts recorded when each case was decided.'
LOOK_AHEAD = 'If each customer asked today for 14 more days on each open invoice'
NO_CASES = 'There are no requests in this window.'


# ---------------------------------------------------------------- helpers over one case

def first_handling(c):
    """Where the request was first sent: the evaluation's handling, kept on the case after the Owner decides."""
    return (c.get('evaluation') or {}).get('handling') or c.get('handling')


def came(c):
    return first_handling(c) in CAME


def owner_did(c):
    """approve | decline | withdrawn (the Owner's own decision, later overridden) | closed | waiting."""
    if impact.owner_decided(c):
        d = c.get('decision') or {}
        return 'withdrawn' if d.get('overridden') else d.get('outcome') or 'waiting'
    return 'closed' if c.get('status') == 'closed' else 'waiting'


def features(c):
    return (c.get('evaluation') or {}).get('features') or None


def tryable(c):
    return c.get('kind') == 'extension' and bool(features(c))


def reasons_of(c):
    """[(key, label)] of the checks that sent the case on: failing or unknown bounds, a held customer first, else the evaluation's own words."""
    e = c.get('evaluation') or {}
    out = [(k['key'], k['label']) for k in (e.get('risk') or {}).get('checks', []) if k.get('status') in ('fail', 'unknown')]
    if any(k == 'days_past_original_due' for k, _ in out):   # one Quick setup answer sets both day limits: named once, as the preview names it
        out = [x for x in out if x[0] != 'extension_days']
    if first_handling(c) == 'policy_hold' and (features(c) or {}).get('heldCustomer'):
        out.insert(0, ('held_customer', 'The customer is on your never-decide list'))
    if not out:
        why = e.get('why') or 'Another rule'
        out = [('other:' + why, why)]   # each reason in its own words, never lumped under the first one seen
    return out


def lower_first(text):
    return text[:1].lower() + text[1:]


def plural(n, one, many):
    return str(n) + ' ' + (one if n == 1 else many)


def in_window(cases, as_of, days):
    if days is None:
        return list(cases)
    since = (as_of - timedelta(days=days)).isoformat()
    return [c for c in cases if (c.get('createdAt') or '')[:10] >= since]


def _money(units, settings):
    return delegation.money_view(units, settings)['text']


def _plain(units, settings):
    return money_text_plain(delegation.money_of(units, settings))


def _answer(question, window, n, headline, findings=(), suggestions=(), notes=(), enough=True):
    findings, suggestions, notes = list(findings), list(suggestions), list(notes)
    return {'question': question, 'label': LABEL[question], 'window': {'days': window, 'cases': n}, 'enough': enough, 'headline': headline,
            'findings': findings, 'suggestions': suggestions, 'notes': notes, 'facts': [headline] + findings + [s['text'] for s in suggestions] + notes}


def _few(n):
    return 'There are too few cases (' + str(n) + ') to see a pattern yet; the counts here are everything there is.'


class _Policies:
    """Candidate policies made from Quick setup answer patches, validated once each. Quick setup always writes the total-lateness limit it shows (the longest
    extension, on a policy without one); a what-if that does not touch that answer keeps the real policy's absence of it, so "now" and every candidate differ only
    in what the patch says."""
    def __init__(self, policy, settings):
        self.policy, self.settings, self.base, self.cache = policy, settings, delegation.quick_setup_answers(policy), {}

    def make(self, patch):
        key = repr(sorted(patch.items()))
        if key not in self.cache:
            try:
                cand = delegation.validate_policy(delegation.quick_setup_policy({**self.base, **patch}, self.policy), self.settings)
                if 'daysPastOriginalDue' not in patch and self.policy['extensions'].get('maxDaysPastOriginalDue') is None:
                    cand['extensions']['maxDaysPastOriginalDue'] = None
                self.cache[key] = cand
            except Exception:   # a patch the policy cannot take (e.g. an amount out of range) is simply not offered
                self.cache[key] = None
        return self.cache[key]


def _approves(candidate, c):
    return delegation.would_approve(candidate, 'extension', features(c))


# ---------------------------------------------------------------- 1. why so many requests come to the Owner

def _relaxations(policy, settings, base, tried):
    """The Quick setup patches that could let the agent decide more of these cases, each {key, label, answers}; only those that differ from the current answers."""
    out = []
    failing = lambda key: [c for c in tried if key in {k for k, _ in reasons_of(c)}]
    if not base['allowOtherOverdue']:
        out.append({'key': 'other_overdue', 'label': 'customers with another overdue invoice were allowed', 'answers': {'allowOtherOverdue': True}})
    if base['lateHistory'] != 'any':
        out.append({'key': 'late_history', 'label': 'customers who paid late before were allowed', 'answers': {'lateHistory': 'any'}})
    long = failing('extension_days') + failing('days_past_original_due')
    if long:
        need = max((features(c).get('daysPastOriginalDue') or features(c).get('extensionDays') or 0) for c in long)
        steps = [d for d in DAY_STEPS if d > (base['daysPastOriginalDue'] or 0) and d >= need]
        if steps:
            out.append({'key': 'total_days', 'label': 'the total-lateness limit were ' + str(steps[0]) + ' days', 'answers': {'daysPastOriginalDue': steps[0]}})
    if base['daysFromRequest'] is not None and failing('days_from_request'):
        out.append({'key': 'from_request', 'label': 'there were no limit counted from the day of the request', 'answers': {'daysFromRequest': None}})
    for key, feature, answer, word in (('decision_exposure', 'exposure', 'maxInvoice', 'the invoice limit'), ('customer_exposure', 'customerExposure', 'maxCustomer', 'the customer total limit')):
        values = [features(c).get(feature) for c in failing(key) if features(c).get(feature) is not None]
        if values:
            top = int(max(values))
            out.append({'key': key, 'label': word + ' were ' + _money(top, settings), 'answers': {answer: _plain(top, settings)}})
    return out


def _came(cases, policy, settings, window, names, preview, preview_for):
    n = len(cases)
    if not n:
        return _answer('came', window, 0, NO_CASES, notes=[_few(0)], enough=False)
    to_owner = [c for c in cases if came(c)]
    groups = {}
    for c in to_owner:
        for key, label in reasons_of(c):
            g = groups.setdefault(key, {'label': label, 'cases': []})
            g['cases'].append(c)
    order = sorted(groups.values(), key=lambda g: (-len(g['cases']), g['label']))
    headline = str(len(to_owner)) + ' of your ' + str(n) + ' requests came to you.'
    if order:
        headline += ' The most common reason: ' + lower_first(order[0]['label']) + ' (' + str(len(order[0]['cases'])) + ').'
    findings = []
    for g in order:
        did = [owner_did(c) for c in g['cases']]
        findings.append(str(len(did)) + ' — ' + g['label'] + ': you approved ' + str(did.count('approve')) + ', declined ' + str(did.count('decline')) + ', ' +
                        str(did.count('waiting')) + ' still waiting' + (', ' + str(did.count('closed')) + ' closed' if did.count('closed') else '') +
                        (', ' + str(did.count('withdrawn')) + ' withdrawn' if did.count('withdrawn') else '') + '.')
    tried = [c for c in to_owner if tryable(c)]
    notes = []
    if len(to_owner) - len(tried):
        u = len(to_owner) - len(tried)
        notes.append(plural(u, 'request was', 'requests were') + ' not tried (a first credit, or recorded before Nucleon kept the facts it needs).')
    pol = _Policies(policy, settings)
    now = {c['id'] for c in tried if _approves(policy, c)}   # the real policy's limits, as they stand
    k0 = len(now)
    if k0:
        notes.append(str(k0) + " of these pass today's limits; they came to you for another reason (for example the assistant did not recommend approving, "
                     "a track record was needed, or the limits were stricter then).")

    def measure(answers):
        cand = pol.make(answers)
        if cand is None:
            return None
        hit = [c for c in tried if _approves(cand, c)]
        did = [owner_did(c) for c in hit if c['id'] not in now]   # the cost is counted over what the change adds, not over what already passes
        return {'k': len(hit), 'g': len(did), 'a': did.count('approve'), 'd': did.count('decline')}
    options = []
    for r in _relaxations(policy, settings, pol.base, tried):
        m = measure(r['answers'])
        if m:
            options.append({**r, **m})
    good = [o for o in options if o['d'] <= o['a']]
    best_single = max((o['k'] for o in options), default=k0)
    combined = None
    for size in range(2, MAX_COMBINED + 1):
        for parts in combinations(good, size):
            answers = {}
            for p in parts:
                answers.update(p['answers'])
            m = measure(answers)
            if m and m['k'] > best_single and (combined is None or (m['k'], -size, -m['d']) > (combined['k'], -len(combined['parts']), -combined['d'])):
                combined = {'key': '+'.join(p['key'] for p in parts), 'label': ' and '.join(p['label'] for p in parts), 'answers': answers, 'parts': parts, **m}
    chosen = [o for o in options if o['k'] > k0] + ([combined] if combined else [])
    chosen.sort(key=lambda o: (o['d'] > o['a'], -o['k'], o['d']))
    suggestions = []
    for o in chosen:
        text = ('If ' + o['label'] + ': the agent would have decided ' + str(o['k']) + ' of these ' + str(len(tried)) + ' itself (now ' + str(k0) + '). Of the ' + str(o['g']) +
                ' it would add, you had approved ' + str(o['a']) + ' and declined ' + str(o['d']) + '.')
        if preview is not None and preview_for is not None:
            ahead = preview_for(o['answers'])
            if ahead:
                text += (' ' + LOOK_AHEAD + ', it would decide ' + str(ahead['counts']['agent']) + ' of ' + str(ahead['total']) + ' (now ' + str(preview['counts']['agent']) + ')' +
                         ('; only the first ' + str(ahead['total']) + ' open invoices were tried.' if ahead.get('truncated') else '.'))
        bad = o['d'] > o['a']
        if bad:
            text += ' You declined most of these, so this change is not recommended.'
        suggestions.append({'text': text, 'answers': None if bad else o['answers']})   # no "Try this in Quick setup" for a change the Owner mostly declined
    if suggestions:
        notes.append(WHAT_IF_NOTE)
    if suggestions and all(s['answers'] is None for s in suggestions):
        notes.append('No change here is recommended: each would let the agent approve requests you declined.')
    if len(groups) and any(len(reasons_of(c)) > 1 for c in to_owner):
        notes.append('A request can have more than one reason, so the counts above can add up to more than the requests.')
    enough = len(to_owner) >= MIN_CASES
    if not enough:
        notes.append(_few(len(to_owner)))
    return _answer('came', window, n, headline, findings, suggestions, notes, enough)


# ---------------------------------------------------------------- 2. why the Owner keeps correcting the agent

def _tightenings(policy, settings, base, corrected):
    """Limits strictly tighter than today's, each just below a value a corrected approval had: never a looser one."""
    out = []
    days_now = base['daysPastOriginalDue']
    for v in sorted({features(c)['daysPastOriginalDue'] for c in corrected if features(c).get('daysPastOriginalDue') is not None}):
        if 1 <= v - 1 and (days_now is None or v - 1 < days_now):
            out.append(('days', 'the total-lateness limit were ' + str(v - 1) + ' days', {'daysPastOriginalDue': v - 1}))
    for feature, answer, word, dim, limit in (('exposure', 'maxInvoice', 'the invoice limit', 'invoice', policy['limits'].get('maxDecisionExposure')),
                                              ('customerExposure', 'maxCustomer', 'the customer total limit', 'customer', policy['limits'].get('maxCustomerExposure'))):
        now = int(limit['minorUnits']) if limit else None
        for v in sorted({int(features(c)[feature]) for c in corrected if features(c).get(feature) is not None}):
            if v - 1 >= 0 and (now is None or v - 1 < now):
                out.append((dim, word + ' were ' + _money(v - 1, settings), {answer: _plain(v - 1, settings)}))
    stricter = {'any': ('some', 'none'), 'some': ('none',), 'none': ()}[base['lateHistory']]
    for level in stricter:
        out.append(('late', 'customers who paid late before came to you' if level == 'none' else 'only customers with at most a quarter of their payments late were decided by the agent',
                    {'lateHistory': level}))
    if base['allowOtherOverdue']:
        out.append(('overdue', 'customers with another overdue invoice came to you', {'allowOtherOverdue': False}))
    return out


def _corrections(cases, policy, settings, window):
    n = len(cases)
    agent = [c for c in cases if impact.agent_decided(c)]
    if not agent:
        return _answer('corrections', window, n, 'The agent has not decided anything in this window.', notes=[_few(0)], enough=False)
    is_corrected = lambda c: impact.overridden(c) or impact.last_verdict(c) == 'disagree'
    is_agreed = lambda c: not is_corrected(c) and impact.last_verdict(c) in ('agree', 'tacit_agree')
    reviewed = [c for c in agent if is_corrected(c) or is_agreed(c)]
    corrected, agreed = [c for c in agent if is_corrected(c)], [c for c in agent if is_agreed(c)]
    headline = "You reviewed " + str(len(reviewed)) + " of the agent's " + str(len(agent)) + " decisions: you agreed with " + str(len(agreed)) + " and corrected " + str(len(corrected)) + "."
    findings = []
    declines = [c for c in corrected if (c.get('decision') or {}).get('outcome') == 'decline']
    reversed_ = [c for c in declines if impact.overridden(c)]
    if reversed_:
        findings.append(plural(len(reversed_), 'of the corrections was a decline you reversed.', 'of the corrections were declines you reversed.'))
    if len(declines) - len(reversed_):
        findings.append(plural(len(declines) - len(reversed_), 'of the corrections was a decline you disagreed with.', 'of the corrections were declines you disagreed with.'))
    waiting = len(agent) - len(reviewed)
    if waiting:
        findings.append(plural(waiting, 'decision is', 'decisions are') + ' not reviewed yet.')
    ca = [c for c in corrected if (c.get('decision') or {}).get('outcome') == 'approve' and tryable(c)]
    aa = [c for c in agreed if (c.get('decision') or {}).get('outcome') == 'approve' and tryable(c)]
    untried = sum(1 for c in corrected if (c.get('decision') or {}).get('outcome') == 'approve' and not tryable(c))
    pol, best = _Policies(policy, settings), {}
    c0, a0 = sum(1 for c in ca if not _approves(policy, c)), sum(1 for c in aa if not _approves(policy, c))   # what today's limits already send to the Owner
    for dim, label, answers in _tightenings(policy, settings, pol.base, ca):
        cand = pol.make(answers)
        if cand is None:
            continue
        cc, cg = sum(1 for c in ca if not _approves(cand, c)), sum(1 for c in aa if not _approves(cand, c))
        if cc - c0 < 2 or (aa and (cg >= len(aa) or cg * len(ca) >= cc * len(aa))):   # it must catch corrections at a higher rate than agreements, and not every agreement
            continue
        score = ((cc - c0) - (cg - a0), -(cg - a0))
        if dim not in best or score > best[dim]['score']:
            best[dim] = {'label': label, 'answers': answers, 'c': cc, 'a': cg, 'score': score}
    picked = sorted(best.values(), key=lambda b: b['score'], reverse=True)
    suggestions = [{'text': 'If ' + b['label'] + ': ' + str(b['c']) + ' of the ' + str(len(ca)) + ' approvals you corrected would have come to you instead (now ' + str(c0) +
                    '), and so would ' + str(b['a']) + ' of the ' + str(len(aa)) + ' you agreed with (now ' + str(a0) + ').', 'answers': b['answers']} for b in picked]
    notes = [WHAT_IF_NOTE] if suggestions else []
    if untried:
        notes.append(plural(untried, 'corrected decision was', 'corrected decisions were') + ' not tried (a first credit, or recorded before Nucleon kept the facts it needs).')
    if ca and c0 == len(ca):
        notes.append("Today's limits already send all of these corrected approvals to you.")
    elif corrected and not suggestions:
        notes.append('No tighter limit would have caught most of your corrections without also catching decisions you agreed with.')
    enough = len(reviewed) >= MIN_CASES
    if not enough:
        notes.append(_few(len(reviewed)))
    return _answer('corrections', window, n, headline, findings, suggestions, notes, enough)


# ---------------------------------------------------------------- 3 to 6

def _help(cases, window):
    n = len(cases)
    if not n:
        return _answer('help', window, 0, NO_CASES, notes=[_few(0)], enough=False)
    agent = [c for c in cases if impact.agent_decided(c)]
    approved = sum(1 for c in agent if (c.get('decision') or {}).get('outcome') == 'approve')
    to_owner = [c for c in cases if came(c)]
    headline = ('Of your ' + str(n) + ' requests, the agent decided ' + str(len(agent)) + ' by itself (' + str(approved) + ' approved, ' + str(len(agent) - approved) +
                ' declined) and ' + str(len(to_owner)) + ' came to you.')
    holds = [c for c in cases if first_handling(c) == 'policy_hold']
    held = sum(1 for c in holds if (features(c) or {}).get('heldCustomer'))
    contradicted = len(holds) - held
    gathering = sum(1 for c in cases if c.get('status') == 'gathering_evidence')
    corrected = sum(1 for c in agent if impact.overridden(c) or impact.last_verdict(c) == 'disagree')
    agreed = sum(1 for c in agent if not (impact.overridden(c) or impact.last_verdict(c) == 'disagree') and impact.last_verdict(c) in ('agree', 'tacit_agree'))
    findings = [str(held) + (' of those that came to you was from a customer on your never-decide list.' if held == 1 else ' of those that came to you were from customers on your never-decide list.')]
    if contradicted:
        findings.append(str(contradicted) + (' was' if contradicted == 1 else ' were') + ' held because the information contradicted the records.')
    findings += [str(gathering) + (' is' if gathering == 1 else ' are') + ' waiting for information from Staff.',
                "Of the agent's " + plural(len(agent), 'decision', 'decisions') + ' you agreed with ' + str(agreed) + ', corrected ' + str(corrected) + ', and ' +
                str(len(agent) - agreed - corrected) + (' is' if len(agent) - agreed - corrected == 1 else ' are') + ' not reviewed yet.']
    return _answer('help', window, n, headline, findings, notes=[] if n >= MIN_CASES else [_few(n)], enough=n >= MIN_CASES)


def _outcomes(cases, window, events_by_case):
    n = len(cases)
    standing = [c for c in cases if impact.agent_decided(c) and impact.observable(c)]
    if not standing:
        return _answer('outcomes', window, n, 'The agent has not approved any request that still stands in this window.', notes=[_few(0)], enough=False)
    seen = [impact.observation(c, (events_by_case or {}).get(c['id'], [])) or 'unknown' for c in standing]
    parts = [str(seen.count(k)) + ' ' + w for k, w in OUTCOME_WORDS if seen.count(k)]
    headline = 'The agent approved ' + plural(len(standing), 'request that still stands', 'requests that still stand') + ': ' + ', '.join(parts) + '.'
    enough = len(standing) >= MIN_CASES
    return _answer('outcomes', window, n, headline, notes=[] if enough else [_few(len(standing))], enough=enough)


def _customers(cases, window, names):
    n = len(cases)
    to_owner = [c for c in cases if came(c)]
    if not to_owner:
        return _answer('customers', window, n, NO_CASES if not n else 'No request came to you in this window.', notes=[_few(0)], enough=False)
    by = {}
    for c in to_owner:
        by.setdefault(c.get('customerId'), []).append(c)
    total = {}
    for c in cases:
        total[c.get('customerId')] = total.get(c.get('customerId'), 0) + 1
    name = lambda cid: names.get(cid) or cid or 'Unknown customer'
    order = sorted(by, key=lambda cid: (-len(by[cid]), name(cid)))[:5]
    findings = []
    for cid in order:
        counts = {}
        for c in by[cid]:
            for key, label in reasons_of(c):
                counts[label] = counts.get(label, 0) + 1
        label, k = sorted(counts.items(), key=lambda x: (-x[1], x[0]))[0]
        findings.append(name(cid) + ': ' + str(len(by[cid])) + ' of ' + str(total[cid]) + ' requests came to you, mostly: ' + label + ' (' + str(k) + ').')
    headline = plural(len(by), 'customer had requests come to you', 'customers had requests come to you') + '; ' + name(order[0]) + ' the most (' + str(len(by[order[0]])) + ').'
    enough = len(to_owner) >= MIN_CASES
    return _answer('customers', window, n, headline, findings, notes=[] if enough else [_few(len(to_owner))], enough=enough)


def _active_rules(policy):
    ext = policy['extensions']
    on = {'decision_exposure', 'customer_exposure', 'extension_days'}
    if ext.get('requireNothingElseOverdue'):
        on.add('nothing_else_overdue')
    if ext.get('maxPriorLateShare') is not None:
        on.add('late_history')
    if ext.get('maxDaysFromRequest') is not None:
        on.add('days_from_request')
    if ext.get('maxDaysPastOriginalDue') is not None:
        on.add('days_past_original_due')
    return on


def _rules(cases, policy, window, preview):
    n = len(cases)
    sent, labels = {}, dict(RULE_NAMES)
    for c in cases:
        if came(c):
            for key, label in reasons_of(c):
                sent[key] = sent.get(key, 0) + 1
                labels.setdefault(key, label)
    blocks, t = {}, (preview or {}).get('total') or 0
    for r in (preview or {}).get('reasons') or []:
        blocks[r['key']] = r['count']
        labels.setdefault(r['key'], r['label'])
    keys = sorted(set(sent) | set(blocks), key=lambda k: (-(blocks.get(k, 0) + sent.get(k, 0)), labels.get(k, k)))
    findings = [labels.get(k, k) + ': sent ' + plural(sent.get(k, 0), 'request', 'requests') + ' to you' +
                ("; blocks " + str(blocks.get(k, 0)) + " of today's " + str(t) + " open invoices" if preview else '') + '.' +
                (' It blocks almost everything.' if t >= MIN_CASES and blocks.get(k, 0) >= 0.9 * t else '') for k in keys]
    never = [RULE_NAMES[k] for k in sorted(_active_rules(policy)) if k not in sent and k not in blocks]
    if never and n >= MIN_CASES:
        findings.append('These never sent you a request in this window: ' + ', '.join(never) + '.')
    hard = [k for k in keys if t >= MIN_CASES and blocks.get(k, 0) >= 0.9 * t]
    if hard:
        k = max(hard, key=lambda k: blocks[k])
        headline = labels.get(k, k) + ' blocks almost every open invoice (' + str(blocks[k]) + ' of ' + str(t) + ').'
    elif sent:
        k = max(sent, key=lambda k: (sent[k], labels.get(k, k)))
        headline = labels.get(k, k) + ' sent you the most requests (' + str(sent[k]) + ').'
    else:
        headline = 'No rule has sent you a request in this window.'
    enough = n >= MIN_CASES
    notes = []
    if preview:
        notes.append('Blocks count each open invoice as if its customer asked today for 14 more days' +
                     ('; only the first ' + str(t) + ' open invoices were tried.' if preview.get('truncated') else '.'))
    if not enough:
        notes.append(_few(n))
    return _answer('rules', window, n, headline, findings, notes=notes, enough=enough)


# ---------------------------------------------------------------- entry points

def answer(question, cases, policy, settings, as_of, days, names, events_by_case=None, preview=None, preview_for=None):
    """One question's answer over the live cases created in the last `days` days (None: all). See the module and the spec for the shape."""
    if question not in LABEL:
        raise ValueError('Unknown question: ' + str(question))
    w = in_window(cases, as_of, days)
    if question == 'came':
        return _came(w, policy, settings, days, names, preview, preview_for)
    if question == 'corrections':
        return _corrections(w, policy, settings, days)
    if question == 'help':
        return _help(w, days)
    if question == 'outcomes':
        return _outcomes(w, days, events_by_case)
    if question == 'customers':
        return _customers(w, days, names)
    return _rules(w, policy, days, preview)


def headlines(cases, policy, settings, as_of, days, names, events_by_case=None, preview=None):
    """[{question, label, headline}] for the six questions (no look-ahead per suggestion: that is worked out only for the question asked)."""
    return [{'question': q, 'label': label, 'headline': answer(q, cases, policy, settings, as_of, days, names, events_by_case, preview, None)['headline']}
            for q, label in QUESTIONS]
