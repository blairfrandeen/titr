#!/usr/bin/python3

"""
titr - pronounced 'titter'

A time tracker CLI.
https://github.com/blairfrandeen/titr
"""

import argparse
import configparser
import datetime
import os
import sqlite3
import sys
import textwrap
from typing import Optional, Tuple, Dict, List, Any


from colorama import Fore, Style

# TODO: import datum_console as dc
try:
    from titr.datum_console import (
        ConsoleCommand,
        ConsolePattern,
        get_input,
        disable_command,
        enable_command,
        patch_command,
        set_pattern,
    )
    from titr import __version__
except ModuleNotFoundError:
    from __init__ import __version__
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

try:
    import pywintypes
    import win32com.client
except ImportError:  # pragma: no cover
    OUTLOOK_ENABLED = False
else:
    OUTLOOK_ENABLED = True

CONFIG_FILE: str = os.path.join(os.path.expanduser("~"), ".titr", "titr.cfg")
TITR_DB: str = os.path.join(os.path.expanduser("~"), ".titr", "titr.db")
COLUMN_WIDTHS = [12, 8, 22, 22, 24]

parser = argparse.ArgumentParser(description="titr")
parser.add_argument(
    "--testdb",
    action="store_true",
    help="use a test database file in the local folder",
)
args = parser.parse_args()
if args.testdb:  # pragma: no cover
    TITR_DB = "titr_test.db"


def main() -> None:
    print(f"Welcome to titr. Version {__version__}")
    print("https://github.com/blairfrandeen/titr")
    with ConsoleSession() as cs:
        get_input(session_args=cs)


###########
# CLASSES #
###########
@dataclass
class Config:
    outlook_account: str = ""
    default_category: int = 0
    default_task: str = ""
    calendar_name: str = ""
    skip_event_names: list[str] = field(default_factory=list)
    skip_event_status: list[int] = field(default_factory=list)
    category_list: dict = field(default_factory=dict)
    task_list: dict = field(default_factory=dict)
    skip_all_day_events: bool = True
    max_duration: float = 9
    deep_work_goal: float = 0
    incidental_tasks: list[str] = field(default_factory=list)


class ConsoleSession:
    def __init__(self) -> None:
        self.time_entries: List[TimeEntry] = []
        self.date = datetime.date.today()
        self.config = load_config()
        self.outlook_item: Optional[Tuple[float, int, str]] = None
        self.db_connection: sqlite3.Connection = db_initialize()
        # Populate the task and category lists in the database from the titr.cfg
        # File, which has already been loaded into the console session
        db_populate_task_category_lists(self)

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        self.db_connection.close()

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
        self.category = (
            session.config.default_category if category is None else category
        )
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
        w0, w1, w2, w3, w4 = COLUMN_WIDTHS
        comment_str_first: list[str] = (
            textwrap.wrap(
                self.comment,
                width=w4,
                initial_indent="",
                subsequent_indent=sum(COLUMN_WIDTHS[0:4]) * " ",
            )[0]
            if self.comment
            else ""
        )
        self_str = (
            "{date:{w0}}{duration:<{w1}.2f}{task:{w2}}{cat:{w3}}{comment:{w4}}".format(
                date=self.date_str,
                duration=self.duration,
                task=textwrap.shorten(self.tsk_str, w2 - 1, break_on_hyphens=False),
                cat=textwrap.shorten(self.cat_str, w3 - 1, break_on_hyphens=False),
                comment=comment_str_first,
                w0=w0,
                w1=w1,
                w2=w2,
                w3=w3,
                w4=w4,
            )
        )
        comment_str_others: list[str] = textwrap.wrap(
            self.comment[len(comment_str_first) :].strip(),
            width=sum(COLUMN_WIDTHS),
            initial_indent=sum(COLUMN_WIDTHS[0:4]) * " ",
            subsequent_indent=sum(COLUMN_WIDTHS[0:4]) * " ",
            max_lines=2,
        )
        for line in comment_str_others:
            self_str += "\n" + line
        return self_str.strip()


#####################
# CONSOLE FUNCTIONS #
#####################


def time_entry_pattern(user_input: str) -> bool:
    return is_float(user_input.split(" ")[0])


def outlook_entry_pattern(user_input: str) -> bool:
    return time_entry_pattern(user_input) or user_input == ""


@ConsoleCommand(name="add")
def add_help(console):  # pragma: no cover
    """
    Add a new entry to the time log.

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
    pass  # documentation only function


@ConsolePattern(pattern=time_entry_pattern, name="add_entry")
def add_entry(console, user_input: str) -> None:
    """Add a new entry to the time log."""
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


@ConsoleCommand(name="clear")
def clear_entries(console) -> None:
    """Delete all entered data."""
    console.time_entries = []


@ConsoleCommand(name="clip", aliases=["copy"])
def copy_output(console) -> None:
    """
    Copy output to clipboard.

    Output is copied in TSV (tab-separated values)"""
    import pyperclip

    output_str: str = ""
    if len(console.time_entries) > 0:
        for entry in console.time_entries:
            output_str += entry.tsv_str + "\n"

        pyperclip.copy(output_str.strip())
        print("TSV Output copied to clipboard.")
    else:
        print("No time has been entered.")


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
    """Preview time entries that have been entered so far."""
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


@ConsoleCommand(name="scale", aliases=["s"])
def scale_time_entries(console: ConsoleSession, target_total: str) -> None:
    """Scale time entries by weighted average to sum to a target total duration."""
    if not is_float(target_total):
        raise TypeError(f"Cannot convert {target_total} to float.")
    if float(target_total) == 0:
        raise ValueError("Cannot scale to zero.")
    unscaled_total: float = sum([entry.duration for entry in console.time_entries])
    scale_amount: float = float(target_total) - unscaled_total
    if scale_amount == 0:
        return None
    if unscaled_total == 0:
        print("No entries to scale / cannot scale from zero.")
        return None

    print(f"Scaling from {unscaled_total} hours to {target_total} hours.")
    for entry in console.time_entries:
        entry.duration = entry.duration + scale_amount * entry.duration / unscaled_total


@ConsoleCommand(name="date", aliases=["d"])
def set_date(console, datestr: str = None) -> None:
    """
    Set the date for time entries and timecard.

    Enter 'date' with no arguments to set date to today.
    Enter 'date -<n>' where n is an integer to set date n days back from today
        for example 'date -1' will set it to yesterday.
    Enter 'date yyyy-mm-dd' to set to any custom date.
    Dates must not be in the future.
    """
    if not datestr:
        console.date = datetime.date.today()
        print(f"Date set to {console.date.isoformat()}")
        return None
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
    if new_date > datetime.date.today():
        raise ValueError("Date cannot be in the future")

    console.date = new_date
    print(f"Date set to {console.date.isoformat()}")


@ConsoleCommand(name="undo", aliases=["u", "z"])
def undo_last(console) -> None:
    """Undo last entry."""
    console.time_entries = console.time_entries[:-1]


@ConsoleCommand(name="write", aliases=["c", "commit"])
def write_db(console: ConsoleSession) -> None:  # pragma: no cover
    """
    Permanently commit time entries to the database.

    Database is in ~/.titr/titr.db by default. Run titr --testdb
    to use a test database file in the working directory.

    Entries are copied to clipboard for those still using Excel.
    """

    if len(console.time_entries) == 0:
        raise ValueError("Nothing to commit. Get back to work.")

    # TODO: Store task & category lists exclusively in the database
    # modifiable through the program

    # Write metadata about the current session, and get the session id
    session_id = db_session_metadata(console.db_connection)

    # Write the time entries to the database
    db_write_time_log(console, session_id)

    # Copy entries to clipboard in case we are still using Excel
    copy_output(console)

    # Clear all time entries so they aren't entered a second time
    clear_entries(console)
    print(f"Commited entries to {TITR_DB}.")


@ConsoleCommand(name="timecard", aliases=["tc"])
def show_weekly_timecard(console: ConsoleSession) -> Optional[float]:
    """
    Show timecard summary for this week.

    To show summary for a different week, set the date
    to any day within the week of interest using the date command.

    Weeks start on Monday."""
    week_start: datetime.date = console.date - datetime.timedelta(
        days=console.date.weekday()
    )
    week_end: datetime.date = week_start + datetime.timedelta(days=6)
    cursor = console.db_connection.cursor()

    get_week_total_hours: str = """--sql
        SELECT sum(duration) FROM time_log WHERE
        date >= (?)
        AND
        date <= (?)
    """
    cursor.execute(get_week_total_hours, [week_start, week_end])
    week_total_hours: Optional[float] = cursor.fetchone()[0]

    col_widths = [30, 8, 15, 12]
    inc_task_str = "('" + "', '".join(console.config.incidental_tasks) + "')"
    if week_total_hours is not None:
        get_totals_by_task: str = """--sql
            SELECT t.name, sum(l.duration), t.user_key FROM time_log l
            JOIN tasks t ON t.id = l.task_id
            WHERE l.date >= (?) AND l.date <= (?)
            GROUP BY task_id;
        """
        get_total_incidental: str = """--sql
            SELECT sum(l.duration) FROM time_log l
            JOIN tasks t ON t.id = l.task_id
            WHERE l.date >= (?) AND l.date <= (?)
            AND t.user_key IN {}
        """.format(
            inc_task_str
        )
        cursor.execute(
            get_totals_by_task,
            [week_start, week_end],
        )
        totals_by_task: list[tuple[str, float, str]] = cursor.fetchall()
        cursor.execute(
            get_total_incidental,
            [week_start, week_end],
        )
        total_incidental: float = cursor.fetchone()[0]
        if total_incidental is None:
            total_incidental = 0
        print(  # HEADER ROW
            Style.BRIGHT
            + "{:{}}{:{}}{:{}}{:{}}".format(
                "TASK",
                col_widths[0],
                "HOURS",
                col_widths[1],
                "ADJ. HOURS",
                col_widths[2],
                "PERCENTAGE",
                col_widths[3],
            )
            + Style.NORMAL
        )
        # Print individual rows by task
        for task in totals_by_task:
            if task[2] not in console.config.incidental_tasks:
                task_percentage: float = task[1] / (week_total_hours - total_incidental)
                task_adj_hrs: float = task[1] + total_incidental * task_percentage
            else:
                task_percentage, task_adj_hrs = 0, 0
            print(
                "{:{}}{:<{}.2f}{:<{}.2f}{:<{}.2%}".format(
                    task[0],
                    col_widths[0],
                    task[1],
                    col_widths[1],
                    task_adj_hrs,
                    col_widths[2],
                    task_percentage,
                    col_widths[3],
                )
            )
        print(  # TOTAL ROW
            Style.BRIGHT
            + Fore.GREEN
            + "{:{}}{:<{}.2f}".format(
                "", col_widths[0], week_total_hours, col_widths[1]
            )
            + Style.RESET_ALL
        )
    else:
        print("No time entered for this week.")

    return week_total_hours


@ConsoleCommand(name="deepwork", aliases=["dw"])
def deep_work(console: ConsoleSession) -> float:
    """
    Show total deep work and deep work over past 365 days.

    Deep work goal currently set in source code to 300 hours."""
    cursor = console.db_connection.cursor()

    get_dw_total = """--sql
        SELECT sum(duration) FROM time_log t
        JOIN categories c on t.category_id=c.id
        WHERE c.name = 'Deep Work'
    """
    cursor.execute(get_dw_total)
    dw_total = cursor.fetchone()[0]
    get_dw_last_365 = get_dw_total + " AND date>=(?)"

    last_year = datetime.date.today() - datetime.timedelta(days=365)
    cursor.execute(get_dw_last_365, [last_year])
    dw_last_365 = cursor.fetchone()[0]
    w1, w2, w3, w4 = 15, 12, 18, 15  # column widths
    print(
        Style.BRIGHT
        + "{:{}}{:{}}{:{}}{:{}}".format(
            "DEEP WORK", w1, "TOTAL", w2, "LAST 365 DAYS", w3, "GOAL", w4
        )
        + Style.NORMAL
    )
    goal_color = (
        Fore.GREEN if dw_last_365 >= console.config.deep_work_goal else Fore.RED
    )
    print(
        Style.BRIGHT
        + "{:{}}".format("----------", w1)
        + "{:<{}.1f}".format(dw_total, w2)
        + goal_color
        + "{:<{}.1f}".format(dw_last_365, w3)
        + Fore.RESET
        + "{:<{}.0f}".format(console.config.deep_work_goal, w4)
        + Style.NORMAL
    )
    return dw_total


@ConsoleCommand(name="outlook", aliases=["o"], enabled=OUTLOOK_ENABLED)
def import_from_outlook(console: ConsoleSession) -> None:
    """
    Import appointments from outlook for the current date.

    Requires that outlook be running with the account specified
    in your ~/.titr/titr.cfg file active. Windows only."""
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
                (
                    item.AllDayEvent is True
                    and console.config.skip_all_day_events is True
                )
                or item.Subject in console.config.skip_event_names
                or item.BusyStatus in console.config.skip_event_status
            ):
                continue
            comment: str = item.Subject
            duration: float = item.Duration / 60  # convert minutes to hours

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


@ConsoleCommand(name="import")
def import_from_csv(
    console: ConsoleSession,
    csv_file_path: str,
    header_row: Optional[int] = None,
) -> int:
    """
    Import data from a CSV into the database.

    Usage: import <filename> [header_row=<header_row_num>]
    CSV data must be structured as
    Date: date | duration: float | task: str | category: str | comment: str
    Returns number of rows added.
    """

    import csv

    cursor = console.db_connection.cursor()
    session_id: int = db_session_metadata(
        console.db_connection, input_type="import_from_csv"
    )
    write_entry: str = """--sql
        INSERT INTO time_log (date, duration, category_id, task_id, comment, session_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """

    try:
        with open(csv_file_path, "r") as csv_handle:
            csv_reader = csv.reader(csv_handle)
            row_num: int = 0
            num_entries: int = 0
            total_hours: float = 0.0
            # loop row-by-row, starting at the first row if header_row=None
            # else start at header_row + 1
            for row in csv_reader:
                row_num += 1
                if header_row is not None and row_num <= int(header_row):
                    continue

                # convert the date
                try:
                    month, day, year = row[0].split("/")
                    entry_date: datetime.date = datetime.date(
                        int(year), int(month), int(day)
                    )
                except ValueError:
                    print(
                        f"Warning: {row_num=} has invalid date {row[0]}. Skipping entry."
                    )
                    continue

                # convert the entry duration
                try:
                    entry_duration = float(row[1])
                except ValueError:
                    print(
                        f"Warning: {row_num=} has invalid duration {row[1]}. Skipping entry."
                    )
                    continue

                # Get task & category ids
                task_id = db_populate_user_table(console.db_connection, "tasks", row[2])
                category_id = db_populate_user_table(
                    console.db_connection,
                    "categories",
                    row[3],
                    user_key=None,
                )

                entry_comment = row[4]

                cursor.execute(
                    write_entry,
                    [
                        entry_date,
                        entry_duration,
                        category_id,
                        task_id,
                        entry_comment,
                        session_id,
                    ],
                )
                num_entries = num_entries + 1
                total_hours = total_hours + entry_duration
    except FileNotFoundError as err:
        print(err)
        return 0

    print(f"Total of {num_entries} entries found totalling {total_hours} hours.")
    continue_prompt = input("Enter 'y' to continue: ")
    if continue_prompt == "y":
        console.db_connection.commit()
        print("Entries committed to database.")

    return num_entries


#####################
# PRIVATE FUNCTIONS #
#####################
# TODO: Rename with leading underscore, organize


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
        "deep_work_goal": "300",
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
    config["incidental_tasks"] = {
        "keys": "i",
    }
    config_path: str = os.path.dirname(CONFIG_FILE)
    if not os.path.exists(config_path):  # pragma: no cover
        os.mkdir(config_path)
    with open(CONFIG_FILE, "w") as config_file_handle:
        config.write(config_file_handle)

    return CONFIG_FILE


def disp_dict(dictionary: dict, dict_name: str):  # pragma: no cover
    """Display items in a dict"""
    print(f"{Style.BRIGHT}{dict_name}{Style.NORMAL}: ")
    for key, value in dictionary.items():
        print(f"{Fore.BLUE}{key}{Fore.RESET}: {value}")


def get_outlook_items(
    search_date: datetime.date, calendar_name: str, outlook_account: str
):
    """Read calendar items from Outlook."""

    # connect to outlook
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


def is_float(item: str) -> bool:
    """Determine if a string represents a float."""
    if not isinstance(item, (str, int, float)):
        raise TypeError
    try:
        float(item)
        return True
    except ValueError:
        return False


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
    config.incidental_tasks = parser["incidental_tasks"]["keys"].split(", ")
    config.incidental_tasks = list(map(str.strip, config.incidental_tasks))
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
    config.deep_work_goal = float(parser["general_options"]["deep_work_goal"])

    config.outlook_account = parser["outlook_options"]["email"]
    config.calendar_name = parser["outlook_options"]["calendar_name"]
    config.skip_event_names = [
        event.strip()
        for event in parser["outlook_options"]["skip_event_names"].split(",")
    ]
    # TODO: Error handling
    config.skip_event_status = [
        int(status)
        for status in parser["outlook_options"]["skip_event_status"].split(",")
    ]
    config.skip_all_day_events = parser.getboolean(
        "outlook_options", "skip_all_day_events"
    )

    return config


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
            not is_float(cat_key)
            and task.lower() not in console.config.task_list.keys()
        ):
            new_comment: str = (cat_key + " " + task + " " + " ".join(comment)).strip()
            if new_comment:
                time_entry_arguments["comment"] = new_comment
        case comment:
            time_entry_arguments["comment"] = " ".join(comment).strip()
            #  raise ValueError("Invalid arguments for time entry")

    return time_entry_arguments


######################
# DATABASE FUNCTIONS #
######################
def db_initialize(
    database_file: str = TITR_DB, test_flag: bool = False
) -> sqlite3.Connection:
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
            user_key TEXT,
            name TEXT
        )
    """
    # Create task table
    task_table = """--sql
        CREATE TABLE IF NOT EXISTS tasks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_key TEXT,
            name TEXT
        )
    """
    # Create sessions table
    session_table = """--sql
        CREATE TABLE IF NOT EXISTS sessions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titr_version TEXT,
            user TEXT,
            platform TEXT,
            ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            input_type TEXT
        )
    """

    for table in [time_log_table, category_table, task_table, session_table]:
        cursor.execute(table)

    #  if not test_flag:  # pragma: no cover
    db_connection.commit()

    return db_connection


def db_populate_user_table(
    db_connection: sqlite3.Connection,
    table: str,
    value: str,
    user_key: Optional[str] = None,
    test_flag: bool = False,
) -> int:
    """Populate a single row of a table with a key-value pair.

    Will update an existing entry if the name (value) field is recognized.
    Otherwise a new entry will be added.
    User keys will be enforced to be unique.

    Return the primary_key of the entry"""
    # Determine the id of the row to populate
    # Search the table and find the id of the item with a matching name
    cursor = db_connection.cursor()

    get_primary_key: str = """--sql
        SELECT id FROM {} WHERE name=(?)
    """.format(
        table
    )
    cursor.execute(get_primary_key, [value])
    primary_key_query: Optional[tuple] = cursor.fetchone()

    # If no result, create a new table row
    if primary_key_query is None:
        get_last_key: str = "SELECT MAX(id) from {}".format(table)
        cursor.execute(get_last_key, [])
        last_key: tuple[Optional[int]] = cursor.fetchone()
        # start at zero if table is empty:7
        primary_key: int = 0 if last_key[0] is None else last_key[0] + 1
    else:
        primary_key = primary_key_query[0]

    if user_key is not None:
        write_table: str = """--sql
            REPLACE INTO {} (id, user_key, name) VALUES (?, ?, ?)
        """.format(
            table
        )
        cursor.execute(write_table, [primary_key, user_key, value])

        # Ensure that all keys in the table are unique
        enforce_unique_keys: str = """--sql
            UPDATE {} SET user_key=null WHERE id != (?) AND user_key = (?)
        """.format(
            table
        )
        cursor.execute(enforce_unique_keys, [primary_key, user_key])
    else:
        write_table = """--sql
            INSERT OR REPLACE INTO {} (id, name) VALUES (?, ?)
        """.format(
            table
        )
        cursor.execute(write_table, [primary_key, value])

    return primary_key


def db_populate_task_category_lists(
    console: ConsoleSession,
) -> None:
    """Populate the category & task tables in the sqlite db."""
    for user_key, value in console.config.category_list.items():
        db_populate_user_table(console.db_connection, "categories", value, user_key)

    for user_key, value in console.config.task_list.items():
        db_populate_user_table(console.db_connection, "tasks", value, user_key)

    console.db_connection.commit()


def db_session_metadata(
    db_connection: sqlite3.Connection, input_type: str = "user", test_flag: bool = False
) -> int:
    """Make entry in session table and return the session id."""
    cursor = db_connection.cursor()
    new_entry: str = """--sql
        INSERT INTO sessions (titr_version, user, platform, input_type) VALUES (?, ?, ?, ?)
    """
    platform: str = sys.platform
    if "linux" in platform:
        user = os.uname().nodename
    elif "win" in platform:
        user = os.getlogin()
    else:
        user = None

    cursor.execute(new_entry, [__version__, user, platform, input_type])
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


def db_write_time_log(console: ConsoleSession, session_id: int) -> None:
    """Write time entries from console session to database."""
    cursor = console.db_connection.cursor()
    write_entry = """--sql
        INSERT INTO time_log (date, duration, category_id, task_id, comment, session_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    get_task_id = """--sql
        SELECT id
        FROM tasks
        WHERE user_key = (?)
    """
    get_category_id = """--sql
        SELECT id
        FROM categories
        WHERE user_key = (?)
    """
    for entry in console.time_entries:
        # TODO: Handling for no task ID found
        cursor.execute(get_task_id, [entry.task])
        task_id = cursor.fetchone()[0]
        cursor.execute(get_category_id, [entry.category])
        category_id = cursor.fetchone()[0]
        cursor.execute(
            write_entry,
            [
                entry.date,
                entry.duration,
                category_id,
                task_id,
                entry.comment,
                session_id,
            ],
        )
    console.db_connection.commit()


if __name__ == "__main__":
    main()
