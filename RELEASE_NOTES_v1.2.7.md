# Yakushi Control Deck v1.2.7

v1.2.7 polishes Fastfetch Studio after the v1.2.6 apply fixes.

## Fixed

- Custom ASCII logos no longer turn white after saving.
- Yakushi now uses Fastfetch `file` mode with `$1` color placeholders for the rendered logo, while keeping the pasted ASCII source untouched.
- ASCII logo color follows Terminal Studio accent through Kitty ANSI color1.
- Re-enabled Fastfetch modules no longer get appended to the bottom.
- Disabled modules remember neighboring modules and restore to a stable position.
- A one-time migration repairs information modules that v1.2.6 had already placed after the final color palette.

For Arch Linux + Hyprland.
