-- Simple year dimension (promote to a full dim_date only if later specs need month/quarter grain).
with years as (
    select distinct year
    from {{ source('staging', 'wdi_observation') }}
)
select
    dense_rank() over (order by year) as year_key,
    year
from years
