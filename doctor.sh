#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$HOME/.local/share/yakushi-control-deck"
fail=0
ok(){ printf '[ OK ] %s\n' "$*"; }
bad(){ printf '[FAIL] %s\n' "$*"; fail=1; }
info(){ printf '[INFO] %s\n' "$*"; }

# Package/source integrity. Works from either a fresh clone/archive or the
# installed application directory.
if [[ -x "$ROOT/smoke-test.sh" ]]; then
  "$ROOT/smoke-test.sh" --quiet >/dev/null 2>&1 && ok 'Yakushi package integrity' || bad 'Yakushi package integrity failed (run ./smoke-test.sh)'
else
  info 'package smoke-test helper not present in this directory'
fi

for cmd in python3 hyprctl waybar rofi kitty pkexec; do
  command -v "$cmd" >/dev/null 2>&1 && ok "$cmd" || bad "$cmd not found"
done

python3 -c 'import gi; gi.require_version("GdkPixbuf","2.0"); from gi.repository import GdkPixbuf' >/dev/null 2>&1 \
  && ok 'GdkPixbuf Auto Color backend' || bad 'GdkPixbuf Python binding unavailable'
command -v nautilus >/dev/null 2>&1 && ok 'nautilus (optional integration)' || info 'nautilus not installed (Nautilus Studio remains optional)'

for file in \
  "$HOME/.config/waybar/config.jsonc" \
  "$HOME/.config/waybar/style.css" \
  "$HOME/.config/rofi/config.rasi" \
  "$HOME/.config/hypr/colors.css" \
  "$HOME/.config/hypr/colors.rasi"; do
  [[ -f "$file" ]] && ok "$file" || bad "$file missing"
done

VALIDATOR=""
for candidate in "$ROOT/tools/jsonc_check.py" "$TARGET/tools/jsonc_check.py"; do
  if [[ -f "$candidate" ]]; then VALIDATOR="$candidate"; break; fi
done
if [[ -f "$HOME/.config/waybar/config.jsonc" ]]; then
  if [[ -n "$VALIDATOR" ]]; then
    python3 "$VALIDATOR" "$HOME/.config/waybar/config.jsonc" >/dev/null 2>&1 \
      && ok 'Waybar JSONC validates' || bad 'Waybar JSONC invalid'
  else
    info 'Waybar JSONC validator unavailable'
  fi
fi

if [[ -f "$HOME/.config/rofi/config.rasi" ]]; then
  rofi -no-config -theme "$HOME/.config/rofi/config.rasi" -dump-theme >/dev/null 2>&1 \
    && ok 'Rofi theme validates' || bad 'Rofi theme invalid'
fi

hyprctl -j monitors >/dev/null 2>&1 && ok 'Hyprland IPC responds' || bad 'Hyprland IPC unavailable'
[[ -x "$HOME/.local/bin/yakushi-deck" ]] && ok 'yakushi-deck launcher' || bad 'yakushi-deck launcher missing'
command -v hyprlock >/dev/null 2>&1 && ok 'hyprlock' || bad 'hyprlock not found'

BUNDLED_SDDM=""
for candidate in "$ROOT/integrations/sddm/yakushi/Main.qml" "$TARGET/integrations/sddm/yakushi/Main.qml"; do
  if [[ -f "$candidate" ]]; then BUNDLED_SDDM="$candidate"; break; fi
done
[[ -n "$BUNDLED_SDDM" ]] && ok 'bundled Yakushi SDDM theme' || bad 'bundled Yakushi SDDM theme missing'

if command -v sddm >/dev/null 2>&1; then
  ok 'sddm'
  if command -v sddm-greeter-qt6 >/dev/null 2>&1 || command -v sddm-greeter >/dev/null 2>&1; then
    ok 'SDDM preview binary'
  else
    info 'SDDM preview binary unavailable'
  fi

  [[ -f /usr/share/sddm/themes/yakushi/Main.qml ]] \
    && ok 'installed Yakushi SDDM theme' \
    || info 'Yakushi SDDM theme is not installed system-wide yet'

  if [[ -f /etc/sddm.conf.d/90-yakushi-theme.conf ]] && grep -qE '^Current=yakushi[[:space:]]*$' /etc/sddm.conf.d/90-yakushi-theme.conf 2>/dev/null; then
    ok 'Yakushi SDDM selector'
  else
    info 'Yakushi is not selected through 90-yakushi-theme.conf yet'
  fi
else
  info 'sddm not installed (optional; required only for Yakushi Login Screen)'
fi

printf '\n'
((fail)) && { printf 'Diagnostics found problems.\n'; exit 1; }
printf 'All core checks passed.\n'
