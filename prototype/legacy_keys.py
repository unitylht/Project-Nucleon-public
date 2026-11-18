"""Evidence keys exactly as release a9ce30d computed them, to recognise the keys it stored (docs/EVIDENCE-KEYS.md). Used only by the
startup migration to format 2. Frozen: a change here stops a9ce30d's keys being recognised, and their cases would then be flagged
or prepared again. Checked against a9ce30d's own code on the production copy, the isolated test databases and the backups."""
from datetime import date

from agent import fingerprint

RECORD_KINDS = ('customers', 'invoices', 'notes', 'payments', 'allocations', 'openingBalances', 'coverage')
LATER_FIELDS = ('disputedBy',)                                    # record fields added after a9ce30d
LATER_POSITION_FIELDS = ('notExactCodes', 'conflictCodes', 'checkCodes')


def _day_text(iso):
    d = date.fromisoformat(iso)
    return ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')[d.weekday()] + ' ' + str(d.day) + ' ' + d.strftime('%b %Y')


def _reasons(position):
    """Not-exact reasons as a9ce30d wrote them: its earlier completeness sentence, and no sentence about a broken statement."""
    reasons = []
    for text, (code, values) in zip(position['notExact'], position['notExactCodes']):
        if code == 'completeness_broken':
            continue
        if code == 'no_completeness':
            text = 'Payment records for this customer have no confirmed completeness' + (' from ' + _day_text(values['base']) if values['base'] else '') + '.'
        reasons.append(text)
    return reasons


def _record(record):
    return {k: v for k, v in record.items() if k not in LATER_FIELDS}


def _invoice(invoice):
    invoice, position = _record(invoice), invoice.get('position')
    if position:
        invoice['position'] = {**{k: v for k, v in position.items() if k not in LATER_POSITION_FIELDS}, 'notExact': _reasons(position)}
    return invoice


def _coverage(statement):
    """Contradictions as a9ce30d listed them: the record descriptions only."""
    found = statement.get('contradictedFor')
    return statement if found is None else {**statement, 'contradictedFor': {cid: {kind: [x['record'] for x in items] for kind, items in kinds.items()}
                                                                             for cid, kinds in found.items()}}


def _applies(statement, customer_id):
    return statement['customers'] == 'all' or customer_id in statement['customers']


def decision_key(ev, invoice_id):
    invoice = ev.invoice(invoice_id)
    if invoice is None:
        return None
    cid = invoice['customerId']
    return fingerprint({'customer': ev.customer(cid), 'invoice': _invoice(invoice),
                        'openingBalances': [o for o in ev.fixture.get('openingBalances', []) if o['customerId'] == cid],
                        'coverage': [_coverage(c) for c in ev.fixture.get('coverage', []) if _applies(c, cid)]})


def version(ev, invoice_id):
    f, invoice = ev.fixture, ev.invoice(invoice_id)
    cid = invoice['customerId']
    payments = [_record(p) for p in f.get('payments', []) if p['customerId'] == cid]
    ids = {p['id'] for p in payments}
    return fingerprint({'settings': {k: v for k, v in f.items() if k not in RECORD_KINDS},
                        'customer': ev.customer(cid), 'invoices': [_invoice(i) for i in ev.invoices_for(cid)], 'payments': payments,
                        'allocations': [a for a in f.get('allocations', []) if a['paymentId'] in ids],
                        'openingBalances': [o for o in f.get('openingBalances', []) if o['customerId'] == cid],
                        'coverage': [_coverage(c) for c in f.get('coverage', []) if _applies(c, cid)],
                        'notes': [n for n in f['notes'] if n['scope'] in (cid, 'business')],
                        'invoiceId': invoice_id, 'currentEffectiveDueDate': ev.current_due(invoice)})
