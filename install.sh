#!/bin/bash

set -e
set -u
set -o pipefail

is_app_installed() {
  type "$1" &>/dev/null
}

install_dependencies() {
  if is_app_installed apt; then
    sudo apt update
    sudo apt-get -y install expect git telnet
  elif is_app_installed pacman; then
    sudo pacman -S expect git inetutils
  fi
}

install_tmux() {
  # Installing dependencies
  if [ ! -e "$HOME/tmuxNOC/" ]; then
      mkdir "$HOME/tmuxNOC"
  fi
  cd ~/tmuxNOC/
  if is_app_installed apt; then
    sudo apt-get install tmux
  elif is_app_installed pacman; then
    sudo pacman -Sy tmux
  else
    printf "\nNor apt nor pacman found in the system.\n"
    exit
  fi
}

if ! is_app_installed expect || ! is_app_installed git || ! is_app_installed telnet; then
  printf "\nYou don't have expect, git or telnet installed on the system.\n\
To install them you'll need sudo rights.\n\n"
read -p "Press Enter to continue..."
  install_dependencies
fi

if ! is_app_installed tmux; then
  printf "\nTmux is not installed. Package manager will be used to install it.\n\
To install you'll need sudo rights.\n\n"
read -p "Press Enter to continue..."
  install_tmux
fi

if [ -e "$HOME/.tmux.conf" ]; then
  printf "\nFound existing .tmux.conf in your \$HOME directory. \
Will create a backup at $HOME/.tmux.conf.bak\n"
fi

cp -f "$HOME/.tmux.conf" "$HOME/.tmux.conf.bak" 2>/dev/null || true
ln -sf "$HOME"/tmuxNOC/tmux.conf "$HOME"/.tmux.conf;

printf "\nOK: Completed\n"
