"""Scratch server for deploy/delegation_page_check.py. Fictional data only; never for real or shared records.

    delegation_check_server.py <db-file> <port> [assistant-url]

A fresh practice workspace holding the fictional delegation demonstration (prototype/delegation_demo.py: six customers, the fictional decision memory and the
fictional demo Owner policy as version 1), the test agent (mock mode), and the AI Agent testing account with a fresh fictional code. assistant-url (optional) is the
config's assistantUrl: the link the pages offer to the assistant; without it they offer none."""
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'prototype'))
from server import App, make_server, log, announce_codes   # noqa: E402
import delegation_demo   # noqa: E402

db, port = Path(sys.argv[1]), int(sys.argv[2])
assistant_url = sys.argv[3] if len(sys.argv) > 3 else None
for f in (db, Path(str(db) + '-wal'), Path(str(db) + '-shm')):
    f.unlink(missing_ok=True)
db.parent.mkdir(parents=True, exist_ok=True)
app = App(str(db), 'mock', None, sample_data=False, access_codes={'agent': 'agent-' + secrets.token_hex(8)}, assistant_url=assistant_url)
delegation_demo.seed(app, with_policy=True)
server = make_server(app, port, [])
log('URL: http://127.0.0.1:' + str(server.server_port))
announce_codes(app)
print('AGENT access code: ' + app.agent_code, flush=True)
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    server.server_close()
    app.db.close()
