from __future__ import annotations

import json
import os

from .io import run


APP_CLASS = "dev.yakushi.ControlDeckLite"
TARGET_WIDTH = 1190
TARGET_HEIGHT = 820


def _client_for_this_process() -> dict | None:
    proc = run(["hyprctl", "-j", "clients"], timeout=2.0)
    if proc.returncode != 0:
        return None

    try:
        clients = json.loads(proc.stdout)
    except (TypeError, json.JSONDecodeError):
        return None

    pid = os.getpid()
    if not isinstance(clients, list):
        return None

    # PID is the strongest selector.  The class fallback covers compositors
    # that report the GTK process through a small launcher indirection.
    for client in clients:
        if int(client.get("pid", -1)) == pid:
            return client
    for client in clients:
        if client.get("class") == APP_CLASS or client.get("initialClass") == APP_CLASS:
            return client
    return None


def _dispatch_new(expression: str) -> bool:
    proc = run(["hyprctl", "dispatch", expression], timeout=2.0)
    return proc.returncode == 0


def _dispatch_legacy(name: str, argument: str = "") -> bool:
    command = ["hyprctl", "dispatch", name]
    if argument:
        command.append(argument)
    proc = run(command, timeout=2.0)
    return proc.returncode == 0


def ensure_control_deck_floating() -> bool:
    """Float this exact Yakushi window on old and new Hyprland releases.

    Hyprland 0.55 moved dispatch expressions to Lua, while older installations
    use the classic positional dispatcher syntax.  Try the current syntax
    first and retain the legacy path so the deck does not force a compositor
    upgrade just to obtain a floating settings window.
    """
    if not os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        return True

    client = _client_for_this_process()
    if not client:
        return False

    address = str(client.get("address", "")).strip()
    if not address:
        return False

    selector = f"address:{address}"

    # Hyprland >= 0.55 Lua dispatcher expression.
    escaped = selector.replace('\\', '\\\\').replace('"', '\\"')
    new_float = (
        'hl.dsp.window.float({ window = "'
        + escaped
        + '", action = "on" })'
    )
    floated = _dispatch_new(new_float)

    # Hyprland <= 0.54 classic dispatcher fallback.
    if not floated:
        floated = _dispatch_legacy("setfloating", selector)

    if not floated:
        return False

    # Force a predictable opening geometry every time. GTK's default size is
    # only a hint under Wayland; Hyprland owns the final floating dimensions.
    new_resize = (
        'hl.dsp.window.resize({ x = '
        + str(TARGET_WIDTH)
        + ', y = '
        + str(TARGET_HEIGHT)
        + ', relative = false, window = "'
        + escaped
        + '" })'
    )
    resized = _dispatch_new(new_resize)

    # Hyprland <= 0.54 classic dispatcher fallback.
    if not resized:
        _dispatch_legacy(
            "resizewindowpixel",
            f"exact {TARGET_WIDTH} {TARGET_HEIGHT},{selector}",
        )

    # Center after resizing so the final geometry is centered, not the old one.
    new_center = 'hl.dsp.window.center({ window = "' + escaped + '" })'
    if not _dispatch_new(new_center):
        # Some 0.55 builds expose center directly under hl.dsp instead.
        fallback_center = 'hl.dsp.center({ window = "' + escaped + '" })'
        if not _dispatch_new(fallback_center):
            # Old Hyprland: this targets the active floating window. The deck is
            # normally focused immediately after present(), so this is best effort.
            _dispatch_legacy("centerwindow", "1")

    return True
