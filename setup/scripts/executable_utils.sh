#!/usr/bin/env bash

isInstalled() {
    pacman -Q -- "$1" >/dev/null 2>&1
}

hasNvidia() {
    lspci | grep -Ei '(VGA|3D).*NVIDIA' >/dev/null
}

startCtl() {
    local unit="${1%.service}.service"
    if systemctl is-enabled --quiet "$unit" && systemctl is-active --quiet "$unit"; then
        printf '%s is enabled and running.\n' "$unit"
    else
        sudo systemctl enable --now "$unit"
    fi
}

enableCtl() {
    local unit="${1%.service}.service"
    if ! systemctl is-enabled --quiet "$unit"; then
        sudo systemctl enable "$unit"
    fi
}

installPkgs() {
    local file line pkg
    local -a words=() missing=()
    local -A seen=()
    file=$(realpath -- "$1") || return
    [[ -f "$file" ]] || { printf 'Package list not found.\n' >&2; return 1; }

    while IFS= read -r line || [[ -n "$line" ]]; do
        line=${line%%#*}
        words=()
        read -r -a words <<< "$line"
        for pkg in "${words[@]}"; do
            [[ -n ${seen[$pkg]:-} ]] && continue
            seen[$pkg]=1
            if ! isInstalled "$pkg"; then
                missing+=("$pkg")
            fi
        done
    done < "$file"

    if (( ${#missing[@]} == 0 )); then
        echo 'All requested packages are already installed.'
        return 0
    fi

    # The caller performs a full upgrade before entering this function.
    # Never refresh repositories here without also upgrading the system.
    if ! command -v yay >/dev/null 2>&1; then
        sudo pacman -S --needed git base-devel || return
        (
            set -e
            local build
            build=$(mktemp -d) || exit 1
            trap 'rm -rf -- "$build"' EXIT
            git clone https://aur.archlinux.org/yay.git "$build/yay" || exit 1
            cd "$build/yay" || exit 1
            makepkg -si || exit 1
        ) || return
    fi

    # Keep confirmations: AUR builds and package conflicts need user review.
    yay -S --needed -- "${missing[@]}"
}
