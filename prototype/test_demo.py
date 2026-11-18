"""Demo console (reset/restore), role sessions and static files. No real model is called."""
import json
import sqlite3
import threading
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from server import App, make_server
from test_agent import HTTPCase, Scripted, ISO_MESSAGE

FIXTURE = json.loads((Path(__file__).parent / 'fixtures.json').read_text())


class DemoCase(HTTPCase):
    demo = True

    def start(self, adapter=None, mode='mock', inline_wait=10, sample_data=True, **options):
        self.backups = Path(self.tmp.name) / 'backups'
        app = App(self.path, mode, adapter, inline_wait=inline_wait,
                  demo={'enabled': True, 'backupDir': str(self.backups)} if self.demo else None, sample_data=sample_data, **options)
        server = make_server(app, 0, self.origins)
        thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=.02), daemon=True)
        thread.start()
        self.apps.append((app, server, thread))
        self.app, self.base = app, 'http://127.0.0.1:' + str(server.server_port)
        self.cookies = {}
        for role in app.demo_codes:
            status, _, headers = self.call('/api/demo/login', {'accessCode': app.demo_codes[role]})
            self.assertEqual(status, 200)
            self.cookies[role] = headers['Set-Cookie'].split(';')[0]
        return app

    def console(self, path='console', body=None, role='operator'):
        return self.call('/api/demo/' + path, body, role)

    def count(self, table):
        return self.app.db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]


class ConsoleAccessTests(DemoCase):
    def test_console_needs_explicit_enabling(self):
        self.demo = False
        app = self.start()
        self.assertNotIn('operator', app.demo_codes)
        self.assertEqual(self.call('/api/demo/reset', {}, 'owner')[0], 404)

    def test_only_operator_uses_console_and_operator_does_no_case_work(self):
        self.start()
        self.assertEqual(self.console(role='staff')[0], 403)
        self.assertEqual(self.console('reset', {}, role='owner')[0], 403)
        status, state, _ = self.console()
        self.assertEqual((status, state['cases'], state['fixtureCurrent']), (200, 0, True))
        self.assertEqual(self.call('/api/requests', {'messageText': ISO_MESSAGE}, 'operator', 'k')[0], 403)
        self.assertEqual(self.call('/api/requests', role='operator')[0], 403)

    def test_console_does_not_reveal_server_paths(self):   # QA B9: the backup folder showed the server account's home folder
        self.start()
        self.console('start-empty', {})   # saves a backup first
        raw = json.dumps(self.console()[1])
        self.assertNotIn(str(self.backups), raw)
        self.assertNotIn(str(Path.home()), raw)
        self.assertTrue(self.console()[1]['backups'])   # backups are still listed by name


class ResetTests(DemoCase):
    def approved_case(self):
        r = self.create()
        self.assertEqual(self.decide(r)[0], 201)
        return r

    def test_reset_backs_up_then_restores_initial_state(self):
        app = self.start()
        codes = dict(app.demo_codes)
        self.approved_case()
        with app.lock, app.db:  # simulate drifted evidence
            app.save_doc({**FIXTURE, 'asOfDate': '2026-12-01'})
        status, result, _ = self.console('reset', {})
        self.assertEqual((status, result['reset']), (200, True))
        backup = self.backups / result['backup']
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        self.assertEqual(sqlite3.connect(backup).execute('SELECT COUNT(*) FROM requests').fetchone()[0], 1)
        self.assertEqual([self.count(t) for t in ('requests', 'events', 'runs', 'idempotency')], [0, 0, 0, 0])
        self.assertEqual(app.fixture(), FIXTURE)
        self.assertEqual(result['console']['lastReset']['backup'], result['backup'])
        # Sessions, codes and settings survive; the approved extension no longer moves DEMO-101's due date.
        self.assertEqual(app.demo_codes, codes)
        again = self.create(key='after-reset')
        self.assertEqual((again['status'], again['analysis']['snapshot']['currentEffectiveDueDate']), ('awaiting_owner', '2026-10-20'))

    def test_second_reset_on_clean_data_changes_nothing(self):
        self.start()
        self.approved_case()
        self.assertTrue(self.console('reset', {})[1]['reset'])
        second = self.console('reset', {})[1]
        self.assertEqual((second['reset'], second['backup']), (False, None))
        self.assertEqual(len(list(self.backups.iterdir())), 1)

    def test_restore_brings_back_reset_records(self):
        self.start()
        original = self.approved_case()
        backup = self.console('reset', {})[1]['backup']
        self.create(key='made-after-reset')
        status, result, _ = self.console('restore', {'backup': backup})
        self.assertEqual(status, 200)
        self.assertTrue(result['backup'].endswith('before-restore.sqlite3'))  # the replaced data is kept too
        restored = self.reopen(original)
        self.assertEqual((restored['status'], restored['decision']['outcome']), ('completed', 'approve'))
        self.assertEqual(self.count('requests'), 1)

    def test_a_restore_changes_the_dataset_id_too(self):
        self.start()
        self.approved_case()
        backup = self.console('reset', {})[1]['backup']
        dataset = lambda: self.call('/api/tools', None, 'owner')[1]['datasetId']
        before = dataset()
        self.assertEqual(self.console('restore', {'backup': backup})[0], 200)
        self.assertNotEqual(dataset(), before)

    def test_restore_keeps_drifted_data_and_the_database_stays_in_wal_mode(self):
        app = self.start()
        self.approved_case()
        backup = self.console('reset', {})[1]['backup']
        with app.lock, app.db:  # no cases, but the invoice data differs from the starting state
            app.save_doc({**FIXTURE, 'asOfDate': '2026-12-01'})
        result = self.console('restore', {'backup': backup})[1]
        self.assertTrue(result['backup'], 'the drifted data must be saved before it is replaced')
        self.assertEqual(app.db.execute('PRAGMA journal_mode').fetchone()[0], 'wal')
        self.assertEqual(sorted(p.name for p in self.backups.iterdir() if not p.name.endswith('.sqlite3')), [])

    def test_relative_backup_folder_sits_next_to_the_database(self):
        app = App(Path(self.tmp.name) / 'rel.sqlite3', demo={'enabled': True, 'backupDir': 'saved'})
        try:
            self.assertEqual(app.backup_dir, Path(self.tmp.name) / 'saved')
        finally:
            app.close()

    def test_restore_accepts_only_listed_backups(self):
        self.start()
        self.approved_case()
        self.console('reset', {})
        for name in ('../demo.sqlite3', 'missing.sqlite3', '/etc/passwd', None):
            status, err, _ = self.console('restore', {'backup': name})
            self.assertEqual((status, err.get('field')), (404, 'backup'), name)

    def test_late_model_result_cannot_recreate_cleared_cases(self):
        gate = threading.Event()
        gated = Scripted(gate=gate)
        self.start(gated, mode='live', inline_wait=0)
        self.create()
        self.wait_calls(gated)  # the model is mid-inference
        self.assertTrue(self.console('reset', {})[1]['reset'])
        gate.set()
        time.sleep(.5)
        self.assertEqual([self.count(t) for t in ('requests', 'events', 'runs')], [0, 0, 0])

    def test_restore_resumes_work_that_was_pending(self):
        gate = threading.Event()
        gated = Scripted(gate=gate)
        self.start(gated, mode='live', inline_wait=0)
        pending = self.create()
        self.wait_calls(gated)
        backup = self.console('reset', {})[1]['backup']  # backup holds an analysing case with a running run
        gate.set()
        time.sleep(.3)
        self.console('restore', {'backup': backup})
        final = self.wait_status(pending)
        self.assertEqual(final['status'], 'awaiting_owner')
        self.assertEqual([x['status'] for x in final['runs']], ['interrupted', 'finished'])


class DecisionRecordTests(DemoCase):
    def test_approved_extension_is_calculated_by_the_server(self):
        self.start()
        r = self.create()
        changed = self.decide(r, approved='2026-11-03')[1]
        self.assertEqual(changed['approvedExtensionDays'], 14)   # due Tue 20 Oct to Tue 3 Nov
        other = self.create('Could we pay invoice DEMO-202 on 2026-11-20 instead?', key='second')
        self.assertIsNone(self.decide(other, 'decline', None, key='d2')[1]['approvedExtensionDays'])


class RoleSessionTests(DemoCase):
    def both(self):
        return self.cookies['staff'] + '; ' + self.cookies['owner']

    def test_one_browser_can_hold_staff_and_owner_sessions(self):
        self.start()
        r = self.create()
        status, session, _ = self.call('/api/session', headers={'Cookie': self.both()})
        self.assertEqual((status, session['authenticated'], session['signedIn']), (200, False, ['owner', 'staff']))
        status, session, _ = self.call('/api/session', headers={'Cookie': self.both(), 'X-Nucleon-Role': 'owner'})
        self.assertEqual(session['role'], 'owner')
        self.assertEqual(self.call('/api/requests', headers={'Cookie': self.both()})[0], 400)  # which role is acting?
        body = {'expectedRequestVersion': r['version'], 'analysisId': r['analysis']['id'], 'evidenceVersion': r['analysis']['snapshot']['evidenceVersion'],
                'outcome': 'approve', 'approvedDueDate': '2026-10-30', 'reason': 'ok'}
        path = '/api/requests/' + r['id'] + '/decisions'
        self.assertEqual(self.call(path, body, key='d1', headers={'Cookie': self.both(), 'X-Nucleon-Role': 'staff'})[0], 403)
        self.assertEqual(self.call(path, body, key='d1', headers={'Cookie': self.both(), 'X-Nucleon-Role': 'owner'})[0], 201)

    def test_role_header_cannot_borrow_another_roles_cookie(self):
        self.start()
        forged = self.cookies['staff'].replace('nucleon_staff=', 'nucleon_owner=')
        status, session, _ = self.call('/api/session', headers={'Cookie': forged, 'X-Nucleon-Role': 'owner'})
        self.assertEqual((status, session['authenticated']), (200, False))

    def test_sign_out_ends_every_role_in_this_browser_and_no_other_browser(self):
        for acting in ('staff', 'owner'):   # whichever role is selected when Sign out is pressed (QA B1, both directions)
            self.start()
            _, _, other = self.call('/api/demo/login', {'accessCode': self.app.demo_codes['owner']})   # a teammate's browser
            teammate = other['Set-Cookie'].split(';')[0]
            status, body, headers = self.call('/api/demo/logout', {}, headers={'Cookie': self.both(), 'X-Nucleon-Role': acting})
            self.assertEqual((status, body['signedOut']), (200, ['owner', 'staff']))
            cleared = headers.get_all('Set-Cookie')
            self.assertEqual(sorted(c.split('=')[0] for c in cleared), ['nucleon_owner', 'nucleon_staff'])
            self.assertTrue(all('Max-Age=0' in c for c in cleared))
            self.assertEqual(self.call('/api/session', headers={'Cookie': self.both()})[1]['signedIn'], [])   # the old cookies no longer work
            self.assertTrue(self.call('/api/session', headers={'Cookie': teammate, 'X-Nucleon-Role': 'owner'})[1]['authenticated'])

    def test_sign_out_without_a_role_header_still_signs_out(self):
        self.start()
        status, body, _ = self.call('/api/demo/logout', {}, headers={'Cookie': self.both()})
        self.assertEqual((status, body['signedOut']), (200, ['owner', 'staff']))
        self.assertEqual(self.call('/api/demo/logout', {})[1]['signedOut'], [])   # nothing to end is not an error

    def test_an_instance_under_a_path_prefix_uses_its_own_cookie_names_and_path(self):   # /preview/ behind the proxy
        self.start(cookie_prefix='nucleonp_', cookie_path='/preview')
        status, _, headers = self.call('/api/demo/login', {'accessCode': self.app.demo_codes['staff']})
        self.assertEqual(status, 200)
        self.assertRegex(headers['Set-Cookie'], r'^nucleonp_staff=[\w-]+; HttpOnly; SameSite=Strict; Path=/preview$')
        staff = headers['Set-Cookie'].split(';')[0]
        root = staff.replace('nucleonp_', 'nucleon_')   # the root instance's cookie name is not this instance's
        self.assertFalse(self.call('/api/session', headers={'Cookie': root})[1]['authenticated'])
        self.assertTrue(self.call('/api/session', headers={'Cookie': staff})[1]['authenticated'])
        status, body, headers = self.call('/api/demo/logout', {}, headers={'Cookie': staff})
        self.assertEqual((status, body['signedOut']), (200, ['staff']))
        self.assertEqual(headers.get_all('Set-Cookie'), ['nucleonp_staff=; HttpOnly; SameSite=Strict; Path=/preview; Max-Age=0'])

    def test_a_code_for_another_role_is_refused_at_a_role_prompt(self):
        self.start()
        status, body, headers = self.call('/api/demo/login', {'accessCode': self.app.demo_codes['staff'], 'role': 'owner'})
        self.assertEqual((status, body['error'], body['field']), (403, 'WRONG_ROLE_CODE', 'accessCode'))
        self.assertIn('staff', body['message'])
        self.assertIsNone(headers.get('Set-Cookie'))   # no session is created for the other role
        status, actor, _ = self.call('/api/demo/login', {'accessCode': self.app.demo_codes['owner'], 'role': 'owner'})
        self.assertEqual((status, actor['role']), (200, 'owner'))
        self.assertEqual(self.call('/api/demo/login', {'accessCode': self.app.demo_codes['owner'], 'role': 'boss'})[0], 400)


class SampleDataTests(DemoCase):
    """Fictional sample records appear only when explicitly asked for, and never replace other records."""

    def store(self, records):
        db = sqlite3.connect(self.path)
        db.execute('CREATE TABLE fixtures (id INTEGER PRIMARY KEY, data TEXT NOT NULL)')
        db.execute('INSERT INTO fixtures VALUES (1, ?)', (json.dumps(records),))
        db.commit()
        db.close()

    def test_an_empty_database_stays_empty_by_default(self):
        default = App(self.path)
        self.assertIsNone(default.fixture())
        default.close()
        self.demo = False
        app = self.start(sample_data=False)
        self.assertEqual(app.db.execute('SELECT COUNT(*) FROM fixtures').fetchone()[0], 0)
        status, session, _ = self.call('/api/session', role='staff')
        self.assertEqual((status, session['hasRecords'], session['dataMode']), (200, False, None))
        status, error, _ = self.call('/api/requests', {'messageText': ISO_MESSAGE}, 'staff', 'k1')
        self.assertEqual((status, error['error']), (409, 'NO_RECORDS'))
        self.assertEqual(self.count('requests'), 0)

    def test_sample_data_loads_when_explicitly_enabled(self):
        self.demo = False
        app = self.start(sample_data=True)
        self.assertEqual(app.fixture(), FIXTURE)
        self.assertTrue(self.call('/api/session', role='staff')[1]['hasRecords'])

    def test_records_that_are_not_the_fictional_sample_are_never_replaced(self):
        own = {'dataMode': 'real', 'version': 1, 'asOfDate': '2026-10-16', 'businessTimezone': 'Australia/Sydney',
               'customers': [], 'invoices': [], 'notes': []}
        self.store(own)
        self.demo = False
        app = self.start(sample_data=True)   # even with the sample enabled, an older version number is not a reason to overwrite
        self.assertEqual(app.fixture(), own)

    def test_an_older_fictional_sample_is_still_upgraded(self):
        self.store({**FIXTURE, 'version': 1, 'invoices': FIXTURE['invoices'][:1]})
        self.demo = False
        self.assertEqual(self.start(sample_data=False).fixture(), FIXTURE)

    def test_the_operator_loads_the_sample_into_an_empty_database_with_reset(self):
        app = self.start(sample_data=False)
        status, state, _ = self.console()
        self.assertEqual((status, state['asOfDate'], state['fixtureCurrent']), (200, None, False))
        self.assertTrue(self.console('reset', {})[1]['reset'])
        self.assertEqual(app.fixture(), FIXTURE)


class StaticFileTests(DemoCase):
    def get(self, path):
        try:
            response = urlopen(Request(self.base + path), timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, response.headers, response.read()

    def test_frontend_files_and_headers(self):
        self.start()
        status, headers, page = self.get('/')
        self.assertEqual(status, 200)
        self.assertIn("script-src 'self'", headers['Content-Security-Policy'])
        self.assertNotIn(b'<script>', page)  # scripts are files, so the policy can forbid inline code
        for path, kind in (('/static/app.css', 'text/css'), ('/static/core.js', 'text/javascript'), ('/static/customers.js', 'text/javascript')):
            status, headers, _ = self.get(path)
            self.assertEqual((status, headers['Content-Type'].split(';')[0]), (200, kind))
        for path in ('/static/../server.py', '/static/%2e%2e/server.py', '/static/missing.js', '/static/app.py'):
            self.assertEqual(self.get(path)[0], 404, path)

    def test_static_files_are_versioned_in_the_page_and_cacheable_by_version(self):
        # The page links static/app.css?v=<content hash>; that address may be cached for a year, the bare one revalidates (no-cache, ETag → 304).
        self.start()
        status, headers, page = self.get('/')
        import re
        links = re.findall(rb'static/([a-z0-9/.-]+)\?v=([0-9a-f]{12})', page)
        self.assertGreaterEqual(len(links), 10, page[:400])
        self.assertIn(b'static/app.css?v=', page)
        name, version = links[0]
        status, headers, _ = self.get('/static/%s?v=%s' % (name.decode(), version.decode()))
        self.assertEqual((status, headers['Cache-Control']), (200, 'public, max-age=31536000, immutable'))
        status, headers, _ = self.get('/static/%s?v=stale' % name.decode())
        self.assertEqual((status, headers['Cache-Control']), (200, 'no-cache'))
        status, headers, _ = self.get('/static/%s' % name.decode())
        self.assertEqual((status, headers['Cache-Control'], headers['ETag']), (200, 'no-cache', '"%s"' % version.decode()))
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError
        try:
            response = urlopen(Request(self.base + '/static/%s' % name.decode(), headers={'If-None-Match': headers['ETag']}))
        except HTTPError as error:
            response = error
        with response:
            self.assertEqual(response.status, 304)

    def test_a_page_load_burst_of_connections_is_never_refused(self):
        # Behind the proxy one page load opens a connection per file at the same instant (8 for the redesigned page). With the
        # default listen queue of 5, some were reset and the proxy answered 502 (deployment of 18 October).
        import socket
        import threading
        self.start()
        port, failed = int(self.base.rsplit(':', 1)[1]), []
        for _ in range(5):
            barrier = threading.Barrier(16)

            def one():
                barrier.wait()
                try:
                    with socket.create_connection(('127.0.0.1', port), timeout=5) as s:
                        s.sendall(b'GET /static/core.js HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n')
                        if b' 200 ' not in s.recv(64):
                            failed.append('status')
                except OSError as error:
                    failed.append(type(error).__name__)
            threads = [threading.Thread(target=one) for _ in range(16)]
            [t.start() for t in threads]
            [t.join() for t in threads]
        self.assertEqual(failed, [])

