#!/usr/bin/env bash
set -u; fail=0
ok(){ printf '[ OK ] %s\n' "$*"; }; bad(){ printf '[FAIL] %s\n' "$*"; fail=1; }
for cmd in python3 hyprctl waybar rofi kitty pkexec; do command -v "$cmd" >/dev/null 2>&1 && ok "$cmd" || bad "$cmd not found"; done
for file in "$HOME/.config/waybar/config.jsonc" "$HOME/.config/waybar/style.css" "$HOME/.config/rofi/config.rasi" "$HOME/.config/hypr/colors.css" "$HOME/.config/hypr/colors.rasi"; do [[ -f "$file" ]] && ok "$file" || bad "$file missing"; done
python3 -c 'import json, pathlib; json.load(open(pathlib.Path.home()/".config/waybar/config.jsonc"))' >/dev/null 2>&1 && ok 'Waybar JSON parses' || bad 'Waybar JSON invalid'
rofi -no-config -theme "$HOME/.config/rofi/config.rasi" -dump-theme >/dev/null 2>&1 && ok 'Rofi theme validates' || bad 'Rofi theme invalid'
hyprctl -j monitors >/dev/null 2>&1 && ok 'Hyprland IPC responds' || bad 'Hyprland IPC unavailable'
[[ -x "$HOME/.local/bin/yakushi-deck" ]] && ok 'yakushi-deck launcher' || bad 'yakushi-deck launcher missing'
printf '\n'; ((fail)) && { printf 'Diagnostics found problems.\n'; exit 1; }; printf 'All core checks passed.\n'
