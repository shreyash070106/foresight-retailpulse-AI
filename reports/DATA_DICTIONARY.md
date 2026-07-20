# Data Dictionary — Enhanced FORESIGHT + RetailPulse Dataset

## sales_daily.csv

Core columns: `date`, `sku_id`, `units_sold`, `revenue`, `unit_price`, `promo_flag`  
Enhanced columns: `customer_id`, `order_id`, `sales_channel`, `region`, `discount_pct`, `ad_spend`, `page_views`, `return_units`, `stockout_flag`

## sku_master.csv

Core columns: `sku_id`, `category`, `subcategory`, `launch_date`, `unit_cost`, `list_price`  
Enhanced columns: `sku_name`, `brand`, `supplier`, `size`, `color`, `lifecycle_stage`, `target_margin`

## calendar.csv

Core columns: `date`, `week`, `month`, `season`, `is_holiday`, `promo_event`  
Enhanced columns: `quarter`, `holiday_name`, `day_of_week`, `is_weekend`, `campaign_intensity`, `weather_index`

## inventory_snapshots.csv

Core columns: `date`, `sku_id`, `on_hand_units`, `on_order_units`, `lead_time_days`, `reorder_point`  
Enhanced columns: `warehouse_zone`, `damaged_units`, `reserved_units`, `inventory_snapshot_quality`
