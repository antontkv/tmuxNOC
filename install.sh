#!/bin/bash

set -e
set -u
set -o pipefail

TMUX_VERSION=3.2-rc3

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
  sudo apt-get -y install wget libutempter0
  wget http://ftp.us.debian.org/debian/pool/main/libe/libevent/libevent-2.1-7_2.1.12-stable-1_amd64.deb
  sudo dpkg -i libevent-2.1-7_2.1.12-stable-1_amd64.deb
  rm libevent-2.1-7_2.1.12-stable-1_amd64.deb

  # Downloading .deb and installing
  wget http://ftp.us.debian.org/debian/pool/main/t/tmux/tmux_3.2~rc3-1_amd64.deb
  sudo dpkg -i tmux_3.2~rc3-1_amd64.deb
  rm tmux_3.2~rc3-1_amd64.deb
}

if ! is_app_installed expect || ! is_app_installed git || ! is_app_installed telnet; then
  printf "\nYou don't have expect, git or telnet installed on the system.\n\
To install them you'll need sudo rights.\n\n"
read -p "Press Enter to continue..."
  install_dependencies
fi

if ! is_app_installed tmux; then
  printf "\nTmux is not installed. Version $TMUX_VERSION will be downloaded and installed from Debian archives.\n\
To install you'll need sudo rights.\n\n"
read -p "Press Enter to continue..."
  install_tmux
elif ! tmux -V | grep -q $TMUX_VERSION; then
  printf "\nWARNING: You have$(tmux -V | sed s/tmux//) tmux version installed.\nThis project was tested on \
$TMUX_VERSION tmux version. So something may be broken.\nYou can cancel this script and remove tmux from the \
system. Then run the script again, it will install needed version of tmux.\n\n"
  read -p "Press Enter to continue..."
fi

# Install TPM plugins.
if [ ! -e "$HOME/tmuxNOC/plugins/tpm" ]; then
  printf "WARNING: Cannot found TPM (Tmux Plugin Manager) \
 at default location: \$HOME/tmuxNOC/plugins/tpm.\n"
  git clone https://github.com/tmux-plugins/tpm ~/tmuxNOC/plugins/tpm
fi

if [ -e "$HOME/.tmux.conf" ]; then
  printf "Found existing .tmux.conf in your \$HOME directory. \
Will create a backup at $HOME/.tmux.conf.bak\n"
fi

cp -f "$HOME/.tmux.conf" "$HOME/.tmux.conf.bak" 2>/dev/null || true
ln -sf "$HOME"/tmuxNOC/tmux.conf "$HOME"/.tmux.conf;

printf "Install TPM plugins\n"
tmux -c "$HOME"/tmuxNOC/plugins/tpm/bin/install_plugins || true

printf "\nOK: Completed\n"
