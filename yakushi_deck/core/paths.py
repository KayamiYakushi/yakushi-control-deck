from pathlib import Path

HOME = Path.home()
CONFIG = HOME / ".config"

DATA = CONFIG / "yakushi-control-deck"
BACKUPS = DATA / "backups"
STATE = DATA / "state.json"
TYPOGRAPHY_STATE = DATA / "typography.json"
POWER_STATE = DATA / "governor"

HYPR_COLORS_CSS = CONFIG / "hypr" / "colors.css"
HYPR_COLORS_RASI = CONFIG / "hypr" / "colors.rasi"
WAYBAR_CONFIG = CONFIG / "waybar" / "config.jsonc"
WAYBAR_STYLE = CONFIG / "waybar" / "style.css"
ROFI_CONFIG = CONFIG / "rofi" / "config.rasi"
KITTY_CONFIG = CONFIG / "kitty" / "kitty.conf"
PICTURES = HOME / "Pictures"
DOCUMENTS = HOME / "Documents"
WALLPAPER_ROOTS = tuple(path for path in (PICTURES, DOCUMENTS) if path.exists())
GTK3_SETTINGS = CONFIG / "gtk-3.0" / "settings.ini"
GTK4_SETTINGS = CONFIG / "gtk-4.0" / "settings.ini"
