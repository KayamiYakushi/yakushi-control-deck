from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from .io import run
from .paths import BACKUPS


def record(label: str, files=(), runtime: dict | None = None) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    directory = BACKUPS / stamp
    directory.mkdir(parents=True, exist_ok=True)

    entries = []
    for index, path in enumerate(files):
        path = Path(path)
        if not path.exists():
            continue

        backup_name = f"{index:02d}-{path.name}"
        shutil.copy2(path, directory / backup_name)
        entries.append({
            "original": str(path),
            "backup": backup_name,
        })

    metadata = {
        "label": label,
        "files": entries,
        "runtime": runtime,
    }
    (directory / "history.json").write_text(
        json.dumps(metadata, indent=2) + "\n"
    )
    return directory


def _hypr_keyword(key: str, value) -> None:
    run(["hyprctl", "keyword", key, str(value)], timeout=4.0)


def _restore_runtime(runtime: dict | None) -> None:
    if not runtime:
        return

    kind = runtime.get("kind")
    values = runtime.get("values", {})

    if kind == "appearance":
        mapping = [
            ("general:gaps_in", values.get("gaps_in")),
            ("general:gaps_out", values.get("gaps_out")),
            ("general:border_size", values.get("border_size")),
            ("decoration:rounding", values.get("rounding")),
            (
                "decoration:blur:enabled",
                "true" if values.get("blur_enabled") else "false",
            ),
            ("decoration:blur:size", values.get("blur_size")),
            ("decoration:blur:passes", values.get("blur_passes")),
            ("decoration:active_opacity", values.get("active_opacity")),
            ("decoration:inactive_opacity", values.get("inactive_opacity")),
        ]
        for key, value in mapping:
            if value is not None:
                _hypr_keyword(key, value)

    elif kind == "keyboard":
        if "layout" in values:
            _hypr_keyword("input:kb_layout", values["layout"])
        if "repeat_rate" in values:
            _hypr_keyword("input:repeat_rate", values["repeat_rate"])
        if "repeat_delay" in values:
            _hypr_keyword("input:repeat_delay", values["repeat_delay"])

    elif kind == "mouse":
        from .hypr import apply_mouse
        apply_mouse(values, record_history=False)

    elif kind == "monitor":
        name = values.get("name")
        mode = values.get("mode")
        position = values.get("position")
        scale = values.get("scale")
        if all(value is not None for value in (name, mode, position, scale)):
            _hypr_keyword(
                "monitor",
                f"{name},{mode},{position},{scale}",
            )

    elif kind == "monitor_layout":
        for item in values or []:
            name = item.get("name")
            mode = item.get("mode")
            position = item.get("position")
            scale = item.get("scale")
            if all(value is not None for value in (name, mode, position, scale)):
                _hypr_keyword(
                    "monitor",
                    f"{name},{mode},{position},{scale}",
                )

    elif kind == "power_mode":
        mode = values.get("mode", "balanced")
        from .power import apply_mode
        apply_mode(mode, record_history=False)


def latest() -> Path | None:
    if not BACKUPS.exists():
        return None

    candidates = [
        path for path in BACKUPS.iterdir()
        if path.is_dir() and (path / "history.json").exists()
    ]
    if not candidates:
        return None

    return max(candidates, key=lambda path: path.name)


def revert_latest() -> tuple[bool, str]:
    directory = latest()
    if directory is None:
        return False, "Nothing to revert yet."

    try:
        metadata = json.loads((directory / "history.json").read_text())
    except Exception:
        return False, "The latest history entry could not be read."

    restored_paths = []

    for entry in metadata.get("files", []):
        original = Path(entry["original"])
        backup = directory / entry["backup"]

        if not backup.exists():
            continue

        original.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup, original)
        restored_paths.append(original)

    _restore_runtime(metadata.get("runtime"))

    # Refresh applications whose configuration may have been restored.
    restored_strings = {str(path) for path in restored_paths}
    if any("waybar" in value or "colors.css" in value for value in restored_strings):
        run(["pkill", "-x", "waybar"], timeout=2.0)
        run(
            ["sh", "-lc", "nohup waybar >/tmp/yakushi-waybar.log 2>&1 &"],
            timeout=2.0,
        )

    if any(value.endswith("/hyprland.lua") or value.endswith("/hyprland.conf") for value in restored_strings):
        run(["hyprctl", "reload"], timeout=5.0)

    label = metadata.get("label", "Last change")

    # Consume this undo step so the next click walks further back in history.
    shutil.rmtree(directory, ignore_errors=True)

    return True, f"Reverted: {label}"
