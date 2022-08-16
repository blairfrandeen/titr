#!/usr/bin/python3

"""
titr - pronounced 'titter'

A time tracker CLI.
https://github.com/blairfrandeen/titr
"""

import argparse
import csv
import configparser
import datetime
import math
import os
import sqlite3
import sys
import textwrap

from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict, List, Any, Union, Callable

from colorama import Fore, Style

try:  # pragma: no cover
    # Attempt to import modules to use with Outlook
    import pywintypes
    import win32com.client
except ImportError:
    # If failed, outlook commands disabled
    OUTLOOK_ENABLED = False
else:  # pragma: no cover
    OUTLOOK_ENABLED = True

# allow for this file to be run from source tree root
sys.path.append("src")

from titr import __version__, __db_user_version__
import titr.datum_console as dc


CONFIG_FILE: str = os.path.join(os.path.expanduser("~"), ".titr", "titr.cfg")
TITR_DB: str = os.path.join(os.path.expanduser("~"), ".titr", "titr.db")
COLUMN_WIDTHS = [12, 8, 22, 22, 24]
# fmt: off
WELCOME_MSG = (
f"""Welcome to titr. Version {__version__}. DB v{__db_user_version__}.
https://github.com/blairfrandeen/titr""")
# fmt: on


def main() -> None:
    args: argparse.Namespace = parse_args()
    print(WELCOME_MSG)
    if args and args.testdb:
        global TITR_DB  # TODO: Clean this up, get away from relying on global
        TITR_DB = "titr_test.db"
        print(f"Using Test Database: {TITR_DB}")
    with ConsoleSession() as cs:
        # For starting a new timed entry
        if args and args.start is not None:
            _start_timed_activity(cs, args.start)
        elif args and args.end is not None:
            _end_timed_activity(cs, args.end)

        if args.outlook:
            try:
                import_from_outlook(cs)
            except dc.InputError as err:
                print(err)
        dc.get_input(session_args=cs)


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


@dataclass
class TimeEntry:
    """Class to capture data for time entries"""

    duration: Optional[float] = None
    category: Optional[int] = None
    task: Optional[str] = None
    date: Optional[datetime.date] = None
    start_ts: Optional[datetime.datetime] = None
    end_ts: Optional[datetime.datetime] = None
    time_log_id: Optional[int] = None
    comment: str = field(default_factory=str)
    cat_str: str = field(default_factory=str)
    tsk_str: str = field(default_factory=str)

    def __repr__(self):
        return f"{self.date.isoformat()},{self.duration},{self.task},{self.category}"

    @property
    def tsv_str(self):  # pragma: no cover
        tsv_str: str = "\t".join(
            [
                self.date.isoformat(),
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
        self_str = "{date:{w0}}{duration:<{w1}.2f}{task:{w2}}{cat:{w3}}{comment:{w4}}".format(
            date=self.date.isoformat(),
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
        comment_str_others: list[str] = (
            textwrap.wrap(
                self.comment[len(comment_str_first) :].strip(),
                width=sum(COLUMN_WIDTHS),
                initial_indent=sum(COLUMN_WIDTHS[0:4]) * " ",
                subsequent_indent=sum(COLUMN_WIDTHS[0:4]) * " ",
                max_lines=2,
            )
            if self.comment
            else ""
        )
        for line in comment_str_others:
            self_str += "\n" + line
        return self_str.strip()


@dataclass
class ConsoleSession:
    date: datetime.date = datetime.date.today()
    outlook_item: Optional[tuple] = field(default_factory=tuple)
    time_entries: list = field(default_factory=list)

    def __post_init__(self) -> None:
        """Populate the task and category lists in the database from the titr.cfg
        File, which has already been loaded into the console session"""
        self.config: Config = load_config()
        self.db_connection: sqlite3.Connection = db_initialize()
        db_populate_task_category_lists(self)

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        """When opened with a context manager, this will
        safely close the connection in case of crash or system exist."""
        self.db_connection.close()

    def add_entry(self, entry: TimeEntry, set_defaults: bool = True) -> TimeEntry:
        """Add a TimeEntry to the console. Set the date, defaults, and the
        string representations of category and task."""
        entry.date = self.date if not entry.date else entry.date
        if set_defaults:
            # Set console-config based default category & task,
            # if they have not already been set
            entry.category = (
                self.config.default_category if entry.category is None else entry.category
            )
            entry.task = self.config.default_task if entry.task is None else entry.task

        entry.cat_str = self.config.category_list[entry.category] if entry.category else ""
        entry.tsk_str = self.config.task_list[entry.task.lower()] if entry.task else ""

        self.time_entries.append(entry)
        return entry

    @property
    def total_duration(self) -> float:
        return round(sum([entry.duration for entry in self.time_entries]), 2)


#####################
# CONSOLE FUNCTIONS #
#####################


def time_entry_pattern(user_input: str) -> bool:
    return is_float(user_input.split(" ")[0])


def outlook_entry_pattern(user_input: str) -> bool:
    return time_entry_pattern(user_input) or user_input == ""


@dc.ConsoleCommand(name="add")
def add_help(console, *args):  # pragma: no cover
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
    print("Use 'help add' for assistence.")


@dc.ConsolePattern(pattern=time_entry_pattern, name="add_entry")
def add_entry(console, user_input: str) -> None:
    """Add a new entry to the time log."""
    new_entry = _parse_time_entry(console, user_input)
    if console.outlook_item:
        if not new_entry:  # if no user input, create a blank entry
            new_entry = TimeEntry(duration=None)
        # TODO: Consider cleaner refactor of below set of conditionals
        # if no user input, fill from outlook
        if new_entry.duration is None:
            new_entry.duration = console.outlook_item[0]
        if new_entry.category is None:
            new_entry.category = console.outlook_item[1]
        if new_entry.comment == "" or new_entry.comment is None:
            new_entry.comment = console.outlook_item[2]

    if new_entry and new_entry.duration != 0:
        console.add_entry(new_entry)
        print(console.time_entries[-1])


@dc.ConsoleCommand(name="clear")
def clear_entries(console) -> None:
    """Delete all entered data."""
    console.time_entries = []


@dc.ConsoleCommand(name="clip", aliases=["copy"])
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


@dc.ConsoleCommand(name="list", aliases=["ls"])
def list_categories_and_tasks(console):
    """Display available category & account codes."""
    for dictionary, name in [
        (console.config.task_list, "TASKS"),
        (console.config.category_list, "CATEGORIES"),
    ]:  # pragma: no cover
        disp_dict(dictionary, name)
        print()


@dc.ConsoleCommand(name="preview", aliases=["p"])
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


@dc.ConsoleCommand(name="scale", aliases=["s"])
def scale_time_entries(console: ConsoleSession, target_total: str) -> None:
    """Scale time entries by weighted average to sum to a target total duration."""
    if not is_float(target_total):
        raise dc.InputError(f"Cannot convert {target_total} to float.")
    if float(target_total) == 0:
        raise dc.InputError("Cannot scale to zero.")
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


# TODO: Fix crash with multiple arguments (e.g. 'd - 1' command causes crash)
@dc.ConsoleCommand(name="date", aliases=["d"])
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
            raise dc.InputError("Date cannot be in the future.")
        new_date = datetime.date.today() + datetime.timedelta(days=date_delta)

    try:
        new_date = datetime.date.fromisoformat(datestr) if not new_date else new_date
    except ValueError as err:
        raise dc.InputError(f"Error: Invalid date: {datestr}. See 'help date' for more info.")
    else:
        if new_date > datetime.date.today():
            raise dc.InputError("Date cannot be in the future")

        console.date = new_date
        print(f"Date set to {console.date.isoformat()}")


@dc.ConsoleCommand(name="undo", aliases=["u", "z"])
def undo_last(console) -> None:
    """Undo last entry."""
    console.time_entries = console.time_entries[:-1]


@dc.ConsoleCommand(name="write", aliases=["c", "commit"])
def write_db(console: ConsoleSession, input_type: str = "user") -> None:  # pragma: no cover
    """
    Permanently commit time entries to the database.

    Database is in ~/.titr/titr.db by default. Run titr --testdb
    to use a test database file in the working directory.

    Entries are copied to clipboard for those still using Excel.
    """

    if len(console.time_entries) == 0:
        raise dc.InputError("Nothing to commit. Get back to work.")

    # TODO: Store task & category lists exclusively in the database
    # modifiable through the program

    # Write metadata about the current session, and get the session id
    session_id: int = db_session_metadata(console.db_connection, input_type=input_type)

    # Write the time entries to the database
    db_write_time_log(console, session_id)

    # Clear all time entries so they aren't entered a second time
    clear_entries(console)
    print(f"Commited entries to {TITR_DB}.")


@dc.ConsoleCommand(name="timecard", aliases=["tc"])
def show_weekly_timecard(console: ConsoleSession) -> float:
    """
    Show timecard summary for this week.

    To show summary for a different week, set the date
    to any day within the week of interest using the date command.

    Weeks start on Monday."""
    week_start: datetime.date = console.date - datetime.timedelta(days=console.date.weekday())
    week_end: datetime.date = week_start + datetime.timedelta(days=6)
    cursor = console.db_connection.cursor()

    get_totals_by_task: str = """--sql
        SELECT t.name, sum(l.duration), t.user_key FROM time_log l
        JOIN tasks t ON t.id = l.task_id
        WHERE l.date >= (?) AND l.date <= (?)
        GROUP BY l.task_id;
    """
    cursor.execute(
        get_totals_by_task,
        [week_start, week_end],
    )
    totals_by_task: list[tuple[str, float, str]] = cursor.fetchall()
    week_total_hours = _sum_grouped_tasks(totals_by_task)

    col_widths = [30, 8, 15, 12]
    if week_total_hours > 0:
        total_incidental: float = _sum_grouped_tasks(
            filter(lambda x: x[2] in console.config.incidental_tasks, totals_by_task)
        )
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
                # TODO: Error handling in case of all incidental time
                try:
                    task_percentage: float = task[1] / (week_total_hours - total_incidental)
                except ZeroDivisionError:
                    task_percentage = float("nan")
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
            + "{:{}}{:<{}.2f}".format("", col_widths[0], week_total_hours, col_widths[1])
            + Style.RESET_ALL
        )
    else:
        print("No time entered for this week.")

    return week_total_hours


@dc.ConsoleCommand(name="deepwork", aliases=["dw"])
def deep_work(console: ConsoleSession) -> None:  # pragma: no cover
    """
    Show total deep work and deep work over past 365 days.

    Deep work goal currently set in source code to 300 hours."""
    dw_total: float
    dw_last_365: float
    dw_total, dw_last_365 = _query_deep_work(console)
    if dw_total <= 0:
        print("No deep work hours found.")
        return None

    w1, w2, w3, w4 = 15, 12, 18, 15  # column widths
    print(
        Style.BRIGHT
        + "{:{}}{:{}}{:{}}{:{}}".format(
            "DEEP WORK", w1, "TOTAL", w2, "LAST 365 DAYS", w3, "GOAL", w4
        )
        + Style.NORMAL
    )
    goal_color: str = Fore.GREEN if dw_last_365 >= console.config.deep_work_goal else Fore.RED
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


@dc.ConsoleCommand(name="outlook", aliases=["o"], enabled=OUTLOOK_ENABLED)
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
            raise dc.InputError(f"No outlook items found for {console.date}")

        # Allow blank entries to be mapped to add_item command
        dc.set_pattern("add_entry", outlook_entry_pattern)
        # Disable commands in the console
        disabled_commands = "date write quit".split(" ")
        for cmd in disabled_commands:
            dc.disable_command(cmd)

        print(f"Found total of {num_items} events for {console.date}:")
        # console._set_outlook_mode()
        for item in outlook_items:
            if (
                (item.AllDayEvent is True and console.config.skip_all_day_events is True)
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
            # TODO: Consider refactoring this to be a TimeEntry object
            console.outlook_item = (duration, category, comment)
            command = dc.get_input(
                session_args=console,
                break_commands=["add_entry", "null_cmd", "quit"],
                prompt=event_str,
            )
            console.outlook_item = None
            if command.name == "quit":
                break

        # Reenable commands
        dc.set_pattern("add_entry", time_entry_pattern)
        for cmd in disabled_commands:
            dc.enable_command(cmd)
        preview_output(console)


@dc.ConsoleCommand(name="import")
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

    cursor = console.db_connection.cursor()
    session_id: int = db_session_metadata(console.db_connection, input_type="import_from_csv")
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
                    entry_date: datetime.date = datetime.date(int(year), int(month), int(day))
                except ValueError:
                    print(f"Warning: {row_num=} has invalid date {row[0]}. Skipping entry.")
                    continue

                # convert the entry duration
                try:
                    entry_duration = float(row[1])
                except ValueError:
                    print(f"Warning: {row_num=} has invalid duration {row[1]}. Skipping entry.")
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


@dc.ConsoleCommand(name="export")
def export_to_csv(
    console: ConsoleSession,
    csv_file_path: str = "titr_export.csv",
) -> int:
    """
    Export database entries to csv.

    Default export to titr_export.csv in working directory
    Export path can be specified as default argument.

    Exports CSV file with header row.
    Columns Date, Duration, Task, Category, and Comment
    """
    csv_export_q = """--sql
        SELECT l.date, l.duration, t.name, c.name, l.comment
        FROM time_log l
        JOIN categories c ON c.id=l.category_id
        JOIN tasks t ON t.id=l.task_id
    """
    cursor = console.db_connection.cursor()
    cursor.execute(csv_export_q)
    data = cursor.fetchall()
    if len(data) < 1:
        print("No data to export.")
        return 0
    with open(csv_file_path, "w", newline="") as csv_handle:
        writer = csv.writer(csv_handle)
        writer.writerow(["Date", "Duration", "Task", "Category", "Comment"])
        writer.writerows(data)

    print(f"Exported {len(data)} rows to {csv_file_path}.")
    return len(data)


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


def get_outlook_items(search_date: datetime.date, calendar_name: str, outlook_account: str):
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
        event.strip() for event in parser["outlook_options"]["skip_event_names"].split(",")
    ]
    # TODO: Error handling
    config.skip_event_status = [
        int(status) for status in parser["outlook_options"]["skip_event_status"].split(",")
    ]
    config.skip_all_day_events = parser.getboolean("outlook_options", "skip_all_day_events")

    return config


def _parse_time_entry(console: ConsoleSession, raw_input: str) -> Optional[TimeEntry]:
    """Parse a user input into a time entry.

    Returns None for blank entry
    Else returns a dict to be passed to a new TimeEntry"""
    if raw_input == "":
        return None
    user_input: List[str] = raw_input.split(" ")
    try:
        duration = float(user_input[0])
    except ValueError as err:
        raise dc.InputError(err)
    if math.isnan(duration):
        raise dc.InputError("Nice try, but I'm nan-plussed.")
    if duration > console.config.max_duration:
        raise dc.InputError("You're working too much.")
    if duration < 0:
        raise dc.InputError("You can't unwork.")
    new_entry = TimeEntry(duration)
    #  time_entry_arguments: dict = {"duration": duration}
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
            new_entry.category = int(cat_key)
            new_entry.task = task
            if comment:
                new_entry.comment = " ".join(comment).strip()
        # Category argument, no task argument
        case (str(cat_key), *comment) if (
            is_float(cat_key) and int(cat_key) in console.config.category_list.keys()
        ):
            new_entry.category = int(cat_key)
            if comment:
                new_entry.comment = " ".join(comment).strip()
        # task argument, no category argument
        case (str(task), *comment) if (
            not is_float(task) and task.lower() in console.config.task_list.keys()
        ):
            new_entry.task = task
            if comment:
                new_entry.comment = " ".join(comment).strip()
        # Comment only
        case (str(cat_key), str(task), *comment) if (
            not is_float(cat_key) and task.lower() not in console.config.task_list.keys()
        ):
            new_comment: str = (cat_key + " " + task + " " + " ".join(comment)).strip()
            if new_comment:
                new_entry.comment = "".join(new_comment).strip()
        case comment:
            new_entry.comment = " ".join(comment).strip()

    return new_entry


def _start_timed_activity(cs: ConsoleSession, user_args: argparse.Namespace) -> None:
    """Start timing an activity using the --start flag
    from the command line."""
    # add zero in front to ensure pattern match and zero duration
    input_str: str = "0 " + " ".join(user_args)
    timed_entry: Optional[TimeEntry] = _parse_time_entry(cs, input_str)
    if timed_entry is None:
        raise Exception("_parse_time_entry returned None, expected TimeEntry instance.")
    timed_entry.start_ts = datetime.datetime.today()
    cs.add_entry(timed_entry, set_defaults=False)

    print(f"Starting Activity Timer at {timed_entry.start_ts.strftime('%D %X')}")
    print(  # TODO: Clean up & prettify formatting
        f"Task: {timed_entry.tsk_str}. "
        + f"Category: {timed_entry.cat_str}. "
        + f"Comment: {timed_entry.comment}"
    )

    # write the entry to the database
    write_db(cs, input_type="command")

    # exit titr
    exit(0)


def _end_timed_activity(cs: ConsoleSession, user_args: argparse.Namespace) -> None:
    """Stop timing an activity using the --end flag
    from the command line. Preview what will be entered
    into the database prior to committing it."""

    # search the databse for an active entry
    query_last_zero_entry = """--sql
        SELECT l.id, l.start_ts, l.comment FROM time_log l
        JOIN sessions s ON s.id = l.session_id
        WHERE l.duration = 0
        AND l.end_ts IS NULL
        AND s.input_type = 'command'
        ORDER BY l.id DESC limit 1
    """
    cursor = cs.db_connection.cursor()
    cursor.execute(query_last_zero_entry)
    last_entry = cursor.fetchone()

    if last_entry is None:  # exit if none found
        print("No tasks in progress. Use titr --start to start one.")
        exit(0)
    entry_id, start_ts, comment = last_entry

    query_task = """--sql
        SELECT t.user_key FROM time_log l
        JOIN tasks t ON t.id = l.task_id
        WHERE l.id = (?)
    """
    cursor.execute(query_task, [entry_id])
    task_id = _fetch_first(cursor)

    query_category = """--sql
        SELECT c.user_key FROM time_log l
        JOIN categories c ON c.id = l.category_id
        WHERE l.id = (?)
    """
    cursor.execute(query_category, [entry_id])
    category_id = _fetch_first(cursor)

    # convert timestamp stored in database to datetime object
    start_ts = datetime.datetime.strptime(start_ts, "%Y-%m-%d %X.%f")

    # use 0 duration for _parse_time entry
    input_str = "0 " + " ".join(user_args)
    final_entry: Optional[TimeEntry] = _parse_time_entry(cs, input_str)
    if final_entry is None:
        raise Exception("_parse_time_entry returned None, expected TimeEntry instance.")
    final_entry.time_log_id = entry_id
    final_entry.date = datetime.date.today()
    final_entry.start_ts = start_ts
    final_entry.end_ts = datetime.datetime.today()
    if final_entry.start_ts is None or final_entry.end_ts is None:
        raise TypeError("Found NoneType in final_entry start and/or end timestamps.")
    final_entry.duration = (final_entry.end_ts - final_entry.start_ts).total_seconds() / 3600
    final_entry.comment = (
        comment + " " + final_entry.comment if final_entry.comment or comment else None
    )

    def _prioritize(initial_entry, final_entry, default):
        """Apply logic for task and category entries.
        Prioritize final entry, then initial entry, then default."""
        if final_entry is not None:
            return final_entry
        if initial_entry is None:
            return default
        return initial_entry

    final_entry.category = int(
        _prioritize(category_id, final_entry.category, cs.config.default_category)
    )
    final_entry.task = _prioritize(task_id, final_entry.task, cs.config.default_task)
    cs.add_entry(final_entry)

    print("The following entry will be added to the database:")
    print(cs.time_entries[-1])

    # write the entry to the database
    confirm = input("Enter 'y' to confirm, 'delete' to remove task, any other key to exit: ")
    if confirm.lower() == "y":
        write_db(cs, input_type="command")
    elif confirm.lower() == "delete":
        del_task = "DELETE FROM time_log WHERE id=(?)"
        cursor.execute(del_task, [entry_id])
        cs.db_connection.commit()

    # exit titr
    exit(0)


######################
# DATABASE FUNCTIONS #
######################
def db_initialize(test_flag: bool = False) -> sqlite3.Connection:
    """Initialize the database, and create all tables."""
    db_connection = sqlite3.connect(TITR_DB)
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
            comment TEXT,
            start_ts TIMESTAMP,
            end_ts TIMESTAMP
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
    db_connection.commit()

    # Check that version is correct
    cursor.execute("PRAGMA user_version")
    user_version = cursor.fetchone()[0]
    if user_version != __db_user_version__:
        db_update_version(db_connection, user_version)

    return db_connection


def db_update_version(db_connection: sqlite3.Connection, user_version: int) -> int:
    """Update the sqlite3 database from an older version.
    Return the new version number."""
    cursor = db_connection.cursor()

    print(f"Updating database from version {user_version} to {__db_user_version__}...")

    def _get_column_names(table_name: str) -> list[str]:
        """Get the column names from a table."""
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [col[1] for col in cursor.fetchall()]

    if user_version < 1:
        # Rename key to user_key in tasks
        task_columns = _get_column_names("tasks")
        if "user_key" not in task_columns:
            print(" Rename key to user_key in tasks...")
            cursor.execute("ALTER TABLE tasks RENAME COLUMN key TO user_key")

        # Add user_key to categories table
        categories_columns = _get_column_names("categories")
        if "user_key" not in categories_columns:
            print(" Add user_key to categories table...")
            cursor.execute("ALTER TABLE categories ADD COLUMN user_key TEXT")

        # Add input_type to sessions table
        sessions_columns = _get_column_names("sessions")
        if "input_type" not in sessions_columns:
            print(" Add input_type to sessions table...")
            cursor.execute("ALTER TABLE sessions ADD COLUMN input_type TEXT")

    if user_version < 2:
        # Add start and end timestamps to time log
        time_log_columns = _get_column_names("time_log")
        if "start_ts" not in time_log_columns:
            print(" Add start_ts to time_log table...")
            cursor.execute("ALTER TABLE time_log ADD COLUMN start_ts TEXT")
        if "end_ts" not in time_log_columns:
            print(" Add end_ts to time_log table...")
            cursor.execute("ALTER TABLE time_log ADD COLUMN end_ts TEXT")

    # Set the user version to the current version
    cursor.execute("PRAGMA user_version={}".format(__db_user_version__))
    db_connection.commit()
    print("Complete.")

    return __db_user_version__


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


def _fetch_first(cursor: sqlite3.Cursor, default: Optional[Any] = None) -> Optional[Any]:
    """Given the result of an sql query from a cursor.fetchone()
    call, return the first element if it exists.

    Adjust the default keyword argument if default other than
    None is desired"""
    query_result = cursor.fetchone()
    return default if query_result is None else query_result[0]


def db_write_time_log(console: ConsoleSession, session_id: int) -> None:
    """Write time entries from console session to database."""
    cursor = console.db_connection.cursor()
    write_entry = """--sql
        INSERT INTO time_log (date, duration, category_id, task_id, comment, session_id, start_ts, end_ts)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    update_entry = """--sql
        UPDATE time_log SET (date, duration, category_id, task_id, comment, session_id, start_ts, end_ts) =
        (?, ?, ?, ?, ?, ?, ?, ?)
        WHERE id = (?)
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
        task_id = _fetch_first(cursor)
        cursor.execute(get_category_id, [entry.category])
        category_id = _fetch_first(cursor)
        entry_parameters = [
            entry.date,
            entry.duration,
            category_id,
            task_id,
            entry.comment,
            session_id,
            entry.start_ts,
            entry.end_ts,
        ]
        if entry.time_log_id is not None:
            # update existing entry
            entry_parameters.append(entry.time_log_id)
            cursor.execute(update_entry, entry_parameters)
        else:
            cursor.execute(write_entry, entry_parameters)
    console.db_connection.commit()


def parse_args() -> argparse.Namespace:
    """Initialize the argument parser and available command line arguments.
    Return the argument namespace."""
    parser = argparse.ArgumentParser(description=WELCOME_MSG)
    group = parser.add_mutually_exclusive_group()
    if OUTLOOK_ENABLED:
        group.add_argument(
            "--outlook", "-o", action="store_true", help="start titr in outlook mode"
        )
    else:
        parser.set_defaults(outlook=False)
    parser.add_argument(
        "--testdb",
        action="store_true",
        help="use a test database file in the local folder",
    )
    group.add_argument(
        "--start",
        nargs="*",
        metavar="category task comment",
        help="Start timing your work.",
    )
    group.add_argument(
        "--end",
        nargs="*",
        metavar="category task comment",
        help="Stop timing your work.",
    )
    args = parser.parse_args()

    return args


def _query_deep_work(console: ConsoleSession) -> tuple[float, float]:
    """Query the database for deep work hours.
    Returns tuple of total and total over past 365 days."""
    cursor = console.db_connection.cursor()

    get_dw_total = """--sql
        SELECT sum(duration) FROM time_log t
        JOIN categories c on t.category_id=c.id
        WHERE c.name = 'Deep Work'
    """
    cursor.execute(get_dw_total)
    dw_total = _fetch_first(cursor)
    if dw_total is None:
        return 0.0, 0.0

    get_dw_last_365 = get_dw_total + " AND date>=(?)"
    last_year = datetime.date.today() - datetime.timedelta(days=365)
    cursor.execute(get_dw_last_365, [last_year])
    dw_last_365 = _fetch_first(cursor)
    if dw_last_365 is None:
        dw_last_365 = 0.0

    return dw_total, dw_last_365


def _sum_grouped_tasks(tasks: list[tuple[str, float, str]]) -> float:
    return sum((item[1] for item in tasks))


if __name__ == "__main__":
    main()
