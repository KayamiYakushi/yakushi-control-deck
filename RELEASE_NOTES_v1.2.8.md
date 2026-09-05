# Yakushi Control Deck v1.2.8

Fastfetch startup and ASCII placement polish.

## Fixed

- Fastfetch startup OFF now catches Fish `fish_greeting.fish` autorun setups in addition to `config.fish` and `conf.d`.
- Common Fish startup calls are disabled reversibly, so manual `fastfetch` remains available while new terminals can open blank.
- Re-enabling autorun restores Yakushi-disabled startup calls.

## Added

- Horizontal ASCII logo offset.
- Vertical ASCII logo offset.
- Apply position + instant Kitty preview.
- Logo padding is preserved when ASCII art or terminal accent settings are updated.
