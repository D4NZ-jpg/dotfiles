"""Read-only driver planning and mocked configuration tests; no GPU changes."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'setup/scripts/executable_nvidia.sh'
MAPS = ROOT / 'setup/dot_nvidia'


class NvidiaTests(unittest.TestCase):
    def plan(self, inventory):
        return subprocess.run(['bash', '-ec', 'source "$1"; lspci() { printf "%s\\n" "$GPU"; }; planNvidia "$2"', 'test', str(HELPER), str(MAPS)],
                              env=dict(os.environ, GPU=inventory), capture_output=True, text=True)

    def test_pascal(self):
        p = self.plan('01:00.0 VGA compatible controller: NVIDIA Corporation GP107 [GeForce GTX 1050]')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.splitlines(), ['nvidia-580xx-dkms', 'nvidia-580xx-utils', 'lib32-nvidia-580xx-utils'])

    def test_modern(self):
        p = self.plan('01:00.0 VGA compatible controller: NVIDIA Corporation AD104 [GeForce RTX 4070]')
        self.assertEqual(p.stdout.splitlines(), ['nvidia-open-dkms', 'nvidia-utils', 'lib32-nvidia-utils'])

    def test_no_gpu_or_audio_only(self):
        for s in ['Intel Corporation VGA', 'Audio device: NVIDIA Corporation GP107GL']:
            p = self.plan(s); self.assertEqual(p.returncode, 0); self.assertEqual(p.stdout, '')

    def test_unknown(self):
        p = self.plan('VGA compatible controller: NVIDIA Corporation UNKNOWN')
        self.assertNotEqual(p.returncode, 0); self.assertEqual(p.stdout, '')

    def test_mixed_driver_families(self):
        p = self.plan('VGA controller: NVIDIA GP107\n3D controller: NVIDIA AD104')
        self.assertNotEqual(p.returncode, 0); self.assertEqual(p.stdout, '')

    def test_same_family_deduplicated(self):
        p = self.plan('VGA controller: NVIDIA GP107\n3D controller: NVIDIA GP108')
        self.assertEqual(p.returncode, 0); self.assertEqual(len(p.stdout.splitlines()), 3)

    def test_old_unsupported_branch(self):
        p = self.plan('VGA controller: NVIDIA GF100')
        self.assertNotEqual(p.returncode, 0); self.assertIn('compatibility review', p.stderr)

    def configure(self, config='', missing=False, service_missing=False, existing_file=False):
        with tempfile.TemporaryDirectory() as d:
            if existing_file:
                (Path(d) / '90-dotfiles-nvidia.conf').write_text('custom untouched')
            code = '''source "$1"
isInstalled() { [[ "$MISSING" == 0 ]]; }
systemctl() { if [[ "$SERVICE_MISSING" == 0 ]]; then echo loaded; else echo not-found; fi; }
modprobe() { printf '%s\\n' "$CONFIG"; }
mkinitcpio() { :; }
sudo() { printf 'sudo'; printf ' <%s>' "$@"; printf '\\n'; if [[ "$1" == tee ]]; then cat >/dev/null; fi; }
enableCtl() { printf 'enable %s\\n' "$1"; }
configureNvidia nvidia-580xx-dkms "$2"
'''
            p = subprocess.run(['bash', '-ec', code, 'test', str(HELPER), d], capture_output=True, text=True,
                               env=dict(os.environ, CONFIG=config, MISSING=str(int(missing)), SERVICE_MISSING=str(int(service_missing))))
            if existing_file:
                self.assertEqual((Path(d) / '90-dotfiles-nvidia.conf').read_text(), 'custom untouched')
            return p

    def test_packages_required_before_configuration(self):
        p = self.configure(missing=True)
        self.assertNotEqual(p.returncode, 0); self.assertEqual(p.stdout, '')

    def test_services_required_before_configuration(self):
        p = self.configure(service_missing=True)
        self.assertNotEqual(p.returncode, 0); self.assertEqual(p.stdout, '')

    def test_existing_setting_avoids_rebuild(self):
        p = self.configure('options nvidia NVreg_PreserveVideoMemoryAllocations=1')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn('sudo', p.stdout); self.assertEqual(p.stdout.count('enable '), 3)

    def test_new_setting_rebuilds_then_enables(self):
        p = self.configure()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('sudo <mkinitcpio> <-P>', p.stdout)
        self.assertLess(p.stdout.index('mkinitcpio'), p.stdout.index('enable nvidia-suspend'))
        self.assertNotIn('--now', p.stdout)

    def test_conflicting_setting_refused(self):
        p = self.configure('options nvidia NVreg_PreserveVideoMemoryAllocations=0')
        self.assertNotEqual(p.returncode, 0); self.assertEqual(p.stdout, '')

    def test_custom_file_preserved(self):
        p = self.configure(existing_file=True)
        self.assertNotEqual(p.returncode, 0); self.assertEqual(p.stdout, '')

    def test_installer_ordering(self):
        text = (ROOT / 'setup/scripts/executable_install.sh').read_text()
        self.assertLess(text.index('nvidia_packages=$(planNvidia'), text.index('sudo '))
        self.assertLess(text.index('installPkgs "$install_list"'), text.index('configureNvidia "$nvidia_driver"'))
        self.assertNotIn('update-initramfs', text)


if __name__ == '__main__':
    unittest.main()
