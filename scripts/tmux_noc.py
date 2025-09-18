#!/usr/bin/env python3
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time
from errno import EEXIST
from pathlib import Path
from typing import Callable, NamedTuple


class AC:
    """ANSI Colors."""

    PURPLE = "\033[95m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    END = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class LP:
    """Local Paths."""

    home = Path.home()
    tmux_noc = home / "tmuxNOC"
    # Scripts
    scripts_dir = tmux_noc / "scripts"
    script = scripts_dir / "tmux_noc.py"
    paste = scripts_dir / "paste.sh"
    # Local
    local_dir = tmux_noc / "local"
    log_dir = local_dir / "log"
    sessions_metadata = local_dir / "sessions.json"
    sessions_history = local_dir / "sessions_history.log"
    logins = local_dir / ".logins"


def create_dir(filename):
    """Creates path for file, if directories doesn't exists."""
    if not os.path.exists(os.path.dirname(filename)):
        try:
            os.makedirs(os.path.dirname(filename))
        except OSError as exc:  # Guard against race condition
            if exc.errno != EEXIST:
                raise


def get_split_command(split_direction):
    """What commands to use in what situation."""
    if split_direction == "vertical":
        return ["tmux", "split-window", "-v"]
    if split_direction == "horizontal":
        return ["tmux", "split-window", "-h"]
    if split_direction == "reopen":
        return ["tmux", "respawn-pane", "-k"]
    return ["tmux", "new-window"]


def save_pane_history(output_file_name, pane_id=":", pipe="o", only_once=False):
    """Saves whole pane history to a file."""
    for _ in pipe:
        output = subprocess.check_output(
            ["tmux", "capture-pane", "-J", "-p", "-S", "-20000", "-t", pane_id], encoding="UTF-8"
        )
        if output == "":
            continue
        with open(output_file_name, "w") as f:
            f.write(output)
        if only_once:
            break
        time.sleep(1)


def pane_log(connection_type, host, restart=False):
    """Toggle pane log."""
    sessions_metadata = load_sessions_metadata()
    last_session_index = "--" if connection_type == "l" else sessions_metadata["last_session_index"]
    year = datetime.datetime.now().strftime("%Y")
    month = datetime.datetime.now().strftime("%m")
    day = datetime.datetime.now().strftime("%d")
    current_time = datetime.datetime.now().strftime("%H_%M_%S")
    log_filename = (
        f"{LP.log_dir}/{year}/{month}/{day}/{current_time}---!{last_session_index}_{connection_type}_{host}.log"
    )
    create_dir(log_filename)

    subprocess.run(
        [
            "tmux",
            "pipe-pane",
            "-o",
            f'{LP.script} save_pane_history --file_name "{log_filename}" --pane_id #{{pane_id}} -i -',
        ],
        check=True,
    )
    if restart:
        subprocess.run(
            [
                "tmux",
                "pipe-pane",
                "-o",
                f'{LP.script} save_pane_history --file_name "{log_filename}" --pane_id #{{pane_id}} -i -',
            ],
            check=True,
        )


def search_logs():
    """Grep in log directory."""
    rename_window()
    query = input(f"{AC.YELLOW}grep in logs:{AC.END} ")
    if not query.isspace() and query != "":
        subprocess.run(
            ["grep", "--color=always", "-n", "-r", query, "."], cwd=f"{LP.home}/tmuxNOC/local/log/", check=True
        )
    else:
        print(f"{AC.RED}Empty query.{AC.END}")
    search_logs()


def tmux_dm(message: str) -> None:
    """Display message in status line."""
    subprocess.run(["tmux", "display-message", message], check=True)


def tmux_set_pane_name(name):
    """Setting pane name."""
    subprocess.run(["tmux", "set", "-p", "@pane_name", name], check=True)


def open_log(history_index, split_direction):
    """Open log file in less."""
    log_file = None
    for path in Path(LP.log_dir).rglob(f"*!{history_index}*"):
        log_file = str(path)
    if log_file is None:
        tmux_dm(f"Log file with index {history_index} not found.")
    else:
        log_file_short = log_file.replace(LP.log_dir + "/", "")
        subprocess.run([*get_split_command(split_direction), f'less -m "{log_file}"'], check=True)
        tmux_set_pane_name(f"Log:{log_file_short}")
        rename_window()


def load_sessions_metadata():
    if not os.path.exists(LP.sessions_metadata):
        return {}
    with open(LP.sessions_metadata, "r") as f:
        return json.load(f)


def save_session(connection_type, host):
    """Saves information about session and updates metadata."""
    sessions_metadata = load_sessions_metadata()
    if "last_session_index" in sessions_metadata:
        sessions_metadata["last_session_index"] += 1
    else:
        sessions_metadata["last_session_index"] = 1
    if "last_five_sessions" in sessions_metadata:
        last_five_sessions = sessions_metadata["last_five_sessions"]
        if host not in str(last_five_sessions):
            if len(last_five_sessions) >= 5:
                last_five_sessions.pop(4)
            last_five_sessions.insert(0, {"connection_type": connection_type, "host": host})
        else:
            last_connection = None
            for index, session in enumerate(last_five_sessions):
                if connection_type == session["connection_type"] and host == session["host"]:
                    last_connection = index
            if last_connection is None:
                if len(last_five_sessions) >= 5:
                    last_five_sessions.pop(4)
                last_five_sessions.insert(0, {"connection_type": connection_type, "host": host})
            else:
                last_five_sessions.pop(last_connection)
                last_five_sessions.insert(0, {"connection_type": connection_type, "host": host})

    else:
        last_five_sessions = [{"connection_type": connection_type, "host": host}]
    sessions_metadata["last_five_sessions"] = last_five_sessions
    sessions_metadata[f"last_{connection_type}_session"] = host
    with open(LP.sessions_metadata, "w") as f:
        json.dump(sessions_metadata, f)

    if not os.path.exists(LP.sessions_history):
        create_dir(LP.sessions_history)
        with open(LP.sessions_history, "w"):
            pass
    with open(LP.sessions_history, "r+") as sessions_history_file:
        sessions_history = sessions_history_file.read()
        current_date = datetime.datetime.now().strftime("%d.%m.%Y")
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        if f"# {current_date}" not in sessions_history:
            sessions_history_file.write(f"# {current_date}\n")
        sessions_history_file.write(
            f"    {sessions_metadata['last_session_index']} {current_date} {current_time} {connection_type} {host}\n"
        )


def ssh_config_hosts():
    """Get .ssh/config hosts. Return list of hostnames."""
    if not os.path.exists(f"{LP.home}/.ssh/config"):
        return None

    with open(f"{LP.home}/.ssh/config") as f:
        ssh_config = f.read().splitlines()
    return [line.replace("Host ", "") for line in ssh_config if line.startswith("Host")]


def short_word(word):
    """This is for tmux menus.

    Tmux menu will not show, if it's content is to big for terminal window.
    This function shortens words for them to fit in window.
    """
    terminal_width = int(subprocess.check_output(["tmux", "display-message", "-p", "#{window_width}"]))

    word_short = word[:50] + "..." if len(word) > 53 else word
    if len(word_short) >= terminal_width:
        word_short = word_short[: terminal_width - 20] + "..."

    return word_short


def ssh_menu(split_direction):
    """Show ssh menu with hosts from .ssh/config."""
    command = [
        "tmux",
        "display-menu",
        "-T",
        "#[align=centre]SSH Config Hosts",
        "-x",
        "P",
        "-y",
        "S",
    ]
    ssh_hosts_list = ssh_config_hosts()
    if ssh_hosts_list is not None:
        for index, host in enumerate(ssh_hosts_list):
            index += 1
            if index == 10:
                index = 0
            elif 20 > index > 10:
                index = f"M-{index - 10}"
            elif index == 20:
                index = "M-0"
            elif 30 > index > 20:
                index = f"C-{index - 20}"
            elif index == 30:
                index = "C-0"
            command += [
                short_word(host),
                str(index),
                (f"run \"{LP.script} connect_ssh --host '{host}' --split_direction {split_direction}\""),
            ]
    subprocess.run(command, check=True)


def clipboard_menu(split_direction):
    """Show menu with options to connect to first word in clipboard."""
    clipboard_first_line = subprocess.check_output(LP.paste, encoding="UTF-8").split("\n")[0]
    clipboard_first_word = [word for word in clipboard_first_line.replace("\t", "").split(" ") if len(word) != 0]
    if len(clipboard_first_word) != 0:
        clipboard_first_word = clipboard_first_word[0]
        clipboard_first_word_short = short_word(clipboard_first_word)
        subprocess.run(
            [
                "tmux",
                "display-menu",
                "-T",
                "#[align=centre]Clipboard",
                "-x",
                "P",
                "-y",
                "S",
                f"telnet {clipboard_first_word_short}",
                "v",
                (
                    f'run "{LP.script} connect_telnet '
                    f"--host '{clipboard_first_word}' --split_direction {split_direction}\""
                ),
                f"jtelnet {clipboard_first_word_short}",
                "J",
                (
                    f'run "{LP.script} connect_jtelnet '
                    f"--host '{clipboard_first_word}' --split_direction {split_direction}\""
                ),
                f"ssh {clipboard_first_word_short}",
                "V",
                (
                    f'run "{LP.script} connect_ssh '
                    f"--host '{clipboard_first_word}' --split_direction {split_direction}\""
                ),
            ],
            check=True,
        )
    else:
        tmux_dm("No content in clipboard.")


def move_pane_window(split_direction):
    """Menu for moving pane to another window."""
    if split_direction == "vertical":
        split_argument = "-h"
    elif split_direction == "horizontal":
        split_argument = "-v"
    else:
        return

    windows_list = subprocess.check_output(
        ["tmux", "list-windows", "-F", "#I&&&#W&&&#{window_id}"], encoding="utf-8"
    ).split("\n")[:-1]

    windows_menu = []
    for window in windows_list:
        index, name, _id = window.split("&&&")
        windows_menu.append(f"{index}:{short_word(name)}")
        if int(index) < 10:
            windows_menu.append(index)
        else:
            windows_menu.append("")
        windows_menu.append(f'join-pane {split_argument} -t {_id}; run "{LP.script} rename_windows"')

    subprocess.run(
        [
            "tmux",
            "display-menu",
            "-T",
            "#[align=centre]Move Pane to:",
            "-x",
            "P",
            "-y",
            "S",
            *windows_menu,
        ],
        check=True,
    )


def noc_menu(split_direction="new"):
    """Show main tmuxNOC menu."""
    script_path = LP.script

    sessions_metadata = load_sessions_metadata()
    if "last_five_sessions" in sessions_metadata:
        last_five_sessions = sessions_metadata["last_five_sessions"]
        last_sessions_menu_block = [""]
        for index, session in enumerate(last_five_sessions):
            connection_type = session["connection_type"]
            host = session["host"]
            host_short = short_word(host)
            last_sessions_menu_block.append(f"{connection_type} {host_short}")
            last_sessions_menu_block.append(f"{index + 1}")
            last_sessions_menu_block.append(
                (f"run \"{script_path} connect_{connection_type} --host '{host}' --split_direction {split_direction}\"")
            )
    else:
        last_sessions_menu_block = None

    if split_direction == "vertical":
        split_command = "split-window -v"
        split_name = "Vertical"
        split_variants = [
            "Split Horizontal",
            "\\",
            f'run "{script_path} noc_menu --split_direction horizontal"',
            "Open in New Window",
            "n",
            f'run "{script_path} noc_menu --split_direction new"',
            "Open in Current Pane",
            "r",
            f'run "{script_path} noc_menu --split_direction reopen"',
            "",
        ]
    elif split_direction == "horizontal":
        split_command = "split-window -h"
        split_name = "Horizontal"
        split_variants = [
            "Split Vertical",
            "-",
            f'run "{script_path} noc_menu --split_direction vertical"',
            "Open in New Window",
            "n",
            f'run "{script_path} noc_menu --split_direction new"',
            "Open in Current Pane",
            "r",
            f'run "{script_path} noc_menu --split_direction reopen"',
            "",
        ]
    elif split_direction == "reopen":
        split_command = "respawn-pane -k"
        split_name = "Open in Current Pane"
        split_variants = [
            "Split Vertical",
            "-",
            f'run "{script_path} noc_menu --split_direction vertical"',
            "Split Horizontal",
            "\\",
            f'run "{script_path} noc_menu --split_direction horizontal"',
            "Open in New Window",
            "n",
            f'run "{script_path} noc_menu --split_direction new"',
            "",
        ]
    else:
        split_command = "new-window"
        split_name = "New Window"
        split_variants = [
            "Split Vertical",
            "-",
            f'run "{script_path} noc_menu --split_direction vertical"',
            "Split Horizontal",
            "\\",
            f'run "{script_path} noc_menu --split_direction horizontal"',
            "Open in Current Pane",
            "r",
            f'run "{script_path} noc_menu --split_direction reopen"',
            "",
        ]

    command = [
        "tmux",
        "display-menu",
        "-T",
        f"#[align=centre]NOC {split_name}",
        "-x",
        "P",
        "-y",
        "S",
        *split_variants,
        "Move Pane to Window - Vertical",
        "m",
        f'run "{script_path} move_pane_window --split_direction vertical"',
        "Move Pane to Window - Horizontal",
        "M",
        f'run "{script_path} move_pane_window --split_direction horizontal"',
        "",
        # -----
        "Show Sessions History",
        "h",
        (
            f'{split_command} "less +G $HOME/tmuxNOC/local/sessions_history.log"; '
            f'set -p @pane_name "Sessions History"; run "{script_path} rename_window"'
        ),
        "Open Log File",
        "l",
        (
            f'command-prompt -p "Open Log Number:" \'run "{script_path} open_log '
            f"--history_index %1 --split_direction {split_direction}\"'"
        ),
        "Search in Logs",
        "L",
        f'{split_command} "{script_path} search_logs"; set -p @pane_name "grep in logs"',
        # -----
    ]
    command += [
        # -----
        "",
        "Connect from Clipboard",
        "v",
        f'run "{script_path} clipboard_menu --split_direction {split_direction}"',
        "New Telnet",
        "q",
        (f'run "{script_path} setup_connection --connection_type telnet --split_direction {split_direction}"'),
        "New Jump Telnet",
        "J",
        (f'run "{script_path} setup_connection --connection_type jtelnet --split_direction {split_direction}"'),
        "New SSH",
        "s",
        (f'run "{script_path} setup_connection --connection_type ssh --split_direction {split_direction}"'),
    ]
    if ssh_config_hosts():
        command += [
            "SSH Config Hosts",
            "S",
            f'run "{script_path} ssh_menu --split_direction {split_direction}"',
        ]
    if last_sessions_menu_block is not None:
        command += last_sessions_menu_block
    subprocess.run(command, check=True)


def setup_connection(connection_type, split_direction):
    """Showing connection prompt."""
    sessions_metadata = load_sessions_metadata()
    if f"last_{connection_type}_session" in sessions_metadata:
        hostname = sessions_metadata[f"last_{connection_type}_session"]
    else:
        hostname = ""
    command = [
        "tmux",
        "command-prompt",
        "-p",
        f"{connection_type}:",
        "-I",
        hostname,
        (f"run \"{LP.script} connect_{connection_type} --host '%1' --split_direction {split_direction}\""),
    ]
    subprocess.run(command, check=True)


def connect_telnet(host, split_direction):
    home = LP.home
    subprocess.run(
        [
            *get_split_command(split_direction),
            f'PROMPT_COMMAND="{home}/tmuxNOC/scripts/kbdfix.sh telnet {host}" TERM=vt100-w bash \
              --rcfile {home}/tmuxNOC/misc/tmux_noc_bashrc',
        ],
        check=True,
    )
    tmux_set_pane_name(f"t/{host}")
    rename_window()
    save_session("telnet", host)
    if split_direction == "reopen":
        pane_log("t", host, restart=True)
    else:
        pane_log("t", host)


def connect_jtelnet(host, split_direction):
    """Connect to telnet via ssh jump host."""
    jump_host = read_jump_host()
    if not jump_host:
        return
    home = LP.home
    subprocess.run(
        [
            *get_split_command(split_direction),
            f'PROMPT_COMMAND="ssh {jump_host} -o ServerAliveInterval=300 -t \'/bin/bash -ilc \\"telnet {host}\\"\'" \
              TERM=vt100-w bash --rcfile {home}/tmuxNOC/misc/tmux_noc_bashrc',
        ],
        check=True,
    )
    tmux_set_pane_name(f"jt/{host}")
    rename_window()
    save_session("jtelnet", host)
    if split_direction == "reopen":
        pane_log("jt", host, restart=True)
    else:
        pane_log("jt", host)


def yes_no(question: str) -> bool:
    """Prompt the yes/no-*question* to the user."""
    while True:
        user_input = input(question + " [Y/n]: ")
        if user_input == "":
            return True
        if "yes".startswith(user_input.lower()):
            return True
        if "no".startswith(user_input.lower()):
            return False
        print("It's yes or no question.\n")


def prompt_for_ssh_login(host):
    use_kbdfix = yes_no("Use kbdfix.sh and VT100 terminal?")
    username = input("Username: ")
    connect_ssh(host, "reopen", use_kbdfix, username)


def connect_ssh(host, split_direction, use_kbdfix=None, username=None):
    home = LP.home
    script = LP.script

    prompt_for_login = not (host in ssh_config_hosts() or "@" in host)

    if prompt_for_login and use_kbdfix is None:
        subprocess.run(
            [*get_split_command(split_direction), f'bash -c "{script} prompt_for_ssh_login --host {host}"'], check=True
        )
    elif use_kbdfix is not None:
        if use_kbdfix:
            command = f'PROMPT_COMMAND="{home}/tmuxNOC/scripts/kbdfix.sh ssh -o ServerAliveInterval=300 \
                        -o StrictHostKeyChecking=no -l {username} {host}" TERM=vt100-w bash --rcfile \
                        {home}/tmuxNOC/misc/tmux_noc_bashrc'
        else:
            command = f'PROMPT_COMMAND="ssh -o ServerAliveInterval=300 -o StrictHostKeyChecking=no \
                        -l {username} {host}" bash --rcfile {home}/tmuxNOC/misc/tmux_noc_bashrc'
        subprocess.run([*get_split_command(split_direction), command], check=True)
    else:
        command = f'PROMPT_COMMAND="ssh -o ServerAliveInterval=300 -o StrictHostKeyChecking=no {host}" \
                    bash --rcfile {home}/tmuxNOC/misc/tmux_noc_bashrc'
        subprocess.run([*get_split_command(split_direction), command], check=True)
    tmux_set_pane_name(f"s/{host}")
    rename_window()
    save_session("ssh", host)
    if split_direction == "reopen":
        pane_log("s", host, restart=True)
    else:
        pane_log("s", host)


def rename_window(window_id=":"):
    """Names windows according to pane name. If user option @window_title is set for window it won't be renamed."""
    if window_id is None:
        window_id = ":"

    window_title = subprocess.check_output(["tmux", "show", "-t", window_id, "-w", "@window_title"], encoding="UTF-8")
    if window_title:
        return

    panes_list = subprocess.check_output(
        ["tmux", "list-panes", "-t", window_id, "-F", "#{@pane_name}"], encoding="UTF-8"
    ).split("\n")[:-1]
    rename = False
    window_name = []
    for pane_name in panes_list:
        if pane_name == "":
            window_name.append("local")
        else:
            rename = True
            window_name.append(pane_name)
    if rename:
        subprocess.run(["tmux", "rename-window", "-t", window_id, "\u2503".join(window_name)], check=True)
    else:
        subprocess.run(["tmux", "set", "-w", "-t", window_id, "automatic-rename", "on"], check=True)


def rename_windows():
    """Rename all windows."""
    windows_list = subprocess.check_output(["tmux", "list-windows", "-F", "#{window_id}"], encoding="UTF-8").split(
        "\n"
    )[:-1]

    for window_id in windows_list:
        rename_window(window_id)


def tmux_send(string: str, conformation_symbol: str = "Enter", target_pane: str = ":") -> None:
    """Send string to the pane."""
    subprocess.run(["tmux", "send-keys", "-t", target_pane, string, f"{conformation_symbol}"], check=True)


def tmux_wait_for(string: str, timeout: float = 3.0, to_lower: bool = False) -> bool:
    """Wait for the string to show up in terminal.

    Returns true if string in the last 2 lines on the screen, else false.
    """
    for _ in range(int(timeout * 10)):  # Number of 0.1 ticks. 0.1 -> 1, 3.5 -> 35
        screen_content = [
            line
            for line in subprocess.check_output(["tmux", "capture-pane", "-J", "-p"], encoding="utf-8").splitlines()
            if len(line) != 0
        ]
        for line in screen_content[-2:]:
            if to_lower:
                line = line.lower()
            if string in line:
                return True
        time.sleep(0.1)

    return False


def read_jump_host():
    jump_host = ""
    if not os.path.exists(LP.logins):
        tmux_dm(f"File {LP.logins} doesn't exists.")
        return None
    with open(LP.logins, "r") as f:
        logins = f.readlines()
    for line in logins:
        if "JUMP=" in line:
            jump_host = line.replace("JUMP=", "").replace("\n", "")
    if not jump_host:
        tmux_dm(f"Jump host not found in {LP.logins}.")
        return None
    return jump_host


def send_login_pwd(login_number: int) -> None:
    """Send login/password sequence."""
    login, password = "", ""

    if not LP.logins.exists():
        tmux_dm(f"File {LP.logins} doesn't exists.")
        return
    with open(LP.logins, "r") as f:
        logins = f.read().splitlines()
    for line in logins:
        if line.startswith(f"LOGIN{login_number}"):
            login = line.replace(f"LOGIN{login_number}=", "")
        if line.startswith(f"PASS{login_number}") or line.startswith(f"PASSWORD{login_number}"):
            password = line.replace(f"PASS{login_number}=", "").replace(f"PASSWORD{login_number}=", "")
    if not login or not password:
        tmux_dm(f"Login-password pair {login_number} not found in {LP.logins}.")
        return
    if tmux_wait_for("assword", timeout=0.1, to_lower=True):
        # If password prompt available right away, send password only.
        tmux_send(password)
        return
    tmux_send(login)
    if tmux_wait_for("assword", to_lower=True):
        tmux_send(password)
    else:
        tmux_dm("Password prompt not found.")


class InteractiveTest:
    def __init__(self) -> None:
        self.keys_re = re.compile(r"`(.*?)`")

        print(f"{AC.BOLD}Welcome to the interactive test of tmuxNOC.{AC.END}")
        print(f"{AC.BOLD}It's meant to test it's functions and also show it's capabilities.{AC.END}")
        print("")

        if yes_no(f"{AC.YELLOW}Test login?{AC.END}"):
            self.test_login()

    def instruction(self, instruction: str) -> None:
        highlight_keys = self.keys_re.sub(rf"{AC.BOLD}{AC.UNDERLINE}\1{AC.END}{AC.PURPLE}", instruction)
        print(f"{AC.PURPLE}{highlight_keys}{AC.END}")

    def success(self) -> None:
        print(f"{AC.GREEN}SUCCESS{AC.END}")

    def fail(self, message: str, exit_call: Callable[[], None] | None = None) -> None:
        yn = yes_no(f"{AC.RED}FAIL: {message}. Continue other tests(y) or exit(n)?{AC.END}")
        if exit_call is not None:
            exit_call()
        if not yn:
            exit(1)

    ### TESTS
    def test_login(self) -> None:
        def cleanup() -> None:
            print("Deleting dummy logins.")
            LP.logins.unlink(missing_ok=True)
            if bk_logins.exists():
                print(f"Restoring {bk_logins} to {LP.logins}.")
                bk_logins.rename(LP.logins)

        class DummyLogin(NamedTuple):
            i: int
            login: str
            pwd: str

            def __str__(self) -> str:
                return f"LOGIN{self.i}={self.login}\nPASSWORD{self.i}={self.pwd}\n"

        print("Setting up login testing environment.")
        bk_logins = LP.local_dir / ".logins.bk"
        if LP.logins.exists():
            print(f"Moving {LP.logins} to {bk_logins}.")
            LP.logins.rename(bk_logins)

        dummy_logins = (DummyLogin(1, "admin", "password"), DummyLogin(2, "root", "1234"))
        print(f"Writing dummy logins to {LP.logins}.")
        LP.logins.write_text("".join(str(dummy_login) for dummy_login in dummy_logins))

        for dummy_login in dummy_logins:
            self.instruction(f"Testing LOGIN{dummy_login.i}. Press `Alt-{dummy_login.i}` to enter login/pwd pair.")
            if input("login: ") != dummy_login.login:
                self.fail(f"Login entered is not '{dummy_login.login}'", cleanup)
                return
            if input("password: ") != dummy_login.pwd:
                self.fail(f"Password entered is not '{dummy_login.pwd}'", cleanup)
                return

        dummy_login = dummy_logins[0]
        self.instruction("Testing bypassing login input if password field available at cursor. Press `Alt-1`.")
        if input("password: ") != dummy_login.pwd:
            self.fail(f"Password entered is not '{dummy_login.pwd}'", cleanup)
            return

        cleanup()
        self.success()


if __name__ == "__main__":
    LP.local_dir.mkdir(parents=True, exist_ok=True)
    parser = argparse.ArgumentParser(description="Connect to telnet or ssh from tmux.")
    parser.add_argument(
        "type",
        choices=[
            "login",
            "noc_menu",
            "ssh_menu",
            "clipboard_menu",
            "move_pane_window",
            "setup_connection",
            "connect_telnet",
            "connect_jtelnet",
            "connect_ssh",
            "toggle_log",
            "save_pane_history",
            "search_logs",
            "open_log",
            "rename_window",
            "rename_windows",
            "prompt_for_ssh_login",
            "interactive_test",
        ],
    )
    parser.add_argument("--login_number", type=int, nargs="?")
    parser.add_argument("--host", nargs="?")
    parser.add_argument("--connection_type", nargs="?")
    parser.add_argument("--pane_id", nargs="?")
    parser.add_argument("--window_id", nargs="?")
    parser.add_argument("--split_direction", nargs="?")
    parser.add_argument("--file_name", nargs="?")
    parser.add_argument(
        "-i", "--input", type=argparse.FileType("r"), default=(None if sys.stdin.isatty() else sys.stdin)
    )
    parser.add_argument("--history_index", nargs="?")
    args = parser.parse_args()

    if args.type == "login":
        send_login_pwd(args.login_number)
    elif args.type == "noc_menu":
        noc_menu(args.split_direction)
    elif args.type == "ssh_menu":
        ssh_menu(args.split_direction)
    elif args.type == "clipboard_menu":
        clipboard_menu(args.split_direction)
    elif args.type == "move_pane_window":
        move_pane_window(args.split_direction)
    elif args.type == "setup_connection":
        setup_connection(args.connection_type, args.split_direction)
    elif args.type == "connect_telnet":
        connect_telnet(args.host, args.split_direction)
    elif args.type == "connect_jtelnet":
        connect_jtelnet(args.host, args.split_direction)
    elif args.type == "connect_ssh":
        connect_ssh(args.host, args.split_direction)
    elif args.type == "toggle_log":
        pane_log("l", "local")
    elif args.type == "save_pane_history":
        save_pane_history(args.file_name, args.pane_id, args.input)
    elif args.type == "search_logs":
        search_logs()
    elif args.type == "open_log":
        open_log(args.history_index, args.split_direction)
    elif args.type == "rename_window":
        rename_window(args.window_id)
    elif args.type == "rename_windows":
        rename_windows()
    elif args.type == "prompt_for_ssh_login":
        prompt_for_ssh_login(args.host)
    elif args.type == "interactive_test":
        InteractiveTest()
