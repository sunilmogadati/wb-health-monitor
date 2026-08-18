import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
import joblib

df = pd.read_csv("worldbank_final_dataset.csv")

feature_cols = ["gdp_per_capita", "health_expenditure_per_capita", "internet_users_pct", "population_growth"]
X = df[feature_cols]
y = df["life_expectancy"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = LinearRegression()
model.fit(X_train, y_train)

print("R2 on test set:", model.score(X_test, y_test))

low_cutoff = y.quantile(1 / 3)
high_cutoff = y.quantile(2 / 3)
print("Low cutoff:", low_cutoff, "| High cutoff:", high_cutoff)

joblib.dump(model, "life_expectancy_model.joblib")
joblib.dump((low_cutoff, high_cutoff), "life_expectancy_cutoffs.joblib")
print("Saved model and cutoffs")