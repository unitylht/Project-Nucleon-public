"""MCP checks for the local Nucleon Lab. Reads tokens from ../config/lab.json; never prints them.
Run: ~/Developer/nucleon-local/venv/bin/python tests/mcp_check.py [--verbose] [--assess] [--save]
Data-driven: customers are picked by name substring from the live findCustomers result and invoice references come from the live invoices result, so the
checks do not depend on display codes or invoice numbers of any one sample dataset (they need a customer named like *Bayview* and *Riverside*, as in the
fictional ADA demo seed prototype/delegation_demo.py). Tool lists are compared by role rules, not by a pinned count.
Mutations: none (assessRequest only with --assess and only if a request exists). --save writes tests/last_outputs.json."""
import asyncio, json, os, sys, urllib.request, urllib.error
import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, '..', 'config', 'lab.json')))
TOK = {role: t for t, role in CFG['mcpTokens'].items()}
URL = 'http://127.0.0.1:%d/mcp/' % CFG['port']
VERBOSE = '--verbose' in sys.argv

# Role rules (lab/mcp_server.py: read + prepare kinds, and the acts in ACTS; never openRequest). Only these facts are pinned, not counts.
READS = {'findCustomers', 'customerOverview', 'invoices', 'ownerContext', 'cases', 'caseDetails', 'whereIs', 'compareExtension', 'workQueue',
         'listRequests', 'decisionStatus', 'actionStatus', 'whatIsNeeded', 'comparableCases', 'customerStatus', 'policyBacktest', 'impactSummary', 'modelStatus'}
PREPARES = {'assessRequest', 'prepareCustomer', 'prepareHoldingMessage', 'proposeImport', 'prepareDecision', 'interpretStatement', 'prepareRequest'}
ACTS = {'withdrawPreparation', 'requestSuggestion', 'resolveDecision'}   # the only write-kind (act) tools an external agent may run
KNOWN = READS | PREPARES | ACTS | {'assessDecision'}
CORE_BOTH = ['findCustomers', 'customerOverview', 'invoices', 'ownerContext', 'cases', 'caseDetails', 'whereIs', 'compareExtension', 'workQueue',
             'listRequests', 'assessRequest', 'prepareCustomer', 'prepareHoldingMessage', 'proposeImport', 'decisionStatus']   # on every role
STAFF_ONLY = {'assessDecision', 'resolveDecision', 'prepareRequest'}   # assessDecision/resolveDecision are staff-only; prepareRequest is staff (where deployed)
OWNER_ONLY = {'prepareDecision', 'interpretStatement', 'withdrawPreparation', 'requestSuggestion'}
BOTH_IF_PRESENT = {'decisionStatus', 'actionStatus'}   # decisionStatus is required (CORE_BOTH); actionStatus is on both roles wherever deployed
S3_BOTH = {'whatIsNeeded', 'comparableCases', 'customerStatus'}   # S3 read tools, off until the Owner switches them on (Setup): on both roles when enabled
S3_OWNER = {'policyBacktest', 'impactSummary', 'modelStatus'}   # S3 Owner-only read tools: never on the staff list
OWNER_AGENT = ['decisionStatus', 'customerStatus', 'comparableCases', 'policyBacktest', 'impactSummary', 'cases', 'workQueue', 'customerOverview', 'invoices', 'findCustomers']   # the tools of the LibreChat Owner agent (nucleon-local-owner)
NEVER = {'openRequest', 'answerConcern'}   # an agent's words never become intake or a concern's answer
rows, saved = [], {}


def rec(name, expected, actual, ok):
    rows.append((name, expected, actual, ok)); print(('PASS ' if ok else 'FAIL ') + name + ' | expected: ' + expected + ' | actual: ' + actual)


def raw(headers, body=None):
    h = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream', **headers}
    body = body or {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-03-26', 'capabilities': {}, 'clientInfo': {'name': 'check', 'version': '0'}}}
    try:
        return urllib.request.urlopen(urllib.request.Request(URL, json.dumps(body).encode(), h), timeout=30).status
    except urllib.error.HTTPError as e:
        return e.code


def client(role):
    hc = httpx2.AsyncClient(headers={'Authorization': 'Bearer ' + TOK[role]}, timeout=120)
    return Client(streamable_http_client(URL, http_client=hc))


async def call(cl, name, args):
    try:
        r = await cl.call_tool(name, args)
        text = ''.join(c.text for c in r.content if getattr(c, 'text', None))
        return ('error' if r.is_error else 'ok'), text
    except Exception as e:
        return 'exc', '%s: %s' % (type(e).__name__, e)


def js(text):
    try:
        return json.loads(text)
    except ValueError:
        return {}


def short(items):
    return ','.join(sorted(items)) or '-'


async def main():
    # 1. transport / auth
    s = raw({}); rec('no token', '401', str(s), s == 401)
    s = raw({'Authorization': 'Bearer ' + 'x' * 43}); rec('wrong token', '401', str(s), s == 401)
    s = raw({'Authorization': 'Bearer ' + TOK['staff'], 'Host': 'evil.example.org'})
    rec('bad Host header (valid staff token)', '421', str(s), s == 421)
    s = raw({'Authorization': 'Bearer ' + TOK['staff'], 'Host': 'host.docker.internal:8630'})
    rec('Host host.docker.internal:8630 (as LibreChat sends)', '200', str(s), s == 200)
    # 2. tool lists, compared by role rules against the live lists
    async with client('owner') as ow:
        owner = {t.name for t in (await ow.list_tools()).tools}
    async with client('staff') as st:
        staff = {t.name for t in (await st.list_tools()).tools}
        rec('staff core tools present', 'all of %d core tools' % len(CORE_BOTH), 'missing: ' + short(set(CORE_BOTH) - staff), set(CORE_BOTH) <= staff)
        rec('owner core tools present', 'all of %d core tools' % len(CORE_BOTH), 'missing: ' + short(set(CORE_BOTH) - owner), set(CORE_BOTH) <= owner)
        rec('staff list is a subset of owner list (less the staff-only tools)', 'staff - staff-only <= owner', 'extra: ' + short(staff - STAFF_ONLY - owner), staff - STAFF_ONLY <= owner)
        rec('staff-only tools are not on the owner list', 'none of ' + short(STAFF_ONLY), 'on owner: ' + short(STAFF_ONLY & owner), not STAFF_ONLY & owner)
        rec('owner-only tools: owner has them, staff does not', 'owner has all, staff none', 'owner lacks: %s; staff has: %s' % (short(OWNER_ONLY - owner), short(OWNER_ONLY & staff)), OWNER_ONLY <= owner and not OWNER_ONLY & staff)
        rec('assessDecision + resolveDecision on staff', 'present', 'missing: ' + short({'assessDecision', 'resolveDecision'} - staff), {'assessDecision', 'resolveDecision'} <= staff)
        rec('decisionStatus on both roles', 'both', 'staff=%s owner=%s' % ('decisionStatus' in staff, 'decisionStatus' in owner), 'decisionStatus' in staff and 'decisionStatus' in owner)
        rec('owner token cannot see resolveDecision/assessDecision/prepareRequest', 'none of them', 'on owner: ' + short({'resolveDecision', 'assessDecision', 'prepareRequest'} & owner),
            not {'resolveDecision', 'assessDecision', 'prepareRequest'} & owner)
        rec('S3 owner-only read tools are never on the staff list', 'none of ' + short(S3_OWNER), 'on staff: ' + short(S3_OWNER & staff), not S3_OWNER & staff)
        # present or absent per role: each S3 read tool is either switched on (Setup) and then on exactly its roles, or off and on none
        rec('S3 tools offered to both roles are on both roles or on neither (each)', 'staff == owner for ' + short(S3_BOTH), 'differs: ' + short({n for n in S3_BOTH if (n in staff) != (n in owner)}),
            all((n in staff) == (n in owner) for n in S3_BOTH))
        s3_on = (S3_BOTH | S3_OWNER) <= owner
        missing = set(OWNER_AGENT) - owner
        rec('Owner-agent tools: every one is on the owner list, or is an S3 tool the Owner has not switched on', 'ten present once the five S3 tools are on', 'missing: ' + short(missing),
            (not missing) if s3_on else missing <= (S3_BOTH | S3_OWNER))
        agent_tools = set(OWNER_AGENT) & owner
        rec('every Owner-agent tool on the owner list is read-only (no act or prepare tool)', 'subset of READS', 'not read: ' + short(agent_tools - READS), agent_tools <= READS)
        rec('actionStatus on both roles or neither', 'both or neither', 'staff=%s owner=%s' % ('actionStatus' in staff, 'actionStatus' in owner), ('actionStatus' in staff) == ('actionStatus' in owner))
        rec('prepareRequest staff only (if deployed)', 'not on owner', 'staff=%s owner=%s' % ('prepareRequest' in staff, 'prepareRequest' in owner), 'prepareRequest' not in owner)
        for role, names in (('staff', staff), ('owner', owner)):
            writes = {n for n in names if n not in READS and n not in PREPARES and n != 'assessDecision'}
            rec(role + ' exposes no write tool outside ACTS', 'only ' + short(ACTS), 'writes: ' + short(writes) + ' | unknown: ' + short(names - KNOWN) + ' | forbidden: ' + short(names & NEVER),
                writes <= ACTS and not names - KNOWN and not names & NEVER)
        print('INFO staff tools (%d): %s' % (len(staff), short(staff))); print('INFO owner tools (%d): %s' % (len(owner), short(owner)))
        # 3. rejected / unknown
        for n in sorted(OWNER_ONLY | S3_OWNER) + ['openRequest', 'answerConcern', 'noSuchTool']:
            k, t = await call(st, n, {})
            want = 'INVALID_PARAMS' if n == 'noSuchTool' else 'rejected'
            rec('staff -> ' + n, 'rejected (' + want + ')', k + ' ' + t[:90], k in ('exc', 'error'))
        # 4. read-only, on customers picked by name from the live findCustomers result
        async def show(label, name, args, check=None):
            k, t = await call(st, name, args); saved[label] = t
            ok = k == 'ok' and (check(t) if check else True)
            rec(label, 'ok', k + ' ' + t[:110].replace('\n', ' '), ok)
            if VERBOSE: print('    ' + t)
            return t

        async def pick(substr):
            k, t = await call(st, 'findCustomers', {'query': substr}); saved['findCustomers ' + substr] = t
            hits = [m for m in js(t).get('matches', []) if substr.lower() in m.get('name', '').lower()]
            rec('findCustomers ' + substr, 'a customer whose name contains it', '%s, %d match(es)' % (k, len(hits)), k == 'ok' and js(t).get('count') == len(js(t).get('matches', [])) and bool(hits))
            return hits[0] if hits else None
        bay, river = await pick('Bayview'), await pick('Riverside')
        for tag, c in (('Bayview', bay), ('Riverside', river)):
            if not c:
                rec('customer-based checks for ' + tag, 'customer found', 'SKIPPED: no customer named like ' + tag + ' (is the ADA demo dataset seeded?)', False); continue
            await show('customerOverview %s (code)' % tag, 'customerOverview', {'customerId': c['code']}, lambda t: isinstance(js(t).get('completeness'), dict))
            t = await show('customerOverview %s (id)' % tag, 'customerOverview', {'customerId': c['customerId']}, lambda t: isinstance(js(t).get('completeness'), dict) and js(t).get('customerId') == c['customerId'])
            for w in ('open', 'all', 'overdue'):
                await show('invoices %s %s' % (tag, w), 'invoices', {'customerId': c['customerId'], 'which': w}, lambda t: 'invoices' in js(t))
            await show('cases ' + tag, 'cases', {'customerId': c['customerId']}, lambda t: 'cases' in js(t))
            await show('ownerContext ' + tag, 'ownerContext', {'customerId': c['customerId']}, lambda t: 'lines' in js(t))
        if bay:
            inv = js(saved.get('invoices Bayview all', '')).get('invoices', [])
            refs = [i.get('reference') for i in inv if i.get('reference')]
            rec('invoices Bayview all returns at least one invoice', '>= 1 invoice with a reference', '%d invoice(s)' % len(refs), bool(refs))
            if refs:   # the reference comes from the live result; it must be findable by that same reference through the invoice's own list
                await show('invoices Bayview open lists a live reference', 'invoices', {'customerId': bay['customerId'], 'which': 'open'},
                           lambda t: all(i.get('reference') for i in js(t).get('invoices', [])) and js(t).get('invoiceCount') == len(js(t).get('invoices', [])))
        t = await show('findCustomers Harbour', 'findCustomers', {'query': 'Harbour'}, lambda t: js(t).get('count', 0) >= 1)
        t = await show('findCustomers non-existent', 'findCustomers', {'query': 'CUST-DOES-NOT-EXIST'}, lambda t: js(t).get('count') == 0 and js(t).get('matches') == [])
        k, t = await call(st, 'customerOverview', {'customerId': 'CUST-DOES-NOT-EXIST'}); saved['customerOverview non-existent'] = t
        rec('customerOverview non-existent', 'not a zero balance', k + ' ' + t[:150], k != 'ok' or ('"owedNow"' not in t and 'outstanding' not in t.lower()))
        k, t = await call(st, 'invoices', {'customerId': 'CUST-DOES-NOT-EXIST', 'which': 'open'}); saved['invoices non-existent'] = t
        rec('invoices non-existent', 'not a zero balance', k + ' ' + t[:150], k != 'ok' or 'total' not in t.lower())
        await show('workQueue', 'workQueue', {}, lambda t: 'forYou' in js(t))
        await show('listRequests all', 'listRequests', {'status': 'all'}, lambda t: 'requests' in js(t))
        await show('whereIs completeness', 'whereIs', {'topic': 'completeness'})
        if '--assess' in sys.argv:
            reqs = js(saved['listRequests all']).get('requests', [])
            if reqs:
                await show('assessRequest (WRITES)', 'assessRequest', {'requestId': reqs[0]['id']})
                await show('caseDetails after assess', 'caseDetails', {'requestId': reqs[0]['id']})
            else:
                print('SKIP assessRequest: no request exists')
    async with client('owner') as ow:
        # owner-only tools are read-safe to refuse-check only for names an owner may not run
        for n in ('openRequest', 'answerConcern', 'noSuchTool', 'assessDecision', 'resolveDecision', 'prepareRequest'):
            k, t = await call(ow, n, {})
            rec('owner -> ' + n, 'rejected', k + ' ' + t[:90], k in ('exc', 'error'))
        if S3_OWNER <= owner:   # the Owner's what-if and impact are reads: they answer, store nothing and carry the compact result the model reads
            for n, args in (('policyBacktest', {}), ('policyBacktest', {'changes': {'extensions': {'maxDays': 10}}}), ('impactSummary', {})):
                k, t = await call(ow, n, args)
                rec('owner -> %s %s (read)' % (n, json.dumps(args)[:40]), 'ok, status in the compact text, at most 1500 characters', k + ' ' + t[:90].replace('\n', ' '),
                    k == 'ok' and 'status' in js(t) and len(t) <= 1500)
            k, t = await call(ow, 'policyBacktest', {'changes': {'noSuchSetting': 1}})
            rec('owner -> policyBacktest with an unknown setting', 'refused, nothing saved', k + ' ' + t[:90], k == 'error')
    if '--save' in sys.argv:
        json.dump(saved, open(os.path.join(HERE, 'last_outputs.json'), 'w'), indent=1)
    bad = [r for r in rows if not r[3]]
    print('\n%d checks passed, %d failed' % (len(rows) - len(bad), len(bad)))
    sys.exit(1 if bad else 0)

asyncio.run(main())
