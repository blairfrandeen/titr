#!/usr/bin/python

"""
titr - pronounced 'titter'

A time tracker CLI.
"""
import re

MAX_HOURS = 9       # maximum hours that can be entered for any task

def parse_command(user_command: str) -> None:
    if not isinstance(user_command, str):
        raise TypeError

    parse_regex = r"((?<=\").+(?=\"))|((?<=\').+(?=\'))|(\d*\.?\d*)(\w)"
    args = []
    for match in re.findall(parse_regex, user_command):
        for arg in match:
            if arg is not None:
                args.append(arg)

    args = user_command.split(' ')
    if args[0].isalpha():
        if len(args[0]) > 1:
            raise ValueError # commands are only single letter
        else:
            raise NotImplementedError

    args[0] = float(args[0])
    if args[0] < 0 or args[0] > MAX_HOURS:
        raise ValueError # hours must be positive, and not excessive

def main() -> None:
    print("Welcome to titr.")
    user_command: str = ''
    while user_command != 'q':
        user_command = input('> ')
        parse_command(user_command)


if __name__ == "__main__":
    main()
