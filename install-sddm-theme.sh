#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$HOME/.local/share/yakushi-control-deck"
PREVIEW="$HOME/.config/yakushi-control-deck/sddm-preview"
SOURCE=""
HELPER=""

printf '\n薬  Yakushi Control Deck — SDDM Installer\n\n'
command -v sudo >/dev/null 2>&1 || { echo 'ERROR: sudo is required.' >&2; exit 1; }
command -v sddm >/dev/null 2>&1 || { echo 'ERROR: SDDM is not installed.' >&2; exit 1; }

for candidate in "$PREVIEW" "$TARGET/integrations/sddm/yakushi" "$ROOT/integrations/sddm/yakushi"; do
  if [[ -f "$candidate/Main.qml" ]]; then SOURCE="$candidate"; break; fi
done
for candidate in "$TARGET/yakushi_deck/core/sddm_root.py" "$ROOT/yakushi_deck/core/sddm_root.py"; do
  if [[ -f "$candidate" ]]; then HELPER="$candidate"; break; fi
done
[[ -n "$SOURCE" ]] || { echo 'ERROR: Yakushi SDDM theme source is missing.' >&2; exit 1; }
[[ -n "$HELPER" ]] || { echo 'ERROR: Yakushi SDDM privilege helper is missing.' >&2; exit 1; }

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
STAGE="$TMP/yakushi"
cp -a "$SOURCE" "$STAGE"
if [[ -f "$STAGE/theme.conf.user" ]]; then
  if grep -q '^previewMode=' "$STAGE/theme.conf.user"; then
    sed -i 's/^previewMode=.*/previewMode=false/' "$STAGE/theme.conf.user"
  else
    printf '\npreviewMode=false\n' >> "$STAGE/theme.conf.user"
  fi
fi

echo 'Administrator access is required once to install the SDDM theme.'
sudo /usr/bin/python3 "$HELPER" install --source "$STAGE"

echo
sudo test -f /usr/share/sddm/themes/yakushi/Main.qml || { echo 'ERROR: theme files were not installed.' >&2; exit 1; }
ACTIVE=""
if [[ -f /etc/sddm.conf.d/90-yakushi-theme.conf ]]; then
  ACTIVE="$(sudo awk -F= '/^[[:space:]]*Current[[:space:]]*=/{gsub(/[[:space:]]/,"",$2); print $2; exit}' /etc/sddm.conf.d/90-yakushi-theme.conf)"
fi
if [[ -f /etc/sddm.conf ]]; then
  LEGACY="$(sudo awk '/^\[Theme\]/{t=1;next} /^\[/{t=0} t && /^[[:space:]]*Current[[:space:]]*=/{sub(/^[^=]*=/,"");gsub(/^[[:space:]]+|[[:space:]]+$/,"");print;exit}' /etc/sddm.conf)"
  [[ -n "$LEGACY" ]] && ACTIVE="$LEGACY"
fi
[[ "$ACTIVE" == "yakushi" ]] || { echo "ERROR: active SDDM theme is '${ACTIVE:-default}', not yakushi." >&2; exit 1; }

echo 'OK: Yakushi SDDM is installed and active.'
echo 'Log out normally or reboot to see it. Do not restart SDDM from inside Hyprland.'
