"""Check real key-bound popup geometry in private PTYs, without restarting user sessions."""
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import shutil
import struct
import subprocess
import tempfile
import termios
import time
import uuid

repo = Path(__file__).resolve().parents[1]
binary = os.environ.get('ZELLIJ_TRIAL_BINARY', str(Path.home() / '.local/state/dotfiles-review/zellij-trial/runtime/usr/bin/zellij'))
source = (repo / 'dot_config/zellij/config.kdl').read_text()
source = source.replace('load_plugins {\n    autolock\n}', '')
source = source.replace('default_shell "/usr/bin/zsh"', 'default_shell "/bin/sh"')
passed = []

for columns, rows in [(120, 40), (85, 25), (160, 50)]:
    session = 'modal-check-' + uuid.uuid4().hex[:10]
    with tempfile.TemporaryDirectory(prefix='zellij-modal-', dir='/tmp') as directory:
        tmp = Path(directory)
        (tmp / 'layouts').mkdir()
        (tmp / 'layouts/default.kdl').write_text((repo / 'dot_config/zellij/layouts/default.kdl').read_text())
        config = tmp / 'config.kdl'
        config.write_text(source + '\nsession_name ' + json.dumps(session) + '\n')
        # Keep picker inventory independent of the user's SSH/authentication
        # state. Native helpers derive CONFIG from HOME, not --config-dir.
        home = tmp / 'home'
        own_config = home / '.config/zellij'
        shutil.copytree(Path.home() / '.config/zellij/bin', own_config / 'bin')
        shutil.copytree(tmp / 'layouts', own_config / 'layouts')
        (own_config / 'config.kdl').write_text(source)
        shutil.copy2(repo / 'dot_config/zellij/directory-picker.lfrc', own_config / 'directory-picker.lfrc')
        (home / 'dev').mkdir(parents=True)
        plugin = home / '.local/share/zellij/plugins/workspace-bar-0.45.1.wasm'
        plugin.parent.mkdir(parents=True)
        shutil.copy2(Path.home() / '.local/share/zellij/plugins/workspace-bar-0.45.1.wasm', plugin)
        env = dict(os.environ, HOME=str(home), XDG_CACHE_HOME=str(tmp / 'cache'), ZELLIJ_WS_STATE=str(tmp / 'state'),
                   ZELLIJ_TRIAL_BINARY=binary, TERM='xterm-kitty', PI_ZELLIJ_NOTIFY='0', PATH=str(Path.home() / '.local/bin') + ':' + os.environ['PATH'])
        for key in ['TMUX', 'TMUX_PANE', 'ZELLIJ', 'ZELLIJ_PANE_ID', 'ZELLIJ_SESSION_NAME']:
            env.pop(key, None)
        subprocess.run(['python3', str(repo / 'setup/zellij-workspace-bar/grant-ui-permissions.py'),
                        str(plugin), '--cache', str(tmp / 'cache/zellij/permissions.kdl'),
                        '--backups', str(tmp / 'permission-backups')], check=True, env=env)
        bar_urls = {'file:' + str(plugin), 'file:~/.local/share/zellij/plugins/workspace-bar-0.45.1.wasm'}
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', rows, columns, 0, 0))
        def terminal():
            os.setsid()
            fcntl.ioctl(0, termios.TIOCSCTTY, 0)
        proc = subprocess.Popen([binary, '--config-dir', str(tmp), '--config', str(config), '--data-dir', str(tmp / 'data')],
                                env=env, stdin=slave, stdout=slave, stderr=slave, preexec_fn=terminal)
        os.close(slave)
        terminal_output = bytearray()
        def drain():
            while select.select([master], [], [], 0)[0]:
                try:
                    terminal_output.extend(os.read(master, 65536))
                    # Keep the initial tab-bar render through a full-screen repaint;
                    # an 8 KiB tail can discard our startup-readiness marker.
                    del terminal_output[:-65536]
                except OSError: break
        def panes():
            drain()
            r = subprocess.run([binary, '-s', session, 'action', 'list-panes', '--json', '--all'],
                               env=env, capture_output=True, text=True, timeout=5)
            try: return json.loads(r.stdout)
            except json.JSONDecodeError: return []
        def wait_for(predicate):
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                value = predicate(panes())
                if value: return value
                time.sleep(0.05)
            raise AssertionError(f'Popup/startup timeout; client status={proc.poll()}; private PTY tail={bytes(terminal_output[-2000:])!r}')
        try:
            # Do not send an action client before FirstClientConnected has initialized
            # the server; Zellij 0.45.1 can panic on that startup race.
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                drain()
                if (' ' + session + ' ').encode() in terminal_output:
                    break
                if proc.poll() is not None:
                    raise AssertionError('Private Zellij client exited during startup')
                time.sleep(0.05)
            else:
                raise AssertionError(f'Private tab bar did not render during startup; client={proc.poll()}; PTY tail={bytes(terminal_output[-2000:])!r}')
            initial = wait_for(lambda ps: [p for p in ps if not p['is_plugin'] and not p['is_floating']])
            initial_ids = {p['id'] for p in initial}
            # Fixed tab bars reserve a row from floating-pane percentage geometry.
            available_rows = rows - sum(p['pane_rows'] for p in panes()
                                        if p.get('plugin_url') in bar_urls)
            for key, title, width, height in [('s', 'Workspaces', 70, 60), ('g', 'Attention', 70, 60),
                                             ('o', 'Projects', 70, 60), ('C', 'New task', 70, 60),
                                             ('n', 'Task name', 60, 30)]:
                os.write(master, b'\x00' + key.encode())
                popup = wait_for(lambda ps: next((p for p in ps if p['is_floating'] and p['title'] == title), None))
                x, y, w, h = [popup[name] for name in ['pane_x', 'pane_y', 'pane_columns', 'pane_rows']]
                assert abs(2*x + w - columns) <= 2, (title, 'horizontal center', x, w, columns)
                assert abs(2*y + h - available_rows) <= 2, (title, 'vertical center', y, h, available_rows)
                assert abs(w - columns*width/100) <= 1, (title, 'width', w)
                assert abs(h - available_rows*height/100) <= 1, (title, 'height', h)
                passed.append(f'{columns}x{rows} {title}: centered {w}x{h}')
                # Verify the picker actually runs, rather than briefly flashing
                # before its child command crashes. Then cancel through its UI.
                if key in ('s', 'g', 'o', 'C'):
                    expected = ('No agents need attention.' if key == 'g' else
                                'Local:' if key in ('o', 'C') else 'type to search')
                    wait_for(lambda ps: expected in subprocess.run(
                        [binary, '-s', session, 'action', 'dump-screen', '--pane-id', 'terminal_' + str(popup['id'])],
                        env=env, capture_output=True, text=True, timeout=5).stdout)
                else:
                    time.sleep(0.3)
                if key == 'g':
                    time.sleep(1)
                live_popup = next(p for p in panes() if p['id'] == popup['id'] and not p['is_plugin'])
                assert not live_popup['exited'], 'Modal command exited before user input'
                if key == 'n':
                    subprocess.run([binary, '-s', session, 'action', 'write-chars', '--pane-id',
                                    'terminal_' + str(popup['id']), 'API tests\n'],
                                   env=env, check=True, capture_output=True, text=True, timeout=5)
                else:
                    subprocess.run([binary, '-s', session, 'action', 'write', '--pane-id',
                                    'terminal_' + str(popup['id']), '27'],
                                   env=env, check=True, capture_output=True, text=True, timeout=5)
                wait_for(lambda ps: not any(p['id'] == popup['id'] and not p['is_plugin'] for p in ps))
                assert initial_ids <= {p['id'] for p in panes() if not p['is_plugin']}
                if key == 'n':
                    # CLI actions are queued; modal exit is not an acknowledgement
                    # that both tab and pane renames have reached the screen thread.
                    original = wait_for(lambda ps: next((p for p in ps if p['id'] in initial_ids
                                        and not p['is_plugin'] and p['tab_name'] == '1:API tests'
                                        and p['title'] == 'API tests'), None))
                    passed.append(f'{columns}x{rows}: task name updates top tab and pane, retaining slot 1')
                    os.write(master, b'\x00n')
                    reset = wait_for(lambda ps: next((p for p in ps if p['is_floating'] and p['title'] == 'Task name'), None))
                    wait_for(lambda ps: 'empty resets to shell' in subprocess.run(
                        [binary, '-s', session, 'action', 'dump-screen', '--pane-id', 'terminal_' + str(reset['id'])],
                        env=env, capture_output=True, text=True, timeout=5).stdout)
                    subprocess.run([binary, '-s', session, 'action', 'write', '--pane-id',
                                    'terminal_' + str(reset['id']), '13'],
                                   env=env, check=True, capture_output=True, text=True, timeout=5)
                    wait_for(lambda ps: not any(p['id'] == reset['id'] and not p['is_plugin'] for p in ps))
                    original = wait_for(lambda ps: next((p for p in ps if p['id'] in initial_ids
                                        and not p['is_plugin'] and p['tab_name'] == '1:shell'
                                        and p['title'] == 'shell'), None))
                    passed.append(f'{columns}x{rows}: empty task-name submission resets to shell')
            if columns == 160:
                # A simulated Pi owner in this disposable shell: no model or transcript.
                original_id = min(initial_ids)
                helper_env = dict(env, ZELLIJ='0', ZELLIJ_SESSION_NAME=session,
                                  ZELLIJ_PANE_ID=str(original_id), ZELLIJ_WS_NO_SAVE='1')
                helper = str(Path.home() / '.config/zellij/bin/zellij-ws')
                for state in ['start', 'done']:
                    subprocess.run([helper, 'event', state, '--pane', str(original_id), '--owner', 'viewer-fixture',
                                    '--pid', str(os.getpid()), '--label', 'Fixture agent',
                                    '--last-prompt', 'FIXTURE_PROMPT_VIEWER'], env=helper_env,
                                   check=True, capture_output=True, text=True, timeout=10)
                for key, title in [('g', 'Attention'), ('G', 'Agents')]:
                    os.write(master, b'\x00' + key.encode())
                    popup = wait_for(lambda ps: next((p for p in ps if p['is_floating'] and p['title'] == title), None))
                    def screen():
                        return subprocess.run([binary, '-s', session, 'action', 'dump-screen', '--pane-id',
                                               'terminal_' + str(popup['id'])], env=env, capture_output=True,
                                              text=True, timeout=5).stdout
                    wait_for(lambda ps: 'FIXTURE_PROMPT_VIEWER' in screen() and 'Current Pi screen' in screen())
                    contents = screen()
                    assert 'DONE' in contents and 'UPDATED' in contents and 'Fixture agent' in contents, contents
                    assert all(heading in contents for heading in ['STATUS', 'SESSION', 'WORKSPACE', 'LAST PROMPT'])
                    if key == 'G':
                        assert '\U000f04b2 DONE' in contents, contents
                        subprocess.run([binary, '-s', session, 'action', 'write', '--pane-id',
                                        'terminal_' + str(popup['id']), '27', '115'], env=env, check=True,
                                       capture_output=True, text=True, timeout=5)
                        wait_for(lambda ps: '\U000f05e0 DONE' in screen())
                        passed.append('Alt+S in G restores the snoozed agent without focusing it')
                    # Viewport ANSI must contain the DONE green even on the selected row.
                    styled = subprocess.run([binary, '-s', session, 'action', 'dump-screen', '--ansi', '--pane-id',
                                             'terminal_' + str(popup['id'])], env=env, capture_output=True,
                                            text=True, timeout=5).stdout
                    assert '38;5;150' in styled or '38;2;175;215;135' in styled, repr(styled)
                    if key == 'g':
                        subprocess.run([binary, '-s', session, 'action', 'write', '--pane-id',
                                        'terminal_' + str(popup['id']), '27', '115'], env=env, check=True,
                                       capture_output=True, text=True, timeout=5)
                        wait_for(lambda ps: 'No agents need attention.' in screen())
                        passed.append('Alt+S in g hides attention and keeps the empty picker open')
                    subprocess.run([binary, '-s', session, 'action', 'write', '--pane-id',
                                    'terminal_' + str(popup['id']), '27'], env=env, check=True,
                                   capture_output=True, text=True, timeout=5)
                    wait_for(lambda ps: not any(p['id'] == popup['id'] and not p['is_plugin'] for p in ps))
                    assert initial_ids <= {p['id'] for p in panes() if not p['is_plugin']}
                    passed.append(f'{columns}x{rows}: populated {title} shows status/prompt/time/live preview')
        finally:
            if proc.poll() is None:
                proc.terminate()
                try: proc.wait(timeout=5)
                except subprocess.TimeoutExpired: proc.kill(); proc.wait()
            os.close(master)
            subprocess.run([binary, 'kill-session', session], env=env, capture_output=True, timeout=10)
print('\n'.join(passed))
print('15 real popup geometry/empty-state/lf checks plus populated g/G previews passed; original terminal panes preserved')
