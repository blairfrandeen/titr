import configparser
import datetime
from argparse import ArgumentError
from dataclasses import dataclass
from typing import Optional

import pyperclip
import pytest

import titr_main as titr  # TODO: clean up into more pure import


TEST_DB = ":memory:"
#  TEST_DB = "testdb.db"


@pytest.fixture
def db_connection(monkeypatch):
    # Remove old database file if it exists
    if TEST_DB != ":memory:":
        os.remove(TEST_DB)
    monkeypatch.setattr("titr_main.TITR_DB", TEST_DB)
    connection = titr.db_initialize(test_flag=True)
    yield connection
    connection.commit()
    connection.close()


@pytest.fixture
def console(monkeypatch, db_connection):
    monkeypatch.setattr(titr, "db_initialize", lambda: db_connection)
    cs = titr.ConsoleSession()
    yield cs


@pytest.fixture
def time_entry(
    date=datetime.date.today(),
    duration=1,
    category=2,
    task="i",
    comment="default test entry",
):
    te = titr.TimeEntry(
        duration=duration,
        date=date,
        category=category,
        task=task,
        comment=comment,
    )
    yield te


@pytest.fixture
def titr_default_config(monkeypatch, tmp_path):
    test_config_path = tmp_path / "test.ini"
    monkeypatch.setattr(titr, "CONFIG_FILE", test_config_path)
    monkeypatch.setattr("builtins.input", lambda _: "yourname@example.com")
    titr.create_default_config()
    test_config = configparser.ConfigParser()

    # Add some illegal entries
    test_config.read(test_config_path)
    test_config.set("categories", "bad_cat_key", "meow!")
    test_config.set("tasks", "long_key", "not allowed!")
    test_config.set("tasks", "8", "digits not allowed!")
    test_config.set("general_options", "default_category", "0")
    test_config.set("general_options", "default_task", "too long")
    test_config.set("outlook_options", "skip_event_names", "Lunch, Meeting")
    with open(test_config_path, "w") as cfg_fh:
        test_config.write(cfg_fh)
    yield test_config_path


def test_query_dw(console, monkeypatch, time_entry):
    """Cases to test:
    - No deep work at all
    - DW total, but none in last 365
    - DW in past 365
    """
    dw_total, dw_last_yr = titr._query_deep_work(console)
    assert dw_total == 0
    assert dw_last_yr == 0

    console.add_entry(
        titr.TimeEntry(category=2, date=datetime.date(1984, 6, 17), duration=11.53)
    )
    titr.write_db(console)
    dw_total, dw_last_yr = titr._query_deep_work(console)
    assert dw_total == 11.53
    assert dw_last_yr == 0

    console.add_entry(
        titr.TimeEntry(category=2, date=datetime.date.today(), duration=8)
    )
    titr.write_db(console)
    dw_total, dw_last_yr = titr._query_deep_work(console)
    assert dw_total == 19.53
    assert dw_last_yr == 8


def test_timecard(console):
    # set console to arbitrary date in past
    console.date = datetime.date(2020, 8, 6)  # weekday = 3 (thurs)

    # test case with no entries
    assert titr.show_weekly_timecard(console) is None

    # Add time entries before, after, and within date range
    for date_tuple in [
        (2020, 7, 1),  # before current week
        (2020, 8, 2),  # sunday before
        (2020, 8, 3),  # monday
        (2020, 8, 5),
        (2020, 8, 7),
        (2020, 8, 9),  # sunday
        (2020, 8, 10),  # monday after
        (2020, 9, 11),  # after current week
    ]:
        console.add_entry(titr.TimeEntry(duration=1, date=datetime.date(*date_tuple)))

    # Commit to the database
    titr.write_db(console)

    # Should have 4x one hour entries
    assert titr.show_weekly_timecard(console) == 4


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
        titr.create_default_config()


def test_load_config(titr_default_config, console, monkeypatch):
    def _mock_create_default():
        return titr_default_config

    #  monkeypatch.setattr(console, "load_config", lambda: titr_default_config)
    monkeypatch.setattr(titr, "create_default_config", lambda: titr_default_config)
    console.config = titr.load_config(config_file="none")
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


class MockTimeEntry:
    def __init__(
        self, duration, task="N", category=5, comment="", date=datetime.date.today()
    ):
        self.duration = duration
        self.category = category
        self.task = task
        self.comment = comment
        self.date = date

    def __str__(self):
        self_str: str = f"{self.duration}\t{self.category}\t{self.task}\t{self.comment}"
        return self_str


@pytest.mark.parametrize(
    "item, expected",
    [
        ("yankee", False),
        ("dOODlE", False),
        ("KLJF#*(@#!!", False),
        (".34", True),
        (".23191", True),
        ("0", True),
        ("-0", True),
        ("99", True),
        ("4e5", True),
        ("inf", True),
        (5, True),
        (4.1, True),
        (-4.23e-5, True),
        (False, True),
        ("NaN", True),
    ],
)
def test_is_float(item, expected):
    assert titr.is_float(item) is expected


def test_float_bad_inputs():
    definitely_not_floats = [[1, 2, 3], {1: "hi"}, None]
    for item in definitely_not_floats:
        with pytest.raises(TypeError):
            titr.is_float(item)


@pytest.mark.parametrize(
    "initial_times, user_input, expected_times",
    [
        ([2, 2], "5", [2.5, 2.5]),
        ([2, 2], "4", [2, 2]),
        (
            [
                2,
            ],
            "5",
            [5],
        ),
        ([3, 4], "6", [3 - 3 / 7, 4 - 4 / 7]),
        ([1, 2, 3], "7", [7 / 6, 14 / 6, 3.5]),
        ([4, 5, 6, 2], "17", [4, 5, 6, 2]),
        ([], "39", []),
        ([1, 2, 3], "not a float", titr.dc.InputError),
        ([1, 2, 3], "0", titr.dc.InputError),
    ],
)
def test_scale_duration(console, capsys, initial_times, user_input, expected_times):
    if not isinstance(expected_times, type):
        console.time_entries = []
        for duration in initial_times:
            console.add_entry(titr.TimeEntry(duration))
        titr.scale_time_entries(console, user_input)
        for index, entry in enumerate(console.time_entries):
            assert entry.duration == expected_times[index]
    else:
        with pytest.raises(expected_times):
            titr.scale_time_entries(console, user_input)


def test_preview(console, time_entry, capsys):
    console.add_entry(time_entry)
    titr.preview_output(console)
    captured = capsys.readouterr()
    assert "test entry" in captured.out
    assert len(captured.out.split("\n")) == 4


def test_copy(console, time_entry):
    pyperclip.copy("testing 123")
    titr.copy_output(console)
    clipboard = pyperclip.paste()
    assert clipboard == "testing 123"

    for _ in range(3):
        console.add_entry(time_entry)
    titr.copy_output(console)
    clipboard = pyperclip.paste()
    assert "test entry" in pyperclip.paste()
    assert len(clipboard.split("\n")) == 3
    assert len(clipboard.split("\n")[0].split("\t")) == 5


@pytest.mark.xfail
def test_time_entry(console):
    te = titr.TimeEntry(2)
    assert te.category == console.config.default_category
    assert te.task == console.config.default_task
    assert te.comment == ""


def test_clear(console, time_entry):
    console.time_entries = [time_entry, time_entry]
    titr.clear_entries(console)
    assert console.time_entries == []


def test_undo(console, time_entry):
    console.time_entries = [time_entry, time_entry]
    titr.undo_last(console)
    assert console.time_entries == [time_entry]
    titr.undo_last(console)
    assert console.time_entries == []
    titr.undo_last(console)
    assert console.time_entries == []


@pytest.mark.parametrize("user_input, expected", [("", True), ("nothing", False)])
def test_outlook_entry_pattern(user_input, expected, monkeypatch):
    monkeypatch.setattr("titr_main.time_entry_pattern", lambda _: False)
    assert titr.outlook_entry_pattern(user_input) == expected


def test_main(monkeypatch, capsys):
    # setup
    monkeypatch.setattr("builtins.input", lambda _: "q")
    monkeypatch.setattr("titr_main.db_initialize.__defaults__", (TEST_DB, False))

    @dataclass
    class MockArgs:
        """Mock class for argparse.Namespace"""

        outlook: bool = False
        testdb: bool = False
        start: Optional[list[str]] = None
        end: Optional[list[str]] = None

        def __contains__(self, name):
            return name in dir(self)

    args: MockArgs = MockArgs()
    monkeypatch.setattr("titr_main.parse_args", lambda: args)

    # Ensure testdb arg is working
    args.testdb = True
    with pytest.raises(SystemExit):
        titr.main()
        assert titr.TITR_DB == "titr_test.db"

    # Ensure outlook arg is working
    args.testdb = False
    args.outlook = True
    with pytest.raises(SystemExit):

        def _raise_in_err():
            """Error with dried grapes."""
            raise titr.dc.InputError("test error")

        monkeypatch.setattr("titr_main.import_from_outlook", lambda _: _raise_in_err())
        titr.main()
    captured = capsys.readouterr()
    assert "Using Test Database" in captured.out
    assert "test error" in captured.out

    # Ensure start and end args are working
    def _fake_call(arg):
        print(arg)

    monkeypatch.setattr(
        "titr_main._start_timed_activity", lambda *_: _fake_call("--start")
    )
    monkeypatch.setattr("titr_main._end_timed_activity", lambda *_: _fake_call("--end"))
    args.outlook = False
    args.start = ["test"]
    args.end = None
    with pytest.raises(SystemExit):
        titr.main()
    captured = capsys.readouterr()
    assert "--start" in captured.out
    args.end = ["test"]
    args.start = None
    with pytest.raises(SystemExit):
        titr.main()
    captured = capsys.readouterr()
    assert "--end" in captured.out


arg_combos = [
    (["--start", "--testdb"], True),
    (["--start", "--end"], False),
    (["--testdb", "--end"], True),
    (["--start", "--testdb", "--end"], False),
    (["--testdb", "--outlook"], True),
    (["--end", "--outlook"], False),
    (["--start", "--outlook"], False),
    (["--start", "--testdb", "--outlook"], False),
    (["--start", "--end", "--outlook"], False),
    (["--testdb", "--end", "--outlook"], False),
    (["--testdb", "--end", "--outlook", "--start"], False),
]


#  @pytest.mark.xfail
@pytest.mark.parametrize("sys_args, valid", arg_combos)
def test_parse_args(monkeypatch, sys_args, valid):
    monkeypatch.setattr("sys.argv", [""] + sys_args)
    monkeypatch.setattr("titr_main.OUTLOOK_ENABLED", True)
    if not valid:
        with pytest.raises(SystemExit):
            titr.parse_args()
    else:
        titr.parse_args()
        assert 1


valid_time_entries = [
    ("3", titr.TimeEntry(3)),
    ("1 2 i", titr.TimeEntry(1, task="i", category=2)),
    (
        "7 2 i test string",
        titr.TimeEntry(7, task="i", category=2, comment="test string"),
    ),
    (
        "7 2 i TEST STRING",
        titr.TimeEntry(7, task="i", category=2, comment="TEST STRING"),
    ),
    (
        '.87 i a really "fun" meeting?',
        titr.TimeEntry(0.87, task="i", comment='a really "fun" meeting?'),
    ),
    (
        ".5 2 doing it right",
        titr.TimeEntry(0.5, category=2, comment="doing it right"),
    ),
    (
        '1 "no comment lol"',
        titr.TimeEntry(1, comment='"no comment lol"'),
    ),
    (
        "1 onewordcomment",
        titr.TimeEntry(1, comment="onewordcomment"),
    ),
    (
        "0 2 i no entry",
        titr.TimeEntry(0, comment="no entry", category=2, task="i"),
    ),
    ("0", titr.TimeEntry(0)),
    ("", None),
]


@pytest.mark.parametrize("user_input, output_dict", valid_time_entries)
def test_parse_time_entry(console, user_input, output_dict):
    assert titr._parse_time_entry(console, user_input) == output_dict


@pytest.mark.parametrize(
    "invalid_entry",
    [
        "99 3 i working too much",
        "hi there!",
        "-1 2 i",
        "e9 34 q wtf",
        "nan lol",
    ],
)
def test_parse_invalid_entries(console, invalid_entry):
    with pytest.raises(titr.dc.InputError):
        titr._parse_time_entry(console, invalid_entry)


def test_add_entry(console, monkeypatch):
    mock_inputs = "1 2 i terst"
    mock_parse = titr.TimeEntry(
        5, category=3, comment="test item"
    )  # {"duration": 5, "category": 3, "comment": "test item"}

    monkeypatch.setattr(titr, "_parse_time_entry", lambda *_: mock_parse)
    titr.add_entry(console, mock_inputs)
    assert console.time_entries[0].duration == 5
    mock_parse.duration = 4
    titr.add_entry(console, mock_inputs)
    assert console.time_entries[1].duration == 4

    monkeypatch.setattr(titr, "_parse_time_entry", lambda *_: None)
    console.outlook_item = (1.234, 2, "test outlook")
    titr.add_entry(console, "0")
    assert console.time_entries[2].duration == 1.234
    assert console.time_entries[2].category == 2
    assert console.time_entries[2].comment == "test outlook"


@pytest.mark.parametrize(
    "test_input, expected",
    [
        (None, datetime.date.today()),
        ("1984-06-17", datetime.date(1984, 6, 17)),
        ("-1", datetime.date.today() + datetime.timedelta(days=-1)),
        ("-7", datetime.date.today() + datetime.timedelta(days=-7)),
        ("0", datetime.date.today()),
        ("", datetime.date.today()),
        ("12", None),
        ("not a date", None),
        ("6/17/84", None),
        ("2121-04-23", None),
    ],
)
def test_set_date(console, test_input, expected, monkeypatch):
    console.date = datetime.date(1941, 12, 7)  # set to arbitrary wrong date.
    if expected is not None:
        titr.set_date(console, test_input)
        assert console.date == expected
    else:

        with pytest.raises(titr.dc.InputError):
            titr.set_date(console, test_input)
