"""Exercise setup orchestration in synthetic homes; never sudo or launch Zen."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'setup/scripts/executable_zen-setup.sh'


class SetupTests(unittest.TestCase):
    def run_setup(self, existing=False, fail_zen=False, fail_sudo=False, no_registry=False):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            bin = home / 'bin'; bin.mkdir()
            style = home / '.config/zen-style'; style.mkdir(parents=True)
            for f in ['apply.py', 'theme.css', 'install-addons.py', 'addon-policies.json']:
                (style / f).write_text('synthetic placeholder')
            if existing:
                (home / '.zen').mkdir()
                (home / '.zen/profiles.ini').write_text('existing registry')
            commands = {
                'zen-browser': '''echo zen >> "$HOME/calls"
[ "$FAIL_ZEN" = 0 ] || exit 1
if [ "$NO_REGISTRY" = 0 ]; then mkdir -p "$HOME/.zen"; printf 'synthetic registry' > "$HOME/.zen/profiles.ini"; fi
''',
                'python3': 'echo preferences >> "$HOME/calls"\n',
                'sudo': 'echo policy >> "$HOME/calls"\n[ "$FAIL_SUDO" = 0 ]\n',
                'xdg-settings': 'echo default >> "$HOME/calls"\n',
            }
            for name, body in commands.items():
                p = bin / name; p.write_text('#!/bin/sh\n' + body); p.chmod(0o700)
            env = dict(os.environ, HOME=str(home), PATH=str(bin) + ':' + os.environ['PATH'],
                       FAIL_ZEN=str(int(fail_zen)), FAIL_SUDO=str(int(fail_sudo)), NO_REGISTRY=str(int(no_registry)))
            p = subprocess.run(['bash', str(SCRIPT)], env=env, capture_output=True, text=True, timeout=10)
            calls = (home / 'calls').read_text().splitlines() if (home / 'calls').exists() else []
            return p.returncode, calls

    def test_fresh_install(self):
        self.assertEqual(self.run_setup(), (0, ['zen', 'preferences', 'policy', 'default']))

    def test_existing_profile(self):
        self.assertEqual(self.run_setup(existing=True), (0, ['preferences', 'policy', 'default']))

    def test_bootstrap_failure_stops(self):
        code, calls = self.run_setup(fail_zen=True)
        self.assertNotEqual(code, 0); self.assertEqual(calls, ['zen'])

    def test_missing_registry_stops(self):
        code, calls = self.run_setup(no_registry=True)
        self.assertNotEqual(code, 0); self.assertEqual(calls, ['zen'])

    def test_sudo_failure_stops(self):
        code, calls = self.run_setup(existing=True, fail_sudo=True)
        self.assertNotEqual(code, 0); self.assertEqual(calls, ['preferences', 'policy'])


if __name__ == '__main__':
    unittest.main()
