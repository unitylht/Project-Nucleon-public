"""The demo console's reset to an empty workspace, and the dataset id that tells a client the records were replaced."""
import unittest

from server import App
from test_demo import DemoCase


class EmptyResetTests(DemoCase):
    def dataset(self):
        return self.call('/api/tools', None, 'owner')[1]['datasetId']

    def test_dataset_id_changes_across_a_reset(self):
        self.start()
        before = self.dataset()
        self.assertTrue(before)
        self.console('start-empty', {})
        self.assertNotEqual(self.dataset(), before)

    def test_empty_reset_then_owner_sets_vnd_and_first_invoice_locks_it(self):
        self.start()
        before = self.dataset()
        status, body, _ = self.console('reset', {'to': 'empty'})
        self.assertEqual((status, body['reset']), (200, True), body)
        self.assertNotEqual(self.dataset(), before)
        self.assertTrue(body['backup'])
        settings = {'currency': 'VND', 'scale': 0, 'timezone': 'Asia/Ho_Chi_Minh', 'businessName': 'Test'}
        self.assertEqual(self.call('/api/setup/settings', settings, 'owner')[0], 200)
        c = self.call('/api/records/customers', {'name': 'An'}, 'staff', 'c1')[1]['record']
        inv = {'customerId': c['id'], 'reference': 'V-1', 'issueDate': '2026-10-01', 'total': '1200000'}
        self.assertEqual(self.call('/api/records/invoices', inv, 'staff', 'i1')[0], 200)
        status, body, _ = self.call('/api/setup/settings', {**settings, 'currency': 'USD', 'scale': 2}, 'owner')
        self.assertEqual((status, body['error']), (409, 'SETTINGS_LOCKED'), body)

    def test_unknown_target_is_refused(self):
        self.start()
        self.assertEqual(self.console('reset', {'to': 'x'})[0], 400)


class FixedAccessCodesTests(unittest.TestCase):
    def test_codes_from_the_config_replace_the_random_ones_and_are_checked(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            app = App(d + '/t.sqlite3', 'mock', demo={'enabled': True, 'backupDir': d}, access_codes={'staff': 'ntk-staff', 'owner': 'ntk-owner'})
            self.assertEqual((app.demo_codes['staff'], app.demo_codes['owner']), ('ntk-staff', 'ntk-owner'))
            self.assertNotIn(app.demo_codes['operator'], ('ntk-staff', 'ntk-owner'))
            with self.assertRaises(Exception):
                App(d + '/u.sqlite3', 'mock', demo={'enabled': True, 'backupDir': d}, access_codes={'staff': 'short', 'owner': 'ntk-owner'})
            with self.assertRaises(Exception):
                App(d + '/v.sqlite3', 'mock', demo={'enabled': True, 'backupDir': d}, access_codes={'staff': 'same-code', 'owner': 'same-code'})
