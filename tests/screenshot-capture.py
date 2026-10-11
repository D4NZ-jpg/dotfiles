#!/usr/bin/env python3
"""Synthetic subprocess tests: never access the live desktop or clipboard."""
import base64
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "dot_config/scripts/executable_screenshot-capture.py"
SPEC = importlib.util.spec_from_file_location("capture", SCRIPT)
capture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(capture)
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a3ioAAAAASUVORK5CYII=")
MONITORS = [{"id": 0, "name": "FAKE-1", "width": 1800, "height": 1200, "scale": 1.5,
             "x": -1200, "y": 0, "focused": True, "activeWorkspace": {"id": 1}}]
CLIENT = {"address": "fixture-a", "mapped": True, "hidden": False,
          "workspace": {"id": 1}, "at": [-1300, 20], "size": [300, 200]}
FAKE = '''#!/usr/bin/python3
import base64,json,os,pathlib,sys
name=pathlib.Path(sys.argv[0]).name
root=pathlib.Path(os.environ['FIXTURE'])
cfg=json.loads((root/'config.json').read_text())
with (root/'calls.jsonl').open('a') as f: f.write(json.dumps([name,*sys.argv[1:]])+'\\n')
if cfg.get('fail') == name: sys.exit(1)
if name == 'hyprctl':
    key=sys.argv[-1]
    value=cfg.get(key, {})
    if key=='clients' and cfg.get('move'):
        count=root/'client-count'
        n=int(count.read_text()) if count.exists() else 0
        count.write_text(str(n+1))
        if n: value=[]
    print(json.dumps(value))
elif name=='slurp':
    # Like real slurp, read predefined boxes from a non-terminal stdin until EOF.
    (root/'slurp-input').write_bytes(sys.stdin.buffer.read())
    if cfg.get('hang'):
        (root/'slurp-pid').write_text(str(os.getpid()))
        import time; time.sleep(60)
    if cfg.get('cancel'): sys.exit(1)
    print(cfg.get('selection','-1200,20 200x200'))
elif name=='grim':
    pathlib.Path(sys.argv[-1]).write_bytes(b'bad png' if cfg.get('bad_png') else base64.b64decode(cfg['png']))
elif name=='wl-copy':
    (root/'fake-clipboard').write_bytes(sys.stdin.buffer.read())
elif name=='xdg-user-dir':
    print(cfg.get('pictures',str(root/'Pictures with spaces')))
'''


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="screenshot-tests-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ("bin", "runtime", "tmp", "home"):
            (self.root / name).mkdir()
        for name in ("hyprctl", "slurp", "grim", "wl-copy", "xdg-user-dir", "notify-send"):
            path = self.root / "bin" / name
            path.write_text(FAKE)
            path.chmod(0o700)
        self.config = {"layers": {}, "monitors": MONITORS, "clients": [CLIENT], "png": base64.b64encode(PNG).decode()}
        self.env = {**os.environ, "PATH": str(self.root / "bin"), "FIXTURE": str(self.root),
                    "HOME": str(self.root / "home"), "XDG_RUNTIME_DIR": str(self.root / "runtime"),
                    "TMPDIR": str(self.root / "tmp")}

    def invoke(self, mode="region", destination="clipboard", **config):
        self.config.update(config)
        (self.root / "config.json").write_text(json.dumps(self.config))
        # Quickshell launches the backend with an open stdin pipe it never closes.
        process = subprocess.Popen(["/usr/bin/python3", str(SCRIPT), mode, destination],
                                   env=self.env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True)
        try:
            stdout, stderr = self.wait_open_stdin(process)
        finally:
            process.stdin.close()
        self.assertEqual(stdout + stderr, "")
        self.assertEqual(list((self.root / "tmp").iterdir()), [], "Private capture files cleaned")
        self.assertEqual(list(self.root.rglob(".screenshot-*")), [], "Staging files cleaned")
        return process.returncode

    def wait_open_stdin(self, process):
        try:
            process.wait(timeout=7)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            self.fail("Backend hung with an open stdin pipe")
        with process.stdout, process.stderr:
            return process.stdout.read(), process.stderr.read()

    def calls(self, name):
        return [x for x in map(json.loads, (self.root / "calls.jsonl").read_text().splitlines()) if x[0] == name]

    def saved(self):
        return list((self.root / "Pictures with spaces" / "Screenshots").glob("*.png"))

    def test_region_clipboard_is_explicit_png(self):
        self.assertEqual(self.invoke(), 0)
        self.assertEqual((self.root / "fake-clipboard").read_bytes(), PNG)
        self.assertEqual(self.calls("wl-copy")[0], ["wl-copy", "--type", "image/png"])
        self.assertEqual(self.calls("grim")[0][1:5], ["-t", "png", "-g", "-1200,20 200x200"])
        self.assertEqual(self.saved(), [])

    def test_screen_folder_and_private_permissions(self):
        self.assertEqual(self.invoke("screen", "folder"), 0)
        self.assertEqual(self.calls("grim")[0][1:5], ["-t", "png", "-o", "FAKE-1"])
        image, = self.saved()
        self.assertEqual(image.read_bytes(), PNG)
        self.assertEqual(image.stat().st_mode & 0o777, 0o600)
        self.assertTrue(image.name.startswith("Screenshot-"))
        self.assertEqual(self.calls("wl-copy"), [])

    def test_both_destinations(self):
        self.assertEqual(self.invoke(destination="both"), 0)
        self.assertEqual(self.saved()[0].read_bytes(), (self.root / "fake-clipboard").read_bytes())
        self.assertIn("and copied", self.calls("notify-send")[-1][-1])

    def test_window_clipped_to_scaled_negative_monitor(self):
        self.assertEqual(self.invoke("window", "folder"), 0)
        self.assertEqual((self.root / "slurp-input").read_text(), "-1200,20 200x200\n")
        self.assertIn("-r", self.calls("slurp")[0])

    def test_cancel_is_quiet_and_never_captures(self):
        self.assertEqual(self.invoke(cancel=True), 0)
        self.assertEqual(self.calls("grim") + self.calls("wl-copy") + self.calls("notify-send"), [])

    def test_empty_selection_cancels(self):
        self.assertEqual(self.invoke(selection=""), 0)
        self.assertEqual(self.calls("grim"), [])

    def test_invalid_geometry_never_captures(self):
        self.assertEqual(self.invoke(selection="0,0 0x2"), 1)
        self.assertEqual(self.calls("grim"), [])

    def test_grim_failure_never_copies_or_saves(self):
        self.assertEqual(self.invoke(destination="both", fail="grim"), 1)
        self.assertEqual(self.calls("wl-copy"), [])
        self.assertEqual(self.saved(), [])

    def test_invalid_png_never_copies_or_saves(self):
        self.assertEqual(self.invoke(destination="both", bad_png=True), 1)
        self.assertEqual(self.calls("wl-copy"), [])
        self.assertEqual(self.saved(), [])

    def test_clipboard_failure_reports_partial_save(self):
        self.assertEqual(self.invoke(destination="both", fail="wl-copy"), 1)
        self.assertEqual(len(self.saved()), 1)
        self.assertIn("but clipboard copy failed", self.calls("notify-send")[-1][-1])

    def test_missing_screen_never_captures(self):
        self.assertEqual(self.invoke("screen", monitors=[]), 1)
        self.assertEqual(self.calls("grim"), [])

    def test_window_moves_during_selection(self):
        self.assertEqual(self.invoke("window", move=True), 1)
        self.assertEqual(self.calls("grim"), [])

    def test_no_visible_window_does_not_start_slurp(self):
        hidden = {**CLIENT, "hidden": True}
        other = {**CLIENT, "workspace": {"id": 2}}
        self.assertEqual(self.invoke("window", clients=[hidden, other]), 1)
        self.assertEqual(self.calls("slurp"), [])

    def test_toolbar_must_unmap(self):
        layers = {"FAKE-1": {"levels": {"3": [{"namespace": "dan-screenshot"}]}}}
        self.assertEqual(self.invoke(layers=layers), 1)
        self.assertEqual(self.calls("grim"), [])

    def test_non_absolute_pictures_path(self):
        self.assertEqual(self.invoke(destination="folder", pictures="relative"), 1)
        self.assertEqual(self.saved(), [])

    def test_directory_failure_does_not_touch_clipboard(self):
        blocked = self.root / "blocked"
        blocked.write_text("fixture")
        self.assertEqual(self.invoke(destination="both", pictures=str(blocked)), 1)
        self.assertEqual(self.calls("wl-copy"), [])

    def test_concurrent_selection_is_rejected(self):
        state = self.root / "runtime" / "dan-screenshot"
        state.mkdir()
        with (state / "capture.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(self.invoke(), 1)
        self.assertEqual(self.calls("grim"), [])

    def test_sigterm_cancels_and_stops_selector(self):
        self.config["hang"] = True
        (self.root / "config.json").write_text(json.dumps(self.config))
        process = subprocess.Popen(["/usr/bin/python3", str(SCRIPT), "region", "clipboard"], env=self.env,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pid_file = self.root / "slurp-pid"
        for _ in range(100):
            if pid_file.exists() and pid_file.read_text():
                break
            time.sleep(0.05)
        process.terminate()
        self.assertEqual(process.wait(timeout=5), 0)
        self.assertEqual(process.stdout.read() + process.stderr.read(), b"")
        process.stdout.close(); process.stderr.close()
        slurp = int(pid_file.read_text())
        for _ in range(40):
            try:
                os.kill(slurp, 0)
            except ProcessLookupError:
                break
            time.sleep(0.05)
        else:
            os.kill(slurp, 9)
            self.fail("slurp survived cancellation")
        self.assertEqual(self.calls("grim") + self.calls("wl-copy") + self.calls("notify-send"), [])
        self.assertEqual(list((self.root / "tmp").iterdir()), [])

    def test_repeated_save_does_not_overwrite(self):
        self.assertEqual(self.invoke(destination="folder"), 0)
        self.assertEqual(self.invoke(destination="folder"), 0)
        self.assertEqual(len(self.saved()), 2)


class GeometryTests(unittest.TestCase):
    def test_rotated_scaled_monitor(self):
        self.assertEqual(capture.monitor_rect({**MONITORS[0], "transform": 1}), (-1200, 0, 800, 1200))

    def test_filter_mapping_workspace_and_offscreen(self):
        clients = [CLIENT, {**CLIENT, "mapped": False}, {**CLIENT, "at": [2000, 0]},
                   {**CLIENT, "workspace": {"id": 2}}]
        self.assertEqual(capture.window_candidates(clients, MONITORS), {"-1200,20 200x200": ["fixture-a"]})

    def test_pinned_and_visible_special_workspace(self):
        monitor = {**MONITORS[0], "specialWorkspace": {"id": -99}}
        clients = [{**CLIENT, "workspace": {"id": -99}}, {**CLIENT, "pinned": True, "workspace": {"id": 3}}]
        self.assertEqual(len(capture.window_candidates(clients, [monitor])["-1200,20 200x200"]), 2)

    def test_window_spanning_outputs_is_not_cut_in_half(self):
        second = {**MONITORS[0], "name": "FAKE-2", "x": 0, "activeWorkspace": {"id": 2}}
        client = {**CLIENT, "at": [-100, 20], "size": [300, 200]}
        self.assertEqual(capture.window_candidates([client], [MONITORS[0], second]),
                         {"-100,20 300x200": ["fixture-a"]})

    def test_mirrored_and_disabled_outputs_are_not_candidates(self):
        self.assertEqual(capture.window_candidates([CLIENT], [{**MONITORS[0], "disabled": True}]), {})
        self.assertEqual(capture.window_candidates([CLIENT], [{**MONITORS[0], "mirrorOf": "FAKE-2"}]), {})

    def test_fractional_client_rounds_outwards(self):
        client = {**CLIENT, "at": [-1100.5, 20.5], "size": [100, 100]}
        self.assertIn("-1101,20 101x101", capture.window_candidates([client], MONITORS))


if __name__ == "__main__":
    unittest.main()
