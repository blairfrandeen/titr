#!/usr/bin/python

"""
titr - pronounced 'titter'

A time tracker CLI.
"""
import re

MAX_HOURS = 9       # maximum hours that can be entered for any task
CATEGORIES = {
    2: "Deep Work",
    3: "Discussions",
    4: "Configuration",
    5: "Meetings",
    6: "Shallow / Misc",
    7: "Career Development",
    8: "Email",
}

COMMANDS = {
    "A": "Add Entry",     # default command
    "C": "Copy",
    "P": "Preview",
    "Z": "Undo Last Input",
    "D": "Start Over",
    "W": "Display WAMS",
    "A": "Display Categories",
    "Q": "Quit",
    "H": "Help",
}

def parse_command(user_command: str) -> None:
    if not isinstance(user_command, str):
        raise TypeError

    re_comment = r"((?<=\").+(?=\"))|((?<=\').+(?=\'))"
    re_num = r"((?<!\")\d*\.?\d*(?!\"))"
    re_char = r"((?<!\")\w?(?!\"))"
    args = []
    if re.search(parse_regex, user_command):
        print(f"{re.search(parse_regex, user_command).groups() = }")
        for match in re.search(parse_regex, user_command).groups():
            print(f"{match = }")
            #  for arg in match:
                #  print(f"{arg = }")
            if match is not None and match != '':
                args.append(arg)
    else:
        return None, None

    command = None
    arguments = None
    # Arguments: (Hours, Category, Charge Number, Date)
    #  arguments = (None, None, None, None)
    print(f"{args[0] = }")
    if args[0].isalpha():
        print(f"{args[0] = }")
        if len(args[0]) > 1:
            raise ValueError # commands are only single letter
        elif args[0].upper() in COMMANDS.keys():
            command = args[0]
            arguments = args[1:]
        else:
            raise ValueError # command not found
    else:
        command = 'A'
        args[0] = float(args[0])
        if args[0] < 0 or args[0] > MAX_HOURS:
            raise ValueError # hours must be positive, and not excessive

    return command, arguments

def main() -> None:
    print("Welcome to titr.")
    user_command: str = ''
    while user_command != 'q':
        user_command = input('> ')
        parse_command(user_command)


if __name__ == "__main__":
    main()
