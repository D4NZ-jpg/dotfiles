#!/usr/bin/env bash
# Install a pinned Deja release without importing shell history.
set -euo pipefail

version=0.4.2
platform=$(uname -s)
arch=$(uname -m)

case "$platform:$arch" in
    Linux:x86_64)
        target=linux_amd64
        checksum=32db767e728d447941a70cf7dc95376a1e0a96168ad79674593715ac165ed310
        ;;
    Linux:aarch64|Linux:arm64)
        target=linux_arm64
        checksum=2473d3fb0a82bb9e03f47b6817960e7b5b499f8904676104956c979b88f657f7
        ;;
    Darwin:x86_64)
        target=darwin_amd64
        checksum=74a2d9b817fd5d86a9e214e1d00364e24d435cbd1de15b70ff49c2837e66e714
        ;;
    Darwin:arm64)
        target=darwin_arm64
        checksum=cd9a55433c4b6c37fc83f000959928d785b65ea68059db88f844778dbd6b53ec
        ;;
    *)
        printf 'Unsupported Deja platform: %s %s\n' "$platform" "$arch" >&2
        exit 1
        ;;
esac

bin="$HOME/.local/bin/deja"
if [[ -x "$bin" && "$($bin --version 2>/dev/null)" == "deja $version "* ]]; then
    "$bin" init zsh >/dev/null
    printf 'Deja %s is already installed.\n' "$version"
    exit 0
fi

asset="deja_${version}_${target}.tar.gz"
url="https://github.com/Giammarco-Ferranti/deja/releases/download/v${version}/${asset}"
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT

curl -fL --retry 3 --retry-delay 1 -o "$tmp/$asset" "$url"
if command -v sha256sum >/dev/null 2>&1; then
    printf '%s  %s\n' "$checksum" "$tmp/$asset" | sha256sum -c -
elif command -v shasum >/dev/null 2>&1; then
    printf '%s  %s\n' "$checksum" "$tmp/$asset" | shasum -a 256 -c -
else
    echo 'Install sha256sum or shasum before installing Deja.' >&2
    exit 1
fi

tar -xzf "$tmp/$asset" -C "$tmp"
mkdir -p "$HOME/.local/bin"
install -m 0755 "$tmp/deja" "$bin"
"$bin" init zsh >/dev/null
printf 'Installed Deja %s for %s.\n' "$version" "$target"
