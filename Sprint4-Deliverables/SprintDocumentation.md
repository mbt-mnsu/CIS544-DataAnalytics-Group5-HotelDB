# Sprint 4 - Sprint Documentation

## Sprint Planning

### Sprint Goal
Complete ETL optimization, visualization proof-of-concept, and integrate new employee/payroll/amenity data using incremental ETL.

### Task Breakdown

| Task | Owner | Status |
|---|---|---|
| ETL Optimization & Benchmarking | Team | Complete |
| Visualization PoC (Streamlit) | Team | Complete |
| Explore new source data (employee, payroll, amenity) | Team | Complete |
| New business questions (payroll/amenity) | Team | Complete |
| New star schema DDL (dim_employee, dim_amenity, fact_payroll, fact_property_amenity) | Team | Complete |
| ETL Metadata table (__ETLMetadata) | Team | Complete |
| Incremental ETL pipeline (etl_incremental.py) | Team | Complete |
| Run full refresh ETL to populate all schemas | Team | Pending |
| Run incremental ETL to verify incremental behavior | Team | Pending |
| Capture dashboard screenshot | Team | Pending |

---

## Standup Notes

### Standup 1 - March 24
- **Completed**: Reviewed Sprint 4 requirements, identified two phases
- **Next**: Begin ETL optimization audit, explore new tables
- **Blockers**: Waiting for new data availability confirmation

### Standup 2 - March 26
- **Completed**: Explored new tables (employee, payroll, amenity, property_amenity). All available. Documented ETL optimization report — existing pipeline already uses fast_executemany and batch inserts.
- **Next**: Design new star schemas, build incremental ETL

### Standup 3 - March 28
- **Completed**: Created new star schema DDL (dim_employee, dim_amenity, fact_payroll, fact_property_amenity). Created ETL metadata table. Built incremental ETL pipeline.
- **Next**: Run full load, verify, build dashboard PoC
- **Blockers**: None

### Standup 4 - March 30
- **Completed**: Streamlit dashboard PoC built. Full ETL pipeline ready. New business questions documented.
- **Next**: Execute full refresh, test incremental mode, capture screenshots

---

## Sprint Retrospective

### What went well
- New source data was available on time (employee, payroll, amenity tables)
- Existing ETL code was already well-optimized (fast_executemany, batch inserts, in-memory caching)
- Unified incremental ETL pipeline handles all source systems in one script

### What could be improved
- Should test FK constraint ordering earlier in development
- Could add more error handling/retry logic for network timeouts

### Key decisions
- **Streamlit** chosen over Power BI for visualization (leverages existing Python skills)
- **Centralized clearing** approach for full refresh (facts -> dims -> metadata) to avoid FK violations
- **ETL metadata table** uses both `last_load_max_id` and `last_load_max_date` to handle different table types
- **Payroll values stored in cents** (matching source data) - conversion to dollars happens at query/display time
