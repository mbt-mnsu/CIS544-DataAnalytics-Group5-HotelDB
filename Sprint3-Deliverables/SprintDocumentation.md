# Sprint 3 Documentation

## Sprint Planning

**Sprint Goal**: Populate the data warehouse star schemas with real data, build cross-source analytics integrating hotel operations and gift shop data.

**Sprint Duration**: ~10 calendar days (shorter sprint)

**Planned Tasks**:
- Populate Sprint 2 star schemas using SQL INSERT INTO...SELECT (same-server optimization)
- Generate dim_date table if empty
- Formulate 2 cross-source business questions (hotel + gift shop)
- Design and implement a new cross-source star schema (fact_gift_shop_sales)
- Build Python ETL pipeline for cross-source data (MongoDB gift shop → SQL Server DW)
- Write Query List 3 (data warehouse queries against populated schemas)

**Task Assignments**:
- **Meena**: DW population scripts, cross-source ETL (etl_cross_source.py), Query List 3
- **Kavaughn**: Cross-source star schema ERD design, cross-source business questions
- **Yu & Meena**: Documentation, data verification, query testing

---

## Standup Notes

### Standup 1

**Done**
- Analyzed current project status (Sprint 1 & 2 deliverables verified complete)
- Reviewed existing DW schema (4 dims, 2 facts - all empty)
- Explored MongoDB gift shop database structure (4 collections, 796K transactions)

**Next**
- Write SQL scripts for populating Sprint 2 star schemas
- Design cross-source star schema DDL

**Blockers**
- None

---

### Standup 2

**Done**
- Created Populate-HotelDW.sql using INSERT INTO...SELECT for all Sprint 2 dims + facts
- Created CrossSource-StarSchema-DDL.sql (dim_shop, dim_gift_product, fact_gift_shop_sales)
- Formulated 2 cross-source business questions

**Next**
- Build cross-source ETL (etl_cross_source.py) for MongoDB data
- Write Query List 3
- Run scripts and verify

**Blockers**
- None

---

### Standup 3

**Done**
- Completed etl_cross_source.py (cross-source ETL from MongoDB → SQL Server)
- Wrote Query List 3 (4 queries across all star schemas)
- Cleaned up unused Python scripts; SQL-based approach is cleaner and faster

**Next**
- Final verification and documentation review

**Blockers**
- None

---

## Sprint Retrospective

**What Went Well**
- SQL INSERT INTO...SELECT approach eliminated network round-trip overhead for same-server data
- Cross-source schema cleanly reuses shared dim_date and dim_property dimensions
- The located_at field in MongoDB shops provided a clean link to hotel properties
- Full-refresh strategy keeps logic simple and reproducible

**What Didn't Go Well**
- Initial Python ETL approach was too slow (8 rows/sec over network) for 29M+ rows - pivoted to SQL
- Customer ID mismatch between SQL Server and MongoDB prevents customer-level cross-source analysis (deferred to Sprint 4)

**Improvements for Next Sprint**
- Consider indexed views or materialized tables for frequently-run DW queries
- Explore customer fuzzy-matching between the two systems (name + email matching)
- Begin building dashboards to visualize data warehouse queries
