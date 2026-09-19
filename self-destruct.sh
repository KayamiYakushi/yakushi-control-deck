#!/usr/bin/env bash
set -uo pipefail

TARGET="$HOME/.local/share/yakushi-control-deck"
DATA="$HOME/.config/yakushi-control-deck"
META="$DATA/install.json"
HELPER="$TARGET/yakushi_deck/core/self_destruct.py"
ROOT_HELPER="$TARGET/yakushi_deck/core/sddm_root.py"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

run_user_helper() {
  (cd "$TARGET" && python3 -m yakushi_deck.core.self_destruct "$@")
}

# Continue from a temporary copy. The installed tree can then be removed while
# this terminal keeps reporting progress and any pacman error to the user.
if [[ "${1:-}" != "--internal" ]]; then
  [[ "${1:-}" == "--execute" ]] || fail 'Run this helper from the confirmed Self Destruction page.'
  temporary="$(mktemp /tmp/yakushi-self-destruct.XXXXXX)" || fail 'Could not create a temporary removal helper.'
  cp -- "$0" "$temporary" || fail 'Could not stage the removal helper.'
  chmod 700 "$temporary"
  exec "$temporary" --internal --execute
fi
shift
[[ "${1:-}" == "--execute" ]] || fail 'Removal confirmation was not supplied.'

SELF_COPY="${BASH_SOURCE[0]}"
trap 'rm -f -- "$SELF_COPY"' EXIT

[[ -f "$META" ]] || fail 'Yakushi install metadata was not found. Nothing was removed.'
[[ -f "$HELPER" ]] || fail 'Yakushi cleanup support is missing. Reinstall before retrying.'

printf '\n薬  YAKUSHI SELF DESTRUCTION\n'
printf 'Restoring pre-Yakushi desktop files...\n\n'
run_user_helper cleanup-user || fail 'Desktop restoration failed. Application files were kept so the operation can be retried.'

if [[ -e /usr/share/sddm/themes/yakushi || -e /etc/sddm.conf.d/90-yakushi-theme.conf ]]; then
  printf '\nRemoving the Yakushi SDDM theme (administrator authorization may be requested)...\n'
  sudo python3 "$ROOT_HELPER" purge || fail 'The SDDM theme could not be removed. Application files were kept.'
fi

package_output="$(run_user_helper packages)" \
  || fail 'Tracked package metadata could not be read. Application files were kept.'
managed_packages=()
while IFS= read -r package; do
  [[ -n "$package" ]] && managed_packages+=("$package")
done <<< "$package_output"
installed_packages=()
for package in "${managed_packages[@]}"; do
  if pacman -Q -- "$package" >/dev/null 2>&1; then
    installed_packages+=("$package")
  fi
done

if ((${#installed_packages[@]})); then
  printf '\nRemoving packages installed by Yakushi and dependencies no longer needed elsewhere:\n'
  printf '  %s\n' "${installed_packages[@]}"
  sudo pacman -Rns --noconfirm -- "${installed_packages[@]}" \
    || fail 'Pacman refused package removal. Yakushi files and package metadata were kept for a safe retry.'
else
  printf '\nNo tracked Yakushi-installed packages need removal.\n'
fi

pkill -x waybar 2>/dev/null || true
if command -v waybar >/dev/null 2>&1; then
  nohup waybar >/tmp/yakushi-waybar.log 2>&1 &
fi
if command -v hyprctl >/dev/null 2>&1; then
  hyprctl reload >/dev/null 2>&1 || true
fi

rm -f -- "$HOME/.local/bin/yakushi-deck"
rm -f -- "$HOME/.local/share/applications/yakushi-control-deck.desktop"
rm -rf -- "$TARGET"
rm -rf -- "$DATA"

printf '\nYakushi Control Deck and every safely attributed dependency were removed.\n'
printf 'Pre-existing packages were never selected for removal.\n'
