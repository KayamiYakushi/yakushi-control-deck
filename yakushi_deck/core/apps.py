from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

from .io import atomic_write, restore, run
from .history import record
from .paths import (
    HYPR_COLORS_RASI,
    KITTY_CONFIG,
    KITTY_COLOR_OVERRIDE,
    ROFI_CONFIG,
    ROFI_LAUNCHER_OPACITY_OVERRIDE,
    ROFI_OPACITY_OVERRIDE,
    WAYBAR_CONFIG,
    WAYBAR_STYLE,
)


# ---------- Kitty ----------

@dataclass
class KittyState:
    font_size: float
    opacity: float
    padding: int


@dataclass
class KittyColorState:
    mode: str = "custom"
    background: str = "#0e0c0d"
    foreground: str = "#e8a29a"
    accent: str = "#e8a29a"


def _kitty_value(text: str, key: str, default: str) -> str:
    # Kitty uses last assignment wins semantics, including values loaded after
    # theme includes. Mirror that behavior when reading the effective file.
    matches = re.findall(rf'(?m)^\s*{re.escape(key)}\s+(.+?)\s*$', text)
    return matches[-1].strip() if matches else default


def _active_kitty_config() -> Path:
    """Best-effort detection of the config file used by running Kitty instances."""
    env_dir = os.environ.get("KITTY_CONFIG_DIRECTORY")
    if env_dir:
        return Path(os.path.expandvars(os.path.expanduser(env_dir))) / "kitty.conf"

    proc_root = Path("/proc")
    if proc_root.exists():
        for proc in proc_root.iterdir():
            if not proc.name.isdigit():
                continue
            try:
                comm = (proc / "comm").read_text().strip()
                if comm != "kitty":
                    continue
                raw = (proc / "cmdline").read_bytes().split(b"\0")
                args = [item.decode(errors="ignore") for item in raw if item]
                for index, arg in enumerate(args):
                    if arg.startswith("--config="):
                        value = arg.split("=", 1)[1]
                        if value and value.upper() != "NONE":
                            return Path(os.path.expandvars(os.path.expanduser(value)))
                    if arg in {"--config", "-c"} and index + 1 < len(args):
                        value = args[index + 1]
                        if value and value.upper() != "NONE":
                            return Path(os.path.expandvars(os.path.expanduser(value)))
                try:
                    environ = (proc / "environ").read_bytes().split(b"\0")
                    for item in environ:
                        if item.startswith(b"KITTY_CONFIG_DIRECTORY="):
                            value = item.split(b"=", 1)[1].decode(errors="ignore")
                            if value:
                                return Path(os.path.expandvars(os.path.expanduser(value))) / "kitty.conf"
                except Exception:
                    pass
            except Exception:
                continue
    return KITTY_CONFIG


def _kitty_override_for(config: Path) -> Path:
    return config.parent / "yakushi-colors.conf"


def _write_preserving_symlink(path: Path, content: str) -> None:
    target = path.resolve() if path.is_symlink() else path
    atomic_write(target, content)


def kitty_load() -> KittyState:
    config = _active_kitty_config()
    text = config.read_text() if config.exists() else ""

    try:
        font_size = float(_kitty_value(text, "font_size", "12"))
    except ValueError:
        font_size = 12.0

    try:
        opacity = float(_kitty_value(text, "background_opacity", "1"))
    except ValueError:
        opacity = 1.0

    try:
        padding = int(float(_kitty_value(text, "window_padding_width", "0")))
    except ValueError:
        padding = 0

    return KittyState(font_size, opacity, padding)


def _kitty_set(text: str, key: str, value: str) -> str:
    pattern = rf'(?m)^\s*{re.escape(key)}\s+.+$'
    if re.search(pattern, text):
        return re.sub(pattern, f"{key} {value}", text, count=1)

    if text and not text.endswith("\n"):
        text += "\n"
    return text + f"{key} {value}\n"


def _normalize_hex(value: str, default: str) -> str:
    match = re.search(r'#[0-9a-fA-F]{6}', value or '')
    return match.group(0).lower() if match else default


def _kitty_color_mode(text: str) -> str:
    match = re.search(
        r'(?mi)^\s*#\s*YAKUSHI KITTY COLOR MODE\s*:\s*(follow|custom)\s*$',
        text,
    )
    return match.group(1).lower() if match else "custom"


def _kitty_set_color_mode(text: str, mode: str) -> str:
    mode = "follow" if str(mode).lower() == "follow" else "custom"
    line = f"# YAKUSHI KITTY COLOR MODE: {mode}"
    pattern = r'(?mi)^\s*#\s*YAKUSHI KITTY COLOR MODE\s*:\s*(?:follow|custom)\s*$'
    if re.search(pattern, text):
        return re.sub(pattern, line, text, count=1)
    if text and not text.endswith("\n"):
        text += "\n"
    return text + line + "\n"


def _blend_hex(first: str, second: str, amount: float) -> str:
    amount = max(0.0, min(1.0, float(amount)))
    a = _normalize_hex(first, "#000000").lstrip('#')
    b = _normalize_hex(second, "#ffffff").lstrip('#')
    av = [int(a[i:i + 2], 16) for i in (0, 2, 4)]
    bv = [int(b[i:i + 2], 16) for i in (0, 2, 4)]
    out = [round(x + (y - x) * amount) for x, y in zip(av, bv)]
    return "#" + "".join(f"{value:02x}" for value in out)


def _contrast_color(background: str) -> str:
    value = _normalize_hex(background, "#000000").lstrip('#')
    r, g, b = [int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#171313" if luminance > 0.56 else "#f5eeee"


def _kitty_color_properties(background: str, foreground: str, accent: str) -> dict[str, str]:
    background = _normalize_hex(background, "#0e0c0d")
    foreground = _normalize_hex(foreground, "#e8a29a")
    accent = _normalize_hex(accent, "#e8a29a")
    selected = _contrast_color(accent)

    # Keep the ANSI palette inside the same tonal family. This is what makes
    # Fastfetch, prompts and CLI color output follow the selected Yakushi tone
    # instead of remaining stuck on an older red/pink palette.
    ansi = {
        "color0": background,
        "color1": accent,
        "color2": _blend_hex(accent, foreground, 0.18),
        "color3": _blend_hex(accent, foreground, 0.34),
        "color4": _blend_hex(accent, foreground, 0.50),
        "color5": _blend_hex(accent, foreground, 0.27),
        "color6": _blend_hex(accent, foreground, 0.43),
        "color7": foreground,
        "color8": _blend_hex(background, foreground, 0.34),
        "color9": _blend_hex(accent, foreground, 0.16),
        "color10": _blend_hex(accent, foreground, 0.30),
        "color11": _blend_hex(accent, foreground, 0.45),
        "color12": _blend_hex(accent, foreground, 0.60),
        "color13": _blend_hex(accent, foreground, 0.38),
        "color14": _blend_hex(accent, foreground, 0.54),
        "color15": _blend_hex(foreground, "#ffffff" if selected == "#171313" else foreground, 0.16),
    }
    return {
        "background": background,
        "foreground": foreground,
        "cursor": accent,
        "cursor_text_color": background,
        "selection_background": accent,
        "selection_foreground": selected,
        "url_color": accent,
        "active_border_color": accent,
        "inactive_border_color": _blend_hex(background, foreground, 0.24),
        "tab_bar_background": background,
        "active_tab_background": accent,
        "active_tab_foreground": selected,
        "inactive_tab_background": _blend_hex(background, foreground, 0.10),
        "inactive_tab_foreground": foreground,
        **ansi,
    }


def _write_kitty_color_block(config: Path, override: Path, value: "KittyColorState") -> None:
    """Write a final concrete color block so no earlier theme include can win."""
    background = _normalize_hex(value.background, "#0e0c0d")
    foreground = _normalize_hex(value.foreground, "#e8a29a")
    accent = _normalize_hex(value.accent, foreground)
    mode = "follow" if str(value.mode).lower() == "follow" else "custom"
    props = _kitty_color_properties(background, foreground, accent)

    override_text = f"# Generated by Yakushi Control Deck.\n# YAKUSHI KITTY COLOR MODE: {mode}\n"
    override_text += "".join(f"{key} {color}\n" for key, color in props.items())
    override.parent.mkdir(parents=True, exist_ok=True)
    _write_preserving_symlink(override, override_text)

    text = config.read_text() if config.exists() else ""
    # Remove older include-based integration and any previous managed block.
    text = re.sub(
        r"(?ms)^# >>> YAKUSHI TERMINAL COLORS >>>\n.*?^# <<< YAKUSHI TERMINAL COLORS <<<\n?",
        "",
        text,
    )
    kept = []
    for line in text.splitlines():
        stripped = line.strip()
        if re.fullmatch(r"include\s+(?:\./)?yakushi-colors\.conf", stripped, flags=re.I):
            continue
        if stripped == "# YAKUSHI KITTY COLORS - KEEP THIS INCLUDE LAST":
            continue
        kept.append(line)
    text = "\n".join(kept).rstrip()
    if text:
        text += "\n\n"
    text += f"# >>> YAKUSHI TERMINAL COLORS >>>\n# YAKUSHI KITTY COLOR MODE: {mode}\n"
    text += "".join(f"{key} {color}\n" for key, color in props.items())
    text += "# <<< YAKUSHI TERMINAL COLORS <<<\n"
    config.parent.mkdir(parents=True, exist_ok=True)
    _write_preserving_symlink(config, text)

def _reload_kitty_config() -> None:
    # Kitty supports SIGUSR1 config reload. This makes the current window pick
    # up colors immediately when possible, while new windows always get them.
    run(["pkill", "-USR1", "-x", "kitty"], timeout=2.0)


def kitty_colors_load() -> KittyColorState:
    config = _active_kitty_config()
    override = _kitty_override_for(config)
    # The managed block in kitty.conf is authoritative. The override file remains
    # a portable representation for diagnostics and migration.
    config_text = config.read_text() if config.exists() else ""
    if "# >>> YAKUSHI TERMINAL COLORS >>>" in config_text:
        text = config_text
    elif override.exists():
        text = override.read_text()
    else:
        text = config_text
    background = _normalize_hex(_kitty_value(text, "background", "#0e0c0d"), "#0e0c0d")
    foreground = _normalize_hex(_kitty_value(text, "foreground", "#e8a29a"), "#e8a29a")
    accent_raw = _kitty_value(text, "cursor", "") or _kitty_value(text, "color1", "") or foreground
    accent = _normalize_hex(accent_raw, foreground)
    return KittyColorState(
        mode=_kitty_color_mode(text),
        background=background,
        foreground=foreground,
        accent=accent,
    )


def _kitty_write_colors(value: KittyColorState, *, history: bool) -> tuple[bool, str]:
    background = _normalize_hex(value.background, "#0e0c0d")
    foreground = _normalize_hex(value.foreground, "#e8a29a")
    accent = _normalize_hex(value.accent, foreground)
    mode = "follow" if str(value.mode).lower() == "follow" else "custom"

    override = f"# Generated by Yakushi Control Deck.\n# YAKUSHI KITTY COLOR MODE: {mode}\n"
    for key, color in _kitty_color_properties(background, foreground, accent).items():
        override += f"{key} {color}\n"

    config = _active_kitty_config()
    override_path = _kitty_override_for(config)
    if history:
        record("Kitty terminal colors", files=[config, override_path])
    _write_kitty_color_block(config, override_path, KittyColorState(mode, background, foreground, accent))
    _reload_kitty_config()

    # Read back the final managed block. This catches write/path problems instead
    # of reporting success while Kitty is still using a different file.
    verify = config.read_text() if config.exists() else ""
    expected = {"background": background, "foreground": foreground, "cursor": accent}
    missing = [key for key, color in expected.items() if not re.search(rf"(?m)^\s*{key}\s+{re.escape(color)}\s*$", verify, flags=re.I)]
    if missing:
        return False, "Kitty color write verification failed for: " + ", ".join(missing)

    base = (
        "Kitty colors now follow the Yakushi desktop palette."
        if mode == "follow"
        else "Custom Kitty colors applied."
    )
    return True, f"{base} Active config: {config}"


def kitty_colors_save(value: KittyColorState) -> tuple[bool, str]:
    return _kitty_write_colors(value, history=True)


def kitty_sync_theme(palette) -> tuple[bool, str]:
    """Refresh Kitty colors only when Terminal Studio is in FOLLOW mode."""
    current = kitty_colors_load()
    if current.mode != "follow":
        return True, "Kitty color mode is custom; desktop theme sync skipped."

    def pick(name: str, default: str) -> str:
        if isinstance(palette, dict):
            return str(palette.get(name, default))
        return str(getattr(palette, name, default))

    return _kitty_write_colors(
        KittyColorState(
            mode="follow",
            background=pick("bg", current.background),
            foreground=pick("fg", current.foreground),
            accent=pick("accent", current.accent),
        ),
        history=False,
    )


def kitty_save(value: KittyState) -> tuple[bool, str]:
    config = _active_kitty_config()
    text = config.read_text() if config.exists() else ""
    text = _kitty_set(text, "font_size", f"{value.font_size:.1f}")
    text = _kitty_set(text, "background_opacity", f"{value.opacity:.2f}")
    text = _kitty_set(text, "window_padding_width", str(value.padding))
    text = _kitty_set(text, "dynamic_background_opacity", "yes")

    record("Kitty settings", files=[config])
    _write_preserving_symlink(config, text)
    _reload_kitty_config()
    return True, f"Kitty configuration updated: {config}"


# ---------- Rofi ----------

@dataclass
class RofiState:
    font: str
    width: int
    radius: int
    padding: int
    lines: int
    opacity: float


ROFI_GLASS_LUA_BEGIN = "-- YAKUSHI ROFI GLASS BEGIN"
ROFI_GLASS_LUA_END = "-- YAKUSHI ROFI GLASS END"
ROFI_GLASS_CONF_BEGIN = "# YAKUSHI ROFI GLASS BEGIN"
ROFI_GLASS_CONF_END = "# YAKUSHI ROFI GLASS END"


def _rofi_hypr_config() -> tuple[Path | None, str | None]:
    directory = Path.home() / ".config" / "hypr"
    lua = directory / "hyprland.lua"
    conf = directory / "hyprland.conf"
    if lua.is_file():
        return lua, "lua"
    if conf.is_file():
        return conf, "conf"
    return None, None


def _remove_rofi_glass_rule(text: str) -> str:
    patterns = (
        r"(?ms)^\s*-- YAKUSHI ROFI GLASS BEGIN.*?^\s*-- YAKUSHI ROFI GLASS END[^\n]*\n?",
        r"(?ms)^\s*# YAKUSHI ROFI GLASS BEGIN.*?^\s*# YAKUSHI ROFI GLASS END[^\n]*\n?",
    )
    for pattern in patterns:
        text = re.sub(pattern, "", text)
    return text


def _rofi_glass_rule(style: str) -> str:
    # Rofi-wayland exposes the layer namespace "rofi". Hyprland needs a
    # layer rule in addition to transparent Rasi colors to render real blur.
    if style == "lua":
        return f'''{ROFI_GLASS_LUA_BEGIN}
-- Managed by Yakushi Control Deck. Blur strength stays under Appearance.
hl.layer_rule({{
    name         = "yakushi-rofi-glass",
    match        = {{ namespace = "rofi" }},
    blur         = true,
    ignore_alpha = 0.20,
}})
{ROFI_GLASS_LUA_END}'''
    return f'''{ROFI_GLASS_CONF_BEGIN}
# Managed by Yakushi Control Deck. Blur strength stays under Appearance.
layerrule {{
    name = yakushi-rofi-glass
    match:namespace = rofi
    blur = true
    ignore_alpha = 0.20
}}
{ROFI_GLASS_CONF_END}'''


def _rofi_glass_hypr_text(text: str, style: str, enabled: bool) -> str:
    cleaned = _remove_rofi_glass_rule(text)
    if not enabled:
        return cleaned
    return cleaned.rstrip() + "\n\n" + _rofi_glass_rule(style) + "\n"



ROFI_THEME_PRESETS = (
    (
        "signature",
        "SIGNATURE",
        "Unified tonal surface with a quiet selection state.",
        {
            "width": 600,
            "window_radius": 18,
            "window_padding": 16,
            "window_border": 1,
            "main_spacing": 10,
            "input_bg": "@yak-surface-alt",
            "input_border": 1,
            "input_radius": 11,
            "input_padding": "10px 13px",
            "list_bg": "@yak-surface",
            "list_radius": 12,
            "list_padding": "4px",
            "lines": 7,
            "row_padding": "10px 11px",
            "row_radius": 8,
            "selected_bg": "@yak-hover",
            "icon_size": 20,
        },
    ),
    (
        "compact",
        "COMPACT",
        "Tighter unified surface for fast keyboard-first launching.",
        {
            "width": 530,
            "window_radius": 14,
            "window_padding": 13,
            "window_border": 1,
            "main_spacing": 8,
            "input_bg": "@yak-surface-alt",
            "input_border": 1,
            "input_radius": 9,
            "input_padding": "8px 11px",
            "list_bg": "@yak-surface",
            "list_radius": 10,
            "list_padding": "3px",
            "lines": 6,
            "row_padding": "8px 9px",
            "row_radius": 7,
            "selected_bg": "@yak-hover",
            "icon_size": 18,
        },
    ),
    (
        "borderless",
        "BORDERLESS",
        "Minimal chrome with one continuous tonal application surface.",
        {
            "width": 580,
            "window_radius": 16,
            "window_padding": 15,
            "window_border": 0,
            "main_spacing": 9,
            "input_bg": "@yak-surface-alt",
            "input_border": 0,
            "input_radius": 10,
            "input_padding": "9px 12px",
            "list_bg": "@yak-surface",
            "list_radius": 11,
            "list_padding": "3px",
            "lines": 7,
            "row_padding": "9px 10px",
            "row_radius": 7,
            "selected_bg": "@yak-hover",
            "icon_size": 20,
        },
    ),
    (
        "lounge",
        "LOUNGE",
        "More breathing room while keeping the list visually continuous.",
        {
            "width": 660,
            "window_radius": 22,
            "window_padding": 20,
            "window_border": 1,
            "main_spacing": 12,
            "input_bg": "@yak-surface-alt",
            "input_border": 1,
            "input_radius": 13,
            "input_padding": "11px 15px",
            "list_bg": "@yak-surface",
            "list_radius": 14,
            "list_padding": "5px",
            "lines": 8,
            "row_padding": "11px 13px",
            "row_radius": 9,
            "selected_bg": "@yak-hover",
            "icon_size": 21,
        },
    ),
    (
        "raycast_glass",
        "RAYCAST GLASS",
        "A compact liquid-glass launcher with fuzzy search and clickable actions.",
        {
            "width": 620,
            "window_radius": 20,
            "window_padding": 10,
            "window_border": 1,
            "main_spacing": 0,
            "input_bg": "@yak-surface-alt",
            "input_border": 1,
            "input_radius": 12,
            "input_padding": "10px 13px",
            "list_bg": "@yak-surface",
            "list_radius": 11,
            "list_padding": "4px",
            "lines": 6,
            "row_padding": "8px 10px",
            "row_radius": 8,
            "selected_bg": "@yak-hover",
            "selected_fg": "@yak-fg",
            "icon_size": 20,
            "layout": "raycast",
        },
    ),
)


def rofi_theme_presets() -> tuple[tuple[str, str, str], ...]:
    return tuple((key, title, description) for key, title, description, _spec in ROFI_THEME_PRESETS)


def _rofi_theme_spec(name: str):
    for key, title, description, spec in ROFI_THEME_PRESETS:
        if key == name:
            return key, title, description, spec
    return ROFI_THEME_PRESETS[0]


def _rofi_theme_text(name: str, font: str) -> str:
    key, _title, _description, spec = _rofi_theme_spec(name)
    font = (font or "JetBrainsMono Nerd Font 12").replace('"', "")
    is_raycast = spec.get("layout") == "raycast"
    main_children = (
        "[ inputbar, textbox-section, message, listview, footer ]"
        if is_raycast
        else "[ inputbar, listview ]"
    )
    input_children = "[ prompt, entry, case-indicator ]" if is_raycast else "[ prompt, entry ]"
    selected_fg = spec.get("selected_fg", "@yak-fg")
    fixed_height = "false" if is_raycast else "true"
    raycast_configuration = (
        '    display-run: " ";\n'
        '    display-filebrowser: "󰉋 ";\n'
        '    display-window: "󰖯 ";\n'
        '    matching: "fuzzy";\n'
        '    sort: true;\n'
        if is_raycast
        else ""
    )
    raycast_widgets = (
        """

textbox-section {
    expand: false;
    content: "APPLICATIONS";
    background-color: transparent;
    text-color: @yak-muted;
    padding: 9px 10px 4px 10px;
}

footer {
    expand: false;
    orientation: horizontal;
    background-color: transparent;
    border: 1px 0px 0px 0px;
    border-color: @yak-border;
    padding: 7px 8px 0px 8px;
    margin: 5px 0px 0px 0px;
    spacing: 6px;
    children: [ textbox-footer-label, footer-spacer, button-close, button-open ];
}

textbox-footer-label {
    expand: false;
    content: "YAKUSHI";
    background-color: transparent;
    text-color: @yak-muted;
    vertical-align: 0.5;
}

footer-spacer {
    expand: true;
}

button-close {
    expand: false;
    content: "Esc  Close";
    action: "kb-cancel";
    background-color: @yak-surface-alt;
    text-color: @yak-muted;
    border: 1px;
    border-color: @yak-border;
    border-radius: 6px;
    padding: 3px 7px;
    vertical-align: 0.5;
}

button-open {
    expand: false;
    content: "Enter  Open";
    action: "kb-accept-entry";
    background-color: @yak-hover;
    text-color: @yak-fg;
    border: 1px;
    border-color: @yak-border;
    border-radius: 6px;
    padding: 3px 7px;
    vertical-align: 0.5;
}
"""
        if is_raycast
        else ""
    )
    return f"""/* YAKUSHI ROFI THEME: {key} */
/* Geometry comes from Rofi Studio; all colors come from Theme Studio. */
@import "../hypr/colors.rasi"

configuration {{
    modi: "drun,run,filebrowser,window";
    show-icons: true;
    display-drun: " ";
{raycast_configuration}    drun-display-format: "{{name}}";
    font: "{font}";
}}

* {{
    bg: @yak-bg;
    surface: @yak-surface;
    surface-alt: @yak-surface-alt;
    accent: @yak-accent;
    hover: @yak-hover;
    border-col: @yak-border;
    text-col: @yak-fg;
    text-alt: @yak-muted;
    selected-fg: @yak-selected-fg;
    background-color: transparent;
    text-color: @text-col;
}}

window {{
    transparency: "real";
    background-color: @yak-rofi-bg;
    border: {spec["window_border"]}px;
    border-color: @yak-border;
    border-radius: {spec["window_radius"]}px;
    width: {spec["width"]}px;
    padding: {spec["window_padding"]}px;
}}

mainbox {{
    background-color: transparent;
    children: {main_children};
    spacing: {spec["main_spacing"]}px;
}}

inputbar {{
    background-color: {spec["input_bg"]};
    border: {spec["input_border"]}px;
    border-color: @yak-border;
    border-radius: {spec["input_radius"]}px;
    padding: {spec["input_padding"]};
    children: {input_children};
}}

prompt {{
    background-color: transparent;
    text-color: @yak-accent;
    margin: 0px 9px 0px 0px;
}}

entry {{
    background-color: transparent;
    text-color: @yak-fg;
    placeholder: "Search applications...";
    placeholder-color: @yak-muted;
}}

listview {{
    background-color: {spec["list_bg"]};
    border: 0px;
    border-color: #00000000;
    border-radius: {spec["list_radius"]}px;
    padding: {spec["list_padding"]};
    lines: {spec["lines"]};
    columns: 1;
    spacing: 0px;
    cycle: true;
    dynamic: true;
    fixed-height: {fixed_height};
    scrollbar: false;
}}

element {{
    background-color: transparent;
    text-color: @yak-fg;
    padding: {spec["row_padding"]};
    border: 0px;
    border-color: #00000000;
    border-radius: {spec["row_radius"]}px;
}}

element normal.normal {{
    background-color: transparent;
    text-color: @yak-fg;
}}

element alternate.normal {{
    background-color: transparent;
    text-color: @yak-fg;
}}

element selected {{
    background-color: {spec["selected_bg"]};
    text-color: {selected_fg};
    border-color: #00000000;
}}

element selected.normal {{
    background-color: {spec["selected_bg"]};
    text-color: {selected_fg};
}}

element-text {{
    background-color: transparent;
    text-color: inherit;
    vertical-align: 0.5;
}}

element-icon {{
    background-color: transparent;
    size: {spec["icon_size"]}px;
    margin: 0px 10px 0px 0px;
}}

message {{
    background-color: @yak-surface;
    border-radius: 10px;
}}

textbox {{
    background-color: transparent;
    text-color: @yak-muted;
}}
{raycast_widgets}

@import "yakushi-launcher-opacity.rasi"
"""


def rofi_apply_theme(name: str) -> tuple[bool, str]:
    if not ROFI_CONFIG.exists():
        return False, "Rofi config.rasi was not found."

    key, title, _description, _spec = _rofi_theme_spec(name)
    current = rofi_load()
    original = ROFI_CONFIG.read_text()
    override_original = (
        ROFI_LAUNCHER_OPACITY_OVERRIDE.read_text()
        if ROFI_LAUNCHER_OPACITY_OVERRIDE.exists()
        else ""
    )
    hypr_config, hypr_style = _rofi_hypr_config()
    hypr_original = hypr_config.read_text() if hypr_config is not None else ""
    hypr_updated = (
        _rofi_glass_hypr_text(hypr_original, hypr_style, key == "raycast_glass")
        if hypr_config is not None and hypr_style is not None
        else hypr_original
    )
    hypr_changed = hypr_config is not None and hypr_updated != hypr_original
    before_errors = (
        run(["hyprctl", "configerrors"], timeout=3.0).stdout.strip()
        if hypr_changed
        else ""
    )
    files = [ROFI_CONFIG]
    if ROFI_LAUNCHER_OPACITY_OVERRIDE.exists():
        files.append(ROFI_LAUNCHER_OPACITY_OVERRIDE)
    if hypr_changed and hypr_config is not None:
        files.append(hypr_config)
    record(f"Rofi theme: {title}", files=files)

    atomic_write(ROFI_CONFIG, _rofi_theme_text(key, current.font))
    colors = HYPR_COLORS_RASI.read_text() if HYPR_COLORS_RASI.exists() else ""
    base = _named_rasi_color(colors, "yak-bg") or _named_rasi_color(colors, "bg") or "#1a1414"
    base_match = re.search(r'#[0-9a-fA-F]{6}', base)
    base = base_match.group(0) if base_match else "#1a1414"
    atomic_write(
        ROFI_LAUNCHER_OPACITY_OVERRIDE,
        _rofi_override_text(base, current.opacity),
    )

    def rollback(*, restore_hypr: bool = False) -> None:
        atomic_write(ROFI_CONFIG, original)
        if override_original:
            atomic_write(ROFI_LAUNCHER_OPACITY_OVERRIDE, override_original)
        else:
            try:
                ROFI_LAUNCHER_OPACITY_OVERRIDE.unlink()
            except FileNotFoundError:
                pass
        if restore_hypr and hypr_changed and hypr_config is not None:
            _write_preserving_symlink(hypr_config, hypr_original)
            run(["hyprctl", "reload"], timeout=5.0)

    proc = run(["rofi", "-no-config", "-theme", str(ROFI_CONFIG), "-dump-theme"], timeout=5.0)
    if proc.returncode != 0:
        rollback()
        detail = (proc.stderr or proc.stdout).strip()
        return False, f"Rofi rejected {title}. Previous theme restored. {detail}".strip()

    if hypr_changed and hypr_config is not None:
        _write_preserving_symlink(hypr_config, hypr_updated)
        reload_proc = run(["hyprctl", "reload"], timeout=5.0)
        if reload_proc.returncode != 0:
            rollback(restore_hypr=True)
            return False, "Hyprland rejected the Rofi blur rule. Theme and compositor config were restored."

        time.sleep(0.20)
        after_errors = run(["hyprctl", "configerrors"], timeout=3.0).stdout.strip()
        if after_errors and after_errors != before_errors:
            rollback(restore_hypr=True)
            return False, f"A new Hyprland config error appeared. Changes were rolled back: {after_errors}"

    if key == "raycast_glass":
        if hypr_config is None:
            return True, (
                "Rofi theme applied: RAYCAST GLASS. Compact actions are active; "
                "no Hyprland config was found, so compositor blur was not changed."
            )
        return True, "RAYCAST GLASS applied with compact actions and Hyprland layer blur."
    return True, f"Rofi theme applied: {title}. Colors follow Yakushi Theme Studio."


def _rasi_prop(text: str, block: str, prop: str, default: str) -> str:
    block_match = re.search(
        rf'(?m)^\s*{re.escape(block)}\s*\{{(.*?)^\s*\}}',
        text,
        flags=re.S,
    )
    if not block_match:
        return default

    prop_match = re.search(
        rf'(?m)^\s*{re.escape(prop)}\s*:\s*([^;]+);',
        block_match.group(1),
    )
    return prop_match.group(1).strip() if prop_match else default


def _configuration_prop(text: str, prop: str, default: str) -> str:
    block = re.search(r'(?m)^\s*configuration\s*\{(.*?)^\s*\}', text, flags=re.S)
    if not block:
        return default

    match = re.search(rf'(?m)^\s*{re.escape(prop)}\s*:\s*([^;]+);', block.group(1))
    return match.group(1).strip() if match else default


def _px(value: str, default: int) -> int:
    match = re.search(r'(\d+)px', value)
    return int(match.group(1)) if match else default


def _opacity_from_color(value: str) -> float:
    value = (value or "").strip()

    match = re.search(r'#([0-9a-fA-F]{8})\b', value)
    if match:
        return int(match.group(1)[6:8], 16) / 255

    match = re.search(
        r'rgba\(\s*\d+%?\s*,\s*\d+%?\s*,\s*\d+%?\s*,\s*([0-9.]+)%?\s*\)',
        value,
        flags=re.I,
    )
    if match:
        raw = float(match.group(1))
        return max(0.0, min(1.0, raw / 100.0 if raw > 1.0 else raw))

    return 1.0


def _named_rasi_color(text: str, name: str, default: str = "") -> str:
    match = re.search(
        rf'(?m)^\s*{re.escape(name)}\s*:\s*(#[0-9a-fA-F]{{6,8}})\s*;',
        text,
    )
    return match.group(1) if match else default


def _set_named_rasi_color(text: str, name: str, value: str) -> str:
    pattern = rf'(?m)^(\s*{re.escape(name)}\s*:\s*)#[0-9a-fA-F]{{6,8}}\s*;'
    if re.search(pattern, text):
        return re.sub(pattern, rf'\g<1>{value};', text, count=1)

    block = re.search(r'(?ms)^\s*\*\s*\{.*?^\s*\}', text)
    if block:
        closing = block.end() - 1
        return text[:closing] + f"    {name}: {value};\n" + text[closing:]

    if text and not text.endswith("\n"):
        text += "\n"
    return text + f"\n* {{\n    {name}: {value};\n}}\n"


def _set_or_add_rasi_block(text: str, block: str, prop: str, value: str) -> tuple[str, bool]:
    updated, ok = _set_rasi_block(text, block, prop, value)
    if ok:
        return updated, True

    block_match = re.search(
        rf'(?ms)^\s*{re.escape(block)}\s*\{{.*?^\s*\}}',
        text,
    )
    if not block_match:
        return text, False

    closing = block_match.end() - 1
    indent_match = re.match(r'([ \t]*)', block_match.group(0))
    indent = (indent_match.group(1) if indent_match else "") + "    "
    return text[:closing] + f"{indent}{prop}: {value};\n" + text[closing:], True


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    match = re.search(r'#([0-9a-fA-F]{6})', value or '')
    hex_value = match.group(1) if match else '1a1414'
    return tuple(int(hex_value[index:index + 2], 16) for index in (0, 2, 4))


def _rgba_rasi(value: str, opacity: float) -> str:
    r, g, b = _hex_to_rgb(value)
    percent = round(max(0.0, min(1.0, opacity)) * 100)
    return f"rgba({r}, {g}, {b}, {percent}%)"


def _rofi_override_text(
    base: str,
    opacity: float,
    surface: str | None = None,
    surface_alt: str | None = None,
    hover: str | None = None,
) -> str:
    # The Rofi opacity slider controls every background surface, not only the
    # outer window. Text and icons remain fully opaque.
    if HYPR_COLORS_RASI.exists():
        colors = HYPR_COLORS_RASI.read_text()
        surface = surface or _named_rasi_color(colors, "yak-surface")
        surface_alt = surface_alt or _named_rasi_color(colors, "yak-surface-alt")
        hover = hover or _named_rasi_color(colors, "yak-hover")

    surface = surface or base
    surface_alt = surface_alt or surface
    hover = hover or surface_alt

    window_rgba = _rgba_rasi(base, opacity)
    surface_rgba = _rgba_rasi(surface, opacity)
    surface_alt_rgba = _rgba_rasi(surface_alt, opacity)
    hover_rgba = _rgba_rasi(hover, opacity)

    return (
        "/* Generated by Yakushi Control Deck. Keep this import last. */\n"
        "window {\n"
        '    transparency: "real";\n'
        f"    background-color: {window_rgba};\n"
        "}\n"
        "mainbox {\n"
        "    background-color: transparent;\n"
        "}\n"
        "inputbar {\n"
        f"    background-color: {surface_alt_rgba};\n"
        "}\n"
        "listview {\n"
        f"    background-color: {surface_rgba};\n"
        "}\n"
        "element {\n"
        "    background-color: transparent;\n"
        "}\n"
        "element normal.normal {\n"
        "    background-color: transparent;\n"
        "}\n"
        "element alternate.normal {\n"
        "    background-color: transparent;\n"
        "}\n"
        "element selected {\n"
        f"    background-color: {hover_rgba};\n"
        "}\n"
        "element selected.normal {\n"
        f"    background-color: {hover_rgba};\n"
        "}\n"
        "message {\n"
        f"    background-color: {surface_rgba};\n"
        "}\n"
        "textbox {\n"
        "    background-color: transparent;\n"
        "}\n"
        "button-close {\n"
        f"    background-color: {surface_alt_rgba};\n"
        "}\n"
        "button-open {\n"
        f"    background-color: {hover_rgba};\n"
        "}\n"
    )

def _ensure_rofi_override_import(text: str) -> str:
    import_line = '@import "yakushi-launcher-opacity.rasi"'
    text = re.sub(
        r'(?m)^\s*@import\s+["\']yakushi-(?:launcher-)?opacity\.rasi["\']\s*;?\s*$',
        '',
        text,
    ).rstrip()
    return text + '\n\n' + import_line + '\n'


def rofi_load() -> RofiState:
    text = ROFI_CONFIG.read_text() if ROFI_CONFIG.exists() else ""
    colors = HYPR_COLORS_RASI.read_text() if HYPR_COLORS_RASI.exists() else ""

    font = _configuration_prop(text, "font", '"JetBrainsMono Nerd Font 12"').strip('"')

    lines_raw = _rasi_prop(text, "listview", "lines", "7")
    try:
        lines = int(lines_raw)
    except ValueError:
        lines = 7

    if ROFI_LAUNCHER_OPACITY_OVERRIDE.exists():
        override = ROFI_LAUNCHER_OPACITY_OVERRIDE.read_text()
    elif ROFI_OPACITY_OVERRIDE.exists():
        # Migration path for installations created before launcher and power
        # menu opacity overrides were separated.
        override = ROFI_OPACITY_OVERRIDE.read_text()
    else:
        override = ""
    opacity_source = _rasi_prop(override, "window", "background-color", "") if override else ""
    if not opacity_source:
        opacity_source = _named_rasi_color(colors, "yak-rofi-bg")
    if not opacity_source:
        opacity_source = _rasi_prop(text, "window", "background-color", "#1a1414ff")

    return RofiState(
        font=font,
        width=_px(_rasi_prop(text, "window", "width", "650px"), 650),
        radius=_px(_rasi_prop(text, "window", "border-radius", "14px"), 14),
        padding=_px(_rasi_prop(text, "window", "padding", "25px"), 25),
        lines=lines,
        opacity=_opacity_from_color(opacity_source),
    )


def _set_rasi_block(text: str, block: str, prop: str, value: str) -> tuple[str, bool]:
    pattern = (
        rf'(^\s*{re.escape(block)}\s*\{{'
        rf'(?:(?!^\s*\}}).)*?'
        rf'^\s*{re.escape(prop)}\s*:\s*)[^;]+;'
    )
    updated, count = re.subn(
        pattern,
        rf'\g<1>{value};',
        text,
        count=1,
        flags=re.S | re.M,
    )
    return updated, count == 1


def _set_rasi_configuration(text: str, prop: str, value: str) -> tuple[str, bool]:
    pattern = (
        rf'(^\s*configuration\s*\{{'
        rf'(?:(?!^\s*\}}).)*?'
        rf'^\s*{re.escape(prop)}\s*:\s*)[^;]+;'
    )
    updated, count = re.subn(
        pattern,
        rf'\g<1>{value};',
        text,
        count=1,
        flags=re.S | re.M,
    )
    return updated, count == 1


def rofi_save(value: RofiState) -> tuple[bool, str]:
    if not ROFI_CONFIG.exists():
        return False, "Rofi config.rasi was not found."

    original = ROFI_CONFIG.read_text()
    colors_original = HYPR_COLORS_RASI.read_text() if HYPR_COLORS_RASI.exists() else ""
    override_original = (
        ROFI_LAUNCHER_OPACITY_OVERRIDE.read_text()
        if ROFI_LAUNCHER_OPACITY_OVERRIDE.exists()
        else ""
    )
    text = original
    colors = colors_original

    base = _named_rasi_color(colors, "yak-bg") or _named_rasi_color(colors, "bg") or "#1a1414"
    base_match = re.search(r'#[0-9a-fA-F]{6}', base)
    base = base_match.group(0) if base_match else "#1a1414"
    alpha = round(max(0.0, min(1.0, value.opacity)) * 255)
    rofi_bg = base + f"{alpha:02x}"
    override = _rofi_override_text(base, value.opacity)

    operations = [
        lambda value_text: _set_rasi_configuration(value_text, "font", f'"{value.font}"'),
        lambda value_text: _set_or_add_rasi_block(value_text, "window", "transparency", '"real"'),
        lambda value_text: _set_or_add_rasi_block(value_text, "window", "background-color", "@yak-rofi-bg" if HYPR_COLORS_RASI.exists() else rofi_bg),
        lambda value_text: _set_rasi_block(value_text, "window", "width", f"{value.width}px"),
        lambda value_text: _set_rasi_block(value_text, "window", "border-radius", f"{value.radius}px"),
        lambda value_text: _set_rasi_block(value_text, "window", "padding", f"{value.padding}px"),
        lambda value_text: _set_rasi_block(value_text, "listview", "lines", str(value.lines)),
    ]

    for operation in operations:
        text, ok = operation(text)
        if not ok:
            return False, "A required Rofi property could not be located."

    text = _ensure_rofi_override_import(text)
    if HYPR_COLORS_RASI.exists():
        colors = _set_named_rasi_color(colors, "yak-rofi-bg", rofi_bg)

    text = text.replace("var(accent, #e8a29a)", "@yak-accent")
    text = text.replace("var(fg, #e8a29a)", "@yak-fg")

    files = [ROFI_CONFIG]
    if HYPR_COLORS_RASI.exists():
        files.append(HYPR_COLORS_RASI)
    if ROFI_LAUNCHER_OPACITY_OVERRIDE.exists():
        files.append(ROFI_LAUNCHER_OPACITY_OVERRIDE)
    record("Rofi settings", files=files)

    atomic_write(ROFI_CONFIG, text)
    if HYPR_COLORS_RASI.exists():
        atomic_write(HYPR_COLORS_RASI, colors)
    atomic_write(ROFI_LAUNCHER_OPACITY_OVERRIDE, override)

    proc = run(["rofi", "-no-config", "-theme", str(ROFI_CONFIG), "-dump-theme"], timeout=5.0)
    if proc.returncode != 0:
        atomic_write(ROFI_CONFIG, original)
        if HYPR_COLORS_RASI.exists():
            atomic_write(HYPR_COLORS_RASI, colors_original)
        if override_original:
            atomic_write(ROFI_LAUNCHER_OPACITY_OVERRIDE, override_original)
        else:
            try:
                ROFI_LAUNCHER_OPACITY_OVERRIDE.unlink()
            except FileNotFoundError:
                pass
        return False, "Rofi validation failed. Changes were rolled back."

    percent = round(max(0.0, min(1.0, value.opacity)) * 100)
    return True, f"Rofi background opacity set to {percent}% and applied as the final window rule."


# ---------- Waybar ----------

@dataclass
class WaybarState:
    height: int
    margin_top: int
    margin_left: int
    margin_right: int
    spacing: int
    font_size: int
    radius: int
    padding: int
    opacity: float
    left: list[str]
    center: list[str]
    right: list[str]


def _json_number(text: str, key: str, default: int) -> int:
    match = re.search(rf'(?m)^\s*"{re.escape(key)}"\s*:\s*(\d+)\s*,?', text)
    return int(match.group(1)) if match else default


def _module_array(text: str, key: str) -> list[str]:
    match = re.search(rf'"{re.escape(key)}"\s*:\s*\[(.*?)\]', text, flags=re.S)
    return re.findall(r'"([^"]+)"', match.group(1)) if match else []


def _set_module_array(text: str, key: str, values: list[str]) -> tuple[str, bool]:
    match = re.search(
        rf'(?P<indent>^[ \t]*)"{re.escape(key)}"\s*:\s*\[(?P<body>.*?)\]',
        text,
        flags=re.S | re.M,
    )
    if not match:
        return text, False

    indent = match.group("indent")
    inner = indent + "    "
    body = "\n".join(
        f'{inner}"{value}"{"," if index < len(values) - 1 else ""}'
        for index, value in enumerate(values)
    )
    replacement = f'{indent}"{key}": [\n{body}\n{indent}]'
    return text[:match.start()] + replacement + text[match.end():], True


def _set_json_number(text: str, key: str, value: int) -> tuple[str, bool]:
    pattern = rf'(?m)^(\s*"{re.escape(key)}"\s*:\s*)\d+(\s*,?)'
    updated, count = re.subn(pattern, rf'\g<1>{value}\g<2>', text, count=1)
    return updated, count == 1


def waybar_load() -> WaybarState:
    config = WAYBAR_CONFIG.read_text() if WAYBAR_CONFIG.exists() else ""
    style = WAYBAR_STYLE.read_text() if WAYBAR_STYLE.exists() else ""

    font = re.search(r'\bfont-size\s*:\s*(\d+)px\s*;', style)
    radius = re.search(
        r'#custom-launcher,.*?\{.*?\bborder-radius\s*:\s*(\d+)px\s*;',
        style,
        flags=re.S,
    )
    padding = re.search(
        r'#custom-launcher,.*?\{.*?\bpadding\s*:\s*(\d+)px\s+(\d+)px\s*;',
        style,
        flags=re.S,
    )
    opacity = re.search(
        r'#custom-launcher,.*?\{.*?\bbackground-color\s*:\s*alpha\(\s*@(?:bg|surface)\s*,\s*([0-9.]+)\s*\)',
        style,
        flags=re.S,
    )

    return WaybarState(
        height=_json_number(config, "height", 34),
        margin_top=_json_number(config, "margin-top", 6),
        margin_left=_json_number(config, "margin-left", 10),
        margin_right=_json_number(config, "margin-right", 10),
        spacing=_json_number(config, "spacing", 2),
        font_size=int(font.group(1)) if font else 13,
        radius=int(radius.group(1)) if radius else 10,
        padding=int(padding.group(2)) if padding else 10,
        opacity=float(opacity.group(1)) if opacity else 1.0,
        left=_module_array(config, "modules-left"),
        center=_module_array(config, "modules-center"),
        right=_module_array(config, "modules-right"),
    )


def waybar_save(value: WaybarState) -> tuple[bool, str]:
    if not WAYBAR_CONFIG.exists() or not WAYBAR_STYLE.exists():
        return False, "Waybar config or style file was not found."

    config_original = WAYBAR_CONFIG.read_text()
    style_original = WAYBAR_STYLE.read_text()

    config = config_original
    for key, number in [
        ("height", value.height),
        ("margin-top", value.margin_top),
        ("margin-left", value.margin_left),
        ("margin-right", value.margin_right),
        ("spacing", value.spacing),
    ]:
        config, ok = _set_json_number(config, key, number)
        if not ok:
            return False, f'Waybar property "{key}" was not found.'

    for key, values in [
        ("modules-left", value.left),
        ("modules-center", value.center),
        ("modules-right", value.right),
    ]:
        config, ok = _set_module_array(config, key, values)
        if not ok:
            return False, f'Waybar module group "{key}" was not found.'

    style, count = re.subn(
        r'(\bfont-size\s*:\s*)\d+px\s*;',
        rf'\g<1>{value.font_size}px;',
        style_original,
        count=1,
    )
    if count != 1:
        return False, "Waybar font-size rule was not found."

    style, count = re.subn(
        r'(#custom-launcher,.*?\{.*?\bborder-radius\s*:\s*)\d+px\s*;',
        rf'\g<1>{value.radius}px;',
        style,
        count=1,
        flags=re.S,
    )
    if count != 1:
        return False, "Waybar module radius rule was not found."

    style, count = re.subn(
        r'(#custom-launcher,.*?\{.*?\bpadding\s*:\s*)\d+px\s+\d+px\s*;',
        rf'\g<1>2px {value.padding}px;',
        style,
        count=1,
        flags=re.S,
    )
    if count != 1:
        return False, "Waybar module padding rule was not found."

    style, count = re.subn(
        r'(#custom-launcher,.*?\{.*?\bbackground-color\s*:\s*)(?:@(?:bg|surface)|alpha\(\s*@(?:bg|surface)\s*,\s*[0-9.]+\s*\))\s*;',
        rf'\g<1>alpha(@surface, {value.opacity:.2f});',
        style,
        count=1,
        flags=re.S,
    )
    if count != 1:
        return False, "Waybar module background rule was not found."

    record(
        "Waybar settings",
        files=[WAYBAR_CONFIG, WAYBAR_STYLE],
    )
    atomic_write(WAYBAR_CONFIG, config)
    atomic_write(WAYBAR_STYLE, style)

    run(["pkill", "-x", "waybar"], timeout=2.0)
    run(["sh", "-lc", "nohup waybar >/tmp/yakushi-waybar.log 2>&1 &"], timeout=2.0)
    return True, "Waybar configuration updated."
