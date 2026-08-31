from __future__ import annotations

import json
import re
import time
from pathlib import Path

from .io import load_json, run, save_json
from .history import record
from .paths import STATE


DEFAULTS = {
    "appearance": {
        "gaps_in": 4,
        "gaps_out": 8,
        "rounding": 12,
        "border_size": 2,
        "blur_enabled": True,
        "blur_size": 8,
        "blur_passes": 3,
        "active_opacity": 1.0,
        "inactive_opacity": 0.96,
    },
    "keyboard": {
        "layout": "tr",
        "repeat_rate": 25,
        "repeat_delay": 600,
    },
    "mouse": {
        "sensitivity": 0.0,
        "accel_profile": "adaptive",
        "left_handed": False,
        "natural_scroll": False,
    },
}


def state() -> dict:
    data = load_json(STATE, DEFAULTS)
    for key, value in DEFAULTS.items():
        if key not in data or not isinstance(data[key], dict):
            data[key] = value.copy()
        else:
            merged = value.copy()
            merged.update(data[key])
            data[key] = merged
    return data


def save_state(data: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    save_json(STATE, data)


def keyword(key: str, value: str) -> tuple[bool, str]:
    proc = run(["hyprctl", "keyword", key, value], timeout=4.0)
    return proc.returncode == 0, (proc.stderr or proc.stdout).strip()


def json_command(command: str):
    proc = run(["hyprctl", "-j", command], timeout=4.0)
    if proc.returncode != 0:
        return []
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return []


def apply_appearance(values: dict) -> tuple[bool, str]:
    previous = state()["appearance"].copy()
    record(
        "Desktop appearance",
        runtime={"kind": "appearance", "values": previous},
    )

    mapping = [
        ("general:gaps_in", values["gaps_in"]),
        ("general:gaps_out", values["gaps_out"]),
        ("general:border_size", values["border_size"]),
        ("decoration:rounding", values["rounding"]),
        ("decoration:blur:enabled", "true" if values["blur_enabled"] else "false"),
        ("decoration:blur:size", values["blur_size"]),
        ("decoration:blur:passes", values["blur_passes"]),
        ("decoration:active_opacity", values["active_opacity"]),
        ("decoration:inactive_opacity", values["inactive_opacity"]),
    ]

    failures = []
    for key, value in mapping:
        ok, message = keyword(key, str(value))
        if not ok:
            failures.append(f"{key}: {message}")

    data = state()
    data["appearance"] = values
    save_state(data)

    if failures:
        return False, "\n".join(failures)
    return True, "Desktop appearance applied."


def apply_keyboard(values: dict) -> tuple[bool, str]:
    previous = state()["keyboard"].copy()
    record(
        "Keyboard settings",
        runtime={"kind": "keyboard", "values": previous},
    )

    mapping = [
        ("input:kb_layout", values["layout"]),
        ("input:repeat_rate", values["repeat_rate"]),
        ("input:repeat_delay", values["repeat_delay"]),
    ]

    failures = []
    for key, value in mapping:
        ok, message = keyword(key, str(value))
        if not ok:
            failures.append(f"{key}: {message}")

    data = state()
    data["keyboard"] = values
    save_state(data)

    if failures:
        return False, "\n".join(failures)
    return True, "Keyboard settings applied."


def _lua_string(value: str) -> str:
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"') + '"'


def _lua_bool(value: bool) -> str:
    return "true" if bool(value) else "false"


def _eval_lua(expression: str) -> tuple[bool, str]:
    proc = run(["hyprctl", "-r", "eval", expression], timeout=4.0)
    message = (proc.stderr or proc.stdout).strip()
    return proc.returncode == 0 and not message.lower().startswith("error"), message


def _pointer_speed_snapshot() -> dict[str, float]:
    result = {}
    for device in pointer_devices():
        name = str(device.get("name", "")).strip()
        if not name:
            continue
        try:
            result[name] = float(device.get("defaultSpeed", device.get("default_speed", 0.0)))
        except (TypeError, ValueError):
            continue
    return result


def apply_mouse(values: dict, record_history: bool = True) -> tuple[bool, str]:
    previous = state()["mouse"].copy()
    if record_history:
        record(
            "Mouse settings",
            runtime={"kind": "mouse", "values": previous},
        )

    normalized = {
        "sensitivity": max(-1.0, min(1.0, float(values.get("sensitivity", 0.0)))),
        "accel_profile": (
            "flat" if str(values.get("accel_profile", "adaptive")).lower() == "flat"
            else "adaptive"
        ),
        "left_handed": bool(values.get("left_handed", False)),
        "natural_scroll": bool(values.get("natural_scroll", False)),
    }

    # Hyprland 0.55+ uses the Lua configuration API.  force_no_accel bypasses
    # most pointer processing, including the user-facing sensitivity control,
    # so disable it for this runtime profile whenever Yakushi owns mouse speed.
    global_lua = (
        "hl.config({ input = { "
        f"sensitivity = {normalized['sensitivity']:.3f}, "
        f"accel_profile = {_lua_string(normalized['accel_profile'])}, "
        "force_no_accel = false, "
        f"left_handed = {_lua_bool(normalized['left_handed'])}, "
        f"natural_scroll = {_lua_bool(normalized['natural_scroll'])} "
        "} })"
    )
    global_ok, global_message = _eval_lua(global_lua)

    # Legacy fallback for Hyprland <= 0.54.
    legacy_failures = []
    if not global_ok:
        legacy_mapping = [
            ("input:sensitivity", normalized["sensitivity"]),
            ("input:accel_profile", normalized["accel_profile"]),
            ("input:force_no_accel", "false"),
            ("input:left_handed", "true" if normalized["left_handed"] else "false"),
            ("input:natural_scroll", "true" if normalized["natural_scroll"] else "false"),
        ]
        for key, value in legacy_mapping:
            ok, message = keyword(key, str(value))
            if not ok:
                legacy_failures.append(f"{key}: {message}")

    devices = pointer_devices()
    device_failures = []
    successful_devices = 0

    for device in devices:
        name = str(device.get("name", "")).strip()
        if not name:
            continue

        device_lua = (
            "hl.device({ "
            f"name = {_lua_string(name)}, "
            f"sensitivity = {normalized['sensitivity']:.3f}, "
            f"accel_profile = {_lua_string(normalized['accel_profile'])}, "
            f"left_handed = {_lua_bool(normalized['left_handed'])}, "
            f"natural_scroll = {_lua_bool(normalized['natural_scroll'])} "
            "})"
        )
        ok, message = _eval_lua(device_lua)

        if not ok:
            # Old syntax fallback for older Hyprland versions.
            old_ok = True
            for option, value in [
                ("sensitivity", normalized["sensitivity"]),
                ("accel_profile", normalized["accel_profile"]),
                ("left_handed", "true" if normalized["left_handed"] else "false"),
                ("natural_scroll", "true" if normalized["natural_scroll"] else "false"),
            ]:
                item_ok, item_message = _device_keyword(name, option, value)
                if not item_ok:
                    old_ok = False
                    device_failures.append(f"{name}/{option}: {item_message}")
            ok = old_ok

        if ok:
            successful_devices += 1

    # Some touchpads additionally expose the dedicated touchpad natural-scroll
    # property. This call is harmless when no touchpad is present.
    _eval_lua(
        "hl.config({ input = { touchpad = { natural_scroll = "
        + _lua_bool(normalized["natural_scroll"])
        + " } } })"
    )

    data = state()
    data["mouse"] = normalized
    save_state(data)

    # Confirm that Hyprland's live device speed actually changed instead of
    # trusting a successful command response. hyprctl devices exposes this as
    # defaultSpeed for pointer devices.
    verified = []
    if devices:
        import time
        time.sleep(0.12)
        snapshot = _pointer_speed_snapshot()
        requested = normalized["sensitivity"]
        for device in devices:
            name = str(device.get("name", "")).strip()
            if name in snapshot and abs(snapshot[name] - requested) <= 0.055:
                verified.append(name)

    hard_failure = (
        (not global_ok and legacy_failures)
        and devices
        and successful_devices == 0
    )

    if hard_failure or (devices and not verified):
        details = []
        if global_message:
            details.append(f"Lua global: {global_message}")
        details.extend(legacy_failures)
        details.extend(device_failures)
        if devices and not verified:
            details.append(
                "Verification failed: Hyprland did not report the requested "
                f"pointer speed {normalized['sensitivity']:.2f}."
            )
        try:
            Path("/tmp/yakushi-mouse-error.log").write_text("\n".join(details) + "\n")
        except OSError:
            pass
        return False, (
            "Hyprland did not apply the requested pointer speed. "
            "Technical details: /tmp/yakushi-mouse-error.log"
        )

    if devices:
        return True, (
            f"Pointer speed {normalized['sensitivity']:+.2f} applied and verified "
            f"on {len(verified)}/{len(devices)} pointer device(s)."
        )

    if global_ok or not legacy_failures:
        return True, (
            f"Pointer speed {normalized['sensitivity']:+.2f} applied globally. "
            "No pointer device was available for live verification."
        )

    return False, "Hyprland rejected the mouse settings."


def monitors() -> list[dict]:
    value = json_command("monitors")
    return value if isinstance(value, list) else []


def normalize_monitor_mode(mode: str) -> str:
    """Convert an advertised mode into stable Hyprland monitor-rule syntax.

    Hyprland reports available modes with a trailing ``Hz`` and often fixed
    decimal precision (for example ``1920x1080@60.00Hz``).  The monitor rule
    syntax is most reliable when whole-number refresh rates are sent as whole
    numbers (``1920x1080@60``).  Fractional rates such as 59.94 are preserved.
    """
    value = str(mode or '').strip()
    if value in {'preferred', 'highres', 'highrr', 'maxwidth'}:
        return value

    value = re.sub(r'(?i)Hz$', '', value).strip()
    match = re.match(r'^(\d+)x(\d+)@([0-9.]+)$', value)
    if not match:
        return value

    width, height = int(match.group(1)), int(match.group(2))
    refresh = float(match.group(3))
    if abs(refresh - round(refresh)) < 0.005:
        refresh_text = str(int(round(refresh)))
    else:
        refresh_text = f'{refresh:.3f}'.rstrip('0').rstrip('.')
    return f'{width}x{height}@{refresh_text}'


def _mode_parts(mode: str) -> tuple[int, int, float] | None:
    match = re.match(r'^(\d+)x(\d+)@([0-9.]+)$', normalize_monitor_mode(mode))
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), float(match.group(3))


def _monitor_matches_mode(monitor: dict, mode: str) -> bool:
    requested = _mode_parts(mode)
    if requested is None:
        return True
    width, height, refresh = requested
    actual_width = int(monitor.get('width', 0) or 0)
    actual_height = int(monitor.get('height', 0) or 0)
    actual_refresh = float(monitor.get('refreshRate', 0.0) or 0.0)
    return (
        actual_width == width
        and actual_height == height
        and abs(actual_refresh - refresh) < 0.20
    )


def current_monitor_mode(monitor: dict) -> str:
    """Return the active monitor mode in the same syntax accepted by Hyprland."""
    return (
        f'{int(monitor.get("width", 0))}x{int(monitor.get("height", 0))}@'
        f'{float(monitor.get("refreshRate", 60)):.2f}'
    )


def pointer_devices() -> list[dict]:
    """Return pointer-like devices reported by Hyprland."""
    value = json_command("devices")
    if not isinstance(value, dict):
        return []

    result = []
    seen = set()
    for group in ("mice", "touchpads"):
        items = value.get(group, [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            if not name or name in seen:
                continue
            seen.add(name)
            result.append(dict(item))
    return result


def _device_keyword(device_name: str, key: str, value) -> tuple[bool, str]:
    proc = run(
        [
            "hyprctl",
            "-r",
            "--",
            "keyword",
            f"device[{device_name}]:{key}",
            str(value),
        ],
        timeout=4.0,
    )
    return proc.returncode == 0, (proc.stderr or proc.stdout).strip()


def _mode_resolution(mode: str) -> tuple[int, int] | None:
    match = re.match(r'^(\d+)x(\d+)(?:@[0-9.]+)?$', normalize_monitor_mode(mode))
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _valid_scale_for_mode(mode: str, scale: float) -> bool:
    resolution = _mode_resolution(mode)
    if resolution is None or scale <= 0:
        return True
    width, height = resolution
    logical_w = width / scale
    logical_h = height / scale
    return abs(logical_w - round(logical_w)) < 1e-7 and abs(logical_h - round(logical_h)) < 1e-7


def _display_error_log(value: str, message: str) -> None:
    try:
        Path('/tmp/yakushi-display-error.log').write_text(
            f'rule={value}\n\n{message}\n'
        )
    except OSError:
        pass


def _apply_monitor_rule(name: str, mode: str, position: str, scale: float) -> tuple[bool, str]:
    clean_mode = normalize_monitor_mode(mode)
    clean_position = str(position or '').strip()

    if not re.match(r'^(?:-?\d+x-?\d+|auto(?:-(?:left|right|up|down))?)$', clean_position):
        return False, 'Monitor position must look like 0x0, -1920x0, or auto.'

    if not _valid_scale_for_mode(clean_mode, float(scale)):
        resolution = _mode_resolution(clean_mode)
        label = f'{resolution[0]}×{resolution[1]}' if resolution else clean_mode
        return False, (
            f'Scale {float(scale):.2f} does not divide {label} into whole logical pixels. '
            'Try 1.00, 1.50, 2.00, or another scale that divides this resolution cleanly.'
        )

    rule = f'{name},{clean_mode},{clean_position},{float(scale):.2f}'

    # Hyprland 0.55+ moved monitor configuration to Lua.  Runtime changes should
    # therefore use hl.monitor(...).  Try that first and retain the legacy
    # `keyword monitor` path for Hyprland <= 0.54.
    def lua_quote(value: str) -> str:
        return (
            '"'
            + str(value).replace('\\', '\\\\').replace('"', '\\"')
            + '"'
        )

    expression = (
        'hl.monitor({ output = ' + lua_quote(name)
        + ', mode = ' + lua_quote(clean_mode)
        + ', position = ' + lua_quote(clean_position)
        + ', scale = ' + f'{float(scale):.4f}'
        + ' })'
    )

    modern = run(['hyprctl', '-r', 'eval', expression], timeout=5.0)
    modern_raw = (modern.stderr or modern.stdout).strip()

    if modern.returncode == 0:
        proc = modern
        raw = modern_raw
        backend = 'lua'
    else:
        legacy = run(
            ['hyprctl', '-r', '--', 'keyword', 'monitor', rule],
            timeout=5.0,
        )
        proc = legacy
        raw = (legacy.stderr or legacy.stdout).strip()
        backend = 'legacy'

    if proc.returncode != 0:
        _display_error_log(
            rule,
            'Lua attempt:\n' + modern_raw + '\n\nFinal backend: ' + backend
            + '\nResult:\n' + raw,
        )
        return False, (
            'Hyprland rejected this display combination. '
            'Technical details were saved to /tmp/yakushi-display-error.log.'
        )

    # Verify the requested mode actually became active.  This catches the case
    # where the compositor returns `ok` but the output remains at the previous
    # refresh rate.
    if _mode_parts(clean_mode) is not None:
        for _attempt in range(8):
            time.sleep(0.12)
            current = next(
                (item for item in monitors() if item.get('name') == name),
                None,
            )
            if current is None or _monitor_matches_mode(current, clean_mode):
                return True, f'{name} updated to {clean_mode}.'

        current = next(
            (item for item in monitors() if item.get('name') == name),
            None,
        )
        if current is not None:
            actual = current_monitor_mode(current)
            _display_error_log(
                rule,
                f'Backend: {backend}\nCommand returned success, but active mode is still {actual}.',
            )
            return False, (
                f'Hyprland kept {normalize_monitor_mode(actual)} instead of {clean_mode}. '
                'The selected mode was not applied. Yakushi tried the current Hyprland monitor API. '
                'Details: /tmp/yakushi-display-error.log.'
            )

    return True, f'{name} updated.'


def apply_monitor(name: str, mode: str, position: str, scale: float) -> tuple[bool, str]:
    current = next(
        (monitor for monitor in monitors() if monitor.get("name") == name),
        None,
    )
    if current:
        previous_mode = current_monitor_mode(current)
        record(
            f"Display {name}",
            runtime={
                "kind": "monitor",
                "values": {
                    "name": name,
                    "mode": previous_mode,
                    "position": f'{current.get("x", 0)}x{current.get("y", 0)}',
                    "scale": float(current.get("scale", 1.0)),
                },
            },
        )

    return _apply_monitor_rule(name, mode, position, scale)



def _logical_rect(item: dict) -> tuple[float, float, float, float] | None:
    mode = item.get("mode")
    resolution = _mode_resolution(str(mode or ""))
    if resolution is None:
        return None
    scale = float(item.get("scale", 1.0) or 1.0)
    if scale <= 0:
        return None
    position = str(item.get("position", "0x0"))
    match = re.match(r'^(-?\d+)x(-?\d+)$', position)
    if not match:
        return None
    x, y = int(match.group(1)), int(match.group(2))
    w, h = resolution[0] / scale, resolution[1] / scale
    return float(x), float(y), float(x + w), float(y + h)


def _layout_overlap(layout: list[dict]) -> tuple[str, str] | None:
    rects = []
    for item in layout:
        rect = _logical_rect(item)
        if rect is not None:
            rects.append((str(item.get("name", "Display")), rect))
    for index, (name_a, a) in enumerate(rects):
        for name_b, b in rects[index + 1:]:
            overlaps = a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]
            if overlaps:
                return name_a, name_b
    return None


def apply_monitor_layout(layout: list[dict]) -> tuple[bool, str]:
    overlap = _layout_overlap(layout)
    if overlap:
        return False, (
            f"{overlap[0]} and {overlap[1]} overlap. Move the display blocks apart "
            "before applying the layout."
        )

    current = monitors()
    previous = []
    for monitor in current:
        previous.append({
            "name": monitor.get("name"),
            "mode": current_monitor_mode(monitor),
            "position": f'{monitor.get("x", 0)}x{monitor.get("y", 0)}',
            "scale": float(monitor.get("scale", 1.0)),
        })

    record(
        "Display layout",
        runtime={"kind": "monitor_layout", "values": previous},
    )

    # Changing several monitor positions one-by-one can create a temporary
    # overlap even when the final layout is valid. First move each display to
    # a harmless staging position, then apply the requested final layout.
    # This avoids Hyprland rejecting swaps/rearrangements midway through.
    failures = []
    for index, item in enumerate(layout):
        name = item.get("name")
        mode = item.get("mode")
        scale = item.get("scale", 1.0)
        if name is None or mode is None or scale is None:
            continue
        staging_position = f'{50000 + (index * 10000)}x0'
        ok, message = _apply_monitor_rule(
            str(name), str(mode), staging_position, float(scale)
        )
        if not ok:
            failures.append(f"{name}: {message}")

    if failures:
        # Best effort restore if staging itself failed.
        for item in previous:
            _apply_monitor_rule(
                str(item["name"]),
                str(item["mode"]),
                str(item["position"]),
                float(item["scale"]),
            )
        return False, "\n".join(failures)

    for item in layout:
        name = item.get("name")
        mode = item.get("mode")
        position = item.get("position")
        scale = item.get("scale", 1.0)
        if not all(value is not None for value in (name, mode, position, scale)):
            continue
        ok, message = _apply_monitor_rule(
            str(name), str(mode), str(position), float(scale)
        )
        if not ok:
            failures.append(f"{name}: {message}")

    if failures:
        return False, "\n".join(failures)
    return True, "Display layout applied."


def preferred_monitor() -> str:
    return str(state().get("preferred_monitor", ""))


def set_preferred_monitor(name: str) -> tuple[bool, str]:
    if not any(monitor.get("name") == name for monitor in monitors()):
        return False, "Display was not found."

    data = state()
    data["preferred_monitor"] = name
    save_state(data)

    proc = run(["hyprctl", "dispatch", "focusmonitor", name], timeout=4.0)
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout).strip() or "Could not focus display."

    return True, f"{name} is now Yakushi's preferred display and has been focused."
