from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path

from .history import record
from .io import atomic_write, load_json, run, save_json
from .paths import NAUTILUS_STATE


LUA_BEGIN = "-- YAKUSHI NAUTILUS RULE BEGIN"
LUA_END = "-- YAKUSHI NAUTILUS RULE END"
CONF_BEGIN = "# YAKUSHI NAUTILUS RULE BEGIN"
CONF_END = "# YAKUSHI NAUTILUS RULE END"


def _hypr_config() -> tuple[Path | None, str | None]:
    directory = Path.home() / ".config" / "hypr"
    lua = directory / "hyprland.lua"
    conf = directory / "hyprland.conf"
    if lua.is_file():
        return lua, "lua"
    if conf.is_file():
        return conf, "conf"
    return None, None


def _live_nautilus_class() -> str:
    proc = run(["hyprctl", "-j", "clients"], timeout=3.0)
    if proc.returncode == 0:
        try:
            clients = json.loads(proc.stdout or "[]")
            for client in clients:
                for key in ("class", "initialClass"):
                    value = str(client.get(key, ""))
                    if "nautilus" in value.lower():
                        return value
        except Exception:
            pass
    return "org.gnome.Nautilus"


def _remove_managed_block(text: str) -> str:
    patterns = [
        r"(?ms)^\s*-- YAKUSHI NAUTILUS RULE BEGIN.*?^\s*-- YAKUSHI NAUTILUS RULE END[^\n]*\n?",
        r"(?ms)^\s*# YAKUSHI NAUTILUS RULE BEGIN.*?^\s*# YAKUSHI NAUTILUS RULE END[^\n]*\n?",
    ]
    for pattern in patterns:
        text = re.sub(pattern, "", text)
    return text.rstrip()


def _block(style: str, opacity: float, class_name: str) -> str:
    opacity = max(0.30, min(1.0, float(opacity)))
    if opacity >= 0.995:
        return ""
    value = f"{opacity:.2f} override {opacity:.2f} override"
    escaped = re.escape(class_name)
    if style == "lua":
        safe_regex = escaped.replace("\\", "\\\\").replace('"', '\\"')
        return f'''{LUA_BEGIN}\n-- Managed by Yakushi Control Deck. Set Nautilus Studio to 100% to remove this override.\nhl.window_rule({{\n    name = "yakushi-nautilus-opacity",\n    match = {{ class = "^({safe_regex})$" }},\n    opacity = "{value}",\n}})\n{LUA_END}'''
    return f'''{CONF_BEGIN}\n# Managed by Yakushi Control Deck. Set Nautilus Studio to 100% to remove this override.\nwindowrulev2 = opacity {value}, class:^({escaped})$\n{CONF_END}'''


def status() -> dict:
    data = load_json(NAUTILUS_STATE, {"opacity": 1.0, "class": "org.gnome.Nautilus"})
    try:
        opacity = max(0.30, min(1.0, float(data.get("opacity", 1.0))))
    except (TypeError, ValueError):
        opacity = 1.0
    config, style = _hypr_config()
    return {
        "opacity": opacity,
        "class": str(data.get("class") or "org.gnome.Nautilus"),
        "available": shutil.which("nautilus") is not None,
        "config": str(config) if config else "",
        "style": style or "",
    }


def apply(opacity: float) -> tuple[bool, str]:
    config, style = _hypr_config()
    if config is None or style is None:
        return False, "Neither ~/.config/hypr/hyprland.lua nor hyprland.conf was found."

    requested = max(0.30, min(1.0, float(opacity)))
    class_name = _live_nautilus_class()
    original = config.read_text()
    previous_state = NAUTILUS_STATE.read_text() if NAUTILUS_STATE.exists() else None
    before_errors = run(["hyprctl", "configerrors"], timeout=3.0).stdout.strip()

    managed = _block(style, requested, class_name)
    updated = _remove_managed_block(original)
    if managed:
        updated = updated + "\n\n" + managed + "\n"
    else:
        updated = updated + "\n"

    record("Nautilus opacity", files=[path for path in (config, NAUTILUS_STATE) if path.exists()])
    atomic_write(config, updated)
    save_json(NAUTILUS_STATE, {"opacity": requested, "class": class_name})

    reload_proc = run(["hyprctl", "reload"], timeout=5.0)
    if reload_proc.returncode != 0:
        atomic_write(config, original)
        if previous_state is None:
            try:
                NAUTILUS_STATE.unlink()
            except FileNotFoundError:
                pass
        else:
            NAUTILUS_STATE.write_text(previous_state)
        run(["hyprctl", "reload"], timeout=5.0)
        return False, "Hyprland rejected the reload. The previous config was restored."

    time.sleep(0.20)
    after_errors = run(["hyprctl", "configerrors"], timeout=3.0).stdout.strip()
    if after_errors and after_errors != before_errors:
        atomic_write(config, original)
        if previous_state is None:
            try:
                NAUTILUS_STATE.unlink()
            except FileNotFoundError:
                pass
        else:
            NAUTILUS_STATE.write_text(previous_state)
        run(["hyprctl", "reload"], timeout=5.0)
        return False, f"A new Hyprland config error appeared. Changes were rolled back: {after_errors}"

    if requested >= 0.995:
        return True, "Nautilus opacity override disabled. Nautilus is back to 100%."
    return True, f"Nautilus opacity set to {round(requested * 100)}% using a compositor-level Hyprland rule."


def open_nautilus() -> tuple[bool, str]:
    if shutil.which("nautilus") is None:
        return False, "Nautilus is not installed. Yakushi keeps it optional to stay bloat-free."
    proc = run(["sh", "-lc", "nohup nautilus --new-window >/tmp/yakushi-nautilus.log 2>&1 &"], timeout=2.0)
    return proc.returncode == 0, ("Nautilus launched." if proc.returncode == 0 else "Nautilus could not be launched.")
