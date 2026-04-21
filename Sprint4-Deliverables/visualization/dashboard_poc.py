"""
Sprint 4 — Visualization Proof-of-Concept
==========================================
Streamlit dashboard connecting to HotelDW data warehouse.
Displays 2 visuals:
  1. Monthly Revenue Trend by Property (top 10)
  2. Hotel Revenue vs Gift Shop Revenue by Property

Usage:
    streamlit run dashboard_poc.py
"""

import streamlit as st
import pandas as pd
import pyodbc
import plotly.express as px
import plotly.graph_objects as go

# ==========================
# Configuration
# ==========================

SQL_SERVER = "cis444.campus-quest.com,25000"
SQL_DW_DB = "HotelDW"
SQL_USER = "sa"
SQL_PASSWORD = "Academic2026U05!"


@st.cache_resource
def get_connection():
    """Create a cached database connection."""
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SQL_SERVER};DATABASE={SQL_DW_DB};UID={SQL_USER};PWD={SQL_PASSWORD};"
        f"TrustServerCertificate=yes;Connection Timeout=30;"
    )


@st.cache_data(ttl=300)
def run_query(sql):
    """Run a SQL query and return a pandas DataFrame."""
    conn = get_connection()
    return pd.read_sql(sql, conn)


# ==========================
# Page Setup
# ==========================

st.set_page_config(
    page_title="HotelDW Analytics Dashboard",
    page_icon="🏨",
    layout="wide"
)

st.title("🏨 HotelDW Analytics Dashboard")
st.markdown("**Sprint 4 — Visualization Proof-of-Concept** | Data sourced from HotelDW data warehouse")
st.divider()

# ==========================
# Visual 1: Monthly Revenue Trend
# ==========================

st.header("📊 Monthly Revenue Trend (Top 10 Properties)")
st.markdown("*Business Question: Which hotel properties generate the most monthly revenue, and how does revenue trend over time?*")

try:
    df_revenue = run_query("""
        SELECT TOP 5000
            dp.name AS property_name,
            dd.year,
            dd.month_num,
            dd.month_name,
            SUM(fr.amount_per * fr.quantity) AS total_revenue
        FROM fact_revenue fr
        JOIN dim_property dp ON fr.property_key = dp.property_key
        JOIN dim_date dd ON fr.date_key = dd.date_key
        GROUP BY dp.name, dd.year, dd.month_num, dd.month_name
        ORDER BY total_revenue DESC
    """)

    if not df_revenue.empty:
        # Get top 10 properties by total revenue
        top_props = df_revenue.groupby('property_name')['total_revenue'].sum().nlargest(10).index
        df_top = df_revenue[df_revenue['property_name'].isin(top_props)].copy()
        df_top['period'] = df_top['year'].astype(str) + '-' + df_top['month_num'].astype(str).str.zfill(2)
        df_top = df_top.sort_values('period')

        fig1 = px.line(
            df_top,
            x='period',
            y='total_revenue',
            color='property_name',
            title='Monthly Revenue by Top 10 Properties',
            labels={
                'period': 'Month',
                'total_revenue': 'Revenue ($)',
                'property_name': 'Property'
            }
        )
        fig1.update_layout(
            hovermode='x unified',
            xaxis_tickangle=-45,
            height=500,
            legend=dict(orientation="h", yanchor="bottom", y=-0.4)
        )
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.warning("No revenue data available. Ensure fact_revenue is populated.")
except Exception as e:
    st.error(f"Error loading revenue data: {e}")

st.divider()

# ==========================
# Visual 2: Hotel vs Gift Shop Revenue
# ==========================

st.header("🛍️ Hotel Revenue vs Gift Shop Revenue by Property")
st.markdown("*Business Question: Do properties with higher hotel room revenue also generate higher gift shop sales?*")

try:
    df_combined = run_query("""
        SELECT 
            dp.name AS property_name,
            ISNULL(hotel_rev.hotel_revenue, 0) AS hotel_revenue,
            ISNULL(gift_rev.gift_shop_revenue, 0) AS gift_shop_revenue
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
        ORDER BY hotel_revenue DESC
    """)

    if not df_combined.empty:
        # Top 15 by combined revenue
        df_combined['combined'] = df_combined['hotel_revenue'] + df_combined['gift_shop_revenue']
        df_top15 = df_combined.nlargest(15, 'combined')

        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            name='Hotel Revenue',
            x=df_top15['property_name'],
            y=df_top15['hotel_revenue'],
            marker_color='#2E86AB'
        ))
        fig2.add_trace(go.Bar(
            name='Gift Shop Revenue',
            x=df_top15['property_name'],
            y=df_top15['gift_shop_revenue'],
            marker_color='#F6511D'
        ))
        fig2.update_layout(
            barmode='group',
            title='Hotel vs Gift Shop Revenue — Top 15 Properties',
            xaxis_title='Property',
            yaxis_title='Revenue ($)',
            xaxis_tickangle=-45,
            height=500,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig2, use_container_width=True)

        # Show key metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Hotel Revenue", f"${df_combined['hotel_revenue'].sum():,.0f}")
        with col2:
            st.metric("Total Gift Shop Revenue", f"${df_combined['gift_shop_revenue'].sum():,.0f}")
        with col3:
            ratio = (df_combined['gift_shop_revenue'].sum() / df_combined['hotel_revenue'].sum() * 100) if df_combined['hotel_revenue'].sum() > 0 else 0
            st.metric("Gift Shop % of Hotel", f"{ratio:.1f}%")
    else:
        st.warning("No combined revenue data available.")
except Exception as e:
    st.error(f"Error loading combined revenue data: {e}")

st.divider()
st.caption("Dashboard built with Streamlit + Plotly | Data from HotelDW (SQL Server)")
