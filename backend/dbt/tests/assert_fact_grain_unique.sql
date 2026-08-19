-- Grain guard (spec SC-003): fails if (country, indicator, year) is not unique in the fact.
select country_key, indicator_key, year_key, count(*) as n
from {{ ref('fact_indicator') }}
group by country_key, indicator_key, year_key
having count(*) > 1
