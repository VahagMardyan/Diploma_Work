import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Dataset-ի բեռնում
df1 = pd.read_csv('../Datasets/dataset_power.csv')
df2 = pd.read_csv('../Datasets/dataset_power_alt.csv')
df = pd.concat([df1, df2], ignore_index=True)

# 2. Feature Engineering (Ֆիզիկական կախվածությունների մոդելավորում)

# Dynamic Power Proxy: alpha * C_est * Vdd^2 * f
# C_est-ը գնահատվում է total_area * max_fanout արտադրյալով
df['dyn_power_proxy'] = np.log1p(
    df['toggle_rate'] * 
    (df['total_area'] * df['max_fanout']) * 
    (df['vdd'] ** 2) * 
    df['clock_frequency_mhz']
)

# Leakage Temperature Proxy: Area * exp(k * Temp)
# Subthreshold leakage-ի էքսպոնենցիալ կախվածության համար
df['leak_temp_proxy'] = df['total_area'] * np.exp(0.015 * df['temperature'])

# Normalized target-ներ (Power per Area)
df['dyn_power_per_area'] = df['dynamic_power_uW'] / (df['total_area'] + 1e-5)
df['leak_power_per_area'] = df['leakage_power_uW'] / (df['total_area'] + 1e-5)

# 3. Սյուների ընտրություն վիզուալիզացիայի համար
selected_cols = [
    'clock_frequency_mhz', 'toggle_rate', 'cell_count', 
    'total_area', 'max_fanout', 'vdd', 'temperature',
    'dyn_power_proxy', 'leak_temp_proxy',
    'dynamic_power_uW', 'leakage_power_uW', 'total_power_uW'
]

rename_dict = {
    'clock_frequency_mhz': 'Freq (MHz)',
    'toggle_rate': 'Toggle Rate',
    'cell_count': 'Cell Count',
    'total_area': 'Area',
    'max_fanout': 'Max Fanout',
    'vdd': 'Vdd',
    'temperature': 'Temp',
    'dyn_power_proxy': 'Dyn Proxy',
    'leak_temp_proxy': 'Leak Proxy',
    'dynamic_power_uW': 'P_dynamic',
    'leakage_power_uW': 'P_leakage',
    'total_power_uW': 'P_total'
}

# 4. Correlation matrix-ի հաշվարկ
corr = df[selected_cols].rename(columns=rename_dict).corr()

# 5. Visual styling & plot setup
plt.style.use('dark_background')
fig, ax = plt.subplots(figsize=(12, 10), facecolor='#0D1117')
ax.set_facecolor('#0D1117')

sns.heatmap(
    corr, 
    annot=True, 
    fmt=".2f", 
    cmap="coolwarm", 
    vmin=-1, vmax=1,
    linewidths=1, 
    linecolor='#1F2937',
    ax=ax,
    annot_kws={"size": 9, "weight": "bold"}
)

plt.xticks(rotation=45, ha='right', color='white', fontsize=10)
plt.yticks(rotation=0, color='white', fontsize=10)
plt.title('Enhanced Correlation Heatmap (with Physical Proxies)', color='white', fontsize=14, fontweight='bold', pad=20)

plt.tight_layout()
plt.savefig('correlation_heatmap_enhanced.png', dpi=300)
plt.show()