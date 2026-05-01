-- ============================================================
-- Gift Shop Open Dataset - DDL (Run once in SSMS)
-- ============================================================
-- Creates the GiftShopOpenDataset database and PII-free tables.
-- Run this BEFORE running etl_gift_shop_dataset.py
-- ============================================================

-- Step 1: Drop database if exists (kills all connections first)
IF EXISTS (SELECT name FROM sys.databases WHERE name = 'GiftShopOpenDataset')
BEGIN
    ALTER DATABASE [GiftShopOpenDataset] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE [GiftShopOpenDataset];
END
GO

-- Step 2: Create fresh database
CREATE DATABASE [GiftShopOpenDataset];
GO

USE [GiftShopOpenDataset];
GO

-- Step 3: Create tables (NO customer PII)

-- Properties (no employee/customer data)
CREATE TABLE properties (
    property_id     INT PRIMARY KEY,
    name            NVARCHAR(192)   NOT NULL,
    city            NVARCHAR(96)    NOT NULL,
    state           VARCHAR(2)      NOT NULL,
    zip             VARCHAR(10)     NOT NULL
);
GO

-- Products
CREATE TABLE products (
    product_id      INT PRIMARY KEY,
    name            NVARCHAR(192)   NOT NULL,
    price           DECIMAL(10,2)   NOT NULL,
    category        NVARCHAR(96)    NOT NULL
);
GO

-- Transactions - NO customer ID, re-sequenced transaction ID via IDENTITY
CREATE TABLE transactions (
    transaction_id      INT IDENTITY(1,1) PRIMARY KEY,
    transaction_date    DATE            NOT NULL,
    property_id         INT             NOT NULL,
    product_id          INT             NOT NULL,
    quantity            INT             NOT NULL,
    sale_amount         DECIMAL(10,2)   NOT NULL,
    payment_method      VARCHAR(50)     NOT NULL,
    payment_status      VARCHAR(20)     NOT NULL,
    CONSTRAINT FK_txn_property FOREIGN KEY (property_id) REFERENCES properties(property_id),
    CONSTRAINT FK_txn_product  FOREIGN KEY (product_id)  REFERENCES products(product_id)
);
GO

-- Verify
SELECT TABLE_NAME,
       (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS c WHERE c.TABLE_NAME = t.TABLE_NAME) AS Column_Count
FROM INFORMATION_SCHEMA.TABLES t
WHERE TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_NAME;
GO

PRINT '============================================';
PRINT 'GiftShopOpenDataset tables created!';
PRINT '3 tables: properties, products, transactions';
PRINT 'No PII columns. Ready for ETL.';
PRINT '============================================';
GO
