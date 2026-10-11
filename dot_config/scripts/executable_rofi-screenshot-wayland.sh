#!/bin/sh
# Compatibility entry point: screenshot controls now live in the Quickshell panel.
if ! quickshell ipc -c panel call panel screenshot focused; then
    notify-send --app-name=Screenshot "Screenshot" "The Quickshell panel is not running" 2>/dev/null
    exit 1
fi
