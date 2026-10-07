#!/usr/bin/env python3
"""Grant only the two UI permissions to this exact owner-controlled plugin."""
import argparse
import json
import os
from pathlib import Path
import re
import stat
import time


def grant(cache, plugin, backup_root):
    plugin = Path(plugin).absolute()
    info = plugin.lstat()
    if plugin.name != 'workspace-bar-0.45.1.wasm' or not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
        raise ValueError('Expected the owned workspace-bar plugin, not another path or symlink')
    cache = Path(cache)
    if cache.is_symlink():
        raise ValueError('Permission cache cannot be a symlink')
    original = cache.read_text() if cache.exists() else ''
    key = json.dumps(str(plugin))
    pattern = re.compile(r'^' + re.escape(key) + r'\s*\{[^{}]*\}', re.M)
    entry = key + ' {\n    ReadApplicationState\n    ChangeApplicationState\n}'
    matches = list(pattern.finditer(original))
    if len(matches) > 1:
        raise ValueError('Duplicate workspace-bar permission entries; refusing to rewrite cache')
    if key in original and not matches:
        raise ValueError('Unexpected workspace-bar permission entry; refusing to rewrite cache')
    if matches:
        modified = pattern.sub(lambda _: entry, original)
    else:
        modified = original + ('\n' if original and not original.endswith('\n') else '') + entry + '\n'
    if modified == original:
        return False
    if cache.exists():
        backup = Path(backup_root) / ('permissions-before-workspace-bar-' + str(time.time_ns()) + '.kdl')
        backup.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with os.fdopen(os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as output:
            output.write(original)
    cache.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = cache.with_name(cache.name + '.workspace-bar-' + str(os.getpid()))
    try:
        with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as output:
            output.write(modified)
        os.replace(temporary, cache)
    finally:
        temporary.unlink(missing_ok=True)
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('plugin')
    parser.add_argument('--cache', default=str(Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'zellij/permissions.kdl'))
    parser.add_argument('--backups', default=str(Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'dotfiles-review'))
    args = parser.parse_args()
    grant(args.cache, args.plugin, args.backups)
