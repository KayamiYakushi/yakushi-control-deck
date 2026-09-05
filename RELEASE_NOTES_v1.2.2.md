# Yakushi Control Deck v1.2.2

v1.2.2 is a focused SDDM responsiveness and privilege-flow fix.

## Fixed

- `INSTALL / UPDATE SDDM` no longer blocks the GTK main loop while waiting for Polkit or sudo authorization.
- SDDM install and restore actions now run in a background worker and return status updates to GTK safely.
- SDDM action buttons are disabled while an operation is active, preventing accidental duplicate installs.
- The Kitty sudo fallback now launches detached and no longer reports a false failure simply because the terminal remains open for password input.

No existing Waybar, Rofi, Hyprland, Kitty, wallpaper, theme, or SDDM settings are replaced by the hotfix.
