from __future__ import annotations

import re
from dataclasses import dataclass

from .history import record
from .io import atomic_write, run
from .paths import (
    HYPR_COLORS_CSS,
    HYPR_COLORS_RASI,
    ROFI_CONFIG,
    ROFI_OPACITY_OVERRIDE,
    WAYBAR_STYLE,
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


def _rofi_concrete_override(bg: str, opacity: float) -> str:
    value = bg.lstrip('#')
    if len(value) != 6:
        value = DEFAULTS["bg"].lstrip('#')
    r, g, b = (int(value[index:index + 2], 16) for index in (0, 2, 4))
    percent = round(max(0.0, min(1.0, opacity)) * 100)
    return (
        '/* Generated by Yakushi Control Deck. Keep this import last. */\n'
        'window {\n'
        '    transparency: "real";\n'
        f'    background-color: rgba({r}, {g}, {b}, {percent}%);\n'
        '}\n'
    )


def _ensure_override_import(text: str) -> str:
    line = '@import "yakushi-opacity.rasi"'
    text = re.sub(
        r'(?m)^\s*@import\s+["\']yakushi-opacity\.rasi["\']\s*;?\s*$',
        '',
        text,
    ).rstrip()
    return text + '\n\n' + line + '\n'


def _patch_rofi(text: str) -> str:
    # Give the existing Rofi theme actual tonal roles instead of replacing only
    # its accent.  Every replacement below targets properties already present
    # in the user's config; if a property is absent we leave it untouched.
    operations = [
        ("*", "bg", "@yak-bg"),
        ("*", "border-col", "@yak-border"),
        ("*", "selected-bg", "@yak-accent"),
        ("*", "selected-fg", "@yak-selected-fg"),
        ("*", "text-col", "@yak-fg"),
        ("*", "text-alt", "@yak-muted"),
        ("window", "background-color", "@yak-rofi-bg"),
        ("window", "border-color", "@yak-border"),
        ("inputbar", "background-color", "@yak-surface"),
        ("inputbar", "border-color", "@yak-border"),
        ("entry", "text-color", "@yak-fg"),
        ("entry", "placeholder-color", "@yak-muted"),
    ]
    for block, prop, value in operations:
        text, _ = _set_block_prop(text, block, prop, value)

    # Rofi needs a real ARGB surface for actual compositor transparency.
    text, _ = _set_or_add_block_prop(text, "window", "transparency", '"real"')

    # Earlier previews repaired these fallbacks; retain compatibility for an
    # installation that skipped those migrations.
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
    rofi_override_original = ROFI_OPACITY_OVERRIDE.read_text() if ROFI_OPACITY_OVERRIDE.exists() else ""
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
    override_opacity = _override_alpha_fraction(rofi_override_original)
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
    rofi_override = _rofi_concrete_override(values["bg"], rofi_opacity)
    waybar = _patch_waybar(waybar_original) if waybar_original else waybar_original

    files = [HYPR_COLORS_CSS, HYPR_COLORS_RASI]
    if ROFI_CONFIG.exists():
        files.append(ROFI_CONFIG)
    if ROFI_OPACITY_OVERRIDE.exists():
        files.append(ROFI_OPACITY_OVERRIDE)
    if WAYBAR_STYLE.exists():
        files.append(WAYBAR_STYLE)
    record("Desktop tonal palette", files=files)

    atomic_write(HYPR_COLORS_CSS, css)
    atomic_write(HYPR_COLORS_RASI, rasi)
    if ROFI_CONFIG.exists():
        atomic_write(ROFI_CONFIG, rofi)
        atomic_write(ROFI_OPACITY_OVERRIDE, rofi_override)
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
            if WAYBAR_STYLE.exists():
                atomic_write(WAYBAR_STYLE, waybar_original)
            return False, "Rofi rejected the tonal palette. The previous theme was restored."

    run(["pkill", "-x", "waybar"], timeout=2.0)
    run(["sh", "-lc", "nohup waybar >/tmp/yakushi-waybar.log 2>&1 &"], timeout=2.0)
    return True, f"Tonal desktop palette applied. Foreground {values['fg']} now matches the preset preview."
