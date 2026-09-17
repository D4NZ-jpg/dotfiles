#!/usr/bin/env python3
"""Exercise the real QML component with fake network objects, without a window."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class NetworkPopupTests(unittest.TestCase):
    def test_synthetic_network_flows(self):
        repo = Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory(prefix="quickshell-network-test-") as directory:
            sandbox = Path(directory)
            (sandbox / "panel").mkdir()
            for name in ("NetworkContent.qml", "PanelAction.qml"):
                shutil.copy2(repo / "dot_config/quickshell/panel" / name, sandbox / "panel" / name)
            shutil.copy2(Path(__file__).with_suffix(".qml"), sandbox / "shell.qml")
            env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
            env.pop("WAYLAND_DISPLAY", None)
            try:
                result = subprocess.run(
                    ["quickshell", "--no-color", "-p", str(sandbox)],
                    capture_output=True, text=True, env=env, timeout=15,
                )
            except subprocess.TimeoutExpired as error:
                self.fail("QML test timed out:\n" + (error.stdout or b"").decode(errors="replace")
                          + (error.stderr or b"").decode(errors="replace"))
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertNotIn("NETWORK_TESTS_FAIL", output, output)
            self.assertRegex(output, r"NETWORK_TESTS_PASS [0-9]+", output)
            self.assertNotIn("WARN", output, output)
            self.assertNotIn("ERROR", output, output)
            print(next(line.strip() for line in output.splitlines() if "NETWORK_TESTS_PASS" in line))


if __name__ == "__main__":
    unittest.main()
