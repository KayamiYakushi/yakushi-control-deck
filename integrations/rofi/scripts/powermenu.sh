#!/usr/bin/env bash
set -u

# Yakushi five-action power menu.
# Icons are SVG assets rendered by Rofi's element-icon widget, avoiding
# font glyph baseline/em-box differences entirely.
ICON_DIR="$HOME/.config/rofi/icons/power"
row() { printf '%s\0icon\x1f%s\n' "$1" "$2"; }

choice=$(
  {
    row lock "$ICON_DIR/lock.svg"
    row suspend "$ICON_DIR/suspend.svg"
    row logout "$ICON_DIR/logout.svg"
    row reboot "$ICON_DIR/reboot.svg"
    row shutdown "$ICON_DIR/shutdown.svg"
  } | rofi -dmenu -i -no-custom -show-icons -p '' -theme "$HOME/.config/rofi/powermenu.rasi"
) || exit 0

case "$choice" in
  lock)
    if command -v hyprlock >/dev/null 2>&1; then hyprlock; else loginctl lock-session; fi
    ;;
  suspend)
    if command -v hyprlock >/dev/null 2>&1; then
      nohup hyprlock >/tmp/yakushi-hyprlock.log 2>&1 &
      sleep 0.35
    else
      loginctl lock-session 2>/dev/null || true
    fi
    systemctl suspend
    ;;
  logout) hyprctl dispatch exit ;;
  reboot) systemctl reboot ;;
  shutdown) systemctl poweroff ;;
esac
