-- ============================================================
-- Sprint 3: Cross-Source Star Schema DDL
-- New tables in HotelDW for gift shop analytics
-- ============================================================

USE HotelDW;
GO

-- ============================================================
-- New Dimension Tables
-- ============================================================

-- DIM_SHOP: Gift shop dimension
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'dim_shop')
CREATE TABLE dim_shop (
    shop_key        INT IDENTITY(1,1) PRIMARY KEY,
    shop_id         INT             NOT NULL,       -- Source: MongoDB hotel.shops.id
    name            NVARCHAR(192)   NOT NULL,
    city            NVARCHAR(96)    NOT NULL,
    state           VARCHAR(10)     NOT NULL,
    zip             VARCHAR(10)     NOT NULL,
    located_at      INT             NULL,            -- property.id link
    date_opened     DATETIME        NULL
);
GO

-- DIM_GIFT_PRODUCT: Gift shop product dimension
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'dim_gift_product')
CREATE TABLE dim_gift_product (
    gift_product_key INT IDENTITY(1,1) PRIMARY KEY,
    product_id       INT             NOT NULL,       -- Source: MongoDB hotel.products.id
    name             NVARCHAR(192)   NOT NULL,
    price            DECIMAL(10,2)   NOT NULL,
    category         NVARCHAR(96)    NOT NULL
);
GO

-- ============================================================
-- New Fact Table
-- ============================================================

-- FACT_GIFT_SHOP_SALES: Gift shop sales fact table
-- Grain: One row per gift shop transaction line item
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'fact_gift_shop_sales')
CREATE TABLE fact_gift_shop_sales (
    gift_sale_key       INT IDENTITY(1,1) PRIMARY KEY,
    date_key            INT             NOT NULL,
    property_key        INT             NOT NULL,
    shop_key            INT             NOT NULL,
    gift_product_key    INT             NOT NULL,
    transaction_id      INT             NOT NULL,       -- Source: MongoDB transactions.id
    sale_amount         DECIMAL(10,2)   NOT NULL,
    quantity            INT             NOT NULL,
    line_total          AS (sale_amount * quantity) PERSISTED,
    payment_method      VARCHAR(50)     NOT NULL,
    payment_status      VARCHAR(20)     NOT NULL,
    CONSTRAINT FK_gift_sales_date       FOREIGN KEY (date_key)          REFERENCES dim_date(date_key),
    CONSTRAINT FK_gift_sales_property   FOREIGN KEY (property_key)      REFERENCES dim_property(property_key),
    CONSTRAINT FK_gift_sales_shop       FOREIGN KEY (shop_key)          REFERENCES dim_shop(shop_key),
    CONSTRAINT FK_gift_sales_product    FOREIGN KEY (gift_product_key)  REFERENCES dim_gift_product(gift_product_key)
);
GO

-- ============================================================
-- Verification: List all tables
-- ============================================================
SELECT TABLE_NAME, 
       (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS c WHERE c.TABLE_NAME = t.TABLE_NAME) AS Column_Count
FROM INFORMATION_SCHEMA.TABLES t 
WHERE TABLE_TYPE = 'BASE TABLE' 
ORDER BY TABLE_NAME;
GO

PRINT '============================================';
PRINT 'Cross-source tables created successfully!';
PRINT '2 new dimension tables + 1 new fact table';
PRINT '============================================';
GO
