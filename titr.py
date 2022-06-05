#!/usr/bin/python

"""
titr - pronounced 'titter'

A time tracker CLI.
https://github.com/blairfrandeen/titr
"""

import datetime
try:
    import pyperclip
except ModuleNotFoundError: # pragma: no cover
    pyperclip = None

from typing import Optional, Tuple, Dict, List, Callable

# TODO: Move all defaults to user-editable config file
# Write function to load configuration
MAX_DURATION: float = 9  # maximum duration that can be entered for any task
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


class TimeEntry:
    def __init__(
        self,
        duration: float,
        category: int = DEFAULT_CATEGORY,
        account: str = DEFAULT_ACCOUNT,
        comment: str = '',
    ) -> None:
        self.duration: float = duration
        self.category: int = category
        self.account: str = account
        self.comment: str = comment

        self.timestamp: datetime.datetime = datetime.datetime.today()
        self.date_str: str = self.timestamp.strftime("%Y/%m/%d")
        self.cat_str = CATEGORIES[self.category]
        self.acct_str = ACCOUNTS[self.account.upper()]
        print(self)

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

    def _parse_new_entry(self, duration: float, *entry_args) -> None:
        match entry_args:
            # No arguments, add entry with all defaults
            case ([] | '' | None):
                self.time_entries.append(TimeEntry(duration))
            # All arguments including comment
            case (str(cat_key), str(account), *comment) if (
                    is_float(cat_key) and
                    int(cat_key) in CATEGORIES.keys() and
                    account.upper() in ACCOUNTS.keys()
                ):
                self.time_entries.append(TimeEntry(
                    duration,
                    category=int(cat_key),
                    account=account,
                    comment=' '.join(comment).strip()
                ))
            # Category argument, no account argument
            case (str(cat_key), str(account), *comment) if (
                    is_float(cat_key) and
                    int(cat_key) in CATEGORIES.keys()
                ):
                self.time_entries.append(TimeEntry(
                    duration,
                    category=int(cat_key),
                    comment=(account + ' ' + ' '.join(comment)).strip()
                ))
            # Account argument, no category argument
            case (str(account), *comment) if (
                    not is_float(account) and
                    account.upper() in ACCOUNTS.keys()
                ):
                self.time_entries.append(TimeEntry(
                    duration,
                    account=account,
                    comment=' '.join(comment).strip()
                ))
            # Comment only
            case (str(cat_key), str(account), *comment) if (
                    not is_float(cat_key) and
                    account.upper() not in ACCOUNTS.keys()
                ):
                self.time_entries.append(TimeEntry(
                    duration,
                    comment=(cat_key + ' ' + account + ' ' + ' '.join(comment)).strip()
                ))
            case _:
                raise ValueError('Invalid arguments for time entry')

        print(self.time_entries[-1])

    def get_user_input(self) -> None:
        user_input: str = input('> ').lower().split(' ')
        match user_input:
            case[str(duration), *entry_args] if is_float(duration):
                duration = float(duration)
                if duration > MAX_DURATION:
                    raise ValueError("You're working too much.")
                self._parse_new_entry(duration, *entry_args)
            case['clear', *_]:
                self.clear()
            case['clip', *_]:
                if pyperclip is not None:
                    self.copy_output()
                else:
                    raise ImportError('Unable to copy to clipboard.')
            case['c' | 'commit', *_]:
                raise NotImplementedError
            case['d' | 'date', str(datestr), *_]:
                raise NotImplementedError
            case['ls' | 'list', str(list_target)]:
                match list_target:
                    case('accounts' | 'wams' | 'a' | 'w'):
                        display_accounts()
                    case('cats' | 'c' | 'categories'):
                        display_categories()
                    case _:
                        raise ValueError("Invalid argument; use 'ls accounts' or 'ls categories'")
            case['p' | 'preview', *_]:
                self.preview_output()
            case['s' | 'scale', str(scale_target), *_]:
                if is_float(scale_target):
                    self.scale_time_entries(float(scale_target))
                else:
                    raise TypeError('Invalid argument, scale_target must be float')
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


def main() -> None:
    print("Welcome to titr.")
    cs = ConsoleSession()
    while True: # pragma: no cover
        try:
            cs.get_user_input()
        except ValueError as err:
            print(f"Error: {err}")
        except TypeError as err:
            print(f"Error: {err}")
        except ImportError as err:
            print(f"Error: {err}")
        except NotImplementedError:
            print('not implemented')


if __name__ == "__main__":
    main()

