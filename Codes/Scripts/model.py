"""Train dual PyTorch ResNets for early-stage digital IC power prediction.

The pipeline trains independent dynamic and leakage models using grouped design
splits. TensorBoard is the sole training-monitoring backend; checkpoints and
their fitted preprocessors are written to ``Model/`` for GUI and CLI inference.
"""

import copy
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import OneHotEncoder, StandardScaler


# ============================================================
# 1. Feature Engineering & Definitions
# ============================================================


def create_tensorboard_writer(log_directory):
    """Create the TensorBoard writer only when a training run requires it.

    Keeping this import local allows saved models to be used for inference in an
    environment that does not install the optional TensorBoard application.
    """
    try:
        from torch.utils.tensorboard import SummaryWriter
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "TensorBoard is required for training. Install it with "
            "'pip install tensorboard'."
        ) from error
    return SummaryWriter(log_dir=log_directory)


def engineer_domain_features(df):
    df = df.copy()

    # 1. Capacitance components (Pin + Wire approximation via Manhattan distance)
    df["c_pin"] = df["cell_count"] * df["avg_fanin"] * df["avg_cell_area"]
    df["c_wire"] = (
        df["num_nets"]
        * df["avg_fanout"]
        * np.sqrt(df["total_area"].clip(lower=0))
    )
    df["c_total_proxy"] = df["c_pin"] + df["c_wire"]

    # 2. Sequential / Clock Tree Load Proxy
    df["seq_proxy"] = (
        df["seq_cell_count"] * (df["vdd"] ** 2) * df["clock_frequency_mhz"]
    )

    # 3. Pure physical dynamic power proxy (alpha * f * V^2 * C)
    df["phys_dynamic_proxy"] = (
        df["avg_net_toggle"]
        * df["clock_frequency_mhz"]
        * (df["vdd"] ** 2)
        * df["c_total_proxy"]
    )

    # 4. Physical Leakage Proxy (Area * Vdd * Temp_exponential)
    df["phys_leakage_proxy"] = (
        df["total_area"]
        * df["vdd"]
        * np.exp((df["temperature"] + 273.15) / 300.0)
    )

    log_columns = [
        "cell_count", "comb_cell_count", "seq_cell_count",
        "inv_count", "buf_count", "nand_count", "nor_count",
        "xor_count", "mux_count", "other_count",
        "total_area", "num_nets", "num_inputs", "num_outputs",
        "c_pin", "c_wire", "c_total_proxy", "seq_proxy",
        "phys_dynamic_proxy", "phys_leakage_proxy",
    ]
    for col in log_columns:
        df[f"log_{col}"] = np.log1p(df[col].clip(lower=0))

    return df


def get_dynamic_features():
    num_features = [
        "clock_frequency_mhz", "toggle_rate", "static_probability", "vdd",
        "temperature",
        "log_cell_count", "log_comb_cell_count", "log_seq_cell_count",
        "log_inv_count", "log_buf_count", "log_nand_count", "log_nor_count",
        "log_xor_count", "log_mux_count", "log_other_count",
        "log_total_area", "log_num_nets", "log_num_inputs", "log_num_outputs",
        "avg_cell_area", "max_fanout", "avg_fanout", "avg_fanin",
        "logic_depth", "depth_mean", "depth_std", "depth_max",
        "avg_net_toggle", "toggle_attenuation",
        "critical_path_delay", "wns", "tns",
        "log_c_pin", "log_c_wire", "log_c_total_proxy",
        "log_seq_proxy", "log_phys_dynamic_proxy",
    ]
    cat_features = ["process", "pvt_corner"]
    return num_features + cat_features, num_features, cat_features


def get_leakage_features():
    num_features = [
        "vdd", "temperature", "log_phys_leakage_proxy",
        "log_total_area", "log_cell_count", "log_comb_cell_count", "log_seq_cell_count",
        "static_probability"
    ]
    cat_features = ["process", "pvt_corner"]
    return num_features + cat_features, num_features, cat_features


def load_data():
    print("Loading datasets...")
    df1 = pd.read_csv("../Datasets/dataset_power.csv")
    df2 = pd.read_csv("../Datasets/dataset_power_alt.csv")
    df = pd.concat([df1, df2], ignore_index=True)
    df = df[df["cell_count"] > 0].copy()
    return df.reset_index(drop=True)


def make_grouped_split(df, test_size=0.15, val_size=0.15, random_state=42):
    indices = np.arange(len(df))
    groups = df["design_name"].to_numpy()

    gss_test = GroupShuffleSplit(
        n_splits=1, test_size=test_size, random_state=random_state
    )
    train_val_idx, test_idx = next(gss_test.split(indices, groups=groups))

    val_relative = val_size / (1.0 - test_size)
    gss_val = GroupShuffleSplit(
        n_splits=1, test_size=val_relative, random_state=random_state + 1
    )
    train_idx_local, val_idx_local = next(
        gss_val.split(train_val_idx, groups=groups[train_val_idx])
    )

    return (
        np.asarray(train_val_idx[train_idx_local]),
        np.asarray(train_val_idx[val_idx_local]),
        np.asarray(test_idx),
    )


def build_preprocessor(num_features, cat_features):
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), num_features),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                cat_features,
            ),
        ]
    )


def log_target(df, target_column):
    return np.log(df[target_column].clip(lower=1e-6).to_numpy(dtype=np.float32))


def calculate_metrics(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)

    # 1. Standard MAPE (Sensitive to near-zero values)
    mape_full = np.mean(np.abs((y_true - y_pred) / y_true)) * 100.0

    # 2. Filtered MAPE for Active Power (> 0.1 uW)
    mask = y_true > 0.1
    if mask.any():
        mape_stable = (
            np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0
        )
    else:
        mape_stable = float("nan")

    # 3. Symmetric MAPE (sMAPE) - Bounded & Robust to Outliers near zero
    # Absolute sums plus epsilon prevent division by zero.
    smape_full = np.mean(
        2.0 * np.abs(y_pred - y_true)
        / (np.abs(y_true) + np.abs(y_pred) + 1e-6)
    ) * 100.0

    return {
        "mae": mae,
        "r2": r2,
        "smape_full": smape_full,
        "mape_stable": mape_stable,
        "mape_full": mape_full,
    }


# ============================================================
# 2. PyTorch Architectures & MAPELoss
# ============================================================

class MAPELoss(nn.Module):
    def __init__(self, eps=1e-3):
        super().__init__()
        self.eps = eps

    def forward(self, y_pred_log, y_true_log):
        y_pred = torch.exp(y_pred_log)
        y_true = torch.exp(y_true_log)
        relative_error = torch.abs(y_pred - y_true) / (y_true + self.eps)
        return torch.mean(relative_error)


class ResidualBlock(nn.Module):
    def __init__(self, dim, dropout=0.15):
        super().__init__()
        self.fc1 = nn.Linear(dim, dim)
        self.norm1 = nn.LayerNorm(dim)
        self.act = nn.GELU()
        self.drop = nn.Dropout(dropout)
        self.fc2 = nn.Linear(dim, dim)
        self.norm2 = nn.LayerNorm(dim)

    def forward(self, x):
        residual = x
        out = self.act(self.norm1(self.fc1(x)))
        out = self.norm2(self.fc2(out))
        return self.act(out + residual)


class DynamicResNet(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.in_proj = nn.Linear(input_dim, 512)

        self.block1 = ResidualBlock(512)
        self.block2 = ResidualBlock(512)
        self.block3 = ResidualBlock(512)

        self.out_proj = nn.Sequential(
            nn.Linear(512, 128),
            nn.GELU(),
            nn.Linear(128, 1)
        )

    def forward(self, x):
        x = nn.GELU()(self.in_proj(x))
        x = self.block1(x)
        x = self.block2(x)
        x = self.block3(x)
        return self.out_proj(x)


class LeakageResNet(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.in_proj = nn.Linear(input_dim, 128)
        self.block1 = ResidualBlock(128)
        self.block2 = ResidualBlock(128)
        self.out_proj = nn.Linear(128, 1)

    def forward(self, x):
        x = nn.GELU()(self.in_proj(x))
        x = self.block1(x)
        x = self.block2(x)
        return self.out_proj(x)


# ============================================================
# 3. Dynamic Power Training Execution
# ============================================================

def train_dynamic_pytorch(df_train, df_val, df_test, device, epochs=200, patience=35):
    print("\n" + "=" * 60)
    print("Training DYNAMIC Power (DynamicResNet + TensorBoard)")
    print("=" * 60)

    writer = create_tensorboard_writer("./runs/dynamic_power")

    df_train_eng = engineer_domain_features(df_train)
    df_val_eng = engineer_domain_features(df_val)
    df_test_eng = engineer_domain_features(df_test)

    features, num_features, cat_features = get_dynamic_features()
    preprocessor = build_preprocessor(num_features, cat_features)

    X_train = preprocessor.fit_transform(df_train_eng[features]).astype(np.float32)
    X_val = preprocessor.transform(df_val_eng[features]).astype(np.float32)
    X_test = preprocessor.transform(df_test_eng[features]).astype(np.float32)

    y_train = log_target(df_train, "dynamic_power_uW")
    y_val = log_target(df_val, "dynamic_power_uW")

    train_loader = DataLoader(
        TensorDataset(torch.tensor(X_train), torch.tensor(y_train).unsqueeze(1)),
        batch_size=512, shuffle=True, pin_memory=(device.type == "cuda")
    )

    X_val_t = torch.tensor(X_val, device=device)
    y_val_t = torch.tensor(y_val, device=device).unsqueeze(1)
    X_test_t = torch.tensor(X_test, device=device)

    model = DynamicResNet(X_train.shape[1]).to(device)
    criterion = MAPELoss(eps=1e-2)

    optimizer = optim.AdamW(model.parameters(), lr=0.0008, weight_decay=1e-3)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=epochs, eta_min=1e-6
    )

    best_val_loss = float("inf")
    best_state = None
    best_epoch = -1
    epochs_no_improve = 0

    print(f"Training Dynamic ResNet ({epochs} epochs, patience={patience})...")

    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for b_X, b_y in train_loader:
            b_X, b_y = b_X.to(device), b_y.to(device)
            optimizer.zero_grad()
            outputs = model(b_X)
            loss = criterion(outputs, b_y)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()

        scheduler.step()

        model.eval()
        with torch.no_grad():
            val_loss = criterion(model(X_val_t), y_val_t).item()

        avg_train_loss = train_loss / len(train_loader)

        # TensorBoard real-time logging
        writer.add_scalar("Dynamic/Train_Loss_MAPE", avg_train_loss, epoch + 1)
        writer.add_scalar("Dynamic/Val_Loss_MAPE", val_loss, epoch + 1)
        writer.add_scalar(
            "Dynamic/Learning_Rate", optimizer.param_groups[0]["lr"], epoch + 1
        )

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = epoch + 1
            best_state = copy.deepcopy(model.state_dict())
            epochs_no_improve = 0
        else:
            epochs_no_improve += 1

        if (epoch + 1) % 10 == 0 or epoch == 0:
            print(
                f"Epoch {epoch + 1}/{epochs} - Train Loss: {avg_train_loss:.4f} | "
                f"Val Loss: {val_loss:.4f} (best: {best_val_loss:.4f} @ "
                f"Ep {best_epoch})"
            )

        if epochs_no_improve >= patience:
            print(
                f"\nEarly stopping triggered at epoch {epoch + 1}! Best epoch was "
                f"{best_epoch} with Val Loss: {best_val_loss:.4f}"
            )
            break

    writer.close()

    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        preds_log = model(X_test_t).cpu().numpy().flatten()

    y_test_true = df_test["dynamic_power_uW"].to_numpy()
    metrics = calculate_metrics(y_test_true, np.exp(preds_log))

    Path("./Model").mkdir(exist_ok=True)
    torch.save(model.state_dict(), "./Model/dynamic_power_predictor_model.pth")
    joblib.dump(preprocessor, "./Model/preprocessor_dynamic.joblib")

    metrics["target"] = "dynamic_power_uW"
    return metrics


# ============================================================
# 4. Leakage Power Training Execution
# ============================================================

def train_leakage_pytorch(df_train, df_val, df_test, device, epochs=120, patience=20):
    print("\n" + "=" * 60)
    print("Training LEAKAGE Power (LeakageResNet + TensorBoard)")
    print("=" * 60)

    writer = create_tensorboard_writer("./runs/leakage_power")

    df_train_eng = engineer_domain_features(df_train)
    df_val_eng = engineer_domain_features(df_val)
    df_test_eng = engineer_domain_features(df_test)

    features, num_features, cat_features = get_leakage_features()
    preprocessor = build_preprocessor(num_features, cat_features)

    X_train = preprocessor.fit_transform(df_train_eng[features]).astype(np.float32)
    X_val = preprocessor.transform(df_val_eng[features]).astype(np.float32)
    X_test = preprocessor.transform(df_test_eng[features]).astype(np.float32)

    y_train = log_target(df_train, "leakage_power_uW")
    y_val = log_target(df_val, "leakage_power_uW")

    train_loader = DataLoader(
        TensorDataset(torch.tensor(X_train), torch.tensor(y_train).unsqueeze(1)),
        batch_size=1024, shuffle=True, pin_memory=(device.type == "cuda")
    )

    X_val_t = torch.tensor(X_val, device=device)
    y_val_t = torch.tensor(y_val, device=device).unsqueeze(1)
    X_test_t = torch.tensor(X_test, device=device)

    model = LeakageResNet(X_train.shape[1]).to(device)
    criterion = MAPELoss(eps=1e-3)
    optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=5
    )

    best_val_loss = float("inf")
    best_state = None
    best_epoch = -1
    epochs_no_improve = 0

    print(f"Training Leakage ResNet ({epochs} epochs, patience={patience})...")

    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for b_X, b_y in train_loader:
            b_X, b_y = b_X.to(device), b_y.to(device)
            optimizer.zero_grad()
            outputs = model(b_X)
            loss = criterion(outputs, b_y)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()

        model.eval()
        with torch.no_grad():
            val_loss = criterion(model(X_val_t), y_val_t).item()

        scheduler.step(val_loss)

        avg_train_loss = train_loss / len(train_loader)

        # TensorBoard real-time logging
        writer.add_scalar("Leakage/Train_Loss_MAPE", avg_train_loss, epoch + 1)
        writer.add_scalar("Leakage/Val_Loss_MAPE", val_loss, epoch + 1)
        writer.add_scalar(
            "Leakage/Learning_Rate", optimizer.param_groups[0]["lr"], epoch + 1
        )

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = epoch + 1
            best_state = copy.deepcopy(model.state_dict())
            epochs_no_improve = 0
        else:
            epochs_no_improve += 1

        if (epoch + 1) % 10 == 0 or epoch == 0:
            print(
                f"Epoch {epoch + 1}/{epochs} - Train Loss: {avg_train_loss:.4f} | "
                f"Val Loss: {val_loss:.4f} (best: {best_val_loss:.4f} @ "
                f"Ep {best_epoch})"
            )

        if epochs_no_improve >= patience:
            print(
                f"\nEarly stopping triggered at epoch {epoch + 1}! Best epoch was "
                f"{best_epoch} with Val Loss: {best_val_loss:.4f}"
            )
            break

    writer.close()

    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        preds_log = model(X_test_t).cpu().numpy().flatten()

    y_test_true = df_test["leakage_power_uW"].to_numpy()
    metrics = calculate_metrics(y_test_true, np.exp(preds_log))

    Path("./Model").mkdir(exist_ok=True)
    torch.save(model.state_dict(), "./Model/leakage_power_predictor_model.pth")
    joblib.dump(preprocessor, "./Model/preprocessor_leakage.joblib")

    metrics["target"] = "leakage_power_uW"
    return metrics


# ============================================================
# 5. Main Execution Pipeline
# ============================================================

def train_all_models(train_dynamic=True, train_leakage=True):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    df = load_data()
    train_idx, val_idx, test_idx = make_grouped_split(df)

    df_train = df.iloc[train_idx].copy()
    df_val = df.iloc[val_idx].copy()
    df_test = df.iloc[test_idx].copy()

    metrics_list = []

    if train_dynamic:
        dyn_metrics = train_dynamic_pytorch(df_train, df_val, df_test, device)
        metrics_list.append(dyn_metrics)

    if train_leakage:
        leak_metrics = train_leakage_pytorch(df_train, df_val, df_test, device)
        metrics_list.append(leak_metrics)

    print("\n" + "=" * 60)
    print("FINAL SUMMARY (TEST SET)")
    print("=" * 60)
    for m in metrics_list:
        print(
            f"{m['target']:<18} "
            f"MAE: {m['mae']:.4f} uW | "
            f"R2: {m['r2']:.4f} | "
            f"sMAPE: {m['smape_full']:.2f}% | "
            f"MAPE(>0.1uW): {m['mape_stable']:.2f}%"
        )


if __name__ == "__main__":
    train_all_models(train_dynamic=True, train_leakage=False)
