"""A scratch records server on a COPY of an existing database (the three sqlite files copied with their timestamps), fresh throwaway codes, mock agent mode.
    copy_server.py <code-root> <source-db> <work-dir> <port>
Nothing is written to the source. The codes are printed to stdout (the caller's private log)."""
import shutil, sys
from pathlib import Path

root, src, work, port = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), int(sys.argv[4])
sys.path.insert(0, str(root / 'prototype'))
from server import App, make_server, log, announce_codes   # noqa: E402

work.mkdir(parents=True, exist_ok=True)
db = work / 'copy.sqlite3'
for suffix in ('', '-wal', '-shm'):
    s = Path(str(src) + suffix)
    if s.exists():
        shutil.copy2(s, str(db) + suffix)
app = App(str(db), 'mock', None, sample_data=False, verbose=False)
server = make_server(app, port, [])
log('URL: http://127.0.0.1:' + str(server.server_port))
announce_codes(app)
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    server.server_close()
    app.db.close()
