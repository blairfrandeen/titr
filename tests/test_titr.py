import configparser
import datetime
from argparse import ArgumentError
from dataclasses import dataclass
from typing import Optional

import os
import pandas as pd
import pyperclip
import pytest

import titr
from titr.titr_main import ConsoleSession, TimeEntry


TEST_DB = ":memory:"
#  TEST_DB = "testdb.db"


@pytest.fixture
def db_connection(monkeypatch):
    # Remove old database file if it exists
    if TEST_DB != ":memory:":
        os.remove(TEST_DB)
    connection = titr.database.db_initialize(TEST_DB)
    yield connection
    connection.commit()
    connection.close()


@pytest.fixture
def console(monkeypatch, db_connection):
    monkeypatch.setattr("titr.database.db_initialize", lambda **_: db_connection)
    cs = ConsoleSession()
    yield cs


@pytest.fixture
def time_entry(
    date=datetime.date.today(),
    duration=1,
    category=2,
    task="i",
    comment="default test entry",
):
    te = TimeEntry(
        duration=duration,
        date=date,
        category=category,
        task=task,
        comment=comment,
    )
    yield te


def test_query_dw(console, monkeypatch, time_entry):
    """Cases to test:
    - No deep work at all
    - DW total, but none in last 365
    - DW in past 365
    """
    dw_total, dw_last_yr = titr.titr_main._query_deep_work(console)
    assert dw_total == 0
    assert dw_last_yr == 0

    console.add_entry(TimeEntry(category=2, date=datetime.date(1984, 6, 17), duration=11.53))
    titr.titr_main.write_db(console)
    dw_total, dw_last_yr = titr.titr_main._query_deep_work(console)
    assert dw_total == 11.53
    assert dw_last_yr == 0

    console.add_entry(TimeEntry(category=2, date=datetime.date.today(), duration=8))
    titr.titr_main.write_db(console)
    dw_total, dw_last_yr = titr.titr_main._query_deep_work(console)
    assert dw_total == 19.53
    assert dw_last_yr == 8


def test_timecard(console):
    # set console to arbitrary date in past
    console.date = datetime.date(2020, 8, 6)  # weekday = 3 (thurs)

    # test case with no entries
    assert titr.titr_main.show_weekly_timecard(console) == 0

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
        console.add_entry(TimeEntry(duration=1, date=datetime.date(*date_tuple)))

    # Commit to the database
    titr.titr_main.write_db(console)

    # Should have 4x one hour entries
    assert titr.titr_main.show_weekly_timecard(console) == 4


class MockTimeEntry:
    def __init__(self, duration, task="N", category=5, comment="", date=datetime.date.today()):
        self.duration = duration
        self.category = category
        self.task = task
        self.comment = comment
        self.date = date

    def __str__(self):
        self_str: str = f"{self.duration}\t{self.category}\t{self.task}\t{self.comment}"
        return self_str


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
        ([1, 2, 3], "not a float", titr.datum_console.InputError),
        ([1, 2, 3], "0", titr.datum_console.InputError),
    ],
)
def test_scale_duration(console, capsys, initial_times, user_input, expected_times):
    if not isinstance(expected_times, type):
        console.time_entries = []
        for duration in initial_times:
            console.add_entry(TimeEntry(duration))
        titr.titr_main.scale_time_entries(console, user_input)
        for index, entry in enumerate(console.time_entries):
            assert entry.duration == expected_times[index]
    else:
        with pytest.raises(expected_times):
            titr.titr_main.scale_time_entries(console, user_input)


def test_preview(console, time_entry, capsys):
    console.add_entry(time_entry)
    titr.titr_main.preview_output(console)
    captured = capsys.readouterr()
    assert "test entry" in captured.out
    assert len(captured.out.split("\n")) == 4


def test_copy(console, time_entry):
    pyperclip.copy("testing 123")
    titr.titr_main.copy_output(console)
    clipboard = pyperclip.paste()
    assert clipboard == "testing 123"

    for _ in range(3):
        console.add_entry(time_entry)
    titr.titr_main.copy_output(console)
    clipboard = pyperclip.paste()
    assert "test entry" in pyperclip.paste()
    assert len(clipboard.split("\n")) == 3
    assert len(clipboard.split("\n")[0].split("\t")) == 5


@pytest.mark.xfail(
    reason="Incomplete test? Seems to only be testing dataclass. Should likely be testing add_entry"
)
def test_time_entry(console):
    te = TimeEntry(2)
    assert te.category == console.config.default_category
    assert te.task == console.config.default_task
    assert te.comment == ""


def test_clear(console, time_entry):
    console.time_entries = [time_entry, time_entry]
    titr.titr_main.clear_entries(console)
    assert console.time_entries == []


def test_undo(console, time_entry):
    console.time_entries = [time_entry, time_entry]
    titr.titr_main.undo_last(console)
    assert console.time_entries == [time_entry]
    titr.titr_main.undo_last(console)
    assert console.time_entries == []
    titr.titr_main.undo_last(console)
    assert console.time_entries == []


@pytest.mark.parametrize("user_input, expected", [("", True), ("nothing", False)])
def test_outlook_entry_pattern(user_input, expected, monkeypatch):
    monkeypatch.setattr("titr_main.time_entry_pattern", lambda _: False)
    assert titr.titr_main.outlook_entry_pattern(user_input) == expected


@pytest.mark.parametrize(
    "tasks, expected_sum",
    [
        ([("titr", 17.0, "t"), ("datum", 5.0, "d"), ("incidental", 3.5, "i")], 25.5),
        ([], 0),
        ((("titr", 17.0, "t"), ("datum", 5.0, "d"), ("incidental", 3.5, "i")), 25.5),
    ],
)
def test_sum_grouped_tasks(tasks, expected_sum):
    assert titr.titr_main._sum_grouped_tasks(tasks) == expected_sum


@pytest.mark.xfail(reason="work in progress")
@pytest.mark.parametrize(
    "inputs, expected",
    [
        (
            [("titr", 10, "t"), ("datum", 10, "d")],
            [("titr", 10, "t", 0.5), ("datum", 10, "t", 0.5)],
        )
    ],
)
def test_list_percentages(inputs, expected):
    assert 0


def test_daily_log(console):
    assert titr.titr_main.show_today_log(console, test_flag=True) is None

    e1 = TimeEntry(1, category=2)
    console.add_entry(e1)
    e2 = TimeEntry(5, category=3)
    console.add_entry(e2)
    titr.titr_main.write_db(console)

    log = titr.titr_main.show_today_log(console, test_flag=True)
    assert log["Duration"].sum() == 6


def test_work_modes(console):
    # Check for no-data case
    assert titr.titr_main.work_modes(console, test_flag=True) is None

    e1 = TimeEntry(1, category=2)
    console.add_entry(e1)
    e2 = TimeEntry(5, category=3)
    console.add_entry(e2)
    titr.titr_main.write_db(console)
    titr.titr_main.preview_output(console)

    modes = titr.titr_main.work_modes(console, test_flag=True)
    assert modes["duration"].sum() == 6
    assert modes["percent"].sum() == 1


def test_main(monkeypatch, capsys):
    # setup
    monkeypatch.setattr("builtins.input", lambda _: "q")

    @dataclass
    class MockArgs:
        # Mock class for argparse.Namespace

        outlook: bool = False
        testdb: bool = False
        start: Optional[list[str]] = None
        end: Optional[list[str]] = None

        def __contains__(self, name):
            return name in dir(self)

    args: MockArgs = MockArgs()
    monkeypatch.setattr("titr.titr_main.parse_args", lambda: args)

    # Ensure testdb arg is working
    args.testdb = True
    with pytest.raises(SystemExit):
        titr.titr_main.main()
        assert titr.TITR_DB == "titr_test.db"

    # Ensure outlook arg is working
    args.testdb = False
    args.outlook = True
    with pytest.raises(SystemExit):

        def _raise_in_err():
            """Error with dried grapes."""
            raise titr.datum_console.InputError("test error")

        monkeypatch.setattr("titr.titr_main.import_from_outlook", lambda _: _raise_in_err())
        titr.titr_main.main()
    captured = capsys.readouterr()
    assert "Using Test Database" in captured.out
    assert "test error" in captured.out

    # Ensure start and end args are working
    def _fake_call(arg):
        print(arg)

    monkeypatch.setattr("titr.titr_main._start_timed_activity", lambda *_: _fake_call("--start"))
    monkeypatch.setattr("titr.titr_main._end_timed_activity", lambda *_: _fake_call("--end"))
    args.outlook = False
    args.start = ["test"]
    args.end = None
    with pytest.raises(SystemExit):
        titr.titr_main.main()
    captured = capsys.readouterr()
    assert "--start" in captured.out
    args.end = ["test"]
    args.start = None
    with pytest.raises(SystemExit):
        titr.titr_main.main()
    captured = capsys.readouterr()
    assert "--end" in captured.out


#  @pytest.mark.xfail
@pytest.mark.parametrize(
    "sys_args, valid",
    [
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
    ],
)
def test_parse_args(monkeypatch, sys_args, valid):
    monkeypatch.setattr("sys.argv", [""] + sys_args)
    monkeypatch.setattr("titr.titr_main.OUTLOOK_ENABLED", True)
    if not valid:
        with pytest.raises(SystemExit):
            titr.titr_main.parse_args()
    else:
        titr.titr_main.parse_args()
        assert 1


@pytest.mark.parametrize(
    "user_input, output_dict",
    [
        ("3", TimeEntry(3)),
        ("1 2 i", TimeEntry(1, task="i", category=2)),
        (
            "7 2 i test string",
            TimeEntry(7, task="i", category=2, comment="test string"),
        ),
        (
            "7 2 i TEST STRING",
            TimeEntry(7, task="i", category=2, comment="TEST STRING"),
        ),
        (
            '.87 i a really "fun" meeting?',
            TimeEntry(0.87, task="i", comment='a really "fun" meeting?'),
        ),
        (
            ".5 2 doing it right",
            TimeEntry(0.5, category=2, comment="doing it right"),
        ),
        (
            '1 "no comment lol"',
            TimeEntry(1, comment='"no comment lol"'),
        ),
        (
            "1 onewordcomment",
            TimeEntry(1, comment="onewordcomment"),
        ),
        (
            "0 2 i no entry",
            TimeEntry(0, comment="no entry", category=2, task="i"),
        ),
        ("0", TimeEntry(0)),
        ("", None),
    ],
)
def test_parse_time_entry(console, user_input, output_dict):
    assert titr.titr_main._parse_time_entry(console, user_input) == output_dict


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
    with pytest.raises(titr.datum_console.InputError):
        titr.titr_main._parse_time_entry(console, invalid_entry)


def test_add_entry(console, monkeypatch):
    mock_inputs = "1 2 i terst"
    mock_parse = TimeEntry(
        5, category=3, comment="test item"
    )  # {"duration": 5, "category": 3, "comment": "test item"}

    monkeypatch.setattr("titr.titr_main._parse_time_entry", lambda *_: mock_parse)
    titr.titr_main.add_entry(console, mock_inputs)
    assert console.time_entries[0].duration == 5
    mock_parse.duration = 4
    titr.titr_main.add_entry(console, mock_inputs)
    assert console.time_entries[1].duration == 4

    monkeypatch.setattr("titr.titr_main._parse_time_entry", lambda *_: None)
    console.outlook_item = (1.234, 2, "test outlook")
    titr.titr_main.add_entry(console, "0")
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
        titr.titr_main.set_date(console, test_input)
        assert console.date == expected
    else:

        with pytest.raises(titr.datum_console.InputError):
            titr.titr_main.set_date(console, test_input)
