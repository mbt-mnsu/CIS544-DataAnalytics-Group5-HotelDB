# Dashboard Documentation - Sprint 6

## Overview

The **HotelDW Analytics Dashboard** is a multi-page Streamlit application powered by Plotly visualizations. It connects directly to the `HotelDW` data warehouse (SQL Server) and presents four analytics pages covering executive metrics, operations, gift shop analytics, and amenity/trend analysis.

**Technology Stack:** Streamlit ≥ 1.30, Plotly ≥ 5.18, pyodbc ≥ 5.0, pandas ≥ 2.0

**Launch Command:**
```bash
streamlit run dashboard.py
```

---

## Global Interactive Controls

| Control | Location | Behavior |
|---------|----------|----------|
| **Date Range** (start / end) | Sidebar | Filters all visualizations by `date_key BETWEEN start AND end` |
| **Property Multi-Select** | Sidebar | Filters visualizations to selected property names; empty = all |
| **Top-N Slider** | Sidebar | Controls the number of items shown in ranked bar charts (5–30) |

---

## Page 1: Executive Overview

### KPI Cards

| KPI | Source Table(s) | Computation |
|-----|----------------|-------------|
| Total Revenue | `fact_revenue` | `SUM(amount_per * quantity)` filtered by date range |
| Transactions | `fact_revenue` | `COUNT(DISTINCT transaction_id)` filtered by date range |
| Total Check-ins | `fact_checkin` | `COUNT(*)` filtered by date range |
| YoY Revenue Δ | `fact_revenue` + `dim_date` | *Computed measure:* `(current_year_rev − prev_year_rev) / prev_year_rev × 100` |

### Viz 1 — Monthly Revenue Trend (Area Chart)

- **Business Question:** How does hotel revenue trend over time?
- **Data Source:** `fact_revenue` JOIN `dim_date`
- **Axes:** X = Year-Month period, Y = Revenue ($)
- **Interactivity:** Responds to global date range filter
- **SQL Summary:**
  ```sql
  SELECT dd.year, dd.month_num, dd.month_name,
         SUM(fr.amount_per * fr.quantity) AS revenue
  FROM fact_revenue fr
  JOIN dim_date dd ON fr.date_key = dd.date_key
  WHERE fr.date_key BETWEEN @start AND @end
  GROUP BY dd.year, dd.month_num, dd.month_name
  ORDER BY dd.year, dd.month_num
  ```

### Viz 2 - Payment Method Distribution (Donut Chart)

- **Business Question:** What is the breakdown of payment methods used for hotel transactions?
- **Data Source:** `fact_revenue`
- **Metric:** Revenue by `payment_method`
- **Interactivity:** Responds to global date range filter

### Viz 3 - Top N Properties by Revenue (Horizontal Bar Chart)

- **Business Question:** Which properties generate the most revenue?
- **Data Source:** `fact_revenue` JOIN `dim_property`
- **Interactivity:** Top-N slider controls how many properties are shown; property multi-select filters the list
- **Computed Feature:** Color gradient based on revenue magnitude

---

## Page 2: Operations & Staffing

### KPI Cards

| KPI | Source Table(s) | Computation |
|-----|----------------|-------------|
| Total Payroll | `fact_payroll` | `SUM(gross_pay) / 100` (stored as cents) |
| Employees | `fact_payroll` | `COUNT(DISTINCT employee_key)` |
| Labor Cost % | `fact_payroll` + `fact_revenue` | *Computed measure:* `total_payroll / total_revenue × 100` |

### Viz 4 - Labor Cost as % of Revenue by Property (Bar Chart)

- **Business Question:** Which properties have the highest labor cost burden relative to their revenue?
- **Data Source:** `fact_payroll` + `fact_revenue` + `dim_property`
- **Computed Measure:** `Labor Cost % = (SUM(gross_pay)/100) / SUM(amount_per * quantity) × 100`
- **Interactivity:** Date range filter, property multi-select, top-N slider
- **Design Note:** 30% benchmark line drawn as reference

### Viz 5 - Weekend vs. Weekday Check-ins (Grouped Bar Chart)

- **Business Question:** How do check-in patterns differ between weekdays and weekends across properties?
- **Data Source:** `fact_checkin` JOIN `dim_property` JOIN `dim_date`
- **Grouping:** `CASE WHEN dd.is_weekend = 1 THEN 'Weekend' ELSE 'Weekday' END`
- **Interactivity:** Date range filter, property multi-select, top-N slider

---

## Page 3: Gift Shop & Cross-Source Analytics

### KPI Cards

| KPI | Source Table(s) | Computation |
|-----|----------------|-------------|
| Gift Shop Revenue | `fact_gift_shop_sales` | `SUM(sale_amount * quantity)` |
| Hotel Revenue | `fact_revenue` | `SUM(amount_per * quantity)` |
| Gift Shop % of Hotel | Both above | *Computed measure:* `gift_shop_rev / hotel_rev × 100` |

### Viz 6 - Hotel vs. Gift Shop Revenue by Property (Grouped Bar Chart)

- **Business Question:** How does gift shop revenue compare to hotel revenue at each property?
- **Data Source:** `fact_revenue` + `fact_gift_shop_sales` + `dim_property`
- **Interactivity:** Date range filter, property multi-select, top-N slider
- **Design Note:** Two traces (Hotel and Gift Shop) shown side by side

### Viz 7 - Gift Shop Revenue by Product Category (Horizontal Bar Chart)

- **Business Question:** Which gift shop product categories generate the most revenue?
- **Data Source:** `fact_gift_shop_sales` JOIN `dim_gift_product` JOIN `dim_property`
- **Interactivity:** Date range filter, property multi-select
- **Design Note:** Color gradient using Magma color scale

---

## Page 4: Amenities & Seasonal Trends

### Viz 8 - Property Revenue vs. Number of Amenities (Scatter Plot)

- **Business Question:** Is there a relationship between the number of amenities a property offers and its revenue?
- **Data Source:** `dim_property` + `fact_property_amenity` + `fact_revenue`
- **Axes:** X = # Amenities, Y = Revenue ($), bubble size = Revenue
- **Design Note:** Hover shows property name

### Viz 9 - Monthly Check-in Heatmap (Heatmap)

- **Business Question:** What seasonal patterns exist in check-in volume across years?
- **Data Source:** `fact_checkin` JOIN `dim_date`
- **Axes:** X = Month (Jan–Dec), Y = Year
- **Color:** YlOrRd scale; darker = more check-ins

---

## Computed Measures Summary

| Measure | Formula | Used In |
|---------|---------|---------|
| **YoY Revenue Change (%)** | `(curr_year_rev − prev_year_rev) / prev_year_rev × 100` | Page 1 KPI card |
| **Labor Cost Ratio (%)** | `total_payroll / total_revenue × 100` | Page 2 KPI card + Viz 4 |
| **Gift Shop % of Hotel Revenue** | `gift_shop_rev / hotel_rev × 100` | Page 3 KPI card |

---

## Data Architecture

```
Source Systems                    Data Warehouse              Dashboard
─────────────                    ──────────────              ─────────
┌─────────────────┐              ┌─────────────┐
│ Hotel (SQL Svr) │──── ETL ────▶│   HotelDW   │
│ cis444:25000    │              │             │       ┌──────────────┐
└─────────────────┘              │  8 dims     │       │  Streamlit   │
                                 │  5 facts    │──────▶│  + Plotly    │
┌─────────────────┐              │  metadata   │       │  Dashboard   │
│ Gift Shop       │──── ETL ────▶│             │       └──────────────┘
│ (MongoDB)       │              └─────────────┘
│ cis444:25010    │
└─────────────────┘
```

All dashboard queries read from `HotelDW` exclusively - no direct access to source systems.
