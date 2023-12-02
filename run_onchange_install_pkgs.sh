#!/bin/sh

# Install git if not installed
if ! command -V git &> /dev/null
then
    echo "Installing git..."
    sudo pacman -S git
fi    

# Install yay if not installed
if ! command -V yay &> /dev/null
then
    echo "Installing yay..."
    cd /tmp/
    git clone https://aur.archlinux.org/yay.git
    cd yay
    makepkg -si
fi

declare -A pkgs
# pkgs["pkgname"]="command"
# pkgname: name in the AUR
# command: a provided command to check if it's installed

pkgs["kitty"]="kitty"
pkgs["lf"]="lf"
pkgs["firefox"]="firefox"
pkgs["hyprland"]="Hyprland"

# Install all pkgs
output=""
for pkg in "${!pkgs[@]}"; do
    cmd="${pkgs[$pkg]}"

    if ! command -V "$cmd" &> /dev/null
    then
        output+="$pkg "
    fi
done

if [ "$output" != "" ]; then
    echo "Installing missing packages..."
    yay -S $output
fi
