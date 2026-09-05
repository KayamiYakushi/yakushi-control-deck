# Yakushi Control Deck v1.2.4

v1.2.4 adds complete Kitty color management to Terminal Studio.

## New

- **FOLLOW YAKUSHI THEME** terminal color mode.
- **CUSTOM** terminal background, foreground and accent color pickers.
- Live terminal palette preview inside Control Deck.
- Theme-aware ANSI 16-color generation for Fastfetch, prompts and CLI color output.
- Automatic Kitty recoloring when Theme Studio or Auto Color changes the desktop palette while FOLLOW mode is active.

## Safety

- Existing Kitty configs remain opt-in: installing/upgrading does not overwrite a user's current terminal colors.
- Yakushi edits only managed Kitty color keys and preserves unrelated settings.
- Fresh installs with no Kitty config start with the default Yakushi palette in FOLLOW mode.

Opacity, font size and window padding remain independently adjustable.
