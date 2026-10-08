#!/usr/bin/env python3
"""Virtual terminal defaults; no SSH, native session creation, or real panes."""
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'dot_config/zellij/bin'))
from workspaces import WorkspaceManager


class TerminalEnvTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='zellij-terminal-env-')
        root = Path(self.tmp.name)
        self.manager = WorkspaceManager({'CONFIG': root, 'HOME_STATE': root, 'SESSION': '',
            'BINARY': '/test/zellij', 'OPTIONS': ['--config', str(root / 'config.kdl')]})
        self.manager.options_for = Mock(return_value=self.manager.c['OPTIONS'])

    def tearDown(self):
        self.tmp.cleanup()

    def invoke(self, args, term):
        environment = {'PATH': '/usr/bin:/bin', 'TMPDIR': '/unsafe',
                       'ZELLIJ': '1', 'ZELLIJ_SESSION_NAME': 'outer', 'ZELLIJ_PANE_ID': '99',
                       'TMUX': 'outer', 'TMUX_PANE': '%99'}
        if term is not None: environment['TERM'] = term
        with patch.dict(os.environ, environment, clear=True):
            with patch('workspaces.subprocess.run', return_value=Mock(stdout='')) as run:
                self.manager.cli(*args)
                return run.call_args

    def test_background_servers_get_valid_term_for_all_callers(self):
        for term in [None, '', 'dumb', 'xterm-kitty', 'xterm-256color', 'screen']:
            with self.subTest(term=term):
                call = self.invoke(['attach', '--create-background', 'fixture'], term)
                self.assertEqual(call.kwargs['env']['TERM'], 'xterm-256color')
                self.assertEqual(call.kwargs['env']['TMPDIR'], '/tmp')
                for key in ['ZELLIJ', 'ZELLIJ_SESSION_NAME', 'ZELLIJ_PANE_ID', 'TMUX', 'TMUX_PANE']:
                    self.assertNotIn(key, call.kwargs['env'])

    def test_interactive_client_keeps_outer_terminal_type(self):
        for term in [None, 'xterm-kitty', 'wezterm', 'xterm-256color']:
            with self.subTest(term=term):
                call = self.invoke(['attach', 'fixture'], term)
                self.assertEqual(call.kwargs['env'].get('TERM'), term)

    def test_read_only_cli_does_not_change_terminal_type(self):
        call = self.invoke(['list-sessions', '--no-formatting'], 'xterm-kitty')
        self.assertEqual(call.kwargs['env']['TERM'], 'xterm-kitty')
        self.manager.options_for.assert_not_called()

    def test_shell_startup_repairs_old_servers_but_preserves_outside_term(self):
        script = 'source ' + shlex.quote(str(ROOT / 'dot_config/zsh/config.zsh')) + '; print -r -- ${TERM:-unset}'
        for zellij in [None, '', '0', '1']:
            for term in [None, 'xterm-kitty', 'xterm-256color']:
                with self.subTest(zellij=zellij, term=term):
                    env = {'PATH': '/usr/bin:/bin', 'HOME': self.tmp.name, 'LC_ALL': 'C.UTF-8'}
                    if zellij is not None: env['ZELLIJ'] = zellij
                    if term is not None: env['TERM'] = term
                    result = subprocess.run(['zsh', '-f', '-c', script], env=env, capture_output=True, text=True, check=True)
                    expected = 'xterm-256color' if zellij else (term if term is not None else 'unset')
                    self.assertEqual(result.stdout.strip(), expected)

    def test_default_and_carrier_configs_pin_the_pane_terminal(self):
        for name in ['config.kdl', 'bridge.kdl']:
            text = (ROOT / 'dot_config/zellij' / name).read_text()
            blocks = re.findall(r'(?m)^env\s*\{([^{}]*)\}', text)
            self.assertEqual(len(blocks), 1, name)
            self.assertRegex(blocks[0], r'\bTERM\s+"xterm-256color"')
            self.assertNotIn('xterm-kitty', blocks[0])


if __name__ == '__main__':
    unittest.main()
