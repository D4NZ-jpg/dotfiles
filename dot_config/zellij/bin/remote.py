"""Explicit host allowlist, bounded SSH control plane and Mosh terminal transport."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import stat
import tempfile
import time
import uuid

SSH_OPTIONS = ['-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
               '-o', 'ConnectTimeout=4', '-o', 'ConnectionAttempts=1',
               '-o', 'ClearAllForwardings=yes', '-o', 'ForwardAgent=no']
SSH_BASE_OPTIONS = SSH_OPTIONS.copy()
SSH_OPTIONS += ['-o', 'ControlMaster=no', '-o', 'ControlPath=none']


def private_control(socket):
    """Only accept our owner-only /tmp directory; stale saved layouts fall back."""
    path = Path(socket)
    if (path.parent.parent != Path('/tmp') or
            not path.parent.name.startswith('zellij-ws-ssh-') or
            not re.fullmatch(r'c-[0-9a-f]{24}', path.name)):
        raise ValueError('Invalid private SSH control path')
    try:
        directory = path.parent.lstat()
    except FileNotFoundError:
        return False
    if (not stat.S_ISDIR(directory.st_mode) or directory.st_uid != os.getuid() or
            stat.S_IMODE(directory.st_mode) != 0o700):
        raise ValueError('Unsafe private SSH control directory')
    try:
        control = path.lstat()
    except FileNotFoundError:
        return False
    if not stat.S_ISSOCK(control.st_mode) or control.st_uid != os.getuid():
        raise ValueError('Unsafe private SSH control socket')
    return True


def ready_path(socket, ready):
    path = Path(ready)
    if path.parent != Path(socket).parent or not re.fullmatch(r'ready-[0-9a-f]{32}', path.name):
        raise ValueError('Invalid SSH readiness path')
    return path


def reuse_options(socket, master='auto'):
    # OpenSSH takes the first value: replace, never append to SSH_OPTIONS.
    return [*SSH_BASE_OPTIONS, '-o', 'ControlMaster=' + master,
            '-o', 'ControlPath=' + str(socket), '-o', 'ControlPersist=120']
REMOTE_HELPER = '$HOME/.config/zellij/bin/zellij-ws'


class Remotes:
    def __init__(self, manager):
        self.m = manager
        self.errors = []
        self._scope_depth = 0
        self._control_dir = None
        self._controls = {}

    @contextmanager
    def connection_scope(self):
        self._scope_depth += 1
        try:
            yield
        finally:
            self._scope_depth -= 1
            if not self._scope_depth:
                self.close_connections()

    def control_path(self, host):
        target = self.hosts()[host]
        if not self._scope_depth:
            return None
        if self._control_dir is None:
            self._control_dir = tempfile.TemporaryDirectory(prefix='zellij-ws-ssh-', dir='/tmp')
        if target not in self._controls:
            self._controls[target] = Path(self._control_dir.name) / ('c-' + hashlib.sha256(target.encode()).hexdigest()[:24])
        return self._controls[target]

    def ssh_options(self, host):
        socket = self.control_path(host)
        return reuse_options(socket) if socket else SSH_OPTIONS.copy()

    def close_connections(self):
        try:
            for target, socket in self._controls.items():
                try:
                    if private_control(socket):
                        subprocess.run(['ssh', '-T', *reuse_options(socket, 'no'), '-O', 'exit', target],
                                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL, timeout=3)
                except (OSError, ValueError, subprocess.SubprocessError):
                    # ControlPersist also bounds lifetime if the owner is interrupted.
                    pass
        finally:
            self._controls.clear()
            if self._control_dir is not None:
                self._control_dir.cleanup()
                self._control_dir = None

    def hosts(self):
        path = self.m.c['CONFIG'] / 'remotes.json'
        hosts = json.loads(path.read_text()) if path.exists() else {}
        for label, target in hosts.items():
            import re
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', label) or not re.fullmatch(r'[A-Za-z0-9._-]+@[A-Za-z0-9][A-Za-z0-9.-]*', target):
                raise ValueError('Invalid remote host configuration')
        return hosts

    def request(self, host, operation, **values):
        target = self.hosts()[host]
        result = subprocess.run(['ssh', '-T', *self.ssh_options(host), target,
                                 REMOTE_HELPER + ' remote-rpc'],
                                input=json.dumps({'operation': operation, **values}),
                                text=True, capture_output=True, timeout=12)
        if result.returncode:
            raise ValueError('Remote ' + host + ' unavailable (SSH/helper failure)')
        if len(result.stdout) > 2_000_000:
            raise ValueError('Remote response exceeds limit')
        reply = json.loads(result.stdout)
        if 'error' in reply:
            raise ValueError('Remote ' + host + ': ' + self.m.c['clean'](reply['error'], 160))
        return reply['result']

    def collect(self, operation, **values):
        self.errors = []
        result = []
        for host in self.hosts():
            try:
                remote_rows = self.request(host, operation, **values)
                for row in remote_rows:
                    result.append({**row, 'host': host})
            except (ValueError, OSError, KeyError, subprocess.SubprocessError):
                self.errors.append(host + ' offline')
        return result

    def bridge_name(self, host, session):
        # Keep already-open legacy transports untouched; future selections use
        # the normal-workspace key routing and borderless transport layout.
        return 'remote-' + host + '-v2-' + hashlib.sha256(session.encode()).hexdigest()[:16]

    def bridge_layout(self, host, session, control=None, ready=None):
        """A fresh transport recipe, never serialized Mosh process state."""
        if host not in self.hosts():
            raise ValueError('Remote restore host is no longer allowlisted')
        self.m.validate_name(session)
        if bool(control) != bool(ready):
            raise ValueError('Private SSH attach requires a readiness path')
        if control:
            ready_path(control, ready)
            if not private_control(control):
                raise ValueError('Remote startup SSH control has expired')
        from workspaces import quoted
        helper = str(self.m.c['CONFIG'] / 'bin/zellij-ws')
        return ('layout {\n    pane command=' + quoted(helper) +
                ' borderless=true {\n        args "remote-attach" ' + quoted(host) + ' ' + quoted(session) +
                (' "--control" ' + quoted(str(control)) + ' "--ready" ' + quoted(str(ready)) if control else '') +
                '\n        start_suspended false\n    }\n}\n')

    def switch(self, row):
        with self.connection_scope():
            return self._switch(row)

    def _switch(self, row):
        host, session = row['host'], row['session']
        # Read-only inventory never creates sessions. Only an explicit selection does.
        self.request(host, 'ensure', session=session, directory=row.get('directory'))
        name = self.bridge_name(host, session)
        _, found = self.m.discover()
        self.m.register(name)
        self.m.tx(lambda data: data['workspaces'][name].update(remote_bridge=True,
                      remote_host=host, remote_session=session, remote_config=str(self.m.c['CONFIG'] / 'bridge.kdl')))
        ready = None
        if found.get(name) != 'live':
            socket = self.control_path(host)
            if socket and private_control(socket):
                ready = socket.parent / ('ready-' + uuid.uuid4().hex)
            layout = self.bridge_layout(host, session)
            path = self.m.path('layouts/' + hashlib.sha256(name.encode()).hexdigest() + '.kdl')
            self.m.atomic_text(path, layout)
        if row.get('pane'):
            self.request(host, 'focus', session=session, pane=row['pane'], activity=row.get('activity'))
        if ready:
            try:
                self.m.ensure(name, remote_start=(str(socket), str(ready)))
                deadline = time.monotonic() + 15
                while not ready.exists() and time.monotonic() < deadline:
                    time.sleep(.025)
                if not ready.exists() or ready.read_text() != '0':
                    raise ValueError('Remote terminal handshake did not finish; select the workspace again')
            finally:
                # A private socket belongs only to this selection, never to a
                # durable restore recipe (including failed handshakes).
                self.m.atomic_text(path, self.bridge_layout(host, session))
        # The carrier has finished SSH. Mosh now owns its independent UDP transport.
        # Close before native attach can exec (which bypasses Python finally blocks).
        self.close_connections()
        self.m.switch(name)

    def ssh_handshake(self, host, socket, ready, args):
        marker = ready_path(socket, ready)
        active = private_control(socket)
        target = self.hosts()[host]
        # Mosh remote-IP mode supplies only these SSH flags, an allowlisted target,
        # '--', and its generated server command. No key/output inspection here.
        separator = args.index('--') if '--' in args else -1
        if (separator < 1 or args[separator - 1] != target or
                any(flag not in ('-n', '-tt', '-4', '-6') for flag in args[:separator - 1]) or
                len(args[separator + 1:]) != 1):
            raise ValueError('Invalid Mosh SSH handshake arguments')
        options = reuse_options(socket, 'no') if active else SSH_OPTIONS
        completed = subprocess.run(['ssh', *options, *args])
        if active and private_control(socket):
            temporary = marker.with_suffix('.tmp')
            try:
                fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, 'w') as output:
                    output.write(str(completed.returncode))
                os.link(temporary, marker)
            finally:
                temporary.unlink(missing_ok=True)
        return completed.returncode

    def attach(self, host, session, control=None, ready=None):
        target = self.hosts()[host]
        self.m.validate_name(session)
        ssh = shlex.join(['ssh', *SSH_OPTIONS])
        extra = []
        if bool(control) != bool(ready):
            raise ValueError('Private SSH attach requires a readiness path')
        if control:
            ready_path(control, ready)
            if private_control(control):
                helper = str(self.m.c['CONFIG'] / 'bin/zellij-ws')
                ssh = shlex.join([helper, 'remote-ssh', host, control, ready])
                # Default Mosh proxy mode forces '-S none', defeating reuse.
                extra = ['--experimental-remote-ip=remote']
        mosh = '/usr/bin/mosh'
        env = dict(os.environ, TMPDIR='/tmp')
        for key in ['ZELLIJ', 'ZELLIJ_SESSION_NAME', 'ZELLIJ_PANE_ID', 'TMUX', 'TMUX_PANE']:
            env.pop(key, None)
        os.execvpe(mosh, [mosh, '--predict=never', *extra, '--ssh=' + ssh, target,
                         '.config/zellij/bin/zellij-ws', 'remote-serve', session], env)


# Native actions whose scope is the selected workspace's machine.
ACTIONS = {
    'left': ['MoveFocus', 'Left'], 'down': ['MoveFocus', 'Down'],
    'up': ['MoveFocus', 'Up'], 'right': ['MoveFocus', 'Right'],
    'split-down': ['NewPane', 'Down'], 'split-right': ['NewPane', 'Right'],
    'close': ['CloseFocus'], 'next-pane': ['SwitchFocus'], 'last-pane': ['FocusLastPane'],
    'fullscreen': ['ToggleFocusFullscreen'],
    'move-left': ['MovePane', 'Left'], 'move-down': ['MovePane', 'Down'],
    'move-up': ['MovePane', 'Up'], 'move-right': ['MovePane', 'Right'],
    'previous-tab': ['GoToPreviousTab'], 'next-tab': ['GoToNextTab'], 'last-tab': ['ToggleTab'],
    'scroll-down': ['ScrollDown'], 'scroll-up': ['ScrollUp'],
    'page-up': ['PageScrollUp'], 'page-down': ['PageScrollDown'],
    'half-up': ['HalfPageScrollUp'], 'half-down': ['HalfPageScrollDown'],
    'scroll-top': ['ScrollToTop'], 'scroll-bottom': ['ScrollToBottom'],
    'start-scroll': ['SwitchToMode', 'Scroll'],
}


def rpc(manager):
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        result = _rpc(manager)
    print(json.dumps({'result': result}))


def _rpc(manager):
    import sys
    request = json.loads(sys.stdin.read(16385))
    op = request['operation']
    if op == 'directory-result':
        from directory import take_directory_result
        result = take_directory_result(manager, request['token'])
    elif op == 'directories':
        raw = request.get('directory')
        path = Path(raw).expanduser().resolve() if raw else Path.home() / 'dev'
        if not path.is_dir() and not raw: path = Path.home()
        if not path.is_dir(): raise ValueError('Directory does not exist')
        result = {'directory': str(path), 'parent': str(path.parent),
                  'directories': sorted([{'name': p.name, 'path': str(p)} for p in path.iterdir() if p.is_dir()], key=lambda row: row['name'])[:5000]}
    elif op == 'rows':
        result = manager.rows(local_only=True)
    elif op == 'inventory':
        result = manager.inventory(bool(request.get('attention')), bool(request.get('agents_only')), local_only=True)
    else:
        session = manager.validate_name(request['session'])
        if op == 'ensure':
            result = manager.ensure(session, request.get('directory'))
        elif op == 'remove-preview':
            result = manager.remote_remove_snapshot(session)
        elif op == 'remove':
            result = manager.remove_remote_workspace(session, request.get('identity'))
        elif op == 'task':
            with manager.session(session):
                command = request['command']
                if command == 'action':
                    action = request['action']
                    if action not in ACTIONS: raise ValueError('Unsupported workspace action')
                    # Zellij's CLI names are kebab-case versions of its KDL actions.
                    cli = {'MoveFocus': 'move-focus', 'NewPane': 'new-pane', 'CloseFocus': 'close-pane',
                           'SwitchFocus': 'focus-next-pane', 'FocusLastPane': 'focus-last-pane',
                           'ToggleFocusFullscreen': 'toggle-fullscreen', 'MovePane': 'move-pane',
                           'GoToPreviousTab': 'go-to-previous-tab', 'GoToNextTab': 'go-to-next-tab',
                           'ToggleTab': 'toggle-tab', 'ScrollDown': 'scroll-down', 'ScrollUp': 'scroll-up',
                           'PageScrollUp': 'page-scroll-up', 'PageScrollDown': 'page-scroll-down',
                           'HalfPageScrollUp': 'half-page-scroll-up', 'HalfPageScrollDown': 'half-page-scroll-down',
                           'ScrollToTop': 'scroll-to-top', 'ScrollToBottom': 'scroll-to-bottom', 'SwitchToMode': 'switch-mode'}
                    native = ACTIONS[action]
                    args = ['send-keys', 'Alt Tab'] if action == 'last-tab' else [cli[native[0]], *[arg.lower() for arg in native[1:]]]
                    if native[0] == 'NewPane': args = ['new-pane', '--direction', native[1].lower()]
                    result = manager.c['call']('action', *args)
                elif command == 'new-tab':
                    result = manager.new_tab(request.get('argv'), request.get('cwd'), request.get('name', 'shell'), bool(request.get('focus', True)))
                elif command == 'open':
                    values = request['values']
                    import argparse
                    if not values.get('cwd'):
                        focused = next((p for p in manager.c['panes']() if p.get('is_focused')), {})
                        values['cwd'] = focused.get('pane_cwd') or str(Path.home())
                    manager.c['open_command'](argparse.Namespace(**values))
                    result = True
                elif command == 'note':
                    pane = request.get('pane') or next(( 'terminal_' + str(p['id']) for p in manager.c['panes']() if p.get('is_focused')), None)
                    if not pane: raise ValueError('No focused remote pane')
                    if request.get('text') is None:
                        import re
                        selected = next(p for p in manager.c['panes']() if 'terminal_' + str(p['id']) == pane)
                        result = re.sub(r'^\d+:', '', selected.get('tab_name', ''))
                    else:
                        manager.window_note(request['text'], pane)
                        result = True
                elif command == 'slot':
                    manager.slot(int(request['number'])); result = True
                elif command == 'save':
                    manager.save(); result = True
                else: raise ValueError('Unsupported remote task command')
        elif op in ('focus', 'snooze', 'preview'):
            with manager.session(session):
                pane = manager.c['pane_id'](request['pane'])
                rows = manager.c['inventory']()
                row = next((row for row in rows if row['pane'] == pane), None)
                if not row or (request.get('activity') is not None and row['activity'] != request['activity']):
                    raise ValueError('Remote pane changed; refresh the picker')
                if op == 'snooze':
                    result = manager.c['snooze'](pane, request['activity'])
                elif op == 'focus':
                    live = next(p for p in manager.c['panes']() if 'terminal_' + str(p['id']) == pane)
                    manager.c['call']('action', 'go-to-tab', str(live.get('tab_position', 0) + 1))
                    manager.c['call']('action', 'focus-pane-id', pane)
                    result = True
                else:
                    if row['state'] in ('shell', 'exited'):
                        result = ''
                    else:
                        screen = manager.c['call']('action', 'dump-screen', '--pane-id', pane)
                        result = '\n'.join(screen.splitlines()[-12:])[:12000]
        elif op == 'label':
            field = request['field']
            if field not in ('name', 'group'):
                raise ValueError('Invalid label field')
            value = manager.c['clean'](request['value'], 80)
            def update(data):
                if field == 'name' and any(key != session and item.get('name') == value for key, item in data['workspaces'].items()):
                    raise ValueError('Another workspace has that label')
                data['workspaces'][session][field] = value
            manager.tx(update)
            result = True
        else:
            raise ValueError('Unsupported remote operation')
    return result
