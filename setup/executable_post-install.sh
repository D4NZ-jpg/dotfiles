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

