#!/usr/bin/env bash
if command -v powerprofilesctl >/dev/null 2>&1; then mode=$(powerprofilesctl get 2>/dev/null || true); else mode=$(cat /sys/devices/system/cpu/cpufreq/policy0/scaling_governor 2>/dev/null || true); fi
case "$mode" in performance) printf "󱐋\n";; balanced|schedutil|powersave) printf "󰂎\n";; *) printf "󰂎\n";; esac
