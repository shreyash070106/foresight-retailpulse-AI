# Advanced Dashboard Upgrade

The Streamlit dashboard has been upgraded from a basic view into an interactive planning command center.

## New dashboard sections

1. **Executive Cockpit**
   - Styled hero section and KPI cards
   - Inventory decision matrix
   - Action pressure sunburst
   - Rupee impact by category
   - Historical revenue trend
   - Board-ready top recommendations

2. **Forecast Lab**
   - SKU-level actual vs forecast chart
   - 80% forecast confidence interval
   - Baseline vs model comparison
   - Multi-SKU forecast comparison
   - Backtest error trend

3. **Risk Command Center**
   - Top priority SKU ranking
   - Category/action heatmap
   - Risk tree map
   - Smart action table
   - Downloadable filtered priority list

4. **What-if Simulator**
   - Discount change simulator
   - Ad-spend change simulator
   - Lead-time change simulator
   - Target service-level safety stock calculator
   - Suggested order quantity recommendation

5. **RetailPulse 360**
   - RFM customer segmentation
   - Customer value map
   - Segment deep dive
   - Churn-risk distribution
   - Retention action queue

6. **Data Explorer**
   - Dataset selector
   - Row/column/missing/duplicate profile
   - Column picker
   - Missing value profile
   - Numeric distribution charts

7. **Reports**
   - Embedded project reports
   - Auto-generated executive meeting summary
   - Downloadable meeting summary

## Run command

```powershell
python run_all.py
python -m streamlit run app\dashboard.py
```

The previous simple dashboard has been kept as:

```text
app/dashboard_basic.py
```
