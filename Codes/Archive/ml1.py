import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
import matplotlib.pyplot as plt

df = pd.read_csv("dataset_power.csv")

def normalize_to_uw(row):
    unit = row['power_units'].split('/')[0]
    val = row['dynamic_power']
    if unit == 'mW': return val * 1000.0
    if unit == 'uW': return val
    if unit == 'nW': return val / 1000.0
    if unit == 'pW': return val / 1000000.0
    return val

df['target_power_uW'] = df.apply(normalize_to_uw, axis=1)

df['vdd_squared'] = df['vdd'] ** 2
df['freq_x_toggle'] = df['clock_frequency_mhz'] * df['toggle_rate']

unseen_design = "syncfifo"
df_train_val = df[df['design_name'] != unseen_design]
df_test_unseen = df[df['design_name'] == unseen_design]

print(f"Մարզման տվյալների չափը (առանց {unseen_design}-ի): {df_train_val.shape[0]} տող")
print(f"Թեստավորման տվյալների չափը (միայն {unseen_design}): {df_test_unseen.shape[0]} տող")

df_encoded = pd.get_dummies(df, columns=['process'], drop_first=True)

train_indices = df_train_val.index
test_indices = df_test_unseen.index

df_train_encoded = df_encoded.loc[train_indices]
df_test_encoded = df_encoded.loc[test_indices]

features = [
    'clock_frequency_mhz', 'toggle_rate', 'static_probability', 
    'cell_count', 'seq_cell_count', 'total_area', 'logic_depth', 
    'vdd', 'temperature', 'vdd_squared', 'freq_x_toggle'
]
process_cols = [col for col in df_encoded.columns if 'process_' in col]
features.extend(process_cols)

X_train = df_train_encoded[features]
y_train = df_train_encoded['target_power_uW']

X_test_unseen = df_test_encoded[features]
y_test_unseen = df_test_encoded['target_power_uW']

print(f"\nՄոդելը մարզվում է բոլոր սխեմաների վրա, բացի `{unseen_design}`-ից...")
model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
model.fit(X_train, y_train)
print("Մարզումն ավարտվեց։")

y_pred_unseen = model.predict(X_test_unseen)

mae = mean_absolute_error(y_test_unseen, y_pred_unseen)
r2 = r2_score(y_test_unseen, y_pred_unseen)

print(f"\n📊 ԱՐԴՅՈՒՆՔՆԵՐԸ ԼՐԻՎ ՆՈՐ ՍԽԵՄԱՅԻ (`{unseen_design}`) ՀԱՄԱՐ:")
print(f"Mean Absolute Error (MAE): {mae:.4f} uW")
print(f"R² Score (Ճշտության գործակից): {r2:.4f}")

plt.figure(figsize=(6, 6))
plt.scatter(y_test_unseen, y_pred_unseen, alpha=0.6, color='purple')
plt.plot([y_test_unseen.min(), y_test_unseen.max()], [y_test_unseen.min(), y_test_unseen.max()], 'r--', lw=2)
plt.xlabel(f"Իրական հզորություն {unseen_design} (uW)")
plt.ylabel(f"Կանխատեսված հզորություն {unseen_design} (uW)")
plt.title(f"Generalization Test: Predicting Unseen Design ({unseen_design})")
plt.grid(alpha=0.3)
plt.savefig("unseen_design_test.png", dpi=300)
plt.show()