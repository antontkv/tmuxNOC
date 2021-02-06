FROM python:3.8.7-slim

# Installing dependencies
RUN set -x; \
    apt-get update && \
    apt-get install -y wget libutempter0 expect xsel git telnet
RUN set -x; \
    wget http://ftp.us.debian.org/debian/pool/main/libe/libevent/libevent-2.1-7_2.1.12-stable-1_amd64.deb && \
    dpkg -i libevent-2.1-7_2.1.12-stable-1_amd64.deb && \
    rm libevent-2.1-7_2.1.12-stable-1_amd64.deb

# Downloading .deb and istalling
RUN set -x; \
    wget http://ftp.us.debian.org/debian/pool/main/t/tmux/tmux_3.2~rc3-1_amd64.deb && \
    dpkg -i tmux_3.2~rc3-1_amd64.deb && \
    rm tmux_3.2~rc3-1_amd64.deb

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
