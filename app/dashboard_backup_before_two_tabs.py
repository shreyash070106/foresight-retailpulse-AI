from __future__ import annotations

from pathlib import Path
import json
import math
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"

st.set_page_config(
    page_title="RetailPulse Foresight AI",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Styling
# -----------------------------
st.markdown(
    """
    <style>
        .main .block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
        div[data-testid="stMetric"] {
            background: linear-gradient(135deg, rgba(20,24,38,.96), rgba(40,50,85,.92));
            border: 1px solid rgba(255,255,255,.11);
            padding: 17px 18px;
            border-radius: 20px;
            box-shadow: 0 12px 32px rgba(0,0,0,.18);
        }
        div[data-testid="stMetric"] label {color: rgba(255,255,255,.72) !important;}
        div[data-testid="stMetricValue"] {color: #ffffff !important; font-size: 1.55rem !important;}
        .hero {
            padding: 24px 28px;
            border-radius: 28px;
            background: radial-gradient(circle at top left, rgba(117,88,255,.35), transparent 31%),
                        linear-gradient(135deg, #0f172a 0%, #172554 42%, #111827 100%);
            color: white;
            border: 1px solid rgba(255,255,255,.13);
            box-shadow: 0 18px 42px rgba(15,23,42,.28);
            margin-bottom: 18px;
        }
        .hero h1 {font-size: 2.35rem; margin-bottom: .25rem;}
        .hero p {font-size: 1.02rem; color: rgba(255,255,255,.80); margin-bottom: 0;}
        .pill {
            display: inline-block;
            padding: 6px 11px;
            border-radius: 999px;
            background: rgba(255,255,255,.12);
            color: rgba(255,255,255,.88);
            border: 1px solid rgba(255,255,255,.14);
            margin-right: 8px;
            margin-top: 12px;
            font-size: .82rem;
        }
        .insight-card {
            padding: 16px 17px;
            border-radius: 18px;
            border: 1px solid rgba(120,120,120,.18);
            background: rgba(127,127,127,.07);
            margin-bottom: 12px;
        }
        .big-number {font-size: 1.55rem; font-weight: 800; margin-bottom: 2px;}
        .small-muted {font-size: .83rem; color: #6b7280;}
        .section-title {font-size: 1.25rem; font-weight: 800; margin: 10px 0 6px 0;}
        .stTabs [data-baseweb="tab-list"] {gap: 10px;}
        .stTabs [data-baseweb="tab"] {
            border-radius: 999px;
            padding: 10px 16px;
            background: rgba(127,127,127,.10);
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Helpers
# -----------------------------
@st.cache_data(show_spinner=False)
def load_outputs():
    weekly = pd.read_csv(PROCESSED / "weekly_demand_features.csv", parse_dates=["week_start"])
    forecasts = pd.read_csv(PROCESSED / "sku_forecasts.csv", parse_dates=["week_start"])
    risk = pd.read_csv(PROCESSED / "risk_scores.csv")
    metrics = pd.read_csv(PROCESSED / "model_metrics.csv")
    customers = pd.read_csv(PROCESSED / "customer_segments.csv")
    backtest = pd.read_csv(PROCESSED / "backtest_predictions.csv", parse_dates=["week_start"])
    summary_path = PROCESSED / "executive_summary.json"
    risk_summary_path = PROCESSED / "risk_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    risk_summary = json.loads(risk_summary_path.read_text(encoding="utf-8")) if risk_summary_path.exists() else {}
    return weekly, forecasts, risk, metrics, customers, backtest, summary, risk_summary


def money(x: float | int | None) -> str:
    try:
        x = float(x)
    except Exception:
        return "₹0"
    if abs(x) >= 1e7:
        return f"₹{x/1e7:,.2f} Cr"
    if abs(x) >= 1e5:
        return f"₹{x/1e5:,.2f} L"
    return f"₹{x:,.0f}"


def pct(x: float | int | None) -> str:
    try:
        return f"{float(x)*100:.1f}%"
    except Exception:
        return "0.0%"


def number(x: float | int | None) -> str:
    try:
        return f"{float(x):,.0f}"
    except Exception:
        return "0"


def safe_div(num: float, den: float) -> float:
    return float(num) / float(den) if float(den or 0) != 0 else 0.0


def card(title: str, value: str, note: str = ""):
    st.markdown(
        f"""
        <div class="insight-card">
            <div class="small-muted">{title}</div>
            <div class="big-number">{value}</div>
            <div class="small-muted">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_report_text(name: str) -> str:
    path = REPORTS / name
    return path.read_text(encoding="utf-8") if path.exists() else "Report not found."


try:
    weekly, forecasts, risk, metrics, customers, backtest, summary, risk_summary = load_outputs()
except FileNotFoundError:
    st.error("Processed files not found. Run `python run_all.py` first, then restart this dashboard.")
    st.stop()

# Normalize columns used in filters
for df in [weekly, forecasts, risk, backtest]:
    for col in ["category", "subcategory", "sku_id"]:
        if col in df.columns:
            df[col] = df[col].astype(str)

# -----------------------------
# Sidebar filters
# -----------------------------
st.sidebar.markdown("## 🎛️ Control Panel")
st.sidebar.caption("Use these filters to turn the dashboard into a planning cockpit.")

category_options = sorted(risk["category"].dropna().unique().tolist())
selected_categories = st.sidebar.multiselect("Category", category_options, default=category_options)

subcategory_options = sorted(risk.loc[risk["category"].isin(selected_categories), "subcategory"].dropna().unique().tolist())
selected_subcategories = st.sidebar.multiselect("Subcategory", subcategory_options, default=subcategory_options)

action_options = sorted(risk["recommended_action"].dropna().unique().tolist())
selected_actions = st.sidebar.multiselect("Recommended action", action_options, default=action_options)

priority_floor = st.sidebar.slider("Minimum priority score", 0.0, 1.0, 0.0, 0.05)
stockout_floor = st.sidebar.slider("Minimum stockout risk", 0.0, 1.0, 0.0, 0.05)

default_start = weekly["week_start"].min().date()
default_end = weekly["week_start"].max().date()
date_range = st.sidebar.date_input("History date range", value=(default_start, default_end), min_value=default_start, max_value=default_end)
if isinstance(date_range, tuple) and len(date_range) == 2:
    date_start, date_end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
else:
    date_start, date_end = weekly["week_start"].min(), weekly["week_start"].max()

search_sku = st.sidebar.text_input("Search SKU / product", placeholder="Example: SKU-001")

filtered_risk = risk.copy()
if selected_categories:
    filtered_risk = filtered_risk[filtered_risk["category"].isin(selected_categories)]
if selected_subcategories:
    filtered_risk = filtered_risk[filtered_risk["subcategory"].isin(selected_subcategories)]
if selected_actions:
    filtered_risk = filtered_risk[filtered_risk["recommended_action"].isin(selected_actions)]
filtered_risk = filtered_risk[
    (filtered_risk["priority_score"] >= priority_floor)
    & (filtered_risk["stockout_risk"] >= stockout_floor)
]
if search_sku.strip():
    q = search_sku.strip().lower()
    filtered_risk = filtered_risk[
        filtered_risk["sku_id"].str.lower().str.contains(q, na=False)
        | filtered_risk["sku_name"].astype(str).str.lower().str.contains(q, na=False)
    ]

selected_skus = filtered_risk["sku_id"].unique().tolist()
filtered_weekly = weekly[
    weekly["sku_id"].isin(selected_skus)
    & (weekly["week_start"] >= date_start)
    & (weekly["week_start"] <= date_end)
].copy()
filtered_forecasts = forecasts[forecasts["sku_id"].isin(selected_skus)].copy()
filtered_backtest = backtest[backtest["sku_id"].isin(selected_skus)].copy()

st.sidebar.divider()
st.sidebar.markdown("### ⚡ Quick actions")
st.sidebar.download_button(
    "Download filtered action list",
    data=filtered_risk.sort_values("priority_score", ascending=False).to_csv(index=False).encode("utf-8"),
    file_name="foresight_filtered_action_list.csv",
    mime="text/csv",
)
with st.sidebar.expander("Need to regenerate data?"):
    st.code("python run_all.py\nstreamlit run app\\dashboard.py", language="powershell")

# -----------------------------
# Header + KPIs
# -----------------------------
st.markdown(
    """
    <div class="hero">
        <h1>📦 RetailPulse Foresight AI</h1>
        <p>AI-powered retail intelligence platform for demand forecasting, inventory risk, customer retention, and business decision support.</p>
        <span class="pill">Demand Forecasting</span>
        <span class="pill">Inventory Risk</span>
        <span class="pill">RFM + Churn</span>
        <span class="pill">What-if Simulator</span>
        <span class="pill">Executive Reports</span>
    </div>
    """,
    unsafe_allow_html=True,
)

metric_row = metrics.iloc[0]
model_wape = float(metric_row.get("model_wape", 0))
baseline_wape = float(metric_row.get("baseline_wape", 0))
improvement = 1 - safe_div(model_wape, max(baseline_wape, 1e-9))
sales_at_risk = float(filtered_risk["sales_at_risk_rupees"].sum())
locked_capital = float(filtered_risk["locked_capital_rupees"].sum())
reorder_count = int((filtered_risk["recommended_action"] == "Reorder now").sum())
markdown_count = int((filtered_risk["recommended_action"] == "Markdown / clear").sum())

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Model WAPE", pct(model_wape), delta=f"{improvement*100:.1f}% better")
k2.metric("Baseline WAPE", pct(baseline_wape))
k3.metric("Sales at risk", money(sales_at_risk))
k4.metric("Locked capital", money(locked_capital))
k5.metric("Reorder SKUs", reorder_count)
k6.metric("Markdown SKUs", markdown_count)

if filtered_risk.empty:
    st.warning("No rows match your filters. Reset the sidebar filters to see the full dashboard.")
    st.stop()

# -----------------------------
# Tabs
# -----------------------------
tabs = st.tabs([
    "🏢 Executive Cockpit",
    "📈 Forecast Lab",
    "🚨 Risk Command",
    "🧪 What-if Simulator",
    "🛒 RetailPulse 360",
    "🔎 Data Explorer",
    "📑 Reports",
])

# -----------------------------
# Executive Cockpit
# -----------------------------
with tabs[0]:
    st.markdown("<div class='section-title'>Executive overview</div>", unsafe_allow_html=True)
    left, mid, right = st.columns([1.15, 1.1, .85])

    with left:
        risk_plot = filtered_risk.copy()
        risk_plot["sales_at_risk_lakh"] = risk_plot["sales_at_risk_rupees"] / 1e5
        fig = px.scatter(
            risk_plot,
            x="overstock_risk",
            y="stockout_risk",
            size="priority_score",
            color="recommended_action",
            hover_name="sku_name",
            hover_data={
                "sku_id": True,
                "category": True,
                "forecast_8w_units": ":,.0f",
                "sales_at_risk_lakh": ":.2f",
                "locked_capital_rupees": ":,.0f",
                "overstock_risk": ":.2f",
                "stockout_risk": ":.2f",
            },
            title="Inventory decision matrix",
            size_max=45,
        )
        fig.add_hrect(y0=.55, y1=1, line_width=0, fillcolor="rgba(255,0,0,.08)")
        fig.add_vrect(x0=.55, x1=1, line_width=0, fillcolor="rgba(255,165,0,.08)")
        fig.add_hline(y=.55, line_dash="dash", opacity=.35)
        fig.add_vline(x=.55, line_dash="dash", opacity=.35)
        fig.update_layout(height=540, legend_title_text="Action")
        st.plotly_chart(fig, use_container_width=True)

    with mid:
        action_mix = filtered_risk.groupby("recommended_action", as_index=False).agg(
            skus=("sku_id", "nunique"),
            sales_at_risk=("sales_at_risk_rupees", "sum"),
            locked_capital=("locked_capital_rupees", "sum"),
            avg_priority=("priority_score", "mean"),
        ).sort_values("skus", ascending=False)
        fig = px.sunburst(
            filtered_risk,
            path=["recommended_action", "category", "subcategory"],
            values="priority_score",
            title="Action pressure by category",
        )
        fig.update_layout(height=540)
        st.plotly_chart(fig, use_container_width=True)

    with right:
        card("Most urgent SKU", str(filtered_risk.sort_values("priority_score", ascending=False).iloc[0]["sku_id"]), "Highest combined risk score")
        card("Forecasted 8W units", number(filtered_risk["forecast_8w_units"].sum()), "Filtered portfolio demand")
        card("Avg stockout risk", pct(filtered_risk["stockout_risk"].mean()), "Across selected SKUs")
        card("Avg overstock risk", pct(filtered_risk["overstock_risk"].mean()), "Across selected SKUs")

    c1, c2 = st.columns([1, 1])
    with c1:
        cat_risk = filtered_risk.groupby("category", as_index=False).agg(
            sales_at_risk=("sales_at_risk_rupees", "sum"),
            locked_capital=("locked_capital_rupees", "sum"),
            skus=("sku_id", "nunique"),
        ).sort_values("sales_at_risk", ascending=False)
        fig = px.bar(cat_risk, x="category", y=["sales_at_risk", "locked_capital"], barmode="group", title="Rupee impact by category")
        fig.update_layout(height=390, yaxis_title="₹ impact")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        trend = filtered_weekly.groupby("week_start", as_index=False).agg(units_sold=("units_sold", "sum"), revenue=("revenue", "sum"))
        fig = px.area(trend, x="week_start", y="revenue", title="Historical revenue trend for selected portfolio")
        fig.update_layout(height=390, yaxis_title="Revenue")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("<div class='section-title'>Board-ready recommendations</div>", unsafe_allow_html=True)
    top_actions = filtered_risk.sort_values("priority_score", ascending=False).head(12).copy()
    top_actions["sales_at_risk_rupees"] = top_actions["sales_at_risk_rupees"].map(money)
    top_actions["locked_capital_rupees"] = top_actions["locked_capital_rupees"].map(money)
    st.dataframe(
        top_actions[["sku_id", "sku_name", "category", "recommended_action", "reason", "recommended_order_qty", "markdown_candidate_units", "sales_at_risk_rupees", "locked_capital_rupees", "priority_score"]],
        use_container_width=True,
        hide_index=True,
    )

# -----------------------------
# Forecast Lab
# -----------------------------
with tabs[1]:
    st.markdown("<div class='section-title'>Forecast lab</div>", unsafe_allow_html=True)
    top_by_priority = filtered_risk.sort_values("priority_score", ascending=False)["sku_id"].head(6).tolist()
    selected_sku = st.selectbox(
        "Select SKU",
        sorted(filtered_risk["sku_id"].unique().tolist()),
        index=0,
        help="Choose any SKU to inspect actual demand, model forecast, baseline forecast, and uncertainty interval.",
    )
    comp_skus = st.multiselect("Compare SKUs", sorted(filtered_risk["sku_id"].unique().tolist()), default=top_by_priority)

    sku_info = filtered_risk[filtered_risk["sku_id"] == selected_sku].iloc[0]
    i1, i2, i3, i4, i5 = st.columns(5)
    i1.metric("Selected SKU", selected_sku)
    i2.metric("Action", sku_info["recommended_action"])
    i3.metric("Stockout risk", pct(sku_info["stockout_risk"]))
    i4.metric("Overstock risk", pct(sku_info["overstock_risk"]))
    i5.metric("Order qty", number(sku_info["recommended_order_qty"]))

    hist = weekly[weekly["sku_id"] == selected_sku].sort_values("week_start").tail(70)
    fut = forecasts[forecasts["sku_id"] == selected_sku].sort_values("week_start")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist["week_start"], y=hist["units_sold"], mode="lines+markers", name="Actual demand"))
    fig.add_trace(go.Scatter(x=fut["week_start"], y=fut["baseline_forecast"], mode="lines", name="Seasonal naive baseline"))
    fig.add_trace(go.Scatter(x=fut["week_start"], y=fut["forecast_units"], mode="lines+markers", name="Model forecast"))
    fig.add_trace(go.Scatter(x=fut["week_start"], y=fut["forecast_upper_80"], mode="lines", name="Upper 80%", line=dict(width=0), showlegend=False))
    fig.add_trace(go.Scatter(x=fut["week_start"], y=fut["forecast_lower_80"], mode="lines", name="80% forecast interval", fill="tonexty", line=dict(width=0)))
    fig.update_layout(title=f"Demand forecast for {selected_sku} — {sku_info['sku_name']}", height=535, xaxis_title="Week", yaxis_title="Units")
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns([1, 1])
    with c1:
        if comp_skus:
            compare = filtered_forecasts[filtered_forecasts["sku_id"].isin(comp_skus)]
            fig = px.line(compare, x="week_start", y="forecast_units", color="sku_id", markers=True, title="Forecast comparison")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        bt = filtered_backtest.copy()
        bt["model_wape_point"] = bt["abs_error_model"] / bt["units_sold"].clip(lower=1)
        bt["baseline_wape_point"] = bt["abs_error_baseline"] / bt["units_sold"].clip(lower=1)
        bt_week = bt.groupby("week_start", as_index=False).agg(model=("model_wape_point", "mean"), baseline=("baseline_wape_point", "mean"))
        fig = px.line(bt_week, x="week_start", y=["model", "baseline"], markers=True, title="Backtest error trend")
        fig.update_layout(height=400, yaxis_tickformat=".0%", yaxis_title="Mean point WAPE")
        st.plotly_chart(fig, use_container_width=True)

    st.expander("Forecast rows for selected SKU", expanded=False).dataframe(fut, use_container_width=True, hide_index=True)

# -----------------------------
# Risk Command
# -----------------------------
with tabs[2]:
    st.markdown("<div class='section-title'>Risk command center</div>", unsafe_allow_html=True)
    r1, r2, r3 = st.columns([1, 1, 1])
    with r1:
        fig = px.bar(
            filtered_risk.sort_values("priority_score", ascending=False).head(15),
            x="priority_score",
            y="sku_id",
            color="recommended_action",
            orientation="h",
            hover_data=["sku_name", "category", "reason"],
            title="Top priority SKUs",
        )
        fig.update_layout(height=460, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)
    with r2:
        heat = filtered_risk.pivot_table(index="category", columns="recommended_action", values="priority_score", aggfunc="mean", fill_value=0)
        fig = px.imshow(heat, text_auto=".2f", aspect="auto", title="Avg priority heatmap")
        fig.update_layout(height=460)
        st.plotly_chart(fig, use_container_width=True)
    with r3:
        fig = px.treemap(
            filtered_risk,
            path=["recommended_action", "category", "sku_id"],
            values="priority_score",
            color="stockout_risk",
            title="Risk tree map",
        )
        fig.update_layout(height=460)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("<div class='section-title'>Smart action list</div>", unsafe_allow_html=True)
    view_cols = [
        "sku_id", "sku_name", "category", "subcategory", "recommended_action", "reason",
        "forecast_8w_units", "available_units", "recommended_order_qty", "markdown_candidate_units",
        "stockout_risk", "overstock_risk", "volatility_risk", "sales_at_risk_rupees", "locked_capital_rupees", "priority_score",
    ]
    st.dataframe(
        filtered_risk.sort_values("priority_score", ascending=False)[view_cols],
        use_container_width=True,
        hide_index=True,
    )

# -----------------------------
# What-if Simulator
# -----------------------------
with tabs[3]:
    st.markdown("<div class='section-title'>Planning simulator</div>", unsafe_allow_html=True)
    st.caption("Change discount, ad spend, lead time, and service level to see how decisions move. This is a planning simulator built on the generated feature columns.")

    sim_sku = st.selectbox("Simulator SKU", sorted(filtered_risk["sku_id"].unique().tolist()), key="sim_sku")
    risk_row = risk[risk["sku_id"] == sim_sku].iloc[0]
    sku_hist = weekly[weekly["sku_id"] == sim_sku].sort_values("week_start").tail(12)
    sku_fut = forecasts[forecasts["sku_id"] == sim_sku].sort_values("week_start")

    s1, s2, s3, s4 = st.columns(4)
    discount_change = s1.slider("Discount change", -20, 40, 0, 5, format="%d%%")
    ad_change = s2.slider("Ad spend change", -50, 150, 0, 10, format="%d%%")
    lead_time_change = s3.slider("Lead time change", -7, 14, 0, 1)
    service_level = s4.slider("Target service level", 0.80, 0.99, 0.92, 0.01)

    base_forecast_8w = float(risk_row["forecast_8w_units"])
    # Transparent assumptions for simulator uplift. It is intentionally simple and explainable for project demonstration.
    discount_uplift = 1 + max(discount_change, -30) * 0.006
    ad_uplift = 1 + ad_change * 0.0025
    simulated_forecast = max(0, base_forecast_8w * discount_uplift * ad_uplift)
    lead_time_days = max(1, float(risk_row["lead_time_days"]) + lead_time_change)
    leadtime_demand = simulated_forecast * (lead_time_days / 56)
    demand_std = float(sku_hist["units_sold"].std() or 0)
    z_lookup = {0.80: 0.84, 0.81: 0.88, 0.82: 0.92, 0.83: 0.95, 0.84: 0.99, 0.85: 1.04, 0.86: 1.08, 0.87: 1.13, 0.88: 1.17, 0.89: 1.23, 0.90: 1.28, 0.91: 1.34, 0.92: 1.41, 0.93: 1.48, 0.94: 1.55, 0.95: 1.64, 0.96: 1.75, 0.97: 1.88, 0.98: 2.05, 0.99: 2.33}
    z = z_lookup.get(round(service_level, 2), 1.41)
    safety_stock = z * demand_std * math.sqrt(lead_time_days / 7)
    available_units = float(risk_row["available_units"])
    suggested_order = max(0, math.ceil(leadtime_demand + safety_stock - available_units))
    simulated_sales = simulated_forecast * float(risk_row.get("forecast_8w_units", 0) and (risk_row["sales_at_risk_rupees"] / max(risk_row["forecast_8w_units"], 1)))

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Base 8W forecast", number(base_forecast_8w))
    m2.metric("Simulated 8W demand", number(simulated_forecast), delta=f"{safe_div(simulated_forecast-base_forecast_8w, base_forecast_8w)*100:.1f}%")
    m3.metric("Lead-time demand", number(leadtime_demand))
    m4.metric("Safety stock", number(safety_stock))
    m5.metric("Suggested order", number(suggested_order))

    c1, c2 = st.columns([1.25, .75])
    with c1:
        sim_curve = sku_fut[["week_start", "forecast_units"]].copy()
        sim_curve["simulated_units"] = sim_curve["forecast_units"] * discount_uplift * ad_uplift
        fig = go.Figure()
        fig.add_trace(go.Bar(x=sim_curve["week_start"], y=sim_curve["forecast_units"], name="Base forecast"))
        fig.add_trace(go.Scatter(x=sim_curve["week_start"], y=sim_curve["simulated_units"], mode="lines+markers", name="Simulated demand"))
        fig.update_layout(title="Base vs simulated weekly demand", height=430, xaxis_title="Week", yaxis_title="Units")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown("#### Decision note")
        if suggested_order > 0:
            st.success(f"Order around **{number(suggested_order)} units** to protect the chosen service level.")
        elif available_units > simulated_forecast * 1.4:
            st.warning("Current inventory still looks high. Consider markdown or bundle promotion.")
        else:
            st.info("Inventory looks balanced for this scenario.")
        st.markdown(
            f"""
            - Current available units: **{number(available_units)}**
            - Current action: **{risk_row['recommended_action']}**
            - Simulated demand value: **{money(simulated_sales)}**
            - Lead time used: **{lead_time_days:.0f} days**
            """
        )

# -----------------------------
# RetailPulse 360
# -----------------------------
with tabs[4]:
    st.markdown("<div class='section-title'>RetailPulse customer 360</div>", unsafe_allow_html=True)
    if customers.empty:
        st.info("Customer analytics is unavailable because the sales file has no customer IDs.")
    else:
        seg = customers.groupby("segment", as_index=False).agg(
            customers=("customer_id", "nunique"),
            revenue=("monetary", "sum"),
            units=("units", "sum"),
            avg_churn_risk=("churn_risk", "mean"),
            avg_return_rate=("return_rate", "mean"),
        ).sort_values("revenue", ascending=False)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Customers", number(customers["customer_id"].nunique()))
        c2.metric("Customer revenue", money(customers["monetary"].sum()))
        c3.metric("High churn customers", number((customers["churn_risk"] > .70).sum()))
        c4.metric("Avg return rate", pct(customers["return_rate"].mean()))

        left, right = st.columns([1.1, 1])
        with left:
            fig = px.bar(seg, x="segment", y="revenue", color="avg_churn_risk", hover_data=["customers", "units", "avg_return_rate"], title="Revenue and churn pressure by segment")
            fig.update_layout(height=440)
            st.plotly_chart(fig, use_container_width=True)
        with right:
            fig = px.scatter(
                customers,
                x="frequency",
                y="monetary",
                size="units",
                color="segment",
                hover_name="customer_id",
                hover_data=["recency_days", "churn_risk", "return_rate", "avg_discount"],
                title="Customer value map",
            )
            fig.update_layout(height=440)
            st.plotly_chart(fig, use_container_width=True)

        a, b = st.columns([.9, 1.1])
        with a:
            selected_segment = st.selectbox("Segment deep dive", seg["segment"].tolist())
            segment_df = customers[customers["segment"] == selected_segment].sort_values("churn_risk", ascending=False)
            card("Selected segment", selected_segment, "Use this section for retention planning")
            card("Segment customers", number(segment_df["customer_id"].nunique()), "Customer count")
            card("Segment revenue", money(segment_df["monetary"].sum()), "Total monetary value")
        with b:
            fig = px.histogram(segment_df, x="churn_risk", nbins=20, title=f"Churn-risk distribution — {selected_segment}")
            fig.update_layout(height=360, xaxis_tickformat=".0%")
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Retention action queue")
        retention = customers.sort_values(["churn_risk", "monetary"], ascending=[False, False]).head(80)
        st.dataframe(retention, use_container_width=True, hide_index=True)
        st.download_button("Download retention list", retention.to_csv(index=False).encode("utf-8"), "retailpulse_retention_list.csv", "text/csv")

# -----------------------------
# Data Explorer
# -----------------------------
with tabs[5]:
    st.markdown("<div class='section-title'>Data explorer and health check</div>", unsafe_allow_html=True)
    data_name = st.radio("Choose dataset", ["Weekly demand features", "Forecasts", "Risk scores", "Customers", "Backtest"], horizontal=True)
    data_map = {
        "Weekly demand features": filtered_weekly,
        "Forecasts": filtered_forecasts,
        "Risk scores": filtered_risk,
        "Customers": customers,
        "Backtest": filtered_backtest,
    }
    df = data_map[data_name].copy()
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Rows", number(len(df)))
    d2.metric("Columns", number(df.shape[1]))
    d3.metric("Missing cells", number(int(df.isna().sum().sum())))
    d4.metric("Duplicate rows", number(int(df.duplicated().sum())))

    col_picker = st.multiselect("Columns to display", df.columns.tolist(), default=df.columns.tolist()[:min(12, len(df.columns))])
    st.dataframe(df[col_picker] if col_picker else df, use_container_width=True, hide_index=True)

    n1, n2 = st.columns([1, 1])
    with n1:
        missing = df.isna().mean().mul(100).reset_index()
        missing.columns = ["column", "missing_pct"]
        missing = missing[missing["missing_pct"] > 0].sort_values("missing_pct", ascending=False)
        if not missing.empty:
            fig = px.bar(missing.head(20), x="missing_pct", y="column", orientation="h", title="Missing value profile")
            fig.update_layout(height=380)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("No missing values detected in this filtered view.")
    with n2:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        if numeric_cols:
            chosen_num = st.selectbox("Numeric column profile", numeric_cols)
            fig = px.histogram(df, x=chosen_num, nbins=40, title=f"Distribution of {chosen_num}")
            fig.update_layout(height=380)
            st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Reports
# -----------------------------
with tabs[6]:
    st.markdown("<div class='section-title'>Executive reports and final project notes</div>", unsafe_allow_html=True)
    report_names = ["Executive_Readout.md", "Risk_Decisioning.md", "Model_Card.md", "EDA_Memo.md", "DATA_DICTIONARY.md"]
    chosen_report = st.selectbox("Open report", report_names)
    st.markdown(get_report_text(chosen_report))

    st.divider()
    st.markdown("#### Auto-generated meeting summary")
    biggest_category = filtered_risk.groupby("category")["sales_at_risk_rupees"].sum().sort_values(ascending=False).index[0]
    top_sku_row = filtered_risk.sort_values("priority_score", ascending=False).iloc[0]
    meeting_summary = f"""
### FORESIGHT + RetailPulse Planning Summary

- Filtered portfolio has **{filtered_risk['sku_id'].nunique()} SKUs** under monitoring.
- Estimated sales at risk is **{money(sales_at_risk)}**, while locked capital is **{money(locked_capital)}**.
- The highest priority SKU is **{top_sku_row['sku_id']} - {top_sku_row['sku_name']}**, with action **{top_sku_row['recommended_action']}**.
- The category with maximum sales-at-risk is **{biggest_category}**.
- Model WAPE is **{pct(model_wape)}** versus baseline WAPE of **{pct(baseline_wape)}**, giving an improvement of **{improvement*100:.1f}%**.
- Immediate business focus: reorder high-risk SKUs, markdown overstocked SKUs, and target high churn RetailPulse customer segments.
"""
    st.markdown(meeting_summary)
    st.download_button("Download meeting summary", meeting_summary.encode("utf-8"), "executive_meeting_summary.md", "text/markdown")
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