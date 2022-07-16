import textwrap
from typing import Callable, Optional


####################
# PUBLIC FUNCTIONS #
####################
def ConsolePattern(
    function: Optional[Callable] = None,
    pattern: Optional[Callable] = None,
    name: Optional[str] = None,
) -> Callable:
    """Decorator for commands that match a pattern rather
    than having an explicit alias."""

    if function:
        return _ConsolePattern(function, pattern)
    else:

        def _wrapper(function):
            return _ConsolePattern(function, pattern, name)

        return _wrapper


def ConsoleCommand(
    function: Callable = None,
    aliases: list[str] = None,
    name: str = None,
    hidden: bool = False,
    enabled: bool = True,
) -> Callable:
    if function:
        return _ConsoleCommand(function)
    else:

        def _wrapper(function):
            return _ConsoleCommand(function, aliases, name, hidden, enabled)

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


def set_pattern(pattern_name: str, new_pattern: Callable) -> Callable:
    """Modify an existing pattern."""
    if pattern_name not in _PATTERN_LIST.keys():
        raise KeyError(f"Invalid Pattern Specified: '{pattern_name}'")
    pat = _PATTERN_LIST[pattern_name]
    old_pattern = pat.match_pattern
    pat.match_pattern = new_pattern
    return old_pattern


def patch_command(target: str, source: str):
    print(f"{_COMMAND_LIST=}")
    if target not in _COMMAND_LIST.keys():
        raise KeyError(f"Invalid Command Specified: '{target}'")
    if source not in _COMMAND_LIST.keys():
        raise KeyError(f"Invalid Command Specified: '{source}'")
    _COMMAND_LIST[target].function = _COMMAND_LIST[source].function


def get_input(
    session_args=None, prompt: str = ">>", break_commands: list[str] = ["quit"]
) -> Callable:
    cmd_dict = _cmd_dict()
    while True:
        user_input = input(prompt)
        exec_cmd: Optional[Callable] = None
        args = []
        kwargs = dict()

        # Check to see if pattern match
        for pattern_cmd in _PATTERN_LIST.values():
            if pattern_cmd.match_pattern(user_input):
                exec_cmd = pattern_cmd
                args = [user_input]

        # If no pattern match, look for command match
        if exec_cmd is None:
            user_cmd, *args = user_input.split(" ")
            if user_cmd in cmd_dict.keys():
                exec_cmd = cmd_dict[user_cmd]
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


_PATTERN_LIST: dict = dict()
_COMMAND_LIST: dict = dict()
_COMMAND_HISTORY: list[str] = []
#####################
# PRIVATE FUNCTIONS #
#####################


class _ConsolePattern:
    def __init__(
        self, function: Callable, pattern: Callable, name: Optional[str] = None
    ):
        # TODO: error handling if no name argument and no function.__doc__
        self.name: str = function.__name__ if not name else name
        self.function: Callable = function
        self.match_pattern = pattern

        # TODO: Allow control of these parameters
        self.enabled = True
        self.hidden = False

        _PATTERN_LIST[self.name] = self

    def __call__(self, *args, **kwargs):
        # argstr = " ".join([arg for arg in args[1:]])
        _COMMAND_HISTORY.append(self.name)
        return self.function(*args, **kwargs)


class _ConsoleCommand:
    def __init__(
        self,
        function: Callable,
        aliases: list[str] = None,
        name: str = None,
        hidden: bool = False,
        enabled: bool = True,
    ):
        #  functools.update_wrapper(self, function)
        self.name: str = function.__name__ if not name else name
        self.function: Callable = function
        self.aliases: list[str] = [self.name]
        if aliases:
            for alias in aliases:
                self.aliases.append(alias)
        self.enabled: bool = enabled
        self.hidden = hidden if self.enabled else True

        _COMMAND_LIST[self.name] = self

    def __call__(self, *args, **kwargs):
        _COMMAND_HISTORY.append(self.name)
        if self.enabled:
            return self.function(*args, **kwargs)
        else:
            print("Disabled.")
            return None

    def __str__(self):
        pre_indent: int = 2
        width_command: int = 20
        width_description: int = 60
        cmd_str = ""
        for alias in self.aliases:
            cmd_str = cmd_str + alias + ", "
        cmd_str = cmd_str[:-2]  # remove the last comma and space
        doc_str: list[str] = textwrap.wrap(
            self.function.__doc__.strip().split("\n")[0],
            width=width_description,
            initial_indent="",
            subsequent_indent=" " * width_command,
        )
        #  if doc_str.startswith("\n"):
        #  doc_str = doc_str[1:]
        #  cmd_str = cmd_str + "\t\t" + doc_str.split("\n")[0]
        cmd_str: str = "{cs:{w1}}{ds:{w2}}".format(
            cs=cmd_str, ds=doc_str[0], w1=width_command, w2=width_description
        )
        for line in doc_str[1:]:
            cmd_str += "\n" + line
        return textwrap.indent(cmd_str, " " * pre_indent)


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
    """Display this help message. Type help <command> for more detail."""
    cmd_dict = _cmd_dict()
    if len(args) > 1 and args[1] in cmd_dict.keys():
        docstr = cmd_dict[args[1]].function.__doc__
        if docstr.startswith("\n"):
            docstr = docstr[1:]  # Trim newline if it exists
        print(textwrap.dedent(docstr))
    else:
        print("Available commands:")
        for key in sorted(_COMMAND_LIST.keys()):
            cmd = _COMMAND_LIST[key]
            if not cmd.hidden:
                #  print("  ", end="")
                print(cmd)
