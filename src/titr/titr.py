#!/usr/bin/python3

"""
titr - pronounced 'titter'

A time tracker CLI.
https://github.com/blairfrandeen/titr
"""

import configparser
import datetime
import os
from typing import Optional, Tuple, Dict, List, Callable, Any

CONFIG_FILE: str = os.path.join(os.path.expanduser("~"), ".titr", "titr.cfg")


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


class TimeEntry:
    def __init__(
        self,
        session,
        duration: float,
        category: int = None,
        task: str = None,
        comment: str = "",
        date: datetime.date = datetime.date.today(),
    ) -> None:
        self.duration: float = duration
        self.category = session.default_category if category is None else category
        self.task = session.default_task if task is None else task
        self.comment: str = comment
        self.date: datetime.date = date

        self.timestamp: datetime.datetime = datetime.datetime.today()
        self.date_str: str = self.date.isoformat()
        self.cat_str = session.category_list[self.category]
        self.tsk_str = session.task_list[self.task.lower()]

    def __repr__(self):
        return f"{self.date_str},{self.duration},{self.task},{self.category}"

    @property
    def tsv_str(self):  # pragma: no cover
        tsv_str: str = "".join(
            [
                self.date_str,
                "\t",
                str(self.duration),
                "\t",
                self.tsk_str,
                "\t",
                self.cat_str,
                "\t",
                self.comment,
            ]
        )
        return tsv_str

    def __str__(self):  # pragma: no cover
        # TODO: Improve formatting
        self_str: str = "".join(
            [
                self.date_str,
                "\t",
                str(round(self.duration, 2)),
                "\t\t",
                self.tsk_str,
                "\t\t",
                self.cat_str,
                "\t\t",
                self.comment,
            ]
        )
        return self_str


class ConsoleSession:
    def __init__(self) -> None:
        self.time_entries: List[TimeEntry] = []
        self.command_list: Dict[str, Tuple[List[str], Optional[Callable]]] = {
            "add": (["add"], self._add_entry),
            "clear": (["clear"], self.clear),
            "clip": (["clip"], self.copy_output),
            "commit": (["c", "commit"], None),  # not implemented
            "date": (["d", "date"], self.set_date),
            "help": (["h", "help"], self.help_msg),
            "list": (["ls", "list"], self.list_categories_and_tasks),
            "outlook": (["o", "outlook"], self.import_from_outlook),
            "null_cmd": ([""], None),
            "preview": (["p", "preview"], self.preview_output),
            "quit": (["q", "quit"], exit),
            "scale": (["s", "scale"], self.scale_time_entries),
            "undo": (["z", "undo"], self.undo_last),
        }
        self.date = datetime.date.today()
        exit.__doc__ = "Quit"
        self.load_config()

    def load_config(self, config_file=CONFIG_FILE):
        """Load and validate configuration options."""
        # look for a config file in the working directory
        # if it doesn't exist, create it with some default options
        if not os.path.isfile(config_file):
            config_file = create_default_config()
        config = configparser.ConfigParser()
        config.read(config_file)
        self.category_list = {}
        self.task_list = {}
        for key in config["categories"]:
            try:
                cat_key = int(key)
            except ValueError as err:
                print(f"Warning: Skipped category key {key} in {config_file}: {err}")
                continue
            self.category_list[cat_key] = config["categories"][key]
        for key in config["tasks"]:
            if len(key) > 1:
                print(f"Warning: Skipped task key {key} in {config_file}: len > 1.")
                continue
            if key.isdigit():
                print(f"Warning: Skipped task key {key} in {config_file}: Digit")
                continue
            self.task_list[key] = config["tasks"][key]

        self.default_task = config["general_options"]["default_task"]
        if self.default_task not in self.task_list.keys():
            print(
                "Warning: Default tasks '",
                self.default_task,
                "' not found in ",
                config_file,
            )
            self.default_task = list(self.task_list.keys())[0]

        # TODO: Error handling for default category as not an int
        self.default_category = int(config["general_options"]["default_category"])
        if self.default_category not in self.category_list.keys():
            self.default_category = int(list(self.category_list.keys())[0])
            print(
                "Warning: Default category '",
                self.default_category,
                "'not found in ",
                config_file,
            )

        # TODO: Error handling
        self.max_duration = float(config["general_options"]["max_entry_duration"])

        self.outlook_account = config["outlook_options"]["email"]
        self.calendar_name = config["outlook_options"]["calendar_name"]
        self.skip_event_names = [
            event.strip()
            for event in config["outlook_options"]["skip_event_names"].split(",")
        ]
        # TODO: Error handling
        self.skip_event_status = [
            int(status)
            for status in config["outlook_options"]["skip_event_status"].split(",")
        ]
        self.skip_all_day_events = config.getboolean(
            "outlook_options", "skip_all_day_events"
        )

    def get_user_input(self, outlook_item=None, input_str: str = "> ") -> Optional[int]:
        user_input: str = input(input_str)
        match user_input.split(" "):
            case [str(duration), *_] if is_float(duration):
                self._add_entry(user_input, outlook_item)
                return 1
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
                self.list_categories_and_tasks()
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
                self._add_entry(user_input, outlook_item)
                return 1
            case _:
                raise ValueError(f'Invalid input: "{user_input}"')

        return None

    def _add_entry(self, user_input: str, outlook_item=None) -> None:
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
        entry_args: Optional[Dict[Any, Any]] = self._parse_new_entry(user_input)
        if outlook_item:
            if not entry_args:
                entry_args = dict()
            for index, key in enumerate(["duration", "category", "comment"]):
                if key not in entry_args.keys():
                    entry_args[key] = outlook_item[index]
        if entry_args and entry_args["duration"] != 0:
            self.time_entries.append(TimeEntry(self, **entry_args))
            print(self.time_entries[-1])

    def _is_alias(self, alias: str, command: str) -> bool:
        """Test if a user command is an alias for a known command."""
        if command not in self.command_list.keys():
            return False
        return alias.lower() in self.command_list[command][0]

    def import_from_outlook(self) -> None:
        """Import appointments from outlook."""
        outlook_items = get_outlook_items(
            self.date, self.calendar_name, self.outlook_account
        )
        if outlook_items is not None:
            # Note: using len(outlook_items) or outlook_items.Count
            # will return an undefined value.
            num_items = sum(1 for _ in outlook_items)
            if num_items == 0:
                raise KeyError(f"No outlook items found for {self.date}")

            print(f"Found total of {num_items} events for {self.date}:")
            self._set_outlook_mode()
            for item in outlook_items:
                if item.AllDayEvent is True and self.skip_all_day_events is True:
                    continue
                if item.Subject in self.skip_event_names:
                    continue
                if item.BusyStatus in self.skip_event_status:
                    continue
                comment = item.Subject
                duration = item.Duration / 60  # convert minutes to hours

                # TODO: Accept multiple categories
                appt_category = item.Categories.split(",")[0].strip()
                category = self.default_category
                for key, cat in self.category_list.items():
                    if cat == appt_category:
                        category = key
                        break

                # TODO: Improve formatting
                cat_str = self.category_list[category]
                event_str = f"{comment}\n{cat_str} - {round(duration,2)} hr > "
                ui = None
                while ui != 1:
                    try:
                        ui = self.get_user_input(
                            outlook_item=(duration, category, comment),
                            input_str=event_str,
                        )
                    except ValueError as err:
                        print(err)

                    if ui == 0:
                        break

                # TODO: Better handling of quitting outlook mode
                if ui == 0:  # pragma: no cover
                    break

            self._set_normal_mode()
            self.preview_output()

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

    def set_date(self, new_date: datetime.date = datetime.date.today()) -> None:
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

    def _parse_new_entry(self, raw_input: str) -> Optional[dict]:
        """Parse a user input into a time entry.

        Returns None for blank entry
        Else returns a dict to be passed to a new TimeEntry"""
        if raw_input == "":
            return None
        user_input: List[str] = raw_input.split(" ")
        duration = float(user_input[0])
        if duration > self.max_duration:
            raise ValueError("You're working too much.")
        if duration < 0:
            raise ValueError("You can't unwork.")
        new_entry_arguments: dict = {"duration": duration}
        entry_args: List[str] = user_input[1:]
        match entry_args:
            # No arguments, add entry with all defaults
            case ([] | "" | None):
                pass
            # All arguments including comment
            case (str(cat_key), str(task), *comment) if (
                is_float(cat_key)
                and int(cat_key) in self.category_list.keys()
                and task.lower() in self.task_list.keys()
            ):
                new_entry_arguments["category"] = int(cat_key)
                new_entry_arguments["task"] = task
                if comment:
                    new_entry_arguments["comment"] = " ".join(comment).strip()
            # Category argument, no task argument
            case (str(cat_key), *comment) if (
                is_float(cat_key) and int(cat_key) in self.category_list.keys()
            ):
                new_entry_arguments["category"] = int(cat_key)
                if comment:
                    new_entry_arguments["comment"] = " ".join(comment).strip()
            # task argument, no category argument
            case (str(task), *comment) if (
                not is_float(task) and task.lower() in self.task_list.keys()
            ):
                new_entry_arguments["task"] = task
                if comment:
                    new_entry_arguments["comment"] = " ".join(comment).strip()
            # Comment only
            case (str(cat_key), str(task), *comment) if (
                not is_float(cat_key) and task.lower() not in self.task_list.keys()
            ):
                new_comment: str = (
                    cat_key + " " + task + " " + " ".join(comment)
                ).strip()
                if new_comment:
                    new_entry_arguments["comment"] = new_comment
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

    def copy_output(self) -> None:
        """Copy output to clipboard."""
        import pyperclip

        output_str: str = ""
        for entry in self.time_entries:
            output_str += entry.tsv_str

        pyperclip.copy(output_str)
        print("TSV Output copied to clipboard.")

    def preview_output(self) -> None:
        """Preview output."""
        print("DATE\t\tDURATION\tTASK\t\tCATEGORY\t\tCOMMENT")
        for entry in self.time_entries:
            print(entry)
        print(f"TOTAL\t\t{self.total_duration}")

    def undo_last(self) -> None:
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
    def total_duration(self) -> float:
        return round(sum([entry.duration for entry in self.time_entries]), 2)

    def list_categories_and_tasks(self):
        """Display available category & account codes."""
        for dictionary, name in [
            (self.task_list, "TASKS"),
            (self.category_list, "CATEGORIES"),
        ]:  # pragma: no cover
            disp_dict(dictionary, name)


def get_outlook_items(
    search_date: datetime.date, calendar_name: str, outlook_account: str
):
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


def parse_date(datestr: str) -> datetime.date:
    try:
        date_delta: int = int(datestr)
    except ValueError:
        pass
    else:
        if date_delta > 0:
            raise ValueError("Date cannot be in the future.")
        return datetime.date.today() + datetime.timedelta(days=date_delta)

    new_date: datetime.date = datetime.date.fromisoformat(datestr)
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


if __name__ == "__main__":
    main()
