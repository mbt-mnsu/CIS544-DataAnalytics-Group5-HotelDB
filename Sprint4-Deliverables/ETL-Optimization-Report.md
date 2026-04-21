# Sprint 4 - ETL Optimization Report

## Overview

This report documents the performance analysis and optimization of our Sprint 3 ETL pipelines. Our data warehouse (HotelDW) is populated by two ETL mechanisms:

1. **SQL-to-SQL ETL** (`Populate-HotelDW.sql`) - Populates `fact_revenue`, `fact_checkin`, and their dimensions from the Hotel SQL Server database using `INSERT INTO...SELECT` statements
2. **Cross-Source Python ETL** (`etl_cross_source.py`) - Populates `fact_gift_shop_sales` and gift shop dimensions from MongoDB + SQL Server

---

## ETL 1: Populate-HotelDW.sql (SQL Server -> HotelDW)

### Architecture Analysis

This pipeline runs entirely **server-side** using `INSERT INTO...SELECT FROM Hotel.dbo.*` statements. Since both the source (`Hotel`) and destination (`HotelDW`) databases reside on the same SQL Server instance, the data never leaves the database engine. This is inherently the most efficient approach for SQL-to-SQL data movement.

**Why it's already optimal:**

| Strategy | Status | Explanation |
|---|---|---|
| Bulk operations | Already in use | `INSERT INTO...SELECT` is the SQL Server equivalent of a bulk load - it processes entire result sets in a single operation |
| No row-by-row processing | Already in use | No cursors, no loops over individual rows (except dim_date generation, which is a one-time operation) |
| No network overhead | Already in use | Both databases are on the same server instance - no data transfer over the network |
| Transaction batching | Already in use | Each `INSERT INTO...SELECT` runs as a single transaction |
| Set-based joins |  Already in use | Dimension lookups happen via JOINs in the SELECT, not via per-row queries |

### Benchmark

| Stage | Rows Processed | Estimated Time |
|---|---|---|
| dim_date (generation, if empty) | ~4,018 | ~5 sec |
| dim_property | 245 | < 1 sec |
| dim_customer | 623,710 | ~5-8 sec |
| dim_product | ~distinct descriptions | < 1 sec |
| fact_revenue (transact + transaction_line join) | ~29M line items | ~3-5 min |
| fact_checkin (event WHERE checkin) | ~8.9M events filtered | ~1-2 min |
| **Total** | **~38M+ rows** | **~5-8 min** |

### Optimization Verdict

**No changes needed.** The SQL-to-SQL pipeline is already optimal by design - it uses set-based operations with no network overhead. Any further optimization would require SQL Server tuning (indexes, memory allocation), which is outside the ETL code itself.

---

## ETL 2: etl_cross_source.py (MongoDB + SQL Server -> HotelDW)

### Before: Sprint 3 Architecture Analysis

The cross-source ETL was written with performance in mind from the start:

| Strategy | Status | Explanation |
|---|---|---|
| `fast_executemany` | Already in use | Uses ODBC array inserts — ~100x faster than standard `executemany` |
| Batch inserts (100K rows) | Already in use | Rows are accumulated in memory and flushed in 100,000-row batches |
| Connection-per-batch | Already in use | Fresh short-lived connections prevent timeouts on remote server |
| In-memory dimension lookups | Already in use | `prop_map`, `shop_map`, `prod_map`, `prod_name_to_key` are all Python dictionaries for O(1) lookups |
| MongoDB streaming cursor | Already in use | Transactions are streamed via cursor, not pulled all at once into memory |
| No per-row queries | Already in use | No database queries inside the transaction processing loop |

### Benchmark: Before Optimization

Running `etl_cross_source.py` with timing instrumentation:

| Stage | Rows | Time |
|---|---|---|
| Extract dim_property mapping | 245 keys | < 1 sec |
| MongoDB connect | - | < 1 sec |
| Truncate tables | 3 tables | < 2 sec |
| Extract shops from MongoDB | 65 docs | < 1 sec |
| Extract products from MongoDB | 2,229 docs | < 1 sec |
| Load dim_shop | 65 rows | < 1 sec |
| Load dim_gift_product | 2,229 rows | < 1 sec |
| Load fact_gift_shop_sales (streaming) | ~1.6M+ rows | ~15-25 sec |
| **Total** | | **~20-30 sec** |

### Optimizations Applied

While the core pipeline was already well-optimized, we added:

1. **Detailed per-stage timing instrumentation** - Each ETL stage now reports elapsed time, enabling future performance monitoring and regression detection
2. **Throughput metrics** - Rows-per-second reporting for fact table loading, making it easy to benchmark across environments

### Benchmark: After Optimization

Performance remains consistent (~20-30 seconds for full refresh) since the pipeline was already well-structured. The added instrumentation has negligible overhead.

### Data Flow Strategy

```
MongoDB (hotel)          SQL Server (Hotel)
     │                        │
     │ pymongo                │ pyodbc
                             
  [Python Memory]         [Python Memory]
  shops[]                 prop_map{}
  products[]              (dim_property cache)
  transactions (stream)
     │
     
  [Transform in Python]
  - Flatten line_items[]
  - Map shop_id -> shop_key (dict lookup)
  - Map prod_name -> gift_product_key (dict lookup)
  - Map store→property via located_at→prop_map (dict lookup)
  - Compute date_key from timestamp
     │
      (100K row batches, fast_executemany)
  [SQL Server HotelDW]
  fact_gift_shop_sales
```

### Performance Strategies Summary

1. **No N+1 queries** - All dimension data is cached in Python dicts before fact processing begins
2. **Batch inserts with array binding** - `fast_executemany = True` uses ODBC's array parameter binding, sending thousands of rows in a single network round trip
3. **Stream vs. bulk** - Small reference data (shops, products) is loaded in bulk; large transaction data is streamed to control memory usage
4. **Connection lifecycle** - Short-lived connections prevent timeouts on a shared remote server
