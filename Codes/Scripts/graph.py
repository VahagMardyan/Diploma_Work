import pandas as pd
import numpy as np
import torch
import joblib
import matplotlib.pyplot as plt

# Մաքուր import առանց մարզումը նորից ակտիվացնելու
from model import PowerNet

def main():
    print("=== Visualizing Predictions (Real vs Predicted) ===")
    
    # 1. Բեռնում ենք անհրաժեշտ ֆայլերը
    df = pd.read_csv('../Datasets/dataset_power_alt.csv')
    preprocessor = joblib.load('./Model/preprocessor.joblib')
    model_path = "./Model/power_predictor_model.pth"
    
    # 2. Ֆիլտրում ենք տվյալները (ինչպես model.py-ում է)
    df = df[df['cell_count'] > 0]
    df = df[df['total_power_uW'] >= 0.1]
    
    # 3. Դինամիկ կերպով որոշում ենք input_dim-ը preprocessor-ի միջոցով
    # Դրա համար վերցնում ենք մեկ տող, կատարում feature engineering և transform
    sample_row = df.iloc[[0]].copy()
    
    sample_row['v2_freq'] = (sample_row['vdd'] ** 2) * sample_row['clock_frequency_mhz']
    log_columns = [
        'cell_count', 'comb_cell_count', 'seq_cell_count', 
        'inv_count', 'buf_count', 'nand_count', 'nor_count', 'xor_count', 'mux_count', 'other_count',
        'total_area', 'num_nets', 'num_inputs', 'num_outputs'
    ]
    for col in log_columns:
        sample_row[f"log_{col}"] = np.log1p(sample_row[col])
        
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
    
    # Ստանում ենք իրական չափը
    sample_processed = preprocessor.transform(sample_row[features])
    input_dim = sample_processed.shape[1]
    print(f"Detected Model Input Dimension: {input_dim}")
    
    # 4. Բեռնում ենք PyTorch մոդելը
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = PowerNet(input_dim).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()
    
    # 5. Ընտրում ենք ցուցադրական տողեր տարբեր տիրույթներից (ինդեքսներ)
    sample_indices = [250, 1500, 5000]
    results = []
    
    print("\nCalculating predictions for chosen samples...")
    for idx in sample_indices:
        if idx >= len(df):
            continue
            
        row = df.iloc[[idx]].copy()
        real_power = row['total_power_uW'].values[0]
        
        # Feature Engineering տվյալ տողի համար
        row['v2_freq'] = (row['vdd'] ** 2) * row['clock_frequency_mhz']
        for col in log_columns:
            row[f"log_{col}"] = np.log1p(row[col])
            
        # Տրանսֆորմացիա և Կանխատեսում (Inference)
        X_row = preprocessor.transform(row[features]).astype(np.float32)
        X_tensor = torch.tensor(X_row).to(device)
        
        with torch.no_grad():
            pred_log = model(X_tensor).item()
            pred_power = np.expm1(pred_log)
            
        results.append({
            'Index': f'Sample {idx}',
            'Real Power': real_power,
            'Predicted Power': pred_power
        })
        print(f"Sample {idx} -> Real: {real_power:.4f} uW | Pred: {pred_power:.4f} uW")
        
    # 6. Կառուցում ենք գրաֆիկը
    plot_df = pd.DataFrame(results)
    
    plt.figure(figsize=(9, 6))
    x = np.arange(len(plot_df))
    width = 0.35
    
    plt.bar(x - width/2, plot_df['Real Power'], width, label='Real Power', color='#2ca02c')
    plt.bar(x + width/2, plot_df['Predicted Power'], width, label='Predicted Power', color='#ff7f0e')
    
    plt.ylabel('Power (uW)', fontsize=12)
    plt.title('Validation: Real vs Predicted Power (Early Design Stage)', fontsize=14, fontweight='bold')
    plt.xticks(x, plot_df['Index'])
    plt.legend(fontsize=11)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    
    # Արժեքները սյուների վրա գրելու համար
    for i, row in plot_df.iterrows():
        plt.text(i - width/2, row['Real Power'] + 1, f"{row['Real Power']:.1f}", ha='center', va='bottom', fontsize=9)
        plt.text(i + width/2, row['Predicted Power'] + 1, f"{row['Predicted Power']:.1f}", ha='center', va='bottom', fontsize=9)
        
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()