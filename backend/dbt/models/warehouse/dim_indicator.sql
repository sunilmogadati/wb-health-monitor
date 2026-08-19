-- Conformed indicator dimension: one row per indicator.
with indicators as (
    select distinct indicator as indicator_code
    from {{ source('staging', 'wdi_observation') }}
)
select
    dense_rank() over (order by indicator_code) as indicator_key,
    indicator_code,
    indicator_code as indicator_name
from indicators
