import datetime
import os
import sys
import sqlite3
from typing import Optional, Any

from titr import TITR_DB, __db_user_version__, __version__

######################
# DATABASE FUNCTIONS #
######################
def db_initialize(database: str = TITR_DB) -> sqlite3.Connection:
    """Initialize the database, and create all tables."""
    db_connection = sqlite3.connect(database)
    cursor = db_connection.cursor()

    # Create time log table
    time_log_table = """--sql
        CREATE TABLE IF NOT EXISTS time_log(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE,
            duration FLOAT,
            category_id INT,
            task_id INT,
            session_id INT,
            comment TEXT,
            start_ts TIMESTAMP,
            end_ts TIMESTAMP
        )
    """
    # Create category table
    category_table = """--sql
        CREATE TABLE IF NOT EXISTS categories(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_key TEXT,
            name TEXT
        )
    """
    # Create task table
    task_table = """--sql
        CREATE TABLE IF NOT EXISTS tasks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_key TEXT,
            name TEXT
        )
    """
    # Create sessions table
    session_table = """--sql
        CREATE TABLE IF NOT EXISTS sessions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titr_version TEXT,
            user TEXT,
            platform TEXT,
            ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            input_type TEXT
        )
    """

    for table in [time_log_table, category_table, task_table, session_table]:
        cursor.execute(table)
    db_connection.commit()

    # Check that version is correct
    cursor.execute("PRAGMA user_version")
    user_version = cursor.fetchone()[0]
    if user_version != __db_user_version__:
        db_update_version(db_connection, user_version)

    return db_connection


def db_update_version(db_connection: sqlite3.Connection, user_version: int) -> int:
    """Update the sqlite3 database from an older version.
    Return the new version number."""
    cursor = db_connection.cursor()

    print(f"Updating database from version {user_version} to {__db_user_version__}...")

    def _get_column_names(table_name: str) -> list[str]:
        """Get the column names from a table."""
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [col[1] for col in cursor.fetchall()]

    if user_version < 1:
        # Rename key to user_key in tasks
        task_columns = _get_column_names("tasks")
        if "user_key" not in task_columns:
            print(" Rename key to user_key in tasks...")
            cursor.execute("ALTER TABLE tasks RENAME COLUMN key TO user_key")

        # Add user_key to categories table
        categories_columns = _get_column_names("categories")
        if "user_key" not in categories_columns:
            print(" Add user_key to categories table...")
            cursor.execute("ALTER TABLE categories ADD COLUMN user_key TEXT")

        # Add input_type to sessions table
        sessions_columns = _get_column_names("sessions")
        if "input_type" not in sessions_columns:
            print(" Add input_type to sessions table...")
            cursor.execute("ALTER TABLE sessions ADD COLUMN input_type TEXT")

    if user_version < 2:
        # Add start and end timestamps to time log
        time_log_columns = _get_column_names("time_log")
        if "start_ts" not in time_log_columns:
            print(" Add start_ts to time_log table...")
            cursor.execute("ALTER TABLE time_log ADD COLUMN start_ts TEXT")
        if "end_ts" not in time_log_columns:
            print(" Add end_ts to time_log table...")
            cursor.execute("ALTER TABLE time_log ADD COLUMN end_ts TEXT")

    # Set the user version to the current version
    cursor.execute("PRAGMA user_version={}".format(__db_user_version__))
    db_connection.commit()
    print("Complete.")

    return __db_user_version__


def db_populate_user_table(
    db_connection: sqlite3.Connection,
    table: str,
    value: str,
    user_key: Optional[str] = None,
    test_flag: bool = False,
) -> int:
    """Populate a single row of a table with a key-value pair.

    Will update an existing entry if the name (value) field is recognized.
    Otherwise a new entry will be added.
    User keys will be enforced to be unique.

    Return the primary_key of the entry"""
    # Determine the id of the row to populate
    # Search the table and find the id of the item with a matching name
    cursor = db_connection.cursor()

    get_primary_key: str = """--sql
        SELECT id FROM {} WHERE name=(?)
    """.format(
        table
    )
    cursor.execute(get_primary_key, [value])
    primary_key_query: Optional[tuple] = cursor.fetchone()

    # If no result, create a new table row
    if primary_key_query is None:
        get_last_key: str = "SELECT MAX(id) from {}".format(table)
        cursor.execute(get_last_key, [])
        last_key: tuple[Optional[int]] = cursor.fetchone()
        # start at zero if table is empty:7
        primary_key: int = 0 if last_key[0] is None else last_key[0] + 1
    else:
        primary_key = primary_key_query[0]

    if user_key is not None:
        write_table: str = """--sql
            REPLACE INTO {} (id, user_key, name) VALUES (?, ?, ?)
        """.format(
            table
        )
        cursor.execute(write_table, [primary_key, user_key, value])

        # Ensure that all keys in the table are unique
        enforce_unique_keys: str = """--sql
            UPDATE {} SET user_key=null WHERE id != (?) AND user_key = (?)
        """.format(
            table
        )
        cursor.execute(enforce_unique_keys, [primary_key, user_key])
    else:
        write_table = """--sql
            INSERT OR REPLACE INTO {} (id, name) VALUES (?, ?)
        """.format(
            table
        )
        cursor.execute(write_table, [primary_key, value])

    return primary_key


def db_populate_task_category_lists(console) -> None:
    """Populate the category & task tables in the sqlite db."""
    for user_key, value in console.config.category_list.items():
        db_populate_user_table(console.db_connection, "categories", value, user_key)

    for user_key, value in console.config.task_list.items():
        db_populate_user_table(console.db_connection, "tasks", value, user_key)

    console.db_connection.commit()


def db_session_metadata(
    db_connection: sqlite3.Connection, input_type: str = "user", test_flag: bool = False
) -> int:
    """Make entry in session table and return the session id."""
    cursor = db_connection.cursor()
    new_entry: str = """--sql
        INSERT INTO sessions (titr_version, user, platform, input_type) VALUES (?, ?, ?, ?)
    """
    platform: str = sys.platform
    if "linux" in platform:
        user = os.uname().nodename
    elif "win" in platform:
        user = os.getlogin()
    else:
        user = None

    cursor.execute(new_entry, [__version__, user, platform, input_type])
    #  if not test_flag:  # pragma: no cover
    db_connection.commit()

    get_session_id: str = """--sql
        SELECT MAX(id) from sessions
    """
    cursor.execute(get_session_id)
    session_id = cursor.fetchone()[0]
    #  if not test_flag:  # pragma: no cover
    #  db_connection.close()

    return session_id


def fetch_first(cursor: sqlite3.Cursor, default: Optional[Any] = None) -> Optional[Any]:
    """Given the result of an sql query from a cursor.fetchone()
    call, return the first element if it exists.

    Adjust the default keyword argument if default other than
    None is desired"""
    query_result = cursor.fetchone()
    return default if query_result is None else query_result[0]


def db_write_time_log(console, session_id: int) -> None:
    """Write time entries from console session to database."""
    cursor = console.db_connection.cursor()
    write_entry = """--sql
        INSERT INTO time_log (date, duration, category_id, task_id, comment, session_id, start_ts, end_ts)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    update_entry = """--sql
        UPDATE time_log SET (date, duration, category_id, task_id, comment, session_id, start_ts, end_ts) =
        (?, ?, ?, ?, ?, ?, ?, ?)
        WHERE id = (?)
    """
    get_task_id = """--sql
        SELECT id
        FROM tasks
        WHERE user_key = (?)
    """
    get_category_id = """--sql
        SELECT id
        FROM categories
        WHERE user_key = (?)
    """
    for entry in console.time_entries:
        # TODO: Handling for no task ID found
        cursor.execute(get_task_id, [entry.task])
        task_id = fetch_first(cursor)
        cursor.execute(get_category_id, [entry.category])
        category_id = fetch_first(cursor)
        entry_parameters = [
            entry.date,
            entry.duration,
            category_id,
            task_id,
            entry.comment,
            session_id,
            entry.start_ts,
            entry.end_ts,
        ]
        if entry.time_log_id is not None:
            # update existing entry
            entry_parameters.append(entry.time_log_id)
            cursor.execute(update_entry, entry_parameters)
        else:
            cursor.execute(write_entry, entry_parameters)
    console.db_connection.commit()


def query_deep_work(console) -> tuple[float, float]:
    """Query the database for deep work hours.
    Returns tuple of total and total over past 365 days."""
    cursor = console.db_connection.cursor()

    get_dw_total = """--sql
        SELECT sum(duration) FROM time_log t
        JOIN categories c on t.category_id=c.id
        WHERE c.name = 'Deep Work'
    """
    cursor.execute(get_dw_total)
    dw_total = fetch_first(cursor)
    if dw_total is None:
        return 0.0, 0.0

    get_dw_last_365 = get_dw_total + " AND date>=(?)"
    last_year = datetime.date.today() - datetime.timedelta(days=365)
    cursor.execute(get_dw_last_365, [last_year])
    dw_last_365 = fetch_first(cursor)
    if dw_last_365 is None:
        dw_last_365 = 0.0

    return dw_total, dw_last_365
