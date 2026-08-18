import pandas as pd

raw = pd.read_csv('raw_worldbank_data.csv')

feature_cols = ['health_spend_pct_gdp', 'gdp_per_capita', 'internet_pct', 'fertility_rate']
target_col = 'life_expectancy'

df = raw.dropna(subset=[target_col] + feature_cols)

df = df.sort_values('time', ascending=False) if 'time' in df.columns else df
df = df.drop_duplicates(subset='country_code', keep='first')

country_meta = wb_country_names = None
try:
    import wbgapi as wb
    names = wb.economy.DataFrame()
    names = names[['name']].reset_index().rename(columns={'economy': 'country_code', 'name': 'country'})
    df = df.merge(names, on='country_code', how='left')
except Exception:
    pass

aggregates_keywords = ['World', 'income', 'IDA', 'IBRD', 'members', 'union', 'area', 'Arab World',
                        'East Asia', 'Europe & Central Asia', 'Latin America', 'Middle East',
                        'North America', 'South Asia', 'Sub-Saharan Africa', 'small states', 'OECD']

if 'country' in df.columns:
    mask = ~df['country'].astype(str).str.contains('|'.join(aggregates_keywords), case=False, na=False)
    df = df[mask]

df = df.reset_index(drop=True)

print('Final cleaned shape:', df.shape)
print(df[[target_col] + feature_cols].describe())

df.to_csv('processed_dataset.csv', index=False)
print('Saved processed_dataset.csv')