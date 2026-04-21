# Sprint 5 - Sprint Documentation

## Sprint Planning (April 6, 2026)

### Sprint Goal
To build a Data Governance Database (DGDB) to track ETL operations and data quality, then integrate new source data using incremental ETL with DGDB logging.

### Key Deliverables
1. DGDB with ETL_Runs and Validation_Results tables (SQLAlchemy ORM)
2. Four validation rules: FK integrity, null checks, date coverage, cross-source customer overlap
3. Updated ETL pipeline with DGDB integration (auto-creates DB/tables on first run)
4. Incremental ETL run processing new source data
5. Evidence documentation

### Task Assignments
- DGDB schema design and ORM models
- Validation rule implementation
- ETL pipeline integration
- Documentation and evidence capture

### Architecture Decisions
- **ORM**: SQLAlchemy - industry standard, well-documented, appropriate for the small DGDB schema
- **Auto-bootstrap**: DGDBClient creates the database and tables automatically on first ETL run (no manual setup scripts)
- **Separate database**: DGDB is `HotelDGDB`, separate from source (`Hotel`) and warehouse (`HotelDW`)
- **Validation approach**: Rules query the DW via pyodbc (raw SQL is appropriate for analytical queries), results logged to DGDB via ORM

---

## Retrospective

### What went well
- Successfully implemented Data Governance Database (DGDB) using SQLAlchemy ORM with auto-creation functionality
- Integrated four comprehensive validation rules: FK integrity, null checks, date coverage, and cross-source customer overlap analysis
- Updated ETL pipeline to log runs and validation results to DGDB automatically
- Incremental ETL processed successfully with full logging and validation (0 new records due to no new source data)
- All validation rules executed correctly, with expected results (0% cross-source overlap due to no MongoDB customer data in this run)
- Clean separation of concerns: DGDB separate from source and warehouse databases

### What could be improved
- Cross-source customer overlap analysis revealed 0% overlap, indicating potential data quality issues or lack of integrated customer data across systems
- ETL pipeline could benefit from more granular error handling and retry logic for production scenarios
- Validation rules documentation could include performance metrics and execution times for large datasets

### Action items
- Investigate why MongoDB gift shop has 0 customers - may indicate data loading issues or separate customer systems
- Consider adding more validation rules in future sprints (e.g., data type consistency, range validation)
- Evaluate DGDB performance with larger datasets and consider indexing strategies

---

## Evidence and Runlogs

### ETL Execution Results
- **File**: `etl_sprint5_output.txt`
- **Run Type**: Incremental ETL with DGDB integration
- **Duration**: 68.5 seconds
- **Records Processed**: 0 (no new data since last run)
- **Status**: Success
- **DGDB Integration**: Run logged as run_id=3, all validations executed and logged

### Key Validation Results
- **FK Integrity**: PASS (74,624,022 fact_revenue rows checked, 0 orphaned keys)
- **Null Completeness**: PASS (76,794,172 records checked, 0 nulls in critical fields)
- **Date Coverage**: PASS (2,794 distinct date_keys checked, 0 missing from dim_date)
- **Cross-Source Overlap**: WARN (0% overlap between SQL and MongoDB customers - expected due to no MongoDB customer data)

### DGDB Tables Populated
- `ETL_Runs`: 3 runs logged (including this incremental run)
- `Validation_Results`: 12 validation results logged across all runs
