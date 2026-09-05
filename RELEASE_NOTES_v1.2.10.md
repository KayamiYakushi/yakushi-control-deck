# Yakushi Control Deck v1.2.10

Fastfetch startup ownership fix.

- Fish autorun now has exact semantics: OFF = zero startup Fastfetch runs, ON = exactly one.
- Legacy Fastfetch calls in Fish startup files are normalized instead of restored alongside Yakushi's own hook.
- Yakushi follows simple `source` chains from Fish startup files, so dotfiles-backed startup scripts are handled too.
- `fish_greeting` is managed explicitly while Fastfetch startup control is active, preventing system/plugin greetings from adding a second Fastfetch run.
- Existing `fish_greeting` state is preserved in Yakushi state before first takeover.
- Startup application performs a probe when Fish is available and reports the observed Fastfetch invocation count.
