import win32com.client as w32
import datetime

# User defaults to connect to proper calendar
OUTLOOK_ACCOUNT = 'blairfrandeen@outlook.com'
OUTLOOK_CAL_NAME = 'Calendar'
BUSY_STATUS = {
        0: 'Free',
        1: 'Tentative',
        2: 'Busy',
        3: 'Out of Office',
        4: 'Working Elsewhere',
        }

# Time format string requried by MAPI to filter by date
MAPI_TIME_FORMAT = "%m-%d-%Y %I:%M %p"

# Connect to Outlook MAPI (Mail API)
outlook = w32.Dispatch("Outlook.Application").GetNamespace("MAPI")

# Connect to calendar
calendar = outlook.Folders.Item(OUTLOOK_ACCOUNT).Folders[OUTLOOK_CAL_NAME]

# Filter for events in a single day
target_date = '2022-06-02'
target_date = datetime.datetime.fromisoformat(target_date)
num_days = 1
search_end = target_date + datetime.timedelta(days=num_days)
res_str = ''.join([
        "[Start] >= '",
        target_date.strftime(MAPI_TIME_FORMAT),
        "' AND [End] <= '",
        search_end.strftime(MAPI_TIME_FORMAT),
        "'",
        ])

cal_filtered = calendar.Items.Restrict(res_str)
cal_filtered.Sort("[Start]", False)
for item in cal_filtered:

    print(
        item.Subject,       # meeting title
        item.Start.strftime("%X"),         # start time, datetime
        item.Duration,      # minutes
        item.Categories,    # comma separated list
        BUSY_STATUS[item.BusyStatus],
    )
#    for rec in range(item.Recipients.Count):
#        print(item.Recipients.Item(rec + 1).Name)

"""      
        item.End.strftime("%Y-%m-%d"),           # end time, datetime
        item.AllDayEvent,   # boolean
        item.Location,
        item.RequiredAttendees,
        item.OptionalAttendees,
        item.Organizer,
    )
"""

