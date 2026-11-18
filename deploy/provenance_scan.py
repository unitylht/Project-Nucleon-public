"""Read-only: attribution produced by the revert rule before f95bbc0, in a COPY of a database (docs/qa/FINDINGS-DISPOSITION.md, R5).

    python3 deploy/provenance_scan.py <copy of a database>

Reports, as JSON:
  credited       records (current or earlier versions) credited to a later import when the import they came from was reverted
                 ("confirmed by a later import"), with that import's row status and whether its values equal the record's;
  dangling       records still active but credited to an import that was itself reverted;
  keptConflicts  conflicting rows a person rejected by keeping the recorded value, with the record's own source.
It writes nothing and rewrites no provenance. Make the copy with the SQLite backup API (or nucleonctl clone-db), never on the live file."""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'prototype'))
import importer   # noqa: E402
import server     # noqa: E402


def scan(path):
    app = server.App.__new__(server.App)   # no startup recovery: nothing is migrated or written
    app.db = sqlite3.connect('file:' + str(path) + '?mode=ro', uri=True)
    app.clock = None
    tables = {n for (n,) in app.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'batches' not in tables:
        return {'skip': 'no imports (before Slice 2)'}
    batches = {b['id']: b for b in (json.loads(d) for (d,) in app.db.execute('SELECT data FROM batches'))}
    doc = app.fixture() if 'meta' in tables else None
    if doc is None and 'fixtures' in tables:   # Slice 2 kept the records as one document
        row = app.db.execute('SELECT data FROM fixtures ORDER BY id DESC LIMIT 1').fetchone()
        doc = json.loads(row[0]) if row else None
    if doc is None:
        return {'skip': 'no records', 'batches': len(batches)}
    out = {'batches': len(batches), 'applied': sum(b.get('status') == 'applied' for b in batches.values()),
           'reverted': sum(b.get('status') == 'reverted' for b in batches.values()), 'credited': [], 'dangling': [], 'keptConflicts': []}
    for kind in ('invoices', 'payments'):
        for record in doc.get(kind, []):
            label = record.get('reference') or record.get('receivedDate')
            fields = importer.INVOICE_VALUES if kind == 'invoices' else ('receivedDate', 'amount', 'reference')
            versions = [(h['setBy'], h['values'], 'earlier version') for h in record.get('history', []) if h.get('setBy')]
            versions.append((record.get('setBy') or {}, {k: record.get(k) for k in fields}, 'current'))
            for set_by, values, which in versions:
                if 'confirmed by a later import' not in (set_by.get('note') or ''):
                    continue
                credited = batches.get(set_by.get('batchId'))
                row = importer.listing({**record, **values}, {**credited, 'status': 'applied'} if credited else None)
                differ = row and row.get('values') and importer.differences({**record, **values}, row)
                verdict = 'row missing' if row is None else row['status'] + (', values differ: ' + ', '.join(differ) if differ else ', values equal')
                out['credited'].append({'kind': kind, 'record': label, 'which': which, 'creditedTo': set_by.get('batchId'),
                                        'creditedImportStatus': (credited or {}).get('status'), 'row': verdict})
            source = (record.get('setBy') or {}).get('batchId')
            if record.get('status', 'active') == 'active' and source and (batches.get(source) or {}).get('status') == 'reverted':
                out['dangling'].append({'kind': kind, 'record': label, 'creditedTo': source})
            for later in record.get('confirmedBy', []):
                row = importer.listing(record, batches.get(later))
                if row and row['status'] == 'conflict':
                    out['keptConflicts'].append({'kind': kind, 'record': label, 'conflict': later, 'fields': row.get('conflictFields'),
                                                 'source': source, 'sourceStatus': (batches.get(source) or {}).get('status')})
    return out


if __name__ == '__main__':
    print(json.dumps(scan(sys.argv[1]), indent=1))
