#!/usr/bin/env bash

set -eu

is_app_installed() {
  type "$1" &>/dev/null
}

# get data either form stdin or from file
buf=$(cat "$@")

# Resolve copy backend: pbcopy (OSX), reattach-to-user-namespace (OSX), xclip/xsel (Linux)
copy_backend=""
if is_app_installed pbcopy; then
  copy_backend="pbcopy"
elif is_app_installed reattach-to-user-namespace; then
  copy_backend="reattach-to-user-namespace pbcopy"
elif is_app_installed win32yank.exe; then
  copy_backend="win32yank.exe -i"
elif is_app_installed clip.exe; then
  copy_backend="clip.exe"
elif [ -n "${DISPLAY-}" ] && is_app_installed xsel; then
  copy_backend="xsel -i --clipboard"
elif [ -n "${DISPLAY-}" ] && is_app_installed xclip; then
  copy_backend="xclip -i -f -selection primary | xclip -i -selection clipboard"
fi

# if copy backend is resolved, copy and exit
if [ -n "$copy_backend" ]; then
  printf "%s" "$buf" | eval "$copy_backend"
  exit;
fi
