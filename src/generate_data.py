from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

from src.config import RAW_DIR, load_config, ensure_directories

CATEGORIES = {
    "Home Decor": ["Wall Art", "Candles", "Vases", "Mirrors"],
    "Furniture": ["Tables", "Chairs", "Storage", "Shelves"],
    "Kitchen": ["Cookware", "Storage Jars", "Serveware", "Appliances"],
    "Bedding": ["Bedsheets", "Pillows", "Blankets", "Comforters"],
    "Lighting": ["Table Lamps", "Ceiling Lights", "Floor Lamps", "Decor Lights"],
}
REGIONS = ["West", "North", "South", "East", "Central"]
CHANNELS = ["Website", "Marketplace", "Mobile App", "Social Commerce"]
SEASONS = {
    12: "Winter", 1: "Winter", 2: "Winter",
    3: "Spring", 4: "Summer", 5: "Summer",
    6: "Monsoon", 7: "Monsoon", 8: "Monsoon",
    9: "Festive", 10: "Festive", 11: "Winter",
}


def _make_calendar(dates: pd.DatetimeIndex, rng: np.random.Generator) -> pd.DataFrame:
    holidays = {
        "2024-01-26": "Republic Day",
        "2024-08-15": "Independence Day",
        "2024-10-31": "Diwali",
        "2024-12-25": "Christmas",
        "2025-01-26": "Republic Day",
        "2025-08-15": "Independence Day",
        "2025-10-20": "Diwali",
        "2025-12-25": "Christmas",
    }
    rows = []
    for d in dates:
        is_holiday = d.strftime("%Y-%m-%d") in holidays
        promo_event = "None"
        if d.month in [10, 11]:
            promo_event = "Festive Sale"
        elif d.month in [6, 7]:
            promo_event = "Monsoon Offer"
        elif d.day <= 7 and d.month in [1, 4, 8, 12]:
            promo_event = "Monthly Mega Sale"
        campaign_intensity = 0
        if promo_event != "None":
            campaign_intensity = int(rng.integers(2, 5))
        rows.append({
            "date": d.date().isoformat(),
            "week": int(d.isocalendar().week),
            "month": int(d.month),
            "quarter": int(d.quarter),
            "season": SEASONS[d.month],
            "is_holiday": bool(is_holiday),
            "holiday_name": holidays.get(d.strftime("%Y-%m-%d"), "None"),
            "promo_event": promo_event,
            "day_of_week": d.day_name(),
            "is_weekend": d.dayofweek >= 5,
            "campaign_intensity": campaign_intensity,
            "weather_index": round(float(np.clip(rng.normal(0.65, 0.18), 0.1, 1.0)), 3),
        })
    return pd.DataFrame(rows)


def _make_sku_master(n_skus: int, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    cat_names = list(CATEGORIES.keys())
    for i in range(1, n_skus + 1):
        category = rng.choice(cat_names)
        subcategory = rng.choice(CATEGORIES[category])
        cost = float(rng.uniform(120, 2400))
        margin = float(rng.uniform(0.32, 0.68))
        list_price = cost / (1 - margin)
        launch = pd.Timestamp("2023-01-01") + pd.Timedelta(days=int(rng.integers(0, 820)))
        rows.append({
            "sku_id": f"SKU{i:04d}",
            "sku_name": f"{subcategory} {i:04d}",
            "category": category,
            "subcategory": subcategory,
            "brand": rng.choice(["NorthBay", "CasaNova", "UrbanNest", "BrightHome", "EcoLiving"]),
            "launch_date": launch.date().isoformat(),
            "unit_cost": round(cost, 2),
            "list_price": round(list_price, 2),
            "supplier": rng.choice(["S1-Mumbai", "S2-Pune", "S3-Delhi", "S4-Bengaluru"]),
            "size": rng.choice(["XS", "S", "M", "L", "XL", "Standard"]),
            "color": rng.choice(["White", "Black", "Brown", "Blue", "Beige", "Green", "Multi"]),
            "lifecycle_stage": rng.choice(["New", "Growth", "Mature", "Slow Moving"], p=[0.17, 0.29, 0.41, 0.13]),
            "target_margin": round(margin, 3),
        })
    return pd.DataFrame(rows)


def _demand_multiplier(row: pd.Series, sku_row: pd.Series, day_index: int) -> float:
    base = 1.0
    if row["is_weekend"]:
        base += 0.16
    if row["is_holiday"]:
        base += 0.25
    if row["promo_event"] != "None":
        base += 0.18 + 0.06 * row["campaign_intensity"]
    if row["season"] == "Festive":
        base += 0.22
    if sku_row["category"] == "Lighting" and row["season"] in ["Festive", "Winter"]:
        base += 0.19
    if sku_row["category"] == "Bedding" and row["season"] == "Winter":
        base += 0.20
    if sku_row["lifecycle_stage"] == "New":
        # New SKUs ramp after launch then stabilize.
        base *= 0.75 + min(day_index / 180, 0.45)
    if sku_row["lifecycle_stage"] == "Slow Moving":
        base *= 0.68
    return max(base, 0.05)


def _make_sales(dates: pd.DatetimeIndex, sku_master: pd.DataFrame, calendar: pd.DataFrame, n_customers: int, rng: np.random.Generator) -> pd.DataFrame:
    cal = calendar.copy()
    cal["date"] = pd.to_datetime(cal["date"])
    calendar_map = cal.set_index("date")
    customers = [f"CUST{i:05d}" for i in range(1, n_customers + 1)]
    sku_popularity = rng.gamma(shape=2.0, scale=1.5, size=len(sku_master))
    rows = []
    order_counter = 100000
    for sku_idx, sku in sku_master.reset_index(drop=True).iterrows():
        launch_date = pd.to_datetime(sku["launch_date"])
        daily_base = sku_popularity[sku_idx] * rng.uniform(0.6, 2.2)
        trend = rng.uniform(-0.0004, 0.0008)
        for day_index, d in enumerate(dates):
            if d < launch_date:
                continue
            cal_row = calendar_map.loc[d]
            multiplier = _demand_multiplier(cal_row, sku, day_index)
            promo_flag = bool(cal_row["promo_event"] != "None" or rng.random() < 0.08)
            discount_pct = 0.0
            if promo_flag:
                discount_pct = round(float(rng.uniform(0.05, 0.28)), 3)
            seasonality = 1 + 0.12 * np.sin(2 * np.pi * day_index / 365.25) + 0.08 * np.sin(2 * np.pi * day_index / 30.5)
            expected = max(daily_base * multiplier * seasonality * (1 + trend * day_index), 0.02)
            units = int(rng.poisson(expected))
            if rng.random() < 0.12:
                units = 0
            if promo_flag and units > 0:
                units += int(rng.poisson(1.4))
            return_units = int(rng.binomial(max(units, 0), 0.025)) if units > 0 else 0
            net_units = max(units - return_units, 0)
            unit_price = float(sku["list_price"] * (1 - discount_pct))
            revenue = round(net_units * unit_price, 2)
            page_views = int(rng.poisson(45 + 11 * units + 18 * promo_flag + 8 * cal_row["campaign_intensity"]))
            ad_spend = round(float((12 + 3.5 * page_views) * (1 if promo_flag else rng.uniform(0.15, 0.45))), 2)
            stockout_flag = bool(units > 0 and rng.random() < max(0.01, 0.05 - min(expected / 300, 0.03)))
            if net_units == 0 and rng.random() < 0.65:
                # keep sparse zero rows but not every zero row; raw POS exports are usually compact.
                continue
            order_counter += 1
            rows.append({
                "date": d.date().isoformat(),
                "sku_id": sku["sku_id"],
                "units_sold": int(net_units),
                "revenue": revenue,
                "unit_price": round(unit_price, 2),
                "promo_flag": promo_flag,
                "customer_id": rng.choice(customers),
                "order_id": f"ORD{order_counter}",
                "sales_channel": rng.choice(CHANNELS, p=[0.42, 0.30, 0.22, 0.06]),
                "region": rng.choice(REGIONS, p=[0.34, 0.19, 0.20, 0.14, 0.13]),
                "discount_pct": discount_pct,
                "ad_spend": ad_spend,
                "page_views": page_views,
                "return_units": return_units,
                "stockout_flag": stockout_flag,
            })
    return pd.DataFrame(rows)


def _make_inventory(dates: pd.DatetimeIndex, sku_master: pd.DataFrame, sales: pd.DataFrame, rng: np.random.Generator, freq_days: int) -> pd.DataFrame:
    """Create inventory snapshots efficiently from daily sales.

    The earlier version filtered the sales table inside a nested loop. This version
    precomputes cumulative daily demand per SKU so the generator remains fast even
    when the number of SKUs is increased.
    """
    snapshot_dates = dates[::freq_days]
    sales_copy = sales.copy()
    sales_copy["date"] = pd.to_datetime(sales_copy["date"])
    daily = sales_copy.groupby(["sku_id", "date"], as_index=False)["units_sold"].sum()
    avg_daily = daily.groupby("sku_id")["units_sold"].mean().to_dict()

    # Build per-SKU cumulative demand arrays aligned to the full date range.
    full_dates = pd.DataFrame({"date": dates})
    cum_lookup = {}
    for sku_id, g in daily.groupby("sku_id"):
        merged = full_dates.merge(g, on="date", how="left").fillna({"units_sold": 0})
        cum_lookup[sku_id] = merged["units_sold"].to_numpy().cumsum()
    date_pos = {d: i for i, d in enumerate(dates)}

    rows = []
    for _, sku in sku_master.iterrows():
        sku_id = sku["sku_id"]
        avg_weekly = max(float(avg_daily.get(sku_id, rng.uniform(1.0, 5.0))) * 7, 1.0)
        on_hand = int(rng.uniform(avg_weekly * 2, avg_weekly * 9))
        lead_time = int(rng.integers(7, 29))
        reorder = int(np.ceil(avg_weekly * (lead_time / 7) * rng.uniform(1.15, 1.75)))
        cum = cum_lookup.get(sku_id, np.zeros(len(dates)))
        for d in snapshot_dates:
            pos = date_pos[d]
            prev_pos = max(pos - freq_days, 0)
            recent = cum[pos] - (cum[prev_pos] if prev_pos > 0 else 0)
            on_hand = max(0, on_hand - int(recent) + int(rng.poisson(avg_weekly * 0.45)))
            if on_hand < reorder and rng.random() < 0.58:
                on_order = int(rng.uniform(avg_weekly * 2, avg_weekly * 6))
            else:
                on_order = int(rng.poisson(avg_weekly * 0.45))
            rows.append({
                "date": d.date().isoformat(),
                "sku_id": sku_id,
                "on_hand_units": int(on_hand),
                "on_order_units": int(on_order),
                "lead_time_days": lead_time,
                "reorder_point": reorder,
                "warehouse_zone": rng.choice(["A", "B", "C", "D"]),
                "damaged_units": int(rng.binomial(max(on_hand, 1), 0.008)),
                "reserved_units": int(rng.binomial(max(on_hand, 1), 0.045)),
                "inventory_snapshot_quality": rng.choice(["Good", "Manual Check", "Late Update"], p=[0.86, 0.09, 0.05]),
            })
    return pd.DataFrame(rows)

def generate_raw_data(output_dir: Path = RAW_DIR) -> dict[str, Path]:
    cfg = load_config()
    ensure_directories()
    rng = np.random.default_rng(cfg.random_seed)
    dates = pd.date_range(cfg.start_date, cfg.end_date, freq="D")

    calendar = _make_calendar(dates, rng)
    sku_master = _make_sku_master(cfg.n_skus, rng)
    sales = _make_sales(dates, sku_master, calendar, cfg.n_customers, rng)
    inventory = _make_inventory(dates, sku_master, sales, rng, cfg.snapshot_frequency_days)

    paths = {
        "sales_daily": output_dir / "sales_daily.csv",
        "sku_master": output_dir / "sku_master.csv",
        "calendar": output_dir / "calendar.csv",
        "inventory_snapshots": output_dir / "inventory_snapshots.csv",
    }
    sales.to_csv(paths["sales_daily"], index=False)
    sku_master.to_csv(paths["sku_master"], index=False)
    calendar.to_csv(paths["calendar"], index=False)
    inventory.to_csv(paths["inventory_snapshots"], index=False)
    return paths


if __name__ == "__main__":
    result = generate_raw_data()
    for name, path in result.items():
        print(f"created {name}: {path}")
