-- ============================================================
-- Sprint 4: New Star Schema DDL
-- Employee/Payroll/Amenity schemas in HotelDW
-- ============================================================

USE HotelDW;
GO

-- ============================================================
-- New Dimension Tables
-- ============================================================

-- DIM_EMPLOYEE: Employee dimension
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'dim_employee')
CREATE TABLE dim_employee (
    employee_key        INT IDENTITY(1,1) PRIMARY KEY,
    employee_id         INT             NOT NULL,       -- Source: Hotel.dbo.employee.id
    first_name          NVARCHAR(96)    NOT NULL,
    last_name           NVARCHAR(96)    NOT NULL,
    email               NVARCHAR(192)   NOT NULL,
    job_title           NVARCHAR(96)    NOT NULL,
    employment_type     VARCHAR(10)     NOT NULL,       -- full_time, part_time
    base_salary         INT             NOT NULL,       -- Annual salary in cents
    property_id         INT             NOT NULL        -- Source property assignment
);
GO

-- DIM_AMENITY: Amenity dimension
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'dim_amenity')
CREATE TABLE dim_amenity (
    amenity_key             INT IDENTITY(1,1) PRIMARY KEY,
    amenity_id              INT             NOT NULL,       -- Source: Hotel.dbo.amenity.id
    amenity_name            NVARCHAR(100)   NOT NULL,       -- Source: display_name
    amenity_key_code        VARCHAR(50)     NOT NULL,       -- Source: key (e.g., 'restaurant')
    group_key               VARCHAR(50)     NULL,           -- Source: group_key (e.g., 'dining')
    group_display_name      NVARCHAR(100)   NULL            -- Source: group_display_name
);
GO

-- ============================================================
-- New Fact Tables
-- ============================================================

-- FACT_PAYROLL: Payroll fact table
-- Grain: One row per paycheck (biweekly pay period per employee)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'fact_payroll')
CREATE TABLE fact_payroll (
    payroll_key         INT IDENTITY(1,1) PRIMARY KEY,
    payroll_id          INT             NOT NULL,       -- Source: Hotel.dbo.payroll.id
    date_key            INT             NOT NULL,       -- pay_date → dim_date
    property_key        INT             NOT NULL,
    employee_key        INT             NOT NULL,
    pay_period_start    DATE            NOT NULL,
    pay_period_end      DATE            NOT NULL,
    hours_regular       DECIMAL(10,2)   NOT NULL,
    hours_overtime      DECIMAL(10,2)   NOT NULL,
    gross_pay           INT             NOT NULL,       -- In cents
    federal_tax         INT             NOT NULL,       -- In cents
    state_tax           INT             NOT NULL,       -- In cents
    social_security     INT             NOT NULL,       -- In cents
    medicare            INT             NOT NULL,       -- In cents
    net_pay             INT             NOT NULL,       -- In cents
    total_deductions    AS (federal_tax + state_tax + social_security + medicare) PERSISTED,
    CONSTRAINT FK_payroll_date       FOREIGN KEY (date_key)       REFERENCES dim_date(date_key),
    CONSTRAINT FK_payroll_property   FOREIGN KEY (property_key)   REFERENCES dim_property(property_key),
    CONSTRAINT FK_payroll_employee   FOREIGN KEY (employee_key)   REFERENCES dim_employee(employee_key)
);
GO

-- FACT_PROPERTY_AMENITY: Bridge/fact table linking properties to their amenities
-- Grain: One row per property-amenity assignment
-- This enables queries like "properties with X amenities generate Y revenue"
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'fact_property_amenity')
CREATE TABLE fact_property_amenity (
    property_amenity_key INT IDENTITY(1,1) PRIMARY KEY,
    property_key         INT             NOT NULL,
    amenity_key          INT             NOT NULL,
    CONSTRAINT FK_propamenity_property FOREIGN KEY (property_key) REFERENCES dim_property(property_key),
    CONSTRAINT FK_propamenity_amenity  FOREIGN KEY (amenity_key)  REFERENCES dim_amenity(amenity_key)
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
PRINT 'Sprint 4 star schema tables created!';
PRINT '  2 new dimension tables: dim_employee, dim_amenity';
PRINT '  2 new fact tables: fact_payroll, fact_property_amenity';
PRINT '============================================';
GO
