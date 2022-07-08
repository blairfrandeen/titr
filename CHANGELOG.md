# Changelog

<!--next-version-placeholder-->

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
