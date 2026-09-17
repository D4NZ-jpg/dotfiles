"""Installer helper tests: all package manager/service calls are mocked."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

UTILS = Path(__file__).resolve().parents[1] / 'setup/scripts/executable_utils.sh'


class InstallerTests(unittest.TestCase):
    def run_case(self, body, packages='', installed='', bootstrap=False, enabled=False, active=False, clone_fail=False):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bin = root / 'bin'; bin.mkdir()
            (root / 'packages.list').write_text(packages)
            stubs = {
                'pacman': '''printf 'pacman'; printf ' <%s>' "$@"; printf '\n'
if [ "$1" = -Q ]; then
 shift; [ "$1" != -- ] || shift
 case " $INSTALLED " in *" $1 "*) exit 0;; *) exit 1;; esac
fi
''',
                'sudo': '''printf 'sudo'; printf ' <%s>' "$@"; printf '\n' ''',
                'yay': '''printf 'yay'; printf ' <%s>' "$@"; printf '\n' ''',
                'systemctl': '''case "$1" in is-enabled) [ "$ENABLED" = 1 ];; is-active) [ "$ACTIVE" = 1 ];; *) exit 99;; esac''',
                'git': '''[ "$CLONE_FAIL" = 0 ] || exit 1
mkdir -p "$3"
''',
                'makepkg': '''printf '#!/bin/sh\nprintf "yay-bootstrap"; printf " <%%s>" "$@"; printf "\\n"\n' > "$TEST_BIN/yay"
chmod +x "$TEST_BIN/yay"
''',
            }
            for name, script in stubs.items():
                if name == 'yay' and bootstrap:
                    continue
                p = bin / name; p.write_text('#!/bin/sh\n' + script + '\n'); p.chmod(0o700)
            # Hide any host Yay binary during the bootstrap test.
            prefix = '''command() {
 if [[ "$1" == -v && "$2" == yay ]]; then [[ -x "$TEST_BIN/yay" ]]; else builtin command "$@"; fi
}
'''
            env = dict(os.environ, PATH=str(bin) + ':' + os.environ['PATH'], TEST_BIN=str(bin),
                       INSTALLED=installed, ENABLED=str(int(enabled)), ACTIVE=str(int(active)), CLONE_FAIL=str(int(clone_fail)))
            p = subprocess.run(['bash', '-ec', 'source "$1"\n' + prefix + body, 'test', str(UTILS)],
                               cwd=root, env=env, capture_output=True, text=True, timeout=10)
            return p.returncode, p.stdout, p.stderr

    def test_grouped_packages_comments_duplicates(self):
        code, out, err = self.run_case('installPkgs packages.list', '\n# comment\none two\none\nthree # note\n', installed='two')
        self.assertEqual(code, 0, err)
        self.assertIn('yay <-S> <--needed> <--> <one> <three>', out)
        self.assertNotIn('sudo', out)

    def test_empty_list_skips_package_managers(self):
        code, out, err = self.run_case('installPkgs packages.list', '\n# none\n')
        self.assertEqual(code, 0, err); self.assertNotIn('yay <', out); self.assertNotIn('sudo', out)

    def test_all_installed_skips_package_managers(self):
        code, out, err = self.run_case('installPkgs packages.list', 'one\ntwo\n', installed='one two')
        self.assertEqual(code, 0, err); self.assertNotIn('yay <', out)

    def test_bootstrap_preserves_cwd_and_list(self):
        code, out, err = self.run_case('before=$PWD; installPkgs packages.list; [[ "$PWD" == "$before" ]]', 'one\ntwo', bootstrap=True)
        self.assertEqual(code, 0, err)
        self.assertIn('sudo <pacman> <-S> <--needed> <git> <base-devel>', out)
        self.assertIn('yay-bootstrap <-S> <--needed> <--> <one> <two>', out)

    def test_bootstrap_failure_propagates(self):
        code, out, err = self.run_case('installPkgs packages.list', 'one', bootstrap=True, clone_fail=True)
        self.assertNotEqual(code, 0); self.assertNotIn('yay-bootstrap', out)

    def test_enabled_but_stopped_service(self):
        code, out, err = self.run_case('startCtl NetworkManager', enabled=True)
        self.assertEqual(code, 0, err)
        self.assertIn('sudo <systemctl> <enable> <--now> <NetworkManager.service>', out)

    def test_healthy_service_noop(self):
        code, out, err = self.run_case('startCtl NetworkManager.service; enableCtl NetworkManager', enabled=True, active=True)
        self.assertEqual(code, 0, err); self.assertNotIn('sudo', out)

    def test_missing_list_fails_without_package_changes(self):
        code, out, err = self.run_case('installPkgs missing.list')
        self.assertNotEqual(code, 0); self.assertNotIn('sudo', out); self.assertNotIn('yay <', out)


if __name__ == '__main__':
    unittest.main()
