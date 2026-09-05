## Yakushi Control Deck v1.2.12

A final v1.2.x stability and presentation release.

### Fixes

- Fixed a false package-integrity failure when `doctor.sh` is run from the installed application directory.
- Diagnostics now automatically distinguish source/release layouts from installed layouts.
- Release smoke testing rejects accidental Python `__pycache__` / `.pyc` files.
- Installed copies now keep the screenshot assets referenced by the bundled README.
- Updated Fastfetch documentation to match the vendor-safe single `fish_greeting` override used for CachyOS and similar Fish setups.

### Showcase

The repository now includes the current Yakushi desktop and Control Deck screenshots under `screenshots/` and displays both near the top of the README.

### Current feature set

- Waybar + Rofi integration
- Wallpaper Studio + Auto Color (Dark / Light)
- Theme Studio and typography controls
- Displays, keyboard, mouse and power controls
- Kitty Terminal Color Studio
- Fastfetch Studio with ASCII editing, module toggles, startup control and logo positioning
- Nautilus opacity
- Hyprlock Lock Screen Studio
- Yakushi SDDM Login Screen
- Window frame + shadow controls
- Backup / restore / diagnostics / smoke testing

### Installation

```bash
git clone https://github.com/KayamiYakushi/yakushi-control-deck.git
cd yakushi-control-deck
./install.sh
```

For Arch Linux + Hyprland. Official Arch repositories only.
