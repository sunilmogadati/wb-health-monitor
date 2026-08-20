/**
 * Indicator codes the published mart exposes (backend/dbt/models/published/country_year_indicators.sql,
 * spec 003). Spec 005 has no "list indicators" endpoint, so this is a small, deliberately static
 * mirror of that contract for the picker UI.
 */
export const INDICATORS = [
  { code: "life_expectancy", label: "Life expectancy" },
  { code: "under5_mortality", label: "Under-5 mortality" },
  { code: "health_spend_pct_gdp", label: "Health spend (% of GDP)" },
  { code: "gdp_per_capita", label: "GDP per capita" },
  { code: "internet_pct", label: "Internet users (%)" },
  { code: "fertility_rate", label: "Fertility rate" },
] as const;

export const DEFAULT_INDICATOR = INDICATORS[0].code;
