from __future__ import annotations

import shlex
import shutil
import time
from pathlib import Path

from .io import load_json, run, save_json
from .paths import DOCUMENTS, PICTURES, STATE, WALLPAPER_ROOTS

EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".avif", ".jxl"}


def roots() -> list[Path]:
    values = [path for path in WALLPAPER_ROOTS if path.exists()]
    return values or [path for path in (PICTURES, DOCUMENTS) if path.exists()]


def _all_images(limit: int = 500) -> list[Path]:
    images, seen = [], set()
    for base in roots():
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in EXTENSIONS and path not in seen:
                seen.add(path)
                images.append(path)
    def mtime(path: Path):
        try: return path.stat().st_mtime
        except OSError: return 0
    images.sort(key=mtime, reverse=True)
    return images[:limit]


def folder_label(path: Path) -> str:
    for base in roots():
        try:
            rel = path.relative_to(base)
            return base.name if str(rel) == "." else f"{base.name}/{rel}"
        except ValueError:
            pass
    return str(path)


def scan(limit: int = 500, folder: str | None = None) -> list[Path]:
    images = _all_images(limit)
    if not folder or folder in {"All", "Pictures & Documents"}:
        return images
    return [path for path in images if folder_label(path.parent) == folder]


def folders() -> list[str]:
    found = {folder_label(path.parent) for path in _all_images()}
    return sorted(found, key=lambda value: (0 if value in {"Pictures", "Documents"} else 1, value.lower()))


def recent(limit: int = 16) -> list[Path]:
    data = load_json(STATE, {})
    result = []
    for item in data.get("wallpaper_recent", []):
        path = Path(item)
        if path.exists() and path.suffix.lower() in EXTENSIONS:
            result.append(path)
        if len(result) >= limit: break
    return result


def current() -> Path | None:
    value = load_json(STATE, {}).get("wallpaper_current")
    if not value: return None
    path = Path(value)
    return path if path.exists() else None


def _remember(path: Path) -> None:
    data = load_json(STATE, {})
    existing = [item for item in data.get("wallpaper_recent", []) if item != str(path)]
    data["wallpaper_recent"] = [str(path), *existing][:24]
    data["wallpaper_current"] = str(path)
    save_json(STATE, data)


def _hyprpaper(path: Path):
    quoted = shlex.quote(str(path))
    cmd = f"hyprctl hyprpaper preload {quoted} && hyprctl hyprpaper wallpaper ',{quoted}'"
    proc = run(["sh", "-lc", cmd], timeout=8.0)
    if proc.returncode == 0: return proc
    run(["sh", "-lc", "nohup hyprpaper >/tmp/yakushi-hyprpaper.log 2>&1 &"], timeout=2.0)
    time.sleep(0.4)
    return run(["sh", "-lc", cmd], timeout=8.0)


def apply(path: Path) -> tuple[bool, str]:
    if not path.exists(): return False, "Wallpaper file no longer exists."
    if shutil.which("awww"):
        proc = run(["awww", "img", str(path)], timeout=8.0)
    elif shutil.which("swww"):
        proc = run(["swww", "img", str(path)], timeout=8.0)
    elif shutil.which("hyprpaper"):
        proc = _hyprpaper(path)
    else:
        return False, "No supported wallpaper backend was detected (hyprpaper, swww, or awww)."
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout).strip() or "Wallpaper backend failed."
    _remember(path)
    return True, "Wallpaper applied."
