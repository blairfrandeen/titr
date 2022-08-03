# Changelog

<!--next-version-placeholder-->

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
