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

def train_model():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    # 1. Loading data
    print("Loading datasets...")
    df1 = pd.read_csv("../Datasets/dataset_power.csv")
    df2 = pd.read_csv("../Datasets/dataset_power_alt.csv")
    df = pd.concat([df1, df2], ignore_index=True)

    df = df[df['cell_count'] > 0]
    df = df[df['total_power_uW'] >= 0.1]

    # We apply log-scale to both Target and large features.
    y_raw = df['total_power_uW'].values.astype(np.float32)
    y_log = np.log1p(y_raw)

    df['v2_freq'] = (df['vdd'] ** 2) * df['clock_frequency_mhz'] # vdd² * f

    # We also logarithmize area and cell_count so that the network can easily understand the scale.
    log_columns = [
        'cell_count', 'comb_cell_count', 'seq_cell_count', 
        'inv_count', 'buf_count', 'nand_count', 'nor_count', 'xor_count', 'mux_count', 'other_count',
        'total_area', 'num_nets', 'num_inputs', 'num_outputs'
    ]

    for col in log_columns:
        df[f"log_{col}"] = np.log1p(df[col])

    # 2. Preprocessing
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

    # We also add pvt_corner as a categorical variable.
    cat_features = ['process', 'pvt_corner']

    features = num_features + cat_features

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), num_features),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), cat_features)
        ])

    X_processed = preprocessor.fit_transform(df[features]).astype(np.float32)
    input_dim = X_processed.shape[1]
    print(f"New Input Dimension (Features count): {input_dim}")

    # 3. Train/Val Split
    X_train, X_val, y_train, y_val = train_test_split(
        X_processed, y_log, test_size=0.2, random_state=42
    )
    y_val_true = np.expm1(y_val) 

    train_dataset = TensorDataset(torch.tensor(X_train), torch.tensor(y_train).unsqueeze(1))
    train_loader = DataLoader(train_dataset, batch_size=2048, shuffle=True)

    model = PowerNet(input_dim).to(device)
    criterion = nn.MSELoss()

    optimizer = optim.AdamW(model.parameters(), lr=0.003, weight_decay=1e-4)

    EPOCHS = 60
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

    # 5. Training
    print(f"\nTraining Neural Network ({EPOCHS} Epochs with Scheduler)...")
    model.train()
    for epoch in range(EPOCHS):
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
            print(f"Epoch {epoch+1}/{EPOCHS} - Loss: {epoch_loss/len(train_loader):.5f} - LR: {scheduler.get_last_lr()[0]:.5f}")

    # 6. Rating
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

    WEIGHT_PATH = "./Model/power_predictor_model.pth"

    torch.save(model.state_dict(), f'{WEIGHT_PATH}')
    print(f"Model weights saved to '{WEIGHT_PATH}'")

    PREPROCESSOR_PATH = "./Model/preprocessor.joblib"
    joblib.dump(preprocessor, f'{PREPROCESSOR_PATH}')
    print(f"Preprocessor saved to '{PREPROCESSOR_PATH}'")

    print("\n" + "="*50)
    print("UPDATED EVALUATION RESULTS (Non-Log Scale uW):")
    print(f"MAE:        {mae:.4f} uW")
    print(f"R2 Score:   {r2:.4f}")
    print(f"Stable MAPE: {mape_stable:.2f}%")
    print("="*50)

if __name__ == "__main__":
    train_model()
