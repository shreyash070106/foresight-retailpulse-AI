from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

from src.config import RAW_DIR, PROCESSED_DIR, ensure_directories

REQUIRED_COLUMNS = {
    "sales_daily": {"date", "sku_id", "units_sold", "revenue", "unit_price", "promo_flag"},
    "sku_master": {"sku_id", "category", "subcategory", "launch_date", "unit_cost", "list_price"},
    "calendar": {"date", "week", "month", "season", "is_holiday", "promo_event"},
    "inventory_snapshots": {"date", "sku_id", "on_hand_units", "on_order_units", "lead_time_days", "reorder_point"},
}


def _read_csv(name: str, raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    path = raw_dir / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing required raw file: {path}")
    df = pd.read_csv(path)
    missing = REQUIRED_COLUMNS[name] - set(df.columns)
    if missing:
        raise ValueError(f"{name}.csv is missing required columns: {sorted(missing)}")
    return df


def load_raw_data(raw_dir: Path = RAW_DIR) -> dict[str, pd.DataFrame]:
    return {name: _read_csv(name, raw_dir) for name in REQUIRED_COLUMNS}


def clean_data(raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    sales = raw["sales_daily"].copy()
    sku = raw["sku_master"].copy()
    cal = raw["calendar"].copy()
    inv = raw["inventory_snapshots"].copy()

    for df in [sales, cal, inv]:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    sku["launch_date"] = pd.to_datetime(sku["launch_date"], errors="coerce")

    sales = sales.dropna(subset=["date", "sku_id"])
    sku = sku.dropna(subset=["sku_id", "category"])
    cal = cal.dropna(subset=["date"])
    inv = inv.dropna(subset=["date", "sku_id"])

    # Remove duplicate export rows but keep separate order rows.
    sales = sales.drop_duplicates()
    sku = sku.drop_duplicates(subset=["sku_id"], keep="last")
    cal = cal.drop_duplicates(subset=["date"], keep="last")
    inv = inv.drop_duplicates(subset=["date", "sku_id"], keep="last")

    numeric_sales = ["units_sold", "revenue", "unit_price", "discount_pct", "ad_spend", "page_views", "return_units"]
    for col in numeric_sales:
        if col in sales.columns:
            sales[col] = pd.to_numeric(sales[col], errors="coerce").fillna(0)
    sales["units_sold"] = sales["units_sold"].clip(lower=0)
    sales["revenue"] = sales["revenue"].clip(lower=0)
    sales["unit_price"] = sales["unit_price"].replace(0, np.nan)

    for col in ["unit_cost", "list_price", "target_margin"]:
        if col in sku.columns:
            sku[col] = pd.to_numeric(sku[col], errors="coerce")
    sku["unit_cost"] = sku["unit_cost"].fillna(sku["unit_cost"].median())
    sku["list_price"] = sku["list_price"].fillna(sku["list_price"].median())

    for col in ["on_hand_units", "on_order_units", "lead_time_days", "reorder_point", "damaged_units", "reserved_units"]:
        if col in inv.columns:
            inv[col] = pd.to_numeric(inv[col], errors="coerce").fillna(0)
            if col != "lead_time_days":
                inv[col] = inv[col].clip(lower=0)
    inv["lead_time_days"] = inv["lead_time_days"].clip(lower=1)

    # Fill missing enhanced columns so official minimal extracts still work.
    defaults = {
        "customer_id": "UNKNOWN_CUSTOMER",
        "sales_channel": "Unknown",
        "region": "Unknown",
        "discount_pct": 0.0,
        "ad_spend": 0.0,
        "page_views": 0,
        "return_units": 0,
        "stockout_flag": False,
    }
    for col, value in defaults.items():
        if col not in sales.columns:
            sales[col] = value
    for col, value in {"warehouse_zone": "Unknown", "damaged_units": 0, "reserved_units": 0}.items():
        if col not in inv.columns:
            inv[col] = value
    if "campaign_intensity" not in cal.columns:
        cal["campaign_intensity"] = np.where(cal["promo_event"].fillna("None") != "None", 2, 0)
    if "is_weekend" not in cal.columns:
        cal["is_weekend"] = cal["date"].dt.dayofweek >= 5

    return {"sales_daily": sales, "sku_master": sku, "calendar": cal, "inventory_snapshots": inv}


def build_weekly_features(cleaned: dict[str, pd.DataFrame]) -> pd.DataFrame:
    sales = cleaned["sales_daily"].copy()
    sku = cleaned["sku_master"].copy()
    cal = cleaned["calendar"].copy()
    inv = cleaned["inventory_snapshots"].copy()

    sales["week_start"] = sales["date"] - pd.to_timedelta(sales["date"].dt.dayofweek, unit="D")
    cal["week_start"] = cal["date"] - pd.to_timedelta(cal["date"].dt.dayofweek, unit="D")
    inv["week_start"] = inv["date"] - pd.to_timedelta(inv["date"].dt.dayofweek, unit="D")

    weekly_sales = sales.groupby(["sku_id", "week_start"], as_index=False).agg(
        units_sold=("units_sold", "sum"),
        revenue=("revenue", "sum"),
        avg_unit_price=("unit_price", "mean"),
        promo_days=("promo_flag", "sum"),
        avg_discount=("discount_pct", "mean"),
        ad_spend=("ad_spend", "sum"),
        page_views=("page_views", "sum"),
        return_units=("return_units", "sum"),
        stockout_days=("stockout_flag", "sum"),
        unique_customers=("customer_id", "nunique"),
    )
    weekly_cal = cal.groupby("week_start", as_index=False).agg(
        month=("month", "max"),
        week=("week", "max"),
        campaign_intensity=("campaign_intensity", "mean"),
        holiday_days=("is_holiday", "sum"),
        weekend_days=("is_weekend", "sum"),
    )
    latest_inv = inv.sort_values("date").groupby(["sku_id", "week_start"], as_index=False).tail(1)
    weekly_inv = latest_inv[[
        "sku_id", "week_start", "on_hand_units", "on_order_units", "lead_time_days", "reorder_point", "damaged_units", "reserved_units", "warehouse_zone"
    ]]

    all_weeks = pd.date_range(weekly_sales["week_start"].min(), weekly_sales["week_start"].max(), freq="W-MON")
    index = pd.MultiIndex.from_product([sku["sku_id"].unique(), all_weeks], names=["sku_id", "week_start"])
    weekly = weekly_sales.set_index(["sku_id", "week_start"]).reindex(index).reset_index()
    for col in ["units_sold", "revenue", "promo_days", "avg_discount", "ad_spend", "page_views", "return_units", "stockout_days", "unique_customers"]:
        weekly[col] = weekly[col].fillna(0)
    weekly = weekly.merge(sku, on="sku_id", how="left")
    weekly = weekly.merge(weekly_cal, on="week_start", how="left")
    weekly = weekly.merge(weekly_inv, on=["sku_id", "week_start"], how="left")
    weekly = weekly.sort_values(["sku_id", "week_start"]).reset_index(drop=True)

    fill_cols = ["on_hand_units", "on_order_units", "lead_time_days", "reorder_point", "damaged_units", "reserved_units"]
    weekly[fill_cols] = weekly.groupby("sku_id")[fill_cols].ffill().bfill()
    weekly["warehouse_zone"] = weekly.groupby("sku_id")["warehouse_zone"].ffill().bfill().fillna("Unknown")
    weekly["avg_unit_price"] = weekly["avg_unit_price"].fillna(weekly["list_price"])
    weekly["gross_margin"] = (weekly["avg_unit_price"] - weekly["unit_cost"]) / weekly["avg_unit_price"].replace(0, np.nan)
    weekly["gross_margin"] = weekly["gross_margin"].fillna(0).clip(-1, 1)

    # Time-series features by SKU; all features use only current/past values.
    for lag in [1, 2, 4, 8, 13, 26, 52]:
        weekly[f"lag_{lag}"] = weekly.groupby("sku_id")["units_sold"].shift(lag)
    weekly["rolling_4_mean"] = weekly.groupby("sku_id")["units_sold"].shift(1).rolling(4).mean().reset_index(level=0, drop=True)
    weekly["rolling_8_mean"] = weekly.groupby("sku_id")["units_sold"].shift(1).rolling(8).mean().reset_index(level=0, drop=True)
    weekly["rolling_13_std"] = weekly.groupby("sku_id")["units_sold"].shift(1).rolling(13).std().reset_index(level=0, drop=True)
    weekly["sell_through_proxy"] = weekly["units_sold"] / (weekly["units_sold"] + weekly["on_hand_units"].fillna(0) + 1)
    weekly["inventory_cover_weeks"] = weekly["on_hand_units"] / (weekly["rolling_4_mean"].fillna(weekly["units_sold"].mean()) + 1)

    # Fill early lag values with sensible SKU/category-level references.
    for col in [c for c in weekly.columns if c.startswith("lag_") or c.startswith("rolling_")]:
        weekly[col] = weekly.groupby("sku_id")[col].transform(lambda s: s.fillna(s.median()))
        weekly[col] = weekly[col].fillna(weekly["units_sold"].median())

    weekly["month"] = weekly["month"].fillna(weekly["week_start"].dt.month).astype(int)
    weekly["week"] = weekly["week"].fillna(weekly["week_start"].dt.isocalendar().week.astype(int)).astype(int)
    weekly["campaign_intensity"] = weekly["campaign_intensity"].fillna(0)
    weekly["holiday_days"] = weekly["holiday_days"].fillna(0)
    weekly["weekend_days"] = weekly["weekend_days"].fillna(2)
    return weekly


def build_customer_segments(cleaned: dict[str, pd.DataFrame]) -> pd.DataFrame:
    sales = cleaned["sales_daily"].copy()
    if "customer_id" not in sales.columns or sales["customer_id"].nunique() <= 1:
        return pd.DataFrame(columns=["customer_id", "recency_days", "frequency", "monetary", "rfm_score", "segment", "churn_risk"])

    snapshot_date = sales["date"].max() + pd.Timedelta(days=1)
    rfm = sales.groupby("customer_id", as_index=False).agg(
        last_purchase=("date", "max"),
        frequency=("order_id", "nunique"),
        monetary=("revenue", "sum"),
        units=("units_sold", "sum"),
        avg_discount=("discount_pct", "mean"),
        return_units=("return_units", "sum"),
    )
    rfm["recency_days"] = (snapshot_date - rfm["last_purchase"]).dt.days
    # Quantile scoring with duplicate-safe fallbacks.
    rfm["r_score"] = pd.qcut(rfm["recency_days"].rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["f_score"] = pd.qcut(rfm["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["m_score"] = pd.qcut(rfm["monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["rfm_score"] = rfm["r_score"] * 100 + rfm["f_score"] * 10 + rfm["m_score"]

    def segment(row):
        if row.r_score >= 4 and row.f_score >= 4 and row.m_score >= 4:
            return "Champions"
        if row.r_score >= 3 and row.f_score >= 4:
            return "Loyal Customers"
        if row.r_score >= 4 and row.f_score <= 3:
            return "Potential Loyalists"
        if row.r_score <= 2 and row.f_score >= 3:
            return "At Risk"
        if row.r_score <= 2 and row.f_score <= 2:
            return "Hibernating"
        return "Need Attention"

    rfm["segment"] = rfm.apply(segment, axis=1)
    rfm["return_rate"] = rfm["return_units"] / (rfm["units"] + rfm["return_units"] + 1)
    rfm["churn_risk"] = (
        0.58 * (rfm["recency_days"] / rfm["recency_days"].max()).fillna(0)
        + 0.22 * (1 - rfm["frequency"] / rfm["frequency"].max()).fillna(0)
        + 0.12 * rfm["avg_discount"].fillna(0)
        + 0.08 * rfm["return_rate"].fillna(0)
    ).clip(0, 1)
    return rfm[["customer_id", "recency_days", "frequency", "monetary", "units", "rfm_score", "segment", "churn_risk", "avg_discount", "return_rate"]]


def run_pipeline(raw_dir: Path = RAW_DIR, processed_dir: Path = PROCESSED_DIR) -> dict[str, Path]:
    ensure_directories()
    raw = load_raw_data(raw_dir)
    cleaned = clean_data(raw)
    weekly = build_weekly_features(cleaned)
    customers = build_customer_segments(cleaned)

    paths = {
        "weekly_features": processed_dir / "weekly_demand_features.csv",
        "customer_segments": processed_dir / "customer_segments.csv",
    }
    weekly.to_csv(paths["weekly_features"], index=False)
    customers.to_csv(paths["customer_segments"], index=False)
    return paths


if __name__ == "__main__":
    for name, path in run_pipeline().items():
        print(f"created {name}: {path}")
