"""
Train the model
"""

import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.metrics import r2_score, mean_absolute_error
import joblib

# 1. Universal function for feature engineering (applies everywhere)
def engineer_features(df):
    df = df.copy() # To avoid damaging the original DataFrame
    df['v2_freq'] = (df['vdd'] ** 2) * df['clock_frequency_mhz'] # vdd² * f

    log_columns = [
        'cell_count', 'comb_cell_count', 'seq_cell_count', 
        'inv_count', 'buf_count', 'nand_count', 'nor_count', 'xor_count', 'mux_count', 'other_count',
        'total_area', 'num_nets', 'num_inputs', 'num_outputs'
    ]
    for col in log_columns:
        df[f"log_{col}"] = np.log1p(df[col])
        
    return df

# 2. Universal function to get feature names
def get_feature_names():
    num_features = [
        # Operational and physical
        'clock_frequency_mhz', 'toggle_rate', 'static_probability', 'vdd', 'temperature', 'v2_freq',
        # Logarithmic quantities (dividing elements by type)
        'log_cell_count', 'log_comb_cell_count', 'log_seq_cell_count',
        'log_inv_count', 'log_buf_count', 'log_nand_count', 'log_nor_count', 
        'log_xor_count', 'log_mux_count', 'log_other_count',
        'log_total_area', 'log_num_nets', 'log_num_inputs', 'log_num_outputs',
        # Topology, load and signals
        'avg_cell_area', 'max_fanout', 'avg_fanout', 'avg_fanin',
        'logic_depth', 'depth_mean', 'depth_std', 'depth_max',
        'avg_net_toggle', 'toggle_attenuation',
        # Timing arrows and delay
        'critical_path_delay', 'wns', 'tns'
    ]
    cat_features = ['process', 'pvt_corner']
    features = num_features + cat_features
    return features, num_features, cat_features

# 3. Function to get validation data (for evaluate.py)
def load_and_preprocess_val_data(data_path1="../Datasets/dataset_power.csv", 
                                 data_path2="../Datasets/dataset_power_alt.csv", 
                                 preprocessor_path="./Model/preprocessor.joblib"):
    
    print("Loading datasets for evaluation...")
    df1 = pd.read_csv(data_path1)
    df2 = pd.read_csv(data_path2)
    df = pd.concat([df1, df2], ignore_index=True)

    df = df[df['cell_count'] > 0]
    df = df[df['total_power_uW'] >= 0.1]

    y_raw = df['total_power_uW'].values.astype(np.float32)
    y_log = np.log1p(y_raw)

    df = engineer_features(df)
    features, _, _ = get_feature_names()

    print("Loading preprocessor...")
    preprocessor = joblib.load(preprocessor_path)
    X_processed = preprocessor.transform(df[features]).astype(np.float32)
    input_dim = X_processed.shape[1]

    _, X_val, _, y_val = train_test_split(
        X_processed, y_log, test_size=0.2, random_state=42
    )
    y_val_true = np.expm1(y_val)
    return X_val, y_val_true, input_dim


# Neural Network Architecture
class PowerNet(nn.Module):
    def __init__(self, input_dim):
        super(PowerNet, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.08), 
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )
    def forward(self, x):
        return self.net(x)

TARGET_CONFIGS = {
    "dynamic_power_uW": "./Model/dynamic_power_predictor_model.pth",
    "leakage_power_uW": "./Model/leakage_power_predictor_model.pth",
}

_LEGACY_TOTAL_POWER_WEIGHT_PATH = "./Model/power_predictor_model.pth"


def _load_training_dataframe():
    """Load, concatenate, and filter the raw datasets shared by every target."""
    print("Loading datasets...")
    df1 = pd.read_csv("../Datasets/dataset_power.csv")
    df2 = pd.read_csv("../Datasets/dataset_power_alt.csv")
    df = pd.concat([df1, df2], ignore_index=True)

    df = df[df['cell_count'] > 0]
    df = df[df['total_power_uW'] >= 0.1]
    return df.reset_index(drop=True)


def _fit_preprocessor(df):
    """Fit the shared ColumnTransformer once. Inputs don't depend on the
    target column, so the same fitted preprocessor is valid for every
    target we train against."""
    df = engineer_features(df)
    features, num_features, cat_features = get_feature_names()

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), num_features),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), cat_features)
        ])

    X_processed = preprocessor.fit_transform(df[features]).astype(np.float32)
    return df, preprocessor, X_processed


def train_single_target(X_processed, df, target_column, weight_path, device,
                         epochs=60, train_idx=None, val_idx=None):
    """Train a PowerNet to predict `target_column` (log1p-scaled) and save
    its weights to `weight_path`. If train_idx/val_idx are given, that split
    is reused instead of computing a new random split, so results across
    multiple targets stay comparable row-for-row."""
    print(f"\n{'='*50}")
    print(f"Training target: {target_column}")
    print(f"{'='*50}")

    y_raw = df[target_column].values.astype(np.float32)
    y_log = np.log1p(y_raw)
    input_dim = X_processed.shape[1]

    if train_idx is None or val_idx is None:
        train_idx, val_idx = train_test_split(
            np.arange(len(df)), test_size=0.2, random_state=42
        )

    X_train, X_val = X_processed[train_idx], X_processed[val_idx]
    y_train, y_val = y_log[train_idx], y_log[val_idx]
    y_val_true = np.expm1(y_val)

    train_dataset = TensorDataset(torch.tensor(X_train), torch.tensor(y_train).unsqueeze(1))
    train_loader = DataLoader(train_dataset, batch_size=2048, shuffle=True)

    model = PowerNet(input_dim).to(device)
    criterion = nn.MSELoss()
    optimizer = optim.AdamW(model.parameters(), lr=0.003, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    print(f"Training Neural Network ({epochs} Epochs with Scheduler)...")
    model.train()
    for epoch in range(epochs):
        epoch_loss = 0
        for batch_X, batch_y in train_loader:
            batch_X, batch_y = batch_X.to(device), batch_y.to(device)

            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()

        scheduler.step()

        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"Epoch {epoch+1}/{epochs} - Loss: {epoch_loss/len(train_loader):.5f} - LR: {scheduler.get_last_lr()[0]:.5f}")

    model.eval()
    with torch.no_grad():
        X_val_tensor = torch.tensor(X_val).to(device)
        preds_log = model(X_val_tensor).cpu().numpy().flatten()

    preds_uW = np.expm1(preds_log)
    preds_uW = np.clip(preds_uW, 0.01, None)

    mae = mean_absolute_error(y_val_true, preds_uW)
    r2 = r2_score(y_val_true, preds_uW)

    mask = y_val_true > 0.1
    mape_stable = np.mean(np.abs((y_val_true[mask] - preds_uW[mask]) / y_val_true[mask])) * 100

    torch.save(model.state_dict(), weight_path)
    print(f"Model weights saved to '{weight_path}'")

    print(f"\nEVALUATION RESULTS for {target_column} (Non-Log Scale uW):")
    print(f"MAE:        {mae:.4f} uW")
    print(f"R2 Score:   {r2:.4f}")
    print(f"Stable MAPE: {mape_stable:.2f}%")

    return {"target": target_column, "mae": mae, "r2": r2, "mape_stable": mape_stable}


def train_model():
    """Backwards-compatible single-target entry point: trains only the
    original total_power_uW model."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    df = _load_training_dataframe()
    df, preprocessor, X_processed = _fit_preprocessor(df)
    print(f"Input Dimension (Features count): {X_processed.shape[1]}")

    train_single_target(
        X_processed, df, "total_power_uW", _LEGACY_TOTAL_POWER_WEIGHT_PATH, device
    )

    PREPROCESSOR_PATH = "./Model/preprocessor.joblib"
    joblib.dump(preprocessor, PREPROCESSOR_PATH)
    print(f"Preprocessor saved to '{PREPROCESSOR_PATH}'")


def train_all_models(epochs=60):
    """Trains one PowerNet per entry in TARGET_CONFIGS (total, dynamic,
    leakage power), reusing a single fitted preprocessor and a single
    train/val split across all three for a fair, comparable evaluation."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    df = _load_training_dataframe()
    df, preprocessor, X_processed = _fit_preprocessor(df)
    print(f"Input Dimension (Features count): {X_processed.shape[1]}")

    train_idx, val_idx = train_test_split(
        np.arange(len(df)), test_size=0.2, random_state=42
    )

    results = []
    for target_column, weight_path in TARGET_CONFIGS.items():
        metrics = train_single_target(
            X_processed, df, target_column, weight_path, device,
            epochs=epochs, train_idx=train_idx, val_idx=val_idx,
        )
        results.append(metrics)

    PREPROCESSOR_PATH = "./Model/preprocessor.joblib"
    joblib.dump(preprocessor, PREPROCESSOR_PATH)
    print(f"\nPreprocessor saved to '{PREPROCESSOR_PATH}' (shared by all targets)")

    print("\n" + "=" * 50)
    print("SUMMARY (all targets)")
    print("=" * 50)
    for r in results:
        print(f"{r['target']:<18} MAE: {r['mae']:.4f} uW | R2: {r['r2']:.4f} | MAPE: {r['mape_stable']:.2f}%")

    return results


if __name__ == "__main__":
    train_all_models()