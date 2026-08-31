# 薬 Yakushi Control Deck

A lightweight GTK4 control deck and matching Waybar/Rofi setup for **Arch Linux + Hyprland**.

![Yakushi Control Deck](screenshots/control-deck.png)

## Highlights

- No shell replacement, Electron, Node, AUR, or `yay` requirement.
- Display layout, refresh rate, scale and position controls.
- Keyboard and mouse controls with live Hyprland verification.
- Balanced / Performance power management.
- Tonal Theme Studio, desktop typography, wallpapers, Kitty and Rofi appearance.
- Waybar drag-and-drop module ordering and enable/disable controls.
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

The installer uses official Arch repositories only. Existing Waybar, Rofi, shared color and Kitty files are backed up under:

```text
~/.config/yakushi-control-deck/install-backups/<timestamp>/
```

Launch with:

```bash
yakushi-deck
```

If your shell does not include `~/.local/bin` in `PATH`, use `~/.local/bin/yakushi-deck`. The bundled Waybar uses the absolute path and is unaffected.

## Diagnostics

```bash
./doctor.sh
```

## Update

```bash
./update.sh
```

## Restore your pre-install desktop files

```bash
./restore-last-install.sh
```

This restores the Waybar/Rofi/shared-color/Kitty files backed up immediately before the most recent install.

## Uninstall

```bash
./uninstall.sh
```

Uninstall intentionally leaves the active desktop configs in place. Pre-install backups remain available.

## Wallpaper sources

The wallpaper page indexes both `~/Pictures` and `~/Documents`. The public installer includes `hyprpaper`; Yakushi starts it on demand if it is installed but not yet running. `swww` and `awww` are also supported when already present.

## Packages

When missing, the installer installs these from official Arch repositories: Python, PyGObject, GTK4, Hyprland, Waybar, Rofi, Kitty, hyprpaper, hyprlock, pavucontrol, playerctl, brightnessctl, wl-clipboard, JetBrains Mono Nerd Font and Polkit.

## Troubleshooting

- Run `./doctor.sh` first.
- Display errors: `/tmp/yakushi-display-error.log`
- Mouse errors: `/tmp/yakushi-mouse-error.log`
- Waybar log: `/tmp/yakushi-waybar.log`
- hyprpaper log: `/tmp/yakushi-hyprpaper.log`

## License

MIT
