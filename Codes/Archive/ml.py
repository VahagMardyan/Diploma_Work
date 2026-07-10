import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
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

df_encoded = pd.get_dummies(df, columns=['process', 'design_name'], drop_first=True)

features = [
    'clock_frequency_mhz', 'toggle_rate', 'static_probability', 
    'cell_count', 'seq_cell_count', 'total_area', 'logic_depth', 
    'vdd', 'temperature', 'vdd_squared', 'freq_x_toggle'
]
encoded_columns = [col for col in df_encoded.columns if 'process_' in col or 'design_name_' in col]
features.extend(encoded_columns)

X = df_encoded[features]
y = df_encoded['target_power_uW']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print(f"Train հավաքածուի չափսը: {X_train.shape}")
print(f"Test հավաքածուի չափսը: {X_test.shape}")

print("\nՄոդելը մարզվում է... Սա կարող է տևել մի քանի վայրկյան...")
model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
model.fit(X_train, y_train)
print("Մարզումն ավարտվեց։")

y_pred = model.predict(X_test)

mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print(f"\n📊 ՄՈԴԵԼԻ ԱՐԴՅՈՒՆՔՆԵՐԸ:")
print(f"Mean Absolute Error (MAE): {mae:.4f} uW")
print(f"R² Score (Ճշտության գործակից): {r2:.4f}")

# plt.figure(figsize=(6, 6))
# plt.scatter(y_test, y_pred, alpha=0.5, color='blue')
# plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', lw=2)
# plt.xlabel("Իրական հզորություն (uW)")
# plt.ylabel("Կանխատեսված հզորություն (uW)")
# plt.title("Actual vs Predicted Power")
# plt.grid(alpha=0.3)
# # plt.savefig("ml.png", dpi = 300, bbox_inches = 'tight')
# plt.show()

importances = model.feature_importances_
indices = np.argsort(importances)[::-1]

# Ցույց տանք թոփ 10 ամենակարևոր հատկանիշները
print("\n🔥 FEATURE IMPORTANCE (Ամենակարևոր հատկանիշները):")
for f in range(min(10, len(features))):
    print(f"{f + 1}. {features[indices[f]]} ({importances[indices[f]]:.4f})")

# Գրաֆիկի կառուցում
plt.figure(figsize=(10, 6))
plt.title("Feature Importances for Power Prediction")
plt.bar(range(min(10, len(features))), importances[indices[:10]], align="center", color="teal")
plt.xticks(range(min(10, len(features))), [features[i] for i in indices[:10]], rotation=45, ha='right')
plt.tight_layout()
plt.savefig("feature_importance.png", dpi=300)
plt.show()