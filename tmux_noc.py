#!/usr/bin/python3
import subprocess
import time
import argparse
import json
import datetime
from pathlib import Path

def load_sessions():
    home = str(Path.home())
    with open(f'{home}/tmuxNOC/sessions.json', 'r') as f:
        sessions = json.load(f)
    return sessions

def save_session(connection_type, host):
    home = str(Path.home())
    sessions = load_sessions()
    session = {
        'connection_type': connection_type,
        'host': host,
        'time': datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    }
    sessions[time.time()] = session
    if connection_type == 'telnet':
        sessions['last_telnet_session'] = host
    with open(f'{home}/tmuxNOC/sessions.json', 'w') as f:
        json.dump(sessions, f)

def setup_telnet():
    home = str(Path.home())
    sessions = load_sessions()
    if 'last_telnet_session' in sessions:
        hostname = sessions['last_telnet_session']
    else:
        hostname = 'hostname'
    command = [
        'tmux',
        'command-prompt',
        '-p',
        'telnet:',
        '-I',
        hostname,
        f'run "{home}/tmuxNOC/tmux_noc.py connect_telnet --host %1"'
    ]
    subprocess.run(command)

def connect_telnet(host):
    home = str(Path.home())
    subprocess.run(
        [
            'tmux',
            'new-window',
            '-n', host,
            f'PROMPT_COMMAND="telnet {host}";TERM=vt100-w bash --rcfile {home}/tmuxNOC/tmux_noc_bashrc'
        ]
    )
    subprocess.run(['tmux', 'source-file', f'{home}/tmuxNOC/telnet_tmux.conf'])
    # subprocess.run(['tmux', 'send-keys', f'telnet {host}', 'Enter'])
    save_session('telnet', host)

def tmux_send(string):
    subprocess.run(
        ['tmux', 'send-keys', string, 'Enter'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def tmux_read_screen():
    output_b = subprocess.run(['tmux', 'capture-pane', '-J', '-p'], stdout=subprocess.PIPE).stdout
    output_list_temp = output_b.decode('UTF-8').split('\n')
    output_list = [line for line in output_list_temp if len(line) != 0]
    return output_list

def tmux_wait_for(string, timeout=3):
    found = False
    for _ in range(timeout*10):
        output_lines = tmux_read_screen()
        for line in output_lines[-5:]:
            if string in line:
                found = True
                break
        if found:
            break
        else:
            time.sleep(0.1)

    return found

def send_login_pwd(login_number):
    home = str(Path.home())
    with open(f'{home}/tmuxNOC/.logins', 'r') as f:
        logins = f.readlines()
    for line in logins:
        if f'LOGIN{login_number}' in line:
            login = line.replace(f'LOGIN{login_number}=', '').replace('\n', '')
        if f'PASS{login_number}' in line:
            password = line.replace(f'PASS{login_number}=', '').replace('\n', '')
    tmux_send(login)
    if tmux_wait_for('assword'):
        tmux_send(password)
    else:
        subprocess.run(['tmux', 'display-message', 'Password prompt not found.'])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Connect to telnet or ssh from tmux.')
    parser.add_argument('type', choices=['login', 'setup_telnet', 'connect_telnet'])
    parser.add_argument('--login_number', nargs='?')
    parser.add_argument('--host', nargs='?')
    args = parser.parse_args()

    if args.type == 'login':
        send_login_pwd(args.login_number)
    elif args.type == 'setup_telnet':
        setup_telnet()
    elif args.type == 'connect_telnet':
        connect_telnet(args.host)
