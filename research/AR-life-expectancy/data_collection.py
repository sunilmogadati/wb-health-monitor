import wbgapi as wb
import pandas as pd

indicators = {
    'SP.DYN.LE00.IN': 'life_expectancy',
    'SH.XPD.CHEX.GD.ZS': 'health_spend_pct_gdp',
    'NY.GDP.PCAP.CD': 'gdp_per_capita',
    'IT.NET.USER.ZS': 'internet_pct',
    'SP.DYN.TFRT.IN': 'fertility_rate'
}

raw = wb.data.DataFrame(list(indicators.keys()), mrv=3, skipBlanks=True, columns='series')
raw = raw.rename(columns=indicators)
raw = raw.reset_index()
raw = raw.rename(columns={'economy': 'country_code'})

print('Raw shape:', raw.shape)
raw.to_csv('raw_worldbank_data.csv', index=False)
print('Saved raw_worldbank_data.csv')