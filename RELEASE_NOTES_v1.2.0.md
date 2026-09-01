# Yakushi Control Deck v1.2.0

This feature release adds wallpaper-driven desktop colors and a dedicated Nautilus integration.

## Highlights

- Auto Color Theme generated from the current wallpaper
- DARK and LIGHT auto-color modes
- Optional FOLLOW WALLPAPER behavior for Yakushi wallpaper changes
- Contrast-safe nine-role tonal palette generation
- GNOME/libadwaita dark/light preference sync where available
- Nautilus Studio with 30–100% opacity control
- Compositor-level Nautilus opacity using Hyprland rules
- Modern Hyprland Lua + legacy hyprland.conf support
- Automatic config backup, reload validation and rollback
- 100% opacity cleanly removes the Yakushi Nautilus rule
- No AUR dependency; GdkPixbuf color sampling comes from official Arch packages

## Notes

Auto Color automatically follows wallpapers changed from Yakushi Control Deck. It does not run a background polling daemon for wallpaper tools managed outside Yakushi.

Nautilus remains optional and is not installed automatically. If it is installed, the opacity control works without modifying Nautilus/libadwaita files.
