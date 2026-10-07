"""Bounded private agent rows and an ephemeral, viewport-only preview."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata

# Nerd Font Material Design glyphs; labels remain readable alongside each icon.
STATUS = {'working': ('\U000f0493', 'WORK', 110),  # md-cog
          'asking': ('\U000f0817', 'ASK', 179),    # md-comment_question
          'done': ('\U000f05e0', 'DONE', 150),     # md-check_circle
          'error': ('\U000f0028', 'ERR', 174),     # md-alert_circle
          'idle': ('\U000f03e5', 'IDLE', 245),     # md-pause_circle
          'exited': ('\U000f0159', 'EXIT', 245)}   # md-close_circle
TERMINAL_ICON = '\U000f018d'  # md-console
ARCHIVE_ICON = '\U000f003c'   # md-archive
PI_ICON = '\U000f06a9'        # md-robot


def text(value, limit):
    value = ''.join(' ' if unicodedata.category(c) in ('Cc', 'Cf', 'Cs', 'Cn') else c for c in str(value))
    value = re.sub(r'\s+', ' ', value).strip()
    return value if len(value) <= limit else value[:limit - 1] + '…'


def updated(value, now=None):
    if not isinstance(value, (int, float)) or value <= 0:
        return 'updated —'
    age = max(0, int((time.time() if now is None else now) - value))
    relative = f'{age}s' if age < 60 else f'{age // 60}m' if age < 3600 else f'{age // 3600}h' if age < 86400 else f'{age // 86400}d'
    return 'updated ' + relative + ' ago'


def cell(value, width):
    """Truncate/pad by terminal cells, including wide and combining characters."""
    value = text(value, 1000)
    def cells(s):
        return sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1 for c in s)
    if cells(value) > width:
        clipped, used = '', 0
        for c in value:
            size = cells(c)
            if used + size > max(0, width - 1):
                break
            clipped += c
            used += size
        value = clipped + ('…' if width else '')
    return value + ' ' * max(0, width - cells(value))


def columns(width):
    # Collapse the workspace column on narrow terminals, retaining the essentials.
    session = min(34, max(12, width // 4))
    workspace = min(20, width // 6) if width >= 90 else 0
    updated_width = 8
    gaps = 8 if workspace else 6
    prompt = max(4, width - 7 - session - workspace - updated_width - gaps)
    return [('STATUS', 7), ('SESSION', session), *([('WORKSPACE', workspace)] if workspace else []),
            ('LAST PROMPT', prompt), ('UPDATED', updated_width)]


def line(index, row, width):
    icon, label, color = STATUS.get(row['state'], STATUS['idle'])
    if row.get('snoozed'):
        icon, color = '\U000f04b2', 245  # nf-md-sleep
    session_name = row.get('session_name') or 'pi'
    name = row.get('note') or session_name
    # Prefer the actual Pi name to a generic shell tab.
    if name in ('shell', 'pi'):
        name = session_name
    elif session_name not in ('pi', name):
        name += ' / ' + session_name
    if row.get('host'):
        name = row['host'] + ' · ' + name
    values = {'STATUS': f'{icon} {label}', 'SESSION': name,
              'WORKSPACE': (row.get('group', '') + '/' if row.get('group') else '') + row['workspace'],
              'LAST PROMPT': row.get('last_prompt') or 'No prompt captured',
              'UPDATED': updated(row.get('updated')).removeprefix('updated ')}
    parts = []
    for heading, size in columns(width):
        value = cell(values[heading], size)
        if heading == 'STATUS':
            value = f'\033[38;5;{color}m{value}\033[0m'
        parts.append(value)
    return str(index) + '\t' + '  '.join(parts)


def table(rows, width):
    header = '-\t' + '  '.join(cell(heading, size) for heading, size in columns(width))
    return [header, *[line(i, row, width) for i, row in enumerate(rows)]]


@contextlib.contextmanager
def picker_data(rows, core):
    size = shutil.get_terminal_size((80, 24))
    lines = table(rows, size.columns - 6)
    if size.columns < 90 or size.lines < 22:
        yield lines, None
        return
    with tempfile.TemporaryDirectory(prefix='zellij-agent-preview-', dir='/tmp') as directory:
        path = Path(directory) / 'rows.json'
        path.write_text(json.dumps({'rows': rows, 'binary': core['BINARY'],
                                   'options': core['OPTIONS'], 'state': str(core['STATE'])}))
        path.chmod(0o600)
        command = ' '.join(shlex.quote(s) for s in [sys.executable, __file__, str(path)]) + ' {1}'
        yield lines, command


def preview(path, index):
    data = json.loads(Path(path).read_text())
    row = data['rows'][int(index)]
    if row.get('host'):
        from remote import Remotes
        class Manager:
            c = {'CONFIG': Path(__file__).resolve().parent.parent, 'clean': text}
        screen = Remotes(Manager()).request(row['host'], 'preview', session=row['session'], pane=row['pane'], activity=row['activity'])
        height = max(1, min(12, int(os.environ.get('FZF_PREVIEW_LINES', '10')) - 1))
        width = max(1, int(os.environ.get('FZF_PREVIEW_COLUMNS', '80')))
        print('Current Pi screen · ' + text(row['host'] + ' / ' + row['workspace'], 60))
        for screen_line in screen.splitlines()[-height:]:
            print(''.join(c for c in screen_line if not unicodedata.category(c).startswith('C'))[:width])
        return
    # Recheck ownership: a reused pane ID must never preview a replacement shell.
    state_path = Path(data['state']) / (hashlib.sha256(row['session'].encode()).hexdigest() + '.json')
    state = json.loads(state_path.read_text()).get(row['pane'], {})
    pid = int(state.get('pid', 0))
    stamp = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19]
    if not state.get('owner') or stamp != state.get('stamp'):
        return
    print('Current Pi screen · ' + text(row['workspace'], 60))
    result = subprocess.run([data['binary'], *data['options'], '-s', row['session'],
                             'action', 'dump-screen', '--pane-id', row['pane']],
                            capture_output=True, text=True, timeout=3,
                            env=dict(os.environ, TMPDIR='/tmp'))
    if result.returncode:
        print('Preview unavailable')
        return
    height = max(1, min(12, int(os.environ.get('FZF_PREVIEW_LINES', '10')) - 1))
    width = max(1, int(os.environ.get('FZF_PREVIEW_COLUMNS', '80')))
    for screen_line in result.stdout.splitlines()[-height:]:
        print(''.join(c for c in screen_line if not unicodedata.category(c).startswith('C'))[:width])


if __name__ == '__main__':
    try:
        preview(sys.argv[1], sys.argv[2])
    except (OSError, ValueError, KeyError, IndexError, subprocess.SubprocessError):
        print('Preview unavailable')
