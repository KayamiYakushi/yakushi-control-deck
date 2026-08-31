#!/usr/bin/env bash
set -u
options=$'Yakushi Control Deck\nLock\nLogout\nReboot\nShutdown'
choice=$(printf '%s\n' "$options" | rofi -dmenu -i -p 'POWER' -theme "$HOME/.config/rofi/config.rasi") || exit 0
case "$choice" in
  'Yakushi Control Deck') "$HOME/.local/bin/yakushi-deck" ;;
  Lock) if command -v hyprlock >/dev/null 2>&1; then hyprlock; else loginctl lock-session; fi ;;
  Logout) hyprctl dispatch exit ;;
  Reboot) systemctl reboot ;;
  Shutdown) systemctl poweroff ;;
esac
