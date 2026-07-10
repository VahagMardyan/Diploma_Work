import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.tree import plot_tree
import shap
import joblib

def main():
    model_path = './power_predictor_rf_new.joblib'
    csv_path = '../Dataset/dataset_power_new.csv'

    if not os.path.exists(model_path):
        print(f"Error: file {model_path} not found.")
        return

    if not os.path.exists(csv_path):
        print(f"Error: file {csv_path} not found.")
        return

    print(f"Loading model: {model_path}")
    model = joblib.load(model_path)
    
    df = pd.read_csv(csv_path)
    print(f"Data loaded. Row count: {len(df)}")

    df['vdd_squared'] = df['vdd'] ** 2
    df['freq_x_toggle'] = df['clock_frequency_mhz'] * df['toggle_rate']

    df_encoded = pd.get_dummies(df, columns=['process'], dtype=float)

    features = [
        'clock_frequency_mhz', 'toggle_rate', 'static_probability', 
        'cell_count', 'seq_cell_count', 'total_area', 'logic_depth', 
        'vdd', 'temperature', 'vdd_squared', 'freq_x_toggle',
        'process_SS', 'process_TT'
    ]

    X = df_encoded.reindex(columns=features, fill_value=0.0)
    y = df['dynamic_power']

    _, X_test, _, _ = train_test_split(X, y, test_size=0.2, random_state=42)

    print("\nPreparing graphs...")

    plt.figure(figsize=(10, 6))
    importances = model.feature_importances_
    feature_imp = pd.Series(importances, index=X.columns).sort_values(ascending=False)
    
    sns.barplot(x=feature_imp, y=feature_imp.index, palette="viridis")
    plt.title('Features Importance in Power Prediction (5nm RVT)', fontsize=14, fontweight='bold')
    plt.xlabel('Importance Score', fontsize=12)
    plt.ylabel('Features', fontsize=12)
    plt.grid(axis='x', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig('feature_importance.png', dpi=300)
    plt.close()
    print("-> Save: feature_importance.png")

    plt.figure(figsize=(24, 12))
    plot_tree(model.estimators_[0], 
              feature_names=X.columns, 
              max_depth=3, 
              filled=True, 
              rounded=True,
              fontsize=10)
    plt.title('Decision Tree Structure (Sample from Random Forest, Depth=3)', fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig('decision_tree.png', dpi=300)
    plt.close()
    print("-> Save: decision_tree.png")

    print("Calculating SHAP values...")
    explainer = shap.TreeExplainer(model)
    X_shap_sample = X_test.sample(min(200, len(X_test)), random_state=42)
    shap_values = explainer.shap_values(X_shap_sample)
    
    plt.figure(figsize=(10, 6))
    shap.summary_plot(shap_values, X_shap_sample, show=False)
    plt.title('SHAP Explainer - Feature Impact on Power Output', fontsize=14, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.savefig('shap_summary.png', dpi=300)
    plt.close()
    print("-> Save: shap_summary.png")

    print("\n[Done] All plots generated successfully!")

if __name__ == "__main__":
    main()