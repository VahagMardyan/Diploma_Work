import pandas as pd
import numpy as np
import torch
import joblib
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split

# Մաքուր import առանց մարզումը նորից ակտիվացնելու
from model import PowerNet

def main():
    print("=== Generating Scatter Plot (True vs Predicted Power) ===")
    
    # 1. Բեռնում ենք տվյալները
    df1 = pd.read_csv("../Datasets/dataset_power.csv")
    df2 = pd.read_csv("../Datasets/dataset_power_alt.csv")
    df = pd.concat([df1, df2], ignore_index=True)
    
    preprocessor = joblib.load('./Model/preprocessor.joblib')
    model_path = "./Model/power_predictor_model.pth"
    
    # 2. Ֆիլտրում ենք (ճիշտ այնպես, ինչպես model.py-ում)
    df = df[df['cell_count'] > 0]
    df = df[df['total_power_uW'] >= 0.1]
    
    # Target-ը ստանում ենք իրական սանդղակով (uW)
    y_raw = df['total_power_uW'].values.astype(np.float32)
    y_log = np.log1p(y_raw)
    
    # Feature engineering
    df['v2_freq'] = (df['vdd'] ** 2) * df['clock_frequency_mhz']
    log_columns = [
        'cell_count', 'comb_cell_count', 'seq_cell_count', 
        'inv_count', 'buf_count', 'nand_count', 'nor_count', 'xor_count', 'mux_count', 'other_count',
        'total_area', 'num_nets', 'num_inputs', 'num_outputs'
    ]
    for col in log_columns:
        df[f"log_{col}"] = np.log1p(df[col])
        
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
    
    # 3. Տրանսֆորմացիա և Train/Val Split (ճիշտ նույն random_state-ով)
    X_processed = preprocessor.transform(df[features]).astype(np.float32)
    _, X_val, _, y_val_log = train_test_split(
        X_processed, y_log, test_size=0.2, random_state=42
    )
    
    y_val_true = np.expm1(y_val_log) # Իրական արժեքները uW-ով
    
    # 4. Բեռնում ենք մոդելը
    input_dim = X_processed.shape[1]
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = PowerNet(input_dim).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()
    
    # 5. Կատարում ենք կանխատեսումներ Validation Set-ի վրա
    X_val_tensor = torch.tensor(X_val).to(device)
    with torch.no_grad():
        preds_log = model(X_val_tensor).cpu().numpy().flatten()
        
    preds_uW = np.expm1(preds_log)
    preds_uW = np.clip(preds_uW, 0.01, None)
    
    # 6. Կառուցում ենք Scatter Plot-ը
    plt.figure(figsize=(8, 8))
    
    # Կետերը նկարում ենք կիսաթափանցիկ (alpha), որպեսզի խտությունը երևա
    plt.scatter(y_val_true, preds_uW, alpha=0.5, color='#1f77b4', edgecolors='none', s=15, label='Predictions')
    
    # Գծում ենք կատարյալ անկյունագիծը (y = x)
    max_val = max(y_val_true.max(), preds_uW.max())
    min_val = min(y_val_true.min(), preds_uW.min())
    plt.plot([min_val, max_val], [min_val, max_val], color='red', linestyle='--', linewidth=2, label='Perfect Fit (y = x)')
    
    # Ձևավորում
    plt.xlabel('True Power (uW)', fontsize=12)
    plt.ylabel('Predicted Power (uW)', fontsize=12)
    plt.title('Validation Set: Predicted vs. True Power', fontsize=14, fontweight='bold')
    
    # Մասշտաբը դարձնում ենք լոգարիթմական, որպեսզի փոքր և մեծ արժեքները հավասարաչափ լավ երևան
    plt.xscale('log')
    plt.yscale('log')
    
    plt.grid(True, which="both", linestyle="--", alpha=0.5)
    plt.legend(fontsize=11)
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()