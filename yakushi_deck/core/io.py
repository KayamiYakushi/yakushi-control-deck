from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from .paths import BACKUPS


def run(command: list[str], timeout: float = 5.0) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(command, 1, "", str(exc))


def backup(path: Path) -> Path | None:
    if not path.exists():
        return None

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    directory = BACKUPS / stamp
    directory.mkdir(parents=True, exist_ok=True)

    destination = directory / path.name
    shutil.copy2(path, destination)
    return destination


def restore(path: Path, source: Path | None) -> None:
    if source and source.exists():
        shutil.copy2(source, path)


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".yakushi-tmp")
    temp.write_text(content)
    temp.replace(path)


def load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return json.loads(json.dumps(default))

    try:
        value = json.loads(path.read_text())
        if isinstance(value, dict):
            return value
    except Exception:
        pass

    return json.loads(json.dumps(default))


def save_json(path: Path, value: dict) -> None:
    atomic_write(path, json.dumps(value, indent=2) + "\n")
