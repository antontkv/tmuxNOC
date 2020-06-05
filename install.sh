#!/bin/bash

TMUX_VERSION=3.1b

# Removing old tmux installed from apt.
sudo apt-get -y remove tmux
# Installing dependencies
sudo apt-get -y install wget tar libevent-dev ncurses-dev build-essential bison pkg-config

# Downloading and unpacking tmux source files
wget https://github.com/tmux/tmux/releases/download/$TMUX_VERSION/tmux-$TMUX_VERSION.tar.gz
tar -zxf tmux-$TMUX_VERSION.tar.gz
rm -f tmux-$TMUX_VERSION.tar.gz

# Building and installing tmux
cd tmux-$TMUX_VERSION
./configure
make && sudo make install
cd -
rm -rf tmux-$TMUX_VERSION
