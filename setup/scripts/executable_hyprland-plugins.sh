#!/usr/bin/env bash
# Run as the desktop user from a terminal; hyprpm manages its privileged cache.
# Tested: Hyprland 0.56.2, ScrollOverview 5e96ae20ec73.
# Do not pin across Hyprland updates: hyprpm selects upstream compatibility pins.
set -euo pipefail

if (( EUID == 0 )); then
    echo 'Run this script as your normal desktop user, not with sudo.' >&2
    exit 1
fi
if [[ -z ${HYPRLAND_INSTANCE_SIGNATURE:-} ]]; then
    echo 'Log into Hyprland, then run ~/setup/scripts/hyprland-plugins.sh.' >&2
    exit 1
fi
command -v hyprpm >/dev/null
sudo -v
hyprpm update
repos=$(hyprpm list)
if ! grep -Fq 'Repository hyprland-scroll-overview ' <<< "$repos"; then
    hyprpm add https://github.com/yayuuu/hyprland-scroll-overview
fi
hyprpm enable scrolloverview
