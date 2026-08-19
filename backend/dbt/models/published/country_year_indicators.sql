-- Published mart: one row per country-year, indicators as columns. The single read surface for the
-- model (spec 002) and the dashboard (spec 005). Reads only the warehouse star (zone discipline).
select
    c.country_code,
    c.country_name,
    y.year,
    max(f.value) filter (where i.indicator_code = 'life_expectancy')      as life_expectancy,
    max(f.value) filter (where i.indicator_code = 'under5_mortality')     as under5_mortality,
    max(f.value) filter (where i.indicator_code = 'health_spend_pct_gdp') as health_spend_pct_gdp,
    max(f.value) filter (where i.indicator_code = 'gdp_per_capita')       as gdp_per_capita,
    max(f.value) filter (where i.indicator_code = 'internet_pct')         as internet_pct,
    max(f.value) filter (where i.indicator_code = 'fertility_rate')       as fertility_rate
from {{ ref('fact_indicator') }} f
join {{ ref('dim_country') }}   c on c.country_key   = f.country_key
join {{ ref('dim_indicator') }} i on i.indicator_key = f.indicator_key
join {{ ref('dim_year') }}      y on y.year_key      = f.year_key
group by c.country_code, c.country_name, y.year
