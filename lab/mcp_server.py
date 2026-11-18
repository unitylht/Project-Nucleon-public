"""The business operations as an MCP server (streamable HTTP, stateless), mounted by the Lab at mcp/. The bearer token gives the
role (config mcpTokens); each call goes to the records surface with a records session for that role, which the Lab signs in to
at first use with the records' SERVICE codes (not the access codes people use) and again when the records answer 401. The records make such a
session a service's, which cannot confirm or cancel an action; the Lab checks that and fails closed. The codes rotate on every records start unless
fixed, so they are read from the records log (recordsLog) when it has them, else from recordsCodes; they are never logged. Exposed: the
role's registry less openRequest (an agent's words never become a case's intake) and less the act kinds other than ACTS; prepare
kinds only prepare, and the person confirms on the records page. customerOverview and invoices also carry a read-only card (lab/card.py) as an
MCP-UI resource after their JSON (assessDecision, resolveDecision and decisionStatus carry one decision card); prepareRequest and actionStatus carry an action card, whose one button opens the Nucleon page of the action
(recordsPublicUrl + the actionId of the result) and writes nothing. Operation identity: a client that sends the _meta key nucleon.lab/idempotencyKey names its operation, and the
records run it once per key (bound to the bearer token and role that sent it); without the key each call is a new operation, and identical
arguments are never taken for a retry. A non-read result says which (_meta nucleon.lab/operation: keySource, replayed).
What the MODEL reads is the first (text) item: when the records' result holds a `forModel` (the compact result of the decision tools and the read tools of
slice S3), that text is the JSON of `forModel` (plus `hint` when the result has one); the full result goes to the card only, never to the model. A refused
call is {error, message} plus its `hint`. Every other tool's text is unchanged. With the config key `timingLog` the Lab appends one JSON line per call (lab/mcp_server.py, TimingLog)."""
import hashlib
import json
import logging
import re
import secrets
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import mcp_types as types
from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
from mcp.shared.exceptions import MCPError
from starlette.datastructures import Headers
from starlette.responses import JSONResponse

from .card import CARD_TOOLS, card_html, card_uri

LAB_VERSION = 'lab-v0.18'
CARD_ONLY = ('flaggedRows', 'customers')   # file rows and names: in the card's payload, never in what a client is given

IDEMPOTENCY_META, OPERATION_META = 'nucleon.lab/idempotencyKey', 'nucleon.lab/operation'   # the client's key in a call's _meta; what a non-read result says of its operation
KEY_FORM = re.compile(r'[A-Za-z0-9._:-]{8,128}')
ACTS = {'withdrawPreparation', 'requestSuggestion', 'resolveDecision'}   # the act kinds an external agent may run
MESSAGE = {'type': 'string', 'description': "the person's own words, as they wrote them (prepareDecision and prepareCustomer keep "
                                            "only what these give; without them prepareDecision answers that something is missing)"}
log = logging.getLogger(__name__)
LOOPBACK = ['127.0.0.1:*', 'localhost:*', '[::1]:*']

# Advisory hints for the client (the MCP tool annotations); the records stay the authority and gate every call by role. Audited against
# the implementation (DeskTools), not the names, by what a call stores (docs/DECISIONS.md, E025 addendum):
#   pure read: stores nothing at all -> READ_ONLY.
#   assessRequest: a read in kind, but it keeps the latest assessment on a case not yet decided (version + 1), so it is not read-only.
#   prepare/draft: prepareCustomer, prepareHoldingMessage, interpretStatement store nothing of the business (a once-per-key record of the call only).
#   prepare that is kept: prepareDecision (the preparation on the case), proposeImport (the proposal); nothing is decided or imported.
#   commit: withdrawPreparation ends a preparation; requestSuggestion keeps a new suggestion version.
#   assessDecision and decisionStatus (Adaptive Decision Authority) store nothing (audited: App.delegation_assess and case_view only read; test_delegation counts the
#   tables before and after) -> READ_ONLY. resolveDecision commits a decision case (and, within the Owner's policy, a decision): not read-only; it is not
#   claimed non-destructive either, since it can make an approval take effect inside Nucleon.
# Fail closed: a tool is read-only only when named here, so a new read-kind tool is not claimed read-only until it has been checked.
READ_ONLY = frozenset({'findCustomers', 'customerOverview', 'invoices', 'ownerContext', 'cases', 'caseDetails', 'whereIs', 'compareExtension',
                       'workQueue', 'listRequests', 'actionStatus', 'assessDecision', 'decisionStatus',
                       'whatIsNeeded', 'comparableCases', 'customerStatus', 'policyBacktest', 'impactSummary', 'doctor'})
NON_DESTRUCTIVE = frozenset({'assessRequest', 'prepareCustomer', 'prepareHoldingMessage', 'interpretStatement', 'prepareDecision', 'proposeImport',
                             'requestSuggestion'})   # they add or replace a derived version and remove nothing; withdrawPreparation is left at the client's default


def model_text(result, ok):
    """The text item the model reads for a records result. A success holding a `forModel` object is that object (and the result's `hint`, if it has one) as
    JSON: the compact result written by code, a few hundred characters, instead of the 8-10k characters the card needs. Anything else is the result as it
    is, so no other tool changes; a refusal is {error, message} and the records' structured `hint` (the question to ask Staff), which carries no private data."""
    if ok and isinstance(result, dict) and isinstance(result.get('forModel'), dict):
        compact = dict(result['forModel'])
        if result.get('hint'):
            compact['hint'] = result['hint']
        return json.dumps(compact, ensure_ascii=False)
    return json.dumps(result, ensure_ascii=False)


class TimingLog:
    """One JSON line per tool call, appended to the file named by the config key `timingLog` (a relative path is under the Lab's working directory, e.g.
    logs/tool-timing.jsonl); off when the key is unset. A line holds what the processing-time metric needs and nothing private: tool, role, caseId (if the
    result has one), start (UTC), duration in ms, the size in characters of the full result and of the model's compact result (null if none), and ok. No
    arguments, no token, no text. A failure to write is logged once per call and never fails the call."""

    def __init__(self, path):
        self.path, self.lock = path, threading.Lock()

    def write(self, tool, role, started, started_at, result, ok, forModel):
        row = {'tool': tool, 'role': role, 'caseId': result.get('caseId') if isinstance(result, dict) and isinstance(result.get('caseId'), str) else None,
               'start': started_at, 'durationMs': round((time.monotonic() - started) * 1000, 1), 'ok': ok,
               'resultChars': len(json.dumps(result, ensure_ascii=False)), 'forModelChars': None if forModel is None else len(forModel)}
        try:
            path = Path(self.path).expanduser()
            with self.lock:
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, 'a', encoding='utf-8') as out:
                    out.write(json.dumps(row, ensure_ascii=False) + '\n')
        except OSError:
            log.exception('the tool timing line could not be written')


def codes_from_log(text):
    """{owner, staff: code}: the SERVICE codes (the lines 'STAFF service code: ...' / 'OWNER service code: ...') printed after the records log's last
    ' URL: http' line, its latest start. The access codes on the lines beside them are people's and are never read here: a session made with one is
    a person's, and the Lab must never operate as one (sign_in checks)."""
    codes = {}
    for line in text.splitlines():
        if ' URL: http' in line:
            codes = {}
        elif m := re.fullmatch(r'(STAFF|OWNER) service code: (\S+)', line):
            codes[m[1].lower()] = m[2]
    return codes


def annotations_for(name):
    """The tool's annotations: readOnlyHint true only for READ_ONLY; destructiveHint false only where accurate; every tool is closed-world
    (it works on the records of this workspace only)."""
    if name in READ_ONLY:
        return types.ToolAnnotations(read_only_hint=True, open_world_hint=False)
    return types.ToolAnnotations(read_only_hint=False, open_world_hint=False, **({'destructive_hint': False} if name in NON_DESTRUCTIVE else {}))


def exposed(registry):
    """An allow-list, fail closed: read and prepare kinds, and the acts in ACTS; never openRequest, and nothing of another kind."""
    return [t for t in registry.get('tools', []) if t['name'] != 'openRequest' and (t.get('kind') in ('read', 'prepare') or t['name'] in ACTS)]


class LabMCP:
    """The ASGI app at mcp/: 401 without a known bearer token, else the SDK's streamable-HTTP transport. Its manager runs in the
    Lab's lifespan."""

    def __init__(self, config, records):
        self.config, self.records, self.cookies = config, records, {}   # cookies: role -> the records Cookie header
        self.timing = TimingLog(config['timingLog']) if config.get('timingLog') else None
        origins = config.get('publicOrigins', [])
        self.server = Server('nucleon-lab', version=LAB_VERSION, on_list_tools=self.list_tools, on_call_tool=self.call_tool)
        self.manager = StreamableHTTPSessionManager(self.server, stateless=True, security_settings=TransportSecuritySettings(
            allowed_hosts=LOOPBACK + [urlsplit(o).netloc for o in origins],   # behind the proxy the Host is the public one
            allowed_origins=['http://' + h for h in LOOPBACK] + origins))

    def role_of(self, headers):
        scheme, _, token = headers.get('authorization', '').partition(' ')
        token = token.strip().encode()
        return next((role for t, role in self.config.get('mcpTokens', {}).items()
                     if scheme.lower() == 'bearer' and secrets.compare_digest(t.encode(), token)), None)

    @staticmethod
    def operation_key(headers, role, client_key):
        """The records' Idempotency-Key for one call: from the client's key it is the same on every retry and bound to the token and role that sent
        it (another client's key, or the same text from another token, is another operation; the token is only hashed, never stored or logged);
        without one, a new key per call."""
        if client_key is None:
            return 'mcp-' + uuid.uuid4().hex
        token = headers.get('authorization', '').partition(' ')[2].strip()
        return 'mcpc-' + hashlib.sha256(json.dumps([hashlib.sha256(token.encode()).hexdigest(), role, client_key]).encode()).hexdigest()[:40]

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or self.role_of(Headers(scope=scope)) is None:   # fail closed (no websocket here)
            refused = JSONResponse({'error': 'UNAUTHORIZED', 'message': 'Send Authorization: Bearer <token>.'}, 401, {'WWW-Authenticate': 'Bearer'})
            return await refused(scope, receive, send)
        await self.manager.handle_request(scope, receive, send)

    def codes(self):
        try:
            logged = codes_from_log(Path(self.config['recordsLog']).read_text()) if self.config.get('recordsLog') else {}
        except OSError:
            logged = {}
        return {**self.config.get('recordsCodes', {}), **logged}

    async def sign_in(self, role):
        """A records session for this role, with the SERVICE code of the records' latest start (the log's, else config recordsCodes). It sends no
        channel: the records decide from the code that the session is a service's (channel 'service'), which they never let confirm or cancel an
        action. FAIL CLOSED: after signing in the session is read back (GET api/session) and, unless it says channel 'service' for this role, it is
        ended and the Lab raises: the Lab never operates on a person's session, whatever code it was given (a person's access code in recordsCodes,
        a records instance that predates service codes). The cookie is returned only after that check."""
        code = self.codes().get(role)
        if code:
            async with self.records.client() as c:
                r = await c.post('/api/demo/login', json={'accessCode': code, 'role': role})
                if r.status_code == 200:
                    cookie = '; '.join(h.split(';', 1)[0] for h in r.headers.get_list('set-cookie'))
                    seen = await c.get('/api/session', headers={'Cookie': cookie})
                    who = seen.json() if seen.status_code == 200 else {}
                    if who.get('authenticated') is True and who.get('channel') == 'service' and who.get('role') == role:
                        return cookie
                    await c.post('/api/demo/logout', headers={'Cookie': cookie}, json={})   # a session that is not a service's is not kept
                    raise MCPError(types.INTERNAL_ERROR, 'The Lab refuses to use the records session for ' + role + ': it is not a service session. '
                                   'Give the Lab the records\' service code (the "service code" lines of their log), never a person\'s access code.')
        raise MCPError(types.INTERNAL_ERROR, 'The Lab could not sign in to the records as ' + role + '; its service codes may be out of date.')

    async def session(self, role, again=False):
        if again or role not in self.cookies:
            self.cookies[role] = await self.sign_in(role)
        return self.cookies[role]

    async def offered(self, role):
        """The role's exposed tools by name. Every list and call starts here, so a session the records ended is renewed here."""
        status, body = await self.records.tools(await self.session(role))
        if status == 401:
            status, body = await self.records.tools(await self.session(role, again=True))
        if status != 200:
            raise MCPError(types.INTERNAL_ERROR, 'The records did not list the tools (HTTP ' + str(status) + ').')
        return {t['name']: t for t in exposed(body)}

    async def list_tools(self, ctx, params):
        return types.ListToolsResult(tools=[
            types.Tool(name=t['name'], description=t['description'],
                       input_schema={**t['parameters'], 'properties': {**t['parameters'].get('properties', {}), 'message': MESSAGE}},
                       annotations=annotations_for(t['name']))
            for t in (await self.offered(self.role_of(ctx.request.headers))).values()])

    async def call_tool(self, ctx, params):
        """The records result as JSON text, or {error, message} with isError when the records refuse."""
        started, started_at = time.monotonic(), datetime.now(timezone.utc).isoformat(timespec='milliseconds')
        role, args = self.role_of(ctx.request.headers), dict(params.arguments or {})
        client_key = (params.meta or {}).get(IDEMPOTENCY_META)   # the client's name for this operation, if it sends one (model-visible arguments never name it)
        if client_key is not None and not (isinstance(client_key, str) and KEY_FORM.fullmatch(client_key)):
            raise MCPError(types.INVALID_PARAMS, '_meta ' + IDEMPOTENCY_META + ' must be 8 to 128 characters: letters, digits, . _ : -')
        if params.name not in await self.offered(role):
            raise MCPError(types.INVALID_PARAMS, 'Unknown tool: ' + params.name)
        key = self.operation_key(ctx.request.headers, role, client_key)
        body = await self.records.call(await self.session(role), params.name, args, args.pop('message', ''), key=key)
        ok = body.get('ok') is True
        result = body.get('result') if ok else {'error': body.get('error'), 'message': body.get('message'), **({'hint': body['hint']} if body.get('hint') else {})}
        if ok and params.name == 'proposeImport':   # the card's payload holds file rows and names: an agent gets the proposal without it
            result = {k: v for k, v in result.items() if k not in CARD_ONLY}
        text = model_text(result, ok)   # what the model reads: the compact forModel when the result has one, else the records' result as it is
        content = [types.TextContent(text=text)]
        if ok and params.name in CARD_TOOLS:   # after it, a read-only card of the FULL result for clients that show one (MCP-UI); never in its place
            try:
                content.append(types.EmbeddedResource(resource=types.TextResourceContents(
                    uri=card_uri(params.name, result), mime_type='text/html', text=card_html(params.name, result, self.config.get('recordsPublicUrl')))))
            except Exception:   # the card is a view: if it cannot be made, the result goes out without it
                log.exception('the %s card could not be rendered; the result is sent without it', params.name)
        if self.timing:
            self.timing.write(params.name, role, started, started_at, result, ok, text if ok and isinstance(result, dict) and isinstance(result.get('forModel'), dict) else None)
        operation = None if params.name in READ_ONLY else {OPERATION_META: {'keySource': 'server' if client_key is None else 'client', 'replayed': body.get('replayed') is True}}
        return types.CallToolResult(content=content, is_error=not ok, meta=operation)
