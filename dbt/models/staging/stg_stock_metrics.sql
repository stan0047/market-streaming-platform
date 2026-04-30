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
from {{ source('public', 'stock_metrics') }}
where price is not null
  and symbol is not null
