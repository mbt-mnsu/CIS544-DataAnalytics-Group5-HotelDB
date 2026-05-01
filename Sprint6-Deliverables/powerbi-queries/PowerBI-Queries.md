# Power BI - Dashboard SQL Queries

> All queries target **HotelDW** on `cis444.campus-quest.com,25000` (sa / Academic2026U05!)

---

## Page 1: Executive Overview

### KPI - Total Revenue & Transactions
```sql
SELECT SUM(fr.amount_per * fr.quantity) AS total_revenue,
       COUNT(DISTINCT fr.transaction_id) AS total_transactions
FROM fact_revenue fr;
```

### KPI - Total Check-ins
```sql
SELECT COUNT(*) AS total_checkins FROM fact_checkin;
```

### KPI - YoY Revenue Change (Computed Measure)
```sql
SELECT
    SUM(CASE WHEN dd.year = (SELECT MAX(year) FROM dim_date) THEN fr.amount_per * fr.quantity ELSE 0 END) AS curr_year_rev,
    SUM(CASE WHEN dd.year = (SELECT MAX(year) FROM dim_date) - 1 THEN fr.amount_per * fr.quantity ELSE 0 END) AS prev_year_rev
FROM fact_revenue fr JOIN dim_date dd ON fr.date_key = dd.date_key;
```
**Formula:** `(curr_year_rev - prev_year_rev) / prev_year_rev * 100`

### Viz 1 - Monthly Revenue Trend (Line Chart)
```sql
SELECT dd.year, dd.month_num, dd.month_name, SUM(fr.amount_per * fr.quantity) AS revenue
FROM fact_revenue fr JOIN dim_date dd ON fr.date_key = dd.date_key
GROUP BY dd.year, dd.month_num, dd.month_name
ORDER BY dd.year, dd.month_num;
```

### Viz 2 - Payment Method Distribution (Donut Chart)
```sql
SELECT fr.payment_method, COUNT(*) AS cnt, SUM(fr.amount_per * fr.quantity) AS revenue
FROM fact_revenue fr GROUP BY fr.payment_method ORDER BY revenue DESC;
```

### Viz 3 - Top N Properties by Revenue (Horizontal Bar)
```sql
SELECT TOP 10 dp.name AS property_name, SUM(fr.amount_per * fr.quantity) AS revenue
FROM fact_revenue fr JOIN dim_property dp ON fr.property_key = dp.property_key
GROUP BY dp.name ORDER BY revenue DESC;
```

---

## Page 2: Operations & Staffing

### KPI - Payroll & Employees
```sql
SELECT SUM(fp.gross_pay)/100.0 AS total_payroll, COUNT(DISTINCT fp.employee_key) AS emp_count
FROM fact_payroll fp;
```

### Viz 4 - Labor Cost % by Property (Bar Chart, Computed Measure)
```sql
SELECT dp.name, ISNULL(SUM(fp.gross_pay),0)/100.0 AS payroll, ISNULL(rev.revenue,0) AS revenue
FROM dim_property dp
LEFT JOIN fact_payroll fp ON dp.property_key = fp.property_key
LEFT JOIN (SELECT property_key, SUM(amount_per*quantity) AS revenue FROM fact_revenue GROUP BY property_key) rev ON dp.property_key = rev.property_key
GROUP BY dp.name, rev.revenue HAVING ISNULL(rev.revenue,0) > 0
ORDER BY payroll/NULLIF(rev.revenue,0) DESC;
```
**Computed Column:** `labor_cost_pct = payroll / revenue * 100`

### Viz 5 - Weekend vs. Weekday Check-ins (Grouped Bar)
```sql
SELECT dp.name, CASE WHEN dd.is_weekend=1 THEN 'Weekend' ELSE 'Weekday' END AS day_type, COUNT(*) AS checkins
FROM fact_checkin fc
JOIN dim_property dp ON fc.property_key = dp.property_key
JOIN dim_date dd ON fc.date_key = dd.date_key
GROUP BY dp.name, dd.is_weekend ORDER BY checkins DESC;
```

---

## Page 3: Gift Shop Analytics

### KPI - Gift Shop Revenue
```sql
SELECT SUM(gs.sale_amount * gs.quantity) AS gift_shop_revenue FROM fact_gift_shop_sales gs;
```

### Viz 6 - Hotel vs Gift Shop Revenue by Property (Grouped Bar)
```sql
SELECT dp.name,
    ISNULL(h.hotel_rev,0) AS hotel_revenue, ISNULL(g.gift_rev,0) AS gift_shop_revenue
FROM dim_property dp
LEFT JOIN (SELECT property_key, SUM(amount_per*quantity) AS hotel_rev FROM fact_revenue GROUP BY property_key) h ON dp.property_key = h.property_key
LEFT JOIN (SELECT property_key, SUM(sale_amount*quantity) AS gift_rev FROM fact_gift_shop_sales GROUP BY property_key) g ON dp.property_key = g.property_key
WHERE ISNULL(h.hotel_rev,0)+ISNULL(g.gift_rev,0) > 0
ORDER BY ISNULL(h.hotel_rev,0)+ISNULL(g.gift_rev,0) DESC;
```

### Viz 7 - Gift Shop by Category (Horizontal Bar)
```sql
SELECT dgp.category, SUM(gs.sale_amount*gs.quantity) AS revenue, COUNT(*) AS items_sold
FROM fact_gift_shop_sales gs
JOIN dim_gift_product dgp ON gs.gift_product_key = dgp.gift_product_key
GROUP BY dgp.category ORDER BY revenue DESC;
```

---

## Page 4: Amenities & Trends

### Viz 8 - Revenue vs Amenity Count (Scatter)
```sql
SELECT dp.name, COUNT(DISTINCT fpa.amenity_key) AS amenity_count, ISNULL(rev.revenue,0) AS revenue
FROM dim_property dp
LEFT JOIN fact_property_amenity fpa ON dp.property_key = fpa.property_key
LEFT JOIN (SELECT property_key, SUM(amount_per*quantity) AS revenue FROM fact_revenue GROUP BY property_key) rev ON dp.property_key = rev.property_key
WHERE ISNULL(rev.revenue,0) > 0
GROUP BY dp.name, rev.revenue;
```

### Viz 9 - Monthly Check-in Heatmap (Matrix with conditional formatting)
```sql
SELECT dd.year, dd.month_num, dd.month_name, COUNT(*) AS checkins
FROM fact_checkin fc JOIN dim_date dd ON fc.date_key = dd.date_key
GROUP BY dd.year, dd.month_num, dd.month_name
ORDER BY dd.year, dd.month_num;
```

---

## DAX Computed Measures

```dax
YoY Revenue Change =
VAR CY = MAX(dim_date[year])
VAR CurrRev = CALCULATE(SUMX(fact_revenue, [amount_per]*[quantity]), dim_date[year]=CY)
VAR PrevRev = CALCULATE(SUMX(fact_revenue, [amount_per]*[quantity]), dim_date[year]=CY-1)
RETURN DIVIDE(CurrRev - PrevRev, PrevRev, 0) * 100

Labor Cost Ratio =
DIVIDE(SUM(fact_payroll[gross_pay])/100, SUMX(fact_revenue, [amount_per]*[quantity]), 0) * 100

Gift Shop Pct =
DIVIDE(SUMX(fact_gift_shop_sales, [sale_amount]*[quantity]),
       SUMX(fact_revenue, [amount_per]*[quantity]), 0) * 100
```
