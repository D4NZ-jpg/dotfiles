#!/usr/bin/env bash
# Main install script. (Arch Linux)
# By: Danz (inspired by prasanthrangan/hyprdots)
echo "dotfiles by Danz. (I use Arch btw)"
set -eo pipefail

if (( EUID == 0 )); then
    echo 'Run the installer as your normal user; privileged steps use sudo.' >&2
    exit 1
fi
source "$HOME/setup/scripts/utils.sh"
workdir=$(mktemp -d)
trap 'rm -rf -- "$workdir"' EXIT
install_list="$workdir/install.lst"
source "$HOME/setup/scripts/nvidia.sh"
command -v lspci >/dev/null || { echo 'Install pciutils before running setup.' >&2; exit 1; }
# Resolve the complete GPU plan before changing repositories or packages.
nvidia_packages=$(planNvidia "$HOME/setup/.nvidia")
nvidia_driver=${nvidia_packages%%$'\n'*}

# Install chaotic-aur
# Check if chaotic-aur is already installed
if ! grep -q "\[chaotic-aur\]" /etc/pacman.conf; then
    echo "Chaotic-aur not found, installing..."
    sudo pacman-key --recv-key 3056513887B78AEB --keyserver keyserver.ubuntu.com
    sudo pacman-key --lsign-key 3056513887B78AEB

    sudo pacman -U 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-keyring.pkg.tar.zst'
    sudo pacman -U 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-mirrorlist.pkg.tar.zst'

    echo -e "\n[chaotic-aur]\nInclude = /etc/pacman.d/chaotic-mirrorlist" | sudo tee -a /etc/pacman.conf
else
    echo "Chaotic-aur found, skipping..."
fi

# Set parallel downloads
sudo sed -i 's/#ParallelDownloads = 5/ParallelDownloads = 5/' /etc/pacman.conf

# Enable multilib (needed for lib32 Nvidia/Vulkan libs used by Steam/Wine)
if ! grep -q "^\[multilib\]" /etc/pacman.conf; then
    sudo sed -i '/^#\[multilib\]/,/^#Include/ s/^#//' /etc/pacman.conf
fi

# Refresh repositories only as part of a full system upgrade.
sudo pacman -Syu

# Keep the package queue independent of the caller's working directory.
cp "$HOME/setup/pkgs/pkgs.lst" "$install_list"

# Queue the selected driver family and headers; no driver configuration yet.
if [[ -n "$nvidia_driver" ]]; then
    printf '%s\n' "$nvidia_packages" >> "$install_list"
    shopt -s nullglob
    kernel_files=(/usr/lib/modules/*/pkgbase)
    shopt -u nullglob
    (( ${#kernel_files[@]} > 0 )) || { echo 'No installed kernel metadata found; cannot select DKMS headers.' >&2; exit 1; }
    for kernel_file in "${kernel_files[@]}"; do
        read -r kernel < "$kernel_file"
        printf '%s-headers\n' "$kernel" >> "$install_list"
    done
    printf 'Selected NVIDIA branch: %s\n' "$nvidia_driver"
else
    echo 'No NVIDIA display GPU detected; skipping driver setup.'
fi

# Ask for extras
echo ""
while IFS='|' read -r name packages || [[ -n "$name" ]]; do
    [[ -z "$name" || "$name" == \#* ]] && continue
    read -r -p "Would you like to install $name? [y/N]: " answer < /dev/tty
    if [[ $answer = [Yy] ]]; then
        read -r -a extra_packages <<< "$packages"
        printf '%s\n' "${extra_packages[@]}" >> "$install_list"
    fi
done < "$HOME/setup/pkgs/extras.lst"

# Install pkgs
installPkgs "$install_list"

# Driver packages must exist before service or initramfs configuration.
if [[ -n "$nvidia_driver" ]]; then
    configureNvidia "$nvidia_driver"
fi

# Configuring packages
source "$HOME/setup/scripts/post-install.sh"

# Systemd
while IFS= read -r service || [[ -n "$service" ]]; do
    [[ -z "$service" || "$service" == \#* ]] && continue
    startCtl "$service"
done < "$HOME/setup/pkgs/system_ctl.lst"

echo ""
echo "===================="
echo " [*] Everything configured without problems."
echo " [~] To configure spotify, log in then run ~/setup/scripts/spotify.sh"
