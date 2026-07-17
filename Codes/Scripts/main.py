"""
The main code...
"""
import os
import json
import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from model import PowerNet, engineer_features, get_feature_names

def main():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    print("=== Digital IC Power Prediction (Inference) ===")
    
    input_path = input("Input file path: ")
    # output_path = "predictions_output.json"
    preprocessor_path = "./Model/preprocessor.joblib"
    model_path = "./Model/power_predictor_model.pth"
    
    print(f"Input file path is: {input_path}\n")
    print(f"Loading '{preprocessor_path}' and '{model_path}'...")
    
    # 1. Loading Preprocessor
    if not os.path.exists(preprocessor_path) or not os.path.exists(model_path):
        print("Error: Model or preprocessor files are missing.")
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

    # 3. Data Scaling (Preprocessing)
    X_processed = preprocessor.transform(df_new[features])
    
    # 4. Loading the PyTorch model
    input_dim = X_processed.shape[1]
    model = PowerNet(input_dim).to(device)
    
    state_dict = torch.load(model_path, map_location=device)
    if isinstance(state_dict, nn.Module):
        model = state_dict
    else:
        model.load_state_dict(state_dict)
        
    model.eval()

    # 5. Inference
    X_tensor = torch.tensor(X_processed, dtype=torch.float32).to(device)
    with torch.no_grad():
        preds_log = model(X_tensor).cpu().numpy().flatten()
        
    predicted_power = np.expm1(preds_log)
    
    df_new['predicted_power_uW'] = predicted_power
    
    # 6. Saving results
    # output_data = df_new.to_dict(orient='records')
    # with open(output_path, 'w', encoding='utf-8') as f:
    #     json.dump(output_data, f, indent=4)
        
    # print(f"Prediction is over. The results were saved in '{output_path}':")
    print(f"Prediction is Over. ")
    for idx, val in enumerate(predicted_power):
        print(f"Row {idx+1} Predicted Power: {val:.4f} uW")

if __name__ == "__main__":
    main()

