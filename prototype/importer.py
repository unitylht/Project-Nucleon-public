"""Invoice-list CSV import: read, map columns, preview against the records, apply, and revert. Deterministic code only.

Slice 2 supports one shape: one row per invoice (customer, invoice number, invoice date, amount; optionally a due
date and an amount still owed or paid). Identity is (customer, invoice number): two customers may share a number.
Ledgers, payments, opening balances and XLSX files are not part of this slice (P002 section 11.3).
"""
from __future__ import annotations

import base64
import copy
import csv
import io
import itertools
import re
import unicodedata
from collections import Counter
from datetime import date, timedelta
from difflib import get_close_matches
from statistics import median

import xlsx
from agent import fingerprint
from records import (RecordsError, active, allocated_from, allocation_room, allocations_to, amount_of, minor, money_text_plain, name_key, new_customer,
                     inclusion_answer, new_opening, opening_of, parse_money, ref_key, require, set_version, statement_answer, statement_of)

FIELDS = ('customer', 'invoiceNumber', 'issueDate', 'amount', 'dueDate', 'stillOwed', 'amountPaid')
REQUIRED = ('customer', 'invoiceNumber', 'issueDate', 'amount')
LABELS = {'customer': 'Customer', 'invoiceNumber': 'Invoice number', 'issueDate': 'Invoice date', 'amount': 'Invoice amount',
          'dueDate': 'Due date', 'stillOwed': 'Amount still owed', 'amountPaid': 'Amount paid'}
SYNONYMS = {
    'customer': ('customer', 'customer name', 'client', 'client name', 'account', 'account name', 'debtor', 'bill to', 'contact',
                 'khach hang', 'ten khach hang', 'customer name english'),
    'invoiceNumber': ('invoice', 'invoice number', 'invoice no', 'invoice num', 'inv', 'inv no', 'invoice ref', 'invoice reference',
                      'so hoa don', 'number'),
    'issueDate': ('invoice date', 'date', 'issue date', 'issued', 'date issued', 'ngay hoa don'),
    'amount': ('amount', 'total', 'invoice total', 'invoice amount', 'gross', 'total amount', 'so tien', 'thanh tien'),
    'dueDate': ('due date', 'due', 'payment due', 'due on', 'han thanh toan'),
    'stillOwed': ('balance', 'amount due', 'outstanding', 'amount owing', 'still owed', 'balance due', 'amount outstanding', 'con no', 'cong no'),
    'amountPaid': ('paid', 'amount paid', 'payments', 'total paid'),
}
# Payments received (Stage 3): one row per payment; an invoice column is an explicit allocation to that customer's invoice.
PAYMENT_FIELDS = ('customer', 'paymentDate', 'amount', 'reference', 'invoiceNumber')
PAYMENT_REQUIRED = ('customer', 'paymentDate', 'amount')
PAYMENT_LABELS = {'customer': 'Customer', 'paymentDate': 'Date received', 'amount': 'Amount received', 'reference': 'Payment reference',
                  'invoiceNumber': 'Invoice it pays'}
PAYMENT_SYNONYMS = {
    'customer': SYNONYMS['customer'],
    'paymentDate': ('date', 'payment date', 'date received', 'received', 'received on', 'paid on', 'transaction date', 'ngay chung tu'),
    'amount': ('amount', 'amount received', 'payment', 'payment amount', 'paid', 'credit', 'so tien'),
    'reference': ('reference', 'ref', 'payment reference', 'memo', 'details', 'description', 'so chung tu'),
    'invoiceNumber': ('invoice', 'invoice number', 'invoice no', 'for invoice', 'applies to', 'so hoa don'),
}
# Opening balances (a proposal's third batch): one row per customer, as at a date, owed by the customer or held in credit for them.
OPENING_FIELDS = ('customer', 'asOf', 'amount', 'direction')
OPENING_REQUIRED = ('customer', 'asOf', 'amount')
OPENING_LABELS = {'customer': 'Customer', 'asOf': 'As at', 'amount': 'Opening balance', 'direction': 'Owed or in credit'}
OPENING_SYNONYMS = {'customer': SYNONYMS['customer'], 'asOf': ('as at', 'as of', 'opening date'), 'amount': ('opening balance', 'amount', 'balance'),
                    'direction': ('direction', 'owed or in credit')}
SHAPES = {'invoices': (FIELDS, REQUIRED, LABELS, SYNONYMS), 'payments': (PAYMENT_FIELDS, PAYMENT_REQUIRED, PAYMENT_LABELS, PAYMENT_SYNONYMS),
          'openings': (OPENING_FIELDS, OPENING_REQUIRED, OPENING_LABELS, OPENING_SYNONYMS)}
MAX_CHARS, MAX_ROWS, MAX_COLUMNS = 2_000_000, 20_000, 60
MONTHS = {m: i + 1 for i, m in enumerate(('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'))}
NUMERIC_DATE = re.compile(r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})')


# ---------------------------------------------------------------- reading the file

def read_rows(text):
    """The file's non-blank rows, each with its row number (the file's lines; blank rows are skipped)."""
    require(isinstance(text, str) and text.strip(), 400, 'INVALID_FILE', 'The file is empty.', 'csvText')
    require(len(text) <= MAX_CHARS, 400, 'INVALID_FILE', 'The file is too large (limit about 2 MB).', 'csvText')
    text = text.lstrip('﻿')
    try:
        dialect = csv.Sniffer().sniff(text[:20000], delimiters=',;\t')
    except csv.Error:
        dialect = csv.excel
    rows = []
    for number, cells in enumerate(csv.reader(io.StringIO(text), dialect), start=1):
        if any(c.strip() for c in cells):
            rows.append((number, [c.strip() for c in cells]))
    require(len(rows) - 1 <= MAX_ROWS, 400, 'INVALID_FILE', 'The file has more than ' + str(MAX_ROWS) + ' rows.', 'csvText')
    return rows


def read_csv(text):
    """Header and data rows. The first non-blank row is the header; blank rows are skipped; row numbers are the file's lines."""
    rows = read_rows(text)
    require(len(rows) >= 2, 400, 'INVALID_FILE', 'The file needs a header row and at least one invoice row.', 'csvText')
    header = rows[0][1]
    require(len(header) <= MAX_COLUMNS, 400, 'INVALID_FILE', 'The file has more than ' + str(MAX_COLUMNS) + ' columns.', 'csvText')
    return header, rows[1:]


def signature(header):
    return '|'.join(name_key(h) for h in header)


def suggest_mapping(header, shape='invoices'):
    """Columns whose heading is a known name for a field. Each column is used once; the person confirms."""
    fields, _, _, synonyms = SHAPES[shape]
    mapping, used = {}, set()
    for field in fields:
        for index, heading in enumerate(header):
            if index not in used and name_key(heading) in synonyms[field]:
                mapping[field] = index
                used.add(index)
                break
    return mapping


def validate_mapping(header, mapping, shape='invoices'):
    fields, required, labels, _ = SHAPES[shape]
    require(isinstance(mapping, dict) and set(mapping) <= set(fields), 400, 'INVALID_MAPPING', 'Unknown field in the column mapping.', 'mapping')
    for field, index in mapping.items():
        require(type(index) is int and 0 <= index < len(header), 400, 'INVALID_MAPPING', 'Choose a column for ' + labels[field] + '.', field)
    require(len(set(mapping.values())) == len(mapping), 400, 'INVALID_MAPPING', 'Each column can be used for one field only.', 'mapping')
    require(not ('stillOwed' in mapping and 'amountPaid' in mapping), 400, 'INVALID_MAPPING',
            'Map either the amount still owed or the amount paid, not both.', 'amountPaid')
    return [labels[f] for f in required if f not in mapping]


# ---------------------------------------------------------------- values

def date_order(cells):
    """'dmy' or 'mdy' when numeric dates show it, 'ymd' when there are none, None when the person must say."""
    days_first = months_first = False
    numeric = [NUMERIC_DATE.fullmatch(c) for c in cells if c]
    for match in filter(None, numeric):
        a, b = int(match.group(1)), int(match.group(2))
        days_first |= a > 12
        months_first |= b > 12
    if not any(numeric):
        return 'ymd'
    if days_first != months_first:
        return 'dmy' if days_first else 'mdy'
    return None


def parse_date_cell(text, order):
    text = text.strip()
    try:
        if re.fullmatch(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', text):
            y, m, d = (int(x) for x in re.split(r'[-/]', text))
            return date(y, m, d).isoformat()
        match = NUMERIC_DATE.fullmatch(text)
        if match and order in ('dmy', 'mdy'):
            a, b, y = (int(x) for x in match.groups())
            return (date(y, b, a) if order == 'dmy' else date(y, a, b)).isoformat()
        match = re.fullmatch(r'(\d{1,2})[ -]([A-Za-z]{3,9})[ -](\d{4})', text)
        if match and match.group(2)[:3].lower() in MONTHS:
            return date(int(match.group(3)), MONTHS[match.group(2)[:3].lower()], int(match.group(1))).isoformat()
    except ValueError:
        return None
    return None


def parse_amount_cell(text, settings, field):
    cleaned = re.sub(r'^(?:' + re.escape(settings['currency']) + r'|[$€£¥₫])\s*', '', text.strip())
    cleaned = re.sub(r'\s*(?:' + re.escape(settings['currency']) + r'|đ|₫)$', '', cleaned)
    return parse_money(cleaned, settings, field)


# ---------------------------------------------------------------- preview

def customer_index(doc):
    """Active customers by name and by names confirmed in earlier imports."""
    index = {}
    for c in doc['customers']:
        if active(c):
            for name in [c['name']] + c.get('aliases', []):
                index.setdefault(name_key(name), c)
    return index


def preview(doc, header, rows, params, settings, today):
    """Classify every row against the current records. Nothing is changed here."""
    if params.get('shape') == 'payments':
        return payment_preview(doc, header, rows, params, settings, today)
    if params.get('shape') == 'openings':
        return opening_preview(doc, header, rows, params, settings, today)
    mapping, resolutions = params.get('mapping') or {}, params.get('resolutions') or {}
    missing_fields = validate_mapping(header, mapping)
    needs = ['Choose a column for: ' + ', '.join(missing_fields) + '.'] if missing_fields else []
    order = params.get('dateOrder')
    if not order and not missing_fields:
        cells = [r[mapping[f]] for _, r in rows for f in ('issueDate', 'dueDate') if f in mapping and mapping[f] < len(r)]
        order = date_order(cells)
    if not missing_fields and not order:
        needs.append('Say whether the dates are day/month/year or month/day/year.')
    owed_mapped = 'stillOwed' in mapping or 'amountPaid' in mapping
    as_of = params.get('asOf')
    if owed_mapped:
        try:
            require(isinstance(as_of, str) and date.fromisoformat(as_of) <= today, 400, '', '')
        except (ValueError, RecordsError):
            as_of = None
            needs.append('Say on which date the amounts still owed in this file were correct ("amounts as of").')
    result = {'dateOrder': order, 'asOf': as_of if owed_mapped else None, 'needs': needs, 'rows': [], 'customers': [], 'coverage': params.get('coverage'),
              'counts': {k: 0 for k in ('new', 'unchanged', 'updated', 'conflict', 'rejected', 'unresolved', 'leftOut')}, 'ready': False}
    if needs:
        return result
    known, seen, unknown = customer_index(doc), {}, {}
    for number, cells in rows:
        row = classify_row(doc, known, number, cells, mapping, order, as_of, settings, resolutions, unknown)
        key = (name_key(row.get('customerName')), ref_key(row.get('reference')))
        if row['status'] != 'rejected' and key in seen:
            first = seen[key]
            same = first['values'] == row['values']
            row.update({'status': 'rejected', 'reason': 'Repeats row ' + str(first['row']) + (' exactly.' if same else ' with different values.')})
            if not same and first['status'] != 'rejected':
                first.update({'status': 'rejected', 'reason': 'Row ' + str(number) + ' has the same invoice with different values.'})
        elif row['status'] != 'rejected':
            seen[key] = row
        result['rows'].append(row)
    for row in result['rows']:
        result['counts'][row['status']] += 1
    names = {c['name'] for c in doc['customers'] if active(c)}
    for key, name in unknown.items():
        choice = resolutions.get('customers', {}).get(key)
        result['customers'].append({'key': key, 'name': name, 'resolution': choice,
                                    'suggestions': get_close_matches(name, sorted(names), n=3, cutoff=0.6)})
    unresolved_customers = [c['name'] for c in result['customers'] if not c['resolution']]
    open_conflicts = [r['row'] for r in result['rows'] if r['status'] == 'conflict' and resolutions.get('conflicts', {}).get(str(r['row'])) not in ('keep', 'take')]
    if unresolved_customers:
        needs.append('Create or choose a customer for: ' + ', '.join(unresolved_customers) + '.')
    if open_conflicts:
        needs.append('Choose keep or replace for rows: ' + ', '.join(str(n) for n in open_conflicts) + '.')
    result['ready'] = not needs and any(r['status'] in ('new', 'updated', 'conflict', 'unchanged') for r in result['rows'])
    return result


def classify_row(doc, known, number, cells, mapping, order, as_of, settings, resolutions, unknown):
    def cell(field):
        index = mapping.get(field)
        return cells[index].strip() if index is not None and index < len(cells) else ''
    row = {'row': number, 'customerName': cell('customer'), 'reference': cell('invoiceNumber')}

    def reject(reason):
        return {**row, 'status': 'rejected', 'reason': reason, 'values': None}
    if not row['customerName']:
        return reject('No customer name.')
    if not row['reference']:
        return reject('No invoice number.')
    issue = parse_date_cell(cell('issueDate'), order)
    if not issue:
        return reject('Invoice date "' + cell('issueDate')[:30] + '" is not a valid date.')
    try:
        total = parse_amount_cell(cell('amount'), settings, 'amount')
    except RecordsError as exc:
        return reject('Invoice amount "' + cell('amount')[:30] + '": ' + exc.message)
    if int(total['minorUnits']) <= 0:
        return reject('The invoice amount must be more than zero (credit notes are not in this version).')
    due = None
    if cell('dueDate'):
        due = parse_date_cell(cell('dueDate'), order)
        if not due or due < issue:
            return reject('Due date "' + cell('dueDate')[:30] + '" is not a valid date on or after the invoice date.')
    owed = None
    if cell('stillOwed') or cell('amountPaid'):
        if issue > as_of:
            return reject('The invoice date is after the "amounts as of" date ' + as_of + '.')
        try:
            if cell('stillOwed'):
                owed = parse_amount_cell(cell('stillOwed'), settings, 'stillOwed')
            else:
                paid = parse_amount_cell(cell('amountPaid'), settings, 'amountPaid')
                owed = {**total, 'minorUnits': str(int(total['minorUnits']) - int(paid['minorUnits']))}
        except RecordsError as exc:
            return reject('Amount still owed or paid: ' + exc.message)
        if not 0 <= int(owed['minorUnits']) <= int(total['minorUnits']):
            return reject('The amount still owed must be between zero and the invoice amount.')
    values = {'issueDate': issue, 'total': total, 'originalDueDate': due, 'outstandingAmount': owed, 'outstandingAsOf': as_of if owed else None}
    row['values'] = values
    key = name_key(row['customerName'])
    customer = known.get(key)
    if customer is None:   # a name the records don't know: a person creates the customer, maps it to one, or leaves the rows out
        unknown.setdefault(key, row['customerName'])
        choice = resolutions.get('customers', {}).get(key)
        if choice == 'skip':
            return {**row, 'status': 'leftOut', 'reason': 'Left out: customer not created.'}
        if choice == 'new':
            return {**row, 'status': 'new', 'customerId': None}
        customer = next((c for c in doc['customers'] if c['id'] == choice and active(c)), None) if choice else None
        if customer is None:
            return {**row, 'status': 'unresolved', 'reason': 'Unknown customer "' + row['customerName'][:60] + '".'}
    existing = next((i for i in doc['invoices'] if active(i) and i['customerId'] == customer['id'] and ref_key(i['reference']) == ref_key(row['reference'])), None)
    row['customerId'] = customer['id']
    if existing is None:
        return {**row, 'status': 'new'}
    return {**row, **compare(existing, values)}


def compare(existing, values):
    """New, unchanged, updated or conflict for a row whose invoice already exists. A correction made by a person wins
    unless they choose to replace it."""
    conflicts, updates = [], {}
    for field in ('issueDate', 'total'):
        if existing.get(field) is None:
            updates[field] = values[field]          # newly supplied (e.g. the sample stores neither)
        elif existing.get(field) != values[field]:
            conflicts.append(field)
    if values['originalDueDate'] and existing.get('originalDueDate') != values['originalDueDate']:
        if existing.get('originalDueDate') is None:
            updates['originalDueDate'] = values['originalDueDate']   # newly supplied
        else:
            conflicts.append('originalDueDate')
    if values['outstandingAmount'] is not None:
        old_amount, old_date = existing.get('outstandingAmount'), existing.get('outstandingAsOf')
        if old_amount is not None and old_date and values['outstandingAsOf'] > old_date and minor(values['outstandingAmount']) > minor(old_amount):
            conflicts.append('outstandingAmount')   # more owed later than stated earlier: a reversed payment, or an error; a person chooses
        elif old_amount is None or (old_date and values['outstandingAsOf'] > old_date):
            updates.update({'outstandingAmount': values['outstandingAmount'], 'outstandingAsOf': values['outstandingAsOf']})
        elif old_date and values['outstandingAsOf'] < old_date:
            conflicts.append('outstandingAsOf')
        elif old_amount != values['outstandingAmount']:
            conflicts.append('outstandingAmount')
    corrected = (existing.get('setBy') or {}).get('kind') == 'correction'
    if corrected and (updates or conflicts):
        conflicts = sorted(set(conflicts) | set(updates))
    status = 'conflict' if conflicts else 'updated' if updates else 'unchanged'
    return {'status': status, 'invoiceId': existing['id'], 'conflictFields': conflicts, 'updates': updates,
            'current': {k: existing.get(k) for k in ('issueDate', 'total', 'originalDueDate', 'outstandingAmount', 'outstandingAsOf')},
            'correctedByPerson': corrected}


# ---------------------------------------------------------------- apply and revert

def apply(doc, batch, result, new_id, set_by):
    """Write a ready preview into the records document. Returns what changed, for the batch record and for revert."""
    require(result['ready'], 409, 'NOT_READY', 'The preview still needs: ' + ' '.join(result['needs']))
    resolutions = batch['params'].get('resolutions') or {}
    created_customers, created_invoices, versions, confirmed, aliases, affected = {}, [], [], [], [], set()
    for choice in result['customers']:
        if choice['resolution'] == 'new':
            created_customers[choice['key']] = None
        elif choice['resolution'] not in (None, 'skip'):
            customer = next(c for c in doc['customers'] if c['id'] == choice['resolution'])
            customer['aliases'] = customer.get('aliases', []) + [choice['name']]
            aliases.append({'customerId': customer['id'], 'alias': choice['name']})
    for row in result['rows']:
        status = row['status']
        if status == 'new':
            customer_id = row.get('customerId')
            if customer_id is None:
                key = name_key(row['customerName'])
                if created_customers.get(key) is None:
                    origin = {**set_by, 'row': row['row']}
                    created_customers[key] = new_customer(doc, {'name': row['customerName']}, new_id('customer'), origin)['id']
                customer_id = created_customers[key]
            values = row['values']
            invoice = {'id': new_id('invoice'), 'customerId': customer_id, 'reference': row['reference'], **values,
                       'outstandingSource': 'file' if values['outstandingAmount'] else None, 'status': 'active', 'version': 1,
                       'origin': {**set_by, 'row': row['row']}, 'setBy': {**set_by, 'row': row['row']}, 'history': []}
            doc['invoices'].append(invoice)
            created_invoices.append(invoice['id'])
        elif status in ('updated', 'conflict'):
            take = status == 'updated' or resolutions.get('conflicts', {}).get(str(row['row'])) == 'take'
            invoice = next(i for i in doc['invoices'] if i['id'] == row['invoiceId'])
            if take:
                # Only what the file states: a column the file leaves empty never clears a recorded value.
                values = row['updates'] if status == 'updated' else {k: v for k, v in row['values'].items() if v is not None}
                values = {**values, 'outstandingSource': 'file' if values.get('outstandingAmount') else invoice.get('outstandingSource')}
                set_version(invoice, 'invoices', {**{k: invoice.get(k) for k in ('issueDate', 'total', 'originalDueDate', 'outstandingAmount',
                                                                                  'outstandingAsOf', 'outstandingSource')}, **values},
                            {**set_by, 'row': row['row']})
                versions.append({'invoiceId': invoice['id'], 'version': invoice['version']})
                affected.add(invoice['id'])
            else:   # the file disagreed and a person kept the recorded value: evidence, unlike a plain confirmation (docs/EVIDENCE-KEYS.md)
                invoice['confirmedBy'] = invoice.get('confirmedBy', []) + [batch['id']]
                invoice['disputedBy'] = invoice.get('disputedBy', []) + [batch['id']]
                confirmed.append(invoice['id'])
        elif status == 'unchanged':
            invoice = next(i for i in doc['invoices'] if i['id'] == row['invoiceId'])
            invoice['confirmedBy'] = invoice.get('confirmedBy', []) + [batch['id']]
            confirmed.append(invoice['id'])
    return {'customers': [c for c in created_customers.values() if c], 'invoices': created_invoices, 'versions': versions,
            'confirmed': confirmed, 'aliases': aliases}, affected


# ---------------------------------------------------------------- which later imports support a record (revert provenance)

INVOICE_VALUES = ('issueDate', 'total', 'originalDueDate', 'outstandingAmount', 'outstandingAsOf')
VALUE_WORDS = {'issueDate': 'invoice date', 'total': 'amount', 'originalDueDate': 'due date', 'outstandingAmount': 'amount still owed',
               'outstandingAsOf': 'date of the amount still owed', 'receivedDate': 'date', 'amount': 'amount', 'reference': 'reference'}


def listing(record, batch):
    """The row in which an applied import listed this record, or None."""
    if not batch or batch.get('status') != 'applied':
        return None
    key = 'paymentId' if 'receivedDate' in record else 'invoiceId'
    return next((r for r in batch['preview']['rows'] if r.get(key) == record['id']), None)


def differences(record, row):
    """The record's current values that the row does not state as they are now."""
    if 'receivedDate' in record:
        same_reference = (ref_key(row['values']['reference']) or None) == (ref_key(record.get('reference')) or None)
        return [f for f in ('receivedDate', 'amount') if row['values'][f] != record[f]] + ([] if same_reference else ['reference'])
    return [f for f in INVOICE_VALUES if row['values'].get(f) != record.get(f)]


def supports(record, batch):
    """Whether a later import supports a record's current values, so that the record can stay, credited to it, when the import the
    values came from is reverted. Only a row accepted as it stood counts, and only if it states every value the record has now. A
    conflicting row whose values a person rejected by keeping the recorded ones never supports them; nor does an equal amount alone, or
    agreement on the fields a file happened to include. The position in 'confirmedBy' decides nothing."""
    row = listing(record, batch)
    return bool(row) and row['status'] in ('unchanged', 'updated') and batch['id'] not in record.get('disputedBy', []) and not differences(record, row)


def words(fields):
    names = [VALUE_WORDS.get(f, f) for f in fields]
    return ', '.join(names[:-1]) + ' and ' + names[-1] if len(names) > 1 else (names[0] if names else 'values')


def unsupported(label, record, later, batch_of):
    """Why reverting would leave a record that stays with no import supporting its values, which later imports are involved, and the way out."""
    parts = []
    for later_id in later:
        batch = batch_of(later_id)
        row = listing(record, batch)
        if row is None:
            parts.append('import ' + later_id + ' lists it, but its row is no longer on record')
            continue
        name = 'the later import "' + batch['sourceLabel'] + '" (' + batch['fileName'] + ', row ' + str(row['row']) + ')'
        if row['status'] == 'conflict' or later_id in record.get('disputedBy', []):
            parts.append(name + ' proposed a different ' + words(row.get('conflictFields') or []) + ', which a person rejected by keeping the recorded '
                         'values')
        else:
            parts.append(name + ' lists it without the ' + words(differences(record, row)) + ' it has now')
    one = len(later) == 1
    return (label + ' would be left with no import supporting the values it keeps: ' + '; '.join(parts) + '. Revert ' +
            ('that import' if one else 'those imports') + ' first (' + ('it changed' if one else 'they changed') + ' nothing in this record), then '
            'this one; or leave this import in place.')


def credited(doc, kind, bid, changes):
    """Records not created or changed by this import whose values were credited to it when the import they came from was reverted."""
    versioned = {v.get('invoiceId') or v.get('paymentId') for v in changes['versions']}
    own = set(changes['invoices' if kind == 'invoices' else 'payments'])
    return [r['id'] for r in doc.get(kind, []) if active(r) and (r.get('setBy') or {}).get('batchId') == bid and r['id'] not in own | versioned]


def revert_impact(doc, batch, cases_about, batch_of=lambda batch_id: None):
    """What reverting this import would do. 'blocked' lists reasons it cannot; 'review' lists what a person must confirm. batch_of
    looks up other imports, to see which of them support a record that would stay."""
    changes, bid = batch['result'], batch['id']
    blocked, review, revert_invoices, restore, keep = [], {'pendingCases': [], 'decidedCases': [], 'answers': []}, [], [], []
    for invoice_id in changes['invoices'] + credited(doc, 'invoices', bid, changes):
        invoice = next(i for i in doc['invoices'] if i['id'] == invoice_id)
        if not active(invoice):
            continue
        later = [b for b in invoice.get('confirmedBy', []) if b != bid]
        if any(a['invoiceId'] == invoice_id and active(a) for a in doc.get('allocations', [])):
            blocked.append('Invoice ' + invoice['reference'] + ' has payments allocated to it. Remove those allocations first.')
        elif (invoice.get('setBy') or {}).get('batchId') != bid:
            blocked.append('Invoice ' + invoice['reference'] + ' was changed afterwards (' + describe(invoice['setBy']) + '). Undo that first.')
        elif later:
            supporters = [b for b in later if supports(invoice, batch_of(b))]
            if supporters:
                keep.append((invoice_id, supporters[-1]))
            else:
                blocked.append(unsupported('Invoice ' + invoice['reference'], invoice, later, batch_of))
        else:
            revert_invoices.append(invoice_id)
    for v in changes['versions']:
        invoice = next(i for i in doc['invoices'] if i['id'] == v['invoiceId'])
        if not active(invoice):
            continue
        if invoice['version'] == v['version'] and invoice['history'] and any(a['invoiceId'] == invoice['id'] and active(a) for a in doc.get('allocations', [])):
            previous = invoice['history'][-1]['values']
            cap = int((previous.get('total') or previous.get('outstandingAmount') or {'minorUnits': '0'})['minorUnits'])
            if sum(int(a['amount']['minorUnits']) for a in doc.get('allocations', []) if a['invoiceId'] == invoice['id'] and active(a)) > cap:
                blocked.append('Invoice ' + invoice['reference'] + ': its earlier amount is less than the payments allocated to it now.')
        if invoice['version'] != v['version']:
            blocked.append('Invoice ' + invoice['reference'] + ' was changed again afterwards (' + describe(invoice['setBy']) + '). Undo that first.')
        else:
            restore.append(v['invoiceId'])
    kept = {invoice_id for invoice_id, _ in keep}
    for customer_id in changes['customers']:
        customer = next(c for c in doc['customers'] if c['id'] == customer_id)
        if not active(customer):
            continue
        others = [i['reference'] for i in doc['invoices'] if i['customerId'] == customer_id and active(i)   # not this import's own invoices
                  and i['id'] not in revert_invoices and i['id'] not in kept and i['id'] not in changes['invoices']]
        notes = [n['id'] for n in doc['notes'] if n.get('scope') == customer_id and n.get('status') in ('draft', 'confirmed')]
        if others or notes:
            blocked.append('Customer ' + customer['name'] + ' has invoices or notes from elsewhere now (' + ', '.join(others + notes)[:200] + ').')
        if opening_of(doc, customer_id):
            blocked.append('Customer ' + customer['name'] + ' has an opening balance recorded after the import. Remove it first.')
    for invoice_id in revert_invoices + restore:
        pending, decided = cases_about(invoice_id)
        review['pendingCases'] += pending
        review['decidedCases'] += decided
    for invoice_id in restore:   # the statement this import set goes back to the earlier one: answers about it stop applying
        invoice = next(i for i in doc['invoices'] if i['id'] == invoice_id)
        review['answers'] += answered(doc, invoice, [a for a, _ in allocations_to(doc, invoice)])
    review['answers'] += inclusion_answered(doc, [i for i in doc['invoices'] if i['id'] in revert_invoices])
    return {'blocked': blocked, 'review': review, 'revertInvoices': revert_invoices, 'restore': restore, 'keep': keep,
            'needsReview': any(review.values())}


def inclusion_answered(doc, records):
    """Answers a person gave about whether these records are part of their customer's opening balance."""
    found = []
    for record in records:
        opening = opening_of(doc, record['customerId'])
        if opening and inclusion_answer(record, opening):
            found.append({'record': record['id'], 'reference': record.get('reference') or record.get('receivedDate'), 'answer': inclusion_answer(record, opening)})
    return found


def answered(doc, invoice, allocations):
    """Answers a person gave about whether this invoice's current statement reflected a payment, among these allocations."""
    statement = statement_of(doc, invoice)
    return [{'allocationId': a['id'], 'invoice': invoice['reference'], 'answer': statement_answer(a, statement)}
            for a in allocations if statement_answer(a, statement)]


def revert(doc, batch, impact, set_by):
    """Apply a revert whose impact is not blocked. Nothing is deleted: records become 'reverted' or get their earlier version back."""
    require(not impact['blocked'], 409, 'REVERT_BLOCKED', 'This import cannot be reverted yet.')
    bid = batch['id']
    for invoice_id in impact['revertInvoices']:
        invoice = next(i for i in doc['invoices'] if i['id'] == invoice_id)
        invoice.update({'status': 'reverted', 'reverted': set_by})
    for invoice_id, later in impact['keep']:
        invoice = next(i for i in doc['invoices'] if i['id'] == invoice_id)
        invoice['confirmedBy'] = [b for b in invoice.get('confirmedBy', []) if b != later]
        invoice['setBy'] = {**invoice['setBy'], 'batchId': later, 'note': 'confirmed by a later import; kept when ' + bid + ' was reverted'}
    for invoice_id in impact['restore']:
        invoice = next(i for i in doc['invoices'] if i['id'] == invoice_id)
        previous = invoice['history'][-1]
        set_version(invoice, 'invoices', previous['values'], set_by)      # the reverted values stay in the history
        invoice['setBy'] = {**previous['setBy'], 'restoredBy': set_by}    # the current values belong to the earlier version again
    for invoice in doc['invoices']:
        if bid in invoice.get('confirmedBy', []):
            invoice['confirmedBy'] = [b for b in invoice['confirmedBy'] if b != bid]
        if bid in invoice.get('disputedBy', []):
            invoice['disputedBy'] = [b for b in invoice['disputedBy'] if b != bid]
    for customer_id in batch['result']['customers']:
        customer = next(c for c in doc['customers'] if c['id'] == customer_id)
        if not any(i['customerId'] == customer_id and active(i) for i in doc['invoices']):
            customer.update({'status': 'reverted', 'reverted': set_by})
    for alias in batch['result']['aliases']:
        customer = next(c for c in doc['customers'] if c['id'] == alias['customerId'])
        customer['aliases'] = [a for a in customer.get('aliases', []) if a != alias['alias']]
    return set(impact['revertInvoices']) | set(impact['restore']), set(impact['revertInvoices'])


def describe(set_by):
    kind = (set_by or {}).get('kind')
    return {'correction': 'a correction', 'file': 'import ' + str((set_by or {}).get('batchId')), 'manual': 'manual entry'}.get(kind, kind or 'a change')



# ---------------------------------------------------------------- payments received (Stage 3)

def payment_preview(doc, header, rows, params, settings, today):
    """Classify payment rows. Identity: (customer, reference) when there is a reference, otherwise (source, customer, date,
    amount, occurrence in the file). Ambiguous identity is never decided here: it goes to review. An invoice column is an
    explicit allocation, only to that same customer's invoice and only up to what is left on it."""
    mapping, resolutions = params.get('mapping') or {}, params.get('resolutions') or {}
    choices = resolutions.get('rows', {})
    missing_fields = validate_mapping(header, mapping, 'payments')
    needs = ['Choose a column for: ' + ', '.join(missing_fields) + '.'] if missing_fields else []
    order = params.get('dateOrder')
    if not order and not missing_fields:
        order = date_order([r[mapping['paymentDate']] for _, r in rows if mapping['paymentDate'] < len(r)])
    if not missing_fields and not order:
        needs.append('Say whether the dates are day/month/year or month/day/year.')
    result = {'shape': 'payments', 'dateOrder': order, 'asOf': None, 'needs': needs, 'rows': [], 'customers': [], 'ready': False,
              'coverage': params.get('coverage'),
              'counts': {k: 0 for k in ('new', 'unchanged', 'updated', 'conflict', 'rejected', 'unresolved', 'leftOut')}}
    if needs:
        return result
    known, unknown, source = customer_index(doc), {}, params.get('sourceLabel') or ''
    parsed = [parse_payment_row(doc, known, number, cells, mapping, order, settings, today, resolutions, unknown) for number, cells in rows]
    # A reference repeated within the file: identical rows are repeats; different values need a person.
    by_ref = {}
    for row in parsed:
        if row['status'] not in ('rejected', 'leftOut', 'unresolved') and row['values']['reference']:
            by_ref.setdefault((name_key(row['customerName']), ref_key(row['values']['reference'])), []).append(row)
    for group in by_ref.values():
        first = group[0]
        for row in group[1:]:
            if row['values'] == first['values'] and choices.get(str(row['row'])) != 'distinct':
                row.update({'status': 'rejected', 'reason': 'Repeats row ' + str(first['row']) + ' exactly.'})
        varied = [r for r in group if r['status'] != 'rejected']
        if len(varied) > 1:
            for row in varied:
                choice = choices.get(str(row['row']))
                if choice == 'skip':
                    row.update({'status': 'leftOut', 'reason': 'Left out by a person.'})
                elif choice != 'distinct' and sum(1 for r in varied if choices.get(str(r['row'])) != 'skip') > 1:
                    row.update({'status': 'unresolved', 'review': 'duplicateReference', 'reason': 'Reference ' + row['values']['reference'] +
                                ' appears in more than one row with different dates or amounts. Leave one out, or say they are different payments.'})
    occurrences, planned = {}, {}
    for row in parsed:
        if row['status'] in ('rejected', 'leftOut', 'unresolved') and row.get('review') != 'possibleDuplicate':
            continue
        v, cust = row['values'], name_key(row['customerName'])
        if v['reference'] and choices.get(str(row['row'])) != 'distinct':
            row['sourceKey'] = fingerprint(['payment', source, cust, 'ref', ref_key(v['reference'])])
        elif v['reference']:
            row['sourceKey'] = fingerprint(['payment', source, cust, 'ref', ref_key(v['reference']), v['receivedDate'], v['amount']])
        else:
            key = (cust, v['receivedDate'], v['amount']['minorUnits'])
            occurrences[key] = occurrences.get(key, 0) + 1
            row['sourceKey'] = fingerprint(['payment', source, cust, 'noref', v['receivedDate'], v['amount'], occurrences[key]])
        classify_payment(doc, row, choices)
        plan_allocation(doc, row, planned)
    result['rows'] = parsed
    for row in parsed:
        result['counts'][row['status']] += 1
    names = {c['name'] for c in doc['customers'] if active(c)}
    for key, name in unknown.items():
        result['customers'].append({'key': key, 'name': name, 'resolution': resolutions.get('customers', {}).get(key),
                                    'suggestions': get_close_matches(name, sorted(names), n=3, cutoff=0.6)})
    unresolved_customers = [c['name'] for c in result['customers'] if not c['resolution']]
    open_conflicts = [r['row'] for r in parsed if r['status'] == 'conflict' and resolutions.get('conflicts', {}).get(str(r['row'])) not in ('keep', 'take')]
    open_rows = [r['row'] for r in parsed if r['status'] == 'unresolved' and r.get('review')]
    if unresolved_customers:
        needs.append('Create or choose a customer for: ' + ', '.join(unresolved_customers) + '.')
    if open_conflicts:
        needs.append('Choose keep or replace for rows: ' + ', '.join(str(n) for n in open_conflicts) + '.')
    if open_rows:
        needs.append('Review rows: ' + ', '.join(str(n) for n in open_rows) + '.')
    result['ready'] = not needs and any(r['status'] in ('new', 'updated', 'conflict', 'unchanged') for r in parsed)
    return result


def parse_payment_row(doc, known, number, cells, mapping, order, settings, today, resolutions, unknown):
    def cell(field):
        index = mapping.get(field)
        return cells[index].strip() if index is not None and index < len(cells) else ''
    row = {'row': number, 'customerName': cell('customer'), 'reference': cell('reference') or None, 'invoiceNumber': cell('invoiceNumber') or None,
           'values': None, 'allocation': None}

    def reject(reason):
        return {**row, 'status': 'rejected', 'reason': reason}
    if not row['customerName']:
        return reject('No customer name.')
    received = parse_date_cell(cell('paymentDate'), order)
    if not received:
        return reject('Date "' + cell('paymentDate')[:30] + '" is not a valid date.')
    if received > today.isoformat():
        return reject('The date is after today.')
    try:
        amount = parse_amount_cell(cell('amount'), settings, 'amount')
    except RecordsError as exc:
        return reject('Amount "' + cell('amount')[:30] + '": ' + exc.message)
    if minor(amount) <= 0:
        return reject('The amount must be more than zero (refunds are not in this version).')
    row['values'] = {'receivedDate': received, 'amount': amount, 'reference': row['reference']}
    key = name_key(row['customerName'])
    customer = known.get(key)
    if customer is None:
        unknown.setdefault(key, row['customerName'])
        choice = resolutions.get('customers', {}).get(key)
        if choice == 'skip':
            return {**row, 'status': 'leftOut', 'reason': 'Left out: customer not created.'}
        if choice == 'new':
            return {**row, 'status': 'new', 'customerId': None}
        customer = next((c for c in doc['customers'] if c['id'] == choice and active(c)), None) if choice else None
        if customer is None:
            return {**row, 'status': 'unresolved', 'reason': 'Unknown customer "' + row['customerName'][:60] + '".'}
    return {**row, 'status': 'new', 'customerId': customer['id']}


def classify_payment(doc, row, choices):
    """New, unchanged, conflict or (ambiguous) unresolved for one payment row of a known customer."""
    if row.get('customerId') is None:
        return
    mine = [p for p in doc.get('payments', []) if active(p) and p['customerId'] == row['customerId']]
    v, choice = row['values'], choices.get(str(row['row']))
    match = next((p for p in mine if p.get('sourceKey') == row['sourceKey']), None)
    if match is None and v['reference'] and choice != 'distinct':
        match = next((p for p in mine if p.get('reference') and ref_key(p['reference']) == ref_key(v['reference'])), None)
    if match is None and not v['reference']:
        alike = next((p for p in mine if p['receivedDate'] == v['receivedDate'] and p['amount'] == v['amount']), None)
        if alike and choice == 'same':
            match = alike
        elif alike and choice == 'skip':
            row.update({'status': 'leftOut', 'reason': 'Left out by a person.'})
            return
        elif alike and choice != 'distinct':
            row.update({'status': 'unresolved', 'review': 'possibleDuplicate', 'matchId': alike['id'], 'reason': 'A payment of this customer with the '
                        'same date and amount is already recorded (' + describe(alike.get('setBy') or alike.get('origin')) + '). Same payment, or a different one?'})
            return
    if match is None:
        row['status'] = 'new'
        return
    current = {k: match.get(k) for k in ('receivedDate', 'amount', 'reference')}
    differs = [k for k in ('receivedDate', 'amount') if current[k] != v[k]]
    corrected = (match.get('setBy') or {}).get('kind') == 'correction'
    row.update({'paymentId': match['id'], 'current': current, 'conflictFields': differs, 'correctedByPerson': corrected,
                'status': 'conflict' if differs else 'unchanged'})


def invoice_key(reference):
    """Invoice numbers compare without surrounding or inner spaces, case, or leading zeros of each run of digits: '35', '035' and
    '00000035' are one number, and so are 'hd-007' and 'HD-7'. An alphabetic prefix is kept as written: 'HD73' is not '73' (a prefix
    the other side lacks is a different number, never a guess)."""
    return re.sub(r'\d+', lambda m: m.group().lstrip('0') or '0', ref_key(reference))


def find_invoice(doc, customer_id, number, received=None):
    """(the invoice, None) of this customer that a payment's invoice number names, else (None, why): 'ambiguous' when the number
    reads as two of the customer's invoices, 'issuedAfter' when it names only invoices issued after the payment was received (a
    payment cannot pay an invoice that did not exist yet), 'otherCustomer' when only another customer has it, else 'notInFile'. The
    number as written (case and spaces aside) wins over the normalised reading when it names one invoice. received: the payment's
    date (ISO); an invoice issued after it is not a match."""
    mine = [i for i in doc['invoices'] if active(i) and i['customerId'] == customer_id]
    later = lambda i: bool(received) and bool(i.get('issueDate')) and i['issueDate'] > received
    same_all = [i for i in mine if ref_key(i['reference']) == ref_key(number)]
    close_all = [i for i in mine if invoice_key(i['reference']) == invoice_key(number)]
    same, close = [i for i in same_all if not later(i)], [i for i in close_all if not later(i)]
    if len(same) == 1:
        return same[0], None
    if len(close) == 1:
        return close[0], None
    if close or len(same) > 1:
        return None, 'ambiguous'
    if close_all or same_all:
        return None, 'issuedAfter'
    if any(active(i) and i['customerId'] != customer_id and invoice_key(i['reference']) == invoice_key(number) for i in doc['invoices']):
        return None, 'otherCustomer'
    return None, 'notInFile'


def plan_allocation(doc, row, planned):
    """An explicit allocation from the file's invoice column: only to an invoice of the same customer, only what is left on it
    and on the payment. The rest stays unallocated, and nothing is allocated across customers or by guesswork."""
    if row['status'] not in ('new', 'unchanged') or not row.get('invoiceNumber'):
        return
    if row.get('customerId') is None:
        row['unmatched'] = 'notInFile'
        row['allocationNote'] = 'The customer is new, so it has no invoices yet; the payment stays unallocated.'
        return
    invoice, why = find_invoice(doc, row['customerId'], row['invoiceNumber'], row['values']['receivedDate'])
    if invoice is None:
        row['unmatched'] = why
        if why == 'issuedAfter':
            named = next((i['reference'] for i in doc['invoices'] if active(i) and i['customerId'] == row['customerId'] and invoice_key(i['reference']) == invoice_key(row['invoiceNumber'])), row['invoiceNumber'])
            row['allocationNote'] = 'This payment names invoice ' + named + ', issued after this payment; left unmatched.'
        else:
            row['allocationNote'] = ('Invoice ' + row['invoiceNumber'] + ' could be more than one invoice of this customer; the payment stays unallocated.'
                                     if why == 'ambiguous' else 'Invoice ' + row['invoiceNumber'] +
                                     ' is not an invoice of this customer in the records; the payment stays unallocated.')
        return
    existing = row.get('paymentId')
    if existing and any(active(a) and a['paymentId'] == existing and a['invoiceId'] == invoice['id'] for a in doc.get('allocations', [])):
        return   # already allocated there
    received = row['values']['receivedDate']
    left_on_payment = minor(row['values']['amount']) - (allocated_from(doc, existing) if existing else 0)
    left_on_invoice = allocation_room(doc, invoice, received, planned.get(invoice['id'], ())) or 0
    amount = min(left_on_payment, left_on_invoice)
    if amount <= 0:
        row['allocationNote'] = 'Invoice ' + invoice['reference'] + ' has nothing left to allocate; the payment stays unallocated.'
        return
    planned.setdefault(invoice['id'], []).append((amount, received))
    rest = left_on_payment - amount
    row['allocation'] = {'invoiceId': invoice['id'], 'reference': invoice['reference'], 'amount': amount_of(row['values']['amount'], amount),
                         'note': money_text_plain(amount_of(row['values']['amount'], rest)) + ' stays unallocated.' if rest > 0 else None}
    if row['status'] == 'unchanged':
        row['status'] = 'updated'   # the payment is known; the file adds its allocation


def apply_payments(doc, batch, result, new_id, set_by):
    require(result['ready'], 409, 'NOT_READY', 'The preview still needs: ' + ' '.join(result['needs']))
    resolutions = batch['params'].get('resolutions') or {}
    created_customers, created_payments, created_allocations, versions, confirmed, aliases, affected = {}, [], [], [], [], [], set()
    for choice in result['customers']:
        if choice['resolution'] not in (None, 'new', 'skip'):
            customer = next(c for c in doc['customers'] if c['id'] == choice['resolution'])
            customer['aliases'] = customer.get('aliases', []) + [choice['name']]
            aliases.append({'customerId': customer['id'], 'alias': choice['name']})
    for row in result['rows']:
        at = {**set_by, 'row': row['row']}
        if row['status'] == 'new':
            customer_id = row.get('customerId')
            if customer_id is None:
                key = name_key(row['customerName'])
                if created_customers.get(key) is None:
                    created_customers[key] = new_customer(doc, {'name': row['customerName']}, new_id('customer'), at)['id']
                customer_id = created_customers[key]
            payment = {'id': new_id('payment'), 'customerId': customer_id, **row['values'], 'sourceKey': row['sourceKey'], 'status': 'active',
                       'version': 1, 'origin': at, 'setBy': at, 'history': []}
            doc.setdefault('payments', []).append(payment)
            created_payments.append(payment['id'])
            payment_id = payment['id']
        elif row['status'] in ('unchanged', 'updated'):
            payment = next(p for p in doc['payments'] if p['id'] == row['paymentId'])
            payment['confirmedBy'] = payment.get('confirmedBy', []) + [batch['id']]
            confirmed.append(payment['id'])
            payment_id = payment['id']
        elif row['status'] == 'conflict':
            payment = next(p for p in doc['payments'] if p['id'] == row['paymentId'])
            if resolutions.get('conflicts', {}).get(str(row['row'])) == 'take':
                require(minor(row['values']['amount']) >= allocated_from(doc, payment['id']), 409, 'ALLOCATED', 'Row ' + str(row['row']) +
                        ': more than the file\'s amount is already allocated from this payment. Keep the recorded value, or remove allocations first.')
                set_version(payment, 'payments', {k: row['values'][k] for k in ('receivedDate', 'amount', 'reference')}, at)
                versions.append({'paymentId': payment['id'], 'version': payment['version']})
                affected |= {a['invoiceId'] for a in doc.get('allocations', []) if active(a) and a['paymentId'] == payment['id']}
            else:   # the file disagreed and a person kept the recorded value
                payment['confirmedBy'] = payment.get('confirmedBy', []) + [batch['id']]
                payment['disputedBy'] = payment.get('disputedBy', []) + [batch['id']]
                confirmed.append(payment['id'])
            continue
        else:
            continue
        if row.get('allocation'):
            allocation = {'id': new_id('allocation'), 'paymentId': payment_id, 'invoiceId': row['allocation']['invoiceId'],
                          'customerId': next(p['customerId'] for p in doc['payments'] if p['id'] == payment_id), 'amount': row['allocation']['amount'],
                          'status': 'active', 'version': 1, 'origin': at, 'setBy': at, 'history': []}
            doc.setdefault('allocations', []).append(allocation)
            created_allocations.append(allocation['id'])
            affected.add(allocation['invoiceId'])
    return {'shape': 'payments', 'customers': [c for c in created_customers.values() if c], 'payments': created_payments,
            'allocations': created_allocations, 'versions': versions, 'confirmed': confirmed, 'aliases': aliases}, affected


def opening_preview(doc, header, rows, params, settings, today):
    """One row per customer: an opening balance as at a date. A customer who already has one keeps it: the same figure is
    unchanged, a different one is refused (it is corrected on the Records page)."""
    mapping, resolutions = params.get('mapping') or {}, params.get('resolutions') or {}
    missing = validate_mapping(header, mapping, 'openings')
    result = {'shape': 'openings', 'dateOrder': 'ymd', 'asOf': None, 'needs': ['Choose a column for: ' + ', '.join(missing) + '.'] if missing else [],
              'rows': [], 'customers': [], 'ready': False, 'coverage': None,
              'counts': {k: 0 for k in ('new', 'unchanged', 'updated', 'conflict', 'rejected', 'unresolved', 'leftOut')}}
    if missing:
        return result
    known, unknown, seen = customer_index(doc), {}, set()
    for number, cells in rows:
        def cell(field):
            return cells[mapping[field]].strip() if field in mapping and mapping[field] < len(cells) else ''
        row = {'row': number, 'customerName': cell('customer'), 'reference': None, 'values': None}
        on, direction = parse_date_cell(cell('asOf'), 'ymd'), cell('direction') or 'owed'
        try:
            amount = parse_amount_cell(cell('amount'), settings, 'amount')
        except RecordsError as exc:
            amount = None
            row.update({'status': 'rejected', 'reason': 'Amount "' + cell('amount')[:30] + '": ' + exc.message})
        if row.get('status'):
            pass
        elif not row['customerName']:
            row.update({'status': 'rejected', 'reason': 'No customer name.'})
        elif not on or on > today.isoformat():
            row.update({'status': 'rejected', 'reason': 'The as-at date is not a date on or before today.'})
        elif minor(amount) <= 0 or direction not in ('owed', 'credit'):
            row.update({'status': 'rejected', 'reason': 'The opening balance must be more than zero, owed or in credit.'})
        elif name_key(row['customerName']) in seen:
            row.update({'status': 'rejected', 'reason': 'This customer has more than one opening balance in the file.'})
        else:
            seen.add(name_key(row['customerName']))
            row['values'] = {'asOf': on, 'amount': amount_of(amount, minor(amount) if direction == 'owed' else -minor(amount)), 'direction': direction}
            key = name_key(row['customerName'])
            customer = known.get(key)
            if customer is None:
                unknown.setdefault(key, row['customerName'])
                choice = resolutions.get('customers', {}).get(key)
                customer = next((c for c in doc['customers'] if c['id'] == choice and active(c)), None) if choice not in (None, 'new', 'skip') else None
                if choice == 'skip':
                    row.update({'status': 'leftOut', 'reason': 'Left out: customer not created.'})
                elif choice == 'new':
                    row.update({'status': 'new', 'customerId': None})
                elif customer is None:
                    row.update({'status': 'unresolved', 'reason': 'Unknown customer "' + row['customerName'][:60] + '".'})
            if customer is not None:
                existing = opening_of(doc, customer['id'])
                row['customerId'] = customer['id']
                if existing is None:
                    row['status'] = 'new'
                elif (existing['asOf'], existing['amount']) == (on, row['values']['amount']):
                    row.update({'status': 'unchanged', 'openingId': existing['id']})
                else:
                    row.update({'status': 'rejected', 'reason': 'This customer already has a different opening balance; correct it on the Records page.'})
        result['rows'].append(row)
        result['counts'][row['status']] += 1
    names = {c['name'] for c in doc['customers'] if active(c)}
    for key, name in unknown.items():
        result['customers'].append({'key': key, 'name': name, 'resolution': resolutions.get('customers', {}).get(key),
                                    'suggestions': get_close_matches(name, sorted(names), n=3, cutoff=0.6)})
    unresolved = [c['name'] for c in result['customers'] if not c['resolution']]
    if unresolved:
        result['needs'].append('Create or choose a customer for: ' + ', '.join(unresolved) + '.')
    result['ready'] = not result['needs'] and any(r['status'] in ('new', 'unchanged') for r in result['rows'])
    return result


def apply_openings(doc, batch, result, new_id, set_by):
    require(result['ready'], 409, 'NOT_READY', 'The preview still needs: ' + ' '.join(result['needs']))
    created_customers, created = {}, []
    for choice in result['customers']:
        if choice['resolution'] not in (None, 'new', 'skip'):
            customer = next(c for c in doc['customers'] if c['id'] == choice['resolution'])
            customer['aliases'] = customer.get('aliases', []) + [choice['name']]
    for row in result['rows']:
        if row['status'] != 'new':
            continue
        at, customer_id = {**set_by, 'row': row['row']}, row.get('customerId')
        if customer_id is None:
            key = name_key(row['customerName'])
            if created_customers.get(key) is None:
                created_customers[key] = new_customer(doc, {'name': row['customerName']}, new_id('customer'), at)['id']
            customer_id = created_customers[key]
        v = row['values']
        opening = new_opening(doc, {'customerId': customer_id, 'asOf': v['asOf'], 'direction': v['direction'], 'sourceLabel': set_by.get('sourceLabel') or 'Imported ledger',
                                    'amount': money_text_plain(amount_of(v['amount'], abs(minor(v['amount']))))},
                              {'currency': v['amount']['currency'], 'scale': v['amount']['scale']}, date.fromisoformat(set_by['at'][:10]), new_id('opening'), at)
        created.append(opening['id'])
    return {'shape': 'openings', 'customers': [c for c in created_customers.values() if c], 'openings': created, 'aliases': [], 'versions': [], 'confirmed': []}, set()


def opening_revert_impact(doc, batch, cases_about, batch_of=lambda batch_id: None):
    changes, blocked, revert = batch['result'], [], []
    for opening_id in changes['openings']:
        opening = next(o for o in doc['openingBalances'] if o['id'] == opening_id)
        if not active(opening):
            continue
        if (opening.get('setBy') or {}).get('batchId') != batch['id'] or opening['version'] != 1:
            blocked.append('The opening balance was changed afterwards (' + describe(opening['setBy']) + '). Undo that first.')
        else:
            revert.append(opening_id)
    for customer_id in changes['customers']:
        customer = next(c for c in doc['customers'] if c['id'] == customer_id)
        if active(customer) and any(r['customerId'] == customer_id and active(r) for r in doc['invoices'] + doc.get('payments', [])):
            blocked.append('Customer ' + customer['name'] + ' has records from elsewhere now.')
    review = {'pendingCases': [], 'decidedCases': [], 'answers': []}
    return {'blocked': blocked, 'review': review, 'revertOpenings': revert, 'keep': [], 'restore': [], 'needsReview': False}


def opening_revert(doc, batch, impact, set_by):
    require(not impact['blocked'], 409, 'REVERT_BLOCKED', 'This import cannot be reverted yet.')
    for opening in doc.get('openingBalances', []):
        if opening['id'] in impact['revertOpenings']:
            opening.update({'status': 'reverted', 'reverted': set_by})
    for customer_id in batch['result']['customers']:
        customer = next(c for c in doc['customers'] if c['id'] == customer_id)
        if not any(r.get('customerId') == customer_id and active(r) for r in doc['invoices'] + doc.get('payments', [])):
            customer.update({'status': 'reverted', 'reverted': set_by})
    return set(), set()


def payment_revert_impact(doc, batch, cases_about, batch_of=lambda batch_id: None):
    changes, bid = batch['result'], batch['id']
    mine = set(changes['allocations'])
    blocked, revert_payments, keep, restore = [], [], [], []
    allocations = [a for a in doc.get('allocations', []) if active(a)]
    for payment_id in changes['payments'] + credited(doc, 'payments', bid, changes):
        payment = next(p for p in doc['payments'] if p['id'] == payment_id)
        if not active(payment):
            continue
        later = [b for b in payment.get('confirmedBy', []) if b != bid]
        others = [a for a in allocations if a['paymentId'] == payment_id and a['id'] not in mine]
        label = payment['receivedDate'] + ' ' + payment['amount']['currency'] + ' ' + money_text_plain(payment['amount'])
        if (payment.get('setBy') or {}).get('batchId') != bid:
            blocked.append('Payment ' + label + ' was changed afterwards (' + describe(payment['setBy']) + '). Undo that first.')
        elif others:
            refs = ', '.join(next(i['reference'] for i in doc['invoices'] if i['id'] == a['invoiceId']) for a in others)
            blocked.append('Payment ' + label + ' has money allocated after the import (' + refs + '). Remove those allocations first.')
        elif later:
            supporters = [b for b in later if supports(payment, batch_of(b))]
            if supporters:
                keep.append((payment_id, supporters[-1]))
            else:
                blocked.append(unsupported('Payment ' + label + (' (' + payment['reference'] + ')' if payment.get('reference') else ''), payment, later, batch_of))
        else:
            revert_payments.append(payment_id)
    for v in changes['versions']:
        payment = next(p for p in doc['payments'] if p['id'] == v['paymentId'])
        if active(payment) and payment['version'] != v['version']:
            blocked.append('A payment this import changed was changed again afterwards (' + describe(payment['setBy']) + '). Undo that first.')
        elif active(payment):
            restore.append(v['paymentId'])
    kept = {payment_id for payment_id, _ in keep}
    revert_allocations = [a['id'] for a in allocations if a['id'] in mine and a['paymentId'] not in kept]
    for customer_id in changes['customers']:
        customer = next(c for c in doc['customers'] if c['id'] == customer_id)
        if not active(customer):
            continue
        others = [i['reference'] for i in doc['invoices'] if i['customerId'] == customer_id and active(i)]
        others += [p['id'] for p in doc.get('payments', []) if p['customerId'] == customer_id and active(p) and p['id'] not in revert_payments and p['id'] not in kept]
        if others or opening_of(doc, customer_id):
            blocked.append('Customer ' + customer['name'] + ' has records from elsewhere now.')
    review = {'pendingCases': [], 'decidedCases': [], 'answers': []}
    for invoice_id in {a['invoiceId'] for a in allocations if a['id'] in revert_allocations}:
        pending, decided = cases_about(invoice_id)
        review['pendingCases'] += pending
        review['decidedCases'] += decided
        invoice = next(i for i in doc['invoices'] if i['id'] == invoice_id)
        review['answers'] += answered(doc, invoice, [a for a in allocations if a['id'] in revert_allocations and a['invoiceId'] == invoice_id])
    review['answers'] += inclusion_answered(doc, [p for p in doc.get('payments', []) if p['id'] in revert_payments])
    return {'blocked': blocked, 'review': review, 'revertPayments': revert_payments, 'revertAllocations': revert_allocations, 'keep': keep,
            'restore': restore, 'needsReview': any(review.values())}


def payment_revert(doc, batch, impact, set_by):
    require(not impact['blocked'], 409, 'REVERT_BLOCKED', 'This import cannot be reverted yet.')
    bid, affected = batch['id'], set()
    for allocation in doc.get('allocations', []):
        if allocation['id'] in impact['revertAllocations']:
            allocation.update({'status': 'reverted', 'reverted': set_by})
            affected.add(allocation['invoiceId'])
    for payment in doc.get('payments', []):
        if payment['id'] in impact['revertPayments']:
            payment.update({'status': 'reverted', 'reverted': set_by})
        if bid in payment.get('confirmedBy', []):
            payment['confirmedBy'] = [b for b in payment['confirmedBy'] if b != bid]
        if bid in payment.get('disputedBy', []):
            payment['disputedBy'] = [b for b in payment['disputedBy'] if b != bid]
    for payment_id, later in impact['keep']:
        payment = next(p for p in doc['payments'] if p['id'] == payment_id)
        payment['setBy'] = {**payment['setBy'], 'batchId': later, 'note': 'confirmed by a later import; kept when ' + bid + ' was reverted'}
    for payment_id in impact['restore']:
        payment = next(p for p in doc['payments'] if p['id'] == payment_id)
        previous = payment['history'][-1]
        set_version(payment, 'payments', previous['values'], set_by)
        payment['setBy'] = {**previous['setBy'], 'restoredBy': set_by}
        affected |= {a['invoiceId'] for a in doc.get('allocations', []) if active(a) and a['paymentId'] == payment_id}
    for customer_id in batch['result']['customers']:
        customer = next(c for c in doc['customers'] if c['id'] == customer_id)
        if not any(r.get('customerId') == customer_id and active(r) for r in doc['invoices'] + doc.get('payments', [])):
            customer.update({'status': 'reverted', 'reverted': set_by})
    for alias in batch['result']['aliases']:
        customer = next(c for c in doc['customers'] if c['id'] == alias['customerId'])
        customer['aliases'] = [a for a in customer.get('aliases', []) if a != alias['alias']]
    return affected, set()


APPLY = {'payments': apply_payments, 'openings': apply_openings}   # by a batch's shape; the invoices batch is apply
REVERT_IMPACT = {'payments': payment_revert_impact, 'openings': opening_revert_impact}
REVERT = {'payments': payment_revert, 'openings': opening_revert}


# ---------------------------------------------------------------- import proposals (agent-assisted import, plan 2026-10-21)
# A proposal reads a whole file: it finds the heading row below any title rows, works out what the file lists (invoices, payments
# received, or a ledger of both), maps each field to a column by its heading (or by the model's reading of a column no heading names,
# checked against the data), and turns the rows into invoices and payments. Those are imported through the importer's own shapes
# (derived), previewed against the records first (dry_run). The model never sees more than the headings and three sample rows.

CODES = ('customer id', 'customer code', 'customer no', 'ma khach hang', 'ma kh', 'ma doi tuong', 'doi tuong')
TERMS = ('credit term days', 'credit term', 'credit terms', 'credit days', 'payment terms', 'terms', 'term days', 'so ngay no', 'thoi han no',
         'han no', 'so ngay duoc no')
LEDGER_FIELDS = ('customer', 'invoiceNumber', 'issueDate', 'paymentDate', 'reference', 'debit', 'credit', 'creditDays', 'dueDate', 'description',
                 'mentioned', 'customerCode', 'recordType', 'transactionType', 'outstanding', 'advance')
LEDGER_REQUIRED = ('customer', 'invoiceNumber', 'paymentDate', 'debit', 'credit')
LEDGER_LABELS = {'customer': 'Customer', 'invoiceNumber': 'Invoice number', 'issueDate': 'Invoice date', 'paymentDate': 'Posting or document date',
                 'reference': 'Document number', 'debit': 'Debit', 'credit': 'Credit', 'creditDays': 'Credit term (days)', 'dueDate': 'Due date',
                 'description': 'Description', 'mentioned': 'Invoice a payment names', 'customerCode': 'Customer code', 'recordType': 'Record type', 'transactionType': 'Transaction type',
                 'outstanding': 'Amount owed (opening balances)', 'advance': 'Amount held in advance (opening balances)'}
LEDGER_SYNONYMS = {   # in order of preference: a document (receipt) date before a posting date
    'customer': SYNONYMS['customer'] + CODES,
    'invoiceNumber': ('invoice number', 'invoice no', 'invoice num', 'invoice', 'inv no', 'so hoa don', 'hoa don'),
    'issueDate': ('invoice date', 'ngay hoa don'),
    'paymentDate': ('document date', 'ngay chung tu', 'posting date', 'ngay hach toan', 'ngay ghi so', 'transaction date', 'date', 'ngay'),
    'reference': ('document number', 'document no', 'so chung tu', 'voucher number', 'voucher no', 'reference', 'ref'),
    'debit': ('debit dr', 'debit', 'dr', 'debit amount', 'phat sinh no', 'ps no', 'so tien no', 'no'),
    'credit': ('credit cr', 'credit', 'cr', 'credit amount', 'phat sinh co', 'ps co', 'so tien co', 'co'),
    'creditDays': TERMS,
    'dueDate': SYNONYMS['dueDate'] + ('ngay den han',),
    'description': ('description', 'narration', 'details', 'dien giai', 'noi dung', 'ly do'),
    'mentioned': ('invoice reference mentioned', 'invoice mentioned', 'invoice named'),
    'recordType': ('record type', 'loai ban ghi'),
    'transactionType': ('transaction type', 'loai giao dich'),
    'outstanding': ('outstanding debt', 'amount outstanding', 'du no'),
    'advance': ('advance payment', 'thanh toan truoc'),
    'customerCode': CODES,   # taken only when the customer column is a name: the code then becomes an alias
}
PROPOSAL_SHAPES = {   # fields, required, labels, synonyms
    'invoices': (FIELDS[:5] + ('creditDays',), REQUIRED, {**LABELS, 'creditDays': LEDGER_LABELS['creditDays']},
                 {**SYNONYMS, 'customer': SYNONYMS['customer'] + CODES, 'creditDays': TERMS}),
    'payments': (PAYMENT_FIELDS, PAYMENT_REQUIRED, PAYMENT_LABELS, {**PAYMENT_SYNONYMS, 'customer': SYNONYMS['customer'] + CODES}),
    'ledger': (LEDGER_FIELDS, LEDGER_REQUIRED, LEDGER_LABELS, LEDGER_SYNONYMS),
}
PROPOSAL_FIELDS = tuple(dict.fromkeys(f for shape in PROPOSAL_SHAPES.values() for f in shape[0]))
HEADINGS = {name for shape in PROPOSAL_SHAPES.values() for names in shape[3].values() for name in names}
HINTS = ('shape', 'sheet', 'mapping', 'customerPrefix', 'creditDays', 'dateOrder', 'customers', 'sourceLabel')
DATE_FIELDS, MONEY_FIELDS = ('issueDate', 'paymentDate', 'dueDate'), ('amount', 'debit', 'credit', 'outstanding', 'advance')
MISFIT = {'date': 'its values are not dates', 'money': 'its values are not amounts', 'days': 'its values are not numbers of days', 'text': 'the column is empty'}
CODE = re.compile(r'[A-Za-z]{0,6}[-_.]?\d{1,12}')   # a customer code: 0001, KH001, C-12
DATE_HEADING = re.compile(r'\b(?:date|dated|due|ngay|han)\b')   # a heading, as name_key gives it, that names a date
SERIALS = (32874, 73415)   # Excel serial days from 1 Jan 1990 to 31 Dec 2100
NO_CUSTOMER = 'No customer on this row (an opening balance, a total or a heading?); left out.'
INVOICE_HEADER = ('Customer', 'Invoice number', 'Invoice date', 'Invoice amount', 'Due date', 'Rows in the file')
PAYMENT_HEADER = ('Customer', 'Date received', 'Amount received', 'Payment reference', 'Invoice it pays', 'Row in the file')
OPENING_HEADER = ('Customer', 'As at', 'Opening balance', 'Owed or in credit', 'Row in the file')
WRITES = ('new', 'updated', 'conflict', 'unchanged')   # preview statuses an apply writes or confirms
# A flag's reason never quotes the file (the model may read it); the importer's own reason is the card's detail.
REVIEWED = {'rejected': 'The importer would not accept this row; left out.',
            'conflict': 'It differs from what the records hold; a person chooses on the Records import page.',
            'unresolved': 'It needs a choice this proposal cannot make (a customer, or a payment that may repeat one); a person chooses on the '
                          'Records import page.'}


def check_hints(value):
    """A person's hints or corrections for a proposal, checked for their form: shape, sheet, mapping {field: a column (its number
    from 0, its letter or its heading) or null for none}, customerPrefix, creditDays (0 to 365), dateOrder, customers {name key:
    'new', 'skip' or a customerId}, sourceLabel. Empty values are left out. Whether a field and a column exist is checked by propose."""
    v = value if value is not None else {}
    text = lambda x, limit: x is None or isinstance(x, str) and len(x.strip()) <= limit
    ok = (isinstance(v, dict) and set(v) <= set(HINTS) and v.get('shape') in (None, *PROPOSAL_SHAPES) and text(v.get('sheet'), 120)
          and isinstance(v.get('mapping') or {}, dict) and all(isinstance(f, str) and (c is None or type(c) is int or text(c, 120))
                                                              for f, c in (v.get('mapping') or {}).items())
          and text(v.get('customerPrefix'), 40) and (v.get('creditDays') is None or type(v['creditDays']) is int and 0 <= v['creditDays'] <= 365)
          and v.get('dateOrder') in (None, 'dmy', 'mdy', 'ymd') and isinstance(v.get('customers') or {}, dict)
          and all(isinstance(k, str) and isinstance(c, str) and 0 < len(c) <= 80 for k, c in (v.get('customers') or {}).items())
          and text(v.get('sourceLabel'), 80))
    require(ok, 400, 'INVALID_ARGUMENT', 'hints: shape (invoices, payments or ledger), sheet, mapping {field: column number from 0, letter or heading, '
            'or null}, customerPrefix, creditDays (0 to 365), dateOrder (dmy, mdy or ymd), customers {name: new, skip or a customerId}, sourceLabel.', 'hints')
    return {k: x.strip() if isinstance(x, str) else x for k, x in v.items() if x is not None and (k != 'sourceLabel' or x.strip())}


def revised(base, corrections):
    """The hints of a proposal's next version: its own, with the person's corrections on top. The columns the earlier version
    mapped stay mapped (and who mapped each), unless the sheet or the shape changes or a correction takes the column."""
    old, view = base['hints'], base['view']
    hints = {**old, **{k: v for k, v in corrections.items() if k not in ('mapping', 'customers')}}
    hints['customers'] = {**old.get('customers', {}), **corrections.get('customers', {})}
    same = hints.get('shape', view['shape']) == view['shape'] and hints.get('sheet', view['sheet']) == view['sheet']

    def index(ref):   # a letter or heading as its column number, to see which earlier field it takes; propose refuses one not in the file
        try:
            return column_of(view['columns'], ref) if same and ref is not None else ref
        except RecordsError:
            return ref
    new = {f: index(c) for f, c in corrections.get('mapping', {}).items()}
    kept = [m for m in view['mapping'] if same and m['by'] and m['field'] not in new and m['column'] not in new.values()]
    hints['mapping'] = {**{m['field']: m['column'] for m in kept}, **new}
    hints['mappedBy'] = {**{m['field']: m['by'] for m in kept}, **{f: 'person' for f in new}}
    return hints


def sheets_of(file):
    """{sheet name: its non-blank rows, numbered}: {None: rows} for CSV text, or an attachment's (an .xlsx workbook, or CSV in
    UTF-8 or in UTF-16 with its byte-order mark)."""
    if file.get('csvText') is not None:
        return {None: read_rows(file['csvText'])}
    data = base64.b64decode(file['fileBase64'])
    if data[:4] == b'PK\x03\x04':
        return {name: [(n, cells) for n, cells in enumerate(rows, start=1) if any(c.strip() for c in cells)]
                for name, rows in xlsx.read_workbook(data).items()}
    try:
        text = data.decode('utf-16') if data[:2] in (b'\xff\xfe', b'\xfe\xff') else data.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise RecordsError(400, 'INVALID_FILE', 'Save the file as .xlsx, or as CSV in UTF-8, and try again.', 'fileBase64') from None
    return {None: read_rows(text)}


def heading_score(cells):
    return sum(name_key(c) in HEADINGS for c in cells)


def header_of(rows):
    """(row number, cells) of the heading row: the first of the first 30 rows with at least 3 filled cells, 2 of them known
    headings; else the first row."""
    return next((r for r in rows[:30] if sum(bool(c.strip()) for c in r[1]) >= 3 and heading_score(r[1]) >= 2), rows[0])


def sheet_score(rows):
    """(score, header row number) for a sheet's rows: its mapped required fields, half a point per optional one, and one more
    for a ledger (both a debit and a credit column); (0, None) when no row qualifies as a heading row."""
    if not rows:
        return 0, None
    number, header = header_of(rows)
    if heading_score(header) < 2:
        return 0, None
    shape = detect_shape(header)
    found = match(header, shape, (), ())
    required = PROPOSAL_SHAPES[shape][1]
    return sum(f in required for f in found) + 0.5 * sum(f not in required for f in found) + (shape == 'ledger'), number


def sheet_scores(sheets):
    """[{name, score, headerRow}] for the named sheets of a workbook ([] for CSV)."""
    return [{'name': name, 'score': sheet_score(rows)[0], 'headerRow': sheet_score(rows)[1]} for name, rows in sheets.items() if name is not None]


def pick_sheet(sheets, wanted):
    """The sheet to read: the one asked for, else the best scoring (sheet_score), the earliest on a tie."""
    if list(sheets) == [None]:
        return None
    if wanted is not None:
        require(wanted in sheets, 400, 'INVALID_ARGUMENT', 'The workbook has no sheet "' + wanted[:60] + '"; its sheets: ' + ', '.join(sheets) + '.', 'sheet')
        return wanted
    named = [s for s in sheets if sheets[s]]
    require(named, 400, 'INVALID_FILE', 'The workbook has no rows.', 'fileBase64')
    return max(named, key=lambda s: sheet_score(sheets[s])[0])


def match(header, shape, taken, chosen):
    """{field: column} for the fields (not chosen by the person) whose heading is a known name for them: each column once, the
    preferred name first."""
    fields, _, _, synonyms = PROPOSAL_SHAPES[shape]
    keys, found, used = [name_key(h) for h in header], {}, set(taken)
    for field in (f for f in fields if f not in chosen):
        column = next((i for name in synonyms[field] for i, k in enumerate(keys) if k == name and i not in used), None)
        if column is not None:
            found[field] = column
            used.add(column)
    return found


def detect_shape(header):
    """'ledger' when debit and credit columns are named; else invoices or payments: of those whose required columns are all
    named (else of both), the one with more of its fields named, invoices on a tie. A payment list naming the invoice each pays
    has an invoice list's columns too; its reference column tells it apart."""
    found = {shape: match(header, shape, (), ()) for shape in PROPOSAL_SHAPES}
    if {'debit', 'credit'} <= set(found['ledger']):
        return 'ledger'
    complete = [s for s in ('invoices', 'payments') if set(PROPOSAL_SHAPES[s][1]) <= set(found[s])]
    return max(complete or ('invoices', 'payments'), key=lambda s: len(found[s]))


def column_of(header, ref):
    """A column a person named: its number from 0, its heading, or its letter (A, B, …)."""
    keys = [name_key(h) for h in header]
    if type(ref) is int and 0 <= ref < len(header):
        return ref
    if isinstance(ref, str) and name_key(ref) in keys:
        return keys.index(name_key(ref))
    if isinstance(ref, str) and re.fullmatch(r'[A-Za-z]{1,2}', ref):
        n = 0
        for ch in ref.upper():
            n = n * 26 + ord(ch) - 64
        if n <= len(header):
            return n - 1
    raise RecordsError(400, 'INVALID_ARGUMENT', 'Column ' + str(ref)[:40] + ' is not in the file; give its number from 0, its letter or its heading.', 'hints')


def excel_day(text):
    """An Excel serial day number (1900 date system) in a plausible range, as YYYY-MM-DD; else None. shortcut: a 1904-system
    workbook's dates are read right only when their cells are formatted as dates (xlsx reads those); upgrade if one turns up."""
    if not re.fullmatch(r'\d{5}(?:\.\d+)?', text):
        return None
    days = int(float(text))
    return (date(1899, 12, 30) + timedelta(days=days)).isoformat() if SERIALS[0] <= days <= SERIALS[1] else None


def is_date_column(values, heading):
    """Every value filled in is a date: written (day/month or month/day) or, under a heading that names a date, an Excel serial
    day. A column with anything else in it is not a date column."""
    serials, filled = bool(DATE_HEADING.search(name_key(heading))), [v for v in values if v]
    return bool(filled) and all(parse_date_cell(v, 'dmy') or parse_date_cell(v, 'mdy') or serials and excel_day(v) for v in filled)


def column_dates(values, heading, order):
    """Each value as YYYY-MM-DD, '' when blank, None when it is not a date. Serial numbers are dates only in a date column."""
    serials = is_date_column(values, heading)
    return [(parse_date_cell(v, order) or (excel_day(v) if serials else None)) if v else '' for v in values]


def amount_cell(text, settings):
    """An amount of more than zero, None when blank or zero; RecordsError when it is not an amount."""
    amount = parse_amount_cell(text, settings, 'amount') if text else None
    return amount if amount and minor(amount) > 0 else None


def kind_of(field):
    return 'date' if field in DATE_FIELDS else 'money' if field in MONEY_FIELDS else 'days' if field == 'creditDays' else 'text'


def fits(field, values, heading, settings):
    """Whether a column's data is what the field needs: dates, amounts, whole numbers of days, or anything filled in."""
    filled, kind = [v for v in values if v], kind_of(field)
    if kind == 'date':
        return is_date_column(values, heading)
    if kind == 'days':
        return bool(filled) and all(re.fullmatch(r'\d{1,3}', v) and int(v) <= 365 for v in filled)
    if kind == 'money':
        try:
            return bool(filled) and all(parse_amount_cell(v, settings, field) for v in filled)
        except RecordsError:
            return False
    return bool(filled)


VIET_HEADINGS = {'phat sinh no', 'phat sinh co', 'so chung tu', 'dien giai', 'ngay hach toan', 'ngay chung tu', 'so hoa don', 'ma khach hang',
                 'khach hang', 'so tien no', 'so tien co', 'ngay hoa don', 'ps no', 'ps co', 'so ngay no'}
CURRENCY_HEADINGS = {'currency', 'ccy', 'currency code', 'loai tien', 'tien te'}
UNIT_TOKEN = re.compile(r'(?<!\w)(VND|AUD|USD)(?!\w)|(?<!\w)([đĐ₫])(?!\w)|(\$)', re.I)


DOLLARS = ('AUD', 'USD', 'NZD', 'SGD', 'CAD', 'HKD')


def detect_unit(header, rows):
    """The money unit the file itself states: {detected: 'VND' | 'AUD' | ..., basis: words a person can read}. In order: a currency
    column whose values agree, a currency token in a heading (VND, USD, AUD, đ, ₫; "$" is 'dollar', fitting any of DOLLARS), Vietnamese ledger headings
    (VND); else detected is None. rows are the data rows' cells."""
    for i, h in enumerate(header):
        if name_key(h) in CURRENCY_HEADINGS:
            values = {cells[i].strip().upper() for cells in rows if i < len(cells) and cells[i].strip()}
            if len(values) == 1 and re.fullmatch(r'[A-Z]{3}', next(iter(values))):
                return {'detected': next(iter(values)), 'basis': 'the "' + h + '" column says ' + next(iter(values))}
    for h in header:
        m = UNIT_TOKEN.search(h)
        if m:
            if m.group(3):   # a dollar sign fits any dollar currency
                return {'detected': 'dollar', 'basis': 'a dollar sign in the headings'}
            code = 'VND' if m.group(2) else m.group(1).upper()
            return {'detected': code, 'basis': 'the heading "' + h + '" says ' + (code if m.group(1) else m.group(2))}
    if sum(name_key(h) in VIET_HEADINGS for h in header) >= 2:
        return {'detected': 'VND', 'basis': 'the headings are in Vietnamese'}
    return {'detected': None, 'basis': 'no heading or column in the file names a currency'}


def doubtful_unit(unit, entries, settings):
    """A file that names no unit, in a workspace with decimals, whose amounts are all whole numbers with a median of 10,000 or more
    looks like a zero-decimal currency: the unit is doubtful, and the file is not imported as if it were cents."""
    if unit['detected'] is not None or not settings['scale'] or not entries:
        return unit
    units = [minor(x['amount']) for x in entries]
    if all(m % 10 ** settings['scale'] == 0 for m in units) and median(units) >= 10_000 * 10 ** settings['scale']:
        return {'detected': None, 'doubtful': True, 'basis': 'whole numbers in the millions, no decimals'}
    return unit


def _fold(text):
    return ''.join(ch for ch in unicodedata.normalize('NFKD', str(text or '').casefold().replace('đ', 'd')) if not unicodedata.combining(ch))


_KEYWORD = r'(?<![a-z0-9])(?:so\s*hd|hoa\s*don|hd|invoice|inv)(?![a-z])(?:\s+so\b)?\s*(?:no\.?|number|#|:)?\s*'
_NUMBER = r'[a-z]{0,3}\d[\w./-]*'
_REFERENCE = re.compile(_KEYWORD + '(' + _NUMBER + r')((?:\s*(?:,|;|&|\+|\band\b|\bva\b)\s*' + _NUMBER + ')*)')


def _named_in(text):
    """The invoice numbers a text names after HĐ, hóa đơn (số), HD, invoice or inv, as written (a list or "12, 13" gives each)."""
    out = []
    for m in _REFERENCE.finditer(_fold(text)):
        out += [m.group(1)] + re.findall(_NUMBER, m.group(2))
    return [x.rstrip('.,;') for x in out]


def invoice_reference_from(description, reference_cell=''):
    """The invoice numbers a payment names: a reference cell first (a number, or words such as "HĐ 73"), else the description. A list:
    empty when none is named, more than one when it names several (such a payment is flagged, not allocated)."""
    cell = str(reference_cell or '').strip()
    if not cell:
        return _named_in(description)
    parts = re.split(r'\s*(?:,|;|&|\+)\s*', cell)   # "12,13": a list of bare numbers
    return _named_in(cell) or (parts if len(parts) > 1 and all(re.fullmatch(_NUMBER, x.lower()) for x in parts) else [cell])


def propose(rows, hints, classify, settings, today, others=None):
    """An import proposal for a file's non-blank rows [(row number, cells)]: the heading row (header_of), the shape (hints, else detect_shape), the column of each field (the person's first, then known
    headings, then, only while a required field is still missing, classify(header, three sample rows, fields) for the columns
    no heading names: an answer is used only if the column's data fits the field), the customer names (prefix and code when the
    customer column holds codes), the due dates (a due-date column, else a credit-term column, else hints.creditDays), and the
    invoices (a ledger's debit lines summed by invoice number) and payments (its credit rows), with the rows left out and why.
    classify may be None: then no model is asked. Counts are the code's. Nothing is written."""
    require(rows, 400, 'INVALID_FILE', 'The file has no rows.', 'file')
    number, header = header_of(rows)
    header = [c.strip() for c in header]
    require(len(header) <= MAX_COLUMNS, 400, 'INVALID_FILE', 'The file has more than ' + str(MAX_COLUMNS) + ' columns.', 'file')
    width = len(header)
    data = [(n, [c.strip() for c in cells] + [''] * (width - len(cells))) for n, cells in rows if n > number]
    require(data, 400, 'INVALID_FILE', 'The file needs a heading row and at least one row below it.', 'file')
    shape = hints.get('shape') or detect_shape(header)
    fields, required, labels, _ = PROPOSAL_SHAPES[shape]
    chosen = hints.get('mapping') or {}
    require(set(chosen) <= set(fields), 400, 'INVALID_ARGUMENT', 'A file of ' + shape + ' has no field ' + ', '.join(sorted(set(chosen) - set(fields))) + '.', 'hints')
    mapping = {f: column_of(header, c) for f, c in chosen.items() if c is not None}
    require(len(set(mapping.values())) == len(mapping), 400, 'INVALID_ARGUMENT', 'Each column can be used for one field only.', 'hints')
    by = {f: (hints.get('mappedBy') or {}).get(f, 'person') for f in chosen}
    for f, c in match(header, shape, mapping.values(), chosen).items():
        mapping[f], by[f] = c, 'header'
    values = lambda c: [cells[c] for _, cells in data]
    notes = []
    unknown = [i for i, h in enumerate(header) if h and i not in mapping.values()]
    if classify and unknown and any(f not in mapping and f not in chosen for f in required):
        free = [f for f in fields if f not in mapping and f not in chosen]
        answer = classify(header, [cells for _, cells in data[:3]], [{'field': f, 'label': labels[f]} for f in free])
        items = answer.get('columns') if isinstance(answer, dict) else None
        for item in items if isinstance(items, list) else []:
            column, field = (item.get('column'), item.get('field')) if isinstance(item, dict) else (None, None)
            if type(column) is not int or column not in unknown or field not in free or field in mapping or column in mapping.values():
                continue   # not a column or a field it was asked about, or one already answered
            if fits(field, values(column), header[column], settings):
                mapping[field], by[field] = column, 'model'
            else:
                notes.append('The model read "' + header[column] + '" as ' + labels[field] + ', but ' + MISFIT[kind_of(field)] + '; it is not used.')
    for i, h in enumerate(header):
        if shape == 'invoices' and i not in mapping.values() and name_key(h) in SYNONYMS['stillOwed'] + SYNONYMS['amountPaid']:
            notes.append('"' + h + '" (what is still owed or paid) is not imported by a proposal; import the file on the Records page to include it.')
    missing = [labels[f] for f in required if f not in mapping]
    needs = ['Choose a column for: ' + ', '.join(missing) + '.'] if missing else []
    order = hints.get('dateOrder') or date_order([v for f in DATE_FIELDS if f in mapping for v in values(mapping[f])])
    if not order:
        needs.append('Say whether the dates are day/month/year or month/day/year.')
    names = [v for v in values(mapping['customer']) if v] if 'customer' in mapping else []
    codes = len(names) > 0 and 2 * sum(bool(CODE.fullmatch(v)) for v in names) > len(names)
    prefix = hints.get('customerPrefix', 'Customer') if codes else None
    first = next((v for _, cells in data[:3] for v in [cells[mapping['customer']]] if v and (not codes or CODE.fullmatch(v))), None) \
        if 'customer' in mapping else None   # from the sample rows: the model may read the example
    named = lambda raw: ((prefix or '') + ' ' + raw).strip() if codes else raw
    days = hints.get('creditDays')
    rule = 'dueDate' if 'dueDate' in mapping else 'creditTerm' if 'creditDays' in mapping else 'days' if days is not None else 'none'
    view = {'shape': shape, 'headerRow': number, 'columns': header, 'samples': [cells for _, cells in data[:3]],
            'mapping': [{'field': f, 'label': labels[f], 'required': f in required, 'column': mapping.get(f),
                         'header': header[mapping[f]] if f in mapping else None, 'by': by.get(f)} for f in fields],
            'naming': {'rule': 'code' if codes else 'name', 'prefix': prefix, 'example': first and named(first)},
            'dueDates': {'rule': rule, 'column': mapping.get('dueDate', mapping.get('creditDays')) if rule in ('dueDate', 'creditTerm') else None, 'days': days},
            'dateOrder': order, 'needs': needs, 'notes': notes}
    unit = detect_unit(header, [cells for _, cells in data])
    for sheet_name, sheet_rows in (others or {}).items() if unit['detected'] is None else ():   # the file's other sheets state the unit too
        if sheet_rows:
            seen = detect_unit([c.strip() for c in header_of(sheet_rows)[1]], [])
            if seen['detected']:
                unit = {**seen, 'basis': 'the sheet "' + sheet_name + '": ' + seen['basis']}
                break
    invoices, payments, flagged, aliases, openings = [], [], [], {}, []
    if not needs:
        invoices, payments, flagged, aliases, openings = split(shape, data, mapping, header, order, codes, named, days, settings, today)
    unit = doubtful_unit(unit, invoices + payments, settings)
    counts = {'rows': len(data), 'customers': len({name_key(x['customer']) for x in invoices + payments}), 'invoices': len(invoices),
              'invoiceLines': sum(len(i['rows']) for i in invoices), 'payments': len(payments), 'openingBalances': len(openings),
              'flagged': len({f['row'] for f in flagged})}
    return {**view, 'unit': unit, 'aliases': aliases, 'counts': counts, 'flags': [{'row': f['row'], 'reason': f['reason']} for f in flagged], 'flaggedRows': flagged,
            'entries': {'invoices': invoices, 'payments': payments, 'openings': openings}}


KIND_WORDS = {'netting': 'a debt-netting row', 'adjustment': 'an adjustment row'}


def row_kind(record_type, transaction_type, description):
    """'opening', 'netting' or 'adjustment' when a ledger row's record or transaction type says so (an opening balance also by a
    description such as "Số dư đầu kỳ"); else None."""
    typed = name_key(record_type + ' ' + transaction_type)
    if 'opening balance' in typed or 'so du dau ky' in typed or name_key(description) in ('opening balance', 'so du dau ky'):
        return 'opening'
    return 'netting' if re.search(r'netting|offset|bu tru', typed) else 'adjustment' if 'adjustment' in typed or 'dieu chinh' in typed else None


def amount_or_none(text, settings):
    try:
        return amount_cell(text, settings)
    except RecordsError:
        return None


def money_words(amount):
    whole, _, part = money_text_plain(amount).partition('.')
    return amount['currency'] + ' ' + format(int(whole), ',') + ('.' + part if part else '')


def negative_words(amounts, settings):
    """The flag for a row whose amount is negative (a reversal or credit note), else None."""
    for text in amounts:
        if text.strip().startswith('-'):
            try:
                amount = parse_amount_cell(text.strip().lstrip('-'), settings, 'amount')
            except RecordsError:
                continue
            return 'A negative amount of ' + money_words(amount) + ' (a reversal or a credit note?); not imported, so this customer\'s balance excludes it.'
    return None


def split(shape, data, mapping, header, order, codes, named, days, settings, today):
    """The rows as invoices and payments: in a ledger a debit line is part of the invoice its number names (an invoice's amount
    is the sum of its debit lines, VAT lines included, each once) and a credit row is a payment, never an invoice. Rows that
    cannot be read are left out and flagged; a row with neither a customer nor an amount is a heading and is skipped."""
    dates = {f: column_dates([cells[mapping[f]] for _, cells in data], header[mapping[f]], order) for f in DATE_FIELDS if f in mapping}
    groups, payments, flagged, aliases, openings = {}, [], [], {}, []
    first_entry = min((d for f in ('paymentDate', 'issueDate') for d in dates.get(f, ()) if d), default=None)
    as_at = (date.fromisoformat(first_entry) - timedelta(days=1)).isoformat() if first_entry else None   # the file states no date for an opening balance

    def cell(cells, field):
        return cells[mapping[field]] if field in mapping else ''

    def day(field, i):
        return dates[field][i] if field in dates else ''

    def flag(n, cells, reason):
        flagged.append({'row': n, 'reason': reason, 'cells': cells})
    for i, (n, cells) in enumerate(data):
        raw = cell(cells, 'customer')
        kind = row_kind(cell(cells, 'recordType'), cell(cells, 'transactionType'), cell(cells, 'description'))
        amounts = [cell(cells, 'debit'), cell(cells, 'credit')] if shape == 'ledger' else [cell(cells, 'amount')]
        if not raw and not any(amounts):
            continue
        if not raw:
            flag(n, cells, NO_CUSTOMER)
            continue
        if codes and not CODE.fullmatch(raw):
            flag(n, cells, 'Not a customer code like the others (a total or a heading?); left out.')
            continue
        alias = raw if codes else cell(cells, 'customerCode')   # the code stays findable, whatever the customer is named
        if alias and alias != named(raw) and alias not in aliases.setdefault(named(raw), []):
            aliases[named(raw)].append(alias)
        if kind == 'opening':
            owed, held = (amount_or_none(cell(cells, f), settings) for f in ('outstanding', 'advance'))
            owed = owed or (amount_or_none(cell(cells, 'debit'), settings) if shape == 'ledger' else None)
            amount, direction = (owed, 'owed') if owed else (held, 'credit')
            if amount and as_at:
                openings.append({'customer': named(raw), 'amount': amount, 'direction': direction, 'asOf': as_at, 'row': n})
                flag(n, cells, 'An opening balance of ' + money_words(amount) + (' owed by' if direction == 'owed' else ' held in credit for') +
                     ' this customer, as at ' + as_at + ', the day before the ledger\'s first entry (the file states no date).')
            elif amount:
                flag(n, cells, 'An opening balance, but the file has no entry date to place it before; left out.')
            else:
                flag(n, cells, 'An opening balance row with no amount; left out.')
            continue
        try:
            money = [amount_cell(a, settings) for a in amounts]
        except RecordsError:
            flag(n, cells, negative_words(amounts, settings) or 'An amount is not understood (only amounts of more than zero are imported); left out.')
            continue
        if kind in KIND_WORDS and any(money):
            flag(n, cells, KIND_WORDS[kind].capitalize() + ' of ' + money_words(next(m for m in money if m)) +
                 "; not imported, so this customer's balance excludes it.")
            continue
        debit, credit = money if shape == 'ledger' else (money[0], None) if shape == 'invoices' else (None, money[0])
        if debit and credit:
            flag(n, cells, 'Both a debit and a credit on one row; left out.')
        elif not debit and not credit:
            flag(n, cells, 'No amount (zero or blank)' + (' on ' + KIND_WORDS[kind] if kind in KIND_WORDS else '') + '; left out.')
        elif debit:
            reference, issued = cell(cells, 'invoiceNumber'), day('issueDate', i)
            issued = day('paymentDate', i) if issued == '' and shape == 'ledger' else issued   # a ledger line with no invoice date: its posting date
            if not reference:
                flag(n, cells, 'A debit with no invoice number; left out.' if shape == 'ledger' else 'No invoice number; left out.')
            elif not issued:
                flag(n, cells, 'The invoice date is not a date; left out.')
            elif day('dueDate', i) is None:
                flag(n, cells, 'The due date is not a date; left out.')
            else:
                groups.setdefault((name_key(named(raw)), ref_key(reference)), []).append(
                    {'row': n, 'cells': cells, 'customer': named(raw), 'invoiceNumber': reference, 'issueDate': issued, 'dueDate': day('dueDate', i),
                     'term': cell(cells, 'creditDays'), 'amount': debit})
        else:
            paid = day('paymentDate', i)
            if not paid:
                flag(n, cells, 'The payment date is not a date; left out.')
            elif paid > today.isoformat():
                flag(n, cells, 'The payment is dated after today; left out.')
            else:
                # the invoice-number column is a number as written; a column of what the payment mentions, or its description, is read for HD73 and the like
                named_refs = [cell(cells, 'invoiceNumber')] if cell(cells, 'invoiceNumber') else invoice_reference_from(cell(cells, 'description'), cell(cells, 'mentioned'))
                if len(named_refs) > 1:   # imported, but not matched to any of them
                    flag(n, cells, 'This payment names several invoices; left unmatched.')
                payments.append({'customer': named(raw), 'date': paid, 'amount': credit, 'reference': cell(cells, 'reference') or None,
                                 'invoiceNumber': named_refs[0] if len(named_refs) == 1 else None, 'multipleInvoices': len(named_refs) > 1, 'row': n})
    invoices = []
    for lines in groups.values():
        first = lines[0]
        if shape == 'invoices' and len(lines) > 1:   # in an invoice list a number twice is a doubt, not two lines of one invoice
            for x in lines:
                flag(x['row'], x['cells'], 'The same invoice number of the same customer is on more than one row; left out.')
            continue
        issued = sorted({x['issueDate'] for x in lines})
        if len(issued) > 1:
            for x in lines:
                flag(x['row'], x['cells'], 'The lines of this invoice have different dates; the earliest is used.')
        term = next((int(x['term']) for x in lines if re.fullmatch(r'\d{1,3}', x['term'])), days)
        due = next((x['dueDate'] for x in lines if x['dueDate']), None)
        due = due or (None if term is None else (date.fromisoformat(issued[0]) + timedelta(days=term)).isoformat())
        if due and due < issued[0]:
            for x in lines:
                flag(x['row'], x['cells'], 'The due date is before the invoice date; left out.')
            continue
        invoices.append({'customer': first['customer'], 'invoiceNumber': first['invoiceNumber'], 'issueDate': issued[0], 'dueDate': due,
                         'amount': amount_of(first['amount'], sum(minor(x['amount']) for x in lines)), 'rows': [x['row'] for x in lines]})
    flagged.sort(key=lambda f: f['row'])
    return invoices, payments, flagged, aliases, openings


def csv_text(header, rows):
    out = io.StringIO()
    csv.writer(out, lineterminator='\n').writerows([header] + rows)
    return out.getvalue()


def derived(entries, choices):
    """A proposal's invoices and payments as files of the importer's own shapes, a batch each (when there are any), with each
    batch's params: the columns, ISO dates, a customer choice for every name ('new' unless the person chose 'skip' or a customer)
    and, in a ledger, payments sharing a reference kept as distinct payments (one receipt can pay several invoices, a line each).
    sources: the file's rows behind each batch row."""
    choices = {name_key(k): v for k, v in choices.items()}   # a name as written, or its key
    customers = {k: choices.get(k, 'new') for k in (name_key(x['customer']) for x in entries['invoices'] + entries['payments'] + entries.get('openings', []))}
    out, invoices, payments = [], entries['invoices'], entries['payments']
    if invoices:
        rows = [[i['customer'], i['invoiceNumber'], i['issueDate'], money_text_plain(i['amount']), i['dueDate'] or '', ' '.join(map(str, i['rows']))]
                for i in invoices]
        out.append({'shape': 'invoices', 'csvText': csv_text(INVOICE_HEADER, rows), 'sources': [i['rows'] for i in invoices], 'params': {
            'mapping': {'customer': 0, 'invoiceNumber': 1, 'issueDate': 2, 'amount': 3, 'dueDate': 4}, 'dateOrder': 'ymd', 'asOf': None,
            'resolutions': {'customers': customers, 'conflicts': {}, 'rows': {}}}})
    if payments:
        shared = Counter((name_key(x['customer']), ref_key(x['reference'])) for x in payments if x['reference'])
        rows = [[x['customer'], x['date'], money_text_plain(x['amount']), x['reference'] or '', x['invoiceNumber'] or '', str(x['row'])] for x in payments]
        distinct = {str(n): 'distinct' for n, x in enumerate(payments, start=2) if x['reference'] and shared[(name_key(x['customer']), ref_key(x['reference']))] > 1}
        out.append({'shape': 'payments', 'csvText': csv_text(PAYMENT_HEADER, rows), 'sources': [[x['row']] for x in payments], 'params': {
            'mapping': {'customer': 0, 'paymentDate': 1, 'amount': 2, 'reference': 3, 'invoiceNumber': 4}, 'dateOrder': 'ymd', 'asOf': None,
            'resolutions': {'customers': customers, 'conflicts': {}, 'rows': distinct}}})
    if entries.get('openings'):
        rows = [[x['customer'], x['asOf'], money_text_plain(x['amount']), x['direction'], str(x['row'])] for x in entries['openings']]
        out.append({'shape': 'openings', 'csvText': csv_text(OPENING_HEADER, rows), 'sources': [[x['row']] for x in entries['openings']], 'params': {
            'mapping': {'customer': 0, 'asOf': 1, 'amount': 2, 'direction': 3}, 'dateOrder': 'ymd', 'asOf': None,
            'resolutions': {'customers': customers, 'conflicts': {}, 'rows': {}}}})
    return out


def reference_summary(listed, batches, previews):
    """(references, text) for a proposal's payments: how many name an invoice, how many are matched (will be allocated to that
    invoice) and why each of the rest is not: noReference (names none), multiple (names several), notInFile, otherCustomer (the
    number is only another customer's) or ambiguous (it reads as two of the customer's invoices). The reasons and the matches add
    up to the payments. listed: the proposal's payments, in the order of the payments batch's rows."""
    rows = next((p['rows'] for b, p in zip(batches, previews) if b['shape'] == 'payments'), [])
    why = dict.fromkeys(('noReference', 'notInFile', 'otherCustomer', 'ambiguous', 'multiple', 'issuedAfter'), 0)
    matched = 0
    for x, r in zip(listed, rows):
        if r.get('allocation'):
            matched += 1
        elif x.get('multipleInvoices'):
            why['multiple'] += 1
        elif not x.get('invoiceNumber'):
            why['noReference'] += 1
        else:
            why[r.get('unmatched') or 'notInFile'] += 1
    named = sum(1 for x in listed if x.get('invoiceNumber'))
    references = {'payments': len(listed), 'named': named, 'matched': matched, 'unmatched': len(listed) - matched,
                  'multiple': why['multiple'], 'unmatchedReasons': why}
    other = why['notInFile'] + why['otherCustomer']
    text = (str(named) + ' of ' + str(len(listed)) + ' payments name an invoice; ' + str(matched) + ' of them match an invoice in this file and will be '
            'matched; ' + str(other) + ' name an invoice not in this file; ' + str(why['noReference'] + why['multiple']) + ' stay without a reference')
    if why['issuedAfter']:
        text += '; ' + str(why['issuedAfter']) + ' name an invoice issued after the payment and stay unmatched'
    if why['ambiguous']:
        text += '; ' + str(why['ambiguous']) + ' could be more than one invoice of the customer and stay unmatched'
    return references, text


def dry_run(doc, batches, settings, today, source):
    """Each batch's preview as importing them in this order would make it, on a copy of the records: the payments are previewed
    after the invoices are applied, so they find the customers and invoices those create. doc is not changed."""
    doc, ids, previews = copy.deepcopy(doc), itertools.count(1), []
    for b in batches:
        header, rows = read_csv(b['csvText'])
        result = preview(doc, header, rows, {**b['params'], 'shape': b['shape'], 'sourceLabel': source}, settings, today)
        previews.append(result)
        if result['ready']:
            APPLY.get(b['shape'], apply)(doc, {'id': 'dry-run', 'params': b['params']}, result,
                                                                    lambda kind: 'dry_' + kind + '_' + str(next(ids)), {'kind': 'file', 'batchId': 'dry-run', 'at': today.isoformat()})
    return previews


def expected(previews):
    """What an apply must still find: each batch row's status and the customers it would create or need a choice for."""
    return [[[r['status'] for r in p['rows']], sorted(c['key'] for c in p['customers'])] for p in previews]


def review(proposal, batches, previews):
    """The proposal with each batch's preview against the records: its counts, the customers it would create, the rows the
    importer rejects or that need a person (a conflict with the records, a payment that may repeat one), flagged with the file's
    rows, the batches that write anything, and whether it is ready to import. unknown: the names the records do not hold, each with
    its choice ('new', 'skip' or a customerId)."""
    flagged, needs, unknown, waiting = list(proposal['flaggedRows']), list(proposal['needs']), {}, set()
    counts = {'invoices': None, 'payments': None}
    for b, p in zip(batches, previews):
        counts[b['shape']] = p['counts']
        unknown.update({c['key']: c['resolution'] for c in p['customers'] if c['key'] not in unknown})
        for r in p['rows']:
            if r['status'] in ('conflict', 'unresolved', 'rejected'):   # the importer's reason may quote the row: the card's detail only
                detail = r.get('reason') or 'It differs from the records (' + words(r.get('conflictFields') or []) + ').'
                flagged += [{'row': n, 'reason': REVIEWED[r['status']], 'cells': None, 'detail': detail} for n in b['sources'][r['row'] - 2]]
                waiting |= set(b['sources'][r['row'] - 2]) if r['status'] != 'rejected' else set()
            elif r.get('unmatched') == 'issuedAfter':   # flagged, nothing to decide: the payment is imported and left unmatched
                flagged += [{'row': n, 'reason': 'Names an invoice issued after the payment; left unmatched.', 'cells': None, 'detail': r['allocationNote']} for n in b['sources'][r['row'] - 2]]
    writes = [i for i, p in enumerate(previews) if any(r['status'] in WRITES for r in p['rows'])]
    if waiting:
        needs.append('Rows ' + ', '.join(map(str, sorted(waiting))) + ' differ from the records or may repeat a recorded payment: import the file on the '
                     'Records page to choose, or correct the file.')
    if not needs and not writes:
        needs.append('Nothing in this file would be imported.')
    flagged.sort(key=lambda f: f['row'])
    return {'preview': counts, 'unknown': unknown, 'flaggedRows': flagged, 'needs': needs, 'writes': writes,
            'ready': not needs and all(previews[i]['ready'] for i in writes), 'expected': expected([previews[i] for i in writes])}
