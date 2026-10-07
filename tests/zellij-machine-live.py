#!/usr/bin/env python3
"""Opt-in authenticated Local → remote creation and key routing, disposable only."""
import fcntl
import base64
import json
import os
from pathlib import Path
import pty
import re
import runpy
import select
import shlex
import shutil
import signal
import struct
import subprocess
import tempfile
import termios
import time
import uuid

HOST = os.environ['ZELLIJ_TEST_REMOTE_HOST']
TARGET = os.environ['ZELLIJ_TEST_REMOTE_TARGET']
NAME = 'machine-check-' + uuid.uuid4().hex[:10]
SSH = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
       '-o', 'ConnectTimeout=8', '-o', 'ClearAllForwardings=yes', '-o', 'ForwardAgent=no', TARGET]
HELPER = Path.home() / '.config/zellij/bin/zellij-ws'
STATE = tempfile.mkdtemp(prefix='machine-live-')
os.environ['ZELLIJ_WS_STATE'] = STATE
os.environ['ZELLIJ_SESSION_NAME'] = ''
os.environ['TMPDIR'] = '/tmp'
g = runpy.run_path(str(HELPER))
m = g['manager']
bridge = m.remotes.bridge_name(HOST, NAME)
origin = 'machine-origin-' + NAME.removeprefix('machine-check-')
pid = None
fd = None
reaped = False
checks = []
timings = {}
buffer = b''


def remote(script):
    p = subprocess.run([*SSH, 'python3 -c ' + shlex.quote(script)], capture_output=True, text=True, timeout=25)
    if p.returncode: raise RuntimeError('Disposable remote operation failed: ' + p.stderr[-500:])
    return p.stdout.strip()


def wait_screen(needle, timeout=25):
    global buffer
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ready, _, _ = select.select([fd], [], [], .15)
        if ready:
            try: chunk = os.read(fd, 65536)
            except OSError: break
            if not chunk: break
            buffer = (buffer + chunk)[-200000:]
        plain = re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]', b'', buffer)
        if needle in plain: return
    raise RuntimeError('UI stage did not render: ' + needle.decode(errors='replace'))


def send(data):
    global buffer
    buffer = b''
    os.write(fd, data)


def drain():
    global buffer
    while select.select([fd], [], [], 0)[0]:
        try: chunk = os.read(fd, 65536)
        except OSError: break
        if not chunk: break
        buffer = (buffer + chunk)[-200000:]


def wait_bridge_client():
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        drain()
        with m.session(bridge):
            clients = g['call']('action', 'list-clients')
        with m.session(origin):
            source_clients = g['call']('action', 'list-clients')
            source_popups = [p for p in g['panes']() if p.get('is_floating')]
        packets = re.findall(rb'\x1bP26661n([A-Za-z0-9+/=]+)\x1b\\', buffer)
        target_state_rendered = any(bridge.encode() in base64.b64decode(packet) for packet in packets)
        if len(clients.splitlines()) > 1 and len(source_clients.splitlines()) <= 1 and not source_popups and target_state_rendered:
            drain()
            return
        time.sleep(.1)
    raise RuntimeError('Local client did not switch to the test remote workspace')


def inventory():
    return [row for row in m.remotes.request(HOST, 'inventory') if row['session'] == NAME]


def wait_inventory(predicate, label):
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        drain()
        try: rows = inventory()
        except ValueError:
            time.sleep(.2)
            continue
        if predicate(rows):
            checks.append(label)
            print('PASS', label, flush=True)
            return rows
        time.sleep(.2)
    raise RuntimeError('Remote routing did not complete: ' + label)


try:
    path = remote('from pathlib import Path; p=Path.home()/' + repr(NAME) + '; p.mkdir(mode=0o700); print(p)')
    m.ensure(origin)
    pid, fd = pty.fork()
    if pid == 0:
        fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 120, 0, 0))
        os.environ['TERM'] = 'xterm-256color'
        os.execv(m.c['BINARY'], [m.c['BINARY'], *m.options_for(origin), 'attach', origin])
    wait_screen(b'1:shell')
    send(b'\x00o')
    wait_screen(b'Local:')
    checks.append('creation starts in Local directory browser')
    print('PASS', checks[-1], flush=True)
    send(b'\x1bm')
    wait_screen(b'Workspace machine')
    started = time.monotonic()
    send(b'\x0e\r')  # Ctrl+N selects the second row: configured remote machine.
    wait_screen((HOST + ':').encode())
    timings['remote_lf_start_seconds'] = round(time.monotonic() - started, 3)
    wait_screen(b'machine-')  # Narrow lf columns can truncate the directory name.
    send(b'/' + NAME.encode())  # Same / search as the local lf browser.
    wait_screen(NAME.encode())  # Search input must render before it is accepted.
    send(b'\r')
    time.sleep(.2)
    drain()
    send(b'l')  # Same h/l navigation; enter the empty disposable directory.
    wait_screen((HOST + ': ~/m/').encode())  # lf abbreviates long paths to fit the popup.
    checks.append('local and remote use lf with the same search/navigation/selection keys')
    print('PASS', checks[-1], flush=True)
    print('Reached selected remote directory', flush=True)
    started = time.monotonic()
    send(b'.')  # Same current-directory selection as local.
    wait_screen(b'Workspace name')
    timings['remote_selection_return_seconds'] = round(time.monotonic() - started, 3)
    print('Reached workspace name prompt', flush=True)
    started = time.monotonic()
    send(NAME.encode() + b'\r')
    wait_screen(b'1:shell', 35)
    wait_bridge_client()
    wait_screen(('at ~/' + NAME).encode(), 20)
    timings['remote_creation_to_prompt_seconds'] = round(time.monotonic() - started, 3)
    checks.append('same flow creates named remote workspace and connects over Mosh')
    print('PASS', checks[-1], flush=True)
    spaces = m.remotes.request(HOST, 'rows')
    assert next(row for row in spaces if row['session'] == NAME)['directory'] == path
    with m.session(bridge):
        assert len(json.loads(g['call']('action', 'list-tabs', '--json'))) == 1
        assert len(g['panes']()) == 1
        layout = g['call']('action', 'dump-layout')
        assert 'zellij:tab-bar' not in layout
        assert 'workspace-bar-0.45.1.wasm' not in layout
    checks.append('transport UI hidden; remote path stored without local validation')
    print('PASS', checks[-1], flush=True)
    send(b'\x00c')
    wait_inventory(lambda rows: len({row['tab'] for row in rows}) == 2, 'prefix c creates a remote task tab')
    send(b'\x00n')
    wait_screen(b'Task name')
    send(b'remote-task\r')
    wait_inventory(lambda rows: any(row['note'] == 'remote-task' for row in rows), 'prefix n renames the remote task')
    send(b'\x00-')
    wait_inventory(lambda rows: len(rows) == 3, 'prefix split creates a remote pane')
    with m.session(bridge):
        assert len(g['panes']()) == 1
        assert len(json.loads(g['call']('action', 'list-tabs', '--json'))) == 1
    checks.append('remote actions do not create local tabs or panes')
    print('PASS', checks[-1], flush=True)
    send(b'\x00d')
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        done, _ = os.waitpid(pid, os.WNOHANG)
        if done: reaped = True; break
        time.sleep(.1)
except Exception:
    if bridge in m.tx(lambda data: data.get('workspaces', {})):
        with m.session(bridge):
            print('Test bridge local panes:', len(g['panes']()), flush=True)
            print('Test bridge local tabs:', len(json.loads(g['call']('action', 'list-tabs', '--json'))), flush=True)
            print('Test bridge attached clients:', max(0, len(g['call']('action', 'list-clients').splitlines()) - 1), flush=True)
        record = m.tx(lambda data: data['workspaces'][bridge])
        print('Test bridge remote context:', {key: record.get(key) for key in ['remote_host', 'remote_session', 'remote_config']}, flush=True)
        print('Test remote task panes:', len(inventory()), flush=True)
        with m.session(origin): print('Test origin local task panes:', len(g['panes']()), flush=True)
    without_packets = re.sub(rb'\x1bP.*?\x1b\\', b'', buffer, flags=re.S)
    plain = re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]', b'', without_packets).decode(errors='replace')
    errors = re.findall(r'zellij-ws: [^\x1b\r\n]{0,200}', plain)
    print('Disposable UI errors:', errors[-3:], flush=True)
    print('UI stage markers:', {text: text in plain for text in ['Local:', HOST + ':', 'Workspace machine', 'Workspace name', 'Permission denied']}, flush=True)
    print('Picker prompt diagnostics:', re.findall(re.escape(HOST) + r': [^\x1b\n]{0,120}', plain)[-3:], flush=True)
    raise
finally:
    if pid and not reaped:
        os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            done, _ = os.waitpid(pid, os.WNOHANG)
            if done: reaped = True; break
            time.sleep(.1)
        if not reaped:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
    if fd is not None: os.close(fd)
    m.c['SESSION'] = ''
    for local_session in [bridge, origin]:
        if local_session in m.tx(lambda data: data.get('workspaces', {})):
            try: m.remove_workspace(local_session)
            except subprocess.CalledProcessError: m.remove_workspace(local_session)
    cleanup = ('from pathlib import Path; import runpy; g=runpy.run_path(str(Path.home()/".config/zellij/bin/zellij-ws")); '
               'm=g["manager"]; name=' + repr(NAME) + '; '
               'm.remove_workspace(name) if name in m.tx(lambda data:data.get("workspaces",{})) else None; '
               '(Path.home()/name).rmdir()')
    remote(cleanup)
    shutil.rmtree(STATE)
    print('Disposed only this test workspace, transport, and empty directory', flush=True)
print(json.dumps({'passed': checks, 'timings': timings, 'errors': []}, indent=2))
