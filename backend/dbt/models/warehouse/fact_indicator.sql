-- Fact at the declared grain: one row per country x indicator x year, keyed to the three dims.
-- staging is already at this grain, so the joins are 1:1; the relationships/grain tests prove it.
select
    c.country_key,
    i.indicator_key,
    y.year_key,
    o.value
from {{ source('staging', 'wdi_observation') }} o
join {{ ref('dim_country') }}   c on c.country_code   = o.country_code
join {{ ref('dim_indicator') }} i on i.indicator_code = o.indicator
join {{ ref('dim_year') }}      y on y.year           = o.year
