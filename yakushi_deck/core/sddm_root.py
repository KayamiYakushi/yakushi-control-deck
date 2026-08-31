#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from pathlib import Path

THEME_DST = Path("/usr/share/sddm/themes/yakushi")
CONF_DIR = Path("/etc/sddm.conf.d")
YAK_CONF = CONF_DIR / "90-yakushi-theme.conf"
LEGACY_CONF = Path("/etc/sddm.conf")
STATE_DIR = Path("/var/lib/yakushi-control-deck/sddm")
STATE_FILE = STATE_DIR / "original.json"
ORIGINAL_LEGACY = STATE_DIR / "original-sddm.conf"


def require_root():
    if os.geteuid() != 0:
        raise SystemExit("This helper must run as root.")


def patch_current(text: str, value: str) -> str:
    block = re.search(r"(?ms)^\s*\[Theme\]\s*(.*?)(?=^\s*\[|\Z)", text)
    if block:
        body = block.group(0)
        if re.search(r"(?m)^\s*Current\s*=", body):
            replaced = re.sub(r"(?m)^(\s*Current\s*=\s*).*$", rf"\g<1>{value}", body, count=1)
            return text[:block.start()] + replaced + text[block.end():]
        insert = block.end()
        return text[:insert] + f"Current={value}\n" + text[insert:]
    if text and not text.endswith("\n"):
        text += "\n"
    return text + f"\n[Theme]\nCurrent={value}\n"


def remember_original():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if STATE_FILE.exists():
        return
    legacy_existed = LEGACY_CONF.exists()
    if legacy_existed:
        shutil.copy2(LEGACY_CONF, ORIGINAL_LEGACY)
    STATE_FILE.write_text(json.dumps({"legacy_existed": legacy_existed}, indent=2) + "\n")


def install(source: Path):
    source = source.resolve()
    if not source.exists() or not (source / "Main.qml").exists():
        raise SystemExit("Invalid Yakushi SDDM theme source.")

    remember_original()
    if THEME_DST.exists():
        shutil.rmtree(THEME_DST)
    shutil.copytree(source, THEME_DST)

    # Never install the SDDM test-preview flag into the real greeter.
    user_conf = THEME_DST / "theme.conf.user"
    if user_conf.exists():
        text = user_conf.read_text(errors="ignore")
        if re.search(r"(?m)^previewMode=", text):
            text = re.sub(r"(?m)^previewMode=.*$", "previewMode=false", text, count=1)
        else:
            if text and not text.endswith("\n"):
                text += "\n"
            text += "previewMode=false\n"
        user_conf.write_text(text)

    for path in THEME_DST.rglob("*"):
        try:
            path.chmod(0o755 if path.is_dir() else 0o644)
        except OSError:
            pass

    CONF_DIR.mkdir(parents=True, exist_ok=True)
    YAK_CONF.write_text("[Theme]\nCurrent=yakushi\n")

    # /etc/sddm.conf has highest precedence. Preserve it once and patch only
    # the Current key so the theme reliably becomes active.
    if LEGACY_CONF.exists():
        text = LEGACY_CONF.read_text(errors="ignore")
        LEGACY_CONF.write_text(patch_current(text, "yakushi"))


def disable():
    state = {}
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text())
        except Exception:
            state = {}

    if state.get("legacy_existed") and ORIGINAL_LEGACY.exists():
        shutil.copy2(ORIGINAL_LEGACY, LEGACY_CONF)

    YAK_CONF.unlink(missing_ok=True)
    if STATE_DIR.exists():
        shutil.rmtree(STATE_DIR)


def main():
    require_root()
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    install_parser = sub.add_parser("install")
    install_parser.add_argument("--source", required=True)
    sub.add_parser("disable")
    args = parser.parse_args()
    if args.command == "install":
        install(Path(args.source))
    else:
        disable()


if __name__ == "__main__":
    main()
