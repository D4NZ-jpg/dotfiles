#!/bin/sh
set -e

isInstalled(){
    local pkg=$1
    if pacman -Qi $pkg &> /dev/null; then
        return 0 # Installed
    else
        return 1 # Not installed
    fi
}

# (https://github.com/prasanthrangan/hyprdots/blob/main/Scripts)
hasNvidia(){
    if [ `lspci -k | grep -A 2 -E "(VGA|3D)" | grep -i nvidia | wc -l` -gt 0 ]; then
        return 0 # Has nvidia
    else
        return 1 # No nvidia
    fi
}

# (https://github.com/prasanthrangan/hyprdots/blob/main/Scripts)
enableCtl(){
    local ServChk=$1

    if [[ $(systemctl list-units --all -t service --full --no-legend "${ServChk}.service" | sed 's/^\s*//g' | cut -f1 -d' ') == "${ServChk}.service" ]]
    then
        echo "$ServChk service is already enabled, enjoy..."
    else
        echo "$ServChk service is not running, enabling..."
        sudo systemctl enable ${ServChk}.service
        sudo systemctl start ${ServChk}.service
        echo "$ServChk service enabled, and running..."
    fi
}

installPkgs(){
    file=$1
    # Install git if missing
    if ! isInstalled git; then
        echo "Installing git..."
        sudo pacman -S git
    fi

    # Install yay for AUR Helper if missing
    if ! isInstalled yay; then
        echo "Installing AUR Helper (yay)"
        cd /tmp
        git clone https://aur.archlinux.org/yay.git; cd yay
        makepkg -si
    fi

    echo "Installing packages..."
    local pkg2Install=()

    while read -r pkg; do
        if ! isInstalled "$pkg"; then
            pkg2Install+=("$pkg")
        fi
    done < "$file"
    yay -S -q "${pkg2Install[@]}"
}
