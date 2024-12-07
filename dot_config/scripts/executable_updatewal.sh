#!/bin/sh
set -e

#Randomize wallpaper
cp "$(find $HOME/wallpapers -type f | shuf -n 1)" "$HOME/.cache/currentWallpaper.jpg"
matugen image $HOME/.cache/currentWallpaper.jpg
