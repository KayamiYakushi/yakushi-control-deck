#!/usr/bin/env bash
set -euo pipefail
rm -rf "$HOME/.local/share/yakushi-control-deck"; rm -f "$HOME/.local/bin/yakushi-deck" "$HOME/.local/share/applications/yakushi-control-deck.desktop"
printf 'Yakushi application files removed. Desktop configs and packages remain in place.\nFor guarded full removal, use 05 // DANGER -> Self Destruction before running this lightweight helper.\nIf Yakushi SDDM is active, remove /etc/sddm.conf.d/90-yakushi-theme.conf manually.\nBackups: %s\n' "$HOME/.config/yakushi-control-deck/install-backups"
