#!/usr/bin/python3

"""
titr - pronounced 'titter'

A time tracker CLI.
https://github.com/blairfrandeen/titr
"""

import configparser
import datetime
import os
import sqlite3
import sys
from typing import Optional, Tuple, Dict, List, Callable, Any

from __init__ import __version__
from colorama import Fore, Style
# TODO: import datum_console as dc
from datum_console import (
    ConsoleCommand,
    ConsolePattern,
    get_input,
    disable_command,
    enable_command,
    patch_command,
    set_pattern,
)
from dataclasses import dataclass, field

CONFIG_FILE: str = os.path.join(os.path.expanduser("~"), ".titr", "titr.cfg")
#  TITR_DB: str = os.path.join(os.path.expanduser("~"), ".titr", "titr.db")
TITR_DB: str = "titr_test.db"
COLUMN_WIDTHS = [13, 8, 12, 25, 38]
NEW_CONSOLE = True


def main() -> None:
    print("Welcome to titr.")
    cmd_dict = dict()
    cs = ConsoleSession()
    if NEW_CONSOLE:
        get_input(session_args=cs)
    else:
        while True:  # pragma: no cover
            try:
                cs.get_user_input()
            except NotImplementedError:
                print("not implemented")
            except (ValueError, TypeError, KeyError) as err:
                print(f"Error: {err}")
            except ImportError as err:
                print(err)


####################
# PUBLIC FUNCTIONS #
####################
def create_default_config():
    """Create a default configuration file"""
    # Ensure we don't accidentally overwrite config
    if os.path.isfile(CONFIG_FILE):
        raise FileExistsError(f"Config file '{CONFIG_FILE}' already exists!")
    config = configparser.ConfigParser(allow_no_value=True)
    user_email: str = input("Enter your email to connect to outlook: ")
    config["outlook_options"] = {
        "email": user_email,
        "calendar_name": "Calendar",
        "# skip events with given status codes, comma separated list": None,
        "# 0 = free": None,
        "# 1 = tentative": None,
        "# 2 = busy": None,
        "# 3 = out of office": None,
        "# 4 = working elsewhere": None,
        "skip_event_status": "0, 3",
        "skip_all_day_events": "yes",
        "# use comma separated list of calendar event names to be skipped": None,
        "skip_event_names": "",
    }
    config["general_options"] = {
        "max_entry_duration": "9",
        "default_category": "2",
        "default_task": "d",
    }
    config["categories"] = {
        2: "Deep Work",
        3: "Email",
        4: "Meetings",
    }
    config["tasks"] = {
        "i": "Incidental",
        "d": "Default Task",
    }
    config_path: str = os.path.dirname(CONFIG_FILE)
    if not os.path.exists(config_path):  # pragma: no cover
        os.mkdir(config_path)
    with open(CONFIG_FILE, "w") as config_file_handle:
        config.write(config_file_handle)

    return CONFIG_FILE


###########
# CLASSES #
###########
@dataclass
class Config:
    category_list: dict = field(default_factory=dict)
    task_list: dict = field(default_factory=dict)


class ConsoleSession:
    def __init__(self) -> None:
        self.time_entries: List[TimeEntry] = []
        self.command_list: Dict[str, Tuple[List[str], Optional[Callable]]] = {
            "add": (["add"], _add_entry),
            "clear": (["clear"], clear_entries),
            "clip": (["clip"], copy_output),
            "commit": (["c", "commit"], write_db),  # not implemented
            "date": (["d", "date"], set_date),
            "help": (["h", "help"], self.help_msg),
            "list": (["ls", "list"], list_categories_and_tasks),
            "outlook": (["o", "outlook"], import_from_outlook),
            "null_cmd": ([""], None),
            "preview": (["p", "preview"], preview_output),
            "quit": (["q", "quit"], exit),
            "scale": (["s", "scale"], scale_time_entries),
            "undo": (["z", "undo"], undo_last),
        }
        self.date = datetime.date.today()
        exit.__doc__ = "Quit"
        self.config = load_config()
        self.outlook_item = None

    def get_user_input(self, outlook_item=None, input_str: str = "> ") -> Optional[int]:
        user_input: str = input(input_str)
        match user_input.split(" "):
            case [str(duration), *_] if is_float(duration):
                _add_entry(self, user_input, outlook_item)
                return 1
            case [alias, *_] if self._is_alias(alias, "add"):
                # self.command_list['help'][1](command='add')
                self.help_msg(command="add")
            case [alias, *_] if self._is_alias(alias, "clear"):
                clear_entries(self)
            case [alias, *_] if self._is_alias(alias, "clip"):
                copy_output(self)
            case [alias, *_] if self._is_alias(alias, "commit"):
                write_db(self)
            case [alias] if self._is_alias(alias, "date"):
                set_date(self)
            case [alias, str(date_input)] if self._is_alias(alias, "date"):
                set_date(self, date_input)
            case [alias, *_] if self._is_alias(alias, "list"):
                list_categories_and_tasks(self)
            case [alias] if self._is_alias(alias, "outlook"):
                import_from_outlook(self)
            case [alias, *_] if self._is_alias(alias, "preview"):
                preview_output(self)
            case [alias, str(scale_target)] if self._is_alias(alias, "scale"):
                if is_float(scale_target):
                    scale_time_entries(self, float(scale_target))
                else:
                    raise TypeError("Invalid argument, scale_target must be float")
            case [alias, *_] if self._is_alias(alias, "undo"):
                undo_last(self)
            case [alias, *_] if self._is_alias(alias, "quit"):
                if self.command_list["quit"] is not None:
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
                _add_entry(self, user_input, outlook_item)
                return 1
            case _:
                raise ValueError(f'Invalid input: "{user_input}"')

        return None

    def _is_alias(self, alias: str, command: str) -> bool:
        """Test if a user command is an alias for a known command."""
        if command not in self.command_list.keys():
            return False
        return alias.lower() in self.command_list[command][0]

    def _set_outlook_mode(self) -> None:
        """Set console mode to add items from outlook."""
        replace_commands: list[str] = ["outlook", "date", "quit"]
        self.default_commands = dict()
        for cmd in replace_commands:
            self.default_commands[cmd] = self.command_list.pop(cmd)

        self.command_list["quit"] = (
            self.default_commands["quit"][0],
            self._set_normal_mode,
        )

    def _set_normal_mode(self) -> None:
        """Return console to normal mode."""
        for cmd in self.default_commands.keys():

            self.command_list[cmd] = self.default_commands[cmd]

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
    def total_duration(self) -> float:
        return round(sum([entry.duration for entry in self.time_entries]), 2)


class TimeEntry:
    """Class to capture data for time entries"""

    def __init__(
        self,
        session: ConsoleSession,
        duration: float,
        category: int = None,
        task: str = None,
        comment: str = "",
        date: datetime.date = datetime.date.today(),
    ) -> None:
        self.duration: float = duration
        self.category = session.config.default_category if category is None else category
        self.task = session.config.default_task if task is None else task
        self.comment: str = comment
        self.date: datetime.date = date

        self.timestamp: datetime.datetime = datetime.datetime.today()
        self.date_str: str = self.date.isoformat()
        self.cat_str = session.config.category_list[self.category]
        self.tsk_str = session.config.task_list[self.task.lower()]

    def __repr__(self):
        return f"{self.date_str},{self.duration},{self.task},{self.category}"

    @property
    def tsv_str(self):  # pragma: no cover
        tsv_str: str = "\t".join(
            [
                self.date_str,
                str(self.duration),
                self.tsk_str,
                self.cat_str,
                self.comment,
            ]
        )
        return tsv_str

    def __str__(self):  # pragma: no cover
        self_str = ""
        for index, item in enumerate(
            [
                self.date_str,
                self.duration,
                self.tsk_str,
                self.cat_str,
                self.comment,
            ]
        ):
            if index == 1:
                fmt, al = ".2f", "<"
            else:
                fmt, al = "", "<"
            self_str += "{i:{al}{wd}{fmt}}".format(i=item, al=al, fmt=fmt, wd=COLUMN_WIDTHS[index])

        return self_str.strip()


#####################
# CONSOLE FUNCTIONS #
#####################


@ConsoleCommand(name="clear")
def clear_entries(console) -> None:
    """Delete all entered data."""
    console.time_entries = []


@ConsoleCommand(name="clip", aliases=["copy"])
def copy_output(console) -> None:
    """Copy output to clipboard."""
    import pyperclip

    output_str: str = ""
    for entry in console.time_entries:
        output_str += entry.tsv_str + "\n"

    pyperclip.copy(output_str.strip())
    print("TSV Output copied to clipboard.")


@ConsoleCommand(name="list", aliases=["ls"])
def list_categories_and_tasks(console):
    """Display available category & account codes."""
    for dictionary, name in [
        (console.config.task_list, "TASKS"),
        (console.config.category_list, "CATEGORIES"),
    ]:  # pragma: no cover
        disp_dict(dictionary, name)
        print()


@ConsoleCommand(name="preview", aliases=["p"])
def preview_output(console: ConsoleSession) -> None:
    """Preview output."""
    print(Style.BRIGHT, end="")
    for index, heading in enumerate(["DATE", "HOURS", "TASK", "CATEGORY", "COMMENT"]):
        print(
            "{heading:{wd}}".format(heading=heading, wd=COLUMN_WIDTHS[index]),
            end="",
        )
    print(Style.NORMAL)
    for entry in console.time_entries:
        print(entry)
    print(Style.BRIGHT + Fore.GREEN, end="")
    print("{s:{wd}}".format(s="TOTAL", wd=COLUMN_WIDTHS[0]), end="")
    print("{d:<{wd}.2f}".format(d=console.total_duration, wd=COLUMN_WIDTHS[1]))
    print(Style.NORMAL + Fore.RESET, end="")


# TODO: Fix this function to accept string input
@ConsoleCommand(name="scale", aliases=["s"])
def scale_time_entries(console, target_total) -> None:
    """Scale time entries by weighted average to sum to a target total duration."""
    unscaled_total: float = sum([entry.duration for entry in console.time_entries])
    scale_amount: float = target_total - unscaled_total
    if scale_amount == 0:
        return None
    if unscaled_total == 0:
        print("No entries to scale / cannot scale from zero.")
        return None

    print(f"Scaling from {unscaled_total} hours to {target_total} hours.")
    for entry in console.time_entries:
        entry.duration = entry.duration + scale_amount * entry.duration / unscaled_total


# TODO: ALlow for no datestr
@ConsoleCommand(name="date", aliases=["d"])
def set_date(console, datestr: str) -> None:
    """Set the date for time entries.

    Enter 'date' with no arguments to set date to today.
    Enter 'date -<n>' where n is an integer to set date n days back
        for example 'date -1' will set it to yesterday.
    Enter 'date yyyy-mm-dd' to set to any custom date.
    Dates must not be in the future.
    """
    new_date: Optional[datetime.date] = None
    try:
        date_delta: int = int(datestr)
    except ValueError:
        pass
    else:
        if date_delta > 0:
            raise ValueError("Date cannot be in the future.")
        new_date = datetime.date.today() + datetime.timedelta(days=date_delta)

    new_date = datetime.date.fromisoformat(datestr) if not new_date else new_date

    console.date = new_date
    print(f"Date set to {new_date.isoformat()}")


@ConsoleCommand(name="undo", aliases=["u", "z"])
def undo_last(console) -> None:
    """Undo last entry."""
    console.time_entries = console.time_entries[:-1]


@ConsoleCommand(name="write", aliases=["c", "commit"])
def write_db(console: ConsoleSession) -> None:  # pragma: no cover
    """Write time entries to the database."""

    if len(console.time_entries) == 0:
        raise ValueError("Nothing to commit. Get back to work.")
    # Establish a connection, and initialize the database if not already done.
    db_connection: sqlite3.Connection = db_initialize()

    # Populate the task and category lists in the database from the titr.cfg
    # File, which has already been loaded into the console session
    # TODO: Store task & category lists exclusively in the database
    # modifiable through the program
    db_populate_task_category_lists(console, db_connection)

    # Write metadata about the current session, and get the session id
    session_id = db_session_metadata(db_connection)

    # Write the time entries to the database
    db_write_time_log(console, db_connection, session_id)

    # Close the connection
    db_connection.close()

    # Copy entries to clipboard in case we are still using Excel
    copy_output(console)

    # Clear all time entries so they aren't entered a second time
    clear_entries(console)
    print(f"Commited entries to {TITR_DB}.")


@ConsoleCommand(name="outlook", aliases=["o"])
def import_from_outlook(console: ConsoleSession) -> None:
    """Import appointments from outlook."""
    outlook_items = get_outlook_items(
        console.date, console.config.calendar_name, console.config.outlook_account
    )
    if outlook_items is not None:
        # Note: using len(outlook_items) or outlook_items.Count
        # will return an undefined value.
        num_items = sum(1 for _ in outlook_items)
        if num_items == 0:
            raise KeyError(f"No outlook items found for {console.date}")

        # Allow blank entries to be mapped to add_item command
        set_pattern("add_entry", outlook_entry_pattern)
        # Disable commands in the console
        disabled_commands = "date write quit".split(" ")
        for cmd in disabled_commands:
            disable_command(cmd)

        print(f"Found total of {num_items} events for {console.date}:")
        # console._set_outlook_mode()
        for item in outlook_items:
            if (
                (item.AllDayEvent is True and console.config.skip_all_day_events is True)
                or item.Subject in console.config.skip_event_names
                or item.BusyStatus in console.config.skip_event_status
            ):
                continue
            comment = item.Subject
            duration = item.Duration / 60  # convert minutes to hours

            # TODO: Accept multiple categories
            appt_category = item.Categories.split(",")[0].strip()
            category = console.config.default_category
            for key, cat in console.config.category_list.items():
                if cat == appt_category:
                    category = key
                    break

            # TODO: Improve formatting
            cat_str = console.config.category_list[category]
            event_str = f"{comment}\n{cat_str} - {round(duration,2)} hr > "
            console.outlook_item = (duration, category, comment)
            command = get_input(
                session_args=console,
                break_commands=["add_entry", "null_cmd", "quit"],
                prompt=event_str,
            )
            console.outlook_item = None
            if command.name == "quit":
                break

        # Reenable commands
        set_pattern("add_entry", time_entry_pattern)
        for cmd in disabled_commands:
            enable_command(cmd)
        preview_output(console)


#####################
# PRIVATE FUNCTIONS #
#####################
# TODO: Rename with leading underscore, organize


def time_entry_pattern(user_input: str) -> bool:
    return is_float(user_input.split(" ")[0])


def outlook_entry_pattern(user_input: str) -> bool:
    return time_entry_pattern(user_input) or user_input == ""


@ConsolePattern(pattern=time_entry_pattern, name="add_entry")
def _add_entry(console, user_input: str) -> None:
    """Add a new entry to the time log.

    Format is <duration> [<category> <task> <comment>]
    There is no need to type 'add'
    Duration is required and must be able to be converted to float
    Type 'ls accounts' and 'ls categories' for available accounts & categories
    Category must be an integer; task must be a single character
    Any text after the task is considered a comment.
    All arguments other than duration are optional.

    Some examples:
    1 2 i this is one hour in category 2 in task 'i'
    1 this is one hour on default task & category
    .5 i this is one hour in task 'i'
    1 2 this is one hour in category 2
    2.1     (2.1 hrs, default category & task, no comment)
    """
    entry_args: Optional[Dict[Any, Any]] = _parse_time_entry(console, user_input)
    if console.outlook_item:
        if not entry_args:
            entry_args = dict()
        for index, key in enumerate(["duration", "category", "comment"]):
            if key not in entry_args.keys():
                entry_args[key] = console.outlook_item[index]
    if entry_args and entry_args["duration"] != 0:
        console.time_entries.append(TimeEntry(console, date=console.date, **entry_args))
        print(console.time_entries[-1])


def _parse_time_entry(console: ConsoleSession, raw_input: str) -> Optional[dict]:
    """Parse a user input into a time entry.

    Returns None for blank entry
    Else returns a dict to be passed to a new TimeEntry"""
    if raw_input == "":
        return None
    user_input: List[str] = raw_input.split(" ")
    duration = float(user_input[0])
    if duration > console.config.max_duration:
        raise ValueError("You're working too much.")
    if duration < 0:
        raise ValueError("You can't unwork.")
    time_entry_arguments: dict = {"duration": duration}
    entry_args: List[str] = user_input[1:]
    match entry_args:
        # No arguments, add entry with all defaults
        case ([] | "" | None):
            pass
        # All arguments including comment
        case (str(cat_key), str(task), *comment) if (
            is_float(cat_key)
            and int(cat_key) in console.config.category_list.keys()
            and task.lower() in console.config.task_list.keys()
        ):
            time_entry_arguments["category"] = int(cat_key)
            time_entry_arguments["task"] = task
            if comment:
                time_entry_arguments["comment"] = " ".join(comment).strip()
        # Category argument, no task argument
        case (str(cat_key), *comment) if (
            is_float(cat_key) and int(cat_key) in console.config.category_list.keys()
        ):
            time_entry_arguments["category"] = int(cat_key)
            if comment:
                time_entry_arguments["comment"] = " ".join(comment).strip()
        # task argument, no category argument
        case (str(task), *comment) if (
            not is_float(task) and task.lower() in console.config.task_list.keys()
        ):
            time_entry_arguments["task"] = task
            if comment:
                time_entry_arguments["comment"] = " ".join(comment).strip()
        # Comment only
        case (str(cat_key), str(task), *comment) if (
            not is_float(cat_key) and task.lower() not in console.config.task_list.keys()
        ):
            new_comment: str = (cat_key + " " + task + " " + " ".join(comment)).strip()
            if new_comment:
                time_entry_arguments["comment"] = new_comment
        case comment:
            time_entry_arguments["comment"] = " ".join(comment).strip()
            #  raise ValueError("Invalid arguments for time entry")

    return time_entry_arguments


def load_config(config_file=CONFIG_FILE) -> Config:
    """Load and validate configuration options."""
    # look for a config file in the working directory
    # if it doesn't exist, create it with some default options
    if not os.path.isfile(config_file):
        config_file = create_default_config()
    config = Config()
    parser = configparser.ConfigParser()
    parser.read(config_file)
    for key in parser["categories"]:
        try:
            cat_key = int(key)
        except ValueError as err:
            print(f"Warning: Skipped category key {key} in {config_file}: {err}")
            continue
        config.category_list[cat_key] = parser["categories"][key]
    for key in parser["tasks"]:
        if len(key) > 1:
            print(f"Warning: Skipped task key {key} in {config_file}: len > 1.")
            continue
        if key.isdigit():
            print(f"Warning: Skipped task key {key} in {config_file}: Digit")
            continue
        config.task_list[key] = parser["tasks"][key]

    config.default_task = parser["general_options"]["default_task"]
    if config.default_task not in config.task_list.keys():
        print(
            "Warning: Default tasks '",
            config.default_task,
            "' not found in ",
            config_file,
        )
        config.default_task = list(config.task_list.keys())[0]

    # TODO: Error handling for default category as not an int
    config.default_category = int(parser["general_options"]["default_category"])
    if config.default_category not in config.category_list.keys():
        config.default_category = int(list(config.category_list.keys())[0])
        print(
            "Warning: Default category '",
            config.default_category,
            "'not found in ",
            config_file,
        )

    # TODO: Error handling
    config.max_duration = float(parser["general_options"]["max_entry_duration"])

    config.outlook_account = parser["outlook_options"]["email"]
    config.calendar_name = parser["outlook_options"]["calendar_name"]
    config.skip_event_names = [
        event.strip() for event in parser["outlook_options"]["skip_event_names"].split(",")
    ]
    # TODO: Error handling
    config.skip_event_status = [
        int(status) for status in parser["outlook_options"]["skip_event_status"].split(",")
    ]
    config.skip_all_day_events = parser.getboolean("outlook_options", "skip_all_day_events")

    return config


def get_outlook_items(search_date: datetime.date, calendar_name: str, outlook_account: str):
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
        acct = namespace.Folders.Item(outlook_account)
    except pywintypes.com_error as err:
        print(f'Error connecting to account "{outlook_account}": {err}')
        return None
    try:
        calendar = acct.Folders(calendar_name)
    except pywintypes.com_error as err:
        print(f'Calendar with name "{calendar_name}" not found: {err}')
        return None

    # Time format string requried by MAPI to filter by date
    MAPI_TIME_FORMAT: str = "%m-%d-%Y %I:%M %p"
    cal_items = calendar.Items
    cal_items.Sort("Start", False)
    cal_items.IncludeRecurrences = True
    search_end: datetime.date = search_date + datetime.timedelta(days=1)
    search_str: str = "".join(
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
    print(f"{Style.BRIGHT}{dict_name}{Style.NORMAL}: ")
    for key, value in dictionary.items():
        print(f"{Fore.BLUE}{key}{Fore.RESET}: {value}")


def is_float(item: str) -> bool:
    """Determine if a string represents a float."""
    if not isinstance(item, (str, int, float)):
        raise TypeError
    try:
        float(item)
        return True
    except ValueError:
        return False


######################
# DATABASE FUNCTIONS #
######################
def db_initialize(database_file: str = TITR_DB, test_flag: bool = False) -> sqlite3.Connection:
    """Write the sessions time entries to a database."""
    db_connection = sqlite3.connect(database_file)
    cursor = db_connection.cursor()

    # Create time log table
    time_log_table = """--sql
        CREATE TABLE IF NOT EXISTS time_log(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE,
            duration FLOAT,
            category_id INT,
            task_id INT,
            session_id INT,
            comment TEXT
        )
    """
    # Create category table
    category_table = """--sql
        CREATE TABLE IF NOT EXISTS categories(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT
        )
    """
    # Create task table
    task_table = """--sql
        CREATE TABLE IF NOT EXISTS tasks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT,
            name TEXT
        )
    """
    # Create task table
    session_table = """--sql
        CREATE TABLE IF NOT EXISTS sessions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titr_version TEXT,
            user TEXT,
            platform TEXT,
            ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """

    for table in [time_log_table, category_table, task_table, session_table]:
        cursor.execute(table)

    #  if not test_flag:  # pragma: no cover
    db_connection.commit()

    return db_connection


def db_populate_task_category_lists(
    console: ConsoleSession,
    db_connection: sqlite3.Connection,
) -> None:
    """Populate the category & task tables in the sqlite db."""
    write_categories = """--sql
        REPLACE INTO categories (id, name) VALUES (?, ?)
    """
    write_tasks = """--sql
        REPLACE INTO tasks (id, key, name) VALUES (?, ?, ?)
    """
    cursor = db_connection.cursor()
    for key, value in console.config.category_list.items():
        cursor.execute(write_categories, [key, value])

    task_id = 0
    for key, value in console.config.task_list.items():
        cursor.execute(write_tasks, [task_id, key, value])
        task_id += 1

    db_connection.commit()


def db_session_metadata(db_connection: sqlite3.Connection, test_flag: bool = False) -> int:
    """Make entry in session table and return the session id."""
    cursor = db_connection.cursor()
    new_entry: str = """--sql
        INSERT INTO sessions (titr_version, user, platform) VALUES (?, ?, ?)
    """
    platform: str = sys.platform
    if "linux" in platform:
        user = os.uname().nodename
    elif "win" in platform:
        user = os.getlogin()
    else:
        user = None

    cursor.execute(new_entry, [__version__, user, platform])
    #  if not test_flag:  # pragma: no cover
    db_connection.commit()

    get_session_id: str = """--sql
        SELECT MAX(id) from sessions
    """
    cursor.execute(get_session_id)
    session_id = cursor.fetchone()[0]
    #  if not test_flag:  # pragma: no cover
    #  db_connection.close()

    return session_id


def db_write_time_log(
    console: ConsoleSession, db_connection: sqlite3.Connection, session_id: int
) -> None:
    """Write time entries from console session to database."""
    cursor = db_connection.cursor()
    write_entry = """--sql
        INSERT INTO time_log (date, duration, category_id, task_id, comment, session_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    get_task_id = """--sql
        SELECT id, key
        FROM tasks
        WHERE key = (?)
    """
    for entry in console.time_entries:
        cursor.execute(get_task_id, [entry.task])
        task_id = cursor.fetchone()[0]
        cursor.execute(
            write_entry,
            [
                entry.date,
                entry.duration,
                entry.category,
                task_id,
                entry.comment,
                session_id,
            ],
        )
    db_connection.commit()


if __name__ == "__main__":
    main()
