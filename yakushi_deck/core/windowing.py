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

    if not isinstance(clients, list):
        return None

    pid = os.getpid()

    for client in clients:
        try:
            if int(client.get("pid", -1)) == pid:
                return client
        except (TypeError, ValueError):
            pass

    for client in clients:
        if client.get("class") == APP_CLASS or client.get("initialClass") == APP_CLASS:
            return client

    return None


def _eval(expression: str) -> bool:
    proc = run(["hyprctl", "-r", "eval", expression], timeout=2.0)
    return proc.returncode == 0


def _legacy(name: str, argument: str = "") -> bool:
    command = ["hyprctl", "dispatch", name]
    if argument:
        command.append(argument)
    proc = run(command, timeout=2.0)
    return proc.returncode == 0


def ensure_control_deck_floating(*, center: bool = True) -> bool:
    """One-shot floating/resize for the Yakushi window.

    No persistent rules, no min/max constraints, no watchdog and no background
    resize loop are used. Hyprland 0.55+ is handled through `hyprctl -r eval`;
    older Hyprland releases retain the classic dispatcher fallback.
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
    escaped = selector.replace("\\", "\\\\").replace('"', '\\"')

    floated = bool(client.get("floating"))
    if not floated:
        floated = _eval(
            'hl.dsp.window.float({ window = "'
            + escaped
            + '", action = "on" })'
        )
        if not floated:
            floated = _legacy("setfloating", selector)

    if not floated:
        return False

    resized = _eval(
        'hl.dsp.window.resize({ x = '
        + str(TARGET_WIDTH)
        + ', y = '
        + str(TARGET_HEIGHT)
        + ', relative = false, window = "'
        + escaped
        + '" })'
    )
    if not resized:
        _legacy(
            "resizewindowpixel",
            f"exact {TARGET_WIDTH} {TARGET_HEIGHT},{selector}",
        )

    if center:
        centered = _eval(
            'hl.dsp.window.center({ window = "' + escaped + '" })'
        )
        if not centered:
            _legacy("centerwindow", "1")

    return True
