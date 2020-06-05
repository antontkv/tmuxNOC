#!/bin/bash

TMUX_VERSION=3.1b

# Removing old tmux installed from apt.
sudo apt-get -y remove tmux
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

# Install TPM plugins.
if [ ! -e "$HOME/tmuxNOC/plugins/tpm" ]; then
  printf "WARNING: Cannot found TPM (Tmux Plugin Manager) \
 at default location: \$HOME/tmuxNOC/plugins/tpm.\n"
  git clone https://github.com/tmux-plugins/tpm ~/tmuxNOC/plugins/tpm
fi

# TPM requires running tmux server, as soon as `tmux start-server` does not work
# create dump __noop session in detached mode, and kill it when plugins are installed
printf "Install TPM plugins\n"
tmux new -d -s __noop >/dev/null 2>&1 || true 
tmux set-environment -g TMUX_PLUGIN_MANAGER_PATH "~/tmuxNOC/plugins"
"$HOME"/tmuxNOC/plugins/tpm/bin/install_plugins || true
tmux kill-session -t __noop >/dev/null 2>&1 || true

printf "OK: Completed\n"
