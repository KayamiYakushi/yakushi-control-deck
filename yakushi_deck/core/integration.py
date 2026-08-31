from __future__ import annotations

import re

from .history import record
from .io import atomic_write, run
from .paths import WAYBAR_CONFIG


def configure_waybar_launcher() -> tuple[bool, str]:
    """Make the existing top-left Waybar launcher open Yakushi Control Deck.

    Left click opens Yakushi.  The previous application-launcher behavior is
    preserved on right click when the module used `rofi -show drun`.
    """
    if not WAYBAR_CONFIG.exists():
        return False, "Waybar config was not found."

    original = WAYBAR_CONFIG.read_text()
    block_match = re.search(
        r'(?P<head>"custom/launcher"\s*:\s*\{)(?P<body>.*?)(?P<tail>\n\s*\})',
        original,
        flags=re.S,
    )
    if not block_match:
        return False, 'Waybar module "custom/launcher" was not found.'

    body = block_match.group('body')
    click_match = re.search(r'"on-click"\s*:\s*"([^"]*)"', body)
    previous_click = click_match.group(1) if click_match else ""

    def append_property(current: str, line: str) -> str:
        trailing = current[len(current.rstrip()):]
        core = current.rstrip()
        if core and not core.endswith(','):
            core += ','
        return core + '\n        ' + line + trailing

    if click_match:
        body = re.sub(
            r'("on-click"\s*:\s*)"[^"]*"',
            r'\1"yakushi-deck"',
            body,
            count=1,
        )
    else:
        body = append_property(body, '"on-click": "yakushi-deck"')

    # Keep the original application menu one right click away.  Do not
    # overwrite a custom right-click action the user already has.
    if '"on-click-right"' not in body and 'rofi -show drun' in previous_click:
        body = append_property(body, '"on-click-right": "rofi -show drun"')

    updated = (
        original[:block_match.start('body')]
        + body
        + original[block_match.end('body'):]
    )

    if updated == original:
        return True, "Waybar launcher already opens Yakushi Control Deck."

    record("Waybar Yakushi launcher", files=[WAYBAR_CONFIG])
    atomic_write(WAYBAR_CONFIG, updated)

    run(["pkill", "-x", "waybar"], timeout=2.0)
    run(
        ["sh", "-lc", "nohup waybar >/tmp/yakushi-waybar.log 2>&1 &"],
        timeout=2.0,
    )
    return True, "Top-left Waybar launcher now opens Yakushi Control Deck."
