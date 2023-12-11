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

# Copy discord css to correct folder 
mkdir -p ~/.config/VencordDesktop/VencordDesktop/theme
cp ~/.cache/wal/discord-wal-theme.css ~/.config/VencordDesktop/VencordDesktop/themes/pywal.theme.css

# Reload waybar
killall waybar
waybar

# Send update to firefox
pywalfox update

# Update spotify if spicetify installed (it will close it)
if command -v spicetify &> /dev/null; then
    spicetify apply
fi

