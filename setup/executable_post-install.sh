#!/bin/sh
set -e

source $HOME/setup/utils.sh

# Setup zathura as default pdf app
if isInstalled zathura; then
    xdg-mime default org.pwmt.zathura.desktop application/pdf
fi

# Set zsh as default shell
if isInstalled zsh && [ "$SHELL" != "/usr/bin/zsh" ]; then
    sudo chsh -s /usr/bin/zsh $USER

    # Intall plugin manager (Zap)
    zsh <(curl -s https://raw.githubusercontent.com/zap-zsh/zap/master/install.zsh) --branch release-v1
    echo "Default shell has been changed, log out to apply changes"
fi

# Config spicetify-cli (spotify)

if isInstalled spotify && isInstalled spicetify-cli; then
    spotify &> /dev/null & sleep 2
    killall spotify

    sudo chmod a+wr /opt/spotify
    sudo chmod a+wr /opt/spotify/Apps -R

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

    spicetify apply 


    # Modify entry for live reload
    cp /usr/share/applications/spotify.desktop $HOME/.local/share/applications

    desktopFile=$HOME/.local/share/applications/spotify.desktop
    newCommand="spicetify -q watch -s"

    sed -i "/^Exec=/c\Exec=$newCommand" $desktopFile
fi
