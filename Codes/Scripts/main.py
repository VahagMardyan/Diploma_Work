"""
The main code (CLI)...
"""
import os
import json
import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from model import PowerNet, engineer_features, get_feature_names, TARGET_CONFIGS

def load_model(model_path, input_dim, device):
    model = PowerNet(input_dim).to(device)
    state_dict = torch.load(model_path, map_location=device)
    if isinstance(state_dict, nn.Module):
        model = state_dict.to(device)
    else:
        model.load_state_dict(state_dict)
    model.eval()
    return model

def main():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    print("=== Digital IC Power Prediction (Inference) ===")
    
    input_path = input("Input file path: ")
    preprocessor_path = "./Model/preprocessor.joblib"
    model_paths = {target: path for target, path in TARGET_CONFIGS.items()}
    
    print(f"Input file path is: {input_path}\n")
    print(f"Loading '{preprocessor_path}' and {len(model_paths)} model(s)...")
    
    # 1. Loading Preprocessor and checking model files
    missing = [p for p in [preprocessor_path, *model_paths.values()] if not os.path.exists(p)]
    if missing:
        print(f"Error: The following file(s) are missing: {', '.join(missing)}")
        return
        
    preprocessor = joblib.load(preprocessor_path)
    
    # 2. Reading input data
    if input_path.endswith('.json'):
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            data = [data]
        df_new = pd.DataFrame(data)
    elif input_path.endswith('.csv'):
        df_new = pd.read_csv(input_path)
    elif input_path.endswith('xlsx'):
        df_new = pd.read_excel(input_path)
    else:
        print("Error: File format must be `.json`, `.csv` or `xlsx`.")
        return

    print(f"{len(df_new)} rows data read successfully!\n")

    # Feature Engineering (Կիրառում ենք 1 տողով՝ 30 տողի փոխարեն)
    df_new = engineer_features(df_new)
    features, _, _ = get_feature_names()

    # 3. Data Scaling (Preprocessing) -- shared across all targets
    X_processed = preprocessor.transform(df_new[features])
    input_dim = X_processed.shape[1]
    X_tensor = torch.tensor(X_processed, dtype=torch.float32).to(device)

    # 4. Loading each model and predicting its target
    df_new = df_new.reset_index(drop=True)
    predictions = {}
    for target_column, model_path in model_paths.items():
        model = load_model(model_path, input_dim, device)
        with torch.no_grad():
            preds_log = model(X_tensor).cpu().numpy().flatten()
        predicted_values = np.expm1(preds_log)
        predictions[target_column] = predicted_values
        df_new[f'predicted_{target_column}'] = predicted_values

    # total_power_uW is derived, not modeled: it equals
    # dynamic_power_uW + leakage_power_uW exactly in the data, so we sum
    # the two predictions instead of training a third model for it.
    predictions['total_power_uW'] = predictions['dynamic_power_uW'] + predictions['leakage_power_uW']
    df_new['predicted_total_power_uW'] = predictions['total_power_uW']

    # 5. Printing results
    print("Prediction is Over.\n")
    print_order = ['total_power_uW', 'dynamic_power_uW', 'leakage_power_uW']
    for idx in range(len(df_new)):
        parts = [f"{target}: {predictions[target][idx]:.4f} uW" for target in print_order]
        print(f"Row {idx+1} -> " + " | ".join(parts))

if __name__ == "__main__":
    main()