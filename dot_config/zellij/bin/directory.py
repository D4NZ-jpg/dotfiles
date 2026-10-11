"""Choose a directory using an isolated lf client and a private result file."""
import json
import os
import re
import shlex
import time
import uuid
from pathlib import Path
import shutil
import subprocess
import tempfile


def create_folder(parent, ask=input, say=print):
    """Ask for one new folder name inside parent. Returns the new path, or None to go back."""
    say('\nNew folder in ' + str(parent))
    while True:
        try:
            name = ask('Name (empty to go back): ').strip()
        except (EOFError, KeyboardInterrupt):
            say('')
            return None
        if not name:
            return None
        if name in ('.', '..') or '/' in name or '\0' in name or len(name.encode()) > 255:
            say('Use a single folder name without "/".')
            continue
        target = Path(parent) / name
        try:
            target.mkdir()
        except FileExistsError:
            say(name + ' already exists.')
            continue
        except OSError as error:
            say('Could not create folder: ' + (error.strerror or str(error)))
            continue
        return target


def pick_directory(config, start, allow_machine=False, machine_label='Local'):
    binary = shutil.which('lf')
    if not binary:
        raise ValueError('Directory browsing requires lf')
    start = Path(start)
    while True:
        selected = _browse(binary, config, start, machine_label)
        if selected is None:
            return None
        if selected.startswith('@new\n'):
            parent = Path(selected.split('\n', 1)[1]).resolve()
            if not parent.is_dir():
                raise ValueError('Directory no longer exists')
            created = create_folder(parent)
            if created is None:
                start = parent  # Back to browsing where the user was.
                continue
            return created.resolve()
        if selected == '@machine':
            return '@machine' if allow_machine else None
        target = Path(selected).resolve()
        if not target.is_dir():
            raise ValueError('Selected directory no longer exists')
        return target


def _browse(binary, config, start, machine_label):
    with tempfile.TemporaryDirectory(prefix='zellij-directory-picker-', dir='/tmp') as directory:
        result = Path(directory) / 'selected-directory'
        env = dict(os.environ, TMPDIR='/tmp', ZELLIJ_WS_DIRECTORY_RESULT=str(result),
                   XDG_DATA_HOME=str(Path(directory) / 'data'),
                   XDG_CACHE_HOME=str(Path(directory) / 'cache'))
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,99}', machine_label):
            raise ValueError('Invalid directory picker machine label')
        shared_config = Path(directory) / 'picker.lfrc'
        shared_config.write_text(Path(config).read_text().replace('set promptfmt "Local:', 'set promptfmt "' + machine_label + ':'))
        shared_config.chmod(0o600)
        completed = subprocess.run([binary, '-single', '-config', str(shared_config)], cwd=str(start), env=env)
        if completed.returncode not in (0, 130):
            raise ValueError(f'lf directory picker exited with status {completed.returncode}')
        if not result.exists():
            return None
        selected = result.read_text().removesuffix('\n')
        return selected or None


def result_path(manager, token):
    if not re.fullmatch(r'[0-9a-f]{32}', token):
        raise ValueError('Invalid directory selection token')
    return manager.path('directory-results/' + token + '.json')


def serve_directory(manager, token, start=None, label='Remote'):
    path = result_path(manager, token)
    # A dropped SSH connection may leave an unconsumed private result. Only
    # expired UUID-named results in this dedicated directory are pruned.
    if path.parent.exists():
        for old in path.parent.glob('*.json'):
            if re.fullmatch(r'[0-9a-f]{32}\.json', old.name) and old.stat().st_mtime < time.time() - 3600:
                old.unlink(missing_ok=True)
    current = Path(start).expanduser().resolve() if start else Path.home() / 'dev'
    if not start and not current.is_dir(): current = Path.home()
    if not current.is_dir(): raise ValueError('Directory does not exist')
    selected = pick_directory(manager.c['CONFIG'] / 'directory-picker.lfrc', current,
                              allow_machine=True, machine_label=label)
    payload = {'kind': 'cancel'} if selected is None else {'kind': 'machine'} if selected == '@machine' else {'kind': 'selected', 'directory': str(selected)}
    manager.atomic_text(path, json.dumps(payload))


def take_directory_result(manager, token):
    path = result_path(manager, token)
    if not path.exists(): return {'kind': 'cancel'}
    try: return json.loads(path.read_text())
    finally: path.unlink(missing_ok=True)


def pick_remote_directory(manager, host, start=None):
    from remote import REMOTE_HELPER
    target = manager.remotes.hosts()[host]
    token = uuid.uuid4().hex
    args = ['remote-directory', token, '--label', host]
    if start is not None: args += ['--start', start]
    # SSH supplies a real remote TTY: lf runs against the remote filesystem,
    # using the identical dedicated config, with no mounts or persistent server.
    try:
        completed = subprocess.run(['ssh', '-tt', '-q', *manager.remotes.ssh_options(host), target,
                                    REMOTE_HELPER + ' ' + shlex.join(args)])
    finally:
        result = manager.remotes.request(host, 'directory-result', token=token)
    if completed.returncode not in (0, 130):
        raise ValueError('Remote directory browser failed on ' + host)
    if result['kind'] == 'machine': return '@machine'
    if result['kind'] == 'selected': return result['directory']
    if result['kind'] != 'cancel': raise ValueError('Invalid remote directory selection')
    return None


def pick_machine_directory(manager, initial_host=None):
    """Local first; Alt+M switches the filesystem without adding a creation step."""
    from modal import pick
    host = initial_host
    local = Path.home() / 'dev'
    if not local.is_dir(): local = Path.home()
    locations = {None: str(local)}
    while True:
        if host is None:
            target = pick_directory(manager.c['CONFIG'] / 'directory-picker.lfrc', Path(locations[None]), allow_machine=True)
            if target != '@machine':
                return (None, str(target)) if target is not None else None
        else:
            target = pick_remote_directory(manager, host, locations.get(host))
            if target != '@machine':
                return (host, target) if target is not None else None
        hosts = list(manager.remotes.hosts())
        lines = ['local\tLocal (default)', *[str(i) + '\t' + name for i, name in enumerate(hosts)]]
        selected, _ = pick(lines, 'Workspace machine · directory and tasks run here')
        if selected is None: return None
        key = selected.split('\t', 1)[0]
        host = None if key == 'local' else hosts[int(key)]
