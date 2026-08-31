#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; [[ -d "$ROOT/.git" ]] && git -C "$ROOT" pull --ff-only; exec "$ROOT/install.sh"
