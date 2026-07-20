from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import yaml

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = ROOT_DIR / "reports"
CONFIG_PATH = ROOT_DIR / "configs" / "project_config.yaml"


@dataclass(frozen=True)
class ProjectConfig:
    project_name: str
    client: str
    forecast_horizon_weeks: int
    seasonal_lag_weeks: int
    random_seed: int
    n_skus: int
    n_customers: int
    start_date: str
    end_date: str
    snapshot_frequency_days: int
    stockout_threshold: float
    overstock_threshold: float
    safety_stock_multiplier: float


def load_config(path: Path = CONFIG_PATH) -> ProjectConfig:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return ProjectConfig(
        project_name=cfg["project"]["name"],
        client=cfg["project"]["client"],
        forecast_horizon_weeks=int(cfg["project"]["forecast_horizon_weeks"]),
        seasonal_lag_weeks=int(cfg["project"]["baseline_seasonal_lag_weeks"]),
        random_seed=int(cfg["project"]["random_seed"]),
        n_skus=int(cfg["data_generation"]["n_skus"]),
        n_customers=int(cfg["data_generation"]["n_customers"]),
        start_date=str(cfg["data_generation"]["start_date"]),
        end_date=str(cfg["data_generation"]["end_date"]),
        snapshot_frequency_days=int(cfg["data_generation"]["snapshot_frequency_days"]),
        stockout_threshold=float(cfg["risk"]["stockout_threshold"]),
        overstock_threshold=float(cfg["risk"]["overstock_threshold"]),
        safety_stock_multiplier=float(cfg["risk"]["safety_stock_multiplier"]),
    )


def ensure_directories() -> None:
    for directory in [RAW_DIR, PROCESSED_DIR, REPORTS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
