#!/usr/bin/env python3
"""
Convert DuckDB database to SQLite database
"""
import duckdb
import sqlite3
from pathlib import Path

def convert_duckdb_to_sqlite(duckdb_path: str, sqlite_path: str):
    """Convert DuckDB database to SQLite"""

    print(f"Reading from DuckDB: {duckdb_path}")
    print(f"Writing to SQLite: {sqlite_path}")

    # Connect to DuckDB
    duck_con = duckdb.connect(duckdb_path, read_only=True)

    # Connect to SQLite
    sqlite_con = sqlite3.connect(sqlite_path)
    sqlite_cur = sqlite_con.cursor()

    # Get list of tables
    tables = duck_con.execute("SHOW TABLES").fetchall()
    print(f"\nFound {len(tables)} tables: {[t[0] for t in tables]}")

    for table_name, in tables:
        print(f"\nConverting table: {table_name}")

        # Get table schema
        schema = duck_con.execute(f"PRAGMA table_info('{table_name}')").fetchall()

        # Create table in SQLite
        columns = []
        for col in schema:
            col_name = col[1]
            col_type = col[2]
            # Map DuckDB types to SQLite types
            if 'VARCHAR' in col_type.upper() or 'TEXT' in col_type.upper():
                sqlite_type = 'TEXT'
            elif 'DOUBLE' in col_type.upper() or 'FLOAT' in col_type.upper():
                sqlite_type = 'REAL'
            elif 'BIGINT' in col_type.upper() or 'INTEGER' in col_type.upper():
                sqlite_type = 'INTEGER'
            elif 'TIMESTAMP' in col_type.upper():
                sqlite_type = 'TEXT'  # Store timestamps as text
            elif 'DATE' in col_type.upper():
                sqlite_type = 'TEXT'
            else:
                sqlite_type = 'TEXT'  # Default to TEXT

            columns.append(f"{col_name} {sqlite_type}")

        create_table_sql = f"CREATE TABLE {table_name} ({', '.join(columns)})"
        print(f"Creating table: {create_table_sql}")
        sqlite_cur.execute(f"DROP TABLE IF EXISTS {table_name}")
        sqlite_cur.execute(create_table_sql)

        # Copy data
        rows = duck_con.execute(f"SELECT * FROM {table_name}").fetchall()
        print(f"Copying {len(rows)} rows...")

        if rows:
            placeholders = ','.join(['?' for _ in rows[0]])
            insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"
            sqlite_cur.executemany(insert_sql, rows)

        print(f"✓ Completed {table_name}")

    # Commit and close
    sqlite_con.commit()
    duck_con.close()
    sqlite_con.close()

    print(f"\n✓ Conversion complete!")
    print(f"SQLite database created at: {sqlite_path}")

if __name__ == "__main__":
    import sys

    duckdb_file = "tibber_data.duckdb"
    sqlite_file = "tibber_data.sqlite"

    if len(sys.argv) > 1:
        duckdb_file = sys.argv[1]
    if len(sys.argv) > 2:
        sqlite_file = sys.argv[2]

    if not Path(duckdb_file).exists():
        print(f"Error: DuckDB file not found: {duckdb_file}")
        sys.exit(1)

    convert_duckdb_to_sqlite(duckdb_file, sqlite_file)
