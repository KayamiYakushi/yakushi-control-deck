from __future__ import annotations

import ast
import re
from pathlib import Path

from .history import record
from .io import atomic_write, load_json, run, save_json
from .paths import (
    GTK3_SETTINGS,
    GTK4_SETTINGS,
    KITTY_CONFIG,
    ROFI_CONFIG,
    TYPOGRAPHY_STATE,
    WAYBAR_STYLE,
)


DEFAULT_STATE = {
    "enabled": False,
    "family": "",
    "terminal_too": False,
    "originals": {},
}


def _state() -> dict:
    data = load_json(TYPOGRAPHY_STATE, DEFAULT_STATE)
    merged = DEFAULT_STATE.copy()
    merged.update(data)
    if not isinstance(merged.get("originals"), dict):
        merged["originals"] = {}
    return merged


def status() -> dict:
    data = _state()
    data["available_fonts"] = available_serif_fonts()
    if not data.get("family"):
        data["family"] = data["available_fonts"][0] if data["available_fonts"] else "serif"
    return data


def _fc_family(pattern: str) -> str:
    proc = run(["fc-match", "-f", "%{family[0]}", pattern], timeout=3.0)
    value = (proc.stdout or "").strip()
    return value or pattern


def available_serif_fonts() -> list[str]:
    # No font package is installed by Yakushi.  These are requests to
    # fontconfig; missing families naturally resolve to the user's installed
    # serif fallback and are de-duplicated.
    candidates = [
        "serif",
        "Noto Serif",
        "DejaVu Serif",
        "Liberation Serif",
        "Nimbus Roman",
        "TeX Gyre Schola",
    ]
    result = []
    for candidate in candidates:
        family = _fc_family(candidate)
        if family and family not in result:
            result.append(family)
    return result or ["serif"]


def _ini_font(path: Path) -> str | None:
    if not path.exists():
        return None
    match = re.search(r'(?m)^\s*gtk-font-name\s*=\s*(.+?)\s*$', path.read_text())
    return match.group(1).strip() if match else None


def _set_ini_font(text: str, value: str | None) -> str:
    pattern = r'(?m)^\s*gtk-font-name\s*=\s*.+?\s*$'
    if value is None:
        return re.sub(pattern + r'\n?', '', text, count=1)
    if re.search(pattern, text):
        return re.sub(pattern, f"gtk-font-name={value}", text, count=1)

    settings = re.search(r'(?m)^\[Settings\]\s*$', text)
    if settings:
        insert = settings.end()
        return text[:insert] + f"\ngtk-font-name={value}" + text[insert:]

    if text and not text.endswith("\n"):
        text += "\n"
    return text + f"[Settings]\ngtk-font-name={value}\n"


def _css_font(text: str) -> str | None:
    match = re.search(r'(?m)^\s*font-family\s*:\s*([^;]+);', text)
    return match.group(1).strip() if match else None


def _set_css_font(text: str, value: str | None) -> str:
    pattern = r'(?m)^(\s*font-family\s*:\s*)[^;]+;'
    if value is None:
        return text
    if re.search(pattern, text):
        return re.sub(pattern, rf'\g<1>{value};', text, count=1)
    return text


def _rofi_font(text: str) -> str | None:
    block = re.search(r'(?ms)^\s*configuration\s*\{.*?^\s*\}', text)
    if not block:
        return None
    match = re.search(r'(?m)^\s*font\s*:\s*"([^"]+)"\s*;', block.group(0))
    return match.group(1) if match else None


def _set_rofi_font(text: str, value: str | None) -> str:
    if value is None:
        return text
    pattern = (
        r'(^\s*configuration\s*\{'
        r'(?:(?!^\s*\}).)*?'
        r'^\s*font\s*:\s*)"[^"]+"\s*;'
    )
    updated, count = re.subn(pattern, rf'\g<1>"{value}";', text, count=1, flags=re.M | re.S)
    return updated if count else text


def _kitty_font(text: str) -> str | None:
    match = re.search(r'(?m)^\s*font_family\s+(.+?)\s*$', text)
    return match.group(1).strip() if match else None


def _set_kitty_font(text: str, value: str | None) -> str:
    pattern = r'(?m)^\s*font_family\s+.+$'
    if value is None:
        return re.sub(pattern + r'\n?', '', text, count=1)
    if re.search(pattern, text):
        return re.sub(pattern, f"font_family {value}", text, count=1)
    if text and not text.endswith("\n"):
        text += "\n"
    return text + f"font_family {value}\n"


def _gsettings_get(key: str) -> str | None:
    proc = run(["gsettings", "get", "org.gnome.desktop.interface", key], timeout=3.0)
    if proc.returncode != 0:
        return None
    value = (proc.stdout or "").strip()
    try:
        parsed = ast.literal_eval(value)
        return parsed if isinstance(parsed, str) else None
    except Exception:
        return None


def _gsettings_set(key: str, value: str | None) -> None:
    if value is None:
        return
    run(["gsettings", "set", "org.gnome.desktop.interface", key, value], timeout=3.0)


def _capture_originals() -> dict:
    waybar = WAYBAR_STYLE.read_text() if WAYBAR_STYLE.exists() else ""
    rofi = ROFI_CONFIG.read_text() if ROFI_CONFIG.exists() else ""
    kitty = KITTY_CONFIG.read_text() if KITTY_CONFIG.exists() else ""
    return {
        "gtk3": _ini_font(GTK3_SETTINGS),
        "gtk4": _ini_font(GTK4_SETTINGS),
        "waybar": _css_font(waybar),
        "rofi": _rofi_font(rofi),
        "kitty": _kitty_font(kitty),
        "gsettings_font": _gsettings_get("font-name"),
        "gsettings_document": _gsettings_get("document-font-name"),
        "gsettings_monospace": _gsettings_get("monospace-font-name"),
    }


def _write_targets(family: str, terminal_too: bool, originals: dict | None = None) -> None:
    gtk_value = f"{family} 11"

    for path in (GTK3_SETTINGS, GTK4_SETTINGS):
        current = path.read_text() if path.exists() else ""
        atomic_write(path, _set_ini_font(current, gtk_value))

    if WAYBAR_STYLE.exists():
        current = WAYBAR_STYLE.read_text()
        family_css = f'"{family}", "JetBrainsMono Nerd Font", "Font Awesome 6 Free", serif'
        atomic_write(WAYBAR_STYLE, _set_css_font(current, family_css))

    if ROFI_CONFIG.exists():
        current = ROFI_CONFIG.read_text()
        atomic_write(ROFI_CONFIG, _set_rofi_font(current, f"{family} 12"))

    if terminal_too and KITTY_CONFIG.exists():
        current = KITTY_CONFIG.read_text()
        atomic_write(KITTY_CONFIG, _set_kitty_font(current, family))

    _gsettings_set("font-name", gtk_value)
    _gsettings_set("document-font-name", f"{family} 11")
    if terminal_too:
        _gsettings_set("monospace-font-name", f"{family} 11")


def _restore_originals(originals: dict) -> None:
    for key, path in (("gtk3", GTK3_SETTINGS), ("gtk4", GTK4_SETTINGS)):
        current = path.read_text() if path.exists() else ""
        atomic_write(path, _set_ini_font(current, originals.get(key)))

    if WAYBAR_STYLE.exists() and originals.get("waybar") is not None:
        current = WAYBAR_STYLE.read_text()
        atomic_write(WAYBAR_STYLE, _set_css_font(current, originals.get("waybar")))

    if ROFI_CONFIG.exists() and originals.get("rofi") is not None:
        current = ROFI_CONFIG.read_text()
        atomic_write(ROFI_CONFIG, _set_rofi_font(current, originals.get("rofi")))

    if KITTY_CONFIG.exists():
        current = KITTY_CONFIG.read_text()
        atomic_write(KITTY_CONFIG, _set_kitty_font(current, originals.get("kitty")))

    _gsettings_set("font-name", originals.get("gsettings_font"))
    _gsettings_set("document-font-name", originals.get("gsettings_document"))
    _gsettings_set("monospace-font-name", originals.get("gsettings_monospace"))


def apply(enabled: bool, family: str, terminal_too: bool = False) -> tuple[bool, str]:
    data = _state()
    family = (family or "").strip() or available_serif_fonts()[0]

    targets = [GTK3_SETTINGS, GTK4_SETTINGS, WAYBAR_STYLE, ROFI_CONFIG]
    if KITTY_CONFIG.exists():
        targets.append(KITTY_CONFIG)
    record("Desktop typography", files=[path for path in targets if path.exists()])

    if enabled:
        originals = data.get("originals") or _capture_originals()
        _write_targets(family, terminal_too, originals)
        data.update({
            "enabled": True,
            "family": family,
            "terminal_too": bool(terminal_too),
            "originals": originals,
        })
        save_json(TYPOGRAPHY_STATE, data)
        run(["pkill", "-x", "waybar"], timeout=2.0)
        run(["sh", "-lc", "nohup waybar >/tmp/yakushi-waybar.log 2>&1 &"], timeout=2.0)
        return True, f"Desktop serif enabled: {family}."

    originals = data.get("originals") or {}
    if originals:
        _restore_originals(originals)
    data.update({
        "enabled": False,
        "terminal_too": False,
        "originals": {},
    })
    save_json(TYPOGRAPHY_STATE, data)
    run(["pkill", "-x", "waybar"], timeout=2.0)
    run(["sh", "-lc", "nohup waybar >/tmp/yakushi-waybar.log 2>&1 &"], timeout=2.0)
    return True, "Desktop serif disabled. Previous font settings restored."
