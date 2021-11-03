#!/bin/bash

set -e
set -u
set -o pipefail

TMUX_VERSION=3.2a

is_app_installed() {
  type "$1" &>/dev/null
}

install_dependencies() {
  sudo apt update
  sudo apt-get -y install expect git telnet
}

install_tmux() {
  # Installing dependencies
  if [ ! -e "$HOME/tmuxNOC/" ]; then
      mkdir "$HOME/tmuxNOC"
  fi
  cd ~/tmuxNOC/
  sudo apt update
  sudo apt-get -y install wget

  # Downloading .appimage and installing it.
  wget https://github.com/antontkv/tmux-appimage/releases/download/$TMUX_VERSION/tmux-$TMUX_VERSION-x86_64.appimage
  chmod +x tmux-$TMUX_VERSION-x86_64.appimage
  sudo mv tmux-$TMUX_VERSION-x86_64.appimage /usr/local/bin/tmux
}

if ! is_app_installed expect || ! is_app_installed git || ! is_app_installed telnet; then
  printf "\nYou don't have expect, git or telnet installed on the system.\n\
To install them you'll need sudo rights.\n\n"
read -p "Press Enter to continue..."
  install_dependencies
fi

if ! is_app_installed tmux; then
  printf "\nTmux is not installed. Version $TMUX_VERSION will be downloaded and installed from \
https://github.com/antontkv/tmux-appimage/releases.\n\
To install you'll need sudo rights.\n\n"
read -p "Press Enter to continue..."
  install_tmux
elif ! tmux -V | grep -q $TMUX_VERSION; then
  printf "\nWARNING: You have$(tmux -V | sed s/tmux//) tmux version installed.\nThis project was tested on \
$TMUX_VERSION tmux version. So something may be broken.\nYou can cancel this script and remove tmux from the \
system. Then run the script again, it will install needed version of tmux.\n\n"
  read -p "Press Enter to continue..."
fi

if [ -e "$HOME/.tmux.conf" ]; then
  printf "\nFound existing .tmux.conf in your \$HOME directory. \
Will create a backup at $HOME/.tmux.conf.bak\n"
fi

cp -f "$HOME/.tmux.conf" "$HOME/.tmux.conf.bak" 2>/dev/null || true
ln -sf "$HOME"/tmuxNOC/tmux.conf "$HOME"/.tmux.conf;

printf "\nOK: Completed\n"
