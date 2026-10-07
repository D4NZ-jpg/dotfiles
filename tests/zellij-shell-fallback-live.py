#!/usr/bin/env python3
"""Native shell recovery at the saved cwd; never launches Pi or a model."""
import fcntl
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

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'dot_config/zellij/bin'))
from workspaces import rewrite_layout, quoted

binary = os.environ.get('ZELLIJ_TRIAL_BINARY', str(Path.home() / '.local/state/dotfiles-review/zellij-trial/runtime/usr/bin/zellij'))
name = 'shell-restore-check-' + uuid.uuid4().hex[:10]
with tempfile.TemporaryDirectory(prefix='shell-restore-check-', dir='/tmp') as directory:
    root = Path(directory)
    cwd = root / 'same directory with spaces'
    cwd.mkdir()
    config = root / 'config.kdl'
    config.write_text('default_shell "/bin/sh"\nsession_serialization false\nshow_release_notes false\n')
    original = ('layout {\n cwd ' + quoted(root) + '\n'
                ' tab name="1:known" {\n  pane command="pi" name="known" {\n   start_suspended true\n  }\n }\n'
                ' tab name="2:unknown" focus=true {\n  pane command="pi" name="[DONE] unknown" cwd=' + quoted(cwd) + ' {\n'
                '   args "--resume"\n   start_suspended true\n  }\n }\n'
                ' tab name="3:node" {\n  pane command="node" name="unmapped node" cwd=' + quoted(cwd) + ' {\n'
                '   start_suspended true\n   args "/opt/coding-agent/dist/cli.js" "--resume"\n  }\n }\n}\n')
    # A harmless stand-in proves automatic execution and exact token delivery.
    # It leaves a shell running; this test can never invoke Pi or a model.
    marker = root / 'resumed-token.json'
    probe = root / 'resume-probe'
    probe.write_text('#!/usr/bin/python3\nimport json,os,sys\nfrom pathlib import Path\n'
                     'Path(' + repr(str(marker)) + ').write_text(json.dumps(sys.argv[1:]))\n'
                     'os.execv("/bin/sh", ["/bin/sh"])\n')
    probe.chmod(0o700)
    patched, matched = rewrite_layout(original, {'known': {'token': 'a' * 32}}, str(probe))
    assert matched == {'known'}
    layout = root / 'layout.kdl'
    layout.write_text(patched)
    env = dict(os.environ, TMPDIR='/tmp', TERM='xterm-256color', XDG_CACHE_HOME=str(root / 'cache'))
    for key in ['ZELLIJ', 'ZELLIJ_SESSION_NAME', 'ZELLIJ_PANE_ID', 'TMUX', 'TMUX_PANE']:
        env.pop(key, None)
    subprocess.run(['python3', str(Path(__file__).resolve().parents[1] / 'setup/zellij-workspace-bar/grant-ui-permissions.py'),
                    str(Path.home() / '.local/share/zellij/plugins/workspace-bar-0.45.1.wasm'),
                    '--cache', str(root / 'cache/zellij/permissions.kdl'),
                    '--backups', str(root / 'permission-backups')], check=True, env=env)
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 35, 120, 0, 0))
    def terminal():
        os.setsid()
        fcntl.ioctl(0, termios.TIOCSCTTY, 0)
    client = subprocess.Popen([binary, '--config-dir', str(root), '--config', str(config),
        '--data-dir', str(root / 'data'), '--layout', str(layout), 'attach', '--create', name],
        env=env, stdin=slave, stdout=slave, stderr=slave, preexec_fn=terminal)
    os.close(slave)
    try:
        deadline = time.monotonic() + 20
        ready = False
        while time.monotonic() < deadline:
            while select.select([master], [], [], .02)[0]:
                try: os.read(master, 65536)
                except OSError: break
            result = subprocess.run([binary, '-s', name, 'action', 'list-panes', '--json', '--all'],
                env=env, capture_output=True, text=True, timeout=5)
            try: panes = [pane for pane in json.loads(result.stdout) if not pane['is_plugin']]
            except (json.JSONDecodeError, KeyError):
                time.sleep(.1)
                continue
            held = [pane for pane in panes if pane.get('is_held')]
            shells = [pane for pane in panes if not pane.get('is_held') and pane.get('pane_cwd') == str(cwd)]
            if not held and len(shells) == 2 and marker.exists():
                ready = True
                break
            time.sleep(.1)
        assert ready, 'Expected automatic exact-thread helper and two live shells at the saved cwd'
        assert json.loads(marker.read_text()) == ['a' * 32]
        assert any(pane['title'] == 'known' and not pane.get('is_held') for pane in panes)
        assert all('pi' not in str(pane.get('terminal_command', '')) for pane in shells)
        print('PASS native recovery: unidentified Pi and Node-Pi become live shells at the same cwd')
        print('PASS native recovery: exact-token helper runs automatically; no Pi was launched')
    finally:
        if client.poll() is None:
            client.terminate()
            try: client.wait(timeout=3)
            except subprocess.TimeoutExpired: client.kill(); client.wait()
        os.close(master)
        subprocess.run([binary, 'kill-session', name], env=env, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=10)
        remaining = subprocess.run([binary, 'list-sessions', '--no-formatting'],
            env=env, capture_output=True, text=True, timeout=10)
        assert not any(line.startswith(name + ' ') for line in remaining.stdout.splitlines())
        print('Disposed only this recovery test session')
