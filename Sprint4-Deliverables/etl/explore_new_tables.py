"""
Sprint 4 - Explore new tables in the source databases.
Discovers employee, payroll, amenity, and any new tables.
"""

import pyodbc
import pymongo
from datetime import datetime

# Connection config (same as existing ETL)
SQL_SERVER = "cis444.campus-quest.com,25000"
SQL_DB = "Hotel"
SQL_USER = "sa"
SQL_PASSWORD = "Academic2026U05!"

MONGO_URI = "mongodb://admin:Academic2026U05!@cis444.campus-quest.com:25010/?tlsInsecure=true&authSource=admin"
MONGO_DATABASE = "hotel"


def explore_sql_server():
    print("=" * 70)
    print("SQL SERVER: Hotel Database - All Tables")
    print("=" * 70)
    conn = pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SQL_SERVER};DATABASE={SQL_DB};UID={SQL_USER};PWD={SQL_PASSWORD};"
        f"TrustServerCertificate=yes;Connection Timeout=30;"
    )
    cursor = conn.cursor()

    # List ALL tables
    cursor.execute("""
        SELECT t.TABLE_NAME, 
               (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS c WHERE c.TABLE_NAME = t.TABLE_NAME) AS col_count
        FROM INFORMATION_SCHEMA.TABLES t
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
    """)
    tables = cursor.fetchall()
    print(f"\nTotal tables: {len(tables)}")
    for t in tables:
        # Get row count
        try:
            cursor.execute(f"SELECT COUNT(*) FROM [{t[0]}]")
            count = cursor.fetchone()[0]
        except:
            count = "ERROR"
        print(f"  {t[0]:30s} | {t[1]:3d} columns | {count:>12,} rows")

    # Look at each new table's schema
    known_tables = {'customer', 'event', 'property', 'property_rooms', 'room_type', 'sysdiagrams', 'transact', 'transaction_line'}
    new_tables = [t[0] for t in tables if t[0] not in known_tables]

    for table_name in new_tables:
        print(f"\n{'=' * 70}")
        print(f"NEW TABLE: {table_name}")
        print(f"{'=' * 70}")
        cursor.execute(f"""
            SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = '{table_name}'
            ORDER BY ORDINAL_POSITION
        """)
        cols = cursor.fetchall()
        for col in cols:
            length = f"({col[2]})" if col[2] else ""
            print(f"  {col[0]:30s} | {col[1]}{length:10s} | Nullable: {col[3]}")

        # FK relationships
        cursor.execute(f"""
            SELECT 
                fk.name AS fk_name,
                cp.name AS parent_col,
                tr.name AS ref_table,
                cr.name AS ref_col
            FROM sys.foreign_keys fk
            JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
            JOIN sys.columns cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
            JOIN sys.tables tr ON fkc.referenced_object_id = tr.object_id
            JOIN sys.columns cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id
            WHERE OBJECT_NAME(fk.parent_object_id) = '{table_name}'
        """)
        fks = cursor.fetchall()
        if fks:
            print(f"  Foreign Keys:")
            for fk in fks:
                print(f"    {fk[1]} -> {fk[2]}.{fk[3]} ({fk[0]})")

        # Sample data
        try:
            cursor.execute(f"SELECT TOP 3 * FROM [{table_name}]")
            sample = cursor.fetchall()
            col_names = [desc[0] for desc in cursor.description]
            print(f"  Sample ({min(3, len(sample))} rows):")
            for row in sample:
                print(f"    {dict(zip(col_names, row))}")
        except Exception as e:
            print(f"  Sample error: {e}")

    # Check for new data range in existing tables
    print(f"\n{'=' * 70}")
    print("DATA RANGE CHECK: Existing tables")
    print(f"{'=' * 70}")

    cursor.execute("SELECT MIN(event_date), MAX(event_date), COUNT(*) FROM event")
    r = cursor.fetchone()
    print(f"  event: {r[0]} to {r[1]} ({r[2]:,} rows)")

    cursor.execute("SELECT MIN(transaction_date), MAX(transaction_date), COUNT(*) FROM transact")
    r = cursor.fetchone()
    print(f"  transact: {r[0]} to {r[1]} ({r[2]:,} rows)")

    cursor.execute("SELECT COUNT(*) FROM customer")
    r = cursor.fetchone()
    print(f"  customer: {r[0]:,} rows")

    conn.close()


def explore_mongodb():
    print(f"\n{'=' * 70}")
    print("MONGODB: hotel Database")
    print(f"{'=' * 70}")
    client = pymongo.MongoClient(MONGO_URI)
    db = client[MONGO_DATABASE]
    collections = db.list_collection_names()
    print(f"Collections: {collections}")
    for coll_name in sorted(collections):
        coll = db[coll_name]
        count = coll.count_documents({})
        print(f"  {coll_name:25s} | {count:>12,} documents")

        # Check for date ranges in transactions
        if coll_name == 'transactions':
            pipeline = [
                {"$group": {"_id": None, "min_date": {"$min": "$timestamp"}, "max_date": {"$max": "$timestamp"}}}
            ]
            result = list(coll.aggregate(pipeline))
            if result:
                print(f"    Date range: {result[0]['min_date']} to {result[0]['max_date']}")

    client.close()


if __name__ == "__main__":
    explore_sql_server()
    explore_mongodb()
