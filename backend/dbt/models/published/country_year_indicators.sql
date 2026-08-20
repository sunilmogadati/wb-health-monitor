-- Published mart: one row per country-year, indicators as columns. The single read surface for the
-- model (spec 002) and the dashboard (spec 005). Reads only the warehouse star (zone discipline).
--
-- Data quality (spec 008 / ADR-0007): the anomaly gate runs at the staging boundary and writes
-- flagged country-year-indicators to ingestion.data_quality_flag; this model NULLs those cells, so
-- the mart is clean at the source and no downstream consumer has to re-filter.
with observations as (
    select
        c.country_code,
        c.country_name,
        y.year,
        i.indicator_code as indicator,
        case when fl.country_code is not null then null else f.value end as value
    from {{ ref('fact_indicator') }} f
    join {{ ref('dim_country') }}   c on c.country_key   = f.country_key
    join {{ ref('dim_indicator') }} i on i.indicator_key = f.indicator_key
    join {{ ref('dim_year') }}      y on y.year_key      = f.year_key
    left join ingestion.data_quality_flag fl
        on fl.country_code = c.country_code
       and fl.year = y.year
       and fl.indicator = i.indicator_code
)
select
    country_code,
    country_name,
    year,
    max(value) filter (where indicator = 'life_expectancy')      as life_expectancy,
    max(value) filter (where indicator = 'under5_mortality')     as under5_mortality,
    max(value) filter (where indicator = 'health_spend_pct_gdp') as health_spend_pct_gdp,
    max(value) filter (where indicator = 'gdp_per_capita')       as gdp_per_capita,
    max(value) filter (where indicator = 'internet_pct')         as internet_pct,
    max(value) filter (where indicator = 'fertility_rate')       as fertility_rate
from observations
group by country_code, country_name, year
