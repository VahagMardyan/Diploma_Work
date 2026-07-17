# Early-Stage Total Power Prediction for Digital ICs using Machine Learning & Deep Learning

This repository contains the source code and datasets for a Bachelor's Graduation Thesis titled: **"Development of software for predicting power consumption in the early stage of design of digital integrated circuits"**.

The project implements an end-to-end machine learning and deep learning pipeline to predict the **total power consumption (in microwatts - uW)** of digital circuits. Predictions are based on early-stage physical, architectural, topological, and environmental parameters across FinFET technology nodes.

## Key Features

* **Advanced Neural Network Architecture:** Features **PowerNet**, a deep Multi-Layer Perceptron (MLP) built in PyTorch with custom log-scale data preprocessing to handle power consumption ranges spanning multiple orders of magnitude (from $0.1$ uW to over $1000$ uW).
* **Multi-Model Evaluation:** Compares traditional Linear Regression, tree-based ensembles (XGBoost, Random Forest), and deep neural networks (PyTorch MLP).
* **Smart Preprocessing & Feature Engineering:** Custom feature engineering (e.g., $V_{\text{dd}}^2 \cdot f$ dynamic scaling factor) and logarithmic feature transformation to capture non-linear physical relationships.
* **GPU Acceleration & Portability:** Native CUDA support with automatic CPU fallback.
* **Modular Pipeline Architecture:** Clean separation of model architecture, training routines, and visualization helpers to prevent unnecessary model retraining when running predictions or plotting results.

---

## What Power We Predict (Target & Scope)

The model predicts the **Total Power Consumption ($P_{\text{total}}$ in uW)** of the digital integrated circuit at the early design stage, which mathematically represents the sum of both dynamic and static power:

$$
P_{\text{total}} = P_{\text{dynamic}} + P_{\text{static}}
$$

Using architectural properties (cell counts, gate types, area, number of nets), physical parameters (logic depth, fanout), operational features (clock frequency, toggle rate, static probability, supply voltage $V_{\text{dd}}$), and PVT environmental variables (process, temperature), the pipeline acts as a high-speed, early-stage replacement for heavy EDA power estimation tools.

---

## Performance Summary

The evaluation results on completely unseen validation/test split configurations (including highly non-linear low-power and high-power zones):

| Model                       | Architecture Details                         |    R² Score    |     Stable MAPE (%)     |          Target Scale Handling          |
| :-------------------------- | :------------------------------------------- | :-------------: | :----------------------: | :--------------------------------------: |
| **Linear Regression** | Standard Linear Model                        |      ~0.00      |          >5000%          |       Poor (struggles with range)       |
| **XGBoost**           | Gradient Boosted Trees                       |      ~0.45      |         ~132.02%         |                 Moderate                 |
| **Random Forest**     | Tree Ensemble                                |      ~0.95      |          ~3.21%          |                Very Good                |
| **PowerNet (MLP)**    | **Deep PyTorch MLP (256-128-64-32-1)** | **>0.99** | **~2.10% - 2.50%** | **Excellent (0.1 uW to 1000+ uW)** |

> **Conclusion:** The PyTorch-based **PowerNet** neural network is selected as the production model due to its exceptional generalization capabilities across different design scales, achieving **near-perfect physical alignment ($R^2 > 0.99$)**.

---

## Repository Structure

```text
.
├── Datasets/                          # Raw and processed CSV power data pairs
│   ├── dataset_power.csv              # Initial design pairs (Dataset Part 1)
│   └── dataset_power_alt.csv          # New iteration design pairs (Dataset Part 2)
├── Model/                             # Saved model binaries & preprocessors (Gitignored)
│   ├── power_predictor_model.pth      # PyTorch model weights
│   └── preprocessor.joblib            # Fitted Scikit-Learn ColumnTransformer
├── Scripts/                           # Core ML pipeline logic
│   ├── model.py                       # Main PyTorch MLP training, evaluation, and saving script
│   ├── graph.py                       # Bar chart generator (comparing Real vs Predicted samples)
│   └── scatter_graph.py               # Scientific Scatter Plot (y = x fit in logarithmic scale)
├── Verilog/                           # RTL hardware designs used for data collection
│   ├── Verilog-Designs/               # Categorized RTL source files
├── environment.yml                    # Conda environment definition file
└── README.md                          # Project documentation
```

---

## Installation & Setup

### Option 1: Using Conda (Recommended)

To recreate the exact isolated environment with PyTorch, Scikit-Learn, CUDA support, and all visual tools:

```bash
conda env create -f environment.yml
conda activate <environment_name>
```

### Option 2: Using Pip

```bash
pip install torch pandas numpy scikit-learn joblib matplotlib
```

---

## How to Run

### 1. Train and Save the Model

To run the data preprocessing, configure the feature transformer, train the PyTorch MLP (with cosine annealing learning rate scheduler), and save the trained weights:

```bash
python Scripts/model.py
```

### 2. Compare Selected Samples (Bar Chart)

To quickly visualize the prediction accuracy on selected circuits representing different power scale zones (e.g., low-power vs high-power cells):

```bash
python Scripts/graph.py

```

### 3. Generate Scientific Validation Plot (Scatter Plot)

To generate a professional logarithmic $y=x$ scatter plot showing prediction consistency over the entire validation dataset:

```bash
python Scripts/scatter_graph.py

```

---

## License & Usage

This is a private repository developed as part of a Bachelor's Diploma Work Project at the **National Polytechnic University of Armenia** in collaboration with **Synopsys Armenia**. All rights reserved.
