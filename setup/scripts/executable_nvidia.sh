#!/usr/bin/env bash
# Sourced helpers. Planning is read-only; configuration runs only after install.

planNvidia() {
    local maps=$1 inventory line map arch code chip description driver='' match utils
    local found_gpu=false
    local -a matches=()
    inventory=$(lspci) || return 1
    shopt -s nullglob
    local -a files=("$maps"/nvidia*dkms)
    while IFS= read -r line; do
        [[ "$line" =~ (VGA|3D|Display).*NVIDIA ]] || continue
        found_gpu=true
        matches=()
        for map in "${files[@]}"; do
            while IFS='|' read -r arch code chip description; do
                [[ -n "$chip" ]] || continue
                if [[ "$line" =~ (^|[^[:alnum:]_])${chip}([^[:alnum:]_]|$) ]]; then
                    matches+=("${map##*/}")
                    break
                fi
            done < "$map"
        done
        if (( ${#matches[@]} != 1 )); then
            echo 'NVIDIA GPU has an unknown or ambiguous driver mapping; refusing automatic selection.' >&2
            return 1
        fi
        match=${matches[0]}
        case "$match" in
            nvidia-580xx-dkms|nvidia-open-dkms) ;;
            *) echo "Legacy driver $match requires a separate compatibility review." >&2; return 1 ;;
        esac
        if [[ -n "$driver" && "$driver" != "$match" ]]; then
            echo 'NVIDIA GPUs require different driver branches; manual selection is required.' >&2
            return 1
        fi
        driver=$match
    done <<< "$inventory"
    [[ "$found_gpu" == true ]] || return 0
    if [[ "$driver" == nvidia-open-dkms ]]; then utils=nvidia-utils; else utils=nvidia-580xx-utils; fi
    printf '%s\n%s\nlib32-%s\n' "$driver" "$utils" "$utils"
}

configureNvidia() {
    local driver=$1 utils unit config current package
    local modprobe_dir=${2:-/etc/modprobe.d}
    case "$driver" in
        nvidia-580xx-dkms) utils=nvidia-580xx-utils ;;
        nvidia-open-dkms) utils=nvidia-utils ;;
        *) echo 'Unexpected NVIDIA driver; refusing configuration.' >&2; return 1 ;;
    esac
    for package in "$driver" "$utils" "lib32-$utils"; do
        isInstalled "$package" || { echo "NVIDIA package missing: $package; configuration stopped." >&2; return 1; }
    done
    command -v mkinitcpio >/dev/null || return 1
    # Validate service availability before modifying anything.
    for unit in nvidia-suspend nvidia-hibernate nvidia-resume; do
        [[ $(systemctl show --property=LoadState --value "$unit.service") == loaded ]] || {
            echo "Missing $unit.service; configuration stopped." >&2; return 1;
        }
    done
    config=$(modprobe -c) || return 1
    if grep -Eq '^options[[:space:]]+nvidia[[:space:]].*NVreg_PreserveVideoMemoryAllocations=([^1[:space:]]|1[^[:space:]])' <<< "$config"; then
        echo 'Conflicting NVIDIA video-memory setting; review local modprobe configuration manually.' >&2
        return 1
    fi
    if ! grep -Eq '^options[[:space:]]+nvidia[[:space:]].*NVreg_PreserveVideoMemoryAllocations=1([[:space:]]|$)' <<< "$config"; then
        current="$modprobe_dir/90-dotfiles-nvidia.conf"
        if [[ -e "$current" || -L "$current" ]]; then
            echo 'Existing NVIDIA dotfiles configuration needs manual review; not overwriting it.' >&2
            return 1
        fi
        sudo install -d -m 755 "$modprobe_dir" || return
        printf '%s\n' 'options nvidia NVreg_PreserveVideoMemoryAllocations=1' | sudo tee "$current" >/dev/null || return
        sudo mkinitcpio -P || return
    fi
    for unit in nvidia-suspend nvidia-hibernate nvidia-resume; do
        # Enable for suspend hooks; do NOT start these one-shot services now.
        enableCtl "$unit" || return
    done
}
