import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
import torch

from model import (
    DynamicResNet,
    engineer_domain_features,
    get_dynamic_features,
    get_leakage_features,
    load_data,
)


def run_shap_analysis():
    print("Loading model and preprocessor for SHAP analysis...")

    device = torch.device("cpu")  # CPU is recommended for SHAP explainers

    # 1. Load saved preprocessor & dynamic model
    preprocessor = joblib.load("./Model/preprocessor_dynamic.joblib")

    # Fetch feature names
    features, num_features, cat_features = get_dynamic_features()

    # Get one-hot encoded feature names for exact plotting
    cat_encoder = preprocessor.named_transformers_["cat"]
    encoded_cat_names = list(cat_encoder.get_feature_names_out(cat_features))
    all_feature_names = num_features + encoded_cat_names

    # 2. Instantiate and load model weights
    sample_dim = len(all_feature_names)
    model = DynamicResNet(input_dim=sample_dim).to(device)
    model.load_state_dict(torch.load("./Model/dynamic_power_predictor_model.pth", map_location=device))
    model.eval()

    # 3. Load dataset
    df = load_data()
    df_eng = engineer_domain_features(df)

    # Transform features
    X_trans = preprocessor.transform(df_eng[features]).astype(np.float32)

    # Sample background & evaluation instances
    np.random.seed(42)
    bg_indices = np.random.choice(len(X_trans), size=100, replace=False)
    eval_indices = np.random.choice(len(X_trans), size=200, replace=False)

    background_data = X_trans[bg_indices]
    eval_data = X_trans[eval_indices]

    # Prediction wrapper for SHAP
    def predict_log_power(x_numpy):
        x_tensor = torch.tensor(x_numpy, dtype=torch.float32).to(device)
        with torch.no_grad():
            return model(x_tensor).cpu().numpy().flatten()

    print("Calculating SHAP values (KernelExplainer)...")
    background_summary = shap.kmeans(background_data, 10)
    explainer = shap.KernelExplainer(predict_log_power, background_summary)
    shap_values = explainer.shap_values(eval_data)

    # 4. Generate & Save Plots
    print("Generating SHAP summary plots...")

    # Plot 1: Bar Plot (Global Importance)
    plt.figure(figsize=(12, 8))
    shap.summary_plot(
        shap_values,
        eval_data,
        feature_names=all_feature_names,
        plot_type="bar",
        show=False,
    )
    plt.title("Global Feature Importance (Dynamic Power ResNet)", fontsize=14)
    plt.tight_layout()
    plt.savefig("shap_dynamic_feature_importance_bar.png", dpi=300)
    plt.close()

    # Plot 2: Beeswarm Plot (Feature Impact Distribution)
    plt.figure(figsize=(12, 8))
    shap.summary_plot(
        shap_values,
        eval_data,
        feature_names=all_feature_names,
        show=False,
    )
    plt.tight_layout()
    plt.savefig("shap_dynamic_summary_beeswarm.png", dpi=300)
    plt.close()

    print("Successfully generated 'shap_dynamic_feature_importance_bar.png' and 'shap_dynamic_summary_beeswarm.png'.")


if __name__ == "__main__":
    run_shap_analysis()