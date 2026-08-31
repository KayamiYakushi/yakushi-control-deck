from __future__ import annotations

import re
from dataclasses import dataclass

from .io import atomic_write, restore, run
from .history import record
from .paths import HYPR_COLORS_RASI, KITTY_CONFIG, ROFI_CONFIG, WAYBAR_CONFIG, WAYBAR_STYLE


# ---------- Kitty ----------

@dataclass
class KittyState:
    font_size: float
    opacity: float
    padding: int


def _kitty_value(text: str, key: str, default: str) -> str:
    match = re.search(rf'(?m)^\s*{re.escape(key)}\s+(.+?)\s*$', text)
    return match.group(1).strip() if match else default


def kitty_load() -> KittyState:
    text = KITTY_CONFIG.read_text() if KITTY_CONFIG.exists() else ""

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


def kitty_save(value: KittyState) -> tuple[bool, str]:
    text = KITTY_CONFIG.read_text() if KITTY_CONFIG.exists() else ""
    text = _kitty_set(text, "font_size", f"{value.font_size:.1f}")
    text = _kitty_set(text, "background_opacity", f"{value.opacity:.2f}")
    text = _kitty_set(text, "window_padding_width", str(value.padding))
    text = _kitty_set(text, "dynamic_background_opacity", "yes")

    record("Kitty settings", files=[KITTY_CONFIG])
    atomic_write(KITTY_CONFIG, text)
    return True, "Kitty configuration updated."


# ---------- Rofi ----------

@dataclass
class RofiState:
    font: str
    width: int
    radius: int
    padding: int
    lines: int
    opacity: float


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


def rofi_load() -> RofiState:
    text = ROFI_CONFIG.read_text() if ROFI_CONFIG.exists() else ""
    colors = HYPR_COLORS_RASI.read_text() if HYPR_COLORS_RASI.exists() else ""

    font = _configuration_prop(text, "font", '"JetBrainsMono Nerd Font 12"').strip('"')

    lines_raw = _rasi_prop(text, "listview", "lines", "7")
    try:
        lines = int(lines_raw)
    except ValueError:
        lines = 7

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
    text = original
    colors = colors_original

    # Theme Studio owns the RGB portion. Rofi Studio owns only the alpha.
    # Keeping those concerns separate means changing a tonal preset does not
    # silently reset Rofi transparency, and changing opacity does not destroy
    # the selected palette.
    base = _named_rasi_color(colors, "yak-bg") or _named_rasi_color(colors, "bg") or "#1a1414"
    base_match = re.search(r'#[0-9a-fA-F]{6}', base)
    base = base_match.group(0) if base_match else "#1a1414"
    alpha = round(max(0.0, min(1.0, value.opacity)) * 255)
    rofi_bg = base + f"{alpha:02x}"

    operations = [
        lambda t: _set_rasi_configuration(t, "font", f'"{value.font}"'),
        lambda t: _set_or_add_rasi_block(t, "window", "transparency", '"real"'),
        lambda t: _set_or_add_rasi_block(t, "window", "background-color", "@yak-rofi-bg" if HYPR_COLORS_RASI.exists() else rofi_bg),
        lambda t: _set_rasi_block(t, "window", "width", f"{value.width}px"),
        lambda t: _set_rasi_block(t, "window", "border-radius", f"{value.radius}px"),
        lambda t: _set_rasi_block(t, "window", "padding", f"{value.padding}px"),
        lambda t: _set_rasi_block(t, "listview", "lines", str(value.lines)),
    ]

    for operation in operations:
        text, ok = operation(text)
        if not ok:
            return False, "A required Rofi property could not be located."

    if HYPR_COLORS_RASI.exists():
        colors = _set_named_rasi_color(colors, "yak-rofi-bg", rofi_bg)

    text = text.replace("var(accent, #e8a29a)", "@yak-accent")
    text = text.replace("var(fg, #e8a29a)", "@yak-fg")

    files = [ROFI_CONFIG]
    if HYPR_COLORS_RASI.exists():
        files.append(HYPR_COLORS_RASI)
    record("Rofi settings", files=files)

    atomic_write(ROFI_CONFIG, text)
    if HYPR_COLORS_RASI.exists():
        atomic_write(HYPR_COLORS_RASI, colors)

    proc = run(
        ["rofi", "-no-config", "-theme", str(ROFI_CONFIG), "-dump-theme"],
        timeout=5.0,
    )
    if proc.returncode != 0:
        atomic_write(ROFI_CONFIG, original)
        if HYPR_COLORS_RASI.exists():
            atomic_write(HYPR_COLORS_RASI, colors_original)
        return False, "Rofi validation failed. Changes were rolled back."

    percent = round(max(0.0, min(1.0, value.opacity)) * 100)
    return True, f"Rofi background opacity set to {percent}% using real compositor transparency."


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
