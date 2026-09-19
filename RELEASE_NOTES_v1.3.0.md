# Yakushi Control Deck v1.3.0

This release makes previews honest, gives Bar Studio explicit surface controls, and adds a guarded complete-removal path.

## Raycast and Waybar polish

- Raycast Glass again uses its original compact single-panel composition, fine border and highlight gradients. The temporary inset faux-shadow wrapper has been removed without losing live staging, search relevance tuning or Hyprland blur.
- The restored Raycast Glass style is the bundled install/update default.
- Waybar shadows now use a restrained two-layer falloff that remains inside the existing module margins, improving visible depth without bringing back clipped edges.

## Live before Apply

- Terminal geometry, opacity and colors update in the embedded preview.
- Rofi theme cards and every fine-tuning control update the launcher preview without writing `config.rasi`.
- Waybar geometry, module lanes, opacity, outline and shadow update in Bar Studio before restart or file changes.
- Lock Screen and Login Screen render the selected wallpaper, brightness, clock/date and an approximate blur preview.

## Waybar control

Bar Studio now exposes independent **Module outline** and **Module shadow** switches. Fresh installs and the Liquid Glass preset use outline off and shadow on. Module order and click actions remain unchanged, and all writes retain the existing validation and rollback path.

## Self Destruction

The final navigation section displays the exact removal plan and requires both an acknowledgement and the phrase `DESTROY YAKUSHI`. The enabled button opens a visible Kitty terminal, restores the first available pre-Yakushi desktop backup, removes marked Hyprland/shell blocks, purges the Yakushi SDDM theme, and deletes the application.

Only packages recorded as missing immediately before Yakushi installed them are eligible for `pacman -Rns`. Packages that predate Yakushi—or packages from a legacy installation whose provenance cannot be proven—are kept.
