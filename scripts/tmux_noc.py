#!/usr/bin/python3
import subprocess
import time
import argparse
import json
import datetime
from pathlib import Path
import os
from errno import EEXIST
import sys
import re


class ANSIColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def create_dir(filename):
    """
    Creates path for file, if directories doesn't exists.
    """
    if not os.path.exists(os.path.dirname(filename)):
        try:
            os.makedirs(os.path.dirname(filename))
        except OSError as exc:  # Guard against race condition
            if exc.errno != EEXIST:
                raise


def save_pane_history(output_file_name, pane_id='*', pipe='o', only_once=False):
    for _ in pipe:
        output_b = subprocess.run([
            'tmux',
            'capture-pane',
            '-J',
            '-p',
            '-S',
            '-20000',
            '-t',
            pane_id,
        ], stdout=subprocess.PIPE).stdout
        output = output_b.decode('UTF-8')
        if output == '':
            continue
        with open(output_file_name, 'w') as f:
            f.write(output)
        if only_once:
            break
        time.sleep(1)


def pane_log(connection_type, host):
    home = str(Path.home())
    sessions_metadata = load_sessions_metadata()
    if connection_type == 'l':
        last_session_index = '--'
    else:
        last_session_index = sessions_metadata['last_session_index']
    year = datetime.datetime.now().strftime("%Y")
    month = datetime.datetime.now().strftime("%m")
    day = datetime.datetime.now().strftime("%d")
    current_time = datetime.datetime.now().strftime("%H_%M_%S")
    log_filename = f'{home}/tmuxNOC/local/log/{year}/{month}/{day}/{current_time}---!{last_session_index}_{connection_type}_{host}.log'
    create_dir(log_filename)

    subprocess.run([
        'tmux',
        'pipe-pane',
        '-o',
        f'{home}/tmuxNOC/scripts/tmux_noc.py save_pane_history --file_name {log_filename}\
          --pane_id #{{pane_id}} -i -'
    ])


def search_logs():
    home = str(Path.home())
    query = input('grep in logs: ')
    subprocess.run(
        ['grep', '--color=always', '-n', '-r', '-A 2', '-B 2', query, '.'],
        cwd=f'{home}/tmuxNOC/local/log/'
    )
    search_logs()


def open_log(history_index):
    home = str(Path.home())
    log_file = None
    for path in Path(f'{home}/tmuxNOC/local/log').rglob(f'*{history_index}*'):
        log_file = str(path)
    if log_file is None:
        subprocess.run(
            ['tmux', 'display-message', f'Log file with index {history_index} not found.']
        )
    else:
        host = log_file.split('_')[-1].replace('.log', '')
        subprocess.run(['tmux', 'new-window', '-n', f'Log {host}', f'less -M "{log_file}"'])


def load_sessions_metadata():
    home = str(Path.home())
    with open(f'{home}/tmuxNOC/sessions.json', 'r') as f:
        sessions = json.load(f)
    return sessions


def save_session(connection_type, host):
    home = str(Path.home())
    sessions_metadata = load_sessions_metadata()
    if 'last_session_index' in sessions_metadata:
        sessions_metadata['last_session_index'] += 1
    else:
        sessions_metadata['last_session_index'] = 1
    if 'last_five_sessions' in sessions_metadata:
        last_five_sessions = sessions_metadata['last_five_sessions']
        if host not in str(last_five_sessions):
            if len(last_five_sessions) >= 5:
                last_five_sessions.pop(4)
            last_five_sessions.insert(0, {
                'connection_type': connection_type,
                'host': host
            })
        else:
            last_connection = None
            for index, session in enumerate(last_five_sessions):
                if connection_type == session['connection_type'] and host == session['host']:
                    last_connection = index
            if last_connection is None:
                if len(last_five_sessions) >= 5:
                    last_five_sessions.pop(4)
                last_five_sessions.insert(0, {
                    'connection_type': connection_type,
                    'host': host
                })
            else:
                last_five_sessions.pop(last_connection)
                last_five_sessions.insert(0, {
                    'connection_type': connection_type,
                    'host': host
                })

    else:
        last_five_sessions = [{
            'connection_type': connection_type,
            'host': host
        }]
    sessions_metadata['last_five_sessions'] = last_five_sessions
    sessions_metadata[f'last_{connection_type}_session'] = host
    with open(f'{home}/tmuxNOC/sessions.json', 'w') as f:
        json.dump(sessions_metadata, f)

    sessions_history_filename = f'{home}/tmuxNOC/local/sessions_history.log'
    with open(sessions_history_filename, 'r+') as sessions_history_file:
        sessions_history = sessions_history_file.read()
        current_date = datetime.datetime.now().strftime("%d.%m.%Y")
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        if f'# {current_date}' not in sessions_history:
            sessions_history_file.write(f'# {current_date}\n')
        sessions_history_file.write(
            f'    {sessions_metadata["last_session_index"]} {current_date} {current_time} {connection_type} {host}\n'
        )


def ssh_config_hosts():
    home = str(Path.home())
    if not os.path.exists(f'{home}/.ssh/config'):
        return 1

    with open(f'{home}/.ssh/config') as f:
        ssh_config = f.readlines()
    hosts = []
    for line in ssh_config:
        if line.startswith('Host'):
            hosts.append(line.replace('Host ', '').replace('\n', ''))
    return hosts


def ssh_menu():
    home = str(Path.home())
    command = [
        'tmux', 'display-menu',
        '-T', '#[align=centre]SSH Config Hosts',
        '-x', 'P',
        '-y', 'S',
    ]
    ssh_hosts_list = ssh_config_hosts()
    if ssh_hosts_list != 1:
        for index, host in enumerate(ssh_hosts_list):
            index += 1
            if index == 10:
                index = 0
            elif 20 > index > 10:
                index = f'M-{index - 10}'
            elif index == 20:
                index = 'M-0'
            elif 30 > index > 20:
                index = f'C-{index - 20}'
            elif index == 30:
                index = 'C-0'
            command += [
                host,
                str(index),
                f'run "{home}/tmuxNOC/scripts/tmux_noc.py connect_ssh --host {host}"'
            ]
    subprocess.run(command)


def noc_menu():
    home = str(Path.home())

    if ssh_config_hosts() == 1:
        ssh_hosts = False
    else:
        ssh_hosts = True

    sessions_metadata = load_sessions_metadata()
    if 'last_five_sessions' in sessions_metadata:
        last_five_sessions = sessions_metadata['last_five_sessions']
        last_sessions = ['']
        for index, session in enumerate(last_five_sessions):
            connection_type = session['connection_type']
            host = session['host']
            last_sessions.append(f'{connection_type} {host}')
            last_sessions.append(f'{index + 1}')
            last_sessions.append(
                f'run "{home}/tmuxNOC/scripts/tmux_noc.py connect_{connection_type} --host {host}"'
            )
    else:
        last_sessions = None

    clipboard = subprocess.run(
        f'{home}/tmuxNOC/scripts/paste.sh', stdout=subprocess.PIPE
    ).stdout.decode('UTF-8').split('\n')[0]
    clipboard = [word for word in clipboard.split(' ') if len(word) != 0]
    if len(clipboard) != 0:
        clipboard = [
            '',
            f'telnet {clipboard[0]}', 'v', f'run "{home}/tmuxNOC/scripts/tmux_noc.py connect_telnet --host {clipboard[0]}"',
            f'ssh {clipboard[0]}', 'V', f'run "{home}/tmuxNOC/scripts/tmux_noc.py connect_ssh --host {clipboard[0]}"',
        ]
    else:
        clipboard = None


    command = [
        'tmux', 'display-menu',
        '-T', '#[align=centre]NOC',
        '-x', 'P',
        '-y', 'S',
        'Show Sessions History', 'h', 'split-window -h "less +G $HOME/tmuxNOC/local/sessions_history.log"',
        'Open Log File', 'l', f'command-prompt -p "Open Log Number:" \'run "{home}/tmuxNOC/scripts/tmux_noc.py open_log --history_index %1"\'',
        'Search in Logs', 'L', f'split-window -v "{home}/tmuxNOC/scripts/tmux_noc.py search_logs"',
        '',
        'Send Commands with Delay', 'd', f'split-window -h "{home}/tmuxNOC/scripts/tmux_noc.py send_with_delay --pane_id $(tmux display -pt - \'#{{pane_id}}\')"',
        '',
        'New Telnet', 'q', f'run "{home}/tmuxNOC/scripts/tmux_noc.py setup_connection --connection_type telnet"',
        'New SSH', 's', f'run "{home}/tmuxNOC/scripts/tmux_noc.py setup_connection --connection_type ssh"',
    ]
    if ssh_hosts:
        command += [
            'SSH Config Hosts', 'S', f'run "{home}/tmuxNOC/scripts/tmux_noc.py ssh_menu"',
        ]
    if last_sessions is not None:
        command += last_sessions
    if clipboard is not None:
        command += clipboard
    subprocess.run(command)


def setup_connection(connection_type):
    home = str(Path.home())
    sessions_metadata = load_sessions_metadata()
    if f'last_{connection_type}_session' in sessions_metadata:
        hostname = sessions_metadata[f'last_{connection_type}_session']
    else:
        hostname = 'hostname'
    command = [
        'tmux',
        'command-prompt',
        '-p',
        f'{connection_type}:',
        '-I',
        hostname,
        f'run "{home}/tmuxNOC/scripts/tmux_noc.py connect_{connection_type} --host \'%1\'"'
    ]
    subprocess.run(command)


def connect_telnet(host):
    home = str(Path.home())
    subprocess.run(
        [
            'tmux',
            'new-window',
            '-n', f't/{host}',
            f'PROMPT_COMMAND="{home}/tmuxNOC/scripts/kbdfix.sh telnet {host}";TERM=vt100-w bash \
              --rcfile {home}/tmuxNOC/misc/tmux_noc_bashrc'
        ]
    )
    save_session('telnet', host)
    pane_log('t', host)

def connect_ssh(host):
    home = str(Path.home())
    subprocess.run(
        [
            'tmux',
            'new-window',
            '-n', f's/{host}',
            f'PROMPT_COMMAND="ssh {host}" bash --rcfile {home}/tmuxNOC/misc/tmux_noc_bashrc'
        ]
    )
    save_session('ssh', host)
    pane_log('s', host)


def tmux_send(string, conformation_symbol='Enter', target_pane=':'):
    subprocess.run(
        ['tmux', 'send-keys', '-t', target_pane, string, f'{conformation_symbol}'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


def tmux_wait_for(string, timeout=3):
    found = False
    for _ in range(timeout*10):
        screen_content_b = subprocess.run([
            'tmux',
            'capture-pane',
            '-J',
            '-p'
        ], stdout=subprocess.PIPE).stdout
        screen_content_list = screen_content_b.decode('UTF-8').split('\n')
        screen_content_list_filtered = [line for line in screen_content_list if len(line) != 0]
        for line in screen_content_list_filtered[-2:]:
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


def send_with_delay(pane_id):
    print(f'{ANSIColors.WARNING}What to send? To end list enter a single dot{ANSIColors.ENDC}\n.')
    commands, s = [], ''
    while s != '.':
        s = input()
        if s != '.':
            commands.append(s)
    while True:
        try:
            line_delay = input(
                f'{ANSIColors.WARNING}Enter LINE delay in milliseconds [500]: {ANSIColors.ENDC}'
            ) or 500
            line_delay = int(line_delay)
        except ValueError:
            print(f'{ANSIColors.FAIL}Enter an integer.{ANSIColors.ENDC}')
            continue
        if line_delay < 0:
            print(f'{ANSIColors.FAIL}Enter a positive integer or 0.{ANSIColors.ENDC}')
            continue
        else:
            break
    while True:
        try:
            character_delay = input(
                f'{ANSIColors.WARNING}Enter CHARACTER delay in milliseconds [0]: {ANSIColors.ENDC}'
            ) or 0
            character_delay = int(character_delay)
        except ValueError:
            print(f'{ANSIColors.FAIL}Enter an integer.{ANSIColors.ENDC}')
            continue
        if character_delay < 0:
            print(f'{ANSIColors.FAIL}Enter a positive integer or 0.{ANSIColors.ENDC}')
            continue
        else:
            break

    rows, columns = subprocess.check_output(['stty', 'size']).decode().split()
    rows = int(rows) - 2
    rows_offset = 0
    for index, command in enumerate(commands):
        subprocess.call('clear', shell=True)
        if len(commands) > rows:
            if index > 5:
                rows_offset = index - 5
        print('\n'.join(commands[rows_offset:index]))
        print(f'{ANSIColors.OKGREEN}{ANSIColors.BOLD}{command}{ANSIColors.ENDC}')
        print('\n'.join(commands[index + 1:rows + rows_offset]))

        if character_delay > 0:
            characters = list(command)
            for character in characters:
                tmux_send(character, '', pane_id)
                time.sleep(character_delay / 1000)
            tmux_send('', 'Enter', pane_id)
        else:
            tmux_send(command, target_pane=pane_id)
        if not index + 1 == len(commands):
            time.sleep(line_delay / 1000)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Connect to telnet or ssh from tmux.')
    parser.add_argument('type', choices=[
        'login',
        'send_with_delay',
        'noc_menu',
        'ssh_menu',
        'setup_connection',
        'connect_telnet',
        'connect_ssh',
        'toggle_log',
        'save_pane_history',
        'search_logs',
        'open_log',
    ])
    parser.add_argument('--login_number', nargs='?')
    parser.add_argument('--host', nargs='?')
    parser.add_argument('--connection_type', nargs='?')
    parser.add_argument('--pane_id', nargs='?')
    parser.add_argument('--file_name', nargs='?')
    parser.add_argument(
        '-i',
        '--input',
        type=argparse.FileType('r'),
        default=(None if sys.stdin.isatty() else sys.stdin)
    )
    parser.add_argument('--history_index', nargs='?')
    args = parser.parse_args()

    if args.type == 'login':
        send_login_pwd(args.login_number)
    elif args.type == 'send_with_delay':
        send_with_delay(args.pane_id)
    elif args.type == 'noc_menu':
        noc_menu()
    elif args.type == 'ssh_menu':
        ssh_menu()
    elif args.type == 'setup_connection':
        setup_connection(args.connection_type)
    elif args.type == 'connect_telnet':
        connect_telnet(args.host)
    elif args.type == 'connect_ssh':
        connect_ssh(args.host)
    elif args.type == 'toggle_log':
        pane_log('l', 'local')
    elif args.type == 'save_pane_history':
        save_pane_history(args.file_name, args.pane_id, args.input)
    elif args.type == 'search_logs':
        search_logs()
    elif args.type == 'open_log':
        open_log(args.history_index)
