#!/bin/sh
set -e
source $HOME/setup/scripts/utils.sh

# Config spicetify-cli (spotify)
if isInstalled spotify && isInstalled spicetify-cli; then
    sudo chmod a+wr /opt/spotify
    sudo chmod a+wr /opt/spotify/Apps -R


    # Theme
    cd ~/.config/spicetify/Themes
    rm -rf Spicetify Comfy 2>> /dev/null
    git clone https://github.com/Comfy-Themes/Spicetify --depth 1 --recursive
    mv Spicetify/Comfy .
    spicetify config current_theme Comfy
    spicetify config color_scheme Everforest
    spicetify config inject_css 1 replace_colors 1 overwrite_assets 1 inject_theme_js 1

    # Extensions (builtin)
    cd ~/.config/spicetify/Extensions
    spicetify config extensions loopyLoop.js
    spicetify config extensions trashbin.js

    # Adblock
    curl https://raw.githubusercontent.com/rxri/spicetify-extensions/main/adblock/adblock.js > adblock.js

    # Hide Podcast
    curl https://raw.githubusercontent.com/theRealPadster/spicetify-hide-podcasts/main/hidePodcasts.js > hidePodcast.js

    # Extensions (extra)
    for file in ~/.config/spicetify/Extensions/*; do
        if [ -f "$file" ]; then
            name=$(basename "$file")
            spicetify config extensions "$name"
        fi
    done

    # CustomApps
    spicetify config custom_apps lyrics-plus


    spicetify backup apply
    # Modify entry for live reload
    cp /usr/share/applications/spotify.desktop $HOME/.local/share/applications

    desktopFile=$HOME/.local/share/applications/spotify.desktop
    newCommand="spicetify -q watch -s"

    sed -i "/^Exec=/c\Exec=$newCommand" $desktopFile
fi
