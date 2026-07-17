"""
Histograms (Real Power vs Predicted Power)
"""

import pandas as pd
import numpy as np
import torch
import joblib
import matplotlib.pyplot as plt
from model import PowerNet, engineer_features, get_feature_names

def main():
    print("=== Visualizing Predictions (Real vs Predicted) ===")
    
    df = pd.read_csv('../Datasets/dataset_power_alt.csv')
    preprocessor = joblib.load('./Model/preprocessor.joblib')
    model_path = "./Model/power_predictor_model.pth"
    
    df = df[df['cell_count'] > 0]
    df = df[df['total_power_uW'] >= 0.1]
    
    df = engineer_features(df)
    features, _, _ = get_feature_names()
    
    sample_processed = preprocessor.transform(df[features].iloc[[0]])
    input_dim = sample_processed.shape[1]
    print(f"Detected Model Input Dimension: {input_dim}")
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = PowerNet(input_dim).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()
    
    sample_indices = [250, 1500, 5000]
    results = []
    
    print("\nCalculating predictions for chosen samples...")
    for idx in sample_indices:
        if idx >= len(df):
            continue
            
        row = df.iloc[[idx]]
        real_power = row['total_power_uW'].values[0]
        
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
    
    for i, row in plot_df.iterrows():
        plt.text(i - width/2, row['Real Power'] + 1, f"{row['Real Power']:.1f}", ha='center', va='bottom', fontsize=9)
        plt.text(i + width/2, row['Predicted Power'] + 1, f"{row['Predicted Power']:.1f}", ha='center', va='bottom', fontsize=9)
        
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()

