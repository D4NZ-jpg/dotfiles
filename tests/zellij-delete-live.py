"""Confirm picker removal against disposable native sessions; never user workspaces."""
import fcntl
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
binary = os.environ.get('ZELLIJ_TRIAL_BINARY', str(Path.home() / '.local/state/dotfiles-review/zellij-trial/runtime/usr/bin/zellij'))
root_session = 'delete-check-' + uuid.uuid4().hex[:10]
target = 'delete-target-' + uuid.uuid4().hex[:10]
helper = str(Path.home() / '.config/zellij/bin/zellij-ws')

with tempfile.TemporaryDirectory(prefix='zellij-delete-check-', dir='/tmp') as directory:
    tmp = Path(directory)
    (tmp / 'layouts').mkdir()
    (tmp / 'layouts/default.kdl').write_text((repo / 'dot_config/zellij/layouts/default.kdl').read_text())
    text = (repo / 'dot_config/zellij/config.kdl').read_text()
    text = text.replace('load_plugins {\n    autolock\n}', '').replace('default_shell "/usr/bin/zsh"', 'default_shell "/bin/sh"')
    config = tmp / 'config.kdl'
    config.write_text(text + '\nsession_name ' + json.dumps(root_session) + '\n')
    env = dict(os.environ, TMPDIR='/tmp', XDG_CACHE_HOME=str(tmp / 'cache'),
               ZELLIJ_WS_STATE=str(tmp / 'state'), TERM='xterm-kitty',
               PI_ZELLIJ_NOTIFY='0', PYTHONDONTWRITEBYTECODE='1')
    for key in ['TMUX', 'TMUX_PANE', 'ZELLIJ', 'ZELLIJ_SESSION_NAME', 'ZELLIJ_PANE_ID']:
        env.pop(key, None)
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 120, 0, 0))
    def terminal():
        os.setsid()
        fcntl.ioctl(0, termios.TIOCSCTTY, 0)
    options = ['--config-dir', str(tmp), '--config', str(config), '--data-dir', str(tmp / 'data')]
    proc = subprocess.Popen([binary, *options], env=env, stdin=slave, stdout=slave,
                            stderr=slave, preexec_fn=terminal)
    os.close(slave)
    output = bytearray()
    def drain():
        while select.select([master], [], [], 0)[0]:
            try: output.extend(os.read(master, 65536))
            except OSError: break
    def cli(*args):
        drain()
        return subprocess.run([binary, *args], env=env, capture_output=True, text=True, timeout=8)
    def panes():
        result = cli('-s', root_session, 'action', 'list-panes', '--json', '--all')
        return json.loads(result.stdout) if result.returncode == 0 else []
    def wait(predicate):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            drain()
            if predicate(): return
            time.sleep(.05)
        raise AssertionError('Private removal fixture timed out')
    def exists(name):
        result = cli('list-sessions', '--no-formatting')
        return any(line.startswith(name + ' [Created ') for line in result.stdout.splitlines())
    popup_id = None
    def screen():
        return cli('-s', root_session, 'action', 'dump-screen', '--pane-id', 'terminal_' + str(popup_id)).stdout
    def write(*bytes_):
        result = cli('-s', root_session, 'action', 'write', '--pane-id', 'terminal_' + str(popup_id), *map(str, bytes_))
        assert result.returncode == 0, result.stderr
    def open_picker(query):
        global popup_id
        os.write(master, b'\x00s')
        wait(lambda: any(p.get('is_floating') and p.get('title') == 'Workspaces' for p in panes()))
        popup_id = next(p['id'] for p in panes() if p.get('is_floating') and p.get('title') == 'Workspaces')
        wait(lambda: 'Alt+D remove' in screen())
        result = cli('-s', root_session, 'action', 'write-chars', '--pane-id', 'terminal_' + str(popup_id), query)
        assert result.returncode == 0
        wait(lambda: query in screen() and bool(re.search(r'\b1/\d+\b', screen())))
    def close_picker():
        write(27)
        wait(lambda: not any(p['id'] == popup_id and not p.get('is_plugin') for p in panes()))
    try:
        wait(lambda: b'Zellij' in output)
        wait(lambda: any(not p.get('is_plugin') and not p.get('is_floating') for p in panes()))
        original_ids = {p['id'] for p in panes() if not p.get('is_plugin')}
        created = subprocess.run([binary, *options, 'attach', '--create-background', target],
                                 env=env, capture_output=True, text=True, timeout=15)
        assert created.returncode == 0, created.stderr
        wait(lambda: exists(target))
        # Selecting the caller must never get as far as a destructive choice.
        open_picker(root_session)
        write(27, 100)  # Alt+D
        wait(lambda: 'Switch to another workspace' in screen())
        assert exists(root_session) and exists(target)
        write(27)
        wait(lambda: 'Alt+D remove' in screen())
        close_picker()
        # Default Enter cancels; selecting Remove is a separate intentional action.
        open_picker(target)
        write(27, 100)
        wait(lambda: 'Remove workspace "' + target + '"?' in screen())
        assert re.search(r'›\s+Cancel', screen()), screen()
        write(13)
        wait(lambda: 'Alt+D remove' in screen())
        assert exists(target)
        close_picker()
        open_picker(target)
        write(27, 100)
        wait(lambda: 'Remove workspace "' + target + '"?' in screen())
        write(10, 13)  # Ctrl+J then Enter: select Remove, confirm.
        wait(lambda: not exists(target))
        wait(lambda: 'Alt+D remove' in screen())
        registry = json.loads((tmp / 'state/registry.json').read_text())
        assert target not in registry['workspaces']
        assert not (tmp / 'cache/zellij/contract_version_1/session_info' / target).exists()
        assert proc.poll() is None
        assert original_ids <= {p['id'] for p in panes() if not p.get('is_plugin')}
        close_picker()
        print('Live picker removal passed: current-workspace guard, default cancellation, confirmed native deletion, registry/cache cleanup, caller panes retained')
    finally:
        if proc.poll() is None:
            proc.terminate()
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired: proc.kill(); proc.wait()
        os.close(master)
        # Exact disposable names only, including failed-test cleanup.
        for name in [target, root_session]:
            subprocess.run([binary, 'kill-session', name], env=env, capture_output=True, timeout=10)
