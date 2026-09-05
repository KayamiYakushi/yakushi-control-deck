# Yakushi Control Deck v1.2.5

v1.2.5 fixes Kitty color precedence and introduces a complete Fastfetch Studio.

## Highlights

- Reliable Kitty color overrides through `yakushi-colors.conf` imported last.
- Immediate Kitty config reload after applying Terminal colors/settings when possible.
- New **Fastfetch Studio** page.
- Toggle Fastfetch auto-run in new Fish, Bash or Zsh terminals.
- Paste any ASCII art into the Control Deck and preview it instantly in Kitty.
- Toggle individual Fastfetch modules such as Window manager / Hyprland, Kernel, OS, CPU, GPU, Memory, Disk and more.
- Preserve custom module objects while disabling/re-enabling common modules.
- Make Fastfetch key/title colors follow the Terminal accent.
- Edit the complete Fastfetch JSONC configuration from Control Deck with validation and backups.
- Fresh installs include Fastfetch from the official Arch repositories without overwriting an existing Fastfetch config.

## Terminal color fix

Previous releases edited color properties directly in `kitty.conf`. A later `include current-theme.conf` or another theme include could override those values. v1.2.5 writes Yakushi colors to `~/.config/kitty/yakushi-colors.conf` and keeps that include last, matching Kitty's documented override behavior.

## Fastfetch workflow

Open `03 // APPS & KEYS → Fastfetch` to control startup, ASCII art, modules and advanced JSONC. `SAVE ASCII + PREVIEW` immediately opens the result in a dedicated Kitty preview window.
