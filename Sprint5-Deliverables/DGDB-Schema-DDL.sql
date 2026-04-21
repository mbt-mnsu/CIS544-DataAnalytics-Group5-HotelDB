-- ============================================================
-- Sprint 5: Data Governance Database (DGDB) Schema Reference
-- ============================================================
-- This DDL documents the tables auto-created by the ETL pipeline
-- via SQLAlchemy ORM (DGDBClient). Do NOT need to run this
-- script manually - running etl_sprint5.py handles creation
-- automatically on first execution.
--
-- Included for portfolio documentation purposes.
-- ============================================================

-- Database: HotelDGDB
-- Created automatically by DGDBClient.__init__() if not exists

-- ============================================================
-- Table: ETL_Runs
-- Logs each execution of the ETL pipeline
-- ============================================================
-- CREATE DATABASE HotelDGDB;
-- GO
-- USE HotelDGDB;
-- GO

CREATE TABLE ETL_Runs (
    run_id              INT IDENTITY(1,1)   PRIMARY KEY,
    job_name            VARCHAR(200)        NOT NULL,
    start_time          DATETIME            NOT NULL,
    end_time            DATETIME            NULL,
    duration_seconds    FLOAT               NULL,
    status              VARCHAR(20)         NOT NULL DEFAULT 'Running',
    records_processed   INT                 NOT NULL DEFAULT 0,
    records_rejected    INT                 NOT NULL DEFAULT 0,
    notes               TEXT                NULL
);
GO

-- ============================================================
-- Table: Validation_Results
-- Logs outcomes of data quality checks
-- ============================================================
CREATE TABLE Validation_Results (
    result_id           INT IDENTITY(1,1)   PRIMARY KEY,
    run_id              INT                 NOT NULL,
    rule_name           VARCHAR(100)        NOT NULL,
    rule_description    VARCHAR(500)        NOT NULL,
    executed_at         DATETIME            NOT NULL,
    records_checked     INT                 NOT NULL DEFAULT 0,
    records_passed      INT                 NOT NULL DEFAULT 0,
    records_failed      INT                 NOT NULL DEFAULT 0,
    CONSTRAINT FK_validation_run FOREIGN KEY (run_id) REFERENCES ETL_Runs(run_id)
);
GO

PRINT '============================================';
PRINT 'HotelDGDB schema reference:';
PRINT '  ETL_Runs           — ETL execution log';
PRINT '  Validation_Results — Data quality check results';
PRINT '============================================';
GO
