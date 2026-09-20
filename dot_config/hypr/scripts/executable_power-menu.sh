#!/usr/bin/env bash
# Power menu in Rofi: j/k or the underlined letter, Enter, Esc.
set -u
choice=$(printf '%s\n' \
    '󰌾   Lock' '󰒲   Suspend' '󰍃   Logout' '󰜉   Reboot' '󰐥   Shutdown' \
    | rofi -dmenu -i -p '' -no-custom -theme-str '
        window { width: 320px; }
        listview { lines: 5; }
        inputbar { enabled: false; }
        element-text { horizontal-align: 0; }' \
        -kb-row-down 'j,Down' -kb-row-up 'k,Up' -kb-cancel 'q,Escape' \
        -kb-remove-char-back 'BackSpace' -kb-accept-entry 'Return,KP_Enter,l')
case "$choice" in
    *Lock) exec "$HOME/.config/hypr/scripts/lock.sh" ;;
    *Suspend) exec systemctl suspend ;;
    *Logout) exec loginctl terminate-user "$USER" ;;
    *Reboot) exec systemctl reboot ;;
    *Shutdown) exec systemctl poweroff ;;
esac
