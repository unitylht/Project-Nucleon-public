"""Local, fictional-data payment-extension workflow with a replaceable agent adapter.

Agent modes: live (configured local model), mock (deterministic scripted adapter, not a model)
and unavailable (simulated model outage -> disclosed manual fallback). Python standard library only.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import contextlib
import copy
import hashlib
import json
import queue
import re
import secrets
import sqlite3
import statistics
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from difflib import SequenceMatcher
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from agent import (decider_words, BRIEF_FORMAT, KEY_FORMAT, PROMPT_VERSION, SERVER_CONTROLLED, WEEKDAYS, AgentRunner, Evidence, MockAdapter, ToolDispatcher, ToolError,
                   MONTH_WORD, UnavailableAdapter, _require_args, _text_arg, appears_in, calendar_date, days_text, deterministic_extract, display_date, evidence_ref, extension_facts,
                   fingerprint, invoice_choices, is_open, money_text, position_note, ref_key, render_brief, signed_money, steps_text, unmatched_payments)
from coordinator import (CAPABILITIES, CLASSIFY_SCHEMA, COUNTERS_NOTE, DAY_LIMIT, DESK_TOOL_NAMES, IMPLEMENTED_KINDS,
                         INTERPRET_SCHEMA, NUMBER_WORDS, classify_messages, STAFF_MOVED, STAFF_SEE, STEP_FAILED, TOOL_KINDS, WHERE_IS, agent_tools, case_summary, facts_for_model, interpret_messages, prepare_needs,
                         prepare_suggestion, said_date, said_days, said_reason, staff_safe, tools_for, validate_interpretation)
from model_adapter import AdapterError, OpenAIChatAdapter, load_model_config
import agent_views
import delegation
import doctor
import impact
import notify
import research
import importer
import legacy_keys
import outcomes
from behaviour import (CALCULATION_VERSION, CHECK_NAMES, EFFECTS, FEATURES, NO_LIMIT, NO_MODEL, OWN_MISSING, STAFF_NO_LIMIT, UNKNOWN, assessment_facts,
                       check_rows, checks_for, facts_view, followed, incomplete_text, opening_paid_text, recommend)
from records import (AUTHORITY_CHECKS, RecordsError, parse_money, active, allocated_from, amount_of, authority_of, validate_authority, minor, active_view, allocate, answer_inclusion, answer_statement, checklist, correct, customer_position,
                     allocations_to, applies_to, coverage_view, customer_blocks, empty_document, exact_outstanding, invoice_position, mark_unrelated, name_key, new_coverage,
                     new_customer, new_invoice, new_note, new_opening, new_payment, note_action, opening_of, opening_view, parse_day, reason_value,
                     retire_coverage, settings_of, split_by_customer, text_value, today_for, validate_settings)

ROOT = Path(__file__).resolve().parent
WEB = ROOT / 'web'
_STATIC_VERSIONS = {}   # path -> (mtime, size, digest): the content hash of each file under web/, recomputed when the file changes


def static_version(path, data=None):
    """A short hash of the file's content, for the ?v= in its address and its ETag."""
    st = path.stat()
    known = _STATIC_VERSIONS.get(path)
    if known and known[0] == st.st_mtime_ns and known[1] == st.st_size:
        return known[2]
    digest = hashlib.sha256(path.read_bytes() if data is None else data).hexdigest()[:12]
    _STATIC_VERSIONS[path] = (st.st_mtime_ns, st.st_size, digest)
    return digest


def page_html():
    """index.html with each static/<file> address versioned (static/<file>?v=<hash>), so a change to a file reaches every browser on the next page load."""
    html = (WEB / 'index.html').read_text(encoding='utf-8')
    def versioned(m):
        target = WEB / m.group(1)
        return m.group(0) if not target.is_file() else '%s?v=%s' % (m.group(0), static_version(target))
    return re.sub(r'static/([a-z0-9-]+(?:/[a-z0-9.-]+)?\.(?:css|js))(?=")', versioned, html).encode('utf-8')
STATIC_TYPES = {'.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.woff2': 'font/woff2',
                '.svg': 'image/svg+xml', '.txt': 'text/plain; charset=utf-8'}
CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self' data:; connect-src 'self'; "
       "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
ROLES = ('staff', 'owner', 'operator')
CASE_ROLES = ('staff', 'owner')
AGENT_ID, AGENT_NAME = 'ai_agent', 'AI Agent'
LAB_ROLE = 'nucleonl_lab_role'   # the AI Agent's selected role, shared with the Lab (which sets it under its own root)
ROLE_WORDS = {'staff': 'staff', 'owner': 'owner', 'operator': 'demo console'}
# A demo reset or start-empty deletes every table here. The Owner's delegation policies, the decision memory (cases, live and fictional) and the facts
# Staff confirmed are DATA, not settings: a reset returns the practice workspace to no policy (version 0: advisory, nothing executes) and no memory.
DATA_TABLES = ('requests', 'events', 'idempotency', 'runs', 'batches', 'profiles', 'record_ops', 'statements', 'threads', 'turns', 'actions',
               'delegation_policies', 'decision_cases', 'confirmed_facts', 'case_events', 'ui_events', 'notices')
ACTION_TTL_HOURS = 24   # a proposed action stays confirmable this long: a read then reports it expired, and a confirm writes it
ACTION_VERSION = 1   # the shape of an action as a person was shown it; a confirm names the version it was shown (STALE_ACTION_VIEW)
MAX_EXTENSION_DAYS = 90   # prepareRequest: the longest extension it proposes when given in days after the current due date
REASON_LIMIT = 500   # characters of the assistant's draft reason, and of the reason a person confirms
LIVE_CASE = ('gathering_evidence', 'awaiting_owner', 'on_hold')   # a decision case still open: at most one per (kind, subject)
DOWNLOADS = ('/api/delegation/training.csv', '/api/delegation/research/model.json')   # plain links: the role comes in the address (?role=owner)
ONE_AT_A_TIME_SECONDS = 20   # the assistant (a service session) opens one new case per Staff message: a second one for another customer this soon after is refused
CASE_TEXT = 1000   # characters of the context the assistant relays from chat (stored as chat-relayed, never as verification)
AGENT_DECIDER = 'nucleon_agent'   # decidedBy of a decision the agent took inside the Owner's delegation policy (never a Staff or service actor's id)
STRUCTURED_ADAPTER = 'confirmed-action-v1'   # what builds the case of a request opened from a confirmed action: application code, never a model
TOOL_OPS_KEEP_DAYS = 90   # how long a finished tool operation's key keeps its answer (App.recover); a retry later than this is treated as new
# Business records, one table per kind. The agent and the record operations work on a document-shaped projection of these
# tables (App.fixture); the tables are the only writable source. Payments and allocations appear in the projection only
# when they exist, so the projection of a records document migrated from Slice 2 is identical to that document.
RECORD_TABLES = {'customers': (), 'invoices': (('customer_id', 'customerId'),), 'notes': (),
                 'payments': (('customer_id', 'customerId'),), 'allocations': (('payment_id', 'paymentId'), ('invoice_id', 'invoiceId')),
                 'openingBalances': (('customer_id', 'customerId'),), 'coverage': ()}
TABLE = {'openingBalances': 'opening_balances'}   # other kinds are stored in a table of the same name
OPTIONAL_LISTS = ('payments', 'allocations', 'openingBalances', 'coverage')
STATES_BEFORE_DECISION = {'received', 'analysing', 'needs_information', 'awaiting_owner', 'preparation_failed'}
ACTIVE_STATES = {'received', 'analysing'}
MAX_STALE_RERUNS = 2
CALLERS = {'live': 'live_model', 'mock': 'mock_adapter', 'unavailable': 'live_model'}
SCOPE_KINDS = ('business', 'customer', 'case', 'unassigned')   # what a statement is about
LINE_KINDS = ('observation', 'relationship', 'expectation', 'guidance', 'constraint')
NO_REASON = 'No reason given; prepared on the desk.'   # a prepared decision's reason when the owner gave none in their own words
# Words that only restate a decision ("approve 14 days for Bayside Café, then"): a reason of these alone is no reason. Numbers, months,
# the customer's name and the invoice reference are left out as well (_prepareDecision).
DECISION_WORDS = {'approve', 'approved', 'decline', 'declined', 'day', 'days', 'week', 'weeks', 'fortnight', 'a', 'an', 'for', 'to', 'until', 'then',
                  'it', 'the', 'and', 'of', 'on', 'ok', 'okay', 'yes', 'please', 'invoice', 'by'}
# A new decline is prepared only in the owner's own words (_prepareDecision): no date implies it, as a date implies an approval.
DECLINE_SAID = re.compile(r"(?<!not )(?<!n't )(?<!n’t )(?<!never )\b(?:declin|refus|reject|den(?:y|ied))\w*", re.I)   # "don't decline" is none
# A limit said ("up to 14 days this time") is guidance to keep, not a decision: with nothing prepared, a message with a limit and no
# decision word is asked about (_prepareDecision), never prepared from.
LIMIT_SAID = re.compile(r'\b(?:up\s+to|at\s+most|no\s+more\s+than|max(?:imum)?)\b', re.I)
DECISION_SAID = re.compile(r'\b(?:approv\w*|give\s+(?:them|him|her|it)|go\s+(?:with|for|ahead)|extend\w*|let\s+them|grant\w*|allow\w*|accept\w*|'
                           r'prepar\w*|make\s+it|declin\w*|refus\w*|reject\w*)\b', re.I)
# A message stating a figure of its own (any digit outside an invoice reference, an ordinal, a month, a weekday, a week, month or
# fortnight, a spelled number): then no figure of an earlier preparation stands in for it (_prepareDecision).
STATES_FIGURE = re.compile(r'\d|\b(?:' + MONTH_WORD + '|' + '|'.join(WEEKDAYS) + r'|tomorrow|weeks?|months?|fortnights?|two|three|four|five|six|seven|'
                           r'eight|nine|ten|eleven|twelve|twenty|thirty|the\s+(?:first|second|third)|fourth|fifth|sixth|seventh|eighth|ninth|tenth|'
                           r'eleventh|twelfth|thirteenth|fourteenth|fifteenth|sixteenth|seventeenth|eighteenth|nineteenth|twentieth|thirtieth)\b', re.I)
OFF_IN_SETUP = 'turned off under Setup → Agent tools'
UNIT_RULES = 2   # version of the money-unit rules (workbook-wide headings, magnitude); a proposal stored under older rules is re-checked
STALE_PROPOSAL = 'This proposal was made before the currency check. Attach the file again.'
IMPORT_PROPOSALS = 'importProposals:'   # meta key prefix: one import proposal each, its file and its current version (DeskTools._proposeImport)
KEPT_PROPOSALS = 5   # the most recent proposals kept; older ones go when a new one is made, and a new proposal supersedes the files of the others (their summaries and batches stay)
IMPORT_SOURCE = 'Spreadsheet import'   # a proposal's batches' source label unless the person names one: steady, so a payment imported again is known
MAX_ATTACHMENT = 2_500_000   # bytes, as /api/imports
STEP_TOOLS = {'open_request': 'openRequest', 'prepare_decision': 'prepareDecision', 'request_suggestion': 'requestSuggestion',
              'add_context': 'interpretStatement'}   # the desk tool each of actions_for's steps needs
# The activity staff may see: every kind the case flow writes except the questions (question.*; view() lets staff see those about a
# question asked of staff) and the advisory suggestion (suggestion.updated). An allowlist, so a kind added later stays with the owner
# until it is listed here.
STAFF_EVENTS = frozenset(('request.received', 'analysis.queued', 'analysis.started', 'agent.extracted', 'model.call', 'tool.executed',
                          'tool.rejected', 'suggestion.suppressed', 'analysis.finished', 'analysis.failed', 'analysis.superseded',
                          'analysis.discarded', 'preparation.failed', 'clarification.answered', 'decision.committed', 'request.completed',
                          'evidence.baseline_recorded', 'evidence.version_updated', 'evidence.key_format_updated',
                          'evidence.changed_after_decision', 'concern.raised', 'concern.answered', 'request.withdrawn'))
STAFF_QUESTION = ('id', 'kind', 'from', 'question', 'why', 'status', 'answeredBy')   # what staff see of a question asked of them
DELEGATION_WRITE = re.compile(r'/api/delegation/(?:policy(?:/(?:pause|resume))?|observe-outcomes|sweep-tacit-consent|research/(?:refit|settings)|schedules(?:/[\w-]+/cancel)?)|/api/notices/read|/api/decision-cases/[\w-]+/(?:decide|feedback|viewed|evidence-request)')   # writes only a person's browser makes (Origin required)
# The append-only timeline of a decision case (table case_events). `actor` is who or what caused the change: the agent (its own decision), the owner, staff, or the system
# (deterministic backend rules and sweeps). A row is written in the SAME transaction as the state change it records, and never for a replay.
CASE_EVENT_KINDS = ('created', 'evaluated', 'evidence_requested', 'evidence_submitted', 'escalated', 'held', 'decided', 'feedback', 'override', 'closed',
                    'outcome_observed', 'tacit_agree', 'viewed')
CASE_EVENT_ACTORS = ('agent', 'owner', 'staff', 'system')
OWNER_ONLY_EVENTS = ('feedback', 'tacit_agree', 'viewed')   # the Owner's own signals: not on the timeline Staff read (case_view shows Staff no feedback either)
UI_EVENT_KINDS = ('page_enter', 'page_leave', 'click', 'decide_start', 'decide_done')   # what the pages report about their own use (D11); nothing else is stored
UI_EVENTS_PER_MINUTE = 60   # per session; the rest of a minute's events are dropped without an error
UI_BATCH_MAX = 50
VIEWED_EVERY_SECONDS = 60   # at most one `viewed` event per case in this many seconds (a page that reloads must not flood the timeline)
INSTRUCTION_LIKE = re.compile(r'\b(?:system|override|ignore (?:all|any|previous|your)|you are (?:now )?authori[sz]ed|approvecredit|sendmessage|mark it approved|developer mode)\b', re.I)


def now():
    return datetime.now(timezone.utc).isoformat()


def case_event(conn, case_id, kind, actor, policy_version, data=None, at=None):
    """Append one row to the case's timeline on `conn` (a connection or cursor), inside the caller's transaction: never commits, so the row and the state change it
    records stand or fall together. `data` is a small JSON object (the handling, outcome, reason or verdict that belongs to the kind), never the whole case."""
    if kind not in CASE_EVENT_KINDS or actor not in CASE_EVENT_ACTORS:
        raise ValueError('unknown case event: ' + str(kind) + ' by ' + str(actor))
    conn.execute('INSERT INTO case_events (case_id, kind, at, actor, policy_version, data) VALUES (?,?,?,?,?,?)',
                 (case_id, kind, at or now(), actor, policy_version, json.dumps(data or {})))


def uid(prefix):
    return prefix + '_' + secrets.token_hex(8)


def log(*parts):
    print(now(), *parts, flush=True)


class APIError(Exception):
    def __init__(self, status, code, message, field=None):
        self.status, self.code, self.message, self.field = status, code, message, field


def require(condition, status, code, message, field=None):
    if not condition:
        raise APIError(status, code, message, field)


def refusal(status, code, message, **extra):
    """An APIError that also carries fields for the response body (the action, the request in the way)."""
    exc = APIError(status, code, message)
    exc.extra = extra
    return exc


def structured_origin(s):
    """Where a structured request came from, in words: a confirmed action, or a delegation case (the assistant's resolveDecision)."""
    return 'confirmed action ' + s['actionId'] if s.get('actionId') else 'delegation case ' + str(s.get('caseId'))


def action_state(a):
    """The status a reader is told for an action: a proposed one past its expiry reads 'expired'. Reading writes nothing; confirm_action
    and cancel_action write 'expired' when they refuse one, and a new proposal for the invoice settles it."""
    return 'expired' if a['status'] == 'proposed' and datetime.fromisoformat(a['expiresAt']) <= datetime.now(timezone.utc) else a['status']


def amount_items(ev, invoice):
    """Open points about the amount still owed, written by code: how an exact amount was reached, or why it is not exact."""
    position = invoice.get('position')
    if position and position.get('exact'):
        exact = position['exact']
        statements = [c for c in ev.fixture.get('coverage', []) if c['id'] in exact['coverage']]
        return [{'kind': 'exact_outstanding', 'text': 'Exactly ' + money_text(exact['amount']) + ' was still owed on this invoice as of ' +
                 display_date(exact['asOf']) + ': ' + steps_text(exact['steps']) + '. Payment records for this customer are confirmed complete from ' +
                 display_date(exact['paymentsFrom']) + ' to ' + display_date(exact['asOf']) + ' (' + '; '.join(
                     c['sourceLabel'] + ', confirmed by the ' + (c.get('confirmedRole') or 'owner') for c in statements) + '), which includes '
                 'that there are no credit notes or other adjustments in that period; this version cannot record them.' +
                 (' Payments after that date allocated to it come to ' + money_text(exact['later']) + ', so at most ' + money_text(position['atMost']) +
                  ' is owed now.' if exact['later'] else '')}]
    if position:
        inclusion, on = position['inclusion'], position['statedAsOf'] and display_date(position['statedAsOf'])
        items = [{'kind': 'payments_allocated', 'text': money_text(position['allocated']) + ' from recorded payments is allocated to this invoice. At most ' +
                  money_text(position['atMost']) + ' is still owed: ' + position_note(position) + '. Payment records are not confirmed complete, '
                  'so this is an upper bound, not an exact amount.'}]
        if inclusion['reconciles']:
            items.append({'kind': 'statement_reconciles', 'text': 'The invoice amount less the payments allocated up to ' + on + ' equals the amount '
                          'stated still owed then. That suggests they were already reflected in it, but an unrecorded credit would reconcile just '
                          'as well, so it is not assumed: they are not taken off, and a person confirms it under Records.'})
        elif inclusion['unresolved']:
            items.append({'kind': 'statement_inclusion_unresolved', 'text': str(len(inclusion['unresolved'])) + ' payment(s) made on or before ' + on +
                          ' are allocated to this invoice. Whether the amount stated still owed then already reflected them is not recorded, so '
                          'they are not taken off it. If it did not, less is owed. Answer this under Records.'})
        if inclusion['stale']:
            items.append({'kind': 'statement_answer_stale', 'text': 'An earlier answer about whether a payment was already reflected was given about a '
                          'different statement of the amount still owed, so it no longer applies.'})
        items += [{'kind': 'records_conflict', 'text': 'The records about this invoice contradict each other: ' + c} for c in position['conflicts']]
        items += [{'kind': 'code_check', 'text': c} for c in position['checks']]
        return items + not_exact_items(position['notExact'])
    items = []
    if invoice.get('outstandingAmount') is None:
        items = [{'kind': 'outstanding_not_recorded', 'text': 'No amount still owed is recorded for this invoice, so the brief does not say how much is outstanding.'}]
    elif invoice.get('outstandingAsOf'):
        source = {'file': 'an import', 'correction': 'a correction', 'opening_balance': 'the opening balance'}.get(invoice.get('outstandingSource'), 'manual entry')
        items = [{'kind': 'stated_outstanding', 'text': 'The amount still owed was stated as of ' + display_date(invoice['outstandingAsOf']) + ' (' + source +
                  '). Payments after that date are not recorded.'}]
    cid = invoice['customerId']
    if opening_of(ev.fixture, cid) or any(applies_to(c, cid) for c in ev.fixture.get('coverage', [])):   # the customer's records are being completed
        items += not_exact_items(exact_outstanding(ev.fixture, invoice)[1])
    return items


def long_date(iso):
    """A date for customers, written out so it can't be misread in any locale (QA U4): Friday 30 October 2026."""
    d = calendar_date(iso)
    return d.strftime('%A') + ' ' + str(d.day) + ' ' + d.strftime('%B %Y')


def trail(actor):
    """Who acted, as the audit trail keeps it beside the id: the actor's name (the AI Agent has one) and the effective role."""
    return {'actorName': actor.get('name'), 'actorRole': actor['role']}


def actor_words(actor):
    """The actor in words: "the owner", or "AI Agent (as owner)" for a named actor."""
    return actor['name'] + ' (as ' + actor['role'] + ')' if actor.get('name') else ROLE_WORDS.get(actor['role'], actor['role'])


def describe_change(doc, parts, result, actor):
    """A records change in plain words, naming the record and the role that made it (QA B5, U7): shown in case activity and flags."""
    kind, action = parts[0], (parts[2] if len(parts) == 3 else 'correct' if len(parts) == 2 else 'add')
    record = result.get('record') or (result.get('records') or [{}])[0]
    by_id = {r['id']: r for k in ('customers', 'invoices', 'payments') for r in doc.get(k, [])}
    owner = by_id.get(record.get('customerId'), {}).get('name')
    who = ' by ' + actor_words(actor)
    verb = {'add': 'added', 'correct': 'corrected', 'remove': 'removed', 'confirm': 'confirmed', 'retire': 'retired', 'unrelated': 'marked',
            'inclusion': 'answered', 'statement': 'answered'}.get(action, 'changed')
    if kind == 'invoices':
        what = 'Invoice ' + record.get('reference', '') + (' (' + owner + ')' if owner else '')
        return (what + ': whether it is part of the opening balance was answered' if action == 'inclusion' else what + ' ' + verb) + who
    if kind == 'payments':
        what = ('Credit ' if record.get('kind') == 'credit' else 'Payment ') + (record.get('reference') or '') + (' ' if record.get('reference') else '') + \
            ('of ' + money_text(record['amount']) + ' ' if record.get('amount') else '') + ('received ' + display_date(record['receivedDate']) if record.get('receivedDate') else '')
        what = what.strip() + (' from ' + owner if owner else '')
        return (what + ': ' + ('marked as not for an open invoice' if record.get('notForOpenInvoices') else 'unmarked') if action == 'unrelated' else
                what + ': whether it is part of the opening balance was answered' if action == 'inclusion' else
                what + (' recorded' if action == 'add' else ' ' + verb)) + who
    if kind == 'allocations':
        invoice = by_id.get(record.get('invoiceId'), {})
        payment = by_id.get(record.get('paymentId'), {})
        target = 'invoice ' + invoice.get('reference', '') + (' (' + by_id.get(invoice.get('customerId'), {}).get('name', '') + ')' if invoice else '')
        if action == 'statement':
            return 'An answer about whether a payment was already counted in the amount stated still owed on ' + target + who
        amount = money_text(record['amount']) + ' ' if record.get('amount') else ''
        return ('Allocation of ' + amount + 'to ' + target + ' removed' if action == 'remove' else
                (amount or 'Money ') + 'from payment ' + (payment.get('reference') or '') + ' allocated to ' + target).replace('  ', ' ') + who
    if kind == 'openingBalances':
        return 'Opening balance for ' + (owner or 'a customer') + ' ' + verb + who
    if kind == 'coverage':
        return 'A completeness statement was ' + ('retired' if action == 'retire' else 'confirmed') + who
    if kind == 'customers':
        return 'Customer ' + record.get('name', '') + ' ' + verb + who
    if kind == 'notes':
        return 'A note was ' + verb + who
    return 'Records changed' + who


def revert_effects(doc, batch, impact):
    """What a revert would do to the records, in plain words (QA B3). Nothing is deleted: records are marked reverted or restored."""
    by_id = {r['id']: r for kind in ('invoices', 'payments', 'customers', 'allocations') for r in doc.get(kind, [])}
    name = lambda record: by_id.get(record.get('customerId'), {}).get('name', '')
    lines = []
    for invoice_id in impact.get('revertInvoices', []):
        lines.append('Invoice ' + by_id[invoice_id]['reference'] + ' (' + name(by_id[invoice_id]) + ') is marked reverted and no longer used.')
    for payment_id in impact.get('revertPayments', []):
        p = by_id[payment_id]
        lines.append('Payment ' + money_text(p['amount']) + ' received ' + (display_date(p['receivedDate']) if p.get('receivedDate') else '(no received date)') + (' (' + p['reference'] + ')' if p.get('reference') else '') +
                     ' from ' + name(p) + ' is marked reverted.')
    for opening in doc.get('openingBalances', []):
        if opening['id'] in impact.get('revertOpenings', []):
            lines.append('The opening balance of ' + money_text(opening['amount']) + ' as at ' + display_date(opening['asOf']) + ' for ' + name(opening) + ' is marked reverted.')
    for allocation_id in impact.get('revertAllocations', []):
        a = by_id[allocation_id]
        lines.append('Its allocation of ' + money_text(a['amount']) + ' to invoice ' + by_id[a['invoiceId']]['reference'] + ' is removed.')
    for record_id in impact.get('restore', []):
        r = by_id[record_id]
        lines.append(('Invoice ' + r['reference'] if 'reference' in r and 'receivedDate' not in r else 'A payment of ' + money_text(r['amount'])) +
                     ' gets back the values it had before this import.')
    for record_id, _ in impact.get('keep', []):
        r = by_id[record_id]
        lines.append(('Invoice ' + r['reference'] if 'receivedDate' not in r else 'A payment of ' + money_text(r['amount'])) +
                     ' stays: a later import lists it with the same values, and it is credited to that import.')
    taken = ((batch.get('params') or {}).get('resolutions') or {}).get('conflicts', {})
    rejected = sum(1 for r in batch['preview']['rows'] if r['status'] == 'conflict' and taken.get(str(r['row'])) != 'take')
    if rejected:
        lines.append('It removes ' + str(rejected) + ' conflicting row(s) a person rejected by keeping the recorded values. Those values stay as they '
                     'are, and the rows no longer hold back a revert of the import the values came from.')
    gone = {*impact.get('revertInvoices', []), *impact.get('revertPayments', [])}
    for customer_id in batch['result']['customers']:
        c = by_id[customer_id]
        if active(c) and not any(r.get('customerId') == customer_id and active(r) and r['id'] not in gone and r['id'] not in dict(impact.get('keep', []))
                                 for r in doc['invoices'] + doc.get('payments', [])):
            lines.append('Customer ' + c['name'] + ' is marked reverted: it came from this import and would have no records left.')
    if not lines:
        same = batch['preview']['counts'].get('unchanged', 0)
        lines.append('This import added or changed no records. Reverting it only removes its note that ' + str(same) + ' row(s) were also in this '
                     'file, so a later revert of the earlier import is not held back by it.')
    return lines


def revert_review_lines(review):
    plural = lambda n, one, many: str(n) + ' ' + (one if n == 1 else many)
    return [line for line, show in (
        (plural(len(review['pendingCases']), 'case waiting for the owner is', 'cases waiting for the owner are') + ' prepared again.', review['pendingCases']),
        (plural(len(review['decidedCases']), 'decided case keeps its', 'decided cases keep their') + ' decision and gets a note that the records changed.',
         review['decidedCases']),
        (plural(len(review.get('answers', [])), 'answer', 'answers') + ' about these records will no longer apply.', review.get('answers')),
        ('The completeness statement that came with this import is removed, and "complete to" dates are recalculated.', review.get('coverage')),
    ) if show]


def not_exact_items(reasons):
    return [{'kind': 'not_exact', 'text': 'Not an exact amount, because: ' + ' '.join(reasons)}] if reasons else []


def paid_text(invoice):
    if invoice.get('position'):
        return ('Payments recorded and allocated to invoice ' + invoice['reference'] + ' cover it in full. Check the invoice number, '
                'or the allocations under Records, then prepare the case again.')
    return ('Records state invoice ' + invoice['reference'] + ' was fully paid' +
            (' as of ' + display_date(invoice['outstandingAsOf']) if invoice.get('outstandingAsOf') else '') +
            '. Check the invoice number, or correct the record under Records and prepare the case again.')


def customer_items(ev, customer_id):
    """Open points about the customer's account, written by code: the balance from an opening balance, what is unresolved about
    it, and recorded payments. A customer's balance or net of records is never the settlement of one invoice."""
    items = opening_items(opening_view(ev.fixture, customer_id), coverage_view(ev.fixture, customer_id))
    if not ev.fixture.get('payments'):
        return items
    position = customer_position(ev.fixture, customer_id, settings_of(ev.fixture))
    if not position['payments']:
        return items
    if int(position['unallocatedOpen']['minorUnits']) > 0:
        items.append({'kind': 'unallocated_payments', 'text': money_text(position['unallocatedOpen']) + ' received, not matched to an invoice, '
                      'for this customer. It may relate to this invoice; allocating it is a person\'s decision.'})
    if int(position['markedUnrelated']['minorUnits']) > 0:
        items.append({'kind': 'payments_marked_unrelated', 'text': money_text(position['markedUnrelated']) + ' in recorded payments is not allocated, and a '
                      'person marked it as not for an open invoice.'})
    if position['recordedNet'] is not None and not opening_view(ev.fixture, customer_id):
        items.append({'kind': 'recorded_net', 'text': 'Recorded invoices minus recorded payments for this customer: ' + money_text(position['recordedNet']) +
                      '. This is a difference of records, not a statement of what is owed; records may be incomplete.'})
    return items


def entered_by(record):
    """Who entered a record, or corrected it last (QA B2: an opening balance did not say whether staff or the owner entered it)."""
    by = record.get('setBy') or record.get('origin') or {}
    role = {'owner': 'the owner', 'staff': 'staff'}.get(by.get('role'), 'a person')
    return ('corrected by ' if by.get('kind') == 'correction' else 'from an import, applied by ' if by.get('kind') == 'file' else 'entered by ') + role


def entered_text(record):
    """Where a payment (or its allocation) came from, in words with the date: "From the import of <file> on <date>", "Entered by AI Agent
    (as owner) on <date>" (the same source words as the stated-amount provenance: an import, a correction, a manual entry)."""
    by = record.get('setBy') or record.get('origin') or {}
    kind, day = by.get('kind'), (by.get('at') or '')[:10]
    on = ' on ' + display_date(day) if day else ''
    who = actor_words({'name': by.get('actorName'), 'role': by.get('actorRole') or by.get('role') or 'person'}) if by.get('actorName') or by.get('role') or by.get('actorRole') else 'a person'
    if kind == 'file':
        return 'From the import of ' + (by.get('fileName') or by.get('sourceLabel') or 'a file') + on
    if kind == 'correction':
        return 'Corrected by ' + who + on
    if kind in ('manual', 'answer'):
        return 'Entered by ' + who + on
    return 'Source not recorded'


def opening_items(view, cover=None):
    if not view:
        return []
    invoices_to, payments_to = [(cover or {}).get(kind, {}).get('completeTo') for kind in ('invoices', 'payments')]
    # Each record type is named, so the brief never says payments are complete and then that the records are not (QA U8).
    completeness = ('Invoice and payment records for this customer are confirmed complete to ' + display_date(min(invoices_to, payments_to)) + '.'
                    if invoices_to and payments_to else
                    'Payment records are confirmed complete to ' + display_date(payments_to) + ', but invoice records are not confirmed complete, so this '
                    'balance only reflects the invoices recorded.' if payments_to else
                    'Invoice records are confirmed complete to ' + display_date(invoices_to) + ', but payment records are not confirmed complete, so this '
                    'balance only reflects the payments recorded.' if invoices_to else
                    'Neither invoice nor payment records for this customer are confirmed complete, so this balance only reflects what is recorded.')
    ob = view['openingBalance']
    on, stated = display_date(view['asOf']), signed_money(ob['amount']).lstrip('− ')
    figure = (stated + ' held in credit' if int(ob['amount']['minorUnits']) < 0 else stated + ' owed') + ' as at ' + on + ' (' + ob['sourceLabel'] + \
        '; ' + entered_by(ob) + ')'
    up, down = view['unresolvedInvoices'], view['unresolvedPayments']
    balance = ('Customer balance (the whole account, not this invoice): ' + money_text(view['balance']) + ', from an opening balance of ' + figure +
               ' and the records after it.' if view['balance'] is not None else
               'Customer balance (the whole account, not this invoice): not calculated, because ' + ', '.join(view['withoutAmount']) + ' has no amount recorded.')
    pending = [part for part, show in (('up to ' + money_text(up['amount']) + ' in invoices', up['count'] > up['withoutAmount']),
                                       (str(up['withoutAmount']) + ' invoice(s) with no amount recorded', up['withoutAmount']),
                                       ('up to ' + money_text(down['amount']) + ' in payments', down['count'])) if show]
    if pending:
        balance += ' Not counted either way until their inclusion is answered: ' + '; '.join(pending) + '.'
    items = [{'kind': 'customer_balance', 'text': balance + ' ' + completeness}]
    if view['suggestion']:
        items.append({'kind': 'opening_reconciles', 'text': 'The amounts still owed on ' + ', '.join(view['suggestion']['references']) + ' at ' + on +
                      ' add up exactly to the opening balance. That suggests they make it up, but a missing invoice and a missing credit '
                      'would reconcile just as well, so it is not assumed until a person confirms it under Records.'})
    items.append({'kind': 'opening_credits', 'text': {
        'none': 'The opening balance is stated to include no credits or prepayments (' + entered_by(ob) + ').',
        'recorded': 'The opening balance is stated to have every credit in it recorded here (' + entered_by(ob) + '; ' + money_text(view['creditsRecorded']) + ' of payments and '
                    'credits included in it).'}.get(view['credits'], 'Whether the opening balance includes credits or prepayments is not stated. A credit '
                                                                  'could settle this invoice, so no amount for this customer is exact.')})
    if up['count'] or down['count']:
        items.append({'kind': 'opening_inclusion_unresolved', 'text': 'Not answered yet: whether ' + ', '.join(
            [r['reference'] for r in view['records'] if r['status'] == 'unresolved'][:6]) + ' is already part of the opening balance as at ' + on +
            '. Until then it is not counted either way. Answer this under Records.'})
    if view['impliedCredits']:
        items.append({'kind': 'opening_credits_implied', 'text': 'Invoices included in the opening balance add up to more than it, so credits or '
                      'prepayments of at least ' + money_text(view['impliedCredits']) + ' are implied. That alone is not an error.'})
    items += [{'kind': 'records_conflict', 'text': 'The records about this customer contradict each other: ' + c} for c in view['conflicts']]
    return items


LOCKED_FIELDS = ('This request was opened from a confirmed action, which fixed its customer, invoice and requested date: no answer changes them. '
                 'Withdraw the request and prepare a new action to change any of them.')
UNKNOWN_DUE_DATE = ('No due date is on record for this invoice (no payment terms recorded), so the extension length and '
                    'days overdue are not calculated.')
LEGACY_NOTICE = ('Legacy brief (format v1, stored before structured facts were introduced on 16 October 2026). Its sentences '
                 'were written by the model and were only checked for known values, not for meaning. Rely on the calculated '
                 'facts, or reanalyse to prepare a structured brief.')


def present(record):
    """Read-time labels for records stored in older formats. Stored data is never rewritten."""
    brief = (record.get('analysis') or {}).get('brief')
    if brief and 'format' not in brief:
        brief.update({'format': 'brief-v1-legacy', 'legacyNotice': LEGACY_NOTICE})
        if brief.get('suggestedOption'):
            # Historical, unvalidated model output: kept with provenance, not presented as a current suggestion.
            brief['historicalSuggestion'] = {**brief.pop('suggestedOption'), 'status': 'historical_unvalidated'}
        brief['suggestedOption'] = None
    decision = record.get('decision')
    if decision and decision.get('aiSuggestion'):
        decision['historicalAiSuggestion'] = {**decision.pop('aiSuggestion'), 'status': 'historical_unvalidated'}
    return record


class RunHooks:
    """Callbacks the runner uses outside the lock; each takes the lock only briefly."""

    def __init__(self, app, run_id, request_id, epoch):
        self.app, self.run_id, self.request_id, self.epoch = app, run_id, request_id, epoch

    def current(self):
        with self.app.lock:
            return self.app.epoch == self.epoch and self.app.run_is_current(self.run_id)

    def record(self, kind, data):
        with self.app.lock:
            if self.app.epoch != self.epoch:   # the data was reset or restored while the model was running
                return
            with self.app.db:
                self.app.db.execute('INSERT INTO events (request_id,kind,at,data) VALUES (?,?,?,?)',
                                    (self.request_id, kind, now(), json.dumps({**data, 'runId': self.run_id})))


class OpConnection(sqlite3.Connection):
    """The records' connection (a real Connection: restore uses its backup). A tool operation (App.tool_call) arms its record_ops key for
    the thread that runs the tool; the first commit that thread makes while armed also marks the key 'applied', in the same SQLite
    transaction as the business write. So after a crash, 'applied' means the change committed and a still 'pending' key means that
    nothing did. CPython's C __exit__ does not call commit, so both are overridden. Never armed while the claim and the finish commit."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.armed = {}   # thread ident -> the scoped record_ops key of the tool operation that thread is running

    def mark(self):
        key = self.armed.get(threading.get_ident())
        if key and self.in_transaction:   # in a transaction = a write waiting to commit
            self.execute("UPDATE record_ops SET state='applied' WHERE key=? AND state='pending'", (key,))

    def commit(self):
        self.mark()
        super().commit()

    def __exit__(self, kind, error, trace):
        if kind is None:
            self.mark()
        return super().__exit__(kind, error, trace)


def checked_assistant_url(value):
    """The assistant's address from the config (assistantUrl), or None when unset. It must be an http or https link without spaces, quotes or
    angle brackets, so the pages can use it as a link target as it stands; anything else is a configuration error."""
    if value is None or value == '':
        return None
    if not isinstance(value, str) or not re.fullmatch(r'https?://[^\s"\'<>`\\]+', value) or len(value) > 500:
        raise ValueError('assistantUrl must be an http or https link (at most 500 characters, no spaces or quotes).')
    return value


class App:
    def __init__(self, database, agent_mode='mock', model_adapter=None, inline_wait=None, deadline_seconds=300, verbose=False, demo=None,
                 sample_data=False, today=None, cookie_prefix='nucleon_', cookie_path='/', access_codes=None, service_codes=None, assistant_url=None, owner_assistant_url=None, shadow_model=None, research_provider=None, notifications=None):
        self.verbose = verbose
        self.notifier = notify.Notifier(notifications, log)   # notices to people outside the page (notify.py): a row on their Home page, and a webhook when configured
        # The research hook (research.py): a bootstrap model file (config shadowModel) used until the first version is saved in research_models, and the provider that fits
        # and scores (config researchProvider: builtin, or an http model service). The rules read a score only once the Owner has promoted the model (research settings).
        self.shadow = research.load_model(shadow_model)
        self.research_provider = research.provider_from(research_provider)
        self.assistant_url = checked_assistant_url(assistant_url)   # where the Records pages send people to the assistant (config assistantUrl); None: no link
        self.owner_assistant_url = checked_assistant_url(owner_assistant_url)   # the Owner's own assistant (config ownerAssistantUrl); None: the Owner gets assistantUrl
        self.recent_opens = {}   # service actor id -> the case the assistant opened last (one_at_a_time); in memory, this boot only
        # A second instance on the same host (e.g. under /preview/ behind a proxy) uses its own cookie names and path.
        self.cookie_prefix, self.cookie_path = cookie_prefix, cookie_path
        # Load the fictional sample only into a database that has no workspace yet. An explicit workspace always wins.
        self.sample_data = sample_data
        self.clock = today   # tests pass a fixed 'today'; otherwise today in the business's time zone
        self.lock = threading.RLock()
        self.settled = threading.Condition(self.lock)
        self.db_path = Path(database)
        self.running = set()   # the scoped keys of the tool operations this process is running now (claimed, not yet finished or abandoned)
        self.boot = uuid.uuid4().hex   # names this run of the process: a pending tool operation of another boot was abandoned by a stopped one
        self.db = sqlite3.connect(str(database), check_same_thread=False, factory=OpConnection)
        self.db.execute('PRAGMA foreign_keys = ON')
        self.db.execute('PRAGMA journal_mode = WAL')
        self.ensure_schema()
        self.agent_mode = agent_mode
        self.model_adapter = model_adapter
        self.inline_wait = inline_wait
        self.deadline_seconds = deadline_seconds
        self.status_lock, self.status_cache = threading.Lock(), None
        self.initial_fixture = json.loads((ROOT / 'fixtures.json').read_text())
        # The demo console exists only when configured, and only for fictional data.
        self.demo = demo if demo and demo.get('enabled') and self.initial_fixture.get('dataMode') == 'fictional' else None
        folder = Path(self.demo.get('backupDir') or 'backups').expanduser() if self.demo else None
        self.backup_dir = (folder if folder.is_absolute() else self.db_path.parent / folder) if folder else None
        self.epoch = 0   # bumped by reset/restore so runs that started earlier cannot write
        self.sessions = {}
        self.ui_seen = {}   # session csrf token -> monotonic times of the UI events it sent in the last minute (rate limit)
        self.agent_code = None
        self.demo_codes = {role: secrets.token_urlsafe(18) for role in ROLES if role in CASE_ROLES or self.demo}
        # Fixed codes from the config ("accessCodes": {role: code}) for a demo instance: they survive restarts, so they are
        # only for fictional data behind a URL the team shares; each must be at least 6 characters and they must differ.
        # "agent" is the AI Agent testing account's code: one login holds a session for every role (staff, owner, and the console
        # where it exists), each acting as the actor ai_agent, so the audit trail names it and the role it acted as.
        fixed = {r: c for r, c in (access_codes or {}).items() if r in self.demo_codes or r == 'agent'}
        if fixed:
            require(all(isinstance(c, str) and len(c) >= 6 for c in fixed.values()) and len(set(fixed.values())) == len(fixed),
                    400, 'INVALID_INPUT', 'accessCodes need at least 6 characters each and must differ.', 'accessCodes')
            self.agent_code = fixed.pop('agent', None)
            self.demo_codes.update(fixed)
        # SERVICE codes, one per case role and never the same as a person's code: a session made with one is a service's (the Lab), set by THIS
        # code from the code used, never from anything the client says (channel 'service'); a session made with an access code is always a
        # person's. Confirming or cancelling an action needs a person's session, so what a service holds cannot do either. Fixed ones
        # ("serviceCodes": {role: code}) survive restarts for a test instance; each needs 6 characters and must differ from every access code,
        # the agent code and each other; otherwise random per start. Printed on their own lines, apart from the access codes people are given.
        self.service_codes = {role: secrets.token_urlsafe(18) for role in CASE_ROLES}
        given = {r: c for r, c in (service_codes or {}).items() if r in CASE_ROLES}
        require(set(service_codes or {}) <= set(CASE_ROLES), 400, 'INVALID_INPUT', 'serviceCodes: only staff and owner have a service code.', 'serviceCodes')
        require(all(isinstance(c, str) and len(c) >= 6 for c in given.values()), 400, 'INVALID_INPUT', 'serviceCodes need at least 6 characters each.', 'serviceCodes')
        self.service_codes.update(given)
        every = [*self.demo_codes.values(), *self.service_codes.values(), *([self.agent_code] if self.agent_code else [])]
        require(len(set(every)) == len(every), 400, 'INVALID_INPUT', 'serviceCodes must differ from every access code, the agent code and each other.', 'serviceCodes')
        self.queue = queue.Queue()
        self.worker = threading.Thread(target=self.work, name='nucleon-agent-worker', daemon=True)
        self.worker.start()
        with self.lock:
            self.recover()

    def ensure_schema(self):
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS fixtures (id INTEGER PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events (
              seq INTEGER PRIMARY KEY AUTOINCREMENT, request_id TEXT NOT NULL,
              kind TEXT NOT NULL, at TEXT NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS idempotency (
              key TEXT PRIMARY KEY, payload_hash TEXT NOT NULL, request_id TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS runs (
              id TEXT PRIMARY KEY, request_id TEXT NOT NULL, request_version INTEGER NOT NULL,
              status TEXT NOT NULL, data TEXT NOT NULL);
            CREATE UNIQUE INDEX IF NOT EXISTS one_running_run ON runs(request_id) WHERE status = 'running';
            CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS batches (id TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS profiles (signature TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS record_ops (key TEXT PRIMARY KEY, payload_hash TEXT NOT NULL, result TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS customers (id TEXT PRIMARY KEY, seq INTEGER NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS invoices (id TEXT PRIMARY KEY, seq INTEGER NOT NULL, customer_id TEXT NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS notes (id TEXT PRIMARY KEY, seq INTEGER NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS payments (id TEXT PRIMARY KEY, seq INTEGER NOT NULL, customer_id TEXT NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS allocations (id TEXT PRIMARY KEY, seq INTEGER NOT NULL, payment_id TEXT NOT NULL,
              invoice_id TEXT NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS opening_balances (id TEXT PRIMARY KEY, seq INTEGER NOT NULL, customer_id TEXT NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS coverage (id TEXT PRIMARY KEY, seq INTEGER NOT NULL, data TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS invoices_by_customer ON invoices(customer_id);
            CREATE INDEX IF NOT EXISTS payments_by_customer ON payments(customer_id);
            CREATE INDEX IF NOT EXISTS allocations_by_payment ON allocations(payment_id);
            CREATE INDEX IF NOT EXISTS allocations_by_invoice ON allocations(invoice_id);
            CREATE TABLE IF NOT EXISTS statements (id TEXT PRIMARY KEY, seq INTEGER NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS threads (id TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS turns (seq INTEGER PRIMARY KEY AUTOINCREMENT, thread_id TEXT NOT NULL, data TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS turns_by_thread ON turns(thread_id);
            CREATE TABLE IF NOT EXISTS actions (id TEXT PRIMARY KEY, kind TEXT NOT NULL, status TEXT NOT NULL, invoice_id TEXT,
                                                created_at TEXT NOT NULL, data TEXT NOT NULL);
            CREATE UNIQUE INDEX IF NOT EXISTS one_live_action ON actions(kind, invoice_id) WHERE status = 'proposed';
            CREATE TABLE IF NOT EXISTS delegation_policies (version INTEGER PRIMARY KEY, created_at TEXT NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS research_models (version INTEGER PRIMARY KEY, created_at TEXT NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS notices (id TEXT PRIMARY KEY, role TEXT NOT NULL, kind TEXT NOT NULL, case_id TEXT, created_at TEXT NOT NULL, read_at TEXT, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS decision_cases (id TEXT PRIMARY KEY, kind TEXT NOT NULL, subject TEXT NOT NULL, status TEXT NOT NULL, dataset TEXT NOT NULL,
                                                       created_at TEXT NOT NULL, updated_at TEXT NOT NULL, data TEXT NOT NULL);
            CREATE UNIQUE INDEX IF NOT EXISTS one_live_case ON decision_cases(kind, subject)
              WHERE status IN ('gathering_evidence', 'awaiting_owner', 'on_hold');
            CREATE TABLE IF NOT EXISTS confirmed_facts (id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, kind TEXT NOT NULL, created_at TEXT NOT NULL, data TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS confirmed_facts_by_customer ON confirmed_facts(customer_id);
            CREATE TABLE IF NOT EXISTS case_events (seq INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, kind TEXT NOT NULL, at TEXT NOT NULL, actor TEXT,
                                                    policy_version INTEGER, data TEXT);
            CREATE INDEX IF NOT EXISTS case_events_by_case ON case_events(case_id);
            CREATE TABLE IF NOT EXISTS ui_events (seq INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, role TEXT, channel TEXT, page TEXT NOT NULL, kind TEXT NOT NULL, data TEXT);
        ''')
        # record_ops grew columns for tool operations (App.tool_call): state pending|applied|done, when it was made, in which boot. Additive:
        # a row from before has state 'done' (it holds its answer), and at/boot NULL (never pruned, never pending).
        have = {row[1] for row in self.db.execute('PRAGMA table_info(record_ops)')}
        for column, kind in (('state', "TEXT NOT NULL DEFAULT 'done'"), ('at', 'TEXT'), ('boot', 'TEXT')):
            if column not in have:
                self.db.execute('ALTER TABLE record_ops ADD COLUMN ' + column + ' ' + kind)
        self.db.commit()

    def recover(self):
        """Bring stored data up to date and resume pending work: at startup and after a restore. Lock held."""
        self.migrate_document()
        sample, stored, ws = self.initial_fixture, self.fixture(), self.meta('workspace')
        with self.db:
            if ws is None and stored is not None:
                # A database from before workspaces. Nothing could edit records then, so an older fictional copy is the sample.
                if stored.get('dataMode') == 'fictional' and stored.get('version', 0) < sample['version']:
                    self.replace_doc(sample)
                    stored = sample
                    log('fictional sample upgraded to version', sample['version'], '(pending owner tasks need reanalysis)')
                practice = stored.get('dataMode') == 'fictional'
                self.set_meta('workspace', {'mode': 'practice' if practice else 'real', 'origin': 'migration', 'createdAt': now(),
                                            'sampleFingerprint': fingerprint(stored) if practice else None, 'skips': {}})
                log('workspace recorded for existing records:', 'practice' if practice else 'real')
            elif ws is None and self.sample_data:
                self.set_meta('workspace', {'mode': 'practice', 'origin': 'config', 'createdAt': now(), 'sampleFingerprint': None, 'skips': {}})
                self.load_sample()
                log('practice workspace with the fictional sample (sampleData is set)')
            elif ws is None:
                log('no workspace yet: the owner sets it up on first sign-in')
            else:
                if self.sample_data and stored is None:
                    log('sampleData is set but ignored: this workspace was set up explicitly as', ws['mode'])
                if ws['mode'] == 'practice' and stored and ws.get('sampleFingerprint') and stored.get('version', 0) < sample['version']:
                    if fingerprint(stored) == ws['sampleFingerprint']:   # the sample exactly as it was loaded: safe to replace
                        self.load_sample()
                        log('fictional sample upgraded to version', sample['version'], '(pending owner tasks need reanalysis)')
                    else:
                        log('practice records changed after the sample was loaded; sample version', sample['version'], 'was not applied')
            for run_id, data in self.db.execute("SELECT id, data FROM runs WHERE status='running'").fetchall():
                run = {**json.loads(data), 'id': run_id}
                self.close_run(run, 'interrupted', {'reason': 'process restarted during the run'})
                if run.get('kind') == 'suggest' and self.meta('showSuggestions') and self.suggestable(self.get(run['requestId'])):
                    self.schedule_suggest(self.get(run['requestId']), 'recovered after restart')
            for record in self.records():
                if record['status'] in ACTIVE_STATES:
                    self.schedule(record, 'recovered after restart')
            self.migrate_evidence_keys()
            # e.g. evidence written by an earlier release, or a restore: prepare those owner cases again, once
            self.prepare_stale_cases('evidence no longer matches the records')
            self.record_decided_baselines()
            # Finished tool operations keep their answer for TOOL_OPS_KEEP_DAYS; only those (never pending/applied, never legacy rows with no
            # time). The scope is matched in code: a client's key text must not make another kind of row look like one.
            cutoff = (datetime.now(timezone.utc) - timedelta(days=TOOL_OPS_KEEP_DAYS)).isoformat()
            old = [k for (k,) in self.db.execute("SELECT key FROM record_ops WHERE state='done' AND at < ? AND key LIKE '%:tool:%'", (cutoff,))
                   if re.match(r'[^:]+:[a-z]+:tool:\w+:', k)]
            self.db.executemany('DELETE FROM record_ops WHERE key=?', [(k,) for k in old])
        for record in self.records():
            if record['status'] == 'decided':
                self.finish(record)

    def close(self):
        self.queue.put(None)
        self.worker.join(timeout=5)
        self.db.close()

    # ------------------------------------------------------------ records

    def fixture(self):
        """The records as one document-shaped projection of the record tables (settings plus records), or None before
        settings exist. Read-only: changes go through save_doc or replace_doc."""
        meta = self.meta('records')
        if meta is None:
            return None
        doc = dict(meta['header'])
        for kind in RECORD_TABLES:
            rows = [json.loads(d) for (d,) in self.db.execute('SELECT data FROM ' + TABLE.get(kind, kind) + ' ORDER BY seq')]
            if rows or kind not in OPTIONAL_LISTS:
                doc[kind] = rows
        return doc

    def allocation_lines(self, invoice_id):
        """[(allocation, payment)] for the active allocations to one invoice, oldest payment first: the payments that cover it, by their
        own reference, date and allocated amount. Read-only."""
        out = []
        for (d,) in self.db.execute('SELECT data FROM allocations WHERE invoice_id = ? ORDER BY seq', (invoice_id,)):
            a = json.loads(d)
            row = a.get('status', 'active') == 'active' and self.db.execute('SELECT data FROM payments WHERE id = ?', (a['paymentId'],)).fetchone()
            if row and json.loads(row[0]).get('status', 'active') == 'active':
                out.append((a, json.loads(row[0])))
        return sorted(out, key=lambda x: (x[1].get('receivedDate') is None, x[1].get('receivedDate') or '', x[0]['id']))

    def save_doc(self, doc):
        """Write a changed projection back: new and changed records are written, unchanged ones are left alone, and a record
        missing from the projection is an error, because records are never deleted (they are removed or reverted by status).
        Lock and transaction held. shortcut: compares every row in Python; fine for small-business volumes, index later."""
        meta = self.meta('records') or {'store': 'tables', 'createdAt': now()}
        self.set_meta('records', {**meta, 'header': {k: v for k, v in doc.items() if k not in RECORD_TABLES}})
        for kind, keys in RECORD_TABLES.items():
            table = TABLE.get(kind, kind)
            stored = dict(self.db.execute('SELECT id, data FROM ' + table).fetchall())
            records = doc.get(kind, [])
            gone = set(stored) - {r['id'] for r in records}
            if gone:
                raise ValueError('records cannot be deleted (' + kind + ': ' + ', '.join(sorted(gone)[:3]) + ')')
            seq = self.db.execute('SELECT COALESCE(MAX(seq), 0) FROM ' + table).fetchone()[0]
            for record in records:
                data = json.dumps(record)
                if stored.get(record['id']) == data:
                    continue
                columns = [column for column, _ in keys]
                values = [record[field] for _, field in keys]
                if record['id'] in stored:
                    self.db.execute('UPDATE ' + table + ' SET data=?' + ''.join(', ' + c + '=?' for c in columns) + ' WHERE id=?',
                                    [data, *values, record['id']])
                else:
                    seq += 1
                    self.db.execute('INSERT INTO ' + table + ' (id, seq, data' + ''.join(', ' + c for c in columns) + ') VALUES (?, ?, ?' +
                                    ', ?' * len(columns) + ')', [record['id'], seq, data, *values])

    def replace_doc(self, doc):
        """Replace every record (loading the sample, starting empty, a sample upgrade). Lock and transaction held."""
        for kind in RECORD_TABLES:
            self.db.execute('DELETE FROM ' + TABLE.get(kind, kind))
        if doc is None:
            self.db.execute("DELETE FROM meta WHERE key='records'")
        else:
            self.save_doc(doc)

    def migrate_document(self):
        """Move a records document (Slice 2 and earlier) into the record tables, once. The document row is kept unchanged as a
        frozen snapshot and is never written again. If the tables would not reproduce the document exactly, nothing changes."""
        row = self.db.execute('SELECT data FROM fixtures WHERE id=1').fetchone()
        moved = self.meta('records')
        if moved is not None:
            # An earlier release reads and writes only the document; its changes would otherwise be silently ignored here.
            if row and moved.get('documentFingerprint') and fingerprint(json.loads(row[0])) != moved['documentFingerprint']:
                raise RuntimeError('the records document changed after the records moved into tables (did an earlier release run on this '
                                   'database?). Those changes are not in the tables. Restore the backup taken before that release ran.')
            return
        if not row:
            return
        doc = json.loads(row[0])
        with self.db:
            self.save_doc(doc)
            if self.fixture() != doc:
                raise RuntimeError('records migration would not be lossless; nothing was changed')
            self.set_meta('records', {**self.meta('records'), 'migratedFrom': 'document', 'migratedAt': now(),
                                      'documentFingerprint': fingerprint(doc)})
        log('records moved into tables:', ', '.join(k + ' ' + str(len(doc.get(k, []))) for k in RECORD_TABLES), '(the document row stays as a frozen snapshot)')

    def load_sample(self):
        """The fictional sample, recorded exactly as loaded so a later sample version only replaces an unchanged copy.
        Lock and transaction held; the workspace must be practice."""
        self.replace_doc(self.initial_fixture)
        ws = self.meta('workspace')
        self.set_meta('workspace', {**ws, 'mode': 'practice', 'sampleFingerprint': fingerprint(self.initial_fixture)})

    def today(self, doc):
        # The demo console can move a practice workspace's business date forward (advance_business_date); never a real one.
        practice = (self.meta('workspace') or {}).get('mode') == 'practice'
        return today_for(doc, self.clock) + timedelta(days=practice and self.meta('businessDateOffset') or 0)

    def records(self):
        return [json.loads(row[0]) for row in self.db.execute('SELECT data FROM requests ORDER BY rowid DESC')]

    def get(self, request_id):
        row = self.db.execute('SELECT data FROM requests WHERE id=?', (request_id,)).fetchone()
        require(row is not None, 404, 'NOT_FOUND', 'Request not found.')
        return json.loads(row[0])

    def save(self, record):
        self.db.execute('INSERT OR REPLACE INTO requests VALUES (?, ?)', (record['id'], json.dumps(record)))

    def event(self, record, kind, value):
        self.db.execute('INSERT INTO events (request_id,kind,at,data) VALUES (?,?,?,?)',
                        (record['id'], kind, now(), json.dumps(value)))

    def trace(self, record, tool, arguments, result, caller, run_id=None):
        self.event(record, 'tool.executed', {'tool': tool, 'arguments': arguments, 'result': result, 'caller': caller,
                                             'ok': True, 'requestVersion': record['version'], 'runId': run_id})

    def history(self, request_id):
        return [dict(seq=r[0], kind=r[1], at=r[2], data=json.loads(r[3])) for r in
                self.db.execute('SELECT seq,kind,at,data FROM events WHERE request_id=? ORDER BY seq', (request_id,))]

    def runs_for(self, request_id):
        return [json.loads(row[0]) for row in self.db.execute('SELECT data FROM runs WHERE request_id=? ORDER BY rowid', (request_id,))]

    def view(self, record, role):
        """A case as this role may see it, with what has been said about its customer (live, from the case's own customer).
        The coordinator's questions are written from the owner's words, which may be owner-only, so staff see only those asked
        of staff (from 'staff', which commit_outcome keeps only when they repeat no owner-only quote), as STAFF_QUESTION, here and
        in the activity; never contextShown nor the needs step's checks. The suggestion is the owner's alone: staff see no trace of it, nor
        of the one a decision saw (suggestionSeen). Staff see only the event kinds in STAFF_EVENTS."""
        shown = present({**copy.deepcopy(record), 'history': self.history(record['id']), 'runs': self.runs_for(record['id'])})
        if record.get('customerId'):
            shown['context'] = self.context_for(record['customerId'], role, record['id'])
            brief = (shown.get('analysis') or {}).get('brief') or {}
            if shown['context']['lines'] and 'openItems' in brief:   # what this role can see was said; owner-only words leave staff's item as it was
                brief['openItems'] = [x for x in brief['openItems'] if x['kind'] != 'no_owner_notes']
        shown.pop('earlierBases', None)   # read one by its version: GET api/requests/<id>/basis
        if record.get('decision'):   # why a decision has no calculation details, when it has none (null when it has them)
            shown['decisionBasisGap'] = basis_gap(record)
        if role != 'owner':
            if shown.get('assessment'):
                shown['assessment'] = staff_plain(shown['assessment'])
            if (shown.get('decision') or {}).get('basis'):
                shown['decision']['basis'] = staff_plain(shown['decision']['basis'])
            shown['history'] = [e for e in shown['history'] if e['kind'] in STAFF_EVENTS or
                                e['kind'] in ('question.answered', 'question.skipped') and e['data'].get('from') == 'staff']
            shown['runs'] = [x for x in shown['runs'] if x.get('kind') != 'suggest']
            for key in ('suggestionVersion', 'suggestionSeen', 'preparedDecision', 'preparedVersion', 'preparations'):
                shown.pop(key, None)
            analyses = [shown['analysis']] + [e['data'] if e['kind'] == 'analysis.finished' else e['data'].get('analysis')
                                              for e in shown['history'] if e['kind'] in ('analysis.finished', 'analysis.superseded')]
            for a in filter(None, analyses):
                if a.get('brief') and 'questions' in a['brief']:
                    a['brief'].update({'questions': [{k: q[k] for k in STAFF_QUESTION} for q in a['brief']['questions'] if q['from'] == 'staff'],
                                       'contextShown': [], 'suggestion': None, 'suggestionStatus': 'off', 'withheldBecause': [],
                                       'openItems': [x for x in a['brief']['openItems'] if 'step' not in x]})   # needs and suggest
                for key in ('suggestModelCalls', 'suggestLatencyMs', 'suggestReason'):
                    (a.get('stats') or {}).pop(key, None)
        return shown

    def basis_view(self, r, role, version=None):
        """GET api/requests/<id>/basis[?version=N]: the calculation details of a case as this role may see them (the case's own reader:
        both roles, staff's words for staff; the numbers are the same). assessment: the latest assessment's {version, at (the day),
        basis}, or with version the one of that version while it is kept (the latest, the last KEEP_BASES before it, and the one the
        decision was made on); decision: the decision with its frozen basis (decision_view 'full'), or None. Lock held."""
        a, d = r.get('assessment'), r.get('decision')
        kept = {x['version']: x for x in r.get('earlierBases') or []}
        frozen = (d or {}).get('basis')
        if frozen and frozen.get('basis'):
            kept[frozen['assessmentVersion']] = {'version': frozen['assessmentVersion'], 'at': frozen['assessedAt'], 'basis': frozen['basis']}
        if a and a.get('basis'):
            kept[a['version']] = {'version': a['version'], 'at': a['at'], 'basis': a['basis']}
        if version is None:
            got = kept.get(a['version']) if a else None
        else:
            require(re.fullmatch(r'[1-9]\d{0,6}', version or ''), 400, 'INVALID_INPUT', 'version is an assessment version, a whole number.', 'version')
            got = kept.get(int(version))
            require(got is not None, 404, 'NOT_FOUND', 'The calculation details of assessment version ' + version + ' are no longer kept: the case was assessed '
                    'again since. Ask for the numbers again to see the latest.')
        plain = (lambda b: b) if role == 'owner' else staff_basis
        return {'requestId': r['id'], 'assessment': got and {'version': got['version'], 'at': got['at'][:10], 'basis': plain(got['basis'])},
                'decision': decision_view(d, role, 'full'), 'decisionBasisGap': basis_gap(r)}

    def evidence(self):
        doc = self.fixture()
        f = {**active_view(doc), 'asOfDate': self.today(doc).isoformat()}   # active records only, with 'today' for this workspace
        original = {i['id']: i['originalDueDate'] for i in f['invoices']}
        due, sources = {}, {}
        for r in self.records():
            decision = r.get('decision')
            if decision and decision['outcome'] == 'approve' and r.get('invoiceId') in original:
                invoice_id = r['invoiceId']
                base = due.get(invoice_id, original[invoice_id])   # None when no due date is on record
                due[invoice_id] = decision['approvedDueDate'] if base is None else max(base, decision['approvedDueDate'])
                if due[invoice_id] == decision['approvedDueDate']:
                    sources[invoice_id] = {'decisionId': decision['id'], 'requestId': r['id'],
                                           'approvedDueDate': decision['approvedDueDate'], 'decidedAt': decision['decidedAt'],
                                           **{k: decision[k] for k in ('decisionSource', 'decidedBy', 'actorName', 'actorRole') if decision.get(k)}}
        return Evidence(f, due, sources)

    # ------------------------------------------------------------ statements, threads and turns (the coordinator's stores)

    def new_statement(self, actor, text, **fields):
        """Store what someone said (build_statement). Commits immediately, like decide."""
        s = self.build_statement(actor, text, **fields)
        with self.db:
            self.save_statement(s)
        return s

    def build_statement(self, actor, text, *, thread_id, scope, visibility, status, lines, source, checks=()):
        """What someone said, with the lines read from it, dated by the business date, not yet saved (save_statement). Only the
        owner makes a confirmed statement, as with notes."""
        require(visibility in ('owner', 'staff') and status in ('proposed', 'confirmed', 'retired'), 400, 'INVALID_INPUT',
                'Unknown visibility or status.')
        require(scope.get('kind') in SCOPE_KINDS and all(line.get('kind') in LINE_KINDS for line in lines), 400, 'INVALID_INPUT',
                'Unknown scope or line kind.')
        if status == 'confirmed' and actor['role'] != 'owner':
            raise RecordsError(403, 'FORBIDDEN', 'Only the owner can confirm what was said.')
        s = {'id': uid('stmt'), 'text': text, 'saidBy': actor['id'], 'role': actor['role'], **trail(actor), 'saidOn': self.today(self.fixture()).isoformat(),
             'recordedAt': now(), 'threadId': thread_id, 'scope': scope, 'visibility': visibility, 'status': status,
             'lines': [{'id': uid('line'), 'kind': line['kind'], 'quote': line['quote'], 'until': None if line.get('until') is None else parse_day(line['until'], 'until'),
                        'certainty': line.get('certainty'), 'status': 'active', 'supersededBy': None} for line in lines],
             'checks': list(checks), 'source': source, 'version': 1, 'history': []}
        return s

    def statement(self, statement_id):
        row = self.db.execute('SELECT data FROM statements WHERE id=?', (statement_id,)).fetchone()
        require(row is not None, 404, 'NOT_FOUND', 'Statement not found.')
        return json.loads(row[0])

    def save_statement(self, s):
        self.db.execute('INSERT INTO statements (id, seq, data) VALUES (?, (SELECT COALESCE(MAX(seq), 0) + 1 FROM statements), ?) '
                        'ON CONFLICT(id) DO UPDATE SET data=excluded.data', (s['id'], json.dumps(s)))

    def statements(self):
        return [json.loads(d) for (d,) in self.db.execute('SELECT data FROM statements ORDER BY seq')]

    def update_statement(self, actor, s, *, lines=None, scope=None, visibility=None, status=None, reason=None):
        """Confirm, retire, rescope, share or edit the lines of a statement; the earlier version is kept in its history. Staff may
        only adjust a proposed statement shared with staff: confirming, retiring, sharing and changing a confirmed one are the
        owner's, as with notes. Line edits are [{id, kind?, until?, remove?: True}]; `reason` is kept with the change. Commits
        immediately, like decide."""
        require(visibility in (None, 'owner', 'staff') and status in (None, 'proposed', 'confirmed', 'retired'), 400, 'INVALID_INPUT',
                'Unknown visibility or status.')
        require((scope is None or scope.get('kind') in SCOPE_KINDS) and all('kind' not in edit or edit['kind'] in LINE_KINDS for edit in lines or ()),
                400, 'INVALID_INPUT', 'Unknown scope or line kind.')
        if actor['role'] != 'owner' and (status in ('confirmed', 'retired') or visibility is not None or s['status'] != 'proposed' or
                                         s['visibility'] != 'staff'):
            raise RecordsError(403, 'FORBIDDEN', 'Only the owner can confirm, retire or share a statement, or change a confirmed one.')
        s = copy.deepcopy(s)
        s['history'] = s['history'] + [{**copy.deepcopy({k: s[k] for k in ('version', 'scope', 'visibility', 'status', 'lines')}),
                                        'changedBy': actor['id'], 'changedAt': now(), 'reason': reason}]
        by_id = {line['id']: line for line in s['lines']}
        for edit in lines or ():
            line = by_id.get(edit.get('id'))
            require(line is not None, 404, 'NOT_FOUND', 'That line is not part of this statement.', 'lines')
            if edit.get('remove') is True:
                line['status'] = 'removed'
            if 'kind' in edit:
                line['kind'] = edit['kind']
            if 'until' in edit:
                line['until'] = None if edit['until'] is None else parse_day(edit['until'], 'until')
        s.update({k: v for k, v in (('scope', scope), ('visibility', visibility), ('status', status)) if v is not None})
        s['version'] += 1
        with self.db:
            self.save_statement(s)
        return s

    def thread(self, thread_id):
        row = self.db.execute('SELECT data FROM threads WHERE id=?', (thread_id,)).fetchone()
        require(row is not None, 404, 'NOT_FOUND', 'Thread not found.')
        return json.loads(row[0])

    def threads(self):
        return [json.loads(d) for (d,) in self.db.execute('SELECT data FROM threads ORDER BY rowid')]

    def open_thread(self, thread_id, kind, request_id=None):
        """A thread, created on first use. Commits immediately, like decide."""
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO threads VALUES (?, ?)',
                            (thread_id, json.dumps({'id': thread_id, 'kind': kind, 'requestId': request_id, 'createdAt': now()})))
        return self.thread(thread_id)

    def general_thread(self):
        return self.open_thread('thread_general', 'general')

    def case_thread(self, request_id):
        self.get(request_id)   # 404 for an unknown case
        return self.open_thread('thread_' + request_id, 'case', request_id)

    def add_turn(self, thread_id, *, by, role, kind, text=None, card=None, visibility='all', meta=None):
        """Append a turn to a thread. `meta` is the agent's {promptVersion, modelCalls, latencyMs}. Commits immediately, like decide."""
        self.thread(thread_id)
        turn = {'id': uid('turn'), 'threadId': thread_id, 'at': now(), 'by': by, 'role': role, 'kind': kind, 'text': text, 'card': card,
                'visibility': visibility, 'meta': meta}
        with self.db:
            self.db.execute('INSERT INTO turns (thread_id, data) VALUES (?, ?)', (thread_id, json.dumps(turn)))
        return turn

    def turns(self, thread_id, viewer_role):
        """A thread's turns that this role may see: those for everyone, and those for this role only."""
        rows = self.db.execute('SELECT data FROM turns WHERE thread_id=? ORDER BY seq', (thread_id,))
        return [t for t in (json.loads(d) for (d,) in rows) if t['visibility'] in ('all', viewer_role)]

    def context_for(self, customer_id, viewer_role, request_id=None):
        """What has been said that bears on this customer, and on this case: active lines of confirmed statements and confirmed
        notes, each with its provenance; expired lines are kept and marked. Staff see only what is shared with staff. Also the
        customer's decided cases, which are history, not guidance."""
        doc = self.fixture()
        today = self.today(doc).isoformat()

        def applies(scope):
            return (scope['kind'] == 'business' or scope['kind'] == 'customer' and scope.get('customerId') == customer_id or
                    scope['kind'] == 'case' and request_id is not None and scope.get('requestId') == request_id)

        lines = [{**line, 'statementId': s['id'], 'scope': s['scope'], 'saidOn': s['saidOn'], 'saidBy': s['saidBy'], 'role': s['role'],
                  'visibility': s['visibility'], 'expired': bool(line['until'] and line['until'] < today),
                  'source': (s['source'] or {}).get('kind'),   # turn, answer or decision; notes below say 'note'
                  **({'checkedLineId': s['source']['lineId']} if (s['source'] or {}).get('lineId') else {})}   # an answer to still_holds
                 for s in self.statements() if s['status'] == 'confirmed' and applies(s['scope']) and
                 (viewer_role == 'owner' or s['visibility'] == 'staff')   # anything not explicitly shared stays with the owner
                 for line in s['lines'] if line['status'] == 'active']
        for n in doc['notes']:
            scope = {'kind': 'business'} if n['scope'] == 'business' else {'kind': 'customer', 'customerId': n['scope']}
            if n.get('status') == 'confirmed' and applies(scope):   # notes predate statements and were always shown to staff
                lines.append({'id': 'note:' + n['id'], 'kind': 'observation' if n.get('kind', 'context') == 'context' else 'guidance',
                              'quote': n['text'], 'until': None, 'certainty': None, 'statementId': None, 'scope': scope,
                              'saidOn': (n.get('createdAt') or '')[:10] or None, 'saidBy': n.get('createdBy'), 'role': n['origin'],
                              'visibility': 'staff', 'expired': False, 'source': 'note'})
        invoices = {i['id']: i for i in doc['invoices']}
        decisions = [{**{k: r['decision'][k] for k in ('decidedAt', 'outcome', 'approvedDueDate', 'approvedExtensionDays', 'reason')},
                      'requestId': r['id'], 'invoiceReference': invoices[r['invoiceId']]['reference']}
                     for r in self.records() if r['status'] in ('decided', 'completed') and r.get('invoiceId') in invoices and
                     invoices[r['invoiceId']]['customerId'] == customer_id]
        return {'lines': lines, 'decisions': decisions}

    # ------------------------------------------------------------ the situation: one role-filtered picture of a case and its customer

    def situation(self, role, *, request_id=None, customer_id=None):
        """What this role sees of a case and its customer: caseDetails returns it (and the case's customer, whose overview the
        customerOverview tool returns). It is built from the views the case page used (view, context_for with the case id, the
        customerOverview tool's overview on records_view positions, summary and case_label), so nothing this role may not see is
        ever in it. The case is request_id's; the customer customer_id's, else the case's. {case | None, customer | None, actions}.
        Lock held."""
        r = request_id and self.get(request_id)
        cid = customer_id or r and r['customerId']
        customer = None
        if cid:   # with no customer there is nothing to read, and before the settings exist no records to read it from
            tools = DeskTools(self, {'role': role}, '', None, None, None, focus_id=cid)
            try:   # the overview the customerOverview tool returns to this role ("current" is cid here)
                customer = tools._customerOverview({'customerId': 'current'})
            except ToolError:   # no currency set yet, or no such customer now
                pass
        out = {'case': r and self.case_situation(r, role), 'customer': customer}
        return {**out, 'actions': actions_for(role, out, {t['function']['name'] for t in tools_for(role, self.meta('agentTools'))})}

    def case_invoice(self, r, invoice, f):
        """The case's invoice for the situation: its reference, the amount still owed as the case shows it (case_amount) and the
        separate labelled figures (invoice_figures): the original amount, the amount still owed with its basis, the payments allocated."""
        said = case_amount(f)
        if said['mark'] == 'none' and r.get('invoiceId'):   # none recorded: what the replay leaves on it today (the stored snapshot is untouched)
            doc = self.fixture()
            left = owed_position(doc, invoice['customerId'], self.today(doc), settings_of(doc))['left'].get(r['invoiceId'])
            if left:
                said = {'amount': left, 'mark': 'workedOut', 'markDetail': 'not recorded; the invoice amount less the payments applied to it, recorded allocations first, then oldest first',
                        'amountText': amount_text(left, 'worked out')}
        return {'reference': invoice.get('reference'), **said, **invoice_figures(
            invoice, said['amount'], said['mark'], f.get('outstandingExactAsOf') if said['mark'] == 'exact' else f.get('outstandingAsOf'),
            invoice.get('position'), self.allocation_lines(r['invoiceId']) if r.get('invoiceId') else [])}

    def assessment_stale(self, r):
        """{reason, text} when a case not yet decided has an assessment that no longer holds: the customer's records (its evidence version)
        or the owner's limits changed after it; else None. An assessment stored before it kept what it read is never called stale (Act
        re-checks everything when pressed)."""
        a = r.get('assessment') or {}
        if r['status'] not in STATES_BEFORE_DECISION or not a.get('evidenceVersion') or not r.get('invoiceId'):
            return None
        try:
            changed = 'records' if self.evidence().version_for(r['invoiceId']) != a['evidenceVersion'] else 'limits' if a.get('authority') != authority_of(self.fixture()) else None
        except StopIteration:   # the invoice is no longer among the active records
            changed = 'records'
        return changed and {'reason': changed, 'text': {'records': "The customer's records changed after this assessment (an invoice, a payment or an allocation), so it no longer holds; assess the case again before acting.",
                                                        'limits': "The owner's limits changed after this assessment, so it no longer holds; assess the case again before acting."}[changed]}

    def case_situation(self, r, role):
        """situation()'s case: the request as this role's case view (view) has it, with the day limit said in its context lines,
        the latest date within it and the days asked against it worked out by code, and the suggestion (the owner's, while the case
        waits for the owner) with what it cites in words, as the page's Sources lists them. Also every decision prepared with its
        status and the current version (the owner's), the due dates, ordinal and flags (summary), and the concerns staff raised."""
        v = self.view(r, role)
        a = v.get('analysis') or {}
        brief, snap, ctx = a.get('brief') or {}, a.get('snapshot') or {}, v.get('context') or {'lines': [], 'decisions': []}
        f = snap.get('facts')
        due, asked, ext = (f or {}).get('currentEffectiveDueDate'), (f or {}).get('requestedDueDate'), (f or {}).get('extensionDays')
        lines = [{'id': x['id'], 'kind': x['kind'], 'quote': x['quote'], 'scope': x['scope']['kind'], 'by': x['role'], 'saidOn': x['saidOn'],
                  'until': x['until'], 'expired': x['expired'], 'source': x['source'], 'visibility': x['visibility']} for x in ctx['lines']]
        quotes, facts = {x['id']: x['quote'] for x in lines}, {x['key']: x for x in brief.get('facts') or []}
        decided = {d['requestId']: d for d in ctx['decisions']}
        answered = {e['data'].get('questionId') for e in v['history'] if e['kind'] == 'question.answered'}
        questions = [{'id': q['id'], 'question': q['question'], 'why': q['why'], 'need': q.get('need'), 'from': q['from'], 'createdBy': q.get('createdBy'), 'lineId': q.get('lineId'),
                      'status': 'known' if q['status'] == 'answered' and q['id'] not in answered else q['status'], 'answer': quotes.get(q.get('answeredBy'))}
                     for q in brief.get('questions') or []]
        limit = min(day_limits(ctx['lines']), key=lambda x: x[1], default=None)   # the smallest, as validate_suggestion applies it
        concerns = [{**{k: x[k] for k in ('id', 'quote', 'kind', 'by', 'saidOn')}, **{k: x[k] for k in ('disagreesWith', 'answeredBy') if x.get(k)}, **({k: x[k] for k in ('actorName', 'actorRole')} if x.get('actorName') else {})}
                    for x in v.get('concerns', [])]   # the day only: a time's digits are no figure
        lines += [{**x, 'scope': 'case', 'until': None, 'expired': False, 'source': 'concern', 'visibility': 'staff'} for x in concerns]   # both roles see them
        answers = [{'id': x['id'], 'quote': x['text'], 'kind': 'answer', 'by': x['by'], 'saidOn': x['saidOn'], 'answers': x['answers'], 'responseKind': x['responseKind'],
                    **({k: x[k] for k in ('actorName', 'actorRole')} if x.get('actorName') else {})} for x in v.get('concernAnswers', [])]   # the owner's replies to staff's concerns, shared with both roles
        lines += [{**x, 'scope': 'case', 'until': None, 'expired': False, 'source': 'concern_answer', 'visibility': 'staff'} for x in answers]

        def cite(x):
            return ('"' + quotes[x] + '"' if x in quotes else facts[x]['label'] + ': ' + facts[x]['display'] if x in facts else
                    'An earlier decision on invoice ' + decided[x]['invoiceReference'] if x in decided else x)
        s, status = brief.get('suggestion'), brief.get('suggestionStatus')
        asking = {q['id']: q['question'] for q in questions}
        suggestion = {'version': s['version'] if s else v.get('suggestionVersion'), 'status': status, 'outcome': s and s['outcome'],
                      'approvedDueDate': s and s['approvedDueDate'], 'sentence': s and s['sentence'], 'cites': [cite(x) for x in s['cites']] if s else [],
                      # the open questions it waits for, or why it could not be formed
                      'withheldBecause': [asking[x] for x in brief.get('withheldBecause') or [] if x in asking] or
                                         [x['text'] for x in brief.get('openItems') or [] if x.get('step') == 'suggest']} \
            if role == 'owner' and r['status'] == 'awaiting_owner' and status is not None else None
        d, invoice, row = v.get('decision'), snap.get('invoice') or {}, summary(r, self.records())
        on = lambda x: {**{k: x[k] for k in x if k != 'decidedAt'}, 'decidedOn': x['decidedAt'][:10]}   # the day: its time's digits are no figure
        return {'requestId': r['id'], 'status': r['status'], 'label': case_label(row, role), 'customer': (snap.get('customer') or {}).get('name'),
                'invoice': f and self.case_invoice(r, invoice, f), 'askedDate': asked, 'currentDue': due, 'extensionDays': ext,
                'dayLimit': limit and {'days': limit[1], 'fromLineId': limit[0], 'latestDate': due and (calendar_date(due) + timedelta(days=limit[1])).isoformat()},
                'comparison': {'askedDays': ext, 'limitDays': limit[1], 'withinLimit': ext <= limit[1]} if limit and ext is not None else None,
                'questions': questions, 'contextLines': lines, 'priorDecisions': [on(x) for x in ctx['decisions'] if x['requestId'] != r['id']],
                'suggestion': suggestion, 'decision': decision_view(d, role, 'summary'),
                'replyDraft': (v.get('responseDraft') or {}).get('text'), 'deliveryStatus': (v.get('responseDraft') or {}).get('deliveryStatus'),
                'preparedDecision': v.get('preparedDecision') and {k: x for k, x in v['preparedDecision'].items() if k not in ('by', 'at', 'givenAs')},   # the owner's
                # the owner's alone: every version prepared, with its status, and the one current (view leaves them out for staff)
                'preparations': [{**{k: y for k, y in x.items() if k not in ('by', 'at', 'decidedAt')}, **({'decidedOn': x['decidedAt'][:10]} if x.get('decidedAt') else {})}
                                 for x in v.get('preparations', [])] if role == 'owner' else None,
                'activePreparation': (v.get('preparedDecision') or {}).get('version'), 'concerns': concerns, 'answers': answers,
                'withStaff': returned(r) and {k: r['withStaff'][k] for k in ('kind', 'why')} or None,
                'withOwner': held(r) and {'kind': r['withOwner']['kind'], 'why': owner_pending(r, role)} or None,
                # the day: a time's digits are no figure; the calculation details as their summary (the full basis: GET api/requests/<id>/basis)
                'assessment': r.get('assessment') and {**{k: x for k, x in (r['assessment'] if role == 'owner' else staff_plain(r['assessment'])).items()
                                                           if k not in ('basis', 'authority', 'evidenceVersion')},
                                                        'basisSummary': basis_summary(r['assessment'].get('basis')), 'at': r['assessment']['at'][:10],
                                                        **({'stale': stale} if (stale := self.assessment_stale(r)) else {})},

                'flags': [{k: y for k, y in x.items() if k not in ('at', 'by')} for x in row['flags']], **{k: row[k] for k in DUE_FIELDS + ('ordinal',)}}

    def desk_done(self, actor, op, key, body):
        """The stored result of a desk write already made with this idempotency key, or None. Lock held."""
        require(isinstance(key, str) and 1 <= len(key) <= 160, 400, 'IDEMPOTENCY_REQUIRED', 'Idempotency-Key is required.')
        row = self.db.execute('SELECT payload_hash, result FROM record_ops WHERE key=?', (actor['id'] + ':desk-' + op + ':' + key,)).fetchone()
        if row:
            require(row[0] == fingerprint(body), 409, 'KEY_REUSED', 'This key was already used with different input.')
        return row and json.loads(row[1])

    def desk_remember(self, actor, op, key, body, result):
        with self.db:
            self.db.execute('INSERT INTO record_ops (key, payload_hash, result, at) VALUES (?,?,?,?)',
                            (actor['id'] + ':desk-' + op + ':' + key, fingerprint(body), json.dumps(result), now()))
        return result

    # ------------------------------------------------------------ sessions

    def signed_in(self, cookie):
        """Roles this browser holds a valid session for (one cookie per role)."""
        found = {}
        for role in self.demo_codes:
            morsel = cookie.get(self.cookie_prefix + role)
            actor = self.sessions.get(morsel.value) if morsel else None
            if actor and actor['role'] == role:
                found[role] = actor
        return found

    @staticmethod
    def identity_view(actor, held):
        """Who the session is (the AI Agent has a name and kind 'agent'), the roles this browser holds and the role selected."""
        return {'identity': {'id': actor['id'], 'name': actor.get('name'), 'kind': actor.get('kind', 'person')}, 'held': sorted(held), 'role': actor['role']}

    def identity(self, cookie, role=None):
        found = self.signed_in(cookie)
        if role:
            found = {role: found[role]} if role in found else {}
        require(found, 401, 'NO_SESSION', 'Sign in with a demo access code.')
        require(len(found) == 1, 400, 'ROLE_REQUIRED', 'Several roles are signed in; choose one.')
        return next(iter(found.values()))

    def login(self, body):
        """A session for the code. The kind of session is decided HERE from the code, never from the request: a service code (serviceCodes: the Lab's
        own, one per case role) makes a session with channel 'service'; an access code, and the AI Agent's, makes a person's (channel 'person').
        A 'channel' the client sends is ignored. Every session gets its own csrf token, which /api/session gives back to that session's page only
        and confirm and cancel require. A service code on its own never opens the console or another role."""
        code, expected = body.get('accessCode', ''), body.get('role')
        require(expected is None or expected in self.demo_codes, 400, 'INVALID_ROLE', 'Unknown role.')
        code = str(code)
        if self.agent_code and secrets.compare_digest(code, self.agent_code):   # the AI Agent: a session for every role at once
            made = {}
            for held in self.demo_codes:
                made[held] = secrets.token_urlsafe(32)
                self.sessions[made[held]] = {'id': AGENT_ID, 'name': AGENT_NAME, 'kind': 'agent', 'role': held, 'businessId': 'fictional_business',
                                             'channel': 'person', 'csrf': secrets.token_urlsafe(24)}
            first = expected if expected in made else 'staff'
            return self.sessions[made[first]], made
        served = next((r for r, c in self.service_codes.items() if secrets.compare_digest(code, c)), None)
        role = served or next((r for r, c in self.demo_codes.items() if secrets.compare_digest(code, c)), None)
        require(role is not None, 403, 'FORBIDDEN', 'Invalid demo access code.')
        # At a prompt for one role, a code for another role is refused rather than silently switching role (QA U2).
        require(expected is None or role == expected, 403, 'WRONG_ROLE_CODE', 'That is the ' + ROLE_WORDS[role] + ' code. Enter the ' +
                ROLE_WORDS[expected or role] + ' code to continue as ' + ROLE_WORDS[expected or role] + '.', 'accessCode')
        token = secrets.token_urlsafe(32)
        self.sessions[token] = {'id': role + '_demo', 'role': role, 'businessId': 'fictional_business', 'channel': 'service' if served else 'person',
                                'csrf': secrets.token_urlsafe(24)}
        return self.sessions[token], {role: token}

    def model_status(self):
        """Cached, best-effort health of the model service. Never called with the application lock held."""
        if self.agent_mode != 'live':
            return {'mode': self.agent_mode, 'state': 'not_used'}
        with self.status_lock:
            cached = self.status_cache
            if cached and time.monotonic() - cached[0] < 20:
                return cached[1]
        health = self.model_adapter.health()
        serving = health.get('serving') or {}
        state = 'ready' if health['reachable'] and serving.get('state') == 'loaded' else 'reachable_not_loaded' if health['reachable'] else 'unreachable'
        value = {'mode': 'live', 'state': state, 'serving': serving, 'checkedAt': now()}
        with self.status_lock:
            self.status_cache = (time.monotonic(), value)
        return value

    def agent_info(self):
        adapter, _ = self.adapter_for(self.agent_mode)
        return {'mode': self.agent_mode, 'promptVersion': PROMPT_VERSION if self.agent_mode == 'live' else None, **adapter.describe()}

    def dedup(self, actor, operation, key, body):
        require(isinstance(key, str) and 1 <= len(key) <= 160, 400, 'IDEMPOTENCY_REQUIRED', 'Idempotency-Key is required.')
        scoped = actor['id'] + ':' + operation + ':' + key
        row = self.db.execute('SELECT payload_hash,request_id FROM idempotency WHERE key=?', (scoped,)).fetchone()
        if row:
            require(row[0] == fingerprint(body), 409, 'KEY_REUSED', 'This key was already used with different input.')
            return scoped, self.get(row[1])
        return scoped, None

    def remember(self, key, body, record):
        self.db.execute('INSERT INTO idempotency VALUES (?,?,?)', (key, fingerprint(body), record['id']))

    # ------------------------------------------------------------ workflow commands (lock held by caller)

    def create(self, actor, body, key):
        require(actor['role'] == 'staff', 403, 'FORBIDDEN', 'Only staff submit requests.')
        message = body.get('messageText')
        require(isinstance(message, str) and 1 <= len(message.strip()) <= 8000, 400, 'INVALID_INPUT', 'Enter the customer message (1–8000 characters).', 'messageText')
        self.require_ready()
        scope, existing = self.dedup(actor, 'create', key, body)
        if existing:
            return existing
        with self.db:
            r = self.new_request(actor, {'channel': 'prototype_inbox', 'text': message, 'receivedAt': now()}, scope, body)
            self.schedule(r, 'request received')
        return r

    def new_request(self, actor, intake, scope, body, event=None, **fields):
        """A new request saved with its first event and its idempotency row (scope, as dedup scoped it; body, what it fingerprints), and nothing else:
        create queues the model's analysis after it, confirm_action builds the case by code. fields: values set at creation (a confirmed action's
        customer, invoice, date and reason, which no later step writes). Lock and transaction held; the caller owns the transaction."""
        r = {'id': uid('req'), 'version': 1, 'type': 'payment_extension', 'status': 'received',
             'dataMode': 'fictional', 'createdAt': now(), 'createdBy': actor['id'],
             'intake': intake,
             'answers': {}, 'customerId': None, 'invoiceId': None, 'requestedDueDate': None, 'requestReason': None,
             'activeRunId': None, 'analysis': None, 'task': None, 'decision': None, 'responseDraft': None, **fields}
        self.save(r)
        self.event(r, 'request.received', {'channel': intake['channel'], 'dataMode': 'fictional', **(event or {})})
        self.remember(scope, body, r)
        return r

    def answer(self, actor, r, task_id, body, key):
        # A request opened from a confirmed action: its customer, invoice and date were fixed by the person who confirmed it, so no answer sets them.
        require(r['intake'].get('structured') is None, 409, 'CONFIRMED_FIELDS_LOCKED', LOCKED_FIELDS)
        scope, previous = self.dedup(actor, 'answer:' + r['id'], key, body)
        if previous:
            return previous
        require(r['status'] == 'needs_information' and r['task']['id'] == task_id, 409, 'STALE_TASK', 'This clarification is no longer pending.')
        self.version(r, body)
        answers = body.get('answers')
        require(isinstance(answers, list) and len(answers) > 0, 400, 'INVALID_INPUT', 'Provide at least one answer.')
        allowed = {x['field'] for x in r['task']['missingFields']}
        updates = {}
        for item in answers:
            require(isinstance(item, dict) and item.get('field') in allowed, 400, 'INVALID_FIELD', 'Answer only the fields requested by this task.')
            field, value = item['field'], item.get('value')
            require(isinstance(value, str) and 0 < len(value.strip()) <= 200, 400, 'INVALID_INPUT', 'Enter a value.', field)
            ev = self.evidence()
            if field == 'requestedDueDate':
                try:
                    wanted = calendar_date(value)
                except ValueError as exc:
                    raise APIError(400, 'INVALID_DATE', str(exc), field)
                invoice = next((i for i in ev.invoices if i['id'] == r.get('invoiceId')), None)
                due = ev.current_due(invoice) if invoice else None
                floor = max(ev.as_of, calendar_date(due)) if due else ev.as_of
                require(wanted > floor, 422, 'INVALID_DATE', 'Enter a date after ' + display_date(floor.isoformat()) +
                        (' (the current due date).' if floor > ev.as_of else ' (the as-of date).'), field)
            if field == 'invoiceReference':
                require(ev.invoices_by_ref(value), 422, 'UNKNOWN_INVOICE',
                        'No invoice "' + value.strip()[:40] + '" is in the records. Check the invoice number.', field)
            if field == 'invoiceId':
                offered = next(m for m in r['task']['missingFields'] if m['field'] == 'invoiceId')['choices']
                require(value in {c['invoiceId'] for c in offered} and ev.invoice(value) is not None, 422, 'INVALID_CHOICE',
                        'Choose one of the listed invoices.', field)
            updates[field] = ref_key(value) if field == 'invoiceReference' else value
        with self.db:
            self.event(r, 'clarification.answered', {'task': r['task'], 'answers': updates, 'actor': actor['id'], **trail(actor), 'origin': 'staff_reported' if actor['role'] == 'staff' else 'owner_confirmed'})
            r['answers'].update(updates)
            r['task']['status'] = 'answered'
            r['version'] += 1
            r['status'] = 'received'
            self.save(r)
            self.remember(scope, body, r)
            self.schedule(r, 'clarification answered')
        return r

    def owner_question(self, actor, r, question_id, action, body, key):
        """The owner answers one of the case's questions, or decides without it (skip). An answer is a confirmed, owner-only
        statement with one guidance line about this case, or about its customer when the owner keeps it for them; the question
        records the line that answers it. Staff may answer a question asked of staff (from 'staff'), never skip one: theirs is a
        proposed statement shared with staff, one observation line about this case only. Neither changes the request version, the
        evidence or the decision controls, and nothing is prepared again; only the suggestion is, when the owner has it on.
        build_statement checks again that only the owner confirms."""
        scope, previous = self.dedup(actor, action + '-question:' + question_id, key, body)
        if previous:
            return previous
        require(r['status'] == 'awaiting_owner', 409, 'INVALID_TRANSITION', 'This case is not waiting for the owner.')
        q = next((x for x in r['analysis']['brief'].get('questions') or () if x['id'] == question_id), None)
        require(q is not None, 404, 'NOT_FOUND', 'Question not found.')
        owner = actor['role'] == 'owner'
        require(owner or action == 'answer' and q['from'] == 'staff', 403, 'FORBIDDEN', 'Only the owner answers these questions.')
        require(q['status'] == 'open', 409, 'INVALID_TRANSITION', 'This question is no longer open.')
        if action == 'answer':
            text, keep = body.get('text'), body.get('keepForCustomer', False) if owner else False   # staff answer for this case only
            require(isinstance(text, str) and 1 <= len(text.strip()) <= 500, 400, 'INVALID_INPUT', 'Enter an answer (1–500 characters).', 'text')
            require(isinstance(keep, bool), 400, 'INVALID_INPUT', 'Choose whether to keep this for the customer.', 'keepForCustomer')
            s = self.build_statement(actor, text.strip(), thread_id=None, visibility='owner' if owner else 'staff', status='confirmed' if owner else 'proposed',
                                     scope={'kind': 'customer', 'customerId': r['customerId']} if keep else {'kind': 'case', 'requestId': r['id']},
                                     lines=[{'kind': 'guidance' if owner else 'observation', 'quote': text.strip()}],
                                     source={'kind': 'answer', 'questionId': q['id'], **({'lineId': q['lineId']} if q.get('lineId') else {})})
            q['answeredBy'] = s['lines'][0]['id']
        q['status'] = {'answer': 'answered', 'skip': 'skipped'}[action]
        with self.db:
            if action == 'answer':
                self.save_statement(s)
            self.save(r)
            self.event(r, 'question.' + q['status'], {'questionId': q['id'], 'from': q['from']})   # staff see the event of a staff question
            self.remember(scope, body, r)
            if self.meta('showSuggestions'):
                self.schedule_suggest(r, 'question ' + q['status'])
        return r

    def version(self, r, body):
        require(type(body.get('expectedRequestVersion')) is int and body['expectedRequestVersion'] == r['version'],
                409, 'STALE_VERSION', 'The request changed. Refresh before acting.')

    def reanalyse(self, actor, r, body, key):
        scope, previous = self.dedup(actor, 'reanalyse:' + r['id'], key, body)
        if previous:
            return previous
        self.version(r, body)
        require(r['status'] in STATES_BEFORE_DECISION, 409, 'INVALID_TRANSITION', 'A final decision cannot be reanalysed.')
        with self.db:
            r['version'] += 1
            r['status'] = 'received'
            self.save(r)
            self.remember(scope, body, r)
            self.schedule(r, 'reanalysis requested by ' + actor['id'])
        return r

    def decide(self, actor, r, body, key):
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner can commit a financial decision.')
        scope, previous = self.dedup(actor, 'decide:' + r['id'], key, body)
        if previous:
            return previous
        self.version(r, body)
        require(r['status'] == 'awaiting_owner' and r['decision'] is None, 409, 'INVALID_TRANSITION', 'There is no pending owner decision.')
        a = r['analysis']
        ev = self.evidence()
        current = ev.version_for(r['invoiceId'])
        require(body.get('analysisId') == a['id'] and body.get('evidenceVersion') == current == a['snapshot']['evidenceVersion'],
                409, 'STALE_EVIDENCE', 'Evidence changed. Reanalyse before deciding.')
        pv, p = body.get('preparedVersion'), r.get('preparedDecision')
        # the Confirm decision button (the case page) sends a prepared decision's values with its version: only the current one, as prepared
        require(pv is None or type(pv) is int and p is not None and p['version'] == pv and
                all(body.get(k) == p[k] for k in ('outcome', 'approvedDueDate', 'reason', 'suggestionShown')),
                409, 'STALE_PREPARATION', 'This prepared decision was replaced or the case changed. Prepare it again.')
        outcome, approved, reason = body.get('outcome'), body.get('approvedDueDate'), body.get('reason')
        require(outcome in ('approve', 'decline'), 400, 'INVALID_OUTCOME', 'Choose approve or decline.')
        require(isinstance(reason, str) and 1 <= len(reason.strip()) <= 2000, 400, 'INVALID_REASON', 'Enter a brief reason for this decision.', 'reason')
        due, floor = self.due_and_floor(ev, r)   # due: None when no due date is on record
        if outcome == 'approve':
            try:
                valid = calendar_date(approved) > floor
            except (ValueError, TypeError):
                valid = False
            require(valid, 422, 'INVALID_DATE', 'Choose a date after ' + display_date(floor.isoformat()) + '.', 'approvedDueDate')
        else:
            require(approved is None, 400, 'INVALID_DATE', 'A declined request must not contain an approved date.', 'approvedDueDate')
        shown, keep, brief = body.get('suggestionShown'), body.get('remember') or (pv is not None and p or {}).get('remember'), a['brief'] or {}
        given = brief.get('suggestion') if brief.get('suggestionStatus') == 'given' else None
        if shown is not None:
            require(isinstance(shown, dict) and type(shown.get('version')) is int, 400, 'INVALID_INPUT',
                    'Name the version of the suggestion shown.', 'suggestionShown')
            require(given is not None and all(shown.get(k) == given[k] for k in ('version', 'outcome', 'approvedDueDate')), 409,
                    'STALE_SUGGESTION', 'The suggestion changed. Refresh before deciding.')
        if keep is not None:
            problem = remember_problem(keep)
            require(problem is None, 400, 'INVALID_INPUT', problem and problem[0], 'remember')
        seen = shown and {k: given[k] for k in ('version', 'outcome', 'approvedDueDate')}
        r['decision'] = {'id': uid('decision'), 'requestId': r['id'], 'requestVersionBefore': r['version'],
                         'analysisId': a['id'], 'evidenceVersion': current, 'outcome': outcome,
                         'approvedDueDate': approved, 'reason': reason.strip(),
                         'approvedExtensionDays': (calendar_date(approved) - calendar_date(due)).days if outcome == 'approve' and due else None,
                         'scope': {'kind': 'single_invoice', 'invoiceId': r['invoiceId']},
                         'decidedBy': actor['id'], **trail(actor), 'decidedAt': now(), 'decisionSource': 'owner', **followed(r.get('assessment'), outcome),
                         'basis': frozen_basis(r.get('assessment'))}   # the assessment it was made on, frozen: later records, assessments and limits never change it
        # What the owner was shown, stored beside the decision and never in it (E017); the relation is computed here. None: no
        # suggestion was on screen.
        r['suggestionSeen'] = seen and {**seen, 'relation': 'declined_against' if seen['outcome'] != outcome else
                                        'accepted' if seen['approvedDueDate'] == approved else 'changed'}
        r['evidenceSeen'] = ev.decision_evidence(r['invoiceId'])   # later changes to it are flagged on the case, never applied to the decision
        # Remembered in the owner's own words, as guidance; the outcome itself is history (context_for's decisions), and the
        # decision's reason stays on the decision.
        note = keep and self.build_statement(actor, keep['text'].strip(), thread_id=None, visibility='owner', status='confirmed',
                                             scope={'kind': 'customer', 'customerId': r['customerId']} if keep.get('keepForCustomer') else
                                             {'kind': 'case', 'requestId': r['id']}, lines=[{'kind': 'guidance', 'quote': keep['text'].strip(), 'until': keep.get('until')}],
                                             source={'kind': 'decision', 'id': r['decision']['id']})
        with self.db:
            if note:
                self.save_statement(note)
            r['version'] += 1
            r['status'] = 'decided'
            r['task']['status'] = 'decided'
            self.event(r, 'decision.committed', r['decision'])
            if pv is None:   # decided through the form: a preparation left current is withdrawn; nothing is left to confirm
                self.end_preparation(r, 'withdrawn', actor['id'], trail(actor))
            else:
                self.end_preparation(r, 'confirmed', actor['id'], trail(actor), decidedAt=r['decision']['decidedAt'])
            self.save(r)
            self.remember(scope, body, r)
            self.dg_request_decided(r, actor)   # the case of a delegated request is decided with it
        self.finish(r)
        self.research_after_verdict()
        return r

    def end_preparation(self, r, status, by, who=None, **extra):
        """The current prepared decision, if any, is no longer confirmable: it leaves preparedDecision, is marked status ('superseded',
        'withdrawn' or 'confirmed') with extra in the case's history of preparations, and the event decision.<status> says so. by: who
        caused it (None: the app, when the case is prepared again or its suggestion replaced). The caller saves r. Lock and
        transaction held. who: the trail of whoever caused it (the preparation keeps its preparer's; the end is `endedBy...`)."""
        p = r.pop('preparedDecision', None)
        if p:
            for x in r.get('preparations', ()):   # none for one prepared before the history was kept: the event alone
                if x['version'] == p['version']:
                    x.update({'status': status, **({'endedByName': who['actorName'], 'endedByRole': who['actorRole']} if who and who['actorName'] else {}), **extra})
            self.event(r, 'decision.' + status, {'version': p['version'], 'by': by, **(who or {}), **extra})
        return p

    @staticmethod
    def due_and_floor(ev, r):
        """The case invoice's current due date (None when none is on record), and the date an approval must fall after: the later of
        it and the as-of date."""
        due = ev.current_due(next(i for i in ev.invoices if i['id'] == r['invoiceId']))
        return due, max(calendar_date(due), ev.as_of) if due else ev.as_of

    # ------------------------------------------------------------ controlled actions (docs/CONTROLLED-AGENT-ACTIONS.md)
    # An action is a proposal the assistant prepared and a PERSON confirms over HTTP. Its business effect is fixed by this code when it is prepared
    # (params, basis) and again when it is confirmed (revalidated against the records as they are then): no model and no later answer alters it.

    def get_action(self, action_id):
        """The action as stored: its columns and its data in one dict. 404 NOT_FOUND. Lock held."""
        row = self.db.execute('SELECT id, kind, status, invoice_id, created_at, data FROM actions WHERE id=?', (action_id,)).fetchone()
        require(row is not None, 404, 'NOT_FOUND', 'Action not found.')
        return {**json.loads(row[5]), 'id': row[0], 'kind': row[1], 'status': row[2], 'invoiceId': row[3], 'createdAt': row[4]}

    @staticmethod
    def action_data(a):
        return {k: v for k, v in a.items() if k not in ('id', 'kind', 'status', 'invoiceId', 'createdAt')}

    def add_action(self, a):
        """Save a new action. Lock and transaction held."""
        self.db.execute('INSERT INTO actions (id, kind, status, invoice_id, created_at, data) VALUES (?,?,?,?,?,?)',
                        (a['id'], a['kind'], a['status'], a['invoiceId'], a['createdAt'], json.dumps(self.action_data(a))))

    def move_action(self, a, status, role, **fields):
        """The action in a new status, with what it now records (outcome, requestId, confirmed...) and the step in its history. Lock and transaction held."""
        a.update(fields)
        a['status'] = status
        a['history'] = [*a.get('history', []), {'at': now(), 'status': status, 'role': role}]
        self.db.execute('UPDATE actions SET status=?, data=? WHERE id=?', (status, json.dumps(self.action_data(a)), a['id']))

    def supersede_actions(self, kind, invoice_id, role, by):
        """Settle the proposals still open for this invoice because a new one (by) is being made: 'expired' if past their time, else 'superseded'.
        Returns the ids superseded. Lock and transaction held, so the old ones are never confirmable beside the new one."""
        done = []
        for (action_id,) in self.db.execute("SELECT id FROM actions WHERE kind=? AND invoice_id=? AND status='proposed'", (kind, invoice_id)).fetchall():
            a = self.get_action(action_id)
            if action_state(a) == 'expired':
                self.move_action(a, 'expired', role, outcome={'code': 'EXPIRED', 'message': 'It was not confirmed in time.'})
            else:
                self.move_action(a, 'superseded', role, supersededBy=by, outcome={'code': 'SUPERSEDED', 'message': 'A newer proposal for this invoice replaced it.'})
                done.append(action_id)
        return done

    def open_request_on(self, invoice_id):
        """The id of a request on this invoice that nobody has decided or withdrawn, else None: any request in STATES_BEFORE_DECISION naming the
        invoice, and the request of an executed action that is still being prepared (its invoice not yet identified). One per invoice, whatever
        the idempotency retention. Lock held."""
        for r in self.records():
            if r.get('invoiceId') == invoice_id and r['status'] in STATES_BEFORE_DECISION:
                return r['id']
        for (data,) in self.db.execute("SELECT data FROM actions WHERE kind='open_request' AND invoice_id=? AND status='executed'", (invoice_id,)).fetchall():
            row = self.db.execute('SELECT data FROM requests WHERE id=?', (json.loads(data).get('requestId'),)).fetchone()
            if row and json.loads(row[0])['status'] in ACTIVE_STATES:
                return json.loads(row[0])['id']
        return None

    def action_problem(self, ev, invoice, requested=None):
        """The first reason an extension request cannot be opened for this invoice on the records as they are now, (code, message, extra), else None:
        the invoice is not open, no due date is on record, (with requested) the date is not after the current due date and the as-of date, or
        a request is already open on it. prepareRequest and confirm_action both judge by this. Lock held."""
        if not is_open(invoice):
            return 'INVOICE_NOT_OPEN', 'Invoice ' + invoice['reference'] + ' is not open: the records show it as paid.', {}
        due = ev.current_due(invoice)
        if not due:
            return 'UNKNOWN_DUE_DATE', UNKNOWN_DUE_DATE, {}
        if requested is not None:
            floor = max(ev.as_of, calendar_date(due))
            if not calendar_date(requested) > floor:
                return 'INVALID_DATE', 'The new due date must be after ' + display_date(floor.isoformat()) + (' (the current due date).' if floor > ev.as_of else ' (the as-of date).'), {}
            open_id = self.open_request_on(invoice['id'])
            if open_id:
                return 'OPEN_REQUEST_EXISTS', 'A request for invoice ' + invoice['reference'] + ' is already open, so another is not opened.', {'requestId': open_id}
        return None

    def action_changed(self, ev, a):
        """Why a proposed action no longer holds on the records as they are now, (code, message, extra), else None: the customer or invoice gone or no
        longer together, the customer's evidence version (any invoice, payment, allocation, due date, opening balance or note) or the invoice's
        current due date other than at preparation, or action_problem. Lock held."""
        p, basis = a['params'], a['basis']
        customer, invoice = ev.customer(p['customerId']), ev.invoice(p['invoiceId'])
        if customer is None or invoice is None or invoice['customerId'] != customer['id']:
            return 'RECORDS_CHANGED', 'The customer or the invoice is no longer in the records, or they no longer belong together.', {}
        if ev.version_for(invoice['id']) != basis['evidenceVersion']:
            return 'RECORDS_CHANGED', ('The records for ' + customer['name'] + ' changed after this was prepared (an invoice, a payment, an allocation, a due date '
                                       'or a note). Prepare it again from the current records.'), {}
        if ev.current_due(invoice) != basis['currentDueDate']:
            return 'RECORDS_CHANGED', 'The due date of invoice ' + invoice['reference'] + ' changed after this was prepared. Prepare it again from the current records.', {}
        return self.action_problem(ev, invoice, p['requestedDueDate'])

    def request_view(self, request_id):
        """{id, status, label} of the request an action opened, as the case list words it (case_label), else None. The label's words are for the
        viewer's role; nothing of the case itself (no brief, suggestion or owner notes) is in it. Lock held."""
        row = request_id and self.db.execute('SELECT data FROM requests WHERE id=?', (request_id,)).fetchone()
        r = row and json.loads(row[0])
        return r and {'id': r['id'], 'status': r['status'], 'summary': summary(r, self.records())}

    def action_view(self, actor, a):
        """GET api/actions/<id>: the action as a person or the assistant may read it, a pure read. status is computed (expired past expiresAt, not
        written); params and preview are as they were fixed when it was prepared; request is {id, status, label} of the request it opened, the
        label in this viewer's role's words. Nothing owner-only is in it. Lock held."""
        if a['kind'] == 'evidence':
            return self.evidence_action_view(actor, a)
        p, shown = a['params'], self.request_view(a.get('requestId'))
        return {'id': a['id'], 'kind': a['kind'], 'status': action_state(a), 'version': a['version'], 'createdAt': a['createdAt'], 'expiresAt': a['expiresAt'],
                'preparedBy': {'role': a['preparedBy']['role']},
                'params': {'customerId': p['customerId'], 'customerName': a['preview']['fromRecords']['customer']['name'], 'invoiceId': p['invoiceId'],
                           'invoiceReference': p['invoiceReference'], 'currentDueDate': p['currentDueDate'], 'requestedDueDate': p['requestedDueDate'],
                           'days': p['days'], 'reasonDraft': p['reasonDraft']},
                'preview': a['preview'], 'outcome': a.get('outcome'), 'requestId': a.get('requestId'),
                'confirmed': a.get('confirmed') and {k: a['confirmed'][k] for k in ('at', 'role', 'reason')},
                'request': shown and {'id': shown['id'], 'status': shown['status'], 'label': case_label(shown['summary'], actor['role'])}}

    @staticmethod
    def person_required(actor):
        """Confirming or cancelling an action needs a person signed in to Nucleon: never the AI Agent's identity, and never a service session (made
        with a service code, which is the only way a session gets channel 'service': login sets it, a client cannot). Records has no per-person
        identity: a role's session is as specific as a person gets, and anyone holding the person's staff access code can confirm."""
        require(actor.get('kind') != 'agent' and actor.get('channel') != 'service', 403, 'PERSON_REQUIRED',
                'Only a person signed in to Nucleon can confirm or cancel an action, not the assistant or a service connection.')

    @staticmethod
    def require_csrf(actor, token):
        """The session's own csrf token, sent by its page in X-Nucleon-CSRF (read from /api/session): a write another site or a script drives with
        the browser's cookie but without the page's token is 403 CSRF_REQUIRED, nothing changed. Compared in constant time."""
        want = actor.get('csrf')
        require(isinstance(token, str) and isinstance(want, str) and secrets.compare_digest(token.encode(), want.encode()), 403, 'CSRF_REQUIRED',
                'Reload the Nucleon page and try again: this request did not carry the page\'s security token.')

    @staticmethod
    def action_key(key):
        require(isinstance(key, str) and 1 <= len(key) <= 160, 400, 'IDEMPOTENCY_REQUIRED', 'Idempotency-Key is required.')

    def confirm_action(self, actor, action_id, body, key):
        """POST api/actions/<id>/confirm {version}: a staff person confirms the proposal they were shown, and Nucleon opens the request for the owner
        to decide. Confirming submits; it approves nothing. The effect is fixed by code: the request's customer, invoice, date AND REASON are the
        action's frozen params (the reason is the assistant's draft, params.reasonDraft: the body carries none, and one that differs is 400
        REASON_FROZEN, nothing changed; to change the wording, cancel and prepare a new proposal). The case is built by application code
        (structured_case) with no model run, and what the records say now is checked first. All of it is ONE transaction (a crash or an exception
        before commit leaves the action proposed and no request; after commit every retry replays), under the lock. The Idempotency-Key is a
        convention; the action id is the identity. Refusals that change nothing: 401/403, 404, 400 REASON_FROZEN, 409 ACTION_NOT_LIVE,
        STALE_ACTION_VIEW, 400 INVALID_INPUT. Refusals that settle the action, committed before the 409: ACTION_EXPIRED (writes expired) and the
        records no longer supporting it (writes invalidated with the code: RECORDS_CHANGED, INVOICE_NOT_OPEN, INVALID_DATE, OPEN_REQUEST_EXISTS).
        The caller has already checked the csrf token (require_csrf). Lock held."""
        self.person_required(actor)
        require(actor['role'] == 'staff', 403, 'FORBIDDEN', 'Only staff confirm a request for the owner to decide.')
        self.action_key(key)
        a = self.get_action(action_id)
        require(a['kind'] == 'open_request', 409, 'WRONG_ACTION_KIND', 'This action is not a proposal to confirm.')
        reason = a['params']['reasonDraft']   # frozen when prepared: the only reason this action can ever carry
        require('reason' not in body or body['reason'] == reason, 400, 'REASON_FROZEN',
                'The reason is the one the assistant drafted and cannot be changed here. To change the wording, cancel this proposal and ask the assistant to prepare a new one.', 'reason')
        if a['status'] == 'executed':   # a retry, a second tab, a lost response: the stored answer
            shown = self.request_view(a['requestId'])
            return {'action': self.action_view(actor, a), 'request': shown and shown['summary'], 'replayed': True}
        require(a['status'] == 'proposed', 409, 'ACTION_NOT_LIVE', 'This action is no longer open to confirm (' + action_state(a) + ').')
        if action_state(a) == 'expired':
            with self.db:
                self.move_action(a, 'expired', actor['role'], outcome={'code': 'EXPIRED', 'message': 'It was not confirmed in time. Prepare it again.'})
            raise refusal(409, 'ACTION_EXPIRED', 'This proposal expired before it was confirmed. Ask the assistant to prepare it again.', action=self.action_view(actor, a))
        require(type(body.get('version')) is int and body['version'] == a['version'], 409, 'STALE_ACTION_VIEW',
                'This proposal is not the version you were shown. Reload it before confirming.')
        self.require_ready()
        refused = None
        with self.db:
            ev = self.evidence()
            problem = self.action_changed(ev, a)
            if problem:
                code, message, extra = problem
                self.move_action(a, 'invalidated', actor['role'], outcome={'code': code, 'message': message, **extra})
                refused = refusal(409, code, message, action=self.action_view(actor, a), **extra)
            else:
                r = self.open_confirmed(actor, a, ev, reason)
        if refused:
            raise refused
        self.settled.notify_all()
        return {'action': self.action_view(actor, a), 'request': summary(r, self.records())}

    def open_confirmed(self, actor, a, ev, reason):
        """The request a confirmed action opens, and the action executed: created through new_request (the same code as create, with its event and
        idempotency row key 'action:<id>' for the confirming actor), its case built at once by structured_case, never queued for a model. Its customer,
        invoice, date and reason are the action's frozen params (the reason is params.reasonDraft: nothing a person or a body adds). Lock and transaction held."""
        p = a['params']
        text = ('Payment-extension request for invoice ' + p['invoiceReference'] + ' (' + a['preview']['fromRecords']['customer']['name'] + '): requested new due date ' +
                p['requestedDueDate'] + ' (from ' + p['currentDueDate'] + ', ' + days_text(p['days']) + '). ' +
                ('Reason given: ' + ' '.join(reason.split()) if reason else 'No reason given.'))
        structured = {'actionId': a['id'], 'customerId': p['customerId'], 'invoiceId': p['invoiceId'], 'invoiceReference': p['invoiceReference'],
                      'requestedDueDate': p['requestedDueDate'], 'currentDueDate': p['currentDueDate'], 'days': p['days'], 'reason': reason}
        r = self.new_request(actor, {'channel': 'confirmed_action', 'text': text, 'receivedAt': now(), 'structured': structured},
                             actor['id'] + ':create:action:' + a['id'], {'actionId': a['id'], 'version': a['version']}, event={'actionId': a['id']},
                             customerId=p['customerId'], invoiceId=p['invoiceId'], requestedDueDate=p['requestedDueDate'], requestReason=reason)
        self.structured_case(r)
        self.move_action(a, 'executed', actor['role'], requestId=r['id'], confirmed={'at': now(), 'role': actor['role'], 'actorId': actor['id'], 'reason': reason})
        return self.get(r['id'])

    def cancel_action(self, actor, action_id, body, key):
        """POST api/actions/<id>/cancel: a person (staff or the owner) withdraws a proposal before it is confirmed. Only a proposed action can be;
        one that has run, was settled or has expired is 409 ACTION_NOT_LIVE. Lock held."""
        self.person_required(actor)
        require(actor['role'] in CASE_ROLES, 403, 'FORBIDDEN', 'Only staff or the owner cancel an action.')
        self.action_key(key)
        a = self.get_action(action_id)
        require(a['kind'] == 'open_request', 409, 'WRONG_ACTION_KIND', 'This action is not a proposal to cancel.')
        state = action_state(a)
        if state == 'expired':   # settle it, as a confirm would
            with self.db:
                self.move_action(a, 'expired', actor['role'], outcome={'code': 'EXPIRED', 'message': 'It was not confirmed in time.'})
        require(state == 'proposed', 409, 'ACTION_NOT_LIVE', 'This action is no longer open to cancel (' + state + ').')
        with self.db:
            self.move_action(a, 'cancelled', actor['role'], outcome={'code': 'CANCELLED', 'message': 'A person cancelled it before it was confirmed.'})
        return {'action': self.action_view(actor, a)}

    # ------------------------------------------------------------ adaptive decision authority (docs/ADAPTIVE-DECISION-AUTHORITY.md)
    # The Owner delegates (a versioned policy, Owner person only); the assistant recommends; delegation.evaluate (pure code) decides whether the
    # recommendation takes effect, under the CURRENT policy at the moment of execution. A decision case is written in the same transaction as the
    # request or decision it causes. All of it under the lock. The model never sets a status, widens the policy or sends anything to a customer.

    def policy_current(self):
        """The effective delegation policy: the latest saved version, else version 0 (advisory, everything off, so nothing executes). Lock held."""
        row = self.db.execute('SELECT version, created_at, data FROM delegation_policies ORDER BY version DESC LIMIT 1').fetchone()
        if row:
            data = json.loads(row[2])
            rules = {k: data[k] for k in delegation.POLICY_KEYS if k in data}   # a version saved before `feedback` existed has no such key
            digest = delegation.policy_digest(rules)   # of the rules as saved: a version saved before staffCheckedDepositUpTo existed keeps its digest and reads as null (strictest)
            rules['newCustomers'] = {'staffCheckedDepositUpTo': None, **rules['newCustomers']}
            rules['feedback'] = {'tacitAgreeAfterDays': None, **rules.get('feedback', {})}   # and reads as off
            rules['trackRecord'] = {'sources': 'both', **rules['trackRecord']}   # and a version saved before trackRecord.sources existed counts both (D7)
            rules['customers'] = rules.get('customers') or {}   # versions saved before customer rules and the exception band existed read as none / off
            rules['exceptions'] = {**delegation.EXCEPTIONS_DEFAULT, **(rules.get('exceptions') or {})}
            rules['smallOverage'] = {**delegation.SMALL_OVERAGE_DEFAULT, **(rules.get('smallOverage') or {})}   # versions saved before the allowance (5 Nov) read as off
            rules['autoDecline'] = {**delegation.AUTO_DECLINE_DEFAULT, **(rules.get('autoDecline') or {})}   # and before autonomous decline (8 Nov) as off
            return {**rules, 'version': row[0], 'createdAt': row[1], 'createdBy': data.get('createdBy'), 'note': data.get('note'), 'digest': digest}
        rules = delegation.default_policy(settings_of(self.fixture()))
        return {**rules, 'version': 0, 'createdAt': None, 'createdBy': None, 'note': 'No policy has been saved: advisory mode, nothing executes.',
                'digest': delegation.policy_digest(rules)}

    @staticmethod
    def policy_view(actor, policy):
        """The policy as this role reads it: staff may read the current rules (read-only), without who saved them."""
        return {**{k: v for k, v in policy.items() if actor['role'] == 'owner' or k != 'createdBy'}, 'readOnly': actor['role'] != 'owner'}

    def save_policy(self, actor, body, action=None):
        """PUT api/delegation/policy {expectedVersion, note?, ...policy}, POST .../pause and .../resume {expectedVersion, note?}: the Owner, as a PERSON
        (the caller has checked person_required and the csrf token, as for confirm), saves a NEW version; nothing is edited in place. A stale
        expectedVersion is 409 POLICY_CHANGED (with the current policy). The policy is strict (delegation.validate_policy: an unknown key is 400).
        A PUT keeps the current pause unless it says otherwise. No tool, MCP call or service session reaches this. Lock held."""
        self.person_required(actor)
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner changes the delegation policy.')
        body = dict(body)
        expected, note = body.pop('expectedVersion', None), body.pop('note', None)
        require(type(expected) is int and expected >= 0, 400, 'INVALID_INPUT', 'Name the policy version you were shown (expectedVersion).', 'expectedVersion')
        require(note is None or isinstance(note, str) and len(note.strip()) <= 500, 400, 'INVALID_INPUT', 'The note is text of at most 500 characters.', 'note')
        doc = self.fixture()
        require(doc is not None, 409, 'NO_RECORDS', 'Set the currency, decimal places and time zone under Records first.')
        current = self.policy_current()
        if expected != current['version']:
            raise refusal(409, 'POLICY_CHANGED', 'The policy was changed since you loaded it (it is now version ' + str(current['version']) + '). Reload and review it.',
                          current=self.policy_view(actor, current))
        if action:
            require(not body, 400, 'INVALID_INPUT', 'Pause and resume take no settings.')
            rules = {k: current[k] for k in delegation.POLICY_KEYS}
            require(rules['paused'] != (action == 'pause'), 409, 'INVALID_TRANSITION', 'The policy is already ' + ('paused' if rules['paused'] else 'running') + '.')
            rules['paused'] = action == 'pause'
        else:
            # Until the Owner page has controls for them (S2), two settings keep the CURRENT version's value when the body leaves them out (an explicit value, null included, wins).
            # Every other key that is left out still takes its version-0 value (validate_policy), so leaving one out never widens a bound.
            fb, tr = body.get('feedback', {}), body.get('trackRecord', {})
            if isinstance(fb, dict) and 'tacitAgreeAfterDays' not in fb:
                body['feedback'] = {**fb, 'tacitAgreeAfterDays': current['feedback']['tacitAgreeAfterDays']}
            if isinstance(tr, dict) and 'sources' not in tr:
                body['trackRecord'] = {**tr, 'sources': current['trackRecord']['sources']}
            if 'customers' not in body:   # the customer rules are edited on their own part of the panel; a save of the form keeps them
                body['customers'] = current.get('customers') or {}
            if 'exceptions' not in body:   # a client that predates the exception band keeps the current one
                body['exceptions'] = current.get('exceptions') or delegation.EXCEPTIONS_DEFAULT
            if 'smallOverage' not in body:   # likewise the small-overage allowance
                body['smallOverage'] = current.get('smallOverage') or delegation.SMALL_OVERAGE_DEFAULT
            if 'autoDecline' not in body:   # and autonomous decline (8 Nov)
                body['autoDecline'] = current.get('autoDecline') or delegation.AUTO_DECLINE_DEFAULT
            ext = body.get('extensions')
            if isinstance(ext, dict):   # a client that predates the two Quick setup day limits (11 Nov) keeps them; an explicit null still clears one
                body['extensions'] = {**{k: current['extensions'].get(k) for k in delegation.EXTRA_DAY_LIMITS if k not in ext}, **ext}
            rules = delegation.validate_policy({'paused': current['paused'], **body}, settings_of(doc))
        with self.db:
            self.db.execute('INSERT INTO delegation_policies (version, created_at, data) VALUES (?,?,?)',
                            (current['version'] + 1, now(), json.dumps({**rules, 'createdBy': {'actorId': actor['id'], 'role': actor['role'], 'channel': 'person', **trail(actor)},
                                                                        'note': note.strip() if note else None, 'action': action or 'save'})))
        return self.policy_view(actor, self.policy_current())

    def policy_history(self, actor):
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner reads the policy history.')
        out = []
        for version, created_at, data in self.db.execute('SELECT version, created_at, data FROM delegation_policies ORDER BY version DESC').fetchall():
            d = json.loads(data)
            rules = {k: d[k] for k in delegation.POLICY_KEYS if k in d}
            digest = delegation.policy_digest(rules)
            rules['newCustomers'] = {'staffCheckedDepositUpTo': None, **rules['newCustomers']}
            rules['feedback'] = {'tacitAgreeAfterDays': None, **rules.get('feedback', {})}
            rules['trackRecord'] = {'sources': 'both', **rules['trackRecord']}
            out.append({**rules, 'version': version, 'createdAt': created_at, 'createdBy': d.get('createdBy'), 'note': d.get('note'), 'action': d.get('action'),
                        'digest': digest})
        return {'versions': out, 'currentVersion': out[0]['version'] if out else 0}

    # ---- the facts a decision rests on

    def dg_template(self, doc=None):
        s = settings_of(doc or self.fixture())
        return {'currency': s['currency'], 'scale': s['scale']}

    def dg_ledger(self, doc, ev, customer_id, invoice_id=None):
        """What one customer's records show, for delegation.evaluate: the replay's current and prior facts (behaviour.assessment_facts, the same one the
        assessment reads), the receipts that could be a deposit, the earlier invoice totals and whether the owner confirmed the records complete. Returns
        (ledger, replay facts). Lock held."""
        mine = customer_records(doc, customer_id)
        f = assessment_facts(mine['invoices'], mine['payments'], doc.get('allocations', []), mine['openingBalances'], ev.as_of, invoice_id)
        receipts = [{'id': p['id'], 'reference': p.get('reference'), 'amount': minor(p['amount']), 'receivedDate': p.get('receivedDate'),
                     'unallocated': minor(p['amount']) - allocated_from(doc, p['id'])}
                    for p in mine['payments'] if active(p) and p.get('kind', 'payment') == 'payment' and not p.get('notForOpenInvoices')]
        cover = coverage_view(split_by_customer(doc)[customer_id], customer_id)['payments']
        used = {'recordIds': [], 'factIds': []}   # a deposit already given for an approved trial credit is not given again for another
        for earlier in self.dg_cases("kind='trial_credit' AND dataset='live' AND status='decided'"):
            d = earlier.get('decision') or {}
            if earlier.get('customerId') == customer_id and d.get('outcome') == 'approve' and not d.get('overridden'):
                for src in (earlier.get('evaluation') or {}).get('evidence', {}).get('depositSources', []):
                    if src.get('counted'):
                        used['recordIds' if src.get('recordId') else 'factIds'].append(src.get('recordId') or src.get('factId'))
        # A receipt that is (or could be) a deposit also reduces the replay's debt (oldest-first matching, e.g. against an opening balance), but a deposit pays for its
        # order, not for what was owed: the debts a customer total reads are taken without those receipts, so a deposit is never counted twice. For a new trial credit
        # that is every receipt that could be its deposit (unallocated, inside the window); for any request, the receipts already given as an approved trial's deposit.
        window = (ev.as_of - timedelta(days=delegation.DEPOSIT_DAYS)).isoformat()

        def debt_without(ids):
            held = {r['id']: r['unallocated'] for r in receipts if r['id'] in ids and r['unallocated'] > 0}
            if not held or f['incomplete']:
                return f['debt_before_m']
            rest = [p if p['id'] not in held else {**p, 'amount': amount_of(self.dg_template(doc), minor(p['amount']) - held[p['id']])} for p in mine['payments']
                    if p['id'] not in held or held[p['id']] < minor(p['amount'])]
            return max(f['debt_before_m'], assessment_facts(mine['invoices'], rest, doc.get('allocations', []), mine['openingBalances'], ev.as_of, invoice_id)['debt_before_m'])
        candidates = {r['id'] for r in receipts if r.get('receivedDate') and window <= r['receivedDate'] <= ev.as_of.isoformat()}
        given = set(used['recordIds'])
        return ({'incomplete': f['incomplete'], 'debtBeforeDeposits': debt_without(candidates | given), 'debtBeforeGivenDeposits': debt_without(given), 'depositsUsed': used, 'incompleteText': incomplete_text(f) if f['incomplete'] else None, 'debt': f['debt_before_m'], 'overdueOther': f['overdue_other_m'],
                 'noDueOther': f['noDueOther'], 'receiptCount': f['prior_receipt_count'], 'lateReceipts': f['lateReceipts'],
                 'lateUnknown': bool(f['unplacedPayments'] or f['noDueDate']), 'invoiceCount': sum(1 for i in mine['invoices'] if active(i)),
                 'priorInvoiceTotals': [minor(i['total']) for i in mine['invoices'] if active(i) and i.get('total') and i['id'] != invoice_id],
                 'receipts': receipts, 'coverageConfirmed': cover['completeTo'] is not None,
                 'linesInForce': self.dg_lines(customer_id, ev), 'trialInForce': len(self.dg_trial_lines(customer_id, ev))}, f)

    def dg_facts(self, customer_id):
        """The facts Staff confirmed for this customer, newest first: {id, kind, createdAt, data, provenance}. Lock held."""
        return [{'id': i, 'kind': k, 'createdAt': at, 'data': json.loads(d)['values'], 'provenance': json.loads(d)['provenance']}
                for i, k, at, d in self.db.execute('SELECT id, kind, created_at, data FROM confirmed_facts WHERE customer_id=? ORDER BY created_at DESC, id', (customer_id,)).fetchall()]

    def dg_cases(self, where='1', args=()):
        return [self.dg_load(row) for row in self.db.execute('SELECT id, kind, subject, status, dataset, created_at, updated_at, data FROM decision_cases WHERE ' + where +
                                                           ' ORDER BY created_at, id', args).fetchall()]

    @staticmethod
    def dg_load(row):
        return {**json.loads(row[7]), 'id': row[0], 'kind': row[1], 'subject': row[2], 'status': row[3], 'dataset': row[4], 'createdAt': row[5], 'updatedAt': row[6]}

    def dg_case(self, case_id):
        found = self.dg_cases('id=?', (case_id,))
        require(found, 404, 'NOT_FOUND', 'Decision case not found.')
        return found[0]

    def dg_put(self, case, new=False):
        """Save a case: its columns and its data. A second live case for the same (kind, subject) is the unique index's 409 CASE_OPEN. Lock and transaction held."""
        case['updatedAt'], case['version'] = now(), case.get('version', 0) + 1
        data = json.dumps({k: v for k, v in case.items() if k not in ('id', 'kind', 'subject', 'status', 'dataset', 'createdAt', 'updatedAt')})
        try:
            if new:
                self.db.execute('INSERT INTO decision_cases (id, kind, subject, status, dataset, created_at, updated_at, data) VALUES (?,?,?,?,?,?,?,?)',
                                (case['id'], case['kind'], case['subject'], case['status'], case['dataset'], case['createdAt'], case['updatedAt'], data))
            else:
                self.db.execute('UPDATE decision_cases SET status=?, updated_at=?, data=? WHERE id=?', (case['status'], case['updatedAt'], data, case['id']))
        except sqlite3.IntegrityError:
            open_case = self.dg_live(case['kind'], case['subject'])
            raise refusal(409, 'CASE_OPEN', 'A decision case for this request is already open.', **({'caseId': open_case['id'], 'caseStatus': open_case['status']} if open_case else {})) from None

    def dg_live(self, kind, subject):
        found = self.dg_cases("kind=? AND subject=? AND status IN ('gathering_evidence', 'awaiting_owner', 'on_hold')", (kind, subject))
        return found[0] if found else None

    def case_event(self, case_id, kind, actor, policy_version, data=None):
        """A row on the case's timeline, in the caller's transaction (see the module-level case_event). Transaction held."""
        case_event(self.db, case_id, kind, actor, policy_version, data)

    def case_viewed(self, actor, case_id):
        """POST api/decision-cases/<id>/viewed: the Owner (a person) has the case in front of them. Writes a case_events row `viewed` (actor owner), at most one per case in
        VIEWED_EVERY_SECONDS so a page that reloads does not flood the timeline; inside that window nothing is written and the answer carries the earlier time
        (recorded: false). It changes no case data. Lock held."""
        self.person_required(actor)
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner views a case as the owner.')
        case = self.dg_case(case_id)
        require(case['dataset'] == 'live', 404, 'NOT_FOUND', 'Decision case not found.')
        last = self.db.execute("SELECT at FROM case_events WHERE case_id=? AND kind='viewed' ORDER BY seq DESC LIMIT 1", (case_id,)).fetchone()
        stamp = now()
        if last and (datetime.fromisoformat(stamp) - datetime.fromisoformat(last[0])).total_seconds() < VIEWED_EVERY_SECONDS:
            return {'caseId': case_id, 'at': last[0], 'recorded': False}
        with self.db:
            case_event(self.db, case_id, 'viewed', 'owner', (case.get('policy') or {}).get('version'), {}, at=stamp)
        return {'caseId': case_id, 'at': stamp, 'recorded': True}

    def case_events_view(self, actor, case_id):
        """GET api/decision-cases/<id>/events: the case's timeline in order (seq), for an Owner person or Staff. Staff do not see the Owner's private signals (feedback,
        tacit agreement, views) and never an Owner's reason, as case_view shows them neither. Lock held."""
        require(actor['role'] in CASE_ROLES, 403, 'FORBIDDEN', 'Only the owner or staff read a case timeline.')
        if actor['role'] == 'owner':
            self.person_required(actor)
        case = self.dg_case(case_id)
        require(case['dataset'] == 'live', 404, 'NOT_FOUND', 'Decision case not found.')
        out = []
        for seq, kind, at, who, version, data in self.db.execute('SELECT seq, kind, at, actor, policy_version, data FROM case_events WHERE case_id=? ORDER BY seq', (case_id,)):
            data = json.loads(data) if data else {}
            if actor['role'] != 'owner':
                if kind in OWNER_ONLY_EVENTS:
                    continue
                data = {k: v for k, v in data.items() if k != 'reason'}
            out.append({'seq': seq, 'kind': kind, 'at': at, 'actor': who, 'policyVersion': version, 'data': data})
        return {'caseId': case_id, 'events': out}

    @staticmethod
    def dg_owner_view(c):
        """What the Owner's judgment of a case is, for comparables and the back-test: their decision, or (a case the agent decided) their feedback.
        'approve', 'decline' or None (not reviewed)."""
        d = c.get('decision') or {}
        if c.get('dataset', 'live') != 'live':
            return c.get('ownerDecision')
        if d.get('by') in ('owner', 'owner_exception'):
            return d.get('outcome')
        last = (c.get('feedback') or [None])[-1]
        if d.get('by') == 'agent' and last:
            agreed = last['verdict'] in ('agree', 'tacit_agree')   # a tacit agreement counts as agreeing, labelled by dg_owner_kind
            if d.get('outcome') == 'decline':   # the agent's own decline (8 Nov 2026): agreeing is a decline, disagreeing an approval
                return 'decline' if agreed else 'approve'
            return 'approve' if agreed else 'decline'
        return None

    @staticmethod
    def dg_owner_kind(c):
        """How the Owner's verdict on a live case was given, for whoever shows it: 'explicit' (the Owner decided it, or gave feedback on the agent's decision), 'tacit' (the
        Owner never answered and the policy's tacit agreement applied: verdictKind 'tacit') or None (not reviewed)."""
        if c.get('dataset', 'live') != 'live' or App.dg_owner_view(c) is None:
            return None
        last = (c.get('feedback') or [None])[-1]
        return 'tacit' if (c.get('decision') or {}).get('by') == 'agent' and last and last['verdict'] == 'tacit_agree' else 'explicit'

    def dg_memory(self, ev, doc):
        """Reviewed cases for retrieval and the back-test: the fictional examples and evaluation cases, and live cases the Owner has reviewed (their
        outcome read from the records now). delegation.comparables reads only examples and live; the back-test only the evaluation set (and live, apart). Lock held."""
        out = []
        for c in self.dg_cases("status='decided'"):
            if not c.get('features'):
                continue
            owner = self.dg_owner_view(c)
            if owner is None:
                continue
            live = c['dataset'] == 'live'
            d = c.get('decision') or {}
            verdict = self.dg_owner_kind(c)
            out.append({'id': c['id'], 'kind': c['kind'], 'dataset': c['dataset'], 'features': c['features'], 'ownerDecision': owner, 'verdictKind': verdict,
                        'ownerReason': None if verdict == 'tacit' else (c.get('feedback') or [{}])[-1].get('reason') if live and d.get('by') == 'agent' else d.get('reason') if live else c.get('ownerReason'),
                        'outcome': self.dg_outcome(c, ev) if live else c.get('outcome'), 'observed': (c.get('outcomeObserved') or {}).get('outcome') if live else None, 'customerId': c.get('customerId'), 'customerName': c.get('customerName'),
                        'summary': c.get('summary') or (c.get('evaluation') or {}).get('reasons', [None])[0]})
        return out

    def dg_outcome(self, c, ev):
        """A live case's outcome, read from the records as they are now (delegation.derive_outcome)."""
        p, d = c['params'], c.get('decision') or {}
        invoices = [{'id': i['id'], 'issueDate': i.get('issueDate'), 'dueDate': ev.current_due(i), 'open': is_open(i)} for i in ev.invoices_for(c['customerId'])]
        return delegation.derive_outcome(c['kind'], {'invoiceId': p.get('invoiceId'), 'approvedDueDate': d.get('approvedDueDate') or p.get('requestedDueDate'),
                                                     'approvedOn': d.get('asOf')}, invoices, ev.as_of)

    def dg_invoice_facts(self, invoice, ev):
        """What outcomes.invoice_outcome reads of one invoice: its total, whether the records still show it open, whether its payment records conflict, its current due
        date and the recorded payments allocated to it ([(received date or None, minor units)])."""
        return {'id': invoice['id'], 'reference': invoice.get('reference'), 'issueDate': invoice.get('issueDate'), 'due': ev.current_due(invoice),
                'total': minor(invoice['total']) if invoice.get('total') else None, 'open': is_open(invoice),
                'conflict': (invoice.get('position') or {}).get('status') == 'conflict',
                'payments': [(pay.get('receivedDate'), minor(a['amount'])) for a, pay in allocations_to(ev.fixture, invoice)]}

    def dg_observe(self, c, ev, as_of, current):
        """{outcome, basis} for an approved live case, from the ledger as it is now (outcomes.observe_case). Reads only. Lock held."""
        p, d = c['params'], c.get('decision') or {}
        facts = [self.dg_invoice_facts(i, ev) for i in ev.invoices_for(c['customerId'])]
        return outcomes.observe_case(c['kind'], p, d.get('approvedDueDate') or p.get('requestedDueDate'), d.get('asOf'), facts, as_of, current)

    def dg_patch(self, case_id, key, value):
        """Set one key of a case's data WITHOUT counting a new version: an observation of the world is not a change the Owner has to have seen (feedback names the
        version they saw). Transaction and lock held."""
        data = json.loads(self.db.execute('SELECT data FROM decision_cases WHERE id=?', (case_id,)).fetchone()[0])
        data[key] = value
        self.db.execute('UPDATE decision_cases SET data=? WHERE id=?', (json.dumps(data), case_id))

    def observe_outcomes(self, as_of=None):
        """Store how every live, approved, not overridden decision has turned out, from the ledger as of `as_of` (a date or YYYY-MM-DD; default the ledger's own date).
        A case_events row `outcome_observed` {outcome, asOf, observedAt, policyVersion, basis} is written, and the latest observation kept in the case's
        data.outcomeObserved, ONLY when the outcome differs from the case's last observation, so running it again, or on another day with the same result, writes
        nothing; a later ledger edit appends a new observation and never rewrites an old one. All the changes are one transaction. Returns
        {observed, changed, unchanged, cases, asOf}. Lock held."""
        ev = self.evidence()
        day = ev.as_of if as_of is None else calendar_date(as_of) if isinstance(as_of, str) else as_of
        current, stamp, found, unchanged = day >= ev.as_of, now(), [], 0
        for c in self.dg_cases("dataset='live' AND status='decided'"):
            d = c.get('decision') or {}
            if d.get('outcome') != 'approve' or d.get('overridden'):
                continue
            seen = self.dg_observe(c, ev, day, current)
            if (c.get('outcomeObserved') or {}).get('outcome') == seen['outcome']:
                unchanged += 1
            else:
                found.append((c, {'outcome': seen['outcome'], 'asOf': day.isoformat(), 'observedAt': stamp, 'policyVersion': (c.get('policy') or {}).get('version'), 'basis': seen['basis']}))
        if found:
            with self.db:
                for c, observation in found:
                    self.case_event(c['id'], 'outcome_observed', 'system', observation['policyVersion'], observation)
                    self.dg_patch(c['id'], 'outcomeObserved', observation)
        return {'observed': len(found) + unchanged, 'changed': len(found), 'unchanged': unchanged, 'cases': len(found) + unchanged, 'asOf': day.isoformat()}

    def delegation_observe(self, actor, body):
        """POST api/delegation/observe-outcomes {asOf?}: the Owner (a person) asks for the observations now. Lock held."""
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner observes outcomes.')
        as_of = body.get('asOf')
        if as_of is not None:
            try:
                calendar_date(as_of)
            except ValueError:
                raise APIError(400, 'INVALID_INPUT', 'asOf is a calendar date, YYYY-MM-DD.', 'asOf') from None
        return self.observe_outcomes(as_of)

    def sweep_tacit_consent(self, as_of=None):
        """Record a tacit agreement (D8) on every live case the agent decided that the Owner never answered, once the policy's tacitAgreeAfterDays have passed since
        the decision (`as_of`: a date or YYYY-MM-DD; default the ledger's date). Only while the CURRENT policy sets the number and is not paused; never on an overridden
        case, one with any feedback (explicit, or already tacit) or one decided fewer days ago. Each agreement is a feedback[] entry {verdict: 'tacit_agree', at, reason,
        policyVersion} and a case_events row tacit_agree, in one transaction. Idempotent: a case is agreed once. Returns {agreed: [case ids], skipped: {paused, off,
        tooRecent, hasFeedback, alreadyTacit}, tacitAgreeAfterDays, asOf}. Lock held."""
        policy = self.policy_current()
        days = policy['feedback']['tacitAgreeAfterDays']
        skipped = {'paused': 0, 'off': 0, 'tooRecent': 0, 'hasFeedback': 0, 'alreadyTacit': 0}
        candidates = [c for c in self.dg_cases("dataset='live' AND status='decided'")
                      if (c.get('decision') or {}).get('by') == 'agent' and c['decision'].get('outcome') == 'approve' and not c['decision'].get('overridden')]
        out = {'agreed': [], 'skipped': skipped, 'tacitAgreeAfterDays': days, 'asOf': None}
        if days is None or policy['paused']:
            skipped['off' if days is None else 'paused'] = len(candidates)
            return out
        if not candidates:
            return out
        day = self.today(self.fixture()) if as_of is None else calendar_date(as_of) if isinstance(as_of, str) else as_of
        out['asOf'], stamp = day.isoformat(), now()
        with self.db:
            for c in candidates:
                given = c.get('feedback') or []
                if any(f.get('verdict') == 'tacit_agree' for f in given):
                    skipped['alreadyTacit'] += 1
                elif given:
                    skipped['hasFeedback'] += 1
                elif (day - calendar_date(c['decision']['at'][:10])).days < days:
                    skipped['tooRecent'] += 1
                else:
                    reason = 'No Owner objection within ' + str(days) + ' days (policy setting)'
                    c['feedback'] = [{'verdict': 'tacit_agree', 'at': stamp, 'reason': reason, 'policyVersion': policy['version'], 'afterDays': days}]
                    c['history'] = [*c['history'], {'at': stamp, 'status': 'decided', 'note': 'tacit agreement: ' + reason}]
                    self.dg_put(c)
                    self.case_event(c['id'], 'tacit_agree', 'system', policy['version'], {'verdict': 'tacit_agree', 'afterDays': days, 'decidedAt': c['decision']['at'], 'asOf': out['asOf']})
                    out['agreed'].append(c['id'])
        return out

    def delegation_sweep(self, actor):
        """POST api/delegation/sweep-tacit-consent: the Owner (a person) runs the sweep now. It takes no date: only elapsed time makes an agreement. Lock held."""
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner runs the tacit-agreement sweep.')
        return self.sweep_tacit_consent()

    def dg_in_force(self, c, ev):
        """Whether an approved case's exposure still counts: an extension while its invoice is open; a trial credit line until its due date; never one
        the Owner overrode."""
        d = c.get('decision') or {}
        if c['status'] != 'decided' or d.get('outcome') != 'approve' or d.get('overridden'):
            return False
        if c['kind'] == 'extension':
            invoice = ev.invoice(c['params']['invoiceId'])
            return invoice is not None and is_open(invoice)
        return d['creditLine']['dueDate'] >= ev.as_of.isoformat()

    def dg_trial_lines(self, customer_id, ev):
        """The customer's trial credit cases still in force (approved by the agent or the Owner, not overridden, not past their due date), oldest first."""
        return [c for c in self.dg_cases("kind='trial_credit' AND dataset='live' AND status='decided'") if c.get('customerId') == customer_id and self.dg_in_force(c, ev)]

    def dg_lines(self, customer_id, ev):
        """What the customer's trial credit lines still in force add to their exposure (minor units); records do not hold them."""
        return sum(int(c['decision']['exposure']) for c in self.dg_trial_lines(customer_id, ev))

    def dg_autonomous(self, ev):
        """The exposure of the agent's own approvals of the last 30 days that are still in force (the rolling bound)."""
        since = (ev.as_of - timedelta(days=30)).isoformat()
        return sum(int(c['decision']['exposure']) for c in self.dg_cases("dataset='live' AND status='decided'")
                   if (c.get('decision') or {}).get('by') == 'agent' and c['decision']['asOf'] >= since and self.dg_in_force(c, ev))

    def dg_request(self, kind, ev, doc, c, invoice, params, received=None):
        """(request, ledger) for delegation.evaluate from the resolved customer, invoice and parameters, on the records as they are now. received: the ISO date the
        request came in (a stored case's receivedDate), default today; the days-from-request limit counts from it, so a later re-check gives the same count. Lock held."""
        ledger, f = self.dg_ledger(doc, ev, c['id'], invoice and invoice['id'])
        ledger['researchFeatures'] = research.numeric(f, research.REPLAY_FEATURES)   # the replay's twelve pipeline features as of this request, for research.py only
        if kind == 'trial_credit':
            return {'customerId': c['id'], 'customerName': c['name'], 'orderAmount': params['orderAmount'], 'termsDays': params['termsDays']}, ledger
        due = ev.current_due(invoice)
        facts = extension_facts(ev.as_of, invoice, due, params['requestedDueDate'], [])
        shown = case_amount(facts)
        owed, mark, text = (minor(shown['amount']) if shown['amount'] else None), shown['mark'], shown['amountText']
        if owed is None and f.get('ownOpen') is not None and not f['incomplete'] and not f['ownMissing']:   # the replay's remainder, worked out, as the case page words it
            owed, mark, text = f['ownOpen'], 'workedOut', delegation.money_view(f['ownOpen'], self.dg_template(doc))['text'] + ' (worked out)'
        return {'customerId': c['id'], 'customerName': c['name'], 'invoiceId': invoice['id'], 'invoiceReference': invoice['reference'],
                'originalDueDate': invoice.get('originalDueDate'), 'currentDueDate': due, 'requestedDueDate': params['requestedDueDate'],
                'extensionDays': (calendar_date(params['requestedDueDate']) - calendar_date(due)).days,
                'daysFromRequest': (calendar_date(params['requestedDueDate']) - (calendar_date(received) if received else ev.as_of)).days,
                'daysPastOriginalDue': (calendar_date(params['requestedDueDate']) - calendar_date(invoice['originalDueDate'])).days if invoice.get('originalDueDate') else None, 'amountOwed': owed, 'amountMark': mark, 'amountText': text,
                'daysOverdue': facts['daysOverdue'], 'daysOverdueReason': facts['daysOverdueReason']}, ledger

    def dg_evaluate(self, kind, request, ledger, ev, doc, recommendation, seen):
        memory = self.dg_memory(ev, doc)
        e = delegation.evaluate(self.policy_current(), kind, request, ledger, self.dg_facts(request['customerId']), memory, recommendation,
                                self.dg_template(doc), ev.as_of, seen, self.dg_autonomous(ev), scorer=self.dg_scorer(ledger))
        # How each live Owner verdict was given (explicit, or tacit under the policy's tacit-agreement setting) is reported beside the rules' own figures, which are unchanged:
        # on the live track record (counts of the reviewed live cases in this category) and on each live comparable.
        live = [m for m in memory if m['dataset'] == 'live']
        e['reliability']['live']['verdictKinds'] = {k: sum(1 for m in live if m['kind'] == kind and m['verdictKind'] == k) for k in ('explicit', 'tacit')}
        kinds = {m['id']: m['verdictKind'] for m in live}
        for c in e['comparables']:
            if c['id'] in kinds:
                c['verdictKind'] = kinds[c['id']]
        return e

    # ---- notices (notify.py): what a person is told outside the page they are on

    def notice(self, role, kind, text, case_id=None, link=None):
        """A notice for a role: a row the Home page lists until read, and the webhook when configured. Lock held (a transaction may be open: one INSERT)."""
        n = {'id': uid('notice'), 'role': role, 'kind': kind, 'text': text, 'caseId': case_id, 'link': link, 'createdAt': now()}
        self.db.execute('INSERT INTO notices (id, role, kind, case_id, created_at, read_at, data) VALUES (?,?,?,?,?,?,?)',
                        (n['id'], role, kind, case_id, n['createdAt'], None, json.dumps({'text': text, 'link': link})))
        self.notifier.post(n)
        return n

    def notices_list(self, actor, limit=50):
        """GET api/notices: this role's notices, newest first, with the unread count. Reading runs the sweeps that produce notices (evidence expiry, scheduled changes)."""
        require(actor['role'] in CASE_ROLES, 403, 'FORBIDDEN', 'Only Staff and the owner read notices.')
        self.sweep_schedules()
        self.sweep_evidence()
        rows = self.db.execute('SELECT id, kind, case_id, created_at, read_at, data FROM notices WHERE role=? ORDER BY created_at DESC, id DESC LIMIT ?', (actor['role'], limit)).fetchall()
        unread = self.db.execute('SELECT COUNT(*) FROM notices WHERE role=? AND read_at IS NULL', (actor['role'],)).fetchone()[0]
        return {'notices': [dated({'id': i, 'kind': k, 'caseId': c, 'createdAt': at, 'readAt': r, **json.loads(d)}) for i, k, c, at, r, d in rows], 'unread': unread}

    def notices_read(self, actor, body):
        """POST api/notices/read {ids: [...]} or {all: true}: marks this role's notices read."""
        require(actor['role'] in CASE_ROLES, 403, 'FORBIDDEN', 'Only Staff and the owner read notices.')
        with self.db:
            if body.get('all'):
                self.db.execute('UPDATE notices SET read_at=? WHERE role=? AND read_at IS NULL', (now(), actor['role']))
            else:
                ids = body.get('ids')
                require(isinstance(ids, list) and all(isinstance(x, str) for x in ids) and len(ids) <= 200, 400, 'INVALID_INPUT', 'ids is a list of notice ids.', 'ids')
                for i in ids:
                    self.db.execute('UPDATE notices SET read_at=? WHERE id=? AND role=? AND read_at IS NULL', (now(), i, actor['role']))
        return self.notices_list(actor)

    def sweep_evidence(self, remind_hours=6):
        """Evidence requests about to expire get Staff a reminder; expired ones tell the Owner and Staff the case is stalled. Each once (flags on the case). Lock held."""
        if self.fixture() is None:
            return
        now_dt = datetime.now(timezone.utc)
        with self.db:
            for (action_id,) in self.db.execute("SELECT id FROM actions WHERE kind='evidence' AND status='proposed' ORDER BY created_at, id").fetchall():
                a = self.get_action(action_id)
                case = self.dg_case(a['caseId']) if a.get('caseId') else None
                if not case or case['dataset'] != 'live' or case['status'] != 'gathering_evidence':
                    continue
                left = datetime.fromisoformat(a['expiresAt']) - now_dt
                hours = left.total_seconds() / 3600
                name = case.get('customerName') or 'a customer'
                if hours <= 0 and not case.get('evidenceExpiredNoticed'):
                    self.dg_patch(case['id'], 'evidenceExpiredNoticed', now())
                    self.notice('staff', 'evidence_expired', 'The information request for ' + name + ' expired unanswered; the case is stalled. Ask the assistant again, or tell the Owner.',
                                case['id'], '#/decision-cases/' + case['id'])
                    self.notice('owner', 'evidence_expired', name + ': Staff did not provide the information asked for within 24 hours; the case is stalled.', case['id'], '#/decision-cases/' + case['id'])
                elif 0 < hours <= remind_hours and not case.get('evidenceReminded'):
                    self.dg_patch(case['id'], 'evidenceReminded', now())
                    self.notice('staff', 'evidence_due', 'The information request for ' + name + ' expires in about ' + str(max(1, int(hours))) + ' hour(s): ' + ', '.join(case.get('needs') or []) + '.',
                                case['id'], '#/actions/' + a['id'])

    # ---- scheduled policy changes (the Owner's "from December, lower the limit; in January, put it back")

    def schedules_list(self, actor):
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner reads the scheduled changes.')
        ev = self.evidence()
        return {'schedules': self.meta('policySchedules') or [], 'today': ev.as_of.isoformat() if ev else None}

    def schedule_add(self, actor, body):
        """POST api/delegation/schedules {at, revertAt?, note?, change: {policy sections...}}: the change is validated now against the current policy (merged) and applied on
        its date by sweep_schedules as a new version; with revertAt, the previous values of the same keys come back on that date as another version."""
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner schedules a change.')
        doc = self.fixture()
        require(doc is not None, 409, 'NO_RECORDS', 'Set the currency, decimal places and time zone under Records first.')
        at, revert, note, change = body.get('at'), body.get('revertAt'), body.get('note'), body.get('change')
        for key, value in (('at', at), ('revertAt', revert)):
            if value is not None or key == 'at':
                try:
                    datetime.fromisoformat(value)
                except (TypeError, ValueError):
                    raise refusal(400, 'INVALID_INPUT', key + ' is a date (YYYY-MM-DD).', field=key)
        require(revert is None or revert > at, 400, 'INVALID_INPUT', 'revertAt is after the date of the change.', 'revertAt')
        require(note is None or isinstance(note, str) and len(note.strip()) <= 500, 400, 'INVALID_INPUT', 'The note is text of at most 500 characters.', 'note')
        require(isinstance(change, dict) and change and set(change) <= set(delegation.POLICY_KEYS), 400, 'INVALID_INPUT', 'change names the policy settings to change.', 'change')
        current = self.policy_current()
        delegation.validate_policy(self._merged_rules(current, change), settings_of(doc))   # a bad value is refused now, not on the day
        entry = {'id': uid('sched'), 'at': at, 'revertAt': revert, 'note': (note or '').strip() or None, 'change': change, 'status': 'pending', 'createdAt': now(),
                 'createdBy': {'actorId': actor['id'], 'role': actor['role']}, 'appliedVersion': None}
        with self.db:
            self.set_meta('policySchedules', [*(self.meta('policySchedules') or []), entry])
        return self.schedules_list(actor)

    def schedule_cancel(self, actor, sid):
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner cancels a scheduled change.')
        found = [x for x in (self.meta('policySchedules') or []) if x['id'] == sid]
        require(found, 404, 'NOT_FOUND', 'No such scheduled change.')
        require(found[0]['status'] == 'pending', 409, 'INVALID_TRANSITION', 'This change is ' + found[0]['status'] + '.')
        with self.db:
            self.set_meta('policySchedules', [{**x, 'status': 'cancelled', 'cancelledAt': now()} if x['id'] == sid else x for x in self.meta('policySchedules')])
        return self.schedules_list(actor)

    @staticmethod
    def _merged_rules(current, change):
        rules = {k: current[k] for k in delegation.POLICY_KEYS if k in current}
        for k, v in change.items():
            rules[k] = {**rules.get(k, {}), **v} if isinstance(v, dict) and isinstance(rules.get(k), dict) and k != 'customers' else v
        return rules

    def sweep_schedules(self):
        """Apply every pending scheduled change whose date has come (business date): a new policy version each, by the system, naming the schedule. Lock held."""
        doc = self.fixture()
        if doc is None:
            return
        pending = [x for x in (self.meta('policySchedules') or []) if x['status'] == 'pending']
        if not pending:
            return
        today = self.evidence().as_of.isoformat()
        for entry in sorted(pending, key=lambda x: (x['at'], x['createdAt'])):
            if entry['at'] > today:
                continue
            try:
                current = self.policy_current()
                before = {k: current[k] for k in entry['change'] if k in current}
                rules = delegation.validate_policy(self._merged_rules(current, entry['change']), settings_of(doc))
                with self.db:
                    self.db.execute('INSERT INTO delegation_policies (version, created_at, data) VALUES (?,?,?)',
                                    (current['version'] + 1, now(), json.dumps({**rules, 'createdBy': {'actorId': 'system', 'role': 'system', 'channel': 'schedule', 'scheduleId': entry['id']},
                                                                                'note': 'Scheduled change for ' + entry['at'] + (': ' + entry['note'] if entry.get('note') else ''), 'action': 'schedule'})))
                    items = self.meta('policySchedules')
                    items = [{**x, 'status': 'applied', 'appliedAt': now(), 'appliedVersion': current['version'] + 1} if x['id'] == entry['id'] else x for x in items]
                    if entry.get('revertAt'):
                        items.append({'id': uid('sched'), 'at': entry['revertAt'], 'revertAt': None, 'note': 'Reverts the scheduled change of ' + entry['at'], 'change': before, 'status': 'pending',
                                      'createdAt': now(), 'createdBy': {'actorId': 'system', 'role': 'system'}, 'appliedVersion': None, 'revertsSchedule': entry['id']})
                    self.set_meta('policySchedules', items)
                self.notice('owner', 'policy_scheduled', 'The scheduled policy change for ' + entry['at'] + ' was applied as version ' + str(current['version'] + 1) + '.', None, '#/delegation')
            except Exception as e:
                log('scheduled policy change ' + entry['id'] + ' failed: ' + str(e)[:200])
                with self.db:
                    self.set_meta('policySchedules', [{**x, 'status': 'failed', 'error': str(e)[:200]} if x['id'] == entry['id'] else x for x in self.meta('policySchedules')])

    # ---- the Owner's exposure view: every customer, what they owe now, what is overdue, against their limit

    def delegation_exposure(self, actor):
        """GET api/delegation/exposure: per active customer, from the records as they are now: recorded debt, overdue amount and the oldest days past due, trial credit
        lines in force, the exposure (debt plus lines), the limit that applies (the customer's own rule or the policy's) and whether it is exceeded. Owner only."""
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner reads the exposure view.')
        ev, doc = self.evidence(), self.fixture()
        require(doc is not None, 409, 'NO_RECORDS', 'No records yet.')
        policy, template = self.policy_current(), self.dg_template(doc)
        rows = []
        for c in doc.get('customers', []):
            if not active(c):
                continue
            ledger, f = self.dg_ledger(doc, ev, c['id'])
            rule = delegation.customer_rule(policy, c['id'], ev.as_of)
            limit = delegation._m((rule or {}).get('maxExposure') or policy['limits']['maxCustomerExposure'])
            exposure = (f['debt_before_m'] or 0) + (ledger.get('linesInForce') or 0)
            rows.append({'customer': {'id': c['id'], 'name': c['name']}, 'debt': delegation.money_view(f['debt_before_m'], template), 'overdue': delegation.money_view(f['overdue_before_m'] or 0, template),
                         'daysPastDue': f.get('max_days_past_due_before') or 0, 'linesInForce': delegation.money_view(ledger.get('linesInForce') or 0, template),
                         'exposure': delegation.money_view(exposure, template), 'limit': delegation.money_view(limit, template), 'over': exposure > limit, 'incomplete': bool(f['incomplete']),
                         'rule': rule, 'openCases': sum(1 for x in self.dg_cases("dataset='live'") if x.get('customerId') == c['id'] and x['status'] in ('awaiting_owner', 'on_hold', 'gathering_evidence'))})
        rows.sort(key=lambda r: -int(r['exposure']['minorUnits']))
        total = sum(int(r['exposure']['minorUnits']) for r in rows)
        overdue = sum(int(r['overdue']['minorUnits']) for r in rows)
        return dated({'asOf': ev.as_of.isoformat(), 'customers': rows, 'totals': {'exposure': delegation.money_view(total, template), 'overdue': delegation.money_view(overdue, template),
                                                                                  'overLimit': sum(1 for r in rows if r['over']), 'incomplete': sum(1 for r in rows if r['incomplete'])}})

    # ---- research (research.py): model versions, settings, the scorer the ladder is given, the Owner's refit

    def research_settings(self):
        return research.validate_settings(self.meta('researchSettings') or {})

    def research_model_current(self):
        """The model in force: the latest saved version (research_models), else the bootstrap file from the config (version as the file says it), else None."""
        row = self.db.execute('SELECT version, created_at, data FROM research_models ORDER BY version DESC LIMIT 1').fetchone()
        if row:
            m = json.loads(row[2])
            return {**m, 'version': str(row[0]), 'createdAt': row[1], 'source': 'saved'}
        if self.shadow:
            return {**self.shadow, 'source': 'config'}
        return None

    def research_versions(self):
        out = []
        for version, created_at, data in self.db.execute('SELECT version, created_at, data FROM research_models ORDER BY version DESC').fetchall():
            m = json.loads(data)
            out.append({'version': str(version), 'createdAt': created_at, 'name': m.get('name'), 'features': m.get('features'), 'trainedOn': m.get('trainedOn'), 'scoring': m.get('scoring', 'builtin'),
                        'coefficients': dict(zip(m.get('features') or [], m.get('coef') or [])) if m.get('coef') else None, 'intercept': m.get('intercept'), 'createdBy': m.get('createdBy')})
        return out

    def research_cases(self):
        """Decided cases with the Owner's verdict, as research reads them (every dataset, labelled). Lock held."""
        out = []
        for c in self.dg_cases("status='decided'"):
            owner = self.dg_owner_view(c)
            if owner is None:
                continue
            live = c['dataset'] == 'live'
            outcome = (c.get('outcomeObserved') or {}).get('outcome') if live else (c.get('outcome') or {}).get('label')
            out.append({**c, 'ownerDecision': owner, 'policyVersion': (c.get('policy') or {}).get('version'), 'outcome': outcome})
        return out

    def research_agreement(self, cases=None):
        """The model's agreement with the Owner over scored LIVE cases with a verdict (fictional cases never count towards promotion)."""
        cases = self.research_cases() if cases is None else cases
        return research.agreement([c for c in cases if c['dataset'] == 'live'], self.research_settings()['promotion']['threshold'])

    def dg_scorer(self, ledger, model=None, promotion=None):
        """The function delegation.evaluate calls with the ladder's features: scores them with the model in force (with the replay's features from the ledger) and says
        whether, under the Owner's promotion bar, that score is a recommendation. Computed once per evaluation; None when no model is in force."""
        model = self.research_model_current() if model is None else model
        if not model:
            return None
        promotion = promotion or research.promotion_status(self.research_settings(), self.research_agreement(), model)

        def scorer(f):
            features = research.case_features(f, ledger.get('researchFeatures'))
            shadow = self.research_provider.score(model, features)
            return research.as_recommendation(shadow, promotion, model)
        return scorer

    def dg_research(self, e, ledger):
        """What a case keeps for the team's classifier (research.py): its numeric feature row as of the request, the score the model in force gave it (from the
        evaluation's own call), which model version, and whether promotion was active. Stored beside the evaluation."""
        features = research.case_features(e['features'], ledger.get('researchFeatures'))
        m = e.get('model') or {}
        return {'features': features, 'shadow': m.get('shadow'), 'modelVersion': m.get('version'), 'promoted': bool(m.get('promoted')), 'recommendation': m.get('recommendation'),
                'at': now(), 'asOf': e['keyFacts']['asOfDate']}

    def research_refit(self, actor, body=None, auto=False):
        """POST api/delegation/research/refit {features?, name?, note?}: fit a new model version on the training table (the provider does the fitting) and save it, immutable.
        Too few rows, or one class only, is 409 NOT_ENOUGH_DATA. auto: called after an Owner verdict under the autoRefitEvery setting (errors are logged, not raised)."""
        body = dict(body or {})
        if not auto:
            require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner refits the model.')
        rows = research.training_rows(self.research_cases())
        features = body.get('features')
        if features is None:
            features = research.choose_features(rows)
            if not features:   # nothing to choose from (no row yet, or no feature that varies): too little data, not a bad request (NTK, 11 Nov 2026)
                declines = sum(r[research.LABEL] for r in rows)
                raise refusal(409, 'NOT_ENOUGH_DATA', 'There is nothing to fit on yet: the training table has ' + str(len(rows)) + (' usable row' if len(rows) == 1 else ' usable rows') +
                              ' (' + str(declines) + (' decline' if declines == 1 else ' declines') + '). A fit needs requests you decided, or what-if questions you answered, where you '
                              'approved some and declined some, and that differ from each other.', rows=len(rows), positives=declines, features=[])
        require(isinstance(features, list) and features and all(isinstance(k, str) for k in features), 400, 'INVALID_INPUT', 'features is a list of feature names.', 'features')
        unknown = [k for k in features if k not in research.LADDER_FEATURES + research.REPLAY_FEATURES]
        require(not unknown, 400, 'INVALID_INPUT', 'Unknown feature(s): ' + ', '.join(unknown), 'features')
        usable = [r for r in rows if all(r.get(k) is not None for k in features)]
        positives = sum(r[research.LABEL] for r in usable)
        if len(usable) < 2 or positives == 0 or positives == len(usable):
            raise refusal(409, 'NOT_ENOUGH_DATA', 'The training table has ' + str(len(usable)) + ' usable row(s) with ' + str(positives) + ' decline(s): a fit needs rows of both classes.',
                          rows=len(usable), positives=positives, features=features)
        version = (self.db.execute('SELECT MAX(version) FROM research_models').fetchone()[0] or 0) + 1
        try:
            m = self.research_provider.train(usable, features, body.get('name') or 'nucleon-' + self.research_provider.kind, version)
        except Exception as e:
            raise refusal(502, 'MODEL_SERVICE', 'The model could not be fitted: ' + str(e)[:200])
        counts = {}
        for r in usable:
            counts[r['dataset']] = counts.get(r['dataset'], 0) + 1
        m['trainedOn'] = {**(m.get('trainedOn') or {}), 'rows': len(usable), 'positives': positives, 'features': list(features), 'byDataset': counts,
                          'ownerAnswered': sum(1 for c in self.research_cases() if c['dataset'] == 'live'), 'at': now()}
        m['createdBy'] = {'actorId': actor['id'] if actor else 'system', 'role': actor['role'] if actor else 'system', 'auto': auto, 'note': (body.get('note') or None)}
        with self.db:
            self.db.execute('INSERT INTO research_models (version, created_at, data) VALUES (?,?,?)', (version, now(), json.dumps(m)))
        return self.delegation_research(actor or {'role': 'owner'})

    def research_after_verdict(self):
        """After an Owner verdict lands on a case: refit automatically when the setting asks for it (every N verdicts since the model in force was fitted). Never raises."""
        try:
            every = self.research_settings()['autoRefitEvery']
            if not every:
                return
            answered = sum(1 for c in self.research_cases() if c['dataset'] == 'live')
            m = self.research_model_current()
            since = (m or {}).get('trainedOn', {}).get('ownerAnswered', 0) if m and m.get('source') == 'saved' else 0
            if answered - since >= every:
                self.research_refit(None, auto=True)
        except Exception as e:
            log('research: automatic refit skipped: ' + str(e)[:200])

    def save_research_settings(self, actor, body):
        """POST api/delegation/research/settings: the Owner, as a person (caller checked csrf), saves the research settings (research.validate_settings)."""
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner changes the research settings.')
        try:
            settings = research.validate_settings(body or {})
        except ValueError as e:
            raise refusal(400, 'INVALID_INPUT', str(e))
        with self.db:
            self.set_meta('researchSettings', settings)
        return self.delegation_research(actor)

    # ---- views

    def case_view(self, case, role, replayed=False):
        """A case as the assistant, Staff or the Owner reads it (the same shape for assess, resolve and status): the BACKEND's status and handling, a
        statusText the assistant repeats verbatim, key facts, warnings, the three dimensions, comparables (labelled as analogies), the authority it
        was decided under, and what was and was not communicated. The Owner's reasons on comparables and their feedback are the Owner's alone."""
        e = case['evaluation']
        comps = [{k: v for k, v in c.items() if k != 'ownerReason'} for c in e['comparables']] if role != 'owner' else e['comparables']
        d = case.get('decision')
        out = {'caseId': case['id'], 'kind': case['kind'], 'status': case['status'], 'handling': case['handling'], 'dataset': case['dataset'],
               'statusText': delegation.status_text({**case, 'keyFacts': e['keyFacts'], 'authority': case['authority'], 'why': e.get('why'), 'evidenceExpired': self.dg_evidence_expired(case)}), 'why': e.get('why'),
               'exception': e.get('exception'), 'suggested': e.get('suggested'),   # the exception band's verdict on this case, and a decline prepared for the Owner (3 Nov 2026)
               'keyFacts': e['keyFacts'], 'warnings': e['warnings'], 'reasons': e['reasons'], 'evidence': e['evidence'], 'risk': e['risk'], 'reliability': e['reliability'],
               'comparables': comps, 'authority': case['authority'], 'policyChangedSinceAssessment': e['policyChangedSinceAssessment'],
               'recommendation': {**case['recommendation'], 'text': delegation.recommendation_text(case['recommendation'].get('recommendation'))}, 'communication': dict(delegation.COMMUNICATION), 'customer': {'id': case['customerId'], 'name': case['customerName']},
               'requestId': case.get('requestId'), 'actionId': case.get('actionId'), 'evidenceLink': case.get('actionId') and case['status'] == 'gathering_evidence' and not self.dg_evidence_expired(case) and '#/actions/' + case['actionId'],
               'evidenceExpired': self.dg_evidence_expired(case),
               'needs': case.get('needs') or [], 'decision': d, 'version': case['version'], 'createdAt': case['createdAt'], 'updatedAt': case['updatedAt'],
               'outcome': self.dg_outcome(case, self.evidence()) if case['dataset'] == 'live' and d and d.get('outcome') == 'approve' else None,
               'outcomeObserved': case.get('outcomeObserved')}
        if role == 'staff':   # information Staff may add unasked while the Owner has the case (Hoang's round, 6 Nov 2026); None when there is nothing to add
            addable = self.dg_addable(case)
            out['addEvidence'] = {'kinds': [n['label'] for n in addable]} if addable else None
        out['outcomeNow'] = out['outcome'] and {**out['outcome'], 'source': 'current ledger says'}   # the read-time label; outcomeObserved is the stored observation
        if role == 'owner':
            out['feedback'] = case.get('feedback') or []
            out['override'] = case.get('override')
            out['research'] = case.get('research')   # the Owner alone sees the research row and the shadow score; Staff and the assistant never do
        if d and d.get('overridden'):
            out['externalEffects'] = (case.get('override') or {}).get('externalEffects') or delegation.external_effects(case['kind'])
        if replayed:
            out['replayed'] = True
        if case['status'] == 'gathering_evidence' and case['recommendation'].get('recommendation') not in delegation.APPROVING:
            out['note'] = ("Your recommendation '" + str(case['recommendation'].get('recommendation')) + "' is recorded. If your only concern was the missing information, call resolveDecision again "
                           "for this case with recommendation approve_if_verified; nothing is approved until Staff confirm the information.")
        return dated(out)

    def delegation_assess(self, actor, kind, c, invoice, params, recommendation, seen):
        """assessDecision: what would happen now under the current policy, stored nowhere (no case, no action, no request). Lock held."""
        self.sweep_schedules()
        ev, doc = self.evidence(), self.fixture()
        request, ledger = self.dg_request(kind, ev, doc, c, invoice, params)
        e = self.dg_evaluate(kind, request, ledger, ev, doc, recommendation, seen)
        out = {'caseId': None, 'stored': False, 'kind': kind, 'status': 'assessed', 'handling': e['handling'],
               'statusText': delegation.status_text({'kind': kind, 'handling': e['handling'], 'assessedOnly': True, 'authority': e['authority'], 'why': e.get('why')}), 'why': e.get('why'),
               'keyFacts': e['keyFacts'], 'warnings': e['warnings'], 'reasons': e['reasons'], 'evidence': e['evidence'], 'risk': e['risk'], 'reliability': e['reliability'],
               'comparables': [{k: v for k, v in x.items() if k != 'ownerReason'} for x in e['comparables']] if actor['role'] != 'owner' else e['comparables'],
               'authority': e['authority'], 'policyChangedSinceAssessment': e['policyChangedSinceAssessment'], 'recommendation': e['recommendation'],
               'communication': dict(delegation.COMMUNICATION), 'customer': {'id': c['id'], 'name': c['name']}, 'needs': [m['label'] for m in e['staffNeeds']]}
        return dated(out)

    # ---- resolving

    def dg_same(self, case, kind, params):
        p = case['params']
        return p['requestedDueDate'] == params['requestedDueDate'] if kind == 'extension' else (p['orderAmount'], p['termsDays']) == (params['orderAmount'], params['termsDays'])

    def dg_evidence_expired(self, case):
        """A case gathering evidence whose information request lapsed unanswered (ACTION_TTL_HOURS): stalled until Staff ask the assistant again. Lock held."""
        if case.get('status') != 'gathering_evidence' or not case.get('actionId'):
            return False
        try:
            return action_state(self.get_action(case['actionId'])) == 'expired'
        except APIError:
            return False

    def dg_supersede(self, case):
        """Closes a stalled case (its information request expired unanswered) because Staff asked for a different request for the same customer: nothing was
        decided or executed on it, so nothing is undone; the new request is resolved in its place (4 Nov 2026). Lock held."""
        note = 'Superseded: the information request expired unanswered and Staff asked for a different request for this customer.'
        case['status'] = 'closed'
        case['history'] = [*case.get('history', []), {'at': now(), 'status': 'closed', 'note': note}]
        with self.db:
            self.dg_put(case)
            self.case_event(case['id'], 'closed', 'system', (case.get('policy') or {}).get('version'), {'note': note})
            self.notice('owner', 'case_closed', (case.get('customerName') or 'A customer') + ': the stalled request was closed; Staff asked for a different one, which is being resolved.',
                        case['id'], '#/decision-cases/' + case['id'])

    def delegation_existing(self, actor, kind, subject, params, invoice=None, recommendation=None, context=None):
        """A case that already answers this resolve: the live case with the same parameters (the stored case, replayed: true, nothing created); another live
        case for the same invoice or customer is 409 CASE_OPEN naming it; an extension the agent already approved for the same date (or, when asked in
        days, the same days within a day of the approval) returns that decision. None: nothing to replay. Lock held."""
        live = self.dg_live(kind, subject)
        if live:
            if self.dg_same(live, kind, params):
                return self.dg_replay(actor, live, recommendation, context)
            if self.dg_evidence_expired(live):   # stalled: Staff never answered; a different request from them takes its place
                self.dg_supersede(live)
                return None
            raise refusal(409, 'CASE_OPEN', 'There is already an open decision case for this ' + ('invoice' if kind == 'extension' else 'customer') + ' (' + live['id'] + ', ' +
                          live['status'].replace('_', ' ') + '), asked for different terms. It must be settled before another is made. That is the state at the time of this call: '
                          'the Owner decides in Nucleon, outside the chat, so when Staff ask again, call resolveDecision again rather than repeating this message.', caseId=live['id'], caseStatus=live['status'])
        done = self.dg_decided_match(kind, subject, params, invoice)
        if done:
            return self.case_view(done, actor['role'], replayed=True)
        return None

    def dg_decided_match(self, kind, subject, params, invoice=None):
        """The decided live case that already answers this request (read only): a trial credit line in force with these terms; an extension the agent approved (not overridden)
        for the same date or, when asked in days, the same days within a day of the approval. None: no such case. Lock held."""
        if kind == 'trial_credit':   # a line already in force with these terms is that decision again; other terms are judged (they go to the Owner)
            for c in reversed(self.dg_trial_lines(subject, self.evidence())):
                if self.dg_same(c, kind, params):
                    return c
        if kind == 'extension':
            for c in reversed(self.dg_cases("kind='extension' AND subject=? AND status='decided' AND dataset='live'", (subject,))):
                d = c.get('decision') or {}
                if d.get('by') != 'agent' or d.get('overridden'):
                    continue
                recent = datetime.fromisoformat(d['at']) > datetime.now(timezone.utc) - timedelta(hours=24)
                if c['params']['requestedDueDate'] == params['requestedDueDate'] or recent and params.get('days') is not None and c['params'].get('days') == params['days'] \
                        and invoice and self.evidence().current_due(invoice) == c['params']['requestedDueDate']:
                    return c
        return None

    def delegation_handled(self, actor, kind, subject, params, invoice=None):
        """assessDecision: the stored case view (read only, nothing replayed or written) when this very request is already handled: the live case with the same parameters,
        else the decided case delegation_existing would replay. None: assess it as new. Lock held."""
        live = self.dg_live(kind, subject)
        case = live if live and self.dg_same(live, kind, params) else None if live else self.dg_decided_match(kind, subject, params, invoice)
        return case and self.case_view(case, actor['role'])

    def dg_replay(self, actor, case, recommendation=None, context=None):
        """The stored case again. A case still gathering evidence whose action lapsed gets a fresh one (in one transaction), so Staff are never left with a dead link.
        While it is gathering evidence, the same request with another recommendation or reasoning updates the RECORDED recommendation (the history is kept; recommendationUpdated:
        true): that executes nothing, since the evidence is still missing, and the re-evaluation after Staff answer uses the latest one. Once the case is with the Owner
        the recommendation is not changed (a note says so)."""
        note, updated = None, False
        if recommendation and recommendation.get('reasoning') and {k: recommendation.get(k) for k in ('recommendation', 'reasoning')} != {k: case['recommendation'].get(k) for k in ('recommendation', 'reasoning')}:
            if case['status'] == 'gathering_evidence':
                who = {'actorId': actor['id'], 'role': actor['role'], 'channel': 'service' if actor.get('channel') == 'service' else 'person'}
                old = {k: case['recommendation'].get(k) for k in ('recommendation', 'reasoning')}
                history = case.get('recommendationHistory') or [{**old, 'at': case['createdAt'], 'requestedBy': self.dg_requested_by(case)}]
                case['recommendationHistory'] = [*history, {**{k: recommendation[k] for k in ('recommendation', 'reasoning')}, 'at': now(), 'requestedBy': who}]
                case['recommendation'] = {**{k: recommendation[k] for k in ('recommendation', 'reasoning')},
                                          'context': ({'text': context, 'source': 'reported in chat, relayed by the assistant', 'verification': 'none'} if context else case['recommendation'].get('context'))}
                with self.db:
                    self.dg_put(case)
                updated = True
            else:
                note = 'The case is already ' + case['status'].replace('_', ' ') + ', so the recorded recommendation was not changed.'
        if case['status'] == 'gathering_evidence' and self.dg_records_moved(case):   # e.g. Staff recorded the payment in Records: the same ask is judged on the records now
            with self.db:
                self.reapply(case, self.evidence(), self.fixture())
                self.dg_put(case)
        if case['status'] == 'gathering_evidence':
            a = self.get_action(case['actionId']) if case.get('actionId') else None
            if a is None or action_state(a) != 'proposed':
                with self.db:
                    case['actionId'] = self.dg_evidence_action(case, case['evaluation'], case['actor'], by='system')['id']
                    self.dg_put(case)
        out = self.case_view(case, actor['role'], replayed=True)
        return {**out, **({'note': note} if note else {}), **({'recommendationUpdated': True} if updated else {})}

    def dg_records_moved(self, case):
        """Whether a trial-credit case still gathering evidence would now be handled differently (or ask for something else, or verify another deposit) on the records and policy as
        they are: Staff may have recorded the payment in Nucleon Records since it was assessed. Evaluates and stores nothing. Lock held."""
        ev, doc = self.evidence(), self.fixture()
        c = ev.customer(case['customerId'])
        if c is None or case['kind'] != 'trial_credit':
            return False
        request, ledger = self.dg_request(case['kind'], ev, doc, c, None, case['params'], case.get('receivedDate'))
        e = self.dg_evaluate(case['kind'], request, ledger, ev, doc, {k: case['recommendation'][k] for k in ('recommendation', 'reasoning')}, case['policy']['version'])
        old = case['evaluation']
        return (e['handling'], [m['key'] for m in e['staffNeeds']], e['evidence']['verifiedDeposit']) != (old['handling'], [m['key'] for m in old.get('staffNeeds', [])], old['evidence']['verifiedDeposit'])

    def assistant_url_for(self, role):
        """The assistant link this role's pages show: the Owner's own when the config names one (ownerAssistantUrl), else the shared assistantUrl."""
        return (self.owner_assistant_url or self.assistant_url) if role == 'owner' else self.assistant_url

    def one_at_a_time(self, actor, c):
        """The assistant sends one request per Staff message (Hoang, 6 Nov 2026: told to handle one of two, it sent both). The page cannot see the
        conversation, so this is the backstop: a service session (the Lab's, through which the assistant calls) that opened a case for another customer
        less than ONE_AT_A_TIME_SECONDS ago is refused, told to report that one and to send this one only when Staff ask for it in their next message.
        A person's session is never refused, nor the same customer (that is delegation_existing's business). Lock held."""
        if actor.get('channel') != 'service':
            return
        last = self.recent_opens.get(actor['id'])
        if not last or last['customerId'] == c['id']:
            return
        ago = time.monotonic() - last['at']
        if ago >= ONE_AT_A_TIME_SECONDS:
            return
        wait = max(1, int(ONE_AT_A_TIME_SECONDS - ago) + 1)
        raise ToolError('ONE_AT_A_TIME', 'A request for ' + last['customerName'] + ' was sent ' + str(int(ago)) + ' seconds ago from this assistant, so this one for ' + c['name']
                        + ' was not sent: one request per Staff message. Tell Staff that the request for ' + last['customerName']
                        + ' was sent, and send this one only when they ask for it in their next message.', executed=False,
                        extra={'retryAfterSeconds': wait, 'earlierCustomer': last['customerName'], 'notSentFor': c['name']})

    def delegation_resolve(self, actor, via, kind, c, invoice, params, recommendation, context, seen):
        """resolveDecision: the assistant's recommendation and reasoning go in; delegation.evaluate decides, on the CURRENT policy, what takes effect,
        and this applies it in ONE transaction with the case (dg_apply). An identical resolve while a case is live, or after the agent approved the
        same extension, was answered before this (delegation_existing). Lock held."""
        self.sweep_schedules()
        ev, doc = self.evidence(), self.fixture()
        request, ledger = self.dg_request(kind, ev, doc, c, invoice, params)
        e = self.dg_evaluate(kind, request, ledger, ev, doc, recommendation, seen)
        case = {'id': uid('case'), 'kind': kind, 'subject': invoice['id'] if kind == 'extension' else c['id'], 'status': 'awaiting_owner', 'dataset': 'live',
                'createdAt': now(), 'receivedDate': ev.as_of.isoformat(), 'customerId': c['id'], 'customerName': c['name'], 'params': params, 'recommendation': {**recommendation, 'context': context and
                {'text': context, 'source': 'reported in chat, relayed by the assistant', 'verification': 'none'}},
                'actor': {'id': actor['id'], 'role': actor['role'], 'name': actor.get('name'), 'kind': actor.get('kind', 'person'),
                          'channel': 'service' if actor.get('channel') == 'service' else 'person', 'via': via},
                'policy': {'version': e['authority']['version'], 'digest': e['authority']['digest'], 'mode': e['authority']['mode']}, 'authority': e['authority'],
                'history': [], 'feedback': [], 'decision': None, 'version': 0, 'research': self.dg_research(e, ledger)}
        with self.db:
            self.case_event(case['id'], 'created', 'agent', e['authority']['version'], {'kind': kind, 'subject': case['subject'], 'customerId': c['id'],
                                                                                      'via': case['actor']['via'], 'recommendation': recommendation['recommendation']})
            self.dg_apply(case, e, request, ev)
            self.dg_put(case, new=True)
        if actor.get('channel') == 'service':
            self.recent_opens[actor['id']] = {'at': time.monotonic(), 'customerId': c['id'], 'customerName': c['name']}
        return self.case_view(case, actor['role'])

    def dg_apply(self, case, e, request, ev):
        """Carry out the handling delegation.evaluate chose for this case, in the caller's transaction: record the evaluation as it was (frozen), then
        approve (the agent's own decision), ask Staff for evidence (an action), or send it to the Owner (a request for an extension; the case alone for trial credit)."""
        ghost = {k: case['actor'][k] for k in ('id', 'role', 'name')}
        case['evaluation'], case['handling'], case['features'] = e, e['handling'], e['features']
        case['authority'], case['needs'] = e['authority'], [m['label'] for m in e['staffNeeds']]
        case['summary'] = e['reasons'][0]
        if case['kind'] == 'trial_credit':
            ev_ = e['evidence']
            case['trial'] = {'orderAmount': request['orderAmount'], 'verifiedDeposit': ev_['verifiedDeposit'], 'exposure': ev_['exposure'], 'termsDays': request['termsDays']}
        step = {'at': now(), 'handling': e['handling'], 'policyVersion': e['authority']['version']}
        version = e['authority']['version']
        self.case_event(case['id'], 'evaluated', 'system', version, {'handling': e['handling'], 'why': e.get('why')})
        if e['handling'] == 'autonomous_approve':
            if case['kind'] == 'extension':
                case['decision'] = self.dg_approve_extension(case, ghost, ev, request)
            else:
                t = case['trial']
                case['decision'] = {'outcome': 'approve', 'by': 'agent', 'at': now(), 'asOf': ev.as_of.isoformat(), 'exposure': t['exposure'], 'authoritySource': e['authority'],
                                    'decidedBy': AGENT_DECIDER, 'decidedByKind': 'agent', 'requestedBy': self.dg_requested_by(case),
                                    'creditLine': {'exposure': t['exposure'], 'orderAmount': t['orderAmount'], 'verifiedDeposit': t['verifiedDeposit'], 'termsDays': t['termsDays'],
                                                   'approvedOn': ev.as_of.isoformat(), 'dueDate': (ev.as_of + timedelta(days=t['termsDays'])).isoformat()}}
            case['status'] = 'decided'
            self.case_event(case['id'], 'decided', 'agent', version, {'outcome': 'approve', 'by': 'agent', 'asOf': case['decision']['asOf']})
        elif e['handling'] == 'autonomous_decline':
            case['decision'] = self.dg_decline_extension(case, ghost, ev, request)
            case['status'] = 'decided'
            self.case_event(case['id'], 'decided', 'agent', version, {'outcome': 'decline', 'by': 'agent', 'asOf': case['decision']['asOf']})
            self.notice('owner', 'agent_declined', (case.get('customerName') or 'A customer') + ': the agent declined an extension of invoice ' + str(request.get('invoiceReference')) +
                        ' under your decline rules. You can reverse it on the Decide page.', case['id'], '#/decision-cases/' + case['id'])
        elif e['handling'] == 'request_evidence':
            case['actionId'] = self.dg_evidence_action(case, e, ghost)['id']
            case['status'] = 'gathering_evidence'
            self.notice('staff', 'evidence_needed', 'Nucleon needs information from you for ' + (case.get('customerName') or 'a customer') + ': ' + ', '.join(m['label'].lower() for m in e['staffNeeds']) +
                        '. It waits 24 hours.', case['id'], '#/actions/' + case['actionId'])
        else:
            case['status'] = 'on_hold' if e['handling'] == 'policy_hold' else 'awaiting_owner'
            if case['kind'] == 'extension':
                case['requestId'] = self.dg_open_request(case, ghost, ev, e)['id']
            self.case_event(case['id'], 'held' if case['status'] == 'on_hold' else 'escalated', 'system', version, {'handling': e['handling'], 'status': case['status']})
            self.notice('owner', 'needs_decision', (case.get('customerName') or 'A customer') + ' needs your decision' + (' (on hold by policy)' if case['status'] == 'on_hold' else '') + ': ' +
                        (e.get('why') or e['reasons'][0]) + '.', case['id'], '#/review')
        case['history'] = [*case['history'], {**step, 'status': case['status']}]

    def dg_open_request(self, case, ghost, ev, e):
        """The structured request for an extension case (no model, no action): channel 'delegated_agent', built by structured_case from the resolved
        values. Awaiting the Owner, who alone decides it (OWNER_REVIEW_REQUIRED still refuses actWithinAuthority). Lock and transaction held."""
        p, reasoning = case['params'], case['recommendation']['reasoning']
        days = (calendar_date(p['requestedDueDate']) - calendar_date(p['currentDueDate'])).days
        text = ('Payment-extension request for invoice ' + p['invoiceReference'] + ' (' + case['customerName'] + '): requested new due date ' + p['requestedDueDate'] + ' (from ' +
                p['currentDueDate'] + ', ' + days_text(days) + '), resolved by the assistant under the Owner\'s delegation policy (version ' + str(e['authority']['version']) + ').')
        structured = {'actionId': None, 'caseId': case['id'], 'customerId': p['customerId'], 'invoiceId': p['invoiceId'], 'invoiceReference': p['invoiceReference'],
                      'requestedDueDate': p['requestedDueDate'], 'currentDueDate': p['currentDueDate'], 'days': days, 'reason': reasoning}
        r = self.new_request(ghost, {'channel': 'delegated_agent', 'text': text, 'receivedAt': now(), 'structured': structured}, ghost['id'] + ':create:delegation:' + case['id'],
                             {'caseId': case['id'], 'policyVersion': e['authority']['version']}, event={'caseId': case['id']}, customerId=p['customerId'], invoiceId=p['invoiceId'],
                             requestedDueDate=p['requestedDueDate'], requestReason=reasoning,
                             delegation={'caseId': case['id'], 'handling': e['handling'], 'reasons': e['reasons'], 'recommendation': {k: case['recommendation'][k] for k in ('recommendation', 'reasoning')}})
        self.structured_case(r)
        require(r['status'] == 'awaiting_owner', 409, 'RECORDS_CHANGED', 'The records no longer support this request, so nothing was opened. Ask again from the current records.')
        return r

    @staticmethod
    def dg_requested_by(case):
        """The session that asked the assistant's question, kept beside the agent's decision: it is who called, never who decided (the agent decided, under the policy)."""
        a = case['actor']
        return {'actorId': a['id'], 'role': a['role'], 'channel': a['channel']}

    def dg_approve_extension(self, case, ghost, ev, request):
        """The agent's own approval of an extension: the request is opened and decided in this transaction. Its decision is the effective due date's source
        (evidence() reads it like any approval), decisionSource 'delegated_policy', with the policy version and digest it was made under. Lock and transaction held."""
        e = case['evaluation']
        r = self.dg_open_request(case, ghost, ev, e)
        an, current = r['analysis'], ev.version_for(r['invoiceId'])
        asked, due = request['requestedDueDate'], request['currentDueDate']
        authority = {'source': delegation.SOURCE, 'policyVersion': e['authority']['version'], 'policyDigest': e['authority']['digest'], 'mode': e['authority']['mode']}
        reasoning = case['recommendation']['reasoning']
        r['decision'] = {'id': uid('decision'), 'requestId': r['id'], 'requestVersionBefore': r['version'], 'analysisId': an['id'], 'evidenceVersion': current, 'outcome': 'approve',
                         'approvedDueDate': asked, 'reason': "Approved within the owner's delegation policy (version " + str(authority['policyVersion']) + '). ' + ' '.join(reasoning.split()),
                         'approvedExtensionDays': (calendar_date(asked) - calendar_date(due)).days, 'scope': {'kind': 'single_invoice', 'invoiceId': r['invoiceId']},
                         'decidedBy': AGENT_DECIDER, 'decidedByKind': 'agent', 'requestedBy': self.dg_requested_by(case), 'decidedAt': now(), 'decisionSource': 'delegated_policy', 'authority': authority, 'delegationCaseId': case['id'],
                         'aiRecommendation': {k: case['recommendation'][k] for k in ('recommendation', 'reasoning')}, 'basis': None}
        r['suggestionSeen'], r['evidenceSeen'] = None, ev.decision_evidence(r['invoiceId'])
        r['version'] += 1
        r['status'] = r['task']['status'] = 'decided'
        self.event(r, 'decision.committed', r['decision'])
        self.save(r)
        r['responseDraft'] = self.response_draft(r)
        self.complete(r, r['decision'])
        case['requestId'] = r['id']
        return {'outcome': 'approve', 'by': 'agent', 'at': now(), 'asOf': ev.as_of.isoformat(), 'approvedDueDate': asked, 'exposure': request['amountOwed'], 'requestDecisionId': r['decision']['id'],
                'authoritySource': e['authority']}

    def dg_decline_extension(self, case, ghost, ev, request):
        """The agent's own decline of an extension under the Owner's decline rules (policy.autoDecline, 8 Nov 2026): the request is opened and decided (declined) in this
        transaction, decisionSource 'delegated_policy'. Nothing changes on the invoice: its due date stays. The Owner can reverse it (case_feedback with override). Lock and transaction held."""
        e = case['evaluation']
        r = self.dg_open_request(case, ghost, ev, e)
        an, current = r['analysis'], ev.version_for(r['invoiceId'])
        authority = {'source': delegation.SOURCE, 'policyVersion': e['authority']['version'], 'policyDigest': e['authority']['digest'], 'mode': e['authority']['mode']}
        lines = ' '.join(c['sentence'] for c in e.get('declineLines') or [])
        r['decision'] = {'id': uid('decision'), 'requestId': r['id'], 'requestVersionBefore': r['version'], 'analysisId': an['id'], 'evidenceVersion': current, 'outcome': 'decline',
                         'approvedDueDate': None, 'reason': "Declined under the owner's decline rules (policy version " + str(authority['policyVersion']) + '). ' + lines + ' ' +
                         ' '.join(case['recommendation']['reasoning'].split()), 'approvedExtensionDays': None, 'scope': {'kind': 'single_invoice', 'invoiceId': r['invoiceId']},
                         'decidedBy': AGENT_DECIDER, 'decidedByKind': 'agent', 'requestedBy': self.dg_requested_by(case), 'decidedAt': now(), 'decisionSource': 'delegated_policy',
                         'authority': authority, 'delegationCaseId': case['id'], 'aiRecommendation': {k: case['recommendation'][k] for k in ('recommendation', 'reasoning')}, 'basis': None}
        r['suggestionSeen'], r['evidenceSeen'] = None, ev.decision_evidence(r['invoiceId'])
        r['version'] += 1
        r['status'] = r['task']['status'] = 'decided'
        self.event(r, 'decision.committed', r['decision'])
        self.save(r)
        r['responseDraft'] = self.response_draft(r)
        self.complete(r, r['decision'])
        case['requestId'] = r['id']
        return {'outcome': 'decline', 'by': 'agent', 'at': now(), 'asOf': ev.as_of.isoformat(), 'approvedDueDate': None, 'exposure': request['amountOwed'],
                'requestDecisionId': r['decision']['id'], 'authoritySource': e['authority'], 'declineLines': e.get('declineLines') or []}

    def dg_evidence_action(self, case, e, ghost, by='system'):
        """A new evidence action for the case (kind 'evidence', id act_<16 hex>), listing what Staff can provide. Its invoice_id column holds the CASE id, so the
        one_live_action index allows one live evidence action per case; an earlier one is expired or superseded in the same transaction. Lock and transaction held."""
        made = datetime.now(timezone.utc)
        action_id = uid('act')
        self.supersede_actions('evidence', case['id'], 'staff', action_id)
        needs = list(e['staffNeeds'])
        action = {'id': action_id, 'kind': 'evidence', 'status': 'proposed', 'invoiceId': case['id'], 'createdAt': made.isoformat(), 'version': ACTION_VERSION, 'caseId': case['id'],
                  'needs': needs, 'preparedBy': {'role': ghost['role'], 'actorId': ghost['id']}, 'preparedAt': made.isoformat(), 'expiresAt': (made + timedelta(hours=ACTION_TTL_HOURS)).isoformat(),
                  'history': [{'at': made.isoformat(), 'status': 'proposed', 'role': ghost['role']}]}
        self.add_action(action)
        self.case_event(case['id'], 'evidence_requested', by, (case.get('policy') or {}).get('version'), {'actionId': action_id, 'needs': [n.get('kind') for n in needs]})
        return action

    def evidence_action_view(self, actor, a):
        """GET api/actions/<id> for an evidence action: what Staff are asked to confirm, with the case it belongs to. Confirming facts is not approving credit."""
        case = self.dg_case(a['caseId'])
        t = self.dg_template()
        needs = [{**n, **({'atLeastText': delegation.money_view(n['atLeast'], t)['text']} if n.get('atLeast') is not None else {})} for n in a['needs']]
        return dated({'id': a['id'], 'kind': 'evidence', 'status': action_state(a), 'version': a['version'], 'createdAt': a['createdAt'], 'expiresAt': a['expiresAt'], 'caseId': a['caseId'],
                      'needs': needs, 'statement': 'You are confirming facts, not approving credit. Nucleon decides what happens next under the Owner\'s delegation policy.',
                      'customer': {'id': case['customerId'], 'name': case['customerName']}, 'keyFacts': case['evaluation']['keyFacts'], 'submitted': a.get('submitted'),
                      'outcome': a.get('outcome'), 'case': self.case_view(case, actor['role']), 'communication': dict(delegation.COMMUNICATION)})

    # ---- evidence from Staff

    def dg_items(self, items, allowed, settings, as_of, record_only=()):
        """The evidence items of a POST, validated per kind and returned as the values to keep. A kind not asked for (and not no_prior_account), a repeated kind or
        an unknown field is 400. deposit {amount, receivedDate, reference?, basis: bank | document | customer_statement} (how Staff know it: the money seen in the
        bank account or payment system, a receipt or remittance document seen, or only the customer's word, which is kept but never counts; a deposit is refused
        when the need says the payment must be recorded in Nucleon Records); business_identity {registration, tradingName, basis: registry | document, registeredSince? (a day; shown to the Owner, read by no rule)};
        trade_reference {referee, summary}; no_prior_account {confirmed: true}. `allowed` is the set of kinds asked for; `record_only` the kinds that may only be recorded in Records."""
        require(isinstance(items, list) and 1 <= len(items) <= 4, 400, 'INVALID_INPUT', 'Send the facts you are confirming as items.', 'items')
        fields = {'deposit': ('amount', 'receivedDate', 'reference', 'basis'), 'business_identity': ('registration', 'tradingName', 'basis', 'registeredSince'), 'trade_reference': ('referee', 'summary'),
                  'no_prior_account': ('confirmed',)}
        out, seen = [], set()
        for item in items:
            require(isinstance(item, dict) and item.get('kind') in delegation.EVIDENCE_KINDS, 400, 'INVALID_INPUT', 'Each item names its kind: ' + ', '.join(delegation.EVIDENCE_KINDS) + '.', 'items')
            kind = item['kind']
            require(kind in allowed and kind not in seen, 400, 'INVALID_INPUT', 'This page asked for ' + ', '.join(sorted(allowed)) + ', each once.', 'items')
            seen.add(kind)
            require(set(item) <= {'kind', *fields[kind]}, 400, 'INVALID_INPUT', 'Unknown field for ' + kind + '.', 'items')
            require(kind not in record_only, 400, 'RECORD_PAYMENT', 'A deposit Staff only checked is not accepted for this request. Record the payment in Nucleon Records, then ask the assistant to resolve the request again.', 'items')
            if kind == 'deposit':
                require(item.get('basis') in delegation.DEPOSIT_BASES, 400, 'INVALID_INPUT', 'Say how you know the deposit arrived: seen in the bank account, seen on a receipt or document, or only what the customer said.', 'deposit.basis')
                amount = parse_money(item.get('amount'), settings, 'amount')
                require(minor(amount) > 0, 400, 'INVALID_AMOUNT', 'The deposit must be more than zero.', 'amount')
                received = parse_day(item.get('receivedDate'), 'receivedDate')
                require(received <= as_of.isoformat(), 400, 'INVALID_DATE', "A deposit can't be dated after the as-of date.", 'receivedDate')
                ref = item.get('reference')
                out.append((kind, {'amount': minor(amount), 'receivedDate': received, 'basis': item['basis'],
                                   'reference': text_value(ref, 'reference', 60, 'the deposit reference') if ref not in (None, '') else None}))
            elif kind == 'business_identity':
                require(item.get('basis') in delegation.IDENTITY_BASES, 400, 'INVALID_INPUT', 'Say how you know the business identity: seen in a registry lookup, or on a document.', 'business_identity.basis')
                values = {'registration': text_value(item.get('registration'), 'registration', 60, 'the business registration'),
                          'tradingName': text_value(item.get('tradingName'), 'tradingName', 120, 'the trading name'), 'basis': item['basis']}
                if item.get('registeredSince') not in (None, ''):   # optional, information for the Owner only: no rule reads it (delegation.business_background)
                    since = parse_day(item.get('registeredSince'), 'business_identity.registeredSince')
                    require(since <= as_of.isoformat(), 400, 'INVALID_DATE', "The registration date can't be after the as-of date.", 'business_identity.registeredSince')
                    values['registeredSince'] = since
                out.append((kind, values))
            elif kind == 'trade_reference':
                out.append((kind, {'referee': text_value(item.get('referee'), 'referee', 120, 'who gave the reference'),
                                   'summary': text_value(item.get('summary'), 'summary', 500, 'what they said')}))
            else:
                require(item.get('confirmed') is True, 400, 'INVALID_INPUT', 'Confirm there is no earlier account with confirmed: true.', 'confirmed')
                out.append((kind, {'confirmed': True}))
        return out

    @staticmethod
    def dg_verification(kind, values):
        """How a confirmed fact is known, in words, as the case keeps it with the item: a deposit by its level (never 'verified' like a recorded payment), an identity by what
        Staff saw. Always confirmed by a staff person on a Nucleon page, never a ledger payment."""
        if kind == 'deposit':
            level = delegation.deposit_level(values)
            return 'confirmed by a staff person on a Nucleon page: ' + delegation.LEVEL_WORDS[level] + ('' if level == 'staff_assertion' else '; not a ledger payment')
        if kind == 'business_identity':
            return 'confirmed by a staff person on a Nucleon page: ' + delegation.IDENTITY_WORDS[values['basis']]
        return 'confirmed by a staff person on a Nucleon page'

    def submit_evidence(self, actor, action_id, body, key):
        """POST api/actions/<id>/evidence {version, items}: a Staff PERSON confirms facts for an evidence action (the caller has checked person_required and csrf).
        In ONE transaction: each fact is kept with its provenance (role, actor id, channel 'person', action id, time), the action is executed, and the case is
        evaluated again under the CURRENT policy with the recommendation the assistant gave when it was opened: it may now be approved by the agent, go to the
        Owner, be put on hold (a fact that contradicts the records), or ask for what is still missing. A replay returns the stored result. Lock held."""
        require(actor['role'] == 'staff', 403, 'FORBIDDEN', 'Only staff confirm facts for an evidence request.')
        self.action_key(key)
        a = self.get_action(action_id)
        require(a['kind'] == 'evidence', 409, 'WRONG_ACTION_KIND', 'This action is not an evidence request.')
        case = self.dg_case(a['caseId'])
        if a['status'] == 'executed':
            return {'action': self.evidence_action_view(actor, a), 'case': self.case_view(case, actor['role']), 'replayed': True}
        require(a['status'] == 'proposed', 409, 'ACTION_NOT_LIVE', 'This request is no longer open (' + action_state(a) + ').')
        if action_state(a) == 'expired':
            with self.db:
                self.move_action(a, 'expired', actor['role'], outcome={'code': 'EXPIRED', 'message': 'It was not answered in time.'})
            raise refusal(409, 'ACTION_EXPIRED', 'This request expired before it was answered. Ask the assistant to resolve the request again.', action=self.evidence_action_view(actor, a))
        require(type(body.get('version')) is int and body['version'] == a['version'], 409, 'STALE_ACTION_VIEW', 'This is not the version you were shown. Reload it.')
        ev, doc = self.evidence(), self.fixture()
        items = self.dg_items(body.get('items'), {n['kind'] for n in a['needs']} | {'no_prior_account'}, settings_of(doc), ev.as_of, {n['kind'] for n in a['needs'] if n.get('recordPayment')})
        with self.db:
            provenance = {'role': actor['role'], 'actorId': actor['id'], 'channel': 'person', 'actionId': a['id'], 'caseId': case['id'], 'at': now()}
            made = []
            for kind, values in items:
                fact_id = uid('fact')
                self.db.execute('INSERT INTO confirmed_facts (id, customer_id, kind, created_at, data) VALUES (?,?,?,?,?)',
                                (fact_id, case['customerId'], kind, provenance['at'], json.dumps({'values': values, 'provenance': provenance})))
                made.append({'id': fact_id, 'kind': kind})
            case['evidenceItems'] = [*case.get('evidenceItems', []), *[{**m, 'verification': self.dg_verification(m['kind'], v), 'provenance': provenance} for m, (_, v) in zip(made, items)]]
            self.move_action(a, 'executed', actor['role'], submitted={'at': provenance['at'], 'by': actor['id'], 'facts': made},
                             outcome={'code': 'SUBMITTED', 'message': 'The facts were recorded and the case evaluated again.'})
            self.case_event(case['id'], 'evidence_submitted', 'staff', case['policy']['version'], {'actionId': a['id'], 'kinds': [m['kind'] for m in made], 'by': actor['id']})
            self.reapply(case, ev, doc)   # after the action is settled: a new evidence action for what is still missing supersedes nothing live
            self.dg_put(case)
        return {'action': self.evidence_action_view(actor, a), 'case': self.case_view(case, actor['role'])}

    def reapply(self, case, ev, doc):
        """Evaluate a case again on the CURRENT policy and records (after Staff's evidence), reusing the assistant's recommendation recorded when it was opened,
        and carry out the new handling. A case whose request no longer fits the records is closed. Lock and transaction held."""
        c = ev.customer(case['customerId'])
        p, invoice = case['params'], case['kind'] == 'extension' and ev.invoice(case['params']['invoiceId']) or None
        if c is None or case['kind'] == 'extension' and (invoice is None or self.action_problem(ev, invoice, p['requestedDueDate'])):
            case['status'], case['handling'] = 'closed', 'owner_review'
            case['history'] = [*case['history'], {'at': now(), 'status': 'closed', 'note': 'The records no longer support this request.'}]
            self.case_event(case['id'], 'closed', 'system', case['policy']['version'], {'note': 'The records no longer support this request.'})
            return
        request, ledger = self.dg_request(case['kind'], ev, doc, c, invoice, p, case.get('receivedDate'))
        e = self.dg_evaluate(case['kind'], request, ledger, ev, doc, {k: case['recommendation'][k] for k in ('recommendation', 'reasoning')}, case['policy']['version'])
        case['policy'] = {'version': e['authority']['version'], 'digest': e['authority']['digest'], 'mode': e['authority']['mode']}
        self.dg_apply(case, e, request, ev)

    # ---- information Staff add unasked (6 Nov 2026)

    GENERIC_NEEDS = {
        'deposit': {'kind': 'deposit', 'fields': ['amount', 'receivedDate', 'reference', 'basis'], 'recordPayment': False,
                    'how': 'Confirm a deposit you have seen yourself: its amount, the date received and its reference, and how you know: in the bank account, or on a receipt or remittance document. '
                           'It counts only up to the limit the Owner set for deposits Staff check; a larger one must be recorded in Nucleon Records.'},
        'business_identity': {'kind': 'business_identity', 'fields': ['registration', 'tradingName', 'basis'],
                              'how': 'Confirm the business registration and trading name, and say whether you saw them in a registry lookup or on a document.'}}

    def dg_addable(self, case):
        """What Staff may add to a live trial-credit case that waits for the Owner (awaiting_owner or on_hold) without being asked: the evidence the frozen
        evaluation found missing (its own need, with how to give it), else a deposit or a business identity the evaluation did not verify (GENERIC_NEEDS). Nothing
        for an extension (a payment goes into Records, and the assistant is asked again), nothing once decided, and nothing while a case is gathering evidence
        (that request is the way). A list of needs in the staffNeeds shape; empty when there is nothing to add. Lock held."""
        if case['dataset'] != 'live' or case['kind'] != 'trial_credit' or case['status'] not in ('awaiting_owner', 'on_hold'):
            return []
        evidence = (case.get('evaluation') or {}).get('evidence') or {}
        needs = [{'key': m['key'], 'label': m['label'], 'detail': m['detail'], **m['need']} for m in evidence.get('missing') or []]
        have = {n['kind'] for n in needs}
        for item in evidence.get('items') or []:
            if item['key'] in self.GENERIC_NEEDS and item['key'] not in have and item['status'] not in ('verified', 'not_required'):
                needs.append({'key': item['key'], 'label': item['label'], 'detail': item['detail'], **self.GENERIC_NEEDS[item['key']]})
        return needs

    def evidence_request(self, actor, case_id):
        """POST api/decision-cases/<id>/evidence-request: Staff (a person) offer information Nucleon did not ask for, on a trial-credit case the Owner has (a deposit
        that arrived after the request, the business registration): an evidence action for it, the same form and the same path as one Nucleon asks for
        (submit_evidence: the facts are kept and the case is evaluated again on the current policy). An action still open for the case is returned as it is.
        Nothing is decided here. Lock held."""
        self.person_required(actor)
        require(actor['role'] == 'staff', 403, 'FORBIDDEN', 'Only staff add information to a case.')
        case = self.dg_case(case_id)
        require(case['dataset'] == 'live', 404, 'NOT_FOUND', 'Decision case not found.')
        needs = self.dg_addable(case)
        require(needs, 409, 'NOTHING_TO_ADD', 'There is nothing Staff can add to this case here' + (
            ': a payment on an extension goes into Nucleon Records, then ask the assistant again.' if case['kind'] == 'extension' else
            ' while it is ' + case['status'].replace('_', ' ') + '.' if case['status'] not in ('awaiting_owner', 'on_hold') else ': the evaluation verified what it needs.'))
        for (action_id,) in self.db.execute("SELECT id FROM actions WHERE kind='evidence' AND invoice_id=? AND status='proposed'", (case['id'],)).fetchall():
            a = self.get_action(action_id)
            if action_state(a) != 'expired':
                return {'actionId': a['id'], 'link': '#/actions/' + a['id'], 'needs': [n['label'] for n in a['needs']], 'replayed': True, 'case': self.case_view(case, 'staff')}
        ghost = {'id': actor['id'], 'role': actor['role'], 'name': actor.get('name')}
        with self.db:
            a = self.dg_evidence_action(case, {'staffNeeds': needs}, ghost, by='staff')
            case['actionId'] = a['id']
            self.dg_put(case)
        return {'actionId': a['id'], 'link': '#/actions/' + a['id'], 'needs': [n['label'] for n in needs], 'case': self.case_view(case, 'staff')}

    # ---- the Owner's side

    def decide_case(self, actor, case_id, body):
        """POST api/decision-cases/<id>/decide {outcome, reason, version}: the Owner (a person) decides a trial-credit case awaiting them or on hold. An
        extension is decided through its request (App.decide), which updates its case. On hold: an owner exception. agreement: whether the Owner's
        outcome is the assistant's recommendation. Lock held."""
        self.person_required(actor)
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner decides a delegation case.')
        case = self.dg_case(case_id)
        require(case['kind'] == 'trial_credit', 409, 'USE_REQUEST_DECISION', 'An extension is decided through its request (POST api/requests/<id>/decisions).')
        outcome, reason = body.get('outcome'), body.get('reason')
        require(outcome in ('approve', 'decline'), 400, 'INVALID_OUTCOME', 'Choose approve or decline.', 'outcome')
        require(isinstance(reason, str) and 1 <= len(reason.strip()) <= 2000, 400, 'INVALID_REASON', 'Enter a brief reason for this decision.', 'reason')
        d = case.get('decision')
        if case['status'] == 'decided' and d and d.get('by') in ('owner', 'owner_exception'):
            require(d['outcome'] == outcome, 409, 'ALREADY_DECIDED', 'The owner already decided this case.')
            return self.case_view(case, 'owner', replayed=True)
        require(case['status'] in ('awaiting_owner', 'on_hold'), 409, 'INVALID_TRANSITION', 'This case is not waiting for the owner (' + case['status'].replace('_', ' ') + ').')
        require(type(body.get('version')) is int and body['version'] == case['version'], 409, 'STALE_CASE', 'The case changed. Reload it before deciding.')
        ev = self.evidence()
        t, changed = dict(case['trial']), {}
        terms = body.get('terms')   # a counter-offer: approve with shorter terms or a smaller credit line than asked (never more)
        if terms is not None:
            require(outcome == 'approve' and isinstance(terms, dict) and set(terms) <= {'termsDays', 'exposure'}, 400, 'INVALID_INPUT', 'terms (approve only) has termsDays and/or exposure.', 'terms')
            if terms.get('termsDays') is not None:
                require(type(terms['termsDays']) is int and 1 <= terms['termsDays'] <= t['termsDays'], 400, 'INVALID_INPUT', 'termsDays is a whole number from 1 to the ' + str(t['termsDays']) + ' days asked.', 'terms.termsDays')
                if terms['termsDays'] != t['termsDays']:
                    changed['termsDays'] = {'from': t['termsDays'], 'to': terms['termsDays']}
                    t['termsDays'] = terms['termsDays']
            if terms.get('exposure') is not None:
                amount = delegation._money(terms['exposure'], settings_of(self.fixture()), 'terms.exposure', 'The credit line')
                units = int(amount['minorUnits'])
                require(0 < units <= t['exposure'], 400, 'INVALID_INPUT', 'exposure is more than zero and at most the ' + delegation.money_view(t['exposure'], self.dg_template(self.fixture()))['text'] + ' asked.', 'terms.exposure')
                if units != t['exposure']:
                    changed['exposure'] = {'from': t['exposure'], 'to': units}
                    t['exposure'] = units
        by = 'owner_exception' if case['status'] == 'on_hold' else 'owner'
        case['decision'] = {'outcome': outcome, 'by': by, 'at': now(), 'asOf': ev.as_of.isoformat(), 'reason': reason.strip(), 'decidedBy': actor['id'], **trail(actor),
                            'authoritySource': {'source': 'owner'}, 'agreement': delegation.agrees(outcome, case['recommendation']['recommendation']), 'exposure': t['exposure'],
                            **({'creditLine': {'exposure': t['exposure'], 'orderAmount': t['orderAmount'], 'verifiedDeposit': t['verifiedDeposit'], 'termsDays': t['termsDays'],
                                               'approvedOn': ev.as_of.isoformat(), 'dueDate': (ev.as_of + timedelta(days=t['termsDays'])).isoformat()}} if outcome == 'approve' else {})}
        if changed:
            case['decision']['changedTerms'] = changed   # approved, but not as asked: the card and the timeline say so
        case['status'] = 'decided'
        case['history'] = [*case['history'], {'at': now(), 'status': 'decided', 'note': 'decided by the owner: ' + outcome + (' with changed terms' if changed else '')}]
        with self.db:
            self.dg_put(case)
            self.notice('staff', 'decided', (case.get('customerName') or 'A customer') + ': ' + ('approved' if outcome == 'approve' else 'declined') + ' by the owner' +
                        (' with changed terms' if changed else '') + '. ' + reason.strip(), case['id'], '#/decision-cases/' + case['id'])
            self.case_event(case['id'], 'decided', 'owner', case['policy']['version'], {'outcome': outcome, 'by': by, 'reason': case['decision']['reason'], 'agreement': case['decision']['agreement']})
        self.research_after_verdict()
        return self.case_view(case, 'owner')

    def dg_request_decided(self, r, actor):
        """App.decide hook: the Owner decided the request of a delegation case, so the case is decided too, in the same transaction. Lock and transaction held."""
        link = r.get('delegation')
        if not link:
            return
        case = self.dg_case(link['caseId'])
        d, owed = r['decision'], (case['evaluation']['keyFacts'].get('amountOwed') or {}).get('minorUnits')
        case['decision'] = {'outcome': d['outcome'], 'by': 'owner_exception' if case['status'] == 'on_hold' else 'owner', 'at': d['decidedAt'], 'asOf': self.evidence().as_of.isoformat(),
                            'approvedDueDate': d.get('approvedDueDate'), 'reason': d['reason'], 'decidedBy': actor['id'], **trail(actor), 'authoritySource': {'source': 'owner'},
                            'agreement': delegation.agrees(d['outcome'], case['recommendation']['recommendation']), 'requestDecisionId': d['id'],
                            'exposure': int(owed) if owed else None}
        case['status'] = 'decided'
        case['history'] = [*case['history'], {'at': now(), 'status': 'decided', 'note': 'decided by the owner: ' + d['outcome']}]
        self.dg_put(case)
        self.case_event(case['id'], 'decided', 'owner', case['policy']['version'], {'outcome': d['outcome'], 'by': case['decision']['by'], 'reason': d['reason'],
                                                                                  'agreement': case['decision']['agreement'], 'requestId': r['id']})
        self.notice('staff', 'decided', (case.get('customerName') or 'A customer') + ': extension ' + ('approved' if d['outcome'] == 'approve' else 'declined') + ' by the owner' +
                    ((' to ' + d['approvedDueDate']) if d.get('approvedDueDate') else '') + '. ' + (d.get('reason') or ''), case['id'], '#/decision-cases/' + case['id'])

    def dg_request_withdrawn(self, r, reason):
        """The request of an open delegation case was withdrawn: the case is closed, so the invoice can be asked about again. Lock and transaction held."""
        link = r.get('delegation')
        if link:
            case = self.dg_case(link['caseId'])
            if case['status'] in LIVE_CASE:
                case['status'] = 'closed'
                case['history'] = [*case['history'], {'at': now(), 'status': 'closed', 'note': 'the request was withdrawn: ' + reason}]
                self.dg_put(case)
                self.case_event(case['id'], 'closed', 'system', case['policy']['version'], {'note': 'the request was withdrawn', 'reason': reason})

    def case_feedback(self, actor, case_id, body, key=None):
        """POST api/decision-cases/<id>/feedback {verdict: agree | disagree, reason, version, override?}: the Owner (a person) judges a decided case, naming the case
        `version` they were shown (another is 409 STALE_CASE and nothing changes). override (only with disagree, only for the agent's own approval): an agent-approved
        extension's decision is replaced by the Owner's decline (decisionSource 'owner_override'; the earlier decision is kept in decisionHistory; event
        decision.overridden), so evidence() puts the due date back; a trial credit line is revoked. The Owner's own approval can be taken back the same way
        (a wrong click): it is not counted as an override of the agent (stats, the advisory suggestion), only the agent's are. The override decision records the policy version it replaces
        (overridesPolicyVersion) and the Owner's actor provenance (person, channel), and the result says what it does NOT undo (externalEffects: Nucleon sent nothing;
        anything Staff already told the customer or did outside Nucleon is not reversed). With an Idempotency-Key the first result is stored with the write, in the
        same transaction, and a retry (a double click, a lost response, a restart) returns it as replayed: one feedback entry, one override. Lock held."""
        self.person_required(actor)
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner gives feedback on a decision.')
        case = self.dg_case(case_id)
        op = 'feedback-' + case_id
        if key is not None:
            done = self.desk_done(actor, op, key, body)
            if done:
                return {**done, 'replayed': True}
        verdict, reason, override = body.get('verdict'), body.get('reason'), body.get('override', False)
        require(verdict in ('agree', 'disagree'), 400, 'INVALID_INPUT', 'Choose agree or disagree.', 'verdict')
        require(isinstance(reason, str) and 1 <= len(reason.strip()) <= 2000, 400, 'INVALID_REASON', 'Enter a brief reason.', 'reason')
        require(type(override) is bool and not (override and verdict != 'disagree'), 400, 'INVALID_INPUT', 'An override goes with disagree.', 'override')
        require(type(body.get('version')) is int, 400, 'INVALID_INPUT', 'Name the case version you were shown (version).', 'version')
        require(body['version'] == case['version'], 409, 'STALE_CASE', 'The case changed since you loaded it. Reload it before giving feedback.')
        d = case.get('decision')
        require(case['status'] == 'decided' and d, 409, 'INVALID_TRANSITION', 'Only a decided case can be given feedback; decide it first.')
        agent_approval = d.get('by') == 'agent' and d.get('outcome') == 'approve'
        own_approval = d.get('by') in ('owner', 'owner_exception') and d.get('outcome') == 'approve'   # the Owner takes back their own approval (a wrong click, 6 Nov 2026)
        agent_decline = d.get('by') == 'agent' and d.get('outcome') == 'decline'   # the agent's own decline (8 Nov 2026): an override approves the date asked for
        require(not override or (agent_approval or own_approval or agent_decline) and not d.get('overridden'), 409, 'INVALID_TRANSITION',
                'Only a decision not yet overridden can be overridden: an approval (the agent\'s own, or yours) or the agent\'s own decline.')
        if override and agent_decline:
            invoice, asked = self.evidence().invoice(case['params']['invoiceId']), case['params']['requestedDueDate']
            problem = invoice is None and ('RECORDS_CHANGED', 'The invoice is no longer in the records.', {}) or self.action_problem(self.evidence(), invoice, asked)
            require(problem is None, 409, problem and problem[0] or 'INVALID_TRANSITION', (problem[1] if problem else '') + ' So the decline cannot be reversed to the date asked for; '
                    'ask Staff to send a new request.')
        who = {'actorId': actor['id'], 'role': actor['role'], 'channel': 'person', **trail(actor)}
        entry = {'verdict': verdict, 'reason': reason.strip(), 'override': override, 'at': now(), 'by': actor['id'], **trail(actor), 'channel': 'person'}
        with self.db:
            if override:
                replaced = (d.get('authoritySource') or {}).get('version')   # the policy version of the decision this replaces
                effects = delegation.external_effects(case['kind'])
                if case['kind'] == 'extension':
                    r = self.get(case['requestId'])
                    earlier = r['decision']
                    r['decisionHistory'] = [*r.get('decisionHistory', []), earlier]
                    asked = case['params']['requestedDueDate'] if agent_decline else None
                    r['decision'] = {'id': uid('decision'), 'requestId': r['id'], 'requestVersionBefore': r['version'], 'analysisId': earlier['analysisId'], 'evidenceVersion': earlier['evidenceVersion'],
                                     'outcome': 'approve' if agent_decline else 'decline', 'approvedDueDate': asked, 'reason': reason.strip(),
                                     'approvedExtensionDays': (calendar_date(asked) - calendar_date(case['params']['currentDueDate'])).days if asked else None, 'scope': earlier['scope'], 'decidedBy': actor['id'],
                                     **trail(actor), 'decidedAt': entry['at'], 'decisionSource': 'owner_override', 'overrides': earlier['id'], 'overridesPolicyVersion': replaced,
                                     'overriddenBy': who, 'delegationCaseId': case['id'], 'basis': None}
                    r['version'] += 1
                    r['evidenceSeen'] = self.evidence().decision_evidence(r['invoiceId'])
                    self.event(r, 'decision.overridden', {'decision': r['decision'], 'overrides': earlier['id'], 'overridesPolicyVersion': replaced, 'by': actor['id'], **trail(actor), 'channel': 'person'})
                    r['responseDraft'] = self.response_draft(r)
                    self.complete(r, r['decision'])
                    case['override'] = {'decisionId': r['decision']['id'], 'overrides': earlier['id']}
                else:
                    case['override'] = {'decisionId': None, 'overrides': d.get('requestDecisionId')}
                case['override'] = {**case['override'], 'decisionSource': 'owner_override', 'outcome': 'approve' if agent_decline else 'decline' if case['kind'] == 'extension' else 'revoked', 'overridesPolicyVersion': replaced,
                                    'by': who, 'at': entry['at'], 'reason': reason.strip(), 'externalEffects': effects}
                case['decision'] = {**d, 'overridden': True, 'overriddenAt': entry['at'], 'overriddenBy': actor['id'], 'overridesPolicyVersion': replaced}
            case['feedback'] = [*case.get('feedback', []), entry]
            case['history'] = [*case['history'], {'at': entry['at'], 'status': 'decided', 'note': 'owner feedback: ' + verdict + (' (override)' if override else '')}]
            self.dg_put(case)
            self.case_event(case['id'], 'feedback', 'owner', case['policy']['version'], {'verdict': verdict, 'override': override, 'reason': entry['reason']})
            if override:
                self.case_event(case['id'], 'override', 'owner', case['policy']['version'], {'outcome': case['override']['outcome'], 'overridesPolicyVersion': case['override']['overridesPolicyVersion'],
                                                                                           'reason': entry['reason']})
            if override:
                if agent_decline:
                    self.notice('staff', 'overridden', (case.get('customerName') or 'A customer') + ': the owner reversed the agent\'s decline (' + entry['reason'] + '). Invoice ' +
                                str(case['params'].get('invoiceReference')) + ' is now due ' + display_date(case['params']['requestedDueDate']) + '.', case['id'], '#/decision-cases/' + case['id'])
                else:
                    self.notice('staff', 'overridden', (case.get('customerName') or 'A customer') + (': the owner overrode the agent\'s approval (' if agent_approval else ': the owner withdrew their approval (') + entry['reason'] + '). ' +
                                ('The due date goes back.' if case['kind'] == 'extension' else 'The credit line is revoked.'), case['id'], '#/decision-cases/' + case['id'])
            out = self.case_view(case, 'owner')
            if key is not None:
                self.db.execute('INSERT INTO record_ops (key, payload_hash, result, at) VALUES (?,?,?,?)', (actor['id'] + ':desk-' + op + ':' + key, fingerprint(body), json.dumps(out), now()))
        self.research_after_verdict()
        return out

    # ---- policy presets (4 Nov 2026): a preset is saved as a new policy version, named in the note, so it can be gone back from like any other
    PRESETS = {
        'demo': {'label': 'Fits the fictional records', 'description': 'Reasonable limits for the fictional customers: small amounts decided by the agent, larger ones and every first credit go to the Owner, no deposit asked; a little over a money limit (10% or AUD 50) is still approved.',
                 'policy': {'mode': 'delegated', 'paused': False,
                            'limits': {'maxDecisionExposure': '1000.00', 'maxCustomerExposure': '1500.00', 'maxAutonomousExposure30d': '5000.00'},
                            'extensions': {'enabled': True, 'maxDays': 30, 'requireNothingElseOverdue': True, 'maxPriorLateShare': '0.25'},
                            'newCustomers': {'trialCredit': 'limited', 'maxExposure': '600.00', 'minDepositShare': '0', 'maxTermsDays': 30, 'tradeReferenceAbove': '1000.00', 'staffCheckedDepositUpTo': '600.00', 'requireIdentity': True},
                            'evidence': {'confirmedCoverageAbove': None}, 'restrictions': {'holdCustomers': [], 'unusualSizeMultiple': 3},
                            'trackRecord': {'minReviewedCases': 5, 'minAgreement': '0.8'},
                            'smallOverage': {'enabled': True, 'maxShare': '0.1', 'maxAmount': '50.00', 'rule': 'either'}}},
        'open': {'label': 'Wide open for trying things', 'description': 'Every bound as high as it goes, nothing held, no deposit: the agent decides almost everything itself. For testers playing with the assistant, not for real money.',
                 'policy': {'mode': 'delegated', 'paused': False,
                            'limits': {'maxDecisionExposure': '10000000.00', 'maxCustomerExposure': '10000000.00', 'maxAutonomousExposure30d': None},
                            'extensions': {'enabled': True, 'maxDays': 365, 'requireNothingElseOverdue': False, 'maxPriorLateShare': '1'},
                            'newCustomers': {'trialCredit': 'limited', 'maxExposure': '10000000.00', 'minDepositShare': '0', 'maxTermsDays': 365, 'tradeReferenceAbove': None, 'staffCheckedDepositUpTo': None, 'requireIdentity': False},
                            'evidence': {'confirmedCoverageAbove': None}, 'restrictions': {'holdCustomers': [], 'unusualSizeMultiple': None},
                            'trackRecord': {'minReviewedCases': 1, 'minAgreement': '0'}}},
    }

    def policy_presets(self, actor):
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner reads the presets.')
        return {'presets': [{'name': k, 'label': v['label'], 'description': v['description']} for k, v in self.PRESETS.items()]}

    def apply_preset(self, actor, name, body):
        """POST api/delegation/presets/<name> {expectedVersion}: saves the preset as a NEW policy version through save_policy (the same checks, the same
        history), with a note that names it. Nothing is edited in place and the earlier versions stay. Owner person only. Lock held."""
        require(name in self.PRESETS, 404, 'NOT_FOUND', 'No such preset.')
        preset = self.PRESETS[name]
        return self.save_policy(actor, {**preset['policy'], 'expectedVersion': (body or {}).get('expectedVersion'), 'note': 'Preset: ' + preset['label']})

    # ---- Staff practice (4 Nov 2026): the assistant previews every Staff request, stores nothing and sends nothing to the Owner
    def staff_practice(self):
        return self.meta('staffPractice') or {'on': False, 'by': None, 'at': None}

    def set_staff_practice(self, actor, body):
        """POST api/staff/practice {on}: a Staff person switches practice on or off for the workspace (one switch: the testers share the seat). Lock held."""
        self.person_required(actor)
        require(actor['role'] == 'staff', 403, 'FORBIDDEN', 'Only staff switch practice mode.')
        on = (body or {}).get('on')
        require(isinstance(on, bool), 400, 'INVALID_INPUT', 'on is true or false.', 'on')
        with self.db:
            self.set_meta('staffPractice', {'on': on, 'by': actor['id'], 'at': now()})
        return self.staff_practice()

    # ---- Quick setup (11 Nov 2026; docs/superpowers/specs/2026-11-11-quick-setup-design.md): the Owner's first setup in a few questions, with a preview on
    # their own open invoices. Both read only; saving is the ordinary PUT api/delegation/policy.
    QUICK_PREVIEW_LIMIT, QUICK_EXAMPLES = 200, 3

    def quick_open_invoices(self, ev):
        """(customer, invoice) for every open invoice with an original due date, customers in the records' order."""
        return [(c, i) for c in ev.customers for i in ev.invoices_for(c['id']) if i.get('originalDueDate') and is_open(i)]

    def quick_setup(self, actor):
        """GET api/delegation/quick-setup: the current policy, the answers that describe it, the customers and two amounts from the open invoices (the median
        and the largest) to offer as choices. Owner only. Lock held."""
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner sets up the delegation policy.')
        doc = self.fixture()
        require(doc is not None, 409, 'NO_RECORDS', 'Set the currency, decimal places and time zone under Records first.')
        from records import money_text_plain
        ev, policy, template = self.evidence(), self.policy_current(), self.dg_template(doc)
        later = (ev.as_of + timedelta(days=1)).isoformat()   # the amount owed as a request would read it (stated, or worked out from the payments)
        owed = sorted(x for x in (self.dg_request('extension', ev, doc, c, i, {'requestedDueDate': later})[0].get('amountOwed') for c, i in self.quick_open_invoices(ev)) if x)
        view = lambda units: {**delegation.money_view(units, template), 'plain': money_text_plain(delegation.money_of(units, template))}
        amounts = {'median': view(owed[len(owed) // 2]), 'largest': view(owed[-1])} if owed else None
        answers = delegation.quick_setup_first_answers(amounts) if policy['version'] == 0 else delegation.quick_setup_answers(policy)
        return {'policy': self.policy_view(actor, policy), 'answers': answers, 'customers': [{'id': c['id'], 'name': c['name']} for c in ev.customers],
                'amounts': amounts, 'openInvoices': len(owed),
                'levels': delegation.quick_setup_levels({'median': owed[len(owed) // 2], 'largest': owed[-1]} if owed else None,
                                                        lambda u: money_text_plain(delegation.money_of(u, template)))}

    def quick_preview(self, candidate, days, ev, doc):
        """What a validated, UNSAVED policy would do if each customer asked today for `days` more days on each open invoice: {total, skipped, truncated, counts
        (agent, owner, held), reasons (with the Quick setup question of each), examples}. Runs delegation.evaluate as a real request would; writes nothing. Used by
        the Quick setup preview and the Doctor. Lock held."""
        current, template = self.policy_current(), self.dg_template(doc)
        policy = {**candidate, 'version': current['version'] + 1, 'digest': delegation.policy_digest(candidate)}
        target = ev.as_of + timedelta(days=days)
        recommendation = {'recommendation': 'approve', 'reasoning': 'Quick setup preview.'}
        memory, autonomous = self.dg_memory(ev, doc), self.dg_autonomous(ev)
        group = {'autonomous_approve': 'agent', 'policy_hold': 'held'}
        counts, reasons, examples = {'agent': 0, 'owner': 0, 'held': 0}, {}, {'agent': [], 'owner': [], 'held': []}
        total = skipped = 0
        truncated = False
        for c, invoice in self.quick_open_invoices(ev):
            if calendar_date(ev.current_due(invoice)) >= target:
                skipped += 1
                continue
            request, ledger = self.dg_request('extension', ev, doc, c, invoice, {'requestedDueDate': target.isoformat()})
            if not request.get('amountOwed'):
                skipped += 1
                continue
            if total >= self.QUICK_PREVIEW_LIMIT:
                truncated = True
                break
            e = delegation.evaluate(policy, 'extension', request, ledger, self.dg_facts(c['id']), memory, recommendation, template, ev.as_of, None, autonomous, scorer=None)
            total += 1
            g = group.get(e['handling'], 'owner')
            counts[g] += 1
            found = [(k['key'], k['label'], delegation.QUICK_CHECK.get(k['key'])) for k in e['risk']['checks'] if k['status'] in ('fail', 'unknown')]
            if any(f[0] == 'days_past_original_due' for f in found):   # the helper sets both day limits from one answer: name it once
                found = [f for f in found if f[0] != 'extension_days']
            if c['id'] in candidate['restrictions']['holdCustomers']:
                found.insert(0, ('held_customer', 'The customer is on your never-decide list', 'holdCustomers'))
            if g != 'agent' and not found:
                found = [('other', e.get('why') or 'Another rule sends it to you', None)]
            for key, label, question in (found if g != 'agent' else []):
                r = reasons.setdefault(key, {'key': key, 'label': label[0].upper() + label[1:], 'count': 0, 'question': question})
                r['count'] += 1
            if len(examples[g]) < self.QUICK_EXAMPLES:
                examples[g].append({'customer': c['name'], 'invoice': invoice.get('reference'), 'amountText': request.get('amountText'), 'reason': found[0][1] if found and g != 'agent' else None})
        return {'total': total, 'skipped': skipped, 'truncated': truncated, 'counts': counts, 'reasons': sorted(reasons.values(), key=lambda r: -r['count']), 'examples': examples}

    def quick_setup_preview(self, actor, body):
        """POST api/delegation/quick-setup/preview {answers, days?}: what the policy these answers make would do if each customer asked today for `days` more days
        (default 14) on each open invoice: counts (agent, owner, held), the reasons with the question that controls each, and a few examples. It runs
        delegation.evaluate with the UNSAVED policy, as a real request would, and writes nothing. Owner person only. Lock held."""
        self.person_required(actor)
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner sets up the delegation policy.')
        body = body if isinstance(body, dict) else {}
        days = body.get('days', 14)
        require(type(days) is int and 1 <= days <= 365, 400, 'INVALID_INPUT', 'days: a whole number from 1 to 365.', 'days')
        doc = self.fixture()
        require(doc is not None, 409, 'NO_RECORDS', 'Set the currency, decimal places and time zone under Records first.')
        current, template, ev = self.policy_current(), self.dg_template(doc), self.evidence()
        try:
            candidate = delegation.validate_policy(delegation.quick_setup_policy(body.get('answers') or {}, current), settings_of(doc))
        except RecordsError as e:
            raise RecordsError(e.status, e.code, e.message, delegation.QUICK_FIELD.get(e.field, e.field), e.extra)
        out = self.quick_preview(candidate, days, ev, doc)
        names = {c['id']: c['name'] for c in ev.customers}
        return {'policy': candidate, 'summary': delegation.quick_setup_summary(candidate, template, names), 'days': days, **out}

    # ---- the Doctor (11 Nov 2026; docs/superpowers/specs/2026-11-11-doctor-design.md): six questions about how the setup is working, answered by code (doctor.py)
    DOCTOR_WINDOWS = {'30': 30, '90': 90, 'all': None}

    def doctor(self, actor, query):
        """GET api/delegation/doctor[?question=<id>][&days=30|90|all]: without a question, the six questions with their headlines; with one, its answer (headline,
        findings, suggestions as Quick setup answers, notes, facts). Owner only. Reads only. Lock held."""
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner reads the Doctor.')
        question, days = (query.get('question') or [None])[0], (query.get('days') or ['30'])[0]
        require(question is None or question in doctor.LABEL, 400, 'INVALID_INPUT', 'question is one of: ' + ', '.join(q for q, _ in doctor.QUESTIONS) + '.', 'question')
        require(days in self.DOCTOR_WINDOWS, 400, 'INVALID_INPUT', 'days is 30, 90 or all.', 'days')
        doc = self.fixture()
        require(doc is not None, 409, 'NO_RECORDS', 'Set the currency, decimal places and time zone under Records first.')
        ev, policy, settings = self.evidence(), self.policy_current(), settings_of(doc)
        cases = self.dg_cases("dataset='live'")
        events = {}
        for case_id, kind, data in self.db.execute('SELECT case_id, kind, data FROM case_events ORDER BY seq'):
            events.setdefault(case_id, []).append({'kind': kind, 'data': json.loads(data) if data else {}})
        names = {c['id']: c['name'] for c in ev.customers}
        uses_preview = question in (None, 'came', 'rules')   # the list's headlines include the rules question
        current = delegation.validate_policy({k: policy[k] for k in delegation.POLICY_KEYS if k in policy}, settings) if uses_preview else None
        preview = self.quick_preview(current, 14, ev, doc) if uses_preview else None
        window = self.DOCTOR_WINDOWS[days]
        if question is None:
            return {'questions': doctor.headlines(cases, policy, settings, ev.as_of, window, names, events, preview), 'days': days}

        def preview_for(patch):
            try:
                cand = delegation.validate_policy(delegation.quick_setup_policy({**delegation.quick_setup_answers(policy), **patch}, policy), settings)
            except RecordsError:
                return None
            return self.quick_preview(cand, 14, ev, doc)
        return {**doctor.answer(question, cases, policy, settings, ev.as_of, window, names, events, preview, preview_for), 'days': days}

    # ---- the Owner's what-ifs (delegation.next_scenario; 4 Nov 2026)
    def preference_answers(self):
        return self.dg_cases('dataset=?', (delegation.PREFERENCE,))

    def preference_next(self, actor):
        """GET api/delegation/preferences/next: the what-if to ask the Owner now (None when every customer is covered), with the counts. Owner only. Lock held."""
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner answers what-ifs.')
        ev, doc = self.evidence(), self.fixture()
        answers = self.preference_answers()
        scenario = None
        if doc is not None and ev.customers:
            invoices = lambda cid: [{**i, 'open': is_open(i)} for i in ev.invoices_for(cid)]
            scenario = delegation.next_scenario(ev.customers, invoices, ev.current_due, answers, self.policy_current(), self.dg_template(doc), ev.as_of)
        recent = [{'id': a['id'], 'summary': a.get('summary'), 'ownerDecision': a.get('ownerDecision'), 'ownerReason': a.get('ownerReason'), 'source': (a.get('preference') or {}).get('source') or 'asked',
                   'decidedOn': a.get('decidedOn')} for a in sorted(answers, key=lambda a: a.get('createdAt') or '', reverse=True)[:10]]
        return {'scenario': scenario, 'answered': len(answers), 'own': sum(1 for a in answers if (a.get('preference') or {}).get('source') == 'own'), 'recent': recent,
                'customers': len(ev.customers) if doc is not None else 0}

    def preference_answer(self, actor, body):
        """POST api/delegation/preferences/answer {customerId, kind, params, outcome, reason?}: stores the Owner's answer as an owner_preference case with the
        features the real ledger gives the what-if today, then returns the next what-if. The params are rebuilt here from the customer, the invoice and the
        numbers, never taken as sent. Owner person only. Lock held."""
        self.person_required(actor)
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner answers what-ifs.')
        body = body or {}
        outcome, kind, given = body.get('outcome'), body.get('kind'), body.get('params') or {}
        require(outcome in ('approve', 'decline'), 400, 'INVALID_INPUT', 'outcome is approve or decline.', 'outcome')
        require(kind in ('trial_credit', 'extension'), 400, 'INVALID_INPUT', 'kind is trial_credit or extension.', 'kind')
        ev, doc = self.evidence(), self.fixture()
        require(doc is not None, 409, 'NO_RECORDS', 'There are no records to ask about yet.')
        c = ev.customer(body.get('customerId'))
        require(c is not None, 404, 'NOT_FOUND', 'Customer not found.', 'customerId')
        reason = (body.get('reason') or '').strip() or None
        own = body.get('source') == 'own'   # 11 Nov 2026 (Hoang): a decision the Owner made on a scenario of their own, typed in, not a what-if Nucleon asked
        if kind == 'trial_credit':
            amount, terms = given.get('orderAmount'), given.get('termsDays')
            if own and isinstance(given.get('orderAmountText'), str):
                amount = minor(parse_money(given.get('orderAmountText'), settings_of(doc), 'params.orderAmountText'))
            require(type(amount) is int and amount > 0 and type(terms) is int and 1 <= terms <= 365, 400, 'INVALID_INPUT', 'params has orderAmount (minor units) and termsDays (1 to 365).', 'params')
            invoice, params = None, {'customerId': c['id'], 'orderAmount': amount, 'termsDays': terms}
        else:
            invoice, days = ev.invoice(given.get('invoiceId')), given.get('days')
            require(invoice is not None and invoice['customerId'] == c['id'], 404, 'NOT_FOUND', 'Invoice not found for this customer.', 'params.invoiceId')
            require(type(days) is int and 1 <= days <= 365, 400, 'INVALID_INPUT', 'params has days (1 to 365).', 'params.days')
            due = ev.current_due(invoice)
            params = {'customerId': c['id'], 'invoiceId': invoice['id'], 'invoiceReference': invoice['reference'], 'currentDueDate': due,
                      'requestedDueDate': (calendar_date(due) + timedelta(days=days)).isoformat(), 'days': days}
        request, ledger = self.dg_request(kind, ev, doc, c, invoice, params)
        e = self.dg_evaluate(kind, request, ledger, ev, doc, {'recommendation': 'approve', 'reasoning': 'A what-if the Owner answered.'}, None)
        template = self.dg_template(doc)
        lead = 'Your own scenario: ' if own else 'What-if: '
        text = (lead + delegation.money_view(params['orderAmount'], template)['text'] + ' on ' + str(params['termsDays']) + '-day terms') if kind == 'trial_credit' else \
               (lead + 'invoice ' + str(params['invoiceReference']) + ' paid ' + str(params['days']) + ' days after its due date')
        case = {'id': uid('pref'), 'kind': kind, 'status': 'decided', 'dataset': delegation.PREFERENCE, 'createdAt': now(), 'customerId': c['id'], 'customerName': c['name'],
                'fictional': False, 'summary': text + ' for ' + c['name'], 'features': e['features'], 'params': params, 'ownerDecision': outcome, 'ownerReason': reason,
                'outcome': None, 'decidedOn': ev.as_of.isoformat(), 'policy': {'version': e['authority']['version']}, 'handling': e['handling'],
                'research': self.dg_research(e, ledger), 'preference': {'answeredBy': actor['id'], 'at': now(), 'source': 'own' if own else 'asked'}, 'version': 0}
        case['subject'] = case['id']
        with self.db:
            self.dg_put(case, new=True)
        nxt = self.preference_next(actor)
        return {'stored': case['id'], 'ownerDecision': outcome, 'customer': {'id': c['id'], 'name': c['name']}, **nxt}

    def delegation_cases(self, actor, query):
        """GET api/delegation/cases[?dataset=live][&status=...]: the Owner's list, newest first, live cases by default."""
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner reads the delegation cases.')
        self.sweep_schedules()
        self.sweep_evidence()
        current = self.policy_current()
        if current['feedback']['tacitAgreeAfterDays'] is not None and not current['paused']:   # the page is current: elapsed time is recorded when it is read
            self.sweep_tacit_consent()
        dataset = (query.get('dataset') or ['live'])[0]
        require(dataset in delegation.DATASETS, 400, 'INVALID_INPUT', 'dataset is one of ' + ', '.join(delegation.DATASETS) + '.', 'dataset')
        rows = [c for c in self.dg_cases('dataset=?', (dataset,)) if not query.get('status') or c['status'] == query['status'][0]]
        return {'dataset': dataset, 'cases': [self.case_row(c) for c in reversed(rows)]}

    def case_row(self, c):
        d = c.get('decision') or {}
        e = c['evaluation'] if c.get('evaluation') else {}
        return dated({'caseId': c['id'], 'kind': c['kind'], 'status': c['status'], 'handling': c.get('handling'), 'dataset': c['dataset'], 'customer': {'id': c.get('customerId'), 'name': c.get('customerName')},
                      'evidenceExpired': self.dg_evidence_expired(c),
                      'exception': bool((e.get('exception') or {}).get('applied')), 'suggested': e.get('suggested'),
                      'requestId': c.get('requestId'), 'actionId': c.get('actionId'), 'keyFacts': e.get('keyFacts'), 'policyVersion': (c.get('policy') or {}).get('version'),
                      'decision': d and {k: d.get(k) for k in ('outcome', 'by', 'at', 'overridden', 'agreement')}, 'feedback': c.get('feedback', []), 'createdAt': c['createdAt'],
                      'override': c.get('override'), 'outcomeObserved': c.get('outcomeObserved'), 'externalEffects': (d.get('overridden') and ((c.get('override') or {}).get('externalEffects') or delegation.external_effects(c['kind']))) or None,
                      'overrideEffects': ('This approves the date asked for (' + display_date(c['params']['requestedDueDate']) + ') and moves the invoice\'s due date. ' + delegation.external_effects(c['kind'])
                                          if d.get('by') == 'agent' and d.get('outcome') == 'decline' and c['kind'] == 'extension' else delegation.external_effects(c['kind'])),
                      'version': c.get('version'), 'statusText': delegation.status_text({**c, 'keyFacts': e.get('keyFacts'), 'authority': c.get('authority'), 'why': e.get('why'), 'evidenceExpired': self.dg_evidence_expired(c)}) if e else None,
                      'recommendation': c.get('recommendation') and {**{k: c['recommendation'].get(k) for k in ('recommendation', 'reasoning')}, 'text': delegation.recommendation_text(c['recommendation'].get('recommendation'))}, 'reasons': e.get('reasons'), 'needs': c.get('needs') or [],
                      'why': e.get('why'), 'comparables': self.comparables_summary(e.get('comparables')), 'reliability': e.get('reliability') and {k: e['reliability'].get(k) for k in ('status', 'sources', 'gatedOn', 'sentence')}})

    STAFF_LIST_DROPPED = ('feedback', 'suggested', 'override', 'outcomeObserved', 'externalEffects', 'overrideEffects', 'comparables', 'reliability')

    def decision_cases_list(self, actor, query):
        """GET api/decision-cases[?status=...]: every live decision case, newest first. The Owner (the Review page's rows, through delegation_cases) or
        Staff, who get the rows without the Owner's private signals: no feedback, prepared decline, override, observed outcome, comparables or
        reliability, and a decision reduced to its outcome, who and when, as case_view and the timeline show them neither. The Requests page lists
        these beside the form requests, so a request sent through the assistant is found where people look for requests (4 Nov 2026)."""
        if actor['role'] == 'owner':
            return self.delegation_cases(actor, query)
        require(actor['role'] in CASE_ROLES, 403, 'FORBIDDEN', 'Only the owner or staff read the decision cases.')
        rows = [c for c in self.dg_cases("dataset='live'") if not query.get('status') or c['status'] == query['status'][0]]
        out = []
        for c in reversed(rows):
            r = {k: v for k, v in self.case_row(c).items() if k not in self.STAFF_LIST_DROPPED}
            r['decision'] = r['decision'] and {k: r['decision'].get(k) for k in ('outcome', 'by', 'at')}
            out.append(r)
        return {'dataset': 'live', 'cases': out}

    @staticmethod
    def comparables_summary(comps):
        """The closest reviewed cases in one line for a list row: how many, how many the Owner approved and declined, how many are this customer's own. No reasons, no names."""
        comps = comps or []
        return {'n': len(comps), 'approved': sum(1 for x in comps if x.get('ownerDecision') == 'approve'), 'declined': sum(1 for x in comps if x.get('ownerDecision') == 'decline'),
                'sameCustomer': sum(1 for x in comps if x.get('sameCustomer'))}

    def delegation_suggestions(self, actor):
        """GET api/delegation/suggestions: deterministic suggestions from reviewed cases, only ever suggestions (nothing is applied)."""
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner reads policy suggestions.')
        ev, doc = self.evidence(), self.fixture()
        policy = self.policy_current()
        overrides = [{'caseId': c['id'], 'kind': c['kind'], 'customerName': c.get('customerName'), 'policyVersion': (c.get('policy') or {}).get('version'), 'overriddenAt': c['decision'].get('overriddenAt'),
                      'reason': (c.get('override') or {}).get('reason'), 'dataset': 'live'}
                     for c in self.dg_cases("dataset='live' AND status='decided'")
                     if (c.get('decision') or {}).get('by') == 'agent' and c['decision'].get('overridden') and (c.get('policy') or {}).get('version') == policy['version']]
        found = delegation.suggestions(policy, self.dg_memory(ev, doc), self.dg_template(doc), overrides)
        return {'policyVersion': policy['version'], 'suggestions': found,
                'note': 'Suggestions only: nothing changes until you save a new policy version. They read the fictional example cases and live reviewed cases, never the held-out evaluation set.'}

    def delegation_training(self, actor):
        """GET api/delegation/training.csv: the training table for the team's classifier (research.training_rows): every decided case the Owner answered, fictional
        datasets labelled as such, with the features the case kept at request time and Target_Deny. Owner only. A research export, not a report."""
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner exports the training table.')
        return research.csv_text(research.training_rows(self.research_cases()))

    def delegation_research(self, actor):
        """GET api/delegation/research: the model in force (name, version, features, coefficients, what it was trained on), the saved versions, the Owner's settings,
        the promotion bar and whether it is met, the model's agreement with the Owner over scored live cases, the provider, and the counts. Owner only."""
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner reads the research figures.')
        cases = self.research_cases()
        settings = self.research_settings()
        m = self.research_model_current()
        agreement = self.research_agreement(cases)
        live = [c for c in cases if c['dataset'] == 'live']
        model = m and {'name': m.get('name'), 'version': m.get('version'), 'features': m.get('features'), 'positive': m.get('positive'), 'trainedOn': m.get('trainedOn'),
                       'createdAt': m.get('createdAt'), 'source': m.get('source'), 'scoring': m.get('scoring', 'builtin'),
                       'coefficients': dict(zip(m.get('features') or [], m.get('coef') or [])) if m.get('coef') else None, 'intercept': m.get('intercept')}
        rows = research.training_rows(cases)
        by = {}
        for c in live:
            r = c.get('research') or {}
            prob, ver = (r.get('shadow') or {}).get('probability'), r.get('modelVersion')
            if prob is None or not ver:
                continue
            d = by.setdefault(str(ver), {'version': str(ver), 'n': 0, 'agreed': 0})
            d['n'] += 1
            d['agreed'] += 1 if (prob >= settings['promotion']['threshold']) == (c['ownerDecision'] == 'decline') else 0
        cm = {'tp': 0, 'fp': 0, 'tn': 0, 'fn': 0}   # the notebook's confusion matrix (section 17), at the threshold, over scored live cases with the Owner's verdict
        for c in live:
            prob = ((c.get('research') or {}).get('shadow') or {}).get('probability')
            if prob is None:
                continue
            said, was = prob >= settings['promotion']['threshold'], c['ownerDecision'] == 'decline'
            cm['tp' if said and was else 'fp' if said else 'fn' if was else 'tn'] += 1
        cm['precision'] = cm['tp'] / (cm['tp'] + cm['fp']) if cm['tp'] + cm['fp'] else None
        cm['recall'] = cm['tp'] / (cm['tp'] + cm['fn']) if cm['tp'] + cm['fn'] else None
        return {'model': model, 'versions': self.research_versions(), 'settings': settings, 'promotion': research.promotion_status(settings, agreement, m), 'agreement': agreement,
                'agreementByVersion': sorted(by.values(), key=lambda d: int(d['version']) if d['version'].isdigit() else 0), 'confusion': cm,
                'provider': self.research_provider.describe(), 'decided': len(cases), 'live': len(live), 'withFeatures': sum(1 for c in cases if (c.get('research') or {}).get('features')),
                'scored': sum(1 for c in live if ((c.get('research') or {}).get('shadow') or {}).get('probability') is not None),
                'training': {'rows': len(rows), 'positives': sum(r[research.LABEL] for r in rows), 'suggestedFeatures': research.choose_features(rows)}}

    def delegation_stats(self, actor):
        """GET api/delegation/stats: live cases only, with the denominator and since when; the fictional decision memory is excluded and says so."""
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner reads the delegation counts.')
        live = self.dg_cases("dataset='live'")
        decided = [c for c in live if c['status'] == 'decided']
        agent = [c for c in decided if (c.get('decision') or {}).get('by') == 'agent']
        counts = {'autonomous': sum(1 for c in agent if not c['decision'].get('overridden') and c['decision'].get('outcome') != 'decline'),
                  'autonomousDeclined': sum(1 for c in agent if not c['decision'].get('overridden') and c['decision'].get('outcome') == 'decline'), 'gatheringEvidence': sum(1 for c in live if c['status'] == 'gathering_evidence'),
                  'ownerReview': sum(1 for c in live if c['status'] == 'awaiting_owner'), 'onHold': sum(1 for c in live if c['status'] == 'on_hold'),
                  'ownerDecided': sum(1 for c in decided if (c['decision'] or {}).get('by') in ('owner', 'owner_exception')), 'overrides': sum(1 for c in agent if c['decision'].get('overridden')),
                  'closed': sum(1 for c in live if c['status'] == 'closed')}
        fictional = self.count('decision_cases') - len(live)
        policy = self.policy_current()
        memory = self.dg_memory(self.evidence(), self.fixture())
        record = {k: {f: tr[f] for f in ('sources', 'gatedOn', 'gate', 'status', 'sentence')} for k in delegation.KINDS for tr in [delegation.track_record(policy, k, memory)]}
        return {'dataset': 'live', 'denominator': len(live), 'since': live[0]['createdAt'][:10] if live else None, 'counts': counts, 'trackRecord': record,
                'excluded': {'fictional': fictional, 'note': 'The fictional decision memory (' + str(fictional) + ' cases) is not counted here.'},
                'note': 'Counts of live cases since ' + (live[0]['createdAt'][:10] if live else 'the first case') + ': ' + str(len(live)) + ' in all. Workflow counts, not decision quality.'}

    def delegation_impact(self, actor, query):
        """GET api/delegation/impact[?from=YYYY-MM-DD][&to=YYYY-MM-DD][&policyVersion=N]: the impact report over the LIVE cases and their timeline (impact.compute; every number carries
        source and dataset). Owner person only: Staff are 403. No window means all time. Lock held."""
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner reads the impact report.')
        self.person_required(actor)
        return self.impact_report(query)

    def impact_report(self, query):
        """The impact report for a window (the query as parse_qs gives it: from, to, policyVersion); the caller has checked who may read it (the Owner as a person on the
        route, the Owner's read-only tool impactSummary for the Owner's assistant). Reads only. Lock held."""
        window = {}
        for key in ('from', 'to'):
            value = (query.get(key) or [None])[0]
            if value is not None:
                try:
                    require(re.fullmatch(r'\d{4}-\d{2}-\d{2}', value), 400, 'INVALID_INPUT', key + ' is a date such as 2026-10-24.', key)
                    datetime.strptime(value, '%Y-%m-%d')
                except ValueError:
                    raise APIError(400, 'INVALID_INPUT', key + ' is a date such as 2026-10-24.', key)
            window[key] = value
        require(not (window['from'] and window['to']) or window['from'] <= window['to'], 400, 'INVALID_INPUT', 'from is after to.', 'from')
        version = (query.get('policyVersion') or [None])[0]
        require(version is None or re.fullmatch(r'\d{1,6}', version), 400, 'INVALID_INPUT', 'policyVersion is a whole number.', 'policyVersion')
        window['policyVersion'] = None if version is None else int(version)
        events = [{'seq': seq, 'case_id': case_id, 'kind': kind, 'at': at, 'actor': who, 'policy_version': pv, 'data': json.loads(data) if data else {}}
                  for seq, case_id, kind, at, who, pv, data in self.db.execute('SELECT seq, case_id, kind, at, actor, policy_version, data FROM case_events ORDER BY seq')]
        return impact.compute(self.dg_cases("dataset='live'"), events, window)

    def delegation_loop(self, actor):
        """GET api/delegation/loop: how many LIVE cases are at each stage of the loop now (impact.loop_counts; pure, from the cases' own state). Owner person only. Lock held."""
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner reads the loop view.')
        self.person_required(actor)
        evaluated = [{'case_id': row[0], 'kind': 'evaluated'} for row in self.db.execute("SELECT DISTINCT case_id FROM case_events WHERE kind='evaluated'")]
        return impact.loop_counts(self.dg_cases("dataset='live'"), evaluated)

    def ui_events_add(self, actor, body):
        """POST api/ui-events [{page, kind, data?, at?}] (or {events: [...]}): what a person's browser reports about using the pages (D11: page enter/leave, named clicks, how long a
        decision took). A person's session only (a service or the AI Agent is 403 PERSON_REQUIRED), Staff or Owner. Local: one row each in ui_events, never sent anywhere. kind is one of
        UI_EVENT_KINDS and page a route name, else 400 and nothing is stored; `data` is a small flat object (strings of at most 100 characters, numbers, booleans) and `at` a
        recent timestamp (else the server's time). At most UI_BATCH_MAX events are read per call and UI_EVENTS_PER_MINUTE per session per minute are kept: the rest are dropped
        WITHOUT an error (`dropped` says how many). Lock held."""
        self.person_required(actor)
        require(actor['role'] in CASE_ROLES, 403, 'FORBIDDEN', 'Only a case role reports page use.')
        events = body.get('events')
        require(isinstance(events, list), 400, 'INVALID_INPUT', 'Send a list of events.', 'events')
        clock, rows = datetime.now(timezone.utc), []
        for item in events[:UI_BATCH_MAX]:
            require(isinstance(item, dict) and set(item) <= {'page', 'kind', 'data', 'at'}, 400, 'INVALID_INPUT', 'Each event is {page, kind, data?, at?}.', 'events')
            require(item.get('kind') in UI_EVENT_KINDS, 400, 'INVALID_INPUT', 'kind is one of ' + ', '.join(UI_EVENT_KINDS) + '.', 'kind')
            require(isinstance(item.get('page'), str) and re.fullmatch(r'[a-z][a-z0-9-]{0,39}', item['page']), 400, 'INVALID_INPUT', 'page is a route name such as review.', 'page')
            data = item.get('data') or {}
            require(isinstance(data, dict) and len(data) <= 8 and all(isinstance(k, str) and 0 < len(k) <= 40 and (v is None or isinstance(v, (bool, int, float)) or isinstance(v, str) and len(v) <= 100)
                                                                     for k, v in data.items()), 400, 'INVALID_INPUT', 'data is a small flat object.', 'data')
            at = clock
            if item.get('at') is not None:
                try:
                    at = datetime.fromisoformat(str(item['at']).replace('Z', '+00:00'))
                    at = at if at.tzinfo else at.replace(tzinfo=timezone.utc)
                except ValueError:
                    raise APIError(400, 'INVALID_INPUT', 'at is a timestamp.', 'at') from None
                if not clock - timedelta(days=1) <= at <= clock + timedelta(minutes=5):
                    at = clock   # a clock far from the server's is not believed
            rows.append((at.astimezone(timezone.utc).isoformat(), actor['role'], 'person', item['page'], item['kind'], json.dumps(data)))
        mark, key = time.monotonic(), actor.get('csrf') or actor['id']
        seen = [t for t in self.ui_seen.get(key, []) if mark - t < 60]
        room = max(0, UI_EVENTS_PER_MINUTE - len(seen))
        keep = rows[:room]
        self.ui_seen[key] = seen + [mark] * len(keep)
        if len(self.ui_seen) > 500:   # sessions that stopped sending: forget their windows
            self.ui_seen = {k: v for k, v in self.ui_seen.items() if v and mark - v[-1] < 60}
        if keep:
            with self.db:
                self.db.executemany('INSERT INTO ui_events (at, role, channel, page, kind, data) VALUES (?,?,?,?,?,?)', keep)
        return {'accepted': len(keep), 'dropped': len(events) - len(keep)}

    def delegation_ui_summary(self, actor, query):
        """GET api/delegation/ui-summary[?from=YYYY-MM-DD][&to=YYYY-MM-DD]: the page-use events in the window (by the day they happened, UTC), summarised by impact.ui_summary:
        counts per page and the median time on a page, named clicks, and how long decisions took. Owner person only. Lock held."""
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner reads page-use figures.')
        self.person_required(actor)
        window = {}
        for key in ('from', 'to'):
            value = (query.get(key) or [None])[0]
            if value is not None:
                try:
                    require(re.fullmatch(r'\d{4}-\d{2}-\d{2}', value), 400, 'INVALID_INPUT', key + ' is a date such as 2026-10-24.', key)
                    datetime.strptime(value, '%Y-%m-%d')
                except ValueError:
                    raise APIError(400, 'INVALID_INPUT', key + ' is a date such as 2026-10-24.', key) from None
            window[key] = value
        require(not (window['from'] and window['to']) or window['from'] <= window['to'], 400, 'INVALID_INPUT', 'from is after to.', 'from')
        rows = [{'at': at, 'role': role, 'page': page, 'kind': kind, 'data': json.loads(data) if data else {}}
                for at, role, page, kind, data in self.db.execute('SELECT at, role, page, kind, data FROM ui_events ORDER BY seq')]
        return impact.ui_summary(rows, window)

    def actions_open_evidence(self, actor, query):
        """GET api/actions?kind=evidence&status=open: the evidence requests waiting for Staff, read-only, for Staff and the Owner (a person's session) and a service session. Each
        is {id, status, createdAt, expiresAt, caseId, customer, asks, needs, link} for an action still open (proposed and not expired) on a live case; nothing else is listed (other kinds
        and statuses are 400). Lock held."""
        require(actor['role'] in CASE_ROLES, 403, 'FORBIDDEN', 'Only Staff and the owner list evidence requests.')
        kind, status = (query.get('kind') or [None])[0], (query.get('status') or [None])[0]
        require(kind == 'evidence' and status == 'open', 400, 'INVALID_INPUT', 'Only the open evidence requests are listed: ?kind=evidence&status=open.', 'kind')
        out = []
        for (action_id,) in self.db.execute("SELECT id FROM actions WHERE kind='evidence' AND status='proposed' ORDER BY created_at, id").fetchall():
            a = self.get_action(action_id)
            if action_state(a) != 'proposed':
                continue
            case = self.dg_case(a['caseId'])
            if case['dataset'] != 'live' or case['status'] != 'gathering_evidence':
                continue
            needs = [{'kind': n.get('kind'), 'label': n.get('label'), 'detail': n.get('detail')} for n in a['needs']]
            out.append({'id': a['id'], 'kind': 'evidence', 'status': 'open', 'createdAt': a['createdAt'], 'expiresAt': a['expiresAt'], 'caseId': a['caseId'],
                        'customer': {'id': case['customerId'], 'name': case['customerName']}, 'caseKind': case['kind'], 'asks': '; '.join(str(n['label']) for n in needs if n['label']) or 'Confirm the facts the assistant asked for.',
                        'needs': needs, 'link': '#/actions/' + a['id']})
        return {'kind': 'evidence', 'status': 'open', 'actions': out}

    def set_suggestions(self, actor, body):
        """The owner's choice to see advisory suggestions; off by default. Turning it on prepares one for every case already
        waiting; turning it off withdraws theirs. Lock held."""
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner chooses whether to see suggestions.')
        on = body.get('on')
        require(isinstance(on, bool), 400, 'INVALID_INPUT', 'Choose on or off.', 'on')
        if on != bool(self.meta('showSuggestions')):
            # shortcut: turning it on queues one model call per waiting case on the single worker, ahead of new requests; fine for
            # a few waiting cases, batch or prioritise if a business keeps many cases waiting
            with self.db:
                self.set_meta('showSuggestions', on)
                for r in filter(self.suggestable, self.records()):
                    if on:
                        self.schedule_suggest(r, 'suggestions turned on')
                    elif r['analysis']['brief']['suggestionStatus'] != 'off':
                        self.update_suggestion(r, {'suggestion': None, 'status': 'off', 'withheldBecause': []})
            self.settled.notify_all()
        return {'on': on}

    def dataset_id(self):
        """Names this set of records: changes when a reset replaces them, so a client can tell its remembered focus is stale."""
        return (self.meta('lastReset') or {}).get('at') or (self.meta('records') or {}).get('createdAt')

    def tool_registry(self, actor):
        """GET api/tools: the desk tools this role is offered now (tools_for, after the owner's overrides), each with its kind, whether a
        person confirms its effect, what it does (as the model is told) and its JSON schema, for another front end or agent. Lock held."""
        caps = {c['name']: c for c in CAPABILITIES}
        return {'datasetId': self.dataset_id(), 'tools': [{'name': f['name'], 'kind': caps[f['name']]['kind'], 'needsConfirmation': caps[f['name']]['needsConfirmation'],
                           'description': f['description'], 'parameters': f['parameters']}
                          for f in (t['function'] for t in tools_for(actor['role'], self.meta('agentTools')))]}

    def tool_call(self, actor, name, body, key):
        """POST api/tools/<name>: one desk tool run as the desk agent runs it (DeskTools.execute: only the tools on for this role, the
        argument checks, each operation keeping the roles' privacy itself), for another front end or agent. body: {args, message (the
        person's words: prepareDecision and prepareCustomer keep only what they give; openRequest opens the case with them and with
        nothing else, so it needs them; interpretStatement reads only them, not its text argument), current {customerId, requestId} (whom
        and which case "current" names; neither: none)}. A call stands alone, so a customerId may be any the records hold. Returns
        {ok: true, result} with each date also in words (dated), or the tool's refusal {ok: false, error, message}; an unknown tool is 404,
        one this role is not offered now 403. A tool offered to no agent that this role runs with a button (pressedBy: applyImportProposal)
        runs here too.
        An operation runs once per Idempotency-Key: an act or prepare tool always (no key: 400 IDEMPOTENCY_REQUIRED), assessRequest when a
        key is sent (it keeps a new assessment version, though it is a read in kind). The key is scoped to actor, role, tool and key, so the
        AI Agent's owner and staff sessions never share an answer, and it is claimed in record_ops after the role check: pending (this
        boot) -> applied (marked by OpConnection in the very transaction of the first business write) -> done (the answer). A retry gets
        the stored answer with replayed: true beside it; other input under the key 409 KEY_REUSED; 409 OPERATION_IN_PROGRESS while the first
        call still runs (also while a model-calling tool asks the model, CALLS_MODEL, which runs without the lock, or a case opened is
        prepared); 409 OPERATION_RESULT_UNAVAILABLE when it committed but its answer was lost (a crash): never run again. A pending claim
        of another boot was left by a stopped process, with nothing committed, and is reclaimed. A refusal that changed nothing is not
        kept (MODEL_UNAVAILABLE, CASE_PREPARING...): the claim is dropped, so a retry is judged on the records as they are then."""
        require(name in DESK_TOOL_NAMES, 404, 'NOT_FOUND', 'Unknown tool.')
        args, message, current = body.get('args', {}), body.get('message', ''), body.get('current') or {}
        require(isinstance(args, dict), 400, 'INVALID_INPUT', 'args must be a JSON object.', 'args')
        require(isinstance(message, str) and len(message) <= 8000, 400, 'INVALID_INPUT', 'message must be text of at most 8000 characters.', 'message')
        require(isinstance(current, dict) and set(current) <= {'customerId', 'requestId'} and all(isinstance(v, str) for v in current.values()),
                400, 'INVALID_INPUT', 'current may name a customerId and a requestId.', 'current')
        once = TOOL_KINDS[name] in ('act', 'prepare') or name == 'assessRequest' and bool(key)   # assessRequest without a key runs as it always did
        with self.lock:
            require(name in {t['function']['name'] for t in tools_for(actor['role'], self.meta('agentTools'), pressed=True)}, 403, 'FORBIDDEN',
                    'This tool is not available to you.')
            scoped, replay = self.tool_claim(actor, name, body, key) if once else (None, None)
            if replay:
                return replay
            try:
                doc = self.fixture()
                require(doc is not None, 409, 'NO_RECORDS', 'Set the currency, decimal places and time zone under Records first.')
                # "current" is a hint: one that no longer exists (the records were reset) is dropped and said, not refused.
                cid, rid, notes = current.get('customerId'), current.get('requestId'), []
                if cid and not self.evidence().customer(cid):
                    cid = None
                    notes.append('The customer this conversation focused on is no longer in the records.')
                if rid and not self.db.execute('SELECT 1 FROM requests WHERE id=?', (rid,)).fetchone():
                    rid = None
                    notes.append('The case this conversation focused on is no longer in the records.')
                if name == 'openRequest' and not message.strip():   # a case's intake text is the person's message, never the agent's words
                    return self.tool_finish(scoped, {'ok': False, 'error': 'MISSING', 'message': "Send the customer's message as 'message'."})
                tools = DeskTools(self, actor, message, self.today(doc), self.adapter_for(self.agent_mode)[0], self.deadline_seconds, focus_id=cid, request_id=rid,
                                  pressed=True)
                tools.seen = {c['id']: c for c in tools.ev.customers}
                if name not in DeskTools.CALLS_MODEL:
                    with self.armed(scoped):
                        outcome = tools.execute(name, args)
                    return self.tool_result(actor, scoped, key, message, name, outcome, notes)
            except BaseException:
                self.tool_abandon(scoped)
                raise
        try:
            try:
                with self.armed(scoped):
                    outcome = tools.execute(name, args)
            except AdapterError:
                outcome = ToolDispatcher._fail(name, args, ToolError('MODEL_UNAVAILABLE', 'The model could not be reached, so nothing was read. Try again.'))
            with self.lock:
                return self.tool_result(actor, scoped, key, message, name, outcome, notes)
        except BaseException:
            with self.lock:
                self.tool_abandon(scoped)
            raise

    def tool_claim(self, actor, name, body, key):
        """(scoped key, stored answer or None) for a tool operation: the claim in record_ops, or the refusal that says why this key cannot run
        now (tool_call's docstring has the states). The row is committed here, before the tool runs. Lock held."""
        require(isinstance(key, str) and 1 <= len(key) <= 160, 400, 'IDEMPOTENCY_REQUIRED', 'Idempotency-Key is required.')
        scoped, fp = actor['id'] + ':' + actor['role'] + ':tool:' + name + ':' + key, fingerprint(body)
        find = 'SELECT payload_hash, result, state, boot FROM record_ops WHERE key=?'
        row = self.db.execute(find, (scoped,)).fetchone()
        if not row and actor.get('kind') != 'agent':   # an answer kept before the scope had the role; the AI Agent's was never one person's role
            row = self.db.execute(find, (actor['id'] + ':desk-tool:' + name + ':' + key,)).fetchone()
        if not row:
            with self.db:
                self.db.execute('INSERT INTO record_ops (key, payload_hash, result, state, at, boot) VALUES (?,?,?,?,?,?)',
                                (scoped, fp, '', 'pending', now(), self.boot))
            self.running.add(scoped)
            return scoped, None
        require(row[0] == fp, 409, 'KEY_REUSED', 'This key was already used with different input.')
        if row[2] == 'done':
            return scoped, {**json.loads(row[1]), 'replayed': True}
        # applied: committed, and either still running in this process (a case opened is being prepared, a model-calling tool is between its change
        # and its answer) or lost with a process that stopped; pending: running here, or left by a stopped process (which committed nothing)
        if row[2] == 'applied' and scoped not in self.running:
            raise APIError(409, 'OPERATION_RESULT_UNAVAILABLE', 'This operation was applied, but its answer was not kept (the records stopped before it was). '
                           'Check the records with a read tool; do not repeat it with a new key unless the records show it is missing.')
        if row[2] == 'applied' or row[3] == self.boot:
            raise APIError(409, 'OPERATION_IN_PROGRESS', 'This operation is still running. Try again later with the same key.')
        with self.db:   # pending from a stopped process: nothing of it was committed (OpConnection), so it runs now
            self.db.execute('UPDATE record_ops SET boot=?, at=? WHERE key=?', (self.boot, now(), scoped))
        self.running.add(scoped)
        return scoped, None

    @contextlib.contextmanager
    def armed(self, scoped):
        """The operation's key armed for this thread while the tool runs (OpConnection marks it applied with the first write it commits)."""
        me = threading.get_ident()
        if scoped:
            self.db.armed[me] = scoped
        try:
            yield
        finally:
            self.db.armed.pop(me, None)

    def tool_finish(self, scoped, result):
        """Close a claimed operation with its answer; returns it. An answer that is ok, or an operation already applied (it committed, even
        if the tool then refused), is kept (done); a refusal that changed nothing drops the claim, so a retry is judged afresh. A row gone
        meanwhile (the records were reset or restored) is not made again. Lock held."""
        if scoped:
            self.running.discard(scoped)
            row = self.db.execute('SELECT state FROM record_ops WHERE key=?', (scoped,)).fetchone()
            with self.db:
                if row and (result.get('ok') is True or row[0] == 'applied'):
                    self.db.execute("UPDATE record_ops SET state='done', result=? WHERE key=?", (json.dumps(result), scoped))
                elif row:
                    self.db.execute('DELETE FROM record_ops WHERE key=?', (scoped,))
        return result

    def tool_abandon(self, scoped):
        """A tool run that raised: its claim is dropped while nothing committed (pending), so the retry runs; an applied one stays, and the retry
        is told its answer is unavailable. Lock held."""
        if scoped:
            self.running.discard(scoped)
            with self.db:
                self.db.execute("DELETE FROM record_ops WHERE key=? AND state='pending'", (scoped,))

    def tool_result(self, actor, scoped, key, message, name, outcome, notes=()):
        """tool_call's answer from the tool's outcome, closed for its key (tool_finish). openRequest opens the case here, once its run ends (armed, so the case's commit marks the key applied). Lock held."""
        if outcome.ok and name == 'openRequest':
            with self.armed(scoped):
                r = self.create(actor, {'messageText': message}, key)
            self.wait_settled(r['id'], self.wait_seconds())   # the lock is released while the case is prepared; a retry meets OPERATION_IN_PROGRESS
            outcome.result['opened'] = summary(self.get(r['id']), self.records())   # with its ordinal and a likely duplicate flagged
        kept = {k: v for k, v in (outcome.payload or {}).items() if k != 'tool'}   # what a tool hands back beside its result (interpretStatement's reading)
        result = {'ok': True, 'result': dated({**{k: v for k, v in outcome.result.items() if k != 'ok'}, **kept})} if outcome.ok else outcome.result
        if notes:
            target = result['result'] if outcome.ok else result
            target['notes'] = [*target.get('notes', []), *notes]
        return self.tool_finish(scoped, result)

    def agent_tools(self, actor):
        """The owner's table of the desk agent's tools (coordinator.CAPABILITIES), each with whether it is on. Lock held."""
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', "Only the owner manages the agent's tools.")
        return {'tools': agent_tools(self.meta('agentTools'))}

    def set_agent_tool(self, actor, body, key):
        """The owner turns one desk tool on or off, {tool, enabled}, once per idempotency key. It applies from the next message;
        a kind the registry does not implement is never turned on. Returns the table. Lock held."""
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', "Only the owner manages the agent's tools.")
        done = self.desk_done(actor, 'agent-tools', key, body)
        if done:
            return done
        overrides = self.meta('agentTools') or {}
        c = next((x for x in agent_tools(overrides) if x['name'] == body.get('tool')), None)
        require(c is not None, 400, 'INVALID_INPUT', 'Unknown tool.', 'tool')
        require(c['kind'] in IMPLEMENTED_KINDS, 400, 'INVALID_INPUT', 'Tools of this kind are not available in Nucleon.', 'tool')
        require(isinstance(body.get('enabled'), bool), 400, 'INVALID_INPUT', 'Choose on or off.', 'enabled')
        with self.db:
            self.set_meta('agentTools', {**overrides, c['name']: {'enabled': body['enabled']}})
            return self.desk_remember(actor, 'agent-tools', key, body, {'tools': agent_tools(self.meta('agentTools'))})

    def suggestion_counters(self):
        """How the workflow went: each case counted once, on its latest analysis, by whether a suggestion was given, withheld or
        failed; and each decision by how it relates to the suggestion it was shown (suggestionSeen). Workflow counts, not
        decision quality."""
        statuses = [((r.get('analysis') or {}).get('brief') or {}).get('suggestionStatus') for r in self.records()]
        relations = [(r.get('suggestionSeen') or {}).get('relation') for r in self.records()]
        return {'given': statuses.count('given'), 'withheld': statuses.count('withheld'), 'failed': statuses.count('failed'),
                'accepted': relations.count('accepted'), 'changed': relations.count('changed'),
                'declinedAgainst': relations.count('declined_against'), 'note': COUNTERS_NOTE}

    def response_draft(self, r):
        """The draft sentence for the customer that follows the request's decision, written by a template (never sent: deliveryStatus not_sent)."""
        d = r['decision']
        ref = r['analysis']['snapshot']['invoice']['reference']
        # Exact template fields keep the draft faithful to the committed owner outcome and date.
        sentence = ('Your payment extension for invoice ' + ref + ' is approved. The new payment date is ' + long_date(d['approvedDueDate']) + '.') if d['outcome'] == 'approve' else ('Your request to extend payment for invoice ' + ref + ' has been declined. The existing payment terms remain in place.')
        return {'id': uid('draft'), 'requestId': r['id'], 'decisionId': d['id'], 'text': sentence,
                'generation': 'template', 'deliveryStatus': 'not_sent', 'createdAt': now()}

    def finish(self, r):
        r['responseDraft'] = self.response_draft(r)
        with self.db:
            self.complete(r, r['decision'])

    def complete(self, r, d):
        """The request completed with its response draft (finish's write, for a caller that already holds a transaction). Lock and transaction held."""
        r['status'] = 'completed'
        self.trace(r, 'saveResponseDraft', {'decisionId': d['id']}, r['responseDraft'], 'application_template')
        self.save(r)
        self.event(r, 'request.completed', {'decisionId': d['id'], 'deliveryStatus': 'not_sent'})

    # ------------------------------------------------------------ workspace setup

    def setup_state(self):
        ws, doc = self.meta('workspace'), self.fixture()
        state = checklist(ws, doc)
        settings = settings_of(doc) if doc else None
        empty = not self.records() and not (doc and (doc['customers'] or doc['invoices'] or doc['notes']))
        return {'workspace': ws and {k: ws.get(k) for k in ('mode', 'origin', 'createdAt')},
                'settings': settings if settings and settings['currency'] else None, 'sampleLoaded': bool(ws and ws.get('sampleFingerprint')),
                'canLoadSample': bool(ws and ws['mode'] == 'practice' and empty), 'ready': state['ready'], 'checklist': state['items'],
                'notNeeded': state['notNeeded'], 'notYet': state['notYet'], 'asOfDate': doc and self.today(doc).isoformat(),
                'dataMode': doc and doc['dataMode']}

    def require_ready(self):
        ws, doc = self.meta('workspace'), self.fixture()
        require(ws is not None, 409, 'NO_RECORDS', "This workspace isn't set up yet. The owner chooses real or practice under Records.")
        require(doc is not None, 409, 'NO_RECORDS', 'Set the currency, decimal places and time zone under Records first.')
        require(checklist(ws, doc)['ready'], 409, 'NO_RECORDS',
                'Add a customer and an open invoice under Records first, so the agent has something to check the request against.')

    def setup_workspace(self, actor, body):
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner sets up the workspace.')
        require(self.meta('workspace') is None, 409, 'WORKSPACE_EXISTS', 'This database already has a workspace. A different type needs a new database.')
        mode, with_sample = body.get('mode'), body.get('withSample') is True
        require(mode in ('practice', 'real'), 400, 'INVALID_INPUT', 'Choose practice or real.', 'mode')
        require(not (with_sample and mode == 'real'), 400, 'INVALID_INPUT', 'A real workspace never loads the fictional sample.', 'withSample')
        with self.db:
            self.set_meta('workspace', {'mode': mode, 'origin': 'first_run', 'createdAt': now(), 'createdBy': actor['id'],
                                        'sampleFingerprint': None, 'skips': {}})
            if with_sample:
                self.load_sample()
        log('workspace set up by', actor['id'] + ':', mode, '(with the fictional sample)' if with_sample else '(empty)')
        return self.setup_state()

    def save_settings(self, actor, body):
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner changes the workspace settings.')
        ws = self.meta('workspace')
        require(ws is not None, 409, 'NO_WORKSPACE', 'Choose real or practice first.')
        settings, doc = validate_settings(body), self.fixture()
        require(not (doc and doc.get('asOfDate')), 409, 'SAMPLE_SETTINGS', "The sample's settings are fixed. Start empty to use your own.")
        if doc:
            current = settings_of(doc)
            require(not doc['invoices'] or (current['currency'], current['scale']) == (settings['currency'], settings['scale']), 409,
                    'SETTINGS_LOCKED', "Currency and decimal places can't change once invoices are recorded.", 'currency')
            doc.update({'businessTimezone': settings['timezone'], 'currency': settings['currency'], 'scale': settings['scale'],
                        'businessName': settings['businessName']})
        else:
            doc = empty_document(settings, practice=ws['mode'] == 'practice')
        with self.db:
            self.save_doc(doc)
        return self.setup_state()

    def authority_view(self, actor):
        """The owner's authority settings as stored, with the defaults for what was never set, and the limit in words. Lock held."""
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner reads the authority settings.')
        doc = self.fixture()
        require(doc is not None, 409, 'NO_RECORDS', 'Set the currency, decimal places and time zone under Records first.')
        a = authority_of(doc)
        return {**a, 'hardRules': list(a['hardRules']), 'maxOutstandingText': a['maxOutstanding'] and money_text(a['maxOutstanding'])}

    def save_authority(self, actor, body):
        """The owner sets the limits staff may act within (PUT api/setup/authority): the whole object, a key left out taking its default.
        Nothing the agent can call writes it. Lock held."""
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner sets the authority settings.')
        doc = self.fixture()
        require(doc is not None, 409, 'NO_RECORDS', 'Set the currency, decimal places and time zone under Records first.')
        doc['authority'] = validate_authority(body, settings_of(doc))
        with self.db:
            self.save_doc(doc)
        return self.authority_view(actor)

    def load_sample_on_request(self, actor):
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner loads the sample.')
        ws, doc = self.meta('workspace'), self.fixture()
        require(ws is not None, 409, 'NO_WORKSPACE', 'Choose real or practice first.')
        require(ws['mode'] == 'practice', 409, 'REAL_WORKSPACE', 'A real workspace never loads the fictional sample.')
        require(self.setup_state()['canLoadSample'], 409, 'NOT_EMPTY', 'The sample only loads into an empty practice workspace.')
        with self.db:
            self.load_sample()
        log('fictional sample loaded by', actor['id'])
        return self.setup_state()

    def skip(self, actor, body):
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner decides what to skip.')
        ws, item = self.meta('workspace'), body.get('item')
        require(ws is not None, 409, 'NO_WORKSPACE', 'Choose real or practice first.')
        require(item in ('dueDates', 'stillOwed', 'knowledge'), 400, 'INVALID_INPUT', 'Only recommended or optional items can be skipped.', 'item')
        skips = dict(ws.get('skips') or {})
        if body.get('skip') is False:
            skips.pop(item, None)
        else:
            skips[item] = {'by': actor['id'], 'at': now()}
        with self.db:
            self.set_meta('workspace', {**ws, 'skips': skips})
        return self.setup_state()

    # ------------------------------------------------------------ business records: manual entry, corrections, notes

    def records_view(self):
        doc = self.fixture()
        settings = settings_of(doc) if doc else None
        view = active_view(doc) if doc else None
        positions = {}
        if view and settings['currency']:
            whole, parts = split_by_customer(doc), split_by_customer(view)   # each customer's calculations scan only their own records
            today = self.today(doc)
            completing = {c['id'] for c in view['customers'] if opening_of(view, c['id']) or any(applies_to(s, c['id']) for s in view.get('coverage', []))}
            positions = {'customers': {c['id']: {**customer_position(whole[c['id']], c['id'], settings), 'opening': opening_view(whole[c['id']], c['id']),
                                                 'coverage': coverage_view(whole[c['id']], c['id']), 'owed': owed_position(whole[c['id']], c['id'], today, settings)}
                                         for c in view['customers']},
                         'invoices': {i['id']: i['position'] for i in view['invoices'] if i.get('position')},
                         # why an amount is not exact: invoices with payments allocated, and every invoice of a customer whose records are being completed
                         'notExact': {i['id']: i['position']['notExact'] if i.get('position') else exact_outstanding(parts[i['customerId']], i)[1]
                                      for i in view['invoices'] if (i.get('position') or i['customerId'] in completing)
                                      and not (i.get('position') or {}).get('exact')}}
        return {'datasetId': self.dataset_id(), 'workspace': (self.meta('workspace') or {}).get('mode'), 'settings': settings,
                'asOfDate': doc and self.today(doc).isoformat(), 'dataMode': doc and doc['dataMode'],
                'customers': doc['customers'] if doc else [], 'invoices': doc['invoices'] if doc else [], 'notes': doc['notes'] if doc else [],
                'payments': doc.get('payments', []) if doc else [], 'allocations': doc.get('allocations', []) if doc else [],
                'openingBalances': doc.get('openingBalances', []) if doc else [], 'coverage': doc.get('coverage', []) if doc else [],
                'positions': positions}

    def record_op(self, actor, op, key, body, change):
        """Apply one change to the records atomically, at most once per idempotency key. `change(doc)` mutates the document
        projection and returns the result; if it raises, nothing is saved."""
        scoped = actor['id'] + ':' + op + ':' + key if key else None
        if scoped:
            row = self.db.execute('SELECT payload_hash, result FROM record_ops WHERE key=?', (scoped,)).fetchone()
            if row:
                require(row[0] == fingerprint(body), 409, 'KEY_REUSED', 'This key was already used with different input.')
                return json.loads(row[1])
        doc = self.fixture()
        require(doc is not None, 409, 'NO_RECORDS', 'Set the currency, decimal places and time zone under Records first.')
        result = change(doc)
        with self.db:
            self.save_doc(doc)
            if scoped:
                self.db.execute('INSERT INTO record_ops (key, payload_hash, result, at) VALUES (?,?,?,?)', (scoped, fingerprint(body), json.dumps(result), now()))
            self.records_changed(op, actor, describe_change(doc, op.split('/'), result, actor))
        return result

    def records_changed(self, cause, actor, description=None):
        """After any records change: owner cases whose evidence changed are prepared again (evidence versions are per customer,
        so other customers' cases are left alone), and a decided case whose invoice evidence changed since the decision gets a
        visible flag saying what changed. A decision, its stored snapshot and the due date it set are never changed. Lock and
        transaction held. `description` says in plain words which record changed and who changed it (QA B5, U7)."""
        self.prepare_stale_cases('records changed (' + cause + ')', description)
        ev = self.evidence()
        for r in self.records():
            if r['status'] not in ('decided', 'completed') or not r.get('invoiceId'):
                continue
            seen, current = r.get('evidenceSeen'), ev.decision_evidence(r['invoiceId'])
            if seen is None or seen['key'] == current['key']:
                continue
            flag = {'kind': 'invoice_no_longer_in_records' if current['key'] is None else 'records_changed_after_decision', 'at': now(),
                    'by': actor['id'], 'role': actor['role'], **trail(actor), 'cause': cause, 'description': description,
                    'outstandingBefore': seen.get('outstanding'), 'outstandingNow': current['outstanding']}
            r['flags'] = r.get('flags', []) + [flag]
            r['evidenceSeen'] = current
            self.save(r)
            self.event(r, 'evidence.changed_after_decision', flag)
        self.settled.notify_all()

    def prepare_stale_cases(self, cause, description=None):
        """Owner cases whose evidence no longer matches the records are prepared again. A version written in the format of an
        earlier release (a fingerprint of the whole records document) that still matches the records is only re-stamped: the
        evidence is provably the same, so the agent is not run again. Lock and transaction held."""
        ev = self.evidence() if self.fixture() is not None else None
        for r in self.records():
            if r['status'] != 'awaiting_owner' or ev is None:
                continue
            invoice, stored = ev.invoice(r.get('invoiceId')), (r.get('task') or {}).get('evidenceVersion')
            current = invoice and ev.version_for(invoice['id'])
            if invoice is None or current == stored:
                if invoice is None:
                    r['version'] += 1
                    self.schedule(r, cause, description)
                continue
            legacy = fingerprint({'fixture': ev.fixture, 'invoiceId': invoice['id'], 'currentEffectiveDueDate': ev.current_due(invoice)})
            if stored == legacy:
                r['task']['evidenceVersion'] = r['analysis']['snapshot']['evidenceVersion'] = current
                self.save(r)
                self.event(r, 'evidence.version_updated', {'from': stored, 'to': current, 'reason': 'evidence version format changed; '
                                                           'the records it describes are unchanged'})
            else:
                r['version'] += 1
                self.schedule(r, cause, description)

    def record_decided_baselines(self):
        """Decided cases from an earlier release, or restored from a backup, have no record of the evidence they were decided on in
        this form. Start from the evidence as it is now, so only later changes are flagged. Lock and transaction held."""
        if self.fixture() is None:
            return
        ev = self.evidence()
        for r in self.records():
            if r['status'] in ('decided', 'completed') and r.get('invoiceId') and 'evidenceSeen' not in r:
                r['evidenceSeen'] = ev.decision_evidence(r['invoiceId'])
                self.save(r)
                self.event(r, 'evidence.baseline_recorded', {'reason': 'later records changes are compared with the records as they were now'})

    def migrate_evidence_keys(self):
        """Once per database, and after a restore: carry cases over to evidence key format 2 (docs/EVIDENCE-KEYS.md). A stored key is
        replaced only when it equals release a9ce30d's key for the records as they are now, which shows they have not changed since.
        Otherwise a decided case is flagged now, saying when the change was found, and a pending case is left to be prepared again.
        Existing flags, decisions and snapshots are never changed. Lock and transaction held."""
        if self.fixture() is None or (self.meta('evidenceKeys') or {}).get('format') == KEY_FORMAT:
            return
        before, disputes = self.evidence(), self.record_disputes()   # a9ce30d's keys are compared on the records as it left them
        ev, counts = self.evidence(), {'rebaselined': 0, 'restamped': 0, 'flagged': 0, 'disputes': disputes}
        for r in self.records():
            invoice_id = r.get('invoiceId')
            if r['status'] == 'awaiting_owner' and invoice_id and ev.invoice(invoice_id):
                stored, current = (r.get('task') or {}).get('evidenceVersion'), ev.version_for(invoice_id)
                if stored != current and stored == legacy_keys.version(before, invoice_id):
                    r['task']['evidenceVersion'] = r['analysis']['snapshot']['evidenceVersion'] = current
                    self.save(r)
                    self.event(r, 'evidence.version_updated', {'from': stored, 'to': current, 'reason': 'evidence key format 2; the records '
                                                               'it describes are unchanged since the case was prepared'})
                    counts['restamped'] += 1
            elif r['status'] in ('decided', 'completed') and invoice_id and r.get('evidenceSeen') and r['evidenceSeen'].get('format') != KEY_FORMAT:
                seen, current = r['evidenceSeen'], ev.decision_evidence(invoice_id)
                if seen['key'] == legacy_keys.decision_key(before, invoice_id):
                    r['evidenceSeen'] = current
                    self.save(r)
                    self.event(r, 'evidence.key_format_updated', {'from': seen['key'], 'to': current['key'], 'reason': 'the records were '
                                                                  'unchanged since they were last compared with this decision'})
                    counts['rebaselined'] += 1
                else:
                    flag = {'kind': 'invoice_no_longer_in_records' if current['key'] is None else 'records_changed_after_decision', 'at': now(),
                            'by': None, 'role': None, 'cause': 'startup comparison',
                            'description': 'Found when this version started: they no longer match the records last compared with this decision, '
                                           'and when or by whom they changed was not recorded',
                            'outstandingBefore': seen.get('outstanding'), 'outstandingNow': current['outstanding']}
                    r['flags'] = r.get('flags', []) + [flag]
                    r['evidenceSeen'] = current
                    self.save(r)
                    self.event(r, 'evidence.changed_after_decision', flag)
                    counts['flagged'] += 1
        self.set_meta('evidenceKeys', {'format': KEY_FORMAT, 'at': now(), **counts})
        log('evidence keys: format', KEY_FORMAT, counts)

    def record_disputes(self):
        """Imports applied before format 2 recorded a kept conflict only as a confirmation. Record it as the disagreement it is
        ('disputedBy'), for each conflicting row the import did not take. Returns how many were recorded. Lock and transaction held."""
        doc, added = self.fixture(), 0
        for (data,) in self.db.execute('SELECT data FROM batches').fetchall():
            batch = json.loads(data)
            if batch.get('status') != 'applied':
                continue
            taken = ((batch.get('params') or {}).get('resolutions') or {}).get('conflicts', {})
            for row in (batch.get('preview') or {}).get('rows', []):
                if row['status'] != 'conflict' or taken.get(str(row['row'])) == 'take':
                    continue
                kind, record_id = ('invoices', row.get('invoiceId')) if row.get('invoiceId') else ('payments', row.get('paymentId'))
                record = next((x for x in doc.get(kind, []) if x['id'] == record_id), None)
                if record and batch['id'] in record.get('confirmedBy', []) and batch['id'] not in record.get('disputedBy', []):
                    record['disputedBy'] = record.get('disputedBy', []) + [batch['id']]
                    added += 1
        if added:
            self.save_doc(doc)
        return added

    def cases_about(self, invoice_id):
        cases = [r for r in self.records() if r.get('invoiceId') == invoice_id]
        return ([r['id'] for r in cases if r['status'] in STATES_BEFORE_DECISION], [r['id'] for r in cases if r['status'] in ('decided', 'completed')])

    def records_action(self, actor, parts, body, key):
        require(actor['role'] in CASE_ROLES, 403, 'FORBIDDEN', 'Sign in as staff or owner.')
        require(self.meta('workspace') is not None, 409, 'NO_WORKSPACE', "This workspace isn't set up yet.")
        kind, at = parts[0], now()
        require(kind in ('customers', 'invoices', 'notes', 'payments', 'allocations', 'openingBalances', 'coverage') and 1 <= len(parts) <= 3, 404,
                'NOT_FOUND', 'Unknown route.')
        origin = {'kind': 'manual', 'by': actor['id'], 'role': actor['role'], **trail(actor), 'at': at}

        def settings_and_today(doc):
            return settings_of(doc), self.today(doc)
        if kind == 'coverage':
            # Saying records are complete is a claim about the business, confirmed like owner knowledge (B7 is open): owner only.
            require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner confirms that records are complete.')
            require(len(parts) == 1 or (len(parts) == 3 and parts[2] == 'retire'), 404, 'NOT_FOUND', 'Statements are confirmed or retired, not edited.')
            set_by = {'kind': 'manual', 'by': actor['id'], 'role': actor['role'], **trail(actor), 'at': at}
            change = ((lambda doc: {'record': new_coverage(doc, body, self.today(doc), uid('coverage'), set_by)}) if len(parts) == 1 else
                      (lambda doc: {'record': retire_coverage(doc, parts[1], body, set_by)}))
        elif kind == 'notes':
            if len(parts) == 1:
                change = lambda doc: {'record': new_note(doc, body, actor, at, uid('note'))}
            else:
                action = parts[2] if len(parts) == 3 else 'correct'
                require(action in ('confirm', 'retire', 'correct'), 404, 'NOT_FOUND', 'Unknown route.')
                change = lambda doc: {'record': note_action(doc, parts[1], action, body, actor, at)}
        elif kind == 'allocations':
            require(len(parts) in (1, 3) and parts[-1] in ('allocations', 'remove', 'statement'), 404, 'NOT_FOUND',
                    'Allocations are added or removed, not edited.')
            set_by = {'kind': 'answer', 'by': actor['id'], 'role': actor['role'], **trail(actor), 'at': at}
            if len(parts) == 1:
                change = lambda doc: {'records': allocate(doc, body, settings_of(doc), uid, origin)}
            elif parts[2] == 'statement':
                change = lambda doc: {'record': answer_statement(doc, parts[1], body, set_by)}
            else:
                change = lambda doc: self.remove_record(doc, kind, parts[1], body, actor, at)
        elif len(parts) == 1:
            if kind == 'customers':
                change = lambda doc: {'record': new_customer(doc, body, uid('customer'), origin)}
            elif kind == 'payments':
                change = lambda doc: {'record': new_payment(doc, body, *settings_and_today(doc), uid('payment'), origin)}
            elif kind == 'openingBalances':
                change = lambda doc: {'record': new_opening(doc, body, *settings_and_today(doc), uid('opening'), origin)}
            else:
                change = lambda doc: {'record': new_invoice(doc, body, *settings_and_today(doc), uid('invoice'), origin)}
        elif len(parts) == 2:
            def change(doc):
                set_by = {'kind': 'correction', 'by': actor['id'], 'role': actor['role'], **trail(actor), 'at': at, 'reason': reason_value(body)}
                return {'record': correct(doc, kind, parts[1], body, *settings_and_today(doc), set_by)}
        elif parts[2] == 'unrelated' and kind == 'payments':
            set_by = {'kind': 'answer', 'by': actor['id'], 'role': actor['role'], **trail(actor), 'at': at}
            change = lambda doc: {'record': mark_unrelated(doc, parts[1], body, set_by)}
        elif parts[2] == 'inclusion' and kind in ('invoices', 'payments'):
            set_by = {'kind': 'answer', 'by': actor['id'], 'role': actor['role'], **trail(actor), 'at': at}
            change = lambda doc: {'record': answer_inclusion(doc, kind, parts[1], body, settings_of(doc), set_by)}
        else:
            require(parts[2] == 'remove', 404, 'NOT_FOUND', 'Unknown route.')
            change = lambda doc: self.remove_record(doc, kind, parts[1], body, actor, at)
        return self.record_op(actor, '/'.join(parts), key, body, change)

    def remove_record(self, doc, kind, record_id, body, actor, at):
        """Remove a record entered by hand. Blocked when other records depend on it; cases about it need review first."""
        record = next((r for r in doc[kind] if r['id'] == record_id), None)
        require(record is not None, 404, 'NOT_FOUND', 'That record does not exist.')
        require(active(record), 409, 'INACTIVE', 'This record is already removed or reverted.')
        reason = reason_value(body)
        allocations = [a for a in doc.get('allocations', []) if active(a)]
        if kind == 'customers':
            invoices = [i['reference'] for i in doc['invoices'] if i['customerId'] == record_id and active(i)]
            notes = [n['id'] for n in doc['notes'] if n.get('scope') == record_id and n.get('status') in ('draft', 'confirmed')]
            payments = [p['id'] for p in doc.get('payments', []) if p['customerId'] == record_id and active(p)]
            openings = [o['id'] for o in doc.get('openingBalances', []) if o['customerId'] == record_id and active(o)]
            if invoices or notes or payments or openings:
                raise RecordsError(409, 'REMOVE_BLOCKED', 'Remove or retire this customer\'s invoices, payments, opening balance and notes first.',
                                   extra={'impact': {'invoices': invoices, 'notes': notes, 'payments': payments, 'openingBalances': openings}})
        elif kind == 'payments':
            used = [a['id'] for a in allocations if a['paymentId'] == record_id]
            if used:
                raise RecordsError(409, 'REMOVE_BLOCKED', 'Remove this payment\'s allocations first.', extra={'impact': {'allocations': used}})
            if 'file' in ((record.get('origin') or {}).get('kind'), (record.get('setBy') or {}).get('kind')):
                raise RecordsError(409, 'REMOVE_BLOCKED', 'This payment came from an import. Revert that import instead.')
        elif kind == 'openingBalances':
            cases = [self.cases_about(i['id']) for i in doc['invoices'] if i['customerId'] == record['customerId']]
            pending, decided = [c for p, _ in cases for c in p], [c for _, d in cases for c in d]
            if (pending or decided) and body.get('confirm') is not True:
                raise RecordsError(409, 'REVIEW_REQUIRED', 'Cases use this customer\'s invoices. Pending ones will be prepared again; decided ones keep '
                                   'their decision and get a note that the records changed.', extra={'impact': {'pendingCases': pending, 'decidedCases': decided}})
        elif kind == 'allocations':
            pending, decided = self.cases_about(record['invoiceId'])
            if (pending or decided) and body.get('confirm') is not True:
                raise RecordsError(409, 'REVIEW_REQUIRED', 'Cases use this invoice. Pending ones will be prepared again; decided ones keep their '
                                   'decision and get a note that the records changed.', extra={'impact': {'pendingCases': pending, 'decidedCases': decided}})
            record.update({'status': 'removed', 'removed': {'by': actor['id'], 'at': at, 'reason': reason}})
            return {'record': record}
        else:
            if any(a['invoiceId'] == record_id for a in allocations):
                raise RecordsError(409, 'REMOVE_BLOCKED', 'Payments are allocated to this invoice. Remove those allocations first.')
            if 'file' in ((record.get('origin') or {}).get('kind'), (record.get('setBy') or {}).get('kind')):
                raise RecordsError(409, 'REMOVE_BLOCKED', 'This invoice came from an import. Revert that import instead.',
                                   extra={'impact': {'batch': (record.get('setBy') or {}).get('batchId') or (record.get('origin') or {}).get('batchId')}})
            pending, decided = self.cases_about(record_id)
            if (pending or decided) and body.get('confirm') is not True:
                raise RecordsError(409, 'REVIEW_REQUIRED', 'Cases use this invoice. Pending ones will be prepared again; decided ones keep their '
                                   'decision and get a note that the invoice was removed.', extra={'impact': {'pendingCases': pending, 'decidedCases': decided}})
        record.update({'status': 'removed', 'removed': {'by': actor['id'], 'at': at, 'reason': reason}})
        return {'record': record}

    # ------------------------------------------------------------ CSV import of invoice lists

    def batch(self, batch_id):
        row = self.db.execute('SELECT data FROM batches WHERE id=?', (batch_id,)).fetchone()
        require(row is not None, 404, 'NOT_FOUND', 'That import does not exist.')
        return json.loads(row[0])

    def save_batch(self, batch):
        self.db.execute('INSERT OR REPLACE INTO batches VALUES (?, ?)', (batch['id'], json.dumps(batch)))

    @staticmethod
    def batch_view(batch):
        """An import as the page sees it: the stored file text is left out."""
        header, rows = importer.read_csv(batch['csvText'])
        fields, required, labels, _ = importer.SHAPES[batch.get('shape', 'invoices')]
        return {**{k: v for k, v in batch.items() if k != 'csvText'}, 'shape': batch.get('shape', 'invoices'), 'mapping': batch['params']['mapping'],
                'columns': header, 'sample': [cells for _, cells in rows[:5]],
                'fields': [{'id': f, 'label': labels[f], 'required': f in required} for f in fields]}

    def import_preview(self, batch):
        doc = self.fixture()
        header, rows = importer.read_csv(batch['csvText'])
        params = {**batch['params'], 'shape': batch.get('shape', 'invoices'), 'sourceLabel': batch['sourceLabel']}
        batch['preview'] = importer.preview(doc, header, rows, params, settings_of(doc), self.today(doc))
        batch['recordsVersion'] = fingerprint(doc)

    def upload_import(self, actor, body):
        require(self.meta('workspace') is not None and self.fixture() is not None, 409, 'NO_RECORDS',
                'Set the currency, decimal places and time zone under Records first.')
        label = text_value(body.get('sourceLabel'), 'sourceLabel', 80, 'where this file comes from')
        shape = body.get('shape') or 'invoices'
        require(shape in importer.SHAPES, 400, 'INVALID_INPUT', 'Choose what the file lists: invoices or payments received.', 'shape')
        text = body.get('csvText')
        header, rows = importer.read_csv(text)
        signature = importer.signature(header)
        profile = self.db.execute('SELECT data FROM profiles WHERE signature=?', (signature,)).fetchone()
        profile = json.loads(profile[0]) if profile else None
        profile = profile if profile and profile.get('shape', 'invoices') == shape else None   # a mapping is remembered per shape
        earlier = [json.loads(r[0]) for r in self.db.execute('SELECT data FROM batches')]
        same = next((b for b in earlier if b.get('sha256') == fingerprint(text) and b['status'] == 'applied'), None)
        batch = {'id': uid('batch'), 'kind': 'file', 'shape': shape, 'status': 'preview', 'sourceLabel': label,
                 'fileName': str(body.get('fileName') or 'pasted.csv')[:120], 'sha256': fingerprint(text), 'csvText': text,
                 'rowCount': len(rows), 'signature': signature, 'profileUsed': profile is not None,
                 'sameFileAs': same and {'id': same['id'], 'appliedAt': same.get('appliedAt')}, 'createdBy': actor['id'], 'createdAt': now(),
                 'params': {'mapping': profile['mapping'] if profile else importer.suggest_mapping(header, shape),
                            'dateOrder': profile.get('dateOrder') if profile else None, 'asOf': None, 'resolutions': {'customers': {}, 'conflicts': {}}}}
        self.import_preview(batch)
        with self.db:
            self.save_batch(batch)
        return self.batch_view(batch)

    def update_import(self, actor, batch, body):
        require(batch['status'] == 'preview', 409, 'NOT_PREVIEW', 'This import is already ' + batch['status'] + '.')
        resolutions = body.get('resolutions') or {}
        require(isinstance(resolutions, dict) and all(isinstance(resolutions.get(k, {}), dict) for k in ('customers', 'conflicts')), 400,
                'INVALID_INPUT', 'Invalid choices.', 'resolutions')
        require(body.get('dateOrder') in (None, 'dmy', 'mdy', 'ymd'), 400, 'INVALID_INPUT', 'Choose a date order.', 'dateOrder')
        batch['params'] = {'mapping': body.get('mapping', batch['params']['mapping']), 'dateOrder': body.get('dateOrder'),
                           'asOf': body.get('asOf'), 'resolutions': {'customers': resolutions.get('customers', {}), 'conflicts': resolutions.get('conflicts', {}),
                                                                     'rows': resolutions.get('rows', {}) if isinstance(resolutions.get('rows', {}), dict) else {}},
                           'coverage': self.import_coverage(actor, body.get('coverage'))}
        self.import_preview(batch)
        with self.db:
            self.save_batch(batch)
        return self.batch_view(batch)

    def import_coverage(self, actor, value):
        """The uploader's explicit statement that the file is complete for a period: for the customers in it (the default scope) or
        for all customers. Only the owner confirms completeness. Without one, an import says nothing about completeness."""
        if value in (None, False):
            return None
        require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner confirms that a file is complete.')
        require(isinstance(value, dict) and value.get('customers') in ('file', 'all'), 400, 'INVALID_INPUT',
                'Choose the customers in this file, or all customers.', 'coverage')
        start, end = parse_day(value.get('from'), 'coverageFrom'), parse_day(value.get('to'), 'coverageTo')
        require(start <= end <= self.today(self.fixture()).isoformat(), 400, 'INVALID_DATE', 'Choose a period that ends by today.', 'coverageTo')
        return {'customers': value['customers'], 'from': start, 'to': end, 'confirmedBy': actor['id']}

    def apply_coverage(self, doc, batch, set_by):
        """Record the import's completeness statement, if the owner gave one, for the customers its applied rows belong to."""
        coverage = batch['params'].get('coverage')
        if not coverage:
            return None
        known = importer.customer_index(doc)
        applied = {known[name_key(r['customerName'])]['id'] for r in batch['preview']['rows']
                   if r['status'] in ('new', 'unchanged', 'updated', 'conflict') and name_key(r['customerName']) in known}
        customers = 'all' if coverage['customers'] == 'all' else sorted(applied)
        if not customers:
            return None
        return new_coverage(doc, {'customers': customers, 'recordTypes': [batch.get('shape', 'invoices')], 'from': coverage['from'], 'to': coverage['to'],
                                  'confirm': True, 'sourceLabel': 'Import of ' + batch['fileName'] + ' (' + batch['sourceLabel'] + ')'},
                            self.today(doc), uid('coverage'), set_by, basis='export', batch_id=batch['id'])['id']

    def apply_import(self, actor, batch):
        if batch['status'] == 'applied':
            return self.batch_view(batch)   # a retried apply
        require(batch['status'] == 'preview', 409, 'NOT_PREVIEW', 'This import is ' + batch['status'] + '.')
        doc = self.fixture()
        if batch['recordsVersion'] != fingerprint(doc):   # the records changed since this preview was shown
            self.import_preview(batch)
            with self.db:
                self.save_batch(batch)
            raise RecordsError(409, 'RECORDS_CHANGED', 'The records changed since this preview. Check the refreshed preview, then apply.',
                               extra={'batch': self.batch_view(batch)})
        set_by = {'kind': 'file', 'batchId': batch['id'], 'sourceLabel': batch['sourceLabel'], 'fileName': batch.get('fileName'), 'by': actor['id'], 'role': actor['role'], **trail(actor), 'at': now()}
        result, _ = importer.APPLY.get(batch.get('shape'), importer.apply)(doc, batch, batch['preview'], uid, set_by)
        result['coverage'] = self.apply_coverage(doc, batch, set_by)
        header, _ = importer.read_csv(batch['csvText'])
        batch.update({'status': 'applied', 'result': result, 'appliedBy': actor['id'], 'appliedAt': set_by['at']})
        with self.db:
            self.save_doc(doc)
            self.save_batch(batch)
            self.db.execute('INSERT OR REPLACE INTO profiles VALUES (?, ?)', (batch['signature'], json.dumps(
                {'mapping': batch['params']['mapping'], 'dateOrder': batch['params']['dateOrder'], 'sourceLabel': batch['sourceLabel'],
                 'shape': batch.get('shape', 'invoices'),
                 'header': header, 'savedBy': actor['id'], 'savedAt': set_by['at']})))
            self.records_changed('import ' + batch['id'], actor, 'An import was applied (' + batch['fileName'] + ', ' + batch['sourceLabel'] + ')')
        log('import', batch['id'], 'applied by', actor['id'], '-', batch['preview']['counts'])
        try:   # the new payments may settle approved decisions: observe them now (its own transaction; the import is already committed and never fails for this)
            self.observe_outcomes()
        except Exception as error:   # noqa: BLE001 - an observation can be made again on demand
            log('outcome observation after import', batch['id'], 'failed:', type(error).__name__)
        return self.batch_view(batch)

    def revert_impact(self, batch, doc):
        """What reverting this applied import would do: blocked reasons, records it reverts or restores, and what needs review."""
        batches = {b['id']: b for b in (json.loads(d) for (d,) in self.db.execute('SELECT data FROM batches'))}   # which later imports support a record
        impact = importer.REVERT_IMPACT.get(batch.get('shape'), importer.revert_impact)(doc, batch, self.cases_about, batches.get)
        statements = [c for c in doc.get('coverage', []) if active(c) and c.get('batchId') == batch['id']]   # removed with it, after review
        impact['review']['coverage'] = [{'coverageId': c['id'], 'from': c['from'], 'to': c['to'], 'customers': c['customers']} for c in statements]
        impact['needsReview'] = impact['needsReview'] or bool(statements)
        return impact, statements

    def revert_preview(self, batch):
        """Read-only: the revert's impact in plain words, shown before anyone submits a revert (QA B3). The server checks again on submit."""
        require(batch['status'] == 'applied', 409, 'NOT_APPLIED', 'Only an applied import can be reverted. This one is ' + batch['status'] + '.')
        doc = self.fixture()
        impact, _ = self.revert_impact(batch, doc)
        return {'batchId': batch['id'], 'blocked': impact['blocked'], 'needsReview': impact['needsReview'],
                'effects': revert_effects(doc, batch, impact), 'review': revert_review_lines(impact['review']),
                'cases': {'pending': impact['review']['pendingCases'], 'decided': impact['review']['decidedCases']}}

    def revert_import(self, actor, batch, body):
        if batch['status'] == 'reverted':
            return self.batch_view(batch)
        require(batch['status'] == 'applied', 409, 'NOT_APPLIED', 'Only an applied import can be reverted.')
        reason, doc = reason_value(body), self.fixture()
        impact, statements = self.revert_impact(batch, doc)
        if impact['blocked']:
            raise RecordsError(409, 'REVERT_BLOCKED', 'This import cannot be reverted yet.', extra={'impact': impact})
        if impact['needsReview'] and body.get('confirm') is not True:
            review = impact['review']
            raise RecordsError(409, 'REVIEW_REQUIRED', ' '.join(filter(None, [
                (review['pendingCases'] or review['decidedCases']) and 'Cases use these invoices. Pending ones will be prepared again; decided ones '
                'keep their decision and get a note that the records changed.',
                review.get('answers') and str(len(review['answers'])) + ' answer(s) about these records will no longer apply.',
                review.get('coverage') and 'The completeness statement that came with this import will be removed, and "complete to" dates '
                'recalculated.'])), extra={'impact': impact})
        set_by = {'kind': 'revert', 'batchId': batch['id'], 'by': actor['id'], 'role': actor['role'], **trail(actor), 'at': now(), 'reason': reason}
        importer.REVERT.get(batch.get('shape'), importer.revert)(doc, batch, impact, set_by)
        for statement in statements:
            statement.update({'status': 'reverted', 'reverted': set_by})
        batch.update({'status': 'reverted', 'revertedBy': actor['id'], 'revertedAt': set_by['at'], 'revertReason': reason, 'revertImpact': impact})
        with self.db:
            self.save_doc(doc)
            self.save_batch(batch)
            self.records_changed('revert of ' + batch['id'], actor, 'An import was reverted (' + batch['fileName'] + ', ' + batch['sourceLabel'] + ')')
        log('import', batch['id'], 'reverted by', actor['id'])
        return self.batch_view(batch)

    def discard_import(self, actor, batch):
        """A draft that was never applied is discarded: it can no longer be applied, and nothing in the records changes (QA B4)."""
        if batch['status'] == 'discarded':
            return self.batch_view(batch)
        require(batch['status'] == 'preview', 409, 'NOT_PREVIEW', 'Only a draft that was never applied can be discarded. This import is ' +
                batch['status'] + '.')
        batch.update({'status': 'discarded', 'discardedBy': actor['id'], 'discardedAt': now()})
        with self.db:
            self.save_batch(batch)
        return self.batch_view(batch)

    def applied_twin(self, sha, pid):
        """The stored import proposal, other than pid, that was applied from a file with this hash and still has an applied batch (one
        whose batches were all reverted is not imported any more); else None. Lock held."""
        for (data,) in self.db.execute("SELECT data FROM meta WHERE key LIKE ?1 AND key != ?2 AND json_extract(data, '$.sha256') = ?3 "
                                       "AND json_extract(data, '$.status') = 'applied'", (IMPORT_PROPOSALS + '%', IMPORT_PROPOSALS + pid, sha)).fetchall():
            twin = json.loads(data)
            if self.still_applied(twin):
                return twin

    def still_applied(self, p):
        """Whether at least one batch of an applied proposal is still applied (not reverted). Lock held."""
        return any((self.batch(b['id']) or {}).get('status') == 'applied' for b in p['batches'])

    def recheck_unit(self, p):
        """Brings a stored proposal made under older unit rules up to the current ones: the unit is read again from the kept file (all
        sheets, the magnitude rule) and stored in its view. False when that cannot be done (no file kept): the proposal is stale."""
        if p.get('unitRules', 0) >= UNIT_RULES:
            return True
        if not p.get('file'):
            return False
        doc = self.fixture()
        settings = settings_of(doc)
        try:
            unit = DeskTools.draft_import(p['file'], p['hints'], None, settings, self.today(doc))[2]['unit']
        except ToolError:
            return False
        workspace = {'currency': settings['currency'], 'scale': settings['scale']}
        notes = [n for n in p['view']['notes'] if 'does not say its currency' not in n]
        if unit['detected'] is None and not unit.get('doubtful'):
            notes.append('The file does not say its currency; amounts are taken as ' + workspace['currency'] + '.')
        p['view'].update({'unit': unit, 'workspace': workspace, 'unitProblem': unit_problem(unit, workspace), 'notes': notes})
        p['unitRules'] = UNIT_RULES
        with self.db:
            self.set_meta(IMPORT_PROPOSALS + p['id'], p)
        return True

    def proposal_state(self, proposal_id):
        """An import proposal as it stands now, for the card to render from after a refresh, restart or deploy: the proposal's state and
        the view the card uses. A proposed file that an applied proposal already imported reads as a duplicate. Lock held."""
        with self.lock:
            return self._proposal_state(proposal_id)

    def _proposal_state(self, proposal_id):
        p = self.meta(IMPORT_PROPOSALS + proposal_id)
        require(p is not None, 404, 'NOT_FOUND', 'No import proposal has that id.')
        if p['status'] in ('proposed', 'refused', 'duplicate') and not self.recheck_unit(p):
            self.set_meta(IMPORT_PROPOSALS + proposal_id, {**p, 'status': 'stale', 'lastError': STALE_PROPOSAL})
            p = self.meta(IMPORT_PROPOSALS + proposal_id)
        status, view = p['status'], p['view']
        twin = None
        if status in ('proposed', 'duplicate') and p.get('sha256'):
            twin = self.applied_twin(p['sha256'], proposal_id)
            status = 'duplicate' if twin else 'proposed'
        reverted = status == 'applied' and not self.still_applied(p)
        if reverted:
            status = 'reverted'
        zone = (settings_of(self.fixture()) or {}).get('timezone')
        message = duplicate_message(twin, zone) if twin else p.get('lastError') if status in ('refused', 'stale') else None
        proposal = {'id': p['id'], 'version': p['version'], 'status': status, 'fileName': p['fileName'], 'unit': view.get('unit'), 'workspace': view.get('workspace'),
                    'references': view.get('references'), 'counts': view['counts'], 'batches': p['batches'] if status in ('applied', 'reverted') else [],
                    'lastError': p.get('lastError'), 'message': message,
                    **({'appliedAt': p['appliedAt'], 'appliedAtText': imported_text(p, zone)} if status in ('applied', 'reverted') else {}),
                    **({'revertedAt': max(self.batch(b['id']).get('revertedAt') or '' for b in p['batches'])} if reverted else {})}
        if status == 'duplicate' and view.get('references'):
            view = {**view, 'referencesText': ALREADY_MATCHED}
        return {'proposal': proposal, 'view': view, 'card': p['card']}

    def imports_list(self):
        batches = [json.loads(r[0]) for r in self.db.execute('SELECT data FROM batches')]
        keys = ('id', 'status', 'sourceLabel', 'fileName', 'rowCount', 'createdBy', 'createdAt', 'appliedBy', 'appliedAt', 'revertedBy',
                'revertedAt', 'revertReason', 'sameFileAs', 'discardedBy', 'discardedAt')
        return [{**{k: b.get(k) for k in keys}, 'shape': b.get('shape', 'invoices'), 'counts': b['preview']['counts'], 'asOf': b['params'].get('asOf')}
                for b in sorted(batches, key=lambda b: b['createdAt'], reverse=True)]

    # ------------------------------------------------------------ demo console (practice workspaces only)

    def meta(self, key):
        row = self.db.execute('SELECT data FROM meta WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def set_meta(self, key, value):
        self.db.execute('INSERT OR REPLACE INTO meta VALUES (?, ?)', (key, json.dumps(value)))

    def backup_files(self):
        return sorted(self.backup_dir.glob(self.db_path.stem + '-*.sqlite3'), key=lambda f: f.stat().st_mtime, reverse=True) if self.backup_dir.is_dir() else []

    def backups(self, limit=8):
        listed = []
        for f in self.backup_files()[:limit]:
            try:
                source = sqlite3.connect('file:' + str(f) + '?mode=ro', uri=True)
                cases = source.execute('SELECT COUNT(*) FROM requests').fetchone()[0]
                source.close()
            except sqlite3.Error:
                cases = None
            listed.append({'name': f.name, 'createdAt': datetime.fromtimestamp(f.stat().st_mtime, timezone.utc).isoformat(), 'cases': cases})
        return listed

    def backup(self, reason):
        """Consistent copy of the live database (SQLite online backup). Lock held."""
        self.backup_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        path, n = self.backup_dir / (self.db_path.stem + '-' + stamp + '-' + reason + '.sqlite3'), 2
        while path.exists():
            path, n = self.backup_dir / (self.db_path.stem + '-' + stamp + '-' + reason + '-' + str(n) + '.sqlite3'), n + 1
        target = sqlite3.connect(str(path))
        self.db.backup(target)
        target.execute('PRAGMA journal_mode=DELETE')   # one self-contained file
        target.close()
        for companion in ('-wal', '-shm'):   # some SQLite builds leave an empty -shm behind after the switch
            Path(str(path) + companion).unlink(missing_ok=True)
        path.chmod(0o600)
        return path.name

    def is_initial(self):
        ws = self.meta('workspace') or {}
        return not self.records() and self.desk_empty() and self.fixture() == self.initial_fixture and \
            ws.get('sampleFingerprint') == fingerprint(self.initial_fixture) and not any(self.count(t) for t in ('delegation_policies', 'decision_cases', 'confirmed_facts'))

    def count(self, table):
        return self.db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]

    def desk_empty(self):
        """Nothing said and the business date not moved: what reset and start-empty return to."""
        return not self.statements() and self.meta('businessDateOffset') is None

    def console_allowed(self):
        return self.demo is not None and (self.meta('workspace') or {}).get('mode') != 'real'

    def console_state(self):
        counts, doc = {}, self.fixture()
        for r in self.records():
            counts[r['status']] = counts.get(r['status'], 0) + 1
        running = self.db.execute("SELECT COUNT(*) FROM runs WHERE status='running'").fetchone()[0]
        return {'cases': sum(counts.values()), 'byStatus': counts, 'agentRunning': running,
                'fixtureCurrent': self.fixture() == self.initial_fixture, 'lastReset': self.meta('lastReset'),
                'lastRestore': self.meta('lastRestore'), 'backups': self.backups(),
                'agent': self.agent_info(), 'asOfDate': doc and (doc.get('asOfDate') or self.meta('businessDateOffset')) and self.today(doc).isoformat(),
                'workspace': (self.meta('workspace') or {}).get('mode'), 'sampleLoaded': bool((self.meta('workspace') or {}).get('sampleFingerprint'))}

    def reset_demo(self, actor, to=None):
        """Back up, then return to the initial fictional records (to='empty': an empty workspace with no settings, for the owner to
        set up). Sessions and codes are untouched."""
        require(to in (None, 'empty'), 400, 'INVALID_INPUT', "'to' may be 'empty'.", 'to')
        if to is None and self.is_initial():
            return {'reset': False, 'backup': None}   # already clean: a second click changes nothing
        name = self.backup('before-reset')
        self.epoch += 1
        with self.db:
            for table in DATA_TABLES:
                self.db.execute('DELETE FROM ' + table)
            self.db.execute("DELETE FROM meta WHERE key='businessDateOffset' OR key LIKE ?", (IMPORT_PROPOSALS + '%',))
            # The operator's explicit request to load the sample (also on an empty database); never in a real workspace.
            if self.meta('workspace') is None or to:
                self.set_meta('workspace', {'mode': 'practice', 'origin': 'console', 'createdAt': now(), 'sampleFingerprint': None, 'skips': {}})
            if to:
                self.replace_doc(None)
            else:
                self.load_sample()
            self.set_meta('lastReset', {'at': now(), 'by': actor['id'], 'backup': name, **({'kind': 'empty'} if to else {})})
        self.settled.notify_all()
        log('demo reset by', actor['id'], '- backup', name)
        return {'reset': True, 'backup': name}

    def start_empty(self, actor):
        """Back up, then clear cases and records but keep the settings: rehearse setup in a practice workspace."""
        ws, doc = self.meta('workspace') or {}, self.fixture()
        if not self.records() and self.desk_empty() and ws.get('mode') == 'practice' and not ws.get('sampleFingerprint') and \
                not (doc and (doc['customers'] or doc['invoices'] or doc['notes'])):
            return {'emptied': False, 'backup': None}
        name = self.backup('before-start-empty')
        self.epoch += 1
        settings = settings_of(doc) if doc else None
        with self.db:
            for table in DATA_TABLES:
                self.db.execute('DELETE FROM ' + table)
            self.db.execute("DELETE FROM meta WHERE key='businessDateOffset' OR key LIKE ?", (IMPORT_PROPOSALS + '%',))
            self.replace_doc(empty_document(settings, practice=True) if settings and settings['currency'] else None)
            self.set_meta('workspace', {'origin': 'console', 'createdAt': now(), **ws, 'mode': 'practice', 'sampleFingerprint': None, 'skips': {}})
            self.set_meta('lastReset', {'at': now(), 'by': actor['id'], 'backup': name, 'kind': 'start_empty'})
        self.settled.notify_all()
        log('practice workspace emptied by', actor['id'], '- backup', name)
        return {'emptied': True, 'backup': name}

    def restore_demo(self, actor, name):
        require(isinstance(name, str) and re.fullmatch(r'[A-Za-z0-9._-]+\.sqlite3', name) and
                name in {f.name for f in self.backup_files()}, 404, 'NO_BACKUP', 'Choose a backup from the list.', 'backup')
        source = sqlite3.connect('file:' + str(self.backup_dir / name) + '?mode=ro', uri=True)
        try:
            tables = {row[0] for row in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            require({'requests', 'events', 'fixtures'} <= tables, 422, 'INVALID_BACKUP', 'That file is not a Nucleon database.', 'backup')
            saved = None if self.is_initial() else self.backup('before-restore')
            self.epoch += 1
            source.backup(self.db)
        finally:
            source.close()
        self.db.execute('PRAGMA journal_mode = WAL')   # the copied header carries the backup's (rollback) mode
        self.ensure_schema()
        with self.db:
            self.set_meta('lastRestore', {'at': now(), 'by': actor['id'], 'from': name, 'backup': saved})
            self.set_meta('lastReset', {'at': now(), 'by': actor['id'], 'backup': saved, 'kind': 'restore'})   # a new datasetId: the records were replaced
        self.recover()
        self.settled.notify_all()
        log('demo restore by', actor['id'], 'from', name, '- previous data saved as', saved)
        return {'restored': name, 'backup': saved}

    def advance_business_date(self, actor, days):
        """Move a practice workspace's business date forward by whole days, to rehearse what happens later. Lock held."""
        if actor['role'] != 'operator':
            raise RecordsError(403, 'FORBIDDEN', 'Only the demo console moves the business date.')
        if (self.meta('workspace') or {}).get('mode') != 'practice':
            raise RecordsError(409, 'NOT_PRACTICE', 'Only a practice workspace can move its business date.')
        require(type(days) is int and 1 <= days <= 366, 400, 'INVALID_INPUT', 'Enter a whole number of days from 1 to 366.', 'days')
        doc = self.fixture()
        require(doc is not None, 409, 'NO_SETTINGS', 'Save the settings first.')
        with self.db:
            self.set_meta('businessDateOffset', (self.meta('businessDateOffset') or 0) + days)
            # The as-of date is part of every case's evidence: cases waiting for the owner are prepared again for the new date.
            self.prepare_stale_cases('business date advanced', 'The demo console moved the business date forward.')
        self.settled.notify_all()
        log('business date moved', days, 'days by', actor['id'])
        return self.today(doc)

    # ------------------------------------------------------------ agent runs

    def adapter_for(self, mode):
        if mode == 'live':
            require(self.model_adapter is not None, 500, 'NO_MODEL', 'Live mode needs a model configuration.')
            return self.model_adapter, CALLERS['live']
        if mode == 'unavailable':
            return UnavailableAdapter(), CALLERS['unavailable']
        return MockAdapter(), CALLERS['mock']

    def run_record(self, run_id):
        row = self.db.execute('SELECT data FROM runs WHERE id=?', (run_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def store_run(self, run):
        self.db.execute('INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?)',
                        (run['id'], run['requestId'], run['requestVersion'], run['status'], json.dumps(run)))

    def close_run(self, run, status, details):
        run.update({'status': status, 'finishedAt': now(), **details})
        self.store_run(run)

    def run_is_current(self, run_id):
        run = self.run_record(run_id)
        if not run or run['status'] != 'running':
            return False
        r = self.get(run['requestId'])
        return r['version'] == run['requestVersion'] and r.get('activeRunId') == run_id and r['status'] == 'analysing'

    def schedule(self, r, cause, description=None):
        """Persist one queued run for the request's current version (lock and transaction held). `description` is the cause in plain
        words, for the case's activity."""
        for run in self.runs_for(r['id']):
            if run['status'] == 'running':
                self.close_run(run, 'superseded', {'reason': cause})
        if r.get('analysis') or r.get('task'):
            self.event(r, 'analysis.superseded', {'task': r.get('task'), 'analysis': r.get('analysis'), 'cause': cause, 'description': description})
        run = {'id': uid('run'), 'requestId': r['id'], 'requestVersion': r['version'], 'status': 'running',
               'mode': self.agent_mode, 'cause': cause, 'queuedAt': now(), 'startedAt': None}
        r.update({'status': 'analysing', 'activeRunId': run['id'], 'analysis': None, 'task': None})
        r.pop('preparationFailure', None)   # kept in the event log; a new run starts clean
        self.end_preparation(r, 'withdrawn', None)   # prepared on facts now being worked out again
        self.store_run(run)
        self.save(r)
        self.event(r, 'analysis.queued', {'runId': run['id'], 'mode': run['mode'], 'requestVersion': r['version'], 'cause': cause, 'description': description})
        self.queue.put(run['id'])
        return run

    def schedule_suggest(self, r, cause):
        """Queue a suggestion step for a case waiting for the owner, on the same worker queue as preparation. It changes only the
        brief's suggestion fields, never the request's status or version or its analysis. Lock and transaction held."""
        for run in self.runs_for(r['id']):
            if run['status'] == 'running':   # a case waiting for the owner can only be running an earlier suggestion step
                self.close_run(run, 'superseded', {'reason': cause})
        run = {'id': uid('run'), 'kind': 'suggest', 'requestId': r['id'], 'requestVersion': r['version'], 'analysisId': r['analysis']['id'],
               'status': 'running', 'mode': self.agent_mode, 'cause': cause, 'queuedAt': now(), 'startedAt': None}
        self.store_run(run)
        self.queue.put(run['id'])
        return run

    @staticmethod
    def suggestable(r):
        """A case the agent prepared (brief-v3), waiting for the owner."""
        return r['status'] == 'awaiting_owner' and r['task'].get('mode') == 'agent' and 'questions' in (r['analysis'].get('brief') or {})

    def suggest(self, run_id):
        """A suggestion step for a case already waiting for the owner: what it is given is read under the lock, the model is
        asked without it, and the result is written only if the data, the run, the case and its analysis are all unchanged and
        suggestions are still on."""
        with self.lock:
            run, epoch = self.run_record(run_id), self.epoch
            if not run or run['status'] != 'running':
                return
            r = self.suggest_target(run)
            with self.db:
                run['startedAt'] = now()
                if r:
                    self.store_run(run)
                else:
                    self.close_run(run, 'superseded', {'reason': 'the case changed before the step started'})
            if not r:
                self.settled.notify_all()
                return
            adapter, caller = self.adapter_for(run['mode'])
            brief, context = r['analysis']['brief'], self.context_for(r['customerId'], 'owner', r['id'])
            inputs = suggestion_inputs(brief, brief['questions'], context, [{'field': k, 'value': v} for k, v in r['answers'].items()])
        found = suggestion_step(adapter, caller, inputs, self.deadline_seconds)
        with self.lock:
            if self.epoch != epoch:   # reset or restored meanwhile: the run and the case may no longer exist
                return
            run = self.run_record(run_id)
            r = run and self.suggest_target(run)
            with self.db:
                if r:
                    self.update_suggestion(r, found)
                if run and run['status'] == 'running':
                    self.close_run(run, 'finished' if r else 'superseded', {'suggestionStatus': found['status'], 'suggestionStats': found['stats']})
            self.settled.notify_all()

    def suggest_target(self, run):
        """The case a suggest run may still write to, or None: the run is running, suggestions are on, and the case is waiting
        for the owner on the same analysis. Lock held."""
        r = self.get(run['requestId'])
        return r if run['status'] == 'running' and self.meta('showSuggestions') and self.suggestable(r) and r['analysis']['id'] == run['analysisId'] else None

    def put_suggestion(self, r, brief, found):
        """Write one suggestion step's result onto a brief as a new version. The version is counted on the request, so a later
        analysis never repeats one the owner may still have on screen. Its failure sentence replaces the step's earlier one."""
        r['suggestionVersion'] = version = r.get('suggestionVersion', 0) + 1
        brief.update({'suggestion': found['suggestion'] and {**found['suggestion'], 'version': version}, 'suggestionStatus': found['status'],
                      'withheldBecause': found['withheldBecause'],
                      'openItems': [x for x in brief['openItems'] if x.get('step') != 'suggest'] +
                                   [{'kind': 'code_check', 'text': c, 'step': 'suggest'} for c in found.get('checks', ())]})
        return version

    def update_suggestion(self, r, found):
        """A new suggestion on a case already waiting. Lock and transaction held."""
        version = self.put_suggestion(r, r['analysis']['brief'], found)
        self.end_preparation(r, 'withdrawn', None)   # prepared beside the suggestion it replaces: the owner sees the new one and prepares again
        self.save(r)
        self.event(r, 'suggestion.updated', {'version': version, 'status': found['status']})

    def work(self):
        while True:
            run_id = self.queue.get()
            if run_id is None:
                return
            try:
                with self.lock:
                    kind = (self.run_record(run_id) or {}).get('kind')
                (self.suggest if kind == 'suggest' else self.execute)(run_id)
            except Exception as exc:  # never leave a request stuck in analysing
                log('run', run_id, 'internal error:', type(exc).__name__, exc)
                try:
                    with self.lock:
                        run = self.run_record(run_id)
                        if run and run.get('kind') == 'suggest' and run['status'] == 'running':
                            r = self.suggest_target(run)
                            with self.db:
                                if r:   # never leave a status (e.g. withheld for questions since answered) the step was replacing
                                    self.update_suggestion(r, {'suggestion': None, 'status': 'failed', 'withheldBecause': [], 'checks': [STEP_FAILED]})
                                self.close_run(run, 'failed', {'failure': {'kind': 'internal_error', 'detail': type(exc).__name__}})
                        elif run and self.run_is_current(run_id):
                            with self.db:
                                self.close_run(run, 'failed', {'failure': {'kind': 'internal_error', 'detail': type(exc).__name__}})
                                self.fallback_or_fail(self.get(run['requestId']), run, {'kind': 'internal_error', 'detail': type(exc).__name__})
                        self.settled.notify_all()
                except Exception as inner:
                    log('run', run_id, 'recovery failed:', type(inner).__name__)

    def execute(self, run_id):
        with self.lock:
            run = self.run_record(run_id)
            if not run or not self.run_is_current(run_id):
                return
            epoch = self.epoch
            r = self.get(run['requestId'])
            if r['intake'].get('structured') is not None:   # opened from a confirmed action: code builds the case, no model is asked, whatever the run's mode
                run.update({'startedAt': now(), 'adapter': STRUCTURED_ADAPTER, 'model': None, 'promptVersion': None})
                with self.db:
                    self.store_run(run)
                    self.event(r, 'analysis.started', {'runId': run_id, 'requestVersion': r['version'], 'mode': run['mode'], 'adapter': STRUCTURED_ADAPTER,
                                                       'promptVersion': None})
                    self.structured_case(r, run)
                self.settled.notify_all()
                return
            adapter, caller = self.adapter_for(run['mode'])
            evidence = self.evidence()
            message, answers = r['intake']['text'], dict(r['answers'])
            run.update({'startedAt': now(), 'adapter': adapter.name, 'model': adapter.describe(),
                        'promptVersion': PROMPT_VERSION if run['mode'] == 'live' else None})
            with self.db:
                self.store_run(run)
                self.event(r, 'analysis.started', {'runId': run_id, 'requestVersion': r['version'], 'mode': run['mode'],
                                                   'adapter': adapter.name, 'promptVersion': run['promptVersion']})
        # Network and inference happen without the application lock.
        identity = adapter.identity() if run['mode'] == 'live' else None
        outcome = AgentRunner(adapter, caller, self.deadline_seconds).run(message, answers, evidence, RunHooks(self, run_id, r['id'], epoch))
        extras = None
        if outcome.status == 'task' and outcome.terminal.terminal == 'approval':
            extras = self.plan_needs(run_id, r, outcome, evidence, adapter, caller, epoch)
        with self.lock:
            if self.epoch != epoch:   # reset or restored during inference: the result belongs to data that no longer exists
                log('run', run_id, 'discarded: data was reset or restored during inference')
                return
            with self.db:
                self.commit_outcome(run_id, outcome, identity, caller, extras)
            self.settled.notify_all()
        if self.verbose:
            log('run', run_id, 'mode=' + run['mode'], 'status=' + outcome.status,
                'failure=' + (outcome.failure or {}).get('kind', '-'), 'modelCalls=' + str(outcome.stats.get('modelCalls')),
                'toolCalls=' + str(outcome.stats.get('toolCalls')), 'elapsedMs=' + str(outcome.stats.get('elapsedMs')))

    def plan_needs(self, run_id, r, outcome, evidence, adapter, caller, epoch):
        """What an approval case still needs, given what the owner has said (all of it: the questions are the owner's) and the
        customer's decided cases; then, when the owner has suggestions on, the suggestion. Reads them under the lock and asks the
        model without it, within what is left of the run's deadline. After the model's questions, code adds its own (still_holds).
        None when the run is no longer current: commit_outcome then discards it."""
        d = outcome.dispatcher
        snap = d.snapshots[outcome.terminal.payload['snapshotLocalId']]
        with self.lock:
            if self.epoch != epoch or not self.run_is_current(run_id):
                return None
            context, on = self.context_for(snap['customer']['id'], 'owner', r['id']), bool(self.meta('showSuggestions'))
            today = self.today(self.fixture())
        deadline = time.monotonic() + max(1, self.deadline_seconds - outcome.stats['elapsedMs'] / 1000)
        # Rendered here only for its code-written summary and facts, which are what the model is given.
        brief = render_brief(snap, d.facts[snap['localId']], d.request_input, [], [], [], caller, evidence.fixture['version'])
        conflict = (snap['invoice'].get('position') or {}).get('status') == 'conflict'
        answers = [{'field': k, 'value': v} for k, v in r['answers'].items()]
        needs = guarded(prepare_needs, {'questions': [], 'checks': [STEP_FAILED], 'stats': {}}, adapter=adapter, caller=caller,
                        facts_text=facts_for_model(brief['summary'], brief['facts']), lines=context['lines'], decisions=context['decisions'],
                        answers=answers, code_missing=['records_conflict'] if conflict else [], timeout=max(1, deadline - time.monotonic()))
        needs = {**needs, 'questions': needs['questions'] + still_holds(context['lines'], needs['questions'], today)}
        # A decided case is named by its request: context_for gives decisions that way, one per request.
        extras = {**needs, 'contextShown': [x['id'] for x in context['lines']] + [x['requestId'] for x in context['decisions']],
                  'ownerQuotes': [x['quote'] for x in context['lines'] if x['visibility'] == 'owner']}
        if on:
            extras['suggestion'] = suggestion_step(adapter, caller, suggestion_inputs(brief, needs['questions'], context, answers),
                                                   max(1, deadline - time.monotonic()))
        return extras

    def commit_outcome(self, run_id, outcome, identity, caller, extras=None):
        """Re-check run, request and evidence versions before saving any model-prepared result. extras: plan_needs's result for
        an approval (questions, checks, stats, contextShown, ownerQuotes: the owner-only quotes the needs step was given)."""
        run = self.run_record(run_id)
        locked = run and self.get(run['requestId'])
        if locked and locked['intake'].get('structured') is not None:   # defence in depth: execute never asks a model about one, and no outcome is ever used
            self.event(locked, 'analysis.discarded', {'runId': run_id, 'reason': 'opened from a confirmed action: its fields are fixed and a model result is never used',
                                                      'discardedTool': outcome.terminal and outcome.terminal.name})
            if self.run_is_current(run_id):   # the case is still built, by code
                self.structured_case(locked, run)
            return
        if outcome.status == 'superseded' or not self.run_is_current(run_id):
            if run and run['status'] == 'running':
                self.close_run(run, 'superseded', {'reason': 'request changed during inference', 'stats': outcome.stats})
            self.db.execute('INSERT INTO events (request_id,kind,at,data) VALUES (?,?,?,?)', (run['requestId'], 'analysis.discarded', now(), json.dumps(
                {'runId': run_id, 'reason': 'request version or active run changed during inference', 'discardedTool': outcome.terminal and outcome.terminal.name})))
            return
        r = self.get(run['requestId'])
        model = {**run['model'], 'serving': identity, 'servedModel': outcome.stats.get('servedModel')}
        run.update({'model': model, 'stats': outcome.stats})
        if outcome.status == 'failed':
            self.close_run(run, 'failed', {'failure': outcome.failure})
            self.fallback_or_fail(r, run, outcome.failure, outcome)
            return
        dispatcher, terminal = outcome.dispatcher, outcome.terminal
        ev = self.evidence()
        snap = dispatcher.snapshots.get(terminal.payload.get('snapshotLocalId')) if terminal.terminal == 'approval' else dispatcher.primary_snapshot()
        if terminal.terminal == 'approval' and ev.version_for(snap['invoice']['id']) != snap['evidenceVersion']:
            reruns = sum(1 for x in self.runs_for(r['id']) if x['requestVersion'] == r['version'] and x.get('reason') == 'stale_evidence')
            self.close_run(run, 'superseded', {'reason': 'stale_evidence'})
            self.event(r, 'analysis.discarded', {'runId': run_id, 'reason': 'evidence changed while the model was running', 'discardedTool': terminal.name})
            if reruns < MAX_STALE_RERUNS:
                self.schedule(r, 'evidence changed during inference')
            else:
                self.fallback_or_fail(r, run, {'kind': 'stale_evidence', 'detail': 'evidence kept changing during inference'}, outcome)
            return
        ai_status = 'live' if run['mode'] == 'live' else 'mocked'
        extraction = outcome.extraction
        snapshot = self.snapshot_record(r, ev, snap, dispatcher.notes_loaded.get(snap['customer']['id'], []) if snap else [],
                                        dispatcher.facts.get(snap['localId']) if snap else None)
        analysis = {'id': uid('analysis'), 'runId': run_id, 'requestVersion': r['version'], 'aiStatus': ai_status,
                    'modelId': model.get('modelId') if ai_status == 'live' else None, 'model': model if ai_status == 'live' else None,
                    'adapter': run['adapter'], 'promptVersion': run['promptVersion'], 'extraction': extraction,
                    'snapshot': snapshot, 'missingFields': [], 'brief': None, 'briefFormat': BRIEF_FORMAT, 'failure': None, 'stats': outcome.stats, 'createdAt': now()}
        r['customerId'] = snap['customer']['id'] if snap else None
        r['invoiceId'] = snap['invoice']['id'] if snap else None
        r['requestReason'] = extraction.get('reason')
        if terminal.terminal == 'clarification':
            r['requestedDueDate'] = None
            missing, question = self.with_invoice_choice(ev, dispatcher.invoice_hint, r['answers'], terminal.payload['missingFields'],
                                                         terminal.payload['question'])
            if snap and not is_open(snap['invoice']):   # stated as fully paid: the invoice is the issue, explained by code
                missing, question = [{'field': 'invoiceReference', 'reason': paid_text(snap['invoice']), 'neededFrom': 'staff'}], paid_text(snap['invoice'])
            analysis.update({'route': 'needs_information', 'missingFields': missing})
            r['task'] = {'id': uid('clarify'), 'kind': 'clarification', 'status': 'pending', 'requestVersion': r['version'],
                         'analysisId': analysis['id'], 'missingFields': missing, 'question': question, 'createdBy': caller}
            r['status'] = 'needs_information'
        else:
            facts = snapshot['facts']
            r['requestedDueDate'] = facts['requestedDueDate']
            statements, extras = terminal.payload['customerStatements'], extras or {}
            for q in extras.get('questions', ()):   # a question for staff that repeats the owner's private words goes to the owner
                if q['from'] == 'staff' and not staff_safe(q, extras.get('ownerQuotes', ())):
                    q.update({'from': 'owner', 'checks': q['checks'] + [STAFF_MOVED]})
            open_items = self.open_items(ev, extraction, dispatcher, snap, statements) + [{'kind': 'code_check', 'text': c, 'step': 'needs'} for c in extras.get('checks', ())]
            brief = render_brief(snap, facts, dispatcher.request_input, snapshot['confirmedNotes'], statements, open_items, caller,
                                 ev.fixture['version'], extras.get('contextShown', ()), extras.get('questions', ()))
            brief['suggestedOption'] = None   # recommendation boundary enforced here, whatever the model sent
            on = bool(self.meta('showSuggestions'))   # now, not when the step ran: the owner may have changed it meanwhile
            found = on and extras.get('suggestion')
            if found:
                self.put_suggestion(r, brief, found)
            analysis.update({'route': 'awaiting_owner', 'brief': brief,
                             'stats': {**outcome.stats, **extras.get('stats', {}), **(found or {}).get('stats', {})}})
            r['task'] = {'id': uid('approval'), 'kind': 'approval', 'status': 'pending', 'requestVersion': r['version'],
                         'analysisId': analysis['id'], 'snapshotId': snapshot['id'], 'evidenceVersion': snapshot['evidenceVersion'], 'mode': 'agent'}
            r['status'] = 'awaiting_owner'
        r['analysis'] = analysis
        self.trace(r, terminal.name, terminal.arguments, {'ok': True, 'task': r['task']}, caller, run_id)
        self.close_run(run, 'finished', {'route': analysis['route'], 'aiStatus': ai_status})
        self.save(r)
        self.event(r, 'analysis.finished', analysis)
        if terminal.terminal == 'approval' and on and not found:   # turned on while this case was being prepared
            self.schedule_suggest(r, 'suggestions turned on')

    @staticmethod
    def with_invoice_choice(ev, reference, answers, missing, question):
        """If the invoice number belongs to several customers and staff haven't chosen, ask staff to choose one
        (never pick the first match). The choice list and question are written by code."""
        if not reference or answers.get('invoiceId') or len(ev.owners(reference)) < 2:
            return missing, question
        field = {'field': 'invoiceId', 'neededFrom': 'staff', 'choices': invoice_choices(ev, reference),
                 'reason': 'Invoice ' + reference + ' exists for more than one customer. Choose which one this request is about.'}
        return ([field] + [m for m in missing if m['field'] not in ('invoiceReference', 'invoiceId')],
                'Invoice ' + reference + ' exists for more than one customer. Which customer sent this request?')

    def snapshot_record(self, r, ev, snap, notes, facts):
        record = {'id': uid('snapshot'), 'runLocalId': snap and snap['localId'], 'requestVersion': r['version'],
                  'asOfDate': ev.as_of.isoformat(), 'businessTimezone': ev.fixture['businessTimezone'],
                  'evidenceVersion': snap['evidenceVersion'] if snap else ev.global_version(),
                  'customer': snap['customer'] if snap else None, 'invoice': snap['invoice'] if snap else None,
                  'currentEffectiveDueDate': snap['currentEffectiveDueDate'] if snap else None,
                  'confirmedNotes': notes, 'resolution': snap and snap['resolution'], 'dueSource': snap and snap.get('dueSource'),
                  'sourceRefs': (snap['sourceRefs'] + [evidence_ref('note', n, ev.fixture, n['id']) for n in notes]) if snap else []}
        if facts:
            record['facts'] = facts
        return record

    @staticmethod
    def open_items(ev, extraction, dispatcher, snap, statements):
        """Missing or uncertain information for the owner, as typed items written by code."""
        items = []

        def add(kind, text):
            items.append({'kind': kind, 'text': text})
        if dispatcher.request_input['origin'] == 'staff_answer':
            add('staff_reported', 'Staff supplied the requested date in a clarification answer; it is not confirmed by the customer.')
        elif extraction.get('dateInterpretation') == 'relative':
            add('interpreted_date', 'The requested date was interpreted from the words "' + str(extraction.get('requestedDateText')) +
                '" relative to the fixed as-of date ' + display_date(ev.as_of.isoformat()) + '. Confirm it with the customer if unsure.')
        if dispatcher.answers.get('invoiceReference'):
            add('staff_reported', 'Staff supplied the invoice reference in a clarification answer.')
        if snap['resolution'] == 'staff_selection':
            add('staff_selected_invoice', 'Invoice ' + snap['invoice']['reference'] + ' exists for more than one customer; staff chose the one for '
                + snap['customer']['name'] + '.')
        if snap['resolution'] == 'single_open_invoice':
            add('inferred_invoice', "The message did not name an invoice; this is the customer's only open invoice.")
        if (snap.get('dueSource') or {}).get('recordType') == 'decision':
            original = snap['invoice']['originalDueDate']
            add('earlier_extension', ('An earlier approved extension moved the due date from ' + display_date(original) if original else
                                      'No original due date is on record; an earlier approved extension set the due date') +
                ' to ' + display_date(snap['currentEffectiveDueDate']) + '.')
        if not snap['currentEffectiveDueDate']:
            add('unknown_due_date', UNKNOWN_DUE_DATE)
        items.extend(amount_items(ev, snap['invoice']) + customer_items(ev, snap['customer']['id']))
        if statements:
            add('unverified_statements', "The customer's statements are quoted as written and have not been verified.")
        if not dispatcher.notes_loaded.get(snap['customer']['id']):
            add('no_owner_notes', 'There are no confirmed owner notes for this customer.')
        if extraction.get('otherRequests'):
            add('other_request', 'Model note: the message also asks for something this task does not handle (' + '; '.join(extraction['otherRequests']) + ').')
        if extraction.get('ambiguities'):
            add('model_note', 'Model note on the message: ' + '; '.join(extraction['ambiguities']))
        for check in extraction.get('checks') or []:
            add('code_check', check)
        if INSTRUCTION_LIKE.search(dispatcher.message_text):
            add('instruction_text', 'The message contains instruction-like text addressed to the system. It was treated as untrusted data and granted nothing.')
        add('fictional', 'Fictional data. No real owner delegation or approval policy has been validated.')
        return items

    def fallback_or_fail(self, r, run, failure, outcome=None):
        """The code-only fallback. If even that fails, its partial writes are undone and the request becomes a
        recoverable technical failure (preparation_failed) that waits for a person. A request opened from a confirmed action has no fallback:
        the manual one reads the invoice and date from answers and the message, which must never replace the confirmed ones.
        Lock and transaction held."""
        if r['intake'].get('structured') is not None:
            return self.preparation_failed(r, run, failure, 'confirmed_action')
        self.db.execute('SAVEPOINT fallback')
        try:
            self.fallback(r, run, failure, outcome)
        except Exception as exc:
            self.db.execute('ROLLBACK TO fallback')
            log('run', run['id'], 'fallback failed:', type(exc).__name__)
            self.preparation_failed(self.get(r['id']), self.run_record(run['id']) or run, failure, type(exc).__name__)
        finally:
            self.db.execute('RELEASE fallback')

    def preparation_failed(self, r, run, failure, fallback_error):
        """Keep the request and say what went wrong. No automatic retry: 'Prepare again' (reanalyse) is a person's choice."""
        run.update({'status': 'failed', 'finishedAt': now(), 'failure': failure, 'fallbackError': fallback_error})
        self.store_run(run)
        r.update({'status': 'preparation_failed', 'task': None, 'analysis': None, 'activeRunId': None,
                  'preparationFailure': {'kind': failure['kind'], 'detail': failure.get('detail'), 'fallbackError': fallback_error,
                                         'runId': run['id'], 'at': now()}})
        self.save(r)
        self.event(r, 'preparation.failed', r['preparationFailure'])

    def fallback(self, r, run, failure, outcome=None):
        """Code-built manual path after a failed or unavailable model run. Never labelled as live AI. Never for a request opened from a
        confirmed action: its invoice and date come from the action alone (structured_case), not from answers or the parser."""
        require(r['intake'].get('structured') is None, 409, 'CONFIRMED_FIELDS_LOCKED', LOCKED_FIELDS)
        ev = self.evidence()
        parsed = deterministic_extract(r['intake']['text'], ev.as_of)
        ref = ref_key(r['answers'].get('invoiceReference', parsed['invoiceReference'])) or None
        proposed = r['answers'].get('requestedDueDate', parsed['requestedDueDate'])
        chosen = ev.invoice(r['answers'].get('invoiceId')) if r['answers'].get('invoiceId') else None
        candidates = [chosen] if chosen else ev.invoices_by_ref(ref) if ref else []
        invoice = candidates[0] if len(candidates) == 1 else None   # several customers share the number: staff choose below
        customer = ev.customer(invoice['customerId']) if invoice else None
        due = ev.current_due(invoice) if invoice else None
        missing = []
        if len(candidates) > 1:
            missing = self.with_invoice_choice(ev, ref, r['answers'], [], '')[0]
        elif not invoice or not is_open(invoice):
            missing.append({'field': 'invoiceReference', 'reason': paid_text(invoice) if invoice else 'Enter one invoice number that is in the records.',
                            'neededFrom': 'staff'})
            invoice = customer = due = None
        try:
            parsed_date = calendar_date(proposed)
            valid_date = parsed_date > ev.as_of and (due is None or parsed_date > calendar_date(due))
        except (ValueError, TypeError):
            valid_date = False
        if not valid_date:
            missing.append({'field': 'requestedDueDate', 'reason': 'Provide a YYYY-MM-DD date later than the current due date' + (' (' + due + ')' if due else '') + '.', 'neededFrom': 'staff'})
        self.code_case(r, run, ev, invoice, customer, due, proposed, missing, valid_date, parsed=parsed, chosen=chosen, failure=failure, outcome=outcome)

    def structured_case(self, r, run=None):
        """The case of a request opened from a confirmed action, built by code alone (code_case) when it is opened and each time it is prepared again
        (records changed, Prepare again, a restart). The customer, invoice and requested date are r['intake']['structured']'s, fixed when a person
        confirmed the action: never an answer, the parser or a model, and nothing here writes them. If the records no longer support them (the invoice
        paid or gone, the date no longer after its due date) the case needs information that nobody can give: it says to withdraw the request and
        prepare a new action. run: the run being executed, if any. Lock and transaction held."""
        s = r['intake']['structured']
        ev = self.evidence()
        customer, invoice = ev.customer(s['customerId']), ev.invoice(s['invoiceId'])
        if invoice is not None and (customer is None or invoice['customerId'] != customer['id']):
            customer = invoice = None
        due, stop = invoice and ev.current_due(invoice), None
        if invoice is None:
            stop = 'the customer or the invoice is no longer in the records'
        elif not is_open(invoice):
            stop = 'invoice ' + invoice['reference'] + ' is no longer open: the records show it as paid'
        elif not due:
            stop = 'no due date is on record for the invoice now'
        elif not (calendar_date(s['requestedDueDate']) > max(ev.as_of, calendar_date(due))):
            stop = 'the requested date ' + display_date(s['requestedDueDate']) + ' is no longer after the invoice\'s current due date (' + display_date(due) + ') and the as-of date'
        self.code_case(r, run, ev, invoice, customer, due, s['requestedDueDate'], [], stop is None, structured=s,
                       stop=stop and 'This request was opened from ' + structured_origin(s) + ' for invoice ' + s['invoiceReference'] + ', but ' + stop.rstrip('.') +
                       '. Its customer, invoice and date are fixed and nobody can answer them here: withdraw this request and ' + ('prepare a new action' if s.get('actionId') else 'ask again') + ' from the current records.')

    def code_case(self, r, run, ev, invoice, customer, due, proposed, missing, valid_date, parsed=None, chosen=None, failure=None, outcome=None, structured=None, stop=None):
        """The case assembled by application code from an invoice, a customer and a requested date the caller settled: for the manual fallback
        (read from the message and the answers after a model failure: parsed, chosen, failure, outcome) or for a confirmed action (structured: only
        its frozen values; stop: why nobody can answer, else None). Both build the snapshot, the facts and the owner brief by the same code. They
        differ in who is named (aiStatus, adapter, caller, task mode), in whether the case's customer, invoice and date are set from this outcome
        (the fallback) or are never written here (structured: fixed at confirmation), and in the events. Lock and transaction held."""
        caller, run_id = 'application_code' if structured else 'manual_fallback', run and run['id']
        ref = ref_key(structured['invoiceReference']) if structured else ref_key(r['answers'].get('invoiceReference', parsed['invoiceReference'])) or None
        notes = ev.notes_for(customer['id'])[0] if customer else []
        snap = None
        if invoice:
            snap = {'localId': None, 'customer': customer, 'invoice': {**invoice, 'currentEffectiveDueDate': due}, 'currentEffectiveDueDate': due,
                    'dueSource': ev.due_source(invoice), 'evidenceVersion': ev.version_for(invoice['id']),
                    'resolution': 'confirmed_action' if structured else 'staff_selection' if chosen else 'invoice_reference',
                    'sourceRefs': [evidence_ref('invoice', invoice, ev.fixture, invoice['reference']), evidence_ref('customer', customer, ev.fixture, customer['displayCode'])]}
        facts = None
        if invoice and valid_date:
            facts = extension_facts(ev.as_of, invoice, due, proposed, snap['sourceRefs'])
        snapshot = self.snapshot_record(r, ev, snap, notes, facts)
        analysis = {'id': uid('analysis'), 'runId': run_id, 'requestVersion': r['version'], 'aiStatus': 'not_used' if structured else 'failed',
                    'modelId': None, 'model': None if structured else run.get('model'), 'adapter': STRUCTURED_ADAPTER if structured else 'manual-fallback-v0.2',
                    'promptVersion': None if structured else run.get('promptVersion'), 'failure': None if structured else failure,
                    'extraction': {'invoiceReference': structured['invoiceReference'], 'customerQuery': None, 'requestedDateText': structured['requestedDueDate'],
                                   'ambiguities': [], 'requestedDueDate': structured['requestedDueDate'], 'reasonQuote': structured['reason'], 'reason': structured['reason'],
                                   'otherRequests': [], 'origin': 'confirmed_action'} if structured else {**parsed, 'origin': 'deterministic_parser'},
                    'snapshot': snapshot, 'missingFields': missing, 'brief': None, 'briefFormat': BRIEF_FORMAT,
                    'stats': None if structured else outcome.stats if outcome else None, 'createdAt': now()}
        if not structured:   # a confirmed action's customer, invoice and date are never written from here
            r['customerId'] = customer['id'] if customer else None
            r['invoiceId'] = invoice['id'] if invoice else None
            r['requestedDueDate'] = proposed if facts else None
        self.trace(r, 'getInvoiceFacts', {'invoiceReference': ref}, invoice, caller, run_id)
        self.trace(r, 'getConfirmedKnowledge', {'customerId': r['customerId']}, notes, caller, run_id)
        if missing or stop:
            analysis['route'] = 'needs_information'
            r['task'] = {'id': uid('clarify'), 'kind': 'clarification', 'status': 'pending', 'requestVersion': r['version'],
                         'analysisId': analysis['id'], 'missingFields': missing, 'createdBy': caller,
                         'question': stop or 'The AI couldn\'t prepare this case. Enter the details below and the app will check them against the records.'}
            r['status'] = 'needs_information'
            self.trace(r, 'createClarification', {'missingFields': missing}, r['task'], caller, run_id)
        else:
            self.trace(r, 'calculateExtension', {'snapshotId': snapshot['id'], 'requestedDueDate': proposed}, facts, 'application_code', run_id)
            analysis['route'] = 'awaiting_owner'
            if structured:
                request_input = {'value': proposed, 'origin': 'confirmed_action', 'quote': None, 'interpretation': 'confirmed', 'interpretedBy': 'application_code',
                                 'actionId': structured.get('actionId'), 'caseId': structured.get('caseId')}
                open_items = [{'kind': 'confirmed_action', 'text': 'Opened from ' + structured_origin(structured) + ': ' + (
                    'a person confirmed this customer, invoice and requested date on a proposal.' if structured.get('actionId') else
                    'the assistant resolved this request under the Owner\'s delegation policy, with this customer, invoice and requested date.') +
                    ' No model read this request; application code built this case from these values.'},
                              *amount_items(ev, invoice), *customer_items(ev, invoice['customerId']),
                              *([{'kind': 'instruction_text', 'text': 'The reason contains instruction-like text addressed to the system. It was treated as untrusted data and granted nothing.'}]
                                if INSTRUCTION_LIKE.search(structured['reason'] or '') else []),
                              {'kind': 'fictional', 'text': 'Fictional data. No real owner delegation or approval policy has been validated.'}]
            else:
                request_input = {'value': proposed, 'origin': 'staff_answer' if 'requestedDueDate' in r['answers'] else 'customer_message',
                                 'quote': proposed, 'interpretation': 'explicit', 'interpretedBy': 'deterministic_parser'}
                open_items = [{'kind': 'ai_failed', 'text': 'AI case preparation failed (' + failure['kind'] + '). Application code assembled this case '
                               'from fictional records with the basic parser; customer statements were not extracted.'},
                              *([] if due else [{'kind': 'unknown_due_date', 'text': UNKNOWN_DUE_DATE}]), *amount_items(ev, invoice),
                              *customer_items(ev, invoice['customerId']),
                              *([{'kind': 'staff_selected_invoice', 'text': 'Invoice ' + invoice['reference'] + ' exists for more than one customer; staff chose the one for '
                                  + customer['name'] + '.'}] if chosen else []),
                              {'kind': 'fictional', 'text': 'Fictional data. No real owner delegation or approval policy has been validated.'}]
            analysis['brief'] = render_brief(snap, facts, request_input, notes, [], open_items, caller, ev.fixture['version'])
            r['status'] = 'awaiting_owner'
            r['task'] = {'id': uid('approval'), 'kind': 'approval', 'status': 'pending', 'requestVersion': r['version'],
                         'analysisId': analysis['id'], 'snapshotId': snapshot['id'], 'evidenceVersion': snapshot['evidenceVersion'],
                         'mode': 'structured' if structured else 'manual_fallback'}
            self.trace(r, 'prepareApprovalTask', {'snapshotId': snapshot['id']}, r['task'], caller, run_id)
        r['analysis'] = analysis
        if run and run['status'] == 'running':
            self.close_run(run, 'finished', {'route': analysis['route'], 'aiStatus': 'not_used'}) if structured else self.close_run(run, 'failed', {'failure': failure})
        self.save(r)
        if not structured:
            self.event(r, 'analysis.failed', {'runId': run['id'], 'failure': failure, 'fallback': analysis['route']})
        self.event(r, 'analysis.finished', analysis)

    def wait_settled(self, request_id, timeout):
        """Wait (releasing the lock) until the request leaves received/analysing and no suggestion step is running for it, or timeout."""
        deadline = time.monotonic() + timeout
        while self.get(request_id)['status'] in ACTIVE_STATES or any(x['status'] == 'running' and x.get('kind') == 'suggest'
                                                                      for x in self.runs_for(request_id)):
            left = deadline - time.monotonic()
            if left <= 0:
                return
            self.settled.wait(left)

    def wait_seconds(self):
        if self.inline_wait is not None:
            return self.inline_wait
        return 0 if self.agent_mode == 'live' else 10


def guarded(step, failed, **arguments):
    """Run one agent step. A model failure is the step's own to handle; any other fault in it costs that step's result (failed),
    never the case."""
    try:
        return step(**arguments)
    except Exception as exc:
        log('agent step', step.__name__, 'failed:', type(exc).__name__, exc)
        return failed


def suggestion_inputs(brief, questions, context, answers):
    """What the suggestion step is given: the brief's code-written facts and dates, what has been said about the customer and
    the case (context_for), the case's staff answers and its open questions. Cites may name a line, a fact or a decided case,
    never a line kept at a decision (source 'decision'): the owner's words about another case are not an approval of this one."""
    value = {f['key']: f['value'] for f in brief['facts']}
    kept = {x['id'] for x in context['lines'] if x.get('source') == 'decision'}

    def day(key):
        return value.get(key) and calendar_date(value[key])
    return {'facts_text': facts_for_model(brief['summary'], brief['facts']), 'lines': context['lines'], 'decisions': context['decisions'],
            'answers': answers, 'open_questions': [q for q in questions if q['status'] == 'open'], 'as_of': day('asOfDate'),
            'current_due': day('currentEffectiveDueDate'), 'requested': day('requestedDueDate'),
            'loaded_ids': ({x['id'] for x in context['lines']} - kept) | set(value) | {x['requestId'] for x in context['decisions']},
            'decision_line_ids': kept, 'day_limits': day_limits(context['lines'])}


STILL_HOLDS = "On {} you said '{}'. Does that still hold for this request?"


def still_holds(lines, questions, today):
    """The needs step's own questions, after the model's (questions): for each line the case cites (one of its questions quotes it or
    is answered by it, or a day limit comes from it) that the owner said, has not ended, and is an expectation said before today or
    any line said more than 30 days ago, one question (from 'code', asked of the owner) whether it still holds for this request; one
    per line. A line the owner has answered that for (an answer whose source names it, owner_question) is asked as answered by it,
    so the check never reopens when the case is prepared again."""
    day, old = today.isoformat(), (today - timedelta(days=30)).isoformat()
    cited = {q['answeredBy'] for q in questions} | {x for x, _ in day_limits(lines)} | \
        {x['id'] for x in lines for q in questions if appears_in(x['quote'], q['question'] + ' ' + q['why'])}
    answers = {x['checkedLineId']: x['id'] for x in lines if x.get('checkedLineId')}
    picked = {x['id']: x for x in lines if x['id'] in cited and x['role'] == 'owner' and x['saidOn'] and not x['expired'] and
              (x['saidOn'] < old or x['kind'] == 'expectation' and x['saidOn'] < day)}
    return [{'id': uid('q'), 'need': 'Whether this still holds', 'from': 'code', 'kind': 'check', 'lineId': x['id'],
             'why': 'It was said more than 30 days ago.' if x['saidOn'] < old else 'It expects something, and was said before this request.',
             'question': STILL_HOLDS.format(display_date(x['saidOn']), ' '.join(x['quote'].split())), 'answeredBy': answers.get(x['id']),
             'status': 'answered' if x['id'] in answers else 'open', 'checks': [], 'createdBy': 'application_code'} for x in picked.values()]


def day_limits(lines):
    """[(line id, max days)]: the limits the owner stated in their own words ("up to 14 days") in what context_for loaded, which
    loads case lines of this case and customer lines of this customer only; an ended line no longer limits."""
    return [(x['id'], int(m.group(1))) for x in lines if (x.get('source') == 'answer' or x['kind'] == 'guidance')
            and x['scope']['kind'] in ('case', 'customer') and not x.get('expired') for m in [DAY_LIMIT.search(x['quote'])] if m]


def suggestion_step(adapter, caller, inputs, timeout):
    return guarded(prepare_suggestion, {'suggestion': None, 'status': 'failed', 'withheldBecause': [], 'checks': [STEP_FAILED], 'stats': {}},
                   adapter=adapter, caller=caller, timeout=timeout, **inputs)


DUE_FIELDS = ('originalDue', 'originalDueText', 'dueNow', 'dueNowText', 'dueNowFrom')   # summary's due dates, also in the case's situation


def decision_view(d, role=None, basis=None):
    """The recorded decision as both roles may read it: the outcome, the date it moved to, the days, the reason recorded, the day it was
    made (never its time), who decided (decisionSource) and whether it followed the recommendation. The reason is the recorded one, not
    the owner's private conversation, so staff have it; the recommendation as it stood is the owner's alone (role 'owner'). basis: 'full'
    adds the frozen basis of the decision (the assessment it was made on, with its calculation details, staff's words for staff),
    'summary' its basisSummary and assessmentVersion; None neither (lists)."""
    if not d:
        return None
    frozen = d.get('basis')
    if basis == 'full':
        return {**decision_view(d, role), 'basis': frozen if role == 'owner' else staff_plain(frozen)}
    if basis == 'summary':
        return {**decision_view(d, role), 'assessmentVersion': frozen and frozen['assessmentVersion'], 'basisSummary': basis_summary((frozen or {}).get('basis'))}
    day = d['decidedAt'][:10]
    out = {'outcome': d['outcome'], 'approvedDueDate': d.get('approvedDueDate'),
           'approvedDueDateText': d.get('approvedDueDate') and display_date(d['approvedDueDate']),
           'days': d.get('approvedExtensionDays'), 'approvedExtensionDays': d.get('approvedExtensionDays'), 'reason': d['reason'],
           'decidedOn': day, 'decidedOnText': display_date(day), 'decisionSource': d.get('decisionSource'),
           **({k: d[k] for k in ('actorName', 'actorRole')} if d.get('actorName') else {}),
           'followedRecommendation': d.get('followedRecommendation'),
           **({'authority': {'source': d['authority'].get('source'), 'policyVersion': d['authority']['policyVersion']}, 'delegationCaseId': d.get('delegationCaseId')}
              if (d.get('authority') or {}).get('policyVersion') is not None else {})}
    return {**out, 'recommendation': d.get('recommendation'), **({'aiRecommendation': d['aiRecommendation']} if d.get('aiRecommendation') else {})} if role == 'owner' else out


def summary(r, records=None):
    """A request in the request list's shape, with its due dates: originalDue, the invoice's due date when the case was prepared, and
    dueNow, the date an approval moved it to (dueNowFrom 'decision'), else that one ('invoice'), each also in words. With records
    (every request), also ordinal: its place among the open requests on its invoice, oldest first (None before the invoice is
    identified), and flags: the case's own and, for an open request, a duplicateIntake for each earlier open one on the same invoice
    asking for the same date. That flag is informational: intake never refuses or merges a request."""
    analysis = r.get('analysis') or {}
    snapshot = analysis.get('snapshot') or {}
    decision = r.get('decision') or {}
    original = (snapshot.get('facts') or {}).get('currentEffectiveDueDate')
    moved = decision.get('approvedDueDate') if decision.get('outcome') == 'approve' else None
    out = {'id': r['id'], 'status': r['status'], 'version': r['version'], 'createdAt': r['createdAt'],
           'invoiceReference': (snapshot.get('invoice') or {}).get('reference'), 'customerName': (snapshot.get('customer') or {}).get('name'),
           'customerId': (snapshot.get('customer') or {}).get('id'), 'invoiceId': r.get('invoiceId'),
           'requestedDueDate': r.get('requestedDueDate'), 'outcome': decision.get('outcome'), 'approvedDueDate': decision.get('approvedDueDate'),
           'aiStatus': analysis.get('aiStatus'), 'excerpt': ' '.join(r['intake']['text'].split())[:120],
           'originalDue': original, 'originalDueText': original and display_date(original), 'dueNow': moved or original,
           'dueNowText': (moved or original) and display_date(moved or original), 'dueNowFrom': 'decision' if moved else 'invoice',
           'withStaff': returned(r) and r['withStaff']['kind'] or None, 'withStaffWhy': returned(r) and r['withStaff']['why'] or None,
           'withdrawnReason': (r.get('withdrawn') or {}).get('reason'), 'decision': decision_view(decision),
           'confirmedAction': (r['intake'].get('structured') or {}).get('actionId'),
           'delegationCaseId': (r.get('delegation') or {}).get('caseId')}   # set when staff confirmed an action to open it (its request is the owner's alone to decide)
    if records is not None:
        # shortcut: each summary scans every request; group them by invoice once if requests grow into the thousands
        opened = lambda x: x['status'] in STATES_BEFORE_DECISION
        earlier = [x for x in records if r.get('invoiceId') and x.get('invoiceId') == r['invoiceId'] and x['id'] != r['id'] and opened(x)
                   and (x['createdAt'], x['id']) < (r['createdAt'], r['id'])]
        out.update({'ordinal': len(earlier) + 1 if r.get('invoiceId') else None,
                    'flags': (r.get('flags') or []) + [{'kind': 'duplicateIntake', 'requestId': x['id']} for x in earlier if opened(r) and
                                                       r.get('requestedDueDate') and x.get('requestedDueDate') == r['requestedDueDate']]})
    return out


def case_label(case, role):
    """Where a case stands for this role, in the words of the case list (requests.js statusOf)."""
    status = case['status']
    if status == 'withdrawn':
        return 'Withdrawn'
    if status == 'needs_information':
        return 'Needs your answer' if role == 'staff' else 'Waiting for staff'
    if case.get('withStaff') and status == 'awaiting_owner':   # the owner's answer sent it back (answerConcern)
        return 'Waiting on staff'
    if status == 'awaiting_owner':
        return 'Needs your decision' + (', prepared without AI' if case['aiStatus'] == 'failed' else '') if role == 'owner' else 'With the owner'
    return {'received': 'Preparing', 'analysing': 'Preparing', 'decided': 'Saving the decision', 'preparation_failed': "Couldn't prepare"}.get(
        status, 'Declined' if case['outcome'] == 'decline' else 'Approved to ' + display_date(case['approvedDueDate']).rsplit(' ', 1)[0] if case['approvedDueDate'] else 'Approved')   # no year, as statusOf


ANSWER_KINDS = ('needs_info', 'explain', 'guidance')   # answerConcern; a final decision is prepareDecision


def open_concerns(r):
    """The concerns staff raised that the owner has not answered since (answerConcern starts the rounds again)."""
    return (r.get('concerns') or [])[r.get('roundsFrom', 0):]


def concerned(r):
    """Whether staff raised a concern on this case that the owner has not answered, while it is prepared and not yet decided (raiseConcern)."""
    return bool(open_concerns(r)) and r['status'] in STATES_BEFORE_DECISION - ACTIVE_STATES


def returned(r):
    """Whether the owner's answer (answerConcern) sent this case back to staff and they have not raised a concern since: it waits on staff."""
    return bool(r.get('withStaff')) and r['status'] in STATES_BEFORE_DECISION - ACTIVE_STATES


def held(r):
    """Whether the owner answered a concern and kept the decision with themselves (answerConcern next 'owner'), and staff have not raised a
    concern since: the case still waits for the owner's decision, with the answer on it."""
    return bool(r.get('withOwner')) and r['status'] in STATES_BEFORE_DECISION - ACTIVE_STATES


def owner_pending(r, role):
    """Why a held case waits for the owner, in words for this role."""
    return r['withOwner']['why'] if role == 'owner' else "the owner's decision is still pending"


def waiting_on(r, role):
    """Who acts next on a case: 'owner' while it waits for the owner's decision or staff raised a concern on it; 'staff' while it
    needs staff's answer, could not be prepared (staff try again, as the case list marks it theirs), or has an open question asked of
    staff; this role first when both may act; 'none' while the agent prepares it or the decision is saved, and once it is decided."""
    asked = r['status'] == 'awaiting_owner' and any(q['from'] == 'staff' and q['status'] == 'open'
                                                    for q in (((r.get('analysis') or {}).get('brief') or {}).get('questions') or ()))
    on = {'awaiting_owner': ['owner'] + ['staff'] * asked, 'needs_information': ['staff'], 'preparation_failed': ['staff']}.get(r['status'], [])
    on = on + ['owner'] * (concerned(r) and 'owner' not in on)
    on = ['staff'] if returned(r) else on   # the owner answered a concern: the next person is staff, for both roles' queues
    return role if role in on else on[0] if on else 'none'




def staff_plain(a):
    """An assessment as staff read it: the owner-worded no-limit sentence is the neutral one, in its calculation details too (basis).
    Neutralised on read; the stored copy is the owner's. Also a decision's frozen basis, which has the same parts."""
    if not a:
        return a
    plain = lambda t: STAFF_NO_LIMIT if t == NO_LIMIT else t
    p, rec = a['policy'], a['recommendation']
    return {**a, 'policy': {**p, 'checks': [{**x, 'sentence': plain(x['sentence'])} for x in p['checks']], 'summaryText': p['summaryText'].replace(NO_LIMIT, STAFF_NO_LIMIT)},
            'recommendation': {**rec, 'reasons': [plain(x) for x in rec['reasons']]}, **({'basis': staff_basis(a['basis'])} if a.get('basis') else {})}


def staff_basis(b):
    """Calculation details as staff read them: the same records and numbers as the owner's, the no-limit sentence in staff's words."""
    if not b:
        return b
    plain = lambda t: STAFF_NO_LIMIT if t == NO_LIMIT else t
    return {**b, 'checks': [{**x, 'sentence': plain(x['sentence'])} for x in b['checks']],
            'recommendation': {**b['recommendation'], 'reasons': [plain(x) for x in b['recommendation']['reasons']]}}


# ---------------------------------------------------------------- calculation details (the basis of an assessment)

KEEP_BASES = 3   # earlier assessments of a case whose calculation details stay readable (an older card asks for its own version)
RECORDED_STATUS = {'applied': None, 'waiting': 'applied when the invoice is issued', 'undated': 'held against an invoice with no issue date',
                   'stated': 'the stated amount still owed is not reduced', 'unplaced': 'the invoice is not in the records: it reduces nothing'}
STATED_SOURCE = {'file': 'an import', 'correction': 'a correction', 'opening_balance': 'the opening balance'}   # as amount_items words it
ORIGIN_KIND = {'file': 'import', 'manual': 'manual', 'answer': 'manual', 'correction': 'correction'}


def basis_money(m, template):
    """Minor units in words, a credit (below zero) with its sign as the pages write it ("AUD −60.00")."""
    text = money_text({'minorUnits': str(abs(m)), **template})
    return text.replace(' ', ' \u2212', 1) if m < 0 else text


def assessment_basis(ev, customer, r, records, features, checks, measured, rec, authority, template, today):
    """The calculation details of an assessment (behaviour.CALCULATION_VERSION), from the computation that produced it: the records the
    replay read and what it did with each, in order, from its own trail (assessment_facts' trail, recorded by the replay's loop), what it
    could not place or read and what it left out, each with its effect; the exposure up to and including today against the history
    strictly before it; the policy the checks compared against, each check with the values it compared (checks_for's measured); and
    the recommendation. Words are written here from those values; nothing is worked out again. records: the customer's {invoices,
    payments, allocations, openingBalances} as the assessment read them, every status. Every link is a records route."""
    money = lambda m: basis_money(m, template)
    day = lambda iso: iso and display_date(iso)
    cid, f = customer['id'], features
    t, prior = f['trail']['current'], f['trail']['prior']
    links = {'customer': '#/customers/' + cid, 'invoices': '#/customers/' + cid + '/invoices', 'payments': '#/customers/' + cid + '/payments',
             'balance': '#/customers/' + cid + '/balance', 'case': r and '#/case/' + r['id']}
    live = lambda xs: [x for x in xs if x.get('status', 'active') == 'active']
    invs, pays = {i['id']: i for i in live(records['invoices'])}, {p['id']: p for p in live(records['payments'])}
    inv = lambda iid: {'invoiceId': iid, 'reference': (invs.get(iid) or {}).get('reference'), 'link': links['invoices'] if iid in invs else None}
    pay = lambda pid: {'paymentId': pid, 'reference': (pays.get(pid) or {}).get('reference'), 'link': links['payments']}
    trail = []
    for e in t['events']:
        on = {'dateText': day(e['date']), 'link': links['invoices' if e['kind'] == 'invoice' else 'payments']}
        if e['kind'] == 'invoice':
            parts = [{'label': 'Recorded allocation', 'amount': x['amount'], 'amountText': money(x['amount']), 'from': pay(x['paymentId'])} for x in e['fromRecordedAllocations']]
            parts += [{'label': 'Opening credit', 'amount': e['fromOpeningCredit'], 'amountText': money(e['fromOpeningCredit'])}] if e['fromOpeningCredit'] else []
            parts += [{'label': 'Customer credit held', 'amount': e['fromCustomerCredit'], 'amountText': money(e['fromCustomerCredit'])}] if e['fromCustomerCredit'] else []
            trail.append({**e, **on, 'totalText': money(e['total']), 'originalDueText': day(e['originalDueDate']) or 'No due date', 'appliedOnIssue': parts,
                          'leftAfterText': money(e['leftAfter'])})
        else:
            trail.append({**e, **on, 'amountText': money(e['amount']),
                          'recorded': [{**x, **inv(x['invoiceId']), 'amountText': money(x['amount']), 'statusText': RECORDED_STATUS[x['status']]} for x in e['recorded']],
                          'oldestFirst': [{**x, **inv(x['invoiceId']), 'amountText': money(x['amount'])} for x in e['oldestFirst']],
                          'toOpeningText': money(e['toOpening']), 'toCreditText': money(e['toCredit']),
                          'lateText': 'Received while something was past due' if e['late'] else 'Nothing was past due when it was received'})
    left, stated, undated = {x['id']: x['left'] for x in t['invoices']}, {x['id']: x for x in t['stated']}, {x['id']: x for x in t['undated']}
    unreadable, unplaced = {x['id'] for x in t['unreadableInvoices']}, {x['id'] for x in t['unplacedPayments']}
    invoice_rows = []
    for i in invs.values():
        iid = i['id']
        counted = 'issued' if iid in left else 'stated' if iid in stated else 'undated' if iid in undated else 'unreadable' if iid in unreadable else None
        if counted is None:   # left out (in the opening balance, or dated after today): listed under excluded
            continue
        remainder = {'issued': left.get(iid), 'stated': (stated.get(iid) or {}).get('amount'), 'undated': (undated.get(iid) or {}).get('open'), 'unreadable': None}[counted]
        moved, src, owed = ev.effective_due.get(iid), ev.due_sources.get(iid), i.get('outstandingAmount')
        by_decision = bool(moved and src and moved == src['approvedDueDate'])
        effective = moved or i.get('originalDueDate')
        invoice_rows.append({
            'id': iid, 'reference': i.get('reference'), 'link': links['invoices'], 'issueDate': i.get('issueDate'), 'issueText': day(i.get('issueDate')) or 'No issue date',
            'originalDueDate': i.get('originalDueDate'), 'originalDueText': day(i.get('originalDueDate')) or 'No due date',
            'effectiveDueDate': effective, 'effectiveDueText': day(effective) or 'No due date',
            'effectiveDueSource': {'kind': 'decision', 'requestId': src['requestId'], 'link': '#/case/' + src['requestId'], 'decidedOn': src['decidedAt'][:10],
                                   'decidedOnText': day(src['decidedAt'][:10]), 'by': decider_words(src)} if by_decision else {'kind': 'invoice'},
            'total': i.get('total') and int(i['total']['minorUnits']), 'totalText': money(int(i['total']['minorUnits'])) if i.get('total') else 'Not recorded',
            'stated': owed and {'amount': int(owed['minorUnits']), 'amountText': money(int(owed['minorUnits'])), 'asOf': i.get('outstandingAsOf'),
                                'asOfText': day(i.get('outstandingAsOf')), 'source': i.get('outstandingSource') or 'manual',
                                'sourceText': STATED_SOURCE.get(i.get('outstandingSource'), 'manual entry')},
            'counted': counted, 'remainder': remainder, 'remainderText': UNKNOWN if remainder is None else money(remainder),
            'remainderBasis': {'issued': 'derived: the total less what was applied to it', 'stated': 'stated', 'unreadable': 'unknown',
                               'undated': 'derived: the total less recorded allocations' if i.get('total') else 'stated'}[counted]})
    events = {e['id']: n for n, e in enumerate(trail) if e['kind'] == 'payment'}   # a payment row points at its step of the trail
    allocs = [a for a in live(records['allocations']) if a['paymentId'] in pays]
    payment_rows = []
    for p in pays.values():
        step = events.get(p['id'])
        if step is None and p.get('receivedDate'):   # dated after today or part of the opening balance: listed under excluded
            continue
        mine = [a for a in allocs if a['paymentId'] == p['id']]
        payment_rows.append({
            'id': p['id'], 'reference': p.get('reference'), 'link': links['payments'], 'receivedDate': p.get('receivedDate'), 'receivedText': day(p.get('receivedDate')) or 'No received date',
            'amount': int(p['amount']['minorUnits']), 'amountText': money(int(p['amount']['minorUnits'])), 'enteredText': entered_text(p),
            'placed': 'replayed' if step is not None else 'unplaced' if p['id'] in unplaced else 'undated',
            'step': step,   # trail[step]: where each part of it went (recorded, oldest first, to the opening balance, to customer credit)
            'note': None if step is not None else EFFECTS['unplacedPayment'] if p['id'] in unplaced else
            'No received date: only its recorded allocations count, against the invoices they were allocated to.',
            **({} if step is not None else {'recordedAllocations': [{**inv(a['invoiceId']), 'amount': int(a['amount']['minorUnits']), 'amountText': money(int(a['amount']['minorUnits']))} for a in mine]})})
    allocation_rows = []
    for a in allocs:
        by = a if (a.get('setBy') or a.get('origin') or {}).get('kind') in ORIGIN_KIND else pays[a['paymentId']]   # as invoice_figures: else the payment's
        allocation_rows.append({'id': a['id'], 'paymentId': a['paymentId'], 'paymentReference': pays[a['paymentId']].get('reference'), **inv(a['invoiceId']),
                                'amount': int(a['amount']['minorUnits']), 'amountText': money(int(a['amount']['minorUnits'])),
                                'origin': {'kind': ORIGIN_KIND.get((by.get('setBy') or by.get('origin') or {}).get('kind'), 'unknown'), 'text': entered_text(by)}})
    left_out = {(x['kind'], x['id']) for x in t['excluded']}
    opening_rows = [{'id': o['id'], 'asOf': o['asOf'], 'asOfText': day(o['asOf']), 'amount': int(o['amount']['minorUnits']), 'amountText': money(int(o['amount']['minorUnits'])),
                     'kind': 'credit' if int(o['amount']['minorUnits']) < 0 else 'owing', 'link': links['balance'], 'counted': ('openingBalance', o['id']) not in left_out}
                    for o in live(records['openingBalances'])]
    n = plural_text
    unknown_due, overdue, oldest = f.get('noDueDate', 0), f['overdue_before_m'], f['max_days_past_due_before']
    beside = '; ' + UNKNOWN + ' for ' + n(unknown_due, 'open invoice') + ' with no due date'
    exposure = [
        {'key': 'debt', 'name': 'Owed', 'value': f['debt_before_m'], 'text': money(f['debt_before_m']),
         'note': ('Leaves out ' + n(f['unreadableInvoices'], 'invoice') + ' that cannot be read.') if f.get('unreadableInvoices') else None},
        {'key': 'overdue', 'name': 'Overdue', 'value': None if unknown_due and not overdue else overdue,
         'text': (money(overdue) + beside if overdue else UNKNOWN) if unknown_due else money(overdue) if overdue else 'Nothing overdue'},
        {'key': 'oldestDaysPastDue', 'name': 'Oldest past due', 'value': None if unknown_due and not oldest else oldest,
         'text': (n(oldest, 'day') + beside if oldest else UNKNOWN) if unknown_due else n(oldest, 'day') if oldest else 'Nothing past due'},
        {'key': 'remainingOpening', 'name': 'Remaining opening balance', 'value': t['remainingOpening'], 'text': money(t['remainingOpening'])},
        {'key': 'creditHeld', 'name': 'Customer credit held', 'value': t['creditHeld'], 'text': money(t['creditHeld'])},
        {'key': 'invoices', 'name': 'Invoices counted', 'value': f.get('current_invoice_documents'), 'text': str(f.get('current_invoice_documents'))}]
    rows = check_rows(checks, measured, template)
    late_unknown = any(x['key'] == 'late_history' and x['result'] == 'unknown' for x in rows)
    history = [
        {'key': 'invoices', 'name': 'Invoices', 'value': prior['prior_invoice_documents'], 'text': str(prior['prior_invoice_documents'])},
        {'key': 'billed', 'name': 'Billed (recorded totals)', 'value': prior['prior_billed_m'], 'text': money(prior['prior_billed_m'])},
        {'key': 'received', 'name': 'Received', 'value': prior['prior_received_m'], 'text': money(prior['prior_received_m'])},
        {'key': 'receipts', 'name': 'Payments received', 'value': prior['prior_receipt_count'], 'text': str(prior['prior_receipt_count'])},
        {'key': 'lateReceipts', 'name': 'Received while something was past due', 'value': prior['lateReceipts'],
         'text': (str(prior['lateReceipts']) + ' of ' + str(prior['prior_receipt_count'])) if prior['prior_receipt_count'] else 'No earlier payments',
         'note': 'Cannot be fully established: a payment has no received date or an open invoice has no due date.' if late_unknown else None},
        {'key': 'relationshipDays', 'name': 'Records cover', 'value': prior['observed_relationship_days'],
         'text': 'No records yet' if prior['observed_relationship_days'] is None else n(prior['observed_relationship_days'], 'day')},
        {'key': 'lastReceipt', 'name': 'Last payment', 'value': prior['days_since_prior_receipt'],
         'text': 'No earlier payment' if prior['days_since_prior_receipt'] is None else n(prior['days_since_prior_receipt'], 'day') + ' before this date'},
        {'key': 'terms', 'name': 'Terms (median)', 'value': prior['credit_term_days'], 'text': UNKNOWN if prior['credit_term_days'] is None else n(prior['credit_term_days'], 'day')}]
    pay_amount = lambda pid: (pays.get(pid) or {}).get('amount')
    missing = ([{'kind': 'invoice', **inv(x['id']), 'why': 'No invoice total; only a stated amount still owed', 'effect': x['effect'], 'amountText': money(x['amount'])} for x in t['stated']] +
               [{'kind': 'invoice', **inv(x['id']), 'why': 'No issue date', 'effect': x['effect'], 'amountText': money(x['open'])} for x in t['undated']] +
               [{'kind': 'invoice', **inv(x['id']), 'why': 'No due date', 'effect': x['effect'], 'amountText': money(x['amount'])} for x in t['openNoDueDate']] +
               [{'kind': 'payment', **pay(x['id']), 'why': 'No received date and no recorded allocation', 'effect': x['effect'],
                 'amountText': money(int(pay_amount(x['id'])['minorUnits'])) if pay_amount(x['id']) else UNKNOWN} for x in t['unplacedPayments']] +
               [{'kind': 'allocation', **pay(x['paymentId']), 'invoiceId': x['invoiceId'], 'why': 'Allocated to an invoice that is not in the records', 'effect': x['effect'],
                 'amountText': money(x['amount'])} for x in t['unplacedAllocations']] +
               [{'kind': 'invoice', **inv(x['id']), 'why': 'No total and no amount still owed', 'effect': x['effect'], 'amountText': UNKNOWN} for x in t['unreadableInvoices']] +
               ([{'kind': 'invoice', 'invoiceId': r.get('invoiceId'), 'reference': None, 'link': links['case'], 'why': 'The invoice this request is about is not among the current records',
                  'effect': OWN_MISSING, 'amountText': UNKNOWN}] if f.get('ownMissing') and r else []))
    fifo = sum(x['amount'] for e in t['events'] if e['kind'] == 'payment' for x in e['oldestFirst'])
    assumptions = ([{'key': 'oldest_first', 'amount': fifo, 'text': 'Applied oldest first (an assumption, not a record): ' + money(fifo) + ' of payments that no record allocates.'}] if fifo else []) + \
        ([{'key': 'opening_age', 'text': 'An opening balance has no known age: it counts as owed and never as overdue, and only what is left after every open invoice is paid reduces it.'}]
         if t['opening']['owingAtStart'] else []) + \
        ([{'key': 'customer_credit', 'text': 'Money received while nothing was open to pay is held as customer credit and applied to the invoices issued after it.'}]
         if any(e.get('toCredit') or e.get('fromCustomerCredit') for e in t['events']) else []) + \
        [{'key': 'original_due', 'text': 'Overdue is judged by the due dates recorded on the invoices, not by extensions already granted.'}]
    page = {'invoice': 'invoices', 'payment': 'payments', 'openingBalance': 'balance', 'allocation': 'payments'}
    excluded = [{**x, 'link': links[page[x['kind']]]} for x in t['excluded']]
    for kind, key, word in (('invoice', 'invoices', 'invoice'), ('payment', 'payments', 'payment'), ('allocation', 'allocations', 'allocation'), ('openingBalance', 'openingBalances', 'opening balance')):
        gone = sum(1 for x in records[key] if x.get('status', 'active') != 'active')
        if gone:
            excluded.append({'kind': kind, 'id': None, 'reference': None, 'count': gone, 'reason': 'inactive', 'link': links[page[kind]],
                             'effect': n(gone, word) + (' was' if gone == 1 else ' were') + ' removed or reverted: not counted.'})
    a = authority
    policy_rows = [
        {'key': 'staffMayApproveUpToDays', 'name': 'Staff may approve up to', 'text': n(a['staffMayApproveUpToDays'], 'day') if a['staffMayApproveUpToDays'] else 'Not set (staff may approve nothing)'},
        {'key': 'maxOutstanding', 'name': 'Most owed for staff to act', 'text': a.get('maxOutstandingText') or 'Not set'},
        {'key': 'requireNothingOverdue', 'name': 'Nothing else overdue', 'text': 'Required' if a['requireNothingOverdue'] else 'Not required'},
        {'key': 'maxPriorLateShare', 'name': 'Earlier late payments', 'text': 'Not set' if a['maxPriorLateShare'] is None else 'A fraction of at most ' + format(a['maxPriorLateShare'], 'g')},
        {'key': 'hardRules', 'name': 'Hard rules (a failing check declines)', 'text': ', '.join(CHECK_NAMES.get(x, x) for x in a['hardRules']) or 'None'},
        {'key': 'maxConcernRounds', 'name': 'Concern rounds before the owner takes it', 'text': str(a['maxConcernRounds'])}]
    own = r and r.get('invoiceId') and next((i for i in records['invoices'] if i['id'] == r['invoiceId']), None)
    return {'calculationVersion': CALCULATION_VERSION, 'assessmentVersion': None, 'asOf': today.isoformat(), 'asOfText': display_date(today.isoformat()),
            'currency': template['currency'], 'scale': template['scale'], 'customer': {'id': cid, 'name': customer.get('name'), 'link': links['customer']},
            'requestId': r and r['id'], 'invoiceId': r and r.get('invoiceId'), 'invoiceReference': own and own.get('reference'),
            'policy': {'authority': authority, 'rows': policy_rows},
            'records': {'invoices': invoice_rows, 'payments': payment_rows, 'allocations': allocation_rows, 'openingBalances': opening_rows},
            'trail': trail, 'end': {'remainingOpening': t['remainingOpening'], 'remainingOpeningText': money(t['remainingOpening']),
                                    'creditHeld': t['creditHeld'], 'creditHeldText': money(t['creditHeld']),
                                    'reservedUnpaid': [{**inv(x['id']), 'amount': x['reservedUnpaid'], 'amountText': money(x['reservedUnpaid'])} for x in t['invoices'] if x['reservedUnpaid']]},
            'exposure': {'label': 'Current exposure (up to and including today)', 'asOf': t['asOf'], 'readsBefore': t['readsBefore'], 'rows': exposure},
            'history': {'label': 'History (strictly before today)', 'readsBefore': prior['readsBefore'], 'rows': history},
            'missing': missing, 'assumptions': assumptions, 'excluded': excluded, 'checks': rows,
            'recommendation': {'outcome': rec['outcome'], 'reasons': list(rec['reasons'])}, 'links': links}


def basis_summary(b):
    """The compact form a tool result carries (caseDetails, assessRequest): the version and date of the calculation, the ids to fetch
    the full details with (GET api/requests/<requestId>/basis), and how many records it read, could not place or left out."""
    return b and {'calculationVersion': b['calculationVersion'], 'asOf': b['asOf'], 'requestId': b['requestId'], 'assessmentVersion': b['assessmentVersion'],
                  'records': {k: len(v) for k, v in b['records'].items()}, 'missing': len(b['missing']), 'excluded': len(b['excluded']),
                  'assumptions': [x['key'] for x in b['assumptions']]}


def frozen_basis(a):
    """The assessment a decision was made on, copied into the decision (decision.basis) so that later record changes, assessments or
    changes to the limits never change it: its version and time, facts, policy (the limits and checks), recommendation and calculation
    details. None when the case was never assessed."""
    return a and copy.deepcopy({'assessmentVersion': a['version'], 'assessedAt': a['at'], 'facts': a['facts'], 'policy': a['policy'],
                                'recommendation': a['recommendation'], 'basis': a.get('basis')})


# Why a decision has no calculation details, in the records' words (basis_gap): its application version kept none, or no assessment was made.
BASIS_GAPS = {'decision_before_calc': 'Calculation details were not recorded by the application version that made this decision (before calc-v1).',
              'assessment_before_calc': 'Calculation details were not recorded by the application version that made the assessment this decision was '
                                        'made on (before calc-v1).',
              'no_assessment': 'No assessment was performed before this decision, so it has no calculation details.',
              'delegated': 'This decision was made under the owner\'s delegation policy, not from an assessment of the case: its evaluation (key facts, evidence, risk, reliability) is kept on its decision case.'}


def basis_gap(r):
    """Why the decision of case r has no calculation details, {kind, text}, or None (not decided, or it has them). Read from what the case
    recorded of its assessments, never from the missing basis alone: the latest assessment, which is kept on the case once made (only
    before the decision), the recommendation the decision followed and the checks staff acted on. Any of them: an assessment was made, and
    the version that made the decision (or that assessment) kept no details; none: no assessment was performed."""
    d = r.get('decision')
    frozen = (d or {}).get('basis')
    if not d or frozen and frozen.get('basis'):
        return None
    if d.get('decisionSource') in ('delegated_policy', 'owner_override'):
        return {'kind': 'delegated', 'text': BASIS_GAPS['delegated']}
    a = r.get('assessment')
    assessed = bool(frozen or d.get('recommendation') or d.get('assessment') or a and str(a.get('at') or '') <= str(d.get('decidedAt') or ''))
    kind = 'assessment_before_calc' if frozen else 'decision_before_calc' if assessed else 'no_assessment'
    return {'kind': kind, 'text': BASIS_GAPS[kind]}


def remember_problem(keep):
    """Why a remember {text, keepForCustomer, until?} is not valid (the message), or None."""
    if not (isinstance(keep, dict) and isinstance(keep.get('text'), str) and 1 <= len(keep['text'].strip()) <= 500):
        return ('Enter what to remember (1–500 characters).',)
    if not isinstance(keep.get('keepForCustomer', False), bool):
        return ('Choose whether to keep this for the customer.',)
    try:
        keep.get('until') is None or calendar_date(keep['until'])
    except ValueError:
        return ('Enter the end date as YYYY-MM-DD, or leave it out.',)


def queue_why(r, on, role):
    """Why a case waits on whom (waiting_on), in words for this role."""
    mine = on == role
    if on == 'owner' and held(r):   # the owner's answer comes first here too: the decision is still theirs
        return owner_pending(r, role)
    if on == 'staff' and returned(r):   # the owner's answer comes first: it is what staff act on, whatever escalated the case before
        return r['withStaff']['why']
    if r.get('escalated') and on != 'none' and r['status'] in STATES_BEFORE_DECISION:   # a concern-round limit or a failed check (assessment)
        return 'escalated: ' + r['escalated']['reason']
    if mine and role == 'owner' and concerned(r):
        last = open_concerns(r)[-1]
        return 'staff replied: ' + last['quote'] if last.get('kind') == 'reply' else 'staff raised a concern'
    if on == 'none':
        return 'the agent is preparing it' if r['status'] in ACTIVE_STATES else 'the decision is being saved'
    if r['status'] == 'awaiting_owner' and on == 'owner':
        return 'only you decide' if mine else 'the owner decides; nothing to enter'
    if r['status'] == 'awaiting_owner':
        return 'the agent asked you a question'
    if r['status'] == 'needs_information':
        return 'the agent needs your answer to prepare it' if mine else "staff answer the agent's question first"
    return 'it could not be prepared; open it to try again' if mine else 'it could not be prepared; staff try again'


def decision_queue_text(mine, others, role):
    """The decision cases (not the requests) in words, for the model to quote after queue_text: each case waiting for this role by customer, kind and
    exposure, then how many wait on the other role. Empty when there are none. Written by code, so the model cannot leave one out (Hoang, 6 Nov 2026:
    the Owner's assistant reported one of two)."""
    if not mine and not others:
        return ''
    kinds = {'trial_credit': 'trial credit', 'extension': 'extension'}
    each = lambda rows: ', '.join(x['customer'] + ' (' + kinds.get(x['kind'], x['kind']) + (', ' + x['exposureText'] if x.get('exposureText') else '') + ')' for x in rows)
    n = len(mine)
    if not mine:
        first = ' No decision case waits for you.'
    elif role == 'owner':
        first = ' ' + str(n) + (' decision case needs' if n == 1 else ' decision cases need') + ' your decision: ' + each(mine) + '. Decide on the Decide page.'
    else:
        first = ' ' + str(n) + (' decision case waits' if n == 1 else ' decision cases wait') + ' for information from you: ' + each(mine) + '.'
    rest = (' ' + str(len(others)) + (' decision case is ' if len(others) == 1 else ' decision cases are ') + ('with staff' if role == 'owner' else 'with the owner') + ': ' + each(others) + '.') if others else ''
    return first + rest


def queue_text(mine, others, role):
    """workQueue in words, written by code: how many cases wait for this person ('need your decision' when all of the owner's are
    waiting for it), then on whom the rest wait, each invoice once with its customer and how many requests it has."""
    def invoices(rows):
        groups = {}
        for x in rows:
            groups.setdefault(x['invoiceReference'], []).append(x)
        return ', '.join((ref or 'invoice not identified yet') + (' (' + ', '.join(parts) + ')' if parts else '') for ref, g in groups.items()
                         for parts in [[p for p in ((g[0]['customer'] or {}).get('name'), len(g) > 1 and str(len(g)) + ' requests') if p]])

    def cases(rows, verb):
        return str(len(rows)) + (' case ' + verb[0] if len(rows) == 1 else ' cases ' + verb[1])
    what = 'your decision' if role == 'owner' and all(x['status'] == 'awaiting_owner' for x in mine) else 'you'
    first = cases(mine, ('needs ', 'need ')) + what + ': ' + invoices(mine) + '.' if mine else 'Nothing is waiting for you.'
    where = {'owner': 'with the owner', 'staff': 'with staff', 'none': 'being prepared, or their decision saved'}
    rest = ' '.join(cases(g, ('is ', 'are ')) + where[on] + ': ' + invoices(g) + '.' for on in where for g in [[x for x in others if x['waitingOn'] == on]] if g)
    return first + ' ' + (rest or 'Nothing is waiting on others.')


def owed_row(ev, invoice):
    """One invoice as Records shows it (customers.js owedHtml): the amount with its certainty mark, and the days overdue
    worked out as for a case (extension_facts)."""
    p, due = invoice.get('position'), ev.current_due(invoice)
    mark, amount, on = (('exact', p['exact']['amount'], p['exact']['asOf']) if p and p['exact'] else ('atMost', p['atMost'], None) if p else
                        ('stated', invoice['outstandingAmount'], invoice.get('outstandingAsOf')) if invoice.get('outstandingAmount') else ('none', None, None))
    facts = extension_facts(ev.as_of, invoice, due, ev.as_of.isoformat(), [])
    return {'id': invoice['id'], 'reference': invoice['reference'], 'status': p['status'] if p else 'open' if is_open(invoice) else 'settled',
            'mark': mark, 'amount': amount, 'amountAsOf': on, 'position': p, 'dueDate': due, 'daysOverdue': facts['daysOverdue'],
            'daysOverdueReason': facts['daysOverdueReason']}


MARK_WORDS = {'exact': 'exact', 'atMost': 'at most', 'stated': 'stated', 'none': 'not recorded', 'workedOut': 'worked out'}   # owed_row's marks as the page words them (core.js)


def amount_text(amount, mark):
    """An amount as the agent may write it: with its certainty mark after it, as the card shows it."""
    return money_text(amount) + ' (' + mark + ')' if amount else mark


def none_detail(f):
    """Beside "not recorded": what is known when the invoice has a total but no stated amount still owed, else the plain sentence."""
    if not f.get('invoiceTotal'):
        return 'no amount still owed is stated, and no payments are allocated to this invoice yet; record a payment against it or state the amount owed'
    zero = {**f['invoiceTotal'], 'minorUnits': '0'}
    um = f.get('unmatchedPayments')
    return ('Invoice ' + money_text(f['invoiceTotal']) + ' · ' + money_text(f.get('allocatedAmount') or zero) + ' allocated · still owed not stated' +
            ('. ' + plural_text(um['count'], 'unmatched payment') + ' for this customer (' + money_text(um['amount']) + ') may apply' if um else ''))


def invoice_figures(invoice, amount, mark, as_of, position, lines):
    """One invoice's figures, each separate and labelled for the model and the cards: totalText (the original invoice amount),
    stillOwedText (the amount still owed, stated, derived or worked out, with its basis, or "not recorded"), allocations / allocationsText (the
    payments allocated to it, by payment reference, date and amount) and settled. Every amount carries a mark the guard reads
    (as recorded, exact, stated, at most). invoice is the record, amount and mark as owed_row / case_amount give them, position the
    invoice's settlement position (or None), lines the allocation_lines."""
    total, recorded = invoice.get('total'), lambda a: money_text(a) + ' (as recorded)'
    on = display_date(as_of) if as_of else None
    nothing = amount is not None and int(amount['minorUnits']) == 0
    if mark == 'exact':
        owed = 'Still owed: ' + money_text(amount) + ' (exact, as of ' + on + ')'
    elif mark == 'atMost' and position:
        if position['basis'] == 'total':
            how = 'the invoice amount ' + recorded(total) + ' less ' + recorded(position['allocated']) + ' allocated from payments'
        else:
            how = ('the amount stated still owed ' + money_text(position['stated']) + ' (stated as of ' + display_date(position['statedAsOf']) + ')' +
                   (', less ' + recorded(position['counted']) + ' from payments after it' if int(position['counted']['minorUnits']) else ''))
        owed = 'Still owed: ' + money_text(amount) + ' (at most, derived: ' + how + ')' + ('; the records about this invoice contradict each other' if position['status'] == 'conflict' else '')
    elif mark in ('stated', 'atMost') and amount:
        owed = 'Still owed: ' + money_text(amount) + ' (stated' + (' as of ' + on if on else '') + ')'
    elif mark == 'workedOut':   # none recorded: what the replay leaves on it (recorded allocations first, then oldest first)
        owed = ('Still owed: ' + money_text(amount) + ' (worked out: the invoice amount ' + recorded(total) + ' less the payments applied to it, by recorded allocation '
                'first and then oldest first)' + ('; nothing is left on it' if nothing else ''))
    else:
        owed = 'Still owed: not recorded' + ('; the original invoice amount is ' + recorded(total) if total else '')
    if nothing and mark in ('exact', 'atMost') and position and position['status'] == 'settled':
        owed += '; settled: the allocated payments cover the whole invoice'
    rows = [{'paymentReference': p.get('reference'), 'receivedDate': p['receivedDate'], 'amountText': recorded(a['amount']),
             'enteredByText': entered_text(a if (a.get('setBy') or a.get('origin') or {}).get('kind') in ('file', 'manual', 'correction', 'answer') else p)} for a, p in lines]
    said = '; '.join('payment ' + (r['paymentReference'] or 'with no reference') + ', received ' + (display_date(r['receivedDate']) if r['receivedDate'] else '(no received date)') + ': ' + r['amountText'] + ' allocated'
                     for r in rows)
    return {'totalText': recorded(total) + ', the original invoice amount' if total else 'The original invoice amount is not recorded.', 'stillOwedText': owed + '.',
            'allocations': rows, 'allocationsText': (said[0].upper() + said[1:] + '.') if rows else 'No payment is allocated to this invoice.',
            'settled': bool(nothing and (mark == 'workedOut' or position and position['status'] == 'settled'))}


def case_amount(f):
    """What is still owed on a case's invoice as its case shows it (requests.js outstandingHtml), from the snapshot's facts: the
    amount, its mark (owed_row's), the words beside the mark, and the amountText the agent may quote."""
    short = lambda d: display_date(d).rsplit(' ', 1)[0]   # no year, as the card
    amount = f.get('invoiceOutstanding')
    mark, detail = (('exact', 'as of ' + short(f['outstandingExactAsOf'])) if f.get('outstandingExact') else
                    ('atMost', f.get('outstandingNote') or money_text(f['allocatedAmount']) + ' allocated from payments') if f.get('outstandingBound') else
                    ('stated', 'as of ' + short(f['outstandingAsOf']) if f.get('outstandingAsOf') else '') if amount else
                    ('none', none_detail(f)))
    words = MARK_WORDS[mark] + (' ' + detail if detail.startswith('as of') else '; ' + detail if detail else '')
    return {'amount': amount, 'mark': mark, 'markDetail': detail, 'amountText': amount_text(amount, words)}


def actions_for(role, situation, tools):
    """The next steps the workflow allows this role now, from the situation's case and customer, each {id, label, kind ('wait';
    'open': a place in the app; 'prepare': the agent prepares, the person confirms; 'act': an effect in Nucleon), allowed,
    needsConfirmation, why, link (where it is done, or None)}. Staff: wait while a case is with the owner, answer the agent's
    question, enter a request only for an open invoice with none open already, add an invoice, record a payment. The owner:
    decide each case waiting, have the desk prepare a decision or a new suggestion, answer the agent's questions, add context, turn
    suggestions on. A step whose desk tool (STEP_TOOLS) is not among tools, the names on for this role, is not allowed, and says so.
    The desk agent reads them in the situation and answers "what next" from them."""
    c, k = situation['case'], situation['customer']

    def step(name, label, kind, why, link=None, allowed=True, confirm=False):
        return {'id': name, 'label': label, 'kind': kind, 'allowed': allowed, 'needsConfirmation': confirm, 'why': why, 'link': link}
    on = lambda ref: 'invoice ' + (ref or 'not identified yet')
    waiting = {case_label({'status': 'awaiting_owner', 'aiStatus': a}, role) for a in (None, 'failed')}   # the case list's words for it
    cases = {x['requestId']: (x['invoiceReference'], x['link']) for x in (k or {}).get('openCases') or [] if x['status'] in waiting}
    if c and c['status'] == 'awaiting_owner':
        cases = {c['requestId']: ((c['invoice'] or {}).get('reference'), '#/case/' + c['requestId']), **cases}
    if role == 'staff':
        out = [step('wait_for_owner', "Wait for the owner's decision on " + on(ref), 'wait', 'the owner decides; nothing to enter', link) for ref, link in cases.values()]
        if c and (c['status'] == 'needs_information' or any(q['status'] == 'open' for q in c['questions'])):
            out.append(step('answer_staff_question', "Answer the agent's question on " + on((c['invoice'] or {}).get('reference')), 'open',
                            'the agent needs it to prepare the case', '#/case/' + c['requestId']))
        if k:
            taken = {x['invoiceReference'] for x in k['openCases']}
            out += [step('open_request', 'Enter a request for invoice ' + i['reference'], 'act', 'a request for this invoice is already open'
                         if i['reference'] in taken else "paste the customer's message here", allowed=i['reference'] not in taken) for i in k['invoices']]
            out += [step('add_invoice', 'Add an invoice for ' + k['name'], 'open', "invoices are added in the customer's records", k['link']),
                    step('record_payment', 'Record a payment or credit for ' + k['name'], 'open', "payments and credits are recorded in the customer's records", k['link'])]
    else:
        out = [step('decide', 'Decide the request for ' + on(ref), 'act', 'only you decide; the decision form is in the case', link, confirm=True) for ref, link in cases.values()]
        out += [step('prepare_decision', 'Tell me your decision to prepare it for you to confirm', 'prepare', 'I work out the date and compare it with '
                     'the date asked and your limit; nothing is decided until you press Confirm decision', confirm=True)] * bool(cases)
        if c and c['status'] == 'awaiting_owner' and c['label'] != case_label({'status': 'awaiting_owner', 'aiStatus': 'failed'}, role):   # the agent prepared it
            off, asked = (c['suggestion'] or {}).get('status') == 'off', [q for q in c['questions'] if q['status'] == 'open' and q['from'] != 'staff']
            out.append(step('request_suggestion', 'Ask me for a new suggestion', 'act', 'suggestions are off' if off else 'a question is still open; the '
                            'suggestion waits for it' if asked else 'it is advisory; you decide', allowed=not off and not asked))
            out += [step('answer_question', 'Answer: ' + q['question'], 'open', 'the suggestion waits for it; the decision does not', '#/case/' + c['requestId'])
                    for q in asked]
            out += [step('turn_on_suggestions', 'Turn suggestions on', 'act', 'suggestions are off; they are advisory')] * off
        if k:
            out.append(step('add_context', 'Tell me something about ' + k['name'] + ' to keep', 'prepare', 'I show what I understood; it is kept once you confirm it',
                            confirm=True))
    # a step whose tool the owner turned off stays listed, not allowed, with the reason; one already not allowed keeps its own
    return [{**a, 'allowed': False, 'why': OFF_IN_SETUP} if a['allowed'] and a['id'] in STEP_TOOLS and STEP_TOOLS[a['id']] not in tools else a for a in out]


def total(amount, what):
    return amount and {'amount': money_text(amount), 'mark': 'as recorded', 'amountText': amount_text(amount, 'as recorded, ' + what)}


def plural_text(n, word):
    return f'{n} {word}' + ('' if n == 1 else 's')


def unit_problem(unit, workspace):
    """Why a file's money cannot be imported into this workspace (its stated unit is another currency), else None."""
    found = unit['detected']
    if unit.get('doubtful') and workspace['scale']:
        return ('The file\'s amounts look like a zero-decimal currency; these records are kept in ' + workspace['currency'] +
                ' with cents. Nothing was imported. Start a workspace in that currency, or convert the file.')
    if found == 'dollar' and workspace['currency'] in importer.DOLLARS:
        return None   # a dollar sign fits any dollar currency
    if found and found != workspace['currency']:
        what = 'dollars' if found == 'dollar' else found
        return ('The file\'s amounts look like ' + what + '; these records are kept in ' + workspace['currency'] +
                '. Nothing was imported. Start a workspace in ' + ('a dollar currency' if found == 'dollar' else found) + ', or convert the file.')


def clock_text(iso, zone):
    """A moment (an ISO time) on the real clock in the business's time zone, with the zone: "24 Oct 2026, 02:04 AEDT" (a zone with no
    abbreviation is its offset, "UTC+07:00"). Never the business date, which the demo console may have moved."""
    try:
        at = datetime.fromisoformat(iso.replace('Z', '+00:00')).astimezone(ZoneInfo(zone) if zone else timezone.utc)
    except (ValueError, AttributeError, ZoneInfoNotFoundError):
        return str(iso)[:16]
    name = at.tzname() or ''
    offset = at.strftime('%z')
    return at.strftime('%-d %b %Y, %H:%M ') + (name if name.isalpha() else 'UTC' + offset[:3] + ':' + offset[3:])


def imported_text(p, zone):
    """When a proposal was imported: the real clock with its time zone, and apart the business date the records were on then when it
    was kept (appliedOn): "24 Oct 2026, 02:04 AEDT (business date Fri 23 Oct 2026)"."""
    return clock_text(p['appliedAt'], zone) + (' (business date ' + display_date(p['appliedOn']) + ')' if p.get('appliedOn') else '')


def duplicate_message(twin, zone=None):
    counts = twin['view']['counts']
    return ('This file was imported on ' + imported_text(twin, zone) + ': ' + str(counts['invoices']) + ' invoices, ' +
            str(counts['payments']) + ' payments' + (', ' + plural_text(counts['openingBalances'], 'opening balance') if counts.get('openingBalances') else '') + '.')


# The references line of a file already imported: its payments were matched to its invoices when it was imported; matched now against
# the records that import made, none would be "in this file", which reads as if nothing matched.
ALREADY_MATCHED = 'This file was already imported; its payment references were matched to its invoices when it was imported'



def customer_records(doc, customer_id):
    """One customer's invoices, payments, opening balances and (for the calculation details) allocations, as the assessment reads them."""
    mine = {'invoices': [i for i in doc['invoices'] if i['customerId'] == customer_id], 'payments': [p for p in doc.get('payments', []) if p['customerId'] == customer_id],
            'openingBalances': [o for o in doc.get('openingBalances', []) if o['customerId'] == customer_id]}
    paid = {p['id'] for p in mine['payments']}
    mine['allocations'] = [a for a in doc.get('allocations', []) if a['paymentId'] in paid]   # the replay reads them all, as before
    return mine


def owed_position(doc, customer_id, as_of, settings):
    """What one customer owes on as_of, from the same replay the assessment runs (behaviour.assessment_facts, its CURRENT facts and trail):
    owed now and its parts (overdue; not yet due; no due date; left of an opening balance of unknown age), the opening balance, the credit
    held, each invoice's remainder, all as money; openingPaid when an opening balance was paid off by earlier payments. Not yet due is
    what is left of owed now after the other parts, never clamped. The recorded net is not here: it leaves out the opening balance."""
    mine = customer_records(doc, customer_id)
    f = assessment_facts(mine['invoices'], mine['payments'], doc.get('allocations', []), mine['openingBalances'], as_of)
    t, money = f['trail']['current'], lambda units: amount_of(settings, units)
    left = {**{i['id']: i['left'] for i in t['invoices']}, **{i['id']: i['open'] for i in t['undated']}}
    return {'asOf': as_of.isoformat(), 'owedNow': money(f['debt_before_m']), 'overdue': money(f['overdue_before_m']),
            'notYetDue': money(f['debt_before_m'] - f['overdue_before_m'] - f['noDueAmount'] - f['openingOwing']), 'noDueDate': money(f['noDueAmount']),
            'openingOwing': money(f['openingOwing']), 'openingBalance': money(f['openingBalance']), 'creditHeld': money(t['creditHeld']),
            'hasOpening': bool(t['opening']['balances']), 'openingPaid': f['openingBalance'] > 0 and f['openingOwing'] == 0,
            'left': {k: money(v) for k, v in left.items()},
            'incompleteText': incomplete_text({**f, 'noDueDate': 0}) or None}   # a missing due date is a part of owed now, said there


WORKED = 'worked out'   # the mark of an amount the replay derived (not recorded): owed now, its parts, an invoice's remainder, the credit held


def worked(amount, what):
    """An amount the replay worked out, as the tools give it: {amount, mark, amountText}, the mark after it as the reply guard reads it."""
    return {'amount': money_text(amount), 'mark': WORKED, 'amountText': amount_text(amount, WORKED + ', ' + what)}


COMPLETENESS_WORDS = {'invoices': 'invoice records', 'payments': 'payment records'}


INVOICE_ROW_KEYS = ('invoiceId', 'reference', 'status', 'dueDateText', 'originalDueText', 'dueNowText', 'dueNowSource', 'daysOverdue', 'overdueText', 'overdueBasisText', 'stillOwedText', 'amountText',
                    'totalText')


def invoices_for_model(out):
    """What the model reads of an invoices result: every invoice, each as one short row of the sentences code wrote (no allocations), so a list of 20-30
    invoices is a few thousand characters instead of 20-28 thousand the model failed to search (Hoang's NTK round, 9 Nov 2026: it said invoices that were in
    the list did not exist). Nothing is dropped: the card keeps the full result."""
    rows = [{k: m[k] for k in INVOICE_ROW_KEYS if m.get(k) not in (None, '')} for m in out['invoices']]
    keep = ('customerId', 'name', 'which', 'asOf', 'invoiceCount', 'scopeText', 'summaryText', 'unmatchedText')
    view = {k: out[k] for k in keep if out.get(k) not in (None, '')}
    if out.get('filter'):
        view['filter'] = {k: v for k, v in out['filter'].items() if k in ('text', 'noneText') and v}
    for k in ('completeTo', 'completeness'):   # the same completeness object customerOverview gives, whole: a list is never read as the whole position
        if out.get(k) is not None:
            view[k] = out[k]
    return {**view, 'invoices': rows}


def written_date(text):
    """A date written in the assistant's words ("Sun 15 Nov 2026", "15 November 2026", "2026-11-15") as a date, or None."""
    t = re.sub(r'^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,?\s+', '', text.strip(), flags=re.I).replace(',', '')
    for fmt in ('%Y-%m-%d', '%d %b %Y', '%d %B %Y'):
        try:
            return datetime.strptime(t, fmt).date()
        except ValueError:
            pass
    return None


def completeness_view(coverage, as_of, invoice_count, payment_count, owed, blocks=()):
    """How far the records behind a customer's figures are confirmed complete, as one object the customer overview and the invoices tool
    both carry (the same inputs give the same object), so a list or a figure is never read as the customer's whole position. Nothing here
    is a second completeness algorithm: coverage is records.coverage_view's per-kind answer (p['coverage']), owed is owed_position's (its
    incompleteText: records that could not be read or placed) and blocks are records.customer_blocks (the opening-balance prerequisites
    exact_outstanding also needs). Invoices and payments are judged apart (a statement for one says nothing of the other).
      state  complete: confirmed complete to as_of or later; completeToEarlierDate: confirmed only to an earlier date (a past
             confirmation is never current); notConfirmed: no confirmed completeness (a last activity date is never completeness).
      A contradicted statement (records changed inside its period after it was confirmed) adds <kind>_contradicted even when another
      statement still gives a completeTo.
      balanceEstablished: both kinds complete, nothing contradicted, no unreadable or unplaced records and no open opening-balance
      prerequisite. It says the RECORDS support a balance. It changes no mark: a figure worked out from recorded records is exactly
      added up, which is not the same as an established account balance (no amount is ever turned into an exact one by it).
    Reason codes are stable snake_case; caveatText is deterministic plain words with no amount, quotable whole by the agent."""
    short, kinds = (lambda d: display_date(d).rsplit(' ', 1)[0]), {}
    reasons, clauses = [], []
    for kind in ('invoices', 'payments'):
        found, to = coverage[kind], coverage[kind]['completeTo']
        state = 'notConfirmed' if to is None else 'complete' if to >= as_of else 'completeToEarlierDate'
        kinds[kind] = {'completeTo': to, 'state': state, 'lastActivity': found['lastActivity'],
                       'recordedCount': invoice_count if kind == 'invoices' else payment_count, 'contradicted': len(found['contradicted'])}
        words = COMPLETENESS_WORDS[kind]
        if state == 'notConfirmed':
            reasons.append(kind + '_not_confirmed')
            clauses.append(words + ' are not confirmed complete')
        elif state == 'completeToEarlierDate':
            reasons.append(kind + '_complete_to_earlier_date')
            clauses.append(words + ' are confirmed complete only to ' + short(to))
        else:
            clauses.append(words + ' are confirmed complete to ' + short(to))
        if found['contradicted']:
            reasons.append(kind + '_contradicted')
            clauses.append('a completeness statement for ' + words + ' no longer holds, because records changed after it was confirmed')
    sentences = []
    if not invoice_count:
        reasons.append('no_invoices_recorded')
        sentences.append('No invoices are recorded' + (', which does not show that none were issued.' if kinds['invoices']['state'] != 'complete' else ' in the confirmed records.'))
    if not payment_count:
        if kinds['payments']['state'] != 'complete':
            reasons.append('no_payments_recorded')
            sentences.append('No payments are recorded, which does not show that none were made.')
        else:
            sentences.append('No payments are recorded in the confirmed records.')
    if owed.get('incompleteText'):
        reasons.append('records_incomplete')
        sentences.append('Some records could not be read or placed, so the figures may be incomplete.')
    if blocks:
        reasons += [b for b in blocks if b not in reasons]
        sentences.append('The opening balance, and what it includes, is not fully settled.')
    established = (all(k['state'] == 'complete' and not k['contradicted'] for k in kinds.values()) and not owed.get('incompleteText') and not blocks)
    if established:
        text = 'Invoice and payment records are confirmed complete to ' + display_date(min(k['completeTo'] for k in kinds.values())) + '.'
        caveat = ' '.join([text, *sentences])
    else:
        caveat = ' '.join(['Not a confirmed balance: ' + '; '.join(clauses) + '.', *sentences])
    return {'asOf': as_of, **kinds, 'balanceEstablished': established, 'reasons': reasons, 'caveatText': caveat}


def balance_line(name, net, complete, rows, recorded, stated=None, owed=None, moved=()):
    """What a customer owes, in words the agent may quote whole: owed now from the replay
    (owed_position) with its parts in order (overdue; not yet due; no due date; left of an opening balance of unknown age), an opening
    balance paid off, a credit held, then the recorded net under its own label (it leaves out the opening balance) where it differs from
    owed now, and each invoice's amount still owed (rows: the model's, a worked-out nothing left out); how complete the records are is said
    beside owed now, so a brief answer that quotes the line stays short. Every amount is followed by its mark. The model never totals
    amounts itself; with no invoices and nothing owed there is no amount to quote."""
    nothing = lambda a: not int(a['minorUnits'])
    if not recorded and not (owed and not (nothing(owed['owedNow']) and nothing(owed['creditHeld']))):
        return 'No invoices are recorded for ' + name + '.'
    short = lambda d: display_date(d).rsplit(' ', 1)[0]   # no year, as the marks
    done = '; '.join(k + (' complete to ' + short(complete[k]) if complete.get(k) else ' not confirmed complete') for k in ('invoices', 'payments'))
    line = ''
    if owed:
        w, opening = lambda a: money_text(a) + ' (' + WORKED + ')', money_text(owed['openingBalance']) + ' (as recorded)'
        by = ' by the original due date (' + '; '.join(r + ': later date approved, ' + d for r, d in moved) + ')' if moved else ''   # the replay judges by the original date
        parts = [(owed['overdue'], '{} overdue' + by, 'all of it overdue' + by), (owed['notYetDue'], '{} not yet due', 'all of it not yet due'),
                 (owed['noDueDate'], '{} with no due date, so overdue is not known', 'all of it on invoices with no due date, so overdue is not known'),
                 (owed['openingOwing'], '{} left of the opening balance of ' + opening + ', of unknown age', 'all of it left of the opening balance of ' + opening + ', of unknown age')]
        parts = [(w(a), many, only) for a, many, only in parts if not nothing(a)]
        line = 'Owed now ' + money_text(owed['owedNow']) + ' (' + WORKED + '; ' + done + ')' + ((', ' + parts[0][2] if len(parts) == 1 else ': ' + '; '.join(m.format(a) for a, m, _ in parts)) if parts else '') + '.'
        line += (' ' + opening_paid_text(opening)) if owed['openingPaid'] else ''
        line += (' Customer credit held ' + w(owed['creditHeld']) + '.') if not nothing(owed['creditHeld']) else ''
        line += (' ' + owed['incompleteText']) if owed['incompleteText'] else ''
    same = owed and net and not owed['hasOpening'] and minor(net) == minor(owed['owedNow'])   # the recorded net says nothing more
    if net and not same:
        line += ' Recorded invoices less recorded payments: ' + money_text(net) + ' (as recorded' + ('; this leaves out the opening balance' if owed and owed['hasOpening'] else '') + ').'
    elif not net and not stated and not owed:
        line += ' Recorded invoices less recorded payments is not worked out, because an invoice has no total recorded.'
    line += '' if owed else ' Records: ' + done + '.'
    return (line + ' Still owed per invoice: ' + '; '.join(r['reference'] + ' ' + r['amountText'] for r in rows) + '.' if rows else
            line + (' Nothing is owed on the invoices.' if recorded else ' No open invoices.')).strip()


def dated(value):
    """A tool result for the agent with each date (YYYY-MM-DD) also in the page's words beside it, as <key>Text ("Tue 3 Nov
    2026"), so the model copies a date rather than formats one (21 Oct: "until Sun 30 Nov 2026" for 2026-11-30, a Monday). The
    answer card's blocks keep the page's data unchanged."""
    if isinstance(value, list):
        return [dated(x) for x in value]
    if not isinstance(value, dict):
        return value
    out = {}
    for k, v in value.items():
        out[k] = v if k == 'forModel' else dated(v)   # forModel is the compact result written by code, bounded in size: nothing is added to it
        if isinstance(v, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', v):
            try:
                out[k + 'Text'] = display_date(v)
            except ValueError:   # shaped like a date, but none ("2026-02-30", a reference the model passed)
                pass
    return out


class DeskTools:
    """The agent's tools for one call over the tool surface (POST api/tools/<name>), as ToolDispatcher is for a case run. The reads use the app's
    own views as this role may see them (records_view positions, owed_row, context_for, summary and case_label), each under the
    lock and on the records as they are then; the model sees a minimised result (amounts in their display form, no internal ids beyond customerId, invoiceId and
    requestId) and the answer card's block keeps the full one (.blocks). A customerId must be one findCustomers returned in this
    turn, a customer's code, or "current": the thread's current customer for this role (.focus; when the focus is a draft or a name
    not found, .subject, the refusal says so); a requestId one from cases, an invoice reference, or "current": the case of this
    thread (.request_id), whose own context lines ownerContext then includes. The role is offered the tools that are on for
    it (coordinator.tools_for, with the owner's agentTools as the turn starts), and execute runs no other: openRequest (staff) and
    interpretStatement (owner) return a reading and store nothing; interpretStatement makes its model call here, without the lock."""
    LOCKED = ('findCustomers', 'customerOverview', 'invoices', 'ownerContext', 'cases', 'caseDetails', 'whereIs', 'prepareCustomer', 'prepareDecision',
              'compareExtension', 'withdrawPreparation', 'workQueue', 'listRequests', 'prepareHoldingMessage', 'raiseConcern', 'answerConcern', 'applyImportProposal',
              'assessRequest', 'actWithinAuthority', 'withdrawRequest', 'prepareRequest', 'actionStatus', 'assessDecision', 'resolveDecision', 'decisionStatus',
              'whatIsNeeded', 'comparableCases', 'customerStatus', 'policyBacktest', 'impactSummary', 'doctor')
    CONTROLLED = SERVER_CONTROLLED - {'requestId'}   # a case to read is named like a customer, and checked (case_id)
    CALLS_MODEL = ('interpretStatement', 'requestSuggestion', 'proposeImport')   # never run under the lock

    # "current" when this person's focus is no customer: what it is, so the model replies rather than asks again
    NOT_A_CUSTOMER = {'draft': '{} is not yet a customer (a draft); nothing is recorded. Reply now.', 'unknown': '{} was not found in the records. Reply now.'}

    def __init__(self, app, actor, text, today, adapter, timeout, focus_id=None, said=(), request_id=None, subject=None, pressed=False):
        self.app, self.role, self.text, self.today, self.adapter, self.timeout = app, actor['role'], text, today, adapter, timeout
        self.actor, self.by, self.pressed = actor, actor.get('id'), pressed   # pressed: a person on the tool surface (tools_for)
        self.trail = trail(actor)
        self.shown = self.trail if actor.get('name') else {}   # what a result or a view shows of it: only a named actor (the AI Agent)
        self.request_id = request_id   # the case of a case thread
        self.ev = app.evidence()   # lock held by tool_call; each read takes it again and reads afresh
        self.focus, self.said, self.found = focus_id and self.ev.customer(focus_id), list(said), None   # said: this person's recent turns
        self.customers, self.tools = self.ev.customers, tools_for(self.role, app.meta('agentTools'), pressed)
        self.specs = {t['function']['name']: t['function']['parameters'] for t in self.tools}
        self.seen, self.blocks, self.model_calls, self.positions = {}, {}, 0, None
        self.missed, self.existing = None, []   # the closest names when a search this turn found nobody; customers prepareCustomer found already in the records
        self.unknown = None   # the first name a search this turn found nobody for: the thread's next focus, unless a customer is
        self.targets = {x['route'] for x in WHERE_IS.values()}   # where a next step may lead: these, and links in the results
        self.subject = subject   # the focus when it is no customer (a draft or a name not found), or None
        self.cased = {}   # the customers of the cases caseDetails read this turn, by id: whom an answer from them is about
        self.about = None   # the customer the current call named (customer, case_id, a search finding one): its result's subject

    def execute(self, name, raw_arguments):
        with self.app.lock:   # the owner may turn a tool off while the model reads: permitted as the turn started and as it is now
            live = [t['function']['name'] for t in tools_for(self.role, self.app.meta('agentTools'), self.pressed) if t['function']['name'] in self.specs]
        if name not in live:   # permission: a tool off, another role's or made up is refused and never run, whatever the model names
            return ToolDispatcher._fail(name, raw_arguments, ToolError('FORBIDDEN', 'Tool "' + str(name)[:60] + '" is not permitted. Permitted tools: ' +
                                                                       ', '.join(live) + ', reply.', executed=False))
        try:
            args = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
        except ValueError:
            args = None
        try:
            if not isinstance(args, dict):
                raise ToolError('INVALID_ARGUMENT', 'Arguments must be a JSON object.', executed=False)
            if self.CONTROLLED & set(args):
                raise ToolError('FORBIDDEN', 'Server-controlled field(s) cannot be supplied: ' + ', '.join(sorted(self.CONTROLLED & set(args))) + '.', executed=False)
            try:
                _require_args(args, name, self.specs)
            except ToolError as exc:
                missing = [k for k in self.specs[name]['required'] if k not in args] if name in ('assessDecision', 'resolveDecision', 'whatIsNeeded', 'comparableCases') and exc.message.startswith('Missing argument') else []
                if 'kind' in missing:   # a delegation request that does not say which kind it is: ask, rather than guess
                    raise self.hinted(exc, self.kind_hint()) from None
                if 'customerId' in missing:
                    raise self.hinted(exc, self.customer_hint(args)) from None
                raise
            self.about = None   # every result says whom it is about (subject_of), read as the tool read
            if name not in self.LOCKED:
                outcome = getattr(self, '_' + name)(args)
                with self.app.lock:
                    outcome.result['subject'] = self.subject_of(outcome.result)
                return outcome
            with self.app.lock:
                self.ev, self.positions = self.app.evidence(), None
                outcome = ToolDispatcher._ok(name, args, getattr(self, '_' + name)(args))
                outcome.result['subject'] = self.subject_of(outcome.result)
            return outcome
        except ToolError as exc:
            return ToolDispatcher._fail(name, args if isinstance(args, dict) else raw_arguments, exc)

    def block(self, kind, data):
        self.blocks.setdefault(kind, []).append(data)

    def subject_of(self, result):
        """Whom a result is about, {customerId, name}: the customer the call named, else the customer of the case it gives; or None
        (several customers, or none identified). Lock held."""
        c = self.about or isinstance(result.get('requestId'), str) and self.ev.customer(self.app.get(result['requestId']).get('customerId'))
        return {'customerId': c['id'], 'name': c['name']} if c else None

    def not_a_customer(self):
        return ToolError('INVALID_ARGUMENT', self.NOT_A_CUSTOMER[self.subject['kind']].format(self.subject['name']), executed=False)

    def named_customer(self, given):
        """A name, code or invoice reference given as customerId, resolved as findCustomers matches it: one customer is used (and is
        then as if findCustomers had returned it); several are asked about by name; none is None (customer() refuses it). An id is
        not a name: one the model did not get from findCustomers this turn is refused."""
        matches = [c for c, _ in self.ev.find_customers(given)]
        if len(matches) > 1:
            raise ToolError('INVALID_ARGUMENT', 'Several customers match "' + given + '": ' + ', '.join(c['name'] for c in matches[:5]) +
                            '. Ask which one the person means, listing the names. Call reply now.', executed=False)
        if matches:
            self.seen[matches[0]['id']] = matches[0]
            return matches[0]
        return None

    def customer(self, args):
        """The customer a customerId names: one findCustomers returned this turn, a customer's code as the customer list and the
        focus line show it ("C-0003"), or "current"."""
        given = _text_arg(args, 'customerId', 80)
        if given == 'current' and self.missed is not None:   # the person named someone the records do not hold: not the current customer
            raise ToolError('INVALID_ARGUMENT', 'No customer matched; ask which customer the person means, listing names: ' + ', '.join(self.missed) +
                            '. If it is a new customer, say that the customer and their invoice (or order) must be in Nucleon Records before anything can be assessed: '
                            'Staff add them on the Customers page or import a CSV on the Imports page, then ask again. Call reply now.', executed=False)
        if given == 'current' and self.subject:
            raise self.not_a_customer()
        c = self.focus if given == 'current' else self.seen.get(given) or next((x for x in self.ev.customers if x['displayCode'].casefold() == given.casefold()), None)
        if c is None and given != 'current' and not any(x['id'] == given for x in self.ev.customers):
            c = self.named_customer(given)
        c = c and self.ev.customer(c['id'])   # as the records hold it now
        if not c and given != 'current' and not re.fullmatch(r'customer_\w+', given):   # a name or code the records do not hold
            raise ToolError('INVALID_ARGUMENT', 'No customer matches "' + given + '" in the records. Ask which customer the person means, by name or code (never ask for a "customer id": people do not have one). If it is a new '
                            'customer, say that the customer and their invoice (or order) must be in Nucleon Records before anything can be assessed: Staff add them on the '
                            'Customers page or import a CSV on the Imports page, then ask again. Call reply now.', executed=False)
        if not c:
            raise ToolError('INVALID_ARGUMENT', ('There is no current customer. ' if given == 'current' else '') + 'Use a customerId returned by findCustomers in this turn, or "current" for the current customer. '
                            'With no current customer, reply asking which customer.', executed=False)
        self.targets.add('#/customers/' + c['id'])
        self.about = c
        return c

    def case_id(self, args, required=True):
        """The case a requestId names: one that exists, "current" (this thread's case), or the invoice reference the situation names a
        case by (this thread's case, else the one case for it). None when it is optional and not given."""
        given = _text_arg(args, 'requestId', 80, required)
        if given == 'current' and not self.request_id and self.subject:
            raise self.not_a_customer()
        if given == 'current' and not self.request_id and self.focus:   # no case thread: the one open case of the customer in focus
            mine = [x['id'] for x in self.app.records() if x.get('customerId') == self.focus['id'] and x['status'] in STATES_BEFORE_DECISION]
            if len(mine) == 1:
                given = mine[0]
            elif len(mine) > 1:   # never a silent pick: the model asks which
                refs = [summary(self.app.get(i))['invoiceReference'] or 'a request not yet matched to an invoice' for i in mine]
                raise ToolError('INVALID_ARGUMENT', 'Which case do you mean? ' + self.focus['name'] + ' has ' + str(len(mine)) + ' open cases: ' + ', '.join(refs) +
                                '. Ask the person which one, then use that requestId (from cases).', executed=False, extra={'candidates': refs})
            else:
                raise ToolError('INVALID_ARGUMENT', 'There is no open case for ' + self.focus['name'] + ' to use as "current"; ask which case, or use a requestId from cases.', executed=False)
        try:
            rid = given and self.app.get(self.request_id if given == 'current' else given)['id']
        except APIError:
            named = [x['id'] for x in map(summary, self.app.records()) if x['invoiceReference'] and ref_key(x['invoiceReference']) == ref_key(given)]
            if given == 'current' or not (self.request_id in named or len(named) == 1):
                raise ToolError('INVALID_ARGUMENT', 'Use a requestId returned by cases ("current" works in a case thread, or when the customer in focus has one open case).' if given == 'current'
                                else 'Use a requestId returned by cases, or "current" in a case thread.', executed=False) from None
            rid = self.request_id if self.request_id in named else named[0]
        self.about = self.about or rid and self.ev.customer(self.app.get(rid).get('customerId'))   # a customer named first stays the subject
        return rid

    def views(self):
        if self.positions is None:
            self.positions = self.app.records_view()['positions']
        return self.positions

    def rows(self, c, which):
        """The customer's invoices as the overview and invoices tools show them. Where no amount still owed is recorded (none, or only
        derived from allocations) and the replay has a remainder, the replay decides: a "none" row shows the remainder, worked out; the
        row is open only while the remainder is above 0; its days overdue are the days past the ORIGINAL due date (the replay's rule),
        0 with nothing left, unknown with no due date. A recorded amount still owed keeps owed_row's days and amount."""
        left = ((self.views().get('customers', {}).get(c['id']) or {}).get('owed') or {}).get('left', {})
        rows = []
        for i in (owed_row(self.ev, i) for i in self.ev.invoices_for(c['id']) if which == 'all' or is_open(i)):
            if i['id'] in left and (i['mark'] == 'none' or i['mark'] == 'atMost' and (i['position'] or {}).get('basis') == 'total'):
                n, original = minor(left[i['id']]), self.ev.invoice(i['id']).get('originalDueDate')
                days = 0 if not n else None if not original else max(0, (self.ev.as_of - calendar_date(original)).days)
                i = {**i, 'daysOverdue': days, 'daysOverdueReason': None if days is not None else 'needs the due date, which is not on record', 'byReplay': True,
                     'leftMinor': n, **({'mark': 'workedOut', 'amount': left[i['id']], 'worked': True} if i['mark'] == 'none' else {})}
            rows.append(i)
        rows = [i for i in rows if not (i.get('byReplay') and not i['leftMinor'])] if which == 'open' else rows
        rows = [i for i in rows if (i['daysOverdue'] or 0) > 0] if which == 'overdue' else rows
        why = self.views().get('notExact', {})
        mark = lambda i: MARK_WORDS[i['mark']] + (' as of ' + display_date(i['amountAsOf']).rsplit(' ', 1)[0] if i['amountAsOf'] else   # no year, as the card
                                                  ', from allocated payments' if i['mark'] == 'atMost' and (i['position'] or {}).get('basis') == 'total' else '')
        model = []
        for i in rows:
            words = self.due_words(i['id'])
            # the date its overdue days are judged by, said where an owner's decision moved the due date (the Due column shows the one in force)
            basis = ('Overdue judged by the original due date ' + words['originalDueText'] + '; later date approved: ' + words['dueNowText'] + '.' if i.get('byReplay') else
                     'Overdue judged by the approved due date ' + words['dueNowText'] + '.') if words.get('dueNowText') else None
            # in words beside the count, where an extension moved the date (9 Nov 2026: "Due Thu 12 Nov · 12 days overdue" read as late before the new date)
            late = None
            if i.get('byReplay') and words.get('dueNowText') and isinstance(i['daysOverdue'], int) and i['daysOverdue'] > 0:
                ahead = (calendar_date(self.ev.current_due(self.ev.invoice(i['id']))) - self.ev.as_of).days
                late = (days_text(i['daysOverdue']) + ' past the original due date (' + words['originalDueText'] + '). Extended to ' + words['dueNowText'] +
                        (', which has not passed yet.' if ahead >= 0 else ', which has also passed (' + days_text(-ahead) + ' ago).'))
            model.append({'invoiceId': i['id'], 'reference': i['reference'], 'status': i['status'], 'dueDate': i['dueDate'], 'daysOverdue': i['daysOverdue'],
                          **({'overdueText': late} if late else {}),
                          'stillOwed': i['amount'] and money_text(i['amount']), 'mark': mark(i), 'amountText': amount_text(i['amount'], mark(i)),
                          'amountAsOf': i['amountAsOf'], **words, **({'overdueBasisText': basis} if basis else {}),
                          **invoice_figures(self.ev.invoice(i['id']), i['amount'], i['mark'], i['amountAsOf'], i['position'], self.app.allocation_lines(i['id']))})
        rows = [{**i, 'overdueBasisText': m['overdueBasisText']} if 'overdueBasisText' in m else i for i, m in zip(rows, model)]
        return rows, {i['id']: why[i['id']] for i in rows if i['id'] in why}, model

    def due_words(self, invoice_id):
        """The invoice's original due date in words and, when an owner decision moved it, the date it was moved to with its source: the
        two are told apart (dueDate is the one in force)."""
        inv = self.ev.invoice(invoice_id)
        now, source = self.ev.current_due(inv), self.ev.due_source(inv)
        out = {'originalDueText': inv.get('originalDueDate') and display_date(inv['originalDueDate'])}
        if source['origin'] == 'owner_decision':
            by = decider_words(source)
            out.update(dueNowText=display_date(now), dueNowSource='approved to ' + display_date(now) + ' on ' + display_date(source['decidedAt'][:10]) +
                       (' by ' + by if by else ''))
        return out

    def cases_of(self, keep):
        rows = [{'requestId': x['id'], 'status': x['status'], 'label': case_label(x, self.role), 'invoiceReference': x['invoiceReference'],
                 'link': '#/case/' + x['id'], 'customer': x['customerName'], 'asked': x['requestedDueDate']} for x in map(summary, self.app.records()) if keep(x)]
        self.targets.update(x['link'] for x in rows)
        return ([{k: v for k, v in x.items() if k not in ('customer', 'asked')} for x in rows],
                [{'requestId': x['requestId'], 'invoiceReference': x['invoiceReference'], 'customer': x['customer'], 'status': x['label'],
                  'summary': case_summary(x['invoiceReference'], x['customer'], x['label'], x['asked']), 'link': x['link']} for x in rows])

    @staticmethod
    def named(c):
        return {'id': c['id'], 'name': c['name'], 'code': c['displayCode']}

    LIST_ALL = ('*', 'all', 'everyone', 'all customers', 'list', 'list all')

    def _findCustomers(self, args):
        query = _text_arg(args, 'query', 120)
        if query.lower() in self.LIST_ALL:   # "who are our customers": the whole list, by name (1 Nov 2026; the Owner and Staff asked for it)
            matches = sorted(self.ev.customers, key=lambda c: c['name'].lower())
            for c in matches[:25]:
                self.seen[c['id']] = c
                self.targets.add('#/customers/' + c['id'])
            self.found = self.about = None
            return {'count': len(matches), 'listedAll': True, 'shown': min(len(matches), 25),
                    'matches': [{'customerId': c['id'], 'name': c['name'], 'code': c['displayCode']} for c in matches[:25]],
                    'nextStep': 'This is the customer list from the records' + (', the first 25 by name' if len(matches) > 25 else '') + '. The Customers page in Nucleon shows all of them with their balances.'}
        matches = [c for c, _ in self.ev.find_customers(query)]
        for c in matches[:5]:   # only those the model was shown
            self.seen[c['id']] = c
            self.targets.add('#/customers/' + c['id'])
        self.found = self.about = matches[0] if len(matches) == 1 else None   # the thread's next focus; a later search with several or none clears it
        self.unknown = None if matches else self.unknown   # a search that finds anyone clears a name found nobody for before
        result = {'count': len(matches), 'matches': [{'customerId': c['id'], 'name': c['name'], 'code': c['displayCode']} for c in matches[:5]]}
        if not matches:   # a name the records do not hold: what was looked for, and the five closest, so the reply can ask which customer
            result['query'] = query
            result['similar'] = [c['name'] for c in sorted(self.ev.customers, key=lambda c: -SequenceMatcher(None, query.lower(), c['name'].lower()).ratio())[:5]]
            self.missed = result['similar'] if self.missed is None else self.missed
            # shortcut: a query with a digit is taken for a code or reference, not a name; upgrade if names with digits matter
            self.unknown = self.unknown or (None if re.search(r'\d', query) else query)
        return result

    def unmatched(self, c):
        """{unmatchedText} for a customer who has payments no allocation takes, else {}: said apart from every invoice's own figures."""
        um = unmatched_payments(self.ev.fixture, c['id'])
        return {'unmatchedText': plural_text(um['count'], 'payment') + ' of this customer (' + money_text(um['amount']) + ' (as recorded) in all) ' +
                ('is' if um['count'] == 1 else 'are') + ' not allocated to any invoice.'} if um else {}

    def completeness(self, c, p):
        """completeness_view for one customer from the views the overview already reads (p: their positions entry)."""
        paid = sum(1 for q in self.ev.fixture.get('payments', []) if q['customerId'] == c['id'] and q.get('status', 'active') == 'active')
        blocks = customer_blocks(p['opening'], p['coverage']['payments']['base'])
        return completeness_view(p['coverage'], self.ev.as_of.isoformat(), len(self.ev.invoices_for(c['id'])), paid, p['owed'], blocks)

    def _customerOverview(self, args):
        c = self.customer(args)
        p = self.views().get('customers', {}).get(c['id'])
        if p is None:
            raise ToolError('MISSING_DATA', 'The workspace has no currency yet, so nothing is worked out. The owner sets it under Setup.')
        rows, why, model = self.rows(c, 'open')
        owed = p['owed']
        invs = self.ev.invoices_for(c['id'])
        recorded = len(invs)
        # invoices that carry only a stated amount still owed (no total): the position is the sum of those, marked (stated)
        stated = amount_of(p['unallocated'], sum(minor(i['outstandingAmount']) for i in invs)) if p['recordedNet'] is None and invs \
            and all(i.get('outstandingAmount') and not i.get('total') for i in invs) else None
        cases, cases_model = self.cases_of(lambda x: x['customerId'] == c['id'] and x['status'] in STATES_BEFORE_DECISION)
        paid = [{'paymentReference': q.get('reference'), 'receivedDate': q['receivedDate'], 'receivedText': display_date(q['receivedDate']) if q.get('receivedDate') else 'No received date', 'amountText': money_text(q['amount']) + ' (as recorded)', 'enteredByText': entered_text(q)}
                for q in sorted((q for q in self.ev.fixture.get('payments', []) if q['customerId'] == c['id'] and q.get('status', 'active') == 'active'),
                                key=lambda q: (q.get('receivedDate') is None, q.get('receivedDate') or '', q['id']))]   # dated by date, then any with no received date
        gaps = [(calendar_date(i['originalDueDate']) - calendar_date(i['issueDate'])).days for i in invs if i.get('originalDueDate') and i.get('issueDate')]
        terms = ('Invoices are issued on ' + str(int(statistics.median(gaps))) + '-day terms (the median of due date minus issue date over ' + plural_text(len(gaps), 'recorded invoice') + ')'
                 if gaps else 'No payment terms are recorded')
        complete, last = ({k: v[key] for k, v in p['coverage'].items()} for key in ('completeTo', 'lastActivity'))
        # the counts and the balance line as the model gets them
        known = [i for i in rows if i['amount']]   # overdue is counted where a still-owed amount is recorded or the replay works one out
        late = sum(1 for i in known if (i['daysOverdue'] or 0) > 0)
        no_due = [i for i in known if i.get('byReplay') and i['daysOverdue'] is None]
        # an approved later due date on an invoice the replay counts overdue (by its original date): named in the balance line
        moved = [(i['reference'], self.due_words(i['id'])['dueNowText']) for i in invs if minor(owed['left'].get(i['id']) or {'minorUnits': '0'}) > 0
                 and self.due_words(i['id']).get('dueNowText') and i.get('originalDueDate') and calendar_date(i['originalDueDate']) < self.ev.as_of]
        counts = {'openCount': len(rows), 'overdueCount': late if known else None, 'knownAmountCount': len(known), 'caseCount': len(cases),
                  'overdueText': plural_text(len(rows), 'open invoice') + ('; overdue not known because no amount still owed is recorded' if rows and not known else
                                                                              f', {late} overdue' + (f' of {len(known)} with a recorded amount' if len(known) < len(rows) else '') +
                                                                              (f'; overdue not known for {plural_text(len(no_due), "invoice")} with no due date' if no_due else '')),
                  'balanceLine': balance_line(c['name'], p['recordedNet'], complete, [m for m, r in zip(model, rows) if not (r.get('worked') and not minor(r['amount']))],
                                              recorded, stated, owed, moved)}
        self.block('overview', {'customer': self.named(c), 'asOf': self.ev.fixture['asOfDate'], 'recordedNet': p['recordedNet'], 'owed': owed,
                                'unallocated': p['unallocated'], 'completeness': complete, 'lastActivity': last, 'invoices': rows, 'why': why,
                                'cases': cases, **counts})
        return {'customerId': c['id'], 'name': c['name'], 'link': '#/customers/' + c['id'], 'asOf': self.ev.fixture['asOfDate'],
                'recordedNet': total(p['recordedNet'], 'recorded invoices less recorded payments' + ('; this leaves out the opening balance' if owed['hasOpening'] else '')),
                'owedNow': worked(owed['owedNow'], 'owed now'), 'owedOverdue': worked(owed['overdue'], 'overdue'), 'owedNotYetDue': worked(owed['notYetDue'], 'not yet due'),
                'owedNoDueDate': worked(owed['noDueDate'], 'on invoices with no due date, so overdue is not known'),
                'owedFromOpening': worked(owed['openingOwing'], 'left of the opening balance, of unknown age'), 'creditHeld': worked(owed['creditHeld'], 'customer credit held'),
                **({'openingBalance': total(owed['openingBalance'], 'the opening balance')} if minor(owed['openingBalance']) > 0 else {}),
                'openingPaid': owed['openingPaid'],
                **({'statedTotal': {'amount': money_text(stated), 'mark': 'stated', 'amountText': amount_text(stated, 'stated, sum of the amounts stated still owed')}} if stated else {}),
                'notAllocated': total(p['unallocated'], 'received, not matched to an invoice'),
                'completeTo': complete, 'lastActivity': last, 'completeness': self.completeness(c, p), **counts, 'invoiceCount': recorded, 'recordsExist': recorded > 0,
                'invoices': model, 'openCases': cases_model, 'termsText': terms, 'payments': paid[-20:], **self.unmatched(c)}

    def _invoices(self, args):
        c, which = self.customer(args), args['which']
        p = self.views().get('customers', {}).get(c['id'])   # None before the workspace has a currency: no completeness is claimed then
        if which not in ('open', 'overdue', 'all'):
            raise ToolError('INVALID_ARGUMENT', 'which must be open, overdue or all.', executed=False)
        wanted = {}
        for key in ('dueOn', 'issuedOn'):   # a date the question names: code selects the invoices, never the model
            if args.get(key) is not None:
                try:
                    wanted[key] = calendar_date(args[key]).isoformat()
                except (ValueError, TypeError):
                    raise ToolError('INVALID_ARGUMENT', key + ' must be YYYY-MM-DD.', executed=False) from None
        refs = args.get('reference')   # invoice numbers the question names: code finds them, so a long list is never searched by the model (Hoang, 9 Nov 2026)
        if refs is not None:
            refs = [refs] if isinstance(refs, str) else refs
            if not isinstance(refs, list) or not refs or len(refs) > 20 or not all(isinstance(x, str) and x.strip() for x in refs):
                raise ToolError('INVALID_ARGUMENT', 'reference must be an invoice number, or a list of up to 20.', executed=False)
            refs = list(dict.fromkeys(x.strip() for x in refs))
        rows, why, model = self.rows(c, 'all' if wanted or refs else which)
        filter_ = None
        if wanted:
            matched = {}
            for r in rows:
                inv = self.ev.invoice(r['id'])
                original, effective = inv.get('originalDueDate'), self.ev.current_due(inv)
                how = []
                if 'dueOn' in wanted:
                    how.append('original_due' if original == wanted['dueOn'] else 'approved_due' if effective == wanted['dueOn'] else None)
                if 'issuedOn' in wanted:
                    how.append('issue' if inv.get('issueDate') == wanted['issuedOn'] else None)
                if all(how):
                    matched[r['id']] = ', '.join(how)
            rows, model = [r for r in rows if r['id'] in matched], [{**m, 'matchedOn': matched[m['invoiceId']]} for m in model if m['invoiceId'] in matched]
            why = {k: v for k, v in why.items() if k in matched}
            said_on = [('due on ' + display_date(wanted['dueOn']) + ' (original or approved)') if 'dueOn' in wanted else None,
                       ('issued on ' + display_date(wanted['issuedOn'])) if 'issuedOn' in wanted else None]
            filter_ = {**wanted, 'text': ' and '.join(x for x in said_on if x), 'noneText': None}
            if not rows:
                filter_['noneText'] = 'No invoice of ' + c['name'] + ' has ' + ' and '.join(
                    x for x in (display_date(wanted['dueOn']) + ' as its due date (original or approved)' if 'dueOn' in wanted else None,
                                display_date(wanted['issuedOn']) + ' as its issue date' if 'issuedOn' in wanted else None) if x) + '.'
        if refs:
            norm = lambda x: str(x or '').strip().upper()   # noqa: E731
            asked = {norm(x): x for x in refs}
            keep = {m['invoiceId'] for m in model if norm(m.get('reference')) in asked}
            found = {norm(m.get('reference')) for m in model if m['invoiceId'] in keep}
            rows, model = [r for r in rows if r['id'] in keep], [m for m in model if m['invoiceId'] in keep]
            why = {k: v for k, v in why.items() if k in keep}
            missing = [asked[k] for k in asked if k not in found]
            elsewhere = []
            for ref in missing:
                owners = sorted({(self.ev.customer(i['customerId']) or {}).get('name') or i['customerId'] for i in self.ev.fixture.get('invoices', [])
                                 if norm(i.get('reference')) == norm(ref) and i['customerId'] != c['id']})
                elsewhere.append('Invoice ' + ref + (' is not one of ' + c['name'] + "'s; it is recorded for " + ', '.join(owners) + '.' if owners
                                                    else ' is not recorded for ' + c['name'] + ' or any other customer.'))
            filter_ = {**(filter_ or {}), 'reference': refs, 'text': ' and '.join(x for x in ((filter_ or {}).get('text'), 'invoice number ' + ', '.join(refs)) if x),
                       'noneText': ' '.join(elsewhere) or None}
        # daysOverdue is unknown where no still-owed amount is recorded (or the replay has one but no due date is on record), so an empty
        # overdue list is not "none are overdue" for those
        unknown = [i for i in self.rows(c, 'open')[0] if which == 'overdue' and not wanted and i['daysOverdue'] is None and (not i['amount'] or i.get('byReplay'))]
        why_not = ('no amount still owed is recorded' if all(not i['amount'] for i in unknown) else 'no due date is recorded' if all(i['amount'] for i in unknown)
                   else 'no amount still owed or no due date is recorded')
        said = {'unknownCount': len(unknown), 'summaryText': 'Overdue not known for ' + plural_text(len(unknown), 'open invoice') + ': ' + why_not + '.'} if unknown else {}
        shown = which if not (wanted or refs) else 'all'
        extra = {'filter': filter_} if filter_ else {}
        self.block('invoices', {'customer': self.named(c), 'which': shown, 'asOf': self.ev.fixture['asOfDate'], 'invoices': rows, 'why': why, 'invoiceCount': len(rows), **said, **extra})
        scope = {'scopeText': 'This list shows every recorded invoice of ' + c['name'] + "; per-invoice amounts are not the customer's account balance."
                 if shown == 'all' and not filter_ else
                 'This list shows only the ' + ('matching' if filter_ else shown) + ' invoices of ' + c['name'] + ", not the customer's complete account balance."}
        complete = {'completeTo': {k: v['completeTo'] for k, v in p['coverage'].items()}, 'completeness': self.completeness(c, p)} if p else {}
        out = {'customerId': c['id'], 'name': c['name'], 'which': shown, 'asOf': self.ev.fixture['asOfDate'], 'invoiceCount': len(rows), 'invoices': model, **extra,
               **self.unmatched(c), **said, **complete, **scope}
        return {**out, 'forModel': dated(invoices_for_model(out))}   # dated here: the wrapper leaves forModel as it is

    def _ownerContext(self, args):
        c = self.customer(args)
        rid = self.case_id(args, required=False) or self.request_id
        rid = rid if rid and self.app.get(rid)['customerId'] == c['id'] else None   # a case's own lines go with its own customer only
        # context_for gives staff only what the owner shared with them, and nothing of the rest, not even that it exists
        lines = [{k: x[k] for k in ('kind', 'quote', 'saidOn', 'until', 'expired')} for x in self.app.context_for(c['id'], self.role, rid)['lines']]
        lines += [{'kind': x.get('kind', 'concern'), 'quote': x['quote'], 'saidOn': x['saidOn'], 'until': None, 'expired': False}   # staff's, seen by both roles
                  for x in (rid and self.app.get(rid).get('concerns')) or ()]
        lines += [{'kind': 'answer', 'quote': x['text'], 'saidOn': x['saidOn'], 'until': None, 'expired': False}   # the owner's, for both roles
                  for x in (rid and self.app.get(rid).get('concernAnswers')) or ()]
        self.block('context', {'customer': self.named(c), 'lines': lines})
        return dated({'customerId': c['id'], 'name': c['name'], 'lines': lines, **({'note': STAFF_SEE} if self.role == 'staff' else {})})

    def _cases(self, args):   # cases are not owner-only; their briefs are not part of the answer
        c = self.customer(args) if args.get('customerId') is not None else None
        ref = _text_arg(args, 'reference', 40, required=False)
        if not c and not ref:
            raise ToolError('INVALID_ARGUMENT', 'Give a customerId from findCustomers or an invoice reference.', executed=False)
        cases, model = self.cases_of(lambda x: x['customerId'] == c['id'] if c else ref_key(x['invoiceReference']) == ref_key(ref))
        self.block('cases', {'customer': c and self.named(c), 'cases': cases, 'caseCount': len(cases)})
        return dated({**({'customerId': c['id'], 'name': c['name']} if c else {'reference': ref}), 'caseCount': len(cases), 'cases': model})

    def _caseDetails(self, args):
        """One case and its customer as this role sees them: the situation's (App.situation), as the case thread shows it. Its
        context block holds what was said about the case and its customer, as the case thread lists it."""
        rid = self.case_id(args)
        s, c = self.app.situation(self.role, request_id=rid), self.ev.customer(self.app.get(rid)['customerId'])
        self.targets.update(['#/case/' + rid] + ([s['customer']['link']] if s['customer'] else []))
        if c:
            self.cased[c['id']] = self.named(c)
            self.block('context', {'customer': self.named(c), 'lines': [{k: x[k] for k in ('kind', 'quote', 'saidOn', 'until', 'expired')}
                                                                         for x in s['case']['contextLines']]})
        return dated({'case': s['case'], 'customer': s['customer']})

    def _whereIs(self, args):
        if not isinstance(args['topic'], str) or args['topic'] not in WHERE_IS:
            raise ToolError('INVALID_ARGUMENT', 'topic must be one of: ' + ', '.join(WHERE_IS) + '.', executed=False)
        place = {'topic': args['topic'], **WHERE_IS[args['topic']]}
        if self.role == 'staff' and args['topic'] == 'completeness':   # only the owner confirms; staff open the statements
            place['label'] = 'Completeness statements'
        self.block('navigation', place)
        return place

    def _prepareCustomer(self, args):
        """A customer is never created here: the person presses Create in the Add customer dialog. A name the records hold
        already, by find_customers or by name key (the key the records refuse a duplicate by), surfaces those customers instead of a
        draft. The name must be one this person wrote, in the message or in a recent turn ("yes, add it"), compared as names are
        (name_key: case, accents and punctuation aside), word by word."""
        name = _text_arg(args, 'name', 120)
        if not name_key(name) or not any(' ' + name_key(name) + ' ' in ' ' + name_key(t) + ' ' for t in [self.text, *self.said]):
            raise ToolError('INVALID_ARGUMENT', 'Use the name exactly as this person wrote it, in the message or a recent turn. If they name none, '
                            'reply asking which name to add.', executed=False)
        found = [c for c, _ in self.ev.find_customers(name)] + [c for c in self.ev.customers if name_key(c['name']) == name_key(name)]
        existing = list({c['id']: c for c in found}.values())[:5]
        if existing:
            self.existing += [{'customerId': c['id'], 'name': c['name']} for c in existing]
            for c in existing:
                self.seen[c['id']] = c
                self.targets.add('#/customers/' + c['id'])
            return {'existing': [{'customerId': c['id'], 'name': c['name'], 'code': c['displayCode']} for c in existing]}
        self.block('draft', {'name': name})
        return {'draft': {'name': name}}

    def _prepareDecision(self, args):
        """The owner's decision, prepared for the Confirm decision button, which calls decide with it: nothing is decided
        here. Code resolves the date: days after the current due date (asked for, never guessed, when none is on record), or a date
        checked as decide checks it; a decline has neither. The case is the one named, else this thread's, else the one case of the
        current customer waiting for the owner (several: ambiguous, for the model to ask which). Each preparation is a new version,
        counted on the request, so a replaced one is never confirmed (decide's preparedVersion); the case keeps every version with its
        status (preparations). One made while another is current revises it: the outcome, the days or date and the reason not given
        keep the current one's (retained), and the current one is superseded. A reason is kept in the owner's own words when it says
        more than the decision (a reason clause of the message, said_reason, when the one passed is not said: reasonFrom 'message'), or when it is the reason of a preparation of this case before, passed on (reasonFrom: its version;
        the current one's when a revision gives none or one saying nothing more). A days or date given that the owner's message does
        not give, nor gave for a preparation of this case before (figuresFrom: its version; the current one's when a revision keeps
        the date), is not used (said_days, said_date): the model is told to ask. A date said makes a new preparation an approval; a new
        decline is prepared only when the message says it (DECLINE_SAID). With nothing prepared, a limit said with no decision word
        (LIMIT_SAID, DECISION_SAID) is asked about, never prepared. Lock held."""
        if self.role != 'owner':
            raise ToolError('FORBIDDEN', 'Only the owner decides.', executed=False)
        outcome, days, day = args.get('outcome'), args.get('days'), args.get('date')
        invalid = ToolError('INVALID_ARGUMENT', 'outcome is approve or decline; approve takes days or a date, not both; decline takes neither.', executed=False)
        if outcome not in (None, 'approve', 'decline') or days is not None and day is not None:
            raise invalid
        if days is not None and not (type(days) is int and 1 <= days <= 365):
            raise ToolError('INVALID_ARGUMENT', 'days must be a whole number from 1 to 365.', executed=False)
        reason, rid = _text_arg(args, 'reason', 2000, required=False), self.case_id(args, required=False) or self.request_id
        if not rid and self.focus:
            rows = [summary(x) for x in self.app.records() if x['status'] == 'awaiting_owner' and x.get('customerId') == self.focus['id']]
            if len(rows) > 1:
                said = [case_summary(s['invoiceReference'], s['customerName'], case_label(s, 'owner'), s['requestedDueDate']) for s in rows]
                return {'ambiguous': [{'requestId': s['id'], 'summary': x} for s, x in zip(rows, said)], 'ask': 'Which case do you mean? ' + ' '.join(said)}
            rid = rows and rows[0]['id']
        r = rid and self.app.get(rid)
        if not r or r['status'] != 'awaiting_owner':
            raise ToolError('INVALID_ARGUMENT', 'No case here is waiting for your decision. Name one: a requestId from cases.', executed=False)
        if self.ev.version_for(r['invoiceId']) != r['analysis']['snapshot']['evidenceVersion']:   # decide would refuse it (STALE_EVIDENCE)
            return {'requestId': r['id'], 'missing': 'refresh', 'ask': 'The records changed since the analysis; refresh the case first.'}
        current = r.get('preparedDecision')
        # a revision keeps the current outcome unless another is given; with nothing prepared, approve, which only a date said makes
        given, outcome = outcome, outcome or (current or {}).get('outcome') or 'approve'
        if given is None and not current and DECLINE_SAID.search(self.text):   # "decline it" with no outcome passed: never an implied approve
            return {'requestId': r['id'], 'missing': 'outcome', 'ask': 'Approve or decline?'}
        if not current and given is None and not args.get('remember') and LIMIT_SAID.search(self.text) and not DECISION_SAID.search(self.text):   # "up to 14 days this time"
            return {'requestId': r['id'], 'missing': 'outcome', 'ask': 'Is that a decision to approve, or guidance to keep?'}
        if outcome == 'decline' and (days, day) != (None, None):
            raise invalid
        keep = bool(current) and outcome == current['outcome'] == 'approve' and days is None and day is None   # the date stays
        s = self.app.case_situation(r, 'owner')
        ref, (due, floor) = (s['invoice'] or {}).get('reference'), self.app.due_and_floor(self.ev, r)
        named = {w.lower() for w in re.findall(r'[^\W\d_]+', (s['customer'] or '') + ' ' + (ref or ''))}
        says = lambda t: t and [w for w in re.findall(r'[^\W\d_]+', t.lower()) if not (w in DECISION_WORDS or w in NUMBER_WORDS or w in named or
                                                                                  re.fullmatch(MONTH_WORD, w))]
        more = says(reason)
        remember = args.get('remember', (current or {}).get('remember'))   # kept across revisions unless replaced
        problem = remember is not None and remember_problem(remember)
        if problem:
            raise ToolError('INVALID_ARGUMENT', problem[0], executed=False)
        # the reason: said in this message, else a reason clause of the message ("because …": said_reason; reasonFrom 'message'), else
        # one said for a preparation of this case before (the latest with it; case and spacing aside), else, revising, the current
        # one's when none is given or it says nothing more than the decision; else no reason
        norm, clause = lambda t: ' '.join(t.split()).casefold(), said_reason(self.text)
        said = bool(more) and appears_in(reason, self.text)
        earlier = next((x for x in reversed(r.get('preparations', [])) if reason and x['reason'] != NO_REASON and norm(x['reason']) == norm(reason)), None)
        # the clause, passed as it is (the Lab fills it in) or in place of a reason not said; never over an earlier one passed again
        heard = bool(says(clause)) and (norm(reason) == norm(clause) if said else not earlier)
        if heard:
            reason, more, said = clause, True, True
        source = None if said else earlier or (current if current and not more else None)
        # a days or date given: said in this message, else, when the message states no figure of its own ("as it was"), one of a
        # preparation of this case before (the latest with it); kept: the current one's
        said_now = days is None and day is None or (days in said_days(self.text) if days is not None else said_date(day, self.text))
        figures = None if said_now or STATES_FIGURE.search(re.sub(r'\b[A-Z]{2,}-\d+\b', ' ', self.text, flags=re.I)) else next((x for x in reversed(r.get('preparations', [])) if x['days' if days is not None else 'approvedDueDate']
                                              == (days if days is not None else day)), None)
        figures_from = figures or (current if keep else None)
        retained = [k for k, kept in (('outcome', current and given is None),
                                      (('days' if days is not None else 'date') if figures else (current or {}).get('givenAs') or 'date', figures_from),
                                      ('reason', source)) if kept]
        if outcome == 'approve' and days is None and day is None and not keep:
            return {'requestId': r['id'], 'missing': 'days', 'ask': 'How many days, or until which date?'}
        if not (said_now or figures):
            return {'requestId': r['id'], 'missing': 'days' if days is not None else 'date', 'ask': 'How many days, or until which date?'}
        if outcome == 'decline' and (current or {}).get('outcome') != 'decline' and not DECLINE_SAID.search(self.text):   # a new decline, in their words
            return {'requestId': r['id'], 'missing': 'outcome', 'ask': 'Approve or decline?'}
        if days is not None and due is None:
            return {'requestId': r['id'], 'missing': 'currentDue', 'ask': 'No due date is on record for invoice ' + str(ref) + ', so ' + days_text(days) +
                    ' cannot be counted from it. Which date should it move to?'}
        approved = self.extended(due, floor, days, current['approvedDueDate'] if keep else day) if outcome == 'approve' else None   # checked again
        n = (calendar_date(approved) - calendar_date(due)).days if approved and due else None
        limit, sug = s['dayLimit'] and s['dayLimit']['days'], s['suggestion']
        p = {'version': r.get('preparedVersion', 0) + 1, 'by': self.by, **self.trail, 'at': now(), 'outcome': outcome, 'approvedDueDate': approved, 'days': n,
             'givenAs': 'days' if days is not None else 'date' if day is not None else current.get('givenAs') if keep else None,   # how the date was asked
             'reason': reason if said else source['reason'] if source else NO_REASON,
             'comparison': {'askedDays': s['extensionDays'], 'days': n, 'limitDays': limit, 'withinLimit': None if n is None or limit is None else n <= limit},
             'suggestionShown': {k: sug[k] for k in ('version', 'outcome', 'approvedDueDate')} if sug and sug['status'] == 'given' else None,
             **({'remember': {'text': remember['text'].strip(), 'keepForCustomer': remember.get('keepForCustomer', False), 'until': remember.get('until')}} if remember else {})}
        entry = {**{k: p[k] for k in ('version', 'outcome', 'approvedDueDate', 'days', 'reason', 'by', 'at', 'remember') if k in p}, **self.shown, 'status': 'current',
                 'approvedDueDateText': approved and display_date(approved)}
        with self.app.db:
            self.app.end_preparation(r, 'superseded', self.by, self.trail, replacedBy=p['version'])
            r.update({'preparedVersion': p['version'], 'preparedDecision': p, 'preparations': r.get('preparations', []) + [entry]})
            self.app.save(r)
            self.app.event(r, 'decision.prepared', p)
        shown, c = {**{k: v for k, v in p.items() if k not in ('by', 'at', 'givenAs')}, 'requestId': r['id'], 'invoiceReference': ref, 'askedDate': s['askedDate'],
                    'currentDue': due}, self.ev.customer(r['customerId'])
        self.block('prepared', {**shown, 'customer': c and self.named(c)})
        self.targets.add('#/case/' + r['id'])
        return dated({'requestId': r['id'], 'prepared': {k: v for k, v in shown.items() if k not in ('requestId', 'suggestionShown')},
                      'revisionOf': current and current['version'], 'retained': retained, 'reasonFrom': 'message' if heard else source and source['version'],
                      'figuresFrom': figures_from and figures_from['version'],
                      'note': 'Prepared, not decided: the owner confirms it with the Confirm decision button.'})

    @staticmethod
    def extended(due, floor, days, day):
        """The date an extension gives, checked as decide checks an approved date: days after the current due date (due), or a date;
        after floor (App.due_and_floor). ToolError when the days or the date are not valid, or the date is not after floor."""
        if days is not None and not (type(days) is int and 1 <= days <= 365):
            raise ToolError('INVALID_ARGUMENT', 'days must be a whole number from 1 to 365.', executed=False)
        try:
            d = calendar_date(due) + timedelta(days=days) if days is not None else calendar_date(day)
        except (ValueError, TypeError):
            raise ToolError('INVALID_ARGUMENT', 'date must be a real date, YYYY-MM-DD.', executed=False) from None
        if d <= floor:
            raise ToolError('INVALID_ARGUMENT', display_date(d.isoformat()) + ' is not after ' + display_date(floor.isoformat()) + '; ask for a later date.',
                            executed=False)
        return d.isoformat()

    def _compareExtension(self, args):
        """An extension of a case compared, with nothing prepared or recorded: the date days after the current due date, or a date,
        gives (extended, as prepareDecision works it out), against the date and days asked and the day limit this role may see
        (case_situation: staff only a limit in a line the owner shared with them). With a second option (otherDays or otherDate) the
        result also holds it, 'other', the same way, and daysBetween the two dates ("compare 20 November with 27 November"). Unlike
        prepareDecision, the days or date need not be in the person's words, since nothing is kept. Each date also in words, null when
        there is none. Lock held."""
        days, day, other_days, other_day = args.get('days'), args.get('date'), args.get('otherDays'), args.get('otherDate')
        if days is None and day is None:
            raise ToolError('MISSING', 'Give the days after the current due date, or a date, to compare.', executed=False)
        if days is not None and day is not None:
            raise ToolError('INVALID_ARGUMENT', 'Give days or a date, not both.', executed=False)
        second = other_days is not None or other_day is not None
        if other_days is not None and other_day is not None:
            raise ToolError('INVALID_ARGUMENT', 'Give otherDays or otherDate, not both.', executed=False)
        r = self.app.get(self.case_id(args))
        if not r.get('invoiceId'):
            raise ToolError('MISSING', 'The invoice of this request is not identified yet, so there is no due date to compare with.', executed=False)
        (due, floor), s = self.app.due_and_floor(self.ev, r), self.app.case_situation(r, self.role)
        if (days is not None or other_days is not None) and due is None:
            raise ToolError('MISSING', 'No due date is on record for this invoice, so days cannot be counted from it. Give a date.', executed=False)
        limit = s['dayLimit']

        def option(d, dt):
            proposed = self.extended(due, floor, d, dt)
            n = due and (calendar_date(proposed) - calendar_date(due)).days
            return proposed, n, None if n is None or not limit else n <= limit['days']
        proposed, n, within = option(days, day)
        result = {'requestId': r['id'], 'invoiceReference': (s['invoice'] or {}).get('reference'), 'currentDue': due, 'proposedDate': proposed,
                  'daysFromDue': n, 'askedDate': s['askedDate'], 'askedDays': s['extensionDays'], 'limitDays': limit and limit['days'],
                  'latestWithinLimit': limit and limit['latestDate'], 'withinLimit': within}
        if second:
            other, m, other_within = option(other_days, other_day)
            result['other'] = {'proposedDate': other, 'daysFromDue': m, 'withinLimit': other_within}
            result['daysBetween'] = (calendar_date(other) - calendar_date(proposed)).days   # negative when the second is earlier
        c = self.ev.customer(r['customerId'])
        self.block('comparison', {**result, 'customer': c and self.named(c)})
        self.targets.add('#/case/' + r['id'])
        return {**dict.fromkeys(k + 'Text' for k in ('currentDue', 'proposedDate', 'askedDate', 'latestWithinLimit')), **dated(result)}

    def _withdrawPreparation(self, args):
        """The owner cancels the decision prepared on a case: nothing is left to confirm (decide refuses its version), and the case
        still waits for the owner's decision. It is not a decline. With a version, only that preparation, while it is the current one
        (STALE otherwise). Lock held."""
        if self.role != 'owner':
            raise ToolError('FORBIDDEN', 'Only the owner prepares and withdraws decisions.', executed=False)
        version = args.get('version')
        if version is not None and type(version) is not int:
            raise ToolError('INVALID_ARGUMENT', 'version must be a whole number.', executed=False)
        r = self.app.get(self.case_id(args))
        p, ref = r.get('preparedDecision'), summary(r)['invoiceReference']   # the reply names the case by its reference
        if not p:
            return {'requestId': r['id'], 'invoiceReference': ref, 'withdrawn': False,
                    'note': 'No prepared decision is waiting.' if r.get('preparedVersion') else 'Nothing was prepared.'}
        if version is not None and version != p['version']:
            raise ToolError('STALE', 'That prepared decision was replaced; the current one is version ' + str(p['version']) + '.', executed=False)
        with self.app.db:
            self.app.end_preparation(r, 'withdrawn', self.by, self.trail)   # preparedVersion stays: a later preparation is a new version
            self.app.save(r)
        self.targets.add('#/case/' + r['id'])
        return {'requestId': r['id'], 'invoiceReference': ref, 'withdrawn': True, 'version': p['version']}

    def _withdrawRequest(self, args):
        """Staff or the owner close a request opened by mistake, with a reason, while no decision exists: its status becomes withdrawn
        (event request.withdrawn), it leaves both queues, and a prepared decision is withdrawn with it. A request being prepared
        cannot be withdrawn until it settles. Lock held."""
        reason = _text_arg(args, 'reason', 500).strip()
        r = self.app.get(self.case_id(args))
        if r['status'] not in STATES_BEFORE_DECISION or r.get('decision'):
            raise ToolError('INVALID_ARGUMENT', 'This request is ' + ('already withdrawn' if r['status'] == 'withdrawn' else 'decided') + ', so it cannot be withdrawn.', executed=False)
        if r['status'] in ACTIVE_STATES:
            raise ToolError('INVALID_ARGUMENT', 'The agent is still preparing this request. Try again in a moment.', executed=False)
        with self.app.db:
            self.app.end_preparation(r, 'withdrawn', self.by, self.trail)
            r['status'] = r['task']['status'] = 'withdrawn'
            r['version'] += 1
            r['withdrawn'] = {'reason': reason, 'by': self.by, 'role': self.role, **self.trail, 'at': now()}
            r.pop('withStaff', None)
            r.pop('withOwner', None)
            self.app.save(r)
            self.app.event(r, 'request.withdrawn', {'reason': reason, 'by': self.by, 'role': self.role, **self.trail})
            self.app.dg_request_withdrawn(r, reason)
        self.targets.add('#/case/' + r['id'])
        return {'requestId': r['id'], 'invoiceReference': summary(r)['invoiceReference'], 'withdrawn': True, 'request': True, 'reason': reason}

    def _workQueue(self, args):
        """What waits on whom across every customer's cases not yet decided, for this role (waiting_on): forYou, those this role acts on
        next, and waitingOnOthers, the rest: waiting on the other role, or on no one while the agent prepares one or a decision is saved.
        Each in the case list's status words (case_label), with why (queue_why); waitingOn is 'you' in forYou, the other role (or
        'none') in waitingOnOthers, and summaryText says it all in words for the model to quote (queue_text). Lock held."""
        rows, records = [], self.app.records()
        for r in records:
            if r['status'] in STATES_BEFORE_DECISION or r['status'] == 'decided':
                x, on, c = summary(r, records), waiting_on(r, self.role), self.ev.customer(r.get('customerId'))
                rows.append({'requestId': r['id'], 'invoiceReference': x['invoiceReference'], 'customer': c and {'customerId': c['id'], 'name': c['name']},
                             'status': r['status'], 'statusLabel': case_label(x, self.role), 'waitingOn': on, 'why': queue_why(r, on, self.role),
                             'askedDateText': x['requestedDueDate'] and display_date(x['requestedDueDate']), 'link': '#/case/' + r['id'],
                             'ordinal': x['ordinal'], 'flags': x['flags']})
        self.targets.update(x['link'] for x in rows)
        mine, others = [{**x, 'waitingOn': 'you'} for x in rows if x['waitingOn'] == self.role], [x for x in rows if x['waitingOn'] != self.role]
        dmine, dothers = self._decision_queue()
        summary_text = queue_text(mine, others, self.role) + decision_queue_text(dmine, dothers, self.role)
        return dated({'forYou': mine, 'waitingOnOthers': others, 'decisionCasesForYou': dmine, 'decisionCasesWaitingOnOthers': dothers,
                      'asOf': self.ev.as_of.isoformat(), 'summaryText': summary_text,
                      'forModel': agent_views.queue_for_model(self.role, summary_text, dmine, len(dothers), mine)})

    def _decision_queue(self):
        """The live decision cases (not the requests) as the work queue lists them, for this role: (waiting for this role, waiting on the other). The Owner acts on
        awaiting_owner and on_hold cases (link #/review); Staff on gathering_evidence cases (link: the evidence request). Each: caseId, customer, kind, status, exposure
        text (or the invoice and date), since (the case's last change, ISO) and its sinceText, link, needs (what Staff must provide). Lock held."""
        mine_status = ('awaiting_owner', 'on_hold') if self.role == 'owner' else ('gathering_evidence',)
        mine, others = [], []
        for x in self.app.dg_cases("dataset='live'"):
            if x['status'] not in LIVE_CASE:
                continue
            kf = (x.get('evaluation') or {}).get('keyFacts') or {}
            what = (kf.get('exposure') or {}).get('text') or (kf.get('invoiceReference') and ('invoice ' + str(kf['invoiceReference']) + (' to ' + display_date(kf['requestedDueDate']) if kf.get('requestedDueDate') else ''))) or None
            link = '#/review' if x['status'] != 'gathering_evidence' and self.role == 'owner' else (x.get('actionId') and '#/actions/' + x['actionId']) if x['status'] == 'gathering_evidence' else None
            row = {'caseId': x['id'], 'customer': x.get('customerName') or '', 'kind': x['kind'], 'status': x['status'], 'exposureText': what,
                   'since': x['updatedAt'], 'sinceText': display_date(x['updatedAt'][:10]), 'link': link or '#/review',
                   'needs': (x.get('needs') or []) if x['status'] == 'gathering_evidence' else []}
            (mine if x['status'] in mine_status else others).append(row)
        self.targets.update(r['link'] for r in mine)
        return mine, others

    def _listRequests(self, args):
        """The requests of a customer, of an invoice reference, or of every customer when neither is given (cases gives one customer's
        or invoice's, unfiltered), by status: open (not yet decided; the default), decided or all; each in the request list's shape
        (summary) with who acts next (waiting_on). Lock held."""
        status = args.get('status') or 'open'
        if status not in ('open', 'decided', 'all'):
            raise ToolError('INVALID_ARGUMENT', 'status must be open, decided or all.', executed=False)
        c = self.customer(args) if args.get('customerId') is not None else None
        ref = _text_arg(args, 'invoiceReference', 40, required=False)
        records = self.app.records()
        rows = [{**x, 'waitingOn': waiting_on(r, self.role)} for r in records for x in [summary(r, records)]
                if (not c or x['customerId'] == c['id']) and (not ref or x['invoiceReference'] and ref_key(x['invoiceReference']) == ref_key(ref))
                and (status == 'all' or (r['status'] in STATES_BEFORE_DECISION) == (status == 'open'))]
        self.targets.update('#/case/' + x['id'] for x in rows)
        return dated({'requests': rows})

    def _prepareHoldingMessage(self, args):
        """A short message for the customer about a request not yet decided, written by code for the person to copy: the invoice,
        where the request stands and the current due date. It promises no date, outcome or amount, and nothing is sent or kept.
        Lock held."""
        r = self.app.get(self.case_id(args))
        if r['status'] not in STATES_BEFORE_DECISION:
            raise ToolError('INVALID_ARGUMENT', 'This request is decided: the reply to send is in the case.', executed=False)
        ref, due = summary(r)['invoiceReference'], r.get('invoiceId') and self.app.due_and_floor(self.ev, r)[0]
        text = (('Your request about invoice ' + ref if ref else 'Your request') + (' is with the owner' if r['status'] == 'awaiting_owner' else
                ' is being checked before it goes to the owner') + '; we will confirm once it is decided.' +
                (' The current due date is ' + display_date(due) + '.' if due else ''))
        self.targets.add('#/case/' + r['id'])
        return {'requestId': r['id'], 'text': text, 'status': r['status']}

    def _raiseConcern(self, args):
        """Staff raise a concern about a case not yet decided, in their own words as written in the message: one case line, kind
        'concern', kept on the request for both roles to see, and the case waits on the owner too (waiting_on) until it is decided. It
        decides and changes nothing else. Lock held."""
        if self.role != 'staff':
            raise ToolError('FORBIDDEN', 'Staff raise concerns; the owner decides.', executed=False)
        text = _text_arg(args, 'text', 2000)
        if not appears_in(text, self.text):
            raise ToolError('INVALID_ARGUMENT', 'Use the concern exactly as this person wrote it in the message.', executed=False)
        r = self.app.get(self.case_id(args))
        if r['status'] not in STATES_BEFORE_DECISION:
            raise ToolError('INVALID_ARGUMENT', 'This request is decided; a concern no longer changes it.', executed=False)
        assessed = r.get('assessment')   # a concern on an assessed case says which recommendation it disagrees with
        reply = returned(r)   # the case is with staff because of an owner answer of any kind: staff's words reply to it
        line = {'id': uid('line'), 'quote': text.strip(), 'kind': 'reply' if reply else 'concern', 'by': 'staff', **self.shown, 'saidOn': self.today.isoformat(),
                **({'disagreesWith': assessed['recommendation']['outcome']} if assessed and not reply else {})}
        with self.app.db:
            r['concerns'] = r.get('concerns', []) + [{**line, **self.trail, 'at': now()}]   # the time is kept, never shown to the model
            r.pop('withStaff', None)   # staff replied: the case is the owner's again
            r.pop('withOwner', None)
            if assessed and not reply and sum(1 for x in open_concerns(r) if x.get('kind') != 'reply') >= authority_of(self.app.fixture())['maxConcernRounds']:   # the owner takes it from here
                r['escalated'] = {'reason': 'concern rounds', 'at': now()}
            self.app.save(r)
            self.app.event(r, 'concern.raised', {**line, **self.trail, 'byId': self.by})
        self.targets.add('#/case/' + r['id'])
        return {'requestId': r['id'], 'invoiceReference': summary(r)['invoiceReference'], 'line': line}

    ANSWER_WHY = {'explain': 'the owner answered the concern', 'guidance': 'the owner changed the guidance'}
    ANSWER_HELD = {'explain': 'explanation given; your decision is still pending', 'guidance': 'guidance given; your decision is still pending'}
    ANSWER_NEXT = {'needs_info': 'staff', 'explain': 'staff', 'guidance': 'owner'}   # who acts next when the caller does not say

    def _answerConcern(self, args):
        """The owner answers a concern staff raised, in words they wrote, without deciding the case. What the answer is sets the status
        and the next person: needs_info (the owner asks staff for something), explain (the owner explains) and guidance (the owner
        gives guidance that holds beyond this reply: a confirmed statement for the customer, visible to staff as these words, with an
        optional end date). Who acts next is `next` ('owner' | 'staff'), chosen by the caller from the owner's words and not by the
        kind: needs_info is always staff; explain and guidance default to staff and owner (the decision is still pending with the owner)
        and the caller says otherwise when the owner asks staff to act now, or says the case still waits for them. Only next 'staff'
        sends the case to staff (withStaff, the queue's why for each kind); next 'owner' leaves it with the owner (withOwner: the queue's
        why reads "<kind> given; your decision is still pending" for the owner, "the owner's decision is still pending" for staff,
        who see the answer on the case). A final decision stays prepareDecision. One
        case line, kind 'answer', visible to both roles, the concern it answers gets answeredBy, a concern-rounds escalation is
        cleared and the rounds start again. Lock held."""
        if self.role != 'owner':
            raise ToolError('FORBIDDEN', 'The owner answers concerns; staff raise them.', executed=False)
        text, kind = _text_arg(args, 'text', 2000), args.get('kind')
        if kind not in ANSWER_KINDS:
            raise ToolError('INVALID_ARGUMENT', 'kind must be needs_info, explain or guidance; a final decision is prepared with prepareDecision.', executed=False)
        if not appears_in(text, self.text):
            raise ToolError('INVALID_ARGUMENT', 'Use the answer exactly as this person wrote it in the message, only the part meant for staff.', executed=False)
        nxt = args.get('next', self.ANSWER_NEXT[kind])
        if nxt not in ('owner', 'staff') or kind == 'needs_info' and nxt != 'staff':
            raise ToolError('INVALID_ARGUMENT', "next must be 'owner' or 'staff' (who acts next), and is 'staff' when the owner asks staff for information.", executed=False)
        until = args.get('until')
        if until is not None:
            if kind != 'guidance':
                raise ToolError('INVALID_ARGUMENT', 'An end date goes with guidance only.', executed=False)
            try:
                calendar_date(until)
            except (ValueError, TypeError):
                raise ToolError('INVALID_ARGUMENT', 'until must be YYYY-MM-DD.', executed=False)
        r = self.app.get(self.case_id(args))
        if r['status'] not in STATES_BEFORE_DECISION:
            raise ToolError('INVALID_ARGUMENT', 'This request is decided; an answer no longer changes it.', executed=False)
        if kind == 'guidance' and not r.get('customerId'):
            raise ToolError('INVALID_ARGUMENT', 'Guidance is kept for a customer, and this request has none identified yet.', executed=False)
        text = text.strip()
        waiting = open_concerns(r)
        line = {'id': uid('line'), 'kind': 'answer', 'by': 'owner', **self.shown, 'text': text, 'answers': waiting[-1]['id'] if waiting else None,
                'saidOn': self.today.isoformat(), 'responseKind': kind}
        first = kind == 'guidance' and not any(x.get('responseKind') == 'guidance' for x in r.get('concernAnswers', []))   # the first guidance on this case is given, later ones change it
        why = 'the owner asked: ' + text if kind == 'needs_info' else ('the owner gave guidance' if first else self.ANSWER_WHY[kind]) if nxt == 'staff' else self.ANSWER_HELD[kind]
        note = kind == 'guidance' and self.app.build_statement(
            self.actor, text, thread_id=None, visibility='staff', status='confirmed', scope={'kind': 'customer', 'customerId': r['customerId']},
            lines=[{'kind': 'guidance', 'quote': text, 'until': until}], source={'kind': 'concern_answer', 'answerId': line['id']})
        with self.app.db:
            if note:
                self.app.save_statement(note)
            r['concernAnswers'] = r.get('concernAnswers', []) + [{**line, **self.trail, 'at': now()}]
            for c in waiting[-1:]:
                c['answeredBy'] = line['id']
            r['roundsFrom'] = len(r.get('concerns') or [])   # the rounds start again
            if (r.get('escalated') or {}).get('reason') == 'concern rounds':
                r.pop('escalated')
            r.pop('withStaff', None)
            r.pop('withOwner', None)
            r['withStaff' if nxt == 'staff' else 'withOwner'] = {'kind': kind, 'why': why, 'answerId': line['id'], 'at': now()}
            self.app.save(r)
            self.app.event(r, 'concern.answered', {**line, **self.trail, 'byId': self.by})
        self.targets.add('#/case/' + r['id'])
        return {'requestId': r['id'], 'invoiceReference': summary(r)['invoiceReference'], 'line': line, 'kind': kind, 'next': nxt, 'waitingOn': nxt, 'why': why,
                'statement': ('Back with staff: ' if nxt == 'staff' else 'Still with the owner: ') + why[0].upper() + why[1:].rstrip() + ('' if why.rstrip().endswith('.') else '.')}

    def assess(self, c, r):
        """The assessment of customer c as of today, and of case r when there is one: the replay's facts (behaviour.facts_view), the
        owner's limits checked against them (checks_for), the recommendation derived from those checks alone (recommend), the decisions
        recorded and fixed limitations. No model runs and no score is formed. The latest assessment of a case not yet decided is kept
        on it (assessment) as the next version, with its calculation details (basis: assessment_basis, from the replay's own trail and
        the values each check compared); the result carries only basisSummary. Lock held."""
        doc = self.app.fixture()
        settings = settings_of(doc)
        template, auth, cid = {'currency': settings['currency'], 'scale': settings['scale']}, authority_of(doc), c['id']
        mine = customer_records(doc, cid)
        features = assessment_facts(mine['invoices'], mine['payments'], doc.get('allocations', []), mine['openingBalances'], self.today, r and r.get('invoiceId'))
        asked = r and self.app.case_situation(r, self.role)
        measured = []   # what each check compared, for the calculation details
        checks = checks_for(auth, features, asked and asked['extensionDays'], template, measured)
        facts, rec = facts_view(features, template, self.today), recommend(auth, checks)
        shown = {**auth, 'hardRules': list(auth['hardRules']), 'maxOutstandingText': auth['maxOutstanding'] and money_text(auth['maxOutstanding'])}
        calc = assessment_basis(self.ev, c, r, mine, features, checks, measured, rec, shown, template, self.today)
        policy = {'authority': shown, 'checks': checks, 'summaryText': ' '.join(x['sentence'] for x in checks if not x['passes']) or 'Every check passes.'}
        everyone = [x for x in self.app.records() if x.get('decision')]
        mine = [x for x in everyone if x.get('customerId') == cid]
        similar = [{'requestId': x['id'], 'reference': summary(x)['invoiceReference'], 'askedFor': (((x.get('analysis') or {}).get('snapshot') or {}).get('facts') or {}).get('requestedDueDate'),
                    'outcome': x['decision']['outcome'], 'decidedOn': x['decision']['decidedAt'][:10], 'reason': x['decision']['reason']}
                   for x in sorted(mine, key=lambda x: x['decision']['decidedAt'], reverse=True)[:5]]
        concerns = [{'requestId': x['id'], 'quote': q['quote'], 'saidOn': q['saidOn']} for x in self.app.records() if x.get('customerId') == cid
                    and x['status'] in STATES_BEFORE_DECISION for q in open_concerns(x) if q.get('kind') != 'reply']
        basis = {'recorded': 'Every payment is allocated to invoices by a record.', 'fifo': 'No payment is allocated by a record, so payments are applied to the oldest '
                 'invoice first; that is an assumption, not a record.', 'mixed': 'Some payments are allocated by a record; the rest are applied to the oldest invoice first, '
                 'which is an assumption, not a record.'}[facts['allocationBasis']]
        basis += (' ' + facts['prepaymentText']) if facts.get('prepaymentText') else ''
        basis += (' ' + facts['openingCreditText']) if facts.get('openingCreditText') else ''
        basis += (' ' + facts['undatedText']) if facts.get('undatedText') else ''
        out = {'requestId': r and r['id'], 'recorded': False, 'version': None, 'facts': facts, 'policy': policy, 'model': {'status': 'unavailable', 'reason': NO_MODEL},
               'recommendation': rec, 'evidence': {'decisionsRecorded': len(everyone), 'decisionsForThisCustomer': len(mine), 'similar': similar, 'openConcerns': concerns},
               'limitations': [basis, 'No model runs when a request is assessed; every figure is computed from the records.',
                               'Overdue is judged by the due dates recorded on the invoices, not by extensions already granted.',
                               'The records are one company over about one year; they describe what was recorded, not what will happen.']}
        if r and r['status'] in STATES_BEFORE_DECISION:
            last = r.get('assessment')
            calc['assessmentVersion'] = last['version'] + 1 if last else 1
            if last and last.get('basis'):   # an earlier card asks for its own version's details: the last few stay readable
                r['earlierBases'] = (r.get('earlierBases') or [])[-(KEEP_BASES - 1):] + [{'version': last['version'], 'at': last['at'], 'basis': last['basis']}]
            r['assessment'] = {'at': now(), 'version': calc['assessmentVersion'], 'facts': facts, 'policy': policy, 'recommendation': rec,
                                'evidence': out['evidence'], 'basis': calc, 'authority': auth,   # what it read: a later change makes it stale (assessment_stale)
                                'evidenceVersion': r.get('invoiceId') and self.ev.version_for(r['invoiceId'])}
            with self.app.db:
                self.app.save(r)
            out.update(recorded=True, version=r['assessment']['version'])
        out['basisSummary'] = basis_summary(calc)   # the details themselves: GET api/requests/<id>/basis (the model is given only this)
        if self.role == 'staff':   # plain and complete in itself for staff; the stored assessment keeps the neutral sentence
            out = {**out, **{k: staff_plain({'policy': policy, 'recommendation': rec})[k] for k in ('policy', 'recommendation')}}
        return out

    def _assessRequest(self, args):
        """What the records show of a case's customer and how it stands against the owner's limits, as above (assess): of the case named,
        else this thread's, else of a customer when one is named or current. Lock held."""
        if args.get('requestId') is None and (args.get('customerId') is not None or not self.request_id):
            c, r = self.customer({'customerId': args.get('customerId', 'current')}), None
        else:
            r = self.app.get(self.case_id({'requestId': args.get('requestId', 'current')}))
            if r['status'] in ACTIVE_STATES:   # the analysis run has not settled: no customer or invoice is found yet
                raise ToolError('CASE_PREPARING', 'The case is still being prepared; ask again in a moment.', executed=False)
            if not r.get('customerId'):
                raise ToolError('INVALID_ARGUMENT', 'No customer is identified on this case yet, so there is nothing to assess.', executed=False)
            c = self.ev.customer(r['customerId'])
            self.about = c
        out = self.assess(c, r)   # what is stored on the case stays as it was; the completeness is only said with the result
        p = self.views().get('customers', {}).get(c['id'])
        return {**out, 'completeness': self.completeness(c, p)} if p else out

    def _actWithinAuthority(self, args):
        """Staff approve a case the owner's limits allow, as the owner would have approved it, for the date asked: allowed only when the
        assessment recomputed now recommends approve_within_authority. Otherwise NOT_WITHIN_AUTHORITY naming what fails, and the case
        stays with the owner, marked escalated. The decision is recorded with the limits and the checks it rested on. Lock held."""
        if self.role != 'staff':
            raise ToolError('FORBIDDEN', "Staff act within the owner's authority; the owner decides.", executed=False)
        r = self.app.get(self.case_id(args))
        # A request a person confirmed from an action is the owner's to decide, whatever the limits say: refused first, before anything is assessed
        # or stored, so no staff path (this tool, whoever presses it) decides it. The owner's own paths (App.decide) are unchanged.
        if r['intake'].get('structured') is not None:
            raise APIError(409, 'OWNER_REVIEW_REQUIRED', 'This request was submitted from a confirmed action for the owner to review. Only the owner decides it.')
        if r['status'] != 'awaiting_owner' or r['decision'] is not None:
            raise ToolError('INVALID_ARGUMENT', 'There is no pending owner decision on this request, so there is nothing to act on.', executed=False)
        if (r.get('escalated') or {}).get('reason') == 'concern rounds':
            raise ToolError('NOT_WITHIN_AUTHORITY', 'After the concern rounds this case waits for the owner, so staff cannot act on it.', executed=False,
                            extra={'failing': ['concern rounds']})
        a = self.assess(self.ev.customer(r['customerId']), r)
        failing = [x for x in a['policy']['checks'] if not x['passes']]
        if a['recommendation']['outcome'] != 'approve_within_authority':
            with self.app.db:
                r['escalated'] = {'reason': failing[0]['label'] if failing else 'nothing here is within the staff limits', 'at': now()}
                self.app.save(r)
            raise ToolError('NOT_WITHIN_AUTHORITY', "This is not within the owner's authority, so it stays with the owner: " +
                            (' '.join(x['sentence'] for x in failing) or a['policy']['summaryText']), executed=False,
                            extra={'failing': [x['label'] for x in failing] or ['no day limit is set for staff']})
        an, current = r['analysis'], self.ev.version_for(r['invoiceId'])
        if current != an['snapshot']['evidenceVersion']:
            raise ToolError('STALE_EVIDENCE', 'The records changed since the analysis. Refresh the case before acting.', executed=False)
        asked = self.app.case_situation(r, self.role)['askedDate']
        due, floor = self.app.due_and_floor(self.ev, r)
        try:
            valid = calendar_date(asked) > floor
        except (ValueError, TypeError):
            valid = False
        if not valid:
            raise ToolError('INVALID_ARGUMENT', 'The date asked is not after ' + display_date(floor.isoformat()) + ', so the owner decides.', executed=False)
        r['decision'] = {'id': uid('decision'), 'requestId': r['id'], 'requestVersionBefore': r['version'], 'analysisId': an['id'], 'evidenceVersion': current,
                         'outcome': 'approve', 'approvedDueDate': asked, 'reason': "Within the owner's authority. " + ' '.join(a['recommendation']['reasons']),
                         'approvedExtensionDays': (calendar_date(asked) - calendar_date(due)).days if due else None,
                         'scope': {'kind': 'single_invoice', 'invoiceId': r['invoiceId']}, 'decidedBy': self.by, **self.trail, 'decidedAt': now(),
                         'decisionSource': 'staff_within_authority', 'authority': a['policy']['authority'],
                         'assessment': {'facts': a['facts'], 'checks': a['policy']['checks']}, **followed(r['assessment'], 'approve'),
                         'basis': frozen_basis(r['assessment'])}   # the assessment just made, frozen with the decision
        r['suggestionSeen'], r['evidenceSeen'] = None, self.ev.decision_evidence(r['invoiceId'])
        with self.app.db:
            r['version'] += 1
            r['status'] = r['task']['status'] = 'decided'
            self.app.event(r, 'decision.committed', r['decision'])
            self.app.end_preparation(r, 'withdrawn', self.by, self.trail)
            self.app.save(r)
        self.app.finish(r)
        self.targets.add('#/case/' + r['id'])
        d = r['decision']
        return {'requestId': r['id'], 'invoiceReference': summary(r)['invoiceReference'], 'outcome': d['outcome'], 'approvedDueDate': asked,
                'decisionSource': d['decisionSource'], 'reason': d['reason'], **({k: d[k] for k in ('actorName', 'actorRole')} if d.get('actorName') else {})}

    def _requestSuggestion(self, args):
        """A new suggestion on a case now, formed as the automatic step forms one (App.suggest): its inputs read under the lock, the
        model asked without it, the result kept as the next version only if the data, the case, its analysis and the setting are
        unchanged. Returns the case's suggestion as the situation has it: given, withheld or failed with the code's sentences."""
        if self.role != 'owner':
            raise ToolError('FORBIDDEN', 'Only the owner sees suggestions.', executed=False)
        with self.app.lock:
            rid, epoch = self.case_id(args), self.app.epoch
            r = self.app.get(rid)
            if not self.app.suggestable(r):
                raise ToolError('INVALID_ARGUMENT', 'Only a case the agent prepared, waiting for your decision, has a suggestion.', executed=False)
            if not self.app.meta('showSuggestions'):
                return ToolDispatcher._ok('requestSuggestion', args, {'requestId': rid, 'suggestion': {'status': 'off', 'withheldBecause': []}})
            brief, analysis = r['analysis']['brief'], r['analysis']['id']
            inputs = suggestion_inputs(brief, brief['questions'], self.app.context_for(r['customerId'], 'owner', rid),
                                       [{'field': k, 'value': v} for k, v in r['answers'].items()])
        found = suggestion_step(self.adapter, CALLERS[self.app.agent_mode], inputs, self.timeout)
        self.model_calls += found['stats'].get('suggestModelCalls', 0)
        with self.app.lock:
            r = self.app.epoch == epoch and self.app.get(rid)
            if not (r and self.app.suggestable(r) and r['analysis']['id'] == analysis and self.app.meta('showSuggestions')):
                raise ToolError('INVALID_ARGUMENT', 'The case changed while the suggestion was formed, so it was not kept.')
            with self.app.db:
                self.app.update_suggestion(r, found)
            return ToolDispatcher._ok('requestSuggestion', args, {'requestId': rid, 'suggestion': self.app.case_situation(r, 'owner')['suggestion']})

    def _openRequest(self, args):   # tool_result opens the case with the message as typed, after the run
        if self.request_id:
            raise ToolError('INVALID_ARGUMENT', 'Open new requests from the General thread; in a case, raise a concern or reply instead.', executed=False)
        _text_arg(args, 'text', 8000)
        return ToolDispatcher._ok('openRequest', args, {'opened': 'a case, when this turn is saved'}, 'openRequest', {'tool': 'openRequest'})

    def invoice_of(self, c, args):
        """The invoice of customer c that args name by exactly one of invoiceId and invoiceReference (prepareRequest and the delegation tools resolve it
        the same way): an invoiceId must be this customer's; a number must belong to one invoice of theirs, else NOT_FOUND or AMBIGUOUS. Lock held."""
        given = {k: args[k] for k in ('invoiceId', 'invoiceReference') if args.get(k) is not None}
        if len(given) != 1:
            raise ToolError('INVALID_ARGUMENT', 'Give exactly one of invoiceId and invoiceReference.', executed=False)
        if 'invoiceId' in given:
            invoice = self.ev.invoice(_text_arg(args, 'invoiceId', 80))
            if invoice is None or invoice['customerId'] != c['id']:
                raise ToolError('NOT_FOUND', 'No invoice with that invoiceId belongs to ' + c['name'] + '. Use an invoiceId returned by invoices for this customer.', executed=False)
        else:
            ref = ref_key(_text_arg(args, 'invoiceReference', 40))
            if len(self.ev.owners(ref)) > 1:
                raise ToolError('AMBIGUOUS', 'Invoice ' + ref + ' exists for more than one customer. Use the invoiceId of the right one (invoices lists them).', executed=False)
            mine = [i for i in self.ev.invoices_by_ref(ref) if i['customerId'] == c['id']]
            if not mine:
                others = [(self.ev.customer(o) or {}).get('name') or o for o in self.ev.owners(ref) if o != c['id']]   # say whose it is (Hoang, 9 Nov 2026)
                raise ToolError('NOT_FOUND', 'No invoice ' + ref + ' belongs to ' + c['name'] + '.' + (' Invoice ' + ref + ' is recorded for ' + ', '.join(others) +
                                ': ask Staff which customer they mean; do not use another invoice.' if others else ' Check the number, or use an invoiceId returned by invoices.'),
                                executed=False, extra={'hint': {'ask': 'customer', 'question': 'Invoice ' + ref + ' is recorded for ' + ', '.join(others) + ', not ' + c['name'] +
                                                                '. Which customer is the request for?', 'options': [*others, c['name']]}} if others else {})
            if len(mine) > 1:
                raise ToolError('AMBIGUOUS', c['name'] + ' has several invoices numbered ' + ref + '. Use the invoiceId of the right one (invoices lists them).', executed=False)
            invoice = mine[0]
        return invoice

    @staticmethod
    def days_or_date(args):
        """(days, requestedDueDate) from args: exactly one of them, days a whole number from 1 to MAX_EXTENSION_DAYS."""
        days, wanted = args.get('days'), args.get('requestedDueDate')
        if (days is None) == (wanted is None):
            raise ToolError('INVALID_ARGUMENT', 'Give exactly one of days and requestedDueDate.', executed=False)
        if days is not None and not (type(days) is int and 1 <= days <= MAX_EXTENSION_DAYS):
            raise ToolError('INVALID_ARGUMENT', 'days is a whole number from 1 to ' + str(MAX_EXTENSION_DAYS) + ', counted after the current due date.', executed=False)
        return days, wanted

    def _prepareRequest(self, args):
        """A payment-extension request prepared for a person to confirm: nothing is submitted and nothing approved. Code resolves the customer and
        the invoice (the invoice must be this customer's, open, with a due date on record), works out the new due date from days or checks the date
        given, refuses while a request is open on the invoice, and fixes all of it as an action (App.get_action) with the evidence version it rests
        on. Only a person confirming it over HTTP (App.confirm_action), which no tool reaches, opens the request, and only for exactly these values.
        A newer proposal for the invoice supersedes the older ones in the same transaction. The assistant's reason is a draft, shown as such. Lock held."""
        if self.role != 'staff':
            raise ToolError('FORBIDDEN', 'Staff prepare these requests; the owner decides them.', executed=False)
        c = self.customer(args)
        invoice = self.invoice_of(c, args)
        days, wanted = self.days_or_date(args)
        reason = args.get('reason')
        if reason is not None and (not isinstance(reason, str) or len(reason.strip()) > REASON_LIMIT):
            raise ToolError('INVALID_ARGUMENT', 'reason is text of at most ' + str(REASON_LIMIT) + ' characters.', executed=False)
        reason = reason.strip() or None if reason is not None else None
        problem = self.app.action_problem(self.ev, invoice)   # open, with a due date on record
        if problem:
            raise ToolError(problem[0], problem[1], executed=False, extra=problem[2])
        due = self.ev.current_due(invoice)
        if wanted is not None:
            try:
                requested = calendar_date(_text_arg(args, 'requestedDueDate', 20)).isoformat()
            except ValueError:
                raise ToolError('INVALID_ARGUMENT', 'requestedDueDate must be YYYY-MM-DD.', executed=False) from None
        else:
            requested = (calendar_date(due) + timedelta(days=days)).isoformat()
        problem = self.app.action_problem(self.ev, invoice, requested)   # the date, and no request open on the invoice
        if problem:
            raise ToolError(problem[0], problem[1], executed=False, extra=problem[2])
        days = (calendar_date(requested) - calendar_date(due)).days
        p = self.views().get('customers', {}).get(c['id'])
        if p is None:
            raise ToolError('MISSING_DATA', 'The workspace has no currency yet, so nothing is worked out. The owner sets it under Setup.', executed=False)
        shown = next(m for m in self.rows(c, 'all')[2] if m['invoiceId'] == invoice['id'])   # the amount and its mark as the invoices tool gives them
        action_id, made = uid('act'), datetime.now(timezone.utc)
        preview = dated({
            'fromRecords': {'customer': {'id': c['id'], 'name': c['name']},
                            'invoice': {'id': invoice['id'], 'reference': invoice['reference'], 'amount': shown['stillOwed'], 'amountText': shown['amountText'],
                                        'mark': shown['mark'], 'amountAsOf': shown['amountAsOf'], 'issuedOn': invoice.get('issueDate'), 'currentDueDate': due}},
            'completeness': self.completeness(c, p),
            'proposedChange': {'currentDueDate': due, 'requestedDueDate': requested, 'days': days},
            'draftedByAssistant': {'reason': reason},
            'requires': {'confirmation': 'A person signed in to Nucleon as staff must confirm this exact proposal before anything is submitted.',
                         'ownerDecision': 'The owner decides the request; confirming submits it for review and approves nothing.'},
            'effect': 'Opens a payment-extension request for the owner to decide.'})
        action = {'id': action_id, 'kind': 'open_request', 'status': 'proposed', 'invoiceId': invoice['id'], 'createdAt': made.isoformat(), 'version': ACTION_VERSION,
                  'preparedBy': {'role': self.role, 'actorId': self.by, 'actorKind': self.actor.get('kind', 'person'),
                                 'channel': 'service' if self.actor.get('channel') == 'service' else 'tool_surface' if self.pressed else 'desk'},
                  'preparedAt': made.isoformat(), 'expiresAt': (made + timedelta(hours=ACTION_TTL_HOURS)).isoformat(),
                  'params': {'customerId': c['id'], 'invoiceId': invoice['id'], 'invoiceReference': invoice['reference'], 'currentDueDate': due,
                             'requestedDueDate': requested, 'days': days, 'reasonDraft': reason},
                  'basis': {'evidenceVersion': self.ev.version_for(invoice['id']), 'currentDueDate': due, 'invoiceOpen': True},
                  'preview': preview, 'history': [{'at': made.isoformat(), 'status': 'proposed', 'role': self.role}]}
        with self.app.db:   # the older proposals for this invoice are settled in the same commit that makes this one confirmable
            replaced = self.app.supersede_actions('open_request', invoice['id'], self.role, action_id)
            self.app.add_action(action)
        return {'actionId': action_id, 'status': 'proposed', 'expiresAt': action['expiresAt'], 'preview': preview, 'supersededActionIds': replaced}

    def _actionStatus(self, args):
        """Where an action stands, as App.action_view gives it to this role: a read that writes nothing, not even the expiry. Lock held."""
        try:
            a = self.app.get_action(_text_arg(args, 'actionId', 80))
        except APIError:
            raise ToolError('NOT_FOUND', 'No such action. Use an actionId that prepareRequest returned.', executed=False) from None
        return self.app.action_view(self.actor, a)

    # ---- adaptive decision authority (docs/ADAPTIVE-DECISION-AUTHORITY.md): all three are off until the Owner turns them on, and none writes the policy

    @staticmethod
    def hinted(exc, hint):
        """The ToolError with a structured `hint` beside its code: {ask: kind | invoice | customer | amount | terms | dueDate, question: one short question for Staff, options?: [...]}.
        The error code and message are unchanged; the model asks Staff the question instead of guessing."""
        exc.extra = {**exc.extra, 'hint': hint}
        return exc

    @staticmethod
    def kind_hint(question='Is this a payment extension on an invoice, or a trial credit for a new customer?'):
        return {'ask': 'kind', 'question': question, 'options': ['trial_credit', 'extension']}

    def customer_hint(self, args):
        """Ask which customer: the findCustomers matches for what was given, if any (names with their codes)."""
        given = args.get('customerId')
        found = [c for c, _ in self.ev.find_customers(given)] if isinstance(given, str) and given.strip() and given != 'current' else []
        hint = {'ask': 'customer', 'question': 'Which customer is this for?'}
        if found:
            hint['options'] = [c['name'] + ' (' + c['displayCode'] + ')' for c in found[:5]]
        return hint

    def invoice_hint(self, c):
        """Ask which invoice: the customer's open invoice references."""
        refs = [i['reference'] for i in self.ev.invoices_for(c['id']) if is_open(i) and i.get('reference')][:8]
        hint = {'ask': 'invoice', 'question': 'Which of ' + c['name'] + "'s invoices is the extension for?"}
        if refs:
            hint['options'] = refs
        return hint

    @staticmethod
    def due_date_hint():
        return {'ask': 'dueDate', 'question': 'By how many days, or to what date, should the due date move?'}

    @staticmethod
    def amount_hint():
        return {'ask': 'amount', 'question': 'What is the order amount?'}

    @staticmethod
    def terms_hint():
        return {'ask': 'terms', 'question': 'How many days of payment terms does the customer want?'}

    # A number of days the assistant says the extension adds ("15 extra days", "extend by 15 days", "a 15-day extension"), read from its reasoning (8 Nov 2026).
    CURRENT_DUE_SAID = re.compile(r'\b(?:current(?:ly)?\s+due(?:\s+date)?|due\s+date\s+is\s+now)\s*(?:is|of|was|on|:)?\s*\(?\s*'
                                  r'((?:(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,?\s+)?\d{1,2}\s+[A-Z][a-z]{2,8},?\s+\d{4}|\d{4}-\d{2}-\d{2})', re.I)
    DAYS_SAID = re.compile(r'\b(\d{1,3})\s*(?:extra|more|additional|further)\s+days?\b|\bextend(?:ed|ing|s)?\s+(?:it\s+)?(?:by|for)\s+(\d{1,3})\s+days?\b|'
                           r'\b(\d{1,3})[\s-]*days?\s+extension\b|\brequest(?:s|ed|ing)?\s+(?:an?\s+)?(\d{1,3})[\s-]*days?\b', re.I)

    # A date the assistant writes ("31 December 2026", "Thu 31 Dec", "December 31, 2026", "2026-12-31"), read from its reasoning (12 Nov 2026).
    DATE_SAID = re.compile(r'\b(\d{4}-\d{2}-\d{2})\b|\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?,?(?:\s+(\d{4}))?\b|'
                           r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b(?:,?\s+(\d{4}))?', re.I)
    MONTHS = ('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec')

    def dates_said(self, said, as_of):
        """The calendar dates written in the assistant's words. A date without a year is read as its next occurrence on or after the as-of date."""
        found = set()
        for m in self.DATE_SAID.finditer(said):
            iso, d1, mon1, y1, mon2, d2, y2 = m.groups()
            try:
                if iso:
                    found.add(calendar_date(iso))
                    continue
                day, month, year = int(d1 or d2), self.MONTHS.index((mon1 or mon2)[:3].lower()) + 1, y1 or y2
                when = datetime(int(year) if year else as_of.year, month, day).date()
                found.add(when if year or when >= as_of else datetime(as_of.year + 1, month, day).date())
            except ValueError:
                pass
        return found

    def check_extension_dates(self, invoice, due, days, requested, said):
        """Code, not the model, works out extension dates (Hoang's NTK test, 8 Nov 2026: two 15-day requests became 46 and 66 days). In days, the date counts after the
        CURRENT due date: when that is already past (an overdue invoice), nothing is sent and the assistant is told both readings, worked out, to ask Staff which they mean.
        Given as a date, the days the assistant's own words say the extension adds must match the date: after the current due date or from today. Lock held."""
        as_of, cur, asked = self.ev.as_of, calendar_date(due), calendar_date(requested)
        if days is not None and asked <= as_of:
            from_today = as_of + timedelta(days=days)
            late = (as_of - cur).days
            raise ToolError('ASK_STAFF_DATE', 'Nothing was sent. Invoice ' + invoice['reference'] + ' is currently due ' + display_date(due) + ', ' + days_text(late) + ' overdue on ' +
                            display_date(as_of.isoformat()) + '. ' + days_text(days) + ' after the current due date is ' + display_date(requested) + ', which is already past. '
                            'Do not choose a date yourself: ask Staff whether they mean ' + days_text(days) + ' from today (' + display_date(from_today.isoformat()) + ', ' +
                            days_text((from_today - cur).days) + ' after the current due date) or another date, then call again with requestedDueDate set to the date they confirm.',
                            executed=False, extra={'hint': {'ask': 'dueDate', 'question': 'Invoice ' + invoice['reference'] + ' was due ' + display_date(due) + ' and is already overdue. Do you mean ' +
                                                           days_text(days) + ' from today (' + display_date(from_today.isoformat()) + '), or another date?'},
                                                  'currentDueDate': due, 'asOfDate': as_of.isoformat(), 'fromTodayDate': from_today.isoformat(), 'fromTodayAddsDays': (from_today - cur).days})
        if days is not None and said:   # days counted from a due date that is no longer the current one (9 Nov 2026: "9 days after current due date (Sun 15 Nov)" when it was 30 Nov)
            stale = sorted({d for d in (written_date(m.group(1)) for m in self.CURRENT_DUE_SAID.finditer(said)) if d and d != cur})
            if stale:
                raise ToolError('DUE_DATE_CHANGED', 'Nothing was sent. Your reasoning says the current due date is ' + display_date(stale[0].isoformat()) + ', but invoice ' + invoice['reference'] +
                                ' is currently due ' + display_date(due) + ' (an earlier decision may have moved it). ' + days_text(days) + ' after that would be ' + display_date(requested) +
                                '. Do not work out dates yourself: tell Staff the current due date and ask what they want, then call again with the days or the date they confirm.',
                                executed=False, extra={'currentDueDate': due, 'dateInReasoning': stale[0].isoformat(), 'requestedDueDate': requested})
        if said:   # the owners' session, 12 Nov 2026: Staff asked for 31 December, the model gave days=78 (1 December) while its reasoning said 31 December
            original = invoice.get('originalDueDate')
            later = sorted(d for d in self.dates_said(said, as_of) if d > as_of and d != cur and not (original and d == calendar_date(original)))
            if later and asked not in later:
                named = ' and '.join(display_date(d.isoformat()) for d in later[:3])
                how = days_text(days) + ' after the current due date (' + display_date(due) + ') is ' + display_date(requested) if days is not None else 'requestedDueDate is ' + display_date(requested)
                raise ToolError('DATE_MISMATCH', 'Nothing was sent. Your reasoning names ' + named + ', but ' + how + '. Do not work out days yourself: when Staff give a date, '
                                'call again with requestedDueDate set to exactly that date (YYYY-MM-DD) and without days. If ' + display_date(requested) + ' is what Staff asked for, '
                                'say that date in the reasoning.', executed=False,
                                extra={'currentDueDate': due, 'requestedDueDate': requested, 'datesInReasoning': [d.isoformat() for d in later]})
        if days is None and said:
            nums = {int(n) for m in self.DAYS_SAID.finditer(said) for n in m.groups() if n}
            added, ahead = (asked - cur).days, (asked - as_of).days
            if nums and not nums & {added, ahead}:
                n = min(nums)
                right = cur + timedelta(days=n)
                raise ToolError('DAYS_MISMATCH', 'Nothing was sent. Your reasoning says ' + days_text(n) + ', but ' + display_date(requested) + ' is ' + days_text(added) +
                                ' after the current due date (' + display_date(due) + ') and ' + days_text(ahead) + ' from today (' + display_date(as_of.isoformat()) + '). '
                                'Do not work out dates yourself: give days instead (code works out the date' + ('' if right > as_of else '; if that date is already past you will be asked to check with Staff') +
                                '), or correct requestedDueDate and the reasoning so they agree.', executed=False,
                                extra={'currentDueDate': due, 'requestedDueDate': requested, 'addsDays': added, 'daysFromToday': ahead, 'daysInReasoning': sorted(nums)})

    def dg_args(self, args, resolving, anyone=False):
        """The request a delegation tool names, checked against the records: (kind, customer, invoice or None, params, recommendation or None, context, policyVersion).
        The customer and invoice are resolved by the code prepareRequest uses (customer, invoice_of, days_or_date, action_problem). Lock held."""
        if self.role != 'staff' and not anyone:   # anyone: the S3 read tools (whatIsNeeded, comparableCases) are read by the Owner's assistant too
            raise ToolError('FORBIDDEN', 'Staff ask the assistant to resolve these requests; the owner reads their status.', executed=False)
        kind = args.get('kind')
        if kind not in delegation.KINDS:
            raise self.hinted(ToolError('INVALID_ARGUMENT', "kind is 'extension' or 'trial_credit'.", executed=False), self.kind_hint())
        seen = args.get('policyVersion')
        if seen is not None and not (type(seen) is int and seen >= 0):
            raise ToolError('INVALID_ARGUMENT', 'policyVersion is the policy version you last saw, a whole number.', executed=False)
        rec, reasoning, context = args.get('recommendation'), args.get('reasoning'), args.get('context')
        if resolving:
            if rec not in delegation.RECOMMENDATIONS:
                raise ToolError('INVALID_ARGUMENT', "recommendation is 'approve', 'decline' or 'escalate'.", executed=False)
            if not isinstance(reasoning, str) or not 1 <= len(reasoning.strip()) <= 2000:
                raise ToolError('INVALID_ARGUMENT', 'reasoning is your explanation, 1 to 2000 characters.', executed=False)
            if context is not None and (not isinstance(context, str) or len(context.strip()) > CASE_TEXT):
                raise ToolError('INVALID_ARGUMENT', 'context is text of at most ' + str(CASE_TEXT) + ' characters. It is kept as reported in chat; it never counts as verification.', executed=False)
        elif rec is not None and rec not in delegation.RECOMMENDATIONS:
            raise ToolError('INVALID_ARGUMENT', "recommendation is 'approve', 'decline' or 'escalate'.", executed=False)
        recommendation = {'recommendation': rec or 'approve', 'reasoning': reasoning.strip() if isinstance(reasoning, str) else None}
        try:
            c = self.customer(args)
        except ToolError as exc:
            raise self.hinted(exc, self.customer_hint(args)) from None
        if kind == 'extension':
            if args.get('orderAmount') is not None or args.get('termsDays') is not None:
                raise self.hinted(ToolError('INVALID_ARGUMENT', 'orderAmount and termsDays are for trial_credit.', executed=False), self.kind_hint('This looks like a trial credit (it has an order amount or terms), not an extension. Which is it?'))
            try:
                invoice = self.invoice_of(c, args)
            except ToolError as exc:
                raise self.hinted(exc, exc.extra.get('hint') or self.invoice_hint(c)) from None   # an invoice of another customer asks which customer, not which invoice
            try:
                days, wanted = self.days_or_date(args)
            except ToolError as exc:
                raise self.hinted(exc, self.due_date_hint()) from None
            problem = self.app.action_problem(self.ev, invoice)   # open, with a due date on record
            if problem:
                raise ToolError(problem[0], problem[1], executed=False, extra=problem[2])
            due = self.ev.current_due(invoice)
            try:
                requested = calendar_date(_text_arg(args, 'requestedDueDate', 20)).isoformat() if wanted is not None else (calendar_date(due) + timedelta(days=days)).isoformat()
            except ValueError:
                raise self.hinted(ToolError('INVALID_ARGUMENT', 'requestedDueDate must be YYYY-MM-DD.', executed=False), self.due_date_hint()) from None
            self.check_extension_dates(invoice, due, days, requested, ' '.join(x for x in (reasoning, context) if isinstance(x, str)))
            return kind, c, invoice, {'customerId': c['id'], 'invoiceId': invoice['id'], 'invoiceReference': invoice['reference'], 'currentDueDate': due,
                                      'requestedDueDate': requested, 'days': days}, recommendation, context and context.strip(), seen
        if any(args.get(k) is not None for k in ('invoiceId', 'invoiceReference', 'days', 'requestedDueDate')):
            raise self.hinted(ToolError('INVALID_ARGUMENT', 'invoiceId, invoiceReference, days and requestedDueDate are for extension.', executed=False),
                              self.kind_hint('This looks like an extension (it names an invoice or a due date), not a trial credit. Which is it?'))
        terms = args.get('termsDays')
        missing = [x for x, v in (('orderAmount (e.g. "800.00")', args.get('orderAmount')), ('termsDays (e.g. 14)', terms)) if v is None]
        if missing:
            hint = self.amount_hint() if args.get('orderAmount') is None else self.terms_hint()
            if len(missing) == 2:
                hint['alsoMissing'] = ['terms']
            raise self.hinted(ToolError('INVALID_ARGUMENT', 'trial_credit needs orderAmount (e.g. "800.00") and termsDays (e.g. 14). Missing: ' + ' and '.join(missing) + '. Ask the person if they did not say.', executed=False), hint)
        if not (type(terms) is int and 1 <= terms <= 365):
            raise self.hinted(ToolError('INVALID_ARGUMENT', 'termsDays is a whole number of days from 1 to 365, for example 14 (not text).', executed=False), self.terms_hint())
        try:
            order = parse_money(args.get('orderAmount'), settings_of(self.app.fixture()), 'orderAmount')
        except RecordsError as exc:
            raise self.hinted(ToolError('INVALID_ARGUMENT', 'orderAmount: ' + exc.message + ' Give it as a decimal string in the workspace currency.', executed=False), self.amount_hint()) from None
        if minor(order) <= 0:
            raise self.hinted(ToolError('INVALID_ARGUMENT', 'orderAmount must be more than zero.', executed=False), self.amount_hint())
        return kind, c, None, {'customerId': c['id'], 'orderAmount': minor(order), 'termsDays': terms}, recommendation, context and context.strip(), seen

    def _assessDecision(self, args):
        """What would happen to this request now under the Owner's current delegation policy, with its key facts, warnings and the three dimensions. Stores
        nothing: no case, no action, no request. The recommendation, if none is given, is assumed to be approve (and said). Lock held."""
        kind, c, invoice, params, recommendation, _, seen = self.dg_args(args, False)
        handled = self.app.delegation_handled(self.actor, kind, invoice['id'] if invoice else c['id'], params, invoice)   # already resolved: its stored status, not a new preview
        if handled:
            self.about = c
            return self.with_model_view({**handled, 'alreadyHandled': True, 'note': 'This request is already handled (case ' + handled['caseId'] + ', ' + handled['status'] + '). '
                                         'Do not assess or resolve it again; report this statusText.'})
        out = self.app.delegation_assess(self.actor, kind, c, invoice, params, recommendation, seen)
        if args.get('recommendation') is None:
            out['assumedRecommendation'] = 'approve'
        return self.with_model_view(out)

    def _resolveDecision(self, args):
        """The assistant's recommendation and reasoning go in; the backend applies the handling the policy allows (App.delegation_resolve): approve within the
        delegation, ask Staff for evidence, or send it to the Owner. The model never sets a status. A duplicate returns the stored case (replayed: true). Lock held."""
        kind, c, invoice, params, recommendation, context, seen = self.dg_args(args, True)
        if self.actor['role'] == 'staff' and self.app.staff_practice().get('on'):   # practice: the preview, said so, and nothing else (4 Nov 2026)
            out = self.app.delegation_assess(self.actor, kind, c, invoice, params, recommendation, seen)
            out['practice'] = True
            out['statusText'] = 'Practice mode (nothing stored, nothing sent to the Owner): ' + out['statusText']
            return self.with_model_view(out)
        subject = invoice['id'] if invoice else c['id']
        existing = self.app.delegation_existing(self.actor, kind, subject, params, invoice, recommendation, context)
        if existing:
            return self.with_model_view(existing)
        self.app.one_at_a_time(self.actor, c)   # one new case per Staff message from the assistant
        if kind == 'extension':
            problem = self.app.action_problem(self.ev, invoice, params['requestedDueDate'])   # the date, and no other request open on the invoice
            if problem:
                raise ToolError(problem[0], problem[1], executed=False, extra=problem[2])
        return self.with_model_view(self.app.delegation_resolve(self.actor, 'tool_surface' if self.pressed else 'desk', kind, c, invoice, params, recommendation, context, seen))

    # ---- S3 read tools (docs/ADAPTIVE-DECISION-AUTHORITY.md, "As built (S3)"): they store nothing and take no decision. Off by default like the other delegation tools.

    def dg_evaluation(self, args):
        """(kind, customer, evaluation) of the request the arguments name, evaluated on the records and the CURRENT policy exactly as assessDecision does, but
        without the "already handled" shortcut and for either role. Stores nothing. Lock held."""
        kind, c, invoice, params, recommendation, _, seen = self.dg_args(args, False, anyone=True)
        ev, doc = self.app.evidence(), self.app.fixture()
        request, ledger = self.app.dg_request(kind, ev, doc, c, invoice, params)
        self.about = c
        return kind, c, self.app.dg_evaluate(kind, request, ledger, ev, doc, recommendation, seen)

    def _whatIsNeeded(self, args):
        """What evidence a request of this kind would need now, and which of it Staff can provide: the evidence section of the evaluation (delegation.assess_evidence, the
        same path as assessDecision) and a compact forModel. Nothing is stored or decided."""
        kind, c, e = self.dg_evaluation(args)
        return {'stored': False, 'kind': kind, 'customer': {'id': c['id'], 'name': c['name']}, 'policyVersion': e['authority']['version'], 'evidence': dated(e['evidence']),
                'note': 'Evidence on file now; nothing was stored or decided. What Staff confirm on the Nucleon page counts only after they submit it.',
                'forModel': agent_views.needs_for_model(kind, c['name'], e['evidence'])}

    def _comparableCases(self, args):
        """The reviewed cases the evaluation would compare this request with (fictional examples and live reviewed cases, never the held-out evaluation set), each labelled an
        analogy unless it is this customer's own earlier case. The Owner's reasons are the Owner's alone: Staff do not get them."""
        kind, c, e = self.dg_evaluation(args)
        owner = self.role == 'owner'
        comps = e['comparables'] if owner else [{k: v for k, v in x.items() if k != 'ownerReason'} for x in e['comparables']]
        return {'stored': False, 'kind': kind, 'customer': {'id': c['id'], 'name': c['name']}, 'policyVersion': e['authority']['version'], 'comparables': comps,
                'declinedMajority': e['reliability']['comparablesDeclinedMajority'],
                'note': "Analogies, not this customer's history (unless sameCustomer). Nothing was stored or decided.",
                'forModel': agent_views.comparables_for_model(kind, c['name'], comps, e['reliability']['comparablesDeclinedMajority'], owner)}

    def _customerStatus(self, args):
        """Where a customer's decision cases stand, live cases only: the latest status, the trial credit line in force, the evidence requests waiting for Staff and the last
        outcome observation. Either role; the Owner's feedback and reasons are not part of it."""
        try:
            c = self.customer(args)
        except ToolError as exc:
            raise self.hinted(exc, self.customer_hint(args)) from None
        self.about = c
        mine = [x for x in reversed(self.app.dg_cases("dataset='live'")) if x.get('customerId') == c['id']]
        words = lambda x: delegation.status_text({**x, 'keyFacts': x['evaluation']['keyFacts'], 'authority': x['authority'], 'why': x['evaluation'].get('why')})   # noqa: E731
        rows = [{'caseId': x['id'], 'kind': x['kind'], 'status': x['status'], 'handling': x['handling'], 'createdAt': x['createdAt'], 'statusText': words(x)} for x in mine[:5]]
        latest = next((r for r in rows if r['status'] in LIVE_CASE), rows[0]) if rows else None
        lines = self.app.dg_trial_lines(c['id'], self.ev)
        line = None
        if lines:
            x = lines[-1]
            kf = x['evaluation']['keyFacts']
            line = {'caseId': x['id'], 'text': 'Trial credit in force: ' + str((kf.get('exposure') or {}).get('text') or '') + ' exposure on ' + str(kf.get('termsDays')) + '-day terms'}
        waiting = [{'caseId': x['id'], 'kind': x['kind'], 'actionId': x.get('actionId'), 'evidenceLink': x.get('actionId') and '#/actions/' + x['actionId'], 'needs': x.get('needs') or []}
                   for x in mine if x['status'] == 'gathering_evidence']
        seen = [(x['outcomeObserved'].get('observedAt') or '', x) for x in mine if x.get('outcomeObserved')]
        last = max(seen, key=lambda t: t[0])[1] if seen else None
        outcome = last and {'caseId': last['id'], 'outcome': last['outcomeObserved'].get('outcome'), 'asOf': last['outcomeObserved'].get('asOf')}
        return dated({'customer': {'id': c['id'], 'name': c['name']}, 'dataset': 'live', 'latest': latest, 'cases': rows, 'trialInForce': line, 'waitingForStaff': waiting, 'lastOutcome': outcome,
                      'forModel': agent_views.customer_status_for_model(c['name'], latest, rows, line and line['text'], waiting, outcome)})

    def _policyBacktest(self, args):
        """Owner only. What the CURRENT policy with the given partial changes would have decided on the reviewed cases (delegation.track_record/backtest: the bounds, as the
        track-record gate counts them), next to what the current policy does: the fictional evaluation set (a simulation) and the live Owner-reviewed cases, apart. Reads and
        stores nothing; the change is not saved, and only the Owner, as a person, saves a policy on the Control panel."""
        if self.role != 'owner':
            raise ToolError('FORBIDDEN', 'Only the owner asks what a policy change would have done.', executed=False)
        changes = args.get('changes', {})
        if not isinstance(changes, dict):
            raise ToolError('INVALID_ARGUMENT', "changes is an object of the policy settings to change, for example {\"newCustomers\": {\"maxExposure\": \"1500.00\"}}.", executed=False)
        current = self.app.policy_current()
        base = {k: current[k] for k in delegation.POLICY_KEYS}
        try:
            candidate = delegation.validate_policy(agent_views.deep_merge(base, changes), settings_of(self.app.fixture()))
        except RecordsError as exc:
            raise ToolError('INVALID_ARGUMENT', 'changes: ' + exc.message, executed=False) from None
        paths = agent_views.changed_paths(base, changes)
        memory = self.app.dg_memory(self.app.evidence(), self.app.fixture())
        sections = {kind: {'current': agent_views.backtest_section(base, kind, delegation.track_record(base, kind, memory)),
                           'withChanges': agent_views.backtest_section(candidate, kind, delegation.track_record(candidate, kind, memory))} for kind in delegation.KINDS}
        label = ('The fictional evaluation set is a SIMULATION against a fictional Owner, not real credit decisions; live counts are the Owner\'s real reviews. '
                 'The back-test counts the policy\'s bounds; paused, advisory mode and category switches are judged separately.')
        return {'stored': False, 'saved': False, 'policyVersion': current['version'], 'changed': paths, 'categories': sections, 'label': label,
                'note': 'Nothing was saved. Only the Owner, as a person, saves a policy version on the Control panel.',
                'forModel': agent_views.backtest_for_model(current['version'], paths, sections, label)}

    def _doctor(self, args):
        """Owner only. The Doctor's answer (GET api/delegation/doctor) for the Owner's assistant: `question` (one of doctor.QUESTIONS, or none for the six headlines)
        and `days` ("30", "90" or "all"). forModel holds the lines code wrote, nothing else. Reads only."""
        if self.role != 'owner':
            raise ToolError('FORBIDDEN', 'Only the owner reads the Doctor.', executed=False)
        query = {}
        for key in ('question', 'days'):
            value = args.get(key)
            if key == 'days' and type(value) is int:   # a number is taken as its text
                value = str(value)
            if value is not None:
                if not isinstance(value, str):
                    raise ToolError('INVALID_ARGUMENT', key + ' is text: ' + ('one of ' + ', '.join(q for q, _ in doctor.QUESTIONS) if key == 'question' else '"30", "90" or "all"') + '.', executed=False)
                query[key] = [value]
        try:
            out = self.app.doctor({'role': 'owner'}, query)
        except APIError as exc:
            raise ToolError('INVALID_ARGUMENT' if exc.status == 400 else exc.code, exc.message, executed=False) from None
        view = out if 'facts' in out else {'question': None, 'headline': 'The six questions the Doctor answers, each with its headline. Call doctor again with one of them for the details.',
                                           'facts': [q['label'] + ' ' + q['headline'] for q in out['questions']]}
        rules = None
        doc = self.app.fixture()
        if doc is not None:
            policy = self.app.policy_current()
            summary = delegation.quick_setup_summary(policy, self.app.dg_template(doc), {c['id']: c['name'] for c in self.ev.customers})
            rules = {'theAgentDecides': summary['decides'], 'alwaysComesToTheOwner': summary['comesToYou']}
        return {**out, 'stored': False, 'forModel': agent_views.doctor_for_model(view, rules)}

    def _modelStatus(self, args):
        """Owner only. The team's classifier as the Model page shows it: the model in force, what it was fitted on, its coefficients, how often it agreed with the Owner,
        whether promotion is on and its bar is met, the saved versions and the training table's size. Read-only; nothing here decides."""
        if self.role != 'owner':
            raise ToolError('FORBIDDEN', 'Only the owner reads the model status.', executed=False)
        r = self.app.delegation_research({'role': 'owner'})
        m, a, p = r['model'], r['agreement'], r['promotion']
        text = ('No model is in force. ' if not m else 'Model in force: ' + m['name'] + ' v' + str(m['version']) + ', fitted on ' + str((m.get('trainedOn') or {}).get('rows', '?')) + ' rows with ' +
                str((m.get('trainedOn') or {}).get('positives', '?')) + ' declines, features ' + ', '.join(m.get('features') or []) + '. ')
        text += ('It agreed with the Owner on ' + str(a['agreed']) + ' of ' + str(a['n']) + ' scored live cases. ' if a['n'] else 'No scored live case has the Owner\'s verdict yet. ') + p['reason']
        text += ' The training table has ' + str(r['training']['rows']) + ' rows (' + str(r['training']['positives']) + ' declines); ' + str(r['live']) + ' are live cases.'
        return {'text': text, 'model': m, 'agreement': a, 'agreementByVersion': r.get('agreementByVersion', []), 'promotion': p, 'settings': r['settings'], 'provider': r['provider'],
                'versions': r['versions'][:5], 'training': r['training'], 'live': r['live'], 'decided': r['decided'], 'page': '#/research'}

    def _impactSummary(self, args):
        """Owner only. The impact endpoint's figures (live cases only, each with numerator, denominator, source), for an optional window from/to (YYYY-MM-DD)."""
        if self.role != 'owner':
            raise ToolError('FORBIDDEN', 'Only the owner reads the impact summary.', executed=False)
        query = {}
        for key in ('from', 'to'):
            if args.get(key) is not None:
                if not isinstance(args[key], str):
                    raise ToolError('INVALID_ARGUMENT', key + ' is a date such as 2026-10-24.', executed=False)
                query[key] = [args[key]]
        try:
            report = self.app.impact_report(query)
        except APIError as exc:
            raise ToolError('INVALID_ARGUMENT', exc.message, executed=False) from None
        return {**report, 'stored': False, 'forModel': agent_views.impact_for_model(report)}

    @staticmethod
    def with_model_view(out):
        """The full result (the card reads all of it, unchanged) with `forModel` beside it: the compact status, handling, statusText, why, nextStep and at most 8 key facts the
        model reads (delegation.for_model; at most FOR_MODEL_LIMIT characters)."""
        return {**out, 'forModel': delegation.for_model(out)}

    def _decisionStatus(self, args):
        """The authoritative status of a decision case, read from the backend, by exactly one selector: caseId, the evidence actionId, the requestId it opened, or
        customerId (with an optional kind): that customer's most recent live case, else their most recent case, with a short list of their recent cases. Whatever
        the assistant said earlier is not the status. Lock held."""
        given = {k: args[k] for k in ('caseId', 'actionId', 'requestId', 'customerId') if args.get(k) is not None}
        if len(given) != 1 or args.get('kind') is not None and 'customerId' not in given:
            raise ToolError('INVALID_ARGUMENT', 'Give exactly one of caseId, actionId, requestId and customerId (kind only goes with customerId).', executed=False)
        key, value = next(iter(given.items()))
        recent = None
        if key == 'customerId':
            try:
                c = self.customer(args)
            except ToolError as exc:
                raise self.hinted(exc, self.customer_hint(args)) from None
            kind = args.get('kind')
            if kind is not None and kind not in delegation.KINDS:
                raise ToolError('INVALID_ARGUMENT', "kind is 'extension' or 'trial_credit'.", executed=False)
            mine = [x for x in reversed(self.app.dg_cases("dataset='live'")) if x.get('customerId') == c['id'] and (kind is None or x['kind'] == kind)]
            found = [next((x for x in mine if x['status'] in LIVE_CASE), mine[0])] if mine else []
            recent = [{'caseId': x['id'], 'kind': x['kind'], 'status': x['status'], 'createdAt': x['createdAt'],
                       'statusText': delegation.status_text({**x, 'keyFacts': x['evaluation']['keyFacts'], 'authority': x['authority'], 'why': x['evaluation'].get('why')})} for x in mine[:5]]
            if not found:
                raise ToolError('NOT_FOUND', 'There is no decision case for ' + c['name'] + ' yet.', executed=False)
        else:
            value = _text_arg(args, key, 80)
            if key == 'caseId':
                found = self.app.dg_cases("id=? AND dataset='live'", (value,))
            elif key == 'actionId':
                try:
                    a = self.app.get_action(value)
                except APIError:
                    a = None
                found = self.app.dg_cases("id=? AND dataset='live'", (a['caseId'],)) if a and a['kind'] == 'evidence' else []
            else:
                found = [x for x in self.app.dg_cases("dataset='live'") if x.get('requestId') == value]
        if not found:
            raise ToolError('NOT_FOUND', 'No decision case matches. Use a caseId, actionId or requestId that resolveDecision returned, or a customerId.', executed=False)
        case = found[0]
        self.about = self.ev.customer(case['customerId'])
        out = self.app.case_view(case, self.role)
        if recent is not None:
            out['recentCases'] = dated(recent)
        if case.get('requestId'):
            r = self.app.get(case['requestId'])
            out['request'] = {'id': r['id'], 'status': r['status'], 'decision': decision_view(r.get('decision'), self.role)}
        return self.with_model_view(out)

    def _interpretStatement(self, args):   # a model call, so never under the lock; a failure fails the run (AdapterError)
        _text_arg(args, 'text', 8000)
        self.model_calls += 1
        result = self.adapter.respond('interpret_statement', interpret_messages(self.text, self.ev.customers, self.today), schema=INTERPRET_SCHEMA,
                                      timeout=self.timeout)
        if result.kind != 'structured_output':
            raise AdapterError('invalid_output', 'interpret_statement reply was not structured JSON')
        reading = validate_interpretation(result.value, self.text, self.today)
        return ToolDispatcher._ok('interpretStatement', args, {'understood': len(reading['lines'])}, 'interpretStatement',
                                  {'tool': 'interpretStatement', 'reading': reading})

    # ------------------------------------------------------------ import proposals (agent-assisted import)

    def import_proposal(self, proposal_id):
        """A stored import proposal by its id. Lock held."""
        found = self.app.meta(IMPORT_PROPOSALS + proposal_id)
        if not found:
            raise ToolError('NOT_FOUND', 'No import proposal has that proposalId.', executed=False)
        return found

    def applied_twin(self, sha, pid):
        """The stored proposal, other than pid, that was applied from a file with this hash; else None. Lock held."""
        return self.app.applied_twin(sha, pid)

    def import_file(self, args):
        """The file to propose from: on the tool surface an attachment (fileBase64: .xlsx or CSV, at most MAX_ATTACHMENT bytes) or
        CSV text the application passes, else the rows pasted in the person's message. Without one only the message is read: a
        file is never what the model wrote."""
        if not self.pressed:
            args = {}
        if args.get('fileBase64') is not None:
            text, large = args['fileBase64'], ToolError('INVALID_FILE', 'The file is too large (limit 2.5 MB).', executed=False)
            if isinstance(text, str) and len(text) > MAX_ATTACHMENT * 4 // 3 + 4:
                raise large
            try:
                size = len(base64.b64decode(text, validate=True))
            except (binascii.Error, ValueError, TypeError):
                raise ToolError('INVALID_FILE', 'The attached file could not be read.', executed=False) from None
            if size > MAX_ATTACHMENT:
                raise large
            return {'fileBase64': text}
        if args.get('csvText') is not None:
            return {'csvText': args['csvText']}
        if sum(1 for line in self.text.splitlines() if line.strip()) < 2:
            raise ToolError('MISSING_FILE', 'Attach the spreadsheet, or paste its rows in the message, then ask again.', executed=False)
        return {'csvText': self.text}

    def classify_columns(self, header, samples, fields):
        """The model's reading of the columns no heading names, from the headings and three sample rows only. A model call: never
        under the lock. importer.propose checks each answer against the whole column."""
        self.model_calls += 1
        result = self.adapter.respond('classify_columns', classify_messages(header, samples, fields), schema=CLASSIFY_SCHEMA, timeout=self.timeout)
        if result.kind != 'structured_output':
            raise AdapterError('invalid_output', 'classify_columns reply was not structured JSON')
        return result.value

    @staticmethod
    def draft_import(file, hints, classify, settings, today):
        """(sheets, the sheet read, importer.propose's proposal) for a stored file. classify may ask the model: no lock needed."""
        try:
            sheets = importer.sheets_of(file)
            sheet = importer.pick_sheet(sheets, hints.get('sheet'))
            return sheets, sheet, importer.propose(sheets[sheet], hints, classify, settings, today, {k: v for k, v in sheets.items() if k != sheet})
        except RecordsError as exc:
            raise ToolError(exc.code, exc.message, executed=False) from None

    def keep_import(self, base, file, name, hints, sheets, sheet, p):
        """A drafted proposal previewed against the records as they are now (importer.dry_run and review) and kept: a new proposal,
        or the next version of base (refused when base changed meanwhile). Only the most recent KEPT_PROPOSALS are kept. Returns
        the stored proposal: view (what the model and the card see), card (also the flagged rows and the customers by name), the
        batches to import and what their previews must still be. Lock held."""
        if base and self.import_proposal(base['id'])['version'] != base['version']:
            raise ToolError('STALE_VERSION', 'The proposal changed meanwhile; check it again.', executed=False)
        doc = self.app.fixture()
        settings = settings_of(doc)
        batches = importer.derived(p['entries'], hints.get('customers') or {})
        previews = importer.dry_run(doc, batches, settings, self.app.today(doc), hints.get('sourceLabel') or IMPORT_SOURCE)
        checked = importer.review(p, batches, previews)
        pid, at, unknown = base['id'] if base else uid('proposal'), now(), checked['unknown']
        workspace = {'currency': settings['currency'], 'scale': settings['scale']}
        references, references_text = importer.reference_summary(p['entries']['payments'], batches, previews)
        sha = hashlib.sha256(base64.b64decode(file['fileBase64']) if 'fileBase64' in file else file['csvText'].encode()).hexdigest()
        twin = self.applied_twin(sha, pid)
        references_text = ALREADY_MATCHED if twin and references.get('payments') else references_text
        openings = p['entries'].get('openings') or []
        opening_text = openings and (str(len(openings)) + ' opening balance' + ('s' if len(openings) > 1 else '') + ' as at ' + display_date(openings[0]['asOf']) +
                                     ", the day before the ledger's first entry (the file states no date)")
        counts = {**p['counts'], 'newCustomers': sum(1 for c in unknown.values() if c == 'new'), 'flagged': len({f['row'] for f in checked['flaggedRows']})}
        view = {'proposalId': pid, 'version': base['version'] + 1 if base else 1, 'fileName': name, 'sheets': importer.sheet_scores(sheets),
                'sheet': sheet, **{k: p[k] for k in ('shape', 'headerRow', 'columns', 'samples', 'mapping', 'naming', 'dueDates', 'dateOrder')},
                'notes': p['notes'] + (['The file does not say its currency; amounts are taken as ' + workspace['currency'] + '.'] if p['unit']['detected'] is None and not p['unit'].get('doubtful') else []),
                'unit': p['unit'], 'workspace': workspace, 'references': references, 'referencesText': references_text, 'openingsText': opening_text or None, 'unitProblem': unit_problem(p['unit'], workspace),
                'duplicate': twin and duplicate_message(twin, settings['timezone']), 'counts': counts, 'preview': checked['preview'],
                'flags': [{'row': f['row'], 'reason': f['reason']} for f in checked['flaggedRows'][:20]], 'needs': checked['needs'], 'ready': checked['ready']}
        names = {name_key(x['customer']): x['customer'] for x in p['entries']['invoices'] + p['entries']['payments']}
        stored = {'id': pid, 'version': view['version'], 'status': 'duplicate' if twin else 'proposed', 'fileName': name, 'file': file, 'hints': hints,
                  'sha256': sha, 'aliases': p['aliases'], 'unitRules': UNIT_RULES,
                  'createdBy': (base or {}).get('createdBy', self.by), 'createdActorName': (base or {}).get('createdActorName', self.trail['actorName']), 'createdActorRole': (base or {}).get('createdActorRole', self.trail['actorRole']),
                  'createdAt': (base or {}).get('createdAt', at), 'updatedBy': self.by, **self.trail, 'updatedAt': at,
                  'view': view, 'card': {'flaggedRows': checked['flaggedRows'][:200], 'customers': [
                      {'key': k, 'name': n, 'known': k not in unknown, 'choice': unknown.get(k)} for k, n in names.items()]},
                  'batches': [batches[i] for i in checked['writes']], 'expected': checked['expected']}
        with self.app.db:
            self.app.set_meta(IMPORT_PROPOSALS + pid, stored)
            if not base:   # a new proposal supersedes the others' files; each keeps its summary and batches
                self.app.db.execute("UPDATE meta SET data = json_set(data, '$.file', json('null')) WHERE key LIKE ?1 AND key != ?2 "
                                    "AND json_extract(data, '$.file') IS NOT NULL", (IMPORT_PROPOSALS + '%', IMPORT_PROPOSALS + pid))
            self.app.db.execute("DELETE FROM meta WHERE key LIKE ?1 AND key NOT IN (SELECT key FROM meta WHERE key LIKE ?1 ORDER BY "
                                "json_extract(data, '$.createdAt') DESC LIMIT ?2)", (IMPORT_PROPOSALS + '%', KEPT_PROPOSALS))
        return stored

    def _proposeImport(self, args):
        """A proposal for importing a file: an attachment (fileBase64) or CSV text the application passes, else the rows pasted in
        the person's message; or, with proposalId, the next version of that proposal with the person's corrections (hints). Which
        sheet, what the file lists, the column of each field and who chose it (its heading, the model's reading checked against the
        data, or the person), the customer naming, the due-date rule, the counts, the doubtful rows and each batch's preview against
        the records now; nothing is imported. The model is asked only about columns no heading names, and sees their headings and
        three sample rows, without the lock (AdapterError: MODEL_UNAVAILABLE on the surface). The result is what the model may see;
        the card's flagged rows (their cells) and customers come as the payload, which the tool surface adds to the result."""
        try:
            hints = importer.check_hints(args.get('hints'))
        except RecordsError as exc:
            raise ToolError(exc.code, exc.message, executed=False) from None
        if args.get('sheet') is not None:
            hints['sheet'] = _text_arg(args, 'sheet', 120)
        with self.app.lock:
            doc = self.app.fixture()
            settings, today = settings_of(doc), self.app.today(doc)
            base = self.import_proposal(_text_arg(args, 'proposalId', 80)) if args.get('proposalId') is not None else None
        if base and base['status'] == 'applied':
            raise ToolError('ALREADY_APPLIED', 'This proposal was already imported; its batches can be reverted on the Imports page.',
                            executed=False, extra={'batches': base['batches']})
        if base and not base['file']:
            raise ToolError('NOT_FOUND', 'The file of this proposal is no longer kept; attach it again.', executed=False)
        file = base['file'] if base else self.import_file(args)
        name = base['fileName'] if base else _text_arg(args, 'fileName', 120, required=False) or ('pasted.csv' if 'csvText' in file else 'attachment')
        hints = importer.revised(base, hints) if base else hints
        sheets, sheet, p = self.draft_import(file, hints, self.classify_columns, settings, today)
        with self.app.lock:
            stored = self.keep_import(base, file, name, hints, sheets, sheet, p)
        return ToolDispatcher._ok('proposeImport', args, stored['view'], None, {'tool': 'proposeImport', **stored['card']})

    def keep_status(self, p, status, error):
        p.update({'status': status, 'lastError': error})
        with self.app.db:
            self.app.set_meta(IMPORT_PROPOSALS + p['id'], p)

    def keep_aliases(self, p, made):
        """The codes a file gave its customers, kept as aliases of the customers this import created (findCustomers matches aliases)."""
        doc = self.app.fixture()
        created = {c for m in made for c in self.app.batch(m['id'])['result']['customers']}
        for name, found in (p.get('aliases') or {}).items():
            for c in doc['customers']:
                if c['id'] in created and name_key(c['name']) == name_key(name):
                    c['aliases'] = c.get('aliases', []) + [a for a in found if a not in c.get('aliases', [])]
        with self.app.db:
            self.app.save_doc(doc)

    def _applyImportProposal(self, args):
        """The import a person accepted by pressing Import: offered to no agent (tools_for gives it only to a person on the tool
        surface, pressedBy). Only the version shown is imported; corrections sent with the press make the next version (no model
        is asked), which is imported at once. The batches go through the importer's own upload, mapping and apply, each kept with
        its preview and its revert, and only if previewing them on the records as they are now gives what the proposal showed
        (each row's status and the customers created); otherwise nothing is written. Returns {proposalId, version, batches: [{id,
        shape, counts, revertLink}]}. Lock held."""
        p = self.import_proposal(_text_arg(args, 'proposalId', 80))
        if p['status'] == 'applied':   # pressed twice: the same batches, nothing written
            return {'proposalId': p['id'], 'version': p['version'], 'batches': p['batches']}
        if type(args.get('version')) is not int:
            raise ToolError('INVALID_ARGUMENT', 'version must be the version of the proposal shown.', executed=False)
        if not self.app.recheck_unit(p):
            self.keep_status(p, 'stale', STALE_PROPOSAL)
            raise ToolError('STALE_PROPOSAL', STALE_PROPOSAL, executed=False)
        twin = self.applied_twin(p.get('sha256'), p['id']) if p.get('sha256') else None
        if twin:
            self.keep_status(p, 'duplicate', None)
            raise ToolError('DUPLICATE', duplicate_message(twin, settings_of(self.app.fixture())['timezone']), executed=False)
        if args['version'] != p['version']:
            raise ToolError('STALE_VERSION', 'The proposal has changed since version ' + str(args['version']) + ' (it is now version ' + str(p['version']) +
                            '). Check it, then import.', executed=False, extra={'version': p['version']})
        doc = self.app.fixture()
        settings, today = settings_of(doc), self.app.today(doc)
        problem = unit_problem(p['view'].get('unit') or {'detected': None}, {'currency': settings['currency'], 'scale': settings['scale']})
        if problem:   # before anything is written
            self.keep_status(p, 'refused', problem)
            raise ToolError('UNIT_MISMATCH', problem, executed=False)
        if args.get('corrections'):
            if not p['file']:
                raise ToolError('NOT_FOUND', 'The file of this proposal is no longer kept; attach it again.', executed=False)
            try:
                hints = importer.revised(p, importer.check_hints(args['corrections']))
            except RecordsError as exc:
                raise ToolError(exc.code, exc.message, executed=False) from None
            p = self.keep_import(p, p['file'], p['fileName'], hints, *self.draft_import(p['file'], hints, None, settings, today))
        if not p['view']['ready']:
            raise ToolError('NOT_READY', 'The proposal still needs: ' + ' '.join(p['view']['needs']), executed=False,
                            extra={'needs': p['view']['needs'], 'version': p['version']})
        source = p['hints'].get('sourceLabel') or IMPORT_SOURCE
        if importer.expected(importer.dry_run(doc, p['batches'], settings, today, source)) != p['expected']:
            raise ToolError('RECORDS_CHANGED', 'The records changed since this proposal was made. Propose it again (the same proposalId) to see what '
                            'it would import now.', executed=False, extra={'version': p['version']})
        made, batch = [], None
        try:
            for b in p['batches']:   # the lock is held throughout, so each preview is the dry run's
                batch = self.app.batch(self.app.upload_import(self.actor, {'csvText': b['csvText'], 'fileName': p['fileName'], 'sourceLabel': source,
                                                                             'shape': b['shape']})['id'])
                self.app.update_import(self.actor, batch, {k: b['params'][k] for k in ('mapping', 'dateOrder', 'asOf', 'resolutions')})
                done = self.app.apply_import(self.actor, batch)
                made.append({'id': done['id'], 'shape': b['shape'], 'counts': done['preview']['counts'], 'revertLink': '#/imports/' + done['id']})
                batch = None
            self.keep_aliases(p, made)
        except (RecordsError, ToolError) as exc:   # all or nothing: what was applied is reverted, the proposal stays proposed with the error
            message = exc.message
            if batch is not None and self.app.batch(batch['id'])['status'] == 'preview':
                self.app.discard_import(self.actor, self.app.batch(batch['id']))
            for m in reversed(made):
                self.app.revert_import(self.actor, self.app.batch(m['id']), {'reason': 'The import did not complete'})
            self.keep_status(p, 'proposed', message)
            raise ToolError('APPLY_FAILED', 'The import did not finish (' + message + ') and what it had written was undone. Nothing was imported.',
                            executed=False) from None
        p.update({'status': 'applied', 'batches': made, 'appliedBy': self.by, 'pressedBy': self.by, **self.trail, 'appliedAt': now(),
                  'appliedOn': self.today.isoformat(), 'file': None, 'lastError': None})   # the batches keep what was imported; appliedOn: the business date then
        with self.app.db:
            self.app.set_meta(IMPORT_PROPOSALS + p['id'], p)
        return {'proposalId': p['id'], 'version': p['version'], 'batches': made}


class Handler(BaseHTTPRequestHandler):
    timeout = 30   # seconds per socket read; a stalled client cannot hold a worker thread indefinitely

    def log_message(self, *_):
        pass

    def cookie_header(self, role, token):
        secure = '; Secure' if self.server.secure_cookie else ''
        expire = '; Max-Age=0' if token is None else ''
        app = self.server.app
        return app.cookie_prefix + role + '=' + (token or '') + '; HttpOnly; SameSite=Strict; Path=' + app.cookie_path + secure + expire

    @staticmethod
    def lab_role(app, cookie):
        """The role the AI Agent's browser has selected (the Lab's cookie), when this browser holds the agent and that role; else None."""
        value = cookie.get(LAB_ROLE)
        held = app.signed_in(cookie) if value and value.value in CASE_ROLES else {}
        return value.value if held.get(value.value if value else None, {}).get('kind') == 'agent' else None

    def send_json(self, status, payload, cookie=None, cookies=(), extra=()):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        for each in ([cookie] if cookie else []) + list(cookies):
            self.send_header('Set-Cookie', self.cookie_header(*each))
        for each in extra:
            self.send_header('Set-Cookie', each)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_csv(self, text, filename):
        data = text.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/csv; charset=utf-8')
        self.send_header('Content-Disposition', 'attachment; filename="' + filename + '"')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_file(self, path, content_type, cache, data=None, etag=None):
        data = path.read_bytes() if data is None else data
        if etag and self.headers.get('If-None-Match') == etag:
            self.send_response(304); self.send_header('ETag', etag); self.send_header('Cache-Control', cache); self.end_headers(); return
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Cache-Control', cache)
        if etag:
            self.send_header('ETag', etag)
        self.send_header('X-Content-Type-Options', 'nosniff')
        if content_type.startswith('text/html'):
            self.send_header('Content-Security-Policy', CSP)
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.handle_call(False)

    def do_POST(self):
        self.handle_call(True)

    do_PUT = do_POST   # the authority settings are read with GET and set with PUT

    def static(self, path, query):
        """A file under web/. The page links each file with ?v=<hash of its content> (page_html), so a changed file has a new address and no cache (a
        browser's, or Cloudflare's edge in front of the public hostnames) can keep serving the old one; a versioned address may be cached for a year.
        An unversioned address revalidates every time (no-cache) and answers 304 to a matching ETag."""
        name = path[len('/static/'):]
        require(re.fullmatch(r'[a-z0-9-]+(/[a-z0-9.-]+)?\.(css|js|woff2|svg|txt)', name), 404, 'NOT_FOUND', 'Unknown file.')
        target = WEB / name
        require(target.is_file() and target.resolve().is_relative_to(WEB.resolve()), 404, 'NOT_FOUND', 'Unknown file.')
        data = target.read_bytes()
        digest = static_version(target, data)
        asked = (parse_qs(query).get('v') or [None])[0]
        cache = 'public, max-age=31536000, immutable' if asked == digest else ('public, max-age=604800' if name.startswith('fonts/') else 'no-cache')
        self.send_file(target, STATIC_TYPES[target.suffix], cache, data=data, etag='"%s"' % digest)

    def handle_call(self, write):
        try:
            path = urlparse(self.path).path
            if path == '/' and not write:
                return self.send_file(WEB / 'index.html', 'text/html; charset=utf-8', 'no-store', data=page_html())
            if path.startswith('/static/') and not write:
                return self.static(path, urlparse(self.path).query)
            require(path.startswith('/api/'), 404, 'NOT_FOUND', 'Unknown route.')
            app = self.server.app
            body = {}
            if write:
                require(self.headers.get('Content-Type', '').split(';')[0] == 'application/json', 400, 'INVALID_CONTENT_TYPE', 'Use application/json.')
                length = int(self.headers.get('Content-Length', '0'))
                limit = {'/api/imports': 2_500_000, '/api/tools/proposeImport': 4_000_000}.get(path, 65536)   # a 2.5 MB file, in base64
                require(0 < length <= limit, 400, 'INVALID_BODY', 'Invalid request size.')
                origin = self.headers.get('Origin')
                require(not origin or origin in self.server.allowed_origins, 403, 'FORBIDDEN', 'Cross-origin writes are disabled.')
                # Confirming or cancelling an action is a person's act in the browser: a call with no Origin (a script, a service) is refused.
                require(origin or not re.fullmatch(r'/api/actions/[\w-]+/(?:confirm|cancel|evidence)', path), 403, 'ORIGIN_REQUIRED',
                        'Confirm, cancel and evidence come from the Nucleon page in a browser: send the Origin header.')
                require(origin or not DELEGATION_WRITE.fullmatch(path), 403, 'ORIGIN_REQUIRED',
                        'The Owner\'s delegation policy and decisions come from the Nucleon page in a browser: send the Origin header.')
                body = json.loads(self.rfile.read(length))
                if path == '/api/ui-events' and isinstance(body, list):
                    body = {'events': body}   # the pages send the plain list
                require(isinstance(body, dict), 400, 'INVALID_BODY', 'Expected a JSON object.')
            cookie = SimpleCookie()
            cookie.load(self.headers.get('Cookie', ''))
            role = self.headers.get('X-Nucleon-Role') or None
            if role is None and (write and path == '/api/ui-events' or not write and path in DOWNLOADS):   # navigator.sendBeacon (a page closing) and a download link
                role = (parse_qs(urlparse(self.path).query).get('role') or [None])[0]   # cannot set headers: they name the role in the address
            require(role is None or role in app.demo_codes, 400, 'INVALID_ROLE', 'Unknown role.')
            chosen = self.lab_role(app, cookie)   # the AI Agent: one selected role for the Lab and these pages, in the Lab's cookie;
            # the pages mark their requests (X-Nucleon-Follow-Role) so one still acting as another role is told to follow it. A call naming its role without the mark is trusted.
            if chosen and self.headers.get('X-Nucleon-Follow-Role') and role in CASE_ROLES and role != chosen and path not in ('/api/session', '/api/session/role', '/api/demo/login', '/api/demo/logout'):
                raise APIError(409, 'ROLE_CHANGED', 'The role was switched in another tab. This page now follows it.')
            if path == '/api/session/role' and write:
                with app.lock:
                    agent = next((a for a in app.signed_in(cookie).values() if a.get('kind') == 'agent'), None)
                    held = app.signed_in(cookie)
                where = str(body.get('path') or '/')
                require(agent and body.get('role') in CASE_ROLES and body['role'] in held, 400, 'INVALID_ROLE', 'Choose a role this sign-in holds.')
                require(re.fullmatch(r'/[\w./-]*', where) and '..' not in where, 400, 'INVALID_BODY', 'Invalid path.')
                self.send_json(200, {'role': body['role']}, extra=[LAB_ROLE + '=' + body['role'] + '; HttpOnly; SameSite=Strict; Path=' + where + ('; Secure' if self.server.secure_cookie else '')])
                return
            if path == '/api/model-status' and not write:
                with app.lock:
                    app.identity(cookie, role)
                self.send_json(200, app.model_status())   # network probe outside the lock
                return
            tool = re.fullmatch(r'/api/tools(?:/(\w+))?', path)
            if tool:   # each read takes the lock, and a model-calling tool asks the model without it
                with app.lock:
                    actor = app.identity(cookie, role)
                    require(actor['role'] in CASE_ROLES, 403, 'FORBIDDEN', 'The demo console code cannot be used for case work.')
                    if not write and not tool.group(1):
                        self.send_json(200, app.tool_registry(actor))
                        return
                require(write and tool.group(1), 404, 'NOT_FOUND', 'Unknown route.')
                self.send_json(200, app.tool_call(actor, tool.group(1), body, self.headers.get('Idempotency-Key')))
                return
            with app.lock:
                if path == '/api/demo/login' and write:
                    actor, tokens = app.login(body)
                    for role_name in tokens:
                        earlier = cookie.get(app.cookie_prefix + role_name)
                        if earlier:   # signing in again for a role replaces this browser's earlier session for it
                            app.sessions.pop(earlier.value, None)
                    self.send_json(200, {**actor, **app.identity_view(actor, tokens)}, cookies=list(tokens.items()))
                    return
                if path == '/api/demo/logout' and write:
                    # Sign out ends every role session this browser holds (QA B1), whichever role is selected. Sessions are per
                    # browser cookie, so teammates signed in elsewhere stay signed in.
                    held = app.signed_in(cookie)
                    for role_name in held:
                        app.sessions.pop(cookie[app.cookie_prefix + role_name].value, None)
                    sent = [r for r in app.demo_codes if cookie.get(app.cookie_prefix + r)]
                    self.send_json(200, {'signedOut': sorted(held)}, cookies=[(r, None) for r in sent])
                    return
                if path == '/api/session' and not write:
                    roles = app.signed_in(cookie)
                    actor = roles.get(role) if role else (next(iter(roles.values())) if len(roles) == 1 else None)
                    if actor is None:   # a session probe is not an error, and reveals nothing about the environment
                        agent = next((a for a in roles.values() if a.get('kind') == 'agent'), None)   # the probe names the agent before a role is chosen
                        self.send_json(200, {'authenticated': False, 'signedIn': sorted(roles), **({'identity': app.identity_view(agent, roles)['identity'], 'selectedRole': self.lab_role(app, cookie)} if agent else {})})
                        return
                    setup = app.setup_state()
                    self.send_json(200, {**actor, **app.identity_view(actor, roles), 'authenticated': True, 'signedIn': sorted(roles), 'hasRecords': setup['ready'],
                                         'workspace': (setup['workspace'] or {}).get('mode'), 'dataMode': setup['dataMode'],
                                         'agentMode': app.agent_mode, 'agent': app.agent_info(), 'asOfDate': setup['asOfDate'],
                                         'fixedDate': bool((app.fixture() or {}).get('asOfDate')),
                                         'demoConsole': app.console_allowed(), 'assistantUrl': app.assistant_url_for(actor['role'])})
                    return
                actor = app.identity(cookie, role)
                if path.startswith('/api/demo/'):
                    require(app.console_allowed(), 404, 'NOT_FOUND', 'The demo console is not enabled here.')
                    require(actor['role'] == 'operator', 403, 'FORBIDDEN', 'Sign in with the demo console code.')
                    if path == '/api/demo/console' and not write:
                        self.send_json(200, {**app.console_state(), **app.identity_view(actor, app.signed_in(cookie))})
                    elif path == '/api/demo/reset' and write:
                        self.send_json(200, {**app.reset_demo(actor, body.get('to')), 'console': app.console_state()})
                    elif path == '/api/demo/start-empty' and write:
                        self.send_json(200, {**app.start_empty(actor), 'console': app.console_state()})
                    elif path == '/api/demo/restore' and write:
                        self.send_json(200, {**app.restore_demo(actor, body.get('backup')), 'console': app.console_state()})
                    elif path == '/api/demo/advance' and write:
                        self.send_json(200, {'today': app.advance_business_date(actor, body.get('days')).isoformat()})
                    else:
                        raise APIError(404, 'NOT_FOUND', 'Unknown route.')
                    return
                require(actor['role'] in CASE_ROLES, 403, 'FORBIDDEN', 'The demo console code cannot be used for case work.')
                if path == '/api/setup' and not write:
                    self.send_json(200, app.setup_state())
                    return
                setup_actions = {'/api/setup/workspace': app.setup_workspace, '/api/setup/settings': app.save_settings,
                                 '/api/setup/skip': app.skip, '/api/setup/sample': lambda a, b: app.load_sample_on_request(a)}
                if path in setup_actions and write:
                    self.send_json(200, setup_actions[path](actor, body))
                    return
                if path == '/api/setup/authority':
                    self.send_json(200, app.save_authority(actor, body) if write else app.authority_view(actor))
                    return
                if path == '/api/records' and not write:
                    self.send_json(200, app.records_view())
                    return
                if path == '/api/imports':
                    self.send_json(200, app.upload_import(actor, body) if write else app.imports_list())
                    return
                if path.startswith('/api/imports/'):
                    parts = path.strip('/').split('/')
                    batch = app.batch(parts[2])
                    action = parts[3] if len(parts) == 4 else None
                    require(len(parts) in (3, 4), 404, 'NOT_FOUND', 'Unknown route.')
                    handlers = ({'mapping': lambda: app.update_import(actor, batch, body), 'apply': lambda: app.apply_import(actor, batch),
                                 'revert': lambda: app.revert_import(actor, batch, body), 'discard': lambda: app.discard_import(actor, batch)} if write else
                                {None: lambda: app.batch_view(batch), 'impact': lambda: app.revert_preview(batch)})
                    require(action in handlers, 404, 'NOT_FOUND', 'Unknown route.')
                    self.send_json(200, handlers[action]())
                    return
                if path.startswith('/api/records/imports/proposals/') and not write:
                    self.send_json(200, app.proposal_state(path.rsplit('/', 1)[1]))
                    return
                if path.startswith('/api/records/') and write:
                    self.send_json(200, app.records_action(actor, path.strip('/').split('/')[2:], body, self.headers.get('Idempotency-Key')))
                    return
                if path == '/api/requests':
                    if write:
                        r = app.create(actor, body, self.headers.get('Idempotency-Key'))
                        app.wait_settled(r['id'], app.wait_seconds())
                        self.send_json(202, app.view(app.get(r['id']), actor['role']))
                    else:
                        records = app.records()
                        self.send_json(200, [summary(r, records) for r in records])
                    return
                if path == '/api/suggestions':   # staff are told suggestions are off: the setting, like the suggestion, is the owner's
                    self.send_json(200, app.set_suggestions(actor, body) if write else {'on': actor['role'] == 'owner' and bool(app.meta('showSuggestions'))})
                    return
                if path == '/api/agent-tools':
                    self.send_json(200, app.set_agent_tool(actor, body, self.headers.get('Idempotency-Key')) if write else app.agent_tools(actor))
                    return
                if path == '/api/suggestions/counters' and not write:
                    require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner sees the suggestion counters.')
                    self.send_json(200, app.suggestion_counters())
                    return
                action = re.fullmatch(r'/api/actions/([\w-]+)(?:/(confirm|cancel|evidence))?', path)
                if action and not write and not action.group(2):
                    self.send_json(200, app.action_view(actor, app.get_action(action.group(1))))
                    return
                if action and write and action.group(2):
                    app.person_required(actor)   # first: a service or the AI Agent is told so, whatever else it sent
                    app.require_csrf(actor, self.headers.get('X-Nucleon-CSRF'))   # the page's own token; a refusal here changes nothing
                    run = {'confirm': app.confirm_action, 'cancel': app.cancel_action, 'evidence': app.submit_evidence}[action.group(2)]
                    self.send_json(200, run(actor, action.group(1), body, self.headers.get('Idempotency-Key')))
                    return
                # the Owner's delegation policy and decisions (docs/ADAPTIVE-DECISION-AUTHORITY.md section 8): written only by an Owner PERSON, with the page's csrf token and Origin
                if path == '/api/delegation/policy':
                    if write:
                        require(self.command == 'PUT', 405, 'METHOD_NOT_ALLOWED', 'The policy is saved with PUT.')
                        app.person_required(actor)
                        app.require_csrf(actor, self.headers.get('X-Nucleon-CSRF'))
                        self.send_json(200, app.save_policy(actor, body))
                    else:
                        app.sweep_schedules()
                        self.send_json(200, app.policy_view(actor, app.policy_current()))
                    return
                if path in ('/api/delegation/policy/pause', '/api/delegation/policy/resume') and write:
                    app.person_required(actor)
                    app.require_csrf(actor, self.headers.get('X-Nucleon-CSRF'))
                    self.send_json(200, app.save_policy(actor, body, path.rsplit('/', 1)[1]))
                    return
                if path == '/api/delegation/sweep-tacit-consent' and write:
                    app.person_required(actor)
                    app.require_csrf(actor, self.headers.get('X-Nucleon-CSRF'))
                    self.send_json(200, app.delegation_sweep(actor))
                    return
                if path == '/api/delegation/observe-outcomes' and write:
                    app.person_required(actor)
                    app.require_csrf(actor, self.headers.get('X-Nucleon-CSRF'))
                    self.send_json(200, app.delegation_observe(actor, body))
                    return
                if not write and path == '/api/delegation/loop':
                    self.send_json(200, app.delegation_loop(actor))
                    return
                if not write and path == '/api/delegation/ui-summary':
                    self.send_json(200, app.delegation_ui_summary(actor, parse_qs(urlparse(self.path).query)))
                    return
                if write and path == '/api/ui-events':
                    self.send_json(200, app.ui_events_add(actor, body))
                    return
                if not write and path == '/api/actions':
                    self.send_json(200, app.actions_open_evidence(actor, parse_qs(urlparse(self.path).query)))
                    return
                if not write and path == '/api/delegation/impact':
                    self.send_json(200, app.delegation_impact(actor, parse_qs(urlparse(self.path).query)))
                    return
                if path == '/api/notices' and not write:
                    self.send_json(200, app.notices_list(actor)); return
                if path == '/api/notices/read' and write:
                    app.require_csrf(actor, self.headers.get('X-Nucleon-CSRF'))
                    self.send_json(200, app.notices_read(actor, body)); return
                if not write and path == '/api/delegation/exposure':
                    self.send_json(200, app.delegation_exposure(actor)); return
                if path == '/api/delegation/schedules':
                    if write:
                        app.person_required(actor)
                        app.require_csrf(actor, self.headers.get('X-Nucleon-CSRF'))
                        self.send_json(200, app.schedule_add(actor, body))
                    else:
                        self.send_json(200, app.schedules_list(actor))
                    return
                sched = re.fullmatch(r'/api/delegation/schedules/([\w-]+)/cancel', path)
                if sched and write:
                    app.person_required(actor)
                    app.require_csrf(actor, self.headers.get('X-Nucleon-CSRF'))
                    self.send_json(200, app.schedule_cancel(actor, sched.group(1))); return
                if not write and path == '/api/delegation/research/model.json':
                    m = app.research_model_current()
                    require(actor['role'] == 'owner', 403, 'FORBIDDEN', 'Only the owner downloads the model.')
                    require(m is not None, 404, 'NOT_FOUND', 'No model is in force.')
                    self.send_csv(json.dumps({k: v for k, v in m.items() if k != 'source'}, indent=1), 'nucleon-model-v' + str(m.get('version')) + '.json'); return
                if not write and path == '/api/delegation/training.csv':
                    self.send_csv(app.delegation_training(actor), 'nucleon-training.csv'); return
                if not write and path == '/api/delegation/research':
                    self.send_json(200, app.delegation_research(actor)); return
                if write and path in ('/api/delegation/research/refit', '/api/delegation/research/settings'):
                    app.person_required(actor)
                    app.require_csrf(actor, self.headers.get('X-Nucleon-CSRF'))
                    self.send_json(200, app.research_refit(actor, body) if path.endswith('refit') else app.save_research_settings(actor, body))
                    return
                if path == '/api/staff/practice':
                    if write:
                        app.person_required(actor)
                        app.require_csrf(actor, self.headers.get('X-Nucleon-CSRF'))
                        self.send_json(200, app.set_staff_practice(actor, body))
                    else:
                        require(actor['role'] in CASE_ROLES, 403, 'FORBIDDEN', 'Only the owner or staff read this.')
                        self.send_json(200, app.staff_practice())
                    return
                if not write and path == '/api/delegation/presets':
                    self.send_json(200, app.policy_presets(actor))
                    return
                preset = re.fullmatch(r'/api/delegation/presets/(\w+)', path)
                if write and preset:
                    app.person_required(actor)
                    app.require_csrf(actor, self.headers.get('X-Nucleon-CSRF'))
                    self.send_json(200, app.apply_preset(actor, preset.group(1), body))
                    return
                if not write and path == '/api/delegation/doctor':
                    self.send_json(200, app.doctor(actor, parse_qs(urlparse(self.path).query)))
                    return
                if not write and path == '/api/delegation/quick-setup':
                    self.send_json(200, app.quick_setup(actor))
                    return
                if write and path == '/api/delegation/quick-setup/preview':
                    app.person_required(actor)
                    app.require_csrf(actor, self.headers.get('X-Nucleon-CSRF'))
                    self.send_json(200, app.quick_setup_preview(actor, body))
                    return
                if not write and path == '/api/delegation/preferences/next':
                    self.send_json(200, app.preference_next(actor))
                    return
                if write and path == '/api/delegation/preferences/answer':
                    app.person_required(actor)
                    app.require_csrf(actor, self.headers.get('X-Nucleon-CSRF'))
                    self.send_json(200, app.preference_answer(actor, body))
                    return
                if not write and path in ('/api/delegation/policy/history', '/api/delegation/cases', '/api/delegation/suggestions', '/api/delegation/stats'):
                    self.send_json(200, {'/api/delegation/policy/history': lambda: app.policy_history(actor), '/api/delegation/cases': lambda: app.delegation_cases(actor, parse_qs(urlparse(self.path).query)),
                                         '/api/delegation/suggestions': lambda: app.delegation_suggestions(actor), '/api/delegation/stats': lambda: app.delegation_stats(actor)}[path]())
                    return
                if not write and path == '/api/decision-cases':
                    self.send_json(200, app.decision_cases_list(actor, parse_qs(urlparse(self.path).query)))
                    return
                case = re.fullmatch(r'/api/decision-cases/([\w-]+)(?:/(decide|feedback|viewed|events|evidence-request))?', path)
                if case:
                    if not write and case.group(2) == 'events':
                        self.send_json(200, app.case_events_view(actor, case.group(1)))
                        return
                    if not write and not case.group(2):
                        found = app.dg_case(case.group(1))
                        require(found['dataset'] == 'live', 404, 'NOT_FOUND', 'Decision case not found.')
                        self.send_json(200, app.case_view(found, actor['role']))
                        return
                    if write and case.group(2) == 'viewed':
                        app.person_required(actor)
                        app.require_csrf(actor, self.headers.get('X-Nucleon-CSRF'))
                        self.send_json(200, app.case_viewed(actor, case.group(1)))
                        return
                    if write and case.group(2) == 'evidence-request':
                        app.person_required(actor)
                        app.require_csrf(actor, self.headers.get('X-Nucleon-CSRF'))
                        self.send_json(200, app.evidence_request(actor, case.group(1)))
                        return
                    if write and case.group(2) in ('decide', 'feedback'):
                        app.person_required(actor)
                        app.require_csrf(actor, self.headers.get('X-Nucleon-CSRF'))
                        self.send_json(200, app.decide_case(actor, case.group(1), body) if case.group(2) == 'decide' else
                                       app.case_feedback(actor, case.group(1), body, self.headers.get('Idempotency-Key')))
                        return
                parts = path.strip('/').split('/')
                require(len(parts) >= 3 and parts[:2] == ['api', 'requests'], 404, 'NOT_FOUND', 'Unknown route.')
                r = app.get(parts[2])
                if len(parts) == 3 and not write:
                    self.send_json(200, app.view(r, actor['role']))
                    return
                if len(parts) == 4 and parts[3] == 'basis' and not write:   # the calculation details: the case's readers, as the case itself
                    asked = parse_qs(urlparse(self.path).query).get('version')
                    self.send_json(200, app.basis_view(r, actor['role'], asked and asked[0]))
                    return
                if len(parts) == 4 and parts[3] == 'response-draft' and not write:
                    self.send_json(200, r['responseDraft'] or {'status': 'pending'})
                    return
                key = self.headers.get('Idempotency-Key')
                if write and len(parts) == 4 and parts[3] == 'reanalyse':
                    r = app.reanalyse(actor, r, body, key)
                    app.wait_settled(r['id'], app.wait_seconds())
                    self.send_json(202, app.view(app.get(r['id']), actor['role']))
                elif write and len(parts) == 4 and parts[3] == 'decisions':
                    result = app.decide(actor, r, body, key)
                    self.send_json(201, result['decision'])
                elif write and len(parts) == 6 and parts[3] == 'clarifications' and parts[5] == 'answers':
                    r = app.answer(actor, r, parts[4], body, key)
                    app.wait_settled(r['id'], app.wait_seconds())
                    self.send_json(202, app.view(app.get(r['id']), actor['role']))
                elif write and len(parts) == 6 and parts[3] == 'questions' and parts[5] in ('answer', 'skip'):
                    r = app.owner_question(actor, r, parts[4], parts[5], body, key)
                    app.wait_settled(r['id'], app.wait_seconds())   # the suggestion step it may have started
                    self.send_json(200, app.view(app.get(r['id']), actor['role']))
                else:
                    raise APIError(404, 'NOT_FOUND', 'Unknown route.')
        except (APIError, RecordsError) as exc:
            self.send_json(exc.status, {'error': exc.code, 'message': exc.message, **({'field': exc.field} if exc.field else {}),
                                        **getattr(exc, 'extra', {})})
        except (ValueError, TypeError, json.JSONDecodeError):
            self.send_json(400, {'error': 'INVALID_INPUT', 'message': 'Invalid JSON or field format.'})
        except Exception as exc:
            log('request error', type(exc).__name__)
            self.send_json(500, {'error': 'INTERNAL_ERROR', 'message': 'The operation failed. Saved work remains available.'})


class Server(ThreadingHTTPServer):
    # Behind the proxy one page load opens a connection per file at once (8 for the redesigned page); the default queue of 5 reset some (502s).
    request_queue_size = 128


def make_server(app, port=8765, public_origins=()):
    server = Server(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    server.app = app
    bound = server.server_port
    # Explicit allowlist: loopback for local use plus configured public origins (e.g. the HTTPS proxy).
    server.allowed_origins = {'http://127.0.0.1:' + str(bound), 'http://localhost:' + str(bound), *public_origins}
    server.secure_cookie = any(o.startswith('https://') for o in public_origins)
    return server


def announce_codes(app):
    """The codes, one per line on stdout (the service log): the access codes people are given, then, apart, the service codes for the Lab alone.
    Different words ('access code' / 'service code') keep the scripts that read the access lines from ever taking a service code for a person's."""
    for role, code in app.demo_codes.items():
        print(role.upper() + ' access code: ' + code, flush=True)
    for role, code in app.service_codes.items():   # a session made with one is a service's and cannot confirm or cancel an action
        print(role.upper() + ' service code: ' + code, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', help='JSON service config (see config.example.json); flags override it')
    parser.add_argument('--port', type=int)
    parser.add_argument('--db')
    parser.add_argument('--agent-mode', choices=['live', 'mock', 'unavailable'])
    parser.add_argument('--model-config', help='JSON file with the model adapter settings')
    parser.add_argument('--public-origin', action='append', help='Exact browser origin allowed to write, e.g. https://host')
    parser.add_argument('--sample-data', action='store_true', default=None,
                        help='Load the fictional sample records into an empty database (config: "sampleData": true)')
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text()) if args.config else {}
    port = args.port or config.get('port', 8765)
    db = args.db or config.get('db') or str(ROOT / '.runtime' / 'demo.sqlite3')
    mode = args.agent_mode or config.get('agentMode', 'mock')
    origins = args.public_origin or config.get('publicOrigins', [])
    for origin in origins:
        if not re.fullmatch(r'https?://[A-Za-z0-9.-]+(:\d+)?', origin):
            sys.exit('Invalid --public-origin ' + origin + ' (use scheme://host[:port], no path)')
    cookie_prefix, cookie_path = config.get('cookiePrefix', 'nucleon_'), config.get('cookiePath', '/')
    if not re.fullmatch(r'[A-Za-z0-9_]+', str(cookie_prefix)) or not re.fullmatch(r'/[A-Za-z0-9/_.-]*', str(cookie_path)):
        sys.exit('Invalid cookiePrefix or cookiePath (letters, digits and _; a path such as /preview)')
    for key in ('assistantUrl', 'ownerAssistantUrl'):
        try:
            checked_assistant_url(config.get(key))
        except ValueError as error:
            sys.exit('Invalid ' + key + ' in the config: ' + str(error))
    model_config = load_model_config(args.model_config) if args.model_config else config.get('model')
    adapter = OpenAIChatAdapter(model_config) if model_config else None
    if mode == 'live' and adapter is None:
        sys.exit('Live mode needs --model-config or a "model" section in --config.')
    Path(db).parent.mkdir(parents=True, exist_ok=True)
    app = App(db, mode, adapter, deadline_seconds=float((model_config or {}).get('runDeadlineSeconds', 300)), verbose=True,
              demo=config.get('demo'), sample_data=bool(args.sample_data or config.get('sampleData')),
              cookie_prefix=cookie_prefix, cookie_path=cookie_path, access_codes=config.get('accessCodes'), service_codes=config.get('serviceCodes'), assistant_url=config.get('assistantUrl'), owner_assistant_url=config.get('ownerAssistantUrl'),
              shadow_model=config.get('shadowModel'), research_provider=config.get('researchProvider'), notifications=config.get('notifications'))
    server = make_server(app, port, origins)
    records, ws = app.fixture(), app.meta('workspace')
    log(('Workspace: ' + ws['mode'] + (' with the fictional sample' if ws.get('sampleFingerprint') else '') if ws else
         'No workspace yet (the owner sets it up on first sign-in; --sample-data sets up a practice one)') +
        ' | agent mode: ' + mode + (' | model: ' + adapter.label + ' via ' + adapter.base_url if mode == 'live' else ''))
    log('URL: http://127.0.0.1:' + str(server.server_port) + (' | public origins: ' + ', '.join(origins) if origins else ''))
    log('Demo console: ' + ('enabled, backups in ' + str(app.backup_dir) if app.demo else 'disabled'))
    announce_codes(app)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        app.db.close()


if __name__ == '__main__':
    main()
