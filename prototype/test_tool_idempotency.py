"""Idempotency of the desk tool surface (POST api/tools/<name>), the records' side of MCP write safety: an act or prepare tool, and
assessRequest when a key is sent, runs once per key, scoped to actor, role, tool and key. The claim is committed before the tool runs
(pending), the connection marks it applied in the same transaction as the first business write, and the answer is kept after (done); so a
retry replays, is told it is running, or is told the answer is unavailable, and never repeats a change that committed. A refusal that changed
nothing is not kept. All data is fictional; no real model is called."""
import json
import sqlite3
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from model_adapter import AdapterError
from server import AGENT_ID, AGENT_NAME, TOOL_OPS_KEEP_DAYS, APIError, App, DeskTools, OpConnection, fingerprint
from test_assessment import AssessmentCase
from test_helpers import Recording
from test_tool_surface import Unreachable

OWNER = {'role': 'owner', 'id': 'owner_demo'}
STAFF = {'role': 'staff', 'id': 'staff_demo'}
AGENT = {'id': AGENT_ID, 'name': AGENT_NAME, 'kind': 'agent', 'businessId': 'fictional_business'}


class Crash(BaseException):
    """What a stopped process looks like to the code that was running: nothing after it runs."""


class Gate(Recording):
    """The mock, with the suggestion step held until released: the model is being read while the lock is free."""

    def __init__(self):
        super().__init__()
        self.entered, self.release = threading.Event(), threading.Event()

    def respond(self, task, messages, tools=None, schema=None, timeout=None):
        if task == 'suggest':
            self.entered.set()
            self.release.wait(10)
        return super().respond(task, messages, tools, schema, timeout)


class ToolOpsCase(AssessmentCase):
    def rows(self):
        """{key: state} of the tool operations in record_ops."""
        return dict(self.app.db.execute("SELECT key, state FROM record_ops WHERE key LIKE '%:tool:%'").fetchall())

    def stored(self):
        """The case and its events as stored."""
        with self.app.lock:
            return self.app.get(self.r['id']), self.app.history(self.r['id'])

    def events(self, kind, field='version'):
        with self.app.lock:
            return [e['data'].get(field) for e in self.app.history(self.r['id']) if e['kind'] == kind]

    def prepared(self, key='p1', days=14, role='owner'):
        return self.tool('prepareDecision', role, key, message='approve ' + str(days) + ' days', outcome='approve', days=days, requestId=self.r['id'])

    def prepared_body(self, days=14):
        return {'args': {'outcome': 'approve', 'days': days, 'requestId': self.r['id']}, 'message': 'approve ' + str(days) + ' days'}


class RetryTests(ToolOpsCase):
    def test_a_duplicate_key_makes_one_change_and_replays_the_same_result(self):
        status, first, _ = self.prepared()
        self.assertEqual((status, first['ok'], 'replayed' in first), (200, True, False))
        status, again, _ = self.prepared()
        self.assertEqual((status, again['replayed']), (200, True))   # beside the result, not in it
        self.assertEqual({k: v for k, v in again.items() if k != 'replayed'}, first)
        self.assertNotIn('replayed', again['result'])
        self.assertEqual(self.events('decision.prepared'), [1])
        self.assertEqual(self.case()['preparedDecision']['version'], 1)
        self.assertEqual(list(self.rows().values()), ['done'])

    def test_a_lost_response_is_answered_from_the_records_not_run_again(self):
        with self.app.lock:
            first = self.app.tool_call(OWNER, 'prepareDecision', self.prepared_body(), 'lost-1')   # the caller never saw this
        status, again, _ = self.prepared('lost-1')
        self.assertEqual((status, again['replayed'], again['result']), (200, True, first['result']))
        self.assertEqual(self.events('decision.prepared'), [1])

    def test_the_same_key_with_other_input_is_refused_and_changes_nothing(self):
        self.prepared('k1', 14)
        before = self.stored()
        status, body, _ = self.prepared('k1', 10)
        self.assertEqual((status, body['error']), (409, 'KEY_REUSED'))
        self.assertEqual(self.stored(), before)
        p = self.case()['preparedDecision']
        self.assertEqual((p['version'], p['days']), (1, 14))
        self.assertEqual(self.prepared('k1', 14)[1]['replayed'], True)   # the original is untouched

    def test_a_new_key_with_the_same_input_is_a_new_operation_and_the_business_rules_decide(self):
        self.prepared('k1')
        self.assertEqual(self.prepared('k2')[1]['result']['prepared']['version'], 2)   # not deduplicated by its arguments
        self.assertEqual(self.events('decision.prepared'), [1, 2])
        done = self.ok('withdrawPreparation', key='w1', requestId=self.r['id'])
        self.assertTrue(done['withdrawn'])
        second = self.ok('withdrawPreparation', key='w2', requestId=self.r['id'])   # refused by the business (nothing to withdraw), not by the key
        self.assertEqual((second['withdrawn'], second['note']), (False, 'No prepared decision is waiting.'))
        self.assertEqual(self.events('decision.withdrawn'), [2])

    def test_assess_request_with_a_key_runs_once_and_without_one_runs_every_time(self):
        self.set_limits()
        first = self.tool('assessRequest', 'staff', 'a1', requestId=self.r['id'])[1]
        version = first['result']['version']
        again = self.tool('assessRequest', 'staff', 'a1', requestId=self.r['id'])[1]
        self.assertEqual((again['replayed'], again['result']['version']), (True, version))
        self.assertEqual(self.assess()['version'], version + 1)   # no key: as before, a new version each time
        self.assertEqual(self.assess()['version'], version + 2)
        self.assertEqual(self.tool('assessRequest', 'staff', 'a2', requestId=self.r['id'])[1]['result']['version'], version + 3)   # a new key: a new operation
        self.assertEqual(self.tool('assessRequest', 'staff', 'a1', requestId=self.r['id'])[1]['result']['version'], version)   # still the first one's answer
        self.assertEqual(sorted(self.rows().values()), ['done', 'done'])   # the keyless calls left no row

    def test_a_key_that_is_too_long_or_missing_on_a_once_tool_is_400_and_reads_need_none(self):
        for key in (None, 'k' * 161):
            status, body, _ = self.prepared(key)
            self.assertEqual((status, body['error']), (400, 'IDEMPOTENCY_REQUIRED'))
        self.assertEqual(self.rows(), {})
        self.assertEqual(self.tool('assessRequest', 'staff', None, requestId=self.r['id'])[0], 200)

    def test_reads_with_or_without_a_key_create_no_rows(self):
        customer = self.bayside['id']
        for key in (None, 'r1'):
            for name, args in (('customerOverview', {'customerId': customer}), ('invoices', {'customerId': customer, 'which': 'all'}), ('workQueue', {})):
                self.assertTrue(self.ok(name, 'staff', key, **args))
        self.assertEqual(self.app.db.execute('SELECT COUNT(*) FROM record_ops').fetchone()[0], self.ops_before)

    def setUp(self):
        super().setUp()
        self.ops_before = self.app.db.execute('SELECT COUNT(*) FROM record_ops').fetchone()[0]


class ScopeTests(ToolOpsCase):
    def test_an_owner_key_sent_by_staff_is_refused_before_the_claim_and_no_privileged_result_leaks(self):
        self.prepared('shared')
        status, body, _ = self.prepared('shared', role='staff')
        self.assertEqual((status, body['error']), (403, 'FORBIDDEN'))
        self.assertNotIn('result', body)
        status, body, _ = self.tool('withdrawPreparation', 'staff', 'shared', requestId=self.r['id'])
        self.assertEqual((status, body['error']), (403, 'FORBIDDEN'))
        self.assertEqual(len(self.rows()), 1)

    def test_the_ai_agent_has_one_id_for_both_roles_so_the_role_is_part_of_the_scope(self):
        self.set_limits()
        body = {'args': {'requestId': self.r['id']}, 'message': 'assess it'}
        as_owner = {**AGENT, 'role': 'owner'}
        as_staff = {**AGENT, 'role': 'staff'}
        with self.app.lock:
            owner = self.app.tool_call(as_owner, 'assessRequest', body, 'K-agent-1')
            staff = self.app.tool_call(as_staff, 'assessRequest', body, 'K-agent-1')   # the same key and body
            owner_again = self.app.tool_call(as_owner, 'assessRequest', body, 'K-agent-1')
        self.assertNotIn('replayed', staff)   # run fresh as staff, not the owner's stored answer
        self.assertNotEqual(staff['result'], owner['result'])
        self.assertEqual(staff['result']['version'], owner['result']['version'] + 1)
        self.assertEqual(self.assess()['recommendation'], staff['result']['recommendation'])   # the staff view (staff_plain), as any staff member gets it
        self.assertEqual((owner_again['replayed'], owner_again['result']), (True, owner['result']))
        self.assertEqual(sorted(k.split(':tool:')[0] for k in self.rows()), [AGENT_ID + ':owner', AGENT_ID + ':staff'])

    def test_two_people_with_the_same_key_text_do_not_share_an_operation(self):
        self.prepared('same')
        self.assertEqual(self.prepared('same', 14)[1]['replayed'], True)
        with self.app.lock:   # another actor of the same role: its own operation
            other = self.app.tool_call({'role': 'owner', 'id': 'owner_two'}, 'prepareDecision', self.prepared_body(), 'same')
        self.assertNotIn('replayed', other)
        self.assertEqual(self.events('decision.prepared'), [1, 2])


class ConcurrencyTests(ToolOpsCase):
    def test_a_model_calling_tool_asked_again_while_the_model_reads_is_in_progress_and_one_suggestion_is_kept(self):
        self.app.model_adapter = gate = Gate()
        body = {'args': {'requestId': self.r['id']}, 'message': 'suggest'}
        before = self.events('suggestion.updated')
        out = []
        first = threading.Thread(target=lambda: out.append(self.app.tool_call(OWNER, 'requestSuggestion', body, 'sg-1')))
        first.start()
        self.assertTrue(gate.entered.wait(10))
        self.assertEqual(list(self.rows().values()), ['pending'])   # claimed and committed before the model was asked
        with self.assertRaises(APIError) as caught:   # the lock is free while the model reads, so this one gets to the claim
            self.app.tool_call(OWNER, 'requestSuggestion', body, 'sg-1')
        self.assertEqual((caught.exception.status, caught.exception.code), (409, 'OPERATION_IN_PROGRESS'))
        status, refused, _ = self.tool('requestSuggestion', 'owner', 'sg-1', requestId=self.r['id'], message='suggest')   # and over HTTP
        self.assertEqual((status, refused['error']), (409, 'OPERATION_IN_PROGRESS'))
        gate.release.set()
        first.join(10)
        self.assertTrue(out[0]['ok'], out)
        self.assertEqual(len(self.events('suggestion.updated')), len(before) + 1)   # exactly one new version
        again = self.app.tool_call(OWNER, 'requestSuggestion', body, 'sg-1')
        self.assertEqual((again['replayed'], again['result']), (True, out[0]['result']))
        self.assertEqual(len(self.events('suggestion.updated')), len(before) + 1)
        self.assertEqual(list(self.rows().values()), ['done'])

    def test_a_locked_tool_sent_twice_at_once_makes_one_change(self):
        start, out = threading.Barrier(2), []

        def call():
            start.wait()
            out.append(self.app.tool_call(OWNER, 'prepareDecision', self.prepared_body(), 'twin'))
        threads = [threading.Thread(target=call) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(15)
        self.assertEqual(len(out), 2)
        self.assertEqual(sorted('replayed' in x for x in out), [False, True])
        self.assertEqual(out[0]['result'], out[1]['result'])
        self.assertEqual(self.events('decision.prepared'), [1])

    def test_a_case_being_opened_meets_in_progress_not_a_second_case(self):
        said = 'Hi, Bayside Café here. Could we pay invoice DEMO-502 on 2026-11-10 instead?'
        body, retried, wait = {'args': {'text': said}, 'message': said}, [], App.wait_settled
        before = len(self.app.records())

        def waiting(app, request_id, timeout):   # the retry arrives while the first waits for its case to be prepared
            if not retried:
                retried.append(None)
                try:
                    app.tool_call(STAFF, 'openRequest', body, 'open-1')
                except APIError as error:
                    retried.append((error.status, error.code))
            return wait(app, request_id, timeout)
        with mock.patch.object(App, 'wait_settled', waiting):
            opened = self.app.tool_call(STAFF, 'openRequest', body, 'open-1')
        self.assertEqual(retried[1], (409, 'OPERATION_IN_PROGRESS'))
        self.assertTrue(opened['ok'])
        self.assertEqual(len(self.app.records()), before + 1)
        self.assertEqual(self.app.tool_call(STAFF, 'openRequest', body, 'open-1')['result']['opened']['id'], opened['result']['opened']['id'])


class FailureTests(ToolOpsCase):
    def test_an_error_inside_the_business_transaction_rolls_back_and_the_retry_runs_once(self):
        with mock.patch.object(App, 'event', side_effect=RuntimeError('disk full')), self.assertRaises(RuntimeError):
            self.app.tool_call(OWNER, 'prepareDecision', self.prepared_body(), 'boom')
        self.assertEqual(self.rows(), {})   # the claim was dropped: nothing had committed
        self.assertNotIn('preparedDecision', self.case())
        self.assertEqual(self.events('decision.prepared'), [])
        status, body, _ = self.prepared('boom')
        self.assertEqual((status, body['ok'], 'replayed' in body), (200, True, False))
        self.assertEqual(self.prepared('boom')[1]['replayed'], True)
        self.assertEqual(self.events('decision.prepared'), [1])

    def test_a_crash_after_the_change_committed_and_before_the_answer_is_kept_is_never_run_again(self):
        with mock.patch.object(App, 'tool_finish', side_effect=Crash()), self.assertRaises(Crash):
            self.app.tool_call(OWNER, 'prepareDecision', self.prepared_body(), 'crash')
        self.assertEqual(list(self.rows().values()), ['applied'])   # marked by the same transaction as the preparation
        self.assertEqual(self.events('decision.prepared'), [1])
        for restarted in (False, True):   # in the same boot, and in the next one
            if restarted:
                self.restart(mode='live', adapter=self.model)
            status, body, _ = self.prepared('crash')
            self.assertEqual((status, body['error']), (409, 'OPERATION_RESULT_UNAVAILABLE'))
            self.assertIn('Check the records with a read tool', body['message'])
            self.assertEqual(self.events('decision.prepared'), [1])
        self.assertEqual(self.prepared('crash-2')[1]['result']['prepared']['version'], 2)   # a new key is the person's decision to repeat

    def test_a_claim_left_by_a_stopped_process_is_reclaimed_and_runs_exactly_once(self):
        with mock.patch.object(DeskTools, 'execute', side_effect=Crash()), self.assertRaises(Crash):
            self.app.tool_call(OWNER, 'prepareDecision', self.prepared_body(), 'early')
        self.assertEqual(self.rows(), {})   # a raised error drops its claim; a process that was killed cannot, so its claim is made by hand
        key = 'owner_demo:owner:tool:prepareDecision:orphan'
        with self.app.db:   # what a stopped process leaves: a claim of another boot, with nothing committed
            self.app.db.execute("INSERT INTO record_ops (key, payload_hash, result, state, at, boot) VALUES (?,?,?,?,?,?)",
                                (key, fingerprint(self.prepared_body()), '', 'pending', '2026-10-01T00:00:00+00:00', 'a-boot-that-stopped'))
        status, body, _ = self.prepared('orphan')
        self.assertEqual((status, body['ok'], 'replayed' in body), (200, True, False))   # reclaimed and run, exactly once
        self.assertEqual(self.events('decision.prepared'), [1])
        self.assertEqual(self.prepared('orphan')[1]['replayed'], True)
        self.assertEqual(self.app.db.execute('SELECT state, boot FROM record_ops WHERE key=?', (key,)).fetchone(), ('done', self.app.boot))

    def test_a_pending_claim_of_this_boot_is_in_progress_and_other_input_is_still_key_reused(self):
        with self.app.db:
            self.app.db.execute("INSERT INTO record_ops (key, payload_hash, result, state, at, boot) VALUES (?,?,?,?,?,?)",
                                ('owner_demo:owner:tool:prepareDecision:busy', fingerprint(self.prepared_body()), '', 'pending', '2026-10-01T00:00:00+00:00', self.app.boot))
        status, body, _ = self.prepared('busy')
        self.assertEqual((status, body['error']), (409, 'OPERATION_IN_PROGRESS'))
        self.assertEqual(self.prepared('busy', 10)[1]['error'], 'KEY_REUSED')
        self.assertEqual(self.events('decision.prepared'), [])

    def test_a_refusal_that_changed_nothing_is_not_kept_for_its_key(self):
        said = 'Bayside Café is opening a second shop next month.'
        self.app.model_adapter = Unreachable()
        status, body, _ = self.tool('interpretStatement', key='m1', message=said, text=said)
        self.assertEqual((status, body['error']), (200, 'MODEL_UNAVAILABLE'))
        self.assertEqual(self.rows(), {})
        self.app.model_adapter = self.model
        retried = self.tool('interpretStatement', key='m1', message=said, text=said)[1]
        self.assertEqual((retried['ok'], 'replayed' in retried), (True, False))   # judged afresh, not stuck on the refusal
        # a case still being prepared: assessRequest is refused, and the same key works once the case has settled
        r = self.create('Could we pay invoice DEMO-502 on 2026-11-10 instead?', key='intake-9')
        settled = self.app.get(r['id'])
        stored = {**settled, 'status': 'analysing'}
        with self.app.db:
            self.app.save(stored)
        status, body, _ = self.tool('assessRequest', 'staff', 'cp1', requestId=r['id'])
        self.assertEqual((status, body['ok'], body['error']), (200, False, 'CASE_PREPARING'))
        self.assertEqual(self.rows().get('staff_demo:staff:tool:assessRequest:cp1'), None)
        with self.app.db:
            self.app.save(settled)
        status, body, _ = self.tool('assessRequest', 'staff', 'cp1', requestId=r['id'])
        self.assertEqual((status, body['ok'], 'replayed' in body), (200, True, False))
        self.assertEqual(self.tool('assessRequest', 'staff', 'cp1', requestId=r['id'])[1]['replayed'], True)

    def test_a_refusal_after_a_change_committed_is_kept_with_that_change(self):
        # a refusal that left a change behind is part of the operation: the retry gets that answer, not a second try
        row = ('owner_demo:owner:tool:prepareDecision:half',)
        real = App.tool_result

        def refuse_after_writing(app, actor, scoped, key, message, name, outcome, notes=()):
            with app.armed(scoped), app.db:   # something committed under the key, then the tool refuses
                app.db.execute("INSERT OR REPLACE INTO meta VALUES ('probe', '1')")
            outcome.ok, outcome.result = False, {'ok': False, 'error': 'INVALID_ARGUMENT', 'message': 'refused after writing'}
            return real(app, actor, scoped, key, message, name, outcome, notes)
        with mock.patch.object(App, 'tool_result', refuse_after_writing):
            first = self.app.tool_call(OWNER, 'prepareDecision', self.prepared_body(), 'half')
        self.assertEqual((first['ok'], first['error']), (False, 'INVALID_ARGUMENT'))
        self.assertEqual(self.rows()[row[0]], 'done')
        again = self.app.tool_call(OWNER, 'prepareDecision', self.prepared_body(), 'half')
        self.assertEqual((again['replayed'], again['error']), (True, 'INVALID_ARGUMENT'))

    def test_records_reset_meanwhile_leaves_no_row_and_the_answer_is_still_returned(self):
        real = App.tool_finish

        def after_reset(app, scoped, result):
            with app.db:
                app.db.execute('DELETE FROM record_ops')   # as a reset or restore replaces the tables
            return real(app, scoped, result)
        with mock.patch.object(App, 'tool_finish', after_reset):
            body = self.app.tool_call(OWNER, 'prepareDecision', self.prepared_body(), 'gone')
        self.assertTrue(body['ok'])
        self.assertEqual(self.rows(), {})


class RestartTests(ToolOpsCase):
    def test_a_retry_after_the_process_restarted_replays_and_changes_nothing(self):
        first = self.prepared('r1')[1]
        old_boot = self.app.boot
        self.restart(mode='live', adapter=self.model)
        self.assertNotEqual(self.app.boot, old_boot)
        status, again, _ = self.prepared('r1')
        self.assertEqual((status, again['replayed'], again['result']), (200, True, first['result']))
        self.assertEqual(self.events('decision.prepared'), [1])

    def test_the_applied_mark_is_in_the_business_transaction_and_only_for_the_thread_that_armed_it(self):
        db = self.app.db
        self.assertIsInstance(db, sqlite3.Connection)
        self.assertIsInstance(db, OpConnection)
        with db:
            db.execute("INSERT INTO record_ops (key, payload_hash, result, state, at, boot) VALUES ('probe', 'h', '', 'pending', 'now', 'b')")
        state = lambda: db.execute("SELECT state FROM record_ops WHERE key='probe'").fetchone()[0]
        with self.app.armed('probe'):
            with db:
                pass   # nothing written: nothing committed, nothing marked
            self.assertEqual(state(), 'pending')
            other = threading.Thread(target=lambda: db.commit())   # another thread's commit does not mark this key
            other.start()
            other.join()
            self.assertEqual(state(), 'pending')
            with self.assertRaises(RuntimeError):
                with db:
                    db.execute("INSERT OR REPLACE INTO meta VALUES ('probe', '1')")
                    raise RuntimeError('rolled back')
            self.assertEqual(state(), 'pending')
            db.execute("INSERT OR REPLACE INTO meta VALUES ('probe', '2')")
            db.commit()   # an explicit commit marks too
            self.assertEqual(state(), 'applied')
        self.assertEqual(db.armed, {})
        with db:
            db.execute("UPDATE record_ops SET state='pending' WHERE key='probe'")
            db.execute("INSERT OR REPLACE INTO meta VALUES ('probe', '3')")
        self.assertEqual(state(), 'pending')   # not armed any more: a commit marks nothing
        with db:
            db.execute("DELETE FROM record_ops WHERE key='probe'")
            db.execute("DELETE FROM meta WHERE key='probe'")


class CompatibilityTests(unittest.TestCase):
    """A database from before the state, at and boot columns opens, its rows read as done, and only old finished tool rows are pruned."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'old.sqlite3'
        self.apps = []
        db = sqlite3.connect(self.path)
        db.execute('CREATE TABLE record_ops (key TEXT PRIMARY KEY, payload_hash TEXT NOT NULL, result TEXT NOT NULL)')
        self.legacy_body = {'args': {'requestId': 'req_x'}, 'message': 'withdraw it'}
        db.execute('INSERT INTO record_ops VALUES (?,?,?)', ('owner_demo:desk-tool:withdrawPreparation:old-1', fingerprint(self.legacy_body),
                                                             json.dumps({'ok': True, 'result': {'withdrawn': True}})))
        db.execute('INSERT INTO record_ops VALUES (?,?,?)', ('staff_demo:records/customers:c1', 'h', '{}'))
        db.commit()
        db.close()

    def tearDown(self):
        for app in self.apps:
            app.close()
            app.db.close()
        self.tmp.cleanup()

    def open(self):
        app = App(self.path, 'mock')
        self.apps.append(app)
        return app

    def test_old_rows_read_as_done_and_a_legacy_desk_tool_row_replays_for_a_person_but_not_the_agent(self):
        app = self.open()
        self.assertEqual([r[1] for r in app.db.execute('PRAGMA table_info(record_ops)')], ['key', 'payload_hash', 'result', 'state', 'at', 'boot'])
        self.assertEqual(app.db.execute('SELECT DISTINCT state, at, boot FROM record_ops').fetchall(), [('done', None, None)])
        with app.lock:
            replay = app.tool_call(OWNER, 'withdrawPreparation', self.legacy_body, 'old-1')
            self.assertEqual(replay, {'ok': True, 'result': {'withdrawn': True}, 'replayed': True})
            with self.assertRaises(APIError) as caught:   # the fingerprint is checked as it was
                app.tool_call(OWNER, 'withdrawPreparation', {**self.legacy_body, 'message': 'other'}, 'old-1')
            self.assertEqual(caught.exception.code, 'KEY_REUSED')
            with self.assertRaises(APIError) as caught:   # the agent's old rows were never one role's: not replayed (no records here, so it stops at the claim's next step)
                app.tool_call({**AGENT, 'id': 'owner_demo', 'role': 'owner'}, 'withdrawPreparation', self.legacy_body, 'old-1')
            self.assertEqual(caught.exception.code, 'NO_RECORDS')
        self.assertEqual(app.db.execute("SELECT COUNT(*) FROM record_ops WHERE state='pending'").fetchone()[0], 0)   # the failed claim was dropped

    def test_retention_prunes_only_old_finished_tool_rows(self):
        self.open().close()
        old = (datetime.now(timezone.utc) - timedelta(days=TOOL_OPS_KEEP_DAYS + 1)).isoformat()
        recent = (datetime.now(timezone.utc) - timedelta(days=TOOL_OPS_KEEP_DAYS - 1)).isoformat()
        rows = [('owner_demo:owner:tool:prepareDecision:old-done', 'done', old), ('owner_demo:owner:tool:prepareDecision:new-done', 'done', recent),
                ('owner_demo:owner:tool:prepareDecision:old-pending', 'pending', old), ('owner_demo:owner:tool:prepareDecision:old-applied', 'applied', old),
                ('staff_demo:records/customers:old-op', 'done', old), ('staff_demo:desk-turn:x:tool:y:old', 'done', old)]
        db = sqlite3.connect(self.path)
        db.executemany("INSERT INTO record_ops (key, payload_hash, result, state, at) VALUES (?, 'h', '{}', ?, ?)", rows)
        db.commit()
        db.close()
        app = self.open()
        left = {k for (k,) in app.db.execute('SELECT key FROM record_ops')}
        self.assertEqual(left, {'owner_demo:desk-tool:withdrawPreparation:old-1', 'staff_demo:records/customers:c1',   # legacy rows have no time: kept
                                'owner_demo:owner:tool:prepareDecision:new-done', 'owner_demo:owner:tool:prepareDecision:old-pending',
                                'owner_demo:owner:tool:prepareDecision:old-applied', 'staff_demo:records/customers:old-op', 'staff_demo:desk-turn:x:tool:y:old'})


class PerfSanityTests(ToolOpsCase):
    def test_a_read_through_tool_call_touches_no_record_ops(self):
        body = {'args': {'customerId': self.bayside['id']}, 'message': ''}
        before = self.app.db.execute('SELECT COUNT(*) FROM record_ops').fetchone()[0]
        start = time.perf_counter()
        for _ in range(200):
            self.assertTrue(self.app.tool_call(STAFF, 'customerOverview', body, None)['ok'])
        per_call = (time.perf_counter() - start) * 1000 / 200
        print('customerOverview via tool_call: %.2f ms/call over 200 calls' % per_call)
        self.assertEqual(self.app.db.execute('SELECT COUNT(*) FROM record_ops').fetchone()[0], before)


if __name__ == '__main__':
    unittest.main()
