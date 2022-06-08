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
    te = titr.TimeEntry(2, category=6, comment='test entry')
    yield te

class MockTimeEntry:
    def __init__(self, duration, account = 'N', category = 5, comment = '', date = datetime.date.today()):
        self.duration = duration
        self.category = category
        self.account = account
        self.comment = comment
        self.date = date

    def __str__(self):
        self_str: str = f"{self.duration}\t{self.category}\t{self.account}\t{self.comment}"
        return self_str

float_tests = [
    ('yankee', False),
    ('dOODlE', False),
    ('KLJF#*(@#!!', False),
    ('.34', True),
    ('.23191', True),
    ('0', True),
    ('-0', True),
    ('99', True),
    ('4e5', True),
    ('inf', True),
    (5, True),
    (4.1, True),
    (-4.23e-5, True),
    (False, True),
    ('NaN', True),
]

@pytest.mark.parametrize("item, expected", float_tests)
def test_is_float(item, expected):
    assert titr.is_float(item) is expected

def test_float_bad_inputs():
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
        (7, '2 i TEST STRING'.split(' '), (7, 2, 'i', 'TEST STRING')),
        (.8731, 'i test string'.split(' '), (.8731, default_cat, 'i', 'test string')),
        (0.25, '2 a damn good feeling is a damn good time, wait, "who wrote my rhyme"?'.split(' '),
            (0.25, 2, default_acct, 'a damn good feeling is a damn good time, wait, "who wrote my rhyme"?')
        ),
        (1, 'test string'.split(' '), (1, default_cat, default_acct, 'test string')),
    ]

    for entry in valid_time_entries:
        duration, arg_str = entry[0], entry[1]
        console._parse_new_entry(duration, *arg_str)
        assert console.time_entries[0].duration == entry[2][0]
        assert console.time_entries[0].category == entry[2][1]
        assert console.time_entries[0].account == entry[2][2]
        assert console.time_entries[0].comment == entry[2][3]
        console.time_entries = []

    invalid_time_entries = [
        (1, [99, 'category out of bounds']),
        (2, [2, 'z', 'account out of bounds.']),
    ]
    for entry in invalid_time_entries:
        with pytest.raises(ValueError):
            console._parse_new_entry(entry[0], *entry[1])

def test_help_msg(console, monkeypatch, capsys):
    def _add_entry(): # pragma: no cover
        """add"""
        return None
    def _clear(): # pragma: no cover
        """clear"""
        return None
    _command_list: Dict[str, Tuple[List[str], Callable]] = {
        'add':      (['add'],           _add_entry),
        'clear':    (["clear"],         _clear),
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

    console.set_date(datetime.date.fromisoformat('2022-06-17'))
    assert console.date == datetime.date(2022,6,17)

    with pytest.raises(TypeError):
        console.set_date('1941-12-07')

invalid_commands = [
    "help, I'm a bug",
    ".25*923",
    "Y",
    "45e12",
    "-2 4 g 'negative work'",
]

@pytest.mark.parametrize("cmd", invalid_commands)
def test_get_user_input_invalid(cmd, monkeypatch, console):
    monkeypatch.setattr('builtins.input', lambda _: cmd)
    with pytest.raises(ValueError):
        console.get_user_input()


def test_get_user_input(console, monkeypatch, capsys):
    valid_commands = {
            'clear':    ["clear"],
            'copy_output':     ["clip"],
            #  'commit':   ['c', 'commit'],
            'set_date':     ['d', 'date', 'D', 'd -1', 'date 2013-08-05'],
            'get_outlook_items':  ["O", "outlook"],
            'preview_output':  ["p", "preview"],
            'list_categories_and_accounts':  ["ls", "list"],
            'undo_last':     ["z", "undo"],
            'scale_time_entries':    ["s 9", "scale 10"],
            'help_msg':     ["h", "help", "help scale", "help date", "add"],
            '_parse_new_entry': ['.5 1 i j', '1 2 g test'],
            #  'exit':     ["q", "quit"],
    }
    for cmd, aliases in valid_commands.items():
        def _mock_alias_function(*args, **kwargs):
            print(f"mock alias function: {cmd}")
        monkeypatch.setattr(console, cmd, _mock_alias_function)
        for alias in aliases:
            monkeypatch.setattr('builtins.input', lambda _: alias)
            console.get_user_input()
            captured = capsys.readouterr()
            assert f'mock alias function: {cmd}' in captured.out

    monkeypatch.setattr('builtins.input', lambda _: 'help me!')
    with pytest.raises(ValueError):
        console.get_user_input()


today = datetime.date.today()
valid_dates = [
    ('1984-06-17', datetime.date(1984, 6, 17)),
    ('-1', today + datetime.timedelta(days=-1)),
    ('-7', today + datetime.timedelta(days=-7)),
    ('0', today),
    ('12', None),
    ('not a date', None),
    ('6/17/84', None),
    ('2121-04-23', None),
]
@pytest.mark.parametrize("test_input, expected", valid_dates)
def test_parse_date(test_input, expected):
    if expected is not None:
        assert titr.parse_date(test_input) == expected
    else:
        with pytest.raises(ValueError):
            titr.parse_date(test_input)


