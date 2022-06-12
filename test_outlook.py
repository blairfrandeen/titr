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
    remove_calendar(TEST_CALENDAR_NAME, MAPI_account)
    try:
        test_folder = MAPI_account.Folders.Add(TEST_CALENDAR_NAME, 9)
    except pywintypes.com_error:
        raise Exception("Test folder already exists, please delete and try again.")
    yield test_folder

    # Clean up
    # remove_calendar(TEST_CALENDAR_NAME, MAPI_account)

def remove_calendar(calendar_name, MAPI_account):
    # Find the index of the folder to remove
    test_folder_index = 0
    for index in range(MAPI_account.Folders.Count):
        if MAPI_account.Folders.Item(index + 1).Name == calendar_name:
            test_folder_index = index + 1
            break

#    ready = input('enter to remove cal and continue')
    if test_folder_index > 0:
        try:
            MAPI_account.Folders.Remove(test_folder_index)
        except pywintypes.com_error:
            pass
            #time.sleep(1)
            #MAPI_account.Folders.Remove(test_folder_index)

@pytest.fixture
def make_appointment(calendar_folder):
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
        new_appointment.Move(calendar_folder)
        return calendar_folder.Items(calendar_folder.Items.Count)

    return _make_appointment

@pytest.mark.skip(reason='Working; connect to outlook time consuming')
def test_get_outlook_items(console, calendar_folder, make_appointment, monkeypatch):
    # Make a bunch of mock appointments
    test_appt_parameters = [
        (datetime.time(8), 90, "Test Event #1", "Deep Work"),
        (datetime.time(10), 30, "Test Event #2", "Meetings"),
        (datetime.time(11), 30, "Tentative Event", "Meetings"),
        (datetime.time(11), 90, "Free Event", "Meetings"),
        (datetime.time(12), 60, "Filtered Event", "Meetings"),
        (datetime.time(0), 1440, "All-Day Event", "Meetings"),
        (datetime.time(13), 120, "Out of Office", "Meetings"),
        (datetime.time(15), 120, "Working Elsewhere", "Meetings"),
    ]
    test_appointments = []
    for appt in test_appt_parameters:
        test_appointments.append(make_appointment(*appt))

    # Modifiy some additional parameters
    test_appointments[2].BusyStatus = 1      # tentative
    test_appointments[3].BusyStatus = 0      # free
    test_appointments[5].AllDayEvent = True  # all day
    test_appointments[6].BusyStatus = 3      # out of office
    test_appointments[7].BusyStatus = 4      # working elsewhere
    for appt in test_appointments:
        appt.Save()

    # Set titr to look in new test folder
    monkeypatch.setattr("titr.OUTLOOK_ACCOUNT", OUTLOOK_ACCOUNT)
    monkeypatch.setattr("titr.CALENDAR_NAME", TEST_CALENDAR_NAME)
    console.date = TEST_DAY

    outlook_items = console.get_outlook_items()

    assert len(outlook_items) == len(test_appt_parameters)
    for index, appt in enumerate(outlook_items):
        assert outlook_items[index].Duration == test_appt_parameters[index][1]
        assert outlook_items[index].Subject == test_appt_parameters[index][2]
        assert outlook_items[index].Categories == test_appt_parameters[index][3]


def test_import_from_outlook(console, monkeypatch):
    def _mock_get_outlook_items():
        return []
    monkeypatch.setattr(console, 'get_outlook_items', _mock_get_outlook_items)
    with pytest.raises(KeyError):
        console.import_from_outlook()


def test_set_outlook_mode(console):
    console._set_outlook_mode()
    cmd_list = console.command_list
    assert 'outlook' not in cmd_list.keys()
    assert 'date' not in cmd_list.keys()
    assert cmd_list['quit'][1] == console._set_normal_mode

# def test_set_normal_mode(console):
    console._set_normal_mode()
    cmd_list = console.command_list
    assert 'outlook' in cmd_list.keys()
    assert 'date' in cmd_list.keys()
    assert cmd_list['quit'][1] == exit
    assert cmd_list['null_cmd'][1] is None
