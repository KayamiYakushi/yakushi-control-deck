# Changelog

## 1.2.1

- Reset the main content scroll position to the top whenever a sidebar page is opened.
- Wallpapers now defaults to the `~/Documents` library.
- `Documents` and `Pictures` root filters now include images in nested subfolders.
- Keep both wallpaper roots indexed while making Documents the initial view.

## 1.2.0

- Added **Auto Color Theme** generation from the current wallpaper.
- Added DARK and LIGHT auto-palette modes with contrast-safe tonal roles.
- Added optional **FOLLOW WALLPAPER** mode; wallpapers applied through Yakushi can recolor Waybar/Rofi/shared desktop colors automatically.
- Auto Color also requests the matching GNOME/libadwaita color scheme so apps such as Nautilus follow dark/light intent where supported.
- Added **Nautilus Studio** with compositor-level opacity control.
- Nautilus opacity uses a marked Hyprland window rule instead of fragile GTK/libadwaita CSS overrides.
- Supports both modern Hyprland Lua config and legacy `hyprland.conf`, with backup, reload validation, and automatic rollback on new config errors.
- 100% Nautilus opacity removes the Yakushi-managed rule cleanly.
- Added explicit `gdk-pixbuf2` dependency for wallpaper color sampling; still official Arch repositories only.

## 1.1.5
- Fixed `doctor.sh` false failures for Waybar JSONC files and fresh-clone SDDM bundle detection.
- Added a standard-library JSONC validator supporting comments and trailing commas.
- Installer now runs a package-integrity preflight before modifying desktop files.
- Installer validates Waybar with JSONC rules instead of strict JSON.
- Added `./smoke-test.sh` for non-destructive fresh-clone/release validation.
- Installed app now keeps diagnostics, SDDM recovery, lock-bind helper, restore helper, and JSONC tooling under `~/.local/share/yakushi-control-deck`.
- Added terminal `sudo` fallback when disabling/restoring the Yakushi SDDM theme if Polkit fails.

## 1.1.4
- Fixed SDDM installation on systems where Polkit/pkexec authentication fails even though normal `sudo` works.
- `INSTALL / UPDATE SDDM` now falls back to a visible Kitty sudo installer instead of silently leaving the stock SDDM theme active.
- Added `./install-sddm-theme.sh` as a reliable terminal installer and recovery path.
- Hardened the root SDDM helper so `previewMode=true` can never leak from test mode into the real login greeter.
- Added post-install verification for the Yakushi theme files and active `Current=yakushi` selection.
- Added optional `./bind-super-m-lock.fish` helper to map `Super+M` to Hyprlock without logging out; it backs up the Hyprland config and rolls back on new config errors.

## 1.1.3
- SDDM preview mode no longer gets stuck on `WAIT`; SDDM test mode cannot perform real login actions, so Yakushi now reports preview-only status instead.
- Removed the editable username field from the Yakushi login screen.
- Login automatically uses SDDM's last successful user, with the installing user as a safe fallback.
- Password input receives focus immediately for a faster boot-login flow.

## 1.1.2
- Fixed SDDM preview fallback caused by `SddmComponents` / `QtQuick.Controls` type-name collisions.
- SDDM controls are now explicitly bound to Qt Quick Controls 2 (`QQC2`).
- Improved Polkit authorization failure feedback for SDDM installation.

## 1.1.1

- Fixed the 1.1.0 hotfix/install-path bug where the SDDM theme source could be absent from the installed Control Deck.
- Added the complete Qt6 `integrations/sddm/yakushi` theme (`Main.qml`, `metadata.desktop`, `theme.conf`).
- Reworked the SDDM design to visually mirror the Yakushi Hyprlock screen.
- Login staging now follows Lock Screen wallpaper, 12/24-hour clock, date visibility, brightness, and blur intent by default.
- SDDM preview clears conflicting Qt/QML environment paths before launching test mode.
- SDDM installation now verifies `/usr/share/sddm/themes/yakushi/Main.qml` and that the active theme resolves to `yakushi` before reporting success.

## 1.1.0

- Added Lock Screen Studio for Hyprlock wallpaper, blur, brightness, clock, and date controls.
- Added Login Screen Studio with a custom Yakushi SDDM theme.
- SDDM wallpaper is copied into the system theme so private home-directory permissions do not break the greeter.
- Added SDDM test-mode preview, install/update, and disable/restore actions.
- SDDM install uses Polkit authorization and preserves the original `/etc/sddm.conf` when it must be patched for precedence.

## 1.0.1

- Fixed Rofi background opacity not reliably affecting the final rendered window.
- Added a final `yakushi-opacity.rasi` override imported after the main theme.
- Theme Studio changes the Rofi RGB while preserving the selected opacity.
- Rofi Studio now writes a concrete `rgba(...)` window background.


## 1.0.0 — 2026-08-31

First public release. Includes Control Deck, bundled Waybar/Rofi integration, display/input/power controls, tonal themes, wallpapers, typography, Bar Studio, Rofi Studio, Kitty controls, history and backups.
