# Yakushi Control Deck v1.2.3

v1.2.3 fixes SDDM administrator authorization on minimal Hyprland sessions.

## Fixes

- `INSTALL / UPDATE SDDM` now opens a visible Kitty terminal and uses normal `sudo` authentication.
- No graphical Polkit agent is required for SDDM install/update or restore.
- The Control Deck does not wait for administrator input and remains responsive while the terminal handles authorization.
- Clearer status text explains where to enter the administrator password.

Enter the same Linux user password you normally use with `sudo` in the terminal window that Yakushi opens.
