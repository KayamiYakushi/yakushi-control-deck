# 薬 Yakushi Control Deck

A lightweight GTK4 control deck and matching Waybar/Rofi setup for **Arch Linux + Hyprland**.

## Showcase

### Desktop

![Yakushi desktop](screenshots/desktop.png)

### Control Deck

![Yakushi Control Deck](screenshots/control-deck.png)

## Highlights

- No shell replacement, Electron, Node, AUR, or `yay` requirement.
- Display layout, refresh rate, scale and position controls.
- Keyboard and mouse controls with live Hyprland verification.
- Balanced / Performance power management.
- Tonal Theme Studio, **wallpaper-driven Auto Color (Dark/Light)**, desktop typography, wallpapers, reliable theme-aware Kitty colors, Fastfetch Studio (startup toggle, ASCII editor, module switches and logo positioning) and Rofi appearance.
- Matching Hyprlock lock screen and Yakushi SDDM boot login theme.
- Waybar drag-and-drop module ordering and enable/disable controls.
- **Nautilus Studio** with reversible Hyprland-level window opacity control.
- `REVERT LAST` history and automatic install backups.

## Bundled Waybar + Rofi

The installer deploys a tested matching setup:

- Left click **薬** → Yakushi Control Deck
- Right click **薬** → Rofi applications
- Power button → Rofi power menu
- Shared `~/.config/hypr/colors.css` + `colors.rasi` theme roles
- Hardware-independent CPU/GPU temperature detection for common drivers

## Install

```bash
git clone https://github.com/KayamiYakushi/yakushi-control-deck.git
cd yakushi-control-deck
./install.sh
```

Fish users can run:

```fish
./install.fish
```

The installer uses official Arch repositories only. Existing Waybar, Rofi, shared color, Kitty and Fastfetch files are backed up under:

```text
~/.config/yakushi-control-deck/install-backups/<timestamp>/
```

Launch with:

```bash
yakushi-deck
```

If your shell does not include `~/.local/bin` in `PATH`, use `~/.local/bin/yakushi-deck`. The bundled Waybar uses the absolute path and is unaffected.

## Pre-install / release smoke test

Before installing, a fresh clone or extracted release can be checked without changing system files:

```bash
./smoke-test.sh
```

The installer runs the same package-integrity preflight automatically before it backs up or replaces desktop files.

## Diagnostics

After installation:

```bash
./doctor.sh
```

The installed copy also keeps the maintenance helpers under `~/.local/share/yakushi-control-deck/`, so diagnostics and SDDM recovery remain available even if the original clone is removed.

## Update

```bash
./update.sh
```

## Restore your pre-install desktop files

```bash
./restore-last-install.sh
```

This restores the Waybar/Rofi/shared-color/Kitty/Fastfetch files backed up immediately before the most recent install.

## Uninstall

```bash
./uninstall.sh
```

Uninstall intentionally leaves the active desktop configs in place. Pre-install backups remain available.

## Wallpaper sources

The wallpaper page indexes both `~/Documents` and `~/Pictures`; `~/Documents` is selected by default and root filters include nested subfolders. The public installer includes `hyprpaper`; Yakushi starts it on demand if it is installed but not yet running. `swww` and `awww` are also supported when already present.

## Packages

When missing, the installer installs these from official Arch repositories: Python, PyGObject, GTK4, GdkPixbuf, Hyprland, Waybar, Rofi, Kitty, **Fastfetch**, hyprpaper, hyprlock, pavucontrol, playerctl, brightnessctl, wl-clipboard, JetBrains Mono Nerd Font and Polkit.

## Troubleshooting

- Run `./doctor.sh` first.
- Display errors: `/tmp/yakushi-display-error.log`
- Mouse errors: `/tmp/yakushi-mouse-error.log`
- Waybar log: `/tmp/yakushi-waybar.log`
- hyprpaper log: `/tmp/yakushi-hyprpaper.log`

## v1.2.12 stability polish

- Installed diagnostics now automatically use installed-layout smoke testing, avoiding false package-integrity failures after a normal install.
- Release archives are cleaned of Python bytecode/cache files.
- The README and release bundle now include the current desktop and Control Deck showcase screenshots.
- Fastfetch startup documentation now matches the vendor-safe `fish_greeting` override used by v1.2.11+.

## License

MIT


### Rofi transparency

Rofi opacity is stored in `~/.config/rofi/yakushi-opacity.rasi` and imported last, so earlier theme rules cannot shadow the slider.


## Lock & Login

Yakushi 1.1 adds two session pages:

- **Lock Screen** manages a generated Hyprlock configuration with wallpaper, blur, backdrop brightness, 12/24-hour clock, and date visibility.
- **Login Screen** ships a real Qt6 `yakushi` SDDM theme. Its layout intentionally mirrors Hyprlock and synchronizes the Lock Screen wallpaper, clock/date preference, darkness/blur intent, Theme Studio palette, and desktop typography when staged.
- **PREVIEW SDDM** uses SDDM test mode without ending the current session.
- **INSTALL / UPDATE SDDM** opens a visible Kitty terminal and uses normal `sudo` authentication. This avoids invisible Polkit prompts on minimal Hyprland sessions. The installer copies the theme to `/usr/share/sddm/themes/yakushi`, activates it, and verifies both the theme files and active configuration.
- **DISABLE YAKUSHI SDDM** restores the previous `/etc/sddm.conf` theme selection when Yakushi had to patch it.

SDDM remains the real boot login manager; Hyprlock remains the in-session lock screen. SDDM is optional and Yakushi does not replace a different display manager automatically.

### Optional Super+M lock shortcut

To make `Super+M` lock the current Hyprland session with Hyprlock instead of logging out:

```fish
./bind-super-m-lock.fish
```

The helper supports both modern Hyprland Lua config and legacy `hyprland.conf`, creates a timestamped backup, reloads Hyprland, checks for new config errors, and verifies the resulting `Yakushi Lock Screen` bind. Logout remains available from the Rofi power menu.

### SDDM terminal install / recovery

SDDM changes always use a visible terminal + `sudo` flow. You can also run the installer directly:

```bash
./install-sddm-theme.sh
```

Enter your normal Linux `sudo` password. The script refuses to report success unless `/usr/share/sddm/themes/yakushi/Main.qml` exists and SDDM resolves `Current=yakushi`. Log out normally or reboot afterward; do not restart SDDM from inside an active Hyprland session.
## Auto Color Theme

Theme Studio now includes **Auto Color Theme**. It samples the current wallpaper without an AUR helper or external color generator and builds all nine Yakushi tonal roles (accent, background, surfaces, foreground, muted text, border, hover and selected text).

- **DARK** creates deep wallpaper-tinted surfaces with a readable accent/foreground pair.
- **LIGHT** creates a paper-like palette with dark text and wallpaper-derived accents.
- **FOLLOW WALLPAPER** automatically regenerates the palette whenever a wallpaper is applied from Yakushi's Wallpaper page.
- `GENERATE + APPLY NOW` is available for one-shot recoloring without enabling follow mode.
- Rofi's separately configured opacity is preserved while its RGB background follows the new palette.
- Kitty automatically follows Auto Color and Theme Studio whenever Terminal Studio is set to **FOLLOW YAKUSHI THEME**.
- Auto Color requests the matching GNOME/libadwaita dark/light preference when the schema is available, which helps Nautilus match the chosen mode.

Auto Color follows wallpapers applied through Yakushi. External wallpaper daemons that change images without updating Yakushi state are intentionally not polled in the background.

## Nautilus Studio

The **03 // APPS & KEYS → Nautilus** page adds a 30–100% opacity slider. Yakushi does not patch Nautilus or libadwaita CSS; it writes one clearly marked Hyprland window rule instead. This makes the feature independent of Nautilus theme internals and keeps it reversible.

- Modern Hyprland uses a named `hl.window_rule(...)` Lua rule.
- Legacy Hyprland uses a managed `windowrulev2` block.
- The main Hyprland config is backed up before changes.
- A new config error triggers an automatic rollback.
- Setting opacity to **100%** removes the managed rule.
- Nautilus itself remains optional; Yakushi does not install it automatically just to expose this integration.
## Terminal Color Studio

The **03 // APPS & KEYS → Terminal** page can now control Kitty colors as well as font size, padding and opacity.

- **FOLLOW YAKUSHI THEME** uses the current desktop background, foreground and accent and keeps Kitty synchronized when Theme Studio or Auto Color changes the palette.
- **CUSTOM** lets the user choose independent Background, Foreground and Accent colors.
- Accent also generates a matching 16-color ANSI palette so prompts and colored CLI output follow the selected terminal tone.
- Yakushi writes generated colors to `~/.config/kitty/yakushi-colors.conf` and keeps that include **last** in `kitty.conf`, so `current-theme.conf` or another earlier include cannot silently override the selected palette.
- Applying Terminal colors requests a Kitty config reload, so existing Kitty windows can update immediately when Kitty allows it.
- Fresh installs start in FOLLOW mode, while existing Kitty configs remain opt-in until the user applies Terminal Colors.

Kitty opacity stays independent from color mode, so the liquid-glass transparency slider continues to work with either FOLLOW or CUSTOM colors.

## Fastfetch Studio

The **03 // APPS & KEYS → Fastfetch** page exposes both simple controls and the full Fastfetch JSONC config without requiring a separate editor.

- Toggle **Run Fastfetch in new terminals** on/off. On Fish, Yakushi owns a final user-level `fish_greeting` override so distro/vendor greetings such as CachyOS cannot create duplicate output. OFF means zero automatic Fastfetch runs; ON means exactly one. Package-owned files under `/usr/share` are never modified. Bash and Zsh use clearly marked managed startup blocks.
- Paste any ASCII art into the editor and press **SAVE ASCII + PREVIEW**. Yakushi stores it in `~/.config/fastfetch/logo.txt`, keeps the pasted source in `logo.txt`, generates a color-aware `yakushi-logo.txt`, and opens an immediate Kitty preview. The ASCII logo follows Terminal Studio accent color.
- Toggle common modules individually, including OS, Host, Kernel, Packages, Displays, **Window manager / Hyprland**, CPU, GPU, Memory, Disk, Battery, network information and more.
- Disabled custom module objects are remembered when possible, so re-enabling a module restores its custom key/format instead of replacing it with a generic entry.
- **FOLLOW TERMINAL ACCENT** maps Fastfetch key/title output to Kitty ANSI color1, which Yakushi Terminal Studio maps to the selected accent.
- **ADVANCED JSONC** provides the complete config for arbitrary Fastfetch changes. Yakushi validates JSONC and asks Fastfetch to load a lightweight candidate before replacing the real config.
- Existing Fastfetch config and logo files are preserved on install; Yakushi creates defaults only when they do not already exist.


### Window Frame & Shadow Studio

Appearance can control Hyprland active/inactive window border colors and drop shadows. Choose **FOLLOW YAKUSHI THEME** to synchronize with Theme Studio / Auto Color, or **CUSTOM** for independent colors. Shadow opacity, size, falloff, offset and scale are adjustable.

Fastfetch Studio also repairs a zero-length config automatically and includes **RESET SAFE DEFAULT** for recovery without deleting the user ASCII source.
