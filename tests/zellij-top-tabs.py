"""Private live proof: adding top tabs preserves terminal IDs and shell PIDs."""
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import pty
import re
import select
import struct
import subprocess
import tempfile
import termios
import time
import uuid

repo = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('workspace_layout', repo / 'dot_config/zellij/bin/workspaces.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
binary = os.environ.get('ZELLIJ_TRIAL_BINARY', str(Path.home() / '.local/state/dotfiles-review/zellij-trial/runtime/usr/bin/zellij'))
session = 'top-tabs-' + uuid.uuid4().hex[:10]
with tempfile.TemporaryDirectory(prefix='zellij-top-tabs-', dir='/tmp') as directory:
    tmp = Path(directory)
    config = tmp / 'config.kdl'
    config.write_text('default_shell "/bin/sh"\nsession_serialization false\nshow_release_notes false\nshow_startup_tips false\nsession_name ' + json.dumps(session) + '\nui {\n pane_frames {\n  hide_session_name true\n }\n}\n')
    layout = tmp / 'before.kdl'
    old_bar = '        pane size=1 borderless=true {\n            plugin location="zellij:tab-bar"\n        }\n'
    layout.write_text('layout {\n    tab name="1:first" {\n' + old_bar + '        pane command="/bin/sh"\n        pane command="/bin/sh"\n    }\n    tab name="2:second" {\n' + old_bar + '        pane command="/bin/sh"\n    }\n}\n')
    env = dict(os.environ, TMPDIR='/tmp', XDG_CACHE_HOME=str(tmp / 'cache'), TERM='xterm-kitty')
    for key in ['TMUX', 'TMUX_PANE', 'ZELLIJ', 'ZELLIJ_PANE_ID', 'ZELLIJ_SESSION_NAME']:
        env.pop(key, None)
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 35, 120, 0, 0))
    def terminal():
        os.setsid()
        fcntl.ioctl(0, termios.TIOCSCTTY, 0)
    proc = subprocess.Popen([binary, '--config-dir', str(tmp), '--config', str(config), '--layout', str(layout)],
                            env=env, stdin=slave, stdout=slave, stderr=slave, preexec_fn=terminal)
    os.close(slave)
    captured = bytearray()
    def call(*args):
        while select.select([master], [], [], 0)[0]:
            try: captured.extend(os.read(master, 65536))
            except OSError: break
        return subprocess.run([binary, '-s', session, *args], env=env, check=True,
                              capture_output=True, text=True, timeout=10).stdout
    def shell_pids():
        result = set()
        for p in Path('/proc').iterdir():
            if not p.name.isdigit(): continue
            try:
                if (p / 'cmdline').read_bytes().split(b'\0')[0] == b'/bin/sh' and ('ZELLIJ_SESSION_NAME=' + session).encode() in (p / 'environ').read_bytes().split(b'\0'):
                    result.add(int(p.name))
            except OSError: pass
        return result
    try:
        # A socket alone is not startup readiness: action clients can race
        # FirstClientConnected on 0.45.1. Wait for this fixture's native bar.
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            while select.select([master], [], [], .02)[0]:
                try: captured.extend(os.read(master, 65536))
                except OSError: break
            if b' Zellij ' in captured: break
            if proc.poll() is not None: raise AssertionError('Private client exited before rendering')
            time.sleep(.05)
        else: raise AssertionError('Private bar did not render during startup')
        for attempt in range(80):
            try:
                before = json.loads(call('action', 'list-panes', '--json', '--all'))
                if len([p for p in before if not p['is_plugin']]) == 3: break
            except (subprocess.SubprocessError, json.JSONDecodeError): pass
            time.sleep(0.05)
        else:
            raise AssertionError('Startup failed: ' + captured.decode(errors='replace')[-1500:])
        old_ids = {p['id'] for p in before if not p['is_plugin']}
        old_bar_ids = {p['id'] for p in before if p.get('plugin_url') == 'zellij:tab-bar'}
        assert len(old_bar_ids) == 2
        old_pids = shell_pids()
        # Grant after the native server starts: this also verifies live permission
        # cache lookup, without granting commands or touching the user's cache.
        plugin = Path.home() / '.local/share/zellij/plugins/workspace-bar-0.45.1.wasm'
        subprocess.run(['python3', str(repo / 'setup/zellij-workspace-bar/grant-ui-permissions.py'),
                        str(plugin), '--cache', str(tmp / 'cache/zellij/permissions.kdl'),
                        '--backups', str(tmp / 'permission-backups')], check=True, env=env)
        bar_urls = {module.WORKSPACE_BAR_URL, 'file:' + str(plugin)}
        assert len(old_pids) == 3, old_pids
        text = call('action', 'dump-layout')
        patched = module.with_top_tabs(text)
        assert module.with_top_tabs(patched) == patched
        # Explicit command/cwd runs would spawn replacement terminals even
        # with retention enabled. Anonymous leaves reuse the existing panes.
        live_layout = re.sub(r'\b(?:command|cwd)=' + module.STRING + r'[ \t]*', '', patched)
        live_layout = '\n'.join(line for line in live_layout.splitlines()
                                if not re.match(r'\s*(?:args|cwd|start_suspended)\b', line)) + '\n'
        call('action', 'override-layout', '--layout-string', live_layout,
             '--retain-existing-terminal-panes', '--retain-existing-plugin-panes')
        for attempt in range(80):
            after = json.loads(call('action', 'list-panes', '--json', '--all'))
            bars = [p for p in after if p.get('plugin_url') in bar_urls]
            if len(bars) == 2: break
            time.sleep(0.05)
        assert len(bars) == 2, bars
        assert all(p['pane_y'] == 0 and p['pane_rows'] == 1 for p in bars), bars
        assert old_ids <= {p['id'] for p in after if not p['is_plugin']}
        assert old_pids <= shell_pids()
        # Remove only retained original native bar plugins, never terminals or
        # unrelated plugins. The new workspace bars are already verified above.
        for pane in after:
            if pane['is_plugin'] and pane['id'] in old_bar_ids:
                call('action', 'close-pane', '--pane-id', 'plugin_' + str(pane['id']))
        # Explicit-run originals can be retained as extra panes. Remove only
        # empty replacement shells allocated by this operation, never originals.
        for pane in after:
            if not pane['is_plugin'] and pane['id'] not in old_ids:
                assert pane.get('pane_command') == '/bin/sh'
                call('action', 'close-pane', '--pane-id', 'terminal_' + str(pane['id']))
        after = json.loads(call('action', 'list-panes', '--json', '--all'))
        assert {p['id'] for p in after if not p['is_plugin']} == old_ids
        assert shell_pids() == old_pids, (old_pids, shell_pids())
        assert not any(p.get('plugin_url') == 'zellij:compact-bar' for p in after)
        tabs = json.loads(call('action', 'list-tabs', '--json', '--all'))
        assert [t['name'] for t in tabs] == ['1:first', '2:second']
        assert not any(p.get('plugin_url') == 'zellij:tab-bar' for p in after)
        captured.clear()
        call('action', 'go-to-tab', '2')
        call('action', 'go-to-tab', '1')
        def visible_text():
            data = re.sub(rb'\x1b\].*?(?:\x07|\x1b\\)', b'', bytes(captured), flags=re.S)
            data = re.sub(rb'\x1bP.*?\x1b\\', b'', data, flags=re.S)
            return re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]', b'', data).decode(errors='replace')
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            call('action', 'list-tabs', '--json', '--all')
            if ' ' + session + ' ' in visible_text() and '2:second' in visible_text(): break
            time.sleep(.1)
        plain = visible_text()
        assert ' ' + session + ' ' in plain, 'Workspace label did not render'
        assert ' Zellij ' not in plain, 'Native branding remained in the bar'
        row = plain[plain.rfind(' ' + session + ' '):]
        column = row.index('2:second') + 3
        os.write(master, ('\x1b[<0;' + str(column + 1) + ';1M\x1b[<0;' + str(column + 1) + ';1m').encode())
        for attempt in range(40):
            tabs = json.loads(call('action', 'list-tabs', '--json', '--all'))
            if any(t['name'] == '2:second' and t['active'] for t in tabs): break
            time.sleep(.05)
        assert any(t['name'] == '2:second' and t['active'] for t in tabs), 'Native tab mouse selection regressed'
        assert shell_pids() == old_pids
        print('Workspace prefix replaces Zellij even with hidden frame names; native tab clicks work')
        new_layout = 'layout {\n' + module.tab_bar('    ') + '    pane\n}\n'
        call('action', 'new-tab', '--name=3:new', '--layout-string', new_layout)
        for attempt in range(80):
            after = json.loads(call('action', 'list-panes', '--json', '--all'))
            bars = [p for p in after if p.get('plugin_url') in bar_urls]
            if len(bars) == 3: break
            time.sleep(0.05)
        assert len(bars) == 3, 'Explicit new-tab template lost the tab bar'
        print('Top tabs: one row per tab; terminal IDs/PIDs/order preserved; explicit new tabs include bar')
    finally:
        if proc.poll() is None:
            proc.terminate()
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired: proc.kill(); proc.wait()
        os.close(master)
        subprocess.run([binary, 'kill-session', session], env=env, capture_output=True, timeout=10)
