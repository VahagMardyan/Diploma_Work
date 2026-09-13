import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import torch
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupShuffleSplit

SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../Scripts'))
if SCRIPTS_DIR not in sys.path:
    sys.path.append(SCRIPTS_DIR)

# Import components directly from your existing model.py
try:
    from Scripts.model import (
        DynamicResNet,
        LeakageResNet, 
        engineer_domain_features, 
        get_dynamic_features, 
        get_leakage_features
    )
except ImportError:
    print("[!] Error: Could not import from model.py. Ensure model.py is in the same directory.")
    sys.exit(1)

# Design & Style Settings
sns.set_theme(style="whitegrid")
plt.rcParams.update({'font.size': 11, 'figure.autolayout': True})

MODEL_DIR = '../Scripts/Model'  # Adjust path if needed

def load_all_models():
    """Loads preprocessors and trained PyTorch ResNet models."""
    print("[*] Loading trained models and preprocessors...")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    # Load Dynamic Model & Preprocessor
    prep_dyn = joblib.load(os.path.join(MODEL_DIR, "preprocessor_dynamic.joblib"))
    dyn_state = torch.load(os.path.join(MODEL_DIR, "dynamic_power_predictor_model.pth"), map_location=device, weights_only=True)
    dyn_features, _, _ = get_dynamic_features()
    dummy_input_dim_dyn = len(dyn_features) # Will be dynamically sized during inference setup
    model_dyn = DynamicResNet
    
    # Load Leakage Model & Preprocessor
    prep_leak = joblib.load(os.path.join(MODEL_DIR, "preprocessor_leakage.joblib"))
    leak_state = torch.load(os.path.join(MODEL_DIR, "leakage_power_predictor_model.pth"), map_location=device, weights_only=True)
    model_leak = LeakageResNet

    return prep_dyn, dyn_state, prep_leak, leak_state, device

def predict_power(df, models):
    """Runs real PyTorch inference on the dataframe."""
    prep_dyn, dyn_state, prep_leak, leak_state, device = models
    
    df_eng = engineer_domain_features(df)
    
    # 1. Dynamic Power Inference
    dyn_features, _, _ = get_dynamic_features()
    X_dyn = prep_dyn.transform(df_eng[dyn_features]).astype(np.float32)
    X_dyn_tensor = torch.tensor(X_dyn, device=device)
    
    model_dyn = DynamicResNet(X_dyn.shape[1]).to(device)
    model_dyn.load_state_dict(dyn_state)
    model_dyn.eval()
    
    with torch.no_grad():
        pred_dyn_log = model_dyn(X_dyn_tensor).cpu().numpy().flatten()
    df['predicted_dynamic_power_uW'] = np.exp(pred_dyn_log)
    
    # 2. Leakage Power Inference
    leak_features, _, _ = get_leakage_features()
    X_leak = prep_leak.transform(df_eng[leak_features]).astype(np.float32)
    X_leak_tensor = torch.tensor(X_leak, device=device)
    
    model_leak = LeakageResNet(X_leak.shape[1]).to(device)
    model_leak.load_state_dict(leak_state)
    model_leak.eval()
    
    with torch.no_grad():
        pred_leak_log = model_leak(X_leak_tensor).cpu().numpy().flatten()
    df['predicted_leakage_power_uW'] = np.exp(pred_leak_log)
    
    # 3. Total Power Inference
    df['predicted_total_power_uW'] = df['predicted_dynamic_power_uW'] + df['predicted_leakage_power_uW']
    
    power_types = [
        ('total_power_uW', 'predicted_total_power_uW', 'error_total_power_uW_%'),
        ('dynamic_power_uW', 'predicted_dynamic_power_uW', 'error_dynamic_power_uW_%'),
        ('leakage_power_uW', 'predicted_leakage_power_uW', 'error_leakage_power_uW_%')
    ]
    for actual_col, pred_col, err_col in power_types:
        df[err_col] = np.abs((df[actual_col] - df[pred_col]) / df[actual_col]) * 100
        
    return df

def load_data_and_split(file_list, models):
    dfs = []
    for filepath in file_list:
        if os.path.exists(filepath):
            dfs.append(pd.read_csv(filepath))
        else:
            print(f"[!] Warning: File not found: {filepath}")
            
    if not dfs:
        return None

    df = pd.concat(dfs, ignore_index=True)
    df = df[df["cell_count"] > 0].reset_index(drop=True)

    unique_groups = df["design_name"].nunique()

    if unique_groups > 1:
        indices = np.arange(len(df))
        groups = df["design_name"].to_numpy()
        gss_test = GroupShuffleSplit(n_splits=1, test_size=0.15, random_state=42)
        train_val_idx, test_idx = next(gss_test.split(indices, groups=groups))
        df_test = df.iloc[test_idx].copy()
    else:
        df_test = df.copy()

    return predict_power(df_test, models)

def calculate_metrics_dict(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true, dtype=np.float64), np.asarray(y_pred, dtype=np.float64)
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)
    
    mask = y_true > 0.1
    mape_stable = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0 if mask.any() else float("nan")
    smape = np.mean(2.0 * np.abs(y_pred - y_true) / (np.abs(y_true) + np.abs(y_pred) + 1e-6)) * 100.0

    return mae, r2, smape, mape_stable

def process_single_dataset(df_test, key_name):
    output_image_name = f"power_analysis_{key_name}.png"
    targets = [
        ("Total Power", "total_power_uW", "predicted_total_power_uW", "error_total_power_uW_%"),
        ("Dynamic Power", "dynamic_power_uW", "predicted_dynamic_power_uW", "error_dynamic_power_uW_%"),
        ("Leakage Power", "leakage_power_uW", "predicted_leakage_power_uW", "error_leakage_power_uW_%")
    ]

    metrics_summary = []
    fig, axes = plt.subplots(3, 3, figsize=(18, 14))

    for row_idx, (title_prefix, actual_col, pred_col, err_col) in enumerate(targets):
        y_true = df_test[actual_col].to_numpy()
        y_pred = df_test[pred_col].to_numpy()

        mae, r2, smape, mape_stable = calculate_metrics_dict(y_true, y_pred)
        
        metrics_summary.append({
            "Target": title_prefix,
            "MAE (uW)": f"{mae:.4f}",
            "R2 Score": f"{r2:.4f}",
            "sMAPE (%)": f"{smape:.2f}%",
            "MAPE (>0.1uW)": f"{mape_stable:.2f}%"
        })

        # Plot 1: Error Distribution
        ax1 = axes[row_idx, 0]
        sns.histplot(df_test[err_col], kde=True, color='#3B82F6', bins=30, ax=ax1, stat="density", alpha=0.4)
        ax1.axvline(15, color='#EF4444', linestyle='--', linewidth=2, label='15% Threshold')
        median_err = df_test[err_col].median()
        ax1.axvline(median_err, color='#10B981', linestyle='-', linewidth=2, label=f'Median ({median_err:.2f}%)')
        ax1.set_title(f'{title_prefix}: Relative Error (%)', fontsize=12, fontweight='bold')
        ax1.set_xlabel('Relative Error (%)')
        ax1.set_ylabel('Density')
        ax1.legend()

        # Plot 2: Actual vs Predicted
        ax2 = axes[row_idx, 1]
        ax2.scatter(df_test[actual_col], df_test[pred_col], alpha=0.4, color='#8B5CF6', edgecolors='none', s=25)
        max_val = max(df_test[actual_col].max(), df_test[pred_col].max())
        min_val = min(df_test[actual_col].min(), df_test[pred_col].min())
        ax2.plot([min_val, max_val], [min_val, max_val], color='#EF4444', linestyle='--', linewidth=1.8, label='Ideal (y = x)')
        ax2.set_title(f'{title_prefix}: Actual vs Predicted (uW)', fontsize=12, fontweight='bold')
        ax2.set_xlabel(f'Actual {title_prefix} (uW)')
        ax2.set_ylabel(f'Predicted {title_prefix} (uW)')
        ax2.legend()

        # Plot 3: Relative Error vs Actual
        ax3 = axes[row_idx, 2]
        ax3.scatter(df_test[actual_col], df_test[err_col], alpha=0.4, color='#F59E0B', s=25)
        ax3.axhline(15, color='#EF4444', linestyle='--', label='15% Error Threshold')
        ax3.set_title(f'{title_prefix}: Error vs Actual Power', fontsize=12, fontweight='bold')
        ax3.set_xlabel(f'Actual {title_prefix} (uW)')
        ax3.set_ylabel('Relative Error (%)')
        ax3.legend()

    plt.tight_layout()
    plt.savefig(output_image_name, dpi=300)
    plt.close()

    print(f"[+] Saved plot: '{output_image_name}'")
    return output_image_name, metrics_summary

def main():
    datasets = {
        "filter" : [
            '../../Verilog/Test/filter/dataset_power_test.csv',
            '../../Verilog/Test/filter/dataset_power_test_alt.csv'
        ],
        "encoder" : [
            '../../Verilog/Test/encoder/dataset_power_test_encoder.csv'
        ],
        "decoder" : [
            '../../Verilog/Test/decoder/dataset_power_test_decoder.csv'
        ],
        "dataset" : [
            '../Datasets/dataset_power.csv',   
            '../Datasets/dataset_power_alt.csv',   
        ],
        "tests" : [
            '../../Verilog/Test/tests/dataset_power_test.csv'
        ]
    }

    report_file_name = "metrics_report.md"
    models = load_all_models()

    with open(report_file_name, 'w', encoding='utf-8') as f:
        f.write("# Consolidated Power Prediction Evaluation Report\n\n")

    for key, file_list in datasets.items():
        print(f"\nProcessing dataset key: '{key}'...")
        df_test = load_data_and_split(file_list, models)
        
        if df_test is None:
            print(f"[!] Skipping '{key}' due to missing files.")
            continue

        image_name, metrics_summary = process_single_dataset(df_test, key)

        with open(report_file_name, 'a', encoding='utf-8') as f:
            f.write(f"## Dataset: `{key}`\n\n")
            f.write(f"![Power Analysis - {key}]({image_name})\n\n")
            f.write("| Target | MAE (uW) | R2 Score | sMAPE (%) | MAPE (>0.1uW) |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- |\n")
            for item in metrics_summary:
                f.write(f"| {item['Target']} | {item['MAE (uW)']} | {item['R2 Score']} | {item['sMAPE (%)']} | {item['MAPE (>0.1uW)']} |\n")
            f.write("\n---\n\n")

    print(f"\n[+] All evaluations completed. Master report saved in '{report_file_name}'")

if __name__ == "__main__":
    main()
