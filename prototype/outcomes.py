"""How an approved decision turned out, read from the ledger and stored as an observation (slice S1a, decision D10). Pure rules, no I/O: App.observe_outcomes
(server.py) gathers the facts of each invoice and these functions name the outcome. delegation.derive_outcome stays the read-time label ("current ledger says");
this vocabulary is finer and is what gets stored, with the basis it rests on.

Vocabulary: on_time | late_paid | partial | open_not_due | open_past_due | written_off | unknown.
- on_time / late_paid: the invoice is paid in full by recorded payments, on or before / after the approved due date.
- partial: some of it is paid, the rest is open, and the due date has passed.
- open_not_due / open_past_due: open (nothing recorded as paid, or paid in part but not yet due) and not yet / already past the due date.
- written_off: the ledger has no write-off marker today, so nothing here ever produces it; it is in the vocabulary for when it does.
- unknown: anything the records cannot establish (no due date, a payment with no received date, conflicting payment records, an invoice closed in the records without
  recorded payments that show when). Unknown is never read as good or as zero.
Compatible with Python 3.9 (no match, no X | Y unions)."""
from datetime import date

OUTCOMES = ('on_time', 'late_paid', 'partial', 'open_not_due', 'open_past_due', 'written_off', 'unknown')
ADVERSE = ('written_off', 'open_past_due', 'partial', 'late_paid')   # worst first: a definite adverse fact outranks unknown when invoices are combined


def invoice_outcome(inv, due, as_of, payments, current):
    """(outcome, basis) for one invoice against its due date, on `as_of` (a date).
    inv: {id, reference, total (minor units or None), open (the records' own view), conflict}. payments: [(receivedDate or None, minor units)], the recorded
    allocations to this invoice. current: as_of is the ledger's own date or later, so the records' open or closed state applies; for an earlier as_of only the
    payments dated on or before it are read."""
    basis = {'invoiceId': inv['id'], 'reference': inv.get('reference'), 'dueDate': due}

    def done(outcome, why, **more):
        basis.update({'outcome': outcome, 'why': why, **more})
        return outcome, basis
    if not due:
        return done('unknown', 'No due date is on record.')
    if inv.get('conflict'):
        return done('unknown', 'The payment records for this invoice conflict.')
    if any(day is None for day, _ in payments):
        return done('unknown', 'A payment allocated to this invoice has no received date.')
    cutoff = as_of.isoformat()
    seen = sorted((day, amount) for day, amount in payments if day <= cutoff)
    paid, total = sum(amount for _, amount in seen), inv.get('total')
    basis['paidMinor'] = paid
    if total and paid >= total:
        running, settled = 0, None
        for day, amount in seen:
            running += amount
            if running >= total:
                settled = day
                break
        return done('on_time' if settled <= due else 'late_paid', 'Paid in full on ' + settled + ('; due ' + due + '.'), settledOn=settled)
    if current and not inv.get('open'):
        return done('unknown', 'The records show the invoice closed, but recorded payments do not show when it was paid.')
    if as_of <= date.fromisoformat(due):
        return done('open_not_due', 'Open, and not yet past the due date.')
    if paid > 0:
        return done('partial', 'Partly paid, the rest open and past the due date.')
    return done('open_past_due', 'Open and past the due date.')


def combine(parts):
    """One outcome for several invoices: on_time only if ALL are on time; otherwise the worst definite adverse fact; otherwise unknown if any is unknown; otherwise
    open_not_due (a mix of on-time and not-yet-due). No invoices at all is unknown."""
    found = [outcome for outcome, _ in parts]
    if not found:
        return 'unknown'
    if all(o == 'on_time' for o in found):
        return 'on_time'
    for adverse in ADVERSE:
        if adverse in found:
            return adverse
    return 'unknown' if 'unknown' in found else 'open_not_due'


def observe_case(kind, params, approved_due, approved_on, invoices, as_of, current):
    """{outcome, basis} for one approved case. invoices: the facts of the invoices that could matter, [{id, reference, issueDate, due, total, open, conflict, payments}].
    An extension: its invoice against the APPROVED due date. Trial credit: every invoice of the customer issued on or after the day it was approved, each against
    its own due date (combine)."""
    if kind == 'extension':
        inv = next((i for i in invoices if i['id'] == params.get('invoiceId')), None)
        if inv is None:
            return {'outcome': 'unknown', 'basis': {'rule': 'extension', 'why': 'The invoice is not in the records.', 'invoices': []}}
        outcome, basis = invoice_outcome(inv, approved_due or inv.get('due'), as_of, inv['payments'], current)
        return {'outcome': outcome, 'basis': {'rule': 'extension: the invoice against the approved due date', 'invoices': [basis]}}
    later = [i for i in invoices if i.get('issueDate') and i['issueDate'] >= (approved_on or '9999-12-31')]
    parts = [invoice_outcome(i, i.get('due'), as_of, i['payments'], current) for i in later]
    why = None if parts else 'No invoice issued after the approval is in the records.'
    return {'outcome': combine(parts), 'basis': {'rule': 'trial credit: every invoice issued on or after the approval, on time only if all are', 'invoices': [b for _, b in parts],
                                                 **({'why': why} if why else {})}}
