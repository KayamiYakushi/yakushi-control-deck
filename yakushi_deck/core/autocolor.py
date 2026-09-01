from __future__ import annotations

import colorsys
from dataclasses import asdict, dataclass
from pathlib import Path

import gi
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf

from .io import load_json, run, save_json
from .paths import AUTO_COLOR_STATE
from .theme import Palette, save as save_palette
from .wallpapers import current as current_wallpaper


@dataclass
class AutoColorSettings:
    enabled: bool = False
    mode: str = "dark"
    last_wallpaper: str = ""


def status() -> dict:
    raw = load_json(AUTO_COLOR_STATE, asdict(AutoColorSettings()))
    mode = str(raw.get("mode", "dark")).lower()
    if mode not in {"dark", "light"}:
        mode = "dark"
    return {
        "enabled": bool(raw.get("enabled", False)),
        "mode": mode,
        "last_wallpaper": str(raw.get("last_wallpaper", "")),
    }


def configure(*, enabled: bool | None = None, mode: str | None = None) -> dict:
    data = status()
    if enabled is not None:
        data["enabled"] = bool(enabled)
    if mode is not None:
        normalized = str(mode).lower()
        if normalized in {"dark", "light"}:
            data["mode"] = normalized
    save_json(AUTO_COLOR_STATE, data)
    return data


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _hex(rgb: tuple[float, float, float]) -> str:
    return "#{:02x}{:02x}{:02x}".format(
        round(_clamp(rgb[0]) * 255),
        round(_clamp(rgb[1]) * 255),
        round(_clamp(rgb[2]) * 255),
    )


def _hls(h: float, l: float, s: float) -> str:
    return _hex(colorsys.hls_to_rgb(h % 1.0, _clamp(l), _clamp(s)))


def _relative_luminance(hex_value: str) -> float:
    value = hex_value.lstrip("#")
    channels = [int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)]

    def linear(channel: float) -> float:
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4

    r, g, b = (linear(channel) for channel in channels)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a: str, b: str) -> float:
    la, lb = _relative_luminance(a), _relative_luminance(b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def _ensure_text_contrast(color: str, background: str, hue: float, saturation: float, *, dark_mode: bool, target: float = 4.5) -> str:
    if _contrast(color, background) >= target:
        return color
    if dark_mode:
        for lightness in (0.74, 0.78, 0.82, 0.86, 0.90, 0.94):
            candidate = _hls(hue, lightness, min(saturation, 0.42))
            if _contrast(candidate, background) >= target:
                return candidate
        return "#f2eeee"
    for lightness in (0.24, 0.20, 0.16, 0.12, 0.08):
        candidate = _hls(hue, lightness, min(saturation, 0.34))
        if _contrast(candidate, background) >= target:
            return candidate
    return "#171515"


def _sample_wallpaper(path: Path) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Return (accent_rgb, average_rgb) as normalized RGB tuples.

    The image is intentionally reduced before sampling.  Accent choice is based
    on a hue histogram weighted by saturation, mid-tone readability and pixel
    frequency, so a tiny neon pixel cannot hijack the whole desktop palette.
    """
    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path), 96, 96, True)
    width, height = pixbuf.get_width(), pixbuf.get_height()
    channels = pixbuf.get_n_channels()
    stride = pixbuf.get_rowstride()
    pixels = bytes(pixbuf.get_pixels())
    has_alpha = pixbuf.get_has_alpha()

    hue_bins = [
        {"weight": 0.0, "r": 0.0, "g": 0.0, "b": 0.0}
        for _ in range(24)
    ]
    total_r = total_g = total_b = total_weight = 0.0
    neutral_r = neutral_g = neutral_b = neutral_weight = 0.0

    step = 1 if width * height <= 5000 else 2
    for y in range(0, height, step):
        row = y * stride
        for x in range(0, width, step):
            offset = row + x * channels
            if offset + 2 >= len(pixels):
                continue
            r = pixels[offset] / 255.0
            g = pixels[offset + 1] / 255.0
            b = pixels[offset + 2] / 255.0
            if has_alpha and channels >= 4 and pixels[offset + 3] < 96:
                continue

            h, l, s = colorsys.rgb_to_hls(r, g, b)
            # Global average: de-emphasize pure black/white so borders in an
            # image do not dominate the family tint.
            avg_weight = 0.45 + 0.55 * (1.0 - min(1.0, abs(l - 0.5) * 1.7))
            total_r += r * avg_weight
            total_g += g * avg_weight
            total_b += b * avg_weight
            total_weight += avg_weight

            if s < 0.07:
                neutral_r += r
                neutral_g += g
                neutral_b += b
                neutral_weight += 1.0
                continue

            midtone = 1.0 - min(1.0, abs(l - 0.53) * 1.7)
            saturation_weight = 0.25 + s ** 1.35 * 2.2
            weight = saturation_weight * (0.35 + 0.65 * midtone)
            index = min(23, int(h * 24.0))
            bucket = hue_bins[index]
            bucket["weight"] += weight
            bucket["r"] += r * weight
            bucket["g"] += g * weight
            bucket["b"] += b * weight

    if total_weight <= 0:
        raise ValueError("Wallpaper did not contain readable pixels.")

    average = (total_r / total_weight, total_g / total_weight, total_b / total_weight)
    best = max(hue_bins, key=lambda item: item["weight"])
    if best["weight"] > 0.5:
        accent = (
            best["r"] / best["weight"],
            best["g"] / best["weight"],
            best["b"] / best["weight"],
        )
    elif neutral_weight:
        accent = (
            neutral_r / neutral_weight,
            neutral_g / neutral_weight,
            neutral_b / neutral_weight,
        )
    else:
        accent = average

    # Blend a little of the wallpaper's global family into the accent so the
    # result tracks the whole image instead of an isolated object.
    accent = tuple(_clamp(accent[i] * 0.82 + average[i] * 0.18) for i in range(3))
    return accent, average


def generate(path: Path, mode: str = "dark") -> Palette:
    path = Path(path).expanduser()
    if not path.exists() or not path.is_file():
        raise ValueError("Current wallpaper could not be found.")

    normalized_mode = str(mode).lower()
    if normalized_mode not in {"dark", "light"}:
        normalized_mode = "dark"

    accent_rgb, average_rgb = _sample_wallpaper(path)
    accent_h, accent_l, accent_s = colorsys.rgb_to_hls(*accent_rgb)
    base_h, _base_l, base_s = colorsys.rgb_to_hls(*average_rgb)
    if base_s < 0.05:
        base_h = accent_h

    # Keep low-saturation wallpapers tasteful instead of inventing neon.
    chroma = _clamp(accent_s * 0.90 + 0.10, 0.22, 0.72)
    base_chroma = _clamp(base_s * 0.35 + 0.035, 0.035, 0.18)

    if normalized_mode == "dark":
        bg = _hls(base_h, 0.050, base_chroma)
        surface = _hls(base_h, 0.088, min(0.20, base_chroma + 0.025))
        surface_alt = _hls(base_h, 0.125, min(0.24, base_chroma + 0.045))
        accent = _hls(accent_h, _clamp(0.62 + (0.50 - accent_l) * 0.10, 0.55, 0.68), chroma)
        fg = _hls(accent_h, 0.76, min(0.44, chroma * 0.70))
        fg = _ensure_text_contrast(fg, bg, accent_h, chroma, dark_mode=True)
        muted = _hls(accent_h, 0.52, min(0.25, chroma * 0.38))
        border = _hls(accent_h, 0.235, min(0.32, chroma * 0.48))
        hover = _hls(accent_h, 0.170, min(0.31, chroma * 0.46))
        selected_fg = _ensure_text_contrast(bg, accent, base_h, base_chroma, dark_mode=False)
    else:
        bg = _hls(base_h, 0.958, min(0.14, base_chroma + 0.02))
        surface = _hls(base_h, 0.910, min(0.17, base_chroma + 0.035))
        surface_alt = _hls(base_h, 0.850, min(0.20, base_chroma + 0.055))
        accent = _hls(accent_h, _clamp(0.43 + (0.50 - accent_l) * 0.05, 0.38, 0.48), chroma)
        fg = _hls(base_h, 0.180, min(0.28, base_chroma + 0.08))
        fg = _ensure_text_contrast(fg, bg, base_h, base_chroma + 0.08, dark_mode=False)
        muted = _hls(base_h, 0.425, min(0.24, base_chroma + 0.06))
        border = _hls(accent_h, 0.735, min(0.25, chroma * 0.36))
        hover = _hls(accent_h, 0.825, min(0.24, chroma * 0.34))
        selected_fg = _ensure_text_contrast("#f8f6f4", accent, base_h, 0.04, dark_mode=True)

    return Palette(
        accent=accent,
        bg=bg,
        surface=surface,
        surface_alt=surface_alt,
        fg=fg,
        muted=muted,
        border=border,
        hover_bg=hover,
        selected_fg=selected_fg,
    )


def _set_gnome_color_scheme(mode: str) -> None:
    # Nautilus/libadwaita respects this setting.  Failure is harmless on a
    # minimal non-GNOME session or when the schema is absent.
    scheme = "prefer-dark" if mode == "dark" else "prefer-light"
    run(["gsettings", "set", "org.gnome.desktop.interface", "color-scheme", scheme], timeout=2.5)


def apply(path: Path | None = None, mode: str | None = None, *, enable_follow: bool | None = None) -> tuple[bool, str, Palette | None]:
    data = status()
    normalized_mode = (mode or data["mode"]).lower()
    if normalized_mode not in {"dark", "light"}:
        normalized_mode = "dark"

    wallpaper = Path(path).expanduser() if path else current_wallpaper()
    if wallpaper is None or not wallpaper.exists():
        return False, "No current wallpaper is known. Apply a wallpaper from Yakushi first.", None

    try:
        palette = generate(wallpaper, normalized_mode)
    except Exception as exc:
        return False, f"Auto Color could not analyze the wallpaper: {exc}", None

    ok, message = save_palette(palette)
    if not ok:
        return False, message, None

    if enable_follow is not None:
        data["enabled"] = bool(enable_follow)
    data["mode"] = normalized_mode
    data["last_wallpaper"] = str(wallpaper)
    save_json(AUTO_COLOR_STATE, data)
    _set_gnome_color_scheme(normalized_mode)

    lock_note = ""
    try:
        from .lockscreen import refresh_lock_palette
        lock_ok, lock_message = refresh_lock_palette()
        if lock_ok and "synchronized" in lock_message.lower():
            lock_note = " Hyprlock colors synchronized."
    except Exception:
        # Auto Color must never fail only because a lock-screen integration is
        # missing or has not been configured yet.
        pass

    return True, f"Auto Color {normalized_mode.upper()} generated from {wallpaper.name}. {message}{lock_note}", palette


def apply_follow_if_enabled(path: Path) -> tuple[bool, str]:
    data = status()
    if not data["enabled"]:
        return True, ""
    ok, message, _palette = apply(path, data["mode"])
    return ok, message
