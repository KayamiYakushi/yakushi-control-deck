#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QUIET=0
INSTALLED_LAYOUT=0
for arg in "$@"; do
  case "$arg" in
    --quiet) QUIET=1 ;;
    --installed) INSTALLED_LAYOUT=1 ;;
    *) printf 'Unknown smoke-test option: %s\n' "$arg" >&2; exit 2 ;;
  esac
done
fail=0

ok(){ ((QUIET)) || printf '[ OK ] %s\n' "$*"; }
bad(){ printf '[FAIL] %s\n' "$*" >&2; fail=1; }
info(){ ((QUIET)) || printf '[INFO] %s\n' "$*"; }

common_required=(
  README.md LICENSE doctor.sh smoke-test.sh install-sddm-theme.sh
  bind-super-m-lock.fish restore-last-install.sh uninstall.sh
  tools/jsonc_check.py
  yakushi_deck/__init__.py yakushi_deck/__main__.py yakushi_deck/app.py
  yakushi_deck/core/lockscreen.py yakushi_deck/core/sddm_root.py
  yakushi_deck/core/autocolor.py yakushi_deck/core/nautilus.py yakushi_deck/core/fastfetch.py yakushi_deck/core/frame.py
  integrations/waybar/config.jsonc integrations/waybar/style.css
  integrations/rofi/config.rasi integrations/rofi/yakushi-launcher-opacity.rasi integrations/rofi/yakushi-opacity.rasi integrations/rofi/powermenu.rasi integrations/rofi/scripts/powermenu.sh
  integrations/rofi/icons/power/lock.svg integrations/rofi/icons/power/suspend.svg integrations/rofi/icons/power/logout.svg integrations/rofi/icons/power/reboot.svg integrations/rofi/icons/power/shutdown.svg
  integrations/fastfetch/config.jsonc integrations/fastfetch/logo.txt integrations/fastfetch/yakushi-logo.txt
  integrations/sddm/yakushi/Main.qml integrations/sddm/yakushi/metadata.desktop
  integrations/sddm/yakushi/theme.conf
  screenshots/desktop.png screenshots/control-deck.png
)
for rel in "${common_required[@]}"; do
  [[ -f "$ROOT/$rel" ]] && ok "bundle: $rel" || bad "bundle missing: $rel"
done

# Source checkouts/release archives validate self-replacing install/update entrypoints.
# Installed application copies may contain stale source entrypoints from older releases;
# --installed deliberately ignores them so they cannot create false version failures.
if ((INSTALLED_LAYOUT)); then
  info 'installed-layout smoke test: source-only install/update entrypoints skipped'
else
  for rel in install.sh install.fish update.sh; do
    [[ -f "$ROOT/$rel" ]] && ok "source bundle: $rel" || bad "source bundle missing: $rel"
  done
fi

command -v python3 >/dev/null 2>&1 || bad 'python3 is required for package checks'
if command -v python3 >/dev/null 2>&1; then
  python3 "$ROOT/tools/jsonc_check.py" "$ROOT/integrations/waybar/config.jsonc" >/dev/null 2>&1 \
    && ok 'bundled Waybar JSONC validates' || bad 'bundled Waybar JSONC invalid'

  python3 "$ROOT/tools/jsonc_check.py" "$ROOT/integrations/fastfetch/config.jsonc" >/dev/null 2>&1 \
    && ok 'bundled Fastfetch JSONC validates' || bad 'bundled Fastfetch JSONC invalid'

  ROOT="$ROOT" python3 - <<'PY' >/dev/null 2>&1
import json
import os
from pathlib import Path

expected = {
    "os": "󰣇 ",
    "host": "󰌢 ",
    "kernel": "󰒋 ",
    "uptime": "󰅐 ",
    "packages": "󰏖 ",
    "shell": "󰆍 ",
    "display": "󰍹 ",
    "wm": "󰖲 ",
    "terminal": " ",
    "cpu": "󰻠 ",
    "gpu": "󰢮 ",
    "memory": "󰍛 ",
    "disk": "󰋊 ",
}
root = Path(os.environ["ROOT"])
config = json.loads((root / "integrations/fastfetch/config.jsonc").read_text(encoding="utf-8"))
actual = {
    entry.get("type"): entry.get("key")
    for entry in config.get("modules", [])
    if isinstance(entry, dict) and entry.get("type") in expected
}
assert actual == expected
PY
  [[ $? -eq 0 ]] && ok 'bundled Fastfetch Nerd Font module keys match Yakushi defaults' \
    || bad 'bundled Fastfetch Nerd Font module keys are missing or changed'

  ROOT="$ROOT" python3 - <<'PY' >/dev/null 2>&1
import os
import sys
from pathlib import Path
root = Path(os.environ["ROOT"])
for path in sorted((root / "yakushi_deck").rglob("*.py")):
    compile(path.read_text(encoding="utf-8"), str(path), "exec")

sys.dont_write_bytecode = True
sys.path.insert(0, str(root))
from yakushi_deck.core.apps import _rofi_theme_text, rofi_theme_presets

presets = {key: (title, description) for key, title, description in rofi_theme_presets()}
assert "raycast_glass" in presets
raycast = _rofi_theme_text("raycast_glass", "JetBrainsMono Nerd Font 12")
assert "/* YAKUSHI ROFI THEME: raycast_glass */" in raycast
assert "children: [ inputbar, textbox-section, message, listview, footer ];" in raycast
assert 'matching: "fuzzy";' in raycast
assert 'action: "kb-cancel";' in raycast
assert 'action: "kb-accept-entry";' in raycast
assert raycast.rstrip().endswith('@import "yakushi-launcher-opacity.rasi"')
PY
  if [[ $? -eq 0 ]]; then
    ok 'Python sources compile and Raycast Glass preset is complete'
  else
    bad 'Python source or Raycast Glass preset check failed'
  fi
fi

bash_scripts=(doctor.sh uninstall.sh restore-last-install.sh install-sddm-theme.sh smoke-test.sh)
if ((!INSTALLED_LAYOUT)); then
  bash_scripts+=(install.sh update.sh)
fi
for script in "${bash_scripts[@]}"; do
  bash -n "$ROOT/$script" >/dev/null 2>&1 && ok "bash syntax: $script" || bad "bash syntax: $script"
done

if command -v fish >/dev/null 2>&1; then
  fish_scripts=(bind-super-m-lock.fish)
  if ((!INSTALLED_LAYOUT)); then fish_scripts+=(install.fish); fi
  for script in "${fish_scripts[@]}"; do
    fish -n "$ROOT/$script" >/dev/null 2>&1 && ok "fish syntax: $script" || bad "fish syntax: $script"
  done
else
  info 'fish not installed; Fish-only syntax checks skipped'
fi

scan_paths=("$ROOT/doctor.sh" "$ROOT/integrations" "$ROOT/yakushi_deck")
if ((!INSTALLED_LAYOUT)); then scan_paths+=("$ROOT/install.sh"); fi
if grep -RInE --exclude='README.md' --exclude='CHANGELOG.md' --exclude='RELEASE_NOTES_*' '/home/yakushi|yakushidotfiles' \
    "${scan_paths[@]}" 2>/dev/null | grep -v ': No such file or directory' >/dev/null 2>&1; then
  bad 'private hard-coded home/dotfiles path found'
else
  ok 'no private hard-coded home/dotfiles paths'
fi

if ((!INSTALLED_LAYOUT)); then
  if find "$ROOT/yakushi_deck" -type d -name __pycache__ -print -quit 2>/dev/null | grep -q . \
      || find "$ROOT/yakushi_deck" -type f -name '*.pyc' -print -quit 2>/dev/null | grep -q .; then
    bad 'Python cache/bytecode files are present in the source release'
  else
    ok 'source release contains no Python cache/bytecode files'
  fi
fi

if grep -Fq '@import "yakushi-launcher-opacity.rasi"' "$ROOT/integrations/rofi/config.rasi"; then
  if grep -Fq '@import "yakushi-opacity.rasi"' "$ROOT/integrations/rofi/powermenu.rasi"; then
    ok 'Rofi launcher and power-menu opacity overrides are isolated'
  else
    bad 'Rofi power-menu opacity override import is missing'
  fi
else
  bad 'Rofi launcher opacity override import is missing'
fi

version="$(ROOT="$ROOT" python3 - <<'PY' 2>/dev/null
import os, re
from pathlib import Path
p = Path(os.environ['ROOT']) / 'yakushi_deck' / '__init__.py'
m = re.search(r'__version__\s*=\s*["\']([^"\']+)', p.read_text())
print(m.group(1) if m else '')
PY
)"
version_ok=1
[[ -n "$version" ]] || version_ok=0
grep -Fq "Version=$version" "$ROOT/integrations/sddm/yakushi/metadata.desktop" || version_ok=0
if ((!INSTALLED_LAYOUT)); then
  grep -Fq "\"version\":\"$version\"" "$ROOT/install.sh" || version_ok=0
fi
if ((version_ok)); then
  ok "version metadata aligned ($version)"
else
  bad 'version metadata is not aligned'
fi

printf '\n'
if ((fail)); then
  printf 'Package smoke test found problems.\n' >&2
  exit 1
fi
printf 'Package smoke test passed. No system files were changed.\n'
