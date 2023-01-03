# Changelog

<!--next-version-placeholder-->

## v0.10.0 (2023-01-03)
### Feature
* Add 'config' command ([`5c89f39`](https://github.com/blairfrandeen/titr/commit/5c89f39919a94b0b9ff32f739f562649c6fd5dcb))

### Fix
* Minor import changes for compatibility on Linux. ([`d58ed56`](https://github.com/blairfrandeen/titr/commit/d58ed5663e423b980f71f6acd849ecd446d2859b))
* Display correct database file on commit. ([`9d9f77c`](https://github.com/blairfrandeen/titr/commit/9d9f77c06d7107ee740f8efca93d4f1b6080244f))
* Time entries committed when editing config ([`206f5f5`](https://github.com/blairfrandeen/titr/commit/206f5f5d1c2e75813d75f9336a99061a9326ff34))

## v0.9.0 (2022-08-31)
### Feature
* Show daily log of tasks ([`c7b0381`](https://github.com/blairfrandeen/titr/commit/c7b0381a2934d2f3bea6bb424517de4ad926178b))

## v0.8.0 (2022-08-23)
### Feature
* View work modes for the week ([`0db451b`](https://github.com/blairfrandeen/titr/commit/0db451b40895f2f8c85d07ef6c854b1a2b68759f))

## v0.7.3 (2022-08-15)
### Fix
* Fix issue with outlook function not skipping items when 0 time was entered. ([`e1a117c`](https://github.com/blairfrandeen/titr/commit/e1a117cf3711103de00c17add4712d9c14a47f0a))
* Outlook mode no longer starts automatically ([`b8ac4ac`](https://github.com/blairfrandeen/titr/commit/b8ac4aca7b8dc551b68152893cf80c494fb691db))

## v0.7.2 (2022-08-14)
### Fix
* Address crash when using --start and --end arguments. ([`a17ad27`](https://github.com/blairfrandeen/titr/commit/a17ad27ae51face4e3f7a0797a80578935f02df0))

## v0.7.1 (2022-08-14)
### Fix
* Enable command line arguments when using entry points after build. ([`47c3898`](https://github.com/blairfrandeen/titr/commit/47c3898d9270274dba3903e85c75609f1e8d1151))

## v0.7.0 (2022-08-14)
### Feature
* Time activities from the command line ([`4aeae4d`](https://github.com/blairfrandeen/titr/commit/4aeae4d499e9210a21837ff2889f0575a3e6560f))

## v0.6.1 (2022-08-10)
### Fix
* Fix crash when running with entry point and no arguments. ([`ba29a65`](https://github.com/blairfrandeen/titr/commit/ba29a65ffa78653872e2a99ad36e7944e3037aca))

## v0.6.0 (2022-08-10)
### Feature
* Added --outlook (-o) flag to start in outlook mode ([`bcd663e`](https://github.com/blairfrandeen/titr/commit/bcd663e249ad251d197927e83ca612075b9770b7))

### Fix
* Removed copy to clipboard on commit ([`2e76c78`](https://github.com/blairfrandeen/titr/commit/2e76c78dcb9ee8b1c5b2d6d84c56088ddd6c696e))
* Crash with deep work command ([`7a4c649`](https://github.com/blairfrandeen/titr/commit/7a4c649cb4b4f3c299676766309f413dca6946fb))
* Add backwards compatibility for database ([`5778797`](https://github.com/blairfrandeen/titr/commit/57787972862dc032d3200dd69ab210b832117600))
* Improve documentation for add function ([`1e840dd`](https://github.com/blairfrandeen/titr/commit/1e840dd65616c8fbe743cf7d5021780569e8dc7e))
* Catch nan time durations ([`42278c3`](https://github.com/blairfrandeen/titr/commit/42278c37e4b15af682271b3b6b89a0165dc58ad0))
* Replace Value and TypeError with InputError ([`6d3bc6a`](https://github.com/blairfrandeen/titr/commit/6d3bc6aa308312e082907fe8cafea9775d954f2a))
* Raise input errors instead of value/type errors for scale function. ([`8e1e953`](https://github.com/blairfrandeen/titr/commit/8e1e953258664f94ae22b062df705f43246d4ca9))

## v0.5.0 (2022-08-02)
### Feature
* Add export command for basic export to CSV from sqlite3 database. ([`571a3de`](https://github.com/blairfrandeen/titr/commit/571a3de8d91859c91a1923d31bcaab9faba9092b))

### Fix
* Restructure to fix import problems ([`6e2d461`](https://github.com/blairfrandeen/titr/commit/6e2d461aed9b85806d762f35cfd4de986682b6f8))

### Documentation
* Update changelog ([`94a3745`](https://github.com/blairfrandeen/titr/commit/94a374586ff20be982892c63c0cdb0d2443e83a0))

## v0.4.2 (2022-07-20)
### Fix
* Clipboard is not cleared when no time entries exist. ([`6e9197d`](https://github.com/blairfrandeen/titr/commit/6e9197de2355bca785dadcf45ac4a3365fe3f981))

## v0.4.0 (2022-07-16)
Version 0.4.0 includes full sqlite3 database support, and allows for titr to be fully used on a daily without an Excel spreadsheet.

### Feature
* Deep work function now displays color based on whether goal is being met. Greatly improved formatting. ([`d69a359`](https://github.com/blairfrandeen/titr/commit/d69a3593528f1bce32aba7f23317af407af07ad2))
* Import data from csv ([`c8c97d5`](https://github.com/blairfrandeen/titr/commit/c8c97d5cdf65c4e0c98d97c595e421a58adaccf9))
* Added basic timecard command and functionality ([`7647dc7`](https://github.com/blairfrandeen/titr/commit/7647dc7ddff9c0bea5997a13f115dc1337bd287a))
* Add command to display total deep work and deep work over last 365 days. ([`b2ea0e8`](https://github.com/blairfrandeen/titr/commit/b2ea0e80eb2b2cc245710a786124ef06301e27ae))

### Fix
* Timecard function improved formatting. ([`caa6a95`](https://github.com/blairfrandeen/titr/commit/caa6a9544e529ce149cec733c68c940173b563ec))
* Better formatting for TimeEntry string function ([`d703f6a`](https://github.com/blairfrandeen/titr/commit/d703f6a614e309143faf5c4dfb1735bd30af70b7))
* Better formatting of TimeEntry ([`e0903b1`](https://github.com/blairfrandeen/titr/commit/e0903b13462796a8deda4539350eb906ceb8d1fe))
* Cleaner text formatting for console help commands. ([`016251d`](https://github.com/blairfrandeen/titr/commit/016251d8213f696b3e8fb0afe05c55a01d99eb77))
* Help command no longer shows blank doc for some commands. ([`709af52`](https://github.com/blairfrandeen/titr/commit/709af5276f2587dac3e0925ccef20cf3fd43bcc6))
* Time entries in database now have correct user_key for categories; no longer linked to category_id erroneously. ([`d6da539`](https://github.com/blairfrandeen/titr/commit/d6da539b5b4724d7e2d3e1ad00c40226812a2550))
* Deep_work function pulls from ConsoleSession database. ([`c9edd69`](https://github.com/blairfrandeen/titr/commit/c9edd69dfa2f66bee0279184eb4246c2ca61cc56))
* Test and error handling if no time entries found within work week for timecard function. ([`e1253a5`](https://github.com/blairfrandeen/titr/commit/e1253a59bb44a4996c461e97ec7a08d26dd38203))
* Help function now displays multi-line dotstrings without unwanted indentation ([`aac1cb6`](https://github.com/blairfrandeen/titr/commit/aac1cb6c0bc14f682a24f81993852db751312d8a))
* Enforce unique ids and keys a for tasks table ([`722b204`](https://github.com/blairfrandeen/titr/commit/722b204651f75bd180e12714830a3d8527ee2bf4))
* Disable ability to call outlook commands from linux ([`b75753d`](https://github.com/blairfrandeen/titr/commit/b75753d8cb54017fca14acd2dffc385297cddc8c))
* Add default for console.outlook_item = None ([`011a90e`](https://github.com/blairfrandeen/titr/commit/011a90eef1a50bf55da774eb122ac4e190b41340))

## v0.3.4 (2022-07-15)
### Fix
* Fix distrubution error

## v0.3.0 (2022-07-07)
### Feature
* New console enabled for commands; not yet enabled for time entries. Getting excited about deleting some code soon. ([`9f9c271`](https://github.com/blairfrandeen/titr/commit/9f9c2719d3a2dadc05acf0ca0dc52e688202cdf0))
* Time entries can now be written to sqlite database. No read capability built in yet. ([`5ccecf6`](https://github.com/blairfrandeen/titr/commit/5ccecf6af218ac9cb2f3fc2a8b78f4153a38c8a1))
* More implementation of sqlite database ([`28bd494`](https://github.com/blairfrandeen/titr/commit/28bd49490b0ff05c667b263686b601707bdc6c3b))
* Start adding database functionality ([`d39a9a9`](https://github.com/blairfrandeen/titr/commit/d39a9a94638cd5a451629108bdd3bb10adfa4c29))

### Fix
* Scale command gives explicit error if no arguments given ([`823fc0f`](https://github.com/blairfrandeen/titr/commit/823fc0fb3c2347c048edbe81cf99ffb1f2917fd6))
* Report date set to today when no arguments given. ([`f929998`](https://github.com/blairfrandeen/titr/commit/f9299985cef3c3e9d9ec9a879d9c53cd943abfd9))
* Disallow scaling time entries to zero. ([`cbb8547`](https://github.com/blairfrandeen/titr/commit/cbb8547886ea5b0d634545da9f3de51ad88e0e52))

## v0.2.1 (2022-06-21)
### Fix
* Remove unwanted newlines. Add test cases to preview & copy functions. ([`a665661`](https://github.com/blairfrandeen/titr/commit/a665661e9ade0a7625c5f2667f38a85a09f50f66))
* Added missing newline in TSV output. ([`1cbd1c7`](https://github.com/blairfrandeen/titr/commit/1cbd1c78f7f1f9e0f2e2bad7a442104cbf79ef5a))
