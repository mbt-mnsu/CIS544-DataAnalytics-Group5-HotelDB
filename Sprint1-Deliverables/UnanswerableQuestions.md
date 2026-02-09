# Unanswerable Business Questions

This document lists business questions that we would like to answer, but cannot fully address with the current dataset. It also explains what data is missing.

 

## 1. What is the daily occupancy rate per property?

**Why this cannot be fully answered**

Right now, the database does not store a single record for a guest stay or room-night. Check-ins and check-outs are logged as separate events, and there is no table that shows which room was occupied on each night. To calculate daily occupancy accurately, we would need:

- A stay table with check-in and check-out dates  
- Nightly room assignment data per property  

Without this information, we can only estimate occupancy, not calculate it precisely.

 

## 2. How does guest satisfaction impact repeat stays?

**Why this cannot be fully answered**

The database does not include any guest feedback or satisfaction data such as ratings, reviews, or survey responses. To analyze this relationship, we would need a dataset that captures guest satisfaction and links it to:

- customer_id  
- property_id  

Without satisfaction metrics, we cannot determine whether happier guests are more likely to return.

 
