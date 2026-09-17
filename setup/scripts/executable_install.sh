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

# Refresh repositories only as part of a full system upgrade.
sudo pacman -Syu

# Keep the package queue independent of the caller's working directory.
cp "$HOME/setup/pkgs/pkgs.lst" "$install_list"

# Nvidia drivers (https://github.com/prasanthrangan/hyprdots/blob/main/Scripts/install.sh)
if hasNvidia; then
    cat /usr/lib/modules/*/pkgbase | while read krnl; do
        echo "${krnl}-headers" >>"$install_list"
    done
    IFS=$' ' read -r -d '' -a nvga < <(lspci -k | grep -E "(VGA|3D)" | grep -i nvidia | awk -F ':' '{print $NF}' | tr -d '[]()' && printf '\0')
    for nvcode in "${nvga[@]}"; do
        awk -F '|' -v nvc="$nvcode" '{if ($3 == nvc) {split(FILENAME,driver,"/"); print driver[length(driver)],"\nnvidia-utils"}}' "$HOME/setup/.nvidia/nvidia*dkms" >>"$install_list"
    done
    echo -e "\033[0;32m[GPU]\033[0m: detected // ${nvga[@]}"

    # Preserve video memory on suspend
    enableCtl nvidia-suspend
    enableCtl nvidia-hibernate
    enableCtl nvidia-resume

    if ! grep -Fxq "options nvidia NVreg_PreserveVideoMemoryAllocations=1" /etc/modprobe.d/nvidia.conf; then
        echo "options nvidia NVreg_PreserveVideoMemoryAllocations=1" | sudo tee -a /etc/modprobe.d/nvidia.conf > /dev/null
        sudo update-initramfs -u
    fi
else
    echo "No Nvidia Card detected, skipping Nvidia drivers..."
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
