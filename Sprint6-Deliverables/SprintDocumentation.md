# Sprint 6 - Sprint Documentation

## Sprint Overview

**Sprint 6: Dashboard, Data Product, Presentation & Project Wrap-Up**
- Sprint Duration: April 21 - May 4, 2026
- Goal: Deliver the comprehensive analytics dashboard, create a PII-free data product, and prepare the final presentation

---

## Sprint Planning

### Deliverables

| # | Deliverable | Owner | Status |
|---|------------|-------|--------|
| 1 | Comprehensive Streamlit Dashboard (≥6 viz, ≥2 interactive, KPIs, computed measures) | Team | ✅ Complete |
| 2 | Dashboard Documentation (`DashboardDocumentation.md`) | Team | ✅ Complete |
| 3 | Power BI Queries (`PowerBI-Queries.md`) | Team | ✅ Complete |
| 4 | Gift Shop Open Dataset ETL (`etl_gift_shop_dataset.py`) | Team | ✅ Complete |
| 5 | Data Product README / Data Card | Team | ✅ Complete |
| 6 | SSMS Export (`GiftShopOpenDataset.sql`) | Team | ⬜ Pending (manual step) |
| 7 | Final Presentation Outline | Team | ✅ Complete |
| 8 | PowerPoint Slides | Team | ⬜ Pending (manual step) |
| 9 | Individual Retrospectives | Each member | ⬜ Pending (submitted on D2L) |

### Sprint Backlog

| Task | Est. Hours | Actual Hours | Notes |
|------|-----------|-------------|-------|
| Build multi-page Streamlit dashboard | 5-6 |  | 4 tabs, 9 visualizations |
| Write SQL queries for all visualizations | 1-2 |  | All queries hit HotelDW only |
| Implement interactive filters | 1 |  | Date range, property selector, top-N |
| Add computed measures | 1 |  | YoY change, labor cost %, gift shop % |
| Write dashboard documentation | 0.5 |  | |
| Write Power BI queries document | 0.5 |  | SQL + DAX measures |
| Build gift shop ETL (PII-free) | 1-2 |  | |
| Write data card README | 0.5 |  | |
| Prepare presentation outline | 1 |  | 12 slides |
| Create PowerPoint | 2 |  | Manual step |

---

## Standup Log

### Week 1 (April 21-25)

**Focus:** Dashboard development and data product ETL

- Built multi-page Streamlit dashboard with 4 tabs and 9 Plotly visualizations
- Implemented 3 computed measures: YoY Revenue Change, Labor Cost Ratio, Gift Shop %
- Added 3 interactive controls: date range, property multi-select, top-N slider
- Created KPI cards on each page (Total Revenue, Transactions, Check-ins, Payroll, etc.)

### Week 2 (April 26 - May 4)

**Focus:** Documentation, data product, and presentation prep

- Created `DashboardDocumentation.md` documenting all visualizations, data sources, and computed measures
- Created `PowerBI-Queries.md` with all SQL queries formatted for Power BI replication, including DAX measures
- Built `etl_gift_shop_dataset.py` to create PII-free `GiftShopOpenDataset` database
- Wrote data card (`README.md`) documenting schema, privacy safeguards, and limitations
- Prepared 12-slide presentation outline

---

## Technical Decisions

### Dashboard

| Decision | Rationale |
|----------|-----------|
| **Streamlit + Plotly** (not Power BI) | Continues from Sprint 4 POC; code-based dashboard is version-controlled and reproducible |
| **Tab-based layout** (not multi-page) | Simpler navigation for presentation demo; all data visible without page switching |
| **Connection caching** (`@st.cache_resource`) | Prevents re-opening connections on every interaction |
| **Query caching** (`@st.cache_data(ttl=300)`) | 5-minute TTL balances freshness with performance |
| **Dynamic SQL filters** | Property and date filters are injected into SQL; enables real-time interactivity |

### Data Product

| Decision | Rationale |
|----------|-----------|
| **Separate database** (`GiftShopOpenDataset`) | Clean isolation from DW; can be exported independently |
| **IDENTITY-based re-sequencing** | Transaction IDs cannot be correlated back to source system |
| **No customer table** | Complete PII removal - not even anonymized customer IDs |
| **FK constraints preserved** | Maintains referential integrity within the open dataset |

---

## Sprint Retrospective

### What Went Well
- Dashboard development was efficient thanks to the well-structured star schema
- Plotly visualizations are interactive and presentation-ready out of the box
- PII removal strategy was straightforward using the DW's dimensional model

### What Could Be Improved
- Earlier start on the dashboard would have allowed more polish and edge-case testing
- Could have added more advanced Plotly features (drill-down, cross-filtering)

### Lessons Learned
- Star schema design directly impacts dashboard development speed - good schema = fast dashboards
- Computed measures (YoY, ratios) add significant analytical value with minimal code
- Data products require careful PII review; systematic column scanning is essential

---

## Cumulative Project Summary (Sprints 1-6)

| Sprint | Key Deliverables |
|--------|-----------------|
| **1** | ERD, Data Dictionary, 6 Discovery Queries, Team Charter |
| **2** | MongoDB ERD, ETL (SQL→Mongo), Star Schema DDLs |
| **3** | Date Dimension, Cross-Source ETL, DW Population |
| **4** | ETL Optimization, Streamlit POC, New Schemas (Payroll, Amenity) |
| **5** | DGDB (SQLAlchemy ORM), 4 Validation Rules, ETL Integration |
| **6** | 9-Viz Dashboard, Gift Shop Data Product, Final Presentation |
