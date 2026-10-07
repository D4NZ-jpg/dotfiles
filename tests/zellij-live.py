"""Use a private PTY/session, not the user's desktop or any LLM process."""
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

root = Path(__file__).resolve().parent
binary = os.environ.get('ZELLIJ_TRIAL_BINARY', str(Path.home() / '.local/state/dotfiles-review/zellij-trial/runtime/usr/bin/zellij'))
session = 'integration-' + uuid.uuid4().hex[:10]
with tempfile.TemporaryDirectory(prefix='zellij-live-', dir='/tmp') as tmp:
    tmp = Path(tmp)
    config = tmp / 'config.kdl'
    config.write_text(f'session_name "{session}"\ndefault_shell "/bin/sh"\nsession_serialization false\nshow_release_notes false\nshow_startup_tips false\n')
    # The helper derives CONFIG from HOME. Give every child a private config so
    # inventory never authenticates to real remotes or reads user Pi metadata.
    home = tmp / 'home'
    own_config = home / '.config/zellij'
    shutil.copytree(Path.home() / '.config/zellij/bin', own_config / 'bin')
    shutil.copytree(Path.home() / '.config/zellij/layouts', own_config / 'layouts')
    helper_config = (Path.home() / '.config/zellij/config.kdl').read_text()
    helper_config = helper_config.replace('load_plugins {\n    autolock\n}', '').replace('default_shell "/usr/bin/zsh"', 'default_shell "/bin/sh"')
    (own_config / 'config.kdl').write_text(helper_config)
    plugin = home / '.local/share/zellij/plugins/workspace-bar-0.45.1.wasm'
    plugin.parent.mkdir(parents=True)
    shutil.copy2(Path.home() / '.local/share/zellij/plugins/workspace-bar-0.45.1.wasm', plugin)
    env = dict(os.environ, HOME=str(home), XDG_CACHE_HOME=str(tmp / 'cache'),
               ZELLIJ_WS_STATE=str(tmp / 'state'), ZELLIJ_TRIAL_BINARY=binary, TERM='xterm-kitty', PI_ZELLIJ_NOTIFY='0')
    for k in ['TMUX', 'TMUX_PANE', 'ZELLIJ', 'ZELLIJ_PANE_ID', 'ZELLIJ_SESSION_NAME']:
        env.pop(k, None)
    # A unique result file prevents stale results from passing a new run.
    result = tmp / 'result.json'
    env['ZELLIJ_SMOKE_RESULT'] = str(result)
    subprocess.run(['python3', str(root.parent / 'setup/zellij-workspace-bar/grant-ui-permissions.py'),
                    str(plugin), '--cache', str(tmp / 'cache/zellij/permissions.kdl'),
                    '--backups', str(tmp / 'permission-backups')], check=True, env=env)
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 35, 120, 0, 0))
    def terminal():
        os.setsid()
        fcntl.ioctl(0, termios.TIOCSCTTY, 0)
    proc = subprocess.Popen([binary, '--config-dir', str(tmp), '--config', str(config), '--data-dir', str(tmp / 'data')],
                            env=env, stdin=slave, stdout=slave, stderr=slave, preexec_fn=terminal)
    os.close(slave)
    captured = bytearray()
    launched = False
    try:
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline and not result.exists():
            if select.select([master], [], [], 0.1)[0]:
                try: captured.extend(os.read(master, 65536))
                except OSError: break
            if proc.poll() is not None: break
            if not launched:
                # Socket readiness precedes layout readiness. Launching here
                # too early can race the initial terminal/pane allocation.
                ready = subprocess.run([binary, '-s', session, 'action', 'list-panes', '--json', '--all'],
                                       env=env, capture_output=True, text=True, timeout=5)
                try:
                    if not any(not p['is_plugin'] and not p['is_floating'] for p in json.loads(ready.stdout)):
                        continue
                except json.JSONDecodeError:
                    continue
                probe = subprocess.run([binary, '-s', session, 'run', '--floating', '--no-focus', '--close-on-exit', '--name', 'integration check', '--', 'python', str(root / 'zellij-live-smoke.py')], env=env, capture_output=True, text=True, timeout=5)
                launched = probe.returncode == 0
        if not result.exists():
            diag = subprocess.run([binary, '-s', session, 'action', 'list-panes', '--json', '--all'], env=env, capture_output=True, text=True, timeout=5)
            raise RuntimeError('Live test produced no result. Panes: ' + diag.stdout[-2500:] + diag.stderr[-300:] + '\nTerminal tail: ' + captured.decode(errors='replace')[-500:])
        data = json.loads(result.read_text())
        print(json.dumps(data, indent=2))
        if data['errors']: raise RuntimeError('Live smoke failed')
        # Keep a short, non-sensitive evidence artifact outside the disposable dir.
        evidence = Path.home() / '.local/state/dotfiles-review/zellij-migration-live.json'
        evidence.write_text(json.dumps(data, indent=2))
    finally:
        # Stop the client first: a pending switch-session can otherwise
        # reconnect and recreate a session after kill-session has returned.
        if proc.poll() is None:
            proc.terminate()
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired: proc.kill(); proc.wait()
        os.close(master)
        # These are only the uniquely named sessions created by this script.
        for name in [session, session + '-other', session + '-restore', session + '-closed-restore']:
            subprocess.run([binary, 'kill-session', name], env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        remaining = subprocess.run([binary, 'list-sessions', '--no-formatting'], env=env,
                                   capture_output=True, text=True, timeout=10)
        assert not any(line.startswith(session + ' ') or line.startswith(session + '-')
                       for line in remaining.stdout.splitlines()), 'Test session leaked after cleanup'
