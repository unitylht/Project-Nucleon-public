"""The scratch records server the MCP tests run against (deploy/ui_check_server.py: the fictional sample, the demo console) on a
free port. A test module re-exports setUpModule and tearDownModule from here (unittest runs only a test module's own). Fictional data only."""
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx2


ROOT = Path(__file__).resolve().parents[2]
RECORDS_PY = Path.home() / 'srv/nucleon/runtime/python-3.12.14/bin/python3'
SERVER = {}


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def setUpModule():
    SERVER['dir'] = tempfile.mkdtemp(prefix='lab-test-')
    port = free_port()
    SERVER['url'] = 'http://127.0.0.1:' + str(port)
    python = str(RECORDS_PY) if RECORDS_PY.exists() else sys.executable
    log = Path(SERVER['dir']) / 'records.log'
    with open(log, 'w') as out:   # a file, not a pipe: the server's log never fills a buffer nobody reads
        SERVER['proc'] = proc = subprocess.Popen([python, str(ROOT / 'deploy/ui_check_server.py'), SERVER['dir'] + '/records.db', str(port)],
                                                 stdout=out, stderr=subprocess.STDOUT)
    codes, deadline = {}, time.monotonic() + 30
    while len(codes) < 4:
        if proc.poll() is not None or time.monotonic() > deadline:
            raise RuntimeError('the scratch records server did not start: ' + log.read_text())
        time.sleep(0.1)
        codes = {role.lower(): code for role, code in (line.split(' access code: ') for line in log.read_text().splitlines() if ' access code: ' in line)}
    with httpx2.Client(base_url=SERVER['url'], timeout=30) as c:
        for role in ('owner', 'staff'):
            r = c.post('/api/demo/login', json={'accessCode': codes[role]})
            r.raise_for_status()
            SERVER[role] = 'nucleon_' + role + '=' + r.cookies['nucleon_' + role]
    with httpx2.Client(base_url=SERVER['url'], timeout=30) as c:
        r = c.post('/api/demo/login', json={'accessCode': codes['agent']})   # the AI Agent: one login, a session for each role
        r.raise_for_status()
        SERVER['agent'] = '; '.join(n + '=' + v for n, v in r.cookies.items())
    with httpx2.Client(base_url=SERVER['url'], timeout=30) as c:
        r = c.post('/api/tools/openRequest', headers={'Cookie': SERVER['staff'], 'Idempotency-Key': 'lab-test-case'},
                   json={'args': {'text': 'case'}, 'message': 'Hi, Harbour Demo Logistics here. Could we pay invoice DEMO-202 on 2026-11-20 instead?'})
        SERVER['case'] = r.json()['result']['opened']['id']


def tearDownModule():
    SERVER['proc'].terminate()
    SERVER['proc'].wait(10)
