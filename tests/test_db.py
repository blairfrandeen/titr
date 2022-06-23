import datetime
import pytest
import sqlite3

from titr import initialize_db, db_session_metadata


@pytest.fixture
def db_connection(monkeypatch):
    print("Creating Tables in test DB")
    initialize_db("testdb.db", test_flag=True)
    connection = sqlite3.connect("testdb.db", detect_types=sqlite3.PARSE_DECLTYPES)
    print("Connected to Test DB")
    yield connection
    connection.commit()
    print("Closing Test DB...")
    connection.close()


def test_session_metadata(db_connection, monkeypatch):
    def _mock_db_con(*args, **kwargs):
        return db_connection

    monkeypatch.setattr("sqlite3.connect", _mock_db_con)
    platforms: list = "linux windows other".split(" ")
    for session_id, platform in enumerate(platforms):
        monkeypatch.setattr("sys.platform", platform)
        assert db_session_metadata("database", test_flag=True) == session_id + 1
