#!/usr/bin/env bash
# Lock the session with swaylock, recovering from a monitor that Hyprland
# reports at 0x0 (the DP-1/VGA adapter does this after some boots). swaylock
# fails with "mmap failed: Invalid argument" on a zero-sized output and, with
# allow_session_lock_restore, leaves the session locked with no unlock UI.
set -u
if pidof swaylock >/dev/null; then exit 0; fi
if hyprctl -j monitors 2>/dev/null | python3 -c '
import json, sys
sys.exit(0 if any(m["width"] == 0 or m["height"] == 0 for m in json.load(sys.stdin)) else 1)
' 2>/dev/null; then
    hyprctl reload >/dev/null 2>&1
    sleep 1
fi
exec swaylock "$@"
