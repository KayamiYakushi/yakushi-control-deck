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
import subprocess
import sys
import tempfile
from pathlib import Path
root = Path(os.environ["ROOT"])
for path in sorted((root / "yakushi_deck").rglob("*.py")):
    compile(path.read_text(encoding="utf-8"), str(path), "exec")

sys.dont_write_bytecode = True
sys.path.insert(0, str(root))
import yakushi_deck.core.apps as apps
from yakushi_deck.core.theme import _rofi_concrete_override
from yakushi_deck.core.apps import (
    RofiState,
    _rofi_glass_hypr_text,
    _rofi_theme_text,
    rofi_theme_presets,
)

presets = {key: (title, description) for key, title, description in rofi_theme_presets()}
assert "raycast_glass" in presets
raycast = _rofi_theme_text("raycast_glass", "JetBrainsMono Nerd Font 12")
assert "/* YAKUSHI ROFI THEME: raycast_glass */" in raycast
assert "children: [ inputbar, textbox-section, message, listview, footer ];" in raycast
assert 'matching: "fuzzy";' in raycast
assert "width: 620px;" in raycast
assert "fixed-height: false;" in raycast
assert 'font: "Sans 11";' in raycast
assert "case-indicator" not in raycast
assert "background-image: linear-gradient" in raycast
assert "border: 0px 0px 0px 2px;" in raycast
assert 'content: "薬  YAKUSHI";' in raycast
assert 'content: "↵  Open";' in raycast
footer = raycast.split("footer {", 1)[1].split("}", 1)[0]
assert "expand: false;" in footer
assert 'action: "kb-cancel";' in raycast
assert 'action: "kb-accept-entry";' in raycast
assert raycast.rstrip().endswith('@import "yakushi-launcher-opacity.rasi"')

lua = _rofi_glass_hypr_text("hl.config({})\n", "lua", True)
assert lua.count("YAKUSHI ROFI GLASS BEGIN") == 1
assert 'match        = { namespace = "rofi" }' in lua
assert "ignore_alpha = 0.20" in lua
assert "xray         = false" in lua
assert "YAKUSHI ROFI GLASS" not in _rofi_glass_hypr_text(lua, "lua", False)

conf = _rofi_glass_hypr_text("# Hyprland\n", "conf", True)
assert "layerrule {" in conf
assert "match:namespace = rofi" in conf

# Exercise the transactional path without touching the real home directory.
with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    rofi_config = base / "rofi" / "config.rasi"
    override = base / "rofi" / "yakushi-launcher-opacity.rasi"
    colors = base / "hypr" / "colors.rasi"
    hypr = base / "hypr" / "hyprland.lua"
    rofi_config.parent.mkdir(parents=True)
    hypr.parent.mkdir(parents=True)
    rofi_config.write_text("ORIGINAL THEME\n")
    override.write_text("ORIGINAL OVERRIDE\n")
    colors.write_text(
        "* {\n"
        "    yak-bg: #0e0c0d;\n"
        "    yak-surface: #1a1414;\n"
        "    yak-surface-alt: #231919;\n"
        "    yak-hover: #362324;\n"
        "}\n"
    )
    hypr.write_text("hl.config({})\n")

    apps.ROFI_CONFIG = rofi_config
    apps.ROFI_LAUNCHER_OPACITY_OVERRIDE = override
    apps.HYPR_COLORS_RASI = colors
    apps._rofi_hypr_config = lambda: (hypr, "lua")
    apps.rofi_load = lambda: RofiState(
        font="JetBrainsMono Nerd Font 12",
        width=600,
        radius=18,
        padding=16,
        lines=7,
        opacity=0.82,
    )
    apps.record = lambda *_args, **_kwargs: None
    apps.time.sleep = lambda _seconds: None
    apps.run = lambda command, timeout=5.0: subprocess.CompletedProcess(command, 0, "", "")

    ok, _message = apps.rofi_apply_theme("raycast_glass")
    assert ok
    assert "YAKUSHI ROFI GLASS BEGIN" in hypr.read_text()
    assert "fixed-height: false;" in rofi_config.read_text()
    assert "rgba(14, 12, 13, 78%)" in override.read_text()
    assert "rgba(26, 20, 20, 22%)" in override.read_text()
    assert "rgba(35, 25, 25, 33%)" in override.read_text()
    assert "rgba(54, 35, 36, 43%)" in override.read_text()
    assert "button-close {\n    background-color: transparent;" in override.read_text()

    rofi_config.write_text("ORIGINAL THEME\n")
    override.write_text("ORIGINAL OVERRIDE\n")
    hypr.write_text("hl.config({})\n")
    configerror_calls = 0

    def run_with_new_config_error(command, timeout=5.0):
        global configerror_calls
        if command[:2] == ["hyprctl", "configerrors"]:
            configerror_calls += 1
            output = "" if configerror_calls == 1 else "new test error"
            return subprocess.CompletedProcess(command, 0, output, "")
        return subprocess.CompletedProcess(command, 0, "", "")

    apps.run = run_with_new_config_error
    ok, _message = apps.rofi_apply_theme("raycast_glass")
    assert not ok
    assert rofi_config.read_text() == "ORIGINAL THEME\n"
    assert override.read_text() == "ORIGINAL OVERRIDE\n"
    assert hypr.read_text() == "hl.config({})\n"

premium_override = _rofi_concrete_override(
    "#0e0c0d",
    0.78,
    "#1a1414",
    "#231919",
    "#362324",
    premium=True,
)
assert "button-close {\n    background-color: transparent;" in premium_override
assert "button-open {\n    background-color: rgba(54, 35, 36, 43%);" in premium_override

power = (root / "integrations/rofi/scripts/powermenu.sh").read_text()
for action in ("lock", "suspend", "logout", "reboot", "shutdown"):
    assert f"row {action} " in power
    assert f"{action})" in power
PY
  if [[ $? -eq 0 ]]; then
    ok 'Python sources compile; premium Rofi blur and rollback checks pass'
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
  if [[ -d "$ROOT/.git" ]]; then
    if git -C "$ROOT" ls-files | grep -Eq '(^|/)(__pycache__/|[^/]+\.pyc$)'; then
      bad 'tracked Python cache/bytecode files are present in the source checkout'
    else
      ok 'source checkout contains no tracked Python cache/bytecode files'
    fi
  elif find "$ROOT/yakushi_deck" -type d -name __pycache__ -print -quit 2>/dev/null | grep -q . \
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
