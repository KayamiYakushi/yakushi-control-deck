from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .history import record
from .io import atomic_write, load_json, save_json
from .paths import (
    DATA,
    FASTFETCH_CONFIG,
    FASTFETCH_LOGO,
    FASTFETCH_RENDERED_LOGO,
    FASTFETCH_STATE,
    FISH_FASTFETCH_HOOK,
    FISH_FASTFETCH_GREETING,
)


DEFAULT_MODULES = [
    "title",
    "separator",
    {"type": "os", "key": "󰣇 "},
    {"type": "host", "key": "󰌢 "},
    {"type": "kernel", "key": "󰒋 "},
    {"type": "uptime", "key": "󰅐 "},
    {"type": "packages", "key": "󰏖 "},
    {"type": "shell", "key": "󰆍 "},
    {"type": "display", "key": "󰍹 "},
    {"type": "wm", "key": "󰖲 "},
    {"type": "terminal", "key": " "},
    {"type": "cpu", "key": "󰻠 "},
    {"type": "gpu", "key": "󰢮 "},
    {"type": "memory", "key": "󰍛 "},
    {"type": "disk", "key": "󰋊 "},
    "break",
    "colors",
]

COMMON_MODULES = [
    ("title", "Title"),
    ("separator", "Separator"),
    ("os", "Operating system"),
    ("host", "Machine / host"),
    ("kernel", "Kernel"),
    ("uptime", "Uptime"),
    ("packages", "Packages"),
    ("shell", "Shell"),
    ("display", "Displays"),
    ("de", "Desktop environment"),
    ("wm", "Window manager / Hyprland"),
    ("wmtheme", "WM theme"),
    ("theme", "GTK theme"),
    ("icons", "Icons"),
    ("font", "Fonts"),
    ("cursor", "Cursor"),
    ("terminal", "Terminal"),
    ("terminalfont", "Terminal font"),
    ("cpu", "CPU"),
    ("cpuusage", "CPU usage"),
    ("gpu", "GPU"),
    ("memory", "Memory"),
    ("swap", "Swap"),
    ("disk", "Disk"),
    ("battery", "Battery"),
    ("localip", "Local IP"),
    ("publicip", "Public IP"),
    ("locale", "Locale"),
    ("break", "Blank line"),
    ("colors", "Color palette"),
]

DEFAULT_LOGO = r"""     薬
   YAKUSHI
"""

DEFAULT_CONFIG = {
    "$schema": "https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json",
    "logo": {
        "type": "file",
        "source": "~/.config/fastfetch/yakushi-logo.txt",
        "color": {"1": "red"},
        "padding": {"top": 0, "left": 0, "right": 3},
    },
    "display": {"separator": "  -> "},
    "modules": DEFAULT_MODULES,
}

FISH_CONFIG = Path.home() / ".config" / "fish" / "config.fish"
FISH_OVERRIDE_BEGIN = "# >>> YAKUSHI FASTFETCH OVERRIDE >>>"
FISH_OVERRIDE_END = "# <<< YAKUSHI FASTFETCH OVERRIDE <<<"


@dataclass
class FastfetchState:
    available: bool
    auto_run: bool
    logo: str
    config_text: str
    modules: dict[str, bool]
    shell: str
    external_autorun: bool = False
    logo_padding_left: int = 0
    logo_padding_top: int = 0
    logo_padding_right: int = 3


def _write_preserving_symlink(path: Path, content: str) -> None:
    target = path.resolve() if path.is_symlink() else path
    atomic_write(target, content)


def _strip_jsonc(text: str) -> str:
    """Convert JSONC to JSON without touching strings."""
    out: list[str] = []
    i = 0
    in_string = False
    escaped = False
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if in_string:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        if ch == "/" and nxt == "/":
            while i < len(text) and text[i] != "\n":
                i += 1
            if i < len(text):
                out.append("\n")
                i += 1
            continue
        if ch == "/" and nxt == "*":
            i += 2
            while i + 1 < len(text) and not (text[i] == "*" and text[i + 1] == "/"):
                out.append("\n" if text[i] == "\n" else " ")
                i += 1
            i = min(i + 2, len(text))
            continue
        out.append(ch)
        i += 1

    # Remove trailing commas outside strings.
    raw = "".join(out)
    out = []
    i = 0
    in_string = False
    escaped = False
    while i < len(raw):
        ch = raw[i]
        if in_string:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        if ch == ",":
            j = i + 1
            while j < len(raw) and raw[j].isspace():
                j += 1
            if j < len(raw) and raw[j] in "}]":
                i += 1
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def parse_config(text: str) -> dict:
    value = json.loads(_strip_jsonc(text or "{}"))
    if not isinstance(value, dict):
        raise ValueError("Fastfetch config root must be a JSON object.")
    return value


def _default_config_text() -> str:
    return json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False) + "\n"


def ensure_config() -> None:
    FASTFETCH_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    needs_default = not FASTFETCH_CONFIG.exists()
    if FASTFETCH_CONFIG.exists():
        try:
            needs_default = not FASTFETCH_CONFIG.read_text(encoding="utf-8").strip()
        except Exception:
            needs_default = False
    if needs_default:
        if FASTFETCH_CONFIG.exists():
            record("Repair empty Fastfetch config", files=[FASTFETCH_CONFIG])
        _write_preserving_symlink(FASTFETCH_CONFIG, _default_config_text())
    if not FASTFETCH_LOGO.exists():
        _write_preserving_symlink(FASTFETCH_LOGO, DEFAULT_LOGO)
    if not FASTFETCH_RENDERED_LOGO.exists():
        _write_rendered_logo(_read_logo())


def reset_config() -> tuple[bool, str]:
    """Restore a valid Yakushi baseline without deleting the user's ASCII source."""
    FASTFETCH_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    if FASTFETCH_CONFIG.exists():
        record("Reset Fastfetch config", files=[FASTFETCH_CONFIG])
    _write_preserving_symlink(FASTFETCH_CONFIG, _default_config_text())
    if not FASTFETCH_LOGO.exists():
        _write_preserving_symlink(FASTFETCH_LOGO, DEFAULT_LOGO)
    _write_rendered_logo(_read_logo())
    return True, "Fastfetch config restored to a safe Yakushi baseline. Your ASCII source was preserved."


def _read_config_text() -> str:
    if FASTFETCH_CONFIG.exists():
        try:
            return FASTFETCH_CONFIG.read_text(encoding="utf-8")
        except Exception:
            pass
    return _default_config_text()


def _read_logo() -> str:
    if FASTFETCH_LOGO.exists():
        try:
            return FASTFETCH_LOGO.read_text(encoding="utf-8")
        except Exception:
            pass
    return DEFAULT_LOGO


def _render_logo_text(text: str) -> str:
    """Generate Fastfetch's color-aware render copy from plain pasted ASCII."""
    lines = text.rstrip("\n").splitlines() or [""]
    rendered: list[str] = []
    for line in lines:
        # Fastfetch uses $$ for a literal dollar and $1 for logo color slot 1.
        rendered.append("$1" + line.replace("$", "$$"))
    return "\n".join(rendered) + "\n"


def _write_rendered_logo(text: str) -> None:
    FASTFETCH_RENDERED_LOGO.parent.mkdir(parents=True, exist_ok=True)
    _write_preserving_symlink(FASTFETCH_RENDERED_LOGO, _render_logo_text(text))


def _logo_padding(text: str | None = None) -> dict[str, int]:
    source = _read_config_text() if text is None else text
    values = {"top": 0, "left": 0, "right": 3}
    try:
        logo = parse_config(source).get("logo")
        padding = logo.get("padding") if isinstance(logo, dict) else None
        if isinstance(padding, dict):
            for key in values:
                raw = padding.get(key, values[key])
                if isinstance(raw, bool):
                    continue
                try:
                    values[key] = max(0, min(64, int(raw)))
                except (TypeError, ValueError):
                    pass
    except Exception:
        pass
    return values


def _yakushi_logo_config(text: str | None = None) -> dict:
    return {
        "type": "file",
        "source": "~/.config/fastfetch/yakushi-logo.txt",
        "color": {"1": "red"},
        "padding": _logo_padding(text),
    }


def _module_type(entry) -> str:
    if isinstance(entry, str):
        return entry.strip().lower()
    if isinstance(entry, dict):
        return str(entry.get("type", "")).strip().lower()
    return ""


def _modules_from_text(text: str) -> list:
    try:
        value = parse_config(text).get("modules", DEFAULT_MODULES)
        return list(value) if isinstance(value, list) else list(DEFAULT_MODULES)
    except Exception:
        return list(DEFAULT_MODULES)


def _module_status(text: str) -> dict[str, bool]:
    active = {_module_type(item) for item in _modules_from_text(text)}
    return {name: name in active for name, _label in COMMON_MODULES}


def _replace_top_level(text: str, key: str, value) -> str:
    """Replace one top-level JSONC value while preserving unrelated text/comments."""
    try:
        data = parse_config(text)
    except Exception:
        data = {}

    # Lightweight top-level scanner. It intentionally only recognizes quoted
    # keys in the root object, which is how Fastfetch JSONC is structured.
    i = 0
    length = len(text)

    def skip_ws_comments(pos: int) -> int:
        while pos < length:
            if text[pos].isspace():
                pos += 1
                continue
            if text.startswith("//", pos):
                end = text.find("\n", pos + 2)
                return length if end < 0 else skip_ws_comments(end + 1)
            if text.startswith("/*", pos):
                end = text.find("*/", pos + 2)
                return length if end < 0 else skip_ws_comments(end + 2)
            break
        return pos

    def string_end(pos: int) -> int:
        pos += 1
        escaped = False
        while pos < length:
            ch = text[pos]
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                return pos + 1
            pos += 1
        return length

    def value_end(pos: int) -> int:
        pos = skip_ws_comments(pos)
        if pos >= length:
            return pos
        if text[pos] == '"':
            return string_end(pos)
        if text[pos] in "[{":
            stack = [text[pos]]
            pos += 1
            in_string = False
            escaped = False
            while pos < length and stack:
                ch = text[pos]
                nxt = text[pos + 1] if pos + 1 < length else ""
                if in_string:
                    if escaped:
                        escaped = False
                    elif ch == "\\":
                        escaped = True
                    elif ch == '"':
                        in_string = False
                    pos += 1
                    continue
                if ch == '"':
                    in_string = True
                    pos += 1
                    continue
                if ch == "/" and nxt == "/":
                    end = text.find("\n", pos + 2)
                    pos = length if end < 0 else end + 1
                    continue
                if ch == "/" and nxt == "*":
                    end = text.find("*/", pos + 2)
                    pos = length if end < 0 else end + 2
                    continue
                if ch in "[{":
                    stack.append(ch)
                elif ch in "]}":
                    if stack:
                        stack.pop()
                pos += 1
            return pos
        while pos < length and text[pos] not in ",}\n":
            pos += 1
        return pos

    i = skip_ws_comments(i)
    if i < length and text[i] == "{":
        i += 1
        while i < length:
            i = skip_ws_comments(i)
            if i >= length or text[i] == "}":
                break
            if text[i] != '"':
                break
            end_key = string_end(i)
            try:
                found_key = json.loads(text[i:end_key])
            except Exception:
                break
            colon = skip_ws_comments(end_key)
            if colon >= length or text[colon] != ":":
                break
            start_value = skip_ws_comments(colon + 1)
            end_value = value_end(start_value)
            if found_key == key:
                line_start = text.rfind("\n", 0, i) + 1
                indent = re.match(r"\s*", text[line_start:i]).group(0)
                rendered = json.dumps(value, indent=2, ensure_ascii=False)
                rendered = rendered.replace("\n", "\n" + indent)
                return text[:start_value] + rendered + text[end_value:]
            i = skip_ws_comments(end_value)
            if i < length and text[i] == ",":
                i += 1
                continue
            if i < length and text[i] == "}":
                break

    data[key] = value
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _state() -> dict:
    return load_json(FASTFETCH_STATE, {"disabled_modules": {}})


def _save_state(value: dict) -> None:
    save_json(FASTFETCH_STATE, value)


def _shell_name() -> str:
    return Path(os.environ.get("SHELL", "")).name.lower() or "unknown"


def _expand_source_token(raw: str) -> Path | None:
    """Resolve a simple Fish `source` target used during shell startup."""
    token = raw.strip().rstrip(";")
    if not token:
        return None
    # Ignore dynamic command substitutions and variable-heavy expressions.
    if any(part in token for part in ("(", ")", "*", "?", "[", "]")):
        return None
    if (token.startswith('"') and token.endswith('"')) or (token.startswith("'") and token.endswith("'")):
        token = token[1:-1]
    token = token.replace("$HOME", str(Path.home())).replace("${HOME}", str(Path.home()))
    if "$" in token:
        return None
    path = Path(os.path.expanduser(token))
    return path if path.is_absolute() else None


def _simple_sourced_files(path: Path) -> list[Path]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    result: list[Path] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = re.match(r"^(?:source|\.)\s+(.+?)(?:\s*(?:;|$))", stripped)
        if not match:
            continue
        target = _expand_source_token(match.group(1))
        if target and target.exists() and target.is_file():
            result.append(target)
    return result


def _fish_autorun_files() -> list[Path]:
    """Files executed directly or sourced while an interactive Fish shell starts."""
    base = Path.home() / ".config" / "fish"
    seeds: list[Path] = [base / "config.fish"]
    confd = base / "conf.d"
    if confd.exists():
        seeds.extend(sorted(confd.glob("*.fish")))
    # fish_greeting is managed separately, but its pre-Yakushi source may still
    # contain a legacy Fastfetch call before the first migration.
    seeds.append(FISH_FASTFETCH_GREETING)

    seen: set[Path] = set()
    queue = [path for path in seeds if path.exists() and path != FISH_FASTFETCH_HOOK]
    result: list[Path] = []
    while queue:
        path = queue.pop(0)
        try:
            identity = path.resolve()
        except Exception:
            identity = path
        if identity in seen:
            continue
        seen.add(identity)
        result.append(path)
        for child in _simple_sourced_files(path):
            if child != FISH_FASTFETCH_HOOK:
                queue.append(child)
    return result


def _fish_fastfetch_startup_line(stripped: str) -> bool:
    if not stripped or stripped.startswith("#"):
        return False
    # Standalone calls, including arguments, redirection or a display pipe.
    if re.match(r"^(?:command\s+)?fastfetch(?:\s|$)", stripped):
        return True
    # Common one-line guards used in config.fish/conf.d. Commenting the whole
    # line is safe because its only visible action is Fastfetch.
    if re.search(r"(?:^|[;&]\s*)(?:command\s+)?fastfetch(?:\s|[;&]|$)", stripped):
        lowered = stripped.lower()
        return lowered.startswith(("if ", "status ", "type ", "command -", "test ", "and ", "or "))
    return False


def _has_fastfetch_startup_line(path: Path) -> bool:
    try:
        return any(_fish_fastfetch_startup_line(line.strip()) for line in path.read_text(encoding="utf-8").splitlines())
    except Exception:
        return False


def _managed_greeting_mode() -> str | None:
    if not FISH_FASTFETCH_GREETING.exists() or FISH_FASTFETCH_GREETING.is_symlink():
        return None
    try:
        text = FISH_FASTFETCH_GREETING.read_text(encoding="utf-8")
    except Exception:
        return None
    if "# >>> YAKUSHI FASTFETCH GREETING >>>" not in text:
        return None
    if "# YAKUSHI FASTFETCH MODE: on" in text:
        return "on"
    if "# YAKUSHI FASTFETCH MODE: off" in text:
        return "off"
    return None


def _fish_external_autorun() -> bool:
    # Once Yakushi owns the final config.fish override, vendor fish_greeting
    # definitions (for example CachyOS' /usr/share/cachyos-fish-config) are
    # intentionally shadowed and must not be reported as active duplicates.
    if _managed_config_mode() is not None:
        return False
    for path in _fish_autorun_files():
        if path == FISH_FASTFETCH_GREETING and _managed_greeting_mode() is not None:
            continue
        if _has_fastfetch_startup_line(path):
            return True
    return False


def _capture_original_fish_greeting() -> None:
    state = _state()
    autorun = state.setdefault("autorun", {})
    if autorun.get("fish_greeting_captured"):
        return
    greeting = FISH_FASTFETCH_GREETING
    autorun["fish_greeting_captured"] = True
    if greeting.is_symlink():
        autorun["fish_greeting_kind"] = "symlink"
        try:
            autorun["fish_greeting_target"] = os.readlink(greeting)
        except OSError:
            autorun["fish_greeting_target"] = ""
    elif greeting.exists():
        autorun["fish_greeting_kind"] = "file"
        try:
            autorun["fish_greeting_original"] = greeting.read_text(encoding="utf-8")
        except Exception:
            autorun["fish_greeting_original"] = ""
    else:
        autorun["fish_greeting_kind"] = "absent"
    _save_state(state)


def _disable_external_fish_fastfetch_calls() -> list[Path]:
    """Disable user-owned direct startup calls; never edit vendor/system files.

    Vendor configs may define fish_greeting with Fastfetch (CachyOS does this).
    Those definitions are safely shadowed by Yakushi's final config.fish override
    instead of modifying /usr/share or other package-owned files.
    """
    marker = "# YAKUSHI DISABLED FASTFETCH AUTORUN: "
    changed_paths: list[Path] = []
    user_fish = (Path.home() / ".config" / "fish").resolve()
    for path in _fish_autorun_files():
        if path in {FISH_FASTFETCH_HOOK, FISH_FASTFETCH_GREETING, FISH_CONFIG}:
            continue
        try:
            resolved = path.resolve()
            resolved.relative_to(user_fish)
        except Exception:
            # Package-owned/vendor source: leave untouched.
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        changed = False
        out: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(marker):
                out.append(line)
                continue
            if _fish_fastfetch_startup_line(stripped):
                indent = line[: len(line) - len(line.lstrip())]
                out.append(indent + marker + line.lstrip())
                changed = True
            else:
                out.append(line)
        if changed:
            _write_preserving_symlink(path, "\n".join(out) + "\n")
            changed_paths.append(path)
    return changed_paths


def _managed_config_mode() -> str | None:
    if not FISH_CONFIG.exists():
        return None
    try:
        text = FISH_CONFIG.read_text(encoding="utf-8")
    except Exception:
        return None
    if FISH_OVERRIDE_BEGIN not in text:
        return None
    if "# YAKUSHI FASTFETCH MODE: on" in text:
        return "on"
    if "# YAKUSHI FASTFETCH MODE: off" in text:
        return "off"
    return None


def _write_managed_fish_override(enabled: bool) -> None:
    """Write the final fish_greeting definition at the end of config.fish.

    This intentionally runs after distro/vendor config sources, so a packaged
    fish_greeting such as CachyOS' Fastfetch greeting is shadowed without
    touching the package-owned file.
    """
    FISH_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    text = FISH_CONFIG.read_text(encoding="utf-8") if FISH_CONFIG.exists() else ""
    # Match only Yakushi's own managed block.
    block_re = re.compile(
        rf"(?ms)^{re.escape(FISH_OVERRIDE_BEGIN)}\n.*?^{re.escape(FISH_OVERRIDE_END)}\n?"
    )
    text = block_re.sub("", text).rstrip()
    config_arg = shlex.quote(str(FASTFETCH_CONFIG))
    if enabled:
        body = (
            f"{FISH_OVERRIDE_BEGIN}\n"
            "# YAKUSHI FASTFETCH MODE: on\n"
            "function fish_greeting\n"
            "    if status is-interactive; and type -q fastfetch\n"
            f"        fastfetch --config {config_arg}\n"
            "    end\n"
            "end\n"
            f"{FISH_OVERRIDE_END}\n"
        )
    else:
        body = (
            f"{FISH_OVERRIDE_BEGIN}\n"
            "# YAKUSHI FASTFETCH MODE: off\n"
            "function fish_greeting\n"
            "end\n"
            f"{FISH_OVERRIDE_END}\n"
        )
    if text:
        text += "\n\n"
    atomic_write(FISH_CONFIG, text + body)


def _write_managed_fish_greeting(enabled: bool) -> None:
    _capture_original_fish_greeting()
    greeting = FISH_FASTFETCH_GREETING
    greeting.parent.mkdir(parents=True, exist_ok=True)
    # Replacing a user symlink with a regular override leaves the symlink target
    # untouched; its target is recorded in Fastfetch state for future restore.
    if greeting.is_symlink():
        greeting.unlink()
    config_arg = shlex.quote(str(FASTFETCH_CONFIG))
    if enabled:
        body = (
            "# >>> YAKUSHI FASTFETCH GREETING >>>\n"
            "# YAKUSHI FASTFETCH MODE: on\n"
            "function fish_greeting\n"
            "    if status is-interactive; and type -q fastfetch\n"
            f"        fastfetch --config {config_arg}\n"
            "    end\n"
            "end\n"
            "# <<< YAKUSHI FASTFETCH GREETING <<<\n"
        )
    else:
        body = (
            "# >>> YAKUSHI FASTFETCH GREETING >>>\n"
            "# YAKUSHI FASTFETCH MODE: off\n"
            "function fish_greeting\n"
            "end\n"
            "# <<< YAKUSHI FASTFETCH GREETING <<<\n"
        )
    atomic_write(greeting, body)


def _probe_fish_fastfetch_count() -> int | None:
    """Count startup Fastfetch invocations without running the real program."""
    fish = shutil.which("fish")
    if not fish:
        return None
    import tempfile
    with tempfile.TemporaryDirectory(prefix="yakushi-fastfetch-probe-") as tmp:
        root = Path(tmp)
        counter = root / "count"
        fake = root / "fastfetch"
        fake.write_text(
            "#!/bin/sh\nprintf x >> \"$YAKUSHI_FASTFETCH_PROBE\"\nexit 0\n",
            encoding="utf-8",
        )
        fake.chmod(0o755)
        env = os.environ.copy()
        env["PATH"] = str(root) + os.pathsep + env.get("PATH", "")
        env["YAKUSHI_FASTFETCH_PROBE"] = str(counter)
        env.setdefault("TERM", "xterm-256color")
        try:
            subprocess.run(
                [fish, "-i", "-c", "exit"],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=6,
                check=False,
            )
        except Exception:
            return None
        try:
            return len(counter.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return 0


def _managed_autorun_enabled(shell: str) -> bool:
    if shell == "fish":
        mode = _managed_config_mode()
        if mode is not None:
            return mode == "on"
        return _managed_greeting_mode() == "on"
    if shell in {"bash", "zsh"}:
        rc = Path.home() / (".bashrc" if shell == "bash" else ".zshrc")
        if not rc.exists():
            return False
        try:
            return "# >>> YAKUSHI FASTFETCH AUTORUN >>>" in rc.read_text(encoding="utf-8")
        except Exception:
            return False
    return False


def load() -> FastfetchState:
    ensure_config()
    text = _read_config_text()
    shell = _shell_name()
    external = shell == "fish" and _fish_external_autorun()
    padding = _logo_padding(text)
    return FastfetchState(
        available=shutil.which("fastfetch") is not None,
        auto_run=_managed_autorun_enabled(shell) if shell == "fish" else _managed_autorun_enabled(shell),
        logo=_read_logo(),
        config_text=text,
        modules=_module_status(text),
        shell=shell,
        external_autorun=external,
        logo_padding_left=padding["left"],
        logo_padding_top=padding["top"],
        logo_padding_right=padding["right"],
    )


def set_autorun(enabled: bool) -> tuple[bool, str]:
    shell = _shell_name()

    if shell == "fish":
        touched = [FISH_CONFIG, FISH_FASTFETCH_HOOK, FISH_FASTFETCH_GREETING, *_fish_autorun_files()]
        record("Fastfetch shell autorun", files=touched)

        # Do not modify distro/package-owned Fish files. Instead, write the
        # definitive fish_greeting at the very end of ~/.config/fish/config.fish.
        # This reliably shadows vendor greetings such as CachyOS' built-in
        # `function fish_greeting; fastfetch; end`.
        FISH_FASTFETCH_HOOK.unlink(missing_ok=True)
        disabled = _disable_external_fish_fastfetch_calls()
        _write_managed_fish_override(enabled)

        observed = _probe_fish_fastfetch_count()
        expected = 1 if enabled else 0
        source_note = f" Disabled {len(disabled)} older user startup source(s)." if disabled else ""
        if observed is None:
            return True, (
                f"Fastfetch autorun {'enabled' if enabled else 'disabled'} for new Fish terminals."
                + source_note
            )
        if observed != expected:
            return True, (
                f"Yakushi installed the final Fish greeting override, but verification observed {observed} startup call(s) "
                f"instead of {expected}." + source_note
            )
        if enabled:
            return True, "Fastfetch autorun enabled. Verified exactly one Fastfetch run in a new Fish shell." + source_note
        return True, "Fastfetch autorun disabled. Verified zero Fastfetch runs in a new Fish shell." + source_note

    if shell in {"bash", "zsh"}:
        rc = Path.home() / (".bashrc" if shell == "bash" else ".zshrc")
        record("Fastfetch shell autorun", files=[rc])
        text = rc.read_text(encoding="utf-8") if rc.exists() else ""
        block_re = re.compile(
            r"(?ms)^# >>> YAKUSHI FASTFETCH AUTORUN >>>\n.*?^# <<< YAKUSHI FASTFETCH AUTORUN <<<\n?"
        )
        text = block_re.sub("", text)
        if enabled:
            if text and not text.endswith("\n"):
                text += "\n"
            text += (
                "# >>> YAKUSHI FASTFETCH AUTORUN >>>\n"
                "if command -v fastfetch >/dev/null 2>&1; then fastfetch; fi\n"
                "# <<< YAKUSHI FASTFETCH AUTORUN <<<\n"
            )
        _write_preserving_symlink(rc, text)
        return True, f"Fastfetch autorun {'enabled' if enabled else 'disabled'} for {shell}."

    return False, "Automatic Fastfetch startup currently supports Fish, Bash and Zsh."

def set_logo_padding(left: int, top: int, right: int | None = None) -> tuple[bool, str]:
    """Position the Fastfetch logo without changing the user's ASCII source."""
    ensure_config()
    text = _read_config_text()
    try:
        data = parse_config(text)
    except Exception as exc:
        return False, f"Fastfetch config could not be read: {exc}"
    logo = data.get("logo")
    if not isinstance(logo, dict):
        logo = _yakushi_logo_config(text)
    else:
        logo = dict(logo)
    current = _logo_padding(text)
    padding = dict(logo.get("padding")) if isinstance(logo.get("padding"), dict) else {}
    padding["left"] = max(0, min(64, int(left)))
    padding["top"] = max(0, min(32, int(top)))
    padding["right"] = max(0, min(64, int(current["right"] if right is None else right)))
    logo["padding"] = padding
    candidate = _replace_top_level(text, "logo", logo)
    ok, message = _validate_candidate(candidate)
    if not ok:
        return False, message
    record("Fastfetch logo position", files=[FASTFETCH_CONFIG])
    _write_preserving_symlink(FASTFETCH_CONFIG, candidate)
    return True, f"Fastfetch logo position updated: left {padding['left']}, top {padding['top']}."


def save_logo(text: str) -> tuple[bool, str]:
    ensure_config()
    record("Fastfetch ASCII art", files=[FASTFETCH_CONFIG, FASTFETCH_LOGO, FASTFETCH_RENDERED_LOGO])
    plain = text.rstrip("\n") + "\n"
    _write_preserving_symlink(FASTFETCH_LOGO, plain)
    _write_rendered_logo(plain)
    config = _read_config_text()
    candidate = _replace_top_level(config, "logo", _yakushi_logo_config(config))
    ok, message = _validate_candidate(candidate)
    if not ok:
        return False, message
    _write_preserving_symlink(FASTFETCH_CONFIG, candidate)
    return True, "ASCII art saved. Logo color follows the Terminal accent while ~/.config/fastfetch/logo.txt stays clean and editable."


def _validate_candidate(text: str) -> tuple[bool, str]:
    try:
        parse_config(text)
    except Exception as exc:
        return False, f"JSONC error: {exc}"

    fastfetch = shutil.which("fastfetch")
    if not fastfetch:
        return True, ""

    DATA.mkdir(parents=True, exist_ok=True)
    temp = DATA / "fastfetch-validate.jsonc"
    _write_preserving_symlink(temp, text.rstrip() + "\n")
    try:
        proc = subprocess.run(
            [fastfetch, "--config", str(temp), "--pipe"],
            text=True,
            capture_output=True,
            timeout=8,
            check=False,
        )
        if proc.returncode != 0:
            message = (proc.stderr or proc.stdout or "Fastfetch rejected the config.").strip().splitlines()[0]
            return False, f"Fastfetch validation failed: {message}"
    except subprocess.TimeoutExpired:
        return False, "Fastfetch validation timed out."
    finally:
        temp.unlink(missing_ok=True)
    return True, ""


def _module_index_map() -> dict[str, int]:
    return {name: index for index, (name, _label) in enumerate(COMMON_MODULES)}


def _canonical_insert_index(result: list, module_type: str) -> int:
    """Find a stable position using UI order without reordering existing entries."""
    order = _module_index_map()
    target = order.get(module_type)
    if target is None:
        return len(result)
    best_prev_index = None
    best_prev_rank = -1
    for index, entry in enumerate(result):
        rank = order.get(_module_type(entry))
        if rank is not None and rank < target and rank >= best_prev_rank:
            best_prev_index = index
            best_prev_rank = rank
    if best_prev_index is not None:
        return best_prev_index + 1
    best_next_index = None
    best_next_rank = 10**9
    for index, entry in enumerate(result):
        rank = order.get(_module_type(entry))
        if rank is not None and rank > target and rank < best_next_rank:
            best_next_index = index
            best_next_rank = rank
    return best_next_index if best_next_index is not None else len(result)


def _restore_disabled_entry(stored, module_type: str, result: list):
    entry = module_type
    before = after = None
    if isinstance(stored, dict) and "entry" in stored:
        entry = stored.get("entry", module_type)
        before = stored.get("before")
        after = stored.get("after")
    elif stored is not None:
        entry = stored
    if before:
        positions = [i for i, item in enumerate(result) if _module_type(item) == before]
        if positions:
            return entry, positions[-1] + 1
    if after:
        positions = [i for i, item in enumerate(result) if _module_type(item) == after]
        if positions:
            return entry, positions[0]
    return entry, _canonical_insert_index(result, module_type)


def repair_legacy_appended_modules() -> tuple[bool, str]:
    """Repair information modules v1.2.6 could append after the final colors row."""
    ensure_config()
    text = _read_config_text()
    modules = _modules_from_text(text)
    color_positions = [i for i, entry in enumerate(modules) if _module_type(entry) == "colors"]
    if not color_positions:
        return True, "Fastfetch module order is already clean."
    color_index = color_positions[-1]
    known = set(_module_index_map()) - {"colors", "break"}
    trailing_indexes = [i for i in range(color_index + 1, len(modules)) if _module_type(modules[i]) in known]
    if not trailing_indexes:
        return True, "Fastfetch module order is already clean."
    trailing = [modules[i] for i in trailing_indexes]
    trailing_set = set(trailing_indexes)
    result = [entry for i, entry in enumerate(modules) if i not in trailing_set]
    order = _module_index_map()
    for entry in sorted(trailing, key=lambda item: order.get(_module_type(item), 10**9)):
        result.insert(_canonical_insert_index(result, _module_type(entry)), entry)
    candidate = _replace_top_level(text, "modules", result)
    ok, message = _validate_candidate(candidate)
    if not ok:
        return False, message
    record("Fastfetch module order repair", files=[FASTFETCH_CONFIG])
    _write_preserving_symlink(FASTFETCH_CONFIG, candidate)
    return True, "Repaired Fastfetch modules that had been appended after the color palette."


def migrate_logo_rendering() -> tuple[bool, str]:
    """Move Yakushi-managed ASCII rendering to Fastfetch's color-aware file mode."""
    ensure_config()
    text = _read_config_text()
    try:
        data = parse_config(text)
    except Exception as exc:
        return False, f"Fastfetch config could not be read: {exc}"
    logo = data.get("logo")
    if isinstance(logo, dict):
        source = str(logo.get("source", ""))
        if source and not source.endswith(("logo.txt", "yakushi-logo.txt")):
            return True, "Custom external Fastfetch logo was left unchanged."
    plain = _read_logo()
    _write_rendered_logo(plain)
    candidate = _replace_top_level(text, "logo", _yakushi_logo_config(text))
    ok, message = _validate_candidate(candidate)
    if not ok:
        return False, message
    record("Fastfetch logo color migration", files=[FASTFETCH_CONFIG, FASTFETCH_RENDERED_LOGO])
    _write_preserving_symlink(FASTFETCH_CONFIG, candidate)
    return True, "Fastfetch ASCII logo now follows the Terminal accent."


def apply_modules(states: dict[str, bool]) -> tuple[bool, str]:
    ensure_config()
    text = _read_config_text()
    modules = _modules_from_text(text)
    state = _state()
    disabled = state.setdefault("disabled_modules", {})
    result = list(modules)
    for module_type, desired in states.items():
        module_type = module_type.lower()
        positions = [i for i, entry in enumerate(result) if _module_type(entry) == module_type]
        if desired:
            if not positions:
                stored = disabled.pop(module_type, None)
                entry, insert_at = _restore_disabled_entry(stored, module_type, result)
                result.insert(max(0, min(insert_at, len(result))), entry)
        elif positions:
            first = positions[0]
            entry = result[first]
            before = _module_type(result[first - 1]) if first > 0 else None
            after = _module_type(result[first + 1]) if first + 1 < len(result) else None
            if any(_module_type(item) == "colors" for item in result[:first]) and module_type not in {"colors", "break"}:
                before = after = None
            disabled[module_type] = {"entry": entry, "before": before, "after": after}
            result = [entry for entry in result if _module_type(entry) != module_type]
    candidate = _replace_top_level(text, "modules", result)
    expected = {name.lower(): bool(value) for name, value in states.items()}
    actual = _module_status(candidate)
    mismatched = [name for name, desired in expected.items() if actual.get(name, False) != desired]
    if mismatched:
        try:
            data = parse_config(text)
        except Exception as exc:
            return False, f"Fastfetch config could not be updated safely: {exc}"
        data["modules"] = result
        candidate = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        actual = _module_status(candidate)
        mismatched = [name for name, desired in expected.items() if actual.get(name, False) != desired]
        if mismatched:
            return False, "Fastfetch module verification failed for: " + ", ".join(mismatched)
    ok, message = _validate_candidate(candidate)
    if not ok:
        return False, message
    record("Fastfetch modules", files=[FASTFETCH_CONFIG, FASTFETCH_STATE])
    _write_preserving_symlink(FASTFETCH_CONFIG, candidate)
    _save_state(state)
    verify = _module_status(_read_config_text())
    failed = [name for name, desired in expected.items() if verify.get(name, False) != desired]
    if failed:
        return False, "Fastfetch config write verification failed for: " + ", ".join(failed)
    return True, f"Fastfetch modules updated in {FASTFETCH_CONFIG}. Disabled modules keep their position when re-enabled."


def save_config_text(text: str) -> tuple[bool, str]:
    try:
        parsed = parse_config(text)
    except Exception as exc:
        return False, f"JSONC error: {exc}"

    if "modules" in parsed and not isinstance(parsed["modules"], list):
        return False, 'Fastfetch "modules" must be an array.'

    DATA.mkdir(parents=True, exist_ok=True)
    temp = DATA / "fastfetch-validate.jsonc"
    _write_preserving_symlink(temp, text.rstrip() + "\n")

    fastfetch = shutil.which("fastfetch")
    if fastfetch:
        try:
            proc = subprocess.run(
                [fastfetch, "--config", str(temp), "--structure", "title", "--pipe"],
                text=True,
                capture_output=True,
                timeout=6,
                check=False,
            )
            if proc.returncode != 0:
                message = (proc.stderr or proc.stdout or "Fastfetch rejected the config.").strip().splitlines()[0]
                return False, f"Fastfetch validation failed: {message}"
        except subprocess.TimeoutExpired:
            return False, "Fastfetch validation timed out."
        finally:
            temp.unlink(missing_ok=True)

    record("Fastfetch advanced config", files=[FASTFETCH_CONFIG])
    _write_preserving_symlink(FASTFETCH_CONFIG, text.rstrip() + "\n")
    return True, "Fastfetch config validated and saved."



def sync_terminal_colors() -> tuple[bool, str]:
    """Route Fastfetch logo/key/title accent through Kitty ANSI color1."""
    ensure_config()
    text = _read_config_text()
    try:
        data = parse_config(text)
    except Exception as exc:
        return False, f"Fastfetch config could not be read: {exc}"
    display = data.get("display")
    if not isinstance(display, dict):
        display = {}
    else:
        display = dict(display)
    colors = display.get("color")
    if not isinstance(colors, dict):
        colors = {}
    else:
        colors = dict(colors)
    colors["keys"] = "red"
    colors["title"] = "red"
    display["color"] = colors
    modules = _modules_from_text(text)
    normalized = []
    for entry in modules:
        if isinstance(entry, dict) and "keyColor" in entry:
            entry = dict(entry)
            entry["keyColor"] = "red"
        normalized.append(entry)
    logo = data.get("logo")
    if not isinstance(logo, dict) or str(logo.get("source", "")).endswith(("logo.txt", "yakushi-logo.txt")):
        logo = _yakushi_logo_config(text)
    record("Fastfetch terminal color sync", files=[FASTFETCH_CONFIG, FASTFETCH_RENDERED_LOGO])
    _write_rendered_logo(_read_logo())
    text = _replace_top_level(text, "display", display)
    text = _replace_top_level(text, "modules", normalized)
    text = _replace_top_level(text, "logo", logo)
    _write_preserving_symlink(FASTFETCH_CONFIG, text)
    return True, "Fastfetch ASCII logo, keys and title now follow the Terminal accent through Kitty ANSI color1."


def preview() -> tuple[bool, str]:
    ensure_config()
    fastfetch = shutil.which("fastfetch")
    kitty = shutil.which("kitty")
    if not fastfetch:
        return False, "Fastfetch is not installed."
    if not kitty:
        return False, "Kitty is not installed."
    try:
        subprocess.Popen(
            [kitty, "--detach", "--hold", "--title", "Yakushi Fastfetch Preview", fastfetch, "--config", str(FASTFETCH_CONFIG)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True, "Fastfetch preview opened in Kitty."
    except OSError as exc:
        return False, f"Could not open Fastfetch preview: {exc}"
