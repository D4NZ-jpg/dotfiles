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
    "kitty"                    # Terminal
    "lf"                       # File explorer (TUI)
    "firefox"                  # Browser
    "wofi"                     # App launcher

    "zsh"                      # Shell
    "starship"                 # Shell prompt
    "hyprland"                 # WM
    "way-displays"             # Set displays
    
    "swww"                     # Wallpaper setup
    "python-pywal"             # Colorschemes
    "waybar"                   # Infobar

    "wl-clipboard"             # Clipboard manager
    "wlogout"                  # Logout menu
    "swaylock-effects-git"     # Lock screen
    "pavucontrol"              # Sound control
    "htop"                     # Task manager
    "neofetch"                 # Flexing

    # Bluetooth
    "blueman"
    "bluez"
    "bluez-utils"

    # Extra utils
    "ripgrep"
    "xdg-utils"
    "exa"


    # Some fonts used on my configs
    "ttf-firacode-nerd"
    "noto-fonts-emoji"
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

# Set zsh as default shell
if [ "$SHELL" != "/usr/bin/zsh" ]; then
    sudo chsh -s /usr/bin/zsh $USER
    
    # Intall plugin manager (Zap)
    zsh <(curl -s https://raw.githubusercontent.com/zap-zsh/zap/master/install.zsh) --branch release-v1
    echo "Default shell has been changed, log in again to apply changes"
fi

systemctl enable bluetooth.service
