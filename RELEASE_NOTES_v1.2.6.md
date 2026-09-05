# Yakushi Control Deck v1.2.6

v1.2.6 fixes the two remaining live-application issues in Terminal Studio and Fastfetch Studio.

## Fixes

- Terminal colors are now written as a concrete final managed block in the active Kitty config, preventing older theme includes from overriding them.
- Running Kitty config detection supports standard config paths, `KITTY_CONFIG_DIRECTORY`, and explicit `--config` launches.
- Kitty state parsing mirrors Kitty's last-assignment-wins behavior.
- Fastfetch module toggles now verify the transformed config before and after writing.
- Unusual JSONC layouts fall back to a canonical JSON rewrite while preserving parsed Fastfetch settings.
- Applying Fastfetch modules immediately opens a fresh preview so changes such as disabling Uptime are visible at once.
- Yakushi-managed Fish Fastfetch autorun explicitly loads the managed config path.

## Notes

ASCII art editing introduced in v1.2.5 remains unchanged.
