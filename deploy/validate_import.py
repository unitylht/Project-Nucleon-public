#!/usr/bin/env python3
"""Check an imported records database against the source ledger it came from, independently of the importer's code paths.

Usage: validate_import.py <records.sqlite3> <ledger.xlsx> --sheet NAME --as-of YYYY-MM-DD [--customers CODE,CODE,...]
                          [--expect invoices=N,payments=N,allocations=N,openings=N,notInFile=N] [--out FILE]
       validate_import.py --selftest

Reads the database read-only (open a COPY, never the live file). Prints a report and exits 1 when any check finds a discrepancy.
The checks: 1 customers, 2 invoices, 3 payments, 4 allocations, 5 opening balances, 6 positions, 7 replay (the behaviour
features recomputed by hand from the ledger against prototype/behaviour.py on the stored records). It also lists customers that
make good test cases for a routine request and for an escalation. stdlib only; openpyxl is used for .xlsx when installed,
otherwise prototype/xlsx.py."""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'prototype'))

COLUMNS = {'cust': 'Customer_ID', 'inv': 'Invoice Number', 'invdate': 'Invoice Date', 'docdate': 'Document Date', 'posting': 'Posting Date',
           'docno': 'Document Number', 'desc': 'Description (English)', 'mention': 'Invoice Reference Mentioned', 'dr': 'Debit (Dr)',
           'cr': 'Credit (Cr)', 'term': 'Credit Term Days', 'rtype': 'Record Type', 'ttype': 'Transaction Type',
           'owed': 'Outstanding Debt', 'adv': 'Advance Payment'}


# ---------------------------------------------------------------- reading the ledger

def _day(v):
    if v in (None, ''):
        return None
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    return str(v).strip()[:10]


def _num(v):
    if v in (None, ''):
        return 0
    d = Decimal(str(v).replace(',', '').strip())
    return int(d) if d == d.to_integral_value() else d


def _text(v):
    if v in (None, ''):
        return ''
    if isinstance(v, float) and v == int(v):
        v = int(v)
    return str(v).strip()


def read_rows(path, sheet):
    """The ledger sheet as a list of dicts (keys of COLUMNS plus 'row', the sheet row number)."""
    try:
        import openpyxl
        ws = openpyxl.load_workbook(path, data_only=True, read_only=True)[sheet]
        raw = [list(r) for r in ws.iter_rows(values_only=True)]
    except ImportError:
        import xlsx
        raw = xlsx.read_workbook(Path(path).read_bytes())[sheet]
    head = [_text(h) for h in raw[0]]
    where = {k: head.index(v) for k, v in COLUMNS.items()}
    out = []
    for n, cells in enumerate(raw[1:], start=2):
        cells = list(cells) + [None] * (len(head) - len(cells))
        if not any(c not in (None, '') for c in cells):
            continue
        g = lambda k: cells[where[k]]
        out.append({'row': n, 'cust': _text(g('cust')), 'inv': _text(g('inv')), 'invdate': _day(g('invdate')), 'docdate': _day(g('docdate')),
                    'posting': _day(g('posting')), 'docno': _text(g('docno')), 'desc': _text(g('desc')), 'mention': _text(g('mention')),
                    'dr': _num(g('dr')), 'cr': _num(g('cr')), 'term': _text(g('term')), 'rtype': _text(g('rtype')), 'ttype': _text(g('ttype')),
                    'owed': _num(g('owed')), 'adv': _num(g('adv'))})
    return out


# ---------------------------------------------------------------- the records, read straight from the tables

TABLES = {'customers': 'customers', 'invoices': 'invoices', 'payments': 'payments', 'allocations': 'allocations',
          'openingBalances': 'opening_balances'}


def read_records(conn):
    doc = {k: [json.loads(r[0]) for r in conn.execute('SELECT data FROM ' + t + ' ORDER BY seq')] for k, t in TABLES.items()}
    live = lambda xs: [x for x in xs if x.get('status', 'active') == 'active']
    return {k: live(v) for k, v in doc.items()}


def units(amount):
    return int(amount['minorUnits']) if amount else 0


# ---------------------------------------------------------------- the rules, written again here

def key(reference):
    """An invoice number compared without spaces, case or leading zeros of each digit run ('35', '035' and '00000035' agree;
    'HD73' stays different from '73')."""
    return re.sub(r'\d+', lambda m: m.group().lstrip('0') or '0', re.sub(r'\s+', '', str(reference or '')).upper())


NAMED = re.compile(r'(?<![a-z0-9])(?:inv(?:oice)?|hd|hoa\s*don)\s*(?:no\.?|number|#|:)?\s*([a-z]{0,3}\d[\w./-]*)', re.I)


def named_by(row):
    """The invoice numbers a payment row names, as written: the 'Invoice Reference Mentioned' cell, else the description."""
    cell = row['mention']
    if cell:
        parts = [p for p in re.split(r'\s*(?:,|;|&|\+)\s*', cell) if p]
        return [exact(p.rstrip('.,;')) for p in parts]
    return [exact(m.group(1).rstrip('.,;')) for m in NAMED.finditer(row['desc'])]


def exact(reference):
    """An invoice number as written, without spaces or case: two numbers that differ only by leading zeros ('2' and '00000002') are
    two invoices (a new series), as the records keep them."""
    return re.sub(r'\s+', '', str(reference or '')).upper()


def matching(by_code, code, named_key, received=None):
    """The invoices of a customer a normalised reference can mean: [] (none), one, or several (ambiguous). The number as written wins
    when it names exactly one. received: the payment's date; an invoice issued after it cannot be what the payment names (a payment
    cannot pay an invoice that did not exist yet), whatever the normalisation says."""
    mine = {k: v for k, v in by_code.get(code, {}).items() if not (received and v.get('issue') and v['issue'] > received)}
    same = [k for k in mine if k == named_key]
    close = [k for k in mine if key(k) == key(named_key)]
    return same if len(same) == 1 else close


def is_payment(r):
    return r['ttype'].lower() == 'payment'


def sheet_model(rows):
    """What the ledger says, by customer code: invoices {ref key: dict}, payments [dict], openings [dict]."""
    invoices, payments, openings, other = defaultdict(dict), defaultdict(list), defaultdict(list), []
    for r in rows:
        c = r['cust']
        if r['rtype'].lower() == 'opening balance' or r['ttype'].lower() == 'opening balance':
            if c:
                openings[c].append(r)
        elif is_payment(r):
            if c and r['cr']:
                payments[c].append(r)
        elif r['dr'] > 0 and c and r['inv']:
            inv = invoices[c].setdefault(exact(r['inv']), {'ref': r['inv'], 'rows': [], 'total': 0, 'issue': r['invdate'] or r['posting'],
                                                         'terms': set()})
            inv['rows'].append(r['row'])
            inv['total'] += r['dr']
            inv['terms'].add(r['term'])
            if (r['invdate'] or r['posting']) != inv['issue']:
                inv.setdefault('dates', set()).update({inv['issue'], r['invdate'] or r['posting']})
        elif r['cr'] or r['dr']:
            other.append(r)
    return invoices, payments, openings, other


class Report:
    def __init__(self):
        self.lines, self.bad, self.warn = [], [], []
        self.status = {}

    def out(self, text=''):
        self.lines.append(text)

    def section(self, name):
        self.current = name
        self.status[name] = 'PASS'
        self.out('')
        self.out('## ' + name)

    def fail(self, text):
        self.bad.append(self.current + ': ' + text)
        self.status[self.current] = 'FAIL'
        self.out('- DISCREPANCY: ' + text)

    def note(self, text):
        self.out('- ' + text)

    def warning(self, text):
        self.warn.append(self.current + ': ' + text)
        self.out('- note: ' + text)


# ---------------------------------------------------------------- the checks

def check_customers(rep, doc, rows):
    rep.section('1 Customers')
    codes = sorted({r['cust'] for r in rows if r['cust'] and (r['dr'] or r['cr'])})
    withonly = sorted({r['cust'] for r in rows if r['cust']} - set(codes))
    stored = Counter(a for c in doc['customers'] for a in (c.get('aliases') or []))
    by_alias = {a: c for c in doc['customers'] for a in (c.get('aliases') or [])}
    rep.note('sheet customers with a debit or credit: ' + str(len(codes)) + '; stored customers: ' + str(len(doc['customers'])))
    for code in codes:
        c = by_alias.get(code)
        if stored[code] != 1 or c is None:
            rep.fail('customer ' + code + ' appears ' + str(stored[code]) + ' times among the aliases')
        elif c['name'] != 'Customer ' + code:
            rep.fail('customer ' + code + ' is named "' + c['name'] + '", expected "Customer ' + code + '"')
    for c in doc['customers']:
        if not any(a in codes or a in withonly for a in (c.get('aliases') or [])):
            rep.fail('stored customer "' + c['name'] + '" has no code from the sheet')
    names = Counter(c['name'] for c in doc['customers'])
    for n, k in names.items():
        if k > 1:
            rep.fail('name "' + n + '" is stored ' + str(k) + ' times')
    for code in withonly:
        rep.note('code ' + code + ' has only opening-balance/zero rows' + (' and is stored' if code in by_alias else ' and is NOT stored'))
        if code not in by_alias:
            rep.fail('customer ' + code + ' (opening balance only) is not stored')
    return by_alias


def invoice_index(doc, by_alias):
    """{customer code: {ref key: [stored invoice, ...]}}."""
    code_of = {c['id']: next(iter(c.get('aliases') or ['?']), '?') for c in doc['customers']}
    idx = defaultdict(lambda: defaultdict(list))
    for i in doc['invoices']:
        idx[code_of[i['customerId']]][exact(i['reference'])].append(i)
    return idx, code_of


def check_invoices(rep, doc, model, by_alias, expect):
    rep.section('2 Invoices')
    idx, code_of = invoice_index(doc, by_alias)
    sheet_n = sum(len(v) for v in model.values())
    rep.note('invoices in the sheet (distinct number per customer): ' + str(sheet_n) + '; stored: ' + str(len(doc['invoices'])))
    for code, invs in sorted(model.items()):
        for k, s in sorted(invs.items()):
            found = idx[code].get(k, [])
            if not found:
                rep.fail('invoice ' + s['ref'] + ' of ' + code + ' (sheet rows ' + ','.join(map(str, s['rows'])) + ') is missing')
                continue
            if len(found) > 1:
                rep.fail('invoice ' + s['ref'] + ' of ' + code + ' is stored ' + str(len(found)) + ' times')
            i = found[0]
            if units(i['total']) != s['total'] * 10 ** i['total']['scale']:
                rep.fail('invoice ' + s['ref'] + ' of ' + code + ': stored total ' + str(units(i['total'])) + ', sheet debit rows sum to ' + str(s['total']))
            dates = s.get('dates')
            issue = s['issue'] if not dates else min(dates)   # the importer's stated rule: the earliest date of its lines
            if dates:
                rep.warning('invoice ' + s['ref'] + ' of ' + code + ' has lines with different dates ' + ', '.join(sorted(dates)) + '; earliest used')
            if i['issueDate'] != issue:
                rep.fail('invoice ' + s['ref'] + ' of ' + code + ': stored issue date ' + str(i['issueDate']) + ', sheet ' + str(issue))
            terms = {t for t in s['terms'] if t != ''}
            if len(terms) == 1 and re.fullmatch(r'\d+(\.0+)?', next(iter(terms))):
                due = (date.fromisoformat(issue) + timedelta(days=int(float(next(iter(terms)))))).isoformat()
                if i.get('originalDueDate') != due:
                    rep.fail('invoice ' + s['ref'] + ' of ' + code + ': stored due ' + str(i.get('originalDueDate')) + ', issue + term gives ' + due)
            else:
                rep.fail('invoice ' + s['ref'] + ' of ' + code + ' has no single Credit Term Days (' + ','.join(sorted(terms)) + ')')
    extra = [(code, k) for code, d in idx.items() for k in d if k not in model.get(code, {})]
    for code, k in extra:
        rep.fail('stored invoice ' + k + ' of ' + code + ' is not in the sheet')
    if expect.get('invoices') is not None and len(doc['invoices']) != expect['invoices']:
        rep.fail('stored invoice count ' + str(len(doc['invoices'])) + ', expected ' + str(expect['invoices']))
    return idx, code_of


def pay_key(code, p):
    return (code, p['docdate'], p['cr'], p['docno'])


def check_payments(rep, doc, pays, code_of, other, expect):
    rep.section('3 Payments')
    want = Counter()
    for code, ps in pays.items():
        for p in ps:
            want[(code, p['docdate'], p['cr'], p['docno'])] += 1
    have = Counter()
    for p in doc['payments']:
        have[(code_of[p['customerId']], p['receivedDate'], units(p['amount']), p['reference'] or '')] += 1
    rep.note('payment rows with a customer in the sheet: ' + str(sum(want.values())) + '; stored: ' + str(sum(have.values())))
    for k, n in (want - have).items():
        rep.fail('payment of ' + str(k[2]) + ' on ' + k[1] + ' (' + k[3] + ') of ' + k[0] + ' is missing' + (' or stored fewer than ' + str(n) + ' times'))
    for k, n in (have - want).items():
        rep.fail('stored payment of ' + str(k[2]) + ' on ' + k[1] + ' (' + k[3] + ') of ' + k[0] + ' is not a payment row of the sheet (or doubled)')
    for r in other:
        rep.note('left out as not a payment: row ' + str(r['row']) + ' ' + r['cust'] + ' ' + (r['docdate'] or '') + ' ' + r['ttype'] + ' dr=' + str(r['dr']) + ' cr=' + str(r['cr']))
        stored = [p for p in doc['payments'] if code_of[p['customerId']] == r['cust'] and p['receivedDate'] == r['docdate'] and units(p['amount']) == r['cr'] and r['cr']]
        if stored:
            rep.fail('row ' + str(r['row']) + ' (' + r['ttype'] + ') is stored as a payment')
    if expect.get('payments') is not None and len(doc['payments']) != expect['payments']:
        rep.fail('stored payment count ' + str(len(doc['payments'])) + ', expected ' + str(expect['payments']))


def check_allocations(rep, doc, model, pays, code_of, expect):
    rep.section('4 Allocations')
    pay_by_id = {p['id']: p for p in doc['payments']}
    inv_by_id = {i['id']: i for i in doc['invoices']}
    sheet_rows = defaultdict(list)
    for code, ps in pays.items():
        for p in ps:
            sheet_rows[pay_key(code, p)].append(p)
    rep.note('stored allocations: ' + str(len(doc['allocations'])))
    per_pay, per_inv, allocated_pay = Counter(), Counter(), set()
    for a in doc['allocations']:
        p, i = pay_by_id.get(a['paymentId']), inv_by_id.get(a['invoiceId'])
        if p is None or i is None:
            rep.fail('allocation ' + a['id'] + ' points at a missing payment or invoice')
            continue
        code = code_of[p['customerId']]
        label = code + ' ' + (p['reference'] or '') + ' -> invoice ' + i['reference']
        if p['customerId'] != i['customerId']:
            rep.fail(label + ': allocated across customers')
            continue
        if i.get('issueDate') and p['receivedDate'] < i['issueDate']:   # independent of any reference normalisation
            rep.fail(label + ': the payment was received ' + p['receivedDate'] + ', before the invoice was issued (' + i['issueDate'] + ')')
        srcs = sheet_rows.get((code, p['receivedDate'], units(p['amount']), p['reference'] or ''), [])
        if not srcs:
            rep.fail(label + ': the payment is not in the sheet')
            continue
        if not any(key(n) == key(i['reference']) for s in srcs for n in named_by(s)):
            rep.fail(label + ': the payment row does not name this invoice (names ' + ','.join(sorted({k for s in srcs for k in named_by(s)})) + ')')
        amount = units(a['amount'])
        if amount <= 0 or amount > min(units(p['amount']), units(i['total'])):
            rep.fail(label + ': amount ' + str(amount) + ' is not within min(payment ' + str(units(p['amount'])) + ', invoice ' + str(units(i['total'])) + ')')
        per_pay[p['id']] += amount
        per_inv[i['id']] += amount
        allocated_pay.add(p['id'])
    for pid, n in per_pay.items():
        if n > units(pay_by_id[pid]['amount']):
            rep.fail('payment ' + (pay_by_id[pid]['reference'] or pid) + ' is allocated ' + str(n) + ', more than it is')
    for iid, n in per_inv.items():
        if n > units(inv_by_id[iid]['total']):
            rep.fail('invoice ' + inv_by_id[iid]['reference'] + ' of ' + code_of[inv_by_id[iid]['customerId']] + ' is allocated ' + str(n) + ', more than its total')
    # the references that match nothing
    stored_by = defaultdict(list)
    for p in doc['payments']:
        stored_by[(code_of[p['customerId']], p['receivedDate'], units(p['amount']), p['reference'] or '')].append(p)
    not_in_file, unallocated_but_exists, exhausted, ambiguous, multiple, none = [], [], [], [], 0, 0
    issued_after = []
    for code, ps in sorted(pays.items()):
        for s in ps:
            names = named_by(s)
            stored = stored_by.get(pay_key(code, s), [])
            if not names:
                none += 1
                continue
            if any(p['id'] in allocated_pay for p in stored):
                continue
            if len(names) > 1:
                multiple += 1
                continue
            close = matching(model, code, names[0], s['docdate'])
            if not close and matching(model, code, names[0]):
                issued_after.append((code, s, names[0]))
            elif len(close) == 1:
                stored = [i for i in doc['invoices'] if code_of[i['customerId']] == code and exact(i['reference']) == close[0]]
                room = model[code][close[0]]['total'] - sum(per_inv[i['id']] for i in stored)
                (exhausted if room <= 0 else unallocated_but_exists).append((code, s, close[0], room))
            elif close:
                ambiguous.append((code, s, close))
            else:
                other = [c for c, d in model.items() if c != code and matching(model, c, names[0])]
                not_in_file.append((code, s, names[0], other))
    rep.note('payments naming no invoice: ' + str(none) + '; naming several (left unmatched): ' + str(multiple))
    rep.note('references to an invoice issued after the payment (left unmatched, as the importer does): ' + str(len(issued_after)))
    for code, s, k in issued_after:
        rep.out('  - ' + code + ' payment ' + s['docno'] + ' (' + s['docdate'] + ', ' + str(s['cr']) + ') names "' + k + '", issued after it')
    rep.note('references to an invoice not in this file (for that customer): ' + str(len(not_in_file)) + ' -- each confirmed to have no matching invoice for the customer in the sheet')
    for code, s, k, other in not_in_file:
        rep.out('  - ' + code + ' payment ' + s['docno'] + ' (' + s['docdate'] + ', ' + str(s['cr']) + ') names "' + k + '"' + ('; only customer(s) ' + ','.join(other) + ' have it' if other else ''))
    rep.note('references to an invoice that exists but is already fully allocated (the importer\'s summary counts these as "not in this file" too): ' + str(len(exhausted)))
    for code, s, k, room in exhausted:
        rep.out('  - ' + code + ' payment ' + s['docno'] + ' (' + s['docdate'] + ', ' + str(s['cr']) + ') names invoice ' + model[code][k]['ref'] + ' (total ' + str(model[code][k]['total']) + '), nothing left on it')
    for code, s, k, room in unallocated_but_exists:
        rep.fail(code + ' payment ' + s['docno'] + ' (' + s['docdate'] + ', ' + str(s['cr']) + ') names invoice ' + model[code][k]['ref'] + ', which exists with ' + str(room) + ' unallocated, but has no allocation')
    for code, s, close in ambiguous:
        rep.note(code + ' payment ' + s['docno'] + ' names a number that could be any of ' + ', '.join(model[code][k]['ref'] for k in close) + '; left unallocated')
    if expect.get('allocations') is not None and len(doc['allocations']) != expect['allocations']:
        rep.fail('stored allocation count ' + str(len(doc['allocations'])) + ', expected ' + str(expect['allocations']))
    if expect.get('notInFile') is not None and len(not_in_file) + len(exhausted) != expect['notInFile']:
        rep.fail('"not in this file" references: ' + str(len(not_in_file)) + ' absent + ' + str(len(exhausted)) + ' exhausted, expected ' + str(expect['notInFile']))


def check_openings(rep, doc, openings, rows, code_of, expect):
    rep.section('5 Opening balances')
    entries = [d for r in rows for d in (r['docdate'], r['invdate']) if d and not (r['rtype'].lower() == 'opening balance')]
    as_of = (date.fromisoformat(min(entries)) - timedelta(days=1)).isoformat()
    rep.note('as-at date (day before the first entry ' + min(entries) + '): ' + as_of)
    want = {}
    for code, rs in openings.items():
        for r in rs:
            amount = r['owed'] if r['owed'] else -r['adv']
            if amount:
                want[code] = want.get(code, 0) + amount
    have = {}
    for o in doc['openingBalances']:
        c = code_of[o['customerId']]
        if c in have:
            rep.fail('customer ' + c + ' has two opening balances')
        have[c] = (units(o['amount']), o['asOf'])
    rep.note('sheet opening rows: ' + str(len(want)) + '; stored: ' + str(len(have)))
    for c in sorted(set(want) | set(have)):
        if c not in have:
            rep.fail('opening balance of ' + c + ' (' + str(want[c]) + ') is missing')
        elif c not in want:
            rep.fail('stored opening balance of ' + c + ' is not in the sheet')
        else:
            rep.note(c + ': ' + ('owed' if want[c] > 0 else 'credit') + ' ' + str(abs(want[c])) + ' as at ' + have[c][1])
            if have[c][0] != want[c]:
                rep.fail('opening balance of ' + c + ': stored ' + str(have[c][0]) + ', sheet ' + str(want[c]) + ' (direction: owed is positive)')
            if have[c][1] != as_of:
                rep.fail('opening balance of ' + c + ': stored as at ' + have[c][1] + ', expected ' + as_of)
    if expect.get('openings') is not None and len(have) != expect['openings']:
        rep.fail('stored opening balance count ' + str(len(have)) + ', expected ' + str(expect['openings']))
    return want


def check_positions(rep, doc, model, pays, want_open, code_of, chosen, settings):
    rep.section('6 Positions')
    from records import customer_position
    id_of = {v: k for k, v in code_of.items()}
    for code in chosen:
        invoiced = sum(i['total'] for i in model.get(code, {}).values())
        received = sum(p['cr'] for p in pays.get(code, []))
        pos = customer_position(doc, id_of[code], settings)
        net = units(pos['recordedNet'])
        rep.note(code + ': invoiced ' + str(invoiced) + ' - received ' + str(received) + ' = ' + str(invoiced - received) + '; records recordedNet ' + str(net) +
                 '; opening ' + str(want_open.get(code, 0)) + ' so position with opening ' + str(invoiced - received + want_open.get(code, 0)))
        if net != invoiced - received:
            rep.fail(code + ': recordedNet ' + str(net) + ' differs from invoiced - received ' + str(invoiced - received))
        if units(pos['invoicesRecorded']) != invoiced or units(pos['paymentsRecorded']) != received:
            rep.fail(code + ': records totals (' + str(units(pos['invoicesRecorded'])) + ' / ' + str(units(pos['paymentsRecorded'])) + ') differ from the sheet (' + str(invoiced) + ' / ' + str(received) + ')')
        # the opening balance in the records
        o = [units(x['amount']) for x in doc['openingBalances'] if code_of[x['customerId']] == code]
        if sum(o) != want_open.get(code, 0):
            rep.fail(code + ': stored opening ' + str(sum(o)) + ' differs from the sheet ' + str(want_open.get(code, 0)))


# ---------------------------------------------------------------- the replay, by hand

def hand_replay(code, as_of, model, pays, want_open, openings_asof):
    """The behaviour features for one customer from the ledger alone: recorded (reference-named) allocations first, then oldest first."""
    d = date.fromisoformat
    invs = sorted((v for v in model.get(code, {}).values() if d(v['issue']) < as_of), key=lambda v: (v['issue'], v['rows'][0]))
    for v in invs:
        v['due'] = (d(v['issue']) + timedelta(days=int(float(next(t for t in v['terms'] if t != ''))))).isoformat()
    ps = sorted((p for p in pays.get(code, []) if d(p['docdate']) < as_of), key=lambda p: (p['docdate'], p['row']))
    left = {id(v): v['total'] for v in invs}
    opening = want_open.get(code, 0) if d(openings_asof) < as_of else 0
    owing_opening, late, naming = max(opening, 0), 0, 0
    seen_day, day_late = None, False
    # a payment that names one invoice by reference is reserved on that invoice first (up to its total), so oldest-first never uses it;
    # a payment with nothing open to pay stays as customer credit, applied to invoices as they are issued
    named, res = {}, {id(v): 0 for v in invs}
    for p in ps:
        names = named_by(p)
        close = matching(model, code, names[0], p['docdate']) if len(names) == 1 else []   # an invoice issued after the payment is not what it names
        v = model[code][close[0]] if len(close) == 1 else None
        if v is not None and id(v) in left:
            named[p['row']] = (v, min(p['cr'], v['total'] - res[id(v)]))
            res[id(v)] += named[p['row']][1]
    issued, credit, waiting = set(), 0, defaultdict(int)
    held_credit = max(-opening, 0)   # an advance held in credit at the start, applied to invoices as they are issued
    timeline = sorted([(v['issue'], 0, v['rows'][0], v) for v in invs] + [(p['docdate'], 1, p['row'], p) for p in ps], key=lambda e: e[:3])
    for _, kind, _, x in timeline:
        if kind == 0:   # an invoice is issued: the payments waiting for it, then customer credit
            issued.add(id(x))
            left[id(x)] -= waiting[id(x)]
            res[id(x)] -= waiting[id(x)]
            use = min(held_credit, left[id(x)] - res[id(x)])
            left[id(x)] -= use
            held_credit -= use
            use = min(credit, left[id(x)] - res[id(x)])
            left[id(x)] -= use
            credit -= use
            continue
        p = x
        when = d(p['docdate'])
        if seen_day != when:   # judged once per day, before that day's payments
            seen_day, day_late = when, any(left[id(v)] > 0 and d(v['due']) < when for v in invs if id(v) in issued)
        late += day_late
        rest = p['cr']
        if p['row'] in named:
            v, m = named[p['row']]
            rest -= m
            naming += 1
            if id(v) in issued:
                left[id(v)] -= m
                res[id(v)] -= m
            else:
                waiting[id(v)] += m
        for v in invs:
            if rest <= 0:
                break
            if id(v) in issued:
                take = min(rest, left[id(v)] - res[id(v)])
                left[id(v)] -= take
                rest -= take
        paid = min(max(rest, 0), owing_opening)
        owing_opening -= paid
        credit += max(rest, 0) - paid
    past = [(left[id(v)], (as_of - d(v['due'])).days, v) for v in invs if left[id(v)] > 0 and d(v['due']) < as_of]
    days = [d(x) for x in [*(v['issue'] for v in invs), *(p['docdate'] for p in ps), *([openings_asof] if opening else [])]]
    return {'debt_before_m': sum(left.values()) + owing_opening, 'overdue_before_m': sum(m for m, _, _ in past),
            'max_days_past_due_before': max((x for _, x, _ in past), default=0), 'prior_receipt_count': len(ps), 'lateReceipts': late,
            'days_since_prior_receipt': (as_of - d(ps[-1]['docdate'])).days if ps else None,
            'observed_relationship_days': (as_of - min(days)).days if days else None,
            'open': [(v['ref'], v['due'], left[id(v)]) for v in invs if left[id(v)] > 0], 'opening_owing': owing_opening, 'credit_unapplied': held_credit + credit}


REASONS = {
    'debt_before_m': 'the oldest-first matching or an allocation differs (a payment matched by reference in one and not the other)',
    'overdue_before_m': 'the invoices left open differ (reference match versus oldest-first)',
    'max_days_past_due_before': 'the invoices left open differ',
    'lateReceipts': 'same-day payments are ordered differently, or the open invoices before a payment differ',
    'prior_receipt_count': 'a payment is missing or extra',
    'days_since_prior_receipt': 'the last payment differs',
    'observed_relationship_days': 'the first record differs, for example an opening balance dated as at the day before the first entry',
}


def check_replay(rep, doc, model, pays, want_open, openings_asof, code_of, chosen, as_of):
    rep.section('7 Replay as of ' + as_of.isoformat())
    import behaviour
    id_of = {v: k for k, v in code_of.items()}
    results = {}
    for code in chosen:
        mine = hand_replay(code, as_of, model, pays, want_open, openings_asof)
        cid = id_of[code]
        f = behaviour.replay([i for i in doc['invoices'] if i['customerId'] == cid], [p for p in doc['payments'] if p['customerId'] == cid],
                             [a for a in doc['allocations'] if a['customerId'] == cid], [o for o in doc['openingBalances'] if o['customerId'] == cid], as_of)
        results[code] = (mine, f)
        rep.note(code + ' by hand: ' + ', '.join(k + '=' + str(mine[k]) for k in REASONS) + '; opening still owing ' + str(mine['opening_owing']))
        rep.note(code + ' replay : ' + ', '.join(k + '=' + str(f[k]) for k in REASONS) + '; basis ' + f['allocationBasis'] + ', opening ' + str(f['openingBalance']))
        if not f['reconciles'] and f['difference'] == mine['credit_unapplied'] > 0:
            rep.note(code + ': credit unapplied, ' + str(mine['credit_unapplied']) + ' held as customer credit with no invoice to apply it to (not a failure)')
        elif not f['reconciles']:
            rep.fail(code + ': replay does not reconcile, debt is ' + str(f['difference']) + ' more than opening + invoiced - received (a payment beyond what was invoiced, or an allocation to an invoice outside the replay)')
        for k, why in REASONS.items():
            if mine[k] != f[k]:
                if not f['reconciles'] and k in ('debt_before_m', 'overdue_before_m', 'lateReceipts'):
                    why = 'follows from the dropped excess above (' + why + ')'
                extra = ''
                if k == 'observed_relationship_days' and want_open.get(code):
                    extra = ' (this customer has an opening balance as at ' + openings_asof + ')'
                rep.fail(code + ' ' + k + ': by hand ' + str(mine[k]) + ', replay ' + str(f[k]) + '; likely cause: ' + why + extra)
    return results


def candidates(rep, doc, model, pays, want_open, openings_asof, code_of, as_of):
    rep.section('Candidates as of ' + as_of.isoformat())
    import behaviour
    id_of = {v: k for k, v in code_of.items()}
    calm, hot, everyone = [], [], []
    for code in sorted(id_of):
        cid = id_of[code]
        f = behaviour.replay([i for i in doc['invoices'] if i['customerId'] == cid], [p for p in doc['payments'] if p['customerId'] == cid],
                             [a for a in doc['allocations'] if a['customerId'] == cid], [o for o in doc['openingBalances'] if o['customerId'] == cid], as_of)
        mine = hand_replay(code, as_of, model, pays, want_open, openings_asof)
        agree = mine['overdue_before_m'] == f['overdue_before_m'] and mine['lateReceipts'] == f['lateReceipts']
        row = (code, f, mine, agree)
        everyone.append(row)
        if f['overdue_before_m'] == 0 and mine['overdue_before_m'] == 0:
            calm.append(row)
        if f['overdue_before_m'] > 0 and mine['overdue_before_m'] > 0 and f['lateReceipts'] > 0:
            hot.append(row)

    def show(title, rows, n):
        rep.out('')
        rep.out('**' + title + '**')
        for code, f, mine, agree in rows[:n]:
            rep.out('- ' + code + ': debt ' + str(f['debt_before_m']) + ', overdue ' + str(f['overdue_before_m']) + ', ' + str(f['lateReceipts']) + ' of ' +
                    str(f['prior_receipt_count']) + ' receipts late, relationship ' + str(f['observed_relationship_days']) + ' days, replay and hand ' +
                    ('agree' if agree else 'DISAGREE') + '; open: ' + '; '.join(r + ' due ' + due + ' (' + str(m) + ')' for r, due, m in mine['open']))
        if not rows:
            rep.out('- none')
    rep.out('')
    rep.out('All customers (replay): code, debt, overdue, late/receipts, relationship days, open invoices by hand, agree')
    for code, f, mine, agree in everyone:
        rep.out('- ' + code + ': debt ' + str(f['debt_before_m']) + ', overdue ' + str(f['overdue_before_m']) + ', late ' + str(f['lateReceipts']) + '/' +
                str(f['prior_receipt_count']) + ', ' + str(f['observed_relationship_days']) + ' days, ' + str(len(mine['open'])) + ' open, ' + ('agree' if agree else 'DISAGREE') +
                ('' if f['reconciles'] else ', replay does not reconcile (difference ' + str(f['difference']) + ')'))
    calm.sort(key=lambda r: (not r[1]['reconciles'], not r[3], not r[2]['open'], -r[1]['prior_receipt_count']))
    hot.sort(key=lambda r: (not r[1]['reconciles'], not r[3], -r[1]['lateReceipts']))
    show('Nothing overdue as of the date (routine, within authority), best first: reconciling, agreeing, with open invoices, most receipts', calm, 4)
    show('Something overdue and a late history (escalation)', hot, 4)


# ---------------------------------------------------------------- running it

def validate(conn, rows, as_of, chosen=None, expect=None, settings=None):
    expect = expect or {}
    rep = Report()
    doc = read_records(conn)
    invoices, payments, openings, other = sheet_model(rows)
    by_alias = check_customers(rep, doc, rows)
    idx, code_of = check_invoices(rep, doc, invoices, by_alias, expect)
    check_payments(rep, doc, payments, code_of, other, expect)
    check_allocations(rep, doc, invoices, payments, code_of, expect)
    want_open = check_openings(rep, doc, openings, rows, code_of, expect)
    if settings is None:
        settings = {'currency': 'VND', 'scale': 0}
        sample = next((i['total'] for i in doc['invoices'] if i.get('total')), None)
        if sample:
            settings = {'currency': sample['currency'], 'scale': sample['scale']}
    if chosen is None:
        withopen = sorted(c for c in want_open if c in code_of.values())
        chosen = withopen[:3]   # no customers named on the command line: the first with an opening balance
    asof_open = next((o['asOf'] for o in doc['openingBalances']), as_of.isoformat())
    rep.out('')
    rep.out('Customers for checks 6 and 7: ' + ', '.join(chosen))
    check_positions(rep, doc, invoices, payments, want_open, code_of, chosen, settings)
    check_replay(rep, doc, invoices, payments, want_open, asof_open, code_of, chosen, as_of)
    candidates(rep, doc, invoices, payments, want_open, asof_open, code_of, as_of)
    return rep


def render(rep):
    head = ['# Import validation', '', '| check | result |', '|---|---|']
    head += ['| ' + k + ' | ' + v + ' |' for k, v in rep.status.items()]
    tail = ['', '## Summary', '', str(len(rep.bad)) + ' discrepancies, ' + str(len(rep.warn)) + ' notes'] + ['- ' + b for b in rep.bad]
    return '\n'.join(head + rep.lines + tail) + '\n'


# ---------------------------------------------------------------- self-test on a fictional ledger

def _selftest_hand_replay():
    """The hand replay honours the payment date when it reads which invoice a payment names (expectations worked out by hand, not by behaviour.py)."""
    inv = lambda ref, total, issue, row: {'ref': ref, 'rows': [row], 'total': total, 'issue': issue, 'terms': {'1' if ref == 'B' else '30'}}
    pay = lambda docdate, cr, mention, row: {'docdate': docdate, 'row': row, 'cr': cr, 'mention': mention, 'desc': ''}
    as_of = date(2030, 3, 1)
    # (1) opening debt 100 (2030-01-01); a payment of 100 on 2030-01-05 mentions B, which is issued 2030-02-01 (100, due 2030-02-02): the payment cannot
    # be B's, so it clears the opening debt and B stays unpaid and overdue: debt 100, opening remaining 0, overdue 100
    r = hand_replay('C', as_of, {'C': {'B': inv('B', 100, '2030-02-01', 3)}}, {'C': [pay('2030-01-05', 100, 'B', 2)]}, {'C': 100}, '2030-01-01')
    assert (r['debt_before_m'], r['opening_owing'], r['overdue_before_m'], r['open']) == (100, 0, 100, [('B', '2030-02-02', 100)]), r
    # (2) an ordinary match: A (100, issued 2030-01-01) is paid by a payment of 100 on 2030-01-10 that names it: nothing owed, nothing overdue
    r = hand_replay('C', as_of, {'C': {'A': inv('A', 100, '2030-01-01', 2)}}, {'C': [pay('2030-01-10', 100, 'A', 3)]}, {}, '2030-01-01')
    assert (r['debt_before_m'], r['overdue_before_m'], r['open'], r['credit_unapplied']) == (0, 0, [], 0), r
    # (3) no opening debt: a payment of 100 on 2030-01-05 naming B (issued 2030-02-01) is customer credit, applied when B is issued: debt 0, nothing overdue
    r = hand_replay('C', as_of, {'C': {'B': inv('B', 100, '2030-02-01', 3)}}, {'C': [pay('2030-01-05', 100, 'B', 2)]}, {}, '2030-01-01')
    assert (r['debt_before_m'], r['overdue_before_m'], r['open'], r['credit_unapplied']) == (0, 0, [], 0), r


def _selftest():
    mk = lambda **kw: {'row': 0, 'cust': '', 'inv': '', 'invdate': None, 'docdate': None, 'posting': None, 'docno': '', 'desc': '', 'mention': '',
                       'dr': 0, 'cr': 0, 'term': '', 'rtype': 'Transaction', 'ttype': '', 'owed': 0, 'adv': 0, **kw}
    rows = [
        mk(cust='9001', ttype='Opening balance', rtype='Opening Balance', owed=500),
        mk(cust='9001', inv='7', invdate='2030-01-10', docdate='2030-01-10', dr=1000, term='30', ttype='Invoice revenue'),
        mk(cust='9001', inv='7', invdate='2030-01-10', docdate='2030-01-10', dr=100, term='30', ttype='VAT'),
        mk(cust='9001', inv='008', invdate='2030-03-01', docdate='2030-03-01', dr=2000, term='30', ttype='Invoice revenue'),
        mk(cust='9001', docdate='2030-02-20', cr=1100, docno='R1', mention='7', ttype='Payment'),
        mk(cust='9001', docdate='2030-03-15', cr=300, docno='R2', desc='Payment for invoice 8 mentioned', ttype='Payment'),
        mk(cust='9001', docdate='2030-03-20', cr=50, docno='R3', mention='99', ttype='Payment'),
        mk(cust='9002', inv='A1', invdate='2030-02-01', docdate='2030-02-01', dr=400, term='15', ttype='Invoice revenue'),
        mk(cust='9002', docdate='2030-02-10', cr=400, docno='R4', ttype='Payment'),
        mk(cust='9002', docdate='2030-02-11', cr=7, docno='R5', ttype='Adjustment'),
    ]
    for n, r in enumerate(rows, start=2):
        r['row'] = n
    c = sqlite3.connect(':memory:')
    for t in ('customers', 'invoices', 'payments', 'allocations', 'opening_balances'):
        c.execute('CREATE TABLE ' + t + ' (id TEXT, seq INTEGER, data TEXT)')
    money = lambda n: {'minorUnits': str(n), 'currency': 'VND', 'scale': 0}
    put = lambda t, i, d: c.execute('INSERT INTO ' + t + ' VALUES (?,?,?)', (d['id'], i, json.dumps({**d, 'status': 'active', 'history': []})))
    put('customers', 1, {'id': 'c1', 'name': 'Customer 9001', 'aliases': ['9001']})
    put('customers', 2, {'id': 'c2', 'name': 'Customer 9002', 'aliases': ['9002']})
    put('invoices', 1, {'id': 'i7', 'customerId': 'c1', 'reference': '7', 'issueDate': '2030-01-10', 'originalDueDate': '2030-02-09', 'total': money(1100)})
    put('invoices', 2, {'id': 'i8', 'customerId': 'c1', 'reference': '008', 'issueDate': '2030-03-01', 'originalDueDate': '2030-03-31', 'total': money(2000)})
    put('invoices', 3, {'id': 'iA', 'customerId': 'c2', 'reference': 'A1', 'issueDate': '2030-02-01', 'originalDueDate': '2030-02-16', 'total': money(400)})
    put('payments', 1, {'id': 'p1', 'customerId': 'c1', 'receivedDate': '2030-02-20', 'amount': money(1100), 'reference': 'R1'})
    put('payments', 2, {'id': 'p2', 'customerId': 'c1', 'receivedDate': '2030-03-15', 'amount': money(300), 'reference': 'R2'})
    put('payments', 3, {'id': 'p3', 'customerId': 'c1', 'receivedDate': '2030-03-20', 'amount': money(50), 'reference': 'R3'})
    put('payments', 4, {'id': 'p4', 'customerId': 'c2', 'receivedDate': '2030-02-10', 'amount': money(400), 'reference': 'R4'})
    put('allocations', 1, {'id': 'a1', 'paymentId': 'p1', 'invoiceId': 'i7', 'customerId': 'c1', 'amount': money(1100)})
    put('allocations', 2, {'id': 'a2', 'paymentId': 'p2', 'invoiceId': 'i8', 'customerId': 'c1', 'amount': money(300)})
    put('opening_balances', 1, {'id': 'o1', 'customerId': 'c1', 'asOf': '2030-01-09', 'amount': money(500)})
    expect = {'invoices': 3, 'payments': 4, 'allocations': 2, 'openings': 1, 'notInFile': 1}
    ok = validate(c, rows, date(2030, 4, 1), ['9001', '9002'], expect)
    assert not ok.bad, ok.bad
    # a changed invoice total, a doubled payment and a wrong allocation must be found
    c.execute("UPDATE invoices SET data = replace(data, '\"2000\"', '\"2100\"') WHERE id = 'i8'")
    put('payments', 5, {'id': 'p5', 'customerId': 'c2', 'receivedDate': '2030-02-10', 'amount': money(400), 'reference': 'R4'})
    put('allocations', 3, {'id': 'a3', 'paymentId': 'p4', 'invoiceId': 'iA', 'customerId': 'c2', 'amount': money(900)})
    put('payments', 6, {'id': 'p6', 'customerId': 'c1', 'receivedDate': '2030-01-05', 'amount': money(10), 'reference': 'R6'})   # received before invoice 7 was issued
    put('allocations', 4, {'id': 'a4', 'paymentId': 'p6', 'invoiceId': 'i7', 'customerId': 'c1', 'amount': money(10)})
    bad = validate(c, rows, date(2030, 4, 1), ['9001', '9002'], expect)
    text = ' '.join(bad.bad)
    for needle in ('stored total 2100', 'is not a payment row', 'not within min', 'stored payment count 6', 'before the invoice was issued'):
        assert needle in text, (needle, bad.bad)
    _selftest_hand_replay()
    print('selftest ok: clean ledger passes, ' + str(len(bad.bad)) + ' injected faults found')


def main(argv):
    if '--selftest' in argv:
        _selftest()
        return 0
    opts, args = {}, []
    it = iter(argv)
    for a in it:
        if a in ('--sheet', '--as-of', '--customers', '--expect', '--out'):
            opts[a] = next(it)
        else:
            args.append(a)
    if len(args) != 2 or '--sheet' not in opts or '--as-of' not in opts:
        print(__doc__)
        return 2
    conn = sqlite3.connect('file:' + os.path.abspath(args[0]) + '?mode=ro', uri=True)
    rows = read_rows(args[1], opts['--sheet'])
    chosen = opts['--customers'].split(',') if '--customers' in opts else None
    expect = {k: int(v) for k, v in (x.split('=') for x in opts['--expect'].split(','))} if opts.get('--expect') else {}
    rep = validate(conn, rows, date.fromisoformat(opts['--as-of']), chosen, expect)
    text = render(rep)
    print(text)
    if '--out' in opts:
        Path(opts['--out']).write_text(text)
    return 1 if rep.bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
