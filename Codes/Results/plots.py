import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Design & Style Settings
sns.set_theme(style="whitegrid")
plt.rcParams.update({'font.size': 11, 'figure.autolayout': True})

def generate_power_plots(csv_filepath, output_image_name='power_analysis_plots_alt.png'):
    df = pd.read_csv(csv_filepath)

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # 1. Error Distribution
    ax1 = axes[0]
    sns.histplot(df['error_total_power_uW_%'], kde=True, color='#3B82F6', bins=30, ax=ax1, stat="density", alpha=0.4)
    ax1.axvline(15, color='#EF4444', linestyle='--', linewidth=2, label='15% Threshold')
    ax1.axvline(df['error_total_power_uW_%'].median(), color='#10B981', linestyle='-', linewidth=2, 
                label=f'Median ({df["error_total_power_uW_%"].median():.2f}%)')
    ax1.set_title('Distribution of Total Power Relative Error (%)', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Relative Error (%)')
    ax1.set_ylabel('Density')
    ax1.legend()

    # 2. Actual vs Predicted Scatter
    ax2 = axes[1]
    ax2.scatter(df['total_power_uW'], df['predicted_total_power_uW'], alpha=0.4, color='#8B5CF6', edgecolors='none', s=25)
    max_val = max(df['total_power_uW'].max(), df['predicted_total_power_uW'].max())
    ax2.plot([0, max_val], [0, max_val], color='#EF4444', linestyle='--', linewidth=1.8, label='Ideal (y = x)')
    ax2.set_title('Actual vs Predicted Total Power (uW)', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Actual Total Power (uW)')
    ax2.set_ylabel('Predicted Total Power (uW)')
    ax2.legend()

    # 3. Relative Error vs Actual Power
    ax3 = axes[2]
    ax3.scatter(df['total_power_uW'], df['error_total_power_uW_%'], alpha=0.4, color='#F59E0B', s=25)
    ax3.axhline(15, color='#EF4444', linestyle='--', label='15% Error Threshold')
    ax3.set_title('Relative Error vs Actual Total Power', fontsize=12, fontweight='bold')
    ax3.set_xlabel('Actual Total Power (uW)')
    ax3.set_ylabel('Relative Error (%)')
    ax3.legend()

    plt.tight_layout()
    plt.savefig(output_image_name, dpi=300)
    print(f"[+] Plots successfully generated and saved as '{output_image_name}'")

if __name__ == "__main__":
    generate_power_plots('prediction_results_with_errors_alt.csv')