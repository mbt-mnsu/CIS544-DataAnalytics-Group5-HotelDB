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

### Purpose: This query shows monthly revenue by property. It helps identify top-performing hotels and detect seasonal revenue patterns.

## 2. Revenue by Product / Service  

### Business Question: Which products or services generate the most revenue?

### SQL Query

SELECT 
    description, 
    SUM(amount_per * quantity) AS Total_Revenue
FROM dbo.transaction_line
GROUP BY description
ORDER BY Total_Revenue DESC;


### Purpose: This query highlights which services or products contribute most to total revenue. It can support upselling strategies and revenue optimization decisions.


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

## Notes: The event table currently stores only two event types: checkin and checkout but limits operational analytics such as housekeeping or maintenance tracking.




# Additional Queries List – Discovery Queries  

---

## 1️⃣ Total Spent per Customer  

### Business Question  
Which customers have spent the most money overall?

### SQL Query

SELECT 
    c.id, 
    c.first_name, 
    c.last_name, 
    SUM(t.amount) AS Total_Spent
FROM dbo.customer c
JOIN dbo.transact t 
    ON c.id = t.customer_id
GROUP BY c.id, c.first_name, c.last_name
ORDER BY Total_Spent DESC;


### Purpose: This query identifies high-value customers based on total spending. It can support loyalty programs, targeted marketing, and VIP customer segmentation strategies.

---

## 2️⃣ Average Room Price by Room Type  

### Business Question  
What is the average nightly price for each room type?

### SQL Query

SELECT 
    r.description AS Room_Type, 
    AVG(p.price) AS Average_Price
FROM dbo.room_type r
JOIN dbo.property_rooms p 
    ON r.id = p.room_type_id
GROUP BY r.description
ORDER BY Average_Price DESC;


### Purpose: This query compares pricing across room categories. It helps management evaluate pricing strategy and understand differences between room tiers.

---

## 3️⃣ Payment Method Usage
## Business Question: Which payment methods are most commonly used, and how much revenue does each generate?
SELECT 
payment_method, 
COUNT(*) AS transaction_count, 
SUM(amount) AS total_revenue, 
AVG(amount) AS avg_transaction_amount 
FROM dbo.transact 
GROUP BY payment_method 
ORDER BY transaction_count DESC;

### Purpose: This shows customer payment preferences and revenue contribution by payment method. It can support payment processing and fraud monitoring decisions.