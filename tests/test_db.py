import datetime
import pytest
import sqlite3


from dataclasses import dataclass
from titr import initialize_db, db_session_metadata, populate_task_category_lists
from test_titr import console, titr_default_config

TEST_DB = ":memory:"
TEST_DB = "testdb.db"


@pytest.fixture
def db_connection(monkeypatch):
    print("Creating Tables in test DB")
    connection = initialize_db(TEST_DB, test_flag=True)
    #  connection = sqlite3.connect(TEST_DB, detect_types=sqlite3.PARSE_DECLTYPES)
    print("Connected to Test DB")
    yield connection
    connection.commit()
    print("Closing Test DB...")
    connection.close()


@dataclass
class MockUname:
    nodename: str = "windows_user"


def test_session_metadata(db_connection, monkeypatch):
    platforms: list = "linux windows other".split(" ")
    monkeypatch.setattr("os.uname", lambda: MockUname())
    monkeypatch.setattr("os.getlogin", lambda: "windows_user")
    for session_id, platform in enumerate(platforms):
        monkeypatch.setattr("sys.platform", platform)
        assert db_session_metadata(db_connection, test_flag=True) == session_id + 1


@pytest.mark.xfail
def test_populate_tables(console, db_connection):
    populate_task_category_lists(console, db_connection)
    # TODO: Write some actual tests.
    # Inspected database manually, tables appear to populate as desired.
    assert 0
