import pandas as pd
import numpy as np
import joblib
import time
import os
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split, cross_validate
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, r2_score
import matplotlib.pyplot as plt
import shap

os.makedirs("./Models", exist_ok=True)
print("PART 0: Data Loading and Preprocessing...")

try:
    df_1 = pd.read_csv("../Dataset/dataset_old_pairs/dataset_power_1.csv")
    df_2 = pd.read_csv("../Dataset/dataset_new_pairs/dataset_power_2.csv")
except FileNotFoundError:
    df_1 = pd.read_csv("dataset_power_1.csv")
    df_2 = pd.read_csv("dataset_power_2.csv")

df = pd.concat([df_1, df_2], ignore_index=True)

redundant_designs = ['full_half_add_1bit', 'mux_condt']
df = df[~df['design_name'].isin(redundant_designs)]

def normalize_to_uw(row):
    unit = str(row['power_units']).split("/")[0].strip()
    val = row['dynamic_power']
    match unit:
        case 'mW' : return val * 1000.0
        case 'uW' : return val
        case 'nW' : return val / 1000.0
        case 'pW' : return val / 1000000.0
    return val

df['target_power_uW'] = df.apply(normalize_to_uw, axis=1)

df['vdd_squared'] = df['vdd'] ** 2
df['freq_x_toggle'] = df['clock_frequency_mhz'] * df['toggle_rate']

df_encoded = pd.get_dummies(df, columns=['process'], drop_first=True, dtype=int)

features = [
    'clock_frequency_mhz', 'toggle_rate', 'static_probability', 
    'cell_count', 'seq_cell_count', 'total_area', 'logic_depth', 
    'vdd', 'temperature', 'vdd_squared', 'freq_x_toggle'
]
process_cols = [col for col in df_encoded.columns if 'process' in col]
features.extend(process_cols)

x = df_encoded[features]
y = df_encoded['target_power_uW']

X_train, X_temp, y_train, y_temp = train_test_split(x, y, test_size=0.30, random_state=42)
X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.50, random_state=42)

print("\n--- Data Distribution Image ---")
print(f"Train (for Training & 5-Fold CV): {X_train.shape[0]} row (70%)")
print(f"Validation (Hold-out Validation):  {X_val.shape[0]} row (15%)")
print(f"Test (Unseen Final Test):         {X_test.shape[0]} row (15%)")
print("--------------------------------\n")

models = {
    "Linear Regression" : LinearRegression(),
    "Random Forest" : RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1),
    "XGBoost" : XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42, n_jobs=-1)
}

trained_models = {}
cv_results = {}
val_results = {}
test_results = {}

for name, model in models.items():
    print(f"--- Processing {name} ---")
    
    print(f"Running 5-Fold CV on Train set...")
    scoring = {
        'mae': 'neg_mean_absolute_error',
        'mape': 'neg_mean_absolute_percentage_error',
        'r2': 'r2'
    }
    cv_scores = cross_validate(model, X_train, y_train, cv=5, scoring=scoring, n_jobs=-1)
    
    cv_results[name] = {
        "CV Mean MAE (uW)": round(-np.mean(cv_scores['test_mae']), 4),
        "CV Mean MAPE (%)": round(-np.mean(cv_scores['test_mape']) * 100, 4),
        "CV Mean R²": round(np.mean(cv_scores['test_r2']), 4)
    }
    
    print(f"Training final {name} model...")
    model.fit(X_train, y_train)
    trained_models[name] = model

    y_val_pred = model.predict(X_val)
    val_results[name] = {
        "MAE (uW)" : round(mean_absolute_error(y_val, y_val_pred), 4),
        "MAPE (%)": round(mean_absolute_percentage_error(y_val, y_val_pred) * 100, 4),
        "R² Score" : round(r2_score(y_val, y_val_pred), 4)
    }

    start_time = time.time()
    y_test_pred = model.predict(X_test)
    elapsed_time = (time.time() - start_time) / len(X_test) * 1000
    
    test_results[name] = {
        "MAE (uW)": round(mean_absolute_error(y_test, y_test_pred), 4),
        "MAPE (%)": round(mean_absolute_percentage_error(y_test, y_test_pred) * 100, 4),
        "R² Score": round(r2_score(y_test, y_test_pred), 4),
        "Latency per Sample (ms)": round(elapsed_time, 6)
    }

print("\nPART 1: 5-Fold Cross-Validation Results (Train Set Sub-folds)")
print(pd.DataFrame(cv_results).T)

print("\nPART 2: Validation Set Results (15% Hold-out Check)")
print(pd.DataFrame(val_results).T)

print("\nPART 3: Generalization Test Results (15% Unseen Test Data)")
print(pd.DataFrame(test_results).T)

best_model_name = "Random Forest"
best_model = trained_models[best_model_name]
model_filename = "./Models/power_predictor.joblib"

joblib.dump(best_model, model_filename)
print(f"\nThe best model ({best_model_name}) was successfully saved to `{model_filename}`")

print("\nPART 4: SHAP (Shapley's Additive Explanations)")
print("Calculating SHAP values for Random Forest...")
explainer = shap.TreeExplainer(best_model)

X_shap_sample = X_test.sample(n=min(200, len(X_test)), random_state=42)
shap_values = explainer.shap_values(X_shap_sample)

SHAP_SUMMARY = "../Images/shap_summary.png"
plt.figure(figsize=(10, 6))
shap.summary_plot(shap_values, X_shap_sample, show=False)
plt.title("SHAP Feature Impact on Dynamic Power Prediction", fontsize=14)
plt.tight_layout()
plt.savefig(SHAP_SUMMARY, dpi=300)
print(f"SHAP graph successfully saved as `{SHAP_SUMMARY}`.")

