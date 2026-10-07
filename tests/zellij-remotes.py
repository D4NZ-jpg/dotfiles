#!/usr/bin/env python3
"""Remote control-plane contracts, without SSH or persistent sessions."""
import importlib.util
import json
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

BIN = Path(__file__).resolve().parents[1] / 'dot_config/zellij/bin'
sys.dont_write_bytecode = True
sys.path.insert(0, str(BIN))
from remote import Remotes, rpc, SSH_OPTIONS
from workspaces import WorkspaceManager


class RemoteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.config = Path(self.temp.name)
        (self.config / 'remotes.json').write_text(json.dumps({'dev': 'user@dev.example'}))
        self.registry = {'workspaces': {}}
        self.manager = WorkspaceManager({'CONFIG': self.config, 'HOME_STATE': self.config, 'SESSION': 'local',
                                        'transact': lambda fn, path=None: fn(self.registry),
                                        'clean': lambda value, limit: str(value)[:limit]})
        self.remote = self.manager.remotes

    def tearDown(self):
        self.temp.cleanup()

    def bridge_fixture(self):
        name = self.remote.bridge_name('dev', 'work space')
        self.manager.register(name)
        self.registry['workspaces'][name].update(remote_bridge=True, remote_host='dev', remote_session='work space')
        private = self.manager.path('layouts/' + hashlib.sha256(name.encode()).hexdigest() + '.kdl')
        cache = self.config / 'cache/zellij/contract_version_1/session_info' / name / 'session-layout.kdl'
        return name, private, cache

    def test_remote_restore_replaces_native_mosh_and_removes_outer_bar(self):
        name, private, cache = self.bridge_fixture()
        old = 'layout {\n tab {\n  pane { plugin location="zellij:tab-bar"; }\n  pane command="mosh-client" {\n   args "--predict=never" "--control" "/tmp/expired"\n   start_suspended true\n  }\n }\n}\n'
        cache.parent.mkdir(parents=True)
        cache.write_text(old)
        with patch.dict('os.environ', XDG_CACHE_HOME=str(self.config / 'cache')), patch.object(self.remote, 'request') as rpc:
            self.manager.prepare_restore(name)
            rpc.assert_not_called()
        expected = self.remote.bridge_layout('dev', 'work space')
        self.assertEqual(cache.read_text(), expected)
        self.assertEqual(private.read_text(), expected)
        self.assertIn('start_suspended false', expected)
        for unwanted in ['mosh-client', '--control', '--ready', 'tab-bar', 'workspace-bar']:
            self.assertNotIn(unwanted, expected)
        backups = list((self.config / 'restore-backups').glob('*.kdl'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), old)
        with patch.dict('os.environ', XDG_CACHE_HOME=str(self.config / 'cache')):
            self.manager.prepare_restore(name)
        self.assertEqual(len(list((self.config / 'restore-backups').glob('*.kdl'))), 1)

    def test_remote_restore_without_native_cache_repairs_private_recipe(self):
        name, private, cache = self.bridge_fixture()
        private.parent.mkdir(parents=True)
        private.write_text('stale startup recipe')
        with patch.dict('os.environ', XDG_CACHE_HOME=str(self.config / 'cache')):
            self.manager.prepare_restore(name)
        self.assertEqual(private.read_text(), self.remote.bridge_layout('dev', 'work space'))
        self.assertFalse(cache.exists())

    def test_remote_restore_refuses_missing_identity_without_mutation(self):
        name, private, cache = self.bridge_fixture()
        del self.registry['workspaces'][name]['remote_session']
        cache.parent.mkdir(parents=True); cache.write_text('unchanged')
        with patch.dict('os.environ', XDG_CACHE_HOME=str(self.config / 'cache')):
            with self.assertRaisesRegex(ValueError, 'identity'): self.manager.prepare_restore(name)
        self.assertEqual(cache.read_text(), 'unchanged')
        self.assertFalse(private.exists())

    def test_remote_restore_refuses_removed_host_without_mutation(self):
        name, private, cache = self.bridge_fixture()
        (self.config / 'remotes.json').write_text('{}')
        cache.parent.mkdir(parents=True); cache.write_text('unchanged')
        with patch.dict('os.environ', XDG_CACHE_HOME=str(self.config / 'cache')):
            with self.assertRaisesRegex(ValueError, 'allowlisted'): self.manager.prepare_restore(name)
        self.assertEqual(cache.read_text(), 'unchanged')
        self.assertFalse(private.exists())

    def test_remote_recipe_quotes_exact_target_and_validates_it(self):
        layout = self.remote.bridge_layout('dev', 'work space')
        self.assertIn('args "remote-attach" "dev" "work space"', layout)
        self.assertIn('borderless=true', layout)
        with self.assertRaises(ValueError): self.remote.bridge_layout('dev', '../bad')
        with self.assertRaises(ValueError): self.remote.bridge_layout('dev', 'work', '/tmp/x')

    def test_remote_recipe_rejects_expired_controls(self):
        socket = '/tmp/zellij-ws-ssh-expired/c-' + 'a' * 24
        ready = '/tmp/zellij-ws-ssh-expired/ready-' + 'b' * 32
        with self.assertRaisesRegex(ValueError, 'expired'):
            self.remote.bridge_layout('dev', 'work', socket, ready)

    def test_normal_workspace_rejects_remote_start_controls(self):
        self.manager.register('local')
        with patch.dict('os.environ', XDG_CACHE_HOME=str(self.config / 'cache')):
            with self.assertRaisesRegex(ValueError, 'managed remote bridge'):
                self.manager.prepare_restore('local', remote_start=('socket', 'ready'))

    def test_remote_ensure_clears_transient_controls_even_on_start_failure(self):
        name, private, cache = self.bridge_fixture()
        with patch.object(self.manager, 'discover', return_value=({}, {})), \
             patch.object(self.manager, 'prepare_restore') as prepare, \
             patch.object(self.manager, 'cli', side_effect=ValueError('start failed')):
            with self.assertRaisesRegex(ValueError, 'start failed'):
                self.manager.ensure(name, remote_start=('socket', 'ready'))
        self.assertEqual(prepare.call_args_list, [unittest.mock.call(name, remote_start=('socket', 'ready')), unittest.mock.call(name)])

    def test_live_running_transport_is_never_replaced(self):
        import contextlib
        from unittest.mock import Mock
        name, _, _ = self.bridge_fixture()
        call = Mock(return_value=json.dumps([{'id': 0, 'is_plugin': False, 'is_held': False}]))
        self.manager.c['call'] = call
        with patch.object(self.manager, 'session', return_value=contextlib.nullcontext()), patch.object(self.manager, 'prepare_restore') as prepare:
            self.assertFalse(self.manager.repair_stopped_bridge(name, self.registry['workspaces'][name]))
            prepare.assert_not_called()
        call.assert_called_once_with('action', 'list-panes', '--json', '--all')

    def test_live_carrier_with_multiple_terminals_is_never_replaced(self):
        import contextlib
        from unittest.mock import Mock
        name, _, _ = self.bridge_fixture()
        call = Mock(return_value=json.dumps([{'id': 0, 'is_plugin': False, 'is_held': True},
                                            {'id': 1, 'is_plugin': False, 'is_held': False}]))
        self.manager.c['call'] = call
        with patch.object(self.manager, 'session', return_value=contextlib.nullcontext()), patch.object(self.manager, 'prepare_restore') as prepare:
            self.assertFalse(self.manager.repair_stopped_bridge(name, self.registry['workspaces'][name]))
            prepare.assert_not_called()
        self.assertEqual(call.call_count, 1)

    def test_held_transport_repair_removes_only_verified_bar_plugins(self):
        import contextlib
        from unittest.mock import Mock
        name, _, _ = self.bridge_fixture()
        call = Mock(return_value=json.dumps([{'id': 0, 'is_plugin': False, 'is_held': True},
                                            {'id': 5, 'is_plugin': True, 'plugin_url': 'zellij:tab-bar'},
                                            {'id': 6, 'is_plugin': True, 'plugin_url': 'autolock'}]))
        self.manager.c['call'] = call
        with patch.object(self.manager, 'session', return_value=contextlib.nullcontext()), patch.object(self.manager, 'prepare_restore'):
            self.assertTrue(self.manager.repair_stopped_bridge(name, self.registry['workspaces'][name]))
        override = call.call_args_list[1].args
        self.assertEqual(override[:3], ('action', 'override-layout', '--layout-string'))
        self.assertIn('start_suspended false', override[3])
        self.assertIn('--retain-existing-plugin-panes', override)
        self.assertEqual(call.call_args_list[2].args, ('action', 'close-pane', '--pane-id', 'plugin_5'))
        self.assertEqual(call.call_count, 4)

    def test_held_matching_helper_is_retried_if_native_override_reuses_it(self):
        import contextlib
        from unittest.mock import Mock
        name, _, _ = self.bridge_fixture()
        expected = str(self.config / 'bin/zellij-ws') + ' remote-attach dev work space'
        held = [{'id': 8, 'is_plugin': False, 'is_held': True, 'terminal_command': expected}]
        call = Mock(return_value=json.dumps(held)); self.manager.c['call'] = call
        with patch.object(self.manager, 'session', return_value=contextlib.nullcontext()), patch.object(self.manager, 'prepare_restore'):
            self.manager.repair_stopped_bridge(name, self.registry['workspaces'][name])
        self.assertEqual(call.call_args.args, ('action', 'write', '--pane-id', 'terminal_8', '13'))

    def test_repair_never_writes_to_a_transport_that_started_running(self):
        import contextlib
        from unittest.mock import Mock
        name, _, _ = self.bridge_fixture()
        held = [{'id': 8, 'is_plugin': False, 'is_held': True}]
        running = [{'id': 8, 'is_plugin': False, 'is_held': False}]
        call = Mock(side_effect=[json.dumps(held), '', json.dumps(running)]); self.manager.c['call'] = call
        with patch.object(self.manager, 'session', return_value=contextlib.nullcontext()), patch.object(self.manager, 'prepare_restore'):
            self.manager.repair_stopped_bridge(name, self.registry['workspaces'][name])
        self.assertEqual(call.call_count, 3)
        self.assertFalse(any(c.args[:2] == ('action', 'write') for c in call.call_args_list))

    def test_strict_auth_no_forwarding(self):
        flags = ' '.join(SSH_OPTIONS)
        for flag in ['BatchMode=yes', 'StrictHostKeyChecking=yes', 'ForwardAgent=no', 'ClearAllForwardings=yes', 'ControlPath=none']:
            self.assertIn(flag, flags)

    def test_request_data_not_shell(self):
        with patch('remote.subprocess.run') as run:
            run.return_value.returncode = 0
            run.return_value.stdout = '{"result": true}'
            self.assertTrue(self.remote.request('dev', 'focus', session='work space', pane='terminal_1'))
            args, kwargs = run.call_args
            self.assertNotIn('work space', ' '.join(args[0]))
            self.assertEqual(json.loads(kwargs['input'])['session'], 'work space')
            self.assertEqual(kwargs['timeout'], 12)

    def test_readonly_collection_never_ensures(self):
        with patch.object(self.remote, 'request', return_value=[]) as request:
            rows = self.remote.collect('rows')
            self.assertEqual(rows, [])
            request.assert_called_once_with('dev', 'rows')

    def test_offline_no_stale_agents(self):
        with patch.object(self.remote, 'request', side_effect=ValueError('failure')):
            self.assertEqual(self.remote.collect('inventory'), [])
            self.assertEqual(self.remote.errors, ['dev offline'])

    def test_collision_resistant_bridges(self):
        self.assertNotEqual(self.remote.bridge_name('dev', 'home'), self.remote.bridge_name('dev', 'other'))
        self.assertNotEqual(self.remote.bridge_name('dev', 'home'), self.remote.bridge_name('other', 'home'))

    def test_host_allowlist(self):
        (self.config / 'remotes.json').write_text('{"dev":"-oProxyCommand=bad"}')
        with self.assertRaises(ValueError): self.remote.hosts()

    def test_unknown_host_no_ssh(self):
        with patch('remote.subprocess.run') as run:
            with self.assertRaises(KeyError): self.remote.request('unknown', 'rows')
            run.assert_not_called()

    def test_rpc_local_only(self):
        with patch('sys.stdin') as stdin, patch.object(self.manager, 'rows', return_value=[] ) as rows, patch('builtins.print'):
            stdin.read.return_value = '{"operation":"rows"}'
            rpc(self.manager)
            rows.assert_called_once_with(local_only=True)

    def test_no_remote_delete_operation(self):
        with patch('sys.stdin') as stdin:
            stdin.read.return_value = '{"operation":"delete","session":"home"}'
            with self.assertRaisesRegex(ValueError, 'Unsupported'): rpc(self.manager)

    def test_stale_snooze_refuses_before_mutation(self):
        import contextlib
        self.manager.c.update(inventory=lambda: [{'pane': 'terminal_1', 'activity': ['owner', 'stamp', 'done', 2]}],
                              pane_id=lambda value: value, snooze=unittest.mock.Mock())
        with patch('sys.stdin') as stdin, patch.object(self.manager, 'session', return_value=contextlib.nullcontext()):
            stdin.read.return_value = json.dumps({'operation': 'snooze', 'session': 'home', 'pane': 'terminal_1', 'activity': ['old']})
            with self.assertRaisesRegex(ValueError, 'changed'): rpc(self.manager)
            self.manager.c['snooze'].assert_not_called()

    def test_current_snooze_preserves_activity_guard(self):
        import contextlib
        activity = ['owner', 'stamp', 'done', 2]
        self.manager.c.update(inventory=lambda: [{'pane': 'terminal_1', 'activity': activity}],
                              pane_id=lambda value: value, snooze=unittest.mock.Mock(return_value=True))
        with patch('sys.stdin') as stdin, patch.object(self.manager, 'session', return_value=contextlib.nullcontext()), patch('builtins.print'):
            stdin.read.return_value = json.dumps({'operation': 'snooze', 'session': 'home', 'pane': 'terminal_1', 'activity': activity})
            rpc(self.manager)
            self.manager.c['snooze'].assert_called_once_with('terminal_1', activity)

    def test_creation_defaults_local_without_machine_prompt(self):
        from directory import pick_machine_directory
        target = Path(self.temp.name)
        with patch('directory.pick_directory', return_value=target) as browse, patch('modal.pick') as pick:
            self.assertEqual(pick_machine_directory(self.manager), (None, str(target)))
            self.assertTrue(browse.call_args.kwargs['allow_machine'])
            pick.assert_not_called()

    def test_switch_machine_then_browse_remote_directory(self):
        from directory import pick_machine_directory
        with patch('directory.pick_directory', return_value='@machine'), patch('modal.pick', return_value=('0\tdev', '')), patch('directory.pick_remote_directory', return_value='/srv/dev/client') as browser:
            self.assertEqual(pick_machine_directory(self.manager), ('dev', '/srv/dev/client'))
            browser.assert_called_once_with(self.manager, 'dev', None)

    def test_remote_lf_uses_tty_strict_ssh_and_consumes_private_result(self):
        from directory import pick_remote_directory
        with patch('directory.subprocess.run') as run, patch.object(self.remote, 'request', return_value={'kind': 'selected', 'directory': '/remote/path with spaces'}) as request:
            run.return_value.returncode = 0
            self.assertEqual(pick_remote_directory(self.manager, 'dev', '/remote/start with spaces'), '/remote/path with spaces')
            command = run.call_args.args[0]
            self.assertIn('-tt', command)
            self.assertIn('StrictHostKeyChecking=yes', command)
            self.assertIn('ForwardAgent=no', command)
            self.assertIn("'/remote/start with spaces'", command[-1])
            self.assertEqual(request.call_args.args, ('dev', 'directory-result'))
            self.assertRegex(request.call_args.kwargs['token'], r'^[0-9a-f]{32}$')

    def test_remote_lf_alt_m_returns_same_machine_switch_signal(self):
        from directory import pick_remote_directory
        with patch('directory.subprocess.run') as run, patch.object(self.remote, 'request', return_value={'kind': 'machine'}):
            run.return_value.returncode = 0
            self.assertEqual(pick_remote_directory(self.manager, 'dev'), '@machine')

    def test_remote_lf_cancel_does_not_select_a_directory(self):
        from directory import pick_remote_directory
        with patch('directory.subprocess.run') as run, patch.object(self.remote, 'request', return_value={'kind': 'cancel'}):
            run.return_value.returncode = 0
            self.assertIsNone(pick_remote_directory(self.manager, 'dev'))

    def test_remote_lf_failure_still_consumes_result(self):
        from directory import pick_remote_directory
        with patch('directory.subprocess.run') as run, patch.object(self.remote, 'request', return_value={'kind': 'cancel'}) as request:
            run.return_value.returncode = 255
            with self.assertRaisesRegex(ValueError, 'failed'): pick_remote_directory(self.manager, 'dev')
            request.assert_called_once()

    def test_result_token_cannot_escape_private_directory(self):
        from directory import result_path
        with self.assertRaises(ValueError): result_path(self.manager, '../registry')

    def test_result_consumption_removes_only_its_token(self):
        from directory import result_path, take_directory_result
        token = 'a' * 32
        other = 'b' * 32
        self.manager.atomic_text(result_path(self.manager, token), '{"kind":"cancel"}')
        self.manager.atomic_text(result_path(self.manager, other), '{"kind":"machine"}')
        self.assertEqual(take_directory_result(self.manager, token), {'kind': 'cancel'})
        self.assertFalse(result_path(self.manager, token).exists())
        self.assertTrue(result_path(self.manager, other).exists())
        self.assertEqual(result_path(self.manager, other).stat().st_mode & 0o777, 0o600)

    def test_remote_switch_waits_for_client_transfer_not_only_cli_ack(self):
        import os
        self.registry['workspaces']['remote'] = {'remote_host': 'dev'}
        switched = False
        after_source_queries = 0
        def call(*args):
            nonlocal switched, after_source_queries
            if args[1] == 'switch-session':
                switched = True
                return ''
            self.assertEqual(args, ('action', 'list-clients'))
            header = 'CLIENT_ID ZELLIJ_PANE_ID RUNNING_COMMAND'
            if self.manager.c['SESSION'] == 'local':
                if switched: after_source_queries += 1
                return header + ('\n1 terminal_7 picker' if not switched or after_source_queries == 1 else '')
            return header + ('\n2 terminal_0 mosh-client' if switched else '')
        with patch.dict(self.manager.c, {'call': call}), patch.dict(os.environ, {'ZELLIJ_PANE_ID': '7'}), patch.object(self.manager, 'ensure', return_value='remote'), patch('workspaces.time.sleep'):
            self.manager.switch('remote')
        self.assertGreaterEqual(after_source_queries, 2)
        self.assertEqual(self.registry['last'], 'remote')

    def test_remote_project_uses_remote_path_without_local_validation(self):
        with patch('directory.pick_machine_directory', return_value=('dev', '/not/a/local/path/client')), patch('builtins.input', return_value='nice'), patch.object(self.remote, 'switch') as switch, patch.object(self.manager, 'switch') as local:
            self.manager.project()
            switch.assert_called_once_with({'host': 'dev', 'session': 'nice', 'directory': '/not/a/local/path/client'})
            local.assert_not_called()

    def test_remote_tabs_notes_slots_save_route_to_host(self):
        self.registry['workspaces']['local'] = {'remote_host': 'dev', 'remote_session': 'client'}
        with patch.object(self.remote, 'request', return_value=True) as request:
            self.manager.new_tab(cwd='/remote/path')
            self.manager.window_note('test')
            self.manager.slot(3)
            self.manager.save()
            self.assertEqual([call.kwargs['command'] for call in request.call_args_list], ['new-tab', 'note', 'slot', 'save'])
            self.assertTrue(all(call.kwargs['session'] == 'client' for call in request.call_args_list))

    def test_new_tab_directory_defaults_to_workspace_machine(self):
        self.registry['workspaces']['local'] = {'remote_host': 'dev', 'remote_session': 'client'}
        with patch('directory.pick_machine_directory', return_value=('dev', '/remote/task')) as picker, patch.object(self.manager, 'new_tab') as tab:
            self.manager.project(new_tab=True)
            picker.assert_called_once_with(self.manager, 'dev')
            tab.assert_called_once_with(cwd='/remote/task')

    def test_host_visible_narrow_agent_table(self):
        from agent_viewer import line
        row = {'state': 'idle', 'workspace': 'home', 'host': 'dev', 'session_name': 'pi'}
        self.assertIn('dev', line(0, row, 70))


if __name__ == '__main__': unittest.main()
