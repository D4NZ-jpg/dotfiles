#!/usr/bin/env bash
set -euo pipefail

if (( EUID == 0 )); then
    echo 'Run Zen setup as your normal user; only policy installation uses sudo.' >&2
    exit 1
fi
if ! command -v zen-browser >/dev/null 2>&1; then
    echo 'Zen is not installed; skipping browser setup.'
    exit 0
fi
for command in python3 timeout sudo xdg-settings; do
    command -v "$command" >/dev/null 2>&1 || { echo "Missing required command: $command" >&2; exit 1; }
done
style="$HOME/.config/zen-style"
for file in apply.py theme.css install-addons.py addon-policies.json; do
    [[ -f "$style/$file" ]] || { echo 'Apply the Zen dotfiles before running setup.' >&2; exit 1; }
done

# Let Zen choose its own default profile and installation registry. No custom
# profile names, database copying, or hand-written profiles.ini/installs.ini.
if [[ ! -f "$HOME/.zen/profiles.ini" ]]; then
    tmp=$(mktemp -d)
    trap 'rm -rf -- "$tmp"' EXIT
    echo 'Initializing a local Zen profile (headless, about:blank only)...'
    if ! timeout 60s zen-browser --headless --no-remote --screenshot "$tmp/blank.png" about:blank >"$tmp/startup.log" 2>&1; then
        echo 'Zen initialization failed. Launch and close Zen once, then rerun this script.' >&2
        exit 1
    fi
    [[ -f "$HOME/.zen/profiles.ini" ]] || { echo 'Zen did not create its profile registry; no further changes made.' >&2; exit 1; }
fi

python3 "$style/apply.py"
# Interactive authentication belongs here, never inside the theme-only hook.
sudo python3 "$style/install-addons.py"
xdg-settings set default-web-browser zen.desktop
echo 'Zen setup complete. Restart Zen to load preferences and install addons.'
echo 'Bitwarden login, auto-lock and MFA remain manual; no account data is copied.'
