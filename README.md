# titr
titr (pronounced 'titter') is a **ti**me **tr**acker app I've built for myself, which allows me to efficiently log my working hours, as well as automatically log calendar events from Outlook.

For over two years I've been in the daily habit of recording a detailed log of my work modes, which as allowed me to collect metrics for how my time is divided between deep work, email, shallow work, meetings, etc. These metrics are insightful, and also practically useful as I am required to report on a weekly basis how my time was split between different tasks, e.g. 75% task A, 25% task B. 

Entering the data in Excel at the end of the workday is tedious, especially given that each entry requires me to fill out the date, task, and work mode. Even with shortcuts (ctrl + ;) and auto-complete, it still takes about 2.5 minutes to remember what I did and manually enter the data, generally about 8 entries per day.

The goal of titr is to reduce the cost of acquiring daily time-tracking data by using a keyboard-only command-line interface. A secondary benefit is to encourage the use of [time block planning](https://www.calnewport.com/blog/2013/12/21/deep-habits-the-importance-of-planning-every-minute-of-your-work-day/), which I have been doing using Outlook.

## Installation & Setup
```
pip install titr
```

### Requirements
- Python 3.10
- `pip install pyperclip` to enable copying data to clipboard
- `pip install pywin32` to enable integration with Outlook

### Configuration
Configuration is stored in `default.ini`, which will be created in your working directory the first time you run `titr` at the command line. You will be asked to enter your email if you want to connect titr to Outlook. Your email address is stored locally and is not transmitted anywhere.

## Usage
Type `help` at the command line to get a list of commands. titr has been designed to minimize the number of keystrokes required to input data. The pattern for new entries is `duration <category> <account> <comment>`.
- Duration of a time entry must be a float, and is always requried.
- Category must be an integer, and must be one of your pre-set categories.
- Accounts must be a single character (non case-sensitive)
- Anything not registered as a category or account will be interpreted as a comment.

Some example time entries:
- `1` = One hour on the default account and default category
- `.5 2 i` = Half an hour on category 2 (deep work) and account i (incidental)
- `.5 t write a readme` = half an hour on default category on account t (titr) with comment "write a readme"

Change the date for all subsequent entries using the `d` or `date` command:
- `d -1` = set the date to yesterday
- `d 2022-05-06` = set the date to May 6th, 2022
- `date` = set the date to today

Type `p` or `preview` to see the that will be entered in the database. Type `s <duration>` to scale the time entries to add up to however long you were supposed to be working.

Once ready to copy data to Excel, type `clip`, and then paste into your workbook.

## Extracting data from Outlook
Type `o` or `outlook` at the command line to have titr look for Outlook calendar events for whatever date you've set. If the duration, category, and subject of the calendar event are to your liking, simply press `<enter>` to add to your time log. Otherwise enter data like you normally would at the prompt, and any user-inputs will override what's in Outlook. For example, if your meeting was scheduled for 1 hour but went on for 1.5, simply type `1.5` at the prompt and everything else will populate. If you skipped your meeting (good job), enter `0` to skip the entry.

It's recommended to set hotkeys to categorize your Outlook events based on your work-modes, and have these match the categories dictionary in titr. For example `<ctrl>+<F2>` sets the category to "Deep Work" in Outlook, which should be category `2` in titr.

See some of the options in `default.ini` if you want all day events or events with a status of out of office to be included.

