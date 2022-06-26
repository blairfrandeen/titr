import functools
from typing import Callable, List


####################
# PUBLIC FUNCTIONS #
####################
def ConsolePattern(
    function: Callable = None, pattern: Callable = None, name: str = None
) -> Callable:
    """Decorator for commands that match a pattern rather than having an explicit alias."""

    def _wrapper(function):
        return _ConsolePattern(function, pattern, name)

    return _wrapper


def ConsoleCommand(
    function: Callable = None,
    aliases: list[str] = None,
    name: str = None,
    hidden: bool = False,
) -> Callable:
    if function:
        return _ConsoleCommand(function)
    else:

        def _wrapper(function):
            return _ConsoleCommand(function, aliases, name, hidden)

        return _wrapper


def disable_command(command_name: str) -> None:
    """Disables a command. Disabled commands are hidden and cannot be called."""
    if command_name not in _COMMAND_LIST.keys():
        raise KeyError(f"Invalid Command Specified: '{command_name}'")
    cmd = _COMMAND_LIST[command_name]
    cmd.enabled = False
    cmd.hidden = True


def enable_command(command_name: str, hidden=False) -> None:
    """Enables a command."""
    if command_name not in _COMMAND_LIST.keys():
        raise KeyError(f"Invalid Command Specified: '{command_name}'")
    cmd = _COMMAND_LIST[command_name]
    cmd.enabled = True
    cmd.hidden = hidden


def get_input(
    session_args=None, prompt: str = ">>", break_commands: list[str] = ["quit"]
) -> ConsoleCommand:
    cmd_dict = _cmd_dict()
    while True:
        user_input = input(prompt)
        exec_cmd: Optional[Callable] = None
        args = []
        kwargs = dict()

        # Check to see if pattern match
        for pattern_cmd in _PATTERN_LIST:
            if pattern_cmd.match_pattern(user_input):
                exec_cmd = pattern_cmd
                args = [user_input]

        # If no pattern match, look for command match
        if exec_cmd is None:
            user_cmd, *args = user_input.split(" ")
            if user_cmd in cmd_dict.keys():
                exec_cmd: Callable = cmd_dict[user_cmd]
                # if command match, parse args and kwargs
                for arg in args:
                    if "=" in arg:
                        key, value = arg.split("=")
                        kwargs[key] = value
                        args.remove(arg)
            else:
                print("Command not recognized. Type 'h' for help or 'q' to quit.")

        # Try to execute the command
        if exec_cmd is not None:
            try:
                exec_cmd(session_args, *args, **kwargs)
            except (KeyError, ValueError, TypeError) as err:
                print("Error: ", err)
            else:
                if exec_cmd.name in break_commands:
                    return exec_cmd

    return exec_cmd


_PATTERN_LIST: list[ConsolePattern] = []
_COMMAND_LIST: dict = dict()
_COMMAND_HISTORY: list[str] = []
#####################
# PRIVATE FUNCTIONS #
#####################


class _ConsolePattern:
    def __init__(self, function: Callable, pattern: Callable, name: str = None):
        self.name = function.__doc__ if not name else name
        self.function: Callable = function
        self.match_pattern = pattern

        # TODO: Allow control of these parameters
        self.enabled = True
        self.hidden = False

        _PATTERN_LIST.append(self)

    def __call__(self, *args, **kwargs):
        argstr = " ".join([arg for arg in args[1:]])
        _COMMAND_HISTORY.append(self.name)
        return self.function(*args, **kwargs)


class _ConsoleCommand:
    def __init__(
        self,
        function: Callable,
        aliases: list[str] = None,
        name: str = None,
        hidden: bool = False,
    ):
        #  functools.update_wrapper(self, function)
        self.name: str = function.__name__ if not name else name
        self.function: Callable = function
        self.aliases: list[str] = [self.name]
        if aliases:
            for alias in aliases:
                self.aliases.append(alias)
        self.enabled: bool = True
        self.hidden = hidden

        _COMMAND_LIST[self.name] = self

    def __call__(self, *args, **kwargs):
        _COMMAND_HISTORY.append(self.name)
        if self.enabled:
            return self.function(*args, **kwargs)
        else:
            return None

    def __str__(self):
        cmd_str = ""
        for alias in self.aliases:
            cmd_str = cmd_str + alias + ", "
        cmd_str = cmd_str[:-2]  # remove the last comma and space
        cmd_str = cmd_str + "\t\t" + self.function.__doc__.split("\n")[0]
        return cmd_str


def _cmd_dict() -> dict:
    cmd_dict = dict()
    for cmd in _COMMAND_LIST.values():
        for alias in cmd.aliases:
            cmd_dict[alias] = cmd

    return cmd_dict


#####################
# BUILT-IN COMMANDS #
#####################


@ConsoleCommand(name="null_cmd", aliases=[""], hidden=True)
def _null_cmd(*args):
    """Default command if no input given"""
    pass


@ConsoleCommand(name="history", hidden=True)
def _disp_history(*args):
    """Display command history"""
    print("Command History:")
    for item in _COMMAND_HISTORY:
        print(item)


@ConsoleCommand(name="quit", aliases=["q"])
def _quit_function(*args):
    """Exit the console"""
    exit(0)


@ConsoleCommand(name="help", aliases=["h", "wtf"])
def _help_function(*args):
    """Display this help message"""
    cmd_dict = _cmd_dict()
    if len(args) > 1 and args[1] in cmd_dict.keys():
        print(cmd_dict[args[1]].function.__doc__)
    else:
        for key in sorted(_COMMAND_LIST.keys()):
            cmd = _COMMAND_LIST[key]
            if not cmd.hidden:
                print(cmd)
