import win32com.client
import datetime
import time
import pywintypes

OUTLOOK_ACCOUNT = 'blairfrandeen@outlook.com'
TEST_CALENDAR_NAME = 'TITR_TEST_CAL'
TEST_DAY = datetime.date(2022,6,3)
dst = time.daylight and time.localtime().tm_isdst
UTC_OFFSET_HR = -(time.altzone if dst else time.timezone) / 3600

outlook = win32com.client.Dispatch("Outlook.Application")
namespace = outlook.GetNamespace("MAPI")
account = namespace.Folders.Item(OUTLOOK_ACCOUNT)

# Create a new folder for test items
# second argument is olFolderCalendar type
# Reference https://docs.microsoft.com/en-us/office/vba/api/outlook.oldefaultfolders
test_folder = account.Folders.Add(TEST_CALENDAR_NAME, 9)

# Create a new calendar item
# Argument makes it type AppointmentItem
# Reference https://docs.microsoft.com/en-us/office/vba/api/outlook.olitemtype
new_appointment = test_folder.Items.Add(1)
new_appointment.Subject = 'Test appointment.'
new_appointment.ReminderSet = False      # turn off reminder
new_start = datetime.datetime(2022,6,5,12,0) + datetime.timedelta(hours=UTC_OFFSET_HR)
new_start = pywintypes.Time(new_start)
new_appointment.Start = new_start
new_appointment.Duration = 90
new_appointment.Categories = 'Deep Work'
# Move to calendar
new_appointment = new_appointment.Move(test_folder)

# Clean up
# Find the index of the folder to remove
test_folder_index = 0
for index in range(account.Folders.Count):
    if account.Folders.Item(index + 1).Name == TEST_CALENDAR_NAME:
        test_folder_index = index + 1
        break

ready = input('enter to remove cal and continue')
account.Folders.Remove(test_folder_index)
