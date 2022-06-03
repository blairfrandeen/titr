#!/usr/bin/python

"""
titr - pronounced 'titter'

A time tracker CLI.
"""
import datetime
from typing import Optional, Tuple, Dict, List, Callable

MAX_HOURS: float = 9  # maximum hours that can be entered for any task
DEFAULT_CATEGORY: int = 6
DEFAULT_ACCOUNT: str = 'O'

CATEGORIES: Dict[int, str] = {
    2: "Deep Work",
    3: "Configuration",
    4: "Discussions",
    5: "Meetings",
    6: "Shallow / Misc",
    7: "Career Development",
    8: "Email",
}

ACCOUNTS: Dict[str, str] = {
    "O": "OS",
    "G": "Group Lead",
    "I": "Incidental",
}


def main() -> None:
    print("Welcome to titr.")
    cs = ConsoleSession()
    cs.help_msg()
    user_command: str = ""
    while user_command != "q":
        user_command = input("> ")
        try:
            command, args = parse_user_input(cs.command_list, user_command)
            if command and args:
                cs.command_list[command](*args)
            elif command:
                cs.command_list[command]()
        except ValueError as e:
            print("Invalid command: ", e)
        except NotImplementedError:
            print("Command not implemented yet.")


class TimeEntry:
    def __init__(
        self,
        hours: float,
        category: Optional[int],
        account: Optional[str],
        comment: Optional[str],
    ) -> None:
        self.hours: float = hours
        self.category: Optional[int] = category
        self.account: Optional[str] = account
        self.comment: Optional[str] = comment
        if not self.category:
            self.category = DEFAULT_CATEGORY
        if not self.account:
            self.account = DEFAULT_ACCOUNT
        if not self.comment:
            self.comment = ''
        self.timestamp = datetime.datetime.today()

    def to_csv(self):
        csv_str = f"{self.hours},{self.category},{self.account},{self.comment}"

class ConsoleSession:
    def __init__(self) -> None:
        self.output: List[str] = []
        self.command_list: Dict[str, Callable] = {
            "A": self.add_entry,  # default command
            "C": self.copy_output,
            "P": self.preview_output,
            "Z": self.undo_last,
            "D": self.clear,
            "W": self.display_accounts,
            "T": self.display_categories,
            "H": self.help_msg,
            "Q": exit,
        }
        exit.__doc__ = "Quit"

    def add_entry(self, *args):
        """Add a time entry."""
        raise NotImplementedError

    def copy_output(self, *args):
        """Copy output to clipboard."""
        raise NotImplementedError

    def preview_output(self, *args):
        """Preview output."""
        raise NotImplementedError

    def undo_last(self, *args):
        """Undo last entry."""
        self.output = self.output[:-1]

    def clear(self, *args) -> None:
        """Delete all entered data."""
        self.output = []

    def display_accounts(self, *args):
        """Display avalable charge account codes."""
        disp_dict(ACCOUNTS)

    def display_categories(self, *args):
        """Display available category codes."""
        disp_dict(CATEGORIES)

    def help_msg(self, *args):
        """Display this help message"""
        for cmd, function in self.command_list.items():
            print(f"{cmd}\t-\t{function.__doc__}")

def parse_user_input(
    command_list: Dict[str, Callable],
    user_command: str) -> None:
    """
    Parse user commands. Return the command and
    a tuple of arguments. Commands & arguments
    are separated by a semicolon. The logic:
    - If the first split is a char, look for that command
    - If the first split is not a char, apply a default command
    - Remaining splits in the following order:
    - Hours Worked, Work Type, Work Account, Comment
    - If no entry for type, account or comment, apply defaults.
    """
    if not isinstance(user_command, str):
        raise TypeError

    args: List[str] = user_command.split(";")

    command: Optional[str] = None
    hours: Optional[float] = None
    category: Optional[int] = None
    account: Optional[str] = None
    comment: Optional[str] = None

    if args[0].isalpha():
        if len(args[0]) > 1:
            raise ValueError("Command should be single letter.")
        elif args[0].upper() in command_list.keys():
            command = args[0].upper()
            return command, None
        else:
            raise ValueError("Command not found.")
    elif args[0] == '':
        return None, None
    else:
        command = "A"
        hours = float(args[0])
        if hours < 0:
            raise ValueError("Hours must be positive")
        elif hours > MAX_HOURS:
            raise ValueError("You're working too much.")

        if len(args) > 1 and args[1] != "":
            category = int(args[1])
            if category not in CATEGORIES.keys():
                raise ValueError("Unknown category")

        if len(args) > 2 and args[2] != "":
            account = args[2].upper()
            if account not in ACCOUNTS.keys():
                raise ValueError("Unknown account")

        if len(args) > 3 and args[3] != "":
            comment = args[3]

    arguments: Tuple[
        Optional[float],
        Optional[int],
        Optional[str],
        Optional[str],
    ] = (hours, category, account, comment)

    return command, arguments

def disp_dict(dictionary: dict):
    """Display items in a dict"""
    for key, value in dictionary.items():
        print(f"{key}: {value}")

def fill_hours(hours: List[float], target: float) -> List[float]:
    total = sum(hours)
    difference = target - total
    if difference == 0:
        return hours

    for index, item in enumerate(hours):
        hours[index] = item + difference * item / total

    assert sum(hours) == target

    return hours


if __name__ == "__main__":
    main()
