from __future__ import annotations

import argparse
from pathlib import Path

from src.generate_data import generate_raw_data
from src.pipeline import run_pipeline
from src.forecast import run_forecasting
from src.risk import run_risk_scoring
from src.reporting import build_reports
from src.config import ensure_directories


def main() -> None:
    parser = argparse.ArgumentParser(description="Run FORESIGHT + RetailPulse end-to-end pipeline")
    parser.add_argument("--skip-generate", action="store_true", help="Use existing CSVs in data/raw instead of generating seeded enhanced data")
    args = parser.parse_args()

    ensure_directories()
    print("\n=== FORESIGHT + RetailPulse pipeline started ===")
    if not args.skip_generate:
        print("1/5 Generating enhanced raw extracts...")
        generate_raw_data()
    else:
        print("1/5 Skipping generation; using data/raw CSVs...")

    print("2/5 Building cleaned weekly features and customer segments...")
    run_pipeline()

    print("3/5 Training, backtesting, and forecasting...")
    run_forecasting()

    print("4/5 Scoring stockout/overstock risk...")
    run_risk_scoring()

    print("5/5 Writing reports...")
    build_reports()

    print("\nDone. Outputs are in data/processed and reports.")
    print("Run dashboard: streamlit run app/dashboard.py")
    print("Run API: uvicorn service.api:app --reload")


if __name__ == "__main__":
    main()
