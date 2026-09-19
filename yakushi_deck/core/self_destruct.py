from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .paths import BACKUPS, DATA, TYPOGRAPHY_STATE


INSTALL_METADATA = DATA / "install.json"
INSTALL_BACKUPS = DATA / "install-backups"
INSTALL_TARGET = Path.home() / ".local" / "share" / "yakushi-control-deck"
SELF_DESTRUCT_SCRIPT = INSTALL_TARGET / "self-destruct.sh"

_PACKAGE_NAME = re.compile(r"^[A-Za-z0-9@._+:-]+$")


@dataclass(frozen=True)
class SelfDestructPlan:
    version: str
    original_backup: Path | None
    managed_packages: tuple[str, ...]
    legacy_package_provenance: bool
    legacy_config_provenance: bool

    @property
    def backup_available(self) -> bool:
        return bool(self.original_backup and self.original_backup.is_dir())


def _safe_original_backup(raw: object) -> Path | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    candidate = Path(raw).expanduser()
    try:
        resolved = candidate.resolve()
        resolved.relative_to(INSTALL_BACKUPS.resolve())
    except (OSError, ValueError):
        return None
    return resolved


def load_plan(metadata_path: Path = INSTALL_METADATA) -> SelfDestructPlan:
    try:
        value = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        value = {}
    if not isinstance(value, dict):
        value = {}

    raw_packages = value.get("managed_packages")
    packages: list[str] = []
    if isinstance(raw_packages, list):
        for package in raw_packages:
            name = str(package).strip()
            if name and _PACKAGE_NAME.fullmatch(name) and name not in packages:
                packages.append(name)

    return SelfDestructPlan(
        version=str(value.get("version", "unknown")),
        original_backup=_safe_original_backup(value.get("original_backup")),
        managed_packages=tuple(packages),
        legacy_package_provenance=(
            not isinstance(raw_packages, list)
            or bool(value.get("legacy_packages_untracked"))
        ),
        legacy_config_provenance=(
            "legacy_config_untracked" not in value
            or bool(value.get("legacy_config_untracked"))
        ),
    )


def plan_lines(plan: SelfDestructPlan | None = None) -> list[str]:
    plan = plan or load_plan()
    lines = [
        f"Installed release: {plan.version}",
        "Application: launcher, desktop entry and installed Yakushi files",
        "Desktop integration: restore the first pre-Yakushi Waybar, Rofi, Kitty, Fastfetch and palette files",
        "Hyprland: remove only blocks explicitly marked as managed by Yakushi",
        "Login screen: disable and remove the Yakushi SDDM theme",
    ]
    if plan.managed_packages:
        lines.append("Tracked Arch packages: " + ", ".join(plan.managed_packages))
        lines.append("Pacman will remove these packages and now-unused dependencies with -Rns.")
        if plan.legacy_package_provenance:
            lines.append(
                "Legacy note: packages from installations before tracking was introduced will be kept because their ownership cannot be proven."
            )
    elif plan.legacy_package_provenance:
        lines.append(
            "Tracked Arch packages: unavailable for this legacy installation; system packages will be kept for safety."
        )
    else:
        lines.append("Tracked Arch packages: none (all requirements existed before Yakushi).")
    if plan.backup_available:
        lines.append(f"Original desktop backup: {plan.original_backup}")
        if plan.legacy_config_provenance:
            lines.append(
                "Legacy config note: generic files introduced after the first legacy backup are kept when their original ownership cannot be proven."
            )
    else:
        lines.append("Original desktop backup: unavailable; existing desktop configuration files will be kept.")
    return lines


def launch_self_destruct() -> tuple[bool, str]:
    if not INSTALL_METADATA.is_file():
        return False, "Yakushi install metadata was not found. No removal was started."
    if not SELF_DESTRUCT_SCRIPT.is_file():
        return False, "The installed self-destruction helper is missing. Reinstall Yakushi before removing it."
    kitty = shutil.which("kitty")
    if not kitty:
        return False, "Kitty is required to show the removal and administrator authorization safely."
    try:
        subprocess.Popen(
            [
                kitty,
                "--hold",
                "--title",
                "Yakushi Self Destruction",
                "bash",
                str(SELF_DESTRUCT_SCRIPT),
                "--execute",
            ],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        return False, f"The removal terminal could not be opened: {exc}"
    return True, "Removal started in a dedicated Kitty terminal."


def _restore_path(
    backup: Path,
    relative: str,
    destination: Path,
    *,
    remove_when_absent: bool,
) -> str:
    source = backup / relative
    if source.is_symlink() or source.exists():
        if destination.is_symlink() or destination.exists():
            if destination.is_dir() and not destination.is_symlink():
                shutil.rmtree(destination)
            else:
                destination.unlink()
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir() and not source.is_symlink():
            shutil.copytree(source, destination, symlinks=True)
        else:
            shutil.copy2(source, destination, follow_symlinks=False)
        return f"Restored {destination}"
    if remove_when_absent:
        if destination.is_symlink() or destination.exists():
            if destination.is_dir() and not destination.is_symlink():
                shutil.rmtree(destination)
            else:
                destination.unlink()
        return f"Removed Yakushi-owned {destination}"
    return f"Kept unproven legacy file {destination}"


def _strip_managed_blocks(path: Path) -> bool:
    if not path.is_file():
        return False
    original = path.read_text(encoding="utf-8", errors="ignore")
    updated = original
    names = (
        "ROFI GLASS",
        "WAYBAR GLASS",
        "WINDOW FRAME",
        "NAUTILUS RULE",
    )
    for name in names:
        for marker in ("--", "#"):
            updated = re.sub(
                rf"(?ms)^\s*{re.escape(marker)} YAKUSHI {re.escape(name)} BEGIN.*?^\s*{re.escape(marker)} YAKUSHI {re.escape(name)} END[^\n]*\n?",
                "",
                updated,
            )
    if updated != original:
        path.write_text(updated.rstrip() + "\n", encoding="utf-8")
        return True
    return False


def _strip_shell_blocks(path: Path) -> bool:
    if not path.is_file():
        return False
    original = path.read_text(encoding="utf-8", errors="ignore")
    updated = original
    for name in ("FASTFETCH OVERRIDE", "FASTFETCH AUTORUN"):
        updated = re.sub(
            rf"(?ms)^# >>> YAKUSHI {re.escape(name)} >>>\n.*?^# <<< YAKUSHI {re.escape(name)} <<<\n?",
            "",
            updated,
        )
    updated = re.sub(
        r"(?m)^(\s*)# YAKUSHI DISABLED FASTFETCH AUTORUN: ",
        r"\1",
        updated,
    )
    if updated != original:
        path.write_text(updated.rstrip() + "\n", encoding="utf-8")
        return True
    return False


def _restore_fish_greeting() -> str | None:
    state_file = DATA / "fastfetch.json"
    greeting = Path.home() / ".config" / "fish" / "functions" / "fish_greeting.fish"
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
        autorun = state.get("autorun", {})
    except (OSError, json.JSONDecodeError, AttributeError):
        return None
    if not isinstance(autorun, dict) or not autorun.get("fish_greeting_captured"):
        return None
    kind = autorun.get("fish_greeting_kind")
    if kind not in {"symlink", "file", "absent"}:
        return None
    if kind == "absent" and greeting.is_file() and not greeting.is_symlink():
        current = greeting.read_text(encoding="utf-8", errors="ignore")
        if "# >>> YAKUSHI FASTFETCH GREETING >>>" not in current:
            return f"Kept user-modified {greeting}"
    if greeting.is_symlink() or greeting.exists():
        greeting.unlink()
    if kind == "symlink":
        target = str(autorun.get("fish_greeting_target", "")).strip()
        if target:
            greeting.parent.mkdir(parents=True, exist_ok=True)
            greeting.symlink_to(target)
    elif kind == "file":
        greeting.parent.mkdir(parents=True, exist_ok=True)
        greeting.write_text(str(autorun.get("fish_greeting_original", "")), encoding="utf-8")
    return f"Restored {greeting}"


def _restore_typography_settings() -> str | None:
    try:
        state = json.loads(TYPOGRAPHY_STATE.read_text(encoding="utf-8"))
        originals = state.get("originals", {})
    except (OSError, json.JSONDecodeError, AttributeError):
        return None
    if not isinstance(originals, dict) or not originals:
        return None
    if not shutil.which("gsettings"):
        return "Desktop font preferences were kept because gsettings is unavailable"
    mapping = {
        "font-name": originals.get("gsettings_font"),
        "document-font-name": originals.get("gsettings_document"),
        "monospace-font-name": originals.get("gsettings_monospace"),
    }
    for key, value in mapping.items():
        if not isinstance(value, str) or not value:
            continue
        subprocess.run(
            ["gsettings", "set", "org.gnome.desktop.interface", key, value],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    return "Restored pre-Yakushi desktop font preferences"


def _restore_original_hyprlock() -> str | None:
    target = Path.home() / ".config" / "hypr" / "hyprlock.conf"
    for directory in sorted(BACKUPS.glob("*")):
        metadata = directory / "history.json"
        try:
            value = json.loads(metadata.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(value, dict) or not isinstance(value.get("files"), list):
            continue
        for entry in value["files"]:
            if not isinstance(entry, dict):
                continue
            if str(entry.get("original", "")) != str(target):
                continue
            backup = directory / str(entry.get("backup", ""))
            if backup.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup, target)
                return f"Restored {target}"
    if target.is_file():
        text = target.read_text(encoding="utf-8", errors="ignore")
        if text.startswith("# Generated by Yakushi Control Deck."):
            target.unlink()
            return f"Removed Yakushi-owned {target}"
    return None


def cleanup_user_files() -> list[str]:
    plan = load_plan()
    messages: list[str] = []
    home = Path.home()
    if plan.backup_available and plan.original_backup is not None:
        # The final flag marks paths that were introduced after Yakushi 1.0
        # and are not inherently Yakushi-named. On a legacy installation an
        # absent first-backup entry cannot prove that such a generic file was
        # absent before the feature existed, so it is retained.
        managed = (
            ("waybar/config.jsonc", home / ".config/waybar/config.jsonc", False),
            ("waybar/style.css", home / ".config/waybar/style.css", False),
            ("waybar/scripts", home / ".config/waybar/scripts", False),
            ("rofi/config.rasi", home / ".config/rofi/config.rasi", False),
            ("rofi/yakushi-launcher-opacity.rasi", home / ".config/rofi/yakushi-launcher-opacity.rasi", False),
            ("rofi/yakushi-opacity.rasi", home / ".config/rofi/yakushi-opacity.rasi", False),
            ("rofi/powermenu.rasi", home / ".config/rofi/powermenu.rasi", True),
            ("rofi/scripts", home / ".config/rofi/scripts", False),
            ("rofi/icons/power", home / ".config/rofi/icons/power", True),
            ("hypr/colors.css", home / ".config/hypr/colors.css", False),
            ("hypr/colors.rasi", home / ".config/hypr/colors.rasi", False),
            ("kitty/kitty.conf", home / ".config/kitty/kitty.conf", False),
            ("kitty/yakushi-colors.conf", home / ".config/kitty/yakushi-colors.conf", False),
            ("fastfetch/config.jsonc", home / ".config/fastfetch/config.jsonc", True),
            ("fastfetch/logo.txt", home / ".config/fastfetch/logo.txt", True),
            ("fastfetch/yakushi-logo.txt", home / ".config/fastfetch/yakushi-logo.txt", False),
        )
        for relative, destination, legacy_risky in managed:
            messages.append(_restore_path(
                plan.original_backup,
                relative,
                destination,
                remove_when_absent=(
                    not plan.legacy_config_provenance or not legacy_risky
                ),
            ))
    else:
        messages.append("Original desktop backup unavailable; desktop configuration files were left unchanged")

    for path in (home / ".config/hypr/hyprland.lua", home / ".config/hypr/hyprland.conf"):
        if _strip_managed_blocks(path):
            messages.append(f"Removed Yakushi-managed blocks from {path}")
    for path in (
        home / ".config/fish/config.fish",
        home / ".bashrc",
        home / ".zshrc",
    ):
        if _strip_shell_blocks(path):
            messages.append(f"Removed Yakushi-managed shell blocks from {path}")

    greeting_message = _restore_fish_greeting()
    if greeting_message:
        messages.append(greeting_message)
    typography_message = _restore_typography_settings()
    if typography_message:
        messages.append(typography_message)
    lock_message = _restore_original_hyprlock()
    if lock_message:
        messages.append(lock_message)
    return messages


def _main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Yakushi self-destruction support")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan")
    sub.add_parser("packages")
    sub.add_parser("cleanup-user")
    args = parser.parse_args()
    if args.command == "plan":
        print("\n".join(plan_lines()))
    elif args.command == "packages":
        print("\n".join(load_plan().managed_packages))
    else:
        print("\n".join(cleanup_user_files()))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
