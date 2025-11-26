#!/usr/bin/env python3
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, NamedTuple


##############
### Config ###
##############
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


####################
### Menu Helpers ###
####################
class MenuEntry(NamedTuple):
    """Tmux Menu Entry."""

    text: str
    key: str
    cmd: str


def menu_text(message: str, styles: str = "") -> MenuEntry:
    tmux_styles = "".join(f"#[{style.strip()}]" for style in styles.split(","))

    return MenuEntry(f"-#[nodim]{tmux_styles}{message}", "", "")


def menu_subheader(text: str) -> MenuEntry:
    return menu_text(text, styles="align=centre,bold,nodim")


MENU_DELIMITER = ("",)
MENU_EMPTY_LINE = menu_text("")


#######################
### General Helpers ###
#######################
def h_get_split_command(split_direction: str) -> list[str]:
    """What commands to use in what situation."""
    if split_direction == "vertical":
        return ["tmux", "split-window", "-v"]
    if split_direction == "horizontal":
        return ["tmux", "split-window", "-h"]
    if split_direction == "reopen":
        return ["tmux", "respawn-pane", "-k"]
    return ["tmux", "new-window"]


def h_load_sessions_metadata() -> dict[str, Any]:
    if not os.path.exists(LP.sessions_metadata):
        return {}
    with open(LP.sessions_metadata, "r") as f:
        return json.load(f)


def h_save_session(connection_type: str, host: str) -> None:
    """Saves information about session and updates metadata."""
    sessions_metadata = h_load_sessions_metadata()
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

    LP.sessions_history.parent.mkdir(parents=True, exist_ok=True)
    LP.sessions_history.touch(exist_ok=True)
    with open(LP.sessions_history, "r+") as sessions_history_file:
        sessions_history = sessions_history_file.read()
        current_date = datetime.datetime.now().strftime("%d.%m.%Y")
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        if f"# {current_date}" not in sessions_history:
            sessions_history_file.write(f"# {current_date}\n")
        sessions_history_file.write(
            f"    {sessions_metadata['last_session_index']} {current_date} {current_time} {connection_type} {host}\n"
        )


def h_ssh_config_hosts() -> list[str]:
    """Get .ssh/config hosts. Return list of hostnames."""
    if not os.path.exists(f"{LP.home}/.ssh/config"):
        return []

    with open(f"{LP.home}/.ssh/config") as f:
        ssh_config = f.read().splitlines()
    return [line.replace("Host ", "") for line in ssh_config if line.startswith("Host")]


def h_short_word(word: str) -> str:
    """This is for tmux menus.

    Tmux menu will not show, if it's content is to big for terminal window.
    This function shortens words for them to fit in window.
    """
    terminal_width = int(subprocess.check_output(["tmux", "display-message", "-p", "#{window_width}"]))

    word_short = word[:50] + "..." if len(word) > 53 else word
    if len(word_short) >= terminal_width:
        word_short = word_short[: terminal_width - 20] + "..."

    return word_short


def h_index_to_key(index: int) -> str:
    key = str(index)
    if index == 10:
        key = "0"
    elif 20 > index > 10:
        key = f"M-{index - 10}"
    elif index == 20:
        key = "M-0"
    elif 30 > index > 20:
        key = f"C-{index - 20}"
    elif index == 30:
        key = "C-0"
    return key


def h_yes_no(question: str) -> bool:
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


####################
### Tmux Helpers ###
####################
def tmux_dm(message: str) -> None:
    """Display message in status line."""
    subprocess.run(["tmux", "display-message", message], check=True)


def tmux_set_pane_name(name: str) -> None:
    """Setting pane name."""
    subprocess.run(["tmux", "set", "-p", "@pane_name", name], check=True)


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


################
### Commands ###
################
def cmd_login(login_number: int) -> None:
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


def cmd_noc_menu(split_direction: str = "new") -> None:
    """Show main tmuxNOC menu."""
    split_hor_entry = MenuEntry("Horizontal Pane", "\\", f'run "{LP.script} noc_menu --split_direction horizontal"')
    split_vert_entry = MenuEntry("Vertical Pane", "-", f'run "{LP.script} noc_menu --split_direction vertical"')
    reopen_entry = MenuEntry("Current Pane", "r", f'run "{LP.script} noc_menu --split_direction reopen"')
    new_window_entry = MenuEntry("New Window", "n", f'run "{LP.script} noc_menu --split_direction new"')

    split_submenu = [*menu_subheader("New Session Location")]
    if split_direction == "vertical":
        split_command = "split-window -v"
        split_submenu += [
            *menu_text("Current location: #[underscore]Vertical Pane"),
            *MENU_EMPTY_LINE,
            *split_hor_entry,
            *new_window_entry,
            *reopen_entry,
        ]
    elif split_direction == "horizontal":
        split_command = "split-window -h"
        split_submenu += [
            *menu_text("Current location: #[underscore]Horizontal Pane"),
            *MENU_EMPTY_LINE,
            *split_vert_entry,
            *new_window_entry,
            *reopen_entry,
        ]
    elif split_direction == "reopen":
        split_command = "respawn-pane -k"
        split_submenu += [
            *menu_text("Current location: #[underscore]Current Pane"),
            *MENU_EMPTY_LINE,
            *split_vert_entry,
            *split_hor_entry,
            *new_window_entry,
        ]
    else:
        split_command = "new-window"
        split_submenu += [
            *menu_text("Current location: #[underscore]New Window"),
            *MENU_EMPTY_LINE,
            *split_vert_entry,
            *split_hor_entry,
            *reopen_entry,
        ]

    misc_menu = [
        *menu_subheader("Miscellaneous"),
        *MENU_EMPTY_LINE,
        *MenuEntry(
            "Show Sessions History",
            "h",
            (
                f'{split_command} "less +G $HOME/tmuxNOC/local/sessions_history.log"; '
                f'set -p @pane_name "Sessions History"; run "{LP.script} rename_window"'
            ),
        ),
    ]

    session_menu = [
        *menu_subheader("Create New Session"),
        *MENU_EMPTY_LINE,
        *MenuEntry(
            "New Telnet",
            "q",
            (f'run "{LP.script} setup_connection --connection_type telnet --split_direction {split_direction}"'),
        ),
        *MenuEntry(
            "New SSH",
            "s",
            (f'run "{LP.script} setup_connection --connection_type ssh --split_direction {split_direction}"'),
        ),
    ]
    if h_ssh_config_hosts():
        session_menu.extend(
            MenuEntry("SSH Config Hosts", "S", f'run "{LP.script} ssh_menu --split_direction {split_direction}"')
        )

    ### Add last 5 opened sessions to the end of menu
    history_menu = [
        *menu_subheader("Recent Sessions"),
        *MENU_EMPTY_LINE,
    ]
    last_sessions = h_load_sessions_metadata().get("last_five_sessions", [])
    if not last_sessions:
        history_menu.extend(menu_text("No recent sessions", styles="align=centre,dim"))
    for session_index, session in enumerate(last_sessions, start=1):
        connection_type: str = session["connection_type"]
        host: str = session["host"]
        host_short = h_short_word(host)
        history_menu.extend(
            MenuEntry(
                f"{connection_type} {host_short}",
                str(session_index),
                f"run \"{LP.script} connect_{connection_type} --host '{host}' --split_direction {split_direction}\"",
            )
        )

    tmux_cmd = ["tmux", "display-menu", "-T", "#[align=centre]NOC Menu", "-x", "P", "-y", "S"]
    full_menu = [
        *MENU_DELIMITER,
        *split_submenu,
        *MENU_DELIMITER,
        *session_menu,
        *MENU_DELIMITER,
        *misc_menu,
        *MENU_DELIMITER,
        *history_menu,
    ]

    subprocess.run([*tmux_cmd, *full_menu], check=True)


def cmd_tmux_menu() -> None:
    move_submenu = [
        *menu_subheader("Move Pane to Other Window"),
        *MENU_EMPTY_LINE,
        *MenuEntry(
            "Move Vertically",
            "m",
            f'run "{LP.script} move_pane_window --split_direction vertical"',
        ),
        *MenuEntry(
            "Move Horizontally",
            "M",
            f'run "{LP.script} move_pane_window --split_direction horizontal"',
        ),
    ]
    menu = [
        *MENU_DELIMITER,
        *move_submenu,
    ]
    tmux_cmd = ["tmux", "display-menu", "-T", "#[align=centre]Tmux Menu", "-x", "P", "-y", "S"]
    subprocess.run([*tmux_cmd, *menu], check=True)


def cmd_ssh_menu(split_direction: str) -> None:
    """Show ssh menu with hosts from .ssh/config."""
    tmux_cmd = ["tmux", "display-menu", "-T", "#[align=centre]SSH Config Hosts", "-x", "P", "-y", "S"]
    menu: list[str] = []
    ssh_hosts_list = h_ssh_config_hosts()
    if not ssh_hosts_list:
        return

    for index, host in enumerate(ssh_hosts_list, start=1):
        menu.extend(
            MenuEntry(
                h_short_word(host),
                h_index_to_key(index),
                f"run \"{LP.script} connect_ssh --host '{host}' --split_direction {split_direction}\"",
            )
        )
    subprocess.run([*tmux_cmd, *menu], check=True)


def cmd_move_pane_window(split_direction: str) -> None:
    """Menu for moving pane to another window."""
    if split_direction == "vertical":
        split_argument = "-h"
    elif split_direction == "horizontal":
        split_argument = "-v"
    else:
        return

    # &&& is delimiter between values, to try not conflict with any value in pane names
    windows_list = subprocess.check_output(
        ["tmux", "list-windows", "-F", "#I&&&#W&&&#{window_id}"], encoding="utf-8"
    ).split("\n")[:-1]

    menu: list[str] = []
    for window in windows_list:
        index, name, _id = window.split("&&&")
        menu.extend(
            MenuEntry(
                f"{index}:{h_short_word(name)}",
                h_index_to_key(int(index)),
                f'join-pane {split_argument} -t {_id}; run "{LP.script} rename_windows"',
            )
        )

    tmux_cmd = ["tmux", "display-menu", "-T", "#[align=centre]Move Pane to:", "-x", "P", "-y", "S"]
    subprocess.run([*tmux_cmd, *menu], check=True)


def cmd_setup_connection(connection_type: str, split_direction: str) -> None:
    """Showing connection prompt."""
    sessions_metadata = h_load_sessions_metadata()
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


def cmd_connect_telnet(host: str, split_direction: str) -> None:
    subprocess.run(
        [
            *h_get_split_command(split_direction),
            f'PROMPT_COMMAND="{LP.home}/tmuxNOC/scripts/kbdfix.sh telnet {host}" TERM=vt100-w bash \
              --rcfile {LP.home}/tmuxNOC/misc/tmux_noc_bashrc',
        ],
        check=True,
    )
    tmux_set_pane_name(f"t/{host}")
    cmd_rename_window()
    h_save_session("telnet", host)
    if split_direction == "reopen":
        cmd_pane_log("t", host, restart=True)
    else:
        cmd_pane_log("t", host)


def cmd_prompt_for_ssh_login(host: str) -> None:
    use_kbdfix = h_yes_no("Use kbdfix.sh and VT100 terminal?")
    username = input("Username: ")
    cmd_connect_ssh(host, "reopen", use_kbdfix, username)


def cmd_connect_ssh(
    host: str, split_direction: str, use_kbdfix: bool | None = None, username: str | None = None
) -> None:
    home = LP.home
    script = LP.script

    prompt_for_login = not (host in h_ssh_config_hosts() or "@" in host)

    if prompt_for_login and use_kbdfix is None:
        subprocess.run(
            [*h_get_split_command(split_direction), f'bash -c "{script} prompt_for_ssh_login --host {host}"'],
            check=True,
        )
    elif use_kbdfix is not None:
        if use_kbdfix:
            command = f'PROMPT_COMMAND="{home}/tmuxNOC/scripts/kbdfix.sh ssh -o ServerAliveInterval=300 \
                        -o StrictHostKeyChecking=no -l {username} {host}" TERM=vt100-w bash --rcfile \
                        {home}/tmuxNOC/misc/tmux_noc_bashrc'
        else:
            command = f'PROMPT_COMMAND="ssh -o ServerAliveInterval=300 -o StrictHostKeyChecking=no \
                        -l {username} {host}" bash --rcfile {home}/tmuxNOC/misc/tmux_noc_bashrc'
        subprocess.run([*h_get_split_command(split_direction), command], check=True)
    else:
        command = f'PROMPT_COMMAND="ssh -o ServerAliveInterval=300 -o StrictHostKeyChecking=no {host}" \
                    bash --rcfile {home}/tmuxNOC/misc/tmux_noc_bashrc'
        subprocess.run([*h_get_split_command(split_direction), command], check=True)
    tmux_set_pane_name(f"s/{host}")
    cmd_rename_window()
    h_save_session("ssh", host)
    if split_direction == "reopen":
        cmd_pane_log("s", host, restart=True)
    else:
        cmd_pane_log("s", host)


def cmd_pane_log(connection_type: str, host: str, restart: bool = False) -> None:
    """Toggle pane log."""
    sessions_metadata = h_load_sessions_metadata()
    last_session_index = "--" if connection_type == "l" else sessions_metadata["last_session_index"]
    year = datetime.datetime.now().strftime("%Y")
    month = datetime.datetime.now().strftime("%m")
    day = datetime.datetime.now().strftime("%d")
    current_time = datetime.datetime.now().strftime("%H_%M_%S")
    log_filename = (
        f"{LP.log_dir}/{year}/{month}/{day}/{current_time}---!{last_session_index}_{connection_type}_{host}.log"
    )
    Path(log_filename).parent.mkdir(parents=True, exist_ok=True)

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


def cmd_save_pane_history(output_file_name: str, pane_id: str = ":", pipe: str = "o", only_once: bool = False) -> None:
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


def cmd_rename_window(window_id: str = ":") -> None:
    """Names windows according to pane name. If user option @window_title is set for window it won't be renamed."""
    window_title = subprocess.check_output(
        ["tmux", "show", "-t", window_id, "-w", "-q", "@window_title"], encoding="UTF-8"
    )
    if window_title:
        return

    panes_list = subprocess.check_output(
        ["tmux", "list-panes", "-t", window_id, "-F", "#{@pane_name}"], encoding="UTF-8"
    ).splitlines()
    rename = False
    window_name = []
    for pane_name in panes_list:
        if not pane_name:
            window_name.append("local")
        else:
            rename = True
            window_name.append(pane_name)
    if rename:
        subprocess.run(["tmux", "rename-window", "-t", window_id, "\u2503".join(window_name)], check=True)
    else:
        subprocess.run(["tmux", "set", "-w", "-t", window_id, "automatic-rename", "on"], check=True)


def cmd_rename_windows() -> None:
    """Rename all windows."""
    windows_list = subprocess.check_output(
        ["tmux", "list-windows", "-F", "#{window_id}"], encoding="UTF-8"
    ).splitlines()

    for window_id in windows_list:
        cmd_rename_window(window_id)


class CmdInteractiveTest:
    def __init__(self) -> None:
        self.keys_re = re.compile(r"`(.*?)`")

        print(f"{AC.BOLD}Welcome to the interactive test of tmuxNOC.{AC.END}")
        print(f"{AC.BOLD}It's meant to test it's functions and also show it's capabilities.{AC.END}")
        print("")

        if h_yes_no(f"{AC.YELLOW}Test login?{AC.END}"):
            self.test_login()

    def instruction(self, instruction: str) -> None:
        highlight_keys = self.keys_re.sub(rf"{AC.BOLD}{AC.UNDERLINE}\1{AC.END}{AC.PURPLE}", instruction)
        print(f"{AC.PURPLE}{highlight_keys}{AC.END}")

    def success(self) -> None:
        print(f"{AC.GREEN}SUCCESS{AC.END}")

    def fail(self, message: str, exit_call: Callable[[], None] | None = None) -> None:
        yn = h_yes_no(f"{AC.RED}FAIL: {message}. Continue other tests(y) or exit(n)?{AC.END}")
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
            "tmux_menu",
            "ssh_menu",
            "move_pane_window",
            "setup_connection",
            "connect_telnet",
            "prompt_for_ssh_login",
            "connect_ssh",
            "toggle_log",
            "save_pane_history",
            "rename_window",
            "rename_windows",
            "interactive_test",
        ],
    )
    parser.add_argument("--login_number", type=int, nargs="?")
    parser.add_argument("--host", nargs="?")
    parser.add_argument("--connection_type", nargs="?")
    parser.add_argument("--pane_id", nargs="?")
    parser.add_argument("--window_id", nargs="?", default=":")
    parser.add_argument("--split_direction", nargs="?")
    parser.add_argument("--file_name", nargs="?")
    parser.add_argument(
        "-i", "--input", type=argparse.FileType("r"), default=(None if sys.stdin.isatty() else sys.stdin)
    )
    parser.add_argument("--history_index", nargs="?")
    args = parser.parse_args()

    if args.type == "login":
        cmd_login(args.login_number)
    elif args.type == "noc_menu":
        cmd_noc_menu(args.split_direction)
    elif args.type == "tmux_menu":
        cmd_tmux_menu()
    elif args.type == "ssh_menu":
        cmd_ssh_menu(args.split_direction)
    elif args.type == "move_pane_window":
        cmd_move_pane_window(args.split_direction)
    elif args.type == "setup_connection":
        cmd_setup_connection(args.connection_type, args.split_direction)
    elif args.type == "connect_telnet":
        cmd_connect_telnet(args.host, args.split_direction)
    elif args.type == "prompt_for_ssh_login":
        cmd_prompt_for_ssh_login(args.host)
    elif args.type == "connect_ssh":
        cmd_connect_ssh(args.host, args.split_direction)
    elif args.type == "toggle_log":
        cmd_pane_log("l", "local")
    elif args.type == "save_pane_history":
        cmd_save_pane_history(args.file_name, args.pane_id, args.input)
    elif args.type == "rename_window":
        cmd_rename_window(args.window_id)
    elif args.type == "rename_windows":
        cmd_rename_windows()
    elif args.type == "interactive_test":
        CmdInteractiveTest()
    else:
        print(f"Unknown action '{args.type}'")
