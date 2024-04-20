#!/bin/sh
set -e

source $HOME/setup/scripts/utils.sh

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

services=(pipewire pipewire-pulse wireplumber)
for service in "${services[@]}"; do
    if ! systemctl --user is-enabled "$service" &> /dev/null; then
        echo "Enabling and starting $service..."
        systemctl --user enable --now "$service"
    fi
done

# Some parts taken from: 
# https://github.com/prasanthrangan/hyprdots/blob/main/Scripts/install_pre.sh

# Grub
if isInstalled grub && [ -f /boot/grub/grub.cfg ]; then
    echo -e "\033[0;32m[BOOTLOADER]\033[0m detected // grub"

    if [ ! -f /etc/default/grub.t2.bkp ] && [ ! -f /boot/grub/grub.t2.bkp ]; then
        sudo cp /etc/default/grub /etc/default/grub.t2.bkp
        sudo cp /boot/grub/grub.cfg /boot/grub/grub.t2.bkp

        # Nvidia setup
        if hasNvidia; then
            echo -e "\033[0;32m[BOOTLOADER]\033[0m nvidia detected, adding nvidia_drm.modeset=1 to boot option..."
            gcld=$(grep "^GRUB_CMDLINE_LINUX_DEFAULT=" "/etc/default/grub" | cut -d'"' -f2 | sed 's/\b nvidia_drm.modeset=.\b//g')
            sudo sed -i "/^GRUB_CMDLINE_LINUX_DEFAULT=/c\GRUB_CMDLINE_LINUX_DEFAULT=\"${gcld} nvidia_drm.modeset=1\"" /etc/default/grub
        fi

        # Theme
        read -p "Apply GRUB theme? [y/N]: " theme 
        if [[ $theme = [Yy] ]]; then
            sudo sed -i "/^GRUB_DEFAULT=/c\GRUB_DEFAULT=saved
            /^GRUB_GFXMODE=/c\GRUB_GFXMODE=1280x1024x32,auto
            /^#GRUB_THEME=/c\GRUB_THEME=\"$HOME/setup/grub/themes/minegrub-world-selection/theme.txt\"
            /^#GRUB_DISABLE_OS_PROBER=/c\GRUB_DISABLE_OS_PROBER=false
            /^#GRUB_SAVEDEFAULT=true/c\GRUB_SAVEDEFAULT=true" /etc/default/grub
        else 
            echo -e "\033[0;32m[BOOTLOADER]\033[0m Skippinng grub theme..." 
            sudo sed -i "s/^GRUB_THEME=/#GRUB_THEME=/g" /etc/default/grub 
        fi

        sudo grub-mkconfig -o /boot/grub/grub.cfg
    else
        echo -e "\033[0;32m[BOOTLOADER]\033[0m grub is already configured..."
    fi
fi
