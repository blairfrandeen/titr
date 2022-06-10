import datetime
import time

import pytest
import pywintypes
from test_titr import console
import titr
import win32com.client

OUTLOOK_ACCOUNT = 'blairfrandeen@outlook.com'
TEST_CALENDAR_NAME = 'TITR_TEST_CAL'
TEST_DAY = datetime.date(2022,6,3)
dst = time.daylight and time.localtime().tm_isdst
UTC_OFFSET_HR = -(time.altzone if dst else time.timezone) / 3600


@pytest.fixture
def MAPI_account():
    outlook = win32com.client.Dispatch("Outlook.Application")
    namespace = outlook.GetNamespace("MAPI")
    account = namespace.Folders.Item(OUTLOOK_ACCOUNT)
    yield account

@pytest.fixture
def calendar_folder(MAPI_account):
    # Create a new folder for test items
    # second argument is olFolderCalendar type
    # Reference https://docs.microsoft.com/en-us/office/vba/api/outlook.oldefaultfolders
    test_folder = MAPI_account.Folders.Add(TEST_CALENDAR_NAME, 9)
    yield test_folder

    # Clean up
    # Find the index of the folder to remove
    test_folder_index = 0
    for index in range(MAPI_account.Folders.Count):
        if MAPI_account.Folders.Item(index + 1).Name == TEST_CALENDAR_NAME:
            test_folder_index = index + 1
            break

    ready = input('enter to remove cal and continue')
    try:
        MAPI_account.Folders.Remove(test_folder_index)
    except pywintypes.com_error:
        time.sleep(3)
        MAPI_account.Folders.Remove(test_folder_index)

def make_appointment(calendar_folder):
#    @pytest.mark.usefixtures("calendar_folder")
    def _make_appointment(
        start: datetime.time,
        duration: int, # minutes
        subject: str,
        category: str,
    ) -> None:
        # Create a new calendar item
        # Argument makes it type AppointmentItem
        # Reference https://docs.microsoft.com/en-us/office/vba/api/outlook.olitemtype
        new_appointment = calendar_folder.Items.Add(1)
        new_appointment.Subject = subject
        new_appointment.ReminderSet = False      # turn off reminder
        new_start = (
                datetime.datetime.combine(TEST_DAY, start)
                + datetime.timedelta(hours=UTC_OFFSET_HR)
            )
        new_start = pywintypes.Time(new_start)
        new_appointment.Start = new_start
        new_appointment.Duration = duration
        new_appointment.Categories = category
        # Move to calendar
        new_appointment = new_appointment.Move(calendar_folder)
        return new_appointment

    return _make_appointment

def test_get_outlook_items(console, calendar_folder):
    a0 = make_appointment(calendar_folder)
    a0(datetime.time(8), 90, "test", "Deep Work")
    a0(datetime.time(10), 30, "test", "Meetings")
    # a1 = make_appointment(datetime.time(8), 90, "test", "Deep Testing")
    outlook_items = console.get_outlook_items()
    assert len(outlook_items) == 1
