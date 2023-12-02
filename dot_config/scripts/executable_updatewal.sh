#!/bin/sh
# Select random wallpaper
wal -q -i ~/wallpapers

# Load pywal scheme
source "$HOME/.cache/wal/colors.sh"

# set wallpaper
swww img $wallpaper --transition-step 20 --transition-fps 20
