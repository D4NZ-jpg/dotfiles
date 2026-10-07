#!/usr/bin/env bash
set -euo pipefail
version=0.45.1
commit=efd8fd5a89a20c07a111d248ad7fce53848d2c18
rust_version=1.95.0
spec="$(cd "$(dirname "$0")/../zellij-workspace-bar" && pwd)"
state="${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles-review/workspace-bar-build"
folder="${XDG_DATA_HOME:-$HOME/.local/share}/zellij/plugins"
target="$folder/workspace-bar-$version.wasm"
mkdir -p "$state" "$folder"
chmod 700 "$state"
exec 9>"$state/install.lock"
flock 9
fingerprint=$(printf '%s\n' "$commit" "$rust_version"; sha256sum "$0" "$spec/Cargo.toml" "$spec/Cargo.lock" "$spec/workspace-name.patch" "$spec/upstream.sha256" "$spec/grant-ui-permissions.py")
fingerprint=$(printf '%s' "$fingerprint" | sha256sum | cut -d' ' -f1)
receipt="$state/installed.sha256"
if [[ -f $receipt && -f $target && ! -L $target ]]; then
    read -r saved_fingerprint saved_hash < "$receipt"
    if [[ $saved_fingerprint == "$fingerprint" ]] && printf '%s  %s\n' "$saved_hash" "$target" | sha256sum -c --status; then
        python3 "$spec/grant-ui-permissions.py" "$target"
        exit 0
    fi
fi
command -v rustup >/dev/null || { printf '%s\n' 'workspace-bar: rustup is required (no system changes will be made)' >&2; exit 1; }
export RUSTUP_HOME="$state/rustup" CARGO_HOME="$state/cargo" CARGO_BUILD_JOBS=2
rustup toolchain install "$rust_version" --profile minimal --target wasm32-wasip1 --no-self-update
source_dir="$state/source"
mkdir -p "$source_dir/src"
base="https://raw.githubusercontent.com/zellij-org/zellij/$commit"
for name in main line tab; do
    curl -fsSL --retry 2 "$base/default-plugins/tab-bar/src/$name.rs" -o "$source_dir/src/$name.rs"
done
curl -fsSL --retry 2 "$base/LICENSE.md" -o "$source_dir/LICENSE.md"
(cd "$source_dir" && sha256sum -c "$spec/upstream.sha256")
(cd "$source_dir" && patch --batch --forward -p1 < "$spec/workspace-name.patch")
cp "$spec/Cargo.toml" "$spec/Cargo.lock" "$source_dir/"
# A stable target directory permits cached builds without touching global Cargo.
export CARGO_TARGET_DIR="$state/target"
rustup run "$rust_version" cargo build --manifest-path "$source_dir/Cargo.toml" --release --locked --target wasm32-wasip1
built="$CARGO_TARGET_DIR/wasm32-wasip1/release/workspace-bar.wasm"
[[ $(od -An -tx1 -N4 "$built" | tr -d ' \n') == 0061736d ]] || { printf '%s\n' 'workspace-bar: invalid wasm output' >&2; exit 1; }
if [[ -e $target ]]; then
    backup="${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles-review/workspace-bar-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup"
    cp -p "$target" "$backup/"
fi
tmp=$(mktemp "$folder/.workspace-bar.XXXXXX")
trap 'rm -f "$tmp"' EXIT
cp "$built" "$tmp"
chmod 644 "$tmp"
mv "$tmp" "$target"
hash=$(sha256sum "$target" | cut -d' ' -f1)
printf '%s %s\n' "$fingerprint" "$hash" > "$receipt"
python3 "$spec/grant-ui-permissions.py" "$target"
printf 'Installed workspace-bar %s (%s)\n' "$version" "$hash"
