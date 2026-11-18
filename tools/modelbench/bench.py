"""Model test bench for the Staff agent (S3, docs/product/POV-IMPLEMENTATION-PLAN-20261030.md, D5).

Runs the five standard prompts N times against a model served over an OpenAI-compatible chat API, with the REAL MCP tool definitions (the Lab's, for the Staff
token) and the Staff agent's instructions (integrations/librechat/agents/instructions_staff.txt), in a minimal tool loop (temperature 0.2, at most 12 tool calls),
on a scratch Records and a scratch Lab the bench starts itself on free loopback ports with codes and tokens generated for this run (never written to the repo).
Each prompt runs on freshly reset fictional data (prototype/delegation_demo.py, the Owner's delegated demo policy saved through the HTTP API as an Owner person).
A run is judged by the BACKEND state (the Owner's view of the decision cases), the number of tool calls, wall time and tokens; the model's text is recorded, and
only checked crudely for saying "approved" when the backend did not approve. Fictional data only.

    ~/Developer/nucleon-local/venv/bin/python tools/modelbench/bench.py --runs 3                      # LM Studio at http://127.0.0.1:1234/v1, qwen3.5-35b-a3b
    bench.py --base-url https://api.example/v1 --model NAME --api-key-env MY_KEY_VAR --price-in 1 --price-out 3   # a cloud model; prices per million tokens
    bench.py --check-stack                                                                                  # start the stack, list the tools, no model

Needs Python 3.10+ with the Lab's packages (mcp, httpx2): the Lab's venv. Writes results/<model>-<timestamp>.json and .md. Starts nothing on 8630, 8631 or 3080
and never touches LibreChat or the live Records."""
import argparse
import asyncio
import hashlib
import json
import os
import re
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'prototype'))
INSTRUCTIONS_FILE = ROOT / 'integrations' / 'librechat' / 'agents' / 'instructions_staff.txt'

# The tools of the LibreChat Staff agent after update_ada_agent_hints.js, as the Lab names them; the Owner switches them on under Setup.
STAFF_TOOLS = ['findCustomers', 'customerOverview', 'invoices', 'assessDecision', 'resolveDecision', 'decisionStatus', 'whatIsNeeded', 'customerStatus']
MAX_CALLS = 12
TEMPERATURE = 0.2
ADEQUATE_CALLS = 4   # the plan's bar: a prompt counts for the "adequate" rule when it passed with at most this many tool calls

NUDGE_TEXT = ('The request is not submitted yet. If you have everything needed, call resolveDecision now. If something is missing or unclear, tell Staff exactly what is missing; '
              'do not guess it and do not submit.')
INSTRUCTIONS_EXTRA_EXAMPLE = 'End your turn only after the case is submitted with resolveDecision, or after you have told Staff exactly what is missing.'

# name: (prompt, customer shown in the case list or None, expected backend state). Wording as the acceptance round and KNOWN-LIMITATIONS L-001 use it.
PROMPTS = {
    'northside': ('Northside Cafe is a new customer and wants AUD 800 of stock on 14-day terms; they paid a 25% deposit, which is recorded in Nucleon.', 'Northside', 'decided_by_agent'),
    'bayview': ('Bayview Gelato Co asks to move invoice DEMO-301 to 10 November 2026.', 'Bayview', 'decided_by_agent'),
    'harbourline': ('Harbourline Catering, a new customer, wants AUD 5,000 on 14-day terms.', 'Harbourline', 'awaiting_owner'),
    'lakeside': ('Lakeside Kiosk, a new customer, wants AUD 600 on 14-day terms.', 'Lakeside', 'gathering_evidence'),
    'mixed': ('NorthSide Cafe wants an approved credit of 1500 AUD within 30 days extension what is your decision on this?', None, 'no_case'),
}

# The ambiguity set (--extra, phase A5): requests the Staff agent must NOT decide; it must ask Staff one short question and create no case. Not part of the D5 bar.
# 'amount-and-due-date' has two readings: (1) ask, no case (expected: terms in days are missing); (2) a trial credit with terms derived from the date. Judged as (1);
# the record keeps what the backend did so (2) can be read from it.
EXTRA_PROMPTS = {
    'ambiguous-extension': ('Bayview Gelato Co wants an extension on one of its invoices.', None, 'no_case'),
    'bare-approve': ('Please approve this for Harbourline', None, 'no_case'),
    'amount-and-due-date': ('Northside Cafe, a new customer, wants AUD 800 of stock and will pay by 20 November 2026.', None, 'no_case'),
}
ALL_PROMPTS = {**PROMPTS, **EXTRA_PROMPTS}


# ---------------------------------------------------------------- pure helpers (tested in test_bench.py)

def instructions(extra=None, path=None):
    """The Staff agent's instructions exactly as update_ada_agent_hints.js joins them: the paragraphs of instructions_staff.txt, joined by a space. extra: one line
    appended (the --instructions-extra experiment)."""
    text = ' '.join(line.strip() for line in (Path(path) if path else INSTRUCTIONS_FILE).read_text(encoding='utf-8').splitlines() if line.strip())
    return text + ' ' + extra.strip() if extra and extra.strip() else text


def nudge_reason(tool_names, final, already_nudged):
    """The early-stop nudge rule (pure). Called when the model's turn has ended (a reply with no tool call). Returns why ONE automatic user message should follow, or None:
    'empty' when the reply is empty; 'unsubmitted' when the turn called assessDecision or whatIsNeeded and never resolveDecision. At most one nudge per prompt."""
    if already_nudged:
        return None
    if not (final or '').strip():
        return 'empty'
    if ('assessDecision' in tool_names or 'whatIsNeeded' in tool_names) and 'resolveDecision' not in tool_names:
        return 'unsubmitted'
    return None


def nudge_outcome(tool_names_after, final_after):
    """What happened after the nudge: 'resolved' (resolveDecision was called), 'still_empty' (empty reply, no resolve), else 'asked_staff' (a text reply)."""
    if 'resolveDecision' in tool_names_after:
        return 'resolved'
    return 'still_empty' if not (final_after or '').strip() else 'asked_staff'


NEGATION = re.compile(r"\b(not|nothing|no|never|until|unless|if|would|once|before|pending|needs?|can't|cannot|isn't|hasn't|haven't|without|yet|awaiting|if it|whether)\b|n't", re.I)


def contradicts(text, status):
    """Crude: the final text says something was approved when the backend did not approve it (status is the case status, or None for no case). A sentence that says
    "approved" with no negation or condition in it counts. Returns the offending sentence or None. Model text is not otherwise judged."""
    if status == 'decided' or not text:
        return None
    for sentence in re.split(r'(?<=[.!?\n])\s+', text):
        if re.search(r'\bapproved\b|\bapproval granted\b', sentence, re.I) and not NEGATION.search(sentence):
            return sentence.strip()[:200]
    return None


def judge(name, cases, expected, calls, error=None):
    """(passed, reasons): the backend state against the expected one. cases: the live decision cases the Owner's list shows now, for this scratch data. Exactly one case
    for a prompt about one request, none for the mixed one."""
    reasons = []
    if error:
        reasons.append('error: ' + error)
    mine = [c for c in cases if ALL_PROMPTS[name][1] and ALL_PROMPTS[name][1].lower() in ((c.get('customer') or {}).get('name') or '').lower()]
    if expected == 'no_case':
        if cases:
            reasons.append('%d case(s) were created, none expected' % len(cases))
    else:
        if len(cases) != 1 or len(mine) != 1:
            reasons.append('%d case(s) in all, %d for this customer; exactly one expected' % (len(cases), len(mine)))
        elif expected == 'decided_by_agent':
            c = mine[0]
            if c.get('status') != 'decided' or (c.get('decision') or {}).get('by') != 'agent' or (c.get('decision') or {}).get('outcome') != 'approve':
                reasons.append('status %s, decided by %s; expected approved by the agent' % (c.get('status'), (c.get('decision') or {}).get('by')))
        elif mine[0].get('status') != expected:
            reasons.append('status %s; expected %s' % (mine[0].get('status'), expected))
    return not reasons, reasons


def summarise(results, runs):
    """Per prompt: runs passed, passed with at most ADEQUATE_CALLS tool calls, median calls and seconds; and the whole-run figure the plan's rule uses (all five prompts
    passed with at most ADEQUATE_CALLS calls each, in how many runs)."""
    out = {'perPrompt': {}, 'runsAdequate': 0, 'runs': runs}
    for name in ALL_PROMPTS:
        rows = [r for r in results if r['prompt'] == name]
        if not rows:
            continue
        calls = sorted(r['toolCalls'] for r in rows)
        secs = sorted(r['seconds'] for r in rows)
        out['perPrompt'][name] = {'runs': len(rows), 'passed': sum(r['passed'] for r in rows), 'passedWithinCalls': sum(r['passed'] and r['toolCalls'] <= ADEQUATE_CALLS for r in rows),
                                  'medianCalls': calls[len(calls) // 2] if calls else None, 'medianSeconds': secs[len(secs) // 2] if secs else None,
                                  'providerErrors': sum(r['providerErrors'] for r in rows), 'contradictions': sum(bool(r['contradiction']) for r in rows)}
    for i in range(runs):
        rows = [r for r in results if r['run'] == i and r['prompt'] in PROMPTS]
        if len(rows) == len(PROMPTS) and all(r['passed'] and r['toolCalls'] <= ADEQUATE_CALLS for r in rows):
            out['runsAdequate'] += 1
    return out


def markdown(meta, summary, results):
    lines = ['| Prompt | Passed | Passed with <= %d calls | Median calls | Median seconds | Provider errors | Says "approved" wrongly |' % ADEQUATE_CALLS, '|---|---|---|---|---|---|---|']
    for name, s in summary['perPrompt'].items():
        lines.append('| %s | %d/%d | %d/%d | %s | %s | %d | %d |' % (name, s['passed'], s['runs'], s['passedWithinCalls'], s['runs'], s['medianCalls'], s['medianSeconds'], s['providerErrors'], s['contradictions']))
    tokens = [r for r in results if r.get('promptTokens') is not None]
    tail = ['', 'Runs where all five prompts passed with <= %d tool calls each: **%d of %d**.' % (ADEQUATE_CALLS, summary['runsAdequate'], summary['runs'])]
    if tokens:
        tail.append('Tokens per prompt (median): %d prompt, %d completion.' % (sorted(r['promptTokens'] for r in tokens)[len(tokens) // 2], sorted(r['completionTokens'] for r in tokens)[len(tokens) // 2]))
    fired = [r for r in results if r.get('nudge')]
    if meta.get('nudge'):
        tail.append('Nudge fired in %d of %d prompts. After it: %s.' % (len(fired), len(results), ', '.join('%s %d' % (k, sum(r['nudge']['outcome'] == k for r in fired)) for k in ('resolved', 'asked_staff', 'still_empty'))))
        mixed = [r for r in results if r['prompt'] == 'mixed']
        tail.append('Mixed prompt: nudge fired %d of %d, cases created in %d.' % (sum(bool(r.get('nudge')) for r in mixed), len(mixed), sum(bool(r['backend']) for r in mixed)))
    if meta.get('costUsd') is not None:
        tail.append('Cost of this bench: USD %.4f (%d prompts).' % (meta['costUsd'], len(results)))
    return '\n'.join(lines + tail) + '\n'


# ---------------------------------------------------------------- the scratch stack

def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def http(method, url, body=None, headers=None, timeout=60):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={**({'Content-Type': 'application/json'} if data is not None else {}), **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            try:
                return r.status, json.loads(raw or b'null'), r.headers
            except ValueError:   # the MCP endpoint answers an event stream
                return r.status, {'raw': raw[:300].decode('utf-8', 'replace')}, r.headers
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw), e.headers
        except ValueError:
            return e.code, {'raw': raw[:300].decode('utf-8', 'replace')}, e.headers


class Stack:
    """A scratch Records and a scratch Lab on free loopback ports, with codes and tokens generated for this run. reset() puts the fictional data back."""

    def __init__(self, work):
        self.work = Path(work)
        self.rport, self.lport = free_port(), free_port()
        self.access = {'staff': 'bench-' + secrets.token_hex(8), 'owner': 'bench-' + secrets.token_hex(8)}
        self.service = {'staff': 'svc-' + secrets.token_hex(8), 'owner': 'svc-' + secrets.token_hex(8)}
        self.tokens = {'staff': secrets.token_urlsafe(32), 'owner': secrets.token_urlsafe(32)}
        self.records_url, self.lab_url = 'http://127.0.0.1:%d' % self.rport, 'http://127.0.0.1:%d/mcp/' % self.lport
        self.db, self.snapshot = self.work / 'records.db', self.work / 'snapshot.db'
        self.timing = self.work / 'logs' / 'tool-timing.jsonl'
        self.records_proc = self.lab_proc = None
        self.owner = None   # {cookie, csrf}
        (self.work / 'records.json').write_text(json.dumps({'port': self.rport, 'db': str(self.db), 'agentMode': 'mock', 'sampleData': False,
                                                            'accessCodes': self.access, 'serviceCodes': self.service}))
        (self.work / 'lab.json').write_text(json.dumps({'host': '127.0.0.1', 'port': self.lport, 'rootPath': '', 'recordsUrl': self.records_url, 'publicOrigins': [],
                                                        'mcpTokens': {self.tokens['staff']: 'staff', self.tokens['owner']: 'owner'}, 'recordsCodes': self.service,
                                                        'timingLog': str(self.timing)}))
        for f in ('records.json', 'lab.json'):
            os.chmod(self.work / f, 0o600)

    def start_records(self):
        self.records_proc = subprocess.Popen([sys.executable, str(ROOT / 'prototype' / 'server.py'), '--config', str(self.work / 'records.json')],
                                             stdout=open(self.work / 'records.log', 'ab'), stderr=subprocess.STDOUT, cwd=str(ROOT))
        self.wait(lambda: http('GET', self.records_url + '/api/session', timeout=3)[0] == 200, 'the scratch Records')

    def stop_records(self):
        if self.records_proc:
            self.records_proc.terminate()
            try:
                self.records_proc.wait(15)
            except subprocess.TimeoutExpired:
                self.records_proc.kill()
            self.records_proc = None

    def start_lab(self):
        self.lab_proc = subprocess.Popen([sys.executable, '-m', 'lab', '--config', str(self.work / 'lab.json')], stdout=open(self.work / 'lab.log', 'ab'),
                                         stderr=subprocess.STDOUT, cwd=str(self.work), env={**os.environ, 'PYTHONPATH': str(ROOT)})
        self.wait(lambda: http('POST', self.lab_url, {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-03-26', 'capabilities': {}, 'clientInfo': {'name': 'bench', 'version': '0'}}},
                               {'Authorization': 'Bearer ' + self.tokens['staff'], 'Accept': 'application/json, text/event-stream'}, 3)[0] == 200, 'the scratch Lab')

    @staticmethod
    def wait(ready, what, seconds=40):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            try:
                if ready():
                    return
            except (OSError, ValueError):
                pass
            time.sleep(0.3)
        raise RuntimeError(what + ' did not start')

    def login_owner(self):
        status, body, headers = http('POST', self.records_url + '/api/demo/login', {'accessCode': self.access['owner']}, {'Origin': self.records_url})
        assert status == 200, body
        cookie = headers['Set-Cookie'].split(';')[0]
        status, session, _ = http('GET', self.records_url + '/api/session', headers={'Cookie': cookie})
        self.owner = {'cookie': cookie, 'csrf': session['csrf']}

    def owner_call(self, method, path, body=None, key=None):
        h = {'Cookie': self.owner['cookie'], 'Origin': self.records_url, 'X-Nucleon-CSRF': self.owner['csrf'], **({'Idempotency-Key': key} if key else {})}
        return http(method, self.records_url + path, body, h)

    def seed(self):
        """Fictional demonstration data, the delegated demo policy saved through the HTTP API as the Owner person, the tools switched on; then a snapshot to reset to."""
        import delegation_demo
        for f in (self.db, Path(str(self.db) + '-wal'), Path(str(self.db) + '-shm')):
            f.unlink(missing_ok=True)
        subprocess.run([sys.executable, str(ROOT / 'prototype' / 'delegation_demo.py'), '--db', str(self.db), '--replace'], check=True, capture_output=True, cwd=str(ROOT / 'prototype'))
        self.start_records()
        self.login_owner()
        status, policy, _ = self.owner_call('GET', '/api/delegation/policy')
        status, saved, _ = self.owner_call('PUT', '/api/delegation/policy', {**delegation_demo.DEMO_POLICY, 'expectedVersion': policy['version'], 'note': 'Fictional bench policy (the acceptance scenario 0).'})
        assert status == 200, saved
        for tool in STAFF_TOOLS:
            status, out, _ = self.owner_call('POST', '/api/agent-tools', {'tool': tool, 'enabled': True}, 'bench-on-' + tool)
            assert status == 200, out
        self.stop_records()
        src, dst = sqlite3.connect(str(self.db)), sqlite3.connect(str(self.snapshot))
        with dst:
            src.backup(dst)
        src.close()
        dst.close()

    def reset(self):
        """Stop the Records, put the snapshot (fictional data, policy version 1, tools on) back, start it again. The Lab signs in again by itself (it renews on 401)."""
        self.stop_records()
        for f in (self.db, Path(str(self.db) + '-wal'), Path(str(self.db) + '-shm')):
            f.unlink(missing_ok=True)
        shutil.copyfile(self.snapshot, self.db)
        self.start_records()
        self.login_owner()

    def cases(self):
        status, body, _ = self.owner_call('GET', '/api/delegation/cases?dataset=live')
        assert status == 200, body
        return body['cases']

    def close(self):
        for p in (self.lab_proc,):
            if p:
                p.terminate()
                try:
                    p.wait(10)
                except subprocess.TimeoutExpired:
                    p.kill()
        self.stop_records()


# ---------------------------------------------------------------- the model

class ProviderError(Exception):
    pass


class Chat:
    """An OpenAI-compatible chat completions endpoint. The key is only ever sent as a bearer header."""

    def __init__(self, base_url, model, key, max_tokens):
        self.url, self.model, self.key, self.max_tokens = base_url.rstrip('/') + '/chat/completions', model, key, max_tokens

    def complete(self, messages, tools):
        body = {'model': self.model, 'messages': messages, 'tools': tools, 'temperature': TEMPERATURE, 'max_tokens': self.max_tokens, 'stream': False}
        try:
            status, out, _ = http('POST', self.url, body, {'Authorization': 'Bearer ' + self.key}, timeout=900)
        except OSError as e:
            raise ProviderError('connection: %s' % e)
        if status != 200 or not out.get('choices'):
            raise ProviderError('HTTP %s: %s' % (status, json.dumps(out)[:300]))
        return out


async def run_prompt(session, tools, chat, system, prompt, nudge=False):
    """The minimal tool loop: the model answers, calls tools (each result is the Lab's TEXT item, as LibreChat gives it to the model), until it replies in text or has
    made MAX_CALLS calls. Returns the record of what happened."""
    messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': prompt}]
    calls, usage, final, truncated = [], {'prompt': 0, 'completion': 0, 'seen': False}, None, False
    nudged = None   # {'reason', 'callsBefore', 'textBefore'} once the nudge has fired
    for _ in range(MAX_CALLS + 3):
        out = await asyncio.get_running_loop().run_in_executor(None, chat.complete, messages, tools)
        if isinstance(out.get('usage'), dict):
            usage['seen'] = True
            usage['prompt'] += out['usage'].get('prompt_tokens') or 0
            usage['completion'] += out['usage'].get('completion_tokens') or 0
        message = out['choices'][0]['message']
        wanted = message.get('tool_calls') or []
        messages.append({k: v for k, v in message.items() if k in ('role', 'content', 'tool_calls')} | {'content': message.get('content') or ''})
        if not wanted:
            final = message.get('content') or ''
            reason = nudge_reason([c['tool'] for c in calls], final, nudged is not None) if nudge and len(calls) < MAX_CALLS else None
            if reason:
                nudged = {'reason': reason, 'callsBefore': len(calls), 'textBefore': final[:300]}
                messages.append({'role': 'user', 'content': NUDGE_TEXT})
                final = None
                continue
            break
        for call in wanted:
            if len(calls) >= MAX_CALLS:
                truncated = True
                break
            name, raw = call['function']['name'], call['function'].get('arguments') or '{}'
            try:
                args = json.loads(raw) if isinstance(raw, str) else raw
                if not isinstance(args, dict):
                    raise ValueError('not an object')
            except ValueError:
                result, ok = json.dumps({'error': 'INVALID_ARGUMENT', 'message': 'Arguments must be a JSON object.'}), False
                args = {'_raw': str(raw)[:200]}
            else:
                try:
                    r = await session.call_tool(name, args)
                    result, ok = ''.join(c.text for c in r.content if getattr(c, 'text', None)), not r.is_error
                except Exception as e:   # an unknown tool is a protocol error: the model is told, as LibreChat would
                    result, ok = json.dumps({'error': 'TOOL_ERROR', 'message': str(e)[:200]}), False
            calls.append({'tool': name, 'args': args, 'ok': ok, 'resultChars': len(result), 'result': result[:2000]})
            messages.append({'role': 'tool', 'tool_call_id': call.get('id') or 'call_%d' % len(calls), 'content': result})
        if truncated:
            break
    if nudged:
        nudged['outcome'] = nudge_outcome([c['tool'] for c in calls[nudged['callsBefore']:]], final)
        nudged['callsAfter'] = len(calls) - nudged['callsBefore']
    return {'nudge': nudged, 'calls': calls, 'final': final, 'truncated': truncated, 'promptTokens': usage['prompt'] if usage['seen'] else None, 'completionTokens': usage['completion'] if usage['seen'] else None}


def timing_lines(path, offset):
    try:
        with open(path, 'rb') as f:
            f.seek(offset)
            return [json.loads(line) for line in f.read().decode().splitlines() if line.strip()], f.tell()
    except OSError:
        return [], offset


async def one(stack, chat, system, name, run, cost, nudge=False):
    from mcp import Client
    from mcp.client.streamable_http import streamable_http_client
    import httpx2
    prompt, _, expected = ALL_PROMPTS[name]
    record = None
    for attempt in range(2):   # a provider error (LM Studio's "predecessor handoff") is recorded and the prompt retried once, on fresh data
        stack.reset()
        offset = os.path.getsize(stack.timing) if stack.timing.exists() else 0
        started, error = time.monotonic(), None
        loop_result = {'nudge': None, 'calls': [], 'final': None, 'truncated': False, 'promptTokens': None, 'completionTokens': None}
        try:
            async with httpx2.AsyncClient(headers={'Authorization': 'Bearer ' + stack.tokens['staff']}, timeout=300) as hc, Client(streamable_http_client(stack.lab_url, http_client=hc)) as cl:
                listed = (await cl.list_tools()).tools
                tools = [{'type': 'function', 'function': {'name': t.name, 'description': t.description, 'parameters': t.input_schema}} for t in listed if t.name in STAFF_TOOLS]
                loop_result = await run_prompt(cl, tools, chat, system, prompt, nudge)
        except ProviderError as e:
            error = 'provider: ' + str(e)
        except BaseExceptionGroup as e:   # the MCP client's streamable-HTTP stream can fail while the session closes (httpx2.ReadError, seen 31 Oct); the prompt's loop has finished by then
            provider = [x for x in e.exceptions if isinstance(x, ProviderError)]
            if provider:   # the MCP client's task group wraps an error raised inside the session
                error = 'provider: ' + str(provider[0])
            elif loop_result['final'] is None and not loop_result['calls']:
                raise
            else:
                print('  (MCP session teardown error ignored: %s)' % type(e.exceptions[0]).__name__, flush=True)
        seconds = round(time.monotonic() - started, 1)
        cases = stack.cases()
        lab_rows, _ = timing_lines(stack.timing, offset)
        passed, reasons = judge(name, cases, expected, loop_result['calls'], error)
        mine = cases[0] if len(cases) == 1 else None
        wrong = contradicts(loop_result['final'], mine and mine.get('status'))
        if wrong:
            reasons.append('the text says approved but the backend did not approve: ' + wrong)
        record = {'run': run, 'prompt': name, 'passed': passed, 'reasons': reasons, 'toolCalls': len(loop_result['calls']), 'seconds': seconds, 'truncated': loop_result['truncated'],
                  'promptTokens': loop_result['promptTokens'], 'completionTokens': loop_result['completionTokens'], 'providerErrors': attempt + (1 if error else 0) if error else attempt,
                  'contradiction': wrong, 'nudge': loop_result['nudge'], 'backend': [{k: c.get(k) for k in ('caseId', 'kind', 'status', 'handling')} | {'customer': (c.get('customer') or {}).get('name'), 'decidedBy': (c.get('decision') or {}).get('by')} for c in cases],
                  'tools': [{'tool': c['tool'], 'args': c['args'], 'ok': c['ok'], 'resultChars': c['resultChars']} for c in loop_result['calls']],
                  'labToolMs': round(sum(r['durationMs'] for r in lab_rows), 1), 'labToolLines': len(lab_rows), 'finalText': loop_result['final']}
        if error is None:
            break
        record['reasons'] = reasons
    if cost and record['promptTokens'] is not None:
        record['costUsd'] = (record['promptTokens'] * cost[0] + record['completionTokens'] * cost[1]) / 1e6
    return record


async def main_async(args):
    work = Path(tempfile.mkdtemp(prefix='modelbench-'))
    os.chmod(work, 0o700)
    stack = Stack(work)
    try:
        stack.seed()
        stack.start_records()
        stack.login_owner()
        stack.start_lab()
        if args.check_stack:
            from mcp import Client
            from mcp.client.streamable_http import streamable_http_client
            import httpx2
            async with httpx2.AsyncClient(headers={'Authorization': 'Bearer ' + stack.tokens['staff']}, timeout=60) as hc, Client(streamable_http_client(stack.lab_url, http_client=hc)) as cl:
                names = sorted(t.name for t in (await cl.list_tools()).tools)
            print('staff tools (%d): %s' % (len(names), ', '.join(names)))
            print('missing from the Staff agent set: %s' % (', '.join(sorted(set(STAFF_TOOLS) - set(names))) or 'none'))
            print('cases now: %d' % len(stack.cases()))
            return 0
        key = os.environ.get(args.api_key_env, '') if args.api_key_env else ''
        chat = Chat(args.base_url, args.model, key or 'lm-studio', args.max_tokens)
        system = instructions(args.instructions_extra, args.instructions_file)
        cost = (args.price_in, args.price_out) if args.price_in is not None and args.price_out is not None else None
        names = [n for n in (ALL_PROMPTS if args.extra else PROMPTS) if not args.only or n in args.only]
        results = []
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        for run in range(args.runs):
            for name in names:
                r = await one(stack, chat, system, name, run, cost, args.nudge)
                results.append(r)
                print('run %d %-12s %s calls=%d %5.1fs %s%s' % (run + 1, name, 'PASS' if r['passed'] else 'FAIL', r['toolCalls'], r['seconds'], '; '.join(r['reasons'])[:120], ' [provider error retried]' if r['providerErrors'] else ''), flush=True)
        summary = summarise(results, args.runs)
        meta = {'model': args.model, 'baseUrl': re.sub(r'//[^/@]*@', '//', args.base_url), 'startedUtc': stamp, 'runs': args.runs, 'prompts': names, 'temperature': TEMPERATURE, 'maxToolCalls': MAX_CALLS,
                'maxTokens': args.max_tokens, 'tools': STAFF_TOOLS, 'instructionsSha256': hashlib.sha256(system.encode()).hexdigest()[:16], 'instructionsChars': len(system), 'nudge': args.nudge, 'nudgeText': NUDGE_TEXT if args.nudge else None, 'instructionsExtra': args.instructions_extra, 'instructionsFile': args.instructions_file and Path(args.instructions_file).name,
                'commit': subprocess.run(['git', '-C', str(ROOT), 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip(),
                'costUsd': sum(r.get('costUsd', 0) for r in results) if cost else None, 'data': 'fictional', 'stack': 'scratch Records and Lab on loopback, fresh data per prompt'}
        out = HERE / 'results'
        out.mkdir(exist_ok=True)
        base = out / (re.sub(r'[^A-Za-z0-9._-]+', '-', args.model) + '-' + stamp)
        Path(str(base) + '.json').write_text(json.dumps({'meta': meta, 'summary': summary, 'results': results}, indent=1, ensure_ascii=False))
        table = markdown(meta, summary, results)
        Path(str(base) + '.md').write_text('# Model bench: %s, %s\n\n%s' % (args.model, stamp, table))
        print('\n' + table)
        print('wrote ' + str(base) + '.json')
        return 0
    finally:
        stack.close()
        shutil.rmtree(work, ignore_errors=True)


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('--base-url', default='http://127.0.0.1:1234/v1', help='an OpenAI-compatible API (default: LM Studio)')
    p.add_argument('--model', default='qwen3.5-35b-a3b')
    p.add_argument('--api-key-env', default='OPENAI_API_KEY', help='the NAME of the environment variable holding the key (LM Studio needs none)')
    p.add_argument('--runs', type=int, default=3)
    p.add_argument('--only', nargs='*', choices=list(ALL_PROMPTS), help='run only these prompts')
    p.add_argument('--extra', action='store_true', help='also run the ambiguity set (ambiguous-extension, bare-approve, amount-and-due-date); the D5 figure stays on the standard five')
    p.add_argument('--max-tokens', type=int, default=4096)
    p.add_argument('--price-in', type=float, help='USD per million prompt tokens (to record a cloud model\'s cost)')
    p.add_argument('--price-out', type=float, help='USD per million completion tokens')
    p.add_argument('--nudge', action='store_true', help='early-stop nudge: after an empty reply, or a turn with assessDecision/whatIsNeeded and no resolveDecision, send ONE automatic user message')
    p.add_argument('--instructions-extra', help='one line appended to the Staff instructions (an experiment)')
    p.add_argument('--instructions-file', help='a file replacing integrations/librechat/agents/instructions_staff.txt for this run (an experiment)')
    p.add_argument('--check-stack', action='store_true', help='start the scratch stack, list the Staff tools and stop (no model is called)')
    args = p.parse_args()
    if sys.version_info < (3, 10):
        sys.exit('Run the bench with the Lab\'s Python (3.10+ with mcp and httpx2): ~/Developer/nucleon-local/venv/bin/python')
    sys.exit(asyncio.run(main_async(args)))


if __name__ == '__main__':
    main()
