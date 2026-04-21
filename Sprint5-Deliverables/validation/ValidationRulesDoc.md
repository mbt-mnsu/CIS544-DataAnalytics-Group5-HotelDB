# Sprint 5 - Validation Rules Documentation

## Overview

Four data quality validation rules are executed after each ETL run. Results are automatically logged to the Data Governance Database (`HotelDGDB.Validation_Results`) and tied to the specific ETL run that triggered them.

---

## Rule 1: Referential Integrity - `fk_integrity_revenue`

### What It Checks
Verifies that every foreign key in `fact_revenue` has a matching record in its corresponding dimension table:
- `property_key` -> `dim_property`
- `customer_key` -> `dim_customer`
- `product_key` -> `dim_product`

### Why It Matters
If fact records reference non-existent dimensions ("orphaned keys"), those rows will be silently **dropped from any query** that joins to the dimension table. This produces understated revenue totals, missing properties in reports, and incorrect per-customer analytics. In a production environment, orphaned keys often indicate an ETL logic error - dimensions were not loaded before facts, or a filtering condition excluded dimension records that facts still reference.

### Implementation
Performs three LEFT JOIN queries between `fact_revenue` and each dimension table. Counts rows where the dimension side is NULL (orphaned). Returns the sum of all orphaned rows as `records_failed`.

```sql
-- Example: property_key check
SELECT COUNT(*) AS total_facts,
       SUM(CASE WHEN dp.property_key IS NULL THEN 1 ELSE 0 END) AS orphaned
FROM fact_revenue fr
LEFT JOIN dim_property dp ON fr.property_key = dp.property_key
```

---

## Rule 2: Null/Completeness - `null_completeness_check`

### What It Checks
Verifies that critical business fields are populated (not NULL):
- `dim_customer`: `first_name`, `last_name`
- `fact_revenue`: `date_key`, `amount_per`
- `fact_payroll`: `date_key`, `gross_pay`, `net_pay`

### Why It Matters
NULL values in critical fields break aggregations silently - `SUM()` ignores NULLs, leading to **understated totals**. NULL customer names make it impossible to perform customer-level analytics or cross-source matching. NULL dates prevent records from joining to `dim_date`, effectively hiding them from time-based reports. NULL pay amounts produce incorrect labor cost calculations.

### Implementation
Queries each table with conditional aggregation to count NULLs in the specified columns. Sums all NULL occurrences across all three checks as `records_failed`.

```sql
-- Example: customer name completeness
SELECT COUNT(*) AS total,
       SUM(CASE WHEN first_name IS NULL OR last_name IS NULL THEN 1 ELSE 0 END) AS null_names
FROM dim_customer
```

---

## Rule 3: Date Range Coverage - `date_range_coverage`

### What It Checks
Verifies that the `dim_date` table contains rows for **every `date_key`** referenced by any fact table:
- `fact_revenue`
- `fact_checkin`
- `fact_gift_shop_sales`
- `fact_payroll`

### Why It Matters
`dim_date` is a shared dimension across all fact tables. If a fact record's `date_key` doesn't have a corresponding row in `dim_date`, any query that joins to `dim_date` (which is nearly every analytical query) will **silently exclude that fact record**. This is especially dangerous with incremental ETL - if new source data contains dates beyond the current `dim_date` range and the date dimension isn't extended first, all new facts for those dates will be invisible in reports.

### Implementation
For each fact table, extracts distinct `date_key` values and LEFT JOINs to `dim_date`. Counts any `date_key` values where `dim_date` has no matching row.

```sql
SELECT COUNT(DISTINCT f.date_key) AS total_keys,
       SUM(CASE WHEN dd.date_key IS NULL THEN 1 ELSE 0 END) AS missing
FROM (SELECT DISTINCT date_key FROM [fact_revenue]) f
LEFT JOIN dim_date dd ON f.date_key = dd.date_key
```

---

## Rule 4: Cross-Source Customer Overlap - `cross_source_customer_overlap`

### What It Checks
Investigates the overlap between customers in the Hotel SQL Server database and the MongoDB gift shop database. Since these systems use different customer IDs with no direct link, the analysis matches customers based on:

**Matching criteria:** `LOWER(first_name)` + `LOWER(last_name)` + `LOWER(state)`

### Why It Matters
Understanding customer overlap is essential for the reliability of cross-source analytics. Questions like "Do hotel guests spend more at gift shops?" or "Is there a correlation between length of stay and gift shop purchases?" depend on being able to link customers across systems. If the overlap is low, these cross-source analyses may be unreliable or represent only a small subset of actual customers.

### Implementation
1. Extracts unique `(first_name, last_name, state)` tuples from Hotel SQL Server `customer` table
2. Extracts unique `(first_name, last_name, state)` tuples from MongoDB `hotel.customers` collection
3. Computes set intersection (matches), SQL-only, and MongoDB-only counts
4. Reports overlap percentages for both systems

### Limitations
- **Name-only matching is imperfect**: Different people can share the same name and state (false positives)
- **Name variations**: "Bob" vs "Robert", "St." vs "Street" in addresses - not handled
- **Missing state data**: Records without state values are excluded from matching
- **One-to-many ambiguity**: A name+state combo appearing multiple times in one system may map to different individuals

### Findings
*(Populated after first ETL run - see DGDB-Evidence.md)*
