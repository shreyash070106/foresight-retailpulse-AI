from __future__ import annotations

from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.config import PROCESSED_DIR, load_config, ensure_directories

NUMERIC_FEATURES = [
    "avg_unit_price", "promo_days", "avg_discount", "ad_spend", "page_views", "stockout_days",
    "campaign_intensity", "holiday_days", "weekend_days", "unit_cost", "list_price", "target_margin",
    "on_hand_units", "on_order_units", "lead_time_days", "reorder_point", "damaged_units", "reserved_units",
    "gross_margin", "lag_1", "lag_2", "lag_4", "lag_8", "lag_13", "lag_26", "lag_52",
    "rolling_4_mean", "rolling_8_mean", "rolling_13_std", "sell_through_proxy", "inventory_cover_weeks", "month", "week",
]
CATEGORICAL_FEATURES = ["category", "subcategory", "brand", "lifecycle_stage", "warehouse_zone"]
TARGET = "units_sold"


def wape(actual: np.ndarray, forecast: np.ndarray) -> float:
    actual = np.asarray(actual, dtype=float)
    forecast = np.asarray(forecast, dtype=float)
    denom = np.sum(np.abs(actual))
    if denom == 0:
        return float(np.mean(np.abs(actual - forecast)))
    return float(np.sum(np.abs(actual - forecast)) / denom)


def bias(actual: np.ndarray, forecast: np.ndarray) -> float:
    actual = np.asarray(actual, dtype=float)
    forecast = np.asarray(forecast, dtype=float)
    denom = np.sum(np.abs(actual))
    if denom == 0:
        return 0.0
    return float(np.sum(forecast - actual) / denom)


def build_model() -> Pipeline:
    numeric = Pipeline(steps=[("scaler", StandardScaler())])
    categorical = Pipeline(steps=[("onehot", OneHotEncoder(handle_unknown="ignore", min_frequency=5))])
    preprocess = ColumnTransformer(
        transformers=[
            ("num", numeric, NUMERIC_FEATURES),
            ("cat", categorical, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )
    return Pipeline(steps=[("preprocess", preprocess), ("model", Ridge(alpha=2.5, random_state=42))])


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["week_start"] = pd.to_datetime(out["week_start"])
    for col in NUMERIC_FEATURES:
        if col not in out.columns:
            out[col] = 0
        out[col] = pd.to_numeric(out[col], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0)
    for col in CATEGORICAL_FEATURES:
        if col not in out.columns:
            out[col] = "Unknown"
        out[col] = out[col].fillna("Unknown").astype(str)
    out[TARGET] = pd.to_numeric(out[TARGET], errors="coerce").fillna(0).clip(lower=0)
    return out


def backtest_model(weekly: pd.DataFrame, horizon_weeks: int = 8) -> tuple[Pipeline, pd.DataFrame, pd.DataFrame]:
    weekly = _prepare(weekly)
    max_week = weekly["week_start"].max()
    test_start = max_week - pd.Timedelta(weeks=horizon_weeks - 1)
    train = weekly[weekly["week_start"] < test_start].copy()
    test = weekly[weekly["week_start"] >= test_start].copy()

    model = build_model()
    model.fit(train[NUMERIC_FEATURES + CATEGORICAL_FEATURES], train[TARGET])
    pred = np.clip(model.predict(test[NUMERIC_FEATURES + CATEGORICAL_FEATURES]), 0, None)
    baseline = test["lag_52"].fillna(test["lag_4"]).fillna(test["rolling_4_mean"]).fillna(0).to_numpy()

    residual = test[TARGET].to_numpy() - pred
    pred_df = test[["sku_id", "week_start", "category", "subcategory", TARGET]].copy()
    pred_df["model_forecast"] = pred
    pred_df["seasonal_naive_forecast"] = baseline
    pred_df["residual"] = residual
    pred_df["abs_error_model"] = np.abs(pred_df[TARGET] - pred_df["model_forecast"])
    pred_df["abs_error_baseline"] = np.abs(pred_df[TARGET] - pred_df["seasonal_naive_forecast"])

    metric_rows = []
    metric_rows.append({
        "scope": "overall",
        "model": "ridge_regression",
        "model_wape": wape(test[TARGET], pred),
        "baseline_wape": wape(test[TARGET], baseline),
        "model_bias": bias(test[TARGET], pred),
        "baseline_bias": bias(test[TARGET], baseline),
        "mae": mean_absolute_error(test[TARGET], pred),
        "test_weeks": horizon_weeks,
        "train_rows": len(train),
        "test_rows": len(test),
    })
    by_category = pred_df.groupby("category").apply(lambda g: pd.Series({
        "model_wape": wape(g[TARGET], g["model_forecast"]),
        "baseline_wape": wape(g[TARGET], g["seasonal_naive_forecast"]),
        "model_bias": bias(g[TARGET], g["model_forecast"]),
        "test_rows": len(g),
    }), include_groups=False).reset_index().rename(columns={"category": "scope"})
    by_category["model"] = "ridge_regression"
    by_category["baseline_bias"] = np.nan
    by_category["mae"] = np.nan
    by_category["test_weeks"] = horizon_weeks
    by_category["train_rows"] = len(train)
    metrics = pd.concat([pd.DataFrame(metric_rows), by_category[pd.DataFrame(metric_rows).columns]], ignore_index=True)

    final_model = build_model()
    final_model.fit(weekly[NUMERIC_FEATURES + CATEGORICAL_FEATURES], weekly[TARGET])
    return final_model, metrics, pred_df


def make_future_frame(weekly: pd.DataFrame, horizon_weeks: int) -> pd.DataFrame:
    weekly = _prepare(weekly)
    history = weekly.copy().sort_values(["sku_id", "week_start"])
    last_week = history["week_start"].max()
    rows = []
    for sku_id, g in history.groupby("sku_id"):
        g = g.sort_values("week_start")
        last = g.iloc[-1].copy()
        demand_history = list(g[TARGET].astype(float).values)
        for h in range(1, horizon_weeks + 1):
            row = last.copy()
            row["week_start"] = last_week + pd.Timedelta(weeks=h)
            row["month"] = int(row["week_start"].month)
            row["week"] = int(row["week_start"].isocalendar().week)
            row["promo_days"] = float(1 if row["month"] in [10, 11, 12] else 0)
            row["campaign_intensity"] = float(3 if row["month"] in [10, 11] else 1 if row["month"] in [6, 7, 12] else 0)
            row["holiday_days"] = float(1 if row["month"] in [8, 10, 12, 1] and h % 3 == 0 else 0)
            row["lag_1"] = demand_history[-1] if len(demand_history) >= 1 else 0
            row["lag_2"] = demand_history[-2] if len(demand_history) >= 2 else row["lag_1"]
            row["lag_4"] = demand_history[-4] if len(demand_history) >= 4 else np.mean(demand_history[-4:])
            row["lag_8"] = demand_history[-8] if len(demand_history) >= 8 else np.mean(demand_history[-8:])
            row["lag_13"] = demand_history[-13] if len(demand_history) >= 13 else np.mean(demand_history[-13:])
            row["lag_26"] = demand_history[-26] if len(demand_history) >= 26 else np.mean(demand_history[-26:])
            row["lag_52"] = demand_history[-52] if len(demand_history) >= 52 else row["lag_4"]
            row["rolling_4_mean"] = float(np.mean(demand_history[-4:]))
            row["rolling_8_mean"] = float(np.mean(demand_history[-8:]))
            row["rolling_13_std"] = float(np.std(demand_history[-13:])) if len(demand_history) >= 2 else 0
            row["units_sold"] = np.nan
            rows.append(row)
            # placeholder for recursive next step; will be replaced with model prediction later.
            demand_history.append(float(row["rolling_4_mean"]))
    return pd.DataFrame(rows)


def forecast_future(model: Pipeline, weekly: pd.DataFrame, backtest_predictions: pd.DataFrame, horizon_weeks: int = 8) -> pd.DataFrame:
    future = make_future_frame(weekly, horizon_weeks)
    future = _prepare(future.assign(units_sold=0))
    preds = []
    # Predict in chronological order and update lag values recursively.
    for h_week in sorted(future["week_start"].unique()):
        mask = future["week_start"] == h_week
        pred = np.clip(model.predict(future.loc[mask, NUMERIC_FEATURES + CATEGORICAL_FEATURES]), 0, None)
        preds.extend(pred)
    future["forecast_units"] = preds
    residual_std = float(backtest_predictions["residual"].std()) if len(backtest_predictions) else 1.0
    future["forecast_lower_80"] = np.clip(future["forecast_units"] - 1.28 * residual_std, 0, None)
    future["forecast_upper_80"] = future["forecast_units"] + 1.28 * residual_std
    future["baseline_forecast"] = future["lag_52"].fillna(future["lag_4"]).fillna(future["rolling_4_mean"]).fillna(0)
    future["horizon_week"] = ((future["week_start"] - future["week_start"].min()).dt.days // 7 + 1).astype(int)
    keep = [
        "sku_id", "sku_name", "category", "subcategory", "week_start", "horizon_week", "forecast_units", "forecast_lower_80", "forecast_upper_80",
        "baseline_forecast", "avg_unit_price", "unit_cost", "list_price", "on_hand_units", "on_order_units", "lead_time_days", "reorder_point",
        "damaged_units", "reserved_units", "lifecycle_stage"
    ]
    return future[keep]


def run_forecasting(processed_dir: Path = PROCESSED_DIR) -> dict[str, Path]:
    ensure_directories()
    cfg = load_config()
    weekly_path = processed_dir / "weekly_demand_features.csv"
    weekly = pd.read_csv(weekly_path)
    model, metrics, backtest_preds = backtest_model(weekly, cfg.forecast_horizon_weeks)
    forecasts = forecast_future(model, weekly, backtest_preds, cfg.forecast_horizon_weeks)

    paths = {
        "model_metrics": processed_dir / "model_metrics.csv",
        "backtest_predictions": processed_dir / "backtest_predictions.csv",
        "sku_forecasts": processed_dir / "sku_forecasts.csv",
    }
    metrics.to_csv(paths["model_metrics"], index=False)
    backtest_preds.to_csv(paths["backtest_predictions"], index=False)
    forecasts.to_csv(paths["sku_forecasts"], index=False)
    summary = metrics.iloc[0].to_dict()
    (processed_dir / "model_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    return paths


if __name__ == "__main__":
    for name, path in run_forecasting().items():
        print(f"created {name}: {path}")
