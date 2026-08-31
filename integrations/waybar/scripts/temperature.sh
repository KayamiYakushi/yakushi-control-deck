#!/usr/bin/env bash
set -u
kind="${1:-cpu}"
read_temp(){ local hw="$1" input="$2" v; [[ -r "$hw/$input" ]] || return 1; v=$(cat "$hw/$input" 2>/dev/null) || return 1; [[ "$v" =~ ^[0-9]+$ ]] || return 1; printf '%d°C\n' "$((v/1000))"; }
for hw in /sys/class/hwmon/hwmon*; do
  [[ -r "$hw/name" ]] || continue; name=$(cat "$hw/name" 2>/dev/null || true)
  if [[ "$kind" == cpu && "$name" =~ ^(k10temp|coretemp|zenpower)$ ]]; then for input in temp1_input temp2_input temp3_input; do read_temp "$hw" "$input" && exit 0; done; fi
  if [[ "$kind" == gpu && "$name" == amdgpu ]]; then for input in temp1_input temp2_input temp3_input; do read_temp "$hw" "$input" && exit 0; done; fi
done
printf 'N/A\n'
