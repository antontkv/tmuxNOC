#!/usr/bin/env bash

# This script behaves like `yank.sh`. It will output system clipboard content to stdout, but when
# argument 'tmux' send to it, it will set tmux buffer with system clipboard content. This is
# because I was trying to set tmux buffer with command `run 'tmux set-buffer "$($paste)"'` and for
# the most parts it works, but when used with combination of `send-keys -X cancel`, it doesn't
# work. Hence this workaround.

set -e

is_app_installed() {
  type "$1" &>/dev/null
}

# Thanks to https://unix.stackexchange.com/a/658742.
# This function provides a general solution to the problem of preserving
# trailing newlines in a command substitution.
#
#    cmdsub <command goes here>
#
# If the command succeeded, the result will be found in variable CMDSUB_RESULT.
cmdsub() {
  local -r BYTE=$'\x78'
  local result
  if result=$("$@"; ret=$?; echo "$BYTE"; exit "$ret"); then
    local LC_ALL=C
    CMDSUB_RESULT=${result%$BYTE}
  else
    return "$?"
  fi
}

paste_backend=""
if [ -n "${DISPLAY-}" ] && is_app_installed xsel; then
  paste_backend="xsel -o --clipboard"
elif is_app_installed win32yank.exe; then
  paste_backend="win32yank.exe -o"
elif is_app_installed paste.exe; then
  paste_backend="paste.exe"
fi

if [ -n "$paste_backend" ]; then
  if [[ "$paste_backend" =~ ("paste.exe"|"win32yank.exe") ]]; then
    cmd() { $paste_backend | tr -d "\r"; }
  else
    cmd() { $paste_backend; }
  fi
  cmdsub cmd
  clipboard_content=$CMDSUB_RESULT

  if [ "$1" = "tmux" ]; then
    printf "%s" "$clipboard_content" | tmux load-buffer -
  else
    printf "%s" "$clipboard_content"
  fi
  exit;
fi
