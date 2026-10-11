#!/usr/bin/env python3
"""Hyprland screenshot backend. No image bytes or window titles are logged."""
import argparse
from datetime import datetime
import fcntl
import json
import math
import os
from pathlib import Path
import re
import signal
import struct
import subprocess
import tempfile
import time


class CaptureError(Exception):
    pass


class Cancelled(Exception):
    pass


def run(command, *, data=None, stdin=None, collect=True, timeout=10):
    # Never inherit the launcher's stdin: Quickshell passes an open pipe, and
    # tools such as slurp read stdin until EOF when it is not a terminal.
    if data is None and stdin is None:
        stdin = subprocess.DEVNULL
    try:
        result = subprocess.run(command, input=data, stdin=stdin,
                                stdout=subprocess.PIPE if collect else subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, timeout=timeout)
    except FileNotFoundError:
        raise CaptureError(f"Required command not found: {command[0]}") from None
    except subprocess.TimeoutExpired:
        raise CaptureError(f"{command[0]} timed out") from None
    if result.returncode:
        raise CaptureError(f"{command[0]} failed")
    return result.stdout


def hypr(query):
    try:
        return json.loads(run(["hyprctl", "-j", query]))
    except (ValueError, TypeError):
        raise CaptureError("Invalid compositor response") from None


def geometry(rect):
    return f"{rect[0]},{rect[1]} {rect[2]}x{rect[3]}"


def parse_geometry(value):
    match = re.fullmatch(r"(-?\d+),(-?\d+) (\d+)x(\d+)", value.strip())
    if not match:
        raise CaptureError("Invalid selection geometry")
    rect = tuple(map(int, match.groups()))
    if rect[2] <= 0 or rect[3] <= 0:
        raise CaptureError("Empty selection")
    return rect


def monitor_rect(monitor):
    # Hyprland reports physical mode size; clients/slurp use logical coordinates.
    width, height = monitor["width"], monitor["height"]
    if monitor.get("transform", 0) % 2:
        width, height = height, width
    scale = monitor.get("scale", 1)
    if scale <= 0:
        raise CaptureError("Invalid monitor scale")
    return (monitor["x"], monitor["y"], round(width / scale), round(height / scale))


def intersection(a, b):
    x, y = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[0] + a[2], b[0] + b[2]), min(a[1] + a[3], b[1] + b[3])
    if right <= x or bottom <= y:
        return None
    return (x, y, right - x, bottom - y)


def window_candidates(clients, monitors):
    candidates = {}
    outputs = []
    visible = set()
    for monitor in monitors:
        if monitor.get("disabled") or monitor.get("mirrorOf", "none") not in ("none", "", None):
            continue
        outputs.append(monitor_rect(monitor))
        visible.add(monitor.get("activeWorkspace", {}).get("id"))
        special = monitor.get("specialWorkspace", {}).get("id", 0)
        if special:
            visible.add(special)
    visible.discard(None)
    for client in clients:
        if not client.get("mapped") or client.get("hidden"):
            continue
        if client.get("workspace", {}).get("id") not in visible and not client.get("pinned"):
            continue
        at, size = client.get("at", []), client.get("size", [])
        if len(at) != 2 or len(size) != 2 or min(size) <= 0:
            continue
        # Round outward, then clip to connected outputs. Spanning windows retain
        # their visible portions on both screens rather than selecting half a window.
        x, y = math.floor(at[0]), math.floor(at[1])
        rect = (x, y, math.ceil(at[0] + size[0]) - x, math.ceil(at[1] + size[1]) - y)
        pieces = [piece for output in outputs if (piece := intersection(rect, output))]
        if pieces:
            left, top = min(p[0] for p in pieces), min(p[1] for p in pieces)
            right, bottom = max(p[0] + p[2] for p in pieces), max(p[1] + p[3] for p in pieces)
            clipped = (left, top, right - left, bottom - top)
            candidates.setdefault(geometry(clipped), []).append(client.get("address"))
    return candidates


def select(options=None):
    command = ["slurp", "-f", "%x,%y %wx%h"]
    if options is not None:
        command.append("-r")
    try:
        if options is None:
            result = subprocess.run(command, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        else:
            result = subprocess.run(command, input=("\n".join(options) + "\n").encode(),
                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        raise CaptureError("Required command not found: slurp") from None
    if result.returncode or not result.stdout.strip():
        raise Cancelled()
    try:
        return geometry(parse_geometry(result.stdout.decode()))
    except UnicodeError:
        raise CaptureError("Invalid selection") from None


def wait_for_toolbar():
    deadline = time.monotonic() + 2
    while True:
        layers = hypr("layers")
        found = any(surface.get("namespace") == "dan-screenshot"
                    for monitor in layers.values()
                    for surfaces in monitor.get("levels", {}).values()
                    for surface in surfaces)
        if not found:
            # Allow the compositor to present the frame after unmapping.
            time.sleep(0.06)
            return
        if time.monotonic() >= deadline:
            raise CaptureError("Screenshot toolbar is still visible; try again")
        time.sleep(0.02)


def capture_args(mode, monitor):
    if mode == "screen":
        monitors = hypr("monitors")
        chosen = next((m for m in monitors if m["name"] == monitor), None) if monitor else next(
            (m for m in monitors if m.get("focused")), None)
        if not chosen or chosen.get("disabled"):
            raise CaptureError("Selected screen is unavailable")
        return ["-o", chosen["name"]]
    if mode == "region":
        return ["-g", select()]
    monitors, clients = hypr("monitors"), hypr("clients")
    candidates = window_candidates(clients, monitors)
    if not candidates:
        raise CaptureError("No visible windows to select")
    selected = select(list(candidates))
    if selected not in candidates:
        raise CaptureError("Selection is not a visible window")
    # A window may have moved or closed during selection. Never capture its old location.
    current = window_candidates(hypr("clients"), hypr("monitors"))
    if not set(candidates[selected]).intersection(current.get(selected, [])):
        raise CaptureError("Window changed during selection; try again")
    return ["-g", selected]


def validate_png(path):
    with path.open("rb") as image:
        header = image.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise CaptureError("Capture did not produce a PNG")
    if 0 in struct.unpack(">II", header[16:24]):
        raise CaptureError("Capture produced an empty PNG")


def save_png(image):
    pictures = run(["xdg-user-dir", "PICTURES"]).decode().strip()
    if not pictures or not Path(pictures).is_absolute():
        raise CaptureError("XDG Pictures directory is unavailable")
    directory = Path(pictures) / "Screenshots"
    directory.mkdir(parents=True, exist_ok=True)
    name = "Screenshot-" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f") + ".png"
    destination = directory / name
    # Write privately in the destination filesystem, then publish without overwriting.
    fd, staging = tempfile.mkstemp(prefix=".screenshot-", suffix=".png", dir=directory)
    try:
        with os.fdopen(fd, "wb") as output, image.open("rb") as source:
            import shutil
            shutil.copyfileobj(source, output)
            output.flush()
            os.fsync(output.fileno())
        os.link(staging, destination)
    finally:
        Path(staging).unlink(missing_ok=True)
    return destination


def notify(message):
    try:
        subprocess.run(["notify-send", "--app-name=Screenshot", "Screenshot", message],
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3)
    except (OSError, subprocess.TimeoutExpired):
        pass


def execute(args):
    wait_for_toolbar()
    command = ["grim", "-t", "png", *capture_args(args.mode, args.monitor)]
    with tempfile.TemporaryDirectory(prefix="screenshot-") as directory:
        image = Path(directory) / "capture.png"
        run([*command, str(image)])
        validate_png(image)
        saved = save_png(image) if args.destination in ("folder", "both") else None
        if args.destination in ("clipboard", "both"):
            try:
                with image.open("rb") as source:
                    run(["wl-copy", "--type", "image/png"], stdin=source, collect=False)
            except CaptureError:
                if saved:
                    raise CaptureError(f"Saved to {saved}, but clipboard copy failed") from None
                raise
        notify(f"Saved to {saved}" + (" and copied to clipboard" if args.destination == "both" else "")
               if saved else "Copied to clipboard")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("screen", "window", "region"))
    parser.add_argument("destination", choices=("clipboard", "folder", "both"))
    parser.add_argument("--monitor", default="")
    args = parser.parse_args()
    os.umask(0o077)
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: (_ for _ in ()).throw(Cancelled()))
    try:
        state = Path(os.environ.get("XDG_RUNTIME_DIR", str(Path.home() / ".cache"))) / "dan-screenshot"
        state.mkdir(mode=0o700, parents=True, exist_ok=True)
        with (state / "capture.lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise CaptureError("A screenshot selection is already in progress") from None
            execute(args)
    except Cancelled:
        return 0
    except (CaptureError, OSError, ValueError, KeyError, TypeError) as error:
        # OSError diagnostics are paths/errno only, never child output or image content.
        notify(str(error) if isinstance(error, CaptureError) else "Screenshot failed; check folder permissions and compositor state")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
