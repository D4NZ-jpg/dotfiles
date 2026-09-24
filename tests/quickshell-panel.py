#!/usr/bin/env python3
"""Exercise the real panel QML components with fake services, without a window."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parent.parent
PANEL = REPO / "dot_config/quickshell/panel"
COMPONENTS = ("NetworkContent.qml", "VolumeContent.qml", "BluetoothContent.qml", "SyncContent.qml", "PanelAction.qml")


def run_fixture(fixture: str, marker: str) -> str:
    with tempfile.TemporaryDirectory(prefix="quickshell-panel-test-") as directory:
        sandbox = Path(directory)
        (sandbox / "panel").mkdir()
        for name in COMPONENTS:
            shutil.copy2(PANEL / name, sandbox / "panel" / name)
        shutil.copy2(REPO / "tests" / fixture, sandbox / "shell.qml")
        env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
        env.pop("WAYLAND_DISPLAY", None)
        try:
            result = subprocess.run(
                ["quickshell", "--no-color", "-p", str(sandbox)],
                capture_output=True, text=True, env=env, timeout=15,
            )
        except subprocess.TimeoutExpired as error:
            raise AssertionError("QML test timed out:\n" + (error.stdout or "") + (error.stderr or ""))
        output = result.stdout + result.stderr
        assert result.returncode == 0, output
        assert marker + "_FAIL" not in output, output
        assert marker + "_PASS" in output, output
        assert "WARN" not in output and "ERROR" not in output, output
        return next(line.strip() for line in output.splitlines() if marker + "_PASS" in line)


class PanelPopupTests(unittest.TestCase):
    def test_network_flows(self):
        print(run_fixture("quickshell-network.qml", "NETWORK_TESTS"))

    def test_volume_flows(self):
        print(run_fixture("quickshell-volume.qml", "VOLUME_TESTS"))

    def test_bluetooth_flows(self):
        print(run_fixture("quickshell-bluetooth.qml", "BLUETOOTH_TESTS"))

    def test_sync_flows(self):
        print(run_fixture("quickshell-sync.qml", "SYNC_TESTS"))


if __name__ == "__main__":
    unittest.main()
