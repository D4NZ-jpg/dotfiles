#!/bin/sh

# Install git if not installed
if ! pacman -Qi git &> /dev/null; then
    echo "Installing git..."
    sudo pacman -S git
fi    

# Install yay if not installed
if ! pacman -Qi yay &> /dev/null; then
    echo "Installing yay..."
    cd /tmp/
    git clone https://aur.archlinux.org/yay.git
    cd yay
    makepkg -si
fi

pkgs=(
    "kitty"        # Terminal
    "lf"           # File explorer (TUI)
    "firefox"      # Browser

    "hyprland"     # WM
    "way-displays" # Set displays
    
    "swww"         # Wallpaper setup
    "python-pywal" # Colorschemes

    "waybar"       # Infobar
    "wl-clipboard" # Clipboard manager

    # Extra utils
    "ripgrep"
    "xdg-utils"


    # Some fonts used on my configs
    "ttf-firacode-nerd"
)

# Install all pkgs
output=""
for pkg in "${pkgs[@]}"; do
    if ! pacman -Qi "$pkg" &> /dev/null; then
        output+="$pkg "
    fi
done

if [ "$output" != "" ]; then
    echo "Installing missing packages..."
    echo "$output"
    yay -S $output
fi
