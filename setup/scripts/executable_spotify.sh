#!/bin/sh
set -e
source $HOME/setup/scripts/utils.sh

# Config spicetify-cli (spotify)
if isInstalled spotify && isInstalled spicetify-cli; then
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

    spicetify backup apply 


    # Modify entry for live reload
    cp /usr/share/applications/spotify.desktop $HOME/.local/share/applications

    desktopFile=$HOME/.local/share/applications/spotify.desktop
    newCommand="spicetify -q watch -s"

    sed -i "/^Exec=/c\Exec=$newCommand" $desktopFile
fi
