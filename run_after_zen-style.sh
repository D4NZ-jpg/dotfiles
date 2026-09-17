#!/bin/sh
set -eu
# Discover profiles locally; no profile names or browsing data belong in dotfiles.
if [ -f "$HOME/.zen/profiles.ini" ]; then
    if ! command -v python3 >/dev/null 2>&1; then
        printf '%s\n' 'Zen styling requires Python 3. Install python, then run ~/.config/zen-style/apply.py.' >&2
        exit 1
    fi
    python3 "$HOME/.config/zen-style/apply.py"
fi
