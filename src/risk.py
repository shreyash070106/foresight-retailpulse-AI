from __future__ import annotations

from pathlib import Path
import json
import numpy as np
import pandas as pd

from src.config import PROCESSED_DIR, load_config, ensure_directories


def _clip01(x):
    return float(np.clip(x, 0, 1))


def score_risk(forecasts: pd.DataFrame) -> pd.DataFrame:
    cfg = load_config()
    forecasts = forecasts.copy()
    forecasts["week_start"] = pd.to_datetime(forecasts["week_start"])
    rows = []
    for sku_id, g in forecasts.groupby("sku_id"):
        g = g.sort_values("horizon_week")
        first = g.iloc[0]
        lead_weeks = int(np.ceil(float(first["lead_time_days"]) / 7.0))
        lead_weeks = max(1, min(lead_weeks, int(g["horizon_week"].max())))
        demand_lead = float(g.head(lead_weeks)["forecast_units"].sum())
        demand_horizon = float(g["forecast_units"].sum())
        available = float(first["on_hand_units"] + first["on_order_units"] - first.get("damaged_units", 0) - first.get("reserved_units", 0))
        available = max(available, 0)
        safety_stock = cfg.safety_stock_multiplier * max(float(first["reorder_point"]), demand_lead * 0.35)
        projected_gap = demand_lead + safety_stock - available
        stockout_risk = _clip01(projected_gap / (demand_lead + safety_stock + 1))

        excess_units = max(float(first["on_hand_units"]) - demand_horizon * 1.45, 0)
        overstock_risk = _clip01(excess_units / (float(first["on_hand_units"]) + 1))
        volatility = float(g["forecast_units"].std() / (g["forecast_units"].mean() + 1))
        volatility_risk = _clip01(volatility)

        if stockout_risk >= cfg.stockout_threshold and overstock_risk < cfg.overstock_threshold:
            action = "Reorder now"
            reason = "Forecasted lead-time demand can exceed available stock."
        elif overstock_risk >= cfg.overstock_threshold and stockout_risk < cfg.stockout_threshold:
            action = "Markdown / clear"
            reason = "On-hand stock is materially higher than expected horizon demand."
        elif stockout_risk >= cfg.stockout_threshold and overstock_risk >= cfg.overstock_threshold:
            action = "Watch / volatile"
            reason = "SKU shows both shortage and excess signals; review manually."
        else:
            action = "Healthy"
            reason = "Inventory appears aligned with the forecast."

        sales_at_risk_units = max(projected_gap, 0)
        sales_at_risk = sales_at_risk_units * float(first["list_price"])
        locked_capital = excess_units * float(first["unit_cost"])
        recommended_order_qty = int(np.ceil(max(projected_gap, 0)))
        markdown_candidate_units = int(np.ceil(excess_units))

        rows.append({
            "sku_id": sku_id,
            "sku_name": first.get("sku_name", sku_id),
            "category": first["category"],
            "subcategory": first["subcategory"],
            "forecast_8w_units": round(demand_horizon, 2),
            "forecast_leadtime_units": round(demand_lead, 2),
            "available_units": round(available, 2),
            "on_hand_units": float(first["on_hand_units"]),
            "on_order_units": float(first["on_order_units"]),
            "lead_time_days": float(first["lead_time_days"]),
            "reorder_point": float(first["reorder_point"]),
            "stockout_risk": round(stockout_risk, 4),
            "overstock_risk": round(overstock_risk, 4),
            "volatility_risk": round(volatility_risk, 4),
            "recommended_action": action,
            "reason": reason,
            "recommended_order_qty": recommended_order_qty,
            "markdown_candidate_units": markdown_candidate_units,
            "sales_at_risk_rupees": round(sales_at_risk, 2),
            "locked_capital_rupees": round(locked_capital, 2),
            "priority_score": round(100 * (0.48 * stockout_risk + 0.32 * overstock_risk + 0.20 * volatility_risk), 2),
        })
    result = pd.DataFrame(rows)
    return result.sort_values("priority_score", ascending=False).reset_index(drop=True)


def run_risk_scoring(processed_dir: Path = PROCESSED_DIR) -> dict[str, Path]:
    ensure_directories()
    forecasts = pd.read_csv(processed_dir / "sku_forecasts.csv")
    risk = score_risk(forecasts)
    path = processed_dir / "risk_scores.csv"
    risk.to_csv(path, index=False)
    summary = {
        "total_sales_at_risk_rupees": float(risk["sales_at_risk_rupees"].sum()),
        "total_locked_capital_rupees": float(risk["locked_capital_rupees"].sum()),
        "reorder_now_skus": int((risk["recommended_action"] == "Reorder now").sum()),
        "markdown_clear_skus": int((risk["recommended_action"] == "Markdown / clear").sum()),
        "watch_volatile_skus": int((risk["recommended_action"] == "Watch / volatile").sum()),
        "healthy_skus": int((risk["recommended_action"] == "Healthy").sum()),
    }
    (processed_dir / "risk_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return {"risk_scores": path}


if __name__ == "__main__":
    for name, path in run_risk_scoring().items():
        print(f"created {name}: {path}")
