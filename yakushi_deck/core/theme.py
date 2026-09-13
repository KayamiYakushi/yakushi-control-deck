from __future__ import annotations

import re
from dataclasses import dataclass

from .history import record
from .apps import kitty_colors_load, kitty_sync_theme
from .io import atomic_write, run
from .paths import (
    HYPR_COLORS_CSS,
    HYPR_COLORS_RASI,
    KITTY_CONFIG,
    ROFI_CONFIG,
    ROFI_LAUNCHER_OPACITY_OVERRIDE,
    ROFI_OPACITY_OVERRIDE,
    WAYBAR_STYLE,
    WINDOW_FRAME_STATE,
)


# The original user palette is intentionally retained as the default.  The
# important change in Preview 8 is that a palette is no longer only five
# colors: surfaces, muted text, hover, and selected text now get their own
# tonal roles.
DEFAULTS = {
    "accent": "#e8a29a",
    "bg": "#0e0c0d",
    "surface": "#1a1414",
    "surface_alt": "#231919",
    "fg": "#e8a29a",
    "muted": "#8e7370",
    "border": "#3f292a",
    "hover_bg": "#362324",
    "selected_fg": "#1a1414",
}

LEGACY_RASI_NAMES = {
    "accent": "accent",
    "bg": "bg",
    "fg": "fg",
    "border": "border",
    "hover_bg": "hover-bg",
}

YAK_RASI_NAMES = {
    "accent": "yak-accent",
    "bg": "yak-bg",
    "surface": "yak-surface",
    "surface_alt": "yak-surface-alt",
    "fg": "yak-fg",
    "muted": "yak-muted",
    "border": "yak-border",
    "hover_bg": "yak-hover",
    "selected_fg": "yak-selected-fg",
}


@dataclass
class Palette:
    accent: str
    bg: str
    surface: str
    surface_alt: str
    fg: str
    muted: str
    border: str
    hover_bg: str
    selected_fg: str


def _normalize(value: str, default: str) -> str:
    value = (value or "").strip()
    match = re.search(r'#[0-9a-fA-F]{6}', value)
    return match.group(0).lower() if match else default


def _css_value(text: str, key: str) -> str | None:
    match = re.search(
        rf'(?m)^\s*@define-color\s+{re.escape(key)}\s+([^;]+);',
        text,
    )
    return _normalize(match.group(1), DEFAULTS[key]) if match else None


def _rasi_named_value(text: str, name: str, default: str) -> str | None:
    match = re.search(
        rf'(?m)^\s*{re.escape(name)}\s*:\s*(#[0-9a-fA-F]{{6,8}})\s*;',
        text,
    )
    return _normalize(match.group(1), default) if match else None


def load() -> Palette:
    css = HYPR_COLORS_CSS.read_text() if HYPR_COLORS_CSS.exists() else ""
    rasi = HYPR_COLORS_RASI.read_text() if HYPR_COLORS_RASI.exists() else ""

    values = {}
    for key, default in DEFAULTS.items():
        rasi_name = YAK_RASI_NAMES[key]
        value = _css_value(css, key) or _rasi_named_value(rasi, rasi_name, default)

        # Allow older five-color files to seed the new tonal model.
        if value is None and key in LEGACY_RASI_NAMES:
            value = _rasi_named_value(rasi, LEGACY_RASI_NAMES[key], default)
        values[key] = value or default

    # A pre-Preview-8 colors.css has no surface roles.  Use the existing bg as
    # the primary surface so applying the first Preview-8 preset does not cause
    # a surprising flash before the user chooses a new theme.
    if _css_value(css, "surface") is None and _rasi_named_value(rasi, "yak-surface", DEFAULTS["surface"]) is None:
        old_bg = _css_value(css, "bg") or _rasi_named_value(rasi, "bg", DEFAULTS["surface"])
        if old_bg:
            values["surface"] = old_bg

    return Palette(**values)


def _set_css(text: str, key: str, value: str) -> str:
    pattern = rf'(?m)^(\s*@define-color\s+{re.escape(key)}\s+)[^;]+;'
    if re.search(pattern, text):
        return re.sub(pattern, rf'\g<1>{value};', text, count=1)

    if text and not text.endswith("\n"):
        text += "\n"
    return text + f"@define-color {key} {value};\n"


def _set_rasi_name(text: str, name: str, value: str) -> str:
    pattern = rf'(?m)^(\s*{re.escape(name)}\s*:\s*)#[0-9a-fA-F]{{6,8}}\s*;'
    if re.search(pattern, text):
        return re.sub(pattern, rf'\g<1>{value};', text, count=1)

    # Prefer adding to the first global * block when one exists.
    block = re.search(r'(?ms)^\s*\*\s*\{.*?^\s*\}', text)
    if block:
        closing = block.end() - 1
        return text[:closing] + f"    {name}: {value};\n" + text[closing:]

    if text and not text.endswith("\n"):
        text += "\n"
    return text + f"\n* {{\n    {name}: {value};\n}}\n"


def _set_block_prop(text: str, block: str, prop: str, value: str) -> tuple[str, bool]:
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


def _rofi_alpha_suffix(rasi_text: str, rofi_text: str) -> str:
    match = re.search(
        r'(?m)^\s*yak-rofi-bg\s*:\s*#[0-9a-fA-F]{6}([0-9a-fA-F]{2})\s*;',
        rasi_text,
    )
    if match:
        return match.group(1).lower()

    match = re.search(
        r'(?ms)^\s*window\s*\{.*?^\s*background-color\s*:\s*#[0-9a-fA-F]{6}([0-9a-fA-F]{2})\s*;',
        rofi_text,
    )
    if match:
        return match.group(1).lower()

    return "ff"


def _set_or_add_block_prop(text: str, block: str, prop: str, value: str) -> tuple[str, bool]:
    updated, ok = _set_block_prop(text, block, prop, value)
    if ok:
        return updated, True

    block_match = re.search(
        rf'(?ms)^\s*{re.escape(block)}\s*\{{.*?^\s*\}}',
        text,
    )
    if not block_match:
        return text, False

    closing = block_match.end() - 1
    return text[:closing] + f"    {prop}: {value};\n" + text[closing:], True


def _override_alpha_fraction(text: str) -> float | None:
    match = re.search(
        r'background-color\s*:\s*rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*([0-9.]+)%?\s*\)',
        text or "",
        flags=re.I,
    )
    if not match:
        return None
    raw = float(match.group(1))
    return max(0.0, min(1.0, raw / 100.0 if raw > 1.0 else raw))


def _rgba_rasi(value: str, opacity: float, default: str) -> str:
    match = re.search(r"#([0-9a-fA-F]{6})", value or "")
    raw = match.group(1) if match else default.lstrip("#")
    r, g, b = (int(raw[index:index + 2], 16) for index in (0, 2, 4))
    percent = round(max(0.0, min(1.0, opacity)) * 100)
    return f"rgba({r}, {g}, {b}, {percent}%)"


def _rofi_concrete_override(
    bg: str,
    opacity: float,
    surface: str | None = None,
    surface_alt: str | None = None,
    hover: str | None = None,
    premium: bool = False,
) -> str:
    # Theme Studio owns RGB values and Rofi Studio owns the master alpha.
    # Premium glass keeps subordinate surfaces lighter so stacking them does
    # not hide the compositor blur; text and icons remain fully opaque.
    surface = surface or bg
    surface_alt = surface_alt or surface
    hover = hover or surface_alt

    surface_opacity = opacity * 0.28 if premium else opacity
    surface_alt_opacity = opacity * 0.42 if premium else opacity
    hover_opacity = opacity * 0.55 if premium else opacity
    window_rgba = _rgba_rasi(bg, opacity, DEFAULTS["bg"])
    surface_rgba = _rgba_rasi(surface, surface_opacity, DEFAULTS["surface"])
    surface_alt_rgba = _rgba_rasi(surface_alt, surface_alt_opacity, DEFAULTS["surface_alt"])
    hover_rgba = _rgba_rasi(hover, hover_opacity, DEFAULTS["hover_bg"])
    close_background = "transparent" if premium else surface_alt_rgba

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
        f"    background-color: {close_background};\n"
        "}\n"
        "button-open {\n"
        f"    background-color: {hover_rgba};\n"
        "}\n"
    )

def _ensure_override_import(text: str) -> str:
    line = '@import "yakushi-launcher-opacity.rasi"'
    text = re.sub(
        r'(?m)^\s*@import\s+["\']yakushi-(?:launcher-)?opacity\.rasi["\']\s*;?\s*$',
        '',
        text,
    ).rstrip()
    return text + '\n\n' + line + '\n'


def _patch_rofi(text: str) -> str:
    # Rofi geometry is controlled by Rofi Studio, while every visible color
    # role remains linked to the current Yakushi Theme Studio palette.
    operations = [
        ("*", "bg", "@yak-bg"),
        ("*", "border-col", "@yak-border"),
        ("*", "selected-bg", "@yak-hover"),
        ("*", "selected-fg", "@yak-selected-fg"),
        ("*", "text-col", "@yak-fg"),
        ("*", "text-alt", "@yak-muted"),
        ("window", "background-color", "@yak-rofi-bg"),
        ("window", "border-color", "@yak-border"),
        ("inputbar", "background-color", "@yak-surface-alt"),
        ("inputbar", "border-color", "@yak-border"),
        ("entry", "text-color", "@yak-fg"),
        ("entry", "placeholder-color", "@yak-muted"),
        ("listview", "background-color", "@yak-surface"),
        ("element", "background-color", "transparent"),
        ("element", "text-color", "@yak-fg"),
        ("element", "border-color", "#00000000"),
        ("element selected", "background-color", "@yak-hover"),
        ("element selected", "text-color", "@yak-fg"),
        ("element selected", "border-color", "#00000000"),
    ]
    for block, prop, value in operations:
        text, _ = _set_block_prop(text, block, prop, value)

    text, _ = _set_or_add_block_prop(text, "window", "transparency", '"real"')
    text = text.replace("var(accent, #e8a29a)", "@yak-accent")
    text = text.replace("var(fg, #e8a29a)", "@yak-fg")
    text = text.replace("@hover_bg", "@yak-hover")
    return text

def _patch_waybar(text: str) -> str:
    # Module surfaces now use @surface, allowing a dusty salmon theme, a mint
    # theme, and a violet theme to have genuinely different depth rather than
    # merely a different selected-workspace color.
    text = re.sub(
        r'(\bbackground-color\s*:\s*)(?:@bg|@surface|alpha\(\s*@(bg|surface)\s*,\s*([0-9.]+)\s*\))\s*;',
        lambda m: f"{m.group(1)}alpha(@surface, {m.group(3) or '1.00'});",
        text,
        count=1,
        flags=re.S,
    )

    # The supplied Waybar uses a hard-coded dark selected foreground.  Replace
    # that with a role so light pastel themes remain readable too.
    text = text.replace("color: #1a1414;", "color: @selected_fg;")
    return text


def repair_rasi_compatibility() -> tuple[bool, str]:
    """Repair syntax produced by earlier Yakushi previews."""
    changed_files = []
    updates = {}

    if HYPR_COLORS_RASI.exists():
        original = HYPR_COLORS_RASI.read_text()
        repaired = re.sub(r'(?m)^(\s*)hover_bg(\s*:)', r'\1hover-bg\2', original)
        repaired = repaired.replace("@hover_bg", "@hover-bg")
        if repaired != original:
            changed_files.append(HYPR_COLORS_RASI)
            updates[HYPR_COLORS_RASI] = repaired

    if ROFI_CONFIG.exists():
        original = ROFI_CONFIG.read_text()
        repaired = original.replace("var(accent, #e8a29a)", "@accent")
        repaired = repaired.replace("var(fg, #e8a29a)", "@fg")
        repaired = repaired.replace("@hover_bg", "@hover-bg")
        if repaired != original:
            changed_files.append(ROFI_CONFIG)
            updates[ROFI_CONFIG] = repaired

    if not changed_files:
        return True, "Rofi compatibility is already clean."

    record("Rofi compatibility repair", files=changed_files)
    for path, content in updates.items():
        atomic_write(path, content)

    if ROFI_CONFIG.exists():
        proc = run(["rofi", "-no-config", "-theme", str(ROFI_CONFIG), "-dump-theme"], timeout=5.0)
        if proc.returncode != 0:
            return False, (proc.stderr or proc.stdout).strip()

    return True, "Rofi compatibility repaired."


def save(palette: Palette) -> tuple[bool, str]:
    values = {
        key: _normalize(getattr(palette, key), default)
        for key, default in DEFAULTS.items()
    }

    css_original = HYPR_COLORS_CSS.read_text() if HYPR_COLORS_CSS.exists() else ""
    rasi_original = HYPR_COLORS_RASI.read_text() if HYPR_COLORS_RASI.exists() else ""
    rofi_original = ROFI_CONFIG.read_text() if ROFI_CONFIG.exists() else ""
    rofi_override_original = (
        ROFI_LAUNCHER_OPACITY_OVERRIDE.read_text()
        if ROFI_LAUNCHER_OPACITY_OVERRIDE.exists()
        else ""
    )
    legacy_rofi_override = (
        ROFI_OPACITY_OVERRIDE.read_text()
        if ROFI_OPACITY_OVERRIDE.exists()
        else ""
    )
    waybar_original = WAYBAR_STYLE.read_text() if WAYBAR_STYLE.exists() else ""

    css = css_original
    # Keep the five legacy names so the user's existing Waybar continues to
    # work, then add the richer tonal roles.
    css_aliases = {
        "accent": values["accent"],
        "bg": values["bg"],
        "fg": values["fg"],
        "border": values["border"],
        "hover_bg": values["hover_bg"],
        "surface": values["surface"],
        "surface_alt": values["surface_alt"],
        "muted": values["muted"],
        "selected_fg": values["selected_fg"],
    }
    for key, value in css_aliases.items():
        css = _set_css(css, key, value)

    rasi = rasi_original
    override_opacity = _override_alpha_fraction(
        rofi_override_original or legacy_rofi_override
    )
    rofi_alpha = _rofi_alpha_suffix(rasi_original, rofi_original)
    rofi_opacity = override_opacity if override_opacity is not None else int(rofi_alpha, 16) / 255
    # New, unambiguous variable names used by config.rasi.
    for key, value in values.items():
        rasi = _set_rasi_name(rasi, YAK_RASI_NAMES[key], value)
    # The palette controls the RGB; Rofi Studio controls this alpha suffix.
    rasi = _set_rasi_name(rasi, "yak-rofi-bg", values["bg"] + rofi_alpha)
    # Legacy aliases remain available to any other Rofi snippets.
    for key, legacy_name in LEGACY_RASI_NAMES.items():
        rasi = _set_rasi_name(rasi, legacy_name, values[key])

    rofi = _patch_rofi(rofi_original) if rofi_original else rofi_original
    if rofi:
        rofi = _ensure_override_import(rofi)
    premium_rofi = "/* YAKUSHI ROFI THEME: raycast_glass */" in rofi_original
    rofi_override = _rofi_concrete_override(
        values["bg"],
        rofi_opacity,
        values["surface"],
        values["surface_alt"],
        values["hover_bg"],
        premium=premium_rofi,
    )
    waybar = _patch_waybar(waybar_original) if waybar_original else waybar_original

    kitty_follows_theme = KITTY_CONFIG.exists() and kitty_colors_load().mode == "follow"

    files = [HYPR_COLORS_CSS, HYPR_COLORS_RASI]
    if kitty_follows_theme:
        files.append(KITTY_CONFIG)
    if ROFI_CONFIG.exists():
        files.append(ROFI_CONFIG)
    if ROFI_LAUNCHER_OPACITY_OVERRIDE.exists():
        files.append(ROFI_LAUNCHER_OPACITY_OVERRIDE)
    if WAYBAR_STYLE.exists():
        files.append(WAYBAR_STYLE)
    record("Desktop tonal palette", files=files)

    atomic_write(HYPR_COLORS_CSS, css)
    atomic_write(HYPR_COLORS_RASI, rasi)
    if ROFI_CONFIG.exists():
        atomic_write(ROFI_CONFIG, rofi)
        atomic_write(ROFI_LAUNCHER_OPACITY_OVERRIDE, rofi_override)
    if WAYBAR_STYLE.exists():
        atomic_write(WAYBAR_STYLE, waybar)

    # Rofi syntax is fragile, so validate it and restore the exact pre-change
    # files if the user's local config rejects our references.
    if ROFI_CONFIG.exists():
        proc = run(["rofi", "-no-config", "-theme", str(ROFI_CONFIG), "-dump-theme"], timeout=5.0)
        if proc.returncode != 0:
            atomic_write(HYPR_COLORS_CSS, css_original)
            atomic_write(HYPR_COLORS_RASI, rasi_original)
            atomic_write(ROFI_CONFIG, rofi_original)
            if rofi_override_original:
                atomic_write(
                    ROFI_LAUNCHER_OPACITY_OVERRIDE,
                    rofi_override_original,
                )
            else:
                try:
                    ROFI_LAUNCHER_OPACITY_OVERRIDE.unlink()
                except FileNotFoundError:
                    pass
            if WAYBAR_STYLE.exists():
                atomic_write(WAYBAR_STYLE, waybar_original)
            return False, "Rofi rejected the tonal palette. The previous theme was restored."

    if kitty_follows_theme:
        kitty_sync_theme(values)

    frame_note = ""
    try:
        from .frame import sync_follow as sync_window_frame_follow
        frame_ok, _frame_message = sync_window_frame_follow(values)
        if frame_ok and WINDOW_FRAME_STATE.exists():
            frame_note = " Window borders synchronized."
    except Exception:
        frame_note = ""

    run(["pkill", "-x", "waybar"], timeout=2.0)
    run(["sh", "-lc", "nohup waybar >/tmp/yakushi-waybar.log 2>&1 &"], timeout=2.0)
    kitty_note = " Kitty colors synchronized." if kitty_follows_theme else ""
    return True, f"Tonal desktop palette applied. Foreground {values['fg']} now matches the preset preview.{kitty_note}{frame_note}"
