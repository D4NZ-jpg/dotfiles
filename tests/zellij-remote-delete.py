#!/usr/bin/env python3
"""Remote deletion guards; isolated files/mocks, no SSH or native deletion."""
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'dot_config/zellij/bin'))
from workspaces import WorkspaceManager
from remote import _rpc


class DeleteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='remote-delete-')
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, XDG_RUNTIME_DIR=str(self.root), XDG_CACHE_HOME=str(self.root / 'cache'))
        self.env.start()
        self.data = {'workspaces': {'target': {'name': 'Project', 'order': 1, 'directory': str(self.root)}},
                     'next_slot': {'target': 3}}
        self.notes = {'target': {'1': 'note'}}
        def transact(fn, path):
            return fn(self.notes if Path(path).name == 'tab-notes.json' else self.data)
        self.call = Mock(return_value='CLIENT_ID ZELLIJ_PANE_ID RUNNING_COMMAND')
        self.m = WorkspaceManager({'SESSION': '', 'CONFIG': self.root, 'HOME_STATE': self.root,
            'STATE': self.root / 'panes', 'transact': transact, 'call': self.call,
            'clean': lambda s, limit: str(s)[:limit]})
        self.found = {}
        self.m.discover = Mock(side_effect=lambda: (self.data, dict(self.found)))
        self.m.cli = Mock()
        (self.root / 'remotes.json').write_text('{"lab":"user@lab.example"}')
        self.handles = []

    def tearDown(self):
        for handle in self.handles: handle.close()
        self.env.stop(); self.temp.cleanup()

    def live(self):
        path = self.root / 'zellij/contract_version_1/target'
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = socket.socket(socket.AF_UNIX); handle.bind(str(path)); self.handles.append(handle)
        self.found['target'] = 'live'
        return path

    def preview(self):
        return self.m.remote_remove_snapshot('target')

    def test_saved_preview_does_not_start_or_delete(self):
        result = self.preview()
        self.assertEqual(result['session'], 'target')
        self.assertEqual(result['status'], 'saved')
        self.call.assert_not_called(); self.m.cli.assert_not_called()

    def test_detached_live_preview_does_not_delete(self):
        self.live(); result = self.preview()
        self.assertEqual(result['status'], 'live')
        self.call.assert_called_once_with('action', 'list-clients')
        self.m.cli.assert_not_called()

    def test_attached_clients_refused(self):
        self.live(); self.call.return_value += '\n1 terminal_2 zsh'
        with self.assertRaisesRegex(ValueError, 'attached clients'): self.preview()
        self.m.cli.assert_not_called()

    def test_unknown_client_output_refused(self):
        self.live()
        for output in ['', 'error', 'CLIENT_ID OTHER', '1 terminal_2']:
            self.call.return_value = output
            with self.assertRaisesRegex(ValueError, 'verify attached clients'): self.preview()

    def test_client_query_failure_refused(self):
        self.live(); self.call.side_effect = subprocess.TimeoutExpired('zellij', 10)
        with self.assertRaises(subprocess.TimeoutExpired): self.preview()
        self.m.cli.assert_not_called()

    def test_missing_live_socket_refused(self):
        self.found['target'] = 'live'
        with self.assertRaisesRegex(ValueError, 'socket'): self.preview()

    def test_symlink_socket_refused(self):
        path = self.live(); path.unlink(); path.symlink_to(self.root / 'another')
        with self.assertRaisesRegex(ValueError, 'socket'): self.preview()

    def test_current_workspace_refused(self):
        self.m.c['SESSION'] = 'target'
        with self.assertRaisesRegex(ValueError, 'Switch'): self.preview()

    def test_transport_refused(self):
        self.data['workspaces']['target']['remote_bridge'] = True
        with self.assertRaisesRegex(ValueError, 'transports'): self.preview()

    def test_alias_not_resolved_to_other_workspace(self):
        with self.assertRaisesRegex(ValueError, 'no longer exists'):
            self.m.remote_remove_snapshot('Project')

    def test_invalid_name_refused(self):
        with self.assertRaises(ValueError): self.m.remote_remove_snapshot('../target')

    def test_metadata_change_refused(self):
        token = self.preview()['identity']; self.data['workspaces']['target']['order'] = 2
        with self.assertRaisesRegex(ValueError, 'changed'): self.m.remove_remote_workspace('target', token)
        self.m.cli.assert_not_called()

    def test_layout_change_refused(self):
        token = self.preview()['identity']; digest = hashlib.sha256(b'target').hexdigest()
        path = self.root / 'layouts' / (digest + '.kdl'); path.parent.mkdir(); path.write_text('new layout')
        with self.assertRaisesRegex(ValueError, 'changed'): self.m.remove_remote_workspace('target', token)

    def test_saved_to_live_change_refused(self):
        token = self.preview()['identity']; self.live()
        with self.assertRaisesRegex(ValueError, 'changed'): self.m.remove_remote_workspace('target', token)
        self.m.cli.assert_not_called()

    def test_attaching_during_confirmation_refused(self):
        self.live(); token = self.preview()['identity']; self.call.return_value += '\n2 terminal_1 zsh'
        with self.assertRaisesRegex(ValueError, 'attached clients'): self.m.remove_remote_workspace('target', token)
        self.m.cli.assert_not_called()

    def test_missing_or_wrong_confirmation_identity_refused(self):
        for token in [None, '', 'bad', 5]:
            with self.assertRaisesRegex(ValueError, 'changed'): self.m.remove_remote_workspace('target', token)
        self.m.cli.assert_not_called()

    def test_saved_removal_keeps_conversations(self):
        conversation = self.root / 'pi-conversation.jsonl'; conversation.write_text('sentinel')
        self.assertTrue(self.m.remove_remote_workspace('target', self.preview()['identity']))
        self.assertNotIn('target', self.data['workspaces']); self.assertEqual(conversation.read_text(), 'sentinel')
        self.m.cli.assert_not_called()

    def test_live_native_failure_preserves_metadata(self):
        self.live(); token = self.preview()['identity']
        self.m.cli.side_effect = subprocess.CalledProcessError(1, 'zellij')
        with self.assertRaises(subprocess.CalledProcessError): self.m.remove_remote_workspace('target', token)
        self.assertIn('target', self.data['workspaces'])

    def test_native_stopped_but_cache_absent_finishes_cleanup(self):
        path = self.live(); token = self.preview()['identity']
        def stop(*args):
            path.unlink(); self.found.clear(); raise subprocess.CalledProcessError(2, 'zellij')
        self.m.cli.side_effect = stop
        self.assertTrue(self.m.remove_remote_workspace('target', token))
        self.assertNotIn('target', self.data['workspaces'])
        self.m.cli.assert_called_once_with('delete-session', '--force', 'target')

    def test_native_error_with_changed_metadata_refused(self):
        self.live(); token = self.preview()['identity']
        def stop(*args):
            self.found.clear(); self.data['workspaces']['target']['order'] = 9
            raise subprocess.CalledProcessError(2, 'zellij')
        self.m.cli.side_effect = stop
        with self.assertRaisesRegex(ValueError, 'changed'): self.m.remove_remote_workspace('target', token)
        self.assertIn('target', self.data['workspaces'])

    def test_remote_cancel_first_and_escape_never_deletes(self):
        self.m.remotes.request = Mock(return_value=self.preview())
        for selected in [None, 'cancel\tCancel']:
            with patch('modal.pick', return_value=(selected, '')) as picker:
                self.m.confirm_remove({'host': 'lab', 'session': 'target', 'name': 'misleading'})
                options, header = picker.call_args.args
                self.assertTrue(options[0].startswith('cancel'))
                self.assertIn('lab (user@lab.example) / target', header)
                self.assertIn('Pi conversations are kept', header)
        self.assertTrue(all(c.args[1] == 'remove-preview' for c in self.m.remotes.request.call_args_list))

    def test_confirmation_sends_exact_host_session_and_identity(self):
        snapshot = self.preview(); self.m.remotes.request = Mock(return_value=snapshot)
        with patch('modal.pick', return_value=('remove\tRemove', '')):
            self.m.confirm_remove({'host': 'lab', 'session': 'target', 'name': 'misleading'})
        self.m.remotes.request.assert_called_with('lab', 'remove', session='target', identity=snapshot['identity'])

    def test_current_remote_workspace_refused_before_rpc(self):
        self.data['workspaces']['carrier'] = {'remote_host': 'lab', 'remote_session': 'target'}
        self.m.c['SESSION'] = 'carrier'; self.m.remotes.request = Mock()
        with patch('modal.pick') as picker:
            self.m.confirm_remove({'host': 'lab', 'session': 'target'})
        self.m.remotes.request.assert_not_called(); self.assertIn('Switch', picker.call_args.args[1])

    def test_changed_account_refused(self):
        self.m.remotes.request = Mock(return_value=self.preview())
        def confirm(*args):
            (self.root / 'remotes.json').write_text('{"lab":"other@lab.example"}')
            return 'remove\tRemove', ''
        calls = []
        def picker(*args):
            calls.append(args)
            return confirm() if len(calls) == 1 else (None, '')
        with patch('modal.pick', side_effect=picker):
            self.m.confirm_remove({'host': 'lab', 'session': 'target'})
        self.m.remotes.request.assert_called_once_with('lab', 'remove-preview', session='target')
        self.assertIn('account changed', calls[-1][1])

    def test_replaced_session_socket_refused(self):
        path = self.live(); token = self.preview()['identity']
        path.unlink()
        handle = socket.socket(socket.AF_UNIX); handle.bind(str(path)); self.handles.append(handle)
        with self.assertRaisesRegex(ValueError, 'changed'): self.m.remove_remote_workspace('target', token)
        self.m.cli.assert_not_called()

    def test_saved_with_remaining_socket_refused(self):
        self.live(); self.found.clear()
        with self.assertRaisesRegex(ValueError, 'state is changing'): self.preview()

    def test_saved_layout_symlink_refused(self):
        digest = hashlib.sha256(b'target').hexdigest()
        path = self.root / 'layouts' / (digest + '.kdl'); path.parent.mkdir()
        path.symlink_to(self.root / 'missing')
        with self.assertRaisesRegex(ValueError, 'regular file'): self.preview()

    def test_rpc_cannot_remove_without_preview_identity(self):
        with patch('sys.stdin', io.StringIO('{"operation":"remove","session":"target"}')):
            with self.assertRaisesRegex(ValueError, 'changed'): _rpc(self.m)
        self.m.cli.assert_not_called()

    def test_stale_transport_does_not_recreate_deleted_workspace(self):
        self.data['workspaces'].clear()
        with patch.object(self.m, 'attach') as attach:
            with self.assertRaisesRegex(ValueError, 'no longer exists'):
                self.m.attach_remote_existing('target')
        attach.assert_not_called()

    def test_remote_attach_requires_exact_session_not_label(self):
        with patch.object(self.m, 'attach') as attach:
            with self.assertRaisesRegex(ValueError, 'no longer exists'):
                self.m.attach_remote_existing('Project')
            self.m.attach_remote_existing('target')
        attach.assert_called_once_with('target')

    def test_rpc_preview_and_remove_dispatch(self):
        for op in ['remove-preview', 'remove']:
            request = {'operation': op, 'session': 'target', 'identity': self.preview()['identity']}
            with patch('sys.stdin', io.StringIO(json.dumps(request))):
                result = _rpc(self.m)
            self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
