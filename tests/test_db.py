import os
import pytest


from dataclasses import dataclass
from titr.titr_main import (
    _fetch_first,
    db_session_metadata,
    db_populate_task_category_lists,
    db_write_time_log,
    TimeEntry,
)
from test_config import titr_default_config
from test_titr import console, db_connection


@dataclass
class MockUname:
    nodename: str = "windows_user"


def test_session_metadata(db_connection, monkeypatch):
    platforms: list = "linux windows other".split(" ")
    monkeypatch.setattr("os.uname", lambda: MockUname(), raising=False)
    monkeypatch.setattr("os.getlogin", lambda: "windows_user")
    for session_id, platform in enumerate(platforms):
        monkeypatch.setattr("sys.platform", platform)
        assert (
            db_session_metadata(db_connection, input_type="test", test_flag=True) == session_id + 1
        )


@pytest.mark.parametrize(
    "query_result, default, expected",
    [
        ((1,), None, 1),
        (None, None, None),
        (("four", 5, 6), None, "four"),
        (None, 0, 0),
        ((1,), 0, 1),
    ],
)
def test_fetch_first(query_result, default, expected):
    class _MockCursor:
        def fetchone(self):
            return query_result

    assert _fetch_first(_MockCursor(), default=default) == expected


def test_populate_tables(console):
    db_populate_task_category_lists(console)
    cursor = console.db_connection.cursor()

    # Check category table columns
    find_cat_columns = """--sql
        PRAGMA table_info(categories)
    """
    cursor.execute(find_cat_columns)
    category_cols = cursor.fetchall()

    # Check task table columns
    find_task_columns = """--sql
        PRAGMA table_info(tasks)
    """
    cursor.execute(find_task_columns)
    task_cols = cursor.fetchall()
    for index, name in enumerate("id user_key name".split(" ")):
        assert name in category_cols[index]
        assert name in task_cols[index]


def test_write_time_log(console):
    db_populate_task_category_lists(console)
    cs_entry = console.add_entry(TimeEntry(1.11))

    db_write_time_log(console, 0)
    find_entry = """--sql
        SELECT l.duration, c.user_key, t.user_key, l.date, l.comment, l.start_ts, l.end_ts
        FROM time_log l
        JOIN tasks t ON t.id=l.task_id
        JOIN categories c ON c.id=l.category_id
        WHERE l.session_id=0
    """
    cursor = console.db_connection.cursor()
    cursor.execute(find_entry)
    db_entry = cursor.fetchone()
    for index, data in enumerate(
        [
            cs_entry.duration,  # 1 hr
            str(cs_entry.category),  # user_key = 3 ("email")
            cs_entry.task,  # user_key = 't' ("titr")
            cs_entry.date.strftime("%Y-%m-%d"),  # today
            cs_entry.comment,  # "test"
            cs_entry.start_ts,  # none
            cs_entry.end_ts,  # none
        ]
    ):
        assert db_entry[index] == data
