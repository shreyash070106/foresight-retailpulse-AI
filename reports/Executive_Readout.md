# Executive Readout — FORESIGHT + RetailPulse

## Recommendation summary

NorthBay Living should act first on high-priority **Reorder now** SKUs to protect revenue, then clear excess inventory for **Markdown / clear** SKUs to release working capital.

## Project result

| Result | Value |
|---|---:|
| Selected model | Ridge Regression |
| Model WAPE | 10.5% |
| Seasonal-naive baseline WAPE | 50.5% |
| WAPE improvement | 79.3% |
| Sales at risk | ₹10,349,480 |
| Locked capital | ₹146,543 |
| Reorder-now SKUs | 17 |
| Markdown / clear SKUs | 1 |

## What the operations team can do now

1. Open the Streamlit dashboard and filter by category or SKU.
2. Review the priority score and action recommendation.
3. Reorder SKUs where lead-time demand can exceed available inventory.
4. Apply markdown or promotional clearance to slow-moving overstock.
5. Use the FastAPI endpoint for SKU-level forecast and risk lookup.

## RetailPulse customer insight

Customer analytics was added as an enhanced layer using RFM segmentation and churn-risk scoring. It supports retention and campaign planning, while the main FORESIGHT deliverable remains demand and inventory decisioning.

| segment             |   customers |     revenue |   avg_churn_risk |
|:--------------------|------------:|------------:|-----------------:|
| Champions           |         342 | 5.11233e+07 |         0.122195 |
| At Risk             |         433 | 4.55734e+07 |         0.243199 |
| Loyal Customers     |         363 | 3.927e+07   |         0.150335 |
| Potential Loyalists |         472 | 3.54073e+07 |         0.174801 |
| Hibernating         |         527 | 3.12317e+07 |         0.330818 |
| Need Attention      |         262 | 2.12312e+07 |         0.210622 |

## Final conclusion

The project is reproducible, stakeholder-facing, and aligned with the internship brief: it forecasts demand, flags stockout and overstock risk, quantifies rupee impact, and provides both dashboard and API consumption layers.
