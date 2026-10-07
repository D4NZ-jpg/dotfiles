import importlib.machinery
import importlib.util
import json
import hashlib
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import sys
sys.dont_write_bytecode = True
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader('ws', str(Path(__file__).resolve().parents[1] / 'dot_config/zellij/bin/executable_zellij-ws'))
spec = importlib.util.spec_from_loader(loader.name, loader)
ws = importlib.util.module_from_spec(spec)
loader.exec_module(ws)

class HelperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='zellij-helper-', dir='/tmp')
        ws.HOME_STATE = Path(self.tmp.name)
        ws.STATE = ws.HOME_STATE / 'panes'
        ws.SESSION = 'trial/with spaces;not shell'
        self.calls = []
        self.live = [{'id': 0, 'tab_id': 0, 'tab_position': 0, 'tab_name': 'project',
                      'title': 'original', 'pane_cwd': '/tmp'}]
        def call(*args):
            self.calls.append(args)
            if args[:2] == ('action', 'list-panes'):
                return json.dumps(self.live)
            return 'terminal_7'
        self.patches = [patch.object(ws, 'call', call), patch.object(ws, 'process_stamp', lambda pid: 'stamp' if pid == 123 else None),
                        patch.dict(os.environ, {'PI_ZELLIJ_NOTIFY': '0', 'ZELLIJ_PANE_ID': '0', 'ZELLIJ_WS_NO_SAVE': '1'})]
        for p in self.patches: p.start()
    def tearDown(self):
        for p in reversed(self.patches): p.stop()
        self.tmp.cleanup()
    def event(self, state, owner='owner', label=None):
        ws.event(SimpleNamespace(state=state, pane='0', owner=owner, pid=123, label=label))
    def data(self): return json.loads(ws.state_file().read_text())
    def test_prompt_bounded_and_updated_separate_from_since(self):
        self.event('start')
        before = self.data()['terminal_0']['since']
        ws.event(SimpleNamespace(state='label', pane='0', owner='owner', pid=123,
                                 label=None, last_prompt='a' * 500))
        row = self.data()['terminal_0']
        self.assertEqual(len(row['last_prompt']), 240)
        self.assertEqual(row['since'], before)
        self.assertGreaterEqual(row['updated'], before)
        self.assertEqual(ws.inventory()[0]['last_prompt'], 'a' * 240)
        self.event('start', owner='replacement')
        self.assertNotIn('last_prompt', self.data()['terminal_0'])

    def test_snooze_hides_attention_but_keeps_fleet_state(self):
        self.event('start'); self.event('done')
        row = ws.inventory()[0]
        self.assertTrue(ws.snooze(row['pane'], row['activity']))
        self.assertEqual(ws.inventory(True), [])
        self.assertEqual(ws.inventory()[0]['state'], 'done')
        self.assertTrue(ws.inventory()[0]['snoozed'])
        self.assertTrue(ws.snooze(row['pane'], row['activity']))
        self.assertEqual(len(ws.inventory(True)), 1)

    def test_snooze_clears_on_next_work_and_completion(self):
        self.event('start'); self.event('done')
        row = ws.inventory()[0]; ws.snooze(row['pane'], row['activity'])
        self.event('working'); self.event('done')
        self.assertFalse(ws.inventory(True)[0]['snoozed'])

    def test_snooze_survives_renaming_and_duplicate_done(self):
        self.event('start'); self.event('done')
        row = ws.inventory()[0]; ws.snooze(row['pane'], row['activity'])
        self.event('label', label='renamed'); ws.note('new task'); self.event('done')
        self.assertEqual(ws.inventory(True), [])
        self.assertTrue(ws.inventory()[0]['snoozed'])

    def test_new_asking_and_prompt_clear_snooze(self):
        self.event('start'); self.event('asking')
        row = ws.inventory()[0]; ws.snooze(row['pane'], row['activity'])
        self.event('asking')
        self.assertEqual(len(ws.inventory(True)), 1)
        row = ws.inventory()[0]; ws.snooze(row['pane'], row['activity'])
        ws.event(SimpleNamespace(state='label', pane='0', owner='owner', pid=123,
                                 label=None, last_prompt='new user prompt'))
        self.assertEqual(len(ws.inventory(True)), 1)

    def test_snooze_cannot_acknowledge_newer_activity_or_owner(self):
        self.event('start'); self.event('done'); row = ws.inventory()[0]
        self.event('working'); self.event('done')
        self.assertFalse(ws.snooze(row['pane'], row['activity']))
        row = ws.inventory()[0]
        self.event('start', owner='replacement'); self.event('done', owner='replacement')
        self.assertFalse(ws.snooze(row['pane'], row['activity']))
        self.assertFalse(ws.snooze('terminal_99', row['activity']))

    def test_exit_is_new_attention_after_snoozing_done(self):
        self.event('start'); self.event('done'); row = ws.inventory()[0]
        ws.snooze(row['pane'], row['activity'])
        with patch.object(ws, 'process_stamp', lambda _: None):
            self.assertEqual(ws.inventory(True)[0]['state'], 'exited')
            self.assertFalse(ws.inventory(True)[0]['snoozed'])

    def pointer_event(self, state, pointer=None, owner='owner', restore_token=None):
        ws.event(SimpleNamespace(state=state, pane='0', owner=owner, pid=123,
                                 label='task' if state == 'start' else None,
                                 session_file=pointer, restore_token=restore_token))

    def test_matching_restored_thread_keeps_its_token(self):
        self.pointer_event('start', '/tmp/exact.jsonl')
        token = self.data()['terminal_0']['token']
        self.pointer_event('shutdown')
        self.pointer_event('start', '/tmp/exact.jsonl', owner='restored', restore_token=token)
        self.assertEqual(self.data()['terminal_0']['token'], token)

    def test_switch_after_restore_cannot_redirect_original_token(self):
        self.pointer_event('start', '/tmp/original.jsonl')
        token = self.data()['terminal_0']['token']
        self.pointer_event('shutdown')
        self.pointer_event('start', '/tmp/new.jsonl', owner='new', restore_token=token)
        row = self.data()['terminal_0']
        self.assertNotEqual(row['token'], token)
        self.assertEqual(ws.manager.load_agent(token)['session_file'], '/tmp/original.jsonl')
        self.assertEqual(ws.manager.load_agent(row['token'])['session_file'], '/tmp/new.jsonl')

    def test_unknown_restored_pointer_cannot_reuse_original_token(self):
        self.pointer_event('start', '/tmp/original.jsonl')
        token = self.data()['terminal_0']['token']
        self.pointer_event('start', restore_token=token)
        row = self.data()['terminal_0']
        self.assertNotEqual(row['token'], token)
        self.assertNotIn('session_file', row)
        self.assertEqual(ws.manager.load_agent(token)['session_file'], '/tmp/original.jsonl')

    def test_changed_pointer_on_update_gets_a_new_durable_token(self):
        self.pointer_event('start', '/tmp/original.jsonl')
        token = self.data()['terminal_0']['token']
        self.pointer_event('label', '/tmp/new.jsonl')
        row = self.data()['terminal_0']
        self.assertNotEqual(row['token'], token)
        self.assertEqual(ws.manager.load_agent(token)['session_file'], '/tmp/original.jsonl')
        self.assertEqual(ws.manager.load_agent(row['token'])['session_file'], '/tmp/new.jsonl')

    def test_shutdown_persists_pointer_first_available_at_shutdown(self):
        self.pointer_event('start')
        pointer = str(Path(self.tmp.name) / 'exact.jsonl')
        self.pointer_event('shutdown', pointer)
        row = self.data()['terminal_0']
        self.assertEqual(row['session_file'], pointer)
        self.assertNotIn('owner', row)
        self.assertEqual(ws.manager.load_agent(row['token'])['session_file'], pointer)
        self.assertEqual(ws.title(row), 'task · p0')

    def test_shutdown_keeps_existing_pointer_and_token(self):
        self.pointer_event('start', '/tmp/exact-thread.jsonl')
        token = self.data()['terminal_0']['token']
        self.pointer_event('shutdown')
        row = self.data()['terminal_0']
        self.assertEqual(row['token'], token)
        self.assertEqual(row['session_file'], '/tmp/exact-thread.jsonl')
        self.assertNotIn('pid', row); self.assertNotIn('owner', row)

    def test_late_old_shutdown_cannot_replace_new_thread_pointer(self):
        self.pointer_event('start', '/tmp/old.jsonl', owner='old')
        self.pointer_event('start', '/tmp/new.jsonl', owner='new')
        self.pointer_event('shutdown', '/tmp/wrong.jsonl', owner='old')
        row = self.data()['terminal_0']
        self.assertEqual(row['owner'], 'new')
        self.assertEqual(row['session_file'], '/tmp/new.jsonl')

    def test_reload_new_owner_retains_explicit_same_thread(self):
        self.pointer_event('start', '/tmp/exact.jsonl', owner='old')
        self.pointer_event('shutdown', owner='old')
        self.pointer_event('start', '/tmp/exact.jsonl', owner='new')
        self.assertEqual(self.data()['terminal_0']['session_file'], '/tmp/exact.jsonl')
        self.assertEqual(self.data()['terminal_0']['owner'], 'new')

    def test_new_session_without_pointer_does_not_inherit_old_thread(self):
        self.pointer_event('start', '/tmp/old.jsonl')
        old_token = self.data()['terminal_0']['token']
        self.pointer_event('start', owner='replacement')
        row = self.data()['terminal_0']
        self.assertNotIn('session_file', row)
        self.assertNotEqual(old_token, row['token'])

    def test_start_and_work(self):
        self.event('start', label='task'); self.event('working')
        self.assertEqual(self.data()['terminal_0']['state'], 'working')
        self.assertEqual(self.calls[-1][-1], '[WORK] task · p0')
    def test_all_attention_states(self):
        self.event('start')
        for state in ['asking', 'done', 'error']:
            self.event(state); self.assertEqual(ws.inventory(True)[0]['state'], state)
    def test_work_not_attention(self):
        self.event('start'); self.event('working'); self.assertEqual(ws.inventory(True), [])
    def test_note_survives_title_events(self):
        self.event('start', label='old'); ws.note('manual task'); self.event('label', label='new')
        self.event('done'); self.assertEqual(self.calls[-1][-1], '[DONE] manual task · p0')
    def test_clear_note_reveals_label(self):
        self.event('start', label='name'); ws.note('manual'); ws.note('')
        self.assertEqual(self.calls[-1][-1], '[IDLE] name · p0')
    def test_owner_rejects_late_shutdown(self):
        self.event('start', owner='old'); self.event('start', owner='new')
        self.event('shutdown', owner='old'); self.assertEqual(self.data()['terminal_0']['owner'], 'new')
    def test_shutdown_clears_agent_preserves_note(self):
        self.event('start'); ws.note('task'); self.event('shutdown')
        row = self.data()['terminal_0']; self.assertNotIn('state', row); self.assertEqual(row['note'], 'task')
    def test_dead_pid_is_exited_attention(self):
        self.event('start'); self.event('done')
        with patch.object(ws, 'process_stamp', lambda _: None):
            self.assertEqual(ws.inventory(True)[0]['state'], 'exited')
            self.assertEqual(self.calls[-1][-1], '[EXIT] pi · p0')
            self.assertEqual(ws.inventory()[0]['state'], 'exited')
    def test_prunes_closed_panes(self):
        self.event('start'); self.live = []; self.assertEqual(ws.inventory(), [])
        self.assertEqual(self.data(), {})
    def test_file_permissions(self):
        self.event('start'); self.assertEqual(ws.state_file().stat().st_mode & 0o777, 0o600)
    def test_path_no_session_injection(self):
        self.assertEqual(ws.state_file().parent, ws.STATE)
        self.assertNotIn('trial', ws.state_file().name)
    def test_bad_pane_rejected(self):
        for value in ['plugin_1', '../x', '0;touch /tmp/x', '']:
            with self.assertRaises(ValueError): ws.pane_id(value)
    def test_note_missing_pane_rejected(self):
        with self.assertRaises(ValueError): ws.note('task', 'terminal_99')
    def test_focus_missing_pane_rejected(self):
        with self.assertRaises(ValueError): ws.focus('terminal_99')
    def test_no_transcript_fields(self):
        self.event('start'); self.event('done')
        self.assertEqual(set(self.data()['terminal_0']), {'owner', 'pid', 'stamp', 'label', 'state', 'since', 'updated', 'activity_id', 'token', 'pane', 'note'})
    def test_same_state_does_not_reset_age(self):
        self.event('start'); self.event('asking'); before = self.data()['terminal_0']['since']
        self.event('asking'); self.assertEqual(self.data()['terminal_0']['since'], before)
    def test_open_argv_not_shell_interpolated(self):
        ws.open_command(SimpleNamespace(command=['--', 'echo', 'x;rm -rf nope'], cwd='/tmp', kind='split',
                                        direction='right', name='tools', note=None, focus=False, workspace=None))
        self.assertEqual(self.calls[-1][-3:], ('--', 'echo', 'x;rm -rf nope'))
        self.assertIn('--no-focus', self.calls[-1])
    def test_notification_only_once_per_attention_transition(self):
        notices = []
        with patch.dict(os.environ, {'PI_ZELLIJ_NOTIFY': '1'}), patch.object(ws.shutil, 'which', lambda _: '/fake/notify-send'), patch.object(ws.subprocess, 'run', lambda args, **kw: notices.append(args)):
            self.event('start')
            self.event('working')
            for state in ['asking', 'done', 'error']:
                self.event(state)
                self.event(state)
            self.assertEqual(len(notices), 3)
            self.assertEqual(notices[0][-1], 'Needs your input')
    def test_display_sanitizes_controls(self):
        self.assertNotIn('\x1b', ws.clean('x\x1b[31m\nfoo\tbar'))

class WorkspaceTests(HelperTests):
    def native_cache(self, layout):
        path = Path(self.tmp.name) / 'cache/zellij/contract_version_1/session_info' / ws.SESSION / 'session-layout.kdl'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(layout)
        return path

    def test_prepare_restore_after_clean_shutdown_handles_lagged_titles(self):
        self.pointer_event('start', '/tmp/exact.jsonl')
        self.pointer_event('shutdown')
        token = self.data()['terminal_0']['token']
        for title in ['task · p0', '[DONE] task · p0', '[EXIT] task · p0']:
            original = 'layout {\n tab name="1:task" {\n  pane command="pi" name="' + title + '" {\n   args "old"\n  }\n }\n}\n'
            cache = self.native_cache(original)
            with patch.dict(os.environ, {'XDG_CACHE_HOME':str(Path(self.tmp.name) / 'cache')}):
                ws.manager.prepare_restore(ws.SESSION)
            patched = cache.read_text()
            self.assertIn('zellij-agent', patched)
            self.assertIn('args "' + token + '"', patched)
            self.assertIn('start_suspended false', patched)
            self.assertNotIn('args "old"', patched)
        self.assertEqual(ws.manager.load_agent(token)['session_file'], '/tmp/exact.jsonl')

    def test_late_pointer_is_persisted_even_with_an_unidentified_sibling(self):
        self.pointer_event('start')
        token = self.data()['terminal_0']['token']
        pointer = str(Path(self.tmp.name) / 'exact.jsonl')
        Path(pointer).touch()
        original_call = ws.call
        def call(*args):
            if args[:2] == ('action', 'dump-layout'):
                return ('layout {\n cwd "/tmp"\n'
                        ' pane command="pi" name="[DONE] task · p0" {\n }\n'
                        ' pane command="pi" name="[DONE] unknown · p8" {\n  start_suspended true\n }\n}\n')
            return original_call(*args)
        with patch.dict(os.environ, {'ZELLIJ_WS_NO_SAVE': '0'}), patch.object(ws, 'call', call), \
                patch.object(ws.manager, 'register', return_value=('fixture', {})):
            self.pointer_event('done', pointer)
        self.assertEqual(self.data()['terminal_0']['token'], token)
        self.assertEqual(ws.manager.load_agent(token)['session_file'], pointer)
        saved = ws.manager.path('layouts/' + hashlib.sha256(b'fixture').hexdigest() + '.kdl').read_text()
        self.assertIn('args "' + token + '"', saved)
        self.assertIn('start_suspended false', saved)
        self.assertIn('pane name="shell"', saved)
        self.assertNotIn('command="pi"', saved)

    def test_save_after_shutdown_uses_durable_pointer_not_live_owner(self):
        self.pointer_event('start', '/tmp/exact.jsonl')
        self.pointer_event('shutdown')
        token = self.data()['terminal_0']['token']
        self.live[0]['title'] = 'task · p0'
        original_call = ws.call
        def call(*args):
            if args[:2] == ('action', 'dump-layout'):
                return 'layout {\n tab name="1:task" {\n  pane command="pi" name="[DONE] task · p0" {\n  }\n }\n}\n'
            return original_call(*args)
        with patch.object(ws, 'call', call), patch.object(ws.manager, 'register', return_value=('fixture', {})):
            ws.manager.save()
        saved = ws.manager.path('layouts/' + hashlib.sha256(b'fixture').hexdigest() + '.kdl').read_text()
        self.assertIn('args "' + token + '"', saved)
        self.assertIn('start_suspended false', saved)

    def test_closed_agents_sharing_a_task_keep_separate_restore_tokens(self):
        rows = {'terminal_0':dict(token='a'*32, session_file='/tmp/first.jsonl', note='same', pane='terminal_0'),
                'terminal_1':dict(token='b'*32, session_file='/tmp/second.jsonl', note='same', pane='terminal_1')}
        ws.transact(lambda d:d.update(rows))
        cache = self.native_cache('layout {\n tab name="1:same" {\n  pane command="pi" name="same · p0" {\n  }\n  pane command="pi" name="same · p1" {\n  }\n }\n}\n')
        with patch.dict(os.environ, {'XDG_CACHE_HOME':str(Path(self.tmp.name) / 'cache')}):
            ws.manager.prepare_restore(ws.SESSION)
        saved = cache.read_text()
        self.assertIn('args "' + 'a'*32 + '"', saved)
        self.assertIn('args "' + 'b'*32 + '"', saved)
        self.assertEqual(saved.count('start_suspended false'), 2)

    def test_ambiguous_durable_records_refuse_without_rewriting_cache(self):
        rows = {'terminal_0':dict(token='a'*32, session_file='/tmp/first.jsonl', note='same', pane='terminal_0'),
                'terminal_1':dict(token='b'*32, session_file='/tmp/second.jsonl', note='same', pane='terminal_0')}
        ws.transact(lambda d:d.update(rows))
        original = 'layout {\n pane command="pi" name="same · p0" {\n }\n}\n'
        cache = self.native_cache(original)
        with patch.dict(os.environ, {'XDG_CACHE_HOME':str(Path(self.tmp.name) / 'cache')}):
            with self.assertRaisesRegex(ValueError, 'Ambiguous Pi restoration title'):
                ws.manager.prepare_restore(ws.SESSION)
        self.assertEqual(cache.read_text(), original)

    def test_existing_token_cannot_be_reassigned_to_another_file(self):
        row = dict(token='a'*32, session_file='/tmp/original.jsonl')
        ws.manager.save_agent(row)
        with self.assertRaisesRegex(ValueError, 'refusing to redirect'):
            ws.manager.save_agent(dict(row, session_file='/tmp/different.jsonl'))
        self.assertEqual(ws.manager.load_agent(row['token'])['session_file'], '/tmp/original.jsonl')

    def test_new_pointerless_session_restores_shell_not_old_thread(self):
        self.pointer_event('start', '/tmp/original.jsonl')
        self.pointer_event('shutdown')
        self.pointer_event('start', owner='new')
        original = 'layout {\n pane command="pi" name="task · p0" {\n }\n}\n'
        cache = self.native_cache(original)
        with patch.dict(os.environ, {'XDG_CACHE_HOME':str(Path(self.tmp.name) / 'cache')}):
            ws.manager.prepare_restore(ws.SESSION)
        self.assertNotIn('command="pi"', cache.read_text())
        self.assertNotIn('zellij-agent', cache.read_text())
        self.assertIn('pane name="shell"', cache.read_text())
        backups = list(ws.manager.path('restore-backups').glob('*.kdl'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), original)

    def test_pointer_without_token_restores_shell_without_guessing(self):
        ws.transact(lambda d:d.update(terminal_0=dict(session_file='/tmp/exact.jsonl', pane='terminal_0', label='task')))
        original = 'layout {\n pane command="pi" name="task · p0" {\n }\n}\n'
        cache = self.native_cache(original)
        with patch.dict(os.environ, {'XDG_CACHE_HOME':str(Path(self.tmp.name) / 'cache')}):
            ws.manager.prepare_restore(ws.SESSION)
        self.assertNotIn('command="pi"', cache.read_text())
        self.assertNotIn('zellij-agent', cache.read_text())
        self.assertIn('pane name="shell"', cache.read_text())

    def seed_removal(self):
        name = 'remove-me'
        registry = dict(workspaces={ws.SESSION: dict(name='Current', order=0),
                                    name: dict(name='Remove me', order=1)},
                        next_order=2, last=name, previous=ws.SESSION,
                        next_slot={name: 7, ws.SESSION: 3})
        ws.manager.tx(lambda data: data.update(registry))
        ws.manager.tx(lambda data: data.update({name: {'1:task': 'Task'}, ws.SESSION: {}}), 'tab-notes.json')
        digest = hashlib.sha256(name.encode()).hexdigest()
        layout = ws.manager.path('layouts/' + digest + '.kdl')
        layout.parent.mkdir(parents=True, exist_ok=True)
        layout.write_text('saved layout')
        pane = ws.STATE / (digest + '.json')
        pane.parent.mkdir(parents=True, exist_ok=True)
        pane.write_text('{}')
        conversation = Path(self.tmp.name) / 'private-thread.jsonl'
        conversation.write_text('conversation sentinel')
        return name, registry, layout, pane, conversation

    def test_remove_cleans_workspace_state_not_conversations_or_order(self):
        name, registry, layout, pane, conversation = self.seed_removal()
        with patch.object(ws.manager, 'discover', return_value=(registry, {name: 'live'})):
            with patch.object(ws.manager, 'cli') as cli:
                ws.manager.remove_workspace('Remove me')
        cli.assert_called_once_with('delete-session', '--force', name)
        data = ws.manager.tx(lambda d: dict(d))
        self.assertNotIn(name, data['workspaces'])
        self.assertEqual(data['last'], ws.SESSION)
        self.assertNotIn('previous', data)
        self.assertEqual(data['next_order'], 2)
        self.assertEqual(data['next_slot'], {ws.SESSION: 3})
        self.assertFalse(layout.exists()); self.assertFalse(pane.exists())
        self.assertNotIn(name, ws.manager.tx(lambda d: dict(d), 'tab-notes.json'))
        self.assertEqual(conversation.read_text(), 'conversation sentinel')

    def test_remove_native_failure_keeps_registry_and_private_state(self):
        name, registry, layout, pane, _ = self.seed_removal()
        with patch.object(ws.manager, 'discover', return_value=(registry, {name: 'live'})):
            with patch.object(ws.manager, 'cli', side_effect=ws.subprocess.CalledProcessError(1, ['delete-session'])):
                with self.assertRaises(ws.subprocess.CalledProcessError): ws.manager.remove_workspace(name)
        self.assertIn(name, ws.manager.tx(lambda d: dict(d))['workspaces'])
        self.assertTrue(layout.exists()); self.assertTrue(pane.exists())

    def test_remove_saved_only_workspace_skips_native_delete(self):
        name, registry, _, _, _ = self.seed_removal()
        with patch.object(ws.manager, 'discover', return_value=(registry, {})):
            with patch.object(ws.manager, 'cli') as cli:
                ws.manager.remove_workspace(name)
        cli.assert_not_called()
        self.assertNotIn(name, ws.manager.tx(lambda d: dict(d))['workspaces'])

    def test_remove_current_alias_is_refused_before_any_native_call(self):
        self.seed_removal()
        with patch.object(ws.manager, 'cli') as cli:
            with self.assertRaisesRegex(ValueError, 'Switch to another workspace'):
                ws.manager.remove_workspace('Current')
        cli.assert_not_called()

    def test_remove_confirmation_defaults_to_cancel_and_escape_cancels(self):
        import modal
        row = dict(session='other', name='Other')
        for answer in [(None, None), ('cancel\tCancel', '')]:
            with patch.object(modal, 'pick', return_value=answer) as picker:
                with patch.object(ws.manager, 'remove_workspace') as remove:
                    ws.manager.confirm_remove(row)
            self.assertEqual(picker.call_args.args[0][0], 'cancel\tCancel')
            self.assertIn('Stops programs', picker.call_args.args[1])
            self.assertIn('Pi conversations are kept.', picker.call_args.args[1])
            remove.assert_not_called()

    def test_remove_confirmation_passes_exact_session_not_label(self):
        import modal
        with patch.object(modal, 'pick', return_value=('remove\tRemove', '')):
            with patch.object(ws.manager, 'remove_workspace') as remove:
                ws.manager.confirm_remove(dict(session='other', name='Renamed'))
        remove.assert_called_once_with('other')

    def test_picker_remove_action_refreshes_without_switching(self):
        import modal
        row = dict(session='other', name='Other', group='', status='live')
        with patch.object(ws.manager, 'rows', side_effect=[[row], []]):
            with patch.object(modal, 'pick', side_effect=[('0\tOther', 'd'), (None, None)]) as picker:
                with patch.object(ws.manager, 'confirm_remove') as confirm, patch.object(ws.manager, 'switch') as switch:
                    ws.manager.pick('workspaces')
        confirm.assert_called_once_with(row)
        switch.assert_not_called()
        self.assertIn('d', picker.call_args_list[0].kwargs['extra'])

    def test_workspace_picker_icons_preserve_labels_and_order(self):
        import modal
        from agent_viewer import ARCHIVE_ICON, TERMINAL_ICON
        rows = [dict(session='first', name='First', group='', status='saved'),
                dict(session='second', name='Second', group='dev', status='live')]
        with patch.object(ws.manager, 'rows', return_value=rows):
            with patch.object(modal, 'pick', return_value=(None, None)) as picker:
                ws.manager.pick('workspaces')
        self.assertEqual(picker.call_args.args[0], [f'0\t{ARCHIVE_ICON}  First · saved',
                                                   f'1\t{TERMINAL_ICON}  dev/Second · live'])

    def test_task_icons_use_agent_state_not_task_name(self):
        import modal
        from agent_viewer import PI_ICON, TERMINAL_ICON
        base = dict(session='other', workspace='Other', group='', tab='task')
        rows = [dict(base, pane='terminal_1', state='shell', note='pi'),
                dict(base, pane='terminal_2', state='working', note='shell'),
                dict(base, pane='terminal_3', state='exited', note='old agent')]
        with patch.object(ws.manager, 'inventory', return_value=rows):
            with patch.object(modal, 'pick', return_value=(None, None)) as picker:
                ws.manager.pick('tree')
        lines = picker.call_args.args[0]
        self.assertTrue(lines[0].startswith(f'0\t{TERMINAL_ICON}  '))
        self.assertTrue(lines[1].startswith(f'1\t{PI_ICON}  '))
        self.assertTrue(lines[2].startswith(f'2\t{PI_ICON}  '))
        self.assertIn('Enter focus', picker.call_args.args[1])

    def test_picker_snooze_targets_exact_workspace_without_focus(self):
        import modal
        row = dict(session='other', workspace='Other', group='', pane='terminal_5',
                   tab='task', note='task', state='done', activity=['owner', 'stamp', 'done', 2])
        calls = []
        def snooze(pane, activity):
            calls.append((ws.SESSION, pane, activity))
        with patch.object(ws.manager, 'inventory', side_effect=[[row], []]):
            with patch.object(modal, 'pick', side_effect=[('0\trow', 's'), (None, None)]) as picker:
                with patch.dict(ws.manager.c, {'snooze': snooze}), patch.object(ws.manager, 'switch') as switch:
                    ws.manager.pick('attention')
        self.assertEqual(calls, [('other', 'terminal_5', row['activity'])])
        self.assertEqual(picker.call_args_list[0].kwargs['extra'], ['s'])
        switch.assert_not_called()
        self.assertEqual(ws.SESSION, 'trial/with spaces;not shell')

    def test_project_lf_selection_opens_workspace(self):
        import directory
        home = Path(self.tmp.name)
        target = home / 'dev' / 'project'
        target.mkdir(parents=True)
        with patch.object(ws.manager.remotes, 'hosts', return_value={}), patch('workspaces.Path.home', return_value=home), patch.object(directory, 'pick_directory', return_value=target) as picker:
            with patch('builtins.input', return_value=''), patch.object(ws.manager, 'switch') as switch:
                ws.manager.project()
        picker.assert_called_once_with(ws.CONFIG / 'directory-picker.lfrc', home / 'dev')
        switch.assert_called_once_with('project', str(target))
    def test_project_lf_selection_creates_task_tab(self):
        import directory
        home = Path(self.tmp.name)
        target = home / 'dev' / 'project'
        target.mkdir(parents=True)
        with patch('workspaces.Path.home', return_value=home), patch.object(directory, 'pick_directory', return_value=target):
            with patch.object(ws.manager, 'new_tab') as new_tab:
                ws.manager.project(new_tab=True)
        new_tab.assert_called_once_with(cwd=str(target))
    def test_project_lf_cancel_does_not_open_workspace(self):
        import directory
        with patch.object(directory, 'pick_directory', return_value=None):
            with patch.object(ws.manager, 'switch') as switch:
                ws.manager.project()
        switch.assert_not_called()
    def test_task_name_renames_tab_and_all_its_panes(self):
        self.live = [dict(id=0, tab_id=17, tab_name='6:shell'),
                     dict(id=1, tab_id=17, tab_name='6:shell'),
                     dict(id=2, tab_id=18, tab_name='7:other')]
        with patch.object(ws.manager, 'save'):
            ws.manager.window_note('API tests')
        self.assertIn(('action', 'rename-tab', '--tab-id', '17', '6:API tests'), self.calls)
        self.assertEqual(self.data()['terminal_0']['note'], 'API tests')
        self.assertEqual(self.data()['terminal_1']['note'], 'API tests')
        self.assertNotIn('terminal_2', self.data())
        notes = ws.manager.tx(lambda d: d.copy(), 'tab-notes.json')
        self.assertEqual(notes[ws.SESSION]['6:API tests'], 'API tests')
    def test_task_name_can_target_an_inactive_tab(self):
        self.live = [dict(id=0, tab_id=1, tab_name='1:here'),
                     dict(id=2, tab_id=9, tab_name='8:elsewhere')]
        with patch.object(ws.manager, 'save'):
            ws.manager.window_note('Review', 'terminal_2')
        self.assertIn(('action', 'rename-tab', '--tab-id', '9', '8:Review'), self.calls)
        self.assertNotIn('terminal_0', self.data())
    def test_clear_task_name_resets_shell_without_renumbering(self):
        self.live = [dict(id=0, tab_id=17, tab_name='6:API tests')]
        ws.manager.tx(lambda d: d.update({ws.SESSION: {'6:API tests': 'API tests'}}), 'tab-notes.json')
        with patch.object(ws.manager, 'save'):
            ws.manager.window_note('')
        self.assertIn(('action', 'rename-tab', '--tab-id', '17', '6:shell'), self.calls)
        notes = ws.manager.tx(lambda d: d.copy(), 'tab-notes.json')[ws.SESSION]
        self.assertEqual(notes, {'6:shell': 'shell'})
    def test_empty_attention_opens_cancellable_picker(self):
        import modal
        with patch.object(ws.manager, 'inventory', return_value=[]):
            with patch.object(modal, 'pick', return_value=(None, None)) as picker:
                ws.manager.pick('attention')
        picker.assert_called_once_with([], 'No agents need attention.')
    def test_empty_picker_has_no_blank_candidate_or_auto_exit(self):
        import modal
        result = SimpleNamespace(returncode=130, stdout='')
        with patch.object(modal.subprocess, 'run', return_value=result) as runner:
            self.assertEqual(modal.pick([], 'No agents need attention.'), (None, None))
        self.assertEqual(runner.call_args.kwargs['input'], '')
        self.assertIn('--no-exit-0', runner.call_args.args[0])
        self.assertIn('--no-select-1', runner.call_args.args[0])
    def test_top_tabs_are_idempotent_and_preserved_on_restore(self):
        from workspaces import with_top_tabs, rewrite_layout, WORKSPACE_BAR_URL
        original = 'layout {\n    tab name="1:shell" {\n        pane\n    }\n    new_tab_template {\n        pane\n    }\n}\n'
        patched = with_top_tabs(original)
        self.assertEqual(patched.count(WORKSPACE_BAR_URL), 2)
        self.assertEqual(with_top_tabs(patched), patched)
        restored, _ = rewrite_layout(patched, {}, '/safe/agent')
        self.assertEqual(restored.count(WORKSPACE_BAR_URL), 2)
        self.assertNotIn('zellij:compact-bar', restored)

    def test_native_and_canonical_workspace_bars_migrate_without_duplicates(self):
        from workspaces import with_top_tabs, WORKSPACE_BAR_URL
        canonical = WORKSPACE_BAR_URL.replace('file:~', 'file:' + str(Path.home()), 1)
        for location in ['zellij:tab-bar', WORKSPACE_BAR_URL, canonical]:
            original = 'layout {\n tab {\n  pane size=1 borderless=true {\n   plugin location=' + json.dumps(location) + ' {\n    hide_swap_layout_indication true\n   }\n  }\n  pane\n }\n}\n'
            patched = with_top_tabs(original)
            self.assertEqual(patched.count(WORKSPACE_BAR_URL), 1)
            self.assertEqual(patched.count('pane size=1'), 1)
            self.assertNotIn('zellij:tab-bar', patched)
            self.assertEqual(with_top_tabs(patched), patched)
    def run_restore_wrapper(self, pointer, active=False):
        import contextlib, io, runpy, subprocess
        token = 'c' * 32
        ws.manager.save_agent(dict(token=token, session_file=str(pointer)))
        if active:
            stamp = Path(f'/proc/{os.getpid()}/stat').read_text().rsplit(')', 1)[1].split()[19]
            ws.transact(lambda d:d.update(terminal_0=dict(owner='active', pid=os.getpid(),
                                                        stamp=stamp, session_file=str(pointer))))
        class ShellReached(BaseException): pass
        output = io.StringIO()
        source = Path(__file__).resolve().parents[1] / 'dot_config/zellij/bin/executable_zellij-agent'
        with patch.dict(os.environ, {'ZELLIJ_WS_STATE':self.tmp.name, 'SHELL':'/bin/sh'}), \
             patch.object(sys, 'argv', [str(source), token]), \
             patch('shutil.which', return_value=None), \
             patch.object(subprocess, 'run') as runner, \
             patch.object(os, 'execvp', side_effect=ShellReached), contextlib.redirect_stderr(output):
            with self.assertRaises(ShellReached): runpy.run_path(str(source), run_name='__main__')
        return runner, output.getvalue(), token

    def test_restore_wrapper_refuses_missing_exact_file_without_launch(self):
        runner, output, _ = self.run_restore_wrapper(Path(self.tmp.name) / 'missing.jsonl')
        runner.assert_not_called()
        self.assertIn('saved Pi session file is missing', output)

    def test_restore_wrapper_refuses_a_still_active_exact_thread(self):
        pointer = Path(self.tmp.name) / 'exact.jsonl'; pointer.write_text('')
        runner, output, _ = self.run_restore_wrapper(pointer, active=True)
        runner.assert_not_called()
        self.assertIn('already running in Zellij', output)

    def test_restore_wrapper_passes_only_the_exact_recorded_file(self):
        pointer = Path(self.tmp.name) / 'exact.jsonl'; pointer.write_text('')
        runner, output, token = self.run_restore_wrapper(pointer)
        self.assertEqual(output, '')
        runner.assert_called_once()
        self.assertEqual(runner.call_args.args[0], ['pi', '--session', str(pointer)])
        self.assertEqual(runner.call_args.kwargs['env']['ZELLIJ_RESTORE_TOKEN'], token)

    def test_cli_uses_durable_temp_directory(self):
        import workspaces
        result = SimpleNamespace(stdout='')
        with patch.dict(os.environ, {'TMPDIR': '/tmp/removed-sandbox'}):
            with patch.object(workspaces.subprocess, 'run', return_value=result) as runner:
                ws.manager.cli('list-sessions', '--no-formatting')
        self.assertEqual(runner.call_args.kwargs['env']['TMPDIR'], '/tmp')
    def test_empty_server_allows_fresh_start(self):
        import subprocess
        error = subprocess.CalledProcessError(1, ['zellij'], stderr='No active zellij sessions found.\n')
        with patch.object(ws.manager, 'cli', side_effect=error):
            data, found = ws.manager.discover()
        self.assertEqual(found, {})
    def test_discovery_does_not_hide_other_errors(self):
        import subprocess
        error = subprocess.CalledProcessError(1, ['zellij'], stderr='Invalid configuration')
        with patch.object(ws.manager, 'cli', side_effect=error):
            with self.assertRaises(subprocess.CalledProcessError): ws.manager.discover()
    def test_creation_order_survives_rename_and_group(self):
        ws.manager.register('first', '/tmp', 'work')
        ws.manager.register('second', '/tmp', 'side')
        ws.manager.tx(lambda d: d['workspaces']['first'].update(name='renamed', group='projects'))
        data = ws.manager.tx(lambda d: d.copy())
        self.assertLess(data['workspaces']['first']['order'], data['workspaces']['second']['order'])
        self.assertEqual(ws.manager.resolve('renamed'), 'first')
    def test_bad_workspace_name(self):
        for name in ['../escape', 'foo/bar', 'bad\nname', '']:
            with self.assertRaises(ValueError): ws.manager.validate_name(name)
    def test_restore_token_path_guard(self):
        with self.assertRaises(ValueError): ws.manager.load_agent('../escape')
    def test_layout_rewrite_keeps_geometry_and_resumes_exact_thread(self):
        from workspaces import rewrite_layout
        text = 'layout {\n    tab name="1:pi" {\n        pane command="pi" name="[WORK] task · p0" {\n            cwd "/tmp"\n            args "old"\n            width 60\n            start_suspended false\n        }\n    }\n}\n'
        patched, matched = rewrite_layout(text, {'[WORK] task · p0': {'token': 'a' * 32}}, '/safe/agent')
        self.assertEqual(matched, {'[WORK] task · p0'})
        self.assertIn('command="/safe/agent"', patched)
        self.assertIn('start_suspended false', patched)
        self.assertIn('width 60', patched)
        self.assertNotIn('args "old"', patched)
    def test_old_managed_wrapper_resumes_its_exact_token_without_pane_metadata(self):
        from workspaces import rewrite_layout
        token = 'b' * 32
        text = ('layout {\n pane command="/safe/zellij-agent" name="old task" cwd="/same/path" {\n'
                '  start_suspended true\n  args "' + token + '"\n }\n}\n')
        patched, matched = rewrite_layout(text, {}, '/safe/zellij-agent')
        self.assertEqual(matched, set())
        self.assertIn('args "' + token + '"', patched)
        self.assertIn('start_suspended false', patched)
        self.assertNotIn('start_suspended true', patched)
        self.assertIn('cwd="/same/path"', patched)
        self.assertEqual(rewrite_layout(patched, {}, '/safe/zellij-agent')[0], patched)

    def test_existing_wrapper_token_cannot_be_replaced_by_a_reused_title(self):
        from workspaces import rewrite_layout
        original_token, later_token = 'a' * 32, 'b' * 32
        text = ('layout {\n pane command="/safe/zellij-agent" name="same" {\n'
                '  args "' + original_token + '"\n  start_suspended true\n }\n}\n')
        patched, matched = rewrite_layout(text, {'same': {'token': later_token}}, '/safe/zellij-agent')
        self.assertEqual(matched, {'same'})
        self.assertIn('args "' + original_token + '"', patched)
        self.assertNotIn(later_token, patched)
        self.assertIn('start_suspended false', patched)

    def test_unrelated_wrapper_with_same_filename_keeps_its_suspension(self):
        from workspaces import rewrite_layout
        text = 'layout {\n pane command="/other/zellij-agent" {\n  args "other"\n  start_suspended true\n }\n}\n'
        self.assertEqual(rewrite_layout(text, {}, '/managed/zellij-agent')[0], text)

    def test_duplicate_restore_title_refused(self):
        from workspaces import rewrite_layout
        text = 'layout {\n    pane name="same" {\n    }\n    pane name="same" {\n    }\n}\n'
        with self.assertRaises(ValueError): rewrite_layout(text, {'same': {'token': 'a'*32}}, '/safe')
    def test_cli_picker_has_explicit_centered_geometry(self):
        ws.manager.popup('workspaces')
        args = self.calls[-1]
        for flag, value in [('--x','15%'),('--y','20%'),('--width','70%'),('--height','60%')]:
            self.assertEqual(args[args.index(flag) + 1], value)
        self.assertEqual(args[args.index('--name') + 1], 'Workspaces')
    def test_picker_style_preserves_navigation_order(self):
        import modal
        result = SimpleNamespace(returncode=0, stdout='0\tworkspace\n')
        with patch.object(modal.subprocess, 'run', return_value=result) as runner:
            self.assertEqual(modal.pick(['0\tworkspace'], 'Enter switch'), ('0\tworkspace', ''))
        argv = runner.call_args.args[0]
        self.assertIn('--no-sort', argv)
        self.assertNotIn('--disabled', argv)
        bindings = next(arg for arg in argv if arg.startswith('--bind='))
        self.assertIn('esc:abort', bindings)
        self.assertIn('ctrl-j:down', bindings)
        self.assertNotIn('j:down', bindings.removeprefix('--bind=').split(','))
        self.assertIn('--padding=1,2', argv)
        colors = next(arg for arg in argv if arg.startswith('--color='))
        self.assertIn('bg:-1,', colors)
        self.assertNotIn('bg:#1c1c1c', colors)
        self.assertIn('--header=Enter switch\n↑/↓ or Ctrl+J/K move · type to search · Esc cancel', argv)
    def test_unknown_pi_restore_becomes_default_shell_at_same_cwd(self):
        from workspaces import rewrite_layout
        for executable in ['pi', '/usr/bin/pi', 'pi-coding-agent']:
            text = ('layout {\n cwd "/parent with spaces"\n tab name="2:task" {\n'
                    '  pane size="50%" cwd="/exact pane path" command="' + executable + '" name="[DONE] task · p8" {\n'
                    '   args "--session" "/do-not-guess.jsonl"\n   start_suspended true\n   width 60\n  }\n }\n}\n')
            patched, matched = rewrite_layout(text, {}, '/safe')
            self.assertEqual(matched, set())
            self.assertNotIn('command=', patched)
            self.assertNotIn('args ', patched)
            self.assertNotIn('start_suspended', patched)
            self.assertIn('cwd="/exact pane path"', patched)
            self.assertIn('cwd "/parent with spaces"', patched)
            self.assertIn('pane size="50%" cwd="/exact pane path" name="shell"', patched)
            self.assertIn('width 60', patched)
            self.assertEqual(rewrite_layout(patched, {}, '/safe')[0], patched)

    def test_unknown_node_pi_becomes_shell_and_removes_early_suspension(self):
        from workspaces import rewrite_layout
        for script in ['/usr/bin/pi', '/opt/coding-agent/dist/cli.js']:
            text = ('layout {\n pane command="node" cwd="/same/path" name="old" {\n'
                    '  start_suspended true\n  args "' + script + '" "--session" "not-trusted"\n }\n}\n')
            patched, matched = rewrite_layout(text, {}, '/safe')
            self.assertNotIn('command="node"', patched)
            self.assertNotIn('args ', patched)
            self.assertNotIn('start_suspended', patched)
            self.assertIn('cwd="/same/path" name="shell"', patched)
            self.assertEqual(matched, set())

    def test_non_pi_node_command_is_preserved(self):
        from workspaces import rewrite_layout
        text = 'layout {\n pane command="node" name="server" {\n  start_suspended true\n  args "/tools/server.js"\n }\n}\n'
        self.assertEqual(rewrite_layout(text, {}, '/safe')[0], text)

    def test_mixed_restore_resumes_known_pi_and_uses_shell_for_unknown(self):
        from workspaces import rewrite_layout
        text = ('layout {\n cwd "/inherited/path"\n'
                ' pane command="pi" name="known" {\n  args "old"\n }\n'
                ' pane command="pi" name="unknown" {\n  args "--resume"\n  start_suspended true\n }\n'
                ' pane command="echo" name="other" {\n  args "unchanged"\n  start_suspended true\n }\n}\n')
        patched, matched = rewrite_layout(text, {'known': {'token': 'a' * 32}}, '/safe')
        self.assertEqual(matched, {'known'})
        self.assertIn('command="/safe" name="known"', patched)
        self.assertIn('args "' + 'a' * 32 + '"', patched)
        self.assertIn('pane name="shell"', patched)
        self.assertNotIn('--resume', patched)
        self.assertIn('args "unchanged"', patched)
        self.assertEqual(patched.count('start_suspended true'), 1)
        self.assertEqual(patched.count('start_suspended false'), 1)
        self.assertIn('cwd "/inherited/path"', patched)
    def test_stable_slot_uses_tab_id_not_position(self):
        original = ws.call
        def call(*args):
            if args[:2] == ('action', 'list-tabs'):
                return json.dumps([{'name': '3:task', 'position': 0, 'tab_id': 17}])
            return original(*args)
        with patch.object(ws, 'call', call): ws.manager.slot(3)
        self.assertEqual(self.calls[-1], ('action', 'go-to-tab-by-id', '17'))
    def test_live_transfer_explicitly_refused(self):
        with self.assertRaises(ValueError): ws.workspace_command(SimpleNamespace(cmd='move', target='other'))

if __name__ == '__main__': unittest.main()
