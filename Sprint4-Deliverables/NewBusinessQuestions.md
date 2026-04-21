# Sprint 4 - New Business Questions

## New Business Questions (Employee/Payroll/Amenity Data)

### Question 1: How do labor costs compare across properties relative to their hotel revenue?

**Business Question:**
Which properties have the highest labor cost as a percentage of revenue, and are there properties where staffing expenses are disproportionately high or low compared to the revenue they generate?

**Data Needed:**

| Source | Tables | Fields |
|---|---|---|
| SQL Server (Hotel) --> HotelDW | `fact_payroll` | gross_pay, net_pay, total_deductions per property |
| SQL Server (Hotel) --> HotelDW | `fact_revenue` | amount_per * quantity per property |
| HotelDW | `dim_property` | property name, location |
| HotelDW | `dim_date` | year, quarter for time-based analysis |

**How This Informs Business Decisions:**
An executive would use this analysis to identify properties that are over-staffed relative to their revenue (high labor cost ratio -> potential for rightsizing) or under-staffed (low labor cost ratio -> risk of poor service quality). This directly feeds into budgeting, staffing strategy, and P&L optimization for each property. Properties with labor costs exceeding industry benchmarks (typically 25-35% of revenue for hotels) may need operational review.

---

### Question 2: Do properties with more amenities generate higher revenue per room than those without?

**Business Question:**
Is there a measurable relationship between the number and type of amenities a property offers and its revenue performance? Do properties with premium amenities (spa, restaurant, fitness center) outperform properties with fewer amenities?

**Data Needed:**

| Source | Tables | Fields |
|---|---|---|
| SQL Server (Hotel) --> HotelDW | `fact_property_amenity` | amenity_key per property (count of amenities) |
| HotelDW | `dim_amenity` | amenity name, group (dining, recreation, etc.) |
| HotelDW | `fact_revenue` | total revenue per property |
| SQL Server (Hotel) | `property_rooms` | room counts per property (for per-room normalization) |
| HotelDW | `dim_property` | property name, location |

**How This Informs Business Decisions:**
This analysis helps executives make capital investment decisions. If properties with certain amenity combinations (e.g., spa + restaurant) generate significantly more revenue per room, the chain can prioritize those investments at under-performing properties. It also supports marketing decisions - properties with premium amenity packages can be marketed differently. Understanding amenity ROI is essential for new property development and renovation budgeting.

---

## New Data Exploration Summary

### New Tables Discovered

| Table | Rows | Description |
|---|---|---|
| `amenity` | 20 | Reference table of amenity types (restaurant, spa, pool, etc.) with group categorization |
| `employee` | 11,711 | Staff records with job_title, base_salary (in cents), property assignment, employment_type |
| `payroll` | 620,683 | Biweekly paycheck records with hours, gross/net pay, and tax withholding breakdown |
| `property_amenity` | 848 | Junction table linking properties to their amenities |

### Key Observations

- **Payroll monetary values are in cents** (e.g., gross_pay of 163414 = $1,634.14)
- **Employee base_salary is also in cents** (e.g., 6740060 = $67,400.60 annual)
- **Payroll date range**: Starts from late December 2022, with pay periods covering 2023-2025
- **Employment types**: `full_time` and `part_time`
- **Amenity groups**: Dining & Food, Recreation, Business, etc. - 20 distinct amenities across 848 property-amenity assignments
- **Average amenities per property**: ~3.5 amenities per property (848 / 245 properties)
- **Data ranges match**: Event/transaction data runs 2023-01-04 to 2025-01-01, aligning with payroll periods
