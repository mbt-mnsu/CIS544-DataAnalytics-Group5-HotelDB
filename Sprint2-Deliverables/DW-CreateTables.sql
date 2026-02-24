-- ============================================================
-- Sprint 2: Data Warehouse DDL
-- Hotel Data Warehouse (HotelDW)


-- Step 1: Create the Data Warehouse database
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'HotelDW')
BEGIN
    CREATE DATABASE HotelDW;
END
GO

USE HotelDW;
GO

-- ============================================================
-- Step 2: Dimension Tables
-- ============================================================

-- DIM_DATE: Date dimension for time-based analysis
-- date_key uses YYYYMMDD integer format (e.g., 20250115)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'dim_date')
CREATE TABLE dim_date (
    date_key        INT             PRIMARY KEY,
    full_date       DATE            NOT NULL,
    day_of_week     VARCHAR(10)     NOT NULL,
    day_of_month    INT             NOT NULL,
    month_num       INT             NOT NULL,
    month_name      VARCHAR(10)     NOT NULL,
    quarter         INT             NOT NULL,
    year            INT             NOT NULL,
    is_weekend      BIT             NOT NULL
);
GO

-- DIM_PROPERTY: Hotel property dimension
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'dim_property')
CREATE TABLE dim_property (
    property_key    INT IDENTITY(1,1) PRIMARY KEY,
    property_id     INT             NOT NULL,       -- Source: Hotel.dbo.property.id
    name            NVARCHAR(192)   NOT NULL,
    street_address  NVARCHAR(192)   NOT NULL,
    city            NVARCHAR(96)    NOT NULL,
    state           VARCHAR(2)      NOT NULL,
    zip             VARCHAR(10)     NOT NULL
);
GO

-- DIM_CUSTOMER: Customer dimension
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'dim_customer')
CREATE TABLE dim_customer (
    customer_key    INT IDENTITY(1,1) PRIMARY KEY,
    customer_id     INT             NOT NULL,       -- Source: Hotel.dbo.customer.id
    first_name      NVARCHAR(96)    NOT NULL,
    last_name       NVARCHAR(96)    NOT NULL,
    email           NVARCHAR(192)   NOT NULL,
    city            NVARCHAR(96)    NOT NULL,
    state           VARCHAR(2)      NOT NULL,
    zip             VARCHAR(10)     NOT NULL
);
GO

-- DIM_PRODUCT: Product/service dimension (from transaction line descriptions)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'dim_product')
CREATE TABLE dim_product (
    product_key     INT IDENTITY(1,1) PRIMARY KEY,
    description     NVARCHAR(192)   NOT NULL,       -- Source: Hotel.dbo.transaction_line.description
    category        VARCHAR(50)     NULL             -- Can be derived/assigned later
);
GO

-- ============================================================
-- Step 3: Fact Tables
-- ============================================================

-- FACT_REVENUE: Revenue fact table
-- Grain: One row per transaction line item
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'fact_revenue')
CREATE TABLE fact_revenue (
    revenue_key     INT IDENTITY(1,1) PRIMARY KEY,
    date_key        INT             NOT NULL,
    property_key    INT             NOT NULL,
    customer_key    INT             NOT NULL,
    product_key     INT             NOT NULL,
    transaction_id  INT             NOT NULL,       -- Source reference: Hotel.dbo.transact.id
    amount_per      DECIMAL(10,2)   NOT NULL,
    quantity        INT             NOT NULL,
    line_total      AS (amount_per * quantity) PERSISTED,  -- Computed column
    payment_method  VARCHAR(20)     NOT NULL,
    CONSTRAINT FK_revenue_date      FOREIGN KEY (date_key)      REFERENCES dim_date(date_key),
    CONSTRAINT FK_revenue_property  FOREIGN KEY (property_key)  REFERENCES dim_property(property_key),
    CONSTRAINT FK_revenue_customer  FOREIGN KEY (customer_key)  REFERENCES dim_customer(customer_key),
    CONSTRAINT FK_revenue_product   FOREIGN KEY (product_key)   REFERENCES dim_product(product_key)
);
GO

-- FACT_CHECKIN: Check-in fact table
-- Grain: One row per check-in event
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'fact_checkin')
CREATE TABLE fact_checkin (
    checkin_key     INT IDENTITY(1,1) PRIMARY KEY,
    date_key        INT             NOT NULL,
    property_key    INT             NOT NULL,
    customer_key    INT             NOT NULL,
    event_id        INT             NOT NULL,       -- Source reference: Hotel.dbo.event.id
    event_code      VARCHAR(20)     NOT NULL,
    CONSTRAINT FK_checkin_date      FOREIGN KEY (date_key)      REFERENCES dim_date(date_key),
    CONSTRAINT FK_checkin_property  FOREIGN KEY (property_key)  REFERENCES dim_property(property_key),
    CONSTRAINT FK_checkin_customer  FOREIGN KEY (customer_key)  REFERENCES dim_customer(customer_key)
);
GO

-- ============================================================
-- Step 4: Populate dim_date (generate dates from 2020 to 2030)
-- ============================================================
IF NOT EXISTS (SELECT 1 FROM dim_date)
BEGIN
    DECLARE @start DATE = '2020-01-01';
    DECLARE @end   DATE = '2030-12-31';
    DECLARE @date  DATE = @start;

    WHILE @date <= @end
    BEGIN
        INSERT INTO dim_date (date_key, full_date, day_of_week, day_of_month, month_num, month_name, quarter, year, is_weekend)
        VALUES (
            CAST(FORMAT(@date, 'yyyyMMdd') AS INT),
            @date,
            DATENAME(WEEKDAY, @date),
            DAY(@date),
            MONTH(@date),
            DATENAME(MONTH, @date),
            DATEPART(QUARTER, @date),
            YEAR(@date),
            CASE WHEN DATEPART(WEEKDAY, @date) IN (1, 7) THEN 1 ELSE 0 END
        );
        SET @date = DATEADD(DAY, 1, @date);
    END

    PRINT 'dim_date populated with dates from 2020-01-01 to 2030-12-31';
END
GO

-- ============================================================
-- Verification: List all tables created
-- ============================================================
SELECT TABLE_NAME, 
       (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS c WHERE c.TABLE_NAME = t.TABLE_NAME) AS Column_Count
FROM INFORMATION_SCHEMA.TABLES t 
WHERE TABLE_TYPE = 'BASE TABLE' 
ORDER BY TABLE_NAME;
GO

PRINT '============================================';
PRINT 'HotelDW database created successfully!';
PRINT '4 dimension tables + 2 fact tables';
PRINT 'dim_date has been pre-populated.';
PRINT '============================================';
GO
