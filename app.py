"""
app.py
------
Streamlit dashboard: KPI cards + charts over analytics.db, plus a
natural-language query box backed by nl_to_sql.py.

Run:
    streamlit run app.py

If ANTHROPIC_API_KEY is not set (in your environment or a .env file), the
NL query box runs in fallback (pattern-matched) mode — see nl_to_sql.py.
"""

import os
import sqlite3

import pandas as pd
import plotly.express as px
import streamlit as st

import theme
from nl_to_sql import answer_question, _llm_available

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DB_PATH = "analytics.db"

st.set_page_config(page_title="E-Commerce Analytics + GenAI Query", layout="wide")
st.markdown(theme.CSS, unsafe_allow_html=True)


@st.cache_data
def load_kpis() -> dict:
    conn = sqlite3.connect(DB_PATH)

    total_revenue = pd.read_sql_query(
        "SELECT ROUND(SUM(oi.quantity * oi.unit_price), 2) AS v "
        "FROM order_items oi JOIN orders o ON oi.order_id = o.order_id "
        "WHERE o.status = 'Completed'",
        conn,
    ).iloc[0]["v"]

    total_orders = pd.read_sql_query(
        "SELECT COUNT(*) AS v FROM orders WHERE status = 'Completed'", conn
    ).iloc[0]["v"]

    return_rate = pd.read_sql_query(
        "SELECT ROUND(100.0 * SUM(returned) / COUNT(*), 2) AS v FROM order_items", conn
    ).iloc[0]["v"]

    aov = round(total_revenue / total_orders, 2) if total_orders else 0

    revenue_by_category = pd.read_sql_query(
        "SELECT p.category, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue "
        "FROM order_items oi JOIN products p ON oi.product_id = p.product_id "
        "JOIN orders o ON oi.order_id = o.order_id WHERE o.status = 'Completed' "
        "GROUP BY p.category ORDER BY revenue DESC",
        conn,
    )

    return_rate_by_category = pd.read_sql_query(
        "SELECT p.category, ROUND(100.0 * SUM(oi.returned) / COUNT(*), 2) AS return_rate_pct "
        "FROM order_items oi JOIN products p ON oi.product_id = p.product_id "
        "GROUP BY p.category ORDER BY return_rate_pct DESC",
        conn,
    )

    monthly_revenue = pd.read_sql_query(
        "SELECT strftime('%Y-%m', o.order_date) AS month, "
        "ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue "
        "FROM order_items oi JOIN orders o ON oi.order_id = o.order_id "
        "WHERE o.status = 'Completed' GROUP BY month ORDER BY month",
        conn,
    )

    revenue_by_segment = pd.read_sql_query(
        "SELECT c.segment, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue, "
        "COUNT(DISTINCT o.order_id) AS orders "
        "FROM order_items oi JOIN orders o ON oi.order_id = o.order_id "
        "JOIN customers c ON o.customer_id = c.customer_id "
        "WHERE o.status = 'Completed' GROUP BY c.segment ORDER BY revenue DESC",
        conn,
    )

    rating_by_category = pd.read_sql_query(
        "SELECT p.category, ROUND(AVG(r.rating), 2) AS avg_rating, COUNT(*) AS n_reviews "
        "FROM reviews r JOIN products p ON r.product_id = p.product_id "
        "GROUP BY p.category ORDER BY avg_rating DESC",
        conn,
    )

    conn.close()
    return {
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "return_rate": return_rate,
        "aov": aov,
        "revenue_by_category": revenue_by_category,
        "return_rate_by_category": return_rate_by_category,
        "monthly_revenue": monthly_revenue,
        "revenue_by_segment": revenue_by_segment,
        "rating_by_category": rating_by_category,
    }


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

st.title("E-Commerce Analytics Dashboard")
st.caption(
    "SQL-backed KPIs + a GenAI natural-language query layer. "
    "Companion project to the Return Risk Modeling work — same domain, "
    "different lens: SQL + dashboarding + a text-to-SQL agent."
)

if not os.path.exists(DB_PATH):
    st.error(f"'{DB_PATH}' not found. Run `python db_setup.py` first.")
    st.stop()

kpis = load_kpis()

kpi_html = "<div class='kpi-row'>" + "".join(
    [
        theme.kpi_card_html("Total Revenue", f"₹{kpis['total_revenue']:,.0f}", 0),
        theme.kpi_card_html("Completed Orders", f"{kpis['total_orders']:,}", 1),
        theme.kpi_card_html("Return Rate", f"{kpis['return_rate']}%", 2),
        theme.kpi_card_html("Avg. Order Value", f"₹{kpis['aov']:,.0f}", 3),
    ]
) + "</div>"
st.markdown(kpi_html, unsafe_allow_html=True)

CHART_HEIGHT = 260

# ---------------------------------------------------------------------------
# NL query box — right below the KPI cards, above the charts
# ---------------------------------------------------------------------------

with st.container(border=True):
    st.subheader("Ask the data a question")

    mode_label = "🟢 LLM mode (AI generates SQL)" if _llm_available() else "🟡 Fallback mode (no API key set — pattern-matched queries only)"
    st.caption(mode_label)

    qcol1, qcol2 = st.columns([1, 1])
    with qcol1:
        example_questions = [
            "What's our total revenue?",
            "Which category has the highest return rate?",
            "What are the top 5 best-selling products?",
            "How does revenue break down by region?",
            "How do VIP customers compare to regular customers?",
            "Which category has the best average rating?",
        ]
        question = st.selectbox(
            "Pick an example, or type your own below:",
            options=["(type your own)"] + example_questions,
        )
    with qcol2:
        typed = st.text_input(
            "Your question:", value="" if question == "(type your own)" else question
        )

    ask_clicked = st.button("Ask")

    if ask_clicked:
        if not typed.strip():
            st.warning("Type a question first.")
        else:
            with st.spinner("Generating SQL and running query..."):
                result = answer_question(typed)

            with st.expander("Generated SQL", expanded=False):
                st.code(result["sql"], language="sql")

            st.dataframe(result["result"], use_container_width=True)
            st.info(result["summary"])

            # auto-chart if the result looks chartable (one category-like column + one numeric)
            df = result["result"]
            if df.shape[1] == 2 and df.shape[0] > 1:
                cat_col, num_col = df.columns[0], df.columns[1]
                if pd.api.types.is_numeric_dtype(df[num_col]):
                    fig = px.bar(df, x=cat_col, y=num_col, color_discrete_sequence=[theme.PINK])
                    fig.update_layout(template=theme.PLOTLY_TEMPLATE, showlegend=False, height=CHART_HEIGHT)
                    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    with st.container(border=True):
        st.subheader("Revenue by Category")
        fig = px.bar(
            kpis["revenue_by_category"], x="category", y="revenue", text_auto=".2s",
            color_discrete_sequence=[theme.CORAL],
        )
        fig.update_layout(template=theme.PLOTLY_TEMPLATE, showlegend=False, height=CHART_HEIGHT)
        st.plotly_chart(fig, use_container_width=True)

with chart_col2:
    with st.container(border=True):
        st.subheader("Return Rate by Category")
        fig = px.bar(
            kpis["return_rate_by_category"], x="category", y="return_rate_pct",
            text_auto=".1f", color="return_rate_pct",
            color_continuous_scale=theme.RETURN_RATE_SCALE,
        )
        fig.update_layout(template=theme.PLOTLY_TEMPLATE, coloraxis_showscale=False, height=CHART_HEIGHT)
        st.plotly_chart(fig, use_container_width=True)

chart_col3, chart_col4 = st.columns(2)

with chart_col3:
    with st.container(border=True):
        st.subheader("Monthly Revenue Trend")
        fig = px.line(
            kpis["monthly_revenue"], x="month", y="revenue", markers=True,
            color_discrete_sequence=[theme.PINK],
        )
        fig.update_traces(fill="tozeroy", fillcolor="rgba(227,95,168,0.18)",
                           marker=dict(color=theme.GOLD, size=6))
        fig.update_layout(template=theme.PLOTLY_TEMPLATE, height=CHART_HEIGHT)
        st.plotly_chart(fig, use_container_width=True)

with chart_col4:
    with st.container(border=True):
        st.subheader("Revenue by Customer Segment")
        fig = px.bar(
            kpis["revenue_by_segment"], x="segment", y="revenue", text_auto=".2s",
            hover_data=["orders"], color="segment",
            color_discrete_sequence=[theme.BLUE, theme.PURPLE, theme.BLUE_LIGHT],
        )
        fig.update_layout(template=theme.PLOTLY_TEMPLATE, showlegend=False, height=CHART_HEIGHT)
        st.plotly_chart(fig, use_container_width=True)

with st.container(border=True):
    st.subheader("Average Rating by Category")
    fig = px.bar(
        kpis["rating_by_category"], x="category", y="avg_rating", text_auto=".2f",
        color="avg_rating", color_continuous_scale=theme.RATING_SCALE, range_y=[0, 5],
        hover_data=["n_reviews"],
    )
    fig.update_layout(template=theme.PLOTLY_TEMPLATE, coloraxis_showscale=False, height=CHART_HEIGHT)
    st.plotly_chart(fig, use_container_width=True)
