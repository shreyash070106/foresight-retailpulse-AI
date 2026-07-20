from __future__ import annotations

from pathlib import Path
import json
import pandas as pd

from src.config import PROCESSED_DIR, REPORTS_DIR, ensure_directories


def _money(x: float) -> str:
    return f"₹{x:,.0f}"


def _pct(x: float) -> str:
    return f"{x*100:.1f}%"


def build_reports(processed_dir: Path = PROCESSED_DIR, reports_dir: Path = REPORTS_DIR) -> dict[str, Path]:
    ensure_directories()
    weekly = pd.read_csv(processed_dir / "weekly_demand_features.csv")
    metrics = pd.read_csv(processed_dir / "model_metrics.csv")
    risk = pd.read_csv(processed_dir / "risk_scores.csv")
    customers = pd.read_csv(processed_dir / "customer_segments.csv")
    forecasts = pd.read_csv(processed_dir / "sku_forecasts.csv")

    overall = metrics.iloc[0].to_dict()
    sales_at_risk = float(risk["sales_at_risk_rupees"].sum())
    locked_capital = float(risk["locked_capital_rupees"].sum())
    reorder_count = int((risk["recommended_action"] == "Reorder now").sum())
    markdown_count = int((risk["recommended_action"] == "Markdown / clear").sum())
    watch_count = int((risk["recommended_action"] == "Watch / volatile").sum())
    healthy_count = int((risk["recommended_action"] == "Healthy").sum())
    wape_improvement = 1 - float(overall["model_wape"]) / max(float(overall["baseline_wape"]), 1e-9)

    category_summary = weekly.groupby("category", as_index=False).agg(
        revenue=("revenue", "sum"),
        units_sold=("units_sold", "sum"),
        sku_count=("sku_id", "nunique"),
        avg_inventory_cover=("inventory_cover_weeks", "mean"),
    ).sort_values("revenue", ascending=False)
    top_risk = risk.head(10)[["sku_id", "category", "recommended_action", "priority_score", "sales_at_risk_rupees", "locked_capital_rupees"]]
    segment_summary = customers.groupby("segment", as_index=False).agg(
        customers=("customer_id", "nunique"),
        revenue=("monetary", "sum"),
        avg_churn_risk=("churn_risk", "mean"),
    ).sort_values("revenue", ascending=False) if not customers.empty else pd.DataFrame()

    eda = f"""
# Data Quality & EDA Memo — FORESIGHT + RetailPulse

## Dataset overview

- Weekly SKU records prepared: **{len(weekly):,}**
- SKUs: **{weekly['sku_id'].nunique():,}**
- Categories: **{weekly['category'].nunique():,}**
- Forecast horizon: **{forecasts['horizon_week'].max()} weeks**
- Customer records used for RFM: **{customers['customer_id'].nunique() if not customers.empty else 0:,}**

## Revenue and demand patterns

The highest revenue categories are:

{category_summary.head(8).to_markdown(index=False)}

## Data quality checks performed

- Required schema validation for `sales_daily`, `sku_master`, `calendar`, and `inventory_snapshots`.
- Duplicate raw export rows removed.
- Missing prices filled using SKU list price.
- Negative unit, inventory, and revenue values clipped to valid ranges.
- Inventory snapshots forward-filled/back-filled per SKU to support weekly modelling.
- Lag and rolling features created without using future demand.

## Business observations

1. Promotion and campaign intensity produce visible lifts in weekly demand.
2. Slow-moving SKUs are the main source of locked working capital.
3. High-demand SKUs with long lead times create the strongest stockout exposure.
4. RetailPulse customer segmentation adds retention context, while FORESIGHT remains focused on stock planning.
"""

    model_card = f"""
# Model Card — Demand Forecasting

## Objective

Forecast weekly SKU demand for the next 8 weeks and compare against a seasonal-naive baseline.

## Selected model

- Model: **Ridge Regression**
- Target: weekly `units_sold`
- Features: lag demand, rolling demand, calendar, promotions, price, inventory, and SKU attributes.

## Backtest result

| Metric | Value |
|---|---:|
| Model WAPE | {_pct(float(overall['model_wape']))} |
| Seasonal-naive WAPE | {_pct(float(overall['baseline_wape']))} |
| WAPE improvement | {_pct(wape_improvement)} |
| Model bias | {_pct(float(overall['model_bias']))} |
| Test rows | {int(overall['test_rows']):,} |

## Why this model is used

Ridge regression is transparent, fast, stable on moderate-size retail datasets, and easier to defend to a non-technical stakeholder than an unnecessarily complex model. The baseline remains visible so the forecast is judged honestly.

## Limitations

- Forecast quality depends on the quality of the raw extracts.
- Future promotion plans are approximated if no official promotion calendar is supplied.
- The model should be retrained after each monthly data refresh.
"""

    risk_doc = f"""
# Risk Decisioning Memo

## Decision logic

Each SKU receives three risk signals:

1. **Stockout risk** — lead-time forecast demand plus safety stock compared with available inventory.
2. **Overstock risk** — on-hand inventory compared with expected 8-week demand.
3. **Volatility risk** — forecast variability over the horizon.

## Recommended actions

| Action | Count |
|---|---:|
| Reorder now | {reorder_count} |
| Markdown / clear | {markdown_count} |
| Watch / volatile | {watch_count} |
| Healthy | {healthy_count} |

## Business impact

- Sales at risk: **{_money(sales_at_risk)}**
- Locked capital: **{_money(locked_capital)}**

## Top priority SKUs

{top_risk.to_markdown(index=False)}
"""

    executive = f"""
# Executive Readout — FORESIGHT + RetailPulse

## Recommendation summary

NorthBay Living should act first on high-priority **Reorder now** SKUs to protect revenue, then clear excess inventory for **Markdown / clear** SKUs to release working capital.

## Project result

| Result | Value |
|---|---:|
| Selected model | Ridge Regression |
| Model WAPE | {_pct(float(overall['model_wape']))} |
| Seasonal-naive baseline WAPE | {_pct(float(overall['baseline_wape']))} |
| WAPE improvement | {_pct(wape_improvement)} |
| Sales at risk | {_money(sales_at_risk)} |
| Locked capital | {_money(locked_capital)} |
| Reorder-now SKUs | {reorder_count} |
| Markdown / clear SKUs | {markdown_count} |

## What the operations team can do now

1. Open the Streamlit dashboard and filter by category or SKU.
2. Review the priority score and action recommendation.
3. Reorder SKUs where lead-time demand can exceed available inventory.
4. Apply markdown or promotional clearance to slow-moving overstock.
5. Use the FastAPI endpoint for SKU-level forecast and risk lookup.

## RetailPulse customer insight

Customer analytics was added as an enhanced layer using RFM segmentation and churn-risk scoring. It supports retention and campaign planning, while the main FORESIGHT deliverable remains demand and inventory decisioning.

{segment_summary.to_markdown(index=False) if not segment_summary.empty else 'No customer segmentation available.'}

## Final conclusion

The project is reproducible, stakeholder-facing, and aligned with the internship brief: it forecasts demand, flags stockout and overstock risk, quantifies rupee impact, and provides both dashboard and API consumption layers.
"""

    dictionary = """
# Data Dictionary — Enhanced FORESIGHT + RetailPulse Dataset

## sales_daily.csv

Core columns: `date`, `sku_id`, `units_sold`, `revenue`, `unit_price`, `promo_flag`  
Enhanced columns: `customer_id`, `order_id`, `sales_channel`, `region`, `discount_pct`, `ad_spend`, `page_views`, `return_units`, `stockout_flag`

## sku_master.csv

Core columns: `sku_id`, `category`, `subcategory`, `launch_date`, `unit_cost`, `list_price`  
Enhanced columns: `sku_name`, `brand`, `supplier`, `size`, `color`, `lifecycle_stage`, `target_margin`

## calendar.csv

Core columns: `date`, `week`, `month`, `season`, `is_holiday`, `promo_event`  
Enhanced columns: `quarter`, `holiday_name`, `day_of_week`, `is_weekend`, `campaign_intensity`, `weather_index`

## inventory_snapshots.csv

Core columns: `date`, `sku_id`, `on_hand_units`, `on_order_units`, `lead_time_days`, `reorder_point`  
Enhanced columns: `warehouse_zone`, `damaged_units`, `reserved_units`, `inventory_snapshot_quality`
"""

    paths = {
        "EDA_Memo": reports_dir / "EDA_Memo.md",
        "Model_Card": reports_dir / "Model_Card.md",
        "Risk_Decisioning": reports_dir / "Risk_Decisioning.md",
        "Executive_Readout": reports_dir / "Executive_Readout.md",
        "DATA_DICTIONARY": reports_dir / "DATA_DICTIONARY.md",
    }
    paths["EDA_Memo"].write_text(eda.strip() + "\n", encoding="utf-8")
    paths["Model_Card"].write_text(model_card.strip() + "\n", encoding="utf-8")
    paths["Risk_Decisioning"].write_text(risk_doc.strip() + "\n", encoding="utf-8")
    paths["Executive_Readout"].write_text(executive.strip() + "\n", encoding="utf-8")
    paths["DATA_DICTIONARY"].write_text(dictionary.strip() + "\n", encoding="utf-8")

    summary = {
        "model_wape": float(overall["model_wape"]),
        "baseline_wape": float(overall["baseline_wape"]),
        "wape_improvement": float(wape_improvement),
        "sales_at_risk_rupees": sales_at_risk,
        "locked_capital_rupees": locked_capital,
        "reorder_now_skus": reorder_count,
        "markdown_clear_skus": markdown_count,
        "watch_volatile_skus": watch_count,
        "healthy_skus": healthy_count,
    }
    (processed_dir / "executive_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return paths


if __name__ == "__main__":
    for name, path in build_reports().items():
        print(f"created {name}: {path}")
