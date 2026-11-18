"""Read-only checks of the Lab through the public URL: no sign-in, no codes, no tokens, no writes.

    python3 deploy/e2e_lab_check.py [https://nucleon.dracooz.top]

The Lab's records instance at
/lab/records/ (a session probe answers 200 "not signed in"), the MCP endpoint with a made-up bearer token (refused), and
the root site and the preview still answering 200.
"""
import json
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

results = []


def ok(name, condition, detail=''):
    results.append(bool(condition))
    print(('PASS ' if condition else 'FAIL ') + name.ljust(52) + ' ' + str(detail)[:160], flush=True)


def fetch(url, body=None, headers=None):
    request = Request(url, data=body, headers={'User-Agent': 'nucleon-e2e-lab', **(headers or {})})
    try:
        response = urlopen(request, timeout=30)
    except HTTPError as error:
        response = error
    with response:
        return response.status, response.read().decode('utf-8', 'replace')


def as_json(text):
    try:
        return json.loads(text)
    except ValueError:
        return {}


base = (sys.argv[1] if len(sys.argv) > 1 else 'https://nucleon.dracooz.top').rstrip('/')

status, body = fetch(base + '/lab/records/api/session')   # the records server answers a probe with 200, never 401
ok('/lab/records/api/session -> not signed in', status == 200 and as_json(body).get('authenticated') is False, status)

initialize = {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
              'params': {'protocolVersion': '2025-06-18', 'capabilities': {}, 'clientInfo': {'name': 'e2e_lab_check', 'version': '1'}}}
status, body = fetch(base + '/lab/mcp/', json.dumps(initialize).encode(),
                     {'Authorization': 'Bearer not-a-lab-token', 'Content-Type': 'application/json',
                      'Accept': 'application/json, text/event-stream'})
ok('/lab/mcp/ with a made-up bearer token is refused', status in (401, 403), status)

for path in ('/', '/preview/'):
    status, _ = fetch(base + path)
    ok(path + ' -> 200 (unchanged)', status == 200, status)

print('RESULT: %d/%d PASS' % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
