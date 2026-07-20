# Risk Decisioning Memo

## Decision logic

Each SKU receives three risk signals:

1. **Stockout risk** — lead-time forecast demand plus safety stock compared with available inventory.
2. **Overstock risk** — on-hand inventory compared with expected 8-week demand.
3. **Volatility risk** — forecast variability over the horizon.

## Recommended actions

| Action | Count |
|---|---:|
| Reorder now | 17 |
| Markdown / clear | 1 |
| Watch / volatile | 0 |
| Healthy | 22 |

## Business impact

- Sales at risk: **₹10,349,480**
- Locked capital: **₹146,543**

## Top priority SKUs

| sku_id   | category   | recommended_action   |   priority_score |   sales_at_risk_rupees |   locked_capital_rupees |
|:---------|:-----------|:---------------------|-----------------:|-----------------------:|------------------------:|
| SKU0025  | Kitchen    | Reorder now          |            63.23 |       119595           |                       0 |
| SKU0011  | Furniture  | Reorder now          |            58.4  |       140699           |                       0 |
| SKU0001  | Furniture  | Reorder now          |            58.21 |       335210           |                       0 |
| SKU0003  | Kitchen    | Reorder now          |            57.68 |       902408           |                       0 |
| SKU0008  | Bedding    | Reorder now          |            57.59 |       157672           |                       0 |
| SKU0018  | Furniture  | Reorder now          |            57.49 |            1.25116e+06 |                       0 |
| SKU0028  | Kitchen    | Reorder now          |            57.33 |       943637           |                       0 |
| SKU0009  | Bedding    | Reorder now          |            56.23 |            1.17628e+06 |                       0 |
| SKU0012  | Lighting   | Reorder now          |            55.41 |       365486           |                       0 |
| SKU0037  | Bedding    | Reorder now          |            55.04 |       532725           |                       0 |
