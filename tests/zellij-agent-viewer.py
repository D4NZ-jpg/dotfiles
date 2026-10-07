"""Private agent viewer formatting, preview targeting and responsiveness."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'dot_config/zellij/bin'))
import agent_viewer as viewer

class ViewerTests(unittest.TestCase):
    def row(self, **extra):
        return dict(workspace='work space', session='session;literal', pane='terminal_7',
                    tab='2:task', note='task', state='asking', last_prompt='Fix the picker', updated=100, **extra)
    def test_status_first(self):
        value = viewer.line(0, self.row(), 110)
        self.assertTrue(value.startswith('0\t\033[38;5;179m\U000f0817 ASK'))
        self.assertIn('Fix the picker', value)
    def test_table_columns_aligned_and_no_separators(self):
        rows = [self.row(), dict(self.row(), note='非常に長いタスクの名前', last_prompt='SECOND_PROMPT')]
        rendered = viewer.table(rows, 110)
        import re
        plain = [re.sub(r'\x1b\[[0-9;]*m', '', s.split('\t', 1)[1]) for s in rendered]
        self.assertNotIn(' · ', ''.join(plain))
        self.assertIn('WORKSPACE', plain[0])
        self.assertEqual(plain[0].index('LAST PROMPT'), plain[1].index('Fix the picker'))
        # A wide session occupies the same terminal-cell width as an ASCII session.
        self.assertEqual(viewer.cell('界', 4), '界  ')
        self.assertEqual(viewer.cell('e\u0301', 4), 'e\u0301   ')
        self.assertTrue(rendered[1].startswith('0\t'))
        self.assertTrue(rendered[2].startswith('1\t'))
        self.assertNotIn('WORKSPACE', viewer.table(rows, 54)[0])

    def test_snoozed_status_remains_visible_and_labeled(self):
        value = viewer.line(0, dict(self.row(), snoozed=True), 110)
        self.assertIn('\033[38;5;245m\U000f04b2 ASK', value)
        self.assertEqual(viewer.cell('\U000f04b2', 3), '\U000f04b2  ')
        self.assertIn('Fix the picker', value)

    def test_all_statuses_use_single_cell_nerd_glyphs_and_keep_labels(self):
        for state, (icon, label, color) in viewer.STATUS.items():
            self.assertEqual(__import__('unicodedata').category(icon), 'Co')
            self.assertEqual(viewer.cell(icon, 2), icon + ' ')
            row = dict(self.row(), state=state)
            self.assertTrue(viewer.line(0, row, 110).startswith(f'0\t\033[38;5;{color}m{icon} {label}'))

    def test_timestamp_not_status_age(self):
        self.assertEqual(viewer.updated(100, 160), 'updated 1m ago')
        self.assertEqual(viewer.updated(None), 'updated —')
    def test_control_sanitization_and_bounds(self):
        self.assertEqual(viewer.text('a\n\x1bb\u202ec', 20), 'a b c')
        self.assertEqual(len(viewer.text('a' * 400, 20)), 20)
    def test_small_viewport_no_preview(self):
        with patch.object(shutil, 'get_terminal_size', return_value=os.terminal_size((60, 20))):
            with viewer.picker_data([self.row()], {}) as (lines, command):
                self.assertIsNone(command)
                plain = __import__('re').sub(r'\x1b\[[0-9;]*m', '', lines[0].split('\t')[1])
                self.assertLessEqual(len(plain), 54)
    def test_preview_private_and_cleaned_up(self):
        core = dict(BINARY='/bin/false', OPTIONS=[], STATE='/tmp/private')
        with patch.object(shutil, 'get_terminal_size', return_value=os.terminal_size((110, 30))):
            with viewer.picker_data([self.row()], core) as (_, command):
                import shlex
                path = Path(shlex.split(command)[2])
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
            self.assertFalse(path.exists())
    def test_real_fzf_preview_and_cancel(self):
        import fcntl, pty, select, struct, subprocess, termios, time
        import modal
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 30, 110, 0, 0))
        code = ('import sys; sys.path.insert(0, ' + repr(str(Path(viewer.__file__).parent)) + '); '
                'from modal import pick; from agent_viewer import table; '
                'rows = table(' + repr([self.row()]) + ', 104); '
                'row, action = pick(rows, "Enter focus", '
                'preview="printf SCREEN_FIXTURE", ansi=True, header_lines=1); '
                'print("CANCELLED" if row is None else "SELECTED")')
        def terminal():
            os.setsid(); fcntl.ioctl(0, termios.TIOCSCTTY, 0)
        proc = subprocess.Popen([sys.executable, '-c', code], stdin=slave, stdout=slave, stderr=slave,
                                env=dict(os.environ, TERM='xterm-256color', PYTHONDONTWRITEBYTECODE='1', NO_COLOR='1'),
                                preexec_fn=terminal)
        os.close(slave)
        output = bytearray()
        try:
            deadline = time.monotonic() + 5
            while b'SCREEN_FIXTURE' not in output and time.monotonic() < deadline:
                if select.select([master], [], [], .1)[0]: output.extend(os.read(master, 65536))
            self.assertIn(b'SCREEN_FIXTURE', output)
            # Only one candidate: its status must be colored even when selected,
            # and despite inherited NO_COLOR (fzf bw otherwise strips input ANSI).
            self.assertIn(b'38;5;179', output)
            self.assertIn(b'LAST PROMPT', output)
            os.write(master, b'Fix'); os.write(master, b'\x1b')
            proc.wait(timeout=5)
            while select.select([master], [], [], .1)[0]:
                try: output.extend(os.read(master, 65536))
                except OSError: break
            self.assertIn(b'CANCELLED', output)
            self.assertEqual(proc.returncode, 0)
        finally:
            if proc.poll() is None: proc.terminate(); proc.wait(timeout=5)
            os.close(master)

    def test_preview_exact_session_pane_no_scrollback(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as directory:
            base = Path(directory)
            state = {'terminal_7': {'owner':'owner', 'pid':os.getpid(), 'stamp':Path(f'/proc/{os.getpid()}/stat').read_text().rsplit(')',1)[1].split()[19]}}
            (base / (hashlib.sha256(b'session;literal').hexdigest() + '.json')).write_text(json.dumps(state))
            path = base / 'rows.json'
            path.write_text(json.dumps(dict(rows=[self.row()], binary='/fake/zellij', options=[], state=directory)))
            result = type('Result', (), dict(returncode=0, stdout='  terminal content\n'))()
            with patch.object(viewer.subprocess, 'run', return_value=result) as run, contextlib.redirect_stdout(io.StringIO()) as output:
                viewer.preview(path, 0)
            args = run.call_args.args[0]
            self.assertEqual(args, ['/fake/zellij', '-s', 'session;literal', 'action', 'dump-screen', '--pane-id', 'terminal_7'])
            self.assertEqual(run.call_args.kwargs['env']['TMPDIR'], '/tmp')
            self.assertIn('  terminal content', output.getvalue())
            state['terminal_7'].pop('owner')
            (base / (hashlib.sha256(b'session;literal').hexdigest() + '.json')).write_text(json.dumps(state))
            with patch.object(viewer.subprocess, 'run') as run:
                viewer.preview(path, 0)
            run.assert_not_called()

if __name__ == '__main__': unittest.main()
