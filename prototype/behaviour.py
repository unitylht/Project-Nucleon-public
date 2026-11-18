"""The deterministic part of the team's credit-model pipeline (Hoang's ledger replay), with his feature names: what a customer's
own records show of their payment behaviour strictly before a date. Pure functions on the stored records; money is integer minor
units. No model, no score: facts only. A payment with recorded allocations puts them where they were recorded; the rest of it
is applied first-in-first-out, oldest invoice first (shortcut: FIFO is an assumption, so allocationBasis says how much of it
was used). An opening balance has no known age: it is debt, never overdue, and only what is left after every invoice is paid
reduces it."""
from datetime import date, timedelta
from fractions import Fraction
from statistics import median

from agent import display_date, money_text

FEATURES = ('credit_term_days', 'debt_before_m', 'overdue_before_m', 'max_days_past_due_before', 'prior_invoice_documents', 'prior_billed_m',
            'prior_received_m', 'prior_receipt_count', 'has_prior_receipt', 'days_since_prior_receipt', 'observed_relationship_days',
            'prior_late_receipt_fraction')
CALCULATION_VERSION = 'calc-v1'   # bump when a rule of the replay, the checks or the recommendation changes: a saved basis names the one it was made with

# What each record the replay cannot place in time, or reads only in part, does to the figures (the trail's lists say it per record).
EFFECTS = {'stated': 'Counted at its stated amount still owed; payments are not matched to it, and it is left out of the amount billed.',
           'undated': 'No issue date: counted in what is owed and overdue (total less recorded allocations, else its stated amount), left out of the history.',
           'openNoDueDate': 'No due date: owed, but whether it is overdue cannot be established.',
           'unplacedPayment': 'No received date and no recorded allocation: it cannot be placed, so it reduces nothing.',
           'unplacedAllocation': 'Allocated to an invoice that is not in the records: the amount reduces nothing, and the rest of the payment is applied as usual.',
           'unreadable': 'No total and no amount still owed: it cannot be read, so it is left out of every figure.',
           'inOpening': 'Already part of the opening balance: counted there, not again.',
           'after': 'Dated after this date: not counted.',
           'uncountedInvoice': 'Allocated to an invoice this calculation does not count (dated after this date, part of the opening balance, or unreadable): '
                               'the payment is applied as if this allocation were not recorded.'}


def _minor(amount):
    return int(amount['minorUnits']) if amount else 0


def _live(records):
    return [x for x in records if x.get('status', 'active') == 'active']


# credit_term_days is the median, a half day rounded up (statistics.median averages the two middle values).
def replay(invoices, payments, allocations, opening_balances, as_of, own_invoice_id=None, horizon=None, with_trail=False):
    """One customer's records replayed up to, not including, as_of (a date). Returns the twelve FEATURES (credit_term_days and
    the days None when there is nothing to count; prior_late_receipt_fraction None with no receipts), lateReceipts (how many of
    prior_receipt_count came while something was past due), allocationBasis ('recorded', 'fifo' or 'mixed'), openingBalance,
    reconciles (debt equals opening + billed - received) and difference (debt minus that, in minor units). With own_invoice_id (the
    invoice a request is about): overdue_other_m (overdue on every other invoice) and own_overdue_m / own_days_past_due of that one.
    with_trail: also 'trail', what this replay did, recorded by its own loop as it did it (the calculation details): events in order
    (each invoice issued, with what was applied to it on issue; each payment, with its recorded allocations, what was applied oldest
    first (an assumption, not a record), to the opening balance and to customer credit, and whether it came while something was past
    due), then what is left on each invoice, the remaining opening balance, the credit held, and the records it could not place or read
    and the ones it left out, each with its effect (EFFECTS)."""
    day = lambda text: date.fromisoformat(text)
    horizon = horizon or as_of   # records before this date are read; overdue is judged against as_of (assessment_facts reads up to and including as_of)
    included = lambda x: (x.get('openingInclusion') or {}).get('status') != 'included'   # already part of the opening balance
    invs = sorted((i for i in _live(invoices) if i.get('issueDate') and day(i['issueDate']) < horizon and included(i) and i.get('total')),
                  key=lambda i: (i['issueDate'], i['id']))
    pays = sorted((p for p in _live(payments) if p.get('receivedDate') and day(p['receivedDate']) < horizon and included(p)),
                  key=lambda p: (p['receivedDate'], p['id']))
    # an invoice with a stated outstanding amount and no total counts with that amount, open and not matched by FIFO; one with neither
    # amount cannot be read at all (incomplete)
    dated = lambda i: bool(i.get('issueDate')) and day(i['issueDate']) < horizon
    stated = [i for i in _live(invoices) if not i.get('total') and i.get('outstandingAmount') and dated(i) and included(i)]
    # an active invoice with no issue date is never dropped: it counts in what is owed and overdue (total less allocations, else its stated
    # amount), and stays out of the history features (prior documents, billed, terms). With no amount of either kind it cannot be read.
    undated = [i for i in _live(invoices) if not i.get('issueDate') and included(i) and (i.get('total') or i.get('outstandingAmount'))]
    unreadable_list = [i for i in _live(invoices) if not i.get('total') and not i.get('outstandingAmount') and (dated(i) or not i.get('issueDate')) and included(i)]
    unreadable = len(unreadable_list)
    # a payment with no received date cannot be placed in time: only its recorded allocations count (they reduce what they were allocated
    # to); with none it cannot be placed at all (incomplete), and an allocation to an invoice that is not in the records cannot be placed either
    undated_pays = {p['id'] for p in _live(payments) if not p.get('receivedDate') and included(p)}
    allocated_pays = {a['paymentId'] for a in _live(allocations)}
    live_ids = {i['id'] for i in _live(invoices)}
    openings = [o for o in _live(opening_balances) if day(o['asOf']) < horizon]
    opening = sum(_minor(o['amount']) for o in openings)
    ids = {p['id'] for p in pays}
    unplaced_payment_ids = sorted(undated_pays - allocated_pays)
    unplaced_payments = len(unplaced_payment_ids)
    unplaced_allocation_list = [a for a in _live(allocations) if (a['paymentId'] in ids or a['paymentId'] in undated_pays) and a['invoiceId'] not in live_ids]
    unplaced_allocations = len(unplaced_allocation_list)
    total = {i['id']: _minor(i['total']) for i in invs}
    total.update({i['id']: _minor(i['total']) for i in undated if i.get('total')})
    total.update({i['id']: _minor(i['outstandingAmount']) for i in [*stated, *undated] if not i.get('total')})   # a cap only: the stated amount is not reduced
    # pre-pass: every recorded allocation is reserved on its invoice first (capped at the invoice total; an excess goes back to the
    # payment's unallocated remainder), so oldest-first only sees what each invoice has open net of the reservations
    reserved, recorded, reserved_undated = {}, {}, {}   # invoice id -> minor reserved; payment id -> [(invoice id, minor)]; reserved by undated payments
    for a in sorted(_live(allocations), key=lambda a: next((p['receivedDate'] for p in pays if p['id'] == a['paymentId']), '')):
        if (a['paymentId'] in ids or a['paymentId'] in undated_pays) and a['invoiceId'] in total:
            m = min(_minor(a['amount']), total[a['invoiceId']] - reserved.get(a['invoiceId'], 0))
            if m > 0:
                reserved[a['invoiceId']] = reserved.get(a['invoiceId'], 0) + m
                if a['paymentId'] in undated_pays:
                    reserved_undated[a['invoiceId']] = reserved_undated.get(a['invoiceId'], 0) + m
                else:
                    recorded.setdefault(a['paymentId'], []).append((a['invoiceId'], m))
        elif a['paymentId'] in ids and a['invoiceId'] not in live_ids:   # unplaced (the assessment is incomplete): what it paid must not reduce other invoices
            recorded.setdefault(a['paymentId'], []).append((a['invoiceId'], _minor(a['amount'])))
    undated_received = sum(reserved_undated.values())
    left = {i['id']: total[i['id']] - reserved_undated.get(i['id'], 0) for i in invs}      # open on each invoice (once issued)
    held = {i['id']: reserved.get(i['id'], 0) - reserved_undated.get(i['id'], 0) for i in invs}   # the part of that reserved for a recorded allocation not yet paid
    waiting = {}   # invoice id -> (payment id, recorded amount) received before the invoice was issued, applied when it appears
    issued, credit, prepaid = set(), 0, 0
    held_credit, credit_used = max(-opening, 0), 0   # an advance held in credit at the start: applied to invoices as issued, before any payment
    owing_opening = max(opening, 0)
    late, seen_day, day_late = 0, None, False
    kinds = set()
    log = [] if with_trail else None   # the trail: what the loop did, as it did it
    stated_ids, undated_ids = {i['id'] for i in stated}, {i['id'] for i in undated}
    # where a recorded allocation of a payment goes when its invoice is not issued yet: paid when it is issued, held against an undated
    # invoice's open amount, a stated invoice (its stated amount is not reduced) or an invoice not in the records
    waits = lambda iid: 'waiting' if iid in left else 'undated' if iid in undated_ids else 'stated' if iid in stated_ids else 'unplaced'
    events = sorted([(i['issueDate'], 0, i['id'], i) for i in invs] + [(p['receivedDate'], 1, p['id'], p) for p in pays], key=lambda e: e[:3])
    for _, kind, _, item in events:
        if kind == 0:   # an invoice is issued: waiting allocations pay it, then any customer credit, oldest first
            iid = item['id']
            issued.add(iid)
            paid = waiting.pop(iid, ())
            for _, m in paid:
                left[iid] -= m
                held[iid] -= m
                prepaid += m
            from_opening = min(held_credit, left[iid] - held[iid])
            left[iid] -= from_opening
            held_credit -= from_opening
            credit_used += from_opening
            from_credit = min(credit, left[iid] - held[iid])
            left[iid] -= from_credit
            credit -= from_credit
            prepaid += from_credit
            if log is not None:
                log.append({'kind': 'invoice', 'id': iid, 'reference': item.get('reference'), 'date': item['issueDate'], 'originalDueDate': item.get('originalDueDate'),
                            'total': total[iid], 'fromRecordedAllocations': [{'paymentId': pid, 'amount': m} for pid, m in paid],
                            'fromOpeningCredit': from_opening, 'fromCustomerCredit': from_credit, 'leftAfter': left[iid]})
            continue
        p, when = item, day(item['receivedDate'])
        # a receipt is late when, just before it, any open amount of this customer was past due
        # (judged once per day, before that day's payments, so the order of payments received on the same day does not matter)
        if seen_day != when:
            seen_day, day_late = when, any(left[i['id']] > 0 and i.get('originalDueDate') and day(i['originalDueDate']) < when for i in invs if i['id'] in issued)
        late += day_late
        amount = _minor(p['amount'])
        applied = []
        for iid, m in recorded.get(p['id'], ()):
            applied.append({'invoiceId': iid, 'amount': m, 'status': 'applied' if iid in issued else waits(iid)})
            if iid in issued:
                left[iid] -= m
                held[iid] -= m
            else:
                waiting.setdefault(iid, []).append((p['id'], m))
        rest = amount - sum(m for _, m in recorded.get(p['id'], ()))
        how = 'recorded' if rest <= 0 and p['id'] in recorded else 'fifo' if p['id'] not in recorded else 'mixed'
        kinds.add(how)
        fifo = []
        for i in invs:   # oldest-first for what no record allocates
            if rest <= 0:
                break
            if i['id'] in issued:
                take = min(rest, left[i['id']] - held[i['id']])
                left[i['id']] -= take
                rest -= take
                if take:
                    fifo.append({'invoiceId': i['id'], 'amount': take})
        to_opening = min(max(rest, 0), owing_opening)   # what is left after every invoice reduces the opening balance
        owing_opening -= to_opening
        credit += max(rest, 0) - to_opening   # still unapplied: a customer credit for invoices issued later
        if log is not None:
            log.append({'kind': 'payment', 'id': p['id'], 'reference': p.get('reference'), 'date': p['receivedDate'], 'amount': amount, 'late': bool(day_late),
                        'basis': how, 'recorded': applied, 'oldestFirst': fifo, 'toOpening': to_opening, 'toCredit': max(rest, 0) - to_opening})
    billed, received = sum(_minor(i['total']) for i in invs), sum(_minor(p['amount']) for p in pays)
    owed_stated = sum(_minor(i['outstandingAmount']) for i in stated)
    open_undated = {i['id']: total[i['id']] - reserved.get(i['id'], 0) if i.get('total') else _minor(i['outstandingAmount']) for i in undated}
    base_undated = sum(_minor(i['total'] if i.get('total') else i['outstandingAmount']) for i in undated)
    debt = sum(left.values()) + owing_opening + owed_stated + sum(open_undated.values())
    due = lambda i: day(i['originalDueDate']) if i.get('originalDueDate') else None
    # an invoice still open with no due date: owed, but whether it is overdue cannot be established
    open_no_due = [(i['id'], left[i['id']]) for i in invs if left[i['id']] > 0 and not i.get('originalDueDate')] \
        + [(i['id'], _minor(i['outstandingAmount'])) for i in stated if _minor(i['outstandingAmount']) > 0 and not i.get('originalDueDate')] \
        + [(i['id'], open_undated[i['id']]) for i in undated if open_undated[i['id']] > 0 and not i.get('originalDueDate')]
    no_due = len(open_no_due)
    no_due_other = sum(1 for k, _ in open_no_due if k != own_invoice_id)   # the ones the "nothing else overdue" check cannot judge
    no_due_amount = sum(m for _, m in open_no_due)
    past = [(left[i['id']], (as_of - due(i)).days) for i in invs if left[i['id']] > 0 and due(i) and due(i) < as_of]
    late_stated = [(i['id'], _minor(i['outstandingAmount']), (as_of - due(i)).days) for i in stated if due(i) and due(i) < as_of and _minor(i['outstandingAmount']) > 0]
    past += [(m, d) for _, m, d in late_stated]
    late_undated = [(i['id'], open_undated[i['id']], (as_of - due(i)).days) for i in undated if due(i) and due(i) < as_of and open_undated[i['id']] > 0]
    past += [(m, d) for _, m, d in late_undated]
    own = [(left[i['id']], (as_of - due(i)).days) for i in invs if i['id'] == own_invoice_id and left[i['id']] > 0 and due(i) and due(i) < as_of]
    own += [(m, d) for k, m, d in [*late_stated, *late_undated] if k == own_invoice_id]
    mine = next((due(i) for i in [*invs, *stated, *undated] if i['id'] == own_invoice_id), None)
    own_found = own_invoice_id is None or any(i['id'] == own_invoice_id for i in [*invs, *stated, *undated])
    own_open = left[own_invoice_id] if own_invoice_id in left else open_undated.get(own_invoice_id, next((_minor(i['outstandingAmount']) for i in stated if i['id'] == own_invoice_id), None))
    terms = sorted((day(i['originalDueDate']) - day(i['issueDate'])).days for i in [*invs, *stated] if i.get('originalDueDate') and i.get('issueDate'))
    dates = [day(x) for x in [*(i['issueDate'] for i in invs), *(p['receivedDate'] for p in pays),
                              *(o['asOf'] for o in _live(opening_balances) if day(o['asOf']) < horizon)]]
    net = opening + billed + owed_stated + base_undated - received - undated_received
    basis = 'fifo' if not kinds or kinds == {'fifo'} else 'recorded' if kinds == {'recorded'} else 'mixed'
    trail = None
    if with_trail:   # where the loop ended, and what it could not place or read, each with its effect; then what it left out
        ref = lambda i: {'id': i['id'], 'reference': i.get('reference')}
        cut = lambda kind, x, why: {'kind': kind, 'id': x['id'], 'reference': x.get('reference'), 'reason': why, 'effect': EFFECTS[why]}
        later = lambda x, key: x.get(key) and day(x[key]) >= horizon
        counted = set(total)
        trail = {'asOf': as_of.isoformat(), 'readsBefore': horizon.isoformat(),
                 'opening': {'balances': [{'id': o['id'], 'asOf': o['asOf'], 'amount': _minor(o['amount'])} for o in openings], 'total': opening,
                             'owingAtStart': max(opening, 0), 'creditAtStart': max(-opening, 0)},
                 'events': log, 'invoices': [{**ref(i), 'left': left[i['id']], 'reservedUnpaid': held[i['id']]} for i in invs],
                 'remainingOpening': owing_opening, 'creditHeld': credit + held_credit, 'customerCredit': credit, 'openingCreditUnused': held_credit,
                 'stated': [{**ref(i), 'amount': _minor(i['outstandingAmount']), 'effect': EFFECTS['stated']} for i in stated],
                 'undated': [{**ref(i), 'open': open_undated[i['id']], 'effect': EFFECTS['undated']} for i in undated],
                 'openNoDueDate': [{'id': k, 'amount': m, 'effect': EFFECTS['openNoDueDate']} for k, m in open_no_due],
                 'unplacedPayments': [{'id': k, 'effect': EFFECTS['unplacedPayment']} for k in unplaced_payment_ids],
                 'unplacedAllocations': [{'id': a['id'], 'paymentId': a['paymentId'], 'invoiceId': a['invoiceId'], 'amount': _minor(a['amount']),
                                          'effect': EFFECTS['unplacedAllocation']} for a in unplaced_allocation_list],
                 'unreadableInvoices': [{**ref(i), 'effect': EFFECTS['unreadable']} for i in unreadable_list],
                 'excluded': [cut('invoice', i, 'inOpening' if not included(i) else 'after') for i in _live(invoices) if not included(i) or later(i, 'issueDate')] +
                             [cut('payment', x, 'inOpening' if not included(x) else 'after') for x in _live(payments) if not included(x) or later(x, 'receivedDate')] +
                             [cut('openingBalance', o, 'after') for o in _live(opening_balances) if later(o, 'asOf')] +
                             [cut('allocation', a, 'uncountedInvoice') for a in _live(allocations) if (a['paymentId'] in ids or a['paymentId'] in undated_pays)
                              and a['invoiceId'] in live_ids and a['invoiceId'] not in counted]}
    return {**({'trail': trail} if with_trail else {}), 'credit_term_days': int(median(terms) + 0.5) if terms else None, 'debt_before_m': debt, 'overdue_before_m': sum(m for m, _ in past),
            'max_days_past_due_before': max((d for _, d in past), default=0), 'prior_invoice_documents': len(invs) + len(stated), 'invoicesWithTotal': len(invs), 'invoicesStated': len(stated), 'invoicesBoth': sum(1 for i in invs if i.get('outstandingAmount')),
            'unreadableInvoices': unreadable, 'ownMissing': not own_found, 'ownOpen': own_open, 'undatedInvoices': len(undated), 'ownUndated': any(i['id'] == own_invoice_id for i in undated),
            'noDueDate': no_due, 'noDueOther': no_due_other, 'noDueAmount': no_due_amount, 'unplacedPayments': unplaced_payments, 'unplacedAllocations': unplaced_allocations,
            'incomplete': unreadable > 0 or not own_found or no_due > 0 or unplaced_payments > 0 or unplaced_allocations > 0, 'prior_billed_m': billed,
            'prior_received_m': received, 'prior_receipt_count': len(pays), 'has_prior_receipt': int(bool(pays)),
            'days_since_prior_receipt': (as_of - day(pays[-1]['receivedDate'])).days if pays else None,
            'observed_relationship_days': (as_of - min(dates)).days if dates else None,
            'prior_late_receipt_fraction': late / len(pays) if pays else None, 'lateReceipts': late,
            'overdue_other_m': sum(m for m, _ in past) - sum(m for m, _ in own), 'own_overdue_m': sum(m for m, _ in own),
            'own_days_past_due': own[0][1] if own else 0, 'own_due_date': mine and mine.isoformat(), 'own_days_after_due': mine and (as_of - mine).days,
            'allocationBasis': basis, 'prepaymentApplied': prepaid, 'openingCreditApplied': credit_used,
            'openingBalance': opening, 'openingOwing': owing_opening, 'reconciles': debt == net, 'difference': debt - net}


CURRENT = ('debt_before_m', 'overdue_before_m', 'max_days_past_due_before', 'overdue_other_m', 'own_overdue_m', 'own_days_past_due', 'own_due_date',
           'own_days_after_due', 'ownOpen', 'ownMissing', 'ownUndated', 'undatedInvoices', 'noDueDate', 'noDueOther', 'noDueAmount', 'unplacedPayments', 'unplacedAllocations', 'unreadableInvoices', 'incomplete', 'allocationBasis', 'prepaymentApplied', 'openingCreditApplied',
           'openingBalance', 'openingOwing', 'reconciles', 'difference')
PRIOR = ('prior_invoice_documents', 'prior_billed_m', 'prior_received_m', 'prior_receipt_count', 'lateReceipts', 'prior_late_receipt_fraction',
         'observed_relationship_days', 'days_since_prior_receipt', 'credit_term_days', 'allocationBasis')   # the history, strictly before the date


def _stated_clause(both, only):
    """What the invoices say beyond a total: ', 2 of them also stating an amount still owed' (invoices with a total that also state one) and
    ', 1 more stating only an amount still owed' (no total); nothing for a count of 0."""
    return (', ' + str(both) + ' of them also stating an amount still owed' if both else '') + (', ' + str(only) + ' more with only a stated amount still owed' if only else '')


def assessment_facts(invoices, payments, allocations, opening_balances, as_of, own_invoice_id=None):
    """The replay for an assessment. The historical features (prior receipts, late share, relationship days, billed before) read the records
    strictly before as_of. The CURRENT facts (debt, overdue amount and days, the invoice a request is about, completeness) read every live
    record dated up to and including as_of, because an invoice entered today is owed today. The policy checks use the current facts only.
    The invoice a request is about missing from the current set makes the records incomplete: a record left out never makes a case eligible.
    trail: {current: the current run's own trail (replay with_trail), prior: what the strictly-prior run counted (PRIOR)}."""
    before = replay(invoices, payments, allocations, opening_balances, as_of, own_invoice_id)
    now = replay(invoices, payments, allocations, opening_balances, as_of, own_invoice_id, horizon=as_of + timedelta(days=1), with_trail=True)
    prior = {'asOf': as_of.isoformat(), 'readsBefore': as_of.isoformat(), **{k: before[k] for k in PRIOR}}
    return {**before, **{k: now[k] for k in CURRENT}, 'current_invoice_documents': now['prior_invoice_documents'], 'currentWithTotal': now['invoicesWithTotal'],
            'currentStated': now['invoicesStated'], 'currentBoth': now['invoicesBoth'], 'current_billed_m': now['prior_billed_m'], 'current_credit_term_days': now['credit_term_days'],
            'trail': {'current': now['trail'], 'prior': prior}}


# ---------------------------------------------------------------- the assessment: facts, and checks against the owner's limits

NO_LIMIT = 'The owner has set no day limit for staff, so the owner decides.'   # the owner's wording of the requested_days check with no limit
STAFF_NO_LIMIT = 'No limits are set for staff to act within, so this case goes to the owner.'   # the same, as staff read it
NO_MODEL = ("These figures are numerical analysis of the recorded ledger plus the owner's policy checks. No approval predictor runs: the team's "
            "labelled data are proxies for lateness, not owner decisions, and too few to measure. The features carry the pipeline's names so a "
            "validated predictor can be attached later.")
RECOMMENDS = {'approve_within_authority': 'approve', 'decline_by_policy': 'decline'}   # the owner's outcome each one points to; escalate points to none


INCOMPLETE = 'The records are incomplete for this customer: {} could not be read (no total and no amount still owed), so the figures below leave them out.'
NO_DUE = 'The records are incomplete for this customer: {} has no due date: whether it is overdue cannot be established.'
UNPLACED_PAYMENTS = 'The records are incomplete for this customer: {} has no received date and no recorded allocation, so it cannot be placed.'
UNPLACED_ALLOCATIONS = 'The records are incomplete for this customer: {} is allocated to an invoice that is not in the records, so it cannot be placed.'
OWN_MISSING = 'The invoice this request is about is not among the current records (it may be missing, withdrawn, dated after this date or part of an opening balance), so the figures cannot be relied on.'


def incomplete_text(f):
    return ' '.join(([INCOMPLETE.format(_n(f['unreadableInvoices'], 'invoice'))] if f['unreadableInvoices'] else []) +
                    ([NO_DUE.format(_n(f['noDueDate'], 'invoice'))] if f.get('noDueDate') else []) +
                    ([UNPLACED_PAYMENTS.format(_n(f['unplacedPayments'], 'payment'))] if f.get('unplacedPayments') else []) +
                    ([UNPLACED_ALLOCATIONS.format(_n(f['unplacedAllocations'], 'allocation'))] if f.get('unplacedAllocations') else []) +
                    ([OWN_MISSING] if f['ownMissing'] else []))


def undated_text(count):
    """What happens to an invoice with no issue date, in words."""
    return (_n(count, 'invoice') + (' has' if count == 1 else ' have') + ' no issue date: counted in what is owed and overdue, left out of the history.') if count else None


def _unknown_overdue(f, money):
    """'Overdue not known: 1 open invoice has no due date (VND 1,000,000).' or None when every open invoice has a due date."""
    k = f.get('noDueDate', 0)
    return ('Overdue not known: ' + _n(k, 'open invoice') + (' has' if k == 1 else ' have') + ' no due date (' + money(f.get('noDueAmount', 0)) + ').') if k else None


def _n(count, word):
    return str(count) + ' ' + word + ('' if count == 1 else 's')


def own_text(f, money):
    """The invoice's due date and the oldest-first matching, said separately: a date in the past is never "not past its due date"."""
    missing = 'The issue date of this invoice is missing: it is counted in what is owed and overdue, and left out of the history. ' if f.get('ownUndated') else ''
    if f['own_due_date'] is None:
        return missing + 'No due date is on record for this invoice, or it is not part of the replay.'
    after, on = f['own_days_after_due'], display_date(f['own_due_date'])
    if after <= 0:
        return missing + 'This invoice is due on ' + on + ', in ' + _n(-after, 'day') + '.'
    return (missing + 'This invoice was due on ' + on + ', ' + _n(after, 'day') + ' before this date. By oldest-first matching, ' +
            (money(f['own_overdue_m']) + ' of it is still open.' if f['own_overdue_m'] else
             'earlier payments already cover it; the records state no amount still owed for it.'))


def opening_paid_text(amount):
    """The opening balance fully paid, in the words the assessment and the customer overview share (amount as each writes it)."""
    return 'The opening balance of ' + amount + ' was paid by earlier payments, oldest first.'


def _debt_sentence(f, money):
    """What is owed, said for each mix: on the recorded invoices after the recorded payments, with what remains of an opening balance of
    unknown age; all of it that opening balance when the invoices are paid; or the opening balance said as paid when nothing remains."""
    debt, owing, opening = f['debt_before_m'], f.get('openingOwing', f['openingBalance']), f['openingBalance']
    left = ' (' + money(owing) + ' of the opening balance of ' + money(opening) + ' remains after payments)' if owing != opening else ''
    if opening > 0 and owing > 0 and debt == owing:
        return money(debt) + ' is owed, all of it from an opening balance of unknown age' + left + '; the recorded invoices are paid.'
    said = money(debt) + ' is owed on the recorded invoices after the recorded payments.'
    if opening > 0 and owing > 0:
        return said + ' It includes ' + money(owing) + ' from an opening balance of unknown age' + ('.' if not left else left + '.')
    return said + (' ' + opening_paid_text(money(opening)) if opening > 0 else '')


def facts_view(f, template, as_of):
    """The replay's features as numbers and as one sentence each, written by code (a fraction is never a percentage). template:
    {currency, scale}, for the money words."""
    money = lambda units: money_text({'minorUnits': str(units), **template})
    n, late, overdue, days = f['prior_receipt_count'], f['lateReceipts'], f['overdue_before_m'], f['max_days_past_due_before']
    pay = _n(n, 'earlier payment')
    unknown = _unknown_overdue(f, money)
    said = {
        'credit_term_days': ('No invoice issued before this date has both an issue date and a due date.' + (' The current invoices are on terms of ' + _n(f['current_credit_term_days'], 'day') + '.' if f.get('current_credit_term_days') is not None else '')) if f['credit_term_days'] is None else
        'Invoices are on terms of ' + _n(f['credit_term_days'], 'day') + ' (the median of due date minus issue date over the recorded invoices, rounded to a whole day).',
        'debt_before_m': _debt_sentence(f, money),
        'overdue_before_m': (money(overdue) + ' is overdue, the oldest ' + _n(days, 'day') + ' past due. ' + unknown) if overdue and unknown else
        money(overdue) + ' is overdue, the oldest ' + _n(days, 'day') + ' past due.' if overdue else unknown or 'Nothing is overdue.',
        'max_days_past_due_before': ('The longest anything has been past due is ' + _n(days, 'day') + '.' + (' Days past due are not known for the open invoices with no due date.' if unknown else '')) if days else
        'Days past due not known: ' + _n(f['noDueDate'], 'open invoice') + (' has' if f['noDueDate'] == 1 else ' have') + ' no due date.' if unknown else 'Nothing is past due.',
        'prior_invoice_documents': _n(f['prior_invoice_documents'], 'invoice') + (' was' if f['prior_invoice_documents'] == 1 else ' were') + ' recorded before this date; ' +
        str(f.get('current_invoice_documents', f['prior_invoice_documents'])) + ' are recorded up to and including it (' + str(f.get('currentWithTotal', f['invoicesWithTotal'])) +
        ' with a recorded total' + _stated_clause(f.get('currentBoth', f['invoicesBoth']), f.get('currentStated', f['invoicesStated'])) + ').',
        'prior_billed_m': money(f['prior_billed_m']) + ' was invoiced before this date (recorded totals only).',
        'prior_received_m': money(f['prior_received_m']) + ' has been received.',
        'prior_receipt_count': pay + (' is' if n == 1 else ' are') + ' recorded.',
        'has_prior_receipt': 'An earlier payment is recorded.' if n else 'No earlier payment is recorded.',
        'days_since_prior_receipt': 'No earlier payment is recorded.' if n == 0 else 'The last payment was ' + _n(f['days_since_prior_receipt'], 'day') + ' before this date.',
        'observed_relationship_days': 'No records yet.' if f['observed_relationship_days'] is None else
        'The records for this customer cover ' + _n(f['observed_relationship_days'], 'day') + '.',
        'prior_late_receipt_fraction': 'No earlier payments are recorded.' if n == 0 else
        str(late) + ' of ' + pay + ' arrived' + ' while something was overdue.'}
    unit = {'debt_before_m': 'money', 'overdue_before_m': 'money', 'prior_billed_m': 'money', 'prior_received_m': 'money', 'has_prior_receipt': 'flag',
            'prior_late_receipt_fraction': 'fraction'}
    return {'asOf': as_of.isoformat(), 'allocationBasis': f['allocationBasis'], 'reconciles': f['reconciles'],
            'prepaymentText': money(f['prepaymentApplied']) + ' was received before any invoice was open and applied to later invoices.' if f['prepaymentApplied'] else None,
            'openingCreditText': money(f['openingCreditApplied']) + ' was held in credit at the start and applied to later invoices.' if f['openingCreditApplied'] else None,
            'differenceText': 'The invoices, payments and opening balance account for the debt exactly.' if f['reconciles'] else
            'The debt differs from invoiced minus received by ' + money(abs(f['difference'])) + ', for example a payment beyond what was invoiced.',
            'items': [{'name': k, 'value': f[k], 'unit': unit.get(k, 'days' if 'days' in k else 'count'), 'text': said[k],
                       **({'amountText': money(f[k]) + ' (as recorded)'} if unit.get(k) == 'money' else {})} for k in FEATURES],
            'lateReceipts': late, 'ownInvoiceText': own_text(f, money),
            'undatedText': undated_text(f.get('undatedInvoices', 0)),
            'currentText': 'Current records (up to and including ' + display_date(as_of.isoformat()) + '): ' + _n(f.get('current_invoice_documents', f['prior_invoice_documents']), 'invoice') +
            ', ' + money(f['debt_before_m']) + ' owed' + (', ' + money(overdue) + ' of it overdue.' if overdue else ', overdue not known.' if unknown else ', nothing overdue.') +
            (' ' + undated_text(f['undatedInvoices']) if f.get('undatedInvoices') else ''),
            'ownOpenText': None if f.get('ownOpen') is None else money(f['ownOpen']) + ' is still owed on this invoice.',
            'incomplete': f['incomplete'], 'incompleteText': incomplete_text(f) if f['incomplete'] else None,
            'summaryText': (incomplete_text(f) + ' ' if f['incomplete'] else '') + said['overdue_before_m'] + ' ' + said['prior_late_receipt_fraction']}


def checks_for(auth, f, asked_days, template, measured=None):
    """Each check against the owner's limits: {name, applies, passes, label (why it stops staff, when it fails), sentence}. A limit the
    owner left unset does not apply, except the staff day limit: with none, staff may approve nothing. measured: a list that gets, per
    check, {name, actual, threshold}: the very values the check compared (for the calculation details); the checks are the same."""
    money = money_text
    debt, share, limit = {'minorUnits': str(f['debt_before_m']), **template}, f['prior_late_receipt_fraction'], auth['staffMayApproveUpToDays']
    out = []

    def add(name, applies, passes, label, sentence, unknown=None, actual=None, threshold=None):
        """unknown: why the check cannot be judged (a sentence), or None. An unknown check is neither pass nor fail: passes False so that
        nothing is approved on it, unknown True so that nothing is declined on it either."""
        u = bool(unknown) and applies
        out.append({'name': name, 'applies': applies, 'passes': (passes or not applies) and not u, 'unknown': u,
                    'label': label,
                    'sentence': unknown if u else sentence if applies else 'The owner set no limit for this.'})
        if measured is not None:
            measured.append({'name': name, 'actual': actual, 'threshold': threshold})
    nothing = f['overdue_other_m'] == 0   # the invoice a request is about may be late: that is why it is asked
    other = f.get('noDueOther', 0)
    add('nothing_overdue', auth['requireNothingOverdue'], nothing and not other, 'overdue status cannot be established' if nothing and other else 'something else is overdue',
        'Nothing else is overdue.' if nothing else money({'minorUnits': str(f['overdue_other_m']), **template}) + ' is overdue besides this invoice.',
        unknown=('Cannot be established: ' + _n(other, 'open invoice') + (' has' if other == 1 else ' have') + ' no due date') if nothing and other else None,
        actual={'overdueOther': f['overdue_other_m'], 'noDueOther': other}, threshold=auth['requireNothingOverdue'])
    if f['incomplete']:   # not an owner's limit: it stops staff and goes to the owner
        out.append({'name': 'records_complete', 'applies': True, 'passes': False, 'unknown': False, 'label': 'the records are incomplete for this customer',
                    'sentence': incomplete_text(f)})
        if measured is not None:
            measured.append({'name': 'records_complete', 'actual': 'incomplete', 'threshold': 'complete'})
    cap = auth['maxPriorLateShare']
    ok = share is None or cap is None or Fraction(f['lateReceipts'], f['prior_receipt_count']) <= Fraction(str(cap))   # exact, no float
    late_text = ('No earlier payments are recorded.' if share is None else
                 str(f['lateReceipts']) + ' of ' + _n(f['prior_receipt_count'], 'earlier payment') + ' arrived while something was overdue' +
                 ('; the owner allows up to a fraction of ' + format(cap, 'g') + '.' if cap is not None else '.'))
    cannot = f.get('unplacedPayments', 0) or f.get('noDueDate', 0)   # receipts or due dates missing: lateness cannot be counted
    add('late_history', cap is not None, ok, 'too many earlier payments were late' if not (ok and cannot) else 'late history cannot be established', late_text,
        unknown=('Cannot be established: ' + ' and '.join(([_n(f['unplacedPayments'], 'payment') + ' without a received date'] if f.get('unplacedPayments') else []) +
                                                        ([_n(f['noDueDate'], 'open invoice') + ' without a due date'] if f.get('noDueDate') else []))) if ok and cannot else None,
        actual={'late': f['lateReceipts'], 'of': f['prior_receipt_count']}, threshold=cap)
    within = limit is not None and asked_days is not None and asked_days <= limit
    add('requested_days', True, within,
        'no day limit is set for staff' if limit is None else 'the days asked are not known' if asked_days is None else 'requested days over the staff limit',
        NO_LIMIT if limit is None else
        'The days asked are not known yet.' if asked_days is None else
        _n(asked_days, 'day') + ' asked' + (' is within' if within else ' is more than') + ' the ' + _n(limit, 'day') + ' staff may approve.',
        actual=asked_days, threshold=limit)
    cap = auth['maxOutstanding']
    ok = cap is None or f['debt_before_m'] <= int(cap['minorUnits'])
    cannot = f.get('unreadableInvoices', 0) or f.get('unplacedAllocations', 0)
    add('outstanding_amount', cap is not None, ok, 'the amount owed is over the limit' if not (ok and cannot) else 'the amount owed cannot be established',
        money(debt) + ' is owed' + ('; the limit is ' + money(cap) + '.' if cap else '.'),
        unknown=('Cannot be established: ' + ' and '.join(([_n(f['unreadableInvoices'], 'invoice') + ' without an amount'] if f.get('unreadableInvoices') else []) +
                                                        ([_n(f['unplacedAllocations'], 'allocation') + ' to an invoice not in the records'] if f.get('unplacedAllocations') else []))) if ok and cannot else None,
        actual=f['debt_before_m'], threshold=cap and int(cap['minorUnits']))
    return out


UNKNOWN = 'Unknown'   # an amount or a state the records cannot establish: never 0, never "none"
CHECK_NAMES = {'nothing_overdue': 'Nothing else overdue', 'records_complete': 'Records complete', 'late_history': 'Earlier late payments',
               'requested_days': 'Days asked', 'outstanding_amount': 'Amount owed'}


def check_rows(checks, measured, template):
    """The checks as the calculation details show them: {key, name, actual, actualText, threshold, thresholdText, result ('pass', 'fail',
    'unknown' or 'not set'), label, sentence}, from each check and the values it compared (checks_for's measured). Words only: nothing is
    judged here, the result is the check's own."""
    money = lambda m: money_text({'minorUnits': str(m), **template})
    by = {m['name']: m for m in measured}
    out = []
    for c in checks:
        m, unknown = by.get(c['name'], {}), c.get('unknown')
        a, t = m.get('actual'), m.get('threshold')
        if c['name'] == 'nothing_overdue':   # the measured amount, and apart from it the rule
            actual = UNKNOWN if unknown else money(a['overdueOther']) + ' overdue besides this invoice'
            threshold = 'None allowed' if t else 'Not set'
        elif c['name'] == 'late_history':
            actual = UNKNOWN if unknown else 'No earlier payments' if not a['of'] else str(a['late']) + ' of ' + _n(a['of'], 'earlier payment') + ' late'
            threshold = 'Not set' if t is None else 'A fraction of at most ' + format(t, 'g')
        elif c['name'] == 'requested_days':
            actual = UNKNOWN if a is None else _n(a, 'day')
            threshold = 'Not set (staff may approve nothing)' if t is None else 'Up to ' + _n(t, 'day')
        elif c['name'] == 'outstanding_amount':
            actual = UNKNOWN if unknown else money(a)
            threshold = 'Not set' if t is None else 'Up to ' + money(t)
        else:   # records_complete
            actual, threshold = 'Incomplete', 'Complete records'
        out.append({'key': c['name'], 'name': CHECK_NAMES.get(c['name'], c['name']), 'actual': a, 'actualText': actual, 'threshold': t, 'thresholdText': threshold,
                    'result': 'not set' if not c['applies'] else 'unknown' if unknown else 'pass' if c['passes'] else 'fail',
                    'label': c['label'], 'sentence': c['sentence']})
    return out


def recommend(auth, checks):
    """Only from the policy: a failing check the owner named a hard rule declines by policy; all checks passing with a staff day limit
    set approves within authority; anything else goes to the owner."""
    failing = [c for c in checks if not c['passes']]
    hard = [c for c in failing if c['name'] in auth['hardRules'] and not c.get('unknown')]   # an unknown check never declines
    if hard:
        return {'outcome': 'decline_by_policy', 'reasons': [c['sentence'] for c in hard]}
    if not failing and auth['staffMayApproveUpToDays'] is not None:
        return {'outcome': 'approve_within_authority', 'reasons': [c['sentence'] for c in checks if c['applies']]}
    return {'outcome': 'escalate', 'reasons': [c['sentence'] for c in failing]}


def followed(assessment, outcome):
    """The latest assessment's recommendation as it was when the owner decided, and whether the decision is the outcome it pointed
    to: True or False, or None when there was none or it was to escalate (it pointed to no outcome)."""
    rec = (assessment or {}).get('recommendation')
    return {'recommendation': rec and {'outcome': rec['outcome'], 'reasons': list(rec['reasons'])},
            'followedRecommendation': RECOMMENDS[rec['outcome']] == outcome if rec and rec['outcome'] in RECOMMENDS else None}
