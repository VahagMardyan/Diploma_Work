### Early-Stage Dynamic Power Prediction for Digital ICs using Machine Learning

This repository contains the source code and datasets for a Bachelor's Graduation Thesis titled: **"Development of software for predicting power consumption in the early stage of design of digital integrated circuits"**.

The project implements an end-to-end Machine Learning pipeline to predict the dynamic power consumption of digital circuits based on early-stage architectural, physical, and environmental parameters (FinFET 14nm/5nm technology nodes).

## Key Features

* **Multi-Model Evaluation:** Compares Linear Regression, XGBoost, and Random Forest Regressors.
* **Intra-Design Generalization:** Evaluated using a strict **70/15/15** split (Train/Validation/Test).
* **Robustness:** Validated using **5-Fold Cross-Validation** on the training subset to prevent overfitting.
* **Explainable AI (XAI):** Integrated with **SHAP (Shapley Additive Explanations)** to interpret and physically validate feature importance based on IC design physics.

---

## Performance Summary

| Model                       | 5-Fold CV Mean MAPE (%) | Hold-out Validation MAPE (%) | Unseen Test MAPE (%) | Latency per Sample (ms) |
| :-------------------------- | :---------------------: | :--------------------------: | :------------------: | :---------------------: |
| **Linear Regression** |        5267.27%        |           5712.11%           |       5681.10%       |   **0.000096**   |
| **Random Forest**     |     **4.14%**     |       **3.26%**       |   **3.21%**   |        0.013968        |
| **XGBoost**           |         124.38%         |           134.35%           |       132.02%       |        0.000738        |

> 🏆 **Conclusion:** The **Random Forest Regressor** is chosen as the best production model, achieving **~96.8% accuracy (3.21% MAPE)** on completely unseen test configurations.

---

## Repository Structure

```text
.
├── Codes/
│   ├── Dataset/                       # Raw and processed CSV power data pairs
│   │   ├── dataset_new_pairs/         # New iteration design pairs (Dataset Part 2)
│   │   ├── dataset_old_pairs/         # Initial design pairs (Dataset Part 1)
│   │   └── dataset_with_split_labels.csv
│   ├── Images/                        # Saved visualization plots & evaluation results
│   │   ├── result_saed05rvt_*.png     # PVT corner specific power plots
│   │   └── shap_summary.png           # Generated SHAP Feature Impact chart
│   └── Scripts/                       # Core ML pipeline logic
│       ├── Models/                    # [Gitignored] Trained model binaries (.joblib)
│       ├── model.py                   # Main training, 5-Fold CV, and SHAP execution
│       ├── predict_power.py           # Production inference script
│       └── graph.py, visual.py        # Chart generation & visualization helpers
├── Verilog/                           # RTL hardware designs used for data collection
│   ├── Verilog-Design-Examples/       # Standard benchmark blocks (ALU, FIFOs, Counters)
│   ├── Verilog-Designs/               # Categorized RTL source files (Part 1, 2, 3)
│   └── Verilog_New_Designs/           # Additional validation circuits (Adders, Shifters)
├── Books/                             # [Gitignored] Reference literature & Synopsys user guides
├── environment.yml                    # Conda environment definition file
└── README.md                          # Project documentation
```

---

## Installation & Setup

### Option 1: Using Conda (Recommended)

To recreate the exact environment with all dependencies and Python versions:

```bash
conda env create -f environment.yml
conda activate <environment_name>
```

### Option 2: Using Pip

```bash
pip install -r requirements.txt
```

---

## How to Run

### 1. Train and Evaluate Models

To run the preprocessing, 5-fold cross-validation, final evaluation, and generate the SHAP graph:

```bash
python Scripts/model.py
```

### 2. Physical Interpretability (SHAP)

The model's decisions are interpreted using SHAP values. Features like `cell_count`, `logic_depth`, and `freq_x_toggle` exhibit strong physical alignment with the dynamic power equation ($P_{\text{dyn}} \propto C \cdot V_{\text{dd}}^2 \cdot f \cdot \alpha$).

The summary plot is automatically saved as `shap_summary.png`.

---

## License & Usage

This is a private repository developed as part of a Bachelor's Diploma Work Project at the **National Polytechnic University of Armenia** in collaboration with **Synopsys Armenia**. All rights reserved.
