#!/usr/bin/python

"""
titr - pronounced 'titter'

A time tracker CLI.
https://github.com/blairfrandeen/titr
"""

import datetime
import pyperclip
from typing import Optional, Tuple, Dict, List, Callable

# TODO: Move all defaults to user-editable config file
# Write function to load configuration
MAX_duration: float = 9  # maximum duration that can be entered for any task
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
    "T": "Time Tracker",
    "N": "Non-Productive Effort",
}


def main(test_flag=False) -> None:
    print("Welcome to titr.")
    cs = ConsoleSession()
    cs.help_msg()
    user_command: str = ""
    while user_command != "q":
        user_command = input("> ")
        try:
            command, args = parse_user_input(cs.command_list, user_command)
            if command and args:
                cs.command_list[command](*args) # pragma: no cover
            elif command:
                cs.command_list[command]()
        except ValueError as e:
            print("Invalid command: ", e)
        if test_flag:
            break


class TimeEntry:
    def __init__(
        self,
        duration: float,
        category: Optional[int],
        account: Optional[str],
        comment: Optional[str],
    ) -> None:
        self.duration: float = duration
        self.category: Optional[int] = category
        self.account: Optional[str] = account
        self.comment: Optional[str] = comment
        if not self.category:
            self.category = DEFAULT_CATEGORY
        if not self.account:
            self.account = DEFAULT_ACCOUNT
        if not self.comment:
            self.comment = ''
        self.timestamp: datetime.datetime = datetime.datetime.today()
        self.date_str: str = self.timestamp.strftime("%Y/%m/%d")
        self.cat_str = CATEGORIES[self.category]
        self.acct_str = ACCOUNTS[self.account]

    def __repr__(self):
        tsv_str: str = f"{self.date_str},{self.duration},{self.account},{self.category},{self.comment}"
        return tsv_str

    @property
    def tsv_str(self): # pragma: no cover
        tsv_str: str = f"{self.date_str}\t{self.duration}\t{self.acct_str}\t{self.cat_str}\t{self.comment}\n"
        return tsv_str

    def __str__(self): # pragma: no cover
        self_str: str = f"{self.date_str}\t{self.duration}\t{self.acct_str}\t{self.cat_str}\t{self.comment}"
        return self_str


class ConsoleSession:
    def __init__(self) -> None:
        self.time_entries: List[TimeEntry] = []
        self.command_list: Dict[str, Callable] = {
            "A": self.add_entry,  # default command
            "C": self.copy_output,
            "P": self.preview_output,
            "Z": self.undo_last,
            "D": self.clear,
            "S": self.scale_time_entries,
            "W": display_accounts,
            "T": display_categories,
            "H": self.help_msg,
            "Q": exit,
        }
        exit.__doc__ = "Quit"

    def scale_time_entries(self, target_total: float = 9) -> None:
        """Scale time entries by weighted average to sum to a target total duration."""
        unscaled_total: float = sum([entry.duration for entry in self.time_entries])
        scale_amount: float = target_total - unscaled_total
        if scale_amount == 0:
            return None

        for entry in self.time_entries:
            entry.duration = entry.duration + scale_amount * entry.duration / unscaled_total

    def add_entry(self, *args) -> None:
        """Add a time entry."""
        self.time_entries.append(TimeEntry(*args))
        print(self.time_entries[-1])

    def copy_output(self, *args):
        """Copy output to clipboard."""
        output_str = ''
        for entry in self.time_entries:
            output_str += entry.tsv_str

        pyperclip.copy(output_str)
        print("TSV Output copied to clipboard.")

    def preview_output(self, *args) -> None:
        """Preview output."""
        print("DATE\t\tduration\tACCOUNT\t\tCATEGORY\t\tCOMMENT")
        for entry in self.time_entries:
            print(entry)
        print(f"TOTAL\t\t{self.total_duration}")

    def undo_last(self, *args):
        """Undo last entry."""
        self.time_entries = self.time_entries[:-1]

    def clear(self, *args) -> None:
        """Delete all entered data."""
        self.time_entries = []

    def help_msg(self, *args):
        """Display this help message"""
        for cmd, function in self.command_list.items():
            print(f"{cmd}\t-\t{function.__doc__}")

    @property
    def total_duration(self):
        return sum([entry.duration for entry in self.time_entries])


def display_accounts(): # pragma: no cover
    """Display avalable charge account codes."""
    disp_dict(ACCOUNTS)

def display_categories(): # pragma: no cover
    """Display available category codes."""
    disp_dict(CATEGORIES)

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
    - duration Worked, Work Type, Work Account, Comment
    - If no entry for type, account or comment, apply defaults.
    """
    if not isinstance(user_command, str):
        raise TypeError

    args: List[str] = user_command.split(";")

    command: Optional[str] = None
    duration: Optional[float] = None
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
        duration = float(args[0])
        if duration < 0:
            raise ValueError("duration must be positive")
        elif duration > MAX_duration:
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
    ] = (duration, category, account, comment)

    return command, arguments

def disp_dict(dictionary: dict):# pragma: no cover
    """Display items in a dict"""
    for key, value in dictionary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()

