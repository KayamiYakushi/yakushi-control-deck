#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$HOME/.local/share/yakushi-control-deck"; BIN="$HOME/.local/bin"; DATA="$HOME/.config/yakushi-control-deck"
VERSION="1.3.0"
META="$DATA/install.json"
STAMP="$(date +%Y%m%d-%H%M%S)"; BACKUP="$DATA/install-backups/$STAMP"
say(){ printf '%s\n' "$*"; }; fail(){ printf 'ERROR: %s\n' "$*" >&2; exit 1; }
command -v pacman >/dev/null 2>&1 || fail 'Arch Linux / pacman is required.'
command -v sudo >/dev/null 2>&1 || fail 'sudo is required.'

# Package ownership is deliberately conservative. Only direct requirements
# that were absent immediately before a Yakushi install are eligible for the
# future Self Destruction action. Pacman -Rns then handles their now-unused
# dependency graph without touching packages that predated Yakushi.
managed_packages=()
legacy_packages_untracked=false
legacy_config_untracked=false
if [[ -f "$META" ]]; then
  while IFS= read -r package; do
    [[ -n "$package" ]] && managed_packages+=("$package")
  done < <(python3 - "$META" <<'PY' 2>/dev/null || true
import json, sys
value = json.load(open(sys.argv[1], encoding="utf-8"))
for package in value.get("managed_packages", []):
    if isinstance(package, str):
        print(package)
PY
  )
  if python3 - "$META" <<'PY' >/dev/null 2>&1
import json, sys
value = json.load(open(sys.argv[1], encoding="utf-8"))
raise SystemExit(0 if isinstance(value.get("managed_packages"), list) else 1)
PY
  then
    if python3 - "$META" <<'PY' >/dev/null 2>&1
import json, sys
value = json.load(open(sys.argv[1], encoding="utf-8"))
raise SystemExit(0 if value.get("legacy_packages_untracked") else 1)
PY
    then legacy_packages_untracked=true; fi
  else
    legacy_packages_untracked=true
  fi
  if python3 - "$META" <<'PY' >/dev/null 2>&1
import json, sys
value = json.load(open(sys.argv[1], encoding="utf-8"))
raise SystemExit(0 if "legacy_config_untracked" in value else 1)
PY
  then
    if python3 - "$META" <<'PY' >/dev/null 2>&1
import json, sys
value = json.load(open(sys.argv[1], encoding="utf-8"))
raise SystemExit(0 if value.get("legacy_config_untracked") else 1)
PY
    then legacy_config_untracked=true; fi
  else
    legacy_config_untracked=true
  fi
fi

original_backup=""
if [[ -f "$META" ]]; then
  original_backup="$(python3 - "$META" <<'PY' 2>/dev/null || true
import json, sys
value = json.load(open(sys.argv[1], encoding="utf-8"))
print(value.get("original_backup", ""))
PY
  )"
fi
if [[ -z "$original_backup" || ! -d "$original_backup" ]]; then
  if [[ -d "$DATA/install-backups" ]]; then
    original_backup="$(find "$DATA/install-backups" -mindepth 1 -maxdepth 1 -type d -print | sort | head -n 1)"
  fi
fi
[[ -n "$original_backup" ]] || original_backup="$BACKUP"

PACKAGES=(python python-gobject gtk4 gdk-pixbuf2 hyprland waybar rofi kitty fastfetch hyprpaper hyprlock pavucontrol playerctl brightnessctl wl-clipboard ttf-jetbrains-mono-nerd polkit)
missing=(); for package in "${PACKAGES[@]}"; do pacman -Qi "$package" >/dev/null 2>&1 || missing+=("$package"); done
if ((${#missing[@]})); then say 'Installing official Arch packages:'; printf '  %s\n' "${missing[@]}"; sudo pacman -S --needed "${missing[@]}"; fi
managed_packages+=("${missing[@]}")
declare -A package_seen=()
tracked_packages=()
for package in "${managed_packages[@]}"; do
  [[ -n "${package_seen[$package]:-}" ]] && continue
  package_seen[$package]=1
  tracked_packages+=("$package")
done

# Validate the release bundle before touching the user's desktop files.
[[ -x "$ROOT/smoke-test.sh" ]] || fail 'Package smoke-test helper is missing.'
"$ROOT/smoke-test.sh" --quiet || fail 'Package integrity check failed. Run ./smoke-test.sh for details.'
mkdir -p "$BACKUP" "$BIN" "$DATA"
backup_file(){ local src="$1" rel="$2"; [[ -e "$src" ]] || return 0; mkdir -p "$BACKUP/$(dirname "$rel")"; cp -a "$src" "$BACKUP/$rel"; }
backup_file "$HOME/.config/waybar/config.jsonc" waybar/config.jsonc; backup_file "$HOME/.config/waybar/style.css" waybar/style.css; backup_file "$HOME/.config/waybar/scripts" waybar/scripts
backup_file "$HOME/.config/rofi/config.rasi" rofi/config.rasi; backup_file "$HOME/.config/rofi/yakushi-launcher-opacity.rasi" rofi/yakushi-launcher-opacity.rasi; backup_file "$HOME/.config/rofi/yakushi-opacity.rasi" rofi/yakushi-opacity.rasi; backup_file "$HOME/.config/rofi/powermenu.rasi" rofi/powermenu.rasi; backup_file "$HOME/.config/rofi/scripts" rofi/scripts; backup_file "$HOME/.config/rofi/icons/power" rofi/icons/power
backup_file "$HOME/.config/hypr/colors.css" hypr/colors.css; backup_file "$HOME/.config/hypr/colors.rasi" hypr/colors.rasi; backup_file "$HOME/.config/hypr/hyprland.lua" hypr/hyprland.lua; backup_file "$HOME/.config/hypr/hyprland.conf" hypr/hyprland.conf; backup_file "$HOME/.config/kitty/kitty.conf" kitty/kitty.conf; backup_file "$HOME/.config/kitty/yakushi-colors.conf" kitty/yakushi-colors.conf; backup_file "$HOME/.config/fastfetch/config.jsonc" fastfetch/config.jsonc; backup_file "$HOME/.config/fastfetch/logo.txt" fastfetch/logo.txt; backup_file "$HOME/.config/fastfetch/yakushi-logo.txt" fastfetch/yakushi-logo.txt
rm -rf "$TARGET"; mkdir -p "$TARGET" "$HOME/.config/waybar/scripts" "$HOME/.config/rofi/scripts" "$HOME/.config/rofi/icons/power" "$HOME/.config/hypr" "$HOME/.config/kitty" "$HOME/.config/fastfetch" "$HOME/.local/share/applications"
cp -a "$ROOT/yakushi_deck" "$TARGET/"; cp -a "$ROOT/integrations" "$TARGET/"; cp -a "$ROOT/tools" "$TARGET/"
# Running Yakushi from a source checkout may leave harmless untracked Python
# caches behind. Never ship those into the installed application tree.
find "$TARGET/yakushi_deck" -type f -path '*/__pycache__/*' -delete
find "$TARGET/yakushi_deck" -depth -type d -name __pycache__ -empty -delete
[[ -d "$ROOT/screenshots" ]] && cp -a "$ROOT/screenshots" "$TARGET/"
cp -a "$ROOT/README.md" "$ROOT/LICENSE" "$ROOT/doctor.sh" "$ROOT/smoke-test.sh" "$ROOT/install-sddm-theme.sh" "$ROOT/bind-super-m-lock.fish" "$ROOT/restore-last-install.sh" "$ROOT/uninstall.sh" "$ROOT/self-destruct.sh" "$TARGET/"
cp -a "$ROOT/integrations/waybar/config.jsonc" "$HOME/.config/waybar/config.jsonc"; cp -a "$ROOT/integrations/waybar/style.css" "$HOME/.config/waybar/style.css"; cp -a "$ROOT/integrations/waybar/scripts/." "$HOME/.config/waybar/scripts/"
cp -a "$ROOT/integrations/rofi/config.rasi" "$HOME/.config/rofi/config.rasi"; cp -a "$ROOT/integrations/rofi/yakushi-launcher-opacity.rasi" "$HOME/.config/rofi/yakushi-launcher-opacity.rasi"; cp -a "$ROOT/integrations/rofi/yakushi-opacity.rasi" "$HOME/.config/rofi/yakushi-opacity.rasi"; cp -a "$ROOT/integrations/rofi/powermenu.rasi" "$HOME/.config/rofi/powermenu.rasi"; cp -a "$ROOT/integrations/rofi/scripts/." "$HOME/.config/rofi/scripts/"; cp -a "$ROOT/integrations/rofi/icons/power/." "$HOME/.config/rofi/icons/power/"
cp -a "$ROOT/integrations/hypr/colors.css" "$HOME/.config/hypr/colors.css"; cp -a "$ROOT/integrations/hypr/colors.rasi" "$HOME/.config/hypr/colors.rasi"
chmod +x "$HOME/.config/waybar/scripts/"*.sh "$HOME/.config/rofi/scripts/"*.sh
if [[ ! -s "$HOME/.config/kitty/kitty.conf" ]]; then
  cat > "$HOME/.config/kitty/kitty.conf" <<'KITTY'
font_family JetBrainsMono Nerd Font
font_size 12.0
background_opacity 0.92
dynamic_background_opacity yes
window_padding_width 8

# YAKUSHI KITTY COLORS - KEEP THIS INCLUDE LAST
include yakushi-colors.conf
KITTY
  cat > "$HOME/.config/kitty/yakushi-colors.conf" <<'KITTYCOLORS'
# Generated by Yakushi Control Deck.
# YAKUSHI KITTY COLOR MODE: follow
background #0e0c0d
foreground #e8a29a
cursor #e8a29a
cursor_text_color #0e0c0d
selection_background #e8a29a
selection_foreground #171313
url_color #e8a29a
active_border_color #e8a29a
inactive_border_color #463f41
tab_bar_background #0e0c0d
active_tab_background #e8a29a
active_tab_foreground #171313
inactive_tab_background #242022
inactive_tab_foreground #e8a29a
color0 #0e0c0d
color1 #e8a29a
color2 #e8aca5
color3 #e8b5af
color4 #e8bdb8
color5 #e8b1aa
color6 #e8b9b3
color7 #e8a29a
color8 #584347
color9 #e8aaa3
color10 #e8b2ab
color11 #e8bab4
color12 #e8c2bd
color13 #e8b6b0
color14 #e8beb9
color15 #ecd0cc
KITTYCOLORS
fi

if [[ ! -s "$HOME/.config/fastfetch/config.jsonc" ]]; then
  cp -a "$ROOT/integrations/fastfetch/config.jsonc" "$HOME/.config/fastfetch/config.jsonc"
fi
if [[ ! -s "$HOME/.config/fastfetch/logo.txt" ]]; then
  cp -a "$ROOT/integrations/fastfetch/logo.txt" "$HOME/.config/fastfetch/logo.txt"
fi
if [[ ! -s "$HOME/.config/fastfetch/yakushi-logo.txt" ]]; then
  cp -a "$ROOT/integrations/fastfetch/yakushi-logo.txt" "$HOME/.config/fastfetch/yakushi-logo.txt"
fi
cat > "$BIN/yakushi-deck" <<LAUNCH
#!/usr/bin/env bash
cd "$TARGET"
exec python3 -m yakushi_deck "\$@"
LAUNCH
chmod +x "$BIN/yakushi-deck"
cat > "$HOME/.local/share/applications/yakushi-control-deck.desktop" <<DESKTOP
[Desktop Entry]
Name=Yakushi Control Deck
Comment=Lightweight Hyprland desktop control deck
Exec=$BIN/yakushi-deck
Type=Application
Categories=Settings;System;
Terminal=false
DESKTOP
python3 -m compileall -q "$TARGET/yakushi_deck"
python3 "$TARGET/tools/jsonc_check.py" "$HOME/.config/waybar/config.jsonc"
rofi -no-config -theme "$HOME/.config/rofi/config.rasi" -dump-theme >/dev/null
if ! rofi_glass_status="$(PYTHONPATH="$TARGET" python3 - <<'PY'
from yakushi_deck.core.apps import ensure_rofi_glass

ok, message = ensure_rofi_glass()
print(message)
raise SystemExit(0 if ok else 1)
PY
)"; then
  fail "${rofi_glass_status:-Rofi layer blur setup failed.}"
fi
say "$rofi_glass_status"
pkill -x waybar 2>/dev/null || true; nohup waybar >/tmp/yakushi-waybar.log 2>&1 &
python3 - "$META" "$VERSION" "$BACKUP" "$original_backup" "$STAMP" "$legacy_packages_untracked" "$legacy_config_untracked" "${tracked_packages[@]}" <<'PY'
import json, sys
path, version, backup, original, installed_at, legacy_packages, legacy_config, *packages = sys.argv[1:]
value = {
    "version": version,
    "backup": backup,
    "original_backup": original,
    "managed_packages": packages,
    "legacy_packages_untracked": legacy_packages == "true",
    "legacy_config_untracked": legacy_config == "true",
    "installed_at": installed_at,
}
with open(path, "w", encoding="utf-8") as stream:
    json.dump(value, stream, indent=2)
    stream.write("\n")
PY
say ''; say "薬  Yakushi Control Deck $VERSION installed."; say "Backup: $BACKUP"; say 'Left click 薬 -> Control Deck'; say 'Right click 薬 -> Rofi'; say 'Power button -> Rofi power menu'; say 'Run ./doctor.sh for diagnostics.'
