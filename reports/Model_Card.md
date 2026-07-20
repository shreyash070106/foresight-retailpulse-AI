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
| Model WAPE | 10.5% |
| Seasonal-naive WAPE | 50.5% |
| WAPE improvement | 79.3% |
| Model bias | 4.9% |
| Test rows | 320 |

## Why this model is used

Ridge regression is transparent, fast, stable on moderate-size retail datasets, and easier to defend to a non-technical stakeholder than an unnecessarily complex model. The baseline remains visible so the forecast is judged honestly.

## Limitations

- Forecast quality depends on the quality of the raw extracts.
- Future promotion plans are approximated if no official promotion calendar is supplied.
- The model should be retrained after each monthly data refresh.
