import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv('../Datasets/dataset_power.csv')

selected_cols = [
    'clock_frequency_mhz', 'toggle_rate', 'cell_count', 
    'total_area', 'num_nets', 'max_fanout', 'vdd', 'temperature',
    'dynamic_power_uW', 'leakage_power_uW', 'total_power_uW'
]

rename_dict = {
    'clock_frequency_mhz': 'Freq (MHz)',
    'toggle_rate': 'Toggle Rate',
    'cell_count': 'Cell Count',
    'total_area': 'Area',
    'num_nets': 'Nets',
    'max_fanout': 'Max Fanout',
    'vdd': 'Vdd',
    'temperature': 'Temp',
    'dynamic_power_uW': 'P_dynamic',
    'leakage_power_uW': 'P_leakage',
    'total_power_uW': 'P_total'
}

corr = df[selected_cols].rename(columns=rename_dict).corr()

plt.style.use('dark_background')
fig, ax = plt.subplots(figsize=(10, 8), facecolor='#0D1117')
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
plt.title('Correlation Heatmap', color='white', fontsize=14, fontweight='bold', pad=20)

plt.tight_layout()
plt.savefig('correlation_heatmap.png', dpi=300)
plt.show()