# On-demand panel prototype

Requires Quickshell 0.3.1 or newer and NetworkManager
(recorded in setup/pkgs/pkgs.lst). NetworkManager must be running.

Start manually: `quickshell -c panel -d --no-duplicate`
Stop: `quickshell kill -c panel`
Preview: `quickshell ipc -c panel call panel preview true`
End preview: `quickshell ipc -c panel call panel preview false`
Inspect state: `quickshell ipc -c panel call panel status`
Toggle popups: `quickshell ipc -c panel call panel network HDMI-A-2`,
`... sync HDMI-A-2`,
`... volume focused` (`focused` resolves the active Hyprland monitor)
Close the open popup: `quickshell ipc -c panel call panel network ''`
Logs: `quickshell log -c panel --no-color -t 50`

Starts automatically on Hyprland login, with duplicate-instance protection.
Each monitor has a 38px overlay, zero exclusive zone,
and a 2px input strip while hidden. Hover reveals after 120ms; leaving
hides after 280ms. Reveal/retract slides take 180ms. The panel never takes
keyboard focus; the network popup uses on-demand keyboard focus and a
Hyprland focus grab only while open. Exclusive focus would route all pointer
input to the popup and break outside-click dismissal.

Visibility is the union of hover, Rofi layer presence, ScrollOverview's
plugin-managed `scrolloverview` submap, the open network popup, and explicit preview. Layer queries
are debounced and event-driven, not polled. Startup queries recover existing
Rofi/submap state. The Hyprland config defines the overview submap using
upstream's documented keybind integration; the plugin owns entry and exit.

Current contents: minute-resolution clock, live Wi-Fi/Ethernet connection state,
PipeWire volume and Bluetooth power state. No workspace indicator.

- Network click toggles a themed popup on that monitor. Escape, Close, or a click
  outside the popup/bar dismisses it. Only one network popup is open at a time.
  The bar stays revealed while it is open.
- Volume click toggles a themed popup on that monitor; Super+Ctrl+V opens it
  on the focused monitor. Scroll on the bar label changes the default sink in
  5-point steps (0–100%); right-click toggles mute.
- Bluetooth click toggles a themed popup on that monitor; Super+Ctrl+B opens it
  on the focused monitor.
- Opening controls dismisses ScrollOverview first. No network, volume or Bluetooth
  setting is changed merely by revealing the bar. No scratchpads remain in use
  by the bar; the terminal scratchpad (Super+A) is unrelated.

Only one popup is open at a time; opening another replaces it. Both share
`PanelPopup.qml` for placement, focus and dismissal.

## Volume popup

Uses `Quickshell.Services.Pipewire`. Lists output and input devices with
volume sliders and mute, marks the default device and lets you pick another
when several exist, and shows per-application streams. Sliders allow up to
150% because PipeWire permits it. Opening changes nothing; nodes are bound
only while the popup is open. `pavucontrol` is no longer used by the desktop
but remains installed for advanced routing.

## Bluetooth popup

Uses `Quickshell.Bluetooth`. Shows adapter power with a toggle, paired devices
(connect, disconnect, forget, battery) and a fixed-height scrolling list of
named nearby devices discovered while the popup is open. Discovery stops on
close. Pairing works for devices that need no PIN or confirmation; Quickshell
has no pairing agent, so devices that require one must be paired in
`blueman-manager`, which stays installed. Pairing does not mark devices trusted.

## Network popup

Uses `Quickshell.Networking` directly. It shows Ethernet link status, Wi-Fi
networks, signal strength, saved/connected state, and internet connectivity.
Wi-Fi can be toggled; connections can be activated or disconnected explicitly.
Scanning runs only while the popup is open and stops on close.
No network settings change merely from opening the popup.

Connections try saved credentials first. WPA/WPA2 personal and WPA3 SAE prompt
for a password if needed. Passwords go directly to the native API, never through
shell arguments, files, or logging. The field clears on submit, cancel, and close.
NetworkManager may save credentials in its own connection profile.
Closing does not cancel an in-progress connection attempt.

Saved enterprise profiles can connect, but new enterprise/hidden networks, VPNs,
IP/DNS settings, and credential management still need an external NetworkManager
editor. There is no automatic fallback to nmtui and no additional dependency.

The popup does not bypass Rofi's exclusive input grab. Opening Rofi or overview
closes it. Connection/password handling has synthetic tests in
`tests/quickshell-network.qml`; a real network switch is deliberately not part
of validation. Run from the repository with:
`python3 tests/quickshell-panel.py`.
The runner copies the components and fixtures to a temporary offscreen shell.
23 network checks cover scanning, saved credentials, password retry/clearing,
security types, connection feedback, and closing without disconnecting;
13 volume checks cover node classification, labels, slider/volume sync,
default-device selection and that opening never mutes anything; 18 Bluetooth
checks cover list filtering, discovery start/stop without duplicate writes,
and connect/disconnect/pair/forget routing without trusting devices.

Verified on Hyprland 0.56.2 / ScrollOverview 5e96ae20ec73 / Quickshell 0.3.1:
- two overlay-layer surfaces and zero reserved space on both monitors;
- actual overview open/close updates panel state;
- actual Rofi layer open/close updates panel state;
- no launch or Hyprland configuration errors;
- network popup opens on either monitor, switches monitors, and closes via Escape
  or IPC; scanning stops on close and the existing active connections are unchanged.

Still needs user checks: edge-hover feel, pointer-driven overview exits,
visual stacking, fullscreen apps, monitor unplug/replug, and resource usage.
A hidden panel still has a two-pixel hover target at the top edge.

## Sync indicator

`SYNC` on the left of the status cluster reflects the git handoff system and
Syncthing. `sync-status.py` (run by the panel every 2 min and when the popup
opens; local only, about a second) merges three sources into
`~/.local/state/projects/panel-status.json`:

- `handoff-status.json`, written by `projects handoff` (clean / pushed /
  error / skipped, last success time)
- WIP refs other machines pushed, already fetched by `projects incoming`
  (`refs/wip/<machine>/<worktree>` in each catalogued repo)
- Syncthing's REST API on localhost: per-folder state, pending items, errors

Label and colour: `SYNC` muted when idle; `SYNC …` cream while a folder is
syncing; `SYNC n` in the accent when n incoming worktrees wait (or a handoff
was skipped); `SYNC !` red when a handoff failed or a folder has errors.
The popup lists this machine's handoff state, a Syncthing summary with any
active or erroring folders, and the newest incoming worktrees, each with a
`resume` link. **Hand off** (`h`) runs `projects handoff`; **Resume all**
(`a`) runs `projects resume` for every incoming worktree. Neither ever uses
`--force`: a worktree with local edits is reported as "kept local edits"
and left alone, and taking the other machine's version is a deliberate
`projects resume --force <name>` in a terminal. `r` refreshes.
