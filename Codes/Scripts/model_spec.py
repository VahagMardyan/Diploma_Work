import numpy as np
import torch
import matplotlib.pyplot as plt
import shap
from sklearn.metrics import r2_score, mean_absolute_error
from model import PowerNet, load_and_preprocess_val_data, get_feature_names

def evaluate_saved_model():
    X_val, y_val_true, input_dim = load_and_preprocess_val_data()

    print("Loading trained model weights...")
    model = PowerNet(input_dim)
    model.load_state_dict(torch.load("./Model/power_predictor_model.pth"))
    model.eval()

    print("Calculating metrics...")
    with torch.no_grad():
        X_val_tensor = torch.tensor(X_val)
        preds_log = model(X_val_tensor).numpy().flatten()

    preds_uW = np.expm1(preds_log)
    preds_uW = np.clip(preds_uW, 0.01, None)

    mae = mean_absolute_error(y_val_true, preds_uW)
    r2 = r2_score(y_val_true, preds_uW)

    mask = y_val_true > 0.1
    mape_stable = np.mean(np.abs((y_val_true[mask] - preds_uW[mask]) / y_val_true[mask])) * 100

    print("\n" + "="*50)
    print("LOADED MODEL EVALUATION RESULTS:")
    print(f"MAE:         {mae:.4f} uW")
    print(f"R2 Score:    {r2:.4f}")
    print(f"Stable MAPE: {mape_stable:.2f}%")
    print("="*50)

    print("\nStarting SHAP analysis...")
    
    features, _, _ = get_feature_names()
    
    if len(features) < input_dim:
        extended_features = features + [f"Feature_{i}" for i in range(len(features), input_dim)]
    else:
        extended_features = features[:input_dim]

    background = torch.tensor(X_val[:100], dtype=torch.float32)
    test_samples = torch.tensor(X_val[:500], dtype=torch.float32) 
    
    def model_predict(x_numpy):
        x_tensor = torch.tensor(x_numpy, dtype=torch.float32)
        with torch.no_grad():
            return model(x_tensor).numpy()

    explainer = shap.Explainer(model_predict, background.numpy())
    shap_values = explainer(test_samples.numpy())

    shap_values.feature_names = extended_features

    plt.figure(figsize=(10, 8))
    shap.plots.bar(shap_values, max_display=20, show=False)
    plt.title("SHAP Feature Importance (Top 20)", fontsize=14, fontweight='bold', pad=20)
    plt.tight_layout()
    FEATURE_IMPORTANCE_PATH = "../Images/shap_feature_importance.png"
    plt.savefig(FEATURE_IMPORTANCE_PATH, dpi=300)
    plt.close()
    print(f"Saved: {FEATURE_IMPORTANCE_PATH}")

    plt.figure(figsize=(10, 8))
    shap.summary_plot(shap_values.values, test_samples.numpy(), feature_names=extended_features, max_display=20, show=False)
    plt.title("SHAP Summary Plot (Feature Impact)", fontsize=14, fontweight='bold', pad=20)
    plt.tight_layout()
    SHAP_PATH = "../Images/shap_summary_plot.png"
    plt.savefig(SHAP_PATH, dpi=300)
    plt.close()
    print(f"Saved: {SHAP_PATH}")

if __name__ == "__main__":
    evaluate_saved_model()

