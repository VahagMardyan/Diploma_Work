import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

df = pd.read_csv("../Dataset/dataset_old_pairs/dataset_power_1.csv")
print(f"Dataset shape: {df.shape}")

# PVT_CORNERS = [
#     "saed05rvt_base_tt0p60v125c", "saed05rvt_base_tt0p60v25c", "saed05rvt_base_tt0p75v125c", "saed05rvt_base_tt0p75v25c",
#     "saed05rvt_base_ff0p660v125c", "saed05rvt_base_ff0p660v25c", "saed05rvt_base_ff0p825v125c", "saed05rvt_base_ff0p825v25c",
#     "saed05rvt_base_ss0p540v125c", "saed05rvt_base_ss0p540v25c", "saed05rvt_base_ss0p675v125c", "saed05rvt_base_ss0p675v25c"
# ]

PVT_CORNER = "saed05rvt_base_ss0p675v25c"

PROCESS = PVT_CORNER.split('_')[2][0:2].upper()
temp = PVT_CORNER.split('v')[-1]

def normalize_to_uw(row):
    unit = row['power_units'].split('/')[0]
    val = row['dynamic_power']

    if unit == 'mW':
        return val * 1000.0
    elif unit == 'uW':
        return val
    elif unit == 'nW':
        return val / 1000.0
    elif unit == 'pW':
        return val / 1000000.0
    return val

df['dynamic_power_uW'] = df.apply(normalize_to_uw, axis=1)

df_tt25 = df[df["pvt_corner"] == PVT_CORNER]

plt.figure(figsize=(12, 5))

plt.subplot(1, 2, 1)
for toggle in sorted(df_tt25["toggle_rate"].unique()):
    subset = df_tt25[df_tt25["toggle_rate"] == toggle]
    grouped = subset.groupby("clock_frequency_mhz")["dynamic_power_uW"].mean()
    plt.plot(grouped.index, grouped.values, 'o-', label=f"toggle={toggle}")

plt.xlabel("Frequency (MHz)")
plt.ylabel("Dynamic Power (uW)")
plt.title(f"Power vs Frequency ({PROCESS} {temp.split('c')[0]}°C)")
plt.legend()
plt.grid(alpha=0.3)

plt.subplot(1, 2, 2)
for freq in sorted(df_tt25["clock_frequency_mhz"].unique()):
    subset = df_tt25[df_tt25["clock_frequency_mhz"] == freq]
    grouped = subset.groupby("toggle_rate")["dynamic_power_uW"].mean()
    plt.plot(grouped.index, grouped.values, 'o-', label=f"{freq} MHz")

plt.xlabel("Toggle Rate")
plt.ylabel("Dynamic Power (uW)")
plt.title(f"Power vs Toggle Rate ({PROCESS} {temp.split('c')[0]}°C)")
plt.legend()
plt.grid(alpha=0.3)

plt.tight_layout()

# plt.savefig(f"./Images/result_{PVT_CORNER}", dpi=300, bbox_inches = 'tight')

plt.show()
# else:
#     print("Done!")
