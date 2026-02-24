# Sprint 2 Documentation

## Sprint Planning

**Sprint Goal**: Set up MongoDB integration, build ETL pipeline, design and implement star schemas for analytics.

**Planned Tasks**:
- Explore MongoDB `hotel` database (gift shop data) and create ERD
- Build Python ETL tool to migrate SQL Server Hotel data to MongoDB
- Convert top 3 Sprint 1 SQL queries to MongoDB aggregation pipelines
- Create indexes on MongoDB collections for query performance
- Design two star schemas (Revenue and Check-in analysis)
- Create `HotelDW` data warehouse database with dimension and fact tables

**Task Assignments**:
- **Meena**: ETL tool development, MongoDB aggregation queries, DW table creation
- **Kavaughn**: Star schema ERD design, gift shop ERD design
- **Yu & Meena**: Documentation, index analysis, verification

---

## Standup Notes

### Standup 1

**Done**
- Connected to MongoDB and explored gift shop collections
- Explored SQL Server Hotel schema (7 tables, ~86M rows)

**Next**
- Build ETL tool
- Start MongoDB ERD for gift shop data

**Blockers**
- None

---

### Standup 2

**Done**
- ETL tool built and tested
- Gift shop ERD completed

**Next**
- Convert SQL queries to MongoDB aggregations
- Design star schemas

**Blockers**
- None

---

### Standup 3

**Done**
- Query List 2 completed (3 MongoDB aggregation pipelines)
- Indexes created and verified
- Star schemas designed
- DW tables created in SQL Server

**Next**
- Final documentation and review

**Blockers**
- None

---

## Sprint Retrospective

**What Went Well**
- Clear deliverable structure from Sprint 1 carried forward
- ETL tool worked reliably for large data volumes
- Star schema designs directly support business questions from Sprint 1

**What Didn't Go Well**
- Large table sizes (17M+ events, 29M+ transaction lines) caused ETL to run slowly
- ERD confusion required troubleshooting

**Improvements for Next Sprint**
- Investigate incremental ETL (only new/changed rows) for faster runs
- Begin populating fact tables with actual data
- Consider additional star schemas for gift shop data analysis
