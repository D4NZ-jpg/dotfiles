#!/usr/bin/env bash
# Lock the session with swaylock.
#
# The DP-1/VGA adapter sometimes comes up with a failed modeset and Hyprland
# reports it at 0x0. swaylock then aborts with "mmap failed: Invalid argument"
# on the zero-sized output, and with allow_session_lock_restore the session is
# left locked with no unlock UI. Disable-then-reload recovers the mode; if it
# still cannot, lock with that output disabled rather than not locking at all.
set -u
pidof swaylock >/dev/null && exit 0

zero_outputs() {
    hyprctl -j monitors 2>/dev/null | python3 -c '
import json, sys
print(" ".join(m["name"] for m in json.load(sys.stdin) if m["width"] == 0 or m["height"] == 0))'
}

bad=$(zero_outputs)
if [ -n "$bad" ]; then
    for m in $bad; do
        hyprctl eval "hl.monitor({ output = \"$m\", disabled = true })" >/dev/null 2>&1
    done
    sleep 0.5
    hyprctl reload >/dev/null 2>&1
    sleep 2
    bad=$(zero_outputs)
    for m in $bad; do
        hyprctl eval "hl.monitor({ output = \"$m\", disabled = true })" >/dev/null 2>&1
    done
    [ -n "$bad" ] && sleep 0.5
fi
exec swaylock "$@"
