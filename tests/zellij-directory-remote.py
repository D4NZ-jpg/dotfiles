#!/usr/bin/env python3
"""Opt-in real remote lf controls in isolated PTYs; never creates a workspace."""
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import shlex
import shutil
import subprocess
import tempfile
import termios
import struct
import time

HOST = os.environ['ZELLIJ_TEST_REMOTE_HOST']
TARGET = os.environ['ZELLIJ_TEST_REMOTE_TARGET']
SSH = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
       '-o', 'ConnectTimeout=8', '-o', 'ClearAllForwardings=yes', '-o', 'ForwardAgent=no',
       '-o', 'ControlMaster=no', '-o', 'ControlPath=none', TARGET]
setup = ('from pathlib import Path;import tempfile;h=Path.home(); '
         'p=Path(tempfile.mkdtemp(prefix="lf-shared-check-",dir=str(h/".local/state/dotfiles-review"))); '
         's=p/"browse with spaces"; (s/"a project"/"child").mkdir(parents=True); '
         '(s/"b-project").mkdir(); (s/"0-file-not-a-directory").write_text("fixture");print(p)')
p = subprocess.run([*SSH, 'python3 -c ' + shlex.quote(setup)], capture_output=True, text=True, timeout=20)
p.check_returncode()
remote_root = p.stdout.strip()
start = remote_root + '/browse with spaces'
cases = [('Enter selected', [b'\r'], 'a project'),
         ('j/k motion', [b'j', b'k', b'j', b'\r'], 'b-project'),
         ('h/l browse', [b'l', b'h', b'\r'], 'a project'),
         ('Search', [b'/b-project\r', b'\r'], 'b-project'),
         ('Current directory', [b'.'], '.'),
         ('Empty directory', [b'l', b'l', b'\r'], 'a project/child'),
         ('q cancel', [b'q'], None), ('Esc cancel', [b'\x1b'], None),
         ('Alt+M machine switch', [b'\x1bm'], '@machine'),
         ('New folder', [b'n', b'fresh idea\r'], 'fresh idea'),
         ('New folder back to browsing', [b'n', (b'\r', 2.5), b'j', b'\r'], 'b-project')]
try:
    for label, inputs, expected in cases:
        with tempfile.TemporaryDirectory(prefix='remote-lf-pty-', dir='/tmp') as tmp:
            result = Path(tmp) / 'result.json'
            code = ('import runpy,json;from pathlib import Path;'
                    'g=runpy.run_path(str(Path.home()/".config/zellij/bin/zellij-ws"));'
                    'from directory import pick_remote_directory;'
                    'r=g["manager"].remotes\n'
                    'with r.connection_scope():\n'
                    ' target=pick_remote_directory(g["manager"],' + repr(HOST) + ',' + repr(start) + ')\n'
                    ' control=r.control_path(' + repr(HOST) + ')\n'
                    'assert not control.parent.exists(), "Private SSH directory leaked"\n'
                    'Path(' + repr(str(result)) + ').write_text(json.dumps(target))')
            master, slave = pty.openpty()
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 25, 100, 0, 0))
            def terminal():
                os.setsid()
                fcntl.ioctl(0, termios.TIOCSCTTY, 0)
            env = dict(os.environ, TERM='xterm-kitty', PYTHONDONTWRITEBYTECODE='1', ZELLIJ_SESSION_NAME='')
            proc = subprocess.Popen(['python3', '-c', code], stdin=slave, stdout=slave, stderr=slave,
                                    env=env, preexec_fn=terminal)
            os.close(slave)
            captured = bytearray()
            def drain(seconds):
                end = time.monotonic() + seconds
                while time.monotonic() < end:
                    if select.select([master], [], [], .05)[0]:
                        try: captured.extend(os.read(master, 65536))
                        except OSError: break
            try:
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline and HOST.encode() + b':' not in captured:
                    drain(.1)
                assert HOST.encode() + b':' in captured, 'Shared remote lf header did not render'
                drain(.4)
                for keys in inputs:
                    # (keys, seconds) waits longer, e.g. while remote lf reopens.
                    keys, wait = keys if isinstance(keys, tuple) else (keys, .6 if label.startswith('New folder') else .25)
                    os.write(master, keys)
                    drain(wait)
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline and not result.exists(): drain(.1)
                proc.wait(timeout=3)
                actual = json.loads(result.read_text())
                wanted = expected if expected in (None, '@machine') else start if expected == '.' else start + '/' + expected
                assert actual == wanted, (label, actual, wanted)
                print('PASS remote lf ' + label, flush=True)
            finally:
                if proc.poll() is None:
                    os.killpg(proc.pid, 15)
                    try: proc.wait(timeout=3)
                    except subprocess.TimeoutExpired: os.killpg(proc.pid, 9);proc.wait()
                os.close(master)
finally:
    cleanup = ('from pathlib import Path;import shutil;p=Path(' + repr(remote_root) + ');'
               'assert p.name.startswith("lf-shared-check-");shutil.rmtree(p);print("Removed remote picker fixtures")')
    p = subprocess.run([*SSH, 'python3 -c ' + shlex.quote(cleanup)], capture_output=True, text=True, timeout=20)
    p.check_returncode()
    print(p.stdout.strip(), flush=True)
