#!/usr/bin/env bash
set -euo pipefail
DATA="$HOME/.config/yakushi-control-deck"
META="$DATA/install.json"
[[ -f "$META" ]] || { printf 'No Yakushi install metadata found.\n'; exit 1; }
BACKUP=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("backup", ""))' "$META")
[[ -d "$BACKUP" ]] || { printf 'Backup directory not found: %s\n' "$BACKUP"; exit 1; }
restore_one(){ local rel="$1" dest="$2"; [[ -e "$BACKUP/$rel" ]] || return 0; rm -rf "$dest"; mkdir -p "$(dirname "$dest")"; cp -a "$BACKUP/$rel" "$dest"; printf 'Restored %s\n' "$dest"; }
restore_one waybar/config.jsonc "$HOME/.config/waybar/config.jsonc"
restore_one waybar/style.css "$HOME/.config/waybar/style.css"
restore_one waybar/scripts "$HOME/.config/waybar/scripts"
restore_one rofi/config.rasi "$HOME/.config/rofi/config.rasi"
restore_one rofi/yakushi-opacity.rasi "$HOME/.config/rofi/yakushi-opacity.rasi"
restore_one rofi/scripts "$HOME/.config/rofi/scripts"
restore_one hypr/colors.css "$HOME/.config/hypr/colors.css"
restore_one hypr/colors.rasi "$HOME/.config/hypr/colors.rasi"
restore_one kitty/kitty.conf "$HOME/.config/kitty/kitty.conf"
restore_one kitty/yakushi-colors.conf "$HOME/.config/kitty/yakushi-colors.conf"
restore_one fastfetch/config.jsonc "$HOME/.config/fastfetch/config.jsonc"
restore_one fastfetch/logo.txt "$HOME/.config/fastfetch/logo.txt"
restore_one fastfetch/yakushi-logo.txt "$HOME/.config/fastfetch/yakushi-logo.txt"
pkill -x waybar 2>/dev/null || true
nohup waybar >/tmp/yakushi-waybar.log 2>&1 &
printf 'Latest pre-install desktop files restored.\n'
