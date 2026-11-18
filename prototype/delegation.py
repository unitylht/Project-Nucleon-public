"""Adaptive Decision Authority (docs/ADAPTIVE-DECISION-AUTHORITY.md): the Owner's delegation policy and the pure code that decides what may take
effect under it. No database, no clock, no model: every function takes plain values and returns plain values, so each rule is unit-testable.

The model RECOMMENDS and explains; this code decides (evaluate). Three separate dimensions are returned side by side and never merged into
a score: evidence sufficiency (what is verified), business risk (inside the delegated bounds?) and demonstrated reliability (the policy
back-tested on held-out reviewed cases). Money is integer minor units; shares and multiples are exact (Fraction), never float, except the
log-distance that only RANKS comparable cases. Unknown is never zero: a value the records cannot establish never passes a limit.

An autonomous decline exists only as the Owner's opt-in (policy.autoDecline, 8 Nov 2026, off by default, extensions only): the agent declines on its own only when
the Owner turned it on, the assistant recommended declining, and a value the records establish is over a decline line the Owner set; anything else that is not
approved goes to the Owner, or onto a hold the Owner resolves. There is no external communication (the policy has no setting for it, and every result says nothing was sent).

All figures in the demonstration data and the simulated track record are fictional POC values, not real thresholds or measured accuracy."""
import hashlib
import json
import math
import re
from datetime import date, timedelta
from fractions import Fraction

from agent import display_date, money_text
from records import RecordsError, parse_money, ref_key, require

KINDS = ('extension', 'trial_credit')
PREFERENCE = 'owner_preference'   # the Owner's answers to what-ifs about real customers (4 Nov 2026): retrieval and training, never the track record
DATASETS = ('live', 'fictional_example', 'fictional_evaluation', PREFERENCE)
RETRIEVAL = ('fictional_example', 'live', PREFERENCE)   # comparable cases come from these only: the evaluation set is held out
HANDLINGS = ('autonomous_approve', 'autonomous_decline', 'request_evidence', 'owner_review', 'policy_hold')
RECOMMENDATIONS = ('approve_if_verified', 'approve', 'decline', 'escalate')
APPROVING = ('approve', 'approve_if_verified')   # both recommend approval; approve_if_verified never bypasses evidence (step 3 asks for it first)
RECOMMENDATION_WORDS = {'approve_if_verified': 'The assistant recommended approval once the information is confirmed', 'approve': 'The assistant recommended approval',
                        'decline': 'The assistant recommended declining', 'escalate': 'The assistant recommended sending it to the Owner'}


def recommendation_text(rec):
    return RECOMMENDATION_WORDS.get(rec, 'The assistant gave no recommendation')


def agrees(outcome, rec):
    """Whether the Owner's outcome is what the assistant recommended: approve_if_verified counts as approve."""
    return outcome == rec or outcome == 'approve' and rec in APPROVING
SOURCE = 'owner_delegation_policy'
COMMUNICATION = {'sent': False, 'note': 'Nucleon sent nothing to the customer. Staff informs the customer.'}
DEPOSIT_DAYS = 30   # a recorded or confirmed deposit counts when received at most this long before the as-of date
IDENTITY_DAYS = 365   # a confirmed business identity stays on file this long
# How a deposit is known to have arrived (its verification LEVEL). Only a recorded payment is a ledger payment; the Staff-checked levels are Staff's word about
# what they saw, so the Owner bounds them (newCustomers.staffCheckedDepositUpTo); a customer's statement is kept and shown but never counts.
DEPOSIT_BASES = {'bank': 'staff_checked_bank', 'document': 'staff_checked_document', 'customer_statement': 'staff_assertion'}   # Staff's stated basis -> level
IDENTITY_BASES = ('registry', 'document')
LEVEL_WORDS = {'recorded_payment': 'a recorded payment in Nucleon Records', 'staff_checked_bank': 'checked by Staff in the bank account (not a recorded payment)',
               'staff_checked_document': 'checked by Staff on a receipt or remittance document (not a recorded payment)',
               'staff_assertion': 'reported by the customer, not verified'}
IDENTITY_WORDS = {'registry': 'seen by Staff in a registry lookup', 'document': 'seen by Staff on a document'}


# ---- business background (11 Nov 2026, Tony for an Owner who looks at "a valid ABN and how long they have traded"): shown with the identity, for the Owner to read.
# NO rule reads it: a number that fails the check, or a young business, changes neither the evidence status nor the handling. Nucleon looks nothing up: the check
# below is the ABN's own arithmetic (it catches a typing mistake); whether the ABN is active is what Staff saw in the register.
ABN_WEIGHTS = (10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19)
BACKGROUND_NOTE = 'Shown for your information: no rule uses the ABN check or how long the business has been registered.'


def abn_check(registration):
    """{'abn': '51 824 753 556', 'valid': bool} when the registration is an 11-digit number (spaces, hyphens and a leading "ABN" allowed), else None: another
    registry's number, an ACN, or free text is not an ABN and is not judged. valid is the ABN checksum (first digit less one, weighted sum divisible by 89)."""
    digits = re.sub(r'[\s\-]', '', re.sub(r'^\s*ABN[\s:.]*', '', str(registration or ''), flags=re.I))
    if not re.fullmatch(r'\d{11}', digits):
        return None
    nums = [int(d) for d in digits]
    nums[0] -= 1
    return {'abn': ' '.join((digits[:2], digits[2:5], digits[5:8], digits[8:])), 'valid': sum(w * n for w, n in zip(ABN_WEIGHTS, nums)) % 89 == 0}


def operating_words(since, as_of):
    """'6 years 4 months' from an ISO day to the as-of date (whole months; under a month: 'less than a month'). None when there is no date or it is in the future."""
    try:
        start = date.fromisoformat(str(since)[:10])
    except ValueError:
        return None
    if start > as_of:
        return None
    months = (as_of.year - start.year) * 12 + as_of.month - start.month - (1 if as_of.day < start.day else 0)
    years, rest = divmod(months, 12)
    parts = ([str(years) + (' year' if years == 1 else ' years')] if years else []) + ([str(rest) + (' month' if rest == 1 else ' months')] if rest else [])
    return ' '.join(parts) or 'less than a month'


def business_background(data, as_of):
    """What the Owner reads beside a confirmed business identity: {'abn', 'abnValid', 'registeredSince', 'registeredSinceText', 'operatingFor', 'lookupUrl', 'sentence'}.
    Every key may be None; sentence is '' when there is nothing to say. Information only (BACKGROUND_NOTE)."""
    check, since = abn_check(data.get('registration')), data.get('registeredSince')
    age = operating_words(since, as_of) if since else None
    bits = []
    if check:
        bits.append('ABN ' + check['abn'] + (': the number passes the ABN check, so it is not a typing mistake. Nucleon itself has not looked it up in the register.' if check['valid']
                    else ': this number FAILS the ABN check, so it is probably mistyped. Look it up before relying on it.'))
    if since and age:
        bits.append('Registered since ' + display_date(str(since)[:10]) + ' as Staff read it in the register: ' + age + '.')
    return {'abn': check['abn'] if check else None, 'abnValid': check['valid'] if check else None, 'registeredSince': since if age else None,
            'registeredSinceText': display_date(str(since)[:10]) if age else None, 'operatingFor': age,
            'lookupUrl': 'https://abr.business.gov.au/ABN/View?abn=' + check['abn'].replace(' ', '') if check else None,
            'sentence': (' '.join(bits) + ' ' + BACKGROUND_NOTE) if bits else ''}
EXTERNAL_EFFECTS = ('This reverses Nucleon\'s internal decision only. Nucleon sent nothing to the customer; if Staff already told the customer or acted on it outside '
                    'Nucleon, that is not undone — Staff must follow up.')
TRIAL_EFFECTS = ' Amounts already invoiced under this credit remain owed.'


def external_effects(kind):
    """What an Owner override does and does not undo, in words (it is shown with every overridden case; nothing outbound exists)."""
    return EXTERNAL_EFFECTS + (TRIAL_EFFECTS if kind == 'trial_credit' else '')
SIMULATION = ('SIMULATION on fictional evaluation cases: it shows how this policy would have compared with a fictional Owner\'s decisions, '
              'not how it performs on real credit decisions.')
EVIDENCE_KINDS = ('deposit', 'business_identity', 'trade_reference', 'no_prior_account')
GOOD_OUTCOMES = ('repaid',)

# ---------------------------------------------------------------- the policy

TRACK_SOURCES = ('fictional', 'live', 'both')   # which reviewed cases the track-record gate (ladder step 7) counts (D7)

POLICY_KEYS = ('mode', 'paused', 'limits', 'extensions', 'newCustomers', 'evidence', 'restrictions', 'trackRecord', 'feedback', 'customers', 'exceptions', 'smallOverage', 'autoDecline')
# The exception band (3 Nov 2026): the Owner may let the agent approve requests that breach a money or days bound by a bounded margin, when the team's model predicts
# the Owner would approve and the Owner approved enough of the closest comparable cases. Only these checks can be inside the band; every other failing check escalates.
BAND_CHECKS = ('decision_exposure', 'customer_exposure', 'trial_exposure', 'new_customer_exposure', 'extension_days')
EXCEPTIONS_DEFAULT = {'enabled': False, 'maxOverExposureShare': '0.5', 'maxExtraDays': 15, 'minModelApprove': '0.8', 'minSimilarApproved': 3, 'suggestDeclineAbove': '0.8'}
# The small-overage allowance (5 Nov 2026, the user's call after a tester saw a tiny request escalate): when the ONLY failing checks are money limits exceeded by a
# small margin, the agent may approve anyway, with no model score and no comparables required. "Small" is a share of the limit, an amount, or (rule) either or
# both of them. It never covers days, identity, overdue invoices, earlier dealings, a held customer or incomplete records: those still escalate.
MONEY_CHECKS = ('decision_exposure', 'customer_exposure', 'trial_exposure', 'new_customer_exposure')
SMALL_OVERAGE_DEFAULT = {'enabled': False, 'maxShare': '0.1', 'maxAmount': None, 'rule': 'either'}
# Autonomous decline (8 Nov 2026, the user's call after Hoang's NTK test: "it can approve by itself but never decline"). A first version to look at: off by default,
# payment extensions only. Each line is optional (None: not used); a request is over a line when a value the records establish is above it (an unknown never declines).
# The agent declines only when the switch is on, the assistant recommended declining and at least one line is crossed; a request over a line is never approved by the
# agent either (it goes to the Owner). A held customer, contradicting evidence, advisory mode, a pause or extensions turned off still send it to the Owner.
EXTRA_DAY_LIMITS = ('maxDaysFromRequest', 'maxDaysPastOriginalDue')   # optional extension limits (Quick setup, 11 Nov 2026)
AUTO_DECLINE_DEFAULT = {'enabled': False, 'maxExtensionDays': None, 'maxDecisionExposure': None, 'maxCustomerExposure': None, 'maxPriorLateShare': None}
DECLINE_LINES = ('maxExtensionDays', 'maxDecisionExposure', 'maxCustomerExposure', 'maxPriorLateShare')


def default_policy(settings=None):
    """Version 0, the effective policy while the Owner has saved none: advisory, everything off, every limit nothing. A key a PUT leaves out takes
    its value from here, so leaving one out never widens anything (a late-share limit of 0, a deposit share of 1, a track record required)."""
    zero = {'minorUnits': '0', 'currency': (settings or {}).get('currency') or '', 'scale': (settings or {}).get('scale') or 0}
    return {'mode': 'advisory', 'paused': False,
            'limits': {'maxDecisionExposure': dict(zero), 'maxCustomerExposure': dict(zero), 'maxAutonomousExposure30d': None},
            'extensions': {'enabled': False, 'maxDays': 0, 'requireNothingElseOverdue': True, 'maxPriorLateShare': '0', 'maxDaysFromRequest': None, 'maxDaysPastOriginalDue': None},
            'newCustomers': {'trialCredit': 'off', 'maxExposure': dict(zero), 'minDepositShare': '1', 'maxTermsDays': 0, 'tradeReferenceAbove': None,
                             'staffCheckedDepositUpTo': None, 'requireIdentity': True},
            'evidence': {'confirmedCoverageAbove': None},
            'restrictions': {'holdCustomers': [], 'unusualSizeMultiple': None},
            'trackRecord': {'minReviewedCases': 5, 'minAgreement': '0.8', 'sources': 'both'},
            'feedback': {'tacitAgreeAfterDays': None}}


_default_policy_inner = default_policy


def default_policy(settings=None):
    return {**_default_policy_inner(settings), 'customers': {}, 'exceptions': dict(EXCEPTIONS_DEFAULT), 'smallOverage': dict(SMALL_OVERAGE_DEFAULT),
            'autoDecline': dict(AUTO_DECLINE_DEFAULT)}


def policy_digest(policy):
    """A fingerprint of the policy's rules (not of who saved it or when): a decision records the digest of the policy it was made under. `feedback` (tacit
    agreement, D8) is not a rule the evaluation reads: it joins the fingerprint only when it is set, so a policy without it (or with it off) keeps the digest it always had.
    `trackRecord.sources` (D7) joins it only when it is not the default 'both', for the same reason."""
    rules = {k: policy[k] for k in POLICY_KEYS if k != 'feedback' and k in policy}   # a version saved before a key existed keeps its digest
    if (rules.get('trackRecord') or {}).get('sources', 'both') == 'both':
        rules['trackRecord'] = {k: v for k, v in rules['trackRecord'].items() if k != 'sources'}
    if (policy.get('feedback') or {}).get('tacitAgreeAfterDays') is not None:
        rules['feedback'] = {'tacitAgreeAfterDays': policy['feedback']['tacitAgreeAfterDays']}
    if not (policy.get('smallOverage') or {}).get('enabled'):   # the small-overage allowance (5 Nov) joins only when on, for the same reason
        rules.pop('smallOverage', None)
    if not (policy.get('autoDecline') or {}).get('enabled'):   # autonomous decline (8 Nov) likewise joins only when on
        rules.pop('autoDecline', None)
    if 'extensions' in rules:   # the two day limits of Quick setup (11 Nov) join only when set
        rules['extensions'] = {k: v for k, v in rules['extensions'].items() if k not in EXTRA_DAY_LIMITS or v is not None}
    return hashlib.sha256(json.dumps(rules, sort_keys=True).encode()).hexdigest()[:16]


def _decimal(value, field, label, low, high):
    """A number as exact decimal text between low and high (inclusive): an int, a float as written, or a string. Never kept as a float."""
    text = str(value).strip() if isinstance(value, (int, float, str)) and not isinstance(value, bool) else ''
    require(re.fullmatch(r'\d{1,4}(?:\.\d{1,6})?', text), 400, 'INVALID_INPUT', label + ': enter a number such as 0.25.', field)
    require(low <= Fraction(text) <= high, 400, 'INVALID_INPUT', label + ': between ' + str(low) + ' and ' + str(high) + '.', field)
    return text


def _share(value, field, label, nullable=False):
    if value is None and nullable:
        return None
    return _decimal(value, field, label, 0, 1)


def _money(value, settings, field, label, nullable=False):
    """An amount in the workspace currency: text such as '1000.00', or the {minorUnits, currency, scale} the policy is read back as."""
    if value is None:
        require(nullable, 400, 'INVALID_AMOUNT', label + ': enter an amount.', field)
        return None
    if isinstance(value, dict):
        require(set(value) == {'minorUnits', 'currency', 'scale'} and value['currency'] == settings['currency'] and value['scale'] == settings['scale']
                and isinstance(value['minorUnits'], str) and re.fullmatch(r'\d{1,15}', value['minorUnits']), 400, 'INVALID_AMOUNT',
                label + ': enter an amount in the workspace currency (' + settings['currency'] + ').', field)
        return {'minorUnits': str(int(value['minorUnits'])), 'currency': value['currency'], 'scale': value['scale']}
    require(isinstance(value, str), 400, 'INVALID_AMOUNT', label + ': enter an amount in the workspace currency (' + settings['currency'] + ').', field)
    return parse_money(value, settings, field)


def _int(value, field, label, low, high, nullable=False):
    if value is None and nullable:
        return None
    require(type(value) is int and low <= value <= high, 400, 'INVALID_INPUT', label + ': a whole number from ' + str(low) + ' to ' + str(high) + '.', field)
    return value


def _flag(value, field, label):
    require(type(value) is bool, 400, 'INVALID_INPUT', label + ': choose yes or no.', field)
    return value


def _section(body, name, defaults):
    got = body.get(name, {})
    require(isinstance(got, dict), 400, 'INVALID_INPUT', name + ' must be an object.', name)
    unknown = sorted(set(got) - set(defaults))
    if unknown:
        raise RecordsError(400, 'INVALID_INPUT', 'Unknown policy setting: ' + name + '.' + unknown[0] + '.', name + '.' + unknown[0])
    return {**defaults, **got}


def validate_policy(body, settings):
    """The whole policy from a PUT body (a key left out takes its default_policy value). Strict: an unknown key, here or inside a section, is
    400 INVALID_INPUT (so there is no allowExternalMessages). autoDecline is the Owner's opt-in autonomous decline (off by default). Money is in the workspace currency, shares are exact decimals
    from 0 to 1, days and counts are whole numbers. Raises RecordsError (the server answers it as it does the other records validation)."""
    require(isinstance(body, dict), 400, 'INVALID_BODY', 'Expected a JSON object.')
    unknown = sorted(set(body) - set(POLICY_KEYS))
    if unknown:
        raise RecordsError(400, 'INVALID_INPUT', 'Unknown policy setting: ' + unknown[0] + '.', unknown[0])
    d = default_policy(settings)
    mode = body.get('mode', d['mode'])
    require(mode in ('advisory', 'delegated'), 400, 'INVALID_INPUT', "mode is 'advisory' or 'delegated'.", 'mode')
    lim, ext, new = _section(body, 'limits', d['limits']), _section(body, 'extensions', d['extensions']), _section(body, 'newCustomers', d['newCustomers'])
    evi, res, rec = _section(body, 'evidence', d['evidence']), _section(body, 'restrictions', d['restrictions']), _section(body, 'trackRecord', d['trackRecord'])
    fed = _section(body, 'feedback', d['feedback'])
    require(new['trialCredit'] in ('off', 'limited'), 400, 'INVALID_INPUT', "trialCredit is 'off' or 'limited'.", 'newCustomers.trialCredit')
    require(isinstance(rec['sources'], str) and rec['sources'] in TRACK_SOURCES, 400, 'INVALID_INPUT', "trackRecord.sources is 'fictional', 'live' or 'both'.", 'trackRecord.sources')
    hold = res['holdCustomers']
    customers = body.get('customers', d['customers'])
    require(isinstance(customers, dict) and len(customers) <= 500, 400, 'INVALID_INPUT', 'customers is an object of customer id -> rule.', 'customers')
    exc = _section(body, 'exceptions', d['exceptions'])
    exceptions = {'enabled': _flag(exc['enabled'], 'exceptions.enabled', 'Exception band'),
                  'maxOverExposureShare': _decimal(exc['maxOverExposureShare'], 'exceptions.maxOverExposureShare', 'How far over a money limit the band reaches (a fraction of the limit)', 0, 10),
                  'maxExtraDays': _int(exc['maxExtraDays'], 'exceptions.maxExtraDays', 'How many days over the longest extension the band reaches', 0, 365),
                  'minModelApprove': _share(exc['minModelApprove'], 'exceptions.minModelApprove', 'Chance of your approval the model must give (a fraction)'),
                  'minSimilarApproved': _int(exc['minSimilarApproved'], 'exceptions.minSimilarApproved', 'Closest comparable cases you must have approved', 0, 5),
                  'suggestDeclineAbove': _share(exc['suggestDeclineAbove'], 'exceptions.suggestDeclineAbove', 'Chance of a decline above which a decline is prepared for you', True)}
    so = _section(body, 'smallOverage', d['smallOverage'])
    small = {'enabled': _flag(so['enabled'], 'smallOverage.enabled', 'Small-overage allowance'),
             'maxShare': _share(so['maxShare'], 'smallOverage.maxShare', 'How far over a money limit still counts as small (a fraction of the limit)', True),
             'maxAmount': _money(so['maxAmount'], settings, 'smallOverage.maxAmount', 'Most over a money limit that still counts as small', True),
             'rule': so['rule']}
    require(small['rule'] in ('either', 'both'), 400, 'INVALID_INPUT', "smallOverage.rule is 'either' or 'both'.", 'smallOverage.rule')
    if small['enabled']:
        have = [k for k in ('maxShare', 'maxAmount') if small[k] is not None]
        require(len(have) == 2 if small['rule'] == 'both' else len(have) >= 1, 400, 'INVALID_INPUT',
                'With the allowance on, set the share, the amount, or both (and both when both must hold).', 'smallOverage.' + ('maxAmount' if 'maxShare' in have else 'maxShare'))
    ad = _section(body, 'autoDecline', d['autoDecline'])
    decline = {'enabled': _flag(ad['enabled'], 'autoDecline.enabled', 'Autonomous decline'),
               'maxExtensionDays': _int(ad['maxExtensionDays'], 'autoDecline.maxExtensionDays', 'Decline an extension longer than (days)', 1, 365, True),
               'maxDecisionExposure': _money(ad['maxDecisionExposure'], settings, 'autoDecline.maxDecisionExposure', 'Decline when the invoice amount is over', True),
               'maxCustomerExposure': _money(ad['maxCustomerExposure'], settings, 'autoDecline.maxCustomerExposure', "Decline when the customer's total exposure is over", True),
               'maxPriorLateShare': _share(ad['maxPriorLateShare'], 'autoDecline.maxPriorLateShare', 'Decline when more earlier payments than this were late (a fraction)', True)}
    if decline['enabled']:
        require(any(decline[k] is not None for k in DECLINE_LINES), 400, 'INVALID_INPUT',
                'With autonomous decline on, set at least one decline line (days, invoice amount, customer exposure or late share).', 'autoDecline.maxExtensionDays')
    rules = {}
    for cid, rule in customers.items():
        require(isinstance(cid, str) and 1 <= len(cid) <= 80 and isinstance(rule, dict) and set(rule) <= {'maxExposure', 'maxExtensionDays', 'note', 'until'}, 400, 'INVALID_INPUT',
                'A customer rule has maxExposure, maxExtensionDays, note and until.', 'customers.' + str(cid))
        until = rule.get('until')
        if until is not None:
            try:
                date.fromisoformat(until)
            except (TypeError, ValueError):
                raise RecordsError(400, 'INVALID_INPUT', 'until is a date (YYYY-MM-DD) or null.', 'customers.' + cid + '.until')
        note = rule.get('note')
        require(note is None or isinstance(note, str) and len(note) <= 200, 400, 'INVALID_INPUT', 'The note is text of at most 200 characters.', 'customers.' + cid + '.note')
        r = {'maxExposure': _money(rule.get('maxExposure'), settings, 'customers.' + cid + '.maxExposure', 'Most this customer may owe', True),
             'maxExtensionDays': _int(rule.get('maxExtensionDays'), 'customers.' + cid + '.maxExtensionDays', 'Longest extension for this customer', 0, 365, True),
             'note': (note or '').strip() or None, 'until': until}
        require(r['maxExposure'] is not None or r['maxExtensionDays'] is not None, 400, 'INVALID_INPUT', 'A customer rule sets a most-owed amount, a longest extension, or both.', 'customers.' + cid)
        rules[cid] = r
    require(isinstance(hold, list) and len(hold) <= 500 and all(isinstance(x, str) and 1 <= len(x) <= 80 for x in hold) and len(set(hold)) == len(hold), 400,
            'INVALID_INPUT', 'holdCustomers is a list of customer ids.', 'restrictions.holdCustomers')
    multiple = res['unusualSizeMultiple']
    return {'mode': mode, 'paused': _flag(body.get('paused', d['paused']), 'paused', 'paused'),
            'limits': {'maxDecisionExposure': _money(lim['maxDecisionExposure'], settings, 'limits.maxDecisionExposure', 'Most one decision may add'),
                       'maxCustomerExposure': _money(lim['maxCustomerExposure'], settings, 'limits.maxCustomerExposure', "Most a customer's exposure may reach"),
                       'maxAutonomousExposure30d': _money(lim['maxAutonomousExposure30d'], settings, 'limits.maxAutonomousExposure30d', 'Most autonomous approvals in 30 days', True)},
            'extensions': {'enabled': _flag(ext['enabled'], 'extensions.enabled', 'Extensions'),
                           'maxDays': _int(ext['maxDays'], 'extensions.maxDays', 'Most days an extension may add', 0, 365),
                           'requireNothingElseOverdue': _flag(ext['requireNothingElseOverdue'], 'extensions.requireNothingElseOverdue', 'Nothing else overdue'),
                           'maxPriorLateShare': _share(ext['maxPriorLateShare'], 'extensions.maxPriorLateShare', 'Most late earlier payments (a fraction)', True),
                           'maxDaysFromRequest': _int(ext['maxDaysFromRequest'], 'extensions.maxDaysFromRequest', 'Latest new date, in days after the request', 1, 365, True),
                           'maxDaysPastOriginalDue': _int(ext['maxDaysPastOriginalDue'], 'extensions.maxDaysPastOriginalDue', 'Most days after the original due date', 1, 365, True)},
            'newCustomers': {'trialCredit': new['trialCredit'],
                             'maxExposure': _money(new['maxExposure'], settings, 'newCustomers.maxExposure', 'Most trial credit exposure'),
                             'minDepositShare': _share(new['minDepositShare'], 'newCustomers.minDepositShare', 'Smallest deposit share'),
                             'maxTermsDays': _int(new['maxTermsDays'], 'newCustomers.maxTermsDays', 'Longest trial terms', 0, 365),
                             'tradeReferenceAbove': _money(new['tradeReferenceAbove'], settings, 'newCustomers.tradeReferenceAbove', 'Trade reference needed above', True),
                             'requireIdentity': _flag(new['requireIdentity'], 'newCustomers.requireIdentity', 'Business identity needed'),   # 4 Nov 2026: off in the wide-open preset
                             'staffCheckedDepositUpTo': _money(new['staffCheckedDepositUpTo'], settings, 'newCustomers.staffCheckedDepositUpTo',
                                                               'A deposit Staff checked counts up to this exposure', True)},
            'evidence': {'confirmedCoverageAbove': _money(evi['confirmedCoverageAbove'], settings, 'evidence.confirmedCoverageAbove', 'Confirmed coverage needed above', True)},
            'restrictions': {'holdCustomers': list(hold),
                             'unusualSizeMultiple': None if multiple is None else _decimal(multiple, 'restrictions.unusualSizeMultiple', 'Unusual size multiple', 0, 1000)},
            'trackRecord': {'minReviewedCases': _int(rec['minReviewedCases'], 'trackRecord.minReviewedCases', 'Reviewed cases needed', 1, 100000, True),
                            'minAgreement': _share(rec['minAgreement'], 'trackRecord.minAgreement', 'Agreement needed (a fraction)', True),
                            'sources': rec['sources']},
            'feedback': {'tacitAgreeAfterDays': _int(fed['tacitAgreeAfterDays'], 'feedback.tacitAgreeAfterDays', 'Treat an unreviewed decision as agreed after (days)', 1, 365, True)},
            'customers': rules, 'exceptions': exceptions, 'smallOverage': small, 'autoDecline': decline}


def small_overage(policy, checks, f, template):
    """Whether every failing check is a money limit exceeded by no more than the small margin the Owner allowed (policy.smallOverage): {applied, considered,
    reason, checks, text}. Pure. Never applies in advisory mode, while paused, or when any failing check is not a money limit."""
    so = policy.get('smallOverage') or {}
    out = {'applied': False, 'considered': bool(so.get('enabled')), 'reason': None, 'checks': []}
    failing = [c for c in checks if c['status'] == 'fail']
    if not so.get('enabled') or not failing:
        return out
    if policy['mode'] != 'delegated' or policy['paused']:
        out['reason'] = 'the agent is not delegated, or delegation is paused'
        return out
    outside = [c for c in failing if c['key'] not in MONEY_CHECKS]
    if outside:
        out['reason'] = 'it covers only money limits, not: ' + ', '.join(c['label'].lower() for c in outside)
        return out
    lim, new = policy['limits'], policy['newCustomers']
    limits = {'decision_exposure': (f.get('exposure'), _m(lim['maxDecisionExposure'])), 'customer_exposure': (f.get('customerExposure'), _m(lim['maxCustomerExposure'])),
              'trial_exposure': (f.get('exposure'), _m(new['maxExposure'])), 'new_customer_exposure': (f.get('exposure'), _m(new['maxExposure']))}
    share, amount, rule = so.get('maxShare'), so.get('maxAmount'), so.get('rule') or 'either'
    for c in failing:
        actual, limit = limits[c['key']]
        if actual is None:
            out['reason'] = c['label'].lower() + ' cannot be established'
            return out
        over = Fraction(actual) - Fraction(limit)
        by_share = share is not None and over <= Fraction(limit) * Fraction(str(share))
        by_amount = amount is not None and over <= Fraction(_m(amount))
        ok = (by_share and by_amount) if rule == 'both' else (by_share or by_amount)
        if not ok:
            out['reason'] = c['label'][0].lower() + c['label'][1:] + ' is over by ' + money_text(money_of(int(over), template)) + ', more than the small margin you allowed'
            return out
    words = []
    if share is not None:
        words.append(share_text(Fraction(str(share)) * 100) + '% of the limit')
    if amount is not None:
        words.append(money_text(amount))
    out.update(applied=True, checks=[c['key'] for c in failing],
               text='Approved: ' + ', '.join(c['label'][0].lower() + c['label'][1:] for c in failing) + ' over the limit by a small margin, inside the allowance you set (up to '
                    + (' and '.join(words) if rule == 'both' else ' or '.join(words)) + ').')
    return out


def exception_band(policy, kind, checks, f, template, model, comps):
    """Whether the failing checks of this request fall inside the exception band the Owner delegated (policy.exceptions), and the model and the comparable cases
    back an approval: {applied, considered, reason, checks, modelApprove, similarApproved, text}. Pure. Never applies in advisory mode, while paused, with a check the
    band does not cover, without a model score, or when the Owner approved too few of the closest comparable cases."""
    ex = policy.get('exceptions') or {}
    out = {'applied': False, 'considered': bool(ex.get('enabled')), 'reason': None, 'checks': []}
    failing = [c for c in checks if c['status'] == 'fail']
    if not ex.get('enabled') or not failing:
        return out
    if policy['mode'] != 'delegated' or policy['paused']:
        out['reason'] = 'the agent is not delegated, or delegation is paused'
        return out
    outside = [c for c in failing if c['key'] not in BAND_CHECKS]
    if outside:
        out['reason'] = 'the exception band does not cover: ' + ', '.join(c['label'].lower() for c in outside)
        return out
    lim, ext, new = policy['limits'], policy['extensions'], policy['newCustomers']
    reach = Fraction(1) + Fraction(str(ex['maxOverExposureShare']))
    limits = {'decision_exposure': (f.get('exposure'), _m(lim['maxDecisionExposure'])), 'customer_exposure': (f.get('customerExposure'), _m(lim['maxCustomerExposure'])),
              'trial_exposure': (f.get('exposure'), _m(new['maxExposure'])), 'new_customer_exposure': (f.get('exposure'), _m(new['maxExposure']))}
    for c in failing:
        if c['key'] == 'extension_days':
            days = f.get('extensionDays')
            if days is None or days > ext['maxDays'] + int(ex['maxExtraDays']):
                out['reason'] = 'the extension is beyond the band (' + str(days) + ' days; the band reaches ' + str(ext['maxDays'] + int(ex['maxExtraDays'])) + ')'
                return out
        else:
            actual, limit = limits[c['key']]
            if actual is None or Fraction(actual) > Fraction(limit) * reach:
                out['reason'] = c['label'] + ' is beyond the band (the band reaches ' + money_text(money_of(int(Fraction(limit) * reach), template)) + ')'
                return out
    shadow = (model or {}).get('shadow') or {}
    if not shadow.get('available'):
        out['reason'] = 'no model score is available for this request'
        return out
    approve = 1 - float(shadow['probability'])
    need = float(Fraction(str(ex['minModelApprove'])))
    if approve < need:
        out['reason'] = 'the model put the chance you approve at ' + str(round(approve * 100)) + '%, under the ' + str(round(need * 100)) + '% you require'
        return out
    approved = sum(1 for c in comps if c.get('ownerDecision') == 'approve')
    if approved < int(ex['minSimilarApproved']):
        out['reason'] = 'you approved ' + str(approved) + ' of the closest comparable cases; the band needs ' + str(ex['minSimilarApproved'])
        return out
    out.update(applied=True, checks=[c['key'] for c in failing], modelApprove=round(approve, 4), similarApproved=approved, model=shadow.get('model'), modelVersion=shadow.get('version'),
               text='Approved as an exception inside the band you delegated: ' + ', '.join(c['label'][0].lower() + c['label'][1:] for c in failing) + ' over the limit but within the band; '
                    'the model put the chance you approve at ' + str(round(approve * 100)) + '%; you approved ' + str(approved) + ' of the closest comparable cases.')
    return out


def suggested_decline(policy, model):
    """A decline prepared for the Owner on a case that goes to them: when the exception band is on and the model puts the chance of a decline at or above
    suggestDeclineAbove. The agent never declines; this is one click for the Owner, with the reason written out."""
    ex = policy.get('exceptions') or {}
    shadow = (model or {}).get('shadow') or {}
    if not ex.get('enabled') or ex.get('suggestDeclineAbove') is None or not shadow.get('available'):
        return None
    p = float(shadow['probability'])
    if p < float(Fraction(str(ex['suggestDeclineAbove']))):
        return None
    return {'outcome': 'decline', 'probability': round(p, 4), 'model': shadow.get('model'), 'modelVersion': shadow.get('version'),
            'reason': 'Declined as the model suggested (' + str(round(p * 100)) + '% chance of a decline on cases like this).',
            'text': 'The model puts the chance that you decline at ' + str(round(p * 100)) + '%. Decline with one click, or decide as usual.'}


def decline_lines(policy, kind, f, template):
    """The Owner's decline lines (policy.autoDecline) this request is over: [{key, label, sentence}], extensions only, whether or not the switch is on (evaluate
    reads the switch). A value the records cannot establish is never over a line: the customer's total is skipped while the records are incomplete, the late share
    while which payments were late is unknown. A RECORDED total (records not confirmed complete) counts: more owed would only put it further over."""
    ad = policy.get('autoDecline') or {}
    if kind != 'extension':
        return []
    out, money = [], lambda units: money_text(money_of(units, template))
    days = lambda n: str(n) + (' day' if n == 1 else ' days')

    def over(key, label, actual, line, show):
        if line is not None and actual is not None and actual > line:
            out.append({'key': key, 'label': label, 'sentence': label + ': ' + show(actual) + ' is over your decline line of ' + show(line) + '.'})
    over('maxExtensionDays', 'Days past the current due date', f.get('extensionDays'), ad.get('maxExtensionDays'), days)
    over('maxDecisionExposure', 'Amount owed on this invoice', f.get('exposure'), _m(ad['maxDecisionExposure']) if ad.get('maxDecisionExposure') else None, money)
    over('maxCustomerExposure', "The customer's total exposure", f.get('customerExposure'), _m(ad['maxCustomerExposure']) if ad.get('maxCustomerExposure') else None, money)
    if not f.get('lateUnknown'):
        over('maxPriorLateShare', 'Late share of earlier payments', _f(f.get('priorLateShare')), _f(ad.get('maxPriorLateShare')), lambda x: str(round(float(x) * 100)) + '%')
    return out


def customer_rule(policy, customer_id, as_of):
    """The Owner's standing rule for this customer, if one is set and not past its until date: {maxExposure, maxExtensionDays, note, until}, else None."""
    rule = (policy.get('customers') or {}).get(customer_id)
    if not rule:
        return None
    if rule.get('until') and date.fromisoformat(rule['until']) < as_of:
        return None
    return rule


def with_customer_rule(policy, rule):
    """The policy with the customer's own bounds in place of the general ones (a copy; the general policy is untouched)."""
    if not rule:
        return policy
    out = {**policy, 'limits': dict(policy['limits']), 'extensions': dict(policy['extensions'])}
    if rule.get('maxExposure') is not None:
        out['limits']['maxCustomerExposure'] = rule['maxExposure']
    if rule.get('maxExtensionDays') is not None:
        out['extensions']['maxDays'] = rule['maxExtensionDays']
    return out


def customer_rule_text(rule, template):
    parts = []
    if rule.get('maxExposure') is not None:
        parts.append('most owed ' + money_text(money_of(_m(rule['maxExposure']), template)))
    if rule.get('maxExtensionDays') is not None:
        parts.append('longest extension ' + str(rule['maxExtensionDays']) + ' days')
    return 'Your standing rule for this customer applies (' + ', '.join(parts) + (', until ' + rule['until'] if rule.get('until') else '') + ')' + (': ' + rule['note'] if rule.get('note') else '') + '.'


def _m(amount):
    """Minor units of a policy amount (a money dict), else None."""
    return None if amount is None else int(amount['minorUnits'])


def _f(value):
    """An exact Fraction from None, an int, Fraction or its text ('0.25', '1/4'); None stays None."""
    return None if value is None else value if isinstance(value, Fraction) else Fraction(str(value))


def share_text(share):
    """A share as exact text: decimal when it ends within 4 places ('0.25'), else 'n/d'. Never a percentage."""
    share = _f(share)
    if share is None:
        return None
    if (10 ** 4) % share.denominator == 0:
        scaled = share.numerator * (10 ** 4 // share.denominator)
        return str(scaled // 10 ** 4) + ('.' + str(scaled % 10 ** 4).zfill(4).rstrip('0') if scaled % 10 ** 4 else '')
    return str(share.numerator) + '/' + str(share.denominator)


def times_text(ratio):
    """A ratio for a sentence: exact when it ends within 2 places ('4.5'), else 'about' and rounded half up to 2 places ('about 1.04'). Words only: the check
    compares the exact Fraction."""
    ratio = _f(ratio)
    if 100 % ratio.denominator == 0:
        return share_text(ratio)
    hundredths = (ratio * 100 + Fraction(1, 2)).__floor__()
    return 'about ' + share_text(Fraction(hundredths, 100))


def money_of(units, template):
    return {'minorUnits': str(units), 'currency': template['currency'], 'scale': template['scale']}


def money_view(units, template):
    """{minorUnits, currency, scale, text} for an amount, or None."""
    return None if units is None else {**money_of(units, template), 'text': money_text(money_of(units, template))}


def policy_authority(policy):
    return {'source': SOURCE, 'version': policy['version'], 'digest': policy.get('digest') or policy_digest(policy), 'mode': policy['mode'], 'paused': policy['paused']}


def category_on(policy, kind, new_customer):
    """Whether the Owner turned this category on: extensions enabled (and, for a customer with no earlier receipts, trial credit limited), or trial credit limited."""
    if kind == 'extension':
        return policy['extensions']['enabled'] and (not new_customer or policy['newCustomers']['trialCredit'] == 'limited')
    return policy['newCustomers']['trialCredit'] == 'limited'


# ---------------------------------------------------------------- business risk

def risk_checks(policy, kind, f, template, autonomous30d=None):
    """Each bound of the policy against the features f of one request: [{key, label, status ('pass' | 'fail' | 'unknown' | 'na'), sentence}]. A value
    that is None is unknown and never passes. f (minor units, Fractions or their text): exposure, customerExposure, and for an extension
    extensionDays, nothingElseOverdue, priorLateShare, lateUnknown, sizeRatio, isNew; for trial credit termsDays, isNew (no earlier invoice).
    autonomous30d: the autonomous approvals still in force in the last 30 days, or None (a back-test has none)."""
    out, money = [], lambda units: money_text(money_of(units, template))

    def add(key, label, status, sentence):
        out.append({'key': key, 'label': label, 'status': status, 'sentence': sentence})

    def at_most(key, label, actual, limit, show):
        if actual is None:
            add(key, label, 'unknown', label + ' cannot be established from the records.')
        elif actual <= limit:
            add(key, label, 'pass', label + ': ' + show(actual) + ' is within the limit of ' + show(limit) + '.')
        else:
            add(key, label, 'fail', label + ': ' + show(actual) + ' is over the limit of ' + show(limit) + '.')
    lim, ext, new = policy['limits'], policy['extensions'], policy['newCustomers']
    exposure = f.get('exposure')
    at_most('decision_exposure', 'Exposure of this decision', exposure, _m(lim['maxDecisionExposure']), money)
    at_most('customer_exposure', "The customer's total exposure after this decision", f.get('customerExposure'), _m(lim['maxCustomerExposure']), money)
    if f.get('coverageConfirmed') is False and out[-1]['status'] in ('pass', 'fail'):   # a caveat, not a block: the total is what the records show
        out[-1]['sentence'] += ' This is the RECORDED exposure; the records are not confirmed complete.'
    if lim['maxAutonomousExposure30d'] is None or autonomous30d is None:
        add('autonomous_30d', 'Autonomous approvals in 30 days', 'na', 'No limit on autonomous approvals in 30 days applies.')
    else:
        at_most('autonomous_30d', 'Autonomous approvals in 30 days (with this one)', None if exposure is None else autonomous30d + exposure,
                _m(lim['maxAutonomousExposure30d']), money)
    days = lambda n: str(n) + (' day' if n == 1 else ' days')
    if kind == 'extension':
        at_most('extension_days', 'Days past the current due date', f.get('extensionDays'), ext['maxDays'], days)
        # Quick setup (11 Nov): optional limits, absent from a policy saved before. A reviewed case recorded before them has no such feature (the key is
        # missing, not None): the back-test cannot judge it on this bound, so it is 'na' there rather than a failure of every earlier case.
        for key, fkey, label, limit in (('days_from_request', 'daysFromRequest', 'Days after the day the request was received', ext.get('maxDaysFromRequest')),
                                        ('days_past_original_due', 'daysPastOriginalDue', 'Days after the original due date', ext.get('maxDaysPastOriginalDue'))):
            if limit is None:
                continue
            if fkey in f:
                at_most(key, label, f[fkey], limit, days)
            else:
                add(key, label, 'na', label + ' is not recorded for this earlier case.')
        if ext['requireNothingElseOverdue']:
            nothing = f.get('nothingElseOverdue')
            add('nothing_else_overdue', 'Nothing else overdue', 'unknown' if nothing is None else 'pass' if nothing else 'fail',
                'Whether anything else is overdue cannot be established (an open invoice has no due date).' if nothing is None else
                'Nothing else is overdue.' if nothing else 'Something else is overdue besides this invoice.')
        cap, share = _f(ext['maxPriorLateShare']), _f(f.get('priorLateShare'))
        if cap is None or share is None and not f.get('lateUnknown'):
            add('late_history', 'Earlier late payments', 'na', 'No earlier payments are recorded, so there is no late history.' if cap is not None else 'The Owner set no limit for this.')
        elif f.get('lateUnknown') or share is None:
            add('late_history', 'Earlier late payments', 'unknown', 'Which earlier payments were late cannot be established (a payment has no received date, or an invoice no due date).')
        else:
            add('late_history', 'Earlier late payments', 'pass' if share <= cap else 'fail',
                'Late share of earlier payments ' + share_text(share) + (' is within' if share <= cap else ' is over') + ' the limit of ' + share_text(cap) + '.')
        multiple, ratio = _f(policy['restrictions']['unusualSizeMultiple']), _f(f.get('sizeRatio'))
        if multiple is None or ratio is None:
            add('unusual_size', 'Size against earlier invoices', 'na', 'No comparison with earlier invoices applies.')
        else:
            add('unusual_size', 'Size against earlier invoices', 'pass' if ratio <= multiple else 'fail',
                'The amount is ' + times_text(ratio) + ' times the median earlier invoice' + (' (within ' if ratio <= multiple else ' (over ') + 'the ' + share_text(multiple) + ' times the Owner allows).')
        if f.get('isNew') and new['trialCredit'] != 'limited' and exposure is not None and exposure > _m(new['maxExposure']):
            add('new_customer_exposure', 'Exposure for a customer with no earlier receipts', 'fail',   # 12 Nov 2026: this read "is over the limit of VND 0"
                'No payment from this customer is on record yet, and the policy does not let the agent decide for such customers (trial credit for new customers is off).')
        elif f.get('isNew'):
            at_most('new_customer_exposure', 'Exposure for a customer with no earlier receipts', exposure, _m(new['maxExposure']), money)
    else:
        add('trial_in_force', 'A trial credit already in force', 'fail' if f.get('trialInForce') else 'pass',
            'A trial credit for this customer is already in force; a further one goes to the Owner.' if f.get('trialInForce') else 'No trial credit for this customer is in force.')
        add('first_credit', 'Earlier dealings', 'pass' if f.get('isNew') else 'fail',
            'The customer has no earlier invoices, so this is their first credit.' if f.get('isNew')
            else 'The customer already has invoices with you: a trial credit line is for a customer with no earlier dealings, so the Owner decides this one.')
        at_most('trial_exposure', 'Trial credit exposure', exposure, _m(new['maxExposure']), money)
        at_most('trial_terms', 'Terms', f.get('termsDays'), new['maxTermsDays'], days)
    return out


def risk_summary(checks):
    failing = [c for c in checks if c['status'] == 'fail']
    unknown = [c for c in checks if c['status'] == 'unknown']
    return {'status': 'outside' if failing else 'unknown' if unknown else 'within', 'checks': checks,
            'failing': [c['sentence'] for c in failing], 'unknown': [c['sentence'] for c in unknown]}


def would_approve(policy, kind, f):
    """Whether this policy's BOUNDS would let the agent approve a case with these features, ignoring the model, the live totals and the switches (mode, pause,
    category on/off: they are judged at their own step of evaluate, so a back-test says what the bounds demonstrate): nothing held, every bound passing,
    (trial credit) the deposit share met, and the evidence complete."""
    if f.get('heldCustomer'):
        return False
    if any(c['status'] not in ('pass', 'na') for c in risk_checks(policy, kind, f, {'currency': '', 'scale': 0})):
        return False
    if kind == 'trial_credit' and not (f.get('depositShare') is not None and _f(f['depositShare']) >= _f(policy['newCustomers']['minDepositShare'])):
        return False
    return bool(f.get('evidenceComplete', True))


# ---------------------------------------------------------------- evidence sufficiency

def _day(text):
    return date.fromisoformat(text)


def _age(created_at, as_of):
    """Whole days from when a fact was confirmed (an ISO time) to the as-of date; never negative."""
    return max(0, (as_of - _day(created_at[:10])).days)


def deposit_level(data):
    """The verification level of a confirmed deposit from the basis Staff gave. A fact with no basis, or one this code does not know (an earlier row), is a
    staff_assertion: it never counts."""
    return DEPOSIT_BASES.get(data.get('basis'), 'staff_assertion')


def deposit_state(order, receipts, confirmed, as_of, staff_limit=None):
    """The verified deposit, by LEVEL. recorded_payment: receipts that are active, unallocated and received at most DEPOSIT_DAYS before the as-of date (their
    unallocated part): always counted. staff_checked_bank / staff_checked_document: a deposit Staff confirmed on the evidence page after seeing the money or a
    receipt; it is NOT a ledger payment, and it counts only when the order's exposure with it counted is at most `staff_limit` (None: Staff-checked deposits are
    not accepted, a recorded payment is required). staff_assertion (the customer said so, or no basis was kept): shown, never counted. A confirmed deposit with
    the reference of a recorded receipt is the same money: counted once if the amounts agree (the recorded payment), a CONTRADICTION if they differ. Each source
    says whether it is counted and, if not, why (notCounted: customer_statement | outside_window | over_staff_limit | not_accepted).
    Returns {verified, sources, contradictions}; verified is the counted total in minor units (the caller caps it at the order)."""
    window = as_of - timedelta(days=DEPOSIT_DAYS)
    by_ref = {ref_key(r['reference']): r for r in receipts if r.get('reference')}
    recorded, sources, contradictions, candidates = 0, [], [], []
    for r in receipts:
        if r.get('receivedDate') and window <= _day(r['receivedDate']) <= as_of and r['unallocated'] > 0:
            recorded += r['unallocated']
            sources.append({'source': 'records', 'level': 'recorded_payment', 'reference': r.get('reference'), 'amount': r['unallocated'], 'receivedDate': r['receivedDate'],
                            'recordId': r['id'], 'counted': True, 'notCounted': None})
    counted = set()   # one deposit confirmed twice (same reference, or same amount and day without one) is one deposit
    facts = [f for f in confirmed if f['kind'] == 'deposit']
    facts.sort(key=lambda f: deposit_level(f['data']) == 'staff_assertion')   # a stable sort: a checked deposit is kept ahead of the same one merely asserted
    for fact in facts:
        d = fact['data']
        same = (ref_key(d.get('reference')), int(d['amount']), d['receivedDate'] if not d.get('reference') else None)
        if same in counted:
            continue
        counted.add(same)
        recorded_row = by_ref.get(ref_key(d.get('reference'))) if d.get('reference') else None
        if recorded_row is not None and int(recorded_row['amount']) != int(d['amount']):
            contradictions.append({'key': 'deposit', 'factId': fact['id'], 'recordId': recorded_row['id'], 'confirmed': int(d['amount']), 'recorded': int(recorded_row['amount']),
                                   'reference': d.get('reference')})
        elif recorded_row is not None:
            sources.append({'source': 'staff_confirmed', 'level': 'recorded_payment', 'reference': d.get('reference'), 'amount': 0, 'corroboratedBy': recorded_row['id'],
                            'factId': fact['id'], 'counted': False, 'notCounted': None})
        else:
            level = deposit_level(d)
            row = {'source': 'staff_confirmed', 'level': level, 'reference': d.get('reference'), 'amount': int(d['amount']), 'receivedDate': d['receivedDate'], 'factId': fact['id'],
                   'counted': False, 'notCounted': 'customer_statement' if level == 'staff_assertion' else None if window <= _day(d['receivedDate']) <= as_of else 'outside_window'}
            sources.append(row)
            if row['notCounted'] is None:
                candidates.append(row)
    staff = sum(c['amount'] for c in candidates)
    accepted = False
    if candidates:
        exposure_with = order - min(recorded + staff, order)
        accepted = staff_limit is not None and exposure_with <= staff_limit
        for c in candidates:
            c['counted'], c['notCounted'] = accepted, None if accepted else 'not_accepted' if staff_limit is None else 'over_staff_limit'
    return {'verified': recorded + (staff if accepted else 0), 'sources': sources, 'contradictions': contradictions}


def source_text(s, template, staff_limit=None):
    """One deposit source in words, with its level: 'AUD 150.00 — checked by Staff in the bank account (not a recorded payment); reference X, received Fri 23 Oct 2026',
    and, for one that does not count, why not."""
    money = lambda units: money_text(money_of(units, template))
    out = money(s['amount']) + ' — ' + LEVEL_WORDS[s['level']]
    bits = ([('reference ' + str(s['reference']))] if s.get('reference') else []) + ([('received ' + display_date(s['receivedDate']))] if s.get('receivedDate') else [])
    out += ('; ' + ', '.join(bits)) if bits else ''
    why = {'customer_statement': 'it does not count towards the deposit',
           'outside_window': 'it does not count: it was received more than ' + str(DEPOSIT_DAYS) + ' days before the as-of date',
           'over_staff_limit': 'it does not count: a deposit Staff checked is accepted only when the exposure is ' + (money(staff_limit) if staff_limit is not None else 'within the limit') +
                               ' or less; record the payment in Nucleon Records',
           'not_accepted': "it does not count: the Owner's policy accepts only a payment recorded in Nucleon Records; record the payment in Nucleon Records"}.get(s.get('notCounted'))
    return out + (' — ' + why if why else '')


def assess_evidence(policy, kind, request, ledger, confirmed, as_of, template):
    """Evidence sufficiency (section 5): what the records and the facts Staff confirmed on a Nucleon page establish. Never what the model says.
    Returns {status: sufficient | missing | insufficient | contradictory, items, missing (Staff can provide), insufficient (they cannot),
    contradictions, verifiedDeposit, exposure, depositShare}. A data defect is `insufficient` (never a decline); no history is `none`, not a defect."""
    money = lambda units: money_text(money_of(units, template))
    items, missing, insufficient, contradictions = [], [], [], []

    def item(key, label, status, detail, need=None):
        row = {'key': key, 'label': label, 'status': status, 'detail': detail}
        items.append(row)
        if status == 'missing':
            missing.append({**row, 'need': need or {}})
        elif status == 'insufficient':
            insufficient.append(row)
    # 'Readable', not 'complete': whether the records are complete for a period is the Owner's separate confirmation (coverage_confirmed below), and the two
    # read as a contradiction when they shared the word (Hoang, 6 Nov 2026).
    item('records_complete', 'Records readable', 'insufficient' if ledger['incomplete'] else 'verified',
         ledger.get('incompleteText') or 'Every amount, due date and payment in this customer\'s records could be read and placed. Whether the records are complete for the period is the Owner\'s separate confirmation.')
    deposit = {'verified': 0, 'sources': [], 'contradictions': []}
    notes = []   # sentences about how the deposit is known, for the warnings
    if kind == 'trial_credit':
        order = request['orderAmount']
        staff_limit = _m(policy['newCustomers'].get('staffCheckedDepositUpTo'))
        used = ledger.get('depositsUsed') or {}   # a deposit already given for an earlier approved trial credit is not given again
        deposit = deposit_state(order, [r for r in ledger['receipts'] if r['id'] not in used.get('recordIds', ())],
                                [x for x in confirmed if x['id'] not in used.get('factIds', ())], as_of, staff_limit)
        for src in deposit['sources']:
            src['text'] = source_text(src, template, staff_limit) if src['amount'] else None
        shown = [x for x in deposit['sources'] if x['text']]
        notes = [x['text'] for x in shown if not x['counted'] or x['level'] != 'recorded_payment']
        capped = min(deposit['verified'], order)
        share, exposure = Fraction(capped, order), order - capped
        minimum = _f(policy['newCustomers']['minDepositShare'])
        required = -(-minimum.numerator * order // minimum.denominator)   # the smallest amount that meets the share, rounded up
        if share >= minimum:
            item('deposit', 'Deposit', 'verified', money(capped) + ' verified: ' + '; '.join(x['text'] for x in shown if x['counted']) + '.')
        else:
            refused = any(x['notCounted'] in ('over_staff_limit', 'not_accepted') for x in shown)
            record = staff_limit is None or refused   # Staff cannot supply this by checking: the payment must be recorded in Records
            item('deposit', 'Deposit', 'missing', (money(capped) + ' verified' if capped else 'No deposit is verified') + '; at least ' + money(required) + ' is needed (a deposit share of ' +
                 share_text(minimum) + ' of the order).' + ''.join(' ' + x['text'][0].upper() + x['text'][1:] + '.' for x in shown if not x['counted'] and x['text']),
                 {'kind': 'deposit', 'atLeast': required, 'fields': ['amount', 'receivedDate', 'reference', 'basis'], 'recordPayment': record,
                  'staffCheckedUpTo': None if staff_limit is None else money(staff_limit),
                  'how': ('Record the payment in Nucleon Records (a receipt for this customer), then ask the assistant to resolve the request again. '
                          + ("A deposit Staff only checked is not accepted at this exposure." if staff_limit is not None else
                             "The Owner's policy accepts only a payment recorded in Nucleon Records.")) if record else
                         ('Confirm a deposit you have seen yourself: its amount, the date received and its reference, and how you know: in the bank account, or on a receipt or remittance document. '
                          + 'What the customer says does not count. A deposit Staff checked is accepted when the exposure is ' + money(staff_limit) + ' or less.')})
        identity = next((x for x in confirmed if x['kind'] == 'business_identity' and _age(x['createdAt'], as_of) <= IDENTITY_DAYS and x['data'].get('basis') in IDENTITY_BASES), None)
        if not policy['newCustomers'].get('requireIdentity', True):
            item('business_identity', 'Business identity', 'not_required', "The Owner's policy does not ask a new customer for a business identity.")
        elif identity:
            background = business_background(identity['data'], as_of)
            item('business_identity', 'Business identity', 'verified', ('On file (fictional seed): ' if (identity.get('provenance') or {}).get('channel') == 'seed' else 'Confirmed by Staff: ') +
                 identity['data']['tradingName'] + ' (' + identity['data']['registration'] + '), ' + IDENTITY_WORDS[identity['data']['basis']] + '.' +
                 (' ' + background['sentence'] if background['sentence'] else ''))
            items[-1]['background'] = background
        else:
            unbased = any(x['kind'] == 'business_identity' and _age(x['createdAt'], as_of) <= IDENTITY_DAYS for x in confirmed)
            item('business_identity', 'Business identity', 'missing', ('An earlier statement about the business identity has no recorded basis (registry or document), so it does not count.' if unbased
                                                                      else 'No business identity is on file.'),
                 {'kind': 'business_identity', 'fields': ['registration', 'tradingName', 'basis'],
                  'how': 'Confirm the business registration and trading name, and say whether you saw them in a registry lookup or on a document.'})
        above = _m(policy['newCustomers']['tradeReferenceAbove'])
        if above is not None and exposure > above:
            ref = next((x for x in confirmed if x['kind'] == 'trade_reference' and _age(x['createdAt'], as_of) <= IDENTITY_DAYS), None)
            if ref:
                item('trade_reference', 'Trade reference', 'verified', 'Confirmed by Staff: ' + ref['data']['referee'] + '.')
            else:
                item('trade_reference', 'Trade reference', 'missing', 'Exposure of ' + money(exposure) + ' is over ' + money(above) + ', so a trade reference is needed.',
                     {'kind': 'trade_reference', 'fields': ['referee', 'summary'], 'how': 'Record who gave the reference and what they said.'})
        else:
            item('trade_reference', 'Trade reference', 'not_needed', 'Exposure is not over the level where a trade reference is needed.')
        if any(x['kind'] == 'no_prior_account' for x in confirmed) and ledger['invoiceCount'] > 0:
            contradictions.append({'key': 'no_prior_account', 'confirmed': 'no earlier account', 'recorded': str(ledger['invoiceCount']) + ' invoices'})
    else:
        exposure, share = request.get('amountOwed'), None
    for c in deposit['contradictions']:
        item('deposit_contradiction', 'Deposit matches the records', 'contradicted',
             'Staff confirmed ' + money(c['confirmed']) + ' for reference ' + str(c['reference']) + ', but the records show ' + money(c['recorded']) + ' under that reference.')
    if kind == 'trial_credit' and contradictions:
        item('no_prior_account', 'No earlier account', 'contradicted', 'Staff confirmed there is no earlier account, but the records hold ' + contradictions[0]['recorded'] + ' for this customer.')
    contradictions = [*deposit['contradictions'], *contradictions]
    above = _m(policy['evidence']['confirmedCoverageAbove'])
    if above is not None and exposure is not None and exposure > above:
        covered = ledger.get('coverageConfirmed')
        item('coverage_confirmed', 'Records confirmed complete', 'verified' if covered else 'insufficient',
             'The Owner confirmed these records are complete.' if covered else 'Exposure is over ' + money(above) + ", the level the Owner set under 'Records must be confirmed complete above this exposure', so the records must be confirmed complete, which only the Owner can do (Staff cannot supply this).")
    status = 'contradictory' if contradictions else 'missing' if missing else 'insufficient' if insufficient else 'sufficient'
    return {'status': status, 'items': items, 'missing': missing, 'insufficient': insufficient, 'contradictions': contradictions,
            'verifiedDeposit': min(deposit['verified'], request['orderAmount']) if kind == 'trial_credit' else None, 'depositSources': deposit['sources'], 'depositNotes': notes,
            'exposure': exposure, 'depositShare': share}


# ---------------------------------------------------------------- decision memory: comparables, track record, outcomes, suggestions

def distance(kind, f, g):
    """How far apart two cases' features are (0: alike). Weighted: new customer, exposure (log ratio), days or terms, deposit share or late share,
    anything else overdue. It only ranks; the float never decides a limit."""
    d = 0.0 if bool(f.get('isNew')) == bool(g.get('isNew')) else 1.0
    a, b = f.get('exposure'), g.get('exposure')
    d += 0.5 if a is None or b is None else abs(math.log((int(a) + 1) / (int(b) + 1)))
    key, share = ('extensionDays', 'priorLateShare') if kind == 'extension' else ('termsDays', 'depositShare')
    if f.get(key) is not None and g.get(key) is not None:
        d += 0.5 * abs(f[key] - g[key]) / max(f[key], g[key], 1)
    x, y = _f(f.get(share)), _f(g.get(share))
    d += 0.25 if (x is None) != (y is None) else 0.5 * float(abs(x - y)) if x is not None else 0.0
    if kind == 'extension' and f.get('nothingElseOverdue') is not None and g.get('nothingElseOverdue') is not None and f['nothingElseOverdue'] != g['nothingElseOverdue']:
        d += 0.5
    return round(d, 4)


def comparables(kind, f, pool, customer_id=None, limit=5):
    """The closest reviewed cases to a request, from `pool` restricted to fictional examples and live cases (the evaluation set is held out, whatever
    is passed). Each says whether it is the same customer's: another customer's is 'analogy, not this customer's history'."""
    rows = []
    for c in pool:
        if c.get('dataset') not in RETRIEVAL or c.get('kind') != kind or c.get('ownerDecision') not in ('approve', 'decline'):
            continue
        d = distance(kind, f, c['features'])
        same = bool(customer_id) and c['dataset'] == 'live' and c.get('customerId') == customer_id
        fictional = c['dataset'].startswith('fictional')
        preference = c['dataset'] == PREFERENCE
        rows.append({'id': c['id'], 'dataset': c['dataset'], 'kind': kind, 'fictional': fictional, 'sameCustomer': same, 'preference': preference, 'distance': d, 'similarity': round(1 / (1 + d), 3),
                     'analogyNote': "This customer's own earlier case." if same else
                     ("The Owner's own answer to a what-if about " + ('this customer' if customer_id and c.get('customerId') == customer_id else 'another customer') + ', not a real case.') if preference else
                     "Analogy, not this customer's history: another customer's " + ('fictional example case.' if fictional else 'earlier case.'),
                     'customerName': c.get('customerName'), 'ownerDecision': c['ownerDecision'], 'ownerReason': c.get('ownerReason'),
                     'outcome': (c.get('outcome') or {}).get('label'), 'summary': c.get('summary')})
    rows.sort(key=lambda r: (r['distance'], r['id']))
    return rows[:limit]


def declined_majority(comps):
    """Most of the closest comparable reviewed cases were declined by the Owner: at least three close ones, more than half declined."""
    close = [c for c in comps if c['distance'] <= 1.5][:5]
    return len(close) >= 3 and 2 * sum(1 for c in close if c['ownerDecision'] == 'decline') > len(close)


def backtest(policy, kind, cases):
    """The policy against reviewed cases: among those it would approve, how many the Owner approved, how many declined (false approvals), and the
    repayment outcomes. Each figure is a count with its sample size."""
    rows = [c for c in cases if c.get('kind') == kind and c.get('ownerDecision') in ('approve', 'decline')]
    would = [c for c in rows if would_approve(policy, kind, c['features'])]
    approved = [c for c in would if c['ownerDecision'] == 'approve']
    outcomes = {}
    for c in would:
        label = (c.get('outcome') or {}).get('label') or 'unknown'
        outcomes[label] = outcomes.get(label, 0) + 1
    return {'reviewed': len(rows), 'wouldApprove': len(would), 'ownerApproved': len(approved), 'ownerDeclined': len(would) - len(approved), 'outcomes': outcomes,
            'agreement': None if not would else share_text(Fraction(len(approved), len(would)))}


def _would_rows(policy, kind, cases):
    """The reviewed cases of this kind that the policy would approve (the rows backtest counts)."""
    return [c for c in cases if c.get('kind') == kind and c.get('ownerDecision') in ('approve', 'decline') and would_approve(policy, kind, c['features'])]


def _gate_count(rows):
    approved = sum(1 for c in rows if c['ownerDecision'] == 'approve')
    return {'cases': len(rows), 'approved': approved, 'declined': len(rows) - approved,
            'agreement': None if not rows else share_text(Fraction(approved, len(rows)))}


def track_record(policy, kind, cases):
    """Demonstrated reliability for one category, and the gate for ladder step 7. `trackRecord.sources` (D7) says which reviewed cases the gate counts:
    'fictional' = the held-out fictional_evaluation cases only (a SIMULATION; exactly the earlier behaviour), 'live' = live Owner-reviewed cases only
    (explicit AND tacit verdicts, counted and labelled apart), 'both' (the default) = the two pooled. Whatever the setting, the output shows both counts and
    agreement rates apart, plus the pooled figure (`gate`) and which one gated. A case counts when the policy would approve it and the Owner reviewed it,
    the same rule for both datasets. With no live reviewed case, 'both' is exactly 'fictional'. The input `cases` is the reviewed memory the server already
    computes (live cases carry verdictKind 'explicit' or 'tacit'); this function reads no database."""
    tr = policy['trackRecord']
    sources = tr.get('sources') or 'both'
    required = tr['minReviewedCases'] is not None or tr['minAgreement'] is not None
    evaluation = backtest(policy, kind, [c for c in cases if c.get('dataset') == 'fictional_evaluation'])
    live = backtest(policy, kind, [c for c in cases if c.get('dataset') == 'live'])
    fict_rows = _would_rows(policy, kind, [c for c in cases if c.get('dataset') == 'fictional_evaluation'])
    live_rows = _would_rows(policy, kind, [c for c in cases if c.get('dataset') == 'live'])
    fict, lv = _gate_count(fict_rows), _gate_count(live_rows)
    lv = {'dataset': 'live', **lv, 'explicit': sum(1 for c in live_rows if c.get('verdictKind') != 'tacit'), 'tacit': sum(1 for c in live_rows if c.get('verdictKind') == 'tacit')}
    fict = {'dataset': 'fictional_evaluation', **fict}
    pooled = {'dataset': 'fictional_evaluation + live (pooled for the gate only)', **_gate_count(fict_rows + live_rows)}
    counted = {'fictional': fict, 'live': lv, 'both': pooled}[sources]
    gated = 'fictional' if sources == 'both' and not live_rows else 'pooled' if sources == 'both' else sources
    n, agreed = counted['cases'], counted['approved']
    need = tr['minReviewedCases'] or 0
    enough = n >= need and (tr['minAgreement'] is None or n > 0 and Fraction(agreed, n) >= _f(tr['minAgreement']))
    status = 'not_required' if not required else 'established' if enough and n > 0 else 'not_established'
    rule = ('at least ' + str(tr['minReviewedCases']) + ' cases the policy would approve' if tr['minReviewedCases'] is not None else '') + \
           (' and ' if tr['minReviewedCases'] is not None and tr['minAgreement'] is not None else '') + \
           ('Owner agreement of at least ' + share_text(tr['minAgreement']) if tr['minAgreement'] is not None else '')
    if gated == 'fictional':
        sentence = ('Track record ' + status.replace('_', ' ') + ': the policy would approve ' + str(n) + ' of ' + str(evaluation['reviewed']) + ' held-out fictional evaluation cases in this category, and the '
                    'fictional Owner approved ' + str(agreed) + ' of them. ' + SIMULATION) if evaluation['reviewed'] else \
            'No reviewed evaluation cases exist for this category, so no track record is demonstrated.'
        if sources != 'fictional' and not evaluation['reviewed']:
            sentence += ' No live Owner-reviewed case counts yet either.'
    else:
        where = ('live Owner-reviewed cases' if gated == 'live' else 'fictional evaluation and live Owner-reviewed cases pooled')
        sentence = ('Track record ' + status.replace('_', ' ') + ' (counting ' + where + '): the policy would approve ' + str(n) + ' such cases in this category, and the Owner approved ' + str(agreed) +
                    ' of them (live: ' + str(lv['cases']) + ', ' + str(lv['explicit']) + ' explicit and ' + str(lv['tacit']) + ' tacit verdicts; fictional evaluation: ' + str(fict['cases']) + ').')
    if status == 'not_established' and n < need:
        sentence += ' ' + str(need - n) + ' more ' + ('live ' if gated == 'live' else '') + 'Owner-reviewed case' + ('' if need - n == 1 else 's') + ' the policy would approve ' + ('is' if need - n == 1 else 'are') + ' needed (' + str(n) + ' of ' + str(need) + ').'
    elif status == 'not_established' and n:
        sentence += ' The Owner agreement (' + share_text(Fraction(agreed, n)) + ') is below the ' + share_text(tr['minAgreement']) + ' this policy requires.'
    return {'status': status, 'required': required, 'rule': rule or None, 'simulation': sources != 'live', 'label': SIMULATION if sources != 'live' else
            'Counted on live Owner-reviewed cases (explicit and tacit verdicts, labelled apart); no fictional case is counted.',
            'evaluation': {'dataset': 'fictional_evaluation', **evaluation}, 'live': {'dataset': 'live', **live}, 'sources': sources, 'gatedOn': gated,
            'gate': {'sources': sources, 'gatedOn': gated, 'fictional': fict, 'live': lv, 'pooled': pooled, 'needed': tr['minReviewedCases'], 'shortBy': max(0, need - n) if required else 0},
            'sentence': sentence}


def derive_outcome(kind, params, invoices, as_of):
    """How a live case turned out, read from the records: {label: repaid | open_not_due | open_past_due | unknown, text}. invoices: [{id, issueDate,
    dueDate, open}]. An extension looks at its invoice against the approved date; a trial credit at the customer's invoices issued on or after the day it was approved."""
    if kind == 'extension':
        inv = next((i for i in invoices if i['id'] == params.get('invoiceId')), None)
        if inv is None:
            return {'label': 'unknown', 'text': 'The invoice is not in the records.'}
        if not inv['open']:
            return {'label': 'repaid', 'text': 'The records show the invoice paid.'}
        due = params.get('approvedDueDate') or inv.get('dueDate')
        return ({'label': 'open_past_due', 'text': 'Still open and past the approved date.'} if due and as_of > _day(due) else
                {'label': 'open_not_due', 'text': 'Still open, not yet past the approved date.'})
    later = [i for i in invoices if i.get('issueDate') and i['issueDate'] >= params.get('approvedOn', '9999-12-31')]
    if not later:
        return {'label': 'unknown', 'text': 'No invoice issued after the approval is in the records.'}
    if not any(i['open'] for i in later):
        return {'label': 'repaid', 'text': 'The records show every invoice issued after the approval paid.'}
    return ({'label': 'open_past_due', 'text': 'An invoice issued after the approval is open and past due.'} if any(i['open'] and i.get('dueDate') and as_of > _day(i['dueDate']) for i in later) else
            {'label': 'open_not_due', 'text': 'An invoice issued after the approval is open, not yet due.'})


ADVERSE_OBSERVED = ('late_paid', 'partial', 'open_past_due', 'written_off')   # outcomes.py observations that count against a bound (a live case)
ADVERSE_LABELS = ('late', 'defaulted')   # the stored labels of a fictional case that count against a bound
# Thresholds for the suggestions below; they become Owner settings in S2.
LOWER_MIN_DECLINES = 2   # reviewed cases inside a bound that the Owner declined or disagreed with, before lowering that bound is suggested
LOWER_MIN_ADVERSE = 1   # reviewed cases inside a bound with an adverse stored outcome, before lowering that bound is suggested
ADVISORY_MIN_OVERRIDES = 2   # live agent decisions overridden under the current policy version, before advisory mode is suggested


def adverse(c):
    """Whether a reviewed case turned out badly: a live case by its stored observation (outcomeObserved, S1a; no observation is not adverse and not good either),
    a fictional one by its stored label."""
    if c.get('dataset') == 'live':
        return c.get('observed') in ADVERSE_OBSERVED
    return (c.get('outcome') or {}).get('label') in ADVERSE_LABELS


def _dataset_counts(rows):
    out = {}
    for c in rows:
        d = out.setdefault(c['dataset'], {'n': 0, 'ownerApproved': 0, 'ownerDeclined': 0, 'adverseOutcomes': 0})
        d['n'] += 1
        d['ownerApproved' if c['ownerDecision'] == 'approve' else 'ownerDeclined'] += 1
        d['adverseOutcomes'] += 1 if adverse(c) else 0
    return out


def suggestions(policy, cases, template, overrides=()):
    """Deterministic suggestions, only ever suggestions (suggestionOnly). Nothing is applied and no restriction is ever suggested away. Reads fictional examples and
    live cases, never the held-out evaluation set. Each names its evidence and its datasets, with the counts per dataset (a live and a fictional case are never one number).
    RAISE: where reviewed cases just above a bound were approved by the Owner and repaid, with no Owner decline or late/defaulted case in that band, the Owner may raise
    the bound to the band's top. A tacit agreement counts as an approval there only as labelled (evidence.tacitAgreements), and never alone: at least one explicit approval.
    LOWER: where at least LOWER_MIN_DECLINES reviewed cases INSIDE the bound were declined or disagreed with by the Owner, or at least LOWER_MIN_ADVERSE turned out badly (a live case's
    stored observation late_paid, partial, open_past_due or written_off; a fictional case's stored label late or defaulted), lower the bound to just below the band (one minor unit or day under the
    lowest such case, never below zero; the band runs from there up to the bound). A single decline with no adverse outcome does not trigger it.
    MODE: `overrides` are the live agent decisions the Owner overrode that were made under the current policy version; ADVISORY_MIN_OVERRIDES or more propose advisory mode."""
    pool = [c for c in cases if c.get('dataset') in RETRIEVAL and c.get('ownerDecision') in ('approve', 'decline')]
    out = []

    def band(kind, value, bound):
        above = sorted((c for c in pool if c['kind'] == kind and c['features'].get(value) is not None and c['features'][value] > bound), key=lambda c: (c['features'][value], c['id']))
        run = []
        for c in above:
            if c['ownerDecision'] == 'approve' and (c.get('outcome') or {}).get('label') in GOOD_OUTCOMES and not adverse(c):
                run.append(c)
            else:
                break
        tacit = sum(1 for c in run if c.get('verdictKind') == 'tacit')
        return run if len(run) >= 3 and len(run) > tacit else []   # never on tacit verdicts alone

    def raise_evidence(run, exposure_range):
        return {'n': len(run), 'datasets': sorted({c['dataset'] for c in run}), 'cases': [c['id'] for c in run], 'ownerApproved': len(run), 'repaid': len(run), 'exposureRange': exposure_range,
                'explicitAgreements': len(run) - sum(1 for c in run if c.get('verdictKind') == 'tacit'), 'tacitAgreements': sum(1 for c in run if c.get('verdictKind') == 'tacit'),
                'byDataset': _dataset_counts(run)}

    def lower(kind, value, bound):
        """The problem cases inside the bound, lowest first: the adverse ones when there are at least LOWER_MIN_ADVERSE, and the Owner's declines when there are at least
        LOWER_MIN_DECLINES. A single decline with no adverse outcome is not enough."""
        inside = [c for c in pool if c['kind'] == kind and c['features'].get(value) is not None and c['features'][value] <= bound]
        bad = [c for c in inside if adverse(c)]
        declined = [c for c in inside if c['ownerDecision'] == 'decline']
        picked = (bad if len(bad) >= LOWER_MIN_ADVERSE else []) + [c for c in (declined if len(declined) >= LOWER_MIN_DECLINES else []) if c not in bad]
        return sorted(picked, key=lambda c: (c['features'][value], c['id']))

    def lower_evidence(kind, value, bound, problems):
        low = problems[0]['features'][value]
        inside = [c for c in pool if c['kind'] == kind and c['features'].get(value) is not None and low <= c['features'][value] <= bound]
        ev = {'n': len(inside), 'datasets': sorted({c['dataset'] for c in inside}), 'cases': [c['id'] for c in problems], 'bandCases': [c['id'] for c in inside],
              'ownerDeclined': sum(1 for c in inside if c['ownerDecision'] == 'decline'), 'ownerApproved': sum(1 for c in inside if c['ownerDecision'] == 'approve'),
              'adverseOutcomes': sum(1 for c in inside if adverse(c)), 'tacitAgreements': sum(1 for c in inside if c.get('verdictKind') == 'tacit'),
              'problemCases': [{'id': c['id'], 'dataset': c['dataset'], 'ownerDecision': c['ownerDecision'], 'value': str(c['features'][value]),
                                'outcome': c.get('observed') if c['dataset'] == 'live' else (c.get('outcome') or {}).get('label')} for c in problems],
              'byDataset': _dataset_counts(inside)}
        return ev, low

    cap = _m(policy['newCustomers']['maxExposure'])
    run = band('trial_credit', 'exposure', cap)
    if run:
        top = run[-1]['features']['exposure']
        note = ('The limit of ' + money_text(money_of(_m(policy['limits']['maxDecisionExposure']), template)) + ' for one decision would still apply.'
                if top > _m(policy['limits']['maxDecisionExposure']) else None)
        out.append({'id': 'newCustomers.maxExposure:' + str(top), 'kind': 'raise_limit', 'field': 'newCustomers.maxExposure', 'suggestionOnly': True,
                    'current': money_view(cap, template), 'suggested': money_view(top, template),
                    'text': 'Reviewed trial credits with exposure above ' + money_text(money_of(cap, template)) + ' up to ' + money_text(money_of(top, template)) + ' were all approved by the Owner and repaid (' +
                            str(len(run)) + ' cases, none declined or late). You may raise the trial exposure limit to ' + money_text(money_of(top, template)) + '. This is a suggestion; nothing changes until you save a new version.',
                    'evidence': raise_evidence(run, [str(run[0]['features']['exposure']), str(top)]), 'note': note})
    days = policy['extensions']['maxDays']
    run = band('extension', 'extensionDays', days)
    if run:
        top = run[-1]['features']['extensionDays']
        out.append({'id': 'extensions.maxDays:' + str(top), 'kind': 'raise_limit', 'field': 'extensions.maxDays', 'suggestionOnly': True, 'current': days, 'suggested': top,
                    'text': 'Reviewed extensions longer than ' + str(days) + ' days up to ' + str(top) + ' days were all approved by the Owner and repaid (' + str(len(run)) + ' cases, none declined or late). '
                            'You may raise the day limit to ' + str(top) + '. This is a suggestion; nothing changes until you save a new version.',
                    'evidence': raise_evidence(run, None), 'note': None})
    problems = lower('trial_credit', 'exposure', cap)
    if problems:
        ev, low = lower_evidence('trial_credit', 'exposure', cap, problems)
        new = max(0, low - 1)
        out.append({'id': 'newCustomers.maxExposure:lower:' + str(new), 'kind': 'lower_limit', 'field': 'newCustomers.maxExposure', 'suggestionOnly': True,
                    'current': money_view(cap, template), 'suggested': money_view(new, template),
                    'text': 'Among reviewed trial credits with exposure from ' + money_text(money_of(low, template)) + ' up to the limit of ' + money_text(money_of(cap, template)) + ', ' + _problem_words(ev) +
                            ' You may lower the trial exposure limit to ' + money_text(money_of(new, template)) + ', just below that band. This is a suggestion; nothing changes until you save a new version.',
                    'evidence': ev, 'note': 'Lowering a limit sends more cases to the Owner: this works against growing autonomy, so apply it only if the evidence is convincing.'})
    problems = lower('extension', 'extensionDays', days)
    if problems:
        ev, low = lower_evidence('extension', 'extensionDays', days, problems)
        new = max(0, low - 1)
        out.append({'id': 'extensions.maxDays:lower:' + str(new), 'kind': 'lower_limit', 'field': 'extensions.maxDays', 'suggestionOnly': True, 'current': days, 'suggested': new,
                    'text': 'Among reviewed extensions from ' + str(low) + ' days up to the limit of ' + str(days) + ' days, ' + _problem_words(ev) + ' You may lower the day limit to ' + str(new) +
                            ', just below that band. This is a suggestion; nothing changes until you save a new version.',
                    'evidence': ev, 'note': 'Lowering a limit sends more cases to the Owner: this works against growing autonomy, so apply it only if the evidence is convincing.'})
    overridden = [o for o in overrides]
    if policy['mode'] == 'delegated' and len(overridden) >= ADVISORY_MIN_OVERRIDES:
        out.append({'id': 'mode:advisory', 'kind': 'switch_mode', 'field': 'mode', 'suggestionOnly': True, 'current': 'delegated', 'suggested': 'advisory',
                    'text': 'The Owner overrode ' + str(len(overridden)) + ' of the agent\'s own decisions made under policy version ' + str(policy.get('version')) + '. You may switch the policy to advisory mode, where the agent '
                            'only recommends, until the bounds are reviewed. This is a suggestion; nothing changes until you save a new version.',
                    'evidence': {'n': len(overridden), 'datasets': ['live'], 'cases': [o['caseId'] for o in overridden], 'overrides': overridden, 'policyVersion': policy.get('version'),
                                 'byDataset': {'live': {'n': len(overridden)}}},
                    'note': 'Advisory mode sends every request to the Owner: this works against growing autonomy. Lowering the bound the overrides point to may be enough.'})
    return out


def _problem_words(ev):
    parts = []
    if ev['ownerDeclined']:
        parts.append(str(ev['ownerDeclined']) + ' declined or disagreed with by the Owner')
    if ev['adverseOutcomes']:
        parts.append(str(ev['adverseOutcomes']) + ' turned out late, partly paid, past due or lost')
    return (' and '.join(parts) if parts else 'a case went badly') + ' (' + str(ev['n']) + ' reviewed cases in the band).'


# ---------------------------------------------------------------- the evaluation

def median_ratio(amount, totals):
    """amount divided by the median of earlier invoice totals, exactly, or None with no earlier invoice (or no amount)."""
    if amount is None or not totals:
        return None
    s = sorted(totals)
    mid = Fraction(s[len(s) // 2]) if len(s) % 2 else Fraction(s[len(s) // 2 - 1] + s[len(s) // 2], 2)
    return Fraction(amount) / mid if mid else None


def features_of(policy, kind, request, ledger, evidence):
    """The features risk_checks, the comparables and the back-test read, from one request. Money in minor units, shares as Fractions."""
    held = request['customerId'] in policy['restrictions']['holdCustomers']
    if kind == 'extension':
        nothing = None if ledger['noDueOther'] and not ledger['overdueOther'] else ledger['overdueOther'] == 0
        exposure = request.get('amountOwed')
        return {'exposure': exposure, 'customerExposure': None if ledger['incomplete'] or exposure is None else ledger.get('debtBeforeGivenDeposits', ledger['debt']) + ledger.get('linesInForce', 0),
                'extensionDays': request['extensionDays'], 'nothingElseOverdue': nothing,
                'daysFromRequest': request.get('daysFromRequest'), 'daysPastOriginalDue': request.get('daysPastOriginalDue'),
                'priorLateShare': Fraction(ledger['lateReceipts'], ledger['receiptCount']) if ledger['receiptCount'] else None,
                'lateUnknown': bool(ledger['lateUnknown']), 'sizeRatio': median_ratio(exposure, ledger['priorInvoiceTotals']),
                'isNew': ledger['receiptCount'] == 0, 'heldCustomer': held, 'evidenceComplete': evidence['status'] == 'sufficient', 'coverageConfirmed': ledger.get('coverageConfirmed')}
    exposure = evidence['exposure']
    return {'exposure': exposure, 'orderAmount': request['orderAmount'], 'depositShare': evidence['depositShare'], 'termsDays': request['termsDays'],
            'customerExposure': None if ledger['incomplete'] else ledger.get('debtBeforeDeposits', ledger['debt']) + ledger.get('linesInForce', 0) + exposure,
            'trialInForce': ledger.get('trialInForce', 0) > 0, 'isNew': ledger['invoiceCount'] == 0, 'heldCustomer': held, 'evidenceComplete': evidence['status'] == 'sufficient',
            'coverageConfirmed': ledger.get('coverageConfirmed')}


def raw_features(f):
    """Features as plain JSON (Fractions as exact text), as a case keeps them and the decision memory stores them."""
    return {k: (str(v) if isinstance(v, Fraction) else v) for k, v in f.items()}


def key_facts(kind, request, f, evidence, template, as_of):
    """The facts a person is shown first, all from the backend: dates, days and amounts as the records give them, with the certainty mark."""
    if kind == 'extension':
        owed = request.get('amountOwed')
        return {'kind': 'extension', 'invoiceReference': request.get('invoiceReference'), 'originalDueDate': request['originalDueDate'], 'currentDueDate': request['currentDueDate'],
                'asOfDate': as_of.isoformat(), 'requestedDueDate': request['requestedDueDate'], 'extensionDays': request['extensionDays'],
                'daysOverdueAsOf': request.get('daysOverdue'), 'daysOverdueNote': request.get('daysOverdueReason'),
                'amountOwed': money_view(owed, template), 'amountMark': request.get('amountMark'), 'amountText': request.get('amountText')}
    return {'kind': 'trial_credit', 'asOfDate': as_of.isoformat(), 'orderAmount': money_view(request['orderAmount'], template),
            'verifiedDeposit': money_view(evidence['verifiedDeposit'], template), 'depositShare': share_text(evidence['depositShare']),
            'depositSources': [{'amount': money_view(x['amount'], template), 'level': x['level'], 'levelText': LEVEL_WORDS[x['level']], 'reference': x.get('reference'),
                                'receivedDate': x.get('receivedDate'), 'counted': x['counted'], 'notCounted': x['notCounted'], 'text': x['text']}
                               for x in evidence.get('depositSources', []) if x.get('text')],
            'exposure': money_view(evidence['exposure'], template), 'termsDays': request['termsDays'],
            'dueDateIfApproved': (as_of + timedelta(days=request['termsDays'])).isoformat()}


def evaluate(policy, kind, request, ledger, confirmed, memory, recommendation, template, as_of, policy_seen=None, autonomous30d=0, scorer=None):
    """What may happen to this request now, under the CURRENT policy (section 6). A pure function of plain inputs.
    policy: {version, ...rules}; request: the extension or trial parameters with the facts the records give; ledger: what the customer's records show
    (incomplete, debt, receipts, ...); confirmed: the facts Staff confirmed; memory: reviewed cases (any dataset: only examples and live feed
    the comparables, only the evaluation set the back-test); recommendation: {recommendation, reasoning} as the assistant gave it.
    Handling, in order: 1 restricted customer or contradictory evidence -> policy_hold; 2 risk outside the policy -> owner_review; 3 evidence Staff can
    provide is missing -> request_evidence (even in advisory mode); 4 evidence insufficient and not obtainable -> owner_review; 5 risk unknown ->
    owner_review; 6 most close comparables were declined -> owner_review; 7 track record required and not established -> owner_review; 8 advisory,
    paused or category off -> owner_review; 9 the assistant did not recommend approve -> owner_review; 10 otherwise autonomous_approve.
    scorer: the research hook (research.py), a function of the features returning {shadow, promoted, recommendation, text, version} or None. Its score is kept on the
    case as research; only when the Owner has promoted the model (recommendation 'escalate') does it count, as a step 9 reason beside the assistant's."""
    evidence = assess_evidence(policy, kind, request, ledger, confirmed, as_of, template)
    f = features_of(policy, kind, request, ledger, evidence)
    model = None
    if scorer:
        try:
            model = scorer(f)
        except Exception:   # research never fails a decision
            model = None
    rule = customer_rule(policy, request['customerId'], as_of)
    risk = risk_summary(risk_checks(with_customer_rule(policy, rule), kind, f, template, autonomous30d))
    comps = comparables(kind, f, memory, request['customerId'])
    small = small_overage(with_customer_rule(policy, rule), risk['checks'], f, template)
    if small['applied']:   # a money limit exceeded by a small margin the Owner allowed no longer fails, said so on each check
        for c in risk['checks']:
            if c['key'] in small['checks']:
                c['status'] = 'exception'
                c['sentence'] += ' Over by a small margin, inside the allowance the Owner set.'
        risk = risk_summary(risk['checks'])
    band = exception_band(with_customer_rule(policy, rule), kind, risk['checks'], f, template, model, comps) if not small['applied'] else {'applied': False, 'considered': False, 'reason': None, 'checks': []}
    if band['applied']:   # the failing checks inside the band no longer fail: they are exceptions the Owner delegated, said so on each check
        for c in risk['checks']:
            if c['key'] in band['checks']:
                c['status'] = 'exception'
                c['sentence'] += ' Inside the exception band the Owner delegated.'
        risk = risk_summary(risk['checks'])
    reliability = track_record(policy, kind, memory)
    reliability['comparablesDeclinedMajority'] = declined_majority(comps)
    rec = (recommendation or {}).get('recommendation')
    steps = []   # every step that applies, in order: the first decides, the rest tell the Owner what else stands in the way
    if f['heldCustomer']:
        steps.append((1, 'policy_hold', 'This customer is on the Owner\'s policy hold list, so the agent never decides it.'))
    for c in evidence['contradictions']:
        steps.append((1, 'policy_hold', 'The evidence contradicts the records (' + c['key'].replace('_', ' ') + '), so the request is on hold for the Owner.'))
    for s in risk['failing']:
        steps.append((2, 'owner_review', 'Outside the policy: ' + s))
    if evidence['missing']:
        steps.append((3, 'request_evidence', 'Evidence Staff can provide is missing: ' + ', '.join(m['label'].lower() for m in evidence['missing']) + '.'))
    for i in evidence['insufficient']:
        steps.append((4, 'owner_review', 'Evidence is insufficient and Staff cannot provide it: ' + i['detail']))
    for s in risk['unknown']:
        steps.append((5, 'owner_review', 'Unknown, which is never treated as zero: ' + s))
    # Step 8 is checked before 6 and 7: paused, advisory and category-off are the Owner's explicit settings, so they are the deciding reason
    # whenever they apply (D13, 31 Oct 2026). The step numbers are unchanged; 6 and 7 still appear in the reasons list.
    if policy['mode'] != 'delegated' or policy['paused'] or not category_on(policy, kind, f.get('isNew')):
        steps.append((8, 'owner_review', 'The policy is paused.' if policy['paused'] else 'The policy is in advisory mode, so the agent only recommends.' if policy['mode'] != 'delegated'
                      else 'This category is turned off in the policy (' + ('extensions' if kind == 'extension' and not policy['extensions']['enabled'] else 'trial credit for new customers') + ').'))
    if reliability['comparablesDeclinedMajority']:
        steps.append((6, 'owner_review', 'Most of the closest comparable reviewed cases were declined by the Owner.'))
    if reliability['status'] == 'not_established':
        steps.append((7, 'owner_review', 'The track record this policy requires is not established for this category. ' + reliability['sentence']))
    if rec not in APPROVING:
        steps.append((9, 'owner_review', 'The assistant recommended ' + (rec or 'nothing') + ', not approval, so the Owner decides.' + (' The agent declines on its own only over a decline line the Owner set (autonomous decline is ' + ('on' if (policy.get('autoDecline') or {}).get('enabled') else 'off') + ').' if rec == 'decline' else '')))
    if model and model.get('recommendation') == 'escalate':
        steps.append((9, 'owner_review', model['text']))
    # Autonomous decline (policy.autoDecline, 8 Nov 2026): over a decline line the Owner set, the agent never approves; it declines on its own only when the switch is
    # on, the assistant recommended declining, and none of the Owner's own stops applies (a hold, contradicting evidence, advisory, paused, extensions off).
    ad = policy.get('autoDecline') or {}
    crossed = decline_lines(policy, kind, f, template) if ad.get('enabled') else []
    declining = None
    if crossed:
        stops = [n for (n, _, _) in steps if n in (1, 8)]
        if rec == 'decline' and not stops:
            declining = crossed
        elif rec != 'decline':
            steps.insert(0, (2, 'owner_review', 'Over a decline line you set (' + crossed[0]['sentence'][0].lower() + crossed[0]['sentence'][1:-1] +
                             '), but the assistant did not recommend declining, so the Owner decides.'))
            steps.sort(key=lambda t: t[0])
    if declining:
        step, handling = 11, 'autonomous_decline'
        steps = [(11, 'autonomous_decline', 'Declined by the agent under your decline rule: ' + c['sentence']) for c in declining] + \
                [(n, h, t) for (n, h, t) in steps if not (n == 9 and t.startswith('The assistant recommended decline'))]
    else:
        step, handling = (steps[0][0], steps[0][1]) if steps else (10, 'autonomous_approve')
    suggested = suggested_decline(policy, model) if handling in ('owner_review', 'policy_hold') else None
    failed = [c for c in risk['checks'] if c['status'] == 'fail']
    why = None
    if steps and handling != 'autonomous_decline':   # the deciding reason, as one sentence naming its category (the status text and the card say it)
        why = {1: 'this request is on hold by policy (the customer is restricted, or the information contradicts the records)',
               2: ('a trial credit for this customer is already in force; a further one goes to the Owner' if failed and failed[0]['key'] == 'trial_in_force' else
                   'it is outside what the Owner delegated (' + (failed[0]['label'][0].lower() + failed[0]['label'][1:] if failed else 'a bound of the policy') + ')'),
               3: 'more information is needed from Staff before it can be decided',
               4: 'the records are insufficient and Staff cannot supply what is missing',
               5: 'something the records cannot establish is needed (an unknown is never treated as zero)',
               6: 'most of the closest comparable cases were declined by the Owner',
               7: 'the track record this policy requires is not established for this category',
               8: ("the Owner has paused the agent's authority" if policy['paused'] else 'the agent is in advisory mode' if policy['mode'] != 'delegated'
                   else 'this kind of request is turned off in the policy'),
               9: 'the assistant did not recommend approval'}[step]
        if step == 9 and rec in APPROVING and model and model.get('recommendation') == 'escalate':
            why = "the team's model put the chance that you decline at or above your bar"
        if step == 2 and steps[0][2].startswith('Over a decline line'):
            why = 'it is over a decline line the Owner set and the assistant did not recommend declining'
    warnings = []
    if rule:
        warnings.append(customer_rule_text(rule, template))
    if small['applied']:
        warnings.append(small['text'])
    elif small['considered'] and small.get('reason') and handling != 'autonomous_approve':
        warnings.append('The small-overage allowance did not apply: ' + small['reason'] + '.')
    if band['applied']:
        warnings.append(band['text'])
    elif band['considered'] and band.get('reason') and handling != 'autonomous_approve':
        warnings.append('The exception band did not apply: ' + band['reason'] + '.')
    if ledger['incomplete']:
        warnings.append(ledger.get('incompleteText') or 'The records for this customer are incomplete.')
    if kind == 'extension':
        if request.get('amountOwed') is None:
            warnings.append('The amount still owed on this invoice is not recorded, so its exposure is unknown (not zero).')
        elif request.get('amountMark') not in ('exact', 'stated'):
            warnings.append('The amount owed is ' + str(request.get('amountText') or request.get('amountMark')) + ', not an exact balance.')
        if request.get('daysOverdue') is None and request.get('daysOverdueReason'):
            warnings.append('Days overdue are not known: ' + request['daysOverdueReason'] + '.')
    if f.get('coverageConfirmed') is False and f.get('customerExposure') is not None:
        warnings.append("The customer's total exposure (" + money_text(money_of(f['customerExposure'], template)) + ') is the RECORDED exposure: the records are not confirmed complete, so more may be owed.')
    warnings += [s for s in risk['failing'] + risk['unknown'] if s not in warnings]
    warnings += [t for t in evidence.get('depositNotes', []) if t not in warnings]
    warnings += [t for (n, _, t) in steps if n in (1, 3, 4) and t not in warnings]
    if rec and rec not in APPROVING:
        warnings.append('The assistant recommended ' + rec + '.')
    if model and model.get('recommendation') == 'escalate' and model['text'] not in warnings:
        warnings.append(model['text'])
    changed = policy_seen is not None and policy_seen != policy['version']
    if changed:
        warnings.append('The Owner changed the policy after this was last assessed (version ' + str(policy_seen) + ' then, version ' + str(policy['version']) + ' now): the current version is applied.')
    return {'kind': kind, 'handling': handling, 'step': step, 'reasons': [t for (_, _, t) in steps] or ([band['text']] if band['applied'] else [small['text']] if small['applied'] else ['Within every bound of the policy, with the evidence verified.']),
            'keyFacts': key_facts(kind, request, f, evidence, template, as_of), 'warnings': warnings,
            'evidence': {**evidence, 'depositShare': share_text(evidence['depositShare'])}, 'risk': risk, 'reliability': reliability, 'comparables': comps, 'authority': policy_authority(policy),
            'policyChangedSinceAssessment': changed, 'features': raw_features(f), 'why': why, 'declineLines': crossed, 'model': model, 'customerRule': rule, 'exception': band, 'smallOverage': small, 'suggested': suggested,
            'recommendation': {'recommendation': rec, 'reasoning': (recommendation or {}).get('reasoning'), 'source': 'assistant', 'text': recommendation_text(rec)},
            'staffNeeds': [{'key': m['key'], 'label': m['label'], 'detail': m['detail'], **m['need']} for m in evidence['missing']] if handling == 'request_evidence' else [],
            'communication': dict(COMMUNICATION)}


# ---------------------------------------------------------------- words the assistant repeats

def days_words(n):
    return str(n) + (' day' if abs(n) == 1 else ' days')


def dates_sentence(kf):
    """The dates of an extension written out by code, so nobody has to work them out: the original and current due dates, the date asked for and the days it adds
    (after the current due date, and from the as-of date). '' for anything else. Hoang's NTK test (8 Nov 2026): a 15-day request had become 46 days unseen."""
    if kf.get('kind') != 'extension' or not kf.get('requestedDueDate') or not kf.get('currentDueDate'):
        return ''
    cur, asked = date.fromisoformat(kf['currentDueDate']), date.fromisoformat(kf['requestedDueDate'])
    orig = kf.get('originalDueDate')
    text = 'Dates: ' + ('originally due ' + display_date(orig) + ', ' if orig and orig != kf['currentDueDate'] else '') + 'currently due ' + display_date(kf['currentDueDate']) + \
        ', new date ' + display_date(kf['requestedDueDate']) + ' = ' + days_words((asked - cur).days) + ' after the current due date'
    if kf.get('asOfDate'):
        today = date.fromisoformat(kf['asOfDate'])
        text += ' (' + days_words((asked - today).days) + ' from today, ' + display_date(kf['asOfDate']) + ')'
    return text + '.'


def status_text(case):
    """One sentence for a case's backend status, written by code. The assistant repeats it verbatim; model text never sets a status. case: a stored
    case's fields (kind, status, handling, keyFacts, decision, authority, reasons, ...)."""
    kf, d, a = case.get('keyFacts') or {}, case.get('decision') or {}, case.get('authority') or {}
    v = ' (policy version ' + str(a.get('version')) + ')' if a.get('version') is not None else ''
    what = ('invoice ' + str(kf.get('invoiceReference')) + ' moved to ' + display_date(kf['requestedDueDate'])) if kf.get('kind') == 'extension' and kf.get('requestedDueDate') else \
           ('trial credit of ' + ((kf.get('exposure') or {}).get('text') or '') + ' exposure on ' + str(kf.get('termsDays')) + '-day terms') if kf.get('kind') == 'trial_credit' else 'this request'
    status, handling = case.get('status'), case.get('handling')
    if d.get('overridden') and d.get('outcome') == 'decline':
        return 'The Owner reversed the agent\'s decline: invoice ' + str(kf.get('invoiceReference')) + ' is now due ' + display_date(kf.get('requestedDueDate')) + '. ' + COMMUNICATION['note']
    if d.get('overridden'):
        return ('The Owner withdrew their own approval: ' if d.get('by') in ('owner', 'owner_exception') else 'The Owner overrode the earlier approval: ') + ('the due date is back to what it was.' if case.get('kind') == 'extension' else 'the trial credit line is revoked.')
    dates = dates_sentence(kf)
    dates = ' ' + dates if dates else ''
    if status == 'decided' and d.get('by') == 'agent' and d.get('outcome') == 'decline':
        return 'Declined by the agent under the Owner\'s decline rules' + v + ': invoice ' + str(kf.get('invoiceReference')) + ' keeps its due date of ' + \
            display_date(kf.get('currentDueDate')) + '.' + dates.replace('new date', 'date asked for') + ' The Owner can reverse it on the Decide page. ' + COMMUNICATION['note']
    if status == 'decided' and d.get('by') == 'agent':
        return 'Approved within the Owner\'s delegation policy' + v + ': ' + what + '.' + dates + ' It takes effect now inside Nucleon. ' + COMMUNICATION['note']
    if status == 'decided' and d.get('by') in ('owner', 'owner_exception'):
        return 'The Owner decided: ' + ('approved' if d.get('outcome') == 'approve' else 'declined') + ' (' + what + '). ' + COMMUNICATION['note']
    if status == 'gathering_evidence' and case.get('evidenceExpired'):
        return 'Not decided yet: the information request (' + ', '.join(case.get('needs') or []) + ') expired unanswered, so the case is stalled. Ask the assistant for the request again: ' \
            'the same request gets a fresh page; a different one for this customer replaces it. Nothing is approved.'
    if status == 'gathering_evidence':
        return 'Not decided yet: more information is needed (' + ', '.join(case.get('needs') or []) + '). Staff provide it on the Nucleon page; nothing is approved until then.'
    why = case.get('why')
    if status == 'on_hold':
        return 'On hold by policy for the Owner to resolve' + (': ' + why if why else '') + '. This is not a decline and nothing is approved.'
    if status == 'awaiting_owner':
        return 'Not approved: ' + (why[0].upper() + why[1:] + ', so the Owner decides' if why else 'this is outside what the Owner delegated, so the Owner decides') + \
            ' with the assistant\'s recommendation.' + dates + ' Nothing has been approved or sent.'
    if status == 'closed':
        return 'This case is closed; nothing was approved.'
    if case.get('assessedOnly'):
        word = {'autonomous_approve': 'it would be approved within the Owner\'s delegation policy', 'autonomous_decline': 'the agent would decline it under the Owner\'s decline rules', 'request_evidence': 'more information would be requested from Staff',
                'owner_review': 'it would go to the Owner', 'policy_hold': 'it would be put on hold for the Owner'}[handling]
        return 'Assessment only, nothing was stored: if resolved now, ' + word + v + (' (' + why + ')' if why and handling != 'autonomous_approve' else '') + '.' + dates
    return 'Status: ' + str(status) + '.'


# ---------------------------------------------------------------- the compact result the model reads (S1b)

FOR_MODEL_LIMIT = 800   # characters of JSON, at most (the whole forModel object); 600 until 8 Nov 2026, raised so the dates sentence is not cut


def _clip(text, n):
    text = ' '.join(str(text).split())
    return text if len(text) <= n else text[:max(0, n - 1)].rstrip() + '…'


def next_step(view):
    """What happens next, in one sentence written by code (the model repeats it; it never invents a next step)."""
    status, handling, d = view.get('status'), view.get('handling'), view.get('decision') or {}
    if view.get('practice'):
        return 'Practice mode is on: nothing stored, nothing sent to the Owner. Staff turn it off on their Nucleon Home page to send for real.'
    if view.get('stored') is False or status == 'assessed':
        return 'This is a preview and nothing was stored. Call resolveDecision to submit it.'
    if d.get('overridden'):
        return 'The Owner reversed it. Staff follow up with the customer if they were told; Nucleon sent nothing.'
    if status == 'decided' and d.get('by') == 'agent' and d.get('outcome') == 'decline':
        return 'Tell the customer yourself that it was declined; Nucleon sent nothing. The Owner can reverse it.'
    if status == 'decided' and d.get('by') == 'agent':
        return 'Tell the customer yourself; Nucleon sent nothing. A further request is a new resolveDecision call.'
    if status == 'decided':
        return 'Report the Owner\'s decision; Staff tell the customer, Nucleon sent nothing. A further request is a new resolveDecision call.'
    if status == 'gathering_evidence' and view.get('evidenceExpired'):
        return 'The information request expired. Ask the assistant again: the same request gets a fresh page; a different one replaces this case.'
    if status == 'gathering_evidence':
        link = view.get('evidenceLink')
        needs = ', '.join(view.get('needs') or [])
        return 'Staff open ' + (link or 'the Nucleon evidence page') + (' and enter: ' + needs if needs else '') + '. Nothing is approved until then.'
    if status == 'on_hold':
        return 'The Owner resolves the hold. Do not say it is approved.'
    if status == 'awaiting_owner':
        return 'The Owner decides. Do not say it is approved or tell the customer yet.'
    if handling == 'autonomous_approve':
        return 'Call resolveDecision to apply it.'
    return 'Report the statusText as it is.'


def key_facts_short(view):
    """At most 8 short fields from the case's key facts: who, which case, and the few figures a person checks first. Every value is text written by code."""
    kf = view.get('keyFacts') or {}
    out = {}
    customer = (view.get('customer') or {}).get('name')
    if customer:
        out['customer'] = _clip(customer, 40)
    if view.get('caseId'):
        out['caseId'] = view['caseId']
    if kf.get('kind') == 'extension':
        out['invoice'] = _clip(kf.get('invoiceReference'), 24)
        if kf.get('currentDueDate'):
            out['from'] = display_date(kf['currentDueDate'])
        if kf.get('requestedDueDate'):
            out['to'] = display_date(kf['requestedDueDate'])
        if kf.get('extensionDays') is not None:
            out['days'] = str(kf['extensionDays'])
        if (kf.get('amountOwed') or {}).get('text'):
            out['owed'] = _clip(kf['amountOwed']['text'], 28) + (' (' + kf['amountMark'] + ')' if kf.get('amountMark') else '')
    elif kf.get('kind') == 'trial_credit':
        for key, field in (('order', 'orderAmount'), ('deposit', 'verifiedDeposit'), ('exposure', 'exposure')):
            if (kf.get(field) or {}).get('text'):
                out[key] = _clip(kf[field]['text'], 28)
        if kf.get('termsDays') is not None:
            out['termsDays'] = str(kf['termsDays'])
        if kf.get('dueDateIfApproved'):
            out['dueIfApproved'] = display_date(kf['dueDateIfApproved'])
    return {k: out[k] for k in list(out)[:8]}


def for_model(view):
    """The compact, model-facing result of a delegation tool: {status, handling, statusText, why, nextStep, keyFacts}, at most FOR_MODEL_LIMIT characters of JSON in all.
    The full result stays beside it (the card reads that). If it is too long the facts and then the sentences are shortened, never the status or the handling."""
    out = {'status': view.get('status'), 'handling': view.get('handling'), 'statusText': view.get('statusText') or '', 'why': _clip(view.get('why') or '', 140),
           'nextStep': _clip(next_step(view), 150), 'keyFacts': key_facts_short(view)}
    size = lambda: len(json.dumps(out, ensure_ascii=False))   # noqa: E731
    out['statusText'] = _clip(out['statusText'], 440)
    while size() > FOR_MODEL_LIMIT and len(out['keyFacts']) > 3:
        out['keyFacts'].popitem()
    for field in ('statusText', 'why', 'nextStep'):
        over = size() - FOR_MODEL_LIMIT
        if over > 0:
            out[field] = _clip(out[field], max(40, len(out[field]) - over))
    return out


# ---------------------------------------------------------------- the Owner's what-ifs (4 Nov 2026)
# Real cases are rare, so the Owner is asked about what-ifs on real customers with numbers the records do not hold: first far outside, then narrowed
# between the highest the Owner approved and the lowest they declined, one dimension at a time. Each answer is stored as a case in the owner_preference
# dataset (features from the real ledger as of the day it is answered), so the comparables and the training table see it, labelled as a what-if.

PREF_START_MULTIPLE, PREF_UP_MULTIPLE, PREF_CLOSE_RATIO, PREF_DAYS_START, PREF_DAYS_CLOSE, PREF_FLOOR = 10, 4, 1.25, 180, 7, 100


def preference_bounds(answers, customer_id, kind, key, fixed=None):
    """(highest approved, lowest declined) of params[key] among the Owner's answers for this customer and kind; `fixed` = {other key: value} keeps the
    other dimension constant so the bounds are about one thing."""
    lo = hi = None
    for a in answers:
        p = a.get('params') or {}
        if a.get('customerId') != customer_id or a.get('kind') != kind or p.get(key) is None or a.get('ownerDecision') not in ('approve', 'decline'):
            continue
        if fixed and any(p.get(k) != v for k, v in fixed.items()):
            continue
        v = int(p[key])
        if a['ownerDecision'] == 'approve':
            lo = v if lo is None else max(lo, v)
        else:
            hi = v if hi is None else min(hi, v)
    return lo, hi


def _next_between(lo, hi, base, start_multiple, close_ratio, floor):
    """The next value to ask on one dimension, or None when the bounds are close enough: far out first, then the midpoint."""
    if lo is None and hi is None:
        return max(floor, base * start_multiple)
    if hi is None:
        return max(floor, lo * PREF_UP_MULTIPLE)
    if lo is None:
        return None if hi <= floor else max(floor, hi // PREF_UP_MULTIPLE)
    return None if hi <= lo * close_ratio else (lo + hi) // 2


def _amounts(invoices):
    return sorted(int((i.get('total') or {}).get('minorUnits') or 0) for i in invoices if (i.get('total') or {}).get('minorUnits'))


def _base_amount(invoices, all_invoices, template):
    """The customer's median invoice; a customer with none gets the business's median invoice (what an order usually looks like here), else one unit of 100."""
    for amounts in (_amounts(invoices), _amounts(all_invoices)):
        if amounts:
            return max(PREF_FLOOR, amounts[len(amounts) // 2])
    return 100 * 10 ** int(template.get('scale') or 2)


def _usual_terms(all_invoices):
    """The business's usual terms: the median of due date minus issue date over its invoices, else 14 days."""
    gaps = sorted((date.fromisoformat(i['originalDueDate']) - date.fromisoformat(i['issueDate'])).days for i in all_invoices if i.get('originalDueDate') and i.get('issueDate'))
    gaps = [g for g in gaps if 1 <= g <= 365]
    return gaps[len(gaps) // 2] if gaps else 14


def next_scenario(customers, invoices_for, current_due, answers, policy, template, as_of):
    """The what-if to ask now, or None: the (customer, kind) with the fewest answers that still has an open dimension. customers: the records' list;
    invoices_for(customer_id) and current_due(invoice) as Evidence gives them; answers: the stored owner_preference cases."""
    all_invoices = [i for c in customers for i in invoices_for(c['id'])]
    terms_fixed = _usual_terms(all_invoices)
    options = []
    # customers with a history first (their what-ifs say the most), then by name
    for c in sorted(customers, key=lambda x: (0 if invoices_for(x['id']) else 1, x.get('name') or '', x['id'])):
        invoices = invoices_for(c['id'])
        n = sum(1 for a in answers if a.get('customerId') == c['id'])
        # trial credit: the amount first (terms fixed at the business's usual), then the terms (amount fixed at the highest approved)
        base = _base_amount(invoices, all_invoices, template)
        lo, hi = preference_bounds(answers, c['id'], 'trial_credit', 'orderAmount', {'termsDays': terms_fixed})
        amount = _next_between(lo, hi, base, PREF_START_MULTIPLE, PREF_CLOSE_RATIO, PREF_FLOOR)
        if amount is not None:
            options.append((n, 0, c, {'kind': 'trial_credit', 'params': {'customerId': c['id'], 'orderAmount': int(amount), 'termsDays': terms_fixed}}))
        elif lo is not None:
            tlo, thi = preference_bounds(answers, c['id'], 'trial_credit', 'termsDays', {'orderAmount': lo})
            days = _next_between(tlo, thi, PREF_DAYS_START // PREF_START_MULTIPLE, PREF_START_MULTIPLE, 1.0 + PREF_DAYS_CLOSE / max(tlo or 1, 1), 1)
            if days is not None and days <= 365 and (thi is None or days < thi) and (tlo is None or days > tlo):
                options.append((n, 0, c, {'kind': 'trial_credit', 'params': {'customerId': c['id'], 'orderAmount': lo, 'termsDays': int(min(365, days))}}))
        # extension: days after the due date of the customer's largest open invoice
        open_invoices = [i for i in invoices if i.get('originalDueDate') and i.get('status', 'active') == 'active' and i.get('open', True)]
        if open_invoices:
            inv = max(open_invoices, key=lambda i: int((i.get('total') or {}).get('minorUnits') or 0))
            dlo, dhi = preference_bounds(answers, c['id'], 'extension', 'days', {'invoiceId': inv['id']})
            days = _next_between(dlo, dhi, PREF_DAYS_START // PREF_START_MULTIPLE, PREF_START_MULTIPLE, 1.0 + PREF_DAYS_CLOSE / max(dlo or 1, 1), 1)
            if days is not None and (dhi is None or days < dhi) and (dlo is None or days > dlo):
                due = current_due(inv)
                options.append((n, 1, c, {'kind': 'extension', 'params': {'customerId': c['id'], 'invoiceId': inv['id'], 'invoiceReference': inv.get('reference'), 'currentDueDate': due,
                                                                           'requestedDueDate': (date.fromisoformat(due) + timedelta(days=int(days))).isoformat(), 'days': int(days)}}))
    if not options:
        return None
    options.sort(key=lambda o: (o[0], o[1], 0 if invoices_for(o[2]['id']) else 1, o[2].get('name') or ''))
    n, _, c, s = options[0]
    p = s['params']
    if s['kind'] == 'trial_credit':
        text = 'If ' + c['name'] + ' asked today for ' + money_view(p['orderAmount'], template)['text'] + ' of stock on ' + str(p['termsDays']) + '-day terms, would you approve it?'
    else:
        text = 'If ' + c['name'] + ' asked to pay invoice ' + str(p.get('invoiceReference') or '') + ' ' + str(p['days']) + ' days after its due date (' + display_date(p['currentDueDate']) + ' → ' + display_date(p['requestedDueDate']) + '), would you approve it?'
    return {'id': 'pref:' + c['id'] + ':' + s['kind'] + ':' + ':'.join(str(p[k]) for k in ('orderAmount', 'termsDays', 'invoiceId', 'days') if p.get(k) is not None),
            'customer': {'id': c['id'], 'name': c['name']}, 'kind': s['kind'], 'params': p, 'text': text, 'answeredForCustomer': n}


# ---------------------------------------------------------------- Quick setup (11 Nov 2026)
# The Owner's first setup in a few plain questions (docs/superpowers/specs/2026-11-11-quick-setup-design.md). Answers map to settings by this fixed code, never by a
# model; a setting the helper does not ask about keeps its current value. The preview and the save both use quick_setup_policy, so they cannot disagree.

QUICK_FIELD = {'limits.maxDecisionExposure': 'maxInvoice', 'limits.maxCustomerExposure': 'maxCustomer', 'extensions.maxDaysFromRequest': 'daysFromRequest',
               'extensions.maxDaysPastOriginalDue': 'daysPastOriginalDue', 'extensions.maxDays': 'daysPastOriginalDue', 'restrictions.holdCustomers': 'holdCustomers'}
QUICK_CHECK = {'decision_exposure': 'maxInvoice', 'customer_exposure': 'maxCustomer', 'days_from_request': 'daysFromRequest', 'days_past_original_due': 'daysPastOriginalDue',
               'extension_days': 'daysPastOriginalDue', 'nothing_else_overdue': 'allowOtherOverdue', 'late_history': 'lateHistory'}
QUICK_LATE = {'any': None, 'some': '0.25', 'none': '0'}
QUICK_REVIEWS, QUICK_AGREEMENT = 5, '0.8'


def _quick_money(value):
    return value.replace(' ', '') if isinstance(value, str) else value


def quick_setup_policy(answers, current):
    """A policy body (for validate_policy) from the helper's answers on top of the current policy. Only an answer that differs from what the current policy
    already says (quick_setup_answers) is written, so running the helper again and saving untouched changes nothing the Owner tuned on the Control panel. One
    exception: the total-lateness answer is always written, because an older policy shows its longest extension there and should gain the total limit it implies.
    The longest single extension and the agent's decline line follow a changed total only when they were set to the same number. Raises nothing itself: a bad
    answer is refused by validate_policy, whose field QUICK_FIELD names as a question."""
    a = answers if isinstance(answers, dict) else {}
    p = json.loads(json.dumps({k: current[k] for k in POLICY_KEYS if k in current}))
    lim, ext, res, rec = p.setdefault('limits', {}), p.setdefault('extensions', {}), p.setdefault('restrictions', {}), p.setdefault('trackRecord', {})
    was = quick_setup_answers(current)
    changed = lambda key: key in a and a[key] != was.get(key)
    start = a.get('start')
    require(start is None or start in ('now', 'after_reviews', 'recommend'), 400, 'INVALID_INPUT', "start is 'now', 'after_reviews' or 'recommend'.", 'start')
    if changed('start'):
        if start == 'now':
            p['mode'], rec['minReviewedCases'], rec['minAgreement'] = 'delegated', None, None
        elif start == 'after_reviews':
            p['mode'], rec['minReviewedCases'], rec['minAgreement'], rec['sources'] = 'delegated', QUICK_REVIEWS, QUICK_AGREEMENT, 'live'
        else:
            p['mode'] = 'advisory'
    if changed('maxInvoice'):
        lim['maxDecisionExposure'] = _quick_money(a['maxInvoice'])
    if changed('maxCustomer'):
        lim['maxCustomerExposure'] = _quick_money(a['maxCustomer'])
    if changed('start') and start in ('now', 'after_reviews'):   # the Owner chose to let the agent decide; another change keeps the extensions switch as it is
        ext['enabled'] = True
    if changed('daysFromRequest'):
        ext['maxDaysFromRequest'] = a['daysFromRequest']
    if 'daysPastOriginalDue' in a:
        total, old = a['daysPastOriginalDue'], was['daysPastOriginalDue']
        ext['maxDaysPastOriginalDue'] = total
        if total != old:
            if ext.get('maxDays') == old:
                ext['maxDays'] = total
            ad = p.get('autoDecline') or {}
            if ad.get('enabled') and ad.get('maxExtensionDays') == old and not changed('agentDeclines'):
                ad['maxExtensionDays'] = total
    if changed('allowOtherOverdue'):
        ext['requireNothingElseOverdue'] = not a['allowOtherOverdue']
    if changed('lateHistory'):
        require(a['lateHistory'] in QUICK_LATE, 400, 'INVALID_INPUT', "lateHistory is 'any', 'some' or 'none'.", 'lateHistory')
        ext['maxPriorLateShare'] = QUICK_LATE[a['lateHistory']]
    if changed('holdCustomers'):
        res['holdCustomers'] = a['holdCustomers']
    if changed('agentDeclines'):
        p['autoDecline'] = ({**AUTO_DECLINE_DEFAULT, 'enabled': True, 'maxExtensionDays': ext.get('maxDaysPastOriginalDue') or ext.get('maxDays')}
                            if a['agentDeclines'] else dict(AUTO_DECLINE_DEFAULT))
    # New customers (13 Nov 2026): from a clean start trial credit stayed off, so every first order went to the Owner. "trial" lets the agent give a first order
    # on credit with at most the one-request limit at risk (a larger trial limit would be refused by that limit anyway), a deposit of at least a quarter unless
    # one was already set below 100%, and 30-day terms unless terms were set. A trial limit kept equal to the one-request limit follows a later change of it.
    new = p.setdefault('newCustomers', {})
    require('newCustomers' not in a or a['newCustomers'] in ('owner', 'trial'), 400, 'INVALID_INPUT', "newCustomers is 'owner' or 'trial'.", 'newCustomers')
    cur_new, cur_limit = current.get('newCustomers') or {}, (current.get('limits') or {}).get('maxDecisionExposure')
    if changed('newCustomers'):
        if a['newCustomers'] == 'trial':
            new['trialCredit'], new['maxExposure'], new['staffCheckedDepositUpTo'] = 'limited', lim.get('maxDecisionExposure'), lim.get('maxDecisionExposure')
            if new.get('minDepositShare') is None or Fraction(str(new['minDepositShare'])) >= 1:
                new['minDepositShare'] = '0.25'
            if not new.get('maxTermsDays'):
                new['maxTermsDays'] = 30
        else:
            new['trialCredit'] = 'off'
    elif changed('maxInvoice') and cur_new.get('trialCredit') == 'limited' and cur_limit is not None:
        for key in ('maxExposure', 'staffCheckedDepositUpTo'):
            if cur_new.get(key) is not None and _m(cur_new[key]) == _m(cur_limit):
                new[key] = lim['maxDecisionExposure']
    return p


def quick_setup_first_answers(amounts):
    """The helper's own starting answers for an Owner who has saved no policy yet (version 0 would show zero limits and "only recommends"): the agent decides
    from today inside modest limits taken from the business's own open invoices (amounts: {median, largest} with a 'plain' text each, or None). New customers
    stay with the Owner until the Owner chooses otherwise."""
    plain = lambda which: ((amounts or {}).get(which) or {}).get('plain') or ''
    return {'start': 'now', 'maxInvoice': plain('median'), 'maxCustomer': plain('largest'), 'daysFromRequest': 14, 'daysPastOriginalDue': 60,
            'allowOtherOverdue': False, 'lateHistory': 'some', 'holdCustomers': [], 'agentDeclines': False, 'newCustomers': 'owner'}


QUICK_LEVELS = {   # 12 Nov 2026: an owner asked for presets ("harsh, medium, relaxed") so that nobody has to work out every number first
    'strict': {'label': 'Strict', 'says': 'Small invoices only, one week more at most, and only for customers who have always paid on time.',
               'invoice': ('median', 1), 'customer': ('largest', 1), 'daysFromRequest': 7, 'daysPastOriginalDue': 30, 'allowOtherOverdue': False, 'lateHistory': 'none'},
    'balanced': {'label': 'Balanced', 'says': 'Typical invoices, two weeks more, for customers who mostly pay on time.',
                 'invoice': ('median', 1), 'customer': ('largest', 1), 'daysFromRequest': 14, 'daysPastOriginalDue': 60, 'allowOtherOverdue': False, 'lateHistory': 'some'},
    'relaxed': {'label': 'Relaxed', 'says': 'Up to your largest open invoice, a month more, also for customers who have paid late or have another invoice overdue.',
                'invoice': ('largest', 1), 'customer': ('largest', 2), 'daysFromRequest': 30, 'daysPastOriginalDue': 90, 'allowOtherOverdue': True, 'lateHistory': 'any'},
}


def quick_setup_levels(units, plain):
    """The three ready-made levels as Quick setup answers: [{name, label, says, answers}]. units: {'median': int, 'largest': int} minor units of the business's
    own open invoices, or None (then a level leaves the two money answers alone). plain: minor units -> the plain amount text an answer carries. A level sets
    six answers only: never how the agent starts, the customers it must not decide for, or whether it may say no."""
    out = []
    for name, v in QUICK_LEVELS.items():
        answers = {k: v[k] for k in ('daysFromRequest', 'daysPastOriginalDue', 'allowOtherOverdue', 'lateHistory')}
        if units:
            answers['maxInvoice'] = plain(units[v['invoice'][0]] * v['invoice'][1])
            answers['maxCustomer'] = plain(units[v['customer'][0]] * v['customer'][1])
        out.append({'name': name, 'label': v['label'], 'says': v['says'], 'answers': answers})
    return out


def quick_setup_answers(policy):
    """The answers that describe a policy, to prefill the helper. Money as plain text ('2000.00')."""
    from records import money_text_plain
    ext, rec = policy['extensions'], policy['trackRecord']
    share = ext.get('maxPriorLateShare')
    return {'start': 'recommend' if policy['mode'] == 'advisory' else 'after_reviews' if rec.get('minReviewedCases') is not None else 'now',
            'maxInvoice': money_text_plain(policy['limits']['maxDecisionExposure']), 'maxCustomer': money_text_plain(policy['limits']['maxCustomerExposure']),
            'daysFromRequest': ext.get('maxDaysFromRequest'), 'daysPastOriginalDue': ext.get('maxDaysPastOriginalDue') or ext.get('maxDays'),
            'allowOtherOverdue': not ext.get('requireNothingElseOverdue', True),
            'lateHistory': 'any' if share is None else 'none' if Fraction(share) == 0 else 'some',
            'holdCustomers': list(policy['restrictions'].get('holdCustomers') or []), 'agentDeclines': bool((policy.get('autoDecline') or {}).get('enabled')),
            'newCustomers': 'trial' if policy['newCustomers'].get('trialCredit') == 'limited' else 'owner'}


def _share_words(share):
    f = Fraction(share)
    return {Fraction(1, 4): 'a quarter', Fraction(1, 2): 'half', Fraction(1, 3): 'a third'}.get(f) or (str(round(float(f) * 100, 1)).rstrip('0').rstrip('.') + '%')


def quick_setup_summary(policy, template, names):
    """{decides: [sentences], comesToYou: [sentences]}: what the agent will decide on its own under this policy, and what always comes to the Owner, in plain words.
    names: customer id -> name, for the held customers."""
    money = lambda m: money_text(money_of(int(m['minorUnits']), template)) if m else None
    ext, lim, new, rec = policy['extensions'], policy['limits'], policy['newCustomers'], policy['trackRecord']
    if policy['mode'] == 'advisory':
        return {'decides': ['Nothing yet: the agent only recommends, and you decide everything.'], 'comesToYou': ['Every request.']}
    decides, comes = [], []
    if rec.get('minReviewedCases') is not None:
        agree = (' and agreed with at least ' + _share_words(rec['minAgreement']) + ' of them') if rec.get('minAgreement') is not None else ''
        decides.append('Nothing until you have reviewed ' + str(rec['minReviewedCases']) + ' of its recommendations' + agree + '. After that:')
    if ext['enabled']:
        decides.append('A later payment date on an invoice of up to ' + money(lim['maxDecisionExposure']) + ', when the customer would owe at most ' +
                       money(lim['maxCustomerExposure']) + ' in total.')
        parts = []
        if ext.get('maxDaysFromRequest') is not None:
            parts.append('up to ' + days_words(ext['maxDaysFromRequest']) + ' after the day the customer asks')
        if ext.get('maxDaysPastOriginalDue') is not None:
            parts.append("up to " + days_words(ext['maxDaysPastOriginalDue']) + " after the invoice's original due date")
        if ext.get('maxDaysPastOriginalDue') != ext['maxDays']:
            parts.append("up to " + days_words(ext['maxDays']) + " after the date it is due now")
        decides.append('The new date may be ' + ', and '.join(parts) + '.')
        if not ext['requireNothingElseOverdue']:
            decides.append('Also when the customer has other overdue invoices.')
        ad = policy.get('autoDecline') or {}
        if ad.get('enabled') and ad.get('maxExtensionDays') is not None:
            decides.append('It may decline a request for more than ' + days_words(ad['maxExtensionDays']) + ' when the assistant recommends declining.')
    if new['trialCredit'] == 'limited':
        share = new.get('minDepositShare')
        deposit = ' after a deposit of at least ' + _share_words(share) if share is not None and Fraction(str(share)) > 0 else ''
        terms = ', on terms up to ' + days_words(new['maxTermsDays']) if new.get('maxTermsDays') else ''
        identity = ', once Staff confirm who the business is' if new.get('requireIdentity', True) else ''
        decides.append('A first order on credit for a new customer, with up to ' + money(new['maxExposure']) + ' at risk' + deposit + terms + identity + '.')
    beyond = []   # settings kept from the Control panel that let the agent approve past the limits above
    if (policy.get('smallOverage') or {}).get('enabled'):
        beyond.append('A little over a money limit is still approved (set on the Control panel).')
    if (policy.get('exceptions') or {}).get('enabled'):
        beyond.append("Some requests over a limit, when the team's model says you would approve them (set on the Control panel).")
    n = len(policy.get('customers') or {})
    if n:
        beyond.append('Different limits for ' + str(n) + (' customer with its own rules' if n == 1 else ' customers with their own rules') + ' (set on the Control panel).')
    decides.extend(beyond)
    comes.append('Anything over those limits, except as above.' if beyond else 'Anything over those limits.')
    if ext['enabled'] and ext['requireNothingElseOverdue']:
        comes.append('Any request from a customer with another overdue invoice.')
    share = ext.get('maxPriorLateShare')
    if ext['enabled'] and share is not None:
        comes.append('Any request from a customer who has paid late before.' if Fraction(share) == 0 else
                     'Any request from a customer where more than ' + _share_words(share) + ' of their earlier payments were late.')
    held = policy['restrictions'].get('holdCustomers') or []
    if held:
        comes.append('Every request from: ' + ', '.join(names.get(i, i) for i in held) + '.')
    if new['trialCredit'] != 'limited':
        comes.append('Every first credit for a new customer.')
    if lim.get('maxAutonomousExposure30d'):
        comes.append('Approvals beyond ' + money(lim['maxAutonomousExposure30d']) + ' in 30 days (set on the Control panel).')
    if policy['restrictions'].get('unusualSizeMultiple') is not None:
        comes.append("An amount more than " + str(policy['restrictions']['unusualSizeMultiple']) + " times the customer's usual invoice (set on the Control panel).")
    if (policy.get('evidence') or {}).get('confirmedCoverageAbove'):
        comes.append("Any request above " + money(policy['evidence']['confirmedCoverageAbove']) + " until you confirm the customer's records are complete (set on the Control panel).")
    if policy.get('paused'):
        comes.insert(0, 'Everything, while the agent is paused.')
    return {'decides': decides, 'comesToYou': comes}
