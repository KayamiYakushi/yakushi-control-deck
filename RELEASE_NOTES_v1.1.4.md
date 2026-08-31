# Yakushi Control Deck v1.1.4

This release hardens the new Lock/Login workflow introduced in 1.1.x.

## Fixed

- SDDM installation no longer depends solely on a successful graphical Polkit prompt.
- If `pkexec` authentication fails, Control Deck opens a visible Kitty terminal and falls back to normal `sudo` authentication.
- Added `install-sddm-theme.sh` for manual/recovery installation.
- The real SDDM greeter is protected from accidentally inheriting `previewMode=true` from SDDM test mode.
- SDDM installation verifies both the installed theme and `Current=yakushi` before considering the system configured.

## Added

- Optional `bind-super-m-lock.fish` helper: `Super+M` locks with Hyprlock instead of ending the Hyprland session.
- The bind helper supports modern Hyprland Lua configs and legacy `hyprland.conf`, with backup, rollback, reload, and runtime verification.

## Existing 1.1 features

- Lock Screen Studio: wallpaper, blur, brightness, 12/24-hour clock and date settings.
- Matching Yakushi SDDM login theme.
- Password-first SDDM flow using the last successful user automatically.
- SDDM preview mode that cannot get stuck waiting for a real login response.
