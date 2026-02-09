## 1. Revenue by Property (Monthly)
## Business Question: Which hotel properties generate the most revenue each month?
SELECT 
p.name AS property_name, 
YEAR(t.transaction_date) AS yr, 
MONTH(t.transaction_date) AS mo, 
SUM(t.amount) AS total_revenue 
FROM dbo.transact t 
JOIN dbo.property p 
ON p.id = t.hotel_id 
GROUP BY p.name, YEAR(t.transaction_date), MONTH(t.transaction_date) 
ORDER BY yr, mo, total_revenue DESC; 
This query shows monthly revenue by property. It helps identify top-performing hotels and detect seasonal revenue patterns.

## 2. Payment Method Usage
## Business Question: Which payment methods are most commonly used, and how much revenue does each generate?
SELECT 
payment_method, 
COUNT(*) AS transaction_count, 
SUM(amount) AS total_revenue, 
AVG(amount) AS avg_transaction_amount 
FROM dbo.transact 
GROUP BY payment_method 
ORDER BY transaction_count DESC;
This shows customer payment preferences and revenue contribution by payment method. It can support payment processing and fraud monitoring decisions.

## 3. Check-in Volume by Property (Monthly)
## Business Question: Which properties have the highest check-in volume each month?
SELECT 
p.name AS property_name, 
YEAR(e.event_date) AS yr, 
MONTH(e.event_date) AS mo, 
COUNT(*) AS checkin_count 
FROM dbo.event e 
JOIN dbo.property p 
ON p.id = e.property_id 
WHERE e.event_code = 'checkin' 
GROUP BY p.name, YEAR(e.event_date), MONTH(e.event_date) 
ORDER BY yr, mo, checkin_count DESC;
This query shows monthly check-in workload by property, which helps understand operational demand and staffing needs

## Notes:
## The event table currently stores only two event types: checkin and checkout but limits operational analytics such as housekeeping or maintenance tracking.
