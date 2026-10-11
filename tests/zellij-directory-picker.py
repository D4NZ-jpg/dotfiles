"""Actual lf keyboard selection in isolated PTYs; no workspaces are opened."""
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import struct
import subprocess
import tempfile
import termios
import time

config_root = Path(__file__).resolve().parents[1] / 'dot_config/zellij'
cases = [('Enter selected', [b'\r'], 'a project'),
         ('j/k motion', [b'j', b'k', b'j', b'\r'], 'b-project'),
         ('h/l browse', [b'l', b'h', b'\r'], 'a project'),
         ('Search', [b'/b-project\r', b'\r'], 'b-project'),
         ('Current directory', [b'.'], '.'),
         ('Empty directory', [b'l', b'l', b'\r'], 'a project/child'),
         ('q cancel', [b'q'], None),
         ('Esc cancel', [b'\x1b'], None),
         ('New folder', [b'n', b'fresh idea\r'], 'fresh idea'),
         ('New folder in browsed directory', [b'l', b'n', b'nested\r'], 'a project/nested'),
         ('New folder back to browsing', [b'n', (b'\r', 1.5), b'j', b'\r'], 'b-project'),
         ('New folder existing name', [b'n', b'b-project\r', b'other\r'], 'other'),
         ('New folder rejects paths', [b'n', b'x/y\r', b'..\r', b'ok\r'], 'ok')]
for label, inputs, expected in cases:
    with tempfile.TemporaryDirectory(prefix='zellij-lf-test-', dir='/tmp') as directory:
        tmp = Path(directory)
        start = tmp / 'browse'
        (start / 'a project' / 'child').mkdir(parents=True)
        (start / 'b-project').mkdir()
        (start / '0-file-not-a-directory').write_text('fixture')
        result = tmp / 'result.json'
        code = (f'import sys,json;from pathlib import Path;sys.path.insert(0,{str(config_root / "bin")!r});'
                'import directory;original=directory.subprocess.run;'
                f'directory.subprocess.run=lambda args,**kwargs: original(args+["-log",{str(tmp / "lf.log")!r}],**kwargs);'
                'from directory import pick_directory;'
                f'target=pick_directory(Path({str(config_root / "directory-picker.lfrc")!r}),Path({str(start)!r}));'
                f'Path({str(result)!r}).write_text(json.dumps(str(target) if target else None))')
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 25, 100, 0, 0))
        def terminal():
            os.setsid()
            fcntl.ioctl(0, termios.TIOCSCTTY, 0)
        proc = subprocess.Popen(['python', '-c', code], stdin=slave, stdout=slave, stderr=slave,
                                env=dict(os.environ, TERM='xterm-kitty', PYTHONDONTWRITEBYTECODE='1'),
                                preexec_fn=terminal)
        os.close(slave)
        captured = bytearray()
        def drain(seconds):
            end = time.monotonic() + seconds
            while time.monotonic() < end:
                if select.select([master], [], [], 0.05)[0]:
                    try: captured.extend(os.read(master, 65536))
                    except OSError: break
        try:
            drain(1.5)
            assert proc.poll() is None, 'lf exited before input'
            for keys in inputs:
                # (keys, seconds) waits longer, e.g. while lf reopens after the name prompt.
                keys, wait = keys if isinstance(keys, tuple) else (keys, 0.6 if label.startswith('New folder') else 0.2)
                os.write(master, keys)
                drain(wait)
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and not result.exists():
                drain(0.1)
            proc.wait(timeout=3)
            actual = json.loads(result.read_text())
            wanted = str((start / expected).resolve()) if expected is not None else None
            log = (tmp / 'lf.log').read_text()
            assert 'error:' not in log, log[-3000:]
            assert actual == wanted, (label, actual, wanted, log[-3000:])
            folders = sorted(p.relative_to(start).as_posix() for p in start.rglob('*') if p.is_dir())
            created = {'New folder': ['fresh idea'], 'New folder in browsed directory': ['a project/nested'],
                       'New folder existing name': ['other'], 'New folder rejects paths': ['ok']}.get(label, [])
            assert folders == sorted(['a project', 'a project/child', 'b-project', *created]), (label, folders)
            print(label + ': correct lf directory result')
        finally:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=3)
            os.close(master)
