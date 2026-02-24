# Query List 2: MongoDB Aggregation Pipelines

These queries are MongoDB equivalents of the top 3 SQL queries from Sprint 1 (Query List 1).  
They run against the **`hotel_sql_mirror`** database (created by the ETL tool from SQL Server data).

---

## 1. Revenue by Property (Monthly)

### Business Question
which properties generate the most monthly revenue through American or Discover payment methods?

### MongoDB Aggregation Pipeline

```javascript
db.transact.aggregate([
  {
    $match:
      /**
       * query: The query in MQL.
       */
      {
        payment_method: {
          $in: ["American", "Discover"]
        }
      }
  },
  // 1. GROUP FIRST: Aggregate by ID and Date components
  // This collapses thousands of rows into a few dozen BEFORE the lookup
  {
    $group: {
      _id: {
        hotel_id: "$hotel_id",
        year: {
          $year: "$transaction_date"
        },
        month: {
          $month: "$transaction_date"
        }
      },
      total_revenue: {
        $sum: "$amount"
      }
    }
  },
  // 2. JOIN LATER: Only join the small aggregated result set
  {
    $lookup: {
      from: "property",
      localField: "_id.hotel_id",
      foreignField: "id",
      as: "property_info"
    }
  },
  {
    $unwind: "$property_info"
  },
  // 3. PROJECT: Extract the name and round the revenue
  {
    $project: {
      _id: 0,
      property_name: "$property_info.name",
      year: "$_id.year",
      month: "$_id.month",
      total_revenue: {
        $round: ["$total_revenue", 2]
      }
    }
  },
  // 4. SORT: Order the final results
  {
    $sort: {
      year: 1,
      month: 1,
      total_revenue: -1
    }
  }
]);
```

### Interpretation
This pipeline calculates monthly revenue per property using only transactions paid with American or Discover. It groups transactions by property and month, then joins with the property collection to display the hotel name. The final output helps identify which properties generate the highest revenue for these payment methods and how that revenue changes over time.

---

## 2. Revenue by Product / Service

### Business Question
Which products or services generate the most revenue?

### MongoDB Aggregation Pipeline

```javascript
db.transaction_line.aggregate([
  // Step 1: Calculate line total and group by description
  {
    $group: {
      _id: "$description",
      Total_Revenue: {
        $sum: { $multiply: ["$amount_per", "$quantity"] }
      }
    }
  },
  // Step 2: Reshape output
  {
    $project: {
      _id: 0,
      description: "$_id",
      Total_Revenue: { $round: ["$Total_Revenue", 2] }
    }
  },
  // Step 3: Sort by revenue descending
  { $sort: { Total_Revenue: -1 } }
]);
```

### Interpretation
This pipeline identifies which services or products (room charges, resort fees, taxes, etc.) contribute most to total revenue. It supports upselling strategies and revenue optimization decisions.

---

## 3. Check-in Volume by Property (Monthly)

### Business Question
Which properties have the highest check-in volume each month?

### MongoDB Aggregation Pipeline

```javascript
db.event.aggregate(
[
  // 1. Filter as early as possible
  {
    $match: {
      event_code: "checkin"
    }
  },
  // 2. Group by ID and Date components FIRST
  // This reduces the number of rows drastically before the $lookup
  {
    $group: {
      _id: {
        property_id: "$property_id",
        year: {
          $year: "$event_date"
        },
        month: {
          $month: "$event_date"
        }
      },
      checkin_count: {
        $sum: 1
      }
    }
  },
  // 3. Now join with the property collection (few lookups)
  {
    $lookup: {
      from: "property",
      localField: "_id.property_id",
      foreignField: "id",
      as: "property_info"
    }
  },
  // 4. Extract the name (use $arrayElemAt or $unwind)
  {
    $project: {
      _id: 0,
      property_name: {
        $arrayElemAt: ["$property_info.name", 0]
      },
      year: "$_id.year",
      month: "$_id.month",
      checkin_count: 1
    }
  },
  // 5. Sort the final aggregated set
  {
    $sort: {
      year: 1,
      month: 1,
      checkin_count: -1
    }
  }
]
);
```

### Interpretation
This shows monthly check-in workload by property. It helps understand operational demand and staffing needs, similar to the SQL version but using MongoDB's aggregation framework.

---


