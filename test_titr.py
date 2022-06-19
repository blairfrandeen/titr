import configparser
import datetime
import pytest
import titr
import pyperclip


@pytest.fixture
def console():
    cs = titr.ConsoleSession()
    yield cs


@pytest.fixture
def time_entry():
    te = titr.TimeEntry(2, category=6, comment="test entry")
    yield te


@pytest.fixture
def titr_default_config(monkeypatch, tmp_path):
    test_config_path = tmp_path / 'test.ini'
    monkeypatch.setattr(titr, "CONFIG_FILE", test_config_path)
    titr.create_default_config()
    test_config = configparser.ConfigParser()

    # Add some illegal entries
    test_config.read(test_config_path)
    test_config.set('categories', 'bad_cat_key', 'meow!')
    test_config.set('tasks', 'long_key', 'not allowed!')
    test_config.set('tasks', '8', 'digits not allowed!')
    with open(test_config_path, 'w') as cfg_fh:
        test_config.write(cfg_fh)
    yield test_config_path

def test_default_config(titr_default_config):
    test_config = configparser.ConfigParser()
    test_config.read(titr_default_config)
    for section in ['outlook_options', 'general_options', 'categories', 'tasks']:
        assert section in test_config.sections()

    # expect failure if config already exists
    with pytest.raises(FileExistsError):
        titr.create_default_config()


def test_load_config(titr_default_config, console, monkeypatch):
    def _mock_create_default():
        return titr_default_config
    monkeypatch.setattr(titr, 'create_default_config', lambda: titr_default_config)
    console.load_config()
    assert console.category_list[2] == 'Deep Work'
    assert console.category_list[3] == 'Email'
    assert console.task_list['i'] == 'Incidental'
    assert console.task_list['d'] == 'Default Task'
    test_config = configparser.ConfigParser()

class MockTimeEntry:
    def __init__(
        self, duration, account="N", category=5, comment="", date=datetime.date.today()
    ):
        self.duration = duration
        self.category = category
        self.account = account
        self.comment = comment
        self.date = date

    def __str__(self):
        self_str: str = (
            f"{self.duration}\t{self.category}\t{self.account}\t{self.comment}"
        )
        return self_str


alias_tests = [
    (("d", "date"), True),
    (("o", "outlook"), True),
    (("quit", "quit"), True),
    (("x", "not a command"), False),
    (("?", "undo"), False),
]


@pytest.mark.parametrize("item, expected", alias_tests)
def test_is_alias(console, item, expected):
    assert console._is_alias(*item) is expected


float_tests = [
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
]


@pytest.mark.parametrize("item, expected", float_tests)
def test_is_float(item, expected):
    assert titr.is_float(item) is expected


def test_float_bad_inputs():
    definitely_not_floats = [[1, 2, 3], {1: "hi"}, None]
    for item in definitely_not_floats:
        with pytest.raises(TypeError):
            titr.is_float(item)


def test_scale_duration(console, capsys):
    # initial list, scale total, final list
    scale_tests = [
        ([2, 2], 5, [2.5, 2.5]),
        ([2, 2], 4, [2, 2]),
        (
            [
                2,
            ],
            5,
            [5],
        ),
        ([3, 4], 6, [3 - 3 / 7, 4 - 4 / 7]),
        ([1, 2, 3], 7, [7 / 6, 14 / 6, 3.5]),
        ([4, 5, 6, 2], 17, [4, 5, 6, 2]),
        ([], 39, []),
    ]
    for test in scale_tests:
        console.time_entries = []
        for duration in test[0]:
            console.time_entries.append(titr.TimeEntry(duration))
        console.scale_time_entries(test[1])
        for index, entry in enumerate(console.time_entries):
            print(entry, index)
            assert entry.duration == test[2][index]

    console.time_entries = []
    console.scale_time_entries(3)
    captured = capsys.readouterr()
    assert "cannot scale from zero" in captured.out


def test_preview(console, time_entry, capsys):
    console.time_entries.append(time_entry)
    console.preview_output()
    captured = capsys.readouterr()
    assert "test entry" in captured.out


def test_copy(console, time_entry):
    console.time_entries.append(time_entry)
    console.copy_output()
    assert "test entry" in pyperclip.paste()


def test_set_outlook_mode(console):
    console._set_outlook_mode()
    cmd_list = console.command_list
    assert "outlook" not in cmd_list.keys()
    assert "date" not in cmd_list.keys()
    assert cmd_list["quit"][1] == console._set_normal_mode

    # def test_set_normal_mode(console):
    console._set_normal_mode()
    cmd_list = console.command_list
    assert "outlook" in cmd_list.keys()
    assert "date" in cmd_list.keys()
    assert cmd_list["quit"][1] == exit
    assert cmd_list["null_cmd"][1] is None


def test_time_entry():
    te = titr.TimeEntry(2)
    assert te.category == titr.DEFAULT_CATEGORY
    assert te.account == titr.DEFAULT_ACCOUNT
    assert te.comment == ""


def test_clear(console, time_entry):
    console.time_entries = [time_entry, time_entry]
    console.clear()
    assert console.time_entries == []


def test_undo(console, time_entry):
    console.time_entries = [time_entry, time_entry]
    console.undo_last()
    assert console.time_entries == [time_entry]
    console.undo_last()
    assert console.time_entries == []
    console.undo_last()
    assert console.time_entries == []


def test_main(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "q")
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
            "account": "i",
        },
    ),
    (
        "7 2 i test string",
        {
            "duration": 7,
            "category": 2,
            "account": "i",
            "comment": "test string",
        },
    ),
    (
        "7 2 i TEST STRING",
        {
            "duration": 7,
            "category": 2,
            "account": "i",
            "comment": "TEST STRING",
        },
    ),
    (
        '.87 i a really "fun" meeting?',
        {
            "duration": 0.87,
            "account": "i",
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
        "0 2 i no entry",
        {"duration": 0, "comment": "no entry", "category": 2, "account": "i"},
    ),
    ("0", {"duration": 0}),
    ("", None),
]


@pytest.mark.parametrize("user_input, output_dict", valid_time_entries)
def test_parse_new_entry(console, user_input, output_dict):
    assert console._parse_new_entry(user_input) == output_dict


@pytest.mark.parametrize(
    "invalid_entry",
    [
        "99 3 i working too much",
        "hi there!",
        "-1 2 i",
        "9 34 q wtf",
    ],
)
def test_parse_invalid_entries(console, invalid_entry):
    with pytest.raises(ValueError):
        console._parse_new_entry(invalid_entry)


def test_add_entry(console, monkeypatch):
    mock_inputs = ["0", "1 2 i terst"]
    mock_parse = {"duration": 5, "category": 3, "comment": "test item"}

    monkeypatch.setattr(console, "_parse_new_entry", lambda _: mock_parse)
    console._add_entry(mock_inputs)
    assert console.time_entries[0].duration == 5
    mock_parse["duration"] = 4
    console._add_entry(mock_inputs, outlook_item=(5, 3, "1"))
    assert console.time_entries[1].duration == 4
    mock_parse = None
    console._add_entry(mock_inputs, outlook_item=(2, 2, "5"))
    assert console.time_entries[2].duration == 2


def test_help_msg(console, monkeypatch, capsys):
    def _add_entry():  # pragma: no cover
        """add"""
        return None

    def _clear():  # pragma: no cover
        """clear"""
        return None

    _command_list = {
        "add": (["add"], _add_entry),
        "clear": (["clear"], _clear),
    }
    monkeypatch.setattr(console, "command_list", _command_list)
    console.help_msg()
    captured = capsys.readouterr()
    assert "['add']" in captured.out

    for cmd in _command_list.keys():
        console.help_msg(command=cmd)
        captured = capsys.readouterr()
        assert cmd in captured.out


def test_set_date(console, monkeypatch):
    console.set_date()
    assert console.date == datetime.date.today()

    console.set_date(datetime.date.fromisoformat("2022-06-17"))
    assert console.date == datetime.date(2022, 6, 17)

    with pytest.raises(TypeError):
        console.set_date("1941-12-07")


invalid_commands = [
    "help, I'm a bug",
    ".25*923",
    "Y",
    "45e12",
    "-2 4 g 'negative work'",
]


@pytest.mark.parametrize("cmd", invalid_commands)
def test_get_user_input_invalid(cmd, monkeypatch, console):
    monkeypatch.setattr("builtins.input", lambda _: cmd)
    with pytest.raises(ValueError):
        console.get_user_input()


def test_get_user_input(console, monkeypatch, capsys):
    valid_commands = {
        "clear": ["clear"],
        "copy_output": ["clip"],
        #  'commit':   ['c', 'commit'],
        "set_date": ["d", "date", "D", "d -1", "date 2013-08-05"],
        "import_from_outlook": ["O", "outlook"],
        "preview_output": ["p", "preview"],
        "list_categories_and_accounts": ["ls", "list"],
        "undo_last": ["z", "undo"],
        "scale_time_entries": ["s 9", "scale 10"],
        "help_msg": ["h", "help", "help scale", "help date", "add"],
        "_parse_new_entry": [".5 1 i j", "1 2 g test"],
        #  'exit':     ["q", "quit"],
    }
    for cmd, aliases in valid_commands.items():

        def _mock_alias_function(*args, **kwargs):
            print(f"mock alias function: {cmd}")

        monkeypatch.setattr(console, cmd, _mock_alias_function)
        for alias in aliases:
            monkeypatch.setattr("builtins.input", lambda _: alias)
            console.get_user_input()
            captured = capsys.readouterr()
            assert f"mock alias function: {cmd}" in captured.out

    monkeypatch.setattr("builtins.input", lambda _: "help me!")
    with pytest.raises(ValueError):
        console.get_user_input()

    monkeypatch.setattr("builtins.input", lambda _: "quit")
    with pytest.raises(SystemExit):
        console.get_user_input()

    def _mock_normal_mode():
        return None

    monkeypatch.setattr(console, "_set_normal_mode", _mock_normal_mode)
    monkeypatch.setitem(
        console.command_list, "quit", (["q", "quit"], console._set_normal_mode)
    )
    assert console.get_user_input() == 0


today = datetime.date.today()
valid_dates = [
    ("1984-06-17", datetime.date(1984, 6, 17)),
    ("-1", today + datetime.timedelta(days=-1)),
    ("-7", today + datetime.timedelta(days=-7)),
    ("0", today),
    ("12", None),
    ("not a date", None),
    ("6/17/84", None),
    ("2121-04-23", None),
]


@pytest.mark.parametrize("test_input, expected", valid_dates)
def test_parse_date(test_input, expected):
    if expected is not None:
        assert titr.parse_date(test_input) == expected
    else:
        with pytest.raises(ValueError):
            titr.parse_date(test_input)
