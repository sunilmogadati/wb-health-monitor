import os
from pathlib import Path

import joblib
import pandas as pd

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from openai import OpenAI, OpenAIError
from pydantic import BaseModel, ConfigDict


# --------------------------------------------------
# Configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

DATA_PATH = BASE_DIR / "data" / "cleaned_health_data.csv"
MODEL_PATH = BASE_DIR / "models" / "life_expectancy_xgboost.joblib"
OPENAI_BRIEF_MODEL = os.getenv("OPENAI_BRIEF_MODEL", "gpt-4.1-mini")


FEATURES = [
    "health_spend_pct_gdp",
    "gdp_per_capita",
    "internet_pct",
    "fertility_rate",
    "urban_population_pct",
    "population",
    "unemployment_pct",
    "basic_sanitation_pct",
]


# --------------------------------------------------
# Load model + dataset
# --------------------------------------------------

df = pd.read_csv(DATA_PATH)

model = joblib.load(MODEL_PATH)


# --------------------------------------------------
# FastAPI
# --------------------------------------------------

app = FastAPI(
    title="Country Health API",
    description="Predict life expectancy using World Bank indicators.",
    version="1.0.0",
)


# --------------------------------------------------
# Schemas
# --------------------------------------------------

class PredictionRequest(BaseModel):
    country: str
    year: int


class HealthIndicators(BaseModel):
    health_spend_pct_gdp: float | None
    gdp_per_capita: float | None
    internet_pct: float | None
    fertility_rate: float | None
    urban_population_pct: float | None
    population: float | None
    unemployment_pct: float | None
    basic_sanitation_pct: float | None


class PredictionResponse(BaseModel):
    country: str
    year: int
    predicted_life_expectancy: float
    actual_life_expectancy: float | None
    model: str
    indicators: HealthIndicators


class CountryHealthBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    country: str
    year: int
    predicted_life_expectancy: float
    summary: str
    strengths: list[str]
    concerns: list[str]
    outlook: str
    recommendation: str


class BriefText(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    strengths: list[str]
    concerns: list[str]
    outlook: str
    recommendation: str


# --------------------------------------------------
# Helper
# --------------------------------------------------

def get_openai_client() -> OpenAI:

    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not configured",
        )

    return OpenAI()


def get_country_data(country: str, year: int) -> pd.Series:

    matches = df[
        (df["Country Name"].str.lower() == country.lower())
        & (df["Year"] == year)
    ]

    if matches.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for {country} in {year}",
        )

    return matches.iloc[0]


def build_prediction(row: pd.Series) -> PredictionResponse:

    # Preserve DataFrame + column names because
    # the sklearn pipeline was trained with these features.
    X = row[FEATURES].to_frame().T

    prediction = model.predict(X)[0]

    actual = row.get("life_expectancy")

    if pd.isna(actual):
        actual = None
    else:
        actual = float(actual)

    indicators = {}

    for feature in FEATURES:

        value = row[feature]

        indicators[feature] = (
            None
            if pd.isna(value)
            else float(value)
        )

    return PredictionResponse(
        country=row["Country Name"],
        year=int(row["Year"]),
        predicted_life_expectancy=round(
            float(prediction),
            2,
        ),
        actual_life_expectancy=actual,
        model="XGBoost",
        indicators=HealthIndicators(**indicators),
    )


def create_health_brief(prediction: PredictionResponse) -> CountryHealthBrief:

    client = get_openai_client()

    prompt = f"""
Create a concise country health brief for a policy audience.

Use only the provided model output and indicators. Do not invent facts,
program names, causes, or future events.

Country: {prediction.country}
Year: {prediction.year}
Predicted life expectancy: {prediction.predicted_life_expectancy}
Actual life expectancy, if available: {prediction.actual_life_expectancy}

Indicators:
- Current health expenditure (% of GDP): {prediction.indicators.health_spend_pct_gdp}
- GDP per capita (current US$): {prediction.indicators.gdp_per_capita}
- Internet use (% of population): {prediction.indicators.internet_pct}
- Fertility rate (births per woman): {prediction.indicators.fertility_rate}
- Urban population (% of total): {prediction.indicators.urban_population_pct}
- Population: {prediction.indicators.population}
- Unemployment (% of labor force): {prediction.indicators.unemployment_pct}
- Basic sanitation access (% of population): {prediction.indicators.basic_sanitation_pct}

Keep the summary, outlook, and recommendation to one sentence each.
Each strength and concern should be a short phrase.
"""

    try:
        response = client.responses.create(
            model=OPENAI_BRIEF_MODEL,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You write cautious, data-grounded public health "
                        "briefs from structured indicators."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "country_health_brief_text",
                    "schema": BriefText.model_json_schema(),
                    "strict": True,
                }
            },
        )
    except OpenAIError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"OpenAI request failed: {exc}",
        ) from exc

    brief_text = BriefText.model_validate_json(response.output_text)

    return CountryHealthBrief(
        country=prediction.country,
        year=prediction.year,
        predicted_life_expectancy=prediction.predicted_life_expectancy,
        summary=brief_text.summary,
        strengths=brief_text.strengths,
        concerns=brief_text.concerns,
        outlook=brief_text.outlook,
        recommendation=brief_text.recommendation,
    )


# --------------------------------------------------
# Routes
# --------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "Country Health API",
        "docs": "/docs",
    }


@app.get("/countries")
def get_countries():

    countries = sorted(
        df["Country Name"]
        .dropna()
        .unique()
        .tolist()
    )

    return {
        "count": len(countries),
        "countries": countries,
    }


@app.get("/countries/{country}/years")
def get_country_years(country: str):

    matches = df[
        df["Country Name"].str.lower() == country.lower()
    ]

    if matches.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Country '{country}' not found",
        )

    years = sorted(
        matches["Year"]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    return {
        "country": matches.iloc[0]["Country Name"],
        "years": years,
    }


@app.post(
    "/predict",
    response_model=PredictionResponse,
)
def predict(request: PredictionRequest):

    row = get_country_data(
        request.country,
        request.year,
    )

    return build_prediction(row)


@app.post(
    "/health-brief",
    response_model=CountryHealthBrief,
)
def health_brief(request: PredictionRequest):

    row = get_country_data(
        request.country,
        request.year,
    )

    prediction = build_prediction(row)

    return create_health_brief(prediction)
