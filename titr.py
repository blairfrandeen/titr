#!/usr/bin/python

"""
titr - pronounced 'titter'

A time tracker CLI.
https://github.com/blairfrandeen/titr
"""

import datetime
from typing import Optional, Tuple, Dict, List, Callable

# TODO: Move all defaults to user-editable config file
# Write function to load configuration
MAX_DURATION: float = 9  # maximum duration that can be entered for any task
DEFAULT_CATEGORY: int = 6
DEFAULT_ACCOUNT: str = "O"

OUTLOOK_ACCOUNT: str = "blairfrandeen@outlook.com"
CALENDAR_NAME: str = "Calendar"
SKIP_ALLDAY_EVENTS: bool = True
SKIP_EVENT_NAMES: List[str] = ["Lunch"]  # skip outlook events with these titles
SKIP_EVENT_STATUS: List[int] = [
    0,
    3,
]  # skip outlook events with status free or out of office

CATEGORIES: Dict[int, str] = {
    2: "Deep Work",
    3: "Configuration",
    4: "Discussions",
    5: "Meetings",
    6: "Shallow / Misc",
    7: "Integration Activities",
    8: "Email",
    9: "Reflection",
    10: "Career Development",
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
        comment: str = "",
        date: datetime.date = datetime.date.today(),
    ) -> None:
        self.duration: float = duration
        self.category: int = category
        self.account: str = account
        self.comment: str = comment
        self.date: datetime.date = date

        self.timestamp: datetime.datetime = datetime.datetime.today()
        self.date_str: str = self.date.isoformat()
        self.cat_str = CATEGORIES[self.category]
        self.acct_str = ACCOUNTS[self.account.upper()]

    def __repr__(self):
        tsv_str: str = f"{self.date_str},{self.duration},{self.account},{self.category},{self.comment}"
        return tsv_str

    @property
    def tsv_str(self):  # pragma: no cover
        tsv_str: str = f"{self.date_str}\t{self.duration}\t{self.acct_str}\t{self.cat_str}\t{self.comment}\n"
        return tsv_str

    def __str__(self):  # pragma: no cover
        # TODO: Improve formatting
        self_str: str = f"{self.date_str}\t{round(self.duration,2)}\t\t{self.acct_str}\t\t{self.cat_str}\t\t{self.comment}"
        return self_str


class ConsoleSession:
    def __init__(self) -> None:
        self.time_entries: List[TimeEntry] = []
        self.command_list: Dict[str, Tuple[List[str], Callable]] = {
            "add": (["add"], self._add_entry),
            "clear": (["clear"], self.clear),
            "clip": (["clip"], self.copy_output),
            "commit": (["c", "commit"], None),  # not implemented
            "date": (["d", "date"], self.set_date),
            "help": (["h", "help"], self.help_msg),
            "list": (["ls", "list"], self.list_categories_and_accounts),
            "outlook": (["o", "outlook"], self.import_from_outlook),
            "null_cmd": ([""], None),
            "preview": (["p", "preview"], self.preview_output),
            "quit": (["q", "quit"], exit),
            "scale": (["s", "scale"], self.scale_time_entries),
            "undo": (["z", "undo"], self.undo_last),
        }
        self.date = datetime.date.today()
        exit.__doc__ = "Quit"

    def get_user_input(self, outlook_item=None) -> Optional[int]:
        user_input: str = input("> ")
        match user_input.split(" "):
            case [str(duration), *entry_args] if is_float(duration):
                self._add_entry(user_input, outlook_item)
            case [alias, *_] if self._is_alias(alias, "add"):
                # self.command_list['help'][1](command='add')
                self.help_msg(command="add")
            case [alias, *_] if self._is_alias(alias, "clear"):
                self.clear()
            case [alias, *_] if self._is_alias(alias, "clip"):
                self.copy_output()
            case [alias, *_] if self._is_alias(alias, "commit"):
                raise NotImplementedError
            case [alias] if self._is_alias(alias, "date"):
                self.set_date()
            case [alias, str(date_input)] if self._is_alias(alias, "date"):
                new_date = parse_date(datestr=date_input)
                self.set_date(new_date)
            case [alias, *_] if self._is_alias(alias, "list"):
                self.list_categories_and_accounts()
            case [alias] if self._is_alias(alias, "outlook"):
                self.import_from_outlook()
            case [alias, *_] if self._is_alias(alias, "preview"):
                self.preview_output()
            case [alias, str(scale_target)] if self._is_alias(alias, "scale"):
                if is_float(scale_target):
                    self.scale_time_entries(float(scale_target))
                else:
                    raise TypeError("Invalid argument, scale_target must be float")
            case [alias, *_] if self._is_alias(alias, "undo"):
                self.undo_last()
            case [alias, *_] if self._is_alias(alias, "quit"):
                self.command_list["quit"][1]()
                return 0
            case [alias, str(command)] if self._is_alias(alias, "help"):
                for name, cmd in self.command_list.items():
                    if self._is_alias(command, name):
                        self.help_msg(command=name)
                        return None
                raise ValueError("Command not found. Type 'help' for list.")
            case [alias] if self._is_alias(alias, "help"):
                self.help_msg()
            case [alias] if self._is_alias(alias, "null_cmd"):  # pragma: no cover
                self._add_entry(user_input, outlook_item)
            case _:
                raise ValueError(f'Invalid input: "{" ".join(user_input)}"')

    def _add_entry(self, user_input, outlook_item=None):
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
        entry_args = self._parse_new_entry(user_input)
        if outlook_item and entry_args != 0:
            if not entry_args:
                entry_args = dict()
            for index, key in enumerate(["duration", "category", "comment"]):
                if key not in entry_args.keys():
                    entry_args[key] = outlook_item[index]
        if entry_args and entry_args["duration"] != 0:
            self.time_entries.append(TimeEntry(**entry_args))
            print(self.time_entries[-1])

    def _is_alias(self, alias, command):
        """Test if a user command is an alias for a known command."""
        if command not in self.command_list.keys():
            return False
        return alias.lower() in self.command_list[command][0]

    def import_from_outlook(self):
        """Import appointments from outlook."""
        print("Getting outlook items...", end="")
        outlook_items = get_outlook_items(self.date)
        if outlook_items is not None:
            # Note: using len(outlook_items) or outlook_items.Count
            # will return an undefined value.
            num_items = sum(1 for _ in outlook_items)
            if num_items == 0:
                raise KeyError(f"No outlook items found for {self.date}")

            print(f"Found total of {num_items}")
            self._set_outlook_mode()
            for item in outlook_items:
                if item.AllDayEvent is True and SKIP_ALLDAY_EVENTS is True:
                    continue
                if item.Subject in SKIP_EVENT_NAMES:
                    continue
                if item.BusyStatus in SKIP_EVENT_STATUS:
                    continue
                comment = item.Subject
                duration = item.Duration / 60  # convert minutes to hours

                # TODO: Accept multiple categories
                appt_category = item.Categories.split(",")[0].strip()
                category = DEFAULT_CATEGORY
                for key, cat in CATEGORIES.items():
                    if cat == appt_category:
                        category = key
                        break

                # TODO: Improve formatting
                print(f"{round(duration,2)} hr:\t{category}\t{comment}")
                ui = self.get_user_input(outlook_item=(duration, category, comment))
                if ui == 0:
                    break

            self._set_normal_mode()

    def _set_outlook_mode(self):
        """Set console mode to add items from outlook."""
        replace_commands = ["outlook", "date", "quit"]
        self.default_commands = dict()
        for cmd in replace_commands:
            self.default_commands[cmd] = self.command_list.pop(cmd)

        self.command_list["quit"] = (
            self.default_commands["quit"][0],
            self._set_normal_mode,
        )

    def _set_normal_mode(self):
        """Return console to normal mode."""
        for cmd in self.default_commands.keys():

            self.command_list[cmd] = self.default_commands[cmd]

    def set_date(self, new_date=datetime.date.today()):
        """Set the date for time entries.

        Enter 'date' with no arguments to set date to today.
        Enter 'date -<n>' where n is an integer to set date n days back
            for example 'date -1' will set it to yesterday.
        Enter 'date yyyy-mm-dd' to set to any custom date.
        Dates must not be in the future.
        """
        if not isinstance(new_date, datetime.date):
            raise TypeError("Wrong argument passed to set_date")
        self.date = new_date
        print(f"Date set to {new_date.isoformat()}")

    def _parse_new_entry(self, user_input) -> Optional[dict]:
        """Parse a user input into a time entry.

        Returns None for blank entry
        Else returns a dict to be passed to a new TimeEntry"""
        if user_input == "":
            return None
        user_input = user_input.split(" ")
        duration = float(user_input[0])
        if duration > MAX_DURATION:
            raise ValueError("You're working too much.")
        if duration < 0:
            raise ValueError("You can't unwork.")
        new_entry_arguments = {"duration": duration}
        entry_args = user_input[1:]
        match entry_args:
            # No arguments, add entry with all defaults
            case ([] | "" | None):
                pass
            # All arguments including comment
            case (str(cat_key), str(account), *comment) if (
                is_float(cat_key)
                and int(cat_key) in CATEGORIES.keys()
                and account.upper() in ACCOUNTS.keys()
            ):
                new_entry_arguments["category"] = int(cat_key)
                new_entry_arguments["account"] = account
                if comment:
                    new_entry_arguments["comment"] = " ".join(comment).strip()
            # Category argument, no account argument
            case (str(cat_key), *comment) if (
                is_float(cat_key) and int(cat_key) in CATEGORIES.keys()
            ):
                new_entry_arguments["category"] = int(cat_key)
                if comment:
                    new_entry_arguments["comment"] = " ".join(comment).strip()
            # Account argument, no category argument
            case (str(account), *comment) if (
                not is_float(account) and account.upper() in ACCOUNTS.keys()
            ):
                new_entry_arguments["account"] = account
                if comment:
                    new_entry_arguments["comment"] = " ".join(comment).strip()
            # Comment only
            case (str(cat_key), str(account), *comment) if (
                not is_float(cat_key) and account.upper() not in ACCOUNTS.keys()
            ):
                comment = (cat_key + " " + account + " " + " ".join(comment)).strip()
                if comment:
                    new_entry_arguments["comment"] = comment
            case _:
                raise ValueError("Invalid arguments for time entry")

        return new_entry_arguments

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
            entry.duration = (
                entry.duration + scale_amount * entry.duration / unscaled_total
            )

    def copy_output(self):
        """Copy output to clipboard."""
        import pyperclip

        output_str = ""
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
                if function[1] is None:  # pragma: no cover
                    continue  # pragma: no cover
                summary_doc = function[1].__doc__.split("\n")[0]
                print(f"{function[0]}\t-\t{summary_doc}")

    @property
    def total_duration(self):
        return round(sum([entry.duration for entry in self.time_entries]), 2)

    def list_categories_and_accounts(self):
        """Display available category & account codes."""
        for dictionary, name in [
            (ACCOUNTS, "ACCOUNTS"),
            (CATEGORIES, "CATEGORIES"),
        ]:  # pragma: no cover
            disp_dict(dictionary, name)


def get_outlook_items(search_date: datetime.date):
    """Read calendar items from Outlook."""
    # connect to outlook
    import pywintypes
    import win32com.client

    # TODO: Move to separate function
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")
    except pywintypes.com_error as err:
        print(f"Error connecting to Outlook Namespace: {err}")
        return None
    try:
        acct = namespace.Folders.Item(OUTLOOK_ACCOUNT)
    except pywintypes.com_error as err:
        print(f'Error connecting to account "{OUTLOOK_ACCOUNT}": {err}')
        return None
    try:
        calendar = acct.Folders(CALENDAR_NAME)
    except pywintypes.com_error as err:
        print(f'Calendar with name "{CALENDAR_NAME}" not found: {err}')
        return None

    # Time format string requried by MAPI to filter by date
    MAPI_TIME_FORMAT = "%m-%d-%Y %I:%M %p"
    cal_items = calendar.Items
    cal_items.Sort("Start", False)
    cal_items.IncludeRecurrences = True
    search_end = search_date + datetime.timedelta(days=1)
    search_str = "".join(
        [
            "[Start] >= '",
            search_date.strftime(MAPI_TIME_FORMAT),
            "' AND [End] <= '",
            search_end.strftime(MAPI_TIME_FORMAT),
            "'",
        ]
    )

    cal_filtered = cal_items.Restrict(search_str)

    return cal_filtered


def disp_dict(dictionary: dict, dict_name: str):  # pragma: no cover
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


def parse_date(datestr: str) -> datetime.datetime:
    try:
        date_delta = int(datestr)
    except ValueError:
        pass
    else:
        if date_delta > 0:
            raise ValueError("Date cannot be in the future.")
        return datetime.date.today() + datetime.timedelta(days=date_delta)

    new_date = datetime.date.fromisoformat(datestr)
    if new_date > datetime.date.today():
        raise ValueError("Date cannot be in the future.")
    return new_date


def main() -> None:
    print("Welcome to titr.")
    cs = ConsoleSession()
    while True:  # pragma: no cover
        try:
            cs.get_user_input()
        except NotImplementedError:
            print("not implemented")
        except (ValueError, TypeError, KeyError) as err:
            print(f"Error: {err}")
        except ImportError as err:
            print(err)
            print(
                "Missing depedency. Try 'pip install pywin32' or 'pip install pyperclip'"
            )


if __name__ == "__main__":
    main()
