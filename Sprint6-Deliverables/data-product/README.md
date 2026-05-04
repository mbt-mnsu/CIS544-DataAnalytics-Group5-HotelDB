# Gift Shop Open Dataset - Data Card

## Overview

The **Gift Shop Open Dataset** is a curated, PII-free data product derived from the HotelDW data warehouse. It contains gift shop transaction data across a hotel chain's properties, suitable for public analysis, academic use, or third-party sharing.

## Source

- **Original Source Systems:** SQL Server (Hotel operational DB) + MongoDB (Gift Shop)
- **Intermediate Source:** HotelDW data warehouse (star schema)
- **ETL Tool:** `etl_gift_shop_dataset.py` (Python + pyodbc)

## Privacy & PII

> **⚠ This dataset contains NO personally identifiable information (PII).**

The following safeguards have been applied:

| PII Element | Treatment |
|-------------|-----------|
| Customer IDs | **Removed** - not present in any table |
| Customer Names | **Removed** - not present in any table |
| Customer Email / Phone / Address | **Removed** - not present in any table |
| Employee Data | **Excluded** - no employee tables included |
| Transaction IDs | **Re-sequenced** - IDENTITY-generated IDs that cannot be correlated to source system |
| Payment Card Numbers | **Excluded** - only payment method type (e.g., "credit", "debit") is retained |

## Schema

### `properties`
| Column | Type | Description |
|--------|------|-------------|
| property_id | INT (PK) | Property identifier |
| name | NVARCHAR(192) | Hotel property name |
| city | NVARCHAR(96) | City |
| state | VARCHAR(2) | State abbreviation |
| zip | VARCHAR(10) | ZIP code |

### `products`
| Column | Type | Description |
|--------|------|-------------|
| product_id | INT (PK) | Product identifier |
| name | NVARCHAR(192) | Product name |
| price | DECIMAL(10,2) | Unit price |
| category | NVARCHAR(96) | Product category |

### `transactions`
| Column | Type | Description |
|--------|------|-------------|
| transaction_id | INT (PK, IDENTITY) | Re-sequenced transaction ID |
| transaction_date | DATE | Date of the transaction |
| property_id | INT (FK --> properties) | Property where the sale occurred |
| product_id | INT (FK --> products) | Product sold |
| quantity | INT | Quantity purchased |
| sale_amount | DECIMAL(10,2) | Unit sale amount |
| payment_method | VARCHAR(50) | Payment method (e.g., credit, debit, cash) |
| payment_status | VARCHAR(20) | Payment status (e.g., completed, refunded) |

## Time Period

The dataset covers the full date range available in the HotelDW `dim_date` table, which corresponds to the operational history of the gift shop system.

## Limitations & Caveats

1. **No Customer Linkage:** Transactions cannot be linked to individual customers by design. Customer segmentation or repeat-purchase analysis is not possible.
2. **Re-sequenced IDs:** Transaction IDs in this dataset are synthetic and do not correspond to any source-system identifiers.
3. **Property Subset:** Only properties that have an associated gift shop (`dim_shop.located_at`) are included.
4. **Point-in-Time Snapshot:** This dataset represents a snapshot; it is not incrementally updated.
5. **Derived Data:** Sale amounts and quantities are as recorded in the DW; no adjustments for returns have been applied beyond the `payment_status` field.

## Suggested Use Cases

- Gift shop product performance analysis by category
- Regional/property-level sales comparisons
- Seasonal trend analysis
- Payment method distribution studies
- Pricing strategy research

## Export Format

The dataset is exported using SSMS "Generate Scripts" wizard:
- **Database:** `GiftShopOpenDataset`
- **Script Options:** Schema + Data
- **Output:** Single `.sql` file (`GiftShopOpenDataset.sql`)

### SSMS Export Instructions

1. Open SSMS and connect to `cis444.campus-quest.com,25000`
2. Right-click `GiftShopOpenDataset` --> Tasks --> Generate Scripts
3. Select "Script entire database and all database objects"
4. Click Advanced --> Types of data to script --> **Schema and Data**
5. Save to file --> `GiftShopOpenDataset.sql`
6. If the file exceeds submission size limits, compress to `.zip`
