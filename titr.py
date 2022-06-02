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
    "T": "Display Categories",
    "Q": "Quit",
    "H": "Help",
}

ACCOUNTS = {
    "O": "OS",
    "G": "Group Lead",
    "I": "Incidental",
}

def parse_command(user_command: str) -> None:
    """
    Parse user commands. Return the command and
    a tuple of arguments. Commands & arguments
    are separated by a semicolon. The logic:
    - If the first split is a char, look for that command
    - If the first split is not a char, apply a default command
    - Remaining splits in the following order:
    - Hours Worked, Work Type, Work Account, Comment
    - If no entry for type, account or comment, apply defaults.
    """
    if not isinstance(user_command, str):
        raise TypeError

    args = user_command.split(';')

    command, hours, category, account, comment = None, None, None, None, None
    if args[0].isalpha():
        if len(args[0]) > 1:
            raise ValueError("Command should be single letter.")
        elif args[0].upper() in COMMANDS.keys():
            command = args[0].upper()
            return command, None
        else:
            raise ValueError("Command not found.")
    else:
        command = 'A'
        hours = float(args[0])
        if hours < 0:
            raise ValueError("Hours must be positive")
        elif hours > MAX_HOURS:
            raise ValueError("You're working too much.")

        if len(args) > 1 and args[1] != '':
            category = int(args[1])
            if category not in CATEGORIES.keys():
                raise ValueError("Unknown category")

        if len(args) > 2 and args[2] != '':
            account = args[2].upper()
            if account not in ACCOUNTS.keys():
                raise ValueError("Unknown account")

        if len(args) > 3 and args[3] != '':
            comment = args[3]

    arguments = (hours, category, account, comment)
    return command, arguments

def main() -> None:
    print("Welcome to titr.")
    user_command: str = ''
    while user_command != 'q':
        user_command = input('> ')
        try:
            parse_command(user_command)
        except ValueError as e:
            print("Invalid command: ", e)


if __name__ == "__main__":
    main()
