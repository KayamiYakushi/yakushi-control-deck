from pathlib import Path

HOME = Path.home()
CONFIG = HOME / ".config"

DATA = CONFIG / "yakushi-control-deck"
BACKUPS = DATA / "backups"
STATE = DATA / "state.json"
TYPOGRAPHY_STATE = DATA / "typography.json"
POWER_STATE = DATA / "governor"
AUTO_COLOR_STATE = DATA / "auto-color.json"
NAUTILUS_STATE = DATA / "nautilus.json"
WINDOW_FRAME_STATE = DATA / "window-frame.json"

HYPR_COLORS_CSS = CONFIG / "hypr" / "colors.css"
HYPR_COLORS_RASI = CONFIG / "hypr" / "colors.rasi"
WAYBAR_CONFIG = CONFIG / "waybar" / "config.jsonc"
WAYBAR_STYLE = CONFIG / "waybar" / "style.css"
ROFI_CONFIG = CONFIG / "rofi" / "config.rasi"
ROFI_OPACITY_OVERRIDE = CONFIG / "rofi" / "yakushi-opacity.rasi"
KITTY_CONFIG = CONFIG / "kitty" / "kitty.conf"
KITTY_COLOR_OVERRIDE = CONFIG / "kitty" / "yakushi-colors.conf"
FASTFETCH_CONFIG = CONFIG / "fastfetch" / "config.jsonc"
FASTFETCH_LOGO = CONFIG / "fastfetch" / "logo.txt"
FASTFETCH_RENDERED_LOGO = CONFIG / "fastfetch" / "yakushi-logo.txt"
FASTFETCH_STATE = DATA / "fastfetch.json"
FISH_FASTFETCH_HOOK = CONFIG / "fish" / "conf.d" / "yakushi-fastfetch.fish"
FISH_FASTFETCH_GREETING = CONFIG / "fish" / "functions" / "fish_greeting.fish"
PICTURES = HOME / "Pictures"
DOCUMENTS = HOME / "Documents"
WALLPAPER_ROOTS = tuple(path for path in (PICTURES, DOCUMENTS) if path.exists())
GTK3_SETTINGS = CONFIG / "gtk-3.0" / "settings.ini"
GTK4_SETTINGS = CONFIG / "gtk-4.0" / "settings.ini"

LOCK_STATE = DATA / "lockscreen.json"
SDDM_STATE = DATA / "sddm.json"
HYPRLOCK_CONFIG = CONFIG / "hypr" / "hyprlock.conf"
SDDM_PREVIEW = DATA / "sddm-preview"
