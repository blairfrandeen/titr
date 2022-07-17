import configparser
import datetime
import pytest
import titr
import pyperclip


TEST_DB = ":memory:"
#  TEST_DB = "testdb.db"


@pytest.fixture
def db_connection():
    # Remove old database file if it exists
    if TEST_DB != ":memory:":
        os.remove(TEST_DB)
    connection = titr.db_initialize(TEST_DB, test_flag=True)
    yield connection
    connection.commit()
    connection.close()


@pytest.fixture
def console(monkeypatch, db_connection):
    monkeypatch.setattr(titr, "db_initialize", lambda: db_connection)
    cs = titr.ConsoleSession()
    yield cs


@pytest.fixture
def time_entry(console):
    te = titr.TimeEntry(console, duration=2, comment="test entry")
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


#  @pytest.mark.xfail
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
        console.time_entries.append(
            titr.TimeEntry(console, duration=1, date=datetime.date(*date_tuple))
        )

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
        ([1, 2, 3], "not a float", TypeError),
        ([1, 2, 3], "0", ValueError),
    ],
)
def test_scale_duration(console, capsys, initial_times, user_input, expected_times):
    if not isinstance(expected_times, type):
        console.time_entries = []
        for duration in initial_times:
            console.time_entries.append(titr.TimeEntry(console, duration))
        titr.scale_time_entries(console, user_input)
        for index, entry in enumerate(console.time_entries):
            assert entry.duration == expected_times[index]
    else:
        with pytest.raises(expected_times):
            titr.scale_time_entries(console, user_input)


def test_preview(console, time_entry, capsys):
    console.time_entries.append(time_entry)
    titr.preview_output(console)
    captured = capsys.readouterr()
    assert "test entry" in captured.out
    assert len(captured.out.split("\n")) == 4


def test_copy(console, time_entry):
    for _ in range(3):
        console.time_entries.append(time_entry)
    titr.copy_output(console)
    clipboard = pyperclip.paste()
    assert "test entry" in pyperclip.paste()
    assert len(clipboard.split("\n")) == 3
    assert len(clipboard.split("\n")[0].split("\t")) == 5


def test_time_entry(console):
    te = titr.TimeEntry(console, 2)
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


def test_main(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "q")
    monkeypatch.setattr("titr.db_initialize.__defaults__", (TEST_DB, False))
    with pytest.raises(SystemExit):
        titr.main()


valid_time_entries = [
    (
        "3",
        {
            "duration": 3,
        },
    ),
    (
        "1 2 i",
        {
            "duration": 1,
            "category": 2,
            "task": "i",
        },
    ),
    (
        "7 2 i test string",
        {
            "duration": 7,
            "category": 2,
            "task": "i",
            "comment": "test string",
        },
    ),
    (
        "7 2 i TEST STRING",
        {
            "duration": 7,
            "category": 2,
            "task": "i",
            "comment": "TEST STRING",
        },
    ),
    (
        '.87 i a really "fun" meeting?',
        {
            "duration": 0.87,
            "task": "i",
            "comment": 'a really "fun" meeting?',
        },
    ),
    (
        ".5 2 doing it right",
        {
            "duration": 0.5,
            "category": 2,
            "comment": "doing it right",
        },
    ),
    (
        '1 "no comment lol"',
        {
            "duration": 1,
            "comment": '"no comment lol"',
        },
    ),
    (
        "1 onewordcomment",
        {
            "duration": 1,
            "comment": "onewordcomment",
        },
    ),
    (
        "0 2 i no entry",
        {"duration": 0, "comment": "no entry", "category": 2, "task": "i"},
    ),
    ("0", {"duration": 0}),
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
    ],
)
def test_parse_invalid_entries(console, invalid_entry):
    with pytest.raises(ValueError):
        titr._parse_time_entry(console, invalid_entry)


def test_add_entry(console, monkeypatch):
    mock_inputs = "1 2 i terst"
    mock_parse = {"duration": 5, "category": 3, "comment": "test item"}

    monkeypatch.setattr(titr, "_parse_time_entry", lambda *_: mock_parse)
    titr.add_entry(console, mock_inputs)
    assert console.time_entries[0].duration == 5
    mock_parse["duration"] = 4
    titr.add_entry(console, mock_inputs)
    assert console.time_entries[1].duration == 4


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
def test_set_date(console, test_input, expected):
    console.date = datetime.date(1941, 12, 7)  # set to arbitrary wrong date.
    if expected is not None:
        titr.set_date(console, test_input)
        assert console.date == expected
    else:
        with pytest.raises(ValueError):
            titr.set_date(console, test_input)
