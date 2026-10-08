#!/usr/bin/env python3
"""Opt-in authenticated deletion checks; only UUID-named fixtures, no Pi."""
import fcntl
import json
import os
from pathlib import Path
import pty
import runpy
import select
import shlex
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
import uuid
from unittest.mock import patch

HOST = os.environ['ZELLIJ_TEST_REMOTE_HOST']
TARGET = os.environ['ZELLIJ_TEST_REMOTE_TARGET']
os.environ['TMPDIR'] = '/tmp'
os.environ['ZELLIJ_SESSION_NAME'] = ''
state = tempfile.mkdtemp(prefix='remote-delete-live-', dir='/tmp')
os.environ['ZELLIJ_WS_STATE'] = state
# Run against the installed helpers, just as a desktop client would.
g = runpy.run_path(str(Path.home() / '.config/zellij/bin/zellij-ws'))
m = g['manager']
assert m.remotes.hosts()[HOST] == TARGET, 'Test target must match the local allowlist'
NAME = 'delete-live-' + uuid.uuid4().hex[:12]
OTHER = NAME + '-other'
SSH = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
       '-o', 'ConnectTimeout=8', '-o', 'ClearAllForwardings=yes', '-o', 'ForwardAgent=no', TARGET]
client = None
root = None
checks = []


def remote(code):
    script = ('import os; os.environ["TMPDIR"]="/tmp"; import runpy,json; from pathlib import Path; '
              'g=runpy.run_path(str(Path.home()/".config/zellij/bin/zellij-ws")); m=g["manager"]; ' + code)
    p = subprocess.run([*SSH, 'python3 -c ' + shlex.quote(script)], capture_output=True, text=True, timeout=30)
    if p.returncode: raise RuntimeError(p.stderr[-600:])
    return json.loads(p.stdout) if p.stdout.strip() else None


def check(value, label):
    assert value, label
    checks.append(label)
    print('PASS', label, flush=True)


def exists(name):
    return remote('print(json.dumps(' + repr(name) + ' in m.tx(lambda d:d.get("workspaces",{}))))')


def attach():
    pid, fd = pty.fork()
    if pid == 0:
        fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack('HHHH', 30, 120, 0, 0))
        env = dict(os.environ, TERM='xterm-256color', TMPDIR='/tmp')
        for key in ['ZELLIJ', 'ZELLIJ_SESSION_NAME', 'ZELLIJ_PANE_ID', 'TMUX', 'TMUX_PANE']:
            env.pop(key, None)
        helper = str(Path.home() / '.config/zellij/bin/zellij-ws')
        os.execve(helper, [helper, 'remote-attach', HOST, NAME], env)
    global client
    client = (pid, fd)
    deadline = time.monotonic() + 35
    screen = b''
    while time.monotonic() < deadline:
        if select.select([fd], [], [], .2)[0]:
            try: chunk = os.read(fd, 65536)
            except OSError: break
            screen = (screen + chunk)[-200000:]
            if b'1:shell' in screen: return
    raise RuntimeError('Disposable Mosh terminal did not render')


def detach():
    global client
    if not client: return
    pid, fd = client
    os.write(fd, b'\x00d')
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        done, _ = os.waitpid(pid, os.WNOHANG)
        if done: break
        if select.select([fd], [], [], .1)[0]:
            try: os.read(fd, 65536)
            except OSError: pass
    else:
        os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            done, _ = os.waitpid(pid, os.WNOHANG)
            if done: break
            time.sleep(.1)
        else: os.kill(pid, signal.SIGKILL); os.waitpid(pid, 0)
    os.close(fd); client = None


try:
    root = remote('import tempfile; p=Path(tempfile.mkdtemp(prefix=' + repr(NAME + '-') + ')); '
                  '(p/"pi-sentinel.jsonl").write_text("test conversation sentinel"); print(json.dumps(str(p)))')
    for name in [NAME, OTHER]: m.remotes.request(HOST, 'ensure', session=name, directory=root)
    preview = m.remotes.request(HOST, 'remove-preview', session=NAME)
    check(preview['session'] == NAME, 'preview names the exact disposable remote session')
    attach()
    for operation in ['remove-preview', 'remove']:
        try: m.remotes.request(HOST, operation, session=NAME, identity=preview['identity'])
        except ValueError as error:
            check('attached clients' in str(error), operation + ' refuses a connected Mosh client')
        else: raise AssertionError('Attached workspace was deletable')
    detach()
    deadline = time.monotonic() + 20
    while True:
        try: preview = m.remotes.request(HOST, 'remove-preview', session=NAME); break
        except ValueError:
            if time.monotonic() > deadline: raise
            time.sleep(.2)
    m.remotes.request(HOST, 'label', session=NAME, field='name', value='Deletion fixture')
    try: m.remotes.request(HOST, 'remove', session=NAME, identity=preview['identity'])
    except ValueError as error: check('changed' in str(error), 'stale confirmation is refused')
    else: raise AssertionError('Stale confirmation was accepted')
    row = {'host': HOST, 'session': NAME, 'name': 'Deletion fixture'}
    with patch('modal.pick', return_value=('cancel\tCancel', '')):
        m.confirm_remove(row)
    check(exists(NAME), 'cancel leaves the remote workspace intact')
    headers = []
    def confirm(options, header, **kwargs):
        headers.append(header)
        if options:
            check(options[0].startswith('cancel\t'), 'confirmation defaults to Cancel')
            check(HOST in header and TARGET in header and NAME in header, 'confirmation shows host/account/exact session')
            return 'remove\tRemove', ''
        return None, ''
    with patch('modal.pick', side_effect=confirm): m.confirm_remove(row)
    check(not any('removal failed' in header.lower() for header in headers), 'native deletion reports success')
    check(not exists(NAME), 'only the selected workspace metadata is removed')
    check(remote('print(json.dumps(' + repr(NAME) + ' not in m.discover()[1]))'),
          'native session and saved native cache are absent')
    check(exists(OTHER), 'unrelated disposable workspace is untouched')
    check(remote('print(json.dumps((Path(' + repr(root) + ')/"pi-sentinel.jsonl").read_text()=="test conversation sentinel"))'),
          'conversation sentinel and project directory survive')
    # Invoke the same server path a stale Mosh carrier would use, without a TTY.
    check(remote('name=' + repr(NAME) + '; '
                 'error=None\ntry: m.attach_remote_existing(name)\nexcept ValueError as e: error=str(e)\n'
                 'print(json.dumps(bool(error and "no longer exists" in error)))'),
          'stale carrier cannot recreate a deleted workspace')
    check(not exists(NAME), 'deleted workspace remains absent')
finally:
    detach()
    # Scoped cleanup only: both names were generated by this exact test.
    cleanup = ('names=' + repr([NAME, OTHER]) + '\n'
               'for name in names:\n'
               ' for attempt in range(2):\n'
               '  if name not in m.tx(lambda d:d.get("workspaces",{})): break\n'
               '  try: m.remove_workspace(name); break\n'
               '  except __import__("subprocess").CalledProcessError:\n'
               '   if attempt: raise\n'
               'print(json.dumps(True))')
    remote(cleanup)
    if root:
        remote('p=Path(' + repr(root) + '); (p/"pi-sentinel.jsonl").unlink(); p.rmdir(); print(json.dumps(True))')
    shutil.rmtree(state)
    print('Cleaned only this test\'s UUID-named workspaces and fixtures', flush=True)
print(json.dumps({'passed': checks, 'pi_launched': False, 'errors': []}, indent=2))
