#!/usr/bin/env python3
"""Native TERM regression checks: disposable shells, no Pi or user sessions."""
import fcntl
import json
import os
from pathlib import Path
import pty
import re
import runpy
import select
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
import uuid

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[1]
CONFIG_SOURCE = Path(os.environ.get('ZELLIJ_TEST_CONFIG_SOURCE', str(REPO / 'dot_config/zellij')))
HELPER = Path(os.environ.get('ZELLIJ_TEST_HELPER', str(REPO / 'dot_config/zellij/bin/executable_zellij-ws')))
sys.path.insert(0, str(HELPER.parent))
g = runpy.run_path(str(HELPER))
m = g['manager']
binary = m.c['BINARY']
checks = []


def check(value, label):
    assert value, label
    checks.append(label)
    print('PASS', label, flush=True)


with tempfile.TemporaryDirectory(prefix='zellij-term-live-', dir='/tmp') as directory:
    root = Path(directory)
    config = root / 'config'; config.mkdir(); (config / 'layouts').mkdir()
    source = (CONFIG_SOURCE / 'config.kdl').read_text()
    carrier = (CONFIG_SOURCE / 'bridge.kdl').read_text()
    block = re.search(r'(?m)^env\s*\{[^{}]*\}', source).group()
    check('TERM "xterm-256color"' in block and 'TERM "xterm-256color"' in carrier, 'normal and carrier configs pin a valid virtual TERM')
    base_config = ('default_shell "/usr/bin/zsh"\ndefault_layout "default"\npane_frames false\n'
                   'session_serialization false\nshow_startup_tips false\nshow_release_notes false\n')
    config_file = config / 'config.kdl'
    (config / 'layouts/default.kdl').write_text('layout {\n    pane command="/usr/bin/zsh" {\n        args "-d"\n    }\n}\n')
    zdir = root / 'zsh'; zdir.mkdir()
    # A public prompt and the system highlighter, never the user's shell/history integrations.
    prompt = CONFIG_SOURCE.parent / 'zsh/prompt.zsh'
    starship = CONFIG_SOURCE.parent / 'starship.toml'
    probe = root / 'shell-info'
    base_rc = ('unset HISTFILE\nsource ' + json.dumps(str(prompt)) +
        '\nsource /usr/share/zsh/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh\n'
        'print -r -- "TERM=${TERM:-unset}" >> ' + json.dumps(str(probe)) + '\n')
    guarded_rc = 'source ' + json.dumps(str(CONFIG_SOURCE.parent / 'zsh/config.zsh')) + '\n' + base_rc
    (zdir / '.zshrc').write_text(guarded_rc)
    options = ['--config-dir', str(config), '--config', str(config_file)]
    m.c.update(CONFIG=config, OPTIONS=options, HOME_STATE=root / 'state', STATE=root / 'state/panes', SESSION='')
    previous = dict(os.environ)
    os.environ.update(TMPDIR='/tmp', ZDOTDIR=str(zdir), HISTFILE='/dev/null',
                      STARSHIP_CONFIG=str(starship), STARSHIP_CACHE=str(root / 'starship-cache'),
                      XDG_CACHE_HOME=str(root / 'cache'))
    for key in ['ZELLIJ', 'ZELLIJ_SESSION_NAME', 'ZELLIJ_PANE_ID', 'TMUX', 'TMUX_PANE']:
        os.environ.pop(key, None)

    def cli(name, *args):
        with m.session(name): return m.c['call'](*args)

    def attach(name):
        pid, fd = pty.fork()
        if pid == 0:
            fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack('HHHH', 47, 187, 0, 0))
            env = dict(os.environ, TERM='xterm-256color', TMPDIR='/tmp')
            os.execve(binary, [binary, *options, 'attach', name], env)
        return pid, fd

    def drain(fd, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if select.select([fd], [], [], min(.05, max(0, deadline-time.monotonic())))[0]:
                try: data = os.read(fd, 65536)
                except OSError: break
                if not data: break

    def wait_lines(fd, number):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            drain(fd, .1)
            if probe.exists() and len(probe.read_text().splitlines()) >= number: return
        raise RuntimeError('Fixture shell did not initialize')

    def cleanup(name, client):
        for attempt in range(2):
            try: m.remove_workspace(name); break
            except subprocess.CalledProcessError:
                if attempt: raise
        if client:
            pid, fd = client
            reaped = False
            for action in [None, signal.SIGTERM, signal.SIGKILL]:
                if action: os.kill(pid, action)
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline:
                    done, _ = os.waitpid(pid, os.WNOHANG)
                    if done: reaped = True; break
                    time.sleep(.05)
                if reaped: break
            assert reaped, 'Disposable client did not exit'
            os.close(fd)

    try:
        for inherited in [None, 'xterm-kitty']:
            config_file.write_text(base_config + block + '\n')
            probe.unlink(missing_ok=True)
            if inherited is None: os.environ.pop('TERM', None)
            else: os.environ['TERM'] = inherited
            name = 'term-live-' + uuid.uuid4().hex[:12]
            client = None
            try:
                m.ensure(name, str(root))
                client = attach(name); fd = client[1]
                wait_lines(fd, 1); drain(fd, 1)
                check(probe.read_text().strip() == 'TERM=xterm-256color', 'helper-created shell normalizes ' + str(inherited))
                for command in ['ls', 'echo hi', 'what is happening']:
                    for char in command.encode(): os.write(fd, bytes([char])); drain(fd, .06)
                    os.write(fd, b'\r'); drain(fd, .7)
                screen = cli(name, 'action', 'dump-screen', '--pane-id', 'terminal_0')
                check(not any(text in screen for text in ['lls', 'eecchecho hi', 'wwhhaat']), 'highlighted/transient input redraws cleanly from ' + str(inherited))
            finally: cleanup(name, client)

        # Config environment changes alone do not repair old server environments.
        # The zsh startup guard must protect new shells without restarting old ones.
        probe.unlink(missing_ok=True); config_file.write_text(base_config)
        (zdir / '.zshrc').write_text(base_rc)
        os.environ.pop('TERM', None)
        name = 'term-reload-' + uuid.uuid4().hex[:12]
        client = None
        try:
            m.register(name, str(root))
            subprocess.run([binary, *options, 'attach', '--create-background', name],
                           env=dict(os.environ, TMPDIR='/tmp'), cwd=root, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
            client = attach(name); fd = client[1]; wait_lines(fd, 1)
            check(probe.read_text().splitlines()[0] == 'TERM=unset', 'old-server fixture reproduces missing TERM')
            config_file.write_text(base_config + block + '\n')
            (zdir / '.zshrc').write_text(guarded_rc); drain(fd, 2)
            cli(name, 'action', 'new-pane'); wait_lines(fd, 2)
            check(probe.read_text().splitlines()[-1] == 'TERM=xterm-256color', 'startup guard gives new shells a valid TERM without restarting the old shell')
        finally: cleanup(name, client)
    finally:
        os.environ.clear(); os.environ.update(previous)
print(json.dumps({'passed': checks, 'user_sessions_touched': False, 'pi_launched': False}))
