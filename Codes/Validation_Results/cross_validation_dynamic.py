import numpy as np
import pandas as pd
import torch
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import GroupKFold

from model import (
    load_data,
    engineer_domain_features,
    get_dynamic_features,
    build_preprocessor,
    log_target,
    calculate_metrics,
    DynamicResNet,
    WeightedMAPELoss,
)


def run_5fold_cv_dynamic(epochs=60, batch_size=512):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device for Cross-Validation: {device}")

    # 1. Load & Engineer features
    df = load_data()
    df_eng = engineer_domain_features(df)
    features, num_features, cat_features = get_dynamic_features()

    groups = df_eng["design_name"].to_numpy()
    gkf = GroupKFold(n_splits=5)

    fold_metrics = []

    print("\n" + "=" * 60)
    print("STARTING 5-FOLD GROUPED CROSS-VALIDATION (DYNAMIC POWER)")
    print("=" * 60)

    for fold, (train_idx, val_idx) in enumerate(gkf.split(df_eng, groups=groups)):
        df_train = df_eng.iloc[train_idx].copy()
        df_val = df_eng.iloc[val_idx].copy()

        # Build clean preprocessor per fold to avoid data leakage
        preprocessor = build_preprocessor(num_features, cat_features)
        X_train = preprocessor.fit_transform(df_train[features]).astype(np.float32)
        X_val = preprocessor.transform(df_val[features]).astype(np.float32)

        y_train = log_target(df_train, "dynamic_power_uW")
        y_val_true = df_val["dynamic_power_uW"].to_numpy()

        train_loader = DataLoader(
            TensorDataset(torch.tensor(X_train), torch.tensor(y_train).unsqueeze(1)),
            batch_size=batch_size,
            shuffle=True,
        )

        X_val_t = torch.tensor(X_val, device=device)

        # Model & Training setup
        model = DynamicResNet(X_train.shape[1]).to(device)
        criterion = WeightedMAPELoss(eps=1e-2, threshold_uW=0.1, low_weight=2.0, high_weight=1.0)
        optimizer = optim.AdamW(model.parameters(), lr=0.0008, weight_decay=5e-3)

        for epoch in range(epochs):
            model.train()
            for b_X, b_y in train_loader:
                b_X, b_y = b_X.to(device), b_y.to(device)
                optimizer.zero_grad()
                loss = criterion(model(b_X), b_y)
                loss.backward()
                optimizer.step()
            if (epoch + 1) % 10 == 0 or epoch == 0:
                print(f"  Fold {fold + 1} | Epoch {epoch + 1}/{epochs} finished")

        # Evaluate Validation Fold
        model.eval()
        with torch.no_grad():
            preds_log = model(X_val_t).cpu().numpy().flatten()

        metrics = calculate_metrics(y_val_true, np.exp(preds_log))
        fold_metrics.append(metrics)

        print(
            f"Fold {fold + 1}/5 -> MAE: {metrics['mae']:.4f} uW | "
            f"R2: {metrics['r2']:.4f} | MAPE(>0.1uW): {metrics['mape_stable']:.2f}%"
        )

    # Summary
    mean_r2 = np.mean([m["r2"] for m in fold_metrics])
    std_r2 = np.std([m["r2"] for m in fold_metrics])
    mean_mape = np.mean([m["mape_stable"] for m in fold_metrics])

    print("\n" + "=" * 60)
    print("5-FOLD CV SUMMARY RESULTS")
    print("=" * 60)
    print(f"Mean R2 Score: {mean_r2:.4f} (+/- {std_r2:.4f})")
    print(f"Mean Active MAPE (>0.1uW): {mean_mape:.2f}%")


if __name__ == "__main__":
    run_5fold_cv_dynamic(epochs=60)