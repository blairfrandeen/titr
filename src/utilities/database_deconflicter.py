import argparse
import sqlite3
from os import PathLike
from typing import Optional


# TODO: Rewrite this module so that it can also be used to merge two databases
# while detecting and not writing duplicate data
def find_conflicts(
    master_db: str | bytes | PathLike, conflict_db: str | bytes | PathLike
) -> dict[str, list[int]]:
    """
    Find conflicts between two SQLite databases. A conflict is defined as any row with the
    same primary key but different data between the two databases. This can occur when
    database files get out of sync, for example when backing up to a shared drive.


    Args:
        master_db (str | bytes | PathLike): Path to the master database file.
        conflict_db (str | bytes | PathLike): Path to the conflict database file.

    Returns:
        dict[str, list[int]]: A dictionary containing table names as keys and lists
        of conflicting primary key values as values.
    """
    conflicts: dict[str, list[int]] = {}
    if isinstance(master_db, (str, PathLike)) and isinstance(
        conflict_db, (str, PathLike)
    ):
        print(f"Checking for conflicts between '{master_db}' and '{conflict_db}'...")

    # Connect to databases
    conn1 = sqlite3.connect(master_db)
    conn2 = sqlite3.connect(conflict_db)
    cursor1 = conn1.cursor()
    cursor2 = conn2.cursor()

    # Get table names
    cursor1.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables1 = cursor1.fetchall()

    # Find conflicts in each table
    for table1 in tables1:
        table_name = table1[0]

        # Get primary key column name
        cursor1.execute(f"PRAGMA table_info({table_name})")
        table_info1 = cursor1.fetchall()
        primary_key_col: Optional[int] = None
        for col_info in table_info1:
            if col_info[5] == 1:
                primary_key_col = col_info[1]
                break

        if primary_key_col is None:
            continue

        # Get maximum value in primary key column for conflict database
        cursor2.execute(f"SELECT MAX({primary_key_col}) FROM {table_name}")
        max_id2 = cursor2.fetchone()[0]

        if max_id2 is None:
            continue

        # Find conflicts in primary key column
        for row_id in range(max_id2, max_id2 - 500, -1):
            cursor_start = conn1.cursor()
            cursor_search = conn2.cursor()
            cursor_start.execute(
                f"SELECT * FROM {table_name} WHERE {primary_key_col} = ?", (row_id,)
            )
            row_start = cursor_start.fetchone()
            cursor_search.execute(
                f"SELECT * FROM {table_name} WHERE {primary_key_col} = ?", (row_id,)
            )
            row_search = cursor_search.fetchone()

            if row_start != row_search:
                if table_name not in conflicts:
                    conflicts[table_name] = []
                conflicts[table_name].append(row_id)

    cursor1.close()
    cursor2.close()
    conn1.close()
    conn2.close()

    return conflicts


def resolve_conflicts(
    master_db: str | bytes | PathLike, conflict_db: str | bytes | PathLike
) -> None:
    """
    Given two database files with similar schema, find all conflicts.
    Then for each conflict in the time_log table, copy the version of the conflict
    from the conflict_db to the master_db. Assign a new primary key in the master_db.
    In doing so, check that the category_id, task_id, and session_id keys are not also
    conflicts for the categories, sessions, and task tables, respectively. If these
    are also conflicts, run update_table_for_conflict, and update the tables,
    and the keys in the new time_log entry accordingly.

    It is assumed that the master_db is _ahead of_ the conflict_db, meaning that the
    primary_key of the master_db tables is larger than that of the conflict_db tables

    Args:
        master_db (str): File path of the master database.
        conflict_db (str): File path of the conflicting database.

    Returns:
        None
    """
    # Connect to the master and conflict databases
    master_conn = sqlite3.connect(master_db)
    conflict_conn = sqlite3.connect(conflict_db)

    # Create cursors for the master and conflict databases
    master_cursor = master_conn.cursor()
    conflict_cursor = conflict_conn.cursor()

    # Find conflicts between master and conflict databases
    conflicts = find_conflicts(master_db, conflict_db)

    # Iterate through each conflict in the time_log table
    for primary_key in conflicts.get("time_log", []):
        # Copy the conflict entry from conflict_db to master_db
        new_key = update_table_for_conflict(
            master_cursor, conflict_cursor, "time_log", primary_key
        )
        print(f"Updating time_log duplicating primary key id {primary_key}...")

        # Check if category_id, task_id, and session_id are also conflicts
        for column_name, table in zip(
            ("category_id", "task_id", "session_id"),
            ("categories", "tasks", "sessions"),
        ):
            # Check to see if there's a conflicting reference
            master_cursor.execute(
                f"SELECT {column_name} FROM time_log where id=?", (new_key,)
            )
            reference_id = master_cursor.fetchone()[0]
            if reference_id in conflicts.get(table, []):
                new_id = update_table_for_conflict(
                    master_cursor, conflict_cursor, table, reference_id
                )
                master_cursor.execute(
                    f"UPDATE time_log SET {column_name}=? WHERE id=?", (new_id, new_key)
                )
                conflicts[table].remove(reference_id)

    # Commit changes and close connections
    master_conn.commit()
    master_conn.close()
    conflict_conn.close()


def update_table_for_conflict(
    master_cursor: sqlite3.Cursor,
    conflict_cursor: sqlite3.Cursor,
    table_name: str,
    conflict_key: int,
) -> Optional[int]:
    """
    Given sqlite3 cursors for a master database and a conflicting database, along with
    the name of a table that exists in both databases, and the primary key for the conflicting
    data, make a copy of the data from the conflicting database into the master database.
    If any columns are missing from the conflicting database due to an updated schema, simply
    fill those columns in the master database with None values. The new entry in the master
    database should have an autogenerated primary key.

    Args:
        master_cursor (sqlite3.Cursor): Cursor object for the master database.
        conflict_cursor (sqlite3.Cursor): Cursor object for the conflicting database.
        table_name (str): Name of the table that exists in both databases.
        conflict_key (int): Primary key of the conflicting data.

    Returns:
        int: The primary key of the new entry in the master database.
    """
    print(f"Updating {table_name} primary key id {conflict_key}...")
    # Fetch the conflicting row from the conflict database
    conflict_cursor.execute(f"SELECT * FROM {table_name} WHERE id=?", (conflict_key,))
    conflict_row = conflict_cursor.fetchone()

    # Get the column names of the table in both master and conflict databases
    master_cursor.execute(f"PRAGMA table_info({table_name})")
    master_columns = [col[1] for col in master_cursor.fetchall()]

    conflict_cursor.execute(f"PRAGMA table_info({table_name})")
    conflict_columns = [col[1] for col in conflict_cursor.fetchall()]

    # Fill any missing columns in the conflict row with None values
    for column in master_columns:
        if column not in conflict_columns:
            conflict_row += (None,)

    # Insert the conflict row into the master database
    # placeholders = ['?'] * (len(conflict_row) - 1)
    # column_names = ', '.join([column for column in conflict_row._fields[1:]])
    # new_values = ', '.join(placeholders)
    # master_cursor.execute(f"INSERT INTO {table_name} ({column_names}) VALUES ({new_values})", conflict_row[1:])
    placeholders = ["?"] * len(master_columns[1:])
    new_values = ", ".join(placeholders)
    master_cursor.execute(
        f"INSERT INTO {table_name} ({', '.join(master_columns[1:])}) VALUES ({new_values})",
        conflict_row[1:],
    )
    # master_cursor.execute(f"INSERT INTO {table_name} VALUES ({new_values})", conflict_row)
    conflict_cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (conflict_key,))
    conflict_cursor.connection.commit()
    new_key = master_cursor.lastrowid

    return new_key


def main():
    # Create an ArgumentParser object
    parser = argparse.ArgumentParser(description="titr database deconflicter.\
            Use this utility to resolve conflicts created by cloud storage,\
            Backup your titr.db file before use!")

    # Add positional arguments for the two database file names
    parser.add_argument(
        "master_db",
        type=str,
        help="Master database file name.\
            Entries from the conflict_db will be written to this file!",
    )
    parser.add_argument(
        "conflict_db",
        type=str,
        help="Conflict database file name.\
            Conflicting entries with the master database will be REMOVED from this file!",
    )

    # Add optional argument to show conflicts
    parser.add_argument("--show", action="store_true", help="Show conflicts")

    # Add optional argument to resolve conflicts
    parser.add_argument(
        "--resolve",
        action="store_true",
        help="Resolve conflicts. Recommend backing up your master database before running this command!",
    )

    # Parse the command-line arguments
    args = parser.parse_args()

    # Call the find_conflicts function with the provided database file names
    db_files = (args.master_db, args.conflict_db)
    conflicts = find_conflicts(*db_files)

    # If --show option is provided, print conflicts
    if args.show:
        for table, rows in conflicts.items():
            print("Conflicts in table:", table, rows)

    # If --resolve option is provided, resolve conflicts
    if args.resolve:
        resolve_conflicts(*db_files)


if __name__ == "__main__":
    main()
