from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

app = FastAPI(
    title="FORESIGHT + RetailPulse Scoring API",
    description="Returns SKU-level demand forecast, inventory risk, and recommended action.",
    version="1.0.0",
)


class BatchRequest(BaseModel):
    sku_ids: List[str]


def _load():
    forecasts = pd.read_csv(PROCESSED / "sku_forecasts.csv")
    risk = pd.read_csv(PROCESSED / "risk_scores.csv")
    return forecasts, risk


@app.get("/health")
def health():
    forecasts_exists = (PROCESSED / "sku_forecasts.csv").exists()
    risk_exists = (PROCESSED / "risk_scores.csv").exists()
    return {"status": "ok" if forecasts_exists and risk_exists else "missing_outputs", "forecasts": forecasts_exists, "risk": risk_exists}


@app.get("/skus")
def list_skus(limit: int = 50):
    _, risk = _load()
    return risk[["sku_id", "sku_name", "category", "recommended_action", "priority_score"]].head(limit).to_dict(orient="records")


@app.get("/sku/{sku_id}")
def sku_detail(sku_id: str):
    forecasts, risk = _load()
    risk_row = risk[risk["sku_id"] == sku_id]
    if risk_row.empty:
        raise HTTPException(status_code=404, detail=f"SKU not found: {sku_id}")
    forecast_rows = forecasts[forecasts["sku_id"] == sku_id].sort_values("horizon_week")
    return {"risk": risk_row.iloc[0].to_dict(), "forecast": forecast_rows.to_dict(orient="records")}


@app.get("/score/{sku_id}")
def score_sku(sku_id: str):
    _, risk = _load()
    risk_row = risk[risk["sku_id"] == sku_id]
    if risk_row.empty:
        raise HTTPException(status_code=404, detail=f"SKU not found: {sku_id}")
    row = risk_row.iloc[0].to_dict()
    return {
        "sku_id": row["sku_id"],
        "category": row["category"],
        "forecast_8w_units": row["forecast_8w_units"],
        "stockout_risk": row["stockout_risk"],
        "overstock_risk": row["overstock_risk"],
        "recommended_action": row["recommended_action"],
        "priority_score": row["priority_score"],
        "sales_at_risk_rupees": row["sales_at_risk_rupees"],
        "locked_capital_rupees": row["locked_capital_rupees"],
        "reason": row["reason"],
    }


@app.post("/batch-score")
def batch_score(request: BatchRequest):
    _, risk = _load()
    found = risk[risk["sku_id"].isin(request.sku_ids)]
    return found.to_dict(orient="records")


@app.get("/summary")
def summary():
    _, risk = _load()
    return {
        "sales_at_risk_rupees": float(risk["sales_at_risk_rupees"].sum()),
        "locked_capital_rupees": float(risk["locked_capital_rupees"].sum()),
        "action_counts": risk["recommended_action"].value_counts().to_dict(),
        "sku_count": int(risk["sku_id"].nunique()),
    }
