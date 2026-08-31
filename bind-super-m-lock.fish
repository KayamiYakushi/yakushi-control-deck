#!/usr/bin/env fish

# Yakushi Control Deck — Super+M Lock Screen Hotfix
# Fish-native. No heredocs. No AUR dependencies.

set -l HYPR_DIR "$HOME/.config/hypr"
set -l LUA_CONFIG "$HYPR_DIR/hyprland.lua"
set -l CONF_CONFIG "$HYPR_DIR/hyprland.conf"
set -l DATA_DIR "$HOME/.config/yakushi-control-deck"
set -l STAMP (date +%Y%m%d-%H%M%S)
set -l BACKUP_DIR "$DATA_DIR/manual-backups/super-m-lock-$STAMP"

function fail
    printf 'ERROR: %s\n' "$argv" >&2
    exit 1
end

function info
    printf '  %s\n' "$argv"
end

printf '\n薬  Yakushi Control Deck — Super+M Lock Screen Hotfix\n\n'

if not type -q hyprctl
    fail 'Hyprland / hyprctl was not found.'
end

if not type -q hyprlock
    printf 'Hyprlock is not installed. Installing it from the official Arch repository...\n'
    if not type -q sudo
        fail 'sudo is required to install hyprlock.'
    end
    sudo pacman -S --needed hyprlock; or fail 'hyprlock installation failed.'
end

set -l CONFIG ''
set -l STYLE ''
if test -f "$LUA_CONFIG"
    set CONFIG "$LUA_CONFIG"
    set STYLE lua
else if test -f "$CONF_CONFIG"
    set CONFIG "$CONF_CONFIG"
    set STYLE conf
else
    fail 'Neither ~/.config/hypr/hyprland.lua nor ~/.config/hypr/hyprland.conf exists.'
end

mkdir -p "$BACKUP_DIR"; or fail 'Could not create the backup directory.'
cp -a "$CONFIG" "$BACKUP_DIR/"; or fail 'Could not back up the Hyprland config.'
set -l CONFIG_NAME (basename "$CONFIG")

if test -f "$HYPR_DIR/hyprlock.conf"
    cp -a "$HYPR_DIR/hyprlock.conf" "$BACKUP_DIR/hyprlock.conf"
end

set -l BEFORE_ERRORS (hyprctl configerrors 2>/dev/null | string collect)

# Remove an older Yakushi-managed block, then append the current one last.
# In Lua mode hl.unbind() removes the previous SUPER+M action before binding
# hyprlock. In legacy hyprlang mode `unbind` does the same thing.
set -l PATCHER "$BACKUP_DIR/patch_bind.py"
printf '%s' 'ZnJvbSBwYXRobGliIGltcG9ydCBQYXRoCmltcG9ydCByZQppbXBvcnQgc3lzCgpwYXRoID0gUGF0aChzeXMuYXJndlsxXSkKc3R5bGUgPSBzeXMuYXJndlsyXQp0ZXh0ID0gcGF0aC5yZWFkX3RleHQoKQpwYXR0ZXJuID0gcmUuY29tcGlsZSgKICAgIHIiKD9tcyleWyBcdF0qKD86LS18IykgWUFLVVNISSBMT0NLIEJJTkQgQkVHSU4uKj8iCiAgICByIl5bIFx0XSooPzotLXwjKSBZQUtVU0hJIExPQ0sgQklORCBFTkRbXlxuXSpcbj8iCikKdGV4dCA9IHBhdHRlcm4uc3ViKCIiLCB0ZXh0KS5yc3RyaXAoKQoKbHVhX2Jsb2NrID0gIiIiLS0gWUFLVVNISSBMT0NLIEJJTkQgQkVHSU4KLS0gTWFuYWdlZCBieSBZYWt1c2hpIENvbnRyb2wgRGVjay4gU1VQRVIrTSBsb2NrcyB0aGUgY3VycmVudCBzZXNzaW9uOyBpdCBkb2VzIG5vdCBsb2cgb3V0LgpobC51bmJpbmQoIlNVUEVSICsgTSIpCmhsLmJpbmQoIlNVUEVSICsgTSIsIGhsLmRzcC5leGVjX2NtZCgiaHlwcmxvY2siKSwgeyBkZXNjcmlwdGlvbiA9ICJZYWt1c2hpIExvY2sgU2NyZWVuIiB9KQotLSBZQUtVU0hJIExPQ0sgQklORCBFTkQiIiIKCmNvbmZfYmxvY2sgPSAiIiIjIFlBS1VTSEkgTE9DSyBCSU5EIEJFR0lOCiMgTWFuYWdlZCBieSBZYWt1c2hpIENvbnRyb2wgRGVjay4gU1VQRVIrTSBsb2NrcyB0aGUgY3VycmVudCBzZXNzaW9uOyBpdCBkb2VzIG5vdCBsb2cgb3V0Lgp1bmJpbmQgPSBTVVBFUiwgTQpiaW5kZCA9IFNVUEVSLCBNLCBZYWt1c2hpIExvY2sgU2NyZWVuLCBleGVjLCBoeXBybG9jawojIFlBS1VTSEkgTE9DSyBCSU5EIEVORCIiIgoKYmxvY2sgPSBsdWFfYmxvY2sgaWYgc3R5bGUgPT0gImx1YSIgZWxzZSBjb25mX2Jsb2NrCnBhdGgud3JpdGVfdGV4dCh0ZXh0ICsgIlxuXG4iICsgYmxvY2sgKyAiXG4iKQo=' | base64 -d > "$PATCHER"; or fail 'Could not prepare the config patcher.'
python3 "$PATCHER" "$CONFIG" "$STYLE"; or begin
    cp -a "$BACKUP_DIR/$CONFIG_NAME" "$CONFIG"
    fail 'Could not patch the Hyprland config. The original file was restored.'
end

hyprctl reload >/dev/null 2>&1
sleep 0.35

set -l AFTER_ERRORS (hyprctl configerrors 2>/dev/null | string collect)
if test "$AFTER_ERRORS" != "$BEFORE_ERRORS"
    printf 'A new Hyprland config error appeared. Restoring the original config...\n' >&2
    cp -a "$BACKUP_DIR/$CONFIG_NAME" "$CONFIG"
    hyprctl reload >/dev/null 2>&1
    printf '\nNew config error was:\n%s\n' "$AFTER_ERRORS" >&2
    fail "Patch rolled back safely. Backup: $BACKUP_DIR"
end

# Rebuild the Yakushi hyprlock config from the current Lock Screen Studio state.
# This keeps wallpaper, blur, brightness, clock and date settings in sync.
set -l GENERATED 0
for APP_ROOT in "$HOME/.local/share/yakushi-control-deck" "$HOME/.local/share/yakushi-control-deck-lite"
    if test -f "$APP_ROOT/yakushi_deck/core/lockscreen.py"
        env PYTHONPATH="$APP_ROOT" python3 -c 'from yakushi_deck.core.lockscreen import LockSettings,lock_status,apply_lock; d=lock_status(); s=LockSettings(wallpaper=str(d.get("wallpaper", "")), blur_passes=int(d.get("blur_passes",3)), blur_size=int(d.get("blur_size",8)), brightness=float(d.get("brightness",0.72)), clock_24h=bool(d.get("clock_24h",True)), show_date=bool(d.get("show_date",True))); ok,msg=apply_lock(s); print(msg); raise SystemExit(0 if ok else 1)'
        if test $status -eq 0
            set GENERATED 1
        end
        break
    end
end

# Lua-backed binds are exposed by hyprctl as dispatcher __lua with a numeric arg,
# so verify the stable bind description instead of grepping for the command name.
if not hyprctl binds 2>/dev/null | grep -Fqi 'description: Yakushi Lock Screen'
    printf 'The config was written, but Hyprland does not report the Yakushi lock bind. Restoring the original config...\n' >&2
    cp -a "$BACKUP_DIR/$CONFIG_NAME" "$CONFIG"
    hyprctl reload >/dev/null 2>&1
    fail "Runtime bind verification failed. Backup: $BACKUP_DIR"
end

printf '\nDONE\n'
info 'SUPER + M -> Hyprlock'
info 'No logout. No SDDM during normal locking.'
if test $GENERATED -eq 1
    info 'Yakushi Lock Screen Studio settings were regenerated.'
else
    info 'Hyprlock bind is active. Open Yakushi -> 04 SESSION -> Lock Screen and press APPLY LOCK SCREEN once.'
end
info "Backup: $BACKUP_DIR"
printf '\nPress SUPER + M now to test the lock screen.\n\n'
