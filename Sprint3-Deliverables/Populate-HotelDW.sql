-- ============================================================
-- Sprint 3: Populate HotelDW Star Schemas
-- Uses INSERT INTO...SELECT from Hotel DB (same server)
-- Run this in SSMS connected to the SQL Server instance
-- ============================================================

USE HotelDW;
GO

-- ============================================================
-- Step 1: Clear all fact tables first (FK constraints)
-- ============================================================
PRINT '--- Step 1: Clearing fact tables ---';

DELETE FROM fact_revenue;
DELETE FROM fact_checkin;
PRINT 'Fact tables cleared.';
GO

-- ============================================================
-- Step 2: Clear and reload dimension tables (except dim_date)
-- ============================================================
PRINT '--- Step 2: Clearing dimension tables ---';

DELETE FROM dim_property;
DELETE FROM dim_customer;
DELETE FROM dim_product;

DBCC CHECKIDENT('dim_property', RESEED, 0);
DBCC CHECKIDENT('dim_customer', RESEED, 0);
DBCC CHECKIDENT('dim_product', RESEED, 0);
PRINT 'Dimension tables cleared.';
GO

-- ============================================================
-- Step 3: Populate dim_date (if empty)
-- ============================================================
IF NOT EXISTS (SELECT 1 FROM dim_date)
BEGIN
    PRINT '--- Step 3: Populating dim_date (2020-2030) ---';
    DECLARE @start DATE = '2020-01-01';
    DECLARE @end   DATE = '2030-12-31';
    DECLARE @date  DATE = @start;

    WHILE @date <= @end
    BEGIN
        INSERT INTO dim_date (date_key, full_date, day_of_week, day_of_month,
                              month_num, month_name, quarter, year, is_weekend)
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
    PRINT 'dim_date populated.';
END
ELSE
    PRINT '--- Step 3: dim_date already populated, skipping ---';
GO

-- ============================================================
-- Step 4: Populate dim_property
-- ============================================================
PRINT '--- Step 4: Populating dim_property ---';

INSERT INTO dim_property (property_id, name, street_address, city, state, zip)
SELECT id, name, street_address, city, state, zip
FROM Hotel.dbo.property
ORDER BY id;

PRINT 'dim_property populated.';
SELECT 'dim_property' AS [Table], COUNT(*) AS [Rows] FROM dim_property;
GO

-- ============================================================
-- Step 5: Populate dim_customer
-- ============================================================
PRINT '--- Step 5: Populating dim_customer ---';

INSERT INTO dim_customer (customer_id, first_name, last_name, email, city, state, zip)
SELECT id, first_name, last_name, email, city, state, zip
FROM Hotel.dbo.customer
ORDER BY id;

PRINT 'dim_customer populated.';
SELECT 'dim_customer' AS [Table], COUNT(*) AS [Rows] FROM dim_customer;
GO

-- ============================================================
-- Step 6: Populate dim_product
-- ============================================================
PRINT '--- Step 6: Populating dim_product ---';

INSERT INTO dim_product (description, category)
SELECT DISTINCT description, NULL
FROM Hotel.dbo.transaction_line
ORDER BY description;

PRINT 'dim_product populated.';
SELECT 'dim_product' AS [Table], COUNT(*) AS [Rows] FROM dim_product;
GO

-- ============================================================
-- Step 7: Populate fact_revenue
-- Grain: one row per transaction line item
-- Joins transact + transaction_line + dimension lookups
-- ============================================================
PRINT '--- Step 7: Populating fact_revenue (this may take a few minutes) ---';

INSERT INTO fact_revenue (date_key, property_key, customer_key, product_key,
                          transaction_id, amount_per, quantity, payment_method)
SELECT
    CAST(FORMAT(t.transaction_date, 'yyyyMMdd') AS INT) AS date_key,
    dp.property_key,
    dc.customer_key,
    dpr.product_key,
    t.id AS transaction_id,
    tl.amount_per,
    tl.quantity,
    t.payment_method
FROM Hotel.dbo.transact t
JOIN Hotel.dbo.transaction_line tl ON tl.transaction_id = t.id
JOIN dim_property dp ON dp.property_id = t.hotel_id
JOIN dim_customer dc ON dc.customer_id = t.customer_id
JOIN dim_product dpr ON dpr.description = tl.description;

PRINT 'fact_revenue populated.';
SELECT 'fact_revenue' AS [Table], COUNT(*) AS [Rows] FROM fact_revenue;
GO

-- ============================================================
-- Step 8: Populate fact_checkin
-- Grain: one row per check-in event
-- ============================================================
PRINT '--- Step 8: Populating fact_checkin ---';

INSERT INTO fact_checkin (date_key, property_key, customer_key, event_id, event_code)
SELECT
    CAST(FORMAT(e.event_date, 'yyyyMMdd') AS INT) AS date_key,
    dp.property_key,
    dc.customer_key,
    e.id AS event_id,
    e.event_code
FROM Hotel.dbo.event e
JOIN dim_property dp ON dp.property_id = e.property_id
JOIN dim_customer dc ON dc.customer_id = e.customer_id
WHERE e.event_code = 'checkin';

PRINT 'fact_checkin populated.';
SELECT 'fact_checkin' AS [Table], COUNT(*) AS [Rows] FROM fact_checkin;
GO

-- ============================================================
-- Step 9: Final Verification
-- ============================================================
PRINT '============================================';
PRINT 'VERIFICATION: All HotelDW Table Counts';
PRINT '============================================';

SELECT 'dim_date' AS [Table], COUNT(*) AS [Rows] FROM dim_date
UNION ALL SELECT 'dim_property', COUNT(*) FROM dim_property
UNION ALL SELECT 'dim_customer', COUNT(*) FROM dim_customer
UNION ALL SELECT 'dim_product', COUNT(*) FROM dim_product
UNION ALL SELECT 'fact_revenue', COUNT(*) FROM fact_revenue
UNION ALL SELECT 'fact_checkin', COUNT(*) FROM fact_checkin;

PRINT '============================================';
PRINT 'HotelDW population complete!';
PRINT '============================================';
GO
