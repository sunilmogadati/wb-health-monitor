-- Conformed country dimension: one row per country, stable integer surrogate key.
with countries as (
    select country_code, max(country_name) as country_name
    from {{ source('staging', 'wdi_observation') }}
    group by country_code
)
select
    dense_rank() over (order by country_code) as country_key,
    country_code,
    country_name
from countries
