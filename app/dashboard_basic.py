from __future__ import annotations

from pathlib import Path
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"

st.set_page_config(page_title="RetailPulse Foresight AI", page_icon="📦", layout="wide")

@st.cache_data
def load_outputs():
    weekly = pd.read_csv(PROCESSED / "weekly_demand_features.csv", parse_dates=["week_start"])
    forecasts = pd.read_csv(PROCESSED / "sku_forecasts.csv", parse_dates=["week_start"])
    risk = pd.read_csv(PROCESSED / "risk_scores.csv")
    metrics = pd.read_csv(PROCESSED / "model_metrics.csv")
    customers = pd.read_csv(PROCESSED / "customer_segments.csv")
    summary_path = PROCESSED / "executive_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    return weekly, forecasts, risk, metrics, customers, summary


def money(x):
    return f"₹{x:,.0f}"


def pct(x):
    return f"{x*100:.1f}%"

try:
    weekly, forecasts, risk, metrics, customers, summary = load_outputs()
except FileNotFoundError:
    st.error("Processed files not found. Run `python run_all.py` first.")
    st.stop()

st.sidebar.title("FORESIGHT + RetailPulse")
category_options = ["All"] + sorted(risk["category"].dropna().unique().tolist())
selected_category = st.sidebar.selectbox("Category", category_options)
action_options = ["All"] + sorted(risk["recommended_action"].dropna().unique().tolist())
selected_action = st.sidebar.selectbox("Recommended action", action_options)

filtered_risk = risk.copy()
if selected_category != "All":
    filtered_risk = filtered_risk[filtered_risk["category"] == selected_category]
if selected_action != "All":
    filtered_risk = filtered_risk[filtered_risk["recommended_action"] == selected_action]

st.title("📦 FORESIGHT + RetailPulse")
st.caption("AI-powered demand forecasting, inventory risk decisioning, and customer analytics for retail planning.")

metric_row = metrics.iloc[0]
col1, col2, col3, col4 = st.columns(4)
col1.metric("Model WAPE", pct(float(metric_row["model_wape"])))
col2.metric("Baseline WAPE", pct(float(metric_row["baseline_wape"])))
improvement = 1 - float(metric_row["model_wape"]) / max(float(metric_row["baseline_wape"]), 1e-9)
col3.metric("WAPE improvement", pct(improvement))
col4.metric("Sales at risk", money(summary.get("sales_at_risk_rupees", risk["sales_at_risk_rupees"].sum())))

col5, col6, col7, col8 = st.columns(4)
col5.metric("Locked capital", money(summary.get("locked_capital_rupees", risk["locked_capital_rupees"].sum())))
col6.metric("Reorder now", int((risk["recommended_action"] == "Reorder now").sum()))
col7.metric("Markdown / clear", int((risk["recommended_action"] == "Markdown / clear").sum()))
col8.metric("SKUs monitored", risk["sku_id"].nunique())

st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Executive view", "Forecast explorer", "Risk decisioning", "RetailPulse customers", "Reports"])

with tab1:
    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Decision matrix")
        fig = px.scatter(
            filtered_risk,
            x="overstock_risk",
            y="stockout_risk",
            size="priority_score",
            color="recommended_action",
            hover_data=["sku_id", "category", "forecast_8w_units", "sales_at_risk_rupees", "locked_capital_rupees"],
            title="Stockout vs Overstock Risk",
        )
        fig.add_hline(y=0.55, line_dash="dash")
        fig.add_vline(x=0.55, line_dash="dash")
        fig.update_layout(height=520)
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader("Action mix")
        action_mix = risk["recommended_action"].value_counts().reset_index()
        action_mix.columns = ["action", "count"]
        fig2 = px.pie(action_mix, values="count", names="action", hole=0.45)
        fig2.update_layout(height=360)
        st.plotly_chart(fig2, use_container_width=True)
        st.subheader("Top priority SKUs")
        st.dataframe(filtered_risk.head(10), use_container_width=True, hide_index=True)

with tab2:
    st.subheader("SKU forecast explorer")
    default_sku = filtered_risk.iloc[0]["sku_id"] if not filtered_risk.empty else risk.iloc[0]["sku_id"]
    sku_options = sorted(risk["sku_id"].unique().tolist())
    selected_sku = st.selectbox("Select SKU", sku_options, index=sku_options.index(default_sku) if default_sku in sku_options else 0)
    hist = weekly[weekly["sku_id"] == selected_sku].sort_values("week_start").tail(40)
    fut = forecasts[forecasts["sku_id"] == selected_sku].sort_values("week_start")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist["week_start"], y=hist["units_sold"], mode="lines+markers", name="Actual demand"))
    fig.add_trace(go.Scatter(x=fut["week_start"], y=fut["baseline_forecast"], mode="lines", name="Seasonal-naive baseline"))
    fig.add_trace(go.Scatter(x=fut["week_start"], y=fut["forecast_units"], mode="lines+markers", name="Model forecast"))
    fig.add_trace(go.Scatter(x=fut["week_start"], y=fut["forecast_upper_80"], mode="lines", name="Upper 80%", line=dict(width=0), showlegend=False))
    fig.add_trace(go.Scatter(x=fut["week_start"], y=fut["forecast_lower_80"], mode="lines", name="80% interval", fill="tonexty", line=dict(width=0)))
    fig.update_layout(title=f"8-week forecast for {selected_sku}", height=520, xaxis_title="Week", yaxis_title="Units")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(fut, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Risk scoring table")
    st.download_button(
        "Download priority action list CSV",
        data=filtered_risk.to_csv(index=False).encode("utf-8"),
        file_name="foresight_priority_action_list.csv",
        mime="text/csv",
    )
    st.dataframe(filtered_risk, use_container_width=True, hide_index=True)

with tab4:
    st.subheader("RetailPulse customer segmentation")
    if customers.empty:
        st.info("Customer analytics is unavailable because the loaded sales file has no customer IDs.")
    else:
        c1, c2 = st.columns([1.15, 1])
        seg = customers.groupby("segment", as_index=False).agg(
            customers=("customer_id", "nunique"),
            revenue=("monetary", "sum"),
            avg_churn_risk=("churn_risk", "mean"),
        ).sort_values("revenue", ascending=False)
        with c1:
            fig = px.bar(seg, x="segment", y="revenue", hover_data=["customers", "avg_churn_risk"], title="Revenue by RFM segment")
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig = px.histogram(customers, x="churn_risk", nbins=30, title="Churn-risk distribution")
            st.plotly_chart(fig, use_container_width=True)
        st.dataframe(customers.sort_values("churn_risk", ascending=False).head(100), use_container_width=True, hide_index=True)

with tab5:
    st.subheader("Project reports")
    for report_name in ["EDA_Memo.md", "Model_Card.md", "Risk_Decisioning.md", "Executive_Readout.md", "DATA_DICTIONARY.md"]:
        path = REPORTS / report_name
        with st.expander(report_name, expanded=report_name == "Executive_Readout.md"):
            st.markdown(path.read_text(encoding="utf-8") if path.exists() else "Report not found.")
# =========================================================
# Extra Tabs: Ask RetailPulse + Drilldown & Geo Insights
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def safe_read_csv(path):
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

risk_extra = safe_read_csv(PROJECT_ROOT / "data" / "processed" / "risk_scores.csv")
sales_extra = safe_read_csv(PROJECT_ROOT / "data" / "raw" / "sales_daily.csv")
customers_extra = safe_read_csv(PROJECT_ROOT / "data" / "processed" / "customer_segments.csv")
metrics_extra = safe_read_csv(PROJECT_ROOT / "data" / "processed" / "model_metrics.csv")


def fmt_money(x):
    try:
        x = float(x)
        if abs(x) >= 1e7:
            return f"₹{x / 1e7:.2f} Cr"
        if abs(x) >= 1e5:
            return f"₹{x / 1e5:.2f} L"
        return f"₹{x:,.0f}"
    except Exception:
        return str(x)


def fmt_pct(x):
    try:
        return f"{float(x) * 100:.1f}%"
    except Exception:
        return str(x)


def ask_retailpulse(question):
    q = question.lower()

    if risk_extra.empty:
        return "Risk data is not available. Please run `python run_all.py` first."

    if "reorder" in q or "restock" in q or "order" in q:
        rows = risk_extra.copy()

        if "recommended_action" in rows.columns:
            rows = rows[
                rows["recommended_action"].astype(str).str.contains("Reorder", case=False, na=False)
            ]

        if "priority_score" in rows.columns:
            rows = rows.sort_values("priority_score", ascending=False)

        ans = "### Reorder priority SKUs\n\n"
        for _, r in rows.head(8).iterrows():
            ans += (
                f"- **{r.get('sku_id', 'SKU')}** | "
                f"Action: **{r.get('recommended_action', 'Review')}** | "
                f"Stockout Risk: **{fmt_pct(r.get('stockout_risk', 0))}** | "
                f"Suggested Qty: **{r.get('recommended_order_qty', 0)}** | "
                f"Sales at Risk: **{fmt_money(r.get('sales_at_risk_rupees', 0))}**\n"
            )

        return ans

    if "overstock" in q or "markdown" in q or "clearance" in q:
        rows = risk_extra.copy()

        if "overstock_risk" in rows.columns:
            rows = rows.sort_values("overstock_risk", ascending=False)

        ans = "### Overstock / markdown SKUs\n\n"
        for _, r in rows.head(8).iterrows():
            ans += (
                f"- **{r.get('sku_id', 'SKU')}** | "
                f"Overstock Risk: **{fmt_pct(r.get('overstock_risk', 0))}** | "
                f"Locked Capital: **{fmt_money(r.get('locked_capital_rupees', 0))}** | "
                f"Action: **{r.get('recommended_action', 'Review')}**\n"
            )

        return ans

    if "churn" in q or "customer" in q or "segment" in q:
        if customers_extra.empty:
            return "Customer segment data is not available."

        if {"segment", "customer_id", "churn_risk", "monetary"}.issubset(customers_extra.columns):
            seg = customers_extra.groupby("segment", as_index=False).agg(
                customers=("customer_id", "count"),
                avg_churn=("churn_risk", "mean"),
                revenue=("monetary", "sum"),
            ).sort_values("avg_churn", ascending=False)

            top = seg.iloc[0]

            return f"""
### Customer churn insight

Highest churn-risk segment: **{top['segment']}**

- Customers: **{int(top['customers'])}**
- Average churn risk: **{fmt_pct(top['avg_churn'])}**
- Revenue value: **{fmt_money(top['revenue'])}**

Recommended action: target this segment with retention offers, coupons, and personalized campaigns.
"""

        return "Customer columns required for churn summary are missing."

    if "accuracy" in q or "wape" in q or "model" in q:
        if metrics_extra.empty:
            return "Model metrics are not available."

        m = metrics_extra.iloc[0]

        return f"""
### Forecast model performance

- Model WAPE: **{fmt_pct(m.get('model_wape', 0))}**
- Baseline WAPE: **{fmt_pct(m.get('baseline_wape', 0))}**
- Model: **{m.get('model', 'Forecasting Model')}**

Lower WAPE means better forecast accuracy.
"""

    if "business impact" in q or "sales at risk" in q or "impact" in q:
        total_sales_risk = risk_extra.get("sales_at_risk_rupees", pd.Series(dtype=float)).sum()
        total_locked = risk_extra.get("locked_capital_rupees", pd.Series(dtype=float)).sum()

        return f"""
### Business impact summary

- Total sales at risk: **{fmt_money(total_sales_risk)}**
- Total locked capital: **{fmt_money(total_locked)}**

This helps managers decide which SKUs need reorder action and which SKUs need markdown or clearance.
"""

    sku_match = re.search(r"sku\s*0*(\d+)", q)
    if sku_match:
        sku_id = f"SKU{int(sku_match.group(1)):04d}"
        row = risk_extra[risk_extra["sku_id"].astype(str).str.upper() == sku_id.upper()]

        if not row.empty:
            r = row.iloc[0]
            return f"""
### SKU explanation: {sku_id}

- Product: **{r.get('sku_name', 'N/A')}**
- Category: **{r.get('category', 'N/A')}**
- Recommended action: **{r.get('recommended_action', 'Review')}**
- Stockout risk: **{fmt_pct(r.get('stockout_risk', 0))}**
- Overstock risk: **{fmt_pct(r.get('overstock_risk', 0))}**
- Sales at risk: **{fmt_money(r.get('sales_at_risk_rupees', 0))}**
- Locked capital: **{fmt_money(r.get('locked_capital_rupees', 0))}**

Reason: **{r.get('reason', 'This SKU needs review based on forecast, inventory, and risk score.')}**
"""

    return """
Ask me questions like:

- Which SKUs should I reorder?
- Which products are overstocked?
- Which customer segment has high churn risk?
- How accurate is the model?
- What is the business impact?
- Why is SKU0025 risky?
"""


# -----------------------------
# Tab 8: Ask RetailPulse
# -----------------------------
with tabs[-2]:
    st.markdown("## 🤖 Ask RetailPulse")
    st.caption("A simple AI-style business assistant that answers using your project data.")

    quick_questions = [
        "Which SKUs should I reorder?",
        "Which products are overstocked?",
        "Which customer segment has high churn risk?",
        "How accurate is the model?",
        "What is the business impact?",
        "Why is SKU0025 risky?",
    ]

    selected_question = st.selectbox("Choose a quick question", quick_questions)

    custom_question = st.text_input(
        "Or type your own question",
        placeholder="Example: Why is SKU0025 risky?"
    )

    final_question = custom_question if custom_question else selected_question

    if st.button("Ask RetailPulse", use_container_width=True):
        st.markdown(ask_retailpulse(final_question))


# -----------------------------
# Tab 9: Drilldown & Geo Insights
# -----------------------------
with tabs[-1]:
    st.markdown("## 🧭 Drilldown & Geo Insights")
    st.caption("Explore category → SKU level risk and region-wise sales performance.")

    if risk_extra.empty:
        st.warning("Risk data not found. Run `python run_all.py` first.")
    else:
        st.markdown("### 📊 Category → SKU Drilldown")

        category_col = "category" if "category" in risk_extra.columns else None

        if category_col:
            selected_category = st.selectbox(
                "Select category",
                sorted(risk_extra[category_col].dropna().unique())
            )

            cat_df = risk_extra[risk_extra[category_col] == selected_category].copy()
        else:
            selected_category = "All"
            cat_df = risk_extra.copy()

        sku_col = "sku_id" if "sku_id" in cat_df.columns else cat_df.columns[0]

        selected_sku = st.selectbox(
            "Select SKU",
            sorted(cat_df[sku_col].astype(str).unique())
        )

        sku_df = cat_df[cat_df[sku_col].astype(str) == selected_sku]

        if not sku_df.empty:
            r = sku_df.iloc[0]

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Stockout Risk", fmt_pct(r.get("stockout_risk", 0)))
            c2.metric("Overstock Risk", fmt_pct(r.get("overstock_risk", 0)))
            c3.metric("Sales at Risk", fmt_money(r.get("sales_at_risk_rupees", 0)))
            c4.metric("Locked Capital", fmt_money(r.get("locked_capital_rupees", 0)))

            st.markdown("### SKU Decision Summary")
            st.write(f"**Recommended Action:** {r.get('recommended_action', 'Review')}")
            st.write(f"**Reason:** {r.get('reason', 'No reason available.')}")

            show_cols = [
                col for col in [
                    "sku_id",
                    "sku_name",
                    "category",
                    "subcategory",
                    "available_units",
                    "forecast_8w_units",
                    "recommended_order_qty",
                    "priority_score",
                    "recommended_action",
                ]
                if col in sku_df.columns
            ]

            st.dataframe(sku_df[show_cols], use_container_width=True)

        st.markdown("---")
        st.markdown("### 🗺️ Geographic Sales View")

        if not sales_extra.empty and "region" in sales_extra.columns:
            value_col = None

            for possible_col in ["sales_amount", "revenue", "net_sales", "amount"]:
                if possible_col in sales_extra.columns:
                    value_col = possible_col
                    break

            if value_col is None:
                if "units_sold" in sales_extra.columns:
                    sales_extra["estimated_sales_value"] = sales_extra["units_sold"] * sales_extra.get("unit_price", 1)
                    value_col = "estimated_sales_value"

            if value_col:
                geo_df = sales_extra.groupby("region", as_index=False)[value_col].sum()
                geo_df = geo_df.rename(columns={value_col: "sales_value"})

                region_coordinates = pd.DataFrame({
                    "region": ["North", "South", "East", "West", "Central"],
                    "lat": [28.6139, 12.9716, 22.5726, 19.0760, 23.2599],
                    "lon": [77.2090, 77.5946, 88.3639, 72.8777, 77.4126],
                })

                geo_df = geo_df.merge(region_coordinates, on="region", how="left")

                fig = px.scatter_geo(
                    geo_df,
                    lat="lat",
                    lon="lon",
                    size="sales_value",
                    hover_name="region",
                    hover_data={"sales_value": ":,.0f"},
                    scope="asia",
                    title="Region-wise Sales Performance"
                )

                fig.update_geos(
                    showcountries=True,
                    showcoastlines=True,
                    showland=True,
                    fitbounds="locations"
                )

                st.plotly_chart(fig, use_container_width=True)

                st.dataframe(geo_df, use_container_width=True)
            else:
                st.info("Could not find a sales/revenue column for geo analysis.")
        else:
            st.info("Region column not found in sales data.")