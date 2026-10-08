"""Workspace registry, terminal pickers and private Pi restoration metadata."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import textwrap
import time
import uuid

STRING = r'"(?:[^"\\]|\\.)*"'
WORKSPACE_BAR_URL = 'file:~/.local/share/zellij/plugins/workspace-bar-0.45.1.wasm'


def quoted(value):
    return json.dumps(str(value), ensure_ascii=False)


def without_bars(text):
    lines, out, index = text.splitlines(keepends=True), [], 0
    def delta(line):
        masked = re.sub(STRING, '""', line)
        return masked.count('{') - masked.count('}')
    while index < len(lines):
        end = index + 1
        if re.match(r'\s*pane\b', lines[index]):
            depth = delta(lines[index])
            while depth > 0 and end < len(lines):
                depth += delta(lines[end])
                end += 1
            block = lines[index:end]
            if any(re.match(r'\s*plugin\s+location="zellij:compact-bar"', line) for line in block) and not any(re.match(r'\s*pane\b', line) for line in block[1:]):
                index = end
                continue
        out.append(lines[index])
        index += 1
    return ''.join(out)


def tab_bar(indent=''):
    return (indent + 'pane size=1 borderless=true {\n' +
            indent + '    plugin location=' + quoted(WORKSPACE_BAR_URL) + ' {\n' +
            indent + '        hide_swap_layout_indication true\n' +
            indent + '    }\n' + indent + '}\n')


def with_top_tabs(text):
    """Migrate native bars and add one workspace-labelled row to each tab."""
    locations = ['zellij:tab-bar', WORKSPACE_BAR_URL,
                 WORKSPACE_BAR_URL.replace('file:~', 'file:' + str(Path.home()), 1)]
    pattern = r'(?m)^(\s*plugin\s+location=)(' + '|'.join(re.escape(quoted(url)) for url in locations) + ')'
    text = re.sub(pattern, lambda match: match.group(1) + quoted(WORKSPACE_BAR_URL), text)
    lines = text.splitlines(keepends=True)
    insertions = []
    for index, line in enumerate(lines):
        match = re.match(r'^(\s*)(?:tab\b|new_tab_template\b).*\{\s*$', line)
        if not match:
            continue
        depth, end = 0, index
        for end in range(index, len(lines)):
            masked = re.sub(STRING, '""', lines[end])
            depth += masked.count('{') - masked.count('}')
            if depth == 0:
                break
        if not any('plugin location=' + quoted(WORKSPACE_BAR_URL) in item for item in lines[index:end+1]):
            insertions.append((index + 1, tab_bar(match.group(1) + '    ')))
    for index, block in reversed(insertions):
        lines.insert(index, block)
    return ''.join(lines)


def shell_header(line):
    """Use Zellij's default shell without changing cwd or pane geometry."""
    line = re.sub(r'\bcommand=' + STRING + r'\s*', '', line)
    line = re.sub(r'\bstart_suspended=(?:true|false)\s*', '', line)
    if re.search(r'\bname=' + STRING, line):
        line = re.sub(r'\bname=' + STRING, 'name="shell"', line)
    return line


def rewrite_layout(text, agents, command):
    """Resume exact Pi threads; restore unmapped Pi panes as ordinary shells."""
    text = with_top_tabs(without_bars(text))
    out = []
    target_depth = None
    wrapper_depth = None
    unknown_node_depth = None
    unknown_node_header = None
    unknown_node_properties = []
    depth = 0
    matched = set()
    for line in text.splitlines():
        stripped = re.sub(STRING, '""', line)
        if target_depth is not None and depth == target_depth:
            if re.match(r'\s*(args|start_suspended)\b', line):
                depth += stripped.count('{') - stripped.count('}')
                continue
        if wrapper_depth is not None and depth == wrapper_depth and re.match(r'\s*start_suspended\b', line):
            depth += stripped.count('{') - stripped.count('}')
            continue
        match = re.match(r'^(\s*)pane\b.*?\bname=(' + STRING + r')', line)
        command_match = re.match(r'^\s*pane\b.*?\bcommand=(' + STRING + r')', line)
        known = bool(match and json.loads(match.group(2)) in agents)
        if command_match and json.loads(command_match.group(1)) == command and '{' in stripped:
            # An existing guarded wrapper already binds an exact token. Preserve
            # it even if a later conversation reused the same pane title.
            if known:
                name = json.loads(match.group(2))
                if name in matched:
                    raise ValueError('Ambiguous serialized Pi pane title; refusing unsafe restore')
                matched.add(name)
            line = re.sub(r'\bstart_suspended=(?:true|false)\s*', '', line)
            out.append(line)
            indent = re.match(r'^(\s*)', line).group(1) + '    '
            out.append(indent + 'start_suspended false')
            wrapper_depth = depth + 1
            depth += stripped.count('{') - stripped.count('}')
            continue
        if command_match and not known:
            executable = Path(json.loads(command_match.group(1))).name
            if executable in ('pi', 'pi-coding-agent'):
                line = shell_header(line)
                target_depth = depth + 1 if '{' in stripped else None
            if executable in ('node', 'nodejs'):
                unknown_node_depth = depth + 1
                unknown_node_header = len(out)
                unknown_node_properties = []
        if unknown_node_depth == depth:
            if re.match(r'\s*start_suspended\b', line):
                unknown_node_properties.append(len(out))
            if re.match(r'\s*args\b', line):
                values = [json.loads(value) for value in re.findall(STRING, line)]
                if any(Path(value).name == 'pi' or ('coding-agent' in value and value.endswith('cli.js')) for value in values):
                    out[unknown_node_header] = shell_header(out[unknown_node_header])
                    for index in reversed(unknown_node_properties):
                        del out[index]
                    target_depth = depth
                    unknown_node_depth = None
                    depth += stripped.count('{') - stripped.count('}')
                    continue
        if match and '{' in stripped:
            name = json.loads(match.group(2))
            if name in agents:
                if name in matched:
                    raise ValueError('Ambiguous serialized Pi pane title; refusing unsafe restore')
                matched.add(name)
                line = re.sub(r'\bcommand=' + STRING + r'\s*', '', line)
                line = re.sub(r'\bstart_suspended=(?:true|false)\s*', '', line)
                line = line.replace('pane ', 'pane command=' + quoted(command) + ' ', 1)
                out.append(line)
                target_depth = depth + 1
                indent = match.group(1) + '    '
                out.append(indent + 'args ' + quoted(agents[name]['token']))
                out.append(indent + 'start_suspended false')
                depth += stripped.count('{') - stripped.count('}')
                continue
        out.append(line)
        depth += stripped.count('{') - stripped.count('}')
        if target_depth is not None and depth < target_depth:
            target_depth = None
        if wrapper_depth is not None and depth < wrapper_depth:
            wrapper_depth = None
        if unknown_node_depth is not None and depth < unknown_node_depth:
            unknown_node_depth = None
    return '\n'.join(out) + '\n', matched


class WorkspaceManager:
    def __init__(self, core):
        self.c = core
        from remote import Remotes
        self.remotes = Remotes(self)

    def remote_context(self):
        row = self.tx(lambda data: dict(data.get('workspaces', {}).get(self.c['SESSION'], {})))
        if row.get('remote_host') and row.get('remote_session'):
            return {'host': row['remote_host'], 'session': row['remote_session']}
        return None

    def remote_task(self, command, **values):
        context = self.remote_context()
        if not context: return None
        return self.remotes.request(context['host'], 'task', session=context['session'], command=command, **values)

    @property
    def root(self):
        return self.c['HOME_STATE']

    def path(self, name):
        return self.root / name

    def tx(self, fn, name='registry.json'):
        return self.c['transact'](fn, self.path(name))

    @contextlib.contextmanager
    def session(self, name):
        old = self.c['SESSION']
        self.c['SESSION'] = name
        try:
            yield
        finally:
            self.c['SESSION'] = old

    def options_for(self, name):
        options = list(self.c['OPTIONS'])
        row = self.tx(lambda data: dict(data.get('workspaces', {}).get(name, {})))
        if row.get('remote_config'):
            options[options.index('--config') + 1] = row['remote_config']
        return options

    def cli(self, *args, cwd=None):
        # A background server must not inherit a caller's disposable sandbox.
        env = dict(os.environ, TMPDIR='/tmp')
        env['PATH'] = str(self.c['CONFIG'] / 'bin') + ':' + str(Path.home() / '.local/bin') + ':' + env.get('PATH', '')
        if 'attach' in args:
            # Otherwise --layout can be interpreted as adding tabs to the caller.
            for key in ['ZELLIJ', 'ZELLIJ_SESSION_NAME', 'ZELLIJ_PANE_ID', 'TMUX', 'TMUX_PANE']:
                env.pop(key, None)
        options = self.options_for(args[-1]) if 'attach' in args else self.c['OPTIONS']
        return subprocess.run([self.c['BINARY'], *options, *args],
                              cwd=cwd, env=env, check=True, capture_output=True, text=True, timeout=15).stdout.strip()

    def validate_name(self, name):
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._ -]{0,79}', name) or name in ('.', '..'):
            raise ValueError('Workspace name: letters, numbers, spaces, dot, dash or underscore; no slashes')
        return name

    def discover(self):
        try:
            text = self.cli('list-sessions', '--no-formatting')
        except subprocess.CalledProcessError as error:
            # Zellij reports an empty fresh installation with exit status 1.
            if error.returncode != 1 or 'No active zellij sessions found.' not in (error.stderr or ''):
                raise
            text = ''
        found = {}
        for line in text.splitlines():
            match = re.match(r'^(.*?) \[Created ', line)
            if match:
                found[match.group(1)] = 'exited' if '(EXITED' in line else 'live'
        def update(data):
            spaces = data.setdefault('workspaces', {})
            for name in found:
                if name not in spaces:
                    spaces[name] = {'name': name, 'group': 'trial' if name == 'zellij-trial' else '',
                                    'order': data.get('next_order', 0), 'directory': str(Path.home())}
                    data['next_order'] = data.get('next_order', 0) + 1
            return dict(data)
        data = self.tx(update)
        return data, found

    def resolve(self, name):
        data = self.tx(lambda d: dict(d))
        spaces = data.get('workspaces', {})
        if name in spaces:
            return name
        matches = [key for key, row in spaces.items()
                   if row.get('name') == name or
                   (row.get('group') and row['group'] + '/' + row.get('name', key) == name)]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError('Ambiguous workspace name')
        return self.validate_name(name)

    def register(self, name, cwd=None, group=None):
        name = self.resolve(name)
        cwd = str(Path(cwd or Path.home()).expanduser().resolve())
        if not Path(cwd).is_dir():
            raise ValueError('Workspace directory does not exist')
        if group is None:
            base = str(Path.home() / 'dev') + '/'
            group = next((g for g in ['work', 'projects', 'side'] if cwd.startswith(base + g + '/')), '')
        def update(data):
            spaces = data.setdefault('workspaces', {})
            if name not in spaces:
                spaces[name] = {'name': name, 'group': group, 'directory': cwd,
                                'order': data.get('next_order', 0)}
                data['next_order'] = data.get('next_order', 0) + 1
            return spaces[name].copy()
        return name, self.tx(update)

    def ensure(self, name, cwd=None, remote_start=None):
        name, row = self.register(name, cwd)
        _, found = self.discover()
        if found.get(name) == 'live' and row.get('remote_bridge'):
            self.repair_stopped_bridge(name, row, remote_start)
        if found.get(name) != 'live':
            if remote_start is None:
                self.prepare_restore(name)
            else:
                self.prepare_restore(name, remote_start=remote_start)
            try:
                args = ['attach', '--create-background', name]
                if name not in found:
                    layout = self.path('layouts/' + hashlib.sha256(name.encode()).hexdigest() + '.kdl')
                    if layout.exists():
                        args = ['--layout', str(layout), *args]
                self.cli(*args, cwd=row['directory'] if Path(row['directory']).is_dir() else str(Path.home()))
                # Detached creation can return just before its socket is ready.
                for attempt in range(40):
                    with self.session(name):
                        try:
                            ready = json.loads(self.c['call']('action', 'list-panes', '--json'))
                            if ready:
                                break
                            if attempt == 39:
                                raise ValueError('Workspace started without a usable layout')
                        except subprocess.SubprocessError:
                            if attempt == 39: raise
                    time.sleep(0.05)
            finally:
                if remote_start is not None:
                    self.prepare_restore(name)
        return name

    def repair_stopped_bridge(self, name, row, remote_start=None):
        """Replace only a sole held transport pane; never a running connection."""
        with self.session(name):
            panes = json.loads(self.c['call']('action', 'list-panes', '--json', '--all'))
            terminals = [p for p in panes if not p['is_plugin']]
            if len(terminals) != 1 or not terminals[0].get('is_held'):
                return False
            self.prepare_restore(name, remote_start=remote_start)
            layout = self.remotes.bridge_layout(row['remote_host'], row['remote_session'],
                                               *(remote_start or (None, None)))
            try:
                # No terminal retention: the sole original pane is already stopped.
                # Keep unrelated plugins, then remove only verified old bar plugins.
                self.c['call']('action', 'override-layout', '--layout-string', layout,
                               '--retain-existing-plugin-panes')
                bars = {'zellij:tab-bar', WORKSPACE_BAR_URL,
                        WORKSPACE_BAR_URL.replace('file:~', 'file:' + str(Path.home()), 1)}
                for pane in panes:
                    if pane['is_plugin'] and pane.get('plugin_url') in bars:
                        self.c['call']('action', 'close-pane', '--pane-id', 'plugin_' + str(pane['id']))
                # Native override can reuse an exited pane when its startup
                # command already matches. Retry only that verified held helper,
                # never write input to a running transport or another command.
                current = json.loads(self.c['call']('action', 'list-panes', '--json', '--all'))
                expected = str(self.c['CONFIG'] / 'bin/zellij-ws') + ' remote-attach ' + row['remote_host'] + ' ' + row['remote_session']
                for pane in current:
                    if (not pane['is_plugin'] and pane['id'] == terminals[0]['id'] and
                            pane.get('is_held') and pane.get('terminal_command') == expected):
                        self.c['call']('action', 'write', '--pane-id', 'terminal_' + str(pane['id']), '13')
            finally:
                if remote_start is not None:
                    self.prepare_restore(name)
            return True

    def touch(self, name):
        def update(data):
            if data.get('last') != name:
                data['previous'] = data.get('last')
                data['last'] = name
        self.tx(update)

    def switch(self, name, cwd=None, pane=None, tab=None):
        name = self.ensure(name, cwd)
        if not self.c['SESSION']:
            self.attach(name)
            return
        args = ['action', 'switch-session', name]
        if pane:
            args += ['--pane-id', self.c['pane_id'](pane)]
        if tab is not None:
            args += ['--tab-position', str(tab)]
        last = self.tx(lambda d: d.get('last'))
        source = last if name == self.c['SESSION'] and last else self.c['SESSION']
        def clients(session):
            with self.session(session):
                text = self.c['call']('action', 'list-clients')
            return {fields[0]: fields[1] for line in text.splitlines()[1:]
                    if len(fields := line.split(None, 2)) >= 2 and fields[0].isdigit()}
        waiter = None
        remote_target = self.tx(lambda data: bool(data.get('workspaces', {}).get(name, {}).get('remote_host')))
        if remote_target and source != name:
            own = 'terminal_' + os.environ.get('ZELLIJ_PANE_ID', '').removeprefix('terminal_')
            caller = next((client for client, pane in clients(source).items() if pane == own), None)
            if caller is not None:
                waiter = caller, len(clients(name))
        with self.session(source):
            self.c['call'](*args)
        if waiter:
            # CLI acknowledgement precedes client transfer. Closing the picker
            # immediately can race that transfer, especially after a nested TTY.
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if waiter[0] not in clients(source) and len(clients(name)) > waiter[1]:
                    break
                time.sleep(.05)
            else:
                raise ValueError('Remote workspace is ready, but client transfer did not finish; select it again')
        self.touch(name)
        print('Workspace:', name)

    def attach(self, name=None, scratch=False):
        if not name:
            data = self.tx(lambda d: dict(d))
            name = 'scratch' if scratch else data.get('last', 'home')
            if name == 'scratch' and not scratch:
                name = data.get('previous') or 'home'
        name = self.ensure(name)
        if not scratch:
            self.touch(name)
        # A new terminal must never inherit an enclosing multiplexer identity
        # or a short-lived sandbox's temporary directory.
        env = dict(os.environ, TMPDIR='/tmp')
        for key in ['TMUX', 'TMUX_PANE', 'ZELLIJ', 'ZELLIJ_SESSION_NAME', 'ZELLIJ_PANE_ID']:
            env.pop(key, None)
        self.remotes.close_connections()
        os.execvpe(self.c['BINARY'], [self.c['BINARY'], *self.options_for(name), 'attach', name], env)

    def attach_remote_existing(self, name):
        # A restored/stale Mosh carrier must not recreate a deleted workspace.
        self.validate_name(name)
        row = self.tx(lambda data: data.get('workspaces', {}).get(name))
        if row is None or row.get('remote_bridge'):
            raise ValueError('Remote workspace no longer exists; choose or create one explicitly.')
        return self.attach(name)

    def rows(self, local_only=False):
        data, found = self.discover()
        result = []
        for name, row in sorted(data.get('workspaces', {}).items(), key=lambda item: item[1]['order']):
            if not row.get('remote_bridge'):
                result.append({'session': name, **row, 'status': found.get(name, 'saved')})
        if not local_only:
            result.extend(self.remotes.collect('rows'))
        return result

    def inventory(self, attention=False, agents_only=False, local_only=False):
        rows = []
        for space in self.rows(local_only=True):
            if space['status'] != 'live':
                continue
            with self.session(space['session']):
                try:
                    local = self.c['inventory'](attention)
                except (ValueError, subprocess.SubprocessError):
                    # A session can disappear or return no JSON during a client switch.
                    continue
            for row in local:
                if agents_only and row['state'] == 'shell':
                    continue
                rows.append({'session': space['session'], 'workspace': space['name'],
                             'group': space['group'], **row})
        if not local_only:
            rows.extend(self.remotes.collect('inventory', attention=attention, agents_only=agents_only))
        return rows

    def remove_workspace(self, name, remote_identity=None):
        name = self.resolve(name)
        if name == self.c['SESSION']:
            raise ValueError('Switch to another workspace before removing this one.')
        data, found = self.discover()
        if name not in data.get('workspaces', {}):
            raise ValueError('Workspace no longer exists.')
        if remote_identity is not None and self.remote_remove_snapshot(name)['identity'] != remote_identity:
            raise ValueError('Workspace changed since confirmation; refresh the picker.')
        # Do not forget a workspace unless native removal succeeds. Interactive
        # removal confirms first; remote removal additionally checks clients.
        if name in found:
            self.cli('delete-session', '--force', name)
        digest = hashlib.sha256(name.encode()).hexdigest()
        self.path('layouts/' + digest + '.kdl').unlink(missing_ok=True)
        (self.c['STATE'] / (digest + '.json')).unlink(missing_ok=True)
        self.tx(lambda notes: notes.pop(name, None), 'tab-notes.json')
        def update(registry):
            spaces = registry.get('workspaces', {})
            spaces.pop(name, None)
            registry.get('next_slot', {}).pop(name, None)
            if registry.get('last') == name:
                fallback = self.c['SESSION'] if self.c['SESSION'] in spaces else next(
                    iter(sorted(spaces, key=lambda key: spaces[key]['order'])), None)
                if fallback:
                    registry['last'] = fallback
                else:
                    registry.pop('last', None)
            if registry.get('previous') in (name, registry.get('last')):
                registry.pop('previous', None)
        self.tx(update)

    def remote_remove_snapshot(self, name):
        """Fail closed on clients, aliases, transports, or unverified session identity."""
        self.validate_name(name)
        if name == self.c['SESSION']:
            raise ValueError('Switch to another workspace before removing this one.')
        data, found = self.discover()
        row = data.get('workspaces', {}).get(name)
        if row is None:
            raise ValueError('Workspace no longer exists; refresh the picker.')
        if row.get('remote_bridge'):
            raise ValueError('Remote transports cannot be deleted through this operation.')
        status = found.get(name, 'saved')
        files = []
        runtime = Path(os.environ.get('XDG_RUNTIME_DIR', '/tmp'))
        roots = {runtime / 'zellij', Path('/tmp') / ('zellij-' + str(os.getuid()))}
        sockets = [p for root in roots for p in root.glob('*/' + name)]
        if status == 'live':
            if len(sockets) != 1:
                raise ValueError('Cannot verify the live workspace socket; nothing was removed.')
            info = sockets[0].lstat()
            if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
                raise ValueError('Workspace socket is not owned by this account.')
            files.append((str(sockets[0]), info.st_dev, info.st_ino, info.st_ctime_ns))
            with self.session(name):
                output = self.c['call']('action', 'list-clients')
            lines = output.splitlines()
            if not lines or lines[0].split() != ['CLIENT_ID', 'ZELLIJ_PANE_ID', 'RUNNING_COMMAND']:
                raise ValueError('Cannot verify attached clients; nothing was removed.')
            if any(line.strip() for line in lines[1:]):
                raise ValueError('Workspace has attached clients. Detach every device first.')
        else:
            if sockets:
                raise ValueError('Workspace state is changing; refresh the picker.')
            digest = hashlib.sha256(name.encode()).hexdigest()
            cache = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache')))
            for path in [self.path('layouts/' + digest + '.kdl'),
                         cache / 'zellij/contract_version_1/session_info' / name / 'session-layout.kdl']:
                if path.exists() or path.is_symlink():
                    info = path.lstat()
                    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
                        raise ValueError('Saved workspace layout is not an owned regular file.')
                    files.append((str(path), info.st_dev, info.st_ino, info.st_ctime_ns))
        identity = hashlib.sha256(json.dumps([os.getuid(), str(Path.home()), name, row,
                                              status, files], sort_keys=True).encode()).hexdigest()
        return {'session': name, 'name': row.get('name', name), 'status': status, 'identity': identity}

    def remove_remote_workspace(self, name, identity):
        snapshot = self.remote_remove_snapshot(name)
        if not isinstance(identity, str) or snapshot['identity'] != identity:
            raise ValueError('Workspace changed since confirmation; refresh the picker.')
        original = self.tx(lambda data: dict(data['workspaces'][name]))
        try:
            self.remove_workspace(name, remote_identity=identity)
        except subprocess.CalledProcessError:
            # Zellij can stop a live session yet report failure deleting its
            # already-absent native cache. Only clean metadata if it is gone.
            data, found = self.discover()
            if name in found:
                raise
            if data.get('workspaces', {}).get(name) != original:
                raise ValueError('Workspace changed during removal; refresh the picker.')
            current = self.remote_remove_snapshot(name)
            if current['status'] != 'saved':
                raise ValueError('Workspace changed during removal; refresh the picker.')
            self.remove_workspace(name)
        return True

    @contextlib.contextmanager
    def removal_diagnostic_directory(self):
        root = self.root.absolute()
        if any(path.is_symlink() for path in (root, *root.parents)):
            raise ValueError('Unsafe diagnostic directory symlink')
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            info = os.fstat(directory)
            if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
                raise ValueError('Diagnostic directory must be owned and private')
            try:
                saved = os.stat('last-remote-removal-error.json', dir_fd=directory, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                if (not stat.S_ISREG(saved.st_mode) or saved.st_uid != os.getuid() or
                        stat.S_IMODE(saved.st_mode) != 0o600):
                    raise ValueError('Unsafe diagnostic file')
            yield directory
        finally:
            os.close(directory)

    def record_removal_error(self, host, name, stage, error):
        from remote import removal_error_text
        record = {'timestamp_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                  'host': removal_error_text(host)[:256], 'session': removal_error_text(name)[:256],
                  'stage': stage, 'error': removal_error_text(error)}
        with self.removal_diagnostic_directory() as directory:
            temporary = '.remote-removal-error-' + uuid.uuid4().hex
            try:
                fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=directory)
                with os.fdopen(fd, 'w') as output:
                    json.dump(record, output, ensure_ascii=False)
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(temporary, 'last-remote-removal-error.json',
                           src_dir_fd=directory, dst_dir_fd=directory)
            finally:
                try:
                    os.unlink(temporary, dir_fd=directory)
                except FileNotFoundError:
                    pass
        return self.root / 'last-remote-removal-error.json'

    def clear_removal_error(self):
        with self.removal_diagnostic_directory() as directory:
            try:
                os.unlink('last-remote-removal-error.json', dir_fd=directory)
            except FileNotFoundError:
                pass

    def show_remote_removal_error(self, host, name, stage, error):
        from modal import pick
        from remote import removal_error_text
        message = removal_error_text(error)
        width = max(24, min(72, shutil.get_terminal_size((80, 24)).columns - 8))
        try:
            path = self.record_removal_error(host, name, stage, error)
            capture = 'Details saved privately:\n' + textwrap.fill(str(path), width=width)
        except (OSError, ValueError):
            capture = 'Could not save diagnostics; the private path is unavailable.'
        header = ('Remote removal failed (' + stage + ')\n' +
                  textwrap.fill(host + ' / ' + name, width=width) + '\n\n' +
                  textwrap.fill(message, width=width, max_lines=6, placeholder=' …') +
                  '\n\n' + capture + '\nNo automatic retry was made.')
        pick([], header)

    def confirm_remove_remote(self, row):
        from modal import pick
        host, name = row['host'], row['session']
        stage = 'preflight'
        try:
            if self.remote_context() == {'host': host, 'session': name}:
                raise ValueError('Switch to another workspace before removing this one.')
            account = self.remotes.hosts()[host]
            snapshot = self.remotes.request(host, 'remove-preview', session=name)
            stage = 'confirmation'
            identity = host + ' (' + account + ') / ' + name
            header = ('Remove remote workspace "' + identity + '"?\n'
                      'Stops remote programs; deletes saved workspace state.\n'
                      'All devices must be detached. Pi conversations are kept.')
            selected, _ = pick(['cancel\tCancel', 'remove\tRemove ' + identity], header)
            if selected is None or selected.split('\t', 1)[0] != 'remove':
                return
            if self.remotes.hosts().get(host) != account:
                raise ValueError('Remote account changed; refresh the picker.')
            stage = 'delete'
            self.remotes.request(host, 'remove', session=name, identity=snapshot['identity'])
            try:
                self.clear_removal_error()
            except (OSError, ValueError):
                pass
        except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
            self.show_remote_removal_error(host, name, stage, error)

    def confirm_remove(self, row):
        from modal import pick
        if row.get('host'):
            self.confirm_remove_remote(row)
            return
        if row['session'] == self.c['SESSION']:
            pick([], 'Switch to another workspace before removing this one.')
            return
        label = self.c['clean'](row['name'], 80)
        identity = label if label == row['session'] else label + ' [' + row['session'] + ']'
        header = (f'Remove workspace "{identity}"?\n'
                  'Stops programs; deletes saved workspace state.\n'
                  'Pi conversations are kept.')
        selected, _ = pick(['cancel\tCancel', 'remove\tRemove workspace "' + label + '"'], header)
        if selected is None or selected.split('\t', 1)[0] != 'remove':
            return
        try:
            self.remove_workspace(row['session'])
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            pick([], 'Workspace removal failed: ' + self.c['clean'](error, 200))

    def pick(self, mode='workspaces'):
        from agent_viewer import ARCHIVE_ICON, PI_ICON, TERMINAL_ICON
        if mode == 'workspaces':
            rows = self.rows()
            lines = [f'{i}\t{TERMINAL_ICON if r["status"] == "live" else ARCHIVE_ICON}  {r["group"] + "/" if r["group"] else ""}{r["name"]}{" · " + r["host"] if r.get("host") else ""} · {r["status"]}' for i, r in enumerate(rows)]
            header = 'Enter switch · Alt+R rename · Alt+M group\nAlt+D remove (confirmation)'
        else:
            rows = self.inventory(mode == 'attention', mode == 'fleet')
            own = 'terminal_' + os.environ.get('ZELLIJ_PANE_ID', '').removeprefix('terminal_')
            rows = [r for r in rows if not (not r.get('host') and r['session'] == self.c['SESSION'] and r['pane'] == own)]
            # Agent identity comes from owned Pi metadata, never pane-title guessing.
            lines = [f'{i}\t{PI_ICON if r["state"] != "shell" else TERMINAL_ICON}  {r["group"] + "/" if r["group"] else ""}{r["workspace"]}{" · " + r["host"] if r.get("host") else ""} · {r["tab"]} · {r["state"]} · {r["note"]}' for i, r in enumerate(rows)]
            header = ('Enter focus · Alt+S snooze until next activity' if mode == 'attention' else
                      'Enter focus · Alt+S snooze/restore · 󰒲 = snoozed' if mode == 'fleet' else
                      f'Enter focus · {PI_ICON} Pi · {TERMINAL_ICON} terminal')
        if self.remotes.errors:
            header += '\n' + ' · '.join(self.remotes.errors)
        from modal import pick
        if not rows:
            message = {'attention': 'No agents need attention.',
                       'fleet': 'No Pi agents are running.',
                       'tree': 'No task panes are available.',
                       'workspaces': 'No workspaces are available.'}[mode]
            pick([], message + ('\n' + ' · '.join(self.remotes.errors) if self.remotes.errors else ''))
            return
        if mode in ('attention', 'fleet'):
            from agent_viewer import picker_data
            with picker_data(rows, self.c) as (lines, preview):
                selected, action = pick(lines, header, extra=['s'], preview=preview, ansi=True, header_lines=1)
        else:
            selected, action = pick(lines, header, extra=['r', 'm', 'd'] if mode == 'workspaces' else [])
        if selected is None:
            return
        row = rows[int(selected.split('\t', 1)[0])]
        if mode in ('attention', 'fleet') and action == 's':
            if row.get('host'):
                self.remotes.request(row['host'], 'snooze', session=row['session'], pane=row['pane'], activity=row['activity'])
            else:
                with self.session(row['session']):
                    self.c['snooze'](row['pane'], row['activity'])
            # Rebuild in place; never focus, stop, or pause the selected agent.
            self.pick(mode)
        elif mode == 'workspaces' and action == 'd':
            self.confirm_remove(row)
            self.pick(mode)
        elif mode == 'workspaces' and action in ('r', 'm'):
            value = input('New workspace label: ' if action == 'r' else 'Group (empty clears): ').strip()
            if action == 'r' and not value:
                return
            def update(data):
                value_clean = self.c['clean'](value, 80)
                if action == 'r' and any(key != row['session'] and item.get('name') == value_clean for key, item in data['workspaces'].items()):
                    raise ValueError('Another workspace already has that label')
                data['workspaces'][row['session']]['name' if action == 'r' else 'group'] = value_clean
            if row.get('host'):
                self.remotes.request(row['host'], 'label', session=row['session'], field='name' if action == 'r' else 'group', value=value)
            else:
                self.tx(update)
            self.pick(mode)
        else:
            if row.get('host'):
                self.remotes.switch(row)
            else:
                self.switch(row['session'], pane=row.get('pane'))

    def popup(self, mode):
        helper = str(self.c['CONFIG'] / 'bin/zellij-ws')
        title = {'workspaces': 'Workspaces', 'tree': 'Tasks', 'attention': 'Attention', 'fleet': 'Agents'}.get(mode, mode)
        print(self.c['call']('run', '--floating', '--close-on-exit',
                             '--x', '15%', '--y', '20%', '--width', '70%', '--height', '60%',
                             '--name', title, '--', helper, 'pick', mode))

    def tab_note(self, pane):
        live = self.c['panes']()
        p = next((p for p in live if 'terminal_' + str(p['id']) == pane), None)
        if p is None:
            return ''
        data = self.tx(lambda d: dict(d), 'tab-notes.json')
        return data.get(self.c['SESSION'], {}).get(p.get('tab_name', ''), '')

    def window_note(self, text=None, target=None):
        if self.remote_context():
            result = self.remote_task('note', text=text, pane=target)
            if text is None: print(result)
            return result
        own = self.c['pane_id'](target) if target else self.c['own_pane']()
        live = self.c['panes']()
        p = next((p for p in live if 'terminal_' + str(p['id']) == own), None)
        if p is None:
            raise ValueError('Target pane is unavailable')
        old_name = p.get('tab_name', '')
        if text is None:
            print(re.sub(r'^\d+:', '', old_name))
            return
        label = self.c['clean'](text, 50) or 'shell'
        slot = re.match(r'^(\d+):', old_name)
        name = (slot.group(1) + ':' if slot else '') + label
        self.c['call']('action', 'rename-tab', '--tab-id', str(p['tab_id']), name)
        def update(data):
            notes = data.setdefault(self.c['SESSION'], {})
            notes.pop(old_name, None)
            notes[name] = label
        self.tx(update, 'tab-notes.json')
        for pane in live:
            if pane.get('tab_id') == p.get('tab_id'):
                self.c['note'](label, 'terminal_' + str(pane['id']))
        self.save()

    def prompt_note(self, clear=False):
        text = '' if clear else input('Task name (empty resets to shell): ')
        self.window_note(text)

    def new_tab(self, command=None, cwd=None, name='shell', focus=True):
        if self.remote_context():
            return self.remote_task('new-tab', argv=command, cwd=cwd, name=name, focus=focus)
        label = name
        name = self.c['SESSION']
        with self.session(name):
            tabs = json.loads(self.c['call']('action', 'list-tabs', '--json', '--all'))
            occupied = [int(m.group(1)) for t in tabs for m in [re.match(r'^(\d+):', t.get('name', ''))] if m]
            def advance(data):
                counters = data.setdefault('next_slot', {})
                slot = max(counters.get(name, 1), max(occupied, default=0) + 1)
                counters[name] = slot + 1
                return slot
            slot = self.tx(advance)
            layout = ['layout {', tab_bar('    ').rstrip()]
            if command:
                layout += ['    pane command=' + quoted(command[0]) + ' {',
                           '        args ' + ' '.join(quoted(arg) for arg in command[1:]) if len(command) > 1 else '',
                           '    }']
            else:
                layout.append('    pane')
            layout.append('}')
            args = ['action', 'new-tab', '--layout-string', '\n'.join(layout),
                    '--name=' + str(slot) + ':' + self.c['clean'](label, 50)]
            if cwd:
                args += ['--cwd', cwd]
            if not focus:
                args.append('--no-focus')
            result = self.c['call'](*args)
            task_name = self.c['clean'](label, 50)
            self.tx(lambda data: data.setdefault(name, {}).update({str(slot) + ':' + task_name: task_name}), 'tab-notes.json')
        self.save()
        return result

    def slot(self, slot):
        if self.remote_context():
            return self.remote_task('slot', number=slot)
        tabs = json.loads(self.c['call']('action', 'list-tabs', '--json', '--all'))
        matches = [t for t in tabs if re.match(r'^' + str(slot) + r':', t.get('name', ''))]
        if not matches:
            raise ValueError('No tab in that stable slot')
        self.c['call']('action', 'go-to-tab-by-id', str(matches[0]['tab_id']))

    def project(self, new_tab=False):
        with self.remotes.connection_scope():
            return self._project(new_tab)

    def _project(self, new_tab=False):
        from directory import pick_directory, pick_machine_directory
        context = self.remote_context()
        if self.remotes.hosts():
            chosen = pick_machine_directory(self, context['host'] if new_tab and context else None)
            if chosen is None: return
            host, path = chosen
            target = Path(path)
        else:
            current = Path.home() / 'dev'
            if not current.is_dir(): current = Path.home()
            target = pick_directory(self.c['CONFIG'] / 'directory-picker.lfrc', current)
            if target is None: return
            host = None
        if new_tab and host == (context['host'] if context else None):
            self.new_tab(cwd=str(target))
        else:
            name = input(f'Workspace name [{target.name}]: ').strip() or target.name
            if host:
                self.validate_name(name)
                self.remotes.switch({'host': host, 'session': name, 'directory': str(target)})
            else:
                self.switch(name, str(target))

    def agent_path(self, token):
        if not re.fullmatch(r'[0-9a-f]{32}', token):
            raise ValueError('Invalid agent restoration token')
        return self.path('agents/' + token + '.json')

    def load_agent(self, token):
        path = self.agent_path(token)
        return json.loads(path.read_text()) if path.exists() else {}

    def save_agent(self, row):
        if not row.get('token') or not row.get('session_file'):
            return
        payload = {k: row.get(k) for k in ['session_file', 'note', 'label', 'token']}
        def update(data):
            if data.get('session_file') and data['session_file'] != payload['session_file']:
                raise ValueError('Pi restoration token belongs to a different session; refusing to redirect it')
            data.update(payload)
        self.c['transact'](update, self.agent_path(row['token']))

    def restoration_titles(self, row):
        label = self.c['clean'](row.get('note') or row.get('label') or 'pi', 70)
        suffix = ' · p' + row.get('pane', '').removeprefix('terminal_')
        # Native serialization may lag the last rename or clean shutdown.
        return {self.c['title'](row), label + suffix,
                *[f'[{mark}] {label}{suffix}' for mark in [*self.c['MARKS'].values(), 'EXIT']]}

    def add_restoration_title(self, agents, name, row):
        if name in agents and agents[name]['token'] != row['token']:
            raise ValueError('Ambiguous Pi restoration title; refusing unsafe restore')
        agents[name] = row

    def save(self):
        if self.remote_context():
            return self.remote_task('save')
        if not self.c['SESSION']:
            return
        name, _ = self.register(self.c['SESSION'], os.getcwd())
        data = self.c['transact'](lambda d: {k: dict(v) for k,v in d.items()})
        rows = self.c['panes']()
        agents = {}
        for p in rows:
            row = data.get('terminal_' + str(p['id']), {})
            if row.get('token') and row.get('session_file'):
                self.save_agent(row)
                self.add_restoration_title(agents, p['title'], row)
                for alias in self.restoration_titles(row):
                    self.add_restoration_title(agents, alias, row)
        text = self.c['call']('action', 'dump-layout')
        patched, _ = rewrite_layout(text, agents, str(self.c['CONFIG'] / 'bin/zellij-agent'))
        path = self.path('layouts/' + hashlib.sha256(name.encode()).hexdigest() + '.kdl')
        self.atomic_text(path, patched)

    def atomic_text(self, path, text):
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        temp = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
        try:
            with os.fdopen(os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as out:
                out.write(text)
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)

    def prepare_restore(self, name, remote_start=None):
        # Patch the newest native layout, not an older snapshot. Preserve its original.
        cache = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'zellij/contract_version_1/session_info' / name / 'session-layout.kdl'
        row = self.tx(lambda data: dict(data.get('workspaces', {}).get(name, {})))
        if row.get('remote_bridge'):
            # The carrier has no user terminals to restore. Reconstruct its one
            # borderless transport from trusted metadata, not Mosh argv/UDP state.
            host, target = row.get('remote_host'), row.get('remote_session')
            if not isinstance(host, str) or not isinstance(target, str):
                raise ValueError('Remote bridge is missing its exact host/workspace identity')
            startup = self.remotes.bridge_layout(host, target, *(remote_start or (None, None)))
            private = self.path('layouts/' + hashlib.sha256(name.encode()).hexdigest() + '.kdl')
            for path in [private, cache]:
                if path == cache and not path.exists(): continue
                original = path.read_text() if path.exists() else None
                if original == startup: continue
                if original is not None:
                    backup = self.path('restore-backups/' + hashlib.sha256(name.encode()).hexdigest() +
                                       '-remote-' + ('native' if path == cache else 'private') + '-' + str(time.time_ns()) + '.kdl')
                    self.atomic_text(backup, original)
                self.atomic_text(path, startup)
            return
        if remote_start is not None:
            raise ValueError('SSH startup controls require a managed remote bridge')
        if not cache.exists(): return
        with self.session(name):
            data = self.c['transact'](lambda d: {k: dict(v) for k,v in d.items()})
        agents = {}
        for row in data.values():
            if row.get('token') and row.get('session_file'):
                self.save_agent(row)
                for alias in self.restoration_titles(row):
                    self.add_restoration_title(agents, alias, row)
        text = cache.read_text()
        patched, matched = rewrite_layout(text, agents, str(self.c['CONFIG'] / 'bin/zellij-agent'))
        if patched != text:
            backup = self.path('restore-backups/' + hashlib.sha256(name.encode()).hexdigest() + '-' + str(time.time_ns()) + '.kdl')
            self.atomic_text(backup, text)
            self.atomic_text(cache, patched)

    def import_tmux(self, path):
        already = self.tx(lambda d: bool(d.get('imported_tmux')))
        spaces = {}
        for line in Path(path).read_text().splitlines():
            fields = line.split('\t')
            if len(fields) != 7: raise ValueError('Invalid tmux snapshot row')
            name, group, index, title, cwd, note, pi_file = fields
            self.validate_name(name)
            if not index.isdigit(): raise ValueError('Invalid window index')
            spaces.setdefault(name, []).append((int(index), title, cwd, note, pi_file, group))
        for name, windows in spaces.items():
            if already:
                for index, title, _, note, _, _ in windows:
                    if note:
                        tab_name = f'{index}:{title}'
                        self.tx(lambda data: data.setdefault(name, {}).setdefault(tab_name, note), 'tab-notes.json')
                continue
            self.register(name, windows[0][2] if Path(windows[0][2]).is_dir() else str(Path.home()), windows[0][5])
            lines = ['layout {']
            for index, title, cwd, note, pi_file, _ in sorted(windows):
                cwd = cwd if Path(cwd).is_dir() else str(Path.home())
                lines += ['    tab name=' + quoted(f'{index}:{title}') + ' {', '        pane cwd=' + quoted(cwd) + ' name=' + quoted(note or title) + (' command=' + quoted(str(self.c['CONFIG'] / 'bin/zellij-agent')) + ' {' if pi_file else '')]
                if pi_file:
                    token = uuid.uuid4().hex
                    self.save_agent({'token': token, 'session_file': pi_file, 'note': note, 'label': title})
                    lines += ['            args ' + quoted(token), '            start_suspended false', '        }']
                if note:
                    tab_name = f'{index}:{title}'
                    self.tx(lambda data: data.setdefault(name, {}).update({tab_name: note}), 'tab-notes.json')
                lines.append('    }')
            lines.append('}')
            self.atomic_text(self.path('layouts/' + hashlib.sha256(name.encode()).hexdigest() + '.kdl'), with_top_tabs('\n'.join(lines) + '\n'))
        self.tx(lambda d: d.update(imported_tmux=True))
        print('Existing workspace import retained; missing task notes seeded.' if already else
              'Imported workspace names, slots, directories, notes and exact Pi resume links; no processes moved.')
