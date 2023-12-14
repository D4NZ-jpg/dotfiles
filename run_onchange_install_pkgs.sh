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
    "pywal-16-colors"          # Colorschemes
    "waybar"                   # Infobar
    "python-pywalfox"          # Firefox follow pywal

    "wl-clipboard"             # Clipboard manager
    "wlogout"                  # Logout menu
    "swaylock-effects-git"     # Lock screen
    "pavucontrol"              # Sound control
    "htop"                     # Task manager
    "dunst"                    # Notifications
    "neofetch"                 # Flexing
    "xorg-xwayland"            # Xserver (for compatibility)
    "zathura"                  # Document reader

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
    "bat"
    "zoxide"
    "fzf"
    "entr"                     # watch for file changes
    "ctpv-git"                 # lf image preview
    "zathura-pdf-mupdf"        # zathura pdf plugin
    "zathura-djvu"             # zathura djvu support
    "zaread-git"               # zathura office support

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

# Discord install (Vencord for screen sharing)
if ! pacman -Qi vencord-desktop-git &> /dev/null; then
    read -p "Do you want to intall discord (vencord)? (y/n) " answer
    answer=${answer,,}

    if [[ $answer == "y" || $answer == "yes" ]]; then
        yay -S vencord-desktop-git
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

        # Theme
        spicetify config current_theme Dribbblish color_scheme pywal
        spicetify config inject_css 1 replace_colors 1 overwrite_assets 1 inject_theme_js 1

        # Extensions (builtin)
        spicetify config extensions loopyLoop.js
        spicetify config extensions trashbin.js

        # Extensions (extra)
        for file in ~/.config/spicetify/Extensions/*; do
            if [ -f "$file" ]; then
                name=$(basename "$file") 
               spicetify config extensions "$name"
            fi
        done

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

# set zathura as default pdf app
xdg-mime default org.pwmt.zathura.desktop application/pdf

systemctl enable bluetooth.service
