import configparser
import os

from dataclasses import dataclass, field
from titr import CONFIG_FILE


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
    source_file: str = ""


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

    config.source_file = config_file
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
    # print(f"Loaded config from {config_file=}")

    return config
