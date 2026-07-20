from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from src.generate_data import generate_raw_data
from src.pipeline import run_pipeline
from src.forecast import run_forecasting
from src.risk import run_risk_scoring


def test_end_to_end_outputs_exist():
    generate_raw_data()
    run_pipeline()
    run_forecasting()
    run_risk_scoring()
    processed = Path("data/processed")
    assert (processed / "weekly_demand_features.csv").exists()
    assert (processed / "sku_forecasts.csv").exists()
    assert (processed / "risk_scores.csv").exists()
    risk = pd.read_csv(processed / "risk_scores.csv")
    assert {"sku_id", "stockout_risk", "overstock_risk", "recommended_action"}.issubset(risk.columns)