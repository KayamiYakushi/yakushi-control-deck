from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from .history import record
from .io import atomic_write, load_json, run, save_json
from .paths import WINDOW_FRAME_STATE

LUA_BEGIN = "-- YAKUSHI WINDOW FRAME BEGIN"
LUA_END = "-- YAKUSHI WINDOW FRAME END"
CONF_BEGIN = "# YAKUSHI WINDOW FRAME BEGIN"
CONF_END = "# YAKUSHI WINDOW FRAME END"


@dataclass
class FrameSettings:
    mode: str = "follow"
    active_border: str = "#e8a29a"
    inactive_border: str = "#3f292a"
    shadow_enabled: bool = True
    shadow_color: str = "#0e0c0d"
    shadow_opacity: float = 0.72
    shadow_range: int = 12
    shadow_render_power: int = 3
    shadow_offset_x: int = 0
    shadow_offset_y: int = 4
    shadow_scale: float = 1.0


def _normalize_hex(value: str, fallback: str) -> str:
    match = re.search(r"#[0-9a-fA-F]{6}", str(value or "").strip())
    return match.group(0).lower() if match else fallback


def _normalized(settings: FrameSettings) -> FrameSettings:
    return FrameSettings(
        mode="follow" if str(settings.mode).lower() == "follow" else "custom",
        active_border=_normalize_hex(settings.active_border, "#e8a29a"),
        inactive_border=_normalize_hex(settings.inactive_border, "#3f292a"),
        shadow_enabled=bool(settings.shadow_enabled),
        shadow_color=_normalize_hex(settings.shadow_color, "#0e0c0d"),
        shadow_opacity=max(0.0, min(1.0, float(settings.shadow_opacity))),
        shadow_range=max(0, min(100, int(settings.shadow_range))),
        shadow_render_power=max(1, min(4, int(settings.shadow_render_power))),
        shadow_offset_x=max(-50, min(50, int(settings.shadow_offset_x))),
        shadow_offset_y=max(-50, min(50, int(settings.shadow_offset_y))),
        shadow_scale=max(0.0, min(1.0, float(settings.shadow_scale))),
    )


def _hypr_config() -> tuple[Path | None, str | None]:
    directory = Path.home() / ".config" / "hypr"
    lua = directory / "hyprland.lua"
    conf = directory / "hyprland.conf"
    if lua.is_file():
        return lua, "lua"
    if conf.is_file():
        return conf, "conf"
    return None, None


def _remove_managed_block(text: str) -> str:
    for pattern in (
        r"(?ms)^\s*-- YAKUSHI WINDOW FRAME BEGIN.*?^\s*-- YAKUSHI WINDOW FRAME END[^\n]*\n?",
        r"(?ms)^\s*# YAKUSHI WINDOW FRAME BEGIN.*?^\s*# YAKUSHI WINDOW FRAME END[^\n]*\n?",
    ):
        text = re.sub(pattern, "", text)
    return text.rstrip()


def _rgba(hex_color: str, opacity: float) -> str:
    alpha = round(max(0.0, min(1.0, opacity)) * 255)
    return f"{hex_color.lower()}{alpha:02x}"


def _block(style: str, settings: FrameSettings) -> str:
    s = _normalized(settings)
    shadow_rgba = _rgba(s.shadow_color, s.shadow_opacity)
    if style == "lua":
        return f'''{LUA_BEGIN}
-- Managed by Yakushi Control Deck. Window Frame Studio owns this final override.
hl.config({{
    general = {{
        col = {{
            active_border = "{s.active_border}",
            inactive_border = "{s.inactive_border}",
        }},
    }},
    decoration = {{
        shadow = {{
            enabled = {str(s.shadow_enabled).lower()},
            range = {s.shadow_range},
            render_power = {s.shadow_render_power},
            color = "{shadow_rgba}",
            color_inactive = "{shadow_rgba}",
            offset = {{{s.shadow_offset_x}, {s.shadow_offset_y}}},
            scale = {s.shadow_scale:.2f},
        }},
    }},
}})
{LUA_END}'''

    active = s.active_border.lstrip("#")
    inactive = s.inactive_border.lstrip("#")
    shadow = shadow_rgba.lstrip("#")
    return f'''{CONF_BEGIN}
# Managed by Yakushi Control Deck. Window Frame Studio owns this final override.
general {{
    col.active_border = rgb({active})
    col.inactive_border = rgb({inactive})
}}
decoration {{
    shadow {{
        enabled = {str(s.shadow_enabled).lower()}
        range = {s.shadow_range}
        render_power = {s.shadow_render_power}
        color = rgba({shadow})
        color_inactive = rgba({shadow})
        offset = {s.shadow_offset_x} {s.shadow_offset_y}
        scale = {s.shadow_scale:.2f}
    }}
}}
{CONF_END}'''


def status() -> FrameSettings:
    raw = load_json(WINDOW_FRAME_STATE, asdict(FrameSettings()))
    base = asdict(FrameSettings())
    if isinstance(raw, dict):
        base.update({k: v for k, v in raw.items() if k in base})
    settings = _normalized(FrameSettings(**base))
    if settings.mode == "follow":
        try:
            from .theme import load as load_palette
            palette = load_palette()
            settings.active_border = palette.accent
            settings.inactive_border = palette.border
            settings.shadow_color = palette.bg
        except Exception:
            pass
    return settings


def _resolve_follow(settings: FrameSettings, palette: dict | None = None) -> FrameSettings:
    s = _normalized(settings)
    if s.mode != "follow":
        return s
    if palette is None:
        try:
            from .theme import load as load_palette
            p = load_palette()
            palette = {"accent": p.accent, "border": p.border, "bg": p.bg}
        except Exception:
            palette = None
    if palette:
        s.active_border = _normalize_hex(str(palette.get("accent", s.active_border)), s.active_border)
        s.inactive_border = _normalize_hex(str(palette.get("border", s.inactive_border)), s.inactive_border)
        s.shadow_color = _normalize_hex(str(palette.get("bg", s.shadow_color)), s.shadow_color)
    return s


def apply(
    settings: FrameSettings,
    *,
    record_history: bool = True,
    palette: dict | None = None,
) -> tuple[bool, str]:
    config, style = _hypr_config()
    if config is None or style is None:
        return False, "Neither ~/.config/hypr/hyprland.lua nor hyprland.conf was found."

    requested = _resolve_follow(settings, palette)
    original = config.read_text(encoding="utf-8")
    previous_state = WINDOW_FRAME_STATE.read_text(encoding="utf-8") if WINDOW_FRAME_STATE.exists() else None
    before_errors = run(["hyprctl", "configerrors"], timeout=3.0).stdout.strip()

    updated = _remove_managed_block(original) + "\n\n" + _block(style, requested) + "\n"
    if record_history:
        record("Window frame and shadow", files=[p for p in (config, WINDOW_FRAME_STATE) if p.exists()])
    atomic_write(config, updated)
    save_json(WINDOW_FRAME_STATE, asdict(_normalized(settings)))

    reload_proc = run(["hyprctl", "reload"], timeout=5.0)
    if reload_proc.returncode != 0:
        atomic_write(config, original)
        if previous_state is None:
            WINDOW_FRAME_STATE.unlink(missing_ok=True)
        else:
            WINDOW_FRAME_STATE.write_text(previous_state, encoding="utf-8")
        run(["hyprctl", "reload"], timeout=5.0)
        return False, "Hyprland rejected Window Frame Studio. The previous config was restored."

    time.sleep(0.20)
    after_errors = run(["hyprctl", "configerrors"], timeout=3.0).stdout.strip()
    if after_errors and after_errors != before_errors:
        atomic_write(config, original)
        if previous_state is None:
            WINDOW_FRAME_STATE.unlink(missing_ok=True)
        else:
            WINDOW_FRAME_STATE.write_text(previous_state, encoding="utf-8")
        run(["hyprctl", "reload"], timeout=5.0)
        return False, f"A new Hyprland config error appeared. Changes were rolled back: {after_errors}"

    mode = "desktop theme" if requested.mode == "follow" else "custom colors"
    shadow = "enabled" if requested.shadow_enabled else "disabled"
    return True, f"Window frame applied using {mode}; shadow {shadow}."


def sync_follow(palette: dict) -> tuple[bool, str]:
    raw = load_json(WINDOW_FRAME_STATE, None)
    if not isinstance(raw, dict) or str(raw.get("mode", "follow")).lower() != "follow":
        return True, "Window Frame Studio is not following the desktop theme."
    base = asdict(FrameSettings())
    base.update({k: v for k, v in raw.items() if k in base})
    return apply(FrameSettings(**base), record_history=False, palette=palette)
