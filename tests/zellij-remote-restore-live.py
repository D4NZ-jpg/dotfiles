#!/usr/bin/env python3
"""Cold native carrier resurrection with a fake transport; no SSH/Pi/Mosh launch."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pty
import select
import struct
import subprocess
import sys
import tempfile
import termios
import time
import uuid
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'dot_config/zellij/bin'))
from workspaces import WorkspaceManager, quoted

binary = os.environ.get('ZELLIJ_TRIAL_BINARY', str(Path.home() / '.local/state/dotfiles-review/zellij-trial/runtime/usr/bin/zellij'))
with tempfile.TemporaryDirectory(prefix='remote-restore-check-', dir='/tmp') as directory:
    root = Path(directory)
    config = root / 'config'
    (config / 'bin').mkdir(parents=True)
    (config / 'remotes.json').write_text('{"dev":"tester@invalid.example"}')
    settings = 'default_shell "/bin/sh"\nsession_serialization true\nshow_release_notes false\nshow_startup_tips false\n'
    (config / 'config.kdl').write_text(settings)
    (config / 'bridge.kdl').write_text(settings)
    marker = root / 'transport-argv.json'
    helper = config / 'bin/zellij-ws'
    helper.write_text('#!/usr/bin/python3\nimport json,os,sys\nfrom pathlib import Path\n'
                      'Path(' + repr(str(marker)) + ').write_text(json.dumps({"argv":sys.argv[1:],"pid":os.getpid()}))\n'
                      'os.execv("/bin/sh", ["/bin/sh"])\n')
    helper.chmod(0o700)
    target = 'exact workspace ' + uuid.uuid4().hex[:10]
    state = {'workspaces': {}}
    env = dict(os.environ, TMPDIR='/tmp', TERM='xterm-256color', XDG_CACHE_HOME=str(root / 'cache'))
    for key in ['TMUX', 'TMUX_PANE', 'ZELLIJ', 'ZELLIJ_PANE_ID', 'ZELLIJ_SESSION_NAME']:
        env.pop(key, None)
    c = {'CONFIG': config, 'HOME_STATE': root / 'state', 'SESSION': '', 'BINARY': binary,
         'OPTIONS': ['--config-dir', str(config), '--config', str(config / 'config.kdl'), '--data-dir', str(root / 'data')],
         'transact': lambda fn, path=None: fn(state), 'clean': lambda value, limit=90: str(value)[:limit]}
    manager = WorkspaceManager(c)
    name = manager.remotes.bridge_name('dev', target)
    manager.register(name)
    state['workspaces'][name].update(remote_bridge=True, remote_host='dev', remote_session=target,
                                     remote_config=str(config / 'bridge.kdl'))
    def call(*args):
        r = subprocess.run([binary, '-s', c['SESSION'] or name, *args], env=env,
                           capture_output=True, text=True, timeout=10)
        r.check_returncode()
        return r.stdout
    c['call'] = call
    original = root / 'old.kdl'
    original.write_text('layout {\n tab {\n  pane size=1 borderless=true {\n   plugin location="zellij:tab-bar"\n  }\n'
                        '  pane command="mosh-client" {\n   args "--predict=never" "--ssh=expired"\n   start_suspended true\n  }\n }\n}\n')
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 35, 120, 0, 0))
    def terminal():
        os.setsid()
        fcntl.ioctl(0, termios.TIOCSCTTY, 0)
    client = subprocess.Popen([binary, *c['OPTIONS'], '--layout', str(original), 'attach', '--create', name],
                              env=env, stdin=slave, stdout=slave, stderr=slave, preexec_fn=terminal)
    os.close(slave)
    def drain():
        while select.select([master], [], [], 0)[0]:
            try: os.read(master, 65536)
            except OSError: break
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            drain()
            try: panes = json.loads(call('action', 'list-panes', '--json', '--all'))
            except (subprocess.SubprocessError, json.JSONDecodeError): time.sleep(.1); continue
            if any(not p['is_plugin'] and p['is_held'] for p in panes): break
            time.sleep(.1)
        else: raise AssertionError('Original suspended carrier did not initialize')
        # Save a real native serialization, then kill only this disposable carrier.
        text = call('action', 'dump-layout')
        with patch.dict(os.environ, env, clear=True), patch.object(manager, 'discover', return_value=({}, {name: 'live'})):
            manager.ensure(name)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and not marker.exists(): time.sleep(.05)
        assert marker.exists(), 'Held carrier did not restart its managed transport automatically'
        started = json.loads(marker.read_text())
        assert started['argv'] == ['remote-attach', 'dev', target]
        with patch.dict(os.environ, env, clear=True), patch.object(manager, 'discover', return_value=({}, {name: 'live'})):
            manager.ensure(name)
        assert json.loads(marker.read_text()) == started
        os.kill(started['pid'], 0)
        live = json.loads(call('action', 'list-panes', '--json', '--all'))
        assert len([p for p in live if not p['is_plugin']]) == 1
        assert not any(p.get('plugin_url') == 'zellij:tab-bar' for p in live)
        print('PASS native held repair: automatic exact transport; a healthy second attach preserves its PID')
        marker.unlink()
        # A failed managed helper has the same startup command as the desired
        # layout. Override reuses it: automatic repair must also trigger retry.
        terminal = next(p for p in live if not p['is_plugin'])
        call('action', 'write-chars', '--pane-id', 'terminal_' + str(terminal['id']), 'exit 73\n')
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            stopped = json.loads(call('action', 'list-panes', '--json', '--all'))
            if any(not p['is_plugin'] and p['is_held'] for p in stopped): break
            drain(); time.sleep(.05)
        with patch.dict(os.environ, env, clear=True), patch.object(manager, 'discover', return_value=({}, {name: 'live'})):
            manager.ensure(name)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and not marker.exists(): drain(); time.sleep(.05)
        assert marker.exists(), 'Reused held helper was not retried'
        assert json.loads(marker.read_text())['argv'] == ['remote-attach', 'dev', target]
        assert json.loads(marker.read_text())['pid'] != started['pid']
        print('PASS native retry: failed matching helper is rerun automatically, not left held')
        marker.unlink()
        call('kill-session', name)
        deadline = time.monotonic() + 10
        while client.poll() is None and time.monotonic() < deadline:
            drain()
            time.sleep(.05)
        client.wait(timeout=1)
        cache = root / 'cache/zellij/contract_version_1/session_info' / name / 'session-layout.kdl'
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(text)
        with patch.dict(os.environ, env, clear=True), patch.object(manager, 'discover', return_value=({}, {name: 'saved'})):
            manager.ensure(name)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and not marker.exists(): time.sleep(.05)
        assert marker.exists(), 'Native resurrection did not automatically execute the managed transport'
        assert json.loads(marker.read_text())['argv'] == ['remote-attach', 'dev', target]
        panes = json.loads(call('action', 'list-panes', '--json', '--all'))
        terminals = [p for p in panes if not p['is_plugin']]
        assert len(terminals) == 1
        assert terminals[0]['pane_y'] == 0 and terminals[0]['pane_content_y'] == 0
        assert not terminals[0]['is_held'] and not terminals[0]['exited']
        assert all(p['is_floating'] or p['is_suppressed'] for p in panes if p['is_plugin'])
        private = manager.path('layouts/' + hashlib.sha256(name.encode()).hexdigest() + '.kdl')
        assert private.read_text() == manager.remotes.bridge_layout('dev', target)
        assert 'mosh-client' not in cache.read_text()
        print('PASS native cold restore: exact host/workspace runs automatically without Enter')
        print('PASS native cold restore: one borderless transport pane, no outer bar or stale Mosh argv')
    finally:
        if client.poll() is None:
            client.terminate()
            try: client.wait(timeout=5)
            except subprocess.TimeoutExpired: client.kill(); client.wait()
        os.close(master)
        subprocess.run([binary, 'kill-session', name], env=env, capture_output=True, timeout=10)
        print('Disposed only this fake-transport session; no SSH, Mosh or Pi was launched')
