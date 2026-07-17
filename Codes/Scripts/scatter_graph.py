import numpy as np
import torch
import matplotlib.pyplot as plt
from model import PowerNet, load_and_preprocess_val_data

def main():
    print("=== Generating Scatter Plot (True vs Predicted Power) ===")
    
    X_val, y_val_true, input_dim = load_and_preprocess_val_data()
    model_path = "./Model/power_predictor_model.pth"
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = PowerNet(input_dim).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()
    
    X_val_tensor = torch.tensor(X_val).to(device)
    with torch.no_grad():
        preds_log = model(X_val_tensor).cpu().numpy().flatten()
        
    preds_uW = np.expm1(preds_log)
    preds_uW = np.clip(preds_uW, 0.01, None)
    
    plt.figure(figsize=(8, 8))
    
    plt.scatter(y_val_true, preds_uW, alpha=0.5, color='#1f77b4', edgecolors='none', s=15, label='Predictions')
    
    max_val = max(y_val_true.max(), preds_uW.max())
    min_val = min(y_val_true.min(), preds_uW.min())
    plt.plot([min_val, max_val], [min_val, max_val], color='red', linestyle='--', linewidth=2, label='Perfect Fit (y = x)')
    
    plt.xlabel('True Power (uW)', fontsize=12)
    plt.ylabel('Predicted Power (uW)', fontsize=12)
    plt.title('Validation Set: Predicted vs. True Power', fontsize=14, fontweight='bold')
    
    plt.xscale('log')
    plt.yscale('log')
    
    plt.grid(True, which="both", linestyle="--", alpha=0.5)
    plt.legend(fontsize=11)
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()