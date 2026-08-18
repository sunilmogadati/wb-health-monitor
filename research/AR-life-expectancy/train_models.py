import pandas as pd
import numpy as np
import json
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, AdaBoostRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from xgboost import XGBRegressor
import joblib

df = pd.read_csv('processed_dataset.csv')

feature_cols = ['health_spend_pct_gdp', 'gdp_per_capita', 'internet_pct', 'fertility_rate']
target_col = 'life_expectancy'

X = df[feature_cols]
y = df[target_col]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)
joblib.dump(scaler, 'feature_scaler.joblib')

models = {
    'Linear Regression': (LinearRegression(), False),
    'Decision Tree': (DecisionTreeRegressor(max_depth=5, random_state=42), False),
    'Random Forest': (RandomForestRegressor(n_estimators=300, max_depth=8, random_state=42), False),
    'KNN': (KNeighborsRegressor(n_neighbors=7), True),
    'XGBoost': (XGBRegressor(n_estimators=300, max_depth=4, learning_rate=0.05, random_state=42), False),
    'AdaBoost': (AdaBoostRegressor(n_estimators=200, learning_rate=0.05, random_state=42), False)
}

filenames = {
    'Linear Regression': 'model_linear_regression.joblib',
    'Decision Tree': 'model_decision_tree.joblib',
    'Random Forest': 'model_random_forest.joblib',
    'KNN': 'model_knn.joblib',
    'XGBoost': 'model_xgboost.joblib',
    'AdaBoost': 'model_adaboost.joblib'
}

results = []
trained_models = {}

for name, (model, needs_scaling) in models.items():
    if needs_scaling:
        model.fit(X_train_scaled, y_train)
        predictions = model.predict(X_test_scaled)
    else:
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)

    r2 = r2_score(y_test, predictions)
    rmse = np.sqrt(mean_squared_error(y_test, predictions))
    mae = mean_absolute_error(y_test, predictions)

    results.append({'model': name, 'r2': r2, 'rmse': rmse, 'mae': mae, 'needs_scaling': needs_scaling})
    trained_models[name] = model
    joblib.dump(model, filenames[name])
    print(name, '-> R2:', round(r2, 4), '| RMSE:', round(rmse, 3), '| MAE:', round(mae, 3))

results_df = pd.DataFrame(results).sort_values('r2', ascending=False).reset_index(drop=True)
results_df.to_csv('model_comparison_results.csv', index=False)

best_model_name = results_df.iloc[0]['model']
best_model = trained_models[best_model_name]
joblib.dump(best_model, 'best_model.joblib')

if hasattr(best_model, 'feature_importances_'):
    importances = dict(zip(feature_cols, best_model.feature_importances_.tolist()))
elif hasattr(best_model, 'coef_'):
    importances = dict(zip(feature_cols, best_model.coef_.tolist()))
else:
    importances = {}

summary = {
    'feature_cols': feature_cols,
    'target_col': target_col,
    'n_train': len(X_train),
    'n_test': len(X_test),
    'best_model': best_model_name,
    'results': results_df.to_dict(orient='records'),
    'feature_importances': importances
}

with open('run_summary.json', 'w') as f:
    json.dump(summary, f, indent=2)

print('\nBest model:', best_model_name)
print('Saved all 6 models, best_model.joblib, feature_scaler.joblib, model_comparison_results.csv, run_summary.json')