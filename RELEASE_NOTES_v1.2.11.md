## Yakushi Control Deck v1.2.11

This hotfix makes Fastfetch startup control reliable on CachyOS and other Fish configurations that provide a vendor `fish_greeting`.

### Fixes

- Fastfetch OFF now produces a genuinely blank new Fish terminal.
- Fastfetch ON produces exactly one Fastfetch output.
- Vendor/package-owned Fish config files are never modified.
- Yakushi writes a final reversible `fish_greeting` override to the user's `~/.config/fish/config.fish`.

For Arch Linux / CachyOS + Hyprland.
