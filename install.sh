#!/bin/bash

set -e
set -u
set -o pipefail

TMUX_VERSION=3.1b
TMUX_RC=

is_app_installed() {
  type "$1" &>/dev/null
}

install_tmux() {
  printf "Install tmux from source\n"
  # Installing dependencies
  sudo apt-get -y install wget tar libevent-dev ncurses-dev build-essential bison pkg-config

  # Downloading and unpacking tmux source files
  if [ ! -e "$HOME/tmuxNOC/" ]; then
      mkdir "$HOME/tmuxNOC"
  fi
  cd ~/tmuxNOC/
  wget https://github.com/tmux/tmux/releases/download/$TMUX_VERSION/tmux-$TMUX_VERSION$TMUX_RC.tar.gz
  tar -zxf tmux-$TMUX_VERSION$TMUX_RC.tar.gz
  rm -f tmux-$TMUX_VERSION$TMUX_RC.tar.gz

  # Building and installing tmux
  cd tmux-$TMUX_VERSION$TMUX_RC
  ./configure
  make && sudo make install
  cd -
  rm -rf tmux-$TMUX_VERSIO$TMUX_RC
}

if ! is_app_installed tmux; then
  printf "\nTmux is not installed. Version $TMUX_VERSION$TMUX_RC will be build and installed from source.\n\
To install dependencies for build you need sudo rights.\n\n"
read -p "Press Enter to continue..."
  install_tmux
elif ! tmux -V | grep -q $TMUX_VERSION; then
  printf "\nWARNING: You have$(tmux -V | sed s/tmux//) tmux version installed.\nThis project was tested on \
$TMUX_VERSION$TMUX_RC tmux version. So something may be broken.\nYou can cancel this script and remove tmux from the \
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
