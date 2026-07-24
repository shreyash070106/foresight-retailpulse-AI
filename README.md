# FORESIGHT + RetailPulse — AI Retail Intelligence Platform

A complete Zidio-style Data Science & Analytics internship project combining **Project FORESIGHT** demand and inventory intelligence with **RetailPulse** customer analytics.

The project converts retail sales, SKU, calendar, and inventory extracts into:

- weekly SKU-level demand forecasts for the next 8 weeks
- seasonal-naive baseline comparison with WAPE and forecast bias
- stockout and overstock risk scoring
- reorder / markdown / watch / healthy action recommendations
- rupee business impact estimates
- customer RFM segmentation and churn-risk indicators
- a Streamlit planning dashboard
- a FastAPI scoring service
- EDA, model, risk, and executive reports

> This version is built as a complete reproducible project. It includes a seeded enhanced dataset generator because the actual raw CSV extracts were not available in this workspace. When you receive official Zidio CSVs, replace the files in `data/raw/` and run the same pipeline again.
This project is based on the provided RetailPulse dataset. The raw dataset files are stored in data/raw and include sales, inventory, SKU master, and calendar data. These files were cleaned, merged, and transformed into processed files stored in data/processed, which are used for forecasting, inventory risk scoring, customer analytics, and dashboard visualization.
---

## Project positioning

**Client:** NorthBay Living, a D2C home and lifestyle brand  
**Role:** Data Scientist & Analytics Intern  
**Business problem:** best-selling SKUs stock out while slow-moving SKUs lock capital in inventory.  
**Solution:** forecast demand, score risk, and give the operations team a dashboard/API to decide what to reorder or clear.

---

## Final deliverables included

| ID | Deliverable | Included file/folder |
|---|---|---|
| D1 | Reproducible data pipeline | `src/pipeline.py`, `run_all.py` |
| D2 | Data-quality + EDA memo | `reports/EDA_Memo.md` |
| D3 | Demand forecast model | `src/forecast.py`, `data/processed/sku_forecasts.csv` |
| D4 | Risk scoring and recommended actions | `src/risk.py`, `data/processed/risk_scores.csv` |
| D5 | Planning dashboard | `app/dashboard.py` |
| D6 | Scoring API service | `service/api.py` |
| D7 | Executive readout | `reports/Executive_Readout.md` |
| Extra | RetailPulse customer analytics | `data/processed/customer_segments.csv`, dashboard page |

---

## Repository structure

```text
FORESIGHT_RetailPulse_Complete/
├── app/
│   ├── dashboard.py
│   └── pages/
├── assets/
├── configs/
│   └── project_config.yaml
├── data/
│   ├── raw/
│   │   ├── sales_daily.csv
│   │   ├── sku_master.csv
│   │   ├── calendar.csv
│   │   └── inventory_snapshots.csv
│   ├── processed/
│   │   ├── weekly_demand_features.csv
│   │   ├── model_metrics.csv
│   │   ├── sku_forecasts.csv
│   │   ├── risk_scores.csv
│   │   ├── customer_segments.csv
│   │   └── executive_summary.json
│   └── sample/
├── reports/
│   ├── DATA_DICTIONARY.md
│   ├── EDA_Memo.md
│   ├── Model_Card.md
│   ├── Risk_Decisioning.md
│   └── Executive_Readout.md
├── service/
│   └── api.py
├── src/
│   ├── config.py
│   ├── generate_data.py
│   ├── pipeline.py
│   ├── forecast.py
│   ├── risk.py
│   └── reporting.py
├── tests/
├── Dockerfile
├── Procfile
├── render.yaml
├── requirements.txt
└── run_all.py
```

---

## Quick start — Windows

Open the project folder in VS Code or Command Prompt, then run:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python run_all.py
```

Run the dashboard:

```bash
streamlit run app/dashboard.py
```

Run the API:

```bash
uvicorn service.api:app --reload
```

Open API docs:

```text
http://127.0.0.1:8000/docs
```

---

## Quick start — macOS/Linux/Kali

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run_all.py
streamlit run app/dashboard.py
```

For API:

```bash
uvicorn service.api:app --reload
```

---

## API examples

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/sku/SKU0001
curl http://127.0.0.1:8000/score/SKU0001
curl -X POST http://127.0.0.1:8000/batch-score \
  -H "Content-Type: application/json" \
  -d '{"sku_ids":["SKU0001","SKU0002","SKU0003"]}'
```

---

## Methodology

1. Generate or load raw extracts.
2. Validate schema and clean data.
3. Aggregate daily sales into weekly SKU-level demand.
4. Engineer lag, rolling, calendar, promo, price, inventory, and category features.
5. Build a seasonal-naive baseline.
6. Train a Ridge regression forecasting model.
7. Backtest using holdout periods that respect time order.
8. Compare model WAPE against baseline WAPE.
9. Forecast the next 8 weeks.
10. Score stockout and overstock risk using forecast demand and inventory position.
11. Quantify sales-at-risk and locked capital in rupees.
12. Serve outputs through Streamlit and FastAPI.

---

## Main metrics explained

**WAPE** = total absolute forecast error / total actual demand. Lower is better.  
**Bias** = total forecast error / total actual demand. Close to zero is better.  
**Sales at risk** = units likely missed due to stockout × list price.  
**Locked capital** = estimated excess units × unit cost.

---

## Deployment notes

### Streamlit Cloud

1. Push this folder to GitHub.
2. Create a new Streamlit app.
3. Main file path: `app/dashboard.py`.
4. Add `requirements.txt`.
5. Deploy.

### Render API

Build command:

```bash
pip install -r requirements.txt && python run_all.py
```

Start command:

```bash
uvicorn service.api:app --host 0.0.0.0 --port $PORT
```

---

## Important assumption

The official engagement brief says the project should use provided extracts. Since actual CSV extracts were not available inside this workspace, this package includes a deterministic enhanced dataset generator. It keeps the required FORESIGHT tables and adds RetailPulse-style columns such as customer ID, region, channel, discount, ad spend, return units, warehouse zone, and campaign intensity.

When official data is available, replace the four CSVs in `data/raw/` and rerun:

```bash
python run_all.py --skip-generate
```
