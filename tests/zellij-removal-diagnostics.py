#!/usr/bin/env python3
"""Bounded private deletion diagnostics; no SSH, native deletion or user files."""
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('delete_fixtures', Path(__file__).with_name('zellij-remote-delete.py'))
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
from remote import RemovalFailure, removal_error_text, rpc


class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.DeleteTests()
        self.fixture.setUp()
        self.m = self.fixture.m
        self.root = self.fixture.root
        self.path = self.root / 'last-remote-removal-error.json'
        self.row = {'host': 'lab', 'session': 'target', 'name': 'Project'}

    def tearDown(self):
        self.fixture.tearDown()

    def trigger_failure(self, error, confirm=False):
        snapshot = self.fixture.preview()
        self.m.remotes.request = Mock(side_effect=[snapshot, error] if confirm else error)
        with patch('modal.pick', side_effect=[('remove\tRemove', ''), (None, '')] if confirm else [(None, '')]) as picker:
            self.m.confirm_remove(self.row)
        return picker.call_args.args[1]

    def test_preflight_capture_is_private_and_bounded(self):
        header = self.trigger_failure(ValueError('Cannot verify attached clients. ' + 'x' * 3000))
        record = json.loads(self.path.read_text())
        self.assertEqual(set(record), {'timestamp_utc', 'host', 'session', 'stage', 'error'})
        self.assertEqual(record['host'], 'lab'); self.assertEqual(record['session'], 'target')
        self.assertEqual(record['stage'], 'preflight'); self.assertLessEqual(len(record['error']), 1024)
        self.assertRegex(record['timestamp_utc'], r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$')
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertEqual(self.path.stat().st_uid, os.getuid())
        self.assertIn('Details saved privately', header); self.assertIn('No automatic retry', header)
        self.m.remotes.request.assert_called_once_with('lab', 'remove-preview', session='target')
        self.m.cli.assert_not_called()

    def test_confirmed_failure_captured_without_retry(self):
        self.trigger_failure(ValueError('Native cache permission denied'), confirm=True)
        self.assertEqual(json.loads(self.path.read_text())['stage'], 'delete')
        self.assertEqual(self.m.remotes.request.call_count, 2)
        self.assertEqual(self.m.remotes.request.call_args.args[:2], ('lab', 'remove'))

    def test_latest_error_replaces_previous_only(self):
        sentinel = self.root / 'registry-sentinel'; sentinel.write_text('unchanged')
        self.m.record_removal_error('lab', 'target', 'preflight', 'first')
        self.m.record_removal_error('lab', 'target', 'delete', 'second')
        self.assertEqual(json.loads(self.path.read_text())['error'], 'second')
        self.assertEqual(sentinel.read_text(), 'unchanged')
        self.assertFalse(list(self.root.glob('.remote-removal-error-*')))

    def test_cancel_does_not_capture_or_delete(self):
        self.m.remotes.request = Mock(return_value=self.fixture.preview())
        for selected in [None, 'cancel\tCancel']:
            with patch('modal.pick', return_value=(selected, '')): self.m.confirm_remove(self.row)
        self.assertFalse(self.path.exists())
        self.assertTrue(all(call.args[1] == 'remove-preview' for call in self.m.remotes.request.call_args_list))

    def test_cancel_preserves_timestamped_previous_error(self):
        self.m.record_removal_error('lab', 'target', 'preflight', 'previous')
        original = self.path.read_bytes()
        self.m.remotes.request = Mock(return_value=self.fixture.preview())
        with patch('modal.pick', return_value=(None, '')): self.m.confirm_remove(self.row)
        self.assertEqual(self.path.read_bytes(), original)

    def test_success_clears_previous_capture(self):
        self.m.record_removal_error('lab', 'target', 'delete', 'previous')
        self.m.remotes.request = Mock(return_value=self.fixture.preview())
        with patch('modal.pick', return_value=('remove\tRemove', '')): self.m.confirm_remove(self.row)
        self.assertFalse(self.path.exists()); self.assertEqual(self.m.remotes.request.call_count, 2)

    def test_current_remote_refusal_is_captured_without_rpc(self):
        self.fixture.data['workspaces']['carrier'] = {'remote_host': 'lab', 'remote_session': 'target'}
        self.m.c['SESSION'] = 'carrier'; self.m.remotes.request = Mock()
        with patch('modal.pick'): self.m.confirm_remove(self.row)
        self.assertIn('Switch', json.loads(self.path.read_text())['error'])
        self.m.remotes.request.assert_not_called()

    def test_write_failure_does_not_mask_removal_reason(self):
        with patch.object(self.m, 'record_removal_error', side_effect=OSError('disk full')):
            header = self.trigger_failure(ValueError('Actual native failure'))
        self.assertIn('Actual native failure', header); self.assertIn('Could not save diagnostics', header)
        self.assertFalse(self.path.exists())

    def test_unsafe_directory_refused_without_chmod(self):
        self.root.chmod(0o755)
        header = self.trigger_failure(ValueError('Actual failure'))
        self.assertIn('Actual failure', header); self.assertFalse(self.path.exists())
        self.assertEqual(stat.S_IMODE(self.root.stat().st_mode), 0o755)

    def test_directory_symlink_refused(self):
        link = self.root / 'redirect'; link.symlink_to(self.root, target_is_directory=True)
        self.m.c['HOME_STATE'] = link
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.m.record_removal_error('lab', 'target', 'delete', 'failure')
        self.assertFalse(self.path.exists())

    def test_file_symlink_refused_and_target_untouched(self):
        target = self.root / 'sentinel'; target.write_text('unchanged')
        self.path.symlink_to(target)
        header = self.trigger_failure(ValueError('Actual failure'))
        self.assertIn('Actual failure', header); self.assertTrue(self.path.is_symlink())
        self.assertEqual(target.read_text(), 'unchanged')

    def test_public_existing_capture_refused(self):
        self.path.write_text('unchanged'); self.path.chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'Unsafe diagnostic file'):
            self.m.record_removal_error('lab', 'target', 'delete', 'failure')
        self.assertEqual(self.path.read_text(), 'unchanged')

    def test_atomic_write_failure_preserves_last_error_and_cleans_temp(self):
        self.m.record_removal_error('lab', 'target', 'delete', 'original')
        with patch('workspaces.os.replace', side_effect=OSError('write failure')):
            with self.assertRaises(OSError): self.m.record_removal_error('lab', 'target', 'delete', 'new')
        self.assertEqual(json.loads(self.path.read_text())['error'], 'original')
        self.assertFalse(list(self.root.glob('.remote-removal-error-*')))

    def test_cleanup_failure_after_success_is_not_a_removal_error(self):
        self.m.remotes.request = Mock(return_value=self.fixture.preview())
        with patch.object(self.m, 'clear_removal_error', side_effect=OSError('failed cleanup')):
            with patch('modal.pick', return_value=('remove\tRemove', '')) as picker:
                self.m.confirm_remove(self.row)
        self.assertEqual(picker.call_count, 1)

    def test_popup_wraps_error_and_identifies_phase(self):
        with patch('workspaces.shutil.get_terminal_size', return_value=os.terminal_size((50, 24))):
            header = self.trigger_failure(ValueError('Permission denied reading the saved native session cache. ' * 10))
        self.assertIn('Remote removal failed (preflight)', header)
        lines = header.splitlines()
        self.assertGreater(len(lines), 8)
        self.assertTrue(all(len(line) <= 42 for line in lines if line and not line.startswith('Could not')))
        self.assertIn(' …', header)

    def test_native_command_and_environment_are_not_in_error(self):
        error = subprocess.CalledProcessError(2, ['zellij', 'cmd-secret', 'MOSH_KEY=secret'],
                                             stderr='Permission denied on native cache')
        text = removal_error_text(error)
        self.assertIn('exit 2', text); self.assertIn('Permission denied', text)
        self.assertNotIn('cmd-secret', text); self.assertNotIn('MOSH_KEY', text)

    def test_native_reason_bytes_and_missing_details(self):
        self.assertIn('cache missing', removal_error_text(subprocess.CalledProcessError(1, 'hidden', stderr=b'cache missing')))
        self.assertIn('No native error details', removal_error_text(subprocess.CalledProcessError(1, 'hidden')))

    def test_timeout_does_not_log_command_or_captured_output(self):
        text = removal_error_text(subprocess.TimeoutExpired(['secret-command'], 12, output='secret-output'))
        self.assertIn('outcome is unknown', text); self.assertNotIn('secret', text)

    def test_control_sequences_and_token_assignments_are_removed(self):
        text = removal_error_text('\x1b[31mDenied\x1b[0m\x00 token=abc MOSH_KEY=xyz sk-' + 'a' * 30)
        self.assertNotIn('\x1b', text); self.assertNotIn('\x00', text)
        self.assertNotIn('abc', text); self.assertNotIn('xyz', text); self.assertNotIn('a' * 30, text)
        self.assertIn('Denied', text)

    def test_terminal_hyperlink_does_not_swallow_reason(self):
        text = removal_error_text('\x1b]8;;https://example.invalid\x1b\\cache denied\x1b]8;;\x1b\\')
        self.assertEqual(text, 'cache denied')

    def test_wrong_directory_owner_refused(self):
        info = Mock(st_uid=os.getuid() + 1, st_mode=stat.S_IFDIR | 0o700)
        with patch('workspaces.os.fstat', return_value=info):
            with self.assertRaisesRegex(ValueError, 'owned and private'):
                self.m.record_removal_error('lab', 'target', 'delete', 'failure')
        self.assertFalse(self.path.exists())

    def test_native_reason_survives_server_and_client(self):
        reason = 'Permission denied deleting session-layout.kdl'
        error = subprocess.CalledProcessError(2, ['zellij', 'hidden-argument'], stderr=reason)
        payload = {'operation': 'remove', 'session': 'target', 'identity': 'mocked'}
        with patch.object(self.m, 'remove_remote_workspace', side_effect=error):
            with patch('sys.stdin', io.StringIO(json.dumps(payload))):
                with patch('sys.stdout', new_callable=io.StringIO) as output: rpc(self.m)
        wire = output.getvalue()
        self.assertIn(reason, json.loads(wire)['error']); self.assertNotIn('hidden-argument', wire)
        with patch('remote.subprocess.run', return_value=Mock(returncode=0, stdout=wire)):
            with self.assertRaises(RemovalFailure) as caught: self.m.remotes.request('lab', 'remove', session='target')
        self.assertIn(reason, str(caught.exception))

    def test_native_preview_error_has_useful_reason(self):
        error = subprocess.CalledProcessError(1, ['hidden'], stderr='cannot list clients')
        with patch.object(self.m, 'remote_remove_snapshot', side_effect=error):
            with patch('sys.stdin', io.StringIO('{"operation":"remove-preview","session":"target"}')):
                with patch('sys.stdout', new_callable=io.StringIO) as output: rpc(self.m)
        self.assertIn('cannot list clients', json.loads(output.getvalue())['error'])

    def test_non_removal_rpc_error_behavior_unchanged(self):
        error = subprocess.CalledProcessError(1, 'hidden', stderr='detail')
        with patch.object(self.m, 'ensure', side_effect=error):
            with patch('sys.stdin', io.StringIO('{"operation":"ensure","session":"target"}')):
                with self.assertRaises(subprocess.CalledProcessError): rpc(self.m)

    def test_ssh_failure_detail_only_for_deletion(self):
        result = Mock(returncode=255, stdout='', stderr='Permission denied (publickey)')
        with patch('remote.subprocess.run', return_value=result):
            with self.assertRaises(RemovalFailure) as caught: self.m.remotes.request('lab', 'remove-preview', session='target')
            self.assertIn('publickey', str(caught.exception))
            with self.assertRaises(ValueError) as caught: self.m.remotes.request('lab', 'rows')
            self.assertEqual(str(caught.exception), 'Remote lab unavailable (SSH/helper failure)')

    def test_non_removal_client_error_bound_unchanged(self):
        result = Mock(returncode=0, stdout=json.dumps({'error': 'x' * 3000}))
        with patch('remote.subprocess.run', return_value=result):
            with self.assertRaises(ValueError) as caught: self.m.remotes.request('lab', 'rows')
            self.assertEqual(len(str(caught.exception)), len('Remote lab: ') + 160)
            with self.assertRaises(RemovalFailure) as caught: self.m.remotes.request('lab', 'remove', session='target')
            self.assertLessEqual(len(str(caught.exception)), len('Remote lab: ') + 1024)


if __name__ == '__main__':
    unittest.main()
