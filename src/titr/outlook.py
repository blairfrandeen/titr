import datetime
import pywintypes
import win32com.client


def get_outlook_items(search_date: datetime.date, calendar_name: str, outlook_account: str):
    """Read calendar items from Outlook."""

    # connect to outlook
    # TODO: Move to separate function
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")
    except pywintypes.com_error as err:
        print(f"Error connecting to Outlook Namespace: {err}")
        return None
    try:
        acct = namespace.Folders.Item(outlook_account)
    except pywintypes.com_error as err:
        print(f'Error connecting to account "{outlook_account}": {err}')
        return None
    try:
        calendar = acct.Folders(calendar_name)
    except pywintypes.com_error as err:
        print(f'Calendar with name "{calendar_name}" not found: {err}')
        return None

    # Time format string requried by MAPI to filter by date
    MAPI_TIME_FORMAT: str = "%m-%d-%Y %I:%M %p"
    cal_items = calendar.Items
    cal_items.Sort("Start", False)
    cal_items.IncludeRecurrences = True
    search_end: datetime.date = search_date + datetime.timedelta(days=1)
    search_str: str = "".join(
        [
            "[Start] >= '",
            search_date.strftime(MAPI_TIME_FORMAT),
            "' AND [End] <= '",
            search_end.strftime(MAPI_TIME_FORMAT),
            "'",
        ]
    )

    cal_filtered = cal_items.Restrict(search_str)

    return cal_filtered
