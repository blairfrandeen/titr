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
    while True:
        cs.get_user_input()
        if test_flag:
            break


class TimeEntry:
    def __init__(
        self,
        duration: float,
        category: int = DEFAULT_CATEGORY,
        account: str = DEFAULT_ACCOUNT,
        comment: str = '',
    ) -> None:
        self.duration: float = duration
        self.category: Optional[int] = category
        self.account: Optional[str] = account
        self.comment: Optional[str] = comment

        self.timestamp: datetime.datetime = datetime.datetime.today()
        self.date_str: str = self.timestamp.strftime("%Y/%m/%d")
        self.cat_str = CATEGORIES[self.category]
        self.acct_str = ACCOUNTS[self.account.upper()]

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
            "<duration>": self.add_entry,  # default command
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

    def get_user_input(self) -> None:
        user_input: str = input('> ').lower().split(' ')
        match user_input:
            case[str(duration), *entry_args] if is_float(duration):
                duration = float(duration)
                match entry_args:
                    # No arguments, add entry with all defaults
                    case ([] | '' | None):
                        self.add_entry(duration)
                    # All arguments including comment
                    case (str(cat_key), str(account), *comment) if (
                            is_float(cat_key) and
                            int(cat_key) in CATEGORIES.keys() and
                            account.upper() in ACCOUNTS.keys()
                        ):
                        self.add_entry(
                            duration,
                            category=int(cat_key),
                            account=account,
                            comment=' '.join(comment)
                        )
                    # Category argument, no account argument
                    case (str(cat_key), str(account), *comment) if (
                            is_float(cat_key) and
                            int(cat_key) in CATEGORIES.keys()
                        ):
                        self.add_entry(
                            duration,
                            category=int(cat_key),
                            comment=account + ' ' + ' '.join(comment)
                        )
                    # Account argument, no category argument
                    case (str(account), *comment) if (
                            not is_float(account) and
                            account.upper() in ACCOUNTS.keys()
                        ):
                        self.add_entry(
                            duration,
                            account=account,
                            comment=' '.join(comment)
                        )
                    # Comment only
                    case (str(cat_key), str(account), *comment) if (
                            not is_float(cat_key) and
                            account.upper() not in ACCOUNTS.keys()
                        ):
                        self.add_entry(
                            duration,
                            comment=cat_key + ' ' + account + ' ' + ' '.join(comment)
                        )
                    case _:
                        print('Invalid arguments for time entry')
            case['clear', *_]:
                self.clear()
            case['clip', *_]:
                self.copy_output()
            case['c' | 'commit', *_]:
                print('not implemented')
            case['d' | 'date', str(datestr), *_]:
                print('not implemented')
            case['ls' | 'list', str(list_target)]:
                match list_target:
                    case('accounts' | 'wams' | 'a' | 'w'):
                        display_accounts()
                    case('cats' | 'c' | 'categories'):
                        display_categories()
                    case _:
                        print("Invalid argument, use 'ls accounts' or 'ls categories'")
            case['p' | 'preview', *_]:
                self.preview_output()
            case['s' | 'scale', str(scale_target), *_]:
                if is_float(scale_target):
                    self.scale_time_entries(float(scale_target))
                else:
                    print('Inavlid argument, must be float')
            case['z' | 'undo', *_]:
                self.undo_last()
            case['q' | 'quit', *_]:
                exit(0)
            case['h' | 'help']:
                self.help_msg()
            case['h' | 'help', str(command)]:
                self.help_msg(command)
            case['']:
                pass # no input => no output
            case _:
                print('Invalid input')

    def scale_time_entries(self, target_total) -> None:
        """Scale time entries by weighted average to sum to a target total duration."""
        unscaled_total: float = sum([entry.duration for entry in self.time_entries])
        scale_amount: float = target_total - unscaled_total
        if scale_amount == 0:
            return None
        if unscaled_total == 0:
            print("No entries to scale / cannot scale from zero.")
            return None

        print(f"Scaling from {unscaled_total} hours to {target_total} hours.")
        for entry in self.time_entries:
            entry.duration = entry.duration + scale_amount * entry.duration / unscaled_total

    def add_entry(self, duration, **kwargs) -> None:
        """Add a time entry.

        Format:
        <duration> [ work_mode | account | comment]
        Example:
        .3 2 I Incidental deep work
        2 g Two hours shallow work as group lead
        1 One hour, default account, default mode
        1 5 One hour meeting default account"""
        self.time_entries.append(TimeEntry(duration, **kwargs))
        print(self.time_entries[-1])

    def copy_output(self):
        """Copy output to clipboard."""
        output_str = ''
        for entry in self.time_entries:
            output_str += entry.tsv_str

        pyperclip.copy(output_str)
        print("TSV Output copied to clipboard.")

    def preview_output(self) -> None:
        """Preview output."""
        print("DATE\t\tduration\tACCOUNT\t\tCATEGORY\t\tCOMMENT")
        for entry in self.time_entries:
            print(entry)
        print(f"TOTAL\t\t{self.total_duration}")

    def undo_last(self):
        """Undo last entry."""
        self.time_entries = self.time_entries[:-1]

    def clear(self) -> None:
        """Delete all entered data."""
        self.time_entries = []

    def help_msg(self, command=None):
        """Display this help message. Type help <command> for detail."""
        if not command:
            for cmd, function in self.command_list.items():
                summary_doc = function.__doc__.split('\n')[0]
                print(f"{cmd}\t-\t{summary_doc}")
        elif command.upper() in self.command_list.keys():
            print(self.command_list[command].__doc__)
        else:
            print("Invalid command.")

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


def is_float(item: str) -> bool:
    """Determine if a string represents a float."""
    if not isinstance(item, (str, int, float)):
        raise TypeError
    try:
        float(item)
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    main()

