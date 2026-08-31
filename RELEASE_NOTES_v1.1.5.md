# Yakushi Control Deck v1.1.5

This maintenance release focuses on making clean clones, extracted releases, and first-time installs safer and easier to verify.

## Highlights

- Fixed false `doctor.sh` failures for Waybar JSONC and bundled SDDM theme detection.
- Added a dependency-free JSONC validator for `//`, `/* ... */`, and trailing commas.
- Added `./smoke-test.sh` for non-destructive fresh-clone validation.
- `install.sh` now runs package-integrity checks before touching desktop configuration.
- Waybar validation now follows JSONC rules instead of strict JSON.
- Maintenance and recovery helpers are copied into the installed application directory.
- SDDM disable/restore now has the same visible terminal `sudo` fallback as SDDM installation when Polkit fails.

## Verification flow

```bash
./smoke-test.sh
./install.sh
./doctor.sh
```

`smoke-test.sh` does not modify system or user configuration files.
