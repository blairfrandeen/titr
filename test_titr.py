import pytest
import titr

def test_parse():
    invalid_args = [
        None,
        0,
        1.2,
        [1, 2, 3],
        {1: 'one'},
    ]
    invalid_commands = [
        "help, I'm a bug",
        '-53',
        '.25*923',
        'Y',
        '.25 4 q',
        '.5 g g',
        '.5 93',
        '42 3 i',
    ]
    valid_commands = [
        'C',
        'c',
        '2',
        '43',
        '2 2',
        '2 i',
        '.5 3 g',
        '.5 g 3',
        '.25 5 "daily stand-up"',
        '.25 5 g "group meeting"',
        '.25"group meeting"5 g ',
        '.25"group meeting" g 5 ',
        ".25 5 'daily stand-up'",
    ]
    for arg in invalid_args:
        with pytest.raises(TypeError):
            titr.parse_command(arg)

    for cmd in invalid_commands:
        with pytest.raises(ValueError):
            titr.parse_command(cmd)


    titr.parse_command(valid_commands[0])
    assert 0
