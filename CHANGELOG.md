# v1.2.27

- Fixed the Raycast Glass footer expanding into a large empty panel; it now stays compact and results shrink to the actual item count.
- Reduced launcher width, padding, row height, icon size, and corner radius for a closer Raycast-like footprint.
- Added a managed Hyprland Rofi layer-blur rule for both Lua and modern `.conf` configurations, with reload validation and full rollback on failure.
- Kept the footer's Esc/Enter controls on Rofi's native clickable button actions and left all five power-menu actions unchanged.

# v1.2.26

- Added a Raycast-inspired **RAYCAST GLASS** Rofi preset with fuzzy search, a unified result surface, and clickable keyboard-action hints.
- Added a matching in-app launcher preview while keeping colors linked to Theme Studio and geometry/opacity editable in Rofi Studio.
- Split launcher opacity from the five-action power menu so applying or tuning the new preset cannot restyle its Lock, Suspend, Logout, Reboot, or Shutdown actions.

# v1.2.25

- Replaced Fastfetch's default text labels with compact Nerd Font module icons.
- Kept the packaged fresh-install config and Fastfetch Studio safe-reset config aligned.
- Added a smoke-test guard so the Yakushi Fastfetch icon mapping cannot silently regress.

# v1.2.20

- Reduced the sidebar footprint and prevented decorative content from widening it.
- Removed the `YAKUSHIS FAV SONG` / barcode footer entirely.
- Kept navigation, search, and all functional pages unchanged.

## v1.2.19

- Fixed the remaining Wallpaper page width-growth bug by removing unbounded nested directory names from the folder dropdown model.
- Documents and Pictures remain recursive root filters; search still covers all indexed nested images.
- Prevented hidden Stack pages from contributing their natural width to the application window.
- Prevented the main content scroller from propagating oversized child natural widths to the top-level window.
- Kept the deck non-resizable at its intended floating geometry; oversized content now scrolls internally.
- Reduced the wallpaper library to three columns so its minimum width always fits inside the standard deck size.

## v1.2.18

- Fixed the remaining Wallpaper page/window growth caused by long nested folder captions participating in GTK natural-width negotiation.
- Wallpaper preview labels are now hard-bounded, clipped and tooltip-backed; full filesystem paths can no longer widen the page.
- Wallpaper thumbnails never fall back to an unbounded full-resolution Gtk.Picture on decode errors.
- Re-clamps the Control Deck floating geometry after wallpaper + Follow Wallpaper palette updates, preventing a pathological layout request from leaving the window enlarged.
- Bar Studio module controls now use tiny fixed-size GTK switches: grey when disabled, Yakushi red when enabled.
- Removed inline module preview codes from rows so each switch stays visually separate at the far-right edge.
- Tightened module row height/padding while preserving explicit LEFT / CENTER / RIGHT lanes and drag-and-drop ordering.

# Changelog

## v1.2.14

- Fixed optical misalignment in the five-action Rofi power menu.
- Replaced mixed icon families with one Material Design Nerd Font family so Lock, Suspend, Logout, Reboot, and Shutdown share consistent font metrics.
- Normalized icon sizing and element text padding while preserving the existing Yakushi glass layout.

## v1.2.13

- Removed the obsolete power-menu theme/colorizer action.
- Normalized the Waybar power menu to five actions: Lock, Suspend, Logout, Reboot, Shutdown.
- Added a dedicated horizontal Rofi power-menu theme that follows Yakushi colors and opacity.
- Fresh installs back up and install the dedicated power-menu theme safely.

## v1.2.12

- Fixed installed `doctor.sh` integrity checks by automatically selecting installed-layout smoke testing.
- Added current desktop and Control Deck showcase screenshots to the public README/release bundle.
- Release artifacts are now checked for stray Python `__pycache__` / `.pyc` files.
- Installed copies keep the screenshot assets referenced by their bundled README.
- Updated Fastfetch startup documentation to match the CachyOS/vendor-safe single `fish_greeting` override.
- Final public stability/polish pass over the v1.2.x release line.

## v1.2.11

- Fixed Fastfetch OFF/ON on CachyOS and other Fish setups that define `fish_greeting` from a vendor file.
- Yakushi now shadows vendor `fish_greeting` safely from the end of the user `config.fish`; package-owned files under `/usr/share` are never modified.
- OFF is normalized to zero Fastfetch runs and ON to exactly one run in new Fish terminals.

## 1.2.11

- Fixed duplicate Fastfetch output when startup was enabled.
- Fastfetch OFF now targets zero startup runs; ON targets exactly one managed Fish greeting run.
- Fish startup source chains are normalized so legacy dotfiles calls do not stack with Yakushi.
- Added startup invocation probing for Fish autorun verification.

## 1.2.9

- Repairs a zero-length Fastfetch `config.jsonc` automatically instead of letting terminal startup fail.
- Adds a `RESET SAFE DEFAULT` action to Fastfetch Studio while preserving the user ASCII source.
- Adds Window Frame & Shadow controls to Appearance.
- Window borders can follow the Yakushi theme or use custom active/inactive colors.
- Drop shadows expose color, opacity, size, falloff, X/Y offset, and scale controls.
- FOLLOW mode re-synchronizes window border/shadow colors whenever Theme Studio or Auto Color changes the desktop palette.

## 1.2.8

- Fixed Fastfetch startup OFF on Fish setups that launch Fastfetch from `fish_greeting.fish`, not only `config.fish` or `conf.d`.
- Fastfetch startup OFF now disables common standalone/guarded startup calls while preserving the original line for exact restoration when turned back ON.
- Added Fastfetch ASCII **Horizontal offset** and **Vertical offset** controls using Fastfetch logo left/top padding.
- Saving or recoloring a Yakushi ASCII logo now preserves its position instead of resetting padding.
- Added one-click **APPLY POSITION + PREVIEW** for immediate placement tuning.

## 1.2.7

- Fixed custom Fastfetch ASCII logos turning white by switching Yakushi-managed text logos from `file-raw` to Fastfetch's color-aware `file` mode.
- Added generated `yakushi-logo.txt` rendering with Fastfetch's supported `$1` color placeholder while keeping the user's pasted `logo.txt` clean.
- Fastfetch ASCII logo, title and keys now follow Terminal Studio accent through Kitty ANSI color1.
- Fixed module toggles appending re-enabled entries to the end of the Fastfetch module list.
- Disabled modules now remember neighboring modules and restore to a stable position.
- Added migration repair for information modules that v1.2.6 had already appended after the final color palette.

## 1.2.6

- Fixed Terminal Studio color application by writing a concrete managed color block at the end of the active Kitty config.
- Added active Kitty config detection for KITTY_CONFIG_DIRECTORY and explicit `--config` launches.
- Kitty config reads now respect last-assignment-wins semantics.
- Fixed Fastfetch module toggles with write-back verification and a canonical JSON fallback for unusual JSONC layouts.
- Fastfetch module Apply now opens a fresh Kitty preview automatically.
- Yakushi-managed Fish autorun now uses the exact Fastfetch config path.


## 1.2.5

- Fixed Terminal Color Studio by moving Yakushi colors into a dedicated `~/.config/kitty/yakushi-colors.conf` override imported last, so existing Kitty themes can no longer silently override the selected palette.
- Terminal color changes now request an immediate Kitty config reload when possible.
- Added a dedicated **Fastfetch Studio** under `03 // APPS & KEYS`.
- Added Fastfetch terminal-startup ON/OFF controls for Fish, Bash and Zsh without replacing shell configs.
- Added pasteable custom ASCII art with `SAVE ASCII + PREVIEW`, backed by `~/.config/fastfetch/logo.txt` and Fastfetch `file-raw` logo mode.
- Added per-module visibility switches, including Window manager / Hyprland, OS, Kernel, CPU, GPU, Memory, Disk and more.
- Disabled modules preserve their previous custom object where possible so re-enabling restores custom formatting.
- Added **FOLLOW TERMINAL ACCENT** to route Fastfetch key/title colors through Kitty ANSI color1.
- Added a complete Advanced JSONC editor with validation, backups and one-click Kitty preview.
- Fresh installs now include the official Arch `fastfetch` package and create a Yakushi Fastfetch config only when the user does not already have one.

## 1.2.4

- Added **Terminal Color Studio** to the Kitty page.
- Added **FOLLOW YAKUSHI THEME** mode for automatic Kitty synchronization with Theme Studio and Auto Color.
- Added **CUSTOM** mode with independent background, foreground and accent color pickers.
- Accent now generates a cohesive 16-color ANSI palette so Fastfetch, prompts and CLI colors follow the selected terminal tone.
- Added a live Terminal color preview.
- Existing Kitty opacity, font size and padding controls remain independent from color management.
- Fresh installs start with a Yakushi-matched Kitty palette in FOLLOW mode; existing Kitty configs are preserved until the user explicitly applies terminal colors.

## 1.2.3

- Replaced SDDM `pkexec` authorization with an explicit Kitty + `sudo` terminal prompt.
- Fixes invisible administrator prompts on minimal Hyprland sessions without a graphical Polkit authentication agent.
- SDDM install/update and restore no longer wait on Polkit at all.
- Login Screen status text now tells the user that a terminal authorization prompt is being opened.
- Existing desktop, Waybar, Rofi, Hyprlock, wallpaper, and SDDM settings remain untouched by the hotfix.

## 1.2.2

- Fixed the Control Deck becoming unresponsive while `INSTALL / UPDATE SDDM` or SDDM restore waits for administrator authorization.
- SDDM install/restore now runs off the GTK main thread and updates status safely through the GLib main loop.
- SDDM action buttons are temporarily disabled while a privileged operation is running to prevent duplicate jobs.
- Kitty sudo fallback is now launched detached instead of being misclassified as failed after a short subprocess timeout.

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

## v1.2.15
- Reworked the Rofi power menu to use fixed-size SVG icons instead of font glyphs.
- Removes Nerd Font baseline/em-box drift from Lock, Suspend, Logout, Reboot, and Shutdown.
- Power-menu selection now uses a dark hover surface with an accent border so icon tint remains consistent.


## v1.2.16
- Reworked Bar Studio into a compact two-column settings grid and stacked wrap-aware module lanes.
- Removed oversized fixed-height module columns and redundant per-module technical/description text from the main layout; details remain available via tooltips.
- Hardened Wallpaper Studio thumbnail sizing so a single image cannot stretch to fill the library viewport.
- Disabled homogeneous FlowBox allocation and fixed thumbnail expansion behavior to prevent the wallpaper picker from visually growing after repeated Follow Wallpaper applies.
