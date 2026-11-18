"""Business records: workspace settings, the setup checklist and (later in this file) manual records.

The records document is the existing `fixtures` row: one JSON document per workspace with settings, customers,
invoices and notes. Every function here is deterministic code; no model is involved.
shortcut: one JSON document and whole-document evidence versions; move to tables in stage 3 (P002 section 11.3).
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class RecordsError(Exception):
    def __init__(self, status, code, message, field=None, extra=None):
        super().__init__(message)
        self.status, self.code, self.message, self.field, self.extra = status, code, message, field, extra or {}


def require(condition, status, code, message, field=None, extra=None):
    if not condition:
        raise RecordsError(status, code, message, field, extra)


# ---------------------------------------------------------------- settings and clock

def validate_settings(body):
    currency, scale, timezone, name = body.get('currency'), body.get('scale'), body.get('timezone'), body.get('businessName')
    require(isinstance(currency, str) and re.fullmatch(r'[A-Z]{3}', currency), 400, 'INVALID_INPUT',
            'Enter a three-letter currency code, for example AUD.', 'currency')
    require(type(scale) is int and 0 <= scale <= 3, 400, 'INVALID_INPUT', 'Decimal places must be a whole number from 0 to 3.', 'scale')
    require(isinstance(timezone, str) and valid_timezone(timezone), 400, 'INVALID_INPUT',
            'Enter a time zone name, for example Australia/Sydney.', 'timezone')
    require(name is None or (isinstance(name, str) and len(name.strip()) <= 120), 400, 'INVALID_INPUT',
            'Keep the business name under 120 characters.', 'businessName')
    return {'currency': currency, 'scale': scale, 'timezone': timezone, 'businessName': (name or '').strip() or None}


# The owner's authority settings (the limits staff may act within), stored on the records document as `authority`.
AUTHORITY_DEFAULTS = {'staffMayApproveUpToDays': None, 'maxOutstanding': None, 'requireNothingOverdue': True, 'maxPriorLateShare': None,
                      'hardRules': [], 'maxConcernRounds': 2}
AUTHORITY_CHECKS = ('nothing_overdue', 'late_history', 'requested_days', 'outstanding_amount')   # the assessment's checks: a hard rule names one


def authority_of(doc):
    return {**AUTHORITY_DEFAULTS, **((doc or {}).get('authority') or {})}


def validate_authority(body, settings):
    """The whole authority from a PUT body (a key left out takes its default). Limits are the owner's alone; maxPriorLateShare is a
    fraction from 0 to 1, never a percentage."""
    require(set(body) <= set(AUTHORITY_DEFAULTS), 400, 'INVALID_INPUT', 'Unknown setting.', 'authority')
    got = {**AUTHORITY_DEFAULTS, **body}
    days, rounds, share, hard = got['staffMayApproveUpToDays'], got['maxConcernRounds'], got['maxPriorLateShare'], got['hardRules']
    require(days is None or type(days) is int and 1 <= days <= 365, 400, 'INVALID_INPUT', 'Days staff may approve: a whole number from 1 to 365, or none.', 'staffMayApproveUpToDays')
    require(type(rounds) is int and 1 <= rounds <= 10, 400, 'INVALID_INPUT', 'Concern rounds: a whole number from 1 to 10.', 'maxConcernRounds')
    require(type(got['requireNothingOverdue']) is bool, 400, 'INVALID_INPUT', 'Choose whether nothing may be overdue.', 'requireNothingOverdue')
    require(share is None or type(share) in (int, float) and 0 <= share <= 1, 400, 'INVALID_INPUT',
            'The late share is a fraction from 0 to 1 (for example 0.25), or none.', 'maxPriorLateShare')
    require(isinstance(hard, list) and len(set(hard)) == len(hard) and all(x in AUTHORITY_CHECKS for x in hard), 400, 'INVALID_INPUT',
            'Hard rules are names of checks: ' + ', '.join(AUTHORITY_CHECKS) + '.', 'hardRules')
    limit = got['maxOutstanding']
    if isinstance(limit, dict):   # as the settings are read back
        require(set(limit) == {'minorUnits', 'currency', 'scale'} and limit['currency'] == settings['currency'] and limit['scale'] == settings['scale']
                and isinstance(limit['minorUnits'], str) and limit['minorUnits'].isdigit(), 400, 'INVALID_AMOUNT', 'Enter an amount in the workspace currency.', 'maxOutstanding')
        limit = money_text_plain(limit)
    return {**got, 'maxOutstanding': None if limit is None else parse_money(limit, settings, 'maxOutstanding')}


def valid_timezone(name):
    try:
        ZoneInfo(name)
        return '/' in name or name == 'UTC'
    except (ZoneInfoNotFoundError, ValueError):
        return False


def settings_of(doc):
    """Currency, decimal places and time zone of a records document. The sample predates explicit settings,
    so its settings are read from its own amounts and time zone."""
    if not doc:
        return None
    if 'currency' in doc:
        return {'currency': doc['currency'], 'scale': doc['scale'], 'timezone': doc['businessTimezone'], 'businessName': doc.get('businessName')}
    amount = next((i['outstandingAmount'] for i in doc['invoices'] if i.get('outstandingAmount')), None)
    return {'currency': amount and amount['currency'], 'scale': amount and amount['scale'], 'timezone': doc['businessTimezone'],
            'businessName': doc.get('businessName')}


def empty_document(settings, practice):
    return {'dataMode': 'fictional' if practice else 'real', 'version': 0, 'businessTimezone': settings['timezone'],
            'currency': settings['currency'], 'scale': settings['scale'], 'businessName': settings['businessName'],
            'customers': [], 'invoices': [], 'notes': []}


def today_for(doc, clock=None):
    """'Today' for calculations: the sample's fixed demo date, otherwise today in the business's time zone."""
    if doc.get('asOfDate'):
        return date.fromisoformat(doc['asOfDate'])
    return clock() if clock else datetime.now(ZoneInfo(doc['businessTimezone'])).date()


# ---------------------------------------------------------------- record state

def active(record):
    return record.get('status', 'active') == 'active'


def is_open(invoice):
    """Open unless a stated amount still owed is zero. 'Not recorded' counts as open."""
    amount = invoice.get('outstandingAmount')
    return amount is None or int(amount['minorUnits']) > 0


def active_view(doc, positions=True):
    """What the agent and the evidence see: active records only. Invoices that recorded payments are allocated to carry
    their settlement 'position' (Stage 3); payments and allocations appear only when there are any. positions=False skips the
    positions, for callers that only count or list records (the setup checklist)."""
    customers = [c for c in doc['customers'] if active(c)]
    ids = {c['id'] for c in customers}
    invoices = [i for i in doc['invoices'] if active(i) and i['customerId'] in ids]
    view = {**doc, 'customers': customers, 'invoices': invoices, 'notes': [n for n in doc['notes'] if n.get('status') in ('confirmed', 'draft')]}
    payments = [p for p in doc.get('payments', []) if active(p) and p['customerId'] in ids]
    paid_ids, invoice_ids = {p['id'] for p in payments}, {i['id'] for i in invoices}
    allocations = [a for a in doc.get('allocations', []) if active(a) and a['paymentId'] in paid_ids and a['invoiceId'] in invoice_ids]
    openings = [o for o in doc.get('openingBalances', []) if active(o) and o['customerId'] in ids]
    # Contradictions need the records that have left a confirmed period too, which this view no longer holds: work them out here.
    everything = split_by_customer(doc)
    coverage = [{**c, 'contradictedFor': {cid: {kind: contradictions(everything[cid], c, cid, kind) for kind in c['recordTypes']}
                                          for cid in (ids if c['customers'] == 'all' else ids & set(c['customers']))}}
                for c in doc.get('coverage', []) if active(c)]
    for kind, records in (('payments', payments), ('allocations', allocations), ('openingBalances', openings), ('coverage', coverage)):
        view.pop(kind, None)
        if records:
            view[kind] = records
    if positions:
        parts = split_by_customer(view)
        view['invoices'] = [{**i, 'position': position} if (position := invoice_position(parts[i['customerId']], i)) else i for i in invoices]
    return view


RECORD_KINDS = ('customers', 'invoices', 'notes', 'payments', 'allocations', 'openingBalances', 'coverage')


def split_by_customer(doc):
    """The document split into one document per customer: the workspace settings, and that customer's invoices, payments,
    allocations, opening balance and the completeness statements that apply to them, in every status. Every per-customer
    calculation gives the same result on its part as on the whole document, while scanning only that customer's records."""
    settings = {k: v for k, v in doc.items() if k not in RECORD_KINDS}
    parts = {c['id']: {**settings, 'customers': [c], 'notes': [], 'invoices': [], 'payments': [], 'allocations': [], 'openingBalances': [], 'coverage': []}
             for c in doc['customers']}
    owner = {p['id']: p['customerId'] for p in doc.get('payments', [])}
    for kind in ('invoices', 'payments', 'openingBalances'):
        for record in doc.get(kind, []):
            if record['customerId'] in parts:
                parts[record['customerId']][kind].append(record)
    for allocation in doc.get('allocations', []):
        if owner.get(allocation['paymentId']) in parts:
            parts[owner[allocation['paymentId']]]['allocations'].append(allocation)
    for statement in doc.get('coverage', []):
        for cid in (parts if statement['customers'] == 'all' else [c for c in statement['customers'] if c in parts]):
            parts[cid]['coverage'].append(statement)
    return parts


# ---------------------------------------------------------------- setup checklist (Slice 2 scope)

NOT_NEEDED = 'Credit limits, scores or ratings, contact details and full customer history are not needed for payment extensions.'
NOT_YET = ('Not in this version: payment terms used in calculations and credit-note documents (record a credit held for the customer instead).')


def checklist(workspace, doc):
    """Required, recommended and good-to-have items, computed from the data and the saved skips."""
    skips = (workspace or {}).get('skips', {})
    view = active_view(doc, positions=False) if doc else None   # counts only: what the records state, without payment positions
    open_invoices = [i for i in view['invoices'] if is_open(i)] if view else []

    def item(key, tier, label, done, detail, partly=False):
        status = 'done' if done else 'skipped' if key in skips else 'partly' if partly else 'todo'
        return {'id': key, 'tier': tier, 'label': label, 'status': status, 'detail': detail}
    with_due = [i for i in open_invoices if i.get('originalDueDate')]
    stated = [i for i in open_invoices if i.get('outstandingAmount')]
    confirmed = [n for n in (view['notes'] if view else []) if n.get('status') == 'confirmed']
    items = [
        item('workspace', 'required', 'Workspace type: real or practice', workspace is not None,
             'Practice data is fictional; a real workspace never loads the sample.'),
        item('settings', 'required', 'Currency, decimal places and time zone', bool(doc and settings_of(doc)['currency']),
             'Needed to read amounts and dates safely.'),
        item('invoice', 'required', 'At least one customer with an open invoice', bool(open_invoices),
             str(len(view['customers']) if view else 0) + ' customers, ' + str(len(open_invoices)) + ' open invoices. '
             'A case needs the invoice it is about.'),
        item('dueDates', 'recommended', 'Due dates on open invoices', bool(open_invoices) and len(with_due) == len(open_invoices),
             str(len(with_due)) + ' of ' + str(len(open_invoices)) + ' open invoices have a due date. Without one, a case shows the due '
             'date as not on record. Payment terms can be written as a note for now; they are not used in calculations yet.',
             partly=bool(with_due)),
        item('stillOwed', 'recommended', 'Amount still owed, with the date it was stated', bool(open_invoices) and len(stated) == len(open_invoices),
             str(len(stated)) + ' of ' + str(len(open_invoices)) + ' open invoices have one. Without it, a case shows the amount owed '
             'as not recorded.', partly=bool(stated)),
        item('knowledge', 'good', 'What you already know about customers or the business', bool(confirmed),
             str(len(confirmed)) + ' confirmed notes. Optional; you can add notes at any time.'),
    ]
    ready = all(i['status'] == 'done' for i in items if i['tier'] == 'required')
    return {'items': items, 'ready': ready, 'notNeeded': NOT_NEEDED, 'notYet': NOT_YET}


# ---------------------------------------------------------------- values typed in or imported

def ref_key(reference):
    """Invoice numbers compare without case or spaces (the same rule as agent.ref_key)."""
    return re.sub(r'\s+', '', str(reference or '')).upper()


def name_key(name):
    """Customer names compare without case, accents or punctuation: 'Bayside Café' and 'bayside cafe' are the same name."""
    # 'đ' has no decomposition: without this, 'Số hóa đơn' would never match the synonym 'so hoa don'
    folded = ''.join(ch for ch in unicodedata.normalize('NFKD', str(name or '').casefold().replace('đ', 'd')) if not unicodedata.combining(ch))
    return re.sub(r'[^0-9a-z]+', ' ', folded).strip()


def parse_money(value, settings, field):
    """Text such as '1,200.50' to integer minor units at the workspace's decimal places. Never a float."""
    text = value.strip() if isinstance(value, str) else ''
    scale = settings['scale']
    match = re.fullmatch(r'(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?', text)
    require(match, 400, 'INVALID_AMOUNT', 'Enter an amount using digits, for example 1200.50.', field)
    whole, part = match.group(1).replace(',', ''), match.group(2) or ''
    require(len(part) <= scale, 400, 'INVALID_AMOUNT', 'Use at most ' + str(scale) + ' decimal places.', field)
    minor = int(whole) * 10 ** scale + int((part + '0' * scale)[:scale] or 0)
    return {'minorUnits': str(minor), 'currency': settings['currency'], 'scale': scale}


def parse_day(value, field):
    try:
        require(isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value.strip()), 400, 'INVALID_DATE', '', field)
        return date.fromisoformat(value.strip()).isoformat()
    except (ValueError, RecordsError):
        raise RecordsError(400, 'INVALID_DATE', 'Enter a date as YYYY-MM-DD.', field)


def text_value(value, field, limit, label):
    require(isinstance(value, str) and value.strip() and len(value.strip()) <= limit and not re.search(r'[\x00-\x1f]', value.strip()),
            400, 'INVALID_INPUT', 'Enter ' + label + ' (up to ' + str(limit) + ' characters).', field)
    return value.strip()


# ---------------------------------------------------------------- customers and invoices

def find(doc, kind, record_id):
    record = next((r for r in doc[kind] if r['id'] == record_id), None)
    require(record is not None, 404, 'NOT_FOUND', 'That record does not exist.')
    return record


def origin_of(record):
    return record.get('origin') or {'kind': 'sample'}


def customer_fields(doc, body, current=None):
    name = text_value(body.get('name'), 'name', 120, 'the customer name')
    clash = next((c for c in doc['customers'] if active(c) and c is not current and name_key(c['name']) == name_key(name)), None)
    require(clash is None, 409, 'DUPLICATE_CUSTOMER', 'A customer with this name already exists (' + (clash or {}).get('displayCode', '') + ').', 'name')
    return {'name': name}


def new_customer(doc, body, record_id, origin):
    """origin: {kind: manual|file, by, at, batchId?, sourceLabel?, row?}"""
    fields = customer_fields(doc, body)
    used, number, display_code = {c['displayCode'] for c in doc['customers']}, len(doc['customers']) + 1, None
    while display_code is None or display_code in used:
        display_code, number = 'C-' + str(number).zfill(4), number + 1
    customer = {'id': record_id, 'displayCode': display_code, **fields, 'status': 'active', 'version': 1,
                'origin': origin, 'setBy': origin, 'history': []}
    doc['customers'].append(customer)
    return customer


def invoice_fields(doc, body, settings, today, customer_id, current=None):
    """Validated invoice values. A stated amount still owed always carries the date it was stated."""
    reference = current['reference'] if current else text_value(body.get('reference'), 'reference', 40, 'the invoice number')
    if not current:
        clash = next((i for i in doc['invoices'] if active(i) and i['customerId'] == customer_id and ref_key(i['reference']) == ref_key(reference)), None)
        require(clash is None, 409, 'DUPLICATE_INVOICE', 'This customer already has invoice ' + reference + '.', 'reference')
    issue = parse_day(body.get('issueDate'), 'issueDate')
    total = parse_money(body.get('total'), settings, 'total')
    require(int(total['minorUnits']) > 0, 400, 'INVALID_AMOUNT', 'The invoice amount must be more than zero.', 'total')
    due = parse_day(body['dueDate'], 'dueDate') if body.get('dueDate') else None
    require(due is None or due >= issue, 400, 'INVALID_DATE', 'The due date cannot be before the invoice date.', 'dueDate')
    owed, owed_as_of = None, None
    if body.get('stillOwed') not in (None, ''):
        owed = parse_money(body['stillOwed'], settings, 'stillOwed')
        require(int(owed['minorUnits']) <= int(total['minorUnits']), 400, 'INVALID_AMOUNT', 'The amount still owed cannot be more than the invoice amount.', 'stillOwed')
        require(body.get('stillOwedAsOf'), 400, 'INVALID_DATE', 'Say on which date this amount was still owed.', 'stillOwedAsOf')
        owed_as_of = parse_day(body['stillOwedAsOf'], 'stillOwedAsOf')
        require(issue <= owed_as_of <= today.isoformat(), 400, 'INVALID_DATE', 'Use a date from the invoice date up to today.', 'stillOwedAsOf')
    return {'reference': reference, 'issueDate': issue, 'total': total, 'originalDueDate': due, 'outstandingAmount': owed,
            'outstandingAsOf': owed_as_of}


def new_invoice(doc, body, settings, today, record_id, origin):
    customer = next((c for c in doc['customers'] if c['id'] == body.get('customerId')), None)
    require(customer is not None and active(customer), 400, 'INVALID_INPUT', 'Choose an existing customer.', 'customerId')
    fields = invoice_fields(doc, body, settings, today, customer['id'])
    invoice = {'id': record_id, 'customerId': customer['id'], **fields,
               'outstandingSource': origin['kind'] if fields['outstandingAmount'] else None,
               'status': 'active', 'version': 1, 'origin': origin, 'setBy': origin, 'history': []}
    entry_inclusion(doc, invoice, body, origin)
    doc['invoices'].append(invoice)
    return invoice


CORRECTABLE = {'customers': ('name',), 'invoices': ('issueDate', 'total', 'originalDueDate', 'outstandingAmount', 'outstandingAsOf', 'outstandingSource'),
               'payments': ('receivedDate', 'amount', 'reference'), 'openingBalances': ('asOf', 'amount', 'credits', 'sourceLabel')}


def annotate(record, field, value, set_by):
    """A person's answer about a record (not a value of it): kept with its own history, without a new record version, so it never
    blocks reverting the import the record came from. Reverts list the answers they make moot."""
    record['answers'] = record.get('answers', []) + [{'field': field, 'value': value, 'previous': record.get(field), 'by': set_by['by'],
                                                       'role': set_by.get('role'), 'at': set_by['at']}]
    record[field] = value


def set_version(record, kind, values, set_by):
    """Replace the current values with a new version; the previous values stay in the record's history."""
    previous = {k: record.get(k) for k in CORRECTABLE[kind]}
    record['history'] = record.get('history', []) + [{'version': record.get('version', 1), 'values': previous, 'setBy': record.get('setBy') or origin_of(record),
                                                      'replacedAt': set_by['at'], 'replacedBy': set_by}]
    record.update(values)
    record['version'] = record.get('version', 1) + 1
    record['setBy'] = set_by


def correct(doc, kind, record_id, body, settings, today, set_by):
    record = find(doc, kind, record_id)
    require(active(record), 409, 'INACTIVE', 'A removed or reverted record cannot be corrected.')
    if kind == 'customers':
        values = customer_fields(doc, body, current=record)
    elif kind == 'payments':
        values = correct_payment(doc, record, body, settings, today)
    elif kind == 'openingBalances':
        merged = {'asOf': record['asOf'], 'amount': money_text_plain(amount_of(record['amount'], abs(minor(record['amount'])))),
                  'direction': 'credit' if minor(record['amount']) < 0 else 'owed', 'credits': credits_of(record),
                  'sourceLabel': record['sourceLabel'], **{k: body[k] for k in ('asOf', 'amount', 'direction', 'credits', 'sourceLabel') if k in body}}
        values = opening_fields(merged, settings, today)
    else:
        merged = {'issueDate': record.get('issueDate'), 'total': money_text_plain(record.get('total')), 'dueDate': record.get('originalDueDate'),
                  'stillOwed': money_text_plain(record.get('outstandingAmount')), 'stillOwedAsOf': record.get('outstandingAsOf'),
                  **{k: body[k] for k in ('issueDate', 'total', 'dueDate', 'stillOwed', 'stillOwedAsOf') if k in body}}
        fields = invoice_fields(doc, merged, settings, today, record['customerId'], current=record)
        values = {k: fields[k] for k in ('issueDate', 'total', 'originalDueDate', 'outstandingAmount', 'outstandingAsOf')}
        same_owed = (values['outstandingAmount'], values['outstandingAsOf']) == (record.get('outstandingAmount'), record.get('outstandingAsOf'))
        values['outstandingSource'] = record.get('outstandingSource') if same_owed else ('correction' if values['outstandingAmount'] else None)
        require(minor(values['total']) >= allocated_to(doc, record['id']), 409, 'ALLOCATED', 'More than that is already allocated to this '
                'invoice from payments. Remove allocations first.', 'total')
    changed = {k: v for k, v in values.items() if record.get(k) != v}
    require(changed, 400, 'NO_CHANGE', 'Nothing is different from the current values.')
    set_version(record, kind, values, set_by)
    return record


def money_text_plain(amount):
    if not amount:
        return None
    minor, scale = int(amount['minorUnits']), int(amount['scale'])
    whole, part = divmod(minor, 10 ** scale)
    return str(whole) + ('.' + str(part).zfill(scale) if scale else '')


def reason_value(body):
    return text_value(body.get('reason'), 'reason', 300, 'a short reason')


# ---------------------------------------------------------------- what the owner already knows (notes)

def new_note(doc, body, actor, at, note_id):
    text = text_value(body.get('text'), 'text', 1000, 'the note')
    kind = body.get('kind', 'context')
    require(kind in ('context', 'rule'), 400, 'INVALID_INPUT', 'Choose context or rule.', 'kind')
    scope = body.get('scope')
    require(isinstance(scope, str) and scope, 400, 'INVALID_INPUT', 'Choose the whole business or one customer.', 'scope')
    if scope != 'business':
        customer = next((c for c in doc['customers'] if c['id'] == scope and active(c)), None)
        require(customer is not None, 400, 'INVALID_INPUT', 'Choose an existing customer, or the whole business.', 'scope')
    confirm = body.get('confirm') is True
    require(not (confirm and actor['role'] != 'owner'), 403, 'FORBIDDEN', 'Only the owner can confirm a note. Staff notes are drafts.')
    note = {'id': note_id, 'version': 1, 'status': 'confirmed' if confirm else 'draft', 'origin': actor['role'], 'kind': kind, 'text': text,
            'scope': scope, 'createdBy': actor['id'], 'createdAt': at, 'history': []}
    if confirm:
        note.update({'confirmedBy': actor['id'], 'confirmedAt': at})
    doc['notes'].append(note)
    return note


def note_action(doc, note_id, action, body, actor, at):
    note = find(doc, 'notes', note_id)
    require(note.get('status') in ('draft', 'confirmed'), 409, 'INACTIVE', 'This note has been retired.')
    owner = actor['role'] == 'owner'
    if action == 'confirm':
        require(owner, 403, 'FORBIDDEN', 'Only the owner can confirm a note.')
        require(note['status'] == 'draft', 409, 'ALREADY_CONFIRMED', 'This note is already confirmed.')
        note.update({'status': 'confirmed', 'confirmedBy': actor['id'], 'confirmedAt': at})
    elif action == 'retire':
        require(owner or note['status'] == 'draft', 403, 'FORBIDDEN', 'Only the owner can retire a confirmed note.')
        note.update({'status': 'retired', 'retiredBy': actor['id'], 'retiredAt': at, 'retiredReason': reason_value(body)})
    else:
        require(owner or note['status'] == 'draft', 403, 'FORBIDDEN', 'Only the owner can change a confirmed note.')
        text = text_value(body.get('text'), 'text', 1000, 'the note')
        require(text != note['text'], 400, 'NO_CHANGE', 'Nothing is different from the current text.')
        note['history'] = note.get('history', []) + [{'version': note['version'], 'text': note['text'], 'replacedAt': at, 'replacedBy': actor['id'],
                                                      'reason': reason_value(body)}]
        note.update({'text': text, 'version': note['version'] + 1})
    return note


# ---------------------------------------------------------------- payments and explicit allocations (Stage 3)

def minor(amount):
    return int(amount['minorUnits']) if amount else 0


def amount_of(template, units):
    return {'minorUnits': str(units), 'currency': template['currency'], 'scale': template['scale']}


def payment_fields(body, settings, today):
    received = parse_day(body.get('receivedDate'), 'receivedDate')
    require(received <= today.isoformat(), 400, 'INVALID_DATE', "A payment can't be dated after today.", 'receivedDate')
    amount = parse_money(body.get('amount'), settings, 'amount')
    require(minor(amount) > 0, 400, 'INVALID_AMOUNT', 'The payment amount must be more than zero.', 'amount')
    reference = body.get('reference')
    reference = text_value(reference, 'reference', 60, 'the payment reference') if reference not in (None, '') else None
    kind = body.get('kind') or 'payment'
    require(kind in ('payment', 'credit'), 400, 'INVALID_INPUT', 'Choose money received, or a credit held for the customer.', 'kind')
    return {'receivedDate': received, 'amount': amount, 'reference': reference, 'kind': kind}


def possible_duplicate(doc, customer_id, fields, exclude=None):
    """An active payment of this customer that looks like the same money: the same reference, or (without a reference)
    the same date and amount. A person decides; nothing is merged or skipped automatically."""
    for p in doc.get('payments', []):
        if not active(p) or p['customerId'] != customer_id or p['id'] == exclude:
            continue
        if fields['reference'] and p.get('reference') and ref_key(p['reference']) == ref_key(fields['reference']):
            return p
        if not fields['reference'] and p['receivedDate'] == fields['receivedDate'] and p['amount'] == fields['amount']:
            return p
    return None


def duplicate_error(found, fields):
    return RecordsError(409, 'POSSIBLE_DUPLICATE', 'A payment like this is already recorded (' + found['receivedDate'] + ', ' +
                        found['amount']['currency'] + ' ' + money_text_plain(found['amount']) + (', ' + found['reference'] if found.get('reference') else '') +
                        '). Record it again only if it is a different payment.', 'reference' if fields['reference'] else 'amount',
                        extra={'existing': found['id']})


def new_payment(doc, body, settings, today, record_id, origin):
    customer = next((c for c in doc['customers'] if c['id'] == body.get('customerId') and active(c)), None)
    require(customer is not None, 400, 'INVALID_INPUT', 'Choose an existing customer.', 'customerId')
    fields = payment_fields(body, settings, today)
    found = possible_duplicate(doc, customer['id'], fields)
    if found and body.get('confirmDistinct') is not True:
        raise duplicate_error(found, fields)
    payment = {'id': record_id, 'customerId': customer['id'], **fields, 'status': 'active', 'version': 1, 'origin': origin, 'setBy': origin, 'history': []}
    entry_inclusion(doc, payment, body, origin)
    doc.setdefault('payments', []).append(payment)
    return payment


def allocated_from(doc, payment_id):
    return sum(minor(a['amount']) for a in doc.get('allocations', []) if active(a) and a['paymentId'] == payment_id)


def allocated_to(doc, invoice_id):
    return sum(minor(a['amount']) for a in doc.get('allocations', []) if active(a) and a['invoiceId'] == invoice_id)


def statement_of(doc, invoice):
    """(amount stated still owed in minor units, the date it was stated) or None. The sample's figure is stated as of the sample's
    own date. A statement as of D may already reflect payments made on or before D, so those are never simply subtracted again."""
    if invoice.get('outstandingAmount') is None:
        return None
    return minor(invoice['outstandingAmount']), invoice.get('outstandingAsOf') or doc.get('asOfDate')


def allocations_to(doc, invoice):
    payments = {p['id']: p for p in doc.get('payments', [])}
    return [(a, payments[a['paymentId']]) for a in doc.get('allocations', []) if active(a) and a['invoiceId'] == invoice['id']]


def statement_answer(allocation, statement):
    """A person's answer to "did the amount stated already reflect this payment?", if it was given about this statement."""
    answer = allocation.get('statementInclusion')
    if answer and statement and (answer['asOf'], answer['stated']) == (statement[1], str(statement[0])):
        return answer['status']
    return None


def allocation_room(doc, invoice, received, planned=()):
    """How much more may be allocated to an invoice from a payment received on this date: never more than its amount, and from a
    payment after a statement of what was still owed, never more than that statement leaves. planned: unsaved [(minor, date)].
    None when the invoice has no amount at all."""
    rows = allocations_to(doc, invoice)
    total = minor(invoice['total']) if invoice.get('total') else None
    allocated = sum(minor(a['amount']) for a, _ in rows) + sum(n for n, _ in planned)
    rooms, statement = ([] if total is None else [total - allocated]), statement_of(doc, invoice)
    if statement:
        stated, on = statement
        if on and received > on:
            later = sum(minor(a['amount']) for a, p in rows if p['receivedDate'] > on) + sum(n for n, d in planned if d > on)
            missed = sum(minor(a['amount']) for a, _ in rows if statement_answer(a, statement) == 'missed')
            rooms.append(stated - later - missed)
        elif total is None:   # the sample stores no invoice amount, only the stated figure
            rooms.append(stated - allocated)
    return max(0, min(rooms)) if rooms else None


def allocate(doc, body, settings, new_id, origin):
    """Allocate one payment to one or more invoices of the same customer, explicitly. All or nothing."""
    payment = find(doc, 'payments', body.get('paymentId'))
    require(active(payment), 409, 'INACTIVE', 'This payment has been removed or reverted.', 'paymentId')
    items = body.get('allocations')
    require(isinstance(items, list) and 1 <= len(items) <= 20, 400, 'INVALID_INPUT', 'Choose at least one invoice and an amount.', 'allocations')
    planned, seen, created = {}, set(), []
    for item in items:
        invoice = next((i for i in doc['invoices'] if i['id'] == (item or {}).get('invoiceId') and active(i)), None)
        require(invoice is not None, 400, 'INVALID_INPUT', 'Choose an existing invoice.', 'invoiceId')
        require(invoice['customerId'] == payment['customerId'], 400, 'OTHER_CUSTOMER',
                'A payment can only be allocated to invoices of the same customer.', 'invoiceId')
        require(invoice['id'] not in seen, 400, 'INVALID_INPUT', 'Each invoice once per allocation.', 'invoiceId')
        seen.add(invoice['id'])
        amount = parse_money(item.get('amount'), settings, 'amount')
        require(minor(amount) > 0, 400, 'INVALID_AMOUNT', 'The amount must be more than zero.', 'amount')
        left = allocation_room(doc, invoice, payment['receivedDate'])
        require(left is not None, 409, 'NO_AMOUNT', 'Invoice ' + invoice['reference'] + ' has no amount recorded. Add its amount first.', 'invoiceId')
        on = (statement_of(doc, invoice) or (None, None))[1]
        require(minor(amount) <= left, 422, 'OVER_INVOICE', 'Only ' + money_text_plain(amount_of(amount, left)) + ' is left to allocate on invoice ' +
                invoice['reference'] + (' from a payment after ' + on + ', when its amount still owed was stated' if on and payment['receivedDate'] > on else '') + '.',
                'amount')
        planned[invoice['id']] = amount
    unallocated = minor(payment['amount']) - allocated_from(doc, payment['id'])
    require(sum(minor(a) for a in planned.values()) <= unallocated, 422, 'OVER_PAYMENT', 'Only ' +
            money_text_plain(amount_of(payment['amount'], unallocated)) + ' of this payment is unallocated.', 'amount')
    for invoice_id, amount in planned.items():
        created.append({'id': new_id('allocation'), 'paymentId': payment['id'], 'invoiceId': invoice_id, 'customerId': payment['customerId'],
                        'amount': amount, 'status': 'active', 'version': 1, 'origin': origin, 'setBy': origin, 'history': []})
    doc.setdefault('allocations', []).extend(created)
    return created


def correct_payment(doc, payment, body, settings, today):
    merged = {'receivedDate': payment['receivedDate'], 'amount': money_text_plain(payment['amount']), 'reference': payment.get('reference'),
              **{k: body[k] for k in ('receivedDate', 'amount', 'reference') if k in body}, 'kind': payment.get('kind', 'payment')}
    fields = payment_fields(merged, settings, today)
    require(minor(fields['amount']) >= allocated_from(doc, payment['id']), 409, 'ALLOCATED', 'More than that is already allocated from this '
            'payment. Remove allocations first.', 'amount')
    found = possible_duplicate(doc, payment['customerId'], fields, exclude=payment['id'])
    if found and body.get('confirmDistinct') is not True:
        raise duplicate_error(found, fields)
    return fields


# ---------------------------------------------------------------- what the records support about settlement

def allocation_position(doc, invoice):
    """What payments allocated to one invoice support about it (positive evidence only), or None without allocations.

    With a statement "X still owed as of D": payments after D come off X. Whether X already reflects payments on or before D is
    a person's answer, or unresolved; unresolved ones are not taken off (the bound stays an upper bound). When the invoice amount
    minus them is exactly X they 'reconcile': a suggestion for a person to confirm, never an answer, because an unrecorded credit
    and a payment that was not reflected reconcile just as well. Evidence that contradicts itself is a conflict, which never
    settles the invoice."""
    rows = allocations_to(doc, invoice)
    if not rows:
        return None
    template = invoice.get('total') or invoice['outstandingAmount']
    total = minor(invoice['total']) if invoice.get('total') else None
    amount = {a['id']: minor(a['amount']) for a, _ in rows}
    allocated, statement = sum(amount.values()), statement_of(doc, invoice)
    inclusion = {'basis': None, 'included': [], 'missed': [], 'unresolved': [], 'reconciles': [], 'stale': 0}
    conflicts, checks, conflict_codes, check_codes = [], [], [], []   # the codes say what the sentences say, for evidence keys
    if statement:
        stated, on = statement
        before = [a for a, p in rows if not on or p['receivedDate'] <= on]
        later = sum(amount[a['id']] for a, p in rows if on and p['receivedDate'] > on)
        answers = {a['id']: statement_answer(a, statement) for a in before}
        inclusion['stale'] = sum(1 for a in before if a.get('statementInclusion') and not answers[a['id']])
        before_sum = sum(amount[a['id']] for a in before)
        if before and not any(answers.values()) and total is not None and total - before_sum == stated:
            inclusion['reconciles'] = [a['id'] for a in before]   # a suggestion: offsetting omissions reconcile just as well
        for a in before:
            inclusion[answers[a['id']] or 'unresolved'].append(a['id'])
        inclusion['basis'] = 'answered' if any(answers.values()) else None
        missed = sum(amount[i] for i in inclusion['missed'])
        included = sum(amount[i] for i in inclusion['included'])
        by_statement = stated - later - missed
        if total is not None and stated > total - included:
            conflicts.append('The amount stated as of ' + on + ' is more than the invoice amount minus the payments said to be reflected in it.')
            conflict_codes.append(['stated_above_total_less_reflected', {'on': on}])
        if by_statement < 0:
            conflicts.append('Payments taken off the amount stated as of ' + on + ' add up to more than it.')
            conflict_codes.append(['taken_off_above_stated', {'on': on}])
        if inclusion['unresolved'] and total is not None and stated > total - before_sum:
            checks.append('If the payments on or before ' + on + ' were reflected in the amount stated then, it could not be that high, '
                          'so either they were not reflected, or a record is wrong.')
            check_codes.append(['stated_too_high_if_reflected', {'on': on}])
        within = by_statement if total is None else min(by_statement, total - allocated)
        bound = (by_statement if total is None else max(by_statement, total - allocated)) if conflicts else within
        counted, basis = later + missed, 'stated' if invoice.get('outstandingAsOf') else 'sample'
    else:
        stated, on, counted, basis, bound = None, None, allocated, 'total', total - allocated
    status = 'conflict' if conflicts else 'settled' if bound <= 0 else 'open'
    return {'status': status, 'basis': basis, 'statedAsOf': on, 'stated': amount_of(template, stated) if statement else None,
            'allocated': amount_of(template, allocated), 'counted': amount_of(template, counted), 'atMost': amount_of(template, max(0, bound)),
            'excess': amount_of(template, -bound) if bound < 0 and not conflicts else None, 'inclusion': inclusion, 'conflicts': conflicts,
            'checks': checks, 'conflictCodes': conflict_codes, 'checkCodes': check_codes}


def answer_statement(doc, allocation_id, body, set_by):
    """Record whether the amount stated still owed on the invoice already reflected a payment made on or before its date.
    'unsure' clears the answer. The answer belongs to that statement: once the statement changes, it no longer applies."""
    allocation = find(doc, 'allocations', allocation_id)
    require(active(allocation), 409, 'INACTIVE', 'This allocation has been removed or reverted.')
    status = body.get('status')
    require(status in ('included', 'missed', 'unsure'), 400, 'INVALID_INPUT', 'Choose yes, no or not sure.', 'status')
    invoice, payment = find(doc, 'invoices', allocation['invoiceId']), find(doc, 'payments', allocation['paymentId'])
    statement = statement_of(doc, invoice)
    require(statement and (not statement[1] or payment['receivedDate'] <= statement[1]), 409, 'NOT_APPLICABLE',
            'This payment is after the date the amount still owed was stated, so it simply comes off that amount.')
    value = None if status == 'unsure' else {'status': status, 'asOf': statement[1], 'stated': str(statement[0]), 'by': set_by['by'],
                                              'role': set_by.get('role'), 'at': set_by['at']}
    require((value or {}).get('status') != statement_answer(allocation, statement), 400, 'NO_CHANGE', 'That is already the answer.')
    annotate(allocation, 'statementInclusion', value, set_by)
    return allocation


def customer_position(doc, customer_id, settings):
    """What the records hold for one customer: totals of recorded invoices and payments, and money not allocated. The
    recorded net is a difference of records, not a statement of what is owed: records may be incomplete."""
    invoices = [i for i in doc['invoices'] if active(i) and i['customerId'] == customer_id]
    payments = [p for p in doc.get('payments', []) if active(p) and p['customerId'] == customer_id]
    ids = {p['id'] for p in payments}
    invoiced = sum(minor(i['total']) for i in invoices if i.get('total'))
    missing = sum(1 for i in invoices if not i.get('total'))
    paid = sum(minor(p['amount']) for p in payments)
    allocated = sum(minor(a['amount']) for a in doc.get('allocations', []) if active(a) and a['paymentId'] in ids)
    marked = sum(minor(p['amount']) - allocated_from(doc, p['id']) for p in payments if p.get('notForOpenInvoices'))
    template = {'currency': settings['currency'], 'scale': settings['scale']}
    return {'invoicesRecorded': amount_of(template, invoiced), 'invoicesWithoutAmount': missing, 'paymentsRecorded': amount_of(template, paid),
            'allocated': amount_of(template, allocated), 'unallocated': amount_of(template, paid - allocated),
            'markedUnrelated': amount_of(template, marked), 'unallocatedOpen': amount_of(template, paid - allocated - marked),
            'recordedNet': amount_of(template, invoiced - paid) if not missing else None, 'payments': len(payments)}


# ---------------------------------------------------------------- opening balances and inclusion (Stage 3, P002 section 8.1)

def opening_fields(body, settings, today):
    """An opening balance: what the customer owed (or held in credit) as at a date, and where the figure comes from."""
    on = parse_day(body.get('asOf'), 'asOf')
    require(on <= today.isoformat(), 400, 'INVALID_DATE', 'The as-at date cannot be after today.', 'asOf')
    direction = body.get('direction') or 'owed'
    require(direction in ('owed', 'credit'), 400, 'INVALID_INPUT', 'Choose owed by the customer, or held in credit for them.', 'direction')
    amount = parse_money(body.get('amount'), settings, 'amount')
    credits = body.get('credits') or None
    require(credits in (None, 'none', 'recorded'), 400, 'INVALID_INPUT', 'Say whether it includes credits, or leave it as not stated.', 'credits')
    require(not (credits == 'none' and direction == 'credit' and minor(amount)), 400, 'INVALID_INPUT', 'A balance held in credit is a credit. Record it as '
            'a credit dated on or before the as-at date, then say every credit in it is recorded.', 'credits')
    source = text_value(body.get('sourceLabel'), 'sourceLabel', 80, 'where this figure comes from')
    signed = amount if direction == 'owed' else amount_of(amount, -minor(amount))
    return {'asOf': on, 'amount': signed, 'credits': credits, 'sourceLabel': source}


def credits_of(opening):
    """What a person said about credits in an opening balance: 'none', 'recorded' (every credit in it is recorded here as a payment or
    credit dated on or before its as-at date), or None (not stated). Records from before this field read 'no credits' as 'none'."""
    if 'credits' in opening:
        return opening['credits']
    return 'none' if opening.get('noCredits') is True else None


def new_opening(doc, body, settings, today, record_id, origin):
    customer = next((c for c in doc['customers'] if c['id'] == body.get('customerId') and active(c)), None)
    require(customer is not None, 400, 'INVALID_INPUT', 'Choose an existing customer.', 'customerId')
    require(opening_of(doc, customer['id']) is None, 409, 'OPENING_EXISTS', 'This customer already has an opening balance. Correct it instead.')
    opening = {'id': record_id, 'customerId': customer['id'], **opening_fields(body, settings, today), 'status': 'active', 'version': 1,
               'origin': origin, 'setBy': origin, 'history': []}
    doc.setdefault('openingBalances', []).append(opening)
    return opening


def opening_of(doc, customer_id):
    return next((o for o in doc.get('openingBalances', []) if active(o) and o['customerId'] == customer_id), None)


def record_date(record):
    return record.get('issueDate') or record.get('receivedDate')


def inclusion_answer(record, opening):
    """'included' or 'missed' when a person answered about this opening balance as it is now, else None."""
    answer = record.get('openingInclusion')
    if answer and (answer['openingBalanceId'], answer['asOf']) == (opening['id'], opening['asOf']):
        return answer['status']
    return None


def entry_inclusion(doc, record, body, origin):
    """Manual entry asks whether a record dated on or before the customer's opening balance is already part of it. 'Not sure'
    (or no answer) leaves it unresolved; for a later record the question does not arise."""
    choice = body.get('inclusion')
    require(choice in (None, '', 'included', 'missed', 'unsure'), 400, 'INVALID_INPUT', 'Choose yes, no or not sure.', 'inclusion')
    opening = opening_of(doc, record['customerId'])
    date = record_date(record)
    if choice in ('included', 'missed') and opening and (not date or date <= opening['asOf']):
        annotate(record, 'openingInclusion', {'status': choice, 'openingBalanceId': opening['id'], 'asOf': opening['asOf'],
                                              'by': origin['by'], 'role': origin.get('role'), 'at': origin['at']}, origin)


def answer_inclusion(doc, kind, record_id, body, settings, set_by):
    """Whether an invoice or payment dated on or before the customer's opening balance is part of it. For an included invoice,
    what was still owed on it at the as-at date may be given too (it becomes the invoice's stated amount as of that date)."""
    record = find(doc, kind, record_id)
    require(active(record), 409, 'INACTIVE', 'A removed or reverted record has nothing to answer.')
    opening = opening_of(doc, record['customerId'])
    require(opening is not None, 409, 'NO_OPENING', 'This customer has no opening balance, so there is nothing to answer.')
    date = record_date(record)
    require(not date or date <= opening['asOf'], 409, 'NOT_APPLICABLE', 'This record is dated after the opening balance, so it is new activity.')
    status = body.get('status')
    require(status in ('included', 'missed', 'unsure'), 400, 'INVALID_INPUT', 'Choose yes, no or not sure.', 'status')
    owed = None
    if kind == 'invoices' and body.get('stillOwed') not in (None, ''):
        require(status == 'included', 400, 'INVALID_INPUT', 'An amount still owed at the as-at date only applies to an invoice that is part of it.', 'stillOwed')
        owed = parse_money(body['stillOwed'], settings, 'stillOwed')
        require(minor(owed) <= minor(record.get('total')), 400, 'INVALID_AMOUNT', 'The amount still owed cannot be more than the invoice amount.', 'stillOwed')
        require(not record.get('outstandingAsOf') or record['outstandingAsOf'] <= opening['asOf'], 409, 'LATER_STATEMENT',
                'This invoice already has an amount still owed stated as of a later date (' + str(record.get('outstandingAsOf')) + ').', 'stillOwed')
    value = None if status == 'unsure' else {'status': status, 'openingBalanceId': opening['id'], 'asOf': opening['asOf'], 'by': set_by['by'],
                                              'role': set_by.get('role'), 'at': set_by['at']}
    require(owed is not None or (value or {}).get('status') != inclusion_answer(record, opening), 400, 'NO_CHANGE', 'That is already the answer.')
    annotate(record, 'openingInclusion', value, set_by)
    if owed is not None and (record.get('outstandingAmount'), record.get('outstandingAsOf')) != (owed, opening['asOf']):
        set_version(record, 'invoices', {**{k: record.get(k) for k in CORRECTABLE['invoices']}, 'outstandingAmount': owed, 'outstandingAsOf': opening['asOf'],
                                         'outstandingSource': 'opening_balance'},
                    {**set_by, 'kind': 'correction', 'reason': 'Still owed at the opening balance date ' + opening['asOf']})
    return record


def describe_record(record):
    """An invoice's number, or a payment's reference (or, without one, its date and amount)."""
    if 'receivedDate' in record:
        return record.get('reference') or record['receivedDate'] + ' ' + money_text_plain(record['amount'])
    return record['reference']


def opening_view(doc, customer_id):
    """A customer's opening balance and what the records say about it (P002 8.1), or None without one.

    Records dated after the as-at date are new activity and count. On or before it, each is included (no effect: it explains the
    balance), missed (counts, as an attributed correction) or unresolved (no effect; shown as "plus up to" / "minus up to"). Only a
    person's answer includes or excludes a record. When all the unanswered invoices, with the included ones, have amounts still
    owed at the as-at date that add up exactly to the balance, that is offered as a suggestion: a missing invoice and a missing
    credit reconcile just as well, and so would another combination of records.

    Credits: a person says the figure includes none, or that every credit in it is recorded here (as payments or credits dated on
    or before the as-at date, included in it). Included invoices adding up to more than a net balance imply credits; that is a
    conflict when the figure was said to have none, or when the recorded credits are fewer than that."""
    opening = opening_of(doc, customer_id)
    if opening is None:
        return None
    on, template = opening['asOf'], opening['amount']
    invoices = [i for i in doc['invoices'] if active(i) and i['customerId'] == customer_id]
    payments = [p for p in doc.get('payments', []) if active(p) and p['customerId'] == customer_id]
    status, stale = {}, 0
    for record in invoices + payments:
        date = record_date(record)
        if date and date > on:
            status[record['id']] = 'new'
            continue
        answer = inclusion_answer(record, opening)
        stale += bool(record.get('openingInclusion') and not answer)
        status[record['id']] = answer or 'unresolved'

    def owed_at(invoice):
        return minor(invoice['outstandingAmount']) if invoice.get('outstandingAmount') and invoice.get('outstandingAsOf') == on else None
    candidates = [i for i in invoices if status[i['id']] == 'unresolved']
    pool = candidates + [i for i in invoices if status[i['id']] == 'included']
    suggestion = None
    if candidates and all(owed_at(i) is not None for i in pool) and sum(owed_at(i) for i in pool) == minor(opening['amount']):
        suggestion = {'ids': [i['id'] for i in candidates], 'references': [i['reference'] for i in candidates]}
    included = [i for i in invoices if status[i['id']] == 'included']
    known = [owed_at(i) for i in included if owed_at(i) is not None]
    credits = credits_of(opening)
    recorded = sum(minor(p['amount']) for p in payments if status[p['id']] == 'included')   # credits and prepayments in it, as recorded
    conflicts, conflict_codes, implied, unexplained = [], [], None, None
    if len(known) == len(included):
        difference = sum(known) - minor(opening['amount'])
        if difference > 0:
            implied = amount_of(template, difference)
        elif difference < 0 and included:
            unexplained = amount_of(template, -difference)
    need = minor(implied) if implied else max(0, -minor(opening['amount']))   # a balance held in credit is at least that much credit
    if credits == 'none' and need:
        conflicts.append('The opening balance is said to include no credits, but the invoices included in it and the balance imply credits '
                         'of at least ' + money_text_plain(amount_of(template, need)) + '.')
        conflict_codes.append(['no_credits_but_implied', {'need': need}])
    if credits == 'recorded' and need > recorded:
        conflicts.append('The opening balance implies credits of at least ' + money_text_plain(amount_of(template, need)) + ', but only ' +
                         template['currency'] + ' ' + money_text_plain(amount_of(template, recorded)) + ' of payments and credits included in it is recorded.')
        conflict_codes.append(['credits_recorded_below_implied', {'need': need, 'recorded': recorded}])
    counts = [i for i in invoices if status[i['id']] in ('new', 'missed')]
    without_amount = [i['reference'] for i in counts if not i.get('total')]
    balance = None if without_amount else (minor(opening['amount']) + sum(minor(i['total']) for i in counts) -
                                           sum(minor(p['amount']) for p in payments if status[p['id']] in ('new', 'missed')))
    unresolved_invoices = [i for i in invoices if status[i['id']] == 'unresolved']
    unresolved_payments = [p for p in payments if status[p['id']] == 'unresolved']
    return {'openingBalance': opening, 'asOf': on, 'suggestion': suggestion, 'credits': credits, 'creditsRecorded': amount_of(template, recorded),
            'staleAnswers': stale,
            'records': [{'kind': 'payment' if 'receivedDate' in r else 'invoice', 'id': r['id'], 'reference': describe_record(r), 'date': record_date(r),
                         'status': status[r['id']]} for r in invoices + payments],
            'balance': None if balance is None else amount_of(template, balance), 'withoutAmount': without_amount,
            'unresolvedInvoices': {'count': len(unresolved_invoices), 'references': [i['reference'] for i in unresolved_invoices],
                                   'amount': amount_of(template, sum(minor(i.get('total')) for i in unresolved_invoices)),
                                   'withoutAmount': sum(1 for i in unresolved_invoices if not i.get('total'))},
            'unresolvedPayments': {'count': len(unresolved_payments), 'amount': amount_of(template, sum(minor(p['amount']) for p in unresolved_payments))},
            'impliedCredits': implied, 'unexplained': unexplained, 'conflicts': conflicts, 'conflictCodes': conflict_codes}


# ---------------------------------------------------------------- coverage statements (Stage 3, P002 section 8.2)

COVERAGE_TYPES = ('invoices', 'payments')


def coverage_fields(doc, body, today):
    """Which records are confirmed complete: customers (a list, or 'all'), record types and a period. Nothing else establishes it."""
    customers = body.get('customers')
    known = {c['id'] for c in doc['customers'] if active(c)}
    require(customers == 'all' or (isinstance(customers, list) and customers and len(set(customers)) == len(customers) and set(customers) <= known),
            400, 'INVALID_INPUT', 'Choose all customers, or one or more existing customers.', 'customers')
    types = body.get('recordTypes')
    require(isinstance(types, list) and types and len(set(types)) == len(types) and set(types) <= set(COVERAGE_TYPES), 400, 'INVALID_INPUT',
            'Choose invoices, payments or both.', 'recordTypes')
    start, end = parse_day(body.get('from'), 'from'), parse_day(body.get('to'), 'to')
    require(end <= today.isoformat(), 400, 'INVALID_DATE', 'Completeness can only be confirmed up to today.', 'to')
    require(start <= end, 400, 'INVALID_DATE', 'The period has to start on or before its last day.', 'from')
    return {'customers': customers, 'recordTypes': [t for t in COVERAGE_TYPES if t in types], 'from': start, 'to': end}


def new_coverage(doc, body, today, record_id, origin, basis='attestation', batch_id=None):
    """A person's statement that the records of these types, for these customers, are complete for the period."""
    fields = coverage_fields(doc, body, today)
    require(body.get('confirm') is True, 400, 'INVALID_INPUT', 'Tick to confirm the records are complete for this period. If you are not sure, '
            'leave it: nothing is assumed complete.', 'confirm')
    source = text_value(body.get('sourceLabel'), 'sourceLabel', 80, 'how you know they are complete')
    statement = {'id': record_id, **fields, 'basis': basis, 'batchId': batch_id, 'sourceLabel': source, 'confirmedBy': origin['by'],
                 'confirmedRole': origin.get('role'), 'confirmedAt': origin['at'], 'status': 'active', 'version': 1, 'origin': origin, 'setBy': origin,
                 'history': []}
    doc.setdefault('coverage', []).append(statement)
    return statement


def retire_coverage(doc, coverage_id, body, set_by):
    statement = find(doc, 'coverage', coverage_id)
    require(active(statement), 409, 'INACTIVE', 'This statement is no longer in force.')
    require(statement.get('basis') != 'export', 409, 'FROM_IMPORT', 'This statement came with an import. Revert that import instead.')
    statement.update({'status': 'retired', 'retired': {'by': set_by['by'], 'role': set_by.get('role'), 'at': set_by['at'], 'reason': reason_value(body)}})
    return statement


def applies_to(statement, customer_id):
    return statement['customers'] == 'all' or customer_id in statement['customers']


def day(iso, delta):
    return (date.fromisoformat(iso) + timedelta(days=delta)).isoformat()


def contradictions(doc, statement, customer_id, kind):
    """This customer's records of this type whose place in the confirmed period changed after it was confirmed: added to it, or
    removed, reverted or corrected out of it although they were in it then (or corrected into it). The statement was about the records
    as they were, so for this customer it no longer holds. A record entered and removed again after confirmation changes nothing."""
    found, at = [], statement['confirmedAt']

    def within(day_):
        return statement['from'] <= (day_ or '') <= statement['to']
    for record in doc.get(kind, []):
        if record['customerId'] != customer_id:
            continue
        later = [h for h in record.get('history', []) if h['replacedAt'] > at]
        gone = (record.get('removed') or record.get('reverted') or {}).get('at')
        existed = ((record.get('origin') or {}).get('at') or '') <= at and not (gone and gone <= at)
        was_in = existed and within(record_date(later[0]['values']) if later else record_date(record))
        is_in = active(record) and within(record_date(record))
        if was_in != is_in:   # says which way, so the explanation can name what happened (QA U7)
            found.append({'id': record['id'], 'record': describe_record(record), 'change': 'added' if is_in else 'removed'})
    return found


def coverage_view(doc, customer_id):
    """Per record type: the customer's base (opening balance as-at date, else the start of their earliest usable statement), the
    end of the unbroken run of confirmed periods from it ('complete to'; None without one), and last activity, which is shown
    separately and never used as completeness. Contradicted statements don't count for this customer."""
    opening = opening_of(doc, customer_id)
    statements = [c for c in doc.get('coverage', []) if active(c) and applies_to(c, customer_id)]
    usable, contradicted = {k: [] for k in COVERAGE_TYPES}, {k: [] for k in COVERAGE_TYPES}
    for statement in statements:
        for kind in statement['recordTypes']:
            found = (statement['contradictedFor'][customer_id][kind] if 'contradictedFor' in statement else
                     contradictions(doc, statement, customer_id, kind))
            (contradicted[kind].append({'coverageId': statement['id'], 'from': statement['from'], 'to': statement['to'],
                                        'records': [x['record'] for x in found], 'changes': found}) if found else usable[kind].append(statement))
    starts = [c['from'] for kind in COVERAGE_TYPES for c in usable[kind]]
    base = opening['asOf'] if opening else min(starts) if starts else None
    view = {}
    for kind in COVERAGE_TYPES:
        run = None if base is None else base if opening else day(base, -1)   # an opening balance summarises everything up to its date
        start = run
        for statement in sorted(usable[kind], key=lambda c: c['from']):
            if run is None or statement['from'] > day(run, 1):
                break
            run = max(run, statement['to'])
        dates = [record_date(r) for r in doc.get(kind, []) if active(r) and r['customerId'] == customer_id and record_date(r)]
        view[kind] = {'base': base, 'completeTo': run if run is not None and run != start else None,
                      'statements': [c['id'] for c in usable[kind]], 'contradicted': contradicted[kind], 'lastActivity': max(dates) if dates else None}
    return view


# ---------------------------------------------------------------- an exact amount still owed (Stage 3, P002 section 8.3)

def day_text(iso):
    d = date.fromisoformat(iso)
    return ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')[d.weekday()] + ' ' + str(d.day) + ' ' + d.strftime('%b %Y')


def money_words(template, units):
    return template['currency'] + ' ' + money_text_plain(amount_of(template, units))


def opening_prerequisites(opening, view, base):
    """[(text, code, values)] for prerequisite 0 of exact_outstanding, which is about the customer, not one invoice: an opening balance
    exists and a person has said what credits it includes. Shared with customer_blocks so the two never differ."""
    if opening is None:
        return [('No opening balance says what this customer owed, or held in credit, before ' + (day_text(base) if base else 'their records start') +
                 '. A credit from before then could settle this invoice.', 'no_opening_balance', {'base': base})]
    if view['credits'] is None:
        if minor(opening['amount']) < 0:
            return [('The opening balance is a credit of ' + money_words(opening['amount'], -minor(opening['amount'])) + ' held for the customer, and it '
                     'is not recorded what that credit is for. It could settle this invoice.', 'opening_credit_unexplained', {'credit': -minor(opening['amount'])})]
        return [('Whether the opening balance as at ' + day_text(opening['asOf']) + ' includes credits or prepayments is not stated. A credit in it '
                 'could settle this invoice: say it has none, or record its credits.', 'opening_credits_not_stated', {'asOf': opening['asOf']})]
    return []


def opening_unresolved(view):
    """[(text, code, values)] for the customer-level part of prerequisite 5 of exact_outstanding: records on or before the opening balance
    date not yet answered, and conflicts the opening balance itself shows."""
    if not view:
        return []
    out, unresolved = [], view['unresolvedInvoices']['count'] + view['unresolvedPayments']['count']
    if unresolved:
        out.append((str(unresolved) + ' record(s) dated on or before the opening balance are not yet answered as part of it or not' +
                    (' (their amounts reconcile with it, which only suggests they are)' if view['suggestion'] else '') + '.',
                    'opening_records_unanswered', {'count': unresolved, 'suggestion': bool(view['suggestion'])}))
    return out + [(text, code, values) for text, (code, values) in zip(view['conflicts'], view['conflictCodes'])]


def customer_blocks(opening_view_, base):
    """Codes of the customer-level prerequisites that stop any exact amount for this customer (exact_outstanding's 0 and the opening part
    of 5): no opening balance, credits not stated or unexplained, opening records unanswered, opening conflicts. opening_view_ is
    opening_view(doc, customer) (None without an opening balance); base is coverage_view's base. [] when none stops it."""
    opening = opening_view_ and opening_view_['openingBalance']
    return [code for _, code, _ in opening_prerequisites(opening, opening_view_, base) + opening_unresolved(opening_view_)]


def exact_outstanding(doc, invoice):
    """(exact, reasons, codes). An exact amount still owed on one invoice, as of the date the customer's payment records are confirmed
    complete to, only when every prerequisite holds (P002 8.3, made stricter for credits):
      0. an opening balance says what the customer owed or held in credit at the base, and a person has said what credits it
         includes (none, or every one recorded here): an unaccounted credit could settle any later invoice;
      1. the invoice amount is known, and nothing about it contradicts itself;
      2. its starting amount is known: it is dated after the opening balance (start: its amount), or a person confirmed it is part
         of the opening balance and what was still owed on it then (start: that amount, then);
      3. the customer's payments are confirmed complete from the opening balance date;
      4. every payment or credit of the customer received up to that date, however early, is allocated, or marked by a person as
         not for an open invoice;
      5. nothing about the customer is unresolved: inclusion (equal amounts only suggest it), conflicts.
    Otherwise exact is None and reasons says, in plain words, what is missing. Nothing is assumed. Codes say the same as the reasons
    without their wording, each with the values its sentence states, so evidence keys compare what is said (docs/EVIDENCE-KEYS.md)."""
    cid, reasons, codes, start = invoice['customerId'], [], [], None

    def why(text, code, **values):
        reasons.append(text)
        codes.append([code, values])
    opening, cover = opening_of(doc, cid), coverage_view(doc, cid)['payments']
    base, complete = cover['base'], cover['completeTo']
    template = invoice.get('total') or invoice.get('outstandingAmount') or {'currency': doc.get('currency', ''), 'scale': doc.get('scale', 2)}
    total = minor(invoice['total']) if invoice.get('total') else None
    rows, statement = allocations_to(doc, invoice), statement_of(doc, invoice)
    position, view = allocation_position(doc, invoice), opening_view(doc, cid)
    if total is None:
        why('The invoice amount is not recorded.', 'no_invoice_amount')
    for text, code, values in opening_prerequisites(opening, view, base):
        why(text, code, **values)
    if complete is None:
        # From the day after the opening balance: it summarises everything up to its own date (QA U7 read "from Wed 30 Sep" as wrong).
        start_day = (day(base, 1) if opening else base) if base else None
        why('Payment records for this customer have no confirmed completeness' + (' from ' + day_text(start_day) if start_day else '') +
            (', the day after the opening balance' if opening and start_day else '') + '.', 'no_completeness', base=base, opening=bool(opening))
        for broken in cover['contradicted']:
            why('The statement that they were complete from ' + day_text(broken['from']) + ' to ' + day_text(broken['to']) + ' no longer holds: ' +
                '; '.join(x['record'] + (' was added inside that period' if x['change'] == 'added' else ' was taken out of that period')
                          for x in broken['changes']) + ' after it was confirmed. Confirm completeness again if the records are complete.',
                'completeness_broken', coverageId=broken['coverageId'], changes=[[x['id'], x['change']] for x in broken['changes']])
    issue = invoice.get('issueDate')
    if opening and total is not None:
        if issue and issue > base:
            start = ('total', total, None)
            if statement:   # a statement of what was still owed has to agree with complete records
                stated, on = statement
                missed = sum(minor(a['amount']) for a, p in rows if p['receivedDate'] <= on and statement_answer(a, statement) == 'missed')
                expected = total - sum(minor(a['amount']) for a, p in rows if p['receivedDate'] <= on) + missed
                if expected != stated:
                    why('The amount stated still owed as of ' + day_text(on) + ' (' + money_words(template, stated) + ') does not match the '
                        'invoice amount less the payments allocated to it up to then (' + money_words(template, expected) + ').',
                        'stated_differs_from_records', on=on, stated=stated, expected=expected)
        else:
            status = next(r['status'] for r in view['records'] if r['id'] == invoice['id'])
            on, as_of = day_text(opening['asOf']), opening['asOf']
            if status == 'included' and statement and statement[1] == opening['asOf']:
                start = ('opening', statement[0], opening['asOf'])
                if position and position['inclusion']['unresolved']:
                    why('Whether what was still owed on it at ' + on + ' already reflected earlier payments allocated to it is not answered.',
                        'opening_reflection_unanswered', asOf=as_of)
            elif status == 'included':
                why('What was still owed on it at the opening balance date (' + on + ') is not recorded.', 'opening_amount_not_recorded', asOf=as_of)
            elif status == 'missed':
                why('It was left out of the opening balance, so what was owed on it at ' + on + ' is not established.', 'left_out_of_opening', asOf=as_of)
            else:
                why('Whether it is part of the opening balance as at ' + on + ' is not answered.', 'opening_inclusion_unanswered', asOf=as_of)
    if issue and complete and issue > complete:
        why('Payment records are confirmed complete only to ' + day_text(complete) + ', before this invoice was issued.', 'complete_before_issue', to=complete)
    first = (day(base, 1) if opening else base) if base else None
    if complete:
        loose = [(p, minor(p['amount']) - allocated_from(doc, p['id'])) for p in doc.get('payments', [])
                 if active(p) and p['customerId'] == cid and p['receivedDate'] <= complete and not p.get('notForOpenInvoices')]
        loose = [(p, left) for p, left in loose if left > 0]
        if loose:
            why(money_words(template, sum(left for _, left in loose)) + ' in ' + str(len(loose)) + ' payment(s) or credit(s) received up to ' +
                day_text(complete) + ' is neither allocated nor marked as not for an open invoice.', 'unallocated_in_period', to=complete,
                amount=sum(left for _, left in loose), payments=sorted(p['id'] for p, _ in loose))
    for text, code, values in opening_unresolved(view):
        why(text, code, **values)
    if position and position['conflicts']:
        why('Its records contradict each other.', 'records_conflict')
    if reasons or start is None:
        return None, reasons, codes
    kind, amount, since = start
    counted = sum(minor(a['amount']) for a, p in rows if (since is None or p['receivedDate'] > since) and p['receivedDate'] <= complete)
    missed = sum(minor(a['amount']) for a, p in rows if since and p['receivedDate'] <= since and statement_answer(a, statement) == 'missed')
    later = sum(minor(a['amount']) for a, p in rows if p['receivedDate'] > complete)
    if amount - counted - missed < 0:
        return None, ['Payments allocated to it add up to more than its starting amount.'], [['over_allocated', {}]]
    steps = [{'label': 'Invoice amount' if kind == 'total' else 'Still owed on it at the opening balance date, ' + day_text(since), 'amount': amount_of(template, amount)}]
    if counted:
        steps.append({'label': 'Payments and credits allocated to it ' + ('after ' + day_text(since) + ', ' if since else '') + 'up to ' + day_text(complete),
                      'amount': amount_of(template, -counted)})
    if missed:
        steps.append({'label': 'Earlier payments the amount at ' + day_text(since) + ' did not reflect', 'amount': amount_of(template, -missed)})
    return {'amount': amount_of(template, amount - counted - missed), 'asOf': complete, 'basis': kind, 'steps': steps, 'paymentsFrom': first,
            'later': amount_of(template, later) if later else None, 'coverage': cover['statements']}, [], []


def invoice_position(doc, invoice):
    """What the records support about the amount still owed on one invoice: an 'at most' bound from allocated payments, and an
    exact amount when the prerequisites hold (with the reasons when they don't). None when neither applies, so cases keep their
    plain facts (stated, sample or not recorded)."""
    position = allocation_position(doc, invoice)
    exact, reasons, codes = exact_outstanding(doc, invoice)
    if position is None and exact is None:
        return None
    if position is None:
        zero = amount_of(exact['amount'], 0)
        position = {'status': 'open', 'basis': exact['basis'], 'statedAsOf': None, 'stated': None, 'allocated': zero, 'counted': zero,
                    'atMost': exact['amount'], 'excess': None, 'inclusion': {'basis': None, 'included': [], 'missed': [], 'unresolved': [], 'reconciles': [],
                                                                             'stale': 0},
                    'conflicts': [], 'checks': [], 'conflictCodes': [], 'checkCodes': []}
    position.update({'exact': exact, 'notExact': [] if exact else reasons, 'notExactCodes': [] if exact else codes})
    if exact:
        now = minor(exact['amount']) - minor(exact['later'])   # payments after the complete-to date still come off, as an upper bound
        position.update({'atMost': amount_of(exact['amount'], max(0, now)), 'status': 'settled' if now <= 0 else 'open'})
    return position


def mark_unrelated(doc, payment_id, body, set_by):
    """A person says the unallocated part of a payment is not for any open invoice (for example a deposit for a future order),
    so it no longer stands in the way of an exact amount. Undone with unrelated: false."""
    payment = find(doc, 'payments', payment_id)
    require(active(payment), 409, 'INACTIVE', 'This payment has been removed or reverted.')
    value = body.get('unrelated')
    require(value in (True, False), 400, 'INVALID_INPUT', 'Say whether it is for an open invoice.', 'unrelated')
    require(bool(payment.get('notForOpenInvoices')) != value, 400, 'NO_CHANGE', 'That is already recorded.')
    annotate(payment, 'notForOpenInvoices', {'by': set_by['by'], 'role': set_by.get('role'), 'at': set_by['at'], 'reason': reason_value(body)}
             if value else None, set_by)
    return payment
