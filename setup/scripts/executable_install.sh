#!/bin/sh
# Main install script. (Arch Linux)
# By: Danz (inspired by prasanthrangan/hyprdots)
echo "dotfiles by Danz. (I use Arch btw)"
set -e 

source "$HOME/setup/scripts/utils.sh"

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

# Install
cp "$HOME/setup/pkgs/pkgs.lst" "install.lst"

# Nvidia drivers (https://github.com/prasanthrangan/hyprdots/blob/main/Scripts/install.sh)
if hasNvidia; then
    cat /usr/lib/modules/*/pkgbase | while read krnl; do
        echo "${krnl}-headers" >>install.lst
    done
    IFS=$' ' read -r -d '' -a nvga < <(lspci -k | grep -E "(VGA|3D)" | grep -i nvidia | awk -F ':' '{print $NF}' | tr -d '[]()' && printf '\0')
    for nvcode in "${nvga[@]}"; do
        awk -F '|' -v nvc="$nvcode" '{if ($3 == nvc) {split(FILENAME,driver,"/"); print driver[length(driver)],"\nnvidia-utils"}}' "$HOME/setup/.nvidia/nvidia*dkms" >>install.lst
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
while read LINE; do
    name="${LINE%%|*}"; pkgs="${LINE#*|}"

    read -p "Would you like to install $name? [y/N]: " answer < /dev/tty
    if [[ $answer = [Yy] ]]; then
        for pkg in "${pkgs[@]}"; do
            echo "$pkg" >> install.lst 
        done
    fi
done < "$HOME/setup/pkgs/extras.lst"

# Install pkgs
installPkgs install.lst

# Configuring packages
source "$HOME/setup/scripts/post-install.sh"

# Systemd
while read service ; do
    startCtl "$service"
done < "$HOME/setup/pkgs/system_ctl.lst"

echo ""
echo "===================="
echo " [*] Everything configured without problems."
echo " [~] To configure spotify, log in then run ~/setup/scripts/spotify.sh"
