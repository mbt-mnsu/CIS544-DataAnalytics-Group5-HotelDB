"""
Sprint 6 — Gift Shop Open Dataset ETL (Data Load Only)
=======================================================
Loads PII-free data into GiftShopOpenDataset from HotelDW.

Prerequisites:
    Run GiftShopOpenDataset-DDL.sql in SSMS first to create the database and tables.

Usage:
    python etl_gift_shop_dataset.py
"""

import pyodbc
import time

# ============================================================
# Configuration
# ============================================================

SQL_SERVER = "cis444.campus-quest.com,25000"
SQL_DW_DB = "HotelDW"
SQL_DEST_DB = "GiftShopOpenDataset"
SQL_USER = "sa"
SQL_PASSWORD = "Academic2026U05!"

BATCH_SIZE = 5000


def get_conn(database):
    """Get a fresh SQL Server connection."""
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SQL_SERVER};"
        f"DATABASE={database};"
        f"UID={SQL_USER};"
        f"PWD={SQL_PASSWORD};"
        f"TrustServerCertificate=yes;"
        f"Connection Timeout=30;"
    )


# ============================================================
# Step 1: Clear existing data
# ============================================================

def clear_tables():
    """Truncate tables for a clean load."""
    print("[Step 1] Clearing existing data...")
    conn = get_conn(SQL_DEST_DB)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions")
    cursor.execute("DELETE FROM products")
    cursor.execute("DELETE FROM properties")
    # Reset identity on transactions
    try:
        cursor.execute("DBCC CHECKIDENT('transactions', RESEED, 0)")
    except Exception:
        pass
    conn.commit()
    conn.close()
    print("  Tables cleared.")


# ============================================================
# Step 2: Load Properties
# ============================================================

def load_properties():
    """Load property data from HotelDW — no PII."""
    print("[Step 2] Loading properties...")
    dw = get_conn(SQL_DW_DB)
    rows = dw.cursor().execute("""
        SELECT DISTINCT dp.property_id, dp.name, dp.city, dp.state, dp.zip
        FROM dim_property dp
        JOIN dim_shop ds ON dp.property_id = ds.located_at
        ORDER BY dp.property_id
    """).fetchall()
    dw.close()

    dest = get_conn(SQL_DEST_DB)
    cursor = dest.cursor()
    for r in rows:
        cursor.execute(
            "INSERT INTO properties (property_id, name, city, state, zip) VALUES (?,?,?,?,?)",
            r[0], r[1], r[2], r[3], r[4]
        )
    dest.commit()
    dest.close()
    print(f"  Loaded {len(rows)} properties")
    return len(rows)


# ============================================================
# Step 3: Load Products
# ============================================================

def load_products():
    """Load product data from HotelDW — no PII."""
    print("[Step 3] Loading products...")
    dw = get_conn(SQL_DW_DB)
    rows = dw.cursor().execute("""
        SELECT product_id, name, price, category
        FROM dim_gift_product
        ORDER BY product_id
    """).fetchall()
    dw.close()

    dest = get_conn(SQL_DEST_DB)
    cursor = dest.cursor()
    for r in rows:
        cursor.execute(
            "INSERT INTO products (product_id, name, price, category) VALUES (?,?,?,?)",
            r[0], r[1], r[2], r[3]
        )
    dest.commit()
    dest.close()
    print(f"  Loaded {len(rows)} products")
    return len(rows)


# ============================================================
# Step 4: Load Transactions (PII-free, re-sequenced)
# ============================================================

def load_transactions():
    """
    Load gift shop transaction line items from HotelDW.
    - NO customer IDs or names
    - Transaction IDs are re-sequenced via IDENTITY
    """
    print("[Step 4] Loading transactions (PII-free, re-sequenced IDs)...")

    dw = get_conn(SQL_DW_DB)
    cursor_dw = dw.cursor()

    total = cursor_dw.execute("SELECT COUNT(*) FROM fact_gift_shop_sales").fetchone()[0]
    print(f"  Source rows: {total:,}")

    # Simple JOINs only — no cross-database subqueries, no ORDER BY
    cursor_dw.execute("""
        SELECT
            dd.full_date AS transaction_date,
            dp.property_id,
            dgp.product_id,
            gs.quantity,
            gs.sale_amount,
            gs.payment_method,
            gs.payment_status
        FROM fact_gift_shop_sales gs
        JOIN dim_date dd ON gs.date_key = dd.date_key
        JOIN dim_property dp ON gs.property_key = dp.property_key
        JOIN dim_gift_product dgp ON gs.gift_product_key = dgp.gift_product_key
    """)

    insert_sql = (
        "INSERT INTO transactions "
        "(transaction_date, property_id, product_id, quantity, sale_amount, payment_method, payment_status) "
        "VALUES (?,?,?,?,?,?,?)"
    )

    loaded = 0
    skipped = 0
    start = time.time()

    # Load valid property_ids and product_ids for FK validation
    dest_conn = get_conn(SQL_DEST_DB)
    valid_props = set(r[0] for r in dest_conn.cursor().execute("SELECT property_id FROM properties").fetchall())
    valid_prods = set(r[0] for r in dest_conn.cursor().execute("SELECT product_id FROM products").fetchall())
    dest_conn.close()

    while True:
        rows = cursor_dw.fetchmany(BATCH_SIZE)
        if not rows:
            break

        # Filter rows to only those matching loaded properties/products (FK safety)
        batch = []
        for r in rows:
            if r[1] in valid_props and r[2] in valid_prods:
                batch.append((r[0], r[1], r[2], r[3], r[4], r[5], r[6]))
            else:
                skipped += 1

        if batch:
            dest = get_conn(SQL_DEST_DB)
            dest_cursor = dest.cursor()
            dest_cursor.fast_executemany = True
            dest_cursor.executemany(insert_sql, batch)
            dest.commit()
            dest.close()

        loaded += len(batch)
        elapsed = time.time() - start
        rate = loaded / elapsed if elapsed > 0 else 0
        print(f"    ... {loaded:,} / {total:,} rows ({rate:.0f} rows/sec)")

    dw.close()
    elapsed = time.time() - start
    print(f"  Loaded {loaded:,} transactions in {elapsed:.1f}s (skipped {skipped:,} FK mismatches)")
    return loaded


# ============================================================
# Step 5: Verify - No PII
# ============================================================

def verify_no_pii():
    """Verify the dataset contains no PII columns."""
    print("[Step 5] Verifying no PII...")
    conn = get_conn(SQL_DEST_DB)
    cursor = conn.cursor()

    pii_keywords = ['customer', 'first_name', 'last_name', 'email', 'phone',
                    'address', 'ssn', 'social', 'card_number', 'card_stub']
    issues = []

    cursor.execute("""
        SELECT TABLE_NAME, COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_CATALOG = ?
    """, SQL_DEST_DB)

    for row in cursor.fetchall():
        col_lower = row[1].lower()
        for kw in pii_keywords:
            if kw in col_lower:
                issues.append(f"  WARNING: PII suspect: {row[0]}.{row[1]} (matched '{kw}')")

    if issues:
        for i in issues:
            print(i)
    else:
        print("  No PII columns detected")

    for table in ['properties', 'products', 'transactions']:
        cnt = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {cnt:,} rows")

    conn.close()
    return len(issues) == 0


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 60)
    print("Gift Shop Open Dataset ETL — Data Load")
    print("=" * 60)
    print(f"  Source: {SQL_SERVER}/{SQL_DW_DB}")
    print(f"  Target: {SQL_SERVER}/{SQL_DEST_DB}")
    print("=" * 60)

    overall_start = time.time()

    clear_tables()
    n_props = load_properties()
    n_prods = load_products()
    n_txns = load_transactions()
    pii_ok = verify_no_pii()

    elapsed = time.time() - overall_start
    print(f"\n{'=' * 60}")
    print(f"ETL COMPLETE in {elapsed:.1f}s")
    print(f"  Properties:   {n_props:,}")
    print(f"  Products:     {n_prods:,}")
    print(f"  Transactions: {n_txns:,}")
    print(f"  PII Check:    {'PASSED' if pii_ok else 'FAILED'}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
