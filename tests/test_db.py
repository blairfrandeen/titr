import datetime
import os
import pytest
import sqlite3


from dataclasses import dataclass
from titr import (
    db_initialize,
    db_session_metadata,
    db_populate_task_category_lists,
    db_write_time_log,
    TimeEntry,
)
from test_titr import console, titr_default_config

TEST_DB = ":memory:"
#  TEST_DB = "testdb.db"


@pytest.fixture
def db_connection(monkeypatch):
    # Remove old database file if it exists
    if TEST_DB != ":memory:":
        os.remove(TEST_DB)
    connection = db_initialize(TEST_DB, test_flag=True)
    #  connection = sqlite3.connect(TEST_DB, detect_types=sqlite3.PARSE_DECLTYPES)
    yield connection
    connection.commit()
    connection.close()


@dataclass
class MockUname:
    nodename: str = "windows_user"


def test_session_metadata(db_connection, monkeypatch):
    platforms: list = "linux windows other".split(" ")
    monkeypatch.setattr("os.uname", lambda: MockUname(), raising=False)
    monkeypatch.setattr("os.getlogin", lambda: "windows_user")
    for session_id, platform in enumerate(platforms):
        monkeypatch.setattr("sys.platform", platform)
        assert db_session_metadata(db_connection, test_flag=True) == session_id + 1


def test_populate_tables(console, db_connection):
    db_populate_task_category_lists(console, db_connection)
    cursor = db_connection.cursor()

    # Check category table columns
    find_cat_columns = """--sql
        PRAGMA table_info(categories)
    """
    cursor.execute(find_cat_columns)
    category_cols = cursor.fetchall()
    for index, name in enumerate(["id", "name"]):
        assert name in category_cols[index]

    # Check task table columns
    find_task_columns = """--sql
        PRAGMA table_info(tasks)
    """
    cursor.execute(find_task_columns)
    task_cols = cursor.fetchall()
    for index, name in enumerate("id key name".split(" ")):
        assert name in task_cols[index]


def test_write_time_log(console, db_connection):
    db_populate_task_category_lists(console, db_connection)
    console.time_entries.append(
        TimeEntry(console, duration=1, comment="test", task="t", category=9)
    )

    db_write_time_log(console, db_connection, 0)
    find_entry = """--sql
        SELECT session_id, duration, category_id, task_id, date, comment
        FROM time_log
        WHERE session_id=0
    """
    cursor = db_connection.cursor()
    cursor.execute(find_entry)
    db_entry = cursor.fetchone()
    cs_entry = console.time_entries[-1]
    for index, data in enumerate(
        [
            0,
            cs_entry.duration,
            cs_entry.category,
            1,  # default task id
            cs_entry.date.strftime("%Y-%m-%d"),
            cs_entry.comment,
        ]
    ):
        assert db_entry[index] == data
