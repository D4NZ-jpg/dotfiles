#!/usr/bin/env python3
"""Event-driven per-output row indicator for Waybar on Hyprland's Lua IPC.

One idle socket listener per bar; no polling timer. Lua owns all workspace moves.
"""
import argparse
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import sys

EVENTS = {"workspace", "workspacev2", "focusedmon", "focusedmonv2", "createworkspace",
          "createworkspacev2", "destroyworkspace", "destroyworkspacev2", "moveworkspace",
          "moveworkspacev2", "changeworkspaceid", "monitoradded", "monitorremoved"}


def query(endpoint):
    return json.loads(subprocess.check_output(["hyprctl", "-j", endpoint], text=True, timeout=5))


def render(monitors, workspaces, output):
    monitor = next((m for m in monitors if m["name"] == output), None)
    rows = sorted(w["id"] for w in workspaces if w["id"] > 0 and w.get("monitor") == output)
    if monitor is None:
        return {"text": "", "tooltip": "Output disconnected", "class": "disconnected"}
    active = monitor["activeWorkspace"]["id"]
    index = rows.index(active) + 1 if active in rows else 0
    return {"text": f"{index} / {len(rows)}", "class": "rows",
            "tooltip": f"{output}: row {index} of {len(rows)}\nScroll: previous/next row\nLeft click: next · Right click: previous"}


def action(output, direction):
    # Lua uses the same double-quoted ASCII string escaping as JSON here.
    code = f'hl.dispatch(hl.dsp.focus({{monitor={json.dumps(output)}}})); workspace_rows.step({direction}, false)'
    return shlex.join(["hyprctl", "eval", code])


def configuration(monitors, script, home):
    configs = []
    for monitor in monitors:
        output = monitor["name"]
        configs.append({"output": output, "layer": "top", "spacing": 0,
                       "margin-top": 0, "margin-left": 0, "margin-right": 0,
                       "include": [str(home / ".config/waybar/modules.json")],
                       "modules-left": ["custom/rows"], "modules-center": [],
                       "modules-right": ["pulseaudio", "battery", "bluetooth", "network", "clock"],
                       "custom/rows": {
                           "exec": shlex.join([sys.executable, str(script), "--output", output]),
                           "return-type": "json", "restart-interval": 3,
                           "on-click": action(output, 1), "on-click-right": action(output, -1),
                           "on-scroll-up": action(output, -1), "on-scroll-down": action(output, 1),
                           "exec-on-event": False}})
    return configs


def launch():
    runtime = Path(os.environ["XDG_RUNTIME_DIR"]) / "hypr-rowbar"
    runtime.mkdir(mode=0o700, exist_ok=True)
    home = Path.home()
    path = runtime / "config.json"
    path.write_text(json.dumps(configuration(query("monitors"), Path(__file__).resolve(), home)))
    path.chmod(0o600)
    style = runtime / "style.css"
    style.write_text('@import "' + str(home / ".config/waybar/style.css") + '";\n#custom-rows { padding: 0 12px; }\n')
    style.chmod(0o600)
    os.execvp("waybar", ["waybar", "-c", str(path), "-s", str(style)])


def stream(output):
    runtime = Path(os.environ["XDG_RUNTIME_DIR"])
    signature = os.environ["HYPRLAND_INSTANCE_SIGNATURE"]
    path = runtime / "hypr" / signature / ".socket2.sock"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.connect(str(path))
        previous = None
        def emit():
            nonlocal previous
            value = json.dumps(render(query("monitors"), query("workspaces"), output))
            if value != previous:
                print(value, flush=True)
                previous = value
        emit()
        with sock.makefile() as events:
            for event in events:
                if event.partition(">>")[0] in EVENTS:
                    emit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--launch", action="store_true")
    mode.add_argument("--output")
    args = parser.parse_args()
    try:
        launch() if args.launch else stream(args.output)
    except BrokenPipeError:
        os._exit(0)
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        print(f"rowbar: {exc}", file=sys.stderr)
        sys.exit(1)
