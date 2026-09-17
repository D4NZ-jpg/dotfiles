# On-demand panel prototype

Requires Arch's `quickshell`, `networkmanager` (nmtui), and `kitty` packages
(recorded in setup/pkgs/pkgs.lst). NetworkManager must be running.

Start manually: `quickshell -c panel -d --no-duplicate`
Stop: `quickshell kill -c panel`
Preview: `quickshell ipc -c panel call panel preview true`
End preview: `quickshell ipc -c panel call panel preview false`
Inspect state: `quickshell ipc -c panel call panel status`
Logs: `quickshell log -c panel --no-color -t 50`

Starts automatically on Hyprland login, with duplicate-instance protection.
Each monitor has a 38px overlay, zero exclusive zone,
and a 2px input strip while hidden. Hover reveals after 120ms; leaving
hides after 280ms. Reveal/retract slides take 180ms. The panel never takes
keyboard focus.

Visibility is the union of hover, Rofi layer presence, ScrollOverview's
plugin-managed `scrolloverview` submap, the running network menu, and explicit preview. Layer queries
are debounced and event-driven, not polled. Startup queries recover existing
Rofi/submap state. The Hyprland config defines the overview submap using
upstream's documented keybind integration; the plugin owns entry and exit.

Current contents: minute-resolution clock, live Wi-Fi/Ethernet connection state,
PipeWire volume and Bluetooth power state. No workspace indicator.

- Network click opens NetworkManager's nmtui in Kitty; the bar stays revealed
  while that process runs. It is a terminal menu for now, not a custom QML menu.
- Volume click opens the existing volume scratchpad on the clicked monitor.
  Scroll changes volume in 5-point steps (0–100%); right-click toggles mute.
- Bluetooth click opens the existing Bluetooth scratchpad on the clicked monitor.
- Opening controls dismisses ScrollOverview first. No network, volume or Bluetooth
  setting is changed merely by revealing the bar.

Live click/scroll behavior still needs user verification.

Verified on Hyprland 0.56.2 / ScrollOverview 5e96ae20ec73 / Quickshell 0.3.1:
- two overlay-layer surfaces and zero reserved space on both monitors;
- actual overview open/close updates panel state;
- actual Rofi layer open/close updates panel state;
- no launch or Hyprland configuration errors.

Still needs user checks: edge-hover feel, pointer-driven overview exits,
visual stacking, fullscreen apps, monitor unplug/replug, and resource usage.
A hidden panel still has a two-pixel hover target at the top edge.
