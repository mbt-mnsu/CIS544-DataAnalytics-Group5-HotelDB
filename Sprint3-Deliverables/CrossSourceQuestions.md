# Cross-Source Business Questions

These business questions require data from **both** the hotel operations database (SQL Server) and the gift shop database (MongoDB). They cannot be answered using only one data source.

---

## Question 1: Do Properties With Higher Hotel Revenue Also Generate Higher Gift Shop Sales?

### Business Question
Is there a correlation between a property's total hotel room revenue and its on-site gift shop revenue? Do high-performing hotels also drive higher gift shop sales?

### Data Needed

**From Hotel Operations (SQL Server):**
- `transact` table - transaction amounts per hotel property
- `property` table - property names and locations

**From Gift Shop (MongoDB):**
- `transactions` collection - gift shop transaction totals per store
- `shops` collection - which shop is located at which property

### How the Data Connects
The `shops` collection in MongoDB has a `located_at` field that maps to the `property.id` in SQL Server. This is the linking field that connects gift shop revenue to hotel property performance. By aggregating hotel revenue from `transact.amount` per `hotel_id` and gift shop revenue from `transactions.total` per `store_id`, we can compare both revenue streams at the property level.

### Analytics Type
**Diagnostic** - Helps understand whether hotel performance drives ancillary revenue.

---

## Question 2: What Are the Most Popular Gift Shop Product Categories at High vs. Low-Occupancy Properties?

### Business Question
Do properties with more guest check-ins see different gift shop purchase patterns? Are certain product categories more popular at busier hotels?

### Data Needed

**From Hotel Operations (SQL Server):**
- `event` table - check-in events per property (used to measure occupancy/traffic)
- `property` table - property details

**From Gift Shop (MongoDB):**
- `transactions` collection - line items showing what products were purchased at each store
- `products` collection - product categories and names
- `shops` collection - store-to-property mapping

### How the Data Connects
The `shops.located_at` field links gift shops to hotel `property.id`. Using `event.property_id` with `event_code = 'checkin'`, we can calculate check-in volume per property (as a proxy for occupancy). Then by joining shop sales data through the `located_at → property_id` mapping, we can compare product category sales at high-traffic vs. low-traffic properties.

### Analytics Type
**Diagnostic / Descriptive** - Describes purchase patterns and diagnoses what drives product category popularity at different property types.

---

## Data Integration Challenge

> **Note:** Customers in the hotel system (`Hotel.dbo.customer`) and the gift shop system (`hotel.customers` in MongoDB) are **partially duplicated** with no direct ID link. The two systems use different customer IDs. In these questions, we focus on **property-level** analysis (linking via `shops.located_at → property.id`) rather than customer-level matching, which avoids the customer ID mismatch problem. Customer-level cross-source analysis will be addressed in Sprint 4 with fuzzy matching techniques.
