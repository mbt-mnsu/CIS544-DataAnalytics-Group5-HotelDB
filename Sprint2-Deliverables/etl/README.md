# ETL Tool: SQL Server --> MongoDB

## Overview

This Python script migrates **all tables and rows** from the SQL Server `Hotel` database into a new MongoDB database called `hotel_sql_mirror`.

## Prerequisites

- Python 3.x installed
- Required packages: `pymongo`, `pyodbc`
- ODBC Driver 17 for SQL Server

## Setup

```bash
pip install -r requirements.txt
```

## Usage

**First run (or to add new data alongside existing):**
```bash
python etl_sql_to_mongo.py
```

**Clean run (drop existing collections first, then re-insert):**
```bash
python etl_sql_to_mongo.py --clean
```

## What It Does

1. Connects to SQL Server (`Hotel` database) and MongoDB
2. Reads all tables (excluding system tables like `sysdiagrams`)
3. For each table:
   - Reads all rows in batches of 10,000
   - Converts data types: `Decimal` → `float`, `date` → `datetime`, `None` → omitted
   - Inserts documents into a MongoDB collection with the same table name
4. After migration, verifies row counts match between source and target

## Tables Migrated

| Table | Approximate Rows |
|---|---|
| customer | 623,710 |
| event | 17,822,709 |
| property | 245 |
| property_rooms | 797 |
| room_type | 5 |
| transact | 8,905,489 |
| transaction_line | 29,373,666 |

## Configuration

Connection details are stored at the top of `etl_sql_to_mongo.py`.
