#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$HOME/.local/share/yakushi-control-deck"; BIN="$HOME/.local/bin"; DATA="$HOME/.config/yakushi-control-deck"
STAMP="$(date +%Y%m%d-%H%M%S)"; BACKUP="$DATA/install-backups/$STAMP"
say(){ printf '%s\n' "$*"; }; fail(){ printf 'ERROR: %s\n' "$*" >&2; exit 1; }
command -v pacman >/dev/null 2>&1 || fail 'Arch Linux / pacman is required.'
command -v sudo >/dev/null 2>&1 || fail 'sudo is required.'
PACKAGES=(python python-gobject gtk4 hyprland waybar rofi kitty hyprpaper hyprlock pavucontrol playerctl brightnessctl wl-clipboard ttf-jetbrains-mono-nerd polkit)
missing=(); for package in "${PACKAGES[@]}"; do pacman -Qi "$package" >/dev/null 2>&1 || missing+=("$package"); done
if ((${#missing[@]})); then say 'Installing official Arch packages:'; printf '  %s\n' "${missing[@]}"; sudo pacman -S --needed "${missing[@]}"; fi
mkdir -p "$BACKUP" "$BIN" "$DATA"
backup_file(){ local src="$1" rel="$2"; [[ -e "$src" ]] || return 0; mkdir -p "$BACKUP/$(dirname "$rel")"; cp -a "$src" "$BACKUP/$rel"; }
backup_file "$HOME/.config/waybar/config.jsonc" waybar/config.jsonc; backup_file "$HOME/.config/waybar/style.css" waybar/style.css; backup_file "$HOME/.config/waybar/scripts" waybar/scripts
backup_file "$HOME/.config/rofi/config.rasi" rofi/config.rasi; backup_file "$HOME/.config/rofi/yakushi-opacity.rasi" rofi/yakushi-opacity.rasi; backup_file "$HOME/.config/rofi/scripts" rofi/scripts
backup_file "$HOME/.config/hypr/colors.css" hypr/colors.css; backup_file "$HOME/.config/hypr/colors.rasi" hypr/colors.rasi; backup_file "$HOME/.config/kitty/kitty.conf" kitty/kitty.conf
rm -rf "$TARGET"; mkdir -p "$TARGET" "$HOME/.config/waybar/scripts" "$HOME/.config/rofi/scripts" "$HOME/.config/hypr" "$HOME/.config/kitty" "$HOME/.local/share/applications"
cp -a "$ROOT/yakushi_deck" "$TARGET/"; cp -a "$ROOT/integrations" "$TARGET/"; cp -a "$ROOT/README.md" "$ROOT/LICENSE" "$TARGET/"
cp -a "$ROOT/integrations/waybar/config.jsonc" "$HOME/.config/waybar/config.jsonc"; cp -a "$ROOT/integrations/waybar/style.css" "$HOME/.config/waybar/style.css"; cp -a "$ROOT/integrations/waybar/scripts/." "$HOME/.config/waybar/scripts/"
cp -a "$ROOT/integrations/rofi/config.rasi" "$HOME/.config/rofi/config.rasi"; cp -a "$ROOT/integrations/rofi/yakushi-opacity.rasi" "$HOME/.config/rofi/yakushi-opacity.rasi"; cp -a "$ROOT/integrations/rofi/scripts/." "$HOME/.config/rofi/scripts/"
cp -a "$ROOT/integrations/hypr/colors.css" "$HOME/.config/hypr/colors.css"; cp -a "$ROOT/integrations/hypr/colors.rasi" "$HOME/.config/hypr/colors.rasi"
chmod +x "$HOME/.config/waybar/scripts/"*.sh "$HOME/.config/rofi/scripts/"*.sh
if [[ ! -s "$HOME/.config/kitty/kitty.conf" ]]; then cat > "$HOME/.config/kitty/kitty.conf" <<'KITTY'
font_family JetBrainsMono Nerd Font
font_size 12.0
background_opacity 0.92
dynamic_background_opacity yes
window_padding_width 8
KITTY
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
python3 -c 'import json, pathlib; json.load(open(pathlib.Path.home()/".config/waybar/config.jsonc"))'
rofi -no-config -theme "$HOME/.config/rofi/config.rasi" -dump-theme >/dev/null
pkill -x waybar 2>/dev/null || true; nohup waybar >/tmp/yakushi-waybar.log 2>&1 &
printf '{"version":"1.1.4","backup":"%s","installed_at":"%s"}\n' "$BACKUP" "$STAMP" > "$DATA/install.json"
say ''; say '薬  Yakushi Control Deck 1.1.4 installed.'; say "Backup: $BACKUP"; say 'Left click 薬 -> Control Deck'; say 'Right click 薬 -> Rofi'; say 'Power button -> Rofi power menu'; say 'Run ./doctor.sh for diagnostics.'
