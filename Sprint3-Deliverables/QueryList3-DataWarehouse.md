# Query List 3: Data Warehouse Queries

These queries run against the **populated HotelDW** data warehouse, demonstrating the value of the star schema design. Each query is simpler than the equivalent query against raw source data because the star schema handles denormalization and surrogate keys.

---

## 1. Revenue Star Schema - Monthly Revenue by Property

### Business Question
Which hotel properties generate the most monthly revenue, and how does revenue trend over time?

### SQL Query

```sql
USE HotelDW;

SELECT 
    dp.name AS property_name,
    dd.year,
    dd.month_name,
    dd.month_num,
    COUNT(*) AS line_item_count,
    SUM(fr.amount_per * fr.quantity) AS total_revenue,
    AVG(fr.amount_per * fr.quantity) AS avg_line_total
FROM fact_revenue fr
JOIN dim_property dp ON fr.property_key = dp.property_key
JOIN dim_date dd ON fr.date_key = dd.date_key
GROUP BY dp.name, dd.year, dd.month_name, dd.month_num
ORDER BY dd.year, dd.month_num, total_revenue DESC;
```

### Interpretation
This query shows monthly revenue by property from the `fact_revenue` table. Compared to the Sprint 1 raw query (which required joining `transact`, `transaction_line`, and `property`), this star schema query uses simple joins on surrogate keys and pre-denormalized data. It helps identify top-performing properties and seasonal revenue trends.

---

## 2. Check-in Star Schema - Weekend vs. Weekday Check-ins by Property

### Business Question
How do check-in volumes compare between weekdays and weekends at each property?

### SQL Query

```sql
USE HotelDW;

SELECT 
    dp.name AS property_name,
    dp.city,
    dp.state,
    CASE WHEN dd.is_weekend = 1 THEN 'Weekend' ELSE 'Weekday' END AS day_type,
    COUNT(*) AS checkin_count
FROM fact_checkin fc
JOIN dim_property dp ON fc.property_key = dp.property_key
JOIN dim_date dd ON fc.date_key = dd.date_key
GROUP BY dp.name, dp.city, dp.state, dd.is_weekend
ORDER BY dp.name, dd.is_weekend;
```

### Interpretation
This query leverages the `dim_date.is_weekend` flag to analyze operational demand patterns. It reveals which properties are business-travel-heavy (more weekday check-ins) vs. leisure-oriented (more weekend check-ins). This insight supports staffing and pricing decisions.

---

## 3. Cross-Source - Hotel Revenue vs. Gift Shop Revenue by Property

### Business Question
Do properties with higher hotel room revenue also generate higher gift shop sales? What is the relationship between the two revenue streams?

### SQL Query

```sql
USE HotelDW;

SELECT 
    dp.name AS property_name,
    dp.city,
    dp.state,
    ISNULL(hotel_rev.hotel_revenue, 0) AS hotel_revenue,
    ISNULL(gift_rev.gift_shop_revenue, 0) AS gift_shop_revenue,
    ISNULL(hotel_rev.hotel_revenue, 0) + ISNULL(gift_rev.gift_shop_revenue, 0) AS combined_revenue,
    CASE 
        WHEN ISNULL(hotel_rev.hotel_revenue, 0) > 0 
        THEN ROUND(ISNULL(gift_rev.gift_shop_revenue, 0) / hotel_rev.hotel_revenue * 100, 2)
        ELSE 0 
    END AS gift_pct_of_hotel
FROM dim_property dp
LEFT JOIN (
    SELECT property_key, SUM(amount_per * quantity) AS hotel_revenue
    FROM fact_revenue
    GROUP BY property_key
) hotel_rev ON dp.property_key = hotel_rev.property_key
LEFT JOIN (
    SELECT property_key, SUM(sale_amount * quantity) AS gift_shop_revenue
    FROM fact_gift_shop_sales
    GROUP BY property_key
) gift_rev ON dp.property_key = gift_rev.property_key
WHERE ISNULL(hotel_rev.hotel_revenue, 0) > 0 
   OR ISNULL(gift_rev.gift_shop_revenue, 0) > 0
ORDER BY combined_revenue DESC;
```

### Interpretation
This cross-source query combines data from **both** the hotel operations (fact_revenue, sourced from SQL Server) and the gift shop (fact_gift_shop_sales, sourced from MongoDB) through their shared `dim_property` dimension. The `gift_pct_of_hotel` metric shows what percentage of hotel revenue each property captures through its gift shop. This is only possible because the data warehouse integrates both source systems into a unified model with a shared property dimension.

---

## 4. Cross-Source - Top Gift Shop Product Categories at Each Property

### Business Question
What are the best-selling gift shop product categories at each hotel property?

### SQL Query

```sql
USE HotelDW;

SELECT 
    dp.name AS property_name,
    dgp.category AS product_category,
    COUNT(*) AS items_sold,
    SUM(gs.sale_amount * gs.quantity) AS category_revenue
FROM fact_gift_shop_sales gs
JOIN dim_property dp ON gs.property_key = dp.property_key
JOIN dim_gift_product dgp ON gs.gift_product_key = dgp.gift_product_key
GROUP BY dp.name, dgp.category
ORDER BY dp.name, category_revenue DESC;
```

### Interpretation
This query shows which product categories perform best at each hotel's gift shop. Combined with check-in data from Query 2, property managers can understand whether high-traffic properties also drive higher sales in specific categories (e.g., souvenirs vs. snacks), enabling targeted inventory decisions.

---

## Query Complexity Comparison

| Aspect | Raw Source Query | Star Schema Query |
|---|---|---|
| Tables/joins | 3-4 tables with complex FK chains | 2-3 tables with simple surrogate key joins |
| Date filtering | `YEAR()`, `MONTH()` functions on raw dates | Direct columns: `dd.year`, `dd.month_name`, `dd.is_weekend` |
| Cross-source | Impossible (different DB systems) | Simple JOINs via shared dim_property |
| Aggregation | Must compute on raw, non-denormalized data | Pre-flattened fact rows, straightforward SUM/COUNT |

## Population Approach

The Sprint 2 star schemas (fact_revenue, fact_checkin + dimensions) are populated using **SQL INSERT INTO...SELECT** statements (`Populate-HotelDW.sql`) that run entirely server-side since both the `Hotel` source DB and `HotelDW` warehouse are on the same SQL Server instance. This avoids the overhead of pulling data through Python.

The cross-source schema (fact_gift_shop_sales) is populated using a **Python ETL** (`etl_cross_source.py`) because the gift shop data lives in MongoDB and must be extracted via `pymongo` before loading into SQL Server.
