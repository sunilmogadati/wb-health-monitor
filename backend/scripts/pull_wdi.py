"""Pull World Bank WDI health indicators (Sub-Saharan Africa) and write a tidy long CSV.

Runs on the HOST (needs wbgapi + pandas, same as explore_wb.py). Output lands under
backend/data/ which is bind-mounted into the api container at /workspace/backend/data.
Then load it with:  make ingest   (or scripts/load_wdi.py inside the container)
"""
from pathlib import Path

import wbgapi as wb

INDICATORS = {
    # target + core health
    "SP.DYN.LE00.IN": "life_expectancy",       # target
    "SH.DYN.MORT": "under5_mortality",
    "SH.XPD.CHEX.GD.ZS": "health_spend_pct_gdp",
    "SH.UHC.SRVS.CV.XD": "uhc_index",           # sparse — usually dropped
    # context features for spec 002 (country-health-model)
    "NY.GDP.PCAP.CD": "gdp_per_capita",         # current US$
    "IT.NET.USER.ZS": "internet_pct",           # % individuals using the internet
    "SP.DYN.TFRT.IN": "fertility_rate",         # births per woman
}
REGION = "SSF"          # Sub-Saharan Africa; use economy="all" for every country
YEAR_FROM, YEAR_TO = 2015, 2022
OUT = Path(__file__).resolve().parent.parent / "data" / "wdi_observation.csv"


def main() -> None:
    economies = wb.region.members(REGION)
    df = wb.data.DataFrame(
        list(INDICATORS),
        economy=economies,
        time=range(YEAR_FROM, YEAR_TO + 1),
        columns="series",
        labels=True,
    ).reset_index().rename(columns=INDICATORS)

    id_cols = [c for c in df.columns if c not in INDICATORS.values()]
    long = df.melt(id_vars=id_cols, var_name="indicator", value_name="value")

    long["country_code"] = long["economy"]
    long["country_name"] = long["Country"] if "Country" in long.columns else long["economy"]
    if "time" in long.columns:
        time_col = "time"
    elif "Time" in long.columns:
        time_col = "Time"
    else:
        time_col = id_cols[-1]
    long["year"] = long[time_col].astype(str).str.extract(r"(\d{4})")[0].astype("Int64")

    out = (
        long[["country_code", "country_name", "year", "indicator", "value"]]
        .dropna(subset=["value", "year"])
        .sort_values(["country_code", "year", "indicator"])
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(f"wrote {len(out)} rows, {out.country_code.nunique()} countries, "
          f"{out.indicator.nunique()} indicators -> {OUT}")


if __name__ == "__main__":
    main()
