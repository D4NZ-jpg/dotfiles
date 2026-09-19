#!/usr/bin/env bash
# Install the Tela icon theme, brown variant only, into ~/.local/share/icons.
# The Arch package ships every colour (300 MiB); upstream's installer builds
# just the variants asked for. Idempotent: skips when already present.
set -euo pipefail
dest="$HOME/.local/share/icons"
[ -d "$dest/Tela-brown-dark" ] && { echo "Tela-brown-dark already installed"; exit 0; }
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
git clone -q --depth 1 https://github.com/vinceliuice/Tela-icon-theme.git "$tmp/tela"
mkdir -p "$dest"
"$tmp/tela/install.sh" -d "$dest" brown
