"""
ETL Pipeline: Cross-Source Star Schema (Hotel + Gift Shop → HotelDW)
=====================================================================
Extracts data from BOTH source systems:
  - SQL Server (Hotel) - property data
  - MongoDB (hotel) - gift shop shops, products, transactions

Transforms and loads into the cross-source star schema in HotelDW:
  - dim_shop, dim_gift_product (new dimensions)
  - fact_gift_shop_sales (new fact table)
  - Reuses shared dim_date and dim_property

Connection Strategy:
  Opens a fresh SQL Server connection for each batch insert, then closes
  it immediately after. This prevents connection timeout issues on the
  remote server.

Prerequisites:
  - Run CrossSource-StarSchema-DDL.sql first to create tables
  - Run Populate-HotelDW.sql first to populate dim_property and dim_date

Usage:
    python etl_cross_source.py
"""

import pyodbc
import pymongo
import sys
import time
from datetime import datetime
from decimal import Decimal


# ============================================================
# Connection Configuration
# ============================================================

SQL_SERVER = "cis444.campus-quest.com,25000"
SQL_DW_DB = "HotelDW"
SQL_USER = "sa"
SQL_PASSWORD = "Academic2026U05!"

MONGO_URI = "mongodb://admin:Academic2026U05!@cis444.campus-quest.com:25010/?tlsInsecure=true&authSource=admin"
MONGO_DATABASE = "hotel"  # Gift shop database

BATCH_SIZE = 10000  # Larger batches with fast_executemany


def get_sql_conn():
    """Get a fresh SQL Server connection (short-lived, per-batch)."""
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SQL_SERVER};"
        f"DATABASE={SQL_DW_DB};"
        f"UID={SQL_USER};"
        f"PWD={SQL_PASSWORD};"
        f"TrustServerCertificate=yes;"
        f"Connection Timeout=30;"
    )


def run_sql(sql, params=None, fetch=False):
    """Open connection, run a single SQL statement, close connection."""
    conn = get_sql_conn()
    cursor = conn.cursor()
    if params:
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)
    result = None
    if fetch:
        result = cursor.fetchall()
    conn.commit()
    conn.close()
    return result


def run_sql_batch(sql, batch_rows):
    """Open connection, fast executemany, commit, close."""
    conn = get_sql_conn()
    cursor = conn.cursor()
    cursor.fast_executemany = True  # ODBC array insert — 100x faster
    cursor.executemany(sql, batch_rows)
    conn.commit()
    conn.close()


def connect_mongo():
    """Connect to MongoDB."""
    print(f"[MongoDB] Connecting to {MONGO_DATABASE}...")
    client = pymongo.MongoClient(MONGO_URI)
    client.admin.command("ping")
    db = client[MONGO_DATABASE]
    print(f"[MongoDB] Connected.")
    return client, db


# ============================================================
# EXTRACT
# ============================================================

def get_property_mapping():
    """Get existing dim_property mapping {property_id: property_key}."""
    rows = run_sql("SELECT property_id, property_key FROM dim_property", fetch=True)
    mapping = {r[0]: r[1] for r in rows}
    print(f"  [DW] dim_property mapping: {len(mapping):,} entries")
    return mapping


def extract_shops(mongo_db):
    shops = list(mongo_db.shops.find({}))
    print(f"  [Extract] shops: {len(shops):,} documents")
    return shops


def extract_products(mongo_db):
    products = list(mongo_db.products.find({}))
    print(f"  [Extract] products: {len(products):,} documents")
    return products


# ============================================================
# TRUNCATE
# ============================================================

def truncate_cross_source():
    """Clear cross-source tables for full refresh."""
    conn = get_sql_conn()
    cursor = conn.cursor()
    for table in ["fact_gift_shop_sales"]:
        try:
            cursor.execute(f"DELETE FROM {table}")
            print(f"  [Truncate] {table} cleared")
        except Exception as e:
            print(f"  [Truncate] {table} - {e}")
    for table in ["dim_shop", "dim_gift_product"]:
        try:
            cursor.execute(f"DELETE FROM {table}")
            cursor.execute(f"DBCC CHECKIDENT('{table}', RESEED, 0)")
            print(f"  [Truncate] {table} cleared + identity reset")
        except Exception as e:
            print(f"  [Truncate] {table} - {e}")
    conn.commit()
    conn.close()


# ============================================================
# LOAD: Dimension tables (small — single connection is fine)
# ============================================================

def load_dim_shop(shops, prop_map):
    """Load dim_shop and return {shop_id: shop_key} mapping."""
    conn = get_sql_conn()
    cursor = conn.cursor()
    mapping = {}

    for shop in shops:
        shop_id = shop.get("id")
        name = shop.get("name", "Unknown")
        city = shop.get("city", "")
        state = shop.get("state", "")
        zip_code = shop.get("zip", "")
        located_at = shop.get("located_at")
        date_opened = shop.get("date_opened")

        cursor.execute(
            "INSERT INTO dim_shop (shop_id, name, city, state, zip, located_at, date_opened) "
            "OUTPUT INSERTED.shop_key "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            shop_id, name, city, state, zip_code, located_at, date_opened
        )
        key = cursor.fetchone()[0]
        mapping[shop_id] = key

    conn.commit()
    conn.close()
    print(f"  [Load] dim_shop: {len(mapping):,} rows inserted")
    return mapping


def load_dim_gift_product(products):
    """Load dim_gift_product and return {product_id: gift_product_key} mapping."""
    conn = get_sql_conn()
    cursor = conn.cursor()
    mapping = {}

    for prod in products:
        prod_id = prod.get("id")
        name = prod.get("name", "Unknown")
        price = prod.get("price", 0.0)
        category = prod.get("category", "Uncategorized")
        if isinstance(price, Decimal):
            price = float(price)

        cursor.execute(
            "INSERT INTO dim_gift_product (product_id, name, price, category) "
            "OUTPUT INSERTED.gift_product_key "
            "VALUES (?, ?, ?, ?)",
            prod_id, name, price, category
        )
        key = cursor.fetchone()[0]
        mapping[prod_id] = key

    conn.commit()
    conn.close()
    print(f"  [Load] dim_gift_product: {len(mapping):,} rows inserted")
    return mapping


# ============================================================
# LOAD: Fact table (open/close per batch)
# ============================================================

def make_date_key(dt):
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return int(dt.strftime("%Y%m%d"))
    return None


def load_fact_gift_shop_sales(mongo_db, shops_raw, products_raw,
                               shop_map, prod_map, prop_map):
    """
    Load fact_gift_shop_sales by flattening MongoDB transactions.line_items[].
    Opens a fresh SQL connection for each batch to avoid timeouts.
    """
    print("  [Load] fact_gift_shop_sales: Starting...")

    # Build shop_id → property_key mapping via located_at
    shop_to_property = {}
    for shop in shops_raw:
        shop_id = shop.get("id")
        located_at = shop.get("located_at")
        if located_at and located_at in prop_map:
            shop_to_property[shop_id] = prop_map[located_at]

    # Build product name → gift_product_key mapping
    prod_name_to_key = {}
    for prod in products_raw:
        name = prod.get("name", "")
        prod_id = prod.get("id")
        if prod_id in prod_map:
            prod_name_to_key[name] = prod_map[prod_id]

    insert_sql = (
        "INSERT INTO fact_gift_shop_sales "
        "(date_key, property_key, shop_key, gift_product_key, transaction_id, "
        "sale_amount, quantity, payment_method, payment_status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )

    # Stream transactions from MongoDB
    txn_count = mongo_db.transactions.count_documents({})
    print(f"  [Extract] transactions: {txn_count:,} documents (streaming)")
    txn_cursor = mongo_db.transactions.find({})

    batch = []
    total_inserted = 0
    skipped = 0
    start_time = time.time()

    for txn in txn_cursor:
        txn_id = txn.get("id", 0)
        store_id = txn.get("store_id")
        timestamp = txn.get("timestamp")
        payment = txn.get("payment", {})
        pay_method = payment.get("method", "Unknown")
        pay_status = payment.get("status", "Unknown")
        line_items = txn.get("line_items", [])

        date_key = make_date_key(timestamp)
        s_key = shop_map.get(store_id)
        p_key = shop_to_property.get(store_id)

        if None in (date_key, s_key, p_key):
            skipped += 1
            continue

        for item in line_items:
            desc = item.get("description", "")
            amount = item.get("amount_per", 0.0)
            qty = item.get("quantity", 1)

            gp_key = prod_name_to_key.get(desc)
            if gp_key is None:
                skipped += 1
                continue

            if isinstance(amount, Decimal):
                amount = float(amount)

            batch.append((date_key, p_key, s_key, gp_key, txn_id,
                          amount, qty, pay_method, pay_status))

            if len(batch) >= BATCH_SIZE:
                # Open connection, push batch, close connection
                run_sql_batch(insert_sql, batch)
                total_inserted += len(batch)
                elapsed = time.time() - start_time
                rate = total_inserted / elapsed if elapsed > 0 else 0
                print(f"    ... {total_inserted:,} gift sales rows ({rate:.0f} rows/sec)")
                batch = []

    # Final batch
    if batch:
        run_sql_batch(insert_sql, batch)
        total_inserted += len(batch)

    elapsed = time.time() - start_time
    print(f"  [DONE] fact_gift_shop_sales: {total_inserted:,} rows in {elapsed:.1f}s (skipped {skipped:,})")
    return total_inserted


# ============================================================
# VERIFICATION
# ============================================================

def verify_cross_source():
    rows = run_sql("""
        SELECT 'dim_shop' AS t, COUNT(*) AS c FROM dim_shop
        UNION ALL SELECT 'dim_gift_product', COUNT(*) FROM dim_gift_product
        UNION ALL SELECT 'fact_gift_shop_sales', COUNT(*) FROM fact_gift_shop_sales
    """, fetch=True)

    print("\n" + "=" * 60)
    print("VERIFICATION: Cross-Source Tables")
    print("=" * 60)
    for r in rows:
        status = "OK" if r[1] > 0 else "EMPTY"
        print(f"  {status:5s} | {r[0]:25s} | {r[1]:>12,} rows")


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("ETL Pipeline: Cross-Source (Hotel + Gift Shop → HotelDW)")
    print("=" * 60)
    print(f"  SQL Server DW: {SQL_SERVER}/{SQL_DW_DB}")
    print(f"  MongoDB Source: {MONGO_DATABASE}")
    print(f"  Strategy: Full Refresh, connection-per-batch")
    print(f"  Batch Size: {BATCH_SIZE:,}")
    print("=" * 60)

    overall_start = time.time()

    # Step 1: Get existing dim_property mapping
    print("\n--- Step 1: Load existing DW mappings ---")
    prop_map = get_property_mapping()
    if not prop_map:
        print("  [ERROR] dim_property is empty! Run Populate-HotelDW.sql first.")
        sys.exit(1)

    # Step 2: Connect to MongoDB
    print("\n--- Step 2: Connect to MongoDB ---")
    mongo_client, mongo_db = connect_mongo()

    try:
        # Step 3: Truncate cross-source tables
        print("\n--- Step 3: Clear cross-source tables ---")
        truncate_cross_source()

        # Step 4: Extract MongoDB data
        print("\n--- Step 4: Extract gift shop data from MongoDB ---")
        shops_raw = extract_shops(mongo_db)
        products_raw = extract_products(mongo_db)

        # Step 5: Load new dimensions
        print("\n--- Step 5: Load new dimension tables ---")
        shop_map = load_dim_shop(shops_raw, prop_map)
        prod_map = load_dim_gift_product(products_raw)

        # Step 6: Load fact table (connection-per-batch)
        print("\n--- Step 6: Load fact_gift_shop_sales ---")
        sales_count = load_fact_gift_shop_sales(
            mongo_db, shops_raw, products_raw,
            shop_map, prod_map, prop_map
        )

        # Step 7: Verify
        verify_cross_source()

        overall_elapsed = time.time() - overall_start
        print(f"\n{'=' * 60}")
        print(f"CROSS-SOURCE ETL COMPLETE in {overall_elapsed:.1f}s")
        print(f"  Dimensions: {len(shop_map):,} shops, {len(prod_map):,} gift products")
        print(f"  Facts: {sales_count:,} gift shop sale rows")
        print(f"{'=' * 60}")

    finally:
        mongo_client.close()
        print("\nConnections closed.")


if __name__ == "__main__":
    main()
