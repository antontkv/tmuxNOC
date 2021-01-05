FROM python:3.8.7-slim
ENV TMUX_VERSION=3.2-rc
ENV TMUX_RC=3

# Installing dependencies
RUN set -x; \
    apt-get update && \
    apt-get install -y wget tar libevent-dev ncurses-dev build-essential bison pkg-config expect xsel git telnet

# Downloading and unpacking tmux source files
RUN set -x; \
    mkdir -p tmux-source && \
    cd tmux-source && \
    wget https://github.com/tmux/tmux/releases/download/$TMUX_VERSION/tmux-$TMUX_VERSION$TMUX_RC.tar.gz && \
    tar -zxf tmux-$TMUX_VERSION$TMUX_RC.tar.gz --strip-components=1 && \
    rm -f tmux-$TMUX_VERSION$TMUX_RC.tar.gz

# Building and installing tmux
RUN set -x; \
    cd tmux-source && \
    ./configure && \
    make && make install && \
    cd - && \
    rm -rf tmux-source

# Creating user
RUN useradd -ms /bin/bash tmuxnoc
USER tmuxnoc
# Enable colors for terminal
ENV TERM=xterm-256color

# Dir for tmuxNOC
RUN cd && mkdir tmuxNOC
WORKDIR "/home/tmuxnoc"
VOLUME "/home/tmuxnoc/tmuxNOC"

CMD ["bash"]
