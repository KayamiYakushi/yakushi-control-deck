#!/usr/bin/env fish
set ROOT (cd (dirname (status filename)); and pwd)
exec bash "$ROOT/install.sh" $argv
