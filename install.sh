#!/bin/bash

set -e
set -u
set -o pipefail

TMUX_VERSION=3.1b

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
  wget https://github.com/tmux/tmux/releases/download/$TMUX_VERSION/tmux-$TMUX_VERSION.tar.gz
  tar -zxf tmux-$TMUX_VERSION.tar.gz
  rm -f tmux-$TMUX_VERSION.tar.gz

  # Building and installing tmux
  cd tmux-$TMUX_VERSION
  ./configure
  make && sudo make install
  cd -
  rm -rf tmux-$TMUX_VERSION
}

if ! is_app_installed tmux; then
  install_tmux
elif ! tmux -V | grep -q $TMUX_VERSION; then
  printf "WARNING: Not configured tmux version installed. Remove it first."
  exit 1
fi

# Install TPM plugins.
if [ ! -e "$HOME/tmuxNOC/plugins/tpm" ]; then
  printf "WARNING: Cannot found TPM (Tmux Plugin Manager) \
 at default location: \$HOME/tmuxNOC/plugins/tpm.\n"
  git clone https://github.com/tmux-plugins/tpm ~/tmuxNOC/plugins/tpm
fi

if [ -e "$HOME/.tmux.conf" ]; then
  printf "Found existing .tmux.conf in your \$HOME directory. Will create a backup at $HOME/.tmux.conf.bak\n"
fi

cp -f "$HOME/.tmux.conf" "$HOME/.tmux.conf.bak" 2>/dev/null || true
ln -sf "$HOME"/tmuxNOC/tmux.conf "$HOME"/.tmux.conf;

# TPM requires running tmux server, as soon as `tmux start-server` does not work
# create dump __noop session in detached mode, and kill it when plugins are installed
printf "Install TPM plugins\n"
tmux new -d -s __noop >/dev/null 2>&1 || true 
tmux set-environment -g TMUX_PLUGIN_MANAGER_PATH "~/tmuxNOC/plugins"
"$HOME"/tmuxNOC/plugins/tpm/bin/install_plugins || true
tmux kill-session -t __noop >/dev/null 2>&1 || true

printf "OK: Completed\n"
