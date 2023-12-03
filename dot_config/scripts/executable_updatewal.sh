#!/bin/sh
# Select random wallpaper
wal -q -i ~/wallpapers -n

# Load pywal scheme
source "$HOME/.cache/wal/colors.sh"

# set wallpaper
swww img $wallpaper --transition-step 20 --transition-fps 20

# copy current file to ~/currentWallpaper
cp $wallpaper ~/.cache/currentWallpaper.jpg

# Update kitty
kill -USR1 $(pgrep kitty)
