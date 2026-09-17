# shap_analysis.py
import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
import os
import sys
import torch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from Scripts.model import (
    DynamicResNet,
    LeakageResNet,
    engineer_domain_features,
    get_dynamic_features,
    get_leakage_features,
    load_data,
)

CONFIGS = {
    "dynamic": {
        "title": "Dynamic Power ResNet",
        "preprocessor_path": "./Model/preprocessor_dynamic.joblib",
        "model_path": "./Model/dynamic_power_predictor_model.pth",
        "feature_fn": get_dynamic_features,
        "model_cls": DynamicResNet,
        "output_prefix": "shap_dynamic",
    },
    "leakage": {
        "title": "Leakage Power ResNet",
        "preprocessor_path": "./Model/preprocessor_leakage.joblib",
        "model_path": "./Model/leakage_power_predictor_model.pth",
        "feature_fn": get_leakage_features,
        "model_cls": LeakageResNet,
        "output_prefix": "shap_leakage",
    },
}


def run_shap_analysis(mode="dynamic"):
    cfg = CONFIGS[mode]
    print(f"Loading model and preprocessor for {mode.upper()} SHAP analysis...")

    device = torch.device("cpu")

    # 1. Load saved preprocessor & features
    preprocessor = joblib.load(cfg["preprocessor_path"])
    features, num_features, cat_features = cfg["feature_fn"]()

    cat_encoder = preprocessor.named_transformers_["cat"]
    encoded_cat_names = list(cat_encoder.get_feature_names_out(cat_features))
    all_feature_names = num_features + encoded_cat_names

    # 2. Load model
    sample_dim = len(all_feature_names)
    model = cfg["model_cls"](input_dim=sample_dim).to(device)
    model.load_state_dict(
        torch.load(cfg["model_path"], map_location=device)
    )
    model.eval()

    # 3. Load dataset & Transform
    df = load_data()
    df_eng = engineer_domain_features(df)
    X_trans = preprocessor.transform(df_eng[features]).astype(np.float32)

    np.random.seed(42)
    bg_indices = np.random.choice(len(X_trans), size=100, replace=False)
    eval_indices = np.random.choice(len(X_trans), size=200, replace=False)

    background_data = X_trans[bg_indices]
    eval_data = X_trans[eval_indices]

    def predict_log_power(x_numpy):
        x_tensor = torch.tensor(x_numpy, dtype=torch.float32).to(device)
        with torch.no_grad():
            return model(x_tensor).cpu().numpy().flatten()

    print(f"Calculating SHAP values for {mode.capitalize()} Power...")
    background_summary = shap.kmeans(background_data, 10)
    explainer = shap.KernelExplainer(predict_log_power, background_summary)
    shap_values = explainer.shap_values(eval_data)

    # 4. Generate & Save Plots
    print("Generating SHAP plots...")

    # Bar Plot
    plt.figure(figsize=(12, 8))
    shap.summary_plot(
        shap_values,
        eval_data,
        feature_names=all_feature_names,
        plot_type="bar",
        show=False,
    )
    plt.title(f"Global Feature Importance ({cfg['title']})", fontsize=14)
    plt.tight_layout()
    bar_file = f"{cfg['output_prefix']}_feature_importance_bar.png"
    plt.savefig(bar_file, dpi=300)
    plt.close()

    # Beeswarm Plot
    plt.figure(figsize=(12, 8))
    shap.summary_plot(
        shap_values,
        eval_data,
        feature_names=all_feature_names,
        show=False,
    )
    plt.tight_layout()
    beeswarm_file = f"{cfg['output_prefix']}_summary_beeswarm.png"
    plt.savefig(beeswarm_file, dpi=300)
    plt.close()

    print(f"Successfully generated '{bar_file}' and '{beeswarm_file}'.")


if __name__ == "__main__":
    run_shap_analysis(mode="dynamic")
    # run_shap_analysis(mode="leakage")