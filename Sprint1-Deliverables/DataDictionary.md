# Data Dictionary

This document describes the core tables discovered in the Hospitality Management Database, including primary keys, foreign keys, key columns, and each table’s purpose.

 

## dbo.customer (State Table)

**Primary Key**
- id  

**Columns**
- first_name  
- last_name  
- email  
- phone  
- address  
- city  
- state  
- zip  

**Purpose**  
Stores customer profile and contact information.

 

## dbo.property (State Table)

**Primary Key**
- id  

**Columns**
- name  
- street_address  
- city  
- state  
- zip  
- email  
- website  
- phone  

**Purpose**  
Stores hotel property metadata.

 

## dbo.room_type (Reference Table)

**Primary Key**
- id  

**Columns**
- code  
- description  

**Purpose**  
Reference table defining room categories (e.g., KING, DBL, SUITE).

 

## dbo.property_rooms (State Table)

**Primary Key**
- id  

**Foreign Keys**
- property_id → property.id  
- room_type_id → room_type.id  

**Columns**
- count  
- price  
- resort_fee  

**Purpose**  
Defines room inventory and pricing for each room type at a property.

 

## dbo.event (Event Log)

**Primary Key**
- id  

**Foreign Keys**
- customer_id → customer.id  
- property_id → property.id  

**Columns**
- event_code  
- event_date  

**Purpose**  
Logs operational events such as check-in and check-out.

 

## dbo.transact (Financial Event Log)

**Primary Key**
- id  

**Foreign Keys**
- customer_id → customer.id  
- hotel_id → property.id  

**Columns**
- transaction_date  
- amount  
- payment_method  
- payment_card_stub (nullable)  

**Purpose**  
Logs financial transactions at a property for a customer.

 

## dbo.transaction_line (Transaction Detail Log)

**Primary Key**
- id  

**Foreign Key**
- transaction_id → transact.id  

**Columns**
- description  
- amount_per  
- quantity  

**Purpose**  
Stores line-item details for each transaction.

 