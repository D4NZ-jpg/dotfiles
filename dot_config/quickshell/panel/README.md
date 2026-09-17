# On-demand panel prototype

Requires Quickshell 0.3.1 or newer and NetworkManager
(recorded in setup/pkgs/pkgs.lst). NetworkManager must be running.

Start manually: `quickshell -c panel -d --no-duplicate`
Stop: `quickshell kill -c panel`
Preview: `quickshell ipc -c panel call panel preview true`
End preview: `quickshell ipc -c panel call panel preview false`
Inspect state: `quickshell ipc -c panel call panel status`
Toggle network popup: `quickshell ipc -c panel call panel network HDMI-A-2`
Close network popup: `quickshell ipc -c panel call panel network ''`
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
- Volume click opens the existing volume scratchpad on the clicked monitor.
  Scroll changes volume in 5-point steps (0–100%); right-click toggles mute.
- Bluetooth click opens the existing Bluetooth scratchpad on the clicked monitor.
- Opening controls dismisses ScrollOverview first. No network, volume or Bluetooth
  setting is changed merely by revealing the bar.

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
`python3 tests/quickshell-network.py`.
The runner copies the component and fixture to a temporary offscreen shell;
23 checks cover scanner restoration, saved credentials, password retry/clearing,
security types, connection feedback, and closing without disconnecting.

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
