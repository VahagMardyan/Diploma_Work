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

    # Only drop degenerate empty-circuit rows (cell_count == 0, which is
    # exactly the set of rows with total_power_uW == 0). Do NOT filter on
    # a total_power_uW magnitude threshold: that used to throw away every
    # low-power example (~5% of training rows, but 50%+ of some real-world
    # small-circuit test sets like the encoder design), leaving the model
    # with zero training signal below the old 0.1 uW cutoff.
    df = df[df['cell_count'] > 0]

    y_raw = df['total_power_uW'].values.astype(np.float32)
    y_log = np.log(y_raw)  # see train_single_target for why plain log, not log1p

    df = engineer_features(df)
    features, _, _ = get_feature_names()

    print("Loading preprocessor...")
    preprocessor = joblib.load(preprocessor_path)
    X_processed = preprocessor.transform(df[features]).astype(np.float32)
    input_dim = X_processed.shape[1]

    _, X_val, _, y_val = train_test_split(
        X_processed, y_log, test_size=0.2, random_state=42
    )
    y_val_true = np.exp(y_val)
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

    # Only drop degenerate empty-circuit rows (cell_count == 0, which is
    # exactly the set of rows with total_power_uW == 0). Do NOT filter on
    # a total_power_uW magnitude threshold: that used to throw away every
    # low-power example (~5% of training rows, but 50%+ of some real-world
    # small-circuit test sets like the encoder design), leaving the model
    # with zero training signal below the old 0.1 uW cutoff.
    df = df[df['cell_count'] > 0]
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
                         epochs=60, train_idx=None, val_idx=None, patience=10):
    """Train a PowerNet to predict `target_column` (log-scaled) and save
    its weights to `weight_path`. If train_idx/val_idx are given, that split
    is reused instead of computing a new random split, so results across
    multiple targets stay comparable row-for-row.

    Uses early stopping on validation loss: the checkpoint with the lowest
    validation loss is what actually gets saved to `weight_path`, not
    whatever the final epoch happens to produce. Training still runs the
    full `epochs` schedule (so the cosine LR decay completes normally),
    but if val loss hasn't improved for `patience` epochs in a row, it
    stops early instead of continuing to overfit."""
    print(f"\n{'='*50}")
    print(f"Training target: {target_column}")
    print(f"{'='*50}")

    y_raw = df[target_column].values.astype(np.float32)
    # Plain log, not log1p: both dynamic_power_uW and leakage_power_uW are
    # strictly positive here (guaranteed by the cell_count > 0 filter) and
    # span several orders of magnitude (leakage: ~2.4e-5 to ~471). log1p(x)
    # ~= x for x << 1, so it barely separates small values from each other,
    # starving the loss of gradient signal for the low end of the range and
    # producing huge relative error there. Plain log spreads every decade
    # evenly regardless of scale, matching what MAPE actually measures.
    y_log = np.log(y_raw)
    input_dim = X_processed.shape[1]

    if train_idx is None or val_idx is None:
        train_idx, val_idx = train_test_split(
            np.arange(len(df)), test_size=0.2, random_state=42
        )

    X_train, X_val = X_processed[train_idx], X_processed[val_idx]
    y_train, y_val = y_log[train_idx], y_log[val_idx]
    y_val_true = np.exp(y_val)

    train_dataset = TensorDataset(torch.tensor(X_train), torch.tensor(y_train).unsqueeze(1))
    train_loader = DataLoader(train_dataset, batch_size=2048, shuffle=True)

    X_val_tensor = torch.tensor(X_val).to(device)
    y_val_tensor = torch.tensor(y_val).unsqueeze(1).to(device)

    model = PowerNet(input_dim).to(device)
    criterion = nn.MSELoss()
    optimizer = optim.AdamW(model.parameters(), lr=0.003, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    best_val_loss = float("inf")
    best_epoch = -1
    best_state = None
    epochs_since_improvement = 0

    print(f"Training Neural Network ({epochs} Epochs with Scheduler, patience={patience})...")
    for epoch in range(epochs):
        model.train()
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

        model.eval()
        with torch.no_grad():
            val_loss = criterion(model(X_val_tensor), y_val_tensor).item()

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = epoch + 1
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
            epochs_since_improvement = 0
        else:
            epochs_since_improvement += 1

        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"Epoch {epoch+1}/{epochs} - Train Loss: {epoch_loss/len(train_loader):.5f} "
                  f"- Val Loss: {val_loss:.5f} (best: {best_val_loss:.5f} @ epoch {best_epoch}) "
                  f"- LR: {scheduler.get_last_lr()[0]:.5f}")

        if epochs_since_improvement >= patience:
            print(f"Early stopping at epoch {epoch+1} "
                  f"(no val improvement for {patience} epochs; best was epoch {best_epoch})")
            break

    # Restore the best-validation checkpoint, not whatever the loop ended on.
    model.load_state_dict(best_state)
    print(f"Restored best checkpoint from epoch {best_epoch} (val loss {best_val_loss:.5f})")

    model.eval()
    with torch.no_grad():
        preds_log = model(X_val_tensor).cpu().numpy().flatten()

    # exp() is positive by construction, so no floor/clip is needed here.
    # The old np.clip(..., 0.01, None) actively hurt small-value accuracy:
    # it silently overwrote any true prediction below 0.01 uW with 0.01,
    # which is exactly the region we're now trying to get right.
    preds_uW = np.exp(preds_log)

    mae = mean_absolute_error(y_val_true, preds_uW)
    r2 = r2_score(y_val_true, preds_uW)

    # Full-range MAPE (what real inference error will actually look like,
    # including low-power rows). A tiny epsilon guards only against exact
    # zeros, it does not hide the low-power region like the old > 0.1
    # mask used to.
    mape_full = np.mean(np.abs((y_val_true - preds_uW) / np.maximum(y_val_true, 1e-6))) * 100

    # Kept alongside as a secondary, less noisy diagnostic: MAPE restricted
    # to rows with non-negligible true power, where relative error isn't
    # dominated by near-zero denominators.
    mask = y_val_true > 0.1
    mape_stable = np.mean(np.abs((y_val_true[mask] - preds_uW[mask]) / y_val_true[mask])) * 100 if mask.any() else float("nan")

    low_mask = ~mask
    mape_low_power = np.mean(np.abs((y_val_true[low_mask] - preds_uW[low_mask]) / np.maximum(y_val_true[low_mask], 1e-6))) * 100 if low_mask.any() else float("nan")

    torch.save(model.state_dict(), weight_path)
    print(f"Model weights saved to '{weight_path}'")

    print(f"\nEVALUATION RESULTS for {target_column} (Non-Log Scale uW):")
    print(f"MAE:              {mae:.4f} uW")
    print(f"R2 Score:         {r2:.4f}")
    print(f"MAPE (full range):        {mape_full:.2f}%")
    print(f"MAPE (>0.1 uW, n={mask.sum()}):      {mape_stable:.2f}%")
    print(f"MAPE (<=0.1 uW, n={low_mask.sum()}):     {mape_low_power:.2f}%")

    return {"target": target_column, "mae": mae, "r2": r2, "mape_full": mape_full,
            "mape_stable": mape_stable, "mape_low_power": mape_low_power}


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


def train_all_models(epochs=60, patience=10):
    """Trains one PowerNet per entry in TARGET_CONFIGS (total, dynamic,
    leakage power), reusing a single fitted preprocessor and a single
    train/val split across all three for a fair, comparable evaluation.
    `patience` controls early stopping: training halts once val loss hasn't
    improved for that many consecutive epochs, and the checkpoint saved is
    the one with the best val loss seen, not the final epoch's weights."""
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
            epochs=epochs, train_idx=train_idx, val_idx=val_idx, patience=patience,
        )
        results.append(metrics)

    PREPROCESSOR_PATH = "./Model/preprocessor.joblib"
    joblib.dump(preprocessor, PREPROCESSOR_PATH)
    print(f"\nPreprocessor saved to '{PREPROCESSOR_PATH}' (shared by all targets)")

    print("\n" + "=" * 50)
    print("SUMMARY (all targets)")
    print("=" * 50)
    for r in results:
        print(f"{r['target']:<18} MAE: {r['mae']:.4f} uW | R2: {r['r2']:.4f} | "
              f"MAPE(full): {r['mape_full']:.2f}% | MAPE(>0.1uW): {r['mape_stable']:.2f}% | "
              f"MAPE(<=0.1uW): {r['mape_low_power']:.2f}%")

    return results


if __name__ == "__main__":
    train_all_models()