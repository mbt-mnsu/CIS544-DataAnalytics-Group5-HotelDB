"""
Sprint 5 - Validation Rules
=============================
Data quality checks executed after ETL loading.
Each rule queries HotelDW and returns (records_checked, records_passed, records_failed).
Results are logged to the DGDB via DGDBClient.

Rules implemented:
  1. fk_integrity_revenue        — Referential integrity in fact_revenue
  2. null_completeness_check     — Null/completeness for critical fields
  3. date_range_coverage         — Date dimension coverage for all facts
  4. cross_source_customer_overlap — Customer overlap between Hotel SQL & MongoDB
"""

import pyodbc
import pymongo
from datetime import datetime


# ============================================================
# Rule 1: Referential Integrity - fact_revenue FK check
# ============================================================

def validate_fk_integrity_revenue(dw_conn_func):
    """
    Verify that every property_key in fact_revenue has a matching
    row in dim_property, and every customer_key has a matching row
    in dim_customer.

    Why it matters:
      If fact records reference non-existent dimensions, joins will
      silently drop rows from query results, producing incorrect
      analytics (understated revenue, missing properties, etc.)
    """
    print("\n  [Rule 1] Referential Integrity -- fact_revenue FK check")

    conn = dw_conn_func()
    cursor = conn.cursor()

    # Check property_key FK
    cursor.execute("""
        SELECT COUNT(*) AS total_facts,
               SUM(CASE WHEN dp.property_key IS NULL THEN 1 ELSE 0 END) AS orphaned
        FROM fact_revenue fr
        LEFT JOIN dim_property dp ON fr.property_key = dp.property_key
    """)
    row = cursor.fetchone()
    total_prop = row[0]
    orphaned_prop = row[1]

    # Check customer_key FK
    cursor.execute("""
        SELECT COUNT(*) AS total_facts,
               SUM(CASE WHEN dc.customer_key IS NULL THEN 1 ELSE 0 END) AS orphaned
        FROM fact_revenue fr
        LEFT JOIN dim_customer dc ON fr.customer_key = dc.customer_key
    """)
    row2 = cursor.fetchone()
    orphaned_cust = row2[1]

    # Check product_key FK
    cursor.execute("""
        SELECT COUNT(*) AS total_facts,
               SUM(CASE WHEN dp.product_key IS NULL THEN 1 ELSE 0 END) AS orphaned
        FROM fact_revenue fr
        LEFT JOIN dim_product dp ON fr.product_key = dp.product_key
    """)
    row3 = cursor.fetchone()
    orphaned_prod = row3[1]

    conn.close()

    total_checked = total_prop  # all three checks are over the same fact table rows
    total_failed = orphaned_prop + orphaned_cust + orphaned_prod

    print(f"    fact_revenue rows: {total_prop:,}")
    print(f"    Orphaned property_key: {orphaned_prop:,}")
    print(f"    Orphaned customer_key: {orphaned_cust:,}")
    print(f"    Orphaned product_key:  {orphaned_prod:,}")

    return (total_checked, total_checked - total_failed, total_failed)


# ============================================================
# Rule 2: Null/Completeness — critical fields
# ============================================================

def validate_null_completeness(dw_conn_func):
    """
    Verify that critical business fields are populated (not NULL):
      - dim_customer: first_name, last_name
      - fact_revenue: date_key, amount_per
      - fact_payroll: date_key, gross_pay, net_pay

    Why it matters:
      NULL values in critical fields break aggregations (SUM ignores NULLs,
      leading to understated totals), cause join failures, and make reports
      unreliable for business decisions.
    """
    print("\n  [Rule 2] Null/Completeness -- critical fields check")

    conn = dw_conn_func()
    cursor = conn.cursor()

    total_checked = 0
    total_failed = 0

    # Check dim_customer names
    cursor.execute("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN first_name IS NULL OR last_name IS NULL THEN 1 ELSE 0 END) AS null_names
        FROM dim_customer
    """)
    row = cursor.fetchone()
    cust_total, cust_nulls = row[0], row[1]
    total_checked += cust_total
    total_failed += cust_nulls
    print(f"    dim_customer (name nulls): {cust_nulls:,} / {cust_total:,}")

    # Check fact_revenue critical fields
    cursor.execute("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN date_key IS NULL OR amount_per IS NULL THEN 1 ELSE 0 END) AS nulls
        FROM fact_revenue
    """)
    row = cursor.fetchone()
    rev_total, rev_nulls = row[0], row[1]
    total_checked += rev_total
    total_failed += rev_nulls
    print(f"    fact_revenue (date/amount nulls): {rev_nulls:,} / {rev_total:,}")

    # Check fact_payroll critical fields
    cursor.execute("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN date_key IS NULL OR gross_pay IS NULL OR net_pay IS NULL THEN 1 ELSE 0 END) AS nulls
        FROM fact_payroll
    """)
    row = cursor.fetchone()
    pay_total, pay_nulls = row[0], row[1]
    total_checked += pay_total
    total_failed += pay_nulls
    print(f"    fact_payroll (date/pay nulls): {pay_nulls:,} / {pay_total:,}")

    conn.close()

    return (total_checked, total_checked - total_failed, total_failed)


# ============================================================
# Rule 3: Date Range Coverage — dim_date completeness
# ============================================================

def validate_date_range_coverage(dw_conn_func):
    """
    Verify that the dim_date table covers all date_key values
    present in ALL fact tables (fact_revenue, fact_checkin,
    fact_gift_shop_sales, fact_payroll).

    Why it matters:
      Missing dates in dim_date mean that fact records referencing
      those dates will be excluded from any query that joins to
      dim_date (which is most analytical queries). This silently
      drops data from reports.
    """
    print("\n  [Rule 3] Date Range Coverage -- dim_date completeness")

    conn = dw_conn_func()
    cursor = conn.cursor()

    fact_tables = ['fact_revenue', 'fact_checkin', 'fact_gift_shop_sales', 'fact_payroll']
    total_checked = 0
    total_failed = 0

    for table in fact_tables:
        try:
            cursor.execute(f"""
                SELECT COUNT(DISTINCT f.date_key) AS total_keys,
                       SUM(CASE WHEN dd.date_key IS NULL THEN 1 ELSE 0 END) AS missing
                FROM (SELECT DISTINCT date_key FROM [{table}]) f
                LEFT JOIN dim_date dd ON f.date_key = dd.date_key
            """)
            row = cursor.fetchone()
            t, m = row[0], row[1]
            total_checked += t
            total_failed += m
            print(f"    {table}: {m:,} missing date_keys / {t:,} distinct date_keys")
        except Exception as e:
            print(f"    {table}: ERROR -- {e}")

    conn.close()

    return (total_checked, total_checked - total_failed, total_failed)


# ============================================================
# Rule 4: Cross-Source Customer Overlap
# ============================================================

def validate_cross_source_customer_overlap(dw_conn_func, source_conn_func, mongo_uri, mongo_db_name):
    """
    Investigate the overlap between customers in the Hotel SQL Server
    database and the MongoDB gift shop database.

    Matching approach:
      Match on LOWER(first_name) + LOWER(last_name) + LOWER(state)
      since both systems share these fields but use different IDs.

    Why it matters:
      Understanding customer overlap is essential for cross-source
      analytics. If the overlap is low, cross-source queries linking
      hotel stays to gift shop purchases may be missing most customers.
      This affects the reliability of questions like "Do hotel guests
      spend more at gift shops?"

    This is more of a data quality investigation than a pass/fail check.
    """
    print("\n  [Rule 4] Cross-Source Customer Overlap Analysis")

    # Get SQL Server customers
    conn = source_conn_func()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT LOWER(first_name), LOWER(last_name), LOWER(state)
        FROM customer
        WHERE first_name IS NOT NULL AND last_name IS NOT NULL AND state IS NOT NULL
    """)
    sql_customers = set()
    sql_total = 0
    for row in cursor.fetchall():
        sql_customers.add((row[0].strip(), row[1].strip(), row[2].strip()))
        sql_total += 1
    conn.close()
    print(f"    Hotel SQL customers: {sql_total:,} ({len(sql_customers):,} unique name+state combos)")

    # Get MongoDB customers
    client = pymongo.MongoClient(mongo_uri)
    db = client[mongo_db_name]
    mongo_cursor = db.customers.find(
        {"first_name": {"$exists": True}, "last_name": {"$exists": True}},
        {"first_name": 1, "last_name": 1, "state": 1}
    )
    mongo_customers = set()
    mongo_total = 0
    for doc in mongo_cursor:
        fn = str(doc.get('first_name', '')).lower().strip()
        ln = str(doc.get('last_name', '')).lower().strip()
        st = str(doc.get('state', '')).lower().strip()
        if fn and ln and st:
            mongo_customers.add((fn, ln, st))
            mongo_total += 1
    client.close()
    print(f"    MongoDB gift shop customers: {mongo_total:,} ({len(mongo_customers):,} unique name+state combos)")

    # Compute overlap
    overlap = sql_customers & mongo_customers
    overlap_count = len(overlap)

    sql_only = len(sql_customers - mongo_customers)
    mongo_only = len(mongo_customers - sql_customers)

    pct_sql = (overlap_count / len(sql_customers) * 100) if sql_customers else 0
    pct_mongo = (overlap_count / len(mongo_customers) * 100) if mongo_customers else 0

    print(f"    Matching customers (name+state): {overlap_count:,}")
    print(f"    SQL-only customers: {sql_only:,}")
    print(f"    MongoDB-only customers: {mongo_only:,}")
    print(f"    Overlap as % of SQL customers: {pct_sql:.1f}%")
    print(f"    Overlap as % of MongoDB customers: {pct_mongo:.1f}%")

    # For this investigation, we treat total checked as total unique combos across both
    total_checked = len(sql_customers) + len(mongo_customers)
    # "passed" = matched in both systems; "failed" = unmatched
    records_passed = overlap_count * 2  # counted in both sets
    records_failed = sql_only + mongo_only

    return (total_checked, records_passed, records_failed)


# ============================================================
# Run All Validations
# ============================================================

def run_all_validations(dgdb_client, run_id, dw_conn_func, source_conn_func,
                        mongo_uri, mongo_db_name):
    """
    Execute all validation rules and log results to the DGDB.

    Args:
        dgdb_client: DGDBClient instance
        run_id: ETL run ID to associate validations with
        dw_conn_func: callable that returns a pyodbc connection to HotelDW
        source_conn_func: callable that returns a pyodbc connection to Hotel (source)
        mongo_uri: MongoDB connection URI
        mongo_db_name: MongoDB database name
    """
    print("\n" + "=" * 60)
    print("VALIDATION PHASE: Running data quality checks")
    print("=" * 60)

    # Rule 1: Referential integrity
    checked, passed, failed = validate_fk_integrity_revenue(dw_conn_func)
    dgdb_client.log_validation(
        run_id, "fk_integrity_revenue",
        "Verify all FK references (property_key, customer_key, product_key) "
        "in fact_revenue have matching dimension rows",
        checked, passed, failed
    )

    # Rule 2: Null/completeness
    checked, passed, failed = validate_null_completeness(dw_conn_func)
    dgdb_client.log_validation(
        run_id, "null_completeness_check",
        "Verify critical business fields (customer names, transaction amounts, "
        "dates, pay amounts) are not NULL",
        checked, passed, failed
    )

    # Rule 3: Date range coverage
    checked, passed, failed = validate_date_range_coverage(dw_conn_func)
    dgdb_client.log_validation(
        run_id, "date_range_coverage",
        "Verify dim_date covers all date_key values in all fact tables "
        "(revenue, checkin, gift shop, payroll)",
        checked, passed, failed
    )

    # Rule 4: Cross-source customer overlap
    checked, passed, failed = validate_cross_source_customer_overlap(
        dw_conn_func, source_conn_func, mongo_uri, mongo_db_name
    )
    dgdb_client.log_validation(
        run_id, "cross_source_customer_overlap",
        "Investigate customer overlap between Hotel SQL Server and MongoDB "
        "gift shop databases using name+state matching",
        checked, passed, failed
    )

    print("\n  All validations complete.")
