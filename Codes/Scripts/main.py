"""Command-line inference interface for Dual PyTorch IC power models.

The module intentionally keeps presentation and file I/O thin. ``ICPowerPredictor``
is the Facade that owns the inference workflow and its model dependencies.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Optional, Type, Union

import joblib
import numpy as np
import pandas as pd
import torch

from model import (
    DynamicResNet,
    LeakageResNet,
    engineer_domain_features,
    get_dynamic_features,
    get_leakage_features,
)

InputPath = Union[str, Path]


class ICPowerPredictor:
    """Facade for loading and executing dual-model IC power inference.

    Args:
        models_dir: Directory containing model weights and fitted preprocessors.
        device: Optional PyTorch device; CUDA is selected automatically when present.

    Raises:
        FileNotFoundError: If one or more inference assets are unavailable.
        RuntimeError: If an asset cannot be deserialized or is incompatible.
    """

    def __init__(
        self,
        models_dir: InputPath = "./Model",
        device: Optional[torch.device] = None,
    ) -> None:
        self.models_dir = Path(models_dir)
        self.device = device or torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self._paths = {
            "dynamic_preprocessor": self.models_dir / "preprocessor_dynamic.joblib",
            "leakage_preprocessor": self.models_dir / "preprocessor_leakage.joblib",
            "dynamic_model": self.models_dir / "dynamic_power_predictor_model.pth",
            "leakage_model": self.models_dir / "leakage_power_predictor_model.pth",
        }
        self._verify_assets()
        self._load_assets()

    def _verify_assets(self) -> None:
        missing = [str(path) for path in self._paths.values() if not path.is_file()]
        if missing:
            formatted_paths = "\n  - ".join(missing)
            raise FileNotFoundError(
                f"Missing required inference assets:\n  - {formatted_paths}"
            )

    def _load_assets(self) -> None:
        try:
            self._dynamic_preprocessor = joblib.load(
                self._paths["dynamic_preprocessor"]
            )
            self._leakage_preprocessor = joblib.load(
                self._paths["leakage_preprocessor"]
            )
            self._dynamic_model = self._load_model(
                DynamicResNet,
                self._dynamic_preprocessor,
                self._paths["dynamic_model"],
            )
            self._leakage_model = self._load_model(
                LeakageResNet,
                self._leakage_preprocessor,
                self._paths["leakage_model"],
            )
        except (AttributeError, OSError, RuntimeError, ValueError, TypeError) as error:
            raise RuntimeError(
                "Unable to load the trained PyTorch inference assets. Confirm that "
                "the weights and preprocessors were produced together."
            ) from error

    def _load_model(
        self,
        model_class: Union[Type[DynamicResNet], Type[LeakageResNet]],
        preprocessor: Any,
        weights_path: Path,
    ) -> Union[DynamicResNet, LeakageResNet]:
        """Create a model using the preprocessor output dimensionality."""
        try:
            input_dimension = len(preprocessor.get_feature_names_out())
        except AttributeError as error:
            raise ValueError(
                f"Preprocessor for '{weights_path.name}' does not expose feature names."
            ) from error

        model = model_class(input_dimension).to(self.device)
        state_dict = torch.load(
            weights_path, map_location=self.device, weights_only=True
        )
        model.load_state_dict(state_dict)
        model.eval()
        return model

    def predict(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Predict dynamic, leakage, and total power for every input row.

        Args:
            dataframe: Raw design-feature records accepted by the training pipeline.

        Returns:
            A copy of ``dataframe`` augmented with power predictions in microwatts.

        Raises:
            ValueError: If the input is empty or lacks a required feature.
        """
        if dataframe.empty:
            raise ValueError("The input dataset contains no rows.")

        engineered = engineer_domain_features(dataframe).reset_index(drop=True)
        dynamic_features, _, _ = get_dynamic_features()
        leakage_features, _, _ = get_leakage_features()
        self._require_features(engineered, dynamic_features + leakage_features)

        dynamic_power = self._predict_component(
            engineered,
            dynamic_features,
            self._dynamic_preprocessor,
            self._dynamic_model,
        )
        leakage_power = self._predict_component(
            engineered,
            leakage_features,
            self._leakage_preprocessor,
            self._leakage_model,
        )

        result = dataframe.copy()
        result["predicted_dynamic_power_uW"] = dynamic_power
        result["predicted_leakage_power_uW"] = leakage_power
        result["predicted_total_power_uW"] = dynamic_power + leakage_power
        return result

    @staticmethod
    def _require_features(dataframe: pd.DataFrame, features: Sequence[str]) -> None:
        missing = sorted(set(features).difference(dataframe.columns))
        if missing:
            raise ValueError(
                f"Input dataset is missing required features: {', '.join(missing)}"
            )

    def _predict_component(
        self,
        dataframe: pd.DataFrame,
        features: Sequence[str],
        preprocessor: Any,
        model: Union[DynamicResNet, LeakageResNet],
    ) -> np.ndarray:
        transformed = preprocessor.transform(dataframe[list(features)]).astype(
            np.float32
        )
        inputs = torch.as_tensor(transformed, device=self.device)
        with torch.inference_mode():
            log_predictions = model(inputs).cpu().numpy().ravel()
        return np.exp(log_predictions)


def load_input_data(file_path: InputPath) -> pd.DataFrame:
    """Load CSV, JSON, or Excel records into a dataframe.

    Args:
        file_path: Existing ``.csv``, ``.json``, ``.xlsx``, or ``.xls`` input file.

    Raises:
        FileNotFoundError: If ``file_path`` does not exist.
        ValueError: If the file extension or JSON payload is unsupported.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Input file not found: {path}")

    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if path.suffix.lower() == ".json":
        with path.open(encoding="utf-8") as input_file:
            payload = json.load(input_file)
        if isinstance(payload, dict):
            return pd.DataFrame([payload])
        if isinstance(payload, list):
            return pd.DataFrame(payload)
        raise ValueError("JSON input must contain an object or a list of objects.")
    raise ValueError("Unsupported input format. Use CSV, JSON, XLS, or XLSX.")


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input_file", nargs="?", type=Path, help="Input CSV, JSON, or Excel file."
    )
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=Path("./Model"),
        help="Directory containing weights and preprocessors (default: %(default)s).",
    )
    parser.add_argument("--output", type=Path, help="Optional CSV path for results.")
    return parser


def main() -> int:
    """Run the CLI and return a process status code."""
    arguments = build_parser().parse_args()
    input_path = arguments.input_file or Path(
        input("Enter path to input dataset (.csv, .json, .xlsx): ").strip()
    )

    try:
        predictor = ICPowerPredictor(arguments.models_dir)
        predictions = predictor.predict(load_input_data(input_path))
    except (
        FileNotFoundError,
        OSError,
        ValueError,
        RuntimeError,
        json.JSONDecodeError,
    ) as error:
        print(f"Inference failed: {error}")
        return 1

    print(
        predictions[
            [
                "predicted_total_power_uW",
                "predicted_dynamic_power_uW",
                "predicted_leakage_power_uW",
            ]
        ].to_string(index=False)
    )
    if arguments.output:
        predictions.to_csv(arguments.output, index=False)
        print(f"Saved predictions to: {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
