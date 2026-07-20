# Data Quality & EDA Memo — FORESIGHT + RetailPulse

## Dataset overview

- Weekly SKU records prepared: **3,360**
- SKUs: **40**
- Categories: **5**
- Forecast horizon: **8 weeks**
- Customer records used for RFM: **2,399**

## Revenue and demand patterns

The highest revenue categories are:

| category   |     revenue |   units_sold |   sku_count |   avg_inventory_cover |
|:-----------|------------:|-------------:|------------:|----------------------:|
| Furniture  | 7.81017e+07 |        28917 |          11 |               65.5143 |
| Kitchen    | 4.54636e+07 |        25091 |           8 |               79.1895 |
| Home Decor | 3.89794e+07 |        17348 |           7 |               57.005  |
| Lighting   | 3.34146e+07 |        20063 |           6 |              150.624  |
| Bedding    | 2.78775e+07 |        10443 |           8 |               15.2521 |

## Data quality checks performed

- Required schema validation for `sales_daily`, `sku_master`, `calendar`, and `inventory_snapshots`.
- Duplicate raw export rows removed.
- Missing prices filled using SKU list price.
- Negative unit, inventory, and revenue values clipped to valid ranges.
- Inventory snapshots forward-filled/back-filled per SKU to support weekly modelling.
- Lag and rolling features created without using future demand.

## Business observations

1. Promotion and campaign intensity produce visible lifts in weekly demand.
2. Slow-moving SKUs are the main source of locked working capital.
3. High-demand SKUs with long lead times create the strongest stockout exposure.
4. RetailPulse customer segmentation adds retention context, while FORESIGHT remains focused on stock planning.
