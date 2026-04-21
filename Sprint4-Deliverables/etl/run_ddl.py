"""This is to run Sprint 4 DDL against HotelDW (metadata + new star schema tables)."""
import pyodbc

SQL_SERVER = "cis444.campus-quest.com,25000"
SQL_DW_DB = "HotelDW"
SQL_USER = "sa"
SQL_PASSWORD = "Academic2026U05!"

conn = pyodbc.connect(
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SQL_SERVER};DATABASE={SQL_DW_DB};UID={SQL_USER};PWD={SQL_PASSWORD};"
    f"TrustServerCertificate=yes;Connection Timeout=30;"
)
cursor = conn.cursor()

# Create __ETLMetadata
print("Creating __ETLMetadata...")
cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = '__ETLMetadata')
    CREATE TABLE __ETLMetadata (
        id                  INT IDENTITY(1,1) PRIMARY KEY,
        source_table        VARCHAR(100)    NOT NULL,
        target_table        VARCHAR(100)    NOT NULL,
        last_load_date      DATETIME        NOT NULL,
        last_load_max_id    INT             NULL,
        last_load_max_date  DATETIME        NULL,
        last_load_rows      INT             NOT NULL DEFAULT 0,
        total_rows_loaded   BIGINT          NOT NULL DEFAULT 0,
        status              VARCHAR(20)     NOT NULL DEFAULT 'success',
        notes               NVARCHAR(500)   NULL,
        CONSTRAINT UQ_etl_source_target UNIQUE (source_table, target_table)
    )
""")
conn.commit()
print("  Done.")

# Create dim_employee
print("Creating dim_employee...")
cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'dim_employee')
    CREATE TABLE dim_employee (
        employee_key        INT IDENTITY(1,1) PRIMARY KEY,
        employee_id         INT             NOT NULL,
        first_name          NVARCHAR(96)    NOT NULL,
        last_name           NVARCHAR(96)    NOT NULL,
        email               NVARCHAR(192)   NOT NULL,
        job_title           NVARCHAR(96)    NOT NULL,
        employment_type     VARCHAR(10)     NOT NULL,
        base_salary         INT             NOT NULL,
        property_id         INT             NOT NULL
    )
""")
conn.commit()
print("  Done.")

# Create dim_amenity
print("Creating dim_amenity...")
cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'dim_amenity')
    CREATE TABLE dim_amenity (
        amenity_key             INT IDENTITY(1,1) PRIMARY KEY,
        amenity_id              INT             NOT NULL,
        amenity_name            NVARCHAR(100)   NOT NULL,
        amenity_key_code        VARCHAR(50)     NOT NULL,
        group_key               VARCHAR(50)     NULL,
        group_display_name      NVARCHAR(100)   NULL
    )
""")
conn.commit()
print("  Done.")

# Create fact_payroll
print("Creating fact_payroll...")
cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'fact_payroll')
    CREATE TABLE fact_payroll (
        payroll_key         INT IDENTITY(1,1) PRIMARY KEY,
        payroll_id          INT             NOT NULL,
        date_key            INT             NOT NULL,
        property_key        INT             NOT NULL,
        employee_key        INT             NOT NULL,
        pay_period_start    DATE            NOT NULL,
        pay_period_end      DATE            NOT NULL,
        hours_regular       DECIMAL(10,2)   NOT NULL,
        hours_overtime      DECIMAL(10,2)   NOT NULL,
        gross_pay           INT             NOT NULL,
        federal_tax         INT             NOT NULL,
        state_tax           INT             NOT NULL,
        social_security     INT             NOT NULL,
        medicare            INT             NOT NULL,
        net_pay             INT             NOT NULL,
        total_deductions    AS (federal_tax + state_tax + social_security + medicare) PERSISTED,
        CONSTRAINT FK_payroll_date       FOREIGN KEY (date_key)       REFERENCES dim_date(date_key),
        CONSTRAINT FK_payroll_property   FOREIGN KEY (property_key)   REFERENCES dim_property(property_key),
        CONSTRAINT FK_payroll_employee   FOREIGN KEY (employee_key)   REFERENCES dim_employee(employee_key)
    )
""")
conn.commit()
print("  Done.")

# Create fact_property_amenity
print("Creating fact_property_amenity...")
cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'fact_property_amenity')
    CREATE TABLE fact_property_amenity (
        property_amenity_key INT IDENTITY(1,1) PRIMARY KEY,
        property_key         INT             NOT NULL,
        amenity_key          INT             NOT NULL,
        CONSTRAINT FK_propamenity_property FOREIGN KEY (property_key) REFERENCES dim_property(property_key),
        CONSTRAINT FK_propamenity_amenity  FOREIGN KEY (amenity_key)  REFERENCES dim_amenity(amenity_key)
    )
""")
conn.commit()
print("  Done.")

# Verify
print("\nAll tables in HotelDW:")
cursor.execute("""
    SELECT TABLE_NAME, 
           (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS c WHERE c.TABLE_NAME = t.TABLE_NAME) AS cols
    FROM INFORMATION_SCHEMA.TABLES t 
    WHERE TABLE_TYPE = 'BASE TABLE' 
    ORDER BY TABLE_NAME
""")
for r in cursor.fetchall():
    print(f"  {r[0]:30s} | {r[1]} columns")

conn.close()
print("\nDDL complete!")
