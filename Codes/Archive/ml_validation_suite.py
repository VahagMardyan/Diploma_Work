import pandas as pd
import numpy as np
import joblib
import time
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from xgboost import XGBRegressor
from sklearn.model_selection import cross_validate
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, r2_score
import matplotlib.pyplot as plt
import shap

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

df_encoded = pd.get_dummies(df, columns=['process'], drop_first=True)

df_train_encoded = df_encoded.loc[df_train_val.index]
df_test_encoded = df_encoded.loc[df_test_unseen.index]

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

models = {
    "Linear Regression": LinearRegression(),
    "Random Forest": RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1),
    "XGBoost": XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42, n_jobs=-1)
}

print("==================================================")
print("PART 1: 5-Fold Cross-Validation (Stability check)")
print("==================================================\n")

cv_results_summary = {}
for name, model in models.items():
    print(f"5-Fold CV in progress for {name}...")
    cv_scores = cross_validate(
        model, X_train, y_train, cv=5,
        scoring={'mae': 'neg_mean_absolute_error', 'r2': 'r2'},
        n_jobs=-1
    )
    
    cv_results_summary[name] = {
        "CV Mean MAE (uW)": round(-cv_scores['test_mae'].mean(), 4),
        "CV Mean R²": round(cv_scores['test_r2'].mean(), 4)
    }

print("\n5-FOLD CROSS-VALIDATION RESULTS (on Train data).")
print(pd.DataFrame(cv_results_summary).T)

print("\n==================================================")
print("PART 2: Generalization Test (Prediction of an unknown pattern)")
print("==================================================\n")

unseen_results = {}
trained_models = {}

for name, model in models.items():
    model.fit(X_train, y_train)
    trained_models[name] = model
    
    start_time = time.time()
    y_pred = model.predict(X_test_unseen)
    elapsed_time = (time.time() - start_time) / len(X_test_unseen) * 1000
    
    mae = mean_absolute_error(y_test_unseen, y_pred)
    mape = mean_absolute_percentage_error(y_test_unseen, y_pred) * 100
    r2 = r2_score(y_test_unseen, y_pred)
    
    unseen_results[name] = {
        "MAE (uW)": round(mae, 4),
        "MAPE (%)": round(mape, 4),
        "R² Score": round(r2, 4),
        "Latency per Sample (ms)": round(elapsed_time, 6)
    }

df_unseen_results = pd.DataFrame(unseen_results).T
print(f"Results for a completely new schema (`{unseen_design}`).")
print(df_unseen_results)

# best_model_name = "Random Forest"
# joblib.dump(trained_models[best_model_name], "power_predictor_rf.joblib")
# print(f"\nThe best model ({best_model_name}) was successfully saved to `power_predictor_rf.joblib`")

print("\n==================================================")
print("PART 3: SHAP (Shapley's Additive Explanations)")
print("==================================================\n")

print("Calculating SHAP values for Random Forest...")
rf_model = trained_models["Random Forest"]
explainer = shap.TreeExplainer(rf_model)

X_shap_sample = X_test_unseen.sample(n=min(200, len(X_test_unseen)), random_state=42)
shap_values = explainer.shap_values(X_shap_sample)

SHAP_SUMMARY = "shap_summary.png"

plt.figure(figsize=(10, 6))
shap.summary_plot(shap_values, X_shap_sample, show=False)
plt.title("SHAP Feature Impact on Dynamic Power Prediction", fontsize=14)
plt.tight_layout()
# plt.savefig(SHAP_SUMMARY, dpi=300)
# print(f"SHAP graph saved as `{SHAP_SUMMARY}`.")
plt.show()