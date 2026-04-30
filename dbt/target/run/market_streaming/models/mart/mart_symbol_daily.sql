
  
    

  create  table "market_db"."public"."mart_symbol_daily__dbt_tmp"
  
  
    as
  
  (
    select
    symbol,
    date_trunc('day', event_time) as trade_date,
    round(avg(price)::numeric, 2)        as avg_price,
    round(max(price)::numeric, 2)        as high_price,
    round(min(price)::numeric, 2)        as low_price,
    round(avg(change_pct)::numeric, 4)   as avg_change_pct,
    sum(volume)                          as total_volume,
    count(*)                             as event_count,
    max(processed_at)                    as last_updated
from "market_db"."public"."stg_stock_metrics"
group by symbol, date_trunc('day', event_time)
order by trade_date desc, symbol
  );
  