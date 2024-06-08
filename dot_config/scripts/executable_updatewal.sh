#!/bin/sh
set -e

# Select random wallpaper
wal --cols16 -q -i ~/wallpapers -n -s

# Load pywal scheme
source "$HOME/.cache/wal/colors.sh"
cp "$HOME/.cache/wal/colors.Xresources" "$HOME/.Xresources"

# set wallpaper
swww img $wallpaper --transition-step 20 --transition-fps 20

# copy current file to ~/currentWallpaper
cp $wallpaper ~/.cache/currentWallpaper.jpg

# Update kitty
kill -USR1 $(pgrep kitty)

# Copy discord css to correct folder 
mkdir -p ~/.config/vesktop/themes
cp ~/.cache/wal/discord-wal-theme.css ~/.config/vesktop/themes/pywal.theme.css


# Reload waybar
killall waybar
waybar

# Send update to firefox
pywalfox update

# Update spotify if spicetify installed (it will close it)
if command -v spicetify &> /dev/null; then
    spicetify apply
fi

