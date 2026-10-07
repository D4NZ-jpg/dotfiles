#!/usr/bin/env python3
"""Private SSH reuse and Mosh handoff lifecycle; no real authentication."""
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
BIN = Path(__file__).resolve().parents[1] / 'dot_config/zellij/bin'
sys.path.insert(0, str(BIN))
from remote import SSH_OPTIONS, private_control, ready_path
from workspaces import WorkspaceManager


class ReuseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.config = Path(self.temp.name)
        (self.config / 'remotes.json').write_text(json.dumps({'dev': 'user@dev.example', 'other': 'dan@other.example'}))
        self.registry = {'workspaces': {}}
        self.manager = WorkspaceManager({'CONFIG': self.config, 'HOME_STATE': self.config, 'SESSION': 'local',
            'transact': lambda fn, path=None: fn(self.registry), 'clean': lambda value, limit: str(value)[:limit]})
        self.remote = self.manager.remotes
        self.sockets = []

    def tearDown(self):
        self.remote.close_connections()
        for handle in self.sockets:
            handle.close()
        self.temp.cleanup()

    def bind(self, path):
        handle = socket.socket(socket.AF_UNIX)
        handle.bind(str(path))
        self.sockets.append(handle)
        return path

    def test_scope_is_lazy_and_outside_uses_no_master(self):
        self.assertEqual(self.remote.ssh_options('dev'), SSH_OPTIONS)
        with self.remote.connection_scope():
            self.assertIsNone(self.remote._control_dir)
        self.assertIsNone(self.remote._control_dir)

    def test_nested_scope_reuses_and_outer_scope_removes_directory(self):
        with self.remote.connection_scope():
            path = self.remote.control_path('dev')
            self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
            with self.remote.connection_scope():
                self.assertEqual(path, self.remote.control_path('dev'))
            self.assertTrue(path.parent.exists())
            self.assertNotEqual(path, self.remote.control_path('other'))
        self.assertFalse(path.parent.exists())
        self.assertEqual(self.remote.ssh_options('dev'), SSH_OPTIONS)

    def test_options_replace_first_values_keep_trust_and_no_forwarding(self):
        with self.remote.connection_scope():
            flags = self.remote.ssh_options('dev')
            for key in ['ControlMaster=', 'ControlPath=', 'ControlPersist=']:
                self.assertEqual(sum(item.startswith(key) for item in flags), 1)
            for value in ['ControlMaster=auto', 'ControlPersist=120', 'StrictHostKeyChecking=yes',
                          'ForwardAgent=no', 'ClearAllForwardings=yes', 'BatchMode=yes']:
                self.assertIn(value, flags)
            self.assertNotIn('ControlPath=none', flags)

    def test_exception_closes_only_owned_socket(self):
        with patch('remote.subprocess.run') as run:
            with self.assertRaisesRegex(ValueError, 'cancel'):
                with self.remote.connection_scope():
                    path = self.bind(self.remote.control_path('dev'))
                    raise ValueError('cancel')
            command = run.call_args.args[0]
            self.assertIn('ControlPath=' + str(path), command)
            self.assertIn('ControlMaster=no', command)
            self.assertEqual(command[-3:], ['-O', 'exit', 'user@dev.example'])
            self.assertEqual(run.call_args.kwargs['timeout'], 3)
            self.assertFalse(path.parent.exists())

    def test_cleanup_failure_still_removes_directory(self):
        with patch('remote.subprocess.run', side_effect=subprocess.TimeoutExpired('ssh', 3)):
            with self.remote.connection_scope():
                path = self.bind(self.remote.control_path('dev'))
        self.assertFalse(path.parent.exists())

    def test_no_socket_cleanup_never_authenticates(self):
        with patch('remote.subprocess.run') as run:
            with self.remote.connection_scope():
                path = self.remote.control_path('dev')
            run.assert_not_called()
        self.assertFalse(path.parent.exists())

    def test_lf_and_result_rpc_share_control_path(self):
        from directory import pick_remote_directory
        with patch('remote.subprocess.run') as run:
            run.return_value.returncode = 0
            run.return_value.stdout = '{"result":{"kind":"cancel"}}'
            with self.remote.connection_scope():
                self.assertIsNone(pick_remote_directory(self.manager, 'dev'))
                commands = [call.args[0] for call in run.call_args_list]
                paths = [[arg for arg in command if arg.startswith('ControlPath=')] for command in commands]
                self.assertEqual(len(paths), 2)
                self.assertEqual(paths[0], paths[1])
                self.assertIn('-tt', commands[0])
                self.assertIn('-T', commands[1])

    def test_validation_rejects_user_master_symlink_and_bad_mode(self):
        with self.assertRaises(ValueError):
            private_control(str(Path.home() / '.ssh/user-master'))
        with self.remote.connection_scope():
            path = self.remote.control_path('dev')
            path.symlink_to(self.config / 'master')
            with self.assertRaisesRegex(ValueError, 'socket'): private_control(path)
            path.unlink()
            path.parent.chmod(0o755)
            with self.assertRaisesRegex(ValueError, 'directory'): private_control(path)
            path.parent.chmod(0o700)

    def test_saved_stale_socket_falls_back_without_recreating_directory(self):
        with self.remote.connection_scope():
            path = self.remote.control_path('dev')
            marker = path.parent / ('ready-' + 'a' * 32)
        self.assertFalse(private_control(path))
        with patch('remote.os.execvpe') as execute:
            self.remote.attach('dev', 'work', str(path), str(marker))
            argv = execute.call_args.args[1]
            self.assertNotIn('--experimental-remote-ip=remote', argv)
            self.assertIn('ControlPath=none', ' '.join(argv))
            self.assertEqual(execute.call_args.args[2]['TMPDIR'], '/tmp')
        self.assertFalse(path.parent.exists())

    def test_mosh_initial_attach_uses_wrapper_and_remote_ip(self):
        with patch('remote.subprocess.run'), self.remote.connection_scope():
            path = self.bind(self.remote.control_path('dev'))
            marker = path.parent / ('ready-' + 'a' * 32)
            with patch('remote.os.execvpe') as execute:
                self.remote.attach('dev', 'work', str(path), str(marker))
            argv = execute.call_args.args[1]
            self.assertIn('--experimental-remote-ip=remote', argv)
            self.assertIn('remote-ssh dev', ' '.join(argv))
            self.assertNotIn('MOSH_KEY', execute.call_args.args[2])

    def test_handshake_ack_only_after_ssh_exit_and_no_output_capture(self):
        with patch('remote.subprocess.run') as run, self.remote.connection_scope():
            path = self.bind(self.remote.control_path('dev'))
            marker = path.parent / ('ready-' + 'a' * 32)
            def ssh(*args, **kwargs):
                self.assertFalse(marker.exists())
                self.assertEqual(kwargs, {})
                self.assertIn('ControlMaster=no', args[0])
                return Mock(returncode=0)
            run.side_effect = ssh
            args = ['-n', '-tt', 'user@dev.example', '--', 'mosh-server new -- command']
            self.assertEqual(self.remote.ssh_handshake('dev', str(path), str(marker), args), 0)
            self.assertEqual(marker.read_text(), '0')
            self.assertEqual(marker.stat().st_mode & 0o777, 0o600)
            run.side_effect = None

    def test_handshake_failure_ack_is_not_success(self):
        with patch('remote.subprocess.run', return_value=Mock(returncode=255)), self.remote.connection_scope():
            path = self.bind(self.remote.control_path('dev'))
            marker = path.parent / ('ready-' + 'b' * 32)
            self.assertEqual(self.remote.ssh_handshake('dev', path, marker,
                ['-tt', 'user@dev.example', '--', 'command']), 255)
            self.assertEqual(marker.read_text(), '255')

    def test_handshake_rejects_wrong_host_flags_and_marker(self):
        with self.remote.connection_scope():
            path = self.remote.control_path('dev')
            marker = path.parent / ('ready-' + 'a' * 32)
            with self.assertRaises(ValueError): ready_path(path, '/tmp/ready-' + 'a' * 32)
            with patch('remote.subprocess.run') as run:
                for args in [['-tt', 'dan@other.example', '--', 'cmd'],
                             ['-S', 'none', 'user@dev.example', '--', 'cmd']]:
                    with self.assertRaises(ValueError): self.remote.ssh_handshake('dev', path, marker, args)
                run.assert_not_called()

    def test_native_attach_closes_before_exec(self):
        with patch.object(self.manager, 'ensure', return_value='work'), patch.object(self.manager, 'touch'), \
                patch.object(self.manager, 'options_for', return_value=[]), patch('workspaces.os.execvpe') as execute:
            self.manager.c['BINARY'] = 'zellij'
            with patch('remote.subprocess.run'), self.remote.connection_scope():
                path = self.bind(self.remote.control_path('dev'))
                execute.side_effect = lambda *args: self.assertFalse(path.parent.exists())
                self.manager.attach('work')

    def test_project_cancel_and_name_abort_close_scope(self):
        with patch('directory.pick_machine_directory', return_value=None):
            self.manager.project()
        self.assertEqual(self.remote._scope_depth, 0)
        with patch('directory.pick_machine_directory', return_value=('dev', '/remote/work')), \
                patch('builtins.input', side_effect=EOFError):
            with self.assertRaises(EOFError): self.manager.project()
        self.assertEqual(self.remote._scope_depth, 0)

    def test_fresh_transport_waits_ack_then_closes_before_switch(self):
        with patch('remote.subprocess.run'), self.remote.connection_scope():
            path = self.bind(self.remote.control_path('dev'))
            with patch.object(self.remote, 'request'), patch.object(self.manager, 'discover', return_value=({}, {})), \
                    patch.object(self.manager, 'ensure') as ensure, patch.object(self.manager, 'switch') as switch:
                def started(name, remote_start=None):
                    layout = next((self.config / 'layouts').glob('*.kdl')).read_text()
                    self.assertNotIn('--control', layout)
                    self.assertEqual(remote_start[0], str(path))
                    marker = Path(remote_start[1])
                    marker.write_text('0')
                ensure.side_effect = started
                switch.side_effect = lambda name: self.assertFalse(path.parent.exists())
                self.remote.switch({'host': 'dev', 'session': 'work'})
                ensure.assert_called_once()
                switch.assert_called_once()
                durable = next((self.config / 'layouts').glob('*.kdl')).read_text()
                self.assertNotIn('--control', durable)
                self.assertIn('start_suspended false', durable)

    def test_handshake_failure_closes_master_without_switching(self):
        with patch('remote.subprocess.run') as run:
            with self.remote.connection_scope():
                path = self.bind(self.remote.control_path('dev'))
                with patch.object(self.remote, 'request'), patch.object(self.manager, 'discover', return_value=({}, {})), \
                        patch.object(self.manager, 'ensure') as ensure, patch.object(self.manager, 'switch') as switch:
                    def failed(name, remote_start=None):
                        Path(remote_start[1]).write_text('255')
                    ensure.side_effect = failed
                    with self.assertRaisesRegex(ValueError, 'handshake'):
                        self.remote.switch({'host': 'dev', 'session': 'work'})
                    switch.assert_not_called()
            self.assertFalse(path.parent.exists())
            self.assertIn('-O', run.call_args.args[0])

    def test_handshake_timeout_closes_master_without_switching(self):
        with patch('remote.subprocess.run') as run:
            with self.remote.connection_scope():
                path = self.bind(self.remote.control_path('dev'))
                with patch.object(self.remote, 'request'), patch.object(self.manager, 'discover', return_value=({}, {})), \
                        patch.object(self.manager, 'ensure'), patch.object(self.manager, 'switch') as switch, \
                        patch('remote.time.monotonic', side_effect=[0, 16]):
                    with self.assertRaisesRegex(ValueError, 'handshake'):
                        self.remote.switch({'host': 'dev', 'session': 'work'})
                    switch.assert_not_called()
            self.assertFalse(path.parent.exists())
            self.assertIn('-O', run.call_args.args[0])

    def test_saved_transport_also_reuses_initial_handshake(self):
        name = self.remote.bridge_name('dev', 'work')
        with patch('remote.subprocess.run'), self.remote.connection_scope():
            path = self.bind(self.remote.control_path('dev'))
            with patch.object(self.remote, 'request'), patch.object(self.manager, 'discover', return_value=({}, {name: 'saved'})), \
                    patch.object(self.manager, 'ensure') as ensure, patch.object(self.manager, 'switch'):
                def started(name, remote_start=None):
                    self.assertEqual(remote_start[0], str(path))
                    Path(remote_start[1]).write_text('0')
                ensure.side_effect = started
                self.remote.switch({'host': 'dev', 'session': 'work'})
                ensure.assert_called_once()
        durable = next((self.config / 'layouts').glob('*.kdl')).read_text()
        self.assertNotIn('--control', durable)
        self.assertNotIn('--ready', durable)

    def test_existing_transport_is_not_rewritten_or_restarted(self):
        name = self.remote.bridge_name('dev', 'work')
        with patch.object(self.remote, 'request'), patch.object(self.manager, 'discover', return_value=({}, {name: 'live'})), \
                patch.object(self.manager, 'ensure') as ensure, patch.object(self.manager, 'switch') as switch:
            self.remote.switch({'host': 'dev', 'session': 'work'})
            self.assertFalse((self.config / 'layouts').exists())
            ensure.assert_not_called()
            switch.assert_called_once_with(name)


if __name__ == '__main__':
    unittest.main()
