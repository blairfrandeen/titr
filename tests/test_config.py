import pytest
import configparser

import titr
from titr.config import create_default_config, load_config
from test_titr import console, db_connection, titr_default_config


def test_default_config(titr_default_config):
    test_config = configparser.ConfigParser()
    test_config.read(titr_default_config)
    for section in [
        "outlook_options",
        "general_options",
        "categories",
        "tasks",
        "incidental_tasks",
    ]:
        assert section in test_config.sections()

    # expect failure if config already exists
    with pytest.raises(FileExistsError):
        create_default_config()


def test_load_config(titr_default_config, console, monkeypatch):
    def _mock_create_default():
        return titr_default_config

    #  monkeypatch.setattr(console, "load_config", lambda: titr_default_config)
    monkeypatch.setattr(titr.config, "create_default_config", lambda: titr_default_config)
    console.config = load_config(config_file="none")
    assert console.config.category_list[2] == "Deep Work"
    assert console.config.category_list[3] == "Email"
    assert console.config.task_list["i"] == "Incidental"
    assert console.config.task_list["d"] == "Default Task"
    assert console.config.default_task == "i"
    assert console.config.default_category == 2
    assert console.config.skip_all_day_events is True
    assert console.config.skip_event_status == [0, 3]
    assert console.config.incidental_tasks == ["i"]
    assert console.config.skip_event_names == ["Lunch", "Meeting"]
    configparser.ConfigParser()
