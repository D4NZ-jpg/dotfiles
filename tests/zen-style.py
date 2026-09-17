"""Synthetic profiles only: never inspect a real browser profile."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

source = Path(__file__).resolve().parents[1] / "dot_config/zen-style/apply.py"
spec = importlib.util.spec_from_file_location("zen_style", source)
style = importlib.util.module_from_spec(spec)
spec.loader.exec_module(style)


class ThemeTests(unittest.TestCase):
    def test_absent_browser(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "absent"
            self.assertEqual(style.apply(root, "/* theme */"), 0)
            self.assertFalse(root.exists())

    def test_discovery_preservation_and_idempotence(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "profiles.ini").write_text("[Profile0]\nPath=random.default\nIsRelative=1\n")
            p = root / "random.default"
            (p / "chrome").mkdir(parents=True)
            css = '@charset "UTF-8";\n/* personal rule */\n#custom { color: red; }\n'
            (p / "chrome/userChrome.css").write_text(css)
            (p / "user.js").write_text('user_pref("custom.setting", "synthetic");\nuser_pref("zen.view.window.scheme", 1);\n')
            (p / "cookies.sqlite").write_bytes(b"synthetic untouched database")
            theme = "/* managed theme */\n"
            self.assertEqual(style.apply(root, theme), 1)
            out = (p / "chrome/userChrome.css").read_text()
            self.assertTrue(out.startswith('@charset "UTF-8";'))
            self.assertIn(style.IMPORT, out)
            self.assertIn('#custom { color: red; }', out)
            self.assertIn('"custom.setting", "synthetic"', (p / "user.js").read_text())
            self.assertIn('"zen.view.window.scheme", 0', (p / "user.js").read_text())
            before = {f: (f.read_bytes(), f.stat().st_mtime_ns) for f in p.rglob('*') if f.is_file()}
            style.apply(root, theme)
            self.assertEqual(before, {f: (f.read_bytes(), f.stat().st_mtime_ns) for f in before})
            self.assertEqual((p / "cookies.sqlite").read_bytes(), b"synthetic untouched database")

    def test_migrate_original_theme(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / 'chrome').mkdir()
            (p / 'chrome/userChrome.css').write_text('/* old managed CSS */')
            style.apply_profile(p, '/* old managed CSS */')
            self.assertEqual((p / 'chrome/userChrome.css').read_text(), style.IMPORT + '\n')

    def test_skip_external_profile(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'zen'; root.mkdir()
            outside = Path(d) / 'external'; outside.mkdir()
            (root / 'profiles.ini').write_text('[Profile0]\nPath=../external\nIsRelative=1\n')
            self.assertEqual(style.apply(root, '/* theme */'), 0)
            self.assertEqual(list(outside.iterdir()), [])

    def test_reject_symlink_target(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); (p / 'chrome').mkdir()
            target = p / 'untouched'; target.write_text('synthetic')
            (p / 'user.js').symlink_to(target)
            with self.assertRaises(ValueError):
                style.apply_profile(p, '/* theme */')
            self.assertEqual(target.read_text(), 'synthetic')


if __name__ == '__main__':
    unittest.main()
