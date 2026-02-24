"""
ETL Tool: SQL Server (Hotel) → MongoDB
=======================================
Migrates ALL tables and rows from the Hotel SQL Server database
into a new MongoDB database called 'hotel_sql_mirror'.

Usage:
    python etl_sql_to_mongo.py [--clean]

Options:
    --clean     Drop existing MongoDB collections before inserting
"""

import pyodbc
import pymongo
import sys
import time
from datetime import datetime, date
from decimal import Decimal


SQL_SERVER = "cis444.campus-quest.com,25000"
SQL_DATABASE = "Hotel"
SQL_USER = "sa"
SQL_PASSWORD = "Academic2026U05!"

MONGO_URI = "mongodb://admin:Academic2026U05!@cis444.campus-quest.com:25010/?tlsInsecure=true&authSource=admin"
MONGO_DATABASE = "hotel_sql_mirror"  # New database for migrated data

BATCH_SIZE = 10000  # Rows to insert per batch (for memory efficiency)

# Tables to skip (system tables)
SKIP_TABLES = ["sysdiagrams"]


def connect_sql_server():
    """Connect to SQL Server and return connection."""
    print(f"[SQL Server] Connecting to {SQL_SERVER}/{SQL_DATABASE}...")
    conn = pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SQL_SERVER};"
        f"DATABASE={SQL_DATABASE};"
        f"UID={SQL_USER};"
        f"PWD={SQL_PASSWORD};"
        f"TrustServerCertificate=yes;"
    )
    print("[SQL Server] Connected successfully.")
    return conn


def connect_mongodb():
    """Connect to MongoDB and return client + database."""
    print(f"[MongoDB] Connecting to {MONGO_DATABASE}...")
    client = pymongo.MongoClient(MONGO_URI)
    # Test connection
    client.admin.command("ping")
    db = client[MONGO_DATABASE]
    print("[MongoDB] Connected successfully.")
    return client, db


def get_tables(sql_conn):
    """Get list of user tables from SQL Server."""
    cursor = sql_conn.cursor()
    cursor.execute(
        "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
        "WHERE TABLE_TYPE='BASE TABLE' ORDER BY TABLE_NAME"
    )
    tables = [row[0] for row in cursor.fetchall() if row[0] not in SKIP_TABLES]
    cursor.close()
    return tables


def get_row_count(sql_conn, table_name):
    """Get the row count for a table."""
    cursor = sql_conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
    count = cursor.fetchone()[0]
    cursor.close()
    return count


def convert_value(value):
    """Convert SQL Server data types to MongoDB-friendly types."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value  # pymongo handles datetime natively
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, bytes):
        return None  # Skip binary data
    return value


def migrate_table(sql_conn, mongo_db, table_name, clean=False):
    """Migrate a single table from SQL Server to MongoDB."""
    collection = mongo_db[table_name]

    # Drop existing collection if --clean flag is set
    if clean:
        collection.drop()
        print(f"  [Clean] Dropped existing '{table_name}' collection.")

    # Get row count for progress tracking
    total_rows = get_row_count(sql_conn, table_name)
    print(f"  [SQL] Reading {total_rows:,} rows from '{table_name}'...")

    # Read data from SQL Server
    cursor = sql_conn.cursor()
    cursor.execute(f"SELECT * FROM [{table_name}]")
    columns = [desc[0] for desc in cursor.description]

    inserted = 0
    batch = []
    start_time = time.time()

    for row in cursor:
        # Convert row to dictionary
        doc = {}
        for col_name, value in zip(columns, row):
            converted = convert_value(value)
            if converted is not None:  # Skip None values
                doc[col_name] = converted
        batch.append(doc)

        # Insert in batches
        if len(batch) >= BATCH_SIZE:
            collection.insert_many(batch)
            inserted += len(batch)
            elapsed = time.time() - start_time
            rate = inserted / elapsed if elapsed > 0 else 0
            pct = (inserted / total_rows * 100) if total_rows > 0 else 100
            print(f"  [MongoDB] Inserted {inserted:,}/{total_rows:,} ({pct:.1f}%) - {rate:.0f} rows/sec")
            batch = []

    # Insert remaining rows
    if batch:
        collection.insert_many(batch)
        inserted += len(batch)

    elapsed = time.time() - start_time
    cursor.close()

    print(f"  [Done] '{table_name}': {inserted:,} documents in {elapsed:.1f}s")
    return inserted


def verify_migration(sql_conn, mongo_db, tables):
    """Compare row counts between SQL Server and MongoDB."""
    print("\n" + "=" * 60)
    print("VERIFICATION: Comparing row counts")
    print("=" * 60)

    all_match = True
    for table in tables:
        sql_count = get_row_count(sql_conn, table)
        mongo_count = mongo_db[table].count_documents({})
        match = "✅" if sql_count == mongo_count else "❌"
        if sql_count != mongo_count:
            all_match = False
        print(f"  {match} {table}: SQL={sql_count:,} | MongoDB={mongo_count:,}")

    if all_match:
        print("\n✅ ALL TABLES MATCH — Migration verified successfully!")
    else:
        print("\n❌ MISMATCH DETECTED — Please review the tables above.")

    return all_match


def main():
    clean = "--clean" in sys.argv

    print("=" * 60)
    print("ETL Tool: SQL Server (Hotel) → MongoDB")
    print("=" * 60)
    print(f"  Source: {SQL_SERVER}/{SQL_DATABASE}")
    print(f"  Target: MongoDB/{MONGO_DATABASE}")
    print(f"  Clean mode: {'ON' if clean else 'OFF'}")
    print(f"  Batch size: {BATCH_SIZE:,}")
    print("=" * 60)

    # Connect to both databases
    sql_conn = connect_sql_server()
    mongo_client, mongo_db = connect_mongodb()

    try:
        # Get list of tables
        tables = get_tables(sql_conn)
        print(f"\nFound {len(tables)} tables to migrate: {tables}")

        # Migrate each table
        total_start = time.time()
        total_docs = 0

        for i, table in enumerate(tables, 1):
            print(f"\n[{i}/{len(tables)}] Migrating '{table}'...")
            count = migrate_table(sql_conn, mongo_db, table, clean=clean)
            total_docs += count

        total_elapsed = time.time() - total_start
        print(f"\n{'=' * 60}")
        print(f"Migration complete: {total_docs:,} total documents in {total_elapsed:.1f}s")
        print(f"{'=' * 60}")

        # Verify
        verify_migration(sql_conn, mongo_db, tables)

    finally:
        sql_conn.close()
        mongo_client.close()
        print("\nConnections closed.")


if __name__ == "__main__":
    main()
