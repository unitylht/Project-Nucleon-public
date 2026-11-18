"""Scratch server for the browser regression check (deploy/ui_check.js). Fictional data only; never for real or shared records.

    ui_check_server.py <db-file> <port> [--fault-fallback]

A fresh practice workspace with the fictional sample, the demo console on (backups next to the database), and the
deterministic test agent (mock mode). With --fault-fallback the AI is switched off and the code-only fallback fails once for
a message containing "[fallback-fault]", so a browser can see the failed-preparation state and use "Prepare again". The
fault is a test seam in this launcher only; the application code is unchanged.
"""
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'prototype'))
from server import App, make_server, log, announce_codes   # noqa: E402

db, port = Path(sys.argv[1]), int(sys.argv[2])
fault = '--fault-fallback' in sys.argv[3:]
for f in (db, Path(str(db) + '-wal'), Path(str(db) + '-shm')):
    f.unlink(missing_ok=True)
db.parent.mkdir(parents=True, exist_ok=True)

if fault:
    original, failed = App.fallback, set()

    def fallback(self, r, run, failure, outcome=None):
        if '[fallback-fault]' in r['intake']['text'] and r['id'] not in failed:
            failed.add(r['id'])
            raise RuntimeError('simulated fallback fault (ui_check_server.py)')
        return original(self, r, run, failure, outcome)
    App.fallback = fallback

app = App(str(db), 'unavailable' if fault else 'mock', None, demo={'enabled': True, 'backupDir': str(db.parent / (db.stem + '-backups'))},
          sample_data=True, access_codes={'agent': 'agent-' + secrets.token_hex(8)})   # the AI Agent testing account, with a fresh fictional code
server = make_server(app, port, [])
log('URL: http://127.0.0.1:' + str(server.server_port) + (' | fallback fault on' if fault else ''))
announce_codes(app)   # the access codes, then the service codes the Lab's MCP server signs in with
print('AGENT access code: ' + app.agent_code, flush=True)
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    server.server_close()
    app.db.close()
