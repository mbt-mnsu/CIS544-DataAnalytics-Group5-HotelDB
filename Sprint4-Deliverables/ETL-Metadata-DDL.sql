-- ============================================================
-- Sprint 4: ETL Metadata Tracking Table
-- Tracks incremental ETL load state for each source table
-- ============================================================

USE HotelDW;
GO

-- ETL Metadata Table
-- Tracks the last successful load for each source → target pipeline
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = '__ETLMetadata')
CREATE TABLE __ETLMetadata (
    id                  INT IDENTITY(1,1) PRIMARY KEY,
    source_table        VARCHAR(100)    NOT NULL,       -- e.g., 'Hotel.dbo.transact', 'mongo.transactions'
    target_table        VARCHAR(100)    NOT NULL,       -- e.g., 'fact_revenue', 'fact_gift_shop_sales'
    last_load_date      DATETIME        NOT NULL,       -- Timestamp of the last successful load
    last_load_max_id    INT             NULL,            -- Max source ID loaded (for ID-based incremental)
    last_load_max_date  DATETIME        NULL,            -- Max source date loaded (for date-based incremental)
    last_load_rows      INT             NOT NULL DEFAULT 0,  -- Rows loaded in last run
    total_rows_loaded   BIGINT          NOT NULL DEFAULT 0,  -- Cumulative rows loaded
    status              VARCHAR(20)     NOT NULL DEFAULT 'success',  -- success, failed, running
    notes               NVARCHAR(500)   NULL,
    CONSTRAINT UQ_etl_source_target UNIQUE (source_table, target_table)
);
GO

PRINT '============================================';
PRINT '__ETLMetadata table created successfully!';
PRINT '============================================';
GO
