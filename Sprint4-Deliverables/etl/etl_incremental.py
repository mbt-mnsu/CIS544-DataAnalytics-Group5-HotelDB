"""
Sprint 4 - Incremental ETL Pipeline
=====================================

This pipeline handles ALL star schemas:
  Phase 1 (existing): fact_revenue, fact_checkin, fact_gift_shop_sales + dimensions
  Phase 2 (new):      fact_payroll, fact_property_amenity + new dimensions

Incremental Strategy:
  - Uses_ETLMetadata table to track last load state per source->target pair
  - For date-stamped tables (transact, event, payroll, mongo transactions):
    loads only records with dates AFTER the last_load_max_date
  - For reference/dimension tables (customer, employee, amenity, property_amenity):
    loads only records with IDs AFTER the last_load_max_id
  - For dim_date: extends range if new dates are discovered

Connection Strategy:
  Opens a fresh SQL Server connection for each operation to prevent
  timeout issues on the remote server.

Usage:
    python etl_incremental.py              # Incremental (default)
    python etl_incremental.py --full       # Full refresh
"""

import pyodbc
import pymongo
import sys
import time
from datetime import datetime, date, timedelta
from decimal import Decimal


# ============================================================
# Connection Configuration
# ============================================================

SQL_SERVER = "cis444.campus-quest.com,25000"
SQL_SOURCE_DB = "Hotel"
SQL_DW_DB = "HotelDW"
SQL_USER = "sa"
SQL_PASSWORD = "Academic2026U05!"

MONGO_URI = "mongodb://admin:Academic2026U05!@cis444.campus-quest.com:25010/?tlsInsecure=true&authSource=admin"
MONGO_DATABASE = "hotel"

BATCH_SIZE = 100000


def get_source_conn():
    """Get a fresh connection to the source Hotel database."""
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SQL_SERVER};DATABASE={SQL_SOURCE_DB};UID={SQL_USER};PWD={SQL_PASSWORD};"
        f"TrustServerCertificate=yes;Connection Timeout=30;"
    )


def get_dw_conn():
    """Get a fresh connection to the HotelDW data warehouse."""
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SQL_SERVER};DATABASE={SQL_DW_DB};UID={SQL_USER};PWD={SQL_PASSWORD};"
        f"TrustServerCertificate=yes;Connection Timeout=30;"
    )


def run_dw(sql, params=None, fetch=False):
    """Run a SQL statement on HotelDW with a fresh connection."""
    conn = get_dw_conn()
    cursor = conn.cursor()
    if params:
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)
    result = cursor.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return result


def run_dw_batch(sql, batch_rows):
    """Batch insert into HotelDW using fast_executemany."""
    if not batch_rows:
        return
    conn = get_dw_conn()
    cursor = conn.cursor()
    cursor.fast_executemany = True
    cursor.executemany(sql, batch_rows)
    conn.commit()
    conn.close()


def run_source(sql, params=None, fetch=True):
    """Run a SQL statement on the source Hotel database."""
    conn = get_source_conn()
    cursor = conn.cursor()
    if params:
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)
    result = cursor.fetchall() if fetch else None
    conn.close()
    return result


def connect_mongo():
    """Connect to MongoDB."""
    client = pymongo.MongoClient(MONGO_URI)
    client.admin.command("ping")
    db = client[MONGO_DATABASE]
    return client, db


# ============================================================
# ETL METADATA
# ============================================================

def ensure_metadata_table():
    """Create __ETLMetadata if it doesn't exist."""
    run_dw("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = '__ETLMetadata')
        CREATE TABLE __ETLMetadata (
            id                  INT IDENTITY(1,1) PRIMARY KEY,
            source_table        VARCHAR(100)    NOT NULL,
            target_table        VARCHAR(100)    NOT NULL,
            last_load_date      DATETIME        NOT NULL,
            last_load_max_id    INT             NULL,
            last_load_max_date  DATETIME        NULL,
            last_load_rows      INT             NOT NULL DEFAULT 0,
            total_rows_loaded   BIGINT          NOT NULL DEFAULT 0,
            status              VARCHAR(20)     NOT NULL DEFAULT 'success',
            notes               NVARCHAR(500)   NULL,
            CONSTRAINT UQ_etl_source_target UNIQUE (source_table, target_table)
        )
    """)


def get_metadata(source_table, target_table):
    """Get the last load metadata for a source→target pair."""
    rows = run_dw(
        "SELECT last_load_max_id, last_load_max_date, last_load_rows, total_rows_loaded "
        "FROM __ETLMetadata WHERE source_table = ? AND target_table = ?",
        (source_table, target_table), fetch=True
    )
    if rows:
        return {
            'max_id': rows[0][0],
            'max_date': rows[0][1],
            'rows': rows[0][2],
            'total': rows[0][3]
        }
    return None


def update_metadata(source_table, target_table, max_id=None, max_date=None, rows_loaded=0):
    """Upsert the ETL metadata after a successful load."""
    existing = get_metadata(source_table, target_table)
    now = datetime.now()

    if existing:
        run_dw(
            "UPDATE __ETLMetadata SET last_load_date = ?, last_load_max_id = ?, "
            "last_load_max_date = ?, last_load_rows = ?, "
            "total_rows_loaded = total_rows_loaded + ?, status = 'success' "
            "WHERE source_table = ? AND target_table = ?",
            (now, max_id, max_date, rows_loaded, rows_loaded, source_table, target_table)
        )
    else:
        run_dw(
            "INSERT INTO __ETLMetadata (source_table, target_table, last_load_date, "
            "last_load_max_id, last_load_max_date, last_load_rows, total_rows_loaded, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'success')",
            (source_table, target_table, now, max_id, max_date, rows_loaded, rows_loaded)
        )


# ============================================================
# DIMENSION LOADING
# ============================================================

def load_dim_date_incremental():
    """Extend dim_date if the source data has dates beyond current range."""
    print("\n--- Loading dim_date (extend if needed) ---")
    start = time.time()

    # Get current max date in dim_date
    rows = run_dw("SELECT MAX(full_date) FROM dim_date", fetch=True)
    current_max = rows[0][0] if rows and rows[0][0] else date(2019, 12, 31)

    # Target end: 2030-12-31 (generous buffer)
    target_end = date(2030, 12, 31)

    if current_max >= target_end:
        print(f"  dim_date already covers through {current_max}, skipping")
        return

    # Generate missing dates
    next_date = current_max + timedelta(days=1)
    batch = []
    while next_date <= target_end:
        dow = next_date.strftime('%A')
        is_weekend = 1 if next_date.weekday() in (5, 6) else 0
        batch.append((
            int(next_date.strftime('%Y%m%d')),
            next_date,
            dow,
            next_date.day,
            next_date.month,
            next_date.strftime('%B'),
            (next_date.month - 1) // 3 + 1,
            next_date.year,
            is_weekend
        ))
        next_date += timedelta(days=1)

    if batch:
        run_dw_batch(
            "INSERT INTO dim_date (date_key, full_date, day_of_week, day_of_month, "
            "month_num, month_name, quarter, year, is_weekend) VALUES (?,?,?,?,?,?,?,?,?)",
            batch
        )
        print(f"  Extended dim_date with {len(batch)} new dates (through {target_end})")
    else:
        print(f"  dim_date already up to date")

    elapsed = time.time() - start
    print(f"  [{elapsed:.1f}s]")


def load_dim_property(is_full):
    """Load dim_property using server-side INSERT...SELECT (same SQL Server instance)."""
    print("\n--- Loading dim_property (server-side) ---")
    start = time.time()
    meta = get_metadata('Hotel.dbo.property', 'dim_property')

    if is_full:
        where_clause = ""
    elif meta and meta['max_id'] is not None:
        where_clause = f"WHERE id > {meta['max_id']}"
    else:
        where_clause = ""

    conn = get_dw_conn()
    cursor = conn.cursor()
    cursor.execute(f"""
        INSERT INTO dim_property (property_id, name, street_address, city, state, zip)
        SELECT id, name, street_address, city, state, zip
        FROM Hotel.dbo.property
        {where_clause}
        ORDER BY id
    """)
    row_count = cursor.rowcount
    conn.commit()
    conn.close()

    if row_count > 0:
        # Get max ID for metadata
        max_id_row = run_dw("SELECT MAX(property_id) FROM dim_property", fetch=True)
        max_id = max_id_row[0][0]
        update_metadata('Hotel.dbo.property', 'dim_property', max_id=max_id, rows_loaded=row_count)
        print(f"  Loaded {row_count} properties (max_id={max_id}) [{time.time()-start:.1f}s]")
    else:
        print(f"  No new properties to load [{time.time()-start:.1f}s]")

    # Return full mapping
    mapping_rows = run_dw("SELECT property_id, property_key FROM dim_property", fetch=True)
    return {r[0]: r[1] for r in mapping_rows}


def load_dim_customer(is_full):
    """Load dim_customer using server-side INSERT...SELECT (same SQL Server instance)."""
    print("\n--- Loading dim_customer (server-side) ---")
    start = time.time()
    meta = get_metadata('Hotel.dbo.customer', 'dim_customer')

    if is_full:
        where_clause = ""
    elif meta and meta['max_id'] is not None:
        where_clause = f"WHERE id > {meta['max_id']}"
    else:
        where_clause = ""

    conn = get_dw_conn()
    cursor = conn.cursor()
    cursor.execute(f"""
        INSERT INTO dim_customer (customer_id, first_name, last_name, email, city, state, zip)
        SELECT id, first_name, last_name, email, city, state, zip
        FROM Hotel.dbo.customer
        {where_clause}
        ORDER BY id
    """)
    row_count = cursor.rowcount
    conn.commit()
    conn.close()

    if row_count > 0:
        max_id_row = run_dw("SELECT MAX(customer_id) FROM dim_customer", fetch=True)
        max_id = max_id_row[0][0]
        update_metadata('Hotel.dbo.customer', 'dim_customer', max_id=max_id, rows_loaded=row_count)
        print(f"  Loaded {row_count:,} customers (max_id={max_id}) [{time.time()-start:.1f}s]")
    else:
        print(f"  No new customers to load [{time.time()-start:.1f}s]")

    mapping_rows = run_dw("SELECT customer_id, customer_key FROM dim_customer", fetch=True)
    return {r[0]: r[1] for r in mapping_rows}


def load_dim_product(is_full):
    """Load dim_product using server-side INSERT...SELECT."""
    print("\n--- Loading dim_product (server-side) ---")
    start = time.time()

    # Insert only new descriptions not already in dim_product
    conn = get_dw_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO dim_product (description, category)
        SELECT DISTINCT tl.description, NULL
        FROM Hotel.dbo.transaction_line tl
        WHERE NOT EXISTS (
            SELECT 1 FROM dim_product dp WHERE dp.description = tl.description
        )
        ORDER BY tl.description
    """)
    row_count = cursor.rowcount
    conn.commit()
    conn.close()

    if row_count > 0:
        print(f"  Loaded {row_count} new product descriptions")
    else:
        print("  No new product descriptions")

    update_metadata('Hotel.dbo.transaction_line', 'dim_product', rows_loaded=row_count)

    mapping_rows = run_dw("SELECT description, product_key FROM dim_product", fetch=True)
    elapsed = time.time() - start
    print(f"  [{elapsed:.1f}s]")
    return {r[0]: r[1] for r in mapping_rows}


def load_dim_employee(is_full):
    """Load dim_employee using server-side INSERT...SELECT (same SQL Server instance)."""
    print("\n--- Loading dim_employee (server-side) ---")
    start = time.time()
    meta = get_metadata('Hotel.dbo.employee', 'dim_employee')

    if is_full:
        where_clause = ""
    elif meta and meta['max_id'] is not None:
        where_clause = f"WHERE id > {meta['max_id']}"
    else:
        where_clause = ""

    conn = get_dw_conn()
    cursor = conn.cursor()
    cursor.execute(f"""
        INSERT INTO dim_employee (employee_id, first_name, last_name, email, job_title,
                                  employment_type, base_salary, property_id)
        SELECT id, first_name, last_name, email, job_title, employment_type, base_salary, property_id
        FROM Hotel.dbo.employee
        {where_clause}
        ORDER BY id
    """)
    row_count = cursor.rowcount
    conn.commit()
    conn.close()

    if row_count > 0:
        max_id_row = run_dw("SELECT MAX(employee_id) FROM dim_employee", fetch=True)
        max_id = max_id_row[0][0]
        update_metadata('Hotel.dbo.employee', 'dim_employee', max_id=max_id, rows_loaded=row_count)
        print(f"  Loaded {row_count:,} employees (max_id={max_id}) [{time.time()-start:.1f}s]")
    else:
        print(f"  No new employees to load [{time.time()-start:.1f}s]")

    mapping_rows = run_dw("SELECT employee_id, employee_key FROM dim_employee", fetch=True)
    return {r[0]: r[1] for r in mapping_rows}


def load_dim_amenity(is_full):
    """Load dim_amenity using server-side INSERT...SELECT."""
    print("\n--- Loading dim_amenity (server-side) ---")
    start = time.time()

    conn = get_dw_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO dim_amenity (amenity_id, amenity_name, amenity_key_code, group_key, group_display_name)
        SELECT a.id, a.display_name, a.[key], a.group_key, a.group_display_name
        FROM Hotel.dbo.amenity a
        WHERE NOT EXISTS (
            SELECT 1 FROM dim_amenity da WHERE da.amenity_id = a.id
        )
        ORDER BY a.id
    """)
    row_count = cursor.rowcount
    conn.commit()
    conn.close()

    if row_count > 0:
        print(f"  Loaded {row_count} amenities")
    else:
        print("  No new amenities to load")

    update_metadata('Hotel.dbo.amenity', 'dim_amenity', rows_loaded=row_count)

    mapping_rows = run_dw("SELECT amenity_id, amenity_key FROM dim_amenity", fetch=True)
    elapsed = time.time() - start
    print(f"  [{elapsed:.1f}s]")
    return {r[0]: r[1] for r in mapping_rows}


# ============================================================
# GIFT SHOP DIMENSIONS (from MongoDB)
# ============================================================

def load_dim_shop(mongo_db, prop_map, is_full):
    """Load dim_shop from MongoDB shops collection."""
    print("\n--- Loading dim_shop (MongoDB) ---")
    start = time.time()

    existing = run_dw("SELECT shop_id FROM dim_shop", fetch=True)
    existing_ids = {r[0] for r in existing}

    shops = list(mongo_db.shops.find({}))
    new_shops = [s for s in shops if s.get('id') not in existing_ids]

    conn = get_dw_conn()
    cursor = conn.cursor()
    mapping = {}

    for shop in new_shops:
        shop_id = shop.get('id')
        cursor.execute(
            "INSERT INTO dim_shop (shop_id, name, city, state, zip, located_at, date_opened) "
            "OUTPUT INSERTED.shop_key VALUES (?,?,?,?,?,?,?)",
            shop_id, shop.get('name', 'Unknown'), shop.get('city', ''),
            shop.get('state', ''), shop.get('zip', ''),
            shop.get('located_at'), shop.get('date_opened')
        )
        key = cursor.fetchone()[0]
        mapping[shop_id] = key

    conn.commit()
    conn.close()

    if new_shops:
        print(f"  Loaded {len(new_shops)} new shops")

    # Get full mapping
    all_rows = run_dw("SELECT shop_id, shop_key FROM dim_shop", fetch=True)
    full_mapping = {r[0]: r[1] for r in all_rows}

    update_metadata('mongo.shops', 'dim_shop', rows_loaded=len(new_shops))
    elapsed = time.time() - start
    print(f"  Total dim_shop: {len(full_mapping)} [{elapsed:.1f}s]")
    return full_mapping, shops


def load_dim_gift_product(mongo_db, is_full):
    """Load dim_gift_product from MongoDB products collection."""
    print("\n--- Loading dim_gift_product (MongoDB) ---")
    start = time.time()

    existing = run_dw("SELECT product_id FROM dim_gift_product", fetch=True)
    existing_ids = {r[0] for r in existing}

    products = list(mongo_db.products.find({}))
    new_prods = [p for p in products if p.get('id') not in existing_ids]

    conn = get_dw_conn()
    cursor = conn.cursor()

    for prod in new_prods:
        price = prod.get('price', 0.0)
        if isinstance(price, Decimal):
            price = float(price)
        cursor.execute(
            "INSERT INTO dim_gift_product (product_id, name, price, category) "
            "OUTPUT INSERTED.gift_product_key VALUES (?,?,?,?)",
            prod.get('id'), prod.get('name', 'Unknown'), price, prod.get('category', 'Uncategorized')
        )
        cursor.fetchone()

    conn.commit()
    conn.close()

    if new_prods:
        print(f"  Loaded {len(new_prods)} new gift products")

    all_rows = run_dw("SELECT product_id, gift_product_key FROM dim_gift_product", fetch=True)
    full_mapping = {r[0]: r[1] for r in all_rows}

    update_metadata('mongo.products', 'dim_gift_product', rows_loaded=len(new_prods))
    elapsed = time.time() - start
    print(f"  Total dim_gift_product: {len(full_mapping)} [{elapsed:.1f}s]")
    return full_mapping, products


# ============================================================
# FACT TABLE LOADING
# ============================================================

def load_fact_revenue(is_full, prop_map, cust_map, prod_map):
    """Load fact_revenue using server-side INSERT...SELECT with JOINs to dimension tables."""
    print("\n--- Loading fact_revenue (server-side) ---")
    start = time.time()
    meta = get_metadata('Hotel.dbo.transact', 'fact_revenue')

    if is_full:
        where_clause = ""
    elif meta and meta['max_date'] is not None:
        where_clause = f"AND t.transaction_date > '{meta['max_date'].strftime('%Y-%m-%d %H:%M:%S')}'"
    else:
        where_clause = ""

    conn = get_dw_conn()
    cursor = conn.cursor()
    cursor.execute(f"""
        INSERT INTO fact_revenue (date_key, property_key, customer_key, product_key,
                                  transaction_id, amount_per, quantity, payment_method)
        SELECT
            CAST(FORMAT(t.transaction_date, 'yyyyMMdd') AS INT) AS date_key,
            dp.property_key,
            dc.customer_key,
            dpr.product_key,
            t.id AS transaction_id,
            tl.amount_per,
            tl.quantity,
            t.payment_method
        FROM Hotel.dbo.transact t
        JOIN Hotel.dbo.transaction_line tl ON tl.transaction_id = t.id
        JOIN dim_property dp ON dp.property_id = t.hotel_id
        JOIN dim_customer dc ON dc.customer_id = t.customer_id
        JOIN dim_product dpr ON dpr.description = tl.description
        WHERE 1=1 {where_clause}
    """)
    row_count = cursor.rowcount
    conn.commit()
    conn.close()

    # Get max date for metadata
    max_date = None
    if row_count > 0:
        max_date_row = run_dw(
            "SELECT MAX(dd.full_date) FROM fact_revenue fr JOIN dim_date dd ON fr.date_key = dd.date_key",
            fetch=True
        )
        if max_date_row and max_date_row[0][0]:
            max_date = datetime.combine(max_date_row[0][0], datetime.min.time())

    update_metadata('Hotel.dbo.transact', 'fact_revenue', max_date=max_date, rows_loaded=row_count)
    elapsed = time.time() - start
    print(f"  [DONE] fact_revenue: {row_count:,} rows in {elapsed:.1f}s")
    return row_count


def load_fact_checkin(is_full, prop_map, cust_map):
    """Load fact_checkin using server-side INSERT...SELECT with JOINs to dimension tables."""
    print("\n--- Loading fact_checkin (server-side) ---")
    start = time.time()
    meta = get_metadata('Hotel.dbo.event', 'fact_checkin')

    if is_full:
        where_clause = ""
    elif meta and meta['max_date'] is not None:
        where_clause = f"AND e.event_date > '{meta['max_date'].strftime('%Y-%m-%d')}'"
    else:
        where_clause = ""

    conn = get_dw_conn()
    cursor = conn.cursor()
    cursor.execute(f"""
        INSERT INTO fact_checkin (date_key, property_key, customer_key, event_id, event_code)
        SELECT
            CAST(FORMAT(e.event_date, 'yyyyMMdd') AS INT) AS date_key,
            dp.property_key,
            dc.customer_key,
            e.id AS event_id,
            e.event_code
        FROM Hotel.dbo.event e
        JOIN dim_property dp ON dp.property_id = e.property_id
        JOIN dim_customer dc ON dc.customer_id = e.customer_id
        WHERE e.event_code = 'checkin' {where_clause}
    """)
    row_count = cursor.rowcount
    conn.commit()
    conn.close()

    # Get max date for metadata
    max_date = None
    if row_count > 0:
        max_date_row = run_dw(
            "SELECT MAX(dd.full_date) FROM fact_checkin fc JOIN dim_date dd ON fc.date_key = dd.date_key",
            fetch=True
        )
        if max_date_row and max_date_row[0][0]:
            max_date = datetime.combine(max_date_row[0][0], datetime.min.time())

    update_metadata('Hotel.dbo.event', 'fact_checkin', max_date=max_date, rows_loaded=row_count)
    elapsed = time.time() - start
    print(f"  [DONE] fact_checkin: {row_count:,} rows in {elapsed:.1f}s")
    return row_count


def load_fact_gift_shop_sales(mongo_db, shops_raw, products_raw,
                               shop_map, prod_map, prop_map, is_full):
    """Load fact_gift_shop_sales — incremental by transaction date or full refresh."""
    print("\n--- Loading fact_gift_shop_sales ---")
    start = time.time()
    meta = get_metadata('mongo.transactions', 'fact_gift_shop_sales')

    # Build lookup maps
    shop_to_property = {}
    for shop in shops_raw:
        sid = shop.get('id')
        loc = shop.get('located_at')
        if loc and loc in prop_map:
            shop_to_property[sid] = prop_map[loc]

    prod_name_to_key = {}
    for prod in products_raw:
        name = prod.get('name', '')
        pid = prod.get('id')
        if pid in prod_map:
            prod_name_to_key[name] = prod_map[pid]

    # Build MongoDB query filter
    query_filter = {}
    if not is_full and meta and meta['max_date'] is not None:
        query_filter = {"timestamp": {"$gt": meta['max_date']}}
        print(f"  Incremental: loading transactions after {meta['max_date']}")

    txn_count = mongo_db.transactions.count_documents(query_filter)
    print(f"  [Extract] transactions to process: {txn_count:,}")
    txn_cursor = mongo_db.transactions.find(query_filter).sort("timestamp", 1)

    insert_sql = (
        "INSERT INTO fact_gift_shop_sales "
        "(date_key, property_key, shop_key, gift_product_key, transaction_id, "
        "sale_amount, quantity, payment_method, payment_status) VALUES (?,?,?,?,?,?,?,?,?)"
    )

    batch = []
    total = 0
    skipped = 0
    max_date = None

    for txn in txn_cursor:
        txn_id = txn.get('id', 0)
        store_id = txn.get('store_id')
        timestamp = txn.get('timestamp')
        payment = txn.get('payment', {})
        pay_method = payment.get('method', 'Unknown')
        pay_status = payment.get('status', 'Unknown')
        line_items = txn.get('line_items', [])

        if timestamp is None:
            skipped += 1
            continue

        date_key = int(timestamp.strftime('%Y%m%d'))
        s_key = shop_map.get(store_id)
        p_key = shop_to_property.get(store_id)

        if None in (s_key, p_key):
            skipped += 1
            continue

        if max_date is None or timestamp > max_date:
            max_date = timestamp

        for item in line_items:
            desc = item.get('description', '')
            amount = item.get('amount_per', 0.0)
            qty = item.get('quantity', 1)

            gp_key = prod_name_to_key.get(desc)
            if gp_key is None:
                skipped += 1
                continue

            if isinstance(amount, Decimal):
                amount = float(amount)

            batch.append((date_key, p_key, s_key, gp_key, txn_id, amount, qty, pay_method, pay_status))

            if len(batch) >= BATCH_SIZE:
                run_dw_batch(insert_sql, batch)
                total += len(batch)
                elapsed = time.time() - start
                rate = total / elapsed if elapsed > 0 else 0
                print(f"    ... {total:,} gift sales rows ({rate:.0f} rows/sec)")
                batch = []

    if batch:
        run_dw_batch(insert_sql, batch)
        total += len(batch)

    update_metadata('mongo.transactions', 'fact_gift_shop_sales', max_date=max_date, rows_loaded=total)
    elapsed = time.time() - start
    print(f"  [DONE] fact_gift_shop_sales: {total:,} rows in {elapsed:.1f}s (skipped {skipped:,})")
    return total


def load_fact_payroll(is_full, prop_map, emp_map):
    """Load fact_payroll using server-side INSERT...SELECT with JOINs to dimension tables."""
    print("\n--- Loading fact_payroll (server-side) ---")
    start = time.time()
    meta = get_metadata('Hotel.dbo.payroll', 'fact_payroll')

    if is_full:
        where_clause = ""
    elif meta and meta['max_date'] is not None:
        where_clause = f"AND p.pay_date > '{meta['max_date'].strftime('%Y-%m-%d')}'"
    else:
        where_clause = ""

    conn = get_dw_conn()
    cursor = conn.cursor()
    cursor.execute(f"""
        INSERT INTO fact_payroll (payroll_id, date_key, property_key, employee_key,
                                  pay_period_start, pay_period_end, hours_regular, hours_overtime,
                                  gross_pay, federal_tax, state_tax, social_security, medicare, net_pay)
        SELECT
            p.id AS payroll_id,
            CAST(FORMAT(p.pay_date, 'yyyyMMdd') AS INT) AS date_key,
            dp.property_key,
            de.employee_key,
            p.pay_period_start,
            p.pay_period_end,
            p.hours_regular,
            p.hours_overtime,
            p.gross_pay,
            p.federal_tax,
            p.state_tax,
            p.social_security,
            p.medicare,
            p.net_pay
        FROM Hotel.dbo.payroll p
        JOIN dim_property dp ON dp.property_id = p.property_id
        JOIN dim_employee de ON de.employee_id = p.employee_id
        WHERE 1=1 {where_clause}
    """)
    row_count = cursor.rowcount
    conn.commit()
    conn.close()

    # Get max date for metadata
    max_date = None
    if row_count > 0:
        max_date_row = run_dw(
            "SELECT MAX(dd.full_date) FROM fact_payroll fp JOIN dim_date dd ON fp.date_key = dd.date_key",
            fetch=True
        )
        if max_date_row and max_date_row[0][0]:
            max_date = datetime.combine(max_date_row[0][0], datetime.min.time())

    update_metadata('Hotel.dbo.payroll', 'fact_payroll', max_date=max_date, rows_loaded=row_count)
    elapsed = time.time() - start
    print(f"  [DONE] fact_payroll: {row_count:,} rows in {elapsed:.1f}s")
    return row_count


def load_fact_property_amenity(is_full, prop_map, amen_map):
    """Load fact_property_amenity using server-side INSERT...SELECT."""
    print("\n--- Loading fact_property_amenity (server-side) ---")
    start = time.time()

    conn = get_dw_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO fact_property_amenity (property_key, amenity_key)
        SELECT dp.property_key, da.amenity_key
        FROM Hotel.dbo.property_amenity pa
        JOIN dim_property dp ON dp.property_id = pa.property_id
        JOIN dim_amenity da ON da.amenity_id = pa.amenity_id
        WHERE NOT EXISTS (
            SELECT 1 FROM fact_property_amenity fpa
            WHERE fpa.property_key = dp.property_key AND fpa.amenity_key = da.amenity_key
        )
    """)
    row_count = cursor.rowcount
    conn.commit()
    conn.close()

    if row_count > 0:
        print(f"  Loaded {row_count} property-amenity assignments")
    else:
        print("  No new property-amenity assignments")

    update_metadata('Hotel.dbo.property_amenity', 'fact_property_amenity', rows_loaded=row_count)
    elapsed = time.time() - start
    print(f"  [{elapsed:.1f}s]")


# ============================================================
# VERIFICATION
# ============================================================

def verify_all():
    """Print row counts for all DW tables."""
    tables = [
        'dim_date', 'dim_property', 'dim_customer', 'dim_product',
        'dim_employee', 'dim_amenity', 'dim_shop', 'dim_gift_product',
        'fact_revenue', 'fact_checkin', 'fact_gift_shop_sales',
        'fact_payroll', 'fact_property_amenity', '__ETLMetadata'
    ]

    print("\n" + "=" * 60)
    print("VERIFICATION: All HotelDW Tables")
    print("=" * 60)

    for table in tables:
        try:
            rows = run_dw(f"SELECT COUNT(*) FROM [{table}]", fetch=True)
            count = rows[0][0]
            status = "OK" if count > 0 else "EMPTY"
            print(f"  {status:5s} | {table:30s} | {count:>12,} rows")
        except Exception as e:
            print(f"  ERROR | {table:30s} | {e}")

    # Show ETL metadata
    print("\n" + "-" * 60)
    print("ETL Metadata (Last Load Info)")
    print("-" * 60)
    try:
        meta_rows = run_dw(
            "SELECT source_table, target_table, last_load_date, last_load_rows, total_rows_loaded, status "
            "FROM __ETLMetadata ORDER BY target_table", fetch=True
        )
        for r in meta_rows:
            print(f"  {r[0]:30s} -> {r[1]:25s} | {r[4]:>10,} total | last: {r[3]:>8,} rows | {r[2]} | {r[5]}")
    except:
        print("  (no metadata yet)")


# ============================================================
# MAIN
# ============================================================

def main():
    is_full = '--full' in sys.argv

    mode = "FULL REFRESH" if is_full else "INCREMENTAL"
    print("=" * 70)
    print(f"Sprint 4 ETL Pipeline -- {mode}")
    print("=" * 70)
    print(f"  SQL Server Source: {SQL_SERVER}/{SQL_SOURCE_DB}")
    print(f"  SQL Server DW:    {SQL_SERVER}/{SQL_DW_DB}")
    print(f"  MongoDB Source:   {MONGO_DATABASE}")
    print(f"  Batch Size:       {BATCH_SIZE:,}")
    print("=" * 70)

    overall_start = time.time()

    # Step 0: Ensure metadata table exists
    ensure_metadata_table()

    # For full refresh: clear ALL tables in dependency order (facts first, then dims)
    if is_full:
        print("\n--- Full Refresh: Clearing all tables (facts -> dimensions) ---")
        # Clear fact tables first (they reference dimensions via FK)
        for t in ['fact_revenue', 'fact_checkin', 'fact_gift_shop_sales', 'fact_payroll', 'fact_property_amenity']:
            try:
                run_dw(f"DELETE FROM [{t}]")
                print(f"  Cleared {t}")
            except Exception as e:
                print(f"  {t}: {e}")
        # Clear dimension tables (now safe since facts are empty)
        for t in ['dim_shop', 'dim_gift_product', 'dim_employee', 'dim_amenity',
                   'dim_product', 'dim_customer', 'dim_property']:
            try:
                run_dw(f"DELETE FROM [{t}]")
                run_dw(f"DBCC CHECKIDENT('{t}', RESEED, 0)")
                print(f"  Cleared {t} + identity reset")
            except Exception as e:
                print(f"  {t}: {e}")
        # Clear metadata
        run_dw("DELETE FROM __ETLMetadata")
        print("  Cleared __ETLMetadata")

    # Step 1: Dimensions (shared)
    print("\n" + "=" * 60)
    print("PHASE 1: Load Dimension Tables")
    print("=" * 60)

    load_dim_date_incremental()
    prop_map = load_dim_property(is_full)
    if not prop_map:
        prop_map_rows = run_dw("SELECT property_id, property_key FROM dim_property", fetch=True)
        prop_map = {r[0]: r[1] for r in prop_map_rows}
    cust_map = load_dim_customer(is_full)
    if not cust_map:
        cust_map_rows = run_dw("SELECT customer_id, customer_key FROM dim_customer", fetch=True)
        cust_map = {r[0]: r[1] for r in cust_map_rows}
    prod_map = load_dim_product(is_full)
    emp_map = load_dim_employee(is_full)
    if not emp_map:
        emp_map_rows = run_dw("SELECT employee_id, employee_key FROM dim_employee", fetch=True)
        emp_map = {r[0]: r[1] for r in emp_map_rows}
    amen_map = load_dim_amenity(is_full)

    # Step 2: MongoDB dimensions
    print("\n" + "=" * 60)
    print("PHASE 2: Load MongoDB Dimensions")
    print("=" * 60)

    mongo_client, mongo_db = connect_mongo()

    try:
        shop_map, shops_raw = load_dim_shop(mongo_db, prop_map, is_full)
        prod_gift_map, products_raw = load_dim_gift_product(mongo_db, is_full)

        # Step 3: Fact tables
        print("\n" + "=" * 60)
        print("PHASE 3: Load Fact Tables")
        print("=" * 60)

        rev_count = load_fact_revenue(is_full, prop_map, cust_map, prod_map)
        checkin_count = load_fact_checkin(is_full, prop_map, cust_map)
        gift_count = load_fact_gift_shop_sales(
            mongo_db, shops_raw, products_raw,
            shop_map, prod_gift_map, prop_map, is_full
        )
        payroll_count = load_fact_payroll(is_full, prop_map, emp_map)
        load_fact_property_amenity(is_full, prop_map, amen_map)

        # Step 4: Verify
        verify_all()

        overall_elapsed = time.time() - overall_start
        print(f"\n{'=' * 70}")
        print(f"ETL COMPLETE ({mode}) in {overall_elapsed:.1f}s")
        print(f"  fact_revenue:          {rev_count:>12,} rows")
        print(f"  fact_checkin:          {checkin_count:>12,} rows")
        print(f"  fact_gift_shop_sales:  {gift_count:>12,} rows")
        print(f"  fact_payroll:          {payroll_count:>12,} rows")
        print(f"{'=' * 70}")

    finally:
        mongo_client.close()
        print("\nAll connections closed.")


if __name__ == "__main__":
    main()
