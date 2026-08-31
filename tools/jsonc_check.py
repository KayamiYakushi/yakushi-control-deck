#!/usr/bin/env python3
"""Validate JSON-with-comments (JSONC) using only Python's standard library.

Supports // line comments, /* block comments */, and trailing commas while
preserving comment-like text inside JSON strings.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def strip_comments(text: str) -> str:
    out: list[str] = []
    i = 0
    in_string = False
    escaped = False
    length = len(text)

    while i < length:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < length else ""

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
            i += 2
            while i < length and text[i] not in "\r\n":
                i += 1
            continue

        if ch == "/" and nxt == "*":
            i += 2
            while i + 1 < length and not (text[i] == "*" and text[i + 1] == "/"):
                # Preserve newlines so parser line numbers stay meaningful.
                if text[i] in "\r\n":
                    out.append(text[i])
                i += 1
            if i + 1 >= length:
                raise ValueError("unterminated block comment")
            i += 2
            continue

        out.append(ch)
        i += 1

    return "".join(out)


def strip_trailing_commas(text: str) -> str:
    out: list[str] = []
    i = 0
    in_string = False
    escaped = False
    length = len(text)

    while i < length:
        ch = text[i]
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
            while j < length and text[j].isspace():
                j += 1
            if j < length and text[j] in "]}":
                i += 1
                continue

        out.append(ch)
        i += 1

    return "".join(out)


def loads_jsonc(text: str):
    return json.loads(strip_trailing_commas(strip_comments(text)))


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {Path(sys.argv[0]).name} FILE", file=sys.stderr)
        return 2

    path = Path(sys.argv[1]).expanduser()
    try:
        loads_jsonc(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"JSONC validation failed for {path}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
