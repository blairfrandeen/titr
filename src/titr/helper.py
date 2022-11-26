from colorama import Style, Fore


def disp_dict(dictionary: dict, dict_name: str):  # pragma: no cover
    """Display items in a dict"""
    print(f"{Style.BRIGHT}{dict_name}{Style.NORMAL}: ")
    for key, value in dictionary.items():
        print(f"{Fore.BLUE}{key}{Fore.RESET}: {value}")


def is_float(item: str) -> bool:
    """Determine if a string represents a float."""
    if not isinstance(item, (str, int, float)):
        raise TypeError
    try:
        float(item)
        return True
    except ValueError:
        return False
