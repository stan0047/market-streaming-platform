
  create view "market_db"."public"."stg_stock_metrics__dbt_tmp"
    
    
  as (
    select
    id,
    symbol,
    price,
    previous_close,
    change_pct,
    volume,
    market_cap,
    event_time,
    processed_at,
    source,
    case when change_pct > 0 then 'up'
         when change_pct < 0 then 'down'
         else 'flat' end as direction
from "market_db"."public"."stock_metrics"
where price is not null
  and symbol is not null
  );