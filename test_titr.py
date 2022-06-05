import pytest
import titr
import pyperclip

@pytest.fixture
def console():
    cs = titr.ConsoleSession()
    yield cs

@pytest.fixture
def time_entry():
    te = titr.TimeEntry(2, category=6, comment='test entry')
    yield te

def test_is_float():
    not_floats = ['yankee', 'doodle', 'foxtrot', '*@(#!)']
    for item in not_floats:
        assert titr.is_float(item) is False

    floats = ['.34', '0.2919', '-23.4', '0', '-0', '99', '4e5', 'inf']
    for item in floats:
        assert titr.is_float(item)

    more_floats = ['5', 5, 5.3, -4.23e-5, False, 'NaN']
    for item in more_floats:
        assert titr.is_float(item)

    definitely_not_floats = [[1,2,3], {1: 'hi'}, None]
    for item in definitely_not_floats:
        with pytest.raises(TypeError):
            titr.is_float(item)


def test_scale_duration(console, capsys):
    # initial list, scale total, final list
    scale_tests = [
        ([2, 2], 5, [2.5, 2.5]),
        ([2, 2], 4, [2, 2]),
        ([2, ], 5, [5]),
        ([3, 4], 6, [3 - 3/7, 4-4/7]),
        ([1,2,3], 7, [7/6, 14/6, 3.5]),
        ([4, 5, 6, 2], 17, [4, 5, 6, 2]),
        ([], 39, []),
    ]
    for test in scale_tests:
        console.time_entries = []
        for duration in test[0]:
            console.time_entries.append(
                titr.TimeEntry(duration))
        console.scale_time_entries(test[1])
        for index, entry in enumerate(console.time_entries):
            print(entry, index)
            assert entry.duration == test[2][index]

    console.time_entries = []
    console.scale_time_entries(3)
    captured = capsys.readouterr()
    assert 'cannot scale from zero' in captured.out

def test_preview(console, time_entry, capsys):
    console.time_entries.append(time_entry)
    console.preview_output()
    captured = capsys.readouterr()
    assert 'test entry' in captured.out

def test_copy(console, time_entry):
    console.time_entries.append(time_entry)
    console.copy_output()
    assert 'test entry' in pyperclip.paste()


def test_time_entry():
    te = titr.TimeEntry(2)
    assert te.category == titr.DEFAULT_CATEGORY
    assert te.account == titr.DEFAULT_ACCOUNT
    assert te.comment == ''

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
    monkeypatch.setattr('builtins.input', lambda _: 'q')
    with pytest.raises(SystemExit):
        titr.main()


class MockTimeEntry:
    def __init__(self, duration, account = 'N', category = 5, comment = ''):
        self.duration = duration
        self.category = category
        self.account = account
        self.comment = comment

    def __str__(self):
        self_str: str = f"{self.duration}\t{self.category}\t{self.account}\t{self.comment}"
        return self_str

def test_parse_new_entry(console, monkeypatch):
    default_acct = 'N'
    default_cat = 5
    monkeypatch.setattr(titr, 'TimeEntry', MockTimeEntry)
    # nested tuple to test parsing
    # first element is duration, processed in get_user_input
    # second element is split string, processed in get_user_input
    # second nested tuple is expected duration, account,
    # category, and comment string
    valid_time_entries = [
        (3, [], (3, default_cat, default_acct, '')),
        #  (1, ['2'], (1, 2, default_acct, '')),
        (1, '2 i'.split(' '), (1, 2, 'i', '')),
        (7, '2 i test string'.split(' '), (7, 2, 'i', 'test string')),
        (.8731, 'i test string'.split(' '), (.8731, default_cat, 'i', 'test string')),
        (0.25, '2 a damn good feeling is a damn good time, wait, "who wrote my rhyme"?'.split(' '),
            (0.25, 2, default_acct, 'a damn good feeling is a damn good time, wait, "who wrote my rhyme"?')
        ),
        (1, 'test string'.split(' '), (1, default_cat, default_acct, 'test string')),
    ]

    for entry in valid_time_entries:
        print(entry)
        duration, arg_str = entry[0], entry[1]
        console.time_entries = []
        console._parse_new_entry(duration, *arg_str)
        assert console.time_entries[0].duration == entry[2][0]
        assert console.time_entries[0].category == entry[2][1]
        assert console.time_entries[0].account == entry[2][2]
        assert console.time_entries[0].comment == entry[2][3]

    invalid_time_entries = [
        (1, [99, 'category out of bounds']),
        (2, [2, 'z', 'account out of bounds.']),
    ]
    for entry in invalid_time_entries:
        with pytest.raises(ValueError):
            console._parse_new_entry(entry[0], *entry[1])

def test_get_user_input(console, monkeypatch, capsys):
    invalid_commands = [
        "help, I'm a bug",
        ".25*923",
        "Y",
    ]
    other_valid_mmands =[
        ".25 4 q",
        "-53",
        ".5 g g",
        ".5 93",
        "42 3 i",
        ".5 g 3",
        "2 i",
        "43",
    ]
    valid_commands = {
        "C": ("C", None),
        "c": ("C", None),
        "2": ("A", (2, None, None, None)),
        "2   ": ("A", (2, None, None, None)),
        "2       ": ("A", (2, None, None, None)),
        "2     oh hi lol  ": ("A", (2, None, None, None)),
        "2 2": ("A", (2, 2, None, None)),
        "2  g": ("A", (2, None, "G", None)),
        '2 2  "great job team"': ("A", (2, 2, None, '"great job team"')),
        ".5 3 g daily stand-up": ("A", (0.5, 3, "G", "daily stand-up")),
        ".5 3 g": ("A", (0.5, 3, "G", None)),
        '.25 5 g "group meeting"': ("A", (0.25, 5, "G", '"group meeting"')),
    }
    for cmd in invalid_commands:
        monkeypatch.setattr('builtins.input', lambda _: cmd)
        console.get_user_input()
        captured = capsys.readouterr()
        assert 'Invalid input' in captured.out
