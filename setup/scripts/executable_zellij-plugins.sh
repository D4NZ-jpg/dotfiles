#!/usr/bin/env bash
set -euo pipefail
version=0.3.0
checksum=217e071b785981efda480b279d1a98e86da21971cf0bc7edd45f8b7c6359ab02
folder="${XDG_DATA_HOME:-$HOME/.local/share}/zellij/plugins"
target="$folder/zellij-autolock-$version.wasm"
mkdir -p "$folder"
if [[ -f $target ]] && printf '%s  %s\n' "$checksum" "$target" | sha256sum -c --status; then
    exit 0
fi
tmp=$(mktemp "$folder/.autolock.XXXXXX")
trap 'rm -f "$tmp"' EXIT
curl -fsSL --retry 2 "https://github.com/fresh2dev/zellij-autolock/releases/download/$version/zellij-autolock.wasm" -o "$tmp"
printf '%s  %s\n' "$checksum" "$tmp" | sha256sum -c --status
if [[ -e $target ]]; then
    backup="${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles-review/zellij-plugins-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup"
    cp -p "$target" "$backup/"
fi
chmod 644 "$tmp"
mv "$tmp" "$target"
