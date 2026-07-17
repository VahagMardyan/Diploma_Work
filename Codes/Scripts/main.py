import os
import json
import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from model import PowerNet

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
    else:
        print("Error: File format must be .json or .csv")
        return

    print(f"{len(df_new)} rows data read successfully!\n")

    # ------------------------------------------------------------------
    # Feature Engineering
    # ------------------------------------------------------------------
    df_new['v2_freq'] = (df_new['vdd'] ** 2) * df_new['clock_frequency_mhz']

    log_columns = [
        'cell_count', 'comb_cell_count', 'seq_cell_count', 
        'inv_count', 'buf_count', 'nand_count', 'nor_count', 'xor_count', 'mux_count', 'other_count',
        'total_area', 'num_nets', 'num_inputs', 'num_outputs'
    ]
    for col in log_columns:
        df_new[f"log_{col}"] = np.log1p(df_new[col])

    num_features = [
        'clock_frequency_mhz', 'toggle_rate', 'static_probability', 'vdd', 'temperature', 'v2_freq',
        'log_cell_count', 'log_comb_cell_count', 'log_seq_cell_count',
        'log_inv_count', 'log_buf_count', 'log_nand_count', 'log_nor_count', 
        'log_xor_count', 'log_mux_count', 'log_other_count',
        'log_total_area', 'log_num_nets', 'log_num_inputs', 'log_num_outputs',
        'avg_cell_area', 'max_fanout', 'avg_fanout', 'avg_fanin',
        'logic_depth', 'depth_mean', 'depth_std', 'depth_max',
        'avg_net_toggle', 'toggle_attenuation',
        'critical_path_delay', 'wns', 'tns'
    ]
    cat_features = ['process', 'pvt_corner']
    features = num_features + cat_features
    # ------------------------------------------------------------------

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
