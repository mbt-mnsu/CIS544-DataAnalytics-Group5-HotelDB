"""
Sprint 6 — Comprehensive Analytics Dashboard
==============================================
Multi-page Streamlit dashboard for HotelDW data warehouse.

Pages:
  1. Executive Overview — KPIs, revenue trends, property performance
  2. Operations & Staffing — labor costs, check-in patterns
  3. Gift Shop Analytics — cross-source revenue, product categories
  4. Amenities & Trends — amenity impact, seasonal patterns

Usage:
    streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import pyodbc
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

# ============================================================
# Configuration
# ============================================================

SQL_SERVER = "cis444.campus-quest.com,25000"
SQL_DW_DB = "HotelDW"
SQL_USER = "sa"
SQL_PASSWORD = "Academic2026U05!"

COLOR_PALETTE = [
    "#6366F1", "#8B5CF6", "#EC4899", "#F43F5E", "#F97316",
    "#EAB308", "#22C55E", "#14B8A6", "#06B6D4", "#3B82F6"
]
BG_CARD = "rgba(255,255,255,0.05)"


@st.cache_resource
def get_connection():
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SQL_SERVER};DATABASE={SQL_DW_DB};UID={SQL_USER};PWD={SQL_PASSWORD};"
        f"TrustServerCertificate=yes;Connection Timeout=30;"
    )


@st.cache_data(ttl=300)
def q(sql):
    """Run a SQL query and return a DataFrame."""
    return pd.read_sql(sql, get_connection())


# ============================================================
# Page Config
# ============================================================

st.set_page_config(
    page_title="Hotel Analytics Dashboard",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .block-container { padding-top: 2rem; }
    div[data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 700; }
    div[data-testid="stMetricDelta"] { font-size: 0.9rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 24px; border-radius: 8px 8px 0 0;
        font-weight: 600; font-size: 0.95rem;
    }
    /* Push tabs below the top toolbar */
    .stTabs { margin-top: 1rem; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# Sidebar — Global Filters
# ============================================================

with st.sidebar:
    st.title("🏨 Hotel Chain Analytics")
    st.caption("Comprehensive Analytics Dashboard")
    st.divider()

    # Date range
    st.subheader("📅 Date Range")
    try:
        date_range = q("SELECT MIN(full_date) AS mn, MAX(full_date) AS mx FROM dim_date WHERE date_key IN (SELECT DISTINCT date_key FROM fact_revenue)")
        min_d = date_range['mn'].iloc[0]
        max_d = date_range['mx'].iloc[0]
        if isinstance(min_d, pd.Timestamp):
            min_d = min_d.date()
        if isinstance(max_d, pd.Timestamp):
            max_d = max_d.date()
    except Exception:
        min_d, max_d = date(2023, 1, 1), date(2025, 12, 31)

    d_start = st.date_input("Start", min_d, min_value=min_d, max_value=max_d)
    d_end = st.date_input("End", max_d, min_value=min_d, max_value=max_d)
    dk_start = int(d_start.strftime('%Y%m%d'))
    dk_end = int(d_end.strftime('%Y%m%d'))

    st.divider()

    # Property filter
    st.subheader("🏢 Properties")
    try:
        all_props = q("SELECT DISTINCT name FROM dim_property ORDER BY name")['name'].tolist()
    except Exception:
        all_props = []
    selected_props = st.multiselect("Filter properties", all_props, default=[], placeholder="All properties")
    prop_filter_sql = ""
    if selected_props:
        escaped = "','".join([p.replace("'", "''") for p in selected_props])
        prop_filter_sql = f" AND dp.name IN ('{escaped}')"

    st.divider()
    st.subheader("📊 Display")
    top_n = st.slider("Top N items", 5, 30, 10)

# Helper: date + property filter fragment
DATE_FILTER = f" AND fr.date_key BETWEEN {dk_start} AND {dk_end}"
DATE_FILTER_FC = f" AND fc.date_key BETWEEN {dk_start} AND {dk_end}"
DATE_FILTER_GS = f" AND gs.date_key BETWEEN {dk_start} AND {dk_end}"
DATE_FILTER_FP = f" AND fp.date_key BETWEEN {dk_start} AND {dk_end}"

# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Executive Overview",
    "👥 Operations & Staffing",
    "🛍️ Gift Shop Analytics",
    "🏖️ Amenities & Trends"
])

# ============================================================
# TAB 1: Executive Overview
# ============================================================

with tab1:
    st.header("Executive Overview")

    # ---- KPI Row ----
    try:
        kpi = q(f"""
            SELECT
                SUM(CAST(fr.amount_per * fr.quantity AS BIGINT)) AS total_rev,
                COUNT(DISTINCT fr.transaction_id) AS total_txn
            FROM fact_revenue fr
            WHERE 1=1 {DATE_FILTER}
        """)
        total_rev = kpi['total_rev'].iloc[0] or 0
        total_txn = kpi['total_txn'].iloc[0] or 0
    except Exception:
        total_rev, total_txn = 0, 0

    try:
        kpi_ci = q(f"""
            SELECT COUNT(*) AS total_checkins
            FROM fact_checkin fc WHERE 1=1 {DATE_FILTER_FC}
        """)
        total_ci = kpi_ci['total_checkins'].iloc[0] or 0
    except Exception:
        total_ci = 0

    # YoY Revenue (computed measure)
    try:
        yoy = q(f"""
            SELECT
                SUM(CASE WHEN dd.year = (SELECT MAX(year) FROM dim_date WHERE date_key <= {dk_end})
                    THEN CAST(fr.amount_per * fr.quantity AS BIGINT) ELSE 0 END) AS curr,
                SUM(CASE WHEN dd.year = (SELECT MAX(year) FROM dim_date WHERE date_key <= {dk_end}) - 1
                    THEN CAST(fr.amount_per * fr.quantity AS BIGINT) ELSE 0 END) AS prev
            FROM fact_revenue fr
            JOIN dim_date dd ON fr.date_key = dd.date_key
            WHERE fr.date_key BETWEEN {dk_start} AND {dk_end}
        """)
        curr_y = yoy['curr'].iloc[0] or 0
        prev_y = yoy['prev'].iloc[0] or 1
        yoy_pct = ((curr_y - prev_y) / prev_y * 100) if prev_y > 0 else 0
    except Exception:
        curr_y, prev_y, yoy_pct = 0, 0, 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Total Revenue", f"${total_rev:,.0f}")
    c2.metric("🧾 Transactions", f"{total_txn:,}")
    c3.metric("🛎️ Check-ins", f"{total_ci:,}")
    c4.metric("📈 YoY Revenue Δ", f"{yoy_pct:+.1f}%",
              delta=f"${curr_y - prev_y:,.0f}")

    st.divider()

    # ---- Viz 1: Monthly Revenue Trend ----
    col_a, col_b = st.columns([3, 2])

    with col_a:
        st.subheader("Monthly Revenue Trend")
        try:
            df_trend = q(f"""
                SELECT dd.year, dd.month_num, dd.month_name,
                       SUM(CAST(fr.amount_per * fr.quantity AS BIGINT)) AS revenue
                FROM fact_revenue fr
                JOIN dim_date dd ON fr.date_key = dd.date_key
                WHERE fr.date_key BETWEEN {dk_start} AND {dk_end}
                GROUP BY dd.year, dd.month_num, dd.month_name
                ORDER BY dd.year, dd.month_num
            """)
            if not df_trend.empty:
                df_trend['period'] = df_trend['year'].astype(str) + '-' + df_trend['month_num'].astype(str).str.zfill(2)
                fig1 = px.area(df_trend, x='period', y='revenue',
                               color_discrete_sequence=[COLOR_PALETTE[0]],
                               labels={'period': 'Month', 'revenue': 'Revenue ($)'})
                fig1.update_layout(height=380, hovermode='x unified',
                                   xaxis_tickangle=-45, showlegend=False)
                st.plotly_chart(fig1, width='stretch')
            else:
                st.info("No revenue data in selected range.")
        except Exception as e:
            st.error(f"Error: {e}")

    # ---- Viz 2: Payment Method Distribution ----
    with col_b:
        st.subheader("Payment Method Distribution")
        try:
            df_pay = q(f"""
                SELECT payment_method, COUNT(*) AS cnt,
                       SUM(CAST(amount_per * quantity AS BIGINT)) AS rev
                FROM fact_revenue fr
                WHERE 1=1 {DATE_FILTER}
                GROUP BY payment_method
                ORDER BY rev DESC
            """)
            if not df_pay.empty:
                fig_pay = px.pie(df_pay, values='rev', names='payment_method',
                                color_discrete_sequence=COLOR_PALETTE,
                                hole=0.45)
                fig_pay.update_layout(height=380, showlegend=True,
                                      legend=dict(orientation="h", y=-0.15))
                fig_pay.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_pay, width='stretch')
            else:
                st.info("No data.")
        except Exception as e:
            st.error(f"Error: {e}")

    st.divider()

    # ---- Viz 3: Top N Properties by Revenue (interactive) ----
    st.subheader(f"Top {top_n} Properties by Revenue")
    try:
        df_prop = q(f"""
            SELECT TOP {top_n} dp.name AS property_name,
                   SUM(CAST(fr.amount_per * fr.quantity AS BIGINT)) AS revenue
            FROM fact_revenue fr
            JOIN dim_property dp ON fr.property_key = dp.property_key
            WHERE 1=1 {DATE_FILTER} {prop_filter_sql}
            GROUP BY dp.name
            ORDER BY revenue DESC
        """)
        if not df_prop.empty:
            fig_prop = px.bar(df_prop, x='revenue', y='property_name',
                              orientation='h',
                              color='revenue',
                              color_continuous_scale='Viridis',
                              labels={'revenue': 'Revenue ($)', 'property_name': 'Property'})
            fig_prop.update_layout(height=max(350, top_n * 30), yaxis=dict(autorange='reversed'),
                                   coloraxis_showscale=False, showlegend=False)
            st.plotly_chart(fig_prop, width='stretch')
        else:
            st.info("No data.")
    except Exception as e:
        st.error(f"Error: {e}")


# ============================================================
# TAB 2: Operations & Staffing
# ============================================================

with tab2:
    st.header("Operations & Staffing")

    # KPIs
    try:
        kpi_pay = q(f"""
            SELECT SUM(CAST(fp.gross_pay AS BIGINT)) AS total_payroll,
                   COUNT(DISTINCT fp.employee_key) AS emp_count
            FROM fact_payroll fp
            WHERE 1=1 {DATE_FILTER_FP}
        """)
        t_payroll = (kpi_pay['total_payroll'].iloc[0] or 0) / 100.0
        emp_cnt = kpi_pay['emp_count'].iloc[0] or 0
    except Exception:
        t_payroll, emp_cnt = 0, 0

    labor_pct = (t_payroll / total_rev * 100) if total_rev > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("💵 Total Payroll", f"${t_payroll:,.0f}")
    c2.metric("👤 Employees", f"{emp_cnt:,}")
    c3.metric("📊 Labor Cost %", f"{labor_pct:.1f}%",
              help="Total payroll / Total hotel revenue × 100")

    st.divider()

    # ---- Viz 4: Labor Cost as % of Revenue by Property (computed measure, interactive) ----
    st.subheader("Labor Cost as % of Revenue by Property")
    try:
        df_labor = q(f"""
            SELECT TOP {top_n}
                dp.name AS property_name,
                ISNULL(SUM(CAST(fp.gross_pay AS BIGINT)), 0) / 100.0 AS payroll,
                ISNULL(rev.revenue, 0) AS revenue
            FROM dim_property dp
            LEFT JOIN fact_payroll fp ON dp.property_key = fp.property_key
                {DATE_FILTER_FP.replace('fp.', 'fp.')}
            LEFT JOIN (
                SELECT property_key, SUM(CAST(amount_per * quantity AS BIGINT)) AS revenue
                FROM fact_revenue WHERE date_key BETWEEN {dk_start} AND {dk_end}
                GROUP BY property_key
            ) rev ON dp.property_key = rev.property_key
            {f"WHERE dp.name IN ('" + "','".join([p.replace("'","''") for p in selected_props]) + "')" if selected_props else ""}
            GROUP BY dp.name, rev.revenue
            HAVING ISNULL(rev.revenue, 0) > 0
            ORDER BY ISNULL(SUM(CAST(fp.gross_pay AS BIGINT)), 0) / 100.0 / NULLIF(ISNULL(rev.revenue, 0), 0) DESC
        """)
        if not df_labor.empty:
            df_labor['labor_pct'] = (df_labor['payroll'] / df_labor['revenue'] * 100).round(2)
            fig_labor = px.bar(df_labor, x='property_name', y='labor_pct',
                               color='labor_pct',
                               color_continuous_scale='RdYlGn_r',
                               labels={'labor_pct': 'Labor Cost %', 'property_name': 'Property'})
            fig_labor.update_layout(height=450, xaxis_tickangle=-45,
                                    coloraxis_showscale=False)
            fig_labor.add_hline(y=30, line_dash="dash", line_color="red",
                                annotation_text="30% benchmark")
            st.plotly_chart(fig_labor, width='stretch')
        else:
            st.info("No data.")
    except Exception as e:
        st.error(f"Error: {e}")

    st.divider()

    # ---- Viz 5: Weekend vs Weekday Check-ins (interactive) ----
    st.subheader("Weekend vs. Weekday Check-ins")
    try:
        df_wk = q(f"""
            SELECT TOP 1000
                dp.name AS property_name,
                CASE WHEN dd.is_weekend = 1 THEN 'Weekend' ELSE 'Weekday' END AS day_type,
                COUNT(*) AS checkins
            FROM fact_checkin fc
            JOIN dim_property dp ON fc.property_key = dp.property_key
            JOIN dim_date dd ON fc.date_key = dd.date_key
            WHERE 1=1 {DATE_FILTER_FC} {prop_filter_sql}
            GROUP BY dp.name, dd.is_weekend
            ORDER BY checkins DESC
        """)
        if not df_wk.empty:
            top_props_wk = df_wk.groupby('property_name')['checkins'].sum().nlargest(top_n).index
            df_wk_top = df_wk[df_wk['property_name'].isin(top_props_wk)]
            fig_wk = px.bar(df_wk_top, x='property_name', y='checkins',
                            color='day_type', barmode='group',
                            color_discrete_map={'Weekday': COLOR_PALETTE[0], 'Weekend': COLOR_PALETTE[3]},
                            labels={'checkins': 'Check-ins', 'property_name': 'Property'})
            fig_wk.update_layout(height=450, xaxis_tickangle=-45,
                                 legend=dict(orientation="h", y=1.05))
            st.plotly_chart(fig_wk, width='stretch')
        else:
            st.info("No data.")
    except Exception as e:
        st.error(f"Error: {e}")


# ============================================================
# TAB 3: Gift Shop Analytics
# ============================================================

with tab3:
    st.header("Gift Shop & Cross-Source Analytics")

    # KPIs
    try:
        kpi_gs = q(f"""
            SELECT SUM(gs.sale_amount * gs.quantity) AS gs_rev
            FROM fact_gift_shop_sales gs WHERE 1=1 {DATE_FILTER_GS}
        """)
        gs_rev = kpi_gs['gs_rev'].iloc[0] or 0
    except Exception:
        gs_rev = 0

    gs_pct = (gs_rev / total_rev * 100) if total_rev > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("🛍️ Gift Shop Revenue", f"${gs_rev:,.0f}")
    c2.metric("💰 Hotel Revenue", f"${total_rev:,.0f}")
    c3.metric("📊 Gift Shop % of Hotel", f"{gs_pct:.1f}%",
              help="Gift shop revenue / Hotel revenue × 100")

    st.divider()

    # ---- Viz 6: Hotel vs Gift Shop Revenue by Property ----
    st.subheader(f"Hotel vs. Gift Shop Revenue — Top {top_n} Properties")
    try:
        df_vs = q(f"""
            SELECT TOP {top_n} dp.name AS property_name,
                ISNULL(h.hotel_rev, 0) AS hotel_revenue,
                ISNULL(g.gift_rev, 0) AS gift_shop_revenue
            FROM dim_property dp
            LEFT JOIN (
                SELECT property_key, SUM(CAST(amount_per * quantity AS BIGINT)) AS hotel_rev
                FROM fact_revenue WHERE date_key BETWEEN {dk_start} AND {dk_end}
                GROUP BY property_key
            ) h ON dp.property_key = h.property_key
            LEFT JOIN (
                SELECT property_key, SUM(sale_amount * quantity) AS gift_rev
                FROM fact_gift_shop_sales WHERE date_key BETWEEN {dk_start} AND {dk_end}
                GROUP BY property_key
            ) g ON dp.property_key = g.property_key
            WHERE ISNULL(h.hotel_rev, 0) + ISNULL(g.gift_rev, 0) > 0
            {prop_filter_sql.replace('dp.name', 'dp.name')}
            ORDER BY ISNULL(h.hotel_rev, 0) + ISNULL(g.gift_rev, 0) DESC
        """)
        if not df_vs.empty:
            fig_vs = go.Figure()
            fig_vs.add_trace(go.Bar(name='Hotel Revenue', x=df_vs['property_name'],
                                    y=df_vs['hotel_revenue'], marker_color=COLOR_PALETTE[0]))
            fig_vs.add_trace(go.Bar(name='Gift Shop Revenue', x=df_vs['property_name'],
                                    y=df_vs['gift_shop_revenue'], marker_color=COLOR_PALETTE[3]))
            fig_vs.update_layout(barmode='group', height=450, xaxis_tickangle=-45,
                                 legend=dict(orientation="h", y=1.05))
            st.plotly_chart(fig_vs, width='stretch')
        else:
            st.info("No data.")
    except Exception as e:
        st.error(f"Error: {e}")

    st.divider()

    # ---- Viz 7: Top Gift Shop Categories (interactive) ----
    st.subheader("Gift Shop Revenue by Product Category")
    try:
        df_cat = q(f"""
            SELECT dgp.category, SUM(gs.sale_amount * gs.quantity) AS revenue,
                   COUNT(*) AS items_sold
            FROM fact_gift_shop_sales gs
            JOIN dim_gift_product dgp ON gs.gift_product_key = dgp.gift_product_key
            JOIN dim_property dp ON gs.property_key = dp.property_key
            WHERE 1=1 {DATE_FILTER_GS} {prop_filter_sql}
            GROUP BY dgp.category
            ORDER BY revenue DESC
        """)
        if not df_cat.empty:
            fig_cat = px.bar(df_cat, x='revenue', y='category', orientation='h',
                             color='revenue', color_continuous_scale='Magma',
                             labels={'revenue': 'Revenue ($)', 'category': 'Category'})
            fig_cat.update_layout(height=max(300, len(df_cat) * 35),
                                  yaxis=dict(autorange='reversed'),
                                  coloraxis_showscale=False)
            st.plotly_chart(fig_cat, width='stretch')
        else:
            st.info("No data.")
    except Exception as e:
        st.error(f"Error: {e}")


# ============================================================
# TAB 4: Amenities & Trends
# ============================================================

with tab4:
    st.header("Amenities & Seasonal Trends")

    # ---- Viz 8: Revenue per Amenity Count (scatter) ----
    st.subheader("Property Revenue vs. Number of Amenities")
    try:
        df_amen = q(f"""
            SELECT dp.name AS property_name,
                   COUNT(DISTINCT fpa.amenity_key) AS amenity_count,
                   ISNULL(rev.revenue, 0) AS revenue
            FROM dim_property dp
            LEFT JOIN fact_property_amenity fpa ON dp.property_key = fpa.property_key
            LEFT JOIN (
                SELECT property_key, SUM(CAST(amount_per * quantity AS BIGINT)) AS revenue
                FROM fact_revenue WHERE date_key BETWEEN {dk_start} AND {dk_end}
                GROUP BY property_key
            ) rev ON dp.property_key = rev.property_key
            WHERE ISNULL(rev.revenue, 0) > 0
            GROUP BY dp.name, rev.revenue
        """)
        if not df_amen.empty:
            fig_amen = px.scatter(df_amen, x='amenity_count', y='revenue',
                                  hover_name='property_name',
                                  color='amenity_count',
                                  color_continuous_scale='Viridis',
                                  size='revenue', size_max=20,
                                  labels={'amenity_count': '# Amenities', 'revenue': 'Revenue ($)'})
            fig_amen.update_layout(height=450, coloraxis_showscale=False)
            st.plotly_chart(fig_amen, width='stretch')
        else:
            st.info("No data.")
    except Exception as e:
        st.error(f"Error: {e}")

    st.divider()

    # ---- Viz 9: Monthly Check-in Heatmap ----
    st.subheader("Monthly Check-in Heatmap (Year × Month)")
    try:
        df_heat = q(f"""
            SELECT dd.year, dd.month_num, dd.month_name,
                   COUNT(*) AS checkins
            FROM fact_checkin fc
            JOIN dim_date dd ON fc.date_key = dd.date_key
            WHERE fc.date_key BETWEEN {dk_start} AND {dk_end}
            GROUP BY dd.year, dd.month_num, dd.month_name
            ORDER BY dd.year, dd.month_num
        """)
        if not df_heat.empty:
            pivot = df_heat.pivot(index='year', columns='month_num', values='checkins').fillna(0)
            month_labels = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
            pivot.columns = [month_labels[c-1] for c in pivot.columns if c <= 12]
            fig_heat = px.imshow(pivot, aspect='auto',
                                 color_continuous_scale='YlOrRd',
                                 labels={'x': 'Month', 'y': 'Year', 'color': 'Check-ins'})
            fig_heat.update_layout(height=300)
            st.plotly_chart(fig_heat, width='stretch')
        else:
            st.info("No data.")
    except Exception as e:
        st.error(f"Error: {e}")


# ============================================================
# Footer
# ============================================================
st.divider()
st.caption("Dashboard built with Streamlit + Plotly | CIS 444/544")
