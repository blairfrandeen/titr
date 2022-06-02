import pytest
import titr

def test_fill_hours():
    assert titr.fill_hours([2, 2], 5) == [2.5, 2.5]
    assert titr.fill_hours([2, 2], 4) == [2, 2]
    assert titr.fill_hours([2, ], 5) == [5]
    assert titr.fill_hours([3, 4], 6) == [3 - 3/7, 4-4/7]
    assert titr.fill_hours([1,2,3], 7) == [7/6, 14/6, 3.5]

def test_parse():
    invalid_args = [
        None,
        0,
        1.2,
        [1, 2, 3],
        {1: "one"},
    ]
    invalid_commands = [
        "help, I'm a bug",
        "-53",
        ".25*923",
        "Y",
        ".25;4 q",
        ".5 g;g",
        ".5;93",
        "42;3;i",
        ".5;g;3",
        "2;i",
        "43",
    ]
    valid_commands = {
        "C": ("C", None),
        "c": ("C", None),
        "2": ("A", (2, None, None, None)),
        "2;;;": ("A", (2, None, None, None)),
        "2;;;;;;;": ("A", (2, None, None, None)),
        "2;;;;;oh hi lol;;": ("A", (2, None, None, None)),
        "2;2": ("A", (2, 2, None, None)),
        "2;;g": ("A", (2, None, "G", None)),
        '2;2;;"great job team"': ("A", (2, 2, None, '"great job team"')),
        ".5;3;g;daily stand-up": ("A", (0.5, 3, "G", "daily stand-up")),
        ".5;3;g": ("A", (0.5, 3, "G", None)),
        '.25;5;g;"group meeting"': ("A", (0.25, 5, "G", '"group meeting"')),
    }
    for arg in invalid_args:
        with pytest.raises(TypeError):
            titr.parse_command(arg)

    for cmd in invalid_commands:
        with pytest.raises(ValueError):
            titr.parse_command(cmd)

    with pytest.raises(ValueError) as excinfo:
        titr.parse_command("-9;3;o")
    assert "Hours must be positive" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        titr.parse_command("99;2;g")
    assert "You're working too much." in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        titr.parse_command("1;39;o")
    assert "Unknown category" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        titr.parse_command("1;2;z")
    assert "Unknown account" in str(excinfo.value)

    for cmd, exp_result in valid_commands.items():
        assert titr.parse_command(cmd) == exp_result
