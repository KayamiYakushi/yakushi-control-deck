#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QUIET=0
[[ "${1:-}" == "--quiet" ]] && QUIET=1
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
  integrations/waybar/config.jsonc integrations/waybar/style.css
  integrations/rofi/config.rasi integrations/rofi/yakushi-opacity.rasi
  integrations/sddm/yakushi/Main.qml integrations/sddm/yakushi/metadata.desktop
  integrations/sddm/yakushi/theme.conf
)
for rel in "${common_required[@]}"; do
  [[ -f "$ROOT/$rel" ]] && ok "bundle: $rel" || bad "bundle missing: $rel"
done

# A source checkout/release archive also contains installation/update entrypoints.
# The installed application copy intentionally omits self-replacing installers.
if [[ -f "$ROOT/install.sh" ]]; then
  for rel in install.sh install.fish update.sh; do
    [[ -f "$ROOT/$rel" ]] && ok "source bundle: $rel" || bad "source bundle missing: $rel"
  done
else
  info 'installed-layout smoke test: source-only install/update entrypoints skipped'
fi

command -v python3 >/dev/null 2>&1 || bad 'python3 is required for package checks'
if command -v python3 >/dev/null 2>&1; then
  python3 "$ROOT/tools/jsonc_check.py" "$ROOT/integrations/waybar/config.jsonc" >/dev/null 2>&1 \
    && ok 'bundled Waybar JSONC validates' || bad 'bundled Waybar JSONC invalid'

  ROOT="$ROOT" python3 - <<'PY' >/dev/null 2>&1
import os
from pathlib import Path
root = Path(os.environ["ROOT"])
for path in sorted((root / "yakushi_deck").rglob("*.py")):
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
PY
  [[ $? -eq 0 ]] && ok 'Python sources compile' || bad 'Python source compile failed'
fi

bash_scripts=(doctor.sh uninstall.sh restore-last-install.sh install-sddm-theme.sh smoke-test.sh)
[[ -f "$ROOT/install.sh" ]] && bash_scripts+=(install.sh update.sh)
for script in "${bash_scripts[@]}"; do
  bash -n "$ROOT/$script" >/dev/null 2>&1 && ok "bash syntax: $script" || bad "bash syntax: $script"
done

if command -v fish >/dev/null 2>&1; then
  fish_scripts=(bind-super-m-lock.fish)
  [[ -f "$ROOT/install.fish" ]] && fish_scripts+=(install.fish)
  for script in "${fish_scripts[@]}"; do
    fish -n "$ROOT/$script" >/dev/null 2>&1 && ok "fish syntax: $script" || bad "fish syntax: $script"
  done
else
  info 'fish not installed; Fish-only syntax checks skipped'
fi

if grep -RInE --exclude='README.md' --exclude='CHANGELOG.md' --exclude='RELEASE_NOTES_*' '/home/yakushi|yakushidotfiles' \
    "$ROOT/doctor.sh" "$ROOT/integrations" "$ROOT/yakushi_deck" ${ROOT:+"$ROOT/install.sh"} 2>/dev/null | grep -v ': No such file or directory' >/dev/null 2>&1; then
  bad 'private hard-coded home/dotfiles path found'
else
  ok 'no private hard-coded home/dotfiles paths'
fi

if grep -Fq '@import "yakushi-opacity.rasi"' "$ROOT/integrations/rofi/config.rasi"; then
  ok 'Rofi opacity override is bundled'
else
  bad 'Rofi opacity override import missing'
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
if [[ -f "$ROOT/install.sh" ]]; then
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
