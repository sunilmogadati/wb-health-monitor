import pandas as pd
import joblib
import numpy as np
from langchain.tools import tool

df = pd.read_csv("worldbank_final_dataset.csv")
model = joblib.load("life_expectancy_model.joblib")
low_cutoff, high_cutoff = joblib.load("life_expectancy_cutoffs.joblib")


def classify(value):
    if value <= low_cutoff:
        return "Low"
    elif value <= high_cutoff:
        return "Medium"
    else:
        return "High"


@tool
def lookup_country(country_name: str) -> str:
    """Looks up a real country's actual recorded life expectancy and development
    statistics (GDP per capita, health expenditure, internet users, population growth)
    directly from the World Bank dataset. Use this when the user asks about a real,
    named country rather than a hypothetical scenario."""

    match = df[df["country"].str.lower() == country_name.lower()]
    if match.empty:
        return f"No country found matching '{country_name}' in the dataset."

    row = match.iloc[0]
    category = classify(row["life_expectancy"])
    return (
        f"{row['country']}: actual life expectancy is {row['life_expectancy']:.2f} years "
        f"({category}). GDP per capita: {row['gdp_per_capita']:.2f}, "
        f"health expenditure per capita: {row['health_expenditure_per_capita']:.2f}, "
        f"internet users: {row['internet_users_pct']:.2f}%, "
        f"population growth: {row['population_growth']:.2f}%."
    )


@tool
def predict_life_expectancy(gdp_per_capita: float, health_expenditure_per_capita: float, internet_users_pct: float, population_growth: float) -> str:
    """Predicts life expectancy for a hypothetical country using a trained model,
    based on GDP per capita in USD, health expenditure per capita in USD, percentage
    of population using the internet, and annual population growth rate as a percentage.
    Use this when the user gives you made-up or hypothetical numbers rather than asking
    about a real named country."""

    features = np.array([[gdp_per_capita, health_expenditure_per_capita, internet_users_pct, population_growth]])
    prediction = model.predict(features)[0]
    category = classify(prediction)
    return f"Predicted life expectancy: {round(float(prediction), 2)} years. Category: {category}."