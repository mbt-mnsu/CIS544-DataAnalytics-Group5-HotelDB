# Sprint 6 Final Presentation - Slide Outline

> Target: 10–12 slides, ~12 minutes presentation + live dashboard demo

---

## Slide 1: Title Slide

**Hotel Chain Analytics Platform**
- Team Name / Members
- Course: CIS 444/544 - Data Warehousing
- Date: Spring 2026
- Sprint 6 - Final Deliverable

---

## Slide 2: Business Context

**The Hotel Chain**
- Overview of the business domain: multi-property hotel chain with 245 properties
- Integrated gift shop operations (MongoDB-sourced)
- Business challenge: Need for unified analytics across operational systems

**Key Stats:**
- 245 properties | 623K customers | 8.9M transactions | 29M line items
- Gift shop: MongoDB with shops, products, and transactions

---

## Slide 3: Business Questions

**11 Business Questions Driving the Analytics:**

1. Monthly revenue by property
2. Revenue by product/service
3. Check-in volume trends
4. Customer spending patterns
5. Room pricing analysis
6. Payment method usage
7. Hotel vs. gift shop revenue (cross-source)
8. Top gift shop categories
9. Weekend vs. weekday check-ins
10. Labor costs vs. revenue
11. Amenities vs. revenue

---

## Slide 4: Data Architecture

**Source → ETL → Warehouse → Dashboard Pipeline**

Diagram showing:
```
Hotel (SQL Server)  ──┐
  cis444:25000        ├──▶  Python ETL  ──▶  HotelDW  ──▶  Streamlit Dashboard
Gift Shop (MongoDB)  ──┘     (pyodbc,       (8 dims,         (Plotly)
  cis444:25010               pymongo)       5 facts)
```

- Incremental ETL with metadata tracking
- Data Governance DB (DGDB) for validation logging
- All dashboard queries hit DW only

---

## Slide 5: Star Schema Design

**5 Star Schemas in HotelDW:**

| Fact Table | Dimensions | Grain |
|-----------|------------|-------|
| fact_revenue | dim_date, dim_property, dim_customer, dim_room_type | Transaction line item |
| fact_checkin | dim_date, dim_property, dim_customer | Check-in event |
| fact_gift_shop_sales | dim_date, dim_property, dim_shop, dim_gift_product | Gift shop line item |
| fact_payroll | dim_date, dim_property, dim_employee | Payroll record |
| fact_property_amenity | dim_property, dim_amenity | Property-amenity mapping |

---

## Slide 6: Dashboard Demo (Live)

**🖥️ LIVE DEMO - Streamlit Dashboard**

Walk through each tab:
1. Executive Overview - KPIs, revenue trend, payment breakdown, top properties
2. Operations & Staffing - labor cost ratios, weekend/weekday patterns
3. Gift Shop Analytics - cross-source comparison, category performance
4. Amenities & Trends - amenity impact, seasonal heatmap

**Highlight:**
- Interactive filters (date range, property selector, top-N)
- 3 computed measures (YoY change, labor cost %, gift shop %)

---

## Slide 7: Dashboard Screenshots (Backup)

Including 4 screenshots, one per tab:
1. Executive Overview with KPIs and revenue trend
2. Operations showing labor cost bar chart
3. Gift Shop dual-axis comparison
4. Amenity scatter plot + heatmap

*Backup in case live demo has connectivity issues*

---

## Slide 8: Key Findings

**Insights from the Data:**

1. **Revenue Concentration:** Top 10 properties account for ~X% of total revenue
2. **Labor Efficiency:** Properties with labor cost % > 30% may need staffing optimization
3. **Gift Shop Impact:** Gift shop revenue represents ~X% of total hotel revenue
4. **Seasonal Patterns:** Check-in volume peaks in [month] and dips in [month]
5. **Amenity Correlation:** Properties with more amenities tend to generate higher revenue

*Note: Replace X% values with actual data from dashboard during prep*

---

## Slide 9: Data Product - Gift Shop Open Dataset

**PII-Free Data Mart for External Sharing**

- Database: `GiftShopOpenDataset`
- 3 tables: properties, products, transactions
- All customer PII removed
- Transaction IDs re-sequenced (cannot be correlated)
- Exported via SSMS as `.sql` file

**Use Cases:** Product performance analysis, regional comparisons, pricing research

---

## Slide 10: Data Governance

**Sprint 5: DGDB Integration**

- `ETL_Runs` table: Logs every ETL execution (start/end time, rows affected, status)
- `Validation_Results` table: Logs 4 automated data quality rules
- SQLAlchemy ORM for Python integration

**4 Validation Rules:**
1. Referential integrity (FK checks)
2. Null checks on required columns
3. Date range validity
4. Numeric range validation

---

## Slide 11: Sprint-by-Sprint Journey

| Sprint | Focus | Key Achievement |
|--------|-------|----------------|
| 1 | Discovery | ERD, data dictionary, 6 initial queries |
| 2 | MongoDB + DW Design | ETL to MongoDB, star schema DDL |
| 3 | DW Population | Cross-source ETL, date dimension |
| 4 | Optimization | Incremental ETL, Streamlit POC, new schemas |
| 5 | Data Governance | DGDB, validation rules, audit logging |
| 6 | Dashboard + Data Product | 9-viz dashboard, PII-free dataset, presentation |

---

## Slide 12: Reflection & Lessons Learned

**What Went Well:**
- Incremental ETL design scaled well across sprints
- Cross-source integration (SQL Server + MongoDB) provided richer analytics
- Streamlit + Plotly enabled rapid dashboard development

**Challenges:**
- Remote SQL Server connection timeouts (solved with connection-per-batch pattern)
- MongoDB schema flexibility required careful data validation
- Large dataset sizes (29M+ rows) required batch processing optimization

**Lessons Learned:**
- Data governance should be integrated early, not retrofitted
- Star schema design decisions have cascading impacts on all downstream analytics
- Interactive dashboards are far more valuable than static reports

---

