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

    def __repr__(self):
        tsv_str: str = f"{self.date_str},{self.duration},{self.account},{self.category},{self.comment}"
        return tsv_str

    @property
    def tsv_str(self): # pragma: no cover
        tsv_str: str = f"{self.date_str}\t{self.duration}\t{self.acct_str}\t{self.cat_str}\t{self.comment}\n"
        return tsv_str

    def __str__(self): # pragma: no cover
        self_str: str = f"{self.date_str}\t{self.duration}\t\t{self.acct_str}\t\t{self.cat_str}\t\t{self.comment}"
        return self_str


class ConsoleSession:
    def __init__(self) -> None:
        self.time_entries: List[TimeEntry] = []
        self.command_list: Dict[str, Tuple[List[str], Callable]] = {
            'add':      (['add'],           self._add_entry),
            'clear':    (["clear"],         self.clear),
            'clip':     (["clip"],          self.copy_output),
            'commit':   (['c', 'commit'],   None),      # not implemented
            'date':     (['d', 'date'],     None),      # not implemented 
            'preview':  (["p", "preview"],  self.preview_output),
            'undo':     (["z", "undo"],     self.undo_last),
            'scale':    (["s", "scale"],    self.scale_time_entries),
            'list':     (["ls", "list"],    self.list_categories_and_accounts),
            'help':     (["h", "help"],     self.help_msg),
            'quit':     (["q", "quit"],     exit),
        }
        exit.__doc__ = "Quit"


    def _is_alias(self, alias, command):
        return alias in self.command_list[command][0]

    def get_user_input(self) -> None:
        user_input: str = input('> ').lower().split(' ')
        match user_input:
            case[str(duration), *entry_args] if is_float(duration):
                duration = float(duration)
                if duration > MAX_DURATION:
                    raise ValueError("You're working too much.")
                self._parse_new_entry(duration, *entry_args)
            case[alias, *_] if self._is_alias(alias, 'add'):
                self.help_msg(command='add')
            case[alias, *_] if self._is_alias(alias, 'clear'):
                self.clear()
            case[alias, *_] if self._is_alias(alias, 'clip'):
                if pyperclip is not None:
                    self.copy_output()
                else:
                    raise ImportError('Unable to copy to clipboard.')
            case[alias, *_] if self._is_alias(alias, 'commit'):
                raise NotImplementedError
            case[alias, *_] if self._is_alias(alias, 'date'):
                raise NotImplementedError
            case[alias, *_] if self._is_alias(alias, 'list'):
                self.list_categories_and_accounts()
            case[alias, *_] if self._is_alias(alias, 'preview'):
                self.preview_output()
            case[alias, str(scale_target)] if self._is_alias(alias, 'scale'):
                if is_float(scale_target):
                    self.scale_time_entries(float(scale_target))
                else:
                    raise TypeError('Invalid argument, scale_target must be float')
            case[alias, *_] if self._is_alias(alias, 'undo'):
                self.undo_last()
            case[alias, *_] if self._is_alias(alias, 'quit'):
                exit(0)
            case[alias, str(command)] if self._is_alias(alias, 'help'):
                for name, cmd in self.command_list.items():
                    if self._is_alias(command, name):
                        self.help_msg(command=name)
                        return None
                raise ValueError("Command not found. Type 'help' for list.")
            case[alias] if self._is_alias(alias, 'help'):
                self.help_msg()
            case['']: # pragma: no cover
                pass # no input => no output
            case _:
                raise ValueError(f'Invalid input: {user_input}')

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
            case (str(cat_key), *comment) if (
                    is_float(cat_key) and
                    int(cat_key) in CATEGORIES.keys()
                ):
                self.time_entries.append(TimeEntry(
                    duration,
                    category=int(cat_key),
                    comment=(' '.join(comment)).strip()
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

    def copy_output(self):
        """Copy output to clipboard."""
        output_str = ''
        for entry in self.time_entries:
            output_str += entry.tsv_str

        pyperclip.copy(output_str)
        print("TSV Output copied to clipboard.")

    def preview_output(self) -> None:
        """Preview output."""
        print("DATE\t\tDURATION\tACCOUNT\t\tCATEGORY\t\tCOMMENT")
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
        if command:
            print(self.command_list[command][1].__doc__)
        else:
            for _, function in self.command_list.items():
                # ignore non-implemented functions
                if function[1] is None: # pragma: no cover
                    continue # pragma: no cover
                summary_doc = function[1].__doc__.split('\n')[0]
                print(f"{function[0]}\t-\t{summary_doc}")

    @property
    def total_duration(self):
        return sum([entry.duration for entry in self.time_entries])

    def _add_entry(self): # pragma: no cover
        """Add a new entry to the time log.

        Format is <duration> [<category> <account> <comment>]
        There is no need to type 'add'
        Duration is required and must be able to be converted to float
        Type 'ls accounts' and 'ls categories' for available accounts & categories
        Category must be an integer; account must be a single character
        Any text after the accounts is considered a comment.
        All arguments other than duration are optional.

        Some examples:
        1 2 i this is one hour in category 2 in account 'i'
        1 this is one hour on default account & category
        .5 i this is one hour in account 'i'
        1 2 this is one hour in category 2
        2.1     (2.1 hrs, default category & account, no comment)
        """
        # documentation only function
        pass

    def list_categories_and_accounts(self):
        """Display available category & account codes."""
        for dictionary, name in [(ACCOUNTS, 'ACCOUNTS'), (CATEGORIES, 'CATEGORIES')]: # pragma: no cover
            disp_dict(dictionary, name)

def disp_dict(dictionary: dict, dict_name: str):# pragma: no cover
    """Display items in a dict"""
    print(f"{dict_name}: ")
    print("--------------")
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

