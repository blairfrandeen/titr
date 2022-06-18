import datetime
import time
import sys

import pytest
from test_titr import console
import titr

if sys.platform.startswith("win32"):
    import pywintypes
    import win32com.client

OUTLOOK_ACCOUNT = "blairfrandeen@outlook.com"
TEST_CALENDAR_NAME = "TITR_TEST_CAL"
TEST_DAY = datetime.date(2022, 6, 3)
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
            # time.sleep(1)
            # MAPI_account.Folders.Remove(test_folder_index)


def datetime_to_pywintime(start_time):
    new_start = datetime.datetime.combine(TEST_DAY, start_time) + datetime.timedelta(
        hours=UTC_OFFSET_HR
    )
    new_start = pywintypes.Time(new_start)
    return new_start


@pytest.fixture
def make_appointment(calendar_folder):
    def _make_appointment(
        start: datetime.time,
        duration: int,  # minutes
        subject: str,
        category: str,
        busy_status: int,
    ) -> None:
        # Create a new calendar item
        # Argument makes it type AppointmentItem
        # Reference https://docs.microsoft.com/en-us/office/vba/api/outlook.olitemtype
        new_appointment = calendar_folder.Items.Add(1)
        new_appointment.Subject = subject
        new_appointment.ReminderSet = False  # turn off reminder
        new_appointment.Start = datetime_to_pywintime(start)
        new_appointment.Duration = duration
        new_appointment.Categories = category
        new_appointment.BusyStatus = busy_status
        if start == datetime.time(0) and duration == 1440:
            new_appointment.AllDayEvent = True
        else:
            new_appointment.AllDayEvent = False
        # Move to calendar
        new_appointment.Move(calendar_folder)
        return calendar_folder.Items(calendar_folder.Items.Count)

    return _make_appointment


@pytest.fixture
def test_appt_parameters():
    # Make a bunch of mock appointments
    params = [
        (datetime.time(0), 1440, "All-Day Event", "Meetings", 0),
        (datetime.time(8), 90, "Test Event #1", "Deep Work", 2),
        (datetime.time(10), 30, "Test Event #2", "Meetings", 2),
        (datetime.time(11), 30, "Tentative Event", "Meetings", 1),
        (datetime.time(11, 15), 90, "Free Event", "Meetings", 0),
        (datetime.time(12), 60, "Filtered Event", "Meetings", 2),
        (datetime.time(13), 120, "Out of Office", "Meetings", 3),
        (datetime.time(15), 120, "Working Elsewhere", "Meetings", 4),
    ]
    return params


# @pytest.mark.skip(reason='Working; connect to outlook time consuming')
@pytest.mark.skipif("win" not in sys.platform, reason="Skipping windows only tets.")
def test_get_outlook_items(make_appointment, monkeypatch, test_appt_parameters):
    test_appointments = []
    for appt in test_appt_parameters:
        test_appointments.append(make_appointment(*appt))

    # Set titr to look in new test folder
    monkeypatch.setattr("titr.OUTLOOK_ACCOUNT", OUTLOOK_ACCOUNT)
    monkeypatch.setattr("titr.CALENDAR_NAME", TEST_CALENDAR_NAME)

    outlook_items = titr.get_outlook_items(TEST_DAY)

    assert sum(1 for _ in outlook_items) == len(test_appt_parameters)
    for index, appt in enumerate(outlook_items):
        assert outlook_items[index].Duration == test_appt_parameters[index][1]
        assert outlook_items[index].Subject == test_appt_parameters[index][2]
        assert outlook_items[index].Categories == test_appt_parameters[index][3]
        assert outlook_items[index].BusyStatus == test_appt_parameters[index][4]

    # Test error handling for connecting to outlook
    # Test bad account
    monkeypatch.setattr("titr.OUTLOOK_ACCOUNT", "not an account")
    # with pytest.raises(pywintypes.com_error):
    #     console.get_outlook_items()
    # Test bad calendar
    monkeypatch.setattr("titr.CALENDAR_NAME", "not a calendar")
    monkeypatch.setattr("titr.OUTLOOK_ACCOUNT", OUTLOOK_ACCOUNT)
    # with pytest.raises(pywintypes.com_error):
    #     console.get_outlook_items()


class MockOutlookAppt:
    def __init__(self, start, duration, subject, categories, busy_status):
        self.Subject = subject
        self.Start = datetime_to_pywintime(start)
        self.Duration = duration
        self.BusyStatus = busy_status
        self.Categories = categories
        if start == datetime.time(0) and duration == 1440:
            self.AllDayEvent = True
        else:
            self.AllDayEvent = False


@pytest.fixture
def mock_appointments(test_appt_parameters):
    appointments = []
    for appt in test_appt_parameters:
        appointments.append(MockOutlookAppt(*appt))
    return appointments


def test_import_from_outlook(console, monkeypatch, mock_appointments, capsys):
    def _mock_get_outlook_items(_):
        return []

    def _mock_set_mode():
        print("Mode changed.")

    monkeypatch.setattr(titr, "get_outlook_items", _mock_get_outlook_items)
    monkeypatch.setattr(console, "_set_outlook_mode", _mock_set_mode)
    monkeypatch.setattr(console, "_set_normal_mode", _mock_set_mode)
    monkeypatch.setattr(titr, "SKIP_EVENT_NAMES", ["Filtered Event"])

    def _mock_user_input(**kwargs):
        print("User input mocked.")

    monkeypatch.setattr(console, "get_user_input", _mock_user_input)
    with pytest.raises(KeyError):
        console.import_from_outlook()

    monkeypatch.setattr(titr, "get_outlook_items", lambda _: mock_appointments)
    console.import_from_outlook()
    captured = capsys.readouterr()
    for entry in console.time_entries:
        for subject in [
            "Filtered Event",
            "Free Event",
            "Filtered Event",
            "All-Day Event",
            "Out of Office",
        ]:
            assert subject not in captured.out
        for subject in [
            "Test Event #1",
            "Test Event #1",
            "Tentative Event",
            "Working Elsewhere",
        ]:
            assert subject in captured.out


def test_set_outlook_mode(console):
    console._set_outlook_mode()
    cmd_list = console.command_list
    assert "outlook" not in cmd_list.keys()
    assert "date" not in cmd_list.keys()
    assert cmd_list["quit"][1] == console._set_normal_mode

    # def test_set_normal_mode(console):
    console._set_normal_mode()
    cmd_list = console.command_list
    assert "outlook" in cmd_list.keys()
    assert "date" in cmd_list.keys()
    assert cmd_list["quit"][1] == exit
    assert cmd_list["null_cmd"][1] is None
