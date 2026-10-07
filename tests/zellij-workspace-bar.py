#!/usr/bin/env python3
"""Workspace-bar source pinning and narrowly scoped permission-cache contracts."""
import importlib.util
import json
from pathlib import Path
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / 'setup/zellij-workspace-bar'
spec = importlib.util.spec_from_file_location('ui_permissions', SPEC / 'grant-ui-permissions.py')
permissions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(permissions)


class PermissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.plugin = self.root / 'workspace-bar-0.45.1.wasm'
        self.plugin.write_bytes(b'\0asm')
        self.cache = self.root / 'permissions.kdl'
        self.backups = self.root / 'backups'

    def tearDown(self):
        self.temp.cleanup()

    def grant(self):
        return permissions.grant(self.cache, self.plugin, self.backups)

    def test_grants_only_ui_and_preserves_other_entries(self):
        existing = '"other-plugin" {\n    OpenFiles\n}\n'
        self.cache.write_text(existing)
        self.assertTrue(self.grant())
        result = self.cache.read_text()
        self.assertTrue(result.startswith(existing))
        self.assertIn(json.dumps(str(self.plugin)), result)
        self.assertIn('ReadApplicationState', result)
        self.assertIn('ChangeApplicationState', result)
        self.assertNotIn('RunCommands', result)
        backup = next(self.backups.glob('*.kdl'))
        self.assertEqual(backup.read_text(), existing)
        self.assertEqual(self.cache.stat().st_mode & 0o777, 0o600)

    def test_repeat_is_idempotent(self):
        self.grant()
        before = self.cache.read_bytes()
        self.assertFalse(self.grant())
        self.assertEqual(self.cache.read_bytes(), before)

    def test_old_broad_entry_is_restricted_only_for_owned_plugin(self):
        self.cache.write_text(json.dumps(str(self.plugin)) + ' {\n RunCommands\n ReadApplicationState\n}\n"other" {\n RunCommands\n}\n')
        self.grant()
        result = self.cache.read_text()
        self.assertEqual(result.count('RunCommands'), 1)
        self.assertIn('"other" {\n RunCommands\n}', result)

    def test_duplicate_entries_refuse_without_mutation(self):
        entry = json.dumps(str(self.plugin)) + ' {\n ReadApplicationState\n}\n'
        self.cache.write_text(entry * 2)
        with self.assertRaises(ValueError): self.grant()
        self.assertEqual(self.cache.read_text(), entry * 2)

    def test_nested_owned_entry_refuses_without_mutation(self):
        original = json.dumps(str(self.plugin)) + ' {\n strange {\n  RunCommands\n }\n}\n'
        self.cache.write_text(original)
        with self.assertRaises(ValueError): self.grant()
        self.assertEqual(self.cache.read_text(), original)

    def test_plugin_and_cache_symlinks_refuse(self):
        self.plugin.unlink()
        self.plugin.symlink_to(self.root / 'elsewhere')
        with self.assertRaises(ValueError): self.grant()
        self.plugin.unlink(); self.plugin.write_bytes(b'\0asm')
        self.cache.symlink_to(self.root / 'other-cache')
        with self.assertRaises(ValueError): self.grant()

    def test_other_plugin_path_refuses(self):
        other = self.root / 'another.wasm'
        other.write_bytes(b'\0asm')
        with self.assertRaises(ValueError): permissions.grant(self.cache, other, self.backups)

    def test_sdk_versions_and_checksums_are_locked(self):
        lock = tomllib.loads((SPEC / 'Cargo.lock').read_text())
        packages = {item['name']: item for item in lock['package']}
        for name, digest in [('zellij-tile', '419f01e4e9150c5cafe204875a8c7113b428fee2fa2edb9b43bc7f33518b17ed'),
                             ('zellij-tile-utils', 'aa7e99ded4e7ae80573fc310ad6b4d8fc854e056263953ed4ac089913dfe7910')]:
            self.assertEqual(packages[name]['version'], '0.45.1')
            self.assertEqual(packages[name]['checksum'], digest)

    def test_patch_has_only_minimal_ui_permissions(self):
        patch = (SPEC / 'workspace-name.patch').read_text()
        added = '\n'.join(line[1:] for line in patch.splitlines() if line.startswith('+') and not line.startswith('+++'))
        self.assertIn('PermissionType::ReadApplicationState', added)
        self.assertIn('PermissionType::ChangeApplicationState', added)
        self.assertNotIn('RunCommands', added)
        self.assertNotIn('run_command', added)
        self.assertIn('session_name.unwrap_or("workspace")', added)
        self.assertIn('_hide_session_name', added)
        self.assertNotIn('" Zellij "', added)


if __name__ == '__main__':
    unittest.main()
