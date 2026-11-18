"""The financial card: one self-contained HTML page for a customerOverview or invoices result, shown by MCP-UI clients (LibreChat) beside
the result's JSON. Presentation only. Every word and figure comes from the result the records gave: nothing is added up, derived or
judged here (completeness, marks and amounts are the records'), a field the records did not give reads "Not recorded" or "Unavailable",
never 0, and only an explicit balanceEstablished of true is shown as confirmed records (anything else is Unconfirmed, fail closed).

The page is inert: no links, forms, buttons or actions; its one script is fixed (no data in it) and only tells the host the page's height
(an `ui-size-change` message, the one type a host takes as a size and not as an action). A CSP meta allows that script by its hash and
nothing else. Every string from the result is escaped. The same result gives the same bytes (the host's resource id is a hash of them).

The DECISION card (assessDecision, resolveDecision, decisionStatus; docs/ADAPTIVE-DECISION-AUTHORITY.md) follows the same rules: its badge is chosen
from the backend's own status and handling only (an assessment is a preview and never claims a decision), every date and figure is the result's, and
its one button, only for a case that is gathering evidence, opens the evidence page of the result's actionId by the same checked URL.

The two ACTION cards (prepareRequest, actionStatus; Phase B of docs/CONTROLLED-AGENT-ACTIONS.md) are the only cards with a button, and the button
writes nothing: a click posts {type: 'link', payload: {url}} to the host, which may open the Nucleon confirmation page (the contract with the
LibreChat patch 0003). The url is built here from the Lab's recordsPublicUrl and the actionId of the result and must fit the contract exactly
(`confirm_url`), else there is no button; the click handler is a second fixed script (the url is in a data attribute, never in a script), allowed
by its own hash, and runs only on a click. The cards above are unchanged, byte for byte."""
import base64
import hashlib
import html
import re
from datetime import datetime, timezone
from urllib.parse import quote

FINANCIAL_CARDS = ('customerOverview', 'invoices')
ACTION_CARDS = ('prepareRequest', 'actionStatus')
DECISION_CARDS = ('assessDecision', 'resolveDecision', 'decisionStatus')   # Adaptive Decision Authority: one card for all three
CARD_TOOLS = FINANCIAL_CARDS + ACTION_CARDS + DECISION_CARDS
MAX_ROWS = 30
NOT_RECORDED, UNAVAILABLE = 'Not recorded', 'Unavailable'

# What each reason code of completeness.reasons means in a few words; a code not here is shown as its own words (underscores to spaces).
REASON_LABELS = {
    'invoices_not_confirmed': 'Invoice records not confirmed complete',
    'payments_not_confirmed': 'Payment records not confirmed complete',
    'invoices_complete_to_earlier_date': 'Invoice records confirmed only to an earlier date',
    'payments_complete_to_earlier_date': 'Payment records confirmed only to an earlier date',
    'invoices_contradicted': 'An invoice completeness statement no longer holds',
    'payments_contradicted': 'A payment completeness statement no longer holds',
    'no_invoices_recorded': 'No invoices recorded',
    'no_payments_recorded': 'No payments recorded',
    'records_incomplete': 'Some records could not be read or placed',
    'no_opening_balance': 'No opening balance recorded',
    'opening_credits_not_stated': 'Opening credits not stated',
}
STATE_WORDS = {'complete': 'Confirmed complete', 'completeToEarlierDate': 'Confirmed only', 'notConfirmed': 'Not confirmed complete'}

SCRIPT = ("(function(){function r(){var c=document.getElementById('card');if(!c||!window.parent)return;"
          "parent.postMessage({type:'ui-size-change',payload:{height:Math.ceil(c.getBoundingClientRect().height),width:0}},'*')}"
          "addEventListener('load',r);addEventListener('resize',r);if(window.ResizeObserver)new ResizeObserver(r).observe(document.getElementById('card'))})();")
SCRIPT_HASH = "'sha256-" + base64.b64encode(hashlib.sha256(SCRIPT.encode()).digest()).decode() + "'"
CSP = "default-src 'none'; style-src 'unsafe-inline'; script-src " + SCRIPT_HASH + "; base-uri 'none'; form-action 'none'"

CSS = """
:root{color-scheme:light dark;--bg:#fff;--fg:#1d2127;--mute:#5d6672;--line:#d9dde3;--soft:#f3f5f8;--warn-bg:#fff4dc;--warn-fg:#6b4500;--warn-line:#e3b44d;--ok-bg:#e6f3ec;--ok-fg:#14502f;--ok-line:#7fbf9b}
@media (prefers-color-scheme:dark){:root{--bg:#1c2026;--fg:#e8ebef;--mute:#9aa4b0;--line:#3a414b;--soft:#262b33;--warn-bg:#3b2f12;--warn-fg:#f3d58b;--warn-line:#8a6a1f;--ok-bg:#16322340;--ok-fg:#a6dcbc;--ok-line:#2f6b4a}}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
#card{display:flow-root;padding:14px;overflow-wrap:anywhere}
.top{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center;margin:0 0 8px}
.badge{display:inline-block;padding:3px 10px;border-radius:999px;font-weight:700;font-size:13px;border:1px solid}
.badge.warn{background:var(--warn-bg);color:var(--warn-fg);border-color:var(--warn-line)}
.badge.ok{background:var(--ok-bg);color:var(--ok-fg);border-color:var(--ok-line)}
.kind{color:var(--mute);font-size:12px;text-transform:uppercase;letter-spacing:.04em}
h1{font-size:16px;margin:0 0 2px}
.id,.muted{color:var(--mute);font-size:12px}
.fig{margin:10px 0 4px}
.fig .lbl{color:var(--mute);font-size:12px}
.fig .amt{font-size:24px;font-weight:700;line-height:1.2}
.fig .mark{font-size:12px;color:var(--mute);margin-left:6px;font-weight:400}
.box{margin:8px 0;padding:9px 11px;border-radius:8px;border:1px solid var(--line);background:var(--soft)}
.box.warn{background:var(--warn-bg);border-color:var(--warn-line);color:var(--warn-fg)}
.box.ok{background:var(--ok-bg);border-color:var(--ok-line);color:var(--ok-fg)}
.box b{display:block;font-size:12px;margin-bottom:2px;text-transform:uppercase;letter-spacing:.04em}
h2{font-size:12px;margin:12px 0 4px;color:var(--mute);text-transform:uppercase;letter-spacing:.05em}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
@media (max-width:420px){.grid{grid-template-columns:1fr}}
.cell{border:1px solid var(--line);border-radius:8px;padding:8px 10px}
.cell .k{font-weight:700}
ul{margin:4px 0 0;padding-left:18px}
.row{border-top:1px solid var(--line);padding:7px 0}
.row .a{display:flex;flex-wrap:wrap;justify-content:space-between;gap:2px 10px}
.row .ref{font-weight:600}
"""


def e(value):
    """A result's value as escaped text (any type)."""
    return html.escape(str(value), quote=True)


def text(source, *path):
    """The non-empty string (or number, not bool) at path in the result, else None."""
    for key in path:
        if not isinstance(source, dict):
            return None
        source = source.get(key)
    return str(source) if isinstance(source, (str, int, float)) and not isinstance(source, bool) and str(source).strip() else None


def sub(source, key):
    value = source.get(key) if isinstance(source, dict) else None
    return value if isinstance(value, dict) else {}


def date_of(source, key):
    """The page's words for a date (<key>Text), else the date as the records gave it."""
    return text(source, key + 'Text') or text(source, key)


def kind_cell(label, found):
    state = text(found, 'state')
    if state not in STATE_WORDS:
        return '<div class="cell"><div class="k">' + e(label) + '</div>' + UNAVAILABLE + '</div>'
    due = date_of(found, 'completeTo')
    said = STATE_WORDS[state] + (' to ' + due if state == 'complete' and due else ' to ' + due if state == 'completeToEarlierDate' and due else '')
    if state != 'notConfirmed' and not due:
        said += ' (date unavailable)'
    lines = [said]
    count = found.get('recordedCount')
    lines.append((str(count) + ' recorded') if isinstance(count, int) and not isinstance(count, bool) else 'Count ' + UNAVAILABLE.lower())
    latest = date_of(found, 'lastActivity')
    if latest:
        lines.append('Latest record ' + latest)
    bad = found.get('contradicted')
    if isinstance(bad, int) and not isinstance(bad, bool) and bad > 0:
        lines.append('A confirmation no longer holds (' + str(bad) + ')')
    return '<div class="cell"><div class="k">' + e(label) + '</div>' + ''.join('<div>' + e(x) + '</div>' for x in lines) + '</div>'


def completeness_html(view):
    """The completeness block, the same for both tools (it reads only the result's completeness object)."""
    established = view.get('balanceEstablished') is True
    caveat = text(view, 'caveatText')
    out = ['<div class="box ' + ('ok' if established else 'warn') + '"><b>' + ('Confirmed records' if established else 'Unconfirmed') + '</b>'
           + e(caveat or 'No completeness statement was given.') + '</div>',
           '<h2>Record completeness' + (' as of ' + e(date_of(view, 'asOf')) if date_of(view, 'asOf') else '') + '</h2>',
           '<div class="grid">' + kind_cell('Invoice records', sub(view, 'invoices')) + kind_cell('Payment records', sub(view, 'payments')) + '</div>']
    reasons = [r for r in view.get('reasons', []) if isinstance(r, str)] if isinstance(view.get('reasons'), list) else []
    if reasons and not established:
        out.append('<h2>Why unconfirmed</h2><ul>' + ''.join('<li>' + e(REASON_LABELS.get(r, r.replace('_', ' '))) + '</li>' for r in reasons) + '</ul>')
    return ''.join(out)


def row_amount(inv):
    """A row's amount as the records worded it, with its own mark; a row with no recorded amount reads "Not recorded", never 0."""
    said, mark = text(inv, 'amountText'), text(inv, 'mark')
    if not said or said.strip().lower() == NOT_RECORDED.lower() or (mark or '').strip().lower() == NOT_RECORDED.lower():
        return NOT_RECORDED
    return said + (' (' + mark + ')' if mark and mark.lower() not in said.lower() else '')


def none_listed(tool, result):
    """What an empty invoice list says, from the result's own context: it never claims "no invoices" for a list that was cut by a question."""
    if tool == 'customerOverview':
        return 'No open invoices shown.'
    filtered = sub(result, 'filter')
    if filtered:
        return text(filtered, 'noneText') or 'No invoices match this filter.'
    which, count = text(result, 'which'), result.get('invoiceCount')
    if which == 'open':
        return 'No open invoices shown.'
    if which == 'overdue':
        return 'No overdue invoices shown.'
    if which == 'all' and count == 0 and not isinstance(count, bool):
        return 'No invoices are recorded.'
    return 'No invoices shown.'


def invoice_rows_html(invoices, empty):
    if not isinstance(invoices, list):
        return '<div class="muted">Invoices ' + UNAVAILABLE.lower() + '.</div>'
    if not invoices:
        return '<div class="muted">' + e(empty) + '</div>'
    out = []
    for inv in invoices[:MAX_ROWS]:
        due = date_of(inv, 'dueDate')
        days = inv.get('daysOverdue') if isinstance(inv, dict) else None
        late = ' · ' + str(days) + (' day' if days == 1 else ' days') + ' overdue' if isinstance(days, int) and not isinstance(days, bool) and days > 0 else ''
        if late and text(inv, 'overdueText'):   # an extension moved the date: say the count is from the original due date (written by code)
            late = ' · ' + text(inv, 'overdueText')
        out.append('<div class="row"><div class="a"><span class="ref">' + e(text(inv, 'reference') or NOT_RECORDED) + '</span><span>'
                   + e(row_amount(inv)) + '</span></div><div class="muted">' + e(text(inv, 'status') or 'Status ' + UNAVAILABLE.lower())
                   + ' · Due ' + e(due or NOT_RECORDED) + e(late) + '</div></div>')
    if len(invoices) > MAX_ROWS:
        out.append('<div class="muted row">Showing the first ' + str(MAX_ROWS) + ' of ' + str(len(invoices)) + ' invoices.</div>')
    return ''.join(out)


def owed_html(result, view, established):
    """The owed-now figure in one of three states, read from the result: confirmed records, an amount on unconfirmed records (with its mark
    and, for a recorded zero, that it does not show the account is settled), or no figure at all. Nothing is worked out here."""
    owed = sub(result, 'owedNow')
    amount, mark = text(owed, 'amount'), text(owed, 'mark')
    shown = amount or text(owed, 'amountText')
    if not shown or not re.search(r'\d', shown):
        return '<div class="fig"><div class="lbl">Balance not established</div><div class="muted">The records gave no owed-now figure, so none is shown.</div></div>'
    figure = '<div class="amt">' + e(shown) + ('<span class="mark">(' + e(mark) + ')</span>' if mark and amount else '') + '</div>'
    if established:
        due = [date_of(sub(view, k), 'completeTo') for k in ('invoices', 'payments')]
        said = 'Records confirmed complete' + (' to ' + due[0] if due[0] and due[0] == due[1] else '') + '.'
        return '<div class="fig"><div class="lbl">Owed now</div>' + figure + '<div class="muted">' + e(said) + '</div></div>'
    units = owed.get('minorUnits')   # read if the records give it; otherwise the digits of the amount the records wrote
    zero = int(units) == 0 if isinstance(units, (int, str)) and not isinstance(units, bool) and str(units).strip().lstrip('-').isdigit() \
        else set(re.findall(r'\d', shown)) == {'0'}
    return ('<div class="fig"><div class="lbl">Recorded amount</div>' + figure + '<div class="muted">Current account balance not verified.'
            + (' This does not show the account is settled.' if zero else '') + '</div></div>')


def card_html(tool, result, public_url=None):
    """The card for a successful tool result (a dict as the records gave it). public_url: the Lab's recordsPublicUrl, used by the action cards only."""
    if tool in ACTION_CARDS:
        return action_card_html(tool, result, public_url)
    if tool in DECISION_CARDS:
        return decision_card_html(tool, result, public_url)
    if tool not in FINANCIAL_CARDS or not isinstance(result, dict):
        raise ValueError('no card for ' + str(tool))
    view = sub(result, 'completeness')
    established = view.get('balanceEstablished') is True
    overview = tool == 'customerOverview'
    top = ['<div class="top"><span class="badge ' + ('ok' if established else 'warn') + '">' + ('Confirmed records' if established else 'Unconfirmed') + '</span>',
           '<span class="kind">' + ('Customer overview' if overview else 'Invoice list') + '</span></div>',
           '<h1>' + e(text(result, 'name') or 'Customer ' + UNAVAILABLE.lower()) + '</h1>',
           '<div class="id">' + e(text(result, 'customerId') or 'Customer id ' + UNAVAILABLE.lower())
           + (' · As of ' + e(date_of(result, 'asOf')) if date_of(result, 'asOf') else '') + '</div>']
    if overview:
        top.append(owed_html(result, view, established))
    else:
        top.append('<div class="box"><b>Invoice list, not the account balance</b>' + e(text(result, 'scopeText') or 'This list is not the customer\'s complete account balance.') + '</div>')
    body = [completeness_html(view)]
    if overview:
        body.append('<h2>Invoices</h2>' + invoice_rows_html(result.get('invoices'), none_listed(tool, result)))
        if text(result, 'unmatchedText'):
            body.append('<div class="box"><b>Payments not matched</b>' + e(text(result, 'unmatchedText')) + '</div>')
    else:
        count = result.get('invoiceCount')
        body.append('<h2>Invoices listed' + (' (' + str(count) + ')' if isinstance(count, int) and not isinstance(count, bool) else '') + '</h2>'
                    + invoice_rows_html(result.get('invoices'), none_listed(tool, result)))
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="' + e(CSP) + '">'
            '<meta name="viewport" content="width=device-width,initial-scale=1"><title>Nucleon financial card</title><style>' + CSS + '</style></head>'
            '<body><div id="card">' + ''.join(top) + ''.join(body) + '</div><script>' + SCRIPT + '</script></body></html>')


def card_uri(tool, result):
    if tool in DECISION_CARDS:
        return 'ui://nucleon/card/' + tool + '/' + quote(text(result, 'caseId') or text(sub(result, 'customer'), 'id') or 'unknown', safe='')
    if tool in ACTION_CARDS:
        return 'ui://nucleon/card/' + tool + '/' + (action_id(result) or 'unknown')
    return 'ui://nucleon/card/' + quote(tool, safe='') + '/' + quote(text(result, 'customerId') or 'unknown', safe='')


# ---------------------------------------------------------------- the action cards (prepareRequest, actionStatus)

ACTION_ID = re.compile(r'act_[0-9a-f]{16}')   # uid('act') in the records: 'act_' + 8 random bytes in hex
# the local runtime, the isolated Phase B test instance, the local runtime over Tailscale Serve (tailnet and its shares only; retired 30 Oct 2026),
# and the PoV's public origin (Cloudflare Tunnel, behind Cloudflare Access); the same list as ALLOWED_ORIGINS in LibreChat patches 0003-0005
# (client/src/utils/nucleonLinks.ts)
CONFIRM_ORIGINS = ('http://127.0.0.1:8631', 'http://127.0.0.1:18631', 'https://nucleon.tail492813.ts.net:8443', 'https://nucleon.dracooz.top')
CONFIRM_URL = re.compile('(?:' + '|'.join(map(re.escape, CONFIRM_ORIGINS)) + r')/#/actions/act_[0-9a-f]{16}')   # the contract: origin, path /, no query, no userinfo, this hash
CLICK_SCRIPT = ("(function(){var b=document.getElementById('open');if(!b)return;b.addEventListener('click',function(){"
                "var u=b.getAttribute('data-url');if(u&&window.parent)parent.postMessage({type:'link',payload:{url:u}},'*')})})();")
CLICK_HASH = "'sha256-" + base64.b64encode(hashlib.sha256(CLICK_SCRIPT.encode()).digest()).decode() + "'"
CSP_WITH_BUTTON = "default-src 'none'; style-src 'unsafe-inline'; script-src " + SCRIPT_HASH + ' ' + CLICK_HASH + "; base-uri 'none'; form-action 'none'"
ACTION_CSS = """
.banner{margin:0 0 10px;padding:10px 12px;border-radius:8px;border:1px solid;font-weight:700}
.banner.warn{background:var(--warn-bg);color:var(--warn-fg);border-color:var(--warn-line)}
.banner.ok{background:var(--ok-bg);color:var(--ok-fg);border-color:var(--ok-line)}
.banner.plain{background:var(--soft);color:var(--fg);border-color:var(--line)}
.banner small{display:block;font-weight:400;margin-top:2px}
.change{margin:8px 0;font-size:16px;font-weight:600}
.change .days{color:var(--mute);font-size:13px;font-weight:400}
.fact{margin:2px 0}
#open{margin:10px 0 2px;padding:8px 14px;border-radius:8px;border:1px solid var(--line);background:var(--fg);color:var(--bg);font:inherit;font-weight:600;cursor:pointer}
"""
BEFORE_DECISION = ('received', 'analysing', 'needs_information', 'awaiting_owner', 'preparation_failed')   # the records' STATES_BEFORE_DECISION: no decision yet
NOT_SUBMITTED = {'expired': ('EXPIRED — NOT SUBMITTED.', 'It was not confirmed in time. Ask the assistant to prepare it again.'),
                 'superseded': ('REPLACED — NOT SUBMITTED.', 'A newer proposal for this invoice replaced it.'),
                 'cancelled': ('CANCELLED — NOT SUBMITTED.', 'A person cancelled it before it was confirmed.'),
                 'invalidated': ('NOT SUBMITTED — THE RECORDS CHANGED.', 'It can no longer be confirmed. Ask the assistant to prepare it again.')}


def action_id(result):
    """The result's action id (prepareRequest: actionId; actionStatus: id) only if it fits the contract's format, else None."""
    found = text(result, 'actionId') or text(result, 'id') if isinstance(result, dict) else None
    return found if found and ACTION_ID.fullmatch(found) else None


def confirm_url(public_url, result):
    """The Nucleon page of this action, <recordsPublicUrl>/#/actions/<actionId>, only if the whole URL fits the contract exactly (one of the two
    origins, path /, no query or credentials, act_ + 16 lowercase hex); else None, and the card has no button. Never from model text."""
    found = action_id(result)
    if not found or not isinstance(public_url, str):
        return None
    url = public_url.rstrip('/') + '/#/actions/' + found
    return url if CONFIRM_URL.fullmatch(url) else None


def expiry_words(result):
    """The expiry in UTC, from the ISO time the records gave (a formatting of that one value; the card has no time zone of its own)."""
    try:
        at = datetime.fromisoformat(text(result, 'expiresAt')).astimezone(timezone.utc)
        return at.strftime('%a ') + str(at.day) + at.strftime(' %b %Y, %H:%M UTC')
    except (TypeError, ValueError):
        return None


def action_banner(result):
    """(css class, headline, detail) for the action's state, in the records' own words where they gave them. A state the card does not know is
    never read as submitted."""
    status = text(result, 'status')
    outcome, request = sub(result, 'outcome'), sub(result, 'request')
    if status == 'proposed':
        return 'warn', 'PROPOSED — NOT SUBMITTED.', 'A person must confirm it in Nucleon.'
    if status == 'executed':
        rid = text(request, 'id') or text(result, 'requestId')
        label, state = text(request, 'label'), text(request, 'status')
        if rid and (state in BEFORE_DECISION or not state):
            return 'ok', 'SUBMITTED FOR OWNER REVIEW — request ' + rid + '; the owner has not decided.', 'Confirming submitted it for the owner to decide. It did not approve the extension.'
        return 'ok', 'SUBMITTED FOR OWNER REVIEW — request ' + (rid or NOT_RECORDED) + (': ' + label if label else '') + '.', \
            'It was submitted for the owner to decide.'
    if status in NOT_SUBMITTED:
        headline, detail = NOT_SUBMITTED[status]
        return 'plain', headline, text(outcome, 'message') or detail
    return 'plain', 'STATUS UNAVAILABLE — nothing here shows it was submitted.', 'Check the action in Nucleon.'


def action_card_html(tool, result, public_url=None):
    """The card for a successful prepareRequest or actionStatus result. prepareRequest gives a proposal, so it reads "PROPOSED — NOT SUBMITTED"; the
    word "submitted" is claimed only for an actionStatus result whose status is executed. All facts are the result's own preview (the records'
    words): the customer and invoice, the current and requested due dates and the days, the assistant's drafted reason (labelled as that), the
    expiry and, when the records are not confirmed complete, the completeness caveat verbatim. No financial figure is worked out here."""
    if not isinstance(result, dict) or not isinstance(result.get('preview'), dict):
        raise ValueError('no action card for this result')
    preview = result['preview']
    shown = sub(sub(preview, 'fromRecords'), 'invoice')
    change, completeness = sub(preview, 'proposedChange'), sub(preview, 'completeness')
    status = 'proposed' if tool == 'prepareRequest' else text(result, 'status')
    result = {**result, 'status': status}
    tone, headline, detail = action_banner(result)
    live = status == 'proposed'
    url = confirm_url(public_url, result)
    days = change.get('days')
    reason = text(sub(preview, 'draftedByAssistant'), 'reason')
    expires = expiry_words(result)
    out = ['<div class="top"><span class="kind">Payment-extension request</span></div>',
           '<div class="banner ' + tone + '">' + e(headline) + '<small>' + e(detail) + '</small></div>',
           '<h1>' + e(text(sub(sub(preview, 'fromRecords'), 'customer'), 'name') or 'Customer ' + UNAVAILABLE.lower()) + '</h1>',
           '<div class="id">Invoice ' + e(text(shown, 'reference') or NOT_RECORDED) + ' · ' + e(row_amount(shown)) + '</div>',
           '<div class="change">' + e(date_of(change, 'currentDueDate') or NOT_RECORDED) + ' → ' + e(date_of(change, 'requestedDueDate') or NOT_RECORDED)
           + (' <span class="days">(' + str(days) + (' day' if days == 1 else ' days') + ')</span>' if isinstance(days, int) and not isinstance(days, bool) else '') + '</div>']
    if reason:
        out.append('<div class="fact"><span class="muted">Reason drafted by the assistant:</span> ' + e(reason) + '</div>')
    if live and completeness.get('balanceEstablished') is not True:   # fail closed: anything but an explicit true carries the caveat
        out.append('<div class="box warn"><b>Unconfirmed</b>' + e(text(completeness, 'caveatText') or 'The records are not confirmed complete.') + '</div>')
    if live:
        out.append('<div class="box"><b>What confirming does</b>Confirming submits this request to the owner for review. It does not approve the extension.</div>')
        if expires:
            out.append('<div class="muted">Expires ' + e(expires) + '</div>')
    if url:
        out.append('<button type="button" id="open" data-url="' + e(url) + '">' + ('Review and confirm in Nucleon' if live else 'View in Nucleon') + '</button>')
    elif live:
        out.append('<div class="muted">Open this action in Nucleon to review and confirm it' + (': ' + e(action_id(result)) if action_id(result) else '') + '.</div>')
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="' + e(CSP_WITH_BUTTON if url else CSP) + '">'
            '<meta name="viewport" content="width=device-width,initial-scale=1"><title>Nucleon action card</title><style>' + CSS + ACTION_CSS + '</style></head>'
            '<body><div id="card">' + ''.join(out) + '</div><script>' + SCRIPT + '</script>' + ('<script>' + CLICK_SCRIPT + '</script>' if url else '') + '</body></html>')


# ---------------------------------------------------------------- the decision card (assessDecision, resolveDecision, decisionStatus)

DECISION_CSS = """
.status{margin:4px 0 8px;color:var(--fg)}
.why{margin:0 0 8px;color:var(--mute);font-size:13px}
.dates{margin:6px 0}
.dates .r{display:flex;align-items:baseline;gap:8px;padding:3px 0;border-top:1px solid var(--line)}
.dates .r:first-child{border-top:0}
.dates .dot{flex:none;width:10px;height:10px;border-radius:3px;align-self:center}
.dates .l{color:var(--mute);min-width:0;flex:1 1 9em}
.dates .v{font-weight:600;text-align:right;flex:0 1 auto}
.tl{position:relative;height:98px;margin:10px 2px 2px}
.tl .axis{position:absolute;left:0;right:0;top:48px;height:2px;background:var(--line)}
.tl .span{position:absolute;top:44px;height:10px;border-radius:5px}
.tl .span.ext.pending{background:#d69e2e}.tl .span.ext.approved{background:var(--ok-line)}.tl .span.ext.declined{background:none;border:2px dashed var(--mute);height:6px;top:46px}
.tl .span.late{background:#c53030;top:56px;height:5px;border-radius:3px}
.tl .pin{position:absolute;top:42px;width:12px;height:14px;margin-left:-6px;border-radius:3px;border:1px solid var(--bg)}
.tl .mark{position:absolute;transform:translateX(-50%);display:flex;flex-direction:column;align-items:center;font-size:12px;line-height:1.25;white-space:nowrap;color:var(--mute)}
.tl .mark b{font-size:13px;color:var(--fg)}
.tl .mark.above{top:4px}.tl .mark.below{top:64px}
.tl .mark.edge-l{transform:none;align-items:flex-start}.tl .mark.edge-r{transform:translateX(-100%);align-items:flex-end}
.m0{background:#5d6672}.m1{background:#2b6cb0}.m2{background:#b7791f}.m3{background:#2f855a}
.facts{margin:6px 0}
.facts div{margin:2px 0}
.dim{margin:6px 0;padding:8px 10px;border:1px solid var(--line);border-radius:8px}
.dim b{display:block;font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--mute)}
.dim ul{margin:3px 0 0}
.comp{margin:6px 0;padding:7px 10px;border:1px dashed var(--line);border-radius:8px;font-size:13px}
.comp .note{color:var(--mute);font-size:12px}
.sent{margin:10px 0 2px;color:var(--mute);font-size:12px}
"""
SENT_TEXT = 'Nucleon sent nothing to the customer. Staff informs the customer.'
ANALOGY = "Another customer's reviewed case — analogy, not this customer's history"
MAX_COMPARABLES = 3
WOULD = {'autonomous_approve': 'WOULD BE APPROVED UNDER OWNER POLICY v{n} — PREVIEW, NOT DECIDED', 'request_evidence': 'WOULD NEED INFORMATION FROM STAFF — PREVIEW, NOT DECIDED',
         'owner_review': 'WOULD GO TO THE OWNER FOR REVIEW — PREVIEW, NOT DECIDED', 'policy_hold': 'WOULD BE PUT ON HOLD BY POLICY — PREVIEW, NOT DECIDED'}


OVERRIDE_EFFECTS = ("This reverses Nucleon's internal decision only. Nucleon sent nothing to the customer; if Staff already told the customer or acted on it outside Nucleon, "
                    "that is not undone — Staff must follow up.")


def policy_version(result):
    n = sub(result, 'authority').get('version')
    return str(n) if isinstance(n, int) and not isinstance(n, bool) else None


def decision_badge(result):
    """(css class, badge text, authority line) from the backend's own status, handling and decision, nothing else. An assessment is a preview and never
    claims a decision; a status the card does not know claims nothing."""
    status, handling, n = text(result, 'status'), text(result, 'handling'), policy_version(result)
    decision = sub(result, 'decision')
    by, outcome = text(decision, 'by'), text(decision, 'outcome')
    v = ' v' + n if n else ''
    only_if = 'Approved under Owner policy' + v + ' only if the information confirms it; otherwise the Owner decides'
    if status == 'assessed' and handling in WOULD:
        return ('ok' if handling == 'autonomous_approve' else 'warn', WOULD[handling].format(n=n or '?'),
                'Would be decided under Owner policy' + v if handling == 'autonomous_approve' else only_if if handling == 'request_evidence' else 'The Owner decides')
    if status == 'decided' and decision.get('overridden') is True:
        return 'plain', 'APPROVAL OVERRIDDEN BY THE OWNER', 'The Owner decided'
    if status == 'decided' and by == 'agent' and outcome == 'approve':
        return 'ok', 'APPROVED UNDER OWNER POLICY' + v + ' — DECIDED BY AGENT', 'Decided under Owner policy' + v
    if status == 'decided' and by == 'agent' and outcome == 'decline':   # 12 Nov 2026: the owners' session showed this as "status unavailable"
        return 'warn', "DECLINED UNDER THE OWNER'S DECLINE RULES" + v + ' — DECIDED BY AGENT', 'Declined under Owner policy' + v + '; the Owner can reverse it'
    if status == 'decided' and by in ('owner', 'owner_exception') and outcome in ('approve', 'decline'):
        return 'plain', 'DECIDED BY THE OWNER — ' + ('APPROVED' if outcome == 'approve' else 'DECLINED'), 'The Owner decided'
    if status == 'gathering_evidence':
        return 'warn', 'INFORMATION NEEDED FROM STAFF', only_if
    if status == 'awaiting_owner':
        return 'warn', 'WITH THE OWNER FOR REVIEW', 'The Owner decides'
    if status == 'on_hold':
        return 'warn', 'ON HOLD BY POLICY', 'The Owner decides'
    if status == 'closed':
        return 'plain', 'CLOSED — NOTHING APPROVED', 'The Owner decides'
    return 'plain', 'STATUS UNAVAILABLE — nothing here shows a decision', 'The Owner decides'


def date_rows(facts):
    """The key dates, in date order: [(label, date text, iso)]. The current due date is listed only when it differs from the original. Labels and
    dates are the backend's; the order is only a sort on its ISO dates."""
    rows = [('Original due date', 'originalDueDate'), ('Current due date', 'currentDueDate'), ('As-of date', 'asOfDate'), ('Requested due date', 'requestedDueDate')]
    out = []
    for label, key in rows:
        iso = text(facts, key)
        if not iso or key == 'currentDueDate' and iso == text(facts, 'originalDueDate'):
            continue
        out.append((label, date_of(facts, key), iso))
    try:
        return sorted(out, key=lambda r: datetime.strptime(r[2], '%Y-%m-%d'))
    except ValueError:
        return out


SHORT_LABELS = {'Original due date': 'Original due', 'Current due date': 'Current due', 'As-of date': 'As of', 'Requested due date': 'Requested'}


def short_date(iso):
    """'2026-10-18' -> '18 Oct' (the year is in the rows above)."""
    try:
        d = datetime.strptime(iso, '%Y-%m-%d')
    except ValueError:
        return iso
    return str(d.day) + ' ' + d.strftime('%b')


def date_bar(rows, state='pending'):
    """Rows of dates in chronological order, and a timeline: an axis with a pin per date, the dates written beside their pins (odd ones below the axis, so
    neighbours never overlap; the first and last anchored to the edges), the extension span from the due date (current, else original) to the requested due
    date filled by state (orange while nothing is decided, green once approved, hollow once declined or overridden), and the overdue stretch from the due
    date to the as-of date marked red beneath. Pin colours match the dots of the rows. (5 Nov 2026: the dates went back onto the bar, as the earlier
    Nucleon timeline had them; the markers-only bar read as a slider. The green-only span read as approved before anything was.)"""
    if not rows:
        return ''
    try:
        days = [datetime.strptime(r[2], '%Y-%m-%d').toordinal() for r in rows]
    except ValueError:
        days = None
    lines = ''.join('<div class="r"><span class="dot m' + str(i) + '"></span><span class="l">' + e(label) + '</span><span class="v">' + e(said or NOT_RECORDED) + '</span></div>'
                    for i, (label, said, _) in enumerate(rows))
    if not days or len(rows) < 2:
        return '<div class="dates">' + lines + '</div>'
    low, span = min(days), max(days) - min(days)
    pct = lambda d: round(100 * (d - low) / span) if span else 50
    by_label = {label: d for (label, _, _), d in zip(rows, days)}
    due = by_label.get('Current due date', by_label.get('Original due date'))
    spans = ''
    if due is not None and by_label.get('Requested due date') is not None and by_label['Requested due date'] > due:
        spans += '<i class="span ext ' + e(state) + '" style="left:' + str(pct(due)) + '%;width:' + str(pct(by_label['Requested due date']) - pct(due)) + '%"></i>'
    if due is not None and by_label.get('As-of date') is not None and by_label['As-of date'] > due:
        spans += '<i class="span late" style="left:' + str(pct(due)) + '%;width:' + str(pct(by_label['As-of date']) - pct(due)) + '%"></i>'
    pins = ''.join('<i class="pin m' + str(i) + '" style="left:' + str(pct(d)) + '%"></i>' for i, d in enumerate(days))
    marks = ''
    for i, ((label, _, iso), d) in enumerate(zip(rows, days)):
        x = pct(d)
        cls = 'mark ' + ('below' if i % 2 else 'above') + (' edge-l' if x <= 8 else ' edge-r' if x >= 92 else '')
        marks += '<div class="' + cls + '" style="left:' + str(x) + '%"><b>' + e(short_date(iso)) + '</b><span>' + e(SHORT_LABELS.get(label, label)) + '</span></div>'
    return '<div class="dates">' + lines + '</div><div class="tl" aria-hidden="true"><div class="axis"></div>' + spans + pins + marks + '</div>'


def money_of(source, key):
    return text(sub(source, key), 'text')


def span_state(result):
    """'approved' once a decision approved it and stands, 'declined' once declined, overridden or closed, else 'pending' (an assessment, a wait on the
    Owner or on Staff, a hold): what the extension span is filled with."""
    status, decision = text(result, 'status'), sub(result, 'decision')
    if status == 'decided' and decision.get('overridden') is True:
        return 'declined'
    if status == 'decided' and text(decision, 'outcome') == 'approve':
        return 'approved'
    if status == 'closed' or status == 'decided' and text(decision, 'outcome') == 'decline':
        return 'declined'
    return 'pending'


def key_facts_html(facts, result):
    kind = text(facts, 'kind')
    if kind == 'extension':
        out = [date_bar(date_rows(facts), span_state(result))]
        days, late = facts.get('extensionDays'), facts.get('daysOverdueAsOf')
        lines = []
        if isinstance(days, int) and not isinstance(days, bool):
            lines.append('+' + str(days) + (' day' if days == 1 else ' days') + ' past the current due date')
        if isinstance(late, int) and not isinstance(late, bool):
            lines.append(str(late) + (' day' if late == 1 else ' days') + ' overdue as of ' + (date_of(facts, 'asOfDate') or NOT_RECORDED))
        else:
            lines.append('Days overdue: ' + (text(facts, 'daysOverdueNote') or UNAVAILABLE.lower()))
        owed = text(facts, 'amountText') or (money_of(facts, 'amountOwed') and money_of(facts, 'amountOwed') + (' (' + text(facts, 'amountMark') + ')' if text(facts, 'amountMark') else ''))
        lines.append('Amount owed: ' + (owed or NOT_RECORDED))
        out.append('<div class="facts">' + ''.join('<div>' + e(x) + '</div>' for x in lines) + '</div>')
        return ''.join(out)
    if kind == 'trial_credit':
        deposit = money_of(facts, 'verifiedDeposit')
        sources = facts.get('depositSources')
        how = []
        for x in sources if isinstance(sources, list) else []:   # the backend's own words, with each source's level: a recorded payment, or Staff-checked / reported (not a recorded payment)
            if isinstance(x, dict) and text(x, 'text'):
                how.append(text(x, 'text'))
        due = date_of(facts, 'dueDateIfApproved')
        lines = ['Order amount: ' + (money_of(facts, 'orderAmount') or NOT_RECORDED),
                 'Verified deposit: ' + (deposit or NOT_RECORDED) + (' — none verified' if deposit and not how else ''),
                 *['Deposit source: ' + x for x in how],
                 'Deposit share: ' + (text(facts, 'depositShare') or NOT_RECORDED), 'Exposure (order less verified deposit): ' + (money_of(facts, 'exposure') or NOT_RECORDED),
                 'Terms: ' + (str(facts['termsDays']) + ' days' if isinstance(facts.get('termsDays'), int) else NOT_RECORDED),
                 'Due date if approved: ' + (due or NOT_RECORDED) + (' (as-of date + terms)' if due else '')]
        return '<div class="facts">' + ''.join('<div>' + e(x) + '</div>' for x in lines) + '</div>'
    return '<div class="muted">Key facts ' + UNAVAILABLE.lower() + '.</div>'


def listed(items, key_a, key_b, limit=8):
    if not isinstance(items, list) or not items:
        return ''
    return '<ul>' + ''.join('<li>' + e((text(i, key_a) or '') + ((': ' + text(i, key_b)) if text(i, key_b) else '')) + '</li>' for i in items[:limit] if isinstance(i, dict)) + '</ul>'


def dimensions_html(result):
    evidence, risk, rel = sub(result, 'evidence'), sub(result, 'risk'), sub(result, 'reliability')
    evaluation = sub(rel, 'evaluation')
    items = [i for i in evidence.get('items', []) if isinstance(i, dict) and i.get('status') != 'not_needed'] if isinstance(evidence.get('items'), list) else []
    checks = [c for c in risk.get('checks', []) if isinstance(c, dict) and c.get('status') != 'na'] if isinstance(risk.get('checks'), list) else []
    dataset = ('fictional evaluation set (simulation)' if text(evaluation, 'dataset') == 'fictional_evaluation' else text(evaluation, 'dataset') or 'evaluation set unavailable')
    n, total = evaluation.get('wouldApprove'), evaluation.get('reviewed')
    sample = ('Sample: the policy would approve ' + str(n) + ' of ' + str(total) + ' reviewed cases; the Owner approved ' + str(evaluation.get('ownerApproved')) + ' of them.'
              if all(isinstance(x, int) and not isinstance(x, bool) for x in (n, total)) else 'Sample size ' + UNAVAILABLE.lower() + '.')
    return ('<h2>Evidence, risk and track record</h2>'
            '<div class="dim"><b>Evidence — ' + e((text(evidence, 'status') or UNAVAILABLE).replace('_', ' ')) + '</b>'
            + '<ul>' + ''.join('<li>' + e(text(i, 'label') + ' — ' + (text(i, 'status') or '').replace('_', ' ') + (': ' + text(i, 'detail') if text(i, 'detail') else '')) + '</li>' for i in items[:8] if text(i, 'label')) + '</ul></div>'
            '<div class="dim"><b>Business risk — ' + e((text(risk, 'status') or UNAVAILABLE).replace('_', ' ')) + '</b>'
            + '<ul>' + ''.join('<li>' + e(text(c, 'sentence') or text(c, 'label') or '') + '</li>' for c in checks[:8]) + '</ul></div>'
            '<div class="dim"><b>Track record — ' + e((text(rel, 'status') or UNAVAILABLE).replace('_', ' ')) + '</b>'
            + e('Dataset: ' + dataset + '. ' + sample) + '</div>')


def comparables_html(result):
    comps = result.get('comparables') if isinstance(result.get('comparables'), list) else []
    out = []
    for c in comps[:MAX_COMPARABLES]:
        if not isinstance(c, dict):
            continue
        same = c.get('sameCustomer') is True
        label = "This customer's earlier case" if same else ANALOGY + (' — fictional' if c.get('fictional') is True else '')
        bits = [x for x in (text(c, 'summary'), 'Owner ' + text(c, 'ownerDecision') + 'd' if text(c, 'ownerDecision') in ('approve', 'decline') else None,
                            'outcome ' + text(c, 'outcome').replace('_', ' ') if text(c, 'outcome') else None) if x]
        out.append('<div class="comp"><div class="note">' + e(label) + '</div>' + e(' · '.join(bits)) + '</div>')
    return ('<h2>Comparable cases</h2>' + ''.join(out)) if out else ''


def decision_card_html(tool, result, public_url=None):
    """The card for a successful assessDecision, resolveDecision or decisionStatus result (the backend's case view). The badge and the authority line come from
    its status, handling and decision only; Key Facts, the three dimensions, up to three comparables (labelled as analogies), what was not communicated, and
    one button only for a case that is gathering evidence with a live evidence action."""
    if not isinstance(result, dict) or not isinstance(result.get('keyFacts'), dict):
        raise ValueError('no decision card for this result')
    tone, badge, authority = decision_badge(result)
    facts = result['keyFacts']
    warnings = [w for w in result.get('warnings', []) if isinstance(w, str)] if isinstance(result.get('warnings'), list) else []
    customer = text(sub(result, 'customer'), 'name')
    reasons = [r for r in result.get('reasons', []) if isinstance(r, str)] if isinstance(result.get('reasons'), list) else []
    needs = [n for n in result.get('needs', []) if isinstance(n, str)] if isinstance(result.get('needs'), list) else []
    url = None
    if text(result, 'status') == 'gathering_evidence' and text(result, 'handling') == 'request_evidence' and result.get('stored') is not False and text(result, 'evidenceLink'):
        url = confirm_url(public_url, {'actionId': text(result, 'actionId')})
    out = ['<div class="top"><span class="badge ' + tone + '">' + e(badge) + '</span><span class="kind">' + ('Payment-extension request' if text(facts, 'kind') == 'extension' else 'Trial credit') + '</span></div>',
           '<h1>' + e(customer or 'Customer ' + UNAVAILABLE.lower()) + '</h1>',
           '<div class="status">' + e(text(result, 'statusText') or '') + '</div>',
           *(['<div class="why">' + e(text(sub(result, 'recommendation'), 'text')) + '</div>'] if text(sub(result, 'recommendation'), 'text') else []),
           *(['<div class="why">Why: ' + e(reasons[0]) + '</div>'] if reasons and text(result, 'status') != 'decided' else []),
           '<h2>Key facts</h2>' + key_facts_html(facts, result)]
    if warnings:
        out.append('<div class="box warn"><b>Warnings</b><ul>' + ''.join('<li>' + e(w) + '</li>' for w in warnings[:10]) + '</ul></div>')
    if needs and text(result, 'status') == 'gathering_evidence':
        out.append('<div class="box"><b>Staff are asked to confirm</b>' + e(', '.join(needs)) + '</div>')
    if sub(result, 'decision').get('overridden') is True:   # what the Owner's override does not undo: the backend's words, else the base sentence (never silent)
        out.append('<div class="box warn" id="external-effects"><b>What this override does not undo</b>' + e(text(result, 'externalEffects') or OVERRIDE_EFFECTS) + '</div>')
    out += [dimensions_html(result), comparables_html(result), '<div class="box"><b>Authority</b>' + e(authority) + '</div>']
    if url:
        out.append('<button type="button" id="open" data-url="' + e(url) + '">Provide information in Nucleon</button>')
    out.append('<div class="sent">' + e(SENT_TEXT) + '</div>')
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="' + e(CSP_WITH_BUTTON if url else CSP) + '">'
            '<meta name="viewport" content="width=device-width,initial-scale=1"><title>Nucleon decision card</title><style>' + CSS + ACTION_CSS + DECISION_CSS + '</style></head>'
            '<body><div id="card">' + ''.join(out) + '</div><script>' + SCRIPT + '</script>' + ('<script>' + CLICK_SCRIPT + '</script>' if url else '') + '</body></html>')
