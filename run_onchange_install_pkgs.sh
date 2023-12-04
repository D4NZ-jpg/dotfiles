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
    "rofi"                     # App launcher

    "zsh"                      # Shell
    "starship"                 # Shell prompt
    "hyprland"                 # WM
    "way-displays"             # Set displays
    
    "swww"                     # Wallpaper setup
    "pywal-git"                # Colorschemes
    "waybar"                   # Infobar

    "wl-clipboard"             # Clipboard manager
    "wlogout"                  # Logout menu
    "swaylock-effects-git"     # Lock screen
    "pavucontrol"              # Sound control
    "htop"                     # Task manager
    "dunst"                    # Notifications
    "neofetch"                 # Flexing
    "xorg-xwayland"             # Cserver (for compatibility)

    # Icons
    "oranchelo-icon-theme"

    # Bluetooth
    "blueman"
    "bluez"
    "bluez-utils"

    # Extra utils
    "ripgrep"
    "xdg-utils"
    "exa"

    # Rofi stuff
    "rofi-emoji"               # Emoji selector
    "rofi-calc"                # Calculator

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

# Discord install (with better discord)
if ! pacman -Qi discord &> /dev/null; then
    read -p "Do you want to intall discord? (y/n) " answer
    answer=${answer,,}

    if [[ $answer == "y" || $answer == "yes" ]]; then
        yay -S discord betterdiscordctl-git
        betterdiscordctl install
    fi
fi

# Spotify install (with spicetify)
if ! pacman -Qi spotify &> /dev/null; then
    read -p "Do you want to install spotify? (y/n) " answer
    answer=${answer,,}

    # Install spotify + spicetify
    if [[ $answer == "y" || $answer == "yes" ]]; then
        yay -S spotify spicetify-cli

        sudo chmod a+wr /opt/spotify
        sudo chmod a+wr /opt/spotify/Apps -R

        # log in
        spotify &> /dev/null&
        echo ""
        read -p "Please login to spotify to generate pref file..."

        spicetify config current_theme Dribbblish color_scheme pywal
        spicetify config inject_css 1 replace_colors 1 overwrite_assets 1 inject_theme_js 1
        spicetify backup apply
    fi
fi

# Set zsh as default shell
if [ "$SHELL" != "/usr/bin/zsh" ]; then
    sudo chsh -s /usr/bin/zsh $USER
    
    # Intall plugin manager (Zap)
    zsh <(curl -s https://raw.githubusercontent.com/zap-zsh/zap/master/install.zsh) --branch release-v1
    echo "Default shell has been changed, log in again to apply changes"
fi

systemctl enable bluetooth.service
